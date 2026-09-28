#!/usr/bin/env bash
# Phase A: Memory bank builder
# Runs evolution with ideas_tracker=true to create memory cards.
# After completion, proceed to launch_phase_b.sh.
#
# Experiment: hover/memory
# Branch: exp/hover-memory
# PR: #161

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/hover/memory"

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
echo "hover/memory Phase A — Memory Bank Builder — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Run M0: ideas_tracker=true, checkpoint_dir=memory_bank"
echo "Redis DB: 3"
echo "================================================================"
echo ""

cd "$PROJ"

# Launch M0
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full7_no_deep \
    pipeline=structural_metrics \
    prompts=default \
    redis.db=3 \
    stage_timeout=6000 \
    dag_timeout=14400 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://localhost:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    scheduling=lpt_chain \
    algorithm=topology_3d_7step \
    ideas_tracker=true \
    checkpoint_dir="$PROJ/experiments/hover/memory/memory_bank" \
    > "$LOG_DIR/logs/M0.log" 2>&1 &
PID_M0=$!
echo "Run M0 started: PID=$PID_M0  DB=3"
echo "$PID_M0" > "$LOG_DIR/pids_phase_a.txt"

sleep 5
if kill -0 $PID_M0 2>/dev/null; then
    echo "M0 PID verified alive."
else
    echo "ABORT: M0 not alive. Check logs."
    exit 1
fi

echo ""
echo "================================================================"
echo "Phase A launched. Monitor with:"
echo "  PYTHONPATH=$PROJ $PYTHON $PROJ/tools/status.py --run chains/hover/full7_no_deep@3:M0"
echo ""
echo "After Phase A completes, run: bash experiments/hover/memory/launch_phase_b.sh"
echo "================================================================"
