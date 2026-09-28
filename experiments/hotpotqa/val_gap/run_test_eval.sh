#!/usr/bin/env bash
# Run gen-50 final test evaluations for all 4 hotpotqa_val_gap runs.
#
# Pre-registration §Gen 50: extract best-by-val program from each run,
# evaluate on fixed 300-sample test set using EM, write results to
# experiments/hotpotqa_val_gap/test_evals/results.json.
#
# Run F: evaluate best-by-val-F1, report test EM (not test F1).
#
# Usage:
#   GIGAEVO_PYTHON=/home/jovyan/envs/evo_fast/bin/python \
#   bash experiments/hotpotqa_val_gap/run_test_eval.sh
#
# Prereqs: all 4 runs at gen 50 (or crashed/stalled at final gen).

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-/home/jovyan/envs/evo_fast/bin/python}
EVAL_SCRIPT="$PROJ/experiments/hotpotqa/thinking/gen10_test_eval.py"
RESULTS_PATH="$PROJ/experiments/hotpotqa/val_gap/test_evals/results.json"
LOG_DIR="$PROJ/experiments/hotpotqa/val_gap/test_evals"
mkdir -p "$LOG_DIR"

# Chain servers (same as launch.sh — one per run, to minimize server variance)
CHAIN_URL_O="http://10.226.17.25:8001/v1"
CHAIN_URL_R="http://10.226.17.25:8000/v1"
CHAIN_URL_Q="http://10.225.185.235:8001/v1"
CHAIN_URL_F="http://10.225.185.235:8000/v1"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"

echo "NO_PROXY=$NO_PROXY"
echo ""

# ── Preflight: thinking-mode verification ─────────────────────────────────────
echo "[preflight] Verifying thinking mode on all 4 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_O" "$CHAIN_URL_R" "$CHAIN_URL_Q" "$CHAIN_URL_F"; do
    HOST="${CHAIN_URL#http://}"; HOST="${HOST%%/*}"; HOST="${HOST%%:*}"
    RESPONSE=$(curl --noproxy "$HOST" -s --connect-timeout 10 --max-time 90 \
        -X POST "$CHAIN_URL/chat/completions" \
        -H "Authorization: Bearer None" \
        -H "Content-Type: application/json" \
        -d '{"model":"Qwen/Qwen3-8B","messages":[{"role":"user","content":"What is 2+2? Answer:"}],"max_tokens":200,"temperature":0.1}' \
        2>/dev/null || echo "CURL_FAIL")
    if echo "$RESPONSE" | grep -q "<think>"; then
        echo "[preflight] OK: $CHAIN_URL (thinking mode confirmed)"
    else
        echo "[preflight] FAIL: $CHAIN_URL NOT in thinking mode — aborting."
        exit 1
    fi
done
echo "[preflight] All chain endpoints verified."
echo ""

# ── Run O: control (fixed-300, EM) ────────────────────────────────────────────
echo "================================================================"
echo "[O] chains/hotpotqa/static  db=4  chain=$CHAIN_URL_O"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_O" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label O \
    --redis-db 4 \
    --redis-prefix chains/hotpotqa/static \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_O.log"
echo ""

# ── Run R: rotating-300 (EM) ──────────────────────────────────────────────────
echo "================================================================"
echo "[R] chains/hotpotqa/static_r  db=7  chain=$CHAIN_URL_R"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_R" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label R \
    --redis-db 7 \
    --redis-prefix chains/hotpotqa/static_r \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset hash_seeded_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_R.log"
echo ""

# ── Run Q: fixed-600 (EM) ─────────────────────────────────────────────────────
echo "================================================================"
echo "[Q] chains/hotpotqa/static_600  db=6  chain=$CHAIN_URL_Q"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_Q" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label Q \
    --redis-db 6 \
    --redis-prefix chains/hotpotqa/static_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_Q.log"
echo ""

# ── Run F: fixed-300 F1 fitness — test eval uses EM (cross-metric) ────────────
echo "================================================================"
echo "[F] chains/hotpotqa/static_f1  db=5  chain=$CHAIN_URL_F"
echo "NOTE: evolved under F1 fitness; evaluated here with EM (test metric)"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_F" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label F \
    --redis-db 5 \
    --redis-prefix chains/hotpotqa/static_f1 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_F.log"
echo ""

echo "================================================================"
echo "All test evals complete."
echo "Results: $RESULTS_PATH"
echo "Logs:    $LOG_DIR/test_eval_{O,R,Q,F}.log"
echo "Primary Gate C: Q vs O (test EM)"
echo "Primary Gate E: F vs O (test EM — Run F evolved under F1)"
echo "================================================================"
