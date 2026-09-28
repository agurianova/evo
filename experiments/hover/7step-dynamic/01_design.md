# Experimental Design: hover/7step-dynamic

**Date**: 2026-03-30
**Researcher**: Dr. Elena Voss (ML Research Methodologist)
**Status**: Revised (R1) -- addressing Reviewer-2 concerns

---

## 1. Research Question

Does allowing dynamic topology mutation (rewiring dependencies, adding/removing steps) within a **7-step budget** improve fitness over static prompt-only evolution, both starting from the same 7-step baseline chain?

### Motivation

Two prior experiments bracket the question:

1. **hover/dynamic-topology** (PR #116, POSITIVE +6pp test): Showed that dynamic topology with up to 10 steps significantly outperforms the fixed 7-step static topology. Evolution discovered 5-retrieval-hop chains that are structurally inaccessible under the fixed topology. However, this comparison is confounded by **step budget asymmetry** -- the treatment had access to 10 steps while the control was limited to 7.

2. **hover/map-elites-topology** (PR #142, NULL +0.50pp val, +1.96pp test, p=0.413): Tested 3D structural MAP-Elites BC vs. 1D fitness binning, both with 10-step `chains/hover/full`. No significant difference. Both conditions had the same step budget and topology freedom; only the archive indexing differed.

A critical open question remains: **how much of the dynamic-topology gain comes from topology flexibility itself vs. the expanded step budget?** If 7-step chains with topology freedom (rewirable dependencies, mutable step types, removable/addable steps within the 7-step cap) outperform 7-step chains with frozen topology, then the gain is from structural flexibility, not merely more steps. If the result is NULL, then the dynamic-topology benefit is primarily a step-budget effect.

Supporting evidence:
- From SS-v2 data, only 4 out of 45 saved programs had exactly 7 steps, and these maxed out at ~78.4% val fitness vs. 86.4% for the best 10-step chains. This suggests 7 steps is a tighter constraint, making any topology-within-budget improvement more meaningful.
- The `dag_depth` and `n_deep_retrieval` features were identified as dominant architectural predictors in the map-elites-topology analysis. These features can still vary meaningfully within a 7-step budget (e.g., dag_depth 3 vs. 7, n_deep_retrieval 0 vs. 4).

This experiment isolates the **topology flexibility** variable by holding the step budget constant at 7.

---

## 2. Hypotheses

### Primary hypothesis (superiority): topology flexibility improves best val fitness

**H0**: mu_treatment - mu_control <= 0 (topology flexibility within a 7-step budget does not improve best val fitness)
**H1**: mu_treatment - mu_control > 0 (topology flexibility within a 7-step budget improves best val fitness)

### Secondary hypothesis (architecture diversity)

**H_div**: Treatment runs maintain a wider range of distinct (`dag_depth`, `max_fan_in`, `n_deep_retrieval`) triples in the archive at gen 25 than control runs, measured as count of occupied cells and Shannon entropy of the cell-occupancy distribution.

**Note on secondary test**: The diversity test is **descriptive only**. No multiplicity adjustment is applied. The primary hypothesis (fitness superiority) is the sole confirmatory test.

### Effect-size thresholds

| Treatment - Control delta | Verdict | Detectable at N=2? |
|---------------------------|---------|---------------------|
| >= +3.0pp | **STRONG POSITIVE** | Marginally (MDE = 4.4pp at 80% power; effects near 3pp detectable at ~50% power) |
| [+1.5pp, +3.0pp) | **POSITIVE** | No -- below MDE; requires N=4 extension |
| (0pp, +1.5pp) | **INCONCLUSIVE** | No -- below MDE; requires N=4 extension |
| <= 0pp | **NULL** | Yes (wrong direction is always observable) |

These thresholds are calibrated against the inter-run SD from map-elites-topology (control: 84.67% mean with ~1.0pp spread; treatment: 85.17% mean). Conservative SD estimate: 1.5pp.

---

## 3. Independent Variable(s)

| Variable | Control value | Treatment value |
|----------|---------------|-----------------|
| Chain topology mutability | `problem.name=chains/hover/static_soft` -- fixed 7-step topology, 3 frozen tool steps, 4 mutable LLM steps; only prompts evolve | `problem.name=chains/hover/full7` -- free topology up to 7 steps, no frozen steps, step types/dependencies/count all mutable; prompts + topology evolve |
| MAP-Elites behavior dimensions | Fitness only, 1D (`single_island.yaml` default: `[fitness]`, 60 bins) | Structural 3D (`topology_3d_7step.yaml`: `[dag_depth, max_fan_in, n_deep_retrieval]`, 4x3x5 = 60 cells) |

### Why two IVs are bundled

This experiment intentionally bundles topology mutability with structural BC, matching the design pattern from map-elites-topology. The rationale:

1. **Treatment coherence**: Dynamic topology produces structural variation that is wasted under 1D fitness binning. Structural BC preserves diverse architectures that topology mutation creates. Testing topology freedom without structural BC would underpower the topology effect.
2. **Control purity**: The static_soft control has no structural variation (all programs are 7-step with identical dependencies), making structural BC meaningless. The 1D fitness binning is the natural archive strategy for a frozen-topology condition.
3. **Interpretability**: If the result is POSITIVE, the secondary diversity analysis (H_div) can disentangle whether the gain comes from topology diversity (many architectures preserved) or from a single dominant architecture discovered via topology freedom (one cell dominates).

### What differs between the two problem variants

| Dimension | `static_soft` (control) | `full7` (treatment) |
|-----------|------------------------|--------------------|
| Max steps | 7 (fixed) | 7 (configurable via FULL7_CHAIN_CONFIG) |
| Frozen steps | Steps 1, 4, 7 are frozen tool steps | No frozen steps -- all steps mutable |
| Allowed step types | LLM only (tool steps frozen) | LLM and tool |
| Available tools | retrieve, retrieve_deep (frozen) | retrieve, retrieve_deep (evolvable) |
| require_final_llm | N/A (topology fixed) | False |
| Retrieval scoring | Positional (hardcoded step indices 0, 3, 6) | Adaptive (scans ALL tool-step outputs for gold articles) |
| Fitness computation | Soft: gold_found / n_gold per sample | Soft: gold_found / n_gold per sample (identical formula) |
| Seed program | 7-step chain with frozen field on tool steps | 7-step chain with NO frozen field, NO frozen steps |

### Treatment implementation details

**New problem variant**: `chains/hover/full7` -- a copy of `chains/hover/full` with `max_steps=7` instead of 10 in the config. All other chain evolution logic (adaptive scoring, step mutation, dependency mutation) is identical to `chains/hover/full`.

**New algorithm config**: `config/algorithm/topology_3d_7step.yaml`
- Behavior space: 3D with keys `[dag_depth, max_dependency_fan_in, n_deep_retrieval]`
- Bounds: `[[1, 7], [1, 6], [0, 4]]` (adjusted for 7-step max; see justification below)
- Resolution: `[4, 3, 5]` = 60 cells (matches control's 60 fitness bins)
- Binning type: `linear` for all three dimensions
- Dynamic expansion: enabled
- All other settings identical to `topology_3d.yaml`

**Bound adjustments for 7-step chains**:

| Dimension | 10-step bound | 7-step bound | Rationale |
|-----------|---------------|--------------|-----------|
| `dag_depth` | [1, 11] | [1, 7] | Max dag_depth = number of steps = 7 (fully sequential chain) |
| `max_fan_in` | [1, 9] | [1, 6] | Max fan-in = steps - 1 = 6 (one step depends on all others) |
| `n_deep_retrieval` | [0, 5] | [0, 4] | With 7 steps, max ~4 tool steps can be retrieve_deep (need at least some LLM steps for reasoning) |

**Control fitness binning**: 60 bins (changed from the default 150 to match treatment cell count). This is specified via `primary_resolution=60` in the control overrides.

**Cell-count matching**: Both conditions have 60 cells/bins, eliminating granularity asymmetry. With `island_max_size=75` and 60 cells, both conditions have identical average occupancy (~1.25 programs per cell).

### What the treatment changes mechanistically

In the control, the 7-step topology is frozen: 3 tool steps at fixed positions with fixed dependencies, 4 LLM steps with mutable prompts. The search space is prompt fields only. Programs are binned along a single fitness axis into 60 bins.

In the treatment, all 7 step slots are mutable: step types can change (LLM to tool or vice versa), dependencies can be rewired, and steps can be added or removed (within the 7-step cap). The seed starts as the same 7-step chain but without frozen annotations. Programs are binned into a 3D grid of `dag_depth` (4 bins) x `max_fan_in` (3 bins) x `n_deep_retrieval` (5 bins) = 60 cells.

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Best val fitness at gen 25 (soft fractional) | `valid_frontier_fitness` from Redis | **YES** |
| Archive structural diversity at gen 25 | Count of distinct occupied (`dag_depth`, `max_fan_in`, `n_deep_retrieval`) cells + Shannon entropy | Secondary (descriptive only) |
| Test coverage (discrete, 5-repeat) | Best-by-val program on 300-sample test set | Exploratory |
| Throughput (programs/hour) | Total evaluated programs / wall hours | Exploratory |
| Architecture of best-by-val program | `dag_depth`, `max_fan_in`, `n_deep_retrieval` of highest-fitness program | Exploratory |
| n_steps distribution in treatment archive | Step count distribution across elite programs at gen 25 | Exploratory (treatment only) |

**Primary metric**: Best `valid_frontier_fitness` at gen 25 (or last completed epoch if gen 25 is not reached -- see Section 10).

**Test protocol**: 5 independent repeats of the full 300-sample discrete test evaluation per run, using the best-by-val program. The 5-repeat mean is the per-run estimate.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Engine | `evolution=steady_state` | Both conditions use SS engine (validated in SS-v2) |
| Scheduling | `scheduling=lpt` | Both use LPT (validated in SS-v2) |
| Pipeline | `structural_metrics` | Same evaluation pipeline; `ChainStructuralMetricsStage` on ALL arms |
| Mutation LLM | Qwen3-235B via LiteLLM proxy (`llm=balanced`) | Same mutation quality |
| Chain LLM | Qwen3-8B thinking via LiteLLM proxy | Same eval quality |
| `max_in_flight` | 8 | Same backpressure (SS engine default) |
| `max_generations` | 25 | Same evolutionary budget |
| `island_max_size` | 75 | Same archive capacity |
| `num_parents` | 1 | Single-parent mutation |
| `max_elites_per_generation` | 8 | Same elite count |
| `max_mutations_per_generation` | 8 | Same mutation budget per epoch |
| `stage_timeout` | 6000 | Match prior experiments |
| `dag_timeout` | 14400 | Match prior experiments |
| `significant_change` | 0.003 | Match prior experiments |
| `mutation_mode` | `rewrite` | Default |
| Val set | First 300 of HoVer train | Same evaluation data |
| Test set | 300 held-out samples | Same test data |
| Seed initialization | Cold start (no `program_loader.problem_dir`) | Identical starting point |
| `ChainStructuralMetricsStage` | Active on ALL runs | Avoids pipeline confound |
| Max step budget | 7 (both conditions) | Isolates topology flexibility from step budget |

---

## 6. Run Design Table

| Run | Label | Condition | `redis.db` | `problem.name` | `extra_overrides` |
|-----|-------|-----------|------------|-----------------|-------------------|
| 1 | V1 | Control | 3 | `chains/hover/static_soft` | `evolution=steady_state scheduling=lpt primary_resolution=60` |
| 2 | V2 | Control | 4 | `chains/hover/static_soft` | `evolution=steady_state scheduling=lpt primary_resolution=60` |
| 3 | V3 | Treatment | 5 | `chains/hover/full7` | `evolution=steady_state scheduling=lpt algorithm=topology_3d_7step` |
| 4 | V4 | Treatment | 6 | `chains/hover/full7` | `evolution=steady_state scheduling=lpt algorithm=topology_3d_7step` |

**N = 2 per condition, 4 runs total.**

All runs share:
- Chain: LiteLLM proxy at `http://10.232.30.185:4000/v1` (model: `Qwen/Qwen3-8B`)
- Mutation: LiteLLM proxy (Qwen3-235B servers, load-balanced by proxy)
- `pipeline=structural_metrics`, `llm=balanced`

**Run naming convention**: V-prefix inherited from prior experiments. V1/V2 = control (static_soft), V3/V4 = treatment (full7).

**Redis DB assignments**: DBs 3-6. These must be archived and flushed before launch if any prior data exists.

**Non-randomization note**: V1/V2 are always control (DBs 3,4), V3/V4 always treatment (DBs 5,6). DB-to-condition assignment is not randomized. Mitigated by flushing all DBs before launch and verifying 0 keys. Noted as a minor limitation.

**All 4 runs launch simultaneously.** The LiteLLM proxy handles load balancing across chain and mutation servers.

---

## 7. Sample Size Justification

N=2 per condition (4 runs total). This is a pragmatic choice driven by:

1. **Compute budget**: 4 simultaneous runs is the maximum feasible allocation on the shared LiteLLM infrastructure without excessive proxy contention.
2. **Strong priors**: Map-elites-topology showed inter-run spread of ~1.0pp per condition. If the treatment effect is comparable to dynamic-topology's (+6pp test), it should be detectable even at N=2. However, since 7-step chains plateau lower (~78% val), the expected effect may be smaller.
3. **Exploratory nature**: This is the first experiment isolating topology flexibility from step budget. A directional signal at N=2 justifies a powered follow-up; absence of signal informs whether topology flexibility alone is productive.

**MDE analysis (t-distribution, df=2)**:
- Conservative SD estimate: 1.5pp (upper bound from prior experiments)
- SE = SD * sqrt(1/n1 + 1/n2) = 1.5 * sqrt(1) = 1.5pp
- t(0.10, df=2) = 1.886 (one-sided, alpha=0.10)
- MDE at 80% power: (t_alpha + t_beta) * SE = (1.886 + 1.061) * 1.5 = 4.42pp

At conservative SD=1.5pp, the test can detect effects >= 4.4pp at 80% power. At optimistic SD=0.8pp, MDE drops to ~2.4pp. Given the low power at N=2, results are interpreted as directional evidence.

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

If the extension to N=4 per condition is triggered:

1. **Additional runs**: 4 new runs on DBs 7-10 (2 control, 2 treatment), using identical configuration to the original 4 runs.
2. **Final test**: Welch's t-test at **alpha = 0.10** (one-sided) on **all 8 runs** (4 per condition). The N=2 result is treated as **descriptive only** and does not contribute to the formal hypothesis test.
3. **No alpha adjustment for the interim look**: The N=2 interim look does not spend alpha because it is not used as a rejection criterion.
4. **Extension wall time**: Same budget per run as the initial 4 runs (48h max).
5. **Sequential-procedure limitation (R1)**: The effective Type I error rate of this sequential procedure (N=2 descriptive look + conditional N=4 formal test) has not been analytically computed. This is accepted as a limitation of the pilot design.

### Secondary hypothesis (diversity)

For H_div: Mann-Whitney U test on count of distinct occupied (`dag_depth`, `max_fan_in`, `n_deep_retrieval`) triples, treatment vs. control. Also report Shannon entropy. **Descriptive only** -- no multiplicity adjustment.

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Two bundled IVs (topology + BC)** | MEDIUM -- if the result is positive, we cannot attribute it to topology alone vs. structural BC alone | This is a deliberate design choice. The map-elites-topology experiment (PR #142) already tested BC-only (NULL result with both conditions on 10-step `full`). If this experiment is POSITIVE, the gain is attributable to topology flexibility (since BC-only was NULL). If NULL, both topology and BC are inert at 7 steps. **Note (R1)**: We cannot rule out that 3D BC provides a diversity-preservation advantage specific to the 7-step regime that was not observed at 10 steps, though this interaction is unlikely given the NULL result at the less-constrained scale. |
| 2 | **Different problem.name between conditions** | LOW -- control uses `static_soft`, treatment uses `full7`; these have different validate.py code paths (positional vs. adaptive scoring) | For identical 7-step chains, both scoring methods produce identical results (verified in dynamic-topology experiment). Adaptive scoring diverges only for non-standard topologies, which is the intended treatment effect. Primary metric is discrete test coverage (all 3 gold docs), which is scoring-independent for complete retrieval. |
| 3 | **No frozen steps removes a structural prior** | LOW-MEDIUM -- in static_soft, frozen tool steps guarantee 3 retrieval hops; in full7, evolution could remove retrieval steps | Mitigated by natural selection. Programs that drop retrieval steps score near-zero on retrieval coverage and are eliminated. With 7 steps max, the step budget is tight enough that degenerate (all-LLM) programs are strongly penalized. Monitor n_tool_steps at gen 5. |
| 4 | **Pipeline confound from metrics stage** | LOW -- `ChainStructuralMetricsStage` runs on ALL arms, eliminating overhead asymmetry | Stage has <1ms overhead, zero LLM cost. Control programs gain structural features in `program.metrics` but the control's 1D behavior space ignores them. |
| 5 | **Stochastic LLM evolution** | HIGH -- inter-run variance with N=2 | Pre-committed extension to N=4 (Section 8). Interpret N=2 results as directional. |
| 6 | **7-step chains may not vary structurally** | MEDIUM -- with only 7 steps, the 3D structural space may collapse (few distinct architectures possible) | H_div tests this directly. The 60-cell grid (4x3x5) is sized for the reduced structural range. If < 10% of cells are occupied in treatment, the grid is over-partitioned. |
| 7 | **Shared infrastructure contention** | LOW -- all 4 runs share LiteLLM proxy | Both conditions experience identical contention. Noise is symmetric. |
| 8 | **Non-randomization of DB-to-condition** | LOW -- V1/V2 always control (DBs 3,4), V3/V4 always treatment (DBs 5,6) | Mitigated by flush-and-verify (0 keys) before launch. DB instances are functionally identical on the same Redis server. |
| 9 | **Cell-count matching requires non-default primary_resolution** | LOW -- control uses `primary_resolution=60` instead of default 150 | This is intentional to match treatment's 60 cells. With `island_max_size=75`, 60 bins gives ~1.25 programs/bin average occupancy, which is actually better-utilized than the default 150 bins (~0.5 programs/bin). Sensitivity check: if concerned, compare against 150-bin runs from map-elites-topology. |
| 10 | **Mutation LLM may struggle with topology mutations at 7 steps** | MEDIUM -- the LLM may not effectively explore the constrained structural space (e.g., removing a step forces all dependencies to rewire) | Monitor n_steps and n_tool_steps metrics. If step count remains at 7 for all 25 generations in treatment, the mutation LLM is not performing topology changes. Flag as "LLM mutation ceiling" rather than "topology not helpful." |
| 11 | **Frozen-step removal is a third bundled IV (R1)** | MEDIUM -- treatment removes frozen annotations on 3 tool steps, allowing the LLM to modify retrieval parameters (query templates, k values) even without topology changes. This is conceptually distinct from topology mutation: unfreezing ≠ rewiring. | If the result is POSITIVE, the H_div analysis and architecture-of-best-program analysis should assess whether best-by-val programs retained the original 3-tool-step topology (suggesting unfreezing, not topology change, was the driver). Report the fraction of treatment programs with non-seed `(n_steps, n_tool_steps)` as a key diagnostic. |

---

## 10. Stop Criteria

### Endpoint rule

**Primary endpoint**: Gen 25 (epoch 25 in steady-state terminology).

**If gen 25 is not reached within 48 hours**: Use the fitness at the **last completed epoch** as the per-run endpoint.

**Rationale for 48h**: SS-v2 treatment runs advanced at roughly 1 epoch per 1.5h under favorable conditions, but slowed to ~1 epoch per 3.5h under contention. At 25 epochs x 2h average = 50h worst case. A 48h budget captures the vast majority of evolution while remaining feasible on shared infrastructure.

### Manipulation check (R1)

At gen 5, compute the fraction of treatment programs whose `(n_steps, n_tool_steps, dag_depth)` triple differs from the seed's triple `(7, 3, 7)`. If this fraction is < 10%, flag the IV as potentially inactive and investigate whether the mutation LLM is performing topology changes. Report this fraction as a key diagnostic in the results regardless of outcome. If topology mutations cannot be induced by gen 10, the experiment should be declared as testing "unfreezing + BC" rather than "topology flexibility."

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

If both runs in a condition are invalidated, that condition is UNANSWERABLE. If 1 run is invalidated, the remaining run provides a point estimate only; extend to N=3.

### Generation-count normalization (R1)

If generation counts differ by > 3 across conditions at the 48h cutoff, analysis will use the fitness at the minimum completed generation across all runs. This prevents generation-count asymmetry from confounding the comparison.

### Stagnation

If `valid_frontier_fitness` shows no improvement for >= 10 consecutive epochs AND current epoch >= 15, the run may be terminated early. Recorded as "early plateau"; final epoch's results are used.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| GPU hours | ~192h (4 runs x ~48h each, conservative estimate) |
| Wall time | ~48h max (all 4 runs in parallel) |
| Redis DBs used | 4 (DBs 3, 4, 5, 6); DBs 7-10 reserved for potential N=4 extension |
| Chain LLM | LiteLLM proxy (Qwen3-8B cluster, shared) |
| Mutation LLM | LiteLLM proxy (Qwen3-235B servers, shared via `llm=balanced`) |
| Test eval time | ~5 min/repeat x 5 repeats x 4 runs = ~100 min total |
| New code required | (1) `chains/hover/full7/` problem variant (copy of `full` with `max_steps=7`), (2) `config/algorithm/topology_3d_7step.yaml` (copy of `topology_3d.yaml` with adjusted bounds) |

---

## 12. Treatment Verification

This section specifies the observable evidence that the treatment is correctly applied and that no pipeline confounds exist.

### Critical design constraint: `ChainStructuralMetricsStage` runs on ALL arms

The `ChainStructuralMetricsStage` extracts `dag_depth`, `max_dependency_fan_in`, and `n_deep_retrieval` from program code and stores them in `program.metrics`. This stage **must run on all 4 runs** (control AND treatment). Rationale:

1. **Pipeline equivalence**: If the stage runs only on treatment, any runtime overhead is a confound.
2. **Diagnostic value**: Structural features in control runs enable post-hoc architecture comparison.
3. **Simplicity**: A single pipeline configuration for all runs.

### Observable evidence that treatment is applied

| Check | What to verify | Control (V1, V2) | Treatment (V3, V4) |
|-------|---------------|-------------------|---------------------|
| 1. Hydra cfg: problem.name | Problem variant | `chains/hover/static_soft` | `chains/hover/full7` |
| 2. Hydra cfg: algorithm | Algorithm config group | `single_island` (default) | `topology_3d_7step` |
| 3. Hydra cfg: behavior_space.keys | Keys for archive binning | `[fitness]` (single key) | `[dag_depth, max_dependency_fan_in, n_deep_retrieval]` |
| 4. Hydra cfg: behavior_space.resolutions | Grid resolution | `[60]` | `[4, 3, 5]` |
| 5. `program.metrics` in Redis | Structural features present | `dag_depth`, `max_dependency_fan_in`, `n_deep_retrieval` PRESENT (shared stage) | PRESENT (used for binning) |
| 6. `topology_3d_7step` in log | Algorithm config name | ABSENT | PRESENT |
| 7. `full7` in log | Problem name | ABSENT | PRESENT |
| 8. Treatment: max_steps enforcement | No program exceeds 7 steps | N/A (topology frozen at 7) | All programs have <= 7 steps |

### `extra_overrides` per condition

- **Control (V1, V2)**: `[evolution=steady_state, scheduling=lpt, primary_resolution=60]`
- **Treatment (V3, V4)**: `[evolution=steady_state, scheduling=lpt, algorithm=topology_3d_7step]`

Differences: `primary_resolution=60` on control (to match 60 cells), `algorithm=topology_3d_7step` on treatment (which sets 60 cells via its 4x3x5 grid). `problem.name` differs per condition (set in launch script, not via `extra_overrides`).

### Automated treatment checks (for `experiment.yaml`)

| Check | Type | Target runs | Expected |
|-------|------|-------------|----------|
| `topology_3d_7step` in Hydra log | `log_pattern_present` | V3, V4 | PRESENT |
| `topology_3d_7step` NOT in control log | `log_pattern_absent` | V1, V2 | ABSENT |
| `full7` in Hydra log | `log_pattern_present` | V3, V4 | PRESENT |
| `static_soft` in Hydra log | `log_pattern_present` | V1, V2 | PRESENT |
| `dag_depth` in program.metrics (Redis) | `redis_key_pattern` | V1, V2, V3, V4 | PRESENT (shared stage) |
| `n_deep_retrieval` in program.metrics | `redis_key_pattern` | V1, V2, V3, V4 | PRESENT |
| behavior_space keys = 3 in cfg dump | `config_override` | V3, V4 | `[dag_depth, max_dependency_fan_in, n_deep_retrieval]` |

---

## 13. Baseline

### Primary reference: hover/map-elites-topology (PR #142)

| Condition | V1 | V2 | Mean |
|-----------|-----|-----|------|
| Control (1D fitness, `full` 10-step) | ~84.2% | ~85.1% | 84.67% |
| Treatment (3D BC, `full` 10-step) | ~84.8% | ~85.5% | 85.17% |

**Important caveat**: These baselines used 10-step `chains/hover/full`. The current experiment uses 7-step constraints, so absolute fitness levels will likely be lower. The 7-step ceiling from SS-v2 data was ~78.4% val fitness. Expected control mean for this experiment: **~75-80% val fitness** (rough estimate, given the 7-step constraint and static topology).

### Historical references

| Source | Metric | Value |
|--------|--------|-------|
| GEPA benchmark | Test coverage (discrete) | 52.33% |
| HoVer baseline (n=4) | Test coverage (discrete) | 51.65% |
| SS-v2 best (10-step) | Val fitness (soft) | 86.44% |
| SS-v2 best 7-step chain | Val fitness (soft) | ~78.4% |
| Dynamic-topology treatment (10-step) | Test coverage (discrete) | 60.37% mean |

---

## 14. Open Questions / Risks

### Priority risks

**Risk 1 -- 7-step budget may be too tight for meaningful topology variation (MEDIUM).**
With only 7 step slots, the structural space is significantly smaller than with 10 steps. The number of meaningfully different architectures (different dependency graphs, different tool/LLM mixes) may be too small to benefit from topology freedom. The seed program already uses all 7 steps efficiently (3 tool + 4 LLM, sequential dependencies).

**Mitigation**: Report the distribution of `n_steps`, `n_tool_steps`, `dag_depth`, and `n_deep_retrieval` across treatment runs at gen 25. If treatment programs are structurally homogeneous (e.g., >80% have the same architecture), the 7-step budget is too constraining for topology variation.

**Risk 2 -- Mutation LLM may not perform topology mutations within 7 steps (MEDIUM).**
Adding a step when already at max (7) requires first removing another step. This two-step mutation (remove + add) may be beyond the LLM's single-mutation capability. The LLM may default to prompt-only changes.

**Mitigation**: Monitor n_steps and step-type distributions from gen 1 onward. If no topology changes are observed by gen 5, this risk is binding. Unlike the 10-step experiment where the LLM could freely add steps, the 7-step cap creates a "mutation bottleneck" that may limit structural exploration.

**Risk 3 -- Control fitness ceiling may be too low for meaningful comparison (LOW-MEDIUM).**
SS-v2 data suggests 7-step chains plateau around ~78% val. If the control reaches this ceiling early (by gen 10), additional generations are wasted. The treatment may show improvement simply because topology freedom finds a slightly different path to the same ceiling.

**Mitigation**: Compare val fitness trajectories. If both conditions plateau at similar levels, the result is NULL regardless of the trajectory shape. Report the gen at which each condition plateaus.

**Risk 4 -- N=2 is inconclusive (HIGH).**
MDE = 4.4pp at conservative SD. Only STRONG POSITIVE effects are marginally detectable at N=2.

**Mitigation**: Pre-committed extension to N=4 (Section 8).

**Risk 5 -- Cell-count matching via `primary_resolution=60` changes control dynamics (LOW).**
Default control uses 150 fitness bins; this experiment uses 60 to match treatment. With 75 archive slots and 60 bins, average occupancy is ~1.25 programs/bin (vs. ~0.5 at 150 bins). This increases within-bin competition relative to prior experiments.

**Mitigation**: 60 bins is still fine-grained enough for fitness discrimination (each bin covers ~1.7% of the fitness range). The increased within-bin competition may slightly improve control fitness by being more selective. If this is a concern, a post-hoc sensitivity check can compare the control against map-elites-topology's control (150 bins, 10-step) adjusting for the step-budget difference.

### Scientific open questions after this experiment

| Result pattern | Interpretation | Next experiment |
|---------------|----------------|-----------------|
| Treatment > control, high diversity | Topology flexibility at 7 steps is productive; the dynamic-topology gain is NOT purely a step-budget effect | Compare 7-step-flexible vs. 10-step-flexible to quantify step-budget contribution |
| Treatment > control, low diversity | Improvement from unfreezing tool steps (editable retrieval params), not from topological variety | Focused: static 7-step with unfrozen tool steps vs. frozen |
| Treatment ~ control, high diversity | Topology explored but no fitness benefit; 7-step static topology is near-optimal | The dynamic-topology gain was primarily a step-budget effect; close 7-step topology line |
| Treatment ~ control, low diversity | Mutation LLM cannot vary topology at 7 steps; IV was not active | Add explicit topology mutation hints or implement programmatic topology operators |
| Treatment < control | Topology freedom at 7 steps is harmful -- removing frozen-step structural prior is destructive at tight budgets | Fixed topology may be necessary at low step counts; topology freedom requires slack (10+ steps) |

---

## Appendix A: Code Verification Required Before Launch

1. **`chains/hover/full7/` correctness**: Verify `FULL7_CHAIN_CONFIG["max_steps"] == 7`. All other config fields must match `chains/hover/full/config.py` exactly.

2. **`topology_3d_7step.yaml` correctness**: Verify the config resolves correctly with `--cfg job`. Behavior space keys must be `[dag_depth, max_dependency_fan_in, n_deep_retrieval]`, bounds `[[1, 7], [1, 6], [0, 4]]`, resolution `[4, 3, 5]`.

3. **Seed program identity**: The seed program in `chains/hover/full7/initial_programs/` must be functionally identical to `chains/hover/static_soft/initial_programs/` (same 7-step topology, same prompts). The only difference is absence of `frozen` fields.

4. **Scoring equivalence on seed program**: Run the seed through both `static_soft/validate.py` and `full7/validate.py` on 50 samples. Soft fitness must match to within +/-0.01.

5. **max_steps enforcement**: Verify that `full7/validate.py` rejects programs with >7 steps.

6. **Control `primary_resolution=60`**: Verify via `--cfg job` that control runs have 60 fitness bins.

7. **`ChainStructuralMetricsStage` on all arms**: Verify via `--cfg job` that all 4 runs use `pipeline=structural_metrics`.

8. **Redis DBs 3-6**: Must show 0 keys after archival and flush.

9. **Hydra config verification for all 4 runs**: `--cfg job` check of `evolution: steady_state`, `scheduling: lpt`, correct `algorithm` and `problem.name` per condition.

---

## Appendix B: Relationship to Prior Experiments

```
hover/dynamic-topology (PR #116, POSITIVE +6pp)
  IV: topology freedom (10-step full vs. 7-step static)
  Confound: step budget asymmetry (10 vs. 7)
      |
      v
hover/7step-dynamic (THIS EXPERIMENT)
  IV: topology freedom (7-step full7 vs. 7-step static)
  Controls for: step budget (both 7 steps)
  Question: Is the dynamic-topology gain from flexibility or step budget?
      |
hover/map-elites-topology (PR #142, NULL +0.50pp)
  IV: archive indexing (3D BC vs. 1D fitness)
  Both conditions: 10-step full, topology free
  Finding: structural BC alone does not improve fitness
```

If this experiment is POSITIVE: the dynamic-topology gain comes (at least partly) from topology flexibility itself, not just the expanded step budget. The result would justify further investigation of topology mutation operators and structural search strategies.

If this experiment is NULL: the dynamic-topology gain was primarily a step-budget effect. The 7-step topology, whether frozen or free, reaches the same fitness ceiling. Future work should focus on increasing the step budget (or improving the mutation LLM's ability to use it) rather than topology flexibility per se.

---

*Ready for Reviewer-2's scrutiny.*
