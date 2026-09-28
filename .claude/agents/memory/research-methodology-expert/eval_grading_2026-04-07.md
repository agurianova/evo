# Skills Evaluation Grading Report
**Evaluator**: Prof. Hiroshi Nakamura, Institute for Scientific Methodology, ETH Zürich
**Date**: 2026-04-07
**Subject**: GigaEvo experiment lifecycle skills — with-skill vs without-skill evaluation (5 pairs)
**Rubric**: 6 dimensions × 1–5 scale, total /30

---

## Grading Rubric Reminder

| Dimension | What earns a 5 |
|---|---|
| **stopping_rule** | Pre-specified, machine-checkable stopping rule (not free-text); surfaced proactively even if not asked |
| **treatment_verification** | Runtime proof the treatment is active — not just code review or config inspection |
| **partial_blinding** | Conclusions explicitly deferred; checkpoint analyst shielded; mid-run steering actively discouraged |
| **deviation_documentation** | All deviations logged with rationale, generation number, and impact classification |
| **reproducibility** | Env, model versions, seeds, dataset checksums committed before runs begin |
| **statistical_rigour** | CIs reported alongside point estimates; pre-specified test used; negative results handled honestly |

---

## Eval 1 — skill: experiment-design

**Prompt**: "design experiment hover/heilbron-prover — test whether adversarial prover improves HoVer accuracy"

### Score Table

| Dimension | With Skill | Without Skill |
|---|---|---|
| stopping_rule | 4 | 3 |
| treatment_verification | 5 | 4 |
| partial_blinding | 4 | 3 |
| deviation_documentation | 3 | 2 |
| reproducibility | 4 | 4 |
| statistical_rigour | 4 | 4 |
| **Total** | **24/30** | **20/30** |

### Key Difference

The with-skill response mandates a Treatment Verification section (§3c) as a **non-optional design doc requirement**, demands observable Redis-key evidence of treatment within gen 1–3, and explicitly blocks launch without this. It also invokes the `reviewer-2-adversary` loop with a structured adversarial checklist covering bootstrap problems, asymmetry risk, and non-stationarity of adversarial fitness. The without-skill response produces a well-structured design doc with all the right sections but the treatment verification block is softer ("treatment_checks in experiment.yaml") and the adversarial review loop is described rather than scaffolded.

### Verdict

**Meaningful improvement** — the skill adds genuine scientific gatekeeping (treatment verification, adversarial review scaffolding, non-stationarity warning). The gap is real, not just verbosity.

**Remaining gap (both)**: Neither response pins a stopping rule that is machine-checkable. Section 10 (Stop Criteria) in the without-skill response is well-written English but nothing in `preflight_check.py` or any gate script will reject a design doc that omits it. The statistical power section in both accepts N=2 as "minimally sufficient" based on a t-test argument that has 1 degree of freedom — this is scientifically weak but neither response forces it through a formal power calculation block.

---

## Eval 2 — skill: experiment-implement

**Prompt**: "implement experiment hover/heilbron-prover"

### Score Table

| Dimension | With Skill | Without Skill |
|---|---|---|
| stopping_rule | 3 | 2 |
| treatment_verification | 5 | 4 |
| partial_blinding | 3 | 3 |
| deviation_documentation | 4 | 3 |
| reproducibility | 4 | 3 |
| statistical_rigour | 3 | 3 |
| **Total** | **22/30** | **18/30** |

### Key Difference

The with-skill response elevates treatment verification from "add treatment_checks to experiment.yaml" (without-skill, Step 6 of a 10-step plan) to **the most critical step** (Step 10, hard gate), with a named `treatment-verifier` agent tracing every code path from Hydra instantiation through the mutation operator, plus a concrete smoke-test verification procedure with pass/fail criteria expressed as shell commands. The without-skill response includes `treatment_checks` but frames them as "verified by preflight_check.py and diagnose.py during monitoring" — runtime verification rather than pre-launch verification. This is the difference between catching silent fallbacks before data collection and detecting them halfway through a 25-generation run.

The with-skill response also maps failure modes explicitly to the checks that would catch them (a 6-row table at Step 10b). This is genuine scientific engineering.

**Reproducibility note**: Neither response requires a complete environment snapshot be committed before first launch. The with-skill response mentions `environment.txt` in the archive step only; dataset checksums appear in the without-skill's pre-reg step but not as a preflight gate.

### Verdict

**Meaningful improvement** — particularly on treatment verification, which is the primary scientific concern for this phase. The gap is not cosmetic.

---

## Eval 3 — skill: experiment-checkpoint

**Prompt**: "checkpoint hover/heilbron-prover — A=67.2% gen 31, B=65.8% gen 29. A is treatment."

### Score Table

| Dimension | With Skill | Without Skill |
|---|---|---|
| stopping_rule | 3 | 2 |
| treatment_verification | 3 | 3 |
| partial_blinding | 5 | 4 |
| deviation_documentation | 3 | 2 |
| reproducibility | 3 | 3 |
| statistical_rigour | 4 | 3 |
| **Total** | **21/30** | **17/30** |

### Key Difference

Both responses correctly refuse to say "the prover appears to be working" — this is the core test. The critical difference is **partial blinding discipline**: the with-skill response invokes the `checkpoint-analyst` agent with the run labels stripped (agent sees "Run A: 67.2%, Run B: 65.8%" without knowing which is treatment), explicitly notes that test-eval results are withheld from the PR comment because "held-out data should not influence mid-run decisions," and documents a 5-row rationale table for every deference decision. The without-skill response has the right instinct but is less systematic: it includes "No conclusions drawn at this stage" as a PR comment footer rather than as an enforced process step, and does not address withholding test-eval numbers from the PR.

The generation count discrepancy (31 vs 29) is flagged by both, but only the with-skill response explicitly states this makes the point estimate uninterpretable for causal attribution and records it in the manifest as a confound.

### Verdict

**Meaningful improvement** — the blinding and test-eval withholding are genuine research hygiene steps that prevent mid-experiment steering. The without-skill response is better than baseline but leaves the door open to subtle influence.

**Remaining gap (both)**: Neither response checks whether the stopping rule pre-specified in `01_design.md` is on track. If section 10 said "stop at gen 50 if invalidity > 40%", the checkpoint should verify that threshold was not silently passed. Both treat stopping rules as passive notes rather than active gates.

---

## Eval 4 — skill: experiment-closeout

**Prompt**: "close hover/heilbron-prover — treatment=68.1% val, control=65.3% val"

### Score Table

| Dimension | With Skill | Without Skill |
|---|---|---|
| stopping_rule | 4 | 3 |
| treatment_verification | 3 | 3 |
| partial_blinding | 4 | 3 |
| deviation_documentation | 5 | 4 |
| reproducibility | 4 | 4 |
| statistical_rigour | 5 | 4 |
| **Total** | **25/30** | **21/30** |

### Key Difference

The with-skill response contains the most important single passage in all ten documents: the explicit instruction that **if 2.8pp is below the pre-registered MES, the result is NULL regardless of p-value**, and that the researcher may not round "approximately 3pp" to claim POSITIVE. It also blocks selection of the statistical test after seeing results ("If the design doc does not specify a test, this is a protocol deviation — I will document it before choosing"). The Elena briefing is 8 numbered non-negotiable requirements, of which the CI requirement is item 2 ("a statement like 'treatment improved by 2.8pp (p=0.03)' is incomplete").

The without-skill response is procedurally correct but does not include this explicit anti-p-hacking instruction. It says "Pre-registered analysis plan" as a section header but does not guard against the post-hoc test selection failure mode. The Deviations section requirement is present in both.

**Critical note on without-skill closeout**: The without-skill response surfaces an important domain-specific concern (adversarial composite fitness vs. actual_fitness — 68.1%/65.3% may be the wrong metric) and notes the max_generations discrepancy deviation. These are genuine research quality contributions. However, the absence of a CI requirement and the absence of explicit MES vs. point-estimate comparison means a result would likely be reported as "+2.8pp, p=X" without the CI or the verdict check.

### Verdict

**Meaningful improvement** — primarily on statistical rigour and anti-p-hacking. The difference between "report CI" and "report CI and compare to MES before declaring POSITIVE" is the difference between a sound and an unsound result.

---

## Eval 5 — skill: experiment-restart

**Prompt**: "restart — found bug in adversarial prover prompt template, single quotes instead of double quotes in JSON output, fixed it now"

### Score Table

| Dimension | With Skill | Without Skill |
|---|---|---|
| stopping_rule | 2 | 1 |
| treatment_verification | 4 | 3 |
| partial_blinding | 3 | 2 |
| deviation_documentation | 5 | 3 |
| reproducibility | 4 | 3 |
| statistical_rigour | 4 | 2 |
| **Total** | **22/30** | **14/30** |

### Key Difference

This is the largest gap (22 vs 14) and the most consequential difference. The with-skill response stops before proceeding and asks three blocking questions: (1) how many generations ran with the broken treatment, (2) were any valid programs produced, (3) is the fix committed. It explicitly classifies the bug as a **treatment fidelity failure** (not a cosmetic issue), warns that any run with valid programs under the broken treatment is a mid-experiment treatment change that requires a `01_design.md` and `04_issues_log.md` entry, and states that the paper must disclose this deviation. The `04_issues_log.md` template entry includes pre-registration impact assessment and a systemic fix recommendation.

The without-skill response executes a clean restart and logs the issue, but does **not** ask how many generations ran, does **not** assess whether any partial data should be archived, and does **not** warn that valid programs produced under the broken treatment are scientifically problematic. It asks "do you want to proceed?" (a safety question) but not "do you have valid data from the broken treatment that affects interpretation?" (a scientific integrity question).

### Verdict

**Large meaningful improvement** — the with-skill response is the only one that treats this as a pre-registration amendment problem rather than a bug-fix-and-restart problem.

---

## Final Summary

### Overall Score Table

| Eval | Skill | With Skill | Without Skill | Delta |
|---|---|---|---|---|
| 1 | experiment-design | 24/30 | 20/30 | +4 |
| 2 | experiment-implement | 22/30 | 18/30 | +4 |
| 3 | experiment-checkpoint | 21/30 | 17/30 | +4 |
| 4 | experiment-closeout | 25/30 | 21/30 | +4 |
| 5 | experiment-restart | 22/30 | 14/30 | +8 |
| **Mean** | | **22.8/30 (76%)** | **18.0/30 (60%)** | **+4.8** |

### Which Skills Show the Largest Quality Improvement?

**experiment-restart** shows the largest improvement (+8 points). The skill converts what would be an operational recovery procedure into a scientific integrity checkpoint. Without the skill, a bug fix is treated as equivalent to a clean launch — the researcher receives no warning that partial data under a broken treatment creates a pre-registration violation and must be disclosed in the results.

**experiment-closeout** (+4) shows the most important improvement per unit gap: the MES-vs-point-estimate check and the CI requirement are where published results actually get made. A 4-point gap here corresponds to a real difference in whether a paper's claim is trustworthy.

### Which Skills Show Little or No Improvement?

All skills show meaningful improvement; none are purely checklist additions. However, **experiment-checkpoint** has the smallest absolute improvement (+4) and the without-skill response is surprisingly capable on the core test (refusing to editorialize about which treatment is working). The skill's improvement over baseline is disciplined blinding procedure and test-eval withholding, which are genuine but narrow contributions.

### Top 3 Concrete Gaps That Remain EVEN WITH the Skills

**1. Stopping rules are not machine-enforced (Critical)**

Section 10 of `01_design.md` exists and is well-written in the with-skill output. But nothing in `preflight_check.py`, `check_phase_order.sh`, or `check_experiment_complete.sh` validates that section 10 is present, non-empty, and machine-parseable. A researcher can write "we'll stop when it looks like stagnation" and the experiment launches. Early termination on positive trends is the most common source of inflated effect sizes in iterative ML experiments. The skill encodes the requirement but does not enforce it as a gate.

**2. Statistical power is accepted at N=2 without formal calculation (Critical)**

The with-skill design response (Eval 1) explicitly calculates that N=2 detects ~3pp at α=0.1, then accepts this as "minimally sufficient." With inter-run SD ≈ 0.63pp on test coverage but higher on val soft fitness, the true power at N=2 for detecting 1.5–2pp effects (the SUGGESTIVE range) is below 0.4. The Volkov review checks N≥2 but not whether N=2 is powered for the pre-registered MES. This gap means experiments will routinely be underpowered and the protocol will produce SUGGESTIVE verdicts that are indistinguishable from NULL.

**3. Confidence intervals are required in the briefing but not enforced in the gate script (Major)**

The with-skill closeout (Eval 4) explicitly requires CIs in the Elena briefing. But `check_experiment_complete.sh` does not validate that `05_results.md` contains a CI notation. If Elena omits it and the researcher approves the results doc, the merge proceeds with a point-estimate-only result. The requirement exists in the procedure but has no terminal gate.

### Overall Verdict

**These skills constitute a substantially better research process than baseline, but not yet a trustworthy research protocol.**

The skills are genuinely effective at two things: (a) structuring human attention on the right questions at each phase, and (b) making treatment verification and deviation documentation feel mandatory rather than optional. The experiment-restart improvement is the clearest demonstration that the skills contain scientific principles rather than just checklist format.

The protocol is not yet trustworthy on three axes that matter for reproducibility: stopping rules can be vague, statistical power is not gated at design-review time, and CIs are required by instruction but not enforced by tooling. A result produced under this protocol could be published but would require careful reader scrutiny of the pre-registration commit to establish whether the analysis was genuinely pre-specified.

The correct analogy: the protocol is a well-trained but unsupervised researcher — it knows what to do but lacks the external enforcement that converts knowing into doing. Gate scripts, not briefings, are what make protocols trustworthy.

*"The protocol is the experiment. Get it right before you touch the data."*

— H. Nakamura

---

## Memory Update Appendix (for MEMORY.md)

**Confirmed improvements since March 2026 audit:**
- Treatment verification now layered and pre-launch (treatment-verifier agent + smoke test + diagnose.py) — material upgrade
- Deviation documentation now systematic with 04_issues_log.md and deviations section in 05_results.md
- Partial blinding at checkpoint-analyst is now present (not present in March)
- Anti-p-hacking MES check appears in closeout skill — new since March

**Open Critical Gaps (2026-04-07, still unaddressed from March or newly confirmed):**
1. Stopping rules in 01_design.md §10: no machine gate, no format validation (Critical)
2. Power calculation: N≥2 accepted without formal power check in Volkov review (Critical)
3. CI enforcement: required in briefing, not in check_experiment_complete.sh regex (Major)
4. Partial blinding is structural only — run labels reveal condition assignment to analyst (Major, newly confirmed)
5. Test-set reuse across 10+ experiments: family-wise error inflation unaddressed (Major, open since March)
