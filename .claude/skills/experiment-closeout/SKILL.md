---
name: experiment-closeout
description: Close out a running experiment (Phase 4 Step 8 + Phase 5). Archives runs, runs final test eval, writes results, and merges PR. Triggers on "close experiment", "finish experiment", or when watchdog detects completion.
argument-hint: <task/name>
model: opus
---

# Experiment Closeout: $ARGUMENTS

Archive, analyze, and close a completed experiment.

## Step 0 -- Gate check: status must be running

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest gate running
gigaevo -e "$EXP" status
```

## Step 0b -- Kill watchdog process

```bash
EXP='$ARGUMENTS'
WD_PID=$(gigaevo -e "$EXP" manifest get control_plane.watchdog_pid 2>/dev/null)
if [ -n "$WD_PID" ] && [ "$WD_PID" != "None" ]; then
  kill "$WD_PID" 2>/dev/null && echo "Watchdog PID $WD_PID: killed" || echo "Watchdog PID $WD_PID: already dead"
else
  echo "No watchdog PID in experiment.yaml"
fi
```

## Step 0a -- Cancel anomaly detector cron

```bash
EXP='$ARGUMENTS'
CRON_ID=$(gigaevo -e "$EXP" manifest get control_plane.anomaly_detector_cron_id 2>/dev/null)
if [ -n "$CRON_ID" ] && [ "$CRON_ID" != "None" ]; then
  echo "Anomaly detector cron ID: $CRON_ID — cancel with CronDelete"
else
  echo "No anomaly detector cron to cancel"
fi
```

If a cron ID is found, use `CronDelete` to cancel it.

## Step 1 -- Read CONTEXT.md

Read `experiments/<task>/CONTEXT.md` for baseline values and benchmark reference.

## Step 2 -- Archive all runs

Use `superpowers:dispatching-parallel-agents` -- archiving each run is independent. See `references/archive-checklist.md` for details.

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
    cmd = ['bash', 'tools/experiment/archive_run.sh', '--exp', '$EXP',
           '--run', f'{prefix}@{db}:{label}', '--upload']
    print(f'Archiving {label}...')
    subprocess.run(cmd, cwd='$PROJ', check=True)
print('All runs archived')
"
```

## Step 3 -- Verify GitHub Release

```bash
EXP='$ARGUMENTS'
RELEASE_TAG="exp/$EXP"
gh release view "$RELEASE_TAG" --json assets -q '.assets | length'
```

Must have at least 1 asset per run.

## Step 4 -- Verify environment_freeze.txt committed

```bash
EXP='$ARGUMENTS'
git log --oneline --max-count=1 -- "experiments/$EXP/environment_freeze.txt"
```

## Step 5 -- Final test evaluation (if has_test_set)

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
HAS_TEST=$(gigaevo -e "$EXP" manifest get contract.problem.has_test_set 2>/dev/null)
if [ "$HAS_TEST" = "True" ] || [ "$HAS_TEST" = "true" ]; then
  echo "Running 5-repeat test evaluation..."
  cd "$PROJ/experiments/$EXP" && bash run_test_eval.sh
else
  echo "No test set -- skipping test evaluation"
fi
```

## Step 6 -- Phase 5: Invoke Elena for results analysis

Use the `ml-research-methodologist` agent. Output: `experiments/$EXP/05_results.md`. See `references/results-template.md` for required sections, CI format, and validation rules.

## Step 6a -- Validate 05_results.md before human review

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
python3 -c "
import re, sys
text = open('$PROJ/experiments/$EXP/05_results.md').read()

errors = []

if not re.search(r'\d+\.?\d*\s*%?\s*\[[\d\.\-,\s]+\]', text) and '95%' not in text and 'confidence interval' not in text.lower():
    errors.append('FAIL: No confidence interval found. Report effect as X.Xpp [Y.Y, Z.Z] 95% CI')

if 'Deviations from Pre-Registration' not in text:
    errors.append('FAIL: Deviations from Pre-Registration section missing')
elif re.search(r'(___+|<fill|PLACEHOLDER|TBD)', text):
    errors.append('FAIL: Deviations section contains unfilled placeholders')

if not re.search(r'\b(POSITIVE|NEGATIVE|NULL|SUGGESTIVE)\b', text):
    errors.append('FAIL: No verdict label (POSITIVE/NEGATIVE/NULL/SUGGESTIVE) found')

if errors:
    print('05_results.md validation FAILED:')
    for e in errors: print(f'  {e}')
    sys.exit(1)
else:
    print('05_results.md validation PASSED')
"
```

Fix any failures before proceeding to Step 7.

## Step 7 -- HUMAN APPROVAL GATE

Ask the researcher: "Please review `experiments/$EXP/05_results.md`. Is the analysis correct and complete? Type 'approved' to proceed with closeout."

Do NOT proceed without explicit approval. This is a hard human gate (R8).

## Step 8 -- Update INDEX.md

Add or update the experiment entry in `experiments/INDEX.md` with all columns:
- **Experiment**: `task/name`
- **Status**: Complete
- **Verdict**: POSITIVE / NEGATIVE / NULL / SUGGESTIVE / INCONCLUSIVE / REGRESSIVE
- **Effect (val)**: pp delta on validation set (e.g., +3.42pp)
- **Effect (test)**: pp delta on test set (e.g., +2.72pp)
- **Treatment Type**: category tag (topology, feedback, fitness, memory, prompt, crossover, meta-evolution, infrastructure, coevolution, baseline, multi-factor)
- **Key Finding**: one-line summary
- **PR**: PR number

## Step 9 -- Set status to complete

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest update status complete
```

## Step 10 -- Run check_experiment_complete.sh (hard gate)

```bash
PROJ="$(git rev-parse --show-toplevel)"
EXP='$ARGUMENTS'
bash $PROJ/tools/experiment/check_experiment_complete.sh "$EXP"
```

All checks must pass. Fix any failures before proceeding.

## Step 11 -- Update PR and merge

See `references/merge-rules.md` for merge policy, DB release, and INDEX.md update rules.

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest pr-description --push
```

Ask the researcher: "PR is ready. Merge with `gh pr merge --merge --delete-branch`? Type 'yes' to proceed."

## Step 12 -- Cleanup

```bash
EXP='$ARGUMENTS'
DBS=$(gigaevo -e "$EXP" manifest get runs --format json | \
  $GIGAEVO_PYTHON -c "import sys,json; print(' '.join(str(r.get('DB') or r.get('db')) for r in json.load(sys.stdin)))")
echo "Released DB claims: $DBS"
# Clean up Redis watchdog keys (raw Redis -- allowed per D-01)
$GIGAEVO_PYTHON -c "
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
for key in ['experiments:$EXP:watchdog_heartbeat', 'experiments:$EXP:rolling_comment_id']:
    r.delete(key)
print('Cleaned up Redis keys')
"
```

## Step 13 -- Update CONTEXT.md

Update `experiments/<task>/CONTEXT.md` with new results from this experiment:
- **Benchmarks table**: Add a row for this experiment's test result (if positive or notable)
- **Known Bugs**: Add any new bugs discovered in `04_issues_log.md` that are task-level (not experiment-specific)
- **Problem Variants**: Add new variants if this experiment created one

This keeps CONTEXT.md as the living single source of truth for future experiment designs.

## Step 13a -- Update PATTERNS.md

Update `experiments/PATTERNS.md` with new findings from this experiment:
- **Confirmed Patterns**: If this experiment strengthens an existing pattern or establishes a new one
- **Refuted Hypotheses**: If this experiment refutes a hypothesis
- **Suggestive Signals**: If results are suggestive but not conclusive
- **GigaEvo Platform Failure Modes**: If new GigaEvo bugs were discovered in `04_issues_log.md`
- **Open Questions**: Update or add based on what this experiment revealed

### Known Failures promotion (D-09)

Read `experiments/$EXP/04_issues_log.md`. For each entry where "Systemic fix needed: YES":

1. Check if a matching Known Failure entry (KF-XX) already exists in PATTERNS.md
2. If YES and the fix was applied: update the entry's Status from `ACTIVE` to `FIXED (<commit>)`
3. If NO: create a new KF-XX entry in the Known Failures table with:
   - **ID**: Next sequential KF-XX number
   - **Trigger Condition**: The circumstances that cause the failure (from "Root cause" field)
   - **Symptoms**: What the user observes (from "What" field)
   - **Root Cause**: Why it happens (from "Root cause" field)
   - **Fix**: How to prevent/resolve (from "Fix applied" field)
   - **Status**: `ACTIVE` if not yet fixed systemically, `FIXED (<commit>)` if fixed
   - **Affected Types**: Which experiment types are affected (solo, adversarial, adversarial_asymmetric, prompt_coevo, all)
   - **Source**: `<task>/<name>` experiment identifier

Skip entries where "Systemic fix needed: NO" -- these are one-off issues that don't warrant a Known Failure entry.

Do NOT update agent-specific memories with experiment results -- those belong in shared stores only.

## Step 13b — Auto-generate paper draft (PaperOrchestra pattern)

Automatically generate paper sections from this experiment's results:

```
/experiment-paper-draft $TASK $EXP
```

This runs non-interactively. Output:
- `experiments/$TASK/paper_data.json` — structured experiment data
- `experiments/$TASK/paper_draft.md` — assembled draft with all sections
- `experiments/$TASK/paper_review.md` — Reviewer 2 adversarial critique

This step does NOT block closeout. If paper-draft fails for any reason, log the error to `04_issues_log.md` and continue.

## Step 13c — Update IDEAS.yaml

Mark the idea that spawned this experiment as done:

```bash
PROJ="$(git rev-parse --show-toplevel)"
EXP='$ARGUMENTS'
TASK=$(echo "$EXP" | cut -d/ -f1)
VERDICT=$(grep "^Verdict:" "experiments/$EXP/05_results.md" 2>/dev/null | head -1 | cut -d: -f2 | xargs || echo "UNKNOWN")

$GIGAEVO_PYTHON -c "
import yaml
from pathlib import Path
p = Path('$PROJ/experiments/IDEAS.yaml')
data = yaml.safe_load(p.read_text())
for idea in data['ideas']:
    if idea.get('started_experiment') == '$EXP' or idea.get('status') == 'in_progress':
        if idea.get('task') == '$TASK' or idea.get('task') == 'any':
            idea['status'] = 'done'
            idea['result'] = '$VERDICT'
            idea['result_experiment'] = '$EXP'
            print(f'Marked done: {idea[\"id\"]}')
            break
p.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))
" 2>/dev/null || echo "WARNING: IDEAS.yaml update failed (non-blocking)"
```

Then call `/idea-generate $TASK` to populate the queue with new proposals based on this result.

## Step 14 -- Completion check (use superpowers:verification-before-completion)

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest gate complete
echo "COMPLETE: experiment-closeout finished successfully"
gh pr view --json state -q '.state'
```

## Gotchas

- **Kill watchdog + cancel cron FIRST** -- before archiving or closeout work.
- **Archive BEFORE flush** -- data loss is permanent. See `references/archive-checklist.md`.
- **Merge with `--merge`** -- never `--squash`. See `references/merge-rules.md`.
- **Human approval mandatory** for 05_results.md (R8).
- **Review issues log** -- `04_issues_log.md` systemic fixes go in deviations section.
- **Release DB claims after merge**, not before.
- **Update PATTERNS.md** -- new findings must flow into the shared pattern store.
- **Don't auto-close tracking issues** (R11).
