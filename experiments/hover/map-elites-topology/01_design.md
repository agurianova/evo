# Experimental Design: hover/map-elites-topology

**Date**: 2026-03-29
**Researcher**: Dr. Elena Voss (ML Research Methodologist)
**Status**: Revised (R1) -- addressing Reviewer-2 concerns

---

## 1. Research Question

Does using chain structural features (`dag_depth`, `max_fan_in`, `n_deep_retrieval`) as a 3D MAP-Elites behavioral characterization (BC) -- instead of the default fitness-only binning -- improve evolved chain quality on HoVer?

### Motivation

Current MAP-Elites uses a 1D behavior space keyed solely on the primary fitness metric (`retrieval_coverage`). The archive bins programs by how well they perform, not by what they look like architecturally. Programs with fundamentally different structures -- deep sequential chains versus wide parallel gather-then-reason patterns, aggressive deep retrieval versus conservative shallow retrieval -- compete in the same fitness-sorted bins. High-fitness architectures crowd out structurally diverse alternatives, and the archive converges to a narrow architectural cluster.

Empirical evidence from prior experiments supports this concern:

1. **hover/dynamic-topology** (PR #116): POSITIVE result, +6pp test coverage. Evolution discovered 5-retrieval-hop architectures that were structurally inaccessible under the fixed 3-hop topology. The Pareto frontier analysis showed architecture tightly clustered at 4-5 retrieval calls + 5-6 LLM steps.

2. **hover/steady-state-v2** (PR #138): SS+LPT achieved 85.2% val fitness at best, confirming that the SS engine is a viable baseline. Both conditions used `chains/hover/full` (dynamic topology), yet the archive still converged to a narrow structural region.

3. **Empirical feature analysis of 824 SS-v2 programs** (4 runs, Redis DBs 3-6): Identified which chain features actually vary and which are degenerate. The original 2D candidate (`n_tool_steps` x `n_llm_steps`) is too concentrated: 79% of programs have `n_total=10`, with tool steps clustered at 4-5 and LLM steps at 5-6. A 7x7 grid would have ~10 occupied cells -- barely better than 1D. The best 3D combination (`dag_depth` x `max_fan_in` x `n_deep_retrieval`) yields 107/486 raw combinations occupied (22%), with the top cell holding only 8.0% of programs. See Section 3 for full justification.

These findings suggest that **structural diversity in the archive is valuable** but not maintained by fitness-only binning. Classic MAP-Elites separates *behavior description* (which cell a program lands in) from *quality* (which program wins within a cell). By keying on three nearly-independent structural axes, the archive is forced to retain the best program at each architecture point. This prevents premature convergence to a single architecture and may surface efficient designs that fitness-only search overlooks.

The treatment is lightweight: a new algorithm config file and a pipeline stage that extracts structural features from program code via DAG analysis and regex (zero LLM cost, <1ms per program). The intervention changes only *how the archive is indexed*, not the mutation operator, evaluation pipeline, or fitness computation.

---

## 2. Hypotheses

### Primary hypothesis (superiority): structural BC improves best val fitness

**H0**: mu_treatment - mu_control <= 0 (structural BC binning does not improve best val fitness)
**H1**: mu_treatment - mu_control > 0 (structural BC binning improves best val fitness)

### Secondary hypothesis (architecture diversity)

**H_div**: Treatment runs maintain a wider range of distinct (`dag_depth`, `max_fan_in`, `n_deep_retrieval`) triples in the archive at gen 25 than control runs, measured as count of occupied cells and Shannon entropy of the cell-occupancy distribution.

**Note on secondary test**: The diversity test is **descriptive only**. No multiplicity adjustment is applied. The primary hypothesis (fitness superiority) is the sole confirmatory test.

### Effect-size thresholds

| Treatment - Control delta | Verdict | Detectable at N=2? |
|---------------------------|---------|---------------------|
| >= +3.0pp | **STRONG POSITIVE** | Marginally (MDE = 4.4pp at 80% power; effects near 3pp detectable at ~50% power) |
| [+1.5pp, +3.0pp) | **POSITIVE** | No -- below MDE; requires N=4 extension |
| (0pp, +1.5pp) | **SUGGESTIVE** | No -- below MDE; requires N=4 extension |
| <= 0pp | **NULL** | Yes (wrong direction is always observable) |

These thresholds are calibrated against the inter-run SD from steady-state-v2 (range 82.4-85.2% val, spread ~1.4pp per condition).

---

## 3. Independent Variable(s)

| Variable | Control value | Treatment value |
|----------|---------------|-----------------|
| MAP-Elites behavior dimensions | Fitness only, 1D (`single_island.yaml` default: `[fitness]`, 150 bins) | Structural 3D (`topology_3d.yaml`: `[dag_depth, max_fan_in, n_deep_retrieval]`, 5x5x6 = 150 cells) |

### Empirical justification for the 3D behavior space

The choice of dimensions is grounded in empirical analysis of 824 programs from SS-v2 (4 runs, Redis DBs 3-6). The analysis evaluated all pairwise and triple combinations of available chain features for occupation spread, cell dominance, and inter-dimension independence.

**Rejected alternatives** (with reasons):

| Feature | Why rejected |
|---------|-------------|
| `n_total_steps` | Nearly constant at 10 (79% of programs) -- useless as a BC dimension |
| `tool_ratio` | Concentrated at 0.4-0.5 -- insufficient variation |
| `num_forks` | r=0.72 with `max_fan_in` -- redundant |
| `dep_density` | r=0.72 with `max_fan_in` -- redundant |
| `n_tool_steps x n_llm_steps` (original v1 proposal) | Tool steps cluster at 4-5, LLM at 5-6; a 7x7 grid would have ~10 occupied cells |

**Selected dimensions**:

1. **`dag_depth`** (range 2-11, 9 unique values in SS-v2): Longest path from root to leaf in the dependency DAG. Captures sequential chain length vs. wide parallel structure. **New feature -- must be added to `ChainFeatureExtractor`.** Computed by parsing each step's dependencies via `_DEP_RE`, building an adjacency list, and finding the longest path via topological DP.

2. **`max_fan_in`** (range 1-9, 9 unique values): Maximum in-degree across all steps. Already computed by `ChainFeatureExtractor`. Captures pipeline (fan_in=1) vs. gather-then-reason (fan_in=4+) patterns.

3. **`n_deep_retrieval`** (range 0-5, 6 unique values): Count of `retrieve_deep` calls (k=10 vs. regular k=7). Already computed by `ChainFeatureExtractor`. Captures retrieval aggressiveness.

**Correlation matrix** (from SS-v2 empirical analysis, N=824):

```
                dag_depth  max_fan_in  n_deep_retrieval
dag_depth         1.000      -0.170        -0.075
max_fan_in       -0.170       1.000         0.186
n_deep_retrieval -0.075       0.186         1.000
```

All |r| < 0.19 -- excellent independence. Each dimension captures a distinct architectural axis.

**Joint distribution statistics** (SS-v2 data):
- 107/486 raw combinations occupied (22%)
- Top cell holds only 8.0% of programs -- no single cell dominates
- 5-bin x 5-bin x 6-bin grid = **150 cells**, matching the control's 150 fitness bins (resolves the cell-count asymmetry concern from Reviewer-2)

### Grid specification

```yaml
behavior_space:
  _target_: gigaevo.config.helpers.build_behavior_space
  keys: [dag_depth, max_fan_in, n_deep_retrieval]
  bounds: [[1, 11], [1, 9], [0, 5]]
  resolutions: [5, 5, 6]
  binning_types: [linear, linear, linear]
  dynamic: true
  expansion_buffer_ratio: 0.1
```

All other variables held constant across conditions:

- **Engine**: `evolution=steady_state` (SS engine, validated in SS-v2)
- **Scheduling**: `scheduling=lpt` (LPT scheduling, validated in SS-v2)
- **Problem**: `problem.name=chains/hover/full` (dynamic topology, soft fractional fitness)
- **Pipeline**: `pipeline=standard`
- **Mutation LLM**: Qwen3-235B via LiteLLM proxy (balanced)
- **Chain LLM**: Qwen3-8B thinking via LiteLLM proxy
- **`max_in_flight`**: 8
- **`max_generations`**: 25
- **`island_max_size`**: 75
- **`ChainStructuralMetricsStage`**: runs on ALL arms (see Section 12)

### What the treatment changes mechanistically

In the control, programs are binned along a single fitness axis into 150 bins. A program with `retrieval_coverage=0.72` competes with all other programs in the same fitness bin, regardless of chain architecture. The archive can hold up to 75 programs; with 150 bins and 75 slots, at most ~50% of bins are occupied.

In the treatment, programs are binned into a 3D grid of `dag_depth` (5 bins) x `max_fan_in` (5 bins) x `n_deep_retrieval` (6 bins), yielding 150 cells. Within each cell, the program with the highest `retrieval_coverage` wins (via `SumArchiveSelector`). A deep-sequential/low-fan-in program and a shallow-parallel/high-fan-in program occupy different cells and do not compete. The archive preserves the best program at each architectural configuration.

**Cell-count matching**: Both conditions have 150 cells/bins, eliminating the granularity asymmetry identified in Reviewer-2 Concern #1. With `island_max_size=75` and 150 cells, both conditions have identical average occupancy (~0.5 programs per cell). Within-cell competition dynamics are matched.

**Fitness selection is preserved**: within each cell, `SumArchiveSelector` on `retrieval_coverage` selects the best-performing program. The treatment changes *where* programs are stored, not *how* they are ranked.

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Best val fitness at gen 25 (soft fractional) | `valid_frontier_fitness` from Redis | **YES** |
| Archive structural diversity at gen 25 | Count of distinct occupied (`dag_depth`, `max_fan_in`, `n_deep_retrieval`) cells + Shannon entropy of cell-occupancy distribution | Secondary (descriptive only) |
| Test coverage (discrete, 5-repeat) | Best-by-val program on 300-sample test set | Exploratory |
| Throughput (programs/hour) | Total evaluated programs / wall hours | Exploratory |
| Architecture of best-by-val program | `dag_depth`, `max_fan_in`, `n_deep_retrieval` of the highest-fitness program | Exploratory |

**Primary metric**: Best `valid_frontier_fitness` at gen 25 (or last completed epoch if gen 25 is not reached -- see Section 10).

**Test protocol**: 5 independent repeats of the full 300-sample discrete test evaluation per run, using the best-by-val program. The 5-repeat mean is the per-run estimate. This is the standard test protocol across all HoVer experiments.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Engine | `evolution=steady_state` | Both conditions use SS engine (validated in SS-v2) |
| Scheduling | `scheduling=lpt` | Both use LPT (validated in SS-v2) |
| Problem | `chains/hover/full` | Dynamic topology, soft fitness; same for both conditions |
| Pipeline | `standard` | Same evaluation pipeline (validate.py returns dict) |
| Mutation LLM | Qwen3-235B via LiteLLM proxy (`llm=balanced`) | Same mutation quality |
| Chain LLM | Qwen3-8B thinking via LiteLLM proxy | Same eval quality |
| `max_in_flight` | 8 | Same backpressure (SS engine default) |
| `max_generations` | 25 | Same evolutionary budget |
| `island_max_size` | 75 | Same archive capacity |
| `num_parents` | 1 | Single-parent mutation |
| `max_elites_per_generation` | 8 | Same elite count |
| `max_mutations_per_generation` | 8 | Same mutation budget per epoch |
| `stage_timeout` | 6000 | Match experiment.yaml |
| `dag_timeout` | 14400 | Match experiment.yaml |
| `significant_change` | 0.003 | Match prior experiments |
| `mutation_mode` | `rewrite` | Default |
| Val set | First 300 of HoVer train | Same evaluation data |
| Test set | 300 held-out samples | Same test data |
| Seed initialization | Cold start (no `program_loader.problem_dir`) | Identical starting point |
| `ChainStructuralMetricsStage` | Active on ALL runs | See Section 12 -- avoids pipeline confound |

---

## 6. Run Design Table

| Run | Label | Condition | `redis.db` | `extra_overrides` |
|-----|-------|-----------|------------|-------------------|
| 1 | V1 | Control | 3 | `evolution=steady_state scheduling=lpt` |
| 2 | V2 | Control | 4 | `evolution=steady_state scheduling=lpt` |
| 3 | V3 | Treatment | 5 | `evolution=steady_state scheduling=lpt algorithm=topology_3d` |
| 4 | V4 | Treatment | 6 | `evolution=steady_state scheduling=lpt algorithm=topology_3d` |

**N = 2 per condition, 4 runs total.**

All runs share:
- Chain: LiteLLM proxy at `http://10.232.30.185:4000/v1` (model: `Qwen/Qwen3-8B`)
- Mutation: LiteLLM proxy (Qwen3-235B servers, load-balanced by proxy)
- `problem.name=chains/hover/full`, `pipeline=standard`, `llm=balanced`

**Run naming convention**: V-prefix inherited from SS-v2 naming. V1/V2 = control, V3/V4 = treatment.

**Redis DB assignments**: DBs 3-6. These must be archived and flushed before launch if any prior data exists.

**Non-randomization note**: V1/V2 are always control (DBs 3,4), V3/V4 always treatment (DBs 5,6). DB-to-condition assignment is not randomized. Any systematic difference between Redis DB instances would be confounded with condition. This is mitigated by flushing all DBs before launch and verifying 0 keys, but the non-randomization should be noted as a minor limitation.

**All 4 runs launch simultaneously.** The LiteLLM proxy handles load balancing across chain and mutation servers, eliminating host-treatment confounds.

### Treatment implementation details

**New algorithm config**: `config/algorithm/topology_3d.yaml`
- Behavior space: 3D with keys `[dag_depth, max_fan_in, n_deep_retrieval]`
- Bounds: `[[1, 11], [1, 9], [0, 5]]` (covers observed ranges from SS-v2 empirical analysis, with margin via `expansion_buffer_ratio: 0.1`)
- Resolution: `[5, 5, 6]` = 150 cells (matches the control's 150 fitness bins)
- Binning type: `linear` for all three dimensions
- Dynamic expansion: enabled (in case evolution discovers architectures beyond observed ranges)
- Archive selector: `SumArchiveSelector` on `retrieval_coverage` (fitness decides within-cell winner)
- All other island settings (elite selector, archive remover, migrant selector) identical to `single_island.yaml`

**New pipeline stage**: `ChainStructuralMetricsStage`
- Extracts `dag_depth`, `max_fan_in`, and `n_deep_retrieval` from program code
- `dag_depth`: parsed from dependency structure via `_DEP_RE`, adjacency list construction, longest-path DP
- `max_fan_in` and `n_deep_retrieval`: extracted via existing `ChainFeatureExtractor` regex patterns
- Stores them as `program.metrics` entries so the behavior space can key on them
- Runs early in the DAG (before archive ingestion), zero LLM cost, <1ms per program
- **Runs on ALL arms** (control AND treatment) to avoid pipeline confound -- see Section 12

**Why the feature extraction is reliable**: `ChainFeatureExtractor` uses compiled regex patterns for `max_fan_in` and `n_deep_retrieval`, already validated in production for LPT scheduling. The new `dag_depth` feature uses dependency parsing from the same codebase (`_DEP_RE` regex) with a standard topological sort + longest-path DP, which is deterministic and testable. Max chain steps = 10 (enforced by `FULL_CHAIN_CONFIG["max_steps"]` in `problems/chains/hover/full/config.py`), bounding `dag_depth` to [1, 11] (10 steps + 1 for root).

---

## 7. Sample Size Justification

N=2 per condition (4 runs total). This is a pragmatic choice driven by:

1. **Compute budget**: 4 simultaneous runs is the maximum feasible allocation on the shared LiteLLM infrastructure without excessive proxy contention.
2. **Strong priors**: SS-v2 showed inter-run spread of ~1.4pp per condition (V1 83.0%, V2 82.4% control; V3 85.2%, V4 82.4% treatment). If the treatment effect is comparable to dynamic-topology (+6pp test), it should be detectable even at N=2.
3. **Exploratory nature**: This is the first experiment testing structural BC dimensions in MAP-Elites for this task. A directional signal at N=2 justifies a powered follow-up; absence of signal informs whether the mechanism is promising.

**MDE analysis (t-distribution, df=2)**:
- Conservative SD estimate: 1.5pp (upper bound from prior experiments)
- SE = SD * sqrt(1/n1 + 1/n2) = 1.5 * sqrt(1) = 1.5pp
- t(0.10, df=2) = 1.886 (one-sided, alpha=0.10)
- MDE at 80% power: (t_alpha + t_beta) * SE = (1.886 + 1.061) * 1.5 = 4.42pp

At conservative SD=1.5pp, the test can detect effects of >= 4.4pp at 80% power. At optimistic SD=0.8pp, MDE drops to ~2.4pp. Given the low power at N=2, results are interpreted as directional evidence. See the effect-size table in Section 2 for which tiers are detectable at N=2 vs. requiring the N=4 extension.

**Pre-committed extension protocol**: If directional signal is promising (treatment mean > control mean by >= 1.0pp) but statistically inconclusive (p > 0.10), extend to N=4 per condition (4 additional runs on DBs 7-10). See Section 8 for the pre-specified N=4 analysis plan.

---

## 8. Statistical Test

**Test**: One-sided Welch's t-test on per-run best val fitness at gen 25 (or last completed epoch)
**Null**: mu_treatment - mu_control <= 0
**Significance threshold**: alpha = 0.10 (one-sided, given N=2 power limitation)
**How computed**: `scipy.stats.ttest_ind(treatment, control, alternative='greater')`

**Decision rule**:

| Outcome | Interpretation | Next step |
|---------|----------------|-----------|
| p < 0.10, delta > 0 | Treatment improves fitness | Report POSITIVE; extend to N=4 to confirm |
| p >= 0.10, delta > +1.0pp | Promising but underpowered | Extend to N=4 (pre-committed) |
| p >= 0.10, delta in [-1.0pp, +1.0pp] | No directional signal | Report NULL; close this line |
| delta < -1.0pp | Treatment hurts fitness | Report NEGATIVE; investigate mechanism |

### N=4 extension analysis protocol (pre-specified)

If the extension to N=4 per condition is triggered (either by p < 0.10 or by delta > +1.0pp with p >= 0.10):

1. **Additional runs**: 4 new runs on DBs 7-10 (2 control, 2 treatment), using identical configuration to the original 4 runs.
2. **Final test**: Welch's t-test at **alpha = 0.10** (one-sided) on **all 8 runs** (4 per condition). The N=2 result is treated as **descriptive only** and does not contribute to the formal hypothesis test. The N=4 analysis is the sole confirmatory test.
3. **No alpha adjustment for the interim look**: The N=2 interim look does not spend alpha because it is not used as a rejection criterion -- it only determines whether to extend. The formal test is conducted once, at N=4.
4. **Extension wall time**: Same budget per run as the initial 4 runs (48h max). Same endpoint rules (Section 10).

### Secondary hypothesis (diversity)

For the diversity hypothesis (H_div): Mann-Whitney U test on count of distinct occupied (`dag_depth`, `max_fan_in`, `n_deep_retrieval`) triples, treatment vs. control. Also report Shannon entropy of the cell-occupancy distribution. **This test is descriptive only** -- no multiplicity adjustment is applied, and results are reported alongside exact counts regardless of significance.

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Archive indexing changes selection dynamics** | LOW (resolved in R1) | In the v1 design, the 49-cell treatment vs. 150-bin control created a 3x asymmetry in within-cell competition. **R1 resolution**: The 3D grid uses 5x5x6 = 150 cells, exactly matching the control's 150 fitness bins. With `island_max_size=75` and 150 cells in both conditions, average occupancy is identical (~0.5 programs per cell). The remaining difference is that control bins programs by *fitness value* while treatment bins by *structural features* -- but this is the intended IV, not a confound. |
| 2 | **Selection pressure change** | Medium -- fitness-only binning creates strong selection toward high fitness; structural binning weakens fitness pressure because mediocre programs survive in their own cells | This is the intended mechanism of the treatment, not a confound. A shallow program with 70% fitness survives in its structural cell even if a deep program has 80% fitness. This is exactly the diversity preservation MAP-Elites is designed to provide. The primary hypothesis tests the net effect. |
| 3 | **Feature extraction accuracy** | Low -- `dag_depth` is a new feature; regex-based extraction for fan-in and retrieval could miscount in edge cases | `max_fan_in` and `n_deep_retrieval` use `ChainFeatureExtractor`, already validated in production for LPT scheduling. `dag_depth` uses deterministic DAG parsing (`_DEP_RE` + topological DP). Unit test before launch: verify all three features on 5 sample programs from SS-v2 against manual counts. |
| 4 | **Pipeline confound from metrics stage** | LOW if mitigated -- if `ChainStructuralMetricsStage` runs only on treatment, any overhead (even <1ms) is a confound | MITIGATED: stage runs on ALL arms. Control programs gain `dag_depth`, `max_fan_in`, and `n_deep_retrieval` in `program.metrics` but the control's behavior space ignores these keys (it keys on `fitness` only). |
| 5 | **Stochastic LLM evolution** | High -- inter-run variance with N=2 | Pre-committed extension to N=4 with pre-specified analysis protocol (Section 8). Interpret N=2 results as directional. |
| 6 | **Structural features may not vary enough** | Medium -- if dynamic topology converges all programs to a narrow region in the 3D space, the grid collapses and treatment degenerates to weak within-cell competition | The diversity hypothesis (H_div) tests this directly. Empirical evidence from SS-v2 shows 22% cell occupation in the raw data (107/486 combinations), with the top cell holding only 8.0% -- substantially more variation than the rejected 2D alternative. |
| 7 | **Shared infrastructure contention** | Low -- all 4 runs share the LiteLLM proxy | Both conditions experience identical contention. Noise is symmetric in expectation. |
| 8 | **Non-randomization of DB-to-condition** | Low -- V1/V2 always control (DBs 3,4), V3/V4 always treatment (DBs 5,6) | Any systematic difference between Redis DB instances is confounded with condition. Mitigated by flush-and-verify (0 keys) before launch. Acknowledged as a minor limitation; DB instances are functionally identical on the same Redis server. |

---

## 10. Stop Criteria

### Endpoint rule

**Primary endpoint**: Gen 25 (epoch 25 in steady-state terminology).

**If gen 25 is not reached within 48 hours**: Use the fitness at the **last completed epoch** as the per-run endpoint. Wall time budget is extended to 48h (revised from the v1 estimate of 24-30h, based on SS-v2 epoch advancement rates showing ~3.5h per epoch under load).

**Rationale for 48h**: SS-v2 treatment runs advanced at roughly 1 epoch per 1.5h under favorable conditions, but slowed to ~1 epoch per 3.5h under contention. At 25 epochs x 2h average = 50h worst case. A 48h budget captures the vast majority of evolution while remaining feasible on shared infrastructure. Runs that plateau early (see stagnation rule below) will terminate before the wall time limit regardless.

### Early termination

- **Treatment runs: 0 occupied structural cells by gen 3**: Stage not working. Stop and debug `ChainStructuralMetricsStage`.
- **Any run: gen-0 val fitness = sentinel (-1000.0)**: Execution error. Invalidate and investigate.
- **Any run: invalidity rate > 90% at gen 10**: Systemic failure. Invalidate.

### Run invalidation

A run is excluded from all analyses if:
1. PID dies before gen 5 and cannot be restarted
2. Redis DB is corrupted or flushed accidentally
3. Treatment verification fails (see Section 12)
4. Gen-0 val fitness is sentinel value (-1000.0)

If both runs in a condition are invalidated, that condition is UNANSWERABLE. If 1 run is invalidated, the remaining run provides a point estimate only (no variance estimate); extend to N=3.

### Stagnation

If `valid_frontier_fitness` shows no improvement for >= 10 consecutive epochs AND current epoch >= 15, the run may be terminated early. This is not an invalidation -- recorded as "early plateau" and the final epoch's results are used.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| GPU hours | ~192h (4 runs x ~48h each, conservative estimate) |
| Wall time | ~48h max (all 4 runs in parallel) |
| Redis DBs used | 4 (DBs 3, 4, 5, 6); DBs 7-10 reserved for potential N=4 extension |
| Chain LLM | LiteLLM proxy (8-node Qwen3-8B cluster, shared) |
| Mutation LLM | LiteLLM proxy (Qwen3-235B servers, shared via `llm=balanced`) |
| Test eval time | ~5 min/repeat x 5 repeats x 4 runs = ~100 min total |
| New code required | (1) `config/algorithm/topology_3d.yaml`, (2) `ChainStructuralMetricsStage` pipeline stage (with `dag_depth` feature addition to `ChainFeatureExtractor`) |

---

## 12. Treatment Verification

This section specifies the observable evidence that the treatment is correctly applied and that no pipeline confounds exist.

### Critical design constraint: `ChainStructuralMetricsStage` runs on ALL arms

The `ChainStructuralMetricsStage` extracts `dag_depth`, `max_fan_in`, and `n_deep_retrieval` from program code and stores them in `program.metrics`. This stage **must run on all 4 runs** (control AND treatment), not only the treatment. Rationale:

1. **Pipeline equivalence**: If the stage runs only on treatment, any runtime overhead -- even if negligible -- is a confound. Both conditions must execute identical pipeline stages.
2. **Diagnostic value**: Having structural features in control runs' `program.metrics` enables post-hoc comparison of architecture distributions between conditions, even though the control's behavior space ignores these keys.
3. **Simplicity**: A single pipeline configuration for all runs eliminates the risk of misconfigured arms.

The control's behavior space (1D, fitness-only) will simply ignore the `dag_depth`, `max_fan_in`, and `n_deep_retrieval` keys in `program.metrics`. These extra keys have no effect on archive binning, selection, or fitness computation in the control condition.

### Observable evidence that treatment is applied

| Check | What to verify | Control (V1, V2) | Treatment (V3, V4) |
|-------|---------------|-------------------|---------------------|
| 1. Hydra cfg dump: algorithm | `algorithm` config group in cfg dump | `single_island` (default) | `topology_3d` |
| 2. Hydra cfg dump: behavior_space.keys | Keys used for archive binning | `[fitness]` (single key) | `[dag_depth, max_fan_in, n_deep_retrieval]` (three keys) |
| 3. Hydra cfg dump: behavior_space.resolutions | Grid resolution | `[150]` | `[5, 5, 6]` |
| 4. `program.metrics` in Redis | Structural features present | `dag_depth`, `max_fan_in`, `n_deep_retrieval` PRESENT (from shared stage) | `dag_depth`, `max_fan_in`, `n_deep_retrieval` PRESENT (used for binning) |
| 5. Archive cell distribution | Occupied cells at gen 25 | Programs spread along fitness axis only | Programs spread across 3D structural grid |
| 6. `topology_3d` in log | Algorithm config name in Hydra log | ABSENT | PRESENT |

### `extra_overrides` per condition

- **Control (V1, V2)**: `[evolution=steady_state, scheduling=lpt]`
- **Treatment (V3, V4)**: `[evolution=steady_state, scheduling=lpt, algorithm=topology_3d]`

The only difference between conditions is `algorithm=topology_3d`. All other overrides are identical.

### Automated treatment checks (for `experiment.yaml`)

| Check | Type | Target runs | Expected |
|-------|------|-------------|----------|
| `topology_3d` in Hydra log | `log_pattern_present` | V3, V4 | PRESENT |
| `topology_3d` NOT in control log | `log_pattern_absent` | V1, V2 | ABSENT |
| `dag_depth` in program.metrics (Redis) | `redis_key_pattern` | V1, V2, V3, V4 | PRESENT (shared stage) |
| behavior_space keys = 3 in cfg dump | `config_override` | V3, V4 | `[dag_depth, max_fan_in, n_deep_retrieval]` |

---

## 13. Baseline

Reference: `hover/steady-state-v2` (PR #138)

| Condition | V1 | V2 | Mean |
|-----------|-----|-----|------|
| Control (generational + FIFO) | 83.0% | 82.4% | 82.7% |
| Treatment (SS + LPT) | 85.2% | 82.4% | 83.8% |

**This experiment's baseline**: The SS+LPT condition from SS-v2 (V3/V4), since both conditions in the current experiment use SS+LPT. Expected control mean: ~83% val fitness.

Historical reference: GEPA benchmark = 52.33% test (discrete). HoVer baseline grand mean = 51.65% test (n=4).

---

## 14. Open Questions / Risks

### Priority risks

**Risk 1 -- Grid may be over-partitioned for the observed structural diversity (LOW).**
With `island_max_size=75` and 150 cells, the archive can keep ~0.5 programs per cell on average. Many cells will remain empty (architectures with dag_depth=2 and max_fan_in=9 and n_deep_retrieval=5 may never be produced by mutation). This is expected behavior for MAP-Elites -- empty cells represent unexplored architecture regions. The archive is not capacity-limited; it is exploration-limited.

**Mitigation**: Report fraction of occupied cells and Shannon entropy of cell-occupancy distribution at gen 25. If < 10% of cells are occupied in treatment, the 3D grid is over-partitioned for the observed structural diversity.

**Risk 2 -- Structural features may not vary enough under evolution (MEDIUM).**
The SS-v2 empirical analysis shows 22% cell occupation in historical data, but evolution under a structural behavior space may produce different dynamics. If mutation converges all programs to a narrow region of the 3D space, the grid collapses and treatment degenerates to weaker within-cell competition than control.

**Mitigation**: The diversity hypothesis (H_div) directly tests this. Shannon entropy provides a more sensitive measure than cell count alone (addresses Reviewer-2 Concern #7). If treatment and control show similar structural distributions, the experiment demonstrates that structural BC provides no diversity benefit -- a useful null finding.

**Risk 3 -- Selection pressure weakening hurts exploitation (MEDIUM).**
Fitness-only binning creates strong selection pressure: only the highest-fitness programs survive. Structural binning preserves mediocre programs in low-competition cells (e.g., a shallow/low-fan-in program with 60% fitness survives because no other program with that structure exists). This may reduce exploitation of the best architectures.

**Mitigation**: The primary hypothesis tests the net effect of exploration (diversity) versus exploitation (fitness pressure). If treatment fitness is lower, this is the most likely mechanism. Compare the fitness of the best program in each condition (exploitation check) alongside the archive-wide fitness distribution (exploration check).

**Risk 4 -- N=2 is inconclusive (HIGH).**
The MDE analysis shows that at conservative SD=1.5pp, the test requires a >= 4.4pp effect for 80% power. Only STRONG POSITIVE effects (>= 3pp) are marginally detectable at N=2; POSITIVE and SUGGESTIVE effects require the N=4 extension. The N=2 phase is therefore a screening test, not a definitive experiment.

**Mitigation**: Pre-committed extension to N=4 with pre-specified analysis protocol (Section 8). The N=4 test is the sole confirmatory analysis. N=2 results are directional evidence only.

**Risk 5 -- `dag_depth` is a new, untested feature (LOW).**
Unlike `max_fan_in` and `n_deep_retrieval`, `dag_depth` must be newly implemented in `ChainFeatureExtractor`. Implementation bugs could produce incorrect BC coordinates, misclassifying programs into wrong cells.

**Mitigation**: Unit tests on 5+ sample programs from SS-v2 with manually verified dag_depth values. Integration test in smoke run (3 generations on scratch DB). Deterministic algorithm (topological sort + DP) is easy to verify.

### Scientific open questions after this experiment

| Result pattern | Interpretation | Next experiment |
|---------------|----------------|-----------------|
| Treatment > control, high diversity | Structural BC improves fitness via architecture preservation | Replicate at N=4; analyze which architectures dominate |
| Treatment > control, low diversity | Improvement comes from different within-cell competition dynamics, not diversity | Investigate archive selection mechanism |
| Treatment ~ control, high diversity | Diversity maintained but does not improve fitness; 1D fitness binning is near-optimal | Close structural BC line; pivot to other interventions |
| Treatment ~ control, low diversity | Architecture converges regardless of BC dimensions; structural BC is inert | Close structural BC line |
| Treatment < control | Weakened fitness pressure hurts; structural binning is counterproductive | Investigate whether hybrid BC (fitness + structure) recovers lost exploitation |

---

## Appendix A: Code Verification Required Before Launch

1. **`topology_3d.yaml` correctness**: Verify the new config resolves correctly with `--cfg job`. Behavior space keys must be `[dag_depth, max_fan_in, n_deep_retrieval]`, bounds `[[1, 11], [1, 9], [0, 5]]`, resolution `[5, 5, 6]`.

2. **`dag_depth` implementation**: Verify `ChainFeatureExtractor.extract()` computes `dag_depth` correctly by running on 5+ sample programs from SS-v2 and comparing against manually traced DAG longest paths.

3. **`ChainStructuralMetricsStage` integration**: Verify the stage stores `dag_depth`, `max_fan_in`, and `n_deep_retrieval` in `program.metrics` by running 1 generation on a scratch DB and inspecting Redis.

4. **Feature extraction accuracy**: Run `ChainFeatureExtractor.extract()` on 5 sample programs from SS-v2 and verify all three features match manual counts.

5. **Control behavior space unaffected**: Verify that control runs (V1/V2) using `single_island.yaml` ignore the extra structural keys in `program.metrics` -- the behavior space keys on `fitness` only, and the extra keys cause no errors or warnings.

6. **Archive selector on fitness**: Verify that treatment runs' `SumArchiveSelector` uses `retrieval_coverage` (the primary fitness key), not any structural feature. Within-cell competition must be on fitness.

7. **Redis DBs 3-6**: Must show 0 keys after archival and flush.

8. **Hydra config verification for all 4 runs**: `--cfg job` check of `evolution: steady_state`, `scheduling: lpt`, correct `algorithm` per condition, `problem.name: chains/hover/full`, `pipeline: standard`.

---

## Appendix B: Reviewer-2 Concern Resolution Summary

| Reviewer-2 Concern | Resolution in R1 |
|---------------------|------------------|
| #1 -- Cell-count asymmetry (150 bins vs. 49 cells) | **Resolved**: 3D grid uses 5x5x6 = 150 cells, matching control's 150 fitness bins. Average occupancy identical at ~0.5 programs/cell. |
| #2 -- Effect-size table detectability at N=2 | **Resolved**: Table in Section 2 now annotates which tiers are detectable at N=2 (only STRONG POSITIVE is marginally detectable; POSITIVE and SUGGESTIVE require N=4). |
| #3 -- N=4 extension analysis protocol | **Resolved**: Section 8 now pre-specifies: Welch's t-test at alpha=0.10 on all 8 runs. N=2 result is descriptive only. No alpha adjustment for the interim look. |
| #4 -- Endpoint if gen 25 not reached | **Resolved**: Section 10 specifies: use last completed epoch. Wall time budget extended to 48h. |
| #5 -- No multiplicity adjustment stated | **Resolved**: Section 2 and Section 8 explicitly state the secondary diversity test is descriptive only, no multiplicity adjustment applied. |
| #6 -- Non-randomization of DB-to-condition | **Resolved**: Section 6 explicitly notes non-randomization as a minor limitation. |
| #7 -- Diversity metric is coarse (cell count only) | **Resolved**: Section 4 and Section 8 add Shannon entropy of cell-occupancy distribution alongside occupied cell count. |

---

*Revised per Reviewer-2 feedback. Ready for re-review.*
