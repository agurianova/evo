#!/usr/bin/env bash
# funny: analog of pmhctcr_final_terra_expert_on_m100_r1 on double_ood_seed.
# Only differences: PMHCTCR_DATA=double_ood_seed and 3-fold leave-one-pMHC-out
# CV inside validate() (2 pMHCs train / 1 pMHC val, fitness = mean AUCPR).
#
# Usage:
#   ./scripts/launch_pmhctcr_funny_terra.sh
#   MAX_MUTANTS=100 ./scripts/launch_pmhctcr_funny_terra.sh
#   nohup ./scripts/launch_pmhctcr_funny_terra.sh > outputs/_funny.log 2>&1 &

set -euo pipefail

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BASE="$(CDPATH= cd -- "$REPO/.." && pwd)"
PCE="$BASE/python_code_evolution"
MAX_MUTANTS="${MAX_MUTANTS:-100}"
RUN_NAME="${RUN_NAME:-pmhctcr_funny_terra_expert_on_m100_r1}"
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

export PMHCTCR_DATA="${PMHCTCR_DATA:-$REPO/double_ood_seed}"
export PMHCTCR_SPLIT="${PMHCTCR_SPLIT:-cv3}"
if [[ ! -f "$PMHCTCR_DATA/tables/samples.parquet" ]]; then
  echo "PMHCTCR_DATA=$PMHCTCR_DATA has no tables/samples.parquet" >&2
  exit 6
fi

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
if [[ -d "$RUN_DIR/storage/pmhctcr_funny" || -d "$RUN_DIR/storage/pmhctcr" ]]; then
  resume=true
fi
mkdir -p "$RUN_DIR"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] START $RUN_NAME max_mutants=$MAX_MUTANTS resume=$resume data=$PMHCTCR_DATA split=$PMHCTCR_SPLIT"

cd "$REPO"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

# 3-fold fit is ~3x a single ImmRep25 val; keep validator under dag_timeout.
python run.py \
  experiment=pmhctcr_python_patch_final \
  expert_prompt=default \
  llm=codex_terra \
  "${EXTRA_ARGS[@]}" \
  max_mutants="$MAX_MUTANTS" \
  max_in_flight=1 \
  llm_max_concurrent=1 \
  request_timeout=180 \
  stage_timeout=240 \
  validator_timeout=1800 \
  dag_timeout=2400 \
  redis.db=12 \
  redis.prefix=pmhctcr_funny \
  program_storage.config.key_prefix=pmhctcr_funny \
  redis.resume="$resume" \
  hydra.run.dir="$RUN_DIR" \
  hydra.job.chdir=false \
  2>&1 | tee -a "$RUN_DIR/launch.out"
