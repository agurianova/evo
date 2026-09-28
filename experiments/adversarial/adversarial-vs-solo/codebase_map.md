# Codebase Map: Solo MAP-Elites vs Adversarial MAP-Elites on Heilbronn N=11

**Generated**: 2026-04-11
**Research Question**: Does adversarial co-evolution improve `actual_fitness` (raw min_area) over standard (non-adversarial) MAP-Elites on Heilbronn N=11?

---

## Entry Points Table

| Component | File | Class/Function | Purpose |
|---|---|---|---|
| **Standard pipeline builder** | `gigaevo/entrypoint/default_pipelines.py` | `DefaultPipelineBuilder` | Builds DAG: ValidateCode -> CallProgram -> CallValidator(validate.py) -> metrics chain |
| **Adversarial pipeline builder** | `gigaevo/adversarial/pipeline.py` | `AdversarialPipelineBuilder` | Extends DefaultPipelineBuilder: adds FetchOpponentIds + FetchOpponentResults stages, replaces CallValidator to use evaluate.py instead of validate.py |
| **Opponent ID sampling** | `gigaevo/adversarial/stages.py` | `FetchOpponentIdsStage` | NO_CACHE stage: samples opponent IDs from live archive every DAG run |
| **Opponent execution** | `gigaevo/adversarial/stages.py` | `FetchOpponentResultsStage` | InputHashCache: executes opponent code in subprocesses, reruns when opponent IDs change |
| **Opponent archive provider** | `gigaevo/adversarial/opponent_provider.py` | `RedisOpponentArchiveProvider` | Reads opponent programs from Redis MAP-Elites archive, fitness-proportional sampling |
| **Generation sync hook** | `gigaevo/prompts/coevolution/sync.py` | `MainRunSyncHook` | Blocks engine until opponent advances by 1 generation (used by adversarial_coevo pipeline) |
| **Progress sync hook** | `gigaevo/adversarial/sync.py` | `ProgressBasedSyncHook` | Blocks until opponent processes `min_delta` programs (used by adversarial_coevo_ss pipeline) |
| **Validator execution** | `gigaevo/programs/stages/python_executors/execution.py` | `CallValidatorFunction` | Calls validate(program_output) or evaluate(context, program_output) depending on pipeline wiring |
| **Solo Heilbronn validate.py** | `problems/heilbron/validate.py` | `validate(coordinates)` | Returns `{"fitness": min_area, "is_valid": 1, ...layout_metrics}` -- standard pipeline compatible |
| **Solo Heilbronn helper** | `problems/heilbron/helper.py` | `get_unit_triangle`, `get_smallest_triangle_area`, `is_inside_triangle` | Shared geometry utilities |
| **Adversarial Pop A evaluate.py** | `problems/heilbron_adversarial/pop_a/evaluate.py` | `evaluate(opponent_results, program_output)` | `fitness = 0.5*quality + 0.5*resistance` (binary). `actual_fitness` = raw min_area |
| **Adversarial Pop B evaluate.py** | `problems/heilbron_adversarial/pop_b/evaluate.py` | `evaluate(opponent_results, program_output)` | `fitness = mean(normalized_improvement)`. Pop B evolves improve() callables |
| **GAN variant Pop A** | `problems/heilbron_adversarial/pop_a_gan/evaluate.py` | `evaluate(opponent_results, program_output)` | `fitness = sigmoid_resistance` (pure D signal, no quality). `actual_fitness` tracked separately |
| **Soft variant Pop A** | `problems/heilbron_adversarial/pop_a_soft/evaluate.py` | `evaluate(opponent_results, program_output)` | `fitness = 0.5*quality + 0.5*sigmoid_resistance`. Same structure as pop_a but sigmoid instead of binary |
| **Standard pipeline YAML** | `config/pipeline/standard.yaml` | -- | Uses DefaultPipelineBuilder. No sync hook, no opponent wiring |
| **Adversarial pipeline YAML** | `config/pipeline/adversarial_coevo.yaml` | -- | Requires `opponent_redis_db`, `opponent_redis_prefix`. Adds sync hook + opponent_provider + AdversarialPipelineBuilder |
| **Default pre_step_hook** | `config/constants/evolution.yaml` | `pre_step_hook: null` | Standard pipeline inherits null hook (no blocking) |

---

## Hydra Wiring

### Standard (Solo) Pipeline

```
pipeline=standard
  -> config/pipeline/standard.yaml
  -> pipeline_builder._target_ = DefaultPipelineBuilder
  -> CallValidatorFunction reads problem.dir/validate.py
  -> calls validate(program_output) -> dict
  -> pre_step_hook: null (from config/constants/evolution.yaml)
```

**DAG stages (standard)**:
```
ValidateCodeStage -> CallProgramFunction -> CallValidatorFunction(validate.py)
                                        -> FetchMetrics -> MergeMetrics -> EnsureMetrics
                                        -> InsightsStage, LineageStage, etc.
```

### Adversarial Pipeline

```
pipeline=adversarial_coevo
  -> config/pipeline/adversarial_coevo.yaml
  -> pipeline_builder._target_ = AdversarialPipelineBuilder
  -> Replaces CallValidatorFunction to use evaluate.py (not validate.py)
  -> Adds: FetchOpponentIdsStage -> FetchOpponentResultsStage -> CallValidatorFunction(context)
  -> pre_step_hook: MainRunSyncHook (blocks until opponent advances)
  -> requires: opponent_redis_db, opponent_redis_prefix
```

**DAG stages (adversarial) -- additional stages**:
```
ValidateCodeStage -> FetchOpponentIdsStage (NO_CACHE, parallel with CallProgramFunction)
                  -> FetchOpponentResultsStage (opponent_ids input)
                  -> CallValidatorFunction(evaluate.py) receives:
                       payload = program_output (from CallProgramFunction)
                       context = opponent_results (from FetchOpponentResultsStage)
                     calls: evaluate(opponent_results, program_output) -> dict
```

**Critical wiring detail**: `CallValidatorFunction._build_call()` passes `context` as the first argument when present. So:
- Standard: `validate(program_output)`
- Adversarial: `evaluate(opponent_results, program_output)` where opponent_results = context from FetchOpponentResultsStage

---

## Treatment Specification

### Solo arm (Control)

```bash
python run.py \
  problem.name=heilbron \
  pipeline=standard \
  redis.db=<DB> \
  max_generations=50 \
  llm_base_url=http://10.232.30.185:4000/v1 \
  model_name=Qwen3-235B-A22B-Thinking-2507 \
  stage_timeout=3000 \
  dag_timeout=7200 \
  max_elites_per_generation=8 \
  max_mutations_per_generation=8 \
  mutation_mode=rewrite
```

- Uses `problems/heilbron/validate.py` which returns `{"fitness": min_area, ...}`
- `fitness` = raw `min_area` directly
- No sync hook, no opponents
- Programs are `entrypoint() -> (11,2) np.ndarray`

### Adversarial arm (Treatment)

Two paired runs per replicate:

**Constructor (Pop A):**
```bash
python run.py \
  problem.name=heilbron_adversarial/pop_a \
  pipeline=adversarial_coevo \
  redis.db=<DB_A> \
  opponent_redis_db=<DB_B> \
  opponent_redis_prefix=heilbron_adversarial/pop_b \
  max_generations=50 \
  pipeline_builder.per_opponent_timeout=300 \
  llm_base_url=http://10.232.30.185:4000/v1 \
  model_name=Qwen3-235B-A22B-Thinking-2507 \
  stage_timeout=3000 \
  dag_timeout=7200 \
  max_elites_per_generation=8 \
  max_mutations_per_generation=8 \
  mutation_mode=rewrite
```

- Uses `problems/heilbron_adversarial/pop_a/evaluate.py`
- `fitness = 0.5*quality + 0.5*resistance` (drives MAP-Elites selection)
- `actual_fitness` = raw min_area (comparison DV)
- Programs: `entrypoint() -> (11,2) np.ndarray`

**Improver (Pop B):**
```bash
python run.py \
  problem.name=heilbron_adversarial/pop_b \
  pipeline=adversarial_coevo \
  redis.db=<DB_B> \
  opponent_redis_db=<DB_A> \
  opponent_redis_prefix=heilbron_adversarial/pop_a \
  max_generations=50 \
  pipeline_builder.per_opponent_timeout=300 \
  llm_base_url=http://10.232.30.185:4000/v1 \
  model_name=Qwen3-235B-A22B-Thinking-2507 \
  stage_timeout=3000 \
  dag_timeout=7200 \
  max_elites_per_generation=8 \
  max_mutations_per_generation=8 \
  mutation_mode=rewrite
```

- Uses `problems/heilbron_adversarial/pop_b/evaluate.py`
- Programs: `entrypoint() -> callable(improve)` where `improve(points) -> improved_points`

### Primary Dependent Variable

For comparison: `actual_fitness` (raw min_area) from the Constructor arm vs `fitness` (= raw min_area) from the Solo arm. These are directly comparable -- both are the min_area of the best point configuration.

---

## Problem Variant Assessment

### Does a solo Heilbronn problem variant already exist?

**YES.** `problems/heilbron/` is a complete, non-adversarial Heilbronn N=11 problem directory:

| File | Status | Notes |
|---|---|---|
| `validate.py` | EXISTS | Returns `{"fitness": min_area, "is_valid": 1, ...metrics}` -- standard pipeline compatible |
| `metrics.yaml` | EXISTS | Primary: `fitness` (min_area), range [0, 0.0365], higher_is_better=true |
| `task_description.txt` | EXISTS | Standard Heilbronn prompt, no adversarial framing |
| `helper.py` | EXISTS | Identical to adversarial helpers (get_unit_triangle, get_smallest_triangle_area, is_inside_triangle) |
| `initial_programs/` | EXISTS | 5 seeds: grid.py, random_arr.py, fan.py, arc.py, cluster.py |

**No new problem directory is needed for the solo arm.**

### Can we reuse `heilbron_adversarial/pop_a` with `pipeline=standard`?

**NO.** The adversarial pop_a directory has NO `validate.py` -- only `evaluate.py`. The standard pipeline explicitly looks for `validate.py` at `problem_dir / "validate.py"` (line 207 of `default_pipelines.py`). Using `pipeline=standard` with `problem.name=heilbron_adversarial/pop_a` would cause a `ValidationError: Validator file not found`.

The correct approach is: use `problems/heilbron/` for the solo arm with `pipeline=standard`.

### Metric comparability

| Arm | Primary metric (MAP-Elites) | Paper DV |
|---|---|---|
| Solo | `fitness` = raw min_area | `fitness` = raw min_area |
| Adversarial | `fitness` = 0.5*quality + 0.5*resistance | `actual_fitness` = raw min_area |

Both arms produce `min_area` as a directly comparable quantity. Solo calls it `fitness`; adversarial calls it `actual_fitness`. The `metrics.yaml` specs confirm the same range [0, 0.0365] and same semantics.

### Initial program comparability

The solo `problems/heilbron/initial_programs/grid.py` and adversarial `problems/heilbron_adversarial/pop_a/initial_programs/grid.py` are **byte-identical**. The solo arm has 4 additional seeds (random_arr, fan, arc, cluster). This is a potential confound: the solo arm starts with 5 seeds vs 1 for adversarial.

**Recommendation**: Either (a) use only `grid.py` for the solo arm too (remove other seeds or use a problem variant with only grid), or (b) document the seed count difference and argue it favors the solo arm (making adversarial wins more impressive).

---

## Implementation Feasibility

### GREEN -- All infrastructure exists. No new code required.

Justification:
1. `problems/heilbron/` exists and is fully compatible with `pipeline=standard`
2. `problems/heilbron_adversarial/pop_a/` + `pop_b/` exist and are proven with `pipeline=adversarial_coevo` (heilbron-prover experiment completed successfully)
3. All config knobs are available via Hydra overrides
4. The primary DV (`actual_fitness` / `fitness`) is directly comparable across arms
5. The heilbron-prover experiment provides a battle-tested reference config

### Implementation work:
- Write `experiment.yaml` with run specs (DB assignments, labels, overrides)
- Write `launch.sh` (can be generated from experiment.yaml)
- Write experiment design docs (01_design, 03_plan)
- No new Python code, no new problem directories, no new pipeline configs

---

## Silent Fallback Modes

### 1. Adversarial cold-start: opponents empty at gen 0

When the adversarial Pop A run starts, Pop B's archive is empty. `FetchOpponentResultsStage` returns `data=[]`. Pop A's `evaluate()` receives an empty `opponent_results` list and falls back to:
```python
if not opponent_results:
    return {"fitness": quality, ..., "resistance": 1.0, ...}
```
This means at gen 0, adversarial fitness = quality only (no resistance pressure). This is expected behavior and not a silent failure -- it's a known warm-up period.

### 2. Fallback opponents in adversarial pipeline

The `AdversarialPipelineBuilder` loads fallback codes from `{problem_dir}/fallback/` if the directory exists. For `pop_a`, there are 2 fallback improvers (`jitter.py`, `local_search.py`). For `pop_b`, there are 3 fallback constructors (`fan.py`, `grid.py`, `random_arr.py`). These are used when the opponent archive is empty. This means the adversarial arm has pre-loaded opponents even at gen 0, unlike a pure cold start.

### 3. Sync hook deadlock risk

The `MainRunSyncHook` blocks until the opponent advances by 1 generation (timeout 7200s = 2h). If one population crashes or stalls, the other will block for up to 2 hours before timing out and proceeding. The heilbron-prover experiment already encountered sync deadlocks (see `adversarial-dynamic-updates` anomaly detector warnings).

**Solo arm is immune to this** -- no sync hook, no deadlock risk.

### 4. Standard pipeline ignores evaluate.py

If someone accidentally uses `pipeline=standard` with `problem.name=heilbron_adversarial/pop_a`, the pipeline will look for `validate.py` (not `evaluate.py`) and fail with `ValidationError: Validator file not found`. This is a HARD failure, not a silent fallback. Good.

### 5. Metric name mismatch in tools

`tools/status.py`, `tools/trajectory.py`, and `tools/comparison.py` read metrics from Redis. For the solo arm, the frontier metric is `valid_frontier_fitness`. For the adversarial arm, you need `valid_frontier_actual_fitness` for the comparable DV. If someone plots `valid_frontier_fitness` across both arms, they'll be comparing min_area (solo) vs composite adversarial fitness (adversarial) -- **not apples-to-apples**.

**Mitigation**: Use `tools/redis2pd.py` to export CSVs and explicitly extract the correct column, or use `tools/top_programs.py --json` and extract `actual_fitness` for adversarial runs.

### 6. Archive re-evaluation inflates adversarial evaluation count

The adversarial pipeline re-evaluates archived programs when opponent IDs change (`archive_reeval: true` by default, which uses `InputHashCache`). This means adversarial programs get re-evaluated more frequently than solo programs, consuming more LLM tokens and wall time per generation. The solo arm has no re-evaluation -- each program is evaluated exactly once. This is not a fairness issue for the research question (we're comparing final `actual_fitness`), but it affects throughput and compute budget.

---

## Recommendations

### For the implementing agent

1. **Use `problems/heilbron/` for the solo arm.** It exists, it's complete, it's standard-pipeline compatible. Do not create a new problem directory.

2. **Match hyperparameters exactly.** Copy all config values from heilbron-prover (`cfg_run_P1_A.txt`):
   - `max_generations=50`, `max_elites_per_generation=8`, `max_mutations_per_generation=8`
   - `stage_timeout=3000`, `dag_timeout=7200`
   - `mutation_mode=rewrite`, `temperature=0.6`, `max_tokens=81920`
   - Same LLM: `Qwen3-235B-A22B-Thinking-2507` at `http://10.232.30.185:4000/v1`

3. **Address the seed count asymmetry.** Solo has 5 initial programs; adversarial Pop A has 1. Options:
   - (a) Copy all 5 solo seeds into adversarial Pop A's initial_programs/ (but only grid.py exists there now)
   - (b) Restrict solo to 1 seed (grid.py only) by creating `problems/heilbron_solo/` with only grid.py
   - (c) Document the asymmetry and accept it (5 seeds advantages solo)
   - **Recommended: (c)** -- the solo arm having more seeds is a conservative choice that biases against the adversarial hypothesis

4. **DB allocation.** Need at minimum 4 DBs for 2 replicates (1 solo replicate = 1 DB, 1 adversarial replicate = 2 DBs). Suggested:
   - Solo A: DB 5, Solo B: DB 6
   - Adversarial pair 1: DB 1 (Pop A), DB 2 (Pop B)
   - Adversarial pair 2: DB 3 (Pop A), DB 4 (Pop B)
   Total: 6 DBs

5. **Run design**: 2 replicates per arm minimum (N=2). Each adversarial replicate needs a Pop A + Pop B pair. Each solo replicate is a single run.

6. **Primary DV for comparison**: Extract `fitness` from solo runs and `actual_fitness` from adversarial Pop A runs. Both are raw min_area on the same scale [0, 0.0365].

7. **Do NOT use `adversarial_coevo_ss` pipeline** unless steady-state is also being tested. The heilbron-prover used `adversarial_coevo` (generation-based sync), not `adversarial_coevo_ss` (progress-based sync).

8. **Smoke test both arms** before full launch. Solo: standard quick smoke with `max_generations=3`. Adversarial: smoke both Pop A and Pop B together (they need each other for sync).

### Reference configs

The heilbron-prover experiment provides battle-tested configs at:
- `experiments/adversarial/heilbron-prover/cfg_run_P1_A.txt` (Pop A)
- `experiments/adversarial/heilbron-prover/cfg_run_P1_B.txt` (Pop B)
- `experiments/adversarial/heilbron-prover/experiment.yaml` (full manifest)

The adversarial-dynamic-updates experiment (currently running on branch `exp/heilbron/adversarial-dynamic-updates`) uses GAN/SOFT variants with `ProgressBasedSyncHook` -- a different experimental design. Do not confuse with the standard adversarial_coevo pipeline.
