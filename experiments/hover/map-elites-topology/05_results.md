# Results: hover/map-elites-topology

**Date**: 2026-03-30
**Input**: Final metrics, `01_design.md`, `03_plan.md`
**Analyst**: Dr. Elena Voss (ML Research Methodologist)

---

## 1. Final Metrics

### Val Fitness (primary metric)

| Run | Condition | Best Val Fitness | Best Program | Steps | Tool Steps |
|-----|-----------|-----------------|-------------|-------|-----------|
| V1 | control (1D fitness) | 82.89% | 23919fae | 10 | 5 |
| V2 | control (1D fitness) | **86.44%** | c1bf77e3 | 10 | 5 |
| V3 | treatment (3D structural) | 84.89% | e19bb14d | 10 | 5 |
| V4 | treatment (3D structural) | 85.44% | ec657572 | 9 | 5 |

| Condition | Mean | SD | N |
|-----------|------|-----|---|
| Control | 84.67% | 2.51pp | 2 |
| Treatment | 85.17% | 0.39pp | 2 |

**Delta (treatment - control): +0.50pp**

### Test Coverage (discrete, 5-repeat mean)

| Run | Condition | Test Coverage (mean ± std) | Repeats |
|-----|-----------|---------------------------|---------|
| V1 | control | 60.33% ± 0.94% | [59.33, 59.33, 60.67, 61.33, 61.00] |
| V2 | control | 65.87% ± 0.84% | [66.00, 65.00, 65.00, 66.67, 66.67] |
| V3 | treatment | **66.40% ± 1.62%** | [67.67, 68.00, 66.67, 65.67, 64.00] |
| V4 | treatment | 63.73% ± 1.44% | [65.33, 64.00, 61.67, 63.00, 64.67] |

| Condition | Mean Test Coverage | SD | N |
|-----------|-------------------|-----|---|
| Control | 63.10% | 3.92pp | 2 |
| Treatment | 65.07% | 1.89pp | 2 |

**Delta (treatment - control): +1.96pp**

### MAP-Elites Archive Diversity

| Run | Condition | Cells Occupied | Entropy (bits) | BC Dimensions |
|-----|-----------|---------------|----------------|---------------|
| V1 | control | 51/150 (34%) | 5.67 | 1D (fitness) |
| V2 | control | 42/150 (28%) | 5.39 | 1D (fitness) |
| V3 | treatment | 33/150 (22%) | 5.04 | 3D (dag_depth × max_fan_in × n_deep_retrieval) |
| V4 | treatment | 41/150 (27%) | 5.36 | 3D (5×5×5 bins) |

Treatment archives span all 5 bins on all 3 dimensions, confirming the BC space induces genuine structural diversity. Both treatment runs cover the full dag_depth range (5-10), max_fan_in range (1-6), and n_deep_retrieval range (0-5).

### Architecture of Best Programs

| Run | dag_depth | max_fan_in | n_deep_retrieval | n_steps |
|-----|-----------|-----------|-----------------|---------|
| V1 (ctrl best) | 10 | — | 2 | 10 |
| V2 (ctrl best) | 8 | — | 5 | 10 |
| V3 (treat best) | 10 | — | 5 | 10 |
| V4 (treat best) | 7 | — | 5 | 9 |

### Throughput

| Run | Total Programs | Valid Programs | Invalid % | Gens Completed |
|-----|---------------|---------------|-----------|----------------|
| V1 | 162 | 58 | ~40% | 25/25 |
| V2 | 164 | 63 | ~47% | 22/25 |
| V3 | 159 | 72 | ~40% | 25/25 |
| V4 | 165 | 59 | ~39% | 23/25 |

**Baseline reference (SS-v2)**: Control mean 82.7%, Treatment (SS+LPT) mean 83.8%.

---

## 2. Hypothesis Test

### Primary (val fitness superiority)

**H₀**: mu_treatment - mu_control <= 0
**H₁**: mu_treatment - mu_control > 0
**Primary metric**: Best `valid_frontier_fitness` at gen 25
**Statistical test**: One-sided Welch's t-test, α = 0.10

**Result**: t = 0.278, p = 0.413. **FAIL TO REJECT H₀.**

Delta = +0.50pp. Per the pre-registered decision rule (Section 8 of 01_design.md):
- p >= 0.10 and delta in [-1.0pp, +1.0pp] → **No directional signal → NULL**

The N=4 extension is **not triggered** (delta < +1.0pp threshold).

### Secondary (test coverage, exploratory)

One-sided Welch's t-test on per-run mean test coverage:
- t = 0.639, p = 0.305. Not significant at α = 0.10.
- Delta = +1.96pp (treatment > control), but driven by high V1 control variance.

### Secondary (diversity, descriptive only)

Treatment occupied fewer cells on average (37/150 = 25%) than control (46/150 = 31%). This is expected: the 3D grid is harder to fill than the 1D fitness grid because it requires diverse architectures, not just diverse fitness values.

Treatment entropy (5.20 bits) is lower than control entropy (5.53 bits), again because the 3D grid has more empty cells.

**Interpretation**: The 3D BC space successfully induced structural diversity across all dimensions, but this did not translate to fitness advantages.

---

## 3. Effect Size

| Metric | Control Mean | Treatment Mean | Delta | Cohen's d | 95% CI (bootstrap) |
|--------|-------------|---------------|-------|-----------|-------------------|
| Val fitness | 84.67% | 85.17% | +0.50pp | 0.28 | N/A (N=2) |
| Test coverage | 63.10% | 65.07% | +1.96pp | 0.64 | N/A (N=2) |

Cohen's d = 0.28 for val fitness is a small effect, consistent with the NULL verdict. The test coverage delta (+1.96pp) is larger but not significant due to high within-condition variance (V1 control is an outlier at 60.3% vs V2 at 65.9%).

---

## 4. Secondary Observations

### Heatmap Analysis (Treatment Runs)

The DAG Depth × N Deep Retrieval heatmaps reveal a clear pattern:
- **High dag_depth (9-10) + high n_deep_retrieval (4-5)** consistently produces the highest fitness (~83-85%)
- **Low dag_depth (5) + any n_deep_retrieval** yields lower fitness (~70-75%)
- **max_fan_in** shows no strong correlation with fitness — programs across fan-in 1-6 achieve similar fitness

This suggests that **chain depth and retrieval aggressiveness** are the key architectural drivers of fitness, while **parallelism (fan-in)** is less important.

### Scatter Plot Analysis

All 4 runs (control and treatment) show similar fitness distributions across BC dimensions:
- DAG depth clusters at 7-10 with a positive fitness trend
- N deep retrieval 4-5 strongly associated with high fitness
- Max fan-in is uniformly distributed with no fitness correlation

This indicates that the fitness landscape is similar across conditions — the treatment's structural BC didn't unlock architectures that were inaccessible to the control.

### Val-Test Gap

All runs show a substantial val-test gap (val 82-86% soft fractional → test 60-66% discrete):
- V1: 82.89% val → 60.33% test (22.6pp gap)
- V2: 86.44% val → 65.87% test (20.6pp gap)
- V3: 84.89% val → 66.40% test (18.5pp gap)
- V4: 85.44% val → 63.73% test (21.7pp gap)

Treatment V3 has the smallest val-test gap (18.5pp), suggesting better generalization, but this is a single data point.

---

## 5. Deviations from Pre-Registration

| # | Deviation | Impact on Validity | Assessment |
|---|-----------|-------------------|-----------|
| 1 | V2 reached gen 22/25, V4 reached gen 23/25 (not full 25) at time of stopping | Minimal — fitness plateaued hours before stopping. Pre-registered endpoint rule allows "last completed epoch" | No confound |
| 2 | `evo` conda environment was recreated mid-experiment (platform restart) | No impact — runs were already stopped. Only affected test evaluation tooling (required reinstalling bm25s, PyStemmer) | No confound |
| 3 | Redis was restarted during closeout (run_state counters reset) | No impact on data — program data intact. Only affected generation counter display | No confound |
| 4 | Pipeline was `structural_metrics` in experiment.yaml, not `standard` as in 03_plan.md | Both conditions used the same pipeline. The structural metrics stage ran on all arms as designed (Section 12 of 01_design.md). This is the intended implementation, not a deviation | No confound |

**Issues from 04_issues_log.md**:
- Issue 6 (SS-v2 data flushed before archive): Does not affect this experiment's validity. Systemic fix recommended.
- Issues 1-5 (smoke test failures, Bearer auth): Cosmetic or pre-launch issues. All resolved before run launch.

---

## 6. Run Validity

| Run | Valid for Analysis? | Reason if Excluded |
|-----|--------------------|--------------------|
| V1 | Yes | Completed 25/25 gens |
| V2 | Yes | Completed 22/25 gens, fitness plateaued |
| V3 | Yes | Completed 25/25 gens |
| V4 | Yes | Completed 23/25 gens, fitness plateaued |

All 4 runs are valid. No invalidation criteria triggered (Section 10 of 01_design.md).

---

## 7. Lessons Learned

**What worked**:
- The 3D structural BC space (dag_depth × max_fan_in × n_deep_retrieval) successfully induced diversity across all dimensions — confirming the empirical analysis from SS-v2 data was predictive
- The `ChainStructuralMetricsStage` running on all arms eliminated pipeline confounds cleanly
- Steady-state engine + LPT scheduling provided consistent throughput across conditions
- Archive visualization (scatter + heatmaps) provided clear insight into the fitness landscape

**What didn't work**:
- Structural diversity did not translate to fitness improvement — the NULL verdict suggests fitness-only binning is near-optimal for this task
- The 3D grid was somewhat over-partitioned (22-25% cell occupation vs 28-34% for 1D), meaning many architectural niches remained unexplored
- max_fan_in as a BC dimension was uninformative — no correlation with fitness

**Bugs / infrastructure issues**:
- `evo` conda env was deleted by platform restart, requiring manual reinstallation of bm25s + PyStemmer for test evaluation
- SS-v2 Redis data was flushed without archival during experiment setup (Issue 6)

---

## 8. Next Steps

Per the pre-registered decision table (Section 14 of 01_design.md):

**Result pattern**: Treatment ~ control, high diversity → "Diversity maintained but does not improve fitness; 1D fitness binning is near-optimal. Close structural BC line; pivot to other interventions."

**Recommended**:
1. **Close the structural BC line** — 3D topology-based BC does not improve fitness over 1D fitness binning
2. **Key insight to carry forward**: DAG depth and n_deep_retrieval are the dominant architectural predictors of fitness. max_fan_in is uninformative. Future experiments should focus on these two axes.
3. **Next experiment candidate**: `hover/7step-dynamic` — test whether dynamic topology mutation within a 7-step budget (matching baseline) improves over static prompt-only evolution. This tests a different hypothesis (topology freedom vs prompts) rather than archive indexing.
4. **N=4 extension**: NOT triggered (delta < +1.0pp threshold)

---

## 9. Paper / Report Notes

**Verdict**: NULL — 3D structural behavioral characterization for MAP-Elites does not improve evolved chain quality on HoVer.

**Key result for paper**: Despite successfully maintaining architectural diversity (treatment archives span all bins on all 3 structural dimensions), the diversity did not translate to fitness improvement. This suggests that for multi-hop retrieval chain evolution, the fitness landscape is sufficiently smooth that fitness-only archive indexing provides adequate exploration.

**Interesting negative finding**: The heatmap analysis shows that high-fitness architectures cluster in a narrow region (deep chains + aggressive retrieval), regardless of whether the archive actively preserves structural diversity. Evolution converges to this region regardless of the BC space used. This supports the view that the task's fitness landscape has a clear global attractor.

**GEPA comparison**: All runs substantially exceed GEPA (52.33% test discrete). Best test coverage: V3 treatment at 66.40% (14.07pp above GEPA).
