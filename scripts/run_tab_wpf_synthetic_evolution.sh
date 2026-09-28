#!/usr/bin/env bash
set -euo pipefail

: "${TAB_WPF_TASK_BANK:?Set TAB_WPF_TASK_BANK to the frozen 100-task bank}"
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY for the selected OpenAI-compatible endpoint}"
: "${TAB_WPF_RUN_DIR:?Set TAB_WPF_RUN_DIR to a new, dedicated Hydra run directory}"
: "${TAB_WPF_LLM_BASE_URL:?Set TAB_WPF_LLM_BASE_URL explicitly for this run}"
: "${TAB_WPF_MODEL_NAME:?Set TAB_WPF_MODEL_NAME explicitly for this run}"

TAB_WPF_MAX_MUTANTS="${TAB_WPF_MAX_MUTANTS:-200}"
TAB_WPF_PYTHON="${TAB_WPF_PYTHON:-python}"
TAB_WPF_MAX_IN_FLIGHT="${TAB_WPF_MAX_IN_FLIGHT:-2}"
TAB_WPF_MAX_TOKENS="${TAB_WPF_MAX_TOKENS:-8192}"
TAB_WPF_ARCHIVE_SELECTOR="${TAB_WPF_ARCHIVE_SELECTOR:-point}"

# The launcher changes into the repository before invoking Hydra.  Resolve
# user-supplied paths first so a relative path cannot be validated in one
# directory and then interpreted as a different target after `cd`.
TAB_WPF_TASK_BANK="$(realpath -- "$TAB_WPF_TASK_BANK")"
TAB_WPF_RUN_DIR="$(realpath -m -- "$TAB_WPF_RUN_DIR")"

for value_name in TAB_WPF_MAX_MUTANTS TAB_WPF_MAX_IN_FLIGHT TAB_WPF_MAX_TOKENS; do
  value="${!value_name}"
  if ! [[ "$value" =~ ^[1-9][0-9]*$ ]]; then
    echo "$value_name must be a positive integer" >&2
    exit 2
  fi
done

if [[ ! -f "$TAB_WPF_TASK_BANK/manifest.json" ]]; then
  echo "No manifest.json in TAB_WPF_TASK_BANK=$TAB_WPF_TASK_BANK" >&2
  exit 2
fi
if [[ -d "$TAB_WPF_RUN_DIR" ]] && [[ -n "$(find "$TAB_WPF_RUN_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "TAB_WPF_RUN_DIR must be absent or empty: $TAB_WPF_RUN_DIR" >&2
  exit 2
fi
if [[ "$TAB_WPF_ARCHIVE_SELECTOR" != "point" ]] && \
   [[ "$TAB_WPF_ARCHIVE_SELECTOR" != "paired_bootstrap" ]]; then
  echo "TAB_WPF_ARCHIVE_SELECTOR must be point or paired_bootstrap" >&2
  exit 2
fi

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(dirname -- "$SCRIPT_DIR")"
cd "$REPO_ROOT"

echo "Verifying frozen synthetic task bank..." >&2
"$TAB_WPF_PYTHON" scripts/generate_tab_wpf_task_bank.py \
  "$TAB_WPF_TASK_BANK" --verify-only >/dev/null

export GIGAEVO_TAB_WPF_EVAL_MODE=synthetic
export GIGAEVO_TAB_WPF_TASK_BANK="$TAB_WPF_TASK_BANK"
export GIGAEVO_TAB_WPF_META_SPLIT=meta_train

exec "$TAB_WPF_PYTHON" run.py \
  experiment=tab_wpf_synthetic \
  "problem.task_bank=${TAB_WPF_TASK_BANK}" \
  problem.task_split=meta_train \
  "archive_selector=${TAB_WPF_ARCHIVE_SELECTOR}" \
  "max_mutants=${TAB_WPF_MAX_MUTANTS}" \
  "llm_base_url=${TAB_WPF_LLM_BASE_URL}" \
  "model_name=${TAB_WPF_MODEL_NAME}" \
  "max_in_flight=${TAB_WPF_MAX_IN_FLIGHT}" \
  "llm_max_concurrent=${TAB_WPF_MAX_IN_FLIGHT}" \
  "max_tokens=${TAB_WPF_MAX_TOKENS}" \
  "hydra.run.dir=${TAB_WPF_RUN_DIR}"
