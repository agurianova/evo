#!/usr/bin/env bash
# Test evaluation script for HoVer prompt_coevolution experiment.
#
# Evaluates the best-by-val program from each main run on the held-out test set.
# ALL test evaluations use DISCRETE scoring (test.py from chains/hover/static_soft).
# Prompt runs (P1, P2) have no test set — skip them.
#
# Usage:
#   bash experiments/hover/prompt_coevolution/run_test_eval.sh [--run C1|C2|all] [--n-repeats N]
#
# Requires HOVER_CHAIN_URL to be set (any valid Qwen3-8B endpoint).

set -euo pipefail

PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core

# Run-to-DB and prefix mapping (main runs only)
declare -A RUN_DB=(
  [C1]=9
  [C2]=10
)
declare -A RUN_PREFIX=(
  [C1]="chains/hover/static_soft"
  [C2]="chains/hover/static_soft"
)

# Parse arguments
TARGET="all"
N_REPEATS=5
while [[ $# -gt 0 ]]; do
  case "$1" in
    --run) TARGET="${2:-all}"; shift 2 ;;
    --n-repeats) N_REPEATS="${2:-5}"; shift 2 ;;
    *) TARGET="$1"; shift ;;
  esac
done

if [[ -z "${HOVER_CHAIN_URL:-}" ]]; then
  echo "ERROR: HOVER_CHAIN_URL not set. Export it first:"
  echo "  export HOVER_CHAIN_URL='http://10.226.17.25:8001/v1'"
  exit 1
fi

run_test() {
  local label=$1
  local db=${RUN_DB[$label]}
  local prefix=${RUN_PREFIX[$label]}

  # CRITICAL: ALL test evaluations use chains/hover/static_soft/test.py (discrete scoring).
  # test.py uses discrete_retrieval_eval regardless of evolutionary fitness metric.
  echo "=== Testing $label (redis.db=$db, prefix=$prefix, n_repeats=$N_REPEATS) ==="
  echo "    Test script: problems.chains.hover.static_soft.test (DISCRETE scoring)"
  cd "$PROJ"
  PYTHONPATH=. $PYTHON -m problems.chains.hover.static_soft.test \
    --mode redis \
    --redis-db "$db" \
    --redis-prefix "$prefix" \
    --redis-host localhost \
    --redis-port 6379 \
    --n-repeats "$N_REPEATS"
  echo ""
}

if [[ "$TARGET" == "all" ]]; then
  for label in C1 C2; do
    run_test "$label"
  done
else
  if [[ -z "${RUN_DB[$TARGET]+x}" ]]; then
    echo "ERROR: Unknown run '$TARGET'. Use C1, C2, or all."
    exit 1
  fi
  run_test "$TARGET"
fi
