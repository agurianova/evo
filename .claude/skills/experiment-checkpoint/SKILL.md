---
name: experiment-checkpoint
description: Check status and record a checkpoint for a running experiment (Phase 4 Step 7). Reads status, runs analysis, updates PR. Repeatable — can be invoked multiple times or via /loop. Triggers on "checkpoint experiment", "check experiment status", or dispatched by /run-experiment when status is running.
argument-hint: <task/name>
model: opus
---

# Experiment Checkpoint: $ARGUMENTS

Record a status checkpoint for a running experiment.

## Step 0 — Gate check: status must be running

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest gate running
```

## Step 1 — Read context

Read these files for context before proceeding:
- `experiments/$ARGUMENTS/experiment.yaml` — full run details and previous checkpoints
- `experiments/$ARGUMENTS/04_issues_log.md` — recent issues (if exists)
- The task's `CONTEXT.md` for baseline reference values

## Step 2 — Get current status

`gigaevo status -e` auto-discovers all runs, PIDs, watchdog, and metrics from `experiment.yaml` — no manual flag building needed:

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" status
```

This shows iteration progress, all metrics (from `metrics.yaml`), invalidity rate, validator timing, and PID liveness for every run.

## Step 2a — Stopping rule compliance check

Read the pre-registered stopping rule (prefer structured `conditions[]`, fall back to regex on prose) and verify no early-stop condition has been silently triggered:

```bash
EXP='$ARGUMENTS'
MAX_GEN=$(gigaevo -e "$EXP" manifest get max_generations)
$GIGAEVO_PYTHON - "$EXP" "$MAX_GEN" << 'PYEOF'
import sys, json, re, redis
from gigaevo.experiment.manifest import load_manifest

exp, max_gen_str = sys.argv[1], sys.argv[2]
max_gen = int(max_gen_str or 0)
m = load_manifest(exp)
metric_name = (m.contract.problem.metric_name or 'fitness')
frontier_key = f'valid_frontier_{metric_name}'
print(f"Stopping: Hydra stopper (engine-managed, max_generations={max_gen})")
print(f"Metric: {metric_name} (frontier key: {frontier_key})")

invalidity_threshold = None
plateau_threshold = None
plateau_window = None

for run in m.contract.runs:
    db = int(run.db)
    prefix = run.prefix
    label = run.label
    r = redis.Redis(host='localhost', port=6379, db=db)
    _raw = r.hget(f'{prefix}:run_state', 'engine:snapshot')
    gen = json.loads(_raw)['programs_processed'] if _raw else 0
    inv_hist = r.lrange(f'{prefix}:metrics:history:program_metrics:is_valid', -20, -1)
    recent_invalid_rate = 0.0
    if inv_hist:
        vals = [1.0 - json.loads(v)['v'] for v in inv_hist]
        recent_invalid_rate = sum(vals) / len(vals)
    print(f'{label}: gen={gen}/{max_gen}, recent_invalidity={recent_invalid_rate:.1%}')
    if invalidity_threshold is not None and recent_invalid_rate > invalidity_threshold:
        print(f'  WARNING: {label} invalidity {recent_invalid_rate:.1%} exceeds pre-registered stop threshold {invalidity_threshold:.0%}')
        print(f'  ACTION REQUIRED: stopping rule may have been triggered — review before continuing')
    if plateau_threshold is not None and plateau_window is not None and gen >= plateau_window:
        frontier = r.lindex(
            f'{prefix}:metrics:history:program_metrics:{frontier_key}', -1
        )
        if frontier:
            best = json.loads(frontier).get('v', 0.0) or 0.0
            if best < plateau_threshold:
                print(f'  WARNING: {label} at gen {gen} (>= window {plateau_window}) best_fitness={best:.4f} < plateau threshold {plateau_threshold:.4f}')
                print(f'  ACTION REQUIRED: futility condition may have been triggered')
PYEOF
```

If a stopping rule violation was detected above, log it:

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
LOG="$PROJ/experiments/$EXP/04_issues_log.md"
[ ! -f "$LOG" ] && cp "$PROJ/experiments/_template/04_issues_log.md" "$LOG"
# Only append if the check above printed WARNING (manual check by Claude -- append only if stopping rule was triggered)
```

Note: Claude should check the output of the Step 2a script. If any WARNING about stopping rule threshold was printed, append an EVENT entry:

```
### [EVENT <timestamp>] -- Stopping rule threshold exceeded

- **When**: <timestamp>
- **What**: Run <label> invalidity <rate> exceeds pre-registered stop threshold <threshold>
- **Category**: checkpoint
- **Impact**: Stopping rule may have been triggered. Review required.
```

If any run has silently hit an early-stop condition, surface it to the researcher before recording the checkpoint. Do NOT proceed as if everything is normal.

## Step 4 — Run diagnostics

Always run `/experiment-diagnose $ARGUMENTS` here. Diagnose is not just for emergencies — it catches subtle issues (wrong prompts loaded, asymmetric server behavior, early stall patterns, config drift) that surface metrics alone won't reveal. It may also confirm everything is healthy, which is valuable information.

Review the diagnose report before continuing:
- **HEALTHY / MINOR** — continue with Steps 5-9 normally
- **MAJOR** — note findings in the checkpoint, continue with caution. Use `superpowers:systematic-debugging` to trace root cause.
- **CRITICAL** — stop checkpoint. Use `superpowers:systematic-debugging` to trace root cause before fixing or escalating.

## Step 5 — Save top programs

Use `superpowers:dispatching-parallel-agents` — each run's top programs save is independent and can run concurrently.

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
gigaevo -e "$EXP" manifest get runs --format json | $GIGAEVO_PYTHON -c "
import sys, json, subprocess
runs = json.load(sys.stdin)
for run in runs:
    prefix = run.get('Prefix') or run.get('prefix')
    db = run.get('DB') or run.get('db')
    label = run.get('Label') or run.get('label')
    subprocess.run([
        'gigaevo', '-r', f'{prefix}@{db}:{label}',
        'top', '--save-dir', f'experiments/$EXP/top_programs_{label}'
    ], cwd='$PROJ')
"
```

## Step 6 — Test evaluation (HARD GATE at 50%+)

**MUST run exactly once** when `problem.has_test_set` is true AND any C run >= 50% of max_generations AND `mid_run_test_eval.completed` is not true in experiment.yaml.

**DO NOT skip for performance reasons.** Chain server contention is acceptable — the test eval is the only way to get an early signal on the hypothesis. If you are tempted to defer, ask the researcher instead of silently skipping.

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
HAS_TEST=$(gigaevo -e "$EXP" manifest get contract.problem.has_test_set 2>/dev/null)
MAX_GEN=$(gigaevo -e "$EXP" manifest get max_generations)
if [ "$HAS_TEST" != "True" ] && [ "$HAS_TEST" != "true" ]; then
  echo "SKIP: no test set"
else
  gigaevo -e "$EXP" manifest get runs --format json | $GIGAEVO_PYTHON -c "
import sys, json, yaml, redis
runs = json.load(sys.stdin)
max_gen = int('$MAX_GEN' or 0)
# Check if already done
raw_yaml = yaml.safe_load(open('$PROJ/experiments/$EXP/experiment.yaml'))
if raw_yaml.get('mid_run_test_eval', {}).get('completed'):
    print('SKIP: mid-run test eval already completed')
    exit(0)
# Check if any chain run (non-P-label) >= 50%
for run in runs:
    label = run.get('Label') or run.get('label')
    if label.startswith('P'):
        continue
    db = int(run.get('DB') or run.get('db'))
    prefix = run.get('Prefix') or run.get('prefix')
    r = redis.Redis(host='localhost', port=6379, db=db)
    _raw = r.hget(f'{prefix}:run_state', 'engine:snapshot')
    gen = json.loads(_raw)['programs_processed'] if _raw else 0
    if gen >= max_gen * 0.5:
        print(f'TRIGGER: {label} at gen {gen}/{max_gen} (>= 50%)')
        print('RUN_TEST_EVAL=yes')
        exit(0)
print('SKIP: no chain run at 50% yet')
"
  # If triggered, run it:
  if [ -f "$PROJ/experiments/$EXP/run_test_eval.sh" ]; then
      cd "$PROJ/experiments/$EXP"
      bash run_test_eval.sh
  fi
fi
```

After test eval completes, record it:
```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest update telemetry.mid_run_test_eval.completed true
gigaevo -e "$EXP" manifest update telemetry.mid_run_test_eval.completed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Mid-run test eval recorded in experiment.yaml"
```

## Step 7 — Invoke checkpoint-analyst agent (at 50%+ only)

**Only invoke** if this checkpoint is at >= 50% of max_generations AND `checkpoint_analysis.mid_run.completed` is not yet true in experiment.yaml. Skip at all other checkpoints — the analyst adds latency without actionable output for routine checks.

When triggered, use the `checkpoint-analyst` agent with:
- Status output from Step 2 **with condition labels replaced by opaque identifiers** (R1, R2, R3...) — do NOT pass run labels that reveal treatment/control assignment. The analyst must not know which arm is which.
- Diagnose report from Step 4 (also with condition labels redacted)
- Test eval results from Step 6 **withheld entirely** — held-out data must not influence the analyst's mid-run assessment. Record test eval results in the manifest but do not include them in the analyst briefing.
- Previous checkpoint data from experiment.yaml (opaque labels only)

To generate the opaque-label mapping before calling the analyst:
```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest get runs --format json | $GIGAEVO_PYTHON -c "
import sys, json
runs = json.load(sys.stdin)
mapping = {(r.get('Label') or r.get('label')): f'R{i+1}' for i, r in enumerate(runs)}
print('Opaque label mapping (keep private — share only Rs with analyst):')
for orig, opaque in mapping.items():
    print(f'  {orig} -> {opaque} (condition: REDACTED)')
print('Pass only the R-labels to the checkpoint-analyst agent.')
"
```

The analyst provides trend analysis using opaque labels only and reports trends.
This is advisory — the researcher decides on amendments/relaunches. The researcher holds the label mapping and interprets analyst findings in context.

After the analyst runs, record it:
```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest update telemetry.checkpoint_analysis.mid_run.completed true
gigaevo -e "$EXP" manifest update telemetry.checkpoint_analysis.mid_run.completed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Mid-run checkpoint analysis recorded"
```

## Step 8 — Record checkpoint in manifest

The Redis metric key is resolved from `problem.metric_name` in `experiment.yaml`:
`valid_frontier_{metric_name}` (e.g. `valid_frontier_actual_fitness`). The checkpoint entry
stores the value under `best_{metric_name}` and records `metric_name` explicitly so downstream
consumers (Step 9, closeout) do not need to re-parse the manifest.

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
gigaevo -e "$EXP" manifest get runs --format json | $GIGAEVO_PYTHON -c "
import sys, json, redis, yaml
from datetime import datetime, timezone
from pathlib import Path

runs = json.load(sys.stdin)

# Resolve metric name from manifest (falls back to 'fitness' — the normalized MAP-Elites metric)
manifest_path = Path('$PROJ/experiments/$EXP/experiment.yaml')
data = yaml.safe_load(manifest_path.read_text())
metric_name = (data.get('problem') or {}).get('metric_name') or 'fitness'
redis_key = f'valid_frontier_{metric_name}'
value_field = f'best_{metric_name}'

run_metrics = []
for run in runs:
    db = int(run.get('DB') or run.get('db'))
    prefix = run.get('Prefix') or run.get('prefix')
    label = run.get('Label') or run.get('label')
    r = redis.Redis(host='localhost', port=6379, db=db)
    _raw = r.hget(f'{prefix}:run_state', 'engine:snapshot')
    gen = json.loads(_raw)['programs_processed'] if _raw else 0
    raw = r.lindex(f'{prefix}:metrics:history:program_metrics:{redis_key}', -1)
    fitness = json.loads(raw)['v'] if raw else 0.0
    # Recent invalidity (last 20) — null-safe aggregation
    inv_hist = r.lrange(f'{prefix}:metrics:history:program_metrics:is_valid', -20, -1)
    vals = [json.loads(v)['v'] for v in inv_hist if json.loads(v).get('v') is not None]
    inv_rate = 1.0 - (sum(vals) / len(vals)) if vals else 0.0
    run_metrics.append({
        'label': label,
        'gen': gen,
        value_field: round(fitness, 5),
        'recent_invalidity': round(inv_rate, 3),
    })

avg_gen = sum(rm['gen'] for rm in run_metrics) / max(len(run_metrics), 1)

# Append checkpoint to experiment.yaml (raw YAML — allowed per D-01)
data.setdefault('checkpoints', []).append({
    'gen': int(avg_gen),
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'metric_name': metric_name,
    'run_metrics': run_metrics,
    'notes': '',
})
manifest_path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))
print(f'Checkpoint recorded at gen ~{avg_gen:.0f} (metric={metric_name})')
for rm in run_metrics:
    print(f'  {rm[\"label\"]}: gen={rm[\"gen\"]}, {value_field}={rm[value_field]}, inv={rm[\"recent_invalidity\"]*100:.0f}%')
"
```

Log the checkpoint event:

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
LOG="$PROJ/experiments/$EXP/04_issues_log.md"
[ ! -f "$LOG" ] && cp "$PROJ/experiments/_template/04_issues_log.md" "$LOG"
AVG_GEN=$(gigaevo -e "$EXP" manifest get runs --format json | \
  $GIGAEVO_PYTHON -c "
import sys, json, redis
runs = json.load(sys.stdin)
gens = []
for run in runs:
    db = int(run.get('DB') or run.get('db'))
    prefix = run.get('Prefix') or run.get('prefix')
    r = redis.Redis(host='localhost', port=6379, db=db)
    _raw = r.hget(f'{prefix}:run_state', 'engine:snapshot')
    gen = json.loads(_raw)['programs_processed'] if _raw else 0
    gens.append(gen)
print(int(sum(gens)/max(len(gens),1)))
")

cat >> "$LOG" << ENTRY

### [EVENT $(date -u +%Y-%m-%dT%H:%M:%SZ)] -- Checkpoint recorded at iter ~$AVG_GEN

- **When**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- **What**: Checkpoint recorded. Average iteration: ~$AVG_GEN.
- **Category**: checkpoint
- **Impact**: Automated capture.
ENTRY
```

## Step 9 — Update PR

Update the PR body AND post a **substantive** checkpoint comment with metrics, diagnose summary, and notes. Never post an empty or one-line comment.

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
# Update PR description
gigaevo -e "$EXP" manifest pr-description --push
# Post checkpoint comment
PR_NUM=$(gigaevo -e "$EXP" manifest get contract.identity.pr_number 2>/dev/null)
if [ -n "$PR_NUM" ] && [ "$PR_NUM" != "None" ]; then
  $GIGAEVO_PYTHON -c "
import yaml
from pathlib import Path
data = yaml.safe_load(Path('$PROJ/experiments/$EXP/experiment.yaml').read_text())
cp = (data.get('checkpoints') or [None])[-1]
if not cp:
    raise RuntimeError('No checkpoint data to post — run Step 8 first')
# Resolve metric name — checkpoints written by Step 8 include it; older rows fall back to problem.metric_name
metric_name = cp.get('metric_name') or (data.get('problem') or {}).get('metric_name') or 'fitness'
value_field = f'best_{metric_name}'
baseline = (data.get('baseline') or {}).get('mean')
lines = [f'## Checkpoint at gen ~{cp[\"gen\"]}', '']
if baseline is not None:
    lines.append(f'Baseline ({metric_name}): {baseline}')
lines.append('')
for rm in cp.get('run_metrics', []):
    val = rm.get(value_field)
    # Back-compat: older checkpoints stored 'best_fitness' regardless of metric
    if val is None:
        val = rm.get('best_fitness')
    inv = rm.get('recent_invalidity')
    delta_str = ''
    if val is not None and baseline is not None:
        delta_str = f' (Δ baseline {val - baseline:+.5f})'
    inv_str = f', inv={inv*100:.0f}%' if inv is not None else ''
    val_str = f'{val:.5f}' if isinstance(val, (int, float)) else str(val)
    lines.append(f'- {rm[\"label\"]}: gen={rm[\"gen\"]}, {value_field}={val_str}{delta_str}{inv_str}')
lines.append('')
lines.append(f'Timestamp: {cp[\"timestamp\"]}')
print('\n'.join(lines))
" | gh pr comment "$PR_NUM" --body-file -
  echo "PR updated with checkpoint"
else
  echo "No PR number — skipping PR update"
fi
```

## Step 9a — Log decisions and deviations (mandatory, not optional)

Record ALL decisions made at this checkpoint — not just errors. Any decision that could affect the interpretation of results is a potential protocol deviation and must be documented **at the time it is made**, not reconstructed at closeout.

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
[ ! -f "$PROJ/experiments/$EXP/04_issues_log.md" ] && \
  cp "$PROJ/experiments/_template/04_issues_log.md" "$PROJ/experiments/$EXP/04_issues_log.md"
```

Log entries fall into two categories:

**Operational issues** (bugs, crashes, interventions):
- When, What, Impact, Root cause, Fix applied, Systemic fix needed

**Protocol decisions** (things that could affect scientific interpretation):
- Examples: "decided to let run B continue despite high invalidity rate", "noticed treatment and control servers swapped — corrected at gen 15", "researcher asked about interim results — showed gen count only (no fitness)"
- For each: date/gen, decision, rationale, whether it constitutes a pre-registration deviation

**This step is never skipped** — if the checkpoint was entirely healthy and no decisions were made, write: `[CHECKPOINT gen=N] — No deviations or decisions. All runs healthy.`

This creates a complete audit trail. Deviations found in `04_issues_log.md` feed directly into the Deviations section of `05_results.md` at closeout.

## Gotchas

- **This skill is repeatable** — run it as often as needed. Use `/loop 2h /experiment-checkpoint <task/name>` for automatic polling.
- **Test eval is a HARD GATE** — MUST run once at 50%+ of max_gen. Do NOT skip for performance reasons. After running, it records `mid_run_test_eval.completed=true` so it won't re-run at subsequent checkpoints.
- **Diagnose runs every checkpoint** — not just when things look broken. Subtle issues are the dangerous ones.
- **Iteration count uses Redis** — `hget {prefix}:run_state engine:snapshot` (JSON blob; read its `programs_processed` field). Never grep logs for iteration counts.
- **Checkpoint-analyst runs at 50%+ only** — not every checkpoint. It's advisory and never decides. The researcher decides on amendments.
- **Don't run checkpoint on a completed experiment** — use the gate check. If you need to analyze a completed experiment, read the archived data directly.
- **When all runs are dead (completed or crashed)** — stop the watchdog (`kill <watchdog_pid>`) and cancel any `/loop` cron jobs (`CronList` → `CronDelete`). Stale watchdogs and crons waste resources and post confusing PR comments on finished experiments.
