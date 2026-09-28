"""Generate the illustrative figures for memory_write_system.tex.

Two schematic figures grounded in the write-path semantics of
config/memory/{writer,full}: the use-attributed base-relative gain events a
card earns (write/stats.py) and the greedy-online + periodic-consolidation bank
dynamic (write/consolidation.py). Both are illustrative, not measured runs. Run
with the repo python; writes memwrite_gain.pdf / memwrite_consolidation.pdf next
to the .tex.
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "8")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))

HELP = "#1b7837"  # helpful / positive gain
HARM = "#b2182b"  # harmful / negative gain
COLD = "#7f7f7f"  # invalid / forced-harm
BASE = "#2166ac"  # bank / baseline
INK = "#222222"

plt.rcParams.update(
    {
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "figure.dpi": 140,
    }
)


# -------------------------------------------- Fig 1: use-attributed gain events
def fig_gain():
    """One credited card's gain events over the children of one base parent.

    Each valid child contributes one signed, base-relative event (child minus
    base fitness in maximize orientation); the strict sign test counts the
    strictly-negative ones as harm; every invalid child contributes one
    forced-harm event pinned at gain 0 and tagged invalid.
    """
    rng = np.random.default_rng(11)
    base = 0.30
    valid = base + rng.normal(0.018, 0.055, 15)
    deltas = np.sort(valid - base)
    x = np.arange(1, len(deltas) + 1)

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    ax.axhspan(-0.2, 0.0, color=HARM, alpha=0.05)
    for xi, d in zip(x, deltas):
        c = HELP if d > 0 else HARM
        ax.plot([xi, xi], [0, d], color=c, lw=2.0, alpha=0.85, zorder=1)
        ax.scatter([xi], [d], color=c, s=26, zorder=2)

    x_inv = np.arange(len(deltas) + 1, len(deltas) + 4)
    ax.scatter(
        x_inv,
        np.zeros_like(x_inv, dtype=float),
        marker="x",
        color=COLD,
        s=55,
        lw=2.0,
        zorder=3,
    )

    ax.axhline(0.0, color=INK, lw=1.4)
    n_harm = int((deltas < 0).sum())
    ax.annotate(
        f"strict sign test:\n$k_{{\\mathrm{{harm}}}}={n_harm}$ of {len(deltas)}",
        xy=(2.0, deltas[0]),
        xytext=(2.2, -0.135),
        fontsize=8.5,
        color=HARM,
        arrowprops=dict(arrowstyle="->", color=HARM, lw=0.8),
    )
    ax.text(
        len(deltas) + 0.4,
        0.012,
        "invalid children:\nforced harm (gain $\\equiv 0$)",
        fontsize=8.0,
        color=COLD,
        va="bottom",
    )
    ax.text(
        0.6,
        0.006,
        "base-relative zero = base parent fitness",
        fontsize=8.0,
        color=INK,
        va="bottom",
    )
    ax.set_xlabel("children of one base parent (one gain event each)")
    ax.set_ylabel(r"gain $=\ f_{\mathrm{child}}-f_{\mathrm{base}}$")
    ax.set_xlim(0.3, len(deltas) + 4)
    ax.set_ylim(-0.16, 0.16)
    ax.set_xticks([])
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "memwrite_gain.pdf"))
    plt.close(fig)


# ------------------------------------ Fig 2: greedy online + periodic cleanup
def fig_consolidation():
    """Bank size under greedy online admission vs periodic consolidation.

    The online librarian is order-dependent: same-lever cards can both enter as
    NEW when neither pulls the other into the reconcile agent's top-k context.
    Every ``every_n`` writes a consolidation pass folds near-duplicates back down
    toward the true distinct-lever count; a pass over an already-deduped bank
    merges nothing (idempotent).
    """
    every_n = 32
    n = 260
    writes = np.arange(n + 1)
    # true distinct levers actually discovered: slow, saturating.
    true_levers = 9.0 * (1.0 - np.exp(-writes / 110.0))

    greedy = np.zeros(n + 1)
    consolidated = np.zeros(n + 1)
    g = c = 0.0
    dup_share = 0.42  # fraction of writes that duplicate an existing lever
    for w in range(1, n + 1):
        grew = true_levers[w] - true_levers[w - 1]
        # every write adds a card; only `1-dup_share` of them are novel levers.
        g += grew + dup_share
        c += grew + dup_share
        if w % every_n == 0:
            c = true_levers[w]  # consolidation folds accumulated near-dups
        greedy[w] = g
        consolidated[w] = c

    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    ax.plot(
        writes,
        greedy,
        color=HARM,
        lw=2.0,
        ls="--",
        label="greedy online only (duplicates accrete)",
    )
    ax.plot(
        writes,
        consolidated,
        color=BASE,
        lw=2.2,
        label="online + consolidation every $n{=}32$",
    )
    ax.plot(
        writes, true_levers, color=HELP, lw=2.2, ls=":", label="true distinct levers"
    )
    for boundary in range(every_n, n + 1, every_n):
        ax.axvline(boundary, color=INK, lw=0.6, ls=":", alpha=0.35)
    ax.set_xlabel("cards written across sweeps")
    ax.set_ylabel("cards in bank")
    ax.set_xlim(0, n)
    ax.set_ylim(0, greedy.max() * 1.05)
    ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "memwrite_consolidation.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    fig_gain()
    fig_consolidation()
    print("wrote memwrite_gain.pdf, memwrite_consolidation.pdf")
