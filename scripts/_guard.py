"""Rule-4 guard helpers shared by the two breaker scripts.

State lives in ``.guard/`` at the repository root (override with
``--state-dir`` or ``DSH_GUARD_DIR``). Nothing here talks to a network or a
database: the guards only count consecutive negative results.
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import sys
from typing import Any

DEFAULT_STATE_DIR = ".guard"
STATE_VERSION = 1


def ensure_utf8_stdout() -> None:
    """Force UTF-8 on stdout.

    The breaker banners are Chinese. A caller that captures this process with a
    non-UTF-8 locale would otherwise fail to decode the output.
    """
    stream = getattr(sys, "stdout", None)
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):  # pragma: no cover - exotic consoles
            pass


def now() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def state_dir(override: str | None = None) -> pathlib.Path:
    raw = override or os.environ.get("DSH_GUARD_DIR") or DEFAULT_STATE_DIR
    path = pathlib.Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_state(name: str, base: pathlib.Path) -> dict[str, Any]:
    path = base / f"{name}.json"
    if not path.exists():
        return {"version": STATE_VERSION}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"version": STATE_VERSION}
    if not isinstance(data, dict):
        return {"version": STATE_VERSION}
    data.setdefault("version", STATE_VERSION)
    return data


def save_state(name: str, base: pathlib.Path, data: dict[str, Any]) -> pathlib.Path:
    path = base / f"{name}.json"
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def banner(title: str, lines: list[str]) -> str:
    width = max(len(title), *(len(line) for line in lines)) + 2
    top = "=" * width
    body = "\n".join(f" {line}" for line in lines)
    return f"\n{top}\n {title}\n{top}\n{body}\n{top}"
