# Preregistration: shortlist novelty boost (w_nov=0.25) — hover full7

Date: 2026-07-11 (pre-launch). Branch: memory-cold-probe-policy (uncommitted).
Launcher: `launch_novelty.sh` (verbatim mirror of `launch_baseline_memory.sh`,
single functional delta). Approved by user 2026-07-11 ("go with 1").

## Question

Does a repeat-use cooldown in card shortlisting (`memory.reader.shortlister.w_nov`
0.0 → 0.25) break single-card dominance and spread injections across the bank
without hurting fitness?

## Treatment

Fused shortlist score becomes `1.0·semantic + 0.0·reputation + 0.25·novelty`
with `novelty(card) = 1/(1 + uses in last 24h)`. Runs last <24h, so within a run
this is `1/(1 + total prior injections)`: 2nd use costs the card ~0.125 fused
score, 5th ~0.20 — enough to drop a warm card below other semantically relevant
cards after a few uses. Everything else identical to the 20260710_041404 control
pair (adaptive read policy, bootstrap-Thompson auction, EV gate untouched).

## Arms

- NOV_R1 / NOV_R2 — new pair, w_nov=0.25, 250 mutants each.
- Control: MEM_R1 / MEM_R2 (outputs/hover-diff-memory-baseline-20260710_041404),
  w_nov=0.0, same launcher otherwise.
- Reference: EXPL pair (3-card), NOMEM pair.

## Causal chain

w_nov>0 → each injection lowers that card's fused shortlist score → after ~3-5
uses a warm card slides below alternatives → different cards reach the auction
and can pass the EV gate → injections spread across the bank → (a) max
injections per card falls, (b) more cards accrue reputation evidence, (c) IF
diverse cards carry independent useful ideas, with-card mutation deltas improve;
if the dominant card was genuinely the only useful one, fitness flat-to-slightly-down.

## Riskiest link

The auction may re-concentrate what the shortlist spreads: the shortlist is 50
deep, and if the EV gate benches most alternatives, the same few cards win
regardless of shortlist order. Then P1 barely moves — that outcome falsifies
"shortlist order is the dominance lever" and points at the auction as the next
lever, NOT at a bigger w_nov.

## Endpoints (variance discipline)

Primary — mechanism endpoints, near-deterministic given the treatment (this is
deliberate: run-level fitness comparisons at n=2 cannot resolve the gaps we care
about, so the verdict must ride on low-noise endpoints):

- **P1 dominance**: max injections of any single card per run.
  Control: MEM_R1=86, MEM_R2=26. Predict ≤30 in both replicates
  (pre-registered violation bar stays 60).
- **P2 coverage**: number of distinct cards injected ≥1×. Predict ≥1.3× control.
- **P3 concentration**: top-1 card's share of all injections. Predict strictly
  lower than the same-replicate-rank control in both replicates.

Secondary — statistical, high-n, reported with mean±SD + bootstrap 95% CI +
Mann-Whitney U (per stats_significance.py conventions):

- **S1**: with-card per-mutation fitness delta vs pooled MEM pair
  (control pooled mean −0.0024, n=198). Bar: non-inferiority
  (no significant harm at MW p<0.05).
- **S2**: population fitness of valid programs, mean±SD.

Descriptive only — **D1**: best-of-run, re-evaluated K=5 with the
reeval_winners.py harness → mean±SD + CI. No conclusions from single in-run
point estimates (winner's curse; per-eval noise measured 2026-07-11).

## Prediction table

| # | Metric | Control | Prediction | Falsified if |
|---|--------|---------|------------|--------------|
| P1 | max injections/card | 86 / 26 | ≤30 both reps | >60 either rep |
| P2 | distinct cards injected | (measure at closeout) | ≥1.3× control | ≤1.0× |
| P3 | top-1 injection share | (measure at closeout) | lower, both reps | higher, either rep |
| S1 | with-card delta vs MEM pooled | −0.0024 | ≥ control, MW ns or better | significantly worse |
| D1 | best-of-run ± CI | 0.8322 / 0.8011 (in-run, curse-inflated) | no prediction | — |

## Decision rule

P1–P3 decide whether w_nov works mechanically; S1 decides whether it ships as
the adaptive-preset default. Dominance broken + fitness non-inferior → SHIP
w_nov=0.25. Mechanism moved but S1 significantly worse → do not ship; inspect
which newly-injected cards harmed. Mechanism did NOT move → auction is the
lever, not shortlist order.

## Analysis plan

Closeout compares NOV / MEM / EXPL / NOMEM with eval-noise CIs everywhere:
winners re-evaluated K=5 each; run-level n=2 gets spreads only, no tests;
population/per-mutation endpoints get MW + Fisher + bootstrap CIs; within-run
non-independence caveat stated. PDF → Telegram.

## Issues log

- (launch) 2026-07-11 02:38 — TS=20260711_023848, PIDs R1 582336 / R2 582337.
  All smoke checks passed (3 proxy models + 8 direct backends). Both cfg dumps
  verified w_nov: 0.25 (w_sem 1.0, w_rep 0.0 unchanged). Launched AFTER the
  eval-noise re-eval study completed, so no load overlap with the σ measurement.
  Run-end watchdog `watchdog_run_end_novelty.sh` detached (log
  `logs/watchdog_novelty_20260711_023848.log`), dominance thresholds wired to
  P1 (≤30 predicted / 60 bar). No other issues at launch.
