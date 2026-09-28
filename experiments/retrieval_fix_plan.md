# Retrieval (research agent) fix plan — post V1/V2

Causal chain: reflector sees truncated/label-level info → rejects or churns → injection 30% vs 78% → memory reads starve. Fixes below restore the funnel; injection-rate is the metric (target: back to ~75%+ non-empty selections), fitness stays the guardrail.

## P0 — correctness defects (small, surgical)

1. **Truncation livelock** (`storage/research.py`): CANDIDATES JSON clipped mid-array at 12,000 chars in 77–91% of reflect calls → reflector re-queries ids it already holds; `_retrieve` refuses re-adds → livelock.
   Fix: render candidates via compact `card_brief()` (no program code bodies) + raise cap; if still over, paginate briefs across steps instead of clipping mid-JSON. Prediction: continue-with-candidates truncation 99% → ~0; held-id re-queries (V1 191/356) → ~0.
2. **Budget-blind reflector** (`research.py:236–268`): nothing tells it a 3-step limit exists; step-3 `continue` forfeits everything (40% of V empties).
   Fix: on `step == max_iters`, append `[FINAL STEP] Retrieval budget exhausted: mode MUST be "final" — select the best-fitting CANDIDATES or an empty hand.` Also show `step k/3` every step.
3. **Held-card re-query black hole**: when the reflector requests an id already in hand, say so in the next observation (`already held: [ids]`) instead of silently dropping.

## P1 — the duplicate rule, graded (user-agreed direction)

4. **Rewrite FIX-6 criterion** (`prompts/retrieval_reflection/system.txt`): reject ONLY true duplicates — same mechanism AND no increment (parameters/structure/details) over the parent's actual code. Partial overlap → SELECT and state the delta. Program exemplars: compare at code level, never on strategy label. Prediction: slate-wide "0 of N" rejections (60% of V empties) drop to near-G levels while genuine copies still bounce.

## P2 — toward "SOTA RAG for ideas" (after P0/P1 measured, one at a time)

5. Cross-encoder rerank of top-k before the reflector (reuse NeighborSource seam; no hand-rolled cosine).
6. MMR/diversity in the shortlist + a novelty axis in card selection (known gap: selection is pure reliability pressure).
7. FIX-12 semantic-conflation spot-check (merge rate +3–5pp under stricter rule — verify merges are truly same-mechanism).

## Gate

- Tree FROZEN until V1/V2 stop (they import prompts+code live). Options: stop them now (past k=245; both closeout questions answered) or wait for 500-mutant natural end.
- Each fix lands with a targeted test where testable (truncation renderer, final-step injection); then a fresh V3/V4 pair re-runs the polish-check config to confirm injection recovery at unchanged-or-better fitness.
