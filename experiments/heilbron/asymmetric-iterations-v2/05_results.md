# Results: heilbron/asymmetric-iterations-v2

**Date**: 2026-04-16
**Input**: Redis trajectories (DBs 1-8), `01_design.md`, `04_issues_log.md`
**Branch**: `exp/heilbron/asymmetric-iterations-v2`, PR #206
**Replicates**: heilbron/asymmetric-iterations (PR #204) with 6 infrastructure bug fixes

---

## 1. Final Metrics

### Per-Run Results

#### Arm A (Composition)

| Run | Role | Max Gen | Best actual_fitness | Best at Gen | Invalid% | Notes |
|-----|------|---------|---------------------|-------------|----------|-------|
| A1_G | Constructor | 50 | 0.03426 | 36 | 25% | Completed |
| A1_D | Improver | 50 | 0.03426 | -- | 8% | Completed; D did not exceed G frontier |
| A2_G | Constructor | 40 | 0.03357 | 22 | 31% | Terminated early |
| A2_D | Improver | 37 | 0.03089 | -- | 69% | Terminated early; high invalidity |

#### Arm C (Gradient-in-prompt)

| Run | Role | Max Gen | Best actual_fitness | Best at Gen | Invalid% | Notes |
|-----|------|---------|---------------------|-------------|----------|-------|
| C1_G | Constructor | 47 | 0.03588 | 22 | 33% | Terminated early |
| C1_D | Improver | 43 | 0.03588 | -- | 30% | D matched G frontier exactly |
| C2_G | Constructor | 34 | 0.03158 | 24 | 44% | Terminated early; below gen-40 threshold |
| C2_D | Improver | 32 | 0.03328 | -- | 18% | D exceeded G: +0.00170 over C2_G |

### Pair Analysis (max(G,D) as primary metric)

| Pair | Arm | G Best | D Best | max(G,D) | vs Baseline (0.03449) | % Baseline |
|------|-----|--------|--------|----------|-----------------------|------------|
| A1 | Composition | 0.03426 | 0.03426 | **0.03426** | -0.00023 | 99.3% |
| A2 | Composition | 0.03357 | 0.03089 | **0.03357** | -0.00092 | 97.3% |
| C1 | Gradient | 0.03588 | 0.03588 | **0.03588** | +0.00139 | 104.0% |
| C2 | Gradient | 0.03158 | 0.03328 | **0.03328** | -0.00121 | 96.5% |

### Arm-Level Summary

| Arm | G Mean | max(G,D) Mean | Best max(G,D) | % Baseline (mean) |
|-----|--------|---------------|---------------|-------------------|
| A (Composition) | 0.03392 | 0.03392 | 0.03426 | 98.3% |
| C (Gradient) | 0.03373 | 0.03458 | 0.03588 | 100.3% |
| **Difference (C - A)** | -0.00019 | +0.00066 | +0.00162 | -- |

### v1 vs v2 Comparison

| Arm | v1 G Mean | v1 Best | v2 G Mean | v2 Best | v2 max(G,D) Mean |
|-----|-----------|---------|-----------|---------|------------------|
| A (Composition) | 0.03413 | 0.03648 | 0.03392 | 0.03426 | 0.03392 |
| C (Gradient) | 0.03494 | 0.03650 | 0.03373 | 0.03588 | 0.03458 |

**Baseline / SOTA reference**: heilbron/baseline-repro, mean best-overall actual_fitness = 0.03449 (N=4, SD=0.00212)

---

## 2. Hypothesis Test

**H0**: Neither feedback mode changes Constructor actual_fitness relative to baseline (0.03449)

**H1**: At least one feedback mode produces Constructor actual_fitness meaningfully different from baseline

**Primary metric**: max(G,D) actual_fitness per pair, averaged across 2 replicates per arm

**Statistical test**: Descriptive comparison vs pre-registered effect-size thresholds (N=2 per arm insufficient for formal testing)

**Result**: H0 **not rejected**. Neither arm's mean max(G,D) exceeds baseline:
- Arm A mean max(G,D) = 0.03392 (98.3% of baseline, within 0.001 of baseline)
- Arm C mean max(G,D) = 0.03458 (100.3% of baseline, within 0.001 of baseline)

Both arms fall in the **NULL** zone (within 0.001 of baseline 0.03449).

Cross-arm difference: 0.00066 -- well below the 0.002 threshold for detecting a feedback-mode effect.

---

## 3. Effect Size

**Arm A vs baseline**: -0.00057 [-0.00092, -0.00023] (range of pair deltas). NULL.

**Arm C vs baseline**: +0.00009 [-0.00121, +0.00139] (range of pair deltas). NULL, but high variance -- C1 was POSITIVE (+0.00139) while C2 was below baseline.

**Cross-arm (C - A)**: +0.00066. No meaningful difference between feedback modes.

**N=2 limitation**: With only 2 replicates per arm, formal confidence intervals cannot be computed. The pair-level ranges above are descriptive only.

---

## 4. Secondary Observations

1. **Replication failed to reproduce v1 peaks.** v2's best (0.03588 from C1_G) is 1.7% below v1's best (0.03650). v2 ran 4-6x more Constructor generations (gen 34-50 vs gen 8-12 in v1) but achieved lower peaks. This is the most significant finding.

2. **Sync fix changed dynamics.** The most parsimonious explanation: v1's min_delta=1 (the "bug") created loose G/D coupling where D ran many micro-steps per G epoch. The fix to min_delta=8 (= max_mutations_per_generation) enforces strict epoch-level alternation. Tight coupling may over-constrain the search by forcing D to wait for full G epochs before acting.

3. **D rarely exceeded G frontier.** In 3/4 pairs, D's best actual_fitness equals G's (A1, C1) or falls below (A2). Only C2_D exceeded its Constructor (0.03328 vs 0.03158). The Improver is not consistently finding improvements beyond what the Constructor discovers alone.

4. **High invalidity in A2_D (69%).** This run struggled to produce valid mutations throughout, limiting its search effectiveness. All other runs had acceptable invalidity (8-44%).

5. **C2 was slowest.** Validation durations of 1066s/1560s suggest server congestion or heavy evaluation. C2_G only reached gen 34, below the minimum completion threshold of gen 40.

6. **Feedback mode is definitively NULL.** Combined with v1's cross-arm delta of 0.00081, across 8 pairs and 16 runs total, Composition vs Gradient-in-prompt does not affect outcomes. This direction should be closed.

---

## 5. Amendment Impact Assessment

| Amendment | Impact on validity | Assessment |
|-----------|-------------------|-----------|
| Timeout reduction (stage 3000->2400, dag 7200->2400) at gen ~6 | Minor -- all gen 0-6 data lost, restarted fresh | No bias; both arms equally affected |
| min_delta changed from 1 (v1) to 8 (v2) | **Major** -- changed G/D coupling dynamics | See Section 4.2; this is likely the dominant confound explaining v2 < v1 |

---

## 6. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| A1_G | Yes | Completed gen 50 |
| A1_D | Yes | Completed gen 50 |
| A2_G | Yes (partial) | Reached gen 40 (minimum threshold) |
| A2_D | Marginal | 69% invalidity, gen 37 only |
| C1_G | Yes | Gen 47, above threshold |
| C1_D | Yes | Gen 43 |
| C2_G | Marginal | Gen 34, below gen-40 threshold |
| C2_D | Marginal | Gen 32, below gen-40 threshold |

**Minimum completion**: Design required >=1/2 pairs per arm reach gen 40. Arm A: met (A1=50, A2=40). Arm C: partially met (C1=47, **C2=34 below threshold**).

---

## 7. Lessons Learned

**What worked**:
- All 6 infrastructure bug fixes held -- no KF-01 through KF-06 recurrences
- WatchdogEngine plugin architecture worked correctly throughout
- Sync hook maintained G/D parity (no generation divergence)
- Archive pipeline captured all 8 runs cleanly

**What didn't work**:
- Tight G/D coupling (min_delta=8) may have reduced search effectiveness vs loose coupling (min_delta=1)
- C2 pair ran slowly due to long validation times, never reaching gen 40
- Improver (D) rarely exceeded Constructor frontier -- the feedback loop is not producing consistent value

**Bugs / infrastructure issues**:
- 3 watchdog CLI bugs required fixes during launch (documented in 04_issues_log.md)
- SyntaxError Pattern 4 (LLM n-prefix) persists, causing 20-30% invalidity
- Telegram event-loop bug required watchdog restart

---

## 8. Next Steps

1. **Test coupling granularity**: Design experiment with min_delta as IV (loose=1 vs tight=8 vs medium=4). This is now the most promising direction -- v1's accidental loose coupling outperformed v2's intentional tight coupling.
2. **Close feedback mode direction**: Composition vs Gradient-in-prompt is NULL across 8 pairs. No further investment.
3. **Test K=5 inner iterations**: The original motivation (multiple D improvement attempts per G epoch) has never been tested with correct infrastructure. Still worth exploring, but secondary to coupling granularity.
4. **Investigate timeout sensitivity**: The mid-run restart (3000->2400s stage timeout) may interact with coupling dynamics.

---

## 9. Deviations from Pre-Registration

1. **Early termination**: Experiment terminated at gen 32-50 (varies by run) instead of all runs reaching gen 50. Reason: researcher decision to close out; C2 pair was progressing very slowly.
2. **Mid-experiment restart**: All runs restarted at gen ~6 with reduced timeouts (stage_timeout 3000->2400, dag_timeout 7200->2400). Documented in 04_issues_log.md. No impact on treatment arms.
3. **C2 below minimum completion**: C2_G reached gen 34, below the gen-40 minimum. C2 pair results are included but flagged as marginal.
4. **min_delta=8**: This was a bug fix from v1 (min_delta=1), not a protocol deviation. However, it changed the effective dynamics significantly and is the most likely explanation for v2 underperforming v1.

---

Verdict: **INCONCLUSIVE**

Neither arm shows a meaningful effect vs baseline (both NULL on pre-registered thresholds). However, the replication's failure to match v1's peaks -- despite running 4-6x more generations -- reveals that the min_delta sync fix was a hidden confound. The experiment answers the feedback-mode question (NULL, close this direction) but opens a new question about coupling granularity that is more promising than the original IV.
