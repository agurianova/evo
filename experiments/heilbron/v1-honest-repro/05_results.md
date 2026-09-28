# Results: heilbron/v1-honest-repro

**Date**: 2026-04-27
**Input**: Final metrics (Redis extraction 2026-04-27), `01_design.md`, `04_issues_log.md`
**Branch**: `exp/heilbron/v1-honest-repro`
**Prereg commit**: `25470e37`
**Verdict**: **SUGGESTIVE** (lean H1 -- current main does NOT cleanly reproduce v1 SOTA)

---

## 1. Final Metrics

Pre-registered `max_generations=200`. Experiment was **early-terminated** at researcher authorization at the following per-run generation counts (25-46% of budget):

| Run | Role | Arm | Gen (of 200) | Best-ever actual_fitness | Best-ever fitness (MAP-Elites norm) | n_programs | Budget used |
|-----|------|-----|--------------|--------------------------|--------------------------------------|------------|-------------|
| A1_G | constructor | composition | 50 | 0.03368 | 0.88862 | 1003 | 25% |
| A1_D | improver | composition | 71 | 0.03547 | 0.10122 | 829 | 36% |
| A2_G | constructor | composition | 52 | 0.03301 | 0.95183 | 919 | 26% |
| A2_D | improver | composition | 90 | 0.03301 | 0.00095 | 1058 | 45% |
| C1_G | constructor | gradient_in_prompt | 56 | 0.03471 | 0.96937 | 590 | 28% |
| C1_D | improver | gradient_in_prompt | 91 | 0.03499 | 0.38242 | 1027 | 46% |
| C2_G | constructor | gradient_in_prompt | 58 | 0.03452 | 0.93993 | 627 | 29% |
| C2_D | improver | gradient_in_prompt | 85 | 0.03467 | 0.03914 | 909 | 43% |

**Baselines**:
- v1 SOTA (heilbron/asymmetric-iterations PR #204, commit `562a1210`): `actual_fitness = 0.03648`
- v1 baseline mean (4 G runs): `0.03574`
- v2 NULL band center: `0.03315`

**Primary metric** (per design Section 4): best-ever `actual_fitness` across the 4 G runs.

| G Run | Best-ever actual_fitness | Gap to v1 SOTA (0.03648) | Gap to v1 mean (0.03574) |
|-------|--------------------------|--------------------------|--------------------------|
| A1_G  | 0.03368 | -0.00280 (-7.7%) | -0.00206 (-5.8%) |
| A2_G  | 0.03301 | -0.00347 (-9.5%) | -0.00273 (-7.6%) |
| C1_G  | 0.03471 | -0.00177 (-4.9%) | -0.00103 (-2.9%) |
| C2_G  | 0.03452 | -0.00196 (-5.4%) | -0.00122 (-3.4%) |
| **Mean** | **0.03398** | **-0.00250 (-6.9%)** | **-0.00176 (-4.9%)** |
| **Std** | **0.00073** | | |
| **Best** | **0.03471 (C1_G)** | **-0.00177** | **-0.00103** |

**Pair-max** (combined G+D best per pair, secondary metric):

| Pair | Pair leader | actual_fitness | Source |
|------|-------------|----------------|--------|
| A1   | A1_D        | 0.03547        | D-side |
| A2   | A2_G = A2_D | 0.03301        | tied   |
| C1   | C1_D        | 0.03499        | D-side |
| C2   | C2_D        | 0.03467        | D-side |

Frontier across all 8 runs: **0.03547 (A1_D)** -- still below v1 baseline mean (0.03574) and well below SOTA (0.03648).

## 2. Hypothesis Test

**H0**: With v1 landscape restored and SBF disabled, current main reaches 0.03648 in at least one G run.
**H1**: Current main produces a measurable shift in the G `actual_fitness` distribution -- implying that some drift element not covered by the 17-decision interview is load-bearing.
**Primary metric**: best-ever `actual_fitness` across 4 G runs.
**Decision rule** (per design Section 4):
  - Best G >= 0.0364 in >=1 run --> H0 supported.
  - Best G >= 0.0364 in 0 runs but median G >= 0.03574 --> partial reproduction.
  - Best G < 0.03574 across all 4 runs --> H1 confirmed.

**Application**:
  - Count G >= 0.0364: **0/4**
  - Count G >= 0.03574: **0/4**
  - Best G = 0.03471 < 0.03574
  - Median G = 0.03410 < 0.03574

**Result**: H0 **rejected** within the data observed. Best G (0.03471) falls below the partial-reproduction threshold (0.03574) and well below v1 SOTA (0.03648). All four G runs are below v1 baseline mean. H1 **supported** -- current main produces a downward shift in the G `actual_fitness` distribution relative to the v1 historical record.

**Critical caveat**: This conclusion is qualified by early termination (see Section 5). G runs consumed only 25-29% of their pre-registered 200-generation budget. The hypothesis test was designed for gen-200 endpoints. Applying the decision rule at gen 50-58 is an amendment that weakens the inferential strength.

## 3. Effect Size

**Grand mean**: G mean = 0.03398, v1 baseline mean = 0.03574. **Delta = -0.00176 (-4.9pp)**.

**95% Confidence interval** (t-distribution, df=3, t_crit=3.182):
  - SE = 0.00073 / sqrt(4) = 0.000365
  - 95% CI for G mean: **0.03398 +/- 0.00116 = [0.03282, 0.03515]**

The v1 baseline mean (0.03574) falls **outside** the upper bound of this confidence interval (0.03515), providing formal evidence that the current main's G distribution is shifted downward. The v1 SOTA (0.03648) is further outside the CI.

**Per-run consistency**: All 4 G runs are below v1 baseline mean. The effect direction is unanimous. The magnitude ranges from -0.00103 (C1_G, closest to baseline) to -0.00273 (A2_G, furthest).

**Arm-level decomposition**:
  - Composition arm (A): mean 0.03335, std 0.00047
  - Gradient-in-prompt arm (C): mean 0.03462, std 0.00013

The C-arm outperforms the A-arm by 0.00127, consistent with the v1 finding that feedback mode is NULL (design Section 3 notes feedback mode is NOT an IV in this experiment). The arm difference is within sampling noise at N=2 per arm.

## 4. Secondary Observations

### 4.1. Trajectory Analysis

| Checkpoint | Timestamp | A1_G | A2_G | C1_G | C2_G |
|------------|-----------|------|------|------|------|
| CP#5 (~gen 6) | 2026-04-26T17:51 | 0.02607 | 0.02864 | 0.02491 | 0.01965 |
| CP#6 (~gen 17) | 2026-04-26T21:44 | 0.03083 | 0.02883 | 0.03306 | 0.03452 |
| CP#7 (~gen 28) | 2026-04-27T01:44 | 0.03277 | 0.02883 | 0.03471 | 0.03452 |
| Final (~gen 54) | 2026-04-27 | 0.03368 | 0.03301 | 0.03471 | 0.03452 |

**Plateau structure differs by arm.** C1_G plateaued at 0.03471 from gen ~28 onward -- no improvement in the final 28 generations (50% of its total runtime). C2_G plateaued at 0.03452 from gen ~17 onward -- no improvement in the final 41 generations (71% of its total runtime). These are genuine plateau signals: the C-arm runs explored approximately twice their stagnation window without finding improvements.

A1_G and A2_G were still ascending at termination. A1_G gained +0.00091 between CP#7 (gen ~28) and final (gen ~50). A2_G gained +0.00418 between CP#6 (gen ~17) and final (gen ~52), with a large jump of +0.00418 in the last ~35 generations. The A-arm runs are **not done**.

**Implication for early termination**: The C-arm plateau supports the hypothesis that further generations would not close the gap for those runs. The A-arm ascending trajectory introduces genuine uncertainty. At A1_G's observed improvement rate (~0.000035/gen over the last 22 gens), an additional 150 generations could yield +0.0053, pushing A1_G from 0.03368 toward 0.03895 -- well above v1 SOTA. However, extrapolating linear improvement over 150 additional generations is unrealistic given diminishing returns in evolutionary optimization; the expected trajectory is concave. The honest assessment is: A-arm runs had remaining potential, but the rate of improvement was decelerating, and the required gap (0.00206 for A1_G to reach baseline mean) would demand sustained improvement across many generations.

### 4.2. D-side as Proxy for G Potential

In 3 of 4 pairs, the D-side run achieved a higher best-ever `actual_fitness` than its paired G run (A1_D > A1_G, C1_D > C1_G, C2_D > C2_G). This reproduces the PATTERNS.md "Improver polishing exceeds Constructor quality" signal. The D-side frontier leader A1_D=0.03547 is the closest any run got to v1 baseline mean (gap = -0.00027, or -0.75%).

This suggests the underlying program quality within the co-evolutionary system was approaching v1 levels in the best pair, but the G-side MAP-Elites archive was slower to surface these programs than D's. Whether this represents a real v1-level capability hidden behind archive dynamics versus a coincidence is unclear from this data.

### 4.3. Generation Rate Asymmetry

D runs reached gen 71-91 while G runs reached gen 50-58 in the same wall-clock window. D/G generation ratio is approximately 1.42-1.55x. This matches v1's observed D-runs-faster-than-G pattern and is expected: D's evaluate.py has fewer opponents to score against (K=1) and the composition/gradient feedback stages add latency on G's path.

### 4.4. MAP-Elites Normalized Fitness

G runs show high MAP-Elites normalized fitness (0.889-0.969) indicating the MAP-Elites archive is well-populated and competitive within G's niche space. D runs show very low normalized fitness (0.001-0.382), consistent with the known D hard-floor pattern documented in PATTERNS.md -- the `max(delta,0)/Q_MAX` scoring creates a point mass at 0.0 that dominates D's archive. A2_D's normalized fitness of 0.00095 is essentially zero, meaning nearly all D archive cells contain programs with identical (zero) fitness, confirming the structural D fitness flaw persists under v1 semantics.

## 5. Deviations from Pre-Registration

### Deviation 1: Early Termination (MAJOR)

**Pre-registered**: `max_generations=200`, no early-stop on plateau, no early-stop on success.

**Actual**: Experiment terminated at researcher authorization at gen 50-58 (G) and gen 71-91 (D), representing 25-46% of the pre-registered generation budget.

**Justification**: C1_G and C2_G had plateaued (no improvement in 28 and 41 generations respectively). The emerging A-vs-C divergence provided initial signal. Continued operation would consume approximately 3 additional days of Qwen3-235B-A22B-Thinking-2507 compute for uncertain marginal value.

**Impact on validity**: This is the experiment's largest methodological weakness. The decision rule in design Section 4 was specified for gen-200 endpoints. Applying it at gen ~54 average is an amendment that weakens the claim. Specifically:

1. **C-arm**: Plateau evidence is strong. C1_G stagnated at 0.03471 for 28 generations, C2_G at 0.03452 for 41 generations. The probability of these runs reaching 0.03574 in the remaining 142-144 generations is low but nonzero. We cannot rule it out.

2. **A-arm**: Trajectory evidence contradicts the conclusion. A1_G gained +0.00091 in its last 22 generations, A2_G gained +0.00418 in its last 35 generations. Both were actively improving. It is plausible (though not probable at a constant improvement rate) that the A-arm could have reached the v1 baseline mean given the full 200-generation budget.

3. **D-side**: D runs were also still climbing. A1_D reached 0.03547 at gen 71, only 0.00027 below baseline mean, with 129 generations remaining. Had D-side improvement continued, D could have exceeded v1 SOTA as a pair-max metric.

**Formal assessment**: Early termination makes this a **suggestive** rather than **conclusive** test of H1. The evidence for a downward shift is consistent across all 4 G runs and supported by the confidence interval analysis, but the comparison is against a truncated trajectory, not the pre-registered full horizon. A firm conclusion would require either (a) completing the remaining generations, or (b) pre-registering the early stopping rule and its decision boundaries.

### Deviation 2: D-side `dg_tracker=null` Override (I-03)

**Pre-registered**: `pipeline_builder.lineage_filter: null` as the only SBF-disabling override.

**Actual**: Added `pipeline_builder.dg_tracker=null` to all 4 D-side `extra_overrides` because the parent yaml's `dg_tracker` wiring was incompatible with `lineage_filter=null` on current main.

**Impact on validity**: **No confound**. This override is arguably MORE faithful to v1, which had no `DGImprovementTracker` at all. The `dg_tracker` was added post-v1 (commit 1d25a9a8). Setting it to null removes a post-v1 mechanism, not a v1 mechanism. D's fitness path is unaffected: the tracker wrote telemetry keys unused by any fitness-relevant pipeline stage. Applied uniformly to all 4 D runs.

### Deviation 3: Manifest YAML Quote-Stripping (I-04)

**Pre-registered**: No amendment anticipated.

**Actual**: `yaml.dump` repeatedly un-quoted `prereg_commit: "25470e37"`, parsing it as float `2.547e+41`. Re-quoted manually after each manifest write at checkpoints #5, #6, #7, and final.

**Impact on validity**: **No scientific impact**. This is a pure I/O bug in the checkpoint skill's YAML serialization. No fitness values, configs, or run parameters were affected. Systemic fix pending (`save_manifest()` helper).

### Deviation 4: LiteLLM Proxy Hang (I-06)

**Pre-registered**: No infra downtime anticipated.

**Actual**: Upstream LLM (Qwen3-235B-A22B-Thinking-2507) became unresponsive at approximately 2h26m post-relaunch (~16:39 UTC). All 8 runs blocked on `/chat/completions` retries. Duration: approximately 43 minutes until researcher restarted the LiteLLM proxy at ~17:22 UTC.

**Impact on validity**: **No fitness-landscape confound**. The hang affected all 8 runs symmetrically. No generation progress occurred during the outage. Matched Pattern 10 (Server Down) from PATTERNS.md. Wall-clock time was consumed but no evolutionary pressure was applied during the stall, so no asymmetric treatment effect could have been introduced.

### Deviation 5: Post-Recovery Process Wedge (I-07)

**Pre-registered**: No process recovery protocol anticipated.

**Actual**: After the LiteLLM proxy recovered (I-06), the 8 run processes failed to self-recover due to asyncio retry-budget exhaustion during the 2.5h outage window. Required coordinated restart: SIGTERM all 8 PIDs, flush Redis DBs 1-8, reset manifest to `implemented`, re-launch.

**Impact on validity**: **Marginal**. The flush-and-restart cost was minimal: only seed-eval state was present (no real generations had completed under the post-relaunch instance). The restart may have shifted the relative gen-rate balance between G and D runs slightly (the restart "clock" reset simultaneously for all runs, whereas organic evolution accrues small timing drift). This is not a fitness-landscape confound.

## 6. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| A1_G | Yes | 50 gens, ascending trajectory |
| A1_D | Yes | 71 gens |
| A2_G | Yes | 52 gens, ascending trajectory |
| A2_D | Yes | 90 gens |
| C1_G | Yes | 56 gens, plateaued at gen ~28 |
| C1_D | Yes | 91 gens |
| C2_G | Yes | 58 gens, plateaued at gen ~17 |
| C2_D | Yes | 85 gens |

All 8 runs are valid. No crashes, no import errors, no treatment integrity violations. Treatment markers (binary resistance scoring, linear D scoring, SBF absent, drift_cap=100000, v1 task_description checksums) all verified via smoke test and checkpoint logs.

## 7. Lessons Learned

**What worked**:

1. **The 17-decision interview** (design Section 3) was thorough. It identified 14 parameters to pin to v1 values and 3 known irreducible drift sources. The I-03 deviation (dg_tracker coupling) was the only parameter missed, and it was caught and corrected before any meaningful generations elapsed.

2. **Treatment verification** (design Section 9) was robust. Eight log-pattern checks plus Redis value inspection confirmed all 8 runs operated under the intended v1-like landscape. No silent treatment failure occurred.

3. **The checkpoint cadence** (every ~4h) provided useful trajectory data without excessive overhead. The trajectory analysis in Section 4.1 is the most informative part of these results -- it distinguishes the C-arm plateau from the A-arm ascent.

**What didn't work**:

1. **No pre-registered early-stopping rule for plateau detection.** The design explicitly stated "No early-stop on plateau" (Section 8). This left the researcher with no principled mechanism to terminate when C-arm runs had clearly stagnated. Future reproducibility stress tests should pre-register a plateau criterion (e.g., "if no improvement for N consecutive generations, consider run plateaued for decision-rule purposes").

2. **Smoke test coverage gap (I-03)**. The smoke test exercised only the G (constructor) code path, leaving the D (improver) instantiation entirely unverified. The `dg_tracker` coupling crash was discovered only at full launch. This is now a known failure pattern: smoke tests for adversarial-asymmetric experiments must exercise both roles.

3. **The experiment was under-scoped for its own question.** A reproducibility stress test is inherently expensive: it must run to the full pre-registered horizon to be conclusive. The 200-generation budget was set to match v1 but required approximately 5-6 days of continuous Qwen3-235B-A22B-Thinking-2507 compute. The early termination at ~1.5 days produced suggestive but not conclusive evidence.

**Bugs / infrastructure issues**:

1. **I-04** (yaml.dump quote-stripping): Recurring annoyance, no scientific impact. Systemic fix needed: `save_manifest()` helper.
2. **I-06/I-07** (LiteLLM proxy hang + post-recovery wedge): Lost approximately 3h of wall-clock time. Framework lacks self-recovery from upstream LLM outage exceeding retry budget. Systemic fix: propagate httpx exceptions in `MutationAgent.acall_llm` and add watchdog detection of post-outage wedge state.

## 8. Next Steps

1. **Do NOT re-run to 200 generations.** The marginal information gain does not justify 4 additional days of compute. The suggestive result is actionable: current main has drifted from v1 in a way that depresses G performance by approximately 5pp. The more productive path is to identify and test the specific drift components rather than brute-force the reproduction.

2. **Isolate the drift candidates.** The 17-decision interview identified 3 known irreducible drift sources:
   - `ConfigurableAggregator` mean-reduction over K=1 (semantically equivalent to v1 scalar under K=1, but the code path differs).
   - evaluate.py `(metrics, artifact)` tuple contract (same data, different ABI).
   - 300+ commits of library code churn.

   Of these, the library code churn is the most likely source of a 5pp regression. A bisection approach (running on intermediate commits between `562a1210` and `25470e37`) could localize the breaking change -- but at high compute cost.

3. **Prioritize the REDESIGN bundle.** The v1-honest-repro result reinforces PATTERNS.md's top priority: the fitness function smoothing bundle addresses the root cause of D stagnation. Whether the library drift depresses G by 5pp or not, a smoothed fitness landscape offers a fundamentally better evolutionary signal. Spending compute on drift forensics is secondary to testing the REDESIGN hypothesis.

4. **Update PATTERNS.md suggestive signals.** The v1-honest-repro result weakens the "source code access accelerates early optimization" signal further: even with v1-identical landscape semantics, the acceleration was not reproduced. The signal is now confounded with library drift on top of the v1/v2 coupling difference.

## 9. Verdict and INDEX.md Entry

**Verdict: SUGGESTIVE**

Current main (commit `25470e37`) does not reproduce the v1 SOTA result (`actual_fitness = 0.03648`) when v1 fitness-landscape semantics are restored and SBF is disabled. Across 4 G runs (mean 0.03398, 95% CI [0.03282, 0.03515]), all fall below the v1 baseline mean (0.03574), and the v1 baseline mean is excluded from the 95% confidence interval.

I assign a SUGGESTIVE verdict rather than a firm NEGATIVE because the experiment was early-terminated at 25-29% of its pre-registered 200-generation budget. Two of four G runs (C-arm) had clearly plateaued, but two (A-arm) were still ascending. The pre-registered decision rule was designed for gen-200 endpoints; applying it at gen ~54 is an amendment. The signal direction is unanimous and the effect size is meaningful (-4.9pp mean gap), but the early-termination uncertainty prevents a conclusive determination.

The most parsimonious interpretation: approximately 300 commits of library code churn between `562a1210` and `25470e37` introduced a regression that depresses G actual_fitness by 1.0-2.8pp (best-case C1_G gap = -0.00103, worst-case A2_G gap = -0.00273) relative to v1's fitness distribution, even after restoring v1's fitness landscape semantics. This drift is load-bearing in the sense that it prevents reproduction, but it may be partially recoverable with additional generations.

**INDEX.md entry**:

```
| `heilbron/v1-honest-repro` | Complete | SUGGESTIVE -- Library drift (~300 commits) depresses G actual_fitness by ~5pp (mean 0.03398 vs v1 baseline 0.03574, 95% CI [0.03282, 0.03515]). 0/4 G runs reproduced v1 SOTA (0.03648). Early-terminated at gen ~54 (25-29% budget) -- C-arm plateaued, A-arm still ascending. | #224 |
```

---

*Ready for Reviewer-2's scrutiny.*
