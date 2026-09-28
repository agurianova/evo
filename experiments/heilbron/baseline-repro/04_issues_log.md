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

---

### Issue #3: P4_A sync stall after P4_B completion

- **When**: 2026-04-11, gen~49 (P4_A stalled ~21 min)
- **What**: P4_A stalled at gen 49/50. Total programs count frozen at 375. Last metric update 1295s ago. P4_B completed gen 50 and exited; P4_A appears blocked in MainRunSyncHook waiting for a dead opponent.
- **Category**: infra issue
- **Impact**: P4_A will likely not reach gen 50. Data from gens 1–49 intact. P4 Constructor final actual_fitness will be from gen 49 (0.03023). Scientific impact low — P3 pair fully complete.
- **Root cause**: MainRunSyncHook polls opponent Redis gen count before allowing a new generation. When P4_B exits naturally at max_gen, it stops updating Redis. P4_A may be stuck waiting for an opponent state update that will never come.
- **Fix applied**: Alert posted. Waiting 1h for sync timeout to self-resolve before manual kill of P4_A (PID 1727172).
- **Systemic fix needed**: YES — MainRunSyncHook should detect when opponent gen >= max_generations and skip the wait, allowing the remaining process to finish its final generation.

---

### [CHECKPOINT gen~42] 2026-04-11 — P4 at 96%. No deviations.

- P4 at 48/50 (96%), expected to complete ~2h. P1 at 42/50 (84%). P2 at 28/50 (56%, slow).
- Mean Constructor actual_fitness: 0.03337 (REVISED band, rising trend: 0.03111→0.03293→0.03337).
- All 6 active PIDs alive, all pairs synchronized (gap=0). Watchdog 1953059 alive.
- Diagnose: HEALTHY. CRITICAL = known false positive (server auth probe, Issue #2).
- **Decisions**: None. No protocol deviations.

---

### [CHECKPOINT gen~39] 2026-04-11 — P3 pair COMPLETE. No deviations.

- P3_A/P3_B reached gen 50/50 (DEAD = natural completion). P3_A actual_fitness=0.03650 (CONFIRMED HIGH, above Q_MAX=0.0365). P3_B actual_fitness=0.03454.
- Active pairs: P4 at 44/50 (88%), P1 at 38/50 (76%), P2 at 24/50 (48%) — P2 still lagging (expensive evolved programs, 38% invalidity, known since gen~12).
- Mean Constructor actual_fitness (N=4): 0.03293 → REVISED band. P3_A alone is CONFIRMED HIGH; others in REVISED range.
- All 6 active PIDs alive. Pair sync healthy (gap ≤1). Watchdog 1953059 alive.
- Diagnose: HEALTHY. CRITICAL = known false positive (server auth probe, Issue #2).
- top_programs saved for all 8 runs. Namespace collision (Issue #1) confirmed fixed.
- **Decisions**: None that affect scientific interpretation. No protocol deviations.

---

### [CHECKPOINT gen~25] 2026-04-10 ~21:30 UTC — Mid-run analysis complete. No protocol deviations.

- All 8 PIDs alive, watchdog 1953059 alive.
- Diagnose run: 1 MAJOR (P1_A: 9 DAG stage failures — normal evolutionary invalidity: exec errors, syntax errors, timeouts), 1 CRITICAL per run (FALSE POSITIVE: diagnose script probes mutation server root `/v1` without auth headers; LiteLLM returns 400; server is operational, confirmed via `/v1/models` with auth).
- Sync check: all 4 pairs in sync (gen gap ≤ 1), no deadlock.
- Mid-run checkpoint-analyst invoked (P3_A at 56%, P4_A at 50%). Mean Constructor actual_fitness = 0.03111 (REVISED band). Rising actual_fitness from gen~12 to gen~25 explained: MAP-Elites selects on composite fitness (quality+resistance), not actual_fitness; Constructors trading raw min_area quality for 100% resistance — expected adversarial dynamics.
- No decisions that affect scientific interpretation.
- **Systemic fix needed (diagnose script false positive)**: YES — diagnose.py should check server reachability using authenticated `/v1/models` request with API key from `custom_env.OPENAI_API_KEY`, not unauthenticated root endpoint.

### Issue #2: diagnose.py false-positive CRITICAL on LiteLLM server

- **When**: 2026-04-10, gen~25 checkpoint
- **What**: `experiment-diagnose` reports CRITICAL "mutation server UNREACHABLE" for all 8 runs.
- **Category**: tool bug
- **Impact**: Misleading CRITICAL alerts requiring manual verification. No actual impact on experiment.
- **Root cause**: diagnose.py checks mutation server by making GET request to `/v1` (root endpoint) without auth headers. LiteLLM returns HTTP 400 (auth required). Script interprets any non-200 as UNREACHABLE.
- **Fix applied**: Manually verified server at `/v1/models` with auth header — returns 200 with `Qwen3-235B-A22B-Thinking-2507` listed.
- **Systemic fix needed**: YES — `diagnose.py` should use authenticated GET `/v1/models` with API key from experiment.yaml `custom_env.OPENAI_API_KEY`.

### [CHECKPOINT gen~21] — 2026-04-10 ~17:00 UTC

- All 9 PIDs alive (8 runs + watchdog 1744577)
- 0% invalidity across all runs, 0 errors in any log
- Diagnose: HEALTHY — MainRunSyncHook confirmed, config correct
- Pair 2 (P2_A/P2_B) at gen 7 vs others at gen 13–16: attributed to computationally expensive evolved programs (up to 2928s CallProgramFunction). Not an infrastructure issue.
- Constructor actual_fitness mean: ~0.02958 (below baseline 0.03464 — expected at gen 12/50)
- No protocol deviations.

### Issue #1: gigaflow/tools namespace collision

- **When**: 2026-04-10, gen~12 checkpoint
- **What**: `tools/top_programs.py` fails with `ModuleNotFoundError: No module named 'tools.utils'` because gigaflow's editable install exposes a conflicting `tools` package that shadows gigaevo's local `tools/`.
- **Category**: infra issue
- **Impact**: top_programs.py unusable without workaround. top programs NOT saved at this checkpoint.
- **Root cause**: gigaflow is installed editable and has `tools/__init__.py`. Its finder hook intercepts `import tools` before `PYTHONPATH=.` can resolve it.
- **Fix applied**: None — user declined sys.path hack approach.
- **Systemic fix needed**: YES — either (a) remove `tools/__init__.py` from gigaflow to make it a namespace package, or (b) rename gigaevo's `tools/` to `gigaevo_tools/`.

### [CHECKPOINT gen~21] — 2026-04-10 ~17:00 UTC

All 8 PIDs alive, watchdog alive (PID 1953059). No errors in logs. All runs advancing.
Actual fitness range: 0.027–0.035, below baseline 0.034 — expected at gen 20/50.
P3_A leading at gen 27 (54%). Diagnose dispatched as background agent (context constrained).
Checkpoint-analyst skipped this cycle — context exhausted (90%+). Will invoke at next checkpoint if mid_run not yet completed.
- **Decisions**: None that affect scientific interpretation.

### [CHECKPOINT gen~29] 2026-04-11 — No deviations or decisions. All runs healthy.

- All 8 PIDs alive, watchdog 1953059 alive.
- P3_A at gen 42/50 (84%), actual_fitness=0.03350 — first Constructor above CONFIRMED threshold (0.033).
- Mean Constructor actual_fitness: 0.03170 (REVISED band, trending up from 0.03111 at gen~25).
- Diagnose: HEALTHY. CRITICAL = known false positive (server auth probe). No new issues.
- No protocol deviations.
