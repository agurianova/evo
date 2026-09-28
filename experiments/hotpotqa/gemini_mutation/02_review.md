# Phase 2: Adversarial Review -- Gemini-3-Flash as Mutation LLM (Re-Review)

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Date**: 2026-03-12
**Review round**: 2 (re-review after NEEDS REVISION)
**Design reviewed**: `experiments/hotpotqa/gemini_mutation/01_design.md`
**Design date**: 2026-03-12

---

## Summary of Design

The experiment proposes replacing the locally-hosted mutation LLM (Qwen3-235B-A22B-Thinking) with a frontier API model (google/gemini-3-flash-preview via OpenRouter) while holding all other variables fixed to the colbert_feedback configuration (ColBERT retriever, rich failure feedback, F1 fitness, 600-sample validation, cold start, 25 generations). N=2 runs are pre-registered as an exploratory screening study with descriptive verdict thresholds, not inferential tests.

---

## Prior Review Summary (Round 1)

Three major concerns were raised; all required resolution before approval.

| # | Concern | Round 1 Severity |
|---|---------|:----------------:|
| M1 | `max_tokens=81920` may exceed Gemini-3-Flash output limit -- silent cap or rejection | Major |
| M2 | Conditional reference selection creates ambiguous verdict thresholds when refs diverge -- no decision rule for discordant verdicts | Major |
| M3 | +/-2pp noise band calibrated from cold_start (Qwen3-235B + BM25) does not transfer to Gemini + ColBERT -- need |V1-V2| diagnostic guard | Major |
| m1 | Checklist item 3 references `mutation_operator` block absent from `hotpotqa_colbert.yaml` | Minor |
| m2 | `api_key` may be exposed in `--cfg job` output | Minor |
| m3 | Cost estimate (500 tokens/call) inconsistent with `max_tokens=81920` | Minor |
| m4 | Manual mutation test (Risk 1 / checklist item 4) has no pre-registered success criterion | Minor |

---

## Resolution of Major Concerns

### M1: max_tokens=81920 -- RESOLVED

The revision adds Appendix A item 6 (lines 581-585), which correctly identifies Gemini-3-Flash-Preview as a thinking model supporting 64K+ output tokens. The pre-launch verification is actionable: "confirm the first mutation call completes without an API error referencing output limit. If the API rejects 81920, add an explicit `max_tokens: 32768` override and file an amendment."

This is a reasonable resolution. The thinking-model classification is consistent with Google's March 2026 Gemini-3-Flash-Preview specifications. The fallback path (amendment with explicit cap) is pre-registered. The pre-launch check catches failure mode #1 (rejection) and the cost-overrun confound in Section 9 (monitoring at gen 5, $3 threshold) catches failure mode #3 (unexpectedly long outputs). Accepted.

### M2: Discordant verdict rule -- RESOLVED

Section 2 (lines 103-107) adds a pre-registered decision rule: "the **primary reference governs the main verdict and escalation decision**. The secondary reference is reported for context only. Discordant verdicts themselves are a finding and will be discussed in Phase 5."

This is clean and unambiguous. The primary reference is well-defined by the conditional table (lines 94-97): colbert_feedback mean if available with n >= 2, cold_start mean otherwise. The secondary reference provides context without polluting the decision logic. Accepted.

### M3: Inter-run spread guard -- RESOLVED

Section 2 (lines 109-112) adds: "If |V1 - V2| > 4pp, the maximum attainable verdict is capped at **INCONCLUSIVE** regardless of the mean." The rationale is stated: "a spread this large indicates the two runs landed in different basins, and the mean is not a reliable summary of the treatment effect."

The 4pp threshold is 4x the cold_start SD, which is a reasonable guard even if the true Gemini SD is somewhat higher than 1.00pp. The cap prevents a misleading POSITIVE verdict from a high-variance mean. Accepted.

---

## Resolution of Minor Concerns

| # | Status | Notes |
|---|--------|-------|
| m1 | **Not addressed** | Appendix A item 3 (line 572) still references "`mutation_operator` block" in `--cfg job` output. Under `hotpotqa_colbert`, the mutation operator config may be structured differently. This is a checklist precision issue that will be caught at pre-launch by visual inspection of `--cfg job` output. Does not block approval. |
| m2 | **Not addressed** | API key exposure risk in `--cfg job` output remains unverified. Section 9 adds "API key safety" as a confound (line 415) and Appendix A item 10 says "Confirm `OPENAI_API_KEY` does not appear in `--cfg job` output." The check is present but the exposure risk is not resolved in the design -- it is deferred to pre-launch. Acceptable for an exploratory study. |
| m3 | **Partially addressed** | The thinking-model framing in M1 resolution explains why outputs may be longer, and the cost guard ($3 by gen 5, $8 per run by gen 10) provides a safety net. The cost estimate in Section 7 still assumes 500 output tokens/call. The estimate may be off by 2-5x, but the pre-registered cost guards catch overruns. Acceptable. |
| m4 | **Not addressed** | Appendix A item 4 (line 575-576) still says "Verify output is parseable" without defining what constitutes a parseable output. Phase 3 engineers should interpret this as: the GigaEvo mutation parser extracts a syntactically valid Python function from the Gemini response AND the function loads without import errors. Not blocking. |

---

## New Concerns Introduced by Revision

### n1: Decision tree omits the inter-run spread guard (Minor)

The decision tree in Appendix B (lines 606-641) does not include the |V1-V2| > 4pp guard as a preliminary check before entering the verdict cascade. The guard is pre-registered in Section 2 (lines 109-112) and takes legal precedence, but the decision tree should reflect it for consistency. Phase 3/5 personnel who consult Appendix B without re-reading Section 2 could miss the guard.

**Recommendation**: Add a first-level branch to the decision tree: "Is |V1 - V2| > 4pp? YES -> INCONCLUSIVE (high variance). NO -> proceed to verdict cascade." Not blocking.

---

## Hypothesis and Falsifiability

- [x] H0 is clearly stated
- [x] H1 is falsifiable and directional
- [x] Primary metric is pre-specified and sufficient to test H1
- [x] Success criteria are numeric and unambiguous

**Notes**: No change from Round 1. The exploratory framing with descriptive thresholds remains the correct approach for n=2. The discordant-verdict rule (M2 fix) and spread guard (M3 fix) strengthen the pre-registration by closing ambiguities that would otherwise require post-hoc judgment.

---

## Confound Analysis

- [x] All controlled variables are genuinely controlled
- [x] IV is isolated (no other differences between conditions)
- [x] Known confounds are mitigated or acknowledged
- [x] Val/test split is not contaminated

**Unaddressed confounds**: None at major severity. The residual `max_tokens` effective-value asymmetry (m3/M1) is acknowledged and guarded by pre-launch verification. The noise-band calibration transfer (M3) is now explicitly caveated with the 4pp guard.

---

## Statistical Validity

- [x] Sample size is justified (as an exploratory screen)
- [x] Statistical test is appropriate for the data (descriptive only -- correct for n=2)
- [x] Significance threshold is pre-specified (N/A -- no NHST)
- [ ] Multiple comparison correction applied if testing multiple hypotheses (N/A -- descriptive study)

**Notes**: No change from Round 1. The statistical approach remains sound. The Round 1 note about the directional consistency probability (Section 7 item 2: "probability ~2.3%" is the per-run probability, not the joint probability of 0.00052) is a presentation imprecision that does not affect design validity. Phase 5 should report the joint probability if both runs exceed ref+2SD.

---

## Evaluation Protocol

- [x] Metric is computed identically across all conditions
- [x] Val set and test set are fixed and identical for all runs
- [x] No metric is cherry-picked post-hoc
- [x] Thinking mode is consistent across all evaluations

**Notes**: No change from Round 1. The evaluation protocol is well-specified and inherited from colbert_feedback.

---

## Required Changes Before Approval

None. All three major concerns from Round 1 are adequately resolved.

---

## Remaining Minor Items (Non-Blocking)

For Phase 3 documentation:

1. **m1**: Verify that Appendix A item 3 (`prompts_dir` in `mutation_operator` block) is correct for `hotpotqa_colbert` pipeline, or update the checklist item to reference the actual YAML structure.
2. **m4**: Define "parseable" in Appendix A item 4 as: parser extracts a syntactically valid Python function AND the function loads without import errors.
3. **n1**: Add the |V1-V2| > 4pp guard as a first-level branch in the Appendix B decision tree.

These are documentation precision items. None affect experimental validity.

---

## Verdict

**[x] APPROVED** -- proceed to Phase 3

**[ ] NEEDS REVISION** -- address required changes, re-submit for review

**[ ] REJECTED** -- fundamental flaw; redesign required

**Reviewer notes**:

All three major concerns from Round 1 are resolved. M1 is addressed with a thinking-model classification and actionable pre-launch verification with a pre-registered fallback. M2 is addressed with a clear decision rule: primary reference governs; secondary reported for context. M3 is addressed with a 4pp spread guard that caps the verdict at INCONCLUSIVE when inter-run variance exceeds the calibrated noise band.

The design remains one of the cleaner entries in this experimental series. The single-substitution approach, honest n=2 framing, and descriptive (not inferential) verdict structure are all appropriate for the research question. The four unresolved minor items (m1, m2, m4, n1) are documentation precision issues that should be addressed in Phase 3 but do not threaten experimental validity.

One note for Phase 5: the directional consistency probability in Section 7 item 2 quotes 2.3% (per-run) rather than the joint probability of 0.052% (both runs independently exceeding ref+2SD). Report the joint probability if that pattern is observed.

*The science demands nothing less.*
