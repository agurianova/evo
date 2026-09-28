#!/usr/bin/env bash
# Status check for cold_start experiment (T1-T4).
# Fill in PIDs after launch.sh completes.

PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/status.py \
    --run chains/hotpotqa/static_f1_600@0:cold-T1 \
    --run chains/hotpotqa/static_f1_600@1:cold-T2 \
    --run chains/hotpotqa/static_f1_600@2:cold-T3 \
    --run chains/hotpotqa/static_f1_600@3:cold-T4 \
    --pid L:3812756 \
    --pid L:3812757 \
    --pid L:3812758 \
    --pid L:3812759 \
    --watchdog 3813084
