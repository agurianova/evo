# Technical Codebase Map: Remove LineageStage from D-side pipeline

## Mechanism Domain

Pipeline DAG surgery — remove the `LineageStage` node (and its two fan-out
stages `LineagesToDescendants` / `LineagesFromAncestors`) from the D (improver)
pipeline only. G (constructor) pipeline must remain unchanged.

---

## Full LineageStage Node Graph

### Where the node is ADDED (default pipeline, always)

`gigaevo/entrypoint/default_pipelines.py` — `_contribute_default_nodes()` — lines 276–286

```
add_stage("LineageStage", lambda: LineageStage(...))
add_stage("LineagesToDescendants", lambda: LineagesToDescendants(storage=..., source_stage_name="LineageStage", ...))
add_stage("LineagesFromAncestors", lambda: LineagesFromAncestors(storage=..., source_stage_name="LineageStage", ...))
```

### Where edges are DECLARED (default pipeline)

`default_pipelines.py` — `_contribute_default_edges()` — lines 370–381

| Edge | Input name | Notes |
|---|---|---|
| `DescendantProgramIds → LineagesToDescendants` | `descendant_ids` | |
| `AncestorProgramIds → LineagesFromAncestors` | `ancestor_ids` | |
| `LineagesToDescendants → MutationContextStage` | `lineage_descendants` | |
| `LineagesFromAncestors → MutationContextStage` | `lineage_ancestors` | |

### Where exec-order deps are DECLARED (default pipeline)

`default_pipelines.py` — `_contribute_default_deps()` — lines 408–415

```
"LineageStage":          [always_after("EnsureMetricsStage")]
"LineagesToDescendants": [always_after("LineageStage")]
"LineagesFromAncestors": [always_after("LineageStage")]
```

### Where the cache_on edge is ADDED (asymmetric builder)

`gigaevo/adversarial/asymmetric_pipeline.py` — `_wire_cache_on_edges()` — lines 313–314

```python
if "LineageStage" in self._nodes:
    self.add_data_flow_edge("FetchOpponentIdsStage", "LineageStage", "cache_on")
```

Guards itself: only fires if node exists.

### Where the node is SWAPPED to filtered variant (D runs only)

`gigaevo/adversarial/asymmetric_pipeline.py` — `__init__()` — lines 206–215

Condition: `dg_tracker is not None AND population_role == "improver"`

Calls `_replace_lineage_with_filtered()` — lines 476–523

`replace_stage("LineageStage", ...)` — node name stays `"LineageStage"`, all existing
edges survive. Adds one extra exec dep: `always_after("DGTrackerStage")` on `"LineageStage"`.

---

## Entry Points Table

| Component | File | Class/Function | Lines | Role |
|---|---|---|---|---|
| Default node factory | `gigaevo/entrypoint/default_pipelines.py` | `_contribute_default_nodes` | 276–303 | Adds LineageStage, LineagesToDescendants, LineagesFromAncestors |
| Default edge wiring | `gigaevo/entrypoint/default_pipelines.py` | `_contribute_default_edges` | 370–381 | Declares DescendantProgramIds/AncestorProgramIds fan-in; fan-out to MutationContextStage |
| Default exec deps | `gigaevo/entrypoint/default_pipelines.py` | `_contribute_default_deps` | 408–415 | always_after chains on Lineage family |
| cache_on edge | `gigaevo/adversarial/asymmetric_pipeline.py` | `_wire_cache_on_edges` | 304–314 | FetchOpponentIdsStage → LineageStage cache_on; guarded by node-exists check |
| D-side swap to filtered | `gigaevo/adversarial/asymmetric_pipeline.py` | `_replace_lineage_with_filtered` | 476–523 | replace_stage("LineageStage", SharedBenchmarkFilteredLineageStage) |
| D-side swap trigger | `gigaevo/adversarial/asymmetric_pipeline.py` | `__init__` | 206–215 | Gate: dg_tracker is not None AND population_role == "improver" |
| Filtered subclass | `gigaevo/adversarial/shared_benchmark_lineage.py` | `SharedBenchmarkFilteredLineageStage` | 61–219 | Filters parents by shared eval benchmark; refresh_pass cache suffix |
| Base class | `gigaevo/programs/stages/insights_lineage.py` | `LineageStage` | 37–83 | LangGraph-based lineage agent; InputsModel=CacheOnlyInput |
| MutationContextStage consumer | `gigaevo/programs/stages/mutation_context.py` | `MutationContextStage.compute` | 74–130 | Reads lineage_ancestors / lineage_descendants as OPTIONAL fields |

---

## MutationContextStage Tolerance Analysis

**Critical question: does MutationContextStage hard-require lineage inputs?**

Answer: **No.** All lineage fields are Optional in `MutationContextInputs`:

```python
class MutationContextInputs(StageIO):
    lineage_ancestors: TransitionAnalysisList | None   # Optional
    lineage_descendants: TransitionAnalysisList | None # Optional
    ...
```

In `compute()` (lines 89–105):

```python
ancestor_lineages: list[TransitionAnalysis] = []
if params.lineage_ancestors is not None:
    ancestor_lineages = params.lineage_ancestors.items

descendant_lineages: list[TransitionAnalysis] = []
if params.lineage_descendants is not None:
    descendant_lineages = params.lineage_descendants.items

if ancestor_lineages or descendant_lineages:
    # only builds FamilyTreeMutationContext if at least one list is non-empty
```

If both inputs are `None` (wires absent), the stage silently skips
`FamilyTreeMutationContext`. No exception, no sentinel required.

---

## Hydra Wiring

### Current state

`config/pipeline/adversarial_asymmetric.yaml` line 126:
```yaml
lineage_filter:
  _target_: gigaevo.adversarial.asymmetric_pipeline.LineageFilterConfig
  min_shared: 1
  inject_shared_evidence: true
```
(no `aggregator:` key — aggregator must be provided by extending config)

`config/pipeline/heilbron_repro_v1.yaml` lines 94–101:
```yaml
pipeline_builder:
  aggregator: ${ref:aggregator}
  lineage_filter:
    _target_: gigaevo.adversarial.asymmetric_pipeline.LineageFilterConfig
    min_shared: 1
    inject_shared_evidence: true
    aggregator: ${ref:aggregator}
```

### How to disable LineageStage on D runs only

**Option A — Hydra override only (no Python changes):**

Set `pipeline_builder.lineage_filter=null` in the D-run launch command.

BUT this will NOT work as intended. Reading `__init__` carefully:

```python
if dg_tracker is not None:
    ...
    if population_role == "improver":
        resolved_filter = _resolve_lineage_filter(lineage_filter, ...)
        self._replace_lineage_with_filtered(...)   # swaps the node factory
```

Setting `lineage_filter=null` causes `_resolve_lineage_filter` to raise
`ValueError: "lineage_filter.aggregator required — no silent fallback"` —
there is an explicit guard. The code path has **no "skip lineage" branch.**

The `null` path is intentionally broken to prevent silent degradation.
This is NOT the disable path.

**Option B — New builder flag `disable_lineage_on_improver: bool = False`:**

Add a new kwarg to `AdversarialAsymmetricPipelineBuilder.__init__`. In `__init__`:

```python
if not disable_lineage_on_improver:
    # existing gate: if dg_tracker is not None and population_role == "improver": _replace_lineage...
    ...
else:
    # population_role == "improver": remove LineageStage family from DAG
    if population_role == "improver":
        self.remove_stage("LineageStage")
        self.remove_stage("LineagesToDescendants")
        self.remove_stage("LineagesFromAncestors")
```

`PipelineBuilder.remove_stage()` (lines 87–97) is already implemented:
strips the node from `_nodes`, removes all data-flow edges where that
node is source or destination, removes its exec deps, and removes any
cross-stage dep that references it by `stage_name`. A single call to
`remove_stage("LineageStage")` followed by `remove_stage("LineagesToDescendants")`
and `remove_stage("LineagesFromAncestors")` cleanly removes the entire
lineage sub-graph without touching MutationContextStage wiring —
MutationContextStage simply receives `None` for `lineage_ancestors` and
`lineage_descendants`.

Hydra override on D launch:
```
pipeline_builder.disable_lineage_on_improver=true
```

**Option C — New pipeline YAML (no Python changes in builder):**

A new `config/pipeline/heilbron_repro_v1_no_d_lineage.yaml` that extends
`heilbron_repro_v1` and sets `pipeline_builder.lineage_filter: null`. This
requires Python to first add a guard that treats `lineage_filter=null` as
"disable" rather than "raise ValueError" — which means the Option A blocker
also applies. Config-only is not feasible without a Python change somewhere.

**Verdict: Option B is the only clean path.** ~15 LOC change confined to
`__init__` of `AdversarialAsymmetricPipelineBuilder` plus a new kwarg.

---

## Silent Fallback Modes

| Risk | Mechanism | Detection |
|---|---|---|
| D run silently skips removal | `disable_lineage_on_improver` kwarg not forwarded in YAML | Config dump must show `disable_lineage_on_improver: true` in the D config |
| G run accidentally removes lineage | `disable_lineage_on_improver` set globally instead of D-only | Guard with `if population_role == "improver"` inside the builder; verify G config dump shows `false` |
| `_wire_cache_on_edges` is a no-op | Already guarded: `if "LineageStage" in self._nodes` — safe after removal | No action needed |
| `_replace_lineage_with_filtered` still runs | If `disable_lineage_on_improver` gate is placed BEFORE the `_replace_lineage` block but after `dg_tracker is not None` check | Implementation MUST short-circuit the entire `if population_role == "improver"` block when flag is True |
| `remove_stage` on non-existent node | `remove_stage` uses `pop(name, None)` — idempotent, silent | Safe |
| `LineagesFromAncestors.compute` reads `source_stage_name="LineageStage"` from removed program stage_results | These nodes are also removed; they never run, so they never read stale stage_results | Safe |

---

## Blast Radius

GitNexus impact on `_replace_lineage_with_filtered`:
- Risk: **LOW**
- d=1 direct callers: only `AdversarialAsymmetricPipelineBuilder.__init__`
- d=2: nothing

Adding `disable_lineage_on_improver` kwarg to `__init__`:

| Depth | Affected symbol | Impact |
|---|---|---|
| d=1 (WILL BREAK) | `config/pipeline/adversarial_asymmetric.yaml` `pipeline_builder:` block | Must add `disable_lineage_on_improver: false` default (or omit — Hydra will use Python default) |
| d=1 (WILL BREAK) | `config/pipeline/heilbron_repro_v1.yaml` `pipeline_builder:` block | Same — but can rely on Python default `False` |
| d=1 (test callers) | `tests/adversarial_pipeline/test_asymmetric_pipeline.py` | New kwarg is keyword-only with default=False; existing tests pass without change |
| d=2 | `SharedBenchmarkFilteredLineageStage` | Never reached if flag is True; no change needed |
| d=2 | `MutationContextStage` | Receives None for lineage fields — already handled |

Blast radius: **2 config files need review; 0 files require forced edits** (Python default False preserves existing behavior).

---

## Feasibility Assessment

**Rating: GREEN**

Rationale:
- `PipelineBuilder.remove_stage()` already exists and is correctly implemented (strips node + all data-flow edges + exec deps in one call).
- `MutationContextStage` explicitly declares lineage inputs as `Optional` and is null-safe.
- The change is 100% confined to `AdversarialAsymmetricPipelineBuilder.__init__`: add one kwarg, one `if` block of 3 `remove_stage` calls.
- G runs are structurally unchanged — the flag defaults to `False` and the removal code is behind a `population_role == "improver"` guard.
- No shared framework code changes (only the asymmetric builder subclass).
- `_wire_cache_on_edges` is already guarded by `if "LineageStage" in self._nodes` — safe.
- `_replace_lineage_with_filtered` must be skipped when flag is True; placing the new `if` block before the existing `if population_role == "improver": _replace_lineage...` block achieves this.

Total change: ~10–15 lines in one file.

---

## Recommended Treatment Specification

### File to modify

`gigaevo/adversarial/asymmetric_pipeline.py`

### Change 1: new constructor kwarg

```python
def __init__(
    self,
    ...
    lineage_filter: LineageFilterConfig | DictConfig | None = None,
    disable_lineage_on_improver: bool = False,   # NEW
    ...
):
```

### Change 2: gate the entire D-side lineage block

Replace the current block at lines 206–215:

```python
# BEFORE:
if dg_tracker is not None:
    ...
    if population_role == "improver":
        resolved_filter = _resolve_lineage_filter(...)
        self._replace_lineage_with_filtered(...)
```

with:

```python
# AFTER:
if dg_tracker is not None:
    ...
    if population_role == "improver":
        if disable_lineage_on_improver:
            self.remove_stage("LineageStage")
            self.remove_stage("LineagesToDescendants")
            self.remove_stage("LineagesFromAncestors")
        else:
            resolved_filter = _resolve_lineage_filter(
                lineage_filter, ctx.problem_ctx.metrics_context
            )
            self._replace_lineage_with_filtered(
                ctx, dg_tracker, resolved_filter, stage_timeout,
            )
```

### Change 3: Hydra YAML override on D runs

In `config/pipeline/heilbron_repro_v1.yaml`, add under `pipeline_builder:`:

```yaml
pipeline_builder:
  aggregator: ${ref:aggregator}
  disable_lineage_on_improver: false   # default; D-run launch overrides to true
  lineage_filter:
    ...
```

In the D-run launch command (or per D-run YAML override):
```
pipeline_builder.disable_lineage_on_improver=true
```

G runs: omit the override entirely (Python default `False` applies).

### Treatment verification log line

Because `LineageStage` no longer runs on D, D logs will be **absent** of:

- `[LineageStage] program=... n_parents=...`
- `[LineageStage:SharedBenchmark] program=...`

G logs must still show these lines. The absence/presence pattern is the primary verifier.

---

## D-Smoothing-Minimal Carry-Forward

The predecessor `d-smoothing-minimal` changed only `problems/heilbron_repro_v1/pop_b/evaluate.py`.
That change must be present in the branch for this experiment. If not merged to main,
the implementing agent must cherry-pick or include both changes:

1. `problems/heilbron_repro_v1/pop_b/evaluate.py` — tanh smoothing (from d-smoothing-minimal)
2. `gigaevo/adversarial/asymmetric_pipeline.py` — `disable_lineage_on_improver` kwarg (this experiment)

These touch non-overlapping files and compose cleanly.

---

## Existing Code Patterns to Reuse

| Precedent | File | Pattern | Reusable? |
|---|---|---|---|
| `remove_stage` API | `gigaevo/entrypoint/default_pipelines.py` lines 87–97 | Already implemented; cascades edge/dep removal | Use directly — no new code needed |
| `_add_source_injection` | `asymmetric_pipeline.py` line 322 | Calls `remove_data_flow_edge` then re-wires; shows pattern for DAG surgery in the builder | Reference only |
| `disable_lineage_on_improver=False` default pattern | — | Any existing kwarg with default in `__init__`; new kwarg follows same pattern | Standard Python |
