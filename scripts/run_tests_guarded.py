#!/usr/bin/env python
"""Run the tests with the rule-4 circuit breaker.

.dsh_rules 规则 4（负结果止损）：同一个方向连续两次负结果必须停下来讨论，
不得继续调参掩盖问题。本脚本把这条规则变成退出码：

    0  本轮通过（失败计数清零）
    1  本轮失败，但尚未触发熔断
    2  同一目标连续失败达到阈值 —— 必须停下向人类汇报

Usage::

    python scripts/run_tests_guarded.py
    python scripts/run_tests_guarded.py --cmd "python -m pytest tests -q"
    python scripts/run_tests_guarded.py --reset      # 清空计数

State: ``.guard/tests.json``
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import _guard  # noqa: E402

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_BREAKER = 2

FAILED_LINE = re.compile(r"^FAILED\s+(\S+)", re.MULTILINE)


def parse_failures(output: str) -> list[str]:
    """Best-effort extraction of failing test ids from pytest output."""
    return sorted(set(FAILED_LINE.findall(output)))


def main(argv: list[str] | None = None) -> int:
    _guard.ensure_utf8_stdout()
    parser = argparse.ArgumentParser(description="rule-4 guarded test runner")
    parser.add_argument("--cmd", default="python -m pytest -q", help="command to run")
    parser.add_argument("--limit", type=int, default=2, help="consecutive failures before the breaker")
    parser.add_argument("--target", default="pytest", help="identity used to key the counter")
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--reset", action="store_true", help="clear the counter and exit")
    args = parser.parse_args(argv)

    base = _guard.state_dir(args.state_dir)
    state = _guard.load_state("tests", base)
    targets = state.setdefault("targets", {})

    if args.reset:
        targets.pop(args.target, None)
        _guard.save_state("tests", base, state)
        print(f"guard: counter for {args.target!r} cleared")
        return EXIT_OK

    print(f"guard: running {args.cmd}")
    completed = subprocess.run(
        args.cmd, shell=True, capture_output=True, encoding="utf-8", errors="replace"
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    sys.stdout.write(output)
    sys.stdout.flush()

    record = targets.setdefault(args.target, {"consecutive_failures": 0, "last_failed": []})

    if completed.returncode == 0:
        record["consecutive_failures"] = 0
        record["last_failed"] = []
        record["updated_at"] = _guard.now()
        _guard.save_state("tests", base, state)
        print("guard: pass — failure counter reset")
        return EXIT_OK

    record["consecutive_failures"] = int(record.get("consecutive_failures", 0)) + 1
    record["last_failed"] = parse_failures(output)
    record["updated_at"] = _guard.now()
    _guard.save_state("tests", base, state)

    streak = record["consecutive_failures"]
    print(
        f"guard: fail #{streak} for {args.target!r}"
        + (f" ({len(record['last_failed'])} failing)" if record["last_failed"] else "")
    )

    if streak >= args.limit:
        print(
            _guard.banner(
                "RULE-4 BREAKER",
                [
                    f"同一目标连续 {streak} 次失败，已触发规则 4 熔断。",
                    "",
                    "停止调参。先向人类说明卡点，不得继续覆盖问题。",
                    "确认继续后，用 --reset 清空计数再跑。",
                ],
            )
        )
        return EXIT_BREAKER

    print(f"guard: {args.limit - streak} more consecutive failure(s) would trip the breaker")
    return EXIT_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
