#!/usr/bin/env bash
# Test evaluation script for prompt_coevolution experiment — 3 main runs on fixed 300-sample test set.
#
# Evaluates the best-by-val program from each main run (X1, X2, X3) on HotpotQA_test.jsonl.
# Run at gen 13 (midpoint) and gen 25 (final). Record results in 03_plan.md.
#
# Usage:
#   GIGAEVO_PYTHON=/home/jovyan/envs/evo_fast/bin/python \
#   bash experiments/hotpotqa/prompt_coevolution/run_test_eval.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-/home/jovyan/envs/evo_fast/bin/python}
export PYTHONPATH="$PROJ"
EVAL_SCRIPT="$PROJ/experiments/hotpotqa/thinking/gen10_test_eval.py"
RESULTS_PATH="$PROJ/experiments/hotpotqa/prompt_coevolution/test_evals/results.json"
LOG_DIR="$PROJ/experiments/hotpotqa/prompt_coevolution/test_evals"
mkdir -p "$LOG_DIR"

# Main runs use three chain LLM endpoints (thinking ON)
CHAIN_URL_X1="http://10.226.17.25:8001/v1"
CHAIN_URL_X2="http://10.226.17.25:8000/v1"
CHAIN_URL_X3="http://10.225.185.235:8001/v1"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.47,10.225.51.251"
export no_proxy="$NO_PROXY"

echo "[preflight] Verifying thinking mode on X1, X2, X3 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_X1" "$CHAIN_URL_X2" "$CHAIN_URL_X3"; do
    HOST="${CHAIN_URL#http://}"; HOST="${HOST%%/*}"; HOST="${HOST%%:*}"
    RESPONSE=$(curl --noproxy "$HOST" -s --connect-timeout 10 --max-time 90 \
        -X POST "$CHAIN_URL/chat/completions" \
        -H "Authorization: Bearer None" -H "Content-Type: application/json" \
        -d '{"model":"Qwen/Qwen3-8B","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":200,"temperature":0.1}' \
        2>/dev/null || echo "CURL_FAIL")
    if echo "$RESPONSE" | grep -q "<think>"; then echo "[preflight] OK: $CHAIN_URL"
    else echo "[preflight] FAIL: $CHAIN_URL — aborting." && exit 1; fi
done
echo "[preflight] All verified."; echo ""

for label in X1 X2 X3; do
    case $label in
        X1) db=4; url="$CHAIN_URL_X1" ;;
        X2) db=5; url="$CHAIN_URL_X2" ;;
        X3) db=8; url="$CHAIN_URL_X3" ;;
    esac
    echo "================================================================"
    echo "[$label] db=$db chain=$url"
    echo "================================================================"
    HOTPOTQA_CHAIN_URL="$url" \
        "$PYTHON" "$EVAL_SCRIPT" \
        --run-label "$label" \
        --redis-db "$db" \
        --redis-prefix chains/hotpotqa/static_f1_600 \
        --max-gen 9999 \
        --n-samples 300 \
        --val-subset fixed_300 \
        --results-path "$RESULTS_PATH" \
        2>&1 | tee "$LOG_DIR/test_eval_${label}.log"
    echo ""
done

echo "================================================================"
echo "All test evals complete. Results: $RESULTS_PATH"
echo ""
echo "H0 reference mean: 59.58% ± 1.00pp (cold_start n=4, PR #75)"
echo "POSITIVE threshold: 61.58% (2σ above reference)"
echo "Individual cold-start runs: T1=59.33%, T2=60.67%, T3=58.33%, T4=60.00%"
echo "================================================================"
