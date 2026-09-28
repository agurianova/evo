#!/usr/bin/env bash
# Launch script for hover baseline experiment — 4 cold-start runs (H1–H4).
#
# COLD START: NO program_loader.problem_dir override.
# program_loader resolves to problems/chains/hover/static/initial_programs/baseline.py
#
# Pre-registration commit: 9bcb905
# Branch: exp/hover-baseline
# PR: #90
#
# Usage: bash experiments/hover/baseline/launch.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=/home/jovyan/envs/evo_fast/bin/python
LOG_DIR="$PROJ/experiments/hover/baseline"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.47,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Chain LLM assignment (Qwen3-8B, one per run)
CHAIN_URL_H1="http://10.226.17.25:8001/v1"
CHAIN_URL_H2="http://10.226.17.25:8000/v1"
CHAIN_URL_H3="http://10.225.185.235:8001/v1"
CHAIN_URL_H4="http://10.225.185.235:8000/v1"

# Mutation LLM assignment (Qwen3-235B, one per run)
MUT_H1="10.226.72.211"
MUT_H2="10.226.15.38"
MUT_H3="10.226.185.47"
MUT_H4="10.225.51.251"

echo "================================================================"
echo "hover baseline experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: 9bcb905"
echo "COLD START: no program_loader.problem_dir override"
echo "================================================================"
echo ""

# ── Preflight: vLLM servers reachable ─────────────────────────────────────────
echo "[preflight] Checking all 8 vLLM servers..."
for ep in \
    "$CHAIN_URL_H1" "$CHAIN_URL_H2" "$CHAIN_URL_H3" "$CHAIN_URL_H4" \
    "http://$MUT_H1:8777/v1" "http://$MUT_H2:8777/v1" "http://$MUT_H3:8777/v1" "http://$MUT_H4:8777/v1"; do
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
for CHAIN_URL in "$CHAIN_URL_H1" "$CHAIN_URL_H2" "$CHAIN_URL_H3" "$CHAIN_URL_H4"; do
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
echo "[preflight] Checking Redis DBs 9–12..."
for db in 9 10 11 12; do
    keys=$(redis-cli -n $db DBSIZE | awk '{print $NF}')
    if [ "$keys" != "0" ]; then
        echo "[preflight] WARN: Redis DB $db has $keys keys — flush required."
        echo "  Run: PYTHONPATH=$PROJ $PYTHON $PROJ/tools/flush.py --db $db --confirm"
        exit 1
    fi
    echo "[preflight] OK: Redis DB $db empty"
done
echo ""

# ── Preflight: dataset checksums ──────────────────────────────────────────────
echo "[preflight] Verifying dataset checksums..."
TRAIN_SHA=$(sha256sum "$PROJ/problems/chains/hover/dataset/HoVer_train.jsonl" | awk '{print $1}')
TEST_SHA=$(sha256sum "$PROJ/problems/chains/hover/dataset/HoVer_test.jsonl" | awk '{print $1}')
EXPECTED_TRAIN="1bfc935d667e405a51cfb0361d1ee672fa3475d82714bcf027fc2d1a2c5cdcfa"
EXPECTED_TEST="1319ef6d1c16c879f4e8d3675df8ebf93be1387da6ee874d9fcdeaa0d56280a2"
[ "$TRAIN_SHA" = "$EXPECTED_TRAIN" ] && echo "[preflight] OK: HoVer_train.jsonl" || { echo "[preflight] FAIL: train checksum mismatch"; exit 1; }
[ "$TEST_SHA" = "$EXPECTED_TEST" ] && echo "[preflight] OK: HoVer_test.jsonl" || { echo "[preflight] FAIL: test checksum mismatch"; exit 1; }
echo ""

# ── Preflight: cold-start baseline program exists ────────────────────────────
echo "[preflight] Verifying cold-start baseline program..."
BASELINE="$PROJ/problems/chains/hover/static/initial_programs/baseline.py"
if [ ! -f "$BASELINE" ]; then
    echo "[preflight] FAIL: baseline.py not found at $BASELINE — aborting."
    exit 1
fi
echo "[preflight] OK: baseline.py found"
echo ""

# ── Preflight: confirm NO program_loader.problem_dir in launch commands ───────
echo "[preflight] Verifying NO program_loader.problem_dir= override..."
if grep -E "^\s+program_loader\.problem_dir=" "$0"; then
    echo "[preflight] FAIL: program_loader.problem_dir= found — cold start broken!"
    exit 1
fi
echo "[preflight] OK: no program_loader.problem_dir= override (cold start confirmed)"
echo ""

echo "================================================================"
echo "All preflight checks passed. Launching 4 cold-start runs..."
echo "================================================================"
echo ""

# ── Run H1: cold-start, host A port 8001 ──────────────────────────────────────
HOVER_CHAIN_URL="$CHAIN_URL_H1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/static \
    pipeline=guided \
    prompts=default \
    redis.db=9 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://$MUT_H1:8777/v1" \
    > "$LOG_DIR/run_H1.log" 2>&1 &
PID_H1=$!
echo "Run H1 started: PID=$PID_H1  DB=9  chain=$CHAIN_URL_H1  mut=$MUT_H1"

# ── Run H2: cold-start, host A port 8000 ──────────────────────────────────────
HOVER_CHAIN_URL="$CHAIN_URL_H2" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/static \
    pipeline=guided \
    prompts=default \
    redis.db=10 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://$MUT_H2:8777/v1" \
    > "$LOG_DIR/run_H2.log" 2>&1 &
PID_H2=$!
echo "Run H2 started: PID=$PID_H2  DB=10  chain=$CHAIN_URL_H2  mut=$MUT_H2"

# ── Run H3: cold-start, host B port 8001 ──────────────────────────────────────
HOVER_CHAIN_URL="$CHAIN_URL_H3" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/static \
    pipeline=guided \
    prompts=default \
    redis.db=11 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://$MUT_H3:8777/v1" \
    > "$LOG_DIR/run_H3.log" 2>&1 &
PID_H3=$!
echo "Run H3 started: PID=$PID_H3  DB=11  chain=$CHAIN_URL_H3  mut=$MUT_H3"

# ── Run H4: cold-start, host B port 8000 ──────────────────────────────────────
HOVER_CHAIN_URL="$CHAIN_URL_H4" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/static \
    pipeline=guided \
    prompts=default \
    redis.db=12 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://$MUT_H4:8777/v1" \
    > "$LOG_DIR/run_H4.log" 2>&1 &
PID_H4=$!
echo "Run H4 started: PID=$PID_H4  DB=12  chain=$CHAIN_URL_H4  mut=$MUT_H4"

echo ""
echo "================================================================"
echo "All 4 runs launched."
echo "PIDs: H1=$PID_H1  H2=$PID_H2  H3=$PID_H3  H4=$PID_H4"
echo ""
echo "GEN-0 SANITY CHECK (CRITICAL — cold start verification):"
echo "  Wait ~15 min then check Redis DB 9:"
echo "  redis-cli -n 9 HGET chains/hover/static:run_state engine:total_generations"
echo "  Val coverage at gen 0 must be < 20%. If > 20%, initialization error — abort."
echo ""
echo "Launch watchdog:"
cat <<WATCHDOG
  NO_PROXY="$NO_PROXY" no_proxy="$NO_PROXY" \\
  nohup $PYTHON \\
      experiments/hover/baseline/run_watchdog.py \\
      > experiments/hover/baseline/watchdog.log 2>&1 &
  sleep 60 && kill -0 \$! && echo "watchdog OK" || echo "watchdog DEAD"
WATCHDOG
echo ""
echo "PIDs: H1=$PID_H1  H2=$PID_H2  H3=$PID_H3  H4=$PID_H4"
echo "================================================================"
