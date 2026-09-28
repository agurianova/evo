#!/usr/bin/env bash
# Test evaluation script for HoVer feedback_softfit experiment.
#
# Evaluates the best-by-val program from each run on the held-out test set.
# ALL runs use DISCRETE test scoring (test.py from chains/hover/static).
#
# Usage:
#   bash experiments/hover/feedback_softfit/run_test_eval.sh [--run F1|F2|F3|F4|all] [--n-repeats N]
#
# Requires HOVER_CHAIN_URL to be set (any valid Qwen3-8B endpoint).

set -euo pipefail

PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core

# Run-to-DB and prefix mapping
# F1, F2 (Cell B): chains/hover/static (feedback pipeline, but test uses same test.py)
# F3, F4 (Cell C): chains/hover/static_soft (soft fitness, but test uses DISCRETE scoring)
declare -A RUN_DB=(
  [F1]=9
  [F2]=10
  [F3]=11
  [F4]=12
)
declare -A RUN_PREFIX=(
  [F1]="chains/hover/static"
  [F2]="chains/hover/static"
  [F3]="chains/hover/static_soft"
  [F4]="chains/hover/static_soft"
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

  # CRITICAL: ALL test evaluations use chains/hover/static/test.py (discrete scoring).
  # Cell C programs are stored under static_soft prefix but tested with discrete metric.
  echo "=== Testing $label (redis.db=$db, prefix=$prefix, n_repeats=$N_REPEATS) ==="
  echo "    Test script: problems.chains.hover.static.test (DISCRETE scoring)"
  cd "$PROJ"
  PYTHONPATH=. $PYTHON -m problems.chains.hover.static.test \
    --mode redis \
    --redis-db "$db" \
    --redis-prefix "$prefix" \
    --redis-host localhost \
    --redis-port 6379 \
    --n-repeats "$N_REPEATS"
  echo ""
}

if [[ "$TARGET" == "all" ]]; then
  for label in F1 F2 F3 F4; do
    run_test "$label"
  done
else
  if [[ -z "${RUN_DB[$TARGET]+x}" ]]; then
    echo "ERROR: Unknown run '$TARGET'. Use F1, F2, F3, F4, or all."
    exit 1
  fi
  run_test "$TARGET"
fi
