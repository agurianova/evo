# Technical Codebase Map: heilbron/k5-budget-loose

**Research Question**: Does K=5 compute budget asymmetry (Improver 40 mutations/gen vs Constructor 8) combined with loose G/D coupling (min_delta=1) break Improver stagnation?

**Generated**: 2026-04-16

---

## Mechanism Domain

Two independent config-level changes to the `adversarial_asymmetric` pipeline:
1. **Compute budget asymmetry** — `max_mutations_per_generation` is a global Hydra constant, settable per-run via `extra_overrides`. D runs get 40; G runs keep 8.
2. **Loose coupling** — `min_delta` in `ProgressBasedSyncHook` is wired as `${max_mutations_per_generation}` (Hydra interpolation). Setting `min_delta=1` overrides that interpolation directly on D runs.

---

## Entry Points

| Component | File | Class/Function | Line | Role |
|---|---|---|---|---|
| Progress sync hook | `gigaevo/adversarial/sync.py` | `ProgressBasedSyncHook` | 24 | Pre-step hook: blocks D until G processes `min_delta` programs |
| Sync hook `__call__` | `gigaevo/adversarial/sync.py` | `ProgressBasedSyncHook.__call__` | 111 | Polls `engine:programs_processed` in Redis; blocks or skips |
| Budget constant | `config/constants/evolution.yaml` | `max_mutations_per_generation` | 6 | Default: 8. Global Hydra constant. Override per-run via extra_overrides. |
| Sync coupling constant | `config/constants/evolution.yaml` | `sync_min_delta` | 7 | Default: 8. **Decoupled** from max_mutations_per_generation. Controls ProgressBasedSyncHook min_delta independently. |
| Budget wiring (SS engine) | `config/evolution/steady_state.yaml` | `engine_config.max_mutations_per_generation` | 14 | `${max_mutations_per_generation}` — reads global constant |
| Default wiring (std engine) | `config/evolution/default.yaml` | `engine_config.max_mutations_per_generation` | 23 | Same interpolation |
| Asymmetric pipeline | `config/pipeline/adversarial_asymmetric.yaml` | `pre_step_hook.min_delta` | 67 | `${sync_min_delta}` — decoupled from max_mutations_per_generation |
| SS adversarial pipeline | `config/pipeline/adversarial_coevo_ss.yaml` | `pre_step_hook.min_delta` | 34 | `${sync_min_delta}` — decoupled from max_mutations_per_generation |
| Epoch trigger | `gigaevo/evolution/engine/steady_state.py` | `SteadyStateEvolutionEngine` | 43 | Fires `pre_step_hook.__call__()` every `max_mutations_per_generation` processed programs |
| Asymmetric pipeline builder | `gigaevo/adversarial/asymmetric_pipeline.py` | `AdversarialAsymmetricPipelineBuilder` | — | Builds G/D DAGs; role differentiation via `population_role` |

---

## Hydra Wiring

### How `max_mutations_per_generation` and `sync_min_delta` flow

```
config/constants/evolution.yaml
  max_mutations_per_generation: 8        ← epoch size
  sync_min_delta: 8                      ← sync coupling (DECOUPLED)

config/evolution/steady_state.yaml
  engine_config.max_mutations_per_generation: ${max_mutations_per_generation}

config/pipeline/adversarial_asymmetric.yaml
  pre_step_hook.min_delta: ${sync_min_delta}
```

After the decoupling fix, `max_mutations_per_generation` controls only epoch size. `sync_min_delta` controls only the sync hook's blocking threshold. A per-run override `max_mutations_per_generation=40` does NOT affect `pre_step_hook.min_delta`.

### Treatment config keys

| Key | Config path | Default | Treatment (D) | Control/G |
|---|---|---|---|---|
| `max_mutations_per_generation` | `config/constants/evolution.yaml:6` | 8 | 40 | 8 |
| `sync_min_delta` | `config/constants/evolution.yaml:7` | 8 | 1 | 8 |

**After decoupling fix**: `sync_min_delta` is independent of `max_mutations_per_generation`. D runs override both:
```
max_mutations_per_generation=40   ← epoch size (K=5)
sync_min_delta=1                  ← loose coupling
```

No Hydra interpolation trap — each override controls exactly one parameter.

### Config group that activates this pipeline

```
pipeline=adversarial_asymmetric
evolution=steady_state
```

Both are required. The asymmetric pipeline does NOT include `evolution=steady_state` — that must be in `extra_overrides` for every run.

### Hydra override strings (concrete)

**D run (Improver)**:
```
evolution=steady_state
max_mutations_per_generation=40
sync_min_delta=1
opponent_redis_db=<G_DB>
opponent_redis_prefix=<G_PREFIX>
feedback_mode=composition
population_role=improver
d_sees_g_source=true
d_archive_persistent=true
```

**G run (Constructor)**:
```
evolution=steady_state
max_mutations_per_generation=8
opponent_redis_db=<D_DB>
opponent_redis_prefix=<D_PREFIX>
feedback_mode=composition
population_role=constructor
post_step_hook=\${composition_injection_hook}
```

Note: G runs do NOT set `pre_step_hook.min_delta` — they inherit `${max_mutations_per_generation}=8`, which means G blocks until D processes 8 programs. This is the expected behavior: G waits for D to do a full micro-epoch (8 programs) before G proceeds.

---

## How `ProgressBasedSyncHook` Works with min_delta=1

Source: `gigaevo/adversarial/sync.py:111–179`

1. On first call: records `_last_progress` baseline from opponent's `engine:programs_processed` Redis key, returns immediately (no block).
2. On subsequent calls: blocks until `min_progress >= _last_progress + min_delta`.
3. With `min_delta=1`: D unblocks after G processes just 1 program. D runs essentially free — it can produce 40 mutations per epoch while G still needs 8 programs to complete an epoch.
4. With `min_delta=40`: D would wait until G processes 40 programs before proceeding — since G only produces 8/epoch, D waits ~5 G-epochs. This is "tight coupling."
5. Timeout: 7200s. On timeout, hook resets baseline to current and proceeds — D cannot deadlock permanently.
6. `sync_every_n_epochs=1` in both pipeline YAMLs: hook fires every epoch (no skipping).

**Deadlock safety**: The docstring at line 38-40 warns: `min_delta MUST be <= max_mutations_per_generation to avoid deadlock when both populations wait for each other`. With min_delta=1 and max_mutations_per_generation=40 for D, and min_delta=8 and max_mutations_per_generation=8 for G: both conditions are satisfied (1 <= 40 for D; 8 <= 8 for G). No deadlock risk.

---

## Silent Fallback Modes

| Risk | Description | Detection |
|---|---|---|
| **sync_min_delta not overridden on D** | If `sync_min_delta=1` is omitted from D extra_overrides, default sync_min_delta=8 applies. D runs with tight coupling (min_delta=8), not loose K=5. | Verify in resolved config: `python run.py ... --cfg job` should show `pre_step_hook.min_delta: 1` for D runs. Also check logs for `[ProgressBasedSyncHook] Init | ... min_delta=1`. |
| **evolution=steady_state missing** | Without this override, the default generational engine is used. `pre_step_hook` is null in non-SS configs; programs_processed counter is not published; ProgressBasedSyncHook reads 0 forever → runs free or timeout every 2h. | Check log for `SteadyStateEvolutionEngine`; absent means KF-01 triggered. |
| **KF-05 regression** | KF-05 (min_delta=1 causing massive D desync) was "fixed" by changing the default to `${max_mutations_per_generation}`. This experiment intentionally re-introduces min_delta=1. The fix was a default change, not a guard. min_delta=1 IS the treatment — not a bug in this experiment. | Expected: D runs 5x faster than G. Monitor generation gap in watchdog. |
| **Hydra resolution of `sync_min_delta`** | Pipeline YAMLs now use `${sync_min_delta}` (not `${max_mutations_per_generation}`). Overriding `sync_min_delta=1` on D runs sets min_delta=1 cleanly. No dotted-path override needed. | In resolved config, confirm `pre_step_hook.min_delta: 1` (not `8`). |
| **model_name config drift** | Default `endpoints.yaml` points to OpenRouter. Must override `llm_base_url` and `model_name` per-run or in `config.extra`. | Verify in resolved config or with `--cfg job`. |
| **KF-02: shell expansion of `${...}`** | `extra_overrides` containing `post_step_hook=\${composition_injection_hook}` must use `\${}` notation in experiment.yaml to prevent shell expansion in `generate_launch.py`. The `\` prefix is the fix. | Check generated `launch.sh` — the shell override should appear as `${composition_injection_hook}` (not empty). |

---

## Blast Radius

`ProgressBasedSyncHook` is instantiated by Hydra at run startup via `_target_`. It has no callers at the Python level — it is a Hydra-instantiated singleton. Modifying it would affect:
- d=1: any experiment using `pipeline=adversarial_asymmetric` or `pipeline=adversarial_coevo_ss` (both set `min_delta: ${max_mutations_per_generation}`)
- This experiment does NOT modify the class — it only changes the `min_delta` constructor argument via config override.

**No Python code changes required. Config-only treatment.**

`max_mutations_per_generation` override:
- d=1: `engine_config.max_mutations_per_generation` — controls epoch size in `SteadyStateEvolutionEngine`
- d=1: `pre_step_hook.min_delta` — via interpolation (overridden explicitly for D)
- d=2: `max_elites_per_generation` (separate key, not affected)
- No other components reference `max_mutations_per_generation`

---

## Feasibility Assessment

**Rating: GREEN**

Justification:
1. Both treatment parameters (`max_mutations_per_generation`, `pre_step_hook.min_delta`) are Hydra config keys already wired in the pipeline. No new Python code.
2. The pipeline (`adversarial_asymmetric`) is battle-tested across asymmetric-iterations and asymmetric-iterations-v2 (16 runs).
3. Per-run `extra_overrides` with different values for G vs D is the established pattern (asymmetric-iterations-v2 used it for `inner_iterations`, `d_sees_g_source`, `d_archive_persistent`).
4. The only non-trivial interaction is that `pre_step_hook.min_delta=1` must be explicitly specified on D runs to override the `${max_mutations_per_generation}=40` interpolation. This is a known requirement, not a discovery.
5. KF-01 through KF-06 are all FIXED. KF-05 is intentionally reintroduced as the treatment mechanism (not a failure mode in this context).

---

## Recommended Treatment Specification for Elena

### experiment.yaml `config.extra` section (shared across all runs)

```yaml
config:
  extra:
    num_parents: 1
    max_elites_per_generation: 8
    max_mutations_per_generation: 8    # baseline; D runs override to 40 in extra_overrides
    stage_timeout: 2400
    dag_timeout: 2400
    mutation_mode: rewrite
    significant_change: 0.01
    inner_iterations: 1
    n_opponents: 1
    source_prompt_k: 1
    archive_reeval: false
```

### G run (Constructor) `extra_overrides`

```yaml
extra_overrides:
  - evolution=steady_state
  - opponent_redis_db=<D_DB>
  - opponent_redis_prefix=<D_PREFIX>
  - feedback_mode=composition
  - population_role=constructor
  - post_step_hook=\${composition_injection_hook}
```

`max_mutations_per_generation` is NOT overridden — inherits 8 from `config.extra`. `pre_step_hook.min_delta` inherits `${max_mutations_per_generation}=8`. G waits for D to process 8 programs per epoch.

### D run (Improver) `extra_overrides`

```yaml
extra_overrides:
  - evolution=steady_state
  - max_mutations_per_generation=40
  - sync_min_delta=1
  - opponent_redis_db=<G_DB>
  - opponent_redis_prefix=<G_PREFIX>
  - feedback_mode=composition
  - population_role=improver
  - d_sees_g_source=true
  - d_archive_persistent=true
```

`max_mutations_per_generation=40`: D produces 40 mutations per epoch (K=5 budget).
`sync_min_delta=1`: D unblocks after G processes just 1 program (loose coupling).

### Verification log strings to check post-launch

For D runs:
```
[ProgressBasedSyncHook] Init | sources=[...] min_delta=1 sync_every=1epochs ...
```

For G runs:
```
[ProgressBasedSyncHook] Init | sources=[...] min_delta=8 sync_every=1epochs ...
```

If D log shows `min_delta=40`, the `pre_step_hook.min_delta=1` override was dropped.

---

## Existing Code Patterns to Reuse

| Prior Experiment | Pattern | Reuse |
|---|---|---|
| `heilbron/asymmetric-iterations-v2` | Per-run `extra_overrides` for D-specific settings (`d_sees_g_source`, `d_archive_persistent`, `inner_iterations`) | Copy run structure verbatim; add `max_mutations_per_generation=40` and `pre_step_hook.min_delta=1` to D runs |
| `heilbron/asymmetric-iterations-v2` | `pipeline=adversarial_asymmetric` + `evolution=steady_state` in extra_overrides | Identical pipeline; no change |
| `experiments/adversarial/adversarial-vs-solo/codebase_map.md` | Prior art for the `adversarial_asymmetric` wiring, blast radius, and fallback modes | Reference for silent fallback patterns (cold-start, metric name mismatch) |
| `heilbron/asymmetric-iterations` (v1) | min_delta=1 (accidental) produced best results (0.03648/0.03650, >=105% SOTA) | This experiment intentionally reproduces the v1 coupling behavior as a treatment condition |

The exact `experiment.yaml` structure from `experiments/heilbron/asymmetric-iterations-v2/experiment.yaml` is the correct template. Diff from v2: add `max_mutations_per_generation=40` and `pre_step_hook.min_delta=1` to each D run's `extra_overrides`, keep G runs unchanged.
