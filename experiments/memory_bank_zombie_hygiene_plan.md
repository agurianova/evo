# Memory bank zombie hygiene — benched cards clog read-path attention

Status: BUILT + LAUNCHED 2026-07-06 (uncommitted). Tier 1 SHIPPED test-first (`gigaevo/memory/read/shortlist.py` digest exclude_ids + `gigaevo/memory/read/fused.py` `_bank_bench` upstream merge, active only with `rep_floor_quantile`); HARD GATE PASSED on the 32 recorded evalD decisions — winners ∩ benched = ∅ under BOTH pin (p_help<0.44 ∨ mag≤0) and shipped q=0.4 semantics, benched-in-slate = 0, all benched were losers (`replay_gate.py`, scratchpad). Decay SHIPPED as `DecayingReputation` (`gigaevo/memory/read/decay.py`, tests `tests/memory/read/test_decay.py`), default OFF in shared config; opt-in group `config/memory/reputation/bd_proximity_decay.yaml`. Full memory suite 130 green + ruff clean. USER DIRECTIVE: full bundle (quantile gates + Tier-1 exclusion + decay) LAUNCHED live as V3/V4 pair — `outputs/memory_rebuild_zombiefix_2026-07-06/` (PIDs 1270164/1270183, 500 mutants each, fresh banks; ablation waiver granted). Tier 2 PARKED. Census: 2026-07-05, evalB bank snapshots V1/V2/G1/G2, script `zombie_census.py` (scratchpad).

## Definitions (current — Bootstrap-EV redesign, 2026-07-06)

The bench, the EV floor, and the reputation summary below were originally
defined on the binarized `p_help` × median-magnitude model. That model is
tail-blind: it discards every loss magnitude and prices the win at the median,
so a card whose wins outnumber its losses but craters far more per loss reads as
positive. The Bootstrap-EV bundle re-grounds all three on the mean of a weighted
bootstrap over each card's RAW oriented deltas (`gigaevo/memory/read/bootstrap.py`).
Opt-in via `memory/reputation=bootstrap_ev` + `memory/auction=thompson_bootstrap`
+ shortlister `_target_=…fused.BootstrapFusedRankingShortlister`. Read the Tier-1
prose below as the historical p_help/median framing; these are the live
definitions that supersede it:

- **Reputation summary** (`BootstrapReputation`, decorates BD-proximity/BetaBinomial):
  re-prices only the three gain-EV block fields — `IntroGain_best_median` → the
  bootstrap-EV **mean** (a fat left tail drags it below zero), `p_help_lo20` →
  the bootstrap-EV **low quantile** (pessimistic EV, the successor to the Beta
  lower-tail probability), `efficacy_confident` → `ev_lo > 0`. The inner Beta
  downside posterior the harm gate reads is untouched.
- **Tier-1 bench** (`BootstrapFusedRankingShortlister._bank_bench`): scoped to
  WARM cards only (a cold / founding-only card carries the inner Beta block whose
  `p_help_lo20` is a probability, not a gain — pooling it would be a unit error;
  cold cards are also the exploration pool the census found truncated, so they
  are never benched). A warm card is benched iff its bootstrap-EV low quantile
  falls below the q-quantile of the warm EV-low distribution, OR its bootstrap-EV
  mean ≤ 0 (a fat-left-tail card lands here even with more wins than losses).
- **EV floor** (`BootstrapThompsonAuctioneer`): two self-normalizing gates, no
  Beta assumption and no absolute scale. (1) Sign gate `bid > 0` — never inject a
  card you expect to hurt; this alone yields the abstain-on-all-harmful guarantee.
  (2) Spread reserve `bid ≥` the `ev_floor_quantile` quantile of the round's OWN
  bids, inclusive so a degenerate round of equal bids (all cold, every bid the
  borrowed scale) does not self-annihilate — the cards clear the reserve and the
  safety gate alone thins them, keeping cold cards explorable.
- **Staleness** is the one bank-cycle mechanism `bank_cycle_weight`
  (`w = 2^(−s/H)`), shared with `DecayingReputation`: here it enters as the
  per-event bootstrap resample weight, so a stale card's own deltas fade and the
  unit-weight cold pseudo-event dominates — its EV relaxes to the borrowed cold
  gain scale (pseudo-cold amnesty), no benched-forever freeze.

Offline verification (replay of the 32 recorded evalD slates through old vs new,
`replay_D.py` scratchpad): non-degenerate (no all-win / all-lose); recorded
slates are ~all cold, so the flips are cold cards relaxing from the old EV-floor
gate (~0.18 fire) to the bare safety gate (~0.5 fire) — the intended
cold-exploration restoration. The dataset holds no warm fat-left-tail card, so a
synthetic direction micro-check confirms the mechanism: fat-left-tail
(median +0.01, mean −0.09) fire 0.86 → 0.11, small-clean-positive (mean +0.005)
fire 0.09 → 0.79. Launched as the bootstrap A/B pair, `outputs/memory_rebuild_bootstrap_2026-07-06/`.

## Problem

The choosy read path (rep_floor_quantile + ev_floor_quantile) benches cards but never removes them from the bank, the research digest, or the vector index. Benched cards earn no new events, so their state freezes: they are permanent. Census of the four real heilbron banks under the shipped config semantics:

| bank | n | rep-benched | ev-neg (mag<=0) | ev-small | union benched | digest slots eaten | cold cards starved out of digest |
|---|---|---|---|---|---|---|---|
| V1 | 66 | 26 | 10 | 4 | 28 (42%) | 28/50 (56%) | 16/16 overflow all cold |
| V2 | 86 | 32 | 18 | 1 | 37 (43%) | 37/50 (74%) | 36/36 overflow all cold |
| G1 | 56 | 21 | 18 | 3 | 24 (43%) | 24/50 (48%) | 6/6 overflow all cold |
| G2 | 40 | 16 | 19 | 1 | 20 (50%) | 20/40 (50%) | 0 (bank under cap) |

Two structural facts make this worse than passive dead weight:

1. **The digest freshness order is anti-correlated with selectability.** `_bank_digest` sorts by latest gain-event timestamp (newest first) and puts never-evented cards LAST. Benched cards HAVE recent events (that is how they got benched), so they sit at the TOP of the planner's 50-line digest; fresh cold cards — the most selectable class — are exactly the ones truncated (V2: all 36 dropped cards are cold). The planner is shown the dead cards and hidden the live ones.
2. **ev-neg cards (IntroGain_best_median <= 0) can never win under ANY config**, including the pre-existing default `ev_floor=0.0` (selection requires bid = theta x magnitude strictly > floor >= 0). This zombie class (10-19 per bank) predates the choosy change; the new floors only made it explicit.

Downstream: zombies eat Chroma top-k hits, digest lines, and research-LLM slate picks; the fused floor then drops them post-hoc, thinning slates -> fire rate decays as the bank grows; bank growth is monotone.

## Causal chain (signal -> behaviour -> metric)

Benched-card ids computable at read time (reputation floor + non-positive magnitude) -> exclude them BEFORE research (digest + index + LLM shortlist) instead of after -> planner digest fills with selectable cards (incl. previously-starved cold cards), slates stop losing slots to auto-rejected candidates -> injection fire rate stays at calibration target as bank grows; digest zombie-occupancy drops from 48-74% to ~0%.

## Fix — Tier 1 (attention hygiene; no new state; self-normalizing)

Seams (per feedback_new_impl_behind_seams_not_modify — no new components, extend the existing choosiness home):

1. `ResearchShortlister`: `_bank_digest` must respect `exclude_ids` (today even lineage-excluded cards occupy digest lines). Small, independently correct.
2. `FusedRankingShortlister` (already holds reputation + store + context + floors): before delegating to the inner shortlister, compute the benched set under the CURRENT DecisionContext —
   - rep-benched: `p_help(card, context) < bank rep-floor quantile` (existing `_bank_rep_floor`, same knob, no new constants);
   - ev-dead: `reputation.card_magnitude(card, context) <= 0` (config-independent: provably unselectable);
   and merge those ids into `exclude_ids` for the inner run. Gate behind the existing knobs: active only when `rep_floor_quantile` is set (neutral reader.yaml wrapper stays a byte-identical no-op).
3. No change to bank/store/index contents. Fully reversible each round; context-conditional for free (a card benched near one behavior-space region re-enters elsewhere); zero absolute constants (veto-2 compliant).

Side effect that heals the starvation: freed digest slots (20-37 per bank) are backfilled by exactly the truncated cold cards.

## Fix — Tier 2 (bank growth bound; PROPOSED ONLY, needs separate approval)

Retire (quarantine out of snapshot + vector index, keep on disk for audit) cards that are BOTH globally `is_confidently_harmful` (pooled events, >= harm_min_events=3) AND stale (no events within the most recent half of the bank's event history — rank-based, self-normalizing). Context-conditionality makes eviction inherently lossy (benched-here != benched-everywhere), hence the conservative pooled-harm criterion and hence Tier 2 is optional if Tier 1 lands. Do not build unless post-Tier-1 metrics still show decay.

## Riskiest link

That research-LLM slate quality actually improves when zombies leave the digest — the planner might have been ignoring the dead lines anyway (LLM attention is not slot-limited the way the cap is). If so, Tier 1 buys fire-rate protection (slates stop losing members to the post-hoc floor) but not slate-quality lift. Mitigation: measure both (fire rate AND injected-episode conditional delta) in the verification A/B.

## Predictions

| metric | before | after Tier 1 |
|---|---|---|
| digest zombie occupancy (V2 bank) | 74% | ~0% |
| cold cards visible to planner (V2) | 26/62 | 62/62 (fits: 86-37=49 <= 50) |
| candidates surviving to auction per round | thin (pilot: 2) | >= before (no slate slots wasted) |
| injection fire rate over bank growth | decays | flat at calibration target |
| rep/EV floor semantics | unchanged | unchanged (same cards win) |

## Verification

- Unit: digest respects exclude_ids; fused merges benched ids only when rep_floor_quantile set; neutral config = passthrough (existing test extends); ev-dead exclusion only with reputation present.
- Offline replay (HARD GATE): re-run the 32-parent retrieval harness with Tier 1 on, assert (a) winner set unchanged vs arm D (same cards win — exclusion only removes auto-losers), (b) digest composition shift as predicted.
- `/run-tests` on tests/memory + ruff.

## Next-step candidate (gated): staleness decay of evidence toward the cold prior

User direction: "then we may add decay" — decide at the same gate as Tier 1 sign-off, with arm-D fire-rate data on the table. DESIGN ONLY until then.

Mechanism (one seam, everything downstream follows):
- Staleness `s` of a card = number of read DECISIONS (auction rounds) since the card's own latest gain event — internal rank count, no wall clock, no absolute constants.
- Half-life `H` = current bank card count at read time (one expected full-bank cycle of chances) — self-normalizing: decay speed scales with how fast the bank is actually being exercised.
- Evidence discount `w = 2^(-s/H)` applied to the Beta sufficient statistics in the `card_stats` seam: `(a_eff, b_eff) = (1 + w*(a-1), 1 + w*(b-1))`; effective intro_events scaled by `w` likewise.
- Emergent behavior, no extra rules: as `w -> 0` the posterior relaxes to the cold prior (Thompson gives the card its ~1/3 shot again); `magnitude_of` returns None below one effective event, so the auction re-borrows the round's cold gain scale (existing fallback); the harm gate (`intro_events >= harm_min_events`) EXPIRES automatically — a harm verdict older than ~2 bank cycles ceases to bench.
- Placement: a decorator reputation (`DecayingReputation` wrapping BetaBinomial/BDProximity) behind the existing reputation seam — new impl behind a Protocol, not a branch in current classes.
- Tradeoff to decide at the gate: decay periodically re-spends real mutations probing measured-harm cards (−0.0033 conditional per retry); the half-life bounds the rate to ~one amnesty per card per bank cycle. Tier 1 exclusion + decay compose cleanly: exclusion keeps a card invisible only while its (decaying) evidence still pins it below the floor.

Data owed at the gate (in arm-D RESULTS.md): fire-rate-over-time — (a) realized arm-D fire rate per bank vs that bank's zombie fraction (cross-sectional decay read), (b) reconstructed benched-fraction trajectory over each source run's event history (longitudinal read).

## Non-goals (current step)

- No decay implementation before the user gate above.
- No exploration epsilon on floors (adds a constant; not pulled).
- No digest reordering beyond exclusion (freshness order is fine once zombies are out).
