#!/usr/bin/env bash
# Monitor ideas_tracker completion and auto-launch Phase B.
#
# Usage: nohup bash wait_and_launch_phase_b.sh > phase_b_monitor.log 2>&1 &
#
# This script:
# 1. Waits for ideas_tracker (PID passed or auto-detected) to complete
# 2. Verifies memory_bank/ has JSON files
# 3. Launches Phase B (4 runs)
# 4. Starts watchdog
# 5. Logs everything to a monitor file

set -euo pipefail

PROJ="/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal"
MEMORY_BANK="$PROJ/experiments/hover/memory/memory_bank"
LOG_DIR="$PROJ/experiments/hover/memory/logs"
MONITOR_LOG="$LOG_DIR/phase_b_monitor.log"

export GIGAEVO_PYTHON="/home/jovyan/.mlspace/envs/evo/bin/python3"

log() {
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $1" | tee -a "$MONITOR_LOG"
}

log "=== Phase B Auto-Launch Monitor ==="

# Find ideas_tracker PID (from monitor process or live grep)
IT_PID=${1:-$(pgrep -f 'ideas_tracker.cli' | head -1)}
if [ -z "$IT_PID" ]; then
    log "ERROR: ideas_tracker PID not found. Pass as argument or ensure it's running."
    exit 1
fi
log "Monitoring ideas_tracker PID: $IT_PID"

# Wait for completion (max 90 min)
MAX_WAIT=90
POLL_INTERVAL=30
ELAPSED=0

while [ $ELAPSED -lt $((MAX_WAIT * 60)) ]; do
    if ! kill -0 "$IT_PID" 2>/dev/null; then
        log "Ideas tracker completed"
        break
    fi

    # Show progress every 10 iterations (5 min)
    if [ $((ELAPSED % 300)) -eq 0 ]; then
        PROGRESS=$(tail -1 "$LOG_DIR/ideas_tracker_final.log" 2>/dev/null | sed 's/.*|//' || echo "?")
        log "Still running... Progress: $PROGRESS"
    fi

    sleep "$POLL_INTERVAL"
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

if kill -0 "$IT_PID" 2>/dev/null; then
    log "ERROR: Timeout waiting for ideas_tracker (max $MAX_WAIT min). Check logs."
    exit 1
fi

log "Waiting 5s for file I/O to settle..."
sleep 5

# Verify memory bank has files
CARD_COUNT=$(find "$MEMORY_BANK" -name "*.json" -type f 2>/dev/null | wc -l)
if [ "$CARD_COUNT" -eq 0 ]; then
    log "ERROR: memory_bank has no JSON files. Ideas_tracker may have failed silently."
    echo "Last 30 lines of log:"
    tail -30 "$LOG_DIR/ideas_tracker_final.log" 2>/dev/null | tee -a "$MONITOR_LOG"
    exit 1
fi
log "Memory bank verified: $CARD_COUNT JSON files found"
ls -lh "$MEMORY_BANK"/*.json 2>/dev/null | head -5 | tee -a "$MONITOR_LOG"

# Launch Phase B
log "Launching Phase B (4 runs)..."
cd "$PROJ"
bash experiments/hover/memory/launch_phase_b.sh 2>&1 | tee -a "$MONITOR_LOG"

# Extract PIDs from phase_b.txt
PIDS_FILE="$LOG_DIR/pids_phase_b.txt"
if [ ! -f "$PIDS_FILE" ]; then
    log "ERROR: Phase B launch failed (pids_phase_b.txt not created)"
    exit 1
fi
read -r PID_R1 PID_R2 PID_R3 PID_R4 < "$PIDS_FILE"
log "Phase B launched: R1=$PID_R1, R2=$PID_R2, R3=$PID_R3, R4=$PID_R4"

# Start watchdog
log "Starting watchdog..."
nohup "$GIGAEVO_PYTHON" experiments/hover/memory/run_watchdog.py \
    > "$LOG_DIR/watchdog.log" 2>&1 &
WATCHDOG_PID=$!
log "Watchdog started: PID=$WATCHDOG_PID"

# Verify watchdog alive after 10s
sleep 10
if kill -0 "$WATCHDOG_PID" 2>/dev/null; then
    log "Watchdog verified alive"
else
    log "WARNING: Watchdog died. Check $LOG_DIR/watchdog.log"
fi

log "=== Phase B Complete ==="
log "Monitor runs: PYTHONPATH=$PROJ $GIGAEVO_PYTHON $PROJ/tools/status.py --experiment hover/memory"
