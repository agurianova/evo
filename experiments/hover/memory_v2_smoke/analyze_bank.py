#!/usr/bin/env python3
"""Summarize a seed card bank without treating v1 events as causal evidence."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gigaevo.memory.cards import Card, CardKind  # noqa: E402
from gigaevo.memory.write.admission import WriteLedgerRecord  # noqa: E402


def _load_cards(path: Path) -> list[Card]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("cards", {})
    values = rows.values() if isinstance(rows, dict) else rows
    return [Card.model_validate(value) for value in values]


def _load_write_ledger(path: Path | None) -> list[WriteLedgerRecord]:
    if path is None or not path.is_file():
        return []
    return [
        WriteLedgerRecord.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _event_kind(event) -> str:
    if event.founding:
        return "founding"
    if event.invalid:
        return "invalid"
    if event.unused:
        return "unused"
    return "direct"


def _card_row(card: Card) -> dict[str, object]:
    event_counts = Counter(_event_kind(event) for event in card.gain_events)
    valid_gains = [
        event.gain
        for event in card.gain_events
        if not event.invalid and not event.unused
    ]
    return {
        "card_id": card.id,
        "kind": card.kind.value,
        "fitness": card.fitness,
        "program_count": len(card.programs),
        "absorbed_id_count": len(card.absorbed_ids),
        "event_count": len(card.gain_events),
        "founding_events": event_counts["founding"],
        "direct_events": event_counts["direct"],
        "unused_events": event_counts["unused"],
        "invalid_events": event_counts["invalid"],
        "positive_valid_events": sum(gain > 0.0 for gain in valid_gains),
        "negative_valid_events": sum(gain < 0.0 for gain in valid_gains),
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _plot(
    path: Path,
    cards: list[Card],
    rows: list[dict[str, object]],
    ledger: list[WriteLedgerRecord],
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10), constrained_layout=True)
    fig.suptitle("HoVer seed memory bank", fontsize=16)

    kind_counts = Counter(card.kind.value for card in cards)
    axes[0, 0].bar(
        list(kind_counts),
        list(kind_counts.values()),
        color=["#26734d", "#3264a8"],
    )
    axes[0, 0].set_title("Active cards by kind")
    axes[0, 0].set_ylabel("cards")

    labels = [str(row["card_id"])[:10] for row in rows]
    bottoms = [0] * len(rows)
    event_palette = {
        "founding_events": "#6b7280",
        "direct_events": "#26734d",
        "unused_events": "#d6a336",
        "invalid_events": "#b54242",
    }
    for key, color in event_palette.items():
        values = [int(row[key]) for row in rows]
        axes[0, 1].bar(labels, values, bottom=bottoms, label=key[:-7], color=color)
        bottoms = [left + right for left, right in zip(bottoms, values)]
    axes[0, 1].set_title("Legacy event coverage by card")
    axes[0, 1].tick_params(axis="x", rotation=55)
    axes[0, 1].legend(frameon=False, ncols=2)

    for index, card in enumerate(cards):
        for event in card.gain_events:
            if event.invalid or event.unused:
                continue
            axes[1, 0].scatter(
                index,
                event.gain,
                marker="o" if event.founding else "s",
                color="#6b7280" if event.founding else "#26734d",
                s=38,
                alpha=0.85,
            )
    axes[1, 0].axhline(0.0, color="#111827", linewidth=0.8)
    axes[1, 0].set_xticks(range(len(labels)), labels, rotation=55)
    axes[1, 0].set_title("Legacy valid gains (descriptive only)")
    axes[1, 0].set_ylabel("stored gain")

    outcomes = Counter(record.outcome.value for record in ledger)
    if outcomes:
        names = list(outcomes)
        axes[1, 1].bar(names, [outcomes[name] for name in names], color="#7a5195")
        axes[1, 1].tick_params(axis="x", rotation=40)
        axes[1, 1].set_title("V1 write-ledger lifecycle")
        axes[1, 1].set_ylabel("records")
    else:
        axes[1, 1].text(0.5, 0.5, "No write ledger", ha="center", va="center")
        axes[1, 1].set_axis_off()

    fig.savefig(path, dpi=170)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cards", type=Path, required=True)
    parser.add_argument("--write-ledger", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    cards = _load_cards(args.cards)
    if not cards:
        raise ValueError("card bank is empty")
    ledger = _load_write_ledger(args.write_ledger)
    rows = [_card_row(card) for card in cards]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(args.output_dir / "cards.csv", rows)

    kind_counts = Counter(card.kind.value for card in cards)
    outcome_counts = Counter(record.outcome.value for record in ledger)
    summary = {
        "card_count": len(cards),
        "task_keys": sorted({card.task_key for card in cards}),
        "kind_counts": dict(sorted(kind_counts.items())),
        "cards_with_events": sum(bool(card.gain_events) for card in cards),
        "event_count": sum(len(card.gain_events) for card in cards),
        "absorbed_id_count": sum(len(card.absorbed_ids) for card in cards),
        "program_exemplar_fitness": sorted(
            card.fitness
            for card in cards
            if card.kind is CardKind.PROGRAM and card.fitness is not None
        ),
        "write_ledger_records": len(ledger),
        "write_outcomes": dict(sorted(outcome_counts.items())),
        "v2_training_eligible": False,
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = [
        "# HoVer Seed Bank Analysis",
        "",
        f"- Active cards: **{len(cards)}** "
        f"({kind_counts.get('insight', 0)} insight, "
        f"{kind_counts.get('program', 0)} program)",
        f"- Cards carrying legacy events: **{summary['cards_with_events']}**; "
        f"stored events: **{summary['event_count']}**",
        f"- Consolidated aliases represented by survivors: "
        f"**{summary['absorbed_id_count']}**",
        f"- V1 write-ledger records: **{len(ledger)}** "
        f"({', '.join(f'{key}={value}' for key, value in sorted(outcome_counts.items()))})",
        "",
        "The cards are valid v2 treatment candidates, but their mutable v1 gain "
        "events are descriptive only. The live run starts a fresh randomized v2 "
        "ledger; no seed event is admitted as causal training evidence.",
    ]
    (args.output_dir / "report.md").write_text(
        "\n".join(report) + "\n", encoding="utf-8"
    )
    _plot(args.output_dir / "bank_overview.png", cards, rows, ledger)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
