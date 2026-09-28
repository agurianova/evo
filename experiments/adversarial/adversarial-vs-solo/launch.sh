#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: PYTHONPATH=. $GIGAEVO_PYTHON tools/experiment/generate_launch.py --experiment adversarial/adversarial-vs-solo
#
# Experiment: adversarial/adversarial-vs-solo
# Branch: exp/adversarial/adversarial-vs-solo
# PR: #203
# Pre-reg commit: d1f744d1d0c11c59c6c7f5426bacdc908c23cd32
#
# Runs: S1, S2, S3, S4

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG_DIR="$PROJ/experiments/adversarial/adversarial-vs-solo"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.232.30.185"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export OPENAI_API_KEY="sk-gigaevo"

echo "================================================================"
echo "adversarial/adversarial-vs-solo experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: d1f744d1d0c11c59c6c7f5426bacdc908c23cd32"
echo "S1: Solo arm: replicate 1 — pipeline=guided"
echo "S2: Solo arm: replicate 2 — pipeline=guided"
echo "S3: Solo arm: replicate 3 — pipeline=guided"
echo "S4: Solo arm: replicate 4 — pipeline=guided"
echo "================================================================"
echo ""

# ── Preflight check (hard gate) ──────────────────────────────────────────
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/experiment/preflight_check.py" --experiment adversarial/adversarial-vs-solo
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- S1 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_solo \
    pipeline=guided \
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
    pre_step_hook=null \
    --cfg job \
    > "$LOG_DIR/cfg_run_S1.txt" 2>&1
cat "$LOG_DIR/cfg_run_S1.txt" | head -40
echo ""
echo "--- S2 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_solo \
    pipeline=guided \
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
    pre_step_hook=null \
    --cfg job \
    > "$LOG_DIR/cfg_run_S2.txt" 2>&1
cat "$LOG_DIR/cfg_run_S2.txt" | head -40
echo ""
echo "--- S3 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_solo \
    pipeline=guided \
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
    pre_step_hook=null \
    --cfg job \
    > "$LOG_DIR/cfg_run_S3.txt" 2>&1
cat "$LOG_DIR/cfg_run_S3.txt" | head -40
echo ""
echo "--- S4 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_solo \
    pipeline=guided \
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
    pre_step_hook=null \
    --cfg job \
    > "$LOG_DIR/cfg_run_S4.txt" 2>&1
cat "$LOG_DIR/cfg_run_S4.txt" | head -40
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Launch runs ────────────────────────────────────────────────────────────
# ── Run S1: Solo arm: replicate 1
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_solo \
    pipeline=guided \
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
    pre_step_hook=null \
    > "$LOG_DIR/run_S1.log" 2>&1 &
PID_S1=$!
echo "Run S1 started: PID=$PID_S1  DB=1  pipeline=guided"

# ── Run S2: Solo arm: replicate 2
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_solo \
    pipeline=guided \
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
    pre_step_hook=null \
    > "$LOG_DIR/run_S2.log" 2>&1 &
PID_S2=$!
echo "Run S2 started: PID=$PID_S2  DB=2  pipeline=guided"

# ── Run S3: Solo arm: replicate 3
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_solo \
    pipeline=guided \
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
    pre_step_hook=null \
    > "$LOG_DIR/run_S3.log" 2>&1 &
PID_S3=$!
echo "Run S3 started: PID=$PID_S3  DB=3  pipeline=guided"

# ── Run S4: Solo arm: replicate 4
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_solo \
    pipeline=guided \
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
    pre_step_hook=null \
    > "$LOG_DIR/run_S4.log" 2>&1 &
PID_S4=$!
echo "Run S4 started: PID=$PID_S4  DB=4  pipeline=guided"

echo ""
echo "================================================================"
echo "All 4 runs launched."
echo "PIDs: S1=$PID_S1  S2=$PID_S2  S3=$PID_S3  S4=$PID_S4"
echo "$PID_S1 $PID_S2 $PID_S3 $PID_S4" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_S1 2>/dev/null || { echo "DEAD: S1 (PID=$PID_S1)"; ALL_ALIVE=false; }
kill -0 $PID_S2 2>/dev/null || { echo "DEAD: S2 (PID=$PID_S2)"; ALL_ALIVE=false; }
kill -0 $PID_S3 2>/dev/null || { echo "DEAD: S3 (PID=$PID_S3)"; ALL_ALIVE=false; }
kill -0 $PID_S4 2>/dev/null || { echo "DEAD: S4 (PID=$PID_S4)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e adversarial/adversarial-vs-solo manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "S1 S2 S3 S4"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/adversarial/adversarial-vs-solo/run_watchdog.py \\"
echo "      > experiments/adversarial/adversarial-vs-solo/watchdog.log 2>&1 &"
echo "================================================================"
