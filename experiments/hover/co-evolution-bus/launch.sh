#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: PYTHONPATH=. $GIGAEVO_PYTHON tools/experiment/generate_launch.py --experiment hover/co-evolution-bus
#
# Experiment: hover/co-evolution-bus
# Branch: exp/hover-co-evolution-bus
# PR: #109
# Pre-reg commit: 01f7dfb
#
# Runs: B1, B2, B3, PM

set -euo pipefail

PROJ="/workspace-SR008.fs2/mathemage/gigaevo-core"
PYTHON="/home/jovyan/envs/evo_fast/bin/python"
LOG_DIR="$PROJ/experiments/hover/co-evolution-bus"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.47,10.225.51.251"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export HOVER_CHAIN_URL="per-run"

echo "================================================================"
echo "hover/co-evolution-bus experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: 01f7dfb"
echo "B1: Treatment: soft fitness + bus co-evolved prompts — pipeline=guided"
echo "B2: Treatment: soft fitness + bus co-evolved prompts — pipeline=guided"
echo "B3: Treatment: soft fitness + bus co-evolved prompts — pipeline=guided"
echo "PM: Prompt meta-evolution run (bus hub for B1+B2+B3) — pipeline=prompt_evolution_multi"
echo "================================================================"
echo ""

# ── Preflight check (hard gate) ──────────────────────────────────────────
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/experiment/preflight_check.py" --experiment hover/co-evolution-bus
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- B1 config ---"
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
    prompt_fetcher.prompt_redis_db=12 \
    prompt_fetcher.prompt_prefix=prompt_evolution_hover \
    --cfg job \
    > "$LOG_DIR/cfg_run_B1.txt" 2>&1
cat "$LOG_DIR/cfg_run_B1.txt" | head -40
echo ""
echo "--- B2 config ---"
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
    > "$LOG_DIR/cfg_run_B2.txt" 2>&1
cat "$LOG_DIR/cfg_run_B2.txt" | head -40
echo ""
echo "--- B3 config ---"
"$PYTHON" "$PROJ/run.py" \
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
    llm_base_url="http://10.226.185.47:8777/v1" \
    mutation_mode=rewrite \
    prompt_fetcher=coevolved \
    prompt_fetcher.prompt_redis_db=12 \
    prompt_fetcher.prompt_prefix=prompt_evolution_hover \
    --cfg job \
    > "$LOG_DIR/cfg_run_B3.txt" 2>&1
cat "$LOG_DIR/cfg_run_B3.txt" | head -40
echo ""
echo "--- PM config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=prompt_evolution_hover \
    pipeline=prompt_evolution_multi \
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
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    '+main_run_sources=[{db:9,prefix:chains/hover/static_soft},{db:10,prefix:chains/hover/static_soft},{db:11,prefix:chains/hover/static_soft}]' \
    --cfg job \
    > "$LOG_DIR/cfg_run_PM.txt" 2>&1
cat "$LOG_DIR/cfg_run_PM.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run B1: Treatment: soft fitness + bus co-evolved prompts
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
    prompt_fetcher.prompt_redis_db=12 \
    prompt_fetcher.prompt_prefix=prompt_evolution_hover \
    > "$LOG_DIR/run_B1.log" 2>&1 &
PID_B1=$!
echo "Run B1 started: PID=$PID_B1  DB=9  pipeline=guided"

# ── Run B2: Treatment: soft fitness + bus co-evolved prompts
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
    > "$LOG_DIR/run_B2.log" 2>&1 &
PID_B2=$!
echo "Run B2 started: PID=$PID_B2  DB=10  pipeline=guided"

# ── Run B3: Treatment: soft fitness + bus co-evolved prompts
HOVER_CHAIN_URL="http://10.226.17.25:8000/v1" nohup "$PYTHON" "$PROJ/run.py" \
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
    llm_base_url="http://10.226.185.47:8777/v1" \
    mutation_mode=rewrite \
    prompt_fetcher=coevolved \
    prompt_fetcher.prompt_redis_db=12 \
    prompt_fetcher.prompt_prefix=prompt_evolution_hover \
    > "$LOG_DIR/run_B3.log" 2>&1 &
PID_B3=$!
echo "Run B3 started: PID=$PID_B3  DB=11  pipeline=guided"

# ── Run PM: Prompt meta-evolution run (bus hub for B1+B2+B3)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=prompt_evolution_hover \
    pipeline=prompt_evolution_multi \
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
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    '+main_run_sources=[{db:9,prefix:chains/hover/static_soft},{db:10,prefix:chains/hover/static_soft},{db:11,prefix:chains/hover/static_soft}]' \
    > "$LOG_DIR/run_PM.log" 2>&1 &
PID_PM=$!
echo "Run PM started: PID=$PID_PM  DB=12  pipeline=prompt_evolution_multi"

echo ""
echo "================================================================"
echo "All 4 runs launched."
echo "PIDs: B1=$PID_B1  B2=$PID_B2  B3=$PID_B3  PM=$PID_PM"
echo "$PID_B1 $PID_B2 $PID_B3 $PID_PM" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_B1 2>/dev/null || { echo "DEAD: B1 (PID=$PID_B1)"; ALL_ALIVE=false; }
kill -0 $PID_B2 2>/dev/null || { echo "DEAD: B2 (PID=$PID_B2)"; ALL_ALIVE=false; }
kill -0 $PID_B3 2>/dev/null || { echo "DEAD: B3 (PID=$PID_B3)"; ALL_ALIVE=false; }
kill -0 $PID_PM 2>/dev/null || { echo "DEAD: PM (PID=$PID_PM)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e hover/co-evolution-bus manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "B1 B2 B3 PM"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/hover/co-evolution-bus/run_watchdog.py \\"
echo "      > experiments/hover/co-evolution-bus/watchdog.log 2>&1 &"
echo "================================================================"
