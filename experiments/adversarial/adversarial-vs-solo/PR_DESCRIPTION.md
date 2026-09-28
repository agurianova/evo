# exp: adversarial/adversarial-vs-solo

**Status**: 🟢 Complete
**Branch**: `exp/adversarial/adversarial-vs-solo`


## Design

See `experiments/adversarial/adversarial-vs-solo/01_design.md` for full design.

## Runs

| Label | DB | Condition | Pipeline | PID |
|-------|----|-----------|----------|-----|
| S1 | 1 | Solo arm: replicate 1 | standard | 3174130 |
| S2 | 2 | Solo arm: replicate 2 | standard | 3174131 |
| S3 | 3 | Solo arm: replicate 3 | standard | 3174132 |
| S4 | 4 | Solo arm: replicate 4 | standard | 3174133 |

## Checkpoints

| Gen | Time | Notes |
|-----|------|-------|
| 21 | 2026-04-11T18:17:28.492975+00:00 |  |
| 41 | 2026-04-12T00:20:12.526781+00:00 | S3 completed (50/50). S4 stale 17 gens at 0.02828. S2 lag persists (gen 32). Analyst: bimodal outcome, R1/R3 near adversarial mean, R2/R4 below. Likely POSITIVE for adversarial. |
| 46 | 2026-04-12T03:16:51.860450+00:00 | S4 recovered from stagnation (0.02828->0.02872 at gen 45). S2 caught up to gen 42. S1 at 46, nearing completion. All active PIDs alive. |
| 50 | 2026-04-12T06:01:38.795467+00:00 | FINAL CHECKPOINT — all 4 runs completed at gen 50/50. Solo mean=0.03267 vs adversarial mean=0.03449 (-5.3%). Ready for closeout. |

## Baseline

Reference: `adversarial/heilbron-prover` (mean=0.03464, metric=actual_fitness)

## Archives

_(pending)_

