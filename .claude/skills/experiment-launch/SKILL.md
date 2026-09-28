---
name: experiment-launch
description: Launch an implemented experiment. Captures reproducibility artifacts, runs `gigaevo launch`, starts crons, and commits. Triggers on "launch experiment" or dispatched by /run-experiment when status is implemented.
argument-hint: <task/name>
model: opus
---

# Experiment Launch: $ARGUMENTS

Launch an implemented experiment after reproducibility capture and researcher confirmation.

The core launch sequence (preflight, DB claims, exec, PID verify, status transition, watchdog) is handled by a single command: `gigaevo -e $EXP launch`. This skill handles the surrounding human gates, reproducibility artifacts, and cron scheduling.

## Step 1 — Gate check and read CONTEXT.md

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest gate implemented
```

Read `experiments/<task>/CONTEXT.md` — verify server IPs are current and infrastructure hasn't changed.

## Step 2 — Config dump (--cfg job)

**Skip this step on re-launch** (if cfg_run_*.txt files already exist and code hasn't changed).

For 2+ runs: use `superpowers:dispatching-parallel-agents` — each run's config dump is independent.

For every run, dump the resolved config:
```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
cd "$PROJ"
# For each run, run: python run.py [overrides] --cfg job > experiments/$EXP/cfg_run_<label>.txt
# Review output to verify all parameters are correct
```

Pause and ask the researcher to confirm the config looks correct.

## Step 3 — Capture server model identity + environment

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
# Get unique server URLs from manifest runs
URLS=$(gigaevo -e "$EXP" manifest get runs --format json | \
  $GIGAEVO_PYTHON -c "import sys,json; runs=json.load(sys.stdin); urls=set(); [urls.update([r.get('chain_url',''),r.get('mutation_url','')]) for r in runs]; print('\n'.join(u for u in sorted(urls) if u))")
API_KEY=$(gigaevo -e "$EXP" manifest get custom_env.OPENAI_API_KEY 2>/dev/null || echo "None")
for url in $URLS; do
  curl -s -H "Authorization: Bearer $API_KEY" "$url/models" | \
    $GIGAEVO_PYTHON -c "import sys,json; data=json.load(sys.stdin); print(f'$url: {[d[\"id\"] for d in data.get(\"data\",[])]}')" 2>/dev/null || echo "$url: ERROR"
done | tee "$PROJ/experiments/$EXP/server_models_at_launch.txt"

$GIGAEVO_PYTHON -m pip freeze > "$PROJ/experiments/$EXP/environment_freeze.txt"
echo "Environment freeze + server models captured"
```

## Step 4 — Commit pre-launch reproducibility artifacts

Commit BEFORE launching — makes artifacts immutable and timestamped in git.

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
cd "$PROJ"
rtk git add \
    "experiments/$EXP/environment_freeze.txt" \
    "experiments/$EXP/server_models_at_launch.txt" \
    "experiments/$EXP/cfg_run_"*.txt 2>/dev/null || true
rtk git commit -m "prelaunch: $EXP — environment + config snapshot before first run

Committed before launch to ensure reproducibility artifacts are immutable.
environment_freeze.txt, server_models_at_launch.txt, cfg_run_*.txt"
```

## Step 5 — Regenerate LAUNCH_PREVIEW.md and researcher confirms launch

`gigaevo launch` writes `LAUNCH_PREVIEW.md` automatically after preflight passes — the file on disk reflects the current manifest + Hydra config, not whatever was committed during `/experiment-implement`. Regenerate once and ask the researcher to inspect it:

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" launch --dry-run
```

**Gate 2 — researcher reads `experiments/$EXP/LAUNCH_PREVIEW.md` and confirms:**
1. Status line is `PASS` with `0 failed` pin assertions.
2. Every pinned row shows `PASS ✓` in every run's table.
3. Non-pinned rows look right — no surprising defaults, no stale overrides.
4. Hydra Default Fingerprint table matches the files they expect to be touched.

If the preview looks wrong (unexpected values, pin failures, new files in fingerprint that weren't there at implement time): DO NOT proceed. Either fix the manifest or abort and re-implement.

Ask: "Config dumps, server models captured, and `LAUNCH_PREVIEW.md` regenerated and reviewed. Ready to launch $EXP? Type 'yes' to proceed."

Do NOT proceed without explicit confirmation. This is a human gate (D-04).

## Step 6 — Launch (single command)

This one command handles: preflight, DB claims, launch.sh generation + exec, PID verification + recording, status → running, watchdog spawn.

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" launch
```

On failure, the command prints the error and rolls back DB claims. Fix the issue and re-run.

For re-launches where preflight already passed:
```bash
gigaevo -e "$EXP" launch --skip-preflight
```

Log the launch event:

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
LOG="$PROJ/experiments/$EXP/04_issues_log.md"
[ ! -f "$LOG" ] && cp "$PROJ/experiments/_template/04_issues_log.md" "$LOG"

cat >> "$LOG" << ENTRY

### [EVENT $(date -u +%Y-%m-%dT%H:%M:%SZ)] -- Experiment launched

- **When**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- **What**: gigaevo launch completed for $EXP. Status: running.
- **Category**: launch
- **Impact**: Automated capture.
ENTRY
```

## Step 7 — Start anomaly detector cron

Use `CronCreate` to schedule the `anomaly-detector` agent:
- **Schedule**: every 2 hours
- **Expiry**: 7 days
- **Prompt**: `Run anomaly detection for experiment $EXP. Read .claude/agents/anomaly-detector.md for full instructions. The experiment name is: $EXP`

Record the returned cron ID:

```bash
EXP='$ARGUMENTS'
CRON_ID='REPLACE_WITH_ACTUAL_CRON_ID'   # set from CronCreate output
gigaevo -e "$EXP" manifest update control_plane.anomaly_detector_cron_id "$CRON_ID"
```

## Step 8 — Start checkpoint cron

Use `CronCreate` to schedule the `experiment-checkpoint` skill:
- **Schedule**: every 4 hours
- **Expiry**: 14 days
- **Prompt**: `Run a checkpoint for experiment $EXP. Invoke the experiment-checkpoint skill with argument: $EXP`

Record the returned cron ID:

```bash
EXP='$ARGUMENTS'
CHECKPOINT_CRON_ID='REPLACE_WITH_ACTUAL_CRON_ID'   # set from CronCreate output
gigaevo -e "$EXP" manifest update control_plane.checkpoint_cron_id "$CHECKPOINT_CRON_ID"
```

## Step 9 — Generate and update PR description

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest pr-description --push
```

## Step 10 — Commit launch artifacts

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
cd "$PROJ"
rtk git add "experiments/$EXP/experiment.yaml" \
       "experiments/$EXP/launch.sh" \
       "experiments/$EXP/04_issues_log.md" \
       "experiments/$EXP/PR_DESCRIPTION.md"
rtk git commit -m "launch: $EXP — runs started, status=running

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

## Step 11 — Completion check

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest gate running
gigaevo -e "$EXP" manifest get lifecycle.launch.time
gigaevo -e "$EXP" manifest get lifecycle.launch.commit
gigaevo -e "$EXP" manifest get runs --format json | $GIGAEVO_PYTHON -c "
import sys, json
runs = json.load(sys.stdin)
for r in runs:
    pid = r.get('PID') or r.get('pid')
    label = r.get('Label') or r.get('label')
    assert pid and str(pid) != '-', f'INCOMPLETE: {label} has no PID'
print(f'All {len(runs)} runs launched.')
print('COMPLETE: experiment-launch finished successfully')
"
```

## Gotchas

- **Issues log** — If anything goes wrong, log to `experiments/$EXP/04_issues_log.md`. Create from `experiments/_template/04_issues_log.md` if missing.
- **Researcher must confirm** before launching (Step 5) — don't auto-launch.
- **Re-launch**: Use `/experiment-restart` first to kill runs, flush DBs, and reset status. Then this skill runs cleanly.
- **Config dump skip**: On re-launch, if `cfg_run_*.txt` files exist and code hasn't changed, skip Step 2.
- **Both crons must be recorded** — anomaly_detector_cron_id and checkpoint_cron_id. If either is missing, re-create it.
- **Dry run available**: `gigaevo -e $EXP launch --dry-run` validates preflight and claims DBs without starting anything.
