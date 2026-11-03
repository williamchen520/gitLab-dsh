"""Tests for the rule-4 breaker scripts. Standard library only."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def run(script: str, *args: str, state: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args, "--state-dir", str(state)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


class RunTestsGuardedTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.state = pathlib.Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_passing_command_exits_zero(self) -> None:
        result = run("run_tests_guarded.py", "--cmd", f'"{sys.executable}" -c "pass"', state=self.state)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_two_consecutive_failures_trip_the_breaker(self) -> None:
        cmd = f'"{sys.executable}" -c "import sys; sys.exit(1)"'

        first = run("run_tests_guarded.py", "--cmd", cmd, state=self.state)
        self.assertEqual(first.returncode, 1, first.stdout)

        second = run("run_tests_guarded.py", "--cmd", cmd, state=self.state)
        self.assertEqual(second.returncode, 2, second.stdout)
        self.assertIn("RULE-4 BREAKER", second.stdout)

    def test_a_pass_resets_the_streak(self) -> None:
        fail = f'"{sys.executable}" -c "import sys; sys.exit(1)"'
        ok = f'"{sys.executable}" -c "pass"'

        self.assertEqual(run("run_tests_guarded.py", "--cmd", fail, state=self.state).returncode, 1)
        self.assertEqual(run("run_tests_guarded.py", "--cmd", ok, state=self.state).returncode, 0)
        third = run("run_tests_guarded.py", "--cmd", fail, state=self.state)
        self.assertEqual(third.returncode, 1, "a pass must clear the previous failure")

    def test_reset_clears_state(self) -> None:
        fail = f'"{sys.executable}" -c "import sys; sys.exit(1)"'
        run("run_tests_guarded.py", "--cmd", fail, state=self.state)
        run("run_tests_guarded.py", "--cmd", fail, state=self.state)

        reset = run("run_tests_guarded.py", "--reset", state=self.state)
        self.assertEqual(reset.returncode, 0)

        after = run("run_tests_guarded.py", "--cmd", fail, state=self.state)
        self.assertEqual(after.returncode, 1, "reset must restart the count")

    def test_failure_details_are_recorded(self) -> None:
        fail = (
            f'"{sys.executable}" -c "'
            "print('FAILED tests/test_x.py::test_y'); import sys; sys.exit(1)\""
        )
        run("run_tests_guarded.py", "--cmd", fail, state=self.state)
        data = json.loads((self.state / "tests.json").read_text(encoding="utf-8"))
        self.assertIn("tests/test_x.py::test_y", data["targets"]["pytest"]["last_failed"])


class RecordEvalMetricTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.state = pathlib.Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_improvement_exits_zero(self) -> None:
        first = run("record_eval_metric.py", "--name", "R@10", "--value", "0.5", state=self.state)
        second = run("record_eval_metric.py", "--name", "R@10", "--value", "0.6", state=self.state)
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)

    def test_two_non_improvements_trip_the_breaker(self) -> None:
        run("record_eval_metric.py", "--name", "R@10", "--value", "0.6", state=self.state)
        first = run("record_eval_metric.py", "--name", "R@10", "--value", "0.6", state=self.state)
        self.assertEqual(first.returncode, 0, "one non-improvement is not a breaker")

        second = run("record_eval_metric.py", "--name", "R@10", "--value", "0.55", state=self.state)
        self.assertEqual(second.returncode, 2, second.stdout)
        self.assertIn("RULE-4 BREAKER", second.stdout)

    def test_min_direction_inverts_improvement(self) -> None:
        run("record_eval_metric.py", "--name", "Loss", "--value", "0.5", "--direction", "min", state=self.state)
        better = run("record_eval_metric.py", "--name", "Loss", "--value", "0.4", "--direction", "min", state=self.state)
        self.assertEqual(better.returncode, 0)

        run("record_eval_metric.py", "--name", "Loss", "--value", "0.45", "--direction", "min", state=self.state)
        worse = run("record_eval_metric.py", "--name", "Loss", "--value", "0.5", "--direction", "min", state=self.state)
        self.assertEqual(worse.returncode, 2, worse.stdout)

    def test_metrics_are_independent(self) -> None:
        run("record_eval_metric.py", "--name", "A", "--value", "1", state=self.state)
        run("record_eval_metric.py", "--name", "B", "--value", "1", state=self.state)
        a2 = run("record_eval_metric.py", "--name", "A", "--value", "1", state=self.state)
        b2 = run("record_eval_metric.py", "--name", "B", "--value", "2", state=self.state)
        self.assertEqual(a2.returncode, 0)
        self.assertEqual(b2.returncode, 0)


if __name__ == "__main__":
    unittest.main()
