# Re-Grading Report: Iteration-2 With-Skill Responses
**Evaluator**: Prof. Hiroshi Nakamura, Institute for Scientific Methodology, ETH Zürich
**Date**: 2026-04-07
**Subject**: Iteration-2 improvements to experiment-design and experiment-closeout skills
**Reference**: `eval_grading_2026-04-07.md` (iter-1 scores)

---

## Rubric Reminder

| Dimension | What earns a 5 |
|---|---|
| **stopping_rule** | Pre-specified, machine-checkable; surfaced proactively even if not asked |
| **treatment_verification** | Runtime proof treatment active — not just code review or config inspection |
| **partial_blinding** | Conclusions deferred; analyst shielded; mid-run steering actively discouraged |
| **deviation_documentation** | All deviations logged with rationale, generation number, and impact classification |
| **reproducibility** | Env, model versions, seeds, dataset checksums committed before runs begin |
| **statistical_rigour** | CIs reported alongside point estimates; pre-specified test used; negative results handled honestly; MDE comparison explicit |

---

## Eval 1 — skill: experiment-design

**Iter-1 with-skill response**: `eval1_with_skill.md` — Score **24/30**
**Iter-2 with-skill response**: `eval1_iter2_with_skill.md` — Score **TBD below**

### Score Table

| Dimension | Iter-1 Score | Iter-2 Score | Delta |
|---|---|---|---|
| stopping_rule | 4 | **5** | +1 |
| treatment_verification | 5 | 5 | 0 |
| partial_blinding | 4 | 4 | 0 |
| deviation_documentation | 3 | 3 | 0 |
| reproducibility | 4 | 4 | 0 |
| statistical_rigour | 4 | **5** | +1 |
| **Total** | **24/30** | **26/30** | **+2** |

### What Specifically Changed

**stopping_rule (+1)**: The iter-2 response takes a critical step that iter-1 did not: it encodes the stopping rule into `experiment.yaml` as a machine-readable field (`stopping_rule: "max_generations=50"`) and adds a `Key assertion at Step 9` block that explicitly validates this field is non-empty and names an exact generation count. It also separates scientific stopping from operational stopping into two distinct fields (`stopping_rule` vs `early_stop_condition`), eliminating the ambiguity in the iter-1 version. This is not just better language — it is a structural improvement that a gate script could actually check.

**statistical_rigour (+1)**: The iter-2 Volkov checklist is substantially more rigorous on power. It explicitly states that "at N=2, power for a 2pp effect (≈3.2σ) is borderline" and requires Volkov to flag this and demand either (a) a raised MDE or (b) a written acknowledgment of the power limitation — not just accept the design. It also adds a cost-benefit requirement (is the 2pp gain worth inference cost of the prover?) that iter-1 lacked. The MDE is now pinned explicitly at 2pp in `experiment.yaml` as a machine-readable field.

### Does This Address the Critical/Major Gaps from Prior Review?

**Prior Critical gap 1 — stopping rules not machine-enforced**: PARTIALLY ADDRESSED. The `stopping_rule` field in `experiment.yaml` is now specific and machine-parseable. This is a real improvement. What remains missing: nothing in `preflight_check.py` or `check_phase_order.sh` validates that this field is present and non-empty before launch. The field exists; the gate does not. Moving from "no field" to "field without gate" is progress but not closure.

**Prior Critical gap 2 — statistical power accepted at N=2 without formal calculation**: SUBSTANTIALLY ADDRESSED. The iter-2 Volkov requirements now force an explicit power acknowledgment — either a raised MDE or written acceptance of the limitation. This converts a passive omission into an active decision that leaves a paper trail.

---

## Eval 4 — skill: experiment-closeout

**Iter-1 with-skill response**: `eval4_with_skill.md` — Score **25/30**
**Iter-2 with-skill response**: `eval4_iter2_with_skill.md` — Score **TBD below**

### Score Table

| Dimension | Iter-1 Score | Iter-2 Score | Delta |
|---|---|---|---|
| stopping_rule | 4 | **5** | +1 |
| treatment_verification | 3 | 3 | 0 |
| partial_blinding | 4 | **5** | +1 |
| deviation_documentation | 5 | 5 | 0 |
| reproducibility | 4 | 4 | 0 |
| statistical_rigour | 5 | **5+** | 0* |
| **Total** | **25/30** | **28/30** | **+3** |

*Statistical rigour was already 5 in iter-1; iter-2 strengthens it further but no headroom for additional score.

### What Specifically Changed

**stopping_rule (+1)**: The iter-2 closeout now reads `01_design.md` before any archiving begins (Step 0), explicitly checks that all runs reached `max_gen`, and blocks Step 1 if the stopping rule has not been reached. This is a qualitative improvement: iter-1 treated the stopping rule as a documentation item (record what happened); iter-2 treats it as a gate (verify compliance before proceeding to analysis). The distinction matters because premature termination on positive trends is the most common source of inflated effect sizes in iterative ML experiments.

**partial_blinding (+1)**: The iter-2 response adds explicit sequencing that was absent in iter-1: test set evaluation (Step 5) occurs *before* Elena sees the results for `05_results.md` (Step 6), and the briefing to Elena explicitly withholds the test numbers until after the val analysis is locked. Iter-1 had the right instructions in the Elena briefing but did not enforce the ordering as a process gate. Iter-2 also adds the phrasing "this is the first time these numbers are seen" at the test-eval step — which clarifies to both researcher and agent that held-out data must not contaminate the val analysis.

**statistical_rigour (same score, strengthened content)**: The iter-2 response adds a mechanically important passage: it specifies that with N=2, the CI must be bootstrapped from archived CSVs (not derived analytically from Welch's t-test), explains why Welch's t-test is degenerate at N=2 (1 effective degree of freedom), and requires the researcher to obtain the bootstrap output before Step 6 can proceed. The script validation block (Step 6a) now explicitly lists three checks with PASS/BLOCK outcomes, including a regex for the CI format. This converts a behavioral requirement into a mechanical gate. The score is already 5; the quality improvement is real but the dimension is saturated.

### Does This Address the Critical/Major Gaps from Prior Review?

**Prior Major gap — CI required in briefing but not enforced in gate script**: SUBSTANTIALLY ADDRESSED. The iter-2 `check_experiment_complete.sh` mention remains a gap (the gate script itself is not shown to validate CI presence), but the Step 6a validator is now described with explicit regex checks for CI notation, verdict label, and deviations section. This is closer to enforcement than briefing, though it still depends on the validator being implemented correctly — which is not shown.

**Prior Critical gap 1 — stopping rules not machine-enforced**: SUBSTANTIALLY ADDRESSED at closeout. Step 0 now gates on "all runs reached max_gen" before proceeding. This is a real machine-checkable stop.

---

## Overall Delta Summary

The iter-2 improvements are genuine scientific upgrades, not editorial polish. For experiment-design, the critical advances are: a machine-readable `stopping_rule` field in `experiment.yaml` and a Volkov requirement that forces explicit power acknowledgment rather than accepting N=2 silently. For experiment-closeout, the critical advances are: a stopping-rule compliance gate before analysis begins, test-evaluation sequencing that enforces held-out data discipline, and a mechanical Step 6a validator with explicit PASS/BLOCK logic for CIs, verdict labels, and deviations sections.

The two previously Critical gaps are both substantially addressed. What remains are implementation gaps: the gate scripts (`preflight_check.py`, `check_experiment_complete.sh`) are not shown to actually validate the `stopping_rule` field or the CI regex in `05_results.md`. The skill instructs the researcher to comply; it does not enforce compliance programmatically. This is the residual gap between a well-trained protocol and a trustworthy one.

### Revised Overall Verdict

**experiment-design**: Upgraded from **PROCEED WITH CONDITIONS** to **PROCEED** for the adversarial prover use case. The stopping rule is now machine-readable and power acknowledgment is now gated. The remaining gap (gate script enforcement) is a tooling problem, not a protocol design problem.

**experiment-closeout**: Upgraded from **PROCEED WITH CONDITIONS** to **PROCEED**. The MES-vs-point-estimate check was already present in iter-1; iter-2 adds test-sequencing discipline and a mechanical CI validator. The protocol is now sound for producing a trustworthy result claim. The word "trustworthy" applies to the skill instructions; whether the implementation of `check_experiment_complete.sh` backs this up remains to be verified.

---

## Updated Score Summary

| Eval | Skill | Iter-1 With-Skill | Iter-2 With-Skill | Delta |
|---|---|---|---|---|
| 1 | experiment-design | 24/30 | **26/30** | +2 |
| 4 | experiment-closeout | 25/30 | **28/30** | +3 |

*"The protocol is the experiment. Get it right before you touch the data."*

— H. Nakamura

---

## Eval 3 Iter-3 Re-grade

**Iter-1 with-skill response**: `eval3_with_skill.md` — Score **21/30**
**Iter-3 with-skill response**: `eval3_iter3_with_skill.md` — Score **TBD below**

### Score Table

| Dimension | Iter-1 Score | Iter-3 Score | Delta |
|---|---|---|---|
| stopping_rule | 3 | **5** | +2 |
| treatment_verification | 3 | **4** | +1 |
| partial_blinding | 5 | 5 | 0 |
| deviation_documentation | 3 | 3 | 0 |
| reproducibility | 3 | 3 | 0 |
| statistical_rigour | 4 | 4 | 0 |
| **Total** | **21/30** | **24/30** | **+3** |

### What Specifically Changed

**stopping_rule (+2)**: This is the most significant improvement. Iter-1 mentioned the gen discrepancy as a confound but never checked whether the stopping rule had been triggered or was at risk. Iter-3 adds a dedicated "Step 2a — Stopping Rule Compliance Check" that explicitly reads `max_generations=50` from `experiment.yaml`, computes percentage of budget consumed per run (62%, 58%), checks for silent invalidity triggers, states "No stopping rule violations" as a positive assertion, and records `stopping_rule_triggered: false` in the manifest. This is the active, proactive check the rubric requires.

**treatment_verification (+1)**: Step 6 (Top Programs Spot-Check) now includes an instruction to confirm "the treatment variable (adversarial prover) is visibly present in Run A's best program." This is inspection of actual evolved code, not just config review. It is still not a runtime Redis-key-pattern check (which would be the gold standard), but it moves from passive to active.

**partial_blinding (unchanged at 5)**: Iter-1 was already at ceiling. Iter-3 matches and strengthens the blinding: it creates an explicit opaque label mapping table (R1/R2), marks it PRIVATE, the analyst briefing uses only R1/R2, test eval numbers (66.1%/64.2%) are explicitly withheld from both the analyst AND the PR comment, and a blinding protocol summary table confirms each item. Critically, the PR comment reports only R1/R2 — the label-reveals-condition gap identified in the original grading is now fully addressed. The prior concern ("labels reveal conditions to analyst") is closed: the analyst receives only R1/R2 with no indication of which is treatment.

### Does This Address the Partial Blinding Gap?

**YES — gap closed.** The prior iter-1 note was: "structural only — labels reveal conditions." The iter-3 response introduces a private opaque-label mapping (R1/R2), applied consistently in the analyst briefing, manifest checkpoint, and PR comment. The analyst cannot infer which run uses the adversarial prover from the labels alone. Test eval numbers are withheld by explicit instruction and confirmed in the blinding summary table.

### Remaining Gaps

- **deviation_documentation**: Still no structured deviation log entry with generation number, rationale, and impact classification. The gen count discrepancy is noted as a YAML comment only.
- **reproducibility**: No env snapshot, seed verification, or dataset checksum. Unchanged from iter-1.
- **statistical_rigour**: No CI computation or formal test described at checkpoint stage; the 1.4pp gap is correctly questioned but not statistically quantified.

*"The protocol is the experiment. Get it right before you touch the data."*

— H. Nakamura
