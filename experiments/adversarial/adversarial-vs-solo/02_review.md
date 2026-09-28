# Design Review: adversarial/adversarial-vs-solo (Revision 1)

**Reviewer**: Volkov
**Date**: 2026-04-11
**Revision**: R1 (re-review of revised 01_design.md)
**Verdict**: APPROVED

---

## Concern Disposition

### Critical

#### C1. Design contradicts itself on problem directory (heilbron_solo vs heilbron)

**RESOLVED.** The contradiction has been eliminated. The revised design commits unambiguously to creating a new `problems/heilbron_solo/` directory (Section 6, line 94-101) with explicit contents enumerated: `validate.py`, `helper.py`, `metrics.yaml`, `task_description.txt`, and `initial_programs/grid.py` -- all identical to the respective files in `problems/heilbron/` or `problems/heilbron_adversarial/pop_a/`. There is no conflicting recommendation elsewhere in the document. The directory does not yet exist on disk, which is expected at design phase.

#### C2. Seed count asymmetry (5 vs 1) inadequately mitigated

**RESOLVED.** The revised design explicitly specifies that `heilbron_solo/initial_programs/` will contain ONLY `grid.py`, identical to the adversarial Constructor seed (Section 6, line 99-101). The rationale is stated: "seed program parity with the adversarial Constructor arm" and "no extra initial diversity confound from the 5-seed solo variant." This eliminates the 5-vs-1 archive coverage confound. Verified: `problems/heilbron_adversarial/pop_a/initial_programs/` contains only `grid.py`, confirming parity.

#### C3. `include_in_prompts` creates unacknowledged hidden IV

**RESOLVED.** The revised design now explicitly acknowledges this as a HIGH-risk confound (Section 9, row 4). The key facts are correctly stated: solo sees 2 metrics (`fitness`, `is_valid`), adversarial sees 4 (`fitness`, `is_valid`, `actual_fitness`, `resistance`). The `resistance` metric provides implicit optimization hints unavailable to solo.

The designer's decision is to NOT modify the adversarial `metrics.yaml`, because the experiment tests "the full adversarial package as-is" rather than isolating opponent pressure. This is framed as an "acknowledged limitation, not a mitigated confound." The implications are carried through to Section 12 (Open Question 1), which explicitly states the experiment cannot distinguish opponent pressure from richer prompts, composite fitness, or adversarial framing.

I accept this framing. The designer has made the tradeoff explicit and consistent: testing the complete adversarial configuration as deployed in prior experiments preserves comparability with the baseline-repro data. Modifying `metrics.yaml` would create a novel configuration never before tested, which introduces its own risk. The limitation is clearly stated and scoped.

### Major

#### M1. 55% power -- NULL should be INCONCLUSIVE not grounds to close line

**RESOLVED.** The interpretation guide (Section 8) has been substantially revised. The four-outcome framework now correctly distinguishes:

- p > 0.10 AND point estimate within 0.001: "SUGGESTIVE NULL -- practical equivalence likely. Close line unless new mechanism proposed."
- p > 0.10 AND point estimate > 0.001: "INCONCLUSIVE -- 55% power cannot distinguish true null from small effect. Do NOT close the line based on this result alone. Consider increasing N."

The MDE at 80% power (~0.0038) is computed and will be reported alongside results. The text explicitly states "Do NOT close the line" for the inconclusive case. This is the correct statistical interpretation.

#### M2. 2x compute asymmetry not adequately addressed

**RESOLVED.** Section 9 (row 2) now includes throughput-normalized comparison as a mitigation. Section 12 (Open Question 2) provides a concrete secondary analysis plan: "compare adversarial at gen 50 vs solo extrapolated to gen 100 (or rerun solo to gen 100 if feasible)." The primary framing is explicitly stated as "per generation comparison, which is what matters for algorithm selection." The opponent evaluation overhead (`FetchOpponentResultsStage`) is acknowledged.

This is a reasonable resolution. The "per generation" framing is the standard in evolutionary computation literature, and the compute-normalized secondary analysis addresses the alternative interpretation.

#### M3. Best-overall metric has order-statistics bias -- should use Constructor-only as primary

**RESOLVED.** The revised design makes Constructor actual_fitness the primary DV (Section 4). The order-statistics reasoning is explicitly stated: "Taking max(Constructor, Improver) inflates the expected value by ~0.56*sigma ~= 0.0015 due to order-statistics bias... This is 50% of the equivalence threshold and would produce a spurious advantage." Best-overall is retained as secondary for continuity with prior reporting. This is exactly what was requested.

#### M4. Task description divergence is a confound

**RESOLVED.** Section 9 (row 5) now explicitly acknowledges the task description divergence as a HIGH-risk confound. The specific optimization hints in the adversarial task description are referenced ("aim for DEEP local optima", game-theoretic framing). The designer correctly notes that isolating the framing effect would require a third arm, which is beyond scope. This is carried through to Section 12 (Open Question 1) as part of the "adversarial package" framing.

Verified against the actual files: `problems/heilbron/task_description.txt` (43 lines, standard optimization) vs `problems/heilbron_adversarial/pop_a/task_description.txt` (62 lines, GAN analogy, explicit strategy guidance). The design's characterization is accurate.

#### M5. One-sided test inappropriate -- need two-sided

**RESOLVED.** Section 8 now specifies a two-sided Welch's t-test with H1: mu_adversarial != mu_solo. The justification explicitly references the adversarial-dynamic-updates NEGATIVE result as evidence that adversarial harm is plausible. The four-outcome interpretation guide covers both directions. This is the correct choice given the empirical evidence base.

### Minor

#### m1. Redis DB allocation TBD

**STILL OPEN (acceptable).** All 12 Redis DB assignments remain "TBD" in the Run Design Table (Section 6). However, this is standard practice at design phase -- DB allocation is typically finalized during implementation when stale DBs are flushed and availability is confirmed. The design notes that 14 DBs are available after flushing adversarial-dynamic-updates data (Section 7). Not blocking.

#### m2. No smoke test protocol for solo

**STILL OPEN (minor).** The design does not include an explicit smoke test protocol for the solo arm. Section 13 provides treatment verification criteria (what to check in `--cfg job` output), but no "run 3 generations and verify metrics" step is specified. This should be part of implementation (Phase 4 Step 2), and the experiment-implement skill typically includes smoke testing. Not blocking, but the implementer should verify that `pipeline=standard` + `problem.name=heilbron_solo` produces valid programs before committing to 12-run launch.

#### m3. Equivalence threshold not formally justified

**RESOLVED.** Section 2 now provides a practical justification: "A 0.003 improvement in min_area would shift a solution from 94.5% to 103% of Q_MAX coverage -- the difference between 'close' and 'solved.' The adversarial engineering cost (doubled runs, sync hooks, paired launch, deadlock risk) is only justified by gains at this scale." This ties the threshold to a concrete operational consequence rather than pure statistical convenience.

#### m4. Stopping rules insufficient

**RESOLVED.** Section 10 now includes a minimum completion threshold: "At least 3/4 runs per arm must reach gen 40 for the arm to be analyzable. If fewer than 3 complete, the arm is marked INCOMPLETE and the experiment verdict is INCONCLUSIVE." Additional data-quality criteria are specified: invalidity rate > 90% sustained for 10+ gens, PID death before gen 10, LLM unreachable for 2+ hours, wall-clock > 5 days, and adversarial generation gap > 10. This is adequate.

#### m5. No blinding protocol

**STILL OPEN (acceptable).** The run labels (S1-S4 vs A1-A4) still make condition assignment obvious. However, given the fully automated analysis pipeline (tools read from experiment.yaml, not hardcoded labels), the risk of analyst bias is low. Not blocking.

#### m6. Fallback opponents not acknowledged

**RESOLVED.** Section 12 (Open Question 4) now explicitly acknowledges the fallback opponents: "Adversarial Pop A has 2 fallback improvers loaded at startup (from `pop_a/fallback/`). Solo has no equivalent mechanism. This provides a warm-start advantage for the adversarial arm that is minor but nonzero. Documented, not mitigated." Verified against the codebase: `pop_a/fallback/` contains `jitter.py` and `local_search.py`; `pop_b/fallback/` contains `fan.py`, `grid.py`, `random_arr.py`. The characterization is accurate.

---

## Summary

| ID | Severity | Status | Notes |
|----|----------|--------|-------|
| C1 | Critical | RESOLVED | Single coherent plan: create `heilbron_solo/` with matched contents |
| C2 | Critical | RESOLVED | 1 seed (grid.py) in both arms, parity confirmed |
| C3 | Critical | RESOLVED | Acknowledged limitation with consistent framing throughout |
| M1 | Major | RESOLVED | INCONCLUSIVE outcome correctly distinguished from NULL |
| M2 | Major | RESOLVED | Compute-normalized secondary analysis planned |
| M3 | Major | RESOLVED | Constructor actual_fitness is now primary DV |
| M4 | Major | RESOLVED | Task description divergence explicitly acknowledged as HIGH confound |
| M5 | Major | RESOLVED | Two-sided test with empirical justification |
| m1 | Minor | OPEN | DB allocation TBD -- standard at design phase, not blocking |
| m2 | Minor | OPEN | No explicit smoke test -- implementer should verify, not blocking |
| m3 | Minor | RESOLVED | Practical justification tied to Q_MAX coverage |
| m4 | Minor | RESOLVED | Minimum completion threshold and data-quality criteria added |
| m5 | Minor | OPEN | No blinding, but automated analysis mitigates risk |
| m6 | Minor | RESOLVED | Fallback opponents acknowledged and documented |

**Critical**: 3/3 resolved
**Major**: 5/5 resolved
**Minor**: 3/6 resolved, 3 open (none blocking)

---

## Verdict

**APPROVED**

The revised design addresses all 3 Critical and all 5 Major concerns. The designer made principled choices throughout: testing the full adversarial package rather than a modified variant preserves comparability with prior experiments; acknowledging confounds as explicit limitations rather than claiming false mitigation is scientifically honest; the four-outcome interpretation guide with the INCONCLUSIVE category prevents premature closure of the research line on underpowered evidence.

The 3 remaining Minor items (Redis DB allocation TBD, no explicit smoke test, no blinding) are standard deferrals to implementation phase and do not affect the validity of the experimental design.

One advisory note for implementation: the `problems/heilbron_solo/` directory does not yet exist. The implementer must create it with exact file parity as specified in Section 6 (lines 94-101), and should run a 3-generation smoke test before committing to the full 12-run launch. This is especially important because this specific combination (`pipeline=standard` + single-seed heilbron problem + current LiteLLM proxy) has never been validated on this infrastructure.
