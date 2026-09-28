#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: PYTHONPATH=. $GIGAEVO_PYTHON tools/experiment/generate_launch.py --experiment hover/dynamic-topology
#
# Experiment: hover/dynamic-topology
# Branch: exp/hover-dynamic-topology
# PR: #116
# Pre-reg commit: 1c58729
#
# Runs: D1, D2, D5, D6

set -euo pipefail

PROJ="/workspace-SR008.fs2/mathemage/gigaevo-core"
PYTHON="/home/jovyan/envs/evo_fast/bin/python"
LOG_DIR="$PROJ/experiments/hover/dynamic-topology"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.47,10.225.51.251"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export HOVER_CHAIN_URL="per_run"

echo "================================================================"
echo "hover/dynamic-topology experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: 1c58729"
echo "D1: control — pipeline=guided"
echo "D2: control — pipeline=guided"
echo "D5: treatment — pipeline=guided"
echo "D6: treatment — pipeline=guided"
echo "================================================================"
echo ""

# ── Preflight check (hard gate) ──────────────────────────────────────────
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/experiment/preflight_check.py" --experiment hover/dynamic-topology
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- D1 config ---"
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
    --cfg job \
    > "$LOG_DIR/cfg_run_D1.txt" 2>&1
cat "$LOG_DIR/cfg_run_D1.txt" | head -40
echo ""
echo "--- D2 config ---"
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
    --cfg job \
    > "$LOG_DIR/cfg_run_D2.txt" 2>&1
cat "$LOG_DIR/cfg_run_D2.txt" | head -40
echo ""
echo "--- D5 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=13 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.226.185.47:8777/v1" \
    mutation_mode=rewrite \
    --cfg job \
    > "$LOG_DIR/cfg_run_D5.txt" 2>&1
cat "$LOG_DIR/cfg_run_D5.txt" | head -40
echo ""
echo "--- D6 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=14 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.225.51.251:8777/v1" \
    mutation_mode=rewrite \
    --cfg job \
    > "$LOG_DIR/cfg_run_D6.txt" 2>&1
cat "$LOG_DIR/cfg_run_D6.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run D1: control
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
    > "$LOG_DIR/logs/D1.log" 2>&1 &
PID_D1=$!
echo "Run D1 started: PID=$PID_D1  DB=9  pipeline=guided"

# ── Run D2: control
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
    > "$LOG_DIR/logs/D2.log" 2>&1 &
PID_D2=$!
echo "Run D2 started: PID=$PID_D2  DB=10  pipeline=guided"

# ── Run D5: treatment
HOVER_CHAIN_URL="http://10.226.17.25:8000/v1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=13 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.226.185.47:8777/v1" \
    mutation_mode=rewrite \
    > "$LOG_DIR/logs/D5.log" 2>&1 &
PID_D5=$!
echo "Run D5 started: PID=$PID_D5  DB=13  pipeline=guided"

# ── Run D6: treatment
HOVER_CHAIN_URL="http://10.225.185.235:8000/v1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=14 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.225.51.251:8777/v1" \
    mutation_mode=rewrite \
    > "$LOG_DIR/logs/D6.log" 2>&1 &
PID_D6=$!
echo "Run D6 started: PID=$PID_D6  DB=14  pipeline=guided"

echo ""
echo "================================================================"
echo "All 4 runs launched."
echo "PIDs: D1=$PID_D1  D2=$PID_D2  D5=$PID_D5  D6=$PID_D6"
echo "$PID_D1 $PID_D2 $PID_D5 $PID_D6" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_D1 2>/dev/null || { echo "DEAD: D1 (PID=$PID_D1)"; ALL_ALIVE=false; }
kill -0 $PID_D2 2>/dev/null || { echo "DEAD: D2 (PID=$PID_D2)"; ALL_ALIVE=false; }
kill -0 $PID_D5 2>/dev/null || { echo "DEAD: D5 (PID=$PID_D5)"; ALL_ALIVE=false; }
kill -0 $PID_D6 2>/dev/null || { echo "DEAD: D6 (PID=$PID_D6)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e hover/dynamic-topology manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "D1 D2 D5 D6"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/hover/dynamic-topology/run_watchdog.py \\"
echo "      > experiments/hover/dynamic-topology/watchdog.log 2>&1 &"
echo "================================================================"
