# Literature Brief: Dynamic D Re-Evaluation in Adversarial Co-Evolution

**Date**: 2026-04-09

---

## Related External Work

**1. Cliff & Miller (1995), "Tracking the Red Queen."** Foundational paper showing that co-evolutionary fitness is inherently relative: as opponents improve, a fixed fitness score becomes meaningless. They call this the "fitness ambiguity" problem and propose measuring progress against historical opponents. D re-evaluation directly addresses this by refreshing fitness against the current opponent archive.

**2. MAP-Elites in noisy/stochastic domains (Flageat et al., 2023; Grillotti & Cully, 2024).** QD literature addresses a closely analogous problem: "lucky" solutions with overestimated fitness dominate archive cells. Deep-Grid constantly re-evaluates ("questions") elites, allowing replacement by truly better solutions. The Extract-QD framework and ARIA (Archive Reproducibility Improvement Algorithm) formalize periodic re-evaluation to correct archive drift. Co-evolutionary staleness is a structured variant of this noise problem: the evaluation function itself shifts as opponents evolve.

**3. GAN discriminator update frequency (Goodfellow et al., 2014; Heusel et al., 2017 TTUR).** GANs face the same asymmetry: if the discriminator falls behind the generator, feedback degrades. The standard fix is multiple discriminator updates per generator step (n_critic > 1 in WGANs). Heusel et al.'s Two Time-Scale Update Rule proves convergence when the discriminator learns faster. D re-evaluation is the MAP-Elites analog: ensure D's archive reflects current G quality before selecting D parents.

**Closely related concurrent work**: Sakana AI's Digital Red Queen (Kumar et al., 2025) evolves programs against a growing history of all prior opponents, preventing staleness by construction. However, DRQ uses sequential self-play (no parallel archive), making it architecturally distinct from MAP-Elites co-evolution.

## Prior GigaEvo Evidence

Improver stagnation is confirmed across three experiments: optimizer-coevo (optimizers +1.8pp vs landscapes +67.7pp), heilbron-prover (0% Improver acceptance for 45 gens), and heilbron/adversarial-v2 (both Improvers stagnate despite bidirectional K=1/K=3 feedback). All Constructors reached 100% resistance. Bidirectional opponent code does not break the bottleneck.

## Novelty Assessment

Archive re-evaluation against current opponents has not been tested in LLM-guided MAP-Elites co-evolution. The QD literature addresses re-evaluation for stochastic noise but not for co-evolutionary fitness shift. The GAN literature addresses update frequency but not discrete archive-based selection. The specific mechanism (NO_CACHE DAG stage triggering re-evaluation when opponent archive changes) is novel in this context.

## Recommendations

1. **Strong theoretical grounding.** The mechanism directly addresses a confirmed root cause (stale fitness leading to wrong parent selection) with clear analogy to GAN n_critic and QD re-evaluation literature.
2. **Symmetric re-evaluation recommended.** Re-evaluate both D against current G and G against current D, consistent with issue #195 design.
3. **Measure selection quality, not just fitness.** Track how often re-evaluated fitness changes the elite in each archive cell (the "elite turnover rate") as a direct measure of staleness correction.
4. **Combine with K=3 feedback.** The adversarial-v2 suggestive signal for K=3 makes it a natural pairing for the next experiment.

---

Sources:
- [Cliff & Miller 1995 — Tracking the Red Queen](https://link.springer.com/chapter/10.1007/3-540-59496-5_300)
- [MAP-Elites for Noisy Domains by Adaptive Sampling](https://dl.acm.org/doi/10.1145/3319619.3321904)
- [Extract-QD Framework (2025)](https://arxiv.org/html/2502.06585)
- [Dynamic Quality-Diversity Search (2024)](https://arxiv.org/html/2404.05769)
- [Which GAN Training Methods Actually Converge (2018)](https://arxiv.org/pdf/1801.04406)
- [GAN Training — Google Developers](https://developers.google.com/machine-learning/gan/training)
- [Digital Red Queen — Sakana AI (2025)](https://arxiv.org/abs/2601.03335)
- [Popovici & Bucci — Coevolutionary Principles](https://www.semant.scholar.org/paper/Coevolutionary-Principles-Popovici-Bucci/10f0ed4eb66fc7f57f45b736149697433142354c)
- [Coevolutionary Principles (Springer)](https://link.springer.com/10.1007/978-3-540-92910-9_31)
