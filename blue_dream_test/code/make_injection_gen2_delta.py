#!/usr/bin/env python3
"""Test deltas for generation-2 injection hosts, in the tree palette.

H1 is the soft blue and A is the pale cyan: filled circles with a black
outline, both on the same row height. A very thin gray dash joins them.
A missing A score is a cross on that row.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Circle

OUT = Path(__file__).resolve().parent / "injection_gen2_delta.png"

SURFACE = "#6eacd8"
KQV = "#b7e8f2"
EDGE = "#1a1a1a"
DOT = 5.6
PLUS_HAZE = "#cfe8c6"
MINUS_HAZE = "#f4cfcf"
INK = "#1a1a1a"
MUTED = "#6a6a6a"
GAIN = "#3d6b4a"
LINK = "#a0a0a0"
GRID = "#ededed"
SPINE = "#d5d5d5"

# (label, H1, A). None means that arm produced no metric.
ROWS = [
    ("r2  275ae460", -0.006371568, -0.011508235),
    ("r4  4996f5b6", +0.006119055, -0.002633135),
    ("r4  52c245fc", +0.001827347, None),
    ("r4  8777238d", +0.005749080, -0.001458553),
    ("r4  c840f89c", +0.020900779, -0.034122898),
    ("r5  c8991aef", +0.000195249, -0.001555842),
    ("r5  773338c2", +0.005174173, -0.006542821),
]


def wash(ax, x0: float, x1: float, y0: float, y1: float, color: str, peak: str) -> None:
    """Soft cloud. `peak` is the side that stays coloured; the other side dissolves."""
    rgb = to_rgb(color)
    width, height = 360, 32
    # u = 0 on the zero line, u = 1 at the outer edge of the cloud.
    u = np.linspace(0.0, 1.0, width)
    if peak == "right":
        u = u[::-1]
    alpha = (1.0 - u) ** 0.55 * 0.62
    image = np.zeros((height, width, 4))
    image[..., 0] = rgb[0]
    image[..., 1] = rgb[1]
    image[..., 2] = rgb[2]
    image[..., 3] = alpha[None, :]
    ax.imshow(
        image,
        extent=(x0, x1, y0, y1),
        origin="lower",
        interpolation="bilinear",
        aspect="auto",
        zorder=0,
    )


def add_tick(ax, x: float, y: float, face: str) -> None:
    from matplotlib.transforms import ScaledTranslation

    trans = ax.figure.dpi_scale_trans + ScaledTranslation(x, y, ax.transData)
    ax.add_patch(Circle(
        (0, 0), (DOT / 2) / 72.0, facecolor=face, edgecolor=EDGE, linewidth=0.55,
        transform=trans, zorder=4,
    ))


def add_link(ax, left: float, right: float, y: float) -> None:
    lo, hi = (left, right) if left <= right else (right, left)
    ax.plot(
        [lo, hi], [y, y], color=LINK, lw=0.35, linestyle=(0, (0.8, 0.9)),
        solid_capstyle="butt", zorder=2,
    )


def main() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 6.5,
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    # Quarter the previous area: each side is half of 8.6 x 5.25.
    fig = plt.figure(figsize=(4.3, 2.62), dpi=220, facecolor="white")
    ax = fig.add_axes([0.24, 0.20, 0.73, 0.66])
    ax.set_facecolor("white")

    n = len(ROWS)
    ys = list(range(n - 1, -1, -1))
    xmin, xmax = -0.044, 0.040
    ymin, ymax = -0.55, n - 0.35
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    wash(ax, xmin, 0.0, ymin, ymax, MINUS_HAZE, peak="right")
    wash(ax, 0.0, xmax, ymin, ymax, PLUS_HAZE, peak="left")
    ax.axvline(0, color=INK, lw=0.6, zorder=3)

    for y, (_label, surface, alone) in zip(ys, ROWS):
        if alone is not None:
            add_link(ax, surface, alone, y)
            add_tick(ax, alone, y, KQV)
        else:
            ax.plot(
                [0.985], [y], marker="x", color=EDGE, ms=4.2, mew=0.8,
                transform=ax.get_yaxis_transform(), clip_on=False, zorder=5,
            )
        add_tick(ax, surface, y, SURFACE)
    ax.text(
        xmax - 0.001, n - 0.55, "выше голой",
        ha="right", va="top", color=GAIN, fontsize=5.5, zorder=5,
    )

    ax.set_yticks(ys)
    ax.set_yticklabels(
        [row[0] for row in ROWS], fontfamily="DejaVu Sans Mono", fontsize=5.4, color=INK,
    )
    ax.set_xlabel(
        "Δ macro AUC-PR на тесте относительно голой программы",
        color=INK, fontsize=6, labelpad=2,
    )
    ax.set_xticks([-0.04, -0.02, 0, 0.02, 0.04])
    ax.tick_params(axis="x", colors=INK, length=2.2, width=0.5, labelsize=5.4, pad=1)
    ax.tick_params(axis="y", length=0, pad=2)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(SPINE)
    ax.spines["bottom"].set_color(SPINE)
    ax.xaxis.grid(True, color=GRID, lw=0.5, zorder=0)
    ax.set_axisbelow(False)

    h1 = Line2D(
        [0], [0], marker="o", color="none", markerfacecolor=SURFACE,
        markeredgecolor=EDGE, markeredgewidth=0.55, markersize=DOT, label="H1",
    )
    alone = Line2D(
        [0], [0], marker="o", color="none", markerfacecolor=KQV,
        markeredgecolor=EDGE, markeredgewidth=0.55, markersize=DOT, label="A",
    )
    leg = fig.legend(
        handles=[h1, alone], frameon=False, loc="lower left",
        bbox_to_anchor=(0.62, 0.90), ncol=2, fontsize=6,
        handletextpad=0.25, columnspacing=0.7, borderaxespad=0,
    )
    for text in leg.get_texts():
        text.set_color(INK)

    fig.text(
        0.24, 0.955, "Инъекции в первые различающиеся программы",
        color=INK, fontsize=7.5, ha="left", va="center",
    )
    fig.text(
        0.24, 0.045,
        "Медиана Δ: H1 +0.0052 (6 из 7), A −0.0046 (0 из 6).  r4 52c245fc: A без метрики.",
        color=MUTED, fontsize=4.8, ha="left", va="center",
    )

    fig.savefig(OUT, dpi=220, facecolor="white")
    fig.savefig(OUT.with_suffix(".svg"), facecolor="white")
    plt.close(fig)
    print(OUT)


if __name__ == "__main__":
    main()
