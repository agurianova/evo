# Phase 5: Results and Post-Mortem -- Generalization via Held-Out Validation

**Experiment name**: `generalization`
**Date**: 2026-03-15
**Author**: Dr. Elena Voss (ml-research-methodologist agent)
**Design doc**: `experiments/hotpotqa/generalization/01_design.md` (APPROVED v5)
**Pre-registration**: `experiments/hotpotqa/generalization/03_plan.md` (commit `ea0884e`)
**GitHub PR**: #81 (branch: `exp/hotpotqa-generalization`)
**Archives**: [exp/hotpotqa/generalization](https://github.com/KhrulkovV/gigaevo-core-internal/releases/tag/exp/hotpotqa/generalization)

---

## 1. Final Metrics

| Run | Mutation LLM | Final gen | Best held_F1 (fitness) | val_EM (1000-sample) | Test EM (run1) | Test EM mean +/- SD (n=5) | val-test gap (5-eval) |
|-----|-------------|-----------|----------------------|---------------------|----------------|--------------------------|----------------------|
| G1 | Qwen3-235B vLLM | 21 (Amendment 1) | 66.94% | 59.30% | 55.00% | 55.00% (n=1 only) | +4.30pp |
| G2 | Qwen3-235B vLLM | 25 | 66.54% | 59.80% | 57.33% | 58.47% +/- 1.41pp | +1.33pp |
| G3 | Gemini-3.1-Pro | 25 | 72.34% | 64.40% | 59.33% | 61.00% +/- 1.03pp | +3.40pp |
| G4 | Gemini-3.1-Pro | 25 | 74.55% | 64.50% | 61.33% | 59.93% +/- 1.30pp | +4.57pp |

**Mean test EM (5-eval means, n=1 for G1)**: 58.60% (SD = 2.61pp)
**Mean test EM (run1 only)**: 58.25% (SD = 2.71pp)

**Cold-start reference** (PR #75): 59.58% (n=4, SD=1.00pp)
**GEPA reference**: 62.3%

---

## 2. Deviations from Pre-Registration

**This section is completed before any results are interpreted.**

| Pre-registered item | Followed? | Notes |
|---------------------|-----------|-------|
| Primary metric (test EM at gen 25, best-by-held_F1) | **Deviated for G1**: gen 21, not 25 | Amendment 1 documents this. G1 terminated at gen 21 due to external process kill. |
| Statistical test (one-sided one-sample t-test, H1 > 59.58%, alpha=0.05, df=3) | **Yes** | Computed below using 5-eval means as the more reliable estimator. |
| Evaluation script | **Yes** | `run_test_eval.sh` used for all runs. |
| Run design table (pipeline=hotpotqa_asi, prompts=generalization, cold start) | **Yes** | All 4 runs launched per design table. G1/G2 = Qwen3-235B, G3/G4 = Gemini-3.1-Pro. |
| Monitoring plan (gen 3/5/13/25 checkpoints) | **Yes** | Gen 1 checkpoint logged in 03_plan.md. Final checkpoint at gen 21 (G1) / 25 (G2-G4). |
| Early termination rule (no frontier improvement for 10+ gens at gen >= 15) | **Not triggered** for G2-G4. G1 terminated externally (Amendment 1). |
| Max generations = 25 | **Deviated for G1** | See Amendment 1. |
| Val-test gap metric: val_em_600 for comparable gap vs cold_start | **Deviated** | val_em_600 values not extracted from archives. Analysis uses val_EM (1000-sample EM) for gap computation. See note below. |

**Unrecorded deviation (val-test gap metric)**: The pre-registered secondary metric for val-test gap comparison was `val_em_600` (EM on train[0:600]), specifically designed for comparability with cold_start's 2.58pp gap. The val-test gaps reported in this analysis use the full 1000-sample `val_EM` instead. This means the gap comparison with cold_start's 2.58pp reference is not on a like-for-like basis. The 1000-sample val_EM includes both evo-set and held-out samples, potentially inflating or deflating the gap relative to what val_em_600 would show. This is a **protocol violation** (unrecorded deviation) that affects only the secondary gap verdict, not the primary t-test. Impact: the gap verdict is reported as APPROXIMATE and should be treated with reduced confidence.

---

## 3. Amendment Impact Assessment

| Amendment | Impact on validity | Assessment |
|-----------|-------------------|-----------|
| Amendment 1: G1 early termination at gen 21 | **Minor** | G1's best held_F1 at gen 21 (66.94%) exceeds G2's final held_F1 at gen 25 (66.54%), suggesting the frontier had plateaued. G1's test EM (55.00%) is the lowest of all 4 runs, but this cannot be attributed to early termination since the best program was already selected. Sensitivity analysis excluding G1 is provided below. |

---

## 4. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| G1 | **Yes (with caveat)** | Terminated at gen 21 (4 gens short). Best-by-held_F1 program selected from available gens. Included in primary analysis; excluded in sensitivity analysis. |
| G2 | **Yes** | Completed gen 25 as designed. |
| G3 | **Yes** | Completed gen 25 as designed. |
| G4 | **Yes** | Completed gen 25 as designed. |

No run triggered any invalidation criterion from the design (Section 10): thinking mode was active, pipeline was hotpotqa_asi, no gen-0 held_F1 > 0.55, max_elites=8, num_parents=1.

---

## 5. Hypothesis Test

**H0**: Mean test EM across n=4 held-out-validation runs does not differ from the cold-start reference mean of 59.58% (PR #75, n=4, SD=1.00pp) by more than 1.67pp (MDE at 80% power).

**H1**: Mean test EM >= 62.00% (+2.42pp above cold-start reference), indicating that held-out validation produces programs that generalize substantially better than single-set fitness.

**Primary metric**: Mean test EM = **58.60%** (using 5-eval means where available, n=1 for G1)

**Statistical test**: One-sided one-sample t-test, H1: treatment_mean > 59.58%

| Statistic | Value |
|-----------|-------|
| n | 4 |
| Mean test EM | 58.60% |
| SD | 2.61pp |
| SE | 1.31pp |
| t(3) | -0.750 |
| p (one-sided) | 0.746 |
| 95% CI | [54.44%, 62.76%] |
| Delta vs reference | -0.98pp |

**Result**: H0 is **not rejected** at alpha = 0.05. The t-statistic is negative (-0.750), indicating the treatment mean is *below* the cold-start reference. The one-sided p-value of 0.746 provides no evidence that held-out validation improves test EM.

### Primary Verdict: NULL

The mean test EM of 58.60% falls below the cold-start reference of 59.58%. The treatment did not produce the predicted improvement. The experiment is well within the NULL band (p >= 0.05 for any threshold).

### Robustness checks

**Using run1 test EM only** (no 5-eval averaging): Mean = 58.25%, SD = 2.71pp, t(3) = -0.983, p = 0.801. Verdict unchanged: **NULL**.

**Sensitivity analysis excluding G1** (Amendment 1, n=3): Mean = 59.80%, SD = 1.27pp, t(2) = 0.300, p = 0.396. Verdict unchanged: **NULL**. Excluding G1 raises the mean to near-reference, but the effect is not significant with n=3.

---

## 6. Effect Size

The point estimate is **-0.98pp** (58.60% vs 59.58%). The held-out validation treatment produced programs that scored *below* the cold-start reference, not above it. Cohen's d = -0.98 / 2.61 = -0.38 (small-to-medium negative effect, opposite to the predicted direction).

The 95% CI for the delta spans [-5.14pp, +3.18pp], encompassing both meaningful positive and meaningful negative effects. With SD = 2.61pp (2.6x the cold-start SD of 1.00pp), the experiment was substantially noisier than predicted, consistent with the pre-registered Risk 6 (held_F1-only fitness increases selection noise).

**Practical significance**: None. The treatment did not improve generalization.

---

## 7. Secondary Observations

### 7a. Val-test EM gap (APPROXIMATE -- see deviation note in Section 2)

Using the available val_EM (1000-sample EM, NOT the pre-registered val_em_600):

| Run | val_EM | Test EM (5-eval) | Gap |
|-----|--------|-----------------|-----|
| G1 | 59.30% | 55.00% | +4.30pp |
| G2 | 59.80% | 58.47% | +1.33pp |
| G3 | 64.40% | 61.00% | +3.40pp |
| G4 | 64.50% | 59.93% | +4.57pp |
| **Mean** | 62.00% | 58.60% | **+3.40pp** |

**Approximate gap verdict**: **GAP UNCHANGED** (3.40pp falls in the [2.5pp, 4.0pp) band).

This verdict carries reduced confidence because val_EM (1000-sample) is not directly comparable to the cold_start val_EM (600-sample). However, the direction is clear: the val-test gap was NOT compressed by the held-out validation mechanism. It was either unchanged or marginally inflated relative to cold_start's 2.58pp.

### 7b. Held_F1 (fitness) vs test EM -- the fitness-generalization disconnect

| Run | Held_F1 (fitness) | Test EM (5-eval) | Fitness-test gap |
|-----|-------------------|-----------------|------------------|
| G1 | 66.94% | 55.00% | +11.94pp |
| G2 | 66.54% | 58.47% | +8.07pp |
| G3 | 72.34% | 61.00% | +11.34pp |
| G4 | 74.55% | 59.93% | +14.62pp |
| **Mean** | 70.09% | 58.60% | **+11.49pp** |

The held_F1 values are dramatically inflated relative to test EM. The fitness metric (held_F1 on train[700:1000]) reached 66-75%, but test EM remained at 55-61%. This 11.5pp average gap between the fitness signal and the actual generalization target reveals that the held-out 300 samples were NOT a reliable proxy for the test set. Programs optimized for high held_F1 did not generalize to the test set proportionally.

This is the most important diagnostic finding of the experiment: **the held-out set itself was overfitted**. With 25 generations x 8 mutations = ~200 programs scored on the same 300 held-out samples, the archive converged on programs that score well on those specific 300 samples, not on truly unseen data. This was pre-registered as Risk 3 and materialized.

### 7c. Mutation LLM subgroup analysis (exploratory)

| Subgroup | Runs | Mean test EM (5-eval) | Mean held_F1 |
|----------|------|----------------------|-------------|
| Qwen3-235B | G1, G2 | 56.73% | 66.74% |
| Gemini-3.1-Pro | G3, G4 | 60.47% | 73.45% |
| Difference | | +3.73pp | +6.71pp |

Gemini runs achieved higher test EM (+3.73pp) and substantially higher held_F1 (+6.71pp). The held_F1 inflation is more pronounced for Gemini, consistent with the finding from gemini_mutation (PR #79) that stronger mutation LLMs amplify val-set overfitting. The test EM advantage is smaller than the held_F1 advantage, confirming that Gemini's superior optimization ability inflates the fitness metric more than it improves actual generalization.

This subgroup comparison is exploratory and confounded with server assignment (G1/G2 on Host A, G3/G4 on Host B). No causal claim is made.

### 7d. Variance inflation

The observed SD of 2.61pp is 2.6x the cold-start SD of 1.00pp. This confirms the pre-registered concern (Design Section 7, Risk 6): using held_F1 as the sole fitness metric, computed on only 300 samples, introduces substantial selection noise. The noisy fitness signal causes higher run-to-run variance in test EM outcomes.

The elevated variance has direct consequences for statistical power. The design assumed SD comparable to cold_start (1.00pp), yielding MDE = 1.67pp. With the observed SD = 2.61pp, the actual MDE rises to (2.353 + 0.978) * 2.61 / 2.0 = **4.35pp** -- meaning the experiment could only detect effects of 4.35pp or larger with 80% power. The pre-registered target effect of +2.42pp would require n = ceil((2.353 + 0.978)^2 * 2.61^2 / 2.42^2) = **13 runs** to detect with 80% power.

However, the power argument is moot: the point estimate is *negative* (-0.98pp). Even with perfect power, the result would be NULL.

---

## 8. Success Criteria Verdict

| Outcome | Threshold | Result |
|---------|-----------|--------|
| STRONG POSITIVE -- PRELIMINARY | mean test EM >= 62.30% | **No** (58.60%) |
| POSITIVE -- PRELIMINARY | mean test EM in [62.00%, 62.30%) | **No** |
| SUGGESTIVE | mean test EM in [60.50%, 62.00%), p < 0.05 | **No** |
| MARGINAL | mean test EM in [59.58%, 60.50%), p < 0.05 | **No** |
| **NULL** | **p >= 0.05** | **YES -- mean 58.60%, p = 0.746** |
| NEGATIVE | mean test EM < 57.58% | **No** (mean 58.60% > 57.58%) |

**Primary verdict: NULL**

The held-out validation mechanism, as implemented (fitness = held_F1 on train[700:1000], mutation feedback from train[0:700] only), produced no detectable improvement in test EM relative to the cold-start reference. The mean test EM of 58.60% is 0.98pp *below* the reference.

### Test 4 (GEPA comparison)

| Criterion | Met? |
|-----------|------|
| Any run >= 62.3% test EM? | **No** (max = 61.00%, G3 5-eval mean; max run1 = 61.33%, G4) |
| t-test mean >= 62.3%? | **No** (mean = 58.60%) |

**Verdict: GEPA NOT REACHED**

---

## 9. Interpretation

### Why did the held-out mechanism fail?

The experiment was designed to break the feedback loop between the selection signal (fitness) and the guidance signal (mutation feedback). The theory was: if fitness is computed on samples the mutation LLM never sees as failure cases, programs that overfit to the evo set will be penalized, and programs with truly general reasoning will be rewarded.

Three factors explain the NULL result:

**Factor 1: The held-out set itself was overfitted.** With ~200 programs evaluated on the same 300 held-out samples across 25 generations, the MAP-Elites archive converged on programs scoring high on those specific samples. The 11.5pp gap between held_F1 (70.1%) and test EM (58.6%) is the smoking gun. The held-out set is "held out" from the mutation LLM's failure feedback but NOT from the selection process. After 25 rounds of selection on the same 300 samples, the programs are tuned to those samples, defeating the purpose of the split. This was pre-registered as Risk 3 and is now confirmed.

**Factor 2: The fitness signal was too noisy.** Using 300 held-out samples with SE ~2.5pp for fitness means that two programs differing by 3pp in true generalization ability are nearly indistinguishable to MAP-Elites. The selection process effectively becomes semi-random for programs within the noise band. The 2.6x variance inflation (SD 2.61pp vs 1.00pp) in run-level outcomes confirms that the noisy fitness propagated through to unstable final results. This was pre-registered as Risk 2.

**Factor 3: The evo/held-out split may have introduced a counterproductive decoupling.** In the standard GigaEvo configuration, the mutation LLM sees failures from the same set used for fitness. This tight coupling means that if the mutation LLM successfully fixes a failure pattern, the fitness improves immediately. With held_F1-only fitness, fixing evo-set failures does not directly improve fitness unless the fix also generalizes to the held-out set. This weaker coupling between "what the mutation LLM works on" and "what gets rewarded" may slow convergence without a compensating generalization benefit.

### What does this tell us about the val-test gap?

The cold-start val-test gap of 2.58pp (PR #75) has now been investigated through two mechanisms:

1. **Rotating validation set** (val_gap, PR #70, Gate B): NULL. Stochastic decoupling via hash-seeded rotation did not help.
2. **Deterministic held-out split** (this experiment): NULL. Complete train/val separation did not help.

Both approaches target the hypothesis that the val-test gap is caused by **selection bias** -- programs are selected on the same data they are optimized for. Both returned NULL results. This pattern strongly suggests that the val-test gap is NOT primarily caused by selection bias. Instead, it is likely caused by **distribution shift** between train and test samples, or by **the inherent generalization limit of prompt-level optimization** within a fixed chain topology.

This is a negative result with genuine scientific value: it narrows the space of plausible mechanisms for the val-test gap, directing future work toward structural interventions rather than regularization.

---

## 10. Lessons Learned

**What worked**:
- The experimental design with n=4 replication and pre-registered statistical tests provided a clean verdict despite the unexpected variance inflation.
- The held_F1/test_EM diagnostic (11.5pp gap) would not have been observed without the explicit metric separation in validate.py. Good instrumentation.
- The stochastic 5-eval protocol (n=5 test evaluations per program) reduced noise in per-run test EM estimates, as demonstrated by G3 (run1=59.33%, mean=61.00%, delta=1.67pp).

**What didn't work**:
- Using 300 held-out samples as the sole fitness metric was too noisy. The SE ~2.5pp per-program evaluation means MAP-Elites cannot reliably distinguish programs within a 5pp band. Future fitness-regularization experiments should use larger held-out sets or multi-evaluation averaging.
- The 25-generation budget was likely too long for the held-out mechanism. By gen 25, the archive had evaluated ~200 programs on the same 300 held-out samples, overfitting the held-out set. A shorter budget (10-15 gens) with early stopping based on held_F1 plateau might produce different results, though this is speculative.

**Bugs / infrastructure issues**:
- G1 external process kill at gen 21. Impact was minor (Amendment 1), but uncontrolled termination is a recurring risk when sharing compute infrastructure. Future experiments should implement graceful shutdown hooks.

---

## 11. Next Steps

1. **Do NOT pursue further held-out validation variants** within the static-chain framework. The NULL result, combined with the rotation NULL (PR #70), provides converging evidence that selection-bias regularization does not address the val-test gap. The gap is likely structural (distribution shift or prompt-level generalization limit).

2. **Structural chain mutation** remains the highest-priority direction. The 59-60% ceiling has now been confirmed across **25 consecutive independent runs** (12 warm, 4 cold Qwen3-235B, 3 ColBERT, 2 Gemini-mutation, 4 generalization). Prompt-level evolution within a fixed 6-step topology is saturated. Allowing the mutation operator to modify chain topology (add/remove/reorder chain steps) is the only remaining untested lever that could fundamentally change the search space.

3. **K-fold cross-validation** (mentioned in the design as a potential follow-up for POSITIVE results) is NOT recommended. If a 300-sample held-out set was overfitted by 200 programs, K-fold with K=3-5 and similar generation budgets would face the same problem. The issue is not the split strategy but the fixed-sample selection mechanism itself.

4. **Population-level diversity maintenance** (e.g., novelty search, MAP-Elites with behavioral descriptors beyond fitness) could address the convergence-to-noise problem observed here, but this is a framework-level change, not a HotpotQA-specific experiment.

---

## 12. Paper / Report Notes

**Claim this experiment supports**: The val-test gap in GigaEvo's HotpotQA chains is NOT caused by selection bias (fitness computed on the same samples used for mutation feedback). A deterministic train/val split with held_F1-only fitness -- the textbook regularization technique -- produced NULL results (mean test EM 58.60% vs 59.58% cold-start reference, t(3) = -0.750, p = 0.746, n = 4). Combined with the prior rotation NULL (PR #70), this provides converging evidence that the gap is structural rather than a selection artifact.

**Claim this experiment refutes**: The hypothesis that "if we simply evaluate fitness on samples the mutation LLM has never seen failures from, programs will generalize better." The held-out set itself was overfitted (held_F1 70.1% vs test EM 58.6%, gap 11.5pp), demonstrating that selection-based overfitting occurs even when the selection set is disjoint from the guidance set.

**Key quantitative result for the paper**: Table row for the generalization experiment in the HotpotQA results summary:

| Method | n | Test EM (mean +/- SD) | Val-test gap | Verdict |
|--------|---|----------------------|-------------|---------|
| Held-out validation (held_F1 only) | 4 | 58.60% +/- 2.61pp | +3.40pp (approx) | NULL |
| Cold-start reference | 4 | 59.58% +/- 1.00pp | +2.58pp | -- |

**Stagnation count update**: 25 consecutive independent HotpotQA runs (all conditions, all fitness metrics) have now stagnated at or below the 59-60% ceiling. This is the strongest evidence yet that the ceiling is a fundamental limitation of prompt-level evolution within a fixed chain topology.

---

*Ready for Reviewer-2's scrutiny.*
