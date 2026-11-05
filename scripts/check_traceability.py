#!/usr/bin/env python
"""Check a plan's traceability matrix against the contract and the tests.

A plan item is only "done" when three things line up:

    plan item  <->  ARCHITECTURE.json entry  <->  an existing test

Usage::

    python scripts/check_traceability.py plans/2026-11-05-foo.traceability.json
    python scripts/check_traceability.py docs/templates/追溯矩阵.example.json \
        --tests-root ../dsh-snapshot

Exit codes: 0 = aligned, 1 = mismatch, 2 = unreadable input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUSES = {"implemented", "planned"}


def load_json(path: Path) -> dict:
    # ``utf-8-sig`` tolerates the BOM Windows editors add; json.loads rejects it.
    return json.loads(path.read_text(encoding="utf-8-sig"))


def contract_index(arch: dict) -> dict[tuple[str, str, tuple[str, ...]], dict]:
    index = {}
    for entry in arch.get("api", {}).get("endpoints", []):
        key = (
            str(entry.get("rule", "")),
            str(entry.get("endpoint", "")),
            tuple(sorted(str(method) for method in entry.get("methods", []))),
        )
        index[key] = entry
    return index


def test_present(tests_root: Path, ref: str) -> tuple[bool, str]:
    if "::" not in ref:
        return False, "test must be written as 'relative/path.py::test_name'"
    path_part, name = ref.split("::", 1)
    path = tests_root / path_part
    if not path.is_file():
        return False, f"test file not found: {path_part}"
    source = path.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(rf"^\s*(?:async\s+)?def\s+{re.escape(name)}\s*\(", re.MULTILINE)
    if pattern.search(source) is None:
        return False, f"test function not found: {name}"
    return True, ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", help="path to <plan-id>.traceability.json")
    parser.add_argument(
        "--arch", default=str(ROOT / "ARCHITECTURE.json"), help="contract file"
    )
    parser.add_argument(
        "--tests-root",
        default=str(ROOT),
        help="directory that test paths are relative to (the code repo)",
    )
    args = parser.parse_args(argv)

    try:
        matrix = load_json(Path(args.matrix))
        arch = load_json(Path(args.arch))
    except (OSError, ValueError) as exc:
        print(f"check_traceability: cannot read input: {exc}", file=sys.stderr)
        return 2

    index = contract_index(arch)
    tests_root = Path(args.tests_root)
    items = matrix.get("items") or []
    errors: list[str] = []

    if not items:
        errors.append("matrix has no items")

    for item in items:
        item_id = str(item.get("id") or "?")
        status = item.get("status")
        if status not in STATUSES:
            errors.append(f"{item_id}: status must be one of {sorted(STATUSES)}")
            continue

        contract = item.get("contract")
        if contract is not None:
            key = (
                str(contract.get("rule", "")),
                str(contract.get("endpoint", "")),
                tuple(sorted(str(method) for method in contract.get("methods", []))),
            )
            if key not in index:
                rule, endpoint, methods = key
                errors.append(
                    f"{item_id}: contract not in ARCHITECTURE.json: "
                    f"{rule} {endpoint} {list(methods)}"
                )

        test_ref = item.get("test")
        if test_ref:
            ok, reason = test_present(tests_root, str(test_ref))
            if not ok:
                errors.append(f"{item_id}: {reason}")
        elif status == "implemented":
            errors.append(f"{item_id}: implemented item needs a test reference")

    if errors:
        print(f"traceability: {len(errors)} problem(s)", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"traceability: {len(items)} item(s) aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
