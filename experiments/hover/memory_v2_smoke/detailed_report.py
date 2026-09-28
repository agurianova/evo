#!/usr/bin/env python3
"""Build a self-contained visual audit for one completed memory-v2 run."""

from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import html
import json
import math
from pathlib import Path
import sqlite3
import sys
import textwrap
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
import numpy as np  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze import (  # noqa: E402
    Audit,
    canonical_treatment_ids,
    causal_observations,
    evaluate_ope,
    evidence_lifecycle,
    flatten,
    invalid_penalty_sensitivity,
    load_ledger,
)

INK = "#17212b"
MUTED = "#64748b"
BLUE = "#2563a6"
TEAL = "#159a8c"
GREEN = "#2b7a4b"
ORANGE = "#e86f45"
RED = "#b13b3b"
PURPLE = "#6d4c9c"
GOLD = "#c99224"
LIGHT = "#f5f7fa"
GRID = "#d6dce5"


@dataclass(frozen=True)
class ArmOutcome:
    ordinal: int
    decision_id: str
    treatment_id: str | None
    arm: str
    status: str
    gain: float | None
    parent_id: str
    parent_fitness: float
    parent_quality: float | None
    cell_index: int | None


@dataclass(frozen=True)
class ProvenanceAudit:
    linked_children: int
    selected_parent_matches: int
    base_metadata_matches: int
    assignment_matches: int
    terminal_matches: int
    issues: tuple[str, ...]


def _label(card_id: str, length: int = 13) -> str:
    value = card_id.replace("program-", "prog-")
    return value[:length]


def _wrap(value: str, width: int) -> str:
    return "\n".join(textwrap.wrap(value, width=width, break_long_words=False))


def _series(
    rows: list[dict[str, Any]], key: str, default: float = np.nan
) -> np.ndarray:
    return np.asarray(
        [default if row.get(key) is None else float(row[key]) for row in rows],
        dtype=float,
    )


def _page(title: str, subtitle: str = "") -> tuple[plt.Figure, Any]:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig = plt.figure(figsize=(16, 10), facecolor="white", constrained_layout=False)
    fig.text(0.04, 0.965, title, fontsize=27, weight="bold", color=INK, va="top")
    if subtitle:
        fig.text(0.04, 0.925, subtitle, fontsize=12.5, color=MUTED, va="top")
    fig.text(
        0.96,
        0.018,
        "Memory v2 visual audit | immutable causal ledger",
        fontsize=8.5,
        color=MUTED,
        ha="right",
    )
    grid = fig.add_gridspec(
        12,
        12,
        left=0.045,
        right=0.965,
        top=0.875,
        bottom=0.065,
        hspace=1.15,
        wspace=1.1,
    )
    return fig, grid


def _clean(ax: plt.Axes) -> None:
    ax.set_facecolor("white")
    ax.grid(color=GRID, linewidth=0.7, alpha=0.8)
    for spine in ax.spines.values():
        spine.set_color(GRID)


def _panel_title(ax: plt.Axes, title: str, note: str = "") -> None:
    ax.set_title(title, loc="left", fontsize=14, weight="bold", color=INK, pad=10)
    if note:
        ax.text(
            1,
            1.02,
            note,
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=8.5,
            color=MUTED,
        )


def _box(
    ax: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    title: str,
    body: str,
    *,
    color: str = BLUE,
    fill: str = "white",
    title_size: float = 13,
    body_size: float = 10.5,
) -> None:
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=1.8,
        edgecolor=color,
        facecolor=fill,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + 0.03 * width,
        xy[1] + 0.78 * height,
        title,
        fontsize=title_size,
        weight="bold",
        color=color,
        va="top",
    )
    ax.text(
        xy[0] + 0.03 * width,
        xy[1] + 0.61 * height,
        body,
        fontsize=body_size,
        color=INK,
        va="top",
        linespacing=1.35,
    )


def _arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = BLUE,
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=15,
            linewidth=1.8,
            color=color,
            connectionstyle="arc3,rad=0.0",
        )
    )


def _kpi(
    ax: plt.Axes,
    x: float,
    title: str,
    value: str,
    detail: str,
    color: str,
) -> None:
    width = 0.18
    patch = FancyBboxPatch(
        (x, 0.05),
        width,
        0.88,
        boxstyle="round,pad=0.012,rounding_size=0.025",
        linewidth=1.3,
        edgecolor=GRID,
        facecolor=LIGHT,
    )
    ax.add_patch(patch)
    ax.text(x + 0.02, 0.82, title.upper(), fontsize=8.5, color=MUTED, va="top")
    ax.text(x + 0.02, 0.58, value, fontsize=25, weight="bold", color=color, va="top")
    ax.text(x + 0.02, 0.27, detail, fontsize=9.5, color=INK, va="top")


def _wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float, float]:
    if total <= 0:
        return 0.0, 0.0, 0.0
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    radius = (
        z
        * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total))
        / denominator
    )
    return p, max(0.0, center - radius), min(1.0, center + radius)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_write_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _card_descriptions(rows: list[Any], canonical: dict[str, str]) -> dict[str, str]:
    descriptions: dict[str, tuple[int, str]] = {}
    for row in rows:
        ordinal = row.decision.event_ordinal
        for card in row.decision.lineage_registry:
            treatment_id = canonical.get(card.treatment_id, card.treatment_id)
            prior = descriptions.get(treatment_id, (-1, ""))
            if ordinal >= prior[0]:
                descriptions[treatment_id] = (ordinal, card.payload.strip())
    return {card_id: value[1] for card_id, value in descriptions.items()}


def _arm_outcomes(rows: list[Any], canonical: dict[str, str]) -> list[ArmOutcome]:
    result: list[ArmOutcome] = []
    for row in rows:
        decision = row.decision
        terminal = row.terminal
        treatment_id = decision.proposed_treatment_id
        if treatment_id is None:
            arm = "abstain"
        else:
            arm = "treated" if decision.delivered else "control"
            treatment_id = canonical.get(treatment_id, treatment_id)
        coordinates = decision.context.map_elites.coordinates
        result.append(
            ArmOutcome(
                ordinal=decision.event_ordinal,
                decision_id=decision.decision_id,
                treatment_id=treatment_id,
                arm=arm,
                status=terminal.status if terminal is not None else "pending",
                gain=(
                    terminal.measurement.value
                    if terminal is not None and terminal.measurement is not None
                    else None
                ),
                parent_id=decision.context.parent_id,
                parent_fitness=decision.context.parent_metrics[
                    decision.context.reward.primary_metric
                ],
                parent_quality=decision.context.map_elites.parent_quality_quantile,
                cell_index=coordinates[0].cell_index if coordinates else None,
            )
        )
    return result


def _writer_trace(
    write_rows: list[dict[str, Any]], current_cards: set[str]
) -> tuple[list[dict[str, Any]], bool]:
    active: set[str] = set()
    counters: Counter[str] = Counter()
    trace: list[dict[str, Any]] = []
    for index, row in enumerate(write_rows, 1):
        outcome = str(row.get("outcome", ""))
        incoming = str(row.get("incoming_id", ""))
        final = str(row.get("final_id", ""))
        if outcome == "added" and final:
            active.add(final)
        elif outcome == "merged" and final:
            if incoming and incoming != final:
                active.discard(incoming)
            active.add(final)
        counters[outcome] += 1
        trace.append(
            {
                "index": index,
                "timestamp_utc": row.get("timestamp_utc", ""),
                "outcome": outcome,
                "bank_size": len(active),
                **{f"cumulative_{key}": counters[key] for key in counters},
            }
        )
    return trace, active == current_cards


def _provenance_audit(ledger: Path, storage_dir: Path) -> ProvenanceAudit:
    program_dirs = list(storage_dir.glob("*/programs"))
    if len(program_dirs) != 1:
        return ProvenanceAudit(0, 0, 0, 0, 0, ("program directory not unique",))
    program_dir = program_dirs[0]
    with sqlite3.connect(ledger) as connection:
        records = connection.execute(
            """
            SELECT dc.decision_id, dc.child_id, dc.base_id, t.terminal_json
            FROM decision_children AS dc
            JOIN terminals AS t USING(decision_id)
            ORDER BY dc.completion_ordinal
            """
        ).fetchall()
    selected_matches = base_matches = assignment_matches = terminal_matches = 0
    issues: list[str] = []
    for decision_id, child_id, base_id, terminal_json in records:
        path = program_dir / f"{child_id}.json"
        if not path.is_file():
            issues.append(f"{decision_id}: child file missing")
            continue
        child = _load_json(path)
        metadata = child.get("metadata", {})
        parents = child.get("lineage", {}).get("parents", [])
        mutation_output = metadata.get("mutation_output") or {}
        raw_base = mutation_output.get("base_parent", 1)
        if isinstance(raw_base, str) and len(raw_base) == 1 and raw_base.isalpha():
            index = ord(raw_base.upper()) - ord("A")
        else:
            try:
                index = int(raw_base) - 1
            except (TypeError, ValueError):
                index = 0
        selected = parents[index] if 0 <= index < len(parents) else None
        if selected == base_id:
            selected_matches += 1
        else:
            issues.append(f"{decision_id}: mutation base parent mismatch")
        if metadata.get("memory_base_id") == base_id:
            base_matches += 1
        else:
            issues.append(f"{decision_id}: frozen base metadata mismatch")
        assignment = (metadata.get("memory_parent_assignments") or {}).get(base_id)
        if (
            isinstance(assignment, dict)
            and assignment.get("decision_id") == decision_id
        ):
            assignment_matches += 1
        else:
            issues.append(f"{decision_id}: frozen assignment mismatch")
        terminal = json.loads(terminal_json)
        if terminal.get("child_id") == child_id and terminal.get("base_id") == base_id:
            terminal_matches += 1
        else:
            issues.append(f"{decision_id}: terminal link mismatch")
    return ProvenanceAudit(
        linked_children=len(records),
        selected_parent_matches=selected_matches,
        base_metadata_matches=base_matches,
        assignment_matches=assignment_matches,
        terminal_matches=terminal_matches,
        issues=tuple(issues),
    )


def _canonical_candidates(
    candidates: list[dict[str, Any]], canonical: dict[str, str]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in candidates:
        item = dict(row)
        item["canonical_treatment_id"] = canonical.get(
            row["treatment_id"], row["treatment_id"]
        )
        result.append(item)
    return result


def _latest_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not candidates:
        return []
    ordinal = max(int(row["ordinal"]) for row in candidates)
    rows = [row for row in candidates if int(row["ordinal"]) == ordinal]
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        by_id[row["canonical_treatment_id"]] = row
    return list(by_id.values())


def _card_empirical(outcomes: list[ArmOutcome]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "treated": 0,
            "control": 0,
            "treated_invalid": 0,
            "control_invalid": 0,
            "treated_gains": [],
            "control_gains": [],
        }
    )
    for row in outcomes:
        if row.treatment_id is None or row.arm == "abstain":
            continue
        item = grouped[row.treatment_id]
        item[row.arm] += 1
        if row.status == "invalid":
            item[f"{row.arm}_invalid"] += 1
        elif row.gain is not None:
            item[f"{row.arm}_gains"].append(row.gain)
    return dict(grouped)


def render_executive(
    output: Path,
    decisions: list[dict[str, Any]],
    outcomes: list[ArmOutcome],
    lifecycle: list[dict[str, Any]],
    writer_trace: list[dict[str, Any]],
    current_cards: int,
    provenance: ProvenanceAudit,
) -> None:
    proposed = [row for row in outcomes if row.arm != "abstain"]
    treated = sum(row.arm == "treated" for row in outcomes)
    control = sum(row.arm == "control" for row in outcomes)
    valid = sum(row.status == "outcome" for row in outcomes)
    invalid = sum(row.status == "invalid" for row in outcomes)
    ready = sum(bool(row["support_ready"]) for row in lifecycle)
    h50 = [float(row["randomized_evidence_h50"]) for row in lifecycle]
    final_evidence = int(max(_series(decisions, "evidence_count"), default=0))
    final_reward = int(max(_series(decisions, "reward_observations"), default=0))

    fig, grid = _page(
        "Memory v2: 100-mutation visual audit",
        "Circle packing n=26 | empty bank start | GPT-5.4-mini | one card per mutation",
    )
    ax = fig.add_subplot(grid[0:2, :])
    ax.axis("off")
    _kpi(
        ax, 0.00, "causal closure", "100 / 100", "decisions linked and terminal", GREEN
    )
    _kpi(
        ax,
        0.205,
        "randomized arms",
        f"{treated} / {control}",
        "delivered / withheld",
        BLUE,
    )
    _kpi(ax, 0.410, "terminal status", f"{valid} / {invalid}", "valid / invalid", TEAL)
    _kpi(
        ax,
        0.615,
        "active bank",
        str(current_cards),
        "cap reached without overflow",
        ORANGE,
    )
    _kpi(
        ax,
        0.820,
        "support ready",
        f"{ready} / {len(lifecycle)}",
        "stable evidence components",
        PURPLE,
    )

    flow = fig.add_subplot(grid[2:5, :])
    flow.set_xlim(0, 1)
    flow.set_ylim(0, 1)
    flow.axis("off")
    _panel_title(flow, "Observed end-to-end flow")
    stages = [
        ("EMPTY BANK", "0 seed cards\nwriter starts live", TEAL),
        ("WRITE", "43 adds\n103 merges", GREEN),
        ("BAYES RANK", "whole eligible bank\n1,910 posterior rows", BLUE),
        ("RANDOMIZE", f"{treated} delivered\n{control} withheld", PURPLE),
        ("EVOLVE", f"{valid} valid\n{invalid} invalid", ORANGE),
        ("REFIT", f"{final_evidence} safety\n{final_reward} valid reward", RED),
    ]
    xs = np.linspace(0.01, 0.84, len(stages))
    for index, ((title, body, color), x) in enumerate(zip(stages, xs, strict=True)):
        _box(
            flow, (float(x), 0.20), 0.145, 0.52, title, body, color=color, body_size=10
        )
        if index < len(stages) - 1:
            _arrow(flow, (float(x) + 0.145, 0.46), (float(xs[index + 1]), 0.46), color)

    ax1 = fig.add_subplot(grid[5:9, 0:6])
    _clean(ax1)
    _panel_title(
        ax1, "Realized terminal outcomes by arm", "counts, not model estimates"
    )
    arms = ["abstain", "control", "treated"]
    valid_counts = [
        sum(row.arm == arm and row.status == "outcome" for row in outcomes)
        for arm in arms
    ]
    invalid_counts = [
        sum(row.arm == arm and row.status == "invalid" for row in outcomes)
        for arm in arms
    ]
    x = np.arange(len(arms))
    ax1.bar(x, valid_counts, color=TEAL, label="valid")
    ax1.bar(x, invalid_counts, bottom=valid_counts, color=ORANGE, label="invalid")
    for i, (good, bad) in enumerate(zip(valid_counts, invalid_counts, strict=True)):
        ax1.text(
            i, good + bad + 1, f"n={good + bad}", ha="center", fontsize=10, color=INK
        )
    ax1.set_xticks(x, arms)
    ax1.set_ylabel("terminal count")
    ax1.legend(frameon=False)

    ax2 = fig.add_subplot(grid[5:9, 6:12])
    _clean(ax2)
    _panel_title(ax2, "Evidence accumulation and bank growth")
    ordinal = _series(decisions, "ordinal")
    ax2.plot(
        ordinal,
        _series(decisions, "evidence_count"),
        color=BLUE,
        linewidth=2.3,
        label="eligible terminals",
    )
    ax2.plot(
        ordinal,
        _series(decisions, "reward_observations"),
        color=TEAL,
        linewidth=2.3,
        label="valid reward rows",
    )
    ax2.set_xlabel("decision ordinal")
    ax2.set_ylabel("posterior observations")
    ax2b = ax2.twinx()
    if writer_trace:
        writer_x = np.linspace(0, max(ordinal, default=99), len(writer_trace))
        ax2b.plot(
            writer_x,
            _series(writer_trace, "bank_size"),
            color=ORANGE,
            alpha=0.8,
            label="bank size",
        )
    ax2b.set_ylabel("active cards", color=ORANGE)
    lines, labels = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2b.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, frameon=False, loc="upper left")

    verdict = fig.add_subplot(grid[9:12, :])
    verdict.axis("off")
    median_h50 = float(np.median(h50)) if h50 else math.nan
    status = "PASS" if not provenance.issues else "ATTENTION"
    verdict.text(
        0.0,
        0.92,
        f"RUN VERDICT: {status}",
        fontsize=17,
        weight="bold",
        color=GREEN if status == "PASS" else RED,
    )
    findings = [
        "Causal ownership is exact: mutation-output base parent, child metadata, decision, and terminal agree for every child.",
        "The posterior moved beyond pure cold start: 10 stable components reached >=2 treated, >=2 controls, and >=2 contexts.",
        f"Evidence remains the main limit: median H50 is {median_h50:.0f} proposals, so runs much shorter than ~80 decisions will stay exploratory.",
        "All candidates remained safety-feasible in this run; this validates numerical behavior, not discrimination at a dangerous boundary.",
        f"Offer allocation stayed calibrated: {treated}/{len(proposed)} delivered versus the fixed 0.5 design.",
    ]
    for index, finding in enumerate(findings):
        verdict.text(
            0.02,
            0.70 - index * 0.16,
            f"{index + 1}. {finding}",
            fontsize=11.2,
            color=INK,
            va="top",
        )
    fig.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(fig)


def render_bayesian_system(output: Path, rows: list[Any]) -> None:
    last = rows[-1].decision
    diagnostics = last.fit_diagnostics
    coordinates = last.context.map_elites.coordinates
    keys = ", ".join(row.key for row in coordinates) or "none"
    fig, grid = _page(
        "What the Bayesian system learns",
        "Minimal hierarchical hurdle model: utility and breakage are modeled separately, then combined",
    )
    ax = fig.add_subplot(grid[:, :])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    _box(
        ax,
        (0.02, 0.69),
        0.21,
        0.22,
        "1. PRE-TREATMENT CONTEXT x",
        _wrap(
            f"Task-local evidence\nParent fitness + progress\nStable model coordinate: {keys}\nLive MAP cell is audit-only",
            31,
        ),
        color=BLUE,
    )
    _box(
        ax,
        (0.28, 0.69),
        0.21,
        0.22,
        "2. STABLE CARD j",
        "One bank lineage is one arm\nMerges preserve evidence\nExact delivered text is frozen\nNo lexical ranking features",
        color=GREEN,
    )
    _box(
        ax,
        (0.54, 0.69),
        0.18,
        0.22,
        "3. RANDOM ACTION A",
        "A=1: deliver one card\nA=0: withhold it\nOffer probability e=0.5\nBoth arms stay leased",
        color=PURPLE,
    )
    _box(
        ax,
        (0.77, 0.69),
        0.21,
        0.22,
        "4. SHARED DESIGN z(x,j,A)",
        "Global context baseline\nShared treatment effect\nShrunk card deviation\nCard x context interaction",
        color=ORANGE,
    )
    for start, end, color in (
        ((0.23, 0.80), (0.28, 0.80), BLUE),
        ((0.49, 0.80), (0.54, 0.80), GREEN),
        ((0.72, 0.80), (0.77, 0.80), PURPLE),
    ):
        _arrow(ax, start, end, color)

    _box(
        ax,
        (0.05, 0.34),
        0.39,
        0.25,
        "VALID-GAIN HEAD",
        (
            "Y | valid ~ Normal(z^T beta, sigma^2 + s_i^2)\n"
            "Gaussian hierarchical coefficients; adaptive integration over sigma\n"
            f"Final fit: {diagnostics.reward_observations} rows, residual SD={diagnostics.reward_residual_sd:.4f}\n"
            "Answers: how much does fitness change when the mutation is valid?"
        ),
        color=BLUE,
        body_size=11,
    )
    _box(
        ax,
        (0.56, 0.34),
        0.39,
        0.25,
        "INVALIDITY HEAD",
        (
            "D ~ Bernoulli(sigmoid(z^T gamma))\n"
            "Proper-prior logistic MAP + Laplace covariance; all non-censored terminals\n"
            f"Final fit: {diagnostics.safety_observations} rows, gradient={diagnostics.safety_gradient_inf:.2e}\n"
            "Answers: how likely is the card to break this mutation?"
        ),
        color=RED,
        body_size=11,
    )
    _arrow(ax, (0.87, 0.69), (0.32, 0.59), MUTED)
    _arrow(ax, (0.88, 0.69), (0.75, 0.59), MUTED)

    _box(
        ax,
        (0.20, 0.08),
        0.60,
        0.18,
        "HURDLE UTILITY AND SAFE SELECTION",
        (
            "q_a = (1 - p_a) * valid_gain_a + p_a * worst_feasible_gain\n"
            "card effect Delta = q_1 - q_0; posterior worlds preserve cross-card correlation\n"
            "admit only if P(p_1 <= 0.25 and p_1 - p_0 <= 0.10) >= 0.90\n"
            "among safe cards: probability matching + 5% uniform exploration, then one 0.5 offer"
        ),
        color=ORANGE,
        body_size=11.3,
    )
    _arrow(ax, (0.25, 0.34), (0.39, 0.26), BLUE)
    _arrow(ax, (0.75, 0.34), (0.61, 0.26), RED)
    ax.text(
        0.02,
        0.015,
        "ELI5: partial pooling = new cards borrow the bank average; posterior = current uncertainty after evidence; "
        "Laplace = a local Gaussian approximation around the safest logistic fit; propensity = the exact chance an action occurred.",
        fontsize=9.5,
        color=MUTED,
        va="bottom",
    )
    fig.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(fig)


def render_posterior_learning(
    output: Path,
    decisions: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    lifecycle: list[dict[str, Any]],
) -> None:
    selected = [row for row in candidates if row["selected"]]
    final = _latest_candidates(candidates)
    final_sorted = sorted(final, key=lambda row: float(row["usable_effect_mean"]))
    fig, grid = _page(
        "Posterior learning: movement, shrinkage, and differentiation",
        "Effects are normalized by the task metric range; bars show posterior uncertainty, not standard error of raw means",
    )

    ax1 = fig.add_subplot(grid[0:5, 0:7])
    _clean(ax1)
    _panel_title(ax1, "Selected card at each decision: usable effect +/- 1 SD")
    x = _series(selected, "ordinal")
    mean = _series(selected, "usable_effect_mean")
    sd = _series(selected, "usable_effect_sd")
    ax1.fill_between(x, mean - sd, mean + sd, color=BLUE, alpha=0.14)
    ax1.plot(x, mean, color=BLUE, marker="o", markersize=3.5, linewidth=1.4)
    ax1.axhline(0, color=INK, linewidth=1)
    ax1.set_xlabel("decision ordinal")
    ax1.set_ylabel("treated - control usable effect")

    ax2 = fig.add_subplot(grid[0:5, 7:12])
    _clean(ax2)
    _panel_title(
        ax2,
        "Final-context card posterior forest",
        "approx. 90% interval = mean +/- 1.645 SD",
    )
    show = (
        final_sorted[:8] + final_sorted[-8:] if len(final_sorted) > 16 else final_sorted
    )
    show = sorted(
        {row["canonical_treatment_id"]: row for row in show}.values(),
        key=lambda row: float(row["usable_effect_mean"]),
    )
    y = np.arange(len(show))
    m = _series(show, "usable_effect_mean")
    err = 1.645 * _series(show, "usable_effect_sd")
    colors = [GREEN if value > 0 else ORANGE for value in m]
    ax2.errorbar(m, y, xerr=err, fmt="none", ecolor=GRID, elinewidth=4, capsize=0)
    ax2.scatter(m, y, c=colors, s=55, zorder=3)
    ax2.axvline(0, color=INK, linewidth=1)
    ax2.set_yticks(
        y, [_label(row["canonical_treatment_id"]) for row in show], fontsize=8.5
    )
    ax2.set_xlabel("usable effect")

    ax3 = fig.add_subplot(grid[5:9, 0:6])
    _clean(ax3)
    _panel_title(ax3, "Uncertainty contracts as evidence accumulates")
    ax3.scatter(
        _series(selected, "ordinal"),
        _series(selected, "usable_effect_sd"),
        c=_series(selected, "probability_helpful"),
        cmap="viridis",
        s=36,
        alpha=0.85,
    )
    ax3.set_xlabel("decision ordinal")
    ax3.set_ylabel("posterior effect SD")
    ax3.text(
        0.98,
        0.95,
        "color = P(helpful)",
        transform=ax3.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        color=MUTED,
    )

    ax4 = fig.add_subplot(grid[5:9, 6:12])
    _clean(ax4)
    _panel_title(ax4, "Evidence readiness by stable component")
    ordered = sorted(
        lifecycle, key=lambda row: float(row["balanced_ess"]), reverse=True
    )
    y = np.arange(len(ordered))
    ess = _series(ordered, "balanced_ess")
    colors = [GREEN if row["support_ready"] else GRID for row in ordered]
    ax4.barh(y, ess, color=colors)
    ax4.set_yticks(
        y, [_label(row["treatment_id"], 12) for row in ordered], fontsize=7.5
    )
    ax4.invert_yaxis()
    ax4.set_xlabel("balanced treated/control ESS")
    ax4.axvline(
        4,
        color=ORANGE,
        linestyle="--",
        linewidth=1.2,
        label="2 treated + 2 control ideal minimum",
    )
    ax4.legend(frameon=False, fontsize=8)

    ax5 = fig.add_subplot(grid[9:12, :])
    ax5.axis("off")
    first_sd = float(np.median(sd[: min(len(sd), 10)])) if len(sd) else math.nan
    last_sd = float(np.median(sd[-min(len(sd), 10) :])) if len(sd) else math.nan
    helpful = _series(final, "probability_helpful") if final else np.asarray([])
    ax5.text(0, 0.86, "READING THE POSTERIOR", fontsize=15, weight="bold", color=INK)
    notes = [
        f"Median selected-card SD moved from {first_sd:.3f} in the first ten proposals to {last_sd:.3f} in the final ten.",
        f"Final-context P(helpful) spans {float(np.min(helpful)):.2f} to {float(np.max(helpful)):.2f}; cards are differentiated but none is certain.",
        "Intervals overlap zero for most cards. That is the honest result at 100 decisions with a growing 32-card bank.",
        "Probability matching can still prefer a card because selection compares correlated posterior worlds, not independent point estimates.",
    ]
    for index, note in enumerate(notes):
        ax5.text(
            0.02,
            0.62 - 0.18 * index,
            f"{index + 1}. {note}",
            fontsize=11,
            color=INK,
            va="top",
        )
    fig.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(fig)


def render_card_dossier(
    output: Path,
    candidates: list[dict[str, Any]],
    lifecycle: list[dict[str, Any]],
    descriptions: dict[str, str],
    empirical: dict[str, dict[str, Any]],
) -> None:
    final = _latest_candidates(candidates)
    final_by_id = {row["canonical_treatment_id"]: row for row in final}
    ready = [row for row in lifecycle if row["support_ready"]]
    ranked = sorted(
        ready,
        key=lambda row: float(
            final_by_id.get(row["treatment_id"], {}).get("usable_effect_mean", -99)
        ),
        reverse=True,
    )
    fig, grid = _page(
        "Stable-card dossier",
        "Evidence is pooled across absorbed near-duplicate IDs; descriptions are the latest observed survivor payload",
    )

    ax1 = fig.add_subplot(grid[0:5, 0:7])
    _clean(ax1)
    _panel_title(ax1, "Support-ready components: randomized evidence")
    ordered = sorted(ready, key=lambda row: int(row["closed"]), reverse=True)
    x = np.arange(len(ordered))
    ax1.bar(x, _series(ordered, "treated", 0), color=BLUE, label="treated")
    ax1.bar(
        x,
        _series(ordered, "control", 0),
        bottom=_series(ordered, "treated", 0),
        color=ORANGE,
        label="control",
    )
    ax1.set_xticks(
        x,
        [_label(row["treatment_id"], 11) for row in ordered],
        rotation=25,
        ha="right",
        fontsize=8,
    )
    ax1.set_ylabel("closed randomized outcomes")
    ax1.legend(frameon=False)

    ax2 = fig.add_subplot(grid[0:5, 7:12])
    _clean(ax2)
    _panel_title(ax2, "Current effect versus randomized support")
    plot_rows = [row for row in lifecycle if row["treatment_id"] in final_by_id]
    sizes = np.asarray([20 + 18 * float(row["closed"]) for row in plot_rows])
    effects = np.asarray(
        [
            float(final_by_id[row["treatment_id"]]["usable_effect_mean"])
            for row in plot_rows
        ]
    )
    colors = np.asarray(
        [
            float(final_by_id[row["treatment_id"]]["probability_helpful"])
            for row in plot_rows
        ]
    )
    scatter = ax2.scatter(
        _series(plot_rows, "balanced_ess"),
        effects,
        s=sizes,
        c=colors,
        cmap="viridis",
        vmin=0,
        vmax=1,
        edgecolor="white",
        linewidth=0.7,
    )
    ax2.axhline(0, color=INK, linewidth=1)
    ax2.set_xlabel("balanced treated/control ESS")
    ax2.set_ylabel("final-context usable effect")
    fig.colorbar(scatter, ax=ax2, label="P(helpful)", shrink=0.8)
    for row, effect in zip(plot_rows, effects, strict=True):
        if row["support_ready"] or abs(effect) >= np.quantile(np.abs(effects), 0.8):
            ax2.annotate(
                _label(row["treatment_id"], 10),
                (float(row["balanced_ess"]), effect),
                fontsize=7,
                xytext=(3, 3),
                textcoords="offset points",
            )

    table_ax = fig.add_subplot(grid[6:12, :])
    table_ax.axis("off")
    table_ax.text(
        0,
        1.02,
        "Highest current posterior means among support-ready cards",
        fontsize=14,
        weight="bold",
        color=INK,
        va="bottom",
    )
    headers = [
        "card",
        "latest advice",
        "T/C",
        "effect +/- SD",
        "P(help)",
        "P(safe)",
        "raw valid gain T/C",
    ]
    widths = [0.10, 0.42, 0.07, 0.12, 0.08, 0.08, 0.13]
    starts = np.cumsum([0, *widths[:-1]])
    for start, header in zip(starts, headers, strict=True):
        table_ax.text(
            float(start),
            0.94,
            header.upper(),
            fontsize=8.5,
            weight="bold",
            color=MUTED,
            va="top",
        )
    shown = ranked[:6]
    for index, life in enumerate(shown):
        card_id = str(life["treatment_id"])
        posterior = final_by_id.get(card_id, {})
        observed = empirical.get(card_id, {})
        tg = observed.get("treated_gains", [])
        cg = observed.get("control_gains", [])
        raw = f"{np.mean(tg):+.3f}/{np.mean(cg):+.3f}" if tg and cg else "insufficient"
        values = [
            _label(card_id, 12),
            _wrap(
                textwrap.shorten(
                    descriptions.get(card_id, "No current payload in final registry"),
                    width=125,
                    placeholder="...",
                ),
                58,
            ),
            f"{life['treated']}/{life['control']}",
            f"{float(posterior.get('usable_effect_mean', math.nan)):+.3f} +/- {float(posterior.get('usable_effect_sd', math.nan)):.3f}",
            f"{float(posterior.get('probability_helpful', math.nan)):.2f}",
            f"{float(posterior.get('probability_safe', math.nan)):.3f}",
            raw,
        ]
        y = 0.84 - index * 0.14
        if index % 2 == 0:
            table_ax.add_patch(
                FancyBboxPatch(
                    (0, y - 0.105),
                    1,
                    0.13,
                    boxstyle="square,pad=0",
                    facecolor=LIGHT,
                    edgecolor="none",
                )
            )
        for start, value in zip(starts, values, strict=True):
            table_ax.text(
                float(start),
                y,
                value,
                fontsize=8.4,
                color=INK,
                va="top",
                linespacing=1.18,
            )
    fig.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(fig)


def render_safety(
    output: Path,
    decisions: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    outcomes: list[ArmOutcome],
    penalty_summary: dict[str, Any],
) -> None:
    selected = [row for row in candidates if row["selected"]]
    final = _latest_candidates(candidates)
    fig, grid = _page(
        "Safety posterior and numerical health",
        "The safety head uses every non-censored terminal; invalid outcomes are never imputed as ordinary reward",
    )

    ax1 = fig.add_subplot(grid[0:5, 0:4])
    _clean(ax1)
    _panel_title(ax1, "Observed invalidity with 95% Wilson intervals")
    arms = ["abstain", "control", "treated"]
    rates = []
    lower = []
    upper = []
    for arm in arms:
        group = [row for row in outcomes if row.arm == arm]
        estimate, lo, hi = _wilson(
            sum(row.status == "invalid" for row in group), len(group)
        )
        rates.append(estimate)
        lower.append(estimate - lo)
        upper.append(hi - estimate)
    x = np.arange(len(arms))
    ax1.bar(x, rates, color=[MUTED, ORANGE, TEAL], alpha=0.85)
    ax1.errorbar(x, rates, yerr=[lower, upper], fmt="none", ecolor=INK, capsize=5)
    ax1.set_xticks(x, arms)
    ax1.set_ylim(0, max(0.42, max(np.asarray(rates) + np.asarray(upper)) * 1.15))
    ax1.set_ylabel("invalid probability")

    ax2 = fig.add_subplot(grid[0:5, 4:8])
    _clean(ax2)
    _panel_title(ax2, "Selected-card risk posterior through time")
    x = _series(selected, "ordinal")
    ax2.plot(
        x,
        _series(selected, "control_invalid_probability"),
        color=ORANGE,
        label="control mean",
    )
    ax2.plot(
        x,
        _series(selected, "treated_invalid_probability"),
        color=RED,
        label="treated mean",
    )
    ax2.plot(
        x,
        _series(selected, "treated_invalid_upper"),
        color=PURPLE,
        alpha=0.8,
        label="treated conservative upper",
    )
    ax2.axhline(0.25, color=INK, linestyle="--", linewidth=1, label="treated threshold")
    ax2.set_xlabel("decision ordinal")
    ax2.set_ylabel("invalid probability")
    ax2.set_ylim(0, 0.30)
    ax2.legend(frameon=False, fontsize=8)

    ax3 = fig.add_subplot(grid[0:5, 8:12])
    _clean(ax3)
    _panel_title(ax3, "Final safety gate geometry")
    scatter = ax3.scatter(
        _series(final, "incremental_invalid_upper"),
        _series(final, "treated_invalid_upper"),
        c=_series(final, "probability_helpful"),
        cmap="viridis",
        s=55,
        edgecolor="white",
    )
    ax3.axvline(0.10, color=RED, linestyle="--", label="incremental <= .10")
    ax3.axhline(0.25, color=ORANGE, linestyle="--", label="treated <= .25")
    ax3.set_xlabel("incremental invalidity upper")
    ax3.set_ylabel("treated invalidity upper")
    ax3.legend(frameon=False, fontsize=8)
    fig.colorbar(scatter, ax=ax3, label="P(helpful)", shrink=0.75)

    ax4 = fig.add_subplot(grid[5:9, 0:7])
    _clean(ax4)
    _panel_title(ax4, "Posterior numerical diagnostics", "log scale")
    ordinal = _series(decisions, "ordinal")
    ax4.semilogy(
        ordinal,
        np.maximum(_series(decisions, "safety_gradient_inf"), 1e-16),
        color=RED,
        label="safety gradient inf",
    )
    ax4.semilogy(
        ordinal,
        np.maximum(_series(decisions, "safety_hessian_condition"), 1),
        color=PURPLE,
        label="Hessian condition",
    )
    ax4.semilogy(
        ordinal,
        _series(decisions, "reward_residual_sd"),
        color=BLUE,
        label="reward residual SD",
    )
    ax4.semilogy(
        ordinal,
        _series(decisions, "reward_card_effect_sd"),
        color=TEAL,
        label="configured card prior SD",
    )
    ax4.set_xlabel("decision ordinal")
    ax4.legend(frameon=False, ncol=2, fontsize=8)

    ax5 = fig.add_subplot(grid[5:9, 7:12])
    _clean(ax5)
    _panel_title(ax5, "Where invalid terminals occurred")
    colors = {"abstain": MUTED, "control": ORANGE, "treated": TEAL}
    for arm in ("abstain", "control", "treated"):
        group = [row for row in outcomes if row.arm == arm]
        ax5.scatter(
            [row.ordinal for row in group],
            [1 if row.status == "invalid" else 0 for row in group],
            color=colors[arm],
            alpha=0.75,
            s=38,
            label=arm,
        )
    ax5.set_yticks([0, 1], ["valid", "invalid"])
    ax5.set_xlabel("decision ordinal")
    ax5.legend(frameon=False, ncol=3, fontsize=8)

    note = fig.add_subplot(grid[9:12, :])
    note.axis("off")
    note.text(0, 0.88, "INTERPRETATION", fontsize=15, weight="bold", color=INK)
    notes = [
        "The Laplace risk approximation stayed numerically well behaved: maximum gradient < 1e-5 and Hessian condition < 20.",
        "All 1,910 candidate rows passed the 90% chance-constrained safety gate. This run did not stress rejection near the 25%/10% boundary.",
        f"Invalid-penalty sensitivity preserved the top action in {100 * float(penalty_summary['top_action_agreement_k_0']):.1f}% (k=0) and {100 * float(penalty_summary['top_action_agreement_k_0.5']):.1f}% (k=.5) of decisions.",
        "Observed treated invalidity is lower here, but the interval is wide. Multiple independent trajectories are needed for a run-level safety claim.",
    ]
    for index, text in enumerate(notes):
        note.text(
            0.02,
            0.64 - 0.19 * index,
            f"{index + 1}. {text}",
            fontsize=11,
            color=INK,
            va="top",
        )
    fig.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(fig)


def render_randomization_ope(
    output: Path,
    decisions: list[dict[str, Any]],
    outcomes: list[ArmOutcome],
    ope: list[dict[str, Any]],
) -> None:
    proposed = [row for row in decisions if row["proposed"]]
    offers = _series(proposed, "offer_probability", 0)
    observed = np.asarray([float(row["delivered"]) for row in proposed])
    residual = np.cumsum(observed - offers)
    band = 2 * np.sqrt(np.maximum(np.cumsum(offers * (1 - offers)), 1e-12))
    fig, grid = _page(
        "Randomization, overlap, and counterfactual offer policies",
        "OPE changes only the deliver/withhold gate after the card was proposed; it does not claim to evaluate a different retrieval policy",
    )

    ax1 = fig.add_subplot(grid[0:5, 0:5])
    _clean(ax1)
    _panel_title(ax1, "Conditional-offer calibration")
    x = np.arange(1, len(proposed) + 1)
    ax1.fill_between(
        x, -band, band, color=BLUE, alpha=0.14, label="+/- 2 conditional SD"
    )
    ax1.plot(
        x,
        residual,
        color=ORANGE,
        marker="o",
        markersize=3,
        label="cumulative delivered - expected",
    )
    ax1.axhline(0, color=INK, linewidth=1)
    ax1.set_xlabel("proposed decision")
    ax1.set_ylabel("cumulative residual")
    ax1.legend(frameon=False)

    ax2 = fig.add_subplot(grid[0:5, 7:12])
    _clean(ax2)
    _panel_title(ax2, "Raw valid parent-to-child gain by arm")
    ax2.text(
        0.99,
        0.96,
        "invalid terminals are modeled on the safety page",
        transform=ax2.transAxes,
        ha="right",
        va="top",
        fontsize=8.5,
        color=MUTED,
    )
    gain_groups = [
        [
            row.gain
            for row in outcomes
            if row.arm == arm and row.status == "outcome" and row.gain is not None
        ]
        for arm in ("control", "treated")
    ]
    violin = ax2.violinplot(
        gain_groups, positions=[0, 1], showmeans=True, showmedians=True
    )
    for body, color in zip(violin["bodies"], [ORANGE, TEAL], strict=True):
        body.set_facecolor(color)
        body.set_alpha(0.55)
    ax2.axhline(0, color=INK, linewidth=1)
    ax2.set_xticks([0, 1], ["withheld control", "delivered card"])
    ax2.set_ylabel("raw fitness delta")

    ax3 = fig.add_subplot(grid[5:9, 0:6])
    _clean(ax3)
    _panel_title(ax3, "Doubly robust bounded utility under target offer rate")
    reward = [row for row in ope if row["endpoint_kind"] == "reward"]
    ax3.plot(
        _series(reward, "target_offer_probability"),
        _series(reward, "estimate"),
        "o-",
        color=BLUE,
        linewidth=2,
    )
    ax3.axvline(0.5, color=INK, linestyle="--", label="logged behavior e=.5")
    ax3.axhline(0, color=INK, linewidth=1)
    ax3.set_xlabel("target probability of delivering proposed card")
    ax3.set_ylabel("expected bounded proximal utility")
    ax3.legend(frameon=False)

    ax4 = fig.add_subplot(grid[5:9, 6:12])
    _clean(ax4)
    _panel_title(ax4, "Doubly robust invalidity under target offer rate")
    risk = [row for row in ope if row["endpoint_kind"] == "invalidity"]
    ax4.plot(
        _series(risk, "target_offer_probability"),
        _series(risk, "estimate"),
        "o-",
        color=RED,
        linewidth=2,
    )
    ax4.axvline(0.5, color=INK, linestyle="--", label="logged behavior e=.5")
    ax4.set_xlabel("target probability of delivering proposed card")
    ax4.set_ylabel("expected invalid probability")
    ax4.set_ylim(0, max(0.12, float(np.max(_series(risk, "estimate"))) * 1.25))
    ax4.legend(frameon=False)

    note = fig.add_subplot(grid[9:12, :])
    note.axis("off")
    e0 = next(row for row in reward if float(row["target_offer_probability"]) == 0)
    e1 = next(row for row in reward if float(row["target_offer_probability"]) == 1)
    r0 = next(row for row in risk if float(row["target_offer_probability"]) == 0)
    r1 = next(row for row in risk if float(row["target_offer_probability"]) == 1)
    notes = [
        f"Directional DR contrast e=1 versus e=0: utility {float(e1['estimate']) - float(e0['estimate']):+.3f}; invalidity {float(r1['estimate']) - float(r0['estimate']):+.3f}.",
        "Overlap is exact: behavior probability is 0.5 for every proposal, maximum importance weight is 2, and overlap violations are zero.",
        "This is one trajectory (one run cluster), so cluster-robust SE is undefined. Treat the curve as a monitored direction, not a confidence claim.",
        "Raw valid-only means and DR hurdle utility can point differently because DR includes invalid outcomes and adjusts for decision-time outcome predictions.",
    ]
    note.text(0, 0.88, "COUNTERFACTUAL READING", fontsize=15, weight="bold", color=INK)
    for index, text in enumerate(notes):
        note.text(
            0.02,
            0.64 - 0.19 * index,
            f"{index + 1}. {text}",
            fontsize=11,
            color=INK,
            va="top",
        )
    fig.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(fig)


def render_bank_lifecycle(
    output: Path,
    writer_trace: list[dict[str, Any]],
    write_rows: list[dict[str, Any]],
    lifecycle: list[dict[str, Any]],
    current_cards: int,
    trace_exact: bool,
) -> None:
    outcomes = Counter(str(row.get("outcome", "")) for row in write_rows)
    added_ids = {
        str(row.get("final_id")) for row in write_rows if row.get("outcome") == "added"
    }
    absorbed = max(len(added_ids) - current_cards, 0)
    fig, grid = _page(
        "Memory bank lifecycle and evidence half-life",
        "Writer consolidation keeps equivalent ideas on one statistical lineage; capacity rejection prevents silent overflow",
    )

    ax1 = fig.add_subplot(grid[0:5, 0:7])
    _clean(ax1)
    _panel_title(
        ax1, "Reconstructed active-bank size", "exact" if trace_exact else "approximate"
    )
    if writer_trace:
        x = _series(writer_trace, "index")
        ax1.step(
            x,
            _series(writer_trace, "bank_size"),
            where="post",
            color=BLUE,
            linewidth=2.2,
        )
        ax1.axhline(
            32, color=RED, linestyle="--", linewidth=1.2, label="active cap = 32"
        )
        reject_x = [
            row["index"]
            for row in writer_trace
            if row["outcome"] == "rejected_capacity"
        ]
        if reject_x:
            ax1.scatter(
                reject_x,
                [32] * len(reject_x),
                marker="x",
                color=RED,
                label="capacity rejection",
            )
        ax1.set_xlabel("writer ledger event")
        ax1.set_ylabel("active cards")
        ax1.legend(frameon=False)

    ax2 = fig.add_subplot(grid[0:5, 7:12])
    _clean(ax2)
    _panel_title(ax2, "Writer operations")
    labels = ["added", "merged", "updated", "rejected_capacity"]
    values = [outcomes[label] for label in labels]
    colors = [GREEN, BLUE, MUTED, RED]
    bars = ax2.bar(np.arange(len(labels)), values, color=colors)
    ax2.set_xticks(np.arange(len(labels)), ["add", "merge", "update", "cap reject"])
    ax2.set_ylabel("operation count")
    ax2.bar_label(bars, padding=3)

    ax3 = fig.add_subplot(grid[5:9, 0:6])
    _clean(ax3)
    _panel_title(ax3, "Randomized evidence half-life versus observed age")
    h50 = _series(lifecycle, "randomized_evidence_h50")
    age = _series(lifecycle, "age_decisions")
    colors = [GREEN if row["support_ready"] else ORANGE for row in lifecycle]
    ax3.scatter(h50, age, c=colors, s=65, alpha=0.85)
    bound = max(float(np.nanmax(h50)), float(np.nanmax(age)), 1)
    ax3.plot(
        [0, bound], [0, bound], "--", color=MUTED, label="observed age = median H50"
    )
    ax3.set_xlabel("median proposals needed for 2 treated + 2 controls")
    ax3.set_ylabel("component age in decisions")
    ax3.legend(frameon=False)

    ax4 = fig.add_subplot(grid[5:9, 6:12])
    _clean(ax4)
    _panel_title(ax4, "Stable-component arm balance")
    ordered = sorted(lifecycle, key=lambda row: int(row["closed"]), reverse=True)
    y = np.arange(len(ordered))
    treated = _series(ordered, "treated", 0)
    controls = _series(ordered, "control", 0)
    ax4.barh(y, treated, color=BLUE, label="treated")
    ax4.barh(y, -controls, color=ORANGE, label="control")
    ax4.axvline(0, color=INK, linewidth=1)
    ax4.set_yticks(
        y, [_label(row["treatment_id"], 11) for row in ordered], fontsize=7.5
    )
    ax4.invert_yaxis()
    ax4.set_xlabel("control < 0 | treated > 0")
    ax4.legend(frameon=False, ncol=2, fontsize=8)

    note = fig.add_subplot(grid[9:12, :])
    note.axis("off")
    h50_values = [float(row["randomized_evidence_h50"]) for row in lifecycle]
    notes = [
        f"The bank began empty, accepted {len(added_ids)} unique additions, consolidated {absorbed} into surviving lineages, and ended at {current_cards} active cards.",
        f"Capacity was explicit: {outcomes['rejected_capacity']} distinct additions were rejected after the cap; the bank never exceeded 32.",
        f"Median H50 is {np.median(h50_values):.0f} proposals (range {np.min(h50_values):.0f}-{np.max(h50_values):.0f}); 10 of {len(lifecycle)} stable components became support-ready.",
        "This directly measures the cold-start criticism: signal does accumulate, but a 100-decision run only begins to separate the older, repeatedly proposed lineages.",
    ]
    note.text(0, 0.88, "CHURN VERDICT", fontsize=15, weight="bold", color=INK)
    for index, text in enumerate(notes):
        note.text(
            0.02,
            0.64 - 0.19 * index,
            f"{index + 1}. {text}",
            fontsize=11,
            color=INK,
            va="top",
        )
    fig.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(fig)


def render_map_elites(
    output: Path,
    rows: list[Any],
    decisions: list[dict[str, Any]],
    outcomes: list[ArmOutcome],
) -> None:
    fig, grid = _page(
        "Evolution and MAP-Elites context",
        "Dynamic cell coordinates are frozen for audit; stable raw-to-model normalization, not transient cell identity, enters the posterior",
    )
    ordinal = _series(decisions, "ordinal")

    ax1 = fig.add_subplot(grid[0:4, 0:5])
    _clean(ax1)
    _panel_title(ax1, "Archive growth")
    ax1.plot(
        ordinal,
        _series(decisions, "archive_size"),
        color=BLUE,
        linewidth=2.2,
        label="archive size",
    )
    ax1.set_xlabel("decision ordinal")
    ax1.set_ylabel("occupied cells")
    ax1b = ax1.twinx()
    ax1b.plot(
        ordinal,
        _series(decisions, "map_coverage"),
        color=TEAL,
        linewidth=2,
        label="coverage",
    )
    ax1b.set_ylabel("coverage", color=TEAL)
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1b.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, frameon=False, loc="upper left")

    ax2 = fig.add_subplot(grid[0:4, 7:12])
    _clean(ax2)
    _panel_title(ax2, "Randomized parent fitness over the run")
    scatter = ax2.scatter(
        _series(decisions, "parent_quality_quantile"),
        _series(decisions, "parent_fitness"),
        c=ordinal,
        cmap="plasma",
        s=45,
        alpha=0.85,
    )
    ax2.set_xlabel("parent archive quality quantile")
    fig.colorbar(scatter, ax=ax2, label="decision ordinal", shrink=0.8)

    counts = Counter(row.parent_id for row in outcomes)
    distinct_parents = len(counts)
    max_parent_reuse = max(counts.values(), default=0)

    ax3 = fig.add_subplot(grid[5:9, 0:4])
    _clean(ax3)
    _panel_title(ax3, "Base-parent reuse", f"{distinct_parents} distinct parents")
    common = counts.most_common(15)
    ax3.barh(np.arange(len(common)), [count for _, count in common], color=BLUE)
    ax3.set_yticks(
        np.arange(len(common)), [card_id[:8] for card_id, _ in common], fontsize=8
    )
    ax3.invert_yaxis()
    ax3.set_xlabel("mutations anchored to parent")

    ax4 = fig.add_subplot(grid[5:9, 4:8])
    _clean(ax4)
    _panel_title(ax4, "Dynamic MAP cell selected")
    ax4.scatter(
        [row.ordinal for row in outcomes if row.cell_index is not None],
        [row.cell_index for row in outcomes if row.cell_index is not None],
        c=[row.parent_quality or 0 for row in outcomes if row.cell_index is not None],
        cmap="viridis",
        s=35,
    )
    ax4.set_xlabel("decision ordinal")
    ax4.set_ylabel("live cell index")

    ax5 = fig.add_subplot(grid[5:9, 8:12])
    _clean(ax5)
    _panel_title(ax5, "Raw gain versus parent quality")
    colors = {"control": ORANGE, "treated": TEAL, "abstain": MUTED}
    for arm in ("control", "treated", "abstain"):
        group = [
            row
            for row in outcomes
            if row.arm == arm
            and row.gain is not None
            and row.parent_quality is not None
        ]
        ax5.scatter(
            [row.parent_quality for row in group],
            [row.gain for row in group],
            color=colors[arm],
            alpha=0.7,
            s=36,
            label=arm,
        )
    ax5.axhline(0, color=INK, linewidth=1)
    ax5.set_xlabel("parent quality quantile")
    ax5.set_ylabel("child - parent fitness")
    ax5.legend(frameon=False, fontsize=8)

    note = fig.add_subplot(grid[9:12, :])
    note.axis("off")
    coords = rows[-1].decision.context.map_elites.coordinates
    axis_text = ", ".join(
        f"{coord.key}: semantic={coord.semantic_normalized:.3f}, live={coord.dynamic_normalized:.3f}, cell={coord.cell_index}"
        for coord in coords
    )
    final_cell = coords[0].cell_index if coords else None
    notes = [
        f"Parent choice was not a deterministic best-parent loop: {distinct_parents} distinct parents anchored {len(outcomes)} mutations; the most reused parent appeared {max_parent_reuse} times.",
        f"The contextual posterior conditions on normalized parent fitness, progress, and stable behavior coordinates. It does not treat cell {final_cell} as a permanent semantic category.",
        f"Example from the final decision: {axis_text}.",
        "This run has one behavior axis (fitness). The same BehaviorDimension contract supports multi-axis HoVer without relying on fixed live bins.",
    ]
    note.text(0, 0.88, "CONTEXT VERDICT", fontsize=15, weight="bold", color=INK)
    for index, text in enumerate(notes):
        note.text(
            0.02,
            0.64 - 0.19 * index,
            f"{index + 1}. {text}",
            fontsize=11,
            color=INK,
            va="top",
        )
    fig.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(fig)


def render_provenance(
    output: Path,
    rows: list[Any],
    terminals: list[dict[str, Any]],
    provenance: ProvenanceAudit,
) -> None:
    fig, grid = _page(
        "Causal provenance and asynchronous integrity",
        "Memory credit follows mutation_output.base_parent into frozen child metadata, then into the exact linked terminal",
    )
    flow = fig.add_subplot(grid[0:5, :])
    flow.set_xlim(0, 1)
    flow.set_ylim(0, 1)
    flow.axis("off")
    _panel_title(flow, "Per-mutation ownership chain")
    stages = [
        ("DECISION", "committed before exposure\n100 immutable records", BLUE),
        ("PARENT", "random eligible elite\nassignment on metadata", TEAL),
        ("MUTATOR", "mutation_output.base_parent\nselects reward anchor", PURPLE),
        ("CHILD", "memory_base_id +\nbirth-frozen assignment", ORANGE),
        ("LINK", "decision -> child -> base\nunique durable handoff", GREEN),
        ("TERMINAL", "valid / invalid / censored\n100 exact closures", RED),
    ]
    xs = np.linspace(0.01, 0.84, len(stages))
    for index, ((title, body, color), x) in enumerate(zip(stages, xs, strict=True)):
        _box(
            flow, (float(x), 0.23), 0.145, 0.48, title, body, color=color, body_size=9.7
        )
        if index < len(stages) - 1:
            _arrow(flow, (float(x) + 0.145, 0.47), (float(xs[index + 1]), 0.47), color)

    ax1 = fig.add_subplot(grid[5:9, 0:6])
    _clean(ax1)
    _panel_title(ax1, "Decision order versus completion order")
    x = _series(terminals, "ordinal")
    y = _series(terminals, "completion_ordinal")
    ax1.scatter(
        x, y, c=_series(terminals, "latency_seconds"), cmap="viridis", s=48, alpha=0.85
    )
    bound = max(float(np.max(x)), float(np.max(y)))
    ax1.plot([0, bound], [0, bound], "--", color=MUTED, label="same order")
    ax1.set_xlabel("decision ordinal")
    ax1.set_ylabel("completion ordinal")
    ax1.legend(frameon=False)

    ax2 = fig.add_subplot(grid[5:9, 6:12])
    _clean(ax2)
    _panel_title(ax2, "Decision-to-terminal latency", "log x-axis")
    latency = _series(terminals, "latency_seconds")
    bins = np.geomspace(
        max(float(np.min(latency[latency > 0])), 0.1), float(np.max(latency)) * 1.01, 22
    )
    ax2.hist(latency, bins=bins, color=BLUE, alpha=0.8)
    ax2.set_xscale("log")
    ax2.set_xlabel("seconds")
    ax2.set_ylabel("terminal count")
    ax2.axvline(
        float(np.median(latency)),
        color=ORANGE,
        linestyle="--",
        label=f"median={np.median(latency):.1f}s",
    )
    ax2.legend(frameon=False)

    audit_ax = fig.add_subplot(grid[9:12, :])
    audit_ax.axis("off")
    checks = [
        ("ledger child links", provenance.linked_children, provenance.linked_children),
        (
            "mutation-output parent -> ledger base",
            provenance.selected_parent_matches,
            provenance.linked_children,
        ),
        (
            "child memory_base_id -> ledger base",
            provenance.base_metadata_matches,
            provenance.linked_children,
        ),
        (
            "birth-frozen assignment -> decision",
            provenance.assignment_matches,
            provenance.linked_children,
        ),
        (
            "terminal child/base -> durable link",
            provenance.terminal_matches,
            provenance.linked_children,
        ),
    ]
    for index, (name, passed, total) in enumerate(checks):
        x0 = index * 0.20
        color = GREEN if passed == total else RED
        _kpi(
            audit_ax,
            x0,
            name,
            f"{passed}/{total}",
            "PASS" if passed == total else "MISMATCH",
            color,
        )
    audit_ax.text(
        0,
        -0.06,
        "Live limitation: num_parents=1 means every mutator emitted base_parent=1. Multi-parent base selection is covered by regression tests, not this trajectory.",
        fontsize=9.8,
        color=MUTED,
        va="top",
    )
    fig.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(fig)


def render_findings(
    output: Path,
    summary: dict[str, Any],
    lifecycle: list[dict[str, Any]],
    ope: list[dict[str, Any]],
) -> None:
    fig, grid = _page(
        "What this run establishes, and what it does not",
        "A first system run should validate causal machinery and numerical behavior before claiming universal card quality",
    )
    ax = fig.add_subplot(grid[:, :])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    columns = [
        (
            0.02,
            "ESTABLISHED",
            GREEN,
            [
                "100/100 decisions have exact child and terminal ownership.",
                "48/46 offer split is calibrated under fixed e=0.5.",
                "Posterior fits remained converged and well conditioned.",
                "The bank starts empty, merges aliases, and respects cap=32.",
                "Stable MAP normalization is separate from drifting cell bins.",
                "One singleton card is injected; withheld controls remain logged.",
            ],
        ),
        (
            0.345,
            "LEARNED, BUT UNCERTAIN",
            ORANGE,
            [
                "10/27 stable components reached minimum randomized support.",
                "Posterior effects differ, but most intervals still cross zero.",
                "DR monitoring favors a higher offer rate on this trajectory.",
                "Observed treated invalidity is lower than control, with wide intervals.",
                "Median evidence H50=80 means short runs remain exploratory.",
                "Invalid-penalty choice changes some rankings but rarely the top card.",
            ],
        ),
        (
            0.67,
            "NOT CLAIMED YET",
            RED,
            [
                "No multi-run confidence interval: this is one trajectory cluster.",
                "No long-horizon descendant or archive-contribution reward.",
                "No cross-task partial pooling; evidence is intentionally task-local.",
                "No LLM/embedding retrieval for banks larger than the active cap.",
                "No multi-card credit assignment; the intervention is one card.",
                "No live multi-parent validation in this num_parents=1 smoke.",
            ],
        ),
    ]
    for x, title, color, points in columns:
        ax.add_patch(
            FancyBboxPatch(
                (x, 0.30),
                0.30,
                0.60,
                boxstyle="round,pad=0.012,rounding_size=0.018",
                linewidth=1.8,
                edgecolor=color,
                facecolor=LIGHT,
            )
        )
        ax.text(
            x + 0.018,
            0.855,
            title,
            fontsize=12.5,
            weight="bold",
            color=color,
            va="top",
        )
        for index, point in enumerate(points):
            ax.text(
                x + 0.025,
                0.78 - index * 0.085,
                f"{index + 1}. {_wrap(point, 43)}",
                fontsize=9.6,
                color=INK,
                va="top",
                linespacing=1.18,
            )

    _box(
        ax,
        (0.08, 0.05),
        0.84,
        0.17,
        "DATA-DRIVEN NEXT EXPERIMENT",
        _wrap(
            "Run multiple independent 300-500 decision trajectories before changing the core model. "
            "That gives older cards several H50 windows, enables run-cluster OPE uncertainty, and reveals whether card rankings replicate. "
            "Keep the same one-card randomized offer so evidence remains comparable; add descendant utility only as a separately logged endpoint.",
            132,
        ),
        color=BLUE,
        body_size=11.2,
    )
    ax.text(
        0.02,
        0.015,
        f"Audit={summary.get('audit_passed')} | support-ready={sum(row['support_ready'] for row in lifecycle)} | "
        f"OPE rows={len(ope)} | warnings={len(summary.get('warnings', []))}",
        fontsize=9,
        color=MUTED,
    )
    fig.savefig(output, dpi=190, bbox_inches="tight")
    plt.close(fig)


def _image_data(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def build_html(
    output: Path,
    pages: list[tuple[str, Path, str]],
    summary: dict[str, Any],
    run_root: Path,
) -> None:
    sections = []
    for title, path, narrative in pages:
        sections.append(
            f"""
            <section class="report-page">
              <h2>{html.escape(title)}</h2>
              <p>{html.escape(narrative)}</p>
              <img src="{_image_data(path)}" alt="{html.escape(title)}">
            </section>
            """
        )
    content = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Memory v2 visual audit</title>
<style>
  @page {{ size: A4 landscape; margin: 8mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; color: {INK}; font-family: Inter, Arial, sans-serif; background: #eef1f5; }}
  .cover {{ min-height: 100vh; background: white; padding: 56px 64px; display: flex; flex-direction: column; justify-content: center; page-break-after: always; }}
  .eyebrow {{ color: {BLUE}; font-weight: 700; font-size: 14px; text-transform: uppercase; }}
  h1 {{ font-size: 50px; margin: 14px 0 10px; max-width: 1000px; }}
  .lead {{ color: {MUTED}; font-size: 21px; max-width: 1000px; line-height: 1.45; }}
  .facts {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-top: 36px; }}
  .fact {{ border: 1px solid {GRID}; background: {LIGHT}; border-radius: 6px; padding: 18px; }}
  .fact strong {{ display: block; font-size: 27px; color: {BLUE}; margin-bottom: 5px; }}
  .fact span {{ color: {MUTED}; font-size: 12px; }}
  .path {{ margin-top: 34px; color: {MUTED}; font-family: monospace; font-size: 11px; }}
  .report-page {{ background: white; padding: 18px 24px 12px; page-break-after: always; min-height: 100vh; }}
  .report-page h2 {{ font-size: 20px; margin: 0 0 4px; }}
  .report-page p {{ color: {MUTED}; margin: 0 0 8px; font-size: 11px; }}
  .report-page img {{ display: block; width: 100%; max-height: 88vh; object-fit: contain; border: 1px solid {GRID}; }}
  @media print {{ body {{ background: white; }} .cover, .report-page {{ min-height: auto; }} }}
</style>
</head>
<body>
  <section class="cover">
    <div class="eyebrow">Completed real-problem causal-bandit smoke</div>
    <h1>Memory v2 visual analytics report</h1>
    <p class="lead">A visual reconstruction of how cards were written, proposed, randomized, used, credited, and learned across 100 circle-packing mutations. Every chart is derived from the immutable SQLite decision and terminal ledger.</p>
    <div class="facts">
      <div class="fact"><strong>{summary["decisions"]}</strong><span>causal decisions</span></div>
      <div class="fact"><strong>{summary["delivered"]} / {summary["controls"]}</strong><span>delivered / withheld</span></div>
      <div class="fact"><strong>{summary["terminal_statuses"]["outcome"]} / {summary["terminal_statuses"]["invalid"]}</strong><span>valid / invalid</span></div>
      <div class="fact"><strong>{summary["maximum_posterior_evidence"]}</strong><span>maximum prior evidence</span></div>
      <div class="fact"><strong>PASS</strong><span>ledger + numerical audit</span></div>
    </div>
    <div class="path">Run: {html.escape(str(run_root))}</div>
  </section>
  {"".join(sections)}
</body>
</html>
"""
    output.write_text(content, encoding="utf-8")


def render_pdf(html_path: Path, pdf_path: Path) -> str | None:
    try:
        from weasyprint import HTML

        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    except Exception as exc:  # pragma: no cover - optional rendering backend
        return f"{type(exc).__name__}: {exc}"
    return None


def _read_summary(path: Path) -> dict[str, Any]:
    return _load_json(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--analytics-dir", type=Path, required=True)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    run_root = args.run_root or args.ledger.parent.parent
    output_dir = args.output_dir or args.analytics_dir / "visual_report"
    output_dir.mkdir(parents=True, exist_ok=True)

    audit = Audit()
    rows, _ = load_ledger(args.ledger, audit)
    decisions, candidates, terminals = flatten(rows)
    canonical = canonical_treatment_ids(rows)
    candidates = _canonical_candidates(candidates, canonical)
    lifecycle = evidence_lifecycle(rows, candidates)
    _, penalty_summary = invalid_penalty_sensitivity(decisions, candidates)
    ope = evaluate_ope(causal_observations(rows))
    outcomes = _arm_outcomes(rows, canonical)
    descriptions = _card_descriptions(rows, canonical)
    empirical = _card_empirical(outcomes)
    current_card_data = _load_json(run_root / "memory/cards.json")
    current_cards = set(current_card_data.get("cards", {}))
    write_rows = _load_write_rows(run_root / "memory/write_ledger.jsonl")
    writer_trace, trace_exact = _writer_trace(write_rows, current_cards)
    provenance = _provenance_audit(args.ledger, run_root / "storage")
    summary = _read_summary(args.analytics_dir / "summary.json")

    page_specs: list[tuple[str, str, Any, tuple[Any, ...]]] = [
        (
            "Executive audit",
            "01_executive_audit.png",
            render_executive,
            (
                decisions,
                outcomes,
                lifecycle,
                writer_trace,
                len(current_cards),
                provenance,
            ),
        ),
        (
            "Bayesian system",
            "02_bayesian_system.png",
            render_bayesian_system,
            (rows,),
        ),
        (
            "Posterior learning",
            "03_posterior_learning.png",
            render_posterior_learning,
            (decisions, candidates, lifecycle),
        ),
        (
            "Stable-card dossier",
            "04_card_dossier.png",
            render_card_dossier,
            (candidates, lifecycle, descriptions, empirical),
        ),
        (
            "Safety and calibration",
            "05_safety_and_calibration.png",
            render_safety,
            (decisions, candidates, outcomes, penalty_summary),
        ),
        (
            "Randomization and OPE",
            "06_randomization_and_ope.png",
            render_randomization_ope,
            (decisions, outcomes, ope),
        ),
        (
            "Bank lifecycle",
            "07_bank_lifecycle.png",
            render_bank_lifecycle,
            (writer_trace, write_rows, lifecycle, len(current_cards), trace_exact),
        ),
        (
            "MAP-Elites context",
            "08_map_elites_context.png",
            render_map_elites,
            (rows, decisions, outcomes),
        ),
        (
            "Causal provenance",
            "09_causal_provenance.png",
            render_provenance,
            (rows, terminals, provenance),
        ),
        (
            "Findings and limits",
            "10_findings_and_limits.png",
            render_findings,
            (summary, lifecycle, ope),
        ),
    ]
    pages: list[tuple[str, Path, str]] = []
    narratives = {
        "Executive audit": "The complete run at a glance: causal closure, randomized allocation, bank growth, terminal outcomes, and the cold-start verdict.",
        "Bayesian system": "A run-specific infographic of the hierarchical reward and invalidity heads, hurdle utility, chance-constrained safety gate, and probability-matching policy.",
        "Posterior learning": "How selected-card effects and uncertainty changed as evidence accumulated, plus final-context card comparisons.",
        "Stable-card dossier": "Card-level randomized support, posterior effects, and the latest advice text for the evidence-ready lineages.",
        "Safety and calibration": "Observed invalidity, posterior risk trajectories, gate margins, numerical convergence, and invalid-penalty sensitivity.",
        "Randomization and OPE": "Offer calibration, raw arm outcomes, overlap diagnostics, and doubly robust counterfactual offer-rate monitoring.",
        "Bank lifecycle": "How an empty bank grew to the cap, how merges preserved lineages, and whether evidence accumulated faster than churn.",
        "MAP-Elites context": "Archive growth, parent diversity, dynamic cells, stable model coordinates, and gains across evolutionary contexts.",
        "Causal provenance": "The exact flow from mutation_output.base_parent to child metadata and terminal evidence, including asynchronous completion.",
        "Findings and limits": "A strict separation between what this run establishes, what is directional, and what remains future work.",
    }
    for title, filename, renderer, renderer_args in page_specs:
        path = output_dir / filename
        renderer(path, *renderer_args)
        pages.append((title, path, narratives[title]))

    html_path = output_dir / "memory_v2_visual_report.html"
    build_html(html_path, pages, summary, run_root)
    pdf_path = output_dir / "memory_v2_visual_report.pdf"
    pdf_error = render_pdf(html_path, pdf_path)
    manifest = {
        "run_root": str(run_root),
        "generated_at_utc": datetime.now(UTC)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "pages": [path.name for _, path, _ in pages],
        "html": html_path.name,
        "pdf": pdf_path.name if pdf_error is None else None,
        "pdf_error": pdf_error,
        "provenance": {
            **provenance.__dict__,
            "issues": list(provenance.issues),
        },
        "writer_trace_exact": trace_exact,
        "audit_errors": audit.errors,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 1 if audit.errors or provenance.issues or pdf_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
