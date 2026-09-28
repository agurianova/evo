#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: gigaevo -e heilbron/d-tanh-no-lineage launch --dry-run
#
# Experiment: heilbron/d-tanh-no-lineage
# Branch: exp/heilbron/d-tanh-no-lineage
# PR: #223
# Pre-reg commit: 7b7c5f5e
#
# Runs: A1_G, A1_D, C1_G, C1_D

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/heilbron/d-tanh-no-lineage"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.232.30.185"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export OPENAI_API_KEY="sk-gigaevo"
export HTTPS_PROXY=""
export HTTP_PROXY=""
export https_proxy=""
export http_proxy=""

echo "================================================================"
echo "heilbron/d-tanh-no-lineage experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: 7b7c5f5e"
echo "A1_G: Arm A (Composition): Constructor, pair 1 — pipeline=heilbron_smooth_v1"
echo "A1_D: Arm A (Composition): Improver, pair 1 — pipeline=heilbron_smooth_v1"
echo "C1_G: Arm C (Gradient-in-prompt): Constructor, pair 1 — pipeline=heilbron_smooth_v1"
echo "C1_D: Arm C (Gradient-in-prompt): Improver, pair 1 — pipeline=heilbron_smooth_v1"
echo "================================================================"
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- A1_G config ---"
"$PYTHON" "$PROJ/run.py" \
    experiment=heilbron \
    problem.name=heilbron_smooth_v1/pop_a \
    pipeline=heilbron_smooth_v1 \
    prompts=default \
    redis.db=1 \
    stage_timeout=900 \
    dag_timeout=3600 \
    max_generations=200 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    stopper=max_generations \
    inner_iterations=1 \
    n_opponents=1 \
    source_prompt_k=1 \
    aggregator=heilbron_constructor \
    evolution=steady_state \
    stopper=max_generations \
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_smooth_v1/pop_b \
    feedback_mode=composition \
    population_role=constructor \
    'post_step_hook=${composition_injection_hook}' \
    opponent_result_mode=exec \
    opponent_sampling_mode=softmax \
    pipeline_builder.archive_reeval=false \
    'pipeline_builder.per_opponent_timeout=${stage_timeout}' \
    --cfg job \
    > "$LOG_DIR/cfg_run_A1_G.txt" 2>&1
cat "$LOG_DIR/cfg_run_A1_G.txt" | head -40
echo ""
echo "--- A1_D config ---"
"$PYTHON" "$PROJ/run.py" \
    experiment=heilbron \
    problem.name=heilbron_smooth_v1/pop_b \
    pipeline=heilbron_smooth_v1 \
    prompts=default \
    redis.db=2 \
    stage_timeout=900 \
    dag_timeout=3600 \
    max_generations=200 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    stopper=max_generations \
    inner_iterations=1 \
    n_opponents=1 \
    source_prompt_k=1 \
    aggregator=heilbron_improver \
    evolution=steady_state \
    stopper=max_generations \
    opponent_redis_db=1 \
    opponent_redis_prefix=heilbron_smooth_v1/pop_a \
    feedback_mode=composition \
    population_role=improver \
    opponent_result_mode=cached \
    opponent_sampling_mode=top_k \
    pipeline_builder.archive_reeval=true \
    engine_config.refresh_order=generation_bucketed \
    engine_config.refresh_passes=1 \
    pipeline_builder.disable_lineage_on_improver=true \
    --cfg job \
    > "$LOG_DIR/cfg_run_A1_D.txt" 2>&1
cat "$LOG_DIR/cfg_run_A1_D.txt" | head -40
echo ""
echo "--- C1_G config ---"
"$PYTHON" "$PROJ/run.py" \
    experiment=heilbron \
    problem.name=heilbron_smooth_v1/pop_a \
    pipeline=heilbron_smooth_v1 \
    prompts=default \
    redis.db=5 \
    stage_timeout=900 \
    dag_timeout=3600 \
    max_generations=200 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    stopper=max_generations \
    inner_iterations=1 \
    n_opponents=1 \
    source_prompt_k=1 \
    aggregator=heilbron_constructor \
    evolution=steady_state \
    stopper=max_generations \
    opponent_redis_db=6 \
    opponent_redis_prefix=heilbron_smooth_v1/pop_b \
    feedback_mode=gradient_in_prompt \
    population_role=constructor \
    opponent_result_mode=exec \
    opponent_sampling_mode=softmax \
    pipeline_builder.archive_reeval=false \
    'pipeline_builder.per_opponent_timeout=${stage_timeout}' \
    --cfg job \
    > "$LOG_DIR/cfg_run_C1_G.txt" 2>&1
cat "$LOG_DIR/cfg_run_C1_G.txt" | head -40
echo ""
echo "--- C1_D config ---"
"$PYTHON" "$PROJ/run.py" \
    experiment=heilbron \
    problem.name=heilbron_smooth_v1/pop_b \
    pipeline=heilbron_smooth_v1 \
    prompts=default \
    redis.db=6 \
    stage_timeout=900 \
    dag_timeout=3600 \
    max_generations=200 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    stopper=max_generations \
    inner_iterations=1 \
    n_opponents=1 \
    source_prompt_k=1 \
    aggregator=heilbron_improver \
    evolution=steady_state \
    stopper=max_generations \
    opponent_redis_db=5 \
    opponent_redis_prefix=heilbron_smooth_v1/pop_a \
    feedback_mode=gradient_in_prompt \
    population_role=improver \
    opponent_result_mode=cached \
    opponent_sampling_mode=top_k \
    pipeline_builder.archive_reeval=true \
    engine_config.refresh_order=generation_bucketed \
    engine_config.refresh_passes=1 \
    pipeline_builder.disable_lineage_on_improver=true \
    --cfg job \
    > "$LOG_DIR/cfg_run_C1_D.txt" 2>&1
cat "$LOG_DIR/cfg_run_C1_D.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run A1_G: Arm A (Composition): Constructor, pair 1
nohup "$PYTHON" "$PROJ/run.py" \
    experiment=heilbron \
    problem.name=heilbron_smooth_v1/pop_a \
    pipeline=heilbron_smooth_v1 \
    prompts=default \
    redis.db=1 \
    stage_timeout=900 \
    dag_timeout=3600 \
    max_generations=200 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    stopper=max_generations \
    inner_iterations=1 \
    n_opponents=1 \
    source_prompt_k=1 \
    aggregator=heilbron_constructor \
    evolution=steady_state \
    stopper=max_generations \
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_smooth_v1/pop_b \
    feedback_mode=composition \
    population_role=constructor \
    'post_step_hook=${composition_injection_hook}' \
    opponent_result_mode=exec \
    opponent_sampling_mode=softmax \
    pipeline_builder.archive_reeval=false \
    'pipeline_builder.per_opponent_timeout=${stage_timeout}' \
    > "$LOG_DIR/run_A1_G.log" 2>&1 &
PID_A1_G=$!
echo "Run A1_G started: PID=$PID_A1_G  DB=1  pipeline=heilbron_smooth_v1"

# ── Run A1_D: Arm A (Composition): Improver, pair 1
nohup "$PYTHON" "$PROJ/run.py" \
    experiment=heilbron \
    problem.name=heilbron_smooth_v1/pop_b \
    pipeline=heilbron_smooth_v1 \
    prompts=default \
    redis.db=2 \
    stage_timeout=900 \
    dag_timeout=3600 \
    max_generations=200 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    stopper=max_generations \
    inner_iterations=1 \
    n_opponents=1 \
    source_prompt_k=1 \
    aggregator=heilbron_improver \
    evolution=steady_state \
    stopper=max_generations \
    opponent_redis_db=1 \
    opponent_redis_prefix=heilbron_smooth_v1/pop_a \
    feedback_mode=composition \
    population_role=improver \
    opponent_result_mode=cached \
    opponent_sampling_mode=top_k \
    pipeline_builder.archive_reeval=true \
    engine_config.refresh_order=generation_bucketed \
    engine_config.refresh_passes=1 \
    pipeline_builder.disable_lineage_on_improver=true \
    > "$LOG_DIR/run_A1_D.log" 2>&1 &
PID_A1_D=$!
echo "Run A1_D started: PID=$PID_A1_D  DB=2  pipeline=heilbron_smooth_v1"

# ── Run C1_G: Arm C (Gradient-in-prompt): Constructor, pair 1
nohup "$PYTHON" "$PROJ/run.py" \
    experiment=heilbron \
    problem.name=heilbron_smooth_v1/pop_a \
    pipeline=heilbron_smooth_v1 \
    prompts=default \
    redis.db=5 \
    stage_timeout=900 \
    dag_timeout=3600 \
    max_generations=200 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    stopper=max_generations \
    inner_iterations=1 \
    n_opponents=1 \
    source_prompt_k=1 \
    aggregator=heilbron_constructor \
    evolution=steady_state \
    stopper=max_generations \
    opponent_redis_db=6 \
    opponent_redis_prefix=heilbron_smooth_v1/pop_b \
    feedback_mode=gradient_in_prompt \
    population_role=constructor \
    opponent_result_mode=exec \
    opponent_sampling_mode=softmax \
    pipeline_builder.archive_reeval=false \
    'pipeline_builder.per_opponent_timeout=${stage_timeout}' \
    > "$LOG_DIR/run_C1_G.log" 2>&1 &
PID_C1_G=$!
echo "Run C1_G started: PID=$PID_C1_G  DB=5  pipeline=heilbron_smooth_v1"

# ── Run C1_D: Arm C (Gradient-in-prompt): Improver, pair 1
nohup "$PYTHON" "$PROJ/run.py" \
    experiment=heilbron \
    problem.name=heilbron_smooth_v1/pop_b \
    pipeline=heilbron_smooth_v1 \
    prompts=default \
    redis.db=6 \
    stage_timeout=900 \
    dag_timeout=3600 \
    max_generations=200 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    evolution=steady_state \
    stopper=max_generations \
    inner_iterations=1 \
    n_opponents=1 \
    source_prompt_k=1 \
    aggregator=heilbron_improver \
    evolution=steady_state \
    stopper=max_generations \
    opponent_redis_db=5 \
    opponent_redis_prefix=heilbron_smooth_v1/pop_a \
    feedback_mode=gradient_in_prompt \
    population_role=improver \
    opponent_result_mode=cached \
    opponent_sampling_mode=top_k \
    pipeline_builder.archive_reeval=true \
    engine_config.refresh_order=generation_bucketed \
    engine_config.refresh_passes=1 \
    pipeline_builder.disable_lineage_on_improver=true \
    > "$LOG_DIR/run_C1_D.log" 2>&1 &
PID_C1_D=$!
echo "Run C1_D started: PID=$PID_C1_D  DB=6  pipeline=heilbron_smooth_v1"

echo ""
echo "================================================================"
echo "All 4 runs launched."
echo "PIDs: A1_G=$PID_A1_G  A1_D=$PID_A1_D  C1_G=$PID_C1_G  C1_D=$PID_C1_D"
echo "$PID_A1_G $PID_A1_D $PID_C1_G $PID_C1_D" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_A1_G 2>/dev/null || { echo "DEAD: A1_G (PID=$PID_A1_G)"; ALL_ALIVE=false; }
kill -0 $PID_A1_D 2>/dev/null || { echo "DEAD: A1_D (PID=$PID_A1_D)"; ALL_ALIVE=false; }
kill -0 $PID_C1_G 2>/dev/null || { echo "DEAD: C1_G (PID=$PID_C1_G)"; ALL_ALIVE=false; }
kill -0 $PID_C1_D 2>/dev/null || { echo "DEAD: C1_D (PID=$PID_C1_D)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e heilbron/d-tanh-no-lineage manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "A1_G A1_D C1_G C1_D"

echo ""
echo "Launch watchdog (CLI — loads .env, wires Telegram):"
echo "  nohup gigaevo -e heilbron/d-tanh-no-lineage watchdog \\"
echo "      > experiments/heilbron/d-tanh-no-lineage/watchdog.log 2>&1 &"
echo "================================================================"
