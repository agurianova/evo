"""Render a dag_tab lineage seed->...->best as (1) a node-link dependency graph
per generation, (2) a node x generation evolution matrix carrying the mutator's
own stated diffs, and (3) a field-level diff sequence.

Reads viz/<arm>_lineage_*.json written by extract_lineage.py.

Usage: python make_lineage_viz.py <arm-slug>
"""

import json
from pathlib import Path
import sys
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
VIZ = HERE / "viz"

ROWWISE_FILL = "#1F4E79"
AGG_FILL = "#C9720B"
ROWWISE_TINT = "#DCE6F4"
AGG_TINT = "#FBE7CF"
CHANGED_EDGE = "#B42318"
ADD = "#1A7F37"
REM = "#B42318"
MOD = "#C9720B"
NEUTRAL = "#9AA5B1"
GRID_EDGE = "#C2C8D0"
CARD_BG = "#FBF4EA"
CARD_EDGE = "#D9C7B0"

NODE_FIELDS = (
    "kind",
    "input_cols",
    "output_cols",
    "code",
    "dependencies",
    "is_output",
    "rationale",
)


NODE_DEFAULTS = {"kind": "rowwise", "dependencies": [], "is_output": False}


def normalise(node):
    """Fill schema defaults before any comparison.

    An omitted optional field and its default are the same genome, so leaving
    them unfilled would paint an untouched node as changed.
    """

    return {**NODE_DEFAULTS, **{k: v for k, v in node.items() if v is not None}}


def load(arm):
    records = []
    for path in sorted(VIZ.glob(f"{arm}_lineage_*.json")):
        rec = json.loads(path.read_text())
        rec["graph"]["nodes"] = [normalise(n) for n in rec["graph"]["nodes"]]
        records.append(rec)
    return records


def nodes_by_id(graph):
    return {n["id"]: n for n in graph["nodes"]}


def consumed_edges(graph):
    """Edges the executor actually honours: a declared parent counts only when the
    child reads one of its output columns.  Declared-but-unread edges inflate
    depth without composing anything, so drawing them would overstate structure."""
    raw = set(graph.get("raw_columns") or [])
    by_id = nodes_by_id(graph)
    edges = set()
    for node in graph["nodes"]:
        generated_inputs = set(node["input_cols"]) - raw
        for dep in node.get("dependencies") or []:
            parent = by_id.get(dep)
            if parent and generated_inputs & set(parent["output_cols"]):
                edges.add((dep, node["id"]))
    return edges


def node_fields(node):
    return {k: json.dumps(node.get(k), sort_keys=True) for k in NODE_FIELDS}


def node_changed(parent_node, child_node):
    return node_fields(parent_node) != node_fields(child_node)


def node_change_tags(parent_node, child_node):
    if parent_node is None:
        cols = ", ".join(child_node["output_cols"])
        return ["NEW NODE", f"→ {cols}"]
    lines = []
    if parent_node.get("kind") != child_node.get("kind"):
        lines.append(f"→ kind {child_node['kind']}")
    if parent_node["output_cols"] != child_node["output_cols"]:
        lines.append("→ " + ", ".join(child_node["output_cols"]))
    if parent_node["input_cols"] != child_node["input_cols"]:
        lines.append("inputs → " + ", ".join(child_node["input_cols"]))
    if parent_node.get("code") != child_node.get("code"):
        lines.append("~ code rewritten")
    if (parent_node.get("dependencies") or []) != (
        child_node.get("dependencies") or []
    ):
        lines.append(f"deps → {child_node.get('dependencies') or []}")
    if parent_node.get("is_output") != child_node.get("is_output"):
        lines.append(f"is_output → {child_node['is_output']}")
    if parent_node.get("rationale") != child_node.get("rationale"):
        lines.append("~ rationale")
    return lines


def row_order(records):
    """Stable row slot per node id: generation order first, then first appearance."""
    order = []
    for rec in records:
        for node in rec["graph"]["nodes"]:
            if node["id"] not in order:
                order.append(node["id"])
    return order


def header_for(rec, prev, narrow=False):
    gen = rec["generation"]
    label = "seed" if prev is None else f"gen {gen}"
    lines = [f"{label}   ({rec['id'][:8]})", f"CV R² {rec['fitness']:.6f}"]
    if prev is not None:
        lines.append(f"Δ {rec['fitness'] - prev['fitness']:+.6f}")
    n = int(rec["node_count"])
    f = int(rec["generated_feature_count"])
    stats = [
        f"{n} node{'s' if n != 1 else ''} · depth {rec['max_depth']:.0f}",
        f"{f} feature{'s' if f != 1 else ''}",
    ]
    lines.extend(stats if narrow else [" · ".join(stats)])
    return "\n".join(lines)


def wrap_label(s, width=17):
    return "\n".join(textwrap.wrap(s, width=width, break_long_words=False) or [s])


PX = 4.6
PY = 1.30
NODE_R = 0.36


def draw_arc(ax, cx, y0, y1, color, lw, dashed):
    span = abs(y1 - y0) / PY
    rad = min(0.5, 0.16 + 0.12 * span)
    ax.add_patch(
        mpatches.FancyArrowPatch(
            (cx, y0),
            (cx, y1),
            connectionstyle=f"arc3,rad={rad}",
            arrowstyle="-|>",
            mutation_scale=12,
            lw=lw,
            color=color,
            linestyle=((0, (4, 2)) if dashed else "solid"),
            shrinkA=10,
            shrinkB=10,
            zorder=2,
        )
    )


TOP_Y = -2.35


def draw_graph_column(ax, cx, rec, prev, header, note, note_y):
    graph = rec["graph"]
    nodes = graph["nodes"]
    ys = {n["id"]: TOP_Y - i * PY for i, n in enumerate(nodes)}
    edges = consumed_edges(graph)
    p_edges = consumed_edges(prev["graph"]) if prev else set()
    added = edges - p_edges if prev else set()
    removed = p_edges - edges if prev else set()
    pby = nodes_by_id(prev["graph"]) if prev else {}

    for d, s in edges:
        is_add = (d, s) in added
        draw_arc(
            ax,
            cx,
            ys[d],
            ys[s],
            ADD if is_add else NEUTRAL,
            2.8 if is_add else 1.4,
            False,
        )
    for d, s in removed:
        if d in ys and s in ys:
            draw_arc(ax, cx, ys[d], ys[s], REM, 2.0, True)

    for node in nodes:
        y = ys[node["id"]]
        is_agg = node.get("kind") != "rowwise"
        changed = prev is not None and (
            node["id"] not in pby or node_changed(pby[node["id"]], node)
        )
        ax.add_patch(
            mpatches.Circle(
                (cx, y),
                NODE_R,
                facecolor=AGG_TINT if is_agg else ROWWISE_TINT,
                edgecolor=CHANGED_EDGE if changed else "#33373B",
                linewidth=3.0 if changed else 1.3,
                zorder=5,
            )
        )
        ax.text(
            cx,
            y,
            "A" if is_agg else "R",
            ha="center",
            va="center",
            fontsize=10.5,
            fontweight="bold",
            color=AGG_FILL if is_agg else ROWWISE_FILL,
            zorder=6,
        )
        ax.text(
            cx + NODE_R + 0.16,
            y + 0.16,
            wrap_label(node["id"]),
            ha="left",
            va="center",
            fontsize=8.6,
            fontweight="semibold",
            color="#15181B",
            zorder=6,
        )
        ax.text(
            cx + NODE_R + 0.16,
            y + 0.02,
            wrap_label(", ".join(node["output_cols"]), 22),
            ha="left",
            va="top",
            fontsize=7.4,
            color="#5A6472",
            family="monospace",
            zorder=6,
        )

    ax.text(
        cx,
        -0.10,
        header,
        ha="center",
        va="top",
        fontsize=11,
        fontweight="bold",
        color="#15181B",
    )
    if note:
        ax.text(
            cx - 0.9,
            note_y,
            note,
            ha="left",
            va="top",
            fontsize=8.0,
            color="#5A6472",
            style="italic",
            zorder=6,
        )


def diff_note(rec, width=42, maxlines=14):
    changes = rec["llm_diff"].get("changes") or []
    lines = []
    for c in changes:
        text = c.get("description") if isinstance(c, dict) else str(c)
        wrapped = textwrap.wrap(text, width=width) or [text]
        lines.append("• " + wrapped[0])
        lines.extend("  " + w for w in wrapped[1:])
    if len(lines) > maxlines:
        lines = lines[: maxlines - 1] + ["  …"]
    return "\n".join(lines)


def make_graph_figure(arm, records):
    n = len(records)
    depth = max(len(r["graph"]["nodes"]) for r in records)
    note_y = TOP_Y - PY * (depth - 1) - 0.95
    fig, ax = plt.subplots(figsize=(3.9 * n, 4.0 + 1.05 * depth))
    for i, rec in enumerate(records):
        prev = records[i - 1] if i else None
        draw_graph_column(
            ax,
            i * PX,
            rec,
            prev,
            header_for(rec, prev),
            diff_note(rec) if prev else None,
            note_y,
        )

    legend = [
        mpatches.Patch(
            facecolor=ROWWISE_TINT, edgecolor="#33373B", label="rowwise node (R)"
        ),
        mpatches.Patch(
            facecolor=AGG_TINT, edgecolor="#33373B", label="aggregate node (A)"
        ),
        mpatches.Patch(
            facecolor="white",
            edgecolor=CHANGED_EDGE,
            linewidth=2.6,
            label="node new or changed vs previous generation",
        ),
        plt.Line2D([0], [0], color=NEUTRAL, lw=1.6, label="consumed dependency (kept)"),
        plt.Line2D([0], [0], color=ADD, lw=2.8, label="dependency added"),
        plt.Line2D([0], [0], color=REM, lw=2.0, ls="--", label="dependency removed"),
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
    ax.set_xlim(-1.5, (n - 1) * PX + 3.4)
    ax.set_ylim(note_y - 3.1, 0.6)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.suptitle(
        "dag_tab lineage as a feature-DAG — each column is one genome, arrows are "
        "dependencies the executor actually consumes\n"
        "seed → best child; italic text under each column is the mutator's own "
        "description of the change it proposed",
        fontsize=12.5,
        fontweight="bold",
        y=0.985,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = HERE / f"{arm}_lineage_graph.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


def draw_diff_card(ax, xl, xr, yt, yb, header, subtitle, body_lines, accent):
    ax.add_patch(
        mpatches.FancyBboxPatch(
            (xl, yb),
            xr - xl,
            yt - yb,
            boxstyle="round,pad=0.008,rounding_size=0.06",
            facecolor=CARD_BG,
            edgecolor=CARD_EDGE,
            linewidth=1.2,
            zorder=3,
        )
    )
    ax.add_patch(
        mpatches.Rectangle(
            (xl, yt - 0.15), xr - xl, 0.15, facecolor=accent, edgecolor="none", zorder=4
        )
    )
    tx = xl + 0.06
    ax.text(
        tx,
        yt - 0.30,
        header,
        ha="left",
        va="top",
        fontsize=8.6,
        fontweight="bold",
        color="#15181B",
        zorder=5,
    )
    ax.text(
        tx,
        yt - 0.55,
        subtitle,
        ha="left",
        va="top",
        fontsize=7.6,
        style="italic",
        color="#7A5A12",
        zorder=5,
    )
    y = yt - 0.80
    for ln in body_lines:
        ax.text(tx, y, ln, ha="left", va="top", fontsize=7.1, color="#33373B", zorder=5)
        y -= 0.145


def card_body(rec, width=34, maxlines=17):
    lines = []
    for c in rec["llm_diff"].get("changes") or []:
        text = c.get("description") if isinstance(c, dict) else str(c)
        wrapped = textwrap.wrap(text, width=width) or [text]
        lines.append("• " + wrapped[0])
        lines.extend("  " + w for w in wrapped[1:])
    if len(lines) > maxlines:
        lines = lines[: maxlines - 1] + ["…"]
    return lines


def make_matrix_figure(arm, records):
    order = row_order(records)
    ncols, nrows = len(records), len(order)
    byid = [nodes_by_id(r["graph"]) for r in records]

    fig, ax = plt.subplots(figsize=(2.6 * ncols + 1.0, 1.35 * nrows + 5.2))
    pad = 0.05
    for j, rec in enumerate(records):
        prev = records[j - 1] if j else None
        ax.text(
            j + 0.5,
            nrows + 0.30,
            header_for(rec, prev, narrow=True),
            ha="center",
            va="bottom",
            fontsize=10.0,
            fontweight="bold",
        )
        for i, node_id in enumerate(order):
            node = byid[j].get(node_id)
            yb = nrows - 1 - i
            if node is None:
                ax.add_patch(
                    mpatches.Rectangle(
                        (j + pad, yb + pad),
                        1 - 2 * pad,
                        1 - 2 * pad,
                        facecolor="#F4F5F7",
                        edgecolor=GRID_EDGE,
                        linewidth=1.0,
                    )
                )
                ax.text(
                    j + 0.5,
                    yb + 0.5,
                    "—",
                    ha="center",
                    va="center",
                    fontsize=12,
                    color=NEUTRAL,
                )
                continue
            is_agg = node.get("kind") != "rowwise"
            changed = j > 0 and (
                node_id not in byid[j - 1] or node_changed(byid[j - 1][node_id], node)
            )
            ax.add_patch(
                mpatches.Rectangle(
                    (j + pad, yb + pad),
                    1 - 2 * pad,
                    1 - 2 * pad,
                    facecolor=AGG_TINT if is_agg else ROWWISE_TINT,
                    edgecolor=CHANGED_EDGE if changed else GRID_EDGE,
                    linewidth=2.6 if changed else 1.0,
                    zorder=1,
                )
            )
            ax.add_patch(
                mpatches.Rectangle(
                    (j + pad, yb + pad),
                    0.055,
                    1 - 2 * pad,
                    facecolor=AGG_FILL if is_agg else ROWWISE_FILL,
                    edgecolor="none",
                    zorder=2,
                )
            )
            ax.text(
                j + 0.13,
                yb + 0.88,
                node_id,
                ha="left",
                va="top",
                fontsize=8.4,
                fontweight="bold",
                color="#15181B",
            )
            deps = node.get("dependencies") or []
            ax.text(
                j + 0.13,
                yb + 0.70,
                f"deps {deps if deps else '∅'}",
                ha="left",
                va="top",
                fontsize=7.2,
                color="#5A6472",
                family="monospace",
            )
            if changed:
                sub = []
                for tag in node_change_tags(
                    byid[j - 1].get(node_id) if j else None, node
                ):
                    sub.extend(
                        textwrap.wrap(tag, width=22, subsequent_indent="  ") or [tag]
                    )
                for k, sl in enumerate(sub[:5]):
                    ax.text(
                        j + 0.13,
                        yb + 0.54 - 0.105 * k,
                        sl,
                        ha="left",
                        va="top",
                        fontsize=7.2,
                        color=CHANGED_EDGE,
                        family="monospace",
                    )

    for i, node_id in enumerate(order):
        ax.text(
            -0.06,
            nrows - 1 - i + 0.5,
            f"#{i + 1}",
            ha="right",
            va="center",
            fontsize=9.5,
            fontweight="bold",
            color="#33373B",
        )

    card_yt, card_yb = -0.55, -4.15
    ax.text(
        0.06,
        -0.50,
        "LLM mutator's stated diff\nfor each new generation  →",
        ha="left",
        va="top",
        fontsize=9.6,
        fontweight="bold",
        color="#15181B",
    )
    ax.text(
        0.06,
        -1.35,
        "the change descriptions the\n"
        "structured-diff operator emitted\n"
        "as it proposed each child — its\n"
        "own words, not a reconstruction.\n\n"
        "the seed carries no diff card.",
        ha="left",
        va="top",
        fontsize=8.4,
        color="#4A5462",
    )
    for j in range(1, ncols):
        rec, prev = records[j], records[j - 1]
        body = card_body(rec)
        if not body:
            continue
        d = rec["fitness"] - prev["fitness"]
        draw_diff_card(
            ax,
            j + 0.06,
            j + 0.94,
            card_yt,
            card_yb,
            f"→ gen {rec['generation']}   Δ{d:+.6f}",
            rec["llm_diff"].get("archetype") or "structured slot diff",
            body,
            ADD if d >= 0 else REM,
        )

    legend = [
        mpatches.Patch(
            facecolor=ROWWISE_TINT, edgecolor=ROWWISE_FILL, label="rowwise node"
        ),
        mpatches.Patch(facecolor=AGG_TINT, edgecolor=AGG_FILL, label="aggregate node"),
        mpatches.Patch(
            facecolor="white",
            edgecolor=CHANGED_EDGE,
            linewidth=2.6,
            label="new or changed vs previous generation",
        ),
        mpatches.Patch(
            facecolor=CARD_BG,
            edgecolor=CARD_EDGE,
            label="mutator's stated diff (below each generation)",
        ),
    ]
    ax.legend(
        handles=legend,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.005),
        ncol=2,
        fontsize=9,
        frameon=False,
        handletextpad=0.6,
    )
    ax.set_xlim(-0.5, ncols)
    ax.set_ylim(card_yb - 0.35, nrows + 1.45)
    ax.axis("off")
    fig.suptitle(
        "dag_tab lineage — feature-DAG evolution matrix (node × generation) paired "
        "with the mutator's stated diffs\n"
        "top: cell colour = node kind · red outline = new/changed vs parent · red text "
        "= exact field changes   |   bottom: the LLM's own diff description",
        fontsize=12,
        fontweight="bold",
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    out = HERE / f"{arm}_lineage_matrix.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


def field_level_diff(parent, child):
    diffs = []
    p_by, c_by = nodes_by_id(parent["graph"]), nodes_by_id(child["graph"])
    for node_id in list(p_by) + [k for k in c_by if k not in p_by]:
        if node_id not in c_by:
            diffs.append(
                (node_id, "node", "remove", p_by[node_id]["output_cols"], None)
            )
            continue
        if node_id not in p_by:
            diffs.append((node_id, "node", "add", None, c_by[node_id]["output_cols"]))
            for field in ("kind", "input_cols", "code", "dependencies"):
                diffs.append((node_id, field, "add", None, c_by[node_id].get(field)))
            continue
        for field in NODE_FIELDS:
            pv, cv = p_by[node_id].get(field), c_by[node_id].get(field)
            if pv != cv:
                diffs.append((node_id, field, "mod", pv, cv))
    ptarget, ctarget = parent["graph"].get("target"), child["graph"].get("target")
    if ptarget != ctarget:
        diffs.append(("<target>", "target", "mod", ptarget, ctarget))
    return diffs


def fmt(v, limit=68):
    if isinstance(v, (dict, list)):
        v = json.dumps(v)
    s = "∅" if v in (None, "") else str(v)
    return s.replace("\n", " ⏎ ")[:limit] + ("…" if len(str(s)) > limit else "")


def diff_rows(diffs):
    kind_color = {"add": ADD, "remove": REM, "mod": MOD}
    kind_sym = {"add": "+", "remove": "−", "mod": "~"}
    rows, cur = [], None
    for node_id, field, kind, pv, cv in diffs:
        if node_id != cur:
            cur = node_id
            rows.append((0.0, node_id, "#33373B", 10.0, "bold", False))
        rows.append(
            (0.03, f"{kind_sym[kind]} {field}", kind_color[kind], 8.8, "bold", False)
        )
        if kind == "mod":
            rows.append((0.06, f"− {fmt(pv)}", REM, 7.2, "normal", True))
            rows.append((0.06, f"+ {fmt(cv)}", ADD, 7.2, "normal", True))
        else:
            rows.append(
                (
                    0.06,
                    fmt(cv if kind == "add" else pv),
                    kind_color[kind],
                    7.2,
                    "normal",
                    True,
                )
            )
    return rows


def make_diff_figure(arm, records):
    transitions = [(records[i - 1], records[i]) for i in range(1, len(records))]
    col_rows = [diff_rows(field_level_diff(p, c)) for p, c in transitions]
    max_rows = max(len(r) for r in col_rows)
    dy = 0.965 / max_rows
    ratios = [max(0.5, len(r)) for r in col_rows]

    fig, axes = plt.subplots(
        1,
        len(transitions),
        figsize=(4.6 * len(transitions), 1.0 + 0.16 * max_rows),
        gridspec_kw={"width_ratios": ratios},
    )
    axes = [axes] if len(transitions) == 1 else list(axes)
    for ax, (p, c), rows in zip(axes, transitions, col_rows):
        ax.axis("off")
        ax.set_title(
            f"gen {p['generation']} → gen {c['generation']}   Δfit {c['fitness'] - p['fitness']:+.6f}",
            fontsize=11,
            fontweight="bold",
        )
        y = 0.975
        for indent, text, color, size, weight, mono in rows:
            ax.text(
                indent,
                y,
                text,
                fontsize=size,
                color=color,
                fontweight=weight,
                family="monospace" if mono else "sans-serif",
                transform=ax.transAxes,
            )
            y -= dy

    fig.suptitle(
        "dag_tab — sequence of structured slot-diffs from seed to best child\n"
        "(green = added, red = removed, orange = modified; − old value / + new value)",
        fontsize=12,
        fontweight="bold",
        y=0.998,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = HERE / f"{arm}_lineage_diffs.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    arm = sys.argv[1]
    records = load(arm)
    make_graph_figure(arm, records)
    make_matrix_figure(arm, records)
    make_diff_figure(arm, records)
