#!/usr/bin/env bash
# Launch the combined BD3D + noise-gate experiment: verbatim mirror of
# launch_noise_gate.sh extended to a 2x2 (arm x rep) = 4-run layout.
# Both arms share the new chain-strategy behavior space and the paired gate:
#   algorithm=chains_bd3d                        (hop_depth x passages x instr)
#   enable_chain_structural_metrics=true         (stage produces the axes)
#   problem.name=chains/hover/full7_vectorized   (same scoring, emits vector)
#   archive_selector=paired_bootstrap            (paired gate, p_accept=0.75)
# The preregistered contrast is the arm delta only:
#   MEM   arm: pipeline=memory_guided memory=full memory/write=live
#   NOMEM arm: pipeline=guided memory=none
#
# Override examples:
#   MAX_MUTANTS=500 ./launch_bd3d_noise.sh
#   DRY_RUN=1 ./launch_bd3d_noise.sh

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
MAX_TOKENS="${MAX_TOKENS:-60000}"
STAGE_TIMEOUT="${STAGE_TIMEOUT:-7200}"
DAG_TIMEOUT="${DAG_TIMEOUT:-14400}"

GIGAEVO_ROOT="${GIGAEVO_ROOT:-$PROJ}"
RUN_ROOT="${RUN_ROOT:-$GIGAEVO_ROOT/outputs/hover-diff-memory-bd3dnoise-$TS}"
MEMORY_ROOT="${MEMORY_ROOT:-$GIGAEVO_ROOT}"
MEM_R1_MEMORY_BANK="${MEM_R1_MEMORY_BANK:-$MEMORY_ROOT/SHARE_HOVER_DIFF_MEMORY_BD3D_R1_$TS}"
MEM_R2_MEMORY_BANK="${MEM_R2_MEMORY_BANK:-$MEMORY_ROOT/SHARE_HOVER_DIFF_MEMORY_BD3D_R2_$TS}"

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

mkdir -p "$LOG_DIR" "$RUN_ROOT/MEM_R1" "$RUN_ROOT/MEM_R2" \
  "$RUN_ROOT/NOMEM_R1" "$RUN_ROOT/NOMEM_R2" \
  "$MEM_R1_MEMORY_BANK" "$MEM_R2_MEMORY_BANK"

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
  problem.name=chains/hover/full7_vectorized
  archive_selector=paired_bootstrap
  program_format=json_document
  mutation=carl_with_retrieval_tools
  algorithm=chains_bd3d
  enable_chain_structural_metrics=true
  llm=single
  llm_base_url="$PROXY_URL"
  model_name="$MUTATION_MODEL"
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
  memory/llm=qwen_instruct
  memory.llm.models.0.base_url="$PROXY_URL"
)

NOMEM_ARGS=(
  pipeline=guided
  memory=none
)

echo "== Hydra config check =="
HOVER_CHAIN_URL="$HOVER_CHAIN_URL" "$PYTHON" run.py \
  "${COMMON_ARGS[@]}" "${MEM_ARGS[@]}" \
  checkpoint_dir="$MEM_R1_MEMORY_BANK" \
  hydra.run.dir="$RUN_ROOT/MEM_R1" \
  --cfg job \
  > "$EXP_DIR/cfg_bd3dnoise_MEM_R1_$TS.yaml"
HOVER_CHAIN_URL="$HOVER_CHAIN_URL" "$PYTHON" run.py \
  "${COMMON_ARGS[@]}" "${MEM_ARGS[@]}" \
  checkpoint_dir="$MEM_R2_MEMORY_BANK" \
  hydra.run.dir="$RUN_ROOT/MEM_R2" \
  --cfg job \
  > "$EXP_DIR/cfg_bd3dnoise_MEM_R2_$TS.yaml"
HOVER_CHAIN_URL="$HOVER_CHAIN_URL" "$PYTHON" run.py \
  "${COMMON_ARGS[@]}" "${NOMEM_ARGS[@]}" \
  hydra.run.dir="$RUN_ROOT/NOMEM_R1" \
  --cfg job \
  > "$EXP_DIR/cfg_bd3dnoise_NOMEM_R1_$TS.yaml"
HOVER_CHAIN_URL="$HOVER_CHAIN_URL" "$PYTHON" run.py \
  "${COMMON_ARGS[@]}" "${NOMEM_ARGS[@]}" \
  hydra.run.dir="$RUN_ROOT/NOMEM_R2" \
  --cfg job \
  > "$EXP_DIR/cfg_bd3dnoise_NOMEM_R2_$TS.yaml"
echo "configs: $EXP_DIR/cfg_bd3dnoise_{MEM_R1,MEM_R2,NOMEM_R1,NOMEM_R2}_$TS.yaml"

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "DRY_RUN=1: smoke and config checks passed; not launching runs."
  exit 0
fi

launch_run() {
  local label="$1"
  local out="$2"
  shift 2
  local log="$LOG_DIR/bd3dnoise_${label}_$TS.log"

  HOVER_CHAIN_URL="$HOVER_CHAIN_URL" setsid "$PYTHON" run.py \
    "$@" \
    hydra.run.dir="$out" \
    > "$log" 2>&1 < /dev/null &

  local pid=$!
  echo "$label pid=$pid log=$log output=$out"
  printf '%s %s %s %s\n' "$label" "$pid" "$log" "$out" >> "$EXP_DIR/pids_bd3dnoise_$TS.txt"
}

rm -f "$EXP_DIR/pids_bd3dnoise_$TS.txt"

echo "== Launch =="
launch_run MEM_R1 "$RUN_ROOT/MEM_R1" \
  "${COMMON_ARGS[@]}" "${MEM_ARGS[@]}" checkpoint_dir="$MEM_R1_MEMORY_BANK"
launch_run MEM_R2 "$RUN_ROOT/MEM_R2" \
  "${COMMON_ARGS[@]}" "${MEM_ARGS[@]}" checkpoint_dir="$MEM_R2_MEMORY_BANK"
launch_run NOMEM_R1 "$RUN_ROOT/NOMEM_R1" "${COMMON_ARGS[@]}" "${NOMEM_ARGS[@]}"
launch_run NOMEM_R2 "$RUN_ROOT/NOMEM_R2" "${COMMON_ARGS[@]}" "${NOMEM_ARGS[@]}"

sleep 5
while read -r label pid _; do
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "ERROR: $label died immediately; inspect its log." >&2
    exit 1
  fi
done < "$EXP_DIR/pids_bd3dnoise_$TS.txt"

cat > "$EXP_DIR/latest_bd3d_noise.env" <<EOF
TS=$TS
PROXY_URL=$PROXY_URL
HOVER_CHAIN_URL=$HOVER_CHAIN_URL
HOVER_CHAIN_MODEL=$HOVER_CHAIN_MODEL
MUTATION_MODEL=$MUTATION_MODEL
MEMORY_MODEL=$MEMORY_MODEL
RUN_ROOT=$RUN_ROOT
MEM_R1_MEMORY_BANK=$MEM_R1_MEMORY_BANK
MEM_R2_MEMORY_BANK=$MEM_R2_MEMORY_BANK
PIDS_FILE=$EXP_DIR/pids_bd3dnoise_$TS.txt
CFG_MEM_R1=$EXP_DIR/cfg_bd3dnoise_MEM_R1_$TS.yaml
CFG_MEM_R2=$EXP_DIR/cfg_bd3dnoise_MEM_R2_$TS.yaml
CFG_NOMEM_R1=$EXP_DIR/cfg_bd3dnoise_NOMEM_R1_$TS.yaml
CFG_NOMEM_R2=$EXP_DIR/cfg_bd3dnoise_NOMEM_R2_$TS.yaml
ALGORITHM=chains_bd3d
MEM_PIPELINE=memory_guided
NOMEM_PIPELINE=guided
ARCHIVE_SELECTOR=paired_bootstrap
ENABLE_CHAIN_STRUCTURAL_METRICS=true
EOF

echo "pids: $EXP_DIR/pids_bd3dnoise_$TS.txt"
echo "latest: $EXP_DIR/latest_bd3d_noise.env"
