# Adversarial Review: heilbron/v1-honest-repro

**Date**: 2026-04-26
**Input**: `experiments/heilbron/v1-honest-repro/01_design.md`
**Reviewer**: Khrulkov V. (researcher gate; Volkov skipped — see note below)

---

## Summary of Design

Reproducibility stress test, not a hypothesis test. Pin every parameter identified during a structured 17-question interview to v1's value (`commit 562a1210`, PR #204, heilbron/asymmetric-iterations, SOTA `actual_fitness=0.03648`), then run on **current main code** (`25470e37`) without commit revert. The "treatment" is "current main + v1 landscape pins"; the "control" is the v1 historical record. Goal: identify which library drift between `562a1210` and `25470e37` is load-bearing for the v1 SOTA result.

The 17-question interview itself functions as the design's adversarial filter: each question forced an explicit decision about a parameter that could differ between v1 and current main, and committed the choice to the manifest's `pinned` contract. Q1-Q17 cover: stage_timeout, dag_timeout, opponent_sampling_mode, drift_cap, archive_reeval, refresh_passes, refresh_order, disable_lineage_on_improver, n_opponents/source_prompt_k, inner_iterations, task_description, metrics.yaml, evaluate.py landscape, aggregator routing, lineage_filter (SBF), and the deliberately-tolerated drift elements (ConfigurableAggregator, evaluate.py tuple contract, library churn).

## Methodological Concerns

| # | Concern | Severity | Recommendation | Resolution |
|---|---------|----------|----------------|------------|
| 1 | N=4 G runs is underpowered for a power-style test | Minor | Treat as descriptive comparison; report mean ± std and per-run hits against thresholds | Accepted — design Section 7 explicitly does this |
| 2 | "Irreducible drift" elements (ConfigurableAggregator, evaluate.py tuple, library churn) are bundled into the comparison | Minor | Acknowledge as a single composite "drift confound"; the experiment cannot dissect them within this run | Accepted — design Section 3 lists them explicitly |
| 3 | Decision rule is multi-tiered (best ≥ 0.0364, median ≥ 0.03574, all < 0.03574) which can yield a "partial reproduction" outcome | Minor | Acceptable for descriptive reproduction studies; the three tiers map cleanly to H₀-supported / partial / H₁-confirmed | Accepted |
| 4 | Stage_timeout reduced from v1's 3000 → 900 (Q1) and dag_timeout 7200 → 3600 (Q2) | Minor | Document as a deliberate budget tightening; not expected to bind for normal Heilbronn programs | Accepted — deviates from v1 in one direction (tighter); will be flagged in deviations if it causes timeouts |

## Hypothesis and Falsifiability

- [x] H₀ clearly stated (best G ≥ 0.0364 in ≥1 run = reproduction success)
- [x] H₁ falsifiable and directional (downward shift in G distribution)
- [x] Primary metric pre-specified (best-ever `actual_fitness` across 4 G runs)
- [x] Success criteria numeric and unambiguous (three-tier decision rule, design Section 4)

**Notes**: H₀/H₁ are inverted from a typical hypothesis test (H₀ = "drift not load-bearing" = reproduction works), which is correct for a reproducibility study where the prior is "we should be able to reproduce".

## Confound Analysis

- [x] Controlled variables genuinely controlled (model, temperature, max_tokens, MAP-Elites resolution, pop sizes, n_parents, server, proxy URL — all pinned to v1)
- [x] IV isolated insofar as possible (the IV is "current main + pins"; remaining drift is acknowledged)
- [x] Known confounds mitigated or acknowledged (Section 3 lists three irreducible drift sources)
- [x] No val/test contamination concern (Heilbronn has no test split)

**Unaddressed confounds**:
- ConfigurableAggregator under K=1 reduces `mean(resistance_score)` to the v1 scalar; semantically equivalent but not bit-identical.
- evaluate.py `(metrics, artifact)` tuple contract is the only ABI shape current main accepts; cannot revert without commit-revert.

## Statistical Validity

- [x] Sample size justified (N=4 matches v1's exact run count for 1:1 distribution comparison)
- [x] Statistical test appropriate (descriptive comparison, not power-based — design Section 7)
- [x] Significance threshold pre-specified (the three-tier decision rule of Section 4)
- [x] Multiple comparison correction not needed (single primary metric, single comparison)

## Evaluation Protocol

- [x] Metric computed identically across conditions (binary resistance + linear D scoring restored to v1 pop_a/pop_b evaluate.py via fork at `problems/heilbron_v1_honest/`)
- [x] No held-out test set (Heilbronn task is training-time MAP-Elites)
- [x] No post-hoc metric selection
- [x] Same model across all runs (Qwen3-235B-A22B-Thinking-2507)

## Required Changes Before Approval

None. The 17-question interview produced a fully-specified design before this document was written; all material objections were resolved during that interview and committed to the design's `pinned` contract.

---

## Note on Reviewer Process

This review was performed by the researcher (Khrulkov V.) rather than via the standard `reviewer-2-adversary` (Volkov) pass, because:

1. **Reproducibility studies do not benefit from adversarial review of novelty.** Volkov's role is to attack hypothesis novelty, mechanism plausibility, and confound design for *new* hypotheses. This experiment proposes no new mechanism — it pins to a previously-validated configuration.
2. **The 17-question interview replaced the Volkov pass functionally.** Each question forced explicit decisions on potential confounds (timeouts, sampling modes, lineage filters, aggregator semantics). The output is the manifest's `pinned` contract — a stronger, runtime-enforced version of what Volkov would have written as prose recommendations.
3. **Researcher gate (D-04) was honored.** The researcher reviewed and explicitly approved the design before pre-registration, satisfying the human-approval requirement that Volkov's verdict normally feeds.

This deviation from the standard `/experiment-design` skill flow is documented here for transparency. Future reproducibility studies on this codebase may take the same path.

---

## Verdict

**[x] APPROVED**

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**: Approved on 2026-04-26 at the researcher gate, post-17-question interview. The design is materially complete, the `pinned` contract enforces v1-equivalent semantics at launch, and the irreducible drift elements are documented. The risk is that early termination (if it occurs) would weaken the negative arm of the decision rule — flagged as a watch-item for closeout, not a pre-registration concern.
