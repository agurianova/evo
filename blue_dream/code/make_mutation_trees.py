#!/usr/bin/env python3
"""Schematic lineage trees for expert-on r1–r5.

Compound umbel: a short stalk and primary rays that end in tight clusters.
Surface complementarity is a soft blue cloud and KQV is a soft cyan cloud
around an otherwise ordinary branch. Fitness numbers sit beside that branch,
in black, on a pale green or pale red cloud that fades out at the edge.
Discarded nodes are a pale gray with a dashed outline.
"""

from __future__ import annotations

from collections import defaultdict
import importlib.util
import json
import math
from pathlib import Path
import sys

from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Polygon
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "mutation_trees"
TREE_PY = REPO / "outputs" / "pmhctcr_python_patch_luna_m200_v5" / "make_tree_figure.py"
HYP_PY = REPO / "outputs" / "_analysis" / "expert_hypothesis_mutation_gains.py"

GRAY = "#c8c8c8"
PLUS_HAZE = "#cfe8c6"
MINUS_HAZE = "#f4cfcf"
INK = "#1a1a1a"
STEM = "#1c4f2e"
LEAF = "#c8f06a"
SURFACE = "#6eacd8"
KQV = "#b7e8f2"
HOST = "#3a3a3a"
PALE = "#f3f3f3"
PALE_EDGE = "#dcdcdc"
INJECT = {
    2: ("275ae460",),
    4: ("4996f5b6", "52c245fc", "8777238d", "c840f89c"),
    5: ("c8991aef", "773338c2"),
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def is_kqv(text: str) -> bool:
    return (
        "self.key = torch.nn.ModuleList" in text
        and "self.value = torch.nn.ModuleList" in text
        and "range(states)" in text
    )


def highlights(hyp) -> dict[int, dict]:
    """Per run: colored children and the fitness delta of each one."""
    rows = [row for row in hyp.load_all() if row["scored"]]
    surface = [
        row
        for row in rows
        if "h1_surface" in row["suggestion"] and "h1_surface" in row["code"]
    ]
    kqv = [row for row in rows if is_kqv(row["added"])]
    out = {
        run: {
            "surface_delta": {},
            "kqv_delta": {},
            "surface_n": 0,
            "kqv_n": 0,
            "surface_plus": 0,
            "kqv_plus": 0,
        }
        for run in range(1, 6)
    }

    def consume(members, kind: str) -> None:
        grouped: dict[tuple[int, str], list[float]] = defaultdict(list)
        for row in members:
            grouped[(row["run"], row["parent"])].append(row["delta"])
            out[row["run"]][f"{kind}_delta"][row["id"]] = row["delta"]
        for (run, _parent), deltas in grouped.items():
            out[run][f"{kind}_n"] += 1
            if float(np.median(deltas)) > 1e-12:
                out[run][f"{kind}_plus"] += 1

    consume(surface, "surface")
    consume(kqv, "kqv")
    return out


def stem_color(t: float) -> tuple[float, float, float]:
    """Umbellifer stem: dark at the root, fresh yellow-green at the leaves."""
    root = np.array(to_rgb(STEM))
    leaf = np.array(to_rgb(LEAF))
    mix = (1.0 - t) * root + t * leaf
    return tuple(float(channel) for channel in mix)


def haze_color(delta: float | None) -> str | None:
    if delta is None or abs(delta) < 1e-8:
        return None
    return PLUS_HAZE if delta > 0 else MINUS_HAZE


def step_delta(by_id: dict, parent: str, child: str) -> float | None:
    parent_fit = by_id[parent].get("fitness")
    child_fit = by_id[child].get("fitness")
    if parent_fit is None or child_fit is None or parent_fit < 0 or child_fit < 0:
        return None
    return child_fit - parent_fit


def umbel(tree):
    """Wide compound umbel: long primary rays, short terminal clusters."""
    return tree.Shape(
        fan_span=math.radians(118),
        x_stretch=1.0,
        y_stretch=1.16,
        curl=0.16,
        tip_curl=0.04,
        up_pull=0.95,
        tangent=0.48,
        depth_exp=0.58,
        root_radius=0.10,
        trunk_base=-0.08,
        jitter_r=0.012,
        jitter_a=0.006,
        jitter_h=0.015,
        width_scale=0.015,
        width_floor=0.11,
        margin=(0.03, 0.03, 0.012, 0.07),
    )


def signed(value: float) -> str:
    if abs(value) < 1e-9:
        return "0"
    body = f"{abs(value):.3f}"
    return f"+{body}" if value > 0 else f"\u2212{body}"


def load_programs(tree, run: int) -> list[dict]:
    folder = (
        REPO
        / "outputs"
        / f"pmhctcr_final_terra_expert_on_m100_r{run}"
        / "storage"
        / "pmhctcr"
        / "programs"
    )
    programs = []
    for path in folder.glob("*.json"):
        blob = json.loads(path.read_text())
        metrics = blob.get("metrics") or {}
        lineage = blob.get("lineage") or {}
        programs.append(
            {
                "id": blob["id"],
                "tag": blob["id"][:4],
                "short": blob["id"][:8],
                "iteration": blob.get("iteration") or 0,
                "generation": lineage.get("generation") or 0,
                "parents": lineage.get("parents") or [],
                "fitness": metrics.get("fitness"),
                "is_valid": metrics.get("is_valid"),
                "state": blob.get("state"),
            }
        )
    # The plant code drops programs whose iteration is missing; every record
    # here has one, and the prefix used by the mutation table is unique.
    shorts = [program["short"] for program in programs]
    if len(shorts) != len(set(shorts)):
        raise RuntimeError(f"r{run}: 8-char ids collide")
    return programs


def paint(tree, programs, marks, run: int, ax, legend: bool) -> None:
    shape = umbel(tree)
    by_id, children, root = tree.build_topology(programs)
    leaves, _, _angle, position, heading = tree.layout(children, root, shape)
    best = max(
        (program for program in programs if tree.valid(program)),
        key=lambda program: program["fitness"],
    )
    by_short = {program["short"]: program["id"] for program in programs}
    kind_of = {}
    delta_of = {}
    for short, delta in marks["surface_delta"].items():
        kind_of[by_short[short]] = "surface"
        delta_of[by_short[short]] = delta
    for short, delta in marks["kqv_delta"].items():
        kind_of[by_short[short]] = "kqv"
        delta_of[by_short[short]] = delta

    line = []
    cursor = best["id"]
    while cursor:
        line.append(cursor)
        cursor = by_id[cursor]["parent"]
    line.reverse()
    champ = set(line)
    champ_t = {
        node: (index / (len(line) - 1) if len(line) > 1 else 1.0)
        for index, node in enumerate(line)
    }

    def branch_width(node: str) -> float:
        share = math.sqrt(leaves[node] / leaves[root])
        return shape.width_scale * (
            shape.width_floor + (1.0 - shape.width_floor) * share
        )

    def add_ribbon(
        parent: str, child: str, color: str, edge: str, lw: float, z: int
    ) -> None:
        xs, ys = tree.hermite(
            position[parent],
            position[child],
            heading[parent],
            heading[child],
            shape,
        )
        ax.add_patch(
            Polygon(
                tree.ribbon(xs, ys, branch_width(parent) * 0.92, branch_width(child)),
                closed=True,
                facecolor=color,
                edgecolor=edge,
                linewidth=lw,
                zorder=z,
                joinstyle="round",
            )
        )

    def add_cloud(parent: str, child: str, color: str) -> None:
        if not parent:
            return
        xs, ys = tree.hermite(
            position[parent],
            position[child],
            heading[parent],
            heading[child],
            shape,
        )
        for radius, alpha, stride in ((0.030, 0.035, 3), (0.017, 0.055, 3)):
            for index in range(0, len(xs), stride):
                ax.add_patch(
                    Circle(
                        (float(xs[index]), float(ys[index])),
                        radius,
                        facecolor=color,
                        edgecolor="none",
                        alpha=alpha,
                        zorder=2.4,
                    )
                )

    def add_delta_cloud(lx: float, ly: float, text: str, ha: str) -> None:
        color = haze_color(
            1.0 if text[:1] == "+" else -1.0 if text[:1] in "-\u2212" else 0.0
        )
        if color is None:
            return
        half_w = 0.011 * len(text) + 0.026
        half_h = 0.032
        cx = lx + (half_w * 0.55 if ha == "left" else -half_w * 0.55)
        rgb = to_rgb(color)
        grid = 80
        span = np.linspace(-1.0, 1.0, grid)
        xx, yy = np.meshgrid(span, span)
        alpha = np.clip(np.exp(-1.35 * (xx * xx + yy * yy)) - 0.18, 0.0, 1.0)
        rgba = np.zeros((grid, grid, 4))
        rgba[..., 0] = rgb[0]
        rgba[..., 1] = rgb[1]
        rgba[..., 2] = rgb[2]
        rgba[..., 3] = alpha * 0.9
        ax.imshow(
            rgba,
            extent=(cx - half_w, cx + half_w, ly - half_h, ly + half_h),
            origin="lower",
            interpolation="bilinear",
            zorder=6.4,
            aspect="auto",
        )

    ax.set_aspect("equal")
    ax.axis("off")

    root_x, root_y = position[root]
    trunk_x, trunk_y = tree.hermite(
        (root_x * 0.35, shape.trunk_base),
        (root_x, root_y),
        (0.0, 1.0),
        heading[root],
        shape,
    )
    ax.add_patch(
        Polygon(
            tree.ribbon(
                trunk_x, trunk_y, branch_width(root) * 1.95, branch_width(root)
            ),
            closed=True,
            facecolor=stem_color(0.0),
            edgecolor="none",
            zorder=1,
            joinstyle="round",
        )
    )

    ordered = sorted(programs, key=lambda program: -leaves[program["id"]])
    for program in ordered:
        parent = program["parent"]
        if not parent or program["id"] in kind_of:
            continue
        on_champ = program["id"] in champ and parent in champ
        dropped = program.get("state") == "discarded" and not on_champ
        add_ribbon(
            parent,
            program["id"],
            PALE
            if dropped
            else (stem_color(champ_t[program["id"]]) if on_champ else GRAY),
            "none",
            0.0,
            1 if dropped else (3 if on_champ else 2),
        )

    for program in ordered:
        parent = program["parent"]
        kind = kind_of.get(program["id"])
        if not parent or not kind:
            continue
        add_cloud(parent, program["id"], SURFACE if kind == "surface" else KQV)
        on_champ = program["id"] in champ and parent in champ
        dropped = program.get("state") == "discarded" and not on_champ
        if on_champ:
            color = stem_color(champ_t[program["id"]])
        elif dropped:
            color = PALE
        else:
            color = GRAY
        add_ribbon(
            parent,
            program["id"],
            color,
            "none",
            0.0,
            3 if dropped else 4,
        )

    for program in programs:
        x, y = position[program["id"]]
        on_champ = program["id"] in champ
        faded = program.get("state") == "discarded" and not on_champ
        if faded:
            face, edge, lw, z = PALE, PALE_EDGE, 0.9, 5
        elif on_champ:
            arrived = stem_color(champ_t[program["id"]])
            face, edge, lw, z = arrived, arrived, 0.0, 5
        else:
            face, edge, lw, z = GRAY, GRAY, 0.0, 5
        radius = 0.022 if program["id"] == best["id"] else 0.016
        ax.add_patch(
            Circle(
                (x, y),
                radius,
                facecolor=face,
                edgecolor=edge,
                linewidth=lw,
                zorder=z,
                linestyle=(0, (1.2, 0.9)) if faded else "solid",
            )
        )
        if program["id"] == best["id"]:
            ax.add_patch(
                Circle(
                    (x, y),
                    radius + 0.012,
                    facecolor="none",
                    edgecolor=stem_color(1.0),
                    linewidth=1.15,
                    zorder=6,
                )
            )

    halo = [pe.withStroke(linewidth=1.6, foreground="white")]
    labels = [
        [
            root_x + 0.05,
            root_y - 0.004,
            by_id[root]["tag"],
            "left",
            False,
            "#1a1a1a",
            5.2,
        ],
        [root_x + 0.05, root_y - 0.038, "seed", "left", False, "#6a6a6a", 6.4],
    ]
    best_x, best_y = position[best["id"]]
    labels.append(
        [best_x + 0.05, best_y + 0.02, best["tag"], "left", False, "#1a1a1a", 5.2]
    )
    labels.append(
        [best_x + 0.05, best_y + 0.055, "best", "left", False, "#6a6a6a", 6.4]
    )
    for node, delta in delta_of.items():
        parent = by_id[node]["parent"]
        if not parent:
            continue
        xs, ys = tree.hermite(
            position[parent],
            position[node],
            heading[parent],
            heading[node],
            shape,
        )
        mid = len(xs) // 2
        mx, my = float(xs[mid]), float(ys[mid])
        tx = float(xs[min(mid + 3, len(xs) - 1)] - xs[max(mid - 3, 0)])
        ty = float(ys[min(mid + 3, len(ys) - 1)] - ys[max(mid - 3, 0)])
        norm = math.hypot(tx, ty) or 1.0
        px, py = -ty / norm, tx / norm
        if py < 0:
            px, py = -px, -py
        labels.append(
            [
                mx + px * 0.034,
                my + py * 0.034,
                signed(delta),
                "left" if px >= 0 else "right",
                True,
                INK,
                5.4,
            ]
        )

    missing = [short for short in INJECT.get(run, ()) if short not in by_short]
    if missing:
        raise RuntimeError(f"r{run}: injection host missing {missing}")
    for short in INJECT.get(run, ()):
        node = by_short[short]
        x, y = position[node]
        radius = 0.022 if node == best["id"] else 0.016
        ax.add_patch(
            Circle(
                (x, y),
                radius + 0.012,
                facecolor="none",
                edgecolor=HOST,
                linewidth=0.95,
                zorder=6,
            )
        )
        hx, _hy = heading[node]
        side = -1.0 if hx >= 0 else 1.0
        labels.append(
            [
                x + side * 0.058,
                y - 0.004,
                by_id[node]["tag"],
                "right" if side < 0 else "left",
                True,
                HOST,
                5.2,
            ]
        )

    for _ in range(4):
        labels.sort(key=lambda item: (item[1], item[0]))
        for index, item in enumerate(labels):
            if not item[4]:
                continue
            for other in labels[max(0, index - 16) : index]:
                if abs(item[0] - other[0]) < 0.12 and abs(item[1] - other[1]) < 0.032:
                    item[1] = other[1] + 0.032
    for _ in range(16):
        shifted = False
        for item in labels:
            if item[5] != HOST or not item[4]:
                continue
            for other in labels:
                if other is item:
                    continue
                dx = item[0] - other[0]
                dy = item[1] - other[1]
                if abs(dx) >= 0.12 or abs(dy) >= 0.048:
                    continue
                if abs(dx) >= abs(dy):
                    item[0] += 0.018 if dx >= 0 else -0.018
                else:
                    item[1] += 0.022 if dy >= 0 else -0.022
                shifted = True
        if not shifted:
            break
    for lx, ly, text, ha, _movable, color, size in labels:
        signed_delta = text[:1] in "+-\u2212"
        if signed_delta:
            add_delta_cloud(lx, ly, text, ha)
        weight = "bold" if signed_delta or text == "0" else "normal"
        ax.text(
            lx,
            ly,
            text,
            ha=ha,
            va="center",
            zorder=7,
            color=color,
            fontsize=size,
            fontweight=weight,
            fontstyle="italic" if text in ("seed", "best") else "normal",
            path_effects=None if signed_delta else halo,
        )
    ax.set_aspect("equal")

    x0, x1, y0, y1 = tree.tree_limits(position, shape)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_title(
        f"r{run}    Surface {marks['surface_plus']}+/{marks['surface_n']}"
        f"    KQV {marks['kqv_plus']}+/{marks['kqv_n']}"
        f"    best {best['tag']}  {best['fitness']:.3f}",
        fontsize=9,
        loc="left",
        color="#1a1a1a",
        pad=4,
    )
    if legend:
        ax.legend(
            handles=legend_handles(),
            loc="lower right",
            frameon=False,
            fontsize=6.2,
            handletextpad=0.4,
            borderpad=0.1,
            labelspacing=0.32,
            handlelength=1.5,
            bbox_to_anchor=(1.0, 0.0),
        )


def legend_handles() -> list[Line2D]:
    return [
        Line2D(
            [], [], color=GRAY, linewidth=4.0, solid_capstyle="butt", label="lineage"
        ),
        Line2D(
            [],
            [],
            color=stem_color(0.72),
            linewidth=4.0,
            solid_capstyle="butt",
            label="champion",
        ),
        Line2D(
            [],
            [],
            color=PLUS_HAZE,
            linewidth=6.0,
            solid_capstyle="round",
            alpha=0.9,
            label="+ fitness",
        ),
        Line2D(
            [],
            [],
            color=MINUS_HAZE,
            linewidth=6.0,
            solid_capstyle="round",
            alpha=0.9,
            label="− fitness",
        ),
        Line2D(
            [],
            [],
            color=SURFACE,
            linewidth=4.0,
            solid_capstyle="butt",
            label="Surface complementarity",
        ),
        Line2D([], [], color=KQV, linewidth=4.0, solid_capstyle="butt", label="KQV"),
        Line2D(
            [],
            [],
            marker="o",
            linestyle="none",
            markersize=7.2,
            markerfacecolor=GRAY,
            markeredgecolor=HOST,
            markeredgewidth=1.15,
            label="injection host",
        ),
        Line2D(
            [],
            [],
            marker="o",
            linestyle="none",
            markersize=6.5,
            markerfacecolor=PALE,
            markeredgecolor=PALE_EDGE,
            markeredgewidth=1.0,
            label="discarded",
        ),
    ]


def save(fig, stem: Path, dpi: int) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(stem.with_suffix(".png"), dpi=dpi)
    plt.close(fig)
    print(f"-> {stem.with_suffix('.png').name}")


def main() -> None:
    tree = load_module("lineage_tree", TREE_PY)
    hyp = load_module("hyp_gains", HYP_PY)
    tree.style()
    marked = highlights(hyp)
    surface_plus = sum(item["surface_plus"] for item in marked.values())
    surface_n = sum(item["surface_n"] for item in marked.values())
    kqv_plus = sum(item["kqv_plus"] for item in marked.values())
    kqv_n = sum(item["kqv_n"] for item in marked.values())
    print(f"surface parents {surface_plus}+/{surface_n}")
    print(f"kqv parents {kqv_plus}+/{kqv_n}")
    loaded = [(run, load_programs(tree, run)) for run in range(1, 6)]

    fig = plt.figure(figsize=(16.4, 4.9))
    for index, (run, programs) in enumerate(loaded):
        ax = fig.add_axes([0.004 + index * 0.199, 0.09, 0.193, 0.82])
        paint(tree, programs, marked[run], run, ax, legend=False)
    fig.legend(
        handles=legend_handles(),
        loc="lower center",
        ncol=8,
        frameon=False,
        fontsize=8,
        handletextpad=0.4,
        columnspacing=0.9,
        handlelength=1.4,
        bbox_to_anchor=(0.5, 0.004),
    )
    save(fig, OUT / "expert_on_r1-5", dpi=180)

    for run, programs in loaded:
        fig = plt.figure(figsize=(4.6, 4.4))
        ax = fig.add_axes([0.02, 0.14, 0.96, 0.78])
        paint(tree, programs, marked[run], run, ax, legend=False)
        fig.legend(
            handles=legend_handles(),
            loc="lower center",
            ncol=4,
            frameon=False,
            fontsize=6.2,
            handletextpad=0.35,
            columnspacing=0.7,
            handlelength=1.2,
            bbox_to_anchor=(0.5, 0.0),
        )
        save(fig, OUT / f"expert_on_r{run}", dpi=300)


if __name__ == "__main__":
    main()
