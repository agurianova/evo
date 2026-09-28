#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: PYTHONPATH=. $GIGAEVO_PYTHON tools/experiment/generate_launch.py --experiment hover/prompt_coevolution
#
# Experiment: hover/prompt_coevolution
# Branch: exp/hover-prompt-coevolution
# PR: #93
# Pre-reg commit: baee9bd
#
# Runs: C1, C2, P1, P2

set -euo pipefail

PROJ="/workspace-SR008.fs2/mathemage/gigaevo-core"
PYTHON="/home/jovyan/envs/evo_fast/bin/python"
LOG_DIR="$PROJ/experiments/hover/prompt_coevolution"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.47,10.225.51.251"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export HOVER_CHAIN_URL="per-run"

echo "================================================================"
echo "hover/prompt_coevolution experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: baee9bd"
echo "C1: Treatment: soft fitness + co-evolved prompts — pipeline=guided"
echo "C2: Treatment: soft fitness + co-evolved prompts — pipeline=guided"
echo "P1: Prompt evolution run paired with C1 — pipeline=prompt_evolution"
echo "P2: Prompt evolution run paired with C2 — pipeline=prompt_evolution"
echo "================================================================"
echo ""

# ── Preflight check (hard gate) ──────────────────────────────────────────
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/experiment/preflight_check.py" --experiment hover/prompt_coevolution
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- C1 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/static_soft \
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
    llm_base_url="http://10.226.72.211:8777/v1" \
    mutation_mode=rewrite \
    prompt_fetcher=coevolved \
    prompt_fetcher.prompt_redis_db=11 \
    prompt_fetcher.prompt_prefix=prompt_evolution_hover \
    --cfg job \
    > "$LOG_DIR/cfg_run_C1.txt" 2>&1
cat "$LOG_DIR/cfg_run_C1.txt" | head -40
echo ""
echo "--- C2 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/static_soft \
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
    llm_base_url="http://10.226.15.38:8777/v1" \
    mutation_mode=rewrite \
    prompt_fetcher=coevolved \
    prompt_fetcher.prompt_redis_db=12 \
    prompt_fetcher.prompt_prefix=prompt_evolution_hover \
    --cfg job \
    > "$LOG_DIR/cfg_run_C2.txt" 2>&1
cat "$LOG_DIR/cfg_run_C2.txt" | head -40
echo ""
echo "--- P1 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=prompt_evolution_hover \
    pipeline=prompt_evolution \
    prompts=default \
    redis.db=11 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.226.185.47:8777/v1" \
    mutation_mode=rewrite \
    main_redis_db=9 \
    main_redis_prefix=chains/hover/static_soft \
    max_elites_per_generation=5 \
    max_mutations_per_generation=2 \
    --cfg job \
    > "$LOG_DIR/cfg_run_P1.txt" 2>&1
cat "$LOG_DIR/cfg_run_P1.txt" | head -40
echo ""
echo "--- P2 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=prompt_evolution_hover \
    pipeline=prompt_evolution \
    prompts=default \
    redis.db=12 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.225.51.251:8777/v1" \
    mutation_mode=rewrite \
    main_redis_db=10 \
    main_redis_prefix=chains/hover/static_soft \
    max_elites_per_generation=5 \
    max_mutations_per_generation=2 \
    --cfg job \
    > "$LOG_DIR/cfg_run_P2.txt" 2>&1
cat "$LOG_DIR/cfg_run_P2.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run C1: Treatment: soft fitness + co-evolved prompts
HOVER_CHAIN_URL="http://10.226.17.25:8001/v1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/static_soft \
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
    llm_base_url="http://10.226.72.211:8777/v1" \
    mutation_mode=rewrite \
    prompt_fetcher=coevolved \
    prompt_fetcher.prompt_redis_db=11 \
    prompt_fetcher.prompt_prefix=prompt_evolution_hover \
    > "$LOG_DIR/run_C1.log" 2>&1 &
PID_C1=$!
echo "Run C1 started: PID=$PID_C1  DB=9  pipeline=guided"

# ── Run C2: Treatment: soft fitness + co-evolved prompts
HOVER_CHAIN_URL="http://10.225.185.235:8001/v1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/static_soft \
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
    llm_base_url="http://10.226.15.38:8777/v1" \
    mutation_mode=rewrite \
    prompt_fetcher=coevolved \
    prompt_fetcher.prompt_redis_db=12 \
    prompt_fetcher.prompt_prefix=prompt_evolution_hover \
    > "$LOG_DIR/run_C2.log" 2>&1 &
PID_C2=$!
echo "Run C2 started: PID=$PID_C2  DB=10  pipeline=guided"

# ── Run P1: Prompt evolution run paired with C1
HOVER_CHAIN_URL="None" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=prompt_evolution_hover \
    pipeline=prompt_evolution \
    prompts=default \
    redis.db=11 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.226.185.47:8777/v1" \
    mutation_mode=rewrite \
    main_redis_db=9 \
    main_redis_prefix=chains/hover/static_soft \
    max_elites_per_generation=5 \
    max_mutations_per_generation=2 \
    > "$LOG_DIR/run_P1.log" 2>&1 &
PID_P1=$!
echo "Run P1 started: PID=$PID_P1  DB=11  pipeline=prompt_evolution"

# ── Run P2: Prompt evolution run paired with C2
HOVER_CHAIN_URL="None" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=prompt_evolution_hover \
    pipeline=prompt_evolution \
    prompts=default \
    redis.db=12 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.225.51.251:8777/v1" \
    mutation_mode=rewrite \
    main_redis_db=10 \
    main_redis_prefix=chains/hover/static_soft \
    max_elites_per_generation=5 \
    max_mutations_per_generation=2 \
    > "$LOG_DIR/run_P2.log" 2>&1 &
PID_P2=$!
echo "Run P2 started: PID=$PID_P2  DB=12  pipeline=prompt_evolution"

echo ""
echo "================================================================"
echo "All 4 runs launched."
echo "PIDs: C1=$PID_C1  C2=$PID_C2  P1=$PID_P1  P2=$PID_P2"
echo "$PID_C1 $PID_C2 $PID_P1 $PID_P2" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_C1 2>/dev/null || { echo "DEAD: C1 (PID=$PID_C1)"; ALL_ALIVE=false; }
kill -0 $PID_C2 2>/dev/null || { echo "DEAD: C2 (PID=$PID_C2)"; ALL_ALIVE=false; }
kill -0 $PID_P1 2>/dev/null || { echo "DEAD: P1 (PID=$PID_P1)"; ALL_ALIVE=false; }
kill -0 $PID_P2 2>/dev/null || { echo "DEAD: P2 (PID=$PID_P2)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e hover/prompt_coevolution manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "C1 C2 P1 P2"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/hover/prompt_coevolution/run_watchdog.py \\"
echo "      > experiments/hover/prompt_coevolution/watchdog.log 2>&1 &"
echo "================================================================"
