# Phase 2: Adversarial Review -- hover/steady-state-validation

**Reviewer**: Prof. Andrei Volkov
**Date**: 2026-03-26
**Round**: 2 (revision review)
**Input**: `experiments/hover/steady-state-validation/01_design.md` (revised)

---

## Summary of Design

A non-inferiority validation comparing `SteadyStateEvolutionEngine` (continuous mutation/evaluation interleaving) against the generational `EvolutionEngine` on `chains/hover/full`. The IV is the engine type alone; all other parameters are held constant. N=2 per cell (Wave 1), with pre-committed extension to N=3 (Wave 2) when the expected inconclusive result materializes. Non-inferiority margin delta=3.0pp on validation fitness.

---

## Revision Assessment

All five concerns from Round 1 have been addressed. I evaluate each below.

### Concern 1 (Major): Ghost sweep asymmetry -- RESOLVED

Section 9 now includes "Mutation budget asymmetry" as an explicit confound with risk rated "Medium." The pre-committed diagnostic is specific and actionable: report `total_mutations_attempted` and `total_ghosts_swept` per run at closeout, with a >10% threshold for acknowledging the confound in results. This is exactly what was required. The confound is not eliminated -- it cannot be, as it is inherent to the engine semantics -- but it is now named, measured, and bounded.

### Concern 2 (Major): MDE computation and power framing -- RESOLVED

Section 7 now contains the explicit MDE computation using the t-distribution: df=2, t_0.05,2 = 2.92, SE = 1.5pp, CI half-width = 4.38pp > delta = 3.0pp. The misleading "~70% power" claim has been removed entirely. The experiment is reframed as "exploratory non-inferiority with pre-committed extension," with Wave 1 (N=2) honestly described as almost certainly inconclusive and Wave 2 (N=3) as the expected path. The extension threshold is pre-committed: trigger when the 90% CI of (control - treatment) includes both 0 and delta=3.0pp.

The note that SD=0.28pp (from dynamic-topology control) would yield a CI half-width of ~0.82pp -- well within the margin -- is appropriate context. The design no longer plans on the optimistic scenario; it plans on the conservative one and commits to extension.

### Concern 3 (Minor): Primary metric measurement point -- RESOLVED

Section 4 now reads: "Best validation fitness (soft fractional retrieval coverage) when `engine:total_generations` reaches 25 (epoch 25 for steady-state, generation 25 for generational)." Unambiguous.

### Concern 4 (Minor): Pre-launch DB flush -- RESOLVED

Section 13, item 1 explicitly commits to flushing all assigned Redis DBs (6, 7, 8, 9) via `tools/flush.py` before launch.

### Concern 5 (Minor): Throughput success criterion -- RESOLVED

Section 4 DV table now includes: "expected: steady-state 3-8x faster; <2x warrants investigation." This makes the throughput measurement interpretable rather than merely descriptive.

### Additional Change: Mechanistic feature reclassification

Ingestion timing within epoch and archive staleness have been reclassified from confounds to mechanistic features of the treatment. This is correct. These are inherent consequences of the steady-state architecture, not threats to internal validity. Calling them "confounds" would imply they should be controlled away, which would defeat the purpose of the experiment.

---

## Hypothesis and Falsifiability

- [x] H0 is clearly stated
- [x] H1 is falsifiable and directional
- [x] Primary metric is pre-specified and sufficient to test H1
- [x] Success criteria are numeric and unambiguous

**Notes**: The three-way decision rule (non-inferior / worse / inconclusive with extension) is now internally consistent with the power arithmetic. The extension threshold is pre-committed, not ad hoc. The success criterion (90% CI upper bound < 3.0pp) is honest about its achievability at each wave size.

---

## Confound Analysis

- [x] All controlled variables are genuinely controlled
- [x] IV is isolated (no other differences between conditions beyond engine semantics)
- [x] Known confounds are mitigated or acknowledged
- [x] Val/test split is not contaminated

**Notes**: The mutation budget asymmetry is now explicitly named with a pre-committed diagnostic and threshold. The IV isolation remains genuine -- `evolution=steady_state` inherits from `default` and changes only the engine class and config type, with no hidden overrides. The reclassification of ingestion timing and archive staleness as mechanistic features (not confounds) is appropriate and improves the clarity of the confound table.

---

## Statistical Validity

- [x] Sample size is justified -- pragmatically justified with honest power arithmetic and pre-committed extension
- [x] Statistical test is appropriate for the data
- [x] Significance threshold is pre-specified
- [x] Multiple comparison correction applied if needed -- single primary hypothesis, not needed

**Notes**: The MDE analysis is now correct. The experiment is designed as a two-wave plan where Wave 1 is expected to be inconclusive and Wave 2 is the decision point. This is a legitimate and well-established approach in clinical trials. The key improvement is that the design no longer overpromises what N=2 can deliver.

---

## Evaluation Protocol

- [x] Metric is computed identically across all conditions
- [x] Val/test sets fixed and identical for all runs
- [x] No post-hoc metric selection
- [x] Thinking mode is consistent across evaluations

**Notes**: Unchanged from Round 1. The evaluation protocol remains sound.

---

## Remaining Issues

None. All critical and major concerns are resolved. All minor concerns are resolved.

---

## Verdict

**[x] APPROVED**

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**:

All five concerns from Round 1 have been addressed with the specificity and honesty required. The two major revisions are substantive: the mutation budget diagnostic (Concern 1) transforms an unnamed confound into a measured and bounded one, and the MDE reframing (Concern 2) replaces misleading power arithmetic with an honest two-wave design that acknowledges the limits of N=2. The three minor revisions are precise and complete.

This design is ready for implementation. It exemplifies what engineering validation should look like: a single cleanly isolated IV, pre-committed diagnostics for the mechanistic differences that cannot be eliminated, honest statistical framing that does not overstate what the sample size can deliver, and a pre-committed extension plan for the expected inconclusive first wave.

*The science demands nothing less.*
