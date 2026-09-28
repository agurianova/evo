#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: PYTHONPATH=. $GIGAEVO_PYTHON tools/experiment/generate_launch.py --experiment heilbron/baseline-repro
#
# Experiment: heilbron/baseline-repro
# Branch: exp/heilbron/baseline-repro
# PR: #201
# Pre-reg commit: 08837375
#
# Runs: P1_A, P1_B, P2_A, P2_B, P3_A, P3_B, P4_A, P4_B

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/heilbron/baseline-repro"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.232.30.185"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export OPENAI_API_KEY="sk-gigaevo"

echo "================================================================"
echo "heilbron/baseline-repro experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: 08837375"
echo "P1_A: Pair 1: Constructor (replication) — pipeline=adversarial_coevo"
echo "P1_B: Pair 1: Improver (replication) — pipeline=adversarial_coevo"
echo "P2_A: Pair 2: Constructor (replication) — pipeline=adversarial_coevo"
echo "P2_B: Pair 2: Improver (replication) — pipeline=adversarial_coevo"
echo "P3_A: Pair 3: Constructor (replication) — pipeline=adversarial_coevo"
echo "P3_B: Pair 3: Improver (replication) — pipeline=adversarial_coevo"
echo "P4_A: Pair 4: Constructor (replication) — pipeline=adversarial_coevo"
echo "P4_B: Pair 4: Improver (replication) — pipeline=adversarial_coevo"
echo "================================================================"
echo ""

# ── Preflight check (hard gate) ──────────────────────────────────────────
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/experiment/preflight_check.py" --experiment heilbron/baseline-repro
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- P1_A config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=1 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    pipeline_builder.per_opponent_timeout=300 \
    --cfg job \
    > "$LOG_DIR/cfg_run_P1_A.txt" 2>&1
cat "$LOG_DIR/cfg_run_P1_A.txt" | head -40
echo ""
echo "--- P1_B config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=2 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=1 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    pipeline_builder.per_opponent_timeout=300 \
    --cfg job \
    > "$LOG_DIR/cfg_run_P1_B.txt" 2>&1
cat "$LOG_DIR/cfg_run_P1_B.txt" | head -40
echo ""
echo "--- P2_A config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=3 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=4 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    pipeline_builder.per_opponent_timeout=300 \
    --cfg job \
    > "$LOG_DIR/cfg_run_P2_A.txt" 2>&1
cat "$LOG_DIR/cfg_run_P2_A.txt" | head -40
echo ""
echo "--- P2_B config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=4 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=3 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    pipeline_builder.per_opponent_timeout=300 \
    --cfg job \
    > "$LOG_DIR/cfg_run_P2_B.txt" 2>&1
cat "$LOG_DIR/cfg_run_P2_B.txt" | head -40
echo ""
echo "--- P3_A config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=5 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=6 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    pipeline_builder.per_opponent_timeout=300 \
    --cfg job \
    > "$LOG_DIR/cfg_run_P3_A.txt" 2>&1
cat "$LOG_DIR/cfg_run_P3_A.txt" | head -40
echo ""
echo "--- P3_B config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=6 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=5 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    pipeline_builder.per_opponent_timeout=300 \
    --cfg job \
    > "$LOG_DIR/cfg_run_P3_B.txt" 2>&1
cat "$LOG_DIR/cfg_run_P3_B.txt" | head -40
echo ""
echo "--- P4_A config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=7 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=8 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    pipeline_builder.per_opponent_timeout=300 \
    --cfg job \
    > "$LOG_DIR/cfg_run_P4_A.txt" 2>&1
cat "$LOG_DIR/cfg_run_P4_A.txt" | head -40
echo ""
echo "--- P4_B config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=8 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=7 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    pipeline_builder.per_opponent_timeout=300 \
    --cfg job \
    > "$LOG_DIR/cfg_run_P4_B.txt" 2>&1
cat "$LOG_DIR/cfg_run_P4_B.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run P1_A: Pair 1: Constructor (replication)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=1 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    pipeline_builder.per_opponent_timeout=300 \
    > "$LOG_DIR/pop_a_pair1.log" 2>&1 &
PID_P1_A=$!
echo "Run P1_A started: PID=$PID_P1_A  DB=1  pipeline=adversarial_coevo"

# ── Run P1_B: Pair 1: Improver (replication)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=2 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=1 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    pipeline_builder.per_opponent_timeout=300 \
    > "$LOG_DIR/pop_b_pair1.log" 2>&1 &
PID_P1_B=$!
echo "Run P1_B started: PID=$PID_P1_B  DB=2  pipeline=adversarial_coevo"

# ── Run P2_A: Pair 2: Constructor (replication)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=3 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=4 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    pipeline_builder.per_opponent_timeout=300 \
    > "$LOG_DIR/pop_a_pair2.log" 2>&1 &
PID_P2_A=$!
echo "Run P2_A started: PID=$PID_P2_A  DB=3  pipeline=adversarial_coevo"

# ── Run P2_B: Pair 2: Improver (replication)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=4 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=3 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    pipeline_builder.per_opponent_timeout=300 \
    > "$LOG_DIR/pop_b_pair2.log" 2>&1 &
PID_P2_B=$!
echo "Run P2_B started: PID=$PID_P2_B  DB=4  pipeline=adversarial_coevo"

# ── Run P3_A: Pair 3: Constructor (replication)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=5 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=6 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    pipeline_builder.per_opponent_timeout=300 \
    > "$LOG_DIR/pop_a_pair3.log" 2>&1 &
PID_P3_A=$!
echo "Run P3_A started: PID=$PID_P3_A  DB=5  pipeline=adversarial_coevo"

# ── Run P3_B: Pair 3: Improver (replication)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=6 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=5 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    pipeline_builder.per_opponent_timeout=300 \
    > "$LOG_DIR/pop_b_pair3.log" 2>&1 &
PID_P3_B=$!
echo "Run P3_B started: PID=$PID_P3_B  DB=6  pipeline=adversarial_coevo"

# ── Run P4_A: Pair 4: Constructor (replication)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=7 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=8 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    pipeline_builder.per_opponent_timeout=300 \
    > "$LOG_DIR/pop_a_pair4.log" 2>&1 &
PID_P4_A=$!
echo "Run P4_A started: PID=$PID_P4_A  DB=7  pipeline=adversarial_coevo"

# ── Run P4_B: Pair 4: Improver (replication)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_coevo \
    prompts=default \
    redis.db=8 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    opponent_redis_db=7 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    pipeline_builder.per_opponent_timeout=300 \
    > "$LOG_DIR/pop_b_pair4.log" 2>&1 &
PID_P4_B=$!
echo "Run P4_B started: PID=$PID_P4_B  DB=8  pipeline=adversarial_coevo"

echo ""
echo "================================================================"
echo "All 8 runs launched."
echo "PIDs: P1_A=$PID_P1_A  P1_B=$PID_P1_B  P2_A=$PID_P2_A  P2_B=$PID_P2_B  P3_A=$PID_P3_A  P3_B=$PID_P3_B  P4_A=$PID_P4_A  P4_B=$PID_P4_B"
echo "$PID_P1_A $PID_P1_B $PID_P2_A $PID_P2_B $PID_P3_A $PID_P3_B $PID_P4_A $PID_P4_B" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_P1_A 2>/dev/null || { echo "DEAD: P1_A (PID=$PID_P1_A)"; ALL_ALIVE=false; }
kill -0 $PID_P1_B 2>/dev/null || { echo "DEAD: P1_B (PID=$PID_P1_B)"; ALL_ALIVE=false; }
kill -0 $PID_P2_A 2>/dev/null || { echo "DEAD: P2_A (PID=$PID_P2_A)"; ALL_ALIVE=false; }
kill -0 $PID_P2_B 2>/dev/null || { echo "DEAD: P2_B (PID=$PID_P2_B)"; ALL_ALIVE=false; }
kill -0 $PID_P3_A 2>/dev/null || { echo "DEAD: P3_A (PID=$PID_P3_A)"; ALL_ALIVE=false; }
kill -0 $PID_P3_B 2>/dev/null || { echo "DEAD: P3_B (PID=$PID_P3_B)"; ALL_ALIVE=false; }
kill -0 $PID_P4_A 2>/dev/null || { echo "DEAD: P4_A (PID=$PID_P4_A)"; ALL_ALIVE=false; }
kill -0 $PID_P4_B 2>/dev/null || { echo "DEAD: P4_B (PID=$PID_P4_B)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e heilbron/baseline-repro manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "P1_A P1_B P2_A P2_B P3_A P3_B P4_A P4_B"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/heilbron/baseline-repro/run_watchdog.py \\"
echo "      > experiments/heilbron/baseline-repro/watchdog.log 2>&1 &"
echo "================================================================"
