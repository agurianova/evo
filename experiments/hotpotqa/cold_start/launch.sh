#!/usr/bin/env bash
# Launch script for cold_start experiment — 4 cold-start F1+default+600 runs (T1–T4).
#
# COLD START: NO program_loader.problem_dir override.
# program_loader resolves to problems/chains/hotpotqa/static_f1_600/initial_programs/baseline.py
#
# Pre-registration commit: bf0c969
# Branch: exp/hotpotqa-cold-start
# PR: #75
#
# Usage: bash experiments/hotpotqa/cold_start/launch.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=/home/jovyan/envs/evo_fast/bin/python
LOG_DIR="$PROJ/experiments/hotpotqa/cold_start"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Server assignment (host A = 10.226.17.25, host B = 10.225.185.235)
CHAIN_URL_T1="http://10.226.17.25:8001/v1"
CHAIN_URL_T2="http://10.226.17.25:8000/v1"
CHAIN_URL_T3="http://10.225.185.235:8001/v1"
CHAIN_URL_T4="http://10.225.185.235:8000/v1"

MUT_T1="10.226.72.211"
MUT_T2="10.226.15.38"
MUT_T3="10.226.185.131"
MUT_T4="10.225.51.251"

echo "================================================================"
echo "cold_start experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: bf0c969"
echo "COLD START: no program_loader.problem_dir override"
echo "================================================================"
echo ""

# ── Preflight: vLLM servers reachable ─────────────────────────────────────────
echo "[preflight] Checking all 8 vLLM servers..."
for ep in \
    "$CHAIN_URL_T1" "$CHAIN_URL_T2" "$CHAIN_URL_T3" "$CHAIN_URL_T4" \
    "http://$MUT_T1:8777/v1" "http://$MUT_T2:8777/v1" "http://$MUT_T3:8777/v1" "http://$MUT_T4:8777/v1"; do
    HOST="${ep#http://}"; HOST="${HOST%%/*}"; HOST="${HOST%%:*}"
    if curl --noproxy "$HOST" -sf --connect-timeout 8 --max-time 15 "${ep}/models" > /dev/null 2>&1; then
        echo "[preflight] OK: $ep"
    else
        echo "[preflight] FAIL: $ep — aborting."
        exit 1
    fi
done
echo "[preflight] All 8 servers reachable."
echo ""

# ── Preflight: thinking mode on chain servers ──────────────────────────────────
echo "[preflight] Verifying thinking mode on 4 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_T1" "$CHAIN_URL_T2" "$CHAIN_URL_T3" "$CHAIN_URL_T4"; do
    HOST="${CHAIN_URL#http://}"; HOST="${HOST%%/*}"; HOST="${HOST%%:*}"
    RESPONSE=$(curl --noproxy "$HOST" -s --connect-timeout 10 --max-time 90 \
        -X POST "$CHAIN_URL/chat/completions" \
        -H "Authorization: Bearer None" \
        -H "Content-Type: application/json" \
        -d '{"model":"Qwen/Qwen3-8B","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":200,"temperature":0.1}' \
        2>/dev/null || echo "CURL_FAIL")
    if echo "$RESPONSE" | grep -q "<think>"; then
        echo "[preflight] OK: $CHAIN_URL (thinking confirmed)"
    else
        echo "[preflight] FAIL: $CHAIN_URL NOT in thinking mode — aborting."
        exit 1
    fi
done
echo "[preflight] Thinking mode confirmed on all chain servers."
echo ""

# ── Preflight: Redis DBs 0–3 empty ────────────────────────────────────────────
echo "[preflight] Checking Redis DBs 0–3 are empty..."
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/flush.py" --db 0 1 2 3
for db in 0 1 2 3; do
    keys=$(redis-cli -n $db DBSIZE)
    if [ "$keys" -ne 0 ]; then
        echo "[preflight] FAIL: Redis DB $db has $keys keys — run flush.py --confirm first."
        exit 1
    fi
    echo "[preflight] OK: Redis DB $db empty"
done
echo ""

# ── Preflight: dataset checksums ──────────────────────────────────────────────
echo "[preflight] Verifying dataset checksums..."
TRAIN_SHA=$(sha256sum "$PROJ/problems/chains/hotpotqa/dataset/HotpotQA_train.jsonl" | awk '{print $1}')
TEST_SHA=$(sha256sum "$PROJ/problems/chains/hotpotqa/dataset/HotpotQA_test.jsonl" | awk '{print $1}')
EXPECTED_TRAIN="9d8b0ba2a19d124fa243c88b650b2ecd42e5c771bc4e039553389c6b9566ef94"
EXPECTED_TEST="c46bfb185e448bf1b92cb75bb5ab967f3211051793967f01500f453945046b0d"
[ "$TRAIN_SHA" = "$EXPECTED_TRAIN" ] && echo "[preflight] OK: HotpotQA_train.jsonl" || { echo "[preflight] FAIL: train checksum mismatch"; exit 1; }
[ "$TEST_SHA" = "$EXPECTED_TEST" ] && echo "[preflight] OK: HotpotQA_test.jsonl" || { echo "[preflight] FAIL: test checksum mismatch"; exit 1; }
echo ""

# ── Preflight: cold-start baseline program exists ────────────────────────────
echo "[preflight] Verifying cold-start baseline program..."
BASELINE="$PROJ/problems/chains/hotpotqa/static_f1_600/initial_programs/baseline.py"
if [ ! -f "$BASELINE" ]; then
    echo "[preflight] FAIL: baseline.py not found at $BASELINE — aborting."
    exit 1
fi
echo "[preflight] OK: baseline.py found"
echo ""

# ── Preflight: confirm NO program_loader.problem_dir in this script ───────────
echo "[preflight] Verifying NO program_loader.problem_dir= override in launch commands..."
# Check for actual Hydra override (key=value form), not mentions in comments/strings
if grep -E "^\s+program_loader\.problem_dir=" "$0"; then
    echo "[preflight] FAIL: program_loader.problem_dir= found in launch commands — cold start broken!"
    exit 1
fi
echo "[preflight] OK: no program_loader.problem_dir= override (cold start confirmed)"
echo ""

echo "================================================================"
echo "All preflight checks passed. Launching 4 cold-start runs..."
echo "================================================================"
echo ""

# ── Run T1: cold-start, host A port 8001 ──────────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_T1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=0 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url="http://$MUT_T1:8777/v1" \
    > "$LOG_DIR/run_T1.log" 2>&1 &
PID_T1=$!
echo "Run T1 started: PID=$PID_T1  DB=0  chain=$CHAIN_URL_T1  mut=$MUT_T1"

# ── Run T2: cold-start, host A port 8000 ──────────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_T2" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=1 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url="http://$MUT_T2:8777/v1" \
    > "$LOG_DIR/run_T2.log" 2>&1 &
PID_T2=$!
echo "Run T2 started: PID=$PID_T2  DB=1  chain=$CHAIN_URL_T2  mut=$MUT_T2"

# ── Run T3: cold-start, host B port 8001 ──────────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_T3" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=2 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url="http://$MUT_T3:8777/v1" \
    > "$LOG_DIR/run_T3.log" 2>&1 &
PID_T3=$!
echo "Run T3 started: PID=$PID_T3  DB=2  chain=$CHAIN_URL_T3  mut=$MUT_T3"

# ── Run T4: cold-start, host B port 8000 ──────────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_T4" nohup "$PYTHON" "$PROJ/run.py" \
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
    llm_base_url="http://$MUT_T4:8777/v1" \
    > "$LOG_DIR/run_T4.log" 2>&1 &
PID_T4=$!
echo "Run T4 started: PID=$PID_T4  DB=3  chain=$CHAIN_URL_T4  mut=$MUT_T4"

echo ""
echo "================================================================"
echo "All 4 runs launched."
echo "PIDs: T1=$PID_T1  T2=$PID_T2  T3=$PID_T3  T4=$PID_T4"
echo ""
echo "GEN-0 SANITY CHECK (CRITICAL — cold start verification):"
echo "  Wait ~10 min then check Redis DB 0:"
echo "  redis-cli -n 0 LRANGE chains/hotpotqa/static_f1_600:metrics:history:program_metrics:valid_iter_fitness_mean 0 0"
echo "  First val EM must be < 0.55 (expect ~0.42). If > 0.55, warm-start leaked — abort all runs."
echo ""
echo "Launch watchdog:"
cat <<WATCHDOG
  NO_PROXY="$NO_PROXY" no_proxy="$NO_PROXY" \\
  nohup $PYTHON \\
      experiments/hotpotqa/cold_start/run_watchdog.py \\
      > experiments/hotpotqa/cold_start/watchdog.log 2>&1 &
  sleep 60 && kill -0 \$! && echo "watchdog OK" || echo "watchdog DEAD"
WATCHDOG
echo ""
echo "Fill PIDs into run_status.sh:"
echo "  T1=$PID_T1  T2=$PID_T2  T3=$PID_T3  T4=$PID_T4"
echo "================================================================"
