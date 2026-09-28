# Pre-Registration: heilbron/baseline-repro

**Date**: 2026-04-10
**Protocol version**: 1.0
**Pre-registration commit**: `08837375` -- commit this file BEFORE any code changes
**GitHub PR**: #201 (branch: `exp/heilbron/baseline-repro`)
**Tracking issue**: N/A
**Design doc**: `experiments/heilbron/baseline-repro/01_design.md`
**Review doc**: `experiments/heilbron/baseline-repro/02_review.md` (verdict: APPROVED)
**Evaluation script**: N/A (no test set -- optimization problem)

---

## Hypothesis

**H0**: The true mean Constructor actual_fitness at gen 50 is <= 0.030
**H1**: The mean Constructor actual_fitness at gen 50 is >= 0.033
**Primary metric**: Constructor actual_fitness (raw min_area) at gen 50, mean of 4 pairs
**Significance threshold**: alpha = 0.10 (one-tailed t-test, H0: mu <= 0.030)

**Interpretive bins**:
- >= 0.035: CONFIRMED HIGH
- 0.033-0.035: CONFIRMED
- 0.030-0.033: REVISED
- < 0.030: UNRELIABLE

---

## Run Design Table

| Run | Label | redis.db | pipeline | problem.name | opponent_redis_db | opponent_redis_prefix |
|-----|-------|----------|----------|-------------|-------------------|----------------------|
| 1 | P1_A | 1 | adversarial_coevo | heilbron_adversarial/pop_a | 2 | heilbron_adversarial/pop_b |
| 2 | P1_B | 2 | adversarial_coevo | heilbron_adversarial/pop_b | 1 | heilbron_adversarial/pop_a |
| 3 | P2_A | 3 | adversarial_coevo | heilbron_adversarial/pop_a | 4 | heilbron_adversarial/pop_b |
| 4 | P2_B | 4 | adversarial_coevo | heilbron_adversarial/pop_b | 3 | heilbron_adversarial/pop_a |
| 5 | P3_A | 5 | adversarial_coevo | heilbron_adversarial/pop_a | 6 | heilbron_adversarial/pop_b |
| 6 | P3_B | 6 | adversarial_coevo | heilbron_adversarial/pop_b | 5 | heilbron_adversarial/pop_a |
| 7 | P4_A | 7 | adversarial_coevo | heilbron_adversarial/pop_a | 8 | heilbron_adversarial/pop_b |
| 8 | P4_B | 8 | adversarial_coevo | heilbron_adversarial/pop_b | 7 | heilbron_adversarial/pop_a |

All runs use identical configurations. Mutation via LiteLLM proxy at `http://10.232.30.185:4000/v1`.

---

## Controlled Variables

| Field | Value |
|-------|-------|
| pipeline | adversarial_coevo |
| evolution engine | generational (EvolutionEngine) |
| max_generations | 50 |
| num_parents | 1 |
| max_elites_per_generation | 8 |
| max_mutations_per_generation | 8 |
| stage_timeout | 3000 |
| dag_timeout | 7200 |
| per_opponent_timeout | 300 |
| mutation_mode | rewrite |
| significant_change | 0.01 |
| pre_step_hook | MainRunSyncHook |
| opponent feedback K | 0 (no code blocks) |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

This is a **same-config, current-codebase replication** of adversarial/heilbron-prover. The codebase has evolved since the original launch commit (`694a6ca9`, 2026-04-06). Codebase drift is an accepted confound -- the purpose is to measure the distribution of actual_fitness under the original configuration on the current codebase.

Known sources of non-determinism:
- LLM sampling temperature in mutation operator
- `random.sample` in initial program generation
- Opponent archive composition (varies per pair due to co-evolution)

**Global seed**: N/A (not supported for adversarial co-evolution)

---

## Dataset Checksums

See `dataset_snapshot.json` for full file-level SHA-256 checksums.

**Data commit**: `ea30e341` (HEAD of `problems/heilbron_adversarial/` at pre-registration)
**Files checked**: 27 files in `problems/heilbron_adversarial/`

---

## Success Criteria

The experiment succeeds if all 4 Constructor runs (P1_A-P4_A) reach gen 50 and produce valid actual_fitness values. The primary output is descriptive: mean, SD, and 95% CI.

---

## Monitoring Plan

`max_generations`: 50

- Gen 5 (~10%): smoke check -- all 8 PIDs alive, Redis keys growing, opponent archives populated
- Gen 10 (~20%): first checkpoint -- verify invalidity < 50%, generation parity within pairs
- Gen 25 (~50%): midpoint checkpoint -- record actual_fitness trajectory
- Gen 50 (100%): final evaluation + analysis

**Early termination rule**: None. All runs proceed to gen 50.
**Run invalidation**: Constructor invalidity > 75% at gen 10+, or generation gap > 10 within pair.

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

_(Add numbered entries here for any post-registration changes.)_
