# Issues Log — hover/steady-state-validation

Track ALL errors, crashes, unexpected behavior, and manual interventions during this experiment.

---

### 11. Treatment runs produce 0 mutations — wrong model_name after rebase on main
- **When**: treatment relaunch #6 (2026-03-27 ~09:20)
- **What**: All LLM mutation calls fail with `404: The model 'deepseek/deepseek-v3.2' does not exist`. Mutation loop spins producing 0 mutants. Runs alive but making no progress.
- **Category**: config mistake
- **Impact**: ~90 min wasted. Treatment runs had to be killed and refllushed again.
- **Root cause**: Rebase on main picked up `config/constants/endpoints.yaml` which changed `model_name` default from `Qwen3-235B-A22B-Thinking-2507` to `deepseek/deepseek-v3.2`. Our servers still serve Qwen. Control runs (launched before rebase) use the old config. Treatment runs (launched after rebase) got the new default.
- **Fix applied**: Added explicit `model_name=Qwen3-235B-A22B-Thinking-2507` override to treatment run launch commands.
- **Systemic fix needed**: YES — when rebasing mid-experiment, always check if `model_name` default changed. The experiment.yaml `model_name` field should be used as an explicit override in launch.sh, not relying on Hydra defaults.

### 10. Treatment runs crash at epoch 0 — `dag_timeout` AttributeError (launch #4)
- **When**: launch #4 (2026-03-27 ~02:15)
- **What**: S3 and S4 crashed with `'SteadyStateEngineConfig' object has no attribute 'dag_timeout'` during epoch 0 refresh.
- **Category**: run crash
- **Impact**: 3rd consecutive treatment run crash. Required another full restart.
- **Root cause**: During stash pop after rebasing on PR #135, `git checkout --theirs` resolved the conflict by keeping our OLD drain code (which referenced `self.config.dag_timeout`), instead of PR #135's scoped drain. The `--theirs` flag refers to the stash, not the branch we rebased onto.
- **Fix applied**: `git checkout origin/worktree-perf+steady-state-throughput -- steady_state.py` to get PR #135's version, then re-applied only the initial epoch counter fix.
- **Systemic fix needed**: YES — when resolving stash conflicts, verify which side is "ours" vs "theirs". For stash pop, `--theirs` = stashed changes, `--ours` = current branch. This is the opposite of merge/rebase convention.

### 9. Treatment runs crash at epoch 0 — `dag_timeout` AttributeError (launch #3)
- **When**: launch #3 (2026-03-27 ~01:03)
- **What**: Same as #10 — S3 and S4 crashed with `dag_timeout` AttributeError.
- **Category**: run crash
- **Impact**: Full restart needed. ~40 min of compute wasted per treatment run.
- **Root cause**: Our drain timeout fix (`self.config.dag_timeout + 600.0`) referenced a field that doesn't exist on `SteadyStateEngineConfig`. Was introduced in the fix for issue #5 and should have been superseded by PR #135's scoped drain.
- **Fix applied**: Same as #10.
- **Systemic fix needed**: YES — same as #10.

### 8. Watchdog crash on launch — NFS import latency + launch.sh nohup race
- **When**: launch #3 (2026-03-27 ~21:18)
- **What**: Watchdog started by launch.sh died immediately. `pgrep` found no running watchdog. Had to restart manually.
- **Category**: watchdog
- **Impact**: ~5 min manual intervention to detect and restart watchdog.
- **Root cause**: Likely NFS import latency (~15s for fresh Python process) combined with launch.sh not verifying watchdog PID survived. The launch.sh fires nohup and moves on without checking.
- **Fix applied**: Manual restart with explicit NO_PROXY env vars.
- **Systemic fix needed**: YES — launch.sh should verify watchdog PID is alive after a short sleep (e.g., `sleep 20 && kill -0 $WD_PID`).

### 7. Watchdog plots: only one plot uploaded per cycle
- **When**: launch #2 (2026-03-26 ~18:30)
- **What**: `generate_plot()` returned a single Path, so only the fitness_vs_time plot was uploaded. The comparison plot was generated but never uploaded to GitHub.
- **Category**: watchdog
- **Impact**: PR comments missing comparison plot. Minor — data still available locally.
- **Root cause**: `generate_plot()` returned the last successful plot path, not both. `upload_plot_to_github` only called once.
- **Fix applied**: Changed `generate_plot()` to return `list[Path]`, upload loop iterates over all plots with unique suffixes.
- **Systemic fix needed**: YES — backport to `_template/run_watchdog.py`.

### 6. Watchdog MODEL DRIFT false positive with `mutation_url=None`
- **When**: launch #1 and #2 (2026-03-26)
- **What**: Watchdog logged "MODEL DRIFT" for all 4 runs every cycle when using `llm=balanced` (no per-run mutation URL).
- **Category**: watchdog
- **Impact**: Noisy logs, watchdog died on first launch requiring manual restart.
- **Root cause**: `check_model_identity(None, model)` fails when `mutation_url` is `None`. The check didn't guard against None URLs.
- **Fix applied**: Added `if run_spec.mutation_url` guard before calling `check_model_identity`.
- **Systemic fix needed**: YES — backport to `_template/run_watchdog.py`.

### 5. Drain timeout (600s) force-releasing valid in-flight programs
- **When**: Epochs 0-2, runs S3 and S4 (2026-03-26 22:31–00:07)
- **What**: `_drain_in_flight()` had a 600s (10min) timeout. HoVer DAGs can take 8-15 min. Timed out and force-released slots for programs still evaluating.
- **Category**: run crash
- **Impact**: Programs' results lost for that epoch (recovered next epoch via archive refresh). 2 drain timeouts per treatment run. Wasted compute.
- **Root cause**: Hardcoded 600s timeout too short for HoVer chain. Should scale with `dag_timeout`.
- **Fix applied**: Changed to `self.config.dag_timeout + 600.0` (= 7800s).
- **Systemic fix needed**: YES — done in `steady_state.py`.

### 4. Stage timeout (3000s) too short for HoVer chain
- **When**: Runs S3 and S4 (2026-03-26 ~23:00–00:07)
- **What**: `CallValidatorFunction` timed out after 3000s for some programs. Also happened in control runs.
- **Category**: config mistake
- **Impact**: Programs DISCARDED. Symmetric across control/treatment, so experiment validity preserved. Minor compute loss.
- **Root cause**: 3000s inherited from previous experiments, insufficient for pathological HoVer programs.
- **Fix applied**: Bumped `stage_timeout` to 3600s in experiment.yaml.
- **Systemic fix needed**: YES — update CONTEXT.md to recommend 3600s for HoVer.

### 3. `engine:total_generations` not initialized for steady-state runs
- **When**: Launch #1 (2026-03-26 ~18:23)
- **What**: `status.py` showed `?` for generation count on treatment runs because Redis key wasn't written until first epoch refresh.
- **Category**: tool bug
- **Impact**: Monitoring confusion. Had to manually set via `redis-cli`.
- **Root cause**: `SteadyStateEvolutionEngine.run()` didn't persist initial epoch counter at startup.
- **Fix applied**: Added `save_run_state()` at start of `run()`. Committed as `88380b6`.
- **Systemic fix needed**: YES — done in `steady_state.py`.

### 2. Preflight SHA mismatch after rebase
- **When**: Pre-launch #2 (2026-03-26 ~17:30)
- **What**: Preflight check #17 failed — `test_set_sha256` in experiment.yaml didn't match after rebase added chain LB import to test.py.
- **Category**: skill bug
- **Impact**: Blocked launch. Had to manually update SHA in experiment.yaml.
- **Root cause**: Rebase changed test.py (new import from chain LB commit `51c4a3e`), but experiment.yaml SHA wasn't updated.
- **Fix applied**: Recomputed SHA and updated manifest.
- **Systemic fix needed**: YES — preflight should suggest the correct SHA when mismatch detected, not just report failure.

### 1. Git rebase merge conflicts in hover chain files
- **When**: Pre-launch rebase (2026-03-26 ~17:00)
- **What**: 4 hover chain files had merge conflicts between `random.choice` (main) and `EndpointPool` (our branch).
- **Category**: git
- **Impact**: Delayed launch by ~15 min.
- **Root cause**: Chain LB implemented differently on main vs our branch. Normal merge conflict.
- **Fix applied**: `git checkout --theirs` for all 4 files.
- **Systemic fix needed**: NO — normal merge conflict resolution.
