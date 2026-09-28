# Issues Log

Track ALL errors, crashes, unexpected behavior, and manual interventions during this experiment.
This includes: run crashes, tool/script failures, watchdog issues, skill execution errors,
config mistakes, git problems, Redis issues, helper script bugs, and anything else that
did not execute as expected and required a manual fix or workaround.

This log is for post-experiment reflection — use it to identify bugs to fix and process improvements.

## Format

Each entry should include:
- **When**: timestamp or phase (e.g., "launch", "checkpoint #3", "gen 12")
- **What**: brief description of the issue
- **Category**: run crash | tool bug | config mistake | infra issue | skill bug | watchdog | git | other
- **Impact**: how it affected the experiment (data loss, wasted compute, delayed launch, etc.)
- **Root cause**: why it happened (if known)
- **Fix applied**: what was done to resolve it (including manual workarounds)
- **Systemic fix needed**: whether a code/process/tool change would prevent recurrence (YES/NO + description)

---

<!-- Add entries below, newest first -->

### Issue 3: Redis disk full — MISCONF errors (hour ~15)

- **When**: ~hour 15 of treatment runs (gen 14-16)
- **What**: Redis RDB snapshot failed, blocking all writes (`MISCONF: unable to persist to disk`)
- **Category**: infra issue
- **Impact**: ~2500 MISCONF errors per treatment run. Runs stalled briefly until fix applied.
- **Root cause**: `/home/jovyan` disk 100% full (100G/100G). Redis couldn't write RDB snapshots.
- **Fix applied**: `redis config set stop-writes-on-bgsave-error no` — disabled write-blocking on RDB failure. Runs resumed immediately.
- **Systemic fix needed**: YES — monitor disk space in watchdog; alert when >90% full.

### Issue 2: task_description.txt said "Maximum 10 steps" for full7 (launch)

- **When**: First treatment run batch (pre-restart)
- **What**: `problems/chains/hover/full7/task_description.txt` was copied from `full/` without updating the step limit from 10 to 7. The mutation LLM generated 9-10 step chains, causing 97% invalidity in treatment runs.
- **Category**: config mistake
- **Impact**: First treatment run batch (V3/V4) wasted ~6 hours. All treatment programs invalid. Required flush + restart.
- **Root cause**: When creating `full7/` by copying `full/`, only `config.py` max_steps was changed; `task_description.txt` was not updated.
- **Fix applied**: Updated all "10 steps" references to "7 steps" in `task_description.txt`. Flushed DBs 5-6, restarted V3/V4.
- **Systemic fix needed**: YES — add a preflight check that verifies `task_description.txt` step limit matches `config.py` max_steps.

### Issue 1: Preflight DB claim collision (launch)

- **When**: Initial launch attempt
- **What**: Preflight check #10 failed — DBs 3-6 still claimed by `hover/map-elites-topology` (completed experiment).
- **Category**: config mistake
- **Impact**: Launch blocked. 2 minutes to fix.
- **Root cause**: DB claims from prior experiment not released during its closeout.
- **Fix applied**: `release_db_claims([3,4,5,6])` then re-ran launch.
- **Systemic fix needed**: NO — existing process works; claims should be released during closeout (was missed for map-elites-topology).
