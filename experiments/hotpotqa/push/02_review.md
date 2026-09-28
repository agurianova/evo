# Adversarial Review: GEPA Push — 4-Run Targeted Attack on 62.3% Test EM

**Date**: 2026-03-07
**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary agent)
**Input**: `experiments/hotpotqa/push/01_design.md`
**Supporting reads**: `experiments/hotpotqa/val_gap/05_results.md`, `experiments/hotpotqa/CONTEXT.md`, `experiments/hotpotqa/nlp_prompts/05_results.md`, `gigaevo/entrypoint/constants.py`, `gigaevo/entrypoint/default_pipelines.py`, `problems/chains/hotpotqa/static_a/pipeline.py`, `config/pipeline/hotpotqa_asi.yaml`, `config/constants/pipeline.yaml`, `gigaevo/prompts/hotpotqa/mutation/system.txt`

---

## Summary of Design

Four evolutionary runs in a partial 2³ factorial (fitness × prompts × val-N) targeting
the GEPA benchmark (62.3% test EM). Run A: F1 fitness + NLP prompts, fixed-300. Run B:
EM fitness + default prompts, fixed-600. Run C: F1 fitness + default prompts, fixed-600.
Run D: EM fitness + NLP prompts, fixed-600. Reference cells from prior experiments
(Runs O and F from val_gap) are used for cross-run comparisons. Primary metric is test EM
at gen 50, best-by-val, on the 300-sample held-out test set.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|---------------|
| 1 | `stage_timeout=6000` Hydra override is silently inert under `pipeline=hotpotqa_asi` | **Critical** | Fix `DEFAULT_SIMPLE_STAGE_TIMEOUT` or add a timeout parameter to ASIPipelineBuilder before launch |
| 2 | NLP mutation prompt system.txt hardcodes "exact match accuracy" in the ROLE section, conflicting with F1 task_description in Run A | **Major** | Resolve the internal contradiction; update system.txt ROLE framing for F1 runs or acknowledge as a deliberate compound confound |
| 3 | The 600-sample compute justification ignores the stagnation ceiling — all 4 prior 300-sample runs peaked at birth-gen 4–6; 600-sample at 50 gens may buy nothing but wall-clock time | **Major** | Pre-register a max_generations=25 cap for 600-sample runs, or explicitly justify why 50 gens is appropriate given confirmed stagnation |
| 4 | No pre-registered primary comparison hierarchy for the experiment-level verdict across 4 runs — the decision tree in Section 12 lists only single-run GEPA crossings and is not a hierarchy | **Major** | Add a Section 2 statement: "The primary test for the experiment-level POSITIVE verdict is [run X, comparison Y]. All others are secondary." |
| 5 | `static_f1_600` problem directory does not exist; Run C depends on a new code artifact whose implementation correctness is unverified at design time | **Major** | Require unit test for validate.py (F1 computation + valid_frontier_em key) as a blocking precondition before Run C launches; document expected gen-0 F1 and EM values |
| 6 | dag_timeout=7200 fires before multiple sequential 600-sample evals can complete per generation | **Major** | Compute per-generation dag_timeout budget correctly; 7200s / (stage_timeout=6000 for validator alone) leaves < 1200s for all other stages |
| 7 | Run F as reference cell has N=1 and is a compound treatment (F1 metric + F1 mutation guidance); using it as the "F1-only" baseline for Run A comparison introduces a false decomposition | **Minor** | Clarify in Sections 2 and 8 that "F1-only" reference is itself a compound treatment; rename to "F1-protocol baseline" consistently |
| 8 | SUGGESTIVE band in primary test (Section 8) adds a secondary gap-reduction condition that does not appear in the hypotheses (Section 2) | **Minor** | Cross-check that every decision-gate condition in Section 8 appears verbatim in Sections 2 and 4; add gap_B < gap_O - 1.0pp as explicit secondary condition in H₁(B) or remove from Gate C |
| 9 | NLP prompts silent-failure pre-launch check is correct but insufficient for Run D — the check must verify `prompts_dir` appears in `evolution_context` AND `mutation_operator` blocks separately | **Minor** | Section 6 pre-launch check should explicitly state: inspect `--cfg job` output and confirm two distinct `prompts_dir` entries, not one |

---

## Concern 1 (Critical): `stage_timeout` Hydra Override Is Silently Inert Under `pipeline=hotpotqa_asi`

This is the experiment's most serious flaw, and it will produce the exact same failure mode that invalidated Run Q.

The design states (Section 5, Controlled Variables):
> "Runs B, C: `stage_timeout=6000` (600-sample eval; empirical max ~2300s observed in val_gap Run Q; 6000s provides 2.6× margin above observed max; safe per Amendment 2 lesson)"

And (Section 12, Risk 2):
> "We are using stage_timeout=6000, which provides 2.6× margin over the observed max of ~2300s."

This reasoning is correct in principle but incorrect in implementation. Code inspection reveals:

1. `/workspace-SR008.fs2/mathemage/gigaevo-core/gigaevo/entrypoint/constants.py`, line 1:
   `DEFAULT_SIMPLE_STAGE_TIMEOUT = 2400`

2. `/workspace-SR008.fs2/mathemage/gigaevo-core/gigaevo/entrypoint/default_pipelines.py`, lines 182–191:
   ```python
   self.add_stage(
       "CallValidatorFunction",
       lambda: CallValidatorFunction(
           path=validator_path,
           function_name="validate",
           timeout=DEFAULT_SIMPLE_STAGE_TIMEOUT,  # ← hardcoded constant, not Hydra var
           ...
       ),
   )
   ```

3. `/workspace-SR008.fs2/mathemage/gigaevo-core/problems/chains/hotpotqa/static_a/pipeline.py`, line 26:
   `ASIPipelineBuilder.__init__` calls `super().__init__(ctx, dag_timeout=dag_timeout)` — it does not override the `CallValidatorFunction` timeout.

4. `/workspace-SR008.fs2/mathemage/gigaevo-core/config/constants/pipeline.yaml`, line 4:
   `stage_timeout: 2400` — this Hydra variable is only consumed by `custom.yaml`, which explicitly wires it to each stage via `timeout: ${stage_timeout}`. The `hotpotqa_asi` pipeline builder ignores this variable entirely.

**Consequence**: Passing `stage_timeout=6000` on the command line has no effect on the `CallValidatorFunction` timeout when using `pipeline=hotpotqa_asi`. The validator will still time out at 2400s, and Runs B, C, and D will replicate Run Q's 96.3% invalidity rate exactly.

The design document correctly diagnoses Amendment 2's root cause ("stage_timeout=2400s was insufficient") but has not verified that the proposed fix (`stage_timeout=6000` override) is mechanically effective for the selected pipeline. It is not.

**Required fix before launch**: Either (a) modify `DEFAULT_SIMPLE_STAGE_TIMEOUT` in `constants.py` to 6000 (affects all runs including A — acceptable since 6000 > 2400 is conservative), or (b) add a `stage_timeout: int = DEFAULT_SIMPLE_STAGE_TIMEOUT` parameter to `ASIPipelineBuilder.__init__` and wire it to `CallValidatorFunction`, passing the Hydra `${stage_timeout}` value via the YAML config, or (c) add a `pipeline=hotpotqa_asi_600` variant that explicitly overrides the timeout. The `--cfg job` pre-launch check does not catch this because the timeout is set inside the Python factory, not in the YAML config.

**This concern must be resolved before any 600-sample run launches.**

---

## Concern 2 (Major): NLP Mutation Prompt Hardcodes "Exact Match" in ROLE Section — Conflicts with F1 Task Description in Run A

The design identifies this risk (Section 12, Risk 4):
> "NLP prompts (designed for the EM landscape) inject conflicting objectives into the mutation LLM when paired with F1 fitness... If NLP prompts hard-code 'maximize exact match' phrases, they must be updated for consistency with the F1 objective before Run A launches."

Code inspection of `/workspace-SR008.fs2/mathemage/gigaevo-core/gigaevo/prompts/hotpotqa/mutation/system.txt`, line 4:
> "You operate within an evolutionary framework where prompt-chain programs are iteratively mutated and evaluated based on their **exact match accuracy** on multi-hop question answering."

This is hardcoded in the ROLE section, which appears before the `{task_description}` placeholder on line 7. The mutation LLM reads:

1. ROLE: "evaluated based on their exact match accuracy" (hardcoded EM framing)
2. OBJECTIVE: {task_description} → injected from `static_f1/task_description.txt` which says "Challenge: Design a chain that maximizes token-level F1 accuracy"

These are directly contradictory instructions in the same prompt. The LLM receives two conflicting objective framings with no reconciliation. The ROLE section establishes the context before the OBJECTIVE is read; the LLM may anchor on "exact match accuracy" from the ROLE and underweight the F1 objective from task_description.

The design acknowledges the risk exists but frames it as something to "review before launch." Given my recurring-weakness pattern (compound treatments stated as single-variable tests), this is not sufficient. The NLP prompt conflict is not just a risk to review — it is an already-identifiable methodological flaw. If the ROLE section contradicts the OBJECTIVE, Run A is not testing "F1 fitness + NLP prompts" — it is testing "F1 fitness + EM-framed NLP prompts," a distinct compound treatment. The mutation LLM's guidance is internally inconsistent, and any result from Run A is harder to interpret as a result of NLP prompts per se.

The mitigation proposed ("review the NLP prompt files before launch... If NLP prompts hard-code 'maximize exact match' phrases, they must be updated... This constitutes a pre-registered change and must be documented as Amendment 1 if executed") is adequate in structure but not sufficient as stated. The design should pre-register the specific change required NOW (update system.txt line 4 to be metric-agnostic) rather than deferring to Phase 4 discovery. The current system.txt text is a known flaw — it has been identified at design time.

**Required fix**: Update `gigaevo/prompts/hotpotqa/mutation/system.txt` line 4 to remove "exact match accuracy" and replace with metric-agnostic framing (e.g., "evaluated based on their task performance on multi-hop question answering") before Run A launches. Document this as Amendment 1 in `03_plan.md`. If the researcher chooses to leave system.txt unchanged and run A with the conflicting framing, this must be explicitly classified as a deliberate compound confound (not just a risk), and the amendment type must be "Confound introduced — deliberate." A compound confound that the researcher already identified at design time cannot be classified post-hoc as a minor unknown.

---

## Concern 3 (Major): 600-Sample Runs at 50 Generations Are Unjustified Given Confirmed Stagnation by Birth-Gen 6

The researcher's pre-stated concern is exactly right. I will quantify why it matters.

All seven valid single-parent HotpotQA GigaEvo runs stagnate by birth-generation 4–6. The frontier does not improve after birth-gen 6 in any case (val_gap 05_results.md §4a; nlp_prompts 05_results.md §4.1). "Birth-generation" is not the same as "generation" — a birth-gen-6 program may be discovered at any iteration 6–50, but on average stagnation of the frontier is confirmed by generation ~30. This means the decision-relevant information is all produced in the first 25–30 iterations.

At 600 samples with the corrected stage_timeout, each program takes a mean of 1412s. At 8 mutations/gen and 4 workers processing sequentially in two phases, the generation time is approximately:
  8 mutations × 2 phases × (1412s mean) / 4 workers ≈ 5648s ≈ 1.57 hours per generation

At 50 generations: 50 × 1.57h ≈ 78.5 hours. The design estimate of ~50h appears to assume full parallelism (divides by 4 workers without accounting for the 2-phase sequential structure). Even if 50h is correct, it is 2× the 300-sample budget.

The question is: does paying 2× wall-clock time for the full 50 gens add scientific value beyond 25 gens?

Under confirmed stagnation by birth-gen ~6, the answer is no — the 25-gen result will be statistically indistinguishable from the 50-gen result at any reasonable tolerance, and the frontier will not improve in gens 25–50. The marginal scientific value of gens 26–50 for 600-sample runs is near zero, while the cost is 50% of total compute. This is a waste of finite compute budget.

The design could address this by pre-registering an early-stopping rule for 600-sample runs: if the frontier val fitness has not improved for 10 consecutive generations (the typical stagnation signal), terminate early and report results. This should be more aggressive than the current invalidity-rate stopping criteria (which are health checks, not scientific stopping criteria).

Alternatively, pre-register max_generations=25 for Runs B, C, D explicitly, with justification: "Given confirmed stagnation by birth-gen 6 across all prior runs, 25 gens provides ≥ 4× the stagnation window and is sufficient to observe the frontier peak and confirm convergence. Extending to 50 gens does not change the best-by-val result under confirmed stagnation."

The design currently contains no stagnation-based stopping criterion, only invalidity-rate criteria. This is an omission. If all 600-sample runs stagnate by gen 25, the researcher will have paid double the compute to get the same result — and will have pre-registered 50 gens, making an early stop look like a deviation.

---

## Concern 4 (Major): No Pre-Registered Primary Comparison Hierarchy for Experiment-Level Verdict

The decision tree in Section 12 lists outcomes by individual run (A ≥ 62.3%? → C ≥ 62.3%? → B ≥ 62.3%?) but does not specify:

(a) Whether any ordering among {A, B, C, D} is pre-registered as primary, or whether all four are treated as equally ranked tests of H₁(cross).

(b) What the experiment-level conclusion is if exactly two of {A, B, C, D} exceed 62.3%.

(c) Whether a SUGGESTIVE result (test EM in [61.5%, 62.3%)) from Run C plus a NULL from Run A should be reported as "F1+600 is promising, NLP prompts add nothing" — a conclusion that requires decomposing the 2³ design — or simply as "SUGGESTIVE."

From my memory of the val_gap v2 review: "When a design expands from 2-cell to 2×2, the number of pairwise comparisons grows from 1 to 6. Without a pre-registered primary comparison hierarchy, Phase 5 analysis will emphasize whichever comparison looks most interesting post-hoc." The push design has four runs and potentially 6+ pairwise comparisons. The H₁(cross) formulation ("at least one of {A, B, C, D} achieves test EM ≥ 62.3%") is the only composite hypothesis, but it does not serve as a primary comparison — it is a disjunction over four independent runs.

**Required fix**: Add to Section 2 (or create a Section 2a): "The primary verdict for the experiment-level conclusion is: Run C (F1×default×600) is the highest-leverage test of the combined gap-reduction mechanisms; if only one run can exceed GEPA, Run C is the planned primary test for the experimental series conclusion. Runs A, B, D are secondary: they test specific mechanism combinations but do not individually determine the experiment-level verdict." If the researcher disagrees with this ordering, a different hierarchy is acceptable — but some hierarchy must be pre-registered.

---

## Concern 5 (Major): `static_f1_600` Code Artifact Is Unverified at Design Time

The design correctly identifies this as "the highest-risk item" (Section 12, Risk 1). I agree with the risk characterization. However, the mitigation is described as:

> "add a unit test for the validate.py, and verify at dry-run (gen-0 archive entry must have both `fitness` (F1) and `em` (EM) fields populated; both should be non-zero on the seed program)"

This is adequate in principle but the design does not specify:

1. The expected gen-0 F1 value for `static_f1_600`. For `static_f1` (300-sample), gen-0 val F1 was 70.27% (val_gap §4a). For `static_f1_600`, the expected gen-0 val F1 is not stated. If the 600-sample F1 differs substantially from 70.27%, this is not a validation failure — but without a pre-registered expected range, the researcher cannot know at dry-run whether the gen-0 value is correct or indicates a bug.

2. Whether the `static_f1_600/validate.py` computes F1 over the full 600-sample batch correctly. F1 is a per-sample quantity averaged over the batch; the implementation must sum individual F1 values and divide by 600, not apply a global token-count formula. This should be verified by comparing `static_f1_600` gen-0 result to `static_f1` gen-0 result: the expected relationship is `F1_600 ≈ F1_300` (same underlying distribution, larger sample, lower variance) not `F1_600 = F1_300 × 2`.

3. Whether `valid_frontier_em` is populated using the 600-sample EM count (correct) or the 300-sample count (a copy-paste error). This is the most likely source of silent failure if `static_f1_600` is implemented by copy-paste from `static_f1` with `N=600` substituted.

**Required fix**: Add to Section 5 (or Section 12, Risk 1): "Expected gen-0 val F1 for static_f1_600: approximately [pre-register a range, e.g., 68–72%] based on static_f1 gen-0 val F1 = 70.27% scaled to 600 samples (lower variance, same mean). Expected gen-0 val EM for static_f1_600: approximately 59–61% (consistent with static gen-0 val EM from the seed). If gen-0 results fall outside these ranges, halt and diagnose before proceeding."

---

## Concern 6 (Major): `dag_timeout=7200` Is Insufficient for 600-Sample Runs Under Corrected `stage_timeout`

Section 5 states:
> "Note: `dag_timeout=7200` must be verified not to fire before `stage_timeout=6000` for Runs B/C. 600-sample mean eval time ~1412s; with 8 parallel workers, mean gen time ≈ 1412s / (4 workers / 2 sequential phases per gen) ≈ 700s."

The arithmetic is incorrect. `dag_timeout` is a per-program-evaluation timeout (the time for one program's entire DAG to complete), not a per-generation timeout. A single program's DAG includes: `CallValidatorFunction` (up to 6000s) + all LLM stages (InsightsStage, LineageStage, MutationContextStage, etc. — typically 300–600s for the mutation LLM). The total per-program DAG time can reach 6000 + 600 = 6600s, which is below dag_timeout=7200 by only 600s margin.

More critically: if `CallValidatorFunction` takes 5800s (within the new stage_timeout=6000 limit), the remaining 1400s for all subsequent pipeline stages is tight. The mutation LLM calls can easily take 200–400s each (InsightsStage + LineageStage), and multiple retry attempts compound this. A dag_timeout of 7200s may fire before the mutation LLM stages complete, even when the validator itself completes within stage_timeout.

The correct calculation is: `dag_timeout` must be ≥ `stage_timeout` + all non-validator stage timeouts. With stage_timeout=6000 for the validator alone, dag_timeout should be at least 6000 + 3 × `DEFAULT_SIMPLE_STAGE_TIMEOUT` = 6000 + 3 × 2400 = 13200s. The design uses dag_timeout=7200, which is 2× the validator-only stage_timeout and leaves no headroom for LLM stages under heavy load.

Note: this concern is conditional on Concern 1 being resolved first. If `stage_timeout=6000` is actually wired to the validator (after fixing Concern 1), then `dag_timeout=7200` is potentially too low. If Concern 1 is not fixed, `stage_timeout` remains 2400 and `dag_timeout=7200` is adequate for the validator but the whole design is moot.

**Required fix**: Resolve Concern 1 first. Then recalculate dag_timeout as: max_validator_time + expected_mutation_llm_time + headroom = 6000 + 1500 + 1000 = 8500s minimum. Pre-register `dag_timeout=9000` for Runs B, C, D, and document the calculation.

---

## Hypothesis and Falsifiability

- [x] H₀ clearly stated — all four null hypotheses are stated and specific.
- [x] H₁ falsifiable and directional — each H₁ specifies a threshold and direction.
- [x] Primary metric pre-specified and sufficient — test EM at gen 50, best-by-val, consistent with GEPA benchmark.
- [x] Success criteria numeric and unambiguous — GEPA (62.3%) is a fixed external threshold; gate thresholds are numeric.

**Notes**: The hypotheses are individually well-formed. The cross-run composite hypothesis H₁(cross) is legitimate as a motivational framing but is not a proper statistical hypothesis (it is a disjunction over four tests with no pre-registered priority order — see Concern 4). The falsifiability is adequate for an n=1 screening study; the design correctly characterizes this as "hypothesis-motivated, not statistically powered."

One precision issue: H₀(A) states "no higher than the F1-only result (Run F, val_gap: 61.67%)" — but the primary metric threshold for POSITIVE in Section 8 is 62.3% (GEPA), not 61.67%. If Run A achieves 61.8% it simultaneously fails H₀(A) in a directional sense but falls in the SUGGESTIVE band by Section 8's criteria. This inconsistency is not fatal but should be harmonized: the H₁(A) threshold for what "matters" (Section 2) should match the POSITIVE threshold in Section 8.

---

## Confound Analysis

- [x] All controlled variables are genuinely controlled — pipeline, seed, chain topology, test set, thinking mode are all held constant across runs. Documented clearly.
- [ ] IV is isolated — NOT fully isolated: Run A has three simultaneous IV changes vs. Run O (fitness + prompts + the compound F1-protocol treatment from Run F). See Concern 2.
- [x] Known confounds are mitigated or acknowledged — compound treatments in A and C are explicitly acknowledged; Run F as compound-treatment reference is noted.
- [x] Val/test split is not contaminated — fixed sequential val (first N train samples); test set is held out. No contamination risk.

**Unaddressed confounds**:

**Unaddressed Confound 1**: The `static_f1/task_description.txt` injects F1-framing into the mutation LLM context, while the NLP mutation prompt's system.txt simultaneously injects EM-framing into the same context. For Run A, the mutation LLM receives both. This is not acknowledged as a confound — it is listed only as "Risk 4." The correct classification is: "Known confound for Run A: mutation LLM receives internally contradictory metric framing. Mitigation: update system.txt line 4 to remove 'exact match accuracy' before launch." See Concern 2.

**Unaddressed Confound 2**: The design notes (Section 9): "The ddce37b4 seed was evolved under EM fitness; using it as warm-start for F1 runs (A, C) introduces a fitness-distribution mismatch at gen 0." This is correctly acknowledged but not adequately mitigated. The mitigation stated is "Inspect gen-0 val F1 for A and C at dry-run; if < 62.7% (the seed's val EM), there is no regression." This comparison is invalid: val F1 and val EM are not directly comparable numbers (70.27% F1 ≠ 62.7% EM for the same seed program). The correct check is: gen-0 val F1 for A and C should approximately match val F1 reported for Run F at gen-0 (70.27% for `static_f1`; ~68–72% for `static_f1_600`). The current mitigation language should be corrected.

---

## Statistical Validity

- [x] Sample size is justified — n=1 per cell is the infrastructure constraint; correctly acknowledged with appropriate language (SUGGESTIVE/POSITIVE/NULL ladder).
- [x] Statistical test appropriate — no formal p-values at n=1; threshold comparisons vs. fixed external benchmark (GEPA) are appropriate.
- [x] Significance threshold pre-specified — 62.3% for POSITIVE; 61.5% for SUGGESTIVE lower bound.
- [ ] Multiple comparison correction — NOT addressed. Four runs tested against the same threshold (GEPA), with H₁(cross) framed as "at least one succeeds." No multiplicity adjustment is applied or discussed.

**Notes**: The multiplicity issue is real but is correctly handled implicitly by the SUGGESTIVE/replication ladder: any single run exceeding GEPA is classified as SUGGESTIVE requiring N ≥ 3 replication, not as a definitive result. This is the appropriate statistical posture for an n=1 screening study. However, the design should acknowledge explicitly that testing four runs against the same threshold inflates the probability of a spurious crossing, which is why the replication requirement is non-negotiable. The current text says this ("A single run above GEPA is treated as SUGGESTIVE requiring follow-up replication (N ≥ 3)") but does not connect the SUGGESTIVE classification to the multiplicity motivation. Add one sentence: "With four runs tested against the same threshold, the probability of at least one spurious crossing by noise alone is ~4× the single-run probability; the replication requirement directly controls this multiplicity."

The Section 7 noise propagation for Gate C (gap comparison ±4.0pp) is acceptable and correctly computed. The Section 7 statement that "MDE at 80% power, α=0.05, with σ≈2.4pp is ≈6.7pp" is internally consistent but the 2.4pp σ estimate derives from same-program retest noise (single-run stochastic variation), not from inter-run variation. The inter-run SD is unknown from the data (n=1 per prior cell). This distinction matters for interpreting "two runs are statistically indistinguishable if |Δ EM| < 5.5pp." That CI is for the single-measurement noise on a single run; the uncertainty from using run O or run F as reference cells adds additional variance that is not quantified.

---

## Evaluation Protocol

- [x] Metric computed identically across all conditions — test EM using `run_test_eval.sh` with sha256 verification; thinking mode required; consistent with GEPA benchmark.
- [x] Val set and test set fixed and identical for all runs — fixed sequential val from train split; test set is the 300-sample held-out set.
- [x] No metric cherry-picked post-hoc — primary metric (test EM) is pre-specified; val EM and gap are secondary; F1 is tertiary.
- [x] Thinking mode consistent — required and verified; consistent with GEPA benchmark.

**Notes**: The cross-metric gap accounting for F1 runs (Runs A, C) is correctly handled: the design requires `valid_frontier_em` to be tracked alongside val F1, and uses within-metric val EM (not val F1) for gap computation. This is the approach that worked in val_gap Run F and avoids the structural inflation problem identified in my prior review.

One procedural precision issue: Section 8 states "No bootstrapping is planned (n=300 is adequate for point estimates; CIs can be added post-hoc if a run is close to 62.3%)." Adding CIs post-hoc is acceptable since they are symmetric and non-directional, but the phrase "if a run is close to 62.3%" could be read as justifying selective CI computation based on the result. Recommend: "Binomial 95% CIs will be computed for all runs regardless of proximity to 62.3%, reported in Section 5 of the results document."

---

## On the Pre-Stated Researcher Concern: Are 600-Sample Runs at 50 Gens Justified?

The researcher asked me to address this explicitly. My answer is no — and I have elevated it to Major (Concern 3).

The core argument is arithmetic: the val_gap results show that under single-parent mutation, all runs stagnate before birth-generation 10. The best-by-val program is born by gen 6, is selected around gen 40–43 (when it has survived long enough to be top of the archive), and produces no frontier improvements after that. Running for 50 gens does not improve the result — it confirms that the result has not improved.

The cost of a 600-sample 50-gen run is approximately 2× a 300-sample 50-gen run. The expected additional scientific value of gens 26–50 is approximately zero under the stagnation hypothesis. Therefore the question is not "does 600-sample reduce the gap" (that is the Gate C hypothesis and is worth testing) but "does 600-sample at 50 gens reduce the gap" (versus 600-sample at 25 gens). The answer should be identical under stagnation.

A 25-gen cap for 600-sample runs would:
- Reduce wall-clock time from ~50h to ~25h per run
- Produce identical scientific information (same stagnation result, same best-by-val program, same test EM at gen 25 ≈ test EM at gen 50 under confirmed stagnation)
- Allow three 600-sample runs within the same total compute budget

The design should pre-register a stagnation-based early-stopping criterion for 600-sample runs: "If the frontier val fitness has not improved for ≥ 10 consecutive generations, the run may be terminated early. Results are reported on the full archive at that point. This is not an invalidation — it is an early-completion under the confirmed stagnation pattern." This does not weaken the study; it correctly reflects the known dynamics.

---

## Required Changes Before Approval

1. **[Critical — blocks all 600-sample runs]** Demonstrate that `stage_timeout=6000` is actually applied to `CallValidatorFunction` under `pipeline=hotpotqa_asi`. Show the mechanism: either (a) modify `DEFAULT_SIMPLE_STAGE_TIMEOUT` in `constants.py`, (b) add a stage_timeout parameter to `ASIPipelineBuilder` and wire it through the Hydra config, or (c) create a new pipeline variant with the corrected timeout. The `--cfg job` dry-run is not sufficient to catch this because the timeout is set in Python code, not in the YAML. Add a launch-time verification: "Inspect the running exec_runner log at gen 0 to confirm that the `CallValidatorFunction` stage is not timing out within 2400s." The design currently does not include this check.

2. **[Major — required before Run A launches]** Resolve the NLP prompt EM/F1 conflict in `gigaevo/prompts/hotpotqa/mutation/system.txt` line 4. Pre-register the specific change in `03_plan.md` as Amendment 1. If the researcher chooses to leave system.txt unchanged and treat Run A as a deliberate compound confound, reclassify Run A's confound table entry accordingly and update Section 8's Run A verdict language to reflect that any result cannot be attributed to NLP prompts specifically.

3. **[Major]** Pre-register a stagnation-based early-stopping criterion for 600-sample runs (Runs B, C, D), or pre-register max_generations=25 explicitly. The current stop criteria (invalidity rate > 50%, sanity failure) are infrastructure health checks. A scientific stopping criterion based on the confirmed stagnation pattern is needed to avoid running 50 gens of a stagnated run at 2× compute cost.

4. **[Major]** Add a primary comparison hierarchy to Section 2 or create Section 2a: state which run is the primary test for the experiment-level verdict and which comparisons are secondary. The decision tree in Section 12 is insufficient — it lists success scenarios but not a pre-registered priority ordering.

5. **[Major]** Specify expected gen-0 val F1 and val EM ranges for `static_f1_600` in the pre-launch checklist. Add: "Expected gen-0 val F1 ≈ 68–72% (based on static_f1 gen-0 val F1 = 70.27%); expected gen-0 val EM ≈ 59–61% (based on seed test EM = 60.0%). Halt if outside these ranges." This is a mandatory gate before Run C proceeds past gen 0.

6. **[Major — conditional on Concern 1 fix]** After fixing stage_timeout wiring, recalculate and pre-register dag_timeout for Runs B, C, D. The design's dag_timeout=7200 is likely insufficient once stage_timeout=6000 is actually effective. Compute: dag_timeout ≥ stage_timeout + expected_mutation_llm_time + headroom. Pre-register the result.

---

## Verdict

**[x] NEEDS REVISION**

There is one Critical concern and five Major concerns. The Critical concern — `stage_timeout=6000` is silently inert under `pipeline=hotpotqa_asi` — will cause Runs B, C, and D to replicate Run Q's 96.3% invalidity rate if not resolved before launch. The design's stated rationale for 600-sample runs ("safe per Amendment 2 lesson") is based on a fix that has not actually been implemented in the code. This is not a presentation issue; it is the same infrastructure failure that invalidated the prior run.

The Major concerns are individually addressable: the NLP prompt EM/F1 conflict requires a one-line change to system.txt (or explicit confound acknowledgment); the stagnation-based stopping criterion requires adding one pre-registration rule; the primary comparison hierarchy requires one paragraph in Section 2; the static_f1_600 expected value range requires two bullet points in the pre-launch checklist; the dag_timeout recalculation requires arithmetic and a pre-registered value.

I respect the scientific motivation of this experiment. The four-run design correctly targets the most plausible mechanisms for exceeding GEPA. The gate structure, confound acknowledgments, and statistical language are generally well-calibrated for an n=1 screening study. The design merits approval after these structural repairs — but it cannot launch with the stage_timeout bug unresolved.

*"The science demands nothing less."*

---

## Re-Review (Round 2)

**Date**: 2026-03-07
**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary agent)
**Input**: `experiments/hotpotqa/push/01_design.md` (revised)
**Supporting reads**: `gigaevo/entrypoint/default_pipelines.py`, `problems/chains/hotpotqa/static_a/pipeline.py`, `config/pipeline/hotpotqa_asi.yaml`, `gigaevo/entrypoint/constants.py`, `gigaevo/prompts/hotpotqa/mutation/system.txt`, `config/algorithm/_base.yaml`

---

### Concern-by-Concern Resolution Status

---

**Concern 1 (Critical): `stage_timeout` Hydra override silently inert under `pipeline=hotpotqa_asi`**

STATUS: RESOLVED

The fix is mechanically complete and traceable through three code layers.

First, `config/pipeline/hotpotqa_asi.yaml` now passes `stage_timeout: ${stage_timeout}` as an explicit argument to the `pipeline_builder` block:

```yaml
pipeline_builder:
  _target_: problems.chains.hotpotqa.static_a.pipeline.ASIPipelineBuilder
  ctx: ${evolution_context}
  stage_timeout: ${stage_timeout}
  dag_timeout: ${dag_timeout}
```

Second, `problems/chains/hotpotqa/static_a/pipeline.py` now accepts `stage_timeout` in its constructor and passes it to the parent:

```python
def __init__(self, ctx, *, dag_timeout=3600.0, stage_timeout=DEFAULT_SIMPLE_STAGE_TIMEOUT):
    super().__init__(ctx, dag_timeout=dag_timeout, stage_timeout=stage_timeout)
```

Third, `gigaevo/entrypoint/default_pipelines.py` `DefaultPipelineBuilder.__init__` now accepts `stage_timeout` as a parameter (lines 143–152), stores it as `self._stage_timeout`, and passes it explicitly to `CallValidatorFunction` inside `_contribute_default_nodes` (line 195). The constant `DEFAULT_SIMPLE_STAGE_TIMEOUT = 2400` in `constants.py` is no longer operative for runs using `pipeline=hotpotqa_asi` with an explicit `stage_timeout` override.

The pre-launch checklist (Section 6, item 4) now includes the correct verification step: inspect exec_runner logs at gen 0 to confirm `CallValidatorFunction` is not timing out at 2400s. The `--cfg job` output is correctly noted as insufficient. The fix is complete, correctly implemented, and the verification path is pre-registered.

---

**Concern 2 (Major): NLP mutation prompt system.txt hardcodes "exact match accuracy" in ROLE section**

STATUS: RESOLVED

`gigaevo/prompts/hotpotqa/mutation/system.txt` line 4 now reads:

> "You operate within an evolutionary framework where prompt-chain programs are iteratively mutated and evaluated on multi-hop question answering."

The phrase "exact match accuracy" has been removed. The framing is now metric-agnostic and does not conflict with F1-objective framing injected via `task_description` for Runs A and C. The mutation LLM's ROLE section no longer contradicts the OBJECTIVE section for F1 runs. Risk 4 in Section 12 remains documented but is now precautionary rather than describing a known flaw.

---

**Concern 3 (Major): 600-sample runs at 50 generations unjustified given confirmed stagnation by birth-gen 6**

STATUS: RESOLVED

Section 5 (Controlled Variables) now explicitly pre-registers:

> "`max_generations` | 50 for Run A; **25 for Runs B, C, D** | 600-sample runs stagnate by birth-gen 6 (confirmed across all prior runs); 25 gens provides >= 4x the stagnation window at half the compute cost."

The Run Design Table (Section 6) confirms `max_gen=25` for Runs B, C, D and `max_gen=50` for Run A. Section 10 now includes a pre-registered stagnation-based early-completion criterion for 600-sample runs (no frontier improvement for >= 10 consecutive generations). The wall-time estimate in Section 11 reflects the 25-gen cap (~25h per 600-sample run). This is a clean resolution — the 25-gen cap is now a pre-registered design parameter, not an ad-hoc deviation.

---

**Concern 4 (Major): No pre-registered primary comparison hierarchy for experiment-level verdict**

STATUS: RESOLVED

Section 2 now contains an explicit "Primary comparison hierarchy" subsection (after the four per-run hypotheses and the cross-run composite). It designates Run C (F1 x default x 600) as the primary test for the experiment-level verdict with the following pre-registration:

> "Run C (F1 x default x 600) is the primary test for the experiment-level verdict."
> "Runs A, B, D are secondary."

The subsection also specifies what happens when Run C is SUGGESTIVE and Run A is POSITIVE: the experiment-level verdict remains SUGGESTIVE pending N >= 3 replication of A. This directly addresses the post-hoc emphasis risk I identified. The hierarchy is unambiguous, pre-registered, and consistent with the decision tree in the Appendix.

---

**Concern 5 (Major): `static_f1_600` unverified at design time — missing expected gen-0 value ranges**

STATUS: RESOLVED

Section 12 Risk 1 now pre-registers explicit expected ranges:

> "Expected gen-0 val F1 ~= 68-72% (based on static_f1 gen-0 val F1 = 70.27%; 600-sample mean is the same distribution, lower variance). Halt and diagnose if gen-0 val F1 < 65% or > 75%."
> "Expected gen-0 val EM ~= 59-61% (based on seed program ddce37b4 test EM = 60.0%). Halt and diagnose if gen-0 val EM < 57% or > 63%."

Section 6 pre-launch item 2 references these ranges as a mandatory halt criterion before Run C proceeds past gen 0. The confound table (Section 9) continues to document `static_f1_600` as a new, untested problem directory requiring dry-run verification. All three components of the required fix (expected gen-0 F1 range, expected gen-0 EM range, halt criterion) are present.

---

**Concern 6 (Major): `dag_timeout=7200` insufficient for 600-sample runs once `stage_timeout=6000` is correctly wired**

STATUS: RESOLVED

The Run Design Table (Section 6) now shows `dag_timeout=9000` for Runs B, C, and D. Section 5 (Controlled Variables) pre-registers the calculation:

> "6000 (validator max) + ~1500 (InsightsStage + LineageStage + MutationContextStage under load) + 1500 headroom = 9000s."

Run A retains `dag_timeout=7200`, which remains adequate (300-sample eval max ~244s, well within the 7200 - 1500 headroom). The 9000s value for 600-sample runs provides a 1500s buffer above the expected stage sum of ~7500s. This is the arithmetic I required.

---

**Concern 7 (Minor): Run F terminology inconsistency — "F1-only" baseline vs. compound treatment**

STATUS: RESOLVED (adequate)

The design consistently acknowledges Run F's limitations in Section 9 (confound table): "Run F as reference has N=1 and 52.4% invalidity... Use Run F as reference for relative comparisons but note the uncertainty." The H₀(A) threshold inconsistency I flagged (61.67% in Section 2 vs. 62.3% POSITIVE threshold in Section 8) is functionally handled by the explicit SUGGESTIVE band [61.7%, 62.3%) in Section 8, which covers the intermediate range. The Section 8 Run A test labels SUGGESTIVE as `test EM(A) in [61.7%, 62.3%)`, providing a clean three-way classification. The minor threshold inconsistency between H₀(A) and Section 8 POSITIVE is residual but not operationally ambiguous — any result in [61.67%, 62.3%) falls in the SUGGESTIVE band and is unambiguously classified.

---

**Concern 8 (Minor): SUGGESTIVE band in Gate C supplemental adds gap condition not in H1(C)**

STATUS: PARTIALLY RESOLVED

The Section 8 Gate C supplemental for Run C defines SUGGESTIVE as:

> "test EM(C) in [61.7%, 62.3%) with gap_EM(C) < 1.5pp"

H1(C) in Section 2 states only: "Fixed-600 F1 achieves test EM >= 62.3% (GEPA)." It does not explicitly include the gap condition as part of the SUGGESTIVE criterion. The gap condition in Section 8 adds specificity not present in Section 2. This is a precision gap, not a validity problem — the gap condition is a sensible secondary qualifier for a SUGGESTIVE result, and it is pre-registered in Section 8. However, strict cross-check fails: Section 2 H1(C) and Section 8 Gate C supplemental are not verbatim consistent. The researcher should note in Phase 3 that SUGGESTIVE for Run C requires both conditions.

This residual inconsistency is acceptable for a pre-registration document of this complexity. It does not create interpretive ambiguity at Phase 5 because both conditions appear in Section 8.

---

**Concern 9 (Minor): Two `prompts_dir` entries verification check insufficient for Run D**

STATUS: RESOLVED

Section 6 pre-launch item 3 now explicitly states:

> "For Runs A and D: `python run.py [overrides] --cfg job` must show **two distinct** `prompts_dir` entries in the output — one under `evolution_context` and one under `mutation_operator`. A single entry means the bug has re-appeared. Do not launch."

Section 9 confounds table (NLP prompts silent failure row) repeats the same requirement with identical language. The verification is now correctly scoped to both Runs A and D, and the two-entry requirement is explicit. Code review confirms `config/pipeline/hotpotqa_asi.yaml` has `prompts_dir: ${prompts.dir}` under `evolution_context`, and `config/algorithm/_base.yaml` has `prompts_dir: ${prompts.dir}` under `mutation_operator`. Both wiring points are present.

---

### New Concerns Found in Revision

No new critical or major concerns were introduced by the revision. One observation of minor relevance:

**Observation (Documentation-only)**: The compute budget table (Section 11) wall-time estimate for Run A states "~25h (50 gens x ~244s/eval / 4 workers x overhead ~= 24.6h; cf. Run F: 24.62h)." The arithmetic in the parenthetical (50 x 244 / 4 = 3050s = ~0.85h, not 24.6h) is internally inconsistent — the actual calculation must fold in the two-phase sequential structure and mutation LLM overhead, which the parenthetical omits. The conclusion (25h) is likely correct by reference to Run F's empirical 24.62h. This is a documentation clarity issue, not a design error, and does not affect any pre-registered decision gate.

---

### Final Verdict

**[x] APPROVED**

All six major/critical concerns from Round 1 are resolved. The three minor concerns are resolved or residually acceptable (Concern 8's partial resolution does not create interpretive ambiguity at Phase 5).

The critical fix — stage_timeout wiring — is mechanically verified through three code layers. The wiring is clean: Hydra `${stage_timeout}` flows through `hotpotqa_asi.yaml` → `ASIPipelineBuilder.__init__` → `DefaultPipelineBuilder.__init__` → `self._stage_timeout` → `CallValidatorFunction(timeout=stage_timeout)`. The hardcoded `DEFAULT_SIMPLE_STAGE_TIMEOUT = 2400` constant is no longer operative for runs with an explicit override under `pipeline=hotpotqa_asi`. Runs B, C, and D will not replicate Run Q's failure mode.

The design is now a well-structured n=1 screening study with pre-registered hypotheses, a clear primary comparison hierarchy, a stagnation-aware 25-generation cap for 600-sample runs, correct dag_timeout arithmetic, metric-agnostic NLP prompt framing, and explicit pre-launch verification gates for all known failure modes. The confound acknowledgments are appropriately calibrated for an experiment that is deliberately exploratory rather than statistically powered.

Phase 3 may proceed. Commit `03_plan.md` before any code changes. The static_f1_600 unit test and dry-run gen-0 verification are non-negotiable blocking preconditions for Run C.

*"The science demands nothing less."*
