#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
# Regenerate: PYTHONPATH=. $GIGAEVO_PYTHON tools/experiment/generate_launch.py --experiment hover/steady-state-validation
#
# Experiment: hover/steady-state-validation
# Branch: exp/hover-steady-state-validation
# PR: #133
# Pre-reg commit: b1d108b47dc9a7298cb1f367d222585ba6c3761e
#
# Runs: S1, S2, S3, S4

set -euo pipefail

PROJ="/workspace-SR008.fs2/mathemage/gigaevo-core"
PYTHON="/home/jovyan/envs/evo_fast/bin/python"
LOG_DIR="$PROJ/experiments/hover/steady-state-validation"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.226.17.25,10.225.185.235,10.226.15.38,10.226.185.47,10.225.51.251"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Task-specific environment variables (from experiment.yaml custom_env)
export HOVER_CHAIN_URL="http://10.226.17.25:8001/v1,http://10.226.17.25:8000/v1,http://10.225.185.235:8001/v1,http://10.225.185.235:8000/v1"

echo "================================================================"
echo "hover/steady-state-validation experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: b1d108b47dc9a7298cb1f367d222585ba6c3761e"
echo "S1: control — pipeline=guided"
echo "S2: control — pipeline=guided"
echo "S3: treatment — pipeline=guided"
echo "S4: treatment — pipeline=guided"
echo "================================================================"
echo ""

# ── Preflight check (hard gate) ──────────────────────────────────────────
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/experiment/preflight_check.py" --experiment hover/steady-state-validation
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- S1 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=6 \
    stage_timeout=3600 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="None" \
    mutation_mode=rewrite \
    llm=balanced \
    --cfg job \
    > "$LOG_DIR/cfg_run_S1.txt" 2>&1
cat "$LOG_DIR/cfg_run_S1.txt" | head -40
echo ""
echo "--- S2 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=7 \
    stage_timeout=3600 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="None" \
    mutation_mode=rewrite \
    llm=balanced \
    --cfg job \
    > "$LOG_DIR/cfg_run_S2.txt" 2>&1
cat "$LOG_DIR/cfg_run_S2.txt" | head -40
echo ""
echo "--- S3 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=8 \
    stage_timeout=3600 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="None" \
    mutation_mode=rewrite \
    evolution=steady_state \
    llm=balanced \
    --cfg job \
    > "$LOG_DIR/cfg_run_S3.txt" 2>&1
cat "$LOG_DIR/cfg_run_S3.txt" | head -40
echo ""
echo "--- S4 config ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=9 \
    stage_timeout=3600 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="None" \
    mutation_mode=rewrite \
    evolution=steady_state \
    llm=balanced \
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
# ── Run S1: control
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=6 \
    stage_timeout=3600 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="None" \
    mutation_mode=rewrite \
    llm=balanced \
    > "$LOG_DIR/logs/S1.log" 2>&1 &
PID_S1=$!
echo "Run S1 started: PID=$PID_S1  DB=6  pipeline=guided"

# ── Run S2: control
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=7 \
    stage_timeout=3600 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="None" \
    mutation_mode=rewrite \
    llm=balanced \
    > "$LOG_DIR/logs/S2.log" 2>&1 &
PID_S2=$!
echo "Run S2 started: PID=$PID_S2  DB=7  pipeline=guided"

# ── Run S3: treatment
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=8 \
    stage_timeout=3600 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="None" \
    mutation_mode=rewrite \
    evolution=steady_state \
    llm=balanced \
    > "$LOG_DIR/logs/S3.log" 2>&1 &
PID_S3=$!
echo "Run S3 started: PID=$PID_S3  DB=8  pipeline=guided"

# ── Run S4: treatment
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=9 \
    stage_timeout=3600 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="None" \
    mutation_mode=rewrite \
    evolution=steady_state \
    llm=balanced \
    > "$LOG_DIR/logs/S4.log" 2>&1 &
PID_S4=$!
echo "Run S4 started: PID=$PID_S4  DB=9  pipeline=guided"

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
gigaevo -e hover/steady-state-validation manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "S1 S2 S3 S4"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" \\"
echo "  nohup $PYTHON experiments/hover/steady-state-validation/run_watchdog.py \\"
echo "      > experiments/hover/steady-state-validation/watchdog.log 2>&1 &"
echo "================================================================"
