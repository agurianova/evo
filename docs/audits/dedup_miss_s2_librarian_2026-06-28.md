# Dedup miss: two `librarian-authored` cards from one lever (S2, 2026-06-28)

**Trigger:** the merge-smoke health monitor flagged `duplicate_description` in S2 — two
cards displayed byte-identical descriptions. This is the root-cause dig.

**Verdict:** a **real, pre-existing online-dedup gap**, orthogonal to the
`feat/livememory-refresh-resilience` branch (`refresh_failed=0` throughout; the bank
is never wiped between refreshes — see §4). The collision was **transient**: both cards
kept merging and have since diverged, so the live S2 bank currently holds **0**
byte-identical pairs. The mechanism that let them both enter, however, is structural.

## 1. The two cards (S2 `write_ledger.jsonl`, 153 rows)

| | id | entered | description at birth | live now | programs |
|---|---|---|---|---|---|
| A | `mem-e03a8f1d9c0c` | #33 `added` | "Scale random perturbations by the current **temperature**…" | "…by the current **minimum inter-point distance**…" | 12 |
| B | `mem-f5f6262c112f` | #116 `added` | "Scale random perturbations by the current **temperature**…" | "Adapt the minimum inter-point distance **threshold to the optimizer's temperature**…" | 2 |

Both entered the gate as `librarian-authored card` (i.e. `ReconcileAgent` decision
`NEW` → `CardAdmissionGate.admit`). Ledger order is the key fact:

```
#33  A added            #46  A merged   #56  A merged     <- A's desc already drifted
#116 B added (NEW)      #119 A merged   #129 A merged  #133 A merged
#140 B merged
```

A was merged **twice (#46, #56) before B was even authored (#116)**, and merges use
`replace_description=True`. So A's *live* description had already moved off its #33
original by the time B arrived.

## 2. Why both entered as NEW — the two structural gaps

### G1 — the pre-gate dedup is query/index **asymmetric** (cross-domain compare)

`Librarian.ingest_idea` (`gigaevo/memory/ideas_tracker/librarian.py:71`) retrieves
neighbors with `neighbors.nearest(note, …)` where `note` is the **raw mutation note**
(pre-authoring). But the Chroma index stores each card's **authored card document** —
`document_for_note` →`_build_gam_card_text` (`_vendor/A_mem/.../memory_system.py:194`)
embeds `"description: {card.description}\ntask_description: …\ncategory: …\n…"`, i.e.
the LLM-**authored** prose.

So the near-dup short-circuit (`hits[0][1] <= eps`, `eps=0.05`,
`librarian.py:80`) compares **embed(raw note)** vs **embed(authored card doc)** — a
cross-domain comparison. Two ideas the LLM will author into the *same* description can
have raw notes far apart in embedding space, so neither pulls the other within `eps`,
and one may not even surface in the other's top-k for the `ReconcileAgent`. The online
path therefore **cannot** catch a post-authoring description collision — by construction.
(This is the "greedy, order-dependent" miss the consolidation docstring already admits.)

### G2 — there is no post-authoring re-check on the admit path

Inside `ReconcileAgent.arun` the LLM *authors the description and decides NEW/DUP/MERGE
in one shot*. Once it says `NEW`, `gate.admit(card)` (`librarian.py:121`) saves the
authored card with **zero comparison against the bank's existing descriptions**. So a
post-authoring collision is invisible to the online path.

The only description-vs-description dedup is the **consolidation sweep**
(`consolidation.py`), which *is* symmetric — it queries `nearest(card.description, …)`
with a looser `eps=0.2`. But it is the backstop, not the gate, and it failed here for a
second-order reason (§3).

## 3. Why the consolidation backstop also missed it

Consolidation ran **once** in S2 and merged **0** (`memory_events.jsonl`:
`consolidation.pass {'merged': 0}`; cadence `every_n=64`). It races description drift:

- The sweep surfaces a merge candidate only if the *current* descriptions of two live
  cards are within `eps=0.2` **at sweep time**.
- A and B were near-identical only briefly at B's birth (#116). By the time the single
  pass fired, A had merged again (#119/#129/#133) and B at #140 — their descriptions had
  drifted apart past `eps`. No candidate pair surfaced; the arbiter never saw them.

So the intended fix (consolidation) is defeated by the very merge-driven drift that
masks the duplicate: identical-at-birth → divergent-by-sweep.

## 4. Ruled out: LiveMemoryRefresh rebuild artifact

The hook calls `tracker.run_increment(window)` (`live_memory_hook.py:115`) — an
**incremental** ingest of newly-landed programs into the existing bank, never a
clear/rebuild. The append-only ledger is one monotonic sequence with A's and B's rows
interleaved, confirming a single continuous bank and dedup view. The miss is **not** a
"two adds in two different rebuilds" artifact.

## 5. Proposed tightening (MVP — closes G2 on the existing seam)

G1 is inherent to authoring-after-retrieval and cannot be closed without re-embedding
the note as a card first. G2 is the cheap, decisive close:

> **Post-authoring near-dup re-query before `admit` on a `NEW` decision.** After the
> `ReconcileAgent` authors a `NEW` card, run one more `neighbors.nearest(card.description,
> k, MemoryCard)` — **symmetric** (authored description vs indexed card docs), reusing the
> existing `NeighborSource` primitive and `eps`. If the authored description lands within
> `eps` of a live card, downgrade `NEW → DUPLICATE`: `gate.bump_provenance(hit.id,
> child_id)` instead of admitting a twin.

Why this fits:

- **Reuses the seam** (`NeighborSource.nearest` + `gate.bump_provenance`) — no new
  abstraction, no hand-rolled cosine.
- **Symmetric** — it compares on the same description axis the consolidation sweep
  already trusts, so it catches exactly the collision the asymmetric pre-gate cannot.
- **LLM-respecting** — the `ReconcileAgent` still authors; we only re-check its authored
  output against the bank before banking it as a new card.
- **No race** — it runs at admit time, before any interleaved merge can drift either
  side, closing the window that defeats consolidation.
- At admit time the new card is not yet indexed, so the re-query returns only existing
  cards (no self-hit).

Heavier alternatives (not recommended for MVP): a stricter consolidation cadence, or
recall on a drift-stable key rather than current description — both add machinery to fix
a window the admit-time re-query closes directly.

## 6. Status

**IMPLEMENTED 2026-06-28** (codex consulted first → SOUND-WITH-CHANGES). The §5 fix
landed in `gigaevo/memory/ideas_tracker/librarian.py`: `_admit_or_bump_authored` runs a
symmetric `nearest(card.description, top_k, MemoryCard)` before admitting a `NEW` card and
downgrades to `bump_provenance` on a hit within `self._eps` (the tight online 0.05, **not**
consolidation's 0.2), falling back to `admit` on a no-op bump or retrieval failure.

Codex-driven refinements vs the original §5 sketch:
- eps = online 0.05 (silent auto-bump axis), not consolidation 0.2 (LLM-arbiter recall axis).
- downgrade is `bump_provenance`, never `merge` — a hard merge would overwrite prose via
  `replace_description=True` with no LLM union decision, and the agent already said NEW.
- the NEW branch carries its **own** admit fallback; the pre-existing
  `if not fid and item.decision != "NEW"` fallback does not cover it.
- no self-hit guard needed: the just-authored card is id-less and unindexed at re-query
  time (admit syncs it afterward) — confirmed in `admission_gate.py:51` → `memory.py` sync.
- intra-batch twins handled for free: the first NEW admits+syncs before the second item's
  re-query, so the second sees it.

TDD: 6 new tests in `tests/memory/test_librarian.py` (RED→GREEN), 2 mutants killed
(eps 0.05→0.2 and bump-disabled), full `tests/memory/` suite green, ruff clean. Commit
held for approval.
