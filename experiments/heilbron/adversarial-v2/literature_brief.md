# Literature Brief: Adversarial Co-Evolution with Structured Feedback

**Experiment**: heilbron/adversarial-v2
**Date**: 2026-04-08
**Purpose**: Inform experiment design with SOTA techniques for improving information flow between co-evolving populations.

---

## 1. Directly Relevant Prior Work

### 1.1 GAME: Generational Adversarial MAP-Elites (2025)

**The closest existing method to GigaEvo's adversarial setup.**

Liden et al. (2025) introduce GAME, which co-evolves two MAP-Elites populations (Blue vs Red) in adversarial domains (battle games, wrestling robots, deck-building). Key mechanisms:

- **Alternating generational evolution**: Only one side evolves per generation; the other side's archive serves as the fitness function. This prevents simultaneous destabilization.
- **K-means task clustering**: When selecting opponents from the archive, GAME clusters elites by behavior and picks the fittest from each cluster --- ensuring the opposing population faces *diverse* challenges, not just the single hardest one.
- **Bootstrapping between generations**: Solutions from generation N are re-evaluated against generation N+1's tasks to seed the next archive, preventing catastrophic forgetting.

**Relevance**: GigaEvo's heilbron-prover already alternates populations. The missing piece is *diverse opponent selection* (currently only top-1) and *bootstrapping* (currently no carryover). GAME validates that both matter.

Source: [Adversarial Coevolutionary Illumination with GAME](https://arxiv.org/html/2505.06617v2)

### 1.2 ASRO: Game-Theoretic Co-Evolution for LLM Heuristic Discovery (2025)

ASRO frames LLM-based heuristic search as a two-player zero-sum game between solvers and instance generators, with persistent strategy pools and Nash equilibrium meta-strategies. Key innovations:

- **Payoff matrix + mixed Nash strategies**: Rather than greedy adversarial pressure, both sides maintain pools of strategies. A meta-game payoff matrix is computed, and mixed Nash equilibrium strategies determine sampling weights. This prevents cycling --- "self-play variants remain inferior to ASRO."
- **Base generator anchoring**: A fixed portion of instances always comes from a static base generator, stabilizing early training.
- **LLM best-response oracles**: New strategies are synthesized by LLMs targeting opponent vulnerabilities exposed by the payoff matrix.

**Relevance**: Directly applicable. The payoff matrix approach gives Improvers a structured view of Constructor weaknesses. Base anchoring prevents the Improver population from drifting too far from useful strategies.

Source: [Game-Theoretic Co-Evolution for LLM-Based Heuristic Discovery](https://arxiv.org/html/2601.22896v1)

### 1.3 Covolve: Adversarial LLM Policy-Environment Co-Evolution (2025)

Covolve models LLM-generated policy vs environment design as a zero-sum game. The environment designer generates increasingly challenging levels (as code) while the policy designer creates solving strategies (as code).

- **Mixed-strategy Nash equilibrium (MSNE)**: The meta-policy samples from a mixture over historical strategies weighted by Nash probabilities. This prevents forgetting previously solved environments.
- **Open-ended learning**: No predefined task distribution --- difficulty emerges from competition.

**Relevance**: The MSNE approach to preventing forgetting is directly transferable. In heilbron-v2, Constructors could sample from a mixture of historical configurations weighted by how effectively they resist Improvers.

Source: [Adversarial Co-Evolution of LLM-Generated Policies and Environments](https://openreview.net/forum?id=ser00zCWC2)

### 1.4 Digital Red Queen (Sakana AI, 2025)

DRQ evolves competitive programs (Core War warriors) using LLMs + MAP-Elites across sequential rounds. Each round optimizes against *all* previous champions.

- **Historical self-play**: Expanding opponent archive reduces cycling by 77% vs single-opponent evolution.
- **Quality-diversity preservation**: MAP-Elites maintains behavioral stepping stones within each round.
- **Convergent evolution**: Warriors converge to similar *performance profiles* while maintaining distinct source code.

**Relevance**: The "compete against all previous champions" approach is a proven anti-cycling mechanism. GigaEvo could maintain a hall-of-fame of resistant Constructor configurations for Improver evaluation.

Source: [Digital Red Queen](https://pub.sakana.ai/drq/)

### 1.5 GenEnv: Difficulty-Aligned Co-Evolution (2025)

GenEnv co-evolves LLM agents and environment simulators with an explicit *difficulty calibration* reward:

- **Alpha-curriculum reward**: Environment receives reward R_env = exp(-beta * (success_rate - alpha)^2), peaking when agent success rate matches target alpha (typically 0.5).
- **Self-regulating difficulty**: As the agent improves, the environment must generate harder tasks to maintain the target success rate.
- **Mathematical justification**: Intermediate difficulty (50% success) maximizes expected squared gradient norm --- the strongest learning signal.

**Relevance**: This is the most actionable technique for heilbron-v2. The Improver population's stagnation (0% improvement rate after gen 5-20) suggests tasks are *too hard*. A difficulty-calibrated reward could keep Improvers in the productive learning zone by selecting Constructor configurations of appropriate difficulty.

Source: [GenEnv: Difficulty-Aligned Co-Evolution](https://arxiv.org/html/2512.19682v1)

### 1.6 Multi-Agent Evolve: LLM Self-Improvement via Co-Evolution (2025)

Three LLM roles (Proposer, Solver, Judge) co-evolve via self-play. The Proposer earns rewards for generating questions that are challenging but solvable ("desirable difficulty").

- **Difficulty reward shaping**: Proposer is rewarded when Solver struggles but can still answer --- too-easy or impossible questions get low reward.
- **Quality filtering**: Minimum quality threshold (0.7) prevents dataset corruption from accumulating bad examples.

**Relevance**: The "desirable difficulty" concept maps directly to Constructor-Improver dynamics. Constructors should be rewarded not for being unbeatable, but for being *appropriately challenging*.

Source: [Multi-Agent Evolve](https://arxiv.org/html/2510.23595v1)

---

## 2. GAN Techniques Most Transferable to Evolution

### 2.1 Two-Timescale Update Rule (TTUR)

**GAN technique**: Discriminator uses higher learning rate than generator, converging to local Nash equilibrium (Heusel et al., NeurIPS 2017).

**Evolutionary analog**: Give Improvers more generations per cycle than Constructors. In heilbron-prover, Improvers stagnate because they get equal compute but face a harder task. A 3:1 or 5:1 Improver:Constructor generation ratio would let Improvers catch up before Constructors shift the landscape.

**Implementation**: In experiment.yaml, set `max_mutations_per_generation` asymmetrically (e.g., Improvers: 30, Constructors: 10).

Source: [TTUR Paper](https://arxiv.org/abs/1706.08500)

### 2.2 Feature Matching (Salimans et al., 2016)

**GAN technique**: Generator optimizes against intermediate discriminator features (L2 distance between feature means), not just pass/fail classification.

**Evolutionary analog**: Feed Improver source code, strategy descriptions, and specific failure modes (which triangle was weakest, which points were moved) into Constructor mutation prompts. This is the core "structured feedback" idea --- Constructors see *how* the Improver tried to attack, not just whether it succeeded.

**Implementation**: After each Improver evaluation, extract a structured critique (weakest triangle ID, moved points, strategy used) and inject it into the Constructor's mutation prompt.

### 2.3 Progressive Training / Curriculum Learning

**GAN technique**: Start with low-resolution images, progressively increase difficulty (Karras et al., 2018).

**Evolutionary analog**: Start Improvers against easy-to-improve configurations (random or early-generation Constructors), then gradually increase difficulty. GenEnv's alpha-curriculum is the modern version of this.

**Implementation**: Maintain a difficulty-sorted archive of Constructor configurations. Sample Improver opponents from the archive with bias toward configurations near the Improver's current success rate (~50%).

### 2.4 Spectral Normalization / Lipschitz Constraints

**GAN technique**: Constrain discriminator's Lipschitz constant to prevent it from becoming too powerful, stabilizing training.

**Evolutionary analog**: Cap Improver "virulence" --- limit how much an Improver can change a configuration (e.g., max 2 point moves per attempt). This prevents Improvers from trivially destroying configurations while encouraging strategic, targeted improvements.

**Implementation**: Add a constraint to the Improver evaluation: improvements that move more than K points are penalized or rejected.

### 2.5 Minibatch Discrimination

**GAN technique**: Discriminator sees batches of generated samples together, detecting lack of diversity (mode collapse).

**Evolutionary analog**: Evaluate Constructors against a *batch* of diverse Improvers simultaneously. If a Constructor only resists one type of attack but falls to others, its fitness is penalized. This prevents Constructors from overfitting to a single Improver strategy.

**Implementation**: Constructor fitness = min(resistance across top-K diverse Improvers), not just resistance to the single best Improver.

---

## 3. Classical Co-Evolution Anti-Pathology Methods

### 3.1 Hall of Fame (HoF)

Maintain an archive of historically best individuals from each population. Evaluate new candidates against HoF members, not just current population. Prevents cycling (Rosin & Belew, 1997).

### 3.2 Reducing Parasite Virulence

When the "parasite" (Improver) is too strong, the "host" (Constructor) disengages --- evolution stalls at mediocre stable states. Solution: reduce parasite virulence by limiting attack power or introducing graduated difficulty (Cartlidge & Bullock, 2004).

### 3.3 Shared Fitness / Resource Sharing

Fitness sharing penalizes individuals that are too similar, maintaining population diversity. In MAP-Elites this is built-in via the behavioral descriptor grid, but additional diversity pressure on *strategies* (not just solutions) may help.

Sources: [Combating Coevolutionary Disengagement](https://eprints.soton.ac.uk/261440/2/Combating.pdf), [Coevolutionary Pathologies](https://www.researchgate.net/publication/2765711_Challenges_in_Coevolutionary_Learning_Arms-Race_Dynamics_Open-Endedness_and_Mediocre_Stable_States)

---

## 4. Novelty Assessment

### What is novel about heilbron-v2

1. **LLM-native structured feedback in co-evolution**: No prior work feeds one population's source code and strategy into the other's LLM mutation prompt. ASRO and Covolve use LLMs as mutation operators but with scalar fitness signals only. Injecting Improver critique (weakest triangle, strategy used, moved points) into Constructor prompts is genuinely new.

2. **Adversarial MAP-Elites with LLM mutation**: GAME uses MAP-Elites with adversarial co-evolution but with standard GP/BT mutation, not LLM-guided. DRQ uses LLMs + MAP-Elites but with sequential (not simultaneous) adversarial dynamics.

3. **Difficulty calibration in LLM evolution**: GenEnv's alpha-curriculum has not been applied to evolutionary program synthesis. Applying it to tune Constructor difficulty for Improvers would be novel.

### What is NOT novel

- Two co-evolving MAP-Elites populations (GAME, 2025)
- LLM as mutation operator in evolution (EvoPrompting, FunSearch, OpenELM, DRQ)
- Adversarial co-evolution with LLM agents (Covolve, ASRO, DRQ)
- Hall-of-fame archives for anti-cycling (classical, 1997+)

---

## 5. Concrete Recommendations for Experiment Design

### R1: Structured Critique Feedback (HIGH PRIORITY)

After each Improver evaluation, generate a structured critique:
```
{
  "weakest_triangle": {"vertices": [3, 7, 10], "area": 0.012},
  "strategy": "moved point 7 closer to centroid",
  "points_modified": [7],
  "improvement_delta": +0.003
}
```
Inject this into the Constructor's mutation prompt as "Last attack report." This is the GAN "feature matching" analog --- richer signal than pass/fail.

**Treatment vs control**: Treatment gets structured critique; control gets only binary resistance signal.

### R2: Asymmetric Generation Ratios (HIGH PRIORITY)

Give Improvers 3x-5x more evaluations per cycle than Constructors. The TTUR analog: the harder role (Improver/discriminator) needs more updates to keep pace.

**Implementation**: Set Improver `max_mutations_per_generation` to 30, Constructor to 10.

### R3: Difficulty-Calibrated Opponent Selection (MEDIUM PRIORITY)

Instead of always pairing Improvers against the best Constructors, select opponents targeting ~50% success rate (GenEnv alpha-curriculum). Maintain a difficulty-sorted archive; sample from the zone where Improver success is 30-70%.

### R4: Diverse Opponent Batches (MEDIUM PRIORITY)

Evaluate Constructor fitness as min(resistance across top-K diverse Improvers), not just top-1. Use K-means clustering on Improver strategies (from GAME) to select K=3-5 diverse attackers.

### R5: Hall-of-Fame Archive (LOW PRIORITY --- MAP-Elites already provides this)

MAP-Elites inherently maintains an archive of diverse solutions. However, explicitly maintaining a separate HoF of "historically hardest to improve" Constructors for Improver training could add value. Low priority because MAP-Elites already provides most of this benefit.

### R6: Virulence Cap (OPTIONAL)

Limit Improvers to modifying at most K=3 points per attempt. This prevents trivial "demolish and rebuild" strategies and forces strategic, targeted improvements that provide more useful feedback to Constructors.

---

## 6. Key Papers Reference List

| Paper | Year | Key Idea | Relevance |
|-------|------|----------|-----------|
| GAME (Liden et al.) | 2025 | Adversarial MAP-Elites with alternating generations | Direct methodological precedent |
| ASRO (arxiv) | 2025 | Game-theoretic LLM heuristic co-evolution with Nash equilibrium | Payoff matrix + mixed strategies |
| Covolve (Sygkounas et al.) | 2025 | LLM policy-environment zero-sum co-evolution | MSNE for anti-forgetting |
| Digital Red Queen (Sakana) | 2025 | LLM + MAP-Elites adversarial program evolution | Historical self-play, 77% cycling reduction |
| GenEnv | 2025 | Difficulty-aligned agent-environment co-evolution | Alpha-curriculum for calibrated difficulty |
| Multi-Agent Evolve | 2025 | LLM self-improvement via 3-role co-evolution | Desirable difficulty concept |
| E-GAN (Wang et al.) | 2019 | Evolutionary GAN with multi-objective mutation | Population of generators, selection by quality+diversity |
| Lipizzaner (Toutouh et al.) | 2019 | Spatial co-evolutionary distributed GAN training | Grid topology, neighborhood exchange |
| TTUR (Heusel et al.) | 2017 | Two-timescale update rule for GAN convergence | Asymmetric learning rates |
| Feature Matching (Salimans et al.) | 2016 | Generator optimizes intermediate D features | Rich feedback beyond binary signal |
| Cartlidge & Bullock | 2004 | Reducing parasite virulence prevents disengagement | Virulence cap for harder role |
| Ficici & Pollack | 2000 | Mediocre stable states in co-evolution | Arms-race failure modes |
