#!/usr/bin/env bash
# Quick status check for hotpotqa_val_gap runs.
# Usage: bash experiments/hotpotqa/val_gap/run_status.sh
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/status.py \
    --run chains/hotpotqa/static@4:O \
    --run chains/hotpotqa/static_r@7:R \
    --run chains/hotpotqa/static_600@6:Q \
    --run chains/hotpotqa/static_f1@5:F \
    --pid O:3054746 --pid R:3054747 --pid Q:3054748 --pid F:3054749 \
    --watchdog 3057704
