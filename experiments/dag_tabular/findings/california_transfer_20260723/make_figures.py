"""Build the figures and derived tables for the California transfer report."""

from __future__ import annotations

import csv
import itertools
import json
from pathlib import Path
import statistics

import matplotlib as mpl
from matplotlib.patches import Patch, Rectangle
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
GRAPHS = ROOT / "graphs"
FIGURES = ROOT / "figures"

MODELS = (
    "catboost",
    "tabm",
    "realmlp",
    "tabicl",
    "tabpfn",
    "lightgbm",
    "xgboost",
    "tabfm",
)
GRAPH_ORDER = ("raw", *MODELS)
LABELS = {
    "raw": "Raw",
    "catboost": "CatBoost",
    "tabm": "TabM",
    "realmlp": "RealMLP",
    "tabicl": "TabICL",
    "tabpfn": "TabPFN",
    "lightgbm": "LightGBM",
    "xgboost": "XGBoost",
    "tabfm": "TabFM",
}
FAMILY_LABELS = {
    "boosting": "Boosting",
    "classical_dl": "Classical DL",
    "foundation": "Foundation",
}
FAMILY_ORDER = ("boosting", "classical_dl", "foundation")
FAMILY_COLORS = {
    "boosting": "#2A6F97",
    "classical_dl": "#D97706",
    "foundation": "#7B2CBF",
}

# Mutually exclusive, hand-coded semantic allocation of every emitted column.
# The report explains the taxonomy and treats it as an interpretive audit, not
# an automatic metric or a statement about feature importance.
SEMANTIC_CATEGORIES = (
    "Metro / proximity",
    "Coordinate / coast",
    "Household ratios",
    "Global interactions",
    "Local covariates",
    "Target neighbourhood",
    "Context contrasts",
    "Learned proxy / basis",
)
SEMANTIC_COUNTS = {
    "catboost": (6, 6, 5, 0, 7, 4, 5, 0),
    "tabm": (2, 0, 1, 2, 12, 8, 8, 0),
    "realmlp": (10, 2, 3, 0, 0, 1, 0, 1),
    "tabicl": (4, 1, 3, 0, 0, 3, 4, 0),
    "tabpfn": (2, 0, 3, 0, 3, 6, 0, 0),
    "lightgbm": (2, 2, 3, 0, 4, 4, 1, 0),
    "xgboost": (2, 2, 3, 0, 12, 3, 0, 10),
    "tabfm": (2, 2, 2, 0, 1, 0, 0, 0),
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _save(fig: plt.Figure, stem: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIGURES / f"{stem}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def _style() -> None:
    sns.set_theme(style="white", context="paper")
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _annotate_heatmap(
    ax: plt.Axes,
    data: np.ndarray,
    labels: list[list[str]],
    *,
    cmap: mpl.colors.Colormap,
    norm: mpl.colors.Normalize,
    fontsize: float = 7.3,
) -> None:
    for row in range(data.shape[0]):
        for col in range(data.shape[1]):
            rgba = cmap(norm(data[row, col]))
            luminance = 0.2126 * rgba[0] + 0.7152 * rgba[1] + 0.0722 * rgba[2]
            color = "#102A43" if luminance > 0.58 else "white"
            ax.text(
                col + 0.5,
                row + 0.5,
                labels[row][col],
                ha="center",
                va="center",
                color=color,
                fontsize=fontsize,
                linespacing=1.15,
            )


def _outline_native_and_winner(
    ax: plt.Axes, values: np.ndarray, *, includes_raw: bool
) -> None:
    offset = 1 if includes_raw else 0
    for row in range(len(MODELS)):
        native_col = row + offset
        winner_col = int(np.argmin(values[row, offset:])) + offset
        ax.add_patch(
            Rectangle(
                (native_col + 0.055, row + 0.055),
                0.89,
                0.89,
                fill=False,
                edgecolor="#F59E0B",
                linewidth=1.6,
                linestyle=(0, (2.5, 1.6)),
            )
        )
        ax.add_patch(
            Rectangle(
                (winner_col + 0.02, row + 0.02),
                0.96,
                0.96,
                fill=False,
                edgecolor="#0B253A",
                linewidth=2.3,
            )
        )


def make_rmse_figure(payload: dict) -> None:
    cells = payload["cells"]
    means = np.asarray(
        [
            [cells[evaluator][graph]["test_rmse"]["mean"] for graph in GRAPH_ORDER]
            for evaluator in MODELS
        ]
    )
    stds = np.asarray(
        [
            [
                cells[evaluator][graph]["test_rmse"]["sample_std"]
                for graph in GRAPH_ORDER
            ]
            for evaluator in MODELS
        ]
    )
    annotations = [
        [
            f"{means[row, col]:.4f}\n±{stds[row, col]:.4f}"
            for col in range(len(GRAPH_ORDER))
        ]
        for row in range(len(MODELS))
    ]
    cmap = sns.color_palette("mako_r", as_cmap=True)
    norm = mpl.colors.Normalize(vmin=float(means.min()), vmax=float(means.max()))
    fig, ax = plt.subplots(figsize=(12.25, 6.15))
    sns.heatmap(
        means,
        ax=ax,
        cmap=cmap,
        norm=norm,
        cbar_kws={"label": "Held-out RMSE (lower is better)", "shrink": 0.80},
        linewidths=0.8,
        linecolor="white",
        annot=False,
        xticklabels=[LABELS[name] for name in GRAPH_ORDER],
        yticklabels=[LABELS[name] for name in MODELS],
    )
    _annotate_heatmap(ax, means, annotations, cmap=cmap, norm=norm)
    _outline_native_and_winner(ax, means, includes_raw=True)
    ax.set_xlabel("FeatureGraph source")
    ax.set_ylabel("Evaluator")
    ax.set_title("Five-seed held-out RMSE: evaluator × frozen FeatureGraph")
    ax.tick_params(axis="x", rotation=25)
    ax.tick_params(axis="y", rotation=0)
    ax.legend(
        handles=[
            Patch(
                facecolor="none", edgecolor="#0B253A", linewidth=2.3, label="row winner"
            ),
            Patch(
                facecolor="none",
                edgecolor="#F59E0B",
                linewidth=1.6,
                linestyle=(0, (2.5, 1.6)),
                label="native graph",
            ),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.19),
        ncol=2,
        frameon=False,
    )
    _save(fig, "rmse_matrix")


def make_improvement_figure(payload: dict) -> None:
    cells = payload["cells"]
    values = np.asarray(
        [
            [
                100.0 * cells[evaluator][graph]["rmse_reduction_fraction"]
                for graph in MODELS
            ]
            for evaluator in MODELS
        ]
    )
    annotations = [[f"{value:.2f}%" for value in row] for row in values]
    cmap = sns.diverging_palette(18, 220, s=85, l=48, as_cmap=True)
    norm = mpl.colors.TwoSlopeNorm(
        vmin=float(values.min()), vcenter=0.0, vmax=float(values.max())
    )
    fig, ax = plt.subplots(figsize=(11.4, 6.1))
    sns.heatmap(
        values,
        ax=ax,
        cmap=cmap,
        norm=norm,
        cbar_kws={"label": "RMSE reduction versus raw (%)", "shrink": 0.80},
        linewidths=0.8,
        linecolor="white",
        annot=False,
        xticklabels=[LABELS[name] for name in MODELS],
        yticklabels=[LABELS[name] for name in MODELS],
    )
    _annotate_heatmap(ax, values, annotations, cmap=cmap, norm=norm, fontsize=8.2)
    # The helper minimizes values, while this matrix should maximize them.
    for row in range(len(MODELS)):
        native_col = row
        winner_col = int(np.argmax(values[row]))
        ax.add_patch(
            Rectangle(
                (native_col + 0.055, row + 0.055),
                0.89,
                0.89,
                fill=False,
                edgecolor="#F59E0B",
                linewidth=1.6,
                linestyle=(0, (2.5, 1.6)),
            )
        )
        ax.add_patch(
            Rectangle(
                (winner_col + 0.02, row + 0.02),
                0.96,
                0.96,
                fill=False,
                edgecolor="#0B253A",
                linewidth=2.3,
            )
        )
    ax.set_xlabel("FeatureGraph source")
    ax.set_ylabel("Evaluator")
    ax.set_title("Relative effect of each frozen graph versus raw features")
    ax.tick_params(axis="x", rotation=25)
    ax.tick_params(axis="y", rotation=0)
    _save(fig, "improvement_matrix")


def _graph_metadata() -> tuple[dict[str, dict], dict[str, set[str]]]:
    metadata: dict[str, dict] = {}
    outputs: dict[str, set[str]] = {}
    for model in MODELS:
        graph = _load_json(GRAPHS / f"{model}.json")
        nodes = graph["nodes"]
        by_id = {node["id"]: node for node in nodes}

        def depth(node_id: str) -> int:
            dependencies = by_id[node_id].get("dependencies", [])
            return 1 + max((depth(dep) for dep in dependencies), default=0)

        rowwise = sum(
            len(node["output_cols"]) for node in nodes if node["kind"] == "rowwise"
        )
        aggregate = sum(
            len(node["output_cols"]) for node in nodes if node["kind"] == "aggregate"
        )
        all_outputs = {
            output for node in nodes for output in node.get("output_cols", [])
        }
        semantic_total = sum(SEMANTIC_COUNTS[model])
        if semantic_total != len(all_outputs):
            raise RuntimeError(
                f"{model}: semantic profile has {semantic_total} columns, "
                f"but graph emits {len(all_outputs)}"
            )
        metadata[model] = {
            "nodes": len(nodes),
            "depth": max(depth(node["id"]) for node in nodes),
            "rowwise_outputs": rowwise,
            "aggregate_outputs": aggregate,
            "features": len(all_outputs),
        }
        outputs[model] = all_outputs
    return metadata, outputs


def make_graph_anatomy_figure() -> None:
    metadata, _ = _graph_metadata()
    semantic = np.asarray([SEMANTIC_COUNTS[model] for model in MODELS], dtype=float)
    fig, (ax_left, ax_right) = plt.subplots(
        1,
        2,
        figsize=(13.4, 6.15),
        gridspec_kw={"width_ratios": (1.65, 1.0), "wspace": 0.30},
    )

    cmap = sns.color_palette("crest", as_cmap=True)
    norm = mpl.colors.Normalize(vmin=0.0, vmax=float(semantic.max()))
    sns.heatmap(
        semantic,
        ax=ax_left,
        cmap=cmap,
        norm=norm,
        cbar_kws={"label": "Emitted columns", "shrink": 0.75},
        linewidths=0.8,
        linecolor="white",
        annot=True,
        fmt=".0f",
        xticklabels=SEMANTIC_CATEGORIES,
        yticklabels=[LABELS[name] for name in MODELS],
    )
    ax_left.set_title("A. Semantic allocation")
    ax_left.set_xlabel("")
    ax_left.set_ylabel("")
    ax_left.tick_params(axis="x", rotation=35)
    ax_left.tick_params(axis="y", rotation=0)

    y = np.arange(len(MODELS))
    rowwise = np.asarray([metadata[name]["rowwise_outputs"] for name in MODELS])
    aggregate = np.asarray([metadata[name]["aggregate_outputs"] for name in MODELS])
    ax_right.barh(y, rowwise, color="#2A9D8F", label="rowwise-node outputs")
    ax_right.barh(
        y,
        aggregate,
        left=rowwise,
        color="#7B2CBF",
        label="aggregate-node outputs",
    )
    for index, model in enumerate(MODELS):
        item = metadata[model]
        ax_right.text(
            item["features"] + 0.7,
            index,
            f"{item['nodes']} nodes · depth {item['depth']}",
            va="center",
            fontsize=8.3,
            color="#334E68",
        )
    ax_right.set_yticks(y, [LABELS[name] for name in MODELS])
    ax_right.invert_yaxis()
    ax_right.set_xlim(0, 44)
    ax_right.set_xlabel("Number of generated columns")
    ax_right.set_title("B. Graph structure")
    ax_right.spines[["top", "right", "left"]].set_visible(False)
    ax_right.grid(axis="x", alpha=0.18)
    ax_right.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=2,
        frameon=False,
        fontsize=8.3,
    )
    _save(fig, "graph_anatomy")


def make_similarity_figure() -> None:
    _, outputs = _graph_metadata()
    exact = np.zeros((len(MODELS), len(MODELS)))
    semantic = np.zeros_like(exact)
    for row, left in enumerate(MODELS):
        for col, right in enumerate(MODELS):
            union = outputs[left] | outputs[right]
            exact[row, col] = len(outputs[left] & outputs[right]) / len(union)
            left_profile = np.asarray(SEMANTIC_COUNTS[left], dtype=float)
            right_profile = np.asarray(SEMANTIC_COUNTS[right], dtype=float)
            semantic[row, col] = float(
                left_profile
                @ right_profile
                / np.linalg.norm(left_profile)
                / np.linalg.norm(right_profile)
            )

    fig, (ax_left, ax_right) = plt.subplots(
        1, 2, figsize=(13.0, 5.75), gridspec_kw={"wspace": 0.36}
    )
    labels = [LABELS[name] for name in MODELS]
    sns.heatmap(
        100.0 * exact,
        ax=ax_left,
        cmap="Blues",
        vmin=0,
        vmax=100,
        square=True,
        linewidths=0.7,
        linecolor="white",
        annot=True,
        fmt=".0f",
        cbar_kws={"label": "Jaccard (%)", "shrink": 0.72},
        xticklabels=labels,
        yticklabels=labels,
    )
    ax_left.set_title("A. Exact output-name overlap")
    ax_left.tick_params(axis="x", rotation=35)
    ax_left.tick_params(axis="y", rotation=0)

    sns.heatmap(
        semantic,
        ax=ax_right,
        cmap="Purples",
        vmin=0,
        vmax=1,
        square=True,
        linewidths=0.7,
        linecolor="white",
        annot=True,
        fmt=".2f",
        cbar_kws={"label": "Cosine similarity", "shrink": 0.72},
        xticklabels=labels,
        yticklabels=labels,
    )
    ax_right.set_title("B. Semantic-allocation similarity")
    ax_right.tick_params(axis="x", rotation=35)
    ax_right.tick_params(axis="y", rotation=0)
    _save(fig, "similarity_matrices")

    with (RESULTS / "output_name_jaccard.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["graph", *MODELS])
        for row, model in enumerate(MODELS):
            writer.writerow([model, *exact[row]])
    with (RESULTS / "semantic_profile_cosine.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["graph", *MODELS])
        for row, model in enumerate(MODELS):
            writer.writerow([model, *semantic[row]])
    with (RESULTS / "semantic_feature_counts.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["graph", *SEMANTIC_CATEGORIES])
        for model in MODELS:
            writer.writerow([model, *SEMANTIC_COUNTS[model]])


def make_transfer_summary_figure(payload: dict) -> None:
    cells = payload["cells"]
    families = payload["model_families"]
    source_rows = list(csv.DictReader((RESULTS / "source_transfer_summary.csv").open()))
    source_rows.sort(
        key=lambda row: float(row["foreign_mean_reduction_percent"]), reverse=True
    )

    family_values = np.zeros((len(FAMILY_ORDER), len(FAMILY_ORDER)))
    family_counts = np.zeros_like(family_values)
    for evaluator, graph in itertools.product(MODELS, MODELS):
        row = FAMILY_ORDER.index(families[evaluator])
        col = FAMILY_ORDER.index(families[graph])
        family_values[row, col] += (
            100.0 * cells[evaluator][graph]["rmse_reduction_fraction"]
        )
        family_counts[row, col] += 1
    family_values /= family_counts

    fig, (ax_left, ax_right) = plt.subplots(
        1,
        2,
        figsize=(12.5, 4.7),
        gridspec_kw={"width_ratios": (1.35, 1.0), "wspace": 0.34},
    )
    ordered_models = [row["graph"] for row in source_rows]
    foreign_means = [
        float(row["foreign_mean_reduction_percent"]) for row in source_rows
    ]
    native = [float(row["native_reduction_percent"]) for row in source_rows]
    best_counts = [int(row["best_evaluator_count"]) for row in source_rows]
    positions = np.arange(len(ordered_models))
    colors = [FAMILY_COLORS[families[model]] for model in ordered_models]
    ax_left.barh(positions, foreign_means, color=colors, alpha=0.90)
    ax_left.scatter(native, positions, color="#111827", s=28, marker="D", zorder=3)
    for index, (value, count) in enumerate(
        zip(foreign_means, best_counts, strict=True)
    ):
        ax_left.text(
            value + 0.18,
            index,
            f"{count} row wins",
            va="center",
            fontsize=8.1,
            color="#334E68",
        )
    ax_left.set_yticks(positions, [LABELS[name] for name in ordered_models])
    ax_left.invert_yaxis()
    ax_left.set_xlim(0, 14.0)
    ax_left.set_xlabel("Mean RMSE reduction on seven foreign evaluators (%)")
    ax_left.set_title("A. Donor quality")
    ax_left.spines[["top", "right", "left"]].set_visible(False)
    ax_left.grid(axis="x", alpha=0.18)
    ax_left.legend(
        handles=[
            Patch(facecolor="#64748B", label="foreign-evaluator mean"),
            mpl.lines.Line2D(
                [],
                [],
                color="#111827",
                marker="D",
                linestyle="None",
                label="native reduction",
            ),
        ],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.17),
        ncol=2,
        frameon=False,
        fontsize=8.1,
    )

    sns.heatmap(
        family_values,
        ax=ax_right,
        cmap="YlGnBu",
        vmin=0,
        vmax=float(family_values.max()),
        linewidths=1.0,
        linecolor="white",
        annot=True,
        fmt=".2f",
        cbar_kws={"label": "Mean reduction vs raw (%)", "shrink": 0.75},
        xticklabels=[FAMILY_LABELS[name] for name in FAMILY_ORDER],
        yticklabels=[FAMILY_LABELS[name] for name in FAMILY_ORDER],
    )
    ax_right.set_xlabel("Graph-source family")
    ax_right.set_ylabel("Evaluator family")
    ax_right.set_title("B. Cross-family transfer")
    ax_right.tick_params(axis="x", rotation=25)
    ax_right.tick_params(axis="y", rotation=0)
    _save(fig, "transfer_summary")

    with (RESULTS / "family_transfer.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["evaluator_family", *FAMILY_ORDER])
        for row, family in enumerate(FAMILY_ORDER):
            writer.writerow([family, *family_values[row]])


def write_native_foreign_summary(payload: dict) -> None:
    cells = payload["cells"]
    rows = []
    for evaluator in MODELS:
        foreign = [graph for graph in MODELS if graph != evaluator]
        best_foreign = min(
            foreign, key=lambda graph: cells[evaluator][graph]["test_rmse"]["mean"]
        )
        native_by_seed = {
            int(row["seed"]): float(row["test_rmse"])
            for row in cells[evaluator][evaluator]["per_seed"]
        }
        foreign_by_seed = {
            int(row["seed"]): float(row["test_rmse"])
            for row in cells[evaluator][best_foreign]["per_seed"]
        }
        paired = [native_by_seed[seed] - foreign_by_seed[seed] for seed in range(5)]
        rows.append(
            {
                "evaluator": evaluator,
                "native_graph": evaluator,
                "native_rmse_mean": cells[evaluator][evaluator]["test_rmse"]["mean"],
                "native_rmse_sample_std": cells[evaluator][evaluator]["test_rmse"][
                    "sample_std"
                ],
                "best_foreign_graph": best_foreign,
                "best_foreign_rmse_mean": cells[evaluator][best_foreign]["test_rmse"][
                    "mean"
                ],
                "best_foreign_rmse_sample_std": cells[evaluator][best_foreign][
                    "test_rmse"
                ]["sample_std"],
                "native_minus_foreign_paired_mean": statistics.fmean(paired),
                "native_minus_foreign_paired_sample_std": statistics.stdev(paired),
                "foreign_wins_seed_count": sum(delta > 0 for delta in paired),
            }
        )
    with (RESULTS / "native_vs_best_foreign.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _metric_tex(summary: dict) -> str:
    mean = float(summary["mean"])
    sample_std = float(summary["sample_std"])
    std_text = "0" if sample_std < 0.5e-7 else f"{sample_std:.6f}"
    return f"{mean:.6f} {{\\scriptsize$\\pm$ {std_text}}}"


def write_tex_tables(payload: dict) -> None:
    cells = payload["cells"]
    families = payload["model_families"]
    metadata, _ = _graph_metadata()

    best_rows = []
    native_foreign_rows = []
    for evaluator in MODELS:
        best = min(
            MODELS, key=lambda graph: cells[evaluator][graph]["test_rmse"]["mean"]
        )
        best_cell = cells[evaluator][best]
        native_cell = cells[evaluator][evaluator]
        best_rows.append(
            " & ".join(
                (
                    LABELS[evaluator],
                    _metric_tex(cells[evaluator]["raw"]["test_rmse"]),
                    _metric_tex(native_cell["test_rmse"]),
                    LABELS[best],
                    _metric_tex(best_cell["test_rmse"]),
                    _metric_tex(best_cell["test_r2"]),
                    str(native_cell["rank"]),
                )
            )
            + r" \\"
        )

        foreign = [graph for graph in MODELS if graph != evaluator]
        best_foreign = min(
            foreign, key=lambda graph: cells[evaluator][graph]["test_rmse"]["mean"]
        )
        native_by_seed = {
            int(row["seed"]): float(row["test_rmse"]) for row in native_cell["per_seed"]
        }
        foreign_by_seed = {
            int(row["seed"]): float(row["test_rmse"])
            for row in cells[evaluator][best_foreign]["per_seed"]
        }
        paired = [native_by_seed[seed] - foreign_by_seed[seed] for seed in range(5)]
        native_foreign_rows.append(
            " & ".join(
                (
                    LABELS[evaluator],
                    LABELS[best_foreign],
                    f"{statistics.fmean(paired):+.6f} "
                    f"{{\\scriptsize$\\pm$ {statistics.stdev(paired):.6f}}}",
                    f"{sum(delta > 0 for delta in paired)}/5",
                )
            )
            + r" \\"
        )

    structure_rows = []
    for model in MODELS:
        item = metadata[model]
        structure_rows.append(
            " & ".join(
                (
                    LABELS[model],
                    FAMILY_LABELS[families[model]],
                    str(item["nodes"]),
                    str(item["depth"]),
                    str(item["features"]),
                    str(item["rowwise_outputs"]),
                    str(item["aggregate_outputs"]),
                )
            )
            + r" \\"
        )

    donor_rows = list(csv.DictReader((RESULTS / "source_transfer_summary.csv").open()))
    donor_rows.sort(
        key=lambda row: float(row["foreign_mean_reduction_percent"]), reverse=True
    )
    donor_tex_rows = [
        " & ".join(
            (
                LABELS[row["graph"]],
                FAMILY_LABELS[row["family"]],
                f"{float(row['native_reduction_percent']):.2f}\\%",
                f"{float(row['foreign_mean_reduction_percent']):.2f}\\%",
                row["best_evaluator_count"],
                row["top3_evaluator_count"],
            )
        )
        + r" \\"
        for row in donor_rows
    ]

    (RESULTS / "best_results_rows.tex").write_text(
        "\n".join(best_rows) + "\n\\bottomrule\n"
    )
    (RESULTS / "native_foreign_rows.tex").write_text(
        "\n".join(native_foreign_rows) + "\n\\bottomrule\n"
    )
    (RESULTS / "graph_structure_rows.tex").write_text(
        "\n".join(structure_rows) + "\n\\bottomrule\n"
    )
    (RESULTS / "donor_summary_rows.tex").write_text(
        "\n".join(donor_tex_rows) + "\n\\bottomrule\n"
    )


def main() -> None:
    _style()
    payload = _load_json(RESULTS / "combined_matrix.json")
    make_rmse_figure(payload)
    make_improvement_figure(payload)
    make_graph_anatomy_figure()
    make_similarity_figure()
    make_transfer_summary_figure(payload)
    write_native_foreign_summary(payload)
    write_tex_tables(payload)


if __name__ == "__main__":
    main()
