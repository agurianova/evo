"""Held-out scores for the top of each run, not just its champion.

Selection ran against cross-validated R^2, so a champion's test RMSE is the score
of the winner of a ~100-way selection and carries that optimism. Scoring the whole
CV-top of each run out of sample answers the two questions the champion alone
cannot: does the CV ranking survive on held-out data (left), and is the gap between
the best neighbour genome and the best genome without one real off the CV split
(right)?

Usage: python make_test_panel_figure.py <arm-slug>[:<label>] ...
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


def main() -> None:
    specs = [a.split(":", 1) for a in sys.argv[1:]]
    arms = [json.loads((VIZ / f"{s[0]}_test.json").read_text()) for s in specs]
    labels = [s[1] if len(s) > 1 else s[0] for s in specs]

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 4.6))

    for arm, label, color in zip(arms, labels, COLORS):
        panel = arm["panel"]
        for marker, flag, name in (
            ("o", True, "neighbour"),
            ("s", False, "no neighbour"),
        ):
            rows = [r for r in panel if r["neighbour"] is flag]
            if not rows:
                continue
            axes[0].scatter(
                [r["cv_r2"] for r in rows],
                [r["test_rmse"] for r in rows],
                s=70,
                marker=marker,
                facecolors=color if flag else "none",
                edgecolors=color,
                linewidths=1.6,
                alpha=0.85,
                label=f"{label} — {name}",
            )
        axes[0].scatter(
            [arm["seed"]["cv_r2"]],
            [arm["seed"]["test_rmse"]],
            s=90,
            marker="x",
            color=color,
            linewidths=2.0,
        )

    seed_cv, seed_test = arms[0]["seed"]["cv_r2"], arms[0]["seed"]["test_rmse"]
    axes[0].axvline(seed_cv, color="#999999", lw=0.7, alpha=0.6)
    axes[0].axhline(seed_test, color="#999999", lw=0.7, alpha=0.6)
    axes[0].set_xlabel("cross-validated R² (what selection optimised)")
    axes[0].set_ylabel("held-out test RMSE (lower is better)")
    axes[0].set_title(
        "top-10 genomes per replica, scored on the untouched test split\n"
        "(× = seed; grey lines mark seed CV and RMSE)",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[0].legend(fontsize=7.5, loc="lower right", ncol=2)

    x = np.arange(len(arms))
    width = 0.36
    with_n = [a["best"]["test_rmse"] for a in arms]
    without_n = [
        a["best_no_neighbour"]["test_rmse"] if a["best_no_neighbour"] else np.nan
        for a in arms
    ]
    base = arms[0]["seed"]["test_rmse"]
    for xi, (a, b) in enumerate(zip(with_n, without_n)):
        color = COLORS[xi]
        axes[1].plot([xi - width / 2, xi + width / 2], [a, b], color=color, lw=1.2)
        axes[1].scatter(
            [xi - width / 2],
            [a],
            s=70,
            color=color,
            marker="o",
            zorder=3,
            label="best genome" if xi == 0 else None,
        )
        axes[1].scatter(
            [xi + width / 2],
            [b],
            s=70,
            facecolors="none",
            edgecolors=color,
            marker="s",
            linewidths=1.6,
            zorder=3,
            label="best genome with NO neighbour feature" if xi == 0 else None,
        )
        axes[1].text(xi - width / 2, a + 0.0013, f"{a:.4f}", ha="center", fontsize=8)
        if not np.isnan(b):
            axes[1].text(
                xi + width / 2, b + 0.0013, f"{b:.4f}", ha="center", fontsize=8
            )
    axes[1].axhline(base, color="#B42318", ls="--", lw=1.0, label=f"seed ({base:.4f})")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels)
    axes[1].set_ylabel("held-out test RMSE (lower is better)")
    axes[1].set_ylim(min(with_n + without_n) - 0.004, base + 0.006)
    axes[1].set_title(
        "does the capability, not just the run, carry the gain?",
        fontsize=10.5,
        fontweight="bold",
    )
    axes[1].legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 0.91))

    for ax in axes:
        ax.grid(axis="y", **GRID)
    fig.suptitle(
        "held-out evaluation — every score from problems.dag_tab.validate.score_on_test",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    out = HERE / "test_panel.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    main()
