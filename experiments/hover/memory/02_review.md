# Adversarial Review: Memory-Augmented Evolution on HoVer

**Date**: 2026-04-03
**Input**: `experiments/hover/memory/01_design.md`

---

## Summary of Design

Tests whether memory-augmented mutation (episodic card-based memory from a prior evolution run) improves fitness on HoVer dynamic 7-step chains without `retrieve_deep`. Two-phase design: Phase A builds a memory card bank from a single run with `ideas_tracker=true`; Phase B is a controlled experiment with N=2 control (standard mutation) vs N=2 treatment (memory-augmented mutation reading Phase A cards). Primary metric: val soft fitness at gen 25. One-sided Welch's t-test, alpha=0.10.

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|---------------|
| 1 | Phase A is a single point of failure -- one mediocre M0 run produces a weak memory bank, testing "bad memory" rather than "memory as a system" | Advisory | Establish a quality gate: M0 must reach >= 75% val soft before Phase B proceeds. Document M0 fitness in results regardless. |
| 2 | experiment.yaml still has template placeholders | Advisory | Fill during implementation phase. Not a design flaw. |
| 3 | Config mismatch: design says `stage_timeout=6000`, `dag_timeout=14400`; experiment.yaml template shows 3000/7200 | Advisory | Align manifest to design values during implementation. |
| 4 | OpenRouter dependency for ideas tracker during Phase A could fail silently | Advisory | Verify OpenRouter access before Phase A launch; check card count after Phase A completes. |
| 5 | No statistical test specified for secondary DV (convergence speed) | Advisory | Report descriptively only. Acceptable for N=2. |

No concerns rise to blocking severity.

## Hypothesis and Falsifiability

- [x] H0 clearly stated
- [x] H1 falsifiable and directional
- [x] Primary metric pre-specified
- [x] Success criteria numeric and unambiguous

**Notes**: H0/H1 are clean. Effect-size thresholds (NULL/SUGGESTIVE/POSITIVE/STRONG POSITIVE) are well-calibrated against the HoVer research line history. The +1.5pp and +3.0pp boundaries are reasonable given prior inter-run SD of ~1.5pp.

## Confound Analysis

- [x] Controlled variables genuinely controlled
- [x] IV isolated
- [x] Known confounds mitigated or acknowledged
- [x] Val/test split not contaminated

**Unaddressed confounds**: The treatment introduces a MemorySelectorAgent execution step (~1-2s per mutation) that the control does not have. This is an inherent and unavoidable property of the treatment, not a design flaw. The design correctly argues the overhead is negligible relative to chain evaluation time (~10min). I accept this. No other unaddressed confounds identified.

## Statistical Validity

- [x] Sample size justified
- [x] Statistical test appropriate
- [x] Significance threshold pre-specified
- [x] Multiple comparison correction applied if needed

**Notes**: N=2 per cell is the minimum. Power analysis is honest: MDE ~4.4pp at 80% power. The relaxed alpha=0.10 is appropriate for an exploratory first test. Welch's t-test (unequal variance) is the right choice given that memory-augmented runs could plausibly have different variance. No multiple comparison correction needed (single primary metric, single test). The pre-commitment to a powered follow-up at N=4 if a suggestive signal appears is responsible practice.

SE calculation verified: SD=1.5, n1=n2=2, SE = 1.5 * sqrt(1/2 + 1/2) = 1.5pp. Correct.

## Evaluation Protocol

- [x] Metric computed identically across conditions
- [x] Val/test sets fixed and identical for all runs
- [x] No post-hoc metric selection
- [x] Thinking mode consistent across evaluations

**Notes**: All runs use the same `chains/hover/full7_no_deep` variant, same LiteLLM proxy (Qwen3-8B thinking mode), same validation set. Test eval uses 5-repeat protocol on 300-sample held-out set, standard for the HoVer line. Treatment verification plan is thorough: 5 checks covering config overrides, log patterns, program metadata, and a precondition check. The gen-5 manipulation check (>10% of treatment programs must have `memory_selected_ids`) is a good safeguard. I confirmed all four referenced code paths exist in the codebase (`MemorySelectorAgent`, `memory_selected_ids`, `memory_enabled` config field, engine runtime check).

## Required Changes Before Approval

None. All concerns are advisory.

---

## Verdict

**[x] APPROVED**

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**: The design is clean, well-motivated, and appropriately scoped for a first test of new infrastructure. The single IV is correctly isolated, the two-phase structure is inherent to the memory system (not an avoidable design choice), and the treatment verification plan is among the most thorough I have seen in this research line. N=2 limits statistical power but is sufficient for detecting strong effects, and the pre-commitment to follow-up is responsible. Advisory notes above should be addressed during implementation and results interpretation but do not block execution.
