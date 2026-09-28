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

### Issue 5: Bearer None health checks fail with LiteLLM proxy (401)
- **When**: Implementation phase, all runs — WARNING in logs at startup
- **What**: `MultiModelRouter._verify_models()` and watchdog `check_model_identity()` use `Authorization: Bearer None` for `/v1/models`. LiteLLM proxy requires auth → 401.
- **Category**: tool bug (codebase-wide)
- **Impact**: Cosmetic WARNING in logs. Does NOT affect actual inference (uses `OPENAI_API_KEY=sk-gigaevo` → 200). Watchdog model drift check always returns false positive.
- **Root cause**: Health checks were written for bare vLLM (no auth). LiteLLM proxy added auth requirement.
- **Fix applied**: None yet — cosmetic issue only.
- **Systemic fix needed**: YES — `_verify_models()` and watchdog `check_model_identity()` should use `os.environ.get("OPENAI_API_KEY", "")` instead of `"None"`. Affects: `gigaevo/llm/models.py`, `experiments/_template/run_watchdog.py`, `tools/experiment/preflight_check.py`.

### Issue 4: Smoke test stuck on InsightsStage LLM call (~10min)
- **When**: Implementation phase, smoke test (1 gen)
- **What**: InsightsStage for initial program 226ebcb2 blocked for >10 min waiting on LLM response. No log activity after 00:36:48.
- **Category**: infra issue
- **Impact**: Smoke test could not complete 1 full generation; killed manually. Key treatment checks (pipeline, structural metrics, topology_3d config) all verified from partial run.
- **Root cause**: Transient proxy issue (LLM endpoint confirmed working: 200 in 0.14s with correct auth). Possibly NO_PROXY env not propagated to subprocess, or InsightsStage timeout too long.
- **Fix applied**: Killed smoke test. Accepted partial verification (all critical checks passed).
- **Systemic fix needed**: YES — smoke test should have a shorter stage_timeout (e.g. 120s) to fail fast on LLM issues.

### Issue 3: Redis DB not empty after interrupted smoke test
- **When**: Implementation phase, smoke test retry #2
- **What**: `run.py` refused to start because DB 7 still had 70 keys from the first interrupted smoke test
- **Category**: tool bug
- **Impact**: Required manual flush before retrying smoke test
- **Root cause**: Interrupted smoke test leaves data in Redis; no auto-cleanup on SIGKILL
- **Fix applied**: `tools/flush.py --db 7 --confirm`
- **Systemic fix needed**: YES — smoke test wrapper should auto-flush the target DB before starting, or use a dedicated ephemeral DB that is always flushed on entry

### Issue 2: Stale Redis instance lock after interrupted smoke test
- **When**: Implementation phase, smoke test retry #1
- **What**: `run.py` failed with "Cannot start: another instance is using Redis prefix 'chains/hover/full'" on DB 7
- **Category**: tool bug
- **Impact**: Had to manually delete the lock key via Python before retrying
- **Root cause**: First smoke test was interrupted (Ctrl+C / SIGKILL), leaving `chains/hover/full:__instance_lock__` in Redis DB 7
- **Fix applied**: `redis.Redis(db=7).delete('chains/hover/full:__instance_lock__')`
- **Systemic fix needed**: YES — `tools/flush.py` should also clear instance locks, or `run.py` should offer a `--force-lock` flag for smoke tests

### Issue 1: Missing OPENAI_API_KEY environment variable
- **When**: Implementation phase, first smoke test attempt
- **What**: `run.py` failed with `KeyError: "Environment variable 'OPENAI_API_KEY' not found"` during Hydra config resolution
- **Category**: skill bug
- **Impact**: Smoke test failed immediately; had to manually export the env var
- **Root cause**: The `/experiment-implement` smoke test step doesn't auto-export `custom_env` from experiment.yaml. The launch.sh script handles this, but ad-hoc smoke runs do not.
- **Fix applied**: Added `export OPENAI_API_KEY="sk-gigaevo"` before the smoke test command
- **Systemic fix needed**: YES — smoke test section of `/experiment-implement` skill should auto-export all `custom_env` vars from experiment.yaml before running
