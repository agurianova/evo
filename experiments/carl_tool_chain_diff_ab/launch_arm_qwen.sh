#!/usr/bin/env bash
# Qwen-mutator copy of the tool-aware DAG-diff A/B on HoVer full7.
# Identical to launch_arm.sh EXCEPT the mutation LLM: Qwen3-235B-A22B-Thinking-2507
# served on the LiteLLM proxy (10.232.89.98:4000, alias_mutation → mutation-3/4/7),
# instead of google/gemini-3.5-flash via OpenRouter. Executor unchanged (Qwen3-8B).
#   Arm A: mutation=llm_rewrite               — free-rewrite of the whole wire-JSON chain.
#   Arm B: mutation=carl_with_retrieval_tools — StructuredDiffMutationOperator + AllowedToolChainChanges.
# Usage: ./launch_arm_qwen.sh A|B [max_mutants] [tag]
set -euo pipefail

ARM=$1
MUTANTS=${2:-250}
TAG=${3:-qwen}

PROJ=/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal
PY=/home/jovyan/.mlspace/envs/evo/bin/python3
RUN_DIR="$PROJ/experiments/carl_tool_chain_diff_ab/runs/arm${ARM}_${TAG}"
mkdir -p "$RUN_DIR/storage"

set -a; source /home/jovyan/gigaevo/.env; set +a

# Both mutator (235B) and executor (8B) hit the proxy at 10.232.89.98 → bypass Squid.
export NO_PROXY="localhost,127.0.0.1,10.232.89.98,10.232.30.185,${NO_PROXY:-}"
export no_proxy="$NO_PROXY"
export HOVER_CHAIN_URL="http://10.232.89.98:4000/v1"
export HOVER_CHAIN_MODEL="Qwen/Qwen3-8B"
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
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
  llm=single \
  model_name=Qwen3-235B-A22B-Thinking-2507 \
  llm_base_url=http://10.232.89.98:4000/v1 \
  memory=none \
  num_parents=1 \
  storage=disk \
  program_storage.config.root_dir="$RUN_DIR/storage" \
  max_mutants="$MUTANTS" \
  max_tokens=60000 \
  stage_timeout=7200 \
  dag_timeout=14400 \
  > "$RUN_DIR/run.log" 2>&1 &

echo "arm=$ARM tag=$TAG mutants=$MUTANTS mutation=$MUTATION mutator=Qwen3-235B-Thinking pid=$! log=$RUN_DIR/run.log"
