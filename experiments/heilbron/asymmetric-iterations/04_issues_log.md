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

### 2026-04-14 — G/D generation divergence: 2-2.5x (post-experiment bug diagnosis)

- **When**: Discovered in post-experiment analysis of completed runs
- **What**: G (Constructor) reached max_gen=8-12 (513-670 total programs) while D (Improver) reached gen=17-29 (425-565 total programs). Observed divergence ratio: 2.1-2.4x. This is asymmetric co-evolution, but the divergence is **buggy** — sync hook should enforce ~1:1 epoch parity.
- **Category**: core bug
- **Impact**: Scientific data is valid (both arms reached SOTA or above), but the mechanism is misaligned. D's stagnation hypothesis cannot be fairly tested when D has 2.5x more generations to explore. Affects the "arms race asymmetric?" narrative in the paper.
- **Root cause**: `SteadyStateEvolutionEngine._ingest_batch()` published `programs_processed` to Redis after every batch (lines 472-475). `ProgressBasedSyncHook` reads this counter to determine when opponent advanced enough to unblock. With incremental publication, the faster population (D, which generates programs faster in most runs) read intermediate counter values between epochs and unblocked multiple times per opponent epoch. Example: G produces 8 mutations per epoch + ~20 from drain + ~5 post-drain = ~33 programs per epoch. Each ~8 programs allows D to unblock once, so D advances ~4 epochs while G advances 1.
  - Step 3a in `_epoch_refresh()` already publishes `programs_processed` before the sync hook (to break MainRunSyncHook deadlock). The incremental publication in `_ingest_batch()` was added earlier and became redundant once step 3a was introduced.
- **Fix applied**: Removed the incremental publication from `_ingest_batch()` (steady_state.py lines 469-475). Now `programs_processed` is published ONLY at epoch boundaries (step 3a). This forces the sync hook to read epoch-level snapshots only, enforcing ~1:1 epoch advancement ratio. Verified: all existing tests pass (25 steady-state tests + 13 progress sync tests).
- **Systemic fix needed**: YES — add a mock-based integration test that verifies two concurrent populations with `ProgressBasedSyncHook` maintain ~1:1 epoch parity. Added `test_enforces_1_to_1_epoch_advancement()` to `tests/adversarial_pipeline/test_progress_sync.py`. Consider documenting in `docs/protocol/` that incremental counter publications break adversarial sync and should never be added without careful analysis.

### 2026-04-13 — MetricsTracker crash + frontier staleness + D>>G desync (restart #3)

- **When**: Discovered at hour ~6 checkpoint. A1_G frontier=0.01097 but archive had programs with actual_fitness=0.03554 (103% SOTA).
- **What**: Three related bugs: (1) MetricsTracker crashed on KeyError for programs without `iteration` in metadata — killed entire tracker async task, so frontier never updated. (2) Only 9 programs tracked for A1_G/A2_G vs 496 for C1_G. (3) D runs at gen 43 while G at gen 17 — 2.5x desync.
- **Category**: run crash | config mistake
- **Impact**: ~17 G generations + ~43 D generations of compute lost. Frontier metrics unreliable (stale at gen 0). Requires full restart.
- **Root cause**:
  1. `CompositionInjectionHook` creates composed Programs without setting `iteration` in metadata. `MetricsTracker._process_program()` did `program.metadata["iteration"]` which threw KeyError. Since the tracker ran as a single async task with no per-program error isolation, one bad program killed the entire tracker.
  2. `programs_total_count=9` because tracker died early; only programs processed before the first composition-injected program were counted.
  3. `min_delta=1` in `ProgressBasedSyncHook` was too permissive — D processes 1 program and unblocks, while G is still mid-epoch. D runs many more iterations per wall-clock hour.
- **Fix applied**:
  1. Promoted `iteration` to a typed `Program` field (`iteration: int = Field(default=0, ge=0)`) — impossible to create a Program without it. Added `model_validator` for backwards compat with existing Redis blobs. Updated all 9 call sites.
  2. Added per-program `try/except` in `MetricsTracker._drain_once()` and resilient `run()` loop — one bad program logs and continues instead of killing the tracker.
  3. Changed `min_delta: 1` → `min_delta: 8` (= `max_mutations_per_generation`) so sync hook blocks until opponent processes a full epoch's worth of programs.
  4. Also: mypy fix (`aclose`→`close` in dg_tracker.py), lint fix (unused var in run_watchdog.py).
- **Systemic fix needed**: YES — (1) is now fixed by design (field cannot be missing). (2) error isolation is now in place. (3) `min_delta` should default to `max_mutations_per_generation` rather than 1 in asymmetric configs.

### 2026-04-13 ~00:00 UTC — MainRunSyncHook deadlock in SteadyState (restart #2)

- **When**: ~20 min after restart #1 launch. All 8 runs stuck at gen=0 with 9-16 programs processed.
- **What**: All 8 runs deadlocked at first epoch boundary. MainRunSyncHook (inherited from adversarial_coevo) waits for opponent's `engine:total_generations > last_seen`. But `total_generations` is incremented at step 9 of `_epoch_refresh()`, AFTER the hook call at step 4. Both populations enter epoch refresh simultaneously, both call the hook, both wait forever.
- **Category**: config mistake
- **Impact**: ~20 min of compute lost (gen 0 programs only, no scientific value). Full restart required.
- **Root cause**: `adversarial_asymmetric.yaml` inherits from `adversarial_coevo` which defines `pre_step_hook: MainRunSyncHook`. This hook uses generation-based sync designed for the generational engine (turn-based G/D). In SteadyState, both populations run concurrently and enter epoch refresh in parallel, creating a circular wait on `total_generations`.
- **Fix applied**: Overrode `pre_step_hook` in `adversarial_asymmetric.yaml` to use `ProgressBasedSyncHook` (from `gigaevo.adversarial.sync`). This hook reads `engine:programs_processed` which is published at step 3a (BEFORE the hook call), breaking the circular dependency. Same approach used by `adversarial_coevo_ss.yaml`. Commit: `e69021c0`.
- **Systemic fix needed**: YES — any pipeline inheriting from `adversarial_coevo` and used with `evolution=steady_state` will deadlock. Either: (a) `adversarial_coevo` should detect engine type and select hook automatically, or (b) `steady_state.yaml` should default `pre_step_hook: null` and require explicit opt-in.

### 2026-04-12 ~20:36 UTC — Full experiment restart (protocol deviation)

- **When**: After initial launch ran gen 0-9 under broken treatment
- **What**: Experiment restarted from scratch — all 8 runs killed, Redis DBs 1-8 flushed, re-launched with fixes
- **Category**: config mistake | run crash
- **Impact**: ~9 generations of compute lost (all 8 runs). Data destroyed. No archive taken (gen progress was under broken treatment so data was not scientifically valid).
- **Root cause**: Multiple issues in initial launch:
  1. `experiment.yaml` missing `evolution=steady_state` override — runs launched with generational engine instead of steady-state
  2. `experiment.yaml` missing `population_role=constructor/improver` overrides — asymmetric pipeline couldn't differentiate G vs D roles
  3. `experiment.yaml` missing `post_step_hook=${composition_injection_hook}` for A1_G/A2_G — Arm A composition treatment never fired
  4. `generate_launch.py` produced unquoted `${composition_injection_hook}` — bash expanded it as empty shell variable
- **Fix applied**:
  1. Added `evolution=steady_state` to all 8 runs' `extra_overrides` in experiment.yaml (commit `5a36157d`)
  2. Added `population_role=constructor/improver` to G/D runs respectively (commit `3fd6bfce`)
  3. Added `'post_step_hook=${composition_injection_hook}'` to A1_G and A2_G only (commit `3fd6bfce`)
  4. Single-quoted all Hydra interpolation refs in generated launch.sh (commit `fdd3dae1`)
  5. Watchdog updated for dual-plot monitoring: arms-race + comparison with actual_fitness vs SOTA
  6. Full restart: kill all processes, flush DBs 1-8, regenerate launch.sh, re-launch
- **Systemic fix needed**: YES — `generate_launch.py` should auto-quote any `extra_overrides` containing `${}` Hydra interpolation syntax. Also, preflight_check.py should verify that `population_role` is set for adversarial_asymmetric pipeline runs.

### 2026-04-12 ~20:00 UTC — Orphan processes repopulated Redis after first flush

- **When**: During restart, after first `gigaevo flush --db 5 6 7`
- **What**: DBs 5, 6, 7 showed non-zero keys after flush because orphan worker processes from a prior experiment repopulated them
- **Category**: infra issue
- **Impact**: Required second flush pass; ~5 minutes delay
- **Root cause**: PIDs 3622539, 3622601, 3622722 were leftover exec_runner workers from a previous experiment that were still writing to DBs 5-7
- **Fix applied**: Second `gigaevo flush` killed the orphan workers before flushing
- **Systemic fix needed**: NO — `gigaevo flush` already kills workers, but the timing window between kill and flush allowed one write cycle. This is a known race condition that self-resolves on second attempt.

### 2026-04-12 ~20:30 UTC — Watchdog Telegram photo 400 error

- **When**: First watchdog cycle (hour 1)
- **What**: Second plot upload (comparison plot) to Telegram failed with HTTP 400 Bad Request
- **Category**: watchdog
- **Impact**: Minor — arms-race plot was sent successfully, only comparison plot failed. Text summary was sent.
- **Root cause**: Under investigation. Possibly the comparison plot file was too large or had an encoding issue.
- **Fix applied**: None yet — watchdog continues with next cycle
- **Systemic fix needed**: DONE — `_send_photo()` now falls back to `sendDocument` (50 MB limit) on HTTP 400. See KF-06 in PATTERNS.md.
