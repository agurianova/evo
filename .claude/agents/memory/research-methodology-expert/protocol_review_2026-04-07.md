# Protocol Review — GigaEvo Experiment Lifecycle Skills
**Reviewer**: Prof. Hiroshi Nakamura  
**Date**: 2026-04-07  
**Scope**: Seven experiment lifecycle skills (`experiment-design`, `experiment-implement`, `experiment-launch`, `experiment-checkpoint`, `experiment-closeout`, `experiment-diagnose`, `experiment-restart`) plus associated templates (`01_design.md`, `02_review.md`, `03_plan.md`, `05_results.md`).  
**Protocol version**: as committed on branch `exp/adversarial-heilbron-prover`.

---

## Executive Summary

This is an unusually mature protocol for an academic ML lab. The lifecycle is fully codified, the state machine is enforced programmatically, and the explicit treatment-verification loop (treatment-verifier agent + runtime smoke-test checks + diagnose.py Check 13) is the most rigorous instrument of this kind I have seen in any automated ML research protocol. Several genuine weaknesses exist, primarily around statistical power and post-hoc analysis controls, but they do not render the protocol unsound — they render it vulnerable to specific classes of self-deception that the researchers should address before results are submitted for peer review.

---

## Strengths

**S1. Pre-registration is structurally enforced, not aspirational.**  
The state machine (`preregistered → implemented → running → complete`) prevents code from being written before a design exists. The `check_phase_order.sh` gate is a hard blocker. The preregistration commit hash is captured in `03_plan.md`. This is better practice than most ML labs.

**S2. Treatment verification is two-tiered and iterative.**  
The `treatment-verifier` agent traces code paths for silent fallback modes before the smoke test. Smoke-test step (f) then verifies `treatment_checks` at runtime using Redis key patterns and log patterns. `diagnose.py` Check 12 and Check 13 repeat this verification at every checkpoint. This layered approach would catch the majority of "treatment was silently disabled" bugs — a category that has invalidated entire experiment programs elsewhere.

**S3. Partial blinding is procedurally enforced at the critical juncture.**  
The `checkpoint-analyst` agent is invoked with run metrics but without condition labels, and is explicitly labelled advisory. Conclusions are deferred to final analysis. This is meaningful partial blinding for the mid-run decision point.

**S4. Deviation documentation is mandatory and structurally auditable.**  
Amendments must be logged in `03_plan.md`. `05_results.md` has a mandatory "Deviations from Pre-Registration" section, and the closeout skill checks that this section is not empty or placeholder-filled. The git commit history provides an independent audit trail (squash merges are explicitly prohibited — good).

**S5. Reproducibility artifacts are captured at launch.**  
`environment_freeze.txt` (pip freeze), `server_models_at_launch.txt` (model identity from the `/models` endpoint), and `cfg_run_*.txt` (Hydra-resolved config dumps) are committed before runs begin. This is sufficient to reconstruct the computational environment for most purposes.

**S6. Infrastructure vs. hypothesis-relevant issue classification is explicit.**  
The diagnose skill's Step 6 decision matrix — "one treatment arm performing worse than control: THIS IS YOUR DATA, NOT A BUG" — directly guards against the most common form of mid-experiment p-hacking. This is exactly right, and its presence as an explicit protocol step is commendable.

**S7. The adversarial review gate is mandatory and iterative.**  
The `reviewer-2-adversary` (Volkov) enforces N≥2 per cell and single-IV-per-comparison as hard rules. The loop in `experiment-design` Step 4 continues until APPROVED. The record lives in `02_review.md` and is checked by `check_experiment_complete.sh`.

**S8. Human approval is gated at critical junctures.**  
Researcher confirmation is required before launch (experiment-launch Step 6), before merge (`05_results.md` human approval gate R8), and before restart (experiment-restart Step 2). These are appropriate points for human judgment.

---

## Concerns

### Critical

**C1. No pre-specified stopping rule or early-termination criterion in the state machine.**  
`01_design.md` template section 10 ("Stop Criteria: Early termination") exists but is free-text with no enforcement. The `03_plan.md` template has "Early termination rule: ___" which is also free-text and not validated. There is no check in `preflight_check.py` or `check_phase_order.sh` that this field is non-empty and non-placeholder. In practice this means an experiment can be stopped early based on observed results without any pre-specified criterion. This creates an undisclosed optional stopping problem: a positive result at gen 30/50 can trigger early closeout; a negative result at gen 30/50 is allowed to continue. This is structurally equivalent to p-hacking.

**Recommendation**: Add a preflight check that `01_design.md` section 10 is non-empty and contains no placeholder strings. Require that early-termination criteria be stated quantitatively (e.g., "stop if best val fitness < 45% at gen 20"). The `check_experiment_complete.sh` should verify that if actual `max_generations` achieved differs from pre-registered `max_generations`, an amendment entry exists.

**C2. Statistical power analysis is requested but not verified.**  
Section 7 of `01_design.md` ("Sample Size Justification") is present but free-text. The adversarial reviewer (Volkov) checks N≥2 per cell but does not check whether N=2 is sufficient to detect the pre-specified effect size at the pre-specified α. From the MEMORY.md experiment history, virtually all experiments run with N=2–4 replications. For the effect sizes observed (e.g., hover/memory: +0.61pp val, p=0.31; hover/map-elites-topology: NULL), the runs appear systematically underpowered to detect small but scientifically meaningful effects. A null result with N=2 and σ≈0.63pp (inter-run SD) has essentially no power to distinguish "no effect" from "effect of 1pp."

**Recommendation**: Require that the sample size justification include a power calculation. For continuous metrics, this requires an estimate of σ (available from prior experiments — the MEMORY.md baseline SD is documented), a minimum detectable effect, and a power target (conventionally 0.80). If N=2 cannot achieve 0.80 power at the pre-specified MDE, either increase N or revise the MDE. This is the single largest methodological gap in the current protocol.

---

### Major

**M1. The checkpoint-analyst's "partial blinding" is insufficiently specified.**  
The skill says the analyst receives data "without condition labels." However, in the GigaEvo context, the condition is often structurally identifiable from the run label (e.g., "C" for chain vs. "P" for prompt), Redis prefix (which encodes `problem.name`), or fitness level. True blinding would require an independent relabelling step. The current "advisory and never decides" qualifier reduces but does not eliminate the risk of the analyst's output influencing mid-run decisions in a direction consistent with the researcher's hypothesis.

**Recommendation**: Either (a) accept that this is weakly blinded and say so explicitly in the protocol documentation and any eventual paper, or (b) implement a genuine relabelling step where condition identity is masked from the analyst agent by an independent intermediary (a simple script that maps labels to anonymous identifiers before passing to the analyst).

**M2. The statistical test is pre-specified in the template but not enforced.**  
`01_design.md` section 8 ("Statistical Test: Test / α / How computed") and `05_results.md` section 2 require a specific statistical test. However, there is no mechanism that prevents `05_results.md` from using a *different* test at analysis time (e.g., switching from a two-sample t-test to a Wilcoxon after seeing the data distribution). The `ml-research-methodologist` agent produces `05_results.md` and could legitimately choose a "better" test post-hoc.

**Recommendation**: Capture the exact statistical test command (including test name, tails, α, and software function call) in `03_plan.md` at pre-registration. Add a check in the closeout skill that `05_results.md` section 2 names the same test as `03_plan.md`. Deviations from the pre-specified test require an amendment entry.

**M3. Mid-run test evaluation has a one-directional trigger bias.**  
`experiment-checkpoint` Step 6 runs the test evaluation exactly once, when any C-run reaches ≥50% of `max_generations`. If results at 50% look negative, the researcher may decide to stop early (see C1) or proceed to final evaluation with no further test eval. If results look positive, the second test eval at closeout provides confirmation. This creates an asymmetric decision environment: positive interim results get a second confirmatory look; negative results may not. The protocol does not address what to do if interim and final test evals diverge.

**Recommendation**: Pre-specify in `03_plan.md` how interim test eval results will be used. Options: (a) treat it as a pure monitoring signal with no stopping power (write this explicitly), or (b) implement a formal group-sequential design with alpha spending. At minimum, add a field to `03_plan.md` ("Interim analysis decision rule: ___") that is checked for completeness before launch.

**M4. The `experiment-restart` skill destroys data without archiving by default.**  
The restart skill explicitly states: "This skill does NOT archive before flushing. If you need to preserve partial results, run `tools/experiment/archive_run.sh` first." This is a data-loss footgun. A partial-results archive is scientifically relevant: if a run was restarted because of an infrastructure failure (which the protocol correctly categorizes as fixable), the partial data before the restart is evidence of whether the fix changed behavior. Discarding it makes post-hoc "the restart didn't affect results" claims unverifiable.

**Recommendation**: Make archiving mandatory in the restart skill. Add a step before Step 3 ("Kill processes") that runs `archive_run.sh` for each run that has data (i.e., where `engine:total_generations > 0`). This is a small addition with large audit-trail value.

**M5. The `05_results.md` template requests effect size (section 3) but provides no formatting constraint.**  
The template says "Effect Size" with no required format. Effect size without a confidence interval is not a scientific claim — it is a point estimate that may or may not be meaningful. From the experiment history in MEMORY.md, some results are reported as "+0.61pp val" without confidence intervals.

**Recommendation**: Require effect size to be reported as point estimate ± confidence interval (e.g., "+0.61 ± 0.42 pp, 95% CI by bootstrap"). The `ml-research-methodologist` agent should be instructed to compute bootstrap confidence intervals when N is small. Add a check in `check_experiment_complete.sh` that section 3 of `05_results.md` contains a confidence interval notation (regex: `CI` or `±`).

---

### Minor

**m1. Seeds are acknowledged as non-reproducible but not systematically recorded.**  
`03_plan.md` has a "Global seed" field noted as "fill in or write N/A" with an explanatory note that LLM sampling is non-deterministic. The "N/A" escape hatch is appropriate for this system, but the note should also record the LLM temperature and top-p values used (which are controllable, even if not fully reproducible), because these affect the distribution of outcomes. They are present in the Hydra config dump but not surfaced in the pre-registration document.

**m2. Dataset checksums are in `03_plan.md` but not verified at launch.**  
`03_plan.md` template includes a "Dataset Checksums" section with sha256 hashes. There is no step in `preflight_check.py` or `experiment-launch` that recomputes these hashes and compares them to the pre-registered values. If the dataset changes between pre-registration and launch (e.g., dataset preprocessing script was updated), the experiment silently uses different data.

**Recommendation**: Add a `preflight_check.py` check that recomputes sha256 of the validation/test data files and compares to values in `03_plan.md`. If the field is "N/A" or empty, log a warning (not a hard failure, to accommodate prompt-evolution runs without fixed data files).

**m3. `04_issues_log.md` is created on demand, not guaranteed to exist.**  
The issues log is created from template if it doesn't exist ("Skip this step if the checkpoint was entirely healthy"). In practice, a perfectly healthy run will never have an issues log. This is fine, but it means that "no 04_issues_log.md" is ambiguous — it could mean "healthy run" or "issues existed but were not logged." The `check_experiment_complete.sh` should distinguish between these cases.

**m4. The anomaly detector cron runs every 2 hours for up to 7 days regardless of experiment pace.**  
For slow experiments (e.g., 1 generation per 8 hours), the anomaly detector fires ~14 times before the first meaningful data exists. This wastes context and generates noise. The trigger condition should be generation-relative, not time-relative.

**m5. No protocol-level requirement for a minimum wait before closeout after max_gen.**  
The closeout gate checks that runs are at `max_generations` but does not require waiting for the test evaluation script to finish before archiving. If the test eval runs asynchronously and the researcher calls closeout immediately after `max_gen` is reached, the Redis data may be flushed before test eval completes.

**Recommendation**: Add a gate in `experiment-closeout` Step 0 that verifies `run_test_eval.sh` has completed (e.g., that `test_evals/results.json` exists and is newer than the latest checkpoint). This is belt-and-suspenders but worth having since data loss is permanent.

---

## Recommendations (Priority Order)

1. **(Critical)** Add preflight and pre-merge validation of early-termination criterion completeness. Require quantitative stopping rules in `01_design.md` section 10.

2. **(Critical)** Require a power calculation in `01_design.md` section 7. Block Volkov's APPROVED verdict if sample size justification does not include a σ estimate, MDE, and resulting power. For N=2 designs, require explicit acknowledgement that the study is exploratory, not confirmatory.

3. **(Major)** Pre-specify the exact statistical test in `03_plan.md` (function call level) and verify the same test is used in `05_results.md`.

4. **(Major)** Make archiving mandatory in `experiment-restart` before any flush. Add Step 2b: "Archive all runs that have >0 generations of data before flushing."

5. **(Major)** Add pre-specified interim analysis decision rule to `03_plan.md` to resolve the asymmetric test eval trigger bias.

6. **(Major)** Require confidence intervals in `05_results.md` effect size section. Add regex check to `check_experiment_complete.sh`.

7. **(Major)** Document partial blinding limitation explicitly, or implement genuine relabelling intermediary for checkpoint-analyst.

8. **(Minor)** Add dataset checksum verification to `preflight_check.py`.

9. **(Minor)** Record LLM temperature and nucleus sampling parameters in `03_plan.md` alongside the "Global seed: N/A" entry.

10. **(Minor)** Change anomaly detector cron trigger to generation-relative (e.g., fire every 5 generations based on Redis gen count poll) rather than every 2 hours.

---

## Overall Assessment

**PROCEED WITH CONDITIONS**

The GigaEvo experiment protocol is substantially stronger than the median academic ML lab's practice. Pre-registration is structurally enforced, treatment verification is layered and runtime-checked, deviation documentation is mandatory, and the infrastructure/hypothesis classification in the diagnose skill directly guards against mid-experiment p-hacking. These are genuine achievements.

The protocol fails at the statistical layer in two ways that matter for peer review: (1) stopping rules are not enforced and create optional stopping exposure, and (2) sample sizes are systematically underpowered for the effect sizes the lab is trying to detect. The null results in the experiment history (hover/memory p=0.31, hover/map-elites-topology NULL) may represent true null effects or they may represent insufficient power — the current protocol cannot distinguish between these explanations, and neither can a reviewer.

**Before submitting any result from this protocol for peer review, Concerns C1 and C2 must be resolved.** Concerns M1–M5 should be resolved; they do not individually threaten validity but collectively weaken the chain of evidence.

The researchers have built infrastructure of which they should be proud. Now they need to fill the statistical rigor gap, or explicitly reframe their experiments as exploratory pilot studies rather than confirmatory tests.

*"The protocol is the experiment. Get it right before you touch the data."*

— Prof. H. Nakamura
