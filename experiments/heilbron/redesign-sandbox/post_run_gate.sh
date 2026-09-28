#!/usr/bin/env bash
# F35 hard end-of-run gate.
# Asserts both arms produced their downstream effect:
#   Arm A (composition): >= 1 [CompositionInjection] mutation_type=d_improvement
#   Arm B (gradient_in_prompt): >= 1 [GradientInPrompt] injecting ... source=per-program
# Either zero ⇒ that arm silently degraded to non-adversarial behavior.

set -uo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
LOG_DIR="$PROJ/experiments/heilbron/redesign-sandbox"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
REDIS_CLI="/home/jovyan/.mlspace/envs/evo/bin/redis-cli"

echo "================================================================"
echo "F35 end-of-run gate — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "================================================================"

fail=0

# Count via tr-wc (avoids grep -c newlines). -c prints to stdout one line per file;
# we chain tr + wc to get a clean integer.
count_pattern() {
    local pattern="$1" file="$2"
    [ -f "$file" ] || { echo 0; return; }
    grep -c -F "$pattern" "$file" 2>/dev/null | tr -d '[:space:]' | head -c 10
}

# Arm A: composition injections must fire on G run (A_G).
# Redis is the source of truth — nohup block-buffers stdout, so logs may lag.
n_inj_log=$(count_pattern "mutation_type=d_improvement" "$LOG_DIR/run_A_G.log")
n_inj_log=${n_inj_log:-0}
n_inj_redis=$("$PYTHON" -c "import redis; r=redis.Redis(host='localhost',port=6379,db=1); print(r.scard('heilbron_adversarial/pop_a:dg_injected_pairs'))" 2>/dev/null)
n_inj_redis=${n_inj_redis:-0}
echo "[Arm A] CompositionInjection events  log=$n_inj_log  redis_dg_injected_pairs(db=1)=$n_inj_redis"
if [ "${n_inj_log:-0}" -lt 1 ] 2>/dev/null && [ "${n_inj_redis:-0}" -lt 1 ] 2>/dev/null; then
    echo "  FAIL: composition arm produced ZERO injections (log AND redis) — Lamarckian transfer dark."
    fail=1
fi

# Arm B: per-program gradient hits must fire on G run (B_G).
# For Arm B, log grep is reliable (GradientInPromptStage is inside DAG, not post-hook)
# but we also cross-check via Redis dg_best_pairs on B's D-side (db=4) > 0.
n_pp=$(count_pattern "source=per-program" "$LOG_DIR/run_B_G.log")
n_gl=$(count_pattern "source=global" "$LOG_DIR/run_B_G.log")
n_pp=${n_pp:-0}; n_gl=${n_gl:-0}
n_bbest=$("$PYTHON" -c "import redis; r=redis.Redis(host='localhost',port=6379,db=4); print(r.zcard('heilbron_adversarial/pop_b:dg_best_pairs'))" 2>/dev/null)
n_bbest=${n_bbest:-0}
echo "[Arm B] GradientInPrompt per-program hits: log=$n_pp  global_fallbacks=$n_gl  redis_dg_best_pairs(db=4)=$n_bbest"
if [ "${n_pp:-0}" -lt 1 ] 2>/dev/null && [ "${n_bbest:-0}" -lt 1 ] 2>/dev/null; then
    echo "  FAIL: gradient_in_prompt arm produced ZERO per-program hits — DGTracker dark."
    fail=1
fi

# Tracker forensic via Python redis (redis-cli may not be in PATH).
echo ""
echo "[Tracker] dg_improvements:* and dg_best_pairs cardinality:"
py_out=$("$PYTHON" - << 'PYEOF' 2>&1
import redis, sys
fail = False
for db, lbl in [(2, "A_D"), (4, "B_D")]:
    r = redis.Redis(host="localhost", port=6379, db=db)
    n_imp = sum(1 for _ in r.scan_iter(match="*:dg_improvements:*"))
    try:
        n_best = r.zcard("heilbron_adversarial/pop_b:dg_best_pairs")
    except Exception:
        n_best = 0
    print(f"  db={db} ({lbl}): dg_improvements_keys={n_imp} dg_best_pairs_zcard={n_best}")
    if n_imp < 1:
        print(f"    FAIL: dg_improvements empty on db={db} — DGTrackerStage never recorded.")
        fail = True
sys.exit(1 if fail else 0)
PYEOF
)
py_rc=$?
echo "$py_out"
if [ $py_rc -ne 0 ]; then
    fail=1
fi

echo ""
if [ "$fail" -ne 0 ]; then
    echo "================================================================"
    echo "GATE FAILED. Sandbox results NOT trustworthy."
    echo "================================================================"
    exit 1
fi
echo "================================================================"
echo "F35 gate PASSED — both arms produced downstream effects."
echo "================================================================"
