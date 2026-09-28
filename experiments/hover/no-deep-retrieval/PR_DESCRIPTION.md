# exp: hover/no-deep-retrieval

**Status**: 🟢 Complete
**Branch**: `exp/hover-no-deep-retrieval`


## Design

See `experiments/hover/no-deep-retrieval/01_design.md` for full design.

## Runs

| Label | DB | Condition | Pipeline | PID |
|-------|----|-----------|----------|-----|
| R1 | 3 | treatment-static | standard | 463835 |
| R2 | 4 | control-static | standard | 463836 |
| R3 | 5 | treatment-dynamic | structural_metrics | 463837 |
| R4 | 6 | control-dynamic | structural_metrics | 463838 |

## Checkpoints

_No checkpoints yet._

## Baseline

Reference: `hover/baseline` (mean=51.65, metric=test_discrete_retrieval_coverage)

## Archives

_(pending)_

