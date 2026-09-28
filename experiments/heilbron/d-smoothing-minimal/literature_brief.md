# Literature Scout Brief: D-Only Fitness Smoothing (Minimal REDESIGN)

**Experiment**: `heilbron/d-smoothing-minimal`
**Date**: 2026-04-24
**Research question**: Does replacing the D-side hard-floor scoring
(`delta = max(raw_delta, 0.0)` at `problems/heilbron_repro_v1/pop_b/evaluate.py:98-99`)
with a smooth tanh-based variant lift mu_G out of the NULL band established by
`heilbron/adversarial-repro-v2` (mu_G=0.03315, 4 G runs)?

**Scope note**: This brief covers only the fitness-smoothing delta relative to
`experiments/heilbron/adversarial-repro-v2/literature_brief.md`, which contains the
full Heilbronn benchmark survey and adversarial co-evolution background. Sections
duplicated in the v2 brief are not reproduced here; instead they are cited with the
relevant claim flagged.

---

## Related External Work

| Paper/System | Year | Mechanism | Result | Relevance to Proposal |
|---|---|---|---|---|
| Ficici & Pollack, "Challenges in Coevolutionary Learning" (GECCO 1998 / Adaptive Behavior) | 1998–2004 | Continuous engagement metric vs binary win/loss in co-evolution; mediocre stable-state pathology | Binary fitness yields equilibria at poor-quality strategies; continuous metric preserves search gradient throughout evolution | Foundation for the D hard-floor pathology. The proposed tanh is one instance of "engagement-preserving objective." Already cited in v2 brief. |
| Ficici & Pollack, "A Game-Theoretic Memory Mechanism for Coevolution" (GECCO 2003) | 2003 | Nash memory to prevent forgetting; game-theoretic analysis of coevolutionary memory | Monotone improvement toward Nash quality with the correct memory; pure Hall-of-Fame is weaker | Supports the deterministic HoF component of adversarial_015; less directly relevant to d-smoothing-minimal which strips HoF changes out. The binary-to-continuous fitness argument is made in the companion paper. |
| Arjovsky, Chintala & Bottou, WGAN (ICML 2017); Gulrajani et al., WGAN-GP (NeurIPS 2017) | 2017 | Wasserstein loss (continuous critic) vs JS divergence (saturating binary) for GAN training | Continuous critic eliminates mode collapse and vanishing gradient; K=5 D updates stabilize training | Closest GAN analogue. `tanh(delta/Q_MAX)` is the evolutionary equivalent of the Wasserstein critic: continuous, signed, zero-sum. Already cited in v2 brief; no new claims needed here beyond confirming the analogy holds even for a minimal D-only change. |
| Lehre & Lin, "Overcoming Binary Adversarial Optimisation with Competitive Coevolution" (PPSN 2024, arXiv:2407.17875) | 2024 | First rigorous runtime analysis of (1,lambda)-CoEA on binary test-based adversarial problems; introduces the Diagonal benchmark | Binary fitness causes disengagement (pathological CoEA failure mode); polynomial runtime recoverable only under specific offspring size / mutation rate constraints | **New since v2 brief.** Directly formalizes the claim that binary adversarial fitness degrades CoEA runtime. The GigaEvo D hard-floor is a real-valued analog of the binary test-based setting analyzed here. Non-binary smoothing is the natural fix — this paper provides rigorous grounding for what was previously heuristic motivation. |
| Liapis, Yannakakis & Togelius, "Generational Adversarial MAP-Elites" (ISAL 2025, arXiv:2505.06617) | 2025 | Coevolutionary QD: alternating-generation MAP-Elites on both populations; fitness defined by wins in the adversarial game | Arms-race-like dynamics observed; generational extinction increases open-endedness; neutral mutations preserved as stepping stones | **New since v2 brief.** The GAME paper is the closest published system to GigaEvo's setup (adversarial MAP-Elites with both sides evolving). It does NOT report a hard-floor pathology because it uses multi-agent game scores (continuous win rates), not binary improvement flags. The absence of the hard-floor problem in GAME, combined with its functional arms race, is positive indirect evidence that continuous scoring enables the dynamics GigaEvo is seeking. |
| Rosin & Belew, "New Methods for Competitive Coevolution" (Evolutionary Computation 1997) | 1997 | Hall of Fame for cycling prevention; best-response training vs random opponents | Deterministic HoF prevents intransitive cycling and forgetting | Cited in REDESIGN.md. Not directly about smoothing but supports the HoF component that adversarial_015 (full REDESIGN) includes. d-smoothing-minimal explicitly excludes HoF changes, so this citation is advisory only. |
| Banzhaf et al., "Competitive Coevolution through Evolutionary Complexification" (JAIR 2004) | 2004 | NEAT applied to competitive coevolution | Structured complexity growth helps escape local optima under binary fitness | Background on binary-fitness stagnation being a known class of failure across multiple competitive coevolution domains. Not specific to MAP-Elites. |

---

## Baselines on This Task

*(From v2 brief and subsequent experiments. No new external baselines discovered.)*

| System | Metric | Value | Notes |
|---|---|---|---|
| heilbron/baseline-repro (N=4, PR #201) | actual_fitness mean | 0.03449 (SD=0.00212) | Canonical adversarial baseline. Q_MAX=0.0365 by definition. |
| heilbron/adversarial-repro-v1 (N=4, PR #211) | mu_G | 0.03413 [0.0306, 0.0377] 95% CI | Bug-fixed v1 library. SBF-Lineage OFF, SOFTMAX OFF. |
| heilbron/adversarial-repro-v2 (N=4, PR #216) | mu_G | 0.03315 [0.03001, 0.03630] 95% CI | Strongest NULL result. SBF-Lineage + SOFTMAX + I-16/I-17 fixes. C1_G=0.03650 outlier; other 3 runs averaged 0.03203. **This is the NULL band that d-smoothing-minimal must beat.** |
| heilbron/asymmetric-iterations v1 (PR #204) | actual_fitness best | 0.03650 (C2_G, gen 5) | SOTA-level. Accidental loose coupling (min_delta=1). |
| AlphaEvolve (DeepMind 2025) | Heilbronn n=11 min_area | > 0.0365 | External SOTA ceiling. Non-adversarial. |

**NULL band definition**: mu_G must exceed 0.03449 (baseline-repro mean) to be considered a positive result. The v2 result (0.03315) is 0.63 SD below that baseline.

---

## Prior GigaEvo Experiments

| Experiment | Result | Key Learning | How It Informs This Design |
|---|---|---|---|
| heilbron/k5-budget-loose (PR #207, INVALID) | INVALID — stopped at gen 1-2 for structural D fitness flaw | D hard-floor produces 60-90% point mass at fitness=0.0 exactly across all 4 D runs. Strategy rejection 56-79% on D vs 0-14% on G. Root cause confirmed: `max(raw_delta, 0.0)` with K=1 creates a binary {win, lose=0} landscape. | Empirical measurement that directly motivates this experiment. The tanh fix is Change 1 from REDESIGN.md. Point mass should collapse to near-zero when tanh is applied. |
| heilbron/adversarial-repro-v2 (PR #216, NULL) | NULL — mu_G=0.03315 despite SBF-Lineage + SOFTMAX + all KF fixes | All information-flow treatments exhausted under broken D fitness. D fitness 0.000 in 2/4 D runs despite SBF-Lineage. G outlier (C1_G=0.03650) stochastic. Strengthens conclusion that the binding constraint is D fitness signal, not information quality. | Establishes the v2 structure that d-smoothing-minimal inherits (SBF-Lineage + SOFTMAX + archive_reeval asymmetric + refresh_passes=2 + drift_cap=100000). The ONLY change vs v2 is the D evaluate.py. |
| heilbron/adversarial-repro-v1 (PR #211, NULL) | NULL — mu_G=0.03413; A1_G reached 0.0365 at gen=5 during I-16-broken phase | Early stochastic peak at gen 5 did not persist. D collapse present throughout. Redis flush protocol bug (KF-12) identified. | Confirms the 0.0365 outlier is reproducible stochastically but not systematically. D smoothing is the missing structural condition. |
| heilbron/k5-budget-v3 (INCONCLUSIVE) | INCONCLUSIVE — 2D MAP-Elites BD eliminated D collapse (all D > 0.50) but G mean 3.3% below v2 baseline | 2D BD workaround prevents point-mass collapse without fixing the underlying formula. Diversity cost is observable. K3_1 deadlocked at gen 29. | Shows that structural D collapse CAN be broken by BD workaround, but at a fitness cost. Direct smoothing is a cleaner intervention: breaks the point mass without adding a diversity tax. |

---

## Novelty Assessment

- [ ] This exact mechanism has been tested before (cite)
- [ ] A similar mechanism (2D BD workaround) was tested with different results — 2D BD eliminated D collapse but imposed a diversity cost (k5-budget-v3). Smoothing is the direct fix; BD workaround is an orthogonal structural change.
- [x] The specific combination of tanh D-fitness smoothing ON a v2-exact baseline (SBF-Lineage + SOFTMAX + asymmetric archive_reeval, inheriting G-smoothing from PR #219) has NOT been run. All prior heilbron-adversarial experiments ran on broken D fitness. The G-smoothing hotfix (commit 2de8267e, 2026-04-24) means even the "current main" state has never been tested in a full adversarial run. d-smoothing-minimal is therefore the FIRST experiment where both G and D sides have continuous fitness signals.

**Relationship to adversarial_015 (full REDESIGN bundle)**: adversarial_015 stacks D-smoothing + deterministic HoF + K=L=3 + archive_reeval + cache_on edges on top of a fresh factorial design. d-smoothing-minimal isolates only the D-smoothing component by keeping every other v2 parameter identical. If d-smoothing-minimal succeeds, adversarial_015's auxiliary components (HoF, K=L=3, cache_on) may be assessed as follow-on. If it fails, the full bundle's additional components are implicated.

**Relationship to adversarial_019 (IDEAS.yaml)**: This experiment IS adversarial_019 in scope: "apply only pop_b/evaluate.py fitness-smoothing edit, inherit pipeline + feedback mode from adversarial-repro-v2, single arm, N=4." The naming `d-smoothing-minimal` aligns with adversarial_019 exactly. No conceptual novelty beyond what adversarial_019 already pre-specified.

**Relationship to adversarial_021 (IDEAS.yaml)**: adversarial_021 is a 3-arm decomposition (neither smoothed / G-only / both). d-smoothing-minimal covers adversarial_021's Arm C ("main + D smoothing = both smoothed") as a standalone experiment. If d-smoothing-minimal is positive, adversarial_021 Arm A (rollback) would add retrospective attribution value but is not required to establish the practical positive result.

---

## Recommendations for Elena

### On the functional form of D fitness smoothing

Three candidate forms are available. The REDESIGN.md commitment is to tanh. The analysis below shows this is well-motivated:

| Form | Formula (raw score per opponent) | Range | Gradient at delta=0 | Point-mass elimination |
|---|---|---|---|---|
| Current hard-floor | `max(delta, 0) / Q_MAX` clamped to [0,1] | [0, 1] | One-sided (zero for delta<0) | No |
| Linear clip (signed) | `max(-1, min(delta / Q_MAX, 1))` | [-1, 1] | Constant = 1/Q_MAX | Yes |
| tanh | `tanh(delta / Q_MAX)` | (-1, 1) | 1/Q_MAX at delta=0; saturates smoothly at extremes | Yes |
| sigmoid offset | `1 / (1 + exp(-k * delta / Q_MAX)) - 0.5` | ~(-0.5, 0.5) | k/(4*Q_MAX) at delta=0 | Yes |

The MAP-Elites bounds requirement (fitness in [0, 1]) means any signed output needs the affine rescale `(score + 1) / 2`. All three non-hard-floor forms are mathematically equivalent in terms of gradient-sign correctness and point-mass elimination. The tanh form is preferred because:

1. It matches the REDESIGN.md spec (Change 1) so the implementation is pre-reviewed.
2. `tanh(1) ≈ 0.762` for delta=Q_MAX — the gradient region is well-centered around the operationally relevant range (programs near G's current Q_MAX value).
3. The WGAN-GP analogy (continuous critic with Lipschitz constraint) maps cleanly to tanh's bounded, smooth, zero-symmetric form.
4. Q_MAX retuning is NOT needed — the existing Q_MAX=0.0365 ensures the gradient knee sits at approximately the current G population quality level, which is intentional (see REDESIGN.md Q_MAX decision, 2026-04-16).

The linear-clip alternative would also work and is simpler to reason about. If there is any implementation doubt about tanh behavior, the linear signed-clip is a valid fallback with identical theoretical properties at the operating point.

**Explicitly do NOT use** sigmoid centered at `1 / (1 + exp(...))` without the offset subtraction — the uncentered sigmoid maps all negative deltas to (0, 0.5) rather than (-0.5, 0), which still suppresses gradient below delta=0 (less severely than hard-floor, but not eliminated).

### On the G-side interaction

The G-side already uses `resistance_score = 1.0 - min(delta / Q_MAX, 1.0)` (PR #219, commit 2de8267e, deployed on main). This is NOT tanh — it is the linear complement of the hard-floor. The D-side is switching to tanh. The two sides will have different functional forms:

- G resistance: `1 - clip(delta / Q_MAX, 0, 1)` — continuous but with a zero-slope floor at delta >= Q_MAX
- D fitness: `(tanh(delta / Q_MAX) + 1) / 2` — smooth everywhere, non-zero gradient even at large deltas

This asymmetry is acceptable given that d-smoothing-minimal is testing D-smoothing IN ISOLATION. The downstream aggregator (ConfigurableAggregator via heilbron_constructor.yaml and heilbron_improver.yaml) computes program-level fitness from per-opponent scores independently for each population, so mixing functional forms is architecturally clean.

If adversarial_021 is later run and discovers that G's linear-clip form is a binding constraint (i.e., symmetrizing to tanh on both sides matters), that is a follow-on ablation, not a prerequisite.

### On Q_MAX

Keep at Q_MAX=0.0365. Three reasons:
1. Decision locked in REDESIGN.md 2026-04-16.
2. Changing Q_MAX is a free DoF that confounds the experiment — any result could be attributed to retuning.
3. The gradient properties of tanh at Q_MAX=0.0365 are favorable: `tanh'(0) = 1/Q_MAX ≈ 27.4` normalized gradient, putting programs at the current G population fitness (0.033-0.035) in the linear regime of tanh, with saturation only at much higher deltas.

### On v2 structural inheritance

d-smoothing-minimal must inherit ALL of v2's configuration unchanged:
- SBF-Lineage on D: keep (adversarial_019 spec).
- SOFTMAX opponent sampling on G: keep.
- `archive_reeval: asymmetric` (D has `archive_reeval=false`, G has `archive_reeval=true` with `refresh_passes=2`): keep.
- `drift_cap=100000` (loose coupling): keep (same as v2 which used this).
- K=1, L=1: keep. Do NOT change to K=L=3 — that is the adversarial_015 full-bundle change.
- Feedback mode: keep COMPOSITION (same as v2 control arm). Do not reintroduce the feedback factorial — feedback mode was confirmed NULL at HIGH confidence (PATTERNS.md).

The only change is `problems/heilbron_repro_v1/pop_b/evaluate.py` lines 98-99.

### Primary success criterion

D fitness distribution at gen 5: fraction of D archive programs with fitness exactly 0.000 should be less than 10% (vs. 60-90% in all v2 runs). This is the mechanistic check — it confirms the point mass is broken.

Secondary criterion: mu_G >= 0.03449 (baseline-repro mean) by gen 50 across N=4 G runs.

Tertiary: any single G run reaching >= 0.03650 (SOTA) is worth reporting as a signal but should not be the pre-registered primary endpoint (see v2 brief section "Is it just stochastic resampling?" for the Bernoulli(2/8) argument).

### On the aggregator contract

The frozen evaluate.py (`problems/heilbron_repro_v1/pop_b/evaluate.py`) must return `(metrics, artifact)` with `artifact["per_opp_metrics"]` and `artifact["per_opp_delta"]` populated — not a bare dict (KF-10). The current v2 version already satisfies this contract (fixed in repro-v1, PR #211). Confirm the d-smoothing change does NOT break the return type by inspecting the artifact construction after the score formula change. The `delta` field stored in per_opp_metrics should store `raw_delta` (before affine rescale), not the score, so the artifact remains interpretable for downstream diagnostics. Check the REDESIGN.md spec:

> `per_opp_metrics[idx] = {"pre_q": float(pre_q), "post_q": float(post_q), "delta": float(raw_delta), "score": float(score), "is_valid": 1.0}`

The `delta` field should be `raw_delta` (i.e., `post_q - pre_q`, signed), not the clamped-to-zero version. This is a behavior change vs. the current code (which stores `max(raw_delta, 0.0)`). It should be pre-registered as part of the artifact contract, as it affects any downstream CIAO or pairwise analysis that uses per_opp_delta.

### On the SOFTMAX + D-collapse interaction (confound warning)

adversarial-repro-v2 observed G invalidity 35-47% vs v1's 24-45% under TOP_K. SOFTMAX opponent sampling may degrade LLM mutation quality when D is collapsed (PATTERNS.md suggestive signal). Under d-smoothing-minimal, D will no longer be collapsed, so the SOFTMAX confound may be LIFTED — i.e., SOFTMAX may perform better under healthy D than it did in v2. This is not a controlled comparison (d-smoothing-minimal does not have a SOFTMAX OFF arm), but Elena should monitor G invalidity as a secondary diagnostic to flag whether the invalidity rate returns to v1-level (24-45%) when D is healthy. A large drop in G invalidity would support the "SOFTMAX hurt when D was broken" hypothesis.

---

## Summary Table: What Is and Is Not Tested

| Component | Status in d-smoothing-minimal | Adversarial_015 (full REDESIGN) |
|---|---|---|
| D-side tanh fitness smoothing | YES — the sole IV | YES |
| G-side linear-clip smoothing | Already deployed (PR #219 on main) | Already deployed |
| Deterministic top-K HoF | NO — stochastic SOFTMAX retained | YES |
| K=L=3 opponent context | NO — K=L=1 retained | YES |
| cache_on edges (CacheOnlyInput) | NO — not wired | YES |
| SBF-Lineage on D | YES — inherited from v2 | YES (as factor) |
| archive_reeval asymmetric | YES — inherited from v2 | YES (modified) |
| drift_cap=100000 (loose coupling) | YES — inherited from v2 | TBD |
| Feedback mode axis | NO — COMPOSITION only (NULL confirmed) | YES (as calibration factor) |
| N=4 G runs | YES | YES |

**This experiment answers**: Is D-smoothing alone sufficient to break D collapse and lift mu_G to baseline parity, holding all v2 parameters fixed?

**This experiment cannot answer**: Does the HoF change matter independently? Does K=L=3 matter? Do the cache_on edges matter? Those require adversarial_015.
