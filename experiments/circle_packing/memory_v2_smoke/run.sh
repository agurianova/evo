#!/usr/bin/env bash
# Real, bounded memory-v2 smoke on the tractable n=26 circle-packing problem.

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
RUN_DIR="${RUN_DIR:-$PROJ/outputs/memory-v2-circle-packing-smoke-$STAMP}"
CHECKPOINT_DIR="$RUN_DIR/memory"
ANALYTICS_DIR="$RUN_DIR/memory_v2_analytics"
REPORT_DIR="$ANALYTICS_DIR/bayesian_audit"
MAX_MUTANTS="${MAX_MUTANTS:-280}"
MEMORY_SEED="${MEMORY_SEED:-20260715}"
LINEAGE_DEPTH="${LINEAGE_DEPTH:-1}"
OPPORTUNITY_BUDGET="${OPPORTUNITY_BUDGET:-32}"
# Environment-specific candidate from the two 20260715-16 trajectories. The
# negative shared treatment mean preserves the randomized arm-risk split.
SAFETY_PRIOR_PROBABILITY="${SAFETY_PRIOR_PROBABILITY:-0.20}"
SAFETY_BASELINE_PRIOR_SD="${SAFETY_BASELINE_PRIOR_SD:-0.15}"
SAFETY_SHARED_EFFECT_PRIOR_MEAN="${SAFETY_SHARED_EFFECT_PRIOR_MEAN:--0.693147}"
OFFER_PROBABILITY="${OFFER_PROBABILITY:-0.50}"
SHADOW_LINEAGE_DEPTH="${SHADOW_LINEAGE_DEPTH:-3}"
SHADOW_OPPORTUNITY_BUDGET="${SHADOW_OPPORTUNITY_BUDGET:-32}"

mkdir -p "$RUN_DIR" "$CHECKPOINT_DIR" "$ANALYTICS_DIR"

if [[ -e "$CHECKPOINT_DIR/cards.json" \
      || -e "$CHECKPOINT_DIR/memory_v2_selection_evidence.sqlite3" \
      || -e "$CHECKPOINT_DIR/write_ledger.jsonl" ]]; then
  echo "Refusing to reuse a nonempty smoke checkpoint: $CHECKPOINT_DIR" >&2
  exit 2
fi

OVERRIDES=(
  storage=disk
  problem.name=alphaevolve/packing_circles/n_26
  llm=gpt54_mini
  llm.models.0.extra_body.reasoning.effort=low
  llm_base_url=https://openrouter.ai/api/v1
  model_name=openai/gpt-5.4-mini
  num_parents=1
  max_in_flight=4
  "max_mutants=$MAX_MUTANTS"
  stage_timeout=900
  dag_timeout=2400
  engine_config.terminal_drain_timeout_s=2700
  pipeline=memory_guided
  memory=v2
  memory/write=live
  post_step_hook.refresh_every=1
  memory/llm=gpt54_mini
  'memory.feature_config.behavior_keys=[fitness]'
  "memory.credit.lineage_depth=$LINEAGE_DEPTH"
  "memory.credit.opportunity_budget=$OPPORTUNITY_BUDGET"
  "memory.posterior_config.invalidity_prior_probability=$SAFETY_PRIOR_PROBABILITY"
  "memory.posterior_config.safety_baseline_prior_sd=$SAFETY_BASELINE_PRIOR_SD"
  "memory.posterior_config.safety_shared_effect_prior_mean=$SAFETY_SHARED_EFFECT_PRIOR_MEAN"
  "memory.posterior_config.reference_offer_probability=$OFFER_PROBABILITY"
  "memory.policy_config.offer_probability=$OFFER_PROBABILITY"
  "memory.run_seed=$MEMORY_SEED"
  "checkpoint_dir=$CHECKPOINT_DIR"
  "hydra.run.dir=$RUN_DIR"
)

printf '%s\n' \
  "problem=alphaevolve/packing_circles/n_26" \
  "run_dir=$RUN_DIR" \
  "checkpoint_dir=$CHECKPOINT_DIR" \
  "max_mutants=$MAX_MUTANTS" \
  "memory_seed=$MEMORY_SEED" \
  "lineage_depth=$LINEAGE_DEPTH" \
  "opportunity_budget=$OPPORTUNITY_BUDGET" \
  "safety_prior_probability=$SAFETY_PRIOR_PROBABILITY" \
  "safety_baseline_prior_sd=$SAFETY_BASELINE_PRIOR_SD" \
  "safety_shared_effect_prior_mean=$SAFETY_SHARED_EFFECT_PRIOR_MEAN" \
  "offer_probability=$OFFER_PROBABILITY" \
  "shadow_lineage_depth=$SHADOW_LINEAGE_DEPTH" \
  "shadow_opportunity_budget=$SHADOW_OPPORTUNITY_BUDGET" \
  "model_name=openai/gpt-5.4-mini" \
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

PYTHONPATH="$PROJ${PYTHONPATH:+:$PYTHONPATH}" gigaevo -f json \
  memory calibrate-safety "$CHECKPOINT_DIR/memory_v2_selection_evidence.sqlite3" \
  --output "$ANALYTICS_DIR/safety_calibration.json" \
  > "$ANALYTICS_DIR/safety_calibration_stdout.json"

REPORT_ARGS=(
  --ledger "$CHECKPOINT_DIR/memory_v2_selection_evidence.sqlite3"
  --output-dir "$REPORT_DIR"
  --shadow-depth "$SHADOW_LINEAGE_DEPTH"
  --shadow-budget "$SHADOW_OPPORTUNITY_BUDGET"
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
