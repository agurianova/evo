#!/usr/bin/env python3
"""Frontier fitness over the run plus the champion's mutation path.

Shares palette, fonts and figure width with make_tree_figure.py. The frontier
fill brightens with each improvement; the champion path reuses the tree
figure's node styling.

Usage:
    python make_frontier_figure.py [--max-iter 50]
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize

from make_tree_figure import CMAP, GREY, build_topology, load, style, valid

RUN_DIR = Path(__file__).resolve().parent

FIG_W, FIG_H = 5.5, 2.45
Y_LIM = (0.0935, 0.1495)

FRONTIER_EDGE = "#2a3c58"
FRONTIER_FILL = "#d4d8dc"   # light grey
LEADER = "#c6c9cb"
CHAMPION_LW = 2.35     # trunk-like weight from the tree figure

# mutation essence — only the two breakthrough hops
MUTATIONS = {
    "4739dbe3": "PDB contacts",
    "02c72044": "surface traces",
}

# (dx in iterations, dy in fitness) — tag sits just beside the node
TAG_OFFSET = {
    "883150c2": (0.45, 0.0032),
    "dc066b87": (0.45, -0.0040),
    "c81fdde2": (0.45, 0.0030),
    "90914635": (0.45, -0.0038),
    "cfeca5d3": (0.45, -0.0035),
    "4739dbe3": (0.55, 0.0045),
    "02c72044": (0.55, 0.0048),
}

HALO = [pe.withStroke(linewidth=1.3, foreground="white")]


def champion_chain(programs):
    by_id, _, root = build_topology(programs)
    best = max((p for p in programs if valid(p)), key=lambda p: p["fitness"])
    chain, node = [], best
    while node is not None:
        chain.append(node)
        node = by_id.get(node["parent"]) if node["parent"] else None
    chain.reverse()
    assert chain[0]["id"] == root
    return chain, best


def frontier(programs, max_iter: int):
    iterations = np.arange(max_iter + 1)
    best_so_far, running = [], -math.inf
    for it in iterations:
        for program in programs:
            if program["iteration"] == it and valid(program):
                running = max(running, program["fitness"])
        best_so_far.append(running)
    return iterations, np.array(best_so_far)


def frontier_jumps(iterations, curve):
    """(start_iter, end_iter, fitness) for each plateau — no merging."""
    jumps: list[tuple[float, float, float]] = []
    prev = -math.inf
    for t, f in zip(iterations, curve):
        if f > prev + 1e-9:
            if jumps:
                jumps[-1] = (jumps[-1][0], float(t), jumps[-1][2])
            jumps.append((float(t), float(iterations[-1]) + 0.5, float(f)))
            prev = f
    return jumps


def draw_gradient_frontier(ax, jumps, y0: float):
    """Step-wise fill: uniform pale-grey bands capped by a dark edge."""
    for t0, t1, fitness in jumps:
        ax.fill_between([t0, t1], y0, fitness, color=FRONTIER_FILL, alpha=0.48,
                        linewidth=0, zorder=1)
        ax.hlines(fitness, t0, t1, colors=FRONTIER_EDGE, linewidth=0.55,
                  alpha=0.72, zorder=3)


def densify_champion_path(chain, steps: int = 28):
    """Interpolate along the lineage so colour can flow smoothly."""
    xs, ys, fits = [], [], []
    for parent, child in zip(chain[:-1], chain[1:]):
        t = np.linspace(0.0, 1.0, steps, endpoint=False)
        xs.extend(parent["iteration"] + t * (child["iteration"] - parent["iteration"]))
        ys.extend(parent["fitness"] + t * (child["fitness"] - parent["fitness"]))
        fits.extend(parent["fitness"] + t * (child["fitness"] - parent["fitness"]))
    xs.append(chain[-1]["iteration"])
    ys.append(chain[-1]["fitness"])
    fits.append(chain[-1]["fitness"])
    return np.column_stack([xs, ys]), np.asarray(fits)


def draw_champion_path(ax, chain, norm):
    """Fitness-coloured ribbon with smooth hue transitions between hops."""
    points, fitness = densify_champion_path(chain)
    segments = np.stack([points[:-1], points[1:]], axis=1)
    ribbon = LineCollection(
        segments, cmap=CMAP, norm=norm, linewidth=CHAMPION_LW,
        capstyle="round", joinstyle="round", zorder=4,
    )
    ribbon.set_array(fitness[:-1])
    ax.add_collection(ribbon)


def label_frontier(ax, jumps):
    """Name the top edge of the final plateau."""
    t0, t1, fitness = jumps[-1]
    ax.text(t1 - 0.4, fitness + 0.0010, "frontier",
            fontsize=5.8, color=GREY, ha="right", va="bottom", zorder=6,
            path_effects=HALO)


def draw_champion_node(ax, program, norm, is_best: bool, is_seed: bool):
    x, y = program["iteration"], program["fitness"]
    face = CMAP(norm(program["fitness"]))
    if is_best:
        ax.scatter([x], [y], s=58, facecolors="none", edgecolors=face,
                   linewidths=1.0, zorder=5)
        ax.scatter([x], [y], s=34, facecolors=face, edgecolors="white",
                   linewidths=0.5, zorder=6)
    else:
        size = 26 if is_seed else 20
        ax.scatter([x], [y], s=size, facecolors=face, edgecolors="white",
                   linewidths=0.5, zorder=6)


def annotate_hop(ax, program):
    key = program["id"][:8]
    x, y = program["iteration"], program["fitness"]
    dx, dy = TAG_OFFSET[key]
    tx, ty = x + dx, y + dy
    va = "bottom" if dy >= 0 else "top"

    ax.text(tx, ty, program["tag"], ha="left", va=va, zorder=7,
            fontsize=4.8, color="#1a1a1a", fontweight="bold", path_effects=HALO)

    if key not in MUTATIONS:
        return

    side = 1 if dy >= 0 else -1
    ax.text(tx, ty + side * 0.0032, MUTATIONS[key], ha="left", va=va,
            fontsize=5.6, color=GREY, style="italic", zorder=7, path_effects=HALO)
    ax.plot([x, tx], [y, ty], color=LEADER, linewidth=0.4, zorder=2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-iter", type=int, default=50)
    args = parser.parse_args()

    style()
    programs = load(args.max_iter)
    chain, best = champion_chain(programs)
    iterations, curve = frontier(programs, args.max_iter)
    evaluated = sorted(
        (p for p in programs if valid(p)),
        key=lambda p: (p["iteration"], p["fitness"]),
    )
    norm = Normalize(vmin=min(p["fitness"] for p in evaluated),
                     vmax=max(p["fitness"] for p in evaluated))
    seed = chain[0]

    fig = plt.figure(figsize=(FIG_W, FIG_H))
    ax = fig.add_axes([0.088, 0.145, 0.895, 0.765])

    ax.set_xlim(-1.5, args.max_iter + 2.2)
    ax.set_ylim(*Y_LIM)
    ax.set_yticks([0.10, 0.11, 0.12, 0.13, 0.14, 0.15])
    ax.set_yticklabels([f"{t:.2f}" for t in ax.get_yticks()], fontsize=6.0)
    ax.set_xticks(range(0, args.max_iter + 1, 10))
    ax.tick_params(labelsize=6.0, length=2.2, width=0.5, pad=2.0, colors="#1a1a1a")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#b8bcc2")
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#e6e8ea", linewidth=0.45)
    ax.set_xlabel("iteration", fontsize=6.5, labelpad=2.0)
    ax.set_ylabel("fitness (macro-AUCPR)", fontsize=6.5, labelpad=3.0)

    jumps = frontier_jumps(iterations, curve)
    draw_gradient_frontier(ax, jumps, Y_LIM[0])
    label_frontier(ax, jumps)

    ax.plot([p["iteration"] for p in evaluated],
            [p["fitness"] for p in evaluated],
            color=GREY, linewidth=0.55, linestyle=(0, (1.4, 2.2)),
            alpha=0.42, zorder=2)
    ax.scatter([p["iteration"] for p in evaluated],
               [p["fitness"] for p in evaluated],
               s=6.5, c=[CMAP(norm(p["fitness"])) for p in evaluated],
               alpha=0.50, linewidths=0.0, zorder=2)

    draw_champion_path(ax, chain, norm)

    for program in chain:
        is_best = program["id"] == best["id"]
        is_seed = program["id"] == seed["id"]
        draw_champion_node(ax, program, norm, is_best, is_seed)
        annotate_hop(ax, program)

    ax.annotate("evaluated programs", xy=(44.0, 0.1180), xytext=(49.0, 0.1255),
                fontsize=5.6, color=GREY, ha="right", va="bottom", zorder=6,
                path_effects=HALO,
                arrowprops=dict(arrowstyle="-", color=LEADER, linewidth=0.4,
                                shrinkA=1.5, shrinkB=1.5))

    fig.text(0.088, 0.985,
             f"Frontier fitness and champion path, iterations 0\u2013{args.max_iter}",
             fontsize=6.8, color=GREY, va="top")

    stem = RUN_DIR / f"fig_frontier_champion_0_{args.max_iter}"
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(stem.with_suffix(".png"), dpi=600)
    with mpl.rc_context({"svg.fonttype": "path"}):
        fig.savefig(stem.with_suffix(".svg"))
    fig.savefig(stem.with_name(f"{stem.name}_editable.svg"))
    plt.close(fig)

    print(f"programs={len(programs)} valid={len(evaluated)} hops={len(chain)} "
          f"frontier_jumps={len(jumps)} seed={seed['fitness']:.4f} "
          f"best={best['tag']} iter={best['iteration']}")
    print(stem.with_suffix(".pdf"))
    print(stem.with_suffix(".svg"))


if __name__ == "__main__":
    main()
