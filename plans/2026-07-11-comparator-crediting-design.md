# Comparator-based card crediting: complete design (OOP, config-first)

Date: 2026-07-11. Status: PROPOSAL, revised post-review — no code. Branch: memory-cold-probe-policy.
Prior discussion: crediting on single-eval deltas is noise-corrupted; user accepted
the comparator seam (returns verdict + effect + se) and asked for a fully OOP,
config-first build. This doc is the build spec, revised per three independent
Opus 4.8 reviews (below).

## Review synthesis (2026-07-11, three independent Opus 4.8 reviewers)

| Reviewer | Verdict | Headline |
|---|---|---|
| OOP/config architect | SOUND-WITH-REVISIONS | plumbing undercounted; 2 hidden branches; wrong freeze site; hard-error on missing vector must be graceful |
| RL/math statistician | SOUND-WITH-REVISIONS | jitter double-counts eval variance; fractional Beta counts understate posterior variance; riskiest link = correlated run-level noise η, needs calibration study as a HARD pre-A/B gate |
| Bandit/decision theorist | SOUND-WITH-REVISIONS | jitter exploration semantics are correct (de-crowns lucky cards 0.75→0.25, explores unlucky 0.00→0.065); BUT it silently converts the hard abstain-on-all-harmful invariant into a soft one (optimizer's curse, ~10-15% end-to-end marginal-harm leak); soft k_harm cuts false eviction of genuinely-good cards 13.3%→1.9% |

Load-bearing revisions folded into the spec below:

1. **Graceful degradation, not hard error** (OOP-F1): `get_per_sample_scores`
   legitimately returns None (seed parents, degenerate vectors, coherence fail at
   1e-4 tol). Missing vector on a valid child → `Measurement(delta, se=0.0)` per
   event (exactly what `PairedBootstrapArchiveSelector` does), count degradations
   for telemetry. Hard error only for config-level impossibility (non-routing
   pipeline), and that fires at compose time.
2. **Branch honesty + rng guard** (OOP-F2, F11): "zero branches" was false.
   Two explicit degenerate branches exist and are load-bearing: (a)
   `bootstrap_ev_samples` must guard `if ses.any()` before touching the shared
   per-round rng — otherwise `crediting=point` under the bootstrap stack consumes
   rng draws and breaks seed-exact replay AND the design's own bit-exact
   regression test; (b) the harm soft-count needs an explicit `se == 0` branch
   (indicator), else 0/0→nan at value == threshold.
3. **Correct freeze site + full plumbing inventory** (OOP-F3, F4): per-claim
   vectors live in `program.metadata["per_sample_scores"]`, NOT metrics; the
   freeze site for `base_scores` is `mutation.py:108-109` (stats.py:405-414 only
   READS frozen metadata). Child scores must be captured too. C3 plumbing:
   `ReputationModel` protocol grows `event_ses` beside `event_deltas`/`event_weights`
   (all four impls), `_ev_ses` helper aligned atom-for-atom, `AuctionCandidate.deltas_se`,
   projector populates it. This is the bulk of the C3 work.
4. **Harm model: inline, not per-preset objects** (OOP-F5, minimum-viable):
   drop the `HarmModel`/`GaussianTailHarm` class + per-preset `harm_model:` nodes
   (bd_proximity/bootstrap_bd presets have TWO reputation nodes each — duplication
   hazard). Instead `beta_binomial_posterior(..., event_ses=None)` computes harm
   mass `Φ((thr − g)/se)` when `se > 0`, exact indicator otherwise. Zero config
   churn in presets; promote to a seam only if a second harm model ever exists.
5. **Jitter kept, with corrected claims** (RL-F2 vs Bandit-F1/F5/F6): the jitter
   term scales as `se²/n` (correct SE-of-mean scaling, no constant floor,
   staleness-weighted correctly) and rescues the degenerate n=1–3 bootstrap.
   BUT observed atoms already contain eval noise, so jitter double-counts it
   (~+55% bid variance asymptotically; conservative bias, wider not wrong).
   Documented as a known conservatism. If the A/B shows over-exploration, the
   coherent v2 is ONE normal-normal random-effects posterior over μ_card
   (MoM τ̂² = max(0, s²_between − mean(se_i²)), Var(μ̂) = 1/Σ1/(τ̂²+se_i²)) which
   fixes RL-F1+F2+F6+F7 together — same seam, drop-in.
6. **Abstain invariant goes soft — say so and gate it** (Bandit-F2, MAJOR):
   with jitter, P(all-marginally-harmful round injects ≥1 card) goes ~0 → ~10-15%
   end-to-end (optimizer's curse; the Šidák no-card gate is a partial backstop).
   Confidently-harmful cards (≤−0.02, or ≤−0.01 at n≥10) essentially never leak,
   and eviction still fires in 3–4 events for them (Bandit-F3), so regret is
   bounded. Resolution: correct the `BootstrapThompsonAuctioneer` docstring
   ("all-negative rounds win nothing" → "confidently-harmful abstain;
   marginally-harmful get bounded exploration backstopped by eviction"), and add
   eviction fire-rate + cold-probe fire-rate as A/B guardrail metrics. If
   all-marginal rounds prove common, the self-normalizing escalation is a
   pessimistic-EV admission gate on the max-bid winner
   (`bootstrap_ev_quantile ≥ 0`) — se=0-exact, no new constants.
7. **C1×C3 co-activate** (Bandit-F4): in the default bootstrap stack the
   auctioneer's no-card gate theta comes from the C1-softened posterior AND the
   bid is jittered — the two marginal-harm guards soften together. Directionally
   coherent (documented), monitored via the same guardrail metrics.
8. **Known limitations, documented not built** (RL-F1, F4, F6, F7): fractional
   Beta counts are a plug-in (understate posterior variance ~21% sd at n=3;
   exact 2ⁿ mixture is the upgrade); baseline B̂ error (~0.002) is shared across
   events and dominates EV at n≳30 (propagate Var(B̂) once per card if it ever
   matters); C2 median is noise-dominated at n=1–3 on the classic stack but
   `magnitude_of` prefers bootstrap-EV mean on the bootstrap stack (moot there);
   children of one parent share −ε_parent (correlated events; cluster-by-parent
   effective-n is the fix if calibration shows it biting).
9. **Calibration study is a HARD pre-A/B gate** (RL-F3, F8 — the riskiest link,
   upgraded): see "Riskiest link" below. se may miss the correlated whole-run
   component η exactly when it dominates. Gate: empirical calibration against
   K≥10 re-evals of BOTH halves of stored pairs; if under-calibrated,
   `se ← √(se² + η̂²)` (η̂ is also the se floor).
10. Minor corrections adopted: prediction C-4 reworded (well-measured cards DO
    widen, ~8–11× at n=10–25 — the honest statement is concentration drops and
    bid sd rises ≈ se/√(n+1)); paired==point value identity asserted within
    COHERENCE_TOL=1e-4, not bit-exact (OOP-F9); `higher_is_better` passed into
    `estimate()` rather than injecting metrics_context (OOP-F10); `k_harm`
    becomes fractional — float-safe in decay.py, field doc updated (OOP-F7);
    compose guard can only check the routing axis (`pipeline.routes_program_metadata`,
    mirroring `validate_paired_selector_pipeline_compat`), never "vectorized
    problem" — vector presence is handled by per-event degradation (OOP-F6).
    Selection bias from the optimizer's curse does NOT poison crediting: the
    injected winner's gain is measured as a fresh child−parent delta independent
    of the inflated bid — no feedback loop (Bandit, checked-and-clear).

## Problem restated

An event's gain is `oriented_delta(child_fitness, parent_fitness) − no_card_baseline`
computed from two single evaluations (`stats.py:266-268`). Single-eval σ≈0.0078 on
hover; true per-mutation effects are 0.005–0.02, so the SIGN of a single event is
close to a coin flip. Three consumers read this evidence today:

| Consumer | Where | What it does with events | Noise exposure |
|---|---|---|---|
| C1 help/harm posterior | `reputation.py` `beta_binomial_posterior` | hard sign count: `k_harm = Σ w·1[g<0] + forced_failures` → Beta(a,b) → p_help, efficacy_confident, harm predicate (eviction) | **acute** — per-event Bernoulli labels; noise corrupts counts; more events do NOT fix it |
| C2 magnitude | `reputation.py` `block_from_events` | `median(use_gains)` → IntroGain_best_median | benign-ish — aggregate; but noise-dominated at n=1–3 (classic stack only; bootstrap stack reads EV mean) |
| C3 auction bid | `bootstrap.py` `bootstrap_ev_samples` / `bootstrap_ev_quantile` | resample raw delta atoms (invalid/unused → 0.0 atoms, + neutral zero pseudo-event, staleness weights) → mean = Thompson draw; low quantile = pessimistic EV | between-event spread captured; **within-event eval noise invisible** — atoms treated as exact |

## Architecture: one config fork, typed objects everywhere

The design has exactly ONE behavioral fork, and it lives in config: **how an
event's effect is measured** (`memory/crediting`). Downstream consumers are
generalized to consume the typed measurement; at `se=0` every consumer is
value-identical to today (bit-exact except where COHERENCE_TOL applies), so the
`point` preset IS the control arm and old banks load unchanged. Two explicit
degenerate branches exist and are documented (rng guard in the bootstrap;
indicator branch in the harm mass) — they are what MAKE se=0 exact.

### Component map

| Component | Kind | File | Selected by |
|---|---|---|---|
| `Measurement` | frozen value object: `value: float`, `se: float = 0.0 (ge=0)` | `gigaevo/memory/cards.py` (next to `ContextualGain`) | — |
| `EffectEstimator` | Protocol: `estimate(outcome, higher_is_better) -> Measurement` | `gigaevo/memory/write/crediting.py` (new) | Hydra group **`memory/crediting`** |
| `PointEffectEstimator` | impl: `Measurement(oriented_delta(child, base), se=0.0)` | same | `crediting=point` (default) |
| `PairedEffectEstimator` | impl: same value (identity within COHERENCE_TOL) + se from the paired comparator on frozen per-claim vectors; **missing/degenerate vector → se=0 degradation, counted** | same | `crediting=paired` |
| `PairedComparison` protocol | grows **`estimate(new_scores, base_scores) -> Measurement`** beside `probability_better` | `gigaevo/programs/metrics/paired.py` | nested `_target_` |
| harm soft-count | inline in `beta_binomial_posterior(..., event_ses=None)`: `Φ((thr−g)/se)` if se>0 else indicator | `gigaevo/memory/read/reputation.py` | no config (formula, not impl) |

### Write side

- **`ContextualGain` gains `gain_se: float = 0.0`** (ge=0, flat field, no
  `Optional`). Old banks deserialize with the default, and `se=0.0` is the *true*
  statement about how their events were measured — additive contract, zero
  migration. (OOP-F8: affirmed.)
- **Per-claim vector freeze**: `InjectionOutcome` gains `base_scores` AND
  `child_scores` (`list[float] | None`), frozen at `mutation.py:108-109` — the
  same stamp site that freezes `base_metrics`/`base_fitness`; the source is
  `program.metadata["per_sample_scores"]`. Freezing is required for coherence:
  the event's value uses `base_fitness` frozen at birth; parent re-eval must not
  decohere the vector from it. Cost ~300 floats × 2 per outcome (accepted;
  bounded by ledger trimming).
- **`compute_contextual_gains(..., estimator: EffectEstimator)`**: the only
  place use-events are built calls `estimator.estimate(...)` and unpacks the
  `Measurement` into the event. Baseline subtraction stays where it is — a
  scalar shift of `value` from cohort no-card evidence; se unchanged (baseline
  uncertainty is shared/correlated across events; folding it per-event would
  double-count — documented limitation, see synthesis #8).
- **`MemoryWriter` takes `effect_estimator: ${ref:memory.crediting}`** — same
  flat `${ref:}` graph style as every other component in `full.yaml`.
- Invalid and unused events are untouched: a crash and a non-use are **exact
  binary observations**, not noisy measurements — forced-count treatment is
  already correct, and stays consistent across all consumers.

### Read side — where se is used

**C1 — help/harm posterior.** `beta_binomial_posterior` grows `event_ses`
(aligned with `event_deltas`/`event_weights`, default None = all-zero):
`k_harm = Σ wᵢ·harm_massᵢ + forced_failures` where `harm_massᵢ = Φ((thr − gᵢ)/seᵢ)`
if `seᵢ>0` else `1[gᵢ<thr]`. A +0.004 gain with se 0.008 contributes ~0.31 harm
instead of 0; a −0.03 gain contributes ~1.0 as before. Every reader — p_help,
p_help_lo20, efficacy_confident, eviction harm predicate, BD-proximity
partitions — inherits through this one formula. `k_harm` becomes fractional
(float-safe everywhere; field doc updated).

Quantified effects (bandit review, simulation): false eviction of genuinely-good
cards (+0.005) drops 13.3% → 1.9%; neutral 57% → 26%; confidently-harmful cards
still evict in 3–4 events (0–2 event delay); the delay lands on marginal cards
(−0.002..−0.005) where slow eviction is correct. Expected side effect: the
**posterior inflation loophole** shrinks — noisy-neutral events contribute ≈0.5
to each side, pinning posteriors near the prior instead of saturating p_help≈0.9.

**C3 — auction bid.** Atoms become (value, se, weight): `ReputationModel`
protocol grows `event_ses`; `_ev_ses` mirrors `_ev_deltas` atom-for-atom
(invalid/unused/neutral/cold atoms carry se=0); `AuctionCandidate.deltas_se`;
projector populates it. `bootstrap_ev_samples(deltas, ses, probs, ...)` draws
each **resampled** atom as `value + N(0, se)` — guarded by `if ses.any()` so the
point preset never touches the shared per-round rng (seed-exact replay
preserved). bootstrap.py stays pure numerics. Consequences (simulated): lucky
low-n cards de-crowned (win share 0.75→0.25 vs fair 0.10), unlucky low-n cards
explored (0.00→0.065); `bootstrap_ev_quantile` discounts noise automatically;
no new constants. Known conservatism: jitter double-counts eval variance already
present between atoms (~+55% bid variance asymptotically) — accepted for v1,
random-effects posterior is the drop-in v2 (synthesis #5). The auctioneer
docstring's hard abstain-on-all-harmful claim is corrected to the soft/bounded
statement (synthesis #6).

**C2 — magnitude: se deliberately NOT used.** `median(use_gains)` stays. On the
bootstrap stack `magnitude_of` prefers `IntroGain_bootstrap_ev_mean`
(reputation.py:610-613) so the median is moot there; on the classic stack it is
noise-dominated at n=1–3 — inverse-variance pooling remains a one-object upgrade
behind the same seam if evidence demands it.

### Config

```
config/memory/crediting/point.yaml    # _target_: PointEffectEstimator
config/memory/crediting/paired.yaml   # _target_: PairedEffectEstimator
                                      # comparison: {_target_: gigaevo.programs.metrics.paired.PairedBootstrap}
config/memory/full.yaml               # defaults: + crediting: point   (ships inert)
config/memory/writer.yaml             # same default
# reputation presets: UNCHANGED (harm soft-count is a formula upgrade, not a node)
```

- One knob for the A/B: `memory/crediting=paired` vs `point`. Consumers are
  universally noise-aware and degenerate at se=0 — no second knob to forget
  (output-consumption protection by construction).
- "One definition of better under noise": the archive gate
  (`PairedBootstrapArchiveSelector`) and `PairedEffectEstimator` both use
  `PairedBootstrap` (the selector already defaults to it internally,
  `paired_selectors.py:50-52`); the crediting preset declares it explicitly with
  the same defaults. Promote to a shared `${ref:}` node only if parameter drift
  becomes real.
- **Compose-time guard**: extend the existing run.py check (mirroring
  `validate_paired_selector_pipeline_compat`, `gigaevo/config/validation.py:199-231`)
  to reject `memory/crediting=paired` without a metadata-routing pipeline
  (`pipeline.routes_program_metadata`). Vector availability per-event is NOT a
  compose-time property — that is what graceful degradation handles.

## Causal chain

Per-event se from paired per-claim vectors (signal) → C1 counts expected harm
instead of coin-flip signs and C3 widens bids on eval-noisy evidence (behaviour)
→ posteriors for small-true-effect cards stay near the prior instead of random-
walking to confident-help/confident-harm; auction de-crowns lucky cards and
explores unlucky ones → card ranking correlates with replicable (K-re-eval)
effect, not one-eval luck → better card selection → MEM-arm fitness (metric).

## Riskiest link — HARD pre-A/B gate

The se computed from ONE eval's per-claim spread must track the true re-eval σ.
Per-claim spread estimates only the idiosyncratic component (√(1−ρ)·σ); a
correlated whole-run shift η (temperature, backend drift) is invisible to it —
worst case se→0 exactly when the shift dominates. **Gate (before any A/B):**
take ~30 stored parent/child pairs, re-run BOTH halves K≥10 times, compare each
pair's one-eval paired-bootstrap se against the empirical sd of the re-eval
mean-diffs (reliability slope ≈1). If under-calibrated, estimate η̂ and inflate
`se ← √(se² + η̂²)`; η̂ is also the se floor. If ρ is large and irreducible, the
seam still ships but `paired` stays off — that outcome is cheaper discovered
offline than mid-A/B.

## Predictions (for the eventual A/B — SEPARATE experiment, one-treatment rule)

| ID | Prediction | Falsified if |
|---|---|---|
| C-1 | offline gate: Φ-based P(harm) calibrated against K-re-eval sign-flip rate (reliability slope ≈1) | systematic under/over-confidence |
| C-2 | share of cards reaching efficacy_confident within 250 mutants DROPS (fewer lucky-sign promotions); those that do have higher re-eval'd median effect | confident set unchanged or worse |
| C-3 | p_help distribution de-saturates: mass near 0.9 shrinks, mass near 0.5 grows for cards whose re-eval'd effect ≈ 0 | inflation persists |
| C-4 | top-card win-concentration drops; per-card bid sd rises ≈ se/√(n+1) (ALL cards widen — most at low n) | concentration unchanged |
| C-5 | fitness: MEM arm ≥ point-crediting MEM arm (directional, K=5 CIs) | clearly below |
| C-6 | guardrails: eviction fire-rate for confidently-harmful cards unchanged; cold-probe fire-rate not starved; false-eviction of good cards drops | eviction stops firing, or probes starve |

## Build order (when approved — small, each step independently green)

0. **Calibration study** (riskiest-link gate; needs backends, not code-complete
   design): PairedBootstrap.estimate on stored per-claim vectors vs K≥10
   re-evals of both halves. Ship/inflate/abort decision for `paired`.
1. `Measurement` + `ContextualGain.gain_se` + `PairedComparison.estimate()` on
   `PairedBootstrap` (value = mean paired diff, se = bootstrap sd).
2. `write/crediting.py`: protocol + both estimators (graceful degradation path +
   degradation counter); `InjectionOutcome.base_scores`/`child_scores` freeze at
   `mutation.py:108-109`; `compute_contextual_gains` takes the estimator; writer
   wiring.
3. C1: `beta_binomial_posterior(..., event_ses)` soft harm mass (explicit se==0
   indicator branch); `k_harm` doc → fractional.
4. C3 plumbing: `ReputationModel.event_ses` (4 impls), `_ev_ses`,
   `AuctionCandidate.deltas_se`, projector; `bootstrap_ev_samples(..., ses)`
   jitter behind `ses.any()` guard; auctioneer docstring correction (abstain
   invariant → soft statement).
5. Config group + defaults (`point` everywhere) + run.py compose-time guard
   (routing axis only).
6. Tests: se=0 ≡ current outputs (bit-exact on reputation blocks; bootstrap
   draws bit-exact INCLUDING rng-stream position; paired==point value within
   COHERENCE_TOL), Φ soft-count unit cases incl. value==threshold at se=0,
   jitter widens quantile spread + rng guard test, degradation-path test
   (missing vector → se=0 event, not error), C-1 calibration script.
