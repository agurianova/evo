# Replication: Structured Improver-Constructor Information Flow (v2)

**Date**: 2026-04-14
**Status**: Replication of heilbron/asymmetric-iterations (PR #204)
**Replicates**: heilbron/asymmetric-iterations (same design, bug fixes applied)

---

## 1. Rationale for Replication

heilbron/asymmetric-iterations (PR #204) produced promising results (both arms >= 105% SOTA) but suffered from multiple infrastructure bugs that compromised data quality:

1. **G/D generation divergence** (KF-05): D ran 2-2.5x more generations than G due to incremental `programs_processed` publication in `SteadyStateEvolutionEngine._ingest_batch()`. Fix: removed incremental publication (commit e803d396).
2. **MetricsTracker crashes** (KF-04): Programs from `CompositionInjectionHook` lacked `iteration` field, crashing the metrics tracker. Fix: promoted `iteration` to typed Program field.
3. **MainRunSyncHook deadlock** (KF-01): `adversarial_asymmetric` inherited wrong sync hook for steady-state engine. Fix: overrode to `ProgressBasedSyncHook`.
4. **Missing config overrides** (KF-02, KF-03): `population_role`, `evolution=steady_state`, and shell-expanded Hydra interpolations. Fix: generate_launch.py quoting + experiment-implement defaults.
5. **min_delta=1 too permissive** (KF-05): Sync hook allowed single-program unblock. Fix: `min_delta=${max_mutations_per_generation}`.
6. **Telegram photo upload** (KF-06): Large plots failed sendPhoto. Fix: fallback to sendDocument.

All 6 fixes are merged to main. No code changes needed -- this is a pure replication with fixed infrastructure.

### v1 Results Summary

| Arm | Best fitness | Mean fitness | % SOTA | Max Gen reached (G) |
|-----|-------------|-------------|--------|---------------------|
| A (Composition) | 0.03648 | 0.03413 | 105.8% | 12 |
| C (Gradient-in-prompt) | 0.03650 | 0.03494 | 105.8% | 9 |
| **Cross-arm delta** | 0.00002 | 0.00081 | -- | -- |

**v1 issues**: Runs never reached max_gen=50 (G stuck at 8-12 due to sync bug). K=1 inner iterations (amended from K=5). Multiple restarts in first 24h.

**v2 expectation**: With sync hook fix, runs should reach max_gen=50. This provides the first complete dataset for this design.

---

## 2. Design (identical to v1)

Refer to `experiments/heilbron/asymmetric-iterations/01_design.md` for the full design document. Key parameters reproduced below.

### Research Question

Does structured Improver-Constructor information flow -- where the Improver (D) sees Constructor (G) source code as a dynamic task description -- improve Constructor actual_fitness on the Heilbronn N=11 triangle problem, and does the feedback mode (Composition vs Gradient-in-prompt) affect the outcome?

### Hypotheses

**H0**: Neither feedback mode changes Constructor actual_fitness relative to historical baseline (0.03449).
**H1**: At least one feedback mode produces Constructor actual_fitness meaningfully different from baseline.

### Independent Variable

**Feedback mode** (2 levels): Composition (Arm A) vs Gradient-in-prompt (Arm C).

Both arms share: D sees G source code, K=1 inner iterations, persistent D archive, `archive_reeval=false`.

### Effect-size Thresholds

| Constructor actual_fitness | Interpretation |
|---|---|
| >= 0.03649 (baseline + 0.002) | STRONG POSITIVE |
| >= 0.03449 and < 0.03649 | POSITIVE |
| within 0.001 of baseline | NULL |
| < 0.03249 (baseline - 0.002) | NEGATIVE |

---

## 3. Run Design Table

### Arm A: Composition -- 2 pairs

| Run | Label | DB | Role | feedback_mode |
|-----|-------|----|------|---------------|
| 1 | A1_G | 1 | Constructor (G) | composition |
| 2 | A1_D | 2 | Improver (D) | composition |
| 3 | A2_G | 3 | Constructor (G) | composition |
| 4 | A2_D | 4 | Improver (D) | composition |

### Arm C: Gradient-in-prompt -- 2 pairs

| Run | Label | DB | Role | feedback_mode |
|-----|-------|----|------|---------------|
| 5 | C1_G | 5 | Constructor (G) | gradient_in_prompt |
| 6 | C1_D | 6 | Improver (D) | gradient_in_prompt |
| 7 | C2_G | 7 | Constructor (G) | gradient_in_prompt |
| 8 | C2_D | 8 | Improver (D) | gradient_in_prompt |

**Total**: 8 runs, DBs 1-8.

---

## 4. Controlled Variables

All values identical to v1. See `experiments/heilbron/asymmetric-iterations/01_design.md` Section 5.

Key values: `max_generations=50`, `max_mutations_per_generation=8`, `max_elites_per_generation=8`, `mutation_mode=rewrite`, `model_name=Qwen3-235B-A22B-Thinking-2507`, `archive_reeval=false`, `inner_iterations=1`.

---

## 5. Stop Criteria

**Hard stop**: `max_generations=50` (outer).

**Futility at gen 25**: If both replicates of an arm have Constructor actual_fitness < 0.03000, stop that arm early.

**Minimum completion**: >= 1/2 pairs per arm must reach gen 40.

---

## 6. Statistical Test

Descriptive comparison vs pre-registered effect-size thresholds (N=2 per arm insufficient for formal testing). Cross-arm Welch's t-test (alpha=0.10, descriptive only).

---

## 7. Monitoring

```yaml
watchdog:
  plugin: adversarial
  sentinel_value: -1.0
  plot_metrics: [actual_fitness]
  poll_interval_s: 3600
  alert_thresholds:
    invalidity_rate: 0.75
    stagnation_window: 10
    generation_gap_threshold: 5
```

Uses new WatchdogEngine with:
- Plugin-based plot generation (arms-race + comparison)
- Telegram + GitHub PR dual-channel notifications
- Redis heartbeat + checkpoint markers
- Stagnation detection
- Auto-restart on crash (max_restarts=3)
- Plot retry logic with matplotlib figure cleanup

---

## 8. Treatment Verification

Same checks as v1 Section 13. Key additions for v2:
- **Sync hook verification**: G and D `engine:total_generations` must remain within 1 of each other at gen 5 (smoke test). This was the primary bug in v1.
- **No incremental programs_processed publication**: Verify `_ingest_batch` does not publish `programs_processed` (code already fixed).

---

## 9. Deviations from v1

| Change | v1 | v2 | Rationale |
|--------|----|----|-----------|
| Sync hook | Buggy (KF-05) | Fixed (e803d396) | G/D parity |
| MetricsTracker | Crashed on missing iteration (KF-04) | Resilient | Continuous monitoring |
| min_delta | 1 | 8 (= max_mutations_per_generation) | Epoch-level sync |
| generate_launch.py | Unquoted Hydra refs (KF-02) | Single-quoted | Correct overrides |
| WatchdogEngine | Legacy run_watchdog.py | New plugin-based engine | Structured monitoring |

---

*Ready for pre-registration.*
