# Program-card dedup — diagnosis + fix design (2026-07-03)

Triggered by two byte-identical program cards (`program-22283940`, `program-a2b53d26`;
same code md5 `a075f8d6ae…`) banked as separate `added` rows in R1. Extends the
`04_issues_log.md` no-op-crossover finding to the **dedup** side.

## Corrected diagnosis (the framing "intra-batch dedup is absent" is only half right)

1. **The index is synchronous.** `LocalMemoryStore.save` = `bank.put → bank.persist →
   index.upsert` (`storage/local.py:80-82`). Both write loops (`ingest_idea` per record,
   `admit_program` per exemplar) are **sequential awaits under one `_run_lock`**. So within
   a batch, iteration N+1's `nearest()`/`snapshot()` already sees what N admitted. Intra-batch
   dedup is **not structurally absent** — the program path's *mechanism* just never fires.

2. **Idea cards get two real dedup layers**, both LLM-arbitrated (no distance threshold):
   - online: `ReconcileAgent` per diff (NEW / DUPLICATE / MERGE) over top-k neighbors;
   - backstop: whole-bank `consolidate()` pass every `consolidation_every_n=32` cards.

3. **Program cards get neither.** Their only gate is `_nearest_program_twin` — a cosine test
   on the **description prose** at `program_twin_eps=0.05` (i.e. ≥0.95 similarity). And
   consolidation **explicitly excludes them** (`consolidation.py:76-78`: "program exemplar
   cards are identity-keyed … never merge them"). So program dedup is: one inert prose gate,
   no backstop.

### Why 0.95-cos is inert (your "completely useless")

The librarian's own docstring concedes it: *"raw notes and authored prose sit too far apart
in embedding space for a cosine gate to fire on real twins"* (`librarian.py:8-11`). Two
**identical codes** get **independently-authored descriptions** from the Thinking model; those
descriptions land well past 0.05 apart, so the twin query returns nothing → both `added`.
The gate can only catch programs whose *prose* is near-identical — which is neither necessary
nor sufficient for code/strategy identity. It is dead weight.

## Fix — exact code-identity dedup for program cards

Replace the prose-cosine twin gate with an **exact code match**, which is deterministic,
embedding-free, LLM-free, and **intra-batch-safe by construction** (the bank is synchronously
updated and the loop is sequential, so a co-batch twin is already in `snapshot()`):

```python
# librarian.py
def admit_program(self, card, *, higher_is_better):
    twin = self._code_twin(card)                 # exact code match, not prose cosine
    if twin is not None:
        if not _strictly_better(card.fitness, twin.fitness, higher_is_better):
            return ""                            # keep banked twin; drop redundant incoming
        self._store.delete(twin.id)              # incoming strictly better → replace
    return self._gate.admit(card)

def _code_twin(self, card):
    key = _code_key(card.code)
    if not key:
        return None
    for other in self._store.snapshot():
        if other.kind is CardKind.PROGRAM and other.id != card.id \
                and _code_key(other.code) == key:
            return other
    return None

def _code_key(code: str) -> str:                 # normalize trailing-whitespace noise only
    return "\n".join(line.rstrip() for line in code.strip().splitlines())
```

Tie-break unchanged: strictly-better fitness wins; equal → incoming dropped. N (program
cards) is tens–low-hundreds, so the per-exemplar `snapshot()` scan is negligible next to the
LLM authoring it follows.

**No program consolidation backstop is needed.** Exact hashing has no greedy/order-dependence
(the reason ideas need a backstop is top-k *recall* misses in embedding space). The online
gate alone now fully prevents exact code twins — and we reintroduce **no** cosine threshold
anywhere.

### Removed (blast radius already grepped)
`program_twin_eps` + `_nearest_program_twin` everywhere: `merge.py` (DedupPolicy field),
`writer.py:192`, `librarian.py` (`__init__` arg + method + docstring), `config/memory/{writer,
full}.yaml`, and the two asserting tests (`test_librarian.py:62`, `test_merge.py:96,99`).
`NeighborSource`/`top_k` stay — still used by `ingest_idea` (INSIGHT) and consolidation.

### Tests (TDD, `tests/memory/write/test_librarian.py`)
- identical code + different prose, equal/lower fitness → second **dropped** (bank = 1);
- identical code, incoming strictly better → **replaces** banked twin;
- distinct code → **both** banked;
- (intra-batch = the same two sequential `admit_program` calls; no new harness).

## Final design — dedup is content-based for BOTH kinds; the arbiter differs by kind

| kind | keyed on | arbiter | why | layers |
|---|---|---|---|---|
| **insight** | description **prose** (semantic) | **LLM** (reconcile + consolidate agents) | near-duplicate ideas are paraphrases, not byte-equal — needs judgment | online reconcile per diff + periodic whole-bank consolidate + **new** intra-batch consolidate |
| **program** | **normalized code** (`_code_key`) | **exact match** (no LLM, no embedding) | two exemplars are twins iff their code is identical — an exact predicate, no judgment | immediate at `admit_program` |

Both are **content-based and threshold-free** — the old `program_twin_eps` cosine was the *only*
distance threshold anywhere in the write path, and it is now gone. The asymmetry the user
flagged ("hardcoded for programs specifically") is resolved: programs no longer get a bespoke
prose-cosine gate; they get an exact-content predicate, ideas get the LLM content arbiter.

## Ideas intra-batch layer (decision **B**, chosen)

Programs dedup **immediately** at admit time (code hash). Ideas only dedup **online** (greedy,
order-dependent) plus a **periodic** whole-bank `consolidate()` every `consolidation_every_n=32`
cards. So two same-lever ideas written *in one batch* sit un-folded until the counter trips —
and get read/injected into the mutator many times first (one card was seen injected 60-120×).

**B** closes that gap symmetrically: run a `consolidate()` pass **scoped to the batch's new card
ids** at the end of every increment (neighbors still ranked over the full bank, so a batch card
also folds against a prior-batch twin). Reuses the exact same LLM arbiter + `gate.merge`
machinery and the shared `reviewed` memo — no new mechanism, just a trigger + a `subset` filter.
Gated on the existing `consolidation_every_n > 0` master switch (no new config knob).

**Decision: B-inline (chosen by user, IMPLEMENTED + green).** The scoped pass is awaited in
`_run_increment_locked` after the stats restamp, bounded by `ingest_call_timeout_s` and
graceful-degrading (timeout/error → skip, never abort the increment). The periodic whole-bank
background pass is kept alongside it (it catches cross-batch drift the subset pass skips).

Concrete edits:
- `consolidation.py`: `consolidate(subset=...)` restricts the outer query loop to the batch ids
  (neighbors still rank over the full bank, so a batch card folds an older twin too); the merge
  fires from either direction of an unordered pair, so querying only the subset still catches
  every subset-vs-anything dup. `ConsolidationScheduler.consolidate_written(ids, timeout=)` runs
  it inline **without re-acquiring the run lock** (caller holds it — the lock is not reentrant),
  sharing the `reviewed` memo with the background pass. Extracted `_consolidate_once` so `_run`
  (background) and `consolidate_written` (inline) share the failure-count + event-emit path.
- `writer.py`: the record loop collects `written_ids`; after stats, `await
  consolidate_written(set(written_ids), timeout=ingest_call_timeout_s)`; `note_writes` still
  schedules the periodic pass. Gated on the existing `consolidation_every_n > 0` master switch —
  no new config knob.

Tests: `consolidate` subset (folds older twin, leaves non-subset pair untouched);
`consolidate_written` fold / disabled-noop / empty-noop / shared-reviewed-memo / timeout-degrade;
writer-level end-to-end (two co-batch same-lever records → one card after `run_increment`).
93 write-layer + 260 memory + 9 integration green; ruff clean.

## Live-run + sequencing notes
- **R1/R2 are unaffected by the edit.** They run from this worktree, but their main processes
  already imported these modules; Python won't hot-reload. The fix applies to the *next*
  launch only. Workers do eval, not memory writing.
- This is a **correctness** fix to the write path, not a reader/fitness change — it does not
  invalidate the A/D fitness comparison R1/R2 are producing.
- Sequencing: fold into PR #294 now vs. land as a follow-up after R1/R2 sign-off — user's call.
- Commit **held** per standing rule (wait for approval; push to #294 still held).
