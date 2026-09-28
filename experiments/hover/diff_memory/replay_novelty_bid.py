#!/usr/bin/env python3
"""Offline replay: novelty-discounted auction bid on logged slates, with the
TRUE BootstrapThompsonAuctioneer semantics — the EV reserve is the
ev_floor_quantile of the round's OWN (discounted) bids, so discounting a
dominant bid lowers the floor and redistributes wins instead of suppressing
them. Recomputes eligibility + Sidak no-card gate exactly from slate fields.

discounted_bid = bid * (1 + uses[card])**(-power); uses = prior replayed
auction-lane injections (proxy for runtime gain-event window; runs < 24h so
the window never expires here). p=0 sanity-checks against logged flags.
"""

from collections import Counter
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta as scipy_beta

ROOT = Path(
    "/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
)
RUNS = {
    "MEM_R1": "outputs/hover-diff-memory-baseline-20260710_041404/R1",
    "MEM_R2": "outputs/hover-diff-memory-baseline-20260710_041404/R2",
    "NOV_R1": "outputs/hover-diff-memory-novelty-20260711_023848/R1",
    "NOV_R2": "outputs/hover-diff-memory-novelty-20260711_023848/R2",
}
POWERS = [0.0, 0.25, 0.5, 1.0]
EV_FLOOR_QUANTILE = 0.765


def resolve_log(rel):
    logs = sorted((ROOT / rel).glob("evolution_*.log"))
    assert logs, f"no log under {rel}"
    return logs[0]


def parse(log_path):
    """MEMORY_AUCTION_RUN events: pristine pre-probe slates (the probe policy
    rewrites selected/floor flags on the READ_SELECTION copy)."""
    aucs = []
    tag = "[MEMORY_AUCTION_RUN] "
    with open(log_path, errors="replace") as fh:
        for line in fh:
            i = line.find(tag)
            if i >= 0:
                try:
                    ev = json.loads(line[i + len(tag) :])
                except json.JSONDecodeError:
                    continue
                if ev.get("bids"):
                    aucs.append(ev)
    return aucs


def auction_round(slate, uses, power):
    """Re-run one bootstrap-auction round with novelty-discounted bids."""
    disc = [
        b["bid"] * (1.0 + uses[b["card_id"]]) ** (-power)
        if b["bid"] is not None
        else 0.0
        for b in slate
    ]
    qf = float(np.quantile(disc, EV_FLOOR_QUANTILE))
    eligible = [d > 0.0 and d >= qf for d in disc]
    n_el = sum(eligible)
    bq = slate[0]["baseline_quantile"]
    base_a, base_b = slate[0]["baseline_a"], slate[0]["baseline_b"]
    gate_q = bq ** (1.0 / n_el) if n_el > 1 else bq
    gate_theta = float(scipy_beta.ppf(gate_q, base_a, base_b))
    winners = [
        (d, b["card_id"])
        for b, d, ok in zip(slate, disc, eligible)
        if ok and b["theta"] > gate_theta
    ]
    return winners


for label, rel in RUNS.items():
    sels = parse(resolve_log(rel))
    print(f"\n=== {label} ({len(sels)} decisions with slates) ===")
    print(
        f"{'power':>6} {'inj':>5} {'distinct':>8} {'max':>4} {'top1%':>6} {'sanity':>7}  top card"
    )
    for p in POWERS:
        uses = Counter()
        injected = Counter()
        mismatch = 0
        for s in sels:
            slate = s["bids"]
            winners = auction_round(slate, uses, p)
            if p == 0.0:
                logged = {b["card_id"] for b in slate if b.get("selected")}
                if {c for _, c in winners} != logged:
                    mismatch += 1
            if winners:
                winners.sort(key=lambda w: (-w[0], w[1]))
                top = winners[0][1]
                injected[top] += 1
                uses[top] += 1
        total = sum(injected.values())
        top_card, top_n = injected.most_common(1)[0] if injected else ("-", 0)
        sanity = f"{mismatch}mm" if p == 0.0 else ""
        print(
            f"{p:>6} {total:>5} {len(injected):>8} {top_n:>4} "
            f"{top_n / total * 100 if total else 0:>5.1f} {sanity:>7}  {top_card[:32]}"
        )
