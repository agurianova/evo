---
name: research-scheduler
description: Autonomous research scheduler. Picks the top-ranked queued idea from IDEAS.yaml, derives an experiment name, and starts the full experiment lifecycle via /run-experiment. Human can veto at Gate 1. Triggers on "start next experiment", "schedule next", "autonomous mode".
argument-hint: [--task <hover|hotpotqa>] [--dry-run]
model: opus
---

# Research Scheduler: $ARGUMENTS

Pick the top-ranked queued idea from IDEAS.yaml and start the experiment lifecycle.

## Step 0 — Parse arguments

- `--task <name>`: only consider ideas for this task
- `--dry-run`: show which idea would be picked, but do not start the experiment

## Step 1 — Check resources

Before picking an idea, verify resources are available. Manually check available servers and Redis DBs in `experiments/infrastructure.yaml`. If no free resources, wait for a run to complete.

## Step 2 — Read IDEAS.yaml

```bash
PROJ="$(git rev-parse --show-toplevel)"
$GIGAEVO_PYTHON -c "
import yaml; from pathlib import Path
ideas = yaml.safe_load(Path('$PROJ/experiments/IDEAS.yaml').read_text())['ideas']
queued = [i for i in ideas if i['status'] == 'queued']
# Filter by task if --task given
task_filter = '$ARGUMENTS'.split('--task')[-1].split()[0] if '--task' in '$ARGUMENTS' else None
if task_filter:
    queued = [i for i in queued if i['task'] == task_filter or i['task'] == 'any']
# Sort by rank descending
queued.sort(key=lambda x: x['rank'], reverse=True)
if not queued:
    print('NO_QUEUED_IDEAS')
else:
    top = queued[0]
    print(f'ID={top[\"id\"]}')
    print(f'TITLE={top[\"title\"]}')
    print(f'TASK={top[\"task\"]}')
    print(f'RANK={top[\"rank\"]}')
    print(f'HYPOTHESIS={top[\"hypothesis\"][:200]}')
"
```

If NO_QUEUED_IDEAS: print "IDEAS.yaml has no queued ideas. Run /experiment-retrospective to generate new ideas." and stop.

## Step 3 — Derive experiment name

From the top idea, derive an experiment name following the convention `<task>/<short-slug>`:

- Take the idea title, lowercase, replace spaces with hyphens
- Trim to ≤ 30 chars
- Example: "Gradient-signal fitness: LLM critique" → `hover/gradient-critique`

Verify no experiment with that name exists yet:
```bash
[ ! -d "experiments/$TASK/$NAME" ] && echo "NAME_OK" || echo "NAME_TAKEN"
```

If taken: append `-v2`, `-v3`, etc.

## Step 4 — Mark idea as in_progress

```bash
PROJ="$(git rev-parse --show-toplevel)"
$GIGAEVO_PYTHON -c "
import yaml
from pathlib import Path
p = Path('$PROJ/experiments/IDEAS.yaml')
data = yaml.safe_load(p.read_text())
for idea in data['ideas']:
    if idea['id'] == '$IDEA_ID':
        idea['status'] = 'in_progress'
        idea['started_experiment'] = '$TASK/$NAME'
        break
p.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False))
print('Marked in_progress')
"
```

## Step 5 — Show selection and confirm (or proceed if dry-run)

Print:
```
Research Scheduler: selected idea

  ID:         hover_001
  Title:      Gradient-signal fitness: LLM critique replaces binary signal
  Rank:       0.91
  Task:       hover
  Experiment: hover/gradient-critique

  Hypothesis:
  [first 300 chars of hypothesis]

Starting /run-experiment hover/gradient-critique in 10 seconds...
Reply 'cancel' to abort.
```

Wait 10 seconds for a cancel reply. If Telegram is configured, also send the selection as a notification.

If `--dry-run`: print selection and stop without starting.

## Step 6 — Start experiment

```
/run-experiment $TASK/$NAME $HYPOTHESIS_ONE_SENTENCE
```

The experiment lifecycle will handle the rest. Gate 1 (design approval) will fire via Telegram.

## Step 7 — Update IDEAS.yaml on completion

After the experiment closes out (status=complete), update the idea:
```yaml
status: done
result: POSITIVE | NULL | NEGATIVE | SUGGESTIVE
result_experiment: hover/gradient-critique
```

This is done automatically by experiment-closeout (which calls idea-generate, which handles status updates).

## Gotchas

- **Never start two experiments simultaneously** on the same task — resource contention and config confusion.
- **On_hold ideas are never picked** — researcher controls when to re-queue them.
- **Any idea can be de-queued** by setting `status: on_hold` in IDEAS.yaml.
- **Rank is a hint, not a mandate** — the scheduler picks the top-ranked, but the human gate (Gate 1) is the actual veto.
