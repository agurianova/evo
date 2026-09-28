"""Render the Sequential-Maze benchmark figures (landscapes, barrier trees,
shrinking-needle geometry, classical-optimizer breakdown, trajectories).

Run with the evo env python; writes PNGs into ./figs.
"""

from __future__ import annotations

import os

import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "8")

import matplotlib

matplotlib.use("Agg")
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt

from problems.sequential_landscape.benchmark import (
    _cma_method,
    gradient_descent,
    random_restart,
    scipy_basinhopping,
    scipy_differential_evolution,
)
from problems.sequential_landscape.specs import get_maze_ladder

HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.join(HERE, "figs")
os.makedirs(FIGS, exist_ok=True)

INK = "#0d1117"
PANEL = "#11161d"
FG = "#e6edf3"
MUTED = "#8b949e"
GOLD = "#ffd23f"
CYAN = "#38e8d8"
RED = "#ff5c66"
GRID = "#222a35"

plt.rcParams.update(
    {
        "figure.facecolor": INK,
        "axes.facecolor": PANEL,
        "savefig.facecolor": INK,
        "text.color": FG,
        "axes.labelcolor": FG,
        "axes.edgecolor": GRID,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.titlecolor": FG,
        "font.size": 12,
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "font.family": "DejaVu Sans",
    }
)

# value map for log(f - f*): bright canyon floor -> visible deep-indigo walls
# (high end is NOT black, so the off-canyon field stays a legible gradient)
LOGMAP = LinearSegmentedColormap.from_list(
    "logf",
    ["#eafff8", "#7bf0e0", "#2bb6c4", "#1f6f9c", "#2a3f73", "#1a2347"],
)

# ----------------------------------------------------------------------------- #
# verified seed-averaged certification table (gate.py, SEEDS=(0,1,2))
SCORES = {
    "maze_easy": {
        "random": 0.08,
        "gradient": 0.21,
        "basinhop": 0.33,
        "diff_evo": 0.00,
        "cma_es": 0.04,
        "oracle": 1.00,
        "gap": 0.67,
    },
    "maze_medium": {
        "random": 0.07,
        "gradient": 0.00,
        "basinhop": 0.30,
        "diff_evo": 0.00,
        "cma_es": 0.00,
        "oracle": 1.00,
        "gap": 0.70,
    },
    "maze_hard": {
        "random": 0.03,
        "gradient": 0.07,
        "basinhop": 0.27,
        "diff_evo": 0.03,
        "cma_es": 0.13,
        "oracle": 1.00,
        "gap": 0.73,
    },
    "maze_insane": {
        "random": 0.03,
        "gradient": 0.08,
        "basinhop": 0.08,
        "diff_evo": 0.00,
        "cma_es": 0.06,
        "oracle": 1.00,
        "gap": 0.92,
    },
}
DIMS = {"maze_easy": 7, "maze_medium": 8, "maze_hard": 10, "maze_insane": 12}


def eval_grid(ls, X, Y):
    """Vectorised f over the (x0,x1) plane with all nuisance dims = 0."""
    P = np.stack([X.ravel(), Y.ravel()], axis=1)
    A, B = ls._A, ls._B
    ab = B - A
    abab = (ab * ab).sum(1)
    M = len(P)
    best_d2 = np.full(M, np.inf)
    best_seg = np.zeros(M, int)
    best_t = np.zeros(M)
    for j in range(len(A)):
        d = P - A[j]
        t = np.clip((d * ab[j]).sum(1) / abab[j], 0.0, 1.0)
        foot = A[j] + t[:, None] * ab[j]
        d2 = ((P - foot) ** 2).sum(1)
        m = d2 < best_d2
        best_d2[m] = d2[m]
        best_seg[m] = j
        best_t[m] = t[m]
    s = ls._s0[best_seg] + best_t * ls._L[best_seg]
    ei = ls._edge[best_seg]
    floor = np.empty(M)
    stiff = np.empty(M)
    for e_idx in np.unique(ei):
        mask = ei == e_idx
        e = ls._edges[e_idx]
        floor[mask] = e["pchip"](s[mask])
        stiff[mask] = ls._stiffness(e["depth"])
    f = floor + stiff * best_d2  # the true landscape value over the slice
    return f.reshape(X.shape)


def _path_child_ids(ls):
    return set(ls._global.path[1:])


def landscape_panel(ax, ls, res=460, show_paths=True):
    pts = np.vstack([e["pts"] for e in ls._edges])
    pad = ls.spec.lane_base * 0.9
    xlo, xhi = pts[:, 0].min() - pad, pts[:, 0].max() + pad
    ylo, yhi = pts[:, 1].min() - pad, pts[:, 1].max() + pad
    gx = np.linspace(xlo, xhi, res)
    gy = np.linspace(ylo, yhi, res)
    X, Y = np.meshgrid(gx, gy)
    f = eval_grid(ls, X, Y)

    # log color scale of the true value above the global: the canyon floor is
    # the bright low end; off-canyon f climbs smoothly as 1/r² per depth level,
    # so the whole field is a legible gradient (no black void) under a colorbar.
    floor_min = float(ls.global_min_value)
    z = f - floor_min + 1.0  # >= 1 everywhere; log-safe
    im = ax.imshow(
        z,
        origin="lower",
        extent=[xlo, xhi, ylo, yhi],
        aspect="auto",
        interpolation="bilinear",
        cmap=LOGMAP,
        norm=LogNorm(vmin=1.0, vmax=float(z.max())),
    )

    if show_paths:
        path_ids = _path_child_ids(ls)
        for e in ls._edges:
            on_path = e["child"] in path_ids
            ax.plot(
                e["pts"][:, 0],
                e["pts"][:, 1],
                color=GOLD if on_path else "#0b1020",
                lw=2.6 if on_path else 1.0,
                alpha=0.95 if on_path else 0.55,
                ls="-" if on_path else (0, (4, 3)),
                zorder=3,
                path_effects=[pe.withStroke(linewidth=4.4, foreground="#06101c")]
                if on_path
                else None,
            )
        leaves = [n for n in ls._nodes if n.is_leaf]
        for n in leaves:
            if n is ls._global:
                ax.scatter(
                    n.x,
                    n.y,
                    s=320,
                    marker="*",
                    color=GOLD,
                    edgecolors="#000",
                    linewidths=1.0,
                    zorder=6,
                )
            else:
                ax.scatter(
                    n.x,
                    n.y,
                    s=70,
                    marker="X",
                    color=RED,
                    edgecolors="#000",
                    linewidths=0.7,
                    zorder=5,
                )
    ax.set_xticks([])
    ax.set_yticks([])
    return im


# ----------------------------------------------------------------------------- #
def _add_colorbar(fig, ax, im, label="value above global   f − f*  (log)"):
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02, extend="max")
    cb.set_label(label, color=FG, fontsize=11)
    cb.ax.yaxis.set_tick_params(color=MUTED, labelcolor=MUTED)
    cb.outline.set_edgecolor(GRID)
    return cb


def fig_hero():
    ls = get_maze_ladder()[0].landscape()  # maze_easy
    fig, ax = plt.subplots(figsize=(11.6, 9))
    im = landscape_panel(ax, ls, res=560)
    ax.set_title(
        "Sequential-Maze landscape  ·  maze_easy  (2-D slice of a 7-D problem)",
        pad=14,
    )
    _add_colorbar(fig, ax, im)
    handles = [
        Line2D([0], [0], color=GOLD, lw=3, label="true root→global canyon"),
        Line2D(
            [0], [0], color="#0b1020", lw=1.5, ls=(0, (4, 3)), label="decoy branches"
        ),
        Line2D(
            [0],
            [0],
            marker="*",
            color=GOLD,
            lw=0,
            markersize=16,
            markeredgecolor="#000",
            label="global minimum (the needle)",
        ),
        Line2D(
            [0],
            [0],
            marker="X",
            color=RED,
            lw=0,
            markersize=10,
            markeredgecolor="#000",
            label="deceptively-deep decoys",
        ),
    ]
    leg = ax.legend(
        handles=handles,
        loc="upper right",
        frameon=True,
        facecolor=PANEL,
        edgecolor=GRID,
        fontsize=11,
    )
    for t in leg.get_texts():
        t.set_color(FG)
    ax.text(
        0.012,
        0.012,
        "color = f − f* on a log scale (bright = the deep samplable floor). Off the\n"
        "canyon, f climbs as 1/r² per depth level — the smooth dark gradient. The gold\n"
        "path is the unique root→global route; its basin narrows to a needle (fig 4).",
        transform=ax.transAxes,
        fontsize=10.5,
        color=MUTED,
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.4", fc=INK, ec=GRID, alpha=0.85),
    )
    fig.tight_layout()
    p = os.path.join(FIGS, "01_hero_landscape.png")
    fig.savefig(p, dpi=145)
    plt.close(fig)
    return p


def fig_landscape_grid():
    ladder = get_maze_ladder()
    fig, axes = plt.subplots(2, 2, figsize=(15.5, 13))
    im = None
    for ax, inst in zip(axes.ravel(), ladder):
        ls = inst.landscape()
        im = landscape_panel(ax, ls, res=380)
        ax.set_title(
            f"{inst.name}   (dim {ls.dim}, {ls.num_minima} basins, "
            f"path depth {len(ls.true_path_points()) - 1})",
            fontsize=13,
        )
        _add_colorbar(fig, ax, im, label="f − f*  (log)")
    fig.suptitle(
        "The difficulty ladder — winding canyons branch, lengthen and "
        "narrow as dimension climbs",
        fontsize=17,
        fontweight="bold",
        y=0.995,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    p = os.path.join(FIGS, "02_ladder_landscapes.png")
    fig.savefig(p, dpi=135)
    plt.close(fig)
    return p


def _layout_tree(ls):
    """x = leaf order midpoints; y = node value (saddle height / basin depth)."""
    leaves = [n for n in ls._nodes if n.is_leaf]
    order = {}
    c = [0]

    def walk(n):
        if n.is_leaf:
            order[n.id] = c[0]
            c[0] += 1
        else:
            for k in n.children:
                walk(ls._nodes[k])
            order[n.id] = float(np.mean([order[k] for k in n.children]))

    walk(ls._nodes[0])
    return order, leaves


def tree_panel(ax, ls, title):
    order, leaves = _layout_tree(ls)
    path_ids = set(ls._global.path)
    for n in ls._nodes:
        if n.parent < 0:
            continue
        p = ls._nodes[n.parent]
        on = (n.id in path_ids) and (p.id in path_ids)
        x0, y0 = order[p.id], p.value
        x1, y1 = order[n.id], n.value
        ax.plot(
            [x0, x0, x1],
            [y0, y1, y1],
            color=GOLD if on else MUTED,
            lw=2.6 if on else 1.1,
            alpha=0.95 if on else 0.55,
            zorder=2,
            solid_capstyle="round",
        )
    for n in leaves:
        if n is ls._global:
            ax.scatter(
                order[n.id],
                n.value,
                s=210,
                marker="*",
                color=GOLD,
                edgecolors="#000",
                linewidths=0.8,
                zorder=4,
            )
        else:
            ax.scatter(
                order[n.id],
                n.value,
                s=46,
                marker="X",
                color=RED,
                edgecolors="#000",
                linewidths=0.5,
                zorder=3,
            )
    ax.set_title(title, fontsize=12.5)
    ax.set_ylabel("energy")
    ax.set_xticks([])
    ax.grid(axis="y", color=GRID, lw=0.6, alpha=0.5)
    ax.invert_yaxis()


def fig_trees():
    ladder = get_maze_ladder()
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    for ax, inst in zip(axes.ravel(), ladder):
        tree_panel(ax, inst.landscape(), inst.name)
    handles = [
        Line2D([0], [0], color=GOLD, lw=3, label="root→global path"),
        Line2D([0], [0], color=MUTED, lw=1.5, label="decoy sub-trees"),
        Line2D(
            [0],
            [0],
            marker="*",
            color=GOLD,
            lw=0,
            markersize=15,
            markeredgecolor="#000",
            label="global minimum",
        ),
        Line2D(
            [0],
            [0],
            marker="X",
            color=RED,
            lw=0,
            markersize=9,
            markeredgecolor="#000",
            label="decoy basins",
        ),
    ]
    leg = fig.legend(
        handles=handles,
        loc="lower center",
        ncol=4,
        frameon=True,
        facecolor=PANEL,
        edgecolor=GRID,
        bbox_to_anchor=(0.5, -0.02),
    )
    for t in leg.get_texts():
        t.set_color(FG)
    fig.suptitle(
        "Barrier trees (disconnectivity graphs) — the global sits behind "
        "the deepest, longest chain of saddles",
        fontsize=16,
        fontweight="bold",
        y=1.0,
    )
    fig.tight_layout(rect=[0, 0.02, 1, 0.97])
    p = os.path.join(FIGS, "03_barrier_trees.png")
    fig.savefig(p, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return p


def fig_shrinking():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    ladder = get_maze_ladder()
    cmap = [GOLD, CYAN, "#a78bfa", RED]
    for inst, col in zip(ladder, cmap):
        ls = inst.landscape()
        radii = ls.tube_radius_by_depth()
        ax1.plot(
            range(len(radii)),
            radii,
            "-o",
            color=col,
            lw=2.2,
            markersize=6,
            label=f"{inst.name} (dim {ls.dim})",
        )
    ax1.set_yscale("log")
    ax1.set_xlabel("tree depth (basin index along the canyon)")
    ax1.set_ylabel("samplable tube radius  (log)")
    ax1.set_title("Shrinking needle: tube radius decays geometrically")
    ax1.grid(color=GRID, lw=0.6, alpha=0.6)
    leg = ax1.legend(facecolor=PANEL, edgecolor=GRID, fontsize=10)
    for t in leg.get_texts():
        t.set_color(FG)

    # volume-vs-path scaling: P(hit basin d by sampling) ~ r^(dim) vs sequential O(1)
    depths = np.arange(0, 12)
    for D, col in [(7, GOLD), (10, "#a78bfa"), (12, RED)]:
        r = 0.5**depths
        vol = r**D
        ax2.plot(
            depths,
            vol,
            "-o",
            color=col,
            lw=2.2,
            markersize=5,
            label=f"random hit-prob, dim={D}  (∝ r^{D})",
        )
    ax2.plot(
        depths,
        np.ones_like(depths, float),
        "--",
        color=CYAN,
        lw=2.4,
        label="sequential follower  (O(1) per basin)",
    )
    ax2.set_yscale("log")
    ax2.set_xlabel("basin depth along the path")
    ax2.set_ylabel("relative cost to reach the basin  (log)")
    ax2.set_title("Why blind search dies: volume collapses, the path does not")
    ax2.grid(color=GRID, lw=0.6, alpha=0.6)
    leg2 = ax2.legend(facecolor=PANEL, edgecolor=GRID, fontsize=10)
    for t in leg2.get_texts():
        t.set_color(FG)
    fig.suptitle(
        "Measure-zero geometry — the core reason off-the-shelf "
        "optimizers cannot solve the maze",
        fontsize=16,
        fontweight="bold",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    p = os.path.join(FIGS, "04_shrinking_needle.png")
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p


def fig_scores():
    names = list(SCORES.keys())
    methods = ["random", "gradient", "basinhop", "diff_evo", "cma_es"]
    mcol = {
        "random": "#5b6673",
        "gradient": "#7c8aa0",
        "basinhop": CYAN,
        "diff_evo": "#a78bfa",
        "cma_es": "#ff8c42",
    }
    fig, ax = plt.subplots(figsize=(14, 7))
    n = len(methods) + 1
    w = 0.8 / n
    idx = np.arange(len(names))
    for k, m in enumerate(methods):
        vals = [SCORES[nm][m] for nm in names]
        ax.bar(idx + k * w, vals, w, color=mcol[m], label=m, edgecolor=INK, lw=0.5)
    vals = [SCORES[nm]["oracle"] for nm in names]
    ax.bar(
        idx + len(methods) * w,
        vals,
        w,
        color=GOLD,
        label="oracle (privileged)",
        edgecolor=INK,
        lw=0.5,
    )
    ax.axhline(1.0, color=GOLD, lw=1.0, ls=":", alpha=0.6)
    ax.set_xticks(idx + 0.4 - w / 2)
    ax.set_xticklabels([f"{nm}\n(dim {DIMS[nm]})" for nm in names], fontsize=12)
    ax.set_ylabel("path progress  (0 = stuck at first basin, 1 = global reached)")
    ax.set_ylim(0, 1.08)
    ax.set_title(
        "Classical optimizers vs the privileged oracle  (progress, mean over seeds 0–2)"
    )
    for nm, x in zip(names, idx):
        ax.annotate(
            f"gap {SCORES[nm]['gap']:.2f}",
            (x + 0.32, 1.012),
            ha="center",
            color=GOLD,
            fontsize=11,
            fontweight="bold",
        )
    ax.grid(axis="y", color=GRID, lw=0.6, alpha=0.5)
    leg = ax.legend(
        facecolor=PANEL,
        edgecolor=GRID,
        ncol=3,
        fontsize=11,
        loc="center",
        bbox_to_anchor=(0.5, 0.6),
    )
    for t in leg.get_texts():
        t.set_color(FG)
    fig.tight_layout()
    p = os.path.join(FIGS, "05_optimizer_breakdown.png")
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p


def fig_trajectories():
    inst = get_maze_ladder()[0]
    ls = inst.landscape()
    budget = inst.budget
    fig, ax = plt.subplots(figsize=(11.6, 9))
    im = landscape_panel(ax, ls, res=520, show_paths=True)
    _add_colorbar(fig, ax, im)
    runners = [
        ("diff_evo", scipy_differential_evolution, "#a78bfa"),
        ("cma_es", _cma_method(), "#ff8c42"),
        ("basinhop", scipy_basinhopping, CYAN),
        ("gradient", gradient_descent, "#7c8aa0"),
        ("random", random_restart, "#5b6673"),
    ]
    handles = []
    for name, fn, col in runners:
        if fn is None:
            continue
        xs = []
        for s in (0, 1, 2):
            x = fn(ls, ls.bounds, budget, s)
            xs.append(x[:2])
        xs = np.array(xs)
        ax.scatter(
            xs[:, 0],
            xs[:, 1],
            s=150,
            marker="o",
            color=col,
            edgecolors="#000",
            linewidths=1.0,
            zorder=7,
        )
        prog = np.mean(
            [ls.progress(np.concatenate([p, np.zeros(ls.dim - 2)])) for p in xs]
        )
        handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                color=col,
                lw=0,
                markersize=11,
                markeredgecolor="#000",
                label=f"{name}  (best-of-seed lands, prog≈{prog:.2f})",
            )
        )
    handles.append(
        Line2D(
            [0],
            [0],
            marker="*",
            color=GOLD,
            lw=0,
            markersize=16,
            markeredgecolor="#000",
            label="global (oracle reaches, 1.00)",
        )
    )
    ax.set_title("Where the classics get stuck  ·  maze_easy", pad=14)
    leg = ax.legend(
        handles=handles,
        loc="upper left",
        facecolor=PANEL,
        edgecolor=GRID,
        fontsize=10.5,
    )
    for t in leg.get_texts():
        t.set_color(FG)
    fig.tight_layout()
    p = os.path.join(FIGS, "06_trajectories.png")
    fig.savefig(p, dpi=140)
    plt.close(fig)
    return p


if __name__ == "__main__":
    outs = [
        fig_hero(),
        fig_landscape_grid(),
        fig_trees(),
        fig_shrinking(),
        fig_scores(),
        fig_trajectories(),
    ]
    for o in outs:
        sz = os.path.getsize(o) / 1024
        print(f"wrote {o}  ({sz:.0f} KB)")
