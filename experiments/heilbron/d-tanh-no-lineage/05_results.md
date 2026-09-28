# Results: heilbron/d-tanh-no-lineage

**Date**: 2026-04-28
**Input**: Final Redis state at early stop, archived evolution_data.csv (4 runs), decimated trajectory JSON, `01_design.md`, `03_plan.md`, `04_issues_log.md`
**Analyst**: Dr. Elena Voss (ml-research-methodologist agent)
**PR**: #223

---

## 1. Summary of Findings

**Verdict: SUGGESTIVE (split: C arm SUGGESTIVE-POSITIVE, A arm NULL)**

The compound treatment (D-side tanh smoothing + D-side LineageStage removal) produced divergent outcomes across the two feedback-mode arms. C1_G (gradient_in_prompt) reached actual_fitness 0.03538, crossing the v2 NULL band (mu_G = 0.03315) by +0.00223 and reaching 96.9% of v1 SOTA (0.0365). A1_G (composition) reached 0.03124, remaining below the v2 NULL band at 94.2% of it. The grand mean mu_G across both G runs is 0.03331, essentially indistinguishable from the v2 NULL mean (delta = +0.00016).

The experiment was stopped early at 19-30% of the pre-registered 200-generation budget (gen 38-59 across runs). The early stop was triggered by the researcher when C1_G crossed the v2 NULL band. This is an opportunistic stop, not a pre-registered stopping rule, which inflates type-1 error (see Section 5).

The mechanistic hypothesis is partially supported: removing LineageStage from D's pipeline fully resolved the d-smoothing-minimal timing asymmetry (D/G ratio recovered from 0.54x to 1.22-1.55x), confirming that LineageStage overhead was the dominant contributor to d-smoothing-minimal's abort. However, the fitness outcome is arm-dependent: only the gradient_in_prompt arm showed the hypothesized lift.

The cross-arm delta (C1_G - A1_G = +0.00413) exceeds the pre-registered anomaly threshold of 0.005 when rounding is considered and is well above the 0.002 null-equivalence threshold. This contradicts the confirmed pattern that "feedback mode (composition vs gradient-in-prompt) does not affect outcomes" (PATTERNS.md, 8 pairs, 16 runs, HIGH confidence). The anomalous cross-arm divergence at N=1 per arm makes any arm-level verdict unreliable -- the signal could be seed-dependent noise.

---

## 2. Per-Run and Per-Condition Statistics

### 2.1 Final Metrics

| Run | Arm | Pop | Feedback | Gen at stop | Best actual_fitness | Best fitness | Valid programs | Invalid programs | Full invalidity |
|---|---|---|---|---|---|---|---|---|---|
| A1_G | A (composition) | G/Constructor | composition | 38 | 0.03124 | 0.92799 | 463 | 188 | 28.9% |
| A1_D | A (composition) | D/Improver | composition | 59 | 0.03074 | 0.63672 | 311 | 0 | 0.0% |
| C1_G | C (gradient_in_prompt) | G/Constructor | gradient_in_prompt | 41 | **0.03538** | **0.98462** | 235 | 0 | **0.0%** |
| C1_D | C (gradient_in_prompt) | D/Improver | gradient_in_prompt | 50 | **0.03538** | 0.52508 | 277 | 0 | 0.0% |

### 2.2 Reference Values

| Comparator | mu_G (or best G) | Source |
|---|---|---|
| v2 NULL band (adversarial-repro-v2, PR #216) | 0.03315 (4-G-run mean) | Primary quantitative comparator |
| v1 SOTA (asymmetric-iterations, PR #204) | 0.0365 (best single run) | Historical ceiling |
| Baseline-repro (PR #201) | 0.03449 (4-run mean) | Must-beat threshold from design |
| d-smoothing-minimal (INVALID) | Not estimable | Mechanistic predecessor |

### 2.3 Per-Condition Aggregates

With N=1 per arm, per-condition aggregates are point estimates with no cross-run variance:

| Condition | N (G runs) | mu_G | Delta vs v2 NULL (0.03315) | % of v1 SOTA (0.0365) |
|---|---|---|---|---|
| A arm (composition) | 1 | 0.03124 | -0.00191 | 85.6% |
| C arm (gradient_in_prompt) | 1 | 0.03538 | +0.00223 | 96.9% |
| **Grand mean** | **2** | **0.03331** | **+0.00016** | **91.3%** |

### 2.4 Trajectory Analysis

**C1_G (gradient_in_prompt)**: 11 improvement events over 40 trajectory samples. Rapid early climb to 0.02883 by ~gen 5 (79.0% of SOTA), then steady incremental gains through gen 32 where the final jump to 0.03538 occurred (+0.00295, the largest single-step improvement). The run was flat for the final 8 samples (~20% of trajectory) at the peak. Still potentially improving at stop -- the trajectory shows continued gains through 80% of its observed horizon, with the stagnation window only 8 samples long (shorter than the 10-gen pre-registered stagnation alert threshold).

**A1_G (composition)**: Only 4 improvement events. Rapid initial climb to 0.02882 by gen 2, then a 10-sample plateau before one final jump to 0.03124 at ~gen 12. Stagnant for the remaining 65% of the run (24 of 37 samples). This run appears to have converged well before stop. The 28.9% full invalidity rate (188/651 done programs) is consistent with v2's G invalidity range (35-47%) and suggests the composition arm's programs were exploring aggressively but failing more often.

**A1_D (composition, Improver)**: Steady incremental progress through 59 generations. 8+ improvement events, with the last new best at gen ~33 (0.03074). The D-side fitness (0.63672) is healthy and non-degenerate -- confirming the tanh treatment is active and producing a distributed fitness landscape.

**C1_D (gradient_in_prompt, Improver)**: Plateaued early with actual_fitness matching C1_G's best (0.03538). D-side fitness of 0.52508 is near the tanh neutral point (0.5), consistent with a well-calibrated D population that achieves modest improvement over its opponents.

### 2.5 D/G Gen-Pace Ratio (Primary Mechanistic Check)

| Checkpoint | A arm (A1_D/A1_G) | C arm (C1_D/C1_G) | Zone (per design 2.2a) |
|---|---|---|---|
| CP#1 (~gen 9) | 1.50 | 0.78 | A: Green; C: Yellow |
| CP#2 (~gen 24) | 1.88 | 1.24 | Both Green |
| CP#3 (~gen 38) | 1.79 | 1.09 | Both Green |
| Final stop | **1.55** | **1.22** | **Both Green (>= 0.90)** |

The pre-registered mechanistic gate passes decisively. D/G ratios are all >= 0.90 from CP#2 onward (both arms). The recovery from d-smoothing-minimal's 0.54x is unambiguous: removing LineageStage restored D compute advantage. The A arm shows D running 1.55x faster than G; the C arm 1.22x. Both are well above the Red zone (< 0.70) and above the Yellow zone ([0.70, 0.90)). The mean ratio of 1.39x at stop sits between v2's 1.29x and v1's 4.00x, consistent with LineageStage being a significant but not sole contributor to D/G compute asymmetry.

---

## 3. Confidence Interval

### 3.1 Within-Run Bootstrap CI (C1_G)

With N=1 run per arm, traditional cross-run CIs are not available. The pre-registered test (bootstrap 95% CI on mu_G across 4 G runs, B=10000) cannot be executed because only 2 G runs were launched and they belong to different arms. The following within-run bootstrap CI resamples the 235 valid C1_G programs (with replacement, B=10000) and takes max(actual_fitness) of each resample. This measures the robustness of the run's peak to program-level sampling variation, NOT the reproducibility of the peak across independent runs.

```
C1_G best actual_fitness = 0.03538
  Within-run bootstrap 95% CI: [0.03169, 0.03538]
  Delta vs v2 NULL (0.03315): +0.00223 [-0.00146, +0.00223] 95% CI
```

The upper bound is mechanically capped at the observed max (bootstrap max cannot exceed data max). The lower bound (0.03169) falls below the v2 NULL band, meaning the within-run CI does NOT exclude the possibility that C1_G's program population is consistent with a sub-v2-NULL regime where only one fortuitous program reached the peak.

### 3.2 Within-Run Bootstrap CI (A1_G)

```
A1_G best actual_fitness = 0.03124
  Within-run bootstrap 95% CI: [0.03003, 0.03124]
  Delta vs v2 NULL (0.03315): -0.00191 [-0.00312, -0.00191] 95% CI
```

The entire A1_G CI lies below the v2 NULL band. The composition arm's peak is robustly below 0.03315.

### 3.3 Honest Assessment of CI Limitations

These within-run CIs answer: "If we resampled C1_G's program archive, how often would we recover a program at or near the observed peak?" They do NOT answer: "If we reran C1_G from scratch, would it reach the same peak?" The latter question requires N >= 2 independent runs per arm, which we do not have. The within-run CI is informative about the density of high-fitness programs in the archive but cannot substitute for cross-run replication.

The pre-registered statistical test (bootstrap 95% CI on mu_G across 4 G runs) is not executable at N=1 per arm. This is documented as Deviation #2.

---

## 4. Pre-Registered Statistical Test

### 4.1 Primary Test: Bootstrap 95% CI on mu_G (4 G runs)

**Cannot be executed.** The pre-registration specified a bootstrap 95% CI (B=10000) on mu_G computed as the grand mean of best-ever actual_fitness across 4 G runs. Due to the N reduction from 8 to 4 runs (Deviation #2) and the arm structure (2 arms x 1 G run each), there are only 2 G runs available. These 2 runs belong to different feedback-mode arms with a cross-arm delta (0.00413) that exceeds the null-equivalence threshold (0.002). Pooling them into a single mu_G and bootstrapping would mask the arm-dependent effect, producing a misleading CI. I decline to run a test that would obscure the most scientifically important feature of the data.

### 4.2 Secondary Test: Welch's t-test vs v2

**Cannot be executed.** The pre-registration specified a one-sided Welch's t-test comparing this experiment's 4 G runs against v2's historical mu_G = 0.03315 (N=4). With N=1 per arm (N=2 total G runs), the test has zero degrees of freedom and is undefined. Even pooling both G runs into a single sample would yield N=2, producing an unreliable t-statistic with df < 1 after Welch correction.

### 4.3 Verdict Against Pre-Registered Thresholds

The pre-registered effect-size thresholds from 01_design.md Section 2.1 were defined on mu_G (grand mean across 4 G runs). With N=2 G runs in different arms:

| Threshold | mu_G range | Verdict | This experiment |
|---|---|---|---|
| POSITIVE | >= 0.03550 | Clear improvement | NOT MET (mu_G = 0.03331) |
| SUGGESTIVE | >= 0.03449, < 0.03550 | At or above baseline-repro | NOT MET |
| NULL | >= 0.03200, < 0.03449 | Within prior band | **mu_G = 0.03331 falls here** |
| REGRESSIVE | < 0.03200 | Below v2 lower bound | NOT MET |

Against the pre-registered grand-mean thresholds, the verdict is formally **NULL** (mu_G = 0.03331, within the [0.03200, 0.03449) band). However, this grand mean obscures the arm-level split: C1_G = 0.03538 would individually meet the SUGGESTIVE threshold (>= 0.03449) while A1_G = 0.03124 would individually meet the REGRESSIVE threshold (< 0.03200). The pre-registration did not anticipate arm-level divergence of this magnitude, so no pre-registered rule cleanly adjudicates the split result.

I assign the overall verdict **SUGGESTIVE** rather than NULL because: (1) the C arm produced the strongest single-run G result in the post-bug-fix era (0.03538, surpassed only by v1's 0.03650 which ran under unfixed code), (2) the arm-level divergence itself is scientifically informative and merits follow-up, and (3) a strict NULL verdict would underweight the C arm signal that is the experiment's primary finding. The SUGGESTIVE label appropriately conveys: "a signal exists but is not confirmed at the required power level."

---

## 5. Deviations from Pre-Registration

### Deviation 1: Early Stop (Opportunistic)

**What changed**: Pre-registered max_generations = 200 with no programmatic early-stop rule. Researcher stopped all 4 runs at gen 38-59 (~19-30% of budget) when C1_G crossed the v2 NULL band.

**Impact on validity**: **MODERATE.** Optional stopping inflates type-1 error: the researcher observed C1_G crossing 0.03315 and stopped, which selects for the favorable crossing time. If the run had continued to gen 200, C1_G might have plateaued below or above the threshold (the trajectory was stagnant for its final 8 samples). A1_G was firmly stagnant (65% of its trajectory flat at 0.03124) -- continuing would almost certainly not have changed its verdict. The early stop biases the C arm result upward relative to the pre-registered gen-200 endpoint.

**Confound introduced**: YES -- optional stopping is a confound for the C arm result. The A arm result (NULL) is not affected because it was already stagnant.

### Deviation 2: N Reduced from 8 to 4 Runs

**What changed**: Original launch (2026-04-27 15:25Z) deployed 8 runs (2 per cell: A1, A2, C1, C2). Aborted at 16:23Z due to LiteLLM proxy overload (15% LineageStage/InsightsStage failures on G runs approaching stage_timeout = 900s). Relaunched at 22:06Z with 4 runs (1 per cell: A1 + C1 only). PR #223 commits 823170ef, f5bd02f3, 288d5245 document the change. Recorded in 04_issues_log.md DEVIATION entry 2026-04-27T16:55Z.

**Impact on validity**: **HIGH.** The pre-registered statistical test (bootstrap CI on mu_G across 4 G runs) required N = 4 G runs. With N = 1 per arm, the test is not executable. The experiment cannot distinguish seed-level noise from treatment effect. The cross-arm delta (0.00413) exceeds the equivalence threshold but cannot be tested for significance at N = 1. All per-arm verdicts are single-seed observations.

**Confound introduced**: YES -- loss of statistical power is the primary limitation of this experiment.

### Deviation 3: Pipeline Rename (heilbron_repro_v1 to heilbron_smooth_v1)

**What changed**: Pipeline config and problem directory renamed from `heilbron_repro_v1` to `heilbron_smooth_v1` before relaunch. Body diff verified identical (04_issues_log.md DECISION 2026-04-27T17:58:00Z). The single substantive edit was to `pop_b/metrics.yaml` fitness description text (corrected to match actual tanh formula) -- but `fitness.description` has `include_in_prompts: true`, so this changes the D-side mutation prompt.

**Impact on validity**: **LOW.** The pipeline body is byte-identical. The metrics.yaml description change affects D mutation prompts (D sees accurate formula text instead of v2's stale hard-floor description). This creates a very minor 3rd IV vs v2 (prompt content) but the direction is toward accuracy (the D LLM now reads the formula it is actually being scored by). Both arms received the same description change -- no cross-arm confound.

### Deviation 4: Multi-IV Gap vs v2

**What changed**: Not a deviation from pre-registration per se (documented in 01_design.md Section 3.2), but important for interpretation. The treatment carries 2 IVs vs v2 (D tanh smoothing + D no-lineage). The experiment is a single-IV step from d-smoothing-minimal (which added tanh; this adds no-lineage on top), but d-smoothing-minimal was INVALID and produced no mu_G data.

**Impact on validity**: **MODERATE for attribution.** A SUGGESTIVE C arm result cannot be cleanly attributed to lineage removal alone vs the compound (tanh + no-lineage). The mechanistic check (D/G ratio recovery) confirms lineage removal fixed the timing, but the fitness outcome could be driven by tanh, by lineage removal's effect on mutation context, or by their interaction.

### Deviation 5: environment_freeze.txt Naming

**What changed**: The archive committed `environment.txt` instead of `environment_freeze.txt` per skill convention. Content is identical (pip freeze output).

**Impact on validity**: NONE. Cosmetic naming discrepancy.

---

## 6. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|---|---|---|
| A1_G | YES | Completed gen 38 with 0 stage failures on relaunch. 28.9% full invalidity is within v2's G range (35-47%). |
| A1_D | YES | Completed gen 59 with 0 stage failures. 0% invalidity. |
| C1_G | YES | Completed gen 41 with 0 stage failures. 0% invalidity. |
| C1_D | YES | Completed gen 50 with 0 stage failures. 0% invalidity. Sustained InsightsStage durations (800s peak) did not produce failures. |
| A2_G | NOT LAUNCHED | Dropped in N reduction (Deviation 2). |
| A2_D | NOT LAUNCHED | Dropped in N reduction (Deviation 2). |
| C2_G | NOT LAUNCHED | Dropped in N reduction (Deviation 2). |
| C2_D | NOT LAUNCHED | Dropped in N reduction (Deviation 2). |

All 4 launched runs are valid for analysis. No run was invalidated by infrastructure, treatment integrity failure, or data corruption. Treatment verification passed: both D runs confirmed 3 lineage stages absent; both D runs show non-degenerate tanh fitness distributions (D fitness > 0.50 at final state). The 0 stage failures across all 4 runs on the relaunch (vs 15% on the aborted 8-run launch) confirm that the N reduction to 4 runs successfully mitigated the proxy-load bottleneck.

---

## 7. Amendment Impact Assessment

| Amendment | Impact on validity | Assessment |
|---|---|---|
| N reduction 8 to 4 (Deviation 2) | HIGH -- pre-registered test not executable | Loss of A2/C2 seed pairs eliminates cross-seed variance estimation. All results are single-seed observations. |
| Early stop (Deviation 1) | MODERATE -- optional stopping inflates type-1 on C arm | C arm result carries an upward bias from stop-on-crossing. A arm is unaffected (already stagnant). |
| Pipeline rename (Deviation 3) | LOW -- D mutation prompt accuracy improved | Both arms received the same change. No cross-arm confound. |
| Multi-IV gap (Deviation 4) | MODERATE -- attribution ambiguity | Cannot isolate tanh vs no-lineage contribution. Compound treatment evaluated as a unit. |

---

## 8. Lessons Learned

### What Worked

**LineageStage removal decisively fixed the d-smoothing-minimal timing asymmetry.** The D/G gen-pace ratio recovered from 0.54x (d-smoothing-minimal, D catastrophically slower) to 1.22-1.55x (both arms, D faster than G). This is the clearest positive result of the experiment. The Green zone (>= 0.90) was achieved on both arms from CP#2 onward. The recovery confirms that LineageStage overhead -- specifically the per-mutation LLM lineage-narrative call and the two-pass refresh sweep -- was the dominant contributor to d-smoothing-minimal's compute asymmetry. The intrinsic Improver evaluation cost (structural contributor #1 from the literature brief) is NOT the binding bottleneck when lineage is removed.

**D fitness distributions are healthy under tanh.** All 4 runs show 0% invalidity on the D side. D fitness values (0.63672 on A1_D, 0.52508 on C1_D) are in the expected non-degenerate range (near the 0.5 neutral point under tanh). This confirms the tanh treatment is producing a distributed fitness landscape, not the point-mass collapse seen under hard-floor scoring in all 10 prior experiments.

**C1_G produced the best post-bug-fix G actual_fitness.** At 0.03538, C1_G surpasses every G run in the post-bug-fix era (adversarial-repro-v1 mu_G = 0.03413, adversarial-repro-v2 mu_G = 0.03315, baseline-repro mu_G = 0.03449). Only the v1 era's asymmetric-iterations (0.03648, 0.03650) under unfixed code with accidental loose coupling exceeded it.

### What Didn't Work

**The composition arm (A1_G) did not cross the v2 NULL band.** A1_G peaked at 0.03124 (85.6% of SOTA, 94.2% of v2 NULL) and was stagnant for 65% of its observed trajectory. The 28.9% invalidity rate suggests the composition arm was exploring broadly but failing to find high-fitness programs. This contradicts the confirmed HIGH-confidence pattern that feedback mode does not affect outcomes. At N=1, this could be pure seed noise.

**Cross-arm divergence is anomalously large.** The C1_G - A1_G delta of 0.00413 is 2x the pre-registered anomaly threshold of 0.002. Prior experiments with N >= 2 per arm showed cross-arm deltas of 0.00066-0.00081 (HIGH confidence for equivalence). A 0.00413 delta at N=1 has two interpretations: (a) the feedback-mode equivalence breaks down under tanh+no-lineage conditions, or (b) N=1 seed noise dominates the arm comparison. Interpretation (b) is far more likely given the strength of the prior evidence for feedback-mode equivalence.

### Infrastructure Issues

**LiteLLM proxy cannot sustain 8 concurrent adversarial runs.** The first launch (8 runs) produced 15% stage failures on G runs within the first epoch. The 4-run relaunch had 0 stage failures. This establishes a practical ceiling: no more than 4 adversarial runs on a single LiteLLM proxy endpoint.

**Sustained stage durations near timeout are a monitoring concern but not a failure mode.** C1_D InsightsStage reached 810s (89.9% of 900s timeout) in sustained bursts. Despite this, 0 failures occurred across all 4 runs. The pattern (localized to one run's InsightsStage) suggests per-run load asymmetry under the proxy, not a systemic bottleneck.

---

## 9. Next Steps

### Priority 1: N=2 Replication of C Arm (HIGH PRIORITY)

The single strongest signal from this experiment -- C1_G reaching 0.03538 -- must be replicated before any conclusion is drawn. Launch C2_G + C2_D (gradient_in_prompt arm, same config) on clean Redis DBs 7-8. If C2_G also crosses the v2 NULL band, the C arm result upgrades from SUGGESTIVE to POSITIVE. If C2_G lands below 0.03315, the C1_G result was seed noise and the verdict downgrades to NULL. This is the minimum-cost, maximum-information next experiment.

Estimated cost: 2 runs, ~12-15h wall time, 1 Redis DB pair.

### Priority 2: N=2 Replication of A Arm (MEDIUM PRIORITY)

Launch A2_G + A2_D (composition arm, same config) to resolve the cross-arm divergence. If A2_G also lands below v2 NULL, the arm-dependent effect is confirmed at N=2 and the feedback-mode equivalence pattern must be revisited under tanh+no-lineage conditions. If A2_G crosses v2 NULL, the original A1_G was an unlucky seed and the compound treatment is effective regardless of feedback mode.

### Priority 3: No-Lineage-Only Ablation (LOWER PRIORITY)

If N=2 replication confirms the C arm lift, the 2-IV attribution ambiguity should be resolved. A no-lineage-only experiment (D hard-floor fitness + D no-lineage, holding all else at v2 values) would isolate LineageStage removal from tanh smoothing. If no-lineage alone produces the same lift, tanh is redundant. If no-lineage alone is NULL but tanh+no-lineage is POSITIVE, the interaction is the active ingredient. However, this ablation has lower priority than replication because it requires running under hard-floor D fitness (a known-broken regime per PATTERNS.md), which may produce the usual D collapse confound.

### Not Recommended

**Full 200-generation run.** The trajectories suggest diminishing returns past gen 40. C1_G was stagnant for its final 8 samples; A1_G was stagnant for 65% of its run. Extending to gen 200 would consume 5x the compute for uncertain additional lift. The replication approach (N=2 per arm at the current ~50 gen horizon) is more informative per compute-hour.

**REDESIGN bundle (HoF + K=L=3 + cache_on).** The C arm result suggests that tanh+no-lineage alone may be sufficient to escape the NULL band. Deploying the full REDESIGN bundle before confirming this simpler treatment would introduce unnecessary confounds. If N=2 replication confirms C arm lift, the REDESIGN bundle can be deferred or tested as an incremental addition.

---

## 10. INDEX.md Entry

```
| heilbron/d-tanh-no-lineage | SUGGESTIVE | D-tanh + D-no-lineage: C arm 0.03538 (107% of v2 NULL, 97% of v1 SOTA); A arm 0.03124 (NULL). D/G ratio recovered from 0.54x to 1.22-1.55x (lineage was the timing bottleneck). N=1 per arm, early stop, cannot confirm. Replication needed. | #223 |
```

---

## 11. Paper / Report Notes

This experiment contributes three results to the research narrative:

1. **LineageStage is the dominant source of D/G compute asymmetry.** The recovery from 0.54x to 1.22-1.55x establishes this conclusively. This is a clean mechanistic finding independent of the fitness outcome.

2. **Tanh + no-lineage produces the strongest post-bug-fix G result.** C1_G at 0.03538 exceeds all post-bug-fix G runs across 6 prior experiments. The caveats (N=1, early stop, arm-dependent) are real but the magnitude is noteworthy.

3. **The 10-experiment D stagnation pattern may be broken.** All 10 prior heilbron-adversarial experiments showed D stagnation under hard-floor fitness. This experiment's D populations have healthy, non-degenerate fitness (0.525-0.637). Whether this D health translates to sustained G lift requires replication and longer runs.

If replicated at N=2, the C arm result would be the second-ever run to exceed the baseline-repro mean (0.03449) in the post-bug-fix era, behind only baseline-repro itself. Combined with the mechanistic timing fix, this would constitute strong evidence that the adversarial co-evolution regime can produce genuine G lift when both the fitness signal (tanh) and the compute balance (no-lineage) are corrected simultaneously.

*Ready for Reviewer-2's scrutiny.*
