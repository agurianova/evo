#!/usr/bin/env bash
# Test evaluation script for HoVer dynamic-topology experiment.
#
# Evaluates the best-by-val program from each run on the held-out test set.
# Control runs (D1-D4) use static_soft test; treatment runs (D5-D8) use full test.
#
# Usage:
#   bash experiments/hover/dynamic-topology/run_test_eval.sh [--run D1|D2|...|all] [--n-repeats N]
#
# Requires HOVER_CHAIN_URL to be set (any valid Qwen3-8B endpoint).

set -euo pipefail

PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core

# Run-to-DB mapping and test module
declare -A RUN_DB=(
  [D1]=9  [D2]=10  [D3]=11  [D4]=12
  [D5]=13 [D6]=14  [D7]=15  [D8]=1
)

# Control runs use static_soft prefix; treatment runs use full prefix
declare -A RUN_PREFIX=(
  [D1]="chains/hover/static_soft"
  [D2]="chains/hover/static_soft"
  [D3]="chains/hover/static_soft"
  [D4]="chains/hover/static_soft"
  [D5]="chains/hover/full"
  [D6]="chains/hover/full"
  [D7]="chains/hover/full"
  [D8]="chains/hover/full"
)

# Control runs use static_soft test module; treatment runs use full test module
declare -A RUN_TEST_MODULE=(
  [D1]="problems.chains.hover.static_soft.test"
  [D2]="problems.chains.hover.static_soft.test"
  [D3]="problems.chains.hover.static_soft.test"
  [D4]="problems.chains.hover.static_soft.test"
  [D5]="problems.chains.hover.full.test"
  [D6]="problems.chains.hover.full.test"
  [D7]="problems.chains.hover.full.test"
  [D8]="problems.chains.hover.full.test"
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

ALL_RUNS=(D1 D2 D3 D4 D5 D6 D7 D8)

if [[ "$TARGET" == "all" ]]; then
  for label in "${ALL_RUNS[@]}"; do
    run_test "$label"
  done
else
  if [[ -z "${RUN_DB[$TARGET]+x}" ]]; then
    echo "ERROR: Unknown run '$TARGET'. Use D1-D8 or all."
    exit 1
  fi
  run_test "$TARGET"
fi
