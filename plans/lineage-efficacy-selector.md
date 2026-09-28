# Lineage-Aware Card Selection — Design (DRAFT, brainstorming output)

> **Status:** design artifact for approval. NOT a plan, NO code yet. Implementation is gated on
> (a) your approval and (b) the E1 counterfactual go/no-go (rank−prod, PID 3504804). Read-side
> twin of the directed-novelty arm in `plans/exemplar-adaptive-memory.md`.
>
> **Architecture: filter-first → retrieve** (confirmed feasible). Exclude the lineage-applied
> card ids from GAM's candidate pool BEFORE it ranks, so GAM's normal single relevance pick is
> automatically lineage-fresh. This dissolves the "widening" and "suppress-vs-substitute"
> problems of the earlier retrieve-then-filter sketch.

## Goal

Stop the shared-bank read path from re-serving cards already used up a program's lineage —
by pruning them from GAM's candidate space before GAM ranks. GAM still does all retrieval and
relevance; it just never sees the stale cards, so its pick substitutes a fresh one for free.

## The shape (one abstraction, filter-first)

One new read-side abstraction — a **`CardExcluder`** — answers "which card ids must not be
retrieved for this program?" Its output is threaded into the GAM research call as a hard prune.
Everything else is plumbing to feed it (a birth-time metadata key) and a one-line guard in the
GAM candidate-assembly step. v1 = **component A + component B**. No widening, no new budgeter.

## Causal chain (signal → behaviour → metric)

- **Signal:** the requesting program's lineage-applied card-id set (cards selected anywhere from
  root through this program), surfaced storage-free via birth-time metadata.
- **Behaviour:** the excluder hands that set to `research(...)`; GAM assembles candidates, drops
  the excluded ids per-iteration, and the selector-LLM ranks over the lineage-fresh remainder →
  the mutator receives a fresh relevant card instead of a re-served stale one.
- **Metric:** injected-card lineage-staleness → ~0% (by construction); monoculture (top-card
  share, 32% baseline) ↓; child-improvement *frequency* ↑ (analytics: fresh 71% vs carry-over
  53%); validity held or ↑. Mean Δfit moves little (Study H: the lever is frequency).

## Riskiest link

Not feasibility (resolved — clean seam below) but **pool-thinning**: if every candidate GAM
retrieves is lineage-applied, the pruned pool is empty → no card injected (acceptable fail-to-
empty, but it's "inject nothing," not "inject fresh"). With `top_k_by_tool` = {vector:3,
page_index:5} and `max_cards=1`, pruning a few ids usually leaves ≥1; the rare empty case is
benign. Guardrail: instrument **empty-injection rate** per arm; optional small `top_k` margin if
it bites. E1's `rank` arm pre-tests substitution offline.

## Codebase constraints this design respects

- **Storage-free read path** — exclusion comes from birth-time **metadata** (your choice), not a
  DAG walk; the provider needs no `ProgramStorage`.
- **GAM stays** — we prune its candidate list; we do not write a ranking selector or widen K.
- **The selector-LLM picks from a candidate list we control** (`ExperimentalDecision.top_ideas`,
  validated against the candidate set at `research_agent.py:559`) → pruning that list *is* a hard
  gate, even against a hallucinated id.
- **No applied-scan, no within-run RCT hook** (`card_rct.py` deleted, task #93) in v1.

## Components

### A. Birth-time lineage-applied metadata  *(write-side, always-on, inert unless an excluder reads it)*
- New constant `MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY = "memory_lineage_applied_ids"`
  in `gigaevo/evolution/mutation/constants.py`.
- Computed at child birth in `gigaevo/evolution/engine/mutation.py` (the spot that already
  freezes `memory_injected_idea_ids`, ~:65-75):
  `child[lineage_applied] = sorted( ∪ over parents p of ( p[lineage_applied] ∪ p[selected_idea_ids] ) )`.
  Root → `[]`. This is the transitive closure built incrementally — O(1) per birth, no storage,
  offline-recomputable. (A 1-hop alternative reusing the existing `memory_injected_idea_ids`
  needs no new key, but only excludes immediate-parent cards; monoculture is multi-generation,
  so we keep the full closure — your birth-time-propagation choice.)

### B. `CardExcluder` abstraction + the prune  *(read-side — the "one more abstraction")*
- New `CardExcluder` Protocol in `gigaevo/memory/core/protocols.py`:
  `exclude_for(self, program: Program) -> set[str]`.
- `NullExcluder` → `set()`; **the default**, so control behaviour is byte-identical.
- `LineageExcluder` → `set(program[lineage_applied]) | set(program[selected_idea_ids])` (all
  cards used from root through this program). Held by `SelectorMemoryProvider`; called in
  `select_cards` (`provider.py:167-181`), which has the `Program` in hand.
- New Hydra group `config/memory/excluder/` with `null.yaml` (default) and `lineage.yaml`.
- **The prune (plumbing + one guard):** thread an optional `exclude_ids: set[str] | None = None`
  along the existing keyword-only chain —
  `select_cards` → `MemoryReadPipeline.select/_select` (`read_pipeline.py:55-92`; retriever call
  at `:112-114`) → `GamRetriever.research` (`retriever.py:49-54`) → `AmemGamMemory.research`
  (`memory.py:443-462`) → `ResearchAgent.research/_research_experimental/_search_no_integrate`
  (`research_agent.py:294-368, 831-941`). Apply the filter at exactly one place:
  **`ResearchAgent._build_retrieved_ideas` (`research_agent.py:~427`)** — skip any hit whose
  resolved `card_id ∈ exclude_ids`. Covers both tools, per-iteration, pre-LLM.
  *(Note: `_build_retrieved_ideas` lives in vendored GAM, `gigaevo/memory/_vendor/GAM_root/...`;
  the repo already patches vendored GAM — tasks #68/#69 — so a one-line guard there is in-bounds.)*

## Data flow

```
select_cards(program)                          provider.py:167
   excluder.exclude_for(program) ─► exclude_ids   <- NEW B (reads lineage_applied metadata, A)
        │
        ▼
read_pipeline.select/_select(exclude_ids=…)    read_pipeline.py:84  (parents in scope)
        ▼
retriever.research(query, exclude_ids=…)       retriever.py:49 → memory.py:443
        ▼
GAM assemble candidates ─► DROP exclude_ids ─► rank        <- NEW one-line guard, research_agent.py:~427
        │  (vector + page_index, per-iteration, before selector-LLM)
        ▼
selector-LLM picks from pruned list ─► shortlist (auto lineage-fresh)
        ▼
resolve → reputation.card_posterior → auction (safety, UNCHANGED) → budget cap → render
```

## Packaging (whole-run arms — recommended, pending your confirm)

- **Control:** `excluder=null` (byte-identical to today).
- **Treatment:** `excluder=lineage`.
- Two runs across two redis dbs, mirroring db9/db10 & db11/db12 (`feedback_mirror_baseline_exactly`).
  Component A ships in both arms (inert in control). Within-run salt-gated RCT deferred.

## Deferred (YAGNI for v1)

- **Widening GAM to top-K** — unnecessary under filter-first; dropped.
- **Efficacy-ranked tie-break (the old component D, "reweight after pick")** — to v2; v1 lets
  GAM relevance order the fresh survivors and the existing auction gate them.
- BD/behavioural directed-novelty (Study F's working axis) — second arm.
- Applied-scan guardrail (redundant-still-present vs genuinely-removed) — the hard lineage prune
  already drops both buckets; no in-repo detection to reuse.

## Prediction table (control → treatment)

| metric | control | treatment (lineage exclude) | why |
|---|---|---|---|
| injected-card lineage-stale % | ~65% | ~0% | hard prune, by construction |
| top-card injection share | 32% | ↓ (more distinct cards) | monoculture is downstream of re-serving |
| P(child improves) | baseline | ↑ several pp | fresh 71% vs carry-over 53% (analytics) |
| mean Δfit | baseline | ~flat / small ↑ | lever is frequency not magnitude (Study H) |
| child validity rate | baseline | ≥ baseline | auction safety gate untouched |
| empty-injection rate | low | watch ↑ | pool-thinning risk (riskiest link) |

## Test plan (TDD, behaviour via public API)

- A: child born from parents with known `selected_ids`/`lineage_applied` carries the correct
  sorted union closure; root → `[]`; idempotent re-eval; grandparent card present at depth 2.
- B (unit): `LineageExcluder.exclude_for` = parent-closure ∪ own selected; `NullExcluder` = ∅.
- B (integration, no LLM): `_build_retrieved_ideas` with `exclude_ids` drops exactly those
  `card_id`s from both vector and page_index hits and nothing else; empty pool when all excluded.
- B (pipeline): `excluder=null` reproduces the frozen control goldens
  (`tests/memory/test_core_read_pipeline.py`); `excluder=lineage` returns a lineage-fresh pick.
- Config: each new leaf Hydra-builds; default presets unchanged.

## Open questions

1. Confirm whole-run packaging (recommended) vs within-run RCT.
2. ~~Filter order~~ — **RESOLVED: filter-first.** ~~Widening~~ — **dropped.** ~~Efficacy~~ — **v2.**
3. Optional `top_k` margin for the pool-thinning edge case — decide empirically (instrument
   empty-injection rate first; only add a margin if it bites).
