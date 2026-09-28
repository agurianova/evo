# Memory-rebuild defect fix plan — 2026-07-04

Branch `refactor/memory-rebuild` (PR #294). Covers every defect from the four review/audit
agents (commit review 7B-*/0A-*, read-path audit, write-path audit, card-health audit) plus
my date-check. User authorized fixing while G1/G2 run.

## Live-run safety (why editing this worktree now is OK)

- G1/G2 mains imported the memory stack at launch (2026-07-04 11:47 UTC). **Empirical
  proof disk edits are invisible to them:** the founding-gain feature (`0aba53b1`) landed
  ~5h after launch and all four live banks contain **zero** founding events — the mains run
  the pre-founding code from memory.
- Research prompts are loaded in agent `__init__` (`storage/research.py:79,131`) — cached
  at launch; prompt-file edits don't reach live processes either.
- Config YAML resolves at launch — inert.
- **Sole contamination path: a G1/G2 restart** (watchdog or manual) would re-import
  everything and poison the A/B. Mitigation: no restarts of G runs until they finish
  (~19h to k≈220); if one dies, note it in `04_issues_log.md` and treat its arm as censored.

**Consequence:** the founding bugs (FIX-3/FIX-4) are *latent* — no live run has ever
exercised founding events. They must be fixed before the **next** launch, not to rescue
the current one.

## Defect → fix table

| # | ID | Sev | Live in G1/G2? | Fix in one line |
|---|----|-----|----------------|-----------------|
| 1 | GATE-DEFAULT (7B-2) | major/design | yes (the A/B variable) | flip `novelty_admission_gate: false` default — **DECIDED 2026-07-04: flip now** |
| 2 | GATE-LEDGER (7B-1) | major | yes (silent rejects) | new `REJECTED_NOVELTY` outcome + ledger row |
| 3 | FOUND-MERGE (0A-1) | major | latent | founding event rides **NEW admits only**; stripped on MERGE |
| 4 | FOUND-FREEZE | high | latent | founding-only card with non-positive median falls back to cold-borrow |
| 5 | NOISE-BAND | high | yes (strict sign live) | **DECIDED 2026-07-04: keep strict sign** (per user: a per-card MAD band was impossible to design properly for this case); document the semantics in code + docs, no silent fork |
| 6 | REFLECT-CRIT | med-high | yes | port anti-redundancy criteria into `retrieval_reflection`; delete dead `memory_selector` prompt |
| 7 | PLAN-CTX | med | yes (planner blind) | wire `ResearchRequest.planning_context` with a bank digest |
| 8 | CONSOL-SCOPE (7B-4) | med | yes | inline consolidation gets freshly-ADDED ids only |
| 9 | EVICT-CHURN (card audit) | med | yes (observed ping-pong) | harm-evicted program ids tombstoned; never re-authored in-run |
| 10 | TEXT-TWIN (card audit) | med | yes (3×/2× dup banks) | exact normalized-description twin → provenance bump, not new id |
| 11 | ORPHAN-CREDIT (card audit) | low | yes (8 events → ghost id) | restamp drops events whose id resolves to no banked card |
| 12 | MERGE-CONFLATE (card audit) | med | yes (~½ of merge survivors) | merge/arbiter prompts: same-mechanism-only, never merge a contradiction |
| 13 | TIMEOUT-ATTR (7B-3) | minor | yes | log which idea index the shared 300s ingest budget ran out on |
| 14 | DOCS (7B-5+) | minor | n/a | sync `gigaevo/memory/README.md` + `docs/memory.md` + tools with all of the above |

Explicit **no-change** decisions at the bottom.

---

## Fix details

### FIX-2 · GATE-LEDGER — novelty rejections must leave a ledger row
**Mechanism:** `librarian._admit_new` (librarian.py:192-198) returns `""` on `keep=False`
with only a log line. R1/R2 rejected 102/96 cards — >50% of idea authorship — with zero
audit trail; every bank-accounting pass has to grep logs.
**Fix:** add `WriteOutcome.REJECTED_NOVELTY`; add `CardAdmissionGate.reject_novelty(card,
reason) -> WriteResult` that records a ledger row (`final_id=""`) and returns a non-landed,
non-benign verdict; librarian calls it instead of bare `return ""`. `_land_dedup`'s
whitelist already handles it correctly (non-landed, non-DISCARDED → drop) — no change.
**Also:** `tools/analyze_bandit_health.py` outcome aggregation gains `rejected_novelty`.
**Tests (first):** reject → row with reason + `benign_noop is False` + truth-table test
extended to 7 members; judge fail-open → admit + no rejection row.
**Files:** `write/admission.py`, `write/librarian.py`, `tools/analyze_bandit_health.py`,
`tests/memory/write/test_admission.py`, `tests/memory/write/test_librarian.py`.

### FIX-3 · FOUND-MERGE — founding rides NEW admits only
**Mechanism:** on MERGE, the incoming card's founding event unions onto the target
(merge.py:70). The restamp path then credits the same parent→child delta as a *use* event —
numerically identical rows differing only in `founding=True`, so `_union_events`'
value-dedup can't collapse them → double-count. Worse: a *negative* founding event drags a
warm target's median magnitude down permanently.
**Fix:** in `ingest_idea`, the MERGE branch passes
`card.model_copy(update={"gain_events": ()})` to `gate.merge(...)` while `_land_dedup`
keeps the original card — so a benign-noop fallback re-authors WITH its founding event
(it genuinely becomes a new card), but a successful merge never imports birth evidence
the target didn't earn. DUPLICATE already drops it. Update the librarian docstring
(lines 79-81) and docs.
**Tests (first):** MERGE lands → target gains no founding event; MERGE benign-noop →
re-authored card keeps founding; DUPLICATE drop pinned (closes 0A-2 test gap).
**Files:** `write/librarian.py`, `tests/memory/write/test_librarian.py`, docs.

### FIX-4 · FOUND-FREEZE — birth evidence may demote, never permanently strand
**Mechanism:** most children are regressions → negative founding gain → magnitude =
median(all events) is negative, **not None** → cold-borrow (auction.py:219-235, fires only
on `magnitude is None`) skipped → bid < 0 ≤ `ev_floor` → never injected → never earns use
events → permanent zombie. Old stack gave cold cards optimistic `prior_magnitude: 0.1`.
**Fix (reputation.py:94 area):** magnitude = median of **use** events; if no use events,
magnitude = founding median **if > 0 else None** (→ cold-borrow path). Founding still
counts in the help/harm posterior, so a regression-born card bids *lower* (θ demoted) but
finite — explorable, and its first real injections resolve it. Docstring at auction.py:178
("the floor never strands them") becomes true again.
**Tests (first):** negative-founding-only card → magnitude None → borrowed magnitude →
positive bid; positive-founding-only card bids its own delta; warm card with use events
ignores founding in magnitude but not in posterior.
**Files:** `read/reputation.py`, `tests/memory/read/test_reputation.py`,
`tests/memory/read/test_auction.py`.

### FIX-5 · NOISE-BAND — RESOLVED: keep strict sign, document it
**Mechanism:** old scorer counted harm only when `gain < −ε`,
ε = `noise_band_k(1.0) × 1.4826 × MAD(gains)`; the rebuild silently switched to strict
sign (`gain < 0`) in `4b6e2e33`. Heilbron deltas are 1e-3-scale and noise-dominated →
strict sign inflates k_harm. (Card audit note: the observed evictions were −0.002…−0.010,
mostly beyond a plausible band — so the drift hasn't visibly mis-evicted yet.)
**Decision (user, 2026-07-04):** per our analysis a per-card MAD band was impossible to
design properly for this case — keep the strict sign test. Fix reduces to documentation:
a WHY note at the threshold definition (`read/reputation.py:31,47`) naming the deliberate
departure from the old MAD-band semantics, plus a line in `docs/memory.md`. No behaviour
change, no new tests.
**Files:** `read/reputation.py`, `docs/memory.md`.

### FIX-6 · REFLECT-CRIT — restore selection discipline in the reflector
**Mechanism:** old `memory_selector` prompt carried anti-redundancy criteria (mechanism-fit
w/ synonym tolerance, skip-if-parent-already-implements, strongest-lineage-signal,
mandatory empty hand); `retrieval_reflection` shipped without them. The card audit shows
the cost: quality-blind winners (a dtype FACTOID won 8 auctions; platitudes win alongside
the best mechanism cards).
**Fix:** port the criteria into `gigaevo/prompts/retrieval_reflection/system.txt`
(feasible — the reflector's request contains parent code via `build_research_query`,
shortlist.py:57-58). Delete the dead `memory_selector` prompt dir + its registry entry
(`gigaevo/prompts/__init__.py:124`).
**Tests:** prompt-content guard (criteria phrases present); registry no longer lists
memory_selector; existing research-agent tests stay green.
**Files:** `gigaevo/prompts/retrieval_reflection/system.txt`, `gigaevo/prompts/__init__.py`,
`tests/llm/`.
**Safety:** prompts are init-cached (research.py:131) — edit is inert to live runs.

### FIX-7 · PLAN-CTX — un-blind the planner
**Mechanism:** `ResearchRequest.planning_context` exists (storage/base.py:30) and is
consumed (`storage/research.py:238`), but shortlist.py:93 never populates it — the planner
writes search queries knowing nothing about what the bank holds (old GAM planner saw a
bank overview).
**Fix:** `ResearchShortlister` gains the store handle it already has; build a compact bank
digest from `store.snapshot()` — per-card one-liner (kind, keywords, description clipped),
capped (~2KB / ~40 cards, newest-first beyond the cap, drop-count logged) — and pass it as
`planning_context`.
**Tests (first):** request carries digest; empty bank → empty context; cap honored with a
logged drop count.
**Files:** `read/shortlist.py`, `tests/memory/read/test_shortlist.py`.

### FIX-8 · CONSOL-SCOPE — consolidate only what this batch actually added
**Mechanism:** the writer's inline consolidation pass receives `written_ids` that include
MERGE/DUPLICATE **target** ids (pre-existing cards), so old cards re-enter consolidation
each batch — compounding with cadence 64→32 this doubles arbiter exposure of the standing
bank and feeds MERGE-CONFLATE.
**Fix:** librarian returns per-card outcomes (it has each `WriteResult`); writer passes
only outcome==ADDED ids to the inline pass. Internal signature change within `write/` —
public `ingest_idea -> list[str]` callers keep the landed-ids view.
**Tests (first):** batch with NEW+MERGE+DUPLICATE → consolidation sees only the NEW id.
**Files:** `write/librarian.py`, `write/writer.py`, `tests/memory/write/`.

### FIX-9 · EVICT-CHURN — tombstone harm-evicted program exemplars
**Mechanism (observed):** G2 `program-ba73ac55` harm-evicted 16:39, re-authored fresh
17:37:36, re-evicted 17:37:44 (8s). Program cards are program-id-keyed and the extractor
happily re-authors an exemplar the gate just deleted for harm.
**Fix:** `CardAdmissionGate` keeps an in-memory tombstone set of harm-evicted/swept
**program** ids (`program-<id>`); `admit_program` (and the extraction seen-set) skips
tombstoned ids for the rest of the run. In-memory only — a restart re-learns after at most
one churn cycle; the ledger already records both events for audit.
**Tests (first):** evict exemplar → re-admit attempt is a no-op; insight cards unaffected.
**Files:** `write/admission.py` (or `write/extraction.py` seen-set — pick the single
narrowest seam at impl time), tests.

### FIX-10 · TEXT-TWIN — byte-identical descriptions must not mint new ids
**Mechanism (observed):** G1 banked one identical description under 3 ids, G2 under 2;
the twins split reputation and one twin got separately harm-evicted. The reconcile agent
is the only dedup arbiter and it misses exact repeats.
**Fix:** in `_admit_new`, before `gate.admit`: exact normalized-description twin scan over
insight snapshot (strip/casefold/whitespace-collapse — same *exact identity* philosophy as
`_code_key`, explicitly not a cosine gate) → on twin hit, `bump_provenance(twin.id, child)`
instead of a fresh admit; founding event is dropped with it (duplicate semantics).
**Tests (first):** identical description → no second id + provenance bump; near-identical
(one word) → still admitted (no fuzzy matching).
**Files:** `write/librarian.py`, `tests/memory/write/test_librarian.py`.

### FIX-11 · ORPHAN-CREDIT — restamps must resolve to a banked card
**Mechanism (observed):** `mem-33b55e262f48` was absorbed into a survivor that was then
evicted; restamps still credit it 8 use events every sweep — credit to a ghost id.
**Fix:** in `stats.stamp_gain_events`, resolve each credited id → banked card or a
survivor via `absorbed_ids`; unresolvable → drop the event with a debug log (once per id).
**Tests (first):** absorbed→survivor-evicted chain → no stamp, one log; absorbed→live
survivor still credited.
**Files:** `write/stats.py`, `tests/memory/write/test_stats.py`.

### FIX-12 · MERGE-CONFLATE — merges must preserve mechanism identity
**Mechanism (observed):** ~half of G-run merge survivors carry narrow labels over
mixed-mechanism evidence; one survivor absorbed its **direct opposite** ("structured init"
absorbed "uniform random instead of hand-designed layouts"). Reputation credit on those
survivors is semantically polluted.
**Fix (prompt-level):** reconcile MERGE decision rules + consolidation arbiter prompt gain:
MERGE only when both cards state the *same mechanism under the same condition*; a card
whose lever contradicts the target is NEVER a MERGE (keep both — coexisting contradiction
is honest, silent absorption is not); the surviving description must cover the union's
evidence or the merge is rejected. FIX-8 halves standing-bank arbiter exposure, which
compounds here.
**Tests:** prompt-content guard; reconcile schema unchanged.
**Files:** `gigaevo/prompts/reconcile/system.txt`, `gigaevo/prompts/consolidate_cards/…`,
prompt-guard tests.

### FIX-13 · TIMEOUT-ATTR — attribute the shared ingest timeout
**Fix:** when the shared 300s ingest budget expires mid-batch, log how many of N ideas were
processed and which index starved. No per-item timeout (keep it simple).
**Files:** `write/writer.py`. **Test:** fake slow librarian → log carries `i/N`.
**Re-scope (as implemented):** the timeout was already per-record (`ingest_call_timeout_s`
bounds each `ingest_idea` call, not the batch), so "which index starved" became: the timeout
log carries `i/N` plus a banked-count, and `ingest_idea` gained a `sink` that receives each
`WriteResult` the moment it is produced — a mid-ingest timeout still counts the cards already
routed through the gate (inline consolidation + cadence accounting stay correct) and the
timed-out record is forgotten for retry next sweep.

### FIX-14 · DOCS — canonical docs catch up in the same PR
`gigaevo/memory/README.md` + `docs/memory.md`: inline consolidation pass (currently
undocumented, README:55 / docs:78), founding-on-NEW-only + DUPLICATE/MERGE drop semantics,
`REJECTED_NOVELTY` in the ledger outcome table, noise-band decision, tombstones, text-twin
dedup, `admission_novelty` prompt listed in the right package table. `tools/README.md` if
`analyze_bandit_health` output columns change.

---

## Explicit no-changes (proposed)

- **Cold-borrow policy** (borrowed warm-median instead of old optimistic 0.1): deliberate
  design (no problem-dependent constants), and G1/G2 run at parity under it. Watch item,
  not a defect. FIX-4 restores the exploration path for the founding case specifically.
- **Consolidation cadence 64→32 + dropped eps-cut:** intentional in `7bafdf48`; FIX-8 +
  FIX-12 attack the actual observed harm (conflation). Revisit only if conflation persists.
- **SA program-card monoculture / prior-redundancy levels in G banks:** observations, not
  code defects; they're what the A/B is measuring.

## Sequencing

1. **Batch 1 — code fixes, start now** (order: 2 → 3 → 4 → 10 → 9 → 11 → 8 → 7 → 13, each
   test-first, `/run-tests` per feature, one commit per fix or tight pair, each commit
   held for approval).
2. **Batch 2 — prompt fixes (6, 12)** — safe now (init-cached), included after Batch 1.
3. **Batch 3 — decisions (RESOLVED 2026-07-04):** GATE-DEFAULT flips to `false` now;
   NOISE-BAND keeps strict sign with a documented rationale.
4. **Docs (14)** ride the last code commit. Push to PR #294 only on explicit go (push HELD
   standing).

## Predictions (next launch, per feedback_plans_need_causal_chain)

| Fix | Signal → behaviour → observable |
|---|---|
| 3+4 | founding events exist but never double-count; regression-born cards get injected ≥1× → zero permanent zombie cards (census: every card either has use events or was evicted/absorbed) |
| 2 | ledger accounting closes **including** novelty rejections without log greps |
| 9 | zero evict→re-author→re-evict loops in ledger |
| 10 | zero byte-identical description twins in bank |
| 11 | zero restamp credit to ids absent from bank∪absorbed |
| 12+8 | merge survivors' absorbed_ids mechanism-coherent on spot-check; standing-bank arbiter exposure per batch drops |
| 6 | FACTOID/platitude injection share drops vs G baseline (dtype-card-class wins ≈ 0) |

**Riskiest link:** FIX-4's asymmetric magnitude rule (founding>0 → own delta; ≤0 → borrow)
is a policy asymmetry — if it over-promotes regression-born cards the harm posterior must
catch them within `harm_min_events=3` injections. Bounded by design (θ is still demoted by
the founding harm count), but it's the one fix that changes selection behaviour rather than
just accounting.
