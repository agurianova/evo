# exp: heilbron/baseline-repro

**Status**: 🟢 Complete
**Branch**: `exp/heilbron/baseline-repro`
**Tracking issue**: #202

## Design

See `experiments/heilbron/baseline-repro/01_design.md` for full design.

## Runs

| Label | DB | Condition | Pipeline | PID |
|-------|----|-----------|----------|-----|
| P1_A | 1 | Pair 1: Constructor (replication) | adversarial_coevo | 1727166 |
| P1_B | 2 | Pair 1: Improver (replication) | adversarial_coevo | 1727167 |
| P2_A | 3 | Pair 2: Constructor (replication) | adversarial_coevo | 1727168 |
| P2_B | 4 | Pair 2: Improver (replication) | adversarial_coevo | 1727169 |
| P3_A | 5 | Pair 3: Constructor (replication) | adversarial_coevo | 1727170 |
| P3_B | 6 | Pair 3: Improver (replication) | adversarial_coevo | 1727171 |
| P4_A | 7 | Pair 4: Constructor (replication) | adversarial_coevo | 1727172 |
| P4_B | 8 | Pair 4: Improver (replication) | adversarial_coevo | 1727173 |

## Checkpoints

| Gen | Time | Notes |
|-----|------|-------|
| 12 | 2026-04-10T14:19:01.583725+00:00 | Gen ~7-15/50. All PIDs alive, 0% invalidity. Diagnose: HEALTHY. Pair 2 slower due to computationally expensive evolved programs (up to 2928s execution time). |
| 20 | 2026-04-10T18:10:08.648619+00:00 | Gen ~20/50 (40%). P3_A leading at gen 27. All PIDs alive. Actual fitness 0.027-0.031, below baseline 0.034 but expected at this stage. Diagnose pending. |
| 21 | 2026-04-10T18:24:33.318204+00:00 | gen ~25/50 (50-56%). Mean Constructor actual_fitness=0.03111 (REVISED band). All PIDs alive. mid-run checkpoint-analyst completed. Rising actual_fitness trend: Constructors trading raw quality for 100% resistance (expected). R3 stagnant (gen 12). No action needed. Analyst: CONFIRMED unlikely without trend reversal. |
| 28 | 2026-04-10T22:09:26.542703+00:00 | gen ~29/50. P3_A at 84% (gen 42), actual_fitness=0.03350 — above CONFIRMED threshold 0.033. All PIDs alive. No action needed. Diagnose HEALTHY (CRITICAL=false positive). P2_A still lagging (gen 16, computationally expensive programs). P3 pair likely first to complete gen 50. |
| 38 | 2026-04-11T06:15:45.818872+00:00 | gen ~38/50 (76%). P3 pair COMPLETE (gen 50). P3_A actual_fitness=0.03650 (CONFIRMED HIGH, above Q_MAX=0.0365). P4 at 88%, P1 at 76%, P2 at 48-50% (slow due to expensive programs). Mean Constructor actual_fitness=0.03293 (REVISED band). All PIDs alive. Diagnose HEALTHY (CRITICAL=false positive). No deviations. |
| 42 | 2026-04-11T10:08:35.784962+00:00 | gen ~42/50 (84%). P3 COMPLETE. P4 at 48/50 (96%, nearly done). P1 at 84%, P2 at 56% (slow). Mean Constructor actual_fitness=0.03337 (REVISED band, rising). P4_A actual_fitness=0.03023 still lagging. All PIDs alive. Diagnose HEALTHY. No deviations. |

## Baseline

Reference: `adversarial/heilbron-prover` (mean=0.03464, metric=actual_fitness)

## Archives

_(pending)_

