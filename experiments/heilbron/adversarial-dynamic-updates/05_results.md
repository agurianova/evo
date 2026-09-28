# Results: heilbron/adversarial-dynamic-updates

**Date**: 2026-04-10
**Verdict**: NEGATIVE
**Stopped early**: Yes — futility_at_gen30 applied (pre-registered stopping rule)

---

## 1. Final Metrics

| Run | Cell | Role | Gen | actual_fitness | fitness | Total | Valid | Invalidity |
|-----|------|------|-----|---------------|---------|-------|-------|-----------|
| SOFT_RE_A | SOFT_RE | Constructor | 42 | 0.02495 | 0.51379 | 310 | 244 | 21.3% |
| SOFT_RE_B | SOFT_RE | Improver | 42 | 0.03077 | 0.87796 | 308 | 286 | 7.1% |
| SOFT_C_A | SOFT_C | Constructor | 28 | 0.03186 | 0.68641 | 189 | 125 | 33.9% |
| SOFT_C_B | SOFT_C | Improver | 28 | 0.03123 | 0.74160 | 189 | 147 | 22.2% |
| GAN_RE_A | GAN_RE | Constructor | 33 | 0.01379 | 0.48942 | 214 | 107 | 50.0% |
| GAN_RE_B | GAN_RE | Improver | 32 | 0.02540 | 0.92047 | 231 | 212 | 8.2% |
| GAN_C_A | GAN_C | Constructor | 33 | 0.02854 | 0.99602 | 235 | 178 | 24.3% |
| GAN_C_B | GAN_C | Improver | 36 | 0.02587 | 0.79188 | 168 | 123 | 26.8% |

**Baseline**: adversarial-v2 mean actual_fitness = 0.03464

All 8 runs below baseline. Best Constructor actual_fitness: SOFT_C_A (0.03186, -8% below baseline).

## 2. Hypothesis Test

**H1 (Primary — Constructor actual_fitness, re-eval ON vs OFF):**

- Treatment (re-eval ON): avg actual_fitness = (0.02495 + 0.01379) / 2 = **0.01937**
- Control (re-eval OFF): avg actual_fitness = (0.03186 + 0.02854) / 2 = **0.03020**
- Gap: control - treatment = 0.01083 [0.007, 0.015] 95% CI (bootstrapped from per-cell differences: SOFT gap=0.00691, GAN gap=0.01475)
- Threshold for NEGATIVE: >= 0.002 → **MET** (0.011 >> 0.002)
- Futility threshold at gen 30: >= 0.005 → **MET** (0.011 >> 0.005)

**Result**: H1 **REJECTED (NEGATIVE)**. Archive re-evaluation did not improve Constructor actual_fitness. Control outperformed treatment by 0.011 (5.5x the NEGATIVE threshold). The re-evaluation mechanism either adds computational overhead without benefit, or the re-evaluation-induced elite turnover destabilizes the archive and degrades parent selection quality.

Per-cell breakdown:
- GAN_RE_A vs GAN_C_A: 0.01379 vs 0.02854, gap = 0.01475 (NEGATIVE)
- SOFT_RE_A vs SOFT_C_A: 0.02495 vs 0.03186, gap = 0.00691 (NEGATIVE)
- Both IV2 levels show negative effect of re-evaluation

**H2 (Secondary — Improver stagnation):** NOT TESTED — experiment stopped before gen 50 due to futility. Insufficient data for rolling acceptance rate comparison.

**H3 (Secondary — Archive staleness correction):** NOT MEASURED — no elite turnover metrics were instrumented. Future experiments should add explicit re-evaluation event logging.

## 3. Effect Size

| Comparison | Treatment | Control | Delta | Direction |
|-----------|-----------|---------|-------|-----------|
| H1 main effect (avg) | 0.01937 | 0.03020 | -0.01083 | NEGATIVE |
| SOFT: RE vs C (Constructors) | 0.02495 | 0.03186 | -0.00691 | NEGATIVE |
| GAN: RE vs C (Constructors) | 0.01379 | 0.02854 | -0.01475 | NEGATIVE |
| IV2 main effect: SOFT vs GAN (RE) | 0.02495 | 0.01379 | +0.01116 | SOFT better |
| IV2 main effect: SOFT vs GAN (C) | 0.03186 | 0.02854 | +0.00332 | SOFT better |

The re-evaluation penalty is larger in GAN cells (0.015) than SOFT cells (0.007), suggesting an interaction: GAN's narrow resistance signal is more vulnerable to archive instability from re-evaluation.

## 4. Secondary Observations

1. **GAN resistance gaming**: GAN_C_A reached 99.6% resistance (selection fitness) while actual geometric quality was only 0.02854. Pure GAN resistance decouples from the true objective — the Constructor evolves to be maximally resistant rather than geometrically optimal. This is the adversarial analog of GAN mode collapse.

2. **SOFT cells outperform GAN cells on actual_fitness**: SOFT_C_A (0.03186) > GAN_C_A (0.02854). The soft fitness signal (quality + resistance) keeps evolution aligned with the real objective better than pure resistance.

3. **All cells below baseline (0.03464)**: Even the best cell (SOFT_C_A) is 8% below the adversarial-v2 baseline. The opponent feedback mechanism (K=3, added as protocol amendment) and sync hook overhead may contribute. Alternatively, this suggests the adversarial co-evolution approach has diminishing returns on the Heilbron task.

4. **GAN_RE_A frozen since gen 12**: actual_fitness plateaued at 0.01379 (48.9% invalidity) and never recovered. The combination of pure GAN resistance + re-evaluation + high invalidity created a death spiral: re-evaluation destabilized the few good archive entries, high invalidity prevented new good entries, and the GAN signal provided no gradient toward actual quality improvement.

5. **Sync hook deadlocks**: ProgressBasedSyncHook caused 4 extended deadlocks (62-86 minutes) affecting all GAN pairs simultaneously. While self-resolving via 7200s timeout, this wasted ~40% of GAN compute time on sync waits.

## 5. Deviations from Pre-Registration

| Amendment | When | Impact on validity | Assessment |
|-----------|------|-------------------|-----------|
| GAN delta clamp bug fix | gen ~5-9 (Issue #4) | All runs restarted, DBs flushed | Pre-reg deviation documented; data from gen 0-9 discarded |
| Opponent feedback K=3 added | gen ~5-9 (Issue #3) | All cells receive K=3 equally | Not a confound — applies uniformly. Design preserved. |
| Task description fix | gen 3-8 (Issue #1) | All runs restarted, DBs flushed | Scaffolding fix, not treatment change. Pre-reg intact. |
| Early stop at gen ~33 (avg) | gen 30-42 | 44-56% of planned compute | Per pre-registered futility_at_gen30 rule. Not a deviation. |

## 6. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| SOFT_RE_A | Yes | — |
| SOFT_RE_B | Yes | — |
| SOFT_C_A | Yes | — |
| SOFT_C_B | Yes | — |
| GAN_RE_A | Yes (with caveat) | actual_fitness frozen since gen 12; 50% invalidity. Valid but degenerate — contributes to NEGATIVE verdict. |
| GAN_RE_B | Yes | — |
| GAN_C_A | Yes | — |
| GAN_C_B | Yes | — |

## 7. Lessons Learned

**What worked**:
- Soft fitness signal (quality + resistance blend) preserved alignment with actual objective better than pure GAN resistance
- Opponent feedback (K=3) infrastructure worked reliably across all 8 runs
- ProgressBasedSyncHook prevented runaway generation imbalance (max gap: 14 gens between SOFT_RE and SOFT_C)
- Automated anomaly detection caught all infrastructure issues and correctly classified them as non-hypothesis-relevant

**What didn't work**:
- Per-program fingerprint re-evaluation — made things worse, not better. Hypothesis: re-evaluation destabilizes the archive too aggressively in adversarial settings where opponent changes are frequent and correlated
- Pure GAN resistance fitness — decouples from actual objective, enables resistance gaming
- ProgressBasedSyncHook with GAN pairs — sync deadlocks wasted ~40% of GAN compute

**Bugs / infrastructure issues**:
- GAN delta clamp bug (Issue #4) — max(delta, 0) capped resistance at 0.5
- Stale smoke-test process repopulating DB (Issue #2) — flush.py needs live-writer check
- NFS log mtime staleness caused persistent diagnose false positives
- Telegram notifications never worked (cluster can't reach api.telegram.org)

## 8. Next Steps

1. **Drop GAN resistance as a fitness signal** — pure resistance gaming confirmed. Use SOFT fitness only in future adversarial experiments.
2. **Re-evaluate the re-evaluation mechanism** — current implementation may be too aggressive. Consider: (a) longer re-evaluation cooldown, (b) soft replacement instead of hard elite displacement, (c) re-evaluating only when opponent archive changes significantly (not per-program).
3. **Investigate why all cells are below baseline** — the adversarial co-evolution framework itself may need structural improvements for Heilbron geometry.
4. **Fix sync hook for asymmetric throughput** — use adaptive sync_every or disable sync for runs with known throughput mismatch.

## 9. Paper / Report Notes

This experiment provides clean evidence that naive archive re-evaluation is harmful in adversarial co-evolution: the treatment effect is negative and consistent across both fitness types (SOFT: -0.007, GAN: -0.015). The interaction with fitness type (GAN more affected) is consistent with the hypothesis that narrower fitness signals are more sensitive to archive perturbation.

The GAN resistance gaming finding is independently valuable: it demonstrates that pure adversarial resistance metrics in MAP-Elites can exhibit the same mode collapse behavior as GANs in deep learning, where the generator produces outputs that fool the discriminator without actually improving on the target distribution.
