# Adversarial Review: adversarial/heilbron-prover

**Reviewer**: Dr. Alexei Volkov (reviewer-2-adversary agent)
**Date**: 2026-04-06
Verdict: APPROVED

---

## Summary

This experiment proposes a Prover/Improver adversarial co-evolution on the Heilbron triangle problem (11 points, unit-area equilateral triangle). Two populations co-evolve: Constructors (Pop A) place points to maximize min_area while resisting improvement, and Improvers (Pop B) take configurations and try to increase min_area. The design is methodologically sound for a proof-of-concept. The fitness formulation creates a genuine zero-sum dynamic with a clean separation between the adversarial selection metric (fitness) and the true objective (actual_fitness = raw min_area). N=2 replicate pairs is the minimum for any reproducibility signal but is consistent with prior adversarial experiments in this project. The design inherits validated infrastructure from PR #169. I have minor concerns about a potential perverse incentive in the fitness formulation and a missing confound, but neither rises to the level of blocking.

## Checklist

| # | Check | Pass? | Notes |
|---|-------|-------|-------|
| 1 | N >= 2 per cell | PASS | 2 replicate pairs (4 runs). Minimum for reproducibility check. Appropriate for PoC. |
| 2 | Single IV | PASS | Single-condition experiment (adversarial co-evolution). No control arm -- this is concept validation, not a treatment-vs-control comparison. |
| 3 | Statistical plan | PASS | Alpha = 0.10 appropriate for N=2. Pre-post paired comparison is the right test. Spearman for H3 (convergence) is reasonable. |
| 4 | Fitness formulation | PASS (with caveat) | Zero-sum property holds. GAN analogy is apt. See Comment 4 for a minor concern about quality-resistance tradeoff. |
| 5 | Effect-size thresholds | PASS | +0.005 absolute min_area threshold is reasonable (~14% of target 0.0365). Absolute quality tiers (0.010/0.020/0.030) provide useful interpretive anchors. |
| 6 | Confounds | PASS (with caveat) | Major confounds addressed. See Comments 6a-6b for two additional confounds to acknowledge. |
| 7 | Stop criteria | PASS | Clear early termination (invalidity >80%, actual_fitness=0 through gen 5, sync block >60min). Run invalidation criteria well-specified. |

## Detailed Comments

### 1. N=2 pairs is adequate for proof-of-concept (PASS)

Two replicate pairs provide the minimum replication needed to distinguish signal from noise. The three-tier verdict system (POSITIVE/SUGGESTIVE/NULL) correctly calibrates conclusions to the sample size. The design document is appropriately humble -- it does not claim this will be a definitive study. The prior experiment (optimizer-vs-landscape) showed consistent qualitative patterns across N=2 pairs, providing precedent.

### 2. Single IV is clean (PASS)

This is a single-condition experiment testing whether the Prover/Improver adversarial dynamic works at all on a real optimization problem. There is no control arm (non-adversarial baseline), which means the experiment cannot prove that adversarial pressure is *better* than non-adversarial evolution. The design acknowledges this -- the question is "does it work?" not "is it better?" This is the right first question to ask. A follow-up experiment with a non-adversarial control would be the natural next step if results are POSITIVE.

### 3. Statistical plan is appropriate (PASS)

Alpha = 0.10 is correctly relaxed for N=2. The paired pre-post comparison (actual_fitness at gen 1 vs final gen) is the simplest valid test for the question. Spearman correlation for H3 (resistance trend) is sensible for ordinal data over time. No multiple comparison correction is needed since H1 is the sole primary hypothesis and H2/H3 are explicitly secondary/exploratory.

### 4. Fitness formulation creates valid adversarial dynamics (PASS, with caveat)

The zero-sum property (`resistance + improvement_ratio = 1.0`) is mathematically clean. The code in `evaluate.py` correctly implements the formulas from the design doc. I verified that:

- Pop A's cold-start fallback (no opponents) uses `fitness = quality` with `resistance = 1.0`, which is correct -- no opponents means no improvement possible.
- Pop B returns INVALID when no opponents are available, which correctly blocks evaluation until Constructors exist.
- Improvements are clamped to `max(delta, 0.0)` -- Improvers cannot hurt a configuration, only help or leave unchanged.
- Post-improvement configurations are re-validated (containment, shape, finiteness), preventing adversarial exploits through constraint violation.

**Caveat (minor)**: The `ALPHA = 0.5` weighting means a Constructor can achieve `fitness = 0.75` by having `quality = 0.5` (mediocre) and `resistance = 1.0` (trivially hard to improve because already at a local minimum of the landscape). Meanwhile, a Constructor with `quality = 1.0` (excellent) but `resistance = 0.5` gets `fitness = 0.75` as well. In principle, a degenerate local optimum with low min_area but high resistance could tie in fitness with a genuinely good configuration. The design document acknowledges this in Section 13 (Open Question 2) and the 0.5 weight does mitigate it (a truly degenerate configuration with near-zero quality would still score poorly). Since `actual_fitness` (raw min_area) is tracked separately and is the paper metric, this is monitored. I consider this acceptable for a PoC, but if resistance consistently dominates quality in the fitness rankings, an ALPHA amendment to 0.7 (quality-weighted) should be triggered.

**Recommendation**: Add a monitoring check at gen 10: if mean `quality` across Pop A frontier is below 0.3 while mean `resistance` is above 0.8, trigger the alpha amendment. This would catch the degenerate-optimum failure mode early.

### 5. Effect-size thresholds are reasonable (PASS)

The +0.005 absolute min_area threshold for POSITIVE verdict represents roughly one significant perturbation step in this problem. The absolute quality tiers (0.010 = moderate, 0.020 = good, 0.030 = excellent relative to target 0.0365) provide interpretive context. These are pre-specified and unambiguous.

One note: the design should clarify what `actual_fitness_gen1` means in context. At gen 1, Pop A has only the seed program (grid.py) plus up to 8 mutants. The gen 1 frontier is likely to be very low (the grid seed is naive), so the bar for "improvement over gen 1" is easy to clear. The more informative comparison is final `actual_fitness` vs the absolute quality tiers. The design already includes these tiers, so this is adequately addressed.

### 6a. Missing confound: seed quality bias (MINOR)

Both replicate pairs use identical seed programs (grid.py for Pop A, seed.py for Pop B). If the seed happens to land in a particular basin of attraction, both pairs may converge to similar solutions -- making cross-pair agreement look like robust replication when it is actually seed dependence.

**Mitigation already present**: MAP-Elites diversity + LLM mutation stochasticity should break seed dependence by gen 3-5. The `mutation_mode = rewrite` setting (full program rewrite, not incremental edit) further reduces seed influence.

**Recommendation**: Note this confound in Section 9. No design change needed, but acknowledge it so results can be interpreted with appropriate caution.

### 6b. Missing confound: Improver computational advantage (MINOR)

Pop B Improvers get 60 seconds per opponent configuration. With `scipy.optimize.minimize` available, a single well-written Improver could perform thousands of gradient steps within budget. Pop A Constructors must produce a static configuration in a single function call. This asymmetry could make Pop B dominant early (high improvement = high fitness, low resistance for Pop A), potentially discouraging the adversarial arms race.

The design acknowledges this in Section 13 (Open Question 1) but does not list it in Section 9 (Known Confounds). It should be listed there.

**Mitigation already present**: The 60s timeout and the quality component of Pop A's fitness prevent total collapse. As Improvers get better, only genuinely good configurations survive in Pop A, which is the desired dynamic.

### 7. Stop criteria are well-specified (PASS)

Early termination conditions are clear and conservative. The invalidity >80% threshold at gen 5 gives the populations time to stabilize before judging. The sync hook block >60min catches deadlocks. Run invalidation for n_opponents=0 beyond gen 1 correctly identifies infrastructure failure vs cold start.

### 8. Infrastructure and implementation quality (informational)

The `evaluate.py` files for both populations are well-written. Error handling is thorough -- every `try/except` path returns a valid metric dict with appropriate sentinel values. The `_validate_config` helper is shared and consistent between populations. The `helper.py` files are identical, ensuring consistent geometry computation. The `metrics.yaml` files correctly tag `fitness` as primary and `actual_fitness` as non-primary (for monitoring only).

One implementation detail worth noting: Pop B's `mean_improvement_raw` is computed as `sum(d * Q_MAX for d in deltas_norm) / len(deltas_norm)`, which back-converts normalized deltas to raw units. This is mathematically equivalent to `sum(raw_deltas) / len(raw_deltas)` only when no delta exceeds Q_MAX (since normalization clamps at 1.0). For very large improvements this would undercount, but in practice improvements will be small relative to Q_MAX, so this is fine.

## Verdict

**APPROVED**

The design is methodologically sound for a proof-of-concept adversarial co-evolution experiment. The fitness formulation creates a genuine zero-sum dynamic. The separation of `fitness` (selection metric) from `actual_fitness` (paper metric) is clean and prevents adversarial gaming of the reported results. N=2 pairs is appropriate for PoC, and the three-tier verdict system correctly scopes conclusions.

**Non-blocking recommendations** (implement if convenient, not required):

1. Add a gen-10 monitoring check for the quality-vs-resistance balance (Comment 4) to trigger an alpha amendment if degenerate optima dominate.
2. Add "seed quality bias" and "Improver computational advantage" to Section 9 confound table (Comments 6a, 6b) for completeness.
3. Clarify in the effect-size section that the gen-1 baseline is expected to be low due to the naive grid seed.
