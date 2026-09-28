# HoVer diff-memory campaign journal

Append-only. Dated entry per launch and per finding. (Started 2026-07-11;
earlier launches are documented in their prereg files and latest_*.env.)

## 2026-07-11 — LAUNCH: novelty-auction pair (TS=20260711_115748)

- Treatment: `+memory/auction=thompson_bootstrap_novelty` (novelty_power=0.5) —
  auction bid pays a `(1+use_count)^-0.5` tax; use_count = the card's
  non-founding gain events (deterministic injection count, no wall clock).
  Implementation landed same day on branch memory-cold-probe-policy
  (NoveltyDiscountedBootstrapAuctioneer behind the `_adjust_bids` seam;
  ~740 tests green, lint clean). Supersedes the falsified w_nov=0.25
  shortlist treatment (inert — auction, not shortlist order, is the lever).
- Prereg: `prereg_novelty_auction_20260711.md`. Mechanism endpoints P1–P3 are
  judged against each run's OWN power=0 counterfactual replay
  (`replay_novelty_bid.py`, exact-reproduction validated: 0 winner mismatches
  on 4 prior runs) — deterministic, no cross-run variance. Fitness S1/D1
  directional only at n=2 (single-eval σ≈0.0078).
- Control: MEM pair 20260710_041404, launcher mirrored verbatim; cfg diff
  verified — exactly one functional delta (auctioneer class + novelty_power).
  Corrected control dominance figures: max-card 17 (R1) / 26 (R2), of which
  14 / 22 via the auction lane (dominance is auction-driven; probe fills are
  cold-card-spread).
- Launch: 11:57, R1 pid 641650 / R2 pid 641651, 250 mutants each,
  storage=disk, banks SHARE_HOVER_DIFF_MEMORY_NOVAUC_R{1,2}_20260711_115748.
  All smoke checks passed (3 proxy models + 8 direct backends). Run-end
  watchdog detached (pid 642921, log
  `logs/watchdog_novelty_auction_20260711_115748.log`).
- Pending: ~1h treatment-consumption check on live MEMORY_AUCTION_RUN
  telemetry (use_count flowing; tax flips ≥1 winner vs raw-bid argmax).

## 2026-07-11 — FINDING: novelty-auction treatment consumed live (half-run check)

- 1h check (13:03): use_count flowing, all zeros — matched baseline
  attribution lag (first card evidence at 61/93 min in MEM pair); not a bug.
- Half-run check (~16:05): tax verifiably changes decisions — R1 27 / R2 6
  auction rounds where the taxed argmax differs from the untaxed argmax, with
  fresh (use_count=0) cards displacing warm repeat cards (use 8 / 4).
  use_count max 19 (R1) / 6 (R2). Both runs healthy, 0 tracebacks.
- Watch item for closeout: R1's top card has 25 auction wins by half-run
  despite the tax (control full-run auction max was 14) — its untaxed
  counterfactual share is the P1 question, not the raw count.

## 2026-07-11 — STAGED: BD3D + noise combined experiment (4 runs), launch pending

- User decision: run BD3D behavior space + paired noise gate TOGETHER, with
  memory and no-memory arms — supersedes the staged fitness-bin noise pair
  (`prereg_noise_gate_20260711.md`, never launched; fitness bins rarely re-hit
  an occupied cell, so the gate would have been near-vacuous).
- Built and green (all uncommitted): semantic chain features
  (hop_depth/passages_fetched/instr_chars) parsed via the CARL parse-layer
  models (`problems.chains.types.RawChainSpec`, lazy import); generic
  `algorithm_requires` preset-prerequisite check in run.py (chain knowledge
  lives in the preset yamls, not framework code); `algorithm=chains_bd3d`
  (5×5×6, dynamic); `pipeline=guided_noise` (no-memory sibling of
  memory_guided_noise). 168 config+scheduling tests + tests/integration
  green, lint clean.
- Launcher `launch_bd3d_noise.sh`: mirror of `launch_noise_gate.sh` extended
  to MEM_R1/R2 + NOMEM_R1/R2 (250 mutants each, launched together for fair
  backend contention). DRY_RUN TS=20260711_prereg PASSED (3 proxy models + 8
  direct backends ok; 4 configs composed). cfg arm-diff verified: exactly the
  memory delta (pipeline builder, memory block, post-step hook,
  checkpoint_dir); foundation fields identical.
- Note: MEM arm's BDCellMemoryContext now keys card contexts by BD3D strategy
  cells (was fitness bins) — intended; it is the S2 mechanism.
- Prereg: `prereg_bd3d_noise_20260711.md` (M1 occupancy ≥35 cells, M2 hop≥3
  share ≥1.5× control 12.7%, G1 gate flips, P-churn, S1 K=5 re-eval CIs MEM
  vs NOMEM, S2 card efficacy by hop niche; 1h check: >5 occupied cells else
  abort all four).
- Launch gated on: NOVAUC pair freeing the 8 chain backends + Telegram go.

## 2026-07-11 — CLOSEOUT: novelty-discounted auction (NOVAUC, power=0.5) — DO NOT PROMOTE

- Pair TS=20260711_115748 vs MEM control 20260710_041404; prereg
  `prereg_novelty_auction_20260711.md`; report `novauc_closeout_20260711.pdf`;
  replay sanity: 0 mismatched rounds in both reps (taxed-bid replay reproduces
  every logged selected flag).
- P1 dominance CONFIRMED: top-card counterfactual share 27.8%→16.5% (R1,
  rel −40.9%) / 14.6%→13.1% (R2, rel −10.1%) — the tax does break winner
  lock-in.
- P2 volume FALSIFIED in R1: auction win volume GREW +19.1% (bar ±10%);
  R2 +0.5% ok. Mechanism: the tax lowers the whole bid distribution, and
  ev_floor_quantile (0.765) is computed on the SAME taxed bids — the floor
  drops with them, so marginal cards that used to fall below it now clear
  it. Redistribute-not-shrink does not hold under a quantile floor coupled
  to the taxed distribution.
- P3 coverage CONFIRMED (distinct winners 30≥27, 31≥31). P4 descriptive:
  max card 47×/34× — above control range (17/26), below the >52 bar.
- S1: NOVAUC with-card vs MEM with-card MW p=.179 → formally non-inferior,
  but directionally worse (−.0154 vs −.0164 is the with-vs-without gap
  story): within-arm with-card advantage COLLAPSED (p=.617; control had
  +.021). More rotation ⇒ reputation sorting gets less data per card.
- D1 K=5 re-evals (frozen winners, live backends): R1 stored .8033 →
  .7882 ± .0071; R2 stored .8067 → .7951 ± .0042. Controls: MEM .8298 ±
  .0109 / .7893. Both NOVAUC winners land at/below the control band;
  stored-vs-re-eval gap ≈ +.011–.015 (winner's curse, consistent with the
  eval-noise addendum).
- VERDICT: mechanism works (P1/P3) but the tax leaks marginal injections
  through the coupled quantile floor (P2) and the fitness advantage of
  injection collapsed (S1). thompson_bootstrap_novelty stays a preset,
  NOT default. Any revival must decouple the eligibility floor from the
  taxed bids (compute floor on raw bids, tax only the ranking) — that is
  the single mechanical fix this experiment points at.

## 2026-07-11 — FINDING: first ALL-IN launch (TS=20260711_224057) crashed at startup — ref write-back vs dataclass estimators

- MEM_R1 died 7.7s in: `InterpolationResolutionError: ConfigIndexError tuple
  index out of range, full_key: crediting`. NOMEM_R1 + watchdog killed to keep
  the pair comparable; artifacts renamed `*_failed_refwriteback`.
- Root cause: `_ref_resolver` (gigaevo/config/resolvers.py:30) writes the
  instantiated node back into the config tree; OmegaConf structured-wraps
  DATACLASS instances instead of storing them opaquely. `PairedEffectEstimator`
  crashed on its `Counter[str]` field; worse, the default `PointEffectEstimator`
  was silently replaced by an empty DictConfig — every `memory=full` run on
  this branch was broken, not just the paired override. `--cfg job` (DRY_RUN)
  never resolves interpolations, which is why the self-check missed it.
- Fix: estimators converted from dataclasses to plain classes (crediting.py);
  failing regression test first (`test_ref_writeback_survives_runtime_resolution`,
  both point + paired params reproduced the bug), then green. Scoped suite
  tests/memory+tests/config all green; lint clean.
- New guard: pre-flight resolve script replays run.py's exact
  `OmegaConf.resolve`-inside-instantiate step on the real launch overrides
  (both arms) — MEM writer now instantiates with a live PairedEffectEstimator.

## 2026-07-11 — LAUNCH: ALL-IN pair (TS=20260711_225431) — BD3D + paired gate + paired crediting, 1 MEM + 1 NOMEM

- Prereg `prereg_bd3d_noise_allin_20260711.md`; launcher
  `launch_bd3d_noise_allin.sh`; MEM pid 732751, NOMEM pid 732752; bank
  `SHARE_HOVER_DIFF_MEMORY_ALLIN_R1_20260711_225431`.
- MEM arm: pipeline=memory_guided_noise memory=full memory/crediting=paired
  (NEW: gain_se → soft harm + auction se-jitter, first live run). NOMEM arm:
  pipeline=guided_noise memory=none. Both: chains_bd3d 5×5×6 space,
  archive_selector=paired_bootstrap, full7_vectorized, 250 mutants.
- Acceptance A1 (user-set): best winner K=5 re-eval mean > 0.8298 AND paired
  per-sample p<.05 + CI>0 vs BOTH MEM_R1 (.8298±.0109) and NOV_R2
  (.8291±.0090). A2: all treatments verified live (T1–T7) else
  integrity-compromised.
- Monitoring armed: `watchdog_allin.sh` (detached) — T+1h HARD GATE via
  `check_allin_progress.py --hard-gate` with preregistered auto-abort
  (+2h T5-W re-check if too few injected children), T+3h/T+6h sweeps,
  run-end final sweep + top-3 — all to Telegram.

## 2026-07-12 — FINDING: 1h hard gate FALSE-POSITIVE abort (TS=20260711_225431) — T7 purity predicate too broad; fixed + RELAUNCH (TS=20260712_000307)

- At the T+1h gate the watchdog aborted the pair on `NOMEM_R1:T7 FAIL`
  ("40 programs with memory_* metadata"). Artifacts preserved at
  `outputs/hover-diff-memory-allin-20260711_225431_aborted_1hgate`.
- Root cause: T7 counted ANY `memory_*` metadata key as contamination, but
  the engine stamps inert keys on EVERY child in BOTH arms
  (`gigaevo/evolution/engine/mutation.py:186-193`): `memory_used=False`,
  empty id lists, and `memory_base_*` snapshots that feed the paired archive
  gate (base treatment, both arms by design). All 40 flagged programs had
  zero active signals; NOMEM had 0 `[MEMORY_` log lines, 0 bank files, no
  memory/ dir. The predicate was written from assumption, never validated
  against a real NOMEM program — same error class as the inert-treatment
  incidents, inverted (check not traced to a real observation).
- Everything else at the gate was HEALTHY: T1–T4 PASS both arms (MEM 11
  cells / NOMEM 12; paired gate 22 + 15 decisions, 0 fallbacks; all score
  vectors coherent, len 300). MEM best .7689 / NOMEM .7600 (single-eval).
- MEM memory loop was warming up exactly as designed: first card admissions
  at T+57min (17 STORE_WRITEs, 5 auction runs), and the 5 read-selections
  after the first write ALL had non-empty candidates (one auction_rejected);
  3 children with `memory_used=True` persisted before the kill. The T5-W/T6
  0-injection WARNs were pure cold start, self-resolving at abort time.
- Fix: `check_allin_progress.py` T7 now counts only truthy ACTIVE signals
  (`memory_used`, `memory_selected/injected/lineage_applied/base_selected`
  id lists, `memory_candidate_slate`, `memory_no_card_control`) and also
  globs `memory/memory_events.jsonl` as a bank artifact. Validated on the
  aborted data: NOMEM PASS (regression), MEM FAIL as positive control
  (206 log lines, 1 event file, 3 active programs).
- RELAUNCH TS=20260712_000307: MEM pid 748447, NOMEM pid 748448, bank
  `SHARE_HOVER_DIFF_MEMORY_ALLIN_R1_20260712_000307`; smoke + treatment
  self-check green; watchdog re-armed (same 1h gate / 3h / 6h schedule).
  Prereg + A1/A2 unchanged.

## 2026-07-12 — NIGHT QUEUE: auto-replicate armed (user directive "launch a copy when it finishes")

- `relaunch_allin_replicate.sh` detached (pid 749869): waits for pair
  TS=20260712_000307 (MEM 748447 / NOMEM 748448) to exit, then for its
  watchdog to finish the final sweep (it re-reads latest_allin.env, which a
  new launch overwrites), then launches an identical second pair (fresh TS,
  fresh bank) + its own watchdog. Gate-abort guard: if the run root was
  renamed `*_aborted_*`, the queue cancels with a Telegram note instead of
  replicating a broken pair. Launch line blanks inherited TS/RUN_ROOT/bank
  so the launcher derives fresh paths.
- Analysis impact: closeout pools winners from both pairs (2 MEM + 2 NOMEM)
  for the A1 K=5 re-eval verdict; prereg bars unchanged.

## 2026-07-12 — PAIR 1 CLEAN FINISH; replicate queue fired; MMR selection + TEST eval

- Pair TS=20260712_000307 finished cleanly ~07:16 (7.2h). Final watchdog
  sweep: ALL checks pass, incl. fixed T7 on NOMEM (0 active memory signals,
  0 bank files). MEM 13 cells / NOMEM 10; paired gate MEM 4/17 ACCEPT,
  NOMEM 11/26, 0 fallbacks. Night queue worked end-to-end: replicate pair
  TS=20260712_071628 launched 07:17 (MEM pid 794461 / NOMEM 794462) + its
  watchdog; pair-2 1h hard gate PASSED all checks at 08:17.
- NEW `mmr_top10.py` (user directive): MMR-rank a pair's pooled top-10 via
  the existing paired machinery — full pairwise P(A beats B) matrix from
  `PairedBootstrap.probability_better` on the stored 300-sample score
  vectors (both arms share the fixed val set, so cross-arm duels are
  paired), Bradley–Terry MM fit on the soft win counts, Elo-style display
  (1500 + 400·log10 s). Pool admits `discarded` challengers deliberately —
  the archive gate's rejection is one duel vs one incumbent; MMR
  re-adjudicates globally. Records → mmr_results.jsonl.
- Pair-1 MMR (490 eligible): winner NOMEM e0f1a2a1 (val-soft .8144, MMR
  1789, mean win-prob .860 vs the other 9 — dominant). MEM stored top-1
  47a27f88 (.8056, state=discarded — gate-rejected challenger that
  `gigaevo top` still ranks #1 by raw fitness) lands rank 3 (MMR 1547).
- TEST eval (hard metric): `eval_test_hard.py` fixed — chain tools must go
  through `run_chain_on_dataset_stepwise(batch_tool_registry=...)` exactly
  as full7/validate.py wires them (batch fns `list[dict] -> list[str]`);
  passing them as the per-sample `tools` arg TypeErrors on `query=`.
  K=5 eval of NOMEM e0f1a2a1 (= MMR winner) + MEM 47a27f88 on the 300-claim
  TEST split RUNNING in background; results → test_eval_results.jsonl.
- Run-end waiter armed for pair 2 (pid 833093, frozen TS=20260712_071628):
  on clean finish runs mmr_top10.py on pair 2, then K=5 TEST hard-metric
  eval of both arms' final top-1 + the MMR winner (if distinct), Telegrams
  the table. Same abort guard + watchdog-exit wait as the replicate queue.

## 2026-07-12 — PAIR 2 CLEAN FINISH; A1 verdict NO-WIN (tie); BRANCH CLOSEOUT (full report + defaults)

- Pair TS=20260712_071628 finished cleanly (~7h); run-end waiter fired
  end-to-end (MMR + TEST evals + Telegram, delivered late via retry queue —
  box-wide internet outage mid-campaign). Final sweeps both pairs: ALL
  treatment checks PASS (T1 occupancy 33/38/41/27 cells; T4 paired gate
  949 decisions 0 fallbacks; T5-W 55/55 & 54/54 gain_se>0; T5-R posteriors
  move, max |Δ| .51/.45; T7 NOMEM pure). Deviation: T6 injection 57.9%/61.8%
  vs 30–55% band (WATCH, not abort); top-card reuse 27×/39× under the 60× bar.
- Pair-2 MMR (494 eligible): winner MEM 40fecc90 (val .8367, MMR 2504, mean
  win-prob 1.000 — entire top-10 is MEM). Cross-pair pooled MMR (984): same
  program rank 1 (mean P .996 vs 11 finalists; P .971 vs runner-up P1_NOMEM
  e0f1a2a1).
- TEST hard (K=5, 300 held-out claims): P2_MEM 40fecc90 62.7±1.9 — campaign
  best, +7.3 pts over best NOMEM (55.4), +16.0 over seed (46.7); beats all
  prior Qwen-mutator finals (56.7–59.0). P1_NOMEM 54.9, P1_MEM 54.7,
  P2_NOMEM 55.4. Soft val→test drop ~.01 across the board (no overfit).
- A1 K=5 val re-eval (per-claim vectors, protocol = eval-noise study;
  reeval_winners_vec.py → reeval_results_vec.json; verdict a1_verdict.py →
  a1_verdict.json): P2_MEM .8229±.0097 (curse −.0138) > P1_MEM .7942±.0046
  > P1_NOMEM .7900±.0053 (curse −.0244) > P2_NOMEM .7831±.0057; prior champs
  re-eval MEM_R1 .8298±.0077 / NOV_R2 .8291±.0063. Paired: P2_MEM vs priors
  diff −.0069 (p=.50) / −.0062 (p=.13) = statistical TIE; all three other
  winners SIG below both priors (p<.0001).
  **A1 VERDICT: NO-WIN** (bar >.8298 not met, no sig superiority; prereg
  asymmetry WIN⇒genuine / NO-WIN⇏worse applies — best winner is val-tied
  with the prior champions and campaign-best on held-out TEST).
- First A1 re-eval launch hung on the ambient-proxy trap (HTTP(S)_PROXY set,
  10.232.24.68 not in NO_PROXY); relaunched proxy-clean. Watchdog T5-W
  re-check regex bug found post-run ("T5-W.*WARN" vs actual "[WARN] T5-W");
  fixed + sweeps now echo to log, was benign both pairs.
- CLOSEOUT REPORT: hover_allin_closeout_20260712.pdf (TL;DR, A1, MMR
  methodology, TEST table, treatment evidence, winner chain analysis, issues
  log, defaults, next research) sent via Telegram. Memory verdict: val MMR
  split 1/1 across pairs, but campaign-best program is MEM and crediting is
  verified live — memory ON recommended as exploratory default with
  injection-band caveat.
- DEFAULTS (→ problems/chains/README.md, sign-off requested): vectorized
  problem + chains_bd3d + paired_bootstrap selector + guided_noise /
  memory_guided_noise (memory=full, write=live, crediting=paired) +
  num_parents=1; winner selection by pooled MMR, K=5 re-eval for headline
  numbers, TEST hard for external claims.
- NEXT: mutator-model lever — rerun recipe with gemini-3.5-flash mutator,
  bar = Part I winner (67.3/68.0) re-evaluated under the K=5 protocol;
  prereg to follow on go.
