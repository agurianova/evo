#!/usr/bin/env bash
# GENERATED from experiment.yaml — do not edit manually.
#
# Experiment: hover/dynamic-crossover
# Branch: exp/hover-dynamic-crossover
#
# Runs: X1 (control, num_parents=1), X2, X3 (treatment, num_parents=2)
# All runs use llm=balanced (3 mutation servers shared via Redis DB 15)
# All runs use chains/hover/full (dynamic topology)

set -euo pipefail

PROJ="/workspace-SR008.fs2/mathemage/gigaevo-core"
PYTHON="/home/jovyan/envs/evo_fast/bin/python"
LOG_DIR="$PROJ/experiments/hover/dynamic-crossover"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.226.17.25,10.225.185.235,10.226.15.38,10.226.185.47,10.225.51.251"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"

# Chain LLM: load-balanced via comma-separated URLs (random per worker)
export HOVER_CHAIN_URL="http://10.226.17.25:8001/v1,http://10.226.17.25:8000/v1,http://10.225.185.235:8001/v1,http://10.225.185.235:8000/v1"

echo "================================================================"
echo "hover/dynamic-crossover experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "X1: control  — num_parents=1, pipeline=guided, DB=3"
echo "X2: treatment — num_parents=2, pipeline=guided, DB=4"
echo "X3: treatment — num_parents=2, pipeline=guided, DB=5"
echo "Mutation LLM: llm=balanced (3 endpoints, Redis DB 15)"
echo "Chain LLM: 4 endpoints via HOVER_CHAIN_URL"
echo "================================================================"
echo ""

# ── Preflight check (hard gate) ──────────────────────────────────────────
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/experiment/preflight_check.py" --experiment hover/dynamic-crossover
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
echo "--- X1 config (control, num_parents=1) ---"
cd "$PROJ"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=3 \
    stage_timeout=5000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm=balanced \
    mutation_mode=rewrite \
    --cfg job \
    > "$LOG_DIR/cfg_run_X1.txt" 2>&1
head -40 "$LOG_DIR/cfg_run_X1.txt"
echo ""

echo "--- X2 config (treatment, num_parents=2) ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=4 \
    stage_timeout=5000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=2 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm=balanced \
    mutation_mode=rewrite \
    --cfg job \
    > "$LOG_DIR/cfg_run_X2.txt" 2>&1
head -40 "$LOG_DIR/cfg_run_X2.txt"
echo ""

echo "--- X3 config (treatment, num_parents=2) ---"
"$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=5 \
    stage_timeout=5000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=2 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm=balanced \
    mutation_mode=rewrite \
    --cfg job \
    > "$LOG_DIR/cfg_run_X3.txt" 2>&1
head -40 "$LOG_DIR/cfg_run_X3.txt"
echo ""

echo "================================================================"
echo "Config verified."
echo "Launching runs..."
echo ""

# ── Launch from project root (Hydra resolves paths relative to CWD) ───────
cd "$PROJ"

# ── Run X1: control (num_parents=1)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=3 \
    stage_timeout=5000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm=balanced \
    mutation_mode=rewrite \
    > "$LOG_DIR/logs/X1.log" 2>&1 &
PID_X1=$!
echo "Run X1 started: PID=$PID_X1  DB=3  num_parents=1 (control)"

# ── Run X2: treatment (num_parents=2)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=4 \
    stage_timeout=5000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=2 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm=balanced \
    mutation_mode=rewrite \
    > "$LOG_DIR/logs/X2.log" 2>&1 &
PID_X2=$!
echo "Run X2 started: PID=$PID_X2  DB=4  num_parents=2 (treatment)"

# ── Run X3: treatment (num_parents=2)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hover/full \
    pipeline=guided \
    prompts=default \
    redis.db=5 \
    stage_timeout=5000 \
    dag_timeout=7200 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=2 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm=balanced \
    mutation_mode=rewrite \
    > "$LOG_DIR/logs/X3.log" 2>&1 &
PID_X3=$!
echo "Run X3 started: PID=$PID_X3  DB=5  num_parents=2 (treatment)"

echo ""
echo "================================================================"
echo "All 3 runs launched."
echo "PIDs: X1=$PID_X1  X2=$PID_X2  X3=$PID_X3"
echo "$PID_X1 $PID_X2 $PID_X3" > "$LOG_DIR/pids.txt"

# ── Verify all PIDs alive ──────────────────────────────────────────────────
sleep 5
ALL_ALIVE=true
kill -0 $PID_X1 2>/dev/null || { echo "DEAD: X1 (PID=$PID_X1)"; ALL_ALIVE=false; }
kill -0 $PID_X2 2>/dev/null || { echo "DEAD: X2 (PID=$PID_X2)"; ALL_ALIVE=false; }
kill -0 $PID_X3 2>/dev/null || { echo "DEAD: X3 (PID=$PID_X3)"; ALL_ALIVE=false; }
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive. Check logs."
    exit 1
fi
echo "All PIDs verified alive."

# ── Record PIDs in experiment.yaml ────────────────────────────────────────
gigaevo -e hover/dynamic-crossover manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "X1 X2 X3"

echo ""
echo "Launch watchdog:"
echo "  NO_PROXY=\"$NO_PROXY\" no_proxy=\"$NO_PROXY\" HOVER_CHAIN_URL=\"$HOVER_CHAIN_URL\" \\"
echo "  nohup $PYTHON experiments/hover/dynamic-crossover/run_watchdog.py \\"
echo "      > experiments/hover/dynamic-crossover/watchdog.log 2>&1 &"
echo "================================================================"
