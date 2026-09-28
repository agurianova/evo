#!/usr/bin/env bash
# Launch one arm of the CARL DAG-diff mutation A/B on the summarizer chain problem.
#   Arm A: stock LLMMutationOperator emitting complete wire-JSON (baseline, tracks failures)
#   Arm B: StructuredDiffMutationOperator emitting schema-constrained positional-slot diffs
# Mutation LLM: google/gemini-3.5-flash via OpenRouter (llm=gemini35_flash).
# Chain executor: Qwen/Qwen3-235B-A22B-Instruct-2507 via LiteLLM proxy 10.232.89.98:4000.
# Usage: ./launch_arm.sh A|B <max_mutants> <tag>
set -euo pipefail

ARM=$1
MUTANTS=$2
TAG=${3:-run}

REPO=/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal
PY=/home/jovyan/.mlspace/envs/evo/bin/python3
cd "$REPO"

set -a
source /home/jovyan/gigaevo/.env
set +a
export NO_PROXY="${NO_PROXY:-},10.232.89.98,localhost,127.0.0.1"
export no_proxy="$NO_PROXY"

RUN_DIR="$REPO/experiments/carl_dag_diff_ab/runs/arm${ARM}_${TAG}"
mkdir -p "$RUN_DIR"

EXTRA=()
if [ "$ARM" = "B" ]; then
  EXTRA+=(mutation=structured_diff_chains)
fi

nohup "$PY" run.py \
  problem.name=chains/summarizer \
  pipeline=guided \
  program_format=json_document \
  memory=none \
  llm=gemini35_flash \
  storage=disk \
  program_storage.config.root_dir="$RUN_DIR/storage" \
  max_tokens=60000 \
  max_mutants="$MUTANTS" \
  "${EXTRA[@]}" \
  > "$RUN_DIR/run.log" 2>&1 &

echo "arm=$ARM tag=$TAG mutants=$MUTANTS pid=$! log=$RUN_DIR/run.log"
