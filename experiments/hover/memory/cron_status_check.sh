#!/usr/bin/env bash
# 15-minute status check — logs run progress and alerts on dead processes.
# Add to crontab: */15 * * * * bash /path/to/cron_status_check.sh
set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"
LOG="$PROJ/experiments/hover/memory/logs/status_checks.log"

TS="$(date -u '+%Y-%m-%d %H:%M UTC')"
echo "========== $TS ==========" >> "$LOG"

# Run status via gigaevo CLI (PIDs/watchdog come from experiment.yaml manifest).
cd "$PROJ"
gigaevo \
    -r chains/hover/full7_no_deep@4:R1 \
    -r chains/hover/full7_no_deep@5:R2 \
    -r chains/hover/full7_no_deep@6:R3 \
    -r chains/hover/full7_no_deep@7:R4 \
    status >> "$LOG" 2>&1

# Alert if any run is dead
for label_pid in R1:1095864 R2:1095865 R3:1095866 R4:1095867 WD:1104178; do
    label="${label_pid%%:*}"
    pid="${label_pid##*:}"
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "ALERT: $label (PID $pid) is DEAD at $TS" >> "$LOG"
    fi
done
echo "" >> "$LOG"
