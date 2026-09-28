# Preregistration: novelty-discounted auction bid (power=0.5) — hover full7

Date: 2026-07-11 (pre-launch). Branch: memory-cold-probe-policy (uncommitted).
Launcher: `launch_novelty_auction.sh` (verbatim mirror of
`launch_baseline_memory.sh`, single functional delta:
`+memory/auction=thompson_bootstrap_novelty`, novelty_power=0.5).
User approval: "Nevermind, finish novelty first. ... when fixed launch fixed
novelty experiments" (2026-07-11). Supersedes the falsified shortlist-side
treatment (prereg_novelty_20260711.md, w_nov=0.25 — proven inert: shortlist
order was not the lever; the auction is).

## Question

Does taxing repeat winners inside the auction — `bid × (1+use_count)^-0.5`,
where use_count = the card's non-founding gain events (its deterministic
injection count, no wall clock) — break single-card injection dominance while
preserving injection volume and not hurting fitness?

## Treatment

`NoveltyDiscountedBootstrapAuctioneer` (subclass of the production
`BootstrapThompsonAuctioneer`; only `_adjust_bids` overridden). The tax is
applied AFTER Thompson bid computation (consumes no rng → draw order pinned)
and BEFORE the EV reserve, which is a quantile (0.765) of the round's OWN taxed
bids — taxing a dominant card drags the floor down with it, so wins
REDISTRIBUTE to fresher cards instead of vanishing. Everything else identical
to the 20260710_041404 MEM control pair.

Provenance (offline replay of 4 finished runs' MEMORY_AUCTION_RUN slates,
2026-07-11; power=0 reproduced live winners bid-for-bid, 0 mismatches):
volume ±4%, top-card auction share down 20–35% at power 0.5–1.0.

## Arms

- NOVAUC_R1 / NOVAUC_R2 — new pair, novelty auction power=0.5, 250 mutants each.
- Control: MEM_R1 / MEM_R2 (outputs/hover-diff-memory-baseline-20260710_041404),
  base auction, same launcher otherwise.
- Reference: NOV (w_nov=0.25) pair, EXPL pair, NOMEM pair.

## Causal chain

Tax scales a card's k-th injection bid by (1+k)^-0.5 → dominant repeat winner's
bid falls relative to fresh cards AND the round's EV floor falls with it →
auction wins redistribute to fresher cards at ~unchanged volume → (a) top-card
share of auction wins falls, (b) more cards accrue reputation evidence,
(c) IF diverse cards carry independent useful ideas, with-card deltas improve;
if the dominant card was genuinely the only useful one, fitness flat-to-down.

## Riskiest link

Live feedback the replay cannot see: redistributed wins change which cards
accrue posterior evidence, which changes future bids (replay held posteriors
fixed at their logged values). The equalizing tax could rotate mediocre cards
into prompts faster than reputation can sort them, diluting prompt quality.
This is exactly what S1 (with-card delta) is for.

## Endpoints (variance discipline)

Mechanism endpoints are computed against the run's OWN power=0 counterfactual:
at closeout, replay each NOVAUC run's logged MEMORY_AUCTION_RUN slates with the
tax removed (same rng, same posteriors) and diff. Within-run, deterministic,
zero sampling noise — no cross-run variance enters the mechanism verdict.

- **P1 dominance**: top card's share of auction wins, per run, vs its own
  untaxed counterfactual. Predict: strictly lower in both replicates; relative
  reduction ≥10% in any replicate whose counterfactual share exceeds 12%
  (tax only bites when there is a repeat winner to tax).
  Falsified if: share not lower in either replicate whose counterfactual
  share exceeds 12%.
- **P2 volume**: total auction wins within ±5% of counterfactual, both reps.
  Falsified if: outside ±10% in either rep (the redistribute-not-shrink
  property failed live).
- **P3 coverage**: distinct auction-winning cards ≥ counterfactual, both reps.
- **P4 sanity (cross-run, descriptive)**: actual max injections/card in the
  range of the MEM controls (17 / 26) or below; probe-lane fraction of
  injections comparable to control (R1 96/187, R2 76/303 — the probe lane is
  untouched by the treatment and should not move).

Secondary — statistical, reported with mean±SD + bootstrap 95% CI +
Mann-Whitney U:

- **S1**: with-card per-mutation fitness delta vs pooled MEM pair (pooled
  with-card mean −0.0052 vs without −0.0251, n(with)=198). Bar:
  non-inferiority (no significant harm at MW p<0.05).
- **S2**: population fitness of valid programs, mean±SD.

Descriptive only — **D1**: best-of-run re-evaluated K=5 (reeval_winners.py)
→ mean±SD + CI. Controls: MEM re-eval means 0.8298±0.0109 / 0.7893. n=2/arm
with single-eval σ≈0.0078 cannot resolve small fitness effects; this pair is
powered for MECHANISM, fitness is directional only. No conclusions from
single in-run point estimates.

## Prediction table

| # | Metric | Control / counterfactual | Prediction | Falsified if |
|---|--------|--------------------------|------------|--------------|
| P1 | top-card share of auction wins | own power=0 replay | lower both reps; ≥10% rel. drop where cf share >12% | not lower in a rep with cf share >12% |
| P2 | auction win volume | own power=0 replay | within ±5% both reps | outside ±10% either rep |
| P3 | distinct auction winners | own power=0 replay | ≥ counterfactual both reps | < counterfactual either rep |
| P4 | actual max injections/card | MEM: 17 / 26 | ≤ control range | >2× control max (>52) |
| S1 | with-card delta vs MEM pooled | −0.0052 (n=198) | non-inferior, MW ns or better | significantly worse |
| D1 | best-of-run K=5 re-eval ± CI | 0.8298 / 0.7893 | no prediction | — |

## Decision rule

P1–P3 decide whether the auction tax works mechanically LIVE (replay already
proved it offline; live feedback is the open question). S1 decides shipping:
mechanism holds + fitness non-inferior → propose `thompson_bootstrap_novelty`
as adaptive-preset default (user approval before any config-default change).
Mechanism holds but S1 significantly worse → do not ship; inspect which
newly-rotated cards harmed. P2 fails (volume moved >10%) → the
redistribute-not-shrink property is replay-only; revisit ev_floor_quantile
coupling before any rerun.

## Treatment-consumption check (within ~1h of launch)

Per the output-consumption rule: verify the treatment changes DECISIONS, not
just code paths. From live MEMORY_AUCTION_RUN telemetry: (a) slate rows carry
`use_count`, with >0 values appearing once cards accrue events; (b) recompute
raw bid = bid × (1+use_count)^0.5 and confirm at least one round where
argmax(raw) ≠ argmax(taxed) — i.e. the tax flipped a winner; (c) composed cfg
dumps show `NoveltyDiscountedBootstrapAuctioneer` + `novelty_power: 0.5`.
(b) not yet observable at 1h if no card has repeated — then re-check at
half-run.

## Issues log

- (pre-launch) 2026-07-11 — control figures corrected vs the w_nov prereg:
  the "86×/26×" P1 control there was stale (it referenced the 20260709 pair);
  the actual 20260710_041404 MEM controls are max-card 17 (R1) / 26 (R2), of
  which 14 / 22 came via the auction lane. Dominance is auction-driven (probe
  fills are cold-card-spread), so the treatment targets the right channel.
- (launch) 2026-07-11 11:57 — TS=20260711_115748, PIDs R1 641650 / R2 641651.
  All smoke checks passed (3 proxy models + 8 direct backends). cfg diff vs
  baseline dump = exactly one functional delta (auctioneer class +
  novelty_power 0.5). Watchdog detached pid 642921.
- (1h check) 13:03 — use_count field flowing, all zeros; support_n also 0 for
  every card = normal attribution lag (baseline firsts at 61/93 min), not a
  treatment failure. Re-check scheduled at half-run per prereg.
- (half-run check) ~16:05 — TREATMENT-CONSUMPTION CHECK PASSED. use_count
  growing (R1 max 19, R2 max 6; R1 243/435 slate rows taxed). Tax FLIPS
  winners: R1 27 rounds, R2 6 rounds where taxed argmax ≠ untaxed argmax
  (e.g. R1 mem-036c1581d48b use=8 loses to fresh mem-02df070f2a03 use=0,
  positive winner) — the decision, not just the code path, changes. Health:
  0 tracebacks both runs. Watch item: R1 top card mem-ea7f174aaca9 already at
  25 auction wins by half-run while taxed — P1's counterfactual replay will
  decide whether the tax reduced its share vs untaxed.
