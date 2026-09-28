# Phase 2: Adversarial Review -- HoVer Feedback + Soft Fitness
<!-- Protocol version: 1.0 -->

**Reviewer**: Professor Andrei Volkov (reviewer-2-adversary agent)
**Date**: 2026-03-20
**Design doc reviewed**: `experiments/hover/feedback_softfit/01_design.md`
**Round**: 1

---

## Summary of Design

A 2x2 factorial (feedback x fitness metric) with 3 active cells tests whether structured
per-hop failure feedback (cell B), fractional fitness scoring (cell C), or their
combination (cell D, deferred) increases HoVer test retrieval coverage beyond the baseline
mean of ~51.87%. The baseline's n=4 replication (H1-H4) serves as cell A. New runs are
n=2 per treatment cell (F1-F4), for a total of 8 data points across 3 conditions.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|---------------|
| 1 | Cell B `problem.name` ambiguity: validate.py return type conflict | **Major** | Clarify which validate.py cell B uses. If it uses the *existing* `chains/hover/static/validate.py` (dict-returning), the feedback pipeline's `FetchArtifact` will receive `None` from `data[1]` and the formatter will produce an empty string -- feedback is silently absent. If a new feedback-returning validate.py replaces the existing one in `chains/hover/static/`, then cell C (which also uses `standard` pipeline with this problem) could be affected by leftover imports. See detailed analysis below. |
| 2 | `model_name` and `llm_base_url` missing from Section 5 | **Major** | The controlled variables table (Section 5) does not list `model_name` or `llm_base_url`. These were flagged as Critical in the baseline review because the global default is `deepseek/deepseek-v3.2` on OpenRouter. Appendix A item 6 mentions `model_name` in passing, but Section 5 -- the canonical controlled-variables reference -- omits them. Add both with values `Qwen3-235B-A22B-Thinking-2507` and per-run mutation LLM URLs, and mark them as explicit overrides. |
| 3 | `hover_feedback.yaml` must wire `prompts_dir` in both blocks | **Minor** | The design states (Section 6, item 4) that `config/pipeline/hover_feedback.yaml` will be created. It must follow the pattern of `hotpotqa_asi.yaml` and include `prompts_dir: ${prompts.dir}` in the `evolution_context` block. This is already present in `standard.yaml` and `hotpotqa_asi.yaml`, but the silent-failure mode if it is omitted (custom prompts silently ignored) warrants an explicit verification step in Appendix A. |
| 4 | H4 data still TBD -- baseline mean is provisional | **Minor** | Section 2 uses "~51.87% from H1-H3" and notes "will be updated with H4 data when available." The user message states H4 is still running. The design must commit to updating the baseline mean with H4 before computing deltas. If H4 is invalidated, acknowledge the reduced baseline N=3 and its impact on the MDE calculation. |
| 5 | `significant_change` difference between cells B and C | **Minor** | Cell B uses the existing `metrics.yaml` with `significant_change: 0.01` (discrete). Cell C's `static_soft/metrics.yaml` will use `significant_change: 0.003`. The design correctly notes this (Section 9) but does not note it in Section 5 as a controlled variable that *differs* between conditions. This is an IV-adjacent parameter. Add it to Section 5 with the per-cell values. |
| 6 | No multiple-comparison correction | **Minor** | The design performs two primary one-sided t-tests (cell B vs. baseline, cell C vs. baseline) at alpha=0.05 each. The family-wise error rate is approximately 0.0975 under the global null. Given the exploratory/decision-stage framing and low power, formal Bonferroni correction would be counterproductive -- but the document should acknowledge the inflated Type I rate. A single sentence in Section 8 suffices. |
| 7 | Run Design Table missing `model_name` and `llm_base_url` columns | **Minor** | The baseline design's Run Design Table (Section 6) included explicit `model_name` and `llm_base_url` columns for every run. The current design's table has `pipeline`, `Chain LLM URL`, and `Mutation LLM URL` but not `model_name`. For audit trail completeness, add `model_name` to the table or note it is identical for all 4 runs. |

---

### Detailed Analysis of Concern #1: Cell B validate.py Architecture

This is the most important architectural question in the design.

The design states (Section 5): `problem.name = chains/hover/static` for cells A and B.
It also states (Section 6): `pipeline = hover_feedback` for cell B.

Here is the issue. The `hover_feedback` pipeline will use `HoVerFeedbackPipelineBuilder`,
which replaces `FormatterStage` with `HoVerFeedbackFormatter`. This formatter expects
failure data from `FetchArtifact`. But `FetchArtifact` extracts `data[1]` from
`CallValidatorFunction`'s output. If validate.py returns a plain `dict` (as the current
`chains/hover/static/validate.py` does), `parse_output()` wraps it as `(dict, None)`,
and `FetchArtifact` returns `None`. The formatter then receives `None` and produces an
empty string -- *exactly the same as the baseline*.

Therefore, cell B **requires** a modified validate.py that returns
`(metrics_dict, failures_list)`. The design acknowledges this in Section 6 item 1:
"Return `(metrics_dict, failures_list)` instead of `metrics_dict`."

But which validate.py file is modified? Two options:

**(a) Modify `chains/hover/static/validate.py` in place.** Then cell B and cell A share
the same validate.py. This is acceptable IF `pipeline=standard` (cell A's pipeline)
correctly handles the tuple return. Checking `parse_output()` at execution.py:249-261:
yes, `isinstance(x, tuple)` returns the tuple directly, so `FetchMetrics` gets
`data[0]` (the metrics dict) and `FetchArtifact` gets `data[1]` (the failures list).
The standard pipeline's default `FormatterStage` will receive the failures list but
call `format_value(data)` on it, which returns its `repr()`. This injects a repr of the
entire failures list into the mutation context -- **repr-contamination**, the exact
failure mode from PR #67 on HotpotQA.

Wait -- I should verify this. The baseline runs (H1-H4) already completed with the
*current* dict-returning validate.py. If the validate.py is modified in place for cell B,
cell A's historical data is unaffected (already collected). But if cell C's runs use
`chains/hover/static` (they do not -- they use `chains/hover/static_soft`), there would
be no issue. And cell C uses `pipeline=standard` with `problem.name=chains/hover/static_soft`,
which has its own validate.py returning a plain dict.

So option (a) works for this experiment because cell A is historical and cell C uses a
separate problem variant. But the design should **explicitly state** that
`chains/hover/static/validate.py` is being modified to return a tuple, and that this
modification does not affect historical baseline data (already collected) or cell C
(uses `static_soft/validate.py`).

**(b) Create a new problem variant `chains/hover/static_feedback/`.** Cleaner separation
but the design does not mention this.

**Recommendation**: Clarify in Section 6 which approach is taken and add a verification
step to Appendix A confirming that the modified validate.py produces identical `data[0]`
(metrics dict) as the original -- the design's item 1 in Appendix A covers this, but
should be strengthened to test specifically that `data[0]["fitness"]` values match on
the gen-0 program.

Additionally, if option (a) is taken, add a note that the standard pipeline's default
`FormatterStage.format_value()` will now receive the failures list (not `None`), producing
a repr-string in the mutation context for any *future* run that uses
`pipeline=standard` + `problem.name=chains/hover/static`. This is an infrastructure
side-effect that should be documented.

---

## Hypothesis and Falsifiability

- [x] H0 is clearly stated
- [x] H1 is falsifiable and directional
- [x] Primary metric is pre-specified and sufficient to test H1
- [x] Success criteria are numeric and unambiguous

**Notes**: The hypotheses are well-constructed. H0 uses a concrete 2.0pp noise-floor
threshold rather than zero, which is appropriate given the baseline's observed inter-run
SD. The directional sub-hypotheses (H1a, H1b, H1c) are properly labeled as exploratory
and pre-registered, which is correct practice.

The SUGGESTIVE category is appropriately split between (0, +2.0pp) -- this is an
improvement over the baseline design which required a revision to differentiate
SUGGESTIVE-SIG from SUGGESTIVE-NS. However, this design drops the SIG/NS distinction.
Since p-values will be unreliable at n=2, this is a defensible choice. I accept it.

---

## Confound Analysis

- [x] All controlled variables are genuinely controlled
- [ ] IV is isolated (no other differences between conditions) -- **see concerns #1, #5**
- [x] Known confounds are mitigated or acknowledged
- [x] Val/test split is not contaminated

**Unaddressed confounds**:

1. **Concern #1 above**: The validate.py architecture for cell B introduces a secondary
   change (tuple return) that alters what the `standard` pipeline sees if anyone
   subsequently runs `pipeline=standard` on `chains/hover/static`. This does not affect
   the *current* experiment's cell C (different problem variant) or cell A (historical),
   but it is an infrastructure side-effect that should be documented.

2. **Cell C `problem.name` change**: Cell C uses `chains/hover/static_soft`, a new
   problem variant. This means cell C differs from cell A in two ways: (a) the fitness
   metric (the IV) and (b) the problem.name path, which determines which validate.py,
   metrics.yaml, and initial_programs directory are loaded. The design correctly states
   that static_soft is a copy of static with a modified validate.py. But the initial
   programs directory must also be copied -- otherwise, the cold-start program may
   differ. The design's Appendix A item 4 tests soft validate.py correctness but does
   not verify that `static_soft/initial_programs/baseline.py` is identical to
   `static/initial_programs/baseline.py`. **Add this verification to Appendix A.**

3. **Host-treatment confound**: Section 9 acknowledges this and offers to shuffle.
   The baseline showed <1.3pp host effect. Given the design's POSITIVE threshold of
   +2.0pp, a 1.3pp host effect is meaningful -- it is 65% of the threshold. However,
   with n=2 per condition, shuffling would place one run from each condition on each
   host, which is the correct mitigation. **I recommend the shuffled assignment
   (F1=host A, F2=host B, F3=host A, F4=host B) as the default, not the fallback.** This
   costs nothing and eliminates a confound.

   That said, this is a recommendation, not a blocker. The host effect is within the
   noise floor and the design correctly identifies the mitigation.

---

## Statistical Validity

- [x] Sample size is justified
- [x] Statistical test is appropriate for the data
- [x] Significance threshold is pre-specified
- [ ] Multiple comparison correction applied if testing multiple hypotheses -- **see concern #6**

**Notes**:

The sample size justification is honest about the power limitations. The MDE calculation
is correct: at n_treatment=2, n_control=4, SD=2pp, MDE ~ 3.7pp. The design correctly
frames this as a "decision-stage experiment" rather than a definitive test, which is
the only honest framing at this sample size.

The statistical test (Welch's two-sample t-test, one-sided) is appropriate.

The factorial main-effects analysis (Test 2) is correctly labeled as exploratory and
does not gate conclusions. This is good practice.

The power analysis correctly notes that effects in the +2-4pp range will not reach
significance. The design's response to this -- using effect-size thresholds as the
primary decision criterion, with p-values as calibration -- is the right approach for
decision-stage work.

One subtle issue: Test 2 computes the feedback main effect as mean(F1,F2) vs.
mean(F3,F4,H1,H2,H3,H4). This pools cell C with cell A as the "no feedback" reference.
But cell C has soft fitness, which may itself affect coverage. If cell C happens to have
higher coverage (due to soft fitness), the "no feedback" pool mean is inflated, making
the feedback main effect *harder* to detect. If cell C has lower coverage, the pool
mean is deflated, making the feedback effect *easier* to detect. This is the standard
limitation of a partial factorial, and the design correctly defers the full interaction
analysis to cell D. But the document should note this explicitly in Section 8 Test 2.

---

## Evaluation Protocol

- [x] Metric is computed identically across all conditions
- [x] Val set and test set are fixed and identical for all runs
- [x] No metric is cherry-picked post-hoc
- [x] Thinking mode is consistent across all evaluations

**Notes**:

The most critical design decision -- using discrete test coverage for ALL conditions,
including cell C (soft fitness) -- is correct and clearly stated. Section 2, Section 4,
and Section 6 all reinforce this. Well done.

The 5-repeat test protocol is identical to the baseline, ensuring within-run variance
estimates are comparable.

The val-test gap diagnostic (Section 4) correctly notes that val coverage numbers are
not directly comparable across cells B and C because cell C's val metric is fractional.
This is handled well.

The test.py SHA-256 verification (Appendix A item 5) is a strong safeguard against
metric contamination. I note that the current `test.py` at
`problems/chains/hover/static/test.py` calls `discrete_retrieval_eval` at line 56 and
does not reference any fractional metric. This is correct.

---

## Required Changes Before Approval

1. **[Major -- Concern #1]**: Section 6 Cell B implementation: Explicitly state which
   validate.py is modified and how. If `chains/hover/static/validate.py` is modified
   in place to return `(metrics_dict, failures_list)`, document: (a) this does not
   affect cell A (historical data), (b) this does not affect cell C (different
   `problem.name`), and (c) this changes the default FormatterStage behavior for any
   future `pipeline=standard` run on `chains/hover/static` (infrastructure side-effect).
   If a separate `chains/hover/static_feedback/` variant is created instead, state this
   and add it to the controlled variables table.

2. **[Major -- Concern #2]**: Section 5: Add `model_name: Qwen3-235B-A22B-Thinking-2507`
   and `llm_base_url: http://<mutation_ip>:8777/v1` to the controlled variables table
   with the note "explicit override required; default is OpenRouter." Also add these to
   the Run Design Table (Section 6) or note they are identical for all 4 runs. This was
   a Critical concern in the baseline review; its omission here is a regression.

3. **[Minor -- Concern #3]**: Appendix A: Add a verification step for
   `hover_feedback.yaml` confirming that `prompts_dir: ${prompts.dir}` is present in
   the `evolution_context` block and that `stage_timeout: ${stage_timeout}` and
   `dag_timeout: ${dag_timeout}` are present in the `pipeline_builder` block. Reference
   the `hotpotqa_asi.yaml` pattern.

4. **[Minor -- new, from confound analysis]**: Appendix A: Add a verification step
   confirming that `chains/hover/static_soft/initial_programs/baseline.py` is identical
   (byte-for-byte or SHA-256 match) to `chains/hover/static/initial_programs/baseline.py`.
   Cold-start initialization must be identical across cells.

5. **[Minor -- Concern #6]**: Section 8: Add one sentence acknowledging the inflated
   family-wise error rate from two primary tests (approximately 0.0975 under the global
   null) and stating that formal correction is not applied because the experiment is
   decision-stage with low power.

6. **[Recommendation, non-blocking]**: Section 6: Adopt the shuffled host assignment
   (F1=host A, F2=host B, F3=host A, F4=host B) as the default rather than the fallback.
   This eliminates the host-treatment confound at zero cost.

7. **[Recommendation, non-blocking]**: Section 8 Test 2: Note that the pooled "no
   feedback" reference (cell A + cell C) may be biased if cell C's coverage differs
   from cell A's due to the soft fitness treatment. This is inherent to the partial
   factorial and does not invalidate the analysis, but should be acknowledged.

---

## Verdict

**[x] NEEDS REVISION** -- address required changes, re-submit for review

Items 1 and 2 are Major concerns that must be resolved before approval. Items 3-5 are
Minor but should be addressed in the revision. Items 6-7 are recommendations; I will
not block on them but will note whether they are adopted.

**Reviewer notes**: This is a well-constructed design for a decision-stage experiment.
The 2x2 factorial with cell D deferred is a sound strategic choice -- it maximizes
information per run while acknowledging the power limitations honestly. The decision
tree (Appendix B) is clear, the effect-size thresholds are pre-registered, and the
test protocol is properly controlled. The treatment of soft fitness as an evolution-only
change with discrete test evaluation is exactly right.

The two Major concerns are essentially documentation gaps, not design flaws. Concern #1
(validate.py architecture) could become a silent failure if the implementation does not
match the design's intent -- the distance between "validate.py returns a tuple" and
"FetchArtifact receives None because nobody changed validate.py" is one missing line of
code. Making the architecture explicit protects against this. Concern #2 (model_name
omission) is a regression from the baseline review that should take two minutes to fix.

I expect this to be APPROVED in one revision.

*The science demands nothing less.*

---
---

# Round 2 Review

**Reviewer**: Professor Andrei Volkov (reviewer-2-adversary agent)
**Date**: 2026-03-20
**Design doc reviewed**: `experiments/hover/feedback_softfit/01_design.md` (revised)
**Round**: 2

---

## Disposition of Round 1 Concerns

| # | Original concern | Severity | Status | Location in revised design |
|---|-----------------|----------|--------|---------------------------|
| 1 | Cell B validate.py architecture ambiguity | **Major** | **RESOLVED** | Section 6, lines 200-223: explicitly states in-place modification of `chains/hover/static/validate.py`; full impact analysis covers (a) cell A historical data unaffected, (b) cell C uses separate `problem.name`, (c) infrastructure side-effect of repr-contamination for future `pipeline=standard` runs documented with reference to PR #67. |
| 2 | `model_name` and `llm_base_url` missing from Section 5 and Run Design Table | **Major** | **RESOLVED** | Section 5, lines 163-165: both variables added with explicit override notes and OpenRouter default warning. Run Design Table (lines 181-186) now includes `model_name` column for all 4 runs. `llm_base_url` shown per-run in the Mutation LLM URL column. |
| 3 | `hover_feedback.yaml` wiring verification | **Minor** | **RESOLVED** | Appendix A item 3 (lines 560-566): verification step confirms `prompts_dir: ${prompts.dir}` in both `evolution_context` and `mutation_operator` blocks, plus `stage_timeout` and `dag_timeout` in `pipeline_builder` block. References `hotpotqa_asi.yaml` pattern. |
| 4 | `initial_programs/baseline.py` identity check | **Minor** | **RESOLVED** | Appendix A item 5 (lines 572-574): byte-for-byte SHA-256 match required between `static_soft/initial_programs/baseline.py` and `static/initial_programs/baseline.py`. |
| 5 | Family-wise error rate acknowledgment | **Minor** | **RESOLVED** | Section 8, Test 1 (lines 374-377): explicit statement of ~0.0975 FWER under global null, with justification for not applying Bonferroni. |
| 6 | Shuffled host assignment (recommendation) | Rec. | **ADOPTED** | Section 6, lines 275-279: shuffled assignment is now the default (F1=host A, F2=host B, F3=host A, F4=host B), with clear rationale. |
| 7 | Pooled reference bias note (recommendation) | Rec. | **ADOPTED** | Section 8, Test 2 (lines 394-399): caveat about cell C contaminating the "no feedback" pool is stated, with direction-of-bias analysis. |

---

## New Issues in Revised Design

None identified. The revision is clean. No new concerns were introduced by the changes.

---

## Checklist (Round 2)

### Hypothesis and Falsifiability
- [x] H0 is clearly stated
- [x] H1 is falsifiable and directional
- [x] Primary metric is pre-specified and sufficient to test H1
- [x] Success criteria are numeric and unambiguous

### Confound Analysis
- [x] All controlled variables are genuinely controlled
- [x] IV is isolated (previously flagged concerns resolved)
- [x] Known confounds are mitigated or acknowledged
- [x] Val/test split is not contaminated

### Statistical Validity
- [x] Sample size is justified
- [x] Statistical test is appropriate for the data
- [x] Significance threshold is pre-specified
- [x] Multiple comparison issue acknowledged (FWER stated, correction justified as inappropriate)

### Evaluation Protocol
- [x] Metric is computed identically across all conditions
- [x] Val set and test set are fixed and identical for all runs
- [x] No metric is cherry-picked post-hoc
- [x] Thinking mode is consistent across all evaluations

---

## Remaining Minor Observations (non-blocking)

1. **Concern #4 from Round 1 (H4 data TBD)**: The baseline mean remains provisional at ~51.87% from H1-H3. The design commits to updating with H4 data. This is acceptable -- the design's structure does not depend on the exact baseline mean, and updating it before Phase 5 analysis is the correct procedure. No action needed now.

2. **Concern #5 from Round 1 (`significant_change` difference)**: Section 9 documents the `significant_change` difference (0.01 vs. 0.003) in the confounds table. Section 5 does not list it as a separate row, but it is implicitly captured by the `problem.name` difference between cells. This is acceptable -- the `significant_change` parameter is downstream of the `problem.name` choice and is not independently manipulated.

---

## Verdict

**[x] APPROVED** -- proceed to Phase 3

All 7 concerns from Round 1 are resolved. Both Major concerns (validate.py architecture documentation, model_name/llm_base_url controlled variables) are fully addressed with the level of specificity requested. All 3 Minor concerns are addressed. Both non-blocking recommendations were adopted, which strengthens the design.

The validate.py impact analysis in Section 6 (lines 208-223) is particularly well done -- it covers the three threat vectors (historical data, concurrent cell C, future infrastructure side-effect) with the exact specificity I asked for, including the PR #67 repr-contamination reference. This is the kind of documentation that prevents silent failures at implementation time.

The Appendix A verification checklist is now comprehensive: 9 items covering validate.py correctness, formatter correctness, pipeline YAML wiring, initial program identity, test.py integrity, config verification, Redis state, and gen-0 diagnostics. This is a strong pre-launch protocol.

This design is ready for implementation.

*The science demands nothing less.*
