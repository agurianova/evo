#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: gigaevo -e heilbron/k5-budget-v2 launch --dry-run
#
# Experiment: heilbron/k5-budget-v2
# Branch: exp/heilbron/k5-budget-v2
#
# Runs: A3_G, A3_D, A5_G, A5_D, B3_G, B3_D, B5_G, B5_D

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/heilbron/k5-budget-v2"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.232.30.185"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export OPENAI_API_KEY="sk-gigaevo"

echo "================================================================"
echo "heilbron/k5-budget-v2 experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "A3_G: Arm A3 (Composition + K=3+loose): Constructor — pipeline=adversarial_asymmetric"
echo "A3_D: Arm A3 (Composition + K=3+loose): Improver — pipeline=adversarial_asymmetric"
echo "A5_G: Arm A5 (Composition + K=5+loose): Constructor — pipeline=adversarial_asymmetric"
echo "A5_D: Arm A5 (Composition + K=5+loose): Improver — pipeline=adversarial_asymmetric"
echo "B3_G: Arm B3 (Gradient-in-prompt + K=3+loose): Constructor — pipeline=adversarial_asymmetric"
echo "B3_D: Arm B3 (Gradient-in-prompt + K=3+loose): Improver — pipeline=adversarial_asymmetric"
echo "B5_G: Arm B5 (Gradient-in-prompt + K=5+loose): Constructor — pipeline=adversarial_asymmetric"
echo "B5_D: Arm B5 (Gradient-in-prompt + K=5+loose): Improver — pipeline=adversarial_asymmetric"
echo "================================================================"
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- A3_G config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=1 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    feedback_mode=composition \
    population_role=constructor \
    'post_step_hook=${composition_injection_hook}' \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    --cfg job \
    > "$LOG_DIR/cfg_run_A3_G.txt" 2>&1
cat "$LOG_DIR/cfg_run_A3_G.txt" | head -40
echo ""
echo "--- A3_D config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=2 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    max_mutations_per_generation=24 \
    sync_min_delta=1 \
    opponent_redis_db=1 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    feedback_mode=composition \
    population_role=improver \
    d_sees_g_source=true \
    d_archive_persistent=true \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    --cfg job \
    > "$LOG_DIR/cfg_run_A3_D.txt" 2>&1
cat "$LOG_DIR/cfg_run_A3_D.txt" | head -40
echo ""
echo "--- A5_G config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=3 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=4 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    feedback_mode=composition \
    population_role=constructor \
    'post_step_hook=${composition_injection_hook}' \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    --cfg job \
    > "$LOG_DIR/cfg_run_A5_G.txt" 2>&1
cat "$LOG_DIR/cfg_run_A5_G.txt" | head -40
echo ""
echo "--- A5_D config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=4 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    max_mutations_per_generation=40 \
    sync_min_delta=1 \
    opponent_redis_db=3 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    feedback_mode=composition \
    population_role=improver \
    d_sees_g_source=true \
    d_archive_persistent=true \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    --cfg job \
    > "$LOG_DIR/cfg_run_A5_D.txt" 2>&1
cat "$LOG_DIR/cfg_run_A5_D.txt" | head -40
echo ""
echo "--- B3_G config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=5 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=6 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    feedback_mode=gradient_in_prompt \
    population_role=constructor \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    --cfg job \
    > "$LOG_DIR/cfg_run_B3_G.txt" 2>&1
cat "$LOG_DIR/cfg_run_B3_G.txt" | head -40
echo ""
echo "--- B3_D config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=6 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    max_mutations_per_generation=24 \
    sync_min_delta=1 \
    opponent_redis_db=5 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    feedback_mode=gradient_in_prompt \
    population_role=improver \
    d_sees_g_source=true \
    d_archive_persistent=true \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    --cfg job \
    > "$LOG_DIR/cfg_run_B3_D.txt" 2>&1
cat "$LOG_DIR/cfg_run_B3_D.txt" | head -40
echo ""
echo "--- B5_G config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=7 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=8 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    feedback_mode=gradient_in_prompt \
    population_role=constructor \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    --cfg job \
    > "$LOG_DIR/cfg_run_B5_G.txt" 2>&1
cat "$LOG_DIR/cfg_run_B5_G.txt" | head -40
echo ""
echo "--- B5_D config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    max_mutations_per_generation=40 \
    sync_min_delta=1 \
    opponent_redis_db=7 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    feedback_mode=gradient_in_prompt \
    population_role=improver \
    d_sees_g_source=true \
    d_archive_persistent=true \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    --cfg job \
    > "$LOG_DIR/cfg_run_B5_D.txt" 2>&1
cat "$LOG_DIR/cfg_run_B5_D.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run A3_G: Arm A3 (Composition + K=3+loose): Constructor
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=1 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    feedback_mode=composition \
    population_role=constructor \
    'post_step_hook=${composition_injection_hook}' \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    > "$LOG_DIR/run_A3_G.log" 2>&1 &
PID_A3_G=$!
echo "Run A3_G started: PID=$PID_A3_G  DB=1  pipeline=adversarial_asymmetric"

# ── Run A3_D: Arm A3 (Composition + K=3+loose): Improver
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=2 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    max_mutations_per_generation=24 \
    sync_min_delta=1 \
    opponent_redis_db=1 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    feedback_mode=composition \
    population_role=improver \
    d_sees_g_source=true \
    d_archive_persistent=true \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    > "$LOG_DIR/run_A3_D.log" 2>&1 &
PID_A3_D=$!
echo "Run A3_D started: PID=$PID_A3_D  DB=2  pipeline=adversarial_asymmetric"

# ── Run A5_G: Arm A5 (Composition + K=5+loose): Constructor
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=3 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=4 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    feedback_mode=composition \
    population_role=constructor \
    'post_step_hook=${composition_injection_hook}' \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    > "$LOG_DIR/run_A5_G.log" 2>&1 &
PID_A5_G=$!
echo "Run A5_G started: PID=$PID_A5_G  DB=3  pipeline=adversarial_asymmetric"

# ── Run A5_D: Arm A5 (Composition + K=5+loose): Improver
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=4 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    max_mutations_per_generation=40 \
    sync_min_delta=1 \
    opponent_redis_db=3 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    feedback_mode=composition \
    population_role=improver \
    d_sees_g_source=true \
    d_archive_persistent=true \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    > "$LOG_DIR/run_A5_D.log" 2>&1 &
PID_A5_D=$!
echo "Run A5_D started: PID=$PID_A5_D  DB=4  pipeline=adversarial_asymmetric"

# ── Run B3_G: Arm B3 (Gradient-in-prompt + K=3+loose): Constructor
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=5 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=6 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    feedback_mode=gradient_in_prompt \
    population_role=constructor \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    > "$LOG_DIR/run_B3_G.log" 2>&1 &
PID_B3_G=$!
echo "Run B3_G started: PID=$PID_B3_G  DB=5  pipeline=adversarial_asymmetric"

# ── Run B3_D: Arm B3 (Gradient-in-prompt + K=3+loose): Improver
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=6 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    max_mutations_per_generation=24 \
    sync_min_delta=1 \
    opponent_redis_db=5 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    feedback_mode=gradient_in_prompt \
    population_role=improver \
    d_sees_g_source=true \
    d_archive_persistent=true \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    > "$LOG_DIR/run_B3_D.log" 2>&1 &
PID_B3_D=$!
echo "Run B3_D started: PID=$PID_B3_D  DB=6  pipeline=adversarial_asymmetric"

# ── Run B5_G: Arm B5 (Gradient-in-prompt + K=5+loose): Constructor
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=7 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    opponent_redis_db=8 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    feedback_mode=gradient_in_prompt \
    population_role=constructor \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    > "$LOG_DIR/run_B5_G.log" 2>&1 &
PID_B5_G=$!
echo "Run B5_G started: PID=$PID_B5_G  DB=7  pipeline=adversarial_asymmetric"

# ── Run B5_D: Arm B5 (Gradient-in-prompt + K=5+loose): Improver
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric \
    prompts=default \
    redis.db=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    max_mutations_per_generation=40 \
    sync_min_delta=1 \
    opponent_redis_db=7 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    feedback_mode=gradient_in_prompt \
    population_role=improver \
    d_sees_g_source=true \
    d_archive_persistent=true \
    pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    n_opponents=3 \
    source_prompt_k=3 \
    > "$LOG_DIR/run_B5_D.log" 2>&1 &
PID_B5_D=$!
echo "Run B5_D started: PID=$PID_B5_D  DB=8  pipeline=adversarial_asymmetric"

echo ""
echo "================================================================"
echo "All 8 runs launched."
echo "PIDs: A3_G=$PID_A3_G  A3_D=$PID_A3_D  A5_G=$PID_A5_G  A5_D=$PID_A5_D  B3_G=$PID_B3_G  B3_D=$PID_B3_D  B5_G=$PID_B5_G  B5_D=$PID_B5_D"
echo "$PID_A3_G $PID_A3_D $PID_A5_G $PID_A5_D $PID_B3_G $PID_B3_D $PID_B5_G $PID_B5_D" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_A3_G 2>/dev/null || { echo "DEAD: A3_G (PID=$PID_A3_G)"; ALL_ALIVE=false; }
kill -0 $PID_A3_D 2>/dev/null || { echo "DEAD: A3_D (PID=$PID_A3_D)"; ALL_ALIVE=false; }
kill -0 $PID_A5_G 2>/dev/null || { echo "DEAD: A5_G (PID=$PID_A5_G)"; ALL_ALIVE=false; }
kill -0 $PID_A5_D 2>/dev/null || { echo "DEAD: A5_D (PID=$PID_A5_D)"; ALL_ALIVE=false; }
kill -0 $PID_B3_G 2>/dev/null || { echo "DEAD: B3_G (PID=$PID_B3_G)"; ALL_ALIVE=false; }
kill -0 $PID_B3_D 2>/dev/null || { echo "DEAD: B3_D (PID=$PID_B3_D)"; ALL_ALIVE=false; }
kill -0 $PID_B5_G 2>/dev/null || { echo "DEAD: B5_G (PID=$PID_B5_G)"; ALL_ALIVE=false; }
kill -0 $PID_B5_D 2>/dev/null || { echo "DEAD: B5_D (PID=$PID_B5_D)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e heilbron/k5-budget-v2 manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "A3_G A3_D A5_G A5_D B3_G B3_D B5_G B5_D"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/heilbron/k5-budget-v2/run_watchdog.py \\"
echo "      > experiments/heilbron/k5-budget-v2/watchdog.log 2>&1 &"
echo "================================================================"
