#!/usr/bin/env bash
# Launch script for prompt_coevolution experiment — 3 main runs (X1, X2, X3) + 1 prompt run (P1).
#
# X1/X2/X3 — HotpotQA chain evolution with co-evolved mutation prompts from P1
# P1 — Prompt evolution run (1-to-many: aggregates stats from X1+X2+X3)
#
# Pre-registration commit: 4ccb787
# Branch: exp/prompt_coevolution
# PR: #84
#
# MANDATORY: Run 3-gen smoke test before full launch.
# Usage: bash experiments/hotpotqa/prompt_coevolution/launch.sh [--smoke-test]

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=/home/jovyan/envs/evo_fast/bin/python
LOG_DIR="$PROJ/experiments/hotpotqa/prompt_coevolution"

SMOKE_TEST=0
if [[ "${1:-}" == "--smoke-test" ]]; then
    SMOKE_TEST=1
fi

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.47,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"
export PYTHONPATH="$PROJ"

# Chain LLMs (Qwen3-8B, thinking ON) — one per main run
CHAIN_URL_X1="http://10.226.17.25:8001/v1"
CHAIN_URL_X2="http://10.226.17.25:8000/v1"
CHAIN_URL_X3="http://10.225.185.235:8001/v1"

# Mutation LLMs (Qwen3-235B-A22B-Thinking) — one per run
MUT_X1="10.226.72.211"
MUT_X2="10.226.15.38"
MUT_X3="10.226.185.47"
MUT_P1="10.225.51.251"

# Redis DBs
DB_X1=4
DB_X2=5
DB_X3=8
DB_P1=6

MAIN_PREFIX="chains/hotpotqa/static_f1_600"
PROMPT_PREFIX="prompt_evolution"

# Multi-source config for P1 (aggregates from all 3 main runs)
MAIN_RUN_SOURCES="[{db:${DB_X1},prefix:${MAIN_PREFIX}},{db:${DB_X2},prefix:${MAIN_PREFIX}},{db:${DB_X3},prefix:${MAIN_PREFIX}}]"

if [[ "$SMOKE_TEST" == "1" ]]; then
    echo "================================================================"
    echo "SMOKE TEST — 3 generations, X1+X2+X3+P1 (full topology)"
    echo "================================================================"
    MAX_GEN=3
else
    echo "================================================================"
    echo "prompt_coevolution experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
    echo "Pre-reg commit: 4ccb787  PR: #84"
    echo "Topology: 3 main (X1/X2/X3) + 1 prompt (P1, multi-source)"
    echo "================================================================"
    MAX_GEN=25
fi
echo ""

# ── Preflight: vLLM servers reachable ─────────────────────────────────────────
echo "[preflight] Checking vLLM servers..."
for ep in "$CHAIN_URL_X1" "$CHAIN_URL_X2" "$CHAIN_URL_X3" \
          "http://$MUT_X1:8777/v1" "http://$MUT_X2:8777/v1" \
          "http://$MUT_X3:8777/v1" "http://$MUT_P1:8777/v1"; do
    HOST="${ep#http://}"; HOST="${HOST%%/*}"; HOST="${HOST%%:*}"
    if curl --noproxy "$HOST" -sf --connect-timeout 8 --max-time 15 "${ep}/models" > /dev/null 2>&1; then
        echo "[preflight] OK: $ep"
    else
        echo "[preflight] FAIL: $ep — aborting."
        exit 1
    fi
done
echo "[preflight] All servers reachable."
echo ""

# ── Preflight: thinking mode on chain servers ──────────────────────────────────
echo "[preflight] Verifying thinking mode on chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_X1" "$CHAIN_URL_X2" "$CHAIN_URL_X3"; do
    HOST="${CHAIN_URL#http://}"; HOST="${HOST%%/*}"; HOST="${HOST%%:*}"
    RESPONSE=$(curl --noproxy "$HOST" -s --connect-timeout 10 --max-time 180 \
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
echo "[preflight] Thinking mode confirmed."
echo ""

# ── Preflight: Redis DBs empty ────────────────────────────────────────────
echo "[preflight] Checking Redis DBs $DB_X1 $DB_X2 $DB_X3 $DB_P1 are empty..."
"$PYTHON" "$PROJ/tools/flush.py" --db $DB_X1 $DB_X2 $DB_X3 $DB_P1
for db in $DB_X1 $DB_X2 $DB_X3 $DB_P1; do
    KEY_COUNT=$(redis-cli -n "$db" DBSIZE)
    if [[ "$KEY_COUNT" != "0" ]]; then
        echo "[preflight] FAIL: Redis DB $db has $KEY_COUNT keys — run flush.py --confirm first"
        exit 1
    fi
done
echo "[preflight] Redis DBs are empty."
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────────
echo "[config] Verifying run configs..."
echo "--- X1 config ---"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_X1" "$PYTHON" "$PROJ/run.py" \
    problem.name=$MAIN_PREFIX \
    pipeline=hotpotqa_asi \
    prompts=default \
    prompt_fetcher=coevolved \
    prompt_fetcher.prompt_redis_db=$DB_P1 \
    redis.db=$DB_X1 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    max_generations=$MAX_GEN \
    num_parents=1 \
    llm_base_url="http://$MUT_X1:8777/v1" \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    --cfg job 2>&1 | head -40
echo ""
echo "--- P1 config (multi-source) ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=$PROMPT_PREFIX \
    pipeline=prompt_evolution_multi \
    redis.db=$DB_P1 \
    "+main_run_sources=$MAIN_RUN_SOURCES" \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_mutations_per_generation=3 \
    max_elites_per_generation=3 \
    max_generations=$MAX_GEN \
    num_parents=1 \
    llm_base_url="http://$MUT_P1:8777/v1" \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    --cfg job 2>&1 | head -40

echo ""
echo "[config] Configs verified. Launching runs..."
# read -r  # Skipped for non-interactive launch

# ── Launch runs ────────────────────────────────────────────────────────────────

# Prompt logging directory (set env var to enable file dumps of mutation prompts)
PROMPT_LOG_BASE="$LOG_DIR/prompt_logs"
mkdir -p "$PROMPT_LOG_BASE"

# Run X1 — main HotpotQA run, co-evolved prompts from P1 (DB 6)
HOTPOTQA_CHAIN_URL="$CHAIN_URL_X1" GIGAEVO_PROMPT_LOG_DIR="$PROMPT_LOG_BASE/X1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=$MAIN_PREFIX \
    pipeline=hotpotqa_asi \
    prompts=default \
    prompt_fetcher=coevolved \
    prompt_fetcher.prompt_redis_db=$DB_P1 \
    redis.db=$DB_X1 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    max_generations=$MAX_GEN \
    num_parents=1 \
    llm_base_url="http://$MUT_X1:8777/v1" \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    > "$LOG_DIR/run_X1.log" 2>&1 &
PID_X1=$!
echo "Run X1 started: PID=$PID_X1  DB=$DB_X1  chain=$CHAIN_URL_X1  mut=$MUT_X1  prompt_db=$DB_P1"

# Run X2 — main HotpotQA run, co-evolved prompts from P1 (DB 6)
HOTPOTQA_CHAIN_URL="$CHAIN_URL_X2" GIGAEVO_PROMPT_LOG_DIR="$PROMPT_LOG_BASE/X2" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=$MAIN_PREFIX \
    pipeline=hotpotqa_asi \
    prompts=default \
    prompt_fetcher=coevolved \
    prompt_fetcher.prompt_redis_db=$DB_P1 \
    redis.db=$DB_X2 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    max_generations=$MAX_GEN \
    num_parents=1 \
    llm_base_url="http://$MUT_X2:8777/v1" \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    > "$LOG_DIR/run_X2.log" 2>&1 &
PID_X2=$!
echo "Run X2 started: PID=$PID_X2  DB=$DB_X2  chain=$CHAIN_URL_X2  mut=$MUT_X2  prompt_db=$DB_P1"

# Run X3 — main HotpotQA run, co-evolved prompts from P1 (DB 6)
HOTPOTQA_CHAIN_URL="$CHAIN_URL_X3" GIGAEVO_PROMPT_LOG_DIR="$PROMPT_LOG_BASE/X3" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=$MAIN_PREFIX \
    pipeline=hotpotqa_asi \
    prompts=default \
    prompt_fetcher=coevolved \
    prompt_fetcher.prompt_redis_db=$DB_P1 \
    redis.db=$DB_X3 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    max_generations=$MAX_GEN \
    num_parents=1 \
    llm_base_url="http://$MUT_X3:8777/v1" \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    > "$LOG_DIR/run_X3.log" 2>&1 &
PID_X3=$!
echo "Run X3 started: PID=$PID_X3  DB=$DB_X3  chain=$CHAIN_URL_X3  mut=$MUT_X3  prompt_db=$DB_P1"

# Run P1 — prompt evolution run, multi-source (reads stats from X1+X2+X3)
GIGAEVO_PROMPT_LOG_DIR="$PROMPT_LOG_BASE/P1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=$PROMPT_PREFIX \
    pipeline=prompt_evolution_multi \
    redis.db=$DB_P1 \
    "+main_run_sources=$MAIN_RUN_SOURCES" \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_mutations_per_generation=3 \
    max_elites_per_generation=3 \
    max_generations=$MAX_GEN \
    num_parents=1 \
    llm_base_url="http://$MUT_P1:8777/v1" \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    > "$LOG_DIR/run_P1.log" 2>&1 &
PID_P1=$!
echo "Run P1 started: PID=$PID_P1  DB=$DB_P1  sources=X1+X2+X3  mut=$MUT_P1"

echo ""
echo "================================================================"
echo "All 4 runs launched (3 main + 1 prompt)."
echo "PIDs: X1=$PID_X1  X2=$PID_X2  X3=$PID_X3  P1=$PID_P1"
echo ""

if [[ "$SMOKE_TEST" == "1" ]]; then
    echo "SMOKE TEST (max_gen=3). After ~10 min, verify:"
    echo "  1. redis-cli -n $DB_X1 keys '${MAIN_PREFIX}:prompt_stats:*'"
    echo "     → must return at least 1 key"
    echo "  2. redis-cli -n $DB_P1 hgetall 'island_fitness_island:archive'"
    echo "     → must have at least 1 entry"
    echo "  3. Check run_X1.log for 'has_champion = True' by gen 3"
    echo "  4. If all checks pass: re-run without --smoke-test for full launch"
else
    echo "Record these PIDs in 03_plan.md Actual Launch Record."
    echo ""
    echo "Launch watchdog:"
    cat << WATCHDOG
  nohup $PYTHON \\
      experiments/hotpotqa/prompt_coevolution/run_watchdog.py \\
      > experiments/hotpotqa/prompt_coevolution/watchdog.log 2>&1 &
  sleep 60 && kill -0 \$! && echo "watchdog OK" || echo "watchdog DEAD"
WATCHDOG
    echo ""
    echo "Gen 3 smoke check (after ~10 min):"
    echo "  redis-cli -n $DB_X1 keys '${MAIN_PREFIX}:prompt_stats:*'"
    echo "  redis-cli -n $DB_P1 hgetall 'island_fitness_island:archive'"
    echo "  grep 'has_champion' $LOG_DIR/run_X1.log | tail -5"
fi
echo "================================================================"
