#!/usr/bin/env bash
# Launch script for hover feedback_softfit experiment — 4 runs (F1-F4).
#
# 2x2 factorial: Cell B (feedback, discrete) and Cell C (soft fitness, no feedback).
# Cell D (feedback + soft) deferred.
#
# F1, F2: pipeline=hover_feedback, problem.name=chains/hover/static
# F3, F4: pipeline=guided,       problem.name=chains/hover/static_soft
#
# COLD START: NO program_loader.problem_dir override.
#
# Pre-registration commit: 5f07a3b
# Branch: exp/hover-feedback-softfit
# PR: #92
#
# Usage: bash experiments/hover/feedback_softfit/launch.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=/home/jovyan/envs/evo_fast/bin/python
LOG_DIR="$PROJ/experiments/hover/feedback_softfit"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.47,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Chain LLM assignment (Qwen3-8B) — shuffled: each cell has one run per host
CHAIN_URL_F1="http://10.226.17.25:8001/v1"      # Cell B, host A
CHAIN_URL_F2="http://10.225.185.235:8001/v1"     # Cell B, host B
CHAIN_URL_F3="http://10.226.17.25:8000/v1"       # Cell C, host A
CHAIN_URL_F4="http://10.225.185.235:8000/v1"     # Cell C, host B

# Mutation LLM assignment (Qwen3-235B, one per run)
MUT_F1="10.226.72.211"
MUT_F2="10.226.15.38"
MUT_F3="10.226.185.47"
MUT_F4="10.225.51.251"

echo "================================================================"
echo "hover feedback_softfit experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: 5f07a3b"
echo "COLD START: no program_loader.problem_dir override"
echo "F1,F2: Cell B (feedback + discrete) — pipeline=hover_feedback"
echo "F3,F4: Cell C (soft fitness, no feedback) — pipeline=guided"
echo "================================================================"
echo ""

# ── Preflight: vLLM servers reachable ─────────────────────────────────────────
echo "[preflight] Checking all 8 vLLM servers..."
for ep in \
    "$CHAIN_URL_F1" "$CHAIN_URL_F2" "$CHAIN_URL_F3" "$CHAIN_URL_F4" \
    "http://$MUT_F1:8777/v1" "http://$MUT_F2:8777/v1" "http://$MUT_F3:8777/v1" "http://$MUT_F4:8777/v1"; do
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
for CHAIN_URL in "$CHAIN_URL_F1" "$CHAIN_URL_F2" "$CHAIN_URL_F3" "$CHAIN_URL_F4"; do
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

# ── Preflight: Redis DBs 9–12 empty ────────────────────────────────────────────
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

# ── Preflight: initial programs ──────────────────────────────────────────────
echo "[preflight] Verifying initial programs..."
BASELINE_STATIC="$PROJ/problems/chains/hover/static/initial_programs/baseline.py"
BASELINE_SOFT="$PROJ/problems/chains/hover/static_soft/initial_programs/baseline.py"
[ -f "$BASELINE_STATIC" ] && echo "[preflight] OK: static/baseline.py found" || { echo "[preflight] FAIL: static baseline missing"; exit 1; }
[ -f "$BASELINE_SOFT" ] && echo "[preflight] OK: static_soft/baseline.py found" || { echo "[preflight] FAIL: static_soft baseline missing"; exit 1; }
SHA_STATIC=$(sha256sum "$BASELINE_STATIC" | awk '{print $1}')
SHA_SOFT=$(sha256sum "$BASELINE_SOFT" | awk '{print $1}')
[ "$SHA_STATIC" = "$SHA_SOFT" ] && echo "[preflight] OK: baselines byte-identical" || { echo "[preflight] FAIL: baselines differ!"; exit 1; }
echo ""

# ── Preflight: test.py unchanged ──────────────────────────────────────────────
echo "[preflight] Verifying test.py integrity..."
TEST_PY_SHA=$(sha256sum "$PROJ/problems/chains/hover/static/test.py" | awk '{print $1}')
EXPECTED_TEST_PY="95c735868957de483926ca5a317d1b37f853ff534be10fccea755660c2275307"
[ "$TEST_PY_SHA" = "$EXPECTED_TEST_PY" ] && echo "[preflight] OK: test.py SHA matches" || { echo "[preflight] FAIL: test.py changed!"; exit 1; }
echo ""

echo "================================================================"
echo "All preflight checks passed. Launching 4 cold-start runs..."
echo "================================================================"
echo ""

# ── Run F1: Cell B (feedback + discrete), host A ──────────────────────────────
HOVER_CHAIN_URL="$CHAIN_URL_F1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/static \
    pipeline=hover_feedback \
    prompts=default \
    redis.db=9 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://$MUT_F1:8777/v1" \
    > "$LOG_DIR/run_F1.log" 2>&1 &
PID_F1=$!
echo "Run F1 started: PID=$PID_F1  DB=9  cell=B(feedback)  chain=$CHAIN_URL_F1  mut=$MUT_F1"

# ── Run F2: Cell B (feedback + discrete), host B ──────────────────────────────
HOVER_CHAIN_URL="$CHAIN_URL_F2" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/static \
    pipeline=hover_feedback \
    prompts=default \
    redis.db=10 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://$MUT_F2:8777/v1" \
    > "$LOG_DIR/run_F2.log" 2>&1 &
PID_F2=$!
echo "Run F2 started: PID=$PID_F2  DB=10  cell=B(feedback)  chain=$CHAIN_URL_F2  mut=$MUT_F2"

# ── Run F3: Cell C (soft fitness), host A ──────────────────────────────────────
HOVER_CHAIN_URL="$CHAIN_URL_F3" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/static_soft \
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
    llm_base_url="http://$MUT_F3:8777/v1" \
    > "$LOG_DIR/run_F3.log" 2>&1 &
PID_F3=$!
echo "Run F3 started: PID=$PID_F3  DB=11  cell=C(soft)  chain=$CHAIN_URL_F3  mut=$MUT_F3"

# ── Run F4: Cell C (soft fitness), host B ──────────────────────────────────────
HOVER_CHAIN_URL="$CHAIN_URL_F4" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/static_soft \
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
    llm_base_url="http://$MUT_F4:8777/v1" \
    > "$LOG_DIR/run_F4.log" 2>&1 &
PID_F4=$!
echo "Run F4 started: PID=$PID_F4  DB=12  cell=C(soft)  chain=$CHAIN_URL_F4  mut=$MUT_F4"

echo ""
echo "================================================================"
echo "All 4 runs launched."
echo "PIDs: F1=$PID_F1  F2=$PID_F2  F3=$PID_F3  F4=$PID_F4"
echo ""
echo "GEN-0 SANITY CHECK (CRITICAL — cold start verification):"
echo "  Wait ~15 min then check:"
echo "  redis-cli -n 9 HGET chains/hover/static:run_state engine:total_generations"
echo "  redis-cli -n 11 HGET chains/hover/static_soft:run_state engine:total_generations"
echo "  Val coverage at gen 0 must be < 20%."
echo ""
echo "Launch watchdog:"
cat <<WATCHDOG
  NO_PROXY="$NO_PROXY" no_proxy="$NO_PROXY" \\
  nohup $PYTHON \\
      experiments/hover/feedback_softfit/run_watchdog.py \\
      > experiments/hover/feedback_softfit/watchdog.log 2>&1 &
  sleep 60 && kill -0 \$! && echo "watchdog OK" || echo "watchdog DEAD"
WATCHDOG
echo ""
echo "PIDs: F1=$PID_F1  F2=$PID_F2  F3=$PID_F3  F4=$PID_F4"
echo "================================================================"
