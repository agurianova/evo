# Pre-Registration: heilbron/asymmetric-iterations-v2

**Date**: 2026-04-14
**Protocol version**: 1.0
**Pre-registration commit**: `<hash>` -- commit this file BEFORE any code changes
**GitHub PR**: #<number> (branch: `exp/heilbron/asymmetric-iterations-v2`)
**Tracking issue**: N/A
**Design doc**: `experiments/heilbron/asymmetric-iterations-v2/01_design.md`
**Review doc**: N/A (replication of approved design from heilbron/asymmetric-iterations PR #204)
**Evaluation script**: N/A (no test split -- optimization task)

---

## Hypothesis

**H0**: Neither feedback mode (Composition nor Gradient-in-prompt) with K=1 inner iterations and source code access changes Constructor actual_fitness relative to historical baseline (0.03449).
**H1**: At least one feedback mode produces Constructor actual_fitness meaningfully different from baseline.
**Primary metric**: Constructor actual_fitness at gen 50 (best raw min_area)
**Significance threshold**: Descriptive (N=2 per arm insufficient for formal testing)

---

## Run Design Table

| Run | Label | DB | Pipeline | Problem | Mutation URL | Condition |
|-----|-------|----|----------|---------|-------------|-----------|
| 1 | A1_G | 1 | adversarial_asymmetric | heilbron_adversarial/pop_a | http://10.232.30.185:4000/v1 | Composition: Constructor, pair 1 |
| 2 | A1_D | 2 | adversarial_asymmetric | heilbron_adversarial/pop_b | http://10.232.30.185:4000/v1 | Composition: Improver, pair 1 |
| 3 | A2_G | 3 | adversarial_asymmetric | heilbron_adversarial/pop_a | http://10.232.30.185:4000/v1 | Composition: Constructor, pair 2 |
| 4 | A2_D | 4 | adversarial_asymmetric | heilbron_adversarial/pop_b | http://10.232.30.185:4000/v1 | Composition: Improver, pair 2 |
| 5 | C1_G | 5 | adversarial_asymmetric | heilbron_adversarial/pop_a | http://10.232.30.185:4000/v1 | Gradient: Constructor, pair 1 |
| 6 | C1_D | 6 | adversarial_asymmetric | heilbron_adversarial/pop_b | http://10.232.30.185:4000/v1 | Gradient: Improver, pair 1 |
| 7 | C2_G | 7 | adversarial_asymmetric | heilbron_adversarial/pop_a | http://10.232.30.185:4000/v1 | Gradient: Constructor, pair 2 |
| 8 | C2_D | 8 | adversarial_asymmetric | heilbron_adversarial/pop_b | http://10.232.30.185:4000/v1 | Gradient: Improver, pair 2 |

---

## Controlled Variables

| Field | Value |
|-------|-------|
| max_generations | 50 |
| max_mutations_per_generation | 8 |
| max_elites_per_generation | 8 |
| mutation_mode | rewrite |
| model_name | Qwen3-235B-A22B-Thinking-2507 |
| archive_reeval | false |
| inner_iterations | 1 |
| engine | steady_state |
| num_parents | 1 |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

This is a replication of heilbron/asymmetric-iterations (PR #204) with infrastructure bug fixes (KF-01 through KF-06). Same design, same config, same model. New Redis DBs, new branch, new data.

Known sources of non-determinism:
- LLM sampling temperature and nucleus sampling in mutation LLM
- Non-deterministic GPU floating point
- Steady-state engine: concurrent batch processing order

---

## Success Criteria

Per pre-registered effect-size thresholds (01_design.md Section 2):
- STRONG POSITIVE: Constructor actual_fitness >= 0.03649
- POSITIVE: >= 0.03449
- NULL: within 0.001 of baseline
- NEGATIVE: < 0.03249

Key v2-specific success criterion: **all runs reach max_gen=50** (v1 reached only 8-12 due to sync bug).

---

## Monitoring Plan

`max_generations`: 50

- Gen 5 (~10%): smoke check -- all PIDs alive, G/D sync within 1 gen, Redis keys growing
- Gen 10 (~20%): first checkpoint -- fitness values, invalidity rates
- Gen 25 (~50%): midpoint checkpoint -- futility check (stop arm if both replicates < 0.03000)
- Gen 50 (100%): final evaluation + analysis

Early termination rule: futility_at_gen25(both_replicates_of_arm < 0.03000)

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|

Watchdog PID:
Launch commit: `<hash>`

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|

---

## Amendments

_(None -- this is a clean replication.)_
