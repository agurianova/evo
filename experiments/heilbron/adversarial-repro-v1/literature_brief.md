# Literature Scout Brief: Reproducibility Stress Test of v1's 0.0365 Result Under Current Library

**Experiment**: heilbron/adversarial-repro-v1
**Date**: 2026-04-19
**Research question**: Does replicating v1's hyperparameters + fitness function + drift-cap-no-op (preserving the natural D>G ~2.2x compute asymmetry) under the current library reproduce the 0.0365 result — or does the absence of v1's process-death bugs change the outcome by letting runs reach gen 50?

---

## Related External Work

| Paper/System | Year | Mechanism | Result | Relevance to Proposal |
|---|---|---|---|---|
| AlphaEvolve (DeepMind) | 2025 | LLM-guided evolutionary coding agent (Gemini ensemble), island-based MAP-Elites | Heilbronn n=11 min_area > 0.0365 (exact value undisclosed; improves prior 0.036 SOTA) | Defines the external SOTA ceiling GigaEvo must beat. AlphaEvolve uses no adversarial co-evolution — solo evolutionary search suffices for improvements. |
| FlowBoost (Hashemi et al., arXiv 2601.18005) | 2026 | Flow-matching generative model + RL reward guidance + stochastic local search | Heilbronn improvements approaching best known, with 100–1000x less compute than AlphaEvolve | FlowBoost is non-adversarial and non-LLM — outperforms AlphaEvolve on Heilbronn at fraction of cost. Raises the external bar and further weakens the "adversarial complexity is justified" argument. |
| Solving Heilbronn via Global Optimization (arXiv 2512.14505) | 2025 | MIQCP/QCP formulations, global optimizer | Certified optimal for n≤8; n=9 certified in 1 day | For n=11, no certified optimum. The 0.0365 GigaEvo target is a numerical best-known, not a proven optimum. Important for framing claims. |
| Exact Coordinates via Mixed-Integer (arXiv 2603.11107) | 2026 | Mixed-integer optimization on unit square | Exact coordinates for small n | Confirms the n=11 problem remains open; numerical heuristics (including GigaEvo's) are still scientifically relevant. |
| GigaEvo OSS paper (arXiv 2511.17592) | 2025 | MAP-Elites + LLM mutation, tested on Heilbronn | Reproduces/approaches AlphaEvolve numbers on Heilbronn | GigaEvo framework paper describes the same system. Confirms Heilbronn as a legitimate benchmark for the framework. |
| PSRO Survey (Muller et al., arXiv 2403.02227) | 2024 | Policy Space Response Oracles — iterated best-response with population of opponents | Standard framework for competitive coevolution; HoF-K is implicit | The REDESIGN.md bundle's deterministic top-K HoF is a single-population PSRO step. Relevant to future experiments, less so for the v1 repro which uses v1's stochastic opponents. |
| Ficici & Pollack (GECCO 2003) | 2003 | Game-theoretic memory for coevolution; engagement metrics; binary fitness pathology identified | Binary win/loss fitness yields mediocre stable states; continuous engagement metric preserves search gradient | Theoretical foundation for why v1's hard-floor fitness (binary {win=positive, lose=0.0}) is expected to cause D collapse. v1 got lucky on G despite this flaw. |
| Evolutionary and Coevolutionary Multi-Agent Design (MIT, GECCO 2025) | 2025 | Survey of coevolutionary dynamics including arms-race vs. mediocre-stable-state transitions | Conditions for arms-race vs. stagnation not well understood; self-play single-model designs fail | Contextualizes GigaEvo's D stagnation as a known class of failure; GECCO 2025 tutorial on coevolution for adversarial deep learning directly maps to GigaEvo's setup. |
| WGAN-GP (Gulrajani et al., NeurIPS 2017) | 2017 | n_critic=5 D:G update ratio; continuous Wasserstein loss instead of binary JS | Continuous loss prevents vanishing gradient; K=5 ratio stabilizes GAN training | Motivates both (a) the K=1 silent collapse in v1 as a degenerate WGAN configuration and (b) the hard-floor vs. smoothed fitness distinction. The D hard-floor is the GigaEvo analog of JS divergence saturation. |

---

## Baselines on This Task

| System | Metric | Value | Notes |
|---|---|---|---|
| AlphaEvolve (DeepMind 2025) | Heilbronn n=11 min_area | > 0.0365 | Exact value not published; described as improvement over 0.036 SOTA in AlphaEvolve paper |
| GigaEvo heilbron/asymmetric-iterations (v1, 2026) | actual_fitness | 0.03650 (C2_G, gen 5) / 0.03648 (A1_G, gen 8) | ONLY deliberate clean positive. K=1 (not K=5), loose coupling (min_delta=1 accidental). Runs died gen 8-12. |
| GigaEvo heilbron/baseline-repro (2026) | actual_fitness mean | 0.03449 (N=4, SD=0.00212) | Canonical adversarial baseline. Q_MAX=0.0365 by definition. |
| GigaEvo heilbron/asymmetric-iterations-v2 (2026) | actual_fitness best | 0.03588 (C1_G, gen 22) | Only replication attempt of v1. Used tight coupling (min_delta=8). NULL vs baseline. |
| GigaEvo heilbron/k5-budget-v3 (2026) | actual_fitness best | 0.03580 (K3_1_G, gen 24, truncated at gen 29) | K=3 vs K=5 comparison, INCONCLUSIVE. K3_1 deadlocked. |
| FlowBoost (2026) | Heilbronn min_area | Approaches best known | Non-adversarial flow model; 100-1000x less compute than AlphaEvolve |

---

## Prior GigaEvo Experiments

| Experiment | Result | Key Learning | How It Informs This Design |
|---|---|---|---|
| heilbron/asymmetric-iterations (v1, PR #204, commit 04bd5e69) | POSITIVE (accidental) — 2/8 runs at ≥105% SOTA (0.03648, 0.03650) | K=5 silently became K=1. min_delta=1 created loose coupling. Runs died gen 8-12 due to 6 bugs (KF-01 through KF-06). Best found gen 4-8 on G. D ran 17-29 gens vs G's 8-12. | **The run being replicated.** The repro must freeze v1 fitness files AND set drift_cap=100,000 (no-op) to restore min_delta=1 semantics without reintroducing KF-01 through KF-06. K=1 is v1's actual operating point. |
| heilbron/asymmetric-iterations-v2 (PR #206) | INCONCLUSIVE — best 0.03588 (104% baseline), NULL arm means | Bug fixes (especially min_delta=1→8) changed tight coupling dynamics. Ran 4-6x more gens than v1 but found lower peaks. Cross-arm delta 0.00066 (NULL). | **The failed replication.** v2 differed from v1 in exactly one unexpected way: min_delta=8 (tight coupling). The repro-v1 experiment isolates whether min_delta=1 alone recovers v1's result by using drift_cap=100,000 to restore loose coupling under the fixed library. |
| heilbron/k5-budget-loose (PR #207, INVALID) | INVALID — D fitness flaw discovered empirically | D hard-floor: 60-90% of D programs at fitness=0.0. This is a structural defect, not a search-space problem. All 10 prior experiments ran on this broken landscape. | Confirms the v1 result was obtained *despite* the D fitness flaw on the G side (G's quality term carries 50% of fitness). The repro-v1 preserves this flaw deliberately. |
| heilbron/k5-budget-v3 | INCONCLUSIVE — K=3 vs K=5 effect −0.00164 [−0.00393, +0.00065] | ProgressBasedSyncHook deadlock at gen 29 (KF-07). 2D BD eliminated D collapse (all D > 0.50). N=2 underpowered. Grand mean 3.3% below v2 baseline. | If KF-07 is not guarded in repro-v1, the same deadlock risk exists. repro-v1 uses drift_cap=100,000 (no-op) which makes the ahead-side never block — so deadlock is structurally impossible under the new ProgressBasedSyncHook semantics. |
| heilbron/baseline-repro (PR #201) | SUGGESTIVE — mean 0.03449, SD 0.00212, N=4 | Stable baseline confirmed. Solo MAP-Elites produces 3 near-Q_MAX outliers/16 runs. High per-run variance. | Establishes the comparison denominator. v1's 0.0365 is 0.58 SD above this baseline — within 1-sigma, not guaranteed to reproduce. |
| heilbron/adversarial-vs-solo (PR #203) | INCONCLUSIVE — adversarial 0.03449 vs solo 0.03267 (p=0.365, d=0.70) | Adversarial > solo directionally but underpowered. Solo bimodal (2/4 matched adversarial, 2/4 far below). | repro-v1's design question (does v1 survive with bugs fixed?) is orthogonal to adversarial-vs-solo. But both are confounded by the D fitness flaw — Improver D running on hard-floor contributes little, so the "adversarial" component may be mostly G running on G's own fitness. |

### Why v2 Failed to Reproduce v1

The v2 results document is explicit: "The most parsimonious explanation: v1's min_delta=1 (the 'bug') created loose G/D coupling where D ran many micro-steps per G epoch. The fix to min_delta=8 (= max_mutations_per_generation) enforces strict epoch-level alternation." The 6 other bug fixes (KF-01 through KF-06) are less plausible culprits because:
- KF-04 (MetricsTracker crashes) caused monitoring gaps but not search path changes.
- KF-01 (sync hook deadlock) was the bug that killed all v1 runs before gen 50 — but the best programs were found gen 4-8, so fixing it prolonged runs past the productive window.
- KF-02/03 (config overrides) were not affecting the actual fitness computation or search.
- KF-05 is identical to min_delta — fixing it IS the tight coupling change.
- KF-06 (Telegram) has zero effect on search.

**Conclusion**: The single most likely explanation for v2's failure is min_delta=1→8. The repro-v1 experiment directly tests this hypothesis by restoring min_delta=1 semantics (via drift_cap=100,000) under the fixed library.

---

## Novelty Assessment

- [x] The exact mechanism has been tested under v1 conditions (v1 itself), but v1's results were confounded by 6 bugs causing early death. No experiment has tested v1's hyperparameters under a bug-free library.
- [x] A similar mechanism was tested in v2 with a DIFFERENT outcome (INCONCLUSIVE, NULL vs baseline). The repro-v1 isolates the min_delta confound.
- [x] This is a novel framing: a "reproducibility stress test" that asks whether a single lucky result survives full exposure (gen 50) under controlled conditions. This is distinct from a vanilla re-run because it specifically freezes problem files at v1's commit, uses drift_cap=100,000 as a v1 emulator, and pre-specifies which residual gaps (library drift, longer runs, same model) could each explain non-reproduction.

**Contribution if it reproduces**: Confirms that v1's loose coupling (min_delta=1 via drift_cap=100,000) is the active mechanism, and that the 0.0365 result is robust to running the full 50 gens (i.e., the early-death bug was not a necessary condition). Converts the accidental result into a deliberate one. Provides the only clean causal story for why the prior chain of improvements works: loose coupling = implicit D compute advantage, not source code access or feedback mode.

**Contribution if it does not reproduce**: The failure can be localized across three residual gaps:
1. Library drift (pipeline, injection hooks, engine changes since 04bd5e69) — if the result is substantially below v1's even at gen 8, the library drift is suspect.
2. Runs reach gen 50 instead of dying gen 8-12 — if the result exceeds gen-8 v1 values early then regresses, the longer run past the productive window is the culprit (D-collapse pathology wins after G peaks early).
3. Same model family but proxy defaults may differ — check if LLM token budget / temperature matches v1 exactly.
Non-reproduction under controlled conditions, with one identifiable gap as the explanatory variable, is a publishable negative result that strengthens the case for the REDESIGN bundle.

---

## Recommendations for Elena

### Arm structure

Keep the 2-arm factorial (Composition x Gradient-in-prompt, 2 pairs each = 8 runs). Rationale: feedback mode is definitively NULL across 8 pairs and 2 experiments (PATTERNS.md: HIGH confidence). Including both arms in repro-v1 serves two functions: (a) internal consistency check — if one arm dramatically outperforms the other, something is wrong with the design, not the mechanism; (b) it reuses the v1 arm structure verbatim, which is required for the "exact replication" framing. Collapsing to a single arm would save compute but remove the built-in consistency check and break comparability with v1.

### Stopping rule

The pre-registered stopping rule should be `max_generations=50` (hard stop) with a `max_runtime_hours` cap (recommend 30h, pre-registered). Do NOT use a fitness plateau as a stopping rule because v1's best programs were found gen 4-8 — a plateau rule would terminate before the full-run comparison is observable. The scientific question is whether the trajectory at gen 50 differs from the trajectory at gen 8-12 (which is where v1 terminated). Running to gen 50 is the whole point.

### Drift-cap setting

drift_cap=100,000 is the correct no-op. Under ProgressBasedSyncHook semantics, the ahead side blocks only when `own_progress - min(opponent_progress) > drift_cap`. At drift_cap=100,000, no side ever blocks regardless of progress divergence — D will naturally run ~2.2x faster (observed empirically in v1: G=12 gens, D=27-29 gens). This preserves v1's de facto compute asymmetry without reintroducing the KF-05 bug (min_delta=1 is no longer the control parameter). Verify with `--cfg job` pre-launch.

### KF-07 deadlock risk

KF-07 (ProgressBasedSyncHook deadlock) is structurally impossible at drift_cap=100,000 because the blocking condition `own_progress - min(opponent_progress) > 100,000` can never be true in a 50-gen run. No explicit deadlock guard is needed for this experiment. However, add a note in the design document acknowledging this.

### Primary comparison

Primary: v1's observed results (0.03648/0.03650) as the SOTA target. Secondary: v2 baseline-repro mean (0.03449). Tertiary: v2 asymmetric-iterations-v2 best (0.03588). Report effect at both gen 25 (matching v1's D generation count) and gen 50 (full run). The two-generation-horizon comparison is the key analytical output.

### Metrics to monitor the D-collapse pathology

Monitor at gen 5, 10, 20, 50:
- D fitness distribution: fraction of D archive programs at fitness exactly 0.0 (expect 60-90% at gen 1-2 in all prior runs on hard-floor).
- D strategy-rejection rate: rolling 10-gen window (expect 56-79% historically).
- G actual_fitness: should peak early (gen 4-8) based on v1 trajectory. If G continues improving past gen 10, v1's early-death was masking additional gains.
- Generation gap between G and D (D should be ~2-2.5x ahead of G at all times under drift_cap=100,000).

The D-collapse pathology check is: does D's fitness point mass prevent meaningful improvement pressure on G? Since the repro uses v1's hard-floor fitness, the answer is expected to be "yes, D collapses." The interesting question is whether G still peaks early despite D collapse (as in v1) or whether, given more time, G's early peak erodes under random noise from a collapsed D.

### Problem files

Freeze `problems/heilbron_repro_v1/pop_{a,b}/` at v1 commit 04bd5e69. Do NOT use the main `heilbron_adversarial` problem files — they may have drifted since v1. The evaluate.py at commit 04bd5e69 is the exact hard-floor fitness: `pop_b/evaluate.py:78 = min(max(delta, 0.0) / Q_MAX, 1.0)` and `pop_a/evaluate.py:95 = float(delta <= 0)`. Verify the frozen files reproduce exactly v1's scoring on a test set of known programs.

---

## Risks and Threats to Validity for Volkov

### If v1 reproduces (0.0365 observed again)

**Confirmation bias risk**: The design was calibrated to v1's numbers. drift_cap=100,000 was chosen to match v1's observed D>G 2.2x ratio; the 2-arm factorial matches v1's structure. If v1 reproduces, the causal attribution (loose coupling is the active mechanism) is plausible but not controlled — we are not simultaneously testing tight coupling. Mitigation: pre-register the exact criteria before observing any run data; report against v2 (tight coupling) as the contrast condition using existing v2 data.

**Is it just stochastic resampling?** v1's 2/8 runs hit 0.0365; the other 6 runs ranged from 0.029 to 0.036. A repro design with 8 runs has ~25% expected reproduction rate under i.i.d. Bernoulli(2/8) draws — so seeing at least 1/8 runs hit 0.0365 is probable even if the mechanism has not been confirmed. The key diagnostic is whether the *mean* across runs improves beyond v1's mean (0.03413 for Arm A, 0.03494 for Arm C). If both arms hit 0.0365 more than 2/8 times, that is genuine improvement. If exactly 2/8 again, it is consistent with stochastic resampling from the same distribution.

**External validity**: The Heilbronn problem n=11 is not at GigaEvo's SOTA frontier anymore. AlphaEvolve reported improvements past 0.0365, and FlowBoost approaches best known values. GigaEvo's 0.0365 would merely match (not beat) an external result that was reported in May 2025. The repro's value is internal (understanding the mechanism) not external (claiming a new record).

### If v1 does not reproduce

**Three-gap problem**: With 3 residual gaps (library drift, longer runs, model proxy), a non-reproducible result cannot be attributed to a single cause without ablation. Mitigation: Design a monitoring protocol that distinguishes early-gen behavior (matching v1's gen 8-12 window) from late-gen behavior (gen 12-50). If the early-gen behavior is the same as v1 but late-gen regresses, the "longer runs expose D-collapse" hypothesis is implicated. If even early-gen behavior is different from v1, library drift or model proxy drift is implicated.

**What causal claims can be made**: Non-reproduction under drift_cap=100,000 AND the same problem files AND same model family narrows the explanation to either (a) library drift in pipeline/hooks since 04bd5e69, or (b) the model proxy defaults differ in a way that changes generation quality (token budget, system prompt, quantization). A diff between the v1 library state (04bd5e69) and current library, focused on `gigaevo/programs/stages/`, `gigaevo/adversarial/`, and `gigaevo/engine/`, would make the library-drift hypothesis falsifiable before or after the run.

**The "2/8 stochastic, hidden third variable" concern**: v1's 2/8 success rate is compatible with both a real mechanism (that repro-v1 should reproduce) and random chance (that repro-v1 need not reproduce). A single instance of 2/8 is insufficient to distinguish. The repro experiment with a different sample of 8 runs has ~75% chance of showing 0 successes at 0.0365 even under the same distribution. Elena should pre-register the analysis on the *distribution* of actual_fitness values (mean and SD), not on whether any run hits 0.0365.

---

## Summary for Elena (10 lines)

1. v1 (asymmetric-iterations, PR #204) is the sole clean positive: 0.03648/0.03650, both arms, gen 4-8, under K=1 (not K=5) and accidental loose coupling (min_delta=1).
2. v2 (asymmetric-iterations-v2, PR #206) failed to reproduce: NULL means, best 0.03588, ran 4-6x more gens. The single most likely culprit is min_delta=1→8 (tight coupling).
3. repro-v1 directly tests the tight-vs-loose coupling hypothesis by restoring min_delta=1 semantics via drift_cap=100,000 under the fixed library (bugs KF-01 through KF-06 gone).
4. The external SOTA has moved past 0.0365: AlphaEvolve (2025) and FlowBoost (2026) both report Heilbronn n=11 improvements without adversarial co-evolution. GigaEvo's 0.0365 is no longer a record — it is a calibration target.
5. The D-collapse pathology (hard-floor fitness, 60-90% point mass at 0.0) will be present in repro-v1 by design. This is expected. Monitor whether G still peaks early despite collapsed D pressure.
6. Keep the 2-arm factorial, set max_generations=50, set max_runtime_hours=30 (pre-registered), monitor D fitness distribution at gen 5/10/20/50.
7. Primary analysis: mean actual_fitness distribution across all 8 runs, not "did at least one run hit 0.0365?" — the latter is likely even under stochastic chance.
8. Freeze problem files at commit 04bd5e69 for pop_a and pop_b. Do not use current heilbron_adversarial problem files.
9. If it reproduces: confirms loose coupling is the active mechanism; converts the accidental result into a deliberate one; enables publication of the causal story.
10. If it does not reproduce: monitor early-gen vs late-gen behavior to localize the culprit across the three residual gaps (library drift, longer runs, proxy defaults). Non-reproduction is still a publishable result with the right pre-registration.
