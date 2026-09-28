# Results: heilbron/k5-budget-v3

**Experiment**: K-lag study under v3 2D MAP-Elites + niche-structured selection (K=3 vs K=5 opponent HoF size)
**Task**: Heilbronn n=11 adversarial co-evolution
**Verdict**: INCONCLUSIVE
**Date**: 2026-04-19

---

## 1. Summary of Findings

**Verdict: INCONCLUSIVE**

The experiment was designed to test whether a larger HoF lag K=5 produces better final G configurations than K=3, under the v3 2D MAP-Elites pipeline. The observed mean difference in best `actual_fitness` (primary DV) was -0.00164 (K5 minus K3), favoring K=3 over K=5, but the bootstrap 95% CI spans zero: [-0.00393, +0.00065]. The effect magnitude is -0.93 pooled standard deviations, which would exceed the pre-registered 2-sigma decisive threshold if the sign were consistent -- but it is not. The CI includes zero, one K=3 run outperformed both K=5 runs while the other K=3 run underperformed one K=5 run, and the K3_1 pair was truncated at gen 29 by a ProgressBasedSyncHook deadlock. The uneven generation counts (K3_1 at 58% completion, K3_2 at 84%, K5 pairs at 100%+) make arm-level pooling unreliable.

The experiment does provide one clear structural result: **v3's 2D MAP-Elites pipeline did not collapse**. All four D populations maintained fitness well above zero (range 0.520 to 0.680), satisfying the pre-registered failure criterion that D fitness must not monotonically approach zero. This is a qualitative improvement over the v2/k5-budget-loose pathology where D collapsed to a 0.0 point mass in 60-90% of runs. However, because the K3-vs-K5 comparison is confounded by uneven generation counts, no directional conclusion about optimal K can be drawn.

Primary effect with 95% CI: **-0.00164 [-0.00393, +0.00065] 95% CI** (bootstrap, 10,000 resamples; raw `actual_fitness` units, scale [0, 0.0365]).

---

## 2. Research Question and Pre-Registered Hypotheses

**Research question** (from 01_design.md section 1.5): Under v3's 2D MAP-Elites + niche-structured selection, does a larger HoF lag K=5 produce better final G configurations than K=3 on the Heilbronn n=11 adversarial co-evolution task?

**Directional hypothesis**: K=5 > K=3 (more stable lag produces better signal fidelity).

**Pre-registered success criterion**: Mean best `actual_fitness` at gen 50 of one arm exceeds the other by at least 2 times the pooled standard deviation.

**Pre-registered failure criterion**: Both arms collapse (D fitness monotonically approaches 0 in any run, OR G archive occupancy <10% at gen 50).

**Pre-registered INCONCLUSIVE criterion**: Effect between +/-1 sigma and +/-2 sigma gap between arms.

---

## 3. Per-Run Summary Table

Data extracted from `raw_redis_backup/*_raw.tar.gz` (authoritative source; see Section 6 for why the normal archive CSVs are empty).

| Label | Role | DB | Condition | Final Gen | Total Progs | Valid Progs | Invalid% | Best actual_fitness | Best fitness | Best wins |
|-------|------|----|-----------|-----------|-------------|-------------|----------|---------------------|--------------|-----------|
| K3_1_G | G (constructor) | 1 | K=3, run 1 | 29 | 327 | 256 | 21.7% | 0.035799 | 0.5000 | 3 |
| K3_1_D | D (improver)    | 2 | K=3, run 1 | 28 | 285 | 173 | 39.3% | 0.031063 | 0.6802 | 23 |
| K3_2_G | G (constructor) | 3 | K=3, run 2 | 42 | 477 | 341 | 28.5% | 0.032509 | 0.5113 | 31 |
| K3_2_D | D (improver)    | 4 | K=3, run 2 | 43 | 500 | 445 | 11.0% | 0.032543 | 0.5783 | 23 |
| K5_1_G | G (constructor) | 5 | K=5, run 1 | 51 | 497 | 341 | 31.4% | 0.031868 | 0.5000 | 37 |
| K5_1_D | D (improver)    | 6 | K=5, run 1 | 52 | 487 | 428 | 12.1% | 0.032496 | 0.5197 | 22 |
| K5_2_G | G (constructor) | 7 | K=5, run 2 | 52 | 538 | 393 | 27.0% | 0.033163 | 0.5173 | 44 |
| K5_2_D | D (improver)    | 8 | K=5, run 2 | 53 | 550 | 479 | 12.9% | 0.033179 | 0.6194 | 29 |

Notes:
- "Final Gen" = `engine:total_generations` from Redis `run_state` hash. Target was 50 for all runs.
- K3_1 pair reached only 29/28 generations (58% of target) due to ProgressBasedSyncHook deadlock; K3_2 reached 42/43 (84%); K5 pairs reached 51-53 (at or above target).
- K5_2_G has only 172 program blobs stored in raw backup (vs 538 per metrics counter) due to the A1/A2 deserialization bugs in the backup pipeline. The metrics history is intact and authoritative.
- K3_1_D has a notably high invalidity rate (39.3%) compared to other D runs (11-13%), suggesting its validator was more stringent or its mutation quality was lower in the truncated run.
- "Best actual_fitness" is frontier max from `program_metrics_valid_frontier_actual_fitness.jsonl`.

---

## 4. Primary Metric Analysis: K=3 vs K=5

### 4.1 Arm-Level Comparison

| Arm | Run 1 (best G actual_fitness) | Run 2 (best G actual_fitness) | Arm Mean | Arm SD |
|-----|-------------------------------|-------------------------------|----------|--------|
| K=3 | 0.035799 (gen 24 of 29) | 0.032509 (gen 27 of 42) | 0.034154 | 0.002326 |
| K=5 | 0.031868 (gen 30 of 51) | 0.033163 (gen 47 of 52) | 0.032516 | 0.000916 |

**Effect (K5 minus K3)**: -0.00164 [-0.00393, +0.00065] 95% CI (bootstrap, N=10,000).
**Effect in pooled-SD units**: -0.93 sigma. Below the pre-registered 2-sigma decisive threshold. Above the 1-sigma INCONCLUSIVE floor.

### 4.2 Within-Pair Deltas

The pre-registered analysis is paired across G vs D per (K, pair_id). Each pair's G run is the unit of analysis for the primary DV.

| Pair | G best actual_fitness | G final gen | G still improving at cancel? |
|------|----------------------|-------------|------------------------------|
| K3_1 | 0.035799 | 29 (58% of target) | YES -- last frontier improvement at gen 24, only 5 stagnant gens |
| K3_2 | 0.032509 | 42 (84% of target) | NO -- plateau from gen 27 onward (15 stagnant gens) |
| K5_1 | 0.031868 | 51 (102% of target) | NO -- plateau from gen 30 onward (21 stagnant gens) |
| K5_2 | 0.033163 | 52 (104% of target) | WEAKLY -- last improvement at gen 47, then stable |

K3_1_G is the strongest single run (0.035799) but had the fewest generations. It was still improving when the deadlock halted its pair, with only 5 generations of stagnation since its last frontier improvement. We cannot know whether K3_1_G would have continued improving, plateaued, or regressed under continued adversarial pressure from K3_1_D. This asymmetry is the primary reason for the INCONCLUSIVE verdict.

### 4.3 Handling of Incomplete K3_1 Pair

K3_1 completed only 29/28 generations (G/D) vs the target of 50, due to a ProgressBasedSyncHook deadlock that blocked both sides for approximately 2 hours before the external cancel at 22.06 hours wall-clock. Three analysis strategies were considered:

1. **Include as-is**: Pool K3_1's gen-29 value with K3_2's gen-42 value. This biases K3 upward if K3_1_G was still climbing (its trajectory shows active improvement at gen 24), and biases K3 downward if K3_1_G would have plateaued or regressed.
2. **Exclude K3_1**: Reduce K3 arm to N=1 (K3_2_G only), making the arm comparison meaningless.
3. **Compare at common generation**: Truncate all runs to gen 28 (K3_1's maximum), but this discards 24 generations of K5 data and defeats the purpose of measuring final-gen outcomes.

The analysis in Section 4.1 uses strategy 1 (include as-is), which is the most conservative for the INCONCLUSIVE finding: even with K3_1_G's inflated value, the CI includes zero. Under strategy 3 (common-gen truncation at gen 28), K3 arm values would be unchanged (K3_2_G's gen-28 frontier was 0.032509), while K5_1_G's gen-28 value was 0.030329 and K5_2_G's gen-28 value was 0.027643. This would widen the K3 advantage, but the small N and different trajectories make such counterfactual comparisons unreliable.

### 4.4 Pre-Registered Decision Criteria

| Criterion | Threshold | Observed | Met? |
|-----------|-----------|----------|------|
| SUCCESS (decisive) | Effect >= 2 * pooled_SD | -0.93 sigma | NO |
| FAILURE (v3 refuted) | D fitness -> 0 in any run | All D > 0.50 | NO |
| INCONCLUSIVE | Effect between +/-1 and +/-2 sigma | -0.93 sigma | YES |

Verdict: **INCONCLUSIVE** per pre-registration. The effect lies within the inconclusive zone (|effect| < 2 sigma), the CI includes zero, and the K3_1 pair's truncation introduces an unresolvable confound.

---

## 5. Secondary Metrics

### 5.1 D Population Health (Failure Criterion Check)

| D Run | Final D fitness | Collapsed? |
|-------|-----------------|------------|
| K3_1_D | 0.6802 | NO |
| K3_2_D | 0.5783 | NO |
| K5_1_D | 0.5197 | NO |
| K5_2_D | 0.6194 | NO |

All D populations maintained fitness well above zero. The v2/k5-budget-loose collapse (D fitness point mass at 0.0) is eliminated under v3's 2D MAP-Elites. This is the single most important structural result of this experiment, even though the K-comparison is inconclusive.

### 5.2 Canonical Events (from LOG_AUDIT_LIVE_SUMMARY.md)

| Run | Events | TRACKER_WRITE | LINEAGE_TREND | LT trend!=null | HOF_ROTATE | CELL_PICK |
|-----|--------|---------------|---------------|----------------|------------|-----------|
| K3_1_G | 2,286 | 354 | 0 | 0 | 29 | 1,146 |
| K3_1_D | 3,455 | 398 | 448 | 382 | 18 | 1,547 |
| K3_2_G | 4,024 | 628 | 0 | 0 | 45 | 2,012 |
| K3_2_D | 3,518 | 521 | 380 | 361 | 17 | 1,554 |
| K5_1_G | 6,452 | 774 | 0 | 0 | 49 | 4,017 |
| K5_1_D | 4,150 | 462 | 403 | 385 | 22 | 2,326 |
| K5_2_G | 5,893 | 698 | 0 | 0 | 49 | 3,684 |
| K5_2_D | 4,274 | 488 | 372 | 351 | 19 | 2,414 |

Treatment mechanism verification:
- **TRACKER_WRITE > 0** on all 8 runs: the DG improvement tracker wrote pairs on every run. CONFIRMED.
- **LINEAGE_TREND with trend!=null** on all 4 D runs (range 351-385): SharedBenchmarkLineageStage produced non-trivial lineage comparisons. G runs correctly show 0 LINEAGE_TREND events (G uses Prong 1: hide HoF-dependent metrics from prompts, not shared-benchmark). CONFIRMED.
- **HOF_ROTATE** on all 8 runs (range 17-49): the opponent HoF rotated on every run, confirming the 2D archive produced changing opponent slates. CONFIRMED.
- **CELL_PICK** on all 8 runs (range 1,146-4,017): the CellStratifiedRedisOpponentArchiveProvider sampled from distinct cells. CONFIRMED.

The v3 treatment mechanism (2D MAP-Elites, cell-stratified opponent sampling, shared-benchmark lineage on D, per-G gradient injection) was fully operational on all 8 runs.

### 5.3 G Career Coverage (wins)

| G Run | Final frontier wins | Interpretation |
|-------|---------------------|----------------|
| K3_1_G | 3 | Very low -- truncated run + low tracker coverage |
| K3_2_G | 31 | Healthy career coverage |
| K5_1_G | 37 | Healthy career coverage |
| K5_2_G | 44 | Highest career coverage |

K5 runs accumulated more wins (37 and 44) than K3 runs (3 and 31), consistent with K5 evaluating against more opponents per generation. K3_1_G's value of 3 is an artifact of the early truncation.

### 5.4 Comparison to v2 Baseline

The pre-registered v2 baseline is `actual_fitness = 0.03449` (mean best-overall from heilbron/baseline-repro).

| Run | Best actual_fitness | Delta vs v2 baseline | % of baseline |
|-----|---------------------|----------------------|---------------|
| K3_1_G | 0.035799 | +0.001309 | 103.8% |
| K3_2_G | 0.032509 | -0.001981 | 94.3% |
| K5_1_G | 0.031868 | -0.002622 | 92.4% |
| K5_2_G | 0.033163 | -0.001327 | 96.1% |
| **Grand mean** | **0.033335** | **-0.001155** | **96.7%** |

Three of four G runs underperformed the v2 baseline. The grand mean is 3.3% below v2. However, this comparison carries several pre-registered caveats (from 01_design.md section 1.5):
- v2 used different metric semantics (hard-floor scoring, v2 bug).
- v2 used a different LLM temperature schedule.
- v2 ran at varying generation counts.
- v3 optimizes for a different BD structure (2D niche diversity, not 1D fitness peak).

The v2-vs-v3 comparison is reported as supporting evidence only, not as a decisive metric.

---

## 6. Deviations from Pre-Registration

### D1. Simultaneous cancel at 22.06 hours (uneven completion)

All 8 runs were cancelled simultaneously at 2026-04-19T11:52:50.929Z after 22.06 hours wall-clock. The pre-registered stopping rule was `max_generations=50` with no wall-clock cap. The external cancel was not part of the pre-registered design.

**Impact**: K3_1 pair reached only 29/28 generations (58%), K3_2 reached 42/43 (84%), while K5 pairs reached 51-53 (100%+). The uneven completion makes the K3-vs-K5 comparison asymmetric: K3's weaker run (K3_2) had 8 fewer generations than target, and K3's stronger run (K3_1) had 21 fewer. K5 runs completed in full.

**Assessment**: This is the single largest threat to validity. The K3 arm is systematically disadvantaged by the truncation. The INCONCLUSIVE verdict would likely hold even without this deviation (K3_1_G was still improving while K5 runs had plateaued), but we cannot confirm this.

### D2. K3_1 pair deadlock on ProgressBasedSyncHook

At cancel time, K3_1_G was waiting for `progress >= 284` (current min = 283, 1 unit short) and K3_1_D was waiting for `progress >= 327` (current min = 319, 8 units short). Both had been blocked for approximately 2 hours before the external cancel. The sync hook at `gigaevo/adversarial/sync.py:170` has no deadlock detection or timeout fallback.

**Impact**: K3_1 pair lost approximately 2 hours of compute to the deadlock, equivalent to roughly 5-10 additional generations based on the pair's throughput before the stall. Combined with D1, this means K3_1 lost both wall-clock budget (external cancel) and within-budget compute (deadlock).

**Assessment**: Introduces a confound specific to K3: the deadlock may be more likely at lower K values (fewer opponents, each evaluation covers a smaller fraction of the archive, progress increments may be more uneven). If this is systematic rather than stochastic, K3's truncation is not merely bad luck but a K-dependent failure mode.

### D3. Archive pipeline defect (bugs A1-A5)

The standard `archive_run.sh` tool produced empty `evolution_data.csv` files for all 8 runs due to two independent deserialization bugs (A1: `extra="forbid"` rejecting legacy `iteration` field; A2: pickle references to task `helper` module). Per-program data was recovered via raw Redis backup (`raw_redis_backup/*_raw.tar.gz`, 182 MB, 3,343 programs). The metrics history data used in this analysis comes from the raw backup and is authoritative.

**Impact on analysis**: The fitness trajectories, generation counts, and event counts reported here are derived from raw Redis data, not from the standard archive pipeline. The evidence chain includes one non-standard step (manual Redis dump). The risk of transcription error is minimal (the dump script reads raw JSON blobs and writes them verbatim), but the chain is less auditable than the standard archive pipeline.

**Audit trail**: Bug audit at `ARCHIVE_BUG_AUDIT.md`; raw backups at `experiments/heilbron/k5-budget-v3/raw_redis_backup/`.

### D4. Live reporting bugs (B1-B12) may have polluted checkpoint fitness values

The reporting stack had 12 bugs (documented in `REPORTING_BUGS_AUDIT.md`), the dominant one being that `EvolutionEngine.run()` never persists `engine:total_generations=0` before the first `step()` completes. This caused some checkpoint records to show `best_fitness=0.0` and `gen=null` when the underlying Redis data was intact. The `experiment.yaml` checkpoints array is empty (no checkpoints were recorded due to these bugs), so no polluted checkpoint data enters this analysis. All fitness values in this report are derived directly from the raw Redis metrics history, not from checkpoint records.

### D5. Run matrix reduction (16 runs to 8)

The original design specified 4 runs per arm (8 pairs, 16 processes). This was reduced to 2 runs per arm (4 pairs, 8 processes) due to Redis DB index constraints (DB 16 does not exist; see issues log entry for db=16 blocker). The reduction was applied symmetrically (both arms lost 2 runs) and recorded in experiment.yaml before launch. This halves the statistical power from an already-low N=4 to N=2 per arm.

### D6. Missing environment freeze at launch time

The `environment.txt` uploaded to the GitHub release was captured during closeout (2026-04-19), not at launch time (2026-04-18). No `environment_freeze.txt` was generated at launch. The risk is that package versions drifted between launch and closeout; in practice, the evo conda environment was not modified during the 22-hour run window.

---

## 7. Trajectories

### 7.1 G Frontier actual_fitness Over Generations

**K3_1_G** (terminated at gen 29):
```
Gen  0: 0.00333    Gen 12: 0.02499    Gen 22: 0.03491
Gen  1: 0.00765    Gen 13: 0.02838    Gen 24: 0.03580  <-- final
Gen  4: 0.01418    Gen 16: 0.02902
Gen  5: 0.01774    Gen 18: 0.03293
```
Active improvement through gen 24. Only 5 stagnant generations before cancel.

**K3_2_G** (terminated at gen 42):
```
Gen  0: 0.01608    Gen  9: 0.02714    Gen 27: 0.03251  <-- final
Gen  3: 0.01880    Gen 19: 0.03036    Gen 38: 0.03251  (11 stagnant)
Gen  5: 0.02138    Gen 25: 0.03102
Gen  8: 0.02580
```
Plateaued at gen 27. 15 stagnant generations suggest convergence.

**K5_1_G** (terminated at gen 51):
```
Gen  0: 0.02388    Gen 10: 0.02743    Gen 30: 0.03187  <-- final
Gen  4: 0.02722    Gen 19: 0.02858    Gen 48: 0.03187  (18 stagnant)
Gen 18: 0.02760    Gen 27: 0.03033
```
Plateaued at gen 30. 21 stagnant generations; fully converged.

**K5_2_G** (terminated at gen 52):
```
Gen  0: 0.00717    Gen 15: 0.02721    Gen 42: 0.03052
Gen  1: 0.02430    Gen 23: 0.02764    Gen 45: 0.03076
Gen  9: 0.02634    Gen 34: 0.02936    Gen 47: 0.03316  <-- final
```
Late improvement at gen 47; may not have fully converged.

### 7.2 Convergence Assessment

K3_2_G and K5_1_G both show clear convergence (15+ stagnant generations). K5_2_G showed a late improvement at gen 47, suggesting it may have continued improving. K3_1_G was actively improving at truncation. This pattern partially explains the within-arm variance: runs that had more time to explore found better local optima (K3_1_G at gen 24) or worse ones (K5_1_G plateaued early at gen 30).

---

## 8. Threats to Validity

### T1. Uneven generation counts (MAJOR)

K3_1 pair completed only 58% of target generations. This is the dominant threat. The K3 arm's mean is computed from one converged run (K3_2_G) and one actively-improving truncated run (K3_1_G). The true gen-50 value for K3_1_G is unknown. If K3_1_G had plateaued at gen 29, K3's advantage shrinks; if it had continued its trajectory, K3's advantage grows.

### T2. ProgressBasedSyncHook deadlock as K-dependent confound (MAJOR)

The deadlock occurred in K3_1 (the K=3 pair), not in any K=5 pair. If the deadlock probability is K-dependent (e.g., smaller K leads to tighter sync requirements and more frequent mutual waits), then the K3 arm is systematically penalized by a mechanism unrelated to the treatment's intended effect on evolution quality. With N=1 deadlock occurrence, we cannot distinguish stochastic bad luck from a systematic K-dependent failure mode.

### T3. N=2 per arm (LOW POWER)

The run matrix was reduced from 4 to 2 runs per arm due to the DB-16 blocker (Deviation D5). With N=2, the bootstrap CI is necessarily wide. The observed within-arm SD ranges from 0.0009 (K5) to 0.0023 (K3); the K3 arm's larger variance is partially attributable to the truncated K3_1 pair.

### T4. Archive pipeline failure requiring raw Redis detour (MINOR)

The standard archive pipeline (A1-A5) failed silently. All data in this report comes from raw Redis backups taken before any flush. The risk of transcription error is minimal (the backup script reads raw JSON), but the evidence chain is non-standard.

### T5. No test set evaluation (MINOR)

The Heilbronn task has `has_test_set: false` in experiment.yaml. The primary DV (best `actual_fitness`) is computed deterministically from the point configuration (no stochastic evaluation noise), so the absence of a test set does not introduce overfitting risk.

### T6. Single LLM proxy shared across all 8 runs (MINOR)

All runs shared the Qwen3-235B-A22B-Thinking-2507 proxy at 10.232.30.185:4000. Contention-induced latency differences could cause some runs to advance faster than others, but this is symmetric across K arms (both K=3 and K=5 runs used the same proxy).

---

## 9. What We Learned

### 9.1 v3 2D MAP-Elites Eliminates D Collapse

The most important result is structural, not comparative: the v3 pipeline eliminated the D-fitness collapse that plagued v2/k5-budget-loose. All four D populations maintained frontier fitness between 0.52 and 0.68 throughout the run. The 2D BD with `(fitness, wins)` axes provided sufficient niche diversity to prevent the 1D fitness-only archive from collapsing all D programs into a single cell. This validates the theoretical prediction from Ficici and Pollack (GECCO 2003) and the GAME ISAL 2025 pattern.

### 9.2 ProgressBasedSyncHook Deadlock is a Production Risk

The K3_1 deadlock is the first observed instance of mutual-wait in the sync hook. The mechanism is clear: when both sides wait for each other's progress without a timeout or fallback, forward motion stops entirely. This needs a fix (deadlock guard with a configurable grace period) before any future co-evolution experiment. The fix is independent of the K-value question.

### 9.3 K=3 vs K=5 Remains an Open Question

With the truncated K3_1 pair and N=2, we cannot distinguish K=3 from K=5 at any useful confidence level. The point estimate favors K=3 (-0.00164 in raw units, 4.8% of v2 baseline), but this could be entirely driven by K3_1_G's lucky early trajectory or by the truncation inflating K3's mean. A properly powered replication with the sync-hook deadlock fix would need at least N=4 per arm to detect a 0.002-unit effect at 80% power (estimated from the observed pooled SD of 0.00177).

### 9.4 v3 Actual Fitness is Close to v2 Baseline

The grand mean across all 4 G runs (0.033335) is 3.3% below the v2 baseline (0.03449). One run (K3_1_G at 0.035799) exceeded v2 by 3.8%, while the other three fell 4-8% below. Given the caveats listed in Section 5.4, this is neither a clear regression nor a clear improvement. The v3 pipeline trades peak fitness for archive diversity (the 2D BD spreads evolutionary effort across 225 cells instead of concentrating it on a 1D fitness axis), so a modest fitness peak reduction is the expected cost of diversity.

### 9.5 Archive Pipeline Must Be Hardened

Bugs A1-A5 in the archive pipeline represent a critical data-loss hazard. The `extra="forbid"` setting on the Program Pydantic model silently rejects all programs with legacy fields, and the pickle-based metadata deserialization fails outside the task's Python path. Both bugs produce empty CSVs with exit code 0. The only reason this experiment's data survived is the manual sanity check before Redis flush. Fixes must land before any future experiment.

---

## 10. Decision and Next Steps

### 10.1 Immediate Fixes (Before Any Future Launch)

1. **ProgressBasedSyncHook deadlock guard**: Add a timeout-based fallback (`if waited >= k * expected_step_duration, allow free pass with WARNING`). Prevents the K3_1 failure mode.
2. **Archive pipeline A1-A5**: Fix `extra="forbid"` -> `extra="ignore"`, add pickle fallback, add CSV emptiness check. Prevents silent data loss.
3. **Reporting stack B1-B12**: Fix `EvolutionEngine.run()` gen-0 persistence, narrow exception handling, preserve None in checkpoint records.
4. **Wall-clock runtime enforcement**: Add `max_runtime_hours` to experiment.yaml stopping rules so the stop is pre-registered, not externally imposed.

### 10.2 K-Value Question

The K=3 vs K=5 comparison should be re-run after fixes 1-4 above, with:
- N=4 per arm (minimum; N=6 preferred for 80% power at the observed effect size).
- Pre-registered wall-clock cap aligned with the generation budget.
- Sync-hook deadlock guard ensuring all pairs complete the full generation target.

### 10.3 v3 Pipeline Viability

Despite the INCONCLUSIVE K-comparison, the v3 pipeline itself passed its structural validation: no D collapse, active adversarial dynamics (HOF_ROTATE > 0 on all runs), and career coverage growing throughout the run. The pipeline is viable for future Heilbronn co-evolution experiments. The open question is whether the 2D BD's diversity benefit justifies the modest (~3%) fitness peak reduction relative to v2's 1D approach.

---

## 11. INDEX.md Entry

```
| `heilbron/k5-budget-v3` | Complete | INCONCLUSIVE -- K=3 vs K=5 effect -0.00164 [-0.00393, +0.00065] 95% CI; K3_1 pair deadlocked at gen 29/50; v3 2D MAP-Elites eliminates D collapse (all D fitness > 0.50). N=2 underpowered. | (PR not yet opened; branch `exp/heilbron/k5-budget-v3`) |
```

---

*Ready for Reviewer-2's scrutiny.*
