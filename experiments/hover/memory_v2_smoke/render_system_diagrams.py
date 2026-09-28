#!/usr/bin/env python3
"""Render the memory-v2 architecture diagrams used by the technical report."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

INK = "#17202a"
CONTENT = "#26734d"
DECISION = "#3264a8"
EVIDENCE = "#b06432"
SAFETY = "#a23b3b"
NEUTRAL = "#667085"
PALE = "#f5f7fa"


def _canvas(width: float, height: float, title: str):
    fig, ax = plt.subplots(figsize=(width, height), constrained_layout=True)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_axis_off()
    ax.set_title(title, fontsize=18, color=INK, pad=16)
    return fig, ax


def _box(ax, x, y, w, h, text, *, color, fontsize=10, linewidth=1.5):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.35,rounding_size=1.2",
        facecolor="white",
        edgecolor=color,
        linewidth=linewidth,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=INK,
        wrap=True,
    )
    return patch


def _arrow(ax, start, end, *, color=NEUTRAL, text="", bend=0.0, style="-|>"):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle=style,
        mutation_scale=13,
        linewidth=1.5,
        color=color,
        connectionstyle=f"arc3,rad={bend}",
    )
    ax.add_patch(arrow)
    if text:
        x = (start[0] + end[0]) / 2
        y = (start[1] + end[1]) / 2 + 2.2
        ax.text(x, y, text, ha="center", va="center", fontsize=8.5, color=color)


def _lane(ax, y, h, label, color):
    ax.add_patch(
        FancyBboxPatch(
            (0.5, y),
            99,
            h,
            boxstyle="round,pad=0.2,rounding_size=1.0",
            facecolor=PALE,
            edgecolor="#d9dee7",
            linewidth=0.8,
        )
    )
    ax.text(2, y + h - 3, label, fontsize=10, weight="bold", color=color, va="top")


def render_architecture(path: Path) -> None:
    fig, ax = _canvas(17, 10, "Memory v2: content, decision, and evidence planes")
    _lane(ax, 67, 29, "CONTENT PLANE (v1 machinery retained)", CONTENT)
    _lane(ax, 35, 29, "DECISION PLANE (v2 Bayesian policy)", DECISION)
    _lane(ax, 3, 29, "EVIDENCE PLANE (v2 causal source of truth)", EVIDENCE)

    _box(ax, 5, 75, 13, 10, "Completed\nparent-child diff", color=CONTENT)
    _box(ax, 23, 75, 14, 10, "LLM librarian\nauthor / reconcile", color=CONTENT)
    _box(ax, 42, 75, 14, 10, "Admission, dedup,\nconsolidation", color=CONTENT)
    _box(ax, 62, 75, 13, 10, "Card bank\nactive cap = 32", color=CONTENT)
    _box(ax, 81, 75, 14, 10, "Program exemplars\nand insight cards", color=CONTENT)
    _arrow(ax, (18, 80), (23, 80), color=CONTENT)
    _arrow(ax, (37, 80), (42, 80), color=CONTENT)
    _arrow(ax, (56, 80), (62, 80), color=CONTENT)
    _arrow(ax, (75, 80), (81, 80), color=CONTENT, style="<->")

    _box(ax, 4, 43, 14, 11, "Fresh parent +\nMAP-Elites context", color=DECISION)
    _box(
        ax,
        22,
        43,
        14,
        11,
        "Whole eligible bank\n(no semantic prefilter)",
        color=DECISION,
    )
    _box(ax, 40, 43, 14, 11, "Audited card\nsnapshots", color=DECISION)
    _box(
        ax,
        58,
        43,
        15,
        11,
        "Hierarchical reward +\ninvalidity posterior",
        color=DECISION,
    )
    _box(
        ax,
        77,
        43,
        18,
        11,
        "Safe probability matching\nthen 0.5 offer/withhold",
        color=DECISION,
    )
    _arrow(ax, (18, 48.5), (22, 48.5), color=DECISION)
    _arrow(ax, (36, 48.5), (40, 48.5), color=DECISION)
    _arrow(ax, (54, 48.5), (58, 48.5), color=DECISION)
    _arrow(ax, (73, 48.5), (77, 48.5), color=DECISION)
    _arrow(
        ax, (68.5, 75), (29, 54), color=CONTENT, text="atomic bank snapshot", bend=0.12
    )

    _box(ax, 4, 11, 14, 11, "Decision committed\nbefore exposure", color=EVIDENCE)
    _box(ax, 23, 11, 14, 11, "One card delivered\nor withheld control", color=EVIDENCE)
    _box(ax, 42, 11, 14, 11, "Child linked +\nterminal outcome", color=EVIDENCE)
    _box(ax, 61, 11, 14, 11, "SQLite causal ledger\nimmutable hashes", color=EVIDENCE)
    _box(ax, 80, 11, 15, 11, "Fresh refit +\nconservative retirement", color=EVIDENCE)
    _arrow(ax, (18, 16.5), (23, 16.5), color=EVIDENCE)
    _arrow(ax, (37, 16.5), (42, 16.5), color=EVIDENCE)
    _arrow(ax, (56, 16.5), (61, 16.5), color=EVIDENCE)
    _arrow(ax, (75, 16.5), (80, 16.5), color=EVIDENCE)
    _arrow(
        ax,
        (86, 43),
        (11, 22),
        color=DECISION,
        text="proposal + exact probabilities",
        bend=-0.13,
    )
    _arrow(ax, (68, 22), (65, 43), color=EVIDENCE, text="terminal evidence", bend=0.08)
    _arrow(
        ax,
        (88, 22),
        (50, 75),
        color=EVIDENCE,
        text="evict only after revalidation",
        bend=0.18,
    )

    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)


def render_posterior(path: Path) -> None:
    fig, ax = _canvas(17, 9.5, "Card posterior: minimal hierarchy and hurdle utility")
    _box(
        ax,
        3,
        70,
        19,
        15,
        "Minimal context x\nfitness, progress, stable\nMAP coordinates",
        color=DECISION,
        fontsize=9.5,
    )
    _box(
        ax,
        28,
        70,
        19,
        15,
        "Card identity j\nstable bank treatment +\nexact content snapshot",
        color=CONTENT,
        fontsize=9.5,
    )
    _box(
        ax,
        53,
        70,
        19,
        15,
        r"Delivered-card action $A$"
        + "\n"
        + r"control $=0$"
        + "\n"
        + r"treated $=1$,  offer $e=0.5$",
        color=EVIDENCE,
        fontsize=9.5,
    )
    _box(
        ax,
        78,
        70,
        19,
        15,
        "Design vector z(x,j,A)\nshared context + card\ndeviation",
        color=NEUTRAL,
        fontsize=9.5,
    )
    _arrow(ax, (22, 77.5), (28, 77.5), color=DECISION)
    _arrow(ax, (47, 77.5), (53, 77.5), color=CONTENT)
    _arrow(ax, (72, 77.5), (78, 77.5), color=EVIDENCE)

    _box(
        ax,
        10,
        38,
        34,
        20,
        "VALID-GAIN MODEL (valid terminals only)\n"
        + r"$Y \sim N(z^T\beta,\;\sigma^2+s_i^2)$"
        + "\nfixed hierarchical Gaussian priors\n"
        + r"$\log\sigma \sim N(\log 0.20,0.75^2)$"
        + "\nadaptive 1-D scale integration",
        color=DECISION,
        fontsize=10,
    )
    _box(
        ax,
        56,
        38,
        34,
        20,
        "INVALIDITY MODEL (all terminals)\n"
        + r"$D \sim Bernoulli(logit^{-1}(z^T\gamma))$"
        + "\nproper hierarchical Gaussian priors\n"
        + r"intercept mean $=logit(0.05)$"
        + "\nMAP + Laplace covariance",
        color=SAFETY,
        fontsize=10,
    )
    _arrow(ax, (87.5, 70), (73, 58), color=NEUTRAL, bend=0.05)
    _arrow(ax, (87.5, 70), (27, 58), color=NEUTRAL, bend=-0.08)

    _box(
        ax,
        26,
        8,
        48,
        19,
        r"HURDLE UTILITY: $q_a=(1-p_a)v_a+p_aL_x$"
        + "\n"
        + r"$v_a=clip(E[Y_a],L_x,U_x)$,  $\Delta_j=q_1-q_0$"
        + "\ninvalidity receives the parent's worst feasible gain"
        + "\nposterior worlds preserve cross-card correlation",
        color=EVIDENCE,
        fontsize=11,
    )
    _arrow(ax, (27, 38), (42, 27), color=DECISION)
    _arrow(ax, (73, 38), (58, 27), color=SAFETY)
    ax.text(
        50,
        2.5,
        "K=3 behavior axes, B stable card treatments: dimension = 12 + 5B; empty-bank smoke starts B=0",
        ha="center",
        va="center",
        fontsize=9,
        color=NEUTRAL,
    )

    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)


def render_selection(path: Path) -> None:
    fig, ax = _canvas(18, 10, "How one card is selected for one parent program")
    stages = [
        (2, "1. Active mutation\nattempt"),
        (18, "2. Freeze parent +\nMAP context"),
        (34, "3. Same-task bank +\nlineage exclusion"),
        (50, "4. Pending lineage\nbudget < 2"),
        (66, "5. Audited card\nsnapshots"),
        (82, "6. Fit posterior\non prior terminals"),
    ]
    for x, text in stages:
        _box(ax, x, 77, 14, 11, text, color=DECISION, fontsize=9)
    for left, right in zip(stages, stages[1:]):
        _arrow(ax, (left[0] + 14, 82.5), (right[0], 82.5), color=DECISION)

    _box(
        ax,
        6,
        49,
        20,
        15,
        "7. Safety certification\n" + r"$P(p_1\leq.25,\;p_1-p_0\leq.10)\geq.90$",
        color=SAFETY,
        fontsize=9.5,
    )
    _box(
        ax,
        31,
        49,
        20,
        15,
        "8. 512 shared worlds\ncard with largest positive\nusable effect wins each world",
        color=DECISION,
        fontsize=9.5,
    )
    _box(
        ax,
        56,
        49,
        19,
        15,
        r"9. Proposal mass $\rho_j$"
        + "\n"
        + r"$.95\,wins_j/512+.05/|S|$"
        + "\nabstention keeps .95 mass",
        color=DECISION,
        fontsize=9.5,
    )
    _box(
        ax,
        80,
        49,
        14,
        15,
        "10. Categorical draw\npropose one card\nor abstain",
        color=EVIDENCE,
        fontsize=9.5,
    )
    _arrow(ax, (89, 77), (16, 64), color=DECISION, bend=-0.12)
    _arrow(ax, (26, 56.5), (31, 56.5), color=SAFETY)
    _arrow(ax, (51, 56.5), (56, 56.5), color=DECISION)
    _arrow(ax, (75, 56.5), (80, 56.5), color=DECISION)

    _box(
        ax,
        2,
        15,
        18,
        14,
        "ABSTAIN\n" + r"leaf mass $\rho_0$" + "\nno proposal",
        color=NEUTRAL,
    )
    _box(
        ax,
        29,
        15,
        18,
        14,
        "PROPOSE CARD j\n" + r"probability $\rho_j$" + "\nlease both arms",
        color=EVIDENCE,
    )
    _box(
        ax,
        56,
        15,
        18,
        14,
        "DELIVER\n" + r"$e=0.5$" + "\n" + r"joint $\rho_j e$",
        color=CONTENT,
    )
    _box(
        ax,
        80,
        15,
        18,
        14,
        "WITHHOLD CONTROL\n" + r"$1-e=0.5$" + "\n" + r"joint $\rho_j(1-e)$",
        color=SAFETY,
    )
    _arrow(
        ax, (87, 49), (11, 29), color=NEUTRAL, bend=-0.12, text="categorical abstain"
    )
    _arrow(
        ax, (87, 49), (38, 29), color=EVIDENCE, bend=-0.05, text="categorical card j"
    )
    _arrow(ax, (47, 22), (56, 22), color=CONTENT)
    _arrow(ax, (47, 22), (80, 22), color=SAFETY, bend=-0.11)
    ax.text(
        65,
        8,
        "Only DELIVER injects one card into the mutator. WITHHOLD still records the proposed stable treatment and keeps its lease pending.",
        ha="center",
        va="center",
        fontsize=9.5,
        color=INK,
    )

    fig.savefig(path, dpi=180, facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "docs" / "diagrams",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    render_architecture(args.output_dir / "memory_v2_architecture.png")
    render_posterior(args.output_dir / "memory_v2_posterior_hierarchy.png")
    render_selection(args.output_dir / "memory_v2_card_selection.png")
    print(args.output_dir)


if __name__ == "__main__":
    main()
