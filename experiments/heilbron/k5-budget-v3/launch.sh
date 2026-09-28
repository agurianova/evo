#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: gigaevo -e heilbron/k5-budget-v3 launch --dry-run
#
# Experiment: heilbron/k5-budget-v3
# Branch: exp/heilbron/k5-budget-v3
#
# Runs: K3_1_G, K3_1_D, K3_2_G, K3_2_D, K5_1_G, K5_1_D, K5_2_G, K5_2_D

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/heilbron/k5-budget-v3"

export NO_PROXY="localhost,127.0.0.1,api.github.com,mutation-1,mutation-2,10.232.30.185"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export OPENAI_API_KEY="sk-gigaevo"

echo "================================================================"
echo "heilbron/k5-budget-v3 experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "K3_1_G: v3_k3_run_1 — pipeline=adversarial_asymmetric_v3"
echo "K3_1_D: v3_k3_run_1 — pipeline=adversarial_asymmetric_v3"
echo "K3_2_G: v3_k3_run_2 — pipeline=adversarial_asymmetric_v3"
echo "K3_2_D: v3_k3_run_2 — pipeline=adversarial_asymmetric_v3"
echo "K5_1_G: v3_k5_run_1 — pipeline=adversarial_asymmetric_v3"
echo "K5_1_D: v3_k5_run_1 — pipeline=adversarial_asymmetric_v3"
echo "K5_2_G: v3_k5_run_2 — pipeline=adversarial_asymmetric_v3"
echo "K5_2_D: v3_k5_run_2 — pipeline=adversarial_asymmetric_v3"
echo "================================================================"
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- K3_1_G config ---"
"$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=1 \
    evolution=steady_state \
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    algorithm=single_island_2d_g \
    pipeline_builder.archive_reeval=true \
    n_opponents=3 \
    opponent_provider.fitness_key=fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=constructor \
    --cfg job \
    > "$LOG_DIR/cfg_run_K3_1_G.txt" 2>&1
cat "$LOG_DIR/cfg_run_K3_1_G.txt" | head -40
echo ""
echo "--- K3_1_D config ---"
"$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=2 \
    evolution=steady_state \
    opponent_redis_db=1 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    algorithm=single_island_2d_d \
    pipeline_builder.archive_reeval=true \
    n_opponents=3 \
    opponent_provider.fitness_key=actual_fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=improver \
    --cfg job \
    > "$LOG_DIR/cfg_run_K3_1_D.txt" 2>&1
cat "$LOG_DIR/cfg_run_K3_1_D.txt" | head -40
echo ""
echo "--- K3_2_G config ---"
"$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=3 \
    evolution=steady_state \
    opponent_redis_db=4 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    algorithm=single_island_2d_g \
    pipeline_builder.archive_reeval=true \
    n_opponents=3 \
    opponent_provider.fitness_key=fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=constructor \
    --cfg job \
    > "$LOG_DIR/cfg_run_K3_2_G.txt" 2>&1
cat "$LOG_DIR/cfg_run_K3_2_G.txt" | head -40
echo ""
echo "--- K3_2_D config ---"
"$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=4 \
    evolution=steady_state \
    opponent_redis_db=3 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    algorithm=single_island_2d_d \
    pipeline_builder.archive_reeval=true \
    n_opponents=3 \
    opponent_provider.fitness_key=actual_fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=improver \
    --cfg job \
    > "$LOG_DIR/cfg_run_K3_2_D.txt" 2>&1
cat "$LOG_DIR/cfg_run_K3_2_D.txt" | head -40
echo ""
echo "--- K5_1_G config ---"
"$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=5 \
    evolution=steady_state \
    opponent_redis_db=6 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    algorithm=single_island_2d_g \
    pipeline_builder.archive_reeval=true \
    n_opponents=5 \
    opponent_provider.fitness_key=fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=constructor \
    --cfg job \
    > "$LOG_DIR/cfg_run_K5_1_G.txt" 2>&1
cat "$LOG_DIR/cfg_run_K5_1_G.txt" | head -40
echo ""
echo "--- K5_1_D config ---"
"$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=6 \
    evolution=steady_state \
    opponent_redis_db=5 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    algorithm=single_island_2d_d \
    pipeline_builder.archive_reeval=true \
    n_opponents=5 \
    opponent_provider.fitness_key=actual_fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=improver \
    --cfg job \
    > "$LOG_DIR/cfg_run_K5_1_D.txt" 2>&1
cat "$LOG_DIR/cfg_run_K5_1_D.txt" | head -40
echo ""
echo "--- K5_2_G config ---"
"$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=7 \
    evolution=steady_state \
    opponent_redis_db=8 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    algorithm=single_island_2d_g \
    pipeline_builder.archive_reeval=true \
    n_opponents=5 \
    opponent_provider.fitness_key=fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=constructor \
    --cfg job \
    > "$LOG_DIR/cfg_run_K5_2_G.txt" 2>&1
cat "$LOG_DIR/cfg_run_K5_2_G.txt" | head -40
echo ""
echo "--- K5_2_D config ---"
"$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=8 \
    evolution=steady_state \
    opponent_redis_db=7 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    algorithm=single_island_2d_d \
    pipeline_builder.archive_reeval=true \
    n_opponents=5 \
    opponent_provider.fitness_key=actual_fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=improver \
    --cfg job \
    > "$LOG_DIR/cfg_run_K5_2_D.txt" 2>&1
cat "$LOG_DIR/cfg_run_K5_2_D.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run K3_1_G: v3_k3_run_1
nohup "$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=1 \
    evolution=steady_state \
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    algorithm=single_island_2d_g \
    pipeline_builder.archive_reeval=true \
    n_opponents=3 \
    opponent_provider.fitness_key=fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=constructor \
    > "$LOG_DIR/run_K3_1_G.log" 2>&1 &
PID_K3_1_G=$!
echo "Run K3_1_G started: PID=$PID_K3_1_G  DB=1  pipeline=adversarial_asymmetric_v3"

# ── Run K3_1_D: v3_k3_run_1
nohup "$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=2 \
    evolution=steady_state \
    opponent_redis_db=1 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    algorithm=single_island_2d_d \
    pipeline_builder.archive_reeval=true \
    n_opponents=3 \
    opponent_provider.fitness_key=actual_fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=improver \
    > "$LOG_DIR/run_K3_1_D.log" 2>&1 &
PID_K3_1_D=$!
echo "Run K3_1_D started: PID=$PID_K3_1_D  DB=2  pipeline=adversarial_asymmetric_v3"

# ── Run K3_2_G: v3_k3_run_2
nohup "$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=3 \
    evolution=steady_state \
    opponent_redis_db=4 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    algorithm=single_island_2d_g \
    pipeline_builder.archive_reeval=true \
    n_opponents=3 \
    opponent_provider.fitness_key=fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=constructor \
    > "$LOG_DIR/run_K3_2_G.log" 2>&1 &
PID_K3_2_G=$!
echo "Run K3_2_G started: PID=$PID_K3_2_G  DB=3  pipeline=adversarial_asymmetric_v3"

# ── Run K3_2_D: v3_k3_run_2
nohup "$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=4 \
    evolution=steady_state \
    opponent_redis_db=3 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    algorithm=single_island_2d_d \
    pipeline_builder.archive_reeval=true \
    n_opponents=3 \
    opponent_provider.fitness_key=actual_fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=improver \
    > "$LOG_DIR/run_K3_2_D.log" 2>&1 &
PID_K3_2_D=$!
echo "Run K3_2_D started: PID=$PID_K3_2_D  DB=4  pipeline=adversarial_asymmetric_v3"

# ── Run K5_1_G: v3_k5_run_1
nohup "$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=5 \
    evolution=steady_state \
    opponent_redis_db=6 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    algorithm=single_island_2d_g \
    pipeline_builder.archive_reeval=true \
    n_opponents=5 \
    opponent_provider.fitness_key=fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=constructor \
    > "$LOG_DIR/run_K5_1_G.log" 2>&1 &
PID_K5_1_G=$!
echo "Run K5_1_G started: PID=$PID_K5_1_G  DB=5  pipeline=adversarial_asymmetric_v3"

# ── Run K5_1_D: v3_k5_run_1
nohup "$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=6 \
    evolution=steady_state \
    opponent_redis_db=5 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    algorithm=single_island_2d_d \
    pipeline_builder.archive_reeval=true \
    n_opponents=5 \
    opponent_provider.fitness_key=actual_fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=improver \
    > "$LOG_DIR/run_K5_1_D.log" 2>&1 &
PID_K5_1_D=$!
echo "Run K5_1_D started: PID=$PID_K5_1_D  DB=6  pipeline=adversarial_asymmetric_v3"

# ── Run K5_2_G: v3_k5_run_2
nohup "$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=7 \
    evolution=steady_state \
    opponent_redis_db=8 \
    opponent_redis_prefix=heilbron_adversarial/pop_b \
    algorithm=single_island_2d_g \
    pipeline_builder.archive_reeval=true \
    n_opponents=5 \
    opponent_provider.fitness_key=fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=constructor \
    > "$LOG_DIR/run_K5_2_G.log" 2>&1 &
PID_K5_2_G=$!
echo "Run K5_2_G started: PID=$PID_K5_2_G  DB=7  pipeline=adversarial_asymmetric_v3"

# ── Run K5_2_D: v3_k5_run_2
nohup "$PYTHON" "$PROJ/run.py" \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    stage_timeout=2400 \
    dag_timeout=2400 \
    mutation_mode=rewrite \
    inner_iterations=1 \
    n_opponents=3 \
    source_prompt_k=3 \
    llm=single \
    llm_base_url=http://10.232.30.185:4000/v1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric_v3 \
    redis.db=8 \
    evolution=steady_state \
    opponent_redis_db=7 \
    opponent_redis_prefix=heilbron_adversarial/pop_a \
    algorithm=single_island_2d_d \
    pipeline_builder.archive_reeval=true \
    n_opponents=5 \
    opponent_provider.fitness_key=actual_fitness \
    opponent_provider.k=3 \
    opponent_provider.higher_is_better=true \
    population_role=improver \
    > "$LOG_DIR/run_K5_2_D.log" 2>&1 &
PID_K5_2_D=$!
echo "Run K5_2_D started: PID=$PID_K5_2_D  DB=8  pipeline=adversarial_asymmetric_v3"

echo ""
echo "================================================================"
echo "All 8 runs launched."
echo "PIDs: K3_1_G=$PID_K3_1_G  K3_1_D=$PID_K3_1_D  K3_2_G=$PID_K3_2_G  K3_2_D=$PID_K3_2_D  K5_1_G=$PID_K5_1_G  K5_1_D=$PID_K5_1_D  K5_2_G=$PID_K5_2_G  K5_2_D=$PID_K5_2_D"
echo "$PID_K3_1_G $PID_K3_1_D $PID_K3_2_G $PID_K3_2_D $PID_K5_1_G $PID_K5_1_D $PID_K5_2_G $PID_K5_2_D" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_K3_1_G 2>/dev/null || { echo "DEAD: K3_1_G (PID=$PID_K3_1_G)"; ALL_ALIVE=false; }
kill -0 $PID_K3_1_D 2>/dev/null || { echo "DEAD: K3_1_D (PID=$PID_K3_1_D)"; ALL_ALIVE=false; }
kill -0 $PID_K3_2_G 2>/dev/null || { echo "DEAD: K3_2_G (PID=$PID_K3_2_G)"; ALL_ALIVE=false; }
kill -0 $PID_K3_2_D 2>/dev/null || { echo "DEAD: K3_2_D (PID=$PID_K3_2_D)"; ALL_ALIVE=false; }
kill -0 $PID_K5_1_G 2>/dev/null || { echo "DEAD: K5_1_G (PID=$PID_K5_1_G)"; ALL_ALIVE=false; }
kill -0 $PID_K5_1_D 2>/dev/null || { echo "DEAD: K5_1_D (PID=$PID_K5_1_D)"; ALL_ALIVE=false; }
kill -0 $PID_K5_2_G 2>/dev/null || { echo "DEAD: K5_2_G (PID=$PID_K5_2_G)"; ALL_ALIVE=false; }
kill -0 $PID_K5_2_D 2>/dev/null || { echo "DEAD: K5_2_D (PID=$PID_K5_2_D)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e heilbron/k5-budget-v3 manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "K3_1_G K3_1_D K3_2_G K3_2_D K5_1_G K5_1_D K5_2_G K5_2_D"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/heilbron/k5-budget-v3/run_watchdog.py \\"
echo "      > experiments/heilbron/k5-budget-v3/watchdog.log 2>&1 &"
echo "================================================================"
