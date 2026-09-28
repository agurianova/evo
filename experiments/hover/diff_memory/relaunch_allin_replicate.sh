#!/usr/bin/env bash
# Night-queue replicate (user directive 2026-07-12): when the ALL-IN pair
# finishes CLEANLY overnight, launch one identical pair (fresh TS) + its
# watchdog for a second replicate (statistical power). A gate abort cancels
# the queue — aborted pairs need diagnosis, not replication.
#   setsid ./relaunch_allin_replicate.sh >> logs/relaunch_replicate_$TS.log 2>&1 &
set -uo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
PYTHON="${GIGAEVO_PYTHON:-/home/jovyan/.mlspace/envs/evo/bin/python3}"
EXP_DIR="$PROJ/experiments/hover/diff_memory"

# Pair-1 identity is frozen HERE — the next launch rewrites latest_allin.env.
# shellcheck disable=SC1090
source "$EXP_DIR/latest_allin.env"
WAIT_TS="$TS"
WAIT_ROOT="$RUN_ROOT"
MEM_PID=$(awk '$1=="MEM_R1"{print $2}' "$PIDS_FILE")
NOMEM_PID=$(awk '$1=="NOMEM_R1"{print $2}' "$PIDS_FILE")
WD_LOG="$EXP_DIR/logs/watchdog_allin_${WAIT_TS}.log"

export HTTPS_PROXY="${HTTPS_PROXY:-$(grep -m1 '^SQUID_PROXY=' "$PROJ/.env" | cut -d= -f2-)}"

tg() {
  cd "$PROJ" && "$PYTHON" -c '
import sys
from tools.telegram_notify import notify
notify(sys.stdin.read(), parse_mode=None)
' <<< "$1"
}

echo "replicate-queue: waiting on TS=$WAIT_TS MEM=$MEM_PID NOMEM=$NOMEM_PID"

while kill -0 "$MEM_PID" 2>/dev/null || kill -0 "$NOMEM_PID" 2>/dev/null; do
  sleep 300
done
# Let the pair-1 watchdog send its final sweep (it re-reads latest_allin.env,
# which the next launch overwrites) before touching anything.
while [ -n "$(lsof -t "$WD_LOG" 2>/dev/null)" ]; do
  sleep 60
done

if [ ! -d "$WAIT_ROOT" ] || ls -d "${WAIT_ROOT}"_aborted_* >/dev/null 2>&1; then
  tg "🌙 Replicate queue CANCELLED: pair TS=$WAIT_TS did not finish cleanly (run root aborted/renamed). No second pair launched — diagnose first."
  exit 1
fi

cd "$EXP_DIR"
# Blank inherited pair-1 values so the launcher derives a fresh TS/paths.
if ! TS="" RUN_ROOT="" MEM_R1_MEMORY_BANK="" ./launch_bd3d_noise_allin.sh \
    > "logs/launch_replicate_after_${WAIT_TS}.log" 2>&1; then
  tg "🌙 Replicate queue FAILED to launch the second pair — see logs/launch_replicate_after_${WAIT_TS}.log. First pair's artifacts are untouched."
  exit 1
fi
# shellcheck disable=SC1090
source "$EXP_DIR/latest_allin.env"
setsid ./watchdog_allin.sh >> "logs/watchdog_allin_${TS}.log" 2>&1 &

tg "🌙 Replicate pair LAUNCHED (TS=$TS) after clean finish of TS=$WAIT_TS — second MEM+NOMEM pair for statistical power. Same launcher, prereg bars, and watchdog schedule (1h hard gate, 3h/6h sweeps, run-end sweep). Closeout pools winners from both pairs for the A1 K=5 re-eval verdict."
echo "replicate-queue: launched TS=$TS; done at $(date '+%F %T')"
