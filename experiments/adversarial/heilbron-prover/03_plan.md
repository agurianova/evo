# Pre-Registration: Adversarial Co-Evolution — Heilbron Prover/Improver

**Date**: 2026-04-06
**Protocol version**: 1.0
**Pre-registration commit**: `1754672`
**GitHub PR**: #183 (branch: `exp/adversarial-heilbron-prover`)
**Tracking issue**: N/A
**Design doc**: `experiments/adversarial/heilbron-prover/01_design.md`
**Review doc**: `experiments/adversarial/heilbron-prover/02_review.md`
**Evaluation script**: N/A (no test split; `has_test_set: false`)

---

## Hypothesis

**H1 (primary -- actual quality)**: Adversarial Prover/Improver pressure drives Pop A Constructors toward higher-quality Heilbron configurations. The frontier `actual_fitness` (raw min_area) improves over generations for both replicate pairs.

**H0**: Adversarial pressure does NOT improve actual quality. At least one pair's Pop A `actual_fitness` shows no improvement from gen 1 to final gen.

**H2 (arms race)**: Both populations show positive adversarial fitness improvement from gen 1 to final gen, averaged across pairs.

**H3 (convergence)**: Pop A's `resistance` metric increases over time as Constructors evolve toward genuine local optima.

**Primary metric**: `actual_fitness` (raw min_area) frontier -- this is the true Heilbron quality, independent of adversarial dynamics.
**Significance threshold**: alpha = 0.10 (relaxed for N=2 pairs)

---

## Fitness Formulas

### Pop A (Constructor) -- "Generator" in GAN analogy

```
quality       = min(min_area(points) / 0.0365, 1.0)
delta_k       = max(min_area(I_k(points)) - min_area(points), 0.0)
resistance    = 1.0 - mean_k(min(delta_k / 0.0365, 1.0))
fitness       = 0.5 * quality + 0.5 * resistance
actual_fitness = min_area(points)    [raw, for paper]
```

### Pop B (Improver) -- "Discriminator" in GAN analogy

```
delta_k       = max(min_area(improve(P_k)) - min_area(P_k), 0.0)
fitness       = mean_k(min(delta_k / 0.0365, 1.0))
actual_fitness = max_k(min_area(improve(P_k)))
```

### Zero-sum: `resistance + improvement_ratio = 1.0`

---

## Run Design Table

| Pair | Pop | Label | `redis.db` | `pipeline` | `problem.name` | `opponent_redis_db` | `opponent_redis_prefix` |
|------|-----|-------|------------|-----------|----------------|---------------------|-------------------------|
| 1 | A | P1-A | 1 | adversarial_coevo | heilbron_adversarial/pop_a | 2 | heilbron_adversarial/pop_b |
| 1 | B | P1-B | 2 | adversarial_coevo | heilbron_adversarial/pop_b | 1 | heilbron_adversarial/pop_a |
| 2 | A | P2-A | 3 | adversarial_coevo | heilbron_adversarial/pop_a | 4 | heilbron_adversarial/pop_b |
| 2 | B | P2-B | 4 | adversarial_coevo | heilbron_adversarial/pop_b | 3 | heilbron_adversarial/pop_a |

All 4 processes: `llm_base_url=http://10.232.30.185:4000/v1`, `model_name=Qwen3-235B-A22B-Thinking-2507`

---

## Controlled Variables

| Field | Value |
|-------|-------|
| pipeline | adversarial_coevo |
| max_generations | 20 |
| num_parents | 1 |
| max_elites_per_generation | 8 |
| max_mutations_per_generation | 8 |
| mutation_mode | rewrite |
| stage_timeout | 3000 |
| dag_timeout | 7200 |
| n_opponents | 5 |
| per_opponent_timeout | 60.0s |
| alpha (quality vs resistance) | 0.5 |
| Q_MAX (normalization) | 0.0365 |
| Mutation LLM | Qwen3-235B-A22B-Thinking via LiteLLM proxy |
| MAP-Elites | Single island (fitness_island), 150 bins |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- LLM sampling temperature in mutation generation
- `random.sample` in opponent selection (fitness-proportional)
- `random.sample` in `FormatterStage` (failure sampling per generation)
- Process scheduling affecting lockstep timing

Cross-pair comparison (N=2 replicate pairs) provides the reproducibility check.

---

## Dataset Checksums

N/A -- pure combinatorial optimization (Heilbron triangle problem, 11 points in unit-area triangle).

---

## Success Criteria

### Primary: actual quality improvement

| Pattern | Verdict |
|---------|---------|
| Both pairs' Pop A `actual_fitness` increases >= 0.005 from gen 1 | **POSITIVE** |
| One pair improves, one stagnates | **SUGGESTIVE** |
| Neither pair improves `actual_fitness` | **NULL** |

### Secondary: arms race

| Pattern | Verdict |
|---------|---------|
| All 4 adversarial fitness improvements positive | ARMS RACE |
| Asymmetric (one population stagnates) | ASYMMETRIC |
| Both stagnate | NULL |

### Infrastructure

PASS if: generation parity <= 2, n_opponents > 0 at gen 1, all processes reach gen 20.

---

## Monitoring Plan

`max_generations`: 20

- Gen 2 (~10%): smoke check -- all PIDs alive, Redis keys growing, n_opponents > 0, actual_fitness > 0
- Gen 5 (~25%): first checkpoint -- actual_fitness frontier for Pop A, invalidity rate
- Gen 10 (~50%): midpoint -- actual_fitness trajectory, resistance trend
- Gen 20 (100%): final evaluation + program inspection + analysis

Early termination: invalidity > 80% at gen 5, or actual_fitness = 0 through gen 5, or sync hook blocks > 60 min.

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|

Watchdog PID:
Launch commit: _(to be filled at launch)_

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|

---

## Amendments

_(Add numbered entries here for any post-registration changes.)_
