---
name: project-pm
description: Audit and enforce experiment tracking hygiene. Discovers experiments, ensures GitHub Issues exist on the project board, validates INDEX.md, and fixes discrepancies. Run manually, via /loop, or called by other experiment skills at lifecycle transitions. Triggers on "audit tracking", "check tracking", "project pm".
argument-hint: [--audit | --sync <task/name> | --bootstrap]
---

# Project PM: $ARGUMENTS

Audit and enforce experiment tracking hygiene on the GitHub project board.

Parse `$ARGUMENTS` to determine mode:
- `--bootstrap` → Run Step 0 (bootstrap: create board, labels, backfill)
- `--sync <task/name>` → Run Step 1 (sync one experiment)
- `--audit` or no args → Run Step 2 (full audit sweep)

## Step 0 — Bootstrap (one-time setup)

Only run when `$ARGUMENTS` contains `--bootstrap`.

### 0a — Check auth scope

```bash
PROJ="$(git rev-parse --show-toplevel)"
gh auth status 2>&1 | grep -q "project" || {
  echo "BLOCKED: 'project' scope not found. Run: gh auth refresh -s project"
  exit 1
}
echo "AUTH OK: project scope present"
```

### 0b — Create labels

```bash
REPO="KhrulkovV/gigaevo-core-internal"
gh label create "experiment"          --color "006b75" --description "Experiment tracking issue" --repo "$REPO" --force
gh label create "task:hotpotqa"       --color "c5def5" --description "HotpotQA experiments" --repo "$REPO" --force
gh label create "task:hover"          --color "bfdadc" --description "HoVer experiments" --repo "$REPO" --force
gh label create "status:preregistered" --color "0e8a16" --description "Pre-registered" --repo "$REPO" --force
gh label create "status:implemented"  --color "1d76db" --description "Implemented" --repo "$REPO" --force
gh label create "status:running"      --color "fbca04" --description "Running" --repo "$REPO" --force
gh label create "status:complete"     --color "0e8a16" --description "Complete" --repo "$REPO" --force
gh label create "status:invalid"      --color "d73a4a" --description "Invalid" --repo "$REPO" --force
gh label create "result:positive"     --color "0e8a16" --description "Positive result" --repo "$REPO" --force
gh label create "result:null"         --color "c5def5" --description "Null result" --repo "$REPO" --force
gh label create "result:negative"     --color "d73a4a" --description "Negative result" --repo "$REPO" --force
echo "Labels created/updated"
```

### 0c — Create project board and save config

```bash
PROJ="$(git rev-parse --show-toplevel)"
PYTHONPATH="$PROJ" $GIGAEVO_PYTHON "$PROJ/.claude/skills/project-pm/scripts/pm_audit.py" --bootstrap
```

This creates the board, queries field/option IDs, saves `board_config.yaml`, and backfills all experiments.

### 0d — Generate INDEX.md

```bash
PROJ="$(git rev-parse --show-toplevel)"
PYTHONPATH="$PROJ" $GIGAEVO_PYTHON "$PROJ/.claude/skills/project-pm/scripts/pm_audit.py" --generate-index
```

### 0e — Report

Use the `project-pm` agent to interpret the bootstrap output and produce a summary for the user.

---

## Step 1 — Sync one experiment

Only run when `$ARGUMENTS` contains `--sync <task/name>`.

```bash
EXP=$(echo '$ARGUMENTS' | sed 's/.*--sync\s*//' | awk '{print $1}')
PROJ="$(git rev-parse --show-toplevel)"
PYTHONPATH="$PROJ" $GIGAEVO_PYTHON "$PROJ/.claude/skills/project-pm/scripts/pm_audit.py" \
    --sync "$EXP" --fix
```

Report what was created or updated.

---

## Step 2 — Full audit sweep

Run when `$ARGUMENTS` is empty, `--audit`, or when invoked via `/loop`.

```bash
PROJ="$(git rev-parse --show-toplevel)"
PYTHONPATH="$PROJ" $GIGAEVO_PYTHON "$PROJ/.claude/skills/project-pm/scripts/pm_audit.py" \
    --audit --fix
```

Use the `project-pm` agent to interpret the audit output and produce a structured tracking hygiene report.
