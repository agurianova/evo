#!/usr/bin/env bash
# Launch the six-model California baseline campaign.

set -Eeuo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd "$script_dir/../.." && pwd)"
python_bin="${GIGAEVO_TABULAR_PYTHON:-/home/jovyan/.mlspace/envs/evo_torch/bin/python}"
env_file="${GIGAEVO_ENV_FILE:-$repo_dir/.env}"
campaign_name="${GIGAEVO_TABULAR_CAMPAIGN_NAME:-tabular_baselines_california_$(date +%Y%m%d_%H%M%S)}"
campaign_dir="${GIGAEVO_TABULAR_CAMPAIGN_DIR:-$script_dir/artifacts/campaigns/$campaign_name}"
models=(realmlp tabicl tabpfn tabfm lightgbm xgboost)

cd "$repo_dir"
source_status="$(git status --porcelain --untracked-files=normal)"
if [[ -n "$source_status" ]]; then
  echo "ERROR: launch from a clean worktree so the recorded commit identifies the exact source." >&2
  printf '%s\n' "$source_status" >&2
  exit 2
fi

mkdir -p "$campaign_dir"/{logs,runs,status}
exec 9>"$campaign_dir/launcher.lock"
if ! flock -n 9; then
  echo "ERROR: campaign launcher is already running: $campaign_dir" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$env_file"
set +a

: "${OPENAI_API_KEY:?OPENAI_API_KEY must be set in $env_file}"
: "${LITELLM_MASTER_KEY:?LITELLM_MASTER_KEY must be set in $env_file}"
: "${LOCAL_LLM_PROXY:?LOCAL_LLM_PROXY must be set in $env_file}"

export GIGAEVO_TABULAR_DATA="${GIGAEVO_TABULAR_DATA:-/home/jovyan/tabm-data/data}"
export GIGAEVO_TABULAR_DAG_GPU_DEVICES="${GIGAEVO_TABULAR_DAG_GPU_DEVICES:-0,1,2,3}"
cpu_threads="${GIGAEVO_TABULAR_CPU_THREADS:-4}"
export OMP_NUM_THREADS="$cpu_threads"
export MKL_NUM_THREADS="$cpu_threads"
export OPENBLAS_NUM_THREADS="$cpu_threads"
export PYTHONPATH="$repo_dir"
unset GIGAEVO_TABULAR_CV_FOLDS

if [[ ! -d "$GIGAEVO_TABULAR_DATA/california" ]]; then
  echo "ERROR: California data missing under $GIGAEVO_TABULAR_DATA" >&2
  exit 2
fi
for model_name in "${models[@]}"; do
  if [[ -e "$campaign_dir/runs/$model_name" ]]; then
    echo "ERROR: refusing to reuse $campaign_dir/runs/$model_name" >&2
    exit 2
  fi
done

proxy_host="${LOCAL_LLM_PROXY#*://}"
proxy_host="${proxy_host%%/*}"
proxy_host="${proxy_host%%:*}"
no_proxy_hosts="$proxy_host,localhost,127.0.0.1"
export NO_PROXY="$no_proxy_hosts${NO_PROXY:+,$NO_PROXY}"
export no_proxy="$no_proxy_hosts${no_proxy:+,$no_proxy}"

{
  echo "started_at=$(date -Is)"
  echo "repo=$repo_dir"
  echo "commit=$(git rev-parse HEAD)"
  echo "branch=$(git rev-parse --abbrev-ref HEAD)"
  echo "python=$python_bin"
  echo "dataset=california"
  echo "mutation_llm=gemini35_flash"
  echo "memory_llm=qwen_instruct"
  echo "cv_folds=3"
  echo "max_mutants=100"
  echo "max_nodes=10"
  echo "models=${models[*]}"
  "$python_bin" - <<'PY'
from importlib.metadata import version

for package in (
    "torch",
    "tabm",
    "pytabkit",
    "tabicl",
    "tabpfn",
    "tabfm",
    "lightgbm",
    "xgboost",
):
    print(f"{package}={version(package)}")
PY
} > "$campaign_dir/manifest.env"

git status --short > "$campaign_dir/source_status.txt"
find config/experiment/tabular_dag problems/tabular_dag_baselines problems/dag_tab \
  -type f -not -path '*/__pycache__/*' -print0 \
  | sort -z | xargs -0 sha256sum > "$campaign_dir/source_sha256.txt"

"$python_bin" - <<'PY' > "$campaign_dir/logs/tabpfn_preflight.log" 2>&1
from problems.tabular_dag_baselines.tabpfn.backend import (
    TabPFNConfig,
    ensure_tabpfn_ready,
)

checkpoint = ensure_tabpfn_ready(TabPFNConfig(), which="regressor")
print(checkpoint)
print(checkpoint.stat().st_size)
PY

"$python_bin" - <<'PY' > "$campaign_dir/logs/tabfm_preflight.log" 2>&1
from problems.tabular_dag_baselines.tabfm.backend import (
    TabFMConfig,
    ensure_tabfm_ready,
)

checkpoint = ensure_tabfm_ready(TabFMConfig.from_env(), model_type="regression")
weights = checkpoint / "regression" / "model.safetensors"
if not weights.is_file():
    weights = checkpoint / "model.safetensors"
print(checkpoint)
print(weights.stat().st_size)
PY

common_overrides=(
  problem.dataset=california
  llm=gemini35_flash
  pipeline=memory_guided
  memory=v2
  memory/llm=qwen_instruct
  algorithm=tabular/2d_local_ood
  mutation_operator.allowed_changes.max_nodes=10
  max_mutants=100
)

run_one() {
  local model_name="$1"
  local run_dir="$campaign_dir/runs/$model_name"
  local log_file="$campaign_dir/logs/$model_name.log"
  local status_file="$campaign_dir/status/$model_name.env"
  local exit_code
  local run_state

  {
    echo "model=$model_name"
    echo "pid=$BASHPID"
    echo "started_at=$(date -Is)"
    echo "state=running"
  } > "$status_file"
  echo "$(date -Is) LAUNCH $model_name -> $run_dir" | tee -a "$campaign_dir/driver.log"

  if "$python_bin" -u run.py \
    experiment="tabular_dag/$model_name" \
    "${common_overrides[@]}" \
    hydra.run.dir="$run_dir" \
    > "$log_file" 2>&1; then
    exit_code=0
    run_state=complete
  else
    exit_code=$?
    run_state=failed
  fi

  {
    echo "model=$model_name"
    echo "pid=$BASHPID"
    echo "finished_at=$(date -Is)"
    echo "state=$run_state"
    echo "exit_code=$exit_code"
  } > "$status_file"
  echo "$(date -Is) DONE $model_name exit=$exit_code" | tee -a "$campaign_dir/driver.log"
  return "$exit_code"
}

: > "$campaign_dir/driver.log"
: > "$campaign_dir/pids.tsv"
pids=()
labels=()
for model_name in "${models[@]}"; do
  run_one "$model_name" &
  process_id=$!
  pids+=("$process_id")
  labels+=("$model_name")
  printf '%s\t%s\n' "$model_name" "$process_id" >> "$campaign_dir/pids.tsv"
done

overall=0
for index in "${!pids[@]}"; do
  if ! wait "${pids[$index]}"; then
    echo "${labels[$index]} failed" | tee -a "$campaign_dir/driver.log"
    overall=1
  fi
done

echo "$(date -Is) ALL RUNS FINISHED overall=$overall" | tee -a "$campaign_dir/driver.log"
echo "$campaign_dir"
exit "$overall"
