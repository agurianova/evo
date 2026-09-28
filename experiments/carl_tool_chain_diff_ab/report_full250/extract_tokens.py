"""Extract per-call mutation-LLM token usage from arm run.logs.

Usage: python extract_tokens.py <armA_run_dir> <armB_run_dir>
Writes mutation_tokens.json (aggregates) and mutation_tokens_per_call.json
(ordered per-call records) next to this script. Records reasoning tokens
(a subset of tokens_out) so non-reasoning vs reasoning models are comparable.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

CALL_RE = re.compile(r"\[LLM_CALL\] (\{.*\})\s*$")
MUTATION_STAGES = {"MutationAgent", "DiffMutationAgent"}


def per_call(run_dir: Path, first_ok: int | None = None) -> list[dict]:
    """Ordered mutation-LLM calls. If first_ok is set, stop after the first_ok-th
    ok=true call, keeping every retry logged up to (and including) it — the token
    cost of accepting that many mutants."""
    calls = []
    ok_calls = 0
    with (run_dir / "run.log").open(errors="replace") as fh:
        for raw in fh:
            for line in raw.split("\r"):
                m = CALL_RE.search(line)
                if not m:
                    continue
                rec = json.loads(m.group(1))
                if rec.get("stage") in MUTATION_STAGES:
                    calls.append(
                        {
                            "ok": rec["ok"],
                            "tokens_in": rec["tokens_in"],
                            "tokens_out": rec["tokens_out"],
                            "tokens_reasoning": rec.get("tokens_reasoning", 0),
                        }
                    )
                    if rec["ok"]:
                        ok_calls += 1
                        if first_ok is not None and ok_calls >= first_ok:
                            return calls
    return calls


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("arm_a")
    ap.add_argument("arm_b")
    ap.add_argument(
        "--first-ok",
        type=int,
        default=None,
        help="cap each arm at the first N accepted mutants (retries counted)",
    )
    args = ap.parse_args()
    arms = {"A": Path(args.arm_a), "B": Path(args.arm_b)}
    out_dir = Path(__file__).parent
    calls = {k: per_call(d, first_ok=args.first_ok) for k, d in arms.items()}
    agg = {
        k: {
            "calls": len(c),
            "ok": sum(1 for r in c if r["ok"]),
            "tokens_in": sum(r["tokens_in"] for r in c),
            "tokens_out": sum(r["tokens_out"] for r in c),
            "tokens_reasoning": sum(r["tokens_reasoning"] for r in c),
        }
        for k, c in calls.items()
    }
    (out_dir / "mutation_tokens.json").write_text(json.dumps(agg, indent=1))
    (out_dir / "mutation_tokens_per_call.json").write_text(json.dumps(calls))
    for k, a in agg.items():
        completed = [r["tokens_out"] for r in calls[k] if r["ok"] and r["tokens_out"]]
        mean_out = sum(completed) / len(completed) if completed else 0
        reason = a["tokens_out"] and a["tokens_reasoning"] / a["tokens_out"]
        print(
            f"arm {k}: {a['calls']} calls ({a['ok']} ok), in {a['tokens_in']:,}, "
            f"out {a['tokens_out']:,} (reasoning {a['tokens_reasoning']:,} = {reason:.0%}), "
            f"mean out/completed {mean_out:,.0f}"
        )


if __name__ == "__main__":
    main()
