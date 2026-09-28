"""Build the Memory V2 follow-up figures and generated TeX fragments.

Usage: python make_memory_report_assets.py mem_r101 r101 r202 r303
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
VIZ = HERE / "viz"
ACCENT = "#1F4E79"
MEMORY = "#C44E52"
CONTROL = "#4C78A8"
IGNORED = "#9D755D"
EXPLICIT = "#2A9D8F"
GRID = {"color": "#D8DEE7", "alpha": 0.75, "linewidth": 0.7}


def _load(name: str) -> dict[str, Any]:
    return json.loads((VIZ / name).read_text())


def _valid(stats: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in stats["programs"] if row["is_valid"] == 1.0]


def _trajectory(stats: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, float]:
    programs = stats["programs"]
    seed = next(row["fitness"] for row in programs if row["is_valid"] == 1.0)
    best = -math.inf
    curve = []
    for row in programs:
        if row["is_valid"] == 1.0:
            best = max(best, row["fitness"])
        curve.append(best)
    return np.arange(len(curve)), np.asarray(curve), seed


def make_convergence(
    memory_stats: dict[str, Any], baselines: list[dict[str, Any]], labels: list[str]
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.6))
    baseline_colors = ["#8E9AAF", "#ADB5BD", "#6C757D"]
    for stats, label, color in zip(baselines, labels, baseline_colors):
        x, y, seed = _trajectory(stats)
        axes[0].step(x, y, where="post", color=color, lw=1.6, alpha=0.9, label=label)
        axes[1].step(
            x,
            y - seed,
            where="post",
            color=color,
            lw=1.6,
            alpha=0.9,
            label=label,
        )

    x, y, seed = _trajectory(memory_stats)
    axes[0].step(
        x, y, where="post", color=MEMORY, lw=3.0, label="Memory V2 (current main)"
    )
    axes[1].step(
        x,
        y - seed,
        where="post",
        color=MEMORY,
        lw=3.0,
        label="Memory V2 (current main)",
    )

    axes[0].scatter([x[-1]], [y[-1]], s=48, color=MEMORY, zorder=5)
    axes[1].scatter([x[-1]], [y[-1] - seed], s=48, color=MEMORY, zorder=5)
    axes[0].annotate(
        f"{y[-1]:.4f}",
        (x[-1], y[-1]),
        xytext=(-4, 9),
        textcoords="offset points",
        ha="right",
        color=MEMORY,
        fontsize=9,
        fontweight="bold",
    )
    axes[1].annotate(
        f"+{y[-1] - seed:.4f}",
        (x[-1], y[-1] - seed),
        xytext=(-4, 9),
        textcoords="offset points",
        ha="right",
        color=MEMORY,
        fontsize=9,
        fontweight="bold",
    )

    axes[0].set_title("absolute CV fitness", fontweight="bold")
    axes[1].set_title("gain above each run's own seed", fontweight="bold")
    axes[0].set_ylabel("best-so-far CV $R^2$")
    axes[1].set_ylabel(r"best-so-far $\Delta$ CV $R^2$")
    for axis in axes:
        axis.set_xlabel("completed programs (seed included)")
        axis.grid(**GRID)
        axis.set_xlim(0, 101)
    axes[0].legend(loc="lower right", fontsize=8.3, framealpha=0.95)
    fig.suptitle(
        "Gemini 3.5 Flash on california: historical no-memory envelope vs Memory V2",
        fontsize=12,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.01,
        "Reference only: the historical runs used an earlier DAG evaluator and a different seed graph.",
        ha="center",
        color="#5A6472",
        fontsize=8.5,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.92))
    fig.savefig(HERE / "memory_convergence.png", dpi=210, bbox_inches="tight")


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else math.nan


def make_memory_dynamics(memory: dict[str, Any]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 8.5))
    syncs = memory["writer_syncs"]
    released = [row["released_child_count"] for row in syncs]
    axes[0, 0].plot(
        released,
        [row["bank_size"] for row in syncs],
        "o-",
        color=ACCENT,
        label="card bank",
    )
    axes[0, 0].plot(
        released,
        [row["evidence_count"] for row in syncs],
        "s-",
        color=EXPLICIT,
        label="released evidence",
    )
    axes[0, 0].fill_between(
        released,
        [row["evidence_count"] for row in syncs],
        [row["evidence_count"] + row["pending_count"] for row in syncs],
        color="#F4A261",
        alpha=0.25,
        label="pending",
    )
    axes[0, 0].set_title("writer state and card-bank growth", fontweight="bold")
    axes[0, 0].set_xlabel("released mutation children")
    axes[0, 0].set_ylabel("count")
    axes[0, 0].legend(fontsize=8.5)

    valid = [
        row
        for row in memory["outcomes"]
        if row["proposed_treatment_id"] is not None and row["gain"] is not None
    ]
    styles = {
        "withheld_control": (CONTROL, "s", "withheld control"),
        "delivered_ignored": (IGNORED, "o", "delivered, not cited"),
        "explicit_use": (EXPLICIT, "*", "explicitly cited"),
    }
    for key, (color, marker, label) in styles.items():
        rows = [row for row in valid if row["assignment"] == key]
        axes[0, 1].errorbar(
            [row["parent_fitness"] for row in rows],
            [row["gain"] for row in rows],
            yerr=[row["gain_se"] for row in rows],
            fmt=marker,
            ms=8 if marker == "*" else 4.5,
            color=color,
            ecolor=color,
            elinewidth=0.55,
            alpha=0.7,
            capsize=0,
            label=label,
        )
    axes[0, 1].axhline(0.0, color="#4A4A4A", lw=1.0)
    axes[0, 1].set_title(
        "observed fitness change (bars are evaluator SE)", fontweight="bold"
    )
    axes[0, 1].set_xlabel("parent CV $R^2$")
    axes[0, 1].set_ylabel("child $-$ parent CV $R^2$")
    axes[0, 1].legend(fontsize=8.0, loc="lower left")

    bins = [
        ("< .865", lambda row: row["parent_fitness"] < 0.865),
        (".865–.875", lambda row: 0.865 <= row["parent_fitness"] < 0.875),
        ("≥ .875", lambda row: row["parent_fitness"] >= 0.875),
    ]
    x = np.arange(len(bins))
    width = 0.34
    for offset, delivered, color, label in (
        (-width / 2, False, CONTROL, "withheld control"),
        (width / 2, True, MEMORY, "delivered (ITT)"),
    ):
        means = []
        counts = []
        for _, predicate in bins:
            rows = [
                row for row in valid if predicate(row) and row["delivered"] is delivered
            ]
            means.append(_mean([row["gain"] for row in rows]))
            counts.append(len(rows))
        bars = axes[1, 0].bar(x + offset, means, width=width, color=color, label=label)
        for bar, count in zip(bars, counts):
            axes[1, 0].text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + (0.00018 if bar.get_height() >= 0 else -0.00035),
                f"n={count}",
                ha="center",
                va="bottom" if bar.get_height() >= 0 else "top",
                fontsize=8,
            )
    axes[1, 0].axhline(0.0, color="#4A4A4A", lw=1.0)
    axes[1, 0].set_xticks(x)
    axes[1, 0].set_xticklabels([label for label, _ in bins])
    axes[1, 0].set_xlabel("parent-fitness band")
    axes[1, 0].set_ylabel("mean valid gain")
    axes[1, 0].set_title(
        "raw randomized-delivery contrast by frontier level", fontweight="bold"
    )
    axes[1, 0].legend(fontsize=8.5)

    group_order = ["withheld_control", "delivered_ignored", "explicit_use", "empty"]
    group_labels = [
        "control",
        "delivered\nignored",
        "explicit\nuse",
        "pre-bank /\nabstain",
    ]
    groups = memory["assignment_groups"]
    valid_counts = [groups[key]["valid_n"] for key in group_order]
    invalid_counts = [groups[key]["invalid_n"] for key in group_order]
    axes[1, 1].bar(
        x := np.arange(4), valid_counts, color=EXPLICIT, label="valid outcome"
    )
    axes[1, 1].bar(
        x, invalid_counts, bottom=valid_counts, color=MEMORY, label="invalid"
    )
    for i, (good, bad) in enumerate(zip(valid_counts, invalid_counts)):
        axes[1, 1].text(i, good + bad + 0.7, str(good + bad), ha="center", fontsize=8.5)
    axes[1, 1].set_xticks(x)
    axes[1, 1].set_xticklabels(group_labels)
    axes[1, 1].set_ylabel("terminal decisions")
    axes[1, 1].set_title("assignment, uptake, and validity", fontweight="bold")
    axes[1, 1].legend(fontsize=8.5)

    for axis in axes.flat:
        axis.grid(axis="y", **GRID)
    fig.suptitle(
        "Memory V2 run dynamics — assignment is randomized; explicit citation is post-treatment",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(HERE / "memory_dynamics.png", dpi=210, bbox_inches="tight")


def _box(
    axis: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    title: str,
    body: str,
    *,
    face: str,
    edge: str,
) -> None:
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.03,rounding_size=0.06",
        facecolor=face,
        edgecolor=edge,
        linewidth=1.5,
    )
    axis.add_patch(patch)
    axis.text(
        x + 0.09, y + height - 0.16, title, fontsize=10, fontweight="bold", va="top"
    )
    axis.text(
        x + 0.09, y + height - 0.47, body, fontsize=8.2, va="top", color="#354052"
    )


def _arrow(
    axis: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = "#748094",
) -> None:
    axis.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.1,
            color=color,
            connectionstyle="arc3,rad=0.0",
            shrinkA=1,
            shrinkB=1,
        )
    )


def make_champion_dag(memory: dict[str, Any]) -> None:
    fig, axis = plt.subplots(figsize=(13.0, 7.2))
    axis.set_xlim(0, 13)
    axis.set_ylim(0, 7.2)
    axis.axis("off")

    _box(
        axis,
        (0.25, 2.65),
        1.65,
        1.35,
        "raw frame",
        "8 California columns\nx0 … x7\n\nraws remain estimator inputs",
        face="#F2F4F7",
        edge="#667085",
    )
    positions = {
        "geo_rotations": (2.7, 5.25),
        "geo_distances": (2.7, 3.85),
        "demographic_ratios": (2.7, 2.45),
        "spatial_neighborhood": (2.7, 0.45),
        "neighborhood_ratios": (7.0, 0.45),
    }
    specs = {
        "geo_rotations": (
            "rowwise · 6 outputs",
            "latitude/longitude rotations\nat 30°, 45°, and 60°",
        ),
        "geo_distances": (
            "rowwise · 6 outputs",
            "Haversine distance to LA, SF,\nSD, SJ + north/south ratios",
        ),
        "demographic_ratios": (
            "rowwise · 5 outputs",
            "income, room, bedroom, and\npopulation ratios per occupant",
        ),
        "spatial_neighborhood": (
            "aggregate · supervised · 11 outputs",
            "leave-one-out kNN target means\n(k=4,16,64), target spread, density,\nand local covariate means",
        ),
        "neighborhood_ratios": (
            "rowwise · 5 outputs",
            "raw/local covariate ratios +\nmicro-to-macro target ratio",
        ),
    }
    for node_id, (title, body) in specs.items():
        aggregate = node_id == "spatial_neighborhood"
        _box(
            axis,
            positions[node_id],
            3.25,
            1.1 if node_id != "spatial_neighborhood" else 1.55,
            f"{node_id}\n{title}",
            body,
            face="#FFF2D8" if aggregate else "#E9F1FA",
            edge="#C9720B" if aggregate else ACCENT,
        )

    _box(
        axis,
        (11.0, 2.55),
        1.65,
        1.55,
        "fixed CatBoost",
        "8 raw + 33 generated\nfeatures\n\nheld-out test refit uses\ntrain + validation",
        face="#EAF6EE",
        edge="#1A7F37",
    )
    raw_out = (1.9, 3.3)
    for node_id in (
        "geo_rotations",
        "geo_distances",
        "demographic_ratios",
        "spatial_neighborhood",
    ):
        x, y = positions[node_id]
        _arrow(axis, raw_out, (x, y + 0.55))
    _arrow(axis, (5.95, 1.15), (7.0, 1.15), color="#1A7F37")
    _arrow(axis, (1.9, 3.3), (11.0, 3.25), color="#667085")
    for node_id in ("geo_rotations", "geo_distances", "demographic_ratios"):
        x, y = positions[node_id]
        _arrow(axis, (x + 3.25, y + 0.55), (11.0, 3.3))
    _arrow(axis, (5.95, 1.15), (11.0, 3.0))
    _arrow(axis, (10.25, 1.1), (11.0, 2.9))

    champion = memory["champion"]
    axis.text(
        0.25,
        7.0,
        f"Champion {champion['id'][:8]} · generation {champion['generation']} · "
        f"CV $R^2$ {champion['fitness']:.6f} ± {champion['cv_score_std']:.6f}",
        fontsize=13,
        fontweight="bold",
        color=ACCENT,
    )
    axis.text(
        0.25,
        6.67,
        "Only one generated-to-generated edge is consumed; the other four feature blocks are independent outputs.",
        fontsize=9.3,
        color="#5A6472",
    )
    axis.text(
        7.0,
        2.15,
        "consumed dependency",
        color="#1A7F37",
        fontsize=8.5,
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(HERE / "memory_champion_dag.png", dpi=210, bbox_inches="tight")


def _tex(value: str) -> str:
    return (
        value.replace("\\", r"\textbackslash{}")
        .replace("_", r"\_")
        .replace("%", r"\%")
        .replace("&", r"\&")
        .replace("#", r"\#")
    )


def _fmt(value: float | None, digits: int = 6, *, signed: bool = False) -> str:
    if value is None or not math.isfinite(value):
        return "--"
    return f"{value:{'+' if signed else ''}.{digits}f}"


def write_card_table(memory: dict[str, Any]) -> None:
    mechanisms = {
        "mem-45c42d56aff74876a1e07c13b3cc9f1a": "multi-scale kNN target means and micro/macro ratio",
        "mem-b491828e8a094af7ab0174d20e232b6c": "add local volatility, density, and covariate means",
        "mem-c27d9dc3b4cf43e7826d29f40d138823": "out-of-fold kNN target embedding",
        "mem-8adc6313f2514aa4a7a5a1254721262b": "K-means centroid-distance features",
        "mem-82d70d2dde454693b61917ea4fc8caec": "normalized distance-to-economic-hub ratios",
        "program-f4e6e08f-9b85-4761-b899-906e0d353f79": "program exemplar: rotations, landmarks, clustering",
    }
    by_id = {row["id"]: row for row in memory["cards"]["rows"]}
    lines = [
        r"\begin{tabular}{p{5.1cm}lrrrr}",
        r"\toprule",
        r"card mechanism & kind & proposed & control & cited & best cited $\Delta R^2$ \\",
        r"\midrule",
    ]
    for card_id, mechanism in mechanisms.items():
        row = by_id[card_id]
        lines.append(
            f"{_tex(mechanism)} \\newline \\scriptsize{{{_tex(card_id[:12])}}} & "
            f"{_tex(row['kind'])} & {row['proposals']} & {row['controls']} & "
            f"{row['explicit_uses']} & {_fmt(row['best_explicit_gain'], signed=True)} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    (HERE / "memory_card_table.tex").write_text("\n".join(lines) + "\n")


def write_dag_table(memory: dict[str, Any]) -> None:
    roles = {
        "geo_rotations": "coast-aligned coordinate projections",
        "geo_distances": "metro proximity and bounded regional gradients",
        "demographic_ratios": "household scale and occupancy-normalized composition",
        "spatial_neighborhood": "leave-one-out local target/covariate summaries at three scales",
        "neighborhood_ratios": "household-to-local and micro-to-macro contrasts",
    }
    lines = [
        r"\begin{tabular}{p{3.8cm}p{3.0cm}rp{6.0cm}}",
        r"\toprule",
        r"node (kind) & dependency & outputs & role \\",
        r"\midrule",
    ]
    for row in memory["champion"]["nodes_detail"]:
        dependency = ", ".join(row["dependencies"])
        dependency_tex = (
            _tex(dependency.replace("_", " ")) if dependency else "raw only"
        )
        lines.append(
            f"{_tex(row['id'].replace('_', ' '))} ({_tex(row['kind'])}) & "
            f"{dependency_tex} & {len(row['output_cols'])} & "
            f"{_tex(roles[row['id']])} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    (HERE / "memory_dag_table.tex").write_text("\n".join(lines) + "\n")


def write_numbers(
    memory_stats: dict[str, Any],
    memory: dict[str, Any],
    test: dict[str, Any],
    baselines: list[dict[str, Any]],
) -> None:
    baseline_curves = [_trajectory(stats) for stats in baselines]
    baseline_finals = [float(curve[-1]) for _, curve, _ in baseline_curves]
    baseline_gains = [float(curve[-1] - seed) for _, curve, seed in baseline_curves]
    _, memory_curve, memory_seed = _trajectory(memory_stats)
    counts = memory["counts"]
    cards = memory["cards"]
    audit = memory["dynamic_map_audit"]
    uncertainty = memory["uncertainty"]
    posterior = memory["posterior"]
    low = memory["causal_slices"]["parent_below_0_865"]
    high = memory["causal_slices"]["parent_at_least_0_875"]
    all_rows = memory["causal_slices"]["all"]
    best_explicit = test["best_explicit_memory"]
    gemini = memory["llm_by_model"]["google/gemini-3.5-flash"]
    qwen = memory["llm_by_model"]["Qwen/Qwen3-235B-A22B-Instruct-2507"]

    values: dict[str, str] = {
        "memProgramsStored": str(counts["programs_stored"]),
        "memProgramsCompleted": str(counts["programs_completed"]),
        "memProgramsValid": str(counts["programs_valid"]),
        "memProgramsInvalid": str(counts["programs_invalid"]),
        "memProgramsIncomplete": str(counts["programs_incomplete"]),
        "memWallMinutes": f"{memory_stats['run_seconds'] / 60:.1f}",
        "memSeedCV": f"{memory_seed:.6f}",
        "memBestCV": f"{memory_curve[-1]:.6f}",
        "memBestCVStd": f"{memory['champion']['cv_score_std']:.6f}",
        "memDeltaCV": f"{memory_curve[-1] - memory_seed:+.6f}",
        "memBestId": memory["champion"]["id"][:8],
        "memBestGeneration": str(memory["champion"]["generation"]),
        "memBestNodes": f"{memory['champion']['nodes']:.0f}",
        "memBestDepth": f"{memory['champion']['depth']:.0f}",
        "memBestFeatures": f"{memory['champion']['features']:.0f}",
        "memSeedTest": f"{test['seed']['test_r2']:.6f}",
        "memSeedTestRmse": f"{test['seed']['test_rmse']:.6f}",
        "memBestTest": f"{test['best']['test_r2']:.6f}",
        "memBestTestRmse": f"{test['best']['test_rmse']:.6f}",
        "memDeltaTest": f"{test['best']['test_r2'] - test['seed']['test_r2']:+.6f}",
        "memDeltaTestRmse": f"{test['best']['test_rmse'] - test['seed']['test_rmse']:+.6f}",
        "memExplicitBestId": best_explicit["id"][:8],
        "memExplicitBestCV": f"{best_explicit['cv_r2']:.6f}",
        "memExplicitBestTest": f"{best_explicit['test_r2']:.6f}",
        "memExplicitBestRmse": f"{best_explicit['test_rmse']:.6f}",
        "memNoMemoryBestLow": f"{min(baseline_finals):.6f}",
        "memNoMemoryBestHigh": f"{max(baseline_finals):.6f}",
        "memNoMemoryGainLow": f"{min(baseline_gains):+.6f}",
        "memNoMemoryGainHigh": f"{max(baseline_gains):+.6f}",
        "memCards": str(cards["count"]),
        "memInsightCards": str(cards["kinds"]["insight"]),
        "memProgramCards": str(cards["kinds"]["program"]),
        "memCardAdds": str(cards["adds"]),
        "memCardUpdates": str(cards["updates"]),
        "memCardRetired": str(cards["retired"]),
        "memDecisions": str(counts["decisions"]),
        "memRandomized": str(counts["randomized_proposals"]),
        "memDelivered": str(counts["delivered"]),
        "memControls": str(counts["withheld_controls"]),
        "memExplicitUses": str(counts["explicit_uses"]),
        "memTerminals": str(counts["terminals"]),
        "memEvidenceFinal": str(posterior["final_writer_evidence_count"]),
        "memPendingFinal": str(posterior["final_writer_pending_count"]),
        "memEvidenceOnline": str(posterior["last_online_evidence_count"]),
        "memAllDeliveredGain": _fmt(all_rows["delivered"]["mean_gain"], signed=True),
        "memAllControlGain": _fmt(
            all_rows["withheld_control"]["mean_gain"], signed=True
        ),
        "memLowDeliveredGain": _fmt(low["delivered"]["mean_gain"], signed=True),
        "memLowControlGain": _fmt(low["withheld_control"]["mean_gain"], signed=True),
        "memHighDeliveredGain": _fmt(high["delivered"]["mean_gain"], signed=True),
        "memHighControlGain": _fmt(high["withheld_control"]["mean_gain"], signed=True),
        "memSemanticSchemas": str(audit["semantic_schema_hashes"]),
        "memDynamicSchemas": str(audit["behavior_schema_hashes"]),
        "memRepeatedParents": str(audit["repeated_parents"]),
        "memMovedParents": str(audit["parents_that_changed_cell"]),
        "memCellErrors": str(audit["cell_alignment_errors"]),
        "memCoordinateErrors": str(audit["dynamic_coordinate_errors"]),
        "memSemanticSpread": f"{audit['semantic_max_spread_for_same_parent']:.1f}",
        "memUnoccupied": str(audit["parent_cell_unoccupied"]),
        "memSeMeasured": str(uncertainty["valid_terminal_measurements"]),
        "memSeNonzero": str(uncertainty["nonzero_terminal_se"]),
        "memFoundingSeZero": str(uncertainty["founding_gain_se_zero"]),
        "memRetirementSweeps": str(memory["retirement"]["disabled_sweeps"]),
        "memBoundaryMass": f"{memory['retirement']['last_boundary_mass']:.3f}",
        "memBoundaryAlpha": f"{memory['retirement']['alpha']:.1f}",
        "memGeminiCalls": str(gemini["calls"]),
        "memQwenCalls": str(qwen["calls"]),
        "memGeminiTokens": f"{gemini['tokens_in'] + gemini['tokens_out']:,}",
        "memQwenTokens": f"{qwen['tokens_in'] + qwen['tokens_out']:,}",
    }
    lines = ["% generated by make_memory_report_assets.py — do not edit"]
    for name, value in values.items():
        lines.append(f"\\newcommand{{\\{name}}}{{{_tex(value)}}}")
    (HERE / "memory_numbers.tex").write_text("\n".join(lines) + "\n")


def main() -> None:
    memory_arm, *baseline_arms = sys.argv[1:]
    if len(baseline_arms) != 3:
        raise SystemExit("expected one Memory V2 arm and three no-memory arms")
    memory_stats = _load(f"{memory_arm}_stats.json")
    memory = _load(f"{memory_arm}_memory.json")
    test = _load(f"{memory_arm}_test.json")
    baselines = [_load(f"{arm}_stats.json") for arm in baseline_arms]
    labels = [f"historical no-memory {arm[1:]}" for arm in baseline_arms]
    make_convergence(memory_stats, baselines, labels)
    make_memory_dynamics(memory)
    make_champion_dag(memory)
    write_card_table(memory)
    write_dag_table(memory)
    write_numbers(memory_stats, memory, test, baselines)
    print("wrote Memory V2 report figures and TeX fragments")


if __name__ == "__main__":
    main()
