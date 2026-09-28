# memory=full default verification — two-reviewer pass (2026-07-13)

Two independent RL/math/bandits reviewers verified the shipped `memory=full`
defaults (read-only, live gemini run in flight). Self-agent (Opus) + Codex
(`gpt-5.6-sol` xhigh). Where they disagreed, the orchestrator adjudicated by
reading the code; the trace is recorded below.

## Agreed, no action
- **`memory/write=live` is the correct default.** Both confirm: reader+writer
  share one run-local store; `end_of_run` + default per-run `checkpoint_dir`
  leaves the reader on an empty bank all run, and the compose guard
  (`gigaevo/config/validation.py:139-150`) hard-rejects it. `live` is the only
  sound default for the shared-bank preset. (This is the change already made +
  queued for commit.)
- Sound as-is (both): `neutral_gain=0.0`, `baseline_prior=[3,3]`,
  `reader.max_cards=1` + recall `10/10`, `top_bid`, `bd_cell`, bootstrap
  means/Kish-N/`ev_lo_quantile=0.20`/`n_bootstrap=512`, `half_life_cycles=1.0`
  (the *value* is fine — see F1 for its *wiring*), EB seeds
  (`seed_prior=[1,1]`, `k∈[2,6]`, `n_ref=32`, `shrink_events=16`,
  `min_parameter=0.25`, `first_exposure_only=true`), shortlist
  `w_sem=1/w_rep=0/w_nov=0` + `rep_floor_quantile=0.4`, cold-probe mechanism
  (`empty=0.50`, `warm=0.03`), `confident_quantile=0.20/threshold=0.5`,
  birth-failure `scale_multiplier=2` + rescue floor, `PolicyNonViableEvictor`
  (correctly uses aged floor), `crediting=point` (honest default; `paired`
  stays opt-in), engineering defaults (`best_programs_percent=5`,
  `consolidation_every_n=32`, dedup `5/3/5`, exemplars `4/12/0`,
  `novelty_admission_gate=false`, `ingest_call_timeout_s=300`).

## Findings (ranked)

### F1 — CONFIRMED (orchestrator-verified in code). Harm eviction ignores staleness; breaks the probe/eviction partition.
Reviewers DISAGREED: self-agent claimed the partition is "bit-identical"; Codex
flagged CRITICAL. Adjudication (read the code) → **Codex is correct.**

Trace:
- Shared floor arithmetic `effective_support()` = aged `credit × staleness`
  (`gigaevo/memory/context/evidence.py:30-50`).
- Read/probe lane uses aged support: `bid.support_n < 3`
  (`gigaevo/memory/read/probe.py:37,90`); intent stated at `probe.py:56-58`
  ("no card falls between the probe and eviction lanes").
- `PolicyNonViableEvictor` honors it: aged `effective_support >= 3`
  (`gigaevo/memory/write/eviction.py:356`).
- `HarmEvictor` does NOT: `is_confidently_harmful(card_stats(card, context))`
  (`eviction.py:265-266`) with no `effective_support` guard. `card_stats`
  (`gigaevo/memory/read/reputation.py:951`) takes the UNAGED inner block
  (`:954`; inner `card_stats` passes `staleness_weights=None` at `:578`/`:822`),
  and `model_copy` (`:989`) ages ONLY the bootstrap-EV fields — never
  `intro_events`/`posterior_a/b`. `is_confidently_harmful` (`:700`) then gates
  on unaged `intro_events >= harm_min_events(3)`.

Failure scenario: a card with 3 old losses, each staleness ≈0.25 → aged support
0.75 `< 3`. Read side marks it probe-eligible (cold, keep exploring). Write side
sees 3 unaged events, optimistic harm quantile below 0.5 → tombstones it for the
whole run. Same card, both lanes at once.

Fix (surgical, restores the invariant, symmetric with `PolicyNonViableEvictor`):
gate `HarmEvictor.should_evict` on the shared aged `effective_support >=
memory.evidence.min_effective_events` before adjudicating harm. Optionally also
feed the harm gate an aged block via `card_stats_with_staleness` so a card that
DOES clear the aged floor has its harm mass computed on faded evidence too
(design question: whether harm evidence should fade at all — the min fix does
not require deciding this). TDD: failing test first (3 stale losses → not
probe-eligible-AND-evictable), then fix, then green.

### F2 — MAJOR (Codex; self-agent flagged same knob as MINOR). `harm_quantile=0.80` too weak for an irreversible tombstone.
`config/memory/reputation/bootstrap_bd.yaml` harm gate; consumed at
`reputation.py:700-704`, `eviction.py`. Optimistic `Beta.ppf(0.80) < 0.5` ≈ 80%
confidence, checked after every event → multiple-looks inflation (Codex:
~27% chance of ever tripping under a true non-harm prob of 0.60, neutral prior).
Also ignores positive-EV plausibility and gain magnitude
(`[-.01,-.01,-.01,+10]` → deletable despite mean +1.99).
Rec: harm eviction should additionally require no plausible positive EV
(e.g. bootstrap `EV_hi <= 0` or low `P(EV>0)`); interim raise `harm_quantile`
to ≥0.95 for the *eviction* read; leave reversible display/confidence at 0.20.
Read-side harm reads can stay 0.80.

### F3 — MAJOR (Codex only; NOT yet orchestrator-verified). Default auction is not pending-aware despite batched/delayed rewards.
`gigaevo/memory/read/auction.py:847` (`_adjust_bids` identity in the shipped
auctioneer), `provider.py:121`. Pending counts are projected but unused by the
default; the pending-discounted auctioneer defaults `pending_power=0` and no
preset selects it. Claim: 32 concurrent mutations can all snapshot
`pending_count=0` before any reward lands → up to 32 correlated exposures of one
card per batch. Rec: ship a pending-aware auction for `memory=full` +
atomically reserve selections with the pending snapshot.
**Needs independent verification** (interacts with `SharedSelectionRegistry`
leases from the cross-task work — may be partially mitigated there).

### F4 — MAJOR (Codex only; NOT yet orchestrator-verified). EB cold prior learns from survivors only (survivorship bias) + self-cohort leakage.
`gigaevo/memory/read/prior.py:256`, `writer.py:218`. Default writer supplies no
`evicted_evidence_sink`, so evicted (harmful) arms drop out of the cohort used
to estimate future cold priors; the queried card is also not excluded from its
own cohort. Codex worked example: default reverses a cohort's cold prior from
pessimistic (`μ≈0.24`) to optimistic (`μ≈0.76`). Rec: wire the existing JSONL
evicted-evidence source/sink into `memory=full`; estimate each card's prior
leave-one-card-out. **Needs independent verification.**

### F5 — MAJOR (both). `ev_floor_quantile=0.765` — single-task calibration + IIA violation.
`config/memory/auction/thompson_bootstrap.yaml:20-24`, `auction.py:705-714`.
Round-relative rank cut: a card's admissibility depends on which unrelated
candidates share the slate (add a stronger co-retrieved card → the same card
flips from eligible to rejected). Value picked offline on 27 heilbron
injections; self-normalizing in form but unproven cross-task.
The IIA-clean alternative is **already built + tested**: `ev_reserve_mode="risk"`
→ per-card `P(EV>0) >= 1-alpha` (`auction.py:596-608,716-722`;
`tests/memory/read/test_auction.py` covers `alpha=0.2`).
- Self-agent rec: wire `risk`/`alpha=0.2` (P(EV>0)≥0.8) as the new default now.
- Codex rec (more conservative): keep `0.765` only as a heilbron *experiment
  override*; for the cross-task default use `ev_floor_quantile=0` (rely on
  EV>0 + the family-wise no-card Sidak gate + top-1 budget) until `risk` mode is
  benchmarked broadly.
User has stated they dislike `0.765`. Decision pending: `risk/α=0.2` now vs
`quantile/0` interim vs A/B-first.

### F6 — MINOR (Codex only). EB ladder is heuristic chained shrinkage over crossed (not nested) cohorts.
`gigaevo/memory/read/prior.py:277`, `empirical_bayes.yaml:14`. Mean carried from
`task+kind+category` into `context` although these are crossed, not nested;
overlapping observations can influence multiple levels. `κ≤6` cap bounds the
damage. Rec: explicit nested paths or a crossed-effects model with one
leave-one-out update per edge. Low urgency.

## Proposed remediation order
1. Commit `write=live` (independent, both-confirmed, already green). — awaiting approval
2. F1 partition bug: failing test → surgical `HarmEvictor` aged-floor guard → green. Highest-value correctness fix.
3. F5 `ev_floor` 0.765: user dislikes it; pick `risk/α=0.2` vs `quantile/0` interim (decision pending).
4. F2 `harm_quantile`→0.95 + positive-EV veto (bundle with F1, same eviction path).
5. F3 pending-awareness, F4 EB survivorship: verify independently first (Codex-only, larger design); schedule as their own changes, not defaults-polish.
6. F6 EB coherence: park.

All code changes gated on commit approval; a live gemini run (pid 1633834) is
using this code (editing source does not affect the running process).

## Status 2026-07-13 (implemented this session, awaiting commit approval)
User decision (AskUserQuestion): fix F1 (TDD, surgical); fix F2 `harm_quantile`;
F5 → `risk` mode, α=0.2; verify F3/F4 first. DONE:

- **write=live** — `config/memory/full.yaml` default flipped to `write: live`
  (+ WHY comment); compat guard test updated
  (`tests/config/test_memory_pipeline_compat.py`:
  `test_full_default_write_is_live` + end_of_run now overrides explicitly);
  docs synced (`docs/memory.md`, `docs/MEMORY_LIFECYCLE_TUTORIAL.md`,
  `problems/chains/README.md`).
- **F1 DONE (TDD).** `HarmEvictor` widened `scorer: CardValueScorer` + new
  `min_effective_events` param (defaults to `scorer.policy_min_effective_events`,
  mirrors `PolicyNonViableEvictor`); `_is_harmful_in_context` now returns False
  when aged `effective_support(...) < min_effective_events`, so a probe-eligible
  (aged-cold) card can no longer be harm-tombstoned. Wired in
  `config/memory/evictor/recommended.yaml`
  (`min_effective_events: ${memory.eviction_safety.min_effective_events}` → 3).
  Failing test first: `test_harm_eviction_respects_shared_aged_support_floor`
  (`tests/memory/write/test_eviction.py`) — 3 stale losses, aged support ≈1.56
  `< 3` while unaged intro_events=3; RED before fix (evicted), GREEN after.
- **F2 DONE (config only, the interim raise).** `harm_quantile` 0.80 → **0.95**
  at both occurrences in `config/memory/reputation/bootstrap_bd.yaml`
  (BDProximity in-cell + BetaBinomial fallback) with WHY comment (irreversible
  tombstone + multiple-looks inflation). Class Field default left at 0.80 to
  avoid churning tests that construct `BetaBinomialReputation()` directly.
  **positive-EV veto: implemented 2026-07-14 (Option A) — see the
  2026-07-14 section below.**
- **F5 DONE.** `config/memory/auction/thompson_bootstrap.yaml`: removed
  `ev_floor_quantile: 0.765`, added `ev_reserve_mode: risk` + `ev_risk_alpha:
  0.2` (per-card P(EV>0) ≥ 0.8, IIA-clean); header/field comments rewritten.
  Preset tests updated (`test_read_policy_presets.py`:
  `test_ev_reserve_is_bootstrap_policy_local` + default-stack guards for
  risk-mode / harm_quantile=0.95 / HarmEvictor.min_effective_events=3). Novelty
  preset (`thompson_bootstrap_novelty.yaml`) deliberately left on
  `ev_floor_quantile` (separate opt-in, out of F5 scope).
- **F3 / F4** — CONFIRMED by independent subagent verification; both are larger
  design changes (ship a pending-aware auction; wire `EvictedEvidenceSink`
  through the writer) scheduled as their own work, NOT this defaults-polish pass.

Gate: 103 preset/compat/auction tests + 680 memory read/write tests green; ruff
check + format clean on touched paths.

## Status 2026-07-14 (second dual-reviewer pass — implemented, awaiting commit approval)
Follow-up round closing the two items the 2026-07-13 pass left open (F2 veto,
F5 IIA), plus a config-propagation sweep. Same read-only constraints (live gemini
run in flight; editing source does not touch the running process).

- **F2 positive-EV veto — IMPLEMENTED (Option A).**
  `HarmEvictor._is_harmful_in_context` (`gigaevo/memory/write/eviction.py:309-312`):
  after the sign gate returns "confidently harmful", the card is spared when its
  optimistic `IntroGain_bootstrap_ev_hi80 > neutral_gain` (finite). A missing or
  non-finite `ev_hi80` leaves the sign gate standing (fail-closed). Rationale: the
  `Beta.ppf(q) < 0.5` sign gate is magnitude-blind, so a fat-tailed winner (rare
  large gains, frequent small losses) can read confidently harmful yet have
  positive optimistic EV — Option A vetoes exactly that case without softening the
  gate for genuine sign-negative cards.
- **F5 IIA — card-local risk vector (Codex-2 fix).** `_risk_probability`
  (`auction.py:630`) now seeds a SEPARATE generator
  `stable_rng(card_id, len(deltas), n_bootstrap)` for the `P(EV>0)` reserve
  probability, decoupled from the shared-stream bid vector. Two consequences:
  (a) admission is order-independent (a card's `ev_positive_probability` no longer
  depends on which candidates precede it in the round's RNG draw); (b) the risk
  gate consumes NONE of the shared round RNG, so bids/theta/baseline stay
  byte-identical to a `quantile` run. Tests rewritten in
  `tests/memory/read/test_auction.py`:
  `test_risk_gate_consumes_no_shared_rng` (risk vs quantile bids byte-identical;
  probability reconstructed from the card-local `stable_rng`) and
  `test_risk_reserve_admission_is_order_independent` (target placed at a different
  RNG draw position alone vs trailing a strong slate → genuinely regresses
  order-dependence; the old `_RiskAtomsRng` fake masked it with fixed indices and
  was removed).
- **B-2 — `harm_quantile=0.95` propagated to ALL reputation presets.** The
  2026-07-13 pass raised only `bootstrap_bd.yaml`; this round brings every preset
  a `memory=full`-adjacent run can select to the same conservative bar. All 11
  occurrences across 7 files now `0.95`: `beta_binomial`, `bootstrap_global`,
  `bootstrap_global_decay`, `bd_proximity` (×2), `bd_proximity_decay` (×2),
  `bootstrap_bd_decay` (×2), `bootstrap_bd` (×2, already 0.95). Full WHY comment on
  each fallback occurrence; a back-reference on the in-cell twin.
- **Docs synced.** `docs/memory.md` (risk default + card-local decoupling +
  harm-gate aged floor + EV-hi80 veto + 0.95 bar) and
  `docs/MEMORY_LIFECYCLE_TUTORIAL.md` (EV-reserve table row, partition section,
  bootstrap-auction step 5, HarmEvictor predicate now
  `effective_support >= min_effective_events AND Beta.ppf(0.95) < 0.5 AND not
  (ev_hi80 > neutral_gain)`).
- **Second-pass reviewers.** Self correctness reviewer: NO MAJOR ISSUES (F1/F2/F5/
  B-2 all verified correct + load-bearing, incl. empirical byte-identity of the
  shared RNG across quantile-vs-risk and a 1600-pair monotonicity sweep of the
  0.95 harm bar). Self test-quality reviewer: one blocking gap — risk × cold /
  zero-support cards had zero coverage; CLOSED with
  `test_risk_gate_admits_cold_card_unconditionally` (cold → `P=1.0`, admitted) and
  `test_risk_gate_rejects_zero_support_known_card` (empty-delta known card → all-
  zero bootstrap atom → `P=0.0`, rejected at any α<1). Two doc MINORs fixed in
  `docs/memory.md`: the legacy `quantile` reserve is retained by the
  `BootstrapThompsonAuctioneer` class default + `thompson_bootstrap_novelty` (the
  `*_legacy` policies use a different auctioneer with no EV reserve — the old
  "`*_legacy` read policies" phrasing was wrong), and the risk default's reach is
  every `thompson_bootstrap` consumer, i.e. `memory=reader`/`portable` too, not
  only `memory=full`.
- **Residuals parked.** B-1: `risk` mode changes the no-card Sidak gate's
  `eligible_count` (fewer round-relative rejections upstream of it) — behavioural,
  not a bug; flagged for A/B monitoring, not a code change. B-1b (launch-note
  item): relative to `quantile`, `risk` reprices the reserve at BOTH tails — more
  permissive for cold cards (empty deltas → `P=1.0`, always clear the reserve vs a
  round-relative floor that could starve them in strong rounds) and stricter for
  thin warm evidence (a lone positive observation gives `P(EV>0)≈0.75 < 0.8` →
  rejected). Both ends are caught by the cold-probe lane (`support < 3` →
  probe-eligible) and volume stays bounded by `top_bid`, so no card is permanently
  starved; surface this in the A/B launch note so the shift reads as intended, not
  noise. B-3:
  `thompson_bootstrap_novelty` deliberately keeps `quantile` at `q=0.765` (novelty
  is a separate opt-in). B-4: `config/memory/evictor/harm.yaml` needs no edit — its
  `HarmEvictor` defaults (`neutral_gain=0.0`, auto-derived `min_effective_events`,
  `skip_contextual_without_context=True`) already match `recommended.yaml`.
- **Convergence (2026-07-14).** All reviewers agree no major / critical-minor
  issues: self correctness, self test-quality (blocking gap closed), self
  re-adjudicator, and Codex gpt-5.6-sol xhigh across two passes. Codex
  re-adjudication (task-mrjskswu-7300rf) verdict "NO MAJOR ISSUES REMAIN" —
  Finding 1 WITHDRAWN, Finding 2 downgraded to design-note, Finding 3 WITHDRAWN,
  minimal patch: none for all three. Codex confirmed both of its own suggested
  fixes would REGRESS a deliberate property (F1 fix → spares a strongly-negative-
  aged-EV card via the magnitude-blind Beta; F3 fix → reintroduces order-dependence,
  breaking F5's IIA). Codex did construct a REALISTIC bounded-delta instance of the
  F2 shape (6×−0.001 fresh + 1×+1 aged @ staleness 0.198 → mean +0.0267,
  ev_hi80 −0.00057, P(EV>0)=0.166) — coherent, not a violation: that same card sits
  far below the P(EV>0)≥0.8 auction-admission bar, so the reader never injects it
  while the evictor retires it. Read-side retire bar and write-side admit bar stay
  consistent. Stop-hook condition satisfied → surgical commit + push.
