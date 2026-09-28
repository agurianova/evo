# Experimental Design: Reproducibility Stress Test of v1's 0.0365 Result Under Current Library

**Date**: 2026-04-19
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Revision 1 -- addressing Reviewer-2 verdict (NEEDS REVISION -- MAJOR)

---

## 1. Research Question

Does replicating v1's hyperparameters + frozen v1 fitness function + drift_cap=100000 (preserving the natural D>G ~2.2x compute asymmetry) under the current bug-fixed library reproduce the 0.0365 actual_fitness result -- or does the absence of v1's process-death bugs (which truncated runs at gen 8-29) change the outcome by letting runs reach gen 50?

**Context**: heilbron/asymmetric-iterations (v1, PR #204) produced GigaEvo's all-time best Heilbronn N=11 result: actual_fitness 0.03648 and 0.03650, both at gen 4-8 on the Constructor side. These were accidental products of three interacting conditions: (1) min_delta=1 creating loose G/D coupling where D ran ~2.2x faster than G, (2) K=1 inner iterations (the design specified K=5 but the loop was never implemented), and (3) six infrastructure bugs (KF-01 through KF-06) that killed all runs before gen 12. The subsequent v2 replication (PR #206) fixed all six bugs but also tightened min_delta from 1 to 8, yielding INCONCLUSIVE results (best 0.03588, mean NULL vs baseline). The most parsimonious explanation for v2's failure: the min_delta tightening, not the bug fixes, degraded performance.

This experiment directly tests that hypothesis by restoring min_delta=1 semantics via drift_cap=100000 under the current bug-fixed library. It is a calibration experiment -- the 0.0365 target has already been exceeded by AlphaEvolve (May 2025) and approached by FlowBoost (Jan 2026). The value is internal: can we reproduce our own prior result deliberately?

---

## 2. Hypotheses

**H0**: Under current library with v1 hyperparameters + frozen v1 fitness + drift_cap=100000, mean best-ever actual_fitness across 4 G runs is not meaningfully higher than v2's G mean (~0.0343) or baseline-repro's mean (0.03449).

**H1**: The restored loose coupling (drift_cap=100000) recovers v1-level performance: mean best-ever actual_fitness across 4 G runs >= 0.03574 (v1's grand mean across 4 G runs), with at least 1/4 G runs reaching actual_fitness >= 0.0365.

### Effect-size thresholds

| Outcome (mean best-ever actual_fitness across 4 G runs) | Verdict |
|---|---|
| >= 0.0360 and >= 1/4 G runs at 0.0365 | **POSITIVE** -- v1 reproduced; loose coupling confirmed as active mechanism |
| >= 0.03449 (baseline parity) and < 0.0360 | **SUGGESTIVE** -- loose coupling helps directionally but does not fully recover v1 |
| within 0.001 of v2 mean (0.0334-0.0354) | **NULL** -- loose coupling insufficient; library drift or longer runs are the culprit |
| < 0.0330 | **NEGATIVE** -- active regression under loose coupling |

### Failure criteria (abandon direction)

If mean best-ever actual_fitness across 4 G runs < 0.0340 (below v2 and baseline), loose coupling under the current library is actively harmful, and the v1 result was an unreproducible stochastic event. In that case, the REDESIGN bundle (smoothed tanh fitness) becomes the sole viable path forward.

---

## 3. Independent Variable(s)

This is a **reproducibility study**, not a factorial experiment. There is no within-experiment IV. The treatment is the composite v1 recipe (frozen v1 fitness + drift_cap=100000 + K=1 + n_opponents=1 + source_prompt_k=1) restored under the current library. The comparison is against historical results:

| Comparator | Mean actual_fitness | Best actual_fitness | Source |
|---|---|---|---|
| v1 (asymmetric-iterations, PR #204) | 0.03574 (grand mean, 4 G runs) | 0.03650 (C2_G, gen 5) | Same design, min_delta=1 accidental, runs died gen 8-12 |
| v2 (asymmetric-iterations-v2, PR #206) | ~0.03383 (G mean both arms) | 0.03588 (C1_G, gen 22) | Same design, min_delta=8 (tight coupling), reached gen 34-50 |
| baseline-repro (PR #201) | 0.03449 (best-overall, N=4) | 0.03610 (P1_B) | Solo adversarial MAP-Elites, no asymmetric mechanism |

The two arms (Composition and Gradient-in-prompt) are retained from v1 for exact structural replication. Feedback mode is definitively NULL (HIGH confidence, PATTERNS.md: 8 pairs, 16 runs, two experiments, cross-arm deltas 0.00066-0.00081). The arms serve as an internal consistency check: if one arm dramatically outperforms the other, something is wrong with the design, not the mechanism.

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| actual_fitness (G) | Raw min_area from Constructor; `program.metrics["actual_fitness"]` in Redis | **Yes** |
| G fitness (composite) | ALPHA * quality + (1-ALPHA) * resistance; hard-floor; stored in Redis | Secondary |
| G resistance | Binary: float(delta <= 0) averaged over opponents; bimodal {0, 1} at n_opponents=1 | Secondary |
| D fitness | min(max(delta, 0) / Q_MAX, 1.0); hard-floor; 60-90% at 0.0 expected | Secondary (D-collapse monitor) |
| programs_processed (G, D) | `engine:programs_processed` in Redis | Secondary (compute ratio) |
| D/G generation ratio | D total_generations / G total_generations at experiment end | Secondary (target ~2.2x) |
| best_fitness_by_gen_12 | Best actual_fitness at or before G gen 12 | Diagnostic (early-gen vs late-gen split) |

**Primary metric**: actual_fitness from Constructor (G) runs, reported as best-ever per run (not final-gen fitness, since v1's peaks appeared gen 4-8).

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| `pipeline` | `heilbron_repro_v1` | Layer-3 config freezing drift_cap, inner_iterations, n_opponents, source_prompt_k |
| `problem.name` | `heilbron_repro_v1/pop_a` (G), `heilbron_repro_v1/pop_b` (D) | Frozen at v1 commit; hard-floor evaluate.py |
| `evolution` | `steady_state` | Matches v1's actual operating mode (KF-01 amendment from generational to steady-state) |
| `drift_cap` | 100000 | No-op sync hook -- emulates v1's unthrottled behavior |
| `inner_iterations` | 1 | v1's actual K (design said K=5 but never implemented; config-only no-op) |
| `n_opponents` | 1 | v1 setting; each program evaluated against exactly 1 opponent |
| `source_prompt_k` | 1 | D sees exactly 1 G source code (best by fitness) |
| `sync_every_n_epochs` | 1 | Hook polls every epoch |
| `max_generations` | 50 | Hard stop; v1 died gen 8-29 due to bugs; this gives full horizon |
| `max_mutations_per_generation` | 8 | Match v1 and all prior heilbron experiments |
| `max_elites_per_generation` | 8 | Match v1 |
| `mutation_mode` | rewrite | Match v1 |
| `model_name` | Qwen3-235B-A22B-Thinking-2507 | Same mutation LLM as v1 and v2 |
| `llm_base_url` | http://10.232.30.185:4000/v1 | LiteLLM proxy |
| `temperature` | 0.6 | Match v1 |
| `max_tokens` | 81920 | Match v1 |
| `island_max_size` | 75 | Match v1 |
| `primary_resolution` | 150 | Match v1 |
| `num_parents` | 1 | Independent mutation, no crossover |
| `stage_timeout` | 3000 | Match v1 |
| `dag_timeout` | 7200 | Match v1 |
| `archive_reeval` | false | Match v1 (which used false). Independently confirmed NEGATIVE in adversarial-dynamic-updates |
| `stopper` | `max_generations` | MaxGenerationsStopper(50); runs terminate at gen 50 |

---

## 6. Run Design Table

### Arm A: Composition -- 2 G/D pairs (4 runs)

| Run | Label | `redis.db` | Role | `feedback_mode` | `opponent_redis_db` | `opponent_redis_prefix` |
|-----|-------|------------|------|-----------------|---------------------|------------------------|
| 1 | A1_G | 1 | Constructor (G) | composition | 2 | heilbron/adversarial-repro-v1/pop_b |
| 2 | A1_D | 2 | Improver (D) | composition | 1 | heilbron/adversarial-repro-v1/pop_a |
| 3 | A2_G | 3 | Constructor (G) | composition | 4 | heilbron/adversarial-repro-v1/pop_b |
| 4 | A2_D | 4 | Improver (D) | composition | 3 | heilbron/adversarial-repro-v1/pop_a |

### Arm C: Gradient-in-prompt -- 2 G/D pairs (4 runs)

| Run | Label | `redis.db` | Role | `feedback_mode` | `opponent_redis_db` | `opponent_redis_prefix` |
|-----|-------|------------|------|-----------------|---------------------|------------------------|
| 5 | C1_G | 5 | Constructor (G) | gradient_in_prompt | 6 | heilbron/adversarial-repro-v1/pop_b |
| 6 | C1_D | 6 | Improver (D) | gradient_in_prompt | 5 | heilbron/adversarial-repro-v1/pop_a |
| 7 | C2_G | 7 | Constructor (G) | gradient_in_prompt | 8 | heilbron/adversarial-repro-v1/pop_b |
| 8 | C2_D | 8 | Improver (D) | gradient_in_prompt | 7 | heilbron/adversarial-repro-v1/pop_a |

**Total**: 8 runs (4 Constructors + 4 Improvers), 8 Redis DBs (1-8), 4 co-evolving pairs, 2 arms. Arm labels A and C are retained from v1 for exact structural replication. No Arm B exists in this design.

This is structurally identical to v1 and v2. The only difference from v2: `pipeline=heilbron_repro_v1` (which sets drift_cap=100000 instead of inheriting min_delta=8 from adversarial_asymmetric). The only difference from v1: bug fixes KF-01 through KF-06 are present in the library, so runs will reach max_generations=50 instead of dying at gen 8-29.

---

## 7. Sample Size Justification

N=4 runs per arm (8 total: 4 G + 4 D), matching v1's exact structure. The primary DV (best-ever actual_fitness) is measured on **4 G runs only** (A1_G, A2_G, C1_G, C2_G). The 4 D runs co-exist as paired co-evolutionary partners and contribute secondary metrics (D fitness, D-collapse rate, compute ratio) but are not pooled with G for the primary comparison.

From baseline-repro (N=4): SD(actual_fitness) = 0.00212. With N=4 G runs pooled across arms (since feedback mode is NULL at HIGH confidence), a one-sample comparison against v1's historical mean can detect effects of approximately 0.003 (1.4 SD) with ~50% power. This is a meaningful loss of power compared to an N=8 design -- we acknowledge that effects smaller than 0.003 may be undetectable.

**With N=4 G runs, this experiment measures effect magnitude and consistency. Formal statistical testing would require N >= 8-12 G runs.** The primary inference is not a p-value but a comparison of distributions: does repro-v1's mean actual_fitness land closer to v1 (0.03574) or to v2 (0.03383)?

The 1/4 G-run success threshold at 0.0365 is a secondary calibration. v1 observed 2/4 G runs at or above 0.0365. Under a Bernoulli(2/4) model, the probability of seeing at least 1/4 successes is ~94%. Under Bernoulli(0/4) (v2's rate), it is 0%. A single G-run success at 0.0365 does not prove the mechanism works, but zero successes combined with a mean near v2 would argue against it.

---

## 8. Statistical Test

**Primary**: Descriptive comparison of mean best-ever actual_fitness across 4 G runs (A1_G, A2_G, C1_G, C2_G) against v1 grand mean (0.03574 over 4 G runs), v2 G mean (~0.03383 over 4 G runs), and baseline-repro mean (0.03449). No p-values -- the comparison is against historical reference points, not a concurrent control. D runs contribute secondary metrics only and are not pooled with G for the primary comparison.

**Per-arm breakdown**: Mean actual_fitness for Composition (2 G runs: A1_G, A2_G) and Gradient-in-prompt (2 G runs: C1_G, C2_G). This is NOT a hypothesis test -- feedback mode is definitively NULL (PATTERNS.md, HIGH confidence). Any large discrepancy (> 0.002) between arms warrants investigation as a design error, not a treatment effect.

**Diagnostic split** (pre-registered): Report (a) best_fitness_by_gen_12 (matching v1's termination window) and (b) best_fitness_by_gen_50 (full run). If (a) matches v1 but (b) does not, the longer run past v1's productive window is the culprit -- D-collapse pathology wins after G peaks early. If neither (a) nor (b) matches v1, library drift or model proxy drift is the culprit.

**D-collapse monitoring**: At gen 10, 20, 30, 40, 50, report fraction of D population with fitness=0.0. Expected: 60-90% point mass at 0.0 (hard-floor collapse, structurally identical to v1). Do NOT treat this as a bug or invalidation criterion. It is the designed behavior of v1's hard-floor fitness.

**Compute ratio**: Observed D_gen / G_gen ratio at experiment end. Expected: D ~2.2x G (v1 observed A1: D=27/G=12=2.25x, A2: D=29/G=12=2.42x, C1: D=17/G=8=2.13x, C2: D=19/G=9=2.11x). If the ratio is ~1:1, drift_cap=100000 is not producing the intended asymmetry, and the treatment is not applied.

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Library drift since v1 commit 04bd5e69** | HIGH | Pipeline builders, injection hooks, and steady-state engine have evolved. Only hyperparameters and problem files are frozen. Cannot be eliminated -- this is one of three residual gaps. The diagnostic split (gen 12 vs gen 50) helps localize: if early-gen behavior differs from v1, library drift is implicated. |
| 2 | **Longer runs (gen 50 vs gen 8-29)** | HIGH | v1's process-death bugs (KF-01 through KF-06) are fixed. Runs will reach gen 50 for the first time. If v1's success depended on catching peaks before D-collapse pathology, the longer horizon may expose regression. Pre-register best_fitness_ever as the metric (not final_fitness) to handle the case where fitness peaks early then decays. |
| 3 | **Model proxy defaults may differ** | MEDIUM | Same model family (Qwen3-235B-A22B-Thinking-2507) and same proxy endpoint. But proxy-level defaults (token budget, system prompt framing, quantization) may have drifted since v1. Cannot be controlled without exact proxy version pinning. Acknowledged as uncontrollable residual gap. |
| 4 | **Stochastic resampling from same distribution** | MEDIUM | v1's 2/4 G-run success rate at 0.0365 is compatible with both a genuine mechanism and random chance. Under Bernoulli(2/4), seeing at least 1/4 G-run successes in repro-v1 is ~94% probable even without the mechanism. Primary analysis uses mean actual_fitness across 4 G runs, not single-run hits. |
| 5 | **No concurrent control arm** | LOW | Adding a tight-coupling control (min_delta=8) would double cost to 16 runs for minimal information gain -- v2's 8 runs at min_delta=8 already provide the control data. The comparison is cross-experiment, acknowledged as weaker than concurrent. |
| 6 | **Feedback mode NULL but included** | LOW | Both arms included for exact v1 replication and internal consistency. Any cross-arm discrepancy > 0.002 is a red flag for design error, not treatment effect. |
| 7 | **D-collapse pathology present by design** | LOW | Hard-floor fitness produces 60-90% D point mass at 0.0. This is identical to v1. Not a confound -- it is the operating condition under which v1 produced 0.0365. Monitor but do not prevent. |

---

## 10. Stop Criteria

**Per-run stopping**: `stopper=max_generations` with `max_generations=50`. Stop when any run reaches generation 50.

```
stopper=max_generations max_generations=50
```

**Experiment-level stopping**: All 8 runs must reach max_generations=50. Report results only after all 8 runs complete.

**Run invalidation criteria** (any one triggers exclusion from primary analysis):

- PID death before gen 5 with no restart within 2 hours
- Redis corruption or key collision between runs (cross-DB contamination)
- wrong `pipeline` or `problem.name` resolved (verified via `--cfg job` pre-launch)
- drift_cap not logged as 100000 at startup (treatment not applied)
- population_role wrong (G running as improver or vice versa)

**Minimum completion**: At least 3/4 G runs must reach gen 25 for the experiment to be analyzable. If fewer than 3 G runs reach gen 25, report as INVALID.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| GPU hours (LLM inference) | ~80h (8 runs x ~10h each; no K=5 inner iterations -- D at K=1 is cheap) |
| Wall time | ~20-24h (all 8 runs concurrent on shared proxy; D runs ~2x faster than G) |
| Redis DBs used | 8 (DBs 1-8) |
| LLM calls (total) | ~6,400 (8 runs x ~50 gens x ~8 mutations + evaluations per gen; G slower than D) |

**Cost comparison**: v1 ran ~15h before all processes died. v2 ran ~48h with timeouts adjusted. This experiment is lighter than v2 because K=1 (no inner iteration overhead) and D evaluation is cheap (single opponent).

---

## 12. Treatment Verification

This section specifies the observable evidence required to confirm that the v1 recipe is actually applied and active in each run. These checks MUST pass before the experiment is considered validly launched.

### 12.1 Startup verification (all 8 runs)

| Check | Observable evidence | Tool |
|-------|-------------------|------|
| drift_cap=100000 | Log line: `[ProgressBasedSyncHook] Init \| own=db=N prefix='...' ... drift_cap=100000` | Startup log, first 10 lines |
| Pipeline resolved | `--cfg job` shows `pipeline: heilbron_repro_v1` | Pre-launch config dump |
| Problem files frozen | `--cfg job` shows `problem.name: heilbron_repro_v1/pop_a` (G) or `heilbron_repro_v1/pop_b` (D) | Pre-launch config dump |
| Population role correct | Log line: `[AsymmetricPipeline] role=constructor` (G) or `role=improver` (D) | Startup log |
| Sync hook never blocks | `grep "drift_cap exceeded" run_*.log` returns 0 matches over full run | Post-run log audit |
| inner_iterations=1 | `--cfg job` shows `inner_iterations: 1` (no-op; never consumed by Python) | Pre-launch config dump |
| n_opponents=1 | `--cfg job` shows `n_opponents: 1` | Pre-launch config dump |
| source_prompt_k=1 | `--cfg job` shows `source_prompt_k: 1` | Pre-launch config dump |

### 12.2 Runtime verification (checked at gen 3+ during smoke test)

| Check | Observable evidence | Tool |
|-------|-------------------|------|
| Source code injection (D only) | Log: `[SourceCodeInjection] showing 1 programs from ...` appears for D runs | `grep "SourceCodeInjection" run_*_D.log` |
| Source code injection NOT on G | No `[SourceCodeInjection]` lines in G logs | `grep "SourceCodeInjection" run_*_G.log` returns empty |
| G fitness distribution | Redis scan: G fitness in [0.0, 1.0] continuous (quality axis + binary resistance) | `gigaevo -r "prefix@db" programs --metric fitness` |
| D fitness distribution | Redis scan: D fitness in [0.0, 1.0] with mode near 0.0 (hard-floor collapse expected) | `gigaevo -r "prefix@db" programs --metric fitness` |
| Compute asymmetry | At gen 12 (v1's G ceiling): D should be at gen ~27 +/- 3 | `gigaevo -r "prefix@db" state` for both pops |
| Arm A specific: CompositionInjection | G log shows `[CompositionInjection] mutation_type=d_improvement` after gen 2 | `grep "CompositionInjection" run_A*_G.log` |
| Arm C specific: GradientInPrompt | G log shows `[GradientInPrompt] injecting D into G prompt` after gen 2 | `grep "GradientInPrompt" run_C*_G.log` |

### 12.3 Extra overrides per run (exact strings for `python run.py`)

**All runs share:**
```
pipeline=heilbron_repro_v1
evolution=steady_state
stopper=max_generations
max_generations=50
```

**Arm A pop_a (Composition, G=Constructor):**
```
problem.name=heilbron_repro_v1/pop_a
redis.db=1
opponent_redis_db=2
opponent_redis_prefix=heilbron/adversarial-repro-v1/pop_b
feedback_mode=composition
population_role=constructor
```

**Arm A pop_b (Composition, D=Improver):**
```
problem.name=heilbron_repro_v1/pop_b
redis.db=2
opponent_redis_db=1
opponent_redis_prefix=heilbron/adversarial-repro-v1/pop_a
feedback_mode=composition
population_role=improver
d_sees_g_source=true
d_archive_persistent=true
```

**Arm C pop_a (Gradient-in-prompt, G=Constructor):**
```
problem.name=heilbron_repro_v1/pop_a
redis.db=5
opponent_redis_db=6
opponent_redis_prefix=heilbron/adversarial-repro-v1/pop_b
feedback_mode=gradient_in_prompt
population_role=constructor
```

**Arm C pop_b (Gradient-in-prompt, D=Improver):**
```
problem.name=heilbron_repro_v1/pop_b
redis.db=6
opponent_redis_db=5
opponent_redis_prefix=heilbron/adversarial-repro-v1/pop_a
feedback_mode=gradient_in_prompt
population_role=improver
d_sees_g_source=true
d_archive_persistent=true
```

**Note on `d_sees_g_source` and `d_archive_persistent`**: Per codebase map analysis, both are NO-OP config keys -- never read by any Python code. The actual source injection mechanism is `population_role=improver`, which triggers `SourceCodeInjectionStage`. These keys are included for documentation/record-keeping consistency with v1 but have zero runtime effect. Treatment verification MUST check for `[SourceCodeInjection] showing` in run logs, NOT for these config keys.

### 12.4 Pinned contract (for experiment.yaml)

```yaml
contract:
  config:
    pinned:
      drift_cap: 100000
      inner_iterations: 1
      n_opponents: 1
      source_prompt_k: 1
      max_generations: 50
      sync_every_n_epochs: 1
```

---

## 13. Pre-Registered Analysis Plan

### 13.1 Primary analysis

Mean and standard deviation of best-ever actual_fitness across all 4 G runs (A1_G, A2_G, C1_G, C2_G). Report as mean +/- stderr. Compare against:

- v1 grand mean: 0.03574 (target to match)
- v2 G mean: ~0.03383 (should exceed)
- baseline-repro mean: 0.03449 (should at least match)

Report the per-run distribution (all 4 G best-ever actual_fitness values) and whether the effect direction is consistent across runs. D runs are reported separately as secondary metrics (D fitness distribution, D-collapse rate, compute ratio).

### 13.2 Per-arm breakdown (internal consistency check)

| Arm | G Runs | Expected mean | Flag threshold |
|-----|--------|---------------|----------------|
| A (Composition) | A1_G, A2_G (N=2) | ~same as Arm C | Cross-arm delta > 0.002 flags design error |
| C (Gradient-in-prompt) | C1_G, C2_G (N=2) | ~same as Arm A | Cross-arm delta > 0.002 flags design error |

This is NOT a hypothesis test. Feedback mode is NULL at HIGH confidence. Any large discrepancy warrants investigation of configuration errors, not mechanism effects.

### 13.3 Diagnostic split (pre-registered, key analytical output)

For each G run, report:

| Window | Metric | v1 reference | Interpretation if different |
|--------|--------|--------------|---------------------------|
| Gen 1-12 | best actual_fitness at or before gen 12 | 0.03648 (A1_G gen 8), 0.03650 (C2_G gen 5) | If repro-v1 matches v1 here, the early-gen mechanism works |
| Gen 13-50 | delta from gen-12 best to gen-50 best | N/A (v1 died) | Positive delta = longer run helps; negative = D-collapse pathology wins |

This is the experiment's unique contribution: v1 never ran past gen 12. If actual_fitness peaks at gen 4-8 (matching v1) then decays or plateaus through gen 50, the early-death bug was coincidentally favorable -- it caught the peak before D-collapse degraded G's fitness. If actual_fitness continues improving past gen 12, the bug was simply harmful and masked additional gains.

### 13.4 D-collapse monitoring

At gen 10, 20, 30, 40, 50, report:

- Fraction of D population with fitness exactly 0.0 (expected: 60-90%)
- D strategy-rejection rate (rolling 10-gen window)
- D generation count (to verify ~2.2x ahead of G)

D-collapse is expected and intentional under hard-floor fitness. Do NOT treat it as invalidation. Monitor it to confirm the experiment replicates v1's operating conditions.

### 13.5 Compute ratio

At experiment end, report G_gen and D_gen for each pair:

| Pair | G_gen | D_gen | Ratio (D/G) | v1 reference |
|------|-------|-------|-------------|--------------|
| A1 | -- | -- | -- | 2.25 (27/12) |
| A2 | -- | -- | -- | 2.42 (29/12) |
| C1 | -- | -- | -- | 2.13 (17/8) |
| C2 | -- | -- | -- | 2.11 (19/9) |

Expected: D/G ratio ~2.0-2.5. If the ratio is ~1.0 (lockstep), drift_cap=100000 is not producing the intended asymmetry and the treatment has failed structurally -- report as INVALID regardless of actual_fitness.

---

## 14. KF-07 Deadlock Safety

The ProgressBasedSyncHook deadlock (KF-07, discovered in k5-budget-v3) is **structurally impossible** under drift_cap=100000. The blocking condition is `own_progress - min(opponent_progress) > drift_cap`. At drift_cap=100000, this requires processing 100,000+ programs before triggering -- far exceeding the ~400 programs in a 50-gen run (50 x 8 mutations). The hook is retained solely for correctness (it correctly tracks progress) but will never activate its blocking path.

The `timeout: 7200` parameter in the hook config provides a 2-hour fallback for any unforeseen blocking scenario, matching v1's dag_timeout.

---

## 15. Threats to Validity (pre-acknowledged for Reviewer-2)

1. **Single positive original + single failed replication = n=2 historical data points.** Any result we get has limited discriminating power. We cannot definitively attribute a positive result to "loose coupling" vs "lucky LLM sample" without a concurrent tight-coupling control arm.

2. **The comparison is cross-experiment against a drifted library.** v2's tight coupling (min_delta=8) ran on a slightly different library state than repro-v1 will. A clean head-to-head isolating ONLY min_delta is not possible retroactively.

3. **If 1/4 G runs hits 0.0365, attribution is ambiguous.** Under Bernoulli(2/4) stochastic draws from v1's observed rate, P(at least 1 success in 4 trials) ~94%. A single hit is consistent with random chance from v1's distribution. The mean across all 4 G runs is the stronger diagnostic.

4. **Stopping at gen 50 may be AFTER the natural peak.** v1's 0.0365 emerged at gen 4-8. We commit to reporting best_fitness_ever (not final_fitness) to handle the case where fitness peaks early then decays under D-collapse pressure.

5. **Novelty is limited.** AlphaEvolve (May 2025) already exceeds 0.0365 without adversarial co-evolution. This is a methodological contribution (can we reproduce our own prior result?), not a SOTA claim.

6. **This experiment is "off-spine" relative to the main research program.** Per RESEARCH_STRATEGY.md, the top priority is the REDESIGN bundle (smoothed tanh fitness). repro-v1 is a calibration hedge for the NeurIPS deadline -- it runs in parallel with REDESIGN preparation and consumes only 8 Redis DBs for ~24h. A positive result strengthens the "loose coupling" narrative; a negative result adds urgency to the REDESIGN bundle.

7. **D-collapse is present by design.** v1's hard-floor fitness produces the same 60-90% point mass at D fitness=0.0 that was identified as a structural defect in k5-budget-loose. We deliberately preserve this defect because the research question is whether v1's result reproduces under v1's operating conditions, not whether v1's operating conditions are optimal.

---

## 16. Open Questions / Risks

1. **If early-gen behavior matches v1 but late-gen regresses, what have we learned?** That v1's process-death bug was coincidentally beneficial -- it caught the peak before D-collapse degraded performance. This would be a genuine finding: it means the v1 result is unreproducible under healthy infrastructure, and the REDESIGN bundle (which addresses D-collapse) is the correct path forward.

2. **If early-gen behavior does NOT match v1, what have we learned?** That library drift or model proxy drift has changed the search dynamics enough to prevent reproduction even under identical hyperparameters and fitness functions. This narrows the culprit to code changes between commit 04bd5e69 and HEAD in `gigaevo/programs/stages/`, `gigaevo/adversarial/`, and `gigaevo/engine/`.

3. **Can we isolate which library changes matter?** Not from this experiment alone. A targeted follow-up would checkout the library at 04bd5e69 and run the same config -- but that is a separate experiment (bisection) beyond the scope of repro-v1.

4. **No early-termination.** With `stopper=max_generations` only, runs that converge early will exhaust remaining compute through gen 50. This is acceptable: the gen-12 vs gen-50 diagnostic split (Section 13.3) is the experiment's key analytical contribution, so running to gen 50 is scientifically necessary even if fitness plateaus early.

---

*Ready for Reviewer-2's scrutiny.*
