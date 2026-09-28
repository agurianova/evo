# exp: heilbron/adversarial-dynamic-updates

**Status**: 🟢 Complete
**Branch**: `exp/heilbron/adversarial-dynamic-updates`
**Tracking issue**: #195

## Design

See `experiments/heilbron/adversarial-dynamic-updates/01_design.md` for full design.

## Runs

| Label | DB | Condition | Pipeline | PID |
|-------|----|-----------|----------|-----|
| SOFT_RE_A | 1 | Cell SOFT_RE: G=soft quality+resistance, re-eval ON — Constructor (Pop A soft) | adversarial_coevo_feedback | 856366 |
| SOFT_RE_B | 2 | Cell SOFT_RE: G=soft quality+resistance, re-eval ON — Improver (Pop B soft) | adversarial_coevo_feedback | 856367 |
| SOFT_C_A | 3 | Cell SOFT_C: G=soft quality+resistance, re-eval OFF — Constructor (Pop A soft) | adversarial_coevo_feedback | 856368 |
| SOFT_C_B | 4 | Cell SOFT_C: G=soft quality+resistance, re-eval OFF — Improver (Pop B soft) | adversarial_coevo_feedback | 856369 |
| GAN_RE_A | 5 | Cell GAN_RE: G=strict GAN pure resistance, re-eval ON — Constructor (Pop A GAN) | adversarial_coevo_feedback | 856370 |
| GAN_RE_B | 6 | Cell GAN_RE: G=strict GAN pure resistance, re-eval ON — Improver (Pop B soft) | adversarial_coevo_feedback | 856371 |
| GAN_C_A | 7 | Cell GAN_C: G=strict GAN pure resistance, re-eval OFF — Constructor (Pop A GAN) | adversarial_coevo_feedback | 856372 |
| GAN_C_B | 8 | Cell GAN_C: G=strict GAN pure resistance, re-eval OFF — Improver (Pop B soft) | adversarial_coevo_feedback | 856373 |

## Checkpoints

| Gen | Time | Notes |
|-----|------|-------|
| 2 | 2026-04-09T22:34:03.664893+00:00 | Restart 3 (post higher_is_better fix). All 8 runs alive, gen=1, 0% invalidity. Diagnose: all HEALTHY (1 MINOR each = insufficient history at gen 1, expected). |
| 17 | 2026-04-10T01:33:39.502905+00:00 | Checkpoint 2. SOFT_C deadlock (gen 0-7) resolved via ProgressBasedSyncHook. All 8 runs alive. Diagnose: all HEALTHY/MINOR. SOFT_RE_B and GAN_RE_B show fitness stagnation (hypothesis-relevant). No stopping rule violations. |
| 21 | 2026-04-10T02:21:50.480425+00:00 | Checkpoint 3. All 8 PIDs alive. Diagnose: GAN_RE_B MAJOR flagged but DAG errors frozen at 9 (1.94%, historical from cold-start, not growing). SOFT_RE_B/GAN_RE_B stagnation ongoing (hypothesis-relevant). GAN_C_A/B leading at gen=30-31. No stopping rule violations. |
| 30 | 2026-04-10T05:37:53.747249+00:00 | Checkpoint 4. Futility stopping rule triggered at gen=30 (H1 gap=0.012>>0.005 threshold). GAN_RE_A actual_fitness=0.01379 vs control avg=0.03020. Researcher action required. GAN_C_B CRITICAL false positive (sync wait). All 8 PIDs alive. |
| 32 | 2026-04-10T06:24:49.742112+00:00 | Checkpoint 5. GAN pairs in extended sync wait (all 4 since ~04:21-04:41 UTC, self-resolving via 7200s timeout). SOFT pairs progressing normally (SOFT_RE gen=40-41, SOFT_C gen=27-28). Futility stopping rule still pending researcher decision (GAN_RE_A actual_fitness=0.01379, H1 gap=0.012>>0.005). Mid-run analyst flagged R5 frozen fitness and R1 lagging. All 8 PIDs alive. |

## Baseline

Reference: `heilbron/adversarial-v2` (mean=0.03464, metric=actual_fitness)

## Archives

_(pending)_

