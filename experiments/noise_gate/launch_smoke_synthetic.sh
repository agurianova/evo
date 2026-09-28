#!/usr/bin/env bash
# Synthetic smoke of the noise-aware archive gate (problems/toy_noise_gate).
# Two mini-runs, identical except the archive_selector group token:
#   POINT : archive_selector=point            (default rule; transport still on)
#   PAIRED: archive_selector=paired_bootstrap (noise gate live)
# Both use pipeline=memory_guided + memory=full.
# hover A/B composition, on a 64-sample synthetic regression whose validate()
# adds deterministic per-sample pseudo-noise. DEBUG logging so every selector
# decision lands in the run log. Verify with checks_smoke.py after completion.
#
#   DRY_RUN=1 ./launch_smoke_synthetic.sh   # compose + preflight only

set -euo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
PYTHON="${GIGAEVO_PYTHON:-/home/jovyan/.mlspace/envs/evo/bin/python3}"
EXP_DIR="$PROJ/experiments/noise_gate"
LOG_DIR="$EXP_DIR/logs"

TS="${TS:-$(date +%Y%m%d_%H%M%S)}"
PROXY_URL="${PROXY_URL:-http://10.232.24.68:4000/v1}"
MUTATION_MODEL="${MUTATION_MODEL:-Qwen3-235B-A22B-Thinking-2507}"
MEMORY_MODEL="${MEMORY_MODEL:-Qwen/Qwen3-235B-A22B-Instruct-2507}"

MAX_MUTANTS="${MAX_MUTANTS:-12}"
MAX_TOKENS="${MAX_TOKENS:-30000}"

RUN_ROOT="${RUN_ROOT:-$PROJ/outputs/noise-gate-smoke-$TS}"

export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-gigaevo}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-8}"
export JAX_PLATFORMS="${JAX_PLATFORMS:-cpu}"
export JAX_PLATFORM_NAME="${JAX_PLATFORM_NAME:-cpu}"

NO_PROXY_HOSTS="10.232.24.68,localhost,127.0.0.1"
export NO_PROXY="$NO_PROXY_HOSTS${NO_PROXY:+,$NO_PROXY}"
export no_proxy="$NO_PROXY_HOSTS${no_proxy:+,$no_proxy}"
export HTTP_PROXY="" HTTPS_PROXY="" http_proxy="" https_proxy="" ALL_PROXY="" all_proxy=""

mkdir -p "$LOG_DIR" "$RUN_ROOT/POINT" "$RUN_ROOT/PAIRED"

require_model() {
  local model="$1" label="$2"
  curl --noproxy '*' -fsS --max-time 15 \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    "$PROXY_URL/models" |
    "$PYTHON" -c '
import json, sys
required, label = sys.argv[1], sys.argv[2]
models = {item.get("id") for item in json.load(sys.stdin).get("data", [])}
if required not in models:
    raise SystemExit(f"{label}: missing {required}; available={sorted(models)}")
print(f"{label}: ok ({required})")
' "$model" "$label"
}

echo "== Preflight: LiteLLM proxy models =="
require_model "$MUTATION_MODEL" "mutation"
require_model "$MEMORY_MODEL" "memory"

cd "$PROJ"

COMMON_ARGS=(
  storage=disk
  problem.name=toy_noise_gate
  pipeline=memory_guided
  llm=single
  llm_base_url="$PROXY_URL"
  model_name="$MUTATION_MODEL"
  memory=full
  memory/write=live
  memory/llm=qwen_instruct
  memory.llm.models.0.base_url="$PROXY_URL"
  num_parents=1
  max_mutants="$MAX_MUTANTS"
  max_tokens="$MAX_TOKENS"
  stage_timeout=1800
  dag_timeout=3600
  logging.level=DEBUG
)

echo "== Hydra config check =="
"$PYTHON" run.py "${COMMON_ARGS[@]}" archive_selector=point \
  checkpoint_dir="$RUN_ROOT/POINT/memory" hydra.run.dir="$RUN_ROOT/POINT" \
  --cfg job > "$EXP_DIR/cfg_smoke_POINT_$TS.yaml"
"$PYTHON" run.py "${COMMON_ARGS[@]}" archive_selector=paired_bootstrap \
  checkpoint_dir="$RUN_ROOT/PAIRED/memory" hydra.run.dir="$RUN_ROOT/PAIRED" \
  --cfg job > "$EXP_DIR/cfg_smoke_PAIRED_$TS.yaml"

grep -q "PairedBootstrapArchiveSelector" "$EXP_DIR/cfg_smoke_PAIRED_$TS.yaml" ||
  { echo "ERROR: PAIRED cfg lacks PairedBootstrapArchiveSelector" >&2; exit 1; }
grep -q "p_accept: 0.75" "$EXP_DIR/cfg_smoke_PAIRED_$TS.yaml" ||
  { echo "ERROR: PAIRED cfg lacks p_accept: 0.75" >&2; exit 1; }
grep -q "PairedBootstrapArchiveSelector" "$EXP_DIR/cfg_smoke_POINT_$TS.yaml" &&
  { echo "ERROR: POINT cfg unexpectedly carries the paired selector" >&2; exit 1; }
grep -q 'archive_selector: ${archive_selector}' "$EXP_DIR/cfg_smoke_POINT_$TS.yaml" ||
  { echo "ERROR: island does not bind the archive_selector group" >&2; exit 1; }
echo "treatment verified in cfg dumps (group binds; PAIRED carries paired selector)"

if [[ "${DRY_RUN:-0}" == "1" ]]; then
  echo "DRY_RUN=1: preflight and config checks passed; not launching."
  exit 0
fi

launch_run() {
  local label="$1" selector="$2"
  local out="$RUN_ROOT/$label"
  local log="$LOG_DIR/smoke_${label}_$TS.log"
  setsid "$PYTHON" run.py "${COMMON_ARGS[@]}" "archive_selector=$selector" \
    checkpoint_dir="$out/memory" hydra.run.dir="$out" \
    > "$log" 2>&1 < /dev/null &
  local pid=$!
  echo "$label pid=$pid log=$log output=$out"
  printf '%s %s %s %s\n' "$label" "$pid" "$log" "$out" >> "$EXP_DIR/pids_smoke_$TS.txt"
}

rm -f "$EXP_DIR/pids_smoke_$TS.txt"

echo "== Launch =="
launch_run POINT point
launch_run PAIRED paired_bootstrap

sleep 5
while read -r label pid _; do
  kill -0 "$pid" 2>/dev/null ||
    { echo "ERROR: $label died immediately; inspect its log." >&2; exit 1; }
done < "$EXP_DIR/pids_smoke_$TS.txt"

cat > "$EXP_DIR/latest_smoke.env" <<EOF
TS=$TS
RUN_ROOT=$RUN_ROOT
PIDS_FILE=$EXP_DIR/pids_smoke_$TS.txt
CFG_POINT=$EXP_DIR/cfg_smoke_POINT_$TS.yaml
CFG_PAIRED=$EXP_DIR/cfg_smoke_PAIRED_$TS.yaml
MAX_MUTANTS=$MAX_MUTANTS
EOF

echo "pids: $EXP_DIR/pids_smoke_$TS.txt"
echo "latest: $EXP_DIR/latest_smoke.env"
