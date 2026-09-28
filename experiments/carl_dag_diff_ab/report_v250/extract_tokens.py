"""Extract per-call mutation-LLM token usage from arm run.logs.

Usage: python extract_tokens.py <armA_run_dir> <armB_run_dir>
Writes mutation_tokens.json (aggregates) and mutation_tokens_per_call.json
(ordered per-call records) next to this script.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

CALL_RE = re.compile(r"\[LLM_CALL\] (\{.*\})\s*$")
MUTATION_STAGES = {"MutationAgent", "DiffMutationAgent"}


def per_call(run_dir: Path) -> list[dict]:
    calls = []
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
                        }
                    )
    return calls


def main() -> None:
    arms = {"A": Path(sys.argv[1]), "B": Path(sys.argv[2])}
    out_dir = Path(__file__).parent
    calls = {k: per_call(d) for k, d in arms.items()}
    agg = {
        k: {
            "calls": len(c),
            "tokens_in": sum(r["tokens_in"] for r in c),
            "tokens_out": sum(r["tokens_out"] for r in c),
        }
        for k, c in calls.items()
    }
    (out_dir / "mutation_tokens.json").write_text(json.dumps(agg, indent=1))
    (out_dir / "mutation_tokens_per_call.json").write_text(json.dumps(calls))
    for k, a in agg.items():
        completed = [r["tokens_out"] for r in calls[k] if r["ok"] and r["tokens_out"]]
        mean_out = sum(completed) / len(completed) if completed else 0
        print(
            f"arm {k}: {a['calls']} calls, in {a['tokens_in']:,}, out {a['tokens_out']:,}, "
            f"mean out/completed {mean_out:,.0f}"
        )


if __name__ == "__main__":
    main()
