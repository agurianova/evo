# Gate 0 — Spearman ρ(quality, resistance) on v2 G archives

**Verdict: FAIL on all runs. v3 G primary BD falls back to `(quality, g_tracker_coverage_count)`.**

## Result

```
============================================================================================
Gate 0 — Spearman ρ(quality, resistance) on v2 G archives
Pass threshold: |ρ| < 0.7  (plan §7)
============================================================================================
  A3_G   n=  54  ρ(q,r)=+0.831  p=7.49e-15  q∈[0.0000,0.8264]  r∈[0.321,0.505]  → FAIL (use fallback)
  A5_G   n=  37  ρ(q,r)=+0.795  p=4.29e-09  q∈[0.0001,0.7858]  r∈[0.336,0.552]  → FAIL (use fallback)
  B3_G   n=  41  ρ(q,r)=+0.714  p=1.62e-07  q∈[0.0000,0.8082]  r∈[0.326,0.523]  → FAIL (use fallback)
  B5_G   n=  32  ρ(q,r)=+0.776  p=1.84e-07  q∈[0.0096,0.9369]  r∈[0.287,0.533]  → FAIL (use fallback)
--------------------------------------------------------------------------------------------
  POOLED n= 164  ρ(q,r)=+0.778  p=1.43e-34  q∈[0.0000,0.9369]  r∈[0.287,0.552]  → FAIL (use fallback)
============================================================================================
Bonus: pooled ρ(fitness, quality)=+0.996  ρ(fitness, resistance)=+0.821
```

## Interpretation

1. **All four G runs independently fail the |ρ| < 0.7 threshold** (range: 0.71–0.83). Not a sampling artifact.
2. **Resistance range is narrow: [0.287, 0.552].** The `tanh`-smoothed `resistance = (tanh(-Δ/Q_MAX) + 1)/2` barely leaves the 0.5 anchor because `|Δ/Q_MAX| ≪ 1` for most programs — most interactions are small fitness deltas. This itself a weak-signal flag that merits investigation in v3's post-experiment analysis, but doesn't change the Gate verdict.
3. **ρ(fitness, quality) = +0.996 (effectively 1.0)** empirically confirms v3's core premise in §1: the scalarized `fitness = ALPHA·quality + (1-ALPHA)·resistance` is essentially a monotone transform of `quality`. The ALPHA-weighted resistance term contributes no effective selection pressure that isn't already in `quality`. Selection-as-scalar is structurally broken exactly as predicted by Ficici & Pollack (GECCO 2003).

## Action — v3 design amendments

**G population primary BD switches from §3.1 to §3.2 (fallback):**

| axis | source | bounds | bins |
|---|---|---|---|
| quality | `pop_a/evaluate.py` | `[0, 0.0365]` | 15 |
| g_tracker_coverage_count | `SCARD({prefix}:dg_g_resisted:{g_id})` | `[0, 150]` | 15 |

Symmetric to D's primary BD. G resolution drops to 15×15 (was 15×10). All other §8 config for G updates accordingly.

D population primary BD is unchanged — Gate 0 only gates G.

## Archive sample sizes

G archive sizes (54, 37, 41, 32) are adequate for Gate 0 but smaller than expected — the 1D-on-fitness archive did collapse partially as predicted by k5-budget-loose post-mortem. v3's 2D archive should reach ≥ 100 cells per run if the fallback BD is well-calibrated.

## Reproducibility

Script: `/tmp/v2_gate0/spearman.py` (committed to `experiments/heilbron/k5-budget-v3/gate0_spearman.py`).
Data source: Redis localhost:6379, DBs 1/3/5/7, key `island_fitness_island:archive`.
Run date: 2026-04-18.
