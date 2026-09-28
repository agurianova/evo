---
name: experiment-restart
description: Restart a running experiment. Kills all run processes, flushes Redis DBs, resets status to implemented, then dispatches /experiment-launch. Use when code fixes require a fresh start. Triggers on "restart experiment", "re-launch experiment", or when a running experiment needs to start over.
argument-hint: <task/name>
model: opus
---

# Experiment Restart: $ARGUMENTS

Kill running processes, flush Redis, reset status, and re-launch with current code.

## Step 0 — Cancel anomaly detector cron (if active)

Before killing processes, cancel the anomaly detector so it doesn't fire on a dead experiment:

```bash
EXP='$ARGUMENTS'
ANOMALY_CRON=$(gigaevo -e "$EXP" manifest get control_plane.anomaly_detector_cron_id 2>/dev/null)
CHECKPOINT_CRON=$(gigaevo -e "$EXP" manifest get control_plane.checkpoint_cron_id 2>/dev/null)
if [ -n "$ANOMALY_CRON" ] && [ "$ANOMALY_CRON" != "None" ]; then
  echo "Anomaly detector cron ID: $ANOMALY_CRON — cancel with CronDelete"
else
  echo "No anomaly detector cron to cancel"
fi
if [ -n "$CHECKPOINT_CRON" ] && [ "$CHECKPOINT_CRON" != "None" ]; then
  echo "Checkpoint cron ID: $CHECKPOINT_CRON — cancel with CronDelete"
else
  echo "No checkpoint cron to cancel"
fi
```

If any cron IDs are found, use `CronDelete` to cancel **both** before proceeding.

## Step 1 — Gate check: status must be running

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest gate running
gigaevo -e "$EXP" manifest get runs
gigaevo -e "$EXP" manifest get control_plane.watchdog_pid 2>/dev/null || echo "No watchdog PID"
```

## Step 1b — Stopping rule violation check

Before killing anything, assess whether the restart constitutes a protocol deviation:

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
MAX_GEN=$(gigaevo -e "$EXP" manifest get max_generations)
gigaevo -e "$EXP" manifest get runs --format json | $GIGAEVO_PYTHON -c "
import sys, json, redis
runs = json.load(sys.stdin)
max_gen = int('$MAX_GEN' or 0)
for run in runs:
    db = int(run.get('DB') or run.get('db'))
    prefix = run.get('Prefix') or run.get('prefix')
    label = run.get('Label') or run.get('label')
    r = redis.Redis(host='localhost', port=6379, db=db)
    _raw = r.hget(f'{prefix}:run_state', 'engine:snapshot')
    gen = json.loads(_raw)['programs_processed'] if _raw else 0
    pct = gen / max_gen * 100 if max_gen else 0
    frontier = r.lindex(f'{prefix}:metrics:history:program_metrics:valid_frontier_fitness', -1)
    best = json.loads(frontier)['v'] if frontier else 0.0
    print(f'  {label}: gen={gen}/{max_gen} ({pct:.0f}%), best={best:.3f}')

print()
print('RESTART IMPACT ASSESSMENT:')
print('  - All progress above will be PERMANENTLY DESTROYED')
print('  - This constitutes a mid-experiment protocol deviation')
print('  - Must be documented in 04_issues_log.md with:')
print('    * Iterations run under broken treatment')
print('    * Whether any valid programs were produced')
print('    * Whether pre-registration is still intact')
"
```

Surface this to the researcher. They must confirm:
1. How many iterations ran under the broken treatment?
2. Were any valid programs produced? (if yes, the pre-registration may need amendment)
3. Is the fix committed and verified?

## Step 2 — Confirm with researcher

Ask: "About to kill all runs for $ARGUMENTS and flush Redis DBs. This destroys all progress. Restart constitutes a protocol deviation that must be documented. Continue? (yes/no)"

Do NOT proceed without explicit confirmation.

After confirmation, log the restart event:

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
LOG="$PROJ/experiments/$EXP/04_issues_log.md"
[ ! -f "$LOG" ] && cp "$PROJ/experiments/_template/04_issues_log.md" "$LOG"
GEN_INFO=$(gigaevo -e "$EXP" manifest get runs --format json | \
  $GIGAEVO_PYTHON -c "
import sys, json, redis
runs = json.load(sys.stdin)
parts = []
for run in runs:
    db = int(run.get('DB') or run.get('db'))
    prefix = run.get('Prefix') or run.get('prefix')
    label = run.get('Label') or run.get('label')
    r = redis.Redis(host='localhost', port=6379, db=db)
    _raw = r.hget(f'{prefix}:run_state', 'engine:snapshot')
    gen = json.loads(_raw)['programs_processed'] if _raw else 0
    parts.append(f'{label}=gen{gen}')
print(' '.join(parts))
")

cat >> "$LOG" << ENTRY

### [EVENT $(date -u +%Y-%m-%dT%H:%M:%SZ)] -- Experiment restart initiated

- **When**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- **What**: Full experiment restart. Progress at restart: $GEN_INFO
- **Category**: restart
- **Impact**: All run progress destroyed. Redis DBs flushed.
ENTRY
echo "Restart event logged to 04_issues_log.md"
```

## Step 2a — MANDATORY archive (if gen > 0)

Before destroying any data, archive runs that have produced results. This is mandatory for any run with gen > 0.

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
MAX_GEN=$(gigaevo -e "$EXP" manifest get max_generations)
gigaevo -e "$EXP" manifest get runs --format json | $GIGAEVO_PYTHON -c "
import sys, json, redis
runs = json.load(sys.stdin)
max_gen = int('$MAX_GEN' or 0)
runs_to_archive = []
for run in runs:
    db = int(run.get('DB') or run.get('db'))
    prefix = run.get('Prefix') or run.get('prefix')
    label = run.get('Label') or run.get('label')
    r = redis.Redis(host='localhost', port=6379, db=db)
    _raw = r.hget(f'{prefix}:run_state', 'engine:snapshot')
    gen = json.loads(_raw)['programs_processed'] if _raw else 0
    if gen > 0:
        runs_to_archive.append(label)
        pct = gen / max_gen * 100 if max_gen else 0
        print(f'  ARCHIVE REQUIRED: {label} at gen {gen}/{max_gen} ({pct:.0f}%)')
        if pct > 50:
            print(f'  WARNING: {label} is {pct:.0f}% complete — significant compute loss')
    else:
        print(f'  SKIP: {label} at gen 0 (no data)')
if not runs_to_archive:
    print('No runs to archive (all at gen 0)')
else:
    print(f'{len(runs_to_archive)} run(s) need archiving before flush')
"
```

For each run with gen > 0, archive before proceeding:

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
# Run archive_run.sh for each run that has data
# Example: bash tools/experiment/archive_run.sh --exp $EXP --run "prefix@db:label" --upload
```

If archiving fails, do NOT proceed to flush — investigate first.

## Step 3 — Kill all run processes and watchdog

```bash
EXP=''
DBS=$(gigaevo -e "$EXP" manifest get runs --format json | \
  $GIGAEVO_PYTHON -c "import sys,json; print(' '.join(str(r.get('DB') or r.get('db')) for r in json.load(sys.stdin)))")
gigaevo flush --db $DBS --kill-only --confirm
```

## Step 4 — Flush Redis DBs

Read DBs from the manifest and flush in one pass:

```bash
EXP='$ARGUMENTS'
DBS=$(gigaevo -e "$EXP" manifest get runs --format json | \
  $GIGAEVO_PYTHON -c "import sys,json; print(' '.join(str(r.get('DB') or r.get('db')) for r in json.load(sys.stdin)))")
echo "Flushing DBs: $DBS"
gigaevo flush --db $DBS --confirm
```

Log the flush completion:

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
LOG="$PROJ/experiments/$EXP/04_issues_log.md"
cat >> "$LOG" << ENTRY

### [EVENT $(date -u +%Y-%m-%dT%H:%M:%SZ)] -- Redis flush completed

- **When**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- **What**: Redis DBs flushed for $EXP. Status reset to implemented.
- **Category**: restart
- **Impact**: Data destroyed. Ready for re-launch.
ENTRY
```

## Step 5 — Reset experiment.yaml to implemented

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
gigaevo -e "$EXP" manifest update status implemented
# Clear PIDs and launch fields (raw YAML manipulation — allowed per D-01)
$GIGAEVO_PYTHON -c "
import yaml
from pathlib import Path
p = Path('$PROJ/experiments/$EXP/experiment.yaml')
raw = yaml.safe_load(p.read_text())
for run in raw.get('runs', []):
    run['pid'] = None
launch = raw.get('launch', {})
for k in ['watchdog_pid', 'time', 'commit', 'confirmed_at']:
    launch.pop(k, None)
p.write_text(yaml.dump(raw, allow_unicode=True, sort_keys=False))
print('PIDs and launch fields cleared — ready for /experiment-launch')
"
```

## Step 6 — Regenerate launch.sh (if needed)

Only regenerate if `experiment.yaml` runs/config changed:

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" launch --generate-script
```

`--generate-script` writes `experiments/$EXP/launch.sh` (chmod +x) from `experiment.yaml` and exits.

## Step 7 — Dispatch to /experiment-launch

Now that status is `implemented`, dispatch to the launch skill:

```
/experiment-launch $ARGUMENTS
```

This runs preflight, launches, starts watchdog, and sets status to running.

## Gotchas

- **Issues log** — After restart, log the reason for restart and any issues encountered to `experiments/$EXP/04_issues_log.md`. Create from `experiments/_template/04_issues_log.md` if it doesn't exist. Include: what broke, root cause, fix applied, and whether a systemic fix is needed.
- **Always confirm** before killing — progress is destroyed permanently.
- **Keep checkpoint cron loops running** — `/loop` cron jobs for checkpoint/monitor should NOT be cancelled on restart since the experiment continues. Only the watchdog (Step 3) and anomaly detector cron (Step 0) are stopped and relaunched with new IDs via experiment-launch.
- **Flush is safe** for other experiments — `gigaevo flush` only kills workers belonging to the target DBs.
- **Mandatory archiving** — Step 2a archives all runs with gen > 0 before flushing. If archive fails, do NOT proceed to flush.
- **launch.sh regeneration** — only needed if experiment.yaml or launch_generator.py changed. If only application code changed (e.g. mutation agent fix), skip Step 6.
- **Status transition** — uses `update_manifest` direct write (not `set_status`) because `running → implemented` is not in the normal state machine. This is intentional for restart.
