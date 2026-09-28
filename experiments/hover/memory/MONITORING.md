# Phase B Monitoring — hover/memory (PR #161)

## System Status (2026-04-03 15:08 UTC)

### Running Processes

| Process | PID | Status | Started |
|---------|-----|--------|---------|
| ideas_tracker | 1088683 | ✅ Running | 14:45 UTC |
| Phase B monitor | 1092493 | ✅ Running | 15:03 UTC |
| Watchdog | (not yet) | ⏳ Staged | after Phase B |

### Ideas Tracker Progress

- **Progress**: 54/273 ideas (19.8%)
- **Elapsed**: ~6m 50s
- **ETA**: ~35m remaining (completion expected ~15:45-15:50 UTC)
- **Log**: `experiments/hover/memory/logs/ideas_tracker_final.log`

### Automation

The Phase B monitor process (PID 1092493) is running in the background and will:

1. Wait for ideas_tracker (PID 1088683) to complete
2. Verify memory_bank/ has JSON files
3. Auto-launch Phase B (4 runs: R1-R4)
4. Start watchdog

**Monitor log**: `experiments/hover/memory/logs/phase_b_monitor.log`

Tail it to watch progress:
```bash
cd /mnt/virtual-...-gigaevo-core-internal
tail -f experiments/hover/memory/logs/phase_b_monitor.log
```

## Manual Commands

### Check Ideas Tracker Progress

```bash
# Last 3 lines of log
tail -3 experiments/hover/memory/logs/ideas_tracker_final.log

# Monitor live (refresh every 10s)
watch -n 10 'tail -1 experiments/hover/memory/logs/ideas_tracker_final.log | sed "s/.*|//"'
```

### Check Phase B Monitor Status

```bash
# Is it running?
ps aux | grep wait_and_launch_phase_b.sh | grep -v grep

# Check log
tail -20 experiments/hover/memory/logs/phase_b_monitor.log
```

### After Phase B Launches

#### Check all 4 runs alive
```bash
gigaevo -e hover/memory status
```

#### Check watchdog
```bash
gigaevo -e hover/memory status  # includes watchdog PID liveness
tail -20 experiments/hover/memory/logs/watchdog.log
```

#### Monitor fitness curve
```bash
gigaevo -r chains/hover/full7_no_deep@4:R1 trajectory
gigaevo -r chains/hover/full7_no_deep@5:R2 trajectory
gigaevo -r chains/hover/full7_no_deep@6:R3 trajectory
gigaevo -r chains/hover/full7_no_deep@7:R4 trajectory
```

## Optional: Set Up Cron Monitoring

To auto-monitor and restart watchdog if it dies, add to crontab:

```bash
crontab -e

# Add this line:
*/10 * * * * cd /mnt/virtual-...-gigaevo-core-internal && bash experiments/hover/memory/cron_monitor_health.sh
```

This runs every 10 minutes and:
- Logs Phase B monitor and watchdog status
- Auto-restarts watchdog if it dies
- Alerts if Phase B monitor dies unexpectedly

Check the health log:
```bash
tail -50 experiments/hover/memory/logs/cron_health.log
```

## Key Files

| File | Purpose |
|------|---------|
| `launch_phase_b.sh` | Manual Phase B launcher (used by auto-monitor) |
| `wait_and_launch_phase_b.sh` | Auto-monitor for ideas_tracker → Phase B transition |
| `run_watchdog.py` | Watchdog: posts hourly status to PR #161 |
| `cron_monitor_health.sh` | Cron job: monitor process health, auto-restart watchdog |
| `run_test_eval.sh` | Test evaluation (run before archiving) |
| `04_issues_log.md` | Issue tracking for this experiment |

## Safety Checks

- [x] All tests pass (680/680)
- [x] Lint clean
- [x] Ideas tracker running
- [x] Phase B monitor running
- [ ] Memory bank has files (pending ideas_tracker completion)
- [ ] Phase B launched
- [ ] All 4 runs alive
- [ ] Watchdog posting to PR
