#!/usr/bin/env python3
"""Re-evaluate stored chain programs K times against the live backends.

Usage: reeval_winners.py <label>:<program_json_path> [...] [--k 5]

Each program's `code` field (a chain-spec JSON string) is re-run through
problems.chains.hover.full7.validate K times; per-eval fitness, mean, SD and
a normal-approx 95% CI are printed and appended to reeval_results.jsonl in
this directory. Requires HOVER_CHAIN_URL/HOVER_CHAIN_MODEL in the env (the
run's latest_*.env values).
"""

from datetime import UTC, datetime
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from problems.chains.hover.full7.validate import validate

HERE = Path(__file__).parent


def main():
    argv = sys.argv[1:]
    k = 5
    if "--k" in argv:
        i = argv.index("--k")
        k = int(argv[i + 1])
        del argv[i : i + 2]
    args = [a for a in argv if not a.startswith("--")]
    sink = HERE / "reeval_results.jsonl"
    for spec in args:
        label, path = spec.split(":", 1)
        prog = json.loads(Path(path).read_text())
        chain_spec = json.loads(prog["code"])
        stored = prog.get("metrics", {}).get("fitness")
        fits = []
        for i in range(k):
            m = validate(chain_spec)
            fits.append(m["fitness"])
            print(f"{label} eval {i + 1}/{k}: fitness={m['fitness']:.4f}", flush=True)
        a = np.asarray(fits)
        mean, sd = a.mean(), a.std(ddof=1)
        ci = 1.96 * sd / np.sqrt(len(a))
        rec = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "label": label,
            "program_id": prog["id"],
            "stored_fitness": stored,
            "k": k,
            "fitness": fits,
            "mean": mean,
            "sd": sd,
            "ci95": ci,
        }
        with open(sink, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(
            f"{label}: stored={stored:.4f} reeval mean={mean:.4f} sd={sd:.4f} "
            f"95%CI ±{ci:.4f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
