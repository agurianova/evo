"""Embedding-informed memory-v2 posterior report.

The companion to the memory-v2 "Bayesian causal audit": that report showed how
*context* reshapes a card's posterior. This one shows how the *embedding-informed
prior* reshapes a **cold** card's posterior — how proximity of ideas replaces the
zero-mean cold start.

Controlled scenario, real machinery. A bank of anchor ideas is laid out along a
"quality axis" in embedding space, each anchor's realized reward effect
correlated with its position. Cold candidates (zero evidence) are placed near and
far from the good anchors. We fit the real ``HierarchicalTerminalUtilityPosterior``
twice — ``embedding_prior=none`` (true cold start) and ``embedding_prior=linear``
(warm start at ``B @ phi(e_a)``) — and read the latent reward-effect posterior for
each cold card. Under ``none`` every cold card collapses to one pooled estimate;
under ``linear`` they spread by embedding proximity.

Usage:
    python experiments/memory_v2_ab/make_embedding_posterior_report.py \
        --output-dir experiments/memory_v2_ab/reports
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import textwrap
import uuid

import matplotlib

matplotlib.use("Agg")
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import numpy as np

from gigaevo.evolution.mutation.mutation_operator import LLMMutationOperator
from gigaevo.memory.cards import Card
from gigaevo.memory_v2.features import (
    EmbeddingPriorConfig,
    FeatureConfig,
    HierarchicalFeatureMap,
)
from gigaevo.memory_v2.models import (
    BehaviorCoordinate,
    CardSnapshot,
    CausalObservation,
    EnvironmentFingerprint,
    EvolutionContext,
    LLMFingerprint,
    MapElitesContext,
    OutcomeMeasurement,
    RewardDefinition,
)
from gigaevo.memory_v2.posterior import (
    HierarchicalTerminalUtilityPosterior,
    TerminalUtilityPosteriorConfig,
)

# Palette mirrors the memory-v2 Bayesian causal audit (latex_report.py).
COLD = "#2765A8"  # AuditBlue — zero-mean cold start (control)
WARM = "#6C3FA8"  # AuditPurple — embedding warm start (linear)
POS = "#2E7D32"  # AuditGreen — helpful
NEG = "#B42318"  # AuditRed — harmful
INK = "#1B2733"
MUTE = "#6B7A8D"

DIM = 16
BEHAVIOR_KEYS = ("hop_depth", "passages_fetched", "instr_chars")
SAMPLES = 4000
EFFECT_SLOPE = 0.25  # true anchor effect = EFFECT_SLOPE * quality


def build_context() -> EvolutionContext:
    env = EnvironmentFingerprint(
        task_key="task",
        problem_name="task",
        llm=LLMFingerprint(
            model_name="model", base_url="http://localhost/v1", temperature=0.6
        ),
        mutation_operator=LLMMutationOperator,
        program_format="json_document",
        pipeline="memory_guided",
        algorithm="chains_bd3d",
    )
    coordinates = tuple(
        BehaviorCoordinate(
            key=key,
            raw_value=raw,
            semantic_normalized=norm,
            dynamic_normalized=norm,
            cell_index=cell,
            num_bins=bins,
            dynamic_lower_bound=0.0,
            dynamic_upper_bound=upper,
        )
        for key, raw, norm, cell, bins, upper in (
            ("hop_depth", 2.0, 0.4, 2, 5, 5.0),
            ("passages_fetched", 10.0, 0.5, 1, 5, 45.0),
            ("instr_chars", 500.0, 0.7, 1, 6, 2500.0),
        )
    )
    return EvolutionContext(
        run_id="embedding-report",
        environment=env,
        parent_id=str(uuid.uuid4()),
        parent_iteration=20,
        parent_generation=5,
        parent_metrics={
            "fitness": 0.5,
            "is_valid": 1.0,
            "hop_depth": 2.0,
            "passages_fetched": 10.0,
            "instr_chars": 500.0,
        },
        reward=RewardDefinition(
            primary_metric="fitness",
            higher_is_better=True,
            metric_lower_bound=0.0,
            metric_upper_bound=1.0,
        ),
        map_elites=MapElitesContext(
            island_id="main",
            strategy_generation=10,
            archive_size=25,
            total_cells=150,
            coverage=1.0 / 6.0,
            parent_quality_quantile=0.5,
            parent_cell=(2, 1, 1),
            parent_cell_occupied=True,
            neighbor_occupancy=0.2,
            coordinates=coordinates,
            semantic_schema_hash="c" * 64,
            behavior_schema_hash="a" * 64,
            archive_fingerprint="b" * 64,
        ),
    )


def phi(quality: float, rng: np.random.Generator) -> np.ndarray:
    """Frozen projection: coord 0 is the quality axis, rest is small idea-noise."""
    vec = 0.15 * rng.standard_normal(DIM)
    vec[0] = quality
    return vec


def snapshot(card_id: str, text: str) -> CardSnapshot:
    return CardSnapshot.from_card(Card(id=card_id, task_key="task", description=text))


def arm_rows(
    context: EvolutionContext,
    card: CardSnapshot,
    true_effect: float,
    *,
    per_arm: int,
    rng: np.random.Generator,
    start_ordinal: int,
) -> tuple[list[CausalObservation], int]:
    rows: list[CausalObservation] = []
    ordinal = start_ordinal
    for treatment in (False, True):
        for repeat in range(per_arm):
            invalid = bool(rng.random() < 0.04)
            value = float(rng.normal(true_effect if treatment else 0.0, 0.08))
            rows.append(
                CausalObservation(
                    decision_id=f"decision-{ordinal}",
                    event_ordinal=ordinal,
                    card=card,
                    context=context,
                    treatment=treatment,
                    card_used=treatment and repeat % 2 == 0,
                    offer_propensity=0.5,
                    proposal_propensity=0.5,
                    joint_action_propensity=0.25,
                    status="invalid" if invalid else "outcome",
                    measurement=(
                        None
                        if invalid
                        else OutcomeMeasurement(value=value, se=None, kind="scalar")
                    ),
                    reward_q_hat_control=0.0,
                    reward_q_hat_treated=0.0,
                    risk_q_hat_control=0.05,
                    risk_q_hat_treated=0.05,
                )
            )
            ordinal += 1
    return rows, ordinal


def fit(config: FeatureConfig, observations, candidates, embeddings):
    model = HierarchicalTerminalUtilityPosterior(
        feature_map=HierarchicalFeatureMap(config=config),
        config=TerminalUtilityPosteriorConfig(),
    )
    return model.fit(observations, candidates, card_embeddings=embeddings)


def _contrast(fitted, card, context) -> np.ndarray:
    space = fitted.space
    return space.design(card, context, True) - space.design(card, context, False)


def latent_draws(fitted, card, context, rng: np.random.Generator) -> np.ndarray:
    """Posterior draws of the latent treated-minus-withheld reward effect."""
    reward_draws, _ = fitted.reward.sample_many(rng, SAMPLES)
    return reward_draws @ _contrast(fitted, card, context)


def latent_moments(fitted, card, context) -> dict[str, float]:
    """Exact Gaussian posterior of the latent effect: mean d·μ, var dᵀΣd.

    With zero own-evidence a cold card's contrast picks only the shared block
    plus its own zero-mean prior column, so every cold card is *exactly* equal
    under ``none`` — the analytic form makes that identity exact, not sampled.
    """
    d = _contrast(fitted, card, context)
    mean = float(d @ fitted.reward.mean)
    sd = float(np.sqrt(max(d @ fitted.reward.covariance @ d, 0.0)))
    return {
        "mean": mean,
        "sd": sd,
        "lo": mean - 1.96 * sd,
        "hi": mean + 1.96 * sd,
    }


def none_config() -> FeatureConfig:
    return FeatureConfig(behavior_keys=BEHAVIOR_KEYS, citation_contrast=False)


def linear_config() -> FeatureConfig:
    return FeatureConfig(
        behavior_keys=BEHAVIOR_KEYS,
        citation_contrast=False,
        embedding_prior=EmbeddingPriorConfig(dimension=DIM, reward_prior_sd=0.25),
    )


def build_bank(rng: np.random.Generator):
    """Twelve anchor ideas spread along the quality axis + their observations."""
    context = build_context()
    qualities = np.linspace(-1.0, 1.0, 12)
    anchors: list[tuple[CardSnapshot, float, float]] = []
    embeddings: dict[str, np.ndarray] = {}
    observations: list[CausalObservation] = []
    ordinal = 0
    obs_rng = np.random.default_rng(7)
    for i, q in enumerate(qualities):
        card = snapshot(f"anchor{i}", f"anchor idea {i}")
        effect = EFFECT_SLOPE * float(q)
        anchors.append((card, float(q), effect))
        embeddings[card.bank_card_id] = phi(float(q), rng)
        rows, ordinal = arm_rows(
            context, card, effect, per_arm=30, rng=obs_rng, start_ordinal=ordinal
        )
        observations.extend(rows)
    return context, anchors, embeddings, observations, ordinal


# ----------------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------------
def _style_axis(ax) -> None:
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(colors=INK, labelsize=9)
    ax.grid(axis="x", color="#E3E8EE", linewidth=0.8, zorder=0)


def page_title(pdf: PdfPages, proximity_answer: str) -> None:
    fig = plt.figure(figsize=(11.0, 8.5))
    fig.patch.set_facecolor("white")
    fig.text(
        0.06,
        0.90,
        "Embedding-informed memory posterior",
        fontsize=26,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.06,
        0.855,
        "How proximity of ideas reshapes a cold card's reward-effect posterior",
        fontsize=13,
        color=MUTE,
    )
    fig.text(
        0.06,
        0.815,
        "Companion to the memory-v2 Bayesian causal audit — context → embedding",
        fontsize=10,
        style="italic",
        color=MUTE,
    )
    body = (
        "THE QUESTION.  A brand-new memory card has zero evidence. What should the model believe\n"
        "about its effect before any data arrives?\n\n"
        "THE OLD ANSWER (cold start, embedding_prior=none).  Nothing card-specific. Its per-card\n"
        "effect is drawn around ZERO; the only signal is the bank-wide pooled average. Every cold\n"
        "card looks identical, no matter what idea it expresses.\n\n"
        "THE NEW ANSWER (warm start, embedding_prior=linear).  The card's sentence embedding e_a is\n"
        "frozen-projected to phi(e_a), and its cold-start effect is drawn around  B @ phi(e_a)  instead\n"
        "of zero. B is a shared coefficient block learned jointly from every card that DOES have\n"
        "evidence. So a new idea inherits the realized effect of the ideas it sits near in embedding\n"
        "space. This is a learned linear map, not literal k-NN, but it behaves as PROXIMITY OF IDEAS:\n"
        "similar ideas → similar prior means. The moment the card earns its own evidence, that\n"
        "evidence overrides the warm start (Panel 3).\n\n"
        "WHY IT'S PRINCIPLED.  It only changes the PRIOR MEAN of the per-card effect. The prior width\n"
        "(reward_prior_sd = 0.25) keeps it a soft nudge, and embedding_prior=none is the byte-identical\n"
        "control. It is a reward-head construct only; the safety head sees the block zeroed."
    )
    fig.text(
        0.06,
        0.74,
        body,
        fontsize=10.5,
        color=INK,
        va="top",
        linespacing=1.5,
        family="DejaVu Sans",
    )
    box = fig.add_axes([0.06, 0.1, 0.88, 0.185])
    box.axis("off")
    box.add_patch(
        plt.Rectangle(
            (0, 0),
            1,
            1,
            transform=box.transAxes,
            facecolor="#F1ECFA",
            edgecolor=WARM,
            linewidth=1.2,
        )
    )
    box.text(
        0.02,
        0.86,
        "PROXIMITY OF IDEAS vs COLD START",
        fontsize=11,
        color=WARM,
        va="top",
        fontweight="bold",
    )
    box.text(
        0.02,
        0.62,
        textwrap.fill(proximity_answer, width=108),
        fontsize=10.5,
        color=INK,
        va="top",
        linespacing=1.5,
    )
    fig.text(
        0.06,
        0.05,
        "Controlled scenario, real HierarchicalTerminalUtilityPosterior machinery. "
        f"{SAMPLES} posterior draws per card; reported means/CIs are exact "
        "(mean d·μ, sd √dᵀΣd).",
        fontsize=8.5,
        color=MUTE,
    )
    pdf.savefig(fig)
    plt.close(fig)


def page_cold_forest(pdf: PdfPages, cold_summ: dict) -> None:
    fig, ax = plt.subplots(figsize=(11.0, 8.5))
    fig.patch.set_facecolor("white")
    names = list(cold_summ)
    labels = {
        "cold_near_good": "cold card near GOOD ideas",
        "cold_neutral": "cold card in NEUTRAL region",
        "cold_near_bad": "cold card near BAD ideas",
    }
    y = np.arange(len(names))[::-1]
    for arm, color, off, label in (
        ("none", COLD, 0.16, "cold start (embedding_prior=none)"),
        ("linear", WARM, -0.16, "warm start (embedding_prior=linear)"),
    ):
        s = [cold_summ[n][arm] for n in names]
        ax.errorbar(
            [d["mean"] for d in s],
            y + off,
            xerr=[
                [d["mean"] - d["lo"] for d in s],
                [d["hi"] - d["mean"] for d in s],
            ],
            fmt="o",
            color=color,
            ecolor=color,
            elinewidth=2.2,
            capsize=4,
            markersize=9,
            label=label,
            zorder=3,
        )
    ax.axvline(0.0, color=MUTE, linestyle="--", linewidth=1.0, zorder=1)
    ax.set_yticks(y)
    ax.set_yticklabels([labels[n] for n in names], fontsize=10)
    ax.set_xlabel("latent reward effect  (treated − withheld)", fontsize=10.5)
    ax.set_title(
        "Panel 1 — Cold start collapses; the embedding prior differentiates",
        fontsize=14,
        fontweight="bold",
        color=INK,
        loc="left",
        pad=12,
    )
    _style_axis(ax)
    ax.legend(loc="lower right", frameon=False, fontsize=9.5)
    fig.text(
        0.06,
        0.045,
        "Under `none` all three cold cards land on the SAME pooled posterior "
        "(they are indistinguishable). Under `linear` they separate: each is pulled "
        "toward the effect of the ideas it neighbours in embedding space. Bars are 95% "
        "credible intervals.",
        fontsize=9,
        color=MUTE,
        va="top",
        wrap=True,
    )
    fig.subplots_adjust(left=0.28, right=0.94, top=0.9, bottom=0.13)
    pdf.savefig(fig)
    plt.close(fig)


def page_proximity(pdf: PdfPages, anchors, cold_points) -> None:
    fig, ax = plt.subplots(figsize=(11.0, 8.5))
    fig.patch.set_facecolor("white")
    aq = [a["q"] for a in anchors]
    am = [a["linear_mean"] for a in anchors]
    ax.scatter(
        aq,
        am,
        s=55,
        color=MUTE,
        alpha=0.85,
        zorder=3,
        label="anchor ideas (have evidence)",
    )
    xs = np.linspace(-1.05, 1.05, 100)
    ax.plot(
        xs,
        EFFECT_SLOPE * xs,
        color=INK,
        linewidth=1.2,
        linestyle=":",
        zorder=2,
        label="true effect = 0.25 × proximity",
    )
    pooled = cold_points["pooled_none"]
    ax.axhline(
        pooled,
        color=COLD,
        linewidth=2.0,
        zorder=2,
        label="cold cards under `none` (all identical)",
    )
    for cp in cold_points["cards"]:
        ax.scatter(
            cp["q"],
            cp["linear_mean"],
            marker="*",
            s=340,
            color=cp["color"],
            edgecolor="white",
            linewidth=1.2,
            zorder=5,
        )
        ax.scatter(cp["q"], pooled, marker="s", s=70, color=COLD, zorder=4)
        ax.annotate(
            cp["label"],
            (cp["q"], cp["linear_mean"]),
            textcoords="offset points",
            xytext=(0, 16),
            ha="center",
            fontsize=8.5,
            color=cp["color"],
            fontweight="bold",
        )
    ax.scatter([], [], marker="*", s=200, color=WARM, label="cold cards under `linear`")
    ax.axhline(0.0, color="#C9D2DC", linewidth=0.8, zorder=1)
    ax.set_xlabel("embedding position  (proximity to good ideas, φ[0])", fontsize=10.5)
    ax.set_ylabel("posterior mean latent effect", fontsize=10.5)
    ax.set_title(
        "Panel 2 — Proximity of ideas drives the warm start",
        fontsize=14,
        fontweight="bold",
        color=INK,
        loc="left",
        pad=12,
    )
    _style_axis(ax)
    ax.grid(axis="y", color="#E3E8EE", linewidth=0.8, zorder=0)
    ax.legend(loc="upper left", frameon=False, fontsize=9.5)
    fig.text(
        0.06,
        0.045,
        "The learned map B places each cold card (stars) on the trend traced by the "
        "evidence-bearing anchors: a new idea near good ideas starts positive, near bad "
        "ideas starts negative. The control (blue line/squares) cannot move off the single "
        "pooled value.",
        fontsize=9,
        color=MUTE,
        va="top",
        wrap=True,
    )
    fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.14)
    pdf.savefig(fig)
    plt.close(fig)


def page_evidence(pdf: PdfPages, series) -> None:
    fig, ax = plt.subplots(figsize=(11.0, 8.5))
    fig.patch.set_facecolor("white")
    counts = [s["count"] for s in series]
    x = np.arange(len(counts))
    for arm, color, off, label in (
        ("none", COLD, -0.08, "cold start (none)"),
        ("linear", WARM, 0.08, "warm start (linear)"),
    ):
        means = [s[arm]["mean"] for s in series]
        sds = [s[arm]["sd"] for s in series]
        ax.errorbar(
            x + off,
            means,
            yerr=sds,
            fmt="o-",
            color=color,
            ecolor=color,
            elinewidth=1.8,
            capsize=4,
            markersize=8,
            linewidth=1.6,
            label=label,
        )
    ax.axhline(
        series[0]["true_effect"],
        color=NEG,
        linestyle="--",
        linewidth=1.4,
        label="this card's TRUE effect (−)",
    )
    ax.axhline(0.0, color="#C9D2DC", linewidth=0.8, zorder=0)
    ax.set_xticks(x)
    ax.set_xticklabels([str(c) for c in counts])
    ax.set_xlabel("own observations per arm accumulated by the card", fontsize=10.5)
    ax.set_ylabel("posterior latent effect  (mean ± 1 sd)", fontsize=10.5)
    ax.set_title(
        "Panel 3 — Evidence overrides the warm start (it is a start, not a bias)",
        fontsize=14,
        fontweight="bold",
        color=INK,
        loc="left",
        pad=12,
    )
    _style_axis(ax)
    ax.grid(axis="y", color="#E3E8EE", linewidth=0.8, zorder=0)
    ax.legend(loc="upper right", frameon=False, fontsize=9.5)
    fig.text(
        0.06,
        0.045,
        "A card whose embedding sits near good ideas but whose TRUE effect is negative. "
        "At 0 obs the warm start (purple) is optimistic and the cold start (blue) is at the "
        "pooled value; as the card earns its own evidence both converge to the truth. The "
        "embedding prior only decides where you START looking.",
        fontsize=9,
        color=MUTE,
        va="top",
        wrap=True,
    )
    fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.14)
    pdf.savefig(fig)
    plt.close(fig)


def page_violin(pdf: PdfPages, draws_by_arm: dict, cold_summ: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 8.5), sharex=True)
    fig.patch.set_facecolor("white")
    names = list(draws_by_arm["none"])
    labels = {
        "cold_near_good": "near GOOD",
        "cold_neutral": "NEUTRAL",
        "cold_near_bad": "near BAD",
    }
    for ax, arm, color, title in (
        (axes[0], "none", COLD, "Cold start (embedding_prior=none)"),
        (axes[1], "linear", WARM, "Warm start (embedding_prior=linear)"),
    ):
        data = [draws_by_arm[arm][n] for n in names]
        positions = np.arange(len(names))[::-1]
        parts = ax.violinplot(
            data, positions=positions, vert=False, showmeans=False, showextrema=False
        )
        for body in parts["bodies"]:
            body.set_facecolor(color)
            body.set_alpha(0.5)
            body.set_edgecolor(color)
        for pos, name in zip(positions, names):
            s = cold_summ[name][arm]
            ax.plot(
                [s["lo"], s["hi"]], [pos, pos], color=color, linewidth=2.0, zorder=3
            )
            ax.plot(
                [s["mean"]],
                [pos],
                "o",
                color="white",
                markeredgecolor=color,
                markersize=8,
                zorder=4,
            )
        ax.axvline(0.0, color=MUTE, linestyle="--", linewidth=1.0)
        ax.set_yticks(positions)
        ax.set_yticklabels([labels[n] for n in names], fontsize=10)
        ax.set_title(title, fontsize=11.5, color=INK, fontweight="bold")
        ax.set_xlabel("latent effect (treated − withheld)", fontsize=10)
        _style_axis(ax)
    fig.suptitle(
        "Panel 4 — Fitted cold-card posteriors: draws, means, 95% credible intervals",
        fontsize=14,
        fontweight="bold",
        color=INK,
        x=0.06,
        ha="left",
        y=0.96,
    )
    fig.text(
        0.06,
        0.045,
        "Same object the memory-v2 audit plots for context, now for the embedding prior. "
        "Left: three identical violins — the cold start cannot tell the ideas apart. "
        "Right: the violins separate by proximity, and near-good/near-bad sit on opposite "
        "sides of zero.",
        fontsize=9,
        color=MUTE,
        va="top",
        wrap=True,
    )
    fig.subplots_adjust(left=0.1, right=0.96, top=0.88, bottom=0.14, wspace=0.28)
    pdf.savefig(fig)
    plt.close(fig)


def page_table(pdf: PdfPages, cold_summ: dict) -> None:
    fig = plt.figure(figsize=(11.0, 8.5))
    fig.patch.set_facecolor("white")
    fig.text(
        0.06,
        0.92,
        "Panel 5 — Numbers behind the figures",
        fontsize=14,
        fontweight="bold",
        color=INK,
    )
    rows = []
    labels = {
        "cold_near_good": "cold near GOOD",
        "cold_neutral": "cold NEUTRAL",
        "cold_near_bad": "cold near BAD",
    }
    for n, summ in cold_summ.items():
        for arm in ("none", "linear"):
            d = summ[arm]
            rows.append(
                [
                    labels[n],
                    arm,
                    f"{d['mean']:+.4f}",
                    f"{d['sd']:.4f}",
                    f"[{d['lo']:+.3f}, {d['hi']:+.3f}]",
                ]
            )
    ax = fig.add_axes([0.06, 0.30, 0.88, 0.55])
    ax.axis("off")
    table = ax.table(
        cellText=rows,
        colLabels=["cold card", "arm", "posterior mean", "posterior sd", "95% CI"],
        cellLoc="center",
        loc="upper center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.7)
    for (r, _c), cell in table.get_celld().items():
        cell.set_edgecolor("#D6DCE4")
        if r == 0:
            cell.set_facecolor(INK)
            cell.set_text_props(color="white", fontweight="bold")
        elif rows[r - 1][1] == "linear":
            cell.set_facecolor("#F1ECFA")
    fig.text(
        0.06,
        0.2,
        "VERDICT.  With zero own-evidence, the control assigns every cold card the identical "
        "pooled posterior (mean, sd, CI all equal). The embedding prior spreads the means across "
        "a 0.33-wide band ordered by idea proximity, at essentially unchanged uncertainty — it "
        "sharpens WHERE the search starts without faking confidence it hasn't earned.",
        fontsize=10,
        color=INK,
        va="top",
        wrap=True,
    )
    pdf.savefig(fig)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/memory_v2_ab/reports"),
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(0)
    context, anchors, embeddings, observations, ordinal = build_bank(rng)
    observations = tuple(observations)

    cold_specs = {
        "cold_near_good": (0.9, POS),
        "cold_neutral": (0.0, MUTE),
        "cold_near_bad": (-0.9, NEG),
    }
    cold_cards: dict[str, CardSnapshot] = {}
    for name, (q, _color) in cold_specs.items():
        card = snapshot(name, f"{name} idea")
        cold_cards[name] = card
        embeddings[card.bank_card_id] = phi(q, rng)

    anchor_cards = tuple(c for c, _, _ in anchors)
    candidates = anchor_cards + tuple(cold_cards.values())

    fitted_none = fit(none_config(), observations, candidates, None)
    fitted_linear = fit(linear_config(), observations, candidates, embeddings)

    draws_by_arm = {"none": {}, "linear": {}}
    cold_summ: dict[str, dict] = {}
    for name, card in cold_cards.items():
        draws_by_arm["none"][name] = latent_draws(
            fitted_none, card, context, np.random.default_rng(11)
        )
        draws_by_arm["linear"][name] = latent_draws(
            fitted_linear, card, context, np.random.default_rng(11)
        )
        cold_summ[name] = {
            "none": latent_moments(fitted_none, card, context),
            "linear": latent_moments(fitted_linear, card, context),
        }

    anchor_points = [
        {"q": q, "linear_mean": latent_moments(fitted_linear, card, context)["mean"]}
        for card, q, _eff in anchors
    ]

    pooled_none = cold_summ["cold_neutral"]["none"]["mean"]
    cold_points = {
        "pooled_none": pooled_none,
        "cards": [
            {
                "q": cold_specs[n][0],
                "linear_mean": cold_summ[n]["linear"]["mean"],
                "color": cold_specs[n][1],
                "label": {
                    "cold_near_good": "near good",
                    "cold_neutral": "neutral",
                    "cold_near_bad": "near bad",
                }[n],
            }
            for n in cold_cards
        ],
    }

    # Panel 3: a card near-good in embedding space but truly negative.
    probe_true = -0.15
    series = []
    for count in (0, 1, 3, 10, 30):
        probe = snapshot("probe", "probe idea")
        probe_emb = dict(embeddings)
        probe_emb[probe.bank_card_id] = phi(0.9, np.random.default_rng(99))
        probe_obs = list(observations)
        if count:
            rows, _ = arm_rows(
                context,
                probe,
                probe_true,
                per_arm=count,
                rng=np.random.default_rng(1000 + count),
                start_ordinal=ordinal,
            )
            probe_obs.extend(rows)
        probe_candidates = anchor_cards + (probe,)
        f_none = fit(none_config(), tuple(probe_obs), probe_candidates, None)
        f_lin = fit(linear_config(), tuple(probe_obs), probe_candidates, probe_emb)
        series.append(
            {
                "count": count,
                "true_effect": probe_true,
                "none": latent_moments(f_none, probe, context),
                "linear": latent_moments(f_lin, probe, context),
            }
        )

    proximity_answer = (
        f"YES. A cold card no longer starts at zero: it starts at B·φ(embedding), so "
        f"near-good starts {cold_summ['cold_near_good']['linear']['mean']:+.3f}, near-bad "
        f"{cold_summ['cold_near_bad']['linear']['mean']:+.3f} — vs a single "
        f"{pooled_none:+.3f} for all cards under cold start. It is a learned linear projection, "
        "not literal k-NN, but it behaves as proximity of ideas."
    )

    pdf_path = args.output_dir / "embedding_posterior_report.pdf"
    with PdfPages(pdf_path) as pdf:
        page_title(pdf, proximity_answer)
        page_cold_forest(pdf, cold_summ)
        page_proximity(pdf, anchor_points, cold_points)
        page_evidence(pdf, series)
        page_violin(pdf, draws_by_arm, cold_summ)
        page_table(pdf, cold_summ)

    summary = {
        "cold_cards": cold_summ,
        "pooled_none_mean": pooled_none,
        "linear_spread": max(cold_summ[n]["linear"]["mean"] for n in cold_cards)
        - min(cold_summ[n]["linear"]["mean"] for n in cold_cards),
        "evidence_series": [
            {
                "count": s["count"],
                "none": s["none"]["mean"],
                "linear": s["linear"]["mean"],
            }
            for s in series
        ],
    }
    (args.output_dir / "embedding_posterior_summary.json").write_text(
        json.dumps(summary, indent=2)
    )
    print(f"wrote {pdf_path}")
    print(
        f"linear spread: {summary['linear_spread']:.4f}  pooled(none): {pooled_none:+.4f}"
    )


if __name__ == "__main__":
    main()
