# Phase 2: Adversarial Review
<!-- Protocol version: 1.0 -->

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Design reviewed**: `experiments/hover/prompt_coevolution/01_design.md`
**Date**: 2026-03-20

---

## Summary of Design

This experiment tests whether co-evolving mutation prompts via a parallel GigaEvo instance, combined with soft fitness, improves HoVer test retrieval coverage beyond soft fitness alone. Two treatment pairs (main + prompt run, 1-to-1 topology) are compared against a historical control (Cell C from feedback_softfit, n=2, mean 54.37%). The single IV is mutation prompt source (fixed vs co-evolved); soft fitness is held constant.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|---------------|
| 1 | Port difference (8001 vs 8000) between treatment and Cell C historical control | **Major** | See detailed analysis below |
| 2 | Historical control adequacy: Cell C n=2 with SD=0.99pp | **Major** | See detailed analysis below |
| 3 | `prompt_evolution_hover` does not exist yet; no way to verify design claims about seed programs or task_description.txt | **Minor** | Acknowledged as code prerequisite. Acceptable, but the review cannot verify that the seed programs are well-constructed. Require the 3-gen smoke test (already specified) to serve as the de facto validation. |
| 4 | Gen-0 upper stop bound of 0.20 soft fitness may be too conservative | **Minor** | See detailed analysis below |
| 5 | Invalidation criterion #9 may be too strict for 1-to-1 topology | **Minor** | See detailed analysis below |

---

### Concern 1: Port difference (8001 vs 8000) -- Major

The design acknowledges this in Confound #9: Cell C used chain LLM ports 8000, this experiment uses 8001. The mitigation is to "verify model identity strings on all chain LLM endpoints." This is insufficient.

**The threat**: vLLM instances on different ports can have different `--tensor-parallel-size`, `--max-model-len`, `--gpu-memory-utilization`, `--max-num-seqs`, or quantization settings. Any of these can change generation quality or latency, which in turn changes timeout behavior and effective chain performance. A model identity string check verifies the weights but not the serving configuration.

**What is required**: The pre-launch checklist (Appendix A) must include explicit verification of serving configuration parity. Specifically:

- Query both `:8000/v1/models` and `:8001/v1/models` endpoints on at least one host. Confirm identical model IDs.
- Query `/v1/models` response metadata (or server logs) to confirm `max_model_len` and quantization match.
- Run a trivial chain evaluation (e.g., 10 samples) on both `:8000` and `:8001` and report results. If the two ports produce wildly different scores, the comparison with Cell C is invalid.

Alternatively, if ports 8000 are available at launch time, use them. The design says 8001 is used because "8000 ports may be occupied by other experiments." If those other experiments have concluded, the cleanest solution is to use the same ports as Cell C.

**Severity justification**: This co-varies with the IV (all treatment runs use 8001, all control runs used 8000) and can affect the DV. It is a classic confound. However, it is mitigable with pre-launch checks, which is why I rate it Major rather than Critical.

---

### Concern 2: Historical control adequacy -- Major

The entire experiment rests on comparing treatment (n=2) against Cell C (n=2, mean=54.37%, SD=0.99pp). The design is transparent about the statistical limitations: MDE is 4.26pp, and effects in the 2-4pp range will not reach significance. I commend the honesty. However, several issues remain:

**(a) Cell C SD is estimated from n=2.** The sample standard deviation from two observations is an extremely noisy estimator. The true population SD could easily be 2-3x larger. The MDE calculation assumes SD=0.99pp; if the true SD is 2.0pp, the MDE doubles. The design should acknowledge that the MDE estimate itself has high uncertainty.

**(b) No within-experiment control.** Confound #10 acknowledges this and proposes a post-hoc single control run "if treatment mean deviates drastically." This is reactive, not proactive. The fundamental problem: if both treatment runs score 53%, is that because co-evolution is regressive, or because infrastructure has drifted since Cell C? Without a concurrent control, these explanations are indistinguishable.

I understand the compute constraint (4 mutation LLM endpoints, all consumed by 2 main + 2 prompt runs). The design makes the best allocation given the constraints. But the limitation should be stated more forcefully: **the absence of a within-experiment control means that any result other than a large positive signal will be ambiguous with respect to infrastructure drift.**

**(c) Cell C is from the same day.** This partially mitigates (b). If launch occurs within 24-48 hours, infrastructure drift is unlikely. If launch is delayed by more than 48 hours, the design should require a single concurrent control run (dropping to n=1 treatment + n=1 prompt + n=1 control, sacrificing replication for drift detection). State this contingency explicitly.

**Resolution required**: (a) Add a sentence to Section 7 acknowledging that the MDE estimate is itself uncertain due to n=2 SD estimation. (b) Add a time-gate to Section 6: if launch occurs more than 72 hours after Cell C completion, a concurrent control run is required (specify how to reconfigure allocation). (c) Strengthen the language in Confound #10 to state explicitly that non-extreme results (e.g., treatment mean in [52%, 55%]) will be ambiguous without a concurrent control.

---

### Concern 3: `prompt_evolution_hover` code prerequisite -- Minor

The problem variant does not yet exist (`problems/prompt_evolution_hover/` is absent). The design correctly identifies this as a code prerequisite (Section 12, Open Question #1; Appendix A, item 1). The 3-gen smoke test (Appendix A, item 7) provides adequate protection against silent misconfiguration. No action required beyond what is already specified.

---

### Concern 4: Gen-0 upper stop bound -- Minor

Section 10 specifies: "Gen-0 val fitness > 0.20 (soft): Halt; initialization error." Cell C achieved soft val fitness ~0.78 by gen 25, starting from cold. What is the expected gen-0 soft val fitness for Cell C? The design says "Cold start should produce near-0.33 soft fitness at most." Is 0.33 based on empirical data from Cell C, or is it a theoretical upper bound (one hop out of three found by BM25 alone)?

If 0.33 is theoretical, the actual gen-0 value from Cell C should be cited. If Cell C's gen-0 soft val fitness was, say, 0.15, then 0.20 is a reasonable upper bound. If it was 0.30, then 0.20 is too tight and would cause spurious halts.

**Recommendation**: Report Cell C's actual gen-0 soft val fitness and calibrate the stop criterion accordingly. This is minor because the stop criterion can be adjusted during the smoke test without affecting the experimental design.

---

### Concern 5: Invalidation criterion #9 strictness -- Minor

Criterion #9: "Prompt run never produced a champion that was fetched by the main run (verified via prompt_stats keys in Redis: count > 0 and at least one prompt_id with trials >= 5)."

With 1-to-1 topology and ~8 trials/gen, it takes ~3 gens for a prompt to reach min_trials=5. If the prompt run's archive is slow to converge (Open Question #2), it is conceivable that no prompt reaches 5 trials until gen 4-5. If the main run completes before the prompt run reaches this threshold (e.g., due to stagnation-based early termination at gen 15), criterion #9 could invalidate a run that was functioning correctly but slowly.

**Recommendation**: Clarify that criterion #9 is evaluated at the end of the main run (not at any intermediate checkpoint). If the main run is terminated early (gen 15-20), the 5-trial threshold should be relaxed proportionally, or the criterion should require only that the prompt fetcher attempted to fetch (even if no champion met the threshold). This is minor because the 3-gen smoke test should catch genuine failures early.

---

## Hypothesis and Falsifiability

- [x] H0 is clearly stated
- [x] H1 is falsifiable and directional
- [x] Primary metric is pre-specified and sufficient to test H1
- [x] Success criteria are numeric and unambiguous

**Notes**: The effect-size threshold table (Section 2) is well-constructed and provides clear decision rules for every outcome region. The 2.00pp threshold is consistent with prior experiments. The INCONCLUSIVE category (one run above, one below) is a thoughtful addition that avoids forced binary verdicts from n=2 data.

The secondary hypothesis (H1_mech, prompt adaptation) is correctly labeled as descriptive rather than confirmatory, with the temporal autocorrelation caveat carried forward from HotpotQA. This is good scientific practice.

---

## Confound Analysis

- [x] All controlled variables are genuinely controlled (with port caveat above)
- [x] IV is isolated (single-factor: prompt source)
- [x] Known confounds are mitigated or acknowledged
- [x] Val/test split is not contaminated

**Unaddressed confounds**:

1. **Port difference (8001 vs 8000)**: Addressed above as Concern #1. The confound co-varies with the IV and is not adequately mitigated by model identity checks alone.

2. **Prompt run compute overhead affecting main run timing**: The prompt run and main run share a Redis server (different DBs). Under high load, Redis write-backs from the prompt stats aggregation could introduce microsecond-level latency to the main run's Redis reads. This is almost certainly negligible, but worth noting for completeness. No action required.

The confound analysis in Section 9 is thorough. Ten explicitly enumerated confounds with risk assessments and mitigations is above average for this field. I note in particular that Confounds #1 (cold-start lag), #6 (asymmetric comparison), and #7 (temporal autocorrelation) demonstrate genuine understanding of the co-evolution failure modes. These were hard-won lessons from the HotpotQA 13-amendment experience.

---

## Statistical Validity

- [x] Sample size is justified (compute-constrained; limitations acknowledged)
- [x] Statistical test is appropriate for the data (Welch's t, one-sided)
- [x] Significance threshold is pre-specified (alpha=0.05)
- [ ] Multiple comparison correction applied if testing multiple hypotheses

**Notes**:

The design specifies four statistical tests (Test 1-4). Tests 2-4 are labeled as secondary/exploratory, which partially addresses the multiple comparison issue. However, the design does not explicitly state whether the alpha=0.05 threshold applies only to Test 1 (the primary test), or whether family-wise error rate is a concern.

**Recommendation**: Add a single sentence to Section 8 stating that alpha=0.05 applies only to Test 1 (the primary comparison). Tests 2-4 are exploratory and their p-values, if reported, should be interpreted descriptively. This is consistent with the approach taken in the feedback_softfit design after my prior review.

The power analysis is honest about the MDE (4.26pp). The framing as a "directional probe" rather than a definitive test is appropriate. The pre-committed follow-up design (Section 7) is a responsible approach to underpowered experiments.

---

## Evaluation Protocol

- [x] Metric is computed identically across all conditions (discrete retrieval coverage, 300-sample test set, 5 repeats)
- [x] Val set and test set are fixed and identical for all runs
- [x] No metric is cherry-picked post-hoc
- [x] Thinking mode is consistent across all evaluations

**Notes**: The explicit statement that test evaluations use discrete scoring (not soft) is critical and well-placed. The val-test metric mismatch (soft val, discrete test) is acknowledged in Confound #8 with appropriate diagnostics. Appendix A item 4 (SHA-256 verification of test.py) provides a concrete safeguard.

---

## Required Changes Before Approval

1. **Section 6, Confound #9 / Appendix A**: Add explicit pre-launch verification of chain LLM serving configuration parity between ports 8001 and 8000. At minimum: (a) query `/v1/models` on both ports of at least one host and confirm identical model IDs, (b) confirm `max_model_len` matches, (c) run a trivial 10-sample evaluation on both ports and report scores. Alternatively, if ports 8000 are available, use them. *(Addresses Concern #1.)*

2. **Section 7**: Add a sentence acknowledging that the MDE estimate (4.26pp) is itself uncertain because the reference SD (0.99pp) is estimated from n=2. *(Addresses Concern #2a.)*

3. **Section 6 or Section 10**: Add a time-gate: if launch occurs more than 72 hours after Cell C completion (2026-03-20), require a concurrent within-experiment control run. Specify how to reconfigure the allocation (e.g., n=1 treatment + n=1 prompt + n=1 control + n=1 idle, or drop to 1 main + 1 prompt + 2 control). *(Addresses Concern #2c.)*

4. **Section 8**: Add a sentence clarifying that alpha=0.05 applies only to Test 1; Tests 2-4 are exploratory with descriptive p-values. *(Addresses Statistical Validity note.)*

---

## Round 2 Re-Review (2026-03-20)

Four changes were submitted in response to the NEEDS REVISION verdict. Assessment of each:

### Concern #1 (Port parity verification) -- RESOLVED

Appendix A item 8 now specifies a three-part pre-launch verification: (a) query `/v1/models` on both ports confirming identical model IDs, (b) confirm `max_model_len` matches, (c) run a 10-sample evaluation on both ports with a 5pp divergence threshold as the failure criterion. Fallback to port 8000 if parity fails. Confound #9 now explicitly states the confound "co-varies with the IV." This is exactly what was requested.

### Concern #2a (MDE uncertainty) -- RESOLVED

Section 7 now includes a caveat paragraph acknowledging that the SD estimate from n=2 is noisy, the true SD could be 1.5-2.5x larger, and the MDE could approximately double to ~8.5pp. The language is appropriately calibrated: it neither dismisses the concern nor catastrophizes it.

### Concern #2c (72-hour time-gate) -- RESOLVED

Section 6 now includes a time-gate: if launch occurs >72h after Cell C completion, a concurrent within-experiment control run is required. The reconfigured allocation is specified (n=1 treatment with 2 mutation endpoints + n=1 concurrent control with 1 chain LLM and 1 mutation endpoint + 1 idle endpoint). This accounts correctly for the 4-endpoint constraint and explicitly acknowledges the sacrifice of replication for drift detection.

### Statistical Validity (Alpha scoping) -- RESOLVED

Section 8 now explicitly states that alpha=0.05 applies only to Test 1; Tests 2-4 are exploratory with descriptive p-values. This is consistent with the approach adopted in the feedback_softfit design.

### Additional improvement noted

Confound #10 language was strengthened to state that "Any result other than a large positive signal will be ambiguous with respect to infrastructure drift" and that non-extreme results "cannot distinguish a genuine co-evolution effect from baseline shift." This is more honest than the original wording.

### Remaining minor concerns (non-blocking)

Concerns #3, #4, and #5 from Round 1 remain as noted. All are Minor severity and do not block approval. The 3-gen smoke test provides adequate protection for #3 and #5; the gen-0 upper bound (#4) can be calibrated during the smoke test without affecting the experimental design.

---

## Verdict

**[x] APPROVED** -- proceed to Phase 3

**[ ] NEEDS REVISION** -- address required changes, re-submit for review

**[ ] REJECTED** -- fundamental flaw; redesign required

**Reviewer notes (Round 1)**:

This is a well-motivated experiment with a clear scientific question. The mechanistic argument -- that soft fitness provides the gradient headroom that co-evolved prompts need to be effective -- is sound. The 1-to-1 topology choice is defensible and the tradeoffs (noisier prompt fitness for independent replications) are thoroughly analyzed. The decision tree (Appendix B) and cross-experiment comparison table (Appendix C) demonstrate the kind of programmatic thinking that accumulates scientific value across experiments.

The two Major concerns are both addressable. The port difference (Concern #1) is a straightforward confound that can be resolved with pre-launch verification or, better yet, by using the same ports. The historical control adequacy (Concern #2) is inherent to the compute constraints but can be strengthened with a time-gate and more explicit language about the ambiguity of non-extreme results.

I do not see any design flaws that require redesign. The experiment correctly isolates the single IV (prompt source), holds soft fitness constant, and specifies clear decision criteria. The confound analysis is the most thorough I have seen in this research program. The required changes are tightening moves, not structural repairs.

**Reviewer notes (Round 2)**:

All four required changes have been addressed precisely and without introducing new issues. The revisions are surgical -- they strengthen the design where it needed strengthening without altering the experimental structure. The port parity verification protocol (Appendix A, item 8) is particularly well-specified, with a concrete 5pp divergence threshold and a clear fallback plan. The MDE uncertainty caveat and time-gate are honest additions that improve the document's value as a pre-registration artifact.

Three minor concerns remain from Round 1. None block approval. The experiment is ready to proceed.

*The science demands nothing less.*
