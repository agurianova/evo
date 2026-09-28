#!/usr/bin/env python3
"""NOVAUC closeout (prereg_novelty_auction_20260711.md): P1-P3 counterfactual
replay + S1/S2 fitness stats, computed with ONE code path for treatment and
control arms.

P1-P3: the NOVAUC logs' slate `bid` fields are the TAXED bids (the tax is
applied before logging, auction.py `_adjust_bids` -> floor -> gate). The
counterfactual removes the tax exactly: raw = bid * (1+use_count)^{+power},
use_count being the logged per-row value the tax consumed. Winner among the
selected set mirrors TopThetaBudgeter.cap: sorted by (-theta, card_id).
Sanity: recomputing decisions from the taxed bids as-is must reproduce the
logged `selected` flags (0 mismatched rounds expected).

S1: per-mutation delta = child fitness - memory_base_metrics.fitness (the
parent fitness FROZEN at mutation time, stamped on the child's metadata);
with-card = memory_injected_idea_ids non-empty. Valid children only.
Control (MEM pair) recomputed with the same definition.
"""

from collections import Counter
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta as scipy_beta
from scipy.stats import mannwhitneyu

ROOT = Path(
    "/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
)
ARMS = {
    "NOVAUC_R1": "outputs/hover-diff-memory-novelty-auction-20260711_115748/R1",
    "NOVAUC_R2": "outputs/hover-diff-memory-novelty-auction-20260711_115748/R2",
    "MEM_R1": "outputs/hover-diff-memory-baseline-20260710_041404/R1",
    "MEM_R2": "outputs/hover-diff-memory-baseline-20260710_041404/R2",
}
NOVELTY_POWER = 0.5
EV_FLOOR_QUANTILE = 0.765


def resolve_log(rel):
    logs = sorted((ROOT / rel).glob("evolution_*.log"))
    assert logs, f"no log under {rel}"
    return logs[0]


def parse_events(log_path, tag):
    events = []
    needle = f"[{tag}] "
    with open(log_path, errors="replace") as fh:
        for line in fh:
            i = line.find(needle)
            if i >= 0:
                try:
                    events.append(json.loads(line[i + len(needle) :]))
                except json.JSONDecodeError:
                    continue
    return events


def round_decision(slate, bids):
    """Eligibility + Sidak gate on given bids; winner per TopThetaBudgeter."""
    qf = float(np.quantile(bids, EV_FLOOR_QUANTILE))
    eligible = [b > 0.0 and b >= qf for b in bids]
    n_el = sum(eligible)
    bq = slate[0]["baseline_quantile"]
    gate_q = bq ** (1.0 / n_el) if n_el > 1 else bq
    gate_theta = float(
        scipy_beta.ppf(gate_q, slate[0]["baseline_a"], slate[0]["baseline_b"])
    )
    selected = [
        row for row, ok in zip(slate, eligible) if ok and row["theta"] > gate_theta
    ]
    if not selected:
        return set(), None
    winner = sorted(selected, key=lambda r: (-r["theta"], r["card_id"]))[0]
    return {r["card_id"] for r in selected}, winner["card_id"]


def replay(label, rel):
    slates = [
        ev["bids"]
        for ev in parse_events(resolve_log(rel), "MEMORY_AUCTION_RUN")
        if ev.get("bids")
    ]
    actual, counterfactual = Counter(), Counter()
    mismatched_rounds = 0
    for slate in slates:
        taxed = [r["bid"] if r["bid"] is not None else 0.0 for r in slate]
        sel, win = round_decision(slate, taxed)
        logged = {r["card_id"] for r in slate if r.get("selected")}
        if sel != logged:
            mismatched_rounds += 1
        if win:
            actual[win] += 1
        raw = [
            b * (1.0 + r.get("use_count", 0)) ** NOVELTY_POWER
            for b, r in zip(taxed, slate)
        ]
        _, cf_win = round_decision(slate, raw)
        if cf_win:
            counterfactual[cf_win] += 1
    return {
        "label": label,
        "rounds": len(slates),
        "sanity_mismatched_rounds": mismatched_rounds,
        "actual": actual,
        "counterfactual": counterfactual,
    }


def share(counter):
    total = sum(counter.values())
    if not total:
        return 0.0, "-", 0
    card, n = counter.most_common(1)[0]
    return n / total, card, total


def load_programs(rel):
    progs = {}
    for f in (ROOT / rel / "storage/chains_hover_full7/programs").glob("*.json"):
        d = json.loads(f.read_text())
        md = d.get("metadata", {})
        progs[d["id"]] = {
            "fitness": d.get("metrics", {}).get("fitness"),
            "valid": d.get("metrics", {}).get("is_valid") == 1.0,
            "base_metrics": md.get("memory_base_metrics"),
            "injected": md.get("memory_injected_idea_ids") or [],
        }
    return progs


def fitness_deltas(progs):
    """(with_deltas, without_deltas): valid children vs frozen base fitness."""
    with_d, without_d = [], []
    for p in progs.values():
        base = p["base_metrics"]
        if not p["valid"] or p["fitness"] is None or not base:
            continue
        if base.get("fitness") is None:
            continue
        delta = p["fitness"] - base["fitness"]
        (with_d if p["injected"] else without_d).append(delta)
    return with_d, without_d


def stats(xs):
    if not xs:
        return "n=0"
    a = np.asarray(xs)
    return f"n={len(a)} mean={a.mean():+.4f} sd={a.std(ddof=1):.4f} median={np.median(a):+.4f}"


def main():
    print("=== P1-P3: counterfactual replay (tax removed, power=0) ===")
    p1_ok, p2_ok, p3_ok = [], [], []
    for label in ("NOVAUC_R1", "NOVAUC_R2"):
        r = replay(label, ARMS[label])
        a_share, a_card, a_total = share(r["actual"])
        c_share, c_card, c_total = share(r["counterfactual"])
        rel_drop = (c_share - a_share) / c_share if c_share else 0.0
        vol_ratio = a_total / c_total if c_total else float("nan")
        print(
            f"\n{label}: rounds={r['rounds']} sanity_mismatch={r['sanity_mismatched_rounds']}"
        )
        print(
            f"  actual        : wins={a_total} distinct={len(r['actual'])} top={a_card[:40]} share={a_share:.1%}"
        )
        print(
            f"  counterfactual: wins={c_total} distinct={len(r['counterfactual'])} top={c_card[:40]} share={c_share:.1%}"
        )
        print(
            f"  P1 rel share drop={rel_drop:+.1%} (cf share {'>' if c_share > 0.12 else '<='}12%)"
        )
        print(
            f"  P2 volume ratio={vol_ratio:.3f}   P3 distinct {len(r['actual'])} vs {len(r['counterfactual'])}"
        )
        p1_ok.append(a_share < c_share if c_share > 0.12 else None)
        p2_ok.append(abs(vol_ratio - 1.0) <= 0.10)
        p3_ok.append(len(r["actual"]) >= len(r["counterfactual"]))
    print(
        f"\nP1 lower-where-applicable: {p1_ok}  P2 within ±10%: {p2_ok}  P3 coverage>=cf: {p3_ok}"
    )

    print("\n=== S1/S2: fitness (same code path both arms) ===")
    pooled = {}
    for arm in ("NOVAUC", "MEM"):
        w_all, wo_all = [], []
        for rep in ("R1", "R2"):
            label = f"{arm}_{rep}"
            progs = load_programs(ARMS[label])
            w, wo = fitness_deltas(progs)
            w_all += w
            wo_all += wo
            fits = [
                p["fitness"]
                for p in progs.values()
                if p["valid"] and p["fitness"] is not None
            ]
            print(f"{label}: S2 valid-pop {stats(fits)}")
        pooled[arm] = (w_all, wo_all)
        print(f"{arm} pooled: with-card {stats(w_all)}")
        print(f"{arm} pooled: without   {stats(wo_all)}")
    u = mannwhitneyu(pooled["NOVAUC"][0], pooled["MEM"][0], alternative="two-sided")
    print(
        f"\nS1 MW (NOVAUC with-card vs MEM with-card): U={u.statistic:.0f} p={u.pvalue:.4f}"
    )
    uw = mannwhitneyu(pooled["NOVAUC"][0], pooled["NOVAUC"][1], alternative="two-sided")
    print(
        f"   MW (NOVAUC with vs without, within-arm): U={uw.statistic:.0f} p={uw.pvalue:.4f}"
    )


if __name__ == "__main__":
    main()
