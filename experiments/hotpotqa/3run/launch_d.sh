#!/usr/bin/env bash
# Launch script for Run D — Experiment 2 Condition B.
#
# Treatment: primary_resolution=50 (vs 10 in the 3-run OFAT experiment)
# Seed:      warmstart_60pct.py (best program from Run C, 60.0% val EM)
# Server:    10.225.51.251:8777 (4th Qwen3-235B mutation server)
# Redis DB:  13
#
# Scientific goal: Test whether coarser archive binning (50 bins vs ~2-3
# effective bins at resolution=10) breaks archive saturation and allows
# evolution to continue past the 60% ceiling seen in all three OFAT runs.
#
# Usage:
#   bash experiments/hotpotqa_3run/launch_d.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
LOG_DIR="$PROJ/experiments/hotpotqa_3run"

# ── Server IPs ─────────────────────────────────────────────────────────────────
CHAIN_SERVER="10.226.17.25"   # chain execution / validation (Qwen3-8B non-thinking)
MUT_D="10.225.51.251"         # mutation LLM for Run D (4th server, different subnet)

export NO_PROXY="localhost,127.0.0.1,$CHAIN_SERVER,$MUT_D"
export no_proxy="$NO_PROXY"

echo "NO_PROXY=$NO_PROXY"

# ── Preflight: server connectivity ────────────────────────────────────────────
echo "[preflight] Checking servers..."
for HOST_PORT in "$CHAIN_SERVER:8001" "$MUT_D:8777"; do
    HOST="${HOST_PORT%%:*}"
    PORT="${HOST_PORT##*:}"
    RESULT=$(curl --noproxy "$HOST" --connect-timeout 5 -s -o /dev/null -w "%{http_code}" \
             "http://$HOST:$PORT/v1/models" 2>/dev/null || echo "FAIL")
    if [ "$RESULT" = "FAIL" ] || [ "$RESULT" = "000" ]; then
        echo "[preflight] FAIL: $HOST:$PORT unreachable — aborting."
        exit 1
    fi
    echo "[preflight] OK:   $HOST:$PORT (HTTP $RESULT)"
done

# ── Preflight: vLLM version check on mutation server ─────────────────────────
echo "[preflight] Checking vLLM version on $MUT_D..."
VLLM_VERSION=$(curl --noproxy "$MUT_D" --connect-timeout 5 -s \
    "http://$MUT_D:8777/version" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['version'])" 2>/dev/null || echo "UNKNOWN")
echo "[preflight] $MUT_D vLLM version: $VLLM_VERSION"
if [ "$VLLM_VERSION" = "UNKNOWN" ]; then
    echo "[preflight] WARNING: Could not determine vLLM version — proceed with caution."
else
    echo "[preflight] Version OK (expected 0.16.0rc2.dev221 or similar)."
fi

# ── Preflight: Redis DB 13 must be empty ─────────────────────────────────────
KEYS=$($PYTHON -c "import redis; r=redis.Redis(host='localhost',port=6379,db=13); print(r.dbsize())")
if [ "$KEYS" -ne 0 ]; then
    echo "[preflight] FAIL: Redis DB 13 has $KEYS keys — flush first with:"
    echo "  redis-cli -n 13 FLUSHDB"
    exit 1
fi
echo "[preflight] Redis DB 13 empty. OK."

# ── Preflight: warm-start seed must be in initial_programs/ ──────────────────
WARMSTART="$PROJ/problems/chains/hotpotqa/static/initial_programs/warmstart_60pct.py"
if [ ! -f "$WARMSTART" ]; then
    echo "[preflight] FAIL: warm-start seed not found at $WARMSTART"
    echo "  Extract it with:"
    echo "  PYTHONPATH=. $PYTHON tools/top_programs.py --run chains/hotpotqa/static@12 -n 1 --save-dir experiments/hotpotqa_3run/top_programs_d/"
    echo "  cp experiments/hotpotqa_3run/top_programs_d/rank01_0.6000_ff0793cb.py $WARMSTART"
    exit 1
fi
echo "[preflight] Warm-start seed present: $WARMSTART"

echo ""
echo "[preflight] All checks passed."
echo ""

# ── Launch Run D ──────────────────────────────────────────────────────────────
DATE=$(date -u '+%Y-%m-%d %H:%M UTC')
echo "[launch] $DATE — starting Run D (Exp 2 Cond B, primary_resolution=50)"

nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static \
    redis.db=13 \
    llm_base_url="http://$MUT_D:8777/v1" \
    primary_resolution=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=5 \
    max_generations=50 \
    > "$LOG_DIR/run_d.log" 2>&1 &

PID_D=$!
echo "[launch] Run D PID: $PID_D"
echo "[launch] $DATE — Run D PID=$PID_D" >> "$LOG_DIR/launch.log"
echo ""
echo "[launch] Monitor with:"
echo "  tail -f $LOG_DIR/run_d.log"
echo ""
echo "[launch] Per-gen stats:"
echo "  PYTHONPATH=$PROJ $PYTHON $PROJ/experiments/hotpotqa_3run/gen_stats.py --run D 2>/dev/null"
