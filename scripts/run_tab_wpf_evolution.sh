#!/usr/bin/env bash
set -euo pipefail

: "${GIGAEVO_TABULAR_DATA:?Set GIGAEVO_TABULAR_DATA to the TabM dataset root}"
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY for the selected OpenAI-compatible endpoint}"
: "${TAB_WPF_RUN_DIR:?Set TAB_WPF_RUN_DIR to a new, dedicated Hydra run directory}"

TAB_WPF_DATASET="${TAB_WPF_DATASET:-california}"
TAB_WPF_MAX_MUTANTS="${TAB_WPF_MAX_MUTANTS:-100}"
TAB_WPF_LLM_BASE_URL="${TAB_WPF_LLM_BASE_URL:-https://openrouter.ai/api/v1}"
TAB_WPF_MODEL_NAME="${TAB_WPF_MODEL_NAME:-google/gemini-3-flash-preview}"
TAB_WPF_PYTHON="${TAB_WPF_PYTHON:-python}"
TAB_WPF_MAX_IN_FLIGHT="${TAB_WPF_MAX_IN_FLIGHT:-2}"
TAB_WPF_MAX_TOKENS="${TAB_WPF_MAX_TOKENS:-8192}"

for value_name in TAB_WPF_MAX_MUTANTS TAB_WPF_MAX_IN_FLIGHT TAB_WPF_MAX_TOKENS; do
  value="${!value_name}"
  if ! [[ "$value" =~ ^[1-9][0-9]*$ ]]; then
    echo "$value_name must be a positive integer" >&2
    exit 2
  fi
done

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(dirname -- "$SCRIPT_DIR")"
cd "$REPO_ROOT"

export GIGAEVO_TABULAR_EVAL_DATASET="$TAB_WPF_DATASET"

exec "$TAB_WPF_PYTHON" run.py \
  experiment=tab_wpf \
  "problem.dataset=${TAB_WPF_DATASET}" \
  "max_mutants=${TAB_WPF_MAX_MUTANTS}" \
  "llm_base_url=${TAB_WPF_LLM_BASE_URL}" \
  "model_name=${TAB_WPF_MODEL_NAME}" \
  "max_in_flight=${TAB_WPF_MAX_IN_FLIGHT}" \
  "llm_max_concurrent=${TAB_WPF_MAX_IN_FLIGHT}" \
  "max_tokens=${TAB_WPF_MAX_TOKENS}" \
  "hydra.run.dir=${TAB_WPF_RUN_DIR}"
