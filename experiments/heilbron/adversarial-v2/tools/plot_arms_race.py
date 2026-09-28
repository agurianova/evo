"""
Arms-race plot for Heilbron adversarial co-evolution (Constructor vs Improver).

Shows Constructor and Improver fitness trajectories side-by-side per pair.
Unlike comparison.py (which lumps all runs on one axis), this reveals the
adversarial dynamics: when the Constructor improves, the Improver's job gets
harder, and vice versa.

Fitness semantics:
  - Constructor: quality of the point configuration (higher = better placement).
    Frontier is cummax (monotonically improves via MAP-Elites archive).
  - Improver: quality of the improvement found for a GIVEN constructor config.
    NOT cummax — each generation re-evaluates against the current opponent
    archive, so fitness can fluctuate as the Constructor evolves.

Usage (standalone):
    PYTHONPATH=. python experiments/heilbron/adversarial-v2/tools/plot_arms_race.py \
        --output-folder experiments/heilbron/adversarial-v2/plots

Usage (from watchdog):
    from experiments.heilbron.adversarial_v2.tools.plot_arms_race import generate_arms_race_plot
    path = generate_arms_race_plot(pairs, output_dir, hour=5)
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import numpy as np  # noqa: E402
import redis  # noqa: E402
import seaborn as sns  # noqa: E402

from gigaevo.evolution.engine.snapshot import (  # noqa: E402
    ENGINE_SNAPSHOT_KEY,
    EngineSnapshot,
)

# ── Style ────────────────────────────────────────────────────────────────────

CONSTRUCTOR_COLOR = "#1565C0"  # Material Blue 800
IMPROVER_COLOR = "#C62828"  # Material Red 800
CONSTRUCTOR_FILL = "#42A5F5"  # Material Blue 400
IMPROVER_FILL = "#EF5350"  # Material Red 400
GRID_COLOR = "#E0E0E0"
BG_COLOR = "white"


def _configure_style():
    """Publication-quality style matching tools/comparison.py."""
    plt.rcdefaults()
    sns.set_theme(style="ticks", context="paper")
    rc = {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.5,
        "grid.color": GRID_COLOR,
        "grid.linewidth": 0.6,
        "figure.facecolor": BG_COLOR,
        "axes.facecolor": BG_COLOR,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.08,
        "savefig.facecolor": BG_COLOR,
    }
    plt.rcParams.update(rc)


# ── Data model ───────────────────────────────────────────────────────────────


@dataclass
class PopulationData:
    label: str
    role: str  # "constructor" or "improver"
    db: int
    prefix: str
    generation: int
    frontier_gens: list[int]
    frontier_vals: list[float]
    mean_gens: list[int]
    mean_vals: list[float]
    std_vals: list[float]
    n_opponents_latest: float | None


@dataclass
class PairSpec:
    pair_label: str
    pop_a: dict  # {label, db, prefix, role}
    pop_b: dict  # {label, db, prefix, role}


# ── Redis reads ──────────────────────────────────────────────────────────────


def _read_metric_history(r: redis.Redis, prefix: str, metric_suffix: str) -> list[dict]:
    key = f"{prefix}:metrics:history:program_metrics:{metric_suffix}"
    raw_list = r.lrange(key, 0, -1)
    entries = []
    for raw in raw_list:
        try:
            entries.append(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            continue
    return entries


def _get_generation(r: redis.Redis, prefix: str) -> int:
    raw = r.hget(f"{prefix}:run_state", ENGINE_SNAPSHOT_KEY)
    if not raw:
        return 0
    try:
        return EngineSnapshot.model_validate_json(raw).total_generations
    except Exception:
        return 0


def _frontier_to_step(entries: list[dict]) -> tuple[list[int], list[float]]:
    """Convert frontier history entries to (gens, vals) step series.

    Frontier entries only appear on improvement, so we forward-fill to make
    a complete step function over all generations.
    """
    if not entries:
        return [], []
    gens = [e["s"] for e in entries if e.get("v") is not None]
    vals = [e["v"] for e in entries if e.get("v") is not None]
    return gens, vals


def _gen_aggregates(
    mean_entries: list[dict], std_entries: list[dict]
) -> tuple[list[int], list[float], list[float]]:
    """Per-gen mean/std: take the last entry per generation."""
    if not mean_entries:
        return [], [], []

    gen_means: dict[int, float] = {}
    for e in mean_entries:
        if e.get("v") is not None:
            gen_means[e["s"]] = e["v"]

    gen_stds: dict[int, float] = {}
    for e in std_entries:
        if e.get("v") is not None:
            gen_stds[e["s"]] = e["v"]

    gens = sorted(gen_means.keys())
    means = [gen_means[g] for g in gens]
    stds = [gen_stds.get(g, 0.0) for g in gens]
    return gens, means, stds


def fetch_population_data(
    host: str, port: int, db: int, prefix: str, label: str, role: str
) -> PopulationData:
    r = redis.Redis(host=host, port=port, db=db)

    gen = _get_generation(r, prefix)
    frontier = _read_metric_history(r, prefix, "valid_frontier_fitness")
    means = _read_metric_history(r, prefix, "valid_gen_fitness_mean")
    stds = _read_metric_history(r, prefix, "valid_gen_fitness_std")

    f_gens, f_vals = _frontier_to_step(frontier)
    m_gens, m_vals, s_vals = _gen_aggregates(means, stds)

    n_opp = None
    n_opp_entries = _read_metric_history(r, prefix, "valid_frontier_n_opponents")
    if n_opp_entries:
        last = n_opp_entries[-1]
        if last.get("v") is not None:
            n_opp = last["v"]

    return PopulationData(
        label=label,
        role=role,
        db=db,
        prefix=prefix,
        generation=gen,
        frontier_gens=f_gens,
        frontier_vals=f_vals,
        mean_gens=m_gens,
        mean_vals=m_vals,
        std_vals=s_vals,
        n_opponents_latest=n_opp,
    )


# ── Plotting ─────────────────────────────────────────────────────────────────


def _plot_population(ax: plt.Axes, pop: PopulationData, color: str, fill: str):
    """Plot one population's fitness trajectory on an axis."""
    role_label = "Constructor" if pop.role == "constructor" else "Improver"

    # Mean + std band
    if pop.mean_gens and pop.mean_vals:
        mg = np.array(pop.mean_gens)
        mv = np.array(pop.mean_vals)
        sv = np.array(pop.std_vals)
        ax.fill_between(
            mg,
            np.clip(mv - sv, 0, 1),
            np.clip(mv + sv, 0, 1),
            alpha=0.12,
            color=fill,
            linewidth=0,
        )
        ax.plot(
            mg,
            mv,
            color=color,
            linewidth=1.2,
            alpha=0.45,
            linestyle=":",
            label=f"{role_label} mean",
        )

    # Frontier — the main line
    if pop.frontier_gens and pop.frontier_vals:
        fg = np.array(pop.frontier_gens)
        fv = np.array(pop.frontier_vals)

        # Extend to current generation for step display
        if pop.generation > 0 and len(fg) > 0 and fg[-1] < pop.generation:
            fg = np.append(fg, pop.generation)
            fv = np.append(fv, fv[-1])

        # Constructor uses step (cummax by nature of MAP-Elites archive).
        # Improver uses line — its fitness can fluctuate as the opponent evolves.
        if pop.role == "constructor":
            ax.step(
                fg,
                fv,
                where="post",
                color=color,
                linewidth=2.2,
                solid_capstyle="round",
                label=f"{role_label} best",
            )
        else:
            ax.plot(
                fg,
                fv,
                color=color,
                linewidth=2.2,
                solid_capstyle="round",
                label=f"{role_label} best",
                marker="o",
                markersize=3,
            )

        # Annotate current best
        if len(fv) > 0:
            best_val = fv[-1]
            best_gen = fg[-1]
            ax.annotate(
                f"{best_val:.1%}",
                xy=(best_gen, best_val),
                xytext=(6, 8 if pop.role == "constructor" else -14),
                textcoords="offset points",
                fontsize=8.5,
                fontweight="bold",
                color=color,
                ha="left",
                va="bottom" if pop.role == "constructor" else "top",
            )


def generate_arms_race_plot(
    pairs: list[PairSpec],
    output_dir: Path,
    hour: int | None = None,
    max_gen: int = 75,
    host: str = "localhost",
    port: int = 6379,
) -> Path | None:
    """Generate the arms-race plot and return the PNG path, or None on failure."""
    _configure_style()

    n_pairs = len(pairs)
    fig, axes = plt.subplots(
        1,
        n_pairs,
        figsize=(5.5 * n_pairs, 4.0),
        sharey=True,
        squeeze=False,
    )

    for i, pair in enumerate(pairs):
        ax = axes[0, i]

        pop_a = fetch_population_data(host, port, **pair.pop_a)
        pop_b = fetch_population_data(host, port, **pair.pop_b)

        _plot_population(ax, pop_a, CONSTRUCTOR_COLOR, CONSTRUCTOR_FILL)
        _plot_population(ax, pop_b, IMPROVER_COLOR, IMPROVER_FILL)

        ax.set_title(pair.pair_label, fontsize=12, fontweight="medium", pad=8)
        ax.set_xlabel("Generation", fontsize=10)
        if i == 0:
            ax.set_ylabel("Frontier Fitness", fontsize=10)

        ax.set_xlim(0, max_gen)
        ax.set_ylim(-0.02, 1.02)
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=10))
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))

        gen_a = pop_a.generation
        gen_b = pop_b.generation
        ax.text(
            0.98,
            0.02,
            f"gen {min(gen_a, gen_b)}/{max_gen}",
            transform=ax.transAxes,
            fontsize=8,
            color="#757575",
            ha="right",
            va="bottom",
        )

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        ncol=4,
        fontsize=9,
        frameon=True,
        fancybox=False,
        edgecolor="#BDBDBD",
        borderpad=0.4,
        columnspacing=1.5,
        bbox_to_anchor=(0.5, 1.02),
    )

    title = "Heilbron Constructor vs Improver"
    if hour is not None:
        title += f"  (hour {hour})"
    fig.suptitle(title, fontsize=13, fontweight="medium", y=1.08)

    fig.tight_layout(rect=[0, 0, 1, 0.96])

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"arms_race_hour_{hour:03d}" if hour is not None else "arms_race"
    png_path = output_dir / f"{stem}.png"
    fig.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="white")

    latest = output_dir / "arms_race_latest.png"
    fig.savefig(latest, dpi=300, bbox_inches="tight", facecolor="white")

    plt.close(fig)
    return png_path


# ── CLI ──────────────────────────────────────────────────────────────────────


def _default_pairs() -> list[PairSpec]:
    """Pair specs for heilbron/adversarial-v2."""
    return [
        PairSpec(
            pair_label="Pair 1 (K=3)",
            pop_a={
                "label": "P1_A",
                "db": 1,
                "prefix": "heilbron_adversarial/pop_a",
                "role": "constructor",
            },
            pop_b={
                "label": "P1_B",
                "db": 2,
                "prefix": "heilbron_adversarial/pop_b",
                "role": "improver",
            },
        ),
        PairSpec(
            pair_label="Pair 2 (K=1)",
            pop_a={
                "label": "P2_A",
                "db": 3,
                "prefix": "heilbron_adversarial/pop_a",
                "role": "constructor",
            },
            pop_b={
                "label": "P2_B",
                "db": 4,
                "prefix": "heilbron_adversarial/pop_b",
                "role": "improver",
            },
        ),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Arms-race plot for Heilbron adversarial co-evolution"
    )
    parser.add_argument(
        "--output-folder",
        type=Path,
        default=Path("experiments/heilbron/adversarial-v2/plots"),
    )
    parser.add_argument("--hour", type=int, default=None)
    parser.add_argument("--max-gen", type=int, default=75)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=6379)
    args = parser.parse_args()

    pairs = _default_pairs()
    path = generate_arms_race_plot(
        pairs,
        args.output_folder,
        hour=args.hour,
        max_gen=args.max_gen,
        host=args.host,
        port=args.port,
    )
    if path:
        print(f"Plot saved: {path}")
    else:
        print("Plot generation failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
