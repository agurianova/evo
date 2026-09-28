#!/usr/bin/env bash
# Launch script for crossover experiment — Run D replication + num_parents=2 stagnation attack.
#
# Run P — DB 0, F1+NLP+600, num_parents=1, 25 gens  [REPLICATION — clean Run D]
# Run Q — DB 1, F1+NLP+600, num_parents=2, 25 gens  [CROSSOVER — primary mechanism test]
# Run R — DB 2, F1+default+600, num_parents=2, 25 gens
# Run S — DB 3, F1+default+600, num_parents=1, 25 gens  [concurrent control for R]
#
# Chain servers (one dedicated per run):
#   Run P → 10.226.17.25:8001
#   Run Q → 10.226.17.25:8000
#   Run R → 10.225.185.235:8001
#   Run S → 10.225.185.235:8000
#
# Mutation LLMs (one per run):
#   Run P → 10.226.72.211:8777
#   Run Q → 10.226.15.38:8777
#   Run R → 10.226.185.131:8777
#   Run S → 10.225.51.251:8777
#
# CRITICAL OVERRIDES (both differ from Hydra defaults — verify via --cfg job):
#   max_elites_per_generation=8   (default in config/constants/evolution.yaml = 5)
#   num_parents=1 for Run P only  (default = 2)
#
# Usage:
#   bash experiments/hotpotqa/crossover/launch.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-/home/jovyan/envs/evo_fast/bin/python}
LOG_DIR="$PROJ/experiments/hotpotqa/crossover"
SEED_DIR="$PROJ/experiments/hotpotqa/thinking/seeds/ddce37b4"

# ── Server IPs ─────────────────────────────────────────────────────────────────
CHAIN_SERVER_1="10.226.17.25"
CHAIN_SERVER_2="10.225.185.235"
MUT_P="10.226.72.211"
MUT_Q="10.226.15.38"
MUT_R="10.226.185.131"
MUT_S="10.225.51.251"

CHAIN_URL_P="http://$CHAIN_SERVER_1:8001/v1"
CHAIN_URL_Q="http://$CHAIN_SERVER_1:8000/v1"
CHAIN_URL_R="http://$CHAIN_SERVER_2:8001/v1"
CHAIN_URL_S="http://$CHAIN_SERVER_2:8000/v1"

export NO_PROXY="localhost,127.0.0.1,$CHAIN_SERVER_1,$CHAIN_SERVER_2,$MUT_P,$MUT_Q,$MUT_R,$MUT_S,api.github.com"
export no_proxy="$NO_PROXY"
export PYTHONPATH="$PROJ"

echo "NO_PROXY=$NO_PROXY"
echo ""

cd "$PROJ"

# ── Preflight: server connectivity ────────────────────────────────────────────
echo "[preflight] Checking all 8 vLLM servers..."
for HOST_PORT in \
    "$CHAIN_SERVER_1:8001" \
    "$CHAIN_SERVER_1:8000" \
    "$CHAIN_SERVER_2:8001" \
    "$CHAIN_SERVER_2:8000" \
    "$MUT_P:8777" \
    "$MUT_Q:8777" \
    "$MUT_R:8777" \
    "$MUT_S:8777"; do
    HOST="${HOST_PORT%%:*}"
    PORT="${HOST_PORT##*:}"
    CTX=$(curl --noproxy "$HOST" --connect-timeout 10 -s "http://$HOST:$PORT/v1/models" \
          | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data'][0].get('max_model_len','?'))" 2>/dev/null || echo "FAIL")
    if [ "$CTX" = "FAIL" ]; then
        echo "[preflight] FAIL: $HOST:$PORT unreachable — aborting."
        exit 1
    fi
    echo "[preflight] OK:   $HOST:$PORT  ctx=$CTX"
done
echo ""

# ── Preflight: thinking mode on chain servers ──────────────────────────────────
echo "[preflight] Verifying thinking mode on chain servers..."
for CHAIN_URL in "$CHAIN_URL_P" "$CHAIN_URL_R"; do
    THINK_TEST=$("$PYTHON" -c "
import requests, os
resp = requests.post(
    '$CHAIN_URL/chat/completions',
    headers={'Authorization': 'Bearer None', 'Content-Type': 'application/json'},
    json={
        'model': 'Qwen/Qwen3-8B',
        'messages': [{'role': 'user', 'content': 'What is 2+2?'}],
        'max_tokens': 256,
        'temperature': 0.1,
    },
    timeout=90,
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
echo "[preflight] Checking Redis DBs 0-3..."
for DB in 0 1 2 3; do
    KEYS=$("$PYTHON" -c "import redis; r=redis.Redis(host='localhost',port=6379,db=$DB); print(r.dbsize())")
    if [ "$KEYS" -ne 0 ]; then
        echo "[preflight] FAIL: Redis DB $DB has $KEYS keys — flush first:"
        echo "  PYTHONPATH=. $PYTHON tools/flush.py --db $DB --confirm"
        exit 1
    fi
    echo "[preflight] DB $DB: empty."
done
echo ""

# ── Preflight: seed directory ──────────────────────────────────────────────────
if [ ! -d "$SEED_DIR/initial_programs" ]; then
    echo "[preflight] FAIL: seed dir $SEED_DIR/initial_programs not found."
    exit 1
fi
N=$(ls "$SEED_DIR/initial_programs/"*.py 2>/dev/null | wc -l)
echo "[preflight] Seed ddce37b4: $N program(s) found."
echo ""

# ── Preflight: dataset checksums ──────────────────────────────────────────────
echo "[preflight] Verifying dataset checksums..."
TRAIN_HASH=$(sha256sum "$PROJ/problems/chains/hotpotqa/dataset/HotpotQA_train.jsonl" | awk '{print $1}')
TEST_HASH=$(sha256sum "$PROJ/problems/chains/hotpotqa/dataset/HotpotQA_test.jsonl" | awk '{print $1}')
EXPECTED_TRAIN="9d8b0ba2a19d124fa243c88b650b2ecd42e5c771bc4e039553389c6b9566ef94"
EXPECTED_TEST="c46bfb185e448bf1b92cb75bb5ab967f3211051793967f01500f453945046b0d"
if [ "$TRAIN_HASH" != "$EXPECTED_TRAIN" ]; then
    echo "[preflight] FAIL: HotpotQA_train.jsonl checksum mismatch."
    exit 1
fi
if [ "$TEST_HASH" != "$EXPECTED_TEST" ]; then
    echo "[preflight] FAIL: HotpotQA_test.jsonl checksum mismatch."
    exit 1
fi
echo "[preflight] Dataset checksums OK."
echo ""

echo "============================================================"
echo "[launch] All preflight checks passed. Launching 4 runs."
DATE=$(date -u '+%Y-%m-%d %H:%M UTC')
echo "[launch] $DATE"
echo "============================================================"
echo ""

# ── Run P: F1+NLP+600, num_parents=1 [REPLICATION] ────────────────────────────
# CRITICAL: num_parents=1 (default=2) — must be explicit
HOTPOTQA_CHAIN_URL="$CHAIN_URL_P" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    redis.db=0 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url="http://$MUT_P:8777/v1" \
    program_loader.problem_dir="$SEED_DIR" \
    > "$LOG_DIR/run_P.log" 2>&1 &
PID_P=$!
echo "[launch] Run P (cross-P) started — PID=$PID_P  DB=0  F1+NLP+600  num_parents=1  chain=$CHAIN_URL_P  [REPLICATION]"
echo "$DATE — Run P PID=$PID_P" >> "$LOG_DIR/launch.log"

# ── Run Q: F1+NLP+600, num_parents=2 [CROSSOVER PRIMARY] ──────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_Q" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    redis.db=1 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=16 \
    max_elites_per_generation=8 \
    num_parents=2 \
    llm_base_url="http://$MUT_Q:8777/v1" \
    program_loader.problem_dir="$SEED_DIR" \
    > "$LOG_DIR/run_Q.log" 2>&1 &
PID_Q=$!
echo "[launch] Run Q (cross-Q) started — PID=$PID_Q  DB=1  F1+NLP+600  num_parents=2  chain=$CHAIN_URL_Q  [CROSSOVER PRIMARY]"
echo "$DATE — Run Q PID=$PID_Q" >> "$LOG_DIR/launch.log"

# ── Run R: F1+default+600, num_parents=2 ──────────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_R" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=2 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=16 \
    max_elites_per_generation=8 \
    num_parents=2 \
    llm_base_url="http://$MUT_R:8777/v1" \
    program_loader.problem_dir="$SEED_DIR" \
    > "$LOG_DIR/run_R.log" 2>&1 &
PID_R=$!
echo "[launch] Run R (cross-R) started — PID=$PID_R  DB=2  F1+default+600  num_parents=2  chain=$CHAIN_URL_R"
echo "$DATE — Run R PID=$PID_R" >> "$LOG_DIR/launch.log"

# ── Run S: F1+default+600, num_parents=1 [concurrent control for R] ───────────
# CRITICAL: num_parents=1 (default=2) — must be explicit
HOTPOTQA_CHAIN_URL="$CHAIN_URL_S" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=3 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url="http://$MUT_S:8777/v1" \
    program_loader.problem_dir="$SEED_DIR" \
    > "$LOG_DIR/run_S.log" 2>&1 &
PID_S=$!
echo "[launch] Run S (cross-S) started — PID=$PID_S  DB=3  F1+default+600  num_parents=1  chain=$CHAIN_URL_S  [control for R]"
echo "$DATE — Run S PID=$PID_S" >> "$LOG_DIR/launch.log"

echo ""
echo "[launch] All 4 runs started. Update run_status.sh with PIDs:"
echo "  sed -i \"s/FILL_P/$PID_P/; s/FILL_Q/$PID_Q/; s/FILL_R/$PID_R/; s/FILL_S/$PID_S/\" experiments/hotpotqa/crossover/run_status.sh"
echo ""
echo "[launch] Start watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/hotpotqa/crossover/run_watchdog.py \\"
echo "      > experiments/hotpotqa/crossover/watchdog.log 2>&1 &"
echo "  sleep 60 && kill -0 \$! && echo 'watchdog OK' || echo 'watchdog DEAD'"
echo ""
echo "[launch] Monitor:"
echo "  bash experiments/hotpotqa/crossover/run_status.sh"
