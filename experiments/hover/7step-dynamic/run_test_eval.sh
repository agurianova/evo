#!/usr/bin/env bash
# Test evaluation script for hover/7step-dynamic.
#
# Evaluates the best-by-val program from each run on the held-out test set.
# Control runs (V1/V2) use static_soft/test.py; treatment runs (V3/V4) use full7/test.py.
#
# Usage:
#   bash experiments/hover/7step-dynamic/run_test_eval.sh <db> <prefix> <label> <condition>
#
# Examples:
#   bash experiments/hover/7step-dynamic/run_test_eval.sh 3 chains/hover/static_soft V1 control
#   bash experiments/hover/7step-dynamic/run_test_eval.sh 5 chains/hover/full7 V3 treatment

set -euo pipefail

PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
PROJ="${PROJ:-.}"

if [ $# -lt 4 ]; then
    echo "Usage: bash run_test_eval.sh <db> <prefix> <label> <condition>"
    echo "  condition: 'control' uses static_soft/test.py, 'treatment' uses full7/test.py"
    exit 1
fi

DB="$1"
PREFIX="$2"
LABEL="$3"
CONDITION="$4"

LOG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="$LOG_DIR/test_eval_${LABEL}.log"

# Select test script based on condition
if [ "$CONDITION" = "control" ]; then
    TEST_SCRIPT="problems/chains/hover/static_soft/test.py"
else
    TEST_SCRIPT="problems/chains/hover/full7/test.py"
fi

echo "================================" | tee "$OUTPUT_FILE"
echo "Test evaluation: $LABEL (DB=$DB, prefix=$PREFIX, condition=$CONDITION)" | tee -a "$OUTPUT_FILE"
echo "Test set: $TEST_SCRIPT" | tee -a "$OUTPUT_FILE"
echo "Output: $OUTPUT_FILE" | tee -a "$OUTPUT_FILE"
echo "================================" | tee -a "$OUTPUT_FILE"

cd "$PROJ"
PYTHONPATH="$PROJ" "$PYTHON" "$TEST_SCRIPT" \
    --mode redis \
    --redis-db "$DB" \
    --redis-prefix "$PREFIX" \
    --n-repeats 5 \
    2>&1 | tee -a "$OUTPUT_FILE"

echo "" | tee -a "$OUTPUT_FILE"
echo "Test evaluation complete: $LABEL" | tee -a "$OUTPUT_FILE"
