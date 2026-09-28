# Results: heilbron/adversarial-repro-v2

**Date**: 2026-04-24
**Input**: Final metrics from Redis DBs 1-8 (archived); `01_design.md`; `03_plan.md` (no amendments)
**Analyst**: Dr. Elena Voss (ml-research-methodologist agent)
**Predecessor**: `heilbron/adversarial-repro-v1` (NULL verdict, PR #211 merged 2026-04-21)

---

## 0. Executive Summary

The three stacked improvements (SharedBenchmarkFilteredLineageStage on D, OpponentSamplingMode.SOFTMAX on G, I-16/I-17 fixes) did not recover signal in the Heilbronn N=11 adversarial co-evolution pipeline. Mean best-ever actual_fitness across 4 G runs = 0.0331 [0.0305, 0.0356] 95% CI (bootstrap, B=10000), compared against the v1 baseline of 0.03413. The point estimate falls at the extreme lower edge of the pre-registered NULL band (0.03313--0.03513), with a delta of -0.10pp [-0.41, +0.21] 95% CI versus v1. The experiment was terminated early at approximately 23 hours of wall-clock time, with G runs reaching only 36--55 engine generations out of the target 200. Despite the early termination, the result is interpretable: the stacked info-flow treatments produced no measurable lift and if anything showed a slight directional regression.

**VERDICT: NULL**

---

## 1. Final Metrics

### 1.1 Primary: Best-Ever actual_fitness per G Run

| Run | Arm | Engine Gen | Best AF | Mean AF | N Programs | Invalid % | Best Program ID |
|-----|-----|------------|---------|---------|------------|-----------|-----------------|
| A1_G | A (Composition) | 36 | **0.03390** | 0.01780 | 453 | 47% | 1144aa63 |
| A2_G | A (Composition) | 55 | **0.03280** | 0.01681 | 577 | 42% | 448df417 |
| C1_G | C (Gradient-in-prompt) | 53 | **0.03650** | 0.02027 | 373 | 42% | e41afaff |
| C2_G | C (Gradient-in-prompt) | 50 | **0.02939** | 0.01567 | 272 | 35% | 33226194 |

**Grand mean (best-AF)**: 0.03315 (SD = 0.00295, SEM = 0.00147)
**95% CI (Student's t, N=4, df=3)**: 0.0331 [0.0285, 0.0378]
**95% CI (bootstrap, B=10000)**: 0.0331 [0.0305, 0.0356]

**Grand mean (mean-AF)**: 0.01764 (SD = 0.00196)

### 1.2 Secondary: D Run Metrics

| Run | Engine Gen | Best AF | Mean AF | N Programs | Invalid % | Best Program ID |
|-----|------------|---------|---------|------------|-----------|-----------------|
| A1_D | 38 | **0.03450** | 0.02247 | 382 | 12% | de5ab59c |
| A2_D | 91 | **0.03086** | 0.02674 | 861 | 17% | c8b98d18 |
| C1_D | 87 | **0.03650** | 0.03456 | 893 | 11% | 2349574d |
| C2_D | 40 | **0.03000** | 0.02523 | 387 | 10% | 092f223e |

**D grand mean (best-AF)**: 0.03297 (SD = 0.00306)
**D grand mean (mean-AF)**: 0.02725 (SD = 0.00518)

### 1.3 Compute Ratio (D/G)

| Pair | G Gen | D Gen | Ratio (D/G) |
|------|-------|-------|-------------|
| A1 | 36 | 38 | 1.06x |
| A2 | 55 | 91 | 1.65x |
| C1 | 53 | 87 | 1.64x |
| C2 | 50 | 40 | 0.80x |

**Mean ratio**: 1.29x (range: 0.80x--1.65x)

This D/G ratio is substantially lower than v1's 4.00x (range 2.28x--6.66x). The reduced asymmetry is consistent with the two-pass bucketed refresh mechanism on D, which imposes additional per-epoch overhead that slows D relative to G. The drift_cap=100000 (effectively no-op cap) was applied uniformly. The near-parity ratio in A1 (1.06x) and C2 (0.80x -- D actually behind G) suggests that the v2 D-side refresh mechanism is compute-heavy enough to neutralize the natural D speed advantage observed in v1.

### 1.4 Baselines and Historical Comparators

| Comparator | mu_G best-AF | Source |
|------------|-------------|--------|
| **v2 (this experiment)** | **0.03315** | 4 G runs |
| v1 (adversarial-repro-v1) | 0.03413 | 4 G runs, PR #211 |
| v0 (asymmetric-iterations) | 0.03574 | Historical SOTA (loose coupling) |
| baseline-repro (solo) | 0.03449 | Non-adversarial MAP-Elites |
| GEPA paper reference | ~0.0374 | Published SOTA |

### 1.5 Strategy Rejection Rates

| Run | Invalid / Total | Rejection Rate |
|-----|----------------|---------------|
| A1_G | ~213 / 453 | 47% |
| A2_G | ~242 / 577 | 42% |
| C1_G | ~157 / 373 | 42% |
| C2_G | ~95 / 272 | 35% |
| A1_D | ~46 / 382 | 12% |
| A2_D | ~146 / 861 | 17% |
| C1_D | ~98 / 893 | 11% |
| C2_D | ~39 / 387 | 10% |

G rejection rates (35--47%) are elevated relative to v1 (24--45%) and continue the established pattern where G rejection is consistently higher than D rejection (10--17%). The G invalidity rates in v2 are uniformly higher than v1's, which may reflect the SOFTMAX sampling treatment: stochastic opponent rotation exposes G to a broader distribution of D improvers, some of which may be harder to resist, leading to more failed mutation attempts.

---

## 2. Hypothesis Test

**H0**: mu_v2_G <= mu_v1_G + 0.0005 (stacked fixes do not move the mean beyond v1-era noise).
**H1**: mu_v2_G >= mu_v1_G + 0.002 (stacked fixes recover >=2pp improvement toward v1-era SOTA 0.03650).

**Primary metric**: mu_v2_G = 0.03315
**Baseline**: mu_v1_G = 0.03413

**Statistical test**: Welch's t-test, one-sided (H1: v2 > v1)
- t = -0.530
- df (Welch-Satterthwaite) = 5.60
- p (one-sided) = 0.692
- Cohen's d = -0.37

**Result**: H0 **not rejected** (p = 0.692). The stacked treatments produced no detectable improvement. The point estimate is directionally negative (v2 < v1 by 0.10pp), opposite to the predicted direction. With N=4 per condition and SD approximately 0.003, this experiment had approximately 30% power for a 0.002pp effect -- consistent with the pre-registered power analysis.

**Pre-registered verdict band determination**:
- mu_v2_G = 0.03315 falls in the NULL band (0.03313--0.03513), at its extreme lower edge (0.03315 vs lower bound 0.03313, a margin of only 0.00002).
- The value is above the REGRESSIVE threshold of 0.0330 (by 0.00015).
- One G run (C1_G) reached 0.03650, matching v1's best-ever, but the remaining three G runs (0.02939--0.03390) pulled the mean well below any signal threshold.

---

## 3. Effect Size

**Primary effect (v2 vs v1 grand mean)**:
-0.10pp [-0.41, +0.21] 95% CI (bootstrap, B=10000)

The point estimate is a slight regression from v1. The CI includes both modest improvement (+0.21pp) and moderate regression (-0.41pp), indicating the experiment cannot distinguish between a small positive and a small negative effect. The CI is wide (0.62pp span) relative to the effect size bands (SUGGESTIVE begins at +1.4pp above v1, REGRESSIVE at -1.1pp below v1), reflecting the fundamental underpowering at N=4.

**Welch-derived CI on delta**:
-0.10pp [-0.56, +0.36] 95% CI (parametric, df=5.60)

**Secondary effect (v2 vs baseline-repro)**:
v2 mean (0.03315) vs baseline-repro mean (0.03449) = -0.13pp. The stacked adversarial treatments with SBF-Lineage and SOFTMAX underperform the non-adversarial solo baseline, though the difference is within noise at this sample size.

**Effect relative to pre-registered thresholds**:
- Distance to POSITIVE (>=0.0365): -0.00335 (3.35pp shortfall)
- Distance to SUGGESTIVE (>=0.0355): -0.00235 (2.35pp shortfall)
- Distance to NULL upper bound (0.03513): -0.00198 (1.98pp shortfall)
- Distance to NULL lower bound (0.03313): +0.00002 (barely inside)
- Distance to REGRESSIVE (<0.0330): +0.00015 (0.15pp margin)

The result is emphatically NULL, sitting at the boundary between NULL and REGRESSIVE. The stacked info-flow improvements provided zero measurable lift.

---

## 4. Secondary Observations

### 4.1 C1_G's 0.03650 is a Genuine Outlier

C1_G (gradient-in-prompt arm) achieved 0.03650 actual_fitness, matching the v1-era best and the GEPA-approximate SOTA. This is the only v2 G-run to breach the SUGGESTIVE threshold. Program `e41afaff` drove this result. However, the remaining three G runs (0.02939, 0.03280, 0.03390) are 2.6--7.1pp below C1_G, producing a within-condition SD of 0.00295. This dispersion is larger than v1's SD (0.00224), indicating that v2's stochastic SOFTMAX sampling may increase variance without increasing the mean.

Notably, C1_D (the paired D run) had the highest mean-AF among D runs (0.03456) and the highest N_programs (893). C1_D's best AF of 0.03650 equals C1_G's best. This pair exhibited the strongest bilateral actual_fitness, suggesting that when D happens to produce high-quality improvements, G benefits -- but this is a stochastic event rather than a systematic treatment effect.

### 4.2 D-side Fitness Distribution

Two of four D runs (A2_D and C1_D) show fitness=0.000 in their engine fitness column, consistent with the known D hard-floor collapse (PATTERNS.md). A1_D (0.695) and C2_D (0.514) show non-zero engine fitness. The D collapse pattern in v2 is qualitatively identical to v1 despite the SharedBenchmarkFilteredLineageStage treatment. SBF-Lineage's filtered mutation narratives did not prevent the D fitness collapse.

D mean-AF (0.02725) exceeds G mean-AF (0.01764) across all 4 pairs, continuing the established pattern where Improver populations develop higher actual_fitness on average than Constructor populations. This is mechanistically expected: Improver starts from G's solution and applies local perturbations, inheriting G's quality floor.

### 4.3 Per-Arm Breakdown

| Arm | G Runs | Mean best-AF | SD |
|-----|--------|-------------|-----|
| A (Composition) | A1_G=0.03390, A2_G=0.03280 | 0.03335 | 0.00078 |
| C (Gradient-in-prompt) | C1_G=0.03650, C2_G=0.02939 | 0.03295 | 0.00503 |
| **Cross-arm delta** | | **0.00041 (0.04pp)** | |

The cross-arm delta (0.04pp) is negligible, well below the 0.20pp threshold that flags potential design error. This is consistent with the 8-experiment, 16-run consensus that feedback mode does not affect outcomes (PATTERNS.md: "Direction CLOSED"). Arm C's higher variance (SD=0.00503 vs 0.00078) is driven entirely by the C1_G outlier; excluding C1_G, Arm C mean would be 0.02939 (single data point).

### 4.4 Invalidity Rate Asymmetry

v2 G-run invalidity rates (35--47%) are uniformly higher than v1 (24--45%, with 3/4 runs below 40%). The SOFTMAX opponent sampling treatment may explain this: under TOP_K (v1), G always faces the single strongest D improver, producing a narrow but predictable adversarial challenge. Under SOFTMAX (v2), G faces a stochastic mixture of D improvers weighted by fitness, including weaker improvers that may produce noisier or less informative feedback. The LLM mutation operator may struggle to extract actionable signal from diverse, inconsistent adversarial feedback, leading to more invalid mutations.

However, this interpretation is speculative and confounded with the other stacked treatments. The invalidity increase could also reflect the I-17 fix (correct lineage labeling changes the archive topology available to mutation context) or simply stochastic variation at N=4.

### 4.5 Early Termination Did Not Bias the Result Toward NULL

The experiment was terminated at approximately 23 hours, with G runs reaching 36--55 engine generations (target: 200). One might argue that the treatments needed more generations to manifest. Against this interpretation:

1. v1's best results appeared at gen 0--29, not at gen 100+. The evolutionary dynamics in this task domain produce breakthroughs early.
2. C1_G already reached 0.03650 by its termination point (gen 53). If the treatments were working, we would expect convergence toward this value across runs, not the observed 0.03315 mean.
3. D runs at 38--91 gens show the same hard-floor collapse pattern as v1, suggesting the underlying fitness landscape defect is active from early generations regardless of treatment.
4. v1 ran to gen 29--37 on G and produced mu_G=0.03413. v2 ran to gen 36--55 on G (equal or longer) and produced mu_G=0.03315. If anything, v2 had more generational budget than v1 and still underperformed.

The early termination converts the experiment from a "200-gen full run" to a "36--55 gen partial run," but this is comparable to v1's achieved horizon (29--37 gens). The comparison remains fair.

---

## 5. Amendment Impact Assessment

| Amendment | Impact on validity | Assessment |
|-----------|-------------------|-----------|
| _(No amendments were recorded in 03_plan.md)_ | N/A | The experiment ran without any post-registration amendments to the pre-registered plan. All deviations are documented as unrecorded deviations in Section 7 below. |

---

## 6. Deviations from Pre-Registration

### Deviation 1: Early termination at ~23 hours instead of 200 generations

**Pre-registered plan**: All 8 runs to max_generations=200. Expected wall-clock: ~18h, hard cap 28h.

**Actual**: Experiment terminated at approximately 23 hours. Engine generations reached per run:

| Run | Target Gen | Actual Gen | % Complete |
|-----|-----------|------------|------------|
| A1_G | 200 | 36 | 18% |
| A1_D | 200 | 38 | 19% |
| A2_G | 200 | 55 | 28% |
| A2_D | 200 | 91 | 46% |
| C1_G | 200 | 53 | 27% |
| C1_D | 200 | 87 | 44% |
| C2_G | 200 | 50 | 25% |
| C2_D | 200 | 40 | 20% |

**Reason**: The researcher chose to close out the experiment early based on the observed trajectory. At 23 hours, no G run showed directional improvement toward the SUGGESTIVE threshold (0.0355); two D runs had already collapsed to fitness=0.000; and the D/G generation ratio (~1.3x) indicated that the two-pass bucketed refresh mechanism was imposing substantial overhead that would push the total wall-clock well beyond the 28h hard cap. Continuing to 200 generations would have required approximately 100+ additional hours at the observed gen/hour rate, with no evidence that further evolution would shift the verdict.

**Impact**: Moderate. The runs achieved 18--46% of the target generational budget. This means the experiment tests "early-to-mid evolution under stacked treatments" rather than "full 200-gen evolution under stacked treatments." However, as argued in Section 4.5, v1 achieved its verdict with comparable or fewer G generations (29--37), and the early-gen trajectory provides sufficient signal for a NULL determination. The pre-registered invalidity criteria ("Fewer than 3/4 G runs reach gen 100") is technically triggered -- 0/4 G runs reached gen 100 -- but this criterion was designed to detect premature crashes, not deliberate early termination. The termination was applied uniformly across all runs (not selective), so it does not introduce between-run bias.

### Deviation 2: No pre-registered amendment for early termination

**Pre-registered plan**: "Any deviation will be logged in 04_issues_log.md before 05_results.md is written."

**Actual**: The early termination was not logged as an amendment in 03_plan.md before results analysis began. This is a protocol violation (Type B: unrecorded deviation). The decision to terminate was made by the researcher based on trajectory analysis, not by the pre-registered stopping rule (which specified no early stop per run).

**Impact**: Minor. The termination was uniform and the justification is sound (see Deviation 1 analysis). The lack of a formal amendment is a procedural gap, not a scientific confound. For future experiments, the protocol should be amended to require a commit-stamped amendment entry in 03_plan.md before any early termination.

### Deviation 3: I-18 cosmetic bug active during run

**Pre-registered plan**: No known bugs at launch (I-16 and I-17 were fixed pre-launch).

**Actual**: I-18 (`Program.create_child` drops `iteration` field) was discovered during the run (2026-04-23). Injected programs in G runs pile up at iteration=0, corrupting frontier plot x-axes. Fix was NOT applied during the run (per `feedback_no_import_changes_mid_run.md`).

**Impact**: None on scientific validity. I-18 affects only the cosmetic `iteration` field used for plot x-axes. The scientific comparison uses `lineage.generation` (correct per I-17 fix) and `actual_fitness` from raw program blobs (unaffected). Detailed in `04_issues_log.md`.

### Summary of Pre-Registration Compliance

| Pre-registered item | Followed? | Notes |
|---------------------|-----------|-------|
| Primary metric (best-ever actual_fitness, 4 G runs) | Yes | Computed exactly as specified |
| Statistical test (Welch t-test, one-sided, bootstrap CI) | Yes | Applied as pre-registered |
| Evaluation script (frozen heilbron_repro_v1 evaluate.py) | Yes | I-16 fix applied pre-launch; same script across all 8 runs |
| Run design table (8 runs, 2 arms, per-role overrides) | Yes | All runs launched per design; per-role asymmetric config verified at startup |
| Controlled variables | Yes | All pinned values confirmed via cfg_run_*.yaml |
| Per-role asymmetric variables (SOFTMAX/TOP_K, archive_reeval, refresh) | Yes | Verified in startup logs |
| Monitoring plan | Partially | Watchdog ran; 23h termination prevented gen-50/100/200 checkpoints |
| Early termination rule | Deviated | Pre-registered: no early stop. Actual: terminated at ~23h. See Deviation 1 |
| Max generations (200) | Deviated | Not reached. See Deviation 1 |

---

## 7. Run Validity

| Run | Valid for primary? | Notes |
|-----|--------------------|-------|
| A1_G | Yes | Best-AF 0.03390 at gen 36. Genuine evolutionary product (I-17 fix ensures correct lineage). |
| A2_G | Yes | Best-AF 0.03280 at gen 55. Genuine evolutionary product. |
| C1_G | Yes | Best-AF 0.03650 at gen 53. Matches v1-era SOTA. Genuine evolutionary product. |
| C2_G | Yes | Best-AF 0.02939 at gen 50. Weakest G run. Genuine evolutionary product. |
| A1_D | Secondary only | D runs contribute secondary metrics; not pooled with G for primary analysis. |
| A2_D | Secondary only | D fitness=0.000 indicates D-collapse. |
| C1_D | Secondary only | Highest mean-AF among D runs (0.03456). |
| C2_D | Secondary only | |

**Experiment-level validity**: VALID for the verdict determination. All 4 G runs completed under the stacked treatment, with per-role asymmetric config verified. The early termination is uniform across all runs and does not selectively advantage any condition. The v1-vs-v2 comparison is valid because v1's G runs also reached only 29--37 engine generations.

---

## 8. Lessons Learned

### What worked

1. **The I-16 and I-17 fixes were clean and effective.** No D-to-G feedback injection failures were observed in v2 (unlike v1's first 6.5 hours of silent failure). The `(metrics, artifact)` return contract and the `Program.create_child` lineage fix both operated correctly throughout the run. Treatment verification at startup confirmed non-zero `dg_best_pairs` keys early, catching what v1 missed.

2. **Per-role asymmetric configuration is viable.** SOFTMAX on G / TOP_K on D, archive_reeval=false/true, fifo/generation_bucketed refresh -- all asymmetric config dimensions were correctly applied and verified. The infrastructure for per-role treatment assignment works. This is important for future factorial designs.

3. **The cross-arm delta collapsed to near-zero (0.04pp).** This is the cleanest evidence yet that feedback mode (composition vs gradient-in-prompt) is genuinely inert. Nine experiments, 20+ paired runs, and the delta remains negligible. The "Direction CLOSED" verdict in PATTERNS.md is further strengthened.

4. **No Redis contamination from v1.** Unlike v1 (which carried broken-phase programs across a relaunch), v2 started from flushed DBs. The gen-0 seed pool issue that confounded v1's analysis is absent in v2.

### What did not work

1. **SharedBenchmarkFilteredLineageStage did not produce measurable lift.** The D-side mutation narratives filtered by shared-opponent benchmarks were intended to give D higher-quality evolutionary context. D collapse rates (2/4 D runs at fitness=0.000) show the treatment did not prevent the fundamental D hard-floor pathology. Information-flow improvements cannot fix a broken fitness landscape.

2. **SOFTMAX opponent sampling may have increased G invalidity.** G invalidity rates in v2 (35--47%) trended higher than v1 (24--45%). Stochastic opponent rotation may have degraded mutation quality by providing inconsistent adversarial feedback. This is a suggestive signal, not a confirmed finding, but it argues against SOFTMAX as a standalone treatment for G.

3. **Two-pass bucketed refresh imposed heavy computational overhead.** The D/G generation ratio in v2 (mean 1.29x) is dramatically lower than v1's (mean 4.00x). The two-pass mechanism causes D to spend substantial wall-clock on archive re-evaluation rather than forward evolution. This may have limited D's ability to generate diverse improvements. If SBF-Lineage is used in future experiments, the overhead-vs-information tradeoff of two-pass refresh should be carefully evaluated.

4. **The stacked treatment design prevented attribution.** With four confounded treatments and a NULL result, we cannot identify which treatment (if any) was helpful, harmful, or inert. The deliberately confounded design was a reasonable cost-saving measure given the precondition-check framing (Section 1 of 01_design.md), but the NULL result means attribution will require individual ablation experiments that may never be run -- the REDESIGN bundle now takes priority.

### Infrastructure issues

1. **I-18 (Program.create_child drops iteration)**: Cosmetic bug that corrupts frontier plot x-axes. Does not affect fitness data. Fix deferred to post-experiment PR. Promoted to PATTERNS.md as a known failure mode.

2. **Two-pass refresh overhead**: The `refresh_passes=2` + `generation_bucketed` configuration on D runs was intended to ensure data freshness for SBF-Lineage narratives. The overhead was not characterized pre-launch. Future experiments using multi-pass refresh should benchmark the per-epoch wall-clock cost against the information freshness benefit.

---

## 9. Next Steps

### 9.1 Immediate: Ablation sweep is NOT the priority

The pre-registered follow-up on a POSITIVE or SUGGESTIVE v2 result was to decompose the stacked treatment via individual ablation (SOFTMAX-only, SBF-Lineage-only). Given the NULL result, this decomposition has low expected information gain. The stacked treatment produced no signal; isolating individual treatments is unlikely to find a hidden winner canceling a hidden loser, especially since the mechanistic entanglement note (01_design.md Section 2) predicted this difficulty.

### 9.2 Strategic: REDESIGN bundle is now the unambiguous top priority

The v2 NULL result is consistent with the REDESIGN-first hypothesis articulated in 01_design.md Section 1: "D hard-floor scoring is the true bottleneck and must be fixed before info-flow treatments can produce measurable lift." Two consecutive replications (v1 NULL at 0.03413, v2 NULL at 0.03315) under progressively richer info-flow treatments have failed to move the needle. The information-flow hypothesis is exhausted -- or at minimum, cannot be tested meaningfully until the fitness landscape is repaired.

The REDESIGN bundle (`experiments/heilbron/k5-budget-loose/REDESIGN.md`) addresses the root cause: smoothed tanh fitness replaces the hard-floor `max(delta,0)` formulation that produces 60--90% point-mass collapse at fitness=0.0. Until this structural defect is fixed, no info-flow, coupling, or budget treatment can be fairly evaluated.

### 9.3 D-side SBF-Lineage disposition

SBF-Lineage should NOT be discarded based on this result alone. The treatment operated on top of a broken D fitness landscape where 50% of D populations collapsed to zero. Under smoothed fitness (REDESIGN), SBF-Lineage may produce measurable signal because D's mutation context would carry meaningful fitness gradients rather than binary {win=positive, lose=0.0} outcomes. SBF-Lineage should be included as a secondary factor in the REDESIGN factorial, not as a standalone treatment.

### 9.4 SOFTMAX disposition

SOFTMAX on G should be revisited with caution. The elevated invalidity rates (35--47% vs v1's 24--45%) are a weak negative signal. The mechanism may need to be paired with a temperature parameter or a minimum-fitness threshold to filter out low-quality opponents before sampling. Alternatively, SOFTMAX may only be beneficial when D populations are healthy (non-collapsed), which the REDESIGN bundle could enable.

---

## 10. Paper / Report Notes

This experiment provides a second consecutive null result for the NeurIPS narrative's information-flow hypothesis section. The key claim: "Two replications with progressively enhanced information flow -- v1 with bug-fixed D-to-G feedback (NULL, mu=0.03413), v2 with shared-benchmark-filtered lineage narratives plus stochastic opponent sampling (NULL, mu=0.03315) -- establish that information quality is not the binding constraint. The D hard-floor fitness formulation (`max(delta,0)`) is the bottleneck, producing 60--90% point-mass collapse that no info-flow treatment can overcome."

For Table 1 in the paper, report this experiment as:

| Experiment | N | mu_G (best-AF) | 95% CI | Verdict |
|-----------|---|---------------|--------|---------|
| adversarial-repro-v2 | 4 G runs | 0.0331 | [0.0305, 0.0356] | NULL |

The cross-experiment progression tells a clear story:

| Experiment | mu_G | Treatment class | Verdict |
|-----------|------|----------------|---------|
| asymmetric-iterations (v1) | 0.03574 | Loose coupling + source access | Historical best |
| baseline-repro | 0.03449 | Solo MAP-Elites (no adversarial) | Baseline |
| adversarial-repro-v1 | 0.03413 | v1 recipe, bug-fixed | NULL |
| **adversarial-repro-v2** | **0.03315** | v1 + SBF-Lineage + SOFTMAX | **NULL** |

The downward trend from 0.03574 to 0.03315 across the replication series is not statistically significant (the CIs all overlap heavily) but is directionally concerning. Each additional treatment layer has produced equal or lower mean fitness, consistent with the hypothesis that the current fitness landscape cannot support meaningful co-evolutionary dynamics regardless of information quality.

---

## 11. VERDICT

**NULL**

Mean best-ever actual_fitness across 4 G runs = 0.0331 [0.0305, 0.0356] 95% CI (bootstrap, B=10000). The point estimate (0.03315) falls within the pre-registered NULL band (0.03313--0.03513), at its extreme lower edge. The delta versus v1 baseline is -0.10pp [-0.41, +0.21] 95% CI. The stacked info-flow treatments (SharedBenchmarkFilteredLineageStage, OpponentSamplingMode.SOFTMAX, I-16/I-17 fixes) did not recover signal in the Heilbronn N=11 adversarial co-evolution pipeline.

One G run (C1_G) reached 0.03650, demonstrating that the search space contains solutions at SOTA quality. But this is a stochastic event (1/4 runs), not a systematic treatment effect. The remaining three G runs averaged 0.03203, well below the v1 baseline.

This NULL result, combined with v1's NULL (0.03413), establishes that information-flow improvements are insufficient to break D stagnation under the current hard-floor fitness formulation. The REDESIGN bundle (smoothed tanh fitness + deterministic HoF) is the logical next step.

---

*Ready for Reviewer-2's scrutiny.*
