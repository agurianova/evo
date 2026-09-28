#!/usr/bin/env bash
# Final test evaluation for HotpotQA NLP-prompts experiment (PR #69).
#
# Evaluates the best-by-val program from each of the 4 runs on the held-out
# test set (300 samples). Pre-registration §8 (Primary Metric).
#
# Runs:
#   K — DB 0, chains/hotpotqa/static,   control (default prompts, fixed-300 val)
#   L — DB 1, chains/hotpotqa/static_r, treatment-1 (NLP prompts, rotation val)
#   M — DB 2, chains/hotpotqa/static_r, treatment-2 (NLP prompts, rotation val)
#   N — DB 3, chains/hotpotqa/static_r, treatment-3 (NLP prompts, rotation val)
#
# Usage:
#   bash experiments/hotpotqa_nlp_prompts/run_test_eval.sh
#
# Prereqs: all 4 runs completed gen 50 (check run_k/l/m/n.log for "max_generations=50").

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
EVAL_SCRIPT="$PROJ/experiments/hotpotqa_thinking/gen10_test_eval.py"
RESULTS_PATH="$PROJ/experiments/hotpotqa_nlp_prompts/test_evals/results.json"
LOG_DIR="$PROJ/experiments/hotpotqa_nlp_prompts/test_evals"

# Chain servers (same as launch.sh)
CHAIN_URL_K="http://10.226.17.25:8001/v1"
CHAIN_URL_L="http://10.226.17.25:8000/v1"
CHAIN_URL_M="http://10.225.185.235:8001/v1"
CHAIN_URL_N="http://10.225.185.235:8000/v1"

# All LLM endpoints must bypass Squid proxy
export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"

echo "NO_PROXY=$NO_PROXY"
echo ""

mkdir -p "$LOG_DIR"

# ── Preflight: thinking-mode verification on all 4 chain endpoints ─────────────
# Critical: servers may have restarted in non-thinking mode since evolution.
echo "[preflight] Verifying thinking mode on all 4 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_K" "$CHAIN_URL_L" "$CHAIN_URL_M" "$CHAIN_URL_N"; do
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
        echo "[preflight] Response: ${RESPONSE:0:200}"
        exit 1
    fi
done
echo "[preflight] All chain endpoints verified."
echo ""

# ── Run K: control — default prompts, fixed-300 val ───────────────────────────
echo "================================================================"
echo "[K] chains/hotpotqa/static  db=0  chain=$CHAIN_URL_K"
echo "    control (default prompts, fixed-300 val)"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_K" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label K \
    --redis-db 0 \
    --redis-prefix chains/hotpotqa/static \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_K.log"
echo ""

# ── Run L: treatment-1 — NLP prompts + rotation val ──────────────────────────
echo "================================================================"
echo "[L] chains/hotpotqa/static_r  db=1  chain=$CHAIN_URL_L"
echo "    treatment-1 (NLP prompts, rotation-300 val)"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_L" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label L \
    --redis-db 1 \
    --redis-prefix chains/hotpotqa/static_r \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset hash_seeded_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_L.log"
echo ""

# ── Run M: treatment-2 — NLP prompts + rotation val ──────────────────────────
echo "================================================================"
echo "[M] chains/hotpotqa/static_r  db=2  chain=$CHAIN_URL_M"
echo "    treatment-2 (NLP prompts, rotation-300 val)"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_M" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label M \
    --redis-db 2 \
    --redis-prefix chains/hotpotqa/static_r \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset hash_seeded_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_M.log"
echo ""

# ── Run N: treatment-3 — NLP prompts + rotation val ──────────────────────────
echo "================================================================"
echo "[N] chains/hotpotqa/static_r  db=3  chain=$CHAIN_URL_N"
echo "    treatment-3 (NLP prompts, rotation-300 val)"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_N" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label N \
    --redis-db 3 \
    --redis-prefix chains/hotpotqa/static_r \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset hash_seeded_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_N.log"
echo ""

echo "================================================================"
echo "All test evals complete."
echo "Results: $RESULTS_PATH"
echo "Logs:    $LOG_DIR/test_eval_{K,L,M,N}.log"
echo "================================================================"
