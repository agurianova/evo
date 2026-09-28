#!/usr/bin/env bash
# final python_patch + expert on + Memory Cards (v2 live).
# Same terra / m100 protocol as pmhctcr_final_terra_expert_on_m100_r*,
# with pipeline=memory_guided and memory=v2.
#
# Usage:
#   ./scripts/launch_pmhctcr_final_terra_expert_on_memory.sh
#   MAX_MUTANTS=100 RUN_NAME=... ./scripts/launch_pmhctcr_final_terra_expert_on_memory.sh

set -euo pipefail

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BASE="$(CDPATH= cd -- "$REPO/.." && pwd)"
PCE="$BASE/python_code_evolution"
MAX_MUTANTS="${MAX_MUTANTS:-100}"
RUN_NAME="${RUN_NAME:-pmhctcr_final_terra_expert_on_memory_m100_r1}"
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

resume=false
if [[ -d "$RUN_DIR/storage/pmhctcr_final_mem" ]]; then
  resume=true
fi
mkdir -p "$RUN_DIR"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] START $RUN_NAME max_mutants=$MAX_MUTANTS resume=$resume expert=on memory=v2"

cd "$REPO"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

# Isolated from ImmRep25 on/off (db 0 / prefix pmhctcr) and funny (db 12).
python run.py \
  experiment=pmhctcr_python_patch_final \
  expert_prompt=default \
  llm=codex_terra \
  pipeline=memory_guided \
  memory=v2 \
  memory/llm=codex \
  pipeline_builder._target_=problems.pmhctcr.pipeline.PmhctcrMemoryGuidedPipelineBuilder \
  memory.writer.require_archive_or_positive_gain=false \
  "${EXTRA_ARGS[@]}" \
  max_mutants="$MAX_MUTANTS" \
  max_in_flight=1 \
  llm_max_concurrent=1 \
  request_timeout=180 \
  stage_timeout=240 \
  validator_timeout=900 \
  dag_timeout=1800 \
  redis.db=13 \
  redis.prefix=pmhctcr_final_mem \
  program_storage.config.key_prefix=pmhctcr_final_mem \
  redis.resume="$resume" \
  hydra.run.dir="$RUN_DIR" \
  hydra.job.chdir=false \
  2>&1 | tee -a "$RUN_DIR/launch.out"
