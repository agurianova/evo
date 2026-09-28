# Phase 2: Adversarial Review -- HoVer Co-Evolution Bus

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Date**: 2026-03-22
**Input**: `experiments/hover/co-evolution-bus/01_design.md`
**Round**: 1

---

## Summary of Design

This experiment tests whether a high-throughput "bus" co-evolution topology (3 main HoVer soft-fitness runs feeding 1 shared prompt meta-evolution run at ~24 trials/gen and 8 mutations/gen) improves test retrieval coverage beyond soft fitness alone (Cell C reference: 54.37%, n=2). This is the third prompt co-evolution experiment across two tasks, following two NULLs.

---

## Strengths

1. **The Preamble (Section 0) is exemplary.** Dr. Voss directly confronts the two prior NULLs, acknowledges the previous recommendation against further co-evolution experiments, and articulates a specific diagnostic hypothesis (throughput starvation) that differentiates this attempt from the prior two. The explicit statement "This is the last prompt co-evolution experiment I would recommend" pre-commits against indefinite hypothesis shifting.

2. **The independence caveat (Section 7, Confound #3, Confound #10) is handled with unusual honesty.** The design document explicitly states that the 3 treatment runs are NOT independent, that the t-test assumes independence anyway, that the effective sample size lies between n=1 and n=3, and that the effect-size threshold table is the primary decision criterion. The conservative n=1 analysis is pre-committed. This is the correct way to handle a design with known dependency.

3. **The trial throughput comparison table (Section 6)** provides clean cross-experiment context. The mechanism check (H1_mech) with explicit numeric thresholds (>30 trials, fitness gap >0.15) tied to prior benchmarks is well-calibrated.

4. **The 72-hour time-gate (Section 10)** converting B3 to a concurrent control if launch is delayed is a sensible contingency that protects historical-control validity.

5. **Appendix D (Treatment Verification Checklist)** is thorough and actionable. The gen-10 pause-and-diagnose trigger is a good safeguard against silent treatment failure.

---

## Methodological Concerns

| # | Concern | Severity | Section |
|---|---------|----------|---------|
| 1 | The "qualitative difference" question is unresolved | **Major** | 12 (OQ2) |
| 2 | Cell C reference has n=2 with unknown true SD | **Major** | 7, 8 |
| 3 | MDE calculation uses the wrong critical value for power | **Minor** | 7 |
| 4 | Host A contention is dismissed too readily | **Minor** | 9 (#2) |
| 5 | Prompt mutation diversity vs. trial dilution tradeoff is uncontrolled | **Major** | 12 (OQ2) |
| 6 | No pre-committed language for the correlation-adjusted interpretation | **Minor** | 8 |

### Concern 1: The experiment may not be qualitatively different from PR #84 (MAJOR)

Section 12, Open Question 2 states: "This COULD improve selection pressure (more diverse candidates) or COULD dilute trials per prompt (fewer trials per candidate)." This is not an open question to leave unresolved at design time -- it is the core scientific risk.

The HotpotQA 3+1 experiment (PR #84) had ~24 trials/gen and 5 mutations/gen, producing ~454 trials across 39 prompts (11.6 trials/prompt average). This experiment projects ~600 trials across 100-200 prompts (3-6 trials/prompt average). With min_trials=5, prompts averaging 3-6 trials will frequently NOT reach the fitness computation threshold. The max_elites=8 cap helps, but the first 5-10 generations will produce 40-80 prompts competing for 120-240 trials -- more dilute than PR #84.

**The net effect**: PR #84 achieved measurable prompt fitness differentiation (67-69% top evolved vs 48% seed) with 11.6 trials/prompt. This experiment may achieve LESS differentiation despite higher raw throughput, because trials are spread across 3-5x more candidates.

**Threat to validity**: If the result is NULL, it will be ambiguous whether the null reflects (a) prompt co-evolution genuinely not working, or (b) trial dilution from the 8 mutations/gen setting undermining prompt fitness estimation. The "definitive closure" claim (Section 2, cross-experiment meta-hypothesis) would be weakened.

**Recommendation**: Add a pre-committed diagnostic criterion. If the average trials-per-prompt at gen 25 is < 5 (below min_trials), report that the trial dilution failure mode was triggered and the null is NOT definitive for prompt co-evolution in general -- only for this specific throughput-to-diversity ratio. Alternatively, reduce max_mutations_per_generation for PM from 8 to 5 (matching PR #84) to isolate the topology/landscape change as the sole IV relative to PR #84.

### Concern 2: Cell C reference precision is fragile (MAJOR)

The entire statistical plan pivots on Cell C mean = 54.37% with SD = 0.99pp from n=2. Section 7 acknowledges that if true SD is 2.0pp, MDE doubles to ~4.3pp. This caveat is noted but not operationalized.

With n=2, the 95% CI for the Cell C population SD extends from approximately 0.50pp to infinity (chi-squared with df=1). The 0.99pp estimate is a single-degree-of-freedom estimate -- it is essentially uninformative about the true population variance. The design's MDE of 2.13pp is a best-case scenario that assumes the Cell C SD estimate is accurate. It could easily be 3-4pp if the true SD is 1.5-2.0pp.

**Threat to validity**: The power analysis creates false confidence. The experiment could easily be underpowered for the stated effect size threshold of 2.0pp.

**Recommendation**: (1) Explicitly state that the 2.13pp MDE is conditional on SD=0.99pp and should be treated as a lower bound on the true MDE. (2) Add a sensitivity table showing MDE at SD = 1.0, 1.5, 2.0, 2.5pp. (3) Pre-commit that interpretation relies on the effect-size threshold table (not p-value) when treatment SD > 2.0pp. This is partially done but should be more explicit.

### Concern 3: MDE calculation error (MINOR)

Section 7 computes: MDE = t(0.95, df~3) * SD * sqrt(1/n1 + 1/n2) = 2.353 * 0.99 * 0.913 = 2.13pp.

The critical value t(0.95, df~3) = 2.353 is for a one-sided test at alpha=0.05. For 80% power, the MDE formula for a two-sample t-test is: MDE = (t_alpha + t_beta) * SD * sqrt(1/n1 + 1/n2), where t_beta = t(0.80, df) ~ 0.978 for df=3. The correct formula gives MDE = (2.353 + 0.978) * 0.99 * 0.913 = 3.01pp.

The design document appears to have omitted the power term (t_beta), underestimating the MDE by approximately 40%. The true MDE at 80% power is closer to 3.0pp, not 2.1pp. This means the 2.0pp POSITIVE threshold is NOT achievable at 80% power with n1=3, n2=2 -- the experiment is underpowered for the stated criterion even under the optimistic SD=0.99pp assumption.

**Recommendation**: Correct the MDE formula. Acknowledge that the experiment is exploratory-powered for the 2.0pp threshold. Since the effect-size table is the primary decision criterion (not p < 0.05), this does not invalidate the design, but the claimed MDE-threshold match should not be overstated.

### Concern 4: Host A contention (MINOR)

Section 9, Confound #2 dismisses the shared-host concern: "NIC bottleneck unlikely for inference workloads." This is plausible but unverified. Two vLLM instances on the same host each generating 32768-token responses for 300-sample validation batches could saturate a 25Gbps NIC during parallel evaluation phases.

**Recommendation**: The mitigation (monitor gen wall time, flag if >30% slower) is adequate. Add a pre-launch bandwidth check: run a concurrent 2-instance throughput test on host A to verify no degradation vs single-instance. This is a minor issue because the treatment-vs-reference comparison is not affected (all treatment runs, no control on host A), but it affects the interpretability of inter-run variance.

### Concern 5: Prompt mutation diversity vs. trial dilution is an uncontrolled confound in the cross-experiment comparison (MAJOR)

This concern is related to Concern 1 but distinct. The design changes THREE parameters simultaneously relative to PR #84: (a) task (HoVer vs HotpotQA), (b) landscape (responsive vs flat), and (c) prompt mutations/gen (8 vs 5). Relative to PR #93, it changes: (a) topology (3+1 vs 1-to-1), (b) prompt mutations/gen (8 vs 2), (c) prompt max_elites (8 vs 5).

Section 3 claims "This is a single-factor experiment" with the IV being "mutation prompt source" (fixed vs co-evolved). This is correct within the experiment. But the "definitive closure" argument (Section 2, cross-experiment meta-hypothesis) requires that this experiment covers the remaining parameter space. If it fails, one could argue that 5 mutations/gen on HoVer's responsive landscape was never tested -- only 2 (PR #93, too few) and 8 (this experiment, potentially too many/dilute).

**Threat to validity**: The cross-experiment grid (Section 12, Open Question 3) has gaps that a null result would not fully close. Specifically, the combination (3+1 topology, 5 mutations/gen, responsive landscape) remains untested.

**Recommendation**: Acknowledge this gap explicitly in Section 12, OQ3. If the result is NULL AND the trial-dilution diagnostic from Concern 1 is triggered (avg trials/prompt < 5), state that one parameter combination (3+1, 5 mut/gen, responsive) remains untested but is not recommended for investigation given the weight of null evidence across three experiments. This is about honest reporting, not about adding more runs.

### Concern 6: Pre-committed language for correlation-adjusted interpretation (MINOR)

Section 8, Test 1 pre-commits a conservative n=1 analysis. Good. But the document does not pre-commit language for the intermediate case: what if inter-run SD is 0.5-1.0pp (partially correlated)? There is no framework for adjusting the effective n between 1 and 3.

**Recommendation**: Add a sentence: "If inter-run SD is < 0.5pp, the conservative n=1 analysis is primary. If inter-run SD is >= 1.0pp (comparable to Cell C SD), the n=3 analysis is primary. For intermediate values, report both and interpret conservatively." This bounds the interpretation space.

---

## Hypothesis and Falsifiability

- [x] H0 is clearly stated (mu_bus <= 54.37%)
- [x] H1 is falsifiable and directional (>= 56.37%)
- [x] Primary metric is pre-specified (test retrieval coverage, discrete, 300-sample, 5 repeats)
- [x] Success criteria are numeric and unambiguous (effect-size threshold table)

**Notes**: The threshold table is well-designed with five distinct verdict bands. The INCONCLUSIVE band (2 of 3 runs >= 56.37%) appropriately avoids forcing a binary verdict on mixed results. The cross-experiment meta-hypothesis (Section 2) is a valuable pre-commitment that bounds the research line regardless of outcome. H1_mech thresholds (>30 trials, gap >0.15) are well-calibrated against PR #93 benchmarks.

---

## Confound Analysis

- [x] Controlled variables genuinely controlled (Section 5 is comprehensive)
- [ ] IV isolated -- **PARTIAL**: single IV within this experiment, but cross-experiment comparison confounds multiple factors (Concern 5)
- [x] Known confounds mitigated or acknowledged (11 confounds, all with mitigations)
- [x] Val/test split not contaminated (discrete test scoring, soft val scoring -- correctly separated)

**Unaddressed confounds**:

1. **Prompt mutation rate as implicit IV**: 8 mutations/gen is not just "higher throughput" -- it changes the selection-diversity tradeoff in the prompt archive. This is acknowledged in OQ2 but not elevated to confound status. It should be Confound #12.

2. **Temporal coupling between PM and main runs**: If PM's champion changes mid-generation for a main run, different mutations within the same generation may use different prompts. This is a feature (per-mutation sampling), not a bug, but it means that "prompt source = co-evolved" is not a stable treatment -- it is a time-varying treatment. Cell C's "fixed prompts" provide a stable mutation signal. The temporal instability of the bus treatment could introduce noise that masks a genuine signal. This is distinct from Confound #3 (shared PM) and should be acknowledged.

---

## Statistical Validity

- [x] Sample size justified (n=3, with honest acknowledgment of n~1 effective)
- [ ] Statistical test appropriate -- **PARTIAL**: Welch's t-test assumes independence; the conservative n=1 analysis is the honest test but has zero power (acknowledged)
- [x] Significance threshold pre-specified (alpha=0.05 one-sided, effect-size table primary)
- [x] Multiple comparison correction applied if needed (Tests 2-4 labeled exploratory; Test 1 owns alpha=0.05)

**Notes**: The MDE calculation contains an error (Concern 3). The statistical plan is fundamentally sound in that it subordinates p-values to the effect-size threshold table, which does not depend on the independence assumption. This is the right call for this design. The pre-committed n=1 conservative analysis is an unusual and commendable safeguard.

---

## Evaluation Protocol

- [x] Metric computed identically across conditions (discrete test scoring for all)
- [x] Val/test sets fixed and identical for all runs (300-sample each, same as Cell C)
- [x] No post-hoc metric selection (pre-specified in Section 4)
- [x] Thinking mode consistent across evaluations (Qwen3-8B, thinking ON, all conditions)

**Notes**: The val metric (soft) differs from the test metric (discrete), which is appropriate and correctly documented. Port parity check (Confound #11) covers the chain LLM configuration consistency. The pre-launch `--cfg job` verification (Appendix A, item 3) is comprehensive.

---

## Required Changes Before Approval

1. **[Major, Concern 1]**: Add a pre-committed diagnostic criterion for trial dilution. Specifically: report average trials-per-prompt at gen 25. If average < 5 (below min_trials), acknowledge that the "definitive closure" claim is weakened by the trial dilution failure mode. Either (a) add this language to Section 2's cross-experiment meta-hypothesis, or (b) reduce PM's max_mutations_per_generation from 8 to 5 to match PR #84 and isolate the landscape/task change as the comparison dimension.

2. **[Major, Concern 2]**: Add a sensitivity table for MDE at SD = 1.0, 1.5, 2.0, 2.5pp to Section 7. Pre-commit that interpretation relies on the effect-size threshold table (not p-value) when treatment SD > 2.0pp.

3. **[Major, Concern 5]**: Add Confound #12: "Prompt mutation rate (8/gen) as implicit second IV relative to cross-experiment comparisons." Acknowledge in Section 12, OQ3 that the combination (3+1, 5 mut/gen, responsive landscape) remains untested. State explicitly whether this gap weakens or does not weaken the "definitive closure" conclusion.

4. **[Minor, Concern 3]**: Correct the MDE formula to include the power term (t_alpha + t_beta). Report the corrected MDE (~3.0pp at 80% power). Acknowledge that the experiment is exploratory-powered relative to the 2.0pp threshold.

---

## Verdict

**[x] APPROVED** (Round 2, after revision)

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Round 2 notes (2026-03-22)**: All 4 required changes addressed in revised 01_design.md:
1. Trial dilution diagnostic pre-committed in Section 2 cross-experiment meta-hypothesis
2. MDE sensitivity table added to Section 7 (SD = 1.0, 1.5, 2.0, 2.5pp)
3. Confound #12 (mutation rate) and #13 (temporal coupling) added to Section 9
4. MDE formula corrected to 3.01pp (includes t_beta power term)

**Round 1 reviewer notes**:

This is a carefully constructed design document -- one of the best I have reviewed in this research program. The scientific motivation is honest, the prior evidence is confronted directly, and the statistical limitations are acknowledged rather than buried. The independence caveat alone elevates this above most designs I see.

The three major concerns (trial dilution ambiguity, reference SD fragility, cross-experiment confounding) are all addressable with language changes and pre-commitments. None requires redesign. The core architecture -- 3+1 bus on a responsive landscape with an explicit closure commitment -- is sound.

My primary worry is that a null result from this design will be claimed as "definitive" when the 8 mutations/gen setting introduces a trial dilution confound that was not present in PR #84. If the design pre-commits diagnostic language for this scenario, the interpretation space is properly bounded regardless of outcome.

I note that Dr. Voss's own assessment (OQ2: "MEDIUM-HIGH risk, most likely outcome remains NULL") is appropriately calibrated. The experiment is worth running as a closure experiment -- but only if the closure claim is honestly scoped.

*The science demands nothing less.*

---

**Severity summary**: 3 Major, 3 Minor. No Critical.
