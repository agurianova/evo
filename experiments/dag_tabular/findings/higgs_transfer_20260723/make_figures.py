"""Validate the Higgs transfer matrix and build report figures/tables."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import sys

import matplotlib as mpl
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from problems.dag_tab.execution import execute_graph  # noqa: E402
from problems.dag_tab.graph import FeatureGraph  # noqa: E402
from problems.tabular._common import tabular_data  # noqa: E402

RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
GRAPHS = ROOT / "graphs"

EVALUATORS = ("catboost", "tabm")
GRAPH_ORDER = ("raw", "catboost", "tabm")
ENGINEERED_GRAPHS = ("catboost", "tabm")
METRICS = ("test_accuracy", "test_auc")
LABELS = {
    "raw": "Raw",
    "catboost": "CatBoost",
    "tabm": "TabM",
    "test_accuracy": "Accuracy",
    "test_auc": "ROC AUC",
}

SEMANTIC_CATEGORIES = (
    "Angular\nseparation",
    "Transverse\nmass",
    "Event scale\n& fractions",
    "Vector balance\n& alignment",
    "Longitudinal\ncentrality",
    "Mass\ncomposites",
    "Flavor /\nb-tag",
)
SEMANTIC_COUNTS = {
    "catboost": (3, 1, 3, 1, 0, 1, 1),
    "tabm": (2, 1, 1, 3, 6, 2, 0),
}

SHORT_FEATURES = {
    "delta_r_lep_jet1": r"$\Delta R(\ell,j_1)$",
    "delta_r_lep_jet2": r"$\Delta R(\ell,j_2)$",
    "m_bb_div_m_jj": r"$m_{bb}/m_{jj}$",
    "mt_lep_met": r"$m_T(\ell,\mathrm{MET})$",
    "energy_scale_ht": r"$H_T$ proxy",
    "energy_fraction": r"$p_T(j_1)/H_T$",
    "met_to_ht": r"$\mathrm{MET}/H_T$",
    "delta_r_jet1_jet2": r"$\Delta R(j_1,j_2)$",
    "btag_sum": r"$\Sigma$ b-tag",
    "pt_lep_met": r"$p_T(\ell+\mathrm{MET})$",
    "delta_r": r"$\Delta R(\ell,j_1)$",
    "delta_r_j1_j2": r"$\Delta R(j_1,j_2)$",
    "met_ratio": r"MET / visible $p_T$",
    "mt": r"$m_T(\ell,\mathrm{MET})$",
    "vis_pt_magnitude": r"$|\vec p_T^{\,vis}|$",
    "mpt_imbalance": r"$|\vec p_T^{\,vis}+\vec{MET}|$",
    "cos_phi_vis_met": r"$\cos(\phi_{vis}-\phi_{MET})$",
    "z_lepton": r"$z_\ell$",
    "c_lepton": r"$c_\ell$",
    "z_jet3": r"$z_{j_3}$",
    "c_jet3": r"$c_{j_3}$",
    "z_jet4": r"$z_{j_4}$",
    "c_jet4": r"$c_{j_4}$",
    "m_l_j1": r"$m(\ell,j_1)$ proxy",
    "m_l_j2": r"$m(\ell,j_2)$ proxy",
}


def _style() -> None:
    sns.set_theme(style="white", context="paper")
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.2,
            "axes.titlesize": 11.5,
            "axes.titleweight": "bold",
            "axes.labelsize": 9.5,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _save(fig: plt.Figure, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / f"{name}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _load_and_validate() -> tuple[dict, dict]:
    payload = json.loads((RESULTS / "cross_eval.json").read_text())
    provenance = json.loads((ROOT / "provenance.json").read_text())
    protocol = payload["protocol"]
    if protocol["phase"] != "test":
        raise ValueError("cross-evaluation is not a test-phase artifact")
    if protocol["seeds"] != [0, 1, 2, 3, 4]:
        raise ValueError(f"unexpected seeds: {protocol['seeds']}")
    if (
        not protocol["feature_graphs_fixed"]
        or not protocol["only_estimator_seed_varied"]
    ):
        raise ValueError(
            "matrix does not declare fixed graphs and estimator-only seeds"
        )

    for evaluator in EVALUATORS:
        if set(payload["cells"][evaluator]) != set(GRAPH_ORDER):
            raise ValueError(f"incomplete graph set for {evaluator}")
        for graph in GRAPH_ORDER:
            cell = payload["cells"][evaluator][graph]
            records = cell["per_seed"]
            if [record["seed"] for record in records] != protocol["seeds"]:
                raise ValueError(f"seed mismatch for {evaluator}/{graph}")
            if len(records) != 5:
                raise ValueError(f"expected five fits for {evaluator}/{graph}")
            expected_hash = provenance["graph_sha256"][graph]
            if {record["graph_file_sha256"] for record in records} != {expected_hash}:
                raise ValueError(f"graph hash mismatch for {evaluator}/{graph}")
            for metric in METRICS:
                values = np.asarray(
                    [record["test_metrics"][metric] for record in records], dtype=float
                )
                summary = cell["test_summary"][metric]
                if not np.isclose(values.mean(), summary["mean"], atol=1e-14):
                    raise ValueError(f"mean mismatch for {evaluator}/{graph}/{metric}")
                if not np.isclose(
                    values.std(ddof=1), summary["sample_std"], atol=1e-14
                ):
                    raise ValueError(f"SD mismatch for {evaluator}/{graph}/{metric}")
                if summary["n_seeds"] != 5:
                    raise ValueError(f"seed count mismatch for {evaluator}/{graph}")
    return payload, provenance


def _seed_values(payload: dict, evaluator: str, graph: str, metric: str) -> np.ndarray:
    return np.asarray(
        [
            record["test_metrics"][metric]
            for record in payload["cells"][evaluator][graph]["per_seed"]
        ],
        dtype=float,
    )


def _write_result_tables(payload: dict, provenance: dict) -> dict:
    rows: list[dict[str, object]] = []
    summary: dict[str, object] = {
        "protocol": payload["protocol"],
        "graph_sha256": provenance["graph_sha256"],
        "cells": {},
    }
    for evaluator in EVALUATORS:
        summary["cells"][evaluator] = {}
        for graph in GRAPH_ORDER:
            row: dict[str, object] = {"evaluator": evaluator, "graph": graph}
            cell_summary: dict[str, object] = {}
            for metric in METRICS:
                values = _seed_values(payload, evaluator, graph, metric)
                raw = _seed_values(payload, evaluator, "raw", metric)
                delta = values - raw
                row[f"{metric}_mean"] = values.mean()
                row[f"{metric}_sample_std"] = values.std(ddof=1)
                row[f"{metric}_paired_gain_pp"] = 100 * delta.mean()
                row[f"{metric}_paired_gain_sample_std_pp"] = 100 * delta.std(ddof=1)
                cell_summary[metric] = {
                    "mean": float(values.mean()),
                    "sample_std": float(values.std(ddof=1)),
                    "paired_gain_pp": float(100 * delta.mean()),
                    "paired_gain_sample_std_pp": float(100 * delta.std(ddof=1)),
                }
            rows.append(row)
            summary["cells"][evaluator][graph] = cell_summary

    with (RESULTS / "test_summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    tex_rows = []
    for evaluator in EVALUATORS:
        for graph in GRAPH_ORDER:
            cell = summary["cells"][evaluator][graph]
            accuracy = cell["test_accuracy"]
            auc = cell["test_auc"]
            tex_rows.append(
                f"{LABELS[evaluator]} & {LABELS[graph]} & "
                f"{100 * accuracy['mean']:.3f} $\\pm$ "
                f"{100 * accuracy['sample_std']:.3f} & "
                f"{accuracy['paired_gain_pp']:+.3f} & "
                f"{100 * auc['mean']:.3f} $\\pm$ "
                f"{100 * auc['sample_std']:.3f} & "
                f"{auc['paired_gain_pp']:+.3f} \\\\"
            )
    (RESULTS / "test_rows.tex").write_text("\n".join(tex_rows) + "\n\\bottomrule\n")

    baseline = {
        "catboost": (0.726322360835279, 0.0032641610508236957),
        "tabm": (0.7373372667204711, 0.001980303246776369),
    }
    evolution_rows = []
    for model in EVALUATORS:
        program = provenance["programs"][model]
        start, start_sd = baseline[model]
        best = program["metrics"]["fitness"]
        best_sd = program["metrics"]["cv_score_std"]
        evolution_rows.append(
            f"{LABELS[model]} & {100 * start:.3f} $\\pm$ {100 * start_sd:.3f} & "
            f"{100 * best:.3f} $\\pm$ {100 * best_sd:.3f} & "
            f"{100 * (best - start):+.3f} & {program['iteration']} & "
            f"{int(program['metrics']['generated_feature_count'])} \\\\"
        )
    (RESULTS / "evolution_rows.tex").write_text(
        "\n".join(evolution_rows) + "\n\\bottomrule\n"
    )
    return summary


def _performance_figure(summary: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.55))
    palettes = ("crest", "mako")
    for ax, metric, palette in zip(axes, METRICS, palettes, strict=True):
        means = np.asarray(
            [
                [
                    100 * summary["cells"][evaluator][graph][metric]["mean"]
                    for graph in GRAPH_ORDER
                ]
                for evaluator in EVALUATORS
            ]
        )
        stds = np.asarray(
            [
                [
                    100 * summary["cells"][evaluator][graph][metric]["sample_std"]
                    for graph in GRAPH_ORDER
                ]
                for evaluator in EVALUATORS
            ]
        )
        cmap = sns.color_palette(palette, as_cmap=True)
        norm = mpl.colors.Normalize(vmin=float(means.min()), vmax=float(means.max()))
        sns.heatmap(
            means,
            ax=ax,
            cmap=cmap,
            norm=norm,
            annot=False,
            linewidths=1,
            linecolor="white",
            xticklabels=[LABELS[g] + " graph" for g in GRAPH_ORDER],
            yticklabels=[LABELS[e] + " evaluator" for e in EVALUATORS],
            cbar_kws={"label": f"Test {LABELS[metric]} (%)", "shrink": 0.8},
        )
        for row in range(2):
            winner = int(np.argmax(means[row]))
            ax.add_patch(
                Rectangle(
                    (winner + 0.03, row + 0.03),
                    0.94,
                    0.94,
                    fill=False,
                    edgecolor="#F4A261",
                    linewidth=2.5,
                )
            )
            for col in range(3):
                rgba = cmap(norm(means[row, col]))
                luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
                ax.text(
                    col + 0.5,
                    row + 0.5,
                    f"{means[row, col]:.3f}\n±{stds[row, col]:.3f}",
                    ha="center",
                    va="center",
                    color="#17324D" if luminance > 0.62 else "white",
                    fontsize=8.3,
                    fontweight="bold" if col == winner else "normal",
                )
        ax.set_xlabel("Frozen FeatureGraph")
        ax.set_ylabel("")
        ax.set_title(f"Five-seed test {LABELS[metric]}")
        ax.tick_params(axis="x", rotation=18)
        ax.tick_params(axis="y", rotation=0)
    fig.suptitle(
        "Higgs-small transfer: the TabM-evolved graph wins both evaluator rows",
        fontsize=13,
        fontweight="bold",
        y=1.03,
    )
    fig.tight_layout()
    _save(fig, "performance_matrix")


def _paired_gain_figure(summary: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8.9, 3.55))
    all_values = []
    matrices = {}
    for metric in METRICS:
        matrix = np.asarray(
            [
                [
                    summary["cells"][evaluator][graph][metric]["paired_gain_pp"]
                    for graph in ENGINEERED_GRAPHS
                ]
                for evaluator in EVALUATORS
            ]
        )
        matrices[metric] = matrix
        all_values.extend(matrix.ravel())
    limit = max(abs(min(all_values)), abs(max(all_values)))
    cmap = sns.diverging_palette(18, 220, s=80, l=48, as_cmap=True)
    norm = mpl.colors.TwoSlopeNorm(vmin=-limit, vcenter=0.0, vmax=limit)
    for ax, metric in zip(axes, METRICS, strict=True):
        matrix = matrices[metric]
        sns.heatmap(
            matrix,
            ax=ax,
            cmap=cmap,
            norm=norm,
            annot=True,
            fmt="+.3f",
            linewidths=1,
            linecolor="white",
            xticklabels=[LABELS[g] + " graph" for g in ENGINEERED_GRAPHS],
            yticklabels=[LABELS[e] + " evaluator" for e in EVALUATORS],
            cbar_kws={"label": "Paired gain vs raw (percentage points)", "shrink": 0.8},
        )
        ax.set_xlabel("Frozen FeatureGraph")
        ax.set_ylabel("")
        ax.set_title(f"{LABELS[metric]} uplift")
        ax.tick_params(axis="x", rotation=18)
        ax.tick_params(axis="y", rotation=0)
    fig.suptitle(
        "Every transfer helps; the TabM graph provides the largest uplift",
        fontsize=13,
        fontweight="bold",
        y=1.03,
    )
    fig.tight_layout()
    _save(fig, "paired_gain_matrix")


def _graph_outputs() -> tuple[dict[str, FeatureGraph], dict[str, pd.DataFrame]]:
    os.environ.setdefault("GIGAEVO_TABULAR_DATA", "/home/jovyan/tabm-data/data")
    dataset = tabular_data.load_dataset("higgs-small")
    raw_columns = [f"x{i}" for i in range(dataset.X_train.shape[1])]
    frame = pd.DataFrame(dataset.X_train, columns=raw_columns)
    graphs = {
        name: FeatureGraph.model_validate_json((GRAPHS / f"{name}.json").read_text())
        for name in ENGINEERED_GRAPHS
    }
    outputs = {}
    for name, graph in graphs.items():
        transformed = execute_graph(graph, frame)
        output = transformed[graph.feature_output_columns]
        if not np.isfinite(output.to_numpy(dtype=float)).all():
            raise ValueError(f"{name} graph emitted non-finite training values")
        outputs[name] = output
    return graphs, outputs


def _semantic_figure(graphs: dict[str, FeatureGraph]) -> None:
    fig, axes = plt.subplots(
        1, 2, figsize=(10.6, 4.25), gridspec_kw={"width_ratios": [1.65, 1]}
    )
    colors = sns.color_palette("Set2", n_colors=len(SEMANTIC_CATEGORIES))
    x = np.arange(2)
    bottoms = np.zeros(2)
    for index, category in enumerate(SEMANTIC_CATEGORIES):
        values = np.asarray([SEMANTIC_COUNTS[name][index] for name in EVALUATORS])
        axes[0].bar(
            x,
            values,
            bottom=bottoms,
            color=colors[index],
            width=0.62,
            label=category.replace("\n", " "),
        )
        for col, value in enumerate(values):
            if value:
                axes[0].text(
                    col,
                    bottoms[col] + value / 2,
                    str(value),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="#17324D",
                )
        bottoms += values
    axes[0].set_xticks(x, [LABELS[name] + " graph" for name in EVALUATORS])
    axes[0].set_ylabel("Generated output columns")
    axes[0].set_title("Semantic allocation of all outputs")
    axes[0].legend(
        ncol=2,
        fontsize=7.2,
        frameon=False,
        loc="upper left",
        bbox_to_anchor=(0.0, -0.15),
    )

    attributes = ("Nodes", "Outputs", "Max depth", "Raw cols touched")
    values = {
        name: (
            len(graphs[name].nodes),
            len(graphs[name].feature_output_columns),
            graphs[name].depth,
            len(
                {
                    column
                    for node in graphs[name].nodes
                    for column in node.input_cols
                    if column.startswith("x")
                }
            ),
        )
        for name in EVALUATORS
    }
    y = np.arange(len(attributes))
    width = 0.35
    for offset, name, color in (
        (-width / 2, "catboost", "#2A6F97"),
        (width / 2, "tabm", "#D97706"),
    ):
        bars = axes[1].barh(
            y + offset,
            values[name],
            height=width,
            label=LABELS[name],
            color=color,
        )
        axes[1].bar_label(bars, padding=2, fontsize=8)
    axes[1].set_yticks(y, attributes)
    axes[1].invert_yaxis()
    axes[1].set_xlim(0, max(max(v) for v in values.values()) * 1.18)
    axes[1].set_xlabel("Count")
    axes[1].set_title("Graph structure")
    axes[1].legend(frameon=False, loc="upper right")
    sns.despine(ax=axes[1])
    fig.suptitle(
        "Broad CatBoost coverage versus dense TabM event geometry",
        fontsize=13,
        fontweight="bold",
        y=1.02,
    )
    fig.tight_layout()
    _save(fig, "feature_anatomy")

    with (RESULTS / "semantic_counts.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["graph", *[x.replace("\n", " ") for x in SEMANTIC_CATEGORIES]])
        for name in EVALUATORS:
            writer.writerow([name, *SEMANTIC_COUNTS[name]])


def _correlation_figure(outputs: dict[str, pd.DataFrame]) -> None:
    cat = outputs["catboost"].rank(method="average")
    tab = outputs["tabm"].rank(method="average")
    combined = np.corrcoef(cat.to_numpy().T, tab.to_numpy().T)
    corr = combined[: cat.shape[1], cat.shape[1] :]
    corr_frame = pd.DataFrame(corr, index=cat.columns, columns=tab.columns)
    corr_frame.to_csv(RESULTS / "cross_feature_spearman.csv")

    pairs = sorted(
        (
            {
                "catboost_feature": cat.columns[row],
                "tabm_feature": tab.columns[col],
                "spearman_rho": corr[row, col],
                "abs_spearman_rho": abs(corr[row, col]),
            }
            for row in range(corr.shape[0])
            for col in range(corr.shape[1])
        ),
        key=lambda item: item["abs_spearman_rho"],
        reverse=True,
    )
    with (RESULTS / "top_correlations.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(pairs[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(pairs)

    top_rows = []
    for item in pairs[:7]:
        top_rows.append(
            f"{SHORT_FEATURES[item['catboost_feature']]} & "
            f"{SHORT_FEATURES[item['tabm_feature']]} & "
            f"{item['spearman_rho']:.3f} \\\\"
        )
    (RESULTS / "top_correlations_rows.tex").write_text(
        "\n".join(top_rows) + "\n\\bottomrule\n"
    )

    fig, ax = plt.subplots(figsize=(11.7, 6.25))
    labels = np.full(corr.shape, "", dtype=object)
    for row in range(corr.shape[0]):
        for col in range(corr.shape[1]):
            if abs(corr[row, col]) >= 0.60:
                labels[row, col] = f"{corr[row, col]:.2f}"
    sns.heatmap(
        corr,
        ax=ax,
        cmap=sns.diverging_palette(240, 15, s=85, l=45, as_cmap=True),
        center=0,
        vmin=-1,
        vmax=1,
        annot=labels,
        fmt="",
        annot_kws={"fontsize": 7.2, "fontweight": "bold"},
        linewidths=0.35,
        linecolor="white",
        xticklabels=[SHORT_FEATURES[column] for column in tab.columns],
        yticklabels=[SHORT_FEATURES[column] for column in cat.columns],
        cbar_kws={"label": "Spearman correlation on training rows", "shrink": 0.78},
    )
    ax.set_xlabel("TabM-evolved output")
    ax.set_ylabel("CatBoost-evolved output")
    ax.set_title(
        "Different names, four shared mechanisms: cross-graph feature correlation"
    )
    ax.tick_params(axis="x", rotation=42, labelsize=7.5)
    ax.tick_params(axis="y", rotation=0, labelsize=7.5)
    fig.tight_layout()
    _save(fig, "cross_feature_correlation")


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    _style()
    payload, provenance = _load_and_validate()
    summary = _write_result_tables(payload, provenance)
    graphs, outputs = _graph_outputs()
    _performance_figure(summary)
    _paired_gain_figure(summary)
    _semantic_figure(graphs)
    _correlation_figure(outputs)
    print(f"validated 30 seed-level fits and wrote report assets under {ROOT}")


if __name__ == "__main__":
    main()
