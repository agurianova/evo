# Issues Log

Track ALL errors, crashes, unexpected behavior, and manual interventions during this experiment.

## Format

Each entry should include:
- **When**: timestamp or phase
- **What**: brief description of the issue
- **Category**: run crash | tool bug | config mistake | infra issue | skill bug | watchdog | git | other
- **Impact**: how it affected the experiment
- **Root cause**: why it happened
- **Fix applied**: what was done to resolve it
- **Systemic fix needed**: whether a code/process/tool change would prevent recurrence

---

### [CLOSEOUT gen=34, 2026-04-09T~13:00 UTC] — PREMATURE STOP (researcher decision)
All runs killed at gen 31-38 (~45% of max_gen=75). Researcher decided to stop early to focus on next experiment (issue #195: D re-evaluation). K=3 pair clearly ahead (+3.1% vs baseline), K=1 pair stalled (-6.2%). Sufficient signal to answer hypotheses without running to completion. This is a pre-registration deviation: experiment stopped before max_generations=75.

### [CHECKPOINT gen=33, 2026-04-09T~12:35 UTC] — No deviations. All runs healthy.
P1_A gen=30 (actual=0.03502), P1_B gen=33 (actual=0.03568, new best overall), P2_A gen=32 (actual=0.03247), P2_B gen=37 (actual=0.03247). All PIDs alive. Watchdog alive. Diagnose: HEALTHY (4x MINOR stagnation, 1x MAJOR false positive on evolution=steady_state cfg group check — known issue). Fixed diagnose.py bug: treatment_checks dict format crashed with AttributeError. ~44% through. Next checkpoint should hit 50% gate.

### Issue 7: diagnose.py crashes on dict-format treatment_checks
- **When**: 2026-04-09T12:30 (checkpoint #9)
- **What**: `check_treatment_declarative()` iterated `treatment_checks` dict, calling `.get()` on string keys
- **Category**: tool bug
- **Impact**: Diagnose script crashed before completing treatment checks for all 4 runs
- **Root cause**: `treatment_checks` in experiment.yaml uses old dict format `{log_pattern_present: [...]}` but diagnose.py expected new list-of-dicts format `[{type: ..., name: ...}]`
- **Fix applied**: Added format normalization in diagnose.py line 1410 — converts old dict format to list-of-dicts before passing to `check_treatment_declarative()`
- **Systemic fix needed**: NO — fix applied

### [CHECKPOINT gen=30, 2026-04-09T~08:20 UTC] — No deviations. All runs healthy.
P1_A gen=27 (actual=0.03502), P1_B gen=29 (actual=0.03449), P2_A gen=29 (actual=0.03247), P2_B gen=33 (actual=0.03247). All PIDs alive. Watchdog alive. K=3 pair ahead of baseline (+1.1%). K=1 pair stalled at 0.03247. ~38% through. Diagnose: HEALTHY. No stopping rules triggered. Approaching 50% gate for checkpoint analyst + test eval.

### [CHECKPOINT gen=26, 2026-04-09T~05:17 UTC] — No deviations. All runs healthy.
P1_A gen=23 (actual=0.03502), P1_B gen=26 (actual=0.03405), P2_A gen=25 (actual=0.03247), P2_B gen=29 (actual=0.03247). All PIDs alive. P2_A stalled at 0.03247 for ~10 gens. Both Improver frontier fitnesses unchanged. No stopping rules triggered.

### [CHECKPOINT gen=21, 2026-04-09T~UTC] — MILESTONE: P1_A exceeds v1 baseline.
P1_A gen=19 (actual_fitness=0.03502 > v1 baseline 0.03462), P1_B gen=21 (0.3669), P2_A gen=20 (0.3248), P2_B gen=24 (0.3831). All PIDs alive. Watchdog 3448119 alive. K=3 pair ahead of K=1. Both Improvers stalled in frontier fitness — consistent with known D stagnation problem. Diagnose: HEALTHY.

### [CHECKPOINT gen=4, 2026-04-08T22:10 UTC] — No deviations. All runs healthy.
P1_A gen=3 (fitness=0.924), P1_B gen=5 (fitness=0.421), P2_A gen=2 (fitness=0.875), P2_B gen=6 (fitness=0.383). All PIDs alive. Watchdog 3448119 alive. Invalidity 0% recent window. Diagnose: HEALTHY. Checkpoint cron changed from 30min/2h to 3h (researcher request).

### [CHECKPOINT gen=4, 2026-04-08T21:15 UTC] — No deviations. All runs healthy.
P1_A gen=3 (fitness=0.924), P1_B gen=5 (fitness=0.421), P2_A gen=2 (fitness=0.875), P2_B gen=6 (fitness=0.383). All PIDs alive. Watchdog restarted with subprocess-based arms-race plot (PID 3448119). Invalidity 0% in recent window. No stopping rules triggered. Diagnose: HEALTHY across all checks.

### [CHECKPOINT gen=2, 2026-04-08T20:50 UTC] — No deviations. All runs healthy.
P1_A/P1_B at gen=1 (stalled waiting for LLM calls ~38-41 min in, within 50-min stage_timeout — will resume). P2_A gen=2, P2_B gen=4. Sync hooks: waited=0.0s. Invalidity: Constructors 23-36% (below 75% stop threshold), Improvers 0-2%. OpponentFeedbackStage active in all 4 runs. No CRITICAL errors.

### Issue 6: experiment-checkpoint skill `!` backtick auto-injection broken
- **When**: 2026-04-08T21:30 (checkpoint #3)
- **What**: Skill's Step 1 used `!` backtick patterns to auto-inject shell output into the prompt. Failed with "Shell command failed for pattern" error, blocking every cron-scheduled checkpoint.
- **Category**: skill bug
- **Impact**: All scheduled checkpoints failed silently for ~1 hour
- **Root cause**: `!` backtick patterns with nested `$(git rev-parse ...)` and `$ARGUMENTS` variable substitution are not supported in this environment's skill loader
- **Fix applied**: Removed the 3 auto-injection lines from SKILL.md Step 1; replaced with read-these-files instructions for the agent
- **Systemic fix needed**: NO — fix applied

### Issue 5: Inter-epoch stale counter — programs_processed only published at epoch boundary
- **When**: 2026-04-08T18:30 (checkpoint #2, launch 4)
- **What**: P1_B had `programs_processed=1` in Redis (seed ingestion value) while P1_A waited for it to reach 2. Counter stuck between epochs because `save_run_state(programs_processed)` only ran during `_epoch_refresh()`.
- **Category**: tool bug
- **Impact**: P1_A sync hook blocked 240+ seconds waiting for P1_B counter that wouldn't advance until next epoch boundary. Slow convergence / potential timeout cascade.
- **Root cause**: `_ingest_batch()` incremented `self.metrics.programs_processed` in memory but only published to Redis at epoch refresh (step 9, later step 3a). Between epochs, Redis had stale value.
- **Fix applied**: Added `save_run_state(programs_processed)` inside `_ingest_batch()` after every batch of completed programs (`steady_state.py:~468`)
- **Systemic fix needed**: NO — structural fix applied (counter now published continuously)

### Issue 4: Sync hook timeout doesn't reset baseline (audit finding)
- **When**: 2026-04-08 pre-launch audit
- **What**: `ProgressBasedSyncHook` doesn't update `_last_progress` after timeout, causing every subsequent epoch to also wait the full 7200s timeout
- **Category**: other (latent bug found by audit)
- **Impact**: Would have caused permanent 2h/epoch degradation after any single timeout event
- **Root cause**: Timeout branch in `__call__()` returned without updating `_last_progress`, so next call used stale baseline
- **Fix applied**: Added `self._last_progress = min_progress` before return in timeout branch (`sync.py:165`)
- **Systemic fix needed**: NO — one-line fix applied

### Issue 3: `programs_processed` only counted accepted programs
- **When**: 2026-04-08 pre-launch audit
- **What**: `_ingest_batch()` incremented `programs_processed` by `added` (accepted only), not `len(completed)` (all evaluated)
- **Category**: other (latent bug found by audit)
- **Impact**: If rejection rate is 100%, sync hook counter never advances, causing deadlock between populations
- **Root cause**: Counter semantics mismatch — sync hook needs "work done" but counter tracked "archive additions"
- **Fix applied**: Changed `_ingest_batch()` to count all completed programs (`steady_state.py:465`)
- **Systemic fix needed**: NO — semantics fix applied

### Issue 2: Epoch refresh deadlock — programs_processed saved after sync hook
- **When**: 2026-04-08T18:16 (launch 3)
- **What**: All 4 runs deadlocked at epoch 0 refresh — sync hook blocked waiting for opponent's counter, but counter only saved to Redis AFTER the hook
- **Category**: config mistake + tool bug
- **Impact**: All 4 runs stuck for 240+ seconds before detection. Required full restart.
- **Root cause**: `_epoch_refresh()` called `_pre_step_hook()` at step 4 but `programs_processed` written to Redis at step 9. Both populations blocked at step 4 waiting for each other.
- **Fix applied**: Added `save_run_state(programs_processed)` at step 3a (before hook call) in `steady_state.py`. Also added save at startup before first hook call. Removed redundant save at step 9.
- **Systemic fix needed**: NO — structural fix applied

### Issue 1: min_delta=10 > max_mutations_per_generation=8 deadlock
- **When**: 2026-04-08T17:08 (launch 2)
- **What**: Both populations deadlocked at gen 1 — each processed 9 programs but sync hook needed min_progress >= 11 (baseline 1 + min_delta 10)
- **Category**: config mistake
- **Impact**: 4 runs stuck permanently. Required full restart.
- **Root cause**: Default `min_delta=10` in `adversarial_coevo_ss.yaml` exceeded `max_mutations_per_generation=8`. Smoke test masked it with `++pre_step_hook.min_delta=1` override.
- **Fix applied**: Changed default `min_delta` from 10 to 1 in `adversarial_coevo_ss.yaml`
- **Systemic fix needed**: YES — preflight_check.py should validate `min_delta <= max_mutations_per_generation`

### Issue 0: Missing evolution=steady_state override
- **When**: 2026-04-08T17:00 (launch 1)
- **What**: Config dumps showed standard `EvolutionEngine` instead of `SteadyStateEvolutionEngine`
- **Category**: config mistake
- **Impact**: Runs used generational engine instead of steady-state. Required restart.
- **Root cause**: `evolution=steady_state` not included in `extra_overrides` in experiment.yaml
- **Fix applied**: Added `evolution=steady_state` to all 4 runs' extra_overrides
- **Systemic fix needed**: YES — pipeline=adversarial_coevo_ss should imply steady_state engine, or preflight should warn
