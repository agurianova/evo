"""
Arms-race plot for adversarial co-evolution experiments.

Reads frontier fitness and per-generation mean/std from Redis for paired
populations, produces a clean 1x2 figure showing both populations per pair.

Usage (standalone):
    PYTHONPATH=. python experiments/adversarial/optimizer-coevo/tools/plot_arms_race.py \
        --output-folder experiments/adversarial/optimizer-coevo/plots

Usage (from watchdog):
    from experiments.adversarial.optimizer_coevo.tools.plot_arms_race import generate_arms_race_plot
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

OPTIMIZER_COLOR = "#1565C0"  # Material Blue 800
LANDSCAPE_COLOR = "#C62828"  # Material Red 800
OPTIMIZER_FILL = "#42A5F5"  # Material Blue 400
LANDSCAPE_FILL = "#EF5350"  # Material Red 400
GRID_COLOR = "#E0E0E0"
BG_COLOR = "white"

PAIR_TITLES = ["Pair 1", "Pair 2"]


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
    role: str  # "optimizer" or "landscape"
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
    """Read a metrics history list from Redis, return parsed JSON entries."""
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
    """Aggregate per-gen mean/std entries.

    Multiple entries per generation are possible (one per valid program).
    We take the last entry per generation as the running aggregate.
    """
    if not mean_entries:
        return [], [], []

    # Group by generation, take last value per gen
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
    """Fetch all plot data for one population from Redis."""
    r = redis.Redis(host=host, port=port, db=db)

    gen = _get_generation(r, prefix)
    frontier = _read_metric_history(r, prefix, "valid_frontier_fitness")
    means = _read_metric_history(r, prefix, "valid_gen_fitness_mean")
    stds = _read_metric_history(r, prefix, "valid_gen_fitness_std")

    f_gens, f_vals = _frontier_to_step(frontier)
    m_gens, m_vals, s_vals = _gen_aggregates(means, stds)

    # Latest n_opponents
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
    role_label = "Optimizer" if pop.role == "optimizer" else "Landscape"

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

    # Frontier (step function) — the main line
    if pop.frontier_gens and pop.frontier_vals:
        fg = np.array(pop.frontier_gens)
        fv = np.array(pop.frontier_vals)

        # Extend to current generation for step display
        if pop.generation > 0 and len(fg) > 0 and fg[-1] < pop.generation:
            fg = np.append(fg, pop.generation)
            fv = np.append(fv, fv[-1])

        ax.step(
            fg,
            fv,
            where="post",
            color=color,
            linewidth=2.2,
            solid_capstyle="round",
            label=f"{role_label} best",
        )

        # Annotate current best
        if len(fv) > 0:
            best_val = fv[-1] if len(fv) > 0 else fv[0]
            best_gen = fg[-1]
            ax.annotate(
                f"{best_val:.1%}",
                xy=(best_gen, best_val),
                xytext=(6, 8 if pop.role == "optimizer" else -14),
                textcoords="offset points",
                fontsize=8.5,
                fontweight="bold",
                color=color,
                ha="left",
                va="bottom" if pop.role == "optimizer" else "top",
            )


def generate_arms_race_plot(
    pairs: list[PairSpec],
    output_dir: Path,
    hour: int | None = None,
    max_gen: int = 20,
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

        # Fetch data
        pop_a = fetch_population_data(host, port, **pair.pop_a)
        pop_b = fetch_population_data(host, port, **pair.pop_b)

        # Plot both populations
        _plot_population(ax, pop_a, OPTIMIZER_COLOR, OPTIMIZER_FILL)
        _plot_population(ax, pop_b, LANDSCAPE_COLOR, LANDSCAPE_FILL)

        # Axis formatting
        ax.set_title(pair.pair_label, fontsize=12, fontweight="medium", pad=8)
        ax.set_xlabel("Generation", fontsize=10)
        if i == 0:
            ax.set_ylabel("Frontier Fitness", fontsize=10)

        ax.set_xlim(0, max_gen)
        ax.set_ylim(-0.02, 1.02)
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=10))
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))

        # Gen progress annotation
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

    # Shared legend (outside axes, top center)
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

    # Suptitle
    title = "Adversarial Co-Evolution"
    if hour is not None:
        title += f"  (hour {hour})"
    fig.suptitle(title, fontsize=13, fontweight="medium", y=1.08)

    fig.tight_layout(rect=[0, 0, 1, 0.96])

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"arms_race_hour_{hour:03d}" if hour is not None else "arms_race"
    png_path = output_dir / f"{stem}.png"
    fig.savefig(png_path, dpi=300, bbox_inches="tight", facecolor="white")

    # Also save latest (overwritten each time)
    latest = output_dir / "arms_race_latest.png"
    fig.savefig(latest, dpi=300, bbox_inches="tight", facecolor="white")

    plt.close(fig)
    return png_path


# ── CLI ──────────────────────────────────────────────────────────────────────


def _default_pairs() -> list[PairSpec]:
    """Default pair specs for adversarial/optimizer-coevo experiment."""
    return [
        PairSpec(
            pair_label="Pair 1",
            pop_a={
                "label": "P1-A",
                "db": 1,
                "prefix": "adversarial/optimizer_v2/pop_a",
                "role": "optimizer",
            },
            pop_b={
                "label": "P1-B",
                "db": 2,
                "prefix": "adversarial/optimizer_v2/pop_b",
                "role": "landscape",
            },
        ),
        PairSpec(
            pair_label="Pair 2",
            pop_a={
                "label": "P2-A",
                "db": 3,
                "prefix": "adversarial/optimizer_v2/pop_a",
                "role": "optimizer",
            },
            pop_b={
                "label": "P2-B",
                "db": 4,
                "prefix": "adversarial/optimizer_v2/pop_b",
                "role": "landscape",
            },
        ),
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Arms-race plot for adversarial co-evolution"
    )
    parser.add_argument(
        "--output-folder",
        type=Path,
        default=Path("experiments/adversarial/optimizer-coevo/plots"),
    )
    parser.add_argument("--hour", type=int, default=None)
    parser.add_argument("--max-gen", type=int, default=20)
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
