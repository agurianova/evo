#!/usr/bin/env bash
# Test evaluation script for HoVer baseline experiment.
#
# Evaluates the best-by-val program from each run on the held-out test set.
# Run at gen 5, 12, and 25 checkpoints. Record results in 03_plan.md.
#
# Usage:
#   bash experiments/hover/baseline/run_test_eval.sh [--run H1|H2|H3|H4|all] [--n-repeats N]
#
# Requires HOVER_CHAIN_URL to be set (any valid Qwen3-8B endpoint).

set -euo pipefail

PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core

# Run-to-DB mapping
declare -A RUN_DB=(
  [H1]=9
  [H2]=10
  [H3]=11
  [H4]=12
)

# Parse arguments
TARGET="all"
N_REPEATS=5
while [[ $# -gt 0 ]]; do
  case "$1" in
    --run) TARGET="${2:-all}"; shift 2 ;;
    --n-repeats) N_REPEATS="${2:-3}"; shift 2 ;;
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
  local prefix="chains/hover/static"

  echo "=== Testing $label (redis.db=$db, prefix=$prefix, n_repeats=$N_REPEATS) ==="
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
  for label in H1 H2 H3 H4; do
    run_test "$label"
  done
else
  if [[ -z "${RUN_DB[$TARGET]+x}" ]]; then
    echo "ERROR: Unknown run '$TARGET'. Use H1, H2, H3, H4, or all."
    exit 1
  fi
  run_test "$TARGET"
fi
