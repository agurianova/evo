#!/usr/bin/env bash
# Test evaluation script for hover/map-elites-topology.
#
# Evaluates the best-by-val program from each run on the held-out test set.
# Run at gen 10, 25, and max_gen checkpoints. Record results in 03_plan.md.
#
# Usage:
#   bash experiments/hover/map-elites-topology/run_test_eval.sh <db> <prefix> <label>
#
# Example:
#   bash experiments/hover/map-elites-topology/run_test_eval.sh 3 chains/hover/full V1

set -euo pipefail

PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
PROJ="${PROJ:-.}"

if [ $# -lt 3 ]; then
    echo "Usage: bash run_test_eval.sh <db> <prefix> <label>"
    echo "Example: bash run_test_eval.sh 3 chains/hover/full V1"
    exit 1
fi

DB="$1"
PREFIX="$2"
LABEL="$3"

LOG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="$LOG_DIR/test_eval_${LABEL}.log"

echo "================================" | tee "$OUTPUT_FILE"
echo "Test evaluation: $LABEL (DB=$DB, prefix=$PREFIX)" | tee -a "$OUTPUT_FILE"
echo "Test set: problems/chains/hover/full/test.py" | tee -a "$OUTPUT_FILE"
echo "Output: $OUTPUT_FILE" | tee -a "$OUTPUT_FILE"
echo "================================" | tee -a "$OUTPUT_FILE"

# TODO: Implement test set evaluation
# - Query Redis DB=$DB for frontier programs in $PREFIX
# - Load and execute each program on the test set (test.py)
# - Record metrics (accuracy, timing, etc.)
# - Compare to baseline if available
# For now, this is a placeholder for manual implementation after experiment runs.

echo "Test eval placeholder — implement after runs complete"
echo "Status: NOT IMPLEMENTED" | tee -a "$OUTPUT_FILE"
