"""Arm-level figures for the dag_tab PR #306 shakedown: search trajectory,
genome quality/topology, and LLM cost. Reads viz/<arm>_stats.json.

Usage: python make_figures.py <arm-slug>[:<label>] ...
"""

import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).parent
VIZ = HERE / "viz"

COLORS = ["#1F4E79", "#C9720B", "#1A7F37"]
REFERENCE_CV = 0.864554  # 2026-07-16 run3_2d, same recipe on the pre-review code
GRID = dict(alpha=0.25, linewidth=0.7)

# OpenRouter list prices, USD per 1M tokens (2026-07-21).
PRICES = {
    "google/gemini-3-flash-preview": (0.50, 3.00),
    "google/gemini-3.5-flash": (1.50, 9.00),
}


def load(arm):
    return json.loads((VIZ / f"{arm}_stats.json").read_text())


def best_so_far(programs):
    best, out = None, []
    for p in programs:
        if p["is_valid"] == 1.0 and (best is None or p["fitness"] > best):
            best = p["fitness"]
        out.append(best)
    return out


def make_trajectory(arms, labels):
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.6))
    for (stats, label), color in zip(zip(arms, labels), COLORS):
        programs = stats["programs"]
        curve = best_so_far(programs)
        idx = [p["index"] for p in programs]
        mins = [p["elapsed_s"] / 60.0 for p in programs]
        axes[0].step(idx, curve, where="post", color=color, lw=2.0, label=label)
        axes[1].step(mins, curve, where="post", color=color, lw=2.0, label=label)
        valid = [p for p in programs if p["is_valid"] == 1.0]
        axes[0].scatter(
            [p["index"] for p in valid],
            [p["fitness"] for p in valid],
            s=11,
            color=color,
            alpha=0.35,
            linewidths=0,
        )

    seed = min(
        p["fitness"]
        for stats in arms
        for p in stats["programs"][:1]
        if p["is_valid"] == 1.0
    )
    floor = min(
        p["fitness"]
        for stats in arms
        for p in stats["programs"]
        if p["is_valid"] == 1.0
    )
    for ax, xlabel in (
        (axes[0], "programs evaluated (creation order)"),
        (axes[1], "wall-clock minutes"),
    ):
        ax.axhline(seed, color="#5A6472", ls=":", lw=1.4, label=f"seed {seed:.4f}")
        ax.axhline(
            REFERENCE_CV,
            color="#B42318",
            ls="--",
            lw=1.4,
            label=f"2026-07-16 reference {REFERENCE_CV:.4f}",
        )
        ax.set_xlabel(xlabel)
        ax.set_ylabel("best-so-far CV R²")
        ax.grid(**GRID)
        ax.set_ylim(floor - 0.002, REFERENCE_CV + 0.004)
    axes[0].legend(fontsize=8.5, loc="lower right", framealpha=0.9)
    fig.suptitle(
        "dag_tab on california — best-so-far cross-validated R²\n"
        "dots are individual valid genomes; the step line is the incumbent",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    out = HERE / "ab_trajectory.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


def make_quality(arms, labels):
    fig, axes = plt.subplots(1, 4, figsize=(14.6, 4.2))
    n = len(arms)
    width = 0.8 / n

    for k, (stats, label, color) in enumerate(zip(arms, labels, COLORS)):
        programs = stats["programs"]
        valid = [p for p in programs if p["is_valid"] == 1.0]
        invalid = [p for p in programs if p["is_valid"] != 1.0]
        x = np.arange(2) + (k - (n - 1) / 2) * width
        axes[0].bar(
            x, [len(valid), len(invalid)], width=width, color=color, label=label
        )
        for xi, v in zip(x, [len(valid), len(invalid)]):
            axes[0].text(xi, v + 0.6, str(v), ha="center", fontsize=8.5)

        axes[1].hist(
            [p["fitness"] for p in valid],
            bins=18,
            color=color,
            alpha=0.55,
            label=label,
        )
        for ax, key in ((axes[2], "node_count"), (axes[3], "max_depth")):
            vals = [p[key] for p in valid]
            centres = np.arange(min(vals), max(vals) + 1)
            counts = [sum(1 for v in vals if v == c) for c in centres]
            ax.bar(
                centres + (k - (n - 1) / 2) * width, counts, width=width, color=color
            )

    axes[0].set_xticks(np.arange(2))
    axes[0].set_xticklabels(["valid", "invalid"])
    axes[0].set_ylabel("programs")
    axes[0].set_title("genome validity", fontsize=11, fontweight="bold")
    axes[0].legend(fontsize=8.5, loc="upper right")
    axes[1].set_xlabel("CV R²")
    axes[1].set_ylabel("valid genomes")
    axes[1].set_title("fitness distribution", fontsize=11, fontweight="bold")
    axes[1].legend(fontsize=8.5, loc="upper left")
    axes[2].set_xlabel("nodes in graph")
    axes[2].set_title("graph size (valid genomes)", fontsize=11, fontweight="bold")
    axes[3].set_xlabel("consumed depth")
    axes[3].set_title("graph depth (valid genomes)", fontsize=11, fontweight="bold")
    for ax in axes:
        ax.grid(axis="y", **GRID)
    fig.suptitle(
        "genome quality and topology — the MAP-Elites behaviour axes the two arms actually filled",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    out = HERE / "ab_quality.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


def cost_usd(calls):
    total = 0.0
    for c in calls:
        pin, pout = PRICES.get(c["model"], (0.0, 0.0))
        total += (c["tokens_in"] or 0) * pin / 1e6 + (c["tokens_out"] or 0) * pout / 1e6
    return total


def make_cost(arms, labels):
    fig, axes = plt.subplots(1, 4, figsize=(14.6, 4.2))
    n = len(arms)
    width = 0.8 / n

    for k, (stats, label, color) in enumerate(zip(arms, labels, COLORS)):
        ok = [c for c in stats["llm_calls"] if c["ok"]]
        off = (k - (n - 1) / 2) * width
        means = [
            np.mean([c["tokens_in"] for c in ok]),
            np.mean([c["tokens_out"] for c in ok]),
            np.mean([c["tokens_reasoning"] for c in ok]),
        ]
        axes[0].bar(np.arange(3) + off, means, width=width, color=color, label=label)
        for xi, v in zip(np.arange(3) + off, means):
            axes[0].text(xi, v * 1.02, f"{v:,.0f}", ha="center", fontsize=8)

        axes[1].hist(
            [c["latency_ms"] / 1000.0 for c in ok],
            bins=22,
            color=color,
            alpha=0.55,
            label=label,
        )
        axes[2].bar(
            [k],
            [cost_usd(ok)],
            width=0.55,
            color=color,
        )
        axes[2].text(
            k, cost_usd(ok) * 1.02, f"${cost_usd(ok):.2f}", ha="center", fontsize=9
        )
        wall = max(p["elapsed_s"] for p in stats["programs"]) / 60.0
        axes[3].bar([k], [wall], width=0.55, color=color)
        axes[3].text(k, wall * 1.02, f"{wall:.0f} min", ha="center", fontsize=9)

    axes[0].set_xticks(np.arange(3))
    axes[0].set_xticklabels(["input", "output", "reasoning"])
    axes[0].set_ylabel("mean tokens per successful call")
    axes[0].set_title("token budget per call", fontsize=11, fontweight="bold")
    axes[0].legend(fontsize=8.5, loc="upper right")
    axes[1].set_xlabel("call latency (s)")
    axes[1].set_ylabel("calls")
    axes[1].set_title("mutation-call latency", fontsize=11, fontweight="bold")
    axes[1].legend(fontsize=8.5, loc="upper left")
    for ax, title, ylab in (
        (axes[2], "LLM spend (list price)", "USD"),
        (axes[3], "wall-clock to last program", "minutes"),
    ):
        ax.set_xticks(range(n))
        ax.set_xticklabels([lb.split(" (")[0] for lb in labels], fontsize=8.5)
        ax.set_ylabel(ylab)
        ax.set_title(title, fontsize=11, fontweight="bold")
    for ax in axes:
        ax.grid(axis="y", **GRID)
    fig.suptitle(
        "what each arm cost — thinking budget, latency under service_tier flex, and list-price spend",
        fontsize=12,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    out = HERE / "ab_cost.png"
    fig.savefig(out, dpi=200, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    specs = [a.split(":", 1) for a in sys.argv[1:]]
    arms = [load(s[0]) for s in specs]
    labels = [s[1] if len(s) > 1 else s[0] for s in specs]
    make_trajectory(arms, labels)
    make_quality(arms, labels)
    make_cost(arms, labels)
