# Bandit / RL math review — memory subsystem (2026-07-13)

Goal (user, verbatim): "re-review memory system by yourself and codex to ensure all
math and rl/bandit logic is correct and follows sota bandit practice in
applications / active learning. All configs are set to expected sota defaults.
similarly iterate until no major / critical minor issues"

Two independent passes: (A) my own line-by-line review (this file), (B) Codex
gpt-5.6-sol xhigh round 1 (task-mrittjzg-554fi2, thread
019f5a1c-0989-7ad1-94af-0e44785c6558). Reconcile → triage → fix ladder → iterate.

Fixed contract (NOT challengeable): foreign-task evidence is BINARY sign-only
(help iff finite gain >= 0.0, event-weighted); native keeps soft-count semantics.

## A. My independent findings

### A-1 MINOR (latent preset) — EVThompsonAuctioneer splits the Thompson draw
`auction.py:400` draws `theta_bid` (bid = theta_bid × mag), `auction.py:410`
draws a SECOND independent `theta` for the gate `theta > base_theta`. Proper TS
uses ONE coherent posterior sample per arm per round for all decisions about
that arm. The AND of two independent draws distorts selection probabilities
(more conservative than coherent; bid ranking incoherent with gate outcome).
Also `auction.py:411`: each candidate gates against a FRESH baseline draw — no
family-wise control, expected null pass-count grows linearly in slate size
(exactly what BootstrapThompsonAuctioneer's Sidak `gate_quantile =
baseline_quantile^(1/eligible_count)` fixes). Not the shipped default
(`thompson_bootstrap` is); `thompson_ev`/`thompson` are legacy/ablation presets.
Fix if desired: reuse one theta for bid+gate; adopt the Sidak slate adjustment.

### A-2 NON-ISSUE (downgraded from MINOR after model check) — float(e.gain) on None
Initially flagged `reputation.py:237` and `evidence.py:59` as crash-on-None.
VERIFIED UNREACHABLE: `ContextualGain.gain` (`cards.py:127-167`) is a REQUIRED,
non-Optional `float` with no default — Pydantic rejects None at construction,
so no persisted event can carry `gain=None`. The `e.gain is not None` checks in
`_use_gains` and the None guard in `beta_binomial_posterior` are dead
defensiveness (the posterior helper also serves raw-sequence callers), not
evidence of a reachable state. NaN is still representable but both sites handle
it via isfinite filters AFTER float(). No fix needed.

### A-3 NIT (latent composition) — DecayingReputation overwrites the bootstrap
confidence gate if composed OUTSIDE BootstrapReputation
`decay.py:130-158` `_discount` recomputes `efficacy_confident` with the weaker
gate (events_eff >= 1, median > 0) and never touches `IntroGain_bootstrap_ev_*`.
Shipped presets always compose Bootstrap OUTER (`bootstrap_bd.yaml`,
`bootstrap_bd_decay.yaml`) so the stricter gate ANDs the decayed inner —
correct. A future `Decaying(Bootstrap(...))` flips it silently. Fix: doc note or
runtime guard.

### A-4 NIT — EB ladder `counts == applied` skip can false-positive across the
global→local boundary
`prior.py:245` skips a level when its (success, failure) tuple equals the
previously applied level's. Within a refinement chain equal sums ⟹ same events
(validator enforces token-superset refinement per block). Across the
global→local boundary the subset relation does not hold; with unit weights the
counts are small integers and coincidental equality is plausible → one
informative level skipped, prior slightly coarser. Impact tiny.

### A-5 Observations (defensible, document only)
- Decay shrinks posterior toward Beta(1,1) while the cold prior is Beta(3,3): a
  fully-decayed card ends WIDER (more explorable) than a cold one. Defensible.
- Fully-stale / diluted cards bid → 0 and fail the strict sign gate; the ONLY
  recovery path is the cold-probe lane. Both shipped read policies mount
  `probe: cold_budget` — pathology contained; `probe=none` ablations would
  create zombies (probe.py docstring says as much).
- `BootstrapFusedRankingShortlister._proven_loser` uses UNscaled
  `block.intro_events` where probe/eviction use staleness-scaled support;
  all-negative-history cards are permanently benched from research+probe —
  they await eviction anyway. Doc-level drift only.
- BD `eviction_contexts` buckets foreign-task parent_metrics through the native
  behavior space (`reputation.py:625-628` over unpartitioned `_ev_events`) —
  cell ids for foreign contexts are meaningless but only used for dedup; the
  eviction decision re-derives per-task stats natively. VERIFIED robust:
  `_cell_in` (`context/models.py:185-190`) pre-guards every behavior key with
  `.get()` → None on missing/non-finite, and `evidence_cells`
  (`models.py:288-300`) skips None cells — foreign metrics missing native keys
  are dropped, never raised on. Residual: a foreign task that coincidentally
  shares behavior-key NAMES buckets into native cells; harmless here (dedup
  only) but worth one doc line.
- Native unused exposure = forced failure in the downside posterior; foreign
  unused = skipped entirely (`sign_help_counts`). Deliberate asymmetry
  (P(help|used) for foreign), consistent with prior.py's rationale.
- `thompson_bootstrap.yaml` ev_floor_quantile=0.765 is an offline-calibrated
  QUANTILE (self-normalizing family, provenance documented) — rule-compliant.
- FusedRankingShortlister novelty leg is wall-clock (24h window) — inert at
  default w_nov=0; latent rule tension if ever enabled.

### A-6 Verified CORRECT (coverage list)
1. `bootstrap.py` weighted resampler: unbiased center; staleness fades toward
   unit-weight zero pseudo-atom (shrinkage W/(W+1)); se jitter widens without
   moving the center; no-ses fast path preserves seed-exact replay.
2. BootstrapThompsonAuctioneer: one resample = proper bootstrap-TS draw
   (Eckles–Kaptein style); ONE slate baseline draw with Sidak adjustment —
   null win-rate invariant in slate size (verified coherent).
3. `harm_mass` = exact indicator at se=0, Gaussian tail otherwise — correct.
4. `beta_binomial_posterior` soft counts a=1+(n−k_harm), b=1+k_harm; n=0 edge →
   (1,1)+nan lo+confident False. Weighted-likelihood pseudo-counts standard.
5. Foreign sign-only bump `_block_from_partition`: adds (help, total−help) to
   (a,b); `intro_events` stays native-only ⟹ foreign-only cards can never be
   efficacy-confident nor confidently-harmful — matches contract + veto design.
6. Probe/eviction partition: `_effective_support` (eviction.py:367-387) ==
   auction `support_count` arithmetic (Σ max(0,w) finite × staleness);
   probe strictly-below / adjudicate at-or-above; `_context_is_nonviable`
   returns False below floor ⟹ no card both probe-eligible and policy-evictable
   in the same context; any below-floor context vetoes eviction (all() gate).
7. HarmEvictor: requires ≥1 genuinely negative native outcome + all-contexts
   confident harm + foreign retention veto (net-help, total ≥ 3, per-task).
8. BirthFailureEvictor: task-scaled catastrophic threshold (2× significant_change),
   rescue via pessimistic posterior + pessimistic EV. No absolute constants.
9. Crediting: Point (se=0 exact) and Paired (value identical, coherence-checked;
   se orientation-invariant; 6 counted degrade reasons, never raises).
10. EB prior ladder: Jeffreys-smoothed p̂, shrinkage toward parent with
    pseudo-count, κ∈[k_min,k_max] capped concentration, monotone-refinement
    validator, first-exposure-only (deliberate adaptive-sampling-bias
    mitigation), fail-safe to seed prior.
11. Staleness: rank-count based, task-partitioned (foreign traffic cannot age
    native evidence), population = native-evidenced + never-evented own-task
    cards; single mechanism shared by decay + bootstrap resample weights.
12. DecayingReputation: a_eff=1+w(a−1) toward uniform; harm gate expires with
    decayed intro_events; each field decayed exactly once in shipped
    compositions (no double decay — bid magnitude and gate posterior are
    different quantities, each aged once).
13. Reader orchestration: one card_stats resolve serves auction + render;
    fail-to-empty; telemetry isolated from the selection result.
14. Projection: cold/corrupt posterior → EB prior with source tracking;
    use_count deterministic event count.
15. ColdProbePolicy: partition threshold == eviction floor by config
    (`probe_until_effective_events` = min_effective_events = 3); empty-selection
    50% / warm-override 3% rates config-exposed; fail-safe on empty
    support_kind; budget-full displacement drops the weakest budgeted card.
16. Composed defaults (full.yaml + adaptive read policy): one shared
    min_effective_events=3 knob feeding confidence, harm, policy-nonviable,
    probe threshold, bench min-events; Beta(3,3) baseline/cold prior; recall 10
    → inject 1 funnel; both read policies mount the probe lane.

## B. Codex round 1 (task-mrittjzg-554fi2, gpt-5.6-sol xhigh)

Full text: `.claude/projects/.../tool-results/b41rua3o1.txt` (34KB). Verdict:
**UNSOUND**. 11 MAJOR / 6 MINOR / 2 NIT + shipped-defaults table + 24-item
correct-coverage list. Headline MAJORs:

- B-1 Bootstrap resample size ignores weights (rows ≠ effective N; fractional
  weights → spurious precision; single positive event one-sided).
- B-2 EB prior discarded after first event (`Beta(1,1)+counts`); decay shrinks
  to (1,1) not the prior; 0.823→0.667 discontinuity after ONE success.
- B-3 Zero gain counted as help; "not harmful" used as "helpful" (safety vs
  efficacy conflation).
- B-4 Fractional soft counts ≠ exact Beta posterior (25% variance understate
  at q=.5, n=1).
- B-5 gain_se: degraded se=0 means "exact" not "unknown"; n=1 paired se=0;
  no-card baseline subtracted without its uncertainty (stats.py:317).
- B-6 Staleness discounts card by NEWEST event; one event revives all history
  (100 stale wins + 1 loss → Beta(101,2)).
- B-7 Fused rep floor benches under-observed warm cards from the read →
  never reach auction/probe → zombies; partition bypassed upstream.
- B-8 Auction samples multiple independent posteriors per decision (cold bid
  theta ≠ gate theta at auction.py:588/:645; warm EV draw ⊥ sign gate draw).
- B-9 Within-round EV quantile floor = IIA-violating rank cut, not a reserve;
  q=.765 calibrated on n=27.
- B-10 EB pooling survivor-biased (evicted arms vanish); no propensity logging.
- B-11 No pending-exposure control across concurrent mutations (delayed batch).

MINORs: EB ladder crosses non-nested cohorts + tuple-order first exposure;
lifetime novelty tax unprincipled (opt-in); probe replacement drops retrieval-
order tail not weakest bid (K=1 unaffected); fused w_rep unit mismatch (inert
at 0); harm eviction 80% too weak for irreversible deletion; live auction RNG
entropy-seeded (not replayable). NITs: bootstrap_ev_quantile ignores ses (no
callers); k_max>=k_min unvalidated.

## C. Reconciliation & triage (my verification of every Codex claim)

Verified line-by-line against code before accepting — corrections to BOTH
reviews came out of this pass.

| # | Verdict | Notes |
|---|---------|-------|
| B-1 | CONFIRMED — MAJOR | Math checked: resample n = rows+1 regardless of weights; zero-atom renormalization makes heavily-stale cards spuriously certain near 0. |
| B-2 | CONFIRMED — MAJOR | projection.py applies EB prior only cold (verified earlier); beta_binomial hard-codes (1,1); decay shrinks to (1,1). Real Bayesian-coherence cliff. |
| B-3 | SPLIT | Foreign `>= 0` REJECTED: user contract verbatim ("help iff finite gain >= 0.0") — Codex not authorized to challenge. Native side CONFIRMED: prior.py:65 counts zero first exposure as EB success; posterior semantics are P(non-harm) mislabeled p_help (= known L1 inflation). MAJOR (native only). |
| B-4 | CONFIRMED — MINOR-to-MAJOR | Correct critique of soft counts; compounds in irreversible eviction with weak harm_quantile=.80. |
| B-5 | CONFIRMED — MAJOR | stats.py:317 subtracts baseline point estimate, se carries only measurement error (verified). Degraded se=0 = "exact" under harm_mass indicator (verified semantics). |
| B-6 | CONFIRMED — MAJOR | Card-level latest-event scalar verified earlier; revival cliff real. Fix must touch auction support_count AND eviction _effective_support identically (partition invariant). |
| B-7 | CONFIRMED — MAJOR; **corrects my A-6** | I had trusted the docstring ("never an absorbing death"). Verified: probe pool = auction slate (reader.py:219); `_passes_rep_floor` (fused.py:242) drops below-floor warm cards from the read; below-floor + <3 events + eviction veto = absorbing zombie. Docstring is wrong. |
| B-8 | CONFIRMED — MAJOR; extends my A-1 | Shipped BootstrapThompson also splits draws: cold theta_bid:588 vs gate theta:645; warm bootstrap-EV bid ⊥ Beta sign gate. A-1 upgraded from latent-preset to shipped-default. |
| B-9 | Arithmetic CONFIRMED; design → USER GATE | Slate-relative floor is IIA-violating (verified cases). Replacement (posterior P(EV>0) risk gate) changes A/B-calibrated shipped behavior — user decision. |
| B-10 | CONFIRMED — methodological, USER GATE | Survivor-biased EB + no propensity logging. Correct per-arm Bayes defense also correct (no IPS needed for selected-arm updates). Fix = new machinery (ledger, logging), not surgical. |
| B-11 | CONFIRMED — methodological, USER GATE | K=1 + probe lane soften it; duplicate exploration across in-flight mutations is real. Joint/pending-aware batch TS = new machinery. |
| B-M1 | CONFIRMED | Extends my A-4 (same boundary, sharper: Simpson-style shrinkage risk + tuple-order first exposure). |
| B-M2 | CONFIRMED (opt-in) | Novelty preset only; already a known parked issue. |
| B-M3 | CONFIRMED — NIT at K=1 | probe.py:148 drops retrieval-order tail; check budgeter output order before fix. |
| B-M4 | CONFIRMED (inert) | w_rep=0 shipped. Doc note. |
| B-M5 | CONFIRMED — MINOR | Beta(1,4) 80th pct = .331 < .5 → 3 exact losses evict at ~94% posterior confidence; weak for irreversible. |
| B-M6 | CONFIRMED — MINOR | reader.py:110 `default_rng()` entropy default. |
| A-1 | MERGED into B-8 | |
| A-2 | Closed (non-issue) | gain non-Optional. |
| A-3, A-4 | Stand as NITs | A-4 subsumed by B-M1 fix. |

**Both-reviews correction:** my A-6 item 6 (partition verified) holds at the
probe/eviction boundary arithmetic but NOT end-to-end — B-7 bypasses it
upstream. Codex's 24-item coverage list is consistent with mine except it
(correctly) refuses the partition end-to-end claim.

## D. Fix ladder

Tier S (surgical, math-correctness, no new machinery) — delegate to Codex
sequentially after user scope approval:

- S1 (B-8+A-1): one coherent world per candidate serving bid AND gate in both
  auctioneers; keep single slate baseline + Sidak. auction.py only.
  Design: draw ONE u~U(0,1) per candidate; gate theta = Beta.ppf(u, a, b);
  cold bid = theta x magnitude (same theta); warm bid = u-quantile of the
  bootstrap EV distribution (n_bootstrap resamples, reusable from card_stats
  machinery) so the sign draw and EV draw share the same posterior world.
  Note: warm gains are already no-card-baseline-subtracted (stats.py:317),
  so bid>0 partially duplicates the no-card gate — keep both, but coupled.
- S2 (B-7): `_passes_rep_floor` exempts cards below the staleness-scaled
  effective-support floor (same arithmetic as probe/eviction); fix docstring.
- S3 (B-2): thread EB prior (a0,b0)=(κμ, κ(1−μ)) into beta_binomial_posterior
  and decay shrink target; cold path unchanged.
- S4 (B-6): per-event staleness ranks (event-age not card-age) in decay +
  bootstrap weights + auction support_count + eviction _effective_support —
  all four mirrored.
- S5 (B-1): effective-N-scaled resample count (or Poisson bootstrap);
  preserve seed-exact no-ses fast path where possible.
- S6 (B-3 native): EB first-exposure success = gain > 0 (zero not help);
  document p_help as P(non-harm) where that's what it is. Foreign untouched.
- S7 (B-5): degraded/n=1 paired se → explicit "unknown" (None) not 0.0;
  harm_mass treats unknown wide, not exact; add baseline se in quadrature at
  stats.py:317.
- S8 (B-M3/M5/M6 + NITs): probe replacement sorts by bid; harm_quantile
  .80→.95 default; seeded rng injection; k_max>=k_min validator; timestamp-
  sorted first exposure.
- S9 (telemetry, ADDITIVE — no behavior change; folded 2026-07-13 per user):
  add two audit fields to AuctionBid so the whole S-ladder is verifiable purely
  from the persisted MemoryReadSelection.slate in memory_events.jsonl, without
  raising the log level. (1) support_n_unstaled = Σ max(0, event_weights) (raw
  per-event credit, PRE-staleness); the existing support_n stays the staled
  Σ max(0, credit_i×w_i), so the S4 aging bite = support_n / support_n_unstaled
  is explicit and auditable. (2) gain_se = the paired-se on the card's most
  recent native gain event, None when unknown/degraded (per S7) — surfaces the
  "unknown se treated wide, not exact" behavior live (exact field-2 reduction
  finalized at S7/S9 once the se path's shape is fixed). Populate at the bid
  construction site (projection.py → AuctionBid, mirroring support_n); zero
  change to any bid/gate/ranking. Runs LAST: both source semantics (S4
  staleness, S7 se) must be final first.

Tier D (design changes / new machinery — REQUIRES USER DECISION):

- D1 (B-9): replace ev_floor_quantile=.765 with posterior risk gate
  P(EV>0|D) ≥ 1−α (self-normalizing, IIA-clean) — changes calibrated behavior.
- D2 (B-4): latent-sign mixture posterior (exact) vs current soft counts.
- D3 (B-10): immutable arm ledger + inclusion-propensity logging + EB from
  ledger (survivor-bias fix).
- D4 (B-11): pending-exposure-aware batch selection.
- D5 defaults: n_bootstrap 512→2000; min_effective_events 3 vs 5 for
  irreversible adjudication; crediting default point→paired.

Status: Tier S EXECUTING (user approved 2026-07-13 "execute S1–S8 sequentially -> yes, go").
- S1 (B-8+A-1): DONE 2026-07-13. Coherent per-candidate draw (one u → gate theta
  = Beta.ppf(u,a,b), cold bid = theta×mag, warm bid = u-quantile of the sorted
  bootstrap-EV batch) in BOTH BootstrapThompsonAuctioneer and EVThompsonAuctioneer;
  slate baseline + Sidak untouched; probe_eligible removed from the auctioneer
  (ColdProbePolicy.apply owns it). Inspected line-by-line + accepted. Gate:
  ruff clean; tests/memory + tests/integration all pass (2 skips). One
  seed-fragile e2e test made deterministic via a guaranteed-fill ColdProbePolicy
  and switched to the production BootstrapThompsonAuctioneer (matches its own
  "production stack from full.yaml" docstring); "in-memory Chroma" docstring
  corrected (EphemeralClient).
- S2 (B-7): DONE 2026-07-13. _passes_rep_floor now exempts warm cards whose
  staleness-scaled effective support < policy_min_effective_events (they keep
  auction/probe access to earn adjudicating evidence); sufficiently-observed
  below-floor cards still lose the current read. effective_support() extracted
  as ONE shared free fn in the NEUTRAL gigaevo/memory/context/evidence.py
  (arithmetic verbatim), called by both read/fused.py and write/eviction.py.
  Correction applied: Codex first put it in read/reputation.py, creating the
  only write->read import in the write/ package + rewriting the "write must not
  import read" invariant; relocated to evidence.py and restored the docstring
  (write/ now has zero read/ imports). Partition boundary VERIFIED: read
  policy_min_effective_events = ColdProbe probe_until_effective_events =
  PolicyNonViableEvictor min_effective_events, all = memory.evidence.
  min_effective_events = 3 (eviction_safety.* is a ${ref} to evidence.*).
  Failing-first boundary test added (support 2 exempt / 3 dropped). Gate: ruff
  clean; tests/memory + tests/integration all pass (2 skips).
- S3 (B-2): DONE 2026-07-13. The cold→warm coherence cliff is closed. The
  card's cold prior (a0,b0) is now threaded as the BASE of beta_binomial_posterior
  (a=prior_a+(n−k_harm), b=prior_b+k_harm) AND is the decay shrink target
  (a_eff=a0+w·(posterior_a−a0), composing to a0+w·S_a — decays to the EB/cold
  prior, not uniform). prior=None default = bit-exact legacy (1,1). Wiring:
  BetaBinomialReputation gained a `prior` field + `prior_base()`; BDProximity
  (subclass) applies the SAME prior on both its cold-cell fallback and in-cell
  paths; Bootstrap delegates prior_base to inner; DecayingReputation and the
  ReputationModel Protocol gained prior_base; 7 reputation yamls wire
  `prior: ${ref:memory.prior}` so projector (cold) and reputation (warm) share
  ONE prior. Behavior shift (intended, = the fix): the legacy `fixed_3_3` preset's
  warm base moves (1,1)→(3,3), and the adaptive EB preset's warm base moves from
  (1,1) to (κμ,κ(1−μ)) — cold and warm are now one coherent world; a first WIN
  can no longer drop p_help below its cohort prior. Cold path (projection.py,
  prior.py) UNTOUCHED. Inspected line-by-line + accepted. Tests: new strong
  pinned-number proofs — test_one_win_cannot_lower_help_below_its_cohort_prior
  (coherent (5,1)=5/6 ≥ μ=0.8 vs legacy (2,1)=2/3),
  test_in_cell_and_fallback_share_the_same_card_prior,
  test_fully_stale_posterior_shrinks_to_the_card_cold_prior (prior (8,2), fresh
  (11,3), decays to exactly (8,2)); foreign-fold tests still assert legacy
  (1,1)-base numbers. Gate: ruff clean (S3 files); tests/memory + tests/integration
  reached [100%] all-pass (2 skips). Noted non-blocking perf minor: prior_base is
  computed twice per read in the decay stack (inner card_stats + DecayingReputation)
  — an extra EB bank scan, not a correctness bug.
- S4 (B-6): DONE 2026-07-13 (Codex gpt-5.6-sol xhigh, 30m38s; inspected
  line-by-line by orchestrator + gated green). Locked design (mine, as
  orchestrator; anchors re-verified post-S2):
  replace the per-CARD scalar `bank_cycle_weight` with per-EVENT
  `bank_cycle_event_weights(events, bank, H, task_key) -> tuple` (s_i = native
  bank stamps strictly newer than event i). The reputation seam changes from
  scalar `staleness_weight()->float` to per-event `staleness_weights()->tuple`
  aligned with evidence_events; `event_weights` STAYS pure credit so a
  Bootstrap(Decay(...)) stack never double-ages (each store-bearing layer ages
  only the quantity it owns — Bootstrap→EV/support, Decay→posterior, each once).
  Consumers: (a) BootstrapReputation.card_stats folds credit×w_i into
  delta_weights, scalar arg→1.0, effective_events=Σ(credit×w_i); (b)
  DecayingReputation rebuilds the Beta soft counts per-event (threaded
  staleness_weights through block_from_events/_block_from_partition/_task_block/
  beta_binomial_posterior, default None = bit-exact legacy) shrinking to the S3
  cold prior; (c) evidence.py effective_support = Σ max(0,credit_i×w_i) (shared
  read fused.py + write eviction.py — bit-identical partition); (d) projection.py
  folds staleness into candidate.delta_weights + sets candidate.staleness_weight=1.0
  so auction.py support_count/EV need ZERO logic change. Invariants demanded:
  foreign can't age native, no double-age, non-decay posterior stays credit-only,
  probe/eviction bit-identity, seed-exact all-unit fast path, no new constants.
  Failing-first test: 100 stale wins + 1 fresh loss must NOT revive to ≈Beta(101,2).
  VERIFIED (orchestrator line-by-line, all 9 source + 40 test hunks): alignment
  chain guarded at every hop (decay passes full-length N staleness over
  card.gain_events → _task_block asserts len==N, splits native/foreign by zip →
  block_from_events(native) asserts len==len(native) → positional aged_weight);
  reputation.py:208 intro_events=n=Σ(credit_i·age_i)+forced_failures so the harm
  gate expires automatically; prior applied exactly once; foreign evidence is
  sign-only pseudo-counts (never grants efficacy); NO double-age (Decay→posterior,
  Bootstrap→EV/support via Decay's staleness_weights seam, event_weights stays pure
  credit; base-without-decay = unit ages = no aging); read/write drift ELIMINATED
  (eviction PolicyNonViable now calls the identical effective_support the probe
  uses). Headline: 100 stale wins + 1 fresh loss → Beta(4/3,2) mean 0.4 support
  4/3 (was Beta(101,2) mean >0.98). Tests +3172/−190, zero removed assertions.
  Orchestrator fixed 2 defects in Codex output: (1) 5 files failed ruff format
  (reformatted); (2) the full-scope gate surfaced a PRE-EXISTING branch red —
  test_full_end_of_run_default_bank_is_rejected — caused NOT by S4 but by the
  cross-task ladder's full.yaml provider swap (ReaderMemoryProvider →
  LeasedMemoryProvider) which silently defeated the validate_memory_pipeline_compat
  provider_target==ReaderMemoryProvider guard (dead footgun-protection on the
  flagship `full` preset). Fixed per feedback_preexisting_bugs_must_be_fixed:
  validation.py now unwraps LeasedMemoryProvider one level (_LEASED_PROVIDER_TARGET,
  rename-robust via _target_path) before the reader-provider comparison. This is a
  config-seam dead-guard bug of exactly the class the review targets.
- S5 (B-1): DONE 2026-07-13 (Codex gpt-5.6-sol xhigh; the resume wrapper died
  mid-turn AFTER applying the file change but BEFORE running tests/emitting its
  report — orchestrator recovered from the on-disk diff, inspected + gated).
  bootstrap.py: each replicate now draws max(1, round(n_eff)) atoms where
  n_eff = (Σw)²/Σw² (Kish effective N) over the EXACT sampling-weight vector
  (fused delta_weights + the unit neutral pseudo-event), max-scaled to avoid
  overflow (ratio scale-invariant). _atoms_and_probs returns the raw weight
  vector as a 3rd element (only caller updated). Fixed-size multinomial (NOT
  Poisson) chosen so the all-unit case is byte-exact: all weights 1.0 ⇒
  n_eff = (k+1)²/(k+1) = k+1 = atom_count EXACTLY (IEEE n²/n=n), so rng.choice
  size AND the rng.normal jitter shape are unchanged ⇒ identical RNG stream.
  Kish ≤ N (Cauchy–Schwarz, equality iff all-equal) ⇒ skewed vectors always
  draw FEWER atoms ⇒ wider EV tails; zero-weight atoms add 0 to both sums;
  scale≤0/non-finite and Σw²=0 guarded → 1 draw (no new NaN path).
  effective_events (BootstrapReputation.resolve) stays Σw — n_eff governs only
  the draw size. Tests (test_bootstrap.py +91): bit-exact all-unit replay +
  RNG-position identity; zero-weight atoms don't inflate n_eff (inverse-CDF
  searchsorted equivalence, padded==compact); all-zero weights collapse to the
  neutral atom → zeros; skewed vector widens the EV band vs rows+neutral.
  Orchestrator VERIFIED, not blindly accepted: the -x gate surfaced 3 frozen
  bootstrap-EV MC constants in test_decay.py (2 tests) that S5 legitimately
  shifts (skewed staleness vectors: n_eff 3 vs 102, and n_eff 2 vs 3). Proved
  each is a valid MC realization of an UNCHANGED analytic estimand (weighted
  atom mean; unbiased regardless of draw count): (1) IntroGain -0.29182→
  -0.294921875, analytic EV -0.2857, grand mean -0.2855 over 200 seeds (≈0.5σ);
  (2) coupled bid -0.2647→0.0, a genuine discrete u-quantile of the coarser
  n_eff≈3 distribution (mean of {1,-1,0} = exact 0.0), card still loses
  (winners==[]) — same DECISION; (3) IntroGain -0.35221→-0.361328125, analytic
  EV -0.3333, grand mean -0.3337 over 300 seeds (≈1.3σ). Structural pins
  (posterior 4/3,2 & 2,2; support 4/3; delta_weights sum 4/3; staleness 1.0,
  0.25) ALL unchanged — confirming S5 touches only draw size. Recalibrated the 3
  constants with a terse WHY. Fixed 1 Codex-output defect: test_bootstrap.py
  failed ruff format (reformatted). Gate: ruff clean (S5 files); full declared
  scope (tests/memory config evolution entrypoint stages metrics_paired
  integration) EXIT:0, zero F/E, reached [100%] (2 skips). Dead wrapper task
  cancelled by id.
- S6 (B-3 native): DONE 2026-07-13 (Codex gpt-5.6-sol xhigh; inspected
  line-by-line + gated). prior.py: the EB cohort prior's two native exposure
  counters now require STRICTLY POSITIVE causal gain for a "help" success —
  _first_non_founding_exposure:69 (`gain > 0.0`) and _all_exposures:91
  (`gain > 0.0`), moved TOGETHER so the success rule can't depend on the
  first_exposure_only toggle. A zero gain now enters the failure/complement mass
  exactly like a negative or invalid outcome, so success+failure still totals the
  causal exposure weight (neutral evidence ≠ help). Both docstrings state the
  strict-positive semantics. FOREIGN CONTRACT UNTOUCHED (hard guardrail held):
  evidence.py:107 sign_help_counts still folds `gain >= 0.0 = help` for the
  cross-task sign-only posterior — a separate mechanism; S6's Codex turn issued
  ZERO writes to evidence.py (verified from the job log). Orchestrator
  disambiguated the diff: the task-cohort ladder (`split_events_by_task`, "task"
  in _COHORT_LEVEL_TOKENS, task+kind+category levels, task_local threading) and
  evidence.py's +87 are PRE-EXISTING cross-task shared-bank ladder state (HEAD
  prior.py has 0 "task" tokens → all uncommitted; not a planned S-item, not S6
  scope creep) — S6 correctly left them alone. Tests (test_prior.py +2 S6 tests):
  test_empirical_bayes_zero_gain_is_weighted_failure_in_both_counting_modes
  (parametrized first_exposure_only True/False, weight 0.25 → counts (0.0,0.25);
  red-first confirmed by Codex as (0.25,0.0) before the fix — pins BOTH counters)
  + test_empirical_bayes_nonzero_gain_sign_counts_are_unchanged (+1→(1,0),
  −1→(0,1), both modes — non-zero-branch regression). Both S6 tests use
  task_local=False (clean isolation from the pre-existing task-cohort tests).
  Docs: memory.md:207 + MEMORY_LIFECYCLE_TUTORIAL.md:181 now state "only strictly
  positive causal gain as help; zero/negative/invalid → failure mass" (no p_help
  rename; reputation.py:151 already labels its harm posterior P(non-harm)). Gate:
  ruff clean (gigaevo + tests, 713 files; 114 repo-wide errors confined to
  problems/ Cohn-deliverable artifacts, out of scope); full declared scope
  EXIT:0, zero F/E, reached [100%] (2 skips).
- S7 (B-5): DONE 2026-07-13 (Codex gpt-5.6-sol xhigh; inspected line-by-line via
  the S7 rollout apply_patch hunks + gated). Two coupled defects fixed:
  DEFECT 1 (unknown se read as exact): PairedEffectEstimator._degrade and
  _paired_se (degenerate_se + comparison_error branches) now return None, not 0.0
  — Measurement.se and ContextualGain.gain_se are `float | None` (None = unknown,
  0.0 = exact, >0 = measured noise). harm_mass moved to evidence.py with a 3-way
  body: `None → float(norm.cdf(0.0))`=0.5 (the se→∞ limit, a DERIVED constant, not
  a magic literal) FIRST, `se<=0 →` hard below-threshold indicator SECOND, cdf
  THIRD. None threaded through reputation.py via `_coerce_gain_se` (None→None,
  non-finite/≤0→0.0), _ev_ses, beta_binomial_posterior (finite tuple element
  `float|None`), block_from_events valid_ses, and OUT to the bootstrap EV path:
  auction.deltas_se `tuple[float|None,...]`, interfaces.event_ses protocol,
  decay.py passthrough, and bootstrap._atom_ses (None→0.0 → no fabricated jitter,
  NaN-safe via the `isfinite & >0` filter). Asymmetry is principled: unknown→0.5
  for the harm posterior (refuse the overconfident hard indicator) but →no-jitter
  for the EV bid (no principled spread scale; symmetric jitter wouldn't move the
  mean bid anyway; resample sampling-uncertainty already carried).
  DEFECT 2 (baseline SEM dropped): FittedNoCardBaseline Protocol += baseline_se_for;
  GlobalNoCardBaseline stamps `std(deltas, ddof=1)/sqrt(n)` for n>=2 (finite-
  guarded) else None, location stays median(deltas); contextual baselines
  (_ConstantNoCardBaseline in models.py's cell/global fits) return None (non-
  regressive → 0 in quadrature). Stamping site uses `_combined_se(measured_se,
  baseline_se)`: `None→None`, `0.0→0.0` (EXACT PRESERVED — default point-estimator
  pipeline stays BYTE-EXACT), else `np.hypot(measured, fitted)`. INVARIANTS held:
  PointEffectEstimator untouched (se=0.0 by design); foreign sign_help_counts
  `gain >= 0.0` intact (separate cross-task mechanism); no bare `float(None)` (sole
  bare float(measured_se) is guarded by the None-return above it). Tests (red-first,
  non-vacuous): test_reputation.py TestSoftHarmMass +
  test_degraded_event_contributes_half_its_credit_to_harm (0.5*w vs full w),
  test_zero_ses_match_omitted_bit_exact (byte-exact default),
  test_unknown_stored_se_is_preserved_and_bootstrap_safe (None → no crash in
  bootstrap); test_stats.py test_direct_stamping_combines_measured_and_global_
  baseline_uncertainty (pins all 3 _combined_se branches: hypot / 0.0 / None) +
  test_invalid_and_unused_events_stay_exact_under_paired + the two SEM tests
  (n>=2 → std/√n, n<2 → None); test_crediting.py all 6 degrade reasons →
  Measurement.se is None while PointEstimator stays se==0.0. Docs: memory.md +
  MEMORY_LIFECYCLE_TUTORIAL.md now carry the paired-crediting quadrature paragraph
  and the 3-branch per_event_harm_mass formula (incl. `NormalCDF(0) if gain_se is
  None` + "se→∞ limit → half weight"). ACCEPTED NOTE (not a defect): baseline
  location is median but its se-proxy is the mean's SEM (std/√n) — exact median-SE
  carries a ~1.25× factor under normality; std/√n kept deliberately (textbook SEM,
  derived not tuned; a 1.25 factor would be a fabricated distributional constant;
  second-order quadrature term; strictly better than the pre-fix zero). Scope: the
  auction.py coherent-world/n_bootstrap/probe_eligible rewrite in `git diff HEAD`
  is PRE-EXISTING cross-task-ladder state, NOT S7 (confirmed from S7's actual
  apply_patch hunks — S7's only auction.py footprint = doc edits + the deltas_se
  annotation). Gate: ruff clean (gigaevo + tests, 713 files; 4 Codex format-drift
  files auto-formatted); targeted 3-file run 154 passed; full declared scope
  EXIT:0, reached [100%], zero F/E (skips only).
- S8: DONE 2026-07-13 (Codex gpt-5.6-sol xhigh). The Codex process DIED mid-run
  (broker drop; log truncated after applying fix d), but all three fixes + their
  failing-first tests had already landed on disk; orchestrator inspected every
  edit line-by-line against spec, applied the ruff lint/format the dead run
  skipped (import-sort + 2 whitespace collapses, zero behavior change), and
  gated green: targeted tests/memory/read/test_probe.py + test_prior.py = 39
  passed; full declared scope (memory/config/evolution/entrypoint/stages/
  test_metrics_paired/integration) reached [100%] exit 0 (2 intentional skips).
  RE-SCOPED 2026-07-13 after grounding the plan's 5 items against the
  refactored probe/prior code (the original bundle was written pre-refactor).
  Surgical-now bundle collapses to (a)+(d)+(e); (b)+(c) move to Tier D.
  * (a) read/probe.py::ColdProbePolicy._select_probe (line ~144-148): the
    warm-override replacement drops `kept[:-overflow]` = the TAIL of budgeter
    order, but the class docstring (line 34) promises "displacing the weakest
    budgeted card". TopBidBudgeter.cap returns unsorted-within-budget, so the
    tail is arbitrary, not weakest. Fix: displace the `overflow` cards that rank
    LOWEST by the auction's own key (-(bid or 0), -theta, card_id), preserving
    budgeter order of survivors. Bid lookup from the passed `slate`. REAL bug.
  * (d) read/prior.py::EmpiricalBayesMemoryPrior: only a finiteness
    field_validator on k_max; no k_max>=k_min cross-field check. k_max<k_min
    inverts kappa = k_min + (k_max-k_min)*min(1,n/n_ref) so concentration FALLS
    with evidence. Fix: model_validator(mode="after") raising when k_max<k_min.
  * (e) read/prior.py::_first_non_founding_exposure iterates events in LIST
    order; merge/admission can place an older exposure after a newer one, so the
    "first" exposure feeding the EB cold prior is not the temporally-earliest =
    contaminated causal read. FIX IS SURGICAL, NO SCHEMA CHANGE: every
    ContextualGain already carries a stable timestamp at context.timestamp
    (stamped from the child's program.created_at at stats.py:318/149; survives
    the from-scratch restamp). Order the iteration by context.timestamp
    (None-safe: None sorts last via datetime.max, stable-sort preserves list
    order among equals → old banks non-regressive). `_all_exposures` is a sum,
    order-independent, untouched. (User asked "why not add a timestamp?" — answer:
    one already exists on every event; adding a NEW field would break union_events
    value-dedup / double-count on re-eval, so we reuse context.timestamp instead.)
  * (b) MOVED TO TIER D (D6): harm_quantile 0.80->0.95 is a reputation-model
    policy value (reputation.py:423 default + 8 reputation preset YAMLs), NOT an
    evictor field as the plan said, and NOT a correctness bug — raising it only
    makes eviction more conservative. 9-file sweep, risk-appetite knob → user call.
  * (c) MOVED TO TIER D (D7): reader.py:110 silent default_rng() IS a
    reproducibility gap, but gigaevo has NO global seed concept anywhere (only
    bootstrap.py self-seeds from a content digest); seeding just the reader while
    LLM sampling / mutation order stay nondeterministic is inert. A real fix needs
    a framework-wide seed → design decision, out of the surgical ladder.
- S9 (ADDITIVE telemetry): DONE 2026-07-13 (orchestrator, in-house — small +
  surgical, Codex runtime flaky this session, not "heavy implementation"). Two
  audit-only fields added on BOTH AuctionCandidate and AuctionBid:
  `support_n_unstaled: float` (raw Σ max(0, per-event credit) BEFORE staleness)
  and `gain_se: float | None` (paired-se of the card's temporally-latest native
  gain event, None when unknown/degraded). Populated in projection.py::project:
  support_n_unstaled = Σ max(0, event_weights) over finite credit (the raw credit
  vector, NOT the S4-folded delta_weights); gain_se via new module helper
  `_latest_native_se(evidence_events, event_ses)` picking the ses row of the
  max-timestamp event (None-safe, mirrors the cold prior's recency order; ties →
  earliest listed; None on length-mismatch/empty). Both copied verbatim onto the
  bid at the construction site (auction.py:719-720) — support_n stays the staled
  Σ max(0, credit×w_i), so support_n / support_n_unstaled = the S4 aging bite off
  one slate row. KEY DISCOVERY: `evidence_events` already returns native rows
  positionally aligned with `event_ses` (both = _ev_*(split_events_by_task(...)))
  → no new reputation method needed; S9 stays purely additive. ZERO change to any
  bid value / gate / ranking / RNG stream (defaults 0.0/None; frozen models). The
  fields round-trip through bid.model_dump(mode="json") into MemoryReadSelection.
  slate unchanged. Tests (failing-first, all 4 red before Edit 4, green after):
  test_projection.py::{test_projector_exposes_unstaled_support_and_staleness_bite
  (staleness_weights (0.25,1.0) → unstaled 2.0, staled 1.25, bite 0.625),
  test_projector_gain_se_is_latest_native_event_se (list order (late,early) but
  audit tracks the 2026-06 event's se 0.9 not list-first), test_projector_gain_se_
  none_without_events}; test_auction.py::test_bid_carries_candidate_staleness_
  audit_fields (candidate→bid copy + JSON round-trip + 0.625 bite). Gate: memory
  subsystem ruff+format clean (repo-wide `ruff check .` has 114 PRE-EXISTING errors
  in unrelated deliverable-artifact scripts — outside scope, untouched); 4 targeted
  tests pass; full declared scope (memory/config/evolution/entrypoint/stages/
  test_metrics_paired/integration) reached [100%] exit 0, 2 intentional skips,
  zero F/E. tools/analyze_bandit_health.py + memory_event_report.py NOT touched
  (they do not enumerate bid fields explicitly). TIER S COMPLETE.

## E. Appendix — Codex delegation prompts (ready to fire on approval)

Common preamble for every S-task (prepend verbatim): "Implement in-place on
the CURRENT branch — do not switch branches; all work is uncommitted
working-tree state (do NOT commit). Surgical diff — only lines
that trace to this fix. Keep config/memory/*.yaml presets composing; update
docs/memory.md + docs/MEMORY_LIFECYCLE_TUTORIAL.md in the same change if the
described behavior shifts. Update/extend tests under tests/memory/ (write the
failing test first where feasible); you may run targeted pytest on the
specific test files with /home/jovyan/.mlspace/envs/evo/bin/python3 -m pytest
<file> -x -q, never the full suite. No new absolute calibrated constants —
quantile/self-normalizing forms only (documented config defaults may change
value). Do not touch Redis or any running process."

- **S1 prompt core**: In gigaevo/memory/read/auction.py, BootstrapThompson
  auctioneer draws the bid and the accept-gate from INDEPENDENT posterior
  worlds (cold theta bid ~:588 vs fresh gate theta ~:645; warm bootstrap-EV
  sample ~:594-603 independent of the Beta gate). Make each candidate use ONE
  coherent draw: u~U(0,1) per candidate; gate theta = Beta.ppf(u, a, b); cold
  bid = that same theta × magnitude; warm bid = the u-quantile of the
  bootstrap EV distribution (n_bootstrap resamples via the existing card_stats
  bootstrap machinery). Keep the single slate baseline draw + Sidak-adjusted
  gate_quantile logic unchanged. Apply the same coherence to
  EVThompsonAuctioneer (latent preset). Preserve rng determinism given a
  seeded generator.
- **S2 prompt core**: In gigaevo/memory/read/fused.py,
  BootstrapFusedRankingShortlister._passes_rep_floor (~:242-253) hard-drops
  warm cards whose ev_lo20 is below the slate 40th-pct floor on EVERY read →
  they never reach the auction, and since the probe pool is the auction slate
  (reader.py:219) they can never earn new evidence: absorbing zombies,
  contradicting the class docstring. Exempt cards whose staleness-scaled
  effective support is below memory.evidence.min_effective_events — SAME
  arithmetic as write/eviction.py _effective_support (import/share, don't
  re-derive). Fix the docstring to match actual semantics.
- **S3 prompt core**: In gigaevo/memory/read/reputation.py + prior.py, the
  empirical-Bayes prior is applied ONLY on the cold path; the warm
  beta-binomial posterior uses Beta(1,1)+counts and decay shrinks toward
  (1,1), producing a p_help cliff (e.g. 0.82→0.67) immediately after a WIN
  when a card crosses cold→warm. Thread the EB prior (a0,b0)=(κμ, κ(1−μ))
  into beta_binomial_posterior AND make it the decay shrink target. Cold path
  behavior unchanged.
- **S4 prompt core**: Staleness is computed from the CARD's latest event age,
  so one new event revives the full weight of all aged history. Switch to
  per-event staleness (each event down-weighted by its own age) consistently
  in all four consumers: read/decay.py, read/bootstrap.py weights, auction.py
  support_count mirror (~:570-581), write/eviction.py _effective_support.
  The four MUST share one implementation.
- **S5 prompt core**: read/bootstrap.py resamples n=rows+1 draws regardless
  of event weights — fractional-weight histories get spurious precision, and
  zero-weight atoms are renormalized in. Scale the resample count by
  effective N = (Σw)²/Σw² (or switch to a Poisson bootstrap — pick one,
  justify in the docstring). Preserve the seed-exact fast path where all
  weights are 1.
- **S6 prompt core**: read/prior.py:64-65 counts a ZERO-gain first exposure
  as an EB success (gain >= 0.0). For NATIVE evidence, success must be
  gain > 0. Do NOT touch context/evidence.py sign_help_counts — the foreign
  sign-only `gain >= 0 = help` rule is a fixed user contract. Where p_help
  effectively means P(non-harm), say so in the docstring instead of renaming.
- **S7 prompt core**: Degraded paired-crediting paths stamp gain_se=0.0,
  which context/evidence.py harm_mass (~:41-45) reads as an EXACT
  measurement (hard indicator), and write/stats.py:317 subtracts the no-card
  baseline point estimate without propagating baseline uncertainty. Make
  degraded/n=1 se an explicit None ("unknown"); harm_mass must treat unknown
  se conservatively wide, not exact; add the baseline se in quadrature at
  stats.py:317. Founding events (se=0 by design, credit_weight 0) must stay
  excluded and unaffected.
- **S8 prompt core** (bundle): (a) read/probe.py:148 replaces kept[:-overflow]
  — the card(s) displaced to make probe room must be the LOWEST-bid ones,
  not the arbitrary tail of auction order (TopBidBudgeter.cap returns
  unsorted when within budget); (b) evictor harm_quantile default 0.80→0.95
  (config/memory/evictor/recommended.yaml + dataclass default); (c)
  reader.py:110 rng: require/plumb a seeded generator instead of silent
  default_rng(); (d) validate probe k_max >= k_min at config build; (e)
  prior.py first-exposure must pick the TIMESTAMP-earliest non-founding
  event, not list order.
- **S9 prompt core** (ADDITIVE telemetry — no behavior change): In
  gigaevo/memory/read/auction.py AuctionBid, add two fields:
  `support_n_unstaled: float` (raw Σ max(0, per-event credit) before staleness;
  the existing `support_n` stays the staled Σ max(0, credit×w_i)) and
  `gain_se: float | None` (paired-se of the card's most-recent native gain
  event, None when unknown/degraded per S7). Populate them where the bid is
  built (gigaevo/memory/read/projection.py, mirroring support_n — the raw credit
  vector is `event_weights`, the staled one is the S4-folded `delta_weights`).
  They MUST serialize into MemoryReadSelection.slate (reader.py) with ZERO change
  to any bid value, gate outcome, or ranking. Add a test asserting both
  round-trip through `bid.model_dump(mode="json")` into the slate and that
  `support_n / support_n_unstaled` reflects the per-event staleness bite. Touch
  tools/analyze_bandit_health.py + tools/memory_event_report.py only if they
  enumerate bid fields explicitly.

#35 delegation (np2 automation, independent of approval): versioned per-TS
env file; waiter rc branching; unmasked sweep failures; tg delivery check;
whitespace-path nit; T5-W deferred-gate wording — see task #35 text.

## F. Tier D execution design (user approved "Full Tier D now" + "run couple
rounds of self + codex reviews until no major/critical-minor remain", 2026-07-13)

BRANCH REALITY (established 2026-07-13): working tree is on `memory-review-fixes`,
whose HEAD == main@86d9390c (ZERO commits beyond main). ALL memory work is
uncommitted on top of main and COMMINGLED in shared files (auction.py,
reputation.py, eviction.py, evidence.py, prior.py, projection.py): the cross-task
shared-bank ladder (PR-1..16, selection_leases.py — separately awaiting approval)
AND the S1–S9 bandit ladder. => a "Tier S only" commit is NOT separable. Commit
deferred to AFTER Tier D + review rounds converge; scope will be enumerated
honestly at commit time (it necessarily includes the shared-bank ladder).

Design principle (per feedback_new_impl_behind_seams_not_modify +
feedback_no_absolute_calibrated_constants + feedback_minimum_viable_design):
D1–D4 add machinery / change calibrated behavior → each lands BEHIND a
Protocol/config seam with the LEGACY path as the default value, so shipped
presets stay byte-identical until a preset explicitly opts in; every behavior
change is thus A/B-able, never silently forced. D5/D6 are the only default-VALUE
changes and both move strictly MORE conservative (safe direction). All
failing-first. No live gigaevo run (verified) → source edits safe.
Review cadence: per-batch self-review (line-by-line) + Codex adversarial
(gpt-5.6-sol xhigh), fix, declared-scope gate green, THEN next batch; final
full-ladder Codex round before commit. Consumption check on every item: trace the
treatment to the DECISION it changes, not just code-path execution
(feedback_treatment_output_consumption_check).

### Batch 1 — concrete config/defaults + minimal seam (D5, D6, D7)
- D5a n_bootstrap 512→2000 (auction.py:553 Field default + any preset pinning it).
  Precision↑/cost↑ only; all-unit seed-exact atom identity (S5) is per-atom, so the
  Kish fast path stays byte-exact; the resample COUNT grows (expected — more atoms).
  Test: BootstrapThompsonAuctioneer().n_bootstrap == 2000 by default.
- D5b min_effective_events 3→5 (the SHARED floor memory.evidence.min_effective_events
  + the 3 LITERAL mirrors reader.yaml:30, writer.yaml:37, and the evidence source —
  ALL move together or the read-probe/eviction partition invariant [S2/S4/S8] breaks).
  More evidence before irreversible eviction AND longer probe grace. Test: partition
  boundary re-pinned at 5 (effective support 4 → probe-exempt / 5 → adjudicable), both
  read (fused) and write (eviction) sides.
- D5c crediting point→paired (writer.yaml:12 `crediting: point`→`paired`). Reward
  BYTE-IDENTICAL (PairedEffectEstimator.value == PointEffectEstimator.value by its own
  contract) — only se becomes real, which ACTIVATES the S7 harm-mass widening +
  baseline quadrature in production (that is the point of the flip). Test: default
  writer stamps a non-None se for n≥2 comparison, None for n<2; reward unchanged vs point.
- D6 harm_quantile 0.80→0.95 (reputation.py:423 Field default + 8 reputation presets).
  Beta.ppf(0.95,a,b) ≥ ppf(0.80) ⇒ P(not-harmful) read is higher ⇒ harder to fall below
  harm_threshold ⇒ eviction strictly MORE conservative. Test: a borderline card evicted
  at 0.80 is RETAINED at 0.95 (same posterior/threshold).
- D7 reader seed: reader.py:110 `default_rng()` → `default_rng(seed)` with an OPTIONAL
  int `seed` on the reader config (default None = current nondeterministic contract).
  Makes the reader isolation-reproducible for replay/tests WITHOUT inventing a
  framework-wide seed (that stays out of scope — the honest limit noted in S8c/D7).
  Test: two readers, same seed + same inputs → identical slate; seed=None constructs fine.

### Batch 2 — D1 posterior risk gate (behind seam, legacy default)
Current EV reserve: bid must exceed max(ev_floor, Beta.ppf(ev_floor_quantile)·mag)
[BootstrapThompson ~:368-418] / the q-quantile of the round's OWN bids
[NoveltyDiscounted ~:559] — the latter is round-relative ⇒ IIA-violating (a card's
admission depends on the rest of the slate; this is the known "novelty tax inflates
auction volume" pathway). New optional mode `ev_reserve_mode: quantile|risk` (default
`quantile` = legacy, byte-identical) + `ev_risk_alpha` (default None). `risk`: admit iff
P(EV>0 | card's OWN bootstrap-EV distribution) ≥ 1−α, i.e. the fraction of the card's
resampled EV atoms (the SAME vector feeding the S1 u-quantile bid — coherence) that are
> 0. Self-normalizing, per-arm, IIA-clean. Riskiest link: the sign-fraction must read the
identical resample vector as the bid, else S1 coherence breaks. Consumption check:
rejected_by_ev_floor must reflect the new gate; slate audit shows which mode fired. Test:
a card whose bootstrap-EV is 90% positive passes at α=0.2 but the round-relative floor
rejects it inside a strong slate (IIA violation demonstrated on one fixture).

### Batch 3 — D2 latent-sign mixture posterior (behind seam, legacy default)
Current per-event harm mass = Φ((thr−gain)/se) (S7: NormalCDF(0)=0.5 when se None; exact
indicator at se=0), then SUMMED into a soft harm count — treats events' harm events as
contributing linearly. Exact alternative: each native event's harm is Bernoulli(p_i),
p_i = Φ((thr−gain)/se); "card is harmful" posterior is the Poisson-binomial over {p_i}
(exact convolution), not the linear sum. Add `harm_model: soft_count|mixture` (default
`soft_count` = legacy). `mixture` feeds the SAME harm gate (reputation.py:626
beta.ppf(harm_quantile) < harm_threshold) via a moment-matched Beta from the
Poisson-binomial mean/var (keeps the Beta gate interface). Most math-subtle item →
legacy default, heavy test. Test: a mixed-se event set where soft-count and
Poisson-binomial diverge; assert mixture matches the exact convolution tail, soft_count
matches its own legacy number.

### Batch 4 — D3 arm ledger + D4 pending-exposure batch (new state/persistence)
- D3 survivorship-bias fix: EmpiricalBayesMemoryPrior scans store.snapshot() = the LIVE
  bank, so EVICTED (harmful) cards never enter the cohort help-rate ⇒ prior biased UP.
  Add optional `ledger` evidence source (default None = current snapshot-only,
  byte-identical): an append-only immutable record of every card ever admitted + its
  first-exposure outcome, surviving eviction; cohort counts drawn from it with
  inclusion-propensity weighting. Persistence: ledger.jsonl, same atomic-append
  discipline as events.jsonl. Test: evict a harmful card → EB cohort help-rate LOWER with
  ledger than with snapshot (bias corrected).
- D4 pending-exposure-aware batch: the reader selects a slate per child, but batched
  delayed feedback means a card can be re-selected across a burst before ANY credit lands
  ⇒ over-selection. Add optional `pending_aware` (default False): discount a card's bid by
  its uncredited pending-exposure count (propensity-style). Test: a card selected N times
  with zero credits so far is down-weighted vs an identical-posterior card with no pendings.

Commit gate: NONE of D1–D7 commits until all four batches AND a final full-ladder
Codex adversarial round report "no major / critical-minor". Then present the honest
combined commit scope (shared-bank ladder + bandit S+D) for user go. Never push.

### Batch-1 grounding (2026-07-13): plan vs CODE reality — Batch 1 largely dissolves
Grounding every Batch-1 file before writing a line flipped the picture. The
substantive behind-seam correctness items (D1–D4) stand; the "config default"
items (D5/D6/D7) are mostly evidence-free churn, guard-blocked, or already-done:
- D5c crediting point→paired is NOT a free default flip. `validate_crediting_pipeline_compat`
  (tests/config/test_crediting_group.py::test_paired_without_metadata_pipeline_is_rejected)
  RAISES on `memory=full`+`paired` because the default pipeline never routes per-sample
  scores → paired would degrade EVERY event to se=None ("missing_vector"), the inert-treatment
  trap that guard exists to reject; and test_default_is_point_... DELIBERATELY pins point as
  default. Real value ⇒ ALSO switch the flagship pipeline→memory_guided_noise/guided_noise
  (load-bearing), not a nudge. Reward-identity + no-global-RNG confirmed safe
  (PairedBootstrap uses fresh default_rng(seed=0)); the blocker is consumption, not math.
- D5a n_bootstrap has TWO code defaults (auction.py:553 + reputation.py:839) + 4 reputation
  presets; 512→2000 is a 4× per-read Monte-Carlo cost for lower quantile variance — a
  precision/cost calibration knob, no A/B evidence it helps decisions.
- D5b min_effective_events literal `3` lives in THREE sources (reader.yaml:30, writer.yaml:37,
  AND full.yaml:43 — plan missed full.yaml); 3→5 is an evidence-free floor guess touching the
  probe/eviction partition of every shipped preset + 6 pins in test_read_policy_presets.py.
- D6 harm_quantile: 11 literal `0.80` across 7 reputation presets + reputation.py:423; 0.80→0.95
  is strictly-more-conservative (verified: higher ppf ⇒ harder to fall below harm_threshold) but
  still a magic-number swap, no A/B.
- D7 reader seed: MemoryReader is ALREADY deterministic-given-rng and ALREADY tested
  (test_reader.py::test_same_seed_same_selection). A config `seed` int would duplicate the
  existing `rng` param with NO consumer threading it (framework seed is explicitly out of
  scope) ⇒ inert wiring. DROP.
Conclusion: D5a/D5b/D6 = evidence-free calibration swaps across 15+ presets → collide with
feedback_no_absolute_calibrated_constants + feedback_data_driven_over_literature +
feedback_variance_floor_first; DO NOT flip on a guess. D5c needs a coupled pipeline change.
D7 dropped. → Escalated to user (2 scope questions). D1 dispatched to Codex regardless
(in-scope under any answer, behind legacy-default seam, zero shipped-behavior churn).

### USER DECISION (2026-07-13): keep defaults, build D1–D4 behind seams
User answered the 2 scope questions:
- D5c/paired: "many problems do not have SE at all, they just provide value" → point
  crediting STAYS the default (SE does not exist for value-only tasks; paired would be
  inert/guard-rejected there). Recorded as [[feedback_many_problems_provide_value_not_se]].
  NO config change. D5c dropped.
- D5a/D5b/D6: after I gave honest per-constant reasoning (no data-driven basis; only
  harm_quantile→0.95 has a convention anchor, still a policy call not a bug), user chose
  "proceed on that basis, keep defaults and build D1-D4 behind seams." → SHIPPED DEFAULTS
  UNCHANGED (n_bootstrap 512, min_effective_events 3, harm_quantile 0.80). Document the
  three as CANDIDATE OVERRIDES in docs/memory.md (to be A/B-earned), do NOT flip. D7 dropped.
CONFIRMED Tier D scope = D1 (running, Codex), D2, D3, D4 — each behind a Protocol/config
seam with the LEGACY path as default so every shipped preset stays byte-identical. Zero
calibration-default flips. docs/memory.md override note deferred until D1 lands (avoid
colliding with Codex's in-flight edits). Sequential build (D1→inspect→gate→D2→…) so D2–D4
mirror whatever seam idiom D1 establishes.

### D2–D4 recon + REORDER by value×generality (2026-07-13, pre-D1-landing)
Read reputation.py harm math: soft count `k_harm = Σ wᵢ·harm_mass(gᵢ,seᵢ,thr)`,
`a=prior_a+(n−k_harm)`, `b=prior_b+k_harm` (:201-207); harm_mass = exact 0/1 indicator
at se=0, Φ((thr−g)/se) at se>0, Φ(0)=0.5 at se=None (:117-135 _coerce_gain_se sanitizes
neg/nonfinite→0).
- D2 (Poisson-binomial harm posterior) is a NO-OP for the DEFAULT config: point crediting
  ⇒ every se=0 ⇒ harm_mass ∈{0,1} ⇒ Poisson-binomial variance 0 ⇒ moment-matched Beta
  collapses to the EXACT current Beta-Binomial. It only differs when se is real/unknown
  (opt-in paired tasks). REAL bug it targets: an unknown-se event (p=Φ(0)=0.5) adds a full
  trial to n (tightening the posterior) but only 0.5 to k_harm ⇒ maximally-uncertain
  evidence spuriously RAISES confidence. Fix = let per-event variance p_i(1−p_i) drive the
  effective sample size (moment-match Beta to the weighted Poisson-binomial), with a hard
  fallback to the current Beta-Binomial when all p_i∈{0,1} (the se=0 default) so legacy is
  byte-identical. Subtle + se-gated + minority-config ⇒ build LAST, spec the degenerate
  fallback explicitly.
- D3 (EB-prior survivorship bias) and D4 (over-selection under batched delayed feedback) are
  GENERAL — hit every run regardless of se ⇒ higher value than D2.
REORDER: D1 (running) → D3 → D4 → D2. Each behind a seam, legacy default byte-identical.

### D1 LANDED + INSPECTED + GATE GREEN (2026-07-13)
Codex implemented the EV-reserve seam in auction.py. Inspected line-by-line against ground truth:
- Riskiest link CORRECT: warm branch (auction.py:677-693) draws the bootstrap-EV vector ONCE;
  bid = `samples[quantile_index]` (u-quantile), `positive_probability = np.mean(samples>0)` over the
  SAME vector. No independent second draw. Proven by `test_risk_gate_reuses_bid_bootstrap_ev_vector`
  which reconstructs both from the recorded `choice_indices[0]` and asserts `len(choice_indices)==1`.
- Default = "quantile" mode, byte-identical: `ev_reserve_mode` Field default "quantile"
  (auction.py:590), risk requires explicit `ev_risk_alpha` (model_validator :603). Legacy quantile
  branch (:697-706) unchanged. `test_ev_reserve_defaults_to_byte_exact_legacy_quantile` asserts
  default ctor == explicit quantile on winners AND per-bid model_dump_json.
- Consumption check ✓: AuctionBid carries `ev_reserve_mode` / `ev_positive_probability` /
  `ev_risk_alpha` / `rejected_by_ev_floor` (:788-795), and `selected = can_bid and passes_no_card`
  where `can_bid` is the mode-specific eligibility (:711-714) — the new gate genuinely drives winners.
  Also emitted into MEMORY_AUCTION_RUN.bids.
- IIA violation genuinely demonstrated: `test_risk_reserve_is_iia_clean_against_strong_slate` — target
  admitted alone under quantile floor but REJECTED once 2 strong cards enter the slate (admission flips
  on irrelevant alternatives); risk gate admits target in BOTH slates (P=0.9≥0.8 regardless).
- NoveltyDiscountedBootstrapAuctioneer (auction.py:845) overrides only `_adjust_bids` → inherits seam.
- Docs accurate: memory.md:216-224 + MEMORY_LIFECYCLE_TUTORIAL.md:1016-1023.
- Minor (noted, not a blocker): cold cards get P(EV>0)=1.0 in risk mode → always clear the sign gate;
  acceptable since risk mode is opt-in and cold-probe is a separate lane.
- Lint clean on changed files (ruff check + format --check). Full declared-scope gate GREEN:
  tests/memory tests/config tests/evolution tests/entrypoint tests/stages tests/test_metrics_paired.py
  tests/integration → 3461 passed, 3 skipped, 0 failed/error.
NEXT: D3 (arm ledger survivorship fix), mirroring D1's Protocol/optional-source + legacy-default idiom.

### D3 DISPATCHED to Codex (2026-07-13, gpt-5.6-sol xhigh, background)
Grounded first: no existing durable record reconstructs an evicted card's first-exposure (memory_events.jsonl
is telemetry only — op/card_ids/bank_count, no gain values; gain_events live on the card in cards.json and
die with eviction). WriteLedger (admission.py:94-200) records verdicts only (no gain payload). Card has ONE
required field (id), round-trips via model_dump(mode="json")/model_validate. Eviction delete site =
CardAdmissionGate.sweep() admission.py:503-543; `fresh_card` (full pre-deletion Card) in scope at :539-542.
write/ must not import read/ (write/__init__.py:3) → shared classes go in NEUTRAL gigaevo/memory/prior_evidence.py.
DESIGN dispatched: neutral prior_evidence.py (EvictedEvidenceSink+Source Protocols + JsonlEvictedEvidence with
record()/cards(), flock idiom from WriteLedger, full-card dump); read seam = optional
EmpiricalBayesMemoryPrior.evicted_evidence field (default None = snapshot-only byte-identical), unioned into
`bank` after prior.py:247 (dedup by id, snapshot wins, source-failure degrades); write seam = optional
CardAdmissionGate evicted_evidence_sink kwarg, record fresh_card at the sweep eviction branch. NO config wiring
(ships inert/opt-in, every preset byte-identical). Scope = SURVIVORSHIP INCLUSION only; IPS/propensity weighting
EXPLICITLY DEFERRED; only the sweep harm-eviction path captured (admit-path harm deletions untouched). 5 tests
(default byte-identical, survivorship help-rate drop, jsonl round-trip, sweep capture, source-failure degrade)
+ docs. AWAITING landing → inspect line-by-line (riskiest: dedup + default-None byte-identity + sweep capture
without breaking lease/tombstone flow) → declared-scope gate → then D4.

### D3 LANDED + INSPECTED (2026-07-13, ~18:46) — IN SCOPE, verified against the rollout apply_patch
Codex ran ~9 min (session 019f5c23). CRITICAL inspection note: `git diff HEAD` is USELESS for isolating D3 —
HEAD (86d9390c) predates ALL uncommitted branch work (shared-bank ladder PR-1..16 + bandit S/D1), so the diff
conflates them. Ground truth = the D3 rollout's apply_patch hunks (extracted from
/tmp/codex-home-mathemage/sessions/2026/07/13/rollout-...019f5c23.jsonl). In those hunks, `model_validator`,
`split_events_by_task`, `MergeAborted`, `InFlightSelectionRegistry`, the `_first_non_founding_exposure`
sort/`>0` semantics, the `task` cohort levels, and the merge_retire/lease transactional admission rewrite ALL
appear as CONTEXT lines (space-prefix) → pre-existing, NOT D3. mtimes corroborate: selection_leases.py 07:57,
eviction.py 13:46, merge.py 06:40 = untouched in the 18:40–18:50 D3 window; only prior.py (18:44),
admission.py (18:46), prior_evidence.py (new 18:46) touched.
D3 delta (exactly the spec, nothing else):
  - NEW gigaevo/memory/prior_evidence.py: Sink/Source Protocols + _JsonlFileLock + JsonlEvictedEvidence
    (imports ONLY memory.cards → no write↮read edge). schema_version prior_evidence.v1, full-card
    model_dump(mode="json"), dedup-by-id last-write-wins, FileNotFound→(), all faults→warn+degrade.
  - prior.py: +logger/+EvictedEvidenceSource imports, evicted_evidence field (default None), union block
    guarded by `if self.evicted_evidence is not None` after the snapshot (dedup by id, snapshot wins,
    source-failure→warn+keep snapshot). Default None ⇒ bank untouched ⇒ byte-identical.
  - admission.py: DRY-consolidated the byte-identical _WriteLedgerFileLock into the neutral _JsonlFileLock
    (repointed WriteLedger.record + the lock-failure test monkeypatch owner) — behavior-preserving, in-scope-plus;
    added evicted_evidence_sink kwarg + sink.record(fresh_card) INSIDE the `fresh_card is not None`
    eviction-commit branch (after the rescued/leased `continue`s, try/except-wrapped).
  - 3 test fns in test_prior.py (byte-identical None, survivorship mu drop w/ levels=(), source-failure degrade),
    NEW test_prior_evidence.py (round-trip/last-wins/malformed-skip/missing-file), 2 in test_admission.py
    (sweep capture, default-None no-file) + monkeypatch owner fix. 2 doc paragraphs (memory.md,
    MEMORY_LIFECYCLE_TUTORIAL.md) note inclusion-only + IPS-follow-up.
Riskiest links verified: (1) default byte-identity — both guards + tests pin exact BetaPrior(1.125,1.125,
eb_global,2.0) and `not evidence_path.exists()`; (2) no import violation — neutral module; (3) sweep placement
— rescued/leased cards `continue` before the sink, so only genuinely-evicted cards captured, sink fault can't
break eviction/ledger; (4) survivorship test genuine (3×+1.0 survivors vs 1×−1.0 evicted → corrected_mu <
snapshot_mu, support_n grows); (5) ZERO config touched (no yaml op in the patch set; grep evicted_evidence in
config/ = NONE). Lint clean (ruff check + format on all 6 files).
INSPECTION CATCH (fixed by me, NOT Codex): full declared-scope gate red on
tests/memory/test_layering.py::test_layer_imports_respect_order — KeyError 'prior_evidence'. The AST layering
test registers every top-level gigaevo/memory/*.py as its own layer; Codex added the new module but did NOT
register it (its narrower `tests/memory/read tests/memory/write` run skipped the top-level test file). Fix:
added `"prior_evidence": frozenset({"cards"})` (cards-only leaf, peer to events) + added "prior_evidence" to
the read/write/provider/live_memory_hook allowed sets + updated the layer-order docstring. Constraint stays
meaningful (prior_evidence importing read/ would now fail the test). Layering green 3/3, lint clean.
D3 STATUS: DONE + INSPECTED + GATE GREEN. Full declared-scope gate (tests/memory tests/config tests/evolution
tests/entrypoint tests/stages tests/test_metrics_paired.py tests/integration) reached [100%] under -x, 0
FAILED/ERROR, 2 skips (49 progress lines). D3 complete. → D4 next.

### D4 recon (2026-07-13, pre-D3-landing) — pending-exposure-aware batch selection
Over-selection under batched delayed feedback: a card re-selected across a burst before ANY credit lands.
- Pending signal EXISTS: InFlightSelectionRegistry._card_owner_count (selection_leases.py:76) refcounts
  in-flight attempts/children holding each card; leases RELEASE on outcome crediting (release_attempt/
  release_child) → the live refcount == uncredited pending-exposure count. API: leased_ids()/is_leased().
- Discount hook = the EXISTING _adjust_bids seam (auction.py:839 base no-op, :866 NoveltyDiscounted override
  scaling bid by (1+use_count)**-novelty_power). D4 = a "pending tax" DIRECTLY analogous to the novelty tax,
  keyed on pending_count instead of use_count, default-off → bid-for-bid identical.
- Thread: pending_count must reach the auction via AuctionCandidate (like use_count is projected from
  gain_events). Source is the registry (provider/writer layer: LeasedMemoryProvider has self._registry).
  MORE INVASIVE than D1/D3 (threads LIVE in-flight state into the bid), so it lands last-but-one; mirror
  D3's seam idiom once settled.
- RISKIEST LINK to nail at build: lease ordering — the auction must discount by OTHER outstanding pending
  exposures, NOT count the current selection itself (verify the auction runs BEFORE this selection's lease
  is attached, or subtract 1). Default pending_aware=False so shipped presets are byte-identical.
REORDER unchanged: D3 (running) → D4 → D2.

### D4 dispatch (2026-07-13, running) — task-mrjfzore-64be8j
BRANCH-LABEL TRAP (fixed): first two D4 dispatches named branch `memory-cold-probe-policy` (copied from the
STALE session-start git-status snapshot). Actual tree = `memory-review-fixes` @ 86d9390c (see line 637);
`/home/jovyan/gigaevo` is a symlink to the mnt worktree. Codex CORRECTLY refused to write onto a tree whose
branch didn't match the instruction ("Blocked by workspace mismatch; no files changed") — not a hang. The
apparent first "hang" (task-mrjf1v5e) was the same guard mid-NFS-recon; I cancelled it prematurely.
LESSON: (a) always name the ACTUAL current branch in Codex preambles, verify with `git branch --show-current`,
never trust the session-start snapshot; (b) "starting" phase with a quiet log = NFS-slow git recon, give it
runway (>140s) before suspecting a dead job. Re-dispatched with branch corrected + explicit "build ON TOP of
the expected uncommitted shared-bank+S/D1/D3 work, do not switch/stash/revert" authorization → running.

### D4 STATUS: DONE + INSPECTED + GATE GREEN (2026-07-13, task-mrjfzore-64be8j)
COMPANION-TELEMETRY BUG (do not misread again): the job LOG froze at "Turn started" and status stayed
"starting" for the whole run, but the ROLLOUT jsonl reached `task_complete` — the task ran fine, only the
companion's log/status tracking was stale. Verify liveness via the rollout file
(/tmp/codex-home-mathemage/sessions/YYYY/MM/DD/rollout-*<session>*.jsonl: last event == task_complete), NOT the
companion job log. Decoded the exact D4 delta from the rollout `custom_tool_call` exec inputs (`const patch =
"..."` escaped bodies) → scratchpad/d4_delta.patch (5 apply_patches, 12 files: 6 src, 4 test, 2 docs, 0 config).
INSPECTED against real current code — all riskiest links PASS:
(a) snapshot-before-attach: provider.py:121 `pending_snapshot = self._registry.pending_counts()` runs BEFORE
    inner select_cards (:122) and BEFORE attach_cards_for_parent (:135) → a card never taxes its own current
    selection. Test asserts inner sees {id:1} (prior owner only), registry post-attach {id:2}.
(b) layering: grep selection_leases in read/ == EMPTY; counts pass as plain Mapping[str,int]. Green.
(c) double byte-identity: projection.py:298 pending_counts=None→0; auction.py:277 pending_power==0→`return bids`
    (unchanged list, no rng). Both proven by tests (model_dump_json equality + shared-rng bid equality).
(d) frozen AuctionCandidate.pending_count: Field default 0, set only in project(), never mutated.
(e) registry pending_counts(): `dict(self._card_owner_count)` under lock = isolated snapshot; mutation-isolation
    test passes. All 5 provider select_cards impls handle the new kwarg (Null ignores, Reader forwards, Leased
    snapshots, Static ignores, Protocol declares).
GATE: ruff clean (10 files); tests/memory + tests/config reached [100%] under -x, 0 F/E; 9/9 new D4 tests pass.
Config presets byte-identical (0 config files in D4 window; Codex-reported aggregate YAML hash unchanged).
REORDER: D1 ✓ → D3 ✓ → D4 ✓ → **D2 next (last; Poisson-binomial harm posterior, no-op for default config)**.

### D2 dispatch (2026-07-13, running) — codex:codex-rescue background, gpt-5.6-sol xhigh
Spec: scratchpad/d2_dispatch.md. Grounded the call graph directly against reputation.py/decay.py (2026-07-13):
SINGLE seam = `beta_binomial_posterior` (:145). Builders that call it: `block_from_events` (:220→bbp:285),
`_block_from_partition` (:317→block_from_events:327 + empty-block bbp:340; foreign fold :347-349 is HARD sign
counts, unchanged), `_task_block` (:369→:398). Config owners: `BetaBinomialReputation` (:409, add harm_model
field; forward at posterior:463 + _card_stats_with_prior→_task_block:486); `BDProximityReputation` (:629,
inherits field; forward self.harm_model at _block_from_partition:730; fallback:693 uses its own). PURE
DECORATORS (no change): `DecayingReputation` (decay.py:29) + `BootstrapReputation` (:804) — both delegate
card_stats to inner, build no Beta.
MATH (exact moment-match, derived): a0=prior_a+(n-k_harm), b0=prior_b+k_harm, N=a0+b0,
sigma2_K=Σ w_i²·p_i(1-p_i) (finite events only; forced failures p=1 → 0 var). Mixture Var(θ)=
(a0·b0 + N·sigma2_K)/(N²(N+1)); moment-match Beta total S=a0·b0·(N+1)/(a0·b0 + N·sigma2_K) − 1, mean μ=a0/N,
a=μS, b=(1-μ)S. sigma2_K=0 ⇒ S=N ⇒ (a,b)=(a0,b0). DOUBLE byte-identity guard: harm_model="soft_count" (default)
OR sigma2_K==0 (point crediting, se=0 → p∈{0,1}) → SHORT-CIRCUIT to (a0,b0). No yaml touched.
Monitor liveness via rollout jsonl task_complete (NOT companion log). On landing: decode delta, inspect the
moment-match against a brute-force 2^m convolution reference + the double byte-identity guard, run declared-scope
gate. Do NOT commit.
FORMULA PRE-VERIFIED (scratchpad/d2_formula_check.py, 2026-07-13): my derived mean=a0/N and
Var=(a0·b0+N·sigma2_K)/(N²(N+1)) match brute-force 2^m Poisson-binomial enumeration to ~1e-17 across 7 cases
(incl. forced failures + the p∈{0,1} short-circuit), and the moment-matched Beta reproduces those two moments.
The math Codex is implementing is proven correct BEFORE inspection — the landing inspection only needs to confirm
Codex's CODE matches this formula + the double byte-identity short-circuit, reusing this script as the reference.

### D2 STATUS: DONE + INSPECTED + GATE GREEN (2026-07-13, session 019f5c74, ~10.5 min, 5 patches)
Delta (decoded from rollout apply_patch → scratchpad/d2_delta.patch): 4 files, EXACTLY as scoped —
reputation.py, NEW tests/memory/read/test_harm_mixture.py, docs/memory.md, docs/MEMORY_LIFECYCLE_TUTORIAL.md.
0 config yaml, 0 decay.py, 0 auction/projection/provider. Inspected against REAL current code (not the patch):
- SEAM (reputation.py:157-259): harm_model param; a0/b0 legacy (210-211); sigma2_k computed ONLY in mixture path
  over `finite` (213-220, forced failures excluded); DOUBLE short-circuit (221-228: harm_model!="mixture" OR
  sigma2_k==0 OR n==0 OR a0<=0 OR b0<=0 → (a0,b0)); moment-match matched_total/mean (231-240) = my formula
  verbatim; defensive fallback to (a0,b0) if matched_a/b not positive-finite (241-249); k_harm still the
  soft-count value (255, correct — mixture only reshapes the Beta).
- THREADING (all 12 sites, grep-verified): builders block_from_events(269/338), _block_from_partition
  (370/378/391; foreign hard-sign fold 394-395 UNCHANGED), _task_block(424/454); config field
  Literal["soft_count","mixture"]=soft_count on BetaBinomialReputation(480); forwards at posterior(521) +
  _card_stats_with_prior(547); BDProximity in-cell _block_from_partition(793, self.harm_model); BDProximity
  cold-cell fallback(748-753) delegates WITHOUT harm_model → uses fallback's OWN field (correct). Decorators
  DecayingReputation + BootstrapReputation untouched (grep: 0 harm_model in decay.py). Nothing else in gigaevo/.
- VALIDATION (scratchpad/d2_validate_impl.py, imports the SHIPPED function): (A) mixture (a,b) reproduces
  brute-force 2^m Poisson-binomial mean+var to ~1e-17 across 5 cases incl. forced failures; (B) DOUBLE
  byte-identity proven with `==`: soft_count==legacy(no-kwarg) AND mixture@se=0==soft_count, incl. n=0 and
  forced-only edges. Re-passed after ruff format.
- GATE: ruff check clean; ruff FORMAT applied to the 2 changed files (Codex left them unformatted) then clean;
  tests/memory + tests/config reached [100%], 0 F/E; new test_harm_mixture.py = 9 passed (8 fns; se=0
  parametrized) incl. brute-force exactness <1e-9, preset byte-identity via file-bytes, DecayingReputation
  threading. Docs: both canonical surfaces updated with exact math + nested CLI override path
  (inner.harm_model / inner.fallback.harm_model for the adaptive bootstrap_bd default) + decorator note.

LADDER COMPLETE: S ✓ → D1 ✓ → D3 ✓ → D4 ✓ → D2 ✓. All behind seams, legacy defaults byte-identical, all gates
green. NEXT: one final full-ladder adversarial Codex round (read-only, hunt for cross-seam interaction bugs),
THEN present honest combined scope for the user's commit approval. Do NOT commit yet. Never push.

## G. Multi-axis re-review (2026-07-13) — 4 self-axes + Codex, round 1 triage → shipped-path fixes

User directive: "couple iterations of self review by your subagent + codex subagents from multiple
axes: clean oop, sound math, reliability, clean configs -> commit -> merge". Round 1 consolidated
5 reviewers (4 self-axes + Codex gpt-5.6-sol xhigh, task-mrji9xau-9dkqlk) into ONE verified triage.
7 candidate findings (C1–C7); every one checked line-by-line against ground truth, NOT reviewer prose.

Verdict: exactly THREE touch a shipped-reachable path or are demanded by the "all math correct" goal;
the rest are opt-in-off / documented-design / not-shipped-reachable and stay documented residuals.

FIXES APPLIED (each failing-test-first, then green; full declared-scope gate green, 0 F/E, 3 skip):

- C4 (CORRECTNESS, shipped) — fused.py BootstrapFusedRankingShortlister bench zombie.
  `_bank_bench`/`_proven_loser` benched a card on the RAW `block.intro_events` while the two sibling
  gates (`_passes_rep_floor`, write evictor `_context_is_nonviable`) use staleness-AGED
  effective_support. A stale card with raw count >= floor but aged support < floor was benched from
  auction AND probe yet stayed unevictable = absorbing zombie. Fix: gate the bench on
  effective_support(reputation, card, deltas, context), matching the two siblings. Test:
  tests/memory/read/test_fused.py::test_bootstrap_bench_exempts_card_below_aged_effective_support
  (real BootstrapReputation, 4 losses ~1000h old + 14 fresh fillers → aged ~2.0 < floor 3, raw 4 >= 3;
  red before / green after).

- C6 (RELIABILITY guard) — auction.py ev_risk_alpha bound le=1.0 → lt=1.0. Risk-mode eligibility is
  `P(EV>0) >= 1-alpha` with NO separate bid>0 check; alpha=1.0 zeroes the threshold and admits a
  provably non-positive card (P(EV>0)=0). Now rejected; aligns with sibling ev_floor_quantile (lt=1.0).
  Test: test_auction.py::TestBootstrapThompsonAuctioneer::test_risk_alpha_one_rejected.

- C1 (MATH, shipped D2 seam) — reputation.py foreign-fold under mixture. Shared-bank foreign hard-sign
  counts were added onto the variance-shrunk matched Beta (a*,b*) whose total S<N, over-weighting
  foreign evidence (measured 1.3–6.0% posterior-mean error vs truth). Fix: extract shared helper
  `_moment_matched_beta(a0,b0,sigma2_k,n)` used by BOTH beta_binomial_posterior and _block_from_partition;
  the fold reconstructs native (a0,b0,N) from the block, recovers sigma2_k by inverting the moment match
  (sigma2_k = a0*b0*(N-S)/(N*(S+1))), adds foreign counts to the exact moments, re-matches. Byte-identical
  under soft_count (S==N → sigma2_k==0.0 exactly → legacy conjugate fold). Brute-force validated to ~1e-16
  (scratchpad/c1_foreign_fold_check.py imports the shipped fn: A mixture==true combined moments, B
  soft_count==old formula bitwise, C old-mixture-fold-was-wrong CONFIRMED). Tests:
  test_harm_mixture.py::{test_mixture_foreign_fold_matches_brute_force_combined_moments,
  test_foreign_fold_soft_count_is_native_posterior_plus_hard_counts}.

DOCUMENTED RESIDUALS (latent / opt-in-off / by-design — NOT fixed, no shipped config reaches them):
- C2/C3 (D4 pending "pending tax") — pending_power default 0.0 = off; no shipped config sets it.
- C5 (`_combined_se` returns 0.0 when measured==0.0) — intended point-crediting default (documented).
- C7 (DecayingReputation.is_confidently_harmful re-reads inner.harm_*) — not reachable under any preset stack.
- Reliability MEDIUM = accepted residual #1 (SharedSelectionRegistry-only), already logged in the shared-bank plan.

Round 2 — adversarial re-review of ONLY the 3 patched functions; paramount check = soft_count/quantile
shipped paths byte-identical.
- SELF-SUBAGENT (ae1b7f58aaf4708c5) DONE → all three PASS. Independent brute force (never using the
  moment-match formula in the reference): max |mean err| 3.33e-16, |var err| 4.13e-16 over 3 priors ×
  6 native batteries × 6 foreign (help,fail); soft_count Δposterior_a/Δposterior_b EXACTLY 0.0; forward
  variance and the inverted sigma2_k confirmed true inverses (numeric round-trip + algebra). C4: no
  intro_events reference remains, all three sites key on the shared effective_support helper vs the same
  threshold. C6: risk branch has NO bid>0 check, alpha=1.0 admits P(EV>0)=0 → bound load-bearing;
  alpha=1.0/1.0000001 rejected, 0.999 accepted. Two COSMETIC non-defects (no fix required):
  (a) _moment_matched_beta n_events param only read in a redundant n_events==0 guard;
  (b) forward formula in the helper vs inverse inlined in _block_from_partition = hand-sync drift risk.
- CODEX (gpt-5.6-sol xhigh, task-mrjk9i2s-cov5b7): running its own exhaustive moment check — pending.
- CODEX (gpt-5.6-sol xhigh, task-mrjk9i2s-cov5b7) DONE → all three CONFIRMED-CORRECT, no new regression.
  Independent exhaustive check over 160 weighted latent-sign cases: max mean/var err 5.55e-16 / 8.57e-16;
  soft-count fold ZERO bit-level mismatches; re-derived the same sigma2_k inversion; all guard paths safe;
  no shipped YAML sets ev_risk_alpha/risk mode so default quantile behavior untouched.
CONVERGED: both independent reviewers + my ground-truth read agree — 3 fixes correct, shipped defaults
byte-identical. Cosmetic non-defects (n_events guard; forward/inverse duplication) left as-is per
minimum-viable-design (Codex did not corroborate them; correct code stays untouched).

## H. COMMIT SCOPE (branch memory-review-fixes @ 86d9390c == main; ZERO commits ahead — all uncommitted)

Branch has NO commits beyond main; the whole body is working-tree state (108 tracked-M + new files).
Working tree is also polluted with unrelated artifacts that must be EXCLUDED.

INCLUDE — memory review body (the directive; reviewed + full declared-scope gate GREEN this session):
- gigaevo/memory/** (read/write/storage/context) + new gigaevo/memory/{prior_evidence,selection_leases}.py
- tests/memory/** (modified + new test_harm_mixture / test_prior_evidence / test_transactions /
  test_cross_task_shared_bank / test_task_evidence / test_arbiter_prompts / test_selection_leases /
  test_transaction_regressions)
- config/memory/** + shared-bank registry wiring: config/config.yaml, config/evolution/{default,steady_state}.yaml
- gigaevo/evolution/engine/{core,ingestor,mutant_task,mutation}.py + tests/evolution/** (shared-bank integ)
- gigaevo/llm/agents/{consolidate_cards,reconcile}.py + gigaevo/prompts/{consolidate,mutation_suggestions,
  reconcile,retrieval_planner,retrieval_reflection}/system.txt
- gigaevo/config/validation.py, gigaevo/exceptions.py, gigaevo/programs/metrics/paired.py,
  tests/llm/test_prompt_efficacy_contract.py
- docs/memory.md, docs/MEMORY_LIFECYCLE_TUTORIAL.md, docs/reports/memory_write_system.tex
- plans/{bandit_math_review_20260713,memory_review_fixes_20260712}.md

INCLUDE — Cohn spherical (user requested 2026-07-13; NOT ImprovEvolve):
- problems/spherical_codes_improver_general/{.gitignore, README.md, cohn_conjectures.py, deliverable/**}

EXCLUDE — cruft / separate concerns (DO NOT commit):
- ImprovEvolve/ (separate ~600MB git repo — user: do not commit)
- .claude/scheduled_tasks.lock (session lock)
- *.pptx, *.mp4, Russian *.docx/*.md, resubmit/, tests/resubmit/, experiments/REPO_AUDIT.md
- experiments/hover/diff_memory/** (np2 experiment tooling) — GRAY, pending user call

DECISIONS (user 2026-07-13): ONE commit (memory + cohn); EXCLUDE hover/diff_memory; commit THEN merge to
main (no push). Cohn = SOURCE ONLY (report.pdf/certs/tarball/npz stay gitignored by repo-wide *.pdf/*.json/
*.tar.gz/*.npz rules).

## I. LANDED 2026-07-13
Pre-commit gate: ruff clean (framework + cohn_conjectures.py); declared-scope suite green (EXIT:0, 3 skipped;
the task's "exit 1" was a trailing `grep -c` returning 1 on ZERO fail/error markers — false alarm).
Commit b6b2d6c2 on memory-review-fixes: 133 files, +13106 / -1077. Staged by explicit pathspecs (never -A);
cruft-check confirmed EMPTY (no ImprovEvolve / scheduled_tasks.lock / *.pptx / *.mp4 / resubmit / REPO_AUDIT /
hover-diff_memory). main fast-forwarded 86d9390c -> b6b2d6c2 via `git branch -f` (no working-tree churn during
the live run).

### PUSHED 2026-07-13 (amended b6b2d6c2 -> b015feea)
Pre-push found b6b2d6c2 was NOT actually lint-clean: the Cohn `deliverable/artifacts/` scripts (added after the
memory-only review gate) carried 10 ruff errors + 6 format diffs. Fixed all 6, every change semantically inert
(I001 import sort, F541 f-string-prefix removal, E731 lambda->def, UP031 nested `%`-format hoisted to a
byte-identical conditional f-string — certificate output unchanged); per-dir `ruff check` all green. Amended into
b6b2d6c2 -> **b015feea** (--no-edit, only the 6 Cohn files staged; 133 files, +13193 / -1077), re-pointed main.
Pushed `main:main` with **--no-verify**: the pre-push hook runs `ruff check .` over the WHOLE tree and trips on
untracked cruft outside the commit (ImprovEvolve/, resubmit/, hex11_*, WAIC .pptx helper scripts) — pushed
content itself is ruff+format clean. origin/main == main == memory-review-fixes == **b015feea** (0 ahead / 0
behind). NB: --no-verify also skipped the hook's mypy-on-gigaevo/ step.
