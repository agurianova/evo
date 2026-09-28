#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: PYTHONPATH=. $GIGAEVO_PYTHON tools/experiment/generate_launch.py --experiment adversarial/optimizer-coevo
#
# Experiment: adversarial/optimizer-coevo
# Branch: exp/adversarial-optimizer-coevo
# PR: #169
# Pre-reg commit: 172a83e
#
# Runs: P1-A, P1-B, P2-A, P2-B

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal/.claude/worktrees/adversarial-coevo"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/adversarial/optimizer-coevo"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.232.30.185"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export OPENAI_API_KEY="sk-gigaevo"

echo "================================================================"
echo "adversarial/optimizer-coevo experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: 172a83e"
echo "P1-A: Pair 1: optimizer (co-evolution) — pipeline=adversarial_coevo"
echo "P1-B: Pair 1: landscape (co-evolution) — pipeline=adversarial_coevo"
echo "P2-A: Pair 2: optimizer (co-evolution) — pipeline=adversarial_coevo"
echo "P2-B: Pair 2: landscape (co-evolution) — pipeline=adversarial_coevo"
echo "================================================================"
echo ""

# ── Preflight check (hard gate) ──────────────────────────────────────────
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/experiment/preflight_check.py" --experiment adversarial/optimizer-coevo
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- P1-A config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=adversarial/optimizer_v2/pop_a \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=1 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=20 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=2 \
    opponent_redis_prefix=adversarial/optimizer_v2/pop_b \
    --cfg job \
    > "$LOG_DIR/cfg_run_P1-A.txt" 2>&1
cat "$LOG_DIR/cfg_run_P1-A.txt" | head -40
echo ""
echo "--- P1-B config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=adversarial/optimizer_v2/pop_b \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=2 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=20 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=1 \
    opponent_redis_prefix=adversarial/optimizer_v2/pop_a \
    --cfg job \
    > "$LOG_DIR/cfg_run_P1-B.txt" 2>&1
cat "$LOG_DIR/cfg_run_P1-B.txt" | head -40
echo ""
echo "--- P2-A config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=adversarial/optimizer_v2/pop_a \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=3 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=20 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=4 \
    opponent_redis_prefix=adversarial/optimizer_v2/pop_b \
    --cfg job \
    > "$LOG_DIR/cfg_run_P2-A.txt" 2>&1
cat "$LOG_DIR/cfg_run_P2-A.txt" | head -40
echo ""
echo "--- P2-B config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=adversarial/optimizer_v2/pop_b \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=4 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=20 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=3 \
    opponent_redis_prefix=adversarial/optimizer_v2/pop_a \
    --cfg job \
    > "$LOG_DIR/cfg_run_P2-B.txt" 2>&1
cat "$LOG_DIR/cfg_run_P2-B.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run P1-A: Pair 1: optimizer (co-evolution)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=adversarial/optimizer_v2/pop_a \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=1 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=20 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=2 \
    opponent_redis_prefix=adversarial/optimizer_v2/pop_b \
    > "$LOG_DIR/pop_a_pair1.log" 2>&1 &
PID_P1A=$!
echo "Run P1-A started: PID=$PID_P1A  DB=1  pipeline=adversarial_coevo"

# ── Run P1-B: Pair 1: landscape (co-evolution)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=adversarial/optimizer_v2/pop_b \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=2 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=20 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=1 \
    opponent_redis_prefix=adversarial/optimizer_v2/pop_a \
    > "$LOG_DIR/pop_b_pair1.log" 2>&1 &
PID_P1B=$!
echo "Run P1-B started: PID=$PID_P1B  DB=2  pipeline=adversarial_coevo"

# ── Run P2-A: Pair 2: optimizer (co-evolution)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=adversarial/optimizer_v2/pop_a \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=3 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=20 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=4 \
    opponent_redis_prefix=adversarial/optimizer_v2/pop_b \
    > "$LOG_DIR/pop_a_pair2.log" 2>&1 &
PID_P2A=$!
echo "Run P2-A started: PID=$PID_P2A  DB=3  pipeline=adversarial_coevo"

# ── Run P2-B: Pair 2: landscape (co-evolution)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=adversarial/optimizer_v2/pop_b \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=4 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=20 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=3 \
    opponent_redis_prefix=adversarial/optimizer_v2/pop_a \
    > "$LOG_DIR/pop_b_pair2.log" 2>&1 &
PID_P2B=$!
echo "Run P2-B started: PID=$PID_P2B  DB=4  pipeline=adversarial_coevo"

echo ""
echo "================================================================"
echo "All 4 runs launched."
echo "PIDs: P1-A=$PID_P1A  P1-B=$PID_P1B  P2-A=$PID_P2A  P2-B=$PID_P2B"
echo "$PID_P1A $PID_P1B $PID_P2A $PID_P2B" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_P1A 2>/dev/null || { echo "DEAD: P1-A (PID=$PID_P1A)"; ALL_ALIVE=false; }
kill -0 $PID_P1B 2>/dev/null || { echo "DEAD: P1-B (PID=$PID_P1B)"; ALL_ALIVE=false; }
kill -0 $PID_P2A 2>/dev/null || { echo "DEAD: P2-A (PID=$PID_P2A)"; ALL_ALIVE=false; }
kill -0 $PID_P2B 2>/dev/null || { echo "DEAD: P2-B (PID=$PID_P2B)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e adversarial/optimizer-coevo manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "P1-A P1-B P2-A P2-B"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/adversarial/optimizer-coevo/run_watchdog.py \\"
echo "      > experiments/adversarial/optimizer-coevo/watchdog.log 2>&1 &"
echo "================================================================"
