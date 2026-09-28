# Implementation Plan: heilbron/adversarial-repro-v1

**Generated**: 2026-04-19
**Design**: `experiments/heilbron/adversarial-repro-v1/01_design.md`
**Codebase map**: `experiments/heilbron/adversarial-repro-v1/codebase_map.md` (feasibility: YELLOW)
**Scope**: produces all artifacts needed for smoke test (Steps 5a through 10b of experiment-implement).
Smoke test, status update, and final commit are separate skill steps OUTSIDE this plan.

---

## Plan summary

- **Tasks**: 11 total (0 code, 4 config, 3 script, 4 verification)
- **Files touched**: `experiments/heilbron/adversarial-repro-v1/experiment.yaml`, `experiments/heilbron/adversarial-repro-v1/launch.sh` (generated), `experiments/heilbron/adversarial-repro-v1/03_plan.md` (amendment note only)
- **No Python code changes** — pipeline (`config/pipeline/heilbron_repro_v1.yaml`) and frozen problem dirs (`problems/heilbron_repro_v1/pop_{a,b}`) are already committed from the prior design-phase PRs.
- **KF mitigations addressed**:
  - KF-01 (generational→steady-state drift): `evolution=steady_state` in every run's `extra_overrides`
  - KF-02 (Hydra interpolation in CLI overrides): escape `\${...}` when referenced in `extra_overrides`
  - KF-03 (missing `population_role` per run): explicit on every run
  - KF-07 (sync-hook deadlock): structurally impossible at `drift_cap=100000` (repro-v1's treatment)

---

## Amendment note (must be logged before Config tasks)

The design doc §12.3 instructs `opponent_redis_prefix=heilbron/adversarial-repro-v1/pop_b`. The established convention across all prior heilbron adversarial experiments (v1 through v2) is `prefix == problem_name` (namespacing by problem dir, NOT by experiment dir). Deviating from this convention would:
1. Break the Redis watchdog plugin's opponent-matching logic (it expects `pop_a` / `pop_b` suffixes)
2. Decouple the prefix from the dataset provenance (checksums in `dataset_snapshot.json` are keyed by problem path)
3. Make cross-experiment key inspection harder

**Amendment A1** (to be added to `03_plan.md` §Amendments before Config task C1):
> Redis key prefix pinned to `heilbron_repro_v1/pop_{a,b}` (matching `problem.name`), not `heilbron/adversarial-repro-v1/pop_{a,b}` as literally written in §12.3 of 01_design.md. Rationale: consistency with v1/v2 convention (`prefix == problem_name`); the experiment directory namespace is tracked in Redis by `experiments:heilbron/adversarial-repro-v1:*` watchdog keys, not by program/metrics prefix. Treatment verification check #1 (`drift_cap=100000` in startup log) is unaffected. Checks #2 and #3 (opponent_redis_prefix values) are updated to `heilbron_repro_v1/pop_{a,b}`.

---

## Config tasks

### C0 — Log Amendment A1 in 03_plan.md

**File**: `experiments/heilbron/adversarial-repro-v1/03_plan.md`
**Action**: append Amendment A1 text under the existing "Amendments" section (line 185).
**Acceptance**: `grep -A1 "Amendment A1" experiments/heilbron/adversarial-repro-v1/03_plan.md` prints the amendment block.

### C1 — Fill `runs[]` with 8 entries in experiment.yaml

**File**: `experiments/heilbron/adversarial-repro-v1/experiment.yaml`
**Action**: fill `contract.runs` with 8 entries following the layout from 01_design.md §6, substituting:
- `pipeline: heilbron_repro_v1` (not `adversarial_asymmetric`)
- `problem_name: heilbron_repro_v1/pop_{a,b}` (frozen problem dir)
- `prefix: heilbron_repro_v1/pop_{a,b}` (per Amendment A1)

Per-run common fields:
- `chain_url: null`
- `mutation_url: http://10.232.30.185:4000/v1`
- `model_name: Qwen3-235B-A22B-Thinking-2507`

**G runs (A1_G, A2_G, C1_G, C2_G)**:
- `role: constructor`
- `extra_overrides` includes: `evolution=steady_state`, `stopper=max_generations`, `opponent_redis_db=<paired_d_db>`, `opponent_redis_prefix=heilbron_repro_v1/pop_b`, `feedback_mode=<composition|gradient_in_prompt>`, `population_role=constructor`, `post_step_hook=\${composition_injection_hook}` (KF-02: escaped `\$`)

**D runs (A1_D, A2_D, C1_D, C2_D)**:
- `role: improver`
- `extra_overrides` includes: `evolution=steady_state`, `stopper=max_generations`, `opponent_redis_db=<paired_g_db>`, `opponent_redis_prefix=heilbron_repro_v1/pop_a`, `feedback_mode=<composition|gradient_in_prompt>`, `population_role=improver`

| Run | DB | Prefix | Problem | Opp DB | Feedback | Role |
|-----|----|--------|---------|--------|----------|------|
| A1_G | 1 | pop_a | pop_a | 2 | composition | constructor |
| A1_D | 2 | pop_b | pop_b | 1 | composition | improver |
| A2_G | 3 | pop_a | pop_a | 4 | composition | constructor |
| A2_D | 4 | pop_b | pop_b | 3 | composition | improver |
| C1_G | 5 | pop_a | pop_a | 6 | gradient_in_prompt | constructor |
| C1_D | 6 | pop_b | pop_b | 5 | gradient_in_prompt | improver |
| C2_G | 7 | pop_a | pop_a | 8 | gradient_in_prompt | constructor |
| C2_D | 8 | pop_b | pop_b | 7 | gradient_in_prompt | improver |

**Acceptance**:
```bash
gigaevo -e heilbron/adversarial-repro-v1 manifest get runs --format json | jq 'length'  # → 8
gigaevo -e heilbron/adversarial-repro-v1 manifest get runs --format json | jq '[.[] | select(.role == "constructor")] | length'  # → 4
```

### C2 — Fill servers / custom_env / tools

**File**: `experiments/heilbron/adversarial-repro-v1/experiment.yaml`
**Action**:
- `contract.servers: [10.232.30.185]` (LiteLLM proxy — single entry, no separate chain servers)
- `contract.custom_env: {OPENAI_API_KEY: sk-gigaevo}`
- `contract.tools: []` (Heilbronn needs no external tools)

**Acceptance**:
```bash
gigaevo -e heilbron/adversarial-repro-v1 manifest get contract.servers --format json | jq '. | length'  # → 1
gigaevo -e heilbron/adversarial-repro-v1 manifest get contract.custom_env.OPENAI_API_KEY  # → sk-gigaevo
```

### C3 — Add `treatment_checks` block

**File**: `experiments/heilbron/adversarial-repro-v1/experiment.yaml`
**Action**: add top-level `treatment_checks:` block matching 01_design.md §12. Verified by smoke-test gate in Step 11.

```yaml
treatment_checks:
  log_pattern_present:
    - "\\[ProgressBasedSyncHook\\] Init.*drift_cap=100000"
    - "pipeline: heilbron_repro_v1"
  log_pattern_absent:
    - "drift_cap exceeded"
```

Per-role log patterns (`[SourceCodeInjection] showing 1 programs` on D only) are role-specific and handled by the alignment check, not the smoke-test regex block (which sees one log at a time).

**Acceptance**: `yq '.treatment_checks.log_pattern_present | length' experiments/heilbron/adversarial-repro-v1/experiment.yaml` → 2.

---

## Script tasks

### S1 — Generate launch.sh

**Action**: `gigaevo -e heilbron/adversarial-repro-v1 launch --generate-script`
**Acceptance**:
- File `experiments/heilbron/adversarial-repro-v1/launch.sh` exists, is executable
- `grep -c "python run.py" launch.sh` → 8 (one per run)
- `grep -c "pipeline=heilbron_repro_v1" launch.sh` → 8
- `grep -c "evolution=steady_state" launch.sh` → 8
- `grep -c "redis.db=" launch.sh` → 8 with DBs 1–8
- **NO_PROXY includes the LiteLLM proxy IP**: `grep -E 'export NO_PROXY=.*10\.232\.30\.185' launch.sh` → match (proxy IP must be present so calls to `http://10.232.30.185:4000/v1` bypass the system Squid proxy)
- `grep -c "llm_base_url=\"http://10.232.30.185:4000/v1\"" launch.sh` → 8

### S2 — Skip run_test_eval.sh

**Rationale**: `problem.has_test_set: false` (Heilbronn is optimization, no test split).
**Acceptance**: `problem.has_test_set` in experiment.yaml is `false`; no run_test_eval.sh needed.

### S3 — Watchdog via CLI (no run_watchdog.py)

**Rationale**: The `experiments/_template/run_watchdog_v2.py` is DEPRECATED. The `watchdog:` section in `experiment.yaml` (already filled in design phase) is invoked directly by `gigaevo -e <exp> watchdog`. No per-experiment watchdog Python file is needed.
**Acceptance**: `yq '.control_plane.watchdog.plugin' experiments/heilbron/adversarial-repro-v1/experiment.yaml` → `adversarial`.

---

## Verification tasks

### V1 — Run `/run-tests` for changed code scope

**Action**: invoke `/run-tests` skill. Since no Python changes are made in this experiment-implement run (pipeline yaml and problem dirs were committed during the design phase), scope will be determined by `git diff --name-only HEAD` — likely config-only. If any `gigaevo/` paths appear, run the mapped test paths; otherwise run `tests/adversarial_pipeline/` as the blueprint requires.
**Acceptance**: lint clean, tests passing.

### V2 — Treatment verification (treatment-verifier agent)

**Action**: invoke the `treatment-verifier` agent with `experiments/heilbron/adversarial-repro-v1/01_design.md` as input.
**Expected verifier output**: confirms that each treatment knob (`drift_cap=100000`, `n_opponents=1`, `source_prompt_k=1`, `feedback_mode`, `population_role`) reaches the intended code path and is not silently falling back to a default. Repeat until no CRITICAL fallbacks remain.
**Acceptance**: verifier verdict is PASS; `gigaevo -e heilbron/adversarial-repro-v1 manifest update lifecycle.treatment_verification.completed true` applied.

### V3 — Implementation alignment check (implementation-aligner agent)

**Action**: invoke the `implementation-aligner` agent. It diffs `git diff main...HEAD` against 01_design.md and emits ALIGNED or MISALIGNED.
**Common gaps to watch for**:
- Design specifies treatment-only override X, but the override is absent from `runs[].extra_overrides` → add it
- Codebase_map names entry point A for the treatment, but the implementing agent modified B → revert and redo
**Acceptance**: verdict ALIGNED. `lifecycle.treatment_verification.alignment_check_completed = true`.

### V4 — Dry-run launch preview (pin contract)

**Action**: `gigaevo -e heilbron/adversarial-repro-v1 launch --dry-run` writes `LAUNCH_PREVIEW.md`.
**Acceptance**:
- Status `PASS`, `0 failed` pin assertions
- Every pinned row shows `PASS ✓` for all 8 runs
- `drift_cap: 100000` row wins from `pipeline: heilbron_repro_v1` (via the pipeline yaml), not from task-group defaults
- `n_opponents: 1`, `source_prompt_k: 1`, `inner_iterations: 1`, `archive_reeval: false` all PASS
- Commit LAUNCH_PREVIEW.md: `rtk git commit -m "preflight(heilbron/adversarial-repro-v1): launch preview — pin contract verified"`

---

## Post-plan steps (NOT in this plan)

These are executed after plan approval and completion, as separate skill steps:

- Step 11: Smoke test (3 generations on A1_G, DB 1)
- Step 11 tail: flush smoke DB
- Step 12: Watchdog 60s survival test
- Step 13: `gigaevo manifest update status implemented`
- Step 14: Final commit + GitNexus scope check
- Step 15: Completion check (`manifest gate implemented`)
