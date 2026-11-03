#!/usr/bin/env python
"""Record an evaluation metric and apply the rule-4 circuit breaker.

.dsh_rules 规则 4：同一个指标连续两次未提升，必须停下来讨论，不得继续调参。

退出码：

    0  本次有提升（未提升计数清零）
    2  连续未提升达到阈值 —— 熔断，必须向人类汇报

Usage::

    python scripts/record_eval_metric.py --name Recall@10 --value 0.5885
    python scripts/record_eval_metric.py --name Loss --value 0.42 --direction min

State: ``.guard/metrics.json``
"""

from __future__ import annotations

import argparse
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

import _guard  # noqa: E402

EXIT_OK = 0
EXIT_BREAKER = 2
HISTORY_LIMIT = 50


def main(argv: list[str] | None = None) -> int:
    _guard.ensure_utf8_stdout()
    parser = argparse.ArgumentParser(description="rule-4 metric tracker")
    parser.add_argument("--name", required=True, help="metric name, e.g. Recall@10")
    parser.add_argument("--value", required=True, type=float)
    parser.add_argument(
        "--direction",
        choices=("max", "min"),
        default="max",
        help="max: higher is better (default); min: lower is better",
    )
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--state-dir", default=None)
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args(argv)

    base = _guard.state_dir(args.state_dir)
    state = _guard.load_state("metrics", base)
    metrics = state.setdefault("metrics", {})
    record = metrics.setdefault(
        args.name, {"history": [], "best": None, "non_improvements": 0}
    )

    if args.reset:
        metrics.pop(args.name, None)
        _guard.save_state("metrics", base, state)
        print(f"guard: metric {args.name!r} cleared")
        return EXIT_OK

    history = list(record.get("history") or [])
    best = record.get("best")

    improved = best is None or (
        args.value > best if args.direction == "max" else args.value < best
    )
    streak = 0 if improved else int(record.get("non_improvements", 0)) + 1
    if improved:
        best = args.value

    history.append(args.value)
    record.update(
        {
            "history": history[-HISTORY_LIMIT:],
            "best": best,
            "non_improvements": streak,
            "direction": args.direction,
            "updated_at": _guard.now(),
        }
    )
    path = _guard.save_state("metrics", base, state)

    arrow = "↑" if improved else "→"
    print(
        f"{args.name} = {args.value:g}  (best={best:g}, direction={args.direction}) {arrow}"
    )
    print(f"state: {path}")

    if streak >= args.limit:
        print(
            _guard.banner(
                "RULE-4 BREAKER",
                [
                    f"{args.name} 连续 {streak} 次未提升。",
                    "",
                    "规则 4：同一方向连续两次负结果必须停下讨论。",
                    "不要继续调参掩盖问题；先向人类说明未提升的原因与下一步假设。",
                    "确认继续后，用 --reset 清空计数。",
                ],
            )
        )
        return EXIT_BREAKER

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
