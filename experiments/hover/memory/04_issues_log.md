# Issues Log — hover/memory (PR #161)

## Session 1 (2026-04-03)

### Bug #1: Ideas tracker MemoryCard.aliases type mismatch (FIXED)
- **Date**: 2026-04-03 ~12:00 UTC
- **Symptom**: `normalize_memory_card()` receives dict with `aliases: list[dict]` from ideas_tracker, but MemoryCard.aliases was typed as `list[str]`, causing Pydantic validation error
- **Root cause**: ideas_tracker.data_components.RecordCardExtended stores version history as `list[dict[str, dict[...]]]`, not list of strings
- **Fix**: Changed `MemoryCard.aliases: list[str]` → `MemoryCard.aliases: list[Any]` in models.py (commit 4eb099c on main, merged to exp/hover-memory)
- **Status**: ✅ FIXED

### Bug #2: _card_type() crashes on Pydantic models (FIXED)
- **Date**: 2026-04-03 ~13:30 UTC
- **Symptom**: `load_memory_cards()` returns list of Pydantic models (AnyCard), but `_card_type(card)` tried `card.get("category")` causing AttributeError: 'MemoryCard' object has no attribute 'get'
- **Root cause**: Pydantic models don't have .get() method; need to check type first
- **Fix**: Added `isinstance(card, ProgramCard)` check before .get() calls in _card_type() (commit c933b94 on main)
- **Testing**: Added main() loop simulation tests in test_memory_e2e_pipeline.py
- **Status**: ✅ FIXED + TESTED

### Bug #3: Lint errors from mypy branch merge (FIXED)
- **Date**: 2026-04-03 ~14:30 UTC
- **Symptom**: Pre-commit hook blocked push due to:
  - F401: `yaml` imported but unused in runtime_config.py:11
  - F821: undefined `warnings` in optuna/stage.py:724
- **Root cause**: 
  - runtime_config.py: `import yaml` used `yaml` name, but code uses `_yaml` variable, never assigned
  - optuna/stage.py: used `warnings.catch_warnings()` without importing warnings
- **Fix**: 
  - Changed `import yaml` → `import yaml as _yaml` (line 11)
  - Added `import warnings` (line 17)
- **Status**: ✅ FIXED + PUSHED to main + merged to exp/hover-memory

### No OpenRouter rate limit issues observed
- Date: 2026-04-03, ideas_tracker running for ~6m50s at 54/273
- Analyzer LLM calls to google/gemini-3-flash-preview (OpenRouter) working steadily
- No JSON decode errors or rate limit 429 responses seen
- Note: This is EXPECTED since we use legacy memory backend (`use_api: false`), not API backend

## Known Gotchas

### Ideas tracker is slow but NOT stalled
- Previous session: I killed ideas_tracker at ~10 min thinking it was stuck. It was actually at 39% and working fine.
- This session: Proceeding with full run. Expect ~45-60 min total from start to memory_bank file write.
- DO NOT interrupt early.

### Memory bank writes at END only
- ideas_tracker.save_card() appends to checkpoint during run (visible in Redis)
- But memory_bank/*.json files are written at trainer.final_save() on completion
- Checking file count before completion will show 0 files — this is normal

### Phase B launch blocking on memory_bank existence
- launch_phase_b.sh checks `if [ ! -d "$MEMORY_BANK" ]` but NOT file count
- Script will launch even if memory_bank/ exists but is empty
- Fixed: wait_and_launch_phase_b.sh does verify file count > 0

## Monitoring

- **Ideas tracker**: PID 1088683, started ~14:45 UTC, expected completion ~15:50 UTC
- **Phase B monitor**: PID 1092493, auto-waits and launches Phase B when ready
- **Monitor log**: experiments/hover/memory/logs/phase_b_monitor.log

## Session 2 (2026-04-04)

### Bug #4: memory_provider not wired from Hydra config into EvolutionContext (CRITICAL, FIXED)
- **Date**: 2026-04-04 ~05:30 UTC
- **Symptom**: All MemoryContextStage calls completed in 0.0s for ALL runs (including treatment R3/R4). No MemorySelectorAgent initialization logs anywhere. Treatment variable was effectively inactive.
- **Root cause**: All 13 pipeline config files (e.g. `config/pipeline/structural_metrics.yaml`) created `EvolutionContext` without passing `memory_provider: ${memory_provider}`. The `EvolutionContext.memory_provider` field defaults to `NullMemoryProvider`, so all runs used no-op memory regardless of `+memory=local` override. Additionally, `config/config.yaml` didn't include a `memory` config group default, so `${memory_provider}` wouldn't resolve unless `+memory=...` was explicitly passed.
- **Fix**:
  1. Added `- memory: none` to `config/config.yaml` defaults
  2. Added `memory_provider: ${memory_provider}` to `evolution_context` block in all 13 pipeline configs
  3. Updated `launch.sh` to use `memory=local` (not `+memory=local`) for treatment runs R3/R4
- **Impact**: Previous Phase B launch (2026-04-03 22:22 UTC) ran ~10 gens with NO memory — data invalidated, Redis flushed, experiment restarted
- **Systemic fix needed**: Yes — `generate_launch.py` should support per-run Hydra overrides from experiment.yaml (e.g. `extra_overrides` field per run)
- **Status**: ✅ FIXED, experiment relaunched at 2026-04-04 05:50 UTC

### Restart #1: Phase B relaunch with memory_provider fix
- **Date**: 2026-04-04 05:50 UTC
- **Reason**: Bug #4 — treatment variable not active
- **Actions**: Killed PIDs 1284969-1284972, watchdog 1286566, flushed DBs 4-7, relaunched
- **Verification**: Logs confirm `[SelectorMemoryProvider] Creating MemorySelectorAgent` and `[MemoryContextStage] Selected 3 card(s)` for treatment runs. Control runs show no memory activity. Fix confirmed working.

### Bug #5: Wrong engine config — used generational instead of steady-state (FIXED)
- **Date**: 2026-04-04 06:15 UTC
- **Symptom**: Experiment was using default `EvolutionEngine` (generational MAP-Elites) instead of `SteadyStateEvolutionEngine` with 3D MAP-Elites topology. Missing `evolution=steady_state`, `scheduling=lpt_chain`, `algorithm=topology_3d_ret` overrides.
- **Root cause**: experiment.yaml `config` section and run entries didn't include the extra Hydra overrides needed to replicate hover/no-deep-retrieval's dynamic arms (the best-performing configuration).
- **Fix**: Added `extra_overrides` per run in experiment.yaml: `evolution=steady_state`, `scheduling=lpt_chain`, `algorithm=topology_3d_ret` for all runs. Treatment runs also get `memory=local`, `checkpoint_dir`, `namespace`. Updated timeouts to match (stage_timeout=3000, dag_timeout=7200).
- **Impact**: Previous 2 launches (~10 gens generational, ~2 gens generational) ran with wrong engine config — data invalidated.
- **Systemic fix needed**: experiment.yaml template should prompt for engine type, scheduling, algorithm choices.
- **Status**: ✅ FIXED, experiment relaunched at 2026-04-04 06:29 UTC

### Restart #2: Relaunch with correct steady-state + topology_3d_ret config
- **Date**: 2026-04-04 06:29 UTC
- **Reason**: Bug #5 — wrong engine configuration
- **Actions**: Killed PIDs 1347578-1347581, watchdog 1348398, flushed DBs 4-7, updated experiment.yaml with extra_overrides, regenerated launch.sh, relaunched
- **Verification**: Config dumps confirm `SteadyStateEvolutionEngine`, `topology_3d_ret`, `lpt_chain` for all runs. R3/R4 additionally show `SelectorMemoryProvider`.
