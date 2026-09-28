# Phase 2 Review: Crossover — Run D Replication + num_parents=2 Stagnation Attack

**Reviewer**: Prof. Andrei Volkov
**Date**: 2026-03-08
**Design document**: `experiments/hotpotqa/crossover/01_design.md`
**Verdict**: NEEDS REVISION

---

## Preliminary Assessment

The design is well-structured. Dr. Voss has correctly identified the two scientific questions
that emerge from the push experiment: whether Run D's above-GEPA result was genuine, and
whether crossover breaks the stagnation wall. The primary comparison hierarchy is explicit
(Run Q vs. Run P, within-experiment), confounds are acknowledged, and the amendment protocol
awareness is genuine. The throughput confound is pre-registered, not hidden — that is good
practice.

Nevertheless, I have found one critical flaw, two major concerns, and several minor issues
that must be resolved before pre-registration.

---

## Critical Concern

### C1: `max_elites_per_generation` override is absent from the Run Design Table — all throughput and combinatorics calculations in the design are wrong if this override is not applied

**Section**: 5 (Controlled Variables), 6 (Run Design Table), Appendix A (Code Verification)

**Finding**: The design lists `max_elites_per_generation: 8` as a controlled variable in
Section 5 and states: "With max_elites=8 and num_parents=2: C(8,2)=28 pairs, capped at
16 → 16 mutations/gen." This claim is factually correct *if and only if* the Hydra override
`max_elites_per_generation=8` is explicitly set at launch.

The default value in `config/constants/evolution.yaml` is:

```yaml
max_elites_per_generation: 5
```

This is confirmed by direct inspection. The prior experiment (push, PR #73) resolved this to
8 by including `max_elites_per_generation=8` as an explicit Hydra override in every launch
command in `experiments/hotpotqa/push/03_plan.md` lines 301–358 and in `launch.sh`.

The Section 6 Run Design Table in the current design has no column for
`max_elites_per_generation` and includes no note requiring this override. If Phase 3 produces
a `launch.sh` that does not include `max_elites_per_generation=8`, all three runs will execute
with max_elites=5 — not 8. The consequences are severe:

- **Run Q and Run R (num_parents=2)**: C(5,2)=10 parent pairs, none reaching the cap of 16.
  Actual throughput: **10 mutations/gen**, not 16. The design's claim of a "2x throughput
  advantage" is wrong: the ratio is 10 vs. 5 (still 2x, but the absolute numbers differ).
- **Run P (num_parents=1)**: C(5,1)=5 mutations per generation under max_mutations=8, not
  8. The design's pre-registered `max_mutations_per_generation=8` for Run P implies 8
  mutations/gen but with max_elites=5, only 5 are generated.
- **Appendix A claim**: "With max_elites=8 and num_parents=2: C(8,2)=28 pairs, capped at
  16 → 16 mutations/gen" is silently false if the override is omitted.

**Threat to validity**: All mechanistic reasoning in Sections 5 and 9 (throughput confound
analysis) is based on the wrong numbers. More importantly, comparability to prior experiments
(push Runs C and D, which used max_elites=8) is broken if max_elites=5 is used here, because
the archive diversity mechanism differs quantitatively.

**Required fix**: Add `max_elites_per_generation=8` to (1) the Run Design Table as an
explicit column or footnote, (2) the Section 5 controlled variables table with a note that
this requires an explicit Hydra override (not relying on the default), and (3) the pre-launch
checklist as a mandatory `--cfg job` verification item: "Confirm `max_elites_per_generation:
8` appears in the resolved config for all three runs." The combinatorics in Section 5 and
Appendix A should then be re-verified against the correct value.

---

## Major Concerns

### M1: H1(Q)'s 63.5% absolute floor appears in the narrative hypothesis but is absent from the Section 8 verdict table — criterion inconsistency between hypothesis and test

**Section**: 2 (Hypotheses, H1(Q)) vs. 8 (Statistical Test, Test 2)

**Finding**: Section 2 states:

> "H1(Q): F1+NLP+600 with num_parents=2 exceeds the single-parent result by >= 2.4pp
> (test EM(Q) - test EM(P) >= +2.4pp) **AND** test EM(Q) >= 63.5%."

This is a conjunctive criterion: both the delta threshold and the absolute floor must be
satisfied for H1(Q) to be accepted. However, the Section 8 Test 2 verdict table classifies
outcomes entirely on the basis of delta and McNemar p, with no reference to the 63.5%
floor:

| Delta | McNemar p | Verdict |
|---|---|---|
| >= +5.0pp | p < 0.05 | STRONG POSITIVE |
| [+2.4pp, +5.0pp) | p < 0.05 | POSITIVE |
| ... | ... | ... |

Under the Section 8 table, a result of delta = +3.0pp AND test EM(Q) = 62.0% (below 63.5%)
would be classified POSITIVE — but under H1(Q), it would fail the conjunctive criterion and
H1(Q) should not be declared accepted. This inconsistency between the pre-registered
hypothesis and the pre-registered decision table means Phase 5 analysis will have no
unambiguous rule to follow.

This is a recurring pattern in this research line: decision gates in Section 8 grow more
complex than the hypotheses in Section 2, or the reverse. The fix is mandatory alignment.

**Required fix**: Either (a) remove the conjunctive absolute floor from H1(Q) and state the
hypothesis purely in terms of delta (which then aligns with the verdict table), or (b) add
a third column to the Test 2 verdict table: "test EM(Q) >= 63.5%?" — making the POSITIVE
verdict require all three conditions. Choose one formulation and apply it consistently in
both Section 2 and Section 8. The choice must be made at pre-registration, not post-hoc.

I note that option (a) is scientifically cleaner for this experiment's purpose: Run Q beating
Run P by >= 2.4pp is the crossover mechanism test regardless of the absolute level. The
63.5% floor is a wish, not a mechanism criterion.

### M2: The noise floor calibration (2.4pp) was measured at step_max_tokens=2048, but this experiment uses step_max_tokens=8192 — the calibration may not transfer

**Section**: 7 (Sample Size Justification)

**Finding**: The design states:

> "The empirical retest noise floor from the p3_crossover design document is 2.4pp (from
> two evaluations of the ddce37b4 seed program on the same n=300 test set)."

The p3_crossover design document specifies this measurement explicitly:

> "Chain LLM: Qwen3-8B, thinking mode ON (default chat template), **step_max_tokens=2048**"

The current experiment uses `step_max_tokens=8192` for all LLM steps, which has been the
standard since the push experiment fixed it for 600-sample runs. Under thinking mode,
larger token budgets allow longer reasoning chains, which can produce different patterns of
LLM non-determinism: longer thoughts may improve consistency on simple items (reducing
sampling variance) while introducing new variance on complex items where the reasoning
explores divergent paths.

The 2.4pp noise floor is therefore an inter-setting measurement transferred to a different
evaluation configuration. The direction of the bias is unknown: the actual noise floor at
step_max_tokens=8192 may be higher or lower than 2.4pp. If it is higher (say, 3.5pp), then
a delta of +3.0pp would be below the actual noise floor despite being classified POSITIVE
under the pre-registered table.

**Threat to validity**: All effect size thresholds (POSITIVE at >= +2.4pp, SUGGESTIVE range
[+2.4pp, +5.0pp)) are calibrated against a measurement made under a different evaluation
configuration. The McNemar test is not affected by this (it operates on item-level
predictions and does not assume a particular noise floor), but the verbal classification of
results as "POSITIVE" or "NULL" is affected.

**Required fix**: The design should acknowledge this calibration transfer explicitly in
Section 7, with one of the following mitigations: (a) note that the 2.4pp threshold is a
lower bound on the true noise floor at step_max_tokens=8192 and interpret borderline results
(delta = 2.4–3.5pp) with additional caution; or (b) pre-register a same-program retest of
the ddce37b4 seed at step_max_tokens=8192 as a gen-0 calibration step (this takes ~10 minutes
and provides a calibrated noise floor for the current configuration). Option (b) is
preferable for scientific rigor but has a compute cost. Option (a) requires only a textual
acknowledgment with explicit caution language for the POSITIVE borderline zone.

---

## Minor Concerns

### m1: Run P verdict table has an unspecified outcome for the case [61.5%, 62.3%) with gap > 2.0pp

**Section**: 8 (Statistical Test, Test 1)

The verdict table reads:

| Test EM(P) | Verdict |
|---|---|
| >= 63.0% | STRONG POSITIVE |
| [62.3%, 63.0%) | POSITIVE |
| [61.5%, 62.3%) with gap <= 2.0pp | SUGGESTIVE |
| < 61.5% | NULL |

The case test EM(P) in [61.5%, 62.3%) with gap > 2.0pp has no specified verdict. This is
a well-populated region of probability space: if Run P scores 62.0% but the val-test gap
is +3.5pp (perfectly plausible given push Run C's +4.17pp gap under similar conditions),
Phase 5 has no pre-registered verdict to apply.

**Required fix**: Add a row for [61.5%, 62.3%) with gap > 2.0pp, or change the table
structure to explicitly handle the gap condition as a modifier rather than a determinant of
the primary EM verdict. A reasonable choice: [61.5%, 62.3%) with gap > 2.0pp → "PARTIAL
NULL — near-GEPA on EM but gap inconsistent with Run D's low-gap result; interpret as
failure of the gap-suppression mechanism, not necessarily as EM-level failure."

### m2: H1(cross) cross-run composite hypothesis has no corresponding formal test in Section 8

**Section**: 2 (Cross-run composite hypothesis) vs. 8 (Statistical Test)

Section 2 defines:

> "H1(cross): At least one of {Q, R} achieves test EM >= 63.5%..."

Section 8 contains Tests 1–4 but no formal test for H1(cross). A hypothesis without a
pre-registered test is an observation, not a pre-registered scientific claim. The composite
hypothesis as stated is fine as an informal summary of the experiment's ambition, but it
should either be elevated to a formal Test 5 in Section 8 (with a verdict table) or
explicitly demoted to "Informal summary, not a pre-registered test" in Section 2.

Given that Tests 2 and 3 already cover Q vs. P and R vs. C individually, a composite test
adds little. I recommend demoting it to an informal summary with explicit language: "This
is not a pre-registered test; it summarizes the individual verdicts from Tests 2 and 3."

### m3: Section 9 claims the throughput confound is analytically mitigated via per-generation frontier improvement inspection, but the Section 8 verdict table classifies a +2.4pp result as POSITIVE (not SUGGESTIVE) when McNemar p < 0.05, regardless of the throughput mechanism

**Section**: 5 (Controlled Variables, max_mutations note), 8 (Test 2), 9 (Confounds)

The Section 5 note on max_mutations states:

> "If Run Q beats Run P by >= 2.4pp under 2x throughput, the result is SUGGESTIVE (not
> POSITIVE) for the crossover mechanism and requires throughput-equalized follow-up."

However, Section 8 Test 2 classifies delta in [+2.4pp, +5.0pp) with McNemar p < 0.05 as
**POSITIVE** (not SUGGESTIVE). This creates a label inconsistency: the same result (+2.4pp,
p < 0.05) is "SUGGESTIVE" under Section 5 and "POSITIVE" under Section 8.

This matters because "POSITIVE" and "SUGGESTIVE" have different implications for what the
experiment concludes and what the required follow-up action is. A reader of the Phase 5
results document will encounter the conflict and not know which label applies.

**Required fix**: Harmonize the labels. The cleanest resolution is to rename Section 8's
[+2.4pp, +5.0pp) row to "POSITIVE (THROUGHPUT CONFOUNDED)" and add a note: "Crossover
exceeds noise floor under 2x throughput advantage. Requires throughput-equalized follow-up
to attribute gain to crossover quality vs. search volume. See Section 5 note." This is
consistent with the Section 5 text and makes the conclusion unambiguous.

### m4: The stagnation test H1_stag_Q uses "after birth-gen 10" as the threshold, but empirically stagnation is confirmed by birth-gen 4–8

**Section**: 2 (H1_stag_Q), 8 (Test 4)

H1_stag_Q requires "frontier improvement after birth-gen 10 in at least 5 consecutive
generations." The empirical stagnation ceiling is birth-gen 4–8 (confirmed across 11
runs). Setting the threshold at birth-gen 10 means that crossover-driven improvement
occurring between birth-gens 8 and 10 would not be counted by the H1_stag_Q criterion,
even though it would represent a genuine escape from the empirical ceiling.

This is a conservative choice that reduces the probability of a false positive for
H1_stag_Q — which is generally acceptable. However, the threshold should be explicitly
motivated: either "birth-gen 10 is conservative to avoid conflating normal early-phase
exploration with post-stagnation recovery" (if intentional), or the threshold should be
reduced to birth-gen 8 to match the empirical ceiling.

**Required fix**: Add one sentence in Section 8 Test 4 explaining why birth-gen 10 was
chosen over birth-gen 8. No change required if the conservative threshold is intentional
and acknowledged.

### m5: Section 9 confound table note on "NLP prompts silent failure" references checking prompts_dir in BOTH `evolution_context` AND `mutation_operator` blocks, but `hotpotqa_asi.yaml` has no `mutation_operator` block

**Section**: 9 (Confounds, NLP prompts silent failure)

The pre-launch check states:

> "must show `prompts_dir: .../hotpotqa` in BOTH `evolution_context` AND `mutation_operator`
> blocks."

Direct inspection of `config/pipeline/hotpotqa_asi.yaml` confirms there is no
`mutation_operator` block in this file. The `mutation_operator` with `prompts_dir:
${prompts.dir}` is configured in `config/algorithm/_base.yaml`, which is included globally.
The check as written will confuse the launcher: they will look for a `mutation_operator`
block in the YAML and not find it, potentially concluding (incorrectly) that the check
failed.

**Required fix**: Update the pre-launch check description to: "Confirm `prompts_dir:
.../hotpotqa` appears in the `evolution_context` block in `hotpotqa_asi.yaml` (already
present per 920c975). Confirm `prompts_dir: ${prompts.dir}` appears in the resolved
`--cfg job` output under `mutation_operator.prompts_dir`." The distinction between the
pipeline YAML (which contains `evolution_context`) and the algorithm base YAML (which
contains `mutation_operator`) should be made clear. The actual configuration is correct;
the pre-launch check description is imprecise.

---

## Verified Claims (No Concerns)

The following design claims were verified against the codebase and prior results:

- **num_parents default is 2**: `config/constants/evolution.yaml` sets `num_parents: 2`.
  The design's Risk 1 (Run P needs explicit `num_parents=1` override) is correct and
  appropriately flagged.

- **pipeline=hotpotqa_asi `prompts_dir` in `evolution_context`**: Present at line 24 of
  `config/pipeline/hotpotqa_asi.yaml`. No regression since push.

- **static_f1_600 `valid_frontier_em` key**: Confirmed populated in push Run D archive
  (via `run_status.py` and `results.json` which contains `val_em` from the F1 run). The
  design's claim that this is "confirmed working in push Run D" is correct.

- **item-level predictions for McNemar (push Run C)**: `experiments/hotpotqa/push/test_evals/
  results.json` contains `per_sample_correct` for Run C (300 binary values). Test 3 can
  run the McNemar comparison against push Run C's per-item predictions.

- **Push Run D best program birth-gen**: CSV inspection confirms the best program (highest
  F1 fitness) was born at `generation=5` in push Run D, consistent with the "birth-gen 4–8"
  stagnation pattern claimed for all prior runs.

- **NLP prompts objective framing (F1)**: `gigaevo/prompts/hotpotqa/mutation/system.txt`,
  `insights/system.txt`, and `lineage/user.txt` all use `{task_description}` injection.
  `problems/chains/hotpotqa/static_f1_600/task_description.txt` correctly describes F1
  fitness as the objective. No "exact match accuracy" hardcoding is present in the current
  NLP prompt files.

- **AllCombinationsParentSelector behavior and mutation_mode=rewrite**: Verified in
  Appendix A of the design document, consistent with prior p3_crossover verification.

- **dag_timeout=9000 calculation**: stage_timeout (6000) + mutation LLM stages (~1500) +
  safety headroom (1500) = 9000. This calculation is correct.

- **F1 < 1.0 equivalence to EM = 0**: Previously documented in memory. Not newly raised
  here because the design uses F1 fitness for selection but EM for primary evaluation —
  the equivalence applies only within validate.py's threshold logic, which is not the
  primary concern for this design.

---

## Summary of Required Changes

### Critical (must fix before pre-registration):

1. **[C1]** Add `max_elites_per_generation=8` as an explicit override requirement in:
   - Section 5 controlled variables table (add note: "requires explicit Hydra override;
     default in `config/constants/evolution.yaml` is 5")
   - Section 6 Run Design Table (add column or footnote)
   - Pre-launch checklist (mandatory `--cfg job` verification)
   - Correct or re-verify all combinatorics claims (C(8,2)=28, 16 mutations/gen for Q/R,
     8 mutations/gen for P) as contingent on the override being applied.

### Major (must fix or explicitly acknowledge):

2. **[M1]** Align H1(Q) criterion with Section 8 Test 2 verdict table. Either:
   - Remove the `test EM(Q) >= 63.5%` conjunctive floor from H1(Q) (recommended), or
   - Add it as a required column in the Test 2 verdict table.

3. **[M2]** Acknowledge the step_max_tokens mismatch in the noise floor calibration.
   Either add a cautionary note for delta = 2.4–3.5pp results, or pre-register a gen-0
   same-program retest at step_max_tokens=8192 to recalibrate the floor.

### Minor (fix or acknowledge):

4. **[m1]** Add a verdict for the unhandled case: Run P test EM in [61.5%, 62.3%) with
   gap > 2.0pp.

5. **[m2]** Demote H1(cross) to an informal summary or add a formal Test 5 in Section 8.

6. **[m3]** Harmonize SUGGESTIVE/POSITIVE labels between Section 5 note and Section 8
   Test 2 verdict table for the +2.4pp throughput-confounded outcome.

7. **[m4]** Add one sentence justifying the birth-gen 10 threshold in Test 4.

8. **[m5]** Correct the pre-launch check description to accurately describe where
   `mutation_operator.prompts_dir` is configured (algorithm `_base.yaml`, not
   `hotpotqa_asi.yaml`).

---

## Verdict

**NEEDS REVISION**

The critical concern (C1) is mechanically straightforward to fix — it requires adding one
Hydra override to three places in the document. The major concerns (M1, M2) require
precision work on the pre-registration language but no changes to the experimental design
itself. The minor concerns are documentation and presentation issues.

None of these flaws require redesigning the experiment. The scientific question is well-posed,
the primary comparison (Q vs. P) is the correct isolation, and the decision to accept the
throughput confound as pre-registered is defensible. Once the three critical and major issues
are resolved, this design is ready for pre-registration.

*The science demands nothing less.*

---

## Round 2 Review

**Reviewer**: Prof. Andrei Volkov
**Date**: 2026-03-08
**Verdict**: APPROVED

---

### Resolution of Round 1 Concerns

I have verified each concern from Round 1 against the revised design document. My findings follow.

#### C1: `max_elites_per_generation` override — RESOLVED

The fix is thorough and correctly applied in three places. Section 5 now includes an explicit
`[C1] Note` that quotes the default value (`max_elites_per_generation: 5`) and states
unambiguously that all four launch commands must include `max_elites_per_generation=8`. Section
6 adds a `max_elites` column to the Run Design Table with **8** bolded for all four runs. The
combinatorics verification table correctly shows C(8,2)=28 capped at 16 for crossover runs and
C(8,1)=8 for single-parent runs, with the caveat "contingent on override being applied." Section
12 elevates this to Risk 1. Run invalidation criterion 7 adds a post-hoc check. This concern is
fully resolved.

#### M1: H1(Q) criterion inconsistency — RESOLVED

The 63.5% conjunctive absolute floor has been removed from H1(Q). The revised hypothesis reads:

> "H1(Q): F1+NLP+600 with num_parents=2 exceeds the single-parent result by >= 2.4pp
> (test EM(Q) - test EM(P) >= +2.4pp)."

The 63.5% figure now appears only in the informal composite summary (Section 2), which is
explicitly labeled "not a pre-registered test." Section 8 Test 2 verdict table is aligned with
the delta-only criterion. The inconsistency is gone.

#### M2: Noise floor calibration transfer — RESOLVED (Option A, with added caution)

Section 7 now contains a dedicated subsection "Noise floor calibration — and its limitation"
that names the step_max_tokens mismatch (2048 vs. 8192), explains the directional uncertainty,
and pre-registers a caution protocol for the borderline zone delta ∈ [+2.4pp, +3.5pp). The
McNemar test is explicitly elevated as the primary instrument "precisely because it does not
rely on calibrated thresholds." This is an adequate and honest treatment. Option A is the
right choice here — option B (a pre-registered retest) would be preferable in principle, but
the additional compute overhead is not justified for a secondary measurement when the concern
is already bounded by the caution zone protocol.

#### m1: Unspecified verdict for [61.5%, 62.3%) with gap > 2.0pp — RESOLVED

Test 1 verdict table now has five rows instead of four. The new row is exactly as I specified:
`[61.5%, 62.3%) | > 2.0pp | PARTIAL NULL — near-GEPA on EM but gap-suppression mechanism
failed...` The table now covers all relevant outcome regions.

#### m2: H1(cross) composite hypothesis — RESOLVED

Section 2 now has a section titled "Informal composite summary (not a pre-registered test)"
with explicit language: "This is an informal characterization of the experiment's ambition,
not a pre-registered test. Individual verdicts are determined by Tests 1–5 in Section 8."
The concern is resolved.

#### m3: SUGGESTIVE/POSITIVE label inconsistency — RESOLVED

Section 5 throughput note now uses "POSITIVE (THROUGHPUT CONFOUNDED)" language that matches
Section 8 Test 2's verdict label exactly. The label is defined once in Test 2 and cross-
referenced in Section 5. The inconsistency is resolved.

#### m4: Birth-gen 10 threshold motivation — RESOLVED

Test 4 now includes the sentence: "The birth-gen 10 threshold is deliberately conservative —
two generations beyond the empirical stagnation ceiling of birth-gen 4–8 — to avoid conflating
early-phase exploration (where even single-parent runs occasionally produce frontier
improvements in gens 6–9) with genuine post-stagnation recovery." The motivation is explicit
and the trade-off (lower false positive rate at the cost of missing gens 8–10 improvements)
is acknowledged. This is a defensible design choice now properly documented.

#### m5: Pre-launch check description for mutation_operator.prompts_dir — RESOLVED

Section 9 confound table now correctly distinguishes the two locations:
(1) `evolution_context` block in `hotpotqa_asi.yaml` at line 24, and (2)
`mutation_operator.prompts_dir` in the resolved `--cfg job` output, noting this field lives
in `config/algorithm/_base.yaml` line 46. Appendix A item 3 makes the same distinction.
The pre-launch check is now unambiguous about what to look for and where to look for it.

---

### Assessment of Run S

The addition of Run S (F1+default+600, num_parents=1) completes the 2×2 factorial and
eliminates the cross-experiment reference problem I identified as a flaw in the original
design (using push Run C as the baseline for Run R). This is scientifically superior to the
original three-run design. Three aspects deserve specific evaluation.

**The factorial completion is correct.** The four cells — (num_parents ∈ {1,2}) ×
(prompts ∈ {hotpotqa, default}) — are fully crossed. All four runs share identical conditions
except the two IVs, with the fixed fitness metric (F1+600) as the common scaffold. The
primary comparisons (Q vs. P and R vs. S) are within-experiment and within-host, providing
clean isolation of the num_parents effect in each prompt setting. This is a well-executed
factorial extension.

**Run S's chain server placement is deliberate and non-trivial.** Runs R and S both use host
10.225.185.235 (ports 8001 and 8000 respectively), which means the R vs. S crossover comparison
is within-host — the gold standard for controlling infrastructure-level variance. Similarly,
Q and P are on host 10.226.17.25. The primary scientific comparisons (Q vs. P, R vs. S) are
each within a single physical host. This is a thoughtful infrastructure assignment.

**Test 5 (P vs. S) carries an unacknowledged cross-host confound that should be named.** The
comparison that isolates the NLP-prompt effect (Run P on 10.226.17.25:8001 vs. Run S on
10.225.185.235:8000) is the only one of the five tests that crosses physical hosts. The chain
client operates at temperature=1.0 with top_p=1.0 (confirmed from `problems/chains/client.py`)
— stochastic, non-deterministic, no shared random seed between hosts. This means that beyond
the 2.4pp within-host retest noise, the P vs. S comparison carries an additional cross-host
sampling variance component. The direction of the bias is unknown.

This is a minor concern. It does not invalidate Test 5 — the P vs. S comparison is still
scientifically informative, just slightly noisier than Tests 2 and 3. It does, however, make
the design's claim in the Primary Comparison Hierarchy that P vs. S are "running on the same
infrastructure" factually imprecise: they share the same experiment, the same mutation
infrastructure, and the same fitness function, but they run on different physical chain
servers. The claim should be qualified. The practical magnitude of the cross-host variance is
likely well below the 2.4pp noise floor for a fixed program (vLLM output distributions are
nearly deterministic given identical weights, tokenization, and sampling parameters), but
the uncertainty should be acknowledged rather than elided.

**No new methodological issues are introduced by Run S beyond this point.** The run
invalidation criteria in Section 10 apply symmetrically to all four runs. Run S's H0/H1
formulation is appropriately modest — it positions Run S as a concurrent control without
pre-registering a directional claim on its isolated performance, which is correct. The "5pp
anomaly" threshold in Section 9 for flagging Run S vs. push Run C deviations is a sensible
infrastructure health check.

---

### Residual Issues

The one new issue identified (Test 5 cross-host confound) is sufficiently minor that it does
not block pre-registration. It is a documentation precision issue, not a validity threat.
For completeness I record it here so it appears in the Phase 5 results document as a named
limitation.

**Residual minor issue (Test 5 cross-host confound)**: Section 2 Primary Comparison Hierarchy
states "both [P and S] are single-parent runs on the same infrastructure." This is imprecise:
P uses chain server 10.226.17.25:8001 and S uses 10.225.185.235:8000. The P vs. S comparison
is cross-host, unlike the primary comparisons Q vs. P and R vs. S which are within-host.
The chain LLM runs at temperature=1.0 (stochastic), so cross-host outputs are not
deterministically equivalent. The practical variance added by the cross-host configuration is
likely small relative to the 2.4pp noise floor, but the claim of "same infrastructure" overstates
the cleanliness of Test 5 relative to Tests 2 and 3. In Phase 5, this should be acknowledged
as a reason why a Test 5 NULL result is less informative than a Test 2 NULL (i.e., a null for
NLP prompts in Test 5 could reflect cross-host noise masking a real effect, whereas a null in
Test 2 has cleaner inferential standing). No design change is required.

---

### Final Assessment

All eight Round 1 concerns are resolved. The design is now a complete 2×2 factorial with four
concurrent runs, a clear primary comparison hierarchy, harmonized verdict labels, properly
documented override requirements, and an honest treatment of statistical limitations. The
scientific questions are focused, the pre-registration language is tight, and the known
confounds are named and assessed. The residual Test 5 cross-host issue is a limitation, not
a flaw.

This design may proceed to pre-registration.

**APPROVED**

*The science demands nothing less.*
