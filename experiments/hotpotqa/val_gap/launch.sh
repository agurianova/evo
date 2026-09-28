#!/usr/bin/env bash
# Launch script for hotpotqa_val_gap experiment.
#
# 4-arm design (Amendment 1: P replaced by F — see 03_plan.md)
#   Run O — DB 4, prompts=default, problem=static    (control: fixed-300 EM)
#   Run R — DB 7, prompts=default, problem=static_r  (rotating-300, EM)
#   Run Q — DB 6, prompts=default, problem=static_600 (fixed-600, EM)
#   Run F — DB 5, prompts=default, problem=static_f1 (fixed-300, F1 fitness)
#
# All runs: pipeline=hotpotqa_asi, prompts=default, seed=ddce37b4, num_parents=1
#
# Chain server assignments (one per run, no cross-run contention):
#   Run O → 10.226.17.25:8001
#   Run R → 10.226.17.25:8000
#   Run Q → 10.225.185.235:8001
#   Run P → 10.225.185.235:8000
#
# Mutation LLM assignments (one per run):
#   Run O → 10.226.72.211:8777
#   Run R → 10.226.15.38:8777
#   Run Q → 10.226.185.131:8777
#   Run P → 10.225.51.251:8777
#
# Pre-registration: experiments/hotpotqa_val_gap/03_plan.md (commit 287e7b6)
# Primary gate: Gate C (Q vs O) — POSITIVE if gap_Q < gap_O − 5.0pp AND test EM(Q) ≥ 60%
#
# Usage:
#   bash experiments/hotpotqa_val_gap/launch.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
LOG_DIR="$PROJ/experiments/hotpotqa_val_gap"
SEED_DIR="$PROJ/experiments/hotpotqa_thinking/seeds/ddce37b4"

# ── Server IPs ─────────────────────────────────────────────────────────────────
CHAIN_SERVER_1="10.226.17.25"
CHAIN_SERVER_2="10.225.185.235"
MUT_O="10.226.72.211"
MUT_R="10.226.15.38"
MUT_Q="10.226.185.131"
MUT_P="10.225.51.251"

CHAIN_URL_O="http://$CHAIN_SERVER_1:8001/v1"
CHAIN_URL_R="http://$CHAIN_SERVER_1:8000/v1"
CHAIN_URL_Q="http://$CHAIN_SERVER_2:8001/v1"
CHAIN_URL_F="http://$CHAIN_SERVER_2:8000/v1"

export NO_PROXY="localhost,127.0.0.1,$CHAIN_SERVER_1,$CHAIN_SERVER_2,$MUT_O,$MUT_R,$MUT_Q,$MUT_P,api.github.com"
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
    "$MUT_O:8777" \
    "$MUT_R:8777" \
    "$MUT_Q:8777" \
    "$MUT_P:8777"; do
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

# ── Preflight: verify context window ≥ 32K on chain servers ──────────────────
echo "[preflight] Checking chain server context window (need ≥ 32768)..."
for CHAIN_URL in "$CHAIN_URL_O" "$CHAIN_URL_R" "$CHAIN_URL_Q" "$CHAIN_URL_F"; do
    HOST="${CHAIN_URL#http://}"
    HOST="${HOST%%:*}"
    CTX=$(curl --noproxy "$HOST" -s --connect-timeout 5 "$CHAIN_URL/models" \
        2>/dev/null | grep -o '"max_model_len":[0-9]*' | head -1 | cut -d: -f2 || echo "unknown")
    echo "[preflight] $CHAIN_URL — max_model_len=$CTX"
done
echo ""

# ── Preflight: verify thinking mode on chain servers ─────────────────────────
echo "[preflight] Verifying thinking mode on all chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_O" "$CHAIN_URL_R" "$CHAIN_URL_Q" "$CHAIN_URL_F"; do
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

# ── Preflight: Redis DBs 4-7 must be empty ────────────────────────────────────
echo "[preflight] Checking Redis DBs 4-7..."
for DB in 4 5 6 7; do
    KEYS=$("$PYTHON" -c "import redis; r=redis.Redis(host='localhost',port=6379,db=$DB); print(r.dbsize())")
    if [ "$KEYS" -ne 0 ]; then
        echo "[preflight] FAIL: Redis DB $DB has $KEYS keys — flush first."
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

# ── Preflight: verify dataset checksums ───────────────────────────────────────
echo "[preflight] Verifying dataset checksums..."
TRAIN_HASH=$(sha256sum "$PROJ/problems/chains/hotpotqa/dataset/HotpotQA_train.jsonl" | cut -d' ' -f1)
TEST_HASH=$(sha256sum "$PROJ/problems/chains/hotpotqa/dataset/HotpotQA_test.jsonl" | cut -d' ' -f1)
EXPECTED_TRAIN="9d8b0ba2a19d124fa243c88b650b2ecd42e5c771bc4e039553389c6b9566ef94"
EXPECTED_TEST="c46bfb185e448bf1b92cb75bb5ab967f3211051793967f01500f453945046b0d"
if [ "$TRAIN_HASH" != "$EXPECTED_TRAIN" ]; then
    echo "[preflight] FAIL: HotpotQA_train.jsonl checksum mismatch!"
    echo "  Expected: $EXPECTED_TRAIN"
    echo "  Got:      $TRAIN_HASH"
    exit 1
fi
if [ "$TEST_HASH" != "$EXPECTED_TEST" ]; then
    echo "[preflight] FAIL: HotpotQA_test.jsonl checksum mismatch!"
    echo "  Expected: $EXPECTED_TEST"
    echo "  Got:      $TEST_HASH"
    exit 1
fi
echo "[preflight] Dataset checksums OK."
echo ""

echo "============================================================"
echo "[preflight] All preflight checks passed."
echo "============================================================"
echo ""

# ── Common parameters (identical for all 4 runs) ──────────────────────────────
COMMON_PARAMS=(
    pipeline=hotpotqa_asi
    prompts=default
    num_parents=1
    primary_resolution=50
    max_mutations_per_generation=8
    max_elites_per_generation=8
    max_generations=50
    program_loader.problem_dir="$SEED_DIR"
)

# ── Config review: dump resolved config for each run (--cfg job exits immediately) ──
echo "[verify] Resolved config for each run (--cfg job — no execution):"
echo ""

echo "--- Run O (control: fixed-300) ---"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_O" "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static \
    redis.db=4 \
    llm_base_url="http://$MUT_O:8777/v1" \
    --cfg job

echo ""
echo "--- Run R (rotating-300) ---"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_R" "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_r \
    redis.db=7 \
    llm_base_url="http://$MUT_R:8777/v1" \
    --cfg job

echo ""
echo "--- Run Q (fixed-600) ---"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_Q" "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_600 \
    redis.db=6 \
    llm_base_url="http://$MUT_Q:8777/v1" \
    --cfg job

echo ""
echo "--- Run F (fixed-300, F1 fitness) ---"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_F" "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_f1 \
    redis.db=5 \
    llm_base_url="http://$MUT_P:8777/v1" \
    --cfg job

echo ""
echo "============================================================"
echo "[verify] Review the output above carefully."
echo "         Check: redis.db, pipeline, problem.name, llm_base_url,"
echo "         all four runs use prompts=default, redis DBs 4/7/6/5."
echo "         For Q and P: note problem.name=static_600/static_r600."
echo "Press Enter to launch all 4 runs, or Ctrl-C to abort."
read -r _ </dev/tty 2>/dev/null || true
echo "============================================================"
echo "[launch] Launching 4 runs."
echo "============================================================"
echo ""

DATE=$(date -u '+%Y-%m-%d %H:%M UTC')
echo "[launch] $DATE"
echo ""

# ── Run O: control — fixed-300 val ────────────────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_O" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static \
    redis.db=4 \
    llm_base_url="http://$MUT_O:8777/v1" \
    > "$LOG_DIR/run_o.log" 2>&1 &
PID_O=$!
echo "[launch] Run O (fixed-300)    PID=$PID_O  DB=4   problem=static      chain=$CHAIN_URL_O"
echo "[launch] $DATE — O=$PID_O" >> "$LOG_DIR/launch.log"

# ── Run R: rotating-300 val ────────────────────────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_R" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_r \
    redis.db=7 \
    llm_base_url="http://$MUT_R:8777/v1" \
    > "$LOG_DIR/run_r.log" 2>&1 &
PID_R=$!
echo "[launch] Run R (rotating-300) PID=$PID_R  DB=7   problem=static_r    chain=$CHAIN_URL_R"
echo "[launch] $DATE — R=$PID_R" >> "$LOG_DIR/launch.log"

# ── Run Q: fixed-600 val ──────────────────────────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_Q" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_600 \
    redis.db=6 \
    llm_base_url="http://$MUT_Q:8777/v1" \
    > "$LOG_DIR/run_q.log" 2>&1 &
PID_Q=$!
echo "[launch] Run Q (fixed-600)    PID=$PID_Q  DB=6   problem=static_600  chain=$CHAIN_URL_Q"
echo "[launch] $DATE — Q=$PID_Q" >> "$LOG_DIR/launch.log"

# ── Run F: fixed-300, F1 fitness (replaces P per Amendment 1) ─────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_F" nohup "$PYTHON" "$PROJ/run.py" \
    "${COMMON_PARAMS[@]}" \
    problem.name=chains/hotpotqa/static_f1 \
    redis.db=5 \
    llm_base_url="http://$MUT_P:8777/v1" \
    > "$LOG_DIR/run_f.log" 2>&1 &
PID_F=$!
echo "[launch] Run F (fixed-300,F1)  PID=$PID_F  DB=5   problem=static_f1   chain=$CHAIN_URL_F"
echo "[launch] $DATE — F=$PID_F" >> "$LOG_DIR/launch.log"

echo ""
echo "[launch] All 4 runs started."
echo ""
echo "Next steps:"
echo "  1. Update PIDs in experiments/hotpotqa_val_gap/run_watchdog.py:"
echo "     O=$PID_O  R=$PID_R  Q=$PID_Q  F=$PID_F"
echo "  2. Start watchdog:"
echo "     NO_PROXY=\"$NO_PROXY\" no_proxy=\"\$NO_PROXY\" \\"
echo "     nohup $PYTHON experiments/hotpotqa_val_gap/run_watchdog.py \\"
echo "       > experiments/hotpotqa_val_gap/watchdog.log 2>&1 &"
echo "  3. Monitor:"
echo "     tail -f $LOG_DIR/run_o.log"
echo "     tail -f $LOG_DIR/run_q.log  # 600-sample — watch gen time"
echo "     tail -f $LOG_DIR/run_f.log  # F1 run"
