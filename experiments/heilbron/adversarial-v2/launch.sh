#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: PYTHONPATH=. $GIGAEVO_PYTHON tools/experiment/generate_launch.py --experiment heilbron/adversarial-v2
#
# Experiment: heilbron/adversarial-v2
# Branch: exp/heilbron/adversarial-v2
# PR: #188
# Pre-reg commit: 24b6b1b297427431389d6f0bf78594fa8778697f
#
# Runs: P1_A, P1_B, P2_A, P2_B

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/heilbron/adversarial-v2"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.232.30.185"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export OPENAI_API_KEY="sk-gigaevo"

echo "================================================================"
echo "heilbron/adversarial-v2 experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: 24b6b1b297427431389d6f0bf78594fa8778697f"
echo "P1_A: K=3 Constructor (bidirectional feedback) — pipeline=adversarial_coevo_feedback"
echo "P1_B: K=3 Improver (bidirectional feedback) — pipeline=adversarial_coevo_feedback"
echo "P2_A: K=1 Constructor (bidirectional feedback) — pipeline=adversarial_coevo_feedback"
echo "P2_B: K=1 Improver (bidirectional feedback) — pipeline=adversarial_coevo_feedback"
echo "================================================================"
echo ""

# ── Preflight check (hard gate) ──────────────────────────────────────────
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/experiment/preflight_check.py" --experiment heilbron/adversarial-v2
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- P1_A config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=1 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    pipeline_builder.per_opponent_timeout=300 \
    opponent_feedback_k=3 \
    population_role=constructor \
    --cfg job \
    > "$LOG_DIR/cfg_run_P1_A.txt" 2>&1
cat "$LOG_DIR/cfg_run_P1_A.txt" | head -40
echo ""
echo "--- P1_B config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=2 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=1 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    pipeline_builder.per_opponent_timeout=300 \
    opponent_feedback_k=3 \
    population_role=improver \
    --cfg job \
    > "$LOG_DIR/cfg_run_P1_B.txt" 2>&1
cat "$LOG_DIR/cfg_run_P1_B.txt" | head -40
echo ""
echo "--- P2_A config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=3 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=4 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    pipeline_builder.per_opponent_timeout=300 \
    opponent_feedback_k=1 \
    population_role=constructor \
    --cfg job \
    > "$LOG_DIR/cfg_run_P2_A.txt" 2>&1
cat "$LOG_DIR/cfg_run_P2_A.txt" | head -40
echo ""
echo "--- P2_B config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=4 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=3 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    pipeline_builder.per_opponent_timeout=300 \
    opponent_feedback_k=1 \
    population_role=improver \
    --cfg job \
    > "$LOG_DIR/cfg_run_P2_B.txt" 2>&1
cat "$LOG_DIR/cfg_run_P2_B.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run P1_A: K=3 Constructor (bidirectional feedback)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=1 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    pipeline_builder.per_opponent_timeout=300 \
    opponent_feedback_k=3 \
    population_role=constructor \
    > "$LOG_DIR/run_P1_A.log" 2>&1 &
PID_P1_A=$!
echo "Run P1_A started: PID=$PID_P1_A  DB=1  pipeline=adversarial_coevo_feedback"

# ── Run P1_B: K=3 Improver (bidirectional feedback)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=2 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=1 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    pipeline_builder.per_opponent_timeout=300 \
    opponent_feedback_k=3 \
    population_role=improver \
    > "$LOG_DIR/run_P1_B.log" 2>&1 &
PID_P1_B=$!
echo "Run P1_B started: PID=$PID_P1_B  DB=2  pipeline=adversarial_coevo_feedback"

# ── Run P2_A: K=1 Constructor (bidirectional feedback)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=3 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=4 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    pipeline_builder.per_opponent_timeout=300 \
    opponent_feedback_k=1 \
    population_role=constructor \
    > "$LOG_DIR/run_P2_A.log" 2>&1 &
PID_P2_A=$!
echo "Run P2_A started: PID=$PID_P2_A  DB=3  pipeline=adversarial_coevo_feedback"

# ── Run P2_B: K=1 Improver (bidirectional feedback)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=4 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=3 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    pipeline_builder.per_opponent_timeout=300 \
    opponent_feedback_k=1 \
    population_role=improver \
    > "$LOG_DIR/run_P2_B.log" 2>&1 &
PID_P2_B=$!
echo "Run P2_B started: PID=$PID_P2_B  DB=4  pipeline=adversarial_coevo_feedback"

echo ""
echo "================================================================"
echo "All 4 runs launched."
echo "PIDs: P1_A=$PID_P1_A  P1_B=$PID_P1_B  P2_A=$PID_P2_A  P2_B=$PID_P2_B"
echo "$PID_P1_A $PID_P1_B $PID_P2_A $PID_P2_B" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_P1_A 2>/dev/null || { echo "DEAD: P1_A (PID=$PID_P1_A)"; ALL_ALIVE=false; }
kill -0 $PID_P1_B 2>/dev/null || { echo "DEAD: P1_B (PID=$PID_P1_B)"; ALL_ALIVE=false; }
kill -0 $PID_P2_A 2>/dev/null || { echo "DEAD: P2_A (PID=$PID_P2_A)"; ALL_ALIVE=false; }
kill -0 $PID_P2_B 2>/dev/null || { echo "DEAD: P2_B (PID=$PID_P2_B)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e heilbron/adversarial-v2 manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "P1_A P1_B P2_A P2_B"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/heilbron/adversarial-v2/run_watchdog.py \\"
echo "      > experiments/heilbron/adversarial-v2/watchdog.log 2>&1 &"
echo "================================================================"
