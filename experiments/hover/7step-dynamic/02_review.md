# Adversarial Review: hover/7step-dynamic

**Date**: 2026-03-30
**Reviewer**: Prof. Alexei Volkov (Reviewer 2)
**Input**: `experiments/hover/7step-dynamic/01_design.md`

---

## Summary of Design

The experiment asks whether dynamic topology mutation (rewiring dependencies, adding/removing steps) within a fixed 7-step budget improves fitness over static prompt-only evolution. This is motivated by the confound in hover/dynamic-topology (PR #116), where the treatment had 10 steps vs. 7 in the control. By constraining both arms to 7 steps, the design attempts to isolate topology flexibility from step-budget effects. The treatment uses `chains/hover/full7` with 3D structural MAP-Elites (4x3x5 = 60 cells); the control uses `chains/hover/static_soft` with 1D fitness binning (60 bins). N=2 per condition, one-sided Welch t-test at alpha=0.10, with a pre-committed extension to N=4.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|----------------|
| 1 | Two bundled IVs (topology mutability + archive indexing strategy) | MAJOR | See detailed analysis below. The justification is reasonable but incomplete. |
| 2 | N=2 yields MDE of 4.4pp -- most plausible effect sizes are undetectable | MAJOR | Acknowledge this is a pilot, not a confirmatory experiment. Reframe accordingly. |
| 3 | Scoring code path differs between conditions (positional vs. adaptive) | MINOR | Equivalence verified in prior experiment, but add explicit verification step to Appendix A. |
| 4 | Frozen-step removal is an unacknowledged third IV | MAJOR | The treatment removes structural priors (guaranteed retrieval hops) in addition to enabling topology mutation. This is distinct from topology freedom. |
| 5 | 7-step topology mutations may never fire (mutation bottleneck) | MAJOR | Pre-specify a manipulation check: if <10% of treatment programs at gen 10 differ structurally from the seed, declare IV inactive and halt. |
| 6 | Alpha=0.10 one-sided with optional extension creates implicit multiplicity | MINOR | Adequately handled by treating N=2 as descriptive only. The protocol is clear. |
| 7 | Non-randomized DB-to-condition assignment | MINOR | Acceptable given Redis DB fungibility. No action needed. |
| 8 | `primary_resolution=60` changes control archive dynamics relative to all prior baselines | MINOR | Acknowledged in Confound #9. Sensitivity analysis against 150-bin historical data is sufficient. |
| 9 | 48h wall-time cutoff may produce unequal generation counts across conditions | MINOR | Pre-specify that analysis normalizes to min(gen_control, gen_treatment) if generation counts differ by >3 across conditions. |

---

## Hypothesis and Falsifiability

- [x] H0 clearly stated
- [x] H1 falsifiable and directional
- [x] Primary metric pre-specified
- [x] Success criteria numeric and unambiguous

**Notes**: The hypothesis framework is well-constructed. H0 and H1 are correctly formulated as a one-sided superiority test. The primary metric (best val fitness at gen 25) is pre-specified. The effect-size threshold table (Section 2) is a strength -- it provides clear interpretive buckets. The "Detectable at N=2?" column is an honest acknowledgment of power limitations.

One minor issue: the "SUGGESTIVE" category (0pp to +1.5pp) will be empirically indistinguishable from noise at N=2. This category should be renamed to "INCONCLUSIVE" to avoid confirmation-biased interpretation.

---

## Confound Analysis

- [x] Controlled variables genuinely controlled
- [ ] IV isolated -- **PARTIAL** (see Concern #4)
- [x] Known confounds mitigated or acknowledged
- [x] Val/test split not contaminated

**Unaddressed confounds**:

### Concern #1 -- Two bundled IVs (MAJOR)

The design bundles topology mutability with structural BC indexing. The stated justification references map-elites-topology (PR #142), which showed BC-only was NULL. The logic is: if this experiment is POSITIVE, it cannot be BC alone (since BC alone was NULL), so it must involve topology flexibility.

This reasoning has a gap. Map-elites-topology tested 3D BC vs. 1D BC with **both conditions having topology freedom on 10-step chains**. It did NOT test 3D BC vs. 1D BC on **static 7-step chains**. The interaction between BC indexing and the constrained 7-step regime is untested. It is conceivable that 3D BC provides a diversity-preservation advantage specifically at the 7-step scale that was invisible at 10 steps (where natural structural variation was already high).

However, this is mitigated by the practical argument in Section 3: 1D fitness binning on a frozen-topology control is indeed the natural choice (structural BC is meaningless when all programs are architecturally identical). The bundling is a defensible design choice, not a fatal flaw. I rate this MAJOR rather than CRITICAL because the control-side argument is sound -- the confound is on the treatment side only.

**Recommendation**: Add a sentence to Section 9 Confound #1 acknowledging the interaction-effect gap explicitly: "We cannot rule out that 3D BC provides a diversity-preservation advantage specific to the 7-step regime that was not observed at 10 steps."

### Concern #4 -- Frozen-step removal as a third IV (MAJOR)

The design frames the treatment as "topology mutability." But `static_soft` has 3 frozen tool steps that guarantee 3 retrieval hops. `full7` has zero frozen steps. Removing frozen annotations is conceptually distinct from enabling topology mutation:

- **Topology freedom** = ability to rewire dependencies, change step types, add/remove steps.
- **Unfreezing** = allowing the LLM to modify retrieval parameters (query templates, k values) or replace tool steps with LLM steps.

Even without any topology mutation (no steps added, removed, or rewired), the treatment programs can diverge from the control by modifying the content of the retrieval steps (e.g., changing k from 7 to 10, modifying query templates). This is a prompt-level change on previously frozen steps, not a topology change.

The design partially addresses this in the "Scientific open questions" table (Section 14, row 2: "Improvement from unfreezing tool steps"). But it does not acknowledge this as a confound in Section 9. If the treatment wins, we cannot distinguish between three causal mechanisms:
1. Topology mutation (new dependency graphs)
2. Unfreezing tool-step parameters
3. The interaction of both

**Recommendation**: Add this as Confound #11 in Section 9 with severity MEDIUM. If the result is POSITIVE, the H_div secondary analysis should be used to assess whether best-by-val programs retained the original 3-tool-step topology (suggesting unfreezing, not topology change, was the driver).

---

## Statistical Validity

- [x] Sample size justified (as a pilot)
- [x] Statistical test appropriate
- [x] Significance threshold pre-specified
- [ ] Multiple comparison correction applied if needed -- N/A (single primary test, secondary is descriptive)

**Notes**:

The MDE analysis is honest and correctly computed. At N=2 with conservative SD=1.5pp, the experiment can only detect effects >= 4.4pp at 80% power. This is a pilot, and the design correctly frames it as such.

The pre-committed extension protocol (Section 8) is well-specified. The claim that "the N=2 interim look does not spend alpha" is technically correct under the stated protocol (N=2 is descriptive, formal test only at N=4 if extended). However, the extension trigger (delta > +1.0pp) introduces a data-dependent decision about whether to collect more data. This is a form of optional stopping. While the alpha is formally preserved (since the N=2 look is not a rejection event), the overall operating characteristics of the procedure should be stated: what is the effective Type I error rate of the complete sequential procedure?

**Recommendation**: Either (a) compute the effective alpha of the full sequential procedure (N=2 descriptive look + conditional N=4 formal test) via simulation, or (b) add a note stating "The effective Type I error rate of this sequential procedure has not been computed; this is accepted as a limitation of the pilot design."

---

## Evaluation Protocol

- [x] Metric computed identically across conditions (soft fractional fitness)
- [x] Val/test sets fixed and identical for all runs
- [x] No post-hoc metric selection
- [x] Thinking mode consistent across evaluations

**Notes**: The evaluation protocol is clean. Val = first 300 of HoVer train, test = 300 held-out. Both conditions use soft fractional fitness. The 5-repeat test protocol is a good practice for reducing stochastic evaluation noise.

One note on scoring: the design states "For identical 7-step chains, both scoring methods produce identical results." This is critical and should be re-verified as part of the pre-launch checks (Appendix A, item 4). The equivalence must hold not just for the seed but for any 7-step chain with the standard 3-tool-step topology. If a treatment program has 7 steps but a non-standard topology (e.g., 2 tool steps + 5 LLM steps), the adaptive scoring in `full7` will correctly handle it, but this is a real topology effect, not a scoring artifact.

---

## Cell-Count Matching

Both conditions have 60 cells/bins. This eliminates granularity asymmetry, which was a potential confound in some MAP-Elites comparisons. The control uses `primary_resolution=60` (non-default, changed from 150). This is well-justified: with `island_max_size=75`, 60 bins gives better utilization (~1.25 programs/bin) than 150 bins (~0.5 programs/bin).

**Rating**: MINOR concern only. The cell-count matching is correctly handled.

---

## Two Bundled IVs -- Detailed Assessment

See Concerns #1 and #4 above. The design bundles three changes relative to the control:
1. Topology mutability (dependencies, step types, step count within 7)
2. Archive indexing (3D structural BC vs. 1D fitness)
3. Frozen-step removal (3 frozen tool steps become mutable)

The design acknowledges #1 and #2 but not #3 explicitly. The justification for bundling #1 and #2 is reasonable (BC-only was NULL at 10 steps; 1D BC is the natural choice for frozen topology). The omission of #3 as a distinct factor is a gap.

**Overall rating for bundled IVs**: MAJOR. Not CRITICAL because (a) the control-side bundling is well-justified, (b) the post-hoc analysis plan (H_div + architecture of best program) can partially disentangle the mechanisms, and (c) the scientific question ("does topology flexibility help at 7 steps?") is inherently a package question in practice.

---

## 7-Step Constraint Feasibility -- Detailed Assessment

This is the experiment's most significant execution risk. The design acknowledges it (Risk 2, Section 14) but does not specify a hard manipulation check.

**The core issue**: With a 7-step cap, adding a step requires first removing one. The mutation LLM performs single-step mutations. A "swap" (remove step X, add step Y with different type/dependencies) requires either (a) two successive mutations that happen to compose well, or (b) a single mutation that the LLM frames as a rewrite of an existing step. Option (b) is plausible (changing a step's type from LLM to tool is a single edit), but option (a) is unlikely to happen reliably.

If the mutation LLM defaults to prompt-only changes (the path of least resistance), then the treatment effectively becomes "static_soft without frozen annotations" -- i.e., the IV (topology mutation) is inactive, and any observed effect comes from unfreezing tool steps (Concern #4).

**Rating**: MAJOR. The experiment may fail to test its stated hypothesis if topology mutations do not occur.

**Recommendation**: Add a formal manipulation check to Section 10:
- At gen 5, compute the fraction of treatment programs whose `(n_steps, n_tool_steps, dag_depth)` triple differs from the seed's triple.
- If this fraction is < 10%, pause the experiment and investigate. If topology mutations cannot be induced, the experiment should be redesigned with explicit topology mutation operators rather than relying on the LLM.
- Report this fraction as a key diagnostic in the results regardless of outcome.

---

## Required Changes Before Approval

1. **Add Confound #11**: Frozen-step removal as a distinct factor (Section 9). Severity MEDIUM. Note that if the result is POSITIVE, the H_div analysis and architecture-of-best-program analysis should assess whether the gain came from topology changes or from unfreezing tool-step parameters.

2. **Add formal manipulation check**: At gen 5, if < 10% of treatment programs differ structurally from the seed topology, flag the IV as inactive. Report topology-change rate as a key diagnostic.

3. **Rename "SUGGESTIVE" to "INCONCLUSIVE"** in the effect-size threshold table (Section 2). An effect of 0-1.5pp at N=2 carries no evidentiary weight.

4. **Acknowledge sequential-procedure limitation**: Add a note in Section 8 stating that the effective Type I error rate of the N=2 descriptive look + conditional N=4 formal test procedure has not been analytically computed.

5. **Add generation-count normalization rule**: In Section 10 or Section 8, specify that if generation counts differ by > 3 across conditions at the 48h cutoff, analysis will use the minimum completed generation across all runs.

---

## Verdict

**[x] APPROVED** (post-R1 revision — all 5 required changes addressed)

**Reviewer notes**:

The experimental design is thoughtful and well-motivated. The scientific question (topology flexibility vs. step budget) is important and clearly articulated. The design builds logically on prior experiments (dynamic-topology, map-elites-topology) and the controlled variables are extensive.

However, three MAJOR concerns prevent immediate approval:

1. **Frozen-step removal is an unacknowledged confound** that creates a third bundled IV. The treatment changes are not purely "topology freedom" -- they also remove structural priors that guarantee retrieval hops. This must be acknowledged and the post-hoc analysis plan must account for it.

2. **No formal manipulation check for topology mutations**. The 7-step constraint may prevent the LLM from performing meaningful topology changes, rendering the IV inactive. A pre-specified diagnostic at gen 5 is essential.

3. **N=2 power is acknowledged but the effect-size labeling is optimistic**. The "SUGGESTIVE" category should not exist at N=2 -- it invites over-interpretation of noise.

None of these are fatal. Items 1-3 and the two minor items (4-5) can be addressed with straightforward additions to the design document. Once revised, this experiment should proceed.

Estimated revision effort: ~30 minutes.

---

*Reviewed by Prof. Alexei Volkov, 2026-03-30.*
