#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: PYTHONPATH=. $GIGAEVO_PYTHON tools/experiment/generate_launch.py --experiment hover/memory
#
# Experiment: hover/memory
# Branch: exp/hover-memory
# PR: #161
# Pre-reg commit: ff379b4
#
# Runs: R1, R2, R3, R4

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/hover/memory"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.232.30.185"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export HOVER_CHAIN_URL="http://localhost:4000/v1"
export OPENAI_API_KEY="sk-gigaevo"

echo "================================================================"
echo "hover/memory experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: ff379b4"
echo "R1: Control: no memory — pipeline=structural_metrics"
echo "R2: Control: no memory — pipeline=structural_metrics"
echo "R3: Treatment: memory enabled — pipeline=structural_metrics"
echo "R4: Treatment: memory enabled — pipeline=structural_metrics"
echo "================================================================"
echo ""

# ── Preflight check (hard gate) ──────────────────────────────────────────
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/experiment/preflight_check.py" --experiment hover/memory
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- R1 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full7_no_deep \
    pipeline=structural_metrics \
    prompts=default \
    redis.db=4 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://localhost:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt_chain \
    algorithm=topology_3d_ret \
    --cfg job \
    > "$LOG_DIR/cfg_run_R1.txt" 2>&1
cat "$LOG_DIR/cfg_run_R1.txt" | head -40
echo ""
echo "--- R2 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full7_no_deep \
    pipeline=structural_metrics \
    prompts=default \
    redis.db=5 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://localhost:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt_chain \
    algorithm=topology_3d_ret \
    --cfg job \
    > "$LOG_DIR/cfg_run_R2.txt" 2>&1
cat "$LOG_DIR/cfg_run_R2.txt" | head -40
echo ""
echo "--- R3 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full7_no_deep \
    pipeline=structural_metrics \
    prompts=default \
    redis.db=6 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://localhost:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt_chain \
    algorithm=topology_3d_ret \
    memory=local \
    checkpoint_dir=experiments/hover/memory/memory_bank \
    namespace=default \
    --cfg job \
    > "$LOG_DIR/cfg_run_R3.txt" 2>&1
cat "$LOG_DIR/cfg_run_R3.txt" | head -40
echo ""
echo "--- R4 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full7_no_deep \
    pipeline=structural_metrics \
    prompts=default \
    redis.db=7 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://localhost:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt_chain \
    algorithm=topology_3d_ret \
    memory=local \
    checkpoint_dir=experiments/hover/memory/memory_bank \
    namespace=default \
    --cfg job \
    > "$LOG_DIR/cfg_run_R4.txt" 2>&1
cat "$LOG_DIR/cfg_run_R4.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run R1: Control: no memory
HOVER_CHAIN_URL="http://localhost:4000/v1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full7_no_deep \
    pipeline=structural_metrics \
    prompts=default \
    redis.db=4 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://localhost:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt_chain \
    algorithm=topology_3d_ret \
    > "$LOG_DIR/logs/R1.log" 2>&1 &
PID_R1=$!
echo "Run R1 started: PID=$PID_R1  DB=4  pipeline=structural_metrics"

# ── Run R2: Control: no memory
HOVER_CHAIN_URL="http://localhost:4000/v1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full7_no_deep \
    pipeline=structural_metrics \
    prompts=default \
    redis.db=5 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://localhost:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt_chain \
    algorithm=topology_3d_ret \
    > "$LOG_DIR/logs/R2.log" 2>&1 &
PID_R2=$!
echo "Run R2 started: PID=$PID_R2  DB=5  pipeline=structural_metrics"

# ── Run R3: Treatment: memory enabled
HOVER_CHAIN_URL="http://localhost:4000/v1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full7_no_deep \
    pipeline=structural_metrics \
    prompts=default \
    redis.db=6 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://localhost:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt_chain \
    algorithm=topology_3d_ret \
    memory=local \
    checkpoint_dir=experiments/hover/memory/memory_bank \
    namespace=default \
    > "$LOG_DIR/logs/R3.log" 2>&1 &
PID_R3=$!
echo "Run R3 started: PID=$PID_R3  DB=6  pipeline=structural_metrics"

# ── Run R4: Treatment: memory enabled
HOVER_CHAIN_URL="http://localhost:4000/v1" nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full7_no_deep \
    pipeline=structural_metrics \
    prompts=default \
    redis.db=7 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://localhost:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt_chain \
    algorithm=topology_3d_ret \
    memory=local \
    checkpoint_dir=experiments/hover/memory/memory_bank \
    namespace=default \
    > "$LOG_DIR/logs/R4.log" 2>&1 &
PID_R4=$!
echo "Run R4 started: PID=$PID_R4  DB=7  pipeline=structural_metrics"

echo ""
echo "================================================================"
echo "All 4 runs launched."
echo "PIDs: R1=$PID_R1  R2=$PID_R2  R3=$PID_R3  R4=$PID_R4"
echo "$PID_R1 $PID_R2 $PID_R3 $PID_R4" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_R1 2>/dev/null || { echo "DEAD: R1 (PID=$PID_R1)"; ALL_ALIVE=false; }
kill -0 $PID_R2 2>/dev/null || { echo "DEAD: R2 (PID=$PID_R2)"; ALL_ALIVE=false; }
kill -0 $PID_R3 2>/dev/null || { echo "DEAD: R3 (PID=$PID_R3)"; ALL_ALIVE=false; }
kill -0 $PID_R4 2>/dev/null || { echo "DEAD: R4 (PID=$PID_R4)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e hover/memory manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "R1 R2 R3 R4"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/hover/memory/run_watchdog.py \\"
echo "      > experiments/hover/memory/watchdog.log 2>&1 &"
echo "================================================================"
