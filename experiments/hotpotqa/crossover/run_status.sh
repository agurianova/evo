#!/usr/bin/env bash
# Status monitor for crossover experiment (runs P/Q/R/S)
# Usage: bash experiments/hotpotqa/crossover/run_status.sh
# Fill in PIDs after launch.

PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/status.py \
    --run chains/hotpotqa/static_f1_600@0:cross-P \
    --run chains/hotpotqa/static_f1_600@1:cross-Q \
    --run chains/hotpotqa/static_f1_600@2:cross-R \
    --run chains/hotpotqa/static_f1_600@3:cross-S \
    --pid L:3660148 \
    --pid L:3660149 \
    --pid L:3660150 \
    --pid L:3660151 \
    --watchdog 3751512
