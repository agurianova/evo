#!/usr/bin/env bash
# Test evaluation script for HoVer co-evolution bus experiment.
#
# Evaluates the best-by-val program from each run on the held-out test set.
# Runs B1, B2, B3 (main chains). PM (prompt meta-evolution) has no test eval.
#
# Usage:
#   bash experiments/hover/co-evolution-bus/run_test_eval.sh [--run B1|B2|B3|all] [--n-repeats N]
#
# Requires HOVER_CHAIN_URL to be set (any valid Qwen3-8B endpoint).

set -euo pipefail

PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core

# Run-to-DB mapping (B1=9, B2=10, B3=11; PM=12 has no test)
declare -A RUN_DB=(
  [B1]=9
  [B2]=10
  [B3]=11
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
  local prefix="chains/hover/static_soft"

  echo "=== Testing $label (redis.db=$db, prefix=$prefix, n_repeats=$N_REPEATS) ==="
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
  for label in B1 B2 B3; do
    run_test "$label"
  done
else
  if [[ -z "${RUN_DB[$TARGET]+x}" ]]; then
    echo "ERROR: Unknown run '$TARGET'. Use B1, B2, B3, or all."
    exit 1
  fi
  run_test "$TARGET"
fi
