#!/usr/bin/env bash
# Run final test evaluations for all 4 hotpotqa_generalization runs.
#
# Evaluates the best-by-held_F1 program from each run on the fixed 300-sample
# test set using EM (primary metric: test EM at gen 25, best-by-held_F1).
#
# Usage:
#   GIGAEVO_PYTHON=/home/jovyan/envs/evo_fast/bin/python \
#   bash experiments/hotpotqa/generalization/run_test_eval.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-/home/jovyan/envs/evo_fast/bin/python}
export PYTHONPATH="$PROJ"
EVAL_SCRIPT="$PROJ/experiments/hotpotqa/thinking/gen10_test_eval.py"
RESULTS_PATH="$PROJ/experiments/hotpotqa/generalization/test_evals/results.json"
LOG_DIR="$PROJ/experiments/hotpotqa/generalization/test_evals"
mkdir -p "$LOG_DIR"

# Chain servers — same assignment as during training (03_plan.md)
CHAIN_URL_G1="http://10.226.17.25:8001/v1"
CHAIN_URL_G2="http://10.226.17.25:8000/v1"
CHAIN_URL_G3="http://10.225.185.235:8001/v1"
CHAIN_URL_G4="http://10.225.185.235:8000/v1"

# Squid proxy bypass for internal LLM servers + GitHub
export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"

echo "NO_PROXY=$NO_PROXY"
echo ""

# Shared CLI flags — kept as an array so multi-word values expand as separate args
COMMON_FLAGS=(
  --max-gen 25
  --n-samples 300
  --val-subset fixed_300
  --select-by fitness
  --results-path "$RESULTS_PATH"
)

# ── Preflight: thinking-mode verification ─────────────────────────────────────
echo "[preflight] Verifying thinking mode on all 4 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_G1" "$CHAIN_URL_G2" "$CHAIN_URL_G3" "$CHAIN_URL_G4"; do
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

# ── Run G1: Qwen3-235B vLLM ───────────────────────────────────────────────────
echo "================================================================"
echo "[G1] chains/hotpotqa/static_holdout_f1  db=0  chain=$CHAIN_URL_G1"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_G1" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label G1 \
    --redis-db 0 \
    --redis-prefix chains/hotpotqa/static_holdout_f1 \
    "${COMMON_FLAGS[@]}" \
    2>&1 | tee "$LOG_DIR/test_eval_G1.log"
echo ""

# ── Run G2: Qwen3-235B vLLM ───────────────────────────────────────────────────
echo "================================================================"
echo "[G2] chains/hotpotqa/static_holdout_f1  db=1  chain=$CHAIN_URL_G2"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_G2" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label G2 \
    --redis-db 1 \
    --redis-prefix chains/hotpotqa/static_holdout_f1 \
    "${COMMON_FLAGS[@]}" \
    2>&1 | tee "$LOG_DIR/test_eval_G2.log"
echo ""

# ── Run G3: Gemini-3.1-Pro ────────────────────────────────────────────────────
echo "================================================================"
echo "[G3] chains/hotpotqa/static_holdout_f1  db=2  chain=$CHAIN_URL_G3"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_G3" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label G3 \
    --redis-db 2 \
    --redis-prefix chains/hotpotqa/static_holdout_f1 \
    "${COMMON_FLAGS[@]}" \
    2>&1 | tee "$LOG_DIR/test_eval_G3.log"
echo ""

# ── Run G4: Gemini-3.1-Pro ────────────────────────────────────────────────────
echo "================================================================"
echo "[G4] chains/hotpotqa/static_holdout_f1  db=3  chain=$CHAIN_URL_G4"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_G4" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label G4 \
    --redis-db 3 \
    --redis-prefix chains/hotpotqa/static_holdout_f1 \
    "${COMMON_FLAGS[@]}" \
    2>&1 | tee "$LOG_DIR/test_eval_G4.log"
echo ""

echo "================================================================"
echo "All test evals complete."
echo "Results: $RESULTS_PATH"
echo "Logs:    $LOG_DIR/test_eval_{G1,G2,G3,G4}.log"
echo ""
echo "Primary metric: test EM at gen 25, best-by-held_F1 program (n=4 runs)."
echo "================================================================"
