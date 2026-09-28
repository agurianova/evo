#!/usr/bin/env bash
# Run Luna m200 replicates sequentially (one finishes, then the next starts).
#
# Usage:
#   ./scripts/launch_pmhctcr_python_patch_luna_m200_sequential.sh 5 6 7 8 9
#   nohup ./scripts/launch_pmhctcr_python_patch_luna_m200_sequential.sh 5 6 7 8 9 \
#     > outputs/_sequential_luna_m200_v5_v9.log 2>&1 &

set -euo pipefail

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BASE="$(CDPATH= cd -- "$REPO/.." && pwd)"
PCE="$BASE/python_code_evolution"
MAX_MUTANTS="${MAX_MUTANTS:-200}"

if [[ "$#" -lt 1 ]]; then
  echo "usage: $0 <run_numbers...>  e.g. $0 5 6 7 8 9" >&2
  exit 2
fi

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

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] sequential luna m200: runs=$* max_mutants=$MAX_MUTANTS"
echo "preflight: skipped (HarnessChat preflight runs inside run.py)"

cd "$REPO"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

run_one() {
  local run_num="$1"
  local run_name="pmhctcr_python_patch_luna_m200_v${run_num}"
  local run_dir="$REPO/outputs/$run_name"
  local resume=false
  if [[ -d "$run_dir/storage/pmhctcr" ]]; then
    resume=true
  fi
  mkdir -p "$run_dir"
  echo ""
  echo "================================================================"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] START $run_name (resume=$resume)"
  echo "================================================================"
  set +e
  python run.py \
    experiment=pmhctcr \
    mutation=python_patch \
    algorithm=pmhctcr_python_2d \
    memory=none \
    loader.pattern=python_patch_seed.py \
    prompts.dir='${problem.dir}/prompts_python_patch' \
    pipeline_builder._target_=problems.pmhctcr.pipeline.PmhctcrGuidedPipelineBuilder \
    llm=codex \
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
  local rc=${PIPESTATUS[0]}
  set -e
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] END $run_name exit=$rc"
  return "$rc"
}

for run_num in "$@"; do
  run_one "$run_num"
done

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] sequential queue finished"
