"""The capability figure: where along the funnel from "proposes a neighbour feature"
to "ships a valid supervised one" each replica actually got.

The funnel is the point. A run that never mentions neighbours failed at retrieval;
one that mentions and never builds failed at translation; one that builds and gets
rejected failed at the probe. Collapsing these into a single "did it do kNN" bar
would hide which death class is still live.

Usage: python make_neighbour_figure.py <arm-slug>[:<label>] ...
"""

import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).parent
VIZ = HERE / "viz"
COLORS = ["#1F4E79", "#C9720B", "#1A7F37"]
GRID = dict(alpha=0.25, linewidth=0.7)

STAGES = [
    ("mentions_neighbour", "proposes\nin prose"),
    ("with_aggregate", "uses the\naggregate ABI"),
    ("with_neighbour", "computes a\nneighbour feature"),
    ("with_supervised_neighbour", "supervised\n(target-aware)"),
    ("valid_with_neighbour", "survives the\nleakage probe"),
]


def main() -> None:
    specs = [a.split(":", 1) for a in sys.argv[1:]]
    arms = [json.loads((VIZ / f"{s[0]}_neighbour.json").read_text()) for s in specs]
    labels = [s[1] if len(s) > 1 else s[0] for s in specs]

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.6))
    n = len(arms)
    width = 0.8 / n

    for k, (nbr, label, color) in enumerate(zip(arms, labels, COLORS)):
        x = np.arange(len(STAGES)) + (k - (n - 1) / 2) * width
        vals = [nbr[key] for key, _ in STAGES]
        axes[0].bar(x, vals, width=width, color=color, label=label)
        for xi, v in zip(x, vals):
            axes[0].text(xi, v + 0.25, str(v), ha="center", fontsize=8.5)

        rows = nbr["programs_detail"]
        valid = [r for r in rows if r["is_valid"] == 1.0]
        axes[1].scatter(
            [r["generation"] for r in valid if not r["has_neighbour"]],
            [r["fitness"] for r in valid if not r["has_neighbour"]],
            s=16,
            color=color,
            alpha=0.30,
            linewidths=0,
        )
        hit = [r for r in valid if r["has_neighbour"]]
        axes[1].scatter(
            [r["generation"] for r in hit],
            [r["fitness"] for r in hit],
            s=95,
            facecolors="none",
            edgecolors=color,
            linewidths=1.8,
            label=f"{label} — neighbour genome",
        )

    axes[0].set_xticks(np.arange(len(STAGES)))
    axes[0].set_xticklabels([lab for _, lab in STAGES], fontsize=8.5)
    axes[0].set_ylabel("children")
    axes[0].set_title(
        "capability funnel — where each replica stopped", fontsize=11, fontweight="bold"
    )
    axes[0].legend(fontsize=8.5, loc="upper right")
    axes[1].set_xlabel("generation")
    axes[1].set_ylabel("CV R²")
    axes[1].set_title(
        "fitness of neighbour genomes against the rest",
        fontsize=11,
        fontweight="bold",
    )
    axes[1].legend(fontsize=8, loc="lower right")
    for ax in axes:
        ax.grid(axis="y", **GRID)
    fig.suptitle(
        "did the search reach a neighbour feature? — classified from each node's AST, "
        "not from its identifiers",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    out = HERE / "neighbour_funnel.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    main()
