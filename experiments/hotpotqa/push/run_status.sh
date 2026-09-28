#!/usr/bin/env bash
# Status monitor for push experiment (runs A/B/C/D)
# Usage: bash experiments/hotpotqa/push/run_status.sh
# Fill in PIDs after launch.

PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/status.py \
    --run chains/hotpotqa/static_f1@8:push-A \
    --run chains/hotpotqa/static_600@9:push-B \
    --run chains/hotpotqa/static_f1_600@10:push-C \
    --run chains/hotpotqa/static_f1_600@11:push-D \
    --pid L:3422378 \
    --pid L:3422379 \
    --pid L:3422380 \
    --pid L:3422381 \
    --watchdog 3499087
