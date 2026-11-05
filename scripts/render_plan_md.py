#!/usr/bin/env python
"""Render a human-readable table from a traceability matrix.

``plans/<id>.traceability.json`` is the machine format; this script writes
``plans/<id>.traceability.md`` next to it so a reviewer can read the matrix
without opening JSON.

Usage::

    python scripts/render_plan_md.py plans/<id>.traceability.json
    python scripts/render_plan_md.py plans/<id>.traceability.json --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _cell(value: object) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def render(matrix: dict) -> str:
    plan_id = matrix.get("plan_id", "")
    lines = [
        f"# 追溯矩阵：{plan_id}",
        "",
        "> 由 `scripts/render_plan_md.py` 从同名 JSON 生成；`--check` 校验是否同步。",
        "",
        "| 条目 | 契约 | 测试 | 状态 |",
        "|---|---|---|---|",
    ]
    for item in matrix.get("items", []):
        contract = item.get("contract")
        if contract:
            methods = ",".join(contract.get("methods", []))
            contract_text = f"`{methods} {contract.get('rule', '')}`"
        else:
            contract_text = "—（内部改动）"
        test = item.get("test") or "—"
        lines.append(
            f"| {_cell(item.get('id'))} | {contract_text} | "
            f"`{_cell(test)}` | {_cell(item.get('status'))} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    matrix_path = Path(args.matrix)
    md_path = matrix_path.with_suffix(".md")
    matrix = json.loads(matrix_path.read_text(encoding="utf-8-sig"))
    expected = render(matrix)

    if args.check:
        if not md_path.is_file() or md_path.read_text(encoding="utf-8").strip() != expected.strip():
            print(f"render_plan_md: {md_path.name} is stale or missing", file=sys.stderr)
            return 1
        print(f"render_plan_md: {md_path.name} is in sync")
        return 0

    md_path.write_text(expected, encoding="utf-8")
    print(f"render_plan_md: wrote {md_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
