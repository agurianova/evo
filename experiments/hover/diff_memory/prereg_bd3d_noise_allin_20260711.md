# Preregistration: ALL-IN launch — BD3D + paired gate + paired crediting (1 MEM + 1 NOMEM)

Date: 2026-07-11 (pre-launch). Branch: memory-cold-probe-policy (uncommitted).
Launcher: `launch_bd3d_noise_allin.sh`. Amends `prereg_bd3d_noise_20260711.md`
(the 4-run layout, never launched) per user directive: "let us go all in!
BD3D+noise + THIS change. 1 memory run + 1 no memory."

## Deltas vs prereg_bd3d_noise_20260711.md

1. **Reps: 1 per arm** (MEM_R1, NOMEM_R1) instead of 2×2. Replication claims
   are out of scope; the experiment is judged on its **product** (best
   program), not on clean per-treatment attribution.
2. **MEM arm adds `memory/crediting=paired`** — the comparator crediting
   system built today: gain events carry a paired-bootstrap `gain_se` from
   (frozen base vector, child vector); reputations count harm softly
   (Φ((thr−gain)/se)); the auction jitters bootstrap atoms by N(0, se).
   This treatment is NEW and live for the first time.
3. This is a **for-fun-bundle style launch** ([user waived ablation
   isolation]): five foundation/treatment changes run together. Correctness
   verification is NOT waived — every change gets a live
   consumption check (below). Attribution of any fitness effect to a single
   change is explicitly impossible at n=1/arm; the acceptance criterion is
   product-level.

Everything else (arms, models, 250 mutants, endpoints M1/M2/G1/P-churn/S2,
riskiest link, treatment provenance) carries over from
`prereg_bd3d_noise_20260711.md` unchanged, with fitness endpoints downgraded
to directional-only at 1 rep/arm.

## Acceptance criterion (user-set): top-1 val significantly better than previous runs

**A1 (primary, decides WIN/NO-WIN):** Let `best_new` = the program with the
highest K=5 re-eval mean among the two arms' final winners. Let `best_prior` =
the best previous hover full7 winner by K=5 re-eval mean:
**MEM_R1 (20260710_041404), re-eval mean 0.8298 ± 0.0109**, runner-up NOV_R2
0.8291 ± 0.0090. WIN requires **both**:

- `best_new` re-eval mean > 0.8298, and
- paired per-sample significance vs BOTH top-2 prior winners
  (MEM_R1 and NOV_R2): same 300-claim val set, per-claim scores averaged over
  K=5 evals for each program, paired Wilcoxon signed-rank + paired-bootstrap
  95% CI of the mean difference; require p < 0.05 and CI > 0 against each.

Method note: this is the same paired machinery as the eval-noise addendum
(single-eval σ≈0.0078; the paired per-sample test resolved Δ≈0.003–0.007 at
p<1e-4 before, so a true ≥0.01 gain is comfortably detectable; K=5 averaging
shrinks per-claim noise further).

**Asymmetry of interpretation (pre-declared):**
- WIN ⇒ genuine: the paired test at the winner level is not confounded by
  run-to-run luck — the program itself is better on the shared val set.
- NO-WIN ⇏ the stack is worse: winner-level variance between same-config
  reps is real (NOV_R1 vs NOV_R2 differed at p=.0008); a single rep failing
  to beat the best of eight prior runs is weak evidence. Verdict then falls
  back to the mechanism endpoints + arm contrast, and the decision is
  re-run-vs-park, not revert.

**A2 (guardrails — a WIN is only claimable if all hold, else the result is
"integrity-compromised, investigate"):** every treatment verified live per
the monitoring plan below (transport P1, occupancy M1, gate consulted G1,
crediting active + consumed C-W/C-R, arm purity).

## Live monitoring plan — every change traced to the decision it changes

Lesson applied ([feedback_treatment_output_consumption_check]): verify each
treatment's OUTPUT is CONSUMED by a decision, not merely that its code path
executes. Two prior inert-treatment incidents make this the core of the plan.

| ID | Change | Live signal | Decision it changes | Inert-treatment symptom |
|---|---|---|---|---|
| T1 | BD3D space (`chains_bd3d`) | `storage/*/archives/island_*.json` distinct keys | which elites are protected/challenged | ≤5 cells: everything maps to a few bins |
| T2 | structural metrics stage | hop_depth/passages_fetched/instr_chars in program metrics, nonzero variance | BD cell assignment | all-zeros ⇒ extractor never parses live specs |
| T3 | vector transport (full7_vectorized + *_noise pipeline) | `metadata.per_sample_scores` len≈300 on scored programs; mean↔fitness ≤1e-4 | enables T4 + T5 | missing vector / incoherent mean |
| T4 | paired archive gate (p_accept=0.75) | `[PairedBootstrapArchiveSelector]` ACCEPT/REJECT lines with P(better); fallback lines | archive replacement on occupied cells | 0 decision lines by 3h with occupied-cell challenges happening; any fallback line = transport bug |
| T5-W | paired crediting, write side (MEM) | bank `gain_events[*].gain_se > 0` on DIRECT events | event evidence stored for reputation | all se==0 while valid card-injected children exist |
| T5-R | paired crediting, read side (MEM) | counterfactual replay on live bank: beta posterior (soft harm) and bootstrap EV quantiles computed with stored ses vs ses:=0 | theta samples, ev_floor gating, auction winners | zero delta on every card while noisy events exist |
| T6 | memory stack health | MEMORY_AUCTION_RUN / MEMORY_READ_SELECTION telemetry via `analyze_memory_behavior.py` | injection slate | outside known-good bands (see thresholds below) |
| T7 | NOMEM arm purity | no MEMORY_* events, no bank writes, no memory metadata | — | any memory artifact in NOMEM |

Automated by `check_allin_progress.py` (this dir): reads `latest_allin.env`,
prints a PASS/WARN/FAIL table for T1–T7 per run. Run it at every checkpoint.

### Checkpoint schedule

- **T+10 min — liveness.** Both PIDs alive (`lsof` on logs, not `ps`
  [rtk_ps_truncation_trap]); no crash loop in logs; config echo sane.
- **T+1 h — HARD GATE (abort-all on failure).**
  (a) T1: >5 distinct occupied cells per run (original prereg criterion);
  (b) T3 on a sample of scored programs;
  (c) MEM writes cards + T5-W: ≥1 DIRECT gain event with gain_se>0, required
      only once ≥3 valid card-injected children exist (else re-check at 2h
      before aborting);
  (d) T7 purity.
  Any failure ⇒ SIGKILL both runs (engine traps TERM), rename artifacts
  `*_aborted_*`, investigate before relaunch. Telegram either way.
- **T+3 h — mid-run study (informational, no abort).** Full T1–T7 sweep plus:
  occupancy growth (cells vs mutant count), hop_depth distribution vs pooled
  control 12.7% hop≥3, gate consult count + REJECT share, T5-R replay deltas,
  crediting degradation rate (share of vector-eligible DIRECT events with
  se==0 — expect low; high = vectors not reaching the writer), auction
  fraction (known-good band 30–55%), max-card injections (dominance bar <60),
  best-so-far trajectory vs the six prior runs at equal mutant count
  (created_at ordering, NOT atomic_counter). Telegram summary with numbers.
- **T+6 h — repeat of T+3h sweep** (drift check; same script, both runs).
- **Run end (watchdog, auto).** Final T1–T7 sweep; winners K=5 re-eval
  (`reeval_winners.py`); A1 paired tests vs MEM_R1 + NOV_R2 stored re-evals;
  M1/M2/G1/P-churn/S2 endpoints; PDF report + ELI5 verdict to Telegram.

### Threshold provenance (all from prior runs, no new absolutes)

Auction band 30–55% and dominance <60 from the memory-overhaul closeouts;
hop≥3 control share 12.7% from the 1491-program mining; occupancy bars from
the offline replay (40–64 cells) with the 1h floor at >5 (degenerate-space
tripwire); σ≈0.0078 and the paired-test power figures from the 2026-07-11
eval-noise addendum.

## Decision rule

- **A1 WIN + A2 clean** → declare the all-in stack the new hover reference;
  next step = replication pair to convert product-level WIN into
  config-level evidence, then per-change ablations only if the replication
  holds.
- **A1 NO-WIN, mechanisms healthy (M1, T4 consulted, T5 consumed)** →
  foundation adopted-in-principle, fitness verdict deferred to a replication
  pair; no reverts on single-rep evidence.
- **Any A2 guardrail failure** → integrity bug: fix, then relaunch; the
  fitness numbers of the compromised run carry no verdict weight.
- **1h hard gate failure** → abort-all (backend budget is the scarce
  resource), diagnose on the aborted artifacts.
