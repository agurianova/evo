#!/usr/bin/env bash
# Latest memory rebuild run on tabular/higgs-small.
#
# Launches from this worktree so code/config resolve to refactor/memory-rebuild,
# while the requested shared bank lives under the canonical gigaevo root.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PYTHON="${GIGAEVO_PYTHON:-/home/jovyan/.mlspace/envs/evo/bin/python3}"

: "${OPENAI_API_KEY:?set OPENAI_API_KEY to the LiteLLM proxy key}"
export OPENAI_API_KEY

GIGAEVO_ROOT="${GIGAEVO_ROOT:-/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo}"
MEMORY_BANK="${MEMORY_BANK:-$GIGAEVO_ROOT/SHARE_TABULAR_MEMORY}"
PROXY_URL="${PROXY_URL:-http://10.232.24.68:4000/v1}"

TS="$(date +%Y%m%d_%H%M%S)"
OUT="${OUT:-$GIGAEVO_ROOT/outputs/memory-tabular-higgs-latest-$TS}"
LOG="${LOG:-$OUT.log}"

cd "$REPO"
mkdir -p "$MEMORY_BANK" "$(dirname "$OUT")"

export GIGAEVO_TABULAR_DATA="${GIGAEVO_TABULAR_DATA:-/home/jovyan/tabm-data/data}"
export GIGAEVO_TABULAR_CV_FOLDS="${GIGAEVO_TABULAR_CV_FOLDS:-3}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-8}"

NO_PROXY_HOSTS="10.232.24.68,10.232.91.196,10.232.28.121,10.232.47.140,10.232.33.122,10.232.30.185,10.232.24.83,localhost,127.0.0.1"
export NO_PROXY="$NO_PROXY_HOSTS${NO_PROXY:+,$NO_PROXY}"
export no_proxy="$NO_PROXY_HOSTS${no_proxy:+,$no_proxy}"

setsid "$PYTHON" run.py \
  storage=disk \
  model_name=Qwen3-235B-A22B-Thinking-2507 \
  llm_base_url="$PROXY_URL" \
  max_mutants="${MAX_MUTANTS:-800}" \
  num_parents=2 \
  problem.name=tabular/higgs-small \
  algorithm=tabular/2d_local_ood \
  pipeline=memory_guided \
  memory=full \
  memory/write=live \
  memory/llm=qwen_instruct \
  memory.llm.models.0.base_url="$PROXY_URL" \
  checkpoint_dir="$MEMORY_BANK" \
  hydra.run.dir="$OUT" \
  > "$LOG" 2>&1 < /dev/null &

PID=$!
echo "$PID" > "$OUT.pid"
echo "launched memory tabular/higgs-small"
echo "pid: $PID"
echo "worktree: $REPO"
echo "output: $OUT"
echo "log: $LOG"
echo "memory_bank: $MEMORY_BANK"
