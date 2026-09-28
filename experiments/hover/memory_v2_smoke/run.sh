#!/usr/bin/env bash
# Bounded real-problem smoke for the memory-v2 causal bandit.

set -euo pipefail

PROJ="$(cd "$(dirname "$0")/../../.." && pwd)"
PRIMARY_REPO="$(dirname "$(git -C "$PROJ" rev-parse --path-format=absolute --git-common-dir)")"
PYTHON="${GIGAEVO_PYTHON:-$(command -v python)}"
SOURCE_ENV="${SOURCE_ENV:-$PRIMARY_REPO/.env}"

if [[ -f "$SOURCE_ENV" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$SOURCE_ENV"
  set +a
fi

STAMP="${RUN_STAMP:-$(date -u '+%Y%m%d_%H%M%S')}"
RUN_DIR="${RUN_DIR:-$PROJ/outputs/memory-v2-hover-smoke-$STAMP}"
CHECKPOINT_DIR="$RUN_DIR/memory"
ANALYTICS_DIR="$RUN_DIR/memory_v2_analytics"
MAX_MUTANTS="${MAX_MUTANTS:-16}"
MEMORY_SEED="${MEMORY_SEED:-20260715}"
# Smoke validation stays balanced; ordinary memory=v2 runs default to 0.70.
OFFER_PROBABILITY="${OFFER_PROBABILITY:-0.50}"
LLM_CONFIG="${LLM_CONFIG:-gemini35_flash}"
LLM_BASE_URL="${LLM_BASE_URL:-https://openrouter.ai/api/v1}"
MODEL_NAME="${MODEL_NAME:-google/gemini-3.5-flash}"
MEMORY_LLM_CONFIG="${MEMORY_LLM_CONFIG:-gemini}"
MEMORY_LLM_BASE_URL="${MEMORY_LLM_BASE_URL:-https://openrouter.ai/api/v1}"
MEMORY_MODEL_NAME="${MEMORY_MODEL_NAME:-google/gemini-3.5-flash}"
: "${LOCAL_LLM_PROXY:?Set LOCAL_LLM_PROXY in .env to the local LiteLLM/vLLM endpoint}"
LOCAL_LLM_PROXY_HOST="${LOCAL_LLM_PROXY#*://}"
LOCAL_LLM_PROXY_HOST="${LOCAL_LLM_PROXY_HOST%%[:/]*}"
export HOVER_CHAIN_URL="${HOVER_CHAIN_URL:-$LOCAL_LLM_PROXY}"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}localhost,127.0.0.1,$LOCAL_LLM_PROXY_HOST"
export no_proxy="$NO_PROXY"

mkdir -p "$RUN_DIR" "$CHECKPOINT_DIR" "$ANALYTICS_DIR"

if [[ -e "$CHECKPOINT_DIR/cards.json" \
      || -e "$CHECKPOINT_DIR/memory_v2_selection_evidence.sqlite3" \
      || -e "$CHECKPOINT_DIR/write_ledger.jsonl" ]]; then
  echo "Refusing to reuse a nonempty smoke checkpoint: $CHECKPOINT_DIR" >&2
  exit 2
fi

OVERRIDES=(
  storage=disk
  problem.name=chains/hover/full7_vectorized
  archive_selector=paired_bootstrap
  program_format=json_document
  mutation=carl_with_retrieval_tools
  algorithm=chains_bd3d
  enable_chain_structural_metrics=true
  "llm=$LLM_CONFIG"
  ~llm.models.0.extra_body.service_tier
  llm.models.0.extra_body.reasoning.effort=minimal
  "llm_base_url=$LLM_BASE_URL"
  "model_name=$MODEL_NAME"
  num_parents=1
  max_in_flight=4
  "max_mutants=$MAX_MUTANTS"
  max_tokens=60000
  stage_timeout=7200
  dag_timeout=14400
  engine_config.terminal_drain_timeout_s=14520
  pipeline=memory_guided
  memory=v2
  memory/write=live
  post_step_hook.refresh_every=1
  "memory/llm=$MEMORY_LLM_CONFIG"
  "memory.llm.models.0.model=$MEMORY_MODEL_NAME"
  "memory.llm.models.0.base_url=$MEMORY_LLM_BASE_URL"
  "memory.run_seed=$MEMORY_SEED"
  "memory.posterior_config.reference_offer_probability=$OFFER_PROBABILITY"
  "memory.policy_config.offer_probability=$OFFER_PROBABILITY"
  "checkpoint_dir=$CHECKPOINT_DIR"
  "hydra.run.dir=$RUN_DIR"
)

printf '%s\n' \
  "run_dir=$RUN_DIR" \
  "checkpoint_dir=$CHECKPOINT_DIR" \
  "max_mutants=$MAX_MUTANTS" \
  "memory_seed=$MEMORY_SEED" \
  "offer_probability=$OFFER_PROBABILITY" \
  "llm_config=$LLM_CONFIG" \
  "model_name=$MODEL_NAME" \
  "llm_base_url=$LLM_BASE_URL" \
  "memory_llm_config=$MEMORY_LLM_CONFIG" \
  "memory_model_name=$MEMORY_MODEL_NAME" \
  "memory_llm_base_url=$MEMORY_LLM_BASE_URL" \
  "hover_chain_url=$HOVER_CHAIN_URL" \
  "git_commit=$(git -C "$PROJ" rev-parse HEAD)" \
  > "$RUN_DIR/run_manifest.txt"

cd "$PROJ"
"$PYTHON" run.py "${OVERRIDES[@]}" --cfg job > "$RUN_DIR/resolved_config.yaml"

if [[ "${CONFIG_ONLY:-0}" == "1" ]]; then
  echo "Configuration composed: $RUN_DIR/resolved_config.yaml"
  exit 0
fi

"$PYTHON" run.py "${OVERRIDES[@]}" 2>&1 | tee "$RUN_DIR/run.log"

"$PYTHON" experiments/hover/memory_v2_smoke/analyze.py \
  --ledger "$CHECKPOINT_DIR/memory_v2_selection_evidence.sqlite3" \
  --output-dir "$ANALYTICS_DIR" \
  | tee "$ANALYTICS_DIR/analyze.log"

echo "Run complete: $RUN_DIR"
echo "Audit report: $ANALYTICS_DIR/report.md"
echo "Dashboard: $ANALYTICS_DIR/memory_v2_dashboard.png"
