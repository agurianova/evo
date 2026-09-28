#!/usr/bin/env python3
"""Refresh frontier fitness PNGs and an auto-updating HTML dashboard."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from gigaevo.monitoring.live_frontier_compare import _render_frontier_plot  # noqa: E402

OUTPUTS = REPO / "outputs"
DASHBOARD_DIR = OUTPUTS / "_dashboard_luna_m200"
METRIC = "fitness"


def _read_series(path: Path) -> list[tuple[int, float]]:
    if not path.exists():
        return []
    out: list[tuple[int, float]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        step, value = row.get("s"), row.get("v")
        if step is None or value is None:
            continue
        out.append((int(step), float(value)))
    return out


def _metric_path(run_dir: Path, suffix: str) -> Path:
    return run_dir / "metrics" / f"program_metrics:valid_{suffix}.jsonl"


def _run_dirs(pattern: str) -> list[Path]:
    return sorted(OUTPUTS.glob(pattern), key=lambda p: p.name)


def _count_programs(run_dir: Path) -> int:
    prog_dir = run_dir / "storage" / "pmhctcr" / "programs"
    return len(list(prog_dir.glob("*.json"))) if prog_dir.exists() else 0


def _last_scalar(path: Path) -> float | None:
    series = _read_series(path)
    return series[-1][1] if series else None


def refresh_run(run_dir: Path) -> dict:
    frontier = _read_series(_metric_path(run_dir, f"frontier_{METRIC}"))
    iter_mean = _read_series(_metric_path(run_dir, f"iter_{METRIC}_mean"))
    plot_path = None
    if frontier:
        plot_path = _render_frontier_plot(
            output_dir=run_dir,
            metric=METRIC,
            frontier_history=frontier,
            iter_mean_history=iter_mean,
            higher_is_better=True,
        )
    best = max(v for _, v in frontier) if frontier else None
    last_iter = frontier[-1][0] if frontier else None
    mutants = _last_scalar(run_dir / "metrics" / "evolution_engine:iteration.jsonl")
    return {
        "name": run_dir.name,
        "programs": _count_programs(run_dir),
        "mutants": mutants,
        "best_fitness": best,
        "last_iter": last_iter,
        "plot": plot_path,
        "has_data": bool(frontier),
    }


def _render_combined(rows: list[dict], out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 7))
    plotted = 0
    for row in rows:
        run_dir = OUTPUTS / row["name"]
        frontier = _read_series(_metric_path(run_dir, f"frontier_{METRIC}"))
        if not frontier:
            continue
        frontier = sorted(frontier, key=lambda x: x[0])
        xs = [s for s, _ in frontier]
        ys: list[float] = []
        best = float("-inf")
        for _, v in frontier:
            best = max(best, v)
            ys.append(best)
        label = row["name"].replace("pmhctcr_python_patch_luna_m200_", "")
        ax.plot(xs, ys, linewidth=2.0, label=label)
        plotted += 1
    if plotted:
        ax.set_xlabel("Iteration")
        ax.set_ylabel("Fitness (best-so-far)")
        ax.set_title("Luna m200 — frontier fitness across runs")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")
    else:
        ax.text(0.5, 0.5, "No frontier data yet", ha="center", va="center")
        ax.set_axis_off()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _render_html(rows: list[dict], html_path: Path, combined_plot: Path) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    cards = []
    for row in rows:
        plot_file = OUTPUTS / row["name"] / f"frontier_{METRIC}.png"
        plot_rel = Path("..") / row["name"] / f"frontier_{METRIC}.png" if plot_file.exists() else None
        img = (
            f'<img src="{plot_rel}" alt="{row["name"]}" style="max-width:100%;border:1px solid #ddd;" />'
            if plot_rel is not None
            else "<p><em>No fitness data yet</em></p>"
        )
        best = (
            f"{row['best_fitness']:.5f}"
            if row["best_fitness"] is not None
            else "—"
        )
        mutants = (
            f"{int(row['mutants'])}"
            if row["mutants"] is not None
            else "—"
        )
        cards.append(
            f"""
            <section style="margin: 1.5rem 0; padding: 1rem; border: 1px solid #ccc; border-radius: 8px;">
              <h2>{row['name']}</h2>
              <p>programs={row['programs']} | mutants={mutants} | best fitness={best} | last iter={row['last_iter'] or '—'}</p>
              {img}
            </section>
            """
        )
    combined_rel = combined_plot.relative_to(DASHBOARD_DIR)
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta http-equiv="refresh" content="60" />
  <title>Luna m200 fitness dashboard</title>
  <style>
    body {{ font-family: sans-serif; max-width: 1200px; margin: 0 auto; padding: 1rem; }}
    h1 {{ margin-bottom: 0.2rem; }}
    .meta {{ color: #555; margin-bottom: 1rem; }}
  </style>
</head>
<body>
  <h1>Luna m200 — fitness dashboard</h1>
  <p class="meta">Auto-refresh every 60s. Last update: {now}</p>
  <section style="margin: 1.5rem 0; padding: 1rem; border: 1px solid #ccc; border-radius: 8px;">
    <h2>Combined frontier</h2>
    <img src="{combined_rel}" alt="combined frontier" style="max-width:100%;border:1px solid #ddd;" />
  </section>
  {''.join(cards)}
</body>
</html>
"""
    html_path.write_text(html)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pattern",
        default="pmhctcr_python_patch_luna_m200_v*",
        help="Glob under outputs/ for run directories",
    )
    args = parser.parse_args()

    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    rows = [refresh_run(run_dir) for run_dir in _run_dirs(args.pattern)]
    combined_plot = DASHBOARD_DIR / "combined_frontier_fitness.png"
    _render_combined(rows, combined_plot)
    html_path = DASHBOARD_DIR / "index.html"
    _render_html(rows, html_path, combined_plot)
    print(f"updated {html_path}")
    for row in rows:
        status = "ok" if row["has_data"] else "no data"
        best = row["best_fitness"]
        print(
            f"  {row['name']}: programs={row['programs']} mutants={row['mutants']} "
            f"best={best if best is not None else '—'} [{status}]"
        )


if __name__ == "__main__":
    main()
