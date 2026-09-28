# Gain-event sparsity in the memory smoke bank (S3_rerun, 2026-06-28)

Run: `outputs/memory_smoke_2026-06-28/S3_rerun` (Heilbronn 11-point, `memory=full` + GAM
auction + `storage=disk`, branch `feat/livememory-refresh-resilience`).

## Question

Why do "reasonable" idea cards in `memory/api_index.json` have so many *null* gain events,
and is `programs` populated correctly / why does it differ from gain events?

## Headline

There are **zero literal-null gains** — `gain` is never `null`. The observation is that
**45 / 58 cards (78%) carry an *empty* `gain_events` list** while holding up to 15 `programs`.
This is **expected, pre-existing memory-efficacy behavior — not a refactor regression**.
`programs` and `gain_events` are two different populations: write-side provenance vs
read-side use-attribution.

## `programs` vs `gain_events` — different fields, different paths

| | `programs` | `gain_events` |
|---|---|---|
| Meaning (models.py) | "Program ids that **exhibited** the idea" | "Use-attributed base-relative **injection** events" |
| Path | WRITE | READ |
| Born | `[child_id]` at authoring (`librarian.py:103,117`) | empty (`None`) |
| Grows by | near-dup provenance bump (`admission_gate.py:90`), MERGE union (`card_merge.py:34`) | a later mutation **selecting + declaring-used** the card |
| Requires the card to be read? | **No** | **Yes** |

So a card authored/reinforced by 15 child diffs but never re-selected has `programs=15,
gain_events=[]` — correct by design. They are orthogonal; equality was never expected.

## Why gain_events is empty for most cards — the attribution funnel

A card earns one `ContextualGain` for a child **only** when (`injection_posterior.py:94-114`):

1. the child has a resolvable base baseline (`base_fitness is not None`) and a non-empty
   `base_selected_idea_ids`, **and**
2. the card id is in `base_selected_idea_ids ∩ card_ids_used` — i.e. it was both
   **selected by the reader for the mutation's base parent** *and* **declared applied by
   the mutator**, **and**
3. the child is valid (invalid → one forced-harm event; missing fitness → skipped).

Measured across the run's 105 program records:

| Stage | Count |
|---|---|
| mutation children (have parents) | 100 |
| valid (`is_valid>0`) | 97 |
| reader selected ≥1 card for the **base parent** | **71** (sum ids = 71 → ~**1 card/child**) |
| mutator declared `card_ids_used` | 48 (sum ids = 55 → ~1.1/child) |
| both non-empty | 44 |
| **base_selected ∩ card_ids_used non-empty → earns an event** | **33** |

Two compounding bottlenecks:

- **Base side is ~1 card per child.** The GAM agent collapses the candidate pool to a
  single base card before the auction (known finding: GAM pool collapse, `candidate_count=1`).
  With at most one creditable card per mutation, credit can only ever land on a tiny set of
  cards per sweep — 45/58 are never *the* one.
- **Read side declares usage only ~half the time** (48/100). Donor cards (used but selected
  for the *other* parent) and hallucinated ids earn nothing (`injection_posterior.py:87-90`).

`gain_events` is also **recomputed authoritatively from the full pool every sweep**
(`card_stats.py:105-121`, `stamping.py:30`): a card not credited in the final sweep has its
events cleared to `None`. So the exported list is the *final-sweep* attribution, not a
cumulative tally.

This reproduces the long-standing card-inertness result (~70-78% of cards never contribute
measured gain). The refactor did not change attribution semantics.

## Two real but minor / pre-existing issues found (NOT introduced by this branch)

**(A) Merge/consolidation does not remap gain attribution (id-namespace mismatch).**
`card_ids_used` is frozen on the child at mutation time, pointing at the card id alive then.
If that card is later merged/consolidated/evicted into a *different* surviving id, the next
sweep recomputes `events[old_id]`, but `restamp_and_sweep` only visits **surviving** cards
and `stamp_gain_events` looks up by the card's **current** id (`stamping.py:30`,
`card_stats.py:117-120`) — so the absorbed id's events have no card to land on and are
dropped. Evidence: the final posterior credited **15 cards / 31 events**, but only
**13 cards / 24 events** survived to export; the 2 missing (`mem-2cf928e04663`,
`mem-1b26a818cf1d`, 7 events) were removed after being credited. This is the documented
"`MemoryCard.usage` DEAD — id-namespace mismatch". Impact here is small because librarian
MERGE folds a *new* `id=""` card into the survivor (survivor keeps its selected id);
consolidation of two *existing* cards is the path that would orphan attribution.

**(B) Eviction-after-credit in the same sweep — verified correct.** `CardStatsUpdater.update`
restamps then calls `gate.sweep()` in the same call (`card_stats.py:103,121`); a card credited
this sweep can be evicted as confidently-harmful in the same sweep. The default evictor is
`HarmEvictor(reputation=BetaBinomialReputation())` (`write_stack.py:148-150`) — the same legacy
`save_card` harm gate relocated, with **unchanged thresholds** (`harm_min_events=3`,
`harm_quantile=0.80`, `harm_threshold=0.5`, `noise_band_k=1.0`); only its *sourcing* changed on
this branch (resolves the block via `block_from_events(card.gain_events)` instead of a
pre-stamped `evolution_statistics.ALL`). `sweep()` reads the **freshly-restamped** bank, so it
acts on the card's full authoritative event set — the ordering is correct, not a race.

The two cards evicted this run were genuinely net-harmful, not "credited-then-wrongly-killed".
Reconstructing the credited-child deltas (heilbron, `higher_is_better=true`, gain =
`child_fitness − base_fitness` over children where the id is in `base_selected ∩ card_ids_used`):

| Evicted card | events at eviction | credited-child deltas | posterior | optimistic 0.80-quantile |
|---|---|---|---|---|
| `mem-2cf928e04663` | 3 (later 4, orphaned) | −0.00085, −0.00061, −0.00154, −0.00095 | Beta(1,5) | ≈0.275 < 0.5 |
| `mem-1b26a818cf1d` | 3 | −0.00310, −0.00673, −0.00287 | Beta(1,4) | ≈0.33 < 0.5 |

**Every credited child of both cards regressed** (all-negative deltas, all below the robust noise
band), so each posterior is `k_harm = n` → even the optimistic read says <50% chance of "not
harmful". Eviction is principled. (The earlier draft's "4 *positive* events" was wrong — the
deltas are all negative.) After eviction the pool-keyed recompute keeps emitting events for the
deleted id (e.g. `mem-2cf928e04663` shows 4 at later sweeps) — orphaned but harmless, since
`restamp_and_sweep` only visits surviving cards. This fully explains the 31→24 export gap as
"2 genuinely-harmful cards removed," **no positive signal lost**.

## Verdict

- Null/empty gain events for reasonable cards: **EXPECTED** (read-side use-attribution is a
  selected∩declared-used conjunction, base side ~1 card/child). Not a refactor bug.
- `programs` populated correctly: **YES** — write-side provenance ("exhibited the idea"),
  distinct from read-side `gain_events` by design.
- (A) merge attribution remap: **genuine bug** (id-namespace mismatch), pre-existing, not
  introduced by `feat/livememory-refresh-resilience`. **Latent in this run** — all 90 ledger
  merges were librarian MERGEs that fold a new `id=""` card into the survivor (survivor keeps
  its selected id, nothing orphaned), and the 2 consolidation passes folded **0** pairs; the
  31→24 export gap is fully explained by (B) eviction, not (A).
- (B) eviction-after-credit: **EXPECTED/correct, empirically verified.** Default evictor is the
  unchanged-threshold `HarmEvictor`; `sweep()` reads the freshly-restamped bank; both evicted
  cards had **all-negative** credited-child deltas (every child regressed) → confidently-harmful
  posteriors. No positive signal was lost in the 31→24 export gap.

## Consolidated dual verdict (Claude + codex, both read the code independently)

| # | Question | Claude | codex | Agree? |
|---|---|---|---|---|
| 1 | `programs` vs `gain_events` | EXPECTED — write-provenance vs use-attribution | EXPECTED — same | ✅ |
| 2 | empty gain_events on reasonable cards | EXPECTED — `base_selected ∩ card_ids_used`, ~1 card/child | EXPECTED — same | ✅ |
| 3a | merge/consolidation id-remap | BUG, pre-existing, latent here | BUG (`stamping.py:30` keys current id; no alias layer) | ✅ |
| 3b | eviction-after-credit same sweep | EXPECTED/correct — both evicted cards all-negative deltas, default `HarmEvictor` thresholds unchanged | (pending re-consult with data) | — |

codex's framing of 3a: the next restamp is authoritative with **no alias/remap layer**, so
absorbed-id events are dropped — contradicting `card_merge.py:3-11`'s evidence-preservation
intent. Identical to Claude's finding.

## Resolution (same PR)

**3a — FIXED via an absorbed-id alias layer.** `MemoryCard` now carries
`absorbed_ids: list[str]` (`models.py`). `merge_cards` records the folded-away id (and any
ids that card had itself absorbed, so multi-hop chains keep re-aliasing) onto the survivor
(`card_merge.py:_absorbed_ids`), and the librarian/consolidation merge submissions forward
the partner's chain (`consolidation.py:100`). At restamp, `stamp_gain_events` folds the
events the pool still keys to a survivor's `absorbed_ids` onto the survivor. The own-id list
is kept **verbatim** and the absorbed fold dedups by **trial identity, not value**
(`stamping.py`): the pool gives each child one `ContextualGain` object that it appends to
every credited id, so a single child crediting both the survivor and an absorbed id is one
shared object (deduped), while distinct invalid children of one base parent are distinct
value-equal objects (all kept) — the multiplicity the harm gate counts as `intro_events`.
This is a **fold-after**, not a remap-before: it preserves the
decision-time `base_selected ∩ card_ids_used` semantics (a remap-before could manufacture an
intersection that never existed when the child was scored). Latent in this run, so no export
numbers change here; the alias layer prevents the orphaning whenever a future consolidation
folds two *existing* cards.

**Evictor verdict is global (`context=None`) — confirmed by design, not a bug.** The
question raised: reputation is contextual (`BDProximityReputation` reweights toward the query
parent's MAP-Elites cell), so why does `HarmEvictor.should_evict` call
`reputation.card_stats(card, None)` with no context? Because an **eviction sweep has no query
parent** — it is bank maintenance run after an ingest pass, not a selection decision keyed to
some mutation's base cell. There is no cell to reweight toward, so `context=None` is the
correct reduction: it pools *all* of the card's gain events (discarding nothing) and only
omits the proximity reweighting, which is undefined absent a target. `BDProximityReputation`
already returns the global posterior when `context is None` (`bd_proximity.py:_in_cell` → None
→ global fallback), so the wiring is consistent across every reputation variant. A
niche-specialist card (helpful in cell X, harmful elsewhere) is in principle judged on its
pooled record, but the only coherent context-aware alternative — bucket a card's own events by
their originating cell — is statistically inert at the current density (~1.85 events/card vs
`harm_min_events=3`): no per-cell bucket would clear the threshold. Decision: keep the global
`HarmEvictor` as the default; a context-aware evictor can be added later behind the `Evictor`
Protocol if event density ever rises. A no-op `NullEvictor` (`writer/evictor=none`) is
available now to run the write path with the harm sweep disabled.
