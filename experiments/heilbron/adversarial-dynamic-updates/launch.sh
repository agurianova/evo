#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: PYTHONPATH=. $GIGAEVO_PYTHON tools/experiment/generate_launch.py --experiment heilbron/adversarial-dynamic-updates
#
# Experiment: heilbron/adversarial-dynamic-updates
# Branch: exp/heilbron/adversarial-dynamic-updates
# PR: #197
# Pre-reg commit: ebc12cc3
#
# Runs: SOFT_RE_A, SOFT_RE_B, SOFT_C_A, SOFT_C_B, GAN_RE_A, GAN_RE_B, GAN_C_A, GAN_C_B

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/heilbron/adversarial-dynamic-updates"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.232.30.185"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export GIGAEVO_PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
export OPENAI_API_KEY="sk-gigaevo"

echo "================================================================"
echo "heilbron/adversarial-dynamic-updates experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: ebc12cc3"
echo "SOFT_RE_A: Cell SOFT_RE: G=soft quality+resistance, re-eval ON — Constructor (Pop A soft) — pipeline=adversarial_coevo_feedback"
echo "SOFT_RE_B: Cell SOFT_RE: G=soft quality+resistance, re-eval ON — Improver (Pop B soft) — pipeline=adversarial_coevo_feedback"
echo "SOFT_C_A: Cell SOFT_C: G=soft quality+resistance, re-eval OFF — Constructor (Pop A soft) — pipeline=adversarial_coevo_feedback"
echo "SOFT_C_B: Cell SOFT_C: G=soft quality+resistance, re-eval OFF — Improver (Pop B soft) — pipeline=adversarial_coevo_feedback"
echo "GAN_RE_A: Cell GAN_RE: G=strict GAN pure resistance, re-eval ON — Constructor (Pop A GAN) — pipeline=adversarial_coevo_feedback"
echo "GAN_RE_B: Cell GAN_RE: G=strict GAN pure resistance, re-eval ON — Improver (Pop B soft) — pipeline=adversarial_coevo_feedback"
echo "GAN_C_A: Cell GAN_C: G=strict GAN pure resistance, re-eval OFF — Constructor (Pop A GAN) — pipeline=adversarial_coevo_feedback"
echo "GAN_C_B: Cell GAN_C: G=strict GAN pure resistance, re-eval OFF — Improver (Pop B soft) — pipeline=adversarial_coevo_feedback"
echo "================================================================"
echo ""

# ── Preflight check (hard gate) ──────────────────────────────────────────
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/experiment/preflight_check.py" --experiment heilbron/adversarial-dynamic-updates
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- SOFT_RE_A config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a_soft \
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
    pipeline_builder.archive_reeval=true \
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_adversarial/pop_b_soft \
    opponent_feedback_k=3 \
    population_role=constructor \
    --cfg job \
    > "$LOG_DIR/cfg_run_SOFT_RE_A.txt" 2>&1
cat "$LOG_DIR/cfg_run_SOFT_RE_A.txt" | head -40
echo ""
echo "--- SOFT_RE_B config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b_soft \
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
    pipeline_builder.archive_reeval=true \
    opponent_redis_db=1 \
    opponent_redis_prefix=heilbron_adversarial/pop_a_soft \
    opponent_feedback_k=3 \
    population_role=improver \
    --cfg job \
    > "$LOG_DIR/cfg_run_SOFT_RE_B.txt" 2>&1
cat "$LOG_DIR/cfg_run_SOFT_RE_B.txt" | head -40
echo ""
echo "--- SOFT_C_A config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a_soft \
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
    pipeline_builder.archive_reeval=false \
    opponent_redis_db=4 \
    opponent_redis_prefix=heilbron_adversarial/pop_b_soft \
    opponent_feedback_k=3 \
    population_role=constructor \
    --cfg job \
    > "$LOG_DIR/cfg_run_SOFT_C_A.txt" 2>&1
cat "$LOG_DIR/cfg_run_SOFT_C_A.txt" | head -40
echo ""
echo "--- SOFT_C_B config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b_soft \
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
    pipeline_builder.archive_reeval=false \
    opponent_redis_db=3 \
    opponent_redis_prefix=heilbron_adversarial/pop_a_soft \
    opponent_feedback_k=3 \
    population_role=improver \
    --cfg job \
    > "$LOG_DIR/cfg_run_SOFT_C_B.txt" 2>&1
cat "$LOG_DIR/cfg_run_SOFT_C_B.txt" | head -40
echo ""
echo "--- GAN_RE_A config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a_gan \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=5 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    pipeline_builder.archive_reeval=true \
    opponent_redis_db=6 \
    opponent_redis_prefix=heilbron_adversarial/pop_b_soft \
    opponent_feedback_k=3 \
    population_role=constructor \
    --cfg job \
    > "$LOG_DIR/cfg_run_GAN_RE_A.txt" 2>&1
cat "$LOG_DIR/cfg_run_GAN_RE_A.txt" | head -40
echo ""
echo "--- GAN_RE_B config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b_soft \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=6 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    pipeline_builder.archive_reeval=true \
    opponent_redis_db=5 \
    opponent_redis_prefix=heilbron_adversarial/pop_a_gan \
    opponent_feedback_k=3 \
    population_role=improver \
    --cfg job \
    > "$LOG_DIR/cfg_run_GAN_RE_B.txt" 2>&1
cat "$LOG_DIR/cfg_run_GAN_RE_B.txt" | head -40
echo ""
echo "--- GAN_C_A config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a_gan \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=7 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    pipeline_builder.archive_reeval=false \
    opponent_redis_db=8 \
    opponent_redis_prefix=heilbron_adversarial/pop_b_soft \
    opponent_feedback_k=3 \
    population_role=constructor \
    --cfg job \
    > "$LOG_DIR/cfg_run_GAN_C_A.txt" 2>&1
cat "$LOG_DIR/cfg_run_GAN_C_A.txt" | head -40
echo ""
echo "--- GAN_C_B config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b_soft \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=8 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    pipeline_builder.archive_reeval=false \
    opponent_redis_db=7 \
    opponent_redis_prefix=heilbron_adversarial/pop_a_gan \
    opponent_feedback_k=3 \
    population_role=improver \
    --cfg job \
    > "$LOG_DIR/cfg_run_GAN_C_B.txt" 2>&1
cat "$LOG_DIR/cfg_run_GAN_C_B.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run SOFT_RE_A: Cell SOFT_RE: G=soft quality+resistance, re-eval ON — Constructor (Pop A soft)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a_soft \
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
    pipeline_builder.archive_reeval=true \
    opponent_redis_db=2 \
    opponent_redis_prefix=heilbron_adversarial/pop_b_soft \
    opponent_feedback_k=3 \
    population_role=constructor \
    > "$LOG_DIR/run_SOFT_RE_A.log" 2>&1 &
PID_SOFT_RE_A=$!
echo "Run SOFT_RE_A started: PID=$PID_SOFT_RE_A  DB=1  pipeline=adversarial_coevo_feedback"

# ── Run SOFT_RE_B: Cell SOFT_RE: G=soft quality+resistance, re-eval ON — Improver (Pop B soft)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b_soft \
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
    pipeline_builder.archive_reeval=true \
    opponent_redis_db=1 \
    opponent_redis_prefix=heilbron_adversarial/pop_a_soft \
    opponent_feedback_k=3 \
    population_role=improver \
    > "$LOG_DIR/run_SOFT_RE_B.log" 2>&1 &
PID_SOFT_RE_B=$!
echo "Run SOFT_RE_B started: PID=$PID_SOFT_RE_B  DB=2  pipeline=adversarial_coevo_feedback"

# ── Run SOFT_C_A: Cell SOFT_C: G=soft quality+resistance, re-eval OFF — Constructor (Pop A soft)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a_soft \
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
    pipeline_builder.archive_reeval=false \
    opponent_redis_db=4 \
    opponent_redis_prefix=heilbron_adversarial/pop_b_soft \
    opponent_feedback_k=3 \
    population_role=constructor \
    > "$LOG_DIR/run_SOFT_C_A.log" 2>&1 &
PID_SOFT_C_A=$!
echo "Run SOFT_C_A started: PID=$PID_SOFT_C_A  DB=3  pipeline=adversarial_coevo_feedback"

# ── Run SOFT_C_B: Cell SOFT_C: G=soft quality+resistance, re-eval OFF — Improver (Pop B soft)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b_soft \
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
    pipeline_builder.archive_reeval=false \
    opponent_redis_db=3 \
    opponent_redis_prefix=heilbron_adversarial/pop_a_soft \
    opponent_feedback_k=3 \
    population_role=improver \
    > "$LOG_DIR/run_SOFT_C_B.log" 2>&1 &
PID_SOFT_C_B=$!
echo "Run SOFT_C_B started: PID=$PID_SOFT_C_B  DB=4  pipeline=adversarial_coevo_feedback"

# ── Run GAN_RE_A: Cell GAN_RE: G=strict GAN pure resistance, re-eval ON — Constructor (Pop A GAN)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a_gan \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=5 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    pipeline_builder.archive_reeval=true \
    opponent_redis_db=6 \
    opponent_redis_prefix=heilbron_adversarial/pop_b_soft \
    opponent_feedback_k=3 \
    population_role=constructor \
    > "$LOG_DIR/run_GAN_RE_A.log" 2>&1 &
PID_GAN_RE_A=$!
echo "Run GAN_RE_A started: PID=$PID_GAN_RE_A  DB=5  pipeline=adversarial_coevo_feedback"

# ── Run GAN_RE_B: Cell GAN_RE: G=strict GAN pure resistance, re-eval ON — Improver (Pop B soft)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b_soft \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=6 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    pipeline_builder.archive_reeval=true \
    opponent_redis_db=5 \
    opponent_redis_prefix=heilbron_adversarial/pop_a_gan \
    opponent_feedback_k=3 \
    population_role=improver \
    > "$LOG_DIR/run_GAN_RE_B.log" 2>&1 &
PID_GAN_RE_B=$!
echo "Run GAN_RE_B started: PID=$PID_GAN_RE_B  DB=6  pipeline=adversarial_coevo_feedback"

# ── Run GAN_C_A: Cell GAN_C: G=strict GAN pure resistance, re-eval OFF — Constructor (Pop A GAN)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a_gan \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=7 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    pipeline_builder.archive_reeval=false \
    opponent_redis_db=8 \
    opponent_redis_prefix=heilbron_adversarial/pop_b_soft \
    opponent_feedback_k=3 \
    population_role=constructor \
    > "$LOG_DIR/run_GAN_C_A.log" 2>&1 &
PID_GAN_C_A=$!
echo "Run GAN_C_A started: PID=$PID_GAN_C_A  DB=7  pipeline=adversarial_coevo_feedback"

# ── Run GAN_C_B: Cell GAN_C: G=strict GAN pure resistance, re-eval OFF — Improver (Pop B soft)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b_soft \
    pipeline=adversarial_coevo_feedback \
    prompts=default \
    redis.db=8 \
    stage_timeout=3000 \
    dag_timeout=7200 \
    max_generations=75 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite \
    pipeline_builder.archive_reeval=false \
    opponent_redis_db=7 \
    opponent_redis_prefix=heilbron_adversarial/pop_a_gan \
    opponent_feedback_k=3 \
    population_role=improver \
    > "$LOG_DIR/run_GAN_C_B.log" 2>&1 &
PID_GAN_C_B=$!
echo "Run GAN_C_B started: PID=$PID_GAN_C_B  DB=8  pipeline=adversarial_coevo_feedback"

echo ""
echo "================================================================"
echo "All 8 runs launched."
echo "PIDs: SOFT_RE_A=$PID_SOFT_RE_A  SOFT_RE_B=$PID_SOFT_RE_B  SOFT_C_A=$PID_SOFT_C_A  SOFT_C_B=$PID_SOFT_C_B  GAN_RE_A=$PID_GAN_RE_A  GAN_RE_B=$PID_GAN_RE_B  GAN_C_A=$PID_GAN_C_A  GAN_C_B=$PID_GAN_C_B"
echo "$PID_SOFT_RE_A $PID_SOFT_RE_B $PID_SOFT_C_A $PID_SOFT_C_B $PID_GAN_RE_A $PID_GAN_RE_B $PID_GAN_C_A $PID_GAN_C_B" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_SOFT_RE_A 2>/dev/null || { echo "DEAD: SOFT_RE_A (PID=$PID_SOFT_RE_A)"; ALL_ALIVE=false; }
kill -0 $PID_SOFT_RE_B 2>/dev/null || { echo "DEAD: SOFT_RE_B (PID=$PID_SOFT_RE_B)"; ALL_ALIVE=false; }
kill -0 $PID_SOFT_C_A 2>/dev/null || { echo "DEAD: SOFT_C_A (PID=$PID_SOFT_C_A)"; ALL_ALIVE=false; }
kill -0 $PID_SOFT_C_B 2>/dev/null || { echo "DEAD: SOFT_C_B (PID=$PID_SOFT_C_B)"; ALL_ALIVE=false; }
kill -0 $PID_GAN_RE_A 2>/dev/null || { echo "DEAD: GAN_RE_A (PID=$PID_GAN_RE_A)"; ALL_ALIVE=false; }
kill -0 $PID_GAN_RE_B 2>/dev/null || { echo "DEAD: GAN_RE_B (PID=$PID_GAN_RE_B)"; ALL_ALIVE=false; }
kill -0 $PID_GAN_C_A 2>/dev/null || { echo "DEAD: GAN_C_A (PID=$PID_GAN_C_A)"; ALL_ALIVE=false; }
kill -0 $PID_GAN_C_B 2>/dev/null || { echo "DEAD: GAN_C_B (PID=$PID_GAN_C_B)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e heilbron/adversarial-dynamic-updates manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "SOFT_RE_A SOFT_RE_B SOFT_C_A SOFT_C_B GAN_RE_A GAN_RE_B GAN_C_A GAN_C_B"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/heilbron/adversarial-dynamic-updates/run_watchdog.py \\"
echo "      > experiments/heilbron/adversarial-dynamic-updates/watchdog.log 2>&1 &"
echo "================================================================"
