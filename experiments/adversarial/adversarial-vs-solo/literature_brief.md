# Literature Brief: Adversarial Co-Evolution vs Solo MAP-Elites on Heilbronn N=11

**Date**: 2026-04-11
**Purpose**: Inform experimental design for `adversarial/adversarial-vs-solo`
**Research question**: Does adversarial co-evolution improve actual_fitness over standard (non-adversarial) MAP-Elites on Heilbronn N=11?

---

## 1. Related External Work

### 1.1 Heilbronn Triangle Problem: Known Bounds and Algorithms

The Heilbronn triangle problem asks: place N points in a convex region to maximize the minimum triangle area over all C(N,3) triples. For the unit-area equilateral triangle with N=11, the target min_area is 0.0365.

**Best known approaches for small N (7-12)**:
- **Simulated annealing**: Comellas & Yebra (2002) found the best known configurations for N=7 through N=12 in the unit square using simulated annealing followed by local optimization to find nearby exact local maxima. Optimality is proven only for N <= 7.
- **Mixed-integer optimization (MINLP)**: Sudermann-Merx (2026, arXiv:2603.11107) developed an optimize-then-refine framework combining global MINLP with exact symbolic computation. Proved global optimality for N=9 (confirming Comellas & Yebra's 2002 configuration). For N >= 10, exact optima remain open.
- **AlphaEvolve** (Google DeepMind, 2025): Found a construction for N=11 with min_area > 0.0365 in a unit-area triangle, improving the previous best of 0.036. AlphaEvolve uses solo (non-adversarial) LLM-guided evolution with a hybrid MAP-Elites + island-model population, not competitive co-evolution.

**Key implication for design**: AlphaEvolve's solo evolutionary approach achieved >= 0.0365 on the exact same problem (Heilbronn N=11, unit triangle). This is the strongest external evidence that adversarial pressure may be unnecessary -- a non-adversarial LLM-guided evolutionary system matched or exceeded the GigaEvo adversarial best (0.03548). However, AlphaEvolve uses Gemini 2.0 Pro/Flash (much larger models than Qwen3-235B), more compute, and a different evolutionary framework, so the comparison is confounded.

### 1.2 LLM-Guided Program Synthesis and Evolution

**FunSearch** (Romera-Paredes et al., Nature 2024): Paired a pre-trained LLM with an automated evaluator in an evolutionary loop. Discovered new constructions for the cap set problem exceeding 20-year-old bounds. Uses solo MAP-Elites-style island populations -- no adversarial component. Demonstrated that LLMs can make genuine mathematical discoveries via evolutionary program search.

**AlphaEvolve** (Google DeepMind, 2025): Generalized FunSearch from single functions to entire codebases. Uses an ensemble of Gemini models (Flash for throughput, Pro for quality) in an evolutionary database inspired by MAP-Elites and island models. Applied to Heilbronn among other problems. Solo evolution throughout.

**OpenELM** (Lehman et al., 2023; CarperAI): Open-source library implementing Evolution through Large Models. Supports MAP-Elites, CVT-MAP-Elites, and Deep Grid MAP-Elites. Includes co-evolution of problems and solutions (cooperative, not adversarial). The library demonstrates that LLM-as-mutation-operator is a viable paradigm across domains.

**CodeEvolve** (2025): Open-source evolutionary coding agent using islands-based genetic algorithm with LLM orchestration. Preliminary results approaching SOTA on Heilbronn and other problems. Solo evolution.

**EvoLattice** (2025): Multi-alternative quality-diversity graph representations for LLM-guided program discovery. Extends MAP-Elites with persistent internal populations. Solo evolution.

**Pattern**: All published LLM-guided evolution systems for mathematical optimization use solo (non-adversarial) evolution. No published work uses adversarial co-evolution for combinatorial geometry or mathematical program synthesis.

### 1.3 Adversarial Co-Evolution in Quality-Diversity

**GAME (Generational Adversarial MAP-Elites)** (Anne et al., ALIFE 2025): The most directly relevant external work. GAME co-evolves both sides of an adversarial problem by alternating which side is evolved each generation. Applied to multi-agent battle games, soft-robot wrestling, and deck building. Key findings: (1) dynamics sometimes resemble an arms race, (2) starting from scratch each generation increases open-endedness, (3) neutral mutations preserve stepping stones.

GAME does NOT compare adversarial vs solo MAP-Elites on the same problem. It compares GAME to solo-side MAP-Elites (evolving only one side while fixing the other), which is a different ablation. The paper does not address whether co-evolving both sides improves quality on the evolved-side metric compared to solo evolution of that side alone.

**Sample-Efficient QD by Cooperative Coevolution** (CCQD, OpenReview 2025): Cooperative (not competitive) co-evolution to improve QD sample efficiency. Decomposes policy networks into representation and decision layers. Different paradigm from adversarial co-evolution.

### 1.4 Competitive Co-Evolution: Known Pathologies

The competitive co-evolution literature documents several failure modes directly relevant to GigaEvo's observed dynamics:

- **Disengagement** (Cartlidge & Bullock, 2004): When one population dominates, fitness gradient disappears for the other. The dominant population drifts randomly rather than continuing to improve. Directly parallels GigaEvo's Improver stagnation at 100% Constructor resistance.
- **Loss of gradient** (Popovici & De Jong, 2005): Asymmetries in problem structure or initial conditions drive one population to convergence before the other, eliminating selection pressure. Matches the structural asymmetry observed across all 5 GigaEvo adversarial experiments.
- **Red Queen cycling** (Cliff & Miller, 1995): Earlier adaptations lost as populations cycle. NOT observed in GigaEvo -- Constructors monotonically improve rather than cycle.
- **Mediocre stable states** (Ficici & Pollack, 1998): Populations reach a mutual equilibrium that is not globally optimal. Potentially relevant -- the 0.034-0.035 plateau may be a mediocre stable state rather than a true optimum, given that AlphaEvolve reached 0.0365+.
- **Fitness ambiguity** (Cliff & Miller, 1995): Progress must be measured relative to current opponents, not historical ones. GigaEvo addresses this via actual_fitness (opponent-independent geometry), but selection fitness is still relative.

**Key implication**: The co-evolution literature predicts exactly the pathologies GigaEvo observes (disengagement/stagnation, asymmetric dynamics). The proposed experiment tests whether these pathologies impose a net cost relative to solo evolution.

---

## 2. Prior GigaEvo Experiments

### 2.1 Summary Table

| # | Experiment | PR | Verdict | Constructor actual_fitness | Key Finding |
|---|-----------|-----|---------|---------------------------|-------------|
| 1 | adversarial/optimizer-coevo | #169 | ASYMMETRIC | N/A (different task) | PoC; 37:1 asymmetry; arms race not supported |
| 2 | adversarial/heilbron-prover | #183 | POSITIVE | 0.03380, 0.03548 (mean 0.03464) | 97% of Q_MAX; 100% resistance; Improver stagnation |
| 3 | heilbron/adversarial-v2 | #188 | SUGGESTIVE | K=3: 0.03502, K=1: 0.03247 | K=3 > K=0 > K=1; premature stop at 45% |
| 4 | heilbron/adversarial-dynamic-updates | #197 | NEGATIVE | Best: 0.03186 (SOFT_C) | Re-eval harmful; GAN mode collapse; all below baseline |
| 5 | heilbron/baseline-repro | #201 | SUGGESTIVE | Mean 0.03337 (Constructor), 0.03449 (best-overall) | Baseline reproducible; 3 near-Q_MAX discoveries |

### 2.2 Established Facts from Prior Experiments

**Confirmed patterns (HIGH confidence)**:
1. Adversarial co-evolution reliably drives Constructors from near-zero to 93-100% of Q_MAX (0.034-0.036)
2. Improver stagnation is structural -- 0% acceptance rate for 20-45 gens across all experiments, regardless of feedback mechanism (K=0, K=1, K=3, soft, GAN, re-eval)
3. Simpler configurations outperform complex ones -- best actual_fitness (0.03548) from simplest setup (K=0, generational, no re-eval)
4. Constructor resistance reaches 100% in all experiments

**Variance characteristics**:
- Inter-pair SD = 0.0026 (Constructor), 0.0021 (best-overall) from baseline-repro (N=4)
- Range: 0.0302 to 0.0365 across Constructors
- Implies N >= 4 per arm needed for effect sizes of 0.003

**Best adversarial result**: 0.03548 (heilbron-prover P2_A), 97.2% of Q_MAX
**Best-overall**: 0.03650 (baseline-repro P3_A Constructor), above Q_MAX

### 2.3 The Critical Gap

Five experiments, 28 runs, ~800 GPU-hours have been invested in adversarial co-evolution on Heilbronn. The adversarial mechanism itself has never been ablated against a non-adversarial control. Every experiment compared adversarial variants against other adversarial variants or historical adversarial baselines.

The baseline-repro experiment (PR #201) confirmed that adversarial co-evolution reproducibly achieves actual_fitness ~0.034-0.035. But the counterfactual -- what does solo MAP-Elites achieve on the same problem with the same compute? -- remains untested.

---

## 3. Novelty Assessment

### 3.1 Has This Exact Comparison Been Done?

**No.** To the best of this review:

1. **No published work** compares adversarial vs solo MAP-Elites on Heilbronn or any combinatorial geometry problem
2. **No published work** compares adversarial vs solo LLM-guided evolution on any mathematical optimization task
3. **GAME** (Anne et al., 2025) is the closest external work but compares co-evolution vs one-side-fixed (not co-evolution vs solo-both-sides)
4. The broader co-evolution literature includes ablation studies (e.g., parasite-host vs solo host) but not in the QD/MAP-Elites or LLM-guided evolution context

### 3.2 Why This Matters

The experiment addresses a gap at the intersection of three research areas:

- **Quality-diversity**: Does adversarial pressure improve archive quality over solo QD? No direct test exists in the literature.
- **LLM-guided evolution**: All published systems (FunSearch, AlphaEvolve, CodeEvolve, OpenELM) use solo evolution. The adversarial variant is unique to GigaEvo. Does it add value?
- **Competitive co-evolution**: The pathology literature (disengagement, loss of gradient) predicts that adversarial co-evolution can be neutral or harmful. Does the empirical data confirm this on a real optimization problem?

### 3.3 External Confounds to Acknowledge

AlphaEvolve achieved >= 0.0365 on Heilbronn N=11 using solo evolution. If GigaEvo's solo MAP-Elites also reaches ~0.034-0.035, the adversarial mechanism adds nothing and the real bottleneck is the evolutionary framework or mutation LLM quality. The experiment should note that AlphaEvolve's result is not directly comparable due to different LLMs (Gemini >> Qwen3-235B), different compute budgets, and different evolutionary frameworks.

---

## 4. Recommendations for Designer

### 4.1 Design Priorities

1. **Strict control matching**: The solo arm must use identical mutation LLM, compute budget, generation count, and MAP-Elites parameters. The ONLY difference should be absence of the opponent population and adversarial fitness components. Use plain actual_fitness (min_area) as the solo arm's fitness signal.

2. **Solo problem variant**: Create a non-adversarial `problems/heilbron/` variant (or use the existing one) that evolves `entrypoint()` programs returning (11,2) arrays, scored by min_area. No FetchOpponentResultsStage, no resistance, no opponent sync.

3. **Sample size**: Given inter-pair SD ~0.0026 and the need to detect deltas of ~0.003, N=4 per arm (8 total runs) provides adequate power. N=6 per arm would be better but doubles compute.

4. **Pipeline**: Use `pipeline=standard` for the solo arm (plain dict return, no feedback). Use `pipeline=adversarial_coevo` for the adversarial arm. This is the cleanest contrast.

5. **Generation count**: Match to heilbron-prover (gen 50). The adversarial arm should use the simplest proven configuration (K=0, generational engine, no re-eval) per the "simpler is better" pattern.

### 4.2 Hypotheses to Pre-Register

- **H0** (null): Solo MAP-Elites actual_fitness is within 0.003 of adversarial (mean difference < 0.003). Adversarial overhead is unjustified.
- **H1** (adversarial advantage): Adversarial actual_fitness exceeds solo by >= 0.003. Adversarial pressure adds value.
- **H2** (adversarial harm): Solo exceeds adversarial by >= 0.003. Adversarial pathologies (disengagement, asymmetry) impose a net cost.

### 4.3 Interpretation Framework

| Solo result | Implication | Next step |
|------------|-------------|-----------|
| Solo >= 0.034 | Adversarial adds nothing; paper pivots to "MAP-Elites + LLM solves Heilbronn" | Close adversarial line |
| Solo ~0.025-0.033 | Adversarial provides meaningful boost | Paper = "adversarial pressure drives optimization quality"; invest in 2-3 more experiments |
| Solo < 0.025 | Adversarial is critical | Strong paper narrative; investigate what adversarial pressure provides |

### 4.4 Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Solo problem variant introduces bugs (different pipeline, no opponent stages) | Smoke test: verify solo run produces valid programs and fitness scores before full launch |
| Solo MAP-Elites converges faster (no sync overhead) -- confounds generation count | Track wall-clock time and total evaluated programs as secondary DVs |
| Existing `problems/heilbron/` task_description may have stale references | Inspect task_description.txt for opponent/adversarial language before using for solo arm |
| AlphaEvolve comparison undermines the paper regardless of outcome | Frame honestly: GigaEvo uses smaller LLM and less compute; the question is whether adversarial pressure helps within a fixed-resource budget |

### 4.5 Literature to Cite in Design Doc

- Romera-Paredes et al. (2024). Mathematical discoveries from program search with large language models. Nature.
- AlphaEvolve (Google DeepMind, 2025). A coding agent for scientific and algorithmic discovery.
- Anne et al. (2025). Generational Adversarial MAP-Elites for Multi-Agent Game Illumination. ALIFE 2025.
- Comellas & Yebra (2002). New Lower Bounds for Heilbronn Numbers. Electronic Journal of Combinatorics.
- Sudermann-Merx (2026). From Computational Certification to Exact Coordinates: Heilbronn's Triangle Problem. arXiv:2603.11107.
- Cartlidge & Bullock (2004). Combating Coevolutionary Disengagement by Reducing Parasite Virulence.
- Ficici & Pollack (1998). Challenges in coevolutionary learning: arms-race dynamics, open-endedness, and mediocre stable states.
- Lehman et al. (2023). Evolution through Large Models.

---

*Generated 2026-04-11 for experiment design of `adversarial/adversarial-vs-solo`.*
