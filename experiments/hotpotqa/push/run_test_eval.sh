#!/usr/bin/env bash
# Run final test evaluations for all 4 hotpotqa_push runs.
#
# All 4 runs evaluated on fixed 300-sample test set using EM.
# val_em and val_test_gap in results.json are correct for all runs:
# gen10_test_eval.py uses best.metrics.get("em", best.metrics["fitness"]),
# so F1 runs (A/C/D) report val EM (not val F1) as the val score.
#
# Usage:
#   GIGAEVO_PYTHON=/home/jovyan/envs/evo_fast/bin/python \
#   bash experiments/hotpotqa/push/run_test_eval.sh
#
# Prereqs: all 4 runs at max gen (A=50, B/C/D=25) or stalled/completed.

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-/home/jovyan/envs/evo_fast/bin/python}
export PYTHONPATH="$PROJ"
EVAL_SCRIPT="$PROJ/experiments/hotpotqa/thinking/gen10_test_eval.py"
RESULTS_PATH="$PROJ/experiments/hotpotqa/push/test_evals/results.json"
LOG_DIR="$PROJ/experiments/hotpotqa/push/test_evals"
mkdir -p "$LOG_DIR"

# Chain servers (same assignment as during training — minimise server variance)
CHAIN_URL_A="http://10.226.17.25:8001/v1"
CHAIN_URL_B="http://10.226.17.25:8000/v1"
CHAIN_URL_C="http://10.225.185.235:8001/v1"
CHAIN_URL_D="http://10.225.185.235:8000/v1"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"

echo "NO_PROXY=$NO_PROXY"
echo ""

# ── Preflight: thinking-mode verification ─────────────────────────────────────
echo "[preflight] Verifying thinking mode on all 4 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_A" "$CHAIN_URL_B" "$CHAIN_URL_C" "$CHAIN_URL_D"; do
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
echo "[preflight] All 4 chain endpoints verified."
echo ""

# ── Run A: F1+NLP+300 ─────────────────────────────────────────────────────────
echo "================================================================"
echo "[A] chains/hotpotqa/static_f1  db=8  chain=$CHAIN_URL_A"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_A" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label A \
    --redis-db 8 \
    --redis-prefix chains/hotpotqa/static_f1 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_A.log"
echo ""

# ── Run B: EM+default+600 ─────────────────────────────────────────────────────
echo "================================================================"
echo "[B] chains/hotpotqa/static_600  db=9  chain=$CHAIN_URL_B"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_B" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label B \
    --redis-db 9 \
    --redis-prefix chains/hotpotqa/static_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_B.log"
echo ""

# ── Run C: F1+default+600 [PRIMARY] ───────────────────────────────────────────
echo "================================================================"
echo "[C] chains/hotpotqa/static_f1_600  db=10  chain=$CHAIN_URL_C"
echo "PRIMARY TEST: H1 requires test_EM >= 62.3% (GEPA)."
echo "SUGGESTIVE:   test_EM in [61.7%, 62.3%) with val_EM gap < 1.5pp."
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_C" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label C \
    --redis-db 10 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_C.log"
echo ""

# ── Run D: F1+NLP+600 (Amendment 3) ──────────────────────────────────────────
echo "================================================================"
echo "[D] chains/hotpotqa/static_f1_600  db=11  chain=$CHAIN_URL_D"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_D" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label D \
    --redis-db 11 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_D.log"
echo ""

echo "================================================================"
echo "All test evals complete."
echo "Results: $RESULTS_PATH"
echo "Logs:    $LOG_DIR/test_eval_{A,B,C,D}.log"
echo ""
echo "Primary gate (Run C): test_EM >= 62.3% → H1 confirmed"
echo "  SUGGESTIVE: test_EM in [61.7%, 62.3%) with val_EM gap < 1.5pp"
echo "================================================================"
