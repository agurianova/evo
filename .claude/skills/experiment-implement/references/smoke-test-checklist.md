# Smoke Test Checklist

## Purpose

The smoke test runs ONE run for 3 iterations (`max_mutants=3`) to verify the implementation works end-to-end before committing to a full experiment launch.

## What to Verify

### a) No errors in log
- Zero `ERROR` or `CRITICAL` lines in `smoke.log`
- A few `WARNING` lines are acceptable (e.g. retry warnings)

### b) Redis keys exist
- `{prefix}:run_state` has `engine:snapshot` set (JSON blob; its `programs_processed` field is the progress counter)
- `{prefix}:metrics:history:program_metrics:valid_frontier_fitness` has entries
- `{prefix}:program:*` keys exist (programs were stored)

### c) Fitness values are plausible
- At least one non-zero fitness value
- If all values identical across 3 iterations, the validator may be broken (warning, not hard fail for 1 iteration)

### d) Custom prompts loaded (if applicable)
- Log contains evidence of custom prompt loading (`prompts_dir`, `loaded prompt`, `custom prompt`)
- If no custom prompt log lines and the experiment uses custom prompts, this is a FAIL

### e) Treatment checks (HARD GATE)
Uses `treatment_checks` from experiment.yaml:

| Check type | What it verifies | Failure means |
|---|---|---|
| `redis_key_pattern` | Expected Redis keys exist | Treatment data not being written |
| `log_pattern_present` | Expected log lines appear | Treatment code path not executing |
| `log_pattern_absent` | Forbidden log lines absent | Treatment silently falling back to default |
| `fitness_uniformity` | Fitness values not all identical | Validator may be broken or treatment not applied |

### f) Post-smoke cleanup
- Flush the smoke DB with `gigaevo flush --db <db> --confirm`
- Record smoke test completion in experiment.yaml (`smoke_test.completed = true`)

## Common Smoke Test Failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Zero fitness, no errors | Wrong pipeline for validate.py return type | Check pipeline selection (see config-patterns.md) |
| `ModuleNotFoundError` | Missing import in new code | Add the import, re-run |
| `KeyError` in validate.py | Changed return dict keys but not pipeline | Align validate.py return with pipeline expectations |
| All fitness identical | Validator always returns same value | Check validate.py logic, ensure test data is being read |
| Treatment check fails | Treatment override not applied | Re-run treatment-verifier, check Hydra config resolution |
| `ConnectionError` to chain server | Chain server not running or wrong URL | Verify `chain_url` in experiment.yaml, check server status |
| Log shows "Falling back to default" | prompts_dir misconfigured | Ensure prompts_dir in BOTH pipeline YAML blocks |

## Smoke Test Config Overrides

This override keeps the smoke test fast while still exercising the full pipeline:

```
max_mutants=3
```

Use the first run's config from experiment.yaml as the base (prefix, db, pipeline, problem_name). This ensures the smoke test exercises the actual experiment configuration.
