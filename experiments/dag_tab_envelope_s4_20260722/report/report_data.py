"""Print every number the report quotes, straight from the reduced stats.

Keeping one printer means the prose and the figures cannot drift apart: any
number in report.tex has a line here that produced it.

Usage: python report_data.py <arm-slug> ...
"""

import json
from pathlib import Path
import sys

from make_figures import PRICES, cost_usd
import numpy as np

VIZ = Path(__file__).parent / "viz"


def summarise(arm):
    stats = json.loads((VIZ / f"{arm}_stats.json").read_text())
    programs = stats["programs"]
    valid = [p for p in programs if p["is_valid"] == 1.0]
    calls = stats["llm_calls"]
    ok = [c for c in calls if c["ok"]]
    test = json.loads((VIZ / f"{arm}_test.json").read_text())
    best = max(valid, key=lambda p: p["fitness"])
    model = ok[0]["model"] if ok else "?"

    print(f"===== {arm}  ({model}) =====")
    print(
        f"programs            {len(programs)} completed  valid {len(valid)}  invalid {len(programs) - len(valid)}  incomplete {stats['incomplete']}"
    )
    print(f"validity rate       {len(valid) / len(programs):.1%}")
    print(f"wall clock          {max(p['elapsed_s'] for p in programs) / 60:.1f} min")
    print(
        f"seed CV R2          {test['seed']['cv_r2']:.6f}   test R2 {test['seed']['test_r2']:.6f}  rmse {test['seed']['test_rmse']:.6f}"
    )
    print(
        f"best CV R2          {test['best']['cv_r2']:.6f}   test R2 {test['best']['test_r2']:.6f}  rmse {test['best']['test_rmse']:.6f}"
    )
    print(
        f"best id / gen       {best['id'][:12]}  gen {best['generation']}  nodes {best['node_count']:.0f}  depth {best['max_depth']:.0f}  feats {best['feature_count']:.0f}"
    )
    print(f"delta CV            {test['best']['cv_r2'] - test['seed']['cv_r2']:+.6f}")
    print(
        f"delta test          {test['best']['test_r2'] - test['seed']['test_r2']:+.6f}"
    )
    print(
        f"child CV mean/std   {np.mean([p['fitness'] for p in valid]):.6f} / {np.std([p['fitness'] for p in valid]):.6f}"
    )
    print(
        f"nodes mean/max      {np.mean([p['node_count'] for p in valid]):.2f} / {max(p['node_count'] for p in valid):.0f}"
    )
    print(
        f"depth mean/max      {np.mean([p['max_depth'] for p in valid]):.2f} / {max(p['max_depth'] for p in valid):.0f}"
    )
    print(f"depth>=2 share      {np.mean([p['max_depth'] >= 2 for p in valid]):.1%}")
    print(f"LLM calls           {len(calls)}  failed {len(calls) - len(ok)}")
    print(
        f"tokens in/out       {sum(c['tokens_in'] for c in ok):,} / {sum(c['tokens_out'] for c in ok):,}"
    )
    print(
        f"reasoning tokens    {sum(c['tokens_reasoning'] for c in ok):,}  ({np.mean([c['tokens_reasoning'] for c in ok]):.0f}/call)"
    )
    print(
        f"out tokens max/mean {max(c['tokens_out'] for c in ok)} / {np.mean([c['tokens_out'] for c in ok]):.0f}"
    )
    print(
        f"latency med/p95 s   {np.median([c['latency_ms'] for c in ok]) / 1000:.1f} / {np.percentile([c['latency_ms'] for c in ok], 95) / 1000:.1f}"
    )
    print(
        f"list-price spend    ${cost_usd(ok):.2f}  (in ${PRICES[model][0]}/M, out ${PRICES[model][1]}/M)"
    )
    print()


if __name__ == "__main__":
    for arm in sys.argv[1:]:
        summarise(arm)
