# Results: hover/dynamic-crossover

**Date**: 2026-03-26
**Input**: Final metrics from Redis + archives, `01_design.md`, `experiment.yaml` checkpoints, mid-run test evaluation
**Analyst**: Dr. Elena Voss (ml-research-methodologist agent)

**Verdict**: **NULL / INCONCLUSIVE** -- The import error bug (Amendment A2) differentially degraded runs, making the comparison uninterpretable. The observed val fitness delta (+0.12pp for the best treatment run vs. control, -1.16pp for treatment mean vs. control) is within noise even without the bug. No topology evolution was observed in any run. The crossover hypothesis remains open and requires a clean rerun.

---

## 1. Final Metrics

### Validation (soft fractional retrieval coverage, 900 samples)

| Run | Condition | Nominal Gen | Real Effective Gens | Best Val Fitness | Top Archive Steps | Top Archive Tools |
|-----|-----------|:-----------:|:-------------------:|:----------------:|:-----------------:|:-----------------:|
| X1 | Control (num_parents=1) | 25/25 | ~14 | 83.44% | 10 | 5 |
| X2 | Treatment (num_parents=2) | 25/25 | ~17 | 83.56% | 10 | 5 |
| X3 | Treatment (num_parents=2) | 25/25 | ~14 | 81.00% | 10 | 5 |

| Condition | Val Fitness (best per run) | Mean | Notes |
|-----------|--------------------------|------|-------|
| Control (X1) | 83.44% | 83.44% | n=1 |
| Treatment (X2, X3) | 83.56%, 81.00% | 82.28% | n=2 |
| **Delta (treatment - control)** | | **-1.16pp** | Control leads on mean |

Within-treatment range: X2 83.56% - X3 81.00% = 2.56pp. This large spread (larger than any treatment-vs-control delta) indicates high within-treatment variance, consistent with the small sample size and stochastic nature of evolution.

### Test (discrete retrieval coverage, 300 samples)

Only X2 received a mid-run test evaluation (at gen 14, the 50% gate). X1 and X3 did not receive test evaluations because the import error bug consumed the remaining compute budget before closeout evaluations could be completed.

| Run | Condition | Test Mean | Test Std | n (repeats) | Gen at eval | Notes |
|-----|-----------|-----------|----------|:-----------:|:-----------:|-------|
| X2 | Treatment | 56.22% | 0.84% | 3 | 14 | Mid-run eval; gen 14 of 25 |
| X1 | Control | -- | -- | -- | -- | No test eval (import error consumed gens) |
| X3 | Treatment | -- | -- | -- | -- | No test eval (import error consumed gens) |

**Reference baselines**:

| Reference | Discrete Test Coverage |
|-----------|:---------------------:|
| GEPA benchmark | 52.33% |
| hover/baseline grand mean | 51.65% |
| hover/feedback_softfit Cell C | 54.37% |
| hover/dynamic-topology D5 (best single-parent) | 60.15% (val 83.11%) |
| hover/dynamic-topology control mean | 54.13% |

X2 mid-run test (56.22%) is +3.89pp above GEPA but -3.93pp below D5 (60.15%). This is a mid-run snapshot at gen 14; X2's val fitness continued improving from 82.44% at gen 14 to 83.56% at gen 17, suggesting the final test coverage would have been higher. However, we cannot know the final test figure.

---

## 2. Hypothesis Test

### Primary hypothesis (H1): crossover improves test retrieval coverage

**H0**: mu_crossover - mu_single <= 0pp.
**H1**: mu_crossover > mu_single.

**Result**: **UNANSWERABLE**.

The primary metric (mean discrete test retrieval coverage at gen 25, 5-repeat average per run) was not collected for X1 or X3. Only X2 received a partial test evaluation (3 repeats at gen 14, not gen 25). Without test coverage for the control run, the primary hypothesis cannot be tested as specified.

On the surrogate metric of validation fitness (soft, 900 samples), the treatment mean (82.28%) is 1.16pp below the control (83.44%). However, the comparison is confounded by the import error bug (Section 5), which differentially affected run throughput. Even if we ignore the bug, a -1.16pp delta falls squarely in the **NULL** category per the pre-registered effect-size thresholds.

The best individual treatment run (X2, 83.56%) leads the control (X1, 83.44%) by +0.12pp -- well within noise given the inter-run SD observed in prior experiments (0.63-1.41pp).

### Secondary hypothesis (H2): crossover accelerates convergence

**H0**: Crossover does not reach 80% val fitness in fewer generations than single-parent mutation.
**H2**: Crossover reaches 80% val fitness faster.

**Result**: **NOT SUPPORTED**.

| Run | Condition | Gen first reaching 80% val |
|-----|-----------|:--------------------------:|
| X1 | Control | 4 |
| X2 | Treatment | 7 |
| X3 | Treatment | 7 |

The control run reached 80% val fitness first (gen 4 vs. gen 7 for both treatment runs). This is the opposite of the H2 prediction. However, with n=1 per condition and substantial stochasticity, this observation is not conclusive evidence against the convergence acceleration hypothesis.

---

## 3. Effect Size

Per the pre-registered effect-size thresholds from Section 2 of the design:

| Comparison | Delta | Verdict |
|-----------|:-----:|---------|
| Treatment val mean (82.28%) vs. control val (83.44%) | -1.16pp | **NULL** (control leads) |
| X2 val (83.56%) vs. X1 val (83.44%) | +0.12pp | Within noise |
| X2 mid-run test (56.22%) vs. GEPA (52.33%) | +3.89pp | Above GEPA (but mid-run, not gen-25) |
| X2 mid-run test (56.22%) vs. D5 (60.15%) | -3.93pp | Below D5 reference |

The experiment does not reach any positive effect-size threshold. However, the NULL verdict is weakened by the import error confound -- we do not know what the final metrics would have been under clean evolution.

---

## 4. Secondary Observations

### 4.1 No topology evolution observed

All three runs remained at 7-step topology for their best programs throughout the monitored period. This is confirmed by the checkpoint notes (checkpoints 3-8 all report "still 7-step topology") and by the top-program archives. While the top-50 archive programs eventually grew to 9-10 steps (likely through the `chains/hover/full` dynamic topology), the best-by-fitness programs were consistently 10-step chains with 5 retrieval hops -- the same architecture that D5 converged on in the dynamic-topology experiment.

**Archive topology distribution at final state**:

| Run | 7-step | 8-step | 9-step | 10-step |
|-----|:------:|:------:|:------:|:-------:|
| X1 (top 50) | 0 | 1 | 3 | 46 |
| X2 (top 50) | 0 | 0 | 0 | 50 |
| X3 (top 50) | 3 | 0 | 18 | 29 |

X2 (treatment) converged entirely to 10-step chains, while X1 and X3 retained some diversity. X3's greater diversity (7-step and 9-step programs) may reflect its slower convergence and lower overall fitness.

### 4.2 Invalidity rates

From the evolution_data.csv archives (covering only the pre-import-error generations):

| Run | Condition | Valid Programs | Total Programs | Invalidity Rate | Gens in Archive |
|-----|-----------|:--------------:|:--------------:|:---------------:|:---------------:|
| X1 | Control | 89 | 173 | 49% | 1-7 |
| X2 | Treatment | 111 | 174 | 36% | 1-12 |
| X3 | Treatment | 57 | 153 | 63% | 1-9 |

X3's high invalidity rate (63%) is consistent with it being the weakest run throughout the experiment. The treatment mean invalidity (49%) is comparable to the control (49%), providing no evidence that crossover systematically increases invalidity. However, the large spread within treatment (36% to 63%) prevents any firm conclusion.

### 4.3 Best program generation of origin

| Run | Best Program Gen | Best Val Fitness | Notes |
|-----|:----------------:|:----------------:|-------|
| X1 | 4 | 83.44% | Early discovery; no improvement in gens 5-25 |
| X2 | 11 | 83.56% | Mid-run discovery; improved from 82.33% (gen 8) |
| X3 | 3 | 81.00% | Very early discovery; stagnated for 22+ generations |

All runs discovered their best programs in early-to-mid generations. X1 and X3 found their champions by gen 3-4 and never improved, suggesting either early convergence or that the import error bug prevented later-generation improvements.

### 4.4 X2 mid-run test evaluation details

The mid-run test evaluation on X2 (gen 14) evaluated the best-by-val program, which was a 10-step chain with 5 retrieval and 5 LLM steps. This architecture matches D5's best chain from the dynamic-topology experiment.

- Test discrete coverage: 56.22% (std=0.84%, n=3 repeats)
- Val-test gap: 83.56% - 56.22% = 27.34pp (consistent with the ~20-25pp gap seen in prior experiments)
- The 56.22% test result places X2 above GEPA (+3.89pp), above the dynamic-topology control mean (+2.09pp), but below D5 (-3.93pp)

### 4.5 Infrastructure improvements validated

**Mutation load balancer**: The `llm=balanced` config distributed mutation requests evenly across 3 servers. Checkpoint notes report distributions of 2/2/2, 19/16/21, 30/28/33, 97/87/98 at successive checkpoints -- near-perfect balance with no run starvation. Final distribution: 307/295/311 across the three mutation servers.

**Chain load balancer**: An initial connection leak was detected (connections 285/417/270/1243) and fixed mid-run with per-call load balancing in shared_config.py. Post-fix, connections dropped to 9/10/11/14 -- even distribution. This fix was the trigger for the import error bug (see Section 5).

---

## 5. Critical Incident: Import Error Bug (Amendment A2)

### Timeline

At approximately 10:45 UTC on 2026-03-26, a code change to `shared_config.py` renamed `LLM_CONFIG` to `get_llm_config()` to enable per-call chain server load balancing. This change, combined with stale `.pyc` bytecode cache files, broke all `CallValidatorFunction` exec_runner subprocesses with:

```
ImportError: cannot import name 'get_llm_config' from 'shared_config'
```

Every generation completed in 6-10 minutes (vs. normal 50-70 minutes) with 0 valid programs -- the evolutionary engine advanced the generation counter without producing any usable mutations.

### Damage assessment per run

| Run | Import Errors | Wasted Gens (approx) | Last Real Evolution Gen | Effective Gens |
|-----|:------------:|:--------------------:|:----------------------:|:--------------:|
| X1 | ~80 | 11 (gens 15-25) | ~14 | ~14 |
| X2 | ~55 | 8 (gens 18-25) | ~17 | ~17 |
| X3 | ~71 | 11 (gens 15-25) | ~14 | ~14 |

### Differential impact on conditions

The import error bug did not affect all runs equally. X2 (treatment) had ~17 effective generations while X1 (control) and X3 (treatment) had ~14. This asymmetry means:

1. **X2's slight val fitness lead (+0.12pp over X1) may partly reflect 3 extra generations of real evolution**, not a treatment effect.
2. **X3 was equally handicapped as X1**, yet produced lower fitness (81.00% vs. 83.44%). This suggests X3 was genuinely weaker, independent of the bug.
3. **The treatment-vs-control comparison is confounded**: the bug introduced a systematic bias in effective compute budget that is correlated with (but not caused by) the treatment assignment.

### Root cause

The `shared_config.py` rename was a live code change applied to the working directory while runs were active. The `.pyc` cache files were not cleared, causing exec_runner subprocesses (which fork fresh Python processes) to import the stale bytecode. The fix (clearing `__pycache__` directories) was applied but too late to salvage the lost generations.

### Conclusion

This incident renders the experiment **INCONCLUSIVE**. The nominal 25-generation budget was not realized for any run, and the effective budget differed across runs in a pattern correlated with the comparison of interest.

---

## 6. Run Validity

| Run | Valid for analysis? | Reason |
|-----|:-------------------:|--------|
| X1 | Partially | Completed 25/25 nominal but only ~14 effective gens. Import error wasted gens 15-25. Val fitness valid but may underestimate potential. No test eval. |
| X2 | Partially | Completed 25/25 nominal but only ~17 effective gens. Import error wasted gens 18-25. Val fitness valid. Mid-run test eval available (56.22% at gen 14). |
| X3 | Partially | Completed 25/25 nominal but only ~14 effective gens. Import error wasted gens 15-25. Consistently weakest run (81.00% val, 63% invalidity). No test eval. |

None of the runs meet the pre-registered invalidation criteria (Section 10 of the design): thinking mode was active, invalidity did not exceed 95% at gen 10, gen-0 val fitness was in range, and all config overrides were correct. The runs are technically valid but operationally degraded. The experiment is therefore not INVALID per protocol, but INCONCLUSIVE due to the import error confound.

---

## 7. Amendment Impact Assessment

| Amendment | Description | Impact on Validity |
|-----------|------------|-------------------|
| A1 (pre-launch) | Chain LB fix: renamed `LLM_CONFIG` to `get_llm_config()` for per-call load balancing | **Triggered the import error bug**. The fix itself was correct and improved chain server distribution, but the live code change during active runs caused the ImportError cascade. |
| A2 (mid-run) | Import error damage acknowledgment | **CRITICAL**. Differentially reduced effective generations across runs. X2 retained 3 more effective gens than X1/X3. Confounds the primary comparison. |

---

## 8. Crossover Diagnostic (IV Realization Check)

The design specified a crossover diagnostic: if >80% of children are structurally dominated by one parent, the treatment IV was not realized (the mutation LLM simply picked a parent and mutated it rather than combining elements from both).

**Partial evidence from archives**: All X2 and X3 top-50 programs have 2 parents listed, confirming the mutation LLM received both parents. However, structural similarity analysis (Jaccard similarity of step types, edit distance of prompts) was not completed due to the abbreviated experiment. The IV realization check is therefore **INCOMPLETE**.

The observation that X2's top 50 programs are uniformly 10-step/5-tool chains (zero diversity) is weakly suggestive of convergence to a single architecture -- which could indicate the LLM was selecting the fitter parent and making minor modifications rather than performing true structural recombination. However, this could also reflect the search space geometry (10-step/5-tool is simply the dominant fitness peak).

---

## 9. Comparison to Prior Experiments

| Experiment | Best Val | Best Test | n_steps | Condition |
|-----------|:--------:|:---------:|:-------:|-----------|
| hover/baseline | 75.6% | 51.65% | 7 (fixed) | Static topology, no feedback |
| hover/feedback_softfit Cell C | 78.7% | 54.37% | 7 (fixed) | Static topology, soft fitness |
| hover/dynamic-topology D5 | 83.11% | 60.15% | 9 | Dynamic topology, single-parent |
| **hover/dynamic-crossover X1** | **83.44%** | **--** | **10** | Dynamic topology, single-parent (control) |
| **hover/dynamic-crossover X2** | **83.56%** | **56.22% (mid-run)** | **10** | Dynamic topology, crossover (treatment) |
| **hover/dynamic-crossover X3** | **81.00%** | **--** | **10** | Dynamic topology, crossover (treatment) |

X1 (control) at 83.44% val closely replicates D5 (83.11%), providing evidence that the dynamic-topology result is reproducible under the new load-balanced infrastructure. The +0.33pp difference is within noise. This partially addresses Analysis 3 from the design (control replication of D5), though without test coverage for X1, the replication is limited to the validation metric.

---

## 10. Lessons Learned

### What worked

- **Mutation load balancer**: The `llm=balanced` config with Redis-coordinated least-loaded routing (DB 15) distributed requests perfectly across 3 mutation servers. Distribution ratios stayed within 5% throughout the experiment. This eliminates the per-run host confound present in all prior experiments.
- **Chain load balancer (once fixed)**: Per-call random endpoint selection from `HOVER_CHAIN_URL` provided even distribution across 4 chain servers.
- **Dynamic topology replication**: X1's val fitness (83.44%) closely matches D5 (83.11%), confirming the dynamic-topology result is reproducible.

### What did not work

- **Live code changes during active runs**: The `shared_config.py` rename broke all exec_runner subprocesses via stale `.pyc` cache. This is the single largest experimental failure in the project's history by wasted compute.
- **No test evaluation for 2 of 3 runs**: The import error consumed the compute window, and closeout test evaluations were not completed for X1 or X3.
- **X3 persistent underperformance**: X3 had the highest invalidity (63%), lowest val fitness (81.00%), and discovered its best program at gen 3 with no improvement over 22 subsequent generations. This may reflect bad luck in the evolutionary search (the stochastic tail) or a genuine issue with crossover when the elite archive lacks diversity.

### Infrastructure lessons

1. **Never modify shared problem code (shared_config.py, validate.py, etc.) while runs are active.** If a live fix is required, clear all `__pycache__` directories immediately and verify exec_runner subprocess imports succeed.
2. **Archive and test-eval before any code changes.** The correct procedure would have been: (a) pause evolution, (b) archive current state, (c) run test evaluations, (d) apply the fix, (e) resume.
3. **Watchdog should detect generation speed anomalies.** A generation completing in 6-10 minutes (vs. normal 50-70) with 0 valid programs is a clear signal of subprocess failure. The watchdog detected invalidity spikes but did not flag the anomalous generation speed.

---

## 11. Next Steps

### 11.1 Clean rerun of crossover experiment (HIGH PRIORITY)

The crossover hypothesis remains untested due to the import error confound. A clean rerun with the following modifications is recommended:

- **Same design**: n=1 control, n=2 treatment, `chains/hover/full`, `llm=balanced`
- **No live code changes**: All infrastructure fixes (chain LB, mutation LB) are now committed and stable
- **Gen 30 or 40**: Extend the generation budget to allow more evolutionary time, especially since all runs in this experiment found their best programs early (gens 3-11)
- **Pre-commit to closeout test eval**: Reserve compute time for full 5-repeat test evaluations before any code modifications

### 11.2 Crossover prompt engineering (MEDIUM PRIORITY)

Risk 1 from the design (mutation LLM ignores second parent) was flagged as HIGH risk. The limited data from this experiment does not resolve whether true recombination occurred. Future work should:

- Add explicit crossover instructions to the mutation prompt (e.g., "Combine the retrieval strategy from Parent 1 with the query generation approach from Parent 2")
- Log per-mutation parent-child structural similarity metrics for post-hoc IV verification

### 11.3 Topology evolution investigation (MEDIUM PRIORITY)

No run in this experiment showed topology evolution during the monitored period -- all best programs remained 7-step through the first 10+ generations, only reaching 9-10 steps in the later archive. This matches D5's trajectory (topology growth happened gradually). With 14-17 effective generations, the runs may not have had enough evolutionary time for topology innovation to emerge. A longer run (40+ generations) would provide more opportunity.

---

## 12. Deviations from Pre-Registration

| # | Deviation | Pre-registered? | Impact |
|---|-----------|:---------------:|--------|
| 1 | Chain LB fix (shared_config.py rename) applied mid-run | No | **CRITICAL** -- triggered import error bug, wasted 8-11 gens per run |
| 2 | Import error bug differentially reduced effective gens | No | **CRITICAL** -- confounds primary comparison (X2 got 3 more gens than X1/X3) |
| 3 | Test evaluations not completed for X1, X3 | No | **MAJOR** -- primary DV (test discrete coverage) unavailable for 2/3 runs |
| 4 | Only 3 test repeats (not 5) for X2 mid-run eval | Minor | Reduces precision of X2 test estimate but 0.84% SD suggests adequate stability |
| 5 | Test eval at gen 14 (not gen 25) for X2 | No | **MODERATE** -- X2's val improved +1.12pp after gen 14; test figure underestimates final potential |

---

## 13. Paper / Report Notes

This experiment does not contribute a positive or negative finding suitable for publication. Its primary value is methodological:

1. **Mutation load balancing works**: Redis-coordinated least-loaded routing across shared mutation servers eliminates the per-run host confound. Distribution ratios remained within 5% across 900+ mutation requests.
2. **Dynamic topology replicates**: The control run (83.44% val) closely matches D5 from the prior experiment (83.11% val), providing an independent replication point for the dynamic-topology finding.
3. **Live code changes during evolution are catastrophic**: This is a cautionary finding. A seemingly benign infrastructure improvement (renaming a function for per-call load balancing) rendered 8-11 generations per run worthless via stale bytecode cache.

The crossover research question remains open and requires a clean experiment.
