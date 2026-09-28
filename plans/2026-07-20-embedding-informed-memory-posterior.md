# Embedding-informed memory-v2 posterior + calibration, empirical Bayes, and DR-OPE

**Date:** 2026-07-20
**Status:** DESIGN (plan-only; nothing implemented)
**Scope:** four interlocking upgrades to the memory-v2 causal head, all anchored on the card
embeddings we already compute but never feed to the Bayesian model.

---

## 0. Why these four go together

The four SOTA gaps are not independent — they form a dependency chain around one new signal
(card embeddings):

```
 (1) Calibration  ──────────────► the MEASUREMENT + the GO/NO-GO gate for everything below
        │                          (also the offline falsification test for (2))
        ▼
 (2) Embedding prior ──────────► the CAPABILITY jump: card-effect prior mean = f(embedding)
        │                          → evidence transfers between semantically-similar cards
        ▼
 (3) Empirical Bayes ──────────► sets (2)'s knobs PRINCIPLEDLY + removes the hardcoded prior
        │                          scales (0.75 / 0.35 / 0.25) that violate "no absolute constants"
        ▼
 (4) Doubly-robust OPE ────────► a BETTER reward model (2)+(3) is a better DR control variate;
                                   DR then evaluates the policy change offline, dodging the n=3
                                   live-A/B power problem
```

Card embeddings feed **all four**: the prior mean in (2), the direct-method control variate in
(4), and a slice-by-semantic-neighborhood axis in (1). Building them as one plan means one payload
change, one feature-map change, one report harness — instead of four disconnected PRs.

---

## 1. Where we are today (grounded in code)

- **Embeddings exist but are invisible to the Bayesian head.** They live in a per-scope
  `VectorIndex` (`gigaevo/memory/storage/index.py`), model `Snowflake/snowflake-arctic-embed-m-v1.5`
  (768-d), `nearest_scope = desc_expl` (= `description` + `explanation_summary`). They drive
  *retrieval* (`nearest()` / agentic research) only. The `CardSnapshot` the posterior fits over
  (`gigaevo/memory_v2/features.py`) carries **no vector**. Embedding of a card is a deterministic
  function of its text + the frozen model, so it is recomputable/replayable.
- **The reward-head card block is a zero-mean independent Gaussian.** Design row (per treated card
  `a`, context `c`, `d = context_dim`):
  `x = [ baseline(d) ; T·( shared(d) ; kind(1) ; retrieval(1) ; citation(1) ; card_block(n·d) ) ]`.
  Each card owns `u_a ∈ ℝ^d` with prior `N(0, card_effect_prior_sd² I)`,
  `card_effect_prior_sd = 0.25`, **independent across cards** → "shrink every card to the shared
  average." The solver is Bayesian ridge with a **diagonal** prior precision
  (`precision = diag(1/prior_var) + designᵀ W design`, `posterior.py`), residual σ marginalized by
  Gauss–Legendre quadrature; the **log marginal likelihood is already computed** in that path.
- **Prior scales are hardcoded constants:** `baseline 0.75 / shared 0.35 / card 0.25`
  (+ safety `0.15 / 0.20 / 0.60`). These are exactly the "absolute calibrated constants" our own
  convention forbids.
- **Propensities are logged per row** (offer `p = 0.7`, Thompson propensities) → causal overlap is
  guaranteed (every card has ≥0.3 control mass). OPE machinery (`_worst_gain`) exists but is
  production-dead (audit M4).
- **Cold-start is the binding constraint.** On the finished seed_101 run, the retirement replay
  showed 14/52 cards blocked purely by `min_treated=2` and 34/52 unjudgeable — the writer mints
  cards faster than Thompson gathers 2 deliveries each. A card with 0–1 observations is an
  undifferentiated cold arm today.

---

## 2. The core change — embedding-informed card prior (item 2)

Replace the independent zero-mean prior on `u_a` with a **hierarchical embedding-linear** prior:

```
 u_a  =  B · φ(e_a)  +  ε_a ,     ε_a ~ N(0, τ² I)
```

- `e_a` = card's 768-d arctic-embed vector; `φ(·)` = a **frozen** dimensionality reduction to
  `m` dims (MVP: seeded Johnson–Lindenstrauss random projection, `m = 16`, version-stamped —
  deterministic and replayable, unlike a bank-dependent PCA).
- `B ∈ ℝ^{d×m}` = a **single shared** "embedding → context-dependent usefulness" map, learned from
  all cards jointly.
- `τ` = a **small** per-card residual sd (< 0.25) — cards lean on `B·φ(e_a)` until their own data
  arrives.

**Why this stays fully conjugate (the elegant part):** rather than a non-diagonal GP prior over the
`u_a`, we implement `B` as **extra shared columns** in the design row:
`+ φ(e_a) ⊗ (c/√d)` (an `m·d` block, appended once, *independent of card count*). Then:
- `B` is just more coefficients with their own **diagonal** Gaussian prior → the existing
  `diag(prior_precision)` solver is untouched.
- The literal per-card block keeps a zero prior mean; its *effective* prior mean is `B·φ(e_a)`,
  supplied through the shared block. **No change to the σ-quadrature or the Laplace/ridge solve.**
- A brand-new card (empty residual block) is predicted at `B·φ(e_a)` — transferred evidence, not
  the global mean.

Design-dimension cost: `+ m·d` (e.g. 16·4 = 64) shared dims, constant in `n_cards`. Cheap.

**Plumbing:** freeze the reduced `φ(e_a)` (16 floats) into the `CardSnapshot` / candidate-slate
payload at decision time, version-stamped with the projection id + embedder id. This keeps the fit
**replayable from the serialized payload alone** (our "reconstruct only from the artifact" rule) and
immune to later embedder drift.

---

## 3. Empirical Bayes on the prior scales (item 3)

Once (2) lands there are new knobs (`m`, `τ`, `B`'s prior sd) plus the legacy scales. Rather than
hand-tune (forbidden), **learn them by maximizing the log marginal likelihood we already compute**:

- Optimize `θ = {baseline_sd, shared_sd, τ (card residual), B_sd, σ-prior mean/sd}` over log-scale
  with a gradient-free optimizer (Nelder–Mead), warm-started at today's constants.
- **Guard against overfitting on cold banks** with a hyperprior that pulls `θ` back to the current
  defaults when evidence is thin, and only let EB move once observation count exceeds a
  *self-normalizing* threshold (relative to parameter count, not an absolute N). On a 5-card bank EB
  is a no-op equal to today's behavior.
- Net effect: shrinkage strength (including "how much to trust the embedding map vs per-card
  residual") adapts to the task's realized noise, and the three magic constants disappear.

---

## 4. Calibration diagnostics (item 1) — infrastructure *and* gate

A new offline harness over the replayable ledgers (`gigaevo/memory_v2/…` analysis tool, read-only):

- **Reliability / coverage:** does the p% predictive interval on gain cover p% of held-out
  randomized *controls*? Predictive NLL, PIT histogram.
- **Cold-start leave-one-card-out:** hide a card's observations, predict its first-k deliveries from
  the prior; compare embedding prior vs zero-mean prior. **This is the falsification test for (2).**
- **Slice by embedding neighborhood:** flag semantic regions where the model is miscalibrated (e.g.
  a cluster where similarity ⊥ effect).

It is not a live-path change — its consumer is *us*, deciding whether (2)+(3) ship.

---

## 5. Doubly-robust off-policy evaluation (item 4)

Replace the dead `_worst_gain` with a proper DR estimator (Dudík 2011; DRos shrinkage, Su 2020):

```
 V_DR(π) = mean_rows [ Σ_a π(a|x)·r̂(a,x)  +  (π(a*|x) / p_log(a*|x))·(r − r̂(a*,x)) ]
```

- **Direct method** `r̂` = the reward head — so **(2)+(3) improving `r̂` tightens DR's variance**
  (better control variate).
- **Importance weights** use the logged offer/Thompson propensities; clip/shrink (DRos) and report
  effective sample size. Forced `p = 0.7` exploration keeps weights well-conditioned.
- **What it buys:** offline estimates of counterfactual policies — offer-probability, abstain
  threshold, and **embedding-prior on vs off** — from logged rows, *without* a fresh live A/B. This
  is the direct answer to the n=3 / LLM-non-determinism power problem: squeeze the policy comparison
  out of the data we already have.

---

## 6. What actually changes (file/behavior by behavior)

| Area | Change | Live-loop impact |
|---|---|---|
| `features.py` `FeatureConfig`/`FeatureSpace` | new `embedding_prior` flag, `m`, projection id; new shared `φ⊗c` block + dims/indices | design gains `m·d` cols; card block prior mean effectively `B·φ` |
| `CardSnapshot` / candidate slate payload | freeze reduced `φ(e_a)` (16 floats) + embedder/projection version | replayable; no fit-time recompute needed |
| candidate source (`candidates.py`) | attach `φ(e_a)` from `VectorIndex`/embedder when building the slate | one extra lookup per decision |
| `posterior.py` prior assembly | card residual sd `0.25 → τ`; new `B_sd` block; **solver unchanged** | cold cards ranked via transferred evidence |
| `posterior.py` hyperparams | optional EB optimizer over marginal likelihood + cold-bank hyperprior guard | shrinkage adapts; legacy constants removed |
| **new** calibration module | reliability/coverage/LOCO/neighborhood, offline | none (analysis) |
| **new** OPE module | DR/DRos over logged propensities, offline | none (analysis) |
| config seams | `memory.posterior.embedding_prior: none\|linear`; `hyperparameter_estimation: fixed\|empirical_bayes` | `none`+`fixed` = **byte-identical control** |

Everything ships **behind seams** with the current behavior as the byte-identical `none`/`fixed`
control (the excluder `none`/`lineage` pattern). Calibration + OPE are additive read-only tools.

---

## 7. Causal chain (signal → behaviour → metric)

- **Signal:** card embedding `φ(e_a)` — already computed for retrieval, currently unseen by the
  Bayesian head.
- **Behaviour:** the reward head's per-card effect prior mean becomes `B·φ(e_a)` (2), with shrinkage
  strength set by marginal likelihood (3); the improved reward model sharpens DR-OPE (4);
  calibration (1) audits the posterior.
- **Metric (primary, offline):** leave-one-card-out predictive NLL + interval coverage on held-out
  controls — embedding+EB vs current. If it does **not** beat the zero-mean prior on held-out cards,
  **STOP** (see §8).
- **Metric (secondary, offline):** DR-OPE policy value, embedding-on vs off, on logged rows.
- **Metric (cold-tail):** fraction of bank clearing retirement `min_treated`/viability gates (today
  34/52 unjudgeable) — should rise as cold cards gain informed posteriors.
- **Metric (confirmatory, online, underpowered):** fitness A/B, two tasks (heilbron + circle).

## 8. Riskiest link + falsification gate (must pass before any live change)

**Riskiest assumption:** semantic similarity predicts *effect* similarity. Counter-case: two cards
with near-identical text where one has a subtle bug → embedding says "same," gains say "opposite."
If similarity ⊥ effect, `B` explains ~0 variance and only adds bias.

**Gate (Phase 0, offline, on existing ledgers — seed_101 + 202/303 + pre-fix runs):** fit `B` and
measure **out-of-sample** (leave-one-card-out) predictive improvement and marginal-likelihood gain
vs the zero-mean prior. **GO only if embedding beats the baseline prior on held-out cards.** This
costs nothing live and kills the idea cheaply if the premise is false.

## 9. Output-consumption (the decision each item changes)

- **(2)** → a fresh card is *ranked and offered on its first appearance* using transferred evidence,
  not as an undifferentiated cold arm → changes Thompson selection, abstain probability, and
  retirement viability.
- **(3)** → shrinkage adapts → fewer over/under-confident effect estimates → same decisions, better
  calibrated; removes hand-tuned constants.
- **(1)** → consumed by *us*: ship / don't-ship gate + ongoing misspecification monitor.
- **(4)** → consumed by *us/config*: pick offer-prob, abstain threshold, embedding-on **offline**,
  replacing underpowered live A/Bs.

---

## 10. Phasing

- **Phase 0 — GATE (offline, no live change):** build calibration (1) + DR-OPE (4); fit embedding
  map on existing ledgers; run LOCO falsification (§8). Deliverable: report answering "does
  embedding predict effect?" + "what does DR say about current vs candidate policies?" **GO/NO-GO.**
- **Phase 1:** embedding-informed prior (2) behind `embedding_prior: linear`; freeze `φ` in payload;
  keep `none` byte-identical. Unit + replay tests.
- **Phase 2:** empirical Bayes (3) behind `hyperparameter_estimation: empirical_bayes` with cold-bank
  guard; retire the three magic constants.
- **Phase 3:** live A/B (embedding+EB vs current) on heilbron + circle; DR-OPE cross-check;
  calibration as a run-time monitor.

## 11. Non-goals / deferred

- Full RBF-GP / non-diagonal kernel prior over `u_a` (Phase-4 "if linear underfits" — breaks the
  diagonal solver).
- Learned deep representation (neural-linear with a trained encoder) — the frozen embedding is the
  MVP; learn the encoder only if the frozen map plateaus.
- DPP/submodular diversity over embeddings for multi-card slates (adjacent; separate plan).
- Feeding embeddings into the RAG applicability contrast (the research agent already does semantic
  work; avoid double-counting).

## 12. Constants avoided

`m`, `τ`, `B_sd`, and the legacy `0.75/0.35/0.25` are all set by empirical Bayes (3), not hardcoded;
the frozen projection is seeded by a version constant (documented, not tuned); the EB "enough data"
threshold is self-normalized to parameter count, not an absolute N.
