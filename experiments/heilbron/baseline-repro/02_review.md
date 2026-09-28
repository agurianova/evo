# Adversarial Review: heilbron/baseline-repro

**Date**: 2026-04-10
**Reviewer**: Prof. Volkov (reviewer-2-adversary)
**Input**: `experiments/heilbron/baseline-repro/01_design.md`

---

## Verdict: APPROVED (with required minor fixes)

**Summary**: This is a well-motivated replication study that addresses a genuine gap in the Heilbronn adversarial research program: the baseline was measured at N=2 and three subsequent experiments have produced results inconsistent with that baseline. The design is honest about what it is (descriptive, not hypothesis-testing), the controlled variables are enumerated clearly, and the primary metric is correct. However, several specification gaps threaten replication fidelity, and the design understates the difficulty of achieving a true replication on a codebase that has evolved significantly since heilbron-prover ran.

---

## Summary of Design

Pure replication of adversarial/heilbron-prover (PR #183) with N=4 pairs instead of N=2. No treatment, no novel mechanism. Goal: establish mean and variance of Constructor actual_fitness at gen 50, producing a reliable reference point for future adversarial experiments. Eight runs (4 Constructor + 4 Improver) on Redis DBs 1-8.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|---------------|
| 1 | **Sync hook class not specified** | Major | See detailed note below |
| 2 | **experiment.yaml max_generations mismatch** | Minor | Fix template: 25 -> 50 |
| 3 | **Codebase drift since heilbron-prover** | Major | See detailed note below |
| 4 | **LLM concurrency confound understated** | Minor | See detailed note below |
| 5 | **Alpha = 0.10 is unusual** | Minor | Acceptable given framing, but document justification |
| 6 | **"No early termination" is too rigid** | Minor | Add a futility/invalidity escape hatch |

### Concern 1 (Major): Sync hook class not specified

The design claims "exact replication" of heilbron-prover but never specifies the `pre_step_hook` class. This is critical because:

- **heilbron-prover** used `gigaevo.prompts.coevolution.sync.MainRunSyncHook` (verified from `cfg_run_P1_A.txt`)
- **adversarial-dynamic-updates** used `gigaevo.adversarial.sync.ProgressBasedSyncHook` (verified from `cfg_run_SOFT_C_A.txt`)

These are different classes with different synchronization behavior. `ProgressBasedSyncHook` has additional parameters (`sources`, `min_delta`, `sync_every_n_epochs`) that `MainRunSyncHook` does not. The adversarial-dynamic-updates results document explicitly noted that `ProgressBasedSyncHook` caused 4 extended deadlocks (62-86 minutes) wasting ~40% of GAN compute time.

If the baseline-repro accidentally uses `ProgressBasedSyncHook` (because the default pipeline config may have been updated since heilbron-prover), this is no longer a faithful replication.

**Required fix**: Add `pre_step_hook._target_: gigaevo.prompts.coevolution.sync.MainRunSyncHook` to the Controlled Variables table (Section 5). Verify during implementation that `--cfg job` shows this class, not `ProgressBasedSyncHook`.

### Concern 3 (Major): Codebase drift since heilbron-prover

heilbron-prover launched at commit `694a6ca9` (2026-04-06). The current codebase has had significant changes since then, including:

- MetricsTracker refactoring (clear_series, full frontier recomputation)
- SteadyStateEvolutionEngine addition
- Various bug fixes in the adversarial pipeline (GAN delta clamp, sync hook fixes)
- Memory system audit changes

The design states "exact replication" but does not pin the codebase to the heilbron-prover commit. Running the "same config" on a different codebase is not the same experiment. Any behavioral change in `AdversarialPipelineBuilder`, `EvolutionEngine`, `MetricsTracker`, or `MapElitesMultiIsland` between `694a6ca9` and HEAD would silently invalidate the replication claim.

**Recommendation**: The design should either (a) pin the codebase to the heilbron-prover commit (run from that exact commit), or (b) explicitly acknowledge that this is a "same-config, current-codebase" replication and document which codebase components have changed. Option (b) is acceptable for a baseline-establishing study, but the design should not claim "exact replication" without qualification.

This is not a fatal flaw -- the primary purpose is to establish the N=4 distribution, not to exactly reproduce the N=2 numbers. But the language should be precise.

### Concern 4 (Minor): LLM concurrency confound understated

The design acknowledges that 8 concurrent mutation requests (vs 4 in heilbron-prover) may increase LLM latency, and proposes monitoring mutation latency. However, this is an actual confound, not just a diagnostic: if mutation latency doubles, the effective exploration rate per generation halves, which directly impacts actual_fitness. The Qwen3-235B model with 8 concurrent requests through a single LiteLLM proxy may exhibit different throughput characteristics.

The design should state: if mean mutation latency exceeds 2x the heilbron-prover latency, the experiment must document this as a confound in the results. It should NOT be a "note" -- it should be a run validity criterion.

### Concern 6 (Minor): No early termination is too rigid

"All 8 runs proceed to gen 50. No early termination." is stated, but the Run Invalidation Criteria (Section 10) contradict this by listing three conditions that do terminate runs. Additionally, if ALL 4 Constructor actual_fitness values fall below 0.025 by gen 30 (indicating a catastrophic failure), running to gen 50 wastes compute for no information gain. A futility clause would be prudent.

---

## Hypothesis and Falsifiability

- [x] H0 clearly stated
- [x] H1 falsifiable and directional
- [x] Primary metric pre-specified
- [x] Success criteria numeric and unambiguous

**Notes**: The hypothesis framing is honest -- this is a descriptive study with a protocol-compliance hypothesis layered on top. The effect-size thresholds (Section 2) are well-calibrated against prior results. The four-bin interpretation table (CONFIRMED HIGH / CONFIRMED / REVISED / UNRELIABLE) is the right way to frame a replication.

One quibble: H0 states "true mean <= 0.030" and H1 states "mean >= 0.033". The gap between 0.030 and 0.033 is not covered by either hypothesis. This is intentional (it maps to the REVISED bin) but should be stated explicitly: "If the mean falls in [0.030, 0.033), neither H0 nor H1 is supported; the result is REVISED."

---

## Confound Analysis

- [x] Controlled variables genuinely controlled (conditional on Concern 1 fix)
- [x] IV isolated (no IV -- this is single-condition)
- [x] Known confounds mitigated or acknowledged
- [x] Val/test split not contaminated (no val/test split -- optimization problem)

**Unaddressed confounds**:

1. **Sync hook class** (see Concern 1) -- if wrong class is used, this is a hidden IV, not a controlled variable.
2. **Codebase version** (see Concern 3) -- not pinned, so pipeline behavior may differ from heilbron-prover.
3. **Time-of-day LLM load**: 8 runs launched simultaneously will compete for LLM proxy bandwidth. heilbron-prover launched 4 runs. Peak-hour vs off-peak LiteLLM throughput may differ. Not easily mitigated, but should be documented.

---

## Statistical Validity

- [x] Sample size justified
- [x] Statistical test appropriate
- [x] Significance threshold pre-specified
- [x] Multiple comparison correction applied if needed (N/A -- single test)

**Notes**: N=4 is defensible for the stated purpose. The sample size justification is sound: assuming sigma ~ 0.001 (from the heilbron-prover within-pair range), the 95% CI half-width is ~0.0016, which is sufficient to distinguish the four interpretation bins. The one-sample t-test with alpha=0.10 is unusual but acceptable for a replication study -- the real output is the CI, not the p-value.

However, the design assumes sigma ~ 0.001 based on the within-pair range of 0.00168 from N=2. This is itself a highly uncertain estimate. If the true sigma is 0.003 (plausible given adversarial-dynamic-updates controls at 0.030-0.032), the 95% CI half-width balloons to ~0.0048, which is too wide to distinguish CONFIRMED from REVISED. The design should acknowledge this and state what happens if the observed SD exceeds 0.003.

---

## Evaluation Protocol

- [x] Metric computed identically across conditions (single condition)
- [x] Val/test sets fixed and identical for all runs (N/A -- optimization)
- [x] No post-hoc metric selection
- [x] Thinking mode consistent across evaluations

**Notes**: actual_fitness (raw min_area) is opponent-independent and computed deterministically from the Constructor's point configuration. This is the correct primary metric. The adversarial fitness is rightly secondary.

---

## Required Changes Before Approval

1. **Add sync hook class to Controlled Variables table**: `pre_step_hook._target_: gigaevo.prompts.coevolution.sync.MainRunSyncHook` with verification plan in Section 12.
2. **Fix experiment.yaml**: `max_generations: 25` should be `max_generations: 50` to match the design.
3. **Qualify "exact replication" language**: Acknowledge that the codebase has evolved since heilbron-prover (`694a6ca9`). State whether this is a same-commit or same-config replication, and if the latter, document that codebase drift is an accepted confound.

---

## Strengths

1. **Directly addresses the most important open question**: The baseline uncertainty is the single biggest threat to interpretability of all prior Heilbronn adversarial results. Fixing this is the highest-value experiment possible right now.
2. **Correct primary metric**: actual_fitness (opponent-independent raw min_area) avoids the adversarial fitness gaming problems that plagued adversarial-dynamic-updates.
3. **Honest framing**: Calling this a descriptive study rather than forcing it into a hypothesis-testing framework shows scientific maturity.
4. **Clear run design table**: DB assignments and opponent pairings are unambiguous.
5. **Good confound awareness**: LLM version drift, initial seed stochasticity, and Redis contention are correctly identified.
6. **The four-bin interpretation table is excellent**: Pre-registering what each outcome range means prevents post-hoc narrative construction.

---

## Recommendation

Proceed after fixing the three required changes listed above. None are fundamental design flaws -- they are specification gaps that would threaten replication fidelity if left unaddressed during implementation. The scientific motivation is strong, the design is sound, and N=4 is the right sample size for this question.

---

## Verdict

**[x] APPROVED**

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**: Clean replication study with strong motivation. The three required fixes are minor specification items, not design flaws. I trust the implementation phase to catch them. If the sync hook class or codebase version is wrong at launch, the experiment is invalid regardless of results -- so get those right.
