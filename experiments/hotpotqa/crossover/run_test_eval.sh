#!/usr/bin/env bash
# Run final test evaluations for all 4 crossover runs (P/Q/R/S).
#
# All runs: chains/hotpotqa/static_f1_600, evaluated on fixed 300-sample test set.
# Chain URL assignment matches training (minimise server variance).
#
# Usage:
#   GIGAEVO_PYTHON=/home/jovyan/envs/evo_fast/bin/python \
#   bash experiments/hotpotqa/crossover/run_test_eval.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-/home/jovyan/envs/evo_fast/bin/python}
export PYTHONPATH="$PROJ"
EVAL_SCRIPT="$PROJ/experiments/hotpotqa/thinking/gen10_test_eval.py"
RESULTS_PATH="$PROJ/experiments/hotpotqa/crossover/test_evals/results.json"
LOG_DIR="$PROJ/experiments/hotpotqa/crossover/test_evals"
mkdir -p "$LOG_DIR"

# Chain servers — same as training assignment
CHAIN_URL_P="http://10.226.17.25:8001/v1"
CHAIN_URL_Q="http://10.226.17.25:8000/v1"
CHAIN_URL_R="http://10.225.185.235:8001/v1"
CHAIN_URL_S="http://10.225.185.235:8000/v1"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"

echo "NO_PROXY=$NO_PROXY"
echo ""

# ── Preflight: thinking-mode verification ─────────────────────────────────────
echo "[preflight] Verifying thinking mode on all 4 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_P" "$CHAIN_URL_Q" "$CHAIN_URL_R" "$CHAIN_URL_S"; do
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

# ── Run P: F1+NLP+600, num_parents=1 [REPLICATION] ───────────────────────────
echo "================================================================"
echo "[P] chains/hotpotqa/static_f1_600  db=0  chain=$CHAIN_URL_P"
echo "PRIMARY: Replication of Run D (63.00%). H1: test_EM >= 62.3% (GEPA)."
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_P" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label P \
    --redis-db 0 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_P.log"
echo ""

# ── Run Q: F1+NLP+600, num_parents=2 [CROSSOVER PRIMARY] ─────────────────────
echo "================================================================"
echo "[Q] chains/hotpotqa/static_f1_600  db=1  chain=$CHAIN_URL_Q"
echo "PRIMARY: Crossover effect. H2: Q-P test_EM >= +2.4pp."
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_Q" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label Q \
    --redis-db 1 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_Q.log"
echo ""

# ── Run R: F1+default+600, num_parents=2 ─────────────────────────────────────
echo "================================================================"
echo "[R] chains/hotpotqa/static_f1_600  db=2  chain=$CHAIN_URL_R"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_R" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label R \
    --redis-db 2 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_R.log"
echo ""

# ── Run S: F1+default+600, num_parents=1 [control] ───────────────────────────
echo "================================================================"
echo "[S] chains/hotpotqa/static_f1_600  db=3  chain=$CHAIN_URL_S"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_S" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label S \
    --redis-db 3 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_S.log"
echo ""

echo "================================================================"
echo "All test evals complete."
echo "Results: $RESULTS_PATH"
echo "Logs:    $LOG_DIR/test_eval_{P,Q,R,S}.log"
echo ""
echo "Primary gate (Run P replication): test_EM >= 62.3% → H1 confirmed"
echo "Primary gate (Q-P delta):         >= +2.4pp AND McNemar p<0.05 → H2 POSITIVE (THROUGHPUT CONFOUNDED)"
echo "Strong positive:                  Q-P >= +5.0pp"
echo "================================================================"
