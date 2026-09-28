"""Render the Qwen3-235B arm-B winning lineage as a dependency-graph DAG
(lineage_graph_qwen.png), mirroring the gemini report's lineage figure.

Unlike the gemini script (hardcoded generations/prose), this one is data-driven:
it reads viz_qwen/manifest.json (written by extract_lineage.py), builds one
column per program in the chain, and derives each transition's change summary
directly from the field-level spec diff — so the annotations are grounded in the
actual genome, not hand-authored.

Usage: python make_lineage_viz_qwen.py   (run inside report_fused/, after extract_lineage.py)
"""

from __future__ import annotations

import json
from pathlib import Path
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
VIZ = HERE / "viz_qwen"

TOOL_FILL = "#1F4E79"
LLM_FILL = "#C9720B"
TOOL_TINT = "#DCE6F4"
LLM_TINT = "#FBE7CF"
CHANGED_EDGE = "#B42318"
ADD = "#1A7F37"
REM = "#B42318"
NEUTRAL = "#9AA5B1"

PX = 3.9
PY = 1.15
NODE_R = 0.34


def load_chain():
    manifest = json.loads((VIZ / "manifest.json").read_text())
    recs = [json.loads((VIZ / fname).read_text()) for fname, _, _ in manifest]
    return recs


def step_fields(step):
    if step["step_type"] == "tool":
        c = step["step_config"]
        return {
            "type": "tool",
            "tool": c["tool_name"],
            "map": tuple(sorted(c["input_mapping"].items())),
            "deps": tuple(step["dependencies"]),
            "title": step["title"],
        }
    return {
        "type": "llm",
        "title": step["title"],
        "aim": step.get("aim"),
        "stage_action": step.get("stage_action"),
        "reasoning_questions": step.get("reasoning_questions"),
        "deps": tuple(step["dependencies"]),
    }


def node_changed(p, c):
    return step_fields(p) != step_fields(c)


def dep_edges(spec):
    e = set()
    for s in spec["steps"]:
        for d in s["dependencies"]:
            e.add((d, s["number"]))
    return e


def side_label(step):
    if step["step_type"] == "tool":
        return step["step_config"]["tool_name"]
    t = step["title"]
    for pre in ("Generate ", "Summarize ", "Retrieve "):
        t = t.replace(pre, "")
    return t


def role_label(step):
    if step["step_type"] == "tool":
        return step["step_config"]["tool_name"]
    return side_label(step)


def wrap_label(s, width=12):
    return "\n".join(textwrap.wrap(s, width=width, break_long_words=False) or [s])


def change_summary(parent_spec, child_spec):
    """Grounded one/two-line summary of what the diff changed, parent->child."""
    if parent_spec is None:
        return None
    p_by = {s["number"]: s for s in parent_spec["steps"]}
    c_by = {s["number"]: s for s in child_spec["steps"]}
    added_steps = len(set(c_by) - set(p_by))
    removed_steps = len(set(p_by) - set(c_by))
    changed = sum(1 for n in set(p_by) & set(c_by) if node_changed(p_by[n], c_by[n]))
    p_edges, c_edges = dep_edges(parent_spec), dep_edges(child_spec)
    deps_added = len(c_edges - p_edges)
    deps_removed = len(p_edges - c_edges)
    p_tool = sum(1 for s in parent_spec["steps"] if s["step_type"] == "tool")
    c_tool = sum(1 for s in child_spec["steps"] if s["step_type"] == "tool")
    bits = []
    if added_steps:
        bits.append(f"+{added_steps} step")
    if removed_steps:
        bits.append(f"−{removed_steps} step")
    if changed:
        bits.append(f"{changed} step{'s' if changed != 1 else ''} rewritten")
    if c_tool != p_tool:
        bits.append(f"{c_tool - p_tool:+d} tool step")
    if deps_added:
        bits.append(f"+{deps_added} dep")
    if deps_removed:
        bits.append(f"−{deps_removed} dep")
    return "\n".join(textwrap.wrap(" · ".join(bits) or "no structural change", 34))


def draw_arc(ax, cx, y0, y1, color, lw, dashed):
    span = abs(y1 - y0) / PY
    rad = min(0.5, 0.13 + 0.11 * span)
    ax.add_patch(
        mpatches.FancyArrowPatch(
            (cx, y0),
            (cx, y1),
            connectionstyle=f"arc3,rad={rad}",
            arrowstyle="-|>",
            mutation_scale=11,
            lw=lw,
            color=color,
            linestyle=((0, (4, 2)) if dashed else "solid"),
            shrinkA=9,
            shrinkB=9,
            zorder=2,
        )
    )


def draw_graph_column(ax, cx, spec, parent, header, diff_line):
    steps = spec["steps"]
    ys = {s["number"]: -0.5 - s["number"] * PY for s in steps}
    edges = dep_edges(spec)
    p_edges = dep_edges(parent) if parent else set()
    added = edges - p_edges if parent else set()
    removed = p_edges - edges if parent else set()
    pby = {s["number"]: s for s in parent["steps"]} if parent else {}

    for d, s in edges:
        is_add = (d, s) in added
        draw_arc(
            ax,
            cx,
            ys[d],
            ys[s],
            ADD if is_add else NEUTRAL,
            2.6 if is_add else 1.4,
            dashed=False,
        )
    for d, s in removed:
        if d in ys and s in ys:
            draw_arc(ax, cx, ys[d], ys[s], REM, 1.9, dashed=True)

    for s in steps:
        n, y = s["number"], ys[s["number"]]
        is_tool = s["step_type"] == "tool"
        changed = parent is not None and (n not in pby or node_changed(pby[n], s))
        ax.add_patch(
            mpatches.Circle(
                (cx, y),
                NODE_R,
                facecolor=TOOL_TINT if is_tool else LLM_TINT,
                edgecolor=CHANGED_EDGE if changed else "#33373B",
                linewidth=3.0 if changed else 1.3,
                zorder=5,
            )
        )
        ax.text(
            cx,
            y,
            str(n),
            ha="center",
            va="center",
            fontsize=10.5,
            fontweight="bold",
            color=TOOL_FILL if is_tool else LLM_FILL,
            zorder=6,
        )
        ax.text(
            cx + NODE_R + 0.13,
            y,
            wrap_label(role_label(s)),
            ha="left",
            va="center",
            fontsize=8.3,
            color="#15181B",
            zorder=6,
        )

    ax.text(
        cx,
        -0.05,
        header,
        ha="center",
        va="top",
        fontsize=11.5,
        fontweight="bold",
        color="#15181B",
    )
    if diff_line:
        ax.text(
            cx,
            -0.95,
            diff_line,
            ha="center",
            va="top",
            fontsize=8.4,
            color="#5A6472",
            style="italic",
            zorder=6,
        )


def main():
    chain = load_chain()
    specs = [r["spec"] for r in chain]
    fits = [r["fitness"] for r in chain]
    labels = [r["label"] for r in chain]

    columns = []
    for i, r in enumerate(chain):
        parent = specs[i - 1] if i > 0 else None
        d = (
            None
            if i == 0 or fits[i] is None or fits[i - 1] is None
            else fits[i] - fits[i - 1]
        )
        hdr = labels[i]
        if fits[i] is not None:
            hdr += f"\nfitness {fits[i]:.3f}"
        if d is not None:
            hdr += f"   Δ{d:+.3f}"
        columns.append((specs[i], parent, hdr, change_summary(parent, specs[i])))

    ncol = len(columns)
    maxsteps = max(len(s["steps"]) for s in specs)
    fig, ax = plt.subplots(figsize=(3.7 * ncol + 1.5, 1.05 * maxsteps + 3.0))
    for c, (spec, parent, header, diff_line) in enumerate(columns):
        draw_graph_column(ax, c * PX, spec, parent, header, diff_line)

    legend = [
        mpatches.Patch(
            facecolor=TOOL_TINT,
            edgecolor="#33373B",
            label="tool step (retrieve / retrieve_deep)",
        ),
        mpatches.Patch(facecolor=LLM_TINT, edgecolor="#33373B", label="LLM step"),
        mpatches.Patch(
            facecolor="white",
            edgecolor=CHANGED_EDGE,
            linewidth=2.6,
            label="node changed vs previous generation",
        ),
        plt.Line2D([0], [0], color=NEUTRAL, lw=1.6, label="dependency (kept)"),
        plt.Line2D([0], [0], color=ADD, lw=2.6, label="dependency added"),
        plt.Line2D([0], [0], color=REM, lw=1.9, ls="--", label="dependency removed"),
    ]
    ax.legend(
        handles=legend,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.05),
        ncol=3,
        fontsize=9.5,
        frameon=False,
        handletextpad=0.6,
        columnspacing=1.8,
    )
    ax.set_xlim(-1.3, (ncol - 1) * PX + 2.6)
    ax.set_ylim(-1.05 * maxsteps - 2.2, 0.9)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.suptitle(
        "Qwen3-235B arm B lineage as a dependency graph — each column is one "
        "program, arrows are step `dependencies`\n"
        "(changed nodes outlined red; green edge = dependency added; "
        "dashed red = removed; grounded change summary under each child)",
        fontsize=12.5,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = HERE / "lineage_graph_qwen.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    main()
