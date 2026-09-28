#!/usr/bin/env bash
# S4-style DAG-tab with Memory V2: 3 replicas x 100 mutations.
#
# Mutation model: Gemini 3.5 Flash (default) or Gemini 3 Flash via OpenRouter.
# Memory model: Qwen/Qwen3-235B-A22B-Instruct-2507 via the local LiteLLM proxy.
# Each replica owns a fresh persistent run directory and Memory V2 ledger/card bank.

set -Eeuo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="${GIGAEVO_PYTHON:-/home/jovyan/.mlspace/envs/evo/bin/python3}"
ENV_FILE="${GIGAEVO_ENV_FILE:-/home/jovyan/gigaevo/.env}"
PROXY_URL="${PROXY_URL:-http://10.232.39.158:4000/v1}"
DATASET="${DATASET:-california}"
MUTATION_LLM="${MUTATION_LLM:-gemini35_flash}"
REQUIRED_BASE=b9a2ad0da6efb336670ad69e88c5a9ab9f7640c2

cd "$REPO"
/usr/bin/git merge-base --is-ancestor "$REQUIRED_BASE" HEAD || {
  echo "ERROR: checkout does not contain required Memory V2 SE commit $REQUIRED_BASE" >&2
  exit 2
}
if ! /usr/bin/git diff --quiet || ! /usr/bin/git diff --cached --quiet; then
  echo "ERROR: launch checkout has tracked changes; commit or remove them first" >&2
  exit 2
fi
if [[ ! "$DATASET" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  echo "ERROR: invalid dataset name $DATASET" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
: "${OPENAI_API_KEY:?OPENAI_API_KEY must be set in $ENV_FILE}"
: "${LITELLM_MASTER_KEY:?LITELLM_MASTER_KEY must be set in $ENV_FILE}"

case "$MUTATION_LLM" in
  gemini35_flash)
    MUTATION_MODEL=google/gemini-3.5-flash
    MUTATION_OVERRIDES=(
      llm=gemini35_flash
      model_name=google/gemini-3.5-flash
      temperature=1.0
      max_tokens=32768
    )
    ;;
  gemini3_flash)
    MUTATION_MODEL=google/gemini-3-flash-preview
    MUTATION_OVERRIDES=(llm=gemini3_flash)
    ;;
  *)
    echo "ERROR: MUTATION_LLM must be gemini35_flash or gemini3_flash" >&2
    exit 2
    ;;
esac

export LOCAL_LLM_PROXY="$PROXY_URL"
PROXY_HOST="${PROXY_URL#*://}"
PROXY_HOST="${PROXY_HOST%%:*}"
NO_PROXY_HOSTS="$PROXY_HOST,localhost,127.0.0.1"
export NO_PROXY="$NO_PROXY_HOSTS${NO_PROXY:+,$NO_PROXY}"
export no_proxy="$NO_PROXY_HOSTS${no_proxy:+,$no_proxy}"

# The production card embedder is cached locally. Offline mode prevents the
# external egress proxy from turning an already-cached model load into a network
# dependency. Do not set SENTENCE_TRANSFORMERS_HOME: it changes the cache root.
export HF_HOME="${HF_HOME:-/home/jovyan/.cache/huggingface}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-$HF_HOME/hub}"
unset TRANSFORMERS_CACHE SENTENCE_TRANSFORMERS_HOME
export HF_HUB_OFFLINE=1

export GIGAEVO_TABULAR_DATA="${GIGAEVO_TABULAR_DATA:-/home/jovyan/tabm-data/data}"
if [[ ! -d "$GIGAEVO_TABULAR_DATA/$DATASET" ]]; then
  echo "ERROR: dataset not found at $GIGAEVO_TABULAR_DATA/$DATASET" >&2
  exit 2
fi
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-8}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-8}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-8}"
export PYTHONPATH="$REPO"

curl --connect-timeout 8 --max-time 30 -fsS -o /dev/null \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  https://openrouter.ai/api/v1/models
curl --noproxy "$PROXY_HOST" --connect-timeout 5 --max-time 20 -fsS -o /dev/null \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  "$PROXY_URL/models"

LABELS=(101 202 303)
CONC="${1:-3}"
START="${2:-1}"
END="${3:-3}"
if (( CONC < 1 || START < 1 || END > ${#LABELS[@]} || START > END )); then
  echo "usage: $0 [concurrency>=1] [start>=1] [end<=${#LABELS[@]}]" >&2
  exit 2
fi

TS="$(date +%Y%m%d_%H%M%S)"
RUNS_ROOT=/home/jovyan/gigaevo/experiments/dag_tab_envelope_s4_20260722/runs
OUT="${RUN_ROOT:-$RUNS_ROOT/memory_v2/${DATASET}/${MUTATION_LLM}/$TS}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
DRIVER="$OUT/driver.log"
{
  echo "=== lineage ==="
  echo "repo=$REPO"
  echo "commit=$(/usr/bin/git rev-parse HEAD)"
  echo "branch=$(/usr/bin/git rev-parse --abbrev-ref HEAD)"
  echo "output_root=$OUT"
  echo "dataset=$DATASET"
  echo "mutation_preset=$MUTATION_LLM"
  echo "mutation_model=$MUTATION_MODEL"
  echo "memory_model=Qwen/Qwen3-235B-A22B-Instruct-2507"
  echo "memory_proxy=$PROXY_URL"
  echo "cv_folds=${GIGAEVO_TABULAR_CV_FOLDS:-3}"
  echo "fitness_aggregation=${GIGAEVO_TABULAR_FITNESS:-mean}"
  "$PY" -c "import gigaevo, problems.dag_tab.validate as v; print('gigaevo=' + gigaevo.__file__); print('dag_tab=' + v.__file__)"
} 2>&1 | tee -a "$DRIVER"

run_one() {
  local label="$1"
  local rundir="$OUT/r${label}"
  local log="$OUT/r${label}.log"
  local rc
  if [[ -e "$rundir" ]]; then
    echo "ERROR: refusing to reuse existing replica directory $rundir" | tee -a "$DRIVER"
    return 2
  fi
  echo "=== $(date -Is) LAUNCH r${label} -> $rundir" | tee -a "$DRIVER"
  if "$PY" -u run.py \
    problem.name=dag_tab \
    problem.dataset="$DATASET" \
    loader=dag_tab_seed \
    program_format=json_document \
    memory/llm=qwen_instruct \
    memory.run_seed="$label" \
    mutation=structured_diff_dag_tab \
    mutation_operator.allowed_changes.max_nodes=10 \
    "${MUTATION_OVERRIDES[@]}" \
    max_mutants=100 \
    algorithm=tabular/2d_local_ood \
    hydra.run.dir="$rundir" \
    > "$log" 2>&1; then
    rc=0
  else
    rc=$?
  fi
  echo "=== $(date -Is) DONE r${label} exit=$rc" | tee -a "$DRIVER"
  return "$rc"
}

overall=0
i=$START
: > "$OUT/replica_pids.tsv"
while (( i <= END )); do
  pids=()
  batch_labels=()
  for ((k=0; k<CONC && i<=END; k++, i++)); do
    label="${LABELS[$((i - 1))]}"
    run_one "$label" &
    pid=$!
    pids+=("$pid")
    batch_labels+=("$label")
    printf '%s\t%s\n' "$label" "$pid" >> "$OUT/replica_pids.tsv"
  done
  for index in "${!pids[@]}"; do
    if ! wait "${pids[$index]}"; then
      echo "replica r${batch_labels[$index]} failed" | tee -a "$DRIVER"
      overall=1
    fi
  done
done

echo "=== $(date -Is) ALL REPLICAS FINISHED overall=$overall ===" | tee -a "$DRIVER"
exit "$overall"
