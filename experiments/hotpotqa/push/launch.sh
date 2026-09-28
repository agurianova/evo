#!/usr/bin/env bash
# Launch script for push experiment (GEPA attack — F1 × prompts × val-N, 4 runs).
#
# Run A — DB  8, F1 fitness,  NLP prompts, 300 samples, 50 gens  (push-A)
# Run B — DB  9, EM fitness,  default,     600 samples, 25 gens  (push-B)
# Run C — DB 10, F1 fitness,  default,     600 samples, 25 gens  (push-C) [PRIMARY]
# Run D — DB 11, EM fitness,  NLP prompts, 600 samples, 25 gens  (push-D)
#
# Chain servers (one dedicated per run):
#   Run A → 10.226.17.25:8001
#   Run B → 10.226.17.25:8000
#   Run C → 10.225.185.235:8001
#   Run D → 10.225.185.235:8000
#
# Mutation LLMs (one per run):
#   Run A → 10.226.72.211:8777
#   Run B → 10.226.15.38:8777
#   Run C → 10.226.185.131:8777
#   Run D → 10.225.51.251:8777
#
# Usage:
#   bash experiments/hotpotqa/push/launch.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-/home/jovyan/envs/evo_fast/bin/python}
LOG_DIR="$PROJ/experiments/hotpotqa/push"
SEED_DIR="$PROJ/experiments/hotpotqa/thinking/seeds/ddce37b4"

# ── Server IPs ─────────────────────────────────────────────────────────────────
CHAIN_SERVER_1="10.226.17.25"
CHAIN_SERVER_2="10.225.185.235"
MUT_A="10.226.72.211"
MUT_B="10.226.15.38"
MUT_C="10.226.185.131"
MUT_D="10.225.51.251"

CHAIN_URL_A="http://$CHAIN_SERVER_1:8001/v1"
CHAIN_URL_B="http://$CHAIN_SERVER_1:8000/v1"
CHAIN_URL_C="http://$CHAIN_SERVER_2:8001/v1"
CHAIN_URL_D="http://$CHAIN_SERVER_2:8000/v1"

export NO_PROXY="localhost,127.0.0.1,$CHAIN_SERVER_1,$CHAIN_SERVER_2,$MUT_A,$MUT_B,$MUT_C,$MUT_D,api.github.com"
export no_proxy="$NO_PROXY"
export PYTHONPATH="$PROJ"

echo "NO_PROXY=$NO_PROXY"
echo ""

# ── Preflight: server connectivity ────────────────────────────────────────────
echo "[preflight] Checking all 8 vLLM servers..."
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
for CHAIN_URL in "$CHAIN_URL_A" "$CHAIN_URL_C"; do
    THINK_TEST=$("$PYTHON" -c "
import requests, os
os.environ['no_proxy'] = os.environ.get('no_proxy', '')
resp = requests.post(
    '$CHAIN_URL/chat/completions',
    headers={'Authorization': 'Bearer None', 'Content-Type': 'application/json'},
    json={
        'model': 'Qwen/Qwen3-8B',
        'messages': [{'role': 'user', 'content': 'What is 2+2?'}],
        'max_tokens': 256,
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
echo "[preflight] Checking Redis DBs 8-11..."
for DB in 8 9 10 11; do
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
    echo "[preflight] FAIL: seed dir $SEED_DIR/initial_programs not found."
    exit 1
fi
N=$(ls "$SEED_DIR/initial_programs/"*.py 2>/dev/null | wc -l)
echo "[preflight] Seed ddce37b4: $N program(s)."
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

# ── Run A: F1 + NLP prompts + 300-sample, 50 gens ─────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_A" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_f1 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    redis.db=8 \
    stage_timeout=2400 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url="http://$MUT_A:8777/v1" \
    program_loader.problem_dir="$SEED_DIR" \
    > "$LOG_DIR/run_A.log" 2>&1 &
PID_A=$!
echo "[launch] Run A (push-A) started — PID=$PID_A  DB=8  F1+NLP+300  chain=$CHAIN_URL_A"
echo "$DATE — Run A PID=$PID_A" >> "$LOG_DIR/launch.log"

# ── Run B: EM + default + 600-sample, 25 gens ─────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_B" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=9 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url="http://$MUT_B:8777/v1" \
    program_loader.problem_dir="$SEED_DIR" \
    > "$LOG_DIR/run_B.log" 2>&1 &
PID_B=$!
echo "[launch] Run B (push-B) started — PID=$PID_B  DB=9  EM+default+600  chain=$CHAIN_URL_B"
echo "$DATE — Run B PID=$PID_B" >> "$LOG_DIR/launch.log"

# ── Run C: F1 + default + 600-sample, 25 gens [PRIMARY] ───────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_C" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=10 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url="http://$MUT_C:8777/v1" \
    program_loader.problem_dir="$SEED_DIR" \
    > "$LOG_DIR/run_C.log" 2>&1 &
PID_C=$!
echo "[launch] Run C (push-C) started — PID=$PID_C  DB=10  F1+default+600  chain=$CHAIN_URL_C  [PRIMARY]"
echo "$DATE — Run C PID=$PID_C" >> "$LOG_DIR/launch.log"

# ── Run D: EM + NLP prompts + 600-sample, 25 gens ─────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_D" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_600 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    redis.db=11 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url="http://$MUT_D:8777/v1" \
    program_loader.problem_dir="$SEED_DIR" \
    > "$LOG_DIR/run_D.log" 2>&1 &
PID_D=$!
echo "[launch] Run D (push-D) started — PID=$PID_D  DB=11  EM+NLP+600  chain=$CHAIN_URL_D"
echo "$DATE — Run D PID=$PID_D" >> "$LOG_DIR/launch.log"

echo ""
echo "[launch] All 4 runs started. Fill PIDs into run_status.sh:"
echo "  sed -i \"s/FILL_RUN_A_PID/$PID_A/; s/FILL_RUN_B_PID/$PID_B/; s/FILL_RUN_C_PID/$PID_C/; s/FILL_RUN_D_PID/$PID_D/\" experiments/hotpotqa/push/run_status.sh"
echo ""
echo "[launch] Monitor with:"
echo "  bash experiments/hotpotqa/push/run_status.sh"
echo "[launch] Or tail logs:"
echo "  tail -f experiments/hotpotqa/push/run_A.log"
