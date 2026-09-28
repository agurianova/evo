# exp: heilbron/adversarial-repro-v1

**Status**: 🟢 Complete
**Branch**: `exp/heilbron/adversarial-repro-v1`

## Design

See `experiments/heilbron/adversarial-repro-v1/01_design.md` for full design.

## Runs

| Label | DB | Condition | Pipeline | PID |
|-------|----|-----------|----------|-----|
| A1_G | 1 | Arm A (Composition): Constructor, pair 1 | heilbron_repro_v1 | 2040531 |
| A1_D | 2 | Arm A (Composition): Improver, pair 1 | heilbron_repro_v1 | 2040532 |
| A2_G | 3 | Arm A (Composition): Constructor, pair 2 | heilbron_repro_v1 | 2040533 |
| A2_D | 4 | Arm A (Composition): Improver, pair 2 | heilbron_repro_v1 | 2040534 |
| C1_G | 5 | Arm C (Gradient-in-prompt): Constructor, pair 1 | heilbron_repro_v1 | 2040535 |
| C1_D | 6 | Arm C (Gradient-in-prompt): Improver, pair 1 | heilbron_repro_v1 | 2040536 |
| C2_G | 7 | Arm C (Gradient-in-prompt): Constructor, pair 2 | heilbron_repro_v1 | 2040537 |
| C2_D | 8 | Arm C (Gradient-in-prompt): Improver, pair 2 | heilbron_repro_v1 | 2040538 |

## Checkpoints

_No checkpoints yet._

## Baseline

Reference: `heilbron/asymmetric-iterations` (mean=0.03574, metric=actual_fitness (best-ever, 4 G runs))

## Archives

[GitHub Release](https://github.com/KhrulkovV/gigaevo-core-internal/releases/tag/exp/heilbron/adversarial-repro-v1)


