# Adversarial Review: P3 Crossover (num_parents=2) for HotpotQA Static Chain Evolution

**Date**: 2026-03-04
**Reviewer**: Prof. Andrei Volkov
**Input**: `experiments/hotpotqa_p3_crossover/01_design.md`

---

## Summary of Design

A single-factor, 2-cell screening experiment comparing single-parent mutation (`num_parents=1`, Run I) against two-parent crossover (`num_parents=2`, Run J) on HotpotQA static chain evolution, with throughput equalized at 8 mutations/generation and N=1 per condition. The primary metric is best-of-archive test EM at generation 50, interpreted against pre-registered effect-size thresholds calibrated from 6 prior runs.

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|---------------|
| 1 | **AllCombinationsParentSelector fallback yields a 1-element list when archive_size < num_parents.** Code inspection (parent_selector.py lines 75-80) confirms that when `len(parents_copy) < self.num_parents`, the selector yields `parents_copy` — a list of 1 program when archive has 1 entry. The design document (Section 9, "Early-generation throughput deficit") states this "produces 1 mutation" but does not address whether the downstream mutation operator correctly handles receiving a 1-element parent list when `num_parents=2` is configured. If the mutation prompt template expects 2 parents and receives 1, it may produce malformed prompts, crash, or silently degrade. The design acknowledges this is "not empirically verified" (Section 12, item 2) but classifies it as a "pre-launch checklist item, not a design blocker." I disagree — the *design* must specify the expected behavior, not just defer to a checklist. | **Major** | Add to Section 9 a concrete specification of what the mutation operator does when it receives fewer parents than configured. Verify in the pre-launch dry-run and document the result in the design before launch. If the operator crashes or produces malformed output, a code change is required, which makes this a design-level concern. |
| 2 | **The 2.4pp "noise floor" is derived from 6 prior runs, but those runs are not homogeneous.** Section 7 states "inter-run variance is approximately 2.4pp (based on the spread of test EM values)" from Runs B, D, E, F, G, H. However, the memory file states E and G are **invalid** (repr-contamination bug). If the 2.4pp figure includes E and G, it is computed from contaminated data. If it excludes them, the reference distribution has only 4 runs (B, D, F, H) — a dangerously small sample to estimate variance from, and the 2.4pp figure should be reported with its own uncertainty. | **Major** | Clarify explicitly which runs are included in the 2.4pp calibration. If E and G are excluded (as they must be), recompute and report the spread from B, D, F, H only. State the range (min, max, IQR) rather than a single summary number. If the spread from 4 runs is wider than 2.4pp, the decision thresholds in Section 10 must be recalibrated. |
| 3 | **POSITIVE decision gate has a conjunctive criterion that includes acceptance rate, but acceptance rate is not defined with sufficient precision.** Section 10 requires "Run J acceptance rate >= Run I acceptance rate" for a POSITIVE verdict. But acceptance rate is defined only as "fraction of 8 mutants per generation that enter the archive" (Section 4). Is this the mean over all 50 generations? The final 10 generations? A single generation-50 value? Crossover may have lower acceptance in early generations (when parents are similar) but higher acceptance later (when parents diverge). The aggregation method matters. | **Minor** | Define acceptance rate precisely: mean over generations 10-50 (excluding the ramp-up period where throughput is asymmetric). |
| 4 | **The baseline selection decision rule (Section 5) conflates pipeline validation with prompt selection.** The rule states that if NLP prompts show a "suggestive" 1-3pp advantage, the design falls back to `prompts=default`. But if the NLP experiment shows 1-3pp advantage, this means `prompts=hotpotqa` is *possibly better*. Using `prompts=default` as the P3 baseline means the P3 control (Run I) may be suboptimal, reducing the absolute fitness level at which crossover is tested. This is not a confound per se (both runs use the same setting), but it means the experiment tests crossover at a potentially lower fitness plateau, where the fitness landscape may behave differently than at the frontier. | **Minor** | Acknowledge in Section 12 that the baseline selection may place both runs at a suboptimal fitness level if NLP prompts are later confirmed beneficial. This does not invalidate the comparison but limits the generalizability of the result. |
| 5 | **Random failure sampling introduces an asymmetry for 2-parent prompts that is acknowledged but not bounded.** Section 12, item 4 states the interaction with random failure sampling is "uncharacterized for 2-parent prompts." With 2 parents, each parent contributes its own set of 10 randomly sampled failures. If the two parents share many failures (likely when both evolved from the same seed and are structurally similar), the mutation LLM sees ~20 failure examples, many of which are near-duplicates. This is wasted context that inflates prompt length without adding information. The design does not specify whether the two failure sets are deduplicated. | **Minor** | Specify whether failure sets from two parents are deduplicated before inclusion in the prompt. If not, add deduplication to the pre-launch checklist as a potential optimization. If yes, document this. Either way, monitor the actual number of unique failures in 2-parent prompts. |
| 6 | **No pre-registered analysis of the secondary hypothesis (H1_stag).** H1_stag is defined in Section 2 as "reduces stagnation, defined as stretches of >= 10 consecutive generations with zero archive replacements." But Section 8 (Statistical Test) and Section 10 (Decision Gates) only reference the primary metric (delta = test EM difference). The SUGGESTIVE gate mentions stagnation ("Run J shows >= 5 fewer consecutive stagnation generations") but this is an OR condition, meaning a run could be classified SUGGESTIVE on stagnation alone even if test EM is in the NULL band. This conflates two signals and makes the decision gates non-orthogonal. | **Major** | Either (a) remove H1_stag from the decision gates entirely and report it as a purely exploratory diagnostic, or (b) pre-register separate decision criteria for H1_stag that do not interact with the primary metric classification. The current formulation allows a null-EM result to be upgraded to SUGGESTIVE based on a secondary metric, which is exactly the kind of post-hoc rescue that decision gates are designed to prevent. |
| 7 | **The ddce37b4 seed's test EM is never reported.** The design states ddce37b4 has val EM 62.7%, and the GEPA benchmark is 62.3% test EM. But the seed's own test EM is not given. If the seed's test EM is, say, 58%, then a Run J test EM of 61% represents a 3pp improvement over the seed but is below GEPA. If the seed's test EM is 64%, a Run J result of 61% is a regression. The POSITIVE gate requires "Run J test EM >= 60.0%" — but without the seed's test EM baseline, this floor is not well-motivated. | **Minor** | Report ddce37b4's test EM in the design document. Adjust the 60% floor if needed, or justify it independently (e.g., as the approximate GEPA threshold). |

## Hypothesis and Falsifiability

- [x] H₀ clearly stated
- [x] H₁ falsifiable and directional
- [x] Primary metric pre-specified
- [ ] Success criteria numeric and unambiguous

**Notes**: H₀ and H₁ are well-formulated. The primary metric (test EM at gen 50) is pre-specified and appropriate. However, the success criteria are not fully unambiguous due to Concern #6: the SUGGESTIVE gate's OR condition with stagnation creates ambiguity about what constitutes a positive signal. The POSITIVE gate's conjunctive criterion (delta >= 3pp AND test EM >= 60% AND acceptance rate comparison) is clear but the acceptance rate term needs tighter definition (Concern #3).

## Confound Analysis

- [x] Controlled variables genuinely controlled
- [x] IV isolated
- [x] Known confounds mitigated or acknowledged
- [x] Val/test split not contaminated

**Unaddressed confounds**:

The confound analysis in Section 9 is thorough and honest. The throughput equalization via `max_mutations_per_generation=8` is the correct approach and is well-justified. The P1-OFF decision for fitness comparability is sound. The early-generation throughput asymmetry is acknowledged with reasonable quantitative bounds.

One confound not explicitly discussed: **mutation prompt quality asymmetry**. The 2-parent prompt is not simply "more context" — it is a structurally different prompt that asks the LLM to perform a qualitatively different cognitive task (combine two programs vs. improve one). The mutation LLM may have been trained/fine-tuned more heavily on single-improvement tasks than on merging tasks, introducing a systematic bias unrelated to the crossover mechanism itself. This is not addressable within the current infrastructure but should be acknowledged as a potential explanation for negative results.

## Statistical Validity

- [x] Sample size justified
- [x] Statistical test appropriate
- [ ] Significance threshold pre-specified
- [ ] Multiple comparison correction applied if needed

**Notes**: The N=1 limitation is handled with unusual maturity for this research area. The honest acknowledgment that "N=1 CANNOT establish precise effect sizes, interaction effects, or statistical significance" (Section 7, item 4) is exactly the kind of language I expect. The external reference distribution from prior runs is a reasonable workaround.

However: there is no formal significance threshold because there is no formal test, which is the correct choice for N=1. The decision thresholds serve as a substitute, but the thresholds themselves depend on the 2.4pp noise floor estimate, which is potentially miscalibrated (Concern #2). The multiple comparison issue arises from testing both the primary metric and stagnation in the same decision gate (Concern #6).

## Evaluation Protocol

- [x] Metric computed identically across conditions
- [x] Val/test sets fixed and identical for all runs
- [x] No post-hoc metric selection
- [x] Thinking mode consistent across evaluations

**Notes**: The evaluation protocol is sound. Thinking mode is specified consistently (Qwen3-8B thinking mode, step_max_tokens 2048-4096). Val and test sets are fixed and identical. The test evaluation script (`run_test_eval.sh`) is referenced and presumably shared. No concerns here.

## Required Changes Before Approval

1. **[Major, Concern #2]** Clarify which runs are included in the 2.4pp noise floor calibration. If E and G are excluded, report the recalculated spread from B, D, F, H with min/max/range. Adjust decision thresholds in Section 10 if the recalculated spread differs materially from 2.4pp.

2. **[Major, Concern #1]** Add to Section 9 (or Section 12) a concrete specification of expected mutation operator behavior when `AllCombinationsParentSelector` yields a 1-element parent list under `num_parents=2`. This must be verified in the pre-launch dry-run; the result must be documented before launch approval.

3. **[Major, Concern #6]** Remove the stagnation OR condition from the SUGGESTIVE decision gate. Report stagnation as a purely exploratory secondary analysis that does not influence the primary verdict classification. The decision gates must be based solely on the primary metric (test EM delta).

---

## Verdict

**[ ] APPROVED**

**[x] NEEDS REVISION** — address required changes, re-submit for review

**[ ] REJECTED**

**Reviewer notes**:

This is a well-structured screening experiment that correctly identifies and addresses the most dangerous confound (throughput asymmetry). The N=1 limitations are handled with appropriate intellectual honesty, and the pre-registered decision gates are a disciplined approach to interpreting underpowered data. The pre-launch checklist covers the known GigaEvo failure modes (repr-contamination, prompts_dir wiring, stale exec_runners, Redis flush).

The three required changes are tractable — none requires a fundamental redesign. Concern #2 (noise floor calibration) is the most consequential: if the actual inter-run spread from valid runs is 4pp rather than 2.4pp, the decision thresholds shift substantially, and the entire experiment becomes even more of a screening study than currently framed. Concern #6 (stagnation in decision gates) is a methodological hygiene issue that, if left unaddressed, would allow the researcher to rescue a null primary result with a secondary metric — the classic post-hoc maneuver that pre-registration is designed to prevent.

I note with approval: the pipeline decision rule (Section 5) correctly mandates `pipeline=hotpotqa_asi` in all cases, eliminating the repr-contamination risk. The `prompts_dir` check is in the pre-launch checklist (Appendix A, item 6). The exec_runner cleanup is in the checklist (Appendix A, item 8). These are lessons learned from prior failures, and it is good to see them institutionalized.

Address the three required changes. I expect revision, not redesign.

---

## Second Review (2026-03-04)

**Reviewer**: Prof. Andrei Volkov
**Input**: Revised `01_design.md` (status: "Revised — resubmitted for review")

### Evaluation of Required Changes

**Required Change #1 [Major, Concern #1]: AllCombinationsParentSelector fallback specification.**

**Status: RESOLVED.** Section 9 ("Early-generation throughput deficit") now contains a concrete, line-referenced specification of the mutation operator's behavior when receiving a 1-element parent list: `build_prompt()` (lines 177-193) iterates over whatever parents it receives, sets `count=len(parents)`, and produces a valid single-parent rewrite prompt. The diff-mode `ValueError` path is explicitly noted as unreachable under `mutation_mode=rewrite`. This is no longer deferred to the checklist — it is specified in the design itself, with the pre-launch dry-run serving as empirical confirmation rather than as the first point of discovery. This is exactly what I asked for.

**Required Change #2 [Major, Concern #2]: Noise floor calibration and source transparency.**

**Status: RESOLVED.** The revision fundamentally corrects the provenance of the 2.4pp figure. It is now described as "same-program retest noise from Run B (re-evaluating ddce37b4 twice on the same n=300 test set)" — a within-program measurement of irreducible EM sampling variance from LLM non-determinism and finite test size. This is independent of the validity of any evolutionary run and therefore immune to the repr-contamination concern I raised. The 4-run external reference distribution (B, D, F, H) is used separately as a secondary cross-check (Section 8, item 4), not as the basis for the noise floor. The statistical grounding is further strengthened by the SE calculation: 95% CI for a proportion at EM ~0.60, n=300 is +/-5.49pp (one SE ~2.80pp), placing the 2.4pp threshold at ~0.44 SE — a moderately conservative filter. This is a cleaner and more defensible calibration than the original inter-run spread.

**Required Change #3 [Major, Concern #6]: Stagnation removed from decision gates.**

**Status: RESOLVED.** Stagnation has been completely excised from the pre-registered decision gates. The SUGGESTIVE criterion is now purely EM-based: "+1.0pp <= delta < +3.0pp". A new subsection ("Secondary/Exploratory Analysis") reports stagnation separately with the explicit, unambiguous statement: "A favorable stagnation result with a NULL primary verdict does **not** upgrade the classification to SUGGESTIVE. The decision gates are based solely on the primary metric (test EM delta)." This is exactly the separation I required. The secondary hypothesis H1_stag is retained as exploratory, which is appropriate — my objection was never to measuring stagnation, but to allowing it to rescue a null primary result.

### Evaluation of Minor Concerns

| # | Concern | Status | Notes |
|---|---------|--------|-------|
| 3 | Acceptance rate aggregation window | RESOLVED | Now defined as "mean over generations 10-50 (excluding the ramp-up period where throughput is asymmetric)" in Section 4. Precise and appropriate. |
| 4 | Baseline selection generalizability | RESOLVED | Section 12, item 6 now explicitly acknowledges the suboptimal-plateau risk and its implications for generalizability. Honest and sufficient. |
| 5 | Failure deduplication for 2-parent prompts | RESOLVED | Section 12, item 4 now specifies that failure sets are not deduplicated, accepts this as-is, and commits to monitoring unique failure counts from mutation logs. Acceptable for a screening study. |
| 7 | Seed test EM not reported | RESOLVED | ddce37b4 test EM (55.3%) now appears in Section 5 and Appendix B. The POSITIVE gate's 60% floor is well-motivated as a meaningful improvement over the seed (55.3%) approaching GEPA (62.3%). |

### Additional Observations

1. The mutation prompt quality asymmetry confound, which I flagged in the first review as an unaddressed confound (not a required change), has been added to Section 9 as a full entry. Good.

2. Section 7's four-point justification for N=1 is now among the most honest and well-calibrated sample-size discussions I have seen in this research program. Item 4 ("What N=1 CAN establish / What N=1 CANNOT establish") sets the right expectations. The ~30-40% probability of a true 3pp effect falling in the null/suggestive band (Section 12, item 5) is a mature acknowledgment that this is a screening study, not a definitive trial.

3. The pre-launch checklist (Appendix A) now includes a specific instruction to verify the fallback prompt text during the dry-run, tying the design specification to empirical confirmation. This is the correct relationship between design and checklist.

### Remaining Risks (accepted, not blocking)

- The N=1 power limitation remains. This is structural, not addressable within compute constraints, and is transparently acknowledged.
- The baseline selection dependency on the NLP experiment introduces a ~48-hour delay before launch. The fallback rule is unambiguous.
- Failure deduplication for 2-parent prompts could waste context tokens in early generations. Monitoring is planned; optimization is deferred. Acceptable.

None of these rise to the level of required changes.

### Checklist Update

- [x] H₀ clearly stated
- [x] H₁ falsifiable and directional
- [x] Primary metric pre-specified
- [x] Success criteria numeric and unambiguous
- [x] Controlled variables genuinely controlled
- [x] IV isolated
- [x] Known confounds mitigated or acknowledged
- [x] Val/test split not contaminated
- [x] Sample size justified
- [x] Statistical test appropriate

---

## Verdict (Second Review)

**[x] APPROVED**

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**:

All three required changes have been addressed with precision and without overreach. The noise floor recalibration (Concern #2) is not merely a correction but an improvement — the same-program retest variance is a more principled calibration source than inter-run spread, and the SE anchoring provides statistical grounding that the original design lacked. The stagnation separation (Concern #6) is clean and leaves no room for post-hoc rescue of a null primary result. The fallback specification (Concern #1) transforms a deferred unknown into a documented, verifiable expectation.

The design is approved for progression to Phase 3 (pre-launch). The pre-launch checklist items — particularly the dry-run verification of the fallback behavior and the token count extraction from NLP experiment logs — remain prerequisites before actual launch. Approval of the design does not constitute approval to skip the checklist.

I will be watching the execution with interest. The 2-parent crossover mechanism is the first genuinely novel search operator being tested in this research program, and its interaction with the LLM mutation paradigm is theoretically unpredictable. The design is now rigorous enough to produce an interpretable result regardless of direction.
