#!/usr/bin/env bash
# Test evaluation script for HoVer no-deep-retrieval experiment.
#
# Evaluates the best-by-val program from each run on the held-out test set.
# Treatment runs (R1, R3) use no_deep test modules; control runs (R2, R4) use standard.
#
# Usage:
#   bash experiments/hover/no-deep-retrieval/run_test_eval.sh [--run R1|R2|...|all] [--n-repeats N]
#
# Uses LiteLLM proxy — set HOVER_CHAIN_URL if needed.

set -euo pipefail

PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
PROJ="$(cd "$(dirname "$0")/../../.." && pwd)"

export HOVER_CHAIN_URL="${HOVER_CHAIN_URL:-http://10.232.30.185:4000/v1}"

# Run-to-DB mapping
declare -A RUN_DB=(
  [R1]=3  [R2]=4  [R3]=5  [R4]=6
)

# Run prefixes (must match Redis)
declare -A RUN_PREFIX=(
  [R1]="chains/hover/static_soft_no_deep"
  [R2]="chains/hover/static_soft"
  [R3]="chains/hover/full_no_deep"
  [R4]="chains/hover/full"
)

# Test modules per run
declare -A RUN_TEST_MODULE=(
  [R1]="problems.chains.hover.static_soft_no_deep.test"
  [R2]="problems.chains.hover.static_soft.test"
  [R3]="problems.chains.hover.full_no_deep.test"
  [R4]="problems.chains.hover.full.test"
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

run_test() {
  local label=$1
  local db=${RUN_DB[$label]}
  local prefix=${RUN_PREFIX[$label]}
  local test_module=${RUN_TEST_MODULE[$label]}

  echo "=== Testing $label (redis.db=$db, prefix=$prefix, module=$test_module, n_repeats=$N_REPEATS) ==="
  cd "$PROJ"
  PYTHONPATH=. $PYTHON -m "$test_module" \
    --mode redis \
    --redis-db "$db" \
    --redis-prefix "$prefix" \
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
