#!/usr/bin/env bash
# Wait for the terra expert ablation supervisor to finish, then launch the
# matching luna ablation (same design: 2 parallel chains x 3 sequential m100).
#
# Usage:
#   ./scripts/launch_pmhctcr_final_luna_after_terra.sh
#   setsid bash ./scripts/launch_pmhctcr_final_luna_after_terra.sh \
#     >> outputs/_final_luna_after_terra_waiter.log 2>&1 &

set -euo pipefail

REPO="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
TERRA_PID_FILE="$REPO/outputs/_final_terra_expert_ablation_supervisor.pid"
WAIT_LOG="$REPO/outputs/_final_luna_after_terra_waiter.log"
LUNA_LOG="$REPO/outputs/_final_luna_expert_ablation_supervisor.log"

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$WAIT_LOG"
}

log "waiter start: will launch luna ablation after terra finishes"

if [[ -f "$TERRA_PID_FILE" ]]; then
  terra_pid="$(cat "$TERRA_PID_FILE")"
  log "waiting for terra supervisor pid=$terra_pid"
  while kill -0 "$terra_pid" 2>/dev/null; do
    sleep 60
  done
  log "terra supervisor pid=$terra_pid exited"
else
  log "no terra supervisor pid file; polling chain logs instead"
  while true; do
    on_done=false
    off_done=false
    if [[ -f "$REPO/outputs/pmhctcr_final_terra_expert_on_chain.log" ]] \
      && grep -q "chain done label=expert_on" "$REPO/outputs/pmhctcr_final_terra_expert_on_chain.log"; then
      on_done=true
    fi
    if [[ -f "$REPO/outputs/pmhctcr_final_terra_expert_off_chain.log" ]] \
      && grep -q "chain done label=expert_off" "$REPO/outputs/pmhctcr_final_terra_expert_off_chain.log"; then
      off_done=true
    fi
    if [[ "$on_done" == true && "$off_done" == true ]]; then
      log "both terra chains report done"
      break
    fi
    sleep 60
  done
fi

log "starting luna expert ablation"
exec "$REPO/scripts/launch_pmhctcr_final_luna_expert_ablation.sh" >>"$LUNA_LOG" 2>&1
