# Failure Patterns Library

Real failure patterns observed across GigaEvo experiments. Each pattern includes symptoms the anomaly detector would observe, root cause, detection heuristic, and recommended action.

This library is the anomaly detector's **institutional memory**. It grows each time we close an experiment and review `04_issues_log.md`.

---

## Pattern 1: Helper Shape Mismatch

- **Experiment**: adversarial/heilbron-prover (2026-04-06)
- **Symptom**: One population has >70% invalidity while its peer population (same role) has <40%. Log shows consistent `ValueError: einstein sum subscripts string contains too many subscripts for operand 0`.
- **Root cause**: `helper.py` expected `(N, 2)` array but LLM-generated code passed single point `(2,)`. The `task_description.txt` did not document helper function input shapes.
- **Detection heuristic**: If one run has >70% invalid while a replicate of the same condition has <40%, AND log shows consistent ValueError → helper/API shape mismatch.
- **Action**: CRITICAL — fix helper.py to accept both shapes (`np.atleast_2d`), update task_description.txt with shape docs, clear `__pycache__`, restart affected runs.

## Pattern 2: Import Error Cascade

- **Experiment**: hover/dynamic-crossover (2026-03-15)
- **Symptom**: All runs 100% invalid from gen 1. Log shows `ImportError: cannot import name 'X' from 'Y'`.
- **Root cause**: Renamed function/import in validate.py or shared_config.py while runs were active. exec_runner subprocesses import the file fresh and crash.
- **Detection heuristic**: If >90% invalid from gen 1 across ALL runs AND log shows `ImportError` → code change broke running experiment.
- **Action**: CRITICAL — revert the import change (additive only during runs), clear `__pycache__` in problem dirs, restart all runs.

## Pattern 3: Timeout Massacre

- **Experiment**: hover/steady-state-v2 (2026-03-20)
- **Symptom**: 96% of evaluations fail. Log shows `ReadTimeoutError` or `httpx.ReadTimeout`. Invalidity spikes suddenly mid-experiment.
- **Root cause**: 120s read timeout too short for chain server under load. Multiple concurrent evaluations overwhelm the server.
- **Detection heuristic**: If invalidity spikes suddenly (was <30%, now >80%) mid-experiment AND log shows timeout errors → server overloaded or timeout misconfigured.
- **Action**: CRITICAL — increase timeout (or set to None with connect=30s), restart. If server overloaded, reduce concurrency.

## Pattern 4: Structured Output Escaping

- **Experiment**: Multiple (hover, hotpotqa)
- **Symptom**: Intermittent 20-30% SyntaxError in generated code. Log shows `SyntaxError` with double-escaped quotes `\\"`.
- **Root cause**: LLM using `with_structured_output()` sometimes double-escapes quotes in code fields. Known LLM quirk.
- **Detection heuristic**: If ~20-30% of mutations have SyntaxError with `\\"` pattern → known LLM quirk. Check if `_fix_double_escaped_quotes()` is in the mutation pipeline.
- **Action**: INFO — not actionable unless rate >50%. The fix is already in the mutation agent code. If rate >50%, check if the fix was bypassed.

## Pattern 5: Orphaned Programs (Ghost Detection)

- **Experiment**: hover/steady-state-v2 (2026-03-20)
- **Symptom**: Programs persisted to Redis but gen count doesn't advance. `programs_total_count` keeps increasing but the `engine:snapshot` blob's `programs_processed` is stuck.
- **Root cause**: `CancelledError` (a `BaseException`) not caught by `except Exception`, causing program IDs to be lost from the in-flight set.
- **Detection heuristic**: If gen stalled (unchanged for 2+ hours) but Redis `programs_total_count` still increasing → ghost detection failure or orphaned programs.
- **Action**: MAJOR — restart the affected run. If pattern recurs, check for `except Exception` that should be `except BaseException`.

## Pattern 6: Wrong Pipeline

- **Experiment**: hotpotqa experiments (multiple)
- **Symptom**: 100% invalid from gen 1 across all runs. Log shows `repr-contamination` or `TypeError` about dict vs tuple.
- **Root cause**: `pipeline=standard` used with a `validate.py` that returns a tuple `(metrics, failures)`. Standard pipeline expects plain dict.
- **Detection heuristic**: If 100% invalid from gen 1 AND cfg dump shows `pipeline=standard` but validate.py returns tuple → config error.
- **Action**: CRITICAL — fix experiment.yaml pipeline field, regenerate launch.sh, restart.

## Pattern 7: Stale __pycache__

- **Experiment**: Multiple
- **Symptom**: After applying a code fix, runs still exhibit the same error. Log shows the old traceback despite file changes.
- **Root cause**: Python cached `.pyc` files in `__pycache__/` directories. The exec_runner loads the cached bytecode.
- **Detection heuristic**: After a code fix + restart, if the same error persists in logs → check for stale `__pycache__`.
- **Action**: MINOR — `find problems/ -name __pycache__ -exec rm -rf {} +` then restart.

## Pattern 8: Asymmetric Throughput

- **Experiment**: adversarial/heilbron-prover (2026-04-06)
- **Symptom**: One replicate has 3-5x fewer valid programs than its peer at the same iteration count. No obvious errors in log.
- **Root cause**: Either (a) systematic bug in one replicate's config (→ fix), or (b) random LLM exploration hit a bad pattern early (→ not actionable).
- **Detection heuristic**: If replicates of SAME condition differ >3x in valid program count at comparable iteration → check if systematic or random. If same error in all failures of the lagging run → systematic bug.
- **Action**: WARN — investigate logs of the lagging run. If systematic (same error in all failures), fix and restart. If random, alert only.

## Pattern 9: Dead PID / Process Crash

- **Experiment**: Multiple
- **Symptom**: `kill -0 <pid>` returns error. Iteration count frozen. Log may end with traceback or mid-line.
- **Root cause**: OOM kill, unhandled exception, machine reboot, or user kill.
- **Detection heuristic**: `status.py --experiment` shows PID as DEAD.
- **Action**: CRITICAL — check last 100 lines of log for root cause. If OOM, reduce concurrency. Restart the dead run.

## Pattern 10: Server Down / Model Drift

- **Experiment**: Multiple
- **Symptom**: All mutations failing. Log shows `ConnectionRefusedError` or `HTTPError 502/503`. Or model identity check fails (different model served).
- **Root cause**: LLM server crashed, rebooted with different model, or network issue.
- **Detection heuristic**: `check_model_identity()` fails OR `status.py` shows all evaluations failing with connection errors.
- **Action**: CRITICAL — alert researcher. Server issues require infrastructure intervention, not experiment restart.

## Pattern 11: LiteLLM Auth Failure

- **Experiment**: adversarial/heilbron-prover (2026-04-06)
- **Symptom**: `/v1/models` returns HTTP 401 Unauthorized. Server model identity check fails. Preflight check 7/8 fail.
- **Root cause**: LiteLLM proxy requires `Authorization: Bearer <key>` but code used `Bearer None`.
- **Detection heuristic**: If `/v1/models` returns 401 but server is reachable on other ports → missing auth header.
- **Action**: MAJOR — fix auth headers to use `custom_env.OPENAI_API_KEY` from experiment.yaml. Non-blocking for evolution (run.py has the key), but breaks monitoring tools.

---

## How to Add New Patterns

When closing an experiment, review `04_issues_log.md` for entries marked "Systemic fix needed: YES". For each:

1. Create a new pattern entry with the format above
2. Include the experiment name and date
3. Describe what the anomaly detector would observe (not what a human noticed)
4. Write a concrete detection heuristic using available tools (status.py, trajectory.py, logs)
5. Classify the action: CRITICAL (auto-restart), MAJOR (alert + investigate), MINOR (note), INFO (ignore)
