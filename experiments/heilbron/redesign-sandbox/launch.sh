#!/usr/bin/env bash
# Sandbox launch — heilbron-adversarial redesign verification.
# 4 short runs (max_generations=8), K=L=3, archive_reeval=true,
# opponent_provider.cache_ttl=2.0.
#
# Pre-run gate (F37+F27): flush target Redis prefixes and assert
# dg_injected_pairs SCARD=0 before any process starts.

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
REDIS_CLI="/home/jovyan/.mlspace/envs/evo/bin/redis-cli"
EXP="heilbron/redesign-sandbox"
LOG_DIR="$PROJ/experiments/$EXP"

export NO_PROXY="localhost,127.0.0.1,api.github.com,10.232.30.185"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"
export OPENAI_API_KEY="sk-gigaevo"

# Hydra resolves problem.name=... relative to CWD; must run from project root.
cd "$PROJ"

echo "================================================================"
echo "$EXP launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Runs: A_G(db=1) A_D(db=2) B_G(db=3) B_D(db=4)"
echo "max_generations=8  K=L=3  archive_reeval=true  cache_ttl=2.0"
echo "================================================================"

# ── F37+F27: pre-run flush + invariant assertion ──────────────────────────
echo ""
echo "--- Pre-run flush (DBs 1-4) ---"
for db in 1 2 3 4; do
    "$REDIS_CLI" -n "$db" FLUSHDB > /dev/null
    echo "  flushed db=$db"
done

echo ""
echo "--- Pre-run invariant assertions ---"
"$PYTHON" - << 'PYEOF'
import sys, redis
expected_zero = [
    (1, "heilbron_adversarial/pop_a:dg_injected_pairs"),
    (1, "heilbron_adversarial/pop_a:dg_best_pairs"),
    (2, "heilbron_adversarial/pop_b:dg_injected_pairs"),
    (2, "heilbron_adversarial/pop_b:dg_best_pairs"),
    (3, "heilbron_adversarial/pop_a:dg_injected_pairs"),
    (3, "heilbron_adversarial/pop_a:dg_best_pairs"),
    (4, "heilbron_adversarial/pop_b:dg_injected_pairs"),
    (4, "heilbron_adversarial/pop_b:dg_best_pairs"),
]
fail = False
for db, key in expected_zero:
    r = redis.Redis(host="localhost", port=6379, db=db)
    n = r.scard(key) if r.type(key) == b"set" else (r.zcard(key) if r.type(key) == b"zset" else 0)
    if n != 0:
        print(f"  FAIL: db={db} key={key} card={n} (expected 0)")
        fail = True
    else:
        print(f"  OK:   db={db} key={key}")
gen_keys = []
for db in (1, 2, 3, 4):
    r = redis.Redis(host="localhost", port=6379, db=db)
    n = r.dbsize()
    print(f"  db={db} dbsize={n}")
    if n != 0:
        print(f"  FAIL: db={db} dbsize={n} after FLUSHDB")
        fail = True
sys.exit(1 if fail else 0)
PYEOF

if [ $? -ne 0 ]; then
    echo "ABORT: pre-run invariants failed."
    exit 1
fi
echo ""

# ── Config verification (--cfg job) ───────────────────────────────────────
for label in A_G A_D B_G B_D; do
    echo "--- $label config ---"
    case $label in
        A_G)
            "$PYTHON" "$PROJ/run.py" \
                problem.name=heilbron_adversarial/pop_a \
                pipeline=adversarial_asymmetric prompts=default \
                redis.db=1 stage_timeout=1800 dag_timeout=1800 \
                max_generations=8 max_mutations_per_generation=8 \
                max_elites_per_generation=8 num_parents=1 \
                model_name=Qwen3-235B-A22B-Thinking-2507 \
                llm_base_url="http://10.232.30.185:4000/v1" \
                mutation_mode=rewrite evolution=steady_state \
                opponent_redis_db=2 opponent_redis_prefix=heilbron_adversarial/pop_b \
                feedback_mode=composition population_role=constructor \
                n_opponents=3 source_prompt_k=3 pipeline_builder.archive_reeval=true \
                opponent_provider.cache_ttl=2.0 \
                'post_step_hook=${composition_injection_hook}' \
                --cfg job > "$LOG_DIR/cfg_$label.txt" 2>&1
            ;;
        A_D)
            "$PYTHON" "$PROJ/run.py" \
                problem.name=heilbron_adversarial/pop_b \
                pipeline=adversarial_asymmetric prompts=default \
                redis.db=2 stage_timeout=1800 dag_timeout=1800 \
                max_generations=8 max_mutations_per_generation=24 \
                max_elites_per_generation=8 num_parents=1 \
                model_name=Qwen3-235B-A22B-Thinking-2507 \
                llm_base_url="http://10.232.30.185:4000/v1" \
                mutation_mode=rewrite evolution=steady_state \
                sync_min_delta=1 \
                opponent_redis_db=1 opponent_redis_prefix=heilbron_adversarial/pop_a \
                feedback_mode=composition population_role=improver \
                d_sees_g_source=true d_archive_persistent=true \
                n_opponents=3 source_prompt_k=3 pipeline_builder.archive_reeval=true \
                opponent_provider.cache_ttl=2.0 \
                --cfg job > "$LOG_DIR/cfg_$label.txt" 2>&1
            ;;
        B_G)
            "$PYTHON" "$PROJ/run.py" \
                problem.name=heilbron_adversarial/pop_a \
                pipeline=adversarial_asymmetric prompts=default \
                redis.db=3 stage_timeout=1800 dag_timeout=1800 \
                max_generations=8 max_mutations_per_generation=8 \
                max_elites_per_generation=8 num_parents=1 \
                model_name=Qwen3-235B-A22B-Thinking-2507 \
                llm_base_url="http://10.232.30.185:4000/v1" \
                mutation_mode=rewrite evolution=steady_state \
                opponent_redis_db=4 opponent_redis_prefix=heilbron_adversarial/pop_b \
                feedback_mode=gradient_in_prompt population_role=constructor \
                n_opponents=3 source_prompt_k=3 pipeline_builder.archive_reeval=true \
                opponent_provider.cache_ttl=2.0 \
                --cfg job > "$LOG_DIR/cfg_$label.txt" 2>&1
            ;;
        B_D)
            "$PYTHON" "$PROJ/run.py" \
                problem.name=heilbron_adversarial/pop_b \
                pipeline=adversarial_asymmetric prompts=default \
                redis.db=4 stage_timeout=1800 dag_timeout=1800 \
                max_generations=8 max_mutations_per_generation=24 \
                max_elites_per_generation=8 num_parents=1 \
                model_name=Qwen3-235B-A22B-Thinking-2507 \
                llm_base_url="http://10.232.30.185:4000/v1" \
                mutation_mode=rewrite evolution=steady_state \
                sync_min_delta=1 \
                opponent_redis_db=3 opponent_redis_prefix=heilbron_adversarial/pop_a \
                feedback_mode=gradient_in_prompt population_role=improver \
                d_sees_g_source=true d_archive_persistent=true \
                n_opponents=3 source_prompt_k=3 pipeline_builder.archive_reeval=true \
                opponent_provider.cache_ttl=2.0 \
                --cfg job > "$LOG_DIR/cfg_$label.txt" 2>&1
            ;;
    esac
    head -5 "$LOG_DIR/cfg_$label.txt"
done
echo ""

# ── Launch ───────────────────────────────────────────────────────────────
echo "--- Launching runs ---"

# Per-arm Hydra run dirs prevent the second-resolution timestamp collision
# in setup_logger (gigaevo/utils/logger_setup.py), so each arm gets its own
# evolution_TIMESTAMP.log under outputs/sandbox/<label>/.
RUN_TS=$(date -u '+%Y%m%d_%H%M%S')
HYDRA_BASE="$PROJ/outputs/sandbox/${RUN_TS}"
mkdir -p "$HYDRA_BASE"

# A_G (composition, constructor)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric prompts=default \
    redis.db=1 stage_timeout=1800 dag_timeout=1800 \
    max_generations=8 max_mutations_per_generation=8 \
    max_elites_per_generation=8 num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite evolution=steady_state \
    opponent_redis_db=2 opponent_redis_prefix=heilbron_adversarial/pop_b \
    feedback_mode=composition population_role=constructor \
    n_opponents=3 source_prompt_k=3 pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    'post_step_hook=${composition_injection_hook}' \
    "hydra.run.dir=$HYDRA_BASE/A_G" \
    > "$LOG_DIR/run_A_G.log" 2>&1 &
PID_A_G=$!
echo "A_G PID=$PID_A_G db=1 composition/constructor hydra=$HYDRA_BASE/A_G"

# A_D (composition, improver)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric prompts=default \
    redis.db=2 stage_timeout=1800 dag_timeout=1800 \
    max_generations=8 max_mutations_per_generation=24 \
    max_elites_per_generation=8 num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite evolution=steady_state \
    sync_min_delta=1 \
    opponent_redis_db=1 opponent_redis_prefix=heilbron_adversarial/pop_a \
    feedback_mode=composition population_role=improver \
    d_sees_g_source=true d_archive_persistent=true \
    n_opponents=3 source_prompt_k=3 pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    "hydra.run.dir=$HYDRA_BASE/A_D" \
    > "$LOG_DIR/run_A_D.log" 2>&1 &
PID_A_D=$!
echo "A_D PID=$PID_A_D db=2 composition/improver hydra=$HYDRA_BASE/A_D"

# B_G (gradient_in_prompt, constructor)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_a \
    pipeline=adversarial_asymmetric prompts=default \
    redis.db=3 stage_timeout=1800 dag_timeout=1800 \
    max_generations=8 max_mutations_per_generation=8 \
    max_elites_per_generation=8 num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite evolution=steady_state \
    opponent_redis_db=4 opponent_redis_prefix=heilbron_adversarial/pop_b \
    feedback_mode=gradient_in_prompt population_role=constructor \
    n_opponents=3 source_prompt_k=3 pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    "hydra.run.dir=$HYDRA_BASE/B_G" \
    > "$LOG_DIR/run_B_G.log" 2>&1 &
PID_B_G=$!
echo "B_G PID=$PID_B_G db=3 gradient/constructor hydra=$HYDRA_BASE/B_G"

# B_D (gradient_in_prompt, improver)
nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=heilbron_adversarial/pop_b \
    pipeline=adversarial_asymmetric prompts=default \
    redis.db=4 stage_timeout=1800 dag_timeout=1800 \
    max_generations=8 max_mutations_per_generation=24 \
    max_elites_per_generation=8 num_parents=1 \
    model_name=Qwen3-235B-A22B-Thinking-2507 \
    llm_base_url="http://10.232.30.185:4000/v1" \
    mutation_mode=rewrite evolution=steady_state \
    sync_min_delta=1 \
    opponent_redis_db=3 opponent_redis_prefix=heilbron_adversarial/pop_a \
    feedback_mode=gradient_in_prompt population_role=improver \
    d_sees_g_source=true d_archive_persistent=true \
    n_opponents=3 source_prompt_k=3 pipeline_builder.archive_reeval=true \
    opponent_provider.cache_ttl=2.0 \
    "hydra.run.dir=$HYDRA_BASE/B_D" \
    > "$LOG_DIR/run_B_D.log" 2>&1 &
PID_B_D=$!
echo "B_D PID=$PID_B_D db=4 gradient/improver hydra=$HYDRA_BASE/B_D"

echo ""
echo "PIDs: A_G=$PID_A_G  A_D=$PID_A_D  B_G=$PID_B_G  B_D=$PID_B_D"
echo "$PID_A_G $PID_A_D $PID_B_G $PID_B_D" > "$LOG_DIR/pids.txt"

# Verify alive
sleep 5
ALL_ALIVE=true
for v in PID_A_G PID_A_D PID_B_G PID_B_D; do
    pid="${!v}"
    kill -0 "$pid" 2>/dev/null || { echo "DEAD: $v (PID=$pid)"; ALL_ALIVE=false; }
done
if [ "$ALL_ALIVE" = "false" ]; then
    echo "ABORT: not all runs alive."
    exit 1
fi
echo "All 4 PIDs verified alive."

# Record PIDs in manifest
gigaevo -e "$EXP" manifest record-pids --pids-file "$LOG_DIR/pids.txt" --labels "A_G A_D B_G B_D"

echo "================================================================"
echo "Sandbox launched. Tail logs:"
echo "  tail -f $LOG_DIR/run_*.log"
echo "After completion, run:"
echo "  bash $LOG_DIR/post_run_gate.sh"
echo "================================================================"
