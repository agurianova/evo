# Adversarial Review (Round 2): HoVer Baseline -- Cold-Start Retrieval Coverage via n=4 Replication

**Date**: 2026-03-18
**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Input**: `experiments/hover/baseline/01_design.md` (revised)
**Round**: 2 (prior verdict: NEEDS REVISION)

---

## Summary of Design

The experiment proposes n=4 independent cold-start replications of GigaEvo on HoVer,
a multi-hop claim verification task with discrete retrieval coverage fitness. All four
runs are identically configured (no independent variable). The primary output is the
mean and SD of test retrieval coverage at generation 25, compared against the GEPA
benchmark of 52.33% via a one-sample t-test. This is the first GigaEvo experiment on
HoVer and mirrors the HotpotQA cold_start design (PR #75).

---

## Round 1 Concern Resolution

All seven concerns from Round 1 have been addressed. Verification follows.

### Critical #1: `stage_timeout` not wired in `standard.yaml` -- RESOLVED

**Round 1**: `config/pipeline/standard.yaml` did not pass `stage_timeout` to
`DefaultPipelineBuilder`. The Hydra override `stage_timeout=3000` was silently ignored;
all stages defaulted to 2400s.

**Fix verified**: `standard.yaml` now contains (lines 14-15):

```yaml
stage_timeout: ${stage_timeout}
dag_timeout: ${dag_timeout}
```

I traced the full resolution chain:
1. `config/constants/pipeline.yaml` defines `stage_timeout: 2400` as the global default.
2. `standard.yaml` interpolates `${stage_timeout}` into the `pipeline_builder` block.
3. A Hydra command-line override `stage_timeout=3000` overrides the global default.
4. `DefaultPipelineBuilder.__init__` (line 148) receives the value as the `stage_timeout`
   keyword argument, stores it as `self._stage_timeout` (line 151).
5. All stages in `_contribute_default_nodes` use `stage_timeout = self._stage_timeout`
   (line 164), including `ValidateCodeStage`, `CallProgramFunction`,
   `CallValidatorFunction`, `FetchMetrics`, and `FetchArtifact`.

The fix is complete and correct. The `--cfg job` pre-launch check will now show
`pipeline_builder.stage_timeout: 3000` when `stage_timeout=3000` is passed as a
Hydra override.

The design document reflects this fix in Section 5 (line 139: `stage_timeout: 3000`)
and Appendix A item 6 (lines 491-495), which notes the verification as complete.

### Critical #2: `model_name` default wrong -- RESOLVED

**Round 1**: `config/constants/endpoints.yaml` defaults to `model_name: deepseek/deepseek-v3.2`.
The design did not list `model_name` or `llm_base_url` as explicit Hydra overrides.

**Fix verified**: I confirmed `endpoints.yaml` still defaults to `deepseek/deepseek-v3.2`
(line 9). The revised design now addresses this at three points:

1. **Section 5** (lines 131-132): `model_name` and `llm_base_url` listed as controlled
   variables with explicit values, bold notation, and the note "requires explicit Hydra
   override (default is `deepseek/deepseek-v3.2`)."
2. **Section 6 Run Design Table** (lines 163-168): New columns `model_name` and
   `llm_base_url` added for all four runs, with bold values and per-run mutation LLM URLs.
   The bold-values legend (lines 170-174) explicitly enumerates both overrides.
3. **Appendix A items 7-8** (lines 497-503): `model_name` and `llm_base_url` overrides
   added to the pre-launch verification checklist with the specific `--cfg job` values
   to confirm.

This is a thorough fix. The researcher has made it impossible to miss these overrides.

### Major #3: `test.py --n-samples` defaults to 3 -- RESOLVED

**Round 1**: `test.py` argparse defaulted `--n-samples` to 3. Running `test.py --mode redis`
without explicit `--n-samples 300` would evaluate on only 3 test samples.

**Fix verified**: `test.py` line 192 now reads `default=None`. The control flow is:
- **Baseline mode** (line 203): `args.n_samples or 3` -- defaults to 3 for quick testing.
- **Redis mode** (line 210): `n_samples=args.n_samples` -- passes `None` to
  `test_best_chain`, which passes it to `load_test_context(n_samples=None)`.
  At line 31: `if n_samples is not None and n_samples < len(raw_samples)` -- with `None`,
  the condition is `False`, so all samples are loaded.

This is the correct fix. Redis mode now loads the full test set by default. The design
document's reference to `test.py --mode redis` (Section 4, line 143) is now accurate
without requiring an explicit `--n-samples` flag.

### Major #4: No failure feedback confound -- RESOLVED

**Round 1**: The absence of failure feedback in the mutation context was noted only in
Risk 4 of Section 12. I required it be elevated to Section 9 as a named confound.

**Fix verified**: Section 9 (line 346) now contains a full confound entry titled "No
failure feedback in mutation context." The entry:
- Describes the mechanism: `FormatterStage` receives `None` from `FetchArtifact` because
  `validate.py` returns a simple dict.
- Identifies the partial confounding with the discrete fitness signal.
- States that a NULL result cannot distinguish between discrete fitness and absent
  feedback as causal factors.
- Frames the baseline condition as intentional, with a failure formatter as a natural
  next treatment condition.

Risk 4 in Section 12 (lines 441-449) now cross-references this confound entry. The
two-way cross-reference ensures neither can be overlooked in Phase 5 analysis. Well done.

### Minor #5: `dag_timeout` not explicit -- RESOLVED

**Fix verified**: `dag_timeout: 7200` is now listed as an explicit Hydra override in:
- Section 5 (line 140): "set as explicit Hydra override for auditability"
- Section 6 Run Design Table: dedicated column with value for all four runs
- Section 6 bold-values legend (line 172)
- Appendix A item 8 (lines 503-504)

### Minor #6: SUGGESTIVE ambiguity -- RESOLVED

**Fix verified**: The revised design now uses two distinct labels:
- **SUGGESTIVE-SIG** (Section 2, line 54 / Section 8, line 280): statistically significant
  but modest improvement; p < 0.05 but mean in (52.33%, 55.0%).
- **SUGGESTIVE-NS** (Section 2, line 54 / Section 8, line 281): directionally above GEPA
  but not significant at N=4; p >= 0.05 with mean > 52.33%.

The Appendix B decision tree (lines 525-533) reflects this distinction, with "SUGGEST-SIG"
and "SUGGEST-NS" as separate leaf nodes. No ambiguity remains.

### Minor #7: Wald CI -- RESOLVED

**Fix verified**: Section 8 (lines 304-315) now uses the Wilson score interval formula
for individual run CIs, with the explicit rationale: "Wilson score interval chosen over
Wald for better coverage probability near boundary values (0 or 1), which may occur at
gen 0." The formula is correctly stated. The t-based CI for the mean across runs is
retained (appropriate for N=4 run-level means).

---

## Independent Assessment of the Revised Design

Beyond verifying the Round 1 fixes, I re-examined the complete revised document for any
new issues or previously unnoticed concerns.

### Hypothesis and Falsifiability

- [x] H0 is clearly stated
- [x] H1 is falsifiable and directional
- [x] Primary metric is pre-specified and sufficient to test H1
- [x] Success criteria are numeric and unambiguous

**Notes**: The hypothesis structure remains well-constructed. H0 (cold-start mean <=
52.33%) is falsifiable via the one-sample t-test. The SUGGESTIVE-SIG / SUGGESTIVE-NS
distinction now makes all five possible verdicts unambiguous in both their triggering
conditions and their scientific implications. The effect size thresholds are pre-registered
with explicit numeric boundaries and clear rationale (Section 2, lines 58-61).

### Confound Analysis

- [x] All controlled variables are genuinely controlled
- [x] IV is isolated (N/A -- no IV; pure replication)
- [x] Known confounds are mitigated or acknowledged
- [x] Val/test split is not contaminated

**Notes**: With the `stage_timeout` wiring fixed and `model_name`/`llm_base_url` now
explicit, all controlled variables listed in Section 5 are genuinely controlled. The
Section 9 confound table is comprehensive: 11 named confounds with mitigations. The
failure feedback confound is now properly documented with its partial confounding with
discrete fitness clearly articulated. I have no additional confounds to raise.

### Statistical Validity

- [x] Sample size is justified
- [x] Statistical test is appropriate for the data
- [x] Significance threshold is pre-specified
- [x] Multiple comparison correction applied if needed

**Notes**: The power analysis (Section 7) is correctly computed. The one-sample t-test
against 52.33% is the right test. The bootstrapped CI as a sensitivity check is good
practice. No multiple comparison correction is needed (single formal inferential test).
The Wilson score interval for individual runs is appropriate.

### Evaluation Protocol

- [x] Metric is computed identically across all conditions
- [x] Val set and test set are fixed and identical for all runs
- [x] No metric is cherry-picked post-hoc
- [x] Thinking mode is consistent across all evaluations

**Notes**: With the `test.py` fix, redis mode now correctly loads all test samples by
default. The evaluation protocol is sound. The thinking-mode verification criterion
(< 95% of outputs with `<think>` blocks = invalidation) and gen-0 sanity check (val
coverage < 20%) are well-calibrated. The `--cfg job` pre-launch checklist in Appendix A
now covers all critical overrides.

---

## Methodological Concerns

| # | Concern | Severity | Status |
|---|---------|----------|--------|
| 1 | `stage_timeout` not wired in `standard.yaml` | Critical | **RESOLVED** -- `standard.yaml` now wires both `stage_timeout` and `dag_timeout` |
| 2 | `model_name` config default wrong | Critical | **RESOLVED** -- added to Section 5, Section 6 Run Design Table, Appendix A items 7-8 |
| 3 | `test.py --n-samples` defaults to 3 | Major | **RESOLVED** -- argparse default changed to `None`; redis mode loads all samples |
| 4 | No failure feedback confound | Major | **RESOLVED** -- elevated to Section 9 with full confound analysis; cross-referenced in Risk 4 |
| 5 | `dag_timeout` not explicit | Minor | **RESOLVED** -- marked as explicit override in Section 5, Section 6, Appendix A item 8 |
| 6 | SUGGESTIVE ambiguity | Minor | **RESOLVED** -- differentiated to SUGGESTIVE-SIG and SUGGESTIVE-NS |
| 7 | Wald CI | Minor | **RESOLVED** -- switched to Wilson score interval |

**No new concerns identified.**

---

## Required Changes Before Approval

_(None.)_

---

## Verdict

**[x] APPROVED** -- proceed to Phase 3

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**:

All seven concerns from the Round 1 review have been addressed satisfactorily. The
two critical infrastructure issues -- the silent `stage_timeout` wiring failure in
`standard.yaml` and the `model_name` config default drift -- are now fixed at the code
level and documented in the design with appropriate verification steps. The two major
concerns -- the `test.py` n-samples default and the failure feedback confound -- are
similarly resolved with clean fixes.

I want to note the quality of the revisions. The `stage_timeout` fix was not merely a
documentation change but a genuine code fix to `standard.yaml` that closes a silent
pipeline misconfiguration affecting all experiments using `pipeline=standard` with
non-default timeouts. The `test.py` fix uses a clean `None`-default pattern that
preserves baseline mode behavior while correctly loading all samples in redis mode. The
failure feedback confound entry in Section 9 is one of the most thorough confound
analyses I have seen in a GigaEvo design document -- the explicit identification of
partial confounding between discrete fitness and absent failure feedback, and the
pre-registered interpretive framework for each possible verdict, demonstrates exactly the
kind of methodological discipline that makes results trustworthy regardless of outcome.

The experiment is well-designed, the code is verified, the confounds are documented,
the statistical plan is appropriate, and the pre-launch checklist is comprehensive. This
design is ready for execution.

> *"The science demands nothing less."*
