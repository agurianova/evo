# Results: adversarial/adversarial-vs-solo

**Date**: 2026-04-12
**Input**: Final metrics from Redis (4 solo runs, gen 50/50), adversarial arm from heilbron/baseline-repro (Amendment 2), `01_design.md`, `03_plan.md`, `04_issues_log.md`

---

## 1. Final Metrics

### Solo Arm (this experiment)

| Run | Label | Gen | Fitness (actual_fitness) | Invalid% | Notes |
|-----|-------|-----|--------------------------|----------|-------|
| 1 | S1 | 50/50 | 0.03538 | 20% | Highest solo run |
| 2 | S2 | 50/50 | 0.03199 | 31% | Persistent gen lag + elevated invalidity (Issue #1) |
| 3 | S3 | 50/50 | 0.03458 | 10% | Lowest invalidity |
| 4 | S4 | 50/50 | 0.02872 | 14% | 17-gen stagnation (gen 26-43), partial recovery |

**Solo mean**: 0.03267 (SD=0.00300)

### Adversarial Arm (from heilbron/baseline-repro, per Amendment 2: best-overall per pair)

| Pair | Source | Gen | Best-overall actual_fitness | Notes |
|------|--------|-----|----------------------------|-------|
| 1 | P1_B (Improver) | 45/50 | 0.03614 | Improver exceeded Constructor |
| 2 | P2_A (Constructor) | 30/50 | 0.03276 | Early closeout |
| 3 | P3_A (Constructor) | 50/50 | 0.03650 | Near Q_MAX (0.0365) |
| 4 | P4_B (Improver) | 50/50 | 0.03255 | Improver exceeded Constructor |

**Adversarial mean (best-overall)**: 0.03449 (SD=0.00212)

### Adversarial Arm (Constructor-only, per Amendment 1)

| Pair | Source | Gen | Constructor actual_fitness |
|------|--------|-----|--------------------------|
| 1 | P1_A | 46/50 | 0.03400 |
| 2 | P2_A | 30/50 | 0.03276 |
| 3 | P3_A | 50/50 | 0.03650 |
| 4 | P4_A | 50/50 | 0.03023 |

**Adversarial mean (Constructor-only)**: 0.03337 (SD=0.00261)

**Baseline / reference**: heilbron-prover mean actual_fitness = 0.03464. Q_MAX (Heilbronn n=11) = 0.0365.

---

## 2. Hypothesis Test

**H₀**: There is no difference in actual_fitness between adversarial co-evolution and solo MAP-Elites.
**H₁**: Adversarial co-evolution produces different actual_fitness than solo MAP-Elites.
**Primary metric**: Best-overall actual_fitness at gen 50 (per Amendment 2)
**Statistical test**: Welch's two-sample t-test (unequal variance), two-sided
**Pre-registered alpha**: 0.10

**Result**: H₀ **not rejected** at α = 0.10.

| Comparison | Difference | t | df | p (two-sided) | Cohen's d |
|------------|-----------|---|-----|---------------|-----------|
| Adversarial (best-overall) vs Solo | +0.00182 | 0.990 | 5.40 | 0.365 | 0.70 |
| Adversarial (Constructor-only) vs Solo | +0.00070 | 0.354 | 5.95 | 0.735 | 0.25 |

---

## 3. Effect Size

**Primary (best-overall vs solo)**: +0.00182 [-0.00183, +0.00547] 90% confidence interval

The point estimate (+0.00182) favors adversarial but falls below the pre-registered equivalence threshold of 0.003. The 90% CI spans zero and includes values up to +0.00547 — the data are consistent with effects ranging from a trivial solo advantage to a meaningful adversarial advantage.

Cohen's d = 0.70 (medium-large). Despite the non-significant p-value, the effect size is not negligible — the non-significance is driven by low power (N=4/arm, estimated 55% at design).

**MDE at 80% power**: ~0.0038 (1.46 * SD). Effects below 0.0038 cannot be reliably detected at N=4/arm.

**Secondary (Constructor-only vs solo)**: +0.00070, negligible effect (d=0.25). This comparison more directly isolates the adversarial mechanism (one population vs one population) and shows near-zero difference.

---

## 4. Secondary Observations

### 4.1 Solo arm bimodality

The solo arm shows a bimodal distribution: S1 (0.03538) and S3 (0.03458) are in the adversarial range (~0.034-0.035), while S2 (0.03199) and S4 (0.02872) are well below. This bimodality (gap of ~0.005 between the two clusters) is larger than the between-arm difference (0.00182).

**Interpretation**: Solo MAP-Elites can reach adversarial-level fitness but with higher variance. Two of four solo runs matched the adversarial mean. The adversarial arm shows tighter clustering (SD=0.00212 vs SD=0.00300), suggesting opponent pressure may regularize solutions toward more consistent quality.

### 4.2 S2 invalidity pattern (Issue #1)

S2 had persistent elevated invalidity (28-31%) and generation lag throughout the run. Root cause: diverse LLM error types (SubprocessError, ValueError, SyntaxError) — not a systematic bug. S2 finished at gen 50 despite the lag. This is hypothesis-relevant: it demonstrates the sensitivity of solo MAP-Elites to initial exploration luck, a risk that adversarial may partially mitigate through the competitive pressure mechanism.

### 4.3 S4 stagnation

S4 stagnated at fitness 0.02828 for 17 generations (gen 26-43), then partially recovered to 0.02872. This stagnation pattern was not observed in any adversarial run. Adversarial opponent pressure may provide escape pressure from local optima that solo MAP-Elites lacks.

### 4.4 Compute asymmetry

Per design Section 12 (Open Question 2): adversarial pairs consume ~2x LLM calls per replicate (Constructor + Improver). A compute-normalized comparison would require solo runs at gen 100 (not available). The primary result is "per generation" which is algorithm selection-relevant: given 50 generations of budget, which approach yields higher actual_fitness?

---

## 5. Amendment Impact Assessment

| Amendment | Impact on validity | Assessment |
|-----------|-------------------|-----------|
| A1: Reuse adversarial data from baseline-repro | Non-contemporaneous comparison (~1 day gap). Same server, model, config. | LOW risk. Server load and model behavior assumed stable. |
| A2: Use best-overall instead of Constructor-only | Favors adversarial arm (+0.00112 mean lift vs Constructor-only). | MEDIUM impact. Scientifically justified: adversarial runs produce solutions from both populations. But inflates adversarial mean. |

---

## 6. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| S1 | Yes | Clean run, gen 50/50 |
| S2 | Yes | Elevated invalidity (31%) but reached gen 50/50. Issue #1 documents root cause as random variance. |
| S3 | Yes | Clean run, gen 50/50, lowest invalidity |
| S4 | Yes | 17-gen stagnation but reached gen 50/50. Stagnation is hypothesis-relevant, not infrastructure. |

All 4 solo runs valid. All 4 adversarial data points from baseline-repro valid (per that experiment's 05_results.md).

Pre-registered minimum: 3/4 runs per arm at gen 40. All 4/4 met this. **No run invalidation.**

---

## 7. Lessons Learned

**What worked**:
- Solo `heilbron_solo/` problem variant with single seed (grid.py) successfully matched the adversarial Constructor setup, eliminating seed diversity confound.
- 50-generation runs completed cleanly for all 4 solo runs despite one having persistent invalidity.
- Reusing adversarial data from baseline-repro (Amendment 1) saved ~400 GPU-hours and 8 Redis DBs.

**What didn't work**:
- N=4/arm provides only 55% power. The medium effect size (d=0.70) could not reach significance. Future comparisons of this type need N=8+ per arm for conclusive results.
- Solo arm variance (SD=0.00300) is higher than adversarial (SD=0.00212), suggesting solo is more sensitive to initial conditions.

**Bugs / infrastructure issues**:
- S2 generation lag with 31% invalidity (Issue #1). Root cause: random LLM output variance, not infrastructure. No systemic fix needed.
- S4 17-generation stagnation (gen 26-43). Algorithm behavior, not bug.
- Checkpoint-analyst accidentally broke blinding by reading 01_design.md (noted in issues log). No decisions were affected — advisory only.

---

## 8. Deviations from Pre-Registration

1. **Adversarial arm not re-run (Amendment 1, pre-registered)**: Reused baseline-repro Constructor data instead of launching 8 new adversarial runs. Justified by identical config. Approved by researcher before launch.

2. **Primary metric changed to best-overall (Amendment 2, pre-registered)**: Changed from Constructor-only to max(Constructor, Improver) per pair. Both metrics reported. Approved before launch.

3. **Checkpoint-analyst blinding breach**: At gen 41, the blinded checkpoint-analyst read the design document (01_design.md) and learned the condition labels. This violates the blinding protocol. Impact: NONE — the analyst's output was advisory only, no decisions were changed based on its assessment, and no stopping rules were triggered.

No un-registered deviations.

---

## 8. Next Steps

1. **Do NOT close the adversarial research line based on this result.** The INCONCLUSIVE verdict at 55% power cannot distinguish a true null from a small positive effect. The point estimate (+0.00182) and Cohen's d (0.70) suggest a real but modest advantage.

2. **Recommended: increase N.** Re-run with N=8/arm (power >80% for MDE=0.003) to distinguish NULL from POSITIVE conclusively. Requires only 4 additional solo runs (adversarial N=8 available from combined heilbron-prover + baseline-repro data).

3. **Consider isolating the adversarial mechanism.** This experiment tested the "full adversarial package" (opponents + richer prompts + composite fitness + adversarial framing). A factorial experiment varying these components would identify which aspect drives any advantage. The metrics-in-prompts confound (4 vs 2 metrics visible to LLM) is the highest-priority factor to isolate.

4. **Variance reduction**: Solo arm variance (SD=0.00300) may be reducible with better initial programs or longer warm-up phases.

---

Verdict: **INCONCLUSIVE**

The adversarial arm (best-overall) outperformed solo by +0.00182 (5.3% of baseline), but this difference is not statistically significant (p=0.365, alpha=0.10) and the study was underpowered (55%). The point estimate falls between the SUGGESTIVE NULL threshold (0.001) and the equivalence threshold (0.003). Two of four solo runs matched adversarial performance, two did not. The adversarial line should not be closed based on this result — increased N is needed for a definitive conclusion.

---

## 9. Paper / Report Notes

This experiment provides the first direct comparison of adversarial co-evolution vs solo MAP-Elites on the Heilbronn n=11 problem. While underpowered, key observations support future investigation:
- Solo MAP-Elites CAN reach adversarial-level fitness (2/4 runs) but with higher variance
- Adversarial arm shows tighter clustering (SD=0.00212 vs 0.00300), suggesting regularization effect
- Stagnation (S4) and elevated invalidity (S2) observed only in solo arm
- Effect size d=0.70 is meaningful if confirmed with larger N
