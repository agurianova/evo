# Technical Codebase Map: heilbron/adversarial-repro-v1

**Research question**: Does replicating v1's hyperparameters + fitness + drift-cap-no-op reproduce the 0.0365 result under the current library with all early-death bugs fixed?

---

## 1. Pipeline Resolution Chain

Config: `config/pipeline/heilbron_repro_v1.yaml`

| Layer | File | Key Contributions |
|---|---|---|
| 1 (innermost) | `config/pipeline/adversarial_coevo.yaml` | `pre_step_hook: MainRunSyncHook` (OVERRIDDEN by layer 3); `opponent_provider: RedisOpponentArchiveProvider`; `evolution_context: EvolutionContext`; `pipeline_builder: AdversarialPipelineBuilder`; `dag_blueprint: build_dag_from_builder`; sets `opponent_redis_db: ???` and `opponent_redis_prefix: ???` as required Hydra interpolations |
| 2 | `config/pipeline/adversarial_asymmetric.yaml` | Overrides `pre_step_hook` to `ProgressBasedSyncHook` with `min_delta: ${sync_min_delta}` (from constants, default=8); adds `feedback_mode: "composition"`, `population_role: "constructor"`, `n_opponents: 1`, `source_prompt_k: 1`, `d_sees_g_source: false`, `d_archive_persistent: false`, `inner_iterations: 1`; adds `dg_tracker: DGImprovementTracker`; adds `composition_injection_hook: CompositionInjectionHook`; overrides `pipeline_builder` to `AdversarialAsymmetricPipelineBuilder` with `archive_reeval: false` |
| 3 (outermost) | `config/pipeline/heilbron_repro_v1.yaml` | Overrides `pre_step_hook` to `ProgressBasedSyncHook` with `drift_cap: 100000`, `own_db: ${redis.db}`, `own_prefix: ${redis.prefix}`, `min_delta: null` (silences deprecation); locks `inner_iterations: 1`, `n_opponents: 1`, `source_prompt_k: 1` |

**`adversarial_asymmetric.yaml` does NOT set `own_db`/`own_prefix` on its hook** — this is a gap that heilbron_repro_v1.yaml fixes by setting them explicitly (line 63-64).

---

## 2. Entry Points — Where Treatment Knobs Fire

### `inner_iterations`

- **Where consumed**: NOWHERE in gigaevo Python code. `grep -rn "inner_iterations" gigaevo/` returns zero matches.
- **What it is**: A top-level Hydra key that appears in pipeline YAMLs and experiment configs. It was intended to parameterize inner iteration loops in D, but that loop was never implemented (v1 01_design.md §1a explicitly notes the loop was a planned but unbuilt component). The key is present purely as a config value — it is NEVER read by any Python class.
- **v1 "K=1 bug"**: The 01_design.md said K=5 but K=1 ran. This was NOT a code bug — `inner_iterations=1` was always in the config; the K=5 design was never implemented in code. The key is a no-op config decoration.
- **Blast radius**: Zero. Changing this value has no effect on runtime behavior.

### `n_opponents`

- **Primary consumer**: `AdversarialAsymmetricPipelineBuilder.__init__()` at `gigaevo/adversarial/asymmetric_pipeline.py:81` receives it from Hydra via `pipeline_builder.n_opponents` interpolation.
- **Passed to**: `AdversarialPipelineBuilder.__init__()` → `_add_adversarial_stages(opponent_provider, n_opponents, ...)` → `FetchOpponentIdsStage(n_opponents=n)` and `FetchOpponentResultsStage(n_opponents=n)`.
- **Effect**: `FetchOpponentIdsStage.compute()` calls `get_top_k(n_opponents)` — controls how many G programs D evaluates against, and how many opponent results flow to `evaluate.py` as the `opponent_results` list.
- **Blast radius**: Changes the number of opponents in the `opponent_results` list passed to evaluate.py. At `n_opponents=1` (v1 setting), each program is evaluated against exactly 1 opponent.

### `source_prompt_k`

- **Consumer**: `AdversarialAsymmetricPipelineBuilder._add_source_injection()` at `asymmetric_pipeline.py:159`, which constructs `SourceCodeInjectionStage(source_prompt_k=l)`.
- **Effect**: Controls how many G source codes are shown in D's mutation prompt (top-L by fitness). Only active for `population_role=improver` runs.
- **At `source_prompt_k=1`**: D sees exactly 1 G source code (the best opponent by fitness).

### `drift_cap`

- **Consumer**: `ProgressBasedSyncHook.__init__()` at `gigaevo/adversarial/sync.py:71`.
- **Effect**: Blocks own population while `own_programs_processed - min(opponent_programs_processed) > drift_cap`. At `drift_cap=100000` (v1 no-op), the condition is never triggered for realistic run sizes (~400 programs total), preserving v1's unthrottled asymmetric compute rate.
- **Log signature**: `[ProgressBasedSyncHook] Init | own=db=... drift_cap=100000` at startup.
- **Requirement**: `own_db` and `own_prefix` must be set — heilbron_repro_v1.yaml provides these as `${redis.db}` and `${redis.prefix}`.

### `feedback_mode=composition|gradient_in_prompt`

- **Consumer**: `AdversarialAsymmetricPipelineBuilder.__init__()` at `asymmetric_pipeline.py:80`, via `pipeline_builder.feedback_mode` interpolation.
- **Arm A (composition)**:
  - G runs: NO pipeline-level change. `CompositionInjectionHook` is wired as `post_step_hook` via `composition_injection_hook` config key — but only if the launch.sh explicitly passes it as `post_step_hook` override. The pipeline builder itself adds nothing for G+composition.
  - D runs: `SourceCodeInjectionStage` is added (triggered by `population_role=improver`, not by feedback_mode).
- **Arm C (gradient_in_prompt)**:
  - G runs: `GradientInPromptStage` is added at `asymmetric_pipeline.py:107-113`. Reads D's archive via `d_provider` (same as `opponent_provider`). Injects best-D-for-this-G source code into G's mutation prompt.
  - D runs: same as Arm A.
- **Default**: If `feedback_mode` is absent from config, `adversarial_asymmetric.yaml` defaults it to `"composition"`.

### `population_role=constructor|improver`

- **Consumer**: `AdversarialAsymmetricPipelineBuilder.__init__()` at `asymmetric_pipeline.py:79`.
- **Divergence point**: Line 102 — `if population_role == "improver": self._add_source_injection(...)`. Line 107 — `if population_role == "constructor" and feedback_mode == "gradient_in_prompt": self._add_gradient_prompt(...)`.
- **For `improver`**: adds `SourceCodeInjectionStage` between `FormatterStage` and `MutationContextStage`; adds `DGTrackerStage`, `ComputeDWinsCountStage`, `MergeCoverageMetricsStage`, `SharedBenchmarkLineageStage`.
- **For `constructor`**: adds `DGTrackerStage`, `ComputeGResistedCountStage`, `MergeCoverageMetricsStage`. If Arm C, also `GradientInPromptStage`.
- **Default**: If absent, defaults to `"constructor"` (from `adversarial_asymmetric.yaml:79`).
- **KF-03**: Missing `population_role` causes the constructor default to fire silently — all runs become G.

### `d_sees_g_source`

- **Consumer**: NOWHERE in gigaevo Python code. `grep -rn "d_sees_g_source" gigaevo/` returns zero matches. This key is only in YAML configs and experiment docs.
- **What it ACTUALLY means**: Its presence/absence in the launch command signals the intent. The ACTUAL mechanism is `population_role=improver` — that is what triggers `SourceCodeInjectionStage`. `d_sees_g_source=true` is a documentation/tagging convention, not a runtime switch.
- **Risk**: There is NO code that reads `d_sees_g_source`. For D runs to see G source, the critical config is `population_role=improver` (which adds `SourceCodeInjectionStage`). If `d_sees_g_source=true` is set but `population_role` is wrong, source injection silently doesn't happen.

### `d_archive_persistent`

- **Consumer**: NOWHERE in gigaevo Python code. `grep -rn "d_archive_persistent" gigaevo/` returns zero matches.
- **What it ACTUALLY means**: Same as `d_sees_g_source` — a documentation convention. D's archive persists by default in Redis (MAP-Elites archive is never reset between generations unless explicitly cleared). There is no code that conditionally enables/disables persistence based on this key.
- **Risk**: This key is a no-op config decoration. Archive persistence is always on in the current engine.

---

## 3. Silent Fallback Modes

| Knob | Missing / Typo'd | What Happens |
|---|---|---|
| `feedback_mode` absent | `adversarial_asymmetric.yaml` default: `"composition"`. Silently runs Arm A. | No crash; wrong arm runs without warning. |
| `feedback_mode="gradient_in_prompt"` on improver | `population_role=="improver"` branch fires; feedback_mode branch only checks constructor. No GradientInPromptStage added. D run unaffected. | Correct — not a silent bug, just an irrelevant key for D. |
| `population_role` absent | Default `"constructor"` fires. All runs become G. D runs never add SourceCodeInjectionStage. | Silent wrong-role execution. KF-03. |
| `population_role` typo (e.g. "Improver") | Neither branch condition matches. No source injection, no gradient prompt. Silently runs as bare AdversarialPipelineBuilder + DGTrackerStage. | No crash; source injection silently disabled. |
| `d_sees_g_source` absent or false on D run | No effect — key is never read by Python. Source injection is controlled solely by `population_role=improver`. | Purely cosmetic; no runtime impact. |
| `d_archive_persistent` absent or false on D run | No effect — key is never read by Python. Archive always persists. | Purely cosmetic; no runtime impact. |
| `inner_iterations` missing | No effect — key is never read by Python. | No-op. |
| `drift_cap` missing (ProgressBasedSyncHook) | `ProgressBasedSyncHook.__init__()` raises `ValueError: ProgressBasedSyncHook requires 'drift_cap' ... to be set explicitly`. HARD CRASH at startup. | Safe — fails loudly. |
| `drift_cap=null` + `min_delta` also null | Same ValueError. HARD CRASH. | Safe — fails loudly. |
| `min_delta: null` (with `drift_cap` set) | Deprecation warning suppressed — this is the intentional pattern in heilbron_repro_v1.yaml. No crash. | Correct behavior. |
| `own_db` / `own_prefix` missing on hook | `ProgressBasedSyncHook` uses them in `_get_own_progress()`. Without them, own progress reads wrong DB. | Incorrect sync behavior — own progress always reads 0, hook never blocks. Runs proceed as if solo. **NOT in `adversarial_asymmetric.yaml` — that config does NOT set `own_db`/`own_prefix`.** Fixed in `heilbron_repro_v1.yaml` which explicitly wires `own_db: ${redis.db}` and `own_prefix: ${redis.prefix}`. |
| `n_opponents=0` | `FetchOpponentIdsStage.get_top_k(0)` returns empty list. `FetchOpponentResultsStage` uses fallback codes. `evaluate.py` receives `opponent_results=[]`. For pop_a: `no_opponent_results` branch returns `fitness=quality, resistance=1.0`. For pop_b: returns `INVALID`. | Silent degradation to solo mode for G; crash-sentinel for D. |
| `source_prompt_k` missing | `AdversarialAsymmetricPipelineBuilder` default is `source_prompt_k=1`. No crash. | Safe default. |

### CRITICAL SILENT FALLBACK: `own_db`/`own_prefix` gap in `adversarial_asymmetric.yaml`

`adversarial_asymmetric.yaml` (layer 2) overrides `pre_step_hook` to `ProgressBasedSyncHook` but does NOT set `own_db`/`own_prefix`. The heilbron_repro_v1.yaml (layer 3) fixes this. However, if anyone runs `pipeline=adversarial_asymmetric` directly (not via repro_v1), the own-progress tracking is broken. This is NOT a repro_v1 concern but is worth flagging for other experiments.

---

## 4. Frozen Problem Dir Integrity Check

### Directory structure

Both `problems/heilbron_repro_v1/pop_a/` and `.../pop_b/` exist and contain:
- `evaluate.py` — present (3.7K and 3.2K respectively)
- `helper.py` — present (both 1.4K)
- `metrics.yaml` — present (both 2.3K)
- `task_description.txt` — present (3.4K and 3.5K)
- `fallback/` — present in both
- `initial_programs/` — present in both

### Fitness formula audit — pop_a (Constructor)

File: `problems/heilbron_repro_v1/pop_a/evaluate.py`

- **Resistance formula** (line 95): `resistance_scores.append(float(delta <= 0))` — HARD FLOOR binary {0, 1}
- **Fitness formula** (line 107): `fitness = ALPHA * quality + (1.0 - ALPHA) * resistance` where `ALPHA=0.5`
- **No `tanh`**: Confirmed absent.
- **No `smooth`**: Confirmed absent.
- **Quality formula** (line 61): `quality = min(raw_quality / Q_MAX, 1.0)` — continuous, capped at 1.0
- **G fitness range**: {0.0 to 1.0}, with mass at two "strips": quality-axis (continuous) + resistance contribution (0 or 0.5). NOT a pure binary — quality provides continuous gradient.

### Fitness formula audit — pop_b (Improver)

File: `problems/heilbron_repro_v1/pop_b/evaluate.py`

- **D fitness formula** (line 78): `scores.append(min(max(delta, 0.0) / Q_MAX, 1.0))` — HARD FLOOR at 0.0
- **Mean fitness** (line 89): `fitness = sum(scores) / len(scores)`
- **No `tanh`**: Confirmed absent.
- **No `smooth`**: Confirmed absent.
- **Known structural defect** (from PATTERNS.md): At `n_opponents=1` and typical deltas, 60-90% of D programs score exactly 0.0. Point-mass collapse confirmed.

### Metrics schema (v1)

- **pop_a metrics.yaml**: Has `fitness`, `is_valid`, `actual_fitness`, `quality`, `resistance`, `mean_improvement`, `best_post_improvement`, `n_opponents`. NO `wins` key.
- **pop_b metrics.yaml**: Has `fitness`, `is_valid`, `actual_fitness`, `mean_improvement_raw`, `mean_pre_quality`, `mean_post_quality`, `max_post_quality`, `n_opponents`. NO `wins` key.
- **`wins` absent**: The `dg_tracker` wired in `adversarial_asymmetric.yaml` adds `ComputeGResistedCountStage`/`ComputeDWinsCountStage` which write `wins` into program.metrics. `EnsureMetricsStage` validates only keys in `metrics.yaml specs` — `wins` is NOT in v1 metrics.yaml, so it is silently ignored and not persisted. The tracker stages add overhead but do not crash.

---

## 5. Fitness Computation Path

```
Pipeline step (SteadyStateEvolutionEngine epoch)
  └─ DAG for each program
       ├─ ValidateCodeStage
       ├─ CallProgramFunction          ← runs entrypoint(), gets point config / callable
       ├─ FetchOpponentIdsStage        ← get_top_k(1) from opponent Redis archive
       ├─ FetchOpponentResultsStage    ← executes opponent entrypoint() in subprocess
       │    └─ runs opponent code via run_exec_runner, returns list of results
       ├─ CallValidatorFunction        ← calls evaluate(opponent_results, program_output)
       │    └─ evaluate.py is the frozen v1 file
       │    └─ returns dict {fitness, is_valid, actual_fitness, ...}
       ├─ MergeMetricsStage            ← merges evaluate() output with program fields
       ├─ [MergeCoverageMetricsStage]  ← merges wins (from DGTrackerStage); wins ignored by EnsureMetrics
       └─ EnsureMetricsStage           ← validates required keys (from metrics.yaml), clamps to bounds
            └─ program.metrics["fitness"] = float(ALPHA*quality + (1-ALPHA)*resistance)
```

**No post-processing normalization** between evaluate.py output and Redis storage. The `fitness` value stored in the archive IS the value returned by evaluate.py, after EnsureMetricsStage clamps to `[lower_bound, upper_bound]` defined in metrics.yaml (pop_a: [0.0, 1.0]; pop_b: [0.0, 1.0]).

---

## 6. Runtime Verification Checks

| Check | What to Look For | Location |
|---|---|---|
| X.1: `drift_cap=100000` reached hook | Log line at startup: `[ProgressBasedSyncHook] Init \| own=db=N prefix='...' opponents=[...] drift_cap=100000 sync_every=1epochs` | stdout / run log, first 10 lines |
| X.2: `inner_iterations=1` "consumed" | Config dump (`--cfg job`) shows `inner_iterations: 1`. No log line from Python — key is never read. Verify config dump, not log. | `python run.py ... --cfg job \| grep inner_iterations` |
| X.3: `feedback_mode` routing | For Arm C G runs: `[GradientInPrompt] injecting D into G prompt` after gen >=1 (once tracker has data). For Arm A G runs: `[CompositionInjection] mutation_type=d_improvement` in log after gen >=1. For D runs: `[SourceCodeInjection] showing N/M opponents` after gen >=1. | run log, search these patterns |
| X.4: `d_sees_g_source=true` → SourceCodeInjection active | `[AsymmetricPipeline] role=improver feedback=... source_prompt_k=1` at startup. Then `[SourceCodeInjection] showing 1/1 opponents (top fitness=...)` per D epoch. | run log, startup + per-epoch |
| X.5: Hard-floor fitness distribution for D | Redis scan of D programs: fitness values should cluster at 0.0 (60-90% expected from PATTERNS.md). G fitness values should be in (0.0, 1.0) range (continuous quality axis, binary resistance component). Verify with `gigaevo -r "prefix@db" programs --metric fitness` | Redis, D programs after gen 2+ |
| X.6: Asymmetric generation rate | D should reach ~2x more generations than G in same wallclock. Verify `engine:total_generations` in Redis for both DBs at same timestamp. | `gigaevo -r "prefix@db" state` for both pops |
| X.7: `population_role` correctly set per run | Startup log: `[AsymmetricPipeline] role=constructor feedback=...` (G runs), `[AsymmetricPipeline] role=improver feedback=...` (D runs). | run log, first 5 lines |

---

## 7. Blast Radius of Proposed Changes

No existing Python code is being modified. All changes are:
1. New frozen problem dirs (`problems/heilbron_repro_v1/`) — already exist.
2. New pipeline config (`config/pipeline/heilbron_repro_v1.yaml`) — already exists.
3. Runs use existing `AdversarialAsymmetricPipelineBuilder`, `ProgressBasedSyncHook`, etc. — no code changes.

**Blast radius: ZERO** — read-only use of existing classes.

---

## 8. Feasibility Assessment

**Rating**: YELLOW

**Rationale**:

The config resolution chain is correct and complete. All required Python entry points exist and are wired. The frozen problem dirs are present with the correct hard-floor evaluate.py. The `drift_cap=100000` no-op is correctly implemented and will log clearly at startup.

Three concerns prevent GREEN:

1. **`inner_iterations` is a no-op** (YELLOW, not RED): The config says `inner_iterations: 1`, but this key is never consumed by any Python code in `gigaevo/`. It is a documentation artifact. This means the experiment correctly replicates v1's actual behavior (K=1 = no inner loop), but any future attempt to set `inner_iterations > 1` to test the K=5 design will silently have no effect. Elena's treatment spec should explicitly note this is a config-only placeholder.

2. **`d_sees_g_source` and `d_archive_persistent` are no-op config keys** (YELLOW): Both are never read by Python. The actual mechanism is `population_role=improver`, which must be set in the launch command. If a launch.sh sets `d_sees_g_source=true` but omits `population_role=improver`, source injection silently doesn't happen. Treatment verification must check for `[SourceCodeInjection] showing` in the log, not for the presence of these config keys.

3. **D hard-floor fitness collapse is EXPECTED** (informational, not a blocker): The frozen pop_b evaluate.py produces 60-90% point-mass at fitness=0.0. This was the structural defect identified in k5-budget-loose. Replication WILL reproduce this collapse. The experiment is asking whether the 0.0365 G result reproduces despite D collapse — which it did in v1. Monitor G actual_fitness, not D fitness.

**No RED blockers** — the pipeline wiring is sound, the config hierarchy is correct, and `drift_cap` fails loudly if misconfigured.

---

## 9. Recommended Treatment Specification

**Config verification**: Run `python run.py problem.name=heilbron_repro_v1/pop_a pipeline=heilbron_repro_v1 ... --cfg job` and verify:
- `drift_cap: 100000` (not 8 from the constants default)
- `min_delta: null` (deprecation warning silenced)
- `n_opponents: 1`
- `source_prompt_k: 1`
- `inner_iterations: 1`
- `feedback_mode: composition` (Arm A) or `gradient_in_prompt` (Arm C)
- `population_role: constructor` (G) or `improver` (D)

**Per-run launch overrides**:
- G runs: `population_role=constructor feedback_mode=composition|gradient_in_prompt`
- D runs: `population_role=improver feedback_mode=composition|gradient_in_prompt d_sees_g_source=true d_archive_persistent=true`

**Note on `d_sees_g_source`/`d_archive_persistent`**: These are documentation-only; include in launch.sh for experiment record-keeping but do not rely on them for mechanism activation. The activating knob is `population_role=improver`.

**Stopper**: `stopper=max_generations_or_fitness_plateau max_generations=50` — confirm this stopper exists in `config/stopper/`.

---

## 10. Existing Code Patterns to Reuse

| Prior Experiment | Pattern Used | Reuse for Repro-V1 |
|---|---|---|
| `heilbron/asymmetric-iterations` (v1, PR #204) | `pipeline=adversarial_asymmetric evolution=steady_state` + per-run `population_role` + `d_sees_g_source=true d_archive_persistent=true` for D | Copy launch structure verbatim; swap `pipeline=adversarial_asymmetric` for `pipeline=heilbron_repro_v1` and `problem.name=heilbron_adversarial/pop_a` for `heilbron_repro_v1/pop_a` |
| `heilbron/asymmetric-iterations` | 8 runs × 2 arms × 2 roles = 4 pairs | Same structure (4 G + 4 D across 2 pairs × 2 arms) |
| `heilbron/asymmetric-iterations` | `max_generations=50 max_mutations_per_generation=8` | Reuse directly |
| `heilbron/asymmetric-iterations-v2` | `extra_overrides` pattern for D-specific settings in experiment.yaml | Copy this pattern for `population_role`, `d_sees_g_source`, `d_archive_persistent` |

> **Post-closeout note (2026-04-22):** `SharedBenchmarkLineageStage`
> described above has been replaced by
> `SharedBenchmarkFilteredLineageStage`, a drop-in subclass of
> `LineageStage` that filters parents by shared evaluation benchmark
> and injects HoF-invariant per-metric means as `TransitionEvidence`
> into D's lineage prompt. The old scalar-trend design + LINEAGE_TREND
> canonical event have been removed. See
> `docs/superpowers/specs/2026-04-21-shared-benchmark-filtered-lineage-design.md`.
