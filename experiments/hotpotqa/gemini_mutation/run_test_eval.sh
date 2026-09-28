#!/usr/bin/env bash
# Run final test evaluations for gemini_mutation runs V1 and V2.
# Amendment 1: BM25 retriever (static_f1_600 + hotpotqa_asi).
#
# Evaluates the best-by-val-EM program from each run on the fixed 300-sample test set.
# Note: evolution uses F1 fitness, but we select the best-by-val-EM program for test
# eval because val EM is the final reported metric and the two may differ.
# Run at gen 25. Record results in 03_plan.md.
#
# Usage:
#   GIGAEVO_PYTHON=/home/jovyan/envs/evo_fast/bin/python \
#   bash experiments/hotpotqa/gemini_mutation/run_test_eval.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-/home/jovyan/envs/evo_fast/bin/python}
export PYTHONPATH="$PROJ"
EVAL_SCRIPT="$PROJ/experiments/hotpotqa/thinking/gen10_test_eval.py"
RESULTS_PATH="$PROJ/experiments/hotpotqa/gemini_mutation/test_evals/results.json"
LOG_DIR="$PROJ/experiments/hotpotqa/gemini_mutation/test_evals"
mkdir -p "$LOG_DIR"

# Chain servers — same assignment as during training
CHAIN_URL_V1="http://10.226.17.25:8000/v1"
CHAIN_URL_V2="http://10.225.185.235:8000/v1"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"

echo "NO_PROXY=$NO_PROXY"
echo ""

# ── Preflight: thinking-mode verification ─────────────────────────────────────
echo "[preflight] Verifying thinking mode on chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_V1" "$CHAIN_URL_V2"; do
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

# ── Run V1: gemini-1  db=3 ───────────────────────────────────────────────────
echo "================================================================"
echo "[V1] chains/hotpotqa/static_f1_600  db=3  chain=$CHAIN_URL_V1"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_V1" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label V1 \
    --redis-db 3 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --select-by val_em \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_V1.log"
echo ""

# ── Run V2: gemini-2  db=4 ───────────────────────────────────────────────────
echo "================================================================"
echo "[V2] chains/hotpotqa/static_f1_600  db=4  chain=$CHAIN_URL_V2"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_V2" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label V2 \
    --redis-db 4 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --select-by val_em \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_V2.log"
echo ""

echo "================================================================"
echo "All test evals complete."
echo "Results: $RESULTS_PATH"
echo "Logs:    $LOG_DIR/test_eval_{V1,V2}.log"
echo ""
echo "Primary ref: cold_start 59.58% (BM25+F1+600, PR #75)"
echo "Verdict thresholds (vs. ref=59.58%):"
echo "  STRONG SIGNAL:   gemini_mean >= 63.58%"
echo "  POSITIVE SIGNAL: gemini_mean >= 61.58%"
echo "  INCONCLUSIVE:    gemini_mean in [57.58%, 61.58%)"
echo "  Spread guard:    if |V1-V2| > 4pp => cap at INCONCLUSIVE"
echo "================================================================"
