"""Build order-free Pareto data for one mutator model from storage + per-call tokens.

Ordering uses `created_at` (finest wall-clock creation timestamp) — NOT
atomic_counter (non-monotone here) and NOT the derived `iteration` field. Every
non-seed child, sorted by created_at, is the k-th accepted mutation call, so the
cost up to (and including) that child's creation = sum of the first k ok-call
costs, in run.log call order. Seeds consume no call ($0).

Validity is a THREE-way split: valid (fitness > -1), penalty (fitness <= -1,
i.e. malformed-JSON / validator fail), in-flight (fitness None, not yet scored).
validity_rate = valid / completed where completed = valid + penalty (in-flight
excluded from the denominator).

Emits pareto_data_<model>.json consumed by make_pareto.py. Qwen drops in by
re-running with its run dirs, per-call file, test_metrics, and lineage ids.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path
import sys

HERE = Path(__file__).parent
PRICES = {"gemini": (1.50e-6, 9.00e-6), "qwen": (0.1495e-6, 1.495e-6)}


def ok_costs(per_call, arm, pin, pout):
    return [
        r["tokens_in"] * pin + r["tokens_out"] * pout for r in per_call[arm] if r["ok"]
    ]


def cost_at_rank(oc, rank):
    """Cumulative ok-call spend through the rank-th created child (1-indexed).
    rank 0 (seed / synthetic root) => $0."""
    return sum(oc[:rank])


def load_children(run_dir):
    """Non-seed children sorted by created_at, 1-indexed chrono rank attached."""
    ch = []
    for f in glob.glob(f"{run_dir}/storage/*/programs/*.json"):
        d = json.load(open(f))
        if (d.get("metadata") or {}).get("source") == "initial_program":
            continue
        ch.append(d)
    ch.sort(key=lambda d: d.get("created_at", ""))
    return ch


def arm_data(model, arm, run_dir, per_call, test_specs):
    pin, pout = PRICES[model]
    oc = ok_costs(per_call, arm, pin, pout)
    children = load_children(run_dir)
    rank_of = {d["id"]: i + 1 for i, d in enumerate(children)}
    rank_of_short = {d["id"][:8]: i + 1 for i, d in enumerate(children)}

    total = sum(r["tokens_in"] * pin + r["tokens_out"] * pout for r in per_call[arm])
    reas_cost = sum(r.get("tokens_reasoning", 0) * pout for r in per_call[arm])
    out_tok = sum(r["tokens_out"] for r in per_call[arm])
    reas_tok = sum(r.get("tokens_reasoning", 0) for r in per_call[arm])

    n_valid = n_penalty = n_inflight = 0
    win = None  # (fitness, rank)
    traj, best = [], -1e9
    for i, d in enumerate(children):
        fit = (d.get("metrics") or {}).get("fitness")
        if fit is None:
            n_inflight += 1
            continue
        if fit <= -1:
            n_penalty += 1
            continue
        n_valid += 1
        rank = i + 1
        best = max(best, fit)
        traj.append([round(cost_at_rank(oc, rank), 4), round(best, 6)])
        if win is None or fit > win[0]:
            win = (fit, rank)

    # test points priced at cost-through-creation; ids absent from the child
    # rank map (synthetic base, seed gen1) => rank 0 => $0.
    test_points = [
        [
            round(
                cost_at_rank(
                    oc, rank_of_short.get(t["id"][:8], rank_of.get(t["id"], 0))
                ),
                4,
            ),
            t["test"],
            t["label"],
        ]
        for t in test_specs
    ]

    n_completed = n_valid + n_penalty
    return {
        "traj": traj,
        "cost_to_winner": round(cost_at_rank(oc, win[1]), 4),
        "winner_fit": round(win[0], 6),
        "winner_rank": win[1],
        "n_children": len(children),
        "total": round(total, 4),
        "n_valid": n_valid,
        "n_penalty": n_penalty,
        "n_inflight": n_inflight,
        "n_completed": n_completed,
        "validity_rate": round(n_valid / max(n_completed, 1), 4),
        "cost_per_valid": round(total / max(n_valid, 1), 4),
        "reasoning_cost": round(reas_cost, 4),
        "reasoning_tok_frac": round(reas_tok / max(out_tok, 1), 4),
        "test_points": test_points,  # [[cost, test_disc_pct, label], ...]
    }


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "gemini"
    cfg = json.loads(Path(sys.argv[2]).read_text())  # build spec
    per_call = json.loads((HERE / f"mutation_tokens_per_call_{model}.json").read_text())
    out = {}
    for arm in ("A", "B"):
        out[arm] = arm_data(
            model, arm, cfg[arm]["run_dir"], per_call, cfg[arm]["test_points"]
        )
    dst = HERE / f"pareto_data_{model}.json"
    dst.write_text(json.dumps(out, indent=2))
    print(f"wrote {dst}")
    for arm in ("A", "B"):
        d = out[arm]
        print(
            f"  arm {arm}: winner fit={d['winner_fit']:.4f}@rank{d['winner_rank']}/{d['n_children']} "
            f"cost-to-winner=${d['cost_to_winner']:.2f} total=${d['total']:.2f} "
            f"valid={d['n_valid']}/{d['n_completed']}={d['validity_rate'] * 100:.1f}% "
            f"(penalty {d['n_penalty']}, in-flight {d['n_inflight']}) "
            f"$/valid={d['cost_per_valid']:.3f}"
        )


if __name__ == "__main__":
    main()
