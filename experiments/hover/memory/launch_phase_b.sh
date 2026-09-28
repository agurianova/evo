#!/usr/bin/env bash
# Phase B: Controlled experiment (4 runs)
# R1, R2 = control (no memory), R3, R4 = treatment (memory enabled)
# PREREQUISITE: Phase A must be complete and memory_bank/ must contain cards.
#
# Experiment: hover/memory
# Branch: exp/hover-memory
# PR: #161

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/hover/memory"
MEMORY_BANK="$PROJ/experiments/hover/memory/memory_bank"

export NO_PROXY="localhost,127.0.0.1,10.232.30.185,10.232.45.196,10.232.90.109,10.232.38.220,10.232.22.232,10.232.21.74"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"
export OPENAI_API_KEY="sk-gigaevo"
export HOVER_CHAIN_URL="http://localhost:4000/v1"

# Source OpenRouter key from .env
if [ -f "$PROJ/.env" ]; then
    export $(grep -v '^#' "$PROJ/.env" | xargs)
fi

echo "================================================================"
echo "hover/memory Phase B — Controlled Experiment — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "R1: control (DB 4), R2: control (DB 5)"
echo "R3: treatment/memory (DB 6), R4: treatment/memory (DB 7)"
echo "================================================================"
echo ""

# Verify memory bank exists
if [ ! -d "$MEMORY_BANK" ]; then
    echo "ABORT: Memory bank not found at $MEMORY_BANK"
    echo "Phase A must complete before launching Phase B."
    exit 1
fi
echo "Memory bank found: $MEMORY_BANK"
echo "Contents: $(ls "$MEMORY_BANK" 2>/dev/null | head -10)"
echo ""

cd "$PROJ"

# Common args for all runs
COMMON_ARGS="problem.name=chains/hover/full7_no_deep \
    pipeline=structural_metrics \
    prompts=default \
    stage_timeout=6000 \
    dag_timeout=14400 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url=http://localhost:4000/v1 \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt_chain \
    algorithm=topology_3d_7step"

# R1: control
nohup "$PYTHON" "$PROJ/run.py" \
    $COMMON_ARGS \
    redis.db=4 \
    > "$LOG_DIR/logs/R1.log" 2>&1 &
PID_R1=$!
echo "Run R1 (control) started: PID=$PID_R1  DB=4"

# R2: control
nohup "$PYTHON" "$PROJ/run.py" \
    $COMMON_ARGS \
    redis.db=5 \
    > "$LOG_DIR/logs/R2.log" 2>&1 &
PID_R2=$!
echo "Run R2 (control) started: PID=$PID_R2  DB=5"

# R3: treatment (memory enabled via DAG pipeline)
nohup "$PYTHON" "$PROJ/run.py" \
    $COMMON_ARGS \
    redis.db=6 \
    +memory=local \
    checkpoint_dir="$MEMORY_BANK" \
    > "$LOG_DIR/logs/R3.log" 2>&1 &
PID_R3=$!
echo "Run R3 (treatment) started: PID=$PID_R3  DB=6"

# R4: treatment (memory enabled via DAG pipeline)
nohup "$PYTHON" "$PROJ/run.py" \
    $COMMON_ARGS \
    redis.db=7 \
    +memory=local \
    checkpoint_dir="$MEMORY_BANK" \
    > "$LOG_DIR/logs/R4.log" 2>&1 &
PID_R4=$!
echo "Run R4 (treatment) started: PID=$PID_R4  DB=7"

echo ""
echo "$PID_R1 $PID_R2 $PID_R3 $PID_R4" > "$LOG_DIR/pids_phase_b.txt"

# Verify all PIDs alive
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

echo ""
echo "================================================================"
echo "Phase B launched."
echo "PIDs: R1=$PID_R1  R2=$PID_R2  R3=$PID_R3  R4=$PID_R4"
echo ""
echo "Monitor:"
echo "  PYTHONPATH=$PROJ $PYTHON $PROJ/tools/status.py --run chains/hover/full7_no_deep@4:R1 --run chains/hover/full7_no_deep@5:R2 --run chains/hover/full7_no_deep@6:R3 --run chains/hover/full7_no_deep@7:R4"
echo "================================================================"
