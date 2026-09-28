"""Static-lever closeout figures: cumulative-best trajectories + fair-end bars.

Reads the four disk-run full CSVs (exported via `gigaevo export csv`) and renders:
  fig_trajectory.png  — cumulative-best vs program count, 4 runs + arm-mean bands,
                        with no-mem (A) and dynamic (D) reference lines.
  fig_fairend.png     — fair-end (program 245) arm means vs A/D bars.
Run:  python make_figures.py <dir-with-{C6-1,C6-2,TL-1,TL-2}_full.csv> <out-dir>
"""

from __future__ import annotations

import csv
import math
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = sys.argv[1] if len(sys.argv) > 1 else "."
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
RUNS = ["C6-1", "C6-2", "TL-1", "TL-2"]
ARM = {"C6-1": "B", "C6-2": "B", "TL-1": "C", "TL-2": "C"}
COLOR = {"C6-1": "#1a6", "C6-2": "#5c9", "TL-1": "#c33", "TL-2": "#e77"}
A_BAR, A_SD = 0.0294, 0.0018
D_BAR = 0.0289
SENTINEL = {-1.0, -999.0, 0.0}


def cum_traj(run: str):
    rows = list(csv.DictReader(open(f"{SRC}/{run}_full.csv")))
    rows.sort(key=lambda r: int(r["atomic_counter"]))
    xs, ys, best = [], [], None
    for i, r in enumerate(rows, start=1):
        f, v = r["metric_fitness"], r["metric_is_valid"]
        if f not in ("", "None") and v in ("1", "1.0", "True", "true"):
            fv = float(f)
            if math.isfinite(fv) and fv not in SENTINEL and (best is None or fv > best):
                best = fv
        if best is not None:
            xs.append(i)
            ys.append(best)
    return xs, ys


def at(xs, ys, k):
    v = None
    for x, y in zip(xs, ys):
        if x <= k:
            v = y
    return v


traj = {r: cum_traj(r) for r in RUNS}

# --- Fig 1: trajectories ---
fig, ax = plt.subplots(figsize=(8.5, 5.2))
for r in RUNS:
    xs, ys = traj[r]
    ax.plot(xs, ys, color=COLOR[r], lw=1.8, label=f"{r} ({ARM[r]})", alpha=0.9)
ax.axhline(A_BAR, color="#333", ls="--", lw=1.3, label="A no-mem bar (0.0294)")
ax.axhspan(A_BAR - A_SD, A_BAR + A_SD, color="#333", alpha=0.08)
ax.axhline(D_BAR, color="#749", ls=":", lw=1.3, label="D dynamic bar (0.0289)")
ax.axvline(245, color="#999", ls="-", lw=0.8, alpha=0.6)
ax.text(
    247, 0.005, "fair-end k=245", color="#666", fontsize=8, rotation=90, va="bottom"
)
ax.set_xlabel("programs created (cumulative)")
ax.set_ylabel("cumulative-best fitness  (higher = better)")
ax.set_title("Static-lever blast — core-6 (B) vs tail (C), heilbron")
ax.legend(fontsize=8, loc="lower right", ncol=2)
ax.grid(alpha=0.25)
fig.tight_layout()
fig.savefig(f"{OUT}/fig_trajectory.png", dpi=140)

# --- Fig 2: fair-end bars at k=245 ---
b = [at(*traj["C6-1"], 245), at(*traj["C6-2"], 245)]
c = [at(*traj["TL-1"], 245), at(*traj["TL-2"], 245)]
bm = sum(b) / 2
cm = sum(c) / 2
fig2, ax2 = plt.subplots(figsize=(6.4, 5.0))
labels = ["B core-6", "C tail", "A no-mem", "D dynamic"]
means = [bm, cm, A_BAR, D_BAR]
errs = [
    (max(b) - min(b)) / 2,
    (max(c) - min(c)) / 2,
    A_SD,
    0.0015,
]
colors = ["#1a6", "#c33", "#333", "#749"]
bars = ax2.bar(labels, means, yerr=errs, capsize=5, color=colors, alpha=0.85)
ax2.axhline(A_BAR, color="#333", ls="--", lw=1.0, alpha=0.6)
for rect, m in zip(bars, means):
    ax2.text(
        rect.get_x() + rect.get_width() / 2,
        m + 0.0006,
        f"{m:.4f}",
        ha="center",
        fontsize=9,
    )
ax2.set_ylabel("cumulative-best fitness @ program 245")
ax2.set_title("Fair-end (k=245): core-6 beats no-mem & dynamic; tail hurts")
ax2.set_ylim(0, 0.037)
ax2.grid(axis="y", alpha=0.25)
fig2.tight_layout()
fig2.savefig(f"{OUT}/fig_fairend.png", dpi=140)
print(f"wrote {OUT}/fig_trajectory.png and {OUT}/fig_fairend.png")
print(f"B mean@245={bm:.5f} C mean@245={cm:.5f}")
