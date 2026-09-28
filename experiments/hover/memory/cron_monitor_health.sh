#!/usr/bin/env bash
# Cron health check: monitor Phase B monitor and watchdog processes.
# Run every 10 minutes via cron (during active experiment phase).
#
# Usage in crontab:
#   */10 * * * * cd /mnt/virtual-...-gigaevo-core-internal && bash experiments/hover/memory/cron_monitor_health.sh

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
LOG_DIR="$PROJ/experiments/hover/memory/logs"
HEALTH_LOG="$LOG_DIR/cron_health.log"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] $1" >> "$HEALTH_LOG"
}

# Check Phase B monitor alive
MONITOR_PID=$(pgrep -f "wait_and_launch_phase_b.sh" | head -1)
if [ -z "$MONITOR_PID" ]; then
    PHASE_B_STATUS="DEAD"
else
    if kill -0 "$MONITOR_PID" 2>/dev/null; then
        PHASE_B_STATUS="ALIVE"
    else
        PHASE_B_STATUS="DEAD"
    fi
fi

# Check watchdog alive
WATCHDOG_PID=$(pgrep -f "run_watchdog.py" | head -1)
if [ -z "$WATCHDOG_PID" ]; then
    WATCHDOG_STATUS="NOT_STARTED"
else
    if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
        WATCHDOG_STATUS="ALIVE"
    else
        WATCHDOG_STATUS="DEAD"
    fi
fi

# Log status
log "Phase B monitor: $PHASE_B_STATUS (PID=$MONITOR_PID), Watchdog: $WATCHDOG_STATUS (PID=$WATCHDOG_PID)"

# Alert if Phase B monitor dies (before watchdog should start)
if [ "$PHASE_B_STATUS" = "DEAD" ] && [ "$WATCHDOG_STATUS" != "ALIVE" ]; then
    log "WARNING: Phase B monitor died before watchdog started. Check phase_b_monitor.log"
fi

# Restart watchdog if it dies but Phase B is running
if [ "$PHASE_B_STATUS" = "ALIVE" ] && [ "$WATCHDOG_STATUS" = "DEAD" ]; then
    log "ALERT: Watchdog died. Restarting..."
    cd "$PROJ"
    nohup /home/jovyan/.mlspace/envs/evo/bin/python3 experiments/hover/memory/run_watchdog.py \
        > "$LOG_DIR/watchdog.log" 2>&1 &
    NEW_PID=$!
    log "Watchdog restarted: new PID=$NEW_PID"
fi
