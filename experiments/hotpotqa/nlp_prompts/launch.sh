#!/usr/bin/env bash
# Launch script for HotpotQA NLP-specific prompts experiment.
#
# Design: 1 control (K) + 3 treatment (L, M, N)
#   Run K — DB 0, prompts=default,  problem=static   (control; fixed-300 val)
#   Run L — DB 1, prompts=hotpotqa, problem=static_r (treatment replicate 1; rotation-300 val)
#   Run M — DB 2, prompts=hotpotqa, problem=static_r (treatment replicate 2; rotation-300 val)
#   Run N — DB 3, prompts=hotpotqa, problem=static_r (treatment replicate 3; rotation-300 val)
#
# Manipulated variables: prompts=hotpotqa AND rotation val set (static_r).
# Rotation rationale: fixed-300 showed 5-10pp val-test gap in P1xP2; rotation reduces selection
# noise and produces cleaner per-program val estimates (each program evaluated on different 300/1000).
# All other config identical: ddce37b4 seed, hotpotqa_asi pipeline (ASI failure formatter), num_parents=1.
# pipeline=hotpotqa_asi: uses HotpotQAASIFormatter to inject per-hop BM25 retrieval diagnostics
# (which gold docs were missed at hop-1 and hop-2) into every mutation prompt as structured markdown.
#
# Chain servers (one dedicated per run — no cross-run contention):
#   Run K → 10.226.17.25:8001
#   Run L → 10.226.17.25:8000
#   Run M → 10.225.185.235:8001
#   Run N → 10.225.185.235:8000
#
# Mutation LLMs:
#   Run K → 10.226.72.211:8777
#   Run L → 10.226.15.38:8777
#   Run M → 10.226.185.131:8777
#   Run N → 10.225.51.251:8777
#
# Pre-registration: docs/plans/2026-03-03-nlp-prompts-experiment.md
# Success criteria: treatment mean test EM >= 62.3% (GEPA) OR >= control + 2.4pp
#
# Usage:
#   bash experiments/hotpotqa_nlp_prompts/launch.sh [--flush]

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
LOG_DIR="$PROJ/experiments/hotpotqa_nlp_prompts"
SEED_DIR="$PROJ/experiments/hotpotqa_thinking/seeds/ddce37b4"

# ── Server IPs ─────────────────────────────────────────────────────────────────
CHAIN_SERVER_1="10.226.17.25"
CHAIN_SERVER_2="10.225.185.235"
MUT_K="10.226.72.211"
MUT_L="10.226.15.38"
MUT_M="10.226.185.131"
MUT_N="10.225.51.251"

CHAIN_URL_K="http://$CHAIN_SERVER_1:8001/v1"
CHAIN_URL_L="http://$CHAIN_SERVER_1:8000/v1"
CHAIN_URL_M="http://$CHAIN_SERVER_2:8001/v1"
CHAIN_URL_N="http://$CHAIN_SERVER_2:8000/v1"

export NO_PROXY="localhost,127.0.0.1,$CHAIN_SERVER_1,$CHAIN_SERVER_2,$MUT_K,$MUT_L,$MUT_M,$MUT_N,api.github.com"
export no_proxy="$NO_PROXY"

echo "NO_PROXY=$NO_PROXY"
echo ""

# ── Optional: flush Redis DBs ──────────────────────────────────────────────────
if [[ "${1:-}" == "--flush" ]]; then
    echo "[flush] Flushing Redis DBs 0/1/2/3..."
    "$PYTHON" -c "
import redis
for db in range(4):
    r = redis.Redis(db=db)
    r.flushdb()
    print(f'[flush] DB {db} flushed ({r.dbsize()} keys remaining).')
    r.close()
"
    echo ""
fi

# ── Preflight: server connectivity ────────────────────────────────────────────
echo "[preflight] Checking all vLLM servers..."
for HOST_PORT in \
    "$CHAIN_SERVER_1:8001" \
    "$CHAIN_SERVER_1:8000" \
    "$CHAIN_SERVER_2:8001" \
    "$CHAIN_SERVER_2:8000" \
    "$MUT_K:8777" \
    "$MUT_L:8777" \
    "$MUT_M:8777" \
    "$MUT_N:8777"; do
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

# ── Preflight: verify thinking mode on all chain endpoints ────────────────────
echo "[preflight] Verifying thinking mode on all chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_K" "$CHAIN_URL_L" "$CHAIN_URL_M" "$CHAIN_URL_N"; do
    HOST="${CHAIN_URL#http://}"
    HOST="${HOST%%:*}"
    RESPONSE=$(curl --noproxy "$HOST" -s --connect-timeout 10 --max-time 90 \
        -X POST "$CHAIN_URL/chat/completions" \
        -H "Authorization: Bearer None" -H "Content-Type: application/json" \
        -d '{"model":"Qwen/Qwen3-8B","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":200,"temperature":0.1}' \
        2>/dev/null || echo "CURL_FAIL")
    if echo "$RESPONSE" | grep -q "<think>"; then
        echo "[preflight] Thinking mode confirmed: $CHAIN_URL"
    else
        echo "[preflight] FAIL: $CHAIN_URL not in thinking mode — abort."
        exit 1
    fi
done
echo ""

# ── Preflight: Redis DBs must be empty ────────────────────────────────────────
echo "[preflight] Checking Redis DBs..."
for DB in 0 1 2 3; do
    KEYS=$($PYTHON -c "import redis; r=redis.Redis(host='localhost',port=6379,db=$DB); print(r.dbsize())")
    if [ "$KEYS" -ne 0 ]; then
        echo "[preflight] FAIL: Redis DB $DB has $KEYS keys — flush first (--flush flag or redis-cli -n $DB FLUSHDB)."
        exit 1
    fi
    echo "[preflight] DB $DB: empty."
done
echo ""

# ── Preflight: seed directory ──────────────────────────────────────────────────
if [ ! -d "$SEED_DIR/initial_programs" ]; then
    echo "[preflight] FAIL: seed dir not found: $SEED_DIR/initial_programs"
    exit 1
fi
N=$(ls "$SEED_DIR/initial_programs/"*.py 2>/dev/null | wc -l)
echo "[preflight] Seed $SEED_DIR: $N program(s)."
echo ""

echo "============================================================"
echo "[preflight] All preflight checks passed."
echo "============================================================"
echo ""

# Common parameters (shared across all 4 runs — NOT the manipulated variables)
COMMON_PARAMS=(
    pipeline=hotpotqa_asi
    num_parents=1
    primary_resolution=50
    max_mutations_per_generation=8
    max_elites_per_generation=8
    max_generations=50
    program_loader.problem_dir="$SEED_DIR"
)

# ── Verify: dry-run each run, then pause for human review ─────────────────────
echo "[verify] Dry run — review what would be launched for each run:"
echo ""

echo "--- Run K (control) ---"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_K" "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static \
    prompts=default \
    redis.db=0 \
    llm_base_url="http://$MUT_K:8777/v1" \
    dry_run=true

echo ""
echo "--- Run L (treatment 1) ---"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_L" "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_r \
    prompts=hotpotqa \
    redis.db=1 \
    llm_base_url="http://$MUT_L:8777/v1" \
    dry_run=true

echo ""
echo "--- Run M (treatment 2) ---"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_M" "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_r \
    prompts=hotpotqa \
    redis.db=2 \
    llm_base_url="http://$MUT_M:8777/v1" \
    dry_run=true

echo ""
echo "--- Run N (treatment 3) ---"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_N" "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_r \
    prompts=hotpotqa \
    redis.db=3 \
    llm_base_url="http://$MUT_N:8777/v1" \
    dry_run=true

echo ""
echo "============================================================"
echo "[verify] Review the output above carefully."
echo "         Check: redis.db, prompts.dir, pipeline, problem.dir,"
echo "         prompt files [CUSTOM]/[default], validate.py returns,"
echo "         FormatterStage override, seed programs, LLM URLs."
echo "Press Enter to launch all 4 runs, or Ctrl-C to abort."
read -r _ </dev/tty 2>/dev/null || true
echo "============================================================"
echo "[launch] Launching 4 runs."
echo "============================================================"
echo ""

# ── Run K: control — default prompts, fixed-300 val ───────────────────────────
DATE=$(date -u '+%Y-%m-%d %H:%M UTC')
echo "[launch] $DATE"
echo ""
HOTPOTQA_CHAIN_URL="$CHAIN_URL_K" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static \
    prompts=default \
    redis.db=0 \
    llm_base_url="http://$MUT_K:8777/v1" \
    > "$LOG_DIR/run_k.log" 2>&1 &
PID_K=$!
echo "[launch] Run K (control)    PID=$PID_K  DB=0   prompts=default   problem=static    chain=$CHAIN_URL_K"
echo "[launch] $DATE — K=$PID_K" >> "$LOG_DIR/launch.log"

# ── Run L: treatment 1 — NLP prompts + rotation ───────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_L" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_r \
    prompts=hotpotqa \
    redis.db=1 \
    llm_base_url="http://$MUT_L:8777/v1" \
    > "$LOG_DIR/run_l.log" 2>&1 &
PID_L=$!
echo "[launch] Run L (treatment)  PID=$PID_L  DB=1   prompts=hotpotqa  problem=static_r  chain=$CHAIN_URL_L"
echo "[launch] $DATE — L=$PID_L" >> "$LOG_DIR/launch.log"

# ── Run M: treatment 2 — NLP prompts + rotation ───────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_M" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_r \
    prompts=hotpotqa \
    redis.db=2 \
    llm_base_url="http://$MUT_M:8777/v1" \
    > "$LOG_DIR/run_m.log" 2>&1 &
PID_M=$!
echo "[launch] Run M (treatment)  PID=$PID_M  DB=2   prompts=hotpotqa  problem=static_r  chain=$CHAIN_URL_M"
echo "[launch] $DATE — M=$PID_M" >> "$LOG_DIR/launch.log"

# ── Run N: treatment 3 — NLP prompts + rotation ───────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_N" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_r \
    prompts=hotpotqa \
    redis.db=3 \
    llm_base_url="http://$MUT_N:8777/v1" \
    > "$LOG_DIR/run_n.log" 2>&1 &
PID_N=$!
echo "[launch] Run N (treatment)  PID=$PID_N  DB=3   prompts=hotpotqa  problem=static_r  chain=$CHAIN_URL_N"
echo "[launch] $DATE — N=$PID_N" >> "$LOG_DIR/launch.log"

echo ""
echo "[launch] All 4 runs started."
echo ""
echo "Next steps:"
echo "  1. Update PIDs in experiments/hotpotqa_nlp_prompts/run_watchdog.py:"
echo "     K=$PID_K  L=$PID_L  M=$PID_M  N=$PID_N"
echo "  2. Start watchdog:"
echo "     NO_PROXY=\"$NO_PROXY\" no_proxy=\"\$NO_PROXY\" \\"
echo "     nohup $PYTHON experiments/hotpotqa_nlp_prompts/run_watchdog.py \\"
echo "       > experiments/hotpotqa_nlp_prompts/watchdog.log 2>&1 &"
echo "  3. Monitor:"
echo "     tail -f $LOG_DIR/run_k.log"
echo "     python experiments/hotpotqa_nlp_prompts/gen_stats.py"
