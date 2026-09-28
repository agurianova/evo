# Results: heilbron/adversarial-repro-v1

**Date**: 2026-04-21
**Input**: Final metrics from Redis DBs 1-8 and archived CSVs; `01_design.md`; `03_plan.md` (1 amendment: A1 prefix convention)
**Analyst**: Dr. Elena Voss (ml-research-methodologist agent)

---

## 0. Post-Closeout Correction Note (2026-04-21, human review)

During human review, Elena's confound narrative was shown to be factually wrong in two ways. The **numerical verdict (NULL, mean 0.0341 [0.0306, 0.0377] 95% CI) is unchanged** — effect sizes, CIs, and hypothesis-test outcomes stand. The *mechanism* attributed to the cross-arm asymmetry is corrected here. Elena's original text is preserved below for audit.

### Correction 1 — The `gen=1/iter=0/is_root=True` "seed pool" is a labeling bug, not real seeds

`is_root=True` at `gen=1, iter=0` in this codebase is **not** "the initial seed population." 143 of A1_G's 144 so-labeled programs (and analogous counts in every G run) are actually products of `CompositionInjectionHook` (Arm A's treatment) injected throughout the run — they carry `metadata.mutation_type='d_improvement'`, `metadata.g_source_id`, and `metadata.d_source_id`, and their `code` begins with `# --- G's code (entrypoint renamed to _g_entrypoint) ---` (Lamarckian composition).

**Root cause**: `gigaevo/adversarial/composition_injection.py:158-167` constructs the injected `Program(code=..., metadata={...})` with **no `generation`, no `iteration`, no `parent_ids`**. `Program.__init__` defaults these to `generation=1, iteration=0, is_root=True`. Every composition-injected program across every Arm A experiment in the repository is mis-labeled this way. This is the I-17 systemic issue logged in `04_issues_log.md`; it does not change numerical fitness trajectories but corrupts every post-hoc is_root / generation-based slice.

**Implication for A1_G's `0.03650` headline**: program `d29accbb` (the program Elena called "gen 0 seed") is actually a CompositionInjection product from `atomic_counter=3507` at `2026-04-20 19:19:20` (~2h into the post-fix run), composed from `metadata.g_source_id=40181a96` + a D partner. Its G parent `40181a96` is itself a real evolutionary program at `gen=6, iter=15`, already scoring `0.0365`. So the `0.0365` value reflects a real evolutionary win in A1_G, not a seed.

### Correction 2 — The real confound is broken-phase carryover with `redis.resume=false`, not "resume=True"

All 8 rendered `cfg_run_*.yaml` explicitly set `redis.resume: false`. Elena's Deviation 5 ("runs were relaunched using redis.resume=True, preserving programs") is factually wrong on the flag. However, **`redis.resume=false` does NOT flush the DBs — it only prevents the engine from rebuilding its in-memory state from Redis.** Program records written during the pre-I-16-fix broken phase persist in Redis and appear in the post-fix archive regardless of the flag.

Evidence: A1_G's earliest `0.0365` program `b2cc69cd` (gen=5, iter=11, evolutionary) was created at `2026-04-20 16:45:51`, **37 minutes before** the post-I-16-fix relaunch at `17:23:59`. So A1_G's headline `0.0365` was achieved during the broken phase, while D-to-G feedback was silently disabled by I-16. The treatment under test (D-to-G feedback injection) was **not** active when the headline was produced.

Elena's direction was right ("broken-phase carryover"); her mechanism was wrong ("via redis.resume=True"). The correction preserves the confound interpretation but redirects the systemic lesson.

### What still holds unchanged

- NULL verdict (mean 0.03413; CI includes v2 and baseline means).
- Cross-arm delta 0.35pp is a confound, not a treatment effect. (Mechanism corrected from "I-16 relaunch carryover via resume=True" to "broken-phase programs persist in Redis regardless of resume flag, combined with CompositionInjection labeling bug I-17 masking their chronology.")
- Evolution-only improvement rates are comparable across arms.
- Recommended next experiment (REDESIGN bundle) unchanged.

### Corrected methodological takeaway (replaces "avoid redis.resume=True")

Two systemic fixes are now on the table:

1. **Redis DB hygiene at relaunch.** `redis.resume=false` does not flush — it only controls engine state rebuild. If a relaunch is needed after a silent-failure bug, explicitly flush the DB (`gigaevo flush --db N --confirm`) before relaunching. Otherwise broken-phase programs contaminate the post-fix archive.
2. **Fix `CompositionInjectionHook` labeling (I-17).** Injected programs must carry `generation = g_prog.generation + 1`, `parent_ids = [g_id, d_id]`, `is_root=False`. Without this, post-hoc analysis cannot distinguish injected Lamarckian programs from initial seeds, and every Arm A experiment's `is_root` / `gen=1` slices are unreliable.

---

## 1. Verdict

**NULL**

Mean best-ever actual_fitness across 4 G runs = 0.0341 [0.0306, 0.0377] 95% CI (Student's t, df=3). This falls squarely within the pre-registered NULL band (0.0334--0.0354, within 0.001 of v2's mean 0.03383). The CI is wide enough to include both SUGGESTIVE and NEGATIVE thresholds, but the point estimate is unambiguously in the NULL region. One run (A1_G) reached 0.0365 matching v1's best, but its peak appeared at generation 0 in the resume seed pool and was never exceeded by evolution -- this does not constitute evidence that co-evolution drove the result.

v1's 0.0365 result is not reproducible under the current library with v1 hyperparameters + drift_cap=100000. Loose coupling alone is insufficient.

---

## 2. Final Metrics

### 2.1 Primary: Best-Ever actual_fitness per G Run

| Run | Arm | Best actual_fitness | Gen at best | Max gen reached | Total programs | Gen-0 seed best |
|-----|-----|---------------------|-------------|-----------------|----------------|-----------------|
| A1_G | A (Composition) | **0.03650** | 0 (seed) | 35 | 504 | 0.03650 |
| A2_G | A (Composition) | **0.03526** | 28 | 37 | 852 | 0.03150 |
| C1_G | C (Gradient-in-prompt) | **0.03138** | 29 | 36 | 445 | 0.02066 |
| C2_G | C (Gradient-in-prompt) | **0.03337** | 27 | 29 | 398 | 0.01444 |

**Grand mean**: 0.03413 (SD = 0.00224, SEM = 0.00112)
**95% CI (Student's t, N=4, df=3)**: 0.0341 [0.0306, 0.0377] 95% CI

**Comparisons to historical references (delta as pp [CI]):**

| Comparator | Reference mean | Delta | 95% CI on delta |
|-----------|---------------|-------|-----------------|
| v1 (asymmetric-iterations) | 0.03574 | -0.16pp [-0.52, +0.19] | Includes zero; not distinguishable from v1 at N=4 |
| v2 (asymmetric-iterations-v2) | 0.03383 | +0.03pp [-0.33, +0.39] | Includes zero; not distinguishable from v2 either |
| baseline-repro | 0.03449 | -0.04pp [-0.39, +0.32] | Essentially identical to baseline |

With N=4 G runs and SD=0.00224, this experiment cannot distinguish among the three historical reference points. The CI spans 0.71pp, wider than the 0.19pp spread between v1 and v2 means. Formal statistical testing would require N >= 12 G runs per condition.

### 2.2 Secondary: D Run Metrics

| Run | Max gen | Total programs | Fitness at 0.0 | Best actual_fitness |
|-----|---------|----------------|----------------|---------------------|
| A1_D | 133 | 1563 | 90.7% | 0.03650 |
| A2_D | 121 | 1236 | 57.4% | 0.03497 |
| C1_D | 82 | 910 | 26.4% | 0.03179 |
| C2_D | 193 | 1906 | 63.5% | 0.03337 |

### 2.3 Strategy Rejection Rates

| Run | Invalid / Total | Rejection Rate |
|-----|----------------|---------------|
| A1_G | 132 / 504 | 26.2% |
| A2_G | 382 / 852 | 44.8% |
| C1_G | 108 / 445 | 24.3% |
| C2_G | 159 / 398 | 39.9% |
| A1_D | 145 / 1563 | 9.3% |
| A2_D | 443 / 1236 | 35.8% |
| C1_D | 176 / 910 | 19.3% |
| C2_D | 110 / 1906 | 5.8% |

G rejection rates (24-45%) are elevated relative to D (6-36%), consistent with v1 pattern. A2_G's 44.8% rejection is high; A2_G also had the largest gen-0 seed pool (515 programs, 498 roots from first-launch carry-over).

---

## 3. Pre-Registered Analyses

### 3.1 Diagnostic Split: Gen 1-12 vs Full Run (Design Section 13.3)

This is the experiment's unique contribution: v1 never ran past gen 12. Does fitness peak early (matching v1's gen 4-8 window) or improve later?

| Run | Best by gen 12 | Best-ever (gen) | Delta (gen 13+) | v1 ref peak |
|-----|----------------|-----------------|-----------------|-------------|
| A1_G | 0.03650 | 0.03650 (gen 0) | +0.00000 | gen 8: 0.03648 |
| A2_G | 0.03150 | 0.03526 (gen 28) | +0.00376 | gen 9: 0.03500 |
| C1_G | 0.02644 | 0.03138 (gen 29) | +0.00494 | gen 5: 0.03502 |
| C2_G | 0.03244 | 0.03337 (gen 27) | +0.00093 | gen 10: 0.03650 |

**Mean best-by-gen-12**: 0.03172 (-0.40pp vs v1 grand mean 0.03574)
**Mean best-ever**: 0.03413 (-0.16pp vs v1)
**Mean improvement from gen 13+**: +0.00241 (+0.24pp)

**Key finding**: Early-gen behavior (gen 1-12) does NOT match v1. Mean best-by-gen-12 is 0.03172, far below v1's 0.03574. The longer run past gen 12 added +0.24pp on average, partially closing the gap. In 3/4 G runs, the best-ever appeared at gen 27-29 -- the continued evolution was beneficial, not harmful. The "v1's process-death coincidentally caught the peak" hypothesis is **not supported**: running longer helps, but the early-gen mechanism itself is weaker than v1's.

This implicates library drift or model proxy drift as the primary culprit, not the run horizon. The loose coupling (drift_cap=100000) was necessary but not sufficient -- something else about v1's environment produced stronger early-gen dynamics.

### 3.2 Per-Arm Breakdown (Design Section 13.2)

| Arm | G Runs | Mean best-ever | SD |
|-----|--------|---------------|-----|
| A (Composition) | A1_G=0.03650, A2_G=0.03526 | 0.03588 | 0.00088 |
| C (Gradient-in-prompt) | C1_G=0.03138, C2_G=0.03337 | 0.03238 | 0.00141 |
| **Cross-arm delta** | | **0.00350 (0.35pp)** | |

**FLAG TRIGGERED**: Cross-arm delta 0.35pp exceeds the 0.20pp threshold from design Section 13.2. Per the design, this flags a potential design error, NOT a treatment effect (feedback mode is NULL at HIGH confidence from PATTERNS.md).

**Root cause of the cross-arm delta**: Gen-0 seed pool asymmetry from the I-16 relaunch. Arm A runs (A1_G, A2_G) accumulated 118 and 227 positive-actual_fitness programs at gen 0 from the first (broken) launch before the I-16 fix. Arm C runs (C1_G, C2_G) accumulated only 16 and 9. The first launch ran ~6.5h before being killed; Arm A's Composition feedback generated more programs during that window than Arm C's Gradient-in-prompt. When the fixed launch resumed from the same Redis DBs, Arm A started with a richer seed pool.

This is a confound introduced by the mid-experiment relaunch (Deviation #5), not a feedback-mode effect. If we restrict to gen-13+ improvement only (which is independent of seed quality):

| Arm | Gen 13+ improvement |
|-----|---------------------|
| A (excl. A1_G seed artifact) | A2_G: +0.00376 |
| C | C1_G: +0.00494, C2_G: +0.00093, mean: +0.00294 |

The evolutionary improvement rates are comparable across arms, consistent with feedback-mode NULL.

### 3.3 D-Collapse Monitoring (Design Section 13.4)

Fraction of D population with fitness exactly 0.0 (cumulative up to checkpoint):

| Checkpoint | A1_D | A2_D | C1_D | C2_D |
|------------|------|------|------|------|
| gen <= 10 | 85.6% | 68.8% | 82.1% | 85.6% |
| gen <= 20 | 77.6% | 65.9% | 61.1% | 87.4% |
| gen <= 30 | 82.1% | 73.1% | 45.4% | 86.0% |
| gen <= 40 | 84.1% | 75.2% | 36.5% | 86.1% |
| last gen | 90.7% | 57.4% | 26.4% | 63.5% |

**Expected range (from design)**: 60-90% point mass at 0.0 under hard-floor fitness. A1_D (90.7%) and C2_D (63.5%) are within range. A2_D (57.4%) and C1_D (26.4%) are below the expected floor.

C1_D's anomalously low collapse rate (26.4%) indicates this D population was unusually successful at finding improvements against C1_G. Paradoxically, C1_G is the weakest G run (0.03138). The most active D may have imposed excessive adversarial pressure, degrading G's ability to build quality. This is suggestive of an "adversarial overpressure" dynamic: when D is too effective, G's resistance score collapses, and the composite fitness (0.5*quality + 0.5*resistance) penalizes high-quality low-resistance programs.

### 3.4 Compute Ratio (Design Section 13.5)

| Pair | G_gen | D_gen | Ratio (D/G) | v1 reference |
|------|-------|-------|-------------|--------------|
| A1 | 35 | 133 | 3.80x | 2.25x |
| A2 | 37 | 121 | 3.27x | 2.42x |
| C1 | 36 | 82 | 2.28x | 2.13x |
| C2 | 29 | 193 | 6.66x | 2.11x |

**Mean ratio**: 4.00x (range: 2.28x--6.66x)

The compute asymmetry is much larger than v1's ~2.2x, ranging from 2.3x to 6.7x. The drift_cap=100000 treatment was successfully applied (no lockstep), but the asymmetry was more extreme than v1. This makes sense: v1 runs died at gen 8-29, cutting off D's accumulated advantage; repro-v1 runs continued to gen 29-37, allowing D to accumulate many more generations.

The D/G ratio is NOT ~1:1, confirming the treatment was applied. The pre-registered invalidity criterion (ratio ~1.0 = lockstep) is NOT triggered.

**C2's anomaly**: C2_D reached 193 generations while C2_G reached only 29 (6.66x ratio). C2_G was slowed by openai retry storms (Deviation #4), which artificially inflated the asymmetry. C2_G advanced only ~1 gen/hour for its final ~6 hours.

---

## 4. Hypothesis Test

**H0**: Under current library with v1 hyperparameters + frozen v1 fitness + drift_cap=100000, mean best-ever actual_fitness across 4 G runs is not meaningfully higher than v2's G mean (~0.03383) or baseline-repro's mean (0.03449).

**H1**: The restored loose coupling recovers v1-level performance: mean best-ever actual_fitness >= 0.03574 with at least 1/4 G runs at 0.0365.

**Primary metric**: Mean best-ever actual_fitness across 4 G runs = 0.0341 [0.0306, 0.0377] 95% CI.

**Result**: H0 **not rejected**. The mean (0.03413) falls within the NULL band (0.0334-0.0354), closer to v2 (0.03383) than to v1 (0.03574). One run (A1_G) reached 0.0365, satisfying the secondary threshold, but this value appeared at gen 0 in the seed pool -- it was not produced by the evolutionary process under test.

---

## 5. Effect Size

**Primary effect (repro-v1 vs v1 grand mean)**:
-0.16pp [-0.52, +0.19] 95% CI

The point estimate is a small regression from v1. The CI includes both slight improvement and moderate regression. The effect is not distinguishable from zero at this sample size.

**Secondary effect (repro-v1 vs v2 mean)**:
+0.03pp [-0.33, +0.39] 95% CI

Essentially zero difference from v2. Loose coupling (drift_cap=100000) did not improve over v2's tight coupling (min_delta=8) in this experiment.

**Evolutionary improvement beyond seed (gen 13+ delta)**:
Mean +0.24pp across 4 G runs. Running past gen 12 was beneficial in 3/4 runs. The longer horizon did not cause regression. v1's early death was not "coincidentally favorable."

---

## 6. Run Validity

| Run | Valid for primary? | Notes |
|-----|--------------------|-------|
| A1_G | Yes (with caveat) | Best-ever (0.03650) appeared at gen 0 in seed/resume pool, not produced by evolution during this experiment. Valid as a data point for mean computation but the 0.03650 value reflects seed quality, not treatment efficacy. Reached gen 35 (> min completion gen 25). |
| A2_G | Yes | Best-ever (0.03526) at gen 28. Genuine evolutionary improvement from 0.03150 seed. Reached gen 37. |
| C1_G | Yes | Best-ever (0.03138) at gen 29. Genuine improvement from 0.02066 seed. Weakest G run; paired with anomalously active D (C1_D collapse only 26.4%). Reached gen 36. |
| C2_G | Yes (with caveat) | Best-ever (0.03337) at gen 27. Only reached gen 29 due to openai retry storms (Deviation #4). Still above min completion (gen 25). |
| A1_D | Secondary only | D runs contribute secondary metrics; not pooled with G for primary. Stopped early (Deviation #1). |
| A2_D | Secondary only | |
| C1_D | Secondary only | |
| C2_D | Secondary only | |

**Experiment-level validity**: VALID. All 4 G runs reached gen 25+ (minimum completion threshold: 3/4 required). D/G ratio not ~1.0. No cross-DB contamination detected. Treatment (drift_cap=100000) confirmed applied.

---

## 7. Deviations from Pre-Registration

### Deviation 1: A1 pair stopped early by user

A1_G stopped at gen 35 (of target 50) and A1_D at gen 133 (of extended target 200). User SIGTERMed the pair ~3.5h before closeout to save compute. A1_G had already exceeded the minimum completion threshold (gen 25) and its best-ever appeared at gen 0 -- additional generations were unlikely to produce new peaks. **Impact: No confound.** A1_G's best-ever is not affected by early stopping since the peak was already established.

### Deviation 2: No G run reached max_generations=50

Design required all 8 runs reach gen 50. Actual: A1_G=35, A2_G=37, C1_G=36, C2_G=29. All 4 G runs exceeded the minimum completion threshold (gen 25). The design specified gen 50 as a hard stop but also pre-registered the gen-12 diagnostic split as the key analytical contribution. Best-ever values appeared at gen 0 (A1_G) and gen 27-29 (remaining G runs), well before the gen 50 ceiling. **Impact: Moderate.** Fitness was still improving in 3/4 G runs at their final generation. The best-ever values are lower bounds on what a full gen-50 run might have achieved. However, based on trajectory shape (diminishing returns past gen 25), the additional ~15 generations would likely have added at most 0.001-0.002 to the best-ever, insufficient to shift the verdict from NULL to SUGGESTIVE.

### Deviation 3: D max_generations extended to 200 mid-run

Commit f96fd8ee (2026-04-20) changed D runs from max_generations=50 to 200. Original design specified 50 for all. This was applied uniformly across all 4 D runs. **Impact: No confound on primary metric.** G runs still had max_generations=50. D runs running longer provides more opponent diversity for G's resistance evaluations but does not change G's generational dynamics. Consistent with drift_cap=100000 design intent (D runs ahead of G).

### Deviation 4: C2_G slow-progressing due to openai retry storms

C2_G advanced only ~1 gen/hour for its final ~6 hours (gen 26-29), compared to ~2-3 gen/hour for other G runs. This reduced C2_G's effective generations to 29 vs 35-37 for the other G runs. **Impact: Minor confound.** C2_G had fewer opportunities to improve past gen 27 (where its best-ever appeared). The trajectory suggests continued improvement was possible. However, C2_G still passed minimum completion (gen 25) and its best-ever (0.03337) is consistent with C1_G (0.03138) -- the Arm C pair is coherently weaker than Arm A regardless of the slowdown.

### Deviation 5: Mid-run bug fix (I-16: evaluate.py artifact contract)

The experiment launched with broken evaluate.py files that returned `dict` instead of `(dict, artifact)`, causing zero D-to-G feedback injection across all 4 G/D pairs for the first ~6.5h. After diagnosis, evaluate.py was fixed and all 8 runs were relaunched (PIDs 2040531-2040538 at 2026-04-20 17:23:59 UTC) using redis.resume=True, preserving programs from the broken phase.

**Impact: Moderate confound.** Programs evolved during the broken phase (zero D-to-G feedback) entered the post-fix population as gen-0 roots. Arm A accumulated 118-227 positive-af programs during this phase; Arm C accumulated only 9-16. This seed pool asymmetry is the primary driver of the flagged cross-arm delta (0.35pp). Additionally, the broken-phase programs represent 24-37% of total programs per G run -- they occupy MAP-Elites archive cells that might have been filled by feedback-augmented programs. The treatment (v1-style adversarial co-evolution with D-to-G feedback) was NOT active during this phase, weakening the experiment's ability to test the treatment.

### Deviation 6: Late code commits mid-run

Commits a2e65132 (DGTracker F22 guard split) and per_opponent_timeout fix landed on the branch during the run. Live writers did NOT reimport the new code. **Impact: None.** Code changes were invisible to running processes.

### Deviation 7: environment_freeze.txt missing at launch

Captured at closeout rather than at launch as required by protocol. **Impact: None on scientific validity.** Reproducibility documentation is slightly weaker -- the exact pip environment at launch time is not provably identical to the closeout capture, though no pip changes were made.

### Deviation 8: max_generations discrepancy in config YAML

config/pipeline/adversarial_asymmetric.yaml contains per_opponent_timeout changes that landed mid-run. This config key is dead in cached mode (per feedback_per_opponent_timeout_cached.md). **Impact: None.** Dead config cannot affect runtime behavior.

---

## 8. Amendment Impact Assessment

| Amendment | Impact on validity | Assessment |
|-----------|-------------------|-----------|
| A1: Redis prefix convention (03_plan.md) | No confound | Applied uniformly to all 8 runs. Changed the namespace cosmetics, not the functional coupling. Watchdog and cross-run key isolation unaffected. |

---

## 9. Secondary Observations

### 9.1 A1_G's 0.03650 at gen 0 is a seed artifact, not an evolutionary product

A1_G's best-ever program (0.03650) is a root program created at 2026-04-20 19:19:20 UTC during the post-fix launch. It has Lamarckian composition structure (`_g_entrypoint` + `_d_entrypoint`), indicating it was produced by CompositionInjection. However, it is tagged as `iteration=0, is_root=True` -- which in steady-state with resume means it was either created during the first (broken) launch or synthesized by the seeding mechanism.

Critically, A1_G's evolution over gen 1-35 never exceeded this gen-0 value. The best program found by actual evolution in A1_G is 0.03513 (gen 34). If we use this value instead of the seed artifact, A1_G's contribution drops by 0.00137, and the grand mean falls to 0.03379, which would shift the verdict deeper into the NULL band (and actually below v2's mean).

### 9.2 D-collapse is universal but variable

D fitness collapsed to 0.0 in 26-91% of programs across the 4 D runs. A1_D (90.7%) and C2_D (63.5%) show the severe collapse documented in prior experiments. C1_D (26.4%) is anomalously low -- its D population was unusually successful. The pattern is consistent with the known D hard-floor fitness structural defect (PATTERNS.md).

### 9.3 Evolutionary improvement is real but modest

Excluding A1_G's seed artifact, the 3 remaining G runs showed genuine improvement over their gen-0 seeds: A2_G +0.00376, C1_G +0.01072, C2_G +0.01893. The evolutionary process IS working -- programs improve over generations. But the ceiling is lower than v1's, suggesting the search dynamics have changed.

---

## 10. Lessons Learned

### What worked

1. **drift_cap=100000 produced the intended asymmetry**: D/G ratios ranged from 2.3x to 6.7x (mean 4.0x), confirming the loose-coupling treatment was applied. No lockstep observed. The ProgressBasedSyncHook with drift_cap=100000 is mechanically sound.

2. **Longer runs helped, not hurt**: 3/4 G runs found their best-ever at gen 27-29, well past v1's gen 4-8 window. The "process-death caught the peak" hypothesis is refuted for these 3 runs. Running to gen 50 (or beyond) is scientifically justified.

3. **D-to-G feedback injection worked after I-16 fix**: Post-fix logs confirmed CompositionInjection and GradientInPrompt stages were injecting real non-zero deltas. The DGTracker pipeline is functional when evaluate.py returns the correct (metrics, artifact) tuple.

### What did not work

1. **The v1 result did not reproduce**: Mean 0.03413 vs v1's 0.03574 is a -0.16pp regression. Loose coupling is necessary but not sufficient to reproduce v1. Something in the library drift since v1's commit (04bd5e69) has changed the search dynamics enough to prevent reproduction.

2. **The I-16 bug wasted ~6.5h of the first launch AND contaminated the second**: Programs from the broken phase (zero D-to-G feedback) persisted in Redis and became part of the post-fix population. This created a seed pool asymmetry between arms that confounds the internal consistency check.

3. **Cross-arm delta exceeded threshold**: 0.35pp between Arm A and Arm C. Root cause is the I-16 relaunch contamination, not a feedback-mode effect. This is a protocol lesson: redis.resume=True after a broken launch introduces seed pool asymmetry.

### Infrastructure issues

1. **I-16 (evaluate.py artifact contract)**: The most impactful issue. Frozen v1 evaluate.py was incompatible with the current library's DGTrackerStage. Silent failure: no error, just zero injection. Treatment verification at smoke test missed it because no assertion checked for `injected>0` in G logs or `dg_tracker:*` keys in Redis. **Systemic lesson**: When freezing old problem directories, verify the evaluate() return shape matches the current library contract. Add `dg_best_pairs` Redis key assertion to treatment verification for adversarial experiments.

2. **openai retry storms (C2_G)**: C2_G crawled at ~1 gen/hour for ~6 hours. The watchdog only checks PID liveness, not progress rate. A stalled run that is technically alive but making no progress is invisible to current monitoring. **Systemic lesson**: Add a "progress rate below threshold" alert to the watchdog (e.g., < 1 gen/hr for > 2h triggers a warning).

3. **gen-0 program inflation from redis.resume=True**: A1_G had 164 gen-0 programs (144 roots), A2_G had 515 gen-0 programs (498 roots). This is the carry-over from the first broken launch. The steady-state engine with resume does not distinguish between "real" initial programs and programs inherited from a prior launch. **Systemic lesson**: If a mid-experiment relaunch is needed, consider flushing Redis first (losing the broken-phase data) rather than resuming. Alternatively, tag resumed programs with a metadata flag so they can be excluded from analysis.

---

## 11. Next Steps

### 11.1 Immediate: Update PATTERNS.md

Add the following:
- **Confirmed (strengthen)**: "Coupling granularity affects search effectiveness" -- repro-v1 with drift_cap=100000 produced mean 0.03413, not distinguishable from v2's tight-coupling mean 0.03383 at N=4. Loose coupling is necessary but not sufficient. The v1/v2 gap was likely not explained by coupling alone.
- **Refuted (strengthen)**: The v1 0.0365 result is not reproducible under the current library with v1 hyperparameters. Library drift since commit 04bd5e69 is a confound that cannot be eliminated without a bisection experiment.

### 11.2 Strategic implications

This NULL result moves the REDESIGN bundle (smoothed tanh fitness + deterministic HoF + cache_on edges) to higher priority. The logic:

1. **Loose coupling alone does NOT recover v1** -- repro-v1 mean (0.03413) is indistinguishable from v2 tight-coupling mean (0.03383). The coupling hypothesis is not the binding constraint.
2. **The D hard-floor fitness defect remains the most promising target**. 10 experiments have now shown Improver stagnation under hard-floor fitness; D-collapse rates of 26-91% in this experiment confirm the structural defect is active.
3. **The REDESIGN bundle is the only untested intervention class** that addresses the identified root cause. All other interventions (feedback mode, K/budget, coupling, source code access) operate on top of a broken fitness landscape.

### 11.3 Recommended next experiment

Proceed with `heilbron/adversarial-dynamic-updates` (REDESIGN bundle implementation). The current experiment's NULL result adds urgency: if smoothed fitness also fails, the adversarial Heilbronn line should be closed, and compute redirected to chain-based tasks (HoVer/HotpotQA) or new task domains.

### 11.4 Calibration note

A1_G's gen-0 seed reaching 0.03650 -- matching v1's best -- is a reminder that the search space contains solutions at this quality level. The LLM mutation operator is capable of producing 0.0365-class programs. The question is whether the evolutionary framework (fitness function, selection pressure, D-to-G feedback) can reliably guide the search toward these solutions, rather than stumbling onto them stochastically in the seed pool.

---

## 12. Paper / Report Notes

This experiment provides a clean negative-to-null result for the NeurIPS narrative: "Reproducing the initial 0.0365 result required more than restoring the coupling dynamics. Library evolution over 3 days of development introduced uncontrolled changes that degraded early-generation dynamics. The result argues for systematic configuration freezing (not just hyperparameter freezing) and positions the REDESIGN bundle as the critical next step."

For Table 1 in the paper, report this experiment as: repro-v1, N=4 G runs, mean actual_fitness = 0.0341 [0.0306, 0.0377] 95% CI, verdict NULL.

---

*Ready for Reviewer-2's scrutiny.*
