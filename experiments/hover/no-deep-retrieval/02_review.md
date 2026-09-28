# Reviewer 2 — Methodological Review

**Reviewer**: Prof. Volkov (adversarial methodologist)
**Design under review**: `experiments/hover/no-deep-retrieval/01_design.md`
**Date**: 2026-03-31

---

## Summary of Design

A 2x2 factorial ablation ({static, dynamic} x {standard retrieval only, standard + deep retrieval}) to determine whether `retrieve_deep` (BM25 k=10) contributes to GigaEvo's advantage over the GEPA benchmark on HoVer. N=2 per cell, 8 runs total. Primary metric: test discrete retrieval coverage. Primary test: pooled main effect of retrieval depth (n=4 per level), Welch's t-test, one-sided, alpha=0.10. Secondary: GEPA-fair comparison (Cell C vs. 52.33%), interaction diagnostic.

---

## Strengths

- The research question is well-motivated and addresses a genuine confound in all prior GEPA comparisons. This should have been run earlier.
- The 2x2 factorial is the correct design for separating retrieval depth from topology. Pooling across topology for the primary test (n=4 per retrieval level) is a sensible use of the factorial structure.
- Treatment enforcement at four levels (tool registry, chain validation, seed program, task description) is thorough. The belt-and-suspenders approach -- structural rejection before runtime plus runtime KeyError as a fallback -- is sound engineering.
- The wave-splitting contingency (1 run per condition per wave) correctly avoids wave-condition aliasing under resource constraints.
- The execution plan routes all runs through the same LiteLLM proxy, eliminating host-treatment confounds that plagued earlier experiments.
- Secondary metrics are well-chosen: tracking `n_steps`, `n_deep_retrieval`, and invalidity rate will provide mechanistic insight regardless of the primary outcome.
- Effect-size thresholds are defined a priori with clear action implications. This is good practice.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|---------------|
| M1 | N=2 per cell makes interaction uninterpretable | Major | Downgrade interaction to exploratory diagnostic, or increase to N=3 per cell |
| M2 | GEPA 52.33% treated as known constant with zero variance | Major | Obtain repeated GEPA evals, or state assumption explicitly |
| M3 | Cold start prevents comparison to prior baselines | Major | Add Cell B replication check against historical 51-54% range |
| m1 | Alpha=0.10 one-sided is liberal for publication claims | Minor | Use alpha=0.05 or justify cost-benefit |
| m2 | No plan for standard > deep outcome | Minor | Add two-sided sensitivity check |
| m3 | No verification that LiteLLM proxy is cache-free | Minor | Confirm proxy config |
| m4 | experiment.yaml still has template placeholders | Minor | Fill at implementation (no action now) |
| m5 | Pipeline compatibility for full variants unverified | Minor | Verify return type of full/validate.py |

### M1. N=2 per cell is the bare minimum and the interaction claim will be uninterpretable

The design acknowledges this (Risk #3) but underestimates the consequence. With n=2 per cell, a single outlier run (infrastructure hiccup, unlucky seed trajectory, chain server timeout spike) can flip the sign of a cell mean. The primary pooled test (n=4 per level) has MDE = 2.49pp at conservative SD, which is adequate for the stated thresholds. However, the "secondary decision" table (topology x retrieval interaction) presents four interpretive outcomes as if they will be distinguishable -- they will not be, at n=2 per cell. The interaction MDE is approximately 4.4pp, meaning only STRONG effects are detectable, and even those with marginal confidence.

**Recommendation**: Downgrade the interaction analysis from "secondary decision" to "exploratory diagnostic." Do not present the four interaction outcomes as decisions -- present them as hypotheses for a powered follow-up. Alternatively, commit to N=3 per cell (12 runs total) if infrastructure permits; this brings the within-cell MDE to ~3.2pp.

### M2. The GEPA-fair comparison (Cell C vs. 52.33%) is a one-sample test against a point estimate with unknown variance

The GEPA benchmark of 52.33% is treated as a fixed constant, but it was presumably computed on the same 300-sample test set. A single-point benchmark has its own sampling variance. If GEPA were re-evaluated with a different random seed or inference run, it would fluctuate. The one-sample t-test assumes the null mean is known exactly. This inflates the effective alpha.

**Recommendation**: Either (a) obtain 5 repeated GEPA evaluations on the test set to estimate its variance (preferred), or (b) acknowledge in the analysis plan that the GEPA comparison treats 52.33% as a population parameter, state the assumption explicitly, and note that the p-value is conditional on this assumption.

### M3. The "cold start" design choice eliminates the ability to compare against prior baselines

All runs start from cold (no `program_loader.problem_dir`). Prior experiments (hover/baseline, hover/feedback_softfit) used warm starts or different engines. This means Cell B (static + deep) cannot be directly compared to hover/baseline (51.65% grand mean) because the engine differs (steady-state vs. generational) and the start condition may differ. The design notes this in Risk #5 but does not elevate it to the analysis plan.

**Recommendation**: Add an explicit replication check: if Cell B's mean deviates from the historical baseline range (51-54%) by more than 3pp, flag the engine-topology interaction as a confounder and interpret the ablation cautiously.

### m1. Alpha = 0.10 is liberal for a one-sided test

The design uses alpha = 0.10 one-sided for the primary comparison. This is equivalent to alpha = 0.20 two-sided. Given that the result will be used to make claims about GEPA comparison fairness in publications, a false positive here has real reputational cost. Alpha = 0.05 one-sided is more standard and still achievable at the stated MDE.

**Recommendation**: Use alpha = 0.05 one-sided, or justify the choice of 0.10 with an explicit cost-benefit argument (e.g., "a false negative -- failing to detect that GEPA comparison is confounded -- is more costly than a false positive").

### m2. No pre-commitment to handling the case where dynamic-std (Cell C) outperforms dynamic-deep (Cell D)

This is a plausible outcome: removing `retrieve_deep` simplifies the search space, potentially letting the mutation LLM find better chains faster. The effect-size table handles "standard >= deep" as NULL, but if standard is significantly *better* than deep, the interpretation changes (deep retrieval is actively harmful by expanding the search space). The analysis plan should include a two-sided sensitivity check.

**Recommendation**: Add a note that if the pooled standard mean exceeds the pooled deep mean by > 2pp, a post-hoc two-sided test will be conducted to assess whether deep retrieval is detrimental.

### m3. No explicit control for mutation LLM prompt contamination across conditions

All 8 runs share the same LiteLLM proxy for the mutation LLM. The mutation LLM is stateless (no cross-run memory), so there is no direct contamination. However, if the proxy applies any caching (e.g., semantic deduplication of identical prompts), runs in Cell A and Cell B could receive cached outputs from each other if the non-tool portions of the prompt are identical. This is unlikely with steady-state's diverse prompts but worth verifying.

**Recommendation**: Confirm that the LiteLLM proxy does not cache completions across requests. A one-line check in the proxy config suffices.

### m4. experiment.yaml is still the template -- not filled in

The manifest file has placeholder values (`<task>/<name>`, `<metric>`, etc.) and empty `runs: []`. This is fine at the design phase but should be flagged: the implementation step must fill this before launch, and the automation tools (status.py, watchdog, diagnose.py) will not function until it is populated.

**Recommendation**: No action needed at design phase; just a reminder for implementation.

### m5. Pipeline compatibility for full variants unverified

The design claims `pipeline=standard` for all runs. CONTEXT.md notes that `pipeline=standard` is for `chains/hover/static_soft` (plain dict, no feedback) while `pipeline=hover_feedback` is for `chains/hover/static` (tuple return). The new `full_no_deep` variant should return the same format as `full`. Both must be verified compatible with `pipeline=standard`.

**Recommendation**: Verify the return type of `full/validate.py` and `full_no_deep/validate.py` during implementation. If either returns a tuple, use `pipeline=hover_feedback`.

---

## Hypothesis and Falsifiability

- [x] H0 clearly stated (deep retrieval provides no benefit; main effect <= 0pp)
- [x] H1 falsifiable and directional (deep > standard)
- [x] Primary metric pre-specified (test discrete retrieval coverage, 300-sample held-out set, 5-repeat mean)
- [x] Success criteria numeric and unambiguous (effect-size thresholds at 0, +2, +4pp)

**Notes**: The thresholds are well-calibrated against the prior GEPA delta (~8pp for dynamic-topology). A +4pp retrieval effect would explain roughly half the observed gain, which correctly triggers "STRONG POSITIVE" and reframes the GEPA comparison.

## Confound Analysis

- [x] Controlled variables genuinely controlled (engine, LLM endpoints, hyperparameters, val/test sets all shared)
- [x] IV isolated (retrieval depth manipulated via problem.name only; topology is the second factor, crossed cleanly)
- [x] Known confounds mitigated or acknowledged (infrastructure contention symmetric; engine novelty on static flagged)
- [x] Val/test split not contaminated (test set held out, never seen during evolution)

**Unaddressed confounds**: The seed program differs between standard-only and deep conditions (Step 7 tool name). This creates a gen-0 fitness confound that propagates through evolution. The design acknowledges this but does not propose a control (e.g., a "deep seed + no-deep registry" condition where the seed is silently downgraded at runtime). At N=2 this additional condition is impractical, but it should be noted as a limitation: the ablation conflates "tool availability" with "seed quality."

## Statistical Validity

- [x] Sample size justified (pooled n=4 per level, MDE = 2.49pp at SD=1.5pp)
- [x] Statistical test appropriate (Welch's t-test for unequal variance; one-sample t for GEPA comparison)
- [ ] Significance threshold pre-specified (alpha=0.10 one-sided is specified but liberal; see m1)
- [x] Multiple comparison correction applied if needed (three planned comparisons, but primary is clearly designated; no correction needed for pre-planned contrasts)

**Notes**: The power analysis correctly uses pooled n=4 rather than per-cell n=2 for the primary test. The within-cell MDE of ~4.4pp is honestly reported as "directional diagnostics only." The SD estimate of 1.5pp is described as "conservative upper bound from prior experiments" -- this should be verified against actual inter-run SDs from hover/baseline (reported SD = 0.63pp, n=4) and hover/feedback_softfit. If the true SD is closer to 0.63pp, the design is substantially overpowered for the primary test, which is fine.

## Evaluation Protocol

- [x] Metric computed identically across conditions (same test.py, same 300-sample test set, same 5-repeat protocol)
- [x] Val/test sets fixed and identical for all runs
- [x] No post-hoc metric selection
- [x] Thinking mode consistent across evaluations (Qwen3-8B thinking mode via LiteLLM proxy for all)

**Notes**: The 5-repeat evaluation protocol for the primary metric is consistent with prior experiments and adequate for reducing evaluation noise.

---

## Required Changes Before Approval

1. Downgrade the interaction analysis (topology x retrieval) from "secondary decision" to "exploratory diagnostic" in the analysis plan and success criteria sections (M1).
2. Add an explicit assumption statement that the GEPA benchmark of 52.33% is treated as a known population parameter, and note that the one-sample p-value is conditional on this assumption (M2).
3. Add a Cell B replication check: if Cell B (static + deep) deviates from the historical baseline range (51-54%) by more than 3pp, flag the engine-topology interaction before interpreting the retrieval ablation (M3).
4. During implementation, verify that `full/validate.py` returns a plain dict (not a tuple) and is compatible with `pipeline=standard` (m5).

---

## Verdict

**[x] APPROVED**

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**: The core design is sound: the question is important, the factorial structure is correct, the treatment enforcement is multi-layered, and the analysis plan is pre-specified with clear decision thresholds. The main limitation is sample size, which is a resource constraint rather than a design flaw. The four required changes above are minor revisions that do not alter the experimental structure -- they add safeguards to the interpretation framework. Proceed to implementation after addressing them.

---

*Reviewed by Prof. Volkov, 2026-03-31.*
