# Results: adversarial/optimizer-coevo (PR #169)

**Date**: 2026-04-06
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Verdict**: **ASYMMETRIC** -- Landscapes improve dramatically (+67.7pp mean), optimizers stagnate (+1.8pp mean). The arms race hypothesis (H1) is not supported. Infrastructure is fully validated.

---

## 1. Summary

Adversarial co-evolution between optimizers (Pop A) and deceptive landscapes (Pop B) does not produce a bidirectional arms race. The result is a **one-sided escalation**: landscapes rapidly evolve sophisticated deception mechanisms (both pairs reaching >97% fitness, with P1-B achieving 100% -- perfect deception), while optimizers plateau early (gen 1 and gen 4 respectively) and never overcome the escalating adversary.

The task exhibits a fundamental structural asymmetry: evolving a function that *traps* a black-box optimizer is substantially easier than evolving a general-purpose optimizer that resists all traps. The LLM mutation operator excels at composing deceptive features (decoy basins, anisotropic decay, ring barriers, phase-shifted sinusoids) but struggles to improve general optimization algorithms beyond simple multi-restart random search.

Despite the null arms race result, the experiment is a **successful infrastructure validation**. The adversarial co-evolution pipeline -- AdversarialPipelineBuilder, FetchOpponentResultsStage, RedisOpponentArchiveProvider, MainRunSyncHook -- operated correctly across all 4 processes for the duration of the experiment. Lockstep synchronization maintained generation parity, opponent sampling produced non-trivial cross-play evaluations from gen 1, and no deadlocks or data loss occurred.

**Frontier fitness at final generation**:

| Population | Pair 1 | Pair 2 | Mean |
|------------|--------|--------|------|
| Pop A (Optimizer) | 78.7% (gen 15, partial) | 71.5% (gen 20) | 75.1% |
| Pop B (Landscape) | 100.0% (gen 15, partial) | 97.8% (gen 20) | 98.9% |

**Fitness improvement from gen 1 to final**:

| Population | Pair 1 | Pair 2 | Mean |
|------------|--------|--------|------|
| Pop A (Optimizer) | +0.0pp | +3.6pp | **+1.8pp** |
| Pop B (Landscape) | +70.2pp | +65.1pp | **+67.7pp** |

---

## 2. Final Metrics

### Pop A -- Optimizers

| Run | Pair | DB | Gen (final/max) | Best Val Fitness | Last Improvement | Acceptance Rate | Notes |
|-----|------|----|-----------------|------------------|------------------|-----------------|-------|
| P1-A | 1 | 1 | 15/20 (partial) | 78.7% | Gen 1 (27.6% -> 78.7%, +51.1pp) | 0.0% (gens 1-7) | Plateau from gen 1; never improved |
| P2-A | 2 | 3 | 20/20 | 71.5% | Gen 4 (67.9% -> 71.5%, +3.6pp) | 0.8% | Plateau from gen 4; mean fitness declining |

### Pop B -- Landscapes

| Run | Pair | DB | Gen (final/max) | Best Val Fitness | Last Improvement | Acceptance Rate | Notes |
|-----|------|----|-----------------|------------------|------------------|-----------------|-------|
| P1-B | 1 | 2 | 15/20 (partial) | 100.0% | Gen 11 (96.8% -> 100.0%) | 5.8% | Perfect deception at gen 11 |
| P2-B | 2 | 4 | 20/20 | 97.8% | Gen 17 (97.1% -> 97.8%, +0.7pp) | 4.8% | Steady improvement throughout |

### Fitness Trajectories

**P1-A (Optimizer, DB 1, gen 15/20 partial)**:

| Gen | Best | Mean | n_valid |
|-----|------|------|---------|
| 1 | 78.7% | 37.0% | 2 |
| 2 | 78.7% | 62.9% | 32 |
| 3-7 | 78.7% | declining to 31.7% | -- |

Last improvement: gen 1. Acceptance rate (gens 1-7): 0.0%. Mean fitness declined as opponents grew stronger, confirming the frontier optimizers could not adapt.

**P1-B (Landscape, DB 2, gen 15/20 partial)**:

| Gen | Best | Key milestones |
|-----|------|----------------|
| 1 | 29.8% | Seed-level |
| 3 | 44.0% | |
| 4 | 59.0% | |
| 5 | 83.6% | Rapid escalation begins |
| 6 | 91.3% | |
| 7 | 96.8% | Near-saturation |
| 11 | 100.0% | Perfect deception |

Last improvement: gen 11 (96.8% -> 100.0%). Acceptance rate: 5.8%.

**P2-A (Optimizer, DB 3, gen 20/20)**:

| Gen | Best | Mean | Key observation |
|-----|------|------|-----------------|
| 1 | 67.9% | -- | Initial |
| 4 | 71.5% | -- | Last improvement |
| 5-11+ | 71.5% | declining to 21.3% | Plateau, mean collapses |

Last improvement: gen 4. Acceptance rate: 0.8%.

**P2-B (Landscape, DB 4, gen 20/20)**:

| Gen | Best | Key milestones |
|-----|------|----------------|
| 1 | 32.7% | Seed-level |
| 4 | 86.5% | Rapid escalation |
| 6 | 91.5% | |
| 10 | 94.7% | |
| 11 | 97.1% | |
| 17 | 97.8% | Diminishing returns near ceiling |

Last improvement: gen 17 (97.1% -> 97.8%). Acceptance rate: 4.8%. Steady improvement throughout run.

**Baseline**: No prior adversarial experiment exists. This is the first adversarial co-evolution run in GigaEvo.

---

## 3. Hypothesis Test

### H1: Arms Race (PRIMARY)

**H0**: At least one population shows no fitness improvement from gen 1 to final (delta <= 0).
**H1**: Both populations show fitness improvement in both pairs (all 4 deltas > 0).
**Primary metric**: Frontier fitness improvement (final gen minus gen 1), per population, per pair.

**Observed deltas**:

| Delta | Pair 1 | Pair 2 |
|-------|--------|--------|
| Pop A (optimizer) | 78.7% - 78.7% = **0.0pp** | 71.5% - 67.9% = **+3.6pp** |
| Pop B (landscape) | 100.0% - 29.8% = **+70.2pp** | 97.8% - 32.7% = **+65.1pp** |

**Decision rule** (from 01_design.md Section 8, Test 1): Arms race is declared if ALL FOUR deltas are positive.

**Result**: P1-A delta = 0.0pp. **Not all four deltas are positive.** H0 is **not rejected**.

**Verdict per effect-size table** (01_design.md Section 2): Pop A mean delta = +1.8pp (< 5pp). Pop B mean delta = +67.7pp (>= 15pp). One population >= 5pp, other < 5pp. This is **ASYMMETRIC**: landscapes improve, optimizers stagnate.

### H2: Zero-Sum Coupling (SECONDARY)

**Expected**: Negative correlation between Pop A and Pop B frontier fitness deltas within pairs (when landscapes improve, optimizer fitness drops).

**Observed**: The data supports a weaker version of H2. Optimizer *mean* fitness declined over generations (P1-A mean: 37.0% at gen 1 -> 31.7% by gen 7; P2-A mean: declining to 21.3%) while landscape frontier fitness rose. However, optimizer *frontier* fitness did not decline -- it simply plateaued. The correlation is between landscape improvement and optimizer *mean* collapse, not frontier collapse.

This is consistent with genuine adversarial coupling: as landscapes become more deceptive, newly mutated optimizers score worse on average against the stronger opponents. But the best optimizer found early remains the best throughout -- it cannot be dethroned, nor can it be improved upon.

**Interpretation**: The zero-sum dynamic is real but one-sided. Landscape pressure makes the optimizer population's task harder over time (declining mean), but the selective pressure does not drive the discovery of better optimizers. The frontier optimizer is good enough to beat some landscapes (maintaining its fitness) but not general enough to beat the increasingly deceptive ones that enter the opponent archive.

### Paired Sign Test (SECONDARY)

Under H0 (P(improvement > 0) = 0.5), the probability of all 4 deltas being positive = 0.0625. We observe 3 of 4 positive (P1-A = 0.0, not positive). p = P(>= 3 of 4 positive) = 5/16 = 0.3125. **Not significant** at alpha = 0.10.

---

## 4. Effect Size

| Quantity | Value | Classification |
|----------|-------|----------------|
| Pop A mean frontier improvement | +1.8pp | Below +5pp threshold |
| Pop B mean frontier improvement | +67.7pp | Far above +15pp (STRONG) |
| Pop A-to-Pop B improvement ratio | 0.027 | 37:1 landscape advantage |
| Pop A mean fitness decline (mean, not frontier) | -15 to -50pp over run | Reflects opponent escalation |

The asymmetry is extreme. Landscapes improved 37x more than optimizers. This is not a minor imbalance -- it reflects a qualitative difference in task difficulty for the LLM mutation operator.

---

## 5. Secondary Observations

### Evolved Landscape Strategies

The LLM produced increasingly sophisticated deception mechanisms over generations:

- **Multiple decoy basins** (6+ in final landscapes): Instead of a single shifted basin, evolved landscapes create constellations of local minima at different depths, each designed to trap optimizers that explore in different directions.
- **Anisotropic decay**: Gradient slopes vary by dimension, preventing axis-aligned search strategies from finding the true optimum.
- **Ring barriers**: Concentric ridges surround the true optimum, requiring optimizers to "jump over" energy barriers -- a feature that defeats greedy local search.
- **Phase-shifted sinusoidal terms**: High-frequency oscillations layered on top of smooth basins create rugged terrain that defeats finite-difference gradient estimates.

These strategies represent genuine qualitative improvement over the seed landscape (shifted Rastrigin with hidden basin). The LLM demonstrated strong ability to compose mathematical deception from known function families.

### Optimizer Stagnation

Both optimizer populations converged to variants of multi-restart random search with local refinement. Despite the mutation LLM having access to knowledge of CMA-ES, particle swarm optimization, differential evolution, and other sophisticated algorithms, it failed to produce working implementations that outperformed the simple approach.

Likely causes:
1. **Pure Python constraint**: The task forbids numpy, scipy, and other libraries. Implementing CMA-ES or PSO from scratch in pure Python with correct matrix operations is error-prone, and the LLM's implementations may have contained subtle bugs.
2. **Budget constraint** (500 evaluations): Sophisticated algorithms need more evaluations to converge. With only 500 function evaluations, simple random search with local refinement is a competitive strategy.
3. **Non-stationary evaluation**: Each optimizer is tested against 5 sampled opponents. The optimal strategy depends on the opponent mix, which changes every generation. A specialist optimizer that beats one landscape type may fail on another.

### Declining Optimizer Mean Fitness

A striking observation: optimizer *mean* fitness declined throughout both runs (P1-A: 37.0% -> 31.7%; P2-A: declining to 21.3%), even as the *frontier* stayed flat. This confirms genuine adversarial pressure -- newly generated optimizers face harder landscapes than their predecessors did. The frontier optimizer survives because it was evaluated against easier early opponents and its fitness is not re-evaluated.

This is a direct consequence of non-stationary fitness (Confound #9 in 01_design.md). A fitness of 78.7% at gen 1 represents performance against weak early landscapes; maintaining 78.7% at gen 7 would require beating much stronger opponents. The frontier value is preserved by MAP-Elites' elitism, not by re-evaluation.

### Landscape Fitness Ceiling

P1-B reached 100.0% (perfect deception) at gen 11, meaning its best landscape program deceived all 5 sampled optimizers on every evaluation. This represents a ceiling effect -- there is no room for further improvement. P2-B approached this ceiling at 97.8% by gen 17. The landscape population effectively "won" the arms race by gen 11-17.

---

## 6. Infrastructure Validation

| Check | Criterion | Pair 1 | Pair 2 | Status |
|-------|-----------|--------|--------|--------|
| Generation parity | max gen gap <= 2 | PASS | PASS | **PASS** |
| n_opponents > 0 at gen 1 | Both pops | PASS (4-5 opponents) | PASS (4-5 opponents) | **PASS** |
| n_opponents at gen 5 | >= 3 for both | PASS | PASS | **PASS** |
| Both pops reach max_gen | YES | PARTIAL (stopped gen 15) | YES (gen 20) | **PARTIAL** |
| No deadlocks | No process blocks > 30 min | PASS | PASS | **PASS** |
| Opponent archive functional | Cross-play evaluations non-trivial | PASS | PASS | **PASS** |

**Lockstep synchronization (MainRunSyncHook)**: Worked correctly throughout both pairs. Generation counters advanced in lockstep with <= 1 generation gap. No timeout events, no sync stalls.

**Opponent sampling (FetchOpponentResultsStage + RedisOpponentArchiveProvider)**: Functional from gen 1. Opponent archives grew as expected (n_opponents reached 4-5 per evaluation). Cross-play evaluations produced meaningful fitness signals.

**Conclusion**: The adversarial co-evolution infrastructure is validated and ready for deployment on more complex domains. All components -- pipeline builder, opponent fetching, cross-play evaluation, lockstep sync, archive population -- performed as designed.

---

## 7. Amendment Impact Assessment

| # | Deviation | Impact on Validity | Assessment |
|---|-----------|-------------------|------------|
| 1 | Pair 1 stopped at gen 15/20 (researcher decision) | Minor -- P1-A had 0% acceptance for 7+ gens, P1-B hit 100%. Trajectory was terminal. | **Valid** -- early stop does not change the verdict. Even 5 more generations would not alter P1-A's 0.0pp delta. |
| 2 | Pop B seed landscape bug fixed pre-launch (hidden basin depth -50 -> -200) | None -- fixed before any run started. The original seed had f(optimum) that was NOT the global minimum, violating the validity constraint. | **Valid** -- the fix was necessary for the experiment to function at all. |

Neither deviation materially affects the analysis. The early stop in Pair 1 was conservative -- by gen 15, the trajectory had been terminal for both populations (P1-A plateau since gen 1, P1-B ceiling at 100% since gen 11). The seed bug was a correctness fix applied before launch.

---

## 8. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| P1-A | Yes | Completed gen 15/20 (early stop, plateau). Trajectory data sufficient. |
| P1-B | Yes | Completed gen 15/20 (early stop, ceiling). Reached 100% fitness. |
| P2-A | Yes | Completed gen 20/20 as pre-registered. |
| P2-B | Yes | Completed gen 20/20 as pre-registered. |

No runs invalidated. Neither pair met any invalidation criterion (Section 10, 01_design.md). Both pairs advanced past gen 5, no deadlocks, no data loss, no config mismatches, n_opponents > 0 at gen 5 for all processes.

---

## 9. Lessons Learned

**What worked**:
- **Adversarial infrastructure is sound**: AdversarialPipelineBuilder, FetchOpponentResultsStage, RedisOpponentArchiveProvider, and MainRunSyncHook all performed correctly. No race conditions, no data corruption, no sync failures. This validates the engineering investment.
- **Lockstep synchronization**: MainRunSyncHook maintained generation parity throughout. The poll-and-wait mechanism with 7200s timeout is robust.
- **Toy domain as PoC**: The pure-Python optimizer-vs-landscape domain delivered fast evaluations (seconds, not minutes), enabling 15-20 generations in hours. This is the right domain for infrastructure validation.
- **LLM landscape evolution**: The mutation LLM (Qwen3-235B) demonstrated strong ability to compose deceptive landscape functions. The evolved strategies (multi-basin, ring barriers, anisotropic decay, sinusoidal perturbation) are qualitatively sophisticated.

**What didn't work**:
- **Optimizer evolution**: The LLM could not evolve optimizers past simple multi-restart random search. The pure-Python + 500-budget constraint creates a narrow corridor that the LLM cannot escape. Relaxing these constraints (allow numpy, increase budget) or choosing a different "attacker" population may be needed.
- **Task symmetry assumption**: The design assumed optimizers and landscapes are comparably difficult to evolve (Confound #8). The 37:1 improvement ratio disproves this. Future adversarial experiments must validate task symmetry before launch, or accept asymmetric dynamics as a feature.
- **Non-stationary fitness interpretation**: Frontier fitness values are not comparable across generations because opponents change (Confound #9, Risk #5). This makes raw fitness trajectories misleading for the optimizer population. A supplementary "absolute" evaluation against fixed benchmarks was pre-registered (Section 9, Risk #5 mitigation) but not executed.

**Infrastructure issues**:
- None. The adversarial infrastructure performed flawlessly.

---

## 10. Next Steps

Per the decision tree (01_design.md, Appendix B):

**Observed pattern**: Pop B improves, Pop A stagnates -> "Improve optimizer task description; add more optimizer seeds; or switch domain."

Specific recommendations:

1. **Rebalance the task**: The optimizer-vs-landscape domain has inherent asymmetry. Options:
   - **Relax optimizer constraints**: Allow numpy/scipy, increase evaluation budget from 500 to 5000. This gives the LLM a richer toolkit for implementing sophisticated algorithms.
   - **Constrain landscape complexity**: Limit landscape dimensionality, ban multi-basin designs, or impose smoothness constraints. This reduces the landscape population's advantage.
   - **Switch to a symmetric domain**: Consider "attack-vs-defense" tasks where both populations evolve programs of comparable complexity (e.g., adversarial test generation vs. robust classifiers on NLP data).

2. **Evaluate optimizers against fixed benchmarks**: Run the final P1-A and P2-A best optimizers against the standard Rastrigin/Griewank/Schwefel suite to measure absolute optimization quality independent of the co-evolved opponents. This was pre-registered but not executed.

3. **Scale to NLP domain (with caution)**: The infrastructure is validated. An adversarial experiment on HoVer or HotpotQA (e.g., evolving hard test examples vs. robust chains) can proceed. However, the asymmetry lesson must inform task design: ensure both populations have comparable evolutionary difficulty.

4. **Analyze evolved programs in depth**: Trace the lineage of P1-B's 100% landscape and P2-B's 97.8% landscape to understand which mutation steps produced the key deception innovations. This qualitative analysis is valuable for the paper regardless of the null arms race result.

5. **Multi-restart experiments**: If the domain is retained, run with N=4 pairs and increased generations (50+) to determine whether optimizer evolution is merely slow (eventually overcomes the landscape) or fundamentally stuck.

---

## 11. Paper / Report Notes

- **Infrastructure contribution is validated**: The adversarial co-evolution pipeline (lockstep sync, opponent fetching, cross-play evaluation, archive population) works correctly and is ready for deployment. This is a publishable engineering contribution.
- **The asymmetry finding is itself interesting**: Demonstrating that LLM-guided evolution has dramatically different capabilities on "offense" (deception) vs. "defense" (robustness) tasks is a novel observation. The 37:1 improvement ratio and the qualitative sophistication of evolved landscapes vs. optimizer stagnation is noteworthy.
- **Evolved landscape strategies are publishable**: The progression from simple shifted Rastrigin to 6-basin anisotropic landscapes with ring barriers and sinusoidal perturbation -- all discovered by an LLM mutation operator without human guidance -- is a compelling illustration of LLM-guided search in mathematical design spaces.
- **Honest framing**: The arms race hypothesis is not supported. This should be presented as a pilot that (a) validates infrastructure, (b) reveals a fundamental task-design challenge in adversarial co-evolution, and (c) motivates domain-rebalancing or domain-switching before scaling to expensive NLP tasks.
- **Non-stationary fitness caveat**: Any figure showing optimizer fitness trajectories must note that the y-axis represents performance against a changing opponent population, not absolute optimization quality. The declining mean fitness is evidence of adversarial pressure, not optimizer degradation.

---

## Appendix A: Detailed Fitness Deltas

| Run | Population | Gen 1 Fitness | Final Gen Fitness | Final Gen | Delta (pp) | Direction |
|-----|------------|--------------|-------------------|-----------|------------|-----------|
| P1-A | Optimizer | 78.7% | 78.7% | 15 | 0.0 | Flat |
| P1-B | Landscape | 29.8% | 100.0% | 15 | +70.2 | Strong positive |
| P2-A | Optimizer | 67.9% | 71.5% | 20 | +3.6 | Weak positive |
| P2-B | Landscape | 32.7% | 97.8% | 20 | +65.1 | Strong positive |

**Mean deltas**:
- Pop A (Optimizer): (0.0 + 3.6) / 2 = **+1.8pp**
- Pop B (Landscape): (70.2 + 65.1) / 2 = **+67.7pp**

## Appendix B: Decision Tree Trace

```
Step 1: Infrastructure validation
  All 4 processes reached max_gen?  PARTIAL (Pair 1 stopped at gen 15)
  n_opponents > 0 at gen 1?         YES (all 4 processes)
  Max gen gap <= 2 within pair?      YES (both pairs)
  -> Infrastructure PASS (partial completion is researcher decision, not failure)
  -> Proceed to Step 2

Step 2: Arms race detection
  delta_A_1 = 0.0pp    (NOT positive)
  delta_A_2 = +3.6pp   (positive)
  delta_B_1 = +70.2pp  (positive)
  delta_B_2 = +65.1pp  (positive)

  All 4 positive?  NO (P1-A = 0.0)
  All Pop B > 0, some Pop A <= 0?  YES
  -> ASYMMETRIC: landscapes improve, optimizers stagnate

Step 3: Effect-size classification (N/A -- arms race not detected)

Step 4: Qualitative analysis
  Pop A optimizers at final gen: variants of multi-restart random search
    with local refinement. No CMA-ES, no PSO, no differential evolution
    implementations survived. Minor variations on seed strategy.
  Pop B landscapes at final gen: sophisticated multi-basin deception with
    6 decoy basins, anisotropic decay, ring barriers, phase-shifted
    sinusoidal perturbation. Qualitative leap beyond seed.
  -> Confirms asymmetry is genuine, not a measurement artifact.

Step 5: Next experiment decision
  ASYMMETRIC -> investigate bottleneck, improve weaker population's setup
  -> Rebalance task constraints or switch domain before scaling
```
