#!/usr/bin/env bash
# Launch one arm of the tool-aware DAG-diff A/B on HoVer full7 (CARL/JSON genome).
#   Arm A: mutation=llm_rewrite            — stock LLMMutationOperator, free-rewrite
#          of the whole wire-JSON chain (chain-flavored prompts under full7/prompts/mutation).
#   Arm B: mutation=carl_with_retrieval_tools — StructuredDiffMutationOperator +
#          AllowedToolChainChanges (schema-constrained positional-slot diffs, tool steps).
# Mutator LLM: google/gemini-3.5-flash via OpenRouter (llm=gemini35_flash).
# Chain executor: Qwen/Qwen3-8B via LiteLLM proxy 10.232.89.98:4000.
# Usage: ./launch_arm.sh A|B [max_mutants] [tag]
set -euo pipefail

ARM=$1
MUTANTS=${2:-250}
TAG=${3:-run}

PROJ=/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal
PY=/home/jovyan/.mlspace/envs/evo/bin/python3
RUN_DIR="$PROJ/experiments/carl_tool_chain_diff_ab/runs/arm${ARM}_${TAG}"
mkdir -p "$RUN_DIR/storage"

set -a; source /home/jovyan/gigaevo/.env; set +a

# Chain proxy (8B) must bypass Squid; OpenRouter (mutator) keeps Squid.
export NO_PROXY="localhost,127.0.0.1,10.232.89.98,10.232.30.185,${NO_PROXY:-}"
export no_proxy="$NO_PROXY"
export HOVER_CHAIN_URL="http://10.232.89.98:4000/v1"
export HOVER_CHAIN_MODEL="Qwen/Qwen3-8B"
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
# bm25s probes jax.lax.top_k on GPU at import; CPU-pin so retrieval evals never
# contend for GPU memory with concurrent JAX runs.
export JAX_PLATFORMS=cpu JAX_PLATFORM_NAME=cpu

MUTATION=llm_rewrite
if [ "$ARM" = "B" ]; then
  MUTATION=carl_with_retrieval_tools
fi

cd "$PROJ"
nohup "$PY" run.py \
  problem.name=chains/hover/full7 \
  pipeline=guided \
  program_format=json_document \
  mutation="$MUTATION" \
  llm=gemini35_flash \
  memory=none \
  num_parents=1 \
  storage=disk \
  program_storage.config.root_dir="$RUN_DIR/storage" \
  max_mutants="$MUTANTS" \
  max_tokens=60000 \
  stage_timeout=7200 \
  dag_timeout=14400 \
  > "$RUN_DIR/run.log" 2>&1 &

echo "arm=$ARM tag=$TAG mutants=$MUTANTS mutation=$MUTATION pid=$! log=$RUN_DIR/run.log"
