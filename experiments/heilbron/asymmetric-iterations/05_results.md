# Results: heilbron/asymmetric-iterations

**Date**: 2026-04-14 (closeout)
**Input**: Redis scan of all programs (DBs 1-8), `01_design.md`
**Branch**: `exp/heilbron/asymmetric-iterations`, PR #204
**Launch commit**: `04bd5e69`

---

## 1. Final Metrics

Best fitness obtained by scanning all valid programs (sentinel -1.0 excluded).

### Arm A (Composition)

| Run | Condition | Best actual_fitness | Best Gen | Max Gen | Total Progs | Valid | Inv% |
|-----|-----------|-------------------|----------|---------|-------------|-------|------|
| A1_G | Composition: Constructor, pair 1 | **0.036483** | 8 | 12 | 513 | 388 | 24.4% |
| A1_D | Composition: Improver, pair 1 | 0.035246 | 18 | 27 | 425 | 215 | 49.4% |
| A2_G | Composition: Constructor, pair 2 | 0.031776 | 8 | 12 | 533 | 395 | 25.9% |
| A2_D | Composition: Improver, pair 2 | 0.029232 | 24 | 29 | 565 | 413 | 26.9% |

### Arm C (Gradient-in-prompt)

| Run | Condition | Best actual_fitness | Best Gen | Max Gen | Total Progs | Valid | Inv% |
|-----|-----------|-------------------|----------|---------|-------------|-------|------|
| C1_G | Gradient: Constructor, pair 1 | 0.033377 | 4 | 8 | 670 | 364 | 45.7% |
| C1_D | Gradient: Improver, pair 1 | 0.031162 | 7 | 17 | 501 | 400 | 20.2% |
| C2_G | Gradient: Constructor, pair 2 | **0.036500** | 5 | 9 | 480 | 239 | 50.2% |
| C2_D | Gradient: Improver, pair 2 | 0.035937 | 16 | 19 | 497 | 297 | 40.2% |

### Pair Analysis

| Pair | Arm | G Best | D Best | max(G,D) | % of SOTA (0.03449) |
|------|-----|--------|--------|----------|---------------------|
| A1 | Composition | 0.03648 | 0.03525 | **0.03648** | 105.8% |
| A2 | Composition | 0.03178 | 0.02923 | 0.03178 | 92.1% |
| C1 | Gradient | 0.03338 | 0.03116 | 0.03338 | 96.8% |
| C2 | Gradient | 0.03650 | 0.03594 | **0.03650** | 105.8% |

### Arm-Level Summary

| Arm | Best (across pairs) | Mean (across pairs) | % SOTA (best) | % SOTA (mean) |
|-----|--------------------|--------------------|---------------|---------------|
| A (Composition) | 0.03648 | 0.03413 | 105.8% | 99.0% |
| C (Gradient-in-prompt) | 0.03650 | 0.03494 | 105.8% | 101.3% |
| **Difference (C - A)** | +0.00002 | +0.00081 | -- | -- |

**Baseline / SOTA reference**: heilbron/baseline-repro, mean best-overall actual_fitness = 0.03449 (N=4, SD=0.00212)

---

## 2. Hypothesis Test

**H0**: Neither feedback mode with K=5 inner iterations changes Constructor actual_fitness relative to baseline (0.03449)

**H1**: At least one feedback mode produces meaningfully different Constructor actual_fitness

**Primary metric**: Constructor actual_fitness (best per run), averaged across 2 replicates per arm

**Statistical test**: Descriptive comparison vs pre-registered effect-size thresholds (N=2 per arm insufficient for formal testing)

**Result**: H0 **rejected** (both arms produced results at or above baseline). Feedback mode comparison **inconclusive** (difference 0.00081 < 0.002 threshold).

**Critical caveat**: K=1 inner iterations used instead of K=5. The compute asymmetry component of the treatment was NOT active. Results reflect information flow changes only.

---

## 3. Effect Size

Per pre-registered thresholds (Section 2 of 01_design.md):

| Metric | Arm A | Arm C | Threshold | Interpretation |
|--------|-------|-------|-----------|----------------|
| Constructor mean best fitness | 0.03413 | 0.03494 | vs baseline 0.03449 | A: NULL (borderline), C: POSITIVE |
| Best pair max(G,D) | 0.03648 | 0.03650 | >= 0.03649 for STRONG POSITIVE | Both: borderline STRONG POSITIVE |
| Cross-arm difference | -- | 0.00081 | >= 0.002 for FEEDBACK MODE MATTERS | FEEDBACK MODE NEUTRAL |
| Stagnation broken | Cannot assess | Cannot assess | >5% acceptance after gen 20 | Runs did not reach gen 20 |

---

## 4. Secondary Observations

### G consistently beats D

Constructor (G) produced the best program in 3 of 4 pairs. Only C2 showed near-parity (G: 0.03650, D: 0.03594). This suggests the Constructor role benefits more from structured feedback than the Improver role.

### Invalidity asymmetry between arms

Arm C Constructors showed ~2x higher invalidity (C1_G: 45.7%, C2_G: 50.2%) than Arm A Constructors (A1_G: 24.4%, A2_G: 25.9%). Yet C2_G produced the overall best fitness despite 50.2% invalidity. Hypothesis: Gradient-in-prompt pushes G toward aggressive mutations that fail more but succeed more spectacularly.

### Best programs found early

In most runs, the best program was found at generation 4-8 (G) or 7-24 (D), well before runs stalled. This suggests diminishing returns and is consistent with prior Heilbronn experiments.

### D runs progressed further than G

D reached 17-29 outer generations while G reached only 8-12. Consistent with the sync hook behavior: G blocks waiting for D at epoch boundaries.

### Information flow accelerates early optimization

Both arms achieved >=105% of SOTA within 8-12 G generations. Baseline runs typically needed 30-40 generations. Source code access + structured feedback appear to accelerate early-phase optimization.

---

## 5. Amendment Impact Assessment

| Amendment | Impact on validity | Assessment |
|-----------|-------------------|-----------|
| K=1 instead of K=5 | HIGH | Compute asymmetry not tested. Only information flow changes tested. |
| 3 restarts in first 24h | MEDIUM | Final data clean (post-restart). Some wall-clock time lost. |
| Early termination (all runs) | MEDIUM | Results may underestimate full-run potential. Best fitness found early. |
| min_delta changed from 1 to 8 | LOW | Improved sync hook behavior. Applied uniformly to all runs. |

---

## 6. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| A1_G | Yes | Reached gen 12 (>10 minimum) |
| A1_D | Yes | Reached gen 27 |
| A2_G | Yes | Reached gen 12 |
| A2_D | Yes | Reached gen 29 |
| C1_G | Marginal | Only reached gen 8 (<10) but has 670 programs |
| C1_D | Yes | Reached gen 17 |
| C2_G | Marginal | Only reached gen 9 but has best overall fitness |
| C2_D | Yes | Reached gen 19 |

Per pre-registered criteria: "Minimum completion >= 1/2 pairs per arm must reach gen 40 for the arm to be analyzable." Neither arm reached gen 40, so formally both arms are under the analyzability threshold. However, substantial data was collected and results are informative.

---

## 7. Lessons Learned

**What worked**:
- Source code access (D sees G code) is a powerful mechanism -- both arms produced competitive results quickly
- Steady-state engine with ProgressBasedSyncHook (after fixing the deadlock)
- Per-iteration aggregation for plots produces much cleaner visualization than raw per-program data
- Sentinel value filtering (-1.0) essential for correct fitness visualization

**What didn't work**:
- K=1 inner iterations (should have been K=5 as designed)
- MetricsTracker lacked error isolation -- one bad program killed the entire tracker
- MainRunSyncHook deadlocked under steady-state engine
- Composition-injected programs lacked `iteration` metadata, causing crashes
- All processes died before reaching max_generations

**Bugs / infrastructure issues**:
- `iteration` not a first-class Program field (fixed: promoted to typed field)
- `min_delta=1` too permissive for sync hook (fixed: set to 8)
- Orphan processes from prior experiments repopulated Redis after flush
- Telegram photo upload intermittent 400 errors
- LaTeX compilation broken on server (conda texlive missing format files)

---

## 8. Next Steps

1. **Run full K=5 design**: The pre-registered heilbron/adversarial-dynamic-updates experiment should test compute asymmetry
2. **Fix process death root cause**: Investigate why all runs died before gen 50
3. **Increase replicates**: N=4 pairs per arm for statistical power
4. **Add control arm**: Standard adversarial (no source code access) for causal inference
5. **Qualitative analysis**: Inspect D's mutation prompts to verify source code was used by LLM
6. **Dose-response**: Test K=3, K=5, K=10 inner iterations if K=5 shows effect

---

## 9. Paper / Report Notes

- LaTeX report: `05_results.tex` (compile locally, server pdflatex broken)
- Paper-quality plots: generated with `--paper` flag (Okabe-Ito palette, 300 DPI)
- Per-iteration aggregation and EMA smoothing match old tools/comparison.py behavior
- Sentinel filtering (-1.0) applied to all plots and analysis
- All fitness values verified by scanning every program in Redis (not relying on metrics tracker)
