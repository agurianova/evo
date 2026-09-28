# Experimental Design: Heilbronn Baseline Reproducibility (N=4 Replication)

**Date**: 2026-04-10
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft -- awaiting Reviewer-2

---

## 1. Research Question

The adversarial co-evolution research program has produced 4 experiments on the Heilbronn triangle problem, all referencing the heilbron-prover baseline of mean actual_fitness = 0.03464 (PR #183, N=2 pairs: P1_A=0.03380, P2_A=0.03548). However, the most recent experiment (adversarial-dynamic-updates, PR #197) found **all 4 cells below this baseline** -- even control cells with no mechanism changes scored 0.03020-0.03186. This raises a critical question: is the 0.03464 baseline stable, or was it an outlier from a high-variance process measured with only N=2?

This experiment is a **same-config, current-codebase replication** of heilbron-prover with N=4 pairs (up from N=2). The codebase has evolved since heilbron-prover's launch commit (`694a6ca9`, 2026-04-06) -- including MetricsTracker refactoring, adversarial pipeline bug fixes, and memory system changes. We accept codebase drift as a known confound: the purpose is to establish the reproducible distribution of Constructor actual_fitness under the original *configuration*, not to reproduce the exact binary. Any behavioral change in core components would itself be a valuable finding.

**Primary research question**: What is the reproducible mean and standard deviation of Constructor actual_fitness (raw min_area) at gen 50 under the original heilbron-prover conditions?

**Secondary questions**:
1. Is the original 0.03464 mean within the 95% CI of the N=4 replication?
2. What is the between-pair variance (sigma) of actual_fitness? This determines the minimum detectable effect for future experiments.
3. Do all 4 pairs exhibit the same qualitative dynamics (Constructor dominance, Improver stagnation, 100% resistance)?

---

## 2. Hypotheses

This is a **replication study**, not a hypothesis test. There is no treatment. The primary output is a **descriptive statistic** (mean and 95% CI of actual_fitness at gen 50).

However, for protocol compliance, we state a minimal hypothesis:

**H0**: The heilbron-prover result was an outlier. The true mean Constructor actual_fitness at gen 50 is <= 0.030 (below the worst adversarial-dynamic-updates control cell).

**H1**: The heilbron-prover result is reproducible. The mean Constructor actual_fitness at gen 50 is >= 0.033 (within 0.002 of the original 0.03464 mean).

### Effect-size thresholds

| Mean actual_fitness (N=4) | Interpretation |
|---------------------------|----------------|
| >= 0.035 | **CONFIRMED HIGH** -- baseline is robust, above-average replication |
| 0.033 - 0.035 | **CONFIRMED** -- baseline is reproducible |
| 0.030 - 0.033 | **REVISED** -- true baseline is lower than originally estimated |
| < 0.030 | **UNRELIABLE** -- original baseline was an outlier; all prior comparisons need revision |

---

## 3. Independent Variable(s)

| Variable | Values | Notes |
|----------|--------|-------|
| Pair identity | 1, 2, 3, 4 | Random effect, not a treatment IV |

**This is a single-condition replication.** There is no treatment/control distinction. All 4 pairs run identical configurations.

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Constructor actual_fitness (raw min_area) | `lindex {prefix}:metrics:history:program_metrics:valid_frontier_actual_fitness -1` | **Yes** |
| Constructor frontier fitness (adversarial) | `lindex {prefix}:metrics:history:program_metrics:valid_frontier_fitness -1` | Secondary |
| Constructor resistance | Computed from adversarial fitness components | Secondary |
| Improver frontier fitness | Same key pattern on pop_b prefix | Secondary |
| Constructor invalidity rate | programs_invalid_count / programs_total_count | Diagnostic |
| Between-pair standard deviation | SD of 4 actual_fitness values | **Key output** |

**Primary metric**: Constructor actual_fitness at gen 50, averaged across 4 pairs. The 95% CI is computed as mean +/- t(0.025, df=3) * SE.

---

## 5. Controlled Variables

All variables are controlled at heilbron-prover values. No deviations permitted.

| Field | Value | Rationale |
|-------|-------|-----------|
| problem.name | heilbron_adversarial/pop_a, pop_b | Exact replication |
| pipeline | adversarial_coevo | Exact replication |
| evolution engine | generational (default EvolutionEngine) | Exact replication (NOT steady-state) |
| max_generations | 50 | Match heilbron-prover |
| num_parents | 1 | Match heilbron-prover |
| max_elites_per_generation | 8 | Match heilbron-prover |
| max_mutations_per_generation | 8 | Match heilbron-prover |
| stage_timeout | 3000 | Match heilbron-prover |
| dag_timeout | 7200 | Match heilbron-prover |
| per_opponent_timeout | 300 | Match heilbron-prover |
| mutation_mode | rewrite | Match heilbron-prover |
| significant_change | 0.01 | Match heilbron-prover |
| mutation LLM | Qwen3-235B-A22B-Thinking via LiteLLM proxy (10.232.30.185:4000/v1) | Match heilbron-prover |
| opponent feedback K | 0 (score only, no code blocks) | Match heilbron-prover |
| custom_env.OPENAI_API_KEY | sk-gigaevo | Match heilbron-prover |
| pre_step_hook | `gigaevo.prompts.coevolution.sync.MainRunSyncHook` | Match heilbron-prover (NOT ProgressBasedSyncHook) |

**Critical**: No opponent code feedback (K=0), no archive re-evaluation, no soft/GAN fitness variants, and MainRunSyncHook (NOT ProgressBasedSyncHook). These additions/changes were introduced in later experiments.

---

## 6. Run Design Table

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

**All runs use identical configs.** The only difference is Redis DB assignments and opponent pairing.

---

## 7. Sample Size Justification

N=4 pairs is the minimum to compute a meaningful 95% CI with t-distribution (df=3). From heilbron-prover, the within-pair range was 0.00168 (P1_A=0.03380, P2_A=0.03548). Assuming sigma ~ 0.001, the standard error with N=4 would be 0.0005, giving a 95% CI half-width of ~0.0016. This is sufficient to distinguish between the interpretations in Section 2 (bins are 0.002-0.005 wide).

N=4 also provides enough replicates to estimate sigma itself, which is a primary output of this experiment. Prior experiments (all N=1-2) could not estimate between-pair variance.

---

## 8. Statistical Test

**Primary analysis**: Descriptive -- compute mean, SD, and 95% CI of Constructor actual_fitness across 4 pairs at gen 50.

**Secondary test (for protocol compliance)**:
- **Test**: One-sample t-test, H0: mu <= 0.030 vs H1: mu > 0.030
- **Significance threshold**: alpha = 0.10 (one-tailed; lenient because this is a replication, not a treatment test)
- **How computed**: t = (mean - 0.030) / (SD / sqrt(4)), df=3, critical t = 1.638

**Interpretive framework**: The 95% CI is the primary output. If 0.03464 falls within the CI, the baseline is confirmed. If 0.03464 falls above the CI upper bound, the baseline was high.

---

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| Mutation LLM version drift | LiteLLM proxy may route to different backend versions than heilbron-prover | Capture server_models_at_launch.txt; compare to heilbron-prover's record |
| Non-stationary opponent fitness | Same as all adversarial experiments | Use actual_fitness (opponent-independent) as primary metric |
| Initial seed stochasticity | Different initial programs lead to different trajectories | N=4 pairs specifically to measure this variance |
| Redis DB contention | 8 concurrent DBs on same Redis instance | Prior experiments showed no contention issues at 8 DBs |
| LLM server load | 8 concurrent mutation requests vs 4 in heilbron-prover | Monitor mutation latency; note if > 2x heilbron-prover |

---

## 10. Stop Criteria

**Stopping rule**: `max_generations=50`

All 8 runs proceed to gen 50. No early termination.

**Run invalidation criteria**:
- Constructor invalidity > 75% at gen 10+ (indicates problem variant bug)
- Generation gap > 10 within a pair (indicates dead process or sync failure)
- Redis DB corruption (missing run_state keys)

If a run is invalidated, restart the entire pair (both A and B). Do not restart individual runs.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time | ~48h (8 runs x 50 gen, ~6 gen/h per run) |
| Redis DBs | 8 (DBs 1-8) |
| Concurrent processes | 8 (4 pairs, each with 2 processes) |

---

## 12. Treatment Verification

This is a replication study -- there is no treatment to verify. Instead, verify **replication fidelity**:

1. **Config parity**: All 8 runs must produce identical `--cfg job` output (modulo redis.db and opponent settings).
2. **Server model identity**: `server_models_at_launch.txt` must show Qwen3-235B-A22B-Thinking (same as heilbron-prover).
3. **Engine type**: Must be generational EvolutionEngine, NOT steady-state. Verify: `evolution._target_` = `gigaevo.evolution.engine.engine.EvolutionEngine`.
4. **No opponent code feedback**: No `OpponentFeedbackStage` in pipeline. Confirm absence in cfg dump.
5. **Archive re-evaluation OFF**: No `ArchiveReEvalStage` in pipeline. Confirm absence in cfg dump.

---

## 13. Open Questions / Risks

1. **If the baseline is NOT reproducible** (mean < 0.030): All prior comparative claims need reinterpretation.
2. **If high variance** (SD > 0.005): Future experiments need N >= 6 for 0.002 effects.
3. **If baseline is higher than expected** (mean > 0.036): Suggests adversarial-dynamic-updates controls were degraded by some mechanism.
