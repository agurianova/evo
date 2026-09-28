# Treatment Verification Reference

## Overview

Treatment verification ensures the experiment's independent variable is actually applied at runtime, not silently falling back to default behavior. This runs BEFORE the smoke test (Step 10) so that `treatment_checks` can be validated during smoke (Step 11).

## Treatment-Verifier Agent Workflow

The `treatment-verifier` agent:

1. Reads `01_design.md` and `experiment.yaml`
2. Identifies the treatment variable (what differs between control and treatment runs)
3. Traces the treatment's code path through config resolution, pipeline construction, and runtime execution
4. Identifies **silent fallback modes** — places where a misconfigured treatment silently reverts to default behavior
5. Classifies each fallback as CRITICAL (experiment-invalidating) or MINOR
6. Proposes `treatment_checks` for experiment.yaml and `diagnose.py` checks

## Feedback Loop

```
10a. Run treatment-verifier agent
      |
10b. Review findings
      |
      +-- All CRITICAL fallbacks covered? --> YES --> proceed
      |
      +-- NO --> 10c. Add checks, re-run agent
```

**10a.** Run the agent. It reports silent fallback modes and coverage gaps.

**10b.** Verify:
- Every `extra_override` maps to a real config key (not silently ignored by Hydra)
- Every CRITICAL silent fallback has a detection mechanism (Check 12 override verification, Check 13 treatment checks, or log/Redis evidence)
- `treatment_checks` are written to experiment.yaml

**10c.** If uncovered CRITICAL fallbacks exist:
1. Add the check to `diagnose.py` (in `check_treatment_applied()`)
2. Re-run the `treatment-verifier` agent to confirm coverage
3. Run `/run-tests` if new code was added

## treatment_checks Schema (experiment.yaml)

```yaml
treatment_checks:
  # Redis keys that MUST exist after a successful run
  redis_key_pattern:
    - "{prefix}:metrics:history:program_metrics:valid_frontier_fitness"
    - "{prefix}:some_treatment_specific_key"

  # Log patterns that MUST appear in run logs (treatment is active)
  log_pattern_present:
    - "Loading custom prompts from"
    - "Feedback pipeline enabled"

  # Log patterns that MUST NOT appear (treatment fallback detected)
  log_pattern_absent:
    - "Falling back to default prompts"
    - "No feedback data available, skipping"

  # Fitness uniformity check (optional) — catches broken validators
  fitness_uniformity:
    max_identical_fraction: 0.8  # fail if >80% of fitness values identical
```

## Two-Tier Verification System

| Tier | Preflight Check | What it verifies |
|---|---|---|
| Check 12 | Override verification | `extra_overrides` appear in Hydra cfg dump |
| Check 13 | Declarative treatment checks | `treatment_checks` from experiment.yaml (redis_key_pattern, log_pattern_present/absent, fitness_uniformity) |

Check 12 catches config-level misapplication. Check 13 catches runtime-level silent fallbacks. Both run during the smoke test.

## Common Silent Fallback Modes

1. **prompts_dir missing from one pipeline block** — mutation uses custom prompts, but insights/lineage use defaults (or vice versa)
2. **Config group override silently ignored** — typo in override name means Hydra uses default
3. **Feature flag not propagated** — treatment flag set in config but not read by the relevant stage
4. **Chain server URL mismatch** — treatment run hits the wrong chain server (same model, different config)
5. **Prompt fetcher prefix mismatch** — `prompt_fetcher.prompt_prefix` doesn't match the prompt evolution run's Redis prefix
