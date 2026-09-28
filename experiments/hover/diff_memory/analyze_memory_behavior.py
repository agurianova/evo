#!/usr/bin/env python3
"""Analyze memory read-stack behavior from MEMORY_READ_SELECTION / MEMORY_AUCTION_RUN
telemetry in run logs, plus bank state. Prints a per-run report and emits a JSON
summary with expectation verdicts (used by the run-end watchdog).

Usage: analyze_memory_behavior.py <label>:<log>:<bank_dir> [<label>:<log>:<bank_dir> ...]
"""

from collections import Counter
import json
from pathlib import Path
import sys

SELECTION_TAG = "[MEMORY_READ_SELECTION] "
AUCTION_TAG = "[MEMORY_AUCTION_RUN] "

EXPECT = {
    "auction_injection_fraction_band": (0.30, 0.40),
    "auction_injection_fraction_hard": (0.10, 0.70),
    "max_card_injections": 60,
    "min_effective_events": 3.0,
}


def parse_events(log_path: Path):
    selections, auctions = [], []
    with open(log_path, errors="replace") as fh:
        for line in fh:
            for tag, sink in ((SELECTION_TAG, selections), (AUCTION_TAG, auctions)):
                idx = line.find(tag)
                if idx >= 0:
                    try:
                        sink.append(json.loads(line[idx + len(tag) :]))
                    except json.JSONDecodeError:
                        pass
    return selections, auctions


def load_cards(bank_dir: Path):
    path = bank_dir / "cards.json"
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    if isinstance(raw, dict):
        raw = raw.get("cards", raw)
    if isinstance(raw, dict):
        raw = list(raw.values())
    return raw if isinstance(raw, list) else []


def analyze_run(label: str, log_path: Path, bank_dir: Path):
    selections, auctions = parse_events(log_path)
    report, verdicts = [], {}

    n_sel = len(selections)
    empty_reasons = Counter(s.get("empty_reason") or "(injected)" for s in selections)
    injected = [s for s in selections if s.get("selected_ids")]
    with_candidates = [s for s in selections if s.get("candidate_ids")]

    lane = Counter()
    per_card = Counter()
    for s in injected:
        chosen = set(s["selected_ids"])
        for bid in s.get("slate", []):
            if bid["card_id"] in chosen:
                per_card[bid["card_id"]] += 1
                if bid.get("probe_selected"):
                    lane["probe"] += 1
                else:
                    lane[bid.get("selection_reason") or "auction"] += 1

    bids = [b for a in auctions for b in a.get("bids", [])]
    n_bids = len(bids)
    ev_floor_rej = sum(1 for b in bids if b.get("rejected_by_ev_floor"))
    no_card_rej = sum(1 for b in bids if b.get("rejected_by_no_card_gate"))
    support_kinds = Counter(b.get("support_kind") for b in bids)
    warm_posterior = sum(
        1 for b in bids if (b.get("posterior_a"), b.get("posterior_b")) != (1.0, 1.0)
    )
    half = len(auctions) // 2
    early_kinds = Counter(
        b.get("support_kind") for a in auctions[:half] for b in a.get("bids", [])
    )
    late_kinds = Counter(
        b.get("support_kind") for a in auctions[half:] for b in a.get("bids", [])
    )
    zombie_suspects = {
        b["card_id"]
        for b in bids
        if b.get("probe_eligible")
        and (b.get("support_n") or 0) >= EXPECT["min_effective_events"]
    }

    auction_inj = lane.get("auction", 0)
    probe_inj = sum(v for k, v in lane.items() if k != "auction")
    frac_of_candidates = auction_inj / len(with_candidates) if with_candidates else 0.0
    frac_of_all = auction_inj / n_sel if n_sel else 0.0

    cards = load_cards(bank_dir)
    card_types = Counter(c.get("kind") or "?" for c in cards)
    ledger_kinds = Counter()
    ledger = bank_dir / "write_ledger.jsonl"
    if ledger.exists():
        for line in ledger.read_text().splitlines():
            try:
                ledger_kinds[json.loads(line).get("outcome") or "?"] += 1
            except json.JSONDecodeError:
                pass
    nce_path = bank_dir / "no_card_evidence.json"
    nce_summary = {}
    if nce_path.exists():
        nce = json.loads(nce_path.read_text())
        obs = nce.get("observations", []) if isinstance(nce, dict) else []
        contexts = Counter(
            ":".join([o["context_key"]["kind"], *o["context_key"]["parts"]])
            for o in obs
            if isinstance(o.get("context_key"), dict)
        )
        nce_summary = {
            "observations": len(obs),
            "contexts": len(contexts),
            "invalid": sum(1 for o in obs if o.get("invalid")),
        }

    report.append(f"=== {label} ===")
    report.append(
        f"selection events: {n_sel}  (injected: {len(injected)}, with candidates: {len(with_candidates)})"
    )
    report.append(f"empty reasons: {dict(empty_reasons.most_common())}")
    report.append(f"injection lanes: {dict(lane.most_common())}")
    report.append(
        f"auction-lane injection fraction: {frac_of_candidates:.2%} of candidate events, "
        f"{frac_of_all:.2%} of all selection events (expert band 30-40% of eligible)"
    )
    report.append(f"probe-lane injections: {probe_inj}")
    report.append(f"top injected cards: {per_card.most_common(8)}")
    report.append(
        f"bids: {n_bids}  ev_floor rejections: {ev_floor_rej} ({ev_floor_rej / n_bids:.1%})  "
        f"no_card_gate rejections: {no_card_rej}"
        if n_bids
        else "bids: 0"
    )
    report.append(f"support kinds (all bids): {dict(support_kinds.most_common())}")
    report.append(f"support kinds early half: {dict(early_kinds.most_common())}")
    report.append(f"support kinds late half:  {dict(late_kinds.most_common())}")
    report.append(f"bids with posterior moved off (1,1): {warm_posterior}/{n_bids}")
    report.append(
        f"zombie suspects (probe_eligible with support_n>=3): {sorted(zombie_suspects) or 'none'}"
    )
    report.append(f"bank: {len(cards)} cards {dict(card_types.most_common())}")
    report.append(f"write ledger ops: {dict(ledger_kinds.most_common())}")
    report.append(f"no-card evidence: {nce_summary or 'n/a'}")

    max_card, max_count = (per_card.most_common(1) or [("-", 0)])[0]
    lo, hi = EXPECT["auction_injection_fraction_hard"]
    verdicts["auction_fraction_in_hard_band"] = lo <= frac_of_candidates <= hi
    verdicts["auction_fraction_of_candidates"] = round(frac_of_candidates, 4)
    verdicts["no_card_dominates"] = max_count <= EXPECT["max_card_injections"]
    verdicts["max_card"] = {"card_id": max_card, "count": max_count}
    verdicts["probe_lane_active"] = probe_inj > 0
    verdicts["reputation_learned"] = (
        any(k not in (None, "", "cold_prior") for k in late_kinds) or warm_posterior > 0
    )
    verdicts["no_zombies"] = not zombie_suspects
    verdicts["no_card_evidence_accumulating"] = bool(
        nce_summary.get("observations", 0) > 0
    )
    verdicts["cards_written"] = len(cards)
    return "\n".join(report), verdicts


def main():
    summary = {}
    for spec in sys.argv[1:]:
        label, log_path, bank_dir = spec.split(":", 2)
        text, verdicts = analyze_run(label, Path(log_path), Path(bank_dir))
        print(text)
        print()
        summary[label] = verdicts
    print("=== VERDICTS (JSON) ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
