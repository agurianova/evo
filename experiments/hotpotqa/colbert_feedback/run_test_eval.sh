#!/usr/bin/env bash
# Run final test evaluations for colbert_feedback runs U1, U3, U4.
# (U2 was dropped in Amendment 4 — GPU node reserved for ColBERT server.)
#
# Evaluates the best-by-val program from each run on the fixed 300-sample test set.
# Record results in 03_plan.md.
#
# IMPORTANT: Uses problem variant static_colbert_f1_600 (ColBERT retriever).
# Do NOT use static_f1_600 or any BM25 variant — that would silently evaluate
# a ColBERT-evolved program under BM25 retrieval, invalidating test EM results.
#
# DB assignments (Amendment 4):
#   U1 = DB 0, chain = 10.226.17.25:8001
#   U3 = DB 1, chain = 10.225.185.235:8001
#   U4 = DB 2, chain = 10.225.185.235:8000
#
# Usage:
#   GIGAEVO_PYTHON=/home/jovyan/envs/evo_fast/bin/python \
#   bash experiments/hotpotqa/colbert_feedback/run_test_eval.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-/home/jovyan/envs/evo_fast/bin/python}
export PYTHONPATH="$PROJ"
EVAL_SCRIPT="$PROJ/experiments/hotpotqa/thinking/gen10_test_eval.py"
RESULTS_PATH="$PROJ/experiments/hotpotqa/colbert_feedback/test_evals/results.json"
LOG_DIR="$PROJ/experiments/hotpotqa/colbert_feedback/test_evals"
mkdir -p "$LOG_DIR"

# Chain servers — same as Amendment 4 launch
CHAIN_URL_U1="http://10.226.17.25:8001/v1"
CHAIN_URL_U3="http://10.225.185.235:8001/v1"
CHAIN_URL_U4="http://10.225.185.235:8000/v1"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"
export HOTPOTQA_COLBERT_SERVER_URL="http://127.0.0.1:8889"

echo "NO_PROXY=$NO_PROXY"
echo ""

# ── Preflight: thinking-mode verification ─────────────────────────────────────
echo "[preflight] Verifying thinking mode on U1/U3/U4 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_U1" "$CHAIN_URL_U3" "$CHAIN_URL_U4"; do
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
echo "[preflight] All 3 chain endpoints verified."
echo ""

# ── Run U1: colbert-1  db=0 ──────────────────────────────────────────────────
echo "================================================================"
echo "[U1] chains/hotpotqa/static_colbert_f1_600  db=0  chain=$CHAIN_URL_U1"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_U1" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label U1 \
    --redis-db 0 \
    --redis-prefix chains/hotpotqa/static_colbert_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_U1.log"
echo ""

# ── Run U3: colbert-3  db=1 (Amendment 4: was db=2) ─────────────────────────
echo "================================================================"
echo "[U3] chains/hotpotqa/static_colbert_f1_600  db=1  chain=$CHAIN_URL_U3"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_U3" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label U3 \
    --redis-db 1 \
    --redis-prefix chains/hotpotqa/static_colbert_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_U3.log"
echo ""

# ── Run U4: colbert-4  db=2 (Amendment 4: was db=3) ─────────────────────────
echo "================================================================"
echo "[U4] chains/hotpotqa/static_colbert_f1_600  db=2  chain=$CHAIN_URL_U4"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_U4" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label U4 \
    --redis-db 2 \
    --redis-prefix chains/hotpotqa/static_colbert_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_U4.log"
echo ""

echo "================================================================"
echo "All test evals complete. (U2 excluded — Amendment 4)"
echo "Results: $RESULTS_PATH"
echo "Logs:    $LOG_DIR/test_eval_{U1,U3,U4}.log"
echo ""
echo "Success gate (n=3, df=2): one-sample t-test p < 0.05 AND mean >= 62.00%"
echo "STRONG POSITIVE: mean >= 62.3% (GEPA)"
echo "================================================================"
