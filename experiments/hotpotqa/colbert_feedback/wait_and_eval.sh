#!/usr/bin/env bash
# Wait for U1 and U4 to finish, then run test evals for U1+U3+U4.
# Logs to experiments/hotpotqa/colbert_feedback/wait_and_eval.log

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
LOG="$PROJ/experiments/hotpotqa/colbert_feedback/wait_and_eval.log"
EVAL_SH="$PROJ/experiments/hotpotqa/colbert_feedback/run_test_eval.sh"

exec >> "$LOG" 2>&1

echo "============================================================"
echo "wait_and_eval.sh started at $(date -u '+%Y-%m-%dT%H:%M:%S UTC')"
echo "Waiting for PIDs 1676589 (U1) and 1676591 (U4) to exit..."

# Wait for U1
while kill -0 1676589 2>/dev/null; do
    sleep 30
done
echo "U1 (PID 1676589) exited at $(date -u '+%Y-%m-%dT%H:%M:%S UTC')"

# Wait for U4
while kill -0 1676591 2>/dev/null; do
    sleep 30
done
echo "U4 (PID 1676591) exited at $(date -u '+%Y-%m-%dT%H:%M:%S UTC')"

echo "Both runs complete. Running test evals..."
GIGAEVO_PYTHON=/home/jovyan/envs/evo_fast/bin/python \
    bash "$EVAL_SH" 2>&1

echo "Test evals complete at $(date -u '+%Y-%m-%dT%H:%M:%S UTC')"
echo "============================================================"
