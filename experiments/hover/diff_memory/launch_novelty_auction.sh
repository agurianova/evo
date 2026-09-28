#!/usr/bin/env bash
# Launch two memory-enabled HoVer CARL tool-diff runs that mirror
# launch_baseline_memory.sh (TS=20260710_041404 control pair) with EXACTLY ONE
# delta: the novelty-discounted auction (`+memory/auction=
# thompson_bootstrap_novelty`, bid tax (1+use_count)^-novelty_power).
# Prereg: prereg_novelty_auction_20260711.md.
#
# Override examples:
#   NOVELTY_POWER=1.0 ./launch_novelty_auction.sh
#   DRY_RUN=1 ./launch_novelty_auction.sh

set -euo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PYTHON="${GIGAEVO_PYTHON:-/home/jovyan/.mlspace/envs/evo/bin/python3}"
EXP_DIR="$PROJ/experiments/hover/diff_memory"
LOG_DIR="$EXP_DIR/logs"

TS="${TS:-$(date +%Y%m%d_%H%M%S)}"
PROXY_URL="${PROXY_URL:-http://10.232.24.68:4000/v1}"
MUTATION_MODEL="${MUTATION_MODEL:-Qwen3-235B-A22B-Thinking-2507}"
MEMORY_MODEL="${MEMORY_MODEL:-Qwen/Qwen3-235B-A22B-Instruct-2507}"
HOVER_CHAIN_MODEL="${HOVER_CHAIN_MODEL:-Qwen/Qwen3-8B}"
HOVER_CHAIN_URL="${HOVER_CHAIN_URL:-$PROXY_URL}"

MAX_MUTANTS="${MAX_MUTANTS:-250}"
NOVELTY_POWER="${NOVELTY_POWER:-0.5}"
MAX_TOKENS="${MAX_TOKENS:-60000}"
STAGE_TIMEOUT="${STAGE_TIMEOUT:-7200}"
DAG_TIMEOUT="${DAG_TIMEOUT:-14400}"

GIGAEVO_ROOT="${GIGAEVO_ROOT:-$PROJ}"
RUN_ROOT="${RUN_ROOT:-$GIGAEVO_ROOT/outputs/hover-diff-memory-novelty-auction-$TS}"
MEMORY_ROOT="${MEMORY_ROOT:-$GIGAEVO_ROOT}"
RUN1_MEMORY_BANK="${RUN1_MEMORY_BANK:-$MEMORY_ROOT/SHARE_HOVER_DIFF_MEMORY_NOVAUC_R1_$TS}"
RUN2_MEMORY_BANK="${RUN2_MEMORY_BANK:-$MEMORY_ROOT/SHARE_HOVER_DIFF_MEMORY_NOVAUC_R2_$TS}"

export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-gigaevo}"
export HOVER_CHAIN_MODEL
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-8}"
export JAX_PLATFORMS="${JAX_PLATFORMS:-cpu}"
export JAX_PLATFORM_NAME="${JAX_PLATFORM_NAME:-cpu}"

NO_PROXY_HOSTS="10.232.24.68,10.232.22.184,10.232.91.196,10.232.28.121,10.232.47.140,10.232.33.122,localhost,127.0.0.1"
export NO_PROXY="$NO_PROXY_HOSTS${NO_PROXY:+,$NO_PROXY}"
export no_proxy="$NO_PROXY_HOSTS${no_proxy:+,$no_proxy}"
# Every route in this experiment is internal. Clear ambient Squid proxy vars so
# Python urllib/httpx model-verification cannot accidentally proxy internal IPs.
export HTTP_PROXY=""
export HTTPS_PROXY=""
export http_proxy=""
export https_proxy=""
export ALL_PROXY=""
export all_proxy=""

mkdir -p "$LOG_DIR" "$RUN_ROOT/R1" "$RUN_ROOT/R2" "$RUN1_MEMORY_BANK" "$RUN2_MEMORY_BANK"

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

echo "== Smoke: LiteLLM proxy models =="
require_model "$PROXY_URL" "$MUTATION_MODEL" "mutation"
require_model "$PROXY_URL" "$MEMORY_MODEL" "memory"
require_model "$PROXY_URL" "$HOVER_CHAIN_MODEL" "chain-via-proxy"

echo "== Smoke: direct Qwen3-8B backends =="
for port in 8000 8001 8002 8003 8004 8005 8006 8007; do
  require_direct_chain_backend "$port"
done

cd "$PROJ"

COMMON_ARGS=(
  storage=disk
  problem.name=chains/hover/full7
  pipeline=memory_guided
  program_format=json_document
  mutation=carl_with_retrieval_tools
  algorithm=single_island_no_distant_parents
  enable_chain_structural_metrics=false
  llm=single
  llm_base_url="$PROXY_URL"
  model_name="$MUTATION_MODEL"
  memory=full
  memory/write=live
  memory/llm=qwen_instruct
  memory.llm.models.0.base_url="$PROXY_URL"
  +memory/auction=thompson_bootstrap_novelty
  memory.auction.novelty_power="$NOVELTY_POWER"
  num_parents=1
  max_mutants="$MAX_MUTANTS"
  max_tokens="$MAX_TOKENS"
  stage_timeout="$STAGE_TIMEOUT"
  dag_timeout="$DAG_TIMEOUT"
)

echo "== Hydra config check =="
HOVER_CHAIN_URL="$HOVER_CHAIN_URL" "$PYTHON" run.py \
  "${COMMON_ARGS[@]}" \
  checkpoint_dir="$RUN1_MEMORY_BANK" \
  hydra.run.dir="$RUN_ROOT/R1" \
  --cfg job \
  > "$EXP_DIR/cfg_novelty_auction_R1_$TS.yaml"
HOVER_CHAIN_URL="$HOVER_CHAIN_URL" "$PYTHON" run.py \
  "${COMMON_ARGS[@]}" \
  checkpoint_dir="$RUN2_MEMORY_BANK" \
  hydra.run.dir="$RUN_ROOT/R2" \
  --cfg job \
  > "$EXP_DIR/cfg_novelty_auction_R2_$TS.yaml"
echo "configs: $EXP_DIR/cfg_novelty_auction_R1_$TS.yaml $EXP_DIR/cfg_novelty_auction_R2_$TS.yaml"

for cfg in "$EXP_DIR/cfg_novelty_auction_R1_$TS.yaml" "$EXP_DIR/cfg_novelty_auction_R2_$TS.yaml"; do
  grep -q "NoveltyDiscountedBootstrapAuctioneer" "$cfg" ||
    { echo "ERROR: $cfg lacks NoveltyDiscountedBootstrapAuctioneer" >&2; exit 1; }
done
echo "treatment verified in both cfg dumps (NoveltyDiscountedBootstrapAuctioneer, power=$NOVELTY_POWER)"

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "DRY_RUN=1: smoke and config checks passed; not launching runs."
  exit 0
fi

launch_run() {
  local label="$1"
  local bank="$2"
  local out="$3"
  local log="$LOG_DIR/novelty_auction_${label}_$TS.log"

  HOVER_CHAIN_URL="$HOVER_CHAIN_URL" setsid "$PYTHON" run.py \
    "${COMMON_ARGS[@]}" \
    checkpoint_dir="$bank" \
    hydra.run.dir="$out" \
    > "$log" 2>&1 < /dev/null &

  local pid=$!
  echo "$label pid=$pid log=$log output=$out memory_bank=$bank"
  printf '%s %s %s %s %s\n' "$label" "$pid" "$log" "$out" "$bank" >> "$EXP_DIR/pids_novelty_auction_$TS.txt"
}

rm -f "$EXP_DIR/pids_novelty_auction_$TS.txt"

echo "== Launch =="
launch_run R1 "$RUN1_MEMORY_BANK" "$RUN_ROOT/R1"
launch_run R2 "$RUN2_MEMORY_BANK" "$RUN_ROOT/R2"

sleep 5
while read -r label pid _; do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "ERROR: $label died immediately; inspect its log." >&2
    exit 1
  fi
done < "$EXP_DIR/pids_novelty_auction_$TS.txt"

cat > "$EXP_DIR/latest_novelty_auction.env" <<EOF
TS=$TS
PROXY_URL=$PROXY_URL
HOVER_CHAIN_URL=$HOVER_CHAIN_URL
HOVER_CHAIN_MODEL=$HOVER_CHAIN_MODEL
MUTATION_MODEL=$MUTATION_MODEL
MEMORY_MODEL=$MEMORY_MODEL
RUN_ROOT=$RUN_ROOT
RUN1_MEMORY_BANK=$RUN1_MEMORY_BANK
RUN2_MEMORY_BANK=$RUN2_MEMORY_BANK
PIDS_FILE=$EXP_DIR/pids_novelty_auction_$TS.txt
CFG_R1=$EXP_DIR/cfg_novelty_auction_R1_$TS.yaml
CFG_R2=$EXP_DIR/cfg_novelty_auction_R2_$TS.yaml
ALGORITHM=single_island_no_distant_parents
PIPELINE=memory_guided
MEMORY=full
NOVELTY_POWER=$NOVELTY_POWER
ENABLE_CHAIN_STRUCTURAL_METRICS=false
EOF

echo "pids: $EXP_DIR/pids_novelty_auction_$TS.txt"
echo "latest: $EXP_DIR/latest_novelty_auction.env"
