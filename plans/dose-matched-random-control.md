# Dose-Matched Random-Drop Control (lineage isolation) — DEFERRED design

**Status:** DESIGNED, launch DEFERRED (blocked by live runs). Queued per user "Yes please"
(2026-06-15) alongside the variance-floor replicates ([[project_lineage_aware_card_selection]],
task #161). This is task #162.

## Why this control exists (causal chain)

The lineage gate ([[project_lineage_aware_card_selection]]) excludes, for each program, the
`k` card ids in its birth-frozen ancestry closure
(`MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY`) from GAM's candidate pool before the
selector-LLM ranks. db13-vs-db7 shows +0.0146 best-CV and carry-over 27%→5%.

**Confound:** two mechanisms are entangled in that delta —
1. **AWARENESS** — excluding the *ancestrally-applied* cards specifically (the hypothesis).
2. **DOSE** — simply removing `k` cards from the slate, shrinking/refreshing it regardless of
   *which* cards (a nuisance: filter-first sometimes empties the slate → mem_used 78%→68%).

Signal → behaviour → metric: if the gain is DOSE, a control that drops `k` **random** pool
cards per program reproduces most of the +0.0146; if the gain is AWARENESS, the random control
stays near db7/db2. **Prediction:** random-drop best-CV lands between db7 (0.860) and db13
(0.875), strictly below db13 — the residual db13−random gap is the awareness-attributable effect.

## Riskiest link — the dose must be matched at the POOL, not the bank

`exclude_for(program) -> frozenset[str]` runs **pre-retrieval** (provider.py:185) and sees only
the program, never the candidate pool. The pool (relevance-ranked `hits`) first exists downstream
in `_build_retrieved_ideas` (research_agent.py:428). A `RandomExcluder` that samples `k` ids from
the **whole bank** would almost always miss the small relevance slate → effective dose ≪ k →
the control trivially shows "no effect" for the wrong reason. **A faithful dose-match must drop
`k` cards from the actual `hits` pool**, which only `_build_retrieved_ideas` can do.

## Faithful design

Thread a per-call **random-drop dose** alongside `exclude_ids` down the existing
read_pipeline → retriever → research_agent path (the same plumbing lineage already uses), and at
the drop site drop `k` of the surviving hits at random:

- New excluder `RandomDropExcluder` (NEW file `gigaevo/memory/core/random_drop.py`) exposes the
  dose, NOT ids: `dose_for(program) -> int = len(lineage closure)` (reads the SAME birth-frozen
  metadata key, so it is exactly per-program dose-matched to lineage). `exclude_for` returns
  `frozenset()` (it excludes nothing by id).
- Extend the `CardExcluder` protocol with an OPTIONAL `dose_for(program) -> int = 0` default so
  `NullExcluder`/`LineageExcluder` are unchanged (dose 0).
- provider.py passes `random_drop_dose=self._excluder.dose_for(program)` through
  read_pipeline → retriever → research_agent into `_build_retrieved_ideas`.
- In `_build_retrieved_ideas`, after the `exclude_ids` filter, if `random_drop_dose > 0`,
  drop `min(dose, len(kept)-? )` kept hits chosen by a **program-seeded** RNG (seed =
  hash(program id) so it is deterministic/reproducible, NOT global `random`). Keep at least the
  top hit unless dose ≥ pool size (mirror lineage, which can empty the slate).
- Hydra: NEW `config/memory/excluder/random_drop.yaml`
  (`_target_: gigaevo.memory.core.random_drop.RandomDropExcluder`). `full.yaml` default stays
  `- excluder: none`. Launch override `memory/excluder=random_drop`.

Control is byte-identical to db7/db2 when dose is 0 everywhere (cold start, no ancestry).

## Why DEFERRED (do not launch yet)

The drop must live in `_build_retrieved_ideas` and the dose must thread through
provider.py / read_pipeline.py / retriever.py / research_agent.py / protocols.py — **all
imported by the live db13 + db14 lineage workers**. Editing them now violates
[[feedback_no_import_changes_mid_run]] (workers re-import → silent corruption of the very runs
we are validating). Launch is gated on **db13 AND db14 completion** (both free the interface);
the random-drop run then goes on **db12** (free), 800-mutant budget, recipe mirrored from
`/tmp/launch_lineage_db14.sh` swapping only `memory/excluder=random_drop` + `redis.db=12` +
outdir. Scientifically the control may run after the treatment — ordering is irrelevant for a
control.

(Rejected alternative: a whole-bank `RandomExcluder` wired store-handle-via-Hydra needs no
live-file edit, but under-doses as argued above. Not worth shipping a control that fails for the
wrong reason.)

## TDD task list (execute once interface is free)

- [ ] **T1** `tests/memory/test_random_drop_excluder.py`: `dose_for(program)` == len of the
  closure metadata; `exclude_for` returns `frozenset()`; dose 0 when no metadata. RED→GREEN with
  `RandomDropExcluder` in `gigaevo/memory/core/random_drop.py`.
- [ ] **T2** Protocol test: `CardExcluder.dose_for` defaults to 0 for Null/Lineage (back-compat).
- [ ] **T3** `_build_retrieved_ideas` test: with `random_drop_dose=k` and a pool of N>k hits,
  exactly k are dropped, choice is deterministic under a fixed program seed, top hit survives
  unless k≥N; `random_drop_dose=0` is byte-identical to today.
- [ ] **T4** Thread-through test: provider → research_agent passes the dose end-to-end (mock the
  research agent, assert it receives `random_drop_dose`).
- [ ] **T5** Hydra build test: `memory/excluder=random_drop` instantiates `RandomDropExcluder`;
  `full.yaml` default still `NullExcluder`.
- [ ] **T6** Green gate (`/run-tests tests/memory`), HOLD commit for user approval, then launch
  db12 and add the hourly monitor a 4th California arm (or a one-shot equal-budget compare).

Related: [[project_lineage_aware_card_selection]] [[project_db7_memory_run_analytics]]
[[feedback_no_import_changes_mid_run]] [[feedback_variance_floor_first]]
