# Merge and Cleanup Rules

## PR Merge

- **Always use `--merge`** -- never `--squash`. Squash destroys the pre-registration audit trail (design, review, plan commits become invisible).
- Command: `gh pr merge --merge --delete-branch`
- Ask the researcher for explicit confirmation before merging.

## DB Release

Release DB claims **after merging**, not before. Other experiments may try to claim those DBs while the PR is still open.

```bash
DBS=$(gigaevo -e "$EXP" manifest get runs --format json | \
  $GIGAEVO_PYTHON -c "import sys,json; print(' '.join(str(r.get('DB') or r.get('db')) for r in json.load(sys.stdin)))")
echo "Released DB claims: $DBS"
```

Also clean up Redis watchdog keys:
```bash
$GIGAEVO_PYTHON -c "
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
for key in ['experiments:$EXP:watchdog_heartbeat', 'experiments:$EXP:rolling_comment_id']:
    r.delete(key)
print('Cleaned up Redis keys')
"
```

## INDEX.md Update

Add or update the experiment entry in `experiments/INDEX.md` with:
- Status (complete)
- Result summary (POSITIVE/NEGATIVE/NULL/SUGGESTIVE + effect size)
- PR number

Update INDEX.md manually during closeout (Step 8).

## Tracking Issues

Don't auto-close tracking issues (R11). The researcher closes them manually after reviewing the merge.

## MEMORY.md Update

Update the active experiments table in MEMORY.md:
- Remove the completed experiment or mark as complete
- Update CONTEXT.md if the experiment produced new task-level learnings

## Issues Log Review

Read `experiments/$EXP/04_issues_log.md` during closeout. Issues marked "Systemic fix needed: YES" should be:
- Mentioned in `05_results.md` deviations section
- Tracked as follow-up work (consider `/post-experiment-fixes`)
