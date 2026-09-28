# Adversarial Review (R2): hover/map-elites-topology

**Date**: 2026-03-29
**Reviewer**: Prof. Dmitri Volkov (Reviewer 2)
**Input**: `experiments/hover/map-elites-topology/01_design.md` (Revised, R1)
**Prior review**: R1 review issued NEEDS REVISION with 4 required changes + 3 additional concerns.

---

## Summary of Design

The experiment tests whether a 3D structural MAP-Elites behavior characterization (`dag_depth` x `max_fan_in` x `n_deep_retrieval`, 5x5x6 = 150 cells) improves evolved chain quality on HoVer compared to the default 1D fitness-only binning (150 bins). The design uses the steady-state engine with LPT scheduling, N=2 per condition (4 runs total), with a pre-committed extension to N=4 if directional signal is promising but statistically inconclusive. The primary DV is best validation fitness at gen 25 (or last completed epoch within 48h). A secondary descriptive hypothesis tests whether treatment runs maintain greater architectural diversity, measured by occupied cell count and Shannon entropy.

**Key change from v1 to R1**: The behavior space was redesigned from a 2D grid (`n_tool_steps` x `n_llm_steps`, 7x7 = 49 cells) to a 3D grid (`dag_depth` x `max_fan_in` x `n_deep_retrieval`, 5x5x6 = 150 cells), grounded in empirical analysis of 824 programs from SS-v2. This change eliminates the cell-count asymmetry that was a primary concern in the R1 review and selects dimensions with demonstrably better independence and spread.

---

## Methodological Concerns

| # | Concern | Severity | Status |
|---|---------|----------|--------|
| 1 | **Cell-count asymmetry (R1 Required #3)** | ~~HIGH~~ RESOLVED | The R1 revision went beyond acknowledgment: the 3D grid was redesigned to 5x5x6 = 150 cells, exactly matching the control's 150 fitness bins. With `island_max_size=75` and 150 cells in both conditions, average occupancy is identical (~0.5 programs/cell). This eliminates the asymmetry rather than merely acknowledging it. Excellent resolution. |
| 2 | **Effect-size table detectability (R1 Required #4)** | ~~HIGH~~ RESOLVED | Section 2 table now includes a "Detectable at N=2?" column with honest annotations: STRONG POSITIVE is "marginally" detectable, POSITIVE and SUGGESTIVE explicitly require N=4 extension. The framing is appropriately cautious. |
| 3 | **N=4 extension protocol (R1 Required #2)** | ~~MEDIUM~~ RESOLVED | Section 8 now contains a full pre-specified protocol: Welch's t-test at alpha=0.10 on all 8 runs, N=2 treated as descriptive only, no alpha adjustment for the interim look. The rationale (interim look does not spend alpha because it is not used as a rejection criterion) is technically sound. |
| 4 | **Endpoint if gen 25 not reached (R1 Required #1)** | ~~MEDIUM~~ RESOLVED | Section 10 specifies: use last completed epoch, 48h wall time budget. Rationale calibrated against SS-v2 epoch advancement rates (~3.5h/epoch under contention). Clear and operational. |
| 5 | **No multiplicity adjustment (R1 Additional #5)** | ~~LOW~~ RESOLVED | Sections 2 and 8 explicitly state the diversity test is "descriptive only" with no multiplicity adjustment. Primary fitness test is the sole confirmatory test. |
| 6 | **Non-randomization of DB-to-condition (R1 Additional #6)** | ~~LOW~~ RESOLVED | Section 6 includes an explicit "Non-randomization note" paragraph acknowledging the limitation and its mitigation (flush-and-verify). |
| 7 | **Diversity metric coarseness (R1 Additional #7)** | ~~LOW~~ RESOLVED | Shannon entropy of cell-occupancy distribution added alongside occupied cell count in Sections 4 and 8. |
| 8 | **`dag_depth` is a new, untested feature** (NEW) | LOW | Unlike `max_fan_in` and `n_deep_retrieval`, `dag_depth` must be newly implemented. The design acknowledges this (Risk 5, Section 14) and specifies unit tests on 5+ sample programs plus a smoke-run integration test (Appendix A). Adequate mitigation for a deterministic algorithm. |
| 9 | **Dynamic expansion could break cell-count matching** (NEW) | NEGLIGIBLE | `expansion_buffer_ratio: 0.1` means the grid could dynamically grow if evolution discovers architectures outside the pre-specified bounds. In principle, this could break the 150-cell symmetry. In practice, the bounds are calibrated from 824 empirical programs with a 10% margin, and any expansion would reflect genuine architectural novelty. Not a concern. |

---

## Hypothesis and Falsifiability

- [x] **H0 clearly stated and falsifiable**: mu_treatment - mu_control <= 0, tested one-sided. Unchanged from v1.
- [x] **Effect-size thresholds pre-specified**: Four-tier table calibrated against prior inter-run variance. Now annotated with detectability at N=2 (R1 fix).
- [x] **Secondary hypothesis stated separately**: H_div on diversity. Explicitly marked as descriptive only (R1 fix).
- [x] **Decision rules cover the extension path**: N=4 extension trigger clearly specified (delta > +1.0pp with p >= 0.10). Analysis protocol pre-specified (R1 fix).
- [x] **Null result is interpretable**: Five-row result-pattern table maps all outcomes to interpretations and next experiments.

---

## Confound Analysis

- [x] **Single IV per comparison**: Only `algorithm=topology_3d` differs between conditions. Verified from `extra_overrides` in Section 6.
- [x] **Cell-count matching**: Both conditions have 150 cells/bins with identical average occupancy. The R1 revision resolved this by redesigning the grid rather than merely acknowledging the asymmetry. The remaining difference -- fitness-axis binning vs. structural-axis binning -- is the intended IV.
- [x] **Pipeline equivalence**: `ChainStructuralMetricsStage` runs on all arms. Still the strongest design feature.
- [x] **Archive selector equivalence**: Both conditions use `SumArchiveSelector` on `retrieval_coverage`. Within-cell competition is on fitness in both conditions.
- [x] **Infrastructure shared**: All runs on same LiteLLM proxy. Symmetric noise.
- [x] **Cold start equivalence**: Both conditions start from scratch.
- [x] **Non-randomization noted**: DB-to-condition assignment is acknowledged as a minor limitation (R1 fix).

---

## Statistical Validity

- [x] **N >= 2 per cell**: Met (2 control, 2 treatment). Hard requirement satisfied.
- [x] **Power limitations honestly stated**: MDE of 4.4pp at 80% power clearly communicated. Effect-size table annotated with detectability. N=2 framed as screening, not definitive. The design does not overclaim what N=2 can resolve.
- [x] **Test appropriate for design**: Welch's t-test, one-sided, alpha=0.10. Valid.
- [x] **Extension protocol pre-registered**: Welch's t-test at alpha=0.10 on all 8 runs. N=2 descriptive only. No alpha adjustment for interim look, with sound justification (interim look is not a rejection criterion). Pre-specified in Section 8.
- [x] **One-sided test justified**: Directional priors from dynamic-topology (+6pp) and mechanistic argument.
- [x] **MDE calculation verified**: SE = 1.5pp, MDE = 4.42pp. Arithmetic unchanged from v1.

---

## Evaluation Protocol

- [x] **Test protocol specified**: 5 independent repeats of 300-sample discrete test eval per run.
- [x] **Treatment verification thorough**: Section 12 provides 6 observable checks + 4 automated checks. Unchanged from v1 (already exemplary).
- [x] **Stop criteria specified**: Early termination, run invalidation, stagnation criterion. Now includes explicit endpoint for wall-time-limited runs (R1 fix).
- [x] **Code verification checklist**: Appendix A lists 8 pre-launch verification steps (expanded from 7 in v1 to include `dag_depth` verification).
- [x] **Endpoint unambiguous**: Gen 25, or last completed epoch if gen 25 not reached within 48h. Clear.

---

## Assessment of the 3D Behavior Space Change

The most substantive revision is the redesign from a 2D behavior space (`n_tool_steps` x `n_llm_steps`) to a 3D space (`dag_depth` x `max_fan_in` x `n_deep_retrieval`). This warrants specific scrutiny:

**Empirical grounding**: The selection is justified by analysis of 824 programs from SS-v2 (4 runs, Redis DBs 3-6). The correlation matrix shows all pairwise |r| < 0.19 -- excellent independence. The rejected alternatives are documented with quantitative reasons (e.g., `n_total_steps` constant at 10 for 79% of programs, `num_forks` redundant with `max_fan_in` at r=0.72). The joint distribution shows 22% cell occupation with no single cell dominating (top cell = 8.0%). This is substantially more thorough than the v1 proposal, which offered no empirical justification for the choice of `n_tool_steps` and `n_llm_steps`.

**Potential concern**: The empirical analysis was conducted on programs evolved under fitness-only binning (SS-v2). Programs evolved under structural binning may exhibit different feature distributions (the treatment changes the selection landscape). However, the SS-v2 data establishes that the features *can* vary -- whether they *will* vary under the treatment is precisely what the experiment tests. The diversity hypothesis (H_div) provides a built-in check.

**Assessment**: The empirical justification is sound. The 3D redesign is a genuine improvement over the v1 proposal, not merely a cosmetic fix. It simultaneously resolves the cell-count asymmetry, improves dimension independence, and increases the resolution of the behavioral characterization.

---

## Required Changes Before Approval

None. All four previously required changes have been addressed:

1. **Endpoint specification** -- Resolved in Section 10 (last completed epoch, 48h budget).
2. **N=4 extension protocol** -- Resolved in Section 8 (pre-specified Welch's t-test, alpha=0.10, N=2 descriptive only).
3. **Cell-count asymmetry** -- Resolved by redesigning the grid to 150 cells (exceeded the original ask of acknowledgment).
4. **Effect-size table detectability** -- Resolved in Section 2 (annotated column).

All three additional concerns (multiplicity, randomization, Shannon entropy) were also addressed. No new critical issues were introduced by the revision.

---

## Verdict

**[x] APPROVED**

The R1 revision addresses all four required changes and all three additional concerns. The most notable improvement is the redesign from a 2D behavior space with a cell-count asymmetry to a 3D space with matched cell counts, grounded in empirical analysis of 824 programs. This is not a minimal fix -- it is a genuine strengthening of the experimental design.

The design retains its prior strengths: pipeline equivalence via shared `ChainStructuralMetricsStage`, thorough treatment verification, honest acknowledgment of N=2 power limitations, and a pre-committed extension protocol with pre-specified analysis. The new `dag_depth` feature is a minor implementation risk, adequately mitigated by the verification checklist.

Remaining limitations (N=2 power, non-randomization of DB-to-condition, potential for structural convergence under treatment) are acknowledged in the design document and are acceptable for an exploratory experiment with a pre-committed extension path.

Approved for implementation and launch.
