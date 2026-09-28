# Reviewer #2 Adversarial Review -- Re-review after Revision 1

**Verdict**: APPROVED
**Reviewer**: Volkov (reviewer-2-adversary, automated)
**Date**: 2026-04-19
**Prior verdict**: NEEDS REVISION -- MAJOR (same date, Revision 0)

## Summary

All concerns from the initial review have been resolved. The design is clean, internally consistent, and ready for pre-registration.

## Concern Resolution

### M1 (MAJOR): FitnessPlateauStopper is dead code -- RESOLVED

The stopper is now `stopper=max_generations` with `max_generations=50` throughout the document. All references to `FitnessPlateauStopper`, `max_generations_or_fitness_plateau`, and the Section 16.4 paragraph about plateau-stopper interaction with hard-floor fitness have been removed. Section 10 (Stop Criteria), Section 5 (Controlled Variables), Section 12.3 (Extra overrides), and Section 12.4 (Pinned contract) are all consistent.

The researcher chose to drop the wallclock cap entirely rather than formalize it. This is acceptable: with `max_generations=50` and the expected ~10h per run, the experiment will terminate naturally. The gen-12 vs gen-50 diagnostic split requires runs to reach gen 50, so no early termination mechanism is needed.

Two remaining uses of "plateau" in the document (lines 332, 393) describe possible fitness trajectories, not the stopper mechanism. These are appropriate.

### m1 (Minor): N=8 G-run count inflated -- RESOLVED

All primary analysis references now correctly specify 4 G runs (A1_G, A2_G, C1_G, C2_G). Section 2 (H1), Section 2 (effect-size thresholds, failure criteria), Section 7 (sample size justification), and Section 13.1 (primary analysis) are internally consistent. The one remaining "N=8" reference (line 130) correctly contrasts the current N=4 design against a hypothetical N=8 design for power context -- this is appropriate.

### m2 (Minor): Wallclock cap enforcement unspecified -- RESOLVED

Wallclock cap dropped per researcher decision. No orphan references to "wall-clock," "30 hours," "30h," "108000," or `WallClockStopper` remain anywhere in the document.

### m3 (Minor): Missing Arm B explanation -- RESOLVED

Line 120: "Arm labels A and C are retained from v1 for exact structural replication. No Arm B exists in this design."

### m4 (Minor): Non-existent run references -- RESOLVED

Section 13.1 now lists the correct 4 G runs directly (A1_G, A2_G, C1_G, C2_G). No drafting artifacts or self-corrections remain.

### m5 (Minor): archive_reeval rationale reordered -- RESOLVED

Line 95: "Match v1 (which used false). Independently confirmed NEGATIVE in adversarial-dynamic-updates."

### m6 (Minor): evolution=steady_state provenance -- RESOLVED

Line 76: "Matches v1's actual operating mode (KF-01 amendment from generational to steady-state)."

## New Issues Introduced by Revision

None identified. The revision was surgical -- it addressed each concern without introducing inconsistencies or orphan references.

## Pre-registration readiness checklist

- [x] N >= 2 per cell -- 4 G runs pooled (2 per arm), exceeds minimum.
- [x] Single IV per comparison -- N/A for reproducibility study (no within-experiment IV). Justified.
- [x] Treatment verification section present and non-empty -- Section 12, exemplary.
- [x] Stopping rule specific and accurate -- `stopper=max_generations` with `max_generations=50`. Matches actual engine behavior.
- [x] Results analysis plan pre-registered -- Section 13, thorough. Gen-12/gen-50 diagnostic split is well-designed.
- [x] Novelty assessment addressed -- Section 15.5 and 15.6 honestly acknowledge limited novelty and off-spine positioning.
- [x] Confound enumeration complete -- Section 9, seven confounds with calibrated risk ratings and mitigations.
- [x] All run-level overrides specified -- Section 12.3, exact strings for `python run.py`.

## Information Gain Assessment

(Unchanged from initial review.) The experiment is worth running at its stated cost (~24h, 8 Redis DBs). It is a calibration hedge, not the main research line. A positive result strengthens the loose-coupling narrative; a negative result localizes the failure via the gen-12 diagnostic. Expected information gain is conditional on the REDESIGN bundle outcome, but the cost is low enough to justify parallel execution.

---

**Verdict: APPROVED.**

The design is internally consistent, the stopping rule accurately describes actual engine behavior, the treatment verification protocol remains exemplary, and all editorial concerns have been resolved. Proceed to pre-registration.

*The science demands nothing less.*
