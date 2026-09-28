# Issues Log — adversarial/adversarial-vs-solo

---

### Issue #1: S2 generation lag with elevated invalidity (persistent)

- **When**: 2026-04-11 ~20:45 UTC (anomaly detector check #2)
- **What**: S2 at gen 11, all other runs at gen 19-25. S2 invalidity 28% vs S1/S3/S4 at 12-15%. Valid program count S3/S2 = 3.33x (marginally above Pattern 8 threshold of 3x). This was first flagged at check #1 (S2 gen 9, invalidity 28%). Both checks: S2 lagging consistently.
- **Category**: hypothesis-relevant (not infrastructure)
- **Impact**: S2 will finish with fewer generations if the run completes at wall-clock cutoff. Random exploration quality variance — does not affect validity of other runs.
- **Root cause**: Diverse error types in S2 failures (SubprocessError x15, ValueError x11, SyntaxError x8, TimeoutError x2 — no single dominant error). Programs per generation ratio is normal (S2: 6.1 vs S1-S4: 6.7-7.2), indicating the engine is healthy. The lag is pure random variance: LLM-generated programs happen to contain more invalid code in this replicate.
- **Pattern 8 assessment**: Ratio 3.33x (just above 3x threshold). However: same diverse error types across different programs (no systematic bug signature), programs/gen normal, no consistent ValueError or import error. Classified as random variance, NOT infrastructure failure.
- **Fix applied**: Alert only. No auto-fix. CRITICAL RULE: do not restart S2 — invalidity pattern may be hypothesis-relevant (tests the robustness of the solo arm to initial exploration luck).
- **Systemic fix needed**: NO. Monitor at next check whether S2 invalidity comes down as run matures.

---

### Issue #2: S2 LineageStage high-duration episodes (early run)

- **When**: 2026-04-11 ~17:30-19:33 UTC (early run period)
- **What**: S2 LineageStage ran up to 286s in early generations (gen 1-8 period), with multiple instances over 100s (107s, 167s, 140s, 189s, 286s). Peers (S1, S3, S4) also show occasional high LineageStage times (max 310-695s), so this is not S2-specific.
- **Category**: normal variance
- **Impact**: Contributed to S2's lower total throughput early, but not significantly different from other runs. S2 average LineageStage = 95.4s vs S1 88.7s, S3 99.5s, S4 106.4s — all within same range.
- **Root cause**: LineageStage duration is proportional to lineage tree size. All runs show similar variance. No anomaly.
- **Fix applied**: None — within normal operating range.
- **Systemic fix needed**: NO.

---

[CHECKPOINT gen=22] — All PIDs ALIVE. Watchdog ALIVE. No new deviations or decisions. S2 generation lag persists (gen 12 vs S1=22, S3=28, S4=24) with 31% invalidity, consistent with Issue #1 (random variance, not infrastructure). No other runs affected. Fitness: S1=0.03450, S2=0.02937, S3=0.03320, S4=0.02602.

---

[CHECKPOINT gen=41] — S3 completed at 50/50 (PID dead, expected). S1/S2/S4 PIDs ALIVE. Watchdog ALIVE. No new deviations or decisions. S2 generation lag persists (gen 32, 30.7% invalid — Issue #1 ongoing). S4 stagnation at gen 26-43 (17 gens, 0.02828 — new observation, not yet flagged as issue since this is algorithm behavior not infrastructure). Mid-run checkpoint-analyst invoked (blinded labels R1-R4). NOTE: analyst broke blinding by reading 01_design.md — advisory-only analysis, no decisions affected, but protocol note for audit trail. Analyst assessment: bimodal outcome (R1/R3 near adversarial mean ~0.0346, R2/R4 below at 0.032/0.028). Likely final verdict: POSITIVE for adversarial arm. Fitness: S1=0.03466, S2=0.03199, S3=0.03458, S4=0.02828.

---

[CHECKPOINT gen=46] — S1/S2/S4 PIDs ALIVE. S3 completed (50/50). Watchdog ALIVE. No new deviations or decisions. S4 broke out of 17-gen stagnation with improvement at gen 45 (0.02828→0.02872). S2 caught up significantly (gen 32→42), lag narrowing. S1 improved to 0.03538 (above adversarial mean 0.03449). All runs nearing completion. Fitness: S1=0.03538, S2=0.03199, S3=0.03458, S4=0.02872.

---

[CHECKPOINT gen=50 FINAL] — ALL 4 RUNS COMPLETED at gen 50/50. All PIDs dead (expected). Watchdog still alive (to be killed at closeout). No deviations or decisions. Final fitness: S1=0.03538, S2=0.03199, S3=0.03458, S4=0.02872. Solo arm mean=0.03267 vs adversarial arm mean=0.03449 (delta=-0.00182, -5.3%). S2 finished despite persistent lag (Issue #1). S4 recovered slightly from stagnation (0.02828→0.02872). Experiment ready for closeout.
