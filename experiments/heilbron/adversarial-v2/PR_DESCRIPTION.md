# exp: heilbron/adversarial-v2

**Status**: 🟢 Complete
**Branch**: `exp/heilbron/adversarial-v2`
**Tracking issue**: #196

## Design

See `experiments/heilbron/adversarial-v2/01_design.md` for full design.

## Runs

| Label | DB | Condition | Pipeline | PID |
|-------|----|-----------|----------|-----|
| P1_A | 1 | K=3 Constructor (bidirectional feedback) | adversarial_coevo_feedback | 3395154 |
| P1_B | 2 | K=3 Improver (bidirectional feedback) | adversarial_coevo_feedback | 3395155 |
| P2_A | 3 | K=1 Constructor (bidirectional feedback) | adversarial_coevo_feedback | 3395156 |
| P2_B | 4 | K=1 Improver (bidirectional feedback) | adversarial_coevo_feedback | 3395157 |

## Checkpoints

| Gen | Time | Notes |
|-----|------|-------|
| 2 | 2026-04-08T18:45:44.736609+00:00 | Launch 5 checkpoint #3. All 5 sync bugs fixed and confirmed. No deadlocks. Sync hooks showing waited=0.0s. P2 advancing faster (K=1 less overhead). P1 stalled waiting for LLM timeouts — expected. |
| 4 | 2026-04-08T19:13:44.380195+00:00 |  |
| 4 | 2026-04-08T19:40:48.061537+00:00 | HEALTHY. All PIDs alive. Watchdog PID 3448119 alive. No invalidity issues. Diagnose: no critical/major findings. |
| 21 | 2026-04-09T00:38:50.612081+00:00 | HEALTHY. P1_A actual_fitness=0.03502 EXCEEDS v1 baseline (0.03462). K=3 pair ahead of K=1. Both Improvers stalled in frontier fitness. All PIDs alive. |
| 25 | 2026-04-09T03:36:17.043249+00:00 | HEALTHY. P1_A=0.03502, P1_B actual=0.03405 (improving). P2_A stalled at 0.03247, P2_B stalled. K=3 pair ahead. |
| 29 | 2026-04-09T06:40:46.207588+00:00 | All runs healthy. K=3 pair (P1) ahead of baseline. P1_A actual_fitness=0.03502 (best). K=1 pair (P2) stalled at 0.03247. No stopping rules triggered. ~38% through. |
| 33 | 2026-04-09T09:37:48.964135+00:00 | All runs healthy. P1_B (K=3 Improver) new best actual_fitness=0.03568. K=3 pair pulling ahead. K=1 pair stalled at 0.03247. diagnose.py dict-format bug fixed. ~44% through. Approaching 50% gate. |

## Baseline

Reference: `adversarial/heilbron-prover` (mean=0.03464, metric=actual_fitness)

## Archives

_(pending)_

