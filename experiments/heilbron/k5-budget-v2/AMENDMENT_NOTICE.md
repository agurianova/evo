# Amendment Notice — heilbron/k5-budget-v2 silent-treatment bug + relaunch

**Date:** 2026-04-17 10:34 UTC
**Severity:** Caught in-flight, no scientific data lost.

---

## What happened

The first v2 launch (10:26 UTC, PIDs 2283482-2283489) was running with **K=1** (n_opponents=1, source_prompt_k=1) instead of the K=3 that the experiment is named after. The hypothesis depends on K=3 — without it the experiment is meaningless.

Caught at the 25-min health check: log line `[AsymmetricPipeline] role=constructor feedback=composition n_opp=1 source_prompt_k=1 dg_tracker=yes` instead of the expected `n_opp=3 source_prompt_k=3`.

## Root cause

`gigaevo/experiment/launch_generator.py:_build_run_cmd` only passes a hand-picked subset of `contract.config.extra` keys through as Hydra overrides. `n_opponents`, `source_prompt_k`, `archive_reeval`, `inner_iterations`, `significant_change` are silently dropped if you only set them under `extra:`. The sandbox worked because its launch.sh was hand-written.

## Fix

1. SIGTERM old PIDs + watchdog (graceful 12s drain).
2. Added `n_opponents=3` and `source_prompt_k=3` to every arm's `extra_overrides` (16 new entries).
3. Flushed Redis DBs 1-8, released DB claims.
4. Relaunched.

## Verification

New PIDs **2291939-2291946** (runs) + **2292454** (watchdog), all alive at 10:34:34 UTC. All 8 logs show `n_opp=3 source_prompt_k=3 dg_tracker=yes`. K=3 confirmed loaded.

## What scientific data was lost

**None.** The K=1 runs only got through cold-start seed evaluation. No mutations completed, no archive entries beyond the seed, no checkpoints recorded.

## Systemic followup (not blocking the experiment)

`_build_run_cmd` should either:
- pass through ALL keys from `extra:` as Hydra overrides, or
- warn loudly when unrecognized keys are dropped.

Treatment-verifier agent should grep launch.sh for the specific overrides the design depends on before allowing launch (already in design language: "K=3" → grep for `n_opponents=3`).

This will be filed as a separate code-fix task after the experiment completes.
