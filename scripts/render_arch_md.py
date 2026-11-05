#!/usr/bin/env python
"""Render the human-readable contract digest from ``ARCHITECTURE.json``.

The JSON stays the single source of truth; this script keeps a generated block
inside ``ARCHITECTURE.md`` (between the markers below) in sync, so reading the
architecture never means reading JSON by hand.

Usage::

    python scripts/render_arch_md.py            # rewrite the block in place
    python scripts/render_arch_md.py --check    # exit 1 when the block is stale

The prose outside the markers is untouched.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEGIN = "<!-- BEGIN GENERATED: contract-digest -->"
END = "<!-- END GENERATED: contract-digest -->"
TITLE = "## 附录 A：契约速查（自动生成，勿手改）"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _cell(value: object) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", " ")


def digest(arch: dict) -> str:
    meta = arch.get("meta", {})
    lines: list[str] = [
        BEGIN,
        TITLE,
        "",
        "> 由 `scripts/render_arch_md.py` 从 `ARCHITECTURE.json` 生成；"
        "`--check` 校验是否同步。手改本块会在下次渲染时被覆盖。",
        "",
        f"**{meta.get('name', '')} v{meta.get('version', '')}** — "
        f"{meta.get('description', '')}",
        "",
    ]

    invariants = arch.get("invariants", [])
    if invariants:
        lines += ["### 不变量", ""]
        lines += [f"{index}. {item}" for index, item in enumerate(invariants, 1)]
        lines.append("")

    decisions = arch.get("decisions", [])
    if decisions:
        lines += ["### 关键决策", "", "| id | 决定 | 选择 | 否决理由 |", "|---|---|---|---|"]
        entries = decisions.items() if isinstance(decisions, dict) else [
            (item.get("id"), item) for item in decisions
        ]
        for key, item in entries:
            rejected = "; ".join(
                f"{option}: {reason}"
                for option, reason in (item.get("rejected_because") or {}).items()
            )
            lines.append(
                f"| {_cell(key)} | {_cell(item.get('summary'))} | "
                f"{_cell(item.get('chosen'))} | {_cell(rejected)} |"
            )
        lines.append("")

    layers = arch.get("layers", {})
    kernel = layers.get("kernel", {})
    shells = layers.get("shells", [])
    lines += ["### 分层", ""]
    if kernel:
        lines.append(f"- **内核** `{kernel.get('path', '')}`（transport-free）")
        for module in kernel.get("modules", []):
            lines.append(f"  - {module}")
    for shell in shells:
        lines.append(
            f"- **{shell.get('name', '')}** `{shell.get('path', '')}`："
            f"{shell.get('tools', shell.get('endpoints', ''))} "
            f"{'tools' if 'tools' in shell else 'endpoints'}"
        )
    lines.append("")

    tools = arch.get("mcp", {}).get("tools", [])
    if tools:
        lines += [f"### MCP 工具（{len(tools)}）", "", "| 工具 | 效果 | 映射 |", "|---|---|---|"]
        for tool in tools:
            lines.append(
                f"| `{_cell(tool.get('name'))}` | {_cell(tool.get('effect'))} | "
                f"{_cell(tool.get('maps_to'))} |"
            )
        lines.append("")

    endpoints = arch.get("api", {}).get("endpoints", [])
    if endpoints:
        lines += [
            f"### HTTP 端点（{len(endpoints)}）",
            "",
            "| 方法 | 路径 | endpoint | 状态 |",
            "|---|---|---|---|",
        ]
        for entry in endpoints:
            methods = ",".join(entry.get("methods", []))
            lines.append(
                f"| {_cell(methods)} | `{_cell(entry.get('rule'))}` | "
                f"{_cell(entry.get('endpoint'))} | {_cell(entry.get('status', ''))} |"
            )
        lines.append("")

    models = arch.get("models", {})
    if models:
        lines += ["### 模型", ""]
        for name, fields in models.items():
            if isinstance(fields, dict):
                keys = "、".join(f"`{key}`" for key in fields)
                lines.append(f"- **{name}**：{keys}")
            else:
                lines.append(f"- **{name}**")
        lines.append("")

    storage = arch.get("storage", {})
    if storage:
        lines += ["### 存储", ""]
        if storage.get("adapters"):
            lines.append(f"- 适配器：{'、'.join(storage['adapters'])}")
        if storage.get("metadata_tables"):
            lines.append(f"- 表：{'、'.join(storage['metadata_tables'])}")
        if storage.get("ordering"):
            lines.append(f"- 排序：{storage['ordering']}")
        lines.append("")

    verification = arch.get("verification", {})
    if verification:
        lines += ["### 验证", ""]
        for key, value in verification.items():
            lines.append(f"- `{key}`：{value}")
        lines.append("")

    lines.append(END)
    return "\n".join(lines)


def replace_block(document: str, block: str) -> str:
    start = document.find(BEGIN)
    end = document.find(END)
    if start == -1 or end == -1:
        return document.rstrip() + "\n\n" + block + "\n"
    return document[:start] + block + document[end + len(END):]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", default=str(ROOT / "ARCHITECTURE.json"))
    parser.add_argument("--md", default=str(ROOT / "ARCHITECTURE.md"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    arch = load(Path(args.arch))
    md_path = Path(args.md)
    current = md_path.read_text(encoding="utf-8")
    expected = replace_block(current, digest(arch))

    if args.check:
        if current.strip() != expected.strip():
            print(
                "render_arch_md: ARCHITECTURE.md is stale; "
                "run `python scripts/render_arch_md.py`",
                file=sys.stderr,
            )
            return 1
        print("render_arch_md: contract digest is in sync")
        return 0

    if current == expected:
        print("render_arch_md: already in sync")
        return 0
    md_path.write_text(expected, encoding="utf-8")
    print(f"render_arch_md: updated {md_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
