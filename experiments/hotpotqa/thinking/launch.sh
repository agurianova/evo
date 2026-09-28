#!/usr/bin/env bash
# Launch script for HotpotQA thinking-mode 2×2 factorial experiment.
#
# Design (all runs: num_parents=1, primary_resolution=50, 16 mut/gen):
#   Run A — DB 10, default pipeline,      baseline seed,    10.226.72.211:8777
#   Run B — DB 11, default pipeline,      ddce37b4 seed,    10.226.15.38:8777
#   Run C — DB 12, hotpotqa_reflective,   baseline seed,    10.226.185.131:8777
#   Run D — DB 13, hotpotqa_reflective,   ddce37b4 seed,    10.225.51.251:8777
#
# Chain servers (one dedicated per run, no contention):
#   Run A → 10.226.17.25:8001
#   Run B → 10.226.17.25:8000
#   Run C → 10.225.185.235:8001
#   Run D → 10.225.185.235:8000
#
# Usage:
#   bash experiments/hotpotqa_thinking/launch.sh
#
# Prereqs: Redis DBs 10/11/12/13 empty, all 6 vLLM servers reachable.

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
LOG_DIR="$PROJ/experiments/hotpotqa_thinking"
SEEDS_DIR="$PROJ/experiments/hotpotqa_thinking/seeds"

# ── Server IPs ─────────────────────────────────────────────────────────────────
CHAIN_SERVER_1="10.226.17.25"    # chain server 1 (Runs A, B)
CHAIN_SERVER_2="10.225.185.235"  # chain server 2 (Runs C, D)
MUT_A="10.226.72.211"            # mutation LLM for Run A
MUT_B="10.226.15.38"             # mutation LLM for Run B
MUT_C="10.226.185.131"           # mutation LLM for Run C
MUT_D="10.225.51.251"            # mutation LLM for Run D

# One dedicated chain server per run — no cross-run contention:
CHAIN_URL_A="http://$CHAIN_SERVER_1:8001/v1"
CHAIN_URL_B="http://$CHAIN_SERVER_1:8000/v1"
CHAIN_URL_C="http://$CHAIN_SERVER_2:8001/v1"
CHAIN_URL_D="http://$CHAIN_SERVER_2:8000/v1"

# All LLM endpoints + GitHub API must bypass Squid proxy
export NO_PROXY="localhost,127.0.0.1,$CHAIN_SERVER_1,$CHAIN_SERVER_2,$MUT_A,$MUT_B,$MUT_C,$MUT_D,api.github.com"
export no_proxy="$NO_PROXY"

echo "NO_PROXY=$NO_PROXY"
echo ""

# ── Preflight: server connectivity ────────────────────────────────────────────
echo "[preflight] Checking all vLLM servers..."
for HOST_PORT in \
    "$CHAIN_SERVER_1:8001" \
    "$CHAIN_SERVER_1:8000" \
    "$CHAIN_SERVER_2:8001" \
    "$CHAIN_SERVER_2:8000" \
    "$MUT_A:8777" \
    "$MUT_B:8777" \
    "$MUT_C:8777" \
    "$MUT_D:8777"; do
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
echo ""

# ── Preflight: verify thinking mode on both chain servers ─────────────────────
echo "[preflight] Verifying thinking mode on chain servers..."
for CHAIN_URL in "http://$CHAIN_SERVER_1:8001/v1" "http://$CHAIN_SERVER_2:8001/v1"; do
    THINK_TEST=$($PYTHON -c "
import requests, os
os.environ['no_proxy'] = os.environ.get('no_proxy', '')
resp = requests.post(
    '$CHAIN_URL/chat/completions',
    headers={'Authorization': 'Bearer None', 'Content-Type': 'application/json'},
    json={
        'model': 'Qwen/Qwen3-8B',
        'messages': [{'role': 'user', 'content': 'What is 2+2? Answer:'}],
        'max_tokens': 512,
        'temperature': 0.1,
    },
    timeout=30,
)
content = resp.json()['choices'][0]['message']['content']
print('HAS_THINK' if '<think>' in content else 'NO_THINK')
" 2>/dev/null || echo "ERROR")
    if [ "$THINK_TEST" != "HAS_THINK" ]; then
        echo "[preflight] FAIL: $CHAIN_URL NOT in thinking mode (got: $THINK_TEST) — abort."
        exit 1
    fi
    echo "[preflight] Confirmed thinking mode: $CHAIN_URL"
done
echo ""

# ── Preflight: Redis DBs must be empty ────────────────────────────────────────
echo "[preflight] Checking Redis DBs..."
for DB in 10 11 12 13; do
    KEYS=$($PYTHON -c "import redis; r=redis.Redis(host='localhost',port=6379,db=$DB); print(r.dbsize())")
    if [ "$KEYS" -ne 0 ]; then
        echo "[preflight] FAIL: Redis DB $DB has $KEYS keys — flush first."
        exit 1
    fi
    echo "[preflight] DB $DB: empty."
done
echo ""

# ── Preflight: seed directories exist ─────────────────────────────────────────
for SEED_DIR in "$SEEDS_DIR/baseline" "$SEEDS_DIR/ddce37b4"; do
    if [ ! -d "$SEED_DIR/initial_programs" ]; then
        echo "[preflight] FAIL: seed dir $SEED_DIR/initial_programs not found."
        exit 1
    fi
    N=$(ls "$SEED_DIR/initial_programs/"*.py 2>/dev/null | wc -l)
    echo "[preflight] Seed $SEED_DIR: $N program(s)."
done
echo ""

echo "============================================================"
echo "[launch] All preflight checks passed. Launching 4 runs."
DATE=$(date -u '+%Y-%m-%d %H:%M UTC')
echo "[launch] $DATE"
echo "============================================================"
echo ""

# Common parameters for all runs
COMMON_PARAMS=(
    problem.name=chains/hotpotqa/static
    num_parents=1
    primary_resolution=50
    max_mutations_per_generation=16
    max_elites_per_generation=8
    max_generations=50
)

# ── Run A: default pipeline, baseline seed, chain→10.226.17.25:8001 ──────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_A" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    redis.db=10 \
    llm_base_url="http://$MUT_A:8777/v1" \
    program_loader.problem_dir="$SEEDS_DIR/baseline" \
    > "$LOG_DIR/run_a.log" 2>&1 &
PID_A=$!
echo "[launch] Run A started — PID=$PID_A  DB=10  pipeline=default  seed=baseline  chain=$CHAIN_URL_A"
echo "[launch] $DATE — Run A PID=$PID_A" >> "$LOG_DIR/launch.log"

# ── Run B: default pipeline, ddce37b4 seed, chain→10.226.17.25:8000 ──────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_B" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    redis.db=11 \
    llm_base_url="http://$MUT_B:8777/v1" \
    program_loader.problem_dir="$SEEDS_DIR/ddce37b4" \
    > "$LOG_DIR/run_b.log" 2>&1 &
PID_B=$!
echo "[launch] Run B started — PID=$PID_B  DB=11  pipeline=default  seed=ddce37b4  chain=$CHAIN_URL_B"
echo "[launch] $DATE — Run B PID=$PID_B" >> "$LOG_DIR/launch.log"

# ── Run C: reflective pipeline, baseline seed, chain→10.225.185.235:8001 ─────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_C" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    redis.db=12 \
    llm_base_url="http://$MUT_C:8777/v1" \
    program_loader.problem_dir="$SEEDS_DIR/baseline" \
    pipeline=hotpotqa_reflective \
    > "$LOG_DIR/run_c.log" 2>&1 &
PID_C=$!
echo "[launch] Run C started — PID=$PID_C  DB=12  pipeline=hotpotqa_reflective  seed=baseline  chain=$CHAIN_URL_C"
echo "[launch] $DATE — Run C PID=$PID_C" >> "$LOG_DIR/launch.log"

# ── Run D: reflective pipeline, ddce37b4 seed, chain→10.225.185.235:8000 ─────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_D" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    redis.db=13 \
    llm_base_url="http://$MUT_D:8777/v1" \
    program_loader.problem_dir="$SEEDS_DIR/ddce37b4" \
    pipeline=hotpotqa_reflective \
    > "$LOG_DIR/run_d.log" 2>&1 &
PID_D=$!
echo "[launch] Run D started — PID=$PID_D  DB=13  pipeline=hotpotqa_reflective  seed=ddce37b4  chain=$CHAIN_URL_D"
echo "[launch] $DATE — Run D PID=$PID_D" >> "$LOG_DIR/launch.log"

echo ""
echo "[launch] All 4 runs started simultaneously."
echo "[launch] Monitor: tail -f $LOG_DIR/run_a.log"
