#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: PYTHONPATH=. $GIGAEVO_PYTHON tools/experiment/generate_launch.py --experiment hover/steady-state-v2
#
# Experiment: hover/steady-state-v2
# Branch: exp/hover-steady-state-v2
# PR: #138
# Pre-reg commit: 3e4faf3
#
# Runs: V1, V2, V3, V4

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/hover/steady-state-v2"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.232.30.185,10.232.45.196,10.232.90.109,10.232.38.220,10.232.22.232,10.232.21.74"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export OPENAI_API_KEY="sk-gigaevo"

echo "================================================================"
echo "hover/steady-state-v2 experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: 3e4faf3"
echo "V1: control — pipeline=guided"
echo "V2: control — pipeline=guided"
echo "V3: treatment — pipeline=guided"
echo "V4: treatment — pipeline=guided"
echo "================================================================"
echo ""

# ── Preflight check (hard gate) ──────────────────────────────────────────
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/experiment/preflight_check.py" --experiment hover/steady-state-v2
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- V1 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=3 \
    stage_timeout=6000 \
    dag_timeout=14400 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    --cfg job \
    > "$LOG_DIR/cfg_run_V1.txt" 2>&1
cat "$LOG_DIR/cfg_run_V1.txt" | head -40
echo ""
echo "--- V2 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=4 \
    stage_timeout=6000 \
    dag_timeout=14400 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    --cfg job \
    > "$LOG_DIR/cfg_run_V2.txt" 2>&1
cat "$LOG_DIR/cfg_run_V2.txt" | head -40
echo ""
echo "--- V3 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=5 \
    stage_timeout=6000 \
    dag_timeout=14400 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt \
    --cfg job \
    > "$LOG_DIR/cfg_run_V3.txt" 2>&1
cat "$LOG_DIR/cfg_run_V3.txt" | head -40
echo ""
echo "--- V4 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=6 \
    stage_timeout=6000 \
    dag_timeout=14400 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt \
    --cfg job \
    > "$LOG_DIR/cfg_run_V4.txt" 2>&1
cat "$LOG_DIR/cfg_run_V4.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run V1: control
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=3 \
    stage_timeout=6000 \
    dag_timeout=14400 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    > "$LOG_DIR/logs/V1.log" 2>&1 &
PID_V1=$!
echo "Run V1 started: PID=$PID_V1  DB=3  pipeline=guided"

# ── Run V2: control
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=4 \
    stage_timeout=6000 \
    dag_timeout=14400 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    > "$LOG_DIR/logs/V2.log" 2>&1 &
PID_V2=$!
echo "Run V2 started: PID=$PID_V2  DB=4  pipeline=guided"

# ── Run V3: treatment
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=5 \
    stage_timeout=6000 \
    dag_timeout=14400 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt \
    > "$LOG_DIR/logs/V3.log" 2>&1 &
PID_V3=$!
echo "Run V3 started: PID=$PID_V3  DB=5  pipeline=guided"

# ── Run V4: treatment
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=6 \
    stage_timeout=6000 \
    dag_timeout=14400 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt \
    > "$LOG_DIR/logs/V4.log" 2>&1 &
PID_V4=$!
echo "Run V4 started: PID=$PID_V4  DB=6  pipeline=guided"

echo ""
echo "================================================================"
echo "All 4 runs launched."
echo "PIDs: V1=$PID_V1  V2=$PID_V2  V3=$PID_V3  V4=$PID_V4"
echo "$PID_V1 $PID_V2 $PID_V3 $PID_V4" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_V1 2>/dev/null || { echo "DEAD: V1 (PID=$PID_V1)"; ALL_ALIVE=false; }
kill -0 $PID_V2 2>/dev/null || { echo "DEAD: V2 (PID=$PID_V2)"; ALL_ALIVE=false; }
kill -0 $PID_V3 2>/dev/null || { echo "DEAD: V3 (PID=$PID_V3)"; ALL_ALIVE=false; }
kill -0 $PID_V4 2>/dev/null || { echo "DEAD: V4 (PID=$PID_V4)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e hover/steady-state-v2 manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "V1 V2 V3 V4"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/hover/steady-state-v2/run_watchdog.py \\"
echo "      > experiments/hover/steady-state-v2/watchdog.log 2>&1 &"
echo "================================================================"
