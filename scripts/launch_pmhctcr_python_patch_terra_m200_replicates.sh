#!/usr/bin/env bash
# Launch N independent pMHC-TCR python_patch runs on gpt-5.6-terra.
# Same inputs as outputs/pmhctcr_python_patch_luna_m200_v2, but:
#   - llm=codex_terra
#   - max_mutants=200
#   - redis.resume=false (fresh independent runs)
#
# Usage:
#   ./scripts/launch_pmhctcr_python_patch_terra_m200_replicates.sh
#   ./scripts/launch_pmhctcr_python_patch_terra_m200_replicates.sh 5 200
#   ./scripts/launch_pmhctcr_python_patch_terra_m200_replicates.sh 5 200 v3

set -euo pipefail

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BASE="$(CDPATH= cd -- "$REPO/.." && pwd)"
PCE="$BASE/python_code_evolution"
NUM_RUNS="${1:-5}"
MAX_MUTANTS="${2:-200}"
RUN_SUFFIX="${3:-v1}"

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
echo "egress: HTTPS_PROXY loaded from $PCE/scripts/proxy.env"

echo "preflight: checking gpt-5.6-terra ..."
preflight_out="$(printf 'Reply with exactly: PREFLIGHT_OK\n' \
  | timeout 180 codex exec --model gpt-5.6-terra \
      -c 'forced_login_method="chatgpt"' \
      --sandbox read-only --ephemeral --skip-git-repo-check 2>&1 || true)"
if [[ "$preflight_out" != *PREFLIGHT_OK* ]]; then
  echo "$preflight_out" | tail -8 >&2
  echo "preflight FAILED" >&2
  exit 5
fi
echo "preflight: terra reachable"

mkdir -p "$REPO/outputs"
cd "$REPO"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

launch_one() {
  local run_name="$1"
  local run_dir="$REPO/outputs/$run_name"
  mkdir -p "$run_dir"
  echo "launching $run_name -> $run_dir"
  nohup python run.py \
    experiment=pmhctcr \
    mutation=python_patch \
    algorithm=pmhctcr_python_2d \
    memory=none \
    loader.pattern=python_patch_seed.py \
    prompts.dir='${problem.dir}/prompts_python_patch' \
    pipeline_builder._target_=problems.pmhctcr.pipeline.PmhctcrGuidedPipelineBuilder \
    llm=codex_terra \
    max_mutants="$MAX_MUTANTS" \
    max_in_flight=1 \
    llm_max_concurrent=1 \
    request_timeout=180 \
    stage_timeout=240 \
    validator_timeout=900 \
    dag_timeout=1800 \
    redis.resume=false \
    hydra.run.dir="$run_dir" \
    hydra.job.chdir=false \
    >"$run_dir/launch.out" 2>&1 &
  echo "$!" >"$run_dir/launch.pid"
  echo "  pid=$(cat "$run_dir/launch.pid")"
}

for ((i = 0; i < NUM_RUNS; i++)); do
  if [[ "$RUN_SUFFIX" =~ ^v([0-9]+)$ ]]; then
    start="${BASH_REMATCH[1]}"
    run_name="pmhctcr_python_patch_terra_m200_v$((start + i))"
  else
    run_name="pmhctcr_python_patch_terra_m200_${RUN_SUFFIX}_$((i + 1))"
  fi
  if [[ -d "$REPO/outputs/$run_name/storage/pmhctcr" ]]; then
    echo "skip $run_name (storage already exists; delete to relaunch)" >&2
    continue
  fi
  launch_one "$run_name"
done

echo "done: launched up to $NUM_RUNS terra m${MAX_MUTANTS} replicate(s)"
