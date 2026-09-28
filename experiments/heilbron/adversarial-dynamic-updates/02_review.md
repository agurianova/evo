# Reviewer-2 Assessment: heilbron/adversarial-dynamic-updates

**Date**: 2026-04-09
**Reviewer**: Dr. Volkov (reviewer-2-adversary agent)
**Verdict**: NEEDS REVISION (1 Critical, 3 Major, 4 Minor concerns)

## Summary

The design is well-motivated, addresses the highest-priority open question from PATTERNS.md, and isolates the IV correctly (re-evaluation ON/OFF with K=0, no compound treatment). The concurrent control arm is a significant improvement over adversarial-v2's historical-only baseline. The compute budget analysis is sound --- re-evaluation overhead is genuinely negligible for the Heilbronn task. The treatment verification plan is thorough, with both positive (treatment shows activity) and negative (control shows no activity) checks, plus runtime gates at gen 5 and gen 10.

However, I identify one critical concern (throughput confound from the sync hook interaction), three major concerns (metrics history corruption, archive diversity collapse without a termination trigger, and the `ArchiveReEvaluationHook` being entirely unimplemented), and four minor concerns detailed below. The critical concern requires a design amendment; the major concerns require clarification or additional safeguards. None are fatal to the research question.

---

## Concerns

### Critical

**C1. Throughput confound: re-evaluation blocks the mutation gate via the sync hook, creating a systematic timing asymmetry between treatment and control.**

The design claims re-evaluation adds "<5% compute overhead" and runs "at epoch boundary (a natural pause)." This analysis accounts only for the CPU cost of re-evaluating geometry. It misses the interaction with `ProgressBasedSyncHook`.

Here is the sequence in `steady_state.py._epoch_refresh()`:

1. Step 3a: Save `programs_processed` to Redis.
2. Step 4: Call `_pre_step_hook()` --- this is the `ProgressBasedSyncHook`, which blocks until the opponent advances by `min_delta` programs.
3. Steps 5-6: Refresh archive (re-run DAG on archived programs).
4. Step 7: Reopen mutation gate.

The proposed `ArchiveReEvaluationHook` runs "at each epoch boundary." If it runs within step 6 (during archive refresh) or as an additional step between steps 4 and 7, the mutation gate remains closed for the duration of the re-evaluation. This means the mutation loop is blocked not for the ~75s re-evaluation time alone, but for the ~75s *plus* whatever time the sync hook adds waiting for the opponent.

Worse, the re-evaluation itself produces no `programs_processed` counter increments (re-evaluated programs are not new programs). So from the opponent's perspective, this population has stalled. If both populations trigger re-evaluation simultaneously (which is likely, since opponent archive changes are the trigger), both sync hooks block, each waiting for the other to advance `min_delta` --- a potential deadlock or at minimum a prolonged mutual wait that resolves only via the sync hook timeout (7200s).

Even if deadlock is avoided, the systematic pattern is: treatment pairs spend more wall-clock time blocked at epoch boundaries than control pairs, because they do re-evaluation work during the gated window. Over 75 epochs, treatment pairs will produce fewer total mutations per wall-clock hour. If treatment shows lower fitness, the confound is: was re-evaluation harmful, or did treatment simply get fewer mutations? If treatment shows higher fitness despite fewer mutations, the result is actually stronger --- but the throughput asymmetry must be measured and reported.

**Required amendment**: (a) Specify exactly where in the epoch lifecycle the re-evaluation hook executes. (b) Confirm that re-evaluation does NOT block while the mutation gate is closed, or quantify the expected gate-closure extension. (c) Add a DV: `mutations_per_wall_hour` for treatment vs control, reported alongside fitness. (d) Address the potential sync-hook deadlock when both populations re-evaluate simultaneously. One mitigation: re-evaluation should NOT increment or interact with `programs_processed`, and the sync hook should fire BEFORE re-evaluation, not after.

---

### Major

**M1. Metrics history corruption during re-evaluation: the design says re-evaluation "should NOT rewrite `metrics:history`" but the existing `MetricsTracker._refresh_changed_fitness()` DOES rewrite frontier history when it detects changed metrics.**

The design document states (Section 14, point 3): "Re-evaluated fitness should update `metrics:latest` but NOT rewrite `metrics:history` (to preserve temporal record)."

However, the codebase already has a mechanism for exactly this situation. `MetricsTracker._refresh_changed_fitness()` (metrics_tracker.py lines 183-222) detects when a program's metrics hash changes, updates `_valid_programs`, and then calls `_recompute_and_write_frontier(key)` for every changed metric. This function uses `clear_series()` to DELETE the existing frontier history and rewrites it from scratch using the current program data.

When re-evaluation changes archived programs' fitness values, the MetricsTracker will detect these changes in its next poll cycle and trigger a full frontier rewrite. This means:

- `valid_frontier_*` history in Redis will be cleared and rewritten with every re-evaluation event.
- The temporal record of when frontier improvements occurred will be destroyed.
- `tools/comparison.py` and `tools/trajectory.py` will show a frontier that appears to jump backward or forward at re-evaluation boundaries.
- The distinction between "genuine new program improved fitness" and "re-evaluation corrected stale fitness" will be lost in the history.

This is not just a data-quality issue. It affects H1: if the frontier history is rewritten, the gen-75 frontier value reflects the last re-evaluation snapshot, not the historical trajectory. This may be exactly what you want (current-truth fitness), but the design must be explicit about this.

**Required action**: Either (a) confirm that frontier rewriting is the desired behavior and adjust the analysis plan to use final-snapshot fitness rather than trajectory-based fitness, OR (b) implement a separate metrics namespace for re-evaluated fitness (e.g., `reeval_frontier_*`) and gate `_refresh_changed_fitness` from rewriting the primary frontier during re-evaluation passes.

**M2. Archive diversity collapse has no termination or amendment trigger.**

Section 14 (risk 5) correctly identifies that re-evaluation may reduce archive diversity: "only currently-relevant programs survive." If all 30 archived programs collapse to 2-3 distinct strategies after re-evaluation, the population loses diversity for parent selection, and subsequent mutations become redundant copies.

The design defines no threshold for "archive diversity has collapsed to a dangerous level." Compare this to the pre-registered amendment for re-evaluation cost (Section 7: "If re-evaluation takes >120s per trigger..."). The diversity risk is higher-impact than the compute risk but has no analogous amendment.

**Required action**: Add a monitoring metric and amendment trigger. For example: track `unique_archive_programs` (count of distinct occupied cells after re-evaluation). If the archive shrinks below 3 occupied cells for 5 consecutive epochs, pause re-evaluation and log as protocol deviation. This distinguishes "re-evaluation correctly pruning stale programs" (healthy, archive stays >10) from "re-evaluation causing mode collapse" (pathological, archive collapses to 1-3).

**M3. `ArchiveReEvaluationHook` does not exist in the codebase --- the treatment mechanism is entirely unimplemented.**

The design references `ArchiveReEvaluationHook` with pseudocode (Section 3), config overrides (`archive_reeval=true`), log patterns (`[ArchiveReEval] triggered`), and Redis keys (`{prefix}:reeval_count`). None of this exists in the codebase. The only match for "ArchiveReEval" or "archive_reeval" in the entire repository is in this design document itself.

This is not inherently a problem --- the implementation phase (Phase 4) will build it. But the design makes specific claims about the mechanism's behavior that are not yet validated against the actual engine lifecycle. The pseudocode shows a simple synchronous loop (`for program in archive: evaluate(program)`), but the real epoch lifecycle in `steady_state.py` has 10 ordered steps with locks, gates, drain sets, and carry-forward counters. Where exactly in this sequence does the hook fire? How does it interact with `_in_flight_lock`? Does it use the same `DagRunner` instance (which may have concurrency limits)?

**Required action**: Before launch, require a unit test demonstrating that the hook fires at the correct lifecycle point, that re-evaluated programs' fitness values actually change in the archive, and that the sync hook does not deadlock when both populations re-evaluate. This should be a Phase 4 gate, not left to ad-hoc validation.

---

### Minor

**m1. Effect size threshold (0.002) is within the noise floor of prior experiments.**

The pre-registered POSITIVE threshold of 0.002 on `actual_fitness` is comparable to the within-pair variance from heilbron-prover (0.00168). With N=2 per condition, the standard error of the treatment-control difference is approximately `sqrt(2) * 0.00168 / sqrt(2) = 0.00168`. A 0.002 difference against a noise floor of 0.00168 yields approximately t = 1.19, which is not significant at any conventional alpha.

The design acknowledges this (Section 8: "N=2 is underpowered for small effects") and proposes supplementary rank comparison (all 4 pairwise comparisons favoring treatment). This is reasonable for a direction-of-effect conclusion. However, the "Cohen's d and 95% CI from the 4 data points" claim (Section 9) is misleading --- a CI from 4 data points with this noise level will be extremely wide and uninformative.

**Suggestion**: Drop the t-test and CI language from the statistical test section. The honest analysis at N=2 is: (a) direction of effect (rank ordering), (b) magnitude of effect (point estimate of treatment - control mean), (c) comparison to prior within-pair variance. Dressing it up in hypothesis-testing language adds no information and may create false confidence.

**m2. The `actual_fitness` DV at gen 75 conflates two effects: better programs via improved parent selection AND more evaluations due to re-evaluation overhead.**

Treatment programs are re-evaluated multiple times. Each re-evaluation is a fresh geometry computation. If re-evaluation occasionally produces slightly different results due to floating-point non-determinism or tie-breaking, treatment programs effectively get multiple chances to register their best score. The design does not specify whether the Heilbronn evaluation is fully deterministic for a given (program, opponent set) pair.

**Suggestion**: Confirm that the Heilbronn evaluation function is deterministic given identical inputs (program code + opponent code). If it is, this concern is moot. If it is not (e.g., random tie-breaking, numerical instability), document the expected noise level.

**m3. Control contamination check (Section 13) only looks for log patterns, not Redis keys.**

The treatment verification checks for `[ArchiveReEval] triggered` log pattern absence in control runs (good), and for `archive_reeval == false` config in control runs (good). But the Redis key `{prefix}:reeval_count` has no corresponding absence check for control runs. If a config wiring bug causes the hook to fire in control runs despite `archive_reeval=false`, the Redis key would reveal it even if the log pattern check fails (e.g., log level misconfigured).

**Suggestion**: Add a control purity check for Redis: `{prefix}:reeval_count` must be absent or zero in all control runs at every checkpoint.

**m4. "No experiment-level early stop" may waste compute if treatment is clearly harmful.**

The design states "both arms run to gen 75" with no experiment-level stopping rule. If by gen 30, both treatment Constructors show fitness 50% lower than both control Constructors (i.e., re-evaluation is clearly destabilizing), the remaining 45 generations provide no additional information while consuming ~15 hours of compute.

**Suggestion**: Add a futility rule: if at gen 30, both treatment Constructor `actual_fitness` values are below both control Constructor values by >= 0.005, the experiment may be stopped early with a NEGATIVE verdict. This preserves resources for the follow-up experiment while still allowing recovery (30 generations is sufficient to observe the mechanism's steady-state effect).

---

## Hypothesis and Falsifiability

- [x] H0 clearly stated (NULL criterion: |delta| < 0.002)
- [x] H1 falsifiable and directional (treatment > control by >= 0.002)
- [x] Primary metric pre-specified (Constructor `actual_fitness` at gen 75)
- [x] Success criteria numeric and unambiguous

**Notes**: H2 and H3 are well-defined secondary hypotheses. The success/null/negative trichotomy for H1 is clear.

## Confound Analysis

- [x] Controlled variables genuinely controlled (K=0, same pipeline, same LLM, same seeds)
- [x] IV isolated (single IV: re-evaluation ON/OFF)
- [ ] Known confounds mitigated or acknowledged (see C1 --- throughput confound not addressed)
- [x] Val/test split not contaminated (Heilbronn uses deterministic geometry, no held-out set)

**Unaddressed confounds**: Throughput asymmetry (C1), metrics history rewriting (M1).

## Statistical Validity

- [x] Sample size justified (N=2 acknowledged as underpowered; rank comparison supplement)
- [ ] Statistical test appropriate (see m1 --- t-test at N=2 is inappropriate)
- [x] Significance threshold pre-specified (0.002 absolute)
- [x] Multiple comparison correction not needed (single primary DV)

**Notes**: The rank-ordering approach (all 4 pairwise comparisons) is the appropriate analysis for N=2. Drop the t-test framing.

## Evaluation Protocol

- [x] Metric computed identically across conditions (same Heilbronn geometry)
- [x] Val/test sets fixed (deterministic Heilbronn --- no held-out set distinction)
- [x] No post-hoc metric selection (primary DV pre-specified)
- [x] Thinking mode consistent (same mutation LLM, same config)

**Notes**: Evaluation protocol is clean. The Heilbronn problem has no chain LLM or test set, eliminating several common confounds.

## Required Changes Before Approval

1. **[Critical]** Address C1: specify re-evaluation hook placement in epoch lifecycle, confirm no sync-hook deadlock, add `mutations_per_wall_hour` as a DV.
2. **[Major]** Address M1: decide whether frontier rewriting by MetricsTracker is desired behavior, and adjust analysis plan or implementation accordingly.
3. **[Major]** Address M2: add archive diversity monitoring metric and amendment trigger for mode collapse.
4. **[Major]** Address M3: add Phase 4 gate requiring unit tests for hook lifecycle integration and sync-hook non-deadlock.

---

## Verdict

**[ ] APPROVED**

**[x] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**: This is the right experiment. The research question, IV isolation, concurrent control, and treatment verification are all well-designed. The concerns are about the mechanism's integration with the existing engine --- specifically, how re-evaluation interacts with the sync hook timing, the metrics tracking pipeline, and archive diversity. These are engineering concerns that can be resolved with targeted amendments to the design and implementation plan. I expect approval after one revision round.

---

*Reviewed by Dr. Volkov, 2026-04-09.*

---

## Re-Review

**Date**: 2026-04-09
**Reviewer**: Dr. Volkov (reviewer-2-adversary agent)
**Verdict**: APPROVED (with one advisory note)

### Verification of Revisions

I verified each concern against the revised design text and the actual codebase (`steady_state.py`, `metrics_tracker.py`, `sync.py`, `evaluate.py`, `helper.py`).

**C1 (Critical): Throughput confound from sync hook interaction --- RESOLVED.**

The revised design specifies the hook placement at step 6b, between archive refresh (step 6) and mutation gate reopen (step 7). I verified the actual `_epoch_refresh()` method in `steady_state.py` (lines 517-645): the sync hook fires at step 4 (`_pre_step_hook()`), and `programs_processed` is published to Redis at step 3a, strictly before both the sync hook and the proposed re-evaluation point. The design correctly identifies that:

1. Re-evaluation fires after the sync hook has already resolved, eliminating the deadlock scenario.
2. Re-evaluation does not write to `programs_processed`, so the opponent's sync hook is never stalled by re-evaluation activity.
3. The mutation gate is already closed during steps 3-7; re-evaluation at step 6b extends this existing closed window by ~25-75s rather than introducing a new gate closure.

The addition of `mutations_per_wall_hour` as a DV (Section 4) quantifies the throughput asymmetry. The analysis plan (Section 9) explicitly includes a throughput check. Satisfactory.

**M1 (Major): Metrics history corruption --- RESOLVED.**

The revised design introduces a separate `reeval_*` namespace and specifies that `_refresh_changed_fitness()` will be gated by a flag on the program object to prevent primary frontier rewriting during re-evaluation passes (Section 3, "Metrics isolation"). I verified that `_refresh_changed_fitness()` in `metrics_tracker.py` (line 183) does currently detect metric changes via hash comparison and triggers `_recompute_and_write_frontier()` which calls `clear_series()` --- confirming the corruption risk was real. The design's mitigation (gating flag) requires implementation, but the mechanism is clearly specified and the Phase 4 gate (see M3 below) covers it. The primary DV is explicitly defined as reading from archive state (live Redis query), not from frontier history. Satisfactory.

**M2 (Major): Archive diversity collapse without amendment trigger --- RESOLVED.**

The revised design adds `archive_occupied_cells` as a tracked metric (Section 4) and a pre-authorized amendment (Section 7): if any run's archive shrinks below 3 occupied cells for 5 consecutive epochs, the re-evaluation hook is paused for that run, with the event logged as a protocol deviation. The threshold (3 cells, 5 epochs) distinguishes healthy pruning from pathological collapse. This is a reasonable safeguard. Satisfactory.

**M3 (Major): Hook unimplemented, no Phase 4 gate --- RESOLVED.**

The revised design adds four required tests as a Phase 4 implementation gate (Section 3, end of "Treatment mechanism" subsection):

1. Unit test: hook fires at step 6b, after sync hook, before mutation gate reopens
2. Unit test: re-evaluated programs have updated fitness in the archive
3. Unit test: sync hook does NOT deadlock when both populations re-evaluate simultaneously
4. Integration test: end-to-end with 2 populations, verifying fitness changes propagate

These are the right tests. The hook remains unimplemented (which is expected at design phase), but the gate ensures it cannot launch without validated integration. Satisfactory.

**m1 (Minor): Drop t-test for rank ordering --- RESOLVED.**

Section 9 now uses rank ordering as the primary analysis (all 4 pairwise comparisons). The t-test and misleading CI language have been removed. The analysis reports direction, magnitude, and comparison to prior within-pair variance. Satisfactory.

**m2 (Minor): Evaluation determinism unconfirmed --- RESOLVED.**

Section 14 now explicitly confirms determinism. I verified the evaluation code: `evaluate.py` calls `get_smallest_triangle_area()` which uses `np.abs()` on cross-product areas and `np.min()` --- all deterministic numpy operations. `is_inside_triangle()` uses barycentric coordinates via `np.einsum` --- also deterministic. No random seeds, no tie-breaking, no stochastic elements. The claim is correct: fitness changes on re-evaluation arise solely from different opponents being fetched. Satisfactory.

**m3 (Minor): Redis key absence check for control purity --- RESOLVED.**

Section 13 (preflight treatment checks) now includes a `redis_key_absent` check for `{prefix}:reeval_count` in all control runs (C1_A, C1_B, C2_A, C2_B), gated at gen 10. This complements the existing log-pattern-absent check. Satisfactory.

**m4 (Minor): No futility stopping rule --- RESOLVED.**

Section 11 now includes an experiment-level futility stop: if at gen 30, both treatment Constructor `actual_fitness` values are below both control values by >= 0.005, the experiment may be stopped early with a NEGATIVE verdict. The threshold (0.005) is well above the noise floor (0.00168 within-pair variance) and the generation gate (30) provides sufficient data. Satisfactory.

### Advisory Note (non-blocking)

**A1. MetricsTracker gating flag requires careful implementation.**

The design specifies that `_refresh_changed_fitness()` will be gated by a flag on the program object to prevent primary frontier rewriting. This is the correct approach, but the implementation must handle a subtle edge case: the MetricsTracker polls asynchronously (`_drain_once` runs on an interval). If a re-evaluation updates a program's metrics in Redis, and the MetricsTracker polls before the gating flag is set on the program object, the frontier will be rewritten despite the design's intent. The Phase 4 implementation should ensure that the gating flag is set atomically with the metric update, or that the MetricsTracker poll is suppressed during re-evaluation. This is covered by the Phase 4 gate tests (M3) but I flag it here to ensure the implementer is aware of the race condition.

### Checklist Update

- [x] Known confounds mitigated or acknowledged (C1 resolved: throughput DV added, deadlock eliminated)
- [x] Statistical test appropriate (m1 resolved: rank ordering primary, t-test dropped)

### Verdict

All 1 Critical, 3 Major, and 4 Minor concerns from the initial review have been substantively addressed. The design correctly identifies where the re-evaluation hook fires in the actual epoch lifecycle (verified against `steady_state.py`), isolates re-evaluation metrics from the primary frontier namespace, adds diversity collapse safeguards, and gates launch on implementation tests. The concurrent control design, single-IV isolation, and treatment verification plan remain strong.

**[x] APPROVED**

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**: The designer has done careful work mapping the hook placement to the actual engine lifecycle and identifying the metrics corruption risk. The advisory note (A1) is non-blocking but should be read by the implementer. This experiment is ready to proceed to Phase 3/4.

---

*Re-reviewed by Dr. Volkov, 2026-04-09.*
