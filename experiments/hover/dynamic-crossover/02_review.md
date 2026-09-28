# Phase 2: Adversarial Review -- hover/dynamic-crossover

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Date**: 2026-03-25
**Design reviewed**: `experiments/hover/dynamic-crossover/01_design.md`
**Round**: 1

---

## Summary of Design

The experiment tests whether multi-parent crossover (`num_parents=2`) improves discrete test retrieval coverage over single-parent mutation (`num_parents=1`) in the dynamic topology setting (`chains/hover/full`), with 1 control run and 2 treatment runs sharing a load-balanced mutation LLM pool. The design is explicitly exploratory, with no formal statistical power.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|---------------|
| 1 | Mutation prompt contains no crossover instruction | **Major** | Add a crossover-specific diagnostic or acknowledge as a confound on the IV's mechanistic validity |
| 2 | Treatment ramp-up period reduces effective mutations/gen in early generations | **Minor** | Quantify and document; add as a controlled-variable difference |
| 3 | D5 reference value inconsistency (60.15% vs 60.78%) | **Minor** | Reconcile and use one consistent value |
| 4 | `max_elites_per_generation=5` is the Hydra default; design says 8 but does not list it in the Hydra override command in Appendix A | **Minor** | Add explicit `max_elites_per_generation=8` to the Appendix A verification command |

---

## Hypothesis and Falsifiability

- [x] H0 is clearly stated
- [x] H1 is falsifiable and directional
- [x] Primary metric is pre-specified and sufficient to test H1
- [x] Success criteria are numeric and unambiguous

**Notes**: The hypotheses are well-formed. The effect-size threshold table (Section 2) with the explicit caveat that these are "descriptive benchmarks, not hypothesis-test decision boundaries" is honest and appropriate for the design's power. The note that "a delta < 2pp is indistinguishable from noise" is a good calibration anchor.

---

## Confound Analysis

- [x] All controlled variables are genuinely controlled
- [x] IV is isolated (no other differences between conditions)
- [x] Known confounds are mitigated or acknowledged
- [x] Val/test split is not contaminated

**Concern #1 (Major): The mutation prompt does not instruct the LLM to perform crossover.**

I examined the mutation prompt template at `gigaevo/prompts/mutation/user.txt`. It reads:

> "EVOLUTIONARY MUTATION: Adaptive Code Evolution -- Transform the program using program insights and historical lineage intelligence..."

The entire prompt is written in the singular: "Transform the program." It discusses archetypes for modifying a single parent. With `num_parents=2`, the LLM receives two `=== Parent N ===` blocks appended to this prompt but receives no instruction to combine, merge, or synthesize elements from both parents. The "Approach Synthesis" archetype (archetype #6) mentions "combine multiple techniques" but this is generic evolutionary guidance, not a crossover-specific instruction.

This is not technically a confound (it affects the treatment identically across runs), but it threatens the *mechanistic validity* of the IV. The design claims in Section 3: "the mutation LLM receives both parent programs simultaneously, enabling it to combine structural elements from both into a child program." This is an assumption about LLM behavior, not a guaranteed mechanism. The LLM may simply ignore the second parent entirely -- in which case the treatment is operationally equivalent to the control, and the experiment cannot distinguish "crossover doesn't help" from "crossover never happened."

The design acknowledges this in Risk 1 (Section 12) and Confound #2, and proposes a structural-similarity diagnostic. This is good. However, the risk is rated HIGH, and I agree with that rating. If the diagnostic reveals that >80% of children are structurally identical to one parent, the experiment's primary hypothesis is untestable because the IV was never realized.

**Recommendation**: (a) Add a pre-committed decision rule: if the crossover diagnostic is negative (>80% one-parent dominance), the experiment is reported as "IV NOT REALIZED" rather than "NULL," and the result is not evidence against crossover's utility. (b) Acknowledge in Section 3 that the mutation prompt is generic and does not contain crossover-specific instructions. This is a known limitation of the current implementation.

**Concern #2 (Minor): Treatment ramp-up reduces effective mutations per generation in early generations.**

I examined `AllCombinationsParentSelector.create_parent_iterator()` at `gigaevo/evolution/mutation/parent_selector.py:60-83`. When `num_parents=2`:

- Gen 0: 1 parent available. Fallback to single-parent mode. Yields 1 selection (1 mutation).
- Gen 1: Assume archive grows to 2 programs. `C(2,2)=1`. Only 1 mutation produced.
- Gen 2: If archive grows to 3 programs. `C(3,2)=3`. Only 3 mutations.
- Gen 3: If archive grows to 4. `C(4,2)=6`. Still below the cap of 8.
- Gen 4+: If archive reaches 5+. `C(5,2)=10 >= 8`. Full 8 mutations/gen.

The control (`num_parents=1`) produces 8 mutations from gen 0 onward (since `C(8,1)=8` once the archive has 8 programs, and before that, each available parent yields 1 mutation). But at gen 0, both conditions start with 1 parent, so gen-0 parity holds.

The critical issue: in the treatment condition, gens 1-3 produce fewer than 8 mutations per generation (1, 3, 6 respectively, assuming the archive grows by 1 valid program per generation). Over those 3 generations, the treatment explores roughly 10 mutations versus the control's 24. This is a systematic disadvantage for the treatment in early generations.

The design says in Confound #5: "Gen-0 behavior is identical...The treatment divergence begins at gen 1...This is a 1-generation delay out of 25, unlikely to materially affect the result." This underestimates the issue. It is not a 1-generation delay; it is a 3-4 generation ramp-up during which the treatment has a reduced mutation budget.

**Recommendation**: Document this ramp-up quantitatively. Monitor actual mutations per generation for all runs in the first 5 generations and report the cumulative mutation deficit in the results. Note that this is a minor concern: by gen 5, the deficit is at most ~14 mutations out of 200 total (7%), and the archive would be populated enough for full crossover from that point forward.

---

## Statistical Validity

- [x] Sample size is justified (as exploratory)
- [x] Statistical test is appropriate (descriptive only -- correct given n=1 control)
- [ ] Significance threshold is pre-specified (N/A -- no formal test, appropriate)
- [ ] Multiple comparison correction applied (N/A)

**Notes**: The statistical approach is the strongest section of this document. The researcher has correctly identified that n=1 control makes formal inference impossible, has committed to purely descriptive analysis, and has pre-specified effect-size thresholds as "descriptive benchmarks." The five-analysis structure (primary comparison, D5 reference, control replication, convergence, architecture) is well-organized with clear priorities.

The explicit commitment in Section 7 -- "a powered replication with n>=3 per cell (6 runs total) is needed before any scientific claim can be made" -- is exactly the right language. Appendix C provides an honest justification for the asymmetric design that I find persuasive: treatment variance is unknown and more important to estimate than control variance, given the D5 historical reference.

One note: the inter-run SD calibration range (0.63-1.41pp, from Section 8 Analysis 1) comes from *static-topology* experiments. Dynamic-topology runs may have higher inter-run variance due to the larger search space. The single clean dynamic-topology run (D5) provides no variance estimate. Acknowledge this explicitly.

---

## Evaluation Protocol

- [x] Metric is computed identically across all conditions
- [x] Val set and test set are fixed and identical for all runs
- [x] No metric is cherry-picked post-hoc
- [x] Thinking mode is consistent across all evaluations

**Notes**: The evaluation protocol is sound. 5 independent test repeats per run, discrete scoring, thinking mode Qwen3-8B, 300-sample test set -- all consistent with prior experiments. The metrics.yaml for `chains/hover/full` is identical across conditions (verified: `n_steps` and `n_tool_steps` have `include_in_prompts: false`), eliminating the hidden-IV concern I flagged in the dynamic-topology review.

**Concern #3 (Minor): D5 reference value inconsistency.**

Section 2 says "D5 achieved 60.15% (the only clean dynamic-topology run)." Section 2 also says "D5 result" and later the Decision Tree (Appendix B) uses "D5 reference: 60.15%." But the dynamic-topology results (05_results.md) report D5 top-1 as 60.78% and D5 top-3 mean as 60.15%. The design uses 60.15% (top-3 mean) as the reference, which is the more conservative estimate -- fine. But Section 1 says "D5 achieved 60.78% discrete test coverage" (top-1). This inconsistency should be reconciled: pick one value and use it everywhere, or explicitly state "D5 top-3 mean: 60.15%, D5 best program: 60.78%."

**Concern #4 (Minor): Appendix A verification command omits `max_elites_per_generation`.**

Appendix A, item 1 shows: `python run.py problem.name=chains/hover/full pipeline=standard llm=balanced num_parents=1 --cfg job | grep num_parents`. This command does not include `max_elites_per_generation=8`, which is an explicit override of the default (5). Item 7 mentions it in the full Hydra config verification, but the command in item 1 should also include it (since the AllCombinationsParentSelector's behavior depends on the archive size, which depends on max_elites).

---

## Load Balancer Assessment

The design introduces load-balanced mutation LLM routing (`llm=balanced`) for the first time in this experiment series. I verified the config at `config/llm/balanced.yaml`: it uses `BalancedChatOpenAI` with 3 endpoints, `pool_name: mutation`, Redis DB 15, and 60-second cooldown.

The load balancer **eliminates** the per-run host confound that plagued prior experiments (dedicated mutation server assignment). This is a genuine improvement. All runs draw from the same 3-server pool with equal priority, so no run has a systematically faster or slower mutation server.

The chain LLM endpoints (4 total, shared via `HOVER_CHAIN_URL` with random per-worker selection) are also shared uniformly. No per-run chain server confound exists.

Confound #3 correctly notes that shared-resource contention adds inter-run variance but does not differentially affect treatment vs. control. Confound #6 correctly notes that the D5 comparison is cross-infrastructure (dedicated vs. load-balanced) and should be interpreted with caution. Both assessments are sound.

I see no new confounds introduced by the load balancer that the design has not already identified.

---

## Internal Consistency Check

The design is internally consistent. Key verifications:

1. `pipeline=standard` is correct for `chains/hover/full` which returns a dict from validate.py. Confirmed.
2. `num_parents` default is 2 in `config/constants/evolution.yaml`. The control requires explicit override to 1. The design correctly notes this in Section 5 ("`num_parents` | 1 (single-parent mutation)") but does not flag that this is an override of the default. The Appendix D treatment verification checks correctly include `num_parents` in Hydra cfg for all runs. The run invalidation criteria (Section 10, item 4) correctly flag `num_parents` mismatch as invalidating.
3. Both conditions use `AllCombinationsParentSelector` (hardcoded in `config/evolution/default.yaml`). Correct.
4. `max_elites_per_generation=8` is an override of the default 5. Correctly specified in Section 5.
5. `stage_timeout=5000` and `dag_timeout=7200` match dynamic-topology post-amendment values. Correct.
6. `mutation_mode=rewrite` is the default. With `num_parents=2`, diff mode would raise an error ("Diff mode requires exactly 1 parent" at mutation.py line 357-358). The design correctly uses rewrite mode.
7. Cold start (no `program_loader.problem_dir`) is specified. Correct.
8. The decision tree (Appendix B) is consistent with the effect-size thresholds in Section 2. Correct.

---

## Positive Notes

The Appendix C justification for the asymmetric design is exemplary. It is the clearest treatment of "why n=1 control" I have seen in this research program. The argument that treatment variance estimation is more valuable than control replication, given the D5 historical reference, is logically sound.

The confound analysis (Section 9) is thorough. Nine confounds identified and assessed, with appropriate risk ratings and diagnostics. Confound #9 (crossover may increase invalidity rate) is a genuinely insightful anticipation of a failure mode.

The decision tree (Appendix B) and the open-questions matrix (Section 12) together provide a complete pre-registered interpretation framework. The 2x2 matrix of (improvement vs. no improvement) x (true crossover vs. one-parent dominance) with specific next-experiment recommendations is excellent scientific planning.

---

## Required Changes Before Approval

1. **(Major, Concern #1)**: Section 3 or Section 12 Risk 1: Add a pre-committed decision rule for the case where the crossover diagnostic reveals >80% one-parent dominance. Specifically: if the diagnostic is negative, the result should be classified as "IV NOT REALIZED" in the open-questions matrix (Section 12), not as evidence for "Treatment ~ control." Also add an explicit note in Section 3 acknowledging that the mutation prompt template (`gigaevo/prompts/mutation/user.txt`) does not contain crossover-specific instructions -- the LLM receives two parent blocks but no explicit direction to combine them.

2. **(Minor, Concern #2)**: Section 5 or Confound #5: Correct the claim that gen-0 is a "1-generation delay." Document the 3-4 generation ramp-up during which the treatment produces fewer than 8 mutations/gen due to `C(n,2) < 8` for small archive sizes. Commit to reporting actual mutations/gen for gens 0-5 across all runs.

3. **(Minor, Concern #3)**: Reconcile D5 test reference: use 60.15% (top-3 mean) OR 60.78% (best program) consistently, or define both explicitly where they first appear (Section 1 vs. Section 2).

4. **(Minor, statistical note)**: Section 8 Analysis 1: Acknowledge that the inter-run SD calibration range (0.63-1.41pp) comes from static-topology experiments and may underestimate dynamic-topology inter-run variance.

---

## Verdict

**[x] NEEDS REVISION** -- address required changes, re-submit for review

The major concern (#1) is not a fatal flaw -- the design already identifies the risk -- but the pre-committed decision rule for "IV not realized" must be in place before launch. Without it, a null result is ambiguous: is crossover unhelpful, or did the LLM never actually perform crossover? The three minor concerns are straightforward to address.

The overall design quality is high. The statistical framing is honest, the confound analysis is thorough, and the load-balanced infrastructure is a genuine improvement over prior experiments. Once the major concern is addressed, I expect to approve this design.

*The science demands nothing less.*
