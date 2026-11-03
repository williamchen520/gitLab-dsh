#!/usr/bin/env python
"""Validate the MCP tool surface against ARCHITECTURE.json.

``validate_arch.py`` covers HTTP routes; MCP tools had no machine check, which
is how the contract drifted from 10 to 16 to 17 tools without anyone noticing.

What it checks:

1. every ``@mcp.tool()`` in ``server.py`` is declared in ``mcp.tools``;
2. every declared tool still exists in ``server.py``;
3. ``layers.shells[name=mcp].tools`` equals the declared count.

Usage::

    python scripts/validate_mcp.py
    python scripts/validate_mcp.py --arch ARCHITECTURE.json \
        --server ../dsh-snapshot/server.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ``@mcp.tool()`` / ``@mcp.tool(name=...)`` followed by the handler.
TOOL_RE = re.compile(r"@mcp\.tool\([^)]*\)\s*\n(?:async\s+)?def\s+(\w+)")


def load_contract(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def declared_tools(contract: dict) -> list[str]:
    return [tool["name"] for tool in contract["mcp"]["tools"]]


def implemented_tools(server: Path) -> list[str]:
    return TOOL_RE.findall(server.read_text(encoding="utf-8"))


def declared_count(contract: dict) -> int | None:
    for shell in contract.get("layers", {}).get("shells", []):
        if shell.get("name") == "mcp":
            return shell.get("tools")
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", default=str(ROOT / "ARCHITECTURE.json"))
    parser.add_argument(
        "--server",
        default=str(ROOT.parent / "dsh-snapshot" / "server.py"),
        help="path to the MCP shell (default: sibling dsh-snapshot/server.py)",
    )
    args = parser.parse_args(argv)

    contract = load_contract(Path(args.arch))
    declared = declared_tools(contract)
    implemented = implemented_tools(Path(args.server))

    missing = [name for name in implemented if name not in declared]
    extra = [name for name in declared if name not in implemented]

    failed = False
    if missing:
        print("missing from the contract: " + ", ".join(missing), file=sys.stderr)
        failed = True
    if extra:
        print("declared but not implemented: " + ", ".join(extra), file=sys.stderr)
        failed = True

    count = declared_count(contract)
    if count is not None and count != len(declared):
        print(
            f"layers.shells[mcp].tools is {count}, mcp.tools has {len(declared)}",
            file=sys.stderr,
        )
        failed = True

    if failed:
        print(
            f"mcp tools mismatch: contract={len(declared)} server={len(implemented)}",
            file=sys.stderr,
        )
        return 1

    print(f"mcp tools: contract={len(declared)} server={len(implemented)}")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
