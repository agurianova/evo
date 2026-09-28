"""Generate the statistical figures for memory_reputation_auction.tex.

Beta posteriors, auction win probabilities, and EV-bid distributions --- all
grounded in the defaults from config/memory/{reputation,auction}. Run with the
repo python; writes memrep_beta.pdf / memrep_winprob.pdf / memrep_bid.pdf next
to the .tex.
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "8")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import integrate
from scipy.stats import beta

HERE = os.path.dirname(os.path.abspath(__file__))

HELP = "#1b7837"  # helpful / positive
HARM = "#b2182b"  # harmful / negative
COLD = "#7f7f7f"  # cold / exploration
BASE = "#2166ac"  # baseline arm
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


def p_win(a, b, a0=3, b0=3):
    """P(theta > theta0), theta~Beta(a,b), theta0~Beta(a0,b0)."""
    val, _ = integrate.quad(
        lambda x: beta.pdf(x, a, b) * beta.cdf(x, a0, b0), 0, 1, limit=200
    )
    return val


# ---------------------------------------------------------------- Fig 1: Beta
def fig_beta():
    x = np.linspace(0, 1, 400)
    fig, ax = plt.subplots(figsize=(6.4, 3.5))
    curves = [
        (5, 2, HELP, "helpful  Beta(5,2)", "-"),
        (2, 4, HARM, "weak/harmful  Beta(2,4)", "-"),
        (1, 1, COLD, "cold  Beta(1,1)", "-"),
    ]
    for a, b, c, lab, ls in curves:
        ax.plot(x, beta.pdf(x, a, b), color=c, lw=2.2, ls=ls, label=lab)
    ax.plot(
        x,
        beta.pdf(x, 3, 3),
        color=BASE,
        lw=2.4,
        ls="--",
        label="baseline arm  Beta(3,3)",
    )
    # efficacy_confident: lo20 of Beta(5,2) vs tau=0.5
    lo = beta.ppf(0.20, 5, 2)
    ax.axvline(0.5, color=INK, lw=1.0, ls=":", alpha=0.8)
    ax.annotate(
        r"$\tau_c=0.5$",
        xy=(0.5, 2.55),
        xytext=(0.30, 2.75),
        fontsize=9,
        color=INK,
        arrowprops=dict(arrowstyle="->", color=INK, lw=0.8),
    )
    # shade the pessimistic 20% tail of the helpful posterior
    xt = np.linspace(0, lo, 120)
    ax.fill_between(xt, 0, beta.pdf(xt, 5, 2), color=HELP, alpha=0.18)
    ax.annotate(
        rf"lower 20%: $\ell={lo:.3f}>\tau_c$",
        xy=(lo, beta.pdf(lo, 5, 2)),
        xytext=(0.62, 1.15),
        fontsize=9,
        color=HELP,
        arrowprops=dict(arrowstyle="->", color=HELP, lw=0.8),
    )
    ax.set_xlabel(r"help-probability  $\theta$")
    ax.set_ylabel("posterior density")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 2.9)
    ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "memrep_beta.pdf"))
    plt.close(fig)


# ------------------------------------------------------ Fig 2: win probability
def fig_winprob():
    cards = [
        ("very strong  Beta(10,2)", 10, 2, HELP),
        ("helpful  Beta(5,2)", 5, 2, HELP),
        ("cold  Beta(1,1)", 1, 1, COLD),
        ("weak  Beta(2,4)", 2, 4, HARM),
    ]
    labels = [c[0] for c in cards]
    probs = [p_win(a, b) for _, a, b, _ in cards]
    colors = [c[3] for c in cards]
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    y = np.arange(len(cards))[::-1]
    ax.barh(y, probs, color=colors, alpha=0.85, height=0.6)
    ax.axvline(0.5, color=INK, ls=":", lw=1.2)
    ax.text(0.5, len(cards) - 0.35, "coin flip", fontsize=8.5, color=INK, ha="center")
    for yi, p in zip(y, probs):
        ax.text(p + 0.012, yi, f"{p:.0%}", va="center", fontsize=10, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9.5)
    ax.set_xlabel(
        r"$\Pr(\theta > \theta_0)$  — chance of beating the inject-nothing arm"
    )
    ax.set_xlim(0, 1)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "memrep_winprob.pdf"))
    plt.close(fig)


# ----------------------------------------------------------- Fig 3: EV bid
def fig_bid():
    rng = np.random.default_rng(7)
    n = 200000
    # bid = theta_bid * magnitude. The cold card has no magnitude of its own; it
    # borrows the round's warm median positive gain -- here the lone positive warm
    # card, +0.05 -- so exploration is scaled to the gains cards actually earn.
    warm_median = 0.05
    helpful = rng.beta(5, 2, n) * 0.05  # M = +0.05
    cold = rng.beta(1, 1, n) * warm_median  # borrowed warm-median magnitude
    harmful = rng.beta(2, 4, n) * (-0.075)  # M = -0.075
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    bins = np.linspace(-0.09, 0.09, 90)
    for data, c, lab in [
        (harmful, HARM, "harmful  $M=-0.075$"),
        (cold, COLD, "cold  borrows $\\hat M=+0.05$"),
        (helpful, HELP, "helpful  $M=+0.05$"),
    ]:
        ax.hist(data, bins=bins, color=c, alpha=0.55, density=True, label=lab)
    ax.axvline(0.0, color=INK, lw=1.6)
    ax.axvspan(-0.09, 0.0, color=HARM, alpha=0.06)
    ax.text(
        -0.045,
        ax.get_ylim()[1] * 0.9,
        "abstain\n(bid $\\leq \\phi=0$)",
        ha="center",
        va="top",
        fontsize=8.5,
        color=HARM,
    )
    ax.set_xlabel(r"realized bid  $=\ \tilde\theta \cdot \hat M$")
    ax.set_ylabel("density")
    ax.set_xlim(-0.09, 0.09)
    ax.legend(loc="upper right", fontsize=8.5, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "memrep_bid.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    fig_beta()
    fig_winprob()
    fig_bid()
    print("wrote memrep_beta.pdf, memrep_winprob.pdf, memrep_bid.pdf")
    for a, b in [(10, 2), (5, 2), (1, 1), (2, 4)]:
        print(f"  P(beat baseline) Beta({a},{b}) = {p_win(a, b):.3f}")
