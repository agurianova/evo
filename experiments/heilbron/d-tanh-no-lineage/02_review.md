# Reviewer-2 Report: D-Side Tanh Smoothing + LineageStage Removal from D Pipeline

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Date**: 2026-04-25
**Design document**: `experiments/heilbron/d-tanh-no-lineage/01_design.md`
**Round**: 1

---

## Summary of Design

This experiment tests two simultaneous interventions on the D (Improver) pipeline relative to `adversarial-repro-v2` (NULL, mu_G=0.03315): (1) replacing the hard-floor D fitness formula with continuous tanh scoring (carried from the INVALID `d-smoothing-minimal` predecessor), and (2) removing `SharedBenchmarkFilteredLineageStage` and its fan-out stages from D's pipeline via a new `disable_lineage_on_improver` flag. The research question is whether removing LineageStage's compute overhead -- identified as the root cause of `d-smoothing-minimal`'s 1.84x D/G timing asymmetry that invalidated the predecessor -- restores D compute parity and allows the tanh fitness signal to produce G lift.

The comparison structure is well-articulated: 1 IV vs d-smoothing-minimal (LineageStage presence), 2 IVs vs v2 (tanh + no-lineage). The cleanest causal claim flows from the d-smoothing-minimal comparison, but d-smoothing-minimal is INVALID with no mu_G data point, which limits its utility as a scientific control (more below).

---

## Summary Assessment

Elena has produced a characteristically thorough design that learns from d-smoothing-minimal's failure in the right ways. The D/G gen-pace ratio gate at gen 5 is the correct mechanistic check -- it directly addresses the structural reason the predecessor was invalidated. The treatment verification checks (tanh active, lineage absent) are concrete and falsifiable. The compound treatment is defended on valid pragmatic grounds. The Volkov C1 fix from d-smoothing-minimal (metrics.yaml description freeze) is correctly preserved (Section 5, line 187).

I have identified one critical concern, two major concerns, and several minor issues.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|----------------|
| C1 | D/G gen-pace ratio threshold of >= 1.0 is poorly calibrated; threshold choice is undefended | **Critical** | Justify threshold or lower it; define what happens in the 0.8--1.0 gray zone |
| M1 | d-smoothing-minimal is INVALID with no mu_G -- the "1 IV comparison" is structurally empty | **Major** | Acknowledge the attribution limitation honestly; reframe the primary comparison |
| M2 | `disable_lineage_on_improver` ordering hazard: the new gate must fire BEFORE `_resolve_lineage_filter` to avoid a `ValueError` crash path | **Major** | Specify exact placement relative to `_resolve_lineage_filter`; add negative test |
| m1 | `refresh_passes=2` is zombie config on D with non-trivial scheduling overhead that may confuse future readers | Minor | Document explicitly in 03_plan.md that this is dead config retained for IV control |
| m2 | Wall-clock estimate (18--24h) is optimistic; no sensitivity analysis for the case where D is faster but G is unchanged | Minor | Acknowledge that if D runs 2--4x faster than G, G becomes the wall-clock bottleneck |
| m3 | The mechanistic prediction D/G ratio "trend back toward v1-era 2x--4x" (Section 2.2a) is an expectation, not a falsifiable bound | Minor | State explicitly: what D/G ratio range would be SURPRISING? |
| m4 | Missing positive log-line specification for the implementer | Minor | Require a specific log line format for `disable_lineage_on_improver=true` activation |
| m5 | Literature scout recommendation on `archive_reeval=false` not directly addressed | Minor | Respond to the scout's argument that v1's 4x D/G ratio ran under `archive_reeval=false` |

---

## Critical Concerns

### C1. D/G Gen-Pace Ratio Threshold (>= 1.0) Is Poorly Calibrated and Undefended

**Severity: CRITICAL**

The primary mechanistic check (Section 2.2a) requires D/G gen-pace ratio >= 1.0 at gen 5, with failure (ratio < 1.0 across 3+ of 4 pairs) triggering `running -> invalid`. This threshold is the experiment's kill switch -- the most consequential pre-registered decision in the design. Yet the choice of 1.0 receives no justification beyond "D no slower than G."

The historical data tells a more nuanced story:

| Experiment | D/G Ratio | Condition | mu_G |
|---|---|---|---|
| adversarial-repro-v1 | 4.00x (2.28--6.66) | No lineage, hard-floor | 0.03413 |
| adversarial-repro-v2 | 1.29x (0.80--1.65) | Lineage ON | 0.03315 |
| d-smoothing-minimal | 0.57x | Lineage ON, tanh | INVALID (aborted) |

The d-smoothing-minimal issues log (ISSUE-001) identifies TWO contributors to D's slowness: (1) intrinsic D evaluation cost (structural, cannot be eliminated), and (2) LineageStage overhead. Removing LineageStage eliminates contributor (2) but NOT contributor (1). The intrinsic asymmetry -- Improver runs optimization-style improvement per opponent while Constructor just emits 11 points -- is permanent.

**The critical question Elena does not answer**: what fraction of d-smoothing-minimal's 1.84x slowdown was due to LineageStage vs intrinsic evaluation cost? If LineageStage contributed 60% of the overhead, removing it brings the ratio from 0.57x to roughly 1.43x. If LineageStage contributed only 30%, the ratio recovers to approximately 0.81x -- which would FAIL the >= 1.0 threshold and invalidate the experiment despite the treatment being correctly applied.

The design acknowledges this possibility obliquely ("If D/G gen-pace ratio at gen 5 < 1.0 across 3+ of 4 pairs, the experiment is uninterpretable for the same structural reason that d-smoothing-minimal was," Section 2.2a). But a ratio of 0.85x is qualitatively different from d-smoothing-minimal's 0.57x -- it would represent a substantial improvement (49% faster D) that nonetheless falls below the 1.0 bright line.

**The gray zone (0.7--1.0) is undefined.** A ratio of 0.8 means D is still slower than G, but dramatically improved from 0.57. Is this "uninterpretable"? The experiment would be producing useful data about tanh fitness under moderately asymmetric timing. Invalidating it throws away that data.

Note also that v2's own D/G ratio included C2 at 0.80x (D actually behind G), yet v2 was not invalidated -- it ran to completion and produced a valid NULL verdict. The >= 1.0 threshold is stricter than what the project accepted for v2.

**Required fix**: (a) Justify why 1.0 is the right threshold, not 0.8 or 0.7. What is the mechanistic argument that D must be AT LEAST as fast as G for the tanh signal to produce G lift? The WGAN-GP literature Elena cites argues for K=5 D updates per G update -- i.e., D MUCH faster than G. If the theoretical framework says D should be faster, then 1.0 is already generous. But if parity is sufficient, 0.8 might also be acceptable. (b) Define explicit handling for the gray zone: if D/G ratio is between 0.7 and 1.0 across 3+ pairs, the experiment continues with an amendment noting the partial timing fix, rather than transitioning to INVALID. Only ratios below 0.7 (minimal improvement from d-smoothing-minimal's 0.57) should trigger INVALID.

---

## Major Concerns

### M1. The "1 IV vs d-smoothing-minimal" Comparison Is Structurally Empty

**Severity: MAJOR**

The design's cleanest causal claim rests on comparing this experiment to d-smoothing-minimal: "if this experiment succeeds where d-smoothing-minimal was invalidated, the causal claim is 'removing LineageStage from D restores D compute parity, enabling the tanh fitness signal to produce G lift'" (Section 1, lines 23-24).

But d-smoothing-minimal has no mu_G data point. It was aborted at 15h with G gens 24-31 and D gens 14-17. There is no estimable mu_G, no D fitness distribution at gen 20 or 50, no arms-race trajectory to compare against. The "comparison" consists of: (a) d-smoothing-minimal's D/G ratio was 0.57x; this experiment's should be > 1.0; and (b) d-smoothing-minimal was INVALID; this experiment should not be. That is a comparison of experiment validity status, not a scientific comparison of treatment effects.

The design states: "If this experiment also produces a NULL, the claim is 'D-side smoothing (with or without lineage) is insufficient'" (Section 1, line 24). But this NULL inference is weak: d-smoothing-minimal never ran long enough to establish whether tanh + lineage-ON would have been NULL or POSITIVE. A NULL here could mean (a) tanh + no-lineage is insufficient, OR (b) tanh + lineage-ON would also have been NULL if timing were fixed differently, OR (c) the compound of tanh + no-lineage introduces a new failure mode (e.g., D mutation quality degrades without lineage context). These cannot be disentangled against an INVALID predecessor.

The actual informative comparison is against v2 (which has complete data: mu_G=0.03315, D fitness distributions, arms-race trajectories, D/G ratio). Against v2, the design has 2 confounded IVs, but at least both conditions have complete DV measurements.

**Required fix**: Reframe the comparison hierarchy. The v2 comparison is the primary quantitative comparison (complete data, 2 confounded IVs). The d-smoothing-minimal comparison is a mechanistic check (timing restoration), not a fitness-outcome comparison. Do not call it "cleanest" when it has no DV data. The design already handles this correctly in the effect-size thresholds (Section 2.1 anchors to v2 and baseline-repro, not to d-smoothing-minimal) -- the framing in Section 1 simply needs to match the analysis plan.

### M2. Implementation Ordering Hazard: `disable_lineage_on_improver` Must Gate BEFORE `_resolve_lineage_filter`

**Severity: MAJOR**

Section 13.1, Change 2 shows the proposed code:

```python
if population_role == "improver":
    if disable_lineage_on_improver:
        self.remove_stage("LineageStage")
        ...
    else:
        resolved_filter = _resolve_lineage_filter(...)
        self._replace_lineage_with_filtered(...)
```

I have read the current code at `asymmetric_pipeline.py` lines 206-215. The existing block is:

```python
if population_role == "improver":
    resolved_filter = _resolve_lineage_filter(
        lineage_filter, ctx.problem_ctx.metrics_context
    )
    self._replace_lineage_with_filtered(...)
```

The `_resolve_lineage_filter` function (lines 80-113) contains an explicit guard: `raise ValueError("lineage_filter.aggregator required -- no silent fallback")` when `lineage_filter` is misconfigured. The codebase_map confirms this at line 157-158: "the code path has **no 'skip lineage' branch**."

The hazard: if the implementer places the `disable_lineage_on_improver` check AFTER the `_resolve_lineage_filter` call (e.g., as a post-hoc removal rather than a pre-emptive gate), the `_resolve_lineage_filter` will still execute and may crash if the Hydra config omits the aggregator. More critically, if a future refactor moves the `_resolve_lineage_filter` call outside the `if population_role == "improver"` block, the `disable_lineage_on_improver` gate becomes inert.

The design's code specification (Section 13.1) shows the correct placement, but does not explicitly state the ordering invariant or require a test for it.

**Required fix**: (a) Add an explicit note in Section 13.1 stating: "The `disable_lineage_on_improver` gate MUST short-circuit BEFORE `_resolve_lineage_filter` is called. If `disable_lineage_on_improver=True`, the function `_resolve_lineage_filter` must never execute for that run." (b) Require a unit test that instantiates the builder with `disable_lineage_on_improver=True` and `lineage_filter=None` and verifies that no `ValueError` is raised and that `"LineageStage"` is absent from `self._nodes`. This test protects against the ordering hazard surviving into implementation.

---

## Minor Concerns

### m1. `refresh_passes=2` Is Zombie Config with Non-Trivial Scheduling Overhead

Section 3.1 documents that `refresh_passes=2` with LineageStage absent causes pass 2 to find all stages up-to-date and do nothing useful. The design correctly identifies this as "dead config" retained for IV control parity with v2. This is the right decision for confound management.

However, "dead config" is not zero-cost. The `_refresh_pass_token` bump and the subsequent full-DAG walk to check hash freshness still execute. At O(archive_size) per epoch, with D archives of 170-190 programs, this is non-trivial scheduling overhead.

**Recommendation**: Flag in 03_plan.md as a secondary observation target. If D/G ratio at gen 5 is >= 1.0 but only barely (e.g., 1.05x), the zombie refresh may be a contributing drag worth investigating in a follow-up.

### m2. Wall-Clock Estimate May Be Optimistic

Section 16 estimates 18-24h wall time. If D runs 2-4x faster than G (the expected v1-era regime), then G becomes the wall-clock bottleneck. G's per-gen pace was ~1990s (~33 min) in d-smoothing-minimal and has no reason to change in this experiment (G pipeline is unchanged). At 33 min/gen, reaching gen 50 on G requires approximately 27.5h -- close to the 28h hard cap.

**Recommendation**: State the per-gen wall-clock assumption for G and derive the expected G generation depth at 28h.

### m3. D/G Ratio Expectation Is Not a Falsifiable Bound

Section 2.2a states: "we expect the ratio to trend back toward the v1-era range (2x--4x)." This is a reasonable expectation but not a pre-registered prediction with pass/fail criteria. A ratio of 1.5x would "trend toward" v1 without being in the 2-4x range.

**Recommendation**: State explicitly what D/G ratio at gen 5 would be SURPRISING (e.g., "A ratio below 1.5x at gen 5 would suggest the intrinsic D evaluation cost is the dominant bottleneck and that LineageStage removal alone is insufficient to restore v1-era D compute advantage").

### m4. Positive Log-Line Specification

Section 11.1 says D run logs "SHOULD contain" a line indicating lineage removal. Absence-based verification (checking that LineageStage markers are NOT present) is weaker than presence-based verification (checking that a removal confirmation IS present).

**Recommendation**: Promote "SHOULD" to "MUST" and specify the exact log line format.

### m5. Literature Scout Recommendation on `archive_reeval=false` Not Directly Addressed

The literature brief (Recommendations for Elena, "On the two-pass refresh interaction") explicitly recommends setting `archive_reeval=false` on D, noting that v1's 4x D/G ratio ran under that configuration. Elena retains `archive_reeval=true` with a valid defense (Section 3.1: minimizing IVs vs v2). However, the scout's strongest point -- that v1's D compute advantage was achieved under `archive_reeval=false` -- deserves a direct response.

**Recommendation**: Add one sentence to Section 3.1 or Confound 5: "We accept that retaining `archive_reeval=true` on D reduces D's effective speed advantage relative to v1. If D/G ratio is >= 1.0 but substantially below v1's 4.0x, `archive_reeval` is a candidate IV for the next experiment."

---

## Consistency with Prior Review (d-smoothing-minimal Round 2)

| Prior Ruling | Current Design | Status |
|---|---|---|
| C1: metrics.yaml description freeze (Round 1 critical) | Section 5, line 187: `"Frozen identical to v2"` -- exact v2 wording preserved verbatim. Section 3, line 101: "metrics.yaml fitness description is NOT changed" | **PASS** |
| M1: mechanistic claim relabeled as treatment verification (Round 1 major) | Section 2.2 is "Treatment Verification Check (Code-Application Diagnostic)"; Section 2.2a contains genuine mechanistic predictions with gen 5/20 checkpoints | **PASS** |
| m5: smoke test tightened to < 5% (Round 1 minor) | Section 11.4 check 2: "fitness < 0.001 fraction < 5%" | **PASS** |

Elena has correctly preserved all prior rulings. Self-consistency is maintained.

---

## Hypothesis and Falsifiability

- [x] H0 clearly stated (mu_G <= 0.03449)
- [x] H1 falsifiable and directional (mu_G > 0.03449)
- [x] Primary metric pre-specified (best-ever actual_fitness, grand mean across 4 G runs)
- [x] Success criteria numeric and unambiguous (four-tier threshold table in Section 2.1)
- [x] Mechanistic predictions have quantitative pass/fail criteria (D fitness shape at gen 5/20, D/G ratio at gen 5)
- [x] Abandon direction specified (Section 2.3)

## Confound Analysis

- [x] Compound treatment acknowledged and defended (Section 3.2, three observations)
- [x] Controlled variables genuinely controlled (Section 5 is comprehensive)
- [x] G-side code confound carried from d-smoothing-minimal and acknowledged (Confound 2)
- [x] `archive_reeval` / `refresh_passes` zombie config documented as derived consequence (Section 3.1, Confound 7)
- [x] metrics.yaml prompt parity preserved (Volkov C1 from prior review -- PASS)
- [x] Redis flush pre-launch specified (Confound 4)
- [x] Historical comparator justified (Confound 6)
- [x] Exception-path incentive documented (Confound 8)

The confound analysis is thorough. Section 9.1 ("Volkov-Targeted Preempts") is noted -- preemptive defense is welcome when the defense is substantive, as it is here.

## Statistical Validity

- [x] N=4 honestly stated and underpowered acknowledged (Section 7)
- [x] Bootstrap CI as primary output (Section 8)
- [x] Power analysis at ~30% for SUGGESTIVE threshold -- acknowledged per PATTERNS.md protocol gap
- [x] Effect-size thresholds, not p-values, drive verdict

No issues. The power analysis is honest and I do not require more at N=4.

## Evaluation Protocol

- [x] Primary DV (actual_fitness) computed identically to v2 via unchanged `pop_a/evaluate.py`
- [x] No post-hoc metric selection
- [x] Stop criteria concrete: `max_generations=200`, 28h hard cap, D/G ratio gate at gen 5
- [x] Treatment verification checks specified in detail (Sections 11.1-11.5)

## Information Gain Assessment

PATTERNS.md contains two relevant entries: "SBF-Lineage on broken D fitness produces no lift" (SUGGESTIVE) and "Two-pass bucketed refresh destroys D compute advantage" (SUGGESTIVE). This experiment removes both the lineage stage and its associated refresh overhead from D, while simultaneously applying the tanh fitness fix. The combination (tanh + no-lineage) has never been tested (literature brief confirms this). The experiment has high expected information gain per compute hour. A POSITIVE result is actionable; a NULL result redirects cleanly toward the full REDESIGN bundle.

---

## Required Changes Before Approval

1. **C1 (Critical)**: Calibrate the D/G ratio threshold. Either (a) justify >= 1.0 with a mechanistic argument, or (b) define a gray zone (e.g., 0.7 <= ratio < 1.0 continues with amendment; ratio < 0.7 triggers INVALID). The current bright line at 1.0 risks invalidating an experiment that has substantially fixed the timing problem.

2. **M1 (Major)**: Reframe the d-smoothing-minimal comparison as a mechanistic check (timing restoration), not as the "cleanest" causal comparison for mu_G. The primary quantitative comparison is against v2 (complete data). Adjust Section 1 language accordingly.

3. **M2 (Major)**: Add an explicit ordering invariant for the `disable_lineage_on_improver` gate relative to `_resolve_lineage_filter`. Require a unit test that verifies: builder with `disable_lineage_on_improver=True` and `lineage_filter=None` does not crash and produces a DAG without LineageStage nodes.

---

## Verdict

**[x] NEEDS REVISION**

One critical concern (C1: D/G ratio threshold poorly calibrated) and two major concerns (M1: empty comparison elevated to "cleanest"; M2: implementation ordering hazard without test requirement) must be resolved. All three fixes are localized -- no redesign required. The minor concerns (m1-m5) should be addressed but do not block approval.

This is a well-motivated experiment targeting the confirmed root cause of d-smoothing-minimal's failure. The design demonstrates genuine learning from the predecessor's issues log. The compound treatment defense (Section 3.2) is persuasive. The treatment verification protocol (Section 11) is the most detailed I have reviewed in the heilbron series. Once C1, M1, and M2 are addressed, I expect to approve on the next round.

*The science demands nothing less.*

---

## Round 3 Review (2026-04-25)

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Scope**: Round 2 to Round 3 revisions (Section 3.1 cache/pass semantics, Section 5a refresh_passes row, Confound 7, Volkov-Targeted Preempt #2). Verification that Round 1 issues (C1, M1, M2) remain resolved.

---

### 1. Prior-Round Issue Disposition

| Round 1 Issue | Status in Round 3 | Assessment |
|---|---|---|
| **C1**: D/G gen-pace ratio threshold poorly calibrated | **RESOLVED** | Graded gate remains in place: Green >= 0.90, Yellow [0.70, 0.90), Red < 0.70 with `running -> invalid`. Sections 2.2a, 2.3, 4, 8, 10, 14.2, 15.2 are internally consistent. The 0.70 cutoff justification (29% improvement over d-smoothing-minimal's 0.54x) and the 0.90 green threshold justification (more demanding than v2's NULL-producing 0.80x) are unchanged and sound. No drift. |
| **M1**: d-smoothing-minimal comparison framing | **RESOLVED** | v2 is the primary quantitative comparator (Section 1, first row of comparison table: "Effect-size estimation for mu_G. Both conditions have complete data."). d-smoothing-minimal is the mechanistic/validity predecessor (Section 1, second row: "Binary question: does removing LineageStage prevent the timing-asymmetry abort?"). The language "cleanest" is absent. No drift. |
| **M2**: `disable_lineage_on_improver` ordering invariant + unit test + `log_pattern_absent` | **RESOLVED** | The ordering invariant is stated explicitly in Section 13.1 ("ORDERING INVARIANT" paragraph). The required unit test `test_no_lineage_on_improver_skips_filter_resolution` is specified with three assertions. Section 11.5 `log_pattern_absent` includes `"lineage_filter.aggregator required"` with severity ABORT. Section 11.1 includes the positive activation log line promoted to MUST. No drift. |

All three prior issues remain correctly addressed. The Round 2-to-3 revisions did not disturb any of them.

---

### 2. Round 3 Revision: Cache/Pass Semantics Assessment

The Round 3 changes are limited to sharpening the description of `archive_reeval=true` and `refresh_passes=2` under the no-lineage regime. I have verified the code citations against the actual source files. My findings:

#### 2.1 `archive_reeval=true` semantics

The design states (Section 3.1): "`archive_reeval=true` selects `InputHashCache` (cached evaluator: re-runs only when opponent IDs change), while `archive_reeval=false` selects `NO_CACHE` (always re-runs). Read the flag as 'let the input-hash cache decide', not 'always re-evaluate'."

**Code verification**: `gigaevo/adversarial/stages.py:156-159` confirms:
```python
def get_cache_handler(self):
    return DEFAULT_CACHE if self._archive_reeval else NO_CACHE
```
And `gigaevo/adversarial/pipeline.py:204-205` confirms the comment:
```
# archive_reeval=True  -> InputHashCache (reruns only when opponent IDs change)
# archive_reeval=False -> NO_CACHE (always reruns)
```

The design's characterization is precise and matches the code. The "backwards-named" observation is correct: the natural reading of `archive_reeval=true` as "always re-evaluate" is the opposite of the actual behavior. This is a genuine platform naming hazard worth documenting, and Elena has done so.

#### 2.2 `refresh_passes=2` pass-2 behavior under no-lineage

The design states (Section 3.1): "pass 1 re-runs `DGTrackerStage` globally; pass 2 re-runs the filtered `LineageStage` with a globally-fresh tracker. [...] With `LineageStage` removed on D, pass-2 fires no LLM call -- it reduces to a `MutationContextStage` refresh."

**Code verification**: `gigaevo/evolution/engine/steady_state.py:807-817` confirms the docstring:
```
Pass 1 re-runs DGTrackerStage globally. Pass 2 re-runs the filtered
LineageStage with a globally-fresh tracker.
```
The mechanism is: `_write_snapshot` bumps `refresh_pass` before each pass (line 830-832), which cache-invalidates stages keyed on it (specifically `SharedBenchmarkFilteredLineageStage.compute_hash` at `shared_benchmark_lineage.py:87-99` suffixes the hash with `:rp{rp}`). With `SharedBenchmarkFilteredLineageStage` absent from the DAG, the bump has no LLM-bearing consumer. The remaining stages (`DGTrackerStage`, `MutationContextStage`, etc.) either have no pass-keyed cache or are not LLM-bound. The claim that pass-2 fires no LLM call under no-lineage is correct.

#### 2.3 v1 reasoning correction

The design states (Section 3.1): "v1's `archive_reeval=false` meant *more* eval work per epoch (NO_CACHE), so v1's 4.0x ratio came from v1's lack of lineage, not from skipping the cache."

This is a sound inference. `archive_reeval=false` selects `NO_CACHE`, which means every archive program re-evaluates every refresh, regardless of whether opponent IDs changed. This is strictly more work than `InputHashCache`. The fact that v1 ran faster (4.0x D/G ratio) despite doing more eval work per refresh confirms that the speed difference was dominated by v1's absence of lineage LLM calls, not by any cache advantage.

#### 2.4 "Independent of LineageStage" claim

The design states (Section 3.1): "cache invalidation lives on the evaluator, not on lineage" and (Section 9, Confound 7): "the load-bearing archive-freshness path [...] is independent of `LineageStage`."

This is correct. The `InputHashCache` on `FetchOpponentResultsStage` is keyed on opponent IDs (constructed in `FetchOpponentIdsStage`). `LineageStage` is a downstream consumer of opponent results, not an upstream provider. Removing `LineageStage` does not affect whether the evaluator cache-misses on opponent-ID change.

#### 2.5 Cross-Section Consistency Check

I have verified that the cache/pass semantics are described consistently across the four modified locations:

| Section | Claim | Consistent? |
|---|---|---|
| 3.1 (full analysis) | `archive_reeval=true` = `InputHashCache`; cache invalidates on opponent-ID change; independent of `LineageStage`. `refresh_passes=2` pass-2 fires no LLM under no-lineage; reduces to `MutationContextStage` refresh. Dominant per-gen drag was pass-2 lineage LLM call. | Anchor |
| 5a (refresh_passes row) | "pass-2 fires **no LLM call** -- it reduces to a `MutationContextStage` refresh (O(archive_size) bookkeeping). The load-bearing archive-freshness path is `archive_reeval=true`'s opponent-ID-keyed cache, not the pass count." | Consistent with 3.1. |
| 9 (Confound 7) | "`archive_reeval=true` (= `InputHashCache`, backwards-named) still invalidates the D evaluator on opponent-ID changes -- the load-bearing archive-freshness path -- and is independent of LineageStage. `refresh_passes=2`'s pass-2 normally re-runs filtered LineageStage; with LineageStage absent it reduces to a `MutationContextStage` refresh and fires no LLM call." | Consistent with 3.1. |
| 9.1 Preempt #2 | Repeats the full analysis with code citations (`pipeline.py:204-205`, `stages.py:131-159`, `steady_state.py:780-900`, `shared_benchmark_lineage.py:60-159`). States: "The behavioral difference (no pass-2 lineage LLM) is a derived consequence of IV 2 (lineage removal). The archive-freshness mechanism is preserved via the evaluator cache; only the per-refresh lineage LLM cost is eliminated." | Consistent with 3.1. |

No contradictions detected across the four locations.

---

### 3. Treatment Specification Integrity Check

The primary treatment specification consists of two IVs:
1. D-side tanh fitness scoring (`pop_b/evaluate.py` change)
2. `disable_lineage_on_improver=true` on D runs (`asymmetric_pipeline.py` change)

I have verified that the Round 3 revisions did not alter the treatment definition. The treatment is unchanged from Round 1. The Round 3 changes are exclusively about the *description* of controlled-variable behavior, not about the treatment itself. The IV table (Section 3), the extra-overrides lists (Section 6.1), and the code specification (Section 13) are untouched by Round 3 revisions.

---

### 4. New Concerns from Round 3 Revisions

#### 4.1 "Dominant per-gen drag was the pass-2 lineage LLM call" -- falsifiability

Section 3.1 states: "The mechanism that lifts D's per-gen wall time is the elimination of pass-2's lineage LLM call."

This is a mechanistic claim about *why* D speeds up, not merely an observation that D speeds up. It is pre-registered only implicitly: the D/G gen-pace ratio gate (Section 2.2a) measures the *outcome* (did D speed up?) but not the *mechanism* (was the lineage LLM call the bottleneck?).

Strictly speaking, this is not a confound or a design flaw. The claim is consistent with d-smoothing-minimal's ISSUE-001 diagnosis and with the PATTERNS.md entry "Two-pass bucketed refresh destroys D compute advantage." But it IS an untested mechanistic attribution. D could speed up for other reasons (e.g., fewer valid programs under tanh -> shorter queues -> faster throughput), and the design would not distinguish these explanations.

**Severity: Not even Minor.** This is an observation, not a concern. The D/G ratio gate tests the *consequence* of the claim. If the ratio enters the Green zone, the mechanistic explanation is plausible and the experiment proceeds; if it enters the Yellow or Red zone, the mechanistic explanation is weakened. The design does not need to instrument the individual pass-2 wall-clock cost to test the fitness hypothesis. The mechanistic attribution is a narrative interpretation of the pre-registered D/G ratio measurement, not a separate hypothesis requiring separate testing. I flag it here for transparency, not as a required change.

#### 4.2 No new confounds, hidden IVs, or unaddressed DVs

The Round 3 revisions are purely descriptive -- they sharpen the explanation of existing controlled-variable behavior. They do not introduce any new configuration value, any new code path, or any new treatment element. The DV table (Section 4) is adequate for capturing any behavioral consequences of the refined understanding: D/G gen-pace ratio already captures timing effects, and D fitness distribution already captures evaluation-path effects. No additional DV is needed.

---

### 5. Summary Assessment

The Round 3 revisions resolve the one remaining imprecision from Round 2: the description of `archive_reeval` and `refresh_passes` behavior under the no-lineage regime. The revised Section 3.1 is now code-verified, internally consistent across all four locations where these mechanisms are discussed, and correctly identifies the `InputHashCache` opponent-ID-keyed invalidation as the load-bearing archive-freshness path independent of `LineageStage`.

The key factual corrections are all accurate:
- `archive_reeval=true` selects `InputHashCache`, not "always re-evaluate." Verified.
- `archive_reeval=false` selects `NO_CACHE` (more work, not less). Verified.
- v1's 4.0x D/G ratio was due to no-lineage, not cache configuration. Sound inference.
- Pass-2 under no-lineage fires no LLM call. Verified.
- The evaluator cache is independent of `LineageStage`. Verified.

The treatment specification (D tanh + `disable_lineage_on_improver=true`) is unchanged. The C1 graded gate, M1 comparison framing, and M2 ordering invariant + test requirement all remain correctly in place.

No new confounds, hidden IVs, or design flaws were introduced by the Round 3 revisions.

---

### Verdict

**[x] APPROVED**

All critical and major concerns from Round 1 are resolved. The Round 3 cache/pass-semantics revisions are code-verified, internally consistent, and factually correct. The treatment specification is unchanged and well-specified. The graded D/G ratio gate, the v2-as-primary-quantitative-comparator framing, and the `disable_lineage_on_improver` ordering invariant with required unit test are all intact. The design is ready for pre-registration and implementation.

*The science demands nothing less.*

---

## Round 4 Review (2026-04-25)

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Scope**: Round 3 to Round 4 revisions. The primary change is setting `engine_config.refresh_passes` on D from `2` to `1`, justified by a per-stage cache-mode trace showing pass 2 is a no-op under the no-lineage regime. Sections modified: 3.1, 5a, 6.1, 9 (Confounds 5 and 7), 9.1 (Preempt #2), 11.3, 19.

---

### 1. Prior-Round Issue Disposition

| Round 1 Issue | Status in Round 4 | Assessment |
|---|---|---|
| **C1**: D/G gen-pace ratio graded gate | **INTACT** | Green >= 0.90, Yellow [0.70, 0.90), Red < 0.70. All zone definitions, justifications, and cross-references (Sections 2.2a, 2.3, 4, 8, 10, 14.2, 15.2) unchanged from Round 2 approval. No drift. |
| **M1**: v2 as primary quantitative comparator | **INTACT** | Section 1 comparison table: v2 is first row ("Effect-size estimation for mu_G. Both conditions have complete data."). d-smoothing-minimal is mechanistic/validity predecessor ("Binary question"). No drift. |
| **M2**: `disable_lineage_on_improver` ordering invariant + unit test + `log_pattern_absent` | **INTACT** | Ordering invariant at Section 13.1 ("ORDERING INVARIANT" paragraph). Unit test `test_no_lineage_on_improver_skips_filter_resolution` with three assertions. Section 11.5 `log_pattern_absent` includes `"lineage_filter.aggregator required"` with severity ABORT. Section 11.1 positive activation log line at MUST. No drift. |
| **Round 3**: Cache/pass semantics | **SUPERSEDED BY ROUND 4** | Round 3 described `refresh_passes=2` as "dead config retained for IV control parity." Round 4 replaces that framing: `refresh_passes=1` is now the active setting, justified by the stage-level trace. The Round 3 factual corrections (cache semantics, v1 reasoning, evaluator independence from LineageStage) remain intact and are incorporated into the Round 4 rewrite of Section 3.1. |

All prior-round resolutions remain correctly addressed. The Round 4 revisions did not disturb C1, M1, or M2.

---

### 2. Per-Stage Cache-Mode Trace Verification

The Round 4 revision adds a per-stage cache-mode table to Section 3.1 and references it from Sections 5a, 9, and 9.1. I have verified each stage's cache mode against the source code.

| Stage | Design claim | Code verification | Verdict |
|---|---|---|---|
| `FetchOpponentIdsStage` | `NO_CACHE` | `stages.py:56`: `cache_handler = NO_CACHE` | **CORRECT** |
| `FetchOpponentResultsStage` | `InputHashCache` (when `archive_reeval=true`) | `stages.py:156-159`: `return DEFAULT_CACHE if self._archive_reeval else NO_CACHE`. `DEFAULT_CACHE` = `InputHashCache` per `cache_handler.py`. | **CORRECT** |
| `CallValidatorFunction` | `InputHashCache` | `execution.py:254`: class inherits from `PythonCodeExecutor(Stage)`, no `cache_handler` override; default is `DEFAULT_CACHE` = `InputHashCache` per `base.py:112`. | **CORRECT** |
| `InsightsStage` | `InputHashCache` + `cache_on=FetchOpponentIdsStage` | `insights.py:38`: `InputsModel = CacheOnlyInput`. No `cache_handler` override; inherits `DEFAULT_CACHE` from `Stage` via `LangGraphStage`. `asymmetric_pipeline.py:309-311`: `add_data_flow_edge("FetchOpponentIdsStage", "InsightsStage", "cache_on")`. | **CORRECT** |
| `DGTrackerStage` | `NO_CACHE` | `dg_tracker_stage.py:64`: `cache_handler = NO_CACHE` | **CORRECT** |
| `MutationContextStage` | `NO_CACHE` | `mutation_context.py:67`: `cache_handler = NO_CACHE` | **CORRECT** |

The `grep -rn "refresh_pass" gigaevo/` claim is verified: only `gigaevo/adversarial/shared_benchmark_lineage.py:98` reads `EngineSnapshot.refresh_pass` in a stage's `compute_hash`. The engine config definition (`config.py:76`) and engine code (`steady_state.py:819-831`) reference it for bookkeeping, and `snapshot.py:32` defines the field, but no other *stage* reads the counter. The claim that "only `SharedBenchmarkFilteredLineageStage.compute_hash` reads the counter" is correct when scoped to stage-level cache invalidation.

All six cache-mode claims are verified. The trace is factually correct.

---

### 3. Cross-Section Consistency Check

| Section | Claim about `refresh_passes` | Consistent? |
|---|---|---|
| 3.1 (anchor, rewritten) | `refresh_passes=1` (changed from v2's `2`). Pass-2 consumer removed by IV 2. Per-stage table shows pass 2 is a no-op. Load-bearing path is pass-1 opponent-ID-keyed cache cascade. | Anchor |
| 5a (row updated) | `refresh_passes` on D: `1` (CHANGED from v2's `2`). "Only `SharedBenchmarkFilteredLineageStage` reads that counter (verified via grep across `gigaevo/`)." Load-bearing freshness path is `archive_reeval=true` evaluator cache + `InsightsStage` `cache_on` in pass 1. | **Consistent** |
| 6.1 (D extra_overrides) | `engine_config.refresh_passes=1` with inline comment: "CHANGED from v2 (was 2): pass-2 consumer (SharedBenchmarkFilteredLineageStage) removed by disable_lineage_on_improver -> pass-2 becomes O(archive_size) no-op of meaningful work" | **Consistent** |
| 9, Confound 5 | Now reads "NONE -- mitigation pre-applied." `refresh_passes` set to `1`. "Only `SharedBenchmarkFilteredLineageStage` reads the `refresh_pass` counter, and that stage is removed by IV 2. Pass 2 had no LLM consumer to invalidate, so dropping it has zero behavioural impact." | **Consistent** |
| 9, Confound 7 | "`refresh_passes` reduced from v2's `2` to `1` (its sole consumer `SharedBenchmarkFilteredLineageStage` is removed by IV 2, verified by grep)." | **Consistent** |
| 9.1 Preempt #2 | Full trace reproduced with code citations. "Pass 2's behavioural delta is zero; its bookkeeping cost is O(archive_size) per epoch." | **Consistent** |
| 11.3 | Hydra `--cfg job` expectation for D runs: `refresh_passes` expects `1`. | **Consistent** |

No contradictions across the seven modified locations. Internal consistency is maintained.

---

### 4. Critical Assessment: "Pass 2 Has Zero Behavioural Change"

This is the central claim justifying the `refresh_passes 2 -> 1` change. The design's argument is: with `SharedBenchmarkFilteredLineageStage` removed, pass 2's `refresh_pass` counter bump has no consumer; `FetchOpponentIdsStage` (NO_CACHE, `top_k`, deterministic) produces the same IDs as pass 1; all `InputHashCache` stages cache-hit; only `DGTrackerStage` (idempotent ZADD GT) and `MutationContextStage` (deterministic re-format) actually run; therefore pass 2 is a strict no-op with O(archive_size) bookkeeping overhead.

I have probed this claim for edge cases.

#### 4.1 `FetchOpponentIdsStage` Determinism Under Cache TTL Expiry

**Finding**: The `top_k` sampling path in `OpponentArchiveProvider.get_top_k()` (and `CellStratifiedOpponentProvider.get_top_k()`) uses a 30-second cache TTL (`opponent_provider.py:157,379`). The method checks `(now - self._cache_time) > self._cache_ttl` before every call. If more than 30 seconds elapse between a D archive program's pass-1 evaluation and its pass-2 evaluation, the opponent cache refreshes from Redis.

Between pass 1 and pass 2, the engine calls `_await_idle()` (`steady_state.py:834-838`) to drain the DAG-runner queue from pass 1. Pass 1 processes 170-190 D archive programs, some of which may trigger LLM calls on `InsightsStage` (cache-miss from a G HoF flip). The elapsed time between the first pass-1 `get_top_k` call and the first pass-2 `get_top_k` call could easily exceed 30 seconds on epochs where G's HoF flips.

If G produces a new top-1 program and writes it to its archive between pass-1's cache fetch and pass-2's cache fetch, `get_top_k` returns a different opponent ID on pass 2. This would cascade: `FetchOpponentResultsStage` cache-miss, `CallValidatorFunction` cache-miss (D improver re-executes against the new G program), `InsightsStage` cache-miss (LLM call), `DGTrackerStage` records a new pair. Pass 2 would do *real work*.

**Assessment of likelihood**: This requires G to publish a new top-1 program during D's intra-epoch pass-1-to-pass-2 window. With G generating approximately 1 program per 33 minutes and the refresh window spanning perhaps 2-10 minutes (depending on how many programs cache-miss on pass 1), the probability of a G HoF flip during any given D epoch's refresh window is roughly 6-30%. Over a 50-epoch D run, this would happen 3-15 times.

**Assessment of impact**: When it does happen, pass 2 catches the G update one epoch sooner than pass 1 of the next epoch would. This is a timing benefit (D responds to G's new top-1 one epoch sooner), not a correctness issue. Removing pass 2 via `refresh_passes=1` means D waits until the next epoch's pass 1 to discover the G update. This is a minor latency cost, not a behavioural change in the fitness landscape.

**Severity: Minor.** The "zero behavioural change" claim is slightly too strong. The precise claim is: "pass 2 produces identical outputs to pass 1 *when the opponent cache does not expire between passes*." When the cache does expire and G has updated, pass 2 does useful work. However, the useful work is merely a timing optimisation (earlier discovery of G updates), not a fundamentally different evaluation path. The same evaluation would happen on the next epoch's pass 1. Dropping pass 2 delays D's response to G HoF flips by at most one D epoch.

This is not a confound. It does not differentially affect treatment vs control (v2 also had a timing benefit from pass 2, but via a different mechanism -- LineageStage re-run). The timing advantage lost by dropping pass 2 is uniform across all 4 D runs and does not co-vary with the IV.

#### 4.2 `DGTrackerStage` Idempotency Under Same Inputs

Verified. `DGTrackerStage` uses `ZADD GT` (score-conditional update). When pass 2 produces the same inputs as pass 1 (same opponent IDs, same validation results), the ZADD GT writes are no-ops because the scores are identical. The "idempotent" claim holds under same-input conditions.

Under the cache-TTL edge case (4.1), pass 2 would receive different inputs and record new (d_id, g_id) pairs. This is correct behaviour -- recording a real new evaluation against a genuinely new opponent. The ZADD GT deduplication handles the same-pair-same-score case.

#### 4.3 `MutationContextStage` Determinism Under Same Inputs

Verified. `MutationContextStage` is `NO_CACHE` and deterministic given the same upstream inputs. Under same-input conditions, pass 2 produces identical mutation context. Under the cache-TTL edge case, it would produce different context (reflecting the new opponent data), which is correct.

#### 4.4 Could a New Opponent ID Arrive Between Pass 1 and Pass 2?

Yes. The `_await_idle()` call between passes ensures D's own DAG runner queue is drained, but it does NOT prevent G from producing new programs. G runs as an independent process writing to its own Redis DB. D's `OpponentArchiveProvider` reads from G's Redis. There is no lock or coordination between D's refresh passes and G's writes.

However, even if a new G program arrives, it only matters if it becomes the NEW top-1 by fitness. With `n_opponents=1` and `top_k` sorting by `(-fitness, program_id)` with deterministic tiebreak (`opponent_provider.py:249-256`), the IDs change only when the new program's fitness exceeds the current top-1's. Ties are broken by `program_id` (lexicographic), which is deterministic.

#### 4.5 Is `refresh_passes=1` a 3rd IV or a Derived Consequence?

The design's argument is sound. `refresh_passes=2` was designed to invalidate `SharedBenchmarkFilteredLineageStage` between passes (the engine's docstring at `steady_state.py:807-817` states this explicitly). With `SharedBenchmarkFilteredLineageStage` removed by IV 2, pass 2's primary consumer is gone. The residual cache-TTL edge case (4.1) is a timing optimisation that was a side effect of pass 2, not its design purpose.

`refresh_passes=1` is a derived consequence of IV 2, not an independent variable. The behavioural delta between `refresh_passes=2` and `refresh_passes=1` under no-lineage is bounded by the cache-TTL edge case: at most one-epoch-earlier detection of G HoF flips, on a fraction of epochs. This is not a fitness-landscape difference. I accept the design's framing.

---

### 5. New Confounds, Hidden Assumptions, or Unmeasured DVs

#### 5.1 The Cache-TTL Timing Effect

As analyzed in 4.1, dropping pass 2 introduces a minor timing asymmetry vs v2: v2's D detected G HoF flips via pass-2 LineageStage re-run; this experiment's D detects them only on the next epoch's pass-1 evaluator cache-miss. However, this is a *consequence of the treatment* (removing LineageStage changes D's refresh dynamics) and is symmetric across all 4 D runs. It is not a confound. The existing D/G gen-pace ratio and D fitness trajectory DVs already capture any timing effects.

#### 5.2 Reduced LLM Call Budget on D

The design correctly notes in Section 16 that estimated LLM calls drop from v2's ~32k to ~20-25k because D skips lineage LLM calls. This is a direct consequence of IV 2, not an unmeasured effect.

No new confounds, hidden IVs, or unmeasured consequences were introduced by the Round 4 change.

---

### 6. Falsification Check for the Pass-2 No-Op Claim

The question was raised whether a runtime falsification check should be added: "if D pass-2 fires more than ~K cheap operations per epoch, the no-op claim is wrong."

**Assessment**: `refresh_passes` is being set to `1`. Pass 2 does not execute at all. There is no pass 2 to monitor. The falsification check is structurally unnecessary -- there is nothing to observe because the code path is never entered.

The relevant verification is already covered:
- Section 11.3: Hydra `--cfg job` must show `refresh_passes: 1` on D runs (confirms pass 2 does not execute)
- Section 11.1: D logs must NOT contain `[LineageStage:SharedBenchmark]` (confirms the pass-2 consumer is absent from the DAG)

If the researcher wished to independently verify the trace's accuracy against runtime behavior, this could be done during the smoke test by temporarily running with `refresh_passes=2` and comparing per-pass LLM call counts. But this is a code-verification exercise, not an experiment-level falsification. The trace has been performed against the source code and independently verified in this review. No additional runtime check is required.

---

### 7. Summary Assessment

The Round 4 revision is a clean, well-justified optimisation. The per-stage cache-mode trace is factually correct against the source code (all six stages verified). The `refresh_passes 2 -> 1` change is a valid derived consequence of IV 2 (LineageStage removal), not a 3rd IV. The cross-section consistency is maintained across all seven modified locations. No prior-round resolutions were disturbed.

The one imprecision I identified -- the opponent cache TTL expiry edge case where pass 2 could detect G HoF flips one epoch sooner -- does not rise to the level of invalidating the design decision. It is a minor timing effect, uniform across all D runs, that does not co-vary with the treatment. The design should acknowledge the edge case in one sentence but is not blocked by it.

---

### Round 4 Concerns

| # | Concern | Severity | Recommendation |
|---|---|---|---|
| m1 | "Zero behavioural change" claim slightly overstates: `OpponentArchiveProvider` cache TTL (30s) can expire between pass 1 and pass 2 during `_await_idle()`. If G publishes a new top-1 during that window, pass 2 would cascade to real LLM work via `InsightsStage`. The timing benefit is minor and uniform across all D runs, but the claim should note the edge case. | **Minor** | Add one sentence to Section 3.1 noting the cache-TTL edge case and that `refresh_passes=1` delays G HoF detection by at most one D epoch vs `refresh_passes=2`. Does not block approval. |

---

### Verdict

**[x] APPROVED**

The Round 4 per-stage cache-mode trace is code-verified and factually correct. The `refresh_passes 2 -> 1` change is a well-justified derived consequence of IV 2, not an independent variable. All prior-round resolutions (C1 graded gate, M1 v2-as-primary-comparator, M2 ordering invariant + unit test) remain intact. The single minor concern (m1: cache-TTL edge case in the "zero behavioural change" claim) is a presentation precision issue that does not affect experimental validity. The design is ready for pre-registration and implementation.

*The science demands nothing less.*
