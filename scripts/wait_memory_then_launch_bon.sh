#!/usr/bin/env bash
# Wait until final_terra_expert_on_memory r1–r5 all reach max_mutants, then
# start 5 sequential independent best-of-N runs (no evolution engine).
# If memory r5 never appears after r4 finishes, start r5 ourselves so BoN
# is not blocked by a dead memory supervisor.

set -euo pipefail

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
MAX_MUTANTS="${MAX_MUTANTS:-100}"
NUM_REPLICATES="${NUM_REPLICATES:-5}"
MEM_PREFIX="${MEM_PREFIX:-pmhctcr_final_terra_expert_on_memory}"
MEM_STORAGE="pmhctcr_final_mem"
MEM_INNER="$REPO/scripts/launch_pmhctcr_final_terra_expert_on_memory.sh"
BON="$REPO/scripts/launch_pmhctcr_final_terra_expert_on_bon_replicates.sh"
POLL_S="${POLL_S:-60}"
R5_GRACE_S="${R5_GRACE_S:-180}"

mem_name() {
  echo "${MEM_PREFIX}_m${MAX_MUTANTS}_r${1}"
}

mem_complete() {
  local rs="$REPO/outputs/$1/storage/${MEM_STORAGE}/run_state.json"
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

mem_lock_pid() {
  local lock="$REPO/outputs/$1/storage/${MEM_STORAGE}/instance.lock"
  if [[ -f "$lock" ]]; then
    tr -d '[:space:]' <"$lock" || true
  fi
}

all_memory_complete() {
  local rep
  for ((rep = 1; rep <= NUM_REPLICATES; rep++)); do
    mem_complete "$(mem_name "$rep")" || return 1
  done
  return 0
}

LOCK="$REPO/outputs/_bon_waiter.lock"
mkdir -p "$REPO/outputs"
if [[ -f "$LOCK" ]]; then
  old_pid="$(tr -d '[:space:]' <"$LOCK" || true)"
  if [[ -n "${old_pid:-}" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "waiter already running (pid=$old_pid)" >&2
    exit 0
  fi
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] stale waiter lock pid=${old_pid:-none}"
fi
echo "$$" >"$LOCK"
trap 'rm -f "$LOCK"' EXIT

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] waiter: hold independent BoN until memory r1–r${NUM_REPLICATES} finish"

r5_nudge_sent=0
while true; do
  if all_memory_complete; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] waiter: memory r1–r${NUM_REPLICATES} complete"
    break
  fi

  # Safety: r4 done, r5 never started (dead supervisor) → launch r5.
  if mem_complete "$(mem_name 4)" && ! mem_complete "$(mem_name 5)"; then
    r5="$(mem_name 5)"
    r5_pid="$(mem_lock_pid "$r5")"
    if [[ ! -d "$REPO/outputs/$r5" && -z "${r5_pid:-}" && "$r5_nudge_sent" -eq 0 ]]; then
      echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] waiter: r4 done, r5 missing; grace ${R5_GRACE_S}s"
      sleep "$R5_GRACE_S"
      r5_pid="$(mem_lock_pid "$r5")"
      if [[ ! -d "$REPO/outputs/$r5" && -z "${r5_pid:-}" ]]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] waiter: launching missing memory $r5"
        r5_nudge_sent=1
        MAX_MUTANTS="$MAX_MUTANTS" RUN_NAME="$r5" "$MEM_INNER" &
      fi
    fi
  fi

  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] waiter: memory still running; sleep ${POLL_S}s"
  sleep "$POLL_S"
done

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] waiter: launching independent BoN r1–r${NUM_REPLICATES}"
MAX_MUTANTS="$MAX_MUTANTS" NUM_REPLICATES="$NUM_REPLICATES" "$BON"
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] waiter: independent BoN chain finished"
