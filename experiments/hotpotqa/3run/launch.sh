#!/usr/bin/env bash
# Attempt 4 — authoritative launch script for the 3-run HotpotQA experiment.
# Always use THIS script to launch runs. Never hand-type IPs or NO_PROXY.
#
# Usage:
#   bash experiments/hotpotqa_3run/launch.sh
#
# Prereqs: DBs 10/11/12 empty, warmstart_56pct.py present in initial_programs/.

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
LOG_DIR="$PROJ/experiments/hotpotqa_3run"

# ── All servers that must bypass Squid proxy ──────────────────────────────────
CHAIN_SERVER="10.226.17.25"   # chain execution / validation (Qwen3-8B non-thinking)
MUT_A="10.226.72.211"         # mutation LLM for Run A
MUT_B="10.226.15.38"          # mutation LLM for Run B
MUT_C="10.226.185.131"        # mutation LLM for Run C

export NO_PROXY="localhost,127.0.0.1,$CHAIN_SERVER,$MUT_A,$MUT_B,$MUT_C"
export no_proxy="$NO_PROXY"

echo "NO_PROXY=$NO_PROXY"

# ── Preflight connectivity check ──────────────────────────────────────────────
echo "[preflight] Checking all servers..."
for HOST_PORT in \
    "$CHAIN_SERVER:8001" \
    "$MUT_A:8777" \
    "$MUT_B:8777" \
    "$MUT_C:8777"; do
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
echo "[preflight] All servers reachable."

# ── Verify DBs are empty ──────────────────────────────────────────────────────
for DB in 10 11 12; do
    KEYS=$($PYTHON -c "import redis; r=redis.Redis(host='localhost',port=6379,db=$DB); print(r.dbsize())")
    if [ "$KEYS" -ne 0 ]; then
        echo "[preflight] FAIL: Redis DB $DB has $KEYS keys — flush first."
        exit 1
    fi
done
echo "[preflight] Redis DBs 10/11/12 empty."

# ── Verify warm-start seed is OUTSIDE initial_programs/ ──────────────────────
# OFAT design: A and B use baseline.py only; warmstart is injected for C only.
WARMSTART_SRC="$PROJ/experiments/hotpotqa_3run/warmstart_56pct.py"
WARMSTART_DST="$PROJ/problems/chains/hotpotqa/static/initial_programs/warmstart_56pct.py"
if [ ! -f "$WARMSTART_SRC" ]; then
    echo "[preflight] FAIL: warm-start source not found at $WARMSTART_SRC"
    exit 1
fi
if [ -f "$WARMSTART_DST" ]; then
    echo "[preflight] FAIL: warmstart_56pct.py is already in initial_programs/ — remove it first (OFAT violation)."
    exit 1
fi
echo "[preflight] Warm-start seed ready (not yet in initial_programs/)."

echo ""
echo "[launch] Starting Attempt 5..."
DATE=$(date -u '+%Y-%m-%d %H:%M UTC')
echo "[launch] $DATE"

# ── Run A ─────────────────────────────────────────────────────────────────────
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static \
    redis.db=10 \
    llm_base_url="http://$MUT_A:8777/v1" \
    primary_resolution=10 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=5 \
    max_generations=50 \
    > "$LOG_DIR/run_a.log" 2>&1 &
PID_A=$!
echo "[launch] Run A PID: $PID_A"

# ── Run B (5 min stagger) ─────────────────────────────────────────────────────
(
    sleep 300
    export NO_PROXY="localhost,127.0.0.1,$CHAIN_SERVER,$MUT_A,$MUT_B,$MUT_C"
    export no_proxy="$NO_PROXY"
    nohup "$PYTHON" "$PROJ/run.py" \
        problem.name=chains/hotpotqa/static \
        redis.db=11 \
        llm_base_url="http://$MUT_B:8777/v1" \
        primary_resolution=10 \
        max_mutations_per_generation=16 \
        max_elites_per_generation=8 \
        max_generations=50 \
        > "$LOG_DIR/run_b.log" 2>&1 &
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Run B PID: $!" | tee -a "$LOG_DIR/launch.log"
) &

# ── Run C (10 min stagger) ─────────────────────────────────────────────────────
# Inject warmstart JUST before C starts, remove it 5 min later (after C loaded it).
(
    sleep 600
    export NO_PROXY="localhost,127.0.0.1,$CHAIN_SERVER,$MUT_A,$MUT_B,$MUT_C"
    export no_proxy="$NO_PROXY"
    cp "$WARMSTART_SRC" "$WARMSTART_DST"
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Warm-start seed injected into initial_programs/." | tee -a "$LOG_DIR/launch.log"
    nohup "$PYTHON" "$PROJ/run.py" \
        problem.name=chains/hotpotqa/static \
        redis.db=12 \
        llm_base_url="http://$MUT_C:8777/v1" \
        primary_resolution=10 \
        max_mutations_per_generation=8 \
        max_elites_per_generation=5 \
        max_generations=50 \
        > "$LOG_DIR/run_c.log" 2>&1 &
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Run C PID: $!" | tee -a "$LOG_DIR/launch.log"
    sleep 300
    rm -f "$WARMSTART_DST"
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] Warm-start seed removed from initial_programs/." | tee -a "$LOG_DIR/launch.log"
) &

echo "[launch] $DATE — Run A PID=$PID_A. B/C launching with 5/10-min stagger." | tee -a "$LOG_DIR/launch.log"
echo "[launch] Done. Monitor: tail -f $LOG_DIR/run_a.log"
