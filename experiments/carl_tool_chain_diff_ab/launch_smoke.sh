#!/usr/bin/env bash
# Smoke: arm B (carl_with_retrieval_tools tool-aware DAG-diff) end-to-end on
# HoVer full7 in CARL/JSON genome format. Chain executor = Qwen3-235B-Instruct
# via the live proxy (10.232.89.98:4000); mutator = gemini-3.5-flash (OpenRouter).
# Goal: confirm valid diffs -> chain executes -> fitness computed. ~10 mutants.
set -euo pipefail

PROJ=/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal
PY=/home/jovyan/.mlspace/envs/evo/bin/python3
SMOKE="$PROJ/experiments/carl_tool_chain_diff_ab/runs/smoke_235b"
mkdir -p "$SMOKE/storage"

set -a; source /home/jovyan/gigaevo/.env; set +a

# Chain proxy (235B) must bypass Squid; OpenRouter (mutator) keeps Squid.
export NO_PROXY="localhost,127.0.0.1,10.232.89.98,10.232.30.185,${NO_PROXY:-}"
export no_proxy="$NO_PROXY"
export HOVER_CHAIN_URL="http://10.232.89.98:4000/v1"
export HOVER_CHAIN_MODEL="Qwen/Qwen3-235B-A22B-Instruct-2507"
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
# bm25s probes jax.lax.top_k on GPU at import; CPU-pin so retrieval evals never
# contend for GPU memory with concurrent JAX runs (e.g. heilbron).
export JAX_PLATFORMS=cpu JAX_PLATFORM_NAME=cpu

cd "$PROJ"
nohup "$PY" run.py \
  problem.name=chains/hover/full7 \
  pipeline=guided \
  program_format=json_document \
  mutation=carl_with_retrieval_tools \
  llm=gemini35_flash \
  memory=none \
  num_parents=1 \
  storage=disk \
  program_storage.config.root_dir="$SMOKE/storage" \
  max_mutants=10 \
  max_tokens=60000 \
  > "$SMOKE/run.log" 2>&1 &
echo "PID=$!"
echo "log: $SMOKE/run.log"
