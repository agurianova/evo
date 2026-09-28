#!/usr/bin/env bash
# Run gen-50 final test evaluations for all 4 P1×P2 runs.
#
# Pre-registration §§4-6: extract best-by-val program, evaluate on test set,
# write results to experiments/hotpotqa_p1p2/test_evals/results.json.
#
# Usage:
#   bash experiments/hotpotqa_p1p2/run_test_eval.sh
#
# Prereqs: all 4 runs at gen 50 (or crashed/stalled at final gen).

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-$(command -v python3)}
EVAL_SCRIPT="$PROJ/experiments/hotpotqa_thinking/gen10_test_eval.py"
RESULTS_PATH="$PROJ/experiments/hotpotqa_p1p2/test_evals/results.json"
LOG_DIR="$PROJ/experiments/hotpotqa_p1p2/test_evals"
SEED_DIR="$PROJ/experiments/hotpotqa_thinking/seeds/ddce37b4"

# Chain servers (same as launch.sh — one per run, to minimize server variance)
CHAIN_URL_E="http://10.226.17.25:8001/v1"
CHAIN_URL_F="http://10.226.17.25:8000/v1"
CHAIN_URL_G="http://10.225.185.235:8001/v1"
CHAIN_URL_H="http://10.225.185.235:8000/v1"

# All LLM endpoints must bypass Squid proxy
export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"

echo "NO_PROXY=$NO_PROXY"
echo ""

# ── Archive stale logs from failed first attempt (2026-03-02) ─────────────────
STALE_LOGS=("$LOG_DIR/run_E_test.log" "$LOG_DIR/run_F_test.log" "$LOG_DIR/run_G_test.log" "$LOG_DIR/run_H_test.log")
ARCHIVE_DIR="$LOG_DIR/archive_failed_attempt_20260302"
for f in "${STALE_LOGS[@]}"; do
    if [ -f "$f" ]; then
        mkdir -p "$ARCHIVE_DIR"
        mv "$f" "$ARCHIVE_DIR/"
        echo "[cleanup] Archived stale log: $(basename "$f") → archive_failed_attempt_20260302/"
    fi
done
echo ""

# ── Preflight: thinking-mode verification on all 4 chain endpoints ────────────
# Critical: servers may have restarted in non-thinking mode since evolution.
# E/F share server 10.226.17.25; G/H share 10.225.185.235. A single restart
# in non-thinking mode would create a differential confound between server groups.
echo "[preflight] Verifying thinking mode on all 4 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_E" "$CHAIN_URL_F" "$CHAIN_URL_G" "$CHAIN_URL_H"; do
    HOST="${CHAIN_URL#http://}"; HOST="${HOST%%/*}"; HOST="${HOST%%:*}"
    RESPONSE=$(curl --noproxy "$HOST" -s --connect-timeout 10 --max-time 90 \
        -X POST "$CHAIN_URL/chat/completions" \
        -H "Authorization: Bearer None" \
        -H "Content-Type: application/json" \
        -d '{"model":"Qwen/Qwen3-8B","messages":[{"role":"user","content":"What is 2+2? Answer:"}],"max_tokens":200,"temperature":0.1}' \
        2>/dev/null || echo "CURL_FAIL")
    if echo "$RESPONSE" | grep -q "<think>"; then
        echo "[preflight] OK: $CHAIN_URL (thinking mode confirmed)"
    else
        echo "[preflight] FAIL: $CHAIN_URL NOT in thinking mode — aborting."
        echo "[preflight] Response: ${RESPONSE:0:200}"
        exit 1
    fi
done
echo "[preflight] All chain endpoints verified."
echo ""

# ── Seed retest calibration (pre-registration §5) ────────────────────────────
# Re-evaluate gen-0 seed on Run E's fixed-300 val set to establish post-fix
# retest noise floor. Uses val set (not test set) — not a protocol violation.
echo "[calibration] Evaluating gen-0 seed (ddce37b4) on E's fixed-300 val set..."
echo "[calibration] Expected gen-0 val EM: ~62.7% (pre-fix) or ~60.0% (post-fix)"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_E" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label E_seed_retest \
    --redis-db 10 \
    --redis-prefix chains/hotpotqa/static \
    --max-gen 0 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --use-val-set \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/seed_retest_val.log"
echo ""

# ── Run E: control (no P1, no P2) — fixed-300 val ────────────────────────────
echo "================================================================"
echo "[E] chains/hotpotqa/static  db=10  chain=$CHAIN_URL_E"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_E" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label E \
    --redis-db 10 \
    --redis-prefix chains/hotpotqa/static \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_E.log"
echo ""

# ── Run F: P2 only (ASI) — fixed-300 val ─────────────────────────────────────
echo "================================================================"
echo "[F] chains/hotpotqa/static_a  db=11  chain=$CHAIN_URL_F"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_F" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label F \
    --redis-db 11 \
    --redis-prefix chains/hotpotqa/static_a \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_F.log"
echo ""

# ── Run G: P1 only (val rotation) — hash-seeded val ──────────────────────────
echo "================================================================"
echo "[G] chains/hotpotqa/static_r  db=12  chain=$CHAIN_URL_G"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_G" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label G \
    --redis-db 12 \
    --redis-prefix chains/hotpotqa/static_r \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset hash_seeded_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_G.log"
echo ""

# ── Run H: P1+P2 (rotation + ASI) — hash-seeded val ─────────────────────────
echo "================================================================"
echo "[H] chains/hotpotqa/static_ra  db=13  chain=$CHAIN_URL_H"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_H" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label H \
    --redis-db 13 \
    --redis-prefix chains/hotpotqa/static_ra \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset hash_seeded_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_H.log"
echo ""

echo "================================================================"
echo "All test evals complete."
echo "Results: $RESULTS_PATH"
echo "Logs:    $LOG_DIR/test_eval_{E,F,G,H}.log"
echo "================================================================"
