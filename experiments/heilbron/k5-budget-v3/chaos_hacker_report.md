# k5-budget-v3 — Chaos-Hacker Adversarial Audit

Last line of defense before 16 production runs. Scope: sandbox smoke logs, the three critical fixes (A/B/C), tracker atomicity, CellStratified provider, cache_on wiring, and VERIFICATION.md pass-claims.

Reviewer: chaos-hacker (adversarial red-team agent)
Date: 2026-04-18
Evidence base: `smoke_logs/pop_{a,b}_278244{5,6}.log` (seed-only, 221s, InsightsStage-stalled by Squid proxy).

---

## Verdict (top-line)

**DO NOT launch.** One CRITICAL (C1) is a *live, demonstrable* key-scheme mismatch between what `CellStratifiedRedisOpponentArchiveProvider.get_top_k` reads and what `RedisArchiveStorage` writes. The CellStratified provider is **non-functional in production** — `smembers` on a non-existent SET returns empty, the code early-returns `[]` at line 394, and the sparse-fallback branch is unreachable. This is already observable in the smoke logs: `[FetchOpponentIds] get_top_k(3) -> 0 ids` on *both* populations for the seed, despite 3 fallback opponents being loaded.

C1 propagates into C2 (data-flow split: `opponent_ids=[]` on DGTrackerStage while `per_opp_delta=3` from validator fallback → batch skip → zero tracker writes → zero SharedBenchmarkLineage signal → v3 treatment signal dead on arrival).

VERIFICATION.md is **not accepted as-is**. Several PROVEN (config) and PROVEN checkboxes are over-claimed — the seed-smoke evidence is silently masking the two critical bugs above. See §"VERIFICATION.md overclaims."

---

## CRITICAL — blocks launch

### C1 — `CellStratifiedRedisOpponentArchiveProvider.get_top_k` reads Redis keys that no writer populates in production

**Symbol / file:** `gigaevo/adversarial/opponent_provider.py:388-394, 407`
**Writer of record:** `gigaevo/evolution/storage/archive_storage.py:91-92` (RedisArchiveStorage)

**What breaks:** The cell-stratified provider queries `{prefix}:archive:cells` (SET) and `{prefix}:archive:cell:{x}:{y}` (ZSET). The only archive writer in production (`RedisArchiveStorage`) writes to `{prefix}:archive` (HASH: field=cell, value=program_id) and `{prefix}:archive:reverse` (HASH). Grep across the whole `gigaevo/` tree confirms **`:archive:cells` and `:archive:cell:` keys are written only in unit-test fixtures** (`tests/adversarial_pipeline/test_cell_stratified_opponent_provider.py:46,54`). In a live run, `r.smembers("{prefix}:archive:cells")` returns an empty set.

**How to trigger:** Run any production evaluation. The provider's `get_top_k(k)` hits line 392 (`cell_strs = await r.smembers(cells_key)`), line 393 sees `not cell_strs`, returns `[]` at line 394, **never reaching the sparse-fallback branch at line 468-479**. The sparse fallback to `super().get_top_k()` (which DOES read the correct `island_fitness_island:archive` key at `RedisOpponentArchiveProvider._refresh_cache` line 246) is unreachable code as currently wired.

**Observable in smoke logs (both pops, both populations, seed, empty archive):**
```
pop_b L88: [FetchOpponentIds] get_top_k(3) -> 0 ids: []
pop_a L88: [FetchOpponentIds] get_top_k(3) -> 0 ids: []
```
This is the *expected* value when the archive is genuinely empty. But this value will **remain 0 forever** because as offspring populate `{prefix}:archive`, the CellStratified provider is still reading `{prefix}:archive:cells` — which nobody writes.

**Reproducing trigger:**
```python
# After some offspring have been admitted to the archive:
r = aioredis.Redis(host=..., port=..., db=D_DB, decode_responses=True)
await r.hlen("island_fitness_island:archive")     # > 0 (populated)
await r.smembers("gigaevo:archive:cells")          # set() — EMPTY (never written)
await r.exists("gigaevo:archive:cell:1:2")         # 0 — EMPTY
```

**Fix hint:** One of:
1. Add a writer for `{prefix}:archive:cells` and `{prefix}:archive:cell:x:y` keyed off `RedisArchiveStorage._field(cell)` — most invasive; requires dual-write discipline.
2. Rewrite `CellStratifiedRedisOpponentArchiveProvider.get_top_k` to read from the actual `island_{island_id}:archive` hash (cell-field→program_id), `HGETALL` it, group program IDs by cell-field, and pick the fitness-best elite per cell. This is a pure reader change.
3. Simplest interim fix: make `get_top_k` ALWAYS call `await self._refresh_cache()` and then stratify by reading `{self._prefix}:archive:reverse` to recover cell assignments — but the `reverse` hash currently stores cell-field strings (`"x,y"`), not `cells:` tokens, so still need a format bridge.

Option (2) is the cleanest. Whichever you pick, **the unit tests currently exercising the dead-code path (`test_cell_stratified_opponent_provider.py`) will continue passing on fake keys while production fails silently** — an obvious lesson about integration-fidelity of that test file.

**Severity: CRITICAL.** This defeats the §3.2 GAME-ISAL cell-stratified contract entirely and makes all cross-population evaluations use either (a) no opponents, or (b) fallback_codes — see C2.

---

### C2 — Data-flow split: empty opponent_ids + non-empty per_opp_delta → DGTrackerStage silently skips every write

**Symbol / file:** `gigaevo/adversarial/stages.py:126-140` (FetchOpponentResultsStage fallback_codes substitution) + `gigaevo/adversarial/dg_tracker_stage.py:113-128` (DGTrackerStage length-mismatch skip)
**Consequence:** Every tracker write is skipped so long as opponent_ids is empty — i.e. as long as C1 holds.

**What breaks:** When `opponent_ids=[]`, `FetchOpponentResultsStage` (line 131-136) substitutes `self._fallback_codes` and proceeds to execute 2–3 fallback programs. `CallValidatorFunction` produces an artifact with `per_opp_delta` length 2 or 3. `DGTrackerStage` compares `len(per_opp_delta) != len(opponent_ids)` (3 != 0 on D, 2 != 0 on G), logs ERROR, and returns without writing.

**Proven in smoke logs:**
```
pop_b L123: ERROR | [DGTrackerStage improver] 6bf88419 per_opp_delta length 3 != opponent_ids length 0
          (artifact role=improver); SKIP batch — possible cache leak between
          FetchOpponentIdsStage and CallValidatorFunction.
pop_a L118: ERROR | [DGTrackerStage constructor] 51b95140 per_opp_delta length 2 != opponent_ids length 0
          (artifact role=constructor); SKIP batch — ...
```

**Cascading consequences, ordered by blast radius:**
1. **Zero `[TRACKER_WRITE]` events ever fire** as long as C1 holds → `dg_delta:{d_id}`, `dg_d_wins:{d_id}`, `dg_g_resisted:{g_id}` all stay empty.
2. **SharedBenchmarkLineageStage always emits `trend=null, n_shared=0`.** The v3 treatment signal is zero-information.
3. **BD y-axis `wins` stays at 0 for every program.** 2D MAP-Elites collapses to 1D (every program lands in the y=0 cell). CellStratified is doubly broken (C1 makes it read nothing, and even if it read `wins`, every program has `wins=0`).
4. **The entire feedback pathway (Arm C gradient_in_prompt) has no tracker data to feed the mutation prompt.** The experiment silently degrades to a no-treatment control — and because the guardian prints ERRORs but doesn't fail the run, the watchdog won't catch it.

**Fix hint:** Any of:
- Make `FetchOpponentResultsStage` also surface the synthetic opponent IDs it used (e.g., emit `fallback-0`, `fallback-1`, ...) into the artifact's `opponent_ids` field. Teach `DGTrackerStage` to accept that. Ugly.
- Better: make `FetchOpponentIdsStage` populate `ids=[]` AND make `FetchOpponentResultsStage` refuse to substitute fallbacks when `archive_reeval=True`. Let the evaluation run with zero opponents (validator should handle that — and it should produce `per_opp_delta=[]`, matching). Align contracts.
- Best (root cause): fix C1 so `opponent_ids` is never empty once either archive has admitted a seed. Then this code path is never exercised.

**Severity: CRITICAL.** Any one of (1)–(4) individually invalidates the experiment treatment.

---

## MAJOR — must fix before `status=running` (not before `status=implemented`)

### M1 — `SharedBenchmarkLineageStage._load_parent` silently returns None when storage is None

**Symbol / file:** `gigaevo/adversarial/shared_benchmark_lineage.py:108-109`

**What breaks:** In production, `_add_shared_benchmark_lineage` passes `storage=ctx.storage` (line 325-333). But if some future refactor or DI error drops that to `None` (or if a subclass inherits without passing storage), the branch at line 108 `if self._storage is None: return None` silently produces `trend=None, parent_d_id=""` — indistinguishable from the legitimate "seed program has no parent" case. The LINEAGE_TREND log doesn't distinguish "no storage" vs "no parent" vs "insufficient shared data."

**How to trigger:** Any Hydra config that forgets to wire `ctx.storage` down to the factory. No exception is raised.

**Fix hint:** Promote `storage=None` to an explicit error unless the test-hook mapping is also present. Or add a `parent_missing_reason` enum to the LINEAGE_TREND payload so the audit tool can distinguish `no_parent_seed`, `no_storage`, `parent_id_not_in_storage`, `insufficient_shared`.

---

### M2 — `SharedBenchmarkLineageStage` uses `DEFAULT_CACHE` (InputHashCache), which means cloudpickle-hashing a growing tracker state can hide real changes

**Symbol / file:** `gigaevo/adversarial/shared_benchmark_lineage.py` (no `cache_handler = NO_CACHE` → inherits `Stage.cache_handler = DEFAULT_CACHE` from `base.py:108`)

**What breaks:** The stage caches output keyed by `cloudpickle.dumps({cache_on: opponent_ids})`. The claim in the file header ("tracker pairs only grow meaningfully when HoF rotates") is reasonable — BUT: within a single HoF window, new tracker pairs CAN be written by the D's own DGTrackerStage in the same DAG tick. The next time this D's DAG runs (e.g., re-evaluation triggered by archive update), `faced_by_d(d_id)` has grown, `shared_benchmark` is larger, `trend` changes — but the cache still returns the STALE trend because `opponent_ids` is unchanged.

**How to trigger:**
1. D program D1 evaluated against opponents {G1, G2} → writes d_delta D1→{G1, G2}.
2. Parent P1 already has d_delta P1→{G1, G2, G3}. Intersection = {G1, G2}, trend computed, cached.
3. Later, D1 re-evaluated (archive_reeval) against SAME opponent IDs {G1, G2}. Tracker now has D1→{G1, G2}, P1→{G1, G2, G3}. Intersection is identical — but the writes happened in a different order, and *more pairs might exist under a different HoF scope*.

In practice this is LOW impact because same opponent_ids → same shared set → same pairs returned by `get_deltas_against`. But: **CallValidatorFunction runs before DGTrackerStage runs before SharedBenchmarkLineageStage** in the DAG (see `_add_shared_benchmark_lineage` line 336-339). So on the SECOND evaluation of D1 (re-eval), DGTrackerStage writes NEW pairs for D1 against {G1, G2}, overwriting — but `dg_delta` is a HASH keyed by g_id so overwrites are OK. Tracker state for SharedBenchmark is `faced_a & faced_b` which is unchanged. So trend is semantically the same value on re-eval. Cache hit is correct.

Still MAJOR because the subtlety is fragile: the assumption "cache_on=opponent_ids is sufficient" depends on `get_deltas_against` being a pure function of (d_a, d_b, g_ids), which it is today. Future changes that add timestamps, per-HoF windowing, or averaging over time would break it silently. At minimum, the code should add a comment explaining this invariant where the cache_handler is inherited.

**Fix hint:** Explicitly set `cache_handler = NO_CACHE` on `SharedBenchmarkLineageStage` to match `ComputeDWinsCountStage` / `ComputeGResistedCountStage` (both set `NO_CACHE` at tracker_coverage_stages.py:42, 81). The stage is sub-millisecond (pure Redis hmget), so skipping the cache has zero cost and eliminates a class of future bugs.

---

### M3 — DGImprovementTracker `record_batch` uses `pipe.execute()` on a non-transactional pipeline — partial failures are possible

**Symbol / file:** `gigaevo/adversarial/dg_tracker.py:161` (`pipe = self._redis.pipeline(transaction=False)`) + line 201 (`await pipe.execute()`)

**What breaks:** `transaction=False` means no MULTI/EXEC. Commands are batched for round-trip efficiency but executed independently. If Redis dies halfway through the batch (kill -9, OOM, network glitch between two commands), you could end up with:
- `dg_delta:{d_id}` HASH written but `dg_d_wins:{d_id}` SET missing → the inverted index is inconsistent with the per-D delta hash.
- `dg_d_wins:{d_id}` written but `expire` not called → key has no TTL, lives forever.

Design claim (VERIFICATION.md V3): "dual-write atomicity under randomized delta sequences" — this is an over-claim. The unit tests may not exercise mid-pipeline failure. The pipeline is not atomic.

**Fix hint:** Either switch to `transaction=True` (MULTI/EXEC) if you need atomicity — but that disables the GT semantics check on `zadd ... gt=True`? Actually ZADD GT works inside MULTI. A Lua EVAL script wrapping all five writes would give true atomicity. At minimum, update the VERIFICATION.md V3 pass-criteria claim: "dual-write atomicity" is NOT proven by the current tests unless they simulate mid-batch Redis failure.

---

### M4 — `DGImprovementTracker.record_batch` treats `delta == 0` as non-positive (routes to `dg_g_resisted`), but design semantics of "tie" are undocumented

**Symbol / file:** `gigaevo/adversarial/dg_tracker.py:174` (`if d_val > 0:` else branch SADDs to `g_resisted`)

**What breaks:** A delta of exactly 0.0 means D did not improve or worsen G. In the design semantics, is this a "tie" (G resisted because D did not improve) or a "no-op" (should not count toward either index)? The code treats it as "G resisted" (SADD to g_resisted). This is a **design choice not documented in the dg_tracker.py docstring or the v3 design doc** (absent from 01_design.md §3).

**Concrete risk:** In the current Heilbron task, many evaluations will produce `delta ≈ 0` when the D program makes a trivial no-op suggestion (e.g., changing variable name only). These inflate `count_d_resisted_by_g` and push G programs into high-`wins` BD cells even though they never faced genuine adversity. The BD y-axis for G is contaminated with no-op-delta inflation.

**Fix hint:** Either:
- Explicitly document in the design doc and in the docstring that `delta == 0` counts as G resisting.
- OR introduce a dead-zone: `delta >= +eps` → D wins, `delta <= -eps` → G resisted, `|delta| < eps` → neither (no tracker write). `eps = 1e-6` is reasonable given float noise.

Preference: document as-is for v3 to avoid design thrash, but put a TODO to revisit after Phase F-2 sandbox data. Update VERIFICATION.md V3.

---

### M5 — Tracker 24h TTL will silently age out the parent D's delta history during long (>24h) runs

**Symbol / file:** `gigaevo/adversarial/dg_tracker.py:64` (default `ttl_seconds=86400`), used at record_batch lines 178, 186, 191, 195, 199.

**What breaks:** `SharedBenchmarkLineageStage` depends on `faced_by_d(parent_d_id)` returning a non-trivial set. If the parent D hasn't been re-evaluated in 24h (because it's deep in the ancestry chain and no longer elite), its `dg_delta:{parent_d_id}` HASH ages out. `faced_by_d(parent)` returns `∅`, intersection with child's `faced_by_d` is `∅`, lineage trend is permanently `None` with `n_shared=0`.

**Consequence:** the v3 treatment signal fades smoothly to zero over time. Early in a 7-day run it works; late in the run every D gets `trend=None`. The experiment silently regresses to no-treatment mode.

**Fix hint:** For the 7-day experimental protocol, bump `ttl_seconds` to >= 7 * 86400 = 604800 for the `dg_delta:{d_id}` HASH. Keep 24h for the per-G sorted set if desired (since HoF rotates faster), but the D-delta hash is the substrate for lineage — it needs to outlive the ancestry.

Alternatively: every time `SharedBenchmarkLineageStage` reads a parent's delta hash, it could touch the key (re-EXPIRE it). But that couples two subsystems.

Preferred: make `ttl_seconds` a Hydra config knob and set it per-experiment. For k5-budget-v3, set it to the experimental-budget duration + 1d grace.

---

### M6 — `ComputeDWinsCountStage` and `ComputeGResistedCountStage` write to `program.metrics["wins"]` AND emit it via `FloatDictContainer` — double-write with no collision detection

**Symbol / file:** `gigaevo/adversarial/tracker_coverage_stages.py:55-68, 93-107`

**What breaks:** Two paths write `wins`:
1. Line 55 / 94: `program.metrics["wins"] = count` (direct mutation).
2. Line 68 / 107: `return FloatDictContainer(data={"wins": float(count)})` → flows into `MergeCoverageMetricsStage` → `EnsureMetricsStage` → `program.add_metrics(final_metrics)` at `metrics.py:69`.

Observationally: because path (2) uses `float(count)` and path (1) uses `count` (an `int`), then if `EnsureMetricsStage._process_metrics` doesn't coerce to float and `program.add_metrics` overwrites with the merged dict, the final `program.metrics["wins"]` is a float. OK. But the MetricsContext clamping (`EnsureMetricsStage.__init__` line 52) could apply bounds to `wins` — and those bounds would apply only to the value flowing through path (2), not path (1).

In practice, `program.add_metrics(final_metrics)` at line 69 is the LAST write, so path (2) overrides path (1). Bounds applied. Fine — but the direct mutation at path (1) serves no purpose and introduces a transient window where `program.metrics["wins"]` holds a non-clamped int.

**Risk:** If any other stage runs concurrently (e.g., EvolutionaryStatisticsCollector reads `program.metrics["wins"]` before MergeCoverageMetricsStage completes), it sees the raw int. Unlikely in the current DAG ordering (coverage → merge → ensure is serial), but fragile.

**Fix hint:** Remove the `program.metrics["wins"] = count` direct mutation. Rely on the `FloatDictContainer` → MergeCoverage → Ensure path exclusively. The METRIC_EMIT log can still fire without mutating the program.

---

### M7 — `MergeCoverageMetricsStage` is a `MergeDictStage[str, float]`, but `FloatDictContainer` is `Box[dict[str, float]]` — generic specialization mismatch risk

**Symbol / file:** `gigaevo/adversarial/asymmetric_pipeline.py:296` (`MergeDictStage[str, float](timeout=_coverage_timeout)`)
**Other input:** `MergeMetricsStage` → `MergeCoverageMetricsStage` as `first`. Need to verify the type is `dict[str, float]` not `dict[str, Any]`.

**What breaks:** `MergeDictStage[str, float]` expects both inputs to be `Box[dict[str, float]]`. If `MergeMetricsStage`'s output is typed as `Box[dict[str, Any]]` (or `DictContainer`), the type system will silently accept it at runtime (Python) but type-checkers would flag it. The merge result is `dict[K, V]` = `dict[str, float]`, and if `first` actually contains non-float values (say a string like a UUID accidentally put into metrics), the merged dict has a mixed type — downstream `EnsureMetricsStage._process_metrics` coerces to float and will raise on non-numeric values.

Looking at smoke log: `[MergeDictStage] merged 21 + 1 -> 22 keys (0 overlapping)` — 21 keys on first (from MergeMetricsStage), 1 key on second (`wins`). No overlap means no collision was tested. This is fragile because `MergeMetricsStage` upstream could one day include a `wins` key from another source (e.g., a legacy metric), and the merge-override semantics would silently resolve it in favor of the coverage stage's `wins`. Fine today — but **this is the kind of silent data-merging that is dangerous at scale**. Consider adding an assertion that `wins` is NOT in `first`.

**Fix hint:** Add a `MergeDictStage` option: `raise_on_collision=True`. Or check `overlapping_keys > 0` and log WARNING. The log line at line 40 emits `0 overlapping` — elevate that to WARNING when overlapping > 0 in strict-merge scenarios.

---

## MINOR — file follow-up

### m1 — `_parent_id_to_d_id` monkey-patch test hook could survive into production if stage instance is shared across runs

**Symbol / file:** `gigaevo/adversarial/shared_benchmark_lineage.py:117-122`

The hook `getattr(self, "_parent_id_to_d_id", None)` is None by default. Tests set it as an instance attribute. If stages are cached / pooled across evaluations (checking `default_pipelines.py` factory ... they're re-constructed per DAG build per program, so pooling risk is low), this is a non-issue in practice. But the name "_parent_id_to_d_id" could collide with a real attribute in a future refactor.

**Fix hint:** Rename to `__test_parent_id_to_d_id` (dunder mangling) or make the hook mechanism explicit via a constructor kwarg.

---

### m2 — LINEAGE_TREND `gen` field is always `null` in smoke logs

**Symbol:** `gigaevo/adversarial/structured_logging.py:emit_lineage_trend`, sourced from `SharedBenchmarkLineageStage._emit_lineage_event`.

The LINEAGE_TREND event includes `"gen": null` (see pop_b L147 evidence). The stage doesn't know the current generation — the DAG doesn't pass it in. The audit tool (pending, task #19) will need to cross-reference program creation time or some other signal to recover gen. Filed as follow-up: either plumb `gen` through `EvolutionContext` or drop the field from the canonical event spec.

---

### m3 — `CellStratifiedRedisOpponentArchiveProvider.__init__` swallows unknown Hydra kwargs via `**_ignored`

**Symbol:** `gigaevo/adversarial/opponent_provider.py:347` (`**_ignored: object`)

While pragmatic, this is a time-bomb: a future Hydra config typo (`sources_` instead of `sources`) will silently instantiate with defaults. Combined with C1, this means a typo in the Hydra config that disables cell stratification would be indistinguishable from the current broken-but-compiling state.

**Fix hint:** Log all ignored kwargs at WARNING level, or whitelist exactly the known legacy keys (`sources`, `island_id`, `cache_ttl`) and reject anything else.

---

### m4 — `SharedBenchmarkLineageStage.compute` does not guard against `tracker` attribute being wrong type

**Symbol:** `gigaevo/adversarial/shared_benchmark_lineage.py:178-185`

`getattr(self._resolver, "_tracker", None)` — if a future alternate resolver implementation is added without a `_tracker` attribute, the stage hits the error-log path and returns `trend=None` silently. The abstract base class `SharedBenchmarkResolver` has no `_tracker` requirement; it's only present on the concrete `DGTrackerSharedOpponentResolver`. This is a leaky abstraction.

**Fix hint:** Either hoist `_tracker` into the ABC, or refactor so the stage calls `resolver.get_deltas_against(...)` instead of reaching into `resolver._tracker`.

---

### m5 — VERIFICATION.md V3 over-claims "unit-test coverage of dual-write atomicity"

See M3 above. The unit tests likely don't simulate mid-batch Redis failure.

**Fix hint:** Update the pass-criteria to "dual-write happens in the same non-transactional pipeline; atomicity under failure is NOT tested." Add a Phase F-2 task to verify: kill Redis mid-evaluation, then inspect for `dg_d_wins`/`dg_g_resisted` without matching `dg_delta` entries.

---

## ACCEPTED — looked, found no vulnerability

### A1 — Fix A (`_load_parent` uses `program.lineage.parents[0]` instead of `program.parent_id`)

`program.lineage.parents` is accessed via `getattr` chain with defaults (lines 104-106). For the seed path, `parents=[]` → returns `None`. No AttributeError. **Smoke log evidence**: pop_b L146 shows clean "no parent; trend=None" → L147 LINEAGE_TREND emission. This fix holds. The M1 finding above is about the OTHER silent-None path (storage=None), not this one.

### A2 — Fix B (Coverage stages use `InputsModel = VoidInput`)

Smoke log pop_b L139-L155 confirms ComputeDWinsCountStage Executing → METRIC_EMIT → FINALIZED COMPLETED without a DAG-construction error. `VoidInput` is a valid typed input model. No TypeError. Fix B holds.

### A3 — Fix C (MergeCoverageMetricsStage merge-order: `first=MergeMetrics, second=coverage_stage`)

`MergeDictStage` at `json_processing.py:38` does `{**first, **second}` — `second` overwrites. In V3's wiring, coverage's `{"wins": 0.0}` is the `second` edge (`asymmetric_pipeline.py:303-305`). If `MergeMetricsStage` ever produces a `wins` key, coverage wins. Correct semantics.

**Smoke log evidence**:
- pop_b L160: `merged 21 + 1 -> 22 keys (0 overlapping)` — coverage added `wins`, no overlap.
- pop_a L149: `merged 19 + 1 -> 20 keys (0 overlapping)` — same.
- pop_b L167: `Stored 9 validated metrics` on program.
- pop_a L156: `Stored 7 validated metrics` on program.

EnsureMetricsStage succeeds — no `Missing required metric keys: ['wins']` anywhere in either log (confirmed via Grep). Fix C holds at stage level.

### A4 — CellStratified `seen_cells` dedup

Even if `list_cells_sorted_by_fitness` returned the same cell twice (shouldn't happen — set membership), the `seen_cells` check at line 431 would drop duplicates. No duplicate-program-ID risk from THIS code path. (The real bug — C1 — is that this code path never fires.)

### A5 — `get_deltas_against` ordering assumption

`pairs` in `SharedBenchmarkLineageStage.compute` line 187 is a list of `(delta_a, delta_b)` tuples where `a=child=d_id`, `b=parent=parent_d_id` — confirmed at `dg_tracker.py:237-256`. Arithmetic at line 197-199: `child_mean = sum(c for c, _ in pairs) / len(pairs); parent_mean = sum(p for _, p in pairs) / len(pairs)`. Order correct.

### A6 — Cache-key ordering of opponent_ids list

`get_top_k` sorts by `(-fitness, program_id)` deterministically (opponent_provider.py:235). So the list fed into `cache_on` has stable ordering for identical archives. cloudpickle of a list preserves ordering, hash is stable. No order-sensitivity bug here. (Separate from C1, which says the list is always empty anyway.)

### A7 — Seed program BD y-axis gracefully handled

`[EnsureMetricsStage] Stored 9 validated metrics` (pop_b L167) and `Stored 7` (pop_a L156) confirm seed programs pass metrics validation with `wins=0`. This is correct: seed has faced nothing, zero wins is the right value. The concern was whether `wins=0` would cause a divide-by-zero or sentinel-clash downstream; did not observe any.

---

## VERIFICATION.md overclaims — pass-criteria I would NOT have checked off

Read against the seed-only evidence:

| Item | VERIFICATION.md claim | Chaos-hacker ruling | Reason |
|---|---|---|---|
| V1 | "PROVEN — 1 line, seed program" | Accept as PROVEN at STAGE WIRING level only; DOWNGRADE the implicit claim that lineage signal will work at runtime | The seed emission confirms `_load_parent` → `None` path. It does NOT confirm the `parent` → `shared benchmark ≥ 2` → `get_deltas_against` → `trend=finite` path. C2 shows that path is **unreachable** as long as C1 holds. |
| V2 (PROVEN config) | "26 edges for 25 stages matches cache_on hookup" | Accept at wiring level; DEFERRED runtime proof is correctly labeled | No objection. |
| V3 | "Unit-test coverage of dual-write atomicity — PROVEN" | DOWNGRADE to "unit tests cover happy path; atomicity under mid-batch Redis failure NOT tested" | See M3. Pipeline is `transaction=False`. |
| V4 | All PROVEN checkboxes | Accept — the fix-C merge-chain works for seed | **BUT**: V4's last unchecked box ("After gen 2+ with opponent evaluations, wins takes positive value for D winners") is DEFERRED — and C2 says this is **unreachable** with current code. Flag as BLOCKED on C1/C2 resolution, not merely DEFERRED. |
| V5 config | Accept config; DEFERRED rightly labeled | No objection at config level. Runtime will fail due to C1. |
| V6 config | "Both sides configured with n_opp=3 source_prompt_k=3" | Accept config; but "Seed phase falls back to fallback opponents (sparse archive → no cell stratification yet)" is a SILENT MISREADING | The seed ran fallback not because of sparse-cell stratification fallback, but because `{prefix}:archive:cells` SET is empty and the code returned `[]` at line 394 — sparse-fallback was never invoked. The fallback was at FetchOpponentResultsStage, not at CellStratified.get_top_k. The V6 evidence conflates two different fallback paths. |
| V7 | DEFERRED — correct | No objection. |
| V8 | "PROVEN — 25 vs 23 stages, LINEAGE_TREND 1 on D / 0 on G" | Accept as PROVEN at STAGE-PRESENCE level, but with asterisk | The asymmetry in stage COUNT is real. But LINEAGE_TREND-emission count ≥1 proves only that the stage FIRES — it does not prove the stage produces a meaningful signal. With trend=null from seed + C1/C2 blocking non-null trend forever, the emission count claim is structurally true but semantically vacuous. |
| V9 | DEFERRED — correct | Audit tool not yet built. |
| V10 | IN PROGRESS → this report | Delivering. |

**Flag**: The sign-off section at line 285-287 says "Eligible for Phase F-2 sandbox run." **This is premature.** Phase F-2 running on the current code would produce 8 generations of:
- zero `TRACKER_WRITE` events (C2)
- `wins=0` for every program (C2 cascade)
- `trend=null` for every program (C2 cascade)
- all 2D MAP-Elites programs landing in the y=0 row (C2 cascade)

The sandbox would appear to "pass" because no exception is raised and the stages FINALIZE COMPLETED. The degradation is silent. Phase F-2 as currently conceived is NOT a sufficient hard gate — it will LGTM a broken experiment.

---

## Summary Scorecard

```
Bugs Found: 15
CRITICAL: 2  |  MAJOR: 7  |  MINOR: 5  |  ACCEPTED: 7
Most Dangerous: C1 — CellStratified provider reads nonexistent Redis keys;
                cascades into C2 (silent zero tracker writes for the entire run).
                Experiment degrades silently to no-treatment control.
Assumptions the code makes that could be wrong:
  - {prefix}:archive:cells SET is populated by somebody (nobody).
  - {prefix}:archive:cell:x:y ZSETs are populated by somebody (nobody).
  - FetchOpponentIds returning [] means "genuinely no archive" (it also means
    "reader bug"; the two are indistinguishable downstream).
  - DGTrackerStage skip-on-length-mismatch is rare (under C1 it's universal).
  - 24h TTL on dg_delta outlives the parent D's ancestry relevance
    (it doesn't — for 7-day runs).
  - Pipeline transaction=False is "atomic enough" for dual-write claims
    (it isn't — RedisException or kill-9 mid-batch leaves inconsistent state).
  - Seed-only smoke proves runtime behavior (it doesn't — seed has parent_d_id="",
    n_shared=0, wins=0: every interesting path is skipped).
```

---

## Recommendations, ordered

1. **BLOCK** `status=implemented`. C1 alone warrants this. C2 is a direct consequence of C1 that compounds the severity.
2. **Rewrite** `CellStratifiedRedisOpponentArchiveProvider.get_top_k` to read from the actual archive hash (`island_{island_id}:archive`) grouped by cell. Reuse the parent class's `_refresh_cache` and stratify in-memory.
3. **Add integration test** that actually writes to Redis using the same keys the production `RedisArchiveStorage` uses, then calls `CellStratified.get_top_k()` and asserts non-empty result. The current `test_cell_stratified_opponent_provider.py` writes to `:archive:cells` — the wrong key — and is therefore complicit in the bug. That test should be deleted or rewritten against real key-format fidelity.
4. **Add smoke-log assertion** that after N >= 2 DAG evaluations, at least one `[TRACKER_WRITE]` event has been emitted. This would have caught C2 in the current smoke.
5. **Address MAJOR findings M1, M2, M3, M5** before `status=running`. M4, M6, M7 can be deferred to a follow-up PR.
6. **Re-score VERIFICATION.md**: V1 → "PROVEN (stage wiring)"; V3 → downgrade atomicity claim; V6 → remove the misread about sparse-fallback; V8 → add "semantically vacuous without non-trivial trend" caveat.
7. After fixes, **re-run the sandbox smoke** with Squid proxy disabled (or `InsightsStage` stubbed to no-op) so the 8-gen gauntlet actually evaluates offspring and emits TRACKER_WRITE / LINEAGE_TREND with non-null trend / non-zero wins. Only then is Phase F-2 evidence meaningful.

---

## Final verdict

The current PROVEN / DEFERRED labels in VERIFICATION.md **cannot be accepted as-is** for Phase F-2 eligibility. C1 makes the v3 treatment variable non-functional in production, and the seed-only smoke provably cannot detect it. Phase F-2 would rubber-stamp a broken run.

**Required before `status=implemented`:** resolve C1 and C2. The three fix-A/B/C claims are themselves technically correct (see A1/A2/A3), but they fix stage-level bugs on top of an infrastructure that never delivers opponent IDs or tracker writes. The house is framed correctly; the plumbing is disconnected from the municipal water supply.
