#!/usr/bin/env bash
# Gemini mutator run: the top-1 recommended arm from the ALL-IN closeout
# (BD3D + paired gate + paired crediting + live memory) with the mutation LLM
# swapped to google/gemini-3.5-flash via OpenRouter (llm=gemini35_flash).
# Single MEM run — user directive 2026-07-12 ("run the top-1 recommended arm
# using gemini 3.5 flash"). Prereg: prereg_gemini_mutator_20260712.md
#
# Proxy split (the one thing that differs from launch_bd3d_noise_allin.sh's
# env handling): the mutator route is EXTERNAL (openrouter.ai needs the Squid
# proxy) while the chain executor + memory LLM stay INTERNAL (litellm proxy
# 10.232.24.68 + backends 10.232.22.184 must bypass it via NO_PROXY).
#
# Override examples:
#   MAX_MUTANTS=500 ./launch_gemini_mem.sh
#   DRY_RUN=1 ./launch_gemini_mem.sh

set -euo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PYTHON="${GIGAEVO_PYTHON:-/home/jovyan/.mlspace/envs/evo/bin/python3}"
EXP_DIR="$PROJ/experiments/hover/diff_memory"
LOG_DIR="$EXP_DIR/logs"

TS="${TS:-$(date +%Y%m%d_%H%M%S)}"
PROXY_URL="${PROXY_URL:-http://10.232.24.68:4000/v1}"
MUTATION_MODEL="google/gemini-3.5-flash"
MEMORY_MODEL="${MEMORY_MODEL:-Qwen/Qwen3-235B-A22B-Instruct-2507}"
HOVER_CHAIN_MODEL="${HOVER_CHAIN_MODEL:-Qwen/Qwen3-8B}"
HOVER_CHAIN_URL="${HOVER_CHAIN_URL:-$PROXY_URL}"
SQUID_PROXY="${SQUID_PROXY:-$(grep -m1 '^SQUID_PROXY=' "$PROJ/.env" | cut -d= -f2-)}"

MAX_MUTANTS="${MAX_MUTANTS:-250}"
MAX_TOKENS="${MAX_TOKENS:-60000}"
STAGE_TIMEOUT="${STAGE_TIMEOUT:-7200}"
DAG_TIMEOUT="${DAG_TIMEOUT:-14400}"

GIGAEVO_ROOT="${GIGAEVO_ROOT:-$PROJ}"
RUN_ROOT="${RUN_ROOT:-$GIGAEVO_ROOT/outputs/hover-diff-memory-gemini-$TS}"
MEMORY_ROOT="${MEMORY_ROOT:-$GIGAEVO_ROOT}"
MEM_R1_MEMORY_BANK="${MEM_R1_MEMORY_BANK:-$MEMORY_ROOT/SHARE_HOVER_DIFF_MEMORY_GEMINI_R1_$TS}"

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  OPENROUTER_API_KEY="$(grep -m1 '^OPENROUTER_API_KEY=' "$PROJ/.env" | cut -d= -f2-)"
fi
export OPENROUTER_API_KEY
: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY not set and not found in $PROJ/.env}"

export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-gigaevo}"
export HOVER_CHAIN_MODEL
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-8}"
export JAX_PLATFORMS="${JAX_PLATFORMS:-cpu}"
export JAX_PLATFORM_NAME="${JAX_PLATFORM_NAME:-cpu}"

# Mutator route is external: openrouter.ai goes through Squid. Every internal
# host must be in NO_PROXY or its LLM calls hang (the A1 re-eval trap).
NO_PROXY_HOSTS="10.232.24.68,10.232.22.184,10.232.91.196,10.232.28.121,10.232.47.140,10.232.33.122,localhost,127.0.0.1"
export NO_PROXY="$NO_PROXY_HOSTS${NO_PROXY:+,$NO_PROXY}"
export no_proxy="$NO_PROXY_HOSTS${no_proxy:+,$no_proxy}"
export HTTPS_PROXY="$SQUID_PROXY"
export https_proxy="$SQUID_PROXY"
export HTTP_PROXY=""
export http_proxy=""
export ALL_PROXY=""
export all_proxy=""

mkdir -p "$LOG_DIR" "$RUN_ROOT/MEM_R1" "$MEM_R1_MEMORY_BANK"

require_model() {
  local url="$1"
  local model="$2"
  local label="$3"
  curl --noproxy '*' -fsS --max-time 15 \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    "$url/models" |
    "$PYTHON" -c '
import json
import sys

required = sys.argv[1]
label = sys.argv[2]
payload = json.load(sys.stdin)
models = {item.get("id") for item in payload.get("data", [])}
if required not in models:
    raise SystemExit(f"{label}: missing {required}; available={sorted(models)}")
print(f"{label}: ok ({required})")
' "$model" "$label"
}

require_direct_chain_backend() {
  local port="$1"
  curl --noproxy '*' -fsS --max-time 10 "http://10.232.22.184:$port/v1/models" |
    "$PYTHON" -c '
import json
import sys

port = sys.argv[1]
payload = json.load(sys.stdin)
models = {item.get("id") for item in payload.get("data", [])}
required = "Qwen/Qwen3-8B"
if required not in models:
    raise SystemExit(f"10.232.22.184:{port}: missing {required}; available={sorted(models)}")
print(f"10.232.22.184:{port}: ok ({required})")
' "$port"
}

echo "== Smoke: LiteLLM proxy models (internal, must bypass Squid) =="
require_model "$PROXY_URL" "$MEMORY_MODEL" "memory"
require_model "$PROXY_URL" "$HOVER_CHAIN_MODEL" "chain-via-proxy"

echo "== Smoke: direct Qwen3-8B backends =="
for port in 8000 8001 8002 8003 8004 8005 8006 8007; do
  require_direct_chain_backend "$port"
done

# Per-route smoke under the EXACT ambient proxy env the run will inherit:
# httpx must route openrouter.ai through Squid and 10.232.x direct. One paid
# gemini call (~1 token) + one internal completion.
echo "== Smoke: per-route httpx proxy split (1-call each) =="
"$PYTHON" - "$PROXY_URL" "$MUTATION_MODEL" "$HOVER_CHAIN_MODEL" <<'PYEOF'
import os
import sys

from openai import OpenAI

proxy_url, gemini_model, chain_model = sys.argv[1:4]

ext = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"], timeout=60)
r = ext.chat.completions.create(
    model=gemini_model,
    messages=[{"role": "user", "content": "Reply with the single word: ok"}],
    max_tokens=200,
    extra_body={"reasoning": {"effort": "minimal"}},
)
print(f"openrouter/{gemini_model} via Squid: ok ({r.choices[0].message.content!r})")

internal = OpenAI(base_url=proxy_url, api_key=os.environ.get("OPENAI_API_KEY", "sk-gigaevo"), timeout=60)
r = internal.chat.completions.create(
    model=chain_model,
    messages=[{"role": "user", "content": "Reply with the single word: ok"}],
    max_tokens=200,
)
print(f"litellm/{chain_model} direct (NO_PROXY): ok ({r.choices[0].message.content!r})")
PYEOF

cd "$PROJ"

COMMON_ARGS=(
  storage=disk
  problem.name=chains/hover/full7_vectorized
  archive_selector=paired_bootstrap
  program_format=json_document
  mutation=carl_with_retrieval_tools
  algorithm=chains_bd3d
  enable_chain_structural_metrics=true
  llm=gemini35_flash
  num_parents=1
  max_mutants="$MAX_MUTANTS"
  max_tokens="$MAX_TOKENS"
  stage_timeout="$STAGE_TIMEOUT"
  dag_timeout="$DAG_TIMEOUT"
)

MEM_ARGS=(
  pipeline=memory_guided
  memory=full
  memory/write=live
  memory/crediting=paired
  memory/llm=qwen_instruct
  memory.llm.models.0.base_url="$PROXY_URL"
)

echo "== Hydra config check =="
HOVER_CHAIN_URL="$HOVER_CHAIN_URL" "$PYTHON" run.py \
  "${COMMON_ARGS[@]}" "${MEM_ARGS[@]}" \
  checkpoint_dir="$MEM_R1_MEMORY_BANK" \
  hydra.run.dir="$RUN_ROOT/MEM_R1" \
  --cfg job \
  > "$EXP_DIR/cfg_gemini_MEM_R1_$TS.yaml"
echo "config: $EXP_DIR/cfg_gemini_MEM_R1_$TS.yaml"

echo "== Treatment self-check: gemini mutator + ALL-IN machinery composed =="
grep -q "google/gemini-3.5-flash" "$EXP_DIR/cfg_gemini_MEM_R1_$TS.yaml" || {
  echo "ERROR: cfg lacks google/gemini-3.5-flash; llm=gemini35_flash inert." >&2
  exit 1
}
grep -q "openrouter.ai/api/v1" "$EXP_DIR/cfg_gemini_MEM_R1_$TS.yaml" || {
  echo "ERROR: cfg lacks the OpenRouter base_url on the mutator route." >&2
  exit 1
}
grep -q "PairedEffectEstimator" "$EXP_DIR/cfg_gemini_MEM_R1_$TS.yaml" || {
  echo "ERROR: cfg lacks PairedEffectEstimator; crediting override inert." >&2
  exit 1
}
grep -q "PairedBootstrapArchiveSelector" "$EXP_DIR/cfg_gemini_MEM_R1_$TS.yaml" || {
  echo "ERROR: cfg lacks PairedBootstrapArchiveSelector." >&2
  exit 1
}
grep -q "10.232.24.68" "$EXP_DIR/cfg_gemini_MEM_R1_$TS.yaml" || {
  echo "ERROR: cfg lacks the internal proxy on the memory-LLM route." >&2
  exit 1
}
echo "treatment self-check: ok"

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "DRY_RUN=1: smoke and config checks passed; not launching runs."
  exit 0
fi

launch_run() {
  local label="$1"
  local out="$2"
  shift 2
  local log="$LOG_DIR/gemini_${label}_$TS.log"

  HOVER_CHAIN_URL="$HOVER_CHAIN_URL" setsid "$PYTHON" run.py \
    "$@" \
    hydra.run.dir="$out" \
    > "$log" 2>&1 < /dev/null &

  local pid=$!
  echo "$label pid=$pid log=$log output=$out"
  printf '%s %s %s %s\n' "$label" "$pid" "$log" "$out" >> "$EXP_DIR/pids_gemini_$TS.txt"
}

rm -f "$EXP_DIR/pids_gemini_$TS.txt"

echo "== Launch =="
launch_run MEM_R1 "$RUN_ROOT/MEM_R1" \
  "${COMMON_ARGS[@]}" "${MEM_ARGS[@]}" checkpoint_dir="$MEM_R1_MEMORY_BANK"

sleep 5
while read -r label pid _; do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "ERROR: $label died immediately; inspect its log." >&2
    exit 1
  fi
done < "$EXP_DIR/pids_gemini_$TS.txt"

cat > "$EXP_DIR/latest_gemini.env" <<EOF
TS=$TS
PROXY_URL=$PROXY_URL
HOVER_CHAIN_URL=$HOVER_CHAIN_URL
HOVER_CHAIN_MODEL=$HOVER_CHAIN_MODEL
MUTATION_MODEL=$MUTATION_MODEL
MEMORY_MODEL=$MEMORY_MODEL
RUN_ROOT=$RUN_ROOT
MEM_R1_MEMORY_BANK=$MEM_R1_MEMORY_BANK
PIDS_FILE=$EXP_DIR/pids_gemini_$TS.txt
CFG_MEM_R1=$EXP_DIR/cfg_gemini_MEM_R1_$TS.yaml
ALGORITHM=chains_bd3d
MEM_PIPELINE=memory_guided
ARCHIVE_SELECTOR=paired_bootstrap
MEM_CREDITING=paired
ENABLE_CHAIN_STRUCTURAL_METRICS=true
EOF

echo "pids: $EXP_DIR/pids_gemini_$TS.txt"
echo "latest: $EXP_DIR/latest_gemini.env"
