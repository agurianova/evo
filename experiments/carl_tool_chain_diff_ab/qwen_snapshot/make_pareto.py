"""Cost / quality Pareto + token-utilization for the CARL mutator A/B.

x-axis  = mutation-model cost only (USD), OpenRouter cheapest per-provider price;
          tokens_out includes reasoning. Executor (Qwen3-8B chain) excluded.
Cost is attributed by `created_at` (the finest wall-clock creation timestamp) —
NOT atomic_counter (non-monotone) or the derived `iteration` field. "Cost to
program" = cumulative ok mutation-call spend through that program's creation.

Consumes pareto_data_qwen.json (built by build_pareto_data.py). INTERIM Qwen
snapshot of the live A/B runs — the gemini report's held-out-test panel is
omitted because no held-out eval has run on the live programs yet.

Figures:
  ab_pareto.png  — cost-to-winner vs train fitness with cost-efficiency
                   trajectories (single panel; no held-out test yet).
  ab_waste.png   — mutation spend split productive (valid child) vs wasted
                   (invalid child), and cost per valid program.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent

MODEL_LABEL = {"gemini": "gemini-3.5-flash", "qwen": "Qwen3-235B-Thinking"}
MODEL_COLOR = {"gemini": "#C9720B", "qwen": "#1F4E79"}
ARM_MARKER = {"A": "o", "B": "D"}
ARM_NAME = {"A": "free rewrite", "B": "CARL diff"}
GREEN = "#2E7D32"
RED = "#C62828"


def load():
    out = {}
    for model in ("gemini", "qwen"):
        f = HERE / f"pareto_data_{model}.json"
        if f.exists():
            out[model] = json.loads(f.read_text())
    return out


def pareto_front(points):
    """Non-dominated set for (minimize x=cost, maximize y=metric)."""
    pts = sorted(points, key=lambda p: (p[0], -p[1]))
    front, best_y = [], -1e9
    for x, y, *rest in pts:
        if y > best_y:
            front.append((x, y, *rest))
            best_y = y
    return front


def pareto_fig(data):
    """Interim Qwen: left cost-to-winner panel only (no held-out test eval yet
    on the live runs, so the gemini report's right panel is intentionally omitted)."""
    fig, axf = plt.subplots(figsize=(7.6, 5.6))
    ys_seen, fpts = [], []
    for model, arms in data.items():
        c = MODEL_COLOR[model]
        for arm in ("A", "B"):
            d = arms[arm]
            pairs = [(x, y) for x, y in d["traj"] if y > 0]
            if pairs:
                axf.plot(
                    [p[0] for p in pairs],
                    [p[1] for p in pairs],
                    color=c,
                    lw=1.1,
                    alpha=0.40,
                    zorder=2,
                )
                ys_seen.extend(p[1] for p in pairs)
            x0, y0 = d["cost_to_winner"], d["winner_fit"]
            fpts.append((x0, y0))
            axf.scatter(
                [x0],
                [y0],
                s=150,
                marker=ARM_MARKER[arm],
                facecolor=(c if arm == "B" else "white"),
                edgecolor=c,
                linewidth=2.0,
                zorder=5,
            )
            off = (9, 8) if arm == "B" else (-9, -20)
            ha = "left" if arm == "B" else "right"
            axf.annotate(
                f"{ARM_NAME[arm]}  ${x0:.2f}\nfit {y0:.3f}",
                (x0, y0),
                textcoords="offset points",
                xytext=off,
                ha=ha,
                fontsize=8.2,
                color="#15181B",
            )
    if ys_seen:
        axf.set_ylim(min(ys_seen) - 0.012, max(ys_seen) + 0.020)
    if len(fpts) >= 2:
        fr = pareto_front(fpts)
        axf.plot(
            [p[0] for p in fr],
            [p[1] for p in fr],
            color="#5A6472",
            lw=1.3,
            ls=(0, (5, 3)),
            zorder=3,
            label="Pareto frontier",
        )
    axf.set_xlabel("mutation-model cost to winner (USD, OpenRouter cheapest)")
    axf.set_ylabel("best train fitness (soft coverage)")
    axf.set_title("Cost-to-winner vs. train fitness  (line = cost-efficiency path)")
    axf.grid(True, alpha=0.25)

    handles = [
        plt.Line2D(
            [],
            [],
            marker="o",
            ls="",
            mfc="white",
            mec="#333",
            label="arm A free rewrite",
        ),
        plt.Line2D(
            [], [], marker="D", ls="", mfc="#333", mec="#333", label="arm B CARL diff"
        ),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=8.5, frameon=False)
    fig.suptitle(
        "Qwen3-235B-Thinking mutator — cost/quality frontier (INTERIM)",
        fontsize=11.5,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    out = HERE / "ab_pareto.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def waste_fig(data):
    labels, prod, waste, cpv, vrate, cols = [], [], [], [], [], []
    for model, arms in data.items():
        for arm in ("A", "B"):
            d = arms[arm]
            labels.append(f"{MODEL_LABEL[model].split('-')[0]}\n{ARM_NAME[arm]}")
            p = d["validity_rate"] * d["total"]
            prod.append(p)
            waste.append(d["total"] - p)
            cpv.append(d["cost_per_valid"])
            vrate.append(d["validity_rate"] * 100)
            cols.append(MODEL_COLOR[model])

    fig, (axs, axc) = plt.subplots(1, 2, figsize=(11.6, 5.0))
    x = range(len(labels))
    b_prod = axs.bar(x, prod, color=GREEN, label="productive (→ valid child)")
    b_waste = axs.bar(
        x, waste, bottom=prod, color=RED, alpha=0.85, label="wasted (→ invalid child)"
    )
    for i, (mdl, arm) in enumerate(
        (m, a) for m, arms in data.items() for a in ("A", "B")
    ):
        d = data[mdl][arm]
        axs.annotate(  # counts inside the green productive band
            f"{d['n_valid']} valid / {d['n_penalty']} bad\n{d['validity_rate'] * 100:.0f}% usable",
            (i, prod[i] * 0.5),
            ha="center",
            va="center",
            fontsize=8.2,
            color="white",
            fontweight="bold",
        )
        if waste[i] > 0.6:
            axs.annotate(
                f"${waste[i]:.1f} wasted",
                (i, prod[i] + waste[i] / 2),
                ha="center",
                va="center",
                fontsize=8.0,
                color="white",
                fontweight="bold",
            )
        else:
            axs.annotate(
                f"${waste[i]:.1f} wasted",
                (i, d["total"]),
                textcoords="offset points",
                xytext=(0, 4),
                ha="center",
                fontsize=8.0,
                color=RED,
                fontweight="bold",
            )
    axs.set_ylim(0, max(d["total"] for m, a in data.items() for d in a.values()) * 1.10)
    axs.set_xticks(list(x))
    axs.set_xticklabels(labels, fontsize=8.5)
    axs.set_ylabel("mutation-model spend (USD)")
    axs.set_title(
        "Where the mutation budget went\n(split est. by valid/invalid child rate)"
    )
    axs.grid(True, axis="y", alpha=0.25)

    axc.bar(x, cpv, color=cols)
    for i, v in enumerate(cpv):
        axc.annotate(
            f"${v:.3f}",
            (i, v),
            textcoords="offset points",
            xytext=(0, 3),
            ha="center",
            fontsize=8.5,
        )
    axc.set_xticks(list(x))
    axc.set_xticklabels(labels, fontsize=8.5)
    axc.set_ylabel("cost per VALID program (USD)")
    axc.set_title("Effective cost per usable program")
    axc.grid(True, axis="y", alpha=0.25)

    fig.legend(
        handles=[b_prod, b_waste],
        fontsize=8.5,
        loc="lower center",
        ncol=2,
        frameon=False,
    )
    fig.suptitle(
        "Mutation-budget utilization (Qwen3-235B-Thinking, INTERIM) — "
        "free rewrite malforms ~11%; CARL diff 0%",
        fontsize=11.5,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    out = HERE / "ab_waste.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def main():
    data = load()
    if not data:
        raise SystemExit("no pareto_data_<model>.json found; run build_pareto_data.py")
    p1 = pareto_fig(data)
    p2 = waste_fig(data)
    print(f"wrote {p1}\nwrote {p2}")
    for model, arms in data.items():
        for arm in ("A", "B"):
            d = arms[arm]
            print(
                f"  {model:6s} arm {arm}: cost-to-winner=${d['cost_to_winner']:.2f} "
                f"total=${d['total']:.2f} fit={d['winner_fit']:.4f} "
                f"valid={d['validity_rate'] * 100:.1f}% $/valid=${d['cost_per_valid']:.3f}"
            )


if __name__ == "__main__":
    main()
