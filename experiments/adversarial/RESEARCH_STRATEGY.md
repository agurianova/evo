# Adversarial Co-Evolution Research Program: Retrospective Analysis

**Date**: 2026-04-12
**Scope**: 6 experiments, 32+ runs, 2 tasks, ~900 GPU-hours
**Task**: Heilbronn triangle (N=11, Q_MAX=0.0365)

---

## 1. Hypothesis Ranking

### CONFIRMED (strong, consistent evidence across 2+ experiments)

| # | Hypothesis | Evidence | Experiments |
|---|-----------|----------|-------------|
| 1 | **Adversarial co-evolution produces genuine optimization on Heilbronn** | Constructors reach 0.034-0.036 (93-100% of Q_MAX) from near-zero seeds. 3 independent discoveries above 0.036. | heilbron-prover, baseline-repro, adversarial-v2 |
| 2 | **Improver stagnation is structural, not feedback-dependent** | 0% acceptance rate for 20-45 gens in every experiment. K=0, K=1, K=3, soft fitness, bidirectional code feedback -- none break stagnation. 100% Constructor resistance in all cases. | All 6 experiments |
| 3 | **Simpler adversarial setups outperform complex ones** | Best actual_fitness (0.03548) from simplest config (K=0, generational, no re-eval). Every mechanism addition either hurt or was within noise. | heilbron-prover > adversarial-v2 > adversarial-dynamic-updates |
| 4 | **All prior interventions changed information, none changed compute budget** | K=1/K=3 opponent code, bidirectional feedback, soft fitness, archive re-eval, GAN resistance -- all are signal/information changes. None gave the Improver more mutation attempts per generation. The Improver's 8 mutations/gen budget is identical to the Constructor's despite a potentially harder task. | Retrospective insight across all 6 experiments |

### SUGGESTIVE (directional evidence, needs replication)

| # | Hypothesis | Evidence | Caveats |
|---|-----------|----------|---------|
| 5 | **Adversarial co-evolution may outperform solo MAP-Elites** | adversarial-vs-solo: +0.00182, p=0.365, d=0.70 (medium-large). Adversarial SD=0.00212 vs solo SD=0.00300. | Underpowered at N=4 (55%). Solo bimodal: 2/4 matched adversarial, 2/4 below. |
| 6 | **Adversarial pressure regularizes fitness variance** | Adversarial SD=0.00212 vs solo SD=0.00300. Stagnation (S4 17-gen plateau) and elevated invalidity (S2 31%) observed only in solo arm. | Single experiment (adversarial-vs-solo), N=4. |
| 7 | **K=3 opponent context may marginally help** | K=3: 0.03502 (+0.00038 above baseline), upward trajectory. K=1: regression. | Premature stop, historical baseline, N=1, steady-state confound |
| 8 | **Improver polishing exceeds Constructor quality** | 3/4 baseline-repro pairs: Improver best >= Constructor best. Mean Improver=0.0340 vs Constructor=0.0334. | Post-hoc, not pre-registered |
| 9 | **Heilbronn baseline (0.03464) is reproducible** | Best-overall mean=0.03449 (within 0.4%). Constructor-only CI wide [0.029, 0.038]. | N=4 borderline, one pair 60% complete |

### REFUTED (tried, consistently failed)

| # | Hypothesis | Evidence | Experiments |
|---|-----------|----------|-------------|
| 10 | **Archive re-evaluation improves adversarial fitness** | Treatment 0.01937 vs control 0.03020 (gap=0.011, 5.5x NEGATIVE threshold). | adversarial-dynamic-updates |
| 11 | **Pure GAN resistance is viable MAP-Elites fitness** | 99.6% resistance with only 0.02854 actual_fitness. Mode collapse. | adversarial-dynamic-updates |
| 12 | **Bidirectional arms race** | 37:1 ratio (optimizer-coevo). 100% Constructor resistance in all Heilbronn exps. | All 6 experiments |

---

## 2. Cross-Experiment Patterns

### The core insight: information vs compute budget

Every experiment in this research line varied the **information** flowing to the Improver:
- Experiment 2 (heilbron-prover): K=0 score-only feedback
- Experiment 3 (adversarial-v2): K=1/K=3 raw opponent code
- Experiment 4 (adversarial-dynamic-updates): Re-eval + soft/GAN fitness signals
- Experiment 5 (baseline-repro): K=0 (replication)
- Experiment 6 (adversarial-vs-solo): No opponent at all

**None** changed the Improver's **computational budget** -- every Improver had exactly 8 mutations per generation. This is the MAP-Elites analog of training a GAN discriminator with a single batch per generator step. WGAN-GP (Gulrajani et al. 2017) showed that D needs K=5 iterations per G step to provide meaningful gradient signal. The same principle may apply here: the Improver needs more attempts per generation to find improvements on near-optimal Constructor solutions.

### What consistently works
**The base mechanism itself** -- adversarial co-evolution reliably drives Constructors from near-zero to 93-100% of Q_MAX. This is a genuine, repeatable computational result on a classic combinatorial geometry problem.

### What consistently fails or hurts
1. **Increased mechanism complexity**: K=1, K=3, re-evaluation, soft fitness, GAN resistance, steady-state engine -- none improved on the simplest K=0/generational/no-re-eval configuration
2. **Archive perturbation**: Re-evaluation destabilized the archive in adversarial settings
3. **Narrow fitness signals**: GAN resistance produced mode collapse

### Research trajectory
- Exp 1 (optimizer-coevo): Infrastructure validation. Arms race fails. POSITIVE as engineering PoC.
- Exp 2 (heilbron-prover): Scientific breakthrough. Near-optimal Heilbronn solutions. POSITIVE.
- Exp 3 (adversarial-v2): First mechanism intervention. Marginal signal, confounded. SUGGESTIVE.
- Exp 4 (adversarial-dynamic-updates): Ambitious factorial. All cells below baseline. NEGATIVE.
- Exp 5 (baseline-repro): Defensive replication. Baseline confirmed within variance. SUGGESTIVE.
- Exp 6 (adversarial-vs-solo): Solo comparison. Adversarial edge suggestive but underpowered. INCONCLUSIVE.

**Trajectory: base mechanism works, mechanisms fail, need to change the approach vector.**

---

## 3. Information Gap Analysis (ranked by expected information gain)

### Gap 1: Does asymmetric iteration ratio (WGAN-GP K:1) break Improver stagnation? (CRITICAL)
All prior interventions changed information, none changed compute budget. K=5 Improver mutations per Constructor generation is the first intervention targeting the budget asymmetry. If it works, it opens a new intervention class. If it fails, stagnation is a search space problem (not budget), and structured Improver operators (adversarial_003) become the priority.
**Status**: Experiment designed -- `heilbron/asymmetric-iterations`.

### Gap 2: Adversarial vs solo with sufficient power (HIGH)
adversarial-vs-solo at N=4 showed d=0.70 but p=0.365. N=8/arm needed for 80% power. 4 additional solo runs required (adversarial N=8 available from combined data).

### Gap 3: What causes the 18% inter-pair variance? (MEDIUM)
SD=0.0026 on N=4. Understanding variance sources could reduce N requirements.

### Gap 4: Can structured Improver operators break stagnation? (MEDIUM)
Only one Improver type tested (generic entrypoint). Structured move operators might be easier for LLM mutation. Becomes priority if Gap 1 answer is "budget doesn't help."

### Gap 5: K=3 with concurrent control to completion? (LOW)
Expected effect +0.0004 is within noise floor. Likely NULL.

---

## 4. Next Experiment Proposals

### Proposal 1: heilbron/asymmetric-iterations (HIGHEST PRIORITY -- DESIGNED)
**Hypothesis**: K=5 Improver mutations/gen breaks stagnation and improves Constructor actual_fitness.
**Design**: K=1 vs K=5, N=3/arm, gen 50. Config-only change.
**Status**: Pre-registered. Ready for implementation.
**Duration**: ~72h.

### Proposal 2: adversarial-vs-solo-v2 (N=8 replication)
**Hypothesis**: Adversarial > solo at N=8 (80% power for d=0.70).
**Design**: 4 additional solo runs, combine with existing adversarial data.
**Duration**: ~48h. **Depends on**: asymmetric-iterations result.

### Proposal 3: structured-improver (adversarial_003)
**Hypothesis**: Perturbation-policy Improver breaks stagnation via reduced search space.
**Design**: Generic vs structured Improver, N=2/arm.
**Duration**: ~36h + engineering. **Priority depends on**: asymmetric-iterations result.

### Proposal 4: dose-response (K=3/5/10)
**Hypothesis**: Optimal K for MAP-Elites differs from WGAN-GP's K=5.
**Design**: 3-arm (K=3/5/10), N=2/arm.
**Duration**: ~72h. **Depends on**: asymmetric-iterations showing a positive signal.

---

## 5. Research Program Health

### Is the line publishable?

**Yes.** The data supports a NeurIPS 2026 paper with:
- **Positive result**: LLM-guided MAP-Elites + adversarial framing produces near-optimal Heilbronn solutions (97-100% of Q_MAX). 3 independent near-Q_MAX discoveries.
- **Negative but informative**: Structural asymmetry analogous to GAN training instability. Constructor converges, Improver collapses. Unlike GANs where D is easier, here D (Improver) is harder.
- **Mechanism taxonomy**: GAN resistance = mode collapse. Re-eval = destabilization. K=1 = over-anchoring. Information vs compute budget as the key distinction.
- **WGAN-GP analog**: If asymmetric-iterations succeeds, it's the central contribution -- showing that GAN training insights transfer to evolutionary quality-diversity methods.

### Critical path

**heilbron/asymmetric-iterations determines the paper's central claim:**
- If K=5 breaks stagnation: Paper = "WGAN-GP ratio transfers to adversarial quality-diversity. Budget allocation matters more than information design."
- If K=5 fails (stagnation persists): Paper = "Improver stagnation is a fundamental search space problem. GAN training analogies have limits in discrete evolutionary settings." Pivot to structured Improver.
- Either outcome is publishable. The question is which story.

### Recommendation

**Run heilbron/asymmetric-iterations immediately.** It's the highest-information-gain experiment, requires zero code changes, and determines the next 2-3 experiments regardless of outcome.

---

*Updated 2026-04-12 after adversarial-vs-solo closeout and retrospective analysis.*
