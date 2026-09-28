#!/usr/bin/env bash
# Sequential independent replicates of final python_patch + expert on + Memory Cards.
# rN starts only after r(N-1) reaches max_mutants (or is skipped if already done).
# A live in-progress replicate is waited out, not relaunched.
#
# Usage:
#   ./scripts/launch_pmhctcr_final_terra_expert_on_memory_replicates.sh
#   NUM_REPLICATES=5 MAX_MUTANTS=100 ./scripts/launch_pmhctcr_final_terra_expert_on_memory_replicates.sh

set -euo pipefail

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
MAX_MUTANTS="${MAX_MUTANTS:-100}"
NUM_REPLICATES="${NUM_REPLICATES:-5}"
RUN_PREFIX="${RUN_PREFIX:-pmhctcr_final_terra_expert_on_memory}"
STORAGE_PREFIX="pmhctcr_final_mem"
INNER="$REPO/scripts/launch_pmhctcr_final_terra_expert_on_memory.sh"

run_name_for() {
  echo "${RUN_PREFIX}_m${MAX_MUTANTS}_r${1}"
}

run_is_complete() {
  local rs="$REPO/outputs/$1/storage/${STORAGE_PREFIX}/run_state.json"
  python3 - "$rs" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.is_file():
    raise SystemExit(1)
snap = json.loads(json.loads(p.read_text()).get("engine:snapshot", "{}"))
raise SystemExit(0 if snap.get("completion_reason") == "max_mutants_reached" else 1)
PY
}

lock_pid() {
  local lock="$REPO/outputs/$1/storage/${STORAGE_PREFIX}/instance.lock"
  if [[ -f "$lock" ]]; then
    tr -d '[:space:]' <"$lock" || true
  fi
}

wait_if_in_progress() {
  local run_name="$1"
  local pid
  while true; do
    pid="$(lock_pid "$run_name")"
    if [[ -z "${pid:-}" ]]; then
      return 0
    fi
    if kill -0 "$pid" 2>/dev/null; then
      echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] wait $run_name (live pid=$pid)"
      sleep 60
    else
      echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] stale lock on $run_name (pid=$pid); continuing"
      return 0
    fi
  done
}

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] sequential memory chain: ${NUM_REPLICATES} x m${MAX_MUTANTS}"
echo "runs:"
for ((rep = 1; rep <= NUM_REPLICATES; rep++)); do
  echo "  outputs/$(run_name_for "$rep")"
done

cd "$REPO"
for ((rep = 1; rep <= NUM_REPLICATES; rep++)); do
  run_name="$(run_name_for "$rep")"
  wait_if_in_progress "$run_name"
  if run_is_complete "$run_name"; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] skip $run_name (max_mutants_reached)"
    continue
  fi
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] launch $run_name"
  MAX_MUTANTS="$MAX_MUTANTS" RUN_NAME="$run_name" "$INNER"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] DONE  $run_name"
done

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] sequential memory chain finished"
