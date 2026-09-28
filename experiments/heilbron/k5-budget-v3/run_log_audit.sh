#!/usr/bin/env bash
# Run log_audit.py against every live run log and emit consolidated markdown.
# Per-run reports: LOG_AUDIT_LIVE_<label>.md
# Summary: LOG_AUDIT_LIVE_SUMMARY.md
#
# NOTE: no `set -e` — grep returns non-zero on empty matches during the
# gen-0 bootstrap phase before structured events start emitting.
set -o pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
EXP_DIR="$PROJ/experiments/heilbron/k5-budget-v3"
AUDIT="$PROJ/tools/experiment/log_audit.py"
SUMMARY="$EXP_DIR/LOG_AUDIT_LIVE_SUMMARY.md"

cd "$PROJ"

{
  echo "# Live Log Audit — heilbron/k5-budget-v3"
  echo ""
  echo "**Generated:** $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "| Run | Role | Events | Result | TRACKER_WRITE | LINEAGE_TREND | LT trend!=null | HOF_ROTATE | CELL_PICK |"
  echo "|---|---|---|---|---|---|---|---|---|"
} > "$SUMMARY"

declare -A ROLE_MAP=(
  [K3_1_G]=constructor [K3_1_D]=improver
  [K3_2_G]=constructor [K3_2_D]=improver
  [K5_1_G]=constructor [K5_1_D]=improver
  [K5_2_G]=constructor [K5_2_D]=improver
)

# Helper: grep-first-or-zero. $1=pattern, $2=file, $3=awk field (e.g. $2)
extract_count() {
  local pat="$1"; local file="$2"; local field="$3"
  local val
  val=$(grep -oE "$pat" "$file" 2>/dev/null | tail -1 | awk "{print $field}")
  echo "${val:-0}"
}

for LABEL in K3_1_G K3_1_D K3_2_G K3_2_D K5_1_G K5_1_D K5_2_G K5_2_D; do
  ROLE="${ROLE_MAP[$LABEL]}"
  LOG_FILE="$EXP_DIR/run_${LABEL}.log"
  OUT_FILE="$EXP_DIR/LOG_AUDIT_LIVE_${LABEL}.md"

  if [ ! -f "$LOG_FILE" ]; then
    echo "| $LABEL | $ROLE | - | MISSING | - | - | - | - | - |" >> "$SUMMARY"
    continue
  fi

  "$PYTHON" "$AUDIT" "heilbron/k5-budget-v3" "$LOG_FILE" \
    --population-role="$ROLE" > "$OUT_FILE" 2>&1

  RESULT=$(grep -oE "Audit result: (PASSED|FAILED)" "$OUT_FILE" 2>/dev/null | tail -1 | awk '{print $3}')
  RESULT="${RESULT:-?}"
  EVENTS=$(grep -oE "canonical events parsed[^0-9]+[0-9]+" "$OUT_FILE" 2>/dev/null | grep -oE "[0-9]+$")
  EVENTS="${EVENTS:-0}"
  TW=$(extract_count "TRACKER_WRITE: [0-9]+" "$OUT_FILE" '$2')
  LT=$(extract_count "LINEAGE_TREND: [0-9]+" "$OUT_FILE" '$2')
  LT_VALID=$(extract_count "trend!=null: [0-9]+" "$OUT_FILE" '$2')
  HR=$(extract_count "HOF_ROTATE: [0-9]+" "$OUT_FILE" '$2')
  CP=$(extract_count "CELL_PICK: [0-9]+" "$OUT_FILE" '$2')

  echo "| $LABEL | $ROLE | $EVENTS | $RESULT | $TW | $LT | $LT_VALID | $HR | $CP |" >> "$SUMMARY"
done

{
  echo ""
  echo "## Process Liveness"
  echo ""
  "$PYTHON" - << PYEOF
import yaml, os
with open('$EXP_DIR/experiment.yaml') as f:
    m = yaml.safe_load(f)
runs = (m.get('contract') or {}).get('runs', []) or m.get('runs', [])
for r in runs:
    label = r.get('label'); pid = r.get('pid')
    alive = False
    try:
        os.kill(int(pid), 0); alive = True
    except (OSError, TypeError, ValueError):
        pass
    print(f'- {label}: PID={pid} {"ALIVE" if alive else "DEAD"}')
PYEOF
} >> "$SUMMARY"

echo "Audit sweep complete: $SUMMARY"
