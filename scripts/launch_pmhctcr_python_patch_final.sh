#!/usr/bin/env bash
# Launch the final expert-hypothesis python_patch evolution run.
#
# Usage:
#   ./scripts/launch_pmhctcr_python_patch_final.sh
#   MAX_MUTANTS=200 ./scripts/launch_pmhctcr_python_patch_final.sh
#   ./scripts/launch_pmhctcr_python_patch_final.sh expert_prompt=disabled
#   ./scripts/launch_pmhctcr_python_patch_final.sh expert_prompt.enabled=false
#   nohup ./scripts/launch_pmhctcr_python_patch_final.sh > outputs/_final.log 2>&1 &

set -euo pipefail

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BASE="$(CDPATH= cd -- "$REPO/.." && pwd)"
PCE="$BASE/python_code_evolution"
MAX_MUTANTS="${MAX_MUTANTS:-200}"
RUN_NAME="${RUN_NAME:-pmhctcr_python_patch_final}"
RUN_DIR="$REPO/outputs/$RUN_NAME"
EXTRA_ARGS=("$@")

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

resume=false
if [[ -d "$RUN_DIR/storage/pmhctcr" ]]; then
  resume=true
fi
mkdir -p "$RUN_DIR"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] START $RUN_NAME max_mutants=$MAX_MUTANTS resume=$resume"

cd "$REPO"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

python run.py \
  experiment=pmhctcr_python_patch_final \
  "${EXTRA_ARGS[@]}" \
  llm=codex \
  max_mutants="$MAX_MUTANTS" \
  max_in_flight=1 \
  llm_max_concurrent=1 \
  request_timeout=180 \
  stage_timeout=240 \
  validator_timeout=900 \
  dag_timeout=1800 \
  redis.resume="$resume" \
  hydra.run.dir="$RUN_DIR" \
  hydra.job.chdir=false \
  2>&1 | tee -a "$RUN_DIR/launch.out"
