#!/usr/bin/env python3
"""Two-panel NeurIPS figure: lineage tree (A) + MAP-Elites archive (B).

Both panels share one fitness colour scale. The figure is exactly one
\\textwidth wide; panel A keeps equal aspect, so its width follows from the
shape of the tree and panel B takes the rest with square cells.

Panel A geometry: a leaf-weighted polar fan is sheared (`curl`, `twist`) and
every parent-child link is drawn as a Hermite ribbon whose start tangent is
the parent's growth direction. Tangent continuity at the joints, an upward
pull at the tips and per-node jitter are what make the lineage read as a
plant rather than a bundle of wires. See SHAPES for the presets.

Writes PDF (for LaTeX), PNG at 600 dpi and two SVGs (text as paths, and an
_editable copy with live text).

Usage:
    python make_tree_figure.py [--max-iter 50] [--style arch|umbel|spiral|all]
                               [--plain]
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import json
import math
from pathlib import Path
from zlib import crc32

import matplotlib as mpl

mpl.use("Agg")
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Polygon, Rectangle
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np

RUN_DIR = Path(__file__).resolve().parent
PROGRAMS = RUN_DIR / "storage/pmhctcr/programs"

# problems/pmhctcr/behavior.py: ARCH_KIND_NAMES and compute_tier()
ARCH_LABELS = ("linear MLP", "modality attn.", "geometric", "interface attn.")
TIER_LABELS = (
    r"$10^{0}$",
    r"$10^{1}$",
    r"$10^{2}$",
    r"$10^{3}$",
    r"$10^{4}$",
    r"$\geq\!10^{5}$",
)

CMAP = LinearSegmentedColormap.from_list(
    "gigaevo",
    ["#1b1545", "#2a3c58", "#3f5c38", "#6f8c2c", "#b4d24e", "#d8f06a"],
)
GREY = "#5d5f66"

FIG_W, FIG_H = 5.5, 2.62  # \textwidth of the NeurIPS style, in inches
TREE_BOX_Y, TREE_BOX_H, TREE_BOX_MAX_W = 0.035, 0.90, 0.575
ARCHIVE_LABEL_GAP = 0.115  # room for panel B row labels
CBAR_X, CBAR_W, CBAR_H = 0.925, 0.013, 0.62
CBAR_GAP = 0.050


@dataclass(frozen=True)
class Shape:
    """Geometry of the lineage plant. Angles in radians, lengths in axes units."""

    fan_span: float  # angular opening of the canopy
    x_stretch: float
    y_stretch: float
    curl: float = 0.24  # outward shear, strongest at the canopy
    twist: float = 0.0  # one-directional shear, gives a spiral
    tip_curl: float = 0.18  # outward turn of each growth direction
    twist_turn: float = 0.0  # one-directional turn of growth directions
    up_pull: float = 0.78  # gravitropism: tips swing back towards vertical
    tangent: float = 0.95  # Hermite tangent length, in chord units
    depth_exp: float = 0.82  # <1 makes early segments longer than late ones
    root_radius: float = 0.20
    trunk_base: float = -0.145
    jitter_r: float = 0.032
    jitter_a: float = 0.034
    jitter_h: float = 0.14
    width_scale: float = 0.026
    width_floor: float = 0.18  # tip width as a fraction of the trunk
    margin: tuple = (0.12, 0.13, 0.04, 0.145)  # left, right, below, above


SHAPES = {
    # Arching side branches, tips lifted: shrub-like.
    "arch": Shape(
        fan_span=math.radians(130.0),
        x_stretch=1.24,
        y_stretch=1.18,
    ),
    # Wide umbel of thin rays that flick upwards: dill-like.
    "umbel": Shape(
        fan_span=math.radians(138.0),
        x_stretch=1.10,
        y_stretch=1.24,
        curl=0.46,
        tip_curl=0.06,
        up_pull=1.15,
        tangent=1.08,
        depth_exp=0.70,
        trunk_base=-0.115,
        width_scale=0.022,
        width_floor=0.14,
        jitter_h=0.11,
    ),
    # Everything sweeps one way: unfurling fiddlehead.
    "spiral": Shape(
        fan_span=math.radians(124.0),
        x_stretch=1.26,
        y_stretch=1.16,
        curl=0.10,
        twist=0.62,
        tip_curl=0.05,
        twist_turn=0.55,
        up_pull=0.45,
        tangent=1.00,
        jitter_h=0.10,
    ),
}


def style() -> None:
    mpl.rcParams.update(
        {
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "font.family": "STIXGeneral",
            "mathtext.fontset": "stix",
            "font.size": 7.0,
            "axes.linewidth": 0.5,
            "text.color": "#1a1a1a",
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def load(max_iter: int) -> list[dict]:
    programs = []
    for path in PROGRAMS.glob("*.json"):
        blob = json.loads(path.read_text())
        iteration = blob.get("iteration")
        if iteration is None or iteration > max_iter:
            continue
        metrics = blob.get("metrics") or {}
        lineage = blob.get("lineage") or {}
        programs.append(
            {
                "id": blob["id"],
                "tag": blob["id"][:4],
                "iteration": iteration,
                "generation": lineage.get("generation") or 0,
                "parents": lineage.get("parents") or [],
                "fitness": metrics.get("fitness"),
                "is_valid": metrics.get("is_valid"),
                "arch_kind": metrics.get("arch_kind"),
                "compute_tier": metrics.get("compute_tier"),
            }
        )
    return programs


def valid(program: dict) -> bool:
    fitness = program["fitness"]
    return program.get("is_valid") == 1.0 and fitness is not None and fitness > 0


def build_topology(programs: list[dict]):
    by_id = {p["id"]: p for p in programs}
    children: dict[str, list[str]] = defaultdict(list)
    roots: list[str] = []
    for program in programs:
        known = [p for p in program["parents"] if p in by_id]
        program["parent"] = known[0] if known else None
        if program["parent"]:
            children[program["parent"]].append(program["id"])
        else:
            roots.append(program["id"])
    for kids in children.values():
        kids.sort(key=lambda k: (by_id[k]["iteration"], k))
    roots.sort(key=lambda k: by_id[k]["iteration"])
    return by_id, children, roots[0]


def wiggle(node: str, salt: int) -> float:
    """Deterministic jitter in [-1, 1); keeps the figure reproducible."""
    return crc32(f"{node}:{salt}".encode()) / 2**31 - 1.0


def layout(children, root, shape: Shape):
    leaves: dict[str, int] = {}
    depth: dict[str, int] = {}

    def descend(node: str, level: int) -> int:
        depth[node] = level
        kids = children.get(node, [])
        leaves[node] = sum(descend(kid, level + 1) for kid in kids) or 1
        return leaves[node]

    descend(root, 0)
    max_depth = max(depth.values())

    angle: dict[str, float] = {}

    def spread(node: str, left: float, right: float) -> None:
        angle[node] = 0.5 * (left + right) + shape.jitter_a * wiggle(node, 1)
        cursor = left
        for kid in children.get(node, []):
            width = (leaves[kid] / leaves[node]) * (right - left)
            spread(kid, cursor, cursor + width)
            cursor += width

    spread(root, -shape.fan_span / 2, shape.fan_span / 2)
    angle[root] = 0.0

    def to_xy(radius: float, theta: float) -> tuple[float, float]:
        reach = max((radius - shape.root_radius) / (1.0 - shape.root_radius), 0.0)
        theta = theta + (shape.curl * math.sin(theta) + shape.twist) * reach**1.25
        return (
            shape.x_stretch * radius * math.sin(theta),
            shape.y_stretch * radius * math.cos(theta),
        )

    radius, position = {}, {}
    for node, level in depth.items():
        reach = (level / max_depth) ** shape.depth_exp
        grow = 1.0 + shape.jitter_r * wiggle(node, 2) * (1.0 if level else 0.0)
        radius[node] = shape.root_radius + (1.0 - shape.root_radius) * reach * grow
        position[node] = to_xy(radius[node], angle[node])

    # Growth direction per node: inherit the parent's heading, bend towards the
    # node's own chord, curl outwards, then swing back up as depth grows.
    heading = {root: (0.0, 1.0)}
    for node in sorted(depth, key=lambda n: depth[n]):
        hx, hy = heading[node]
        px, py = position[node]
        for kid in children.get(node, []):
            kx, ky = position[kid]
            cx, cy = kx - px, ky - py
            chord = math.hypot(cx, cy) or 1e-9
            dx, dy = 0.34 * hx + 0.66 * cx / chord, 0.34 * hy + 0.66 * cy / chord
            reach = (depth[kid] / max_depth) ** 0.7
            turn = (-shape.tip_curl * math.sin(angle[kid]) - shape.twist_turn) * reach
            turn += shape.jitter_h * wiggle(kid, 3)
            cos_t, sin_t = math.cos(turn), math.sin(turn)
            dx, dy = dx * cos_t - dy * sin_t, dx * sin_t + dy * cos_t
            dy += shape.up_pull * reach
            norm = math.hypot(dx, dy) or 1e-9
            heading[kid] = (dx / norm, dy / norm)
    return leaves, depth, angle, position, heading


def hermite(p0, p1, t0, t1, shape: Shape, n: int = 96):
    chord = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * shape.tangent
    s = np.linspace(0.0, 1.0, n)
    h00 = 2 * s**3 - 3 * s**2 + 1
    h10 = s**3 - 2 * s**2 + s
    h01 = -2 * s**3 + 3 * s**2
    h11 = s**3 - s**2
    xs = h00 * p0[0] + h10 * chord * t0[0] + h01 * p1[0] + h11 * chord * t1[0]
    ys = h00 * p0[1] + h10 * chord * t0[1] + h01 * p1[1] + h11 * chord * t1[1]
    return xs, ys


def _smooth(values: np.ndarray, window: int = 9) -> np.ndarray:
    if len(values) < window:
        return values
    kernel = np.hanning(window)
    kernel /= kernel.sum()
    return np.convolve(np.pad(values, window // 2, mode="edge"), kernel, mode="valid")


def ribbon(xs, ys, w_start: float, w_end: float) -> np.ndarray:
    """Tapered outline around a centreline, so branches thin out toward tips."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    widths = np.linspace(w_start, w_end, len(xs))
    dx, dy = np.gradient(xs), np.gradient(ys)
    norm = np.hypot(dx, dy)
    norm[norm < 1e-9] = 1e-9
    nx, ny = _smooth(-dy / norm), _smooth(dx / norm)
    unit = np.hypot(nx, ny)
    unit[unit < 1e-9] = 1e-9
    nx, ny = nx / unit, ny / unit
    left = np.column_stack([xs + nx * widths / 2, ys + ny * widths / 2])
    right = np.column_stack([xs - nx * widths / 2, ys - ny * widths / 2])
    return np.vstack([left, right[::-1]])


def tree_limits(position, shape: Shape):
    xs = [p[0] for p in position.values()]
    ys = [p[1] for p in position.values()]
    left, right, below, above = shape.margin
    return (min(xs) - left, max(xs) + right, shape.trunk_base - below, max(ys) + above)


def draw_tree(
    ax,
    programs,
    by_id,
    children,
    root,
    best,
    leaves,
    angle,
    position,
    heading,
    norm,
    shape: Shape,
):
    def colour(program, alpha=1.0):
        rgb = (
            np.array(to_rgb(GREY))
            if not valid(program)
            else np.array(to_rgb(CMAP(norm(program["fitness"]))))
        )
        return np.append(rgb, alpha)

    def width(node: str) -> float:
        share = math.sqrt(leaves[node] / leaves[root])
        return shape.width_scale * (
            shape.width_floor + (1.0 - shape.width_floor) * share
        )

    ax.set_aspect("equal")
    ax.axis("off")

    root_x, root_y = position[root]
    trunk_x, trunk_y = hermite(
        (root_x * 0.35, shape.trunk_base),
        (root_x, root_y),
        (0.0, 1.0),
        heading[root],
        shape,
    )
    ax.add_patch(
        Polygon(
            ribbon(trunk_x, trunk_y, width(root) * 1.95, width(root)),
            closed=True,
            facecolor=colour(by_id[root]),
            edgecolor="none",
            zorder=1,
            joinstyle="round",
        )
    )

    for program in sorted(programs, key=lambda p: -leaves[p["id"]]):
        parent = program["parent"]
        if not parent:
            continue
        xs, ys = hermite(
            position[parent],
            position[program["id"]],
            heading[parent],
            heading[program["id"]],
            shape,
        )
        ax.add_patch(
            Polygon(
                ribbon(xs, ys, width(parent) * 0.92, width(program["id"])),
                closed=True,
                facecolor=colour(program, 0.97),
                edgecolor="none",
                zorder=2,
                joinstyle="round",
            )
        )

    lo, span = norm.vmin, norm.vmax - norm.vmin
    for program in programs:
        x, y = position[program["id"]]
        scale = (program["fitness"] - lo) / span if valid(program) else 0.0
        r = 0.0105 + 0.0085 * scale
        if program["id"] == best["id"]:
            ax.add_patch(
                Circle(
                    (x, y),
                    r * 2.0,
                    facecolor="none",
                    edgecolor=colour(program),
                    linewidth=0.9,
                    zorder=4,
                )
            )
            r *= 1.45
        elif program["id"] == root:
            r *= 1.30
        ax.add_patch(
            Circle(
                (x, y),
                r,
                facecolor=colour(program),
                edgecolor="white",
                linewidth=0.45,
                zorder=5,
            )
        )

    halo = [pe.withStroke(linewidth=1.3, foreground="white")]
    best_x, best_y = position[best["id"]]
    # [x, y, text, ha, movable, kwargs]
    labels = [
        [
            root_x + 0.048,
            root_y - 0.002,
            by_id[root]["tag"],
            "left",
            False,
            dict(fontsize=4.8, fontweight="bold"),
        ],
        [
            root_x + 0.048,
            root_y - 0.034,
            "seed",
            "left",
            False,
            dict(fontsize=6.0, color=GREY, style="italic"),
        ],
        [
            best_x + 0.054,
            best_y + 0.040,
            best["tag"],
            "left",
            False,
            dict(fontsize=4.8, fontweight="bold"),
        ],
        [
            best_x + 0.054,
            best_y + 0.086,
            "best",
            "left",
            False,
            dict(fontsize=6.0, color=GREY, style="italic"),
        ],
    ]
    for program in programs:
        if program["id"] in (root, best["id"]):
            continue
        x, y = position[program["id"]]
        hx, hy = heading[program["id"]]
        lx = x + 0.030 * hx + (0.011 if hx >= 0 else -0.011)
        ly = y + 0.030 * hy + 0.006
        labels.append(
            [
                lx,
                ly,
                program["tag"],
                "left" if hx >= 0 else "right",
                True,
                dict(fontsize=4.8),
            ]
        )

    for _ in range(3):
        labels.sort(key=lambda item: (item[1], item[0]))
        for i, item in enumerate(labels):
            if not item[4]:
                continue
            for other in labels[max(0, i - 14) : i]:
                if abs(item[0] - other[0]) < 0.105 and abs(item[1] - other[1]) < 0.029:
                    item[1] = other[1] + 0.029
    for lx, ly, text, ha, _, kwargs in labels:
        kwargs.setdefault("color", "#1a1a1a")
        ax.text(lx, ly, text, ha=ha, va="center", zorder=6, path_effects=halo, **kwargs)

    x0, x1, y0, y1 = tree_limits(position, shape)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)

    ax.legend(
        handles=[
            Line2D(
                [],
                [],
                marker="o",
                linestyle="none",
                markersize=3.0,
                markerfacecolor=GREY,
                markeredgecolor="white",
                markeredgewidth=0.4,
                label="invalid program",
            ),
            Line2D(
                [],
                [],
                marker="o",
                linestyle="none",
                markersize=4.2,
                markerfacecolor="none",
                markeredgecolor=CMAP(1.0),
                markeredgewidth=0.9,
                label="run best",
            ),
        ],
        loc="lower right",
        frameon=False,
        fontsize=5.7,
        handletextpad=0.3,
        borderpad=0.0,
        labelspacing=0.3,
        handlelength=1.0,
        bbox_to_anchor=(1.0, 0.01),
    )


def draw_archive(ax, programs, norm):
    elites: dict[tuple[int, int], float] = {}
    for program in programs:
        if not valid(program):
            continue
        if program["arch_kind"] is None or program["compute_tier"] is None:
            continue
        key = (int(program["compute_tier"]), int(program["arch_kind"]))
        elites[key] = max(elites.get(key, -math.inf), program["fitness"])

    ax.set_aspect("equal")
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(-0.5, 3.5)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for tier in range(6):
        for arch in range(4):
            fitness = elites.get((tier, arch))
            ax.add_patch(
                Rectangle(
                    (tier - 0.44, arch - 0.44),
                    0.88,
                    0.88,
                    facecolor=CMAP(norm(fitness)) if fitness is not None else "#e8eae4",
                    edgecolor="white",
                    linewidth=0.8,
                    zorder=2,
                )
            )

    ax.set_xticks(range(6))
    ax.set_xticklabels(TIER_LABELS, fontsize=5.6)
    ax.set_yticks(range(4))
    ax.set_yticklabels(ARCH_LABELS, fontsize=5.6)
    ax.tick_params(length=0, pad=1.6, colors="#1a1a1a")
    ax.set_xlabel(
        r"compute tier ($\log_{10}$ trainable parameters)", fontsize=6.2, labelpad=2.5
    )
    ax.set_ylabel("architecture family", fontsize=6.2, labelpad=2.5)
    return len(elites)


def render(programs, max_iter: int, style_name: str, plain: bool = False) -> Path:
    shape = SHAPES[style_name]
    by_id, children, root = build_topology(programs)
    leaves, _, angle, position, heading = layout(children, root, shape)

    fitnesses = [p["fitness"] for p in programs if valid(p)]
    norm = Normalize(vmin=min(fitnesses), vmax=max(fitnesses))
    best = max((p for p in programs if valid(p)), key=lambda p: p["fitness"])

    # Panel A keeps equal aspect, so its width follows from the tree's shape,
    # capped so that panel B always has room; panel B then takes what is left,
    # with square cells.
    x0, x1, y0, y1 = tree_limits(position, shape)
    aspect = (x1 - x0) / (y1 - y0)
    tree_h = TREE_BOX_H
    tree_w = (tree_h * FIG_H) * aspect / FIG_W
    if tree_w > TREE_BOX_MAX_W:
        tree_w = TREE_BOX_MAX_W
        tree_h = (tree_w * FIG_W) / aspect / FIG_H
    tree_y = TREE_BOX_Y + (TREE_BOX_H - tree_h) / 2
    grid_left = tree_w + ARCHIVE_LABEL_GAP
    grid_w = min(CBAR_X - CBAR_GAP - grid_left, 0.26)
    grid_h = (grid_w * FIG_W * 4 / 6) / FIG_H
    grid_bottom = 0.52 - grid_h / 2

    fig = plt.figure(figsize=(FIG_W, FIG_H))
    ax_tree = fig.add_axes([0.0, tree_y, tree_w, tree_h])
    ax_archive = fig.add_axes([grid_left, grid_bottom, grid_w, grid_h])
    cax = fig.add_axes([CBAR_X, 0.5 - CBAR_H / 2, CBAR_W, CBAR_H])

    draw_tree(
        ax_tree,
        programs,
        by_id,
        children,
        root,
        best,
        leaves,
        angle,
        position,
        heading,
        norm,
        shape,
    )
    occupied = draw_archive(ax_archive, programs, norm)

    bar = fig.colorbar(ScalarMappable(norm=norm, cmap=CMAP), cax=cax)
    bar.set_label("fitness (macro-AUCPR)", fontsize=6.2, labelpad=2.5)
    bar.set_ticks([round(0.09 + 0.01 * i, 2) for i in range(6)])
    bar.ax.tick_params(labelsize=5.6, length=1.8, width=0.4, pad=1.6, colors="#1a1a1a")
    bar.outline.set_visible(False)

    fig.text(0.012, 0.965, "A", fontsize=8.5, fontweight="bold", va="top")
    fig.text(
        0.038,
        0.962,
        f"lineage tree, iterations 0\u2013{max_iter} ({len(programs)} programs)",
        fontsize=6.2,
        color=GREY,
        va="top",
    )
    fig.text(grid_left - 0.038, 0.965, "B", fontsize=8.5, fontweight="bold", va="top")
    fig.text(
        grid_left - 0.012,
        0.962,
        f"MAP-Elites archive ({occupied}/24 cells)",
        fontsize=6.2,
        color=GREY,
        va="top",
    )

    name = f"fig_evolution_tree_0_{max_iter}"
    stem = RUN_DIR / (name if plain else f"{name}_{style_name}")
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(stem.with_suffix(".png"), dpi=600)
    # Text-as-paths renders identically without STIXGeneral installed; the
    # _editable copy keeps live text for tweaking in Inkscape/Illustrator.
    with mpl.rc_context({"svg.fonttype": "path"}):
        fig.savefig(stem.with_suffix(".svg"))
    fig.savefig(stem.with_name(f"{stem.name}_editable.svg"))
    plt.close(fig)
    print(
        f"[{style_name}] cells={occupied} best={best['tag']} "
        f"fitness={best['fitness']:.4f} panelA={tree_w * FIG_W:.2f}in "
        f"cell={grid_w * FIG_W / 6:.3f}in -> {stem.with_suffix('.pdf').name}"
    )
    return stem.with_suffix(".png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-iter", type=int, default=50)
    parser.add_argument("--style", default="arch", choices=[*SHAPES, "all"])
    parser.add_argument(
        "--plain", action="store_true", help="drop the style suffix from the file names"
    )
    args = parser.parse_args()

    style()
    programs = load(args.max_iter)
    names = list(SHAPES) if args.style == "all" else [args.style]
    for name in names:
        render(programs, args.max_iter, name, plain=args.plain and len(names) == 1)


if __name__ == "__main__":
    main()
