# Sandbox Validation Checks — Heilbron Adversarial Redesign

This file is the gating checklist for the mock sandbox run. Each check
- targets a specific behavior the redesign guarantees
- carries a code snippet showing the assertion form
- carries an ELI5 of why the check works (mechanism, not vibes)

Categories (in order of importance for the NeurIPS submission):
A. Fitness rescaling (no point masses)
B. Hall-of-Fame determinism + cache invalidation
C. DGTrackerStage — real program IDs, role-aware recording
D. DGImprovementTracker — dual-write + permanent dedup
E. CompositionInjectionHook — code-level Lamarckian transfer
F. GradientInPromptStage — per-G-D selection
G. Cold-start + engine integration
H. Logging coverage (production debuggability)

---

## A. Fitness rescaling — no point masses

The original D fitness formula `min(max(delta, 0)/Q_MAX, 1.0)` collapsed 60–90% of D
programs to fitness=0. The G resistance formula `float(delta <= 0)` was binary.
Both were replaced with smoothed `tanh` rescaled to (0, 1). These checks confirm
the smoothing actually flows through to the metrics MAP-Elites consumes.

### A1 — D fitness has no point mass at 0.5

```python
d_fitness_vals = [json.loads(v)["v"] for v in r.lrange(f"{prefix_b}:metrics:history:program_metrics:fitness", 0, -1)]
mass_at_neutral = sum(1 for f in d_fitness_vals if abs(f - 0.5) < 1e-6) / len(d_fitness_vals)
assert mass_at_neutral < 0.30, f"D fitness collapsing to neutral: {mass_at_neutral:.1%}"
```

**Why this works (ELI5):** `tanh(0) = 0`, which the rescale `(x+1)/2` maps to
exactly 0.5. So 0.5 is the "no signal" mode — happens when D made zero
progress on its target. If >30% of programs land there, the smoothing isn't
generating gradient and we're back to the original failure mode.

### A2 — G resistance has no point mass at 1.0 (after archive ≥3)

```python
g_resistance = [json.loads(v)["v"] for v in r.lrange(f"{prefix_a}:metrics:history:program_metrics:resistance", 0, -1)]
mass_at_max = sum(1 for r_ in g_resistance if abs(r_ - 1.0) < 1e-6) / len(g_resistance)
assert mass_at_max < 0.40, f"G resistance pinned at upper bound: {mass_at_max:.1%}"
```

**Why this works:** `resistance=1.0` is the "all opponents failed" branch
(cold-start or D crashed every time). Once the archive has ≥3 D programs,
most G evaluations should produce mixed deltas and resistance should land
in (0, 1).

### A3 — D fitness strictly inside (0, 1)

```python
assert min(d_fitness_vals) > 0.0
assert max(d_fitness_vals) < 1.0
```

**Why this works:** `tanh` is bounded in (-1, 1) open. The rescale maps to
(0, 1) open. Hitting exactly 0 or 1 means a downstream clamp is overriding
the smoothing — a regression to look for.

### A4 — No "fitness out of range" or ValueError in logs

```python
log = Path("/tmp/sandbox_run.log").read_text()
assert "fitness out of range" not in log
assert "ValueError" not in log
```

**Why this works:** MAP-Elites validates that fitness ∈ [0, 1]. If it
rejects a value, it logs that exact phrase. Catches accidental sign flips
or formula bugs.

---

## B. Hall-of-Fame determinism + cache invalidation

The asymmetric pipeline relies on a deterministic top-K so that the cache
key (the opponent ID list) only changes when the archive ranking changes.
Stochastic `get_opponents` would produce a new key every call and destroy
the entire `cache_on` mechanism.

### B1 — get_top_k is used; get_opponents is NOT

```python
log = Path("/tmp/sandbox_run.log").read_text()
assert log.count("[FetchOpponentIds] get_top_k(") > 0
assert "get_opponents(n=" not in log
```

**Why this works:** Step 4 of the plan upgraded the FetchOpponentIdsStage
log to INFO with the verbatim call signature. If anything calls the old
sampling API, it would show up in this grep.

### B2 — get_top_k is deterministic (same input → same output)

```python
ids_call_1 = (await provider.get_top_k(3))
ids_call_2 = (await provider.get_top_k(3))
assert [o.program_id for o in ids_call_1] == [o.program_id for o in ids_call_2]
```

**Why this works:** Top-K-by-fitness is a pure function of the archive
state. If it returns a different ordering for the same archive, there's
a hidden tiebreak using a non-deterministic key (e.g. dict ordering on
old Python). This catches that.

### B3 — HoF rotation invalidates cached opponent IDs

```python
ids_before = await provider.get_top_k(3)
# Inject a higher-fitness opponent.
await opponent_storage.add(Program(code="...", metadata={"fitness": 999.0}))
ids_after = await provider.get_top_k(3)
assert ids_before != ids_after
```

**Why this works:** A higher-fitness program must displace the bottom of
the top-K. If it doesn't, the archive isn't actually sorted by fitness
or the storage isn't refreshing.

### B4 — InsightsStage cache hit rate rises with stable archive

```python
assert mock_insights_agent.arun.call_count_per_gen[-1] <= mock_insights_agent.arun.call_count_per_gen[0]
```

**Why this works:** With `cache_on=opponent_ids`, identical opponent IDs
across generations means identical cache keys, so InsightsStage should
re-use cached insights. Per-generation call count should drop.

### B5 — InsightsStage invalidates after HoF rotation

```python
calls_before_rotate = mock_insights_agent.arun.call_count
await opponent_storage.add(Program(code="...", metadata={"fitness": 999.0}))
# trigger one more eval
calls_after_rotate = mock_insights_agent.arun.call_count
assert calls_after_rotate > calls_before_rotate
```

**Why this works:** Inverse of B4 — if the cache_on edge isn't actually
folding opponent IDs into the hash, rotations would not invalidate.

### B6 — `Box[T]` hash folds the contained value

```python
from gigaevo.programs.stages.common import Box
b1 = Box[list[str]](data=["a"]).content_hash
b2 = Box[list[str]](data=["b"]).content_hash
assert b1 != b2
```

**Why this works:** `cache_on` is plumbed via Box-wrapped opponent IDs.
If the hash function ignores the data field (e.g. hashing only by type),
B4/B5 silently break and we'd never know.

### B7 — Default (non-adversarial) pipeline does NOT get the cache_on edge

```python
builder = DefaultPipelineBuilder(...)
graph = builder.build()
assert ("FetchOpponentIdsStage", "InsightsStage") not in graph.edges
```

**Why this works:** The cache_on edge wiring is guarded by
`if "InsightsStage" in self._nodes` — but on a non-adversarial pipeline
there is no FetchOpponentIdsStage either. This check confirms the
guarding still holds and unrelated pipelines aren't accidentally rewired.

---

## C. DGTrackerStage — real program IDs

This was the silent killer: the previous DGTrackerStage hardcoded
`program_id = "<program>"`. Every G evaluation collapsed to the same
key, which meant `tracker.get_best_d_for_g(real_g_id)` always returned
None — and CompositionInjectionHook + GradientInPromptStage had no data
to consume. This block is the new gate.

### C1 — Constructor role records (opp, program.id, delta)

```python
stage = DGTrackerStage(dg_tracker=tracker, role="constructor", timeout=5.0)
stage.attach_inputs({
    "opponent_ids": Box(data=["d-1"]),
    "validation_result": Box(data=({}, {"per_opp_delta": [0.1]})),
})
prog = Program(code="...", metadata={})
await stage.compute(prog)
pairs = tracker.record_batch.await_args.args[0]
assert pairs == [("d-1", prog.id, 0.1)]
assert prog.id != "<program>"  # the bug we fixed
```

**Why this works:** Stage.execute(program) passes the real Program object
into compute(). Our compute extracts `program.id`. If the placeholder
sneaks back in, this assertion catches it immediately.

### C2 — Improver role records (program.id, opp, delta)

```python
stage = DGTrackerStage(dg_tracker=tracker, role="improver", timeout=5.0)
# ... attach_inputs with opponent_ids=["g-1"], per_opp_delta=[0.05]
await stage.compute(prog)
pairs = tracker.record_batch.await_args.args[0]
assert pairs == [(prog.id, "g-1", 0.05)]
```

**Why this works:** Symmetric to C1. The role flag flips which slot
program.id occupies in the (D, G, delta) triple. Tests both directions
because both pipelines (G and D runs) instantiate the stage.

### C3 — NaN deltas are skipped

```python
attach_inputs({...}, validation_result=({}, {"per_opp_delta": [float("nan"), 0.2]}))
await stage.compute(prog)
pairs = tracker.record_batch.await_args.args[0]
assert pairs == [(opp_ids[1], prog.id, 0.2)]  # NaN slot dropped
```

**Why this works:** NaN means "no measurement" (opponent crashed, invalid
output, etc.). Recording NaN as a fitness delta would corrupt the sorted
set. The `math.isnan` check catches it before the tracker.

### C4 — Negative deltas reach the tracker (which filters)

```python
attach_inputs({...}, validation_result=({}, {"per_opp_delta": [-0.05]}))
await stage.compute(prog)
pairs = tracker.record_batch.await_args.args[0]
assert pairs == [("d-1", prog.id, -0.05)]
```

**Why this works:** "D made it worse" is a real measurement (not NaN), so
we forward it. DGTracker.record_batch then drops it because only delta>0
is interesting for "best D for this G". This is the hard separation
between "no signal" (NaN) and "negative signal" (kept for diagnostics).

### C5 — Length mismatch is rejected (alignment gate)

```python
attach_inputs(opponent_ids=["d1", "d2", "d3"], per_opp_delta=[0.1, 0.2])  # 3 vs 2
await stage.compute(prog)
tracker.record_batch.assert_not_awaited()
```

**Why this works:** If `opponent_ids` and `per_opp_delta` are misaligned,
we'd record the wrong D for the wrong delta. Better to reject the whole
batch and warn loudly than corrupt the tracker.

---

## D. DGImprovementTracker — dual-write + permanent dedup

### D1 — record_improvement updates per-G AND global sorted sets

```python
await tracker.record_improvement(d_id="d1", g_id="g1", delta=0.05)
per_g = await redis.zrange(f"{prefix}:dg_improvements:g1", 0, -1, withscores=True)
glob = await redis.zrange(f"{prefix}:dg_best_pairs", 0, -1, withscores=True)
assert ("d1", 0.05) in per_g
assert ("d1|g1", 0.05) in glob
```

**Why this works:** Per-G is read by `get_best_d_for_g` (used by
GradientInPromptStage and CompositionInjectionHook). Global is read by
`get_best_pairs` (used by analytics / diagnostics). Both reads must work,
hence dual write.

### D2 — get_best_d_for_g returns the highest-delta D for that G

```python
await tracker.record_improvement("d1", "g1", 0.03)
await tracker.record_improvement("d2", "g1", 0.08)
await tracker.record_improvement("d3", "g1", 0.05)
best = await tracker.get_best_d_for_g("g1")
assert best == ("d2", 0.08)
```

**Why this works:** `zrevrange(..., 0, 0, withscores=True)` returns the
top member by score. If this returns the wrong D, the entire feedback
pathway points to the wrong code.

### D3 — is_pair_injected / mark_pair_injected use a SET (no TTL)

```python
assert not await tracker.is_pair_injected("d1", "g1")
await tracker.mark_pair_injected("d1", "g1")
assert await tracker.is_pair_injected("d1", "g1")
ttl = await redis.ttl(f"{prefix}:dg_injected_pairs")
assert ttl == -1  # -1 means "no expiration"
```

**Why this works:** "Never repeat" was the user mandate. A TTL would
quietly let a pair come back into circulation after 24h and we'd
silently re-inject. The `-1` TTL guarantees permanence.

### D4 — record_improvement with delta ≤ 0 is silently dropped

```python
await tracker.record_improvement("d1", "g1", -0.1)
await tracker.record_improvement("d2", "g1", 0.0)
assert await tracker.get_best_d_for_g("g1") is None
```

**Why this works:** Only positive improvements count as "D beat G".
Recording zeros and negatives would dilute the sorted set with noise
and could let a "D did nothing" entry shadow a real positive one.

---

## E. CompositionInjectionHook — code-level Lamarckian transfer

The user mandate: "we just need to concat code of D and code of G
reasonably". The composed program is a real G program — entrypoint()
returns D(G()). MAP-Elites then evaluates it like any other G.

### E1 — _compose chains entrypoints correctly

```python
g_code = "import numpy as np\ndef entrypoint(): return np.array([[1.,2.],[3.,4.]])\n"
d_code = "def entrypoint():\n    return lambda pts: pts * 2.0\n"
composed = CompositionInjectionHook._compose(g_code, d_code)
ns = {}
exec(composed, ns)
out = ns["entrypoint"]()
np.testing.assert_array_equal(out, np.array([[2., 4.], [6., 8.]]))
```

**Why this works:** This is the *only* way to confirm that the produced
string is actually executable Python that does what we say. exec + assert
on the output value catches anything from rename bugs to indentation
breakage.

### E2 — _compose does not hardcode G's data

```python
assert "_G_POINTS" not in composed
```

**Why this works:** The previous (rejected) design serialized G's points
into a constant. That would freeze data in code and disconnect the
composed program from G's lineage. This check ensures we're shipping
the new design, not a regression.

### E3 — inject_all iterates ALL G programs

```python
g_storage.get_all.return_value = [g1, g2, g3]
dg_tracker.get_best_d_for_g.side_effect = lambda gid: ("d-X", 0.1) if gid == g1.id else None
await hook.inject_all()
assert dg_tracker.get_best_d_for_g.call_count == 3
```

**Why this works:** The user spec was "for all programs in archives on
each iteration". If we iterate only the first or only the best, we'd
miss most of the improvement opportunities the tracker has identified.

### E4 — inject_all skips when no D recorded for that G

```python
dg_tracker.get_best_d_for_g.return_value = None  # no D for any G
await hook.inject_all()
g_storage.add.assert_not_called()
```

**Why this works:** "If there are none improving — then inject none."
Composing without a tracker hit means we'd be injecting noise.

### E5 — inject_all dedup: same (D, G) never composed twice

```python
dg_tracker.get_best_d_for_g.return_value = ("d-1", 0.5)
dg_tracker.is_pair_injected.return_value = True  # already done
await hook.inject_all()
g_storage.add.assert_not_called()
dg_tracker.mark_pair_injected.assert_not_called()
```

**Why this works:** Permanent dedup. Without this, every iteration would
re-inject the same composed program, flooding the archive with
duplicates and starving genuine new mutations of MAP-Elites slots.

### E6 — D missing from archive does NOT mark dedup

```python
d_provider.get_programs_by_ids.return_value = []  # D evicted
dg_tracker.get_best_d_for_g.return_value = ("d-stale", 0.3)
await hook.inject_all()
dg_tracker.mark_pair_injected.assert_not_called()
```

**Why this works:** If D is just temporarily gone from the archive
(eviction, refresh race), we want a future iteration to compose it if
it comes back. Marking dedup here would lock us out forever.

### E7 — Injected program metadata records lineage

```python
injected = g_storage.add.call_args[0][0]
assert injected.metadata["mutation_type"] == "d_improvement"
assert injected.metadata["d_source_id"] == "d-1"
assert injected.metadata["g_source_id"] == g_prog.id
assert "tracked_delta" in injected.metadata
```

**Why this works:** Lineage tracking. C14 in the original plan grepped
for `mutation_type=d_improvement` to confirm composition fired in
production. The metadata is also what archeology and paper analyses
will trace through.

### E8 — Composed program is reachable from G's archive

```python
ids = await hook.inject_all()
assert len(ids) > 0
all_progs = await g_storage.get_all()
assert any(p.id in ids for p in all_progs)
```

**Why this works:** `inject_all` returns the list of injected IDs. They
must actually land in the storage so MAP-Elites can evaluate them next
generation. If `add()` silently drops them, this catches it.

---

## F. GradientInPromptStage — per-G-D selection

When G's LLM mutates a program, it sees the D that was most effective
against THIS specific G. Falls back to global best D when tracker has
no per-G data yet.

### F1 — dg_tracker is threaded into the stage

```python
builder = AdversarialAsymmetricPipelineBuilder(
    ..., feedback_mode="gradient_in_prompt", dg_tracker=tracker
)
graph = builder.build()
stage = graph.nodes["GradientInPromptStage"]()
assert stage._dg_tracker is tracker
```

**Why this works:** A bug in #29 (now fixed) wired GradientInPromptStage
without the tracker, silently making it always fall back to the global
best D. This check confirms the wiring.

### F2 — _select_best_d uses tracker first

```python
tracker.get_best_d_for_g.return_value = ("d-A", 0.1)
provider.get_programs_by_ids.return_value = [
    OpponentProgram(program_id="d-A", code="...", fitness=0.5)
]
result = await stage._select_best_d(program)
assert result.program_id == "d-A"
provider.get_top_k.assert_not_called()  # didn't fall back
```

**Why this works:** Confirms the priority: tracker before global. Without
this, even with the wiring fix, a code-path bug could still skip the
tracker.

### F3 — Fallback to global when tracker has no data

```python
tracker.get_best_d_for_g.return_value = None
provider.get_top_k.return_value = [OpponentProgram(program_id="d-glob", code="...", fitness=0.9)]
result = await stage._select_best_d(program)
assert result.program_id == "d-glob"
```

**Why this works:** Cold-start safety — at gen 0 there's no per-G data
yet. Falling back to global means G still gets *some* gradient signal
instead of an empty prompt.

### F4 — Fallback when tracker hit but D evicted

```python
tracker.get_best_d_for_g.return_value = ("d-stale", 0.1)
provider.get_programs_by_ids.return_value = []  # evicted
provider.get_top_k.return_value = [OpponentProgram(program_id="d-glob", ...)]
result = await stage._select_best_d(program)
assert result.program_id == "d-glob"
```

**Why this works:** Same eviction race as E6 — defensive fallback so a
transient miss doesn't blank out the gradient prompt.

---

## G. Cold-start + engine integration

### G1 — D cold-start uses fallback opponents

```python
log = Path("/tmp/sandbox_run.log").read_text()
assert "[FetchOpponentResults] using" in log
assert "fallback opponents (archive empty)" in log
```

**Why this works:** At gen 0 there are no opponents in the live archive.
The fallback path exists exactly for this; if it doesn't fire, D's
first-generation evaluations would all be NO_OPPONENTS=INVALID.

### G2 — G cold-start: resistance=1.0, fitness=0.5q+0.5

```python
metrics, _ = pop_a.evaluate(opponent_results=[], program_output=valid_pts)
assert metrics["resistance"] == pytest.approx(1.0)
assert metrics["fitness"] == pytest.approx(0.5 * metrics["quality"] + 0.5)
```

**Why this works:** Cold-start branch must use the same ALPHA mix as the
main branch, otherwise gen-0 fitness lives on a different scale than
gen-1+ and MAP-Elites can't compare them. R7 in the agent's risk
register.

### G3 — K_eff = min(K, archive_size) progression

```python
log = Path("/tmp/sandbox_run.log").read_text()
# Early generation, archive small.
assert "get_top_k(3) -> 1 ids:" in log
# Later generation, archive ≥3.
assert "get_top_k(3) -> 3 ids:" in log
```

**Why this works:** The Hall of Fame should grow naturally as the
archive fills up. If we're stuck at 1 forever, the archive never
populates — a deeper bug.

### G4 — Engine completes 5 gens, dag_errors==0 for both populations

```python
assert engine_g.metrics["dag_errors"] == 0
assert engine_d.metrics["dag_errors"] == 0
assert engine_g.gen >= 5 and engine_d.gen >= 5
```

**Why this works:** The ultimate smoke test. If anything is broken in
the DAG wiring (missing edges, sync hook deadlock, type mismatch), it
shows up here as either a non-zero error count or a stuck generation.

---

## H. Logging coverage (production debuggability)

The user explicitly requested: "WE NEED TO COVER EVERYTHING WITH LOGS
ETC SO WE CAN CHECK". These checks confirm the INFO logs are present
and grep-friendly so a researcher can verify behavior from logs alone.

### H1 — Every recorded pair logged at INFO

```python
assert log.count("[DGTracker] record_improvement d=") >= 1
```

**Why this works:** record_improvement is the moment the tracker is
populated. If we don't see this log, the tracker is empty and every
downstream consumer falls back to global mode.

### H2 — DGTrackerStage logs per program

```python
assert log.count("[DGTrackerStage constructor]") >= 1
assert log.count("[DGTrackerStage improver]") >= 1
```

**Why this works:** The stage runs once per program eval. Both roles
should fire at least once across the dual-engine run. If only one fires,
one population's pipeline is broken.

### H3 — CompositionInjection summary every iteration

```python
assert log.count("[CompositionInjection] iteration summary:") >= 1
assert "injected=" in log
assert "skip_no_d=" in log
assert "skip_dedup=" in log
```

**Why this works:** The summary line gives at-a-glance counts of every
decision branch. If any field is missing, the hook didn't run to
completion (timeout, exception).

### H4 — GradientInPrompt source visibility

```python
assert "[GradientInPrompt] injecting D into G prompt" in log
assert "source=per-program" in log or "source=global" in log
```

**Why this works:** The `source` field tells you whether per-G data
existed. Stuck on `global` for the whole run means the tracker isn't
producing per-G entries (could be the bug we just fixed in C, or a
new regression).

### H5 — FetchOpponentIds uses get_top_k (no fallback to old API)

```python
assert log.count("[FetchOpponentIds] get_top_k(") >= 5
assert "get_opponents(n=" not in log
```

**Why this works:** Same as B1 but explicitly counted as a logging
check. If the new HoF API is bypassed (e.g. by a stale code path),
we'd see the old log and silently lose determinism.

---

---

## Section I — Real-infra forensics: tracker integrity

These checks operate on **live Redis** after the sandbox runs. Use
`redis-cli -n <db>` against DBs 1-4 of the redesign-sandbox.

### I1 — F1/F2 — recorded G IDs match concurrent HoF

For each (D, G, delta) in `dg_improvements:*`, the G ID must have been
in `get_top_k(K)` of G's archive at some plausible point in the run
(not a stale ID never present in the live archive after gen 0).

```python
# For D-side DBs (2, 4):
import redis, json
for db in (2, 4):
    r = redis.Redis(db=db, decode_responses=True)
    g_archive = set(r.hvals("island_fitness_island:archive"))
    g_alive = {pid for pid in g_archive if r.exists(f"heilbron_adversarial/pop_a:program:{pid}")}
    # Walk dg_improvements:<g_id>
    for key in r.scan_iter("*:dg_improvements:*"):
        g_id = key.split(":")[-1]
        # G must have existed in opponent (G's) archive at SOME point
        # — we proxy this via current-archive membership. Stricter check
        # would require historical archive snapshots.
        assert g_id in g_alive, f"orphan g={g_id[:8]} in {key}"
```

**Why this works:** orphan G IDs in the tracker are evidence of cache
leak — DGTrackerStage recorded a G that was never actually in the live
archive when CallValidatorFunction ran.

### I2 — F3 — opponent_ids vs validator n_opponents agree per program

In every D-run log, every `[FetchOpponentResults]` "succeeded" line
must report the same N as the matching `[FetchOpponentIds] get_top_k(K)`
line.

```bash
grep -E "FetchOpponentIds|FetchOpponentResults" run_A_D.log | head -20
# Eyeball: get_top_k(3) -> 3 ids: [...]   then   3/3 opponents succeeded
# Mismatch (e.g. 3/2) ⇒ one opponent code missing from cache, F3.
```

**Why this works:** length divergence between the two stages reveals
TOCTOU races on the opponent archive between fetch_ids and fetch_results.

### I3 — F4 — role labels in tracker keys match expected DB layout

D's runs (DB=2 for A_D, DB=4 for B_D) must own the dg_improvements:*
namespace. G's runs (DB=1, DB=3) should NOT have a populated
dg_improvements set on their own prefix — the tracker writes to D's
prefix only.

```bash
for db in 1 3; do
  echo "G db=$db:"
  redis-cli -n $db --scan --pattern '*:dg_improvements:*' | wc -l
done
for db in 2 4; do
  echo "D db=$db:"
  redis-cli -n $db --scan --pattern '*:dg_improvements:*' | wc -l
done
```

**Why this works:** wrong-side population would mean the
constructor/improver role swap was not detected by F31 (or DGTrackerStage
was wired to the wrong tracker).

### I4 — F6 — every dg_best_pairs member is parseable `d|g`

```bash
redis-cli -n 2 ZRANGE "heilbron_adversarial/pop_b:dg_best_pairs" 0 -1 | \
  awk -F'|' 'NF != 2 { print "BAD:", $0; exit 1 } END { print "OK", NR, "members" }'
```

**Why this works:** `get_best_pairs` does `member.split("|", 1)` — any
member missing the `|` is silently dropped. F6 catches malformed writes
that escape into production.

### I5 — F7 — TTL on dg_improvements keys is set (or intentionally absent)

```bash
redis-cli -n 2 --scan --pattern '*:dg_improvements:*' | head -5 | \
  while read k; do echo "$k TTL=$(redis-cli -n 2 TTL "$k")"; done
# Expect TTL > 0 (default 86400s) OR -1 (no expiry — confirm intentional)
```

**Why this works:** stale dg_improvements drift further from the live
archive over time. TTL must be > the planned run duration; -1 is fine
for sandbox but suspect for long runs.

---

## Section J — Real-infra forensics: cache invalidation

### J1 — F9 — archive_reeval=true actually causes re-evaluation

Pick one G program ID. Read its metrics history for the last gen and
verify the timestamp is within ~one generation of the last opponent
archive update.

```python
import redis, json, time
r = redis.Redis(db=1, decode_responses=True)
prog_ids = r.hvals("island_fitness_island:archive")
for pid in prog_ids[:3]:
    raw = r.get(f"heilbron_adversarial/pop_a:program:{pid}")
    if not raw: continue
    m = json.loads(raw).get("metadata", {})
    print(pid[:8], "last_eval_gen=", m.get("last_eval_gen"), "n_evals=", m.get("n_evals"))
```

**Why this works:** if archive_reeval is silently OFF, n_evals stays
at 1 forever — programs are evaluated once and never re-scored when
the opponent archive rotates.

### J2 — F10 — cache_on edge actually folds opponent_ids into hash

This requires either a unit-test artifact or a manual probe: insert a
high-fitness G mid-run, force HoF rotation, and confirm InsightsStage
reruns rather than serving cached output.

```bash
# After run completes, count InsightsStage cache hits vs misses across log:
grep -c "\[Insights\] cache hit" run_A_D.log
grep -c "\[Insights\] cache miss" run_A_D.log
# Cache hits should be 0 in early gens (cold cache), drop again after
# any HoF rotation event.
```

**Why this works:** cache_on edge wiring without value-folding produces
unconditional cache hits — InsightsStage stops thinking after gen 1.
F10 is hard to detect without forced rotation; this is best-effort.

### J3 — F20 — opponent_provider.cache_ttl override took effect

```bash
grep "OpponentProvider" run_A_G.log | head -5
# Should see frequent refresh logs; with cache_ttl=2.0 a refresh
# happens at most every 2s of wall time (per-process).
```

**Why this works:** if the Hydra override didn't take, cache stays at
30s default — HoF rotations within a generation never propagate.

### J4 — F18/F19 — composition_injection_hook is fast enough

```bash
# Time between consecutive engine "step complete" lines on G run:
grep -E "step complete|CompositionInjection iteration summary" run_A_G.log | \
  awk '{print $1, $2}' | head -20
# inject_all should add < few seconds per iteration. > 30s ⇒ blocks engine.
```

**Why this works:** F18 — inject_all is awaited inline post-step.
A slow hook stalls G's engine, asymmetrically advantaging D.

---

## Section K — Real-infra forensics: arm negation

### K1 — F11/F12 — composed-of-composed not running away

```python
import redis, json
r = redis.Redis(db=1, decode_responses=True)
n_total, n_d_imp, n_d_imp_of_d_imp = 0, 0, 0
for pid in r.hvals("island_fitness_island:archive"):
    raw = r.get(f"heilbron_adversarial/pop_a:program:{pid}")
    if not raw: continue
    m = json.loads(raw).get("metadata", {})
    n_total += 1
    if m.get("mutation_type") == "d_improvement":
        n_d_imp += 1
        # Walk parent chain: was the parent ALSO d_improvement?
        for parent_id in (m.get("parent_ids") or []):
            praw = r.get(f"heilbron_adversarial/pop_a:program:{parent_id}")
            if praw and json.loads(praw).get("metadata", {}).get("mutation_type") == "d_improvement":
                n_d_imp_of_d_imp += 1
print(f"total={n_total} d_imp={n_d_imp} d_imp_of_d_imp={n_d_imp_of_d_imp}")
assert n_d_imp_of_d_imp / max(n_d_imp, 1) < 0.5, "composition cascade dominates archive"
```

**Why this works:** F11 — composed_of_composed cascade indicates the
composition hook is repeatedly stacking D on already-composed Gs,
producing degenerate G(D(G(...))) chains.

### K2 — F13 — MAP-Elites accepted the smoothed fitness range

```python
import redis, json
for db, prefix in [(1,"heilbron_adversarial/pop_a"), (2,"heilbron_adversarial/pop_b")]:
    r = redis.Redis(db=db, decode_responses=True)
    fitnesses = []
    for pid in r.hvals("island_fitness_island:archive"):
        raw = r.get(f"{prefix}:program:{pid}")
        if not raw: continue
        f = json.loads(raw).get("metrics", {}).get("fitness")
        if f is not None and f > -100:  # filter sentinel
            fitnesses.append(f)
    print(f"db={db}: n={len(fitnesses)} min={min(fitnesses):.4f} max={max(fitnesses):.4f}")
    assert 0.0 <= min(fitnesses) and max(fitnesses) <= 1.0, "fitness out of (0,1)"
```

**Why this works:** F13 — silent dedup or bucket collision on
MAP-Elites would distort the distribution. Min/max outside (0,1)
means the smoothing math broke or sentinel filter missed.

### K3 — F14/F15 — composed program metadata complete

```python
import redis, json
r = redis.Redis(db=1, decode_responses=True)
checked = 0
for pid in r.hvals("island_fitness_island:archive"):
    raw = r.get(f"heilbron_adversarial/pop_a:program:{pid}")
    if not raw: continue
    m = json.loads(raw).get("metadata", {})
    if m.get("mutation_type") != "d_improvement": continue
    assert m.get("d_source_id"), f"composed {pid[:8]} missing d_source_id"
    assert m.get("g_source_id"), f"composed {pid[:8]} missing g_source_id"
    assert isinstance(m.get("d_fitness"), (int, float)), f"composed {pid[:8]} bad d_fitness"
    parent_ids = m.get("parent_ids") or m.get("lineage", {}).get("parents") or []
    # F15: composed program lineage should reference at least the G it was composed FROM
    if not parent_ids:
        print(f"WARN: composed {pid[:8]} has no lineage/parent_ids (F15)")
    checked += 1
print(f"verified {checked} composed programs")
```

**Why this works:** missing d_source_id/g_source_id means we can't
trace back to which (D, G) pair produced the composition (audit
failure). Missing parent_ids breaks lineage analysis (F15).

### K4 — F32 — composed code reaches ValidateCodeStage

Composed programs are CODE (not raw output). Verify they were
exec'd by the validator:

```bash
grep -E "(d_source_id|composed)" run_A_G.log | head -5
# Should see the composed program entering ValidateCodeStage and
# emerging with metrics, not bypassing.
```

**Why this works:** F32 — if the post_step_hook short-circuits
ValidateCodeStage, we get untrusted code in the archive.

### K5 — F33 — `injected >= 1` threshold isn't being silently met by 1 trivial injection

Cross-check F35 gate isn't passing on a single fluke. Demand a
proportional rate:

```bash
n_inj=$(grep -c "mutation_type=d_improvement" run_A_G.log)
n_gens=$(grep -c "CompositionInjection iteration summary" run_A_G.log)
echo "injections=$n_inj iterations=$n_gens"
# Expect n_inj >= n_gens * 0.1 across the run (at least 10% of iterations
# yielded an injection on average; loose threshold for sandbox).
```

**Why this works:** F33 — single-injection arms can pass the F35 gate
without proving the mechanism is actually load-bearing.

---

## Section L — Real-infra forensics: producer-side correctness

### L1 — F22 — no skipped batches due to length mismatch

```bash
grep -c "DGTrackerStage.*per_opp_delta length.*!=" run_*.log
# MUST be 0. Any non-zero count = silent batch drop.
```

**Why this works:** with the F22 ERROR-level upgrade (this PR), any
length mismatch grep'able and SKIP semantics preserved. A non-zero
count means cache leak between FetchOpponentIds and CallValidator.

### L2 — F31 — no role swap detected at runtime

```bash
grep -c "DGTrackerStage.*ROLE MISMATCH" run_*.log
# MUST be 0.
```

**Why this works:** ROLE MISMATCH is the F31 cross-check firing — a
non-zero count means a population was wired to the wrong evaluate.py,
and recorded (D, G) pairs would have been swapped.

### L3 — F36 — validator artifact shape always (metrics, artifact)

```bash
grep -c "DGTrackerStage.*unexpected validation_result shape" run_*.log
# MUST be 0.
```

**Why this works:** if pop_a/pop_b evaluate.py ever drops the artifact
slot in a refactor, this log fires and DGTrackerStage silently disables.

### L4 — F26 — higher_is_better consistent end-to-end

For Heilbron: actual_fitness, fitness, quality, resistance all
higher_is_better=true; mean_improvement is higher_is_better=false.

```bash
grep -E "higher_is_better" /path/to/problems/heilbron_adversarial/pop_*/metrics.yaml
# Manual confirm: matches above expectations.
```

**Why this works:** if get_top_k or any selector hardcodes True,
the lower_is_better metric is silently sorted backwards.

---

## Section M — Real-infra forensics: scaffold integrity

### M1 — F37 — pre-run flush + assert was actually run

The launch.sh prints "OK" lines for every dg_injected_pairs key. If
those lines are missing from the launch transcript, the flush gate
was bypassed (script run with --skip-flush or partial execution).

```bash
grep -c "OK:.*dg_injected_pairs" /path/to/sandbox/launch_transcript.log
# Expect == 8 (4 dbs * 2 keys each).
```

**Why this works:** F37 — without the pre-flush, residual state from
prior runs corrupts the dedup tracker. M1 verifies the gate fired.

### M2 — F35 — end-of-run gate ran and passed

```bash
grep "F35 gate PASSED" /path/to/sandbox/post_run_gate_output.log
# Required.
```

**Why this works:** trivial confirmation the post-run gate actually
ran and didn't quietly exit on a non-essential earlier failure.

### M3 — Sentinel value -1000 active (not stale -1.0)

```bash
grep -E "sentinel_value:" problems/heilbron_adversarial/pop_*/metrics.yaml
# All entries should be -1000.0 (not -1.0).
```

**Why this works:** sentinel-vs-smoothed-fitness ambiguity at -1.0
risked invalid programs being treated as low-fitness valid entries.
M3 confirms the change took.

### M4 — opponent_provider.cache_ttl override visible in cfg dump

```bash
grep -A1 "opponent_provider:" cfg_run_A_G.txt | grep "cache_ttl"
# Should print: cache_ttl: 2.0
```

**Why this works:** the Hydra override may silently no-op if the
syntax is wrong. M4 confirms the override resolved.

---

## Pass criteria

A green sandbox run requires ALL checks above to pass. Failure of any
check blocks the next experiment launch — root-cause and fix the
underlying behavior, do NOT relax the check.

The pass table goes into the PR description for the next experiment's
pre-registration so reviewers can audit which behaviors have been
guaranteed before compute is spent.
