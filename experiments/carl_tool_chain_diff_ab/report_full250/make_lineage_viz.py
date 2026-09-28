"""Render the arm-B lineage base->gen1->gen2->gen3->gen4(best) as (1) a row of
colored DAGs with per-generation changed nodes/edges highlighted, and (2) a
colored field-level diff sequence.  Reads viz/lineage_*.json (extracted specs).

Usage: python make_lineage_viz.py   (run inside report_full250/)
"""

import json
from pathlib import Path
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx

HERE = Path(__file__).parent
VIZ = HERE / "viz"

TOOL_FILL = "#1F4E79"
LLM_FILL = "#C9720B"
CHANGED_EDGE = "#B42318"
ADD = "#1A7F37"
REM = "#B42318"
MOD = "#C9720B"
NEUTRAL = "#9AA5B1"

FILES = [
    ("lineage_00_base.json", "base seed", None),
    ("lineage_01_gen1.json", "gen 1", 0.753),
    ("lineage_02_gen2.json", "gen 2", 0.847),
    ("lineage_03_gen3.json", "gen 3", 0.856),
    ("lineage_04_gen4_best.json", "gen 4  (best)", 0.858),
]


def load(f):
    d = json.loads((VIZ / f).read_text())
    return d.get("spec", d)


def load_full(f):
    return json.loads((VIZ / f).read_text())


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


def node_changed(parent_step, child_step):
    return step_fields(parent_step) != step_fields(child_step)


def _short_tool(name):
    return {"retrieve_deep": "retr_deep"}.get(name, name)


def node_change_tags(pstep, cstep):
    """Grouped field-change lines for a cell (modified LLM fields collapse to one).

    So a cell shows WHICH fields mutated, not just that it changed, without one
    line per field blowing past the cell height.
    """
    if pstep is None:
        return ["NEW STEP"]
    cs_type = cstep["step_type"]
    lines = []
    if pstep["step_type"] != cs_type:
        lines.append(f"→ became {cs_type}")
    if cs_type == "tool":
        cc = cstep["step_config"]
        pc = pstep.get("step_config") or {}
        if pstep["step_type"] != "tool" or pc.get("tool_name") != cc["tool_name"]:
            lines.append(f"→ {_short_tool(cc['tool_name'])}")
        pmap = pc.get("input_mapping") if pstep["step_type"] == "tool" else None
        if pmap != cc["input_mapping"]:
            lines.append("~ query rewritten")
    else:
        mods = [
            lbl
            for k, lbl in (
                ("aim", "aim"),
                ("stage_action", "action"),
                ("reasoning_questions", "questions"),
                ("title", "title"),
            )
            if pstep.get(k) != cstep.get(k)
        ]
        if mods:
            lines.append("~ " + ", ".join(mods))
    if tuple(pstep["dependencies"]) != tuple(cstep["dependencies"]):
        lines.append(f"deps → {list(cstep['dependencies'])}")
    return lines


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


YSCALE = 1.25


def draw_dag(ax, spec, parent_spec, title, fitness):
    g = nx.DiGraph()
    steps = spec["steps"]
    for s in steps:
        g.add_node(s["number"])
    edges = dep_edges(spec)
    g.add_edges_from(edges)

    p_edges = dep_edges(parent_spec) if parent_spec else edges
    added = edges - p_edges
    removed = p_edges - edges

    # vertical layout by step number; nudge x by parity to fan the arcs out
    pos = {
        s["number"]: (0.12 if s["number"] % 2 else -0.12, -YSCALE * s["number"])
        for s in steps
    }

    pstep_by_num = {s["number"]: s for s in parent_spec["steps"]} if parent_spec else {}
    node_face, node_edge, node_lw, changed_by = [], [], [], {}
    for s in steps:
        node_face.append(TOOL_FILL if s["step_type"] == "tool" else LLM_FILL)
        changed = parent_spec is not None and (
            s["number"] not in pstep_by_num
            or node_changed(pstep_by_num[s["number"]], s)
        )
        changed_by[s["number"]] = changed
        node_edge.append(CHANGED_EDGE if changed else "#33373B")
        node_lw.append(3.6 if changed else 1.1)

    nx.draw_networkx_nodes(
        g,
        pos,
        ax=ax,
        node_size=1550,
        node_color=node_face,
        edgecolors=node_edge,
        linewidths=node_lw,
    )
    # unchanged edges
    keep = [e for e in edges if e not in added]
    nx.draw_networkx_edges(
        g,
        pos,
        edgelist=keep,
        ax=ax,
        edge_color=NEUTRAL,
        width=1.6,
        arrows=True,
        arrowsize=14,
        node_size=1550,
        connectionstyle="arc3,rad=0.16",
    )
    # added edges (present in child, not parent)
    if added:
        nx.draw_networkx_edges(
            g,
            pos,
            edgelist=list(added),
            ax=ax,
            edge_color=ADD,
            width=3.0,
            arrows=True,
            arrowsize=16,
            node_size=1550,
            connectionstyle="arc3,rad=0.16",
        )
    # removed edges (in parent, gone in child) — draw dashed on child layout
    if removed:
        rg = nx.DiGraph()
        rg.add_nodes_from(g.nodes())
        rg.add_edges_from([e for e in removed if e[0] in pos and e[1] in pos])
        nx.draw_networkx_edges(
            rg,
            pos,
            ax=ax,
            edge_color=REM,
            width=2.2,
            style="dashed",
            arrows=True,
            arrowsize=14,
            node_size=1550,
            connectionstyle="arc3,rad=-0.28",
        )
    labels = {s["number"]: str(s["number"]) for s in steps}
    nx.draw_networkx_labels(
        g, pos, labels, ax=ax, font_size=12, font_color="white", font_weight="bold"
    )

    xt = 0.34
    for s in steps:
        _, y = pos[s["number"]]
        ax.text(
            xt,
            y + 0.20,
            side_label(s),
            fontsize=9.2,
            va="bottom",
            ha="left",
            color="#1A1D20",
            fontweight="semibold",
        )
        if changed_by.get(s["number"]):
            tags = node_change_tags(pstep_by_num.get(s["number"]), s)
            for j, tag in enumerate(tags[:5]):
                ax.text(
                    xt,
                    y - 0.02 - 0.165 * j,
                    tag,
                    fontsize=8.0,
                    va="top",
                    ha="left",
                    color=CHANGED_EDGE,
                    family="monospace",
                )
            if len(tags) > 5:
                ax.text(
                    xt,
                    y - 0.02 - 0.165 * 5,
                    "…",
                    fontsize=8.0,
                    va="top",
                    ha="left",
                    color=CHANGED_EDGE,
                )

    ntool = sum(1 for s in steps if s["step_type"] == "tool")
    sub = f"{len(steps)} steps · {ntool} tool"
    if fitness is not None:
        sub += f"  ·  fitness {fitness:.3f}"
    ax.set_title(title, fontsize=13.5, fontweight="bold", pad=8)
    ax.text(
        0.5,
        -0.015,
        sub,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=9.8,
        color="#33373B",
    )
    ax.set_xlim(-0.5, 2.05)
    ax.set_ylim(-YSCALE * 7 - 0.95, -YSCALE + 0.55)
    ax.axis("off")


def make_dag_figure():
    specs = [load(f) for f, _, _ in FILES]
    fig, axes = plt.subplots(1, 5, figsize=(7.4, 10.4))
    for i, (ax, (_, title, fit)) in enumerate(zip(axes, FILES)):
        parent = specs[i - 1] if i > 0 else None
        draw_dag(ax, specs[i], parent, title, fit)

    legend = [
        mpatches.Patch(color=TOOL_FILL, label="tool step (retrieve / retrieve_deep)"),
        mpatches.Patch(color=LLM_FILL, label="LLM step"),
        mpatches.Patch(
            edgecolor=CHANGED_EDGE,
            facecolor="white",
            linewidth=2.6,
            label="node changed vs parent",
        ),
        plt.Line2D([0], [0], color=ADD, lw=2.6, label="dependency added"),
        plt.Line2D([0], [0], color=REM, lw=1.8, ls="--", label="dependency removed"),
        plt.Line2D([0], [0], color=NEUTRAL, lw=1.3, label="dependency kept"),
    ]
    fig.legend(
        handles=legend,
        loc="lower center",
        ncol=3,
        fontsize=9.2,
        frameon=False,
        bbox_to_anchor=(0.5, 0.005),
    )
    fig.suptitle(
        "arm B lineage — evolving retrieval-chain DAG\n"
        "(changed nodes outlined red; red monospace tags = which fields changed; "
        "colored edges = dependency changes)",
        fontsize=12,
        fontweight="bold",
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0.055, 1, 0.955))
    out = HERE / "lineage_dags.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


def field_level_diff(parent, child):
    """Return list of (step_number, field, kind, parent_val, child_val)."""
    diffs = []
    p_by = {s["number"]: s for s in parent["steps"]}
    c_by = {s["number"]: s for s in child["steps"]}
    for n in sorted(set(p_by) | set(c_by)):
        if n not in p_by:
            diffs.append((n, "step", "add", None, c_by[n]["title"]))
            continue
        if n not in c_by:
            diffs.append((n, "step", "remove", p_by[n]["title"], None))
            continue
        ps, cs = p_by[n], c_by[n]
        keys = [
            "step_type",
            "title",
            "aim",
            "stage_action",
            "reasoning_questions",
            "dependencies",
            "step_config",
        ]
        for k in keys:
            pv, cv = ps.get(k), cs.get(k)
            if pv != cv:
                kind = "mod"
                if pv in (None, "", "<none>") and cv not in (None, "", "<none>"):
                    kind = "add"
                elif cv in (None, "", "<none>") and pv not in (None, "", "<none>"):
                    kind = "remove"
                diffs.append((n, k, kind, pv, cv))
    return diffs


def fmt(v, limit=64):
    if isinstance(v, (dict, list)):
        v = json.dumps(v)
    s = "∅" if v in (None, "") else str(v)
    s = s.replace("\n", " ")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def diff_rows(diffs):
    """Flatten a transition's diffs into a list of drawable rows.

    Each row = (indent, text, color, size, weight, mono).  Pre-counting rows
    lets us size the line spacing so the densest column always fits.
    """
    kind_color = {"add": ADD, "remove": REM, "mod": MOD}
    kind_sym = {"add": "+", "remove": "−", "mod": "~"}
    rows, cur = [], None
    for n, field, kind, pv, cv in diffs:
        if n != cur:
            cur = n
            rows.append((0.0, f"step #{n}", "#33373B", 10.5, "bold", False))
        col = kind_color[kind]
        rows.append((0.03, f"{kind_sym[kind]} {field}", col, 9.2, "bold", False))
        if kind == "mod":
            rows.append((0.06, f"− {fmt(pv)}", REM, 7.6, "normal", True))
            rows.append((0.06, f"+ {fmt(cv)}", ADD, 7.6, "normal", True))
        else:
            rows.append(
                (0.06, fmt(cv if kind == "add" else pv), col, 7.6, "normal", True)
            )
    return rows


def make_diff_figure():
    specs = [load(f) for f, _, _ in FILES]
    titles = [t for _, t, _ in FILES]
    fits = [f for _, _, f in FILES]

    transitions = []
    for i in range(1, len(specs)):
        transitions.append(
            (titles[i - 1], titles[i], specs[i - 1], specs[i], fits[i - 1], fits[i])
        )

    col_rows = [
        diff_rows(field_level_diff(ps, cs)) for (_, _, ps, cs, _, _) in transitions
    ]
    max_rows = max(len(r) for r in col_rows)
    dy = 0.965 / max_rows

    # the base->gen1 no-op column needs almost no width; gen1->gen2 restructures
    # the whole chain and needs the most.
    ratios = [max(0.5, len(r)) for r in col_rows]
    fig, axes = plt.subplots(
        1, len(transitions), figsize=(9.6, 12.4), gridspec_kw={"width_ratios": ratios}
    )
    for ax, (pt, ct, _, _, pf, cf), rows in zip(axes, transitions, col_rows):
        ax.axis("off")
        dfit = "" if pf is None or cf is None else f"  Δfit {cf - pf:+.3f}"
        ax.set_title(f"{pt} → {ct}{dfit}", fontsize=11.5, fontweight="bold")
        if not rows:
            ax.text(
                0.5,
                0.5,
                "identical\n(no-op\nmutation)",
                ha="center",
                va="center",
                fontsize=12,
                color=NEUTRAL,
                style="italic",
                transform=ax.transAxes,
            )
            continue
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
        "arm B — sequence of structured slot-diffs from base seed to best child\n"
        "(green = added field, red = removed field, orange = modified field; "
        "− old value / + new value)",
        fontsize=12,
        fontweight="bold",
        y=0.998,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    out = HERE / "lineage_diffs.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


TOOL_TINT = "#DCE6F4"
LLM_TINT = "#FBE7CF"
GRID_EDGE = "#C2C8D0"
CARD_BG = "#FBF4EA"
CARD_EDGE = "#D9C7B0"


def role_label(step):
    if step["step_type"] == "tool":
        return step["step_config"]["tool_name"]
    return side_label(step)


def card_body(ld, width=33, maxlines=16):
    """The mutator's own diff prose as wrapped lines: bullets when it emitted
    per-change descriptions, else the free-text justification."""
    lines = []
    if ld.get("bullets"):
        for b in ld["bullets"]:
            w = textwrap.wrap(b, width=width) or [b]
            lines.append("• " + w[0])
            lines.extend("  " + c for c in w[1:])
    else:
        lines.extend(textwrap.wrap(ld.get("justification", ""), width=width))
    if len(lines) > maxlines:
        lines = lines[: maxlines - 1] + ["…"]
    return lines


def draw_diff_card(ax, xl, xr, yt, yb, header, archetype, body_lines, accent):
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
        archetype,
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


def make_matrix_figure():
    """A step x generation matrix: rows = pipeline positions, columns = lineage.

    Each cell is colored by step type, outlined red when it changed vs the
    previous generation, and lists the exact fields that changed inside it.
    """
    records = [load_full(f) for f, _, _ in FILES]
    specs = [r.get("spec", r) for r in records]
    diffs = [r.get("llm_diff", {}) for r in records]
    titles = [t for _, t, _ in FILES]
    fits = [f for _, _, f in FILES]
    ncols = len(specs)
    nrows = max(len(s["steps"]) for s in specs)
    byn = [{s["number"]: s for s in sp["steps"]} for sp in specs]

    fig, ax = plt.subplots(figsize=(11.6, 13.6))
    pad = 0.05

    for j in range(ncols):
        x0 = j
        hdr = titles[j] if fits[j] is None else f"{titles[j]}\nfitness {fits[j]:.3f}"
        ax.text(
            x0 + 0.5,
            nrows + 0.30,
            hdr,
            ha="center",
            va="bottom",
            fontsize=12.5,
            fontweight="bold",
        )
        if j > 0 and fits[j] is not None and fits[j - 1] is not None:
            d = fits[j] - fits[j - 1]
            ax.text(
                x0,
                nrows + 0.42,
                f"Δ{d:+.3f}",
                ha="center",
                va="bottom",
                fontsize=9,
                color=(ADD if d >= 0 else REM),
                fontweight="bold",
            )

        for n in range(1, nrows + 1):
            step = byn[j].get(n)
            yb = nrows - n
            if step is None:
                ax.add_patch(
                    mpatches.Rectangle(
                        (x0 + pad, yb + pad),
                        1 - 2 * pad,
                        1 - 2 * pad,
                        facecolor="#F4F5F7",
                        edgecolor=GRID_EDGE,
                        linewidth=1.0,
                    )
                )
                ax.text(
                    x0 + 0.5,
                    yb + 0.5,
                    "—",
                    ha="center",
                    va="center",
                    fontsize=12,
                    color=NEUTRAL,
                )
                continue

            is_tool = step["step_type"] == "tool"
            changed = j > 0 and (
                n not in byn[j - 1] or node_changed(byn[j - 1][n], step)
            )
            ax.add_patch(
                mpatches.Rectangle(
                    (x0 + pad, yb + pad),
                    1 - 2 * pad,
                    1 - 2 * pad,
                    facecolor=TOOL_TINT if is_tool else LLM_TINT,
                    edgecolor=CHANGED_EDGE if changed else GRID_EDGE,
                    linewidth=2.6 if changed else 1.0,
                    zorder=1,
                )
            )
            # type stripe on the left edge of the cell
            ax.add_patch(
                mpatches.Rectangle(
                    (x0 + pad, yb + pad),
                    0.055,
                    1 - 2 * pad,
                    facecolor=TOOL_FILL if is_tool else LLM_FILL,
                    edgecolor="none",
                    zorder=2,
                )
            )

            ax.text(
                x0 + 0.13,
                yb + 0.86,
                role_label(step),
                ha="left",
                va="top",
                fontsize=8.8,
                fontweight="bold",
                color="#15181B",
            )
            deps = step["dependencies"]
            ax.text(
                x0 + 0.13,
                yb + 0.66,
                f"deps {deps if deps else '∅'}",
                ha="left",
                va="top",
                fontsize=7.4,
                color="#5A6472",
                family="monospace",
            )
            if changed:
                sublines = []
                for tag in node_change_tags(byn[j - 1].get(n), step):
                    sublines.extend(
                        textwrap.wrap(tag, width=20, subsequent_indent="  ") or [tag]
                    )
                for k, sl in enumerate(sublines[:7]):
                    ax.text(
                        x0 + 0.13,
                        yb + 0.52 - 0.115 * k,
                        sl,
                        ha="left",
                        va="top",
                        fontsize=7.3,
                        color=CHANGED_EDGE,
                        family="monospace",
                    )

    for n in range(1, nrows + 1):
        ax.text(
            -0.06,
            nrows - n + 0.5,
            f"#{n}",
            ha="right",
            va="center",
            fontsize=9.5,
            fontweight="bold",
            color="#33373B",
        )

    # LLM-diff band: one card per NEW generation, column-aligned under the
    # generation it produced, quoting the mutator's own stated diff.
    card_yt, card_yb = -0.55, -3.55
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
        -1.25,
        "the archetype + change summary the\n"
        "CARL structured-diff operator emitted\n"
        "as it proposed each child — its own\n"
        "words, not a reconstruction.\n\n"
        "base → gen 1 was an identical no-op\n"
        "copy, so it carries no diff card.",
        ha="left",
        va="top",
        fontsize=8.4,
        color="#4A5462",
    )
    for j in range(1, ncols):
        ld = diffs[j]
        if not ld.get("archetype"):
            continue
        d = None if fits[j] is None or fits[j - 1] is None else fits[j] - fits[j - 1]
        dtxt = "" if d is None else f"   Δ{d:+.3f}"
        header = f"→ {titles[j]}{dtxt}"
        draw_diff_card(
            ax,
            j + 0.06,
            j + 0.94,
            card_yt,
            card_yb,
            header,
            ld["archetype"],
            card_body(ld),
            ADD if (d is None or d >= 0) else REM,
        )

    legend = [
        mpatches.Patch(
            facecolor=TOOL_TINT,
            edgecolor=TOOL_FILL,
            label="tool step (retrieve / retrieve_deep)",
        ),
        mpatches.Patch(facecolor=LLM_TINT, edgecolor=LLM_FILL, label="LLM step"),
        mpatches.Patch(
            facecolor="white",
            edgecolor=CHANGED_EDGE,
            linewidth=2.6,
            label="changed vs previous generation",
        ),
        mpatches.Patch(
            facecolor=CARD_BG,
            edgecolor=CARD_EDGE,
            label="mutator's stated diff (below each new generation)",
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
    ax.set_ylim(card_yb - 0.25, nrows + 0.95)
    ax.axis("off")
    fig.suptitle(
        "arm B lineage — chain evolution matrix (step × generation) paired with "
        "the mutator's stated diffs\n"
        "top: cell color = step type · red outline = changed vs parent · red text "
        "= exact field changes   |   bottom: the LLM's own diff description",
        fontsize=12.5,
        fontweight="bold",
        y=0.995,
    )
    fig.tight_layout(rect=(0, 0.02, 1, 0.95))
    out = HERE / "lineage_matrix.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


PX = 3.7
PY = 1.15
NODE_R = 0.34


def wrap_label(s, width=12):
    return "\n".join(textwrap.wrap(s, width=width, break_long_words=False) or [s])


def draw_arc(ax, cx, y0, y1, color, lw, dashed):
    span = abs(y1 - y0) / PY
    rad = min(0.5, 0.13 + 0.11 * span)  # bow left (away from right-side labels)
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
            cx - 0.7,
            ys[max(ys)] - 0.75,
            diff_line,
            ha="left",
            va="top",
            fontsize=8.0,
            color="#5A6472",
            style="italic",
            wrap=False,
            zorder=6,
        )


def make_graph_figure():
    """Node-link lineage: one column per generation, every `dependency` drawn as
    an arc between step-nodes. Added edges green, removed edges dashed red,
    changed nodes outlined red — the structured diff as an actual graph diff."""
    specs = [load(f) for f, _, _ in FILES]
    diffs = [load_full(f).get("llm_diff", {}) for f, _, _ in FILES]  # noqa: F841

    dline = {
        2: "Approach Synthesis: replace the summarise steps\n"
        "with 4 alternating query→retrieve hops; every hop\n"
        "uses retrieve_deep (k=10); add bridging questions.",
        3: "Approach Synthesis: prune slot_4 / slot_6 deps back\n"
        "to the immediate prior hop; embed query-template\n"
        "examples to sharpen term formulation.",
        4: "Approach Synthesis: re-add skip-connections so the\n"
        "query generators see the whole search history;\n"
        "tighten query strings for BM25 recall.",
    }
    # base and gen1 are identical (no-op), so collapse them into one column.
    columns = [
        (specs[1], None, "base ≡ gen 1\nseed · no-op\nfitness 0.753", None),
        (specs[2], specs[1], "gen 2\nfitness 0.847   Δ+0.094", dline[2]),
        (specs[3], specs[2], "gen 3\nfitness 0.856   Δ+0.009", dline[3]),
        (specs[4], specs[3], "gen 4  (best)\nfitness 0.858   Δ+0.002", dline[4]),
    ]

    fig, ax = plt.subplots(figsize=(14.6, 11.4))
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
        bbox_to_anchor=(0.5, 0.045),
        ncol=3,
        fontsize=9.5,
        frameon=False,
        handletextpad=0.6,
        columnspacing=1.8,
    )
    ax.set_xlim(-1.3, 3 * PX + 2.4)
    ax.set_ylim(-11.0, 0.9)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.suptitle(
        "arm B lineage as a dependency graph — each column is one program, "
        "arrows are step `dependencies`\n"
        "base ≡ gen 1 (no-op) → gen 2 rewires every hop → gen 3 prunes "
        "to a linear chain → gen 4 re-adds selective skip-connections",
        fontsize=13,
        fontweight="bold",
        y=0.985,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = HERE / "lineage_graph.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    make_graph_figure()
