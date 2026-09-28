#!/usr/bin/env bash
# Usage: bash experiments/hotpotqa/generalization/run_status.sh
# Shows live status for G1-G4 generalization runs.

PYTHON=/home/jovyan/envs/evo_fast/bin/python
PREFIX=chains/hotpotqa/static_holdout_f1

PYTHONPATH=. $PYTHON tools/status.py \
  --run "${PREFIX}@0:G1" \
  --run "${PREFIX}@1:G2" \
  --run "${PREFIX}@2:G3" \
  --run "${PREFIX}@3:G4" \
  --pid G1:2159756 \
  --pid G2:2159757 \
  --pid G3:2159758 \
  --pid G4:2159759 \
  --watchdog 2160086
