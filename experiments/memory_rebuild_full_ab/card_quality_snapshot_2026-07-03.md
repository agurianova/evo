# Card-quality snapshot — R1/R2 memory=full heilbron (~5.5h in, 2026-07-03)

Quality audit of the rebuilt MemoryWriter's output (PR #294). 3 subagents:
per-bank rubric (R1, R2) + cross-bank adversarial/redundancy read. Full reports:
`scratchpad/{R1_quality,R2_quality,cross_bank_quality}.md`.

Objective the cards must serve: Heilbronn(11) — maximize the MIN of C(11,3)=165
triangle areas in a unit-area equilateral triangle. Target ≥0.0365; runs at
0.01627 (R1) / 0.02181 (R2). Cards are injected into the LLM mutator.

## Scores (1–5)

| Bank | cards | specificity | actionability | correctness | **novelty** | distinct ideas |
|---|---|---|---|---|---|---|
| R1 | 14 | 3.6 | 4.1 | 3.6 | **2.5** | ~6 |
| R2 | 18 | 3.56 | 3.67 | 3.83 | **2.78** | ~6 |

Cross-bank overlap ≈ **65%** — two independent runs' writers converged on nearly
the same idea set. Union of distinct ideas ≈ 10–11 from 32 raw cards.

## Verdict: well-formed and actionable, but novelty-collapsed, paradigm-locked, weakly helpful

The rebuilt writer emits **structurally clean, mostly-correct, high-actionability
cards** — no malformed/garbage output, structured-output holding. But:

1. **Novelty collapse (2.5–2.8/5).** Banks fold to ~6 distinct ideas; ~4–6
   redundancy clusters each (SA cooling, grid init, boundary-clamp plumbing,
   perturbation-scale). Two program cards in R1 (`[12]==[14]`) are literal
   duplicates. Matches the pre-rebuild funnel finding (novelty ~2.4/5) — the
   rebuild did NOT add a novelty axis, so this is expected, not a regression.

2. **Missing the levers that actually move Heilbronn.** Absent entirely:
   (a) **3 corners + edge midpoints** (boundary/vertex occupancy);
   (b) **directly targeting the current min-area triplet** (bottleneck repair);
   (c) **mutual repulsion / max-min spreading** (Lloyd / potential energy),
   basin-hopping / random restarts. Banks over-index on init recipes +
   feasibility plumbing — i.e. polishing, not plateau-escape.

3. **A systemic ANTI-boundary bias that is WRONG for the task.** Multiple cards
   steer the mutator *away* from edges/vertices (R2 [9] "avoids apex or edge
   collapse", R2 [11] warns of "edge pile-up", R2 [2]/[5]/[13] forbid edge
   placement). Heilbronn optima **use** the boundary/vertices — this bias can
   actively cap fitness. Correctness concern, not just inertness.

4. **A few actively misleading cards** (reputation hasn't corrected them — all
   deltas 0, no learning signal yet):
   - **R1 `mem-0d1c899f1c8d`** — recommends collinear grid rows (→ min_area=0,
     its own sibling measured 0.00551 doing this) AND "uniform spatial
     dispersion" (optimizes AVERAGE spacing, not the MIN triangle). **This card
     is being SELECTED by the auction** (seen in R1 read-selection logs).
   - **R2 `mem-...[5]`** — invents an impossible float out-of-bounds failure.
   - **R1 `mem-...[4]`** — invented "equilateral domains prone to collinearities
     under Cartesian noise"; isotropic noise is directionless, the fix is a no-op.

5. **The one genuinely objective-aligned idea** — "switch the insertion
   criterion from min-DISTANCE to min-AREA" (R2 [3]/[10]) — exists **only in R2**.
   It correctly names why spread-based greedy leaves collinear triplets. This is
   the single best card in either bank and R1 never found it.

## Efficacy signal

All gain deltas are **0** in both banks; a handful of cards used once as donors
with no measurable effect; **no negative deltas** (nothing has hurt fitness yet).
Reputation is only barely off the prior — too early for the auction's learning to
down-weight the misleading cards.

## Implications for PR #294 sign-off

- Write path is functioning and producing clean, actionable cards — a genuine
  positive for the rebuild.
- But card *content* reproduces the known inert-memory failure mode: low novelty
  + missing the plateau-escape levers + a couple of wrong cards the auction is
  selecting. This is consistent with the A≈D parity thesis: the mechanism works,
  the cards just don't carry breakout information.
- Watch item: whether accruing gain events eventually let reputation demote
  `mem-0d1c899f1c8d` and the anti-boundary cluster. If it does not (deltas stay
  ~0 because these cards produce neutral, not negative, mutants), the auction has
  no lever to suppress them — a novelty/coverage problem, not a reputation one.
