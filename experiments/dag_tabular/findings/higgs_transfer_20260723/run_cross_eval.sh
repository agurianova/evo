#!/usr/bin/env bash
set -euo pipefail

# Run from the repository root inside the isolated evo_torch environment.
export GIGAEVO_TABULAR_DATA=/home/jovyan/tabm-data/data
export GIGAEVO_TABULAR_DAG_GPU_DEVICES=0,1,2,3

# Exact Higgs-small TabM-mini + PLE recipe used during evolution.
export GIGAEVO_TABM_ARCH_TYPE=tabm-mini
export GIGAEVO_TABM_K=32
export GIGAEVO_TABM_N_BLOCKS=3
export GIGAEVO_TABM_D_BLOCK=816
export GIGAEVO_TABM_DROPOUT=0.4325268896304205
export GIGAEVO_TABM_LEARNING_RATE=0.0009498344265242885
export GIGAEVO_TABM_WEIGHT_DECAY=0
export GIGAEVO_TABM_N_BINS=7
export GIGAEVO_TABM_D_EMBEDDING=20
export GIGAEVO_TABM_BATCH_SIZE=512
export GIGAEVO_TABM_EVAL_BATCH_SIZE=32768
export GIGAEVO_TABM_PATIENCE=16
export GIGAEVO_TABM_MAX_EPOCHS=512
export GIGAEVO_TABM_GRADIENT_CLIPPING_NORM=1
export GIGAEVO_TABM_AMP=true
export GIGAEVO_TABM_SHARE_TRAINING_BATCHES=false
export GIGAEVO_TABM_REFIT=true

report_dir=experiments/dag_tabular/findings/higgs_transfer_20260723

/home/jovyan/.mlspace/envs/evo_torch/bin/python \
  -m problems.tabular_dag_baselines.compare_matrix \
  --graph raw="$report_dir/graphs/raw.json" \
  --graph catboost="$report_dir/graphs/catboost.json" \
  --graph tabm="$report_dir/graphs/tabm.json" \
  --evaluator catboost \
  --evaluator tabm \
  --seeds 0 1 2 3 4 \
  --workers 4 \
  --output "$report_dir/results/cross_eval.json"
