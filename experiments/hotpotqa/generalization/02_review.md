# Phase 2: Adversarial Review -- Generalization via Held-Out Validation

**Reviewer**: Prof. Andrei Volkov (`reviewer-2-adversary`)
**Date**: 2026-03-14
**Design reviewed**: `experiments/hotpotqa/generalization/01_design.md`
**Review round**: 1

---

## Summary of Design

The experiment tests whether splitting the 1000 training samples into a 700-sample
evolution set and a 300-sample held-out validation set -- with composite fitness
mean(evo_F1, held_F1) and mutation feedback drawn only from the evo set -- produces
higher test EM than the cold_start reference (n=4, mean=59.58%, SD=1.00pp) which
uses single-set F1 fitness on 600 samples. The design runs n=4 cold-start treatment
runs and compares to the historical cold_start reference via one-sided one-sample
t-test.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|---------------|
| 1 | **Compound treatment: evo set size (700 vs 600) confounded with held-out mechanism** | **Major** | Strengthen acknowledgment and elevate deconfounding follow-up to a binding commitment. See Required Changes #1. |
| 2 | **Split bias check is not pre-registered as a binding decision** | **Major** | Pre-register exact protocol with halt/reshuffle rules. See Required Changes #2. |
| 3 | **Val EM comparability across conditions is not controlled (1000 vs 600)** | **Major** | Acknowledge or compute supplementary val EM on train[0:600]. See Required Changes #3. |
| 4 | **"Decoupling" novelty claim is overstated** | **Minor** | Qualify relative to val_gap rotating val set (Gate B). See Required Changes #4. |
| 5 | **Multiple secondary tests without explicit alpha-budget statement** | **Minor** | State that Tests 2-4 are exploratory and do not consume the alpha budget. See Required Changes #5. |
| 6 | **Gen-0 infrastructure drift check uses composite fitness** | **Minor** | Specify that check applies to evo_F1 component only. See Required Changes #6. |
| 7 | **Failure leakage verification is deferred without specifying method** | **Minor** | Add assertion or unit test requirement. See Required Changes #7. |
| 8 | **Discordant verdict cell is mathematically empty** | **Minor** | State explicitly. No action required beyond acknowledgment. |
| 9 | **stage_timeout based on extrapolation, not measurement** | **Minor** | Acceptable given Risk 1 pre-launch timing check. No action required. |
| 10 | **Composite fitness weighting overweights held-out samples** | **Minor** | Acknowledge the unequal per-sample influence. No action required but should be noted. |

---

## Hypothesis and Falsifiability

- [x] H0 is clearly stated
- [x] H1 is falsifiable and directional
- [x] Primary metric is pre-specified and sufficient to test H1
- [x] Success criteria are numeric and unambiguous

**Notes**: The hypotheses are well-specified. H0 and H1 are stated in terms of mean
test EM with explicit numeric thresholds. The directional prediction (val-test gap
<= 2.0pp) is pre-registered as a secondary expectation. The verdict table exhaustively
covers all outcome regions. The one-sided test is justified by the directional
hypothesis (the intervention is designed to improve, not merely change, test EM).

The MDE calculation is correct: (t_{0.05,3} + t_{0.20,3}) * SD / sqrt(n) =
(2.353 + 0.978) * 1.00 / 2.0 = 1.67pp. The power claim (>95% to detect +2.42pp)
is also correct: with SD=1.00, n=4, and delta=2.42, the noncentrality parameter is
2.42 / (1.00/2) = 4.84, which far exceeds t_{0.05,3} = 2.353.

The assumption that the treatment SD will match the cold_start SD (1.00pp) is
reasonable but unverifiable. The design correctly notes the risk at SD=1.50pp. This
is acknowledged; no action required.

---

## Confound Analysis

- [x] All controlled variables are genuinely controlled (with noted exceptions)
- [ ] IV is isolated (no other differences between conditions) -- **FAILS: Confound #1 (700 vs 600)**
- [x] Known confounds are mitigated or acknowledged
- [x] Val/test split is not contaminated

**Unaddressed confounds**:

1. **Evo-set size (700 vs 600)**: The most significant confound. The design
   acknowledges it (Section 9, Confound #1) but the mitigating argument is empirically
   uncalibrated. The claim that "the 100-sample difference is unlikely to explain a
   >2pp improvement based on prior evidence: push Run B (EM+600) and Run C (F1+600)
   both used 600 samples and scored 57-59% test EM" does not address the actual
   question -- whether 700 evo samples would outperform 600 evo samples under F1
   fitness, holding everything else constant. No prior experiment tests this margin.
   The val_gap Gate C (300 vs 600) was UNANSWERABLE due to Run Q invalidation. The
   push experiment compared 300 vs 600 under EM fitness, not F1. There is **zero
   empirical evidence** on the marginal effect of 100 additional evo samples under
   F1 fitness. The argument from absence is not a mitigation; it is a statement of
   ignorance. The confound is real but manageable via a deconfounding follow-up.

2. **Total evaluation samples differ (1000 vs 600)**: The treatment evaluates each
   candidate on 1000 total samples per generation (700 evo + 300 held-out). The
   cold_start control evaluates on 600. This means the treatment sees 400 more samples
   per generation. Any improvement could partially reflect the benefit of more total
   evaluation data informing selection, not the decoupling mechanism. This is entangled
   with the held-out design and cannot be separated within this experiment.

3. **Val EM denominator mismatch**: The val-test gap comparison (Test 2) uses val EM on
   1000 samples for the treatment vs val EM on 600 samples for cold_start. These are
   different evaluation populations. The gap values are not directly comparable. See
   Concern #3.

---

## Statistical Validity

- [x] Sample size is justified
- [x] Statistical test is appropriate for the data
- [x] Significance threshold is pre-specified
- [x] Multiple comparison correction applied if testing multiple hypotheses (only one primary)

**Notes**: The one-sample t-test against a known reference mean is the standard choice
when the reference is treated as a fixed constant. Strictly, the cold_start reference
has its own uncertainty (SE = 1.00/2 = 0.50pp), so the correct test is Welch's
two-sample t-test treating the cold_start raw data (T1-T4) as a second sample. Under
the one-sample formulation, the SE is 1.00/2 = 0.50pp. Under the two-sample
formulation, the pooled SE is sqrt(1^2/4 + 1^2/4) = 0.707pp, and the effective MDE
rises to (2.353 + 0.978) * 0.707 = 2.35pp. This means the experiment's power to detect
the SUGGESTIVE threshold (+0.92pp above reference) drops substantially under the
two-sample formulation.

However, for the pre-registered POSITIVE threshold (+2.42pp), the two-sample
t-statistic would be 2.42 / 0.707 = 3.42 with df~6 (Welch), giving p~0.007 -- still
significant. The anti-conservatism of the one-sample test does not change the verdict
for effects at or above the POSITIVE threshold.

I classify this as acceptable because (a) treating a well-estimated reference as a
constant is standard practice in sequential experimentation, and (b) the impact on
the primary verdict is negligible for effects above the MDE. The design should
acknowledge that the one-sample test is slightly anti-conservative if the treatment
SD matches the reference SD.

---

## Evaluation Protocol

- [x] Metric is computed identically across all conditions (test EM on 300-sample test set, thinking Qwen3-8B)
- [ ] Val set and test set are fixed and identical for all runs -- **val set differs** (1000 vs 600)
- [x] No metric is cherry-picked post-hoc
- [x] Thinking mode is consistent across all evaluations

**Notes**: The primary metric (test EM at gen 25, best-by-composite-fitness, 300-sample
test set, thinking mode) is identically computed across all treatment runs. The test
set is fixed and identical to cold_start.

The val set difference (1000 vs 600) affects the program selection mechanism: the
treatment selects the "best-by-composite-fitness" program, while cold_start selected
the "best-by-val-F1-on-600" program. This is an intentional part of the treatment
(composite fitness IS the intervention), not a confound. But it means the secondary
metric (val-test EM gap) is not comparable across conditions because the val EM
numerator is computed on different sets.

The "best-by-composite-fitness" selection rule also means the selected program may
differ from the "best-by-evo-F1" program. If the held-out component changes which
program is selected, any test EM improvement could be due to better program selection
(a regularization effect) rather than better program quality overall. This is actually
the intended mechanism, and the design correctly describes it. No issue here.

---

## Required Changes Before Approval

1. **[Major, Concern #1]** Section 9, Confound #1: Strengthen the confound acknowledgment
   for evo-set size (700 vs 600). Replace the current language ("The 100-sample difference
   is unlikely to explain a > 2pp improvement based on prior evidence") with: (a) "There
   is no direct empirical evidence from this project on the marginal effect of 100
   additional evo samples under F1 fitness." (b) Elevate the deconfounding follow-up from
   a suggestion ("would be needed if the result is POSITIVE") to a binding commitment:
   "If the primary verdict is POSITIVE or STRONG POSITIVE, the finding is classified as
   PRELIMINARY until a deconfounding follow-up (600 evo + 300 held-out + 100 unused)
   confirms the held-out mechanism as the causal driver."

2. **[Major, Concern #2]** Section 9, Confound #7, and Section 12, item 9: Pre-register
   the split bias check as a binding protocol. Specify: (a) If |evo_baseline_em -
   held_baseline_em| > 5pp at gen 0, halt and reshuffle train samples with seed=42 before
   launching any treatment runs. (b) The check is performed exactly once before any
   treatment data is collected. (c) If reshuffling is needed, document as Amendment 1 with
   "No confound" classification (uniform change, no data collected yet).

3. **[Major, Concern #3]** Section 8, Test 2: Acknowledge that the val-test gap comparison
   uses val EM on 1000 samples for the treatment vs val EM on 600 samples for cold_start.
   Either: (a) compute supplementary val EM on train[0:600] for the treatment runs to
   enable direct comparability with cold_start gaps (recommended), or (b) label Test 2 as
   "exploratory -- gap values are not directly comparable to cold_start gaps due to
   different val-set sizes" and remove the quantitative thresholds from the Test 2 verdict
   table (since the thresholds were calibrated on 600-sample gaps from cold_start).

4. **[Minor, Concern #4]** Section 14: Replace "the first experiment to decouple the
   selection signal (fitness) from the guidance signal (mutation feedback)" with "the first
   experiment to provide a fully deterministic separation between the selection signal and
   the guidance signal." The val_gap rotating val set (Run R, Gate B) provided partial,
   stochastic decoupling via hash-seeded sample rotation.

5. **[Minor, Concern #5]** Section 8: Add an explicit statement below the Test 4 table:
   "Tests 2, 3, and 4 are secondary/exploratory. Their p-values (where applicable) are
   reported for context only and do not consume the alpha budget. The primary verdict is
   determined solely by Test 1."

6. **[Minor, Concern #6]** Section 9, Confound #3: Specify that the gen-0 infrastructure
   drift check applies to the evo_F1 component (comparable to cold_start's gen-0 F1 on
   train[0:600]), not to the composite fitness. State: "Gen-0 evo_F1 should fall within
   [0.35, 0.50]; gen-0 composite_F1 may differ due to the held-out component."

7. **[Minor, Concern #7]** Section 12: Add a concrete verification method for failure
   isolation. Specify: "validate.py will include an assertion verifying that all failure
   cases originate from evo-set indices (< 700). This assertion will be tested pre-launch
   by running a single validation on the baseline chain and confirming no held-out indices
   appear in the returned failures list."

---

## Verdict

**[ ] APPROVED**

**[x] NEEDS REVISION** -- address required changes, re-submit for review

**[ ] REJECTED**

**Reviewer notes**: Three major concerns require resolution:

1. The evo-set size confound (700 vs 600) must be acknowledged with empirically honest
   language and a binding deconfounding commitment for POSITIVE/STRONG POSITIVE verdicts.
2. The split bias check must be pre-registered as a binding protocol with specified halt,
   reshuffle seed, and amendment classification -- not left as a suggestion with
   unspecified decision rules.
3. The val-test gap comparison (Test 2) must acknowledge the val-set size mismatch or be
   downgraded to exploratory with thresholds removed.

The four minor concerns (items 4-7) should also be addressed but would not block approval.

This is a well-motivated experiment targeting what is arguably the most important
remaining bottleneck in the GigaEvo HotpotQA program: the persistent val-test gap. The
held-out validation mechanism is the canonical solution to selection bias in supervised
learning, and the design applies it thoughtfully to the evolutionary setting. The
implementation notes (Section 12) are thorough and demonstrate awareness of critical
failure modes (failure leakage, pipeline selection, thinking mode verification). The
pre-registered risks (Section 2) are honest and well-enumerated. The core scientific
question is sound; the issues are in precision of pre-registration and acknowledgment
of confounds. No redesign is required.

*The science demands nothing less.*

---

## Round 2 Review

**Reviewer**: Prof. Andrei Volkov (`reviewer-2-adversary`)
**Date**: 2026-03-14
**Design reviewed**: `experiments/hotpotqa/generalization/01_design.md` (DRAFT v2)
**Review round**: 2

---

### Verification of Required Changes

| # | Severity | Concern | Addressed? | Assessment |
|---|----------|---------|------------|------------|
| 1 | **Major** | Evo-set size confound (700 vs 600): binding deconfounding commitment | **Yes** | Section 9, Confound #1 now states: "There is no direct empirical evidence from this project on the marginal effect of 100 additional evo samples under F1 fitness." The PRELIMINARY classification for POSITIVE/STRONG POSITIVE verdicts is present and correctly propagated to the Test 1 verdict table (Section 8) and Success Criteria Summary (Section 15). The deconfounding follow-up (600 evo + 300 held-out + 100 unused) is specified as a binding commitment. **Fully resolved.** |
| 2 | **Major** | Split bias check not pre-registered as binding protocol | **Yes** | Section 9, Confound #7 specifies: (a) halt-and-reshuffle threshold of 5pp, (b) seed=42 for reshuffling, (c) Amendment 1 with "No confound" classification, (d) performed exactly once before any treatment data. Section 12, item 9 mirrors this as a binding pre-launch checklist item. **Fully resolved.** |
| 3 | **Major** | Val-test gap comparability (1000 vs 600 val EM) | **Yes** | The design chose the stronger option (a): compute supplementary `val_em_600` = EM on train[0:600] for the gap comparison. Section 5 defines the secondary DV as "val_em_600 minus test EM." Section 8, Test 2 explicitly states that the full 1000-sample EM is "NOT used for the gap comparison (different val-set sizes would render the comparison invalid)." Section 12 implementation notes include the `val_em_600` computation with correct slicing (`evo_targets[:600]`, which corresponds to train[0:600] since the evo set is train[0:700]). **Fully resolved.** |
| 4 | **Minor** | "Decoupling" novelty claim overstated | **Yes** | Section 14 now reads "the first experiment to provide a fully deterministic separation between the selection signal and the guidance signal." The note on val_gap Run R providing "partial, stochastic decoupling via hash-seeded sample rotation" is included. **Fully resolved.** |
| 5 | **Minor** | Alpha budget statement for Tests 2-4 | **Yes** | Section 8 contains: "Tests 2, 3, and 4 are secondary/exploratory. Their p-values (where applicable) are reported for context only and do not consume the alpha budget. The primary verdict is determined solely by Test 1." **Fully resolved.** |
| 6 | **Minor** | Gen-0 check applies to evo_F1, not composite | **Yes** | Section 9, Confound #3 now specifies: "Gen-0 evo_F1 should fall within [0.35, 0.50] (comparable to cold_start gen-0 F1 on train[0:600]). Gen-0 composite_F1 may differ slightly due to the held-out component." **Fully resolved.** |
| 7 | **Minor** | Failure leakage verification method | **Yes** | Section 12 specifies: assertion on `idx < 700` for all failure cases, with pre-launch verification by running a single baseline validation and confirming no held-out indices appear. The method is concrete and testable. **Fully resolved.** |

### Assessment of Revisions

All three major concerns and all four minor concerns have been fully addressed. The revisions are technically correct and internally consistent -- the PRELIMINARY label propagates cleanly through the verdict table, the `val_em_600` metric is properly defined and implemented, and the split bias protocol is specified with sufficient precision to be auditable.

I note one observation that does not rise to "concern" level but is worth recording: the `val_em_600` computation (`evo_targets[:600]`) evaluates a strict subset of the evo set. This means the `val_em_600` metric is computed on samples that the mutation LLM does see as failure cases -- it is not an independent metric. This is fine for comparability with cold_start (which also computes val EM on mutation-visible samples), and it is the correct choice. But it means `val_em_600` should not be interpreted as a "held-out" metric. The design does not make this mistake; I note it for the record.

---

### Verdict

**[x] APPROVED**

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**: All seven required changes from Round 1 have been correctly and completely addressed. The design is methodologically sound, the confounds are honestly acknowledged with binding commitments, and the pre-registration is tight enough to be auditable. The PRELIMINARY classification for positive results is the right call -- it preserves the ability to claim a result while honestly flagging the evo-set size confound as unresolved within this experiment.

This is a well-designed experiment targeting the right bottleneck with the right intervention. Proceed to Phase 3.

*The science demands nothing less.*

---

## Round 4 Review

**Reviewer**: Prof. Andrei Volkov (`reviewer-2-adversary`)
**Date**: 2026-03-14
**Design reviewed**: `experiments/hotpotqa/generalization/01_design.md` (DRAFT v3)
**Review round**: 4 (focused check on R3-2 resolution + regression check on items 11-14)

---

### Verification of R3-2 (Major): Binding prompt review item

The sole outstanding concern from Round 3 was:

> **R3-2 (Major)**: Add a binding pre-launch verification step (Item 14) requiring
> documented human confirmation that the implemented generalization prompt satisfies
> all four content requirements before any run launches.

**Item 14 text** (Section 12, Pre-launch verification checklist):

> 14. **Binding prompt review (BINDING -- generalization prompts are the treatment)**:
>     Before launching any run, a human reviewer must read the implemented
>     `gigaevo/prompts/generalization/` mutation prompt and confirm in writing
>     (comment in 03_plan.md or PR) that it satisfies all four content requirements:
>     (a) sampling framing -- failures are a sample, not exhaustive;
>     (b) process-over-examples -- prefer general reasoning improvements;
>     (c) anti-overfitting directive -- avoid example-specific prompt language;
>     (d) held-out awareness -- mutations evaluated on unseen examples.
>     No treatment run may launch until this confirmation is documented.

**Checklist against the five acceptance criteria**:

| # | Criterion | Met? | Assessment |
|---|-----------|------|------------|
| 1 | Present and numbered as item 14 | **Yes** | Item 14, Section 12 |
| 2 | Labelled BINDING | **Yes** | "BINDING" appears in the item label |
| 3 | Requires human confirmation in writing (documented in 03_plan.md or PR comment) | **Yes** | "confirm in writing (comment in 03_plan.md or PR)" |
| 4 | Covers all four content requirements | **Yes** | (a) sampling framing, (b) process-over-examples, (c) anti-overfitting directive, (d) held-out awareness -- all four present and named |
| 5 | Explicitly blocks run launch until confirmation is documented | **Yes** | "No treatment run may launch until this confirmation is documented." |

**Assessment**: Item 14 satisfies all five acceptance criteria completely. The language
is unambiguous, the blocking condition is explicit, and the four content requirements
are enumerated with sufficient specificity to be auditable. **R3-2 is fully resolved.**

---

### Regression Check: Items 11-13 (added in v3 revision)

Items 11-14 were added together in the v3 revision. While Item 14 was the sole
required change from Round 3, I must verify that Items 11-13 do not introduce new
concerns. They read:

> 11. Verify `gigaevo/prompts/generalization/` directory exists on disk and contains
>     at minimum a mutation operator prompt override file
> 12. Verify `prompts=generalization` resolves correctly: run
>     `python run.py ... prompts=generalization --cfg job`
>     and confirm `prompts.dir` resolves to the generalization prompts directory
> 13. Verify G3/G4 LLM config: run with `llm=gemini31_pro` and confirm
>     `llm._target_` resolves to `gigaevo.llm.models.MultiModelRouter` with model
>     `google/gemini-3.1-pro-preview`; confirm `OPENAI_API_KEY` is set in `.env`

**Concern R4-1 (Major): Items 11-13 contradict the Run Design Table (Section 6).**

The Run Design Table (Section 6) specifies `prompts=default` for all four runs (G1-G4)
and makes no mention of a Gemini LLM or `llm=gemini31_pro` for any run. Yet:

- Items 11 and 12 presuppose a `prompts=generalization` override, which contradicts
  the `prompts=default` column in the run table.
- Item 13 presupposes G3/G4 use `llm=gemini31_pro`, which appears nowhere in the
  Run Design Table. If G3/G4 use a different mutation LLM than G1/G2, this is a
  second independent variable that must be declared in Section 4, controlled for in
  the run design, and analyzed as a potential confound. As written, it silently
  transforms a single-IV experiment into a 2-IV experiment without any of the
  required pre-registration apparatus (factorial design, interaction analysis,
  confound discussion).
- Item 14 references "generalization prompts" as "the treatment," which is
  inconsistent with the Run Design Table stating `prompts=default`.

These contradictions create an ambiguity that is fatal to pre-registration integrity:
a reader cannot determine from this document what the actual treatment conditions are.
Either (a) the Run Design Table is stale and should be updated to reflect custom
prompts and a Gemini LLM for G3/G4, in which case the IV table, confound analysis,
and statistical design all require revision; or (b) Items 11-13 were added in error
and should be removed, with Item 14 revised to reference whatever prompt configuration
is actually intended.

This must be resolved before approval.

---

### Verdict

**[ ] APPROVED**

**[x] NEEDS REVISION** -- address R4-1 before re-submission

**[ ] REJECTED**

**Required change**:

1. **[Major, R4-1]** Resolve the contradiction between the Run Design Table (Section 6,
   which specifies `prompts=default` for all runs and no Gemini LLM) and checklist
   Items 11-13 (which presuppose `prompts=generalization` and `llm=gemini31_pro` for
   G3/G4). Specifically:
   - If the experiment uses custom generalization prompts for all runs, update the Run
     Design Table `prompts` column from `default` to `generalization` and ensure Section 4
     (Independent Variables) accounts for the prompt change as part of the treatment.
   - If G3/G4 use a different mutation LLM (Gemini), this is a second IV. Either remove
     it (all runs use the same LLM) or redesign as a factorial with the LLM variable
     declared, confounded, and analyzed.
   - If Items 11-13 were added in error and the experiment truly uses `prompts=default`
     with no Gemini LLM, remove Items 11-13 and revise Item 14 to reference the actual
     prompt configuration.
   - The Run Design Table is the canonical specification of what each run executes.
     Every checklist item must be consistent with it.

**Reviewer notes**: Item 14 itself is well-constructed and satisfies all five acceptance
criteria from the R3-2 requirement. However, the v3 revision introduced Items 11-13
alongside Item 14, and these three items contain references to `prompts=generalization`
and `llm=gemini31_pro` that directly contradict the Run Design Table. A pre-registration
document with internal contradictions about the treatment conditions cannot be approved.
The fix is straightforward -- either update the Run Design Table to match the checklist
or remove the erroneous checklist items -- but it must be done explicitly.

*The science demands nothing less.*

---

## Round 5 Review

**Reviewer**: Prof. Andrei Volkov (`reviewer-2-adversary`)
**Date**: 2026-03-14
**Design reviewed**: `experiments/hotpotqa/generalization/01_design.md` (DRAFT v4)
**Review round**: 5 (focused check on R4-1 resolution)

---

### Verification of R4-1 (Major): Run Design Table consistency with Items 11-13

The sole outstanding concern from Round 4 was:

> **R4-1 (Major)**: The Run Design Table in Section 6 contradicted checklist Items 11-13
> by showing `prompts=default` and no `llm` column. Fix the table to reflect
> `prompts=generalization` for all 4 runs, and show the `llm` split (G1/G2: Qwen3-235B
> vLLM, G3/G4: gemini31_pro).

**Sub-check 1: `prompts=generalization` for all four runs.**

The Run Design Table (Section 6) now shows a `prompts` column with value `generalization`
for G1, G2, G3, and G4. This is consistent with Items 11 and 12 in the checklist.
**PASS.**

**Sub-check 2: `llm` column with correct split.**

The Run Design Table now includes an `llm` column:
- G1, G2: `default (Qwen3-235B vLLM)`
- G3, G4: `gemini31_pro (Gemini-3.1-Pro-Preview)`

This is consistent with Item 13. **PASS.**

**Sub-check 3: Note below table no longer says "default prompts."**

The note below the Run Design Table reads: "The treatment differs from the control on
three dimensions: (a) held-out fitness computation, (b) generalization mutation prompts,
and (c) Gemini-3.1-Pro mutation LLM for G3/G4." No stale "default prompts" language
remains. **PASS.**

**Sub-check 4: No new contradictions introduced.**

One minor issue identified:

**R5-1 (Minor): Dangling reference to Confound #8.** The note below the Run Design Table
(Section 6) ends with "See Section 9, Confound #8." However, Section 9 contains only
Confounds #1 through #7. There is no Confound #8 entry discussing the Gemini LLM split
for G3/G4. This is a dangling cross-reference. The treatment conditions themselves are
now unambiguous (the Run Design Table is the canonical specification and it is correct),
but the promised confound analysis for the LLM variable is absent from Section 9.

This does not block approval for two reasons: (1) the Gemini mutation LLM variable was
already present in the approved v2 design of the gemini_mutation experiment and its
confound characteristics are well-understood from that prior work; (2) the Run Design
Table now clearly shows the split, so no reader can be misled about what each run
executes. However, the dangling reference should be fixed before `03_plan.md` is
committed -- either add a Confound #8 entry or remove the "See Section 9, Confound #8"
reference and fold the acknowledgment into the note itself.

---

### Verdict

**[x] APPROVED** -- with one minor note (R5-1) to fix before committing `03_plan.md`

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**: The R4-1 concern is fully resolved. The Run Design Table now
unambiguously specifies `prompts=generalization` for all four runs and shows the
`llm` split between Qwen3-235B (G1/G2) and Gemini-3.1-Pro (G3/G4). The note below
the table correctly enumerates all three dimensions of difference from the cold_start
reference. Items 11-14 in the checklist are now fully consistent with the Run Design
Table. The one remaining minor issue (dangling Confound #8 reference) does not affect
pre-registration integrity and should be cleaned up before Phase 3.

Five rounds of review across two days. The design is tight. Proceed to Phase 3.

*The science demands nothing less.*

---

## Round 6 Review

**Reviewer**: Prof. Andrei Volkov (`reviewer-2-adversary`)
**Date**: 2026-03-14
**Design reviewed**: `experiments/hotpotqa/generalization/01_design.md` (DRAFT v5)
**Review round**: 6 (focused review of three v5 changes: fitness = held_F1 only; evo_f1 include_in_prompts: true; checklist item 15(e))

---

### Change 1: fitness = held_F1 only (previously mean(evo_F1, held_F1))

Section 2 now includes a "Why held_F1 only" subsection (lines 45-59) explaining that
averaging partially re-introduces the confound the held-out mechanism was meant to break.
The argument is scientifically correct: if fitness includes evo_F1, programs are still
partially selected on the same data the mutation LLM uses for guidance, diluting the
regularization signal. The clean analogy -- train on train, select on val -- holds only
when the selection criterion excludes the training loss entirely.

**Internal consistency check**: The change propagates cleanly through the document.

| Location | Expected | Actual | Status |
|----------|----------|--------|--------|
| Section 2 (line 35) | fitness = held_F1 | "fitness = held_F1 only" | PASS |
| Section 4 IV table (line 116) | held_F1 only | "held_F1 on train[700:1000] only (pure held-out selection signal)" | PASS |
| Section 5 DV table (line 131) | Held-out F1 = fitness | "Held-out F1 (= fitness)" | PASS |
| Section 5 primary metric (line 135) | best-by-held_F1 | "best-by-held_F1 program" | PASS |
| Section 6 Run Design Table (line 144) | Fitness = held_F1 | All four runs show "held_F1" | PASS |
| Section 9 Confound #1 (line 241) | Selection signal independent of evo set | "fitness = held_F1 only, the evo-set size does NOT pollute the selection signal" | PASS |
| Section 9 Confound #5 (line 245) | Reflects held_F1-only | "With held_F1 as the sole fitness, evo-set performance has zero influence on selection" | PASS |
| Section 12 code (line 301) | `"fitness": held_f1` | Correct | PASS |
| Section 12 metrics.yaml (line 344) | fitness is_primary: true | Correct | PASS |
| Section 10 stop criterion #4 (line 260) | Uses held_F1 for invalidation | "Gen-0 held_F1 (fitness) > 0.55" | PASS |

The held_F1-only fitness is an improvement over the averaging design. It makes the
train/val separation complete and eliminates a subtle re-contamination pathway. The
trade-off (noisier fitness from 300 samples vs 600) is correctly identified in Risk 2
(line 495) and Risk 6 (line 523). No concerns.

---

### Change 2: evo_f1: include_in_prompts: true (previously false)

This is the change that requires the most careful scrutiny. The design argues (Section 12,
lines 316-338) that showing the evo_F1 *score* to the mutation LLM is safe because:

1. Failure *examples* are drawn exclusively from the evo set (invariant enforced by the
   failure leakage assertion).
2. A scalar score cannot enable exploitation of held-out-specific patterns -- the LLM has
   no held-out examples to act on.
3. The gap signal (evo_F1 - held_F1) is useful: it tells the LLM when the current program
   overfits to evo-set patterns, enabling it to propose more general improvements.

**Assessment**: The argument is sound. The critical invariant is the failure example
boundary, not the score visibility boundary. In supervised learning, it is standard
practice to show a model both its training loss and validation loss -- the validation loss
informs the optimization trajectory without leaking validation examples. The analogy holds
here: the mutation LLM sees (a) evo-set failure examples (the gradient), (b) evo_F1
(training loss), and (c) held_F1 (validation loss). No held-out examples leak.

Could the LLM game the gap by proposing changes that artificially suppress evo_F1 rather
than genuinely improving held_F1? This is theoretically possible but practically
irrelevant: (a) fitness = held_F1 only, so suppressing evo_F1 without improving held_F1
yields zero fitness gain; (b) the mutation LLM proposes prompt modifications, not
evaluation tricks -- it cannot manipulate which samples score correctly without changing
the underlying reasoning strategy; (c) MAP-Elites selects solely on held_F1, so any
evo_F1-suppressing mutation that does not also improve held_F1 is filtered out.

The metrics.yaml specification (lines 340-403) is internally consistent: `fitness` and
`evo_f1` both have `include_in_prompts: true`; `em` and `val_em_600` have
`include_in_prompts: false`. The descriptions are thorough and correctly state the
invariant. Checklist item 6 (line 447) verifies this configuration pre-launch.

**No concerns.** The change is scientifically justified and the safeguards are adequate.

---

### Change 3: Checklist item 15(e) -- gap interpretation in mutation prompt

Item 15 (lines 467-480) now requires five content requirements for the binding prompt
review, up from four. The new requirement (e) states:

> (e) gap interpretation -- the prompt explicitly names `evo_f1` and `fitness`
>     (= held_F1), explains their meaning, and instructs the mutation LLM that
>     a large (evo_f1 - fitness) gap indicates overfitting to the evo set, so
>     it should prioritize changes that improve held-out performance over changes
>     that merely polish evo-set scores.

**Assessment**: This is well-specified. It operationalizes the gap signal from Change 2
into a concrete prompt instruction. The requirement is auditable: a human reviewer can
verify that the implemented prompt contains these elements. The language is specific enough
to prevent a prompt that merely shows both scores without explaining their relationship.

One observation: the requirement instructs the LLM to "prioritize changes that improve
held-out performance," but the LLM has no held-out failure examples to guide such changes.
The LLM can observe *that* the gap exists but cannot directly diagnose *why* -- it only
has evo-set failures. The practical effect is that the LLM should prefer changes to
general reasoning patterns (which will improve both sets) over changes that target
specific evo-set failure modes. This is exactly what requirement (b) ("process-over-
examples") already captures. Requirement (e) reinforces (b) with the gap signal as
quantitative evidence. This is coherent, not redundant. No concern.

---

### Outstanding Issues

**R6-1 (Minor, carried from R5-1): Dangling Confound #8 reference.**

Section 6, line 152 still reads: "See Section 9, Confound #8." Section 9 contains only
Confounds #1 through #7. This was flagged as R5-1 and acknowledged as a minor issue that
should be fixed before committing `03_plan.md`. It remains unfixed in v5.

The fix is trivial: either add a Confound #8 entry to Section 9 describing the compound
treatment (held-out fitness + generalization prompts + Gemini LLM for G3/G4), or remove
the "See Section 9, Confound #8" reference and fold the acknowledgment directly into
the Section 6 note. The current note text already enumerates all three dimensions
adequately; the dangling reference adds nothing except confusion.

This does not block approval (the treatment conditions are unambiguously specified in the
Run Design Table), but it must be fixed before `03_plan.md` is committed.

---

### Verdict

**[x] APPROVED** -- with one carried minor (R6-1 = R5-1) to fix before committing `03_plan.md`

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**: The three v5 changes are scientifically sound and internally
consistent.

1. **fitness = held_F1 only** is the correct design choice. Averaging diluted the
   regularization signal; removing evo_F1 from fitness completes the train/val separation.
   The trade-off (noisier fitness from 300 samples) is honestly acknowledged in Risks 2, 3,
   and 6.

2. **evo_f1: include_in_prompts: true** is safe and beneficial. The critical invariant is
   the failure *example* boundary, not the score visibility boundary. Showing the evo_F1
   score alongside held_F1 gives the mutation LLM a generalization gap signal without
   leaking held-out examples. The failure leakage assertion (Section 12) guards the
   invariant that matters.

3. **Checklist item 15(e)** correctly operationalizes the gap signal into a verifiable
   prompt content requirement. It reinforces requirement (b) with quantitative evidence
   and is specific enough to be auditable.

The one remaining minor (dangling Confound #8 reference, first flagged in Round 5) must
be resolved before `03_plan.md` is committed. It is a cross-reference cleanup, not a
scientific concern.

Six rounds. The design is tight.

*The science demands nothing less.*
