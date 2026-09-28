# exp: hover/prompt_coevolution

**Status**: 🟢 Complete
**Branch**: `exp/hover-prompt-coevolution`
**Tracking issue**: #94

## Design

See `experiments/hover/prompt_coevolution/01_design.md` for full design.

## Runs

| Label | DB | Condition | Pipeline | PID |
|-------|----|-----------|----------|-----|
| C1 | 9 | Treatment: soft fitness + co-evolved prompts | standard | 420175 |
| C2 | 10 | Treatment: soft fitness + co-evolved prompts | standard | 420176 |
| P1 | 11 | Prompt evolution run paired with C1 | prompt_evolution | 420177 |
| P2 | 12 | Prompt evolution run paired with C2 | prompt_evolution | 420178 |

## Checkpoints

| Gen | Time | Notes |
|-----|------|-------|
| 2 | 2026-03-21T10:36:52.877152+00:00 | Early checkpoint — all runs alive, C runs at 74-77%, P runs at prior (0.25). Too early for treatment checks. |
| 2 | 2026-03-21T13:25:51.514825+00:00 | Attempt 8 — freshly launched with min_trials=3. Too early for analysis. |
| 5 | 2026-03-21T16:59:43.710097+00:00 | All runs healthy. C1=79.2% C2=75.8% at gen 4-5. P1/P2=50% at gen 6-7, not stuck (3 distinct values). Diagnose.py false positives fixed. |
| 8 | 2026-03-21T18:16:10.183031+00:00 | All healthy. C1=79.2% gen6, C2=77.0% gen7. P1=57.1% gen10, P2=50.0% gen11. No CRITICAL/MAJOR findings. |
| 10 | 2026-03-21T19:37:05.508011+00:00 | C1 slow gen (86min gap, 61% invalid) — expected for this chain server. C2/P1/P2 healthy. No CRITICAL. |
| 6 | 2026-03-21T21:37:06.185532+00:00 | All runs healthy and synced. C1=75.7% gen5, C2=77.0% gen6. P1=40% gen6, P2=40% gen7. Feedback loop active (prompt_stats in C DBs). P fitness stagnation at 0.40 is expected — too few trials per prompt for differentiation. |
| 9 | 2026-03-21T23:36:35.242971+00:00 | C1=76.9% gen8, C2=77.6% gen9 — both improving. P1=33.3% gen9, P2=50.0% gen10 — synced. 0 CRITICAL. Val duration increasing (~1800-2400s) but within dag_timeout. |
| 12 | 2026-03-22T01:35:59.528378+00:00 | C1=76.9% gen11, C2=77.6% gen12. P1/P2 synced at gen12/13. C fitness plateauing — no improvement since gen5/gen4. Val durations 1500-2800s. Will run test eval at next checkpoint (>50%). |
| 15 | 2026-03-22T03:36:22.104090+00:00 | C1=76.9% gen14, C2=78.0% gen15 (C2 new high +0.4pp). P1/P2 synced gen14/16. 0 CRITICAL. Test eval deferred to closeout to avoid chain server contention. |
| 18 | 2026-03-22T05:36:11.642893+00:00 | C1=76.9% gen16, C2=78.0% gen19. P1 gen17, P2 gen20 — synced. C2 approaching completion (76%). C1 slower chain server (~3000s/gen). Fitness plateaued for both C runs. 0 CRITICAL. |
| 21 | 2026-03-22T07:36:08.399095+00:00 | C1=78.3% gen19 (new high, broke plateau), C2=78.0% gen22 (3 gens left). P1=57.1% gen20, P2=46.2% gen22. C2/P2 nearing completion. 0 CRITICAL. |
| 21 | 2026-03-22T07:39:44.291113+00:00 | C1=78.3% gen19 (still computing gen20), C2=78.0% gen22 (3 gens left), P2=gen23. C2/P2 approaching max_gen. Minimal change from last checkpoint — C1 chain server slow (~45min/gen). |
| 24 | 2026-03-22T11:04:33.352532+00:00 | C2+P2 complete (25/25). C1 at 23, P1 at 24. Waiting for completion before test eval. |
| 25 | 2026-03-22T13:47:38.960101+00:00 | Final checkpoint. Test eval: C1=52.93%, C2=51.07%. Verdict: NULL/REGRESSIVE. |

## Baseline

Reference: `hover/feedback_softfit` (mean=54.37, metric=test_retrieval_coverage_discrete)

## Archives

_(pending)_
