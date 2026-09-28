#!/usr/bin/env bash
# Expert-prompt ablation on the final python_patch experiment (gpt-5.6-luna).
#
# Two parallel chains (expert on vs off), each with 3 independent sequential
# luna runs of max_mutants=100. Within a chain, run r2 starts only after r1
# finishes; the two chains do not wait for each other.
#
# Usage:
#   ./scripts/launch_pmhctcr_final_luna_expert_ablation.sh
#   MAX_MUTANTS=100 NUM_REPLICATES=3 ./scripts/launch_pmhctcr_final_luna_expert_ablation.sh
#   nohup ./scripts/launch_pmhctcr_final_luna_expert_ablation.sh \
#     > outputs/_final_luna_expert_ablation_supervisor.log 2>&1 &

set -euo pipefail

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
BASE="$(CDPATH= cd -- "$REPO/.." && pwd)"
PCE="$BASE/python_code_evolution"
MAX_MUTANTS="${MAX_MUTANTS:-100}"
NUM_REPLICATES="${NUM_REPLICATES:-3}"
RUN_PREFIX="${RUN_PREFIX:-pmhctcr_final_luna}"

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

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] preflight: checking gpt-5.6-luna ..."
preflight_out="$(printf 'Reply with exactly: PREFLIGHT_OK\n' \
  | timeout 180 codex exec --model gpt-5.6-luna \
      -c 'forced_login_method="chatgpt"' \
      --sandbox read-only --ephemeral --skip-git-repo-check 2>&1 || true)"
if [[ "$preflight_out" != *PREFLIGHT_OK* ]]; then
  echo "$preflight_out" | tail -8 >&2
  echo "preflight FAILED" >&2
  exit 5
fi
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] preflight: luna reachable"

mkdir -p "$REPO/outputs"
cd "$REPO"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1

run_one() {
  local run_name="$1"
  local expert_cfg="$2"
  local run_dir="$REPO/outputs/$run_name"
  mkdir -p "$run_dir"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] START $run_name expert=$expert_cfg max_mutants=$MAX_MUTANTS"
  python run.py \
    experiment=pmhctcr_python_patch_final \
    "$expert_cfg" \
    llm=codex \
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
    2>&1 | tee -a "$run_dir/launch.out"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] DONE  $run_name"
}

run_chain() {
  local label="$1"
  local expert_cfg="$2"
  local chain_log="$REPO/outputs/${RUN_PREFIX}_${label}_chain.log"
  {
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] chain start label=$label expert=$expert_cfg"
    for ((rep = 1; rep <= NUM_REPLICATES; rep++)); do
      run_name="${RUN_PREFIX}_${label}_m${MAX_MUTANTS}_r${rep}"
      if [[ -d "$REPO/outputs/$run_name/storage/pmhctcr" ]]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] skip $run_name (storage exists)"
        continue
      fi
      run_one "$run_name" "$expert_cfg"
    done
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] chain done label=$label"
  } >>"$chain_log" 2>&1
}

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] launching parallel chains: expert on/off, $NUM_REPLICATES x m$MAX_MUTANTS"

run_chain expert_on expert_prompt=default &
pid_expert=$!
echo "$pid_expert" >"$REPO/outputs/${RUN_PREFIX}_expert_on_chain.pid"

run_chain expert_off expert_prompt=disabled &
pid_no_expert=$!
echo "$pid_no_expert" >"$REPO/outputs/${RUN_PREFIX}_expert_off_chain.pid"

echo "expert_on  chain pid=$pid_expert log=outputs/${RUN_PREFIX}_expert_on_chain.log"
echo "expert_off chain pid=$pid_no_expert log=outputs/${RUN_PREFIX}_expert_off_chain.log"
echo "runs:"
for label in expert_on expert_off; do
  for ((rep = 1; rep <= NUM_REPLICATES; rep++)); do
    echo "  outputs/${RUN_PREFIX}_${label}_m${MAX_MUTANTS}_r${rep}"
  done
done

wait "$pid_expert" "$pid_no_expert"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] all chains finished"
