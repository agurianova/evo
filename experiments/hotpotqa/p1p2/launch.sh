#!/usr/bin/env bash
# Launch script for HotpotQA P1×P2 factorial experiment.
#
# Two interventions:
#   P1 (Rotation) — chain_spec-hash-seeded random.sample(1000, 300) per program
#   P2 (ASI)      — per-hop BM25 retrieval recall vs gold docs in mutation context
#
# Design (all runs: ddce37b4 seed, num_parents=1, primary_resolution=50, 8 mut/gen):
# Note: max_mutations_per_generation=16 is a dead param here. AllCombinationsParentSelector
# with num_parents=1, max_elites=8 yields C(8,1)=8 candidates — 16 is never reached.
#   Run E — DB 10, standard pipeline,     static    (control: no P1, no P2)
#   Run F — DB 11, hotpotqa_asi pipeline, static_a  (P2 only)
#   Run G — DB 12, standard pipeline,     static_r  (P1 only)
#   Run H — DB 13, hotpotqa_asi pipeline, static_ra (P1+P2)
#
# Chain servers (one dedicated per run — no cross-run contention):
#   Run E → 10.226.17.25:8001
#   Run F → 10.226.17.25:8000
#   Run G → 10.225.185.235:8001
#   Run H → 10.225.185.235:8000
#
# Mutation LLMs (one per run):
#   Run E → 10.226.72.211:8777
#   Run F → 10.226.15.38:8777
#   Run G → 10.226.185.131:8777
#   Run H → 10.225.51.251:8777
#
# Usage:
#   bash experiments/hotpotqa_p1p2/launch.sh
#
# Prereqs: Redis DBs 10/11/12/13 empty (run FLUSHDB or use --flush flag),
#          all 8 vLLM server endpoints reachable.

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
LOG_DIR="$PROJ/experiments/hotpotqa_p1p2"
SEED_DIR="$PROJ/experiments/hotpotqa_thinking/seeds/ddce37b4"

# ── Server IPs ─────────────────────────────────────────────────────────────────
CHAIN_SERVER_1="10.226.17.25"    # chain server 1 (Runs E, F)
CHAIN_SERVER_2="10.225.185.235"  # chain server 2 (Runs G, H)
MUT_E="10.226.72.211"            # mutation LLM for Run E
MUT_F="10.226.15.38"             # mutation LLM for Run F
MUT_G="10.226.185.131"           # mutation LLM for Run G
MUT_H="10.225.51.251"            # mutation LLM for Run H

CHAIN_URL_E="http://$CHAIN_SERVER_1:8001/v1"
CHAIN_URL_F="http://$CHAIN_SERVER_1:8000/v1"
CHAIN_URL_G="http://$CHAIN_SERVER_2:8001/v1"
CHAIN_URL_H="http://$CHAIN_SERVER_2:8000/v1"

# All LLM endpoints + GitHub API must bypass Squid proxy
export NO_PROXY="localhost,127.0.0.1,$CHAIN_SERVER_1,$CHAIN_SERVER_2,$MUT_E,$MUT_F,$MUT_G,$MUT_H,api.github.com"
export no_proxy="$NO_PROXY"

echo "NO_PROXY=$NO_PROXY"
echo ""

# ── Optional: flush Redis DBs ──────────────────────────────────────────────────
if [[ "${1:-}" == "--flush" ]]; then
    echo "[flush] Flushing Redis DBs 10/11/12/13..."
    for DB in 10 11 12 13; do
        redis-cli -n "$DB" FLUSHDB
        echo "[flush] DB $DB flushed."
    done
    echo ""
fi

# ── Preflight: server connectivity ────────────────────────────────────────────
echo "[preflight] Checking all vLLM servers..."
for HOST_PORT in \
    "$CHAIN_SERVER_1:8001" \
    "$CHAIN_SERVER_1:8000" \
    "$CHAIN_SERVER_2:8001" \
    "$CHAIN_SERVER_2:8000" \
    "$MUT_E:8777" \
    "$MUT_F:8777" \
    "$MUT_G:8777" \
    "$MUT_H:8777"; do
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

# ── Preflight: verify thinking mode on ALL four chain endpoints ───────────────
# All four must be checked: Runs F (port 8000 server 1) and H (port 8000 server 2)
# use port 8000 which is NOT covered if only port 8001 is tested.
echo "[preflight] Verifying thinking mode on all chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_E" "$CHAIN_URL_F" "$CHAIN_URL_G" "$CHAIN_URL_H"; do
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
        echo "[preflight] FAIL: Redis DB $DB has $KEYS keys — flush first (run with --flush or redis-cli -n $DB FLUSHDB)."
        exit 1
    fi
    echo "[preflight] DB $DB: empty."
done
echo ""

# ── Preflight: seed directory exists ──────────────────────────────────────────
if [ ! -d "$SEED_DIR/initial_programs" ]; then
    echo "[preflight] FAIL: seed dir $SEED_DIR/initial_programs not found."
    exit 1
fi
N=$(ls "$SEED_DIR/initial_programs/"*.py 2>/dev/null | wc -l)
echo "[preflight] Seed $SEED_DIR: $N program(s)."
echo ""

echo "============================================================"
echo "[launch] All preflight checks passed. Launching 4 runs."
DATE=$(date -u '+%Y-%m-%d %H:%M UTC')
echo "[launch] $DATE"
echo "============================================================"
echo ""

# Common parameters for all runs
COMMON_PARAMS=(
    num_parents=1
    primary_resolution=50
    max_mutations_per_generation=16
    max_elites_per_generation=8
    max_generations=50
    program_loader.problem_dir="$SEED_DIR"
)

# ── Run E: control — standard pipeline, static, no P1, no P2 ─────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_E" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static \
    pipeline=guided \
    redis.db=10 \
    llm_base_url="http://$MUT_E:8777/v1" \
    > "$LOG_DIR/run_e.log" 2>&1 &
PID_E=$!
echo "[launch] Run E started — PID=$PID_E  DB=10  pipeline=guided      problem=static     chain=$CHAIN_URL_E"
echo "[launch] $DATE — Run E PID=$PID_E" >> "$LOG_DIR/launch.log"

# ── Run F: P2 only — ASI pipeline, static_a ──────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_F" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_a \
    pipeline=hotpotqa_asi \
    redis.db=11 \
    llm_base_url="http://$MUT_F:8777/v1" \
    > "$LOG_DIR/run_f.log" 2>&1 &
PID_F=$!
echo "[launch] Run F started — PID=$PID_F  DB=11  pipeline=hotpotqa_asi  problem=static_a   chain=$CHAIN_URL_F"
echo "[launch] $DATE — Run F PID=$PID_F" >> "$LOG_DIR/launch.log"

# ── Run G: P1 only — standard pipeline, static_r (rotation) ──────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_G" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_r \
    pipeline=guided \
    redis.db=12 \
    llm_base_url="http://$MUT_G:8777/v1" \
    > "$LOG_DIR/run_g.log" 2>&1 &
PID_G=$!
echo "[launch] Run G started — PID=$PID_G  DB=12  pipeline=guided      problem=static_r   chain=$CHAIN_URL_G"
echo "[launch] $DATE — Run G PID=$PID_G" >> "$LOG_DIR/launch.log"

# ── Run H: P1+P2 — ASI pipeline, static_ra (rotation + ASI) ──────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_H" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_ra \
    pipeline=hotpotqa_asi \
    redis.db=13 \
    llm_base_url="http://$MUT_H:8777/v1" \
    > "$LOG_DIR/run_h.log" 2>&1 &
PID_H=$!
echo "[launch] Run H started — PID=$PID_H  DB=13  pipeline=hotpotqa_asi  problem=static_ra  chain=$CHAIN_URL_H"
echo "[launch] $DATE — Run H PID=$PID_H" >> "$LOG_DIR/launch.log"

echo ""
echo "[launch] All 4 runs started."
echo ""
echo "Next steps:"
echo "  1. Update PIDs in experiments/hotpotqa_p1p2/run_watchdog.py:"
echo "     E=$PID_E  F=$PID_F  G=$PID_G  H=$PID_H"
echo "  2. Start watchdog:"
echo "     NO_PROXY=\"$NO_PROXY\" \\"
echo "     no_proxy=\"\$NO_PROXY\" \\"
echo "     nohup $PYTHON experiments/hotpotqa_p1p2/run_watchdog.py \\"
echo "       > experiments/hotpotqa_p1p2/watchdog.log 2>&1 &"
echo "  3. Monitor logs:"
echo "     tail -f $LOG_DIR/run_e.log"
echo "     python experiments/hotpotqa_p1p2/gen_stats.py"
