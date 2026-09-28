#!/usr/bin/env bash
# Test evaluation script for HoVer memory experiment.
#
# Evaluates the best-by-val program from each run on the held-out test set.
# All runs use the same problem (full7_no_deep) — treatment adds memory=local.
#
# Usage:
#   bash experiments/hover/memory/run_test_eval.sh [--run R1|R2|...|all] [--n-repeats N]
#
# Uses LiteLLM proxy — set HOVER_CHAIN_URL if needed.

set -euo pipefail

PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
PROJ="$(cd "$(dirname "$0")/../../.." && pwd)"

export HOVER_CHAIN_URL="${HOVER_CHAIN_URL:-http://localhost:4000/v1}"

# Run-to-DB mapping
declare -A RUN_DB=(
  [R1]=4  [R2]=5  [R3]=6  [R4]=7
)

# All runs use the same prefix and test module
PREFIX="chains/hover/full7_no_deep"
TEST_MODULE="problems.chains.hover.full7_no_deep.test"

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

run_test() {
  local label=$1
  local db=${RUN_DB[$label]}

  echo "=== Testing $label (redis.db=$db, prefix=$PREFIX, module=$TEST_MODULE, n_repeats=$N_REPEATS) ==="
  cd "$PROJ"
  PYTHONPATH=. $PYTHON -m "$TEST_MODULE" \
    --mode redis \
    --redis-db "$db" \
    --redis-prefix "$PREFIX" \
    --redis-host localhost \
    --redis-port 6379 \
    --n-repeats "$N_REPEATS"
  echo ""
}

ALL_RUNS=(R1 R2 R3 R4)

if [[ "$TARGET" == "all" ]]; then
  for label in "${ALL_RUNS[@]}"; do
    run_test "$label"
  done
else
  if [[ -z "${RUN_DB[$TARGET]+x}" ]]; then
    echo "ERROR: Unknown run '$TARGET'. Use R1-R4 or all."
    exit 1
  fi
  run_test "$TARGET"
fi
