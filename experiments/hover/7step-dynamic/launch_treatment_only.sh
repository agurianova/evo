#!/usr/bin/env bash
# Treatment-only relaunch (V3/V4) after task_description.txt fix.
# Env vars copied from generated launch.sh.

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/hover/7step-dynamic"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.232.30.185"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export OPENAI_API_KEY="sk-gigaevo"

echo "================================================================"
echo "hover/7step-dynamic — treatment relaunch (V3, V4)"
echo "================================================================"

cd "$PROJ"

# ── Run V3: treatment
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full7 \
    pipeline=structural_metrics \
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
    algorithm=topology_3d_7step \
    > "$LOG_DIR/logs/V3.log" 2>&1 &
PID_V3=$!
echo "Run V3 started: PID=$PID_V3  DB=5"

# ── Run V4: treatment
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full7 \
    pipeline=structural_metrics \
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
    algorithm=topology_3d_7step \
    > "$LOG_DIR/logs/V4.log" 2>&1 &
PID_V4=$!
echo "Run V4 started: PID=$PID_V4  DB=6"

echo ""
sleep 5
kill -0 $PID_V3 2>/dev/null && echo "V3 ALIVE" || echo "V3 DEAD"
kill -0 $PID_V4 2>/dev/null && echo "V4 ALIVE" || echo "V4 DEAD"
echo "PIDs: V3=$PID_V3  V4=$PID_V4"
