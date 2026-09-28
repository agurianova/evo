# Gate-OFF pair (G1/G2) — closeout: the novelty gate WAS the regression

**Date:** 2026-07-05. Sequel to `05_prior_memory_comparison.md` (which framed the test).
Runs: `outputs/memory_rebuild_full_nogate_2026-07-04/{G1,G2}` (disk storage, durable).
Launched 2026-07-04 11:47 UTC, SIGTERM'd 2026-07-05 ~00:35 UTC at 246/263 programs —
both past the k=245 comparison horizon.

## Setup

Byte-identical to the rebuild+novelty pair (`memory_rebuild_full_ab_novelty_2026-07-03`)
except `memory.writer.novelty_admission_gate=false`. Same harness as every arm in the
05 doc: heilbron, Qwen3-235B-A22B-Thinking-2507 mutator, qwen_instruct memory LLM,
`pipeline=intra_extra_memory`, `num_parents=2`, `storage=disk`. Remaining diffs vs the
PRE-refactor memfix dynamic arm: embedder (MiniLM-L6 → arctic-embed-m-v1.5) + store
architecture (shared_memory/GAM → LocalMemoryStore) ONLY.

## Result — cumulative-best by program count (method of the 05 doc, via `sweep.py`)

| arm | k=50 | k=100 | k=150 | k=200 | **k=220 (fair-end)** | k=245 |
|---|---|---|---|---|---|---|
| G1 (gate OFF) | 0.01545 | 0.02504 | 0.02801 | 0.02928 | 0.02928 | 0.02928 |
| G2 (gate OFF) | 0.02638 | 0.02638 | 0.02728 | 0.02762 | 0.02762 | 0.02762 |
| **gate-OFF mean** | **0.0209** | **0.0257** | **0.0276** | **0.0285** | **0.0285 ± 0.0012** | **0.0285** |
| memfix dynamic (PRE) | 0.0148 | 0.0256 | 0.0270 | 0.0276 | 0.0284 ± 0.0024 | 0.0293* |
| no-mem (PRE) | 0.0151 | 0.0242 | 0.0277 | 0.0288 | 0.0297 ± 0.0019 | 0.0307* |
| rebuild+gate (POST) | 0.0139 | 0.0196 | 0.0220 | 0.0233 | 0.0235 ± 0.0001 | 0.0247 |
| static tail (PRE) | 0.0180 | 0.0204 | 0.0211 | 0.0224 | 0.0224 ± 0.0004 | 0.0229 |

\* capped (≥1 PRE run ended before k=245). G2's terminal best 0.02839 first lands at
k=252, past the horizon.

## Verdict

1. **Gate-OFF reaches memfix parity at the fair-end: 0.0285 vs 0.0284 — and matches or
   beats memfix at every shared milestone (k=50…220).** The rebuild minus the gate
   reproduces the pre-refactor dynamic memory stack, full trajectory shape included.
2. **The novelty-admission gate is confirmed as the cause of the rebuild's
   detrimental-tail regime**: same code with gate ON sat at 0.0235 (below static-tail
   pack); gate OFF recovers +0.0049 at k=220. This closes the hypothesis raised in the
   05 doc §"Leading mechanistic hypothesis".
3. **Embedder (arctic-embed-m-v1.5) and LocalMemoryStore are exonerated** — they were
   the only remaining diffs vs memfix, and parity holds through them.
4. Gate-OFF still sits ~0.0012 below the no-mem bar (0.0297) at k=220 — within noise
   (memfix was −0.0013 below no-mem too). The rebuilt stack, like the old one, buys no
   fitness over no-mem; it just no longer *hurts*. The "memory ≥ no-mem" battle remains
   the card-quality problem (EVOTAB-A-33 verdict), not a plumbing one.

## Run health (from sweep.py; both runs)

Zero dag_errors / dag_build_failures. Cards flowed: G1 189/246 programs carried
injected cards (56 distinct), G2 209/263 (54 distinct). Banks: G1 56 cards
(21 insight/35 program), G2 44 (23/21). Consolidation, eviction, restamp all ran.

## Consequences

- `memory.writer.novelty_admission_gate=false` stays the shipped default (already the
  case since FIX-1; this pair is the empirical justification).
- Follow-up (V1/V2, `outputs/memory_rebuild_polishcheck_2026-07-05`): same config
  relaunched on the tree WITH the round-2/3 polish batch (13-commit series, PR #294,
  held) to confirm the polish did not break the recovered parity.
