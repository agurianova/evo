#!/usr/bin/env bash
# Clean expert-off chain. Uses experiment=pmhctcr_python_patch_final_off
# (scrubbed suggestion prompt and task file). New run prefix, so it does not
# resume the earlier expert-off directories.
#
# Usage:
#   ./scripts/launch_pmhctcr_final_terra_expert_off_clean.sh
#   NUM_REPLICATES=5 ./scripts/launch_pmhctcr_final_terra_expert_off_clean.sh

set -euo pipefail

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BASE="$(CDPATH= cd -- "$REPO/.." && pwd)"
PCE="$BASE/python_code_evolution"
MAX_MUTANTS="${MAX_MUTANTS:-100}"
NUM_REPLICATES="${NUM_REPLICATES:-5}"
RUN_PREFIX="${RUN_PREFIX:-pmhctcr_final_terra_expert_off_clean}"

export PATH="/home/jovyan/.local/bin:$PATH"
unset OPENAI_API_KEY OPENAI_BASE_URL OPENAI_API_BASE AZURE_OPENAI_API_KEY
unset OPENROUTER_API_KEY ANTHROPIC_API_KEY

if [[ -z "${HTTPS_PROXY:-}" && -f "$PCE/scripts/proxy.env" ]]; then
  # shellcheck source=/dev/null
  source "$PCE/scripts/proxy.env"
fi
if [[ -z "${HTTPS_PROXY:-}" ]]; then
  echo "HTTPS_PROXY is not set and $PCE/scripts/proxy.env is missing." >&2
  exit 4
fi
export HTTPS_PROXY HTTP_PROXY="${HTTP_PROXY:-$HTTPS_PROXY}"
export https_proxy="$HTTPS_PROXY" http_proxy="$HTTP_PROXY"
export NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,::1,10.0.0.0/8}"
export no_proxy="$NO_PROXY"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] preflight: checking gpt-5.6-terra ..."
preflight_out="$(printf 'Reply with exactly: PREFLIGHT_OK\n' \
  | timeout 180 codex exec --model gpt-5.6-terra \
      -c 'forced_login_method="chatgpt"' \
      --sandbox read-only --ephemeral --skip-git-repo-check 2>&1 || true)"
if [[ "$preflight_out" != *PREFLIGHT_OK* ]]; then
  echo "$preflight_out" | tail -8 >&2
  echo "preflight FAILED" >&2
  exit 5
fi
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] preflight: terra reachable"

mkdir -p "$REPO/outputs"
cd "$REPO"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

run_is_complete() {
  local rs="$REPO/outputs/$1/storage/pmhctcr/run_state.json"
  python3 - "$rs" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.is_file():
    raise SystemExit(1)
snap = json.loads(json.loads(p.read_text()).get("engine:snapshot", "{}"))
raise SystemExit(0 if snap.get("completion_reason") == "max_mutants_reached" else 1)
PY
}

chain_log="$REPO/outputs/${RUN_PREFIX}_chain.log"
{
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] chain start experiment=pmhctcr_python_patch_final_off"
  for ((rep = 1; rep <= NUM_REPLICATES; rep++)); do
    run_name="${RUN_PREFIX}_m${MAX_MUTANTS}_r${rep}"
    if run_is_complete "$run_name"; then
      echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] skip $run_name (max_mutants_reached)"
      continue
    fi
    resume=false
    if [[ -d "$REPO/outputs/$run_name/storage/pmhctcr" ]]; then
      resume=true
    fi
    run_dir="$REPO/outputs/$run_name"
    mkdir -p "$run_dir"
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] START $run_name max_mutants=$MAX_MUTANTS resume=$resume"
    python run.py \
      experiment=pmhctcr_python_patch_final_off \
      expert_prompt=disabled \
      llm=codex_terra \
      max_mutants="$MAX_MUTANTS" \
      max_in_flight=1 \
      llm_max_concurrent=1 \
      request_timeout=180 \
      stage_timeout=240 \
      validator_timeout=900 \
      dag_timeout=1800 \
      redis.resume="$resume" \
      hydra.run.dir="$run_dir" \
      hydra.job.chdir=false \
      2>&1 | tee -a "$run_dir/launch.out"
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] DONE  $run_name"
  done
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] chain done"
} >>"$chain_log" 2>&1
