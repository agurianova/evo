# Phase 2: Adversarial Review -- hover/dynamic-topology

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Date**: 2026-03-23
**Design reviewed**: `experiments/hover/dynamic-topology/01_design.md`

---

## Summary of Design

This experiment tests whether allowing evolution to freely modify chain topology (step count, step types, dependencies) produces higher test retrieval coverage than evolving within the fixed 7-step static topology, when both conditions use soft fitness. Six runs total: n=3 control (static_soft) and n=3 treatment (full chain), cold start, pipeline=standard, gen 25, with a contemporaneous control cell that also replicates Cell C from PR #92.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|---------------|
| 1 | **n_steps and n_tool_steps metrics have `include_in_prompts: true` and `higher_is_better: false` in the treatment's metrics.yaml -- these metrics are absent from the control's metrics.yaml. This is a hidden IV.** The mutation LLM in treatment runs receives additional metrics feedback ("n_steps: 7, n_tool_steps: 3") in its mutation prompt that control runs do not receive. Worse, `higher_is_better: false` creates implicit selection pressure toward fewer steps, potentially biasing evolution toward step-reduction rather than step-expansion. This is not just an observational difference -- it actively changes the mutation signal the LLM uses to generate offspring. | **Major** | Either (a) set `include_in_prompts: false` for n_steps and n_tool_steps in the treatment metrics.yaml, making them purely observational, OR (b) add equivalent dummy metrics to the control metrics.yaml so both conditions receive identical prompt structure. Option (a) is cleaner and eliminates the confound entirely. If the researcher chooses (b), document the rationale explicitly. Either way, the current configuration introduces an uncontrolled variable that co-varies with the IV and directly affects the mutation process. |
| 2 | **task_description.txt contradicts FULL_CHAIN_CONFIG on require_final_llm.** Line 141 of `full/task_description.txt` lists "Last step is not 'llm' type" as a FAILURE MODE, but `FULL_CHAIN_CONFIG` sets `require_final_llm: False`. The mutation LLM is told that ending with a non-LLM step is an error, while the validator will accept it. This creates a misleading signal that constrains the search space in an undocumented way -- the LLM will avoid tool-final chains (e.g., a chain ending in a deep retrieval) even though they are structurally valid. | **Major** | Fix the task_description.txt to accurately reflect the validation rules. If `require_final_llm=False`, remove the "Last step is not 'llm' type" failure mode from line 141. If you actually want to require a final LLM step, change `require_final_llm` to `True` in FULL_CHAIN_CONFIG and document why. Inconsistency between the prompt the LLM reads and the validator it encounters is a design defect. |
| 3 | **MDE calculation omits the power term (t_beta).** The formula `MDE = t(alpha, df) * SD * sqrt(1/n1 + 1/n2)` uses only the critical value for alpha. The correct formula for 80% power is `MDE = (t_alpha + t_beta) * SD * sqrt(...)` where `t_beta = t(0.80, df) ~ 0.941` at df=4. Corrected: `MDE = (2.132 + 0.941) * 1.5 * 0.816 = 3.76pp` at conservative SD, and `(2.132 + 0.941) * 1.0 * 0.816 = 2.51pp` at optimistic SD. The experiment is materially less powered than stated. At conservative SD, even the STRONG POSITIVE threshold (+4.0pp) is near the MDE, not "well-powered." | **Minor** | Correct the MDE formula and update the power analysis conclusion. The experiment remains worthwhile -- but the language must accurately characterize what can and cannot be detected. Replace "Effects in the STRONG POSITIVE range (>= +4.0pp) are well-powered" with language reflecting that even +4.0pp effects have marginal power at conservative SD. State that the experiment is exploratory-powered and that the effect-size table is the primary decision criterion. This pattern has now appeared in three consecutive design documents; please propagate the corrected formula to your template. |
| 4 | **Wave execution confound is understated.** The design states "Both waves have a mix of control and treatment runs (wave 1: D1-D3 control + D4 treatment; wave 2: D5-D6 treatment)." This means wave 1 has 3 control + 1 treatment, and wave 2 has 0 control + 2 treatment. That is not "a mix" in any balanced sense. Two-thirds of the treatment runs are in wave 2; zero control runs are in wave 2. If server conditions change between waves (even subtly -- thermal throttling, memory fragmentation, model cache state), this confound is aliased entirely with the treatment. With n=3 per cell, one cannot separate wave effects from treatment effects. | **Minor** | Acknowledge this honestly. Replace "Both waves have a mix of control and treatment runs" with an accurate description of the imbalance. If possible, restructure wave allocation to include at least one control run in wave 2 (e.g., wave 1: D1, D2, D4, D5; wave 2: D3, D6 -- giving each wave a mix of both conditions). If the wave structure is fixed by infrastructure constraints, add a diagnostic: compare D4 (treatment, wave 1) against D5-D6 (treatment, wave 2) post-hoc to bound within-treatment wave effects. |
| 5 | **D1 and D5 share the same chain endpoint AND mutation endpoint.** D1 uses chain `10.226.17.25:8001` and mutation `10.226.72.211:8777`. D5 uses the identical pair. Similarly, D2 and D6 share both endpoints. This is described as "reuse after completion," but it creates a potential confound: if there is any persistent state on the server (KV cache fragments, connection pool exhaustion, model weight quantization drift), wave-2 runs inherit it from wave-1 runs. Combined with Concern #4, this means treatment runs D5-D6 inherit server state from control runs D1-D2. | **Minor** | Add to the pre-launch checklist: restart vLLM serving processes (or at minimum verify model health) on chain and mutation servers between waves. Document this as a required step, not an optional one. |
| 6 | **"Best-by-val" selection introduces val-test leakage for the primary metric.** Section 4 specifies "Test retrieval coverage at gen 25 (discrete, best-by-val)" as the primary metric. Selecting the best program by val fitness and then evaluating it on the test set introduces optimization target leakage. This is standard practice in this research program and is not unique to this experiment, but it is worth noting that val fitness is a biased estimator of test performance. The 5-repeat test protocol mitigates stochasticity in the test evaluation itself, but does not address the selection bias. | **Minor** | Acknowledge val-test selection bias in Section 9 (Confounds) or Section 4 (DVs). A one-sentence note is sufficient: "Selecting the best program by val fitness introduces upward bias in the test estimate; this bias is present in all conditions and in the Cell C reference, so it does not differentially affect the treatment comparison." |

---

## Hypothesis and Falsifiability

- [x] H0 is clearly stated -- mu_full - mu_static <= 2.0pp
- [x] H1 is falsifiable and directional
- [x] Primary metric is pre-specified and sufficient to test H1
- [x] Success criteria are numeric and unambiguous

**Notes**: The hypothesis structure is well-formed. The superiority threshold of 2.0pp embedded in H0 is a defensible choice given the Cell C reference. The effect-size table (Section 2) is the correct primary decision mechanism for an exploratory-powered experiment. H2 (topology diversity) is clearly secondary and appropriately scoped.

---

## Confound Analysis

- [ ] All controlled variables are genuinely controlled -- **FAIL** (Concern #1: n_steps/n_tool_steps in mutation prompts; Concern #2: task_description.txt inconsistency)
- [x] IV is isolated (no other differences between conditions) -- conditional on resolving Concerns #1 and #2
- [x] Known confounds are mitigated or acknowledged -- the confound table in Section 9 is thorough
- [x] Val/test split is not contaminated

**Unaddressed confounds**:

**Confound #10 (NEW): Mutation prompt content differs between conditions.** The treatment's metrics.yaml includes `n_steps` and `n_tool_steps` with `include_in_prompts: true`, which means the mutation LLM sees these metrics in its fitness feedback. The control's metrics.yaml does not include them. This is a second-order IV that was not named anywhere in the design. Additionally, the `higher_is_better: false` setting on these metrics may bias the mutation LLM toward step reduction, working against the very hypothesis the experiment is trying to test.

**Confound #11 (NEW): task_description.txt FAILURE MODES section includes a constraint (`require_final_llm`) that is explicitly disabled in the code.** The mutation LLM is guided by the task description; if it avoids producing tool-final chains because the task description says that is an error, the search space is artificially constrained in a way that is invisible to the validator and to the researcher analyzing results.

The existing confound analysis (Section 9, items 1-9) is otherwise well-constructed. Confound #7 (adaptive vs. positional scoring) is correctly identified as non-confounding for the discrete primary metric. Confound #8 (mutation LLM topology capability) is the most honest and scientifically important acknowledgment in the document.

---

## Statistical Validity

- [x] Sample size is justified -- n=3 per cell is the pragmatic choice; the power analysis correctly identifies this as exploratory
- [ ] Statistical test is appropriate for the data -- **conditional**: the power analysis arithmetic is wrong (Concern #3)
- [x] Significance threshold is pre-specified (alpha=0.05, one-sided, Test 1 only)
- [x] Multiple comparison correction applied if testing multiple hypotheses -- Tests 2-5 are secondary/exploratory; alpha scoped to Test 1

**Notes**: The Welch's t-test is appropriate for this design. The Satterthwaite df approximation is correct for potentially unequal variances between conditions. The bootstrapped CI as sensitivity check is a good addition. The power analysis arithmetic must be corrected (Concern #3), but the experimental design remains sound -- the effect-size table is the true decision criterion, and the researcher correctly notes that marginal effects "may not reach significance."

---

## Evaluation Protocol

- [x] Metric is computed identically across all conditions -- discrete coverage on 300-sample test set, 5 repeats
- [x] Val set and test set are fixed and identical for all runs
- [x] No metric is cherry-picked post-hoc
- [x] Thinking mode is consistent across all evaluations

**Notes**: I verified both `test.py` files. The control uses `evaluate_retrieval_coverage` (positional scoring at indices 0, 3, 6) and the treatment uses `evaluate_discrete_coverage_adaptive` (scans all tool-step outputs). For 7-step chains, these produce identical results. For non-7-step chains, the adaptive scorer is the only correct scorer. This is well-handled -- the test protocol adapts to the treatment effect rather than imposing a fixed evaluation template that would penalize topology innovation.

The 5-repeat protocol with mean as the per-run estimate is consistent with all prior experiments. The `full/test.py` correctly computes discrete coverage as the primary metric.

---

## Positive Observations

Three aspects of this design merit explicit acknowledgment:

1. **The contemporaneous control cell.** Previous experiments relied on Cell C (n=2) as a historical reference. This design includes a fresh n=3 replication of static_soft as both a replication check and a contemporaneous baseline. Appendix C articulates the rationale clearly. This is a genuine methodological improvement over the prior experiments in this research program.

2. **The mutation LLM ceiling diagnostic (Confound #8).** Pre-committing to monitor n_steps and n_tool_steps across generations, with a specific threshold ([6.5, 7.5] at gen 25) for flagging "LLM mutation ceiling," is exactly the right way to handle the risk that the IV is not actually active. The decision tree in Appendix B correctly routes the NULL + low-diversity result to "add topology hints" rather than "topology does not work."

3. **The task_description.txt is well-crafted** (modulo the require_final_llm contradiction). The TASK HINTS section explicitly describes topologies that the static chain cannot express -- parallel retrieval branches, variable hop counts, fork-join -- giving the mutation LLM concrete examples of what the expanded search space contains. This directly addresses Risk 1 (mutation LLM cannot perform topology mutations).

---

## Required Changes Before Approval

1. **Concern #1 (Major)**: Set `include_in_prompts: false` for `n_steps` and `n_tool_steps` in `problems/chains/hover/full/metrics.yaml`, OR add equivalent metrics to `static_soft/metrics.yaml`. The current configuration introduces an uncontrolled difference in mutation prompt content between conditions. Document whichever choice is made in Section 9 as a new confound entry.

2. **Concern #2 (Major)**: Fix the contradiction between `full/task_description.txt` line 141 ("Last step is not 'llm' type" as failure mode) and `FULL_CHAIN_CONFIG` (`require_final_llm: False`). Remove the misleading failure mode from the task description, OR change `require_final_llm` to `True` and update the design document accordingly.

3. **Concern #3 (Minor)**: Correct the MDE formula to include the power term. Update the power analysis conclusion to accurately characterize the experiment as exploratory-powered.

4. **Concern #4 (Minor)**: Replace the inaccurate claim that "Both waves have a mix of control and treatment runs" with an honest description of the wave-treatment imbalance, and add a within-treatment wave diagnostic to the analysis plan.

---

## Verdict

**[x] APPROVED** -- all 4 required changes addressed (include_in_prompts: false, task_description fixed, MDE corrected, wave balance fixed with n=4)

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**: This is a well-motivated experiment that asks the right question at the right time in the HoVer research program. The contemporaneous control cell, the mutation LLM ceiling diagnostic, and the detailed decision tree in Appendix B all reflect genuine scientific care. The two major concerns are both fixable in minutes -- they are configuration issues, not design flaws. Concern #1 (mutation prompt leakage from `include_in_prompts: true`) is the more dangerous of the two because it introduces a hidden IV that directly affects the mutation process in a direction that may work *against* the hypothesis (step reduction bias via `higher_is_better: false`). Concern #2 (task description contradiction) is a code-documentation mismatch that constrains the search space in an invisible way. Both must be resolved before this design can be approved.

*The science demands nothing less.*
