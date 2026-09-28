#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)"

export PYTHONPATH="${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
export GIGAEVO_TABULAR_DATA="${GIGAEVO_TABULAR_DATA:-/home/jovyan/tabm-data/data}"
export GIGAEVO_TABM_ARCH_TYPE=tabm-mini
export GIGAEVO_TABM_K=32
export GIGAEVO_TABM_N_BLOCKS=3
export GIGAEVO_TABM_D_BLOCK=576
export GIGAEVO_TABM_DROPOUT=0.24050495351031098
export GIGAEVO_TABM_LEARNING_RATE=0.00029926241255995084
export GIGAEVO_TABM_WEIGHT_DECAY=0
export GIGAEVO_TABM_N_BINS=30
export GIGAEVO_TABM_D_EMBEDDING=16
export GIGAEVO_TABM_BATCH_SIZE=256
export GIGAEVO_TABM_EVAL_BATCH_SIZE=8192
export GIGAEVO_TABM_PATIENCE=16
export GIGAEVO_TABM_MAX_EPOCHS=512
export GIGAEVO_TABM_GRADIENT_CLIPPING_NORM=1
export GIGAEVO_TABM_AMP=true
export GIGAEVO_TABM_SHARE_TRAINING_BATCHES=false
export GIGAEVO_TABM_REFIT=true

exec /home/jovyan/.mlspace/envs/evo_torch/bin/python \
  -m problems.tabular_dag_baselines.compare_matrix "$@"
