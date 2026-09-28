---
name: post-experiment-fixes
description: Read an experiment's issues log (04_issues_log.md) and apply systemic fixes to tools, skills, scripts, templates, and code. Use after an experiment completes (or during, for urgent fixes) to prevent the same issues from recurring. Triggers on "fix experiment issues", "post-experiment fixes", "apply fixes from issues log".
argument-hint: <task/name>
---

# Post-Experiment Fixes: $ARGUMENTS

Read the experiment's issues log and apply all systemic fixes to prevent recurrence.

## Step 0 — Read the issues log

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
cat "$PROJ/experiments/$EXP/04_issues_log.md"
```

If the file doesn't exist, stop — nothing to fix.

## Step 1 — Triage issues

For each entry in the log, classify it:

| Systemic fix needed? | Action |
|---|---|
| **NO** | Skip — one-off issue, already resolved |
| **YES — already fixed in this experiment's code** | Check if fix needs backporting to templates/shared code |
| **YES — not yet fixed** | Plan the fix |

Build a fix list with:
- **What**: the fix description
- **Where**: which file(s) to change
- **Type**: template backport / tool fix / skill update / core code fix / config default change / documentation update
- **Risk**: low (template/docs) / medium (tool/skill) / high (core code)

Use `superpowers:writing-plans` to write the fix plan. Present it for user approval before proceeding.

## Step 2 — Apply fixes (low risk first; use `superpowers:dispatching-parallel-agents` for independent categories)

If multiple approved fixes fall in different categories and touch different files, dispatch them in parallel using `superpowers:dispatching-parallel-agents`. Always apply template fixes before core code fixes to preserve the risk ordering.

Work through the approved fixes in order of risk:

### 2a. Template backports
Copy fixes from experiment-specific files back to templates:
- `experiments/_template/run_watchdog.py` — watchdog fixes
- `experiments/_template/*.md` — documentation fixes
- `experiments/_template/run_test_eval.sh` — test eval fixes

### 2b. Tool and script fixes
Fix issues in shared tools:
- `tools/` — status.py, comparison.py, flush.py, etc.
- `tools/experiment/` — diagnose.py, etc.
- `.claude/skills/experiment-*/scripts/` — diagnose.py, etc.

### 2c. Skill updates
Update skill instructions:
- `.claude/skills/*/SKILL.md` — add gotchas, fix instructions, update steps

### 2d. Core code fixes
Fix issues in the framework:
- `gigaevo/` — engine, storage, stages, etc.

### 2e. Config and documentation
- `config/` — default values, new configs
- `experiments/<task>/CONTEXT.md` — known bugs, recommended settings
- `docs/` — protocol updates

## Step 3 — Run tests (use `superpowers:verification-before-completion`)

After applying fixes:
```
/run-tests
```

Hard gate — all tests must pass. If a fix breaks tests, revert and reconsider.

## Step 4 — Update the issues log

For each fixed issue, update its entry:
- Change "Systemic fix needed: YES" to "Systemic fix needed: DONE — [commit or description]"

### Update PATTERNS.md Known Failure statuses

For each fixed issue that has a corresponding KF-XX entry in `experiments/PATTERNS.md` Known Failures table:
- Update the Status column from `ACTIVE` to `FIXED (<commit-hash>)`
- If no KF-XX entry exists for a systemic fix, create one (follow the same process as experiment-closeout Step 13a)

## Step 5 — Commit (use `superpowers:finishing-a-development-branch`)

Use `superpowers:finishing-a-development-branch` to commit, push, and update any associated PR. Include the list of fixed issues in the commit message.

Include `experiments/$EXP/06_fixes_applied.md` in the commit along with all fixed files.

## Step 6 — Generate 06_fixes_applied.md report

Generate a structured fix report at `experiments/$EXP/06_fixes_applied.md` (D-10). This maps each issue from 04_issues_log.md to its fix or deferral reason.

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
```

Create `experiments/$EXP/06_fixes_applied.md` with this format:

```markdown
# Fixes Applied: <task/name>

**Generated:** <date>
**Source:** 04_issues_log.md (<N> entries processed)

| # | Issue Summary | Fix Type | Files Changed | Status | Commit/Reason |
|---|--------------|----------|---------------|--------|----------------|
| 1 | <description from issues log> | <template/tool/skill/core/config/docs> | <file.py, SKILL.md, ...> | DONE | <commit hash> |
| 2 | <description> | <type> | <files> | SKIPPED | <reason: e.g., "self-resolving race condition"> |
| 3 | <description> | <type> | <files> | DEFERRED | <reason: e.g., "needs design discussion"> |

**Summary:** X fixed, Y skipped, Z deferred
**Patterns promoted to PATTERNS.md:** KF-XX, KF-YY (list IDs of new or updated Known Failure entries)
```

Populate the table from the fix list built in Step 1 (triage) and the results of Steps 2-5 (apply, test, update, commit). Each row corresponds to one entry in 04_issues_log.md. Status values:
- **DONE**: Fix was applied and committed
- **SKIPPED**: Issue was one-off, already resolved, or not worth fixing
- **DEFERRED**: Fix is needed but blocked or requires separate design work

Then present the report to the researcher as the skill's completion output.

## Gotchas

- **Get approval first** — present the fix list before changing anything. Some "fixes" may be intentional behavior or already addressed elsewhere.
- **Low risk first** — template/docs before tools before core code. If a core fix fails tests, you haven't broken anything else.
- **Don't fix hypothesis-relevant issues** — if the log says "treatment arm underperformed," that's data, not a bug.
- **Check for duplicates** — the same fix may appear in multiple experiments' logs. Don't apply it twice.
- **Backport watchdog fixes** — the template `run_watchdog.py` is copied per-experiment. Fixes to one experiment's watchdog need to be backported to the template so new experiments get the fix.
- **This skill can run mid-experiment** — for urgent fixes that need a restart, apply fixes then `/experiment-restart`. But prefer running after closeout when the full picture is clear.
