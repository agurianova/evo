# Heilbron k5-budget-v2 — Launch Report

**Date:** 2026-04-17 ~10:26 UTC
**Branch:** `exp/heilbron/k5-budget-v2`
**Status:** RUNNING

---

## TL;DR

Live experiment `heilbron/k5-budget-v2` is up. 8 arms launched, all PIDs alive, watchdog spawned. This is the resurrected k5-budget hypothesis on the **fixed** heilbron_adversarial problem (smoothed `tanh` fitness + deterministic top-K HoF + cache_on edges + opponent_provider cache-refresh-on-miss), all changes validated by the F35 sandbox gate earlier today.

---

## Hypothesis (unchanged from k5-budget-loose)

The K=5 compute-budget asymmetry on the D side (Improver) combined with **loose G/D coupling** breaks the Improver stagnation observed in `heilbron/asymmetric-iterations-v2`. We test this against:

- 2 feedback modes: `composition` (Lamarckian cross-population transfer, Arm A) vs `gradient_in_prompt` (Baldwinian per-program hints, Arm B)
- 2 K budgets: K=3 (24 mutations/gen on D) vs K=5 (40 mutations/gen on D)

→ 4 cells × 2 populations = 8 concurrent runs.

---

## Live PIDs (2026-04-17 10:26 UTC)

| Arm | DB | PID | Pop | Feedback | K_d | Status |
|-----|----|-----|-----|----------|-----|--------|
| A3_G | 1 | 2283482 | constructor | composition | n/a | ALIVE |
| A3_D | 2 | 2283483 | improver    | composition | 24  | ALIVE |
| A5_G | 3 | 2283484 | constructor | composition | n/a | ALIVE |
| A5_D | 4 | 2283485 | improver    | composition | 40  | ALIVE |
| B3_G | 5 | 2283486 | constructor | gradient_in_prompt | n/a | ALIVE |
| B3_D | 6 | 2283487 | improver    | gradient_in_prompt | 24  | ALIVE |
| B5_G | 7 | 2283488 | constructor | gradient_in_prompt | n/a | ALIVE |
| B5_D | 8 | 2283489 | improver    | gradient_in_prompt | 40  | ALIVE |
| WATCHDOG | – | 2284012 | – | – | – | ALIVE |

`max_generations=50`, `stage_timeout=2400s`, `dag_timeout=2400s`.
Stopping rule: max_generations OR futility-at-gen25 (all 4 cells max(G,D) < 0.030).

---

## Delta vs `k5-budget-loose` (the invalidated v1)

Every change has been independently validated in the redesign-sandbox F35 gate:

1. **Smoothed `tanh` D fitness** (`problems/heilbron_adversarial/pop_b/evaluate.py`)
   - Replaces hard-floor `max(delta,0)/Q_MAX` which collapsed 60-90% of D programs to 0.
   - Sandbox: A_D fitness frontier 0.561, B_D 0.674 — non-degenerate.
2. **Smoothed `tanh(-delta/Q_MAX)` G resistance** (`problems/heilbron_adversarial/pop_a/evaluate.py`)
   - Replaces binary `float(delta<=0)` mask which produced point-mass at upper bound.
   - Sandbox: A_G frontier 0.758, B_G 0.626 — non-degenerate.
3. **Deterministic top-K HoF** via `OpponentArchiveProvider.get_top_k(K)` (replaces stochastic `get_opponents(n)`).
4. **`cache_on` edges** in `AdversarialAsymmetricPipelineBuilder` so InsightsStage / LineageStage invalidate when HoF rotates.
5. **`OpponentArchiveProvider.get_programs_by_ids` cache-refresh-on-miss** (sandbox proved this fix unlocked Lamarckian transfer: `dg_injected_pairs` grew 0 → 91 over 7 gens).
6. **`request_timeout: 600` + `max_retries: 2`** on `ChatOpenAI` (litellm proxy CLOSE-WAIT mitigation).
7. **`opponent_provider.cache_ttl=2.0`** (per-arm override) — tighter cache so HoF rotations propagate fast.
8. **`pipeline_builder.archive_reeval=true`** — explicit, applied to every arm via `extra_overrides`.
9. **K = L = 3** (`source_prompt_k=3`, `n_opponents=3`).

---

## Sandbox provenance

- F35 gate: PASSED — `experiments/heilbron/redesign-sandbox/SANDBOX_REPORT.pdf` (sent earlier)
- All P0 fixes already merged on this branch (commits `e10ed3d1`..`83813688`)
- No code changes between sandbox completion and this launch (configuration-only diff in `experiments/heilbron/k5-budget-v2/experiment.yaml`)

---

## Control plane

- **Watchdog:** `gigaevo -e heilbron/k5-budget-v2 watchdog` (PID 2284012). Polls every 3600s, posts rolling PR comments, sends Telegram alerts on stall/invalidity.
- **Notifications:** Telegram + PR comments enabled.
- **Plot commands wired:** `arms-race.png` and `evolution_runs_comparison.png`.

---

## What I will do next without your input

1. Periodic checkpoint (`/experiment-checkpoint heilbron/k5-budget-v2`) every ~4h via cron once I set it up.
2. Anomaly poll every ~2h via cron.
3. At gen 25, the futility check fires (per pre-registration). I will surface the result.
4. At gen 50 OR full futility, I will close out.

If anything CRITICAL fires (proxy down, all arms stalled, treatment silently degrades) I will wake you with a Telegram message rather than acting unilaterally.

---

## Outstanding (not blocking)

- k5-budget-v2 manifest is currently **untracked** on a new branch. I will commit + open the tracking PR after the first checkpoint confirms the runs are healthy past gen 0 (avoids polluting git with a config that turned out to crash on cold-start).
- `heilbron/k5-budget-loose` remains `status=invalid` — no resurrection, this experiment **supersedes** it on a fresh branch.
