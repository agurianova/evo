#!/usr/bin/env bash
set -euo pipefail

export GIGAEVO_TABULAR_DATA="${GIGAEVO_TABULAR_DATA:-/home/jovyan/tabm-data/data}"

exec /home/jovyan/.mlspace/envs/evo_torch/bin/python \
  -m problems.tabular_dag_baselines.compare_matrix "$@"
