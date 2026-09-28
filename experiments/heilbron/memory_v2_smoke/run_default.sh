#!/usr/bin/env bash
# Fresh Heilbronn run using the shipped base experiment and memory-v2 defaults.

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
RUN_DIR="${RUN_DIR:-$PROJ/outputs/memory-v2-heilbron-default-$STAMP}"
CHECKPOINT_DIR="$RUN_DIR/memory"
ANALYTICS_DIR="$RUN_DIR/memory_v2_analytics"
REPORT_DIR="$ANALYTICS_DIR/bayesian_audit"
MAX_MUTANTS="${MAX_MUTANTS:-64}"
MEMORY_LLM_CONFIG="${MEMORY_LLM_CONFIG:-qwen_instruct}"
: "${LOCAL_LLM_PROXY:?Set LOCAL_LLM_PROXY in .env to the local LiteLLM endpoint}"
if [[ "$MEMORY_LLM_CONFIG" == "qwen_instruct" ]]; then
  : "${LITELLM_MASTER_KEY:?Set LITELLM_MASTER_KEY in .env for memory/llm=qwen_instruct}"
fi
LOCAL_LLM_PROXY_HOST="${LOCAL_LLM_PROXY#*://}"
LOCAL_LLM_PROXY_HOST="${LOCAL_LLM_PROXY_HOST%%[:/]*}"
export NO_PROXY="${NO_PROXY:+$NO_PROXY,}localhost,127.0.0.1,$LOCAL_LLM_PROXY_HOST"
export no_proxy="$NO_PROXY"

mkdir -p "$RUN_DIR" "$ANALYTICS_DIR"
if [[ -e "$CHECKPOINT_DIR/cards.json" \
      || -e "$CHECKPOINT_DIR/memory_v2_selection_evidence.sqlite3" \
      || -e "$CHECKPOINT_DIR/write_ledger.jsonl" ]]; then
  echo "Refusing to reuse a nonempty checkpoint: $CHECKPOINT_DIR" >&2
  exit 2
fi

OVERRIDES=(
  problem.name=heilbron
  memory=v2
  memory/write=live
  "memory/llm=$MEMORY_LLM_CONFIG"
  "max_mutants=$MAX_MUTANTS"
  "hydra.run.dir=$RUN_DIR"
)

printf '%s\n' \
  "problem=heilbron" \
  "run_dir=$RUN_DIR" \
  "checkpoint_dir=$CHECKPOINT_DIR" \
  "max_mutants=$MAX_MUTANTS" \
  "memory_llm_config=$MEMORY_LLM_CONFIG" \
  "memory_llm_base_url=$LOCAL_LLM_PROXY" \
  "git_commit=$(git -C "$PROJ" rev-parse HEAD)" \
  "semantic_overrides=problem.name,memory=v2,memory/write=live,memory/llm,max_mutants,hydra.run.dir" \
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

PYTHONPATH="$PROJ${PYTHONPATH:+:$PYTHONPATH}" gigaevo -f json \
  memory calibrate-safety "$CHECKPOINT_DIR/memory_v2_selection_evidence.sqlite3" \
  --output "$ANALYTICS_DIR/safety_calibration.json" \
  > "$ANALYTICS_DIR/safety_calibration_stdout.json"

REPORT_ARGS=(
  --ledger "$CHECKPOINT_DIR/memory_v2_selection_evidence.sqlite3"
  --output-dir "$REPORT_DIR"
  --shadow-depth 3
  --shadow-budget 32
)
if [[ "${SEND_TELEGRAM:-1}" == "1" ]]; then
  REPORT_ARGS+=(--send-telegram)
fi
"$PYTHON" experiments/hover/memory_v2_smoke/latex_report.py "${REPORT_ARGS[@]}" \
  | tee "$REPORT_DIR.log"

echo "Run complete: $RUN_DIR"
echo "Audit report: $ANALYTICS_DIR/report.md"
echo "Dashboard: $ANALYTICS_DIR/memory_v2_dashboard.png"
echo "Bayesian PDF: $REPORT_DIR/memory_v2_bayesian_audit.pdf"
