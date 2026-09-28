# Research Methodology Expert Memory

## 2026-03-20: First Full Protocol Audit

### Observed Strengths
- Pre-registration with commit-hash anchoring is genuine, not theatrical
- Amendment protocol with impact classification is well-designed
- Adversarial review loop (Elena/Volkov) catches real issues before launch
- Merge policy (--merge not --squash) preserves audit trail correctly
- Results template forces deviation reporting before interpretation
- 10 completed experiments with honest NULL/NEGATIVE verdicts -- no p-hacking pressure

### Recurring Weaknesses Observed
1. **N=1 per cell in factorial designs** (push 2x2, crossover 2x2) -- cannot estimate within-cell variance
2. **Bundled interventions** (colbert_feedback: ColBERT + rich feedback simultaneously) -- prevents causal attribution
3. **Amendment accumulation** (prompt_coevolution: 13 amendments, 8 relaunches) -- suggests insufficient pre-production testing
4. **Val-test gap as systematic issue** -- 4-8pp gaps across many experiments, not addressed at protocol level
5. **No blinding mechanism** -- researcher sees val metrics during monitoring, which influences checkpoint decisions
6. **Test set reuse** -- same 300 test samples across 10+ experiments creates implicit multiple-testing problem
7. **Phase 5 pending on completed experiments** -- hover/baseline complete but no 05_results.md

### Open Recommendations (not yet acted on)
1. Minimum N>=2 per cell requirement in protocol
2. Pre-registered test-set rotation or family-wise error correction across experiments
3. Preflight check for compound confound detection (>1 IV changed)
4. Automated environment drift detection (model_name mismatch caused 2+ failures)
5. Watchdog should detect and alert on val-test gap inflation in real-time
6. Gate script should verify experiment has no pending Phase 5 before launching new experiment on same task

### Protocol Improvements Adopted
- (none yet from 2026-03-20 audit)

---

## 2026-04-07: Full Skills Audit (experiment lifecycle v2)

### Key New Findings
- **Treatment verification is now genuinely layered** (treatment-verifier agent + smoke-test runtime checks + diagnose.py Check 12/13 at every checkpoint) — this is the protocol's strongest element and a material improvement since the March audit.
- **Partial blinding at checkpoint-analyst** is now present but weak — conditions are structurally identifiable from run labels/prefixes; analyst cannot be truly blinded.
- **Stopping rules remain unenforced** — section 10 of 01_design.md is free-text with no preflight validation. Optional stopping exposure confirmed as Critical gap.
- **Statistical power gap is Critical** — N=2-4 runs with inter-run σ≈0.63pp are systematically underpowered. Volkov checks N>=2 but not whether N=2 gives acceptable power given the observed σ and target MDE.
- **Restart skill discards partial data** by default — no archiving before flush.
- **Dataset checksums are pre-registered but not verified at launch** — drift goes undetected.
- **Effect sizes reported without confidence intervals** across multiple completed experiments.

### Open Recommendations (2026-04-07, not yet acted on)
1. (Critical) Add preflight/pre-merge gate for early-termination criterion completeness in 01_design.md section 10
2. (Critical) Require power calculation in section 7 — block Volkov APPROVED if missing σ, MDE, power
3. (Major) Pre-specify exact statistical test command in 03_plan.md; verify same test used in 05_results.md
4. (Major) Make archiving mandatory in experiment-restart before flush
5. (Major) Add interim analysis decision rule field to 03_plan.md
6. (Major) Require CI notation in 05_results.md effect size section; check via regex in check_experiment_complete.sh
7. (Major) Document partial blinding limitation OR implement run-label relabelling intermediary
8. (Minor) Add dataset checksum verification to preflight_check.py
9. (Minor) Record LLM temperature/nucleus params in 03_plan.md
10. (Minor) Make anomaly detector cron generation-relative, not time-relative

### Still Open from March Audit
- Pre-registered test-set rotation / family-wise error correction (test set reuse across 10+ exps)
- Val-test gap watchdog alert
- Phase 5 gate before new experiment launch on same task

---

## 2026-04-07: Skills Evaluation Grading (eval_grading_2026-04-07.md)

### Scores
| Skill | With | Without | Delta |
|---|---|---|---|
| experiment-design | 24/30 | 20/30 | +4 |
| experiment-implement | 22/30 | 18/30 | +4 |
| experiment-checkpoint | 21/30 | 17/30 | +4 |
| experiment-closeout | 25/30 | 21/30 | +4 |
| experiment-restart | 22/30 | 14/30 | +8 |

### Key Finding
Skills constitute a **substantially better process but not yet a trustworthy protocol**. Largest improvement: experiment-restart (+8), which converts operational recovery into a scientific integrity checkpoint. Skills encode requirements but lack terminal enforcement.

### Top 3 Remaining Gaps (even with skills)
1. **(Critical)** Stopping rules in 01_design.md §10: no machine gate, format not validated by any gate script
2. **(Critical)** Statistical power: N≥2 accepted without formal power check (N=2 underpowered for SUGGESTIVE-range effects given σ≈0.63pp)
3. **(Major)** CI notation required in Elena briefing but not enforced in check_experiment_complete.sh

### Protocol Improvements Confirmed Since March
- Treatment verification now pre-launch (treatment-verifier agent + smoke test) — material upgrade
- Partial blinding at checkpoint-analyst now present
- Anti-p-hacking MES check in closeout skill (new since March)
- Deviation documentation systematic via 04_issues_log.md
