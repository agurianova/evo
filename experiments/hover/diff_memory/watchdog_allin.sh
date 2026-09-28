#!/usr/bin/env bash
# Watchdog for the ALL-IN pair (prereg_bd3d_noise_allin_20260711.md).
# Schedule: T+1h HARD GATE (auto-abort per prereg), T+3h and T+6h study
# sweeps (informational), then run-end final sweep. Every checkpoint goes to
# Telegram. Start detached right after launch:
#   setsid ./watchdog_allin.sh >> logs/watchdog_allin_$TS.log 2>&1 &

set -uo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PYTHON="${GIGAEVO_PYTHON:-/home/jovyan/.mlspace/envs/evo/bin/python3}"
EXP_DIR="$PROJ/experiments/hover/diff_memory"
ENV_FILE="$EXP_DIR/latest_allin.env"

# shellcheck disable=SC1090
source "$ENV_FILE"

export HTTPS_PROXY="${HTTPS_PROXY:-$(grep -m1 '^SQUID_PROXY=' "$PROJ/.env" | cut -d= -f2-)}"

tg() {
  cd "$PROJ" && "$PYTHON" -c '
import sys
from tools.telegram_notify import notify
notify(sys.stdin.read(), parse_mode=None)
' <<< "$1"
}

run_checks() {
  cd "$PROJ" && "$PYTHON" "$EXP_DIR/check_allin_progress.py" --env "$ENV_FILE" "$@" 2>&1
}

alive() { kill -0 "$1" 2>/dev/null; }

MEM_PID=$(awk '$1=="MEM_R1"{print $2}' "$PIDS_FILE")
NOMEM_PID=$(awk '$1=="NOMEM_R1"{print $2}' "$PIDS_FILE")
MEM_OUT=$(awk '$1=="MEM_R1"{print $4}' "$PIDS_FILE")
NOMEM_OUT=$(awk '$1=="NOMEM_R1"{print $4}' "$PIDS_FILE")

echo "watchdog: TS=$TS MEM=$MEM_PID NOMEM=$NOMEM_PID"

abort_all() {
  local when="$1" detail="$2"
  kill -9 -- "-$MEM_PID" "-$NOMEM_PID" 2>/dev/null
  sleep 10
  mv "$RUN_ROOT" "${RUN_ROOT}_aborted_${when}" 2>/dev/null
  tg "🛑 ALL-IN pair ABORTED at the preregistered ${when} hard gate (TS=$TS).

Both runs killed; artifacts moved to ${RUN_ROOT}_aborted_${when}.

$detail

Next: diagnose on the aborted artifacts before any relaunch."
  exit 1
}

# --- T+1h HARD GATE (preregistered auto-abort) ---
sleep 3600
GATE_OUT=$(run_checks --hard-gate)
GATE_RC=$?
echo "$GATE_OUT"
if [[ $GATE_RC -ne 0 ]]; then
  abort_all "1hgate" "$GATE_OUT"
fi
tg "✅ ALL-IN pair passed the 1h hard gate (TS=$TS). Occupancy, transport, crediting activity, arm purity all within prereg bars.

$GATE_OUT"

# Prereg: T5-W is only required once >=3 valid card-injected children exist;
# a WARN at 1h (too few children) triggers a re-check at 2h before aborting.
T5W_RECHECK=0
# Checker prints "[WARN] T5-W ..." — status BEFORE the check id.
if grep -q "\[WARN\] T5-W" <<< "$GATE_OUT"; then
  T5W_RECHECK=1
  sleep 3600
  GATE2_OUT=$(run_checks --hard-gate)
  GATE2_RC=$?
  echo "$GATE2_OUT"
  if [[ $GATE2_RC -ne 0 ]]; then
    abort_all "2hgate" "$GATE2_OUT"
  fi
  tg "✅ ALL-IN 2h T5-W re-check passed (TS=$TS).

$GATE2_OUT"
fi

# --- T+3h and T+6h study sweeps (informational) ---
FIRST_DELAY=$(( T5W_RECHECK == 1 ? 3600 : 7200 ))
hours=3
for delay in "$FIRST_DELAY" 10800; do
  sleep "$delay"
  if ! alive "$MEM_PID" && ! alive "$NOMEM_PID"; then
    break
  fi
  SWEEP_OUT=$(run_checks)
  echo "$SWEEP_OUT"
  tg "🔎 ALL-IN T+${hours}h study sweep (TS=$TS) — FAILs here are flags for investigation, not auto-abort.

$SWEEP_OUT"
  hours=6
done

# --- run end ---
while alive "$MEM_PID" || alive "$NOMEM_PID"; do
  sleep 300
done
sleep 60  # final writer sweep + log flush

FINAL_OUT=$(run_checks)
TOP_OUT=$(cd "$PROJ" && gigaevo -r "$MEM_OUT/storage:MEM_R1" top -n 3 2>&1; gigaevo -r "$NOMEM_OUT/storage:NOMEM_R1" top -n 3 2>&1)

echo "$FINAL_OUT"
echo "$TOP_OUT"
tg "🏁 ALL-IN pair finished (TS=$TS). Final treatment sweep + in-run best below. In-run bests are single-eval (sigma~0.008) — the acceptance verdict (A1: top-1 vs MEM_R1 .8298 + NOV_R2 .8291, paired K=5) comes from the re-eval closeout, which runs next.

$FINAL_OUT

--- in-run top-3 per arm (uncorrected) ---
$TOP_OUT"

echo "watchdog: done at $(date '+%F %T')"
