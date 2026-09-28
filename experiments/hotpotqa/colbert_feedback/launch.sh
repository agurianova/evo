#!/usr/bin/env bash
# Launch script for colbert_feedback experiment — 3 cold-start ColBERT+rich-feedback runs (U1, U3, U4).
#
# COLD START: NO program_loader.problem_dir override.
# program_loader resolves to problems/chains/hotpotqa/static_colbert_f1_600/initial_programs/baseline.py
#
# Node 10.226.15.38 is dedicated to GPU ColBERT serving (not used as mutation LLM).
# U2 (which used 10.226.15.38 as mutation LLM) is dropped.
# HOTPOTQA_COLBERT_SERVER_URL points to 10.226.15.38 so exec_runners on any node reach it.
#
# Pre-registration commit: 20c8314
# Branch: exp/hotpotqa-colbert-feedback
# PR: #76
#
# Usage: bash experiments/hotpotqa/colbert_feedback/launch.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=/home/jovyan/envs/evo_fast/bin/python
LOG_DIR="$PROJ/experiments/hotpotqa/colbert_feedback"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.47,10.225.51.251,api.github.com"
export no_proxy="$NO_PROXY"
export GIGAEVO_PYTHON="$PYTHON"
# CUDA_HOME required so exec_runner workers can load ColBERT C++ extensions
export CUDA_HOME=/home/jovyan/envs/evo_fast
# CUDA_VISIBLE_DEVICES intentionally not set here — colbert_server.py assigns
# one GPU per worker subprocess (GPUs 0-7) in --num-gpus 8 mode.

# Chain LLMs (Qwen3-8B, thinking mode)
CHAIN_URL_U1="http://10.226.17.25:8001/v1"
CHAIN_URL_U3="http://10.225.185.235:8001/v1"
CHAIN_URL_U4="http://10.225.185.235:8000/v1"

# Mutation LLMs (Qwen3-235B, one per run)
# NOTE: 10.226.15.38 (this node) is reserved for ColBERT GPU serving — not used as mut LLM.
MUT_U1="10.226.72.211"
MUT_U3="10.226.185.47"
MUT_U4="10.225.51.251"

echo "================================================================"
echo "colbert_feedback experiment launch — $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "Pre-reg commit: 20c8314  (Amendment 2: U3 mut IP corrected)"
echo "COLD START: no program_loader.problem_dir override"
echo "================================================================"
echo ""

# ── Preflight: vLLM servers reachable ─────────────────────────────────────────
echo "[preflight] Checking all 6 vLLM servers..."
for ep in \
    "$CHAIN_URL_U1" "$CHAIN_URL_U3" "$CHAIN_URL_U4" \
    "http://$MUT_U1:8777/v1" "http://$MUT_U3:8777/v1" "http://$MUT_U4:8777/v1"; do
    HOST="${ep#http://}"; HOST="${HOST%%/*}"; HOST="${HOST%%:*}"
    if curl --noproxy "$HOST" -sf --connect-timeout 8 --max-time 15 "${ep}/models" > /dev/null 2>&1; then
        echo "[preflight] OK: $ep"
    else
        echo "[preflight] FAIL: $ep — aborting."
        exit 1
    fi
done
echo "[preflight] All 6 servers reachable."
echo ""

# ── Preflight: thinking mode on chain servers ──────────────────────────────────
echo "[preflight] Verifying thinking mode on 3 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_U1" "$CHAIN_URL_U3" "$CHAIN_URL_U4"; do
    HOST="${CHAIN_URL#http://}"; HOST="${HOST%%/*}"; HOST="${HOST%%:*}"
    RESPONSE=$(curl --noproxy "$HOST" -s --connect-timeout 10 --max-time 90 \
        -X POST "$CHAIN_URL/chat/completions" \
        -H "Authorization: Bearer None" \
        -H "Content-Type: application/json" \
        -d '{"model":"Qwen/Qwen3-8B","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":200,"temperature":0.1}' \
        2>/dev/null || echo "CURL_FAIL")
    if echo "$RESPONSE" | grep -q "<think>"; then
        echo "[preflight] OK: $CHAIN_URL (thinking confirmed)"
    else
        echo "[preflight] FAIL: $CHAIN_URL NOT in thinking mode — aborting."
        exit 1
    fi
done
echo "[preflight] Thinking mode confirmed on all chain servers."
echo ""

# ── Preflight: Redis DBs 0–3 empty ────────────────────────────────────────────
echo "[preflight] Checking Redis DBs 0–2 are empty..."
PYTHONPATH="$PROJ" "$PYTHON" "$PROJ/tools/flush.py" --db 0 1 2
for db in 0 1 2; do
    keys=$(redis-cli -n $db DBSIZE)
    if [ "$keys" -ne 0 ]; then
        echo "[preflight] FAIL: Redis DB $db has $keys keys — run flush.py --confirm first."
        exit 1
    fi
    echo "[preflight] OK: Redis DB $db empty"
done
echo ""

# ── Preflight: dataset checksums ──────────────────────────────────────────────
echo "[preflight] Verifying dataset checksums..."
TRAIN_SHA=$(sha256sum "$PROJ/problems/chains/hotpotqa/dataset/HotpotQA_train.jsonl" | awk '{print $1}')
TEST_SHA=$(sha256sum "$PROJ/problems/chains/hotpotqa/dataset/HotpotQA_test.jsonl" | awk '{print $1}')
EXPECTED_TRAIN="9d8b0ba2a19d124fa243c88b650b2ecd42e5c771bc4e039553389c6b9566ef94"
EXPECTED_TEST="c46bfb185e448bf1b92cb75bb5ab967f3211051793967f01500f453945046b0d"
[ "$TRAIN_SHA" = "$EXPECTED_TRAIN" ] && echo "[preflight] OK: HotpotQA_train.jsonl" || { echo "[preflight] FAIL: train checksum mismatch"; exit 1; }
[ "$TEST_SHA" = "$EXPECTED_TEST" ] && echo "[preflight] OK: HotpotQA_test.jsonl" || { echo "[preflight] FAIL: test checksum mismatch"; exit 1; }
echo ""

# ── Preflight: ColBERT index present ──────────────────────────────────────────
echo "[preflight] Verifying ColBERT index..."
INDEX="$PROJ/experiments/hotpotqa/indexes/colbert_index/metadata.json"
if [ ! -f "$INDEX" ]; then
    echo "[preflight] FAIL: ColBERT index not found at $INDEX"
    exit 1
fi
N_EMBS=$(python3 -c "import json; print(json.load(open('$INDEX'))['num_embeddings'])")
echo "[preflight] OK: ColBERT index found ($N_EMBS embeddings)"
echo ""

# ── Preflight: cold-start baseline program exists ─────────────────────────────
echo "[preflight] Verifying cold-start baseline program..."
BASELINE="$PROJ/problems/chains/hotpotqa/static_colbert_f1_600/initial_programs/baseline.py"
if [ ! -f "$BASELINE" ]; then
    echo "[preflight] FAIL: baseline.py not found at $BASELINE — aborting."
    exit 1
fi
echo "[preflight] OK: baseline.py found"
echo ""

# ── Preflight: confirm NO program_loader.problem_dir in this script ───────────
echo "[preflight] Verifying NO program_loader.problem_dir= override in launch commands..."
if grep -E "^\s+program_loader\.problem_dir=" "$0"; then
    echo "[preflight] FAIL: program_loader.problem_dir= found — cold start broken!"
    exit 1
fi
echo "[preflight] OK: no program_loader.problem_dir= override (cold start confirmed)"
echo ""

echo "================================================================"
echo "All preflight checks passed."
echo "================================================================"
echo ""

# ── ColBERT search server ──────────────────────────────────────────────────────
COLBERT_SERVER_PORT=8889
COLBERT_SERVER_LOG="$LOG_DIR/colbert_server.log"
export HOTPOTQA_COLBERT_SERVER_URL="http://127.0.0.1:$COLBERT_SERVER_PORT"

echo "Starting ColBERT search server on port $COLBERT_SERVER_PORT..."
PYTHONPATH="$PROJ" nohup "$PYTHON" "$PROJ/experiments/hotpotqa/tools/colbert_server.py" \
    --index-dir "$PROJ/experiments/colbert_index" \
    --port "$COLBERT_SERVER_PORT" \
    --host "0.0.0.0" \
    --num-gpus 8 \
    > "$COLBERT_SERVER_LOG" 2>&1 &
PID_SERVER=$!
echo "ColBERT server started: PID=$PID_SERVER  log=$COLBERT_SERVER_LOG"
echo ""

echo "Waiting for ColBERT server to load index (this takes ~3 min)..."
for i in $(seq 1 180); do
    if curl -sf --connect-timeout 2 --max-time 5 \
            "http://127.0.0.1:$COLBERT_SERVER_PORT/health" > /dev/null 2>&1; then
        echo "[colbert_server] Ready after ${i}s"
        break
    fi
    if [ "$i" -eq 180 ]; then
        echo "[colbert_server] FAIL: not ready after 180s — check $COLBERT_SERVER_LOG"
        exit 1
    fi
    sleep 1
done
echo ""

echo "Launching 3 cold-start runs (U1, U3, U4 — U2 dropped; this node serves ColBERT GPU)..."
echo ""

# ── Run U1: cold-start, host A port 8001 ──────────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_U1" HOTPOTQA_COLBERT_SERVER_URL="$HOTPOTQA_COLBERT_SERVER_URL" \
    nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_colbert_f1_600 \
    pipeline=hotpotqa_colbert \
    prompts=default \
    redis.db=0 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url="http://$MUT_U1:8777/v1" \
    > "$LOG_DIR/run_U1.log" 2>&1 &
PID_U1=$!
echo "Run U1 started: PID=$PID_U1  DB=0  chain=$CHAIN_URL_U1  mut=$MUT_U1"

# ── Run U3: cold-start, host B port 8001 ──────────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_U3" HOTPOTQA_COLBERT_SERVER_URL="$HOTPOTQA_COLBERT_SERVER_URL" \
    nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_colbert_f1_600 \
    pipeline=hotpotqa_colbert \
    prompts=default \
    redis.db=1 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url="http://$MUT_U3:8777/v1" \
    > "$LOG_DIR/run_U3.log" 2>&1 &
PID_U3=$!
echo "Run U3 started: PID=$PID_U3  DB=1  chain=$CHAIN_URL_U3  mut=$MUT_U3"

# ── Run U4: cold-start, host B port 8000 ──────────────────────────────────────
HOTPOTQA_CHAIN_URL="$CHAIN_URL_U4" HOTPOTQA_COLBERT_SERVER_URL="$HOTPOTQA_COLBERT_SERVER_URL" \
    nohup "$PYTHON" "$PROJ/run.py" \
    problem.name=chains/hotpotqa/static_colbert_f1_600 \
    pipeline=hotpotqa_colbert \
    prompts=default \
    redis.db=2 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url="http://$MUT_U4:8777/v1" \
    > "$LOG_DIR/run_U4.log" 2>&1 &
PID_U4=$!
echo "Run U4 started: PID=$PID_U4  DB=2  chain=$CHAIN_URL_U4  mut=$MUT_U4"

echo ""
echo "================================================================"
echo "All 3 runs launched."
echo "  Server PID=$PID_SERVER  log=$COLBERT_SERVER_LOG"
echo "  U1 PID=$PID_U1  U3 PID=$PID_U3  U4 PID=$PID_U4"
echo ""
echo "Monitor with:"
echo "  PYTHONPATH=$PROJ $PYTHON $PROJ/tools/status.py \\"
echo "    --run chains/hotpotqa/static_colbert_f1_600@0:colbert-U1 \\"
echo "    --run chains/hotpotqa/static_colbert_f1_600@1:colbert-U3 \\"
echo "    --run chains/hotpotqa/static_colbert_f1_600@2:colbert-U4 \\"
echo "    --pid L:$PID_U1 --pid L:$PID_U3 --pid L:$PID_U4"
echo "================================================================"
