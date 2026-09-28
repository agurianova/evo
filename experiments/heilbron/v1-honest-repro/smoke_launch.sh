#!/usr/bin/env bash
# Smoke test launcher for heilbron/v1-honest-repro (3 gens, DB 1, A1_G config).
set -euo pipefail
PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/heilbron/v1-honest-repro"
export NO_PROXY="localhost,127.0.0.1,10.232.30.185"
export no_proxy="$NO_PROXY"
export OPENAI_API_KEY="sk-gigaevo"
cd "$PROJ"
nohup "$PYTHON" run.py \
    experiment=heilbron \
    problem.name=heilbron_v1_honest/pop_a \
    pipeline=heilbron_v1_honest \
    prompts=default \
    redis.db=1 \
    stage_timeout=900 \
    dag_timeout=3600 \
    max_generations=3 \
    max_mutations_per_generation=2 \
    max_elites_per_generation=2 \
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
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_v1_honest/pop_b \
    feedback_mode=composition \
    population_role=constructor \
    'post_step_hook=${composition_injection_hook}' \
    opponent_result_mode=exec \
    'pipeline_builder.per_opponent_timeout=${stage_timeout}' \
    > "$LOG_DIR/smoke.log" 2>&1 &
echo $! > "$LOG_DIR/smoke.pid"
echo "Launched smoke PID=$(cat $LOG_DIR/smoke.pid)"
