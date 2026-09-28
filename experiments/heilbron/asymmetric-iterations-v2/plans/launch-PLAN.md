# Launch Plan: heilbron/asymmetric-iterations-v2

**Generated**: 2026-04-14
**Experiment**: heilbron/asymmetric-iterations-v2
**Branch**: exp/heilbron/asymmetric-iterations-v2
**PR**: #206

## Overview

8 runs across 2 arms, all on LiteLLM proxy `http://10.232.30.185:4000/v1` with model `Qwen3-235B-A22B-Thinking-2507`.

| Label | Role | DB | Condition |
|-------|------|----|-----------|
| A1_G  | Constructor | 1 | Arm A (Composition), pair 1 |
| A1_D  | Improver    | 2 | Arm A (Composition), pair 1 |
| A2_G  | Constructor | 3 | Arm A (Composition), pair 2 |
| A2_D  | Improver    | 4 | Arm A (Composition), pair 2 |
| C1_G  | Constructor | 5 | Arm C (Gradient-in-prompt), pair 1 |
| C1_D  | Improver    | 6 | Arm C (Gradient-in-prompt), pair 1 |
| C2_G  | Constructor | 7 | Arm C (Gradient-in-prompt), pair 2 |
| C2_D  | Improver    | 8 | Arm C (Gradient-in-prompt), pair 2 |

Pipeline: `adversarial_asymmetric` for all runs.

## Known Failure Checks

| KF ID | Description | Status | Mitigation in this experiment |
|-------|-------------|--------|-------------------------------|
| KF-01 | adversarial pipeline missing `evolution=steady_state` | FIXED (e69021c0) | All runs have `evolution=steady_state` in extra_overrides ✓ |
| KF-02 | `${}` Hydra interpolation refs unquoted in launch.sh | FIXED (fdd3dae1) | `generate_launch.py` now single-quotes; verify launch.sh ✓ |
| KF-03 | Missing `population_role` in adversarial_asymmetric runs | FIXED | All runs have `population_role=constructor/improver` ✓ |
| KF-04 | CompositionInjectionHook programs missing `iteration` field | FIXED | `iteration` promoted to typed field with `default=0` ✓ |
| KF-05 | `min_delta=1` with asymmetric runs causes D/G desync | FIXED | Uses `${max_mutations_per_generation}` Hydra ref ✓ |
| KF-06 | Telegram sendPhoto 400 on large plots | FIXED | Falls back to sendDocument ✓ |

## Task Checklist

### Task 1 — Gate check (Step 0)
- [x] `gigaevo manifest gate implemented` exits 0
- **Criteria**: Must exit 0, status=implemented

### Task 2 — Infrastructure verification (Step 1)
- [ ] Verify LiteLLM proxy at `10.232.30.185:4000` is reachable
- [ ] Confirm server assignment matches `infrastructure.yaml`
- **Criteria**: Server IP matches `litellm_proxy.host` in infrastructure.yaml ✓

### Task 3 — Preflight check (Step 2, hard gate)
- [ ] Run `preflight_check.py --experiment heilbron/asymmetric-iterations-v2`
- [ ] Exit code = 0
- [ ] Log any warnings
- **Criteria**: Exit code 0 required. CRITICAL failures block launch.

### Task 4 — Config dump (Step 3)
- [ ] Dump resolved config for all 8 runs via `--cfg job`
- [ ] Verify: pipeline=adversarial_asymmetric, problem.name, llm_base_url, model_name
- [ ] Researcher confirms configs look correct
- [ ] Save as `cfg_run_<label>.txt`
- **Criteria**: Researcher approval required before proceeding.

### Task 5 — Environment capture (Steps 4-5a)
- [ ] Query LiteLLM proxy `/models` endpoint → `server_models_at_launch.txt`
- [ ] `pip freeze` → `environment_freeze.txt`
- [ ] Commit both files (pre-launch reproducibility anchor)
- **Criteria**: Commit exists before any run starts.

### Task 6 — Researcher launch confirmation (Step 6)
- [ ] Present captured artifacts to researcher
- [ ] Await explicit "yes" confirmation
- **Criteria**: Human gate (D-04) — no auto-launch.

### Task 7 — Launch via launch.sh (Steps 7-8)
- [ ] Execute `bash experiments/heilbron/asymmetric-iterations-v2/launch.sh`
- [ ] Log launch event to `04_issues_log.md`
- [ ] Verify all 8 PIDs alive
- **Criteria**: All 8 runs have live PIDs.

### Task 8 — Set status to running (Step 9)
- [ ] `gigaevo manifest update launch.time ...`
- [ ] `gigaevo manifest update launch.commit ...`
- [ ] `gigaevo manifest set status running`
- **Criteria**: Only after PIDs verified.

### Task 9 — Watchdog + crons (Steps 10-10b)
- [ ] Start watchdog via `gigaevo watchdog`
- [ ] Verify 10s survival
- [ ] Record watchdog PID in experiment.yaml
- [ ] Create anomaly detector cron (every 2h, 7-day expiry)
- [ ] Create checkpoint cron (every 4h, 14-day expiry)
- [ ] Record both cron IDs in experiment.yaml
- **Criteria**: Watchdog alive, both cron IDs recorded.

### Task 10 — PR description + commit (Steps 11-12)
- [ ] `gigaevo manifest pr-description --push`
- [ ] Commit launch artifacts

### Task 11 — Completion verification (Step 13)
- [ ] `gigaevo manifest gate running`
- [ ] All 8 PIDs present and alive in manifest
- **Criteria**: COMPLETE only when gate passes and all PIDs verified.
