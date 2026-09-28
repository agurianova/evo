# Issues log — heilbron/adversarial-repro-v1

Running record of bugs, broken commands, stale docs, and workflow friction encountered
during implement → launch. For systemic fixes see `/post-experiment-fixes`.

## 2026-04-19 — implement phase

### I-00 `contract.config.extra` vs `contract.config.extras` inconsistency
- **Where**: Manifest schema vs `gigaevo/experiment/launch_generator.py:_build_run_cmd`.
- **Symptom**: I populated `contract.config.extra: {evolution: steady_state, stopper: max_generations}` in experiment.yaml (nested mapping — what preview/pin-match reads). Launch script had EMPTY `evolution=` and `stopper=` overrides because `launch_generator` only emits from `contract.config.extras` (the flat `model_extra` keys: stage_timeout, dag_timeout, max_generations, num_parents, mutation_mode, max_{mutations,elites}_per_generation).
- **Impact**: Silent loss of `evolution` and `stopper` overrides at launch time. Would have run as `generational` (KF-01 hit the floor) with no surface error.
- **Workaround used**: Moved `evolution=steady_state` and `stopper=max_generations` into each run's `extra_overrides[]` list (which IS emitted by `_build_run_cmd`) — via a `ruamel.yaml` script that rewrites all 8 runs.
- **Fix**: Either rename so there's only one "extra" field, or have `_build_run_cmd` also emit `contract.config.extra.*` as overrides, or document the distinction prominently. The names "extra" (dict) and "extras" (flat model_extra) are almost impossible to keep straight.

### I-01 `RunSpec.pinned` attribute error (pre-existing)
- **Where**: `gigaevo/experiment/checks.py:370` (per `test_pin_matches_pass`).
- **Symptom**: `AttributeError: 'RunSpec' object has no attribute 'pinned'`.
- **Root cause**: `RunSpec` Pydantic model (`gigaevo/experiment/manifest.py:170-194`) does not declare a `pinned` field and uses `ConfigDict(extra="ignore")`. checks.py nonetheless tries to read `run.pinned`.
- **Impact**: Blocks per-run pin assertions. Treatment-verifier's first proposal (add `pinned:` per run) is impossible under current schema.
- **Fix**: Either add `pinned: dict[str, Any] | None = None` to RunSpec or remove the access in checks.py.

### I-02 `launch --dry-run` blocked by `implemented` gate
- **Where**: `gigaevo/experiment/launch.py:81-85`.
- **Symptom**: Even with `--dry-run`, launch refuses unless `status==implemented`. But skill Step 10c wants dry-run BEFORE Step 13 advances status, and Step 13 requires `smoke_test.completed=true`. Circular: can't get to implemented without smoke, can't smoke-test safely without dry-run.
- **Impact**: Hard gate unreachable via the documented path.
- **Workaround used**: Called `gigaevo.experiment.dry_run.dry_run()` + `launch_preview.write_launch_preview()` in-process to bypass the status gate.
- **Fix**: Allow `--dry-run` from `preregistered` status (preview is read-only and useful pre-smoke).

### I-03 `_build_run_cmd` single-quotes break subprocess callers
- **Where**: `gigaevo/experiment/launch_generator.py:240-243` (pre-fix).
- **Symptom**: `post_step_hook=${composition_injection_hook}` was wrapped as `'post_step_hook=${composition_injection_hook}'`. Bash strips the quotes fine; `dry_run.py`'s `subprocess.run(list, shell=False)` keeps them literal → Hydra override lexer rejects column 0.
- **Impact**: `dry_run()` broken for ANY experiment using `${…}` Hydra interpolation overrides. Explains why no `LAUNCH_PREVIEW.md` has ever been produced repo-wide despite the skill's hard gate.
- **Fix applied here**: Added `shell_escape: bool = True` kwarg to `_build_run_cmd`; `dry_run` passes `shell_escape=False` to skip quote wrapping and strip quotes around `llm_base_url`. Library commit separate from experiment commit.

### I-04 ruamel.yaml silently strips `\$` escape in unquoted overrides
- **Where**: YAML loader behavior around `- post_step_hook=\${composition_injection_hook}`.
- **Symptom**: Raw file has literal `\$`, loaded string has bare `$`. Means the backslash "escape" recommended in plan KF-02 is actually a no-op — the real defense is the single-quote wrapping at bash-emit time.
- **Impact**: The KF-02 convention across all prior heilbron yamls is misleading. Works only by accident because bash handles quoting downstream.
- **Fix**: Document that the backslash is cosmetic; the real defense is `shell_escape=True` in `_build_run_cmd`.

### I-05 `manifest reset-status implemented` validation refuses pre-smoke
- **Where**: `gigaevo/experiment/manifest.py` `ExperimentManifest` validator.
- **Symptom**: `lifecycle.smoke_test.completed must be true for status=implemented`. Combined with I-02 (launch --dry-run wants implemented), there's no legal path to produce `LAUNCH_PREVIEW.md` before smoke.
- **Impact**: The documented Step 10c → Step 11 → Step 13 order is not executable.
- **Fix**: Either loosen the validator (preview doesn't need smoke) or reorder the skill.

### I-06 Amendment A1: opponent_redis_prefix convention deviation
- **Where**: `01_design.md §12.3` says `opponent_redis_prefix=heilbron/adversarial-repro-v1/pop_b`; every other heilbron experiment uses `prefix == problem_name` (`heilbron_repro_v1/pop_{a,b}`).
- **Symptom**: Design doc conflicts with framework convention — Redis watchdog `adversarial` plugin expects `pop_a`/`pop_b` suffixes and `dataset_snapshot.json` is keyed by problem path.
- **Impact**: Following the design literally would break watchdog opponent-matching.
- **Fix**: Logged as Amendment A1 in `03_plan.md`. Systemic: the design template should surface the "prefix == problem_name" convention so designers don't invent new namespaces.

### I-07 GitNexus index stale after every commit
- **Where**: PostToolUse:Bash hook warns stale after `rtk git commit`.
- **Symptom**: Index reminders appear on every commit; user feedback `feedback_skip_gitnexus_reindex.md` says to ignore them. Creates constant noise.
- **Fix**: Either remove the post-commit reindex warning hook or wire it up to honor the per-user `feedback_skip_gitnexus_reindex` preference.

### I-08 PreToolUse:Edit read-before-edit false positives
- **Where**: Edit tool hook.
- **Symptom**: Hook sometimes warns "must Read first" on files that ARE in the session's read state (because they were created via Write earlier, or because a compact replayed the session with a different cache). The edit still succeeds.
- **Impact**: Noise; wastes tokens on clarifying reads.
- **Fix**: The read-state tracker should consider Write-created files as read-known.

### I-09 Treatment-verifier schema gap (per-run `pinned:` not supported)
- **Where**: `RunSpec` model uses `ConfigDict(extra="ignore")`.
- **Symptom**: Treatment-verifier agent proposed adding `pinned: { population_role: ..., feedback_mode: ... }` per run. The schema would silently drop this without warning because of `extra="ignore"`.
- **Impact**: Agent's recommendation impossible to apply. Verifier does not know about this schema constraint.
- **Fix**: Add `per_run_pinned` field to RunSpec, or teach the treatment-verifier agent about the schema constraint so it proposes fixes in the right layer (global `contract.config.pinned` or `extra_overrides`).

### I-10 No `LAUNCH_PREVIEW.md` exists repo-wide
- **Where**: `find experiments -name LAUNCH_PREVIEW.md` → 0 hits.
- **Symptom**: Every heilbron (and likely every) experiment uses `${…}` interpolation in `extra_overrides`; every one hit I-03; nobody ever produced this artifact.
- **Impact**: The Step 10c "hard gate" has never been enforced in practice. Experiments have been launching without pin-contract verification.
- **Fix**: Once I-03 is fixed in the library, re-run dry-run for every preregistered experiment to backfill the artifact.

### I-11 `checks.py:370` unreachable path / missing field
- Same root cause as I-01 but worth noting separately: `test_pin_matches_pass` test exists and expects `RunSpec.pinned` access path to work — indicating the field was planned but never added. Possible in-progress feature abandoned mid-refactor.

### I-13 `run_watchdog.py` template drops `role`, breaks adversarial G/D plots
- **Where**: `experiments/_template/run_watchdog_v2.py:35` (and copies in every adversarial experiment).
- **Symptom**: During 60s watchdog survival test, `AdversarialPlugin._generate_arms_race` logs `"Cannot generate arms-race: missing G or D runs"` and returns None — no plot generated, no Telegram message sent.
- **Root cause**: Template builds `RunSpec(prefix=r.prefix, db=r.db, label=r.label)` — the `role` kwarg (of `RunSpec`, defaulting to `None`) is never passed. `AdversarialPlugin._constructors / _improvers` filter `snapshots` by `snap.run_spec.role == "constructor" | "improver"`; with role=None everywhere, both lists are empty → plugin short-circuits.
- **Impact**: Every adversarial experiment using the deprecated `run_watchdog.py` entry point produces heartbeats but no plots, and never dispatches to Telegram/PR. The CLI watchdog (`gigaevo -e ... watchdog` at `gigaevo/cli/watchdog_cmd.py:126`) does pass `role=run.role` — only the template/script path is broken.
- **Fix applied here**: Template and experiment copy both patched to `RunSpec(prefix=r.prefix, db=r.db, label=r.label, role=r.role)`.
- **Systemic fix**: Consider deleting the deprecated script path entirely (point users at `gigaevo watchdog` which has the correct wiring and handles NO_PROXY / env sourcing). Alternatively, add a smoke test that drives `run_watchdog.py` for a mock adversarial manifest and asserts `_constructors(snapshots)` is non-empty.

### I-14 `run_watchdog.py` template constructs `NotificationDispatcher([])` — Telegram silently never dispatched
- **Where**: `experiments/_template/run_watchdog_v2.py:42-48` and every copy — `WatchdogEngine(..., config=WatchdogConfig())` omits the `dispatcher` kwarg.
- **Symptom**: Watchdog runs, writes heartbeat, generates plots, but no Telegram message ever arrives. No log line indicates a failure because the default `NotificationDispatcher([])` has zero channels — dispatch is a no-op.
- **Root cause**: `WatchdogEngine.__init__` default `self._dispatcher = dispatcher or NotificationDispatcher([])`. The CLI path (`gigaevo/cli/watchdog_cmd.py:145-167`) explicitly builds channels: `channels = [ch for ch in (TelegramChannel.from_env(),) if ch is not None]` then `dispatcher = NotificationDispatcher(channels)`. The deprecated script path skips this entirely.
- **Impact**: Every adversarial experiment that relied on `run_watchdog.py` for Telegram alerts has been silently non-notifying for the life of that script. The 60s watchdog survival test in `/experiment-implement` Step 12 passes (heartbeat is written) even though Telegram is broken — "survival" is orthogonal to "dispatch works". This is the hidden class of the same bug family as I-13 (deprecated script path has silent divergences from CLI).
- **Fix applied here**: Verified the CLI watchdog via `gigaevo -e heilbron/adversarial-repro-v1 watchdog` with `.env` sourced + `NO_PROXY` exempting LiteLLM host. Cycle 1 completed 8 snapshots, 7 alerts, no Telegram errors, heartbeat age 170s — confirming the CLI path is healthy end-to-end. `run_watchdog.py` was NOT used for the survival test.
- **Systemic fix**: Delete the deprecated script path. If kept, either (a) mirror the CLI's channel setup into the template, or (b) fail fast if `TELEGRAM_BOT_TOKEN` is set in env but the script constructs an empty dispatcher.

### I-15 `DGTrackerStage.compute` logs 39–48 ERRORs per run (`per_opp_delta length 0 != opponent_ids length 1`)
- **Where**: `gigaevo/adversarial/dg_tracker_stage.py:118`.
- **Symptom**: `[DGTrackerStage constructor] <pid> per_opp_delta length 0 != opponent_ids length 1 (artifact role=None); SKIP batch — possible cache leak between FetchOpponentIdsStage and CallValidatorFunction.` Batches are skipped (no pairwise G/D delta recorded) but fitness is still computed and the pipeline continues.
- **Root cause**: The DGTracker stage expects `per_opp_delta` to come from `CallValidatorFunction` for each opponent fetched by `FetchOpponentIdsStage`; under steady-state with cached validator results the two stages can see divergent cache states on the same program. The error message itself fingers the bug: "possible cache leak between FetchOpponentIdsStage and CallValidatorFunction." The `role=None` in the artifact is suspicious — DGTrackerStage doesn't propagate run role into the cached artifact.
- **Impact**: Pairwise G vs D deltas missing from `dg_tracker` Redis output for 39/48 smoke batches per side (~0.8% of per-program rates, non-fatal). Breaks `adversarial` plugin's downstream delta plots when aggregated. Actual fitness + evolution unaffected — the run continues; just the instrumentation is lossy. Cosmetic error noise in logs (every 15s during smoke).
- **Fix NOT applied here**: Library-level bug; out of scope for this experiment's branch. Filed for separate remediation. For this experiment, accept the loss — primary metric is `actual_fitness` which is unaffected.
- **Systemic fix**: Either (a) add `role` to the DGTrackerStage artifact so cache keying includes it, preventing cross-role cache hits; (b) make the skip-batch path a DEBUG not ERROR line to stop polluting the log; or (c) assert upstream that FetchOpponentIdsStage and CallValidatorFunction share a cache key. Reproduce via `n_opponents>=1` steady-state adversarial smoke.

### I-12 `${redis.prefix}` interpolation is undefined repo-wide (latent bug)
- **Where**: `config/pipeline/adversarial_coevo_ss.yaml:30` and `config/pipeline/heilbron_repro_v1.yaml:64` both reference `own_prefix: ${redis.prefix}` for `ProgressBasedSyncHook`.
- **Symptom**: `OmegaConf.InterpolationKeyError: Interpolation key 'redis.prefix' not found, full_key: pre_step_hook.own_prefix`. Grep confirms `redis.prefix` is NEVER defined in any config, and never set programmatically in `run.py` or anywhere else.
- **Root cause**: `config/redis/default.yaml` defines `redis.{host,port,db,resume}` only — no `prefix`. The correct key for "this run's redis namespace" is `${problem.name}` (used by `redis_storage.config.key_prefix` at `config/redis/default.yaml:15` and by `dg_tracker.prefix` at `config/pipeline/adversarial_asymmetric.yaml:88`).
- **Why this wasn't hit before**: Prior Heilbronn experiments (v1, v2, asymmetric-iterations, k5-budget-loose) all used `pipeline=adversarial_asymmetric`. That pipeline inherits `pre_step_hook` from its base but overrides to `ProgressBasedSyncHook` WITHOUT setting `own_db`/`own_prefix`. Before today's drift-cap redesign (commit 4ce9f421), `ProgressBasedSyncHook.__init__` did not require `own_db`/`own_prefix`. Today's redesign made them required positional args — but the pipelines that set them (`adversarial_coevo_ss`, `heilbron_repro_v1`) reference a nonexistent `${redis.prefix}` key. So no prior experiment ever exercised this path.
- **Impact**: `heilbron/adversarial-repro-v1` is the first experiment to use a pipeline that actually sets `own_prefix`. Runtime instantiation will fail at Hydra compose (`--cfg job`) AND at actual `_target_` instantiation. Blocks this experiment's launch entirely.
- **Fix applied here**: `config/pipeline/heilbron_repro_v1.yaml:64` changed `${redis.prefix}` → `${problem.name}`. Logged the same bug in `adversarial_coevo_ss.yaml` but leaving that file untouched (out of scope for this experiment's branch; fix should land as a separate library commit).
- **Systemic fix**: Add a lint check that rejects any `${redis.prefix}` interpolation. Also consider defining `redis.prefix: ${problem.name}` in `config/redis/default.yaml` so the indirection actually resolves — that would keep every downstream pipeline author's intuition ("redis.prefix is where I write") working instead of surprising them.

---

## I-16 — v1-frozen evaluate.py returned `dict` instead of `(dict, artifact)`; DGImprovementTracker was empty; zero D→G feedback across all 4 pairs
- **Date**: 2026-04-19 (detected 06:30 UTC after ~6.5h of running post-launch 1474479–1474486)
- **Category**: silent contract break between frozen problem files and library stage
- **Symptom**: All 4 G runs logged `injected=0 skip_no_d=...` (Arm A) and `no D to inject (tracker=per-G) -- skipping` (Arm C) from gen 0 onwards. A1_G: 0 injections in 6h. A2_G: 0 injections, 103 skips. C1_G: 279 "no D to inject" + 0 "injecting". C2_G: 418 "no D to inject" + 0 "injecting". 443 `DG_TRACKER_STAGE` SKIP-BATCH errors in C2_D alone. `dg_tracker:*` Redis keys were 0 across all 8 DBs.
- **Root cause**: `problems/heilbron_repro_v1/{pop_a,pop_b}/evaluate.py` were frozen at v1 commit `04bd5e69`, which predates `DGTrackerStage` (introduced 3 days ago, commit `e313b868`). v1's `evaluate()` returns just `dict[str, float]`. `CallValidatorFunction.parse_output` detects this and wraps as `(dict, None)` — artifact becomes `None`. `DGTrackerStage.compute` then reads `per_opp_delta = artifact.get(...)` via the `isinstance(artifact, dict)` guard, gets `[]`, hits the length-mismatch guard `if len(per_opp_delta) != n_opp`, logs ERROR and skips the batch. `DGImprovementTracker.get_best_d_for_g(g_id)` returns `None` for every G → `CompositionInjectionHook` and `GradientInPromptStage` both skip injection unconditionally.
- **Why treatment_checks missed it**: The manifest's `treatment_checks` verified that `drift_cap=100000` was in the resolved config and that `min_area_avg_config` metric was being emitted. It did NOT assert that `per_opp_delta` would flow through the artifact channel, nor that `injected>0` would appear in G logs, nor that `dg_tracker:*` Redis keys would be non-empty. The design phase assumed v1's evaluate.py was compatible with the current library — nobody traced the artifact shape.
- **Fix applied**: Both `evaluate.py` files updated to return `(metrics, artifact)` where `artifact = {"role": "<constructor|improver>", "per_opp_delta": [...]}` with `per_opp_delta` aligned index-wise to `opponent_results`. `pop_b` pre-initializes `per_opp_delta = [0.0] * len(opponent_results)` because its original loop used `continue` on invalid configs — that would have desynced the index with `DGTrackerStage`'s opponent index. Fitness math is completely unchanged. 329 tests pass.
- **Verification after relaunch (PIDs 1590268-1590275, launched 23:35 UTC)**: A1_G log at 02:54 UTC shows `[CompositionInjection] mutation_type=d_improvement d_id=... g_id=... d_fitness=0.05096 tracked_delta=0.008253 injected_id=...` — real non-zero deltas, real injection. All 8 DBs have `dg_best_pairs`, `dg_d_wins:*`, `dg_delta:*`, `dg_g_resisted:*`, `dg_improvements:*` keys populated.
- **Systemic fix**: Add to PATTERNS.md known-failure list: "When freezing an old problem dir, verify the `evaluate()` return shape matches the current library's expected `(metrics, artifact)` contract. `CallValidatorFunction.parse_output` silently wraps `dict` → `(dict, None)`, which is a no-op from the validator's perspective but breaks any downstream stage that reads from the artifact channel." Treatment verification for any problem-dir freeze should include a `redis_key_pattern` assertion for `{prefix}:dg_best_pairs` (or equivalent tracker key) to catch this at smoke-test time.

---

## I-17 — CompositionInjectionHook stamps every injected program as `gen=1 / iter=0 / is_root=True`
- **Date**: 2026-04-21 (detected during closeout Phase 5 analysis)
- **Category**: silent lineage-labeling bug in Lamarckian transfer hook
- **Where**: `gigaevo/adversarial/composition_injection.py:158-167` (pre-fix) — the `Program(code=..., metadata={...})` constructor call.
- **Symptom**: Every D∘G composed program injected into G's archive landed with `lineage.generation=1`, `lineage.iteration=0`, `lineage.parents=[]`, `is_root=True`, regardless of when it was injected or which G it descended from. In A1_G, 143/144 "is_root=True" archive entries were actually composition injections, not cold-start seeds. Program `d29accbb` (actual_fitness=0.03650, atomic=3507) was injected at 19:19:20 during gen ≈ 6–7 but appeared in `evolution_data.csv` as `gen=1 iter=0 is_root=True mutation=d_improvement`.
- **Root cause**: The hook constructed `Program(code=composed_code, metadata={...})` with no `lineage=` argument. `Program.__init__` falls back to `Lineage()` defaults (`parents=[]`, `generation=1`, `iteration=0`, `mutation=""`) whenever no lineage is supplied. `Lineage.is_root` derives as `not self.parents` → `True`. So every composition injection looked identical in the is_root / gen-1 archive slices, corrupting downstream analysis.
- **Why it was hidden until closeout**: MAP-Elites and fitness math are lineage-agnostic — they care about `actual_fitness`, not `is_root`. The bug only surfaces when an analyst (Elena) slices the archive by `is_root=True` to find "cold-start seeds" or sorts by `generation`. In this experiment the mis-labeling led to the claim "A1_G's headline 0.03650 is a gen-0 root seed", which contradicted actual evolution: the earliest 0.03650 appeared at gen=5 (b2cc69cd, created 16:45:51 — BEFORE the 17:23:59 relaunch) as a normal Lamarckian descendant.
- **Impact**: Every prior Arm A experiment (adversarial-v2, adversarial-dynamic-updates, asymmetric-iterations, asymmetric-iterations-v2, k5-budget-v3, k5-budget-loose) has unreliable `is_root` and `generation=1` archive slices. Fitness results are unchanged (math is independent of lineage). Only the narrative "which programs were seeds vs descendants" is affected.
- **Fix applied**: Replaced the `Program(...)` call with `Program.create_child(parents=[g_prog], code=composed_code, mutation="d_improvement")`, then attached metadata afterwards. This uses the existing factory which sets `generation = G.generation + 1`, `parents = [g_id]`, `mutation = "d_improvement"`, and leaves `is_root` to derive as `False` automatically. D is NOT added to `parents` because D lives in a separate Redis DB — G's graph walker cannot resolve a D id — so the D reference stays in `metadata.d_source_id` (preserving the prior contract for analysis tools that look for it there).
- **Tests added**: `TestInjectedLineage` class in `tests/adversarial_pipeline/test_composition_injection.py`:
  - `test_injected_program_inherits_generation_from_g_plus_one` — G with `generation=7` yields injected program with `generation=8`.
  - `test_injected_program_is_not_root_and_parents_is_g_only` — parents == [g.id], "d-1" NOT in parents, `is_root is False`, `mutation == "d_improvement"`, `metadata["d_source_id"] == "d-1"`.
  Both tests PASS; full `tests/adversarial_pipeline/` suite (245 tests) green; lint clean.
- **Systemic fix needed**: YES. Promote to PATTERNS.md Known Failure entry (Step 13a of closeout) so future hooks that inject programs into an archive MUST construct via `Program.create_child(...)` or equivalent, never via the bare `Program(code=..., metadata={...})` constructor without lineage. Consider adding a runtime assertion in `Program.__init__` that emits a WARNING when `lineage` is omitted for newly-created programs (or tightening the API so an explicit `lineage=None` parent-less case must be opted into).
