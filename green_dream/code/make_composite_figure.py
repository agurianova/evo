#!/usr/bin/env python3
"""Three-panel figure for one terra expert-on replicate.

A  lineage tree
B  MAP-Elites archive
C  frontier fitness and the validation champion's mutation path

Panel A is the compound umbel. Every branch takes the fitness colour,
except discarded ones, which stay pale gray. The same colour runs
through the archive and the champion path.

Usage:
    python make_composite_figure.py [--replicate 1] [--max-iter 100]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Polygon, Rectangle

REPO = Path(__file__).resolve().parents[2]
LUNA_DIR = REPO / "outputs" / "pmhctcr_python_patch_luna_m200_v2"
sys.path.insert(0, str(LUNA_DIR))

import make_frontier_figure as frontier  # noqa: E402
import make_tree_figure as tree  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import make_mutation_trees as plants  # noqa: E402

# Same stem-to-leaf mix as the umbel champion path.
FITNESS = LinearSegmentedColormap.from_list("umbel_fitness", [plants.STEM, plants.LEAF])
tree.CMAP = FITNESS
frontier.CMAP = FITNESS
frontier.FRONTIER_EDGE = plants.STEM

OUTPUTS = REPO / "outputs"
# Same ribbon and node scale as figure_2.svg.
TREE_WIDTH = 2.05
TREE_NODE = 0.68
TITLE_INK = "#243044"
TITLE_DX = 0.16 / 5.5
LETTER_SIZE = 6.6
TITLE_SIZE = 6.2
RUN_PREFIX = "pmhctcr_final_terra_expert_on_m100_r"

# Panel C is 0.7 of its previous height. Top panels keep the same inch size.
FIG_W, FIG_H = 5.5, 4.532
TOP_Y, TOP_H = 0.483, 0.472
FRONTIER_AXES = (0.10, 0.085, 0.84, 0.318)
# Y tick labels of panel B sit in this gap; A:B axes widths are 2:1.
ARCHIVE_LABEL_GAP = 0.155
CBAR_X, CBAR_W = 0.948, 0.012
ARCHIVE_CELLS = 36
HALO = [pe.withStroke(linewidth=1.3, foreground="white")]

# problems/pmhctcr/behavior.py: PMHC_TCR_INTERACTION_NAMES, compute_tier()
INTERACTION_LABELS = (
    "global concat",
    "patch matching",
    "bilinear",
    "cross-attn",
    "dual attn.",
    "gated branches",
)


def run_dir(replicate: int) -> Path:
    return OUTPUTS / f"{RUN_PREFIX}{replicate}"


def figure_dir() -> Path:
    return OUTPUTS / "pmhctcr_final_terra_expert_on_m100_r1-5"


def load_programs(replicate: int) -> list[dict]:
    """Load every saved program and pack it onto steps 0..N-1.

    Burned iterations advance the run counter without writing a program.
    Dropping those empty slots puts one program on every step.
    """
    programs_dir = run_dir(replicate) / "storage/pmhctcr/programs"
    tree.PROGRAMS = programs_dir
    programs = tree.load(10**9)
    interaction: dict[str, float | None] = {}
    state: dict[str, str | None] = {}
    for path in programs_dir.glob("*.json"):
        blob = json.loads(path.read_text())
        metrics = blob.get("metrics") or {}
        interaction[blob["id"]] = metrics.get("pmhc_tcr_interaction")
        state[blob["id"]] = blob.get("state")
    for program in programs:
        program["pmhc_tcr_interaction"] = interaction.get(program["id"])
        program["state"] = state.get(program["id"])
        program["short"] = program["id"][:8]
    programs.sort(key=lambda program: (program["iteration"], program["id"]))
    for step, program in enumerate(programs):
        program["raw_iteration"] = program["iteration"]
        program["iteration"] = step
    return programs


def draw_archive(ax, programs, norm) -> int:
    """6×6 MAP-Elites: compute tier × pMHC–TCR interaction, as in the run."""
    elites: dict[tuple[int, int], float] = {}
    for program in programs:
        if not tree.valid(program):
            continue
        interaction = program.get("pmhc_tcr_interaction")
        tier = program.get("compute_tier")
        if interaction is None or tier is None:
            continue
        key = (int(tier), int(interaction))
        elites[key] = max(elites.get(key, -math.inf), program["fitness"])

    ax.set_aspect("equal")
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(-0.5, 5.5)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for tier in range(6):
        for interaction in range(6):
            fitness = elites.get((tier, interaction))
            ax.add_patch(Rectangle(
                (tier - 0.44, interaction - 0.44), 0.88, 0.88,
                facecolor=tree.CMAP(norm(fitness)) if fitness is not None else "#e8eae4",
                edgecolor="white", linewidth=0.7, zorder=2,
            ))

    ax.set_xticks(range(6))
    ax.set_xticklabels(tree.TIER_LABELS, fontsize=5.2)
    ax.set_yticks(range(6))
    ax.set_yticklabels(INTERACTION_LABELS, fontsize=5.0)
    ax.tick_params(length=0, pad=1.4, colors="#1a1a1a")
    ax.set_xlabel(r"compute tier ($\log_{10}$ trainable parameters)", fontsize=5.8, labelpad=2.0)
    ax.set_ylabel("interaction type", fontsize=5.8, labelpad=2.0)
    return len(elites)


def annotate_chain(ax, chain, best_id: str, seed_id: str) -> None:
    """Tag each hop on the champion path. No invented mutation names."""
    for index, program in enumerate(chain):
        x, y = program["iteration"], program["fitness"]
        above = index % 2 == 0
        dy = 0.0042 if above else -0.0042
        dx = 1.1
        if program["id"] == best_id:
            above, dy, dx = True, 0.0055, 1.4
        if program["id"] == seed_id:
            above, dy, dx = False, -0.0050, 1.2
        tx, ty = x + dx, y + dy
        va = "bottom" if above else "top"
        ax.text(
            tx, ty, program["tag"], ha="left", va=va, zorder=7,
            fontsize=4.8, color="#1a1a1a", fontweight="bold", path_effects=HALO,
        )
        if program["id"] == seed_id:
            ax.text(
                tx, ty - 0.0022, "seed", ha="left", va="top", zorder=7,
                fontsize=5.6, color=tree.GREY, style="italic", path_effects=HALO,
            )
        if program["id"] == best_id:
            ax.text(
                tx, ty + 0.0022, "best", ha="left", va="bottom", zorder=7,
                fontsize=5.6, color=tree.GREY, style="italic", path_effects=HALO,
            )
        ax.plot([x, tx - 0.15], [y, ty], color=frontier.LEADER, linewidth=0.4, zorder=2)


def label_frontier(ax, jumps, best) -> None:
    """Name the final plateau, clear of the champion's 'best' tag."""
    _t0, t1, fitness = jumps[-1]
    best_x = float(best["iteration"])
    on_plateau = abs(float(best["fitness"]) - fitness) < 1e-6
    if on_plateau and t1 - best_x > 18:
        x = 0.5 * (best_x + 10.0 + t1)
    elif best_x > 18:
        x = best_x - 14.0
    else:
        x = t1 + 4.0
    ax.text(
        x, fitness + 0.0010, "frontier",
        fontsize=5.8, color=tree.GREY, ha="center", va="bottom", zorder=6,
        path_effects=HALO,
    )


def draw_frontier_panel(ax, programs, chain, best, norm, max_iter: int, y_lim) -> None:
    iterations, curve = frontier.frontier(programs, max_iter)
    evaluated = sorted(
        (p for p in programs if tree.valid(p)),
        key=lambda p: (p["iteration"], p["fitness"]),
    )
    seed = chain[0]

    ax.set_xlim(-1.5, max_iter + 6.0)
    ax.set_ylim(*y_lim)
    ax.set_xticks(range(0, max_iter + 1, 20))
    ax.tick_params(labelsize=6.0, length=2.2, width=0.5, pad=2.0, colors="#1a1a1a")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#b8bcc2")
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#e6e8ea", linewidth=0.45)
    ax.set_xlabel("step", fontsize=6.5, labelpad=2.0)
    ax.set_ylabel("fitness (macro-AUCPR)", fontsize=6.5, labelpad=3.0)

    jumps = frontier.frontier_jumps(iterations, curve)
    frontier.draw_gradient_frontier(ax, jumps, y_lim[0])
    label_frontier(ax, jumps, best)

    ax.plot(
        [p["iteration"] for p in evaluated],
        [p["fitness"] for p in evaluated],
        color=tree.GREY, linewidth=0.55, linestyle=(0, (1.4, 2.2)),
        alpha=0.42, zorder=2,
    )
    ax.scatter(
        [p["iteration"] for p in evaluated],
        [p["fitness"] for p in evaluated],
        s=6.5, c=[tree.CMAP(norm(p["fitness"])) for p in evaluated],
        alpha=0.50, linewidths=0.0, zorder=2,
    )

    frontier.draw_champion_path(ax, chain, norm)
    for program in chain:
        frontier.draw_champion_node(
            ax, program, norm,
            is_best=program["id"] == best["id"],
            is_seed=program["id"] == seed["id"],
        )
    annotate_chain(ax, chain, best["id"], seed["id"])

    late = [p for p in evaluated if p["id"] != best["id"] and p["iteration"] >= 0.7 * max_iter]
    if late:
        target = max(late, key=lambda p: p["fitness"])
        ax.annotate(
            "evaluated programs",
            xy=(target["iteration"], target["fitness"]),
            xytext=(max_iter - 8.0, y_lim[0] + 0.22 * (y_lim[1] - y_lim[0])),
            fontsize=5.6, color=tree.GREY, ha="right", va="bottom", zorder=6,
            path_effects=HALO,
            arrowprops=dict(
                arrowstyle="-", color=frontier.LEADER, linewidth=0.4,
                shrinkA=1.5, shrinkB=1.5,
            ),
        )


def branch_color(program: dict, norm) -> str | tuple:
    """Fitness colour of one program. Discarded stays pale gray."""
    if program.get("state") == "discarded":
        return plants.PALE
    if tree.valid(program):
        return FITNESS(norm(program["fitness"]))
    return plants.GRAY


def draw_fitness_tree(ax, lineage, programs, best: dict, norm) -> None:
    """Umbel with fitness-coloured branches. No mechanism clouds or deltas."""
    shape = plants.umbel(lineage)
    by_id, children, root = lineage.build_topology(programs)
    leaves, _, _angle, position, heading = lineage.layout(children, root, shape)
    def width(node: str) -> float:
        share = math.sqrt(leaves[node] / leaves[root])
        return TREE_WIDTH * shape.width_scale * (
            shape.width_floor + (1.0 - shape.width_floor) * share
        )

    def add_ribbon(parent: str, child: str, color, z: int) -> None:
        xs, ys = lineage.hermite(
            position[parent], position[child], heading[parent], heading[child], shape,
        )
        ax.add_patch(Polygon(
            lineage.ribbon(xs, ys, width(parent) * 0.92, width(child)),
            closed=True, facecolor=color, edgecolor="none", linewidth=0.0,
            zorder=z, joinstyle="round",
        ))

    ax.set_aspect("equal")
    ax.axis("off")

    root_x, root_y = position[root]
    trunk_x, trunk_y = lineage.hermite(
        (root_x * 0.35, shape.trunk_base), (root_x, root_y),
        (0.0, 1.0), heading[root], shape,
    )
    ax.add_patch(Polygon(
        lineage.ribbon(trunk_x, trunk_y, width(root) * 1.95, width(root)),
        closed=True, facecolor=branch_color(by_id[root], norm),
        edgecolor="none", zorder=1, joinstyle="round",
    ))

    ordered = sorted(programs, key=lambda program: -leaves[program["id"]])
    for program in ordered:
        parent = program["parent"]
        if not parent:
            continue
        dropped = program.get("state") == "discarded"
        add_ribbon(parent, program["id"], branch_color(program, norm), 1 if dropped else 3)

    for program in programs:
        x, y = position[program["id"]]
        dropped = program.get("state") == "discarded"
        face = branch_color(program, norm)
        radius = (0.022 if program["id"] == best["id"] else 0.016) * TREE_NODE
        ax.add_patch(Circle(
            (x, y), radius, facecolor=face,
            edgecolor=plants.PALE_EDGE if dropped else face,
            linewidth=0.9 if dropped else 0.0, zorder=5,
            linestyle=(0, (1.2, 0.9)) if dropped else "solid",
        ))
        if program["id"] == best["id"]:
            ax.add_patch(Circle(
                (x, y), radius + 0.012 * TREE_NODE, facecolor="none",
                edgecolor=face, linewidth=1.15, zorder=6,
            ))

    halo = [pe.withStroke(linewidth=1.6, foreground="white")]
    # Tag and the italic word share an edge: about 0.25 pt of clearance.
    role_gap = 0.039
    labels = [
        [root_x + 0.05, root_y - 0.004, by_id[root]["tag"], "left", False, "#1a1a1a", 5.2],
        [root_x + 0.05, root_y - 0.004 - role_gap, "seed", "left", False, "#6a6a6a", 6.4],
    ]
    best_x, best_y = position[best["id"]]
    labels.append([best_x + 0.05, best_y + 0.02, best["tag"], "left", False, "#1a1a1a", 5.2])
    labels.append([best_x + 0.05, best_y + 0.02 + role_gap, "best", "left", False, "#6a6a6a", 6.4])
    named = {root, best["id"]}
    for program in programs:
        if program["id"] in named:
            continue
        x, y = position[program["id"]]
        hx, hy = heading.get(program["id"], (0.0, 1.0))
        px, py = -hy, hx
        if px < 0:
            px, py = -px, -py
            ha = "right"
        else:
            ha = "left"
        labels.append([
            x + px * 0.032, y + py * 0.032, program["tag"],
            ha, True, "#1a1a1a", 3.2,
        ])
    fixed = [item for item in labels if not item[4]]
    loose = [item for item in labels if item[4]]
    for _ in range(6):
        for item in loose:
            for other in loose:
                if other is item:
                    continue
                dx = item[0] - other[0]
                dy = item[1] - other[1]
                if abs(dx) >= 0.07 or abs(dy) >= 0.022:
                    continue
                item[1] += 0.012 if dy >= 0 else -0.012
            for other in fixed:
                dx = item[0] - other[0]
                dy = item[1] - other[1]
                if abs(dx) >= 0.10 or abs(dy) >= 0.04:
                    continue
                item[0] += 0.02 if dx >= 0 else -0.02

    def draw_label(item, z: int) -> None:
        lx, ly, text, ha, _movable, color, size = item
        ax.text(
            lx, ly, text, ha=ha, va="center", zorder=z, color=color,
            fontsize=size, fontweight="normal",
            fontstyle="italic" if text in ("seed", "best") else "normal",
            path_effects=halo,
        )

    for item in loose:
        draw_label(item, 7)
    for item in fixed:
        draw_label(item, 12)

    x0, x1, y0, y1 = lineage.tree_limits(position, shape)
    left, right = x0 - 0.06, x1 + 0.06
    bottom, top = y0 - 0.06, y1 + 0.08
    # Same framing, canvas at 0.8, so the tree reads larger in the panel.
    cx, cy = (left + right) / 2, (bottom + top) / 2
    ax.set_xlim(cx - 0.4 * (right - left), cx + 0.4 * (right - left))
    ax.set_ylim(cy - 0.4 * (top - bottom), cy + 0.4 * (top - bottom))
    ax.legend(
        handles=[
            Line2D([], [], marker="o", linestyle="none", markersize=5.2,
                   markerfacecolor=plants.PALE, markeredgecolor=plants.PALE_EDGE,
                   markeredgewidth=0.8, label="discarded"),
            Line2D([], [], marker="o", linestyle="none", markersize=6.0,
                   markerfacecolor="none", markeredgecolor=FITNESS(1.0),
                   markeredgewidth=0.9, label="run best"),
        ],
        loc="lower right", frameon=False, fontsize=4.6, handletextpad=0.3,
        borderpad=0.0, labelspacing=0.25, handlelength=1.0,
        bbox_to_anchor=(1.02, 0.0),
    )


def render(replicate: int, max_iter: int) -> Path:
    tree.style()
    programs = load_programs(replicate)
    if not programs:
        raise SystemExit(f"No programs found for replicate {replicate}")
    max_iter = max(program["iteration"] for program in programs)

    lineage = plants.load_module("lineage_tree_v5", plants.TREE_PY)
    shape = plants.umbel(lineage)
    _by_id, children, root = lineage.build_topology(programs)
    _leaves, _, _angle, position, _heading = lineage.layout(children, root, shape)
    chain, best = frontier.champion_chain(programs)
    fitnesses = [p["fitness"] for p in programs if tree.valid(p)]
    norm = Normalize(vmin=min(fitnesses), vmax=max(fitnesses))

    x0, x1, y0, y1 = lineage.tree_limits(position, shape)
    aspect = (x1 - x0) / (y1 - y0)
    pair_right = CBAR_X - 0.020
    pair_w = pair_right - ARCHIVE_LABEL_GAP
    tree_w = pair_w * (2.0 / 3.0)
    grid_w = pair_w * (1.0 / 3.0)
    grid_h = (grid_w * FIG_W) / FIG_H
    if grid_h > TOP_H * 0.92:
        grid_h = TOP_H * 0.92
        grid_w = grid_h * FIG_H / FIG_W
        tree_w = grid_w * 2.0
    tree_h = (tree_w * FIG_W) / aspect / FIG_H
    if tree_h > TOP_H:
        tree_h = TOP_H
    tree_y = TOP_Y + (TOP_H - tree_h) / 2
    grid_left = tree_w + ARCHIVE_LABEL_GAP
    # The cell grid is smaller than the 2:1 slot; the tree keeps its size.
    grid_w *= 0.70
    grid_h *= 0.70
    grid_bottom = TOP_Y + (TOP_H - grid_h) / 2
    cbar_h = grid_h * 0.92
    cbar_y = TOP_Y + TOP_H / 2 - cbar_h / 2
    cbar_x = grid_left + grid_w + 0.014

    fig = plt.figure(figsize=(FIG_W, FIG_H))
    ax_tree = fig.add_axes([0.0, tree_y, tree_w, tree_h])
    ax_archive = fig.add_axes([grid_left, grid_bottom, grid_w, grid_h])
    cax = fig.add_axes([cbar_x, cbar_y, CBAR_W, cbar_h])
    ax_frontier = fig.add_axes(list(FRONTIER_AXES))

    draw_fitness_tree(ax_tree, lineage, programs, best, norm)
    ax_tree.set_position([0.0, tree_y, tree_w, tree_h])
    occupied = draw_archive(ax_archive, programs, norm)
    ax_archive.set_position([grid_left, grid_bottom, grid_w, grid_h])

    bar = fig.colorbar(ScalarMappable(norm=norm, cmap=tree.CMAP), cax=cax)
    bar.set_label("fitness (macro-AUCPR)", fontsize=6.2, labelpad=2.5)
    bar.set_ticks([round(norm.vmin + (norm.vmax - norm.vmin) * i / 4, 2) for i in range(5)])
    bar.ax.tick_params(labelsize=5.6, length=1.8, width=0.4, pad=1.6, colors="#1a1a1a")
    bar.outline.set_visible(False)

    pad = 0.006
    y_lim = (min(fitnesses) - pad, max(fitnesses) + 0.012)
    draw_frontier_panel(ax_frontier, programs, chain, best, norm, max_iter, y_lim)

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    to_fig = fig.transFigure.inverted()

    def content_left(artists) -> float:
        return to_fig.transform((min(artist.get_window_extent(renderer).x0 for artist in artists), 0.0))[0]

    def panel_title(x: float, y: float, letter: str, text: str) -> None:
        fig.text(x, y, letter, fontsize=LETTER_SIZE, color=TITLE_INK, va="top")
        fig.text(x + TITLE_DX, y - 0.002, text, fontsize=TITLE_SIZE, color=TITLE_INK, va="top")

    panel_title(0.012, 0.985, "A", f"Lineage tree, steps 0-{max_iter}")
    b_left = content_left([*ax_archive.get_yticklabels(), ax_archive.yaxis.label])
    panel_title(b_left, 0.985, "B", f"MAP-Elites archive ({occupied}/{ARCHIVE_CELLS} cells)")
    c_left = content_left([ax_frontier.yaxis.label, *ax_frontier.get_yticklabels()])
    panel_title(
        c_left, 0.438, "C",
        f"Frontier fitness and champion path, steps 0–{max_iter}",
    )

    out_dir = figure_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = out_dir / f"fig_composite_expert_on_r{replicate}_0_{max_iter}"
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(stem.with_suffix(".png"), dpi=600)
    with mpl.rc_context({"svg.fonttype": "path"}):
        fig.savefig(stem.with_suffix(".svg"))
    fig.savefig(stem.with_name(f"{stem.name}_editable.svg"))
    plt.close(fig)

    print(
        f"replicate={replicate} programs={len(programs)} "
        f"valid={sum(tree.valid(p) for p in programs)} "
        f"cells={occupied} hops={len(chain)} "
        f"best={best['tag']} fitness={best['fitness']:.4f} iter={best['iteration']}"
    )
    print(stem.with_suffix(".png"))
    return stem.with_suffix(".png")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replicate", type=int, default=1, choices=range(1, 6))
    parser.add_argument("--max-iter", type=int, default=100)
    args = parser.parse_args()
    render(args.replicate, args.max_iter)


if __name__ == "__main__":
    main()
