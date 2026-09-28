#!/usr/bin/env bash
# Test evaluations for cold_start experiment — 4 runs on fixed 300-sample test set.
#
# Usage:
#   GIGAEVO_PYTHON=/home/jovyan/envs/evo_fast/bin/python \
#   bash experiments/hotpotqa/cold_start/run_test_eval.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-/home/jovyan/envs/evo_fast/bin/python}
export PYTHONPATH="$PROJ"
EVAL_SCRIPT="$PROJ/experiments/hotpotqa/thinking/gen10_test_eval.py"
RESULTS_PATH="$PROJ/experiments/hotpotqa/cold_start/test_evals/results.json"
LOG_DIR="$PROJ/experiments/hotpotqa/cold_start/test_evals"
mkdir -p "$LOG_DIR"

CHAIN_URL_T1="http://10.226.17.25:8001/v1"
CHAIN_URL_T2="http://10.226.17.25:8000/v1"
CHAIN_URL_T3="http://10.225.185.235:8001/v1"
CHAIN_URL_T4="http://10.225.185.235:8000/v1"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251"
export no_proxy="$NO_PROXY"

echo "[preflight] Verifying thinking mode on all 4 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_T1" "$CHAIN_URL_T2" "$CHAIN_URL_T3" "$CHAIN_URL_T4"; do
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

for label in T1 T2 T3 T4; do
    case $label in
        T1) db=0; url="$CHAIN_URL_T1" ;;
        T2) db=1; url="$CHAIN_URL_T2" ;;
        T3) db=2; url="$CHAIN_URL_T3" ;;
        T4) db=3; url="$CHAIN_URL_T4" ;;
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
echo "Reference mean: 57.11% (push C=58.67%, crossover P=57.33%, crossover S=55.33%)"
echo "t-test: scipy.stats.ttest_1samp([T1,T2,T3,T4], 0.5711, alternative='greater')"
echo "================================================================"
