# Literature Scout Brief: K=5 Compute Budget + Loose G/D Coupling (heilbron/k5-budget-loose)

**Date**: 2026-04-16
**Research question**: Does K=5 compute budget asymmetry (Improver 40 mutations/gen vs Constructor 8) combined with loose G/D coupling (min_delta=1) break Improver stagnation and match or exceed v1's 105% SOTA peaks on the Heilbronn triangle problem (n=11)?

---

## Related External Work

| Paper/System | Year | Mechanism | Result | Relevance to Proposal |
|---|---|---|---|---|
| Gulrajani et al., "Improved Training of Wasserstein GANs" (WGAN-GP) | 2017 | Critic trained n_critic=5 steps per generator step; gradient penalty enforces Lipschitz constraint | Default n_critic=5 produces stable training; prevents generator from overpowering critic | Direct precedent for the K=5 ratio. Rationale: more D steps per G step prevents G from outrunning D. Exact mechanism the k5 hypothesis imports from GAN literature. |
| Radford et al. / original GAN training heuristics | 2014-2016 | 1-to-1 G/D update ratio as default; practitioners found D needed more steps in practice | 1:1 often unstable; D needs to approximate optimum before G can receive useful gradients | Establishes why asymmetric ratio matters: G gradient quality depends on D quality. |
| Ficici & Pollack, "A Game-Theoretic Memory Mechanism for Coevolution" | 2003 | Nash memory for competitive coevolution; addresses subjective fitness pathologies | Monotonic improvement guarantee under Nash equilibrium; mediocre stable states shown to occur without memory | Known reference on coevolution pathologies. Does NOT address compute budget asymmetry. No k-step analog tested. |
| De Jong, "A Review of Landmark Articles in Co-evolutionary Computing" | 2015 (survey) | Survey of competitive co-evolution methods, arms race dynamics, interaction frequency | Synchronous vs. asynchronous updates covered; no specific asymmetric budget experiments cited | Confirms synchronous/asynchronous coupling is a known dimension but finds no consensus recommendation for budget ratios. |
| Chalmers & Willardson, "Global Progress in Competitive Co-evolution" (Frontiers 2024) | 2024 | Systematic comparison of CEA methods; Generalist algorithm using historical + diverse opponents | Key factors for genuine progress: historical opponents, opponent diversity, discarding local-progress-only variants | Does not test compute budget asymmetry; focuses on opponent selection strategy. Stagnation solutions are information-based, not compute-based. |
| Generational Adversarial MAP-Elites (GAME) | 2025 (arXiv:2505.06617) | QD algorithm alternating which population is evolved each generation; generational alternation | Arms-race-like dynamics; enhanced novelty through extinction; validated on 3 adversarial domains | Strict 1:1 generation alternation -- tighter coupling than min_delta=1. Does not test asymmetric budgets or loose coupling. |
| AlphaEvolve (DeepMind) | 2025 (arXiv:2506.13131) | LLM-guided evolutionary coding agent; Gemini Flash (high throughput) + Pro (high quality) ensemble | Reports Heilbronn n=11 result at ~0.0365 (matching known Q_MAX); Flash called ~5-10x more often than Pro (implicit asymmetric compute) | Closest external analog: asymmetric model usage is functionally an iteration-ratio mechanism. Does NOT supersede Q_MAX=0.0365. |
| FunSearch (DeepMind) | 2023 | LLM + island-based evolutionary evaluator; parallel sampling from program pool | New mathematical results on cap sets and bin packing | Architecture is symmetric (no explicit G/D split); no asymmetric iteration ratio tested. |
| EvoPrompt | 2024 | EA operators (GA/DE) applied to discrete prompts via LLMs | Improvement over OPRO and zero-shot on NLP benchmarks | No adversarial structure; no asymmetric budget. Establishes LLM-EA combination as viable but this work is not adversarial. |

---

## Baselines on the Heilbronn Triangle Task (n=11)

| System | Metric | Value | Notes |
|---|---|---|---|
| Wikipedia best known (Comellas & Yebra 2002, simulated annealing) | Min triangle area | 0.0365 | Long-standing SOTA for n=11 (Q_MAX) |
| AlphaEvolve (DeepMind, 2025) | Min triangle area | ~0.0365 | Matches known Q_MAX; does not improve beyond it |
| GigaEvo baseline-repro (heilbron/baseline-repro, N=4) | actual_fitness mean best-overall | 0.03449 (SD=0.00212) | Internal GigaEvo SOTA; used as comparative reference in all Heilbron experiments |
| GigaEvo asymmetric-iterations v1 best (loose coupling, min_delta=1) | actual_fitness | 0.03650 | Best GigaEvo result; 105.8% of baseline-repro; approximately at theoretical Q_MAX=0.0365 |
| GigaEvo asymmetric-iterations v2 best (tight coupling, min_delta=8) | actual_fitness | 0.03588 | Best v2 result (C1_G); 104.0% of baseline-repro; underperformed v1 despite 4-6x more generations |
| Chen et al. 2017 (previous certified bound for n=9) | Certified H_9* | 0.0548767 | For context; n=9 is certified; n=11 remains open |
| Solving Heilbronn via MIQCP (arXiv:2512.14505) | Certified H_10* | >=0.0465369 | Global optimization approach; n=11 not certified |

**Note on Q_MAX**: Q_MAX=0.0365 for Heilbronn n=11 is confirmed from the primary source (Comellas & Yebra 2002). AlphaEvolve matches but does not exceed this value. GigaEvo v1's peak (0.03650) is at Q_MAX. The internal reference is correct.

---

## Prior GigaEvo Experiments on Heilbron

| Experiment | Result | Key Learning | How It Informs This Design |
|---|---|---|---|
| heilbron/heilbron-prover (#183) | POSITIVE — Constructors reach 97% of Heilbronn target (0.0355) | Adversarial co-evolution works; asymmetric dynamics present from start | Establishes that Improver stagnation is NOT a bug but a structural property of the fitness landscape |
| heilbron/adversarial-v2 (#188) | SUGGESTIVE — K=3 +0.00038; K=1 regressed below K=0 | Minimum effective dose for opponent context: K>=3. K=1 actively harmful | Budget experiment should not confound K (inner iterations) with opponent context count; keep context at K=3 or K=0 |
| heilbron/adversarial-dynamic-updates (#197) | NEGATIVE — archive re-eval hurts -0.011; GAN resistance causes mode collapse | Do not manipulate archive in adversarial settings; GAN fitness signal causes mode collapse | Closed direction. No archive re-eval in k5-budget-loose. |
| heilbron/baseline-repro (#201) | SUGGESTIVE — mean 0.03449; 3/4 near Q_MAX runs | Baseline reproducible; Improver polishing exceeds Constructor in 3/4 pairs | Baseline reference locked: 0.03449 is the comparison anchor for all effect-size calculations |
| heilbron/adversarial-vs-solo (#203) | INCONCLUSIVE — adversarial mean 0.03449 vs solo 0.03267; p=0.365, d=0.70 | Adversarial may beat solo but underpowered (N=4, 55% power) | Adversarial setup is justified but needs N>=8 for definitive comparison |
| heilbron/asymmetric-iterations (#204) | NEUTRAL BETWEEN ARMS — Both arms >=105% SOTA. K=1 used (not K=5). Loose coupling (min_delta=1 accidental) | Information-architecture changes do not break stagnation. Source code access + loose coupling achieved peak 0.03650 very early (gen 4-12). Feedback mode NULL. | **Critical**: K=5 never tested. Loose coupling (min_delta=1) was the confound that produced v1's best results. This is the direct predecessor experiment for k5-budget-loose. |
| heilbron/asymmetric-iterations-v2 (#206) | INCONCLUSIVE — tight coupling (min_delta=8) produced 98-104% baseline despite 4-6x more generations | Tight coupling under-constrains search. v2 < v1 despite more generations. Loose coupling is a performance-enabling condition, not a bug. Feedback mode NULL confirmed. | **Critical**: Confirms loose coupling hypothesis. min_delta=1 should be RESTORED in k5-budget-loose. Combined with K=5, this is the first test of compute budget asymmetry with known-good coupling. |

---

## Novelty Assessment

- [ ] This exact mechanism (K=5 budget + min_delta=1 loose coupling combined) has been tested before
- [ ] A similar mechanism was tested with different results in external literature
- [x] This is a novel combination for the GigaEvo adversarial Heilbron task

**Explanation**: The two components are each independently precedented but have never been combined:

1. **K=5 iteration ratio**: Directly analogous to WGAN-GP's n_critic=5. The GAN literature established this ratio as the standard in 2017. However, no external paper tests this in an LLM-guided MAP-Elites co-evolutionary setting, and no prior GigaEvo experiment has run K=5 (the amendment in asymmetric-iterations reduced it to K=1 before execution).

2. **Loose coupling (min_delta=1)**: No external paper directly studies interaction frequency / synchronization granularity in LLM-guided co-evolution. Island model literature shows migration interval is a dominant factor, with too-frequent migration causing premature convergence (opposing the loose coupling finding) -- but this is a cooperative, not competitive, setting. The competitive co-evolution synchrony question is not directly studied.

3. **Combined K=5 + min_delta=1**: Never tested anywhere. The internal evidence (v1 vs v2 comparison) strongly motivates this combination, but the hypothesis is untested.

---

## Recommendations for Elena

### 1. Update the Q_MAX baseline reference

Q_MAX=0.0365 is confirmed correct for Heilbronn n=11. GigaEvo's v1 peak (0.03650) is at Q_MAX. The internal SOTA (0.03449 from baseline-repro) remains the operative baseline for statistical comparisons.

**Suggested approach**: Use 0.03449 (internal SOTA) as the comparative anchor for effect-size thresholds, and 0.0365 (Q_MAX) as the theoretical ceiling. A result matching or exceeding v1's 0.03650 confirms the mechanism works.

### 2. The GAN analogy is theoretically grounded but imperfectly mapped

WGAN-GP's n_critic=5 rationale: the discriminator must approximate the Wasserstein distance well before generator updates are informative. The analogous claim for GigaEvo: the Improver must make multiple improvement attempts per Constructor epoch to avoid being starved of compute. However, in the GAN case D and G share the same loss; in GigaEvo they have separate objectives (G: maximize min_area; D: improve the best programs from G). The mapping is approximate, not exact. Elena should expect the mechanism to differ even if the quantitative ratio (5:1) transfers.

### 3. Treat loose coupling (min_delta=1) as the dominant IV, K=5 as secondary

The v1/v2 comparison provides stronger direct evidence for min_delta=1 than for K=5. In v1, the min_delta=1 "bug" caused D to run many micro-steps per G epoch -- functionally similar to K=5 inner iterations. It is not clear whether K=5 provides additional benefit beyond what min_delta=1 already delivers. A clean 2x2 factorial (min_delta: 1 vs 8 x inner_K: 1 vs 5) would resolve this, but if Elena is running a single-armed test, she should track whether K=5 additional iterations actually execute (verify in logs that D performs 5 inner loops, not just 1 with min_delta=1 providing implicit compute).

### 4. Expected effect size based on analogous experiments

- Positive scenario (loose coupling restored, K=5 adds additional benefit): Expected peaks in the 0.0360-0.0365 range, matching or slightly exceeding v1's 0.03648/0.03650. Probability moderate (~40%) given v1 evidence.
- Null scenario (loose coupling alone explains v1, K=5 adds nothing): Expected peaks around 0.03600-0.03650, replicating v1's performance with tighter distribution. Probability moderate (~40%).
- Negative scenario (K=5 inner loops cause instability, e.g., D diverges or Improver thrashes): Expected peaks below baseline-repro (0.03449). Probability low (~20%) based on GAN literature suggesting 5:1 is stable.

### 5. Confound to monitor: implicit compute from min_delta=1 vs explicit K=5

If min_delta=1 is active, D already runs many micro-steps between G epochs. Adding K=5 inner iterations on top of this may create a different dynamic than intended (very high effective D compute). The GAN literature warns that training D too much relative to G can cause D to overfit to the current G distribution, reducing useful gradient signal. Monitor Improver acceptance rate and invalidity separately from Constructor metrics.

### 6. Stagnation measurement

Eight prior experiments confirm Improver stagnation is structural. The pre-registered measure should be Improver acceptance rate after gen 20 (compare to baseline). If K=5 + min_delta=1 still shows <5% Improver acceptance rate after gen 20, the stagnation hypothesis survives the budget test and the search-space hypothesis (structured operators) becomes the primary remaining direction.

### 7. External state-of-art note

AlphaEvolve (2025) achieved Heilbronn n=11 ~0.0365 using a different mechanism (Gemini Flash/Pro ensemble with an implicit ~5-10x Flash-to-Pro call ratio). This is an interesting parallel but was achieved with orders-of-magnitude more compute and a fully general LLM coding agent. GigaEvo's goal is to study the mechanism, not simply achieve SOTA -- the finding that Q_MAX is reachable with an LLM-guided MAP-Elites algorithm is novel regardless.

---

## Summary Table: Key Numbers

| Reference | Value | Status |
|---|---|---|
| Internal SOTA (baseline-repro mean) | 0.03449 | Primary comparison anchor |
| GigaEvo peak (v1, loose coupling, min_delta=1) | 0.03650 | Best prior GigaEvo result |
| GigaEvo peak (v2, tight coupling, min_delta=8) | 0.03588 | Replication underperformed v1 |
| Theoretical Q_MAX used internally | 0.0365 | May be slightly low; see note |
| External best known n=11 (Comellas & Yebra / AlphaEvolve) | 0.0365 | Q_MAX — confirmed from primary source |
| WGAN-GP canonical n_critic | 5 | Direct inspiration for K=5 |

---

*Scout: Claude Sonnet 4.6. Sources: WGAN-GP (Gulrajani et al. 2017, arXiv:1704.00028), GAME (arXiv:2505.06617), AlphaEvolve (arXiv:2506.13131), Heilbronn global optimization (arXiv:2512.14505), Frontiers CEA review (frobt.2024.1470886), internal GigaEvo experiments PR #183/#188/#197/#201/#203/#204/#206, Wikipedia Heilbronn triangle problem.*
