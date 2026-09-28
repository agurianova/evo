# Research Strategy: Heilbronn Task Retrospective

**Date**: 2026-04-16
**Trigger**: heilbron/asymmetric-iterations-v2 closeout (PR #206, INCONCLUSIVE)
**Scope**: All 8 completed Heilbronn experiments (3 adversarial/, 5 heilbron/)

---

## 1. Hypothesis Ranking

### CONFIRMED (strong, consistent evidence)

| Hypothesis | Experiments | N (runs) | Continue? |
|---|---|---|---|
| Adversarial co-evolution produces actual_fitness improvement from cold start | 8 experiments, 64+ runs | Every experiment produced Constructor actual_fitness well above seed. Best: 0.03650 (Q_MAX). | NO -- established fact. |
| Improver stagnation is structural, not addressable by information or coupling interventions | 8 experiments, 64+ runs | K=0/1/3, bidirectional code, soft fitness, GAN, re-eval, source code, composition, gradient-in-prompt, loose/tight coupling -- ALL fail. D did not exceed G in 6/8 v1+v2 pairs. | YES -- but ONLY compute budget class remains untested. |
| Feedback mode (composition vs gradient-in-prompt) does not affect outcomes | 2 experiments, 8 pairs, 16 runs | Cross-arm delta 0.00066-0.00081. | NO -- CLOSED. |

### SUGGESTIVE (one positive or mixed evidence)

| Hypothesis | Evidence | Continue? |
|---|---|---|
| Adversarial pressure regularizes fitness variance vs solo | d=0.70 but p=0.365 (N=4, underpowered). Solo SD=0.00300 vs adversarial SD=0.00212. | YES -- N=8 cheap (4 more solo runs). Paper-critical. |
| K=3 bidirectional feedback improves Constructor | +0.00038 vs baseline (marginal). Premature stop at 45%. | DEPRIORITIZE -- marginal, confounded. |
| Source code access accelerates early optimization | v1: >=105% SOTA by gen 8-12. v2: NOT reproduced. Confounded with coupling granularity. | YES but only in factorial design. |
| Loose G/D coupling outperforms tight coupling | v1 (min_delta=1): best 0.03650. v2 (min_delta=8): best 0.03588, 4-6x more gens. | YES -- highest-priority new finding from this retrospective. |
| Improver polishing exceeds Constructor quality | 3/4 pairs in baseline-repro. But 1/4 pairs in v2. Inconsistent. | MONITOR -- track best-overall. |

### NULL

| Hypothesis | Evidence | Continue? |
|---|---|---|
| Feedback mode matters | Delta 0.00066-0.00081, 8 pairs. | NO -- CLOSED. |
| K=1 opponent context helps | K=1 REGRESSED below baseline (0.03247 vs 0.03464). | NO -- K=1 is harmful. |

### REFUTED

| Hypothesis | Evidence | Continue? |
|---|---|---|
| Archive re-evaluation improves adversarial | Control 0.0302 vs treatment 0.0194 (gap 0.011). | NO -- CLOSED. |
| Pure GAN resistance is viable | 99.6% resistance, only 0.02854 actual_fitness. Mode collapse. | NO -- CLOSED. |

---

## 2. Cross-Experiment Patterns

### Pattern A: Information interventions exhausted; compute budget is the last frontier

8 experiments tested information flow (what the LLM sees, how it sees it, what the archive does). NONE broke Improver stagnation. The ONE class never tested: compute budget asymmetry (K=5). The loose coupling finding (v1) provides indirect evidence -- D running many micro-steps while G waits is functionally similar to K>1 inner iterations.

### Pattern B: Best results came from "accidental" configurations

The two best-ever actual_fitness values (0.03648, 0.03650, tied with P3_A baseline-repro) came from v1 which had TWO accidental features: min_delta=1 (loose coupling) and K=1 (instead of K=5). The "fixed" v2 underperformed by 1.7%. Deliberate interventions are less effective than emergent dynamics of loosely-coupled systems.

### Pattern C: Small effects, high variance

Baseline: 0.03449 (SD=0.00212). Ceiling: 0.0365. Exploitable range: 0.002 (5.8% of baseline). Most interventions produce 0.0005-0.002 effects -- below noise floor at N=2-4. Need N>=6/arm for 0.003 MDE at 80% power.

### Pattern D: Diminishing returns on mechanism complexity

Simplest config (heilbron-prover, K=0, generational): 0.03464. Most complex (adversarial-dynamic-updates, K=3, re-eval, SOFT/GAN): 0.03020. No evidence that mechanism complexity improves outcomes.

### Pattern E: Solo MAP-Elites may be competitive

2/4 solo runs matched adversarial (S1=0.03538, S3=0.03458). Adversarial overhead is 2x compute per pair. d=0.70 needs N=8 confirmation.

### Pattern F: Intervention type hierarchy on Heilbronn

1. **Coupling granularity** (SUGGESTIVE+): loose > tight. New, needs direct test.
2. **Adversarial pressure** (SUGGESTIVE+): d=0.70, underpowered.
3. **Source code access** (SUGGESTIVE, confounded): acceleration in v1 not v2.
4. **Opponent context dose** (SUGGESTIVE): K=3 > K=0 > K=1 (non-monotonic).
5. **Feedback mode** (NULL): composition = gradient-in-prompt. Closed.
6. **Archive re-evaluation** (NEGATIVE): hurts. Closed.
7. **GAN resistance** (NEGATIVE): gaming/collapse. Closed.

---

## 3. Information Gap Analysis

Ranked by expected information gain:

### Gap 1: Does compute budget asymmetry (K=5) break Improver stagnation? [HIGHEST]
- **Why**: Only untested intervention CLASS. 8 experiments tested information; 0 tested compute. Loose coupling provides indirect support.
- **Belief**: 55% likely to show effect.
- **Existing idea**: adversarial_010 (rank 0.96)

### Gap 2: Does coupling granularity (min_delta) causally affect search? [HIGH]
- **Why**: v1 vs v2 confounded by 6 bug fixes. Clean isolation needed.
- **Belief**: 60% likely min_delta=1 is causally better (implicit D compute asymmetry).
- **No clean idea in IDEAS.yaml** -- adversarial_010 partially addresses this.

### Gap 3: Adversarial vs solo at adequate power? [HIGH, paper-critical]
- **Why**: d=0.70 at N=4. 4 more solo runs gives >80% power.
- **Belief**: 65% likely to confirm advantage.
- **Existing idea**: adversarial_012 (rank 0.82)

### Gap 4: Is Improver role adding value? [MEDIUM]
- **Why**: Inconsistent -- Improver exceeded Constructor in 3/4 baseline-repro pairs but only 1/4 v2 pairs.

### Gap 5: Theoretical ceiling? [MEDIUM]
- **Why**: 3 paths reached >=0.036 near Q_MAX. Extended runs (gen 150) would test ceiling.

---

## 4. Next Experiment Proposals

### Proposal 1: K=5 Compute Budget with Loose Coupling [HIGHEST PRIORITY]
- **RQ**: Does Improver max_mutations=40 (5x8) break stagnation with loose coupling (min_delta=1)?
- **Design**: 2-arm, N=4/arm. A: K=5 (D=40, G=8) min_delta=1. B: K=1 (D=8, G=8) min_delta=1. Standard adversarial_coevo. No source code access. Gen 50.
- **Primary DV**: Improver acceptance rate after gen 20 + Constructor actual_fitness.
- **Builds on**: adversarial_010, enhanced with loose coupling from v1/v2 finding.
- **Cost**: 16 runs, ~48h.

### Proposal 2: Adversarial vs Solo N=8 Power Increase [HIGH, can run in parallel]
- **RQ**: Does adversarial reliably beat solo at adequate power?
- **Design**: 4 additional solo runs (heilbron_solo, gen 50). Combine with existing N=4+4 for N=8/arm.
- **Primary DV**: Welch's t-test, alpha=0.05.
- **Builds on**: adversarial_012.
- **Cost**: 4 solo runs, ~24h.

### Proposal 3: Coupling Granularity Isolation [CONDITIONAL on Proposal 1]
- **RQ**: Does min_delta=1 causally outperform min_delta=8?
- **Design**: 3-arm (min_delta=1/4/8), N=3/arm. Standard adversarial_coevo (K=0). Gen 50.
- **Run ONLY IF Proposal 1 is positive** -- then isolate coupling vs budget.

### Proposal 4: Structured Move Improver [CONDITIONAL on Proposal 1 failure]
- **RQ**: Does constraining Improver to perturbation policy break stagnation?
- **Design**: 2-arm (structured vs standard Improver), N=3/arm. Gen 50.
- **Builds on**: adversarial_003.
- **Run ONLY IF K=5 fails** -- stagnation is search space, not budget.

### Proposal 5: Extended Run to Q_MAX (gen 150) [LOW PRIORITY]
- **RQ**: Can adversarial push past Q_MAX consistently?
- **Design**: 4 pairs, gen 150, standard adversarial_coevo.
- **Only worthwhile if** adversarial > solo confirmed.

---

## 5. Research Program Health

### Trajectory: PLATEAUING with one clear high-value direction remaining

8 experiments in 10 days. First 3 established the phenomenon. Last 5 explored mechanism variations with diminishing returns. Best actual_fitness (0.03650) achieved in experiment 5 (baseline-repro) and 7 (asymmetric-iterations v1), not in the latest experiments.

### Honest narrative assessment

| Pillar | Strength | Status |
|---|---|---|
| "Adversarial co-evolution works" | CONFIRMED | Not in question |
| "Adversarial > solo MAP-Elites" | UNRESOLVED | d=0.70, p=0.365. Weakest link. |
| "WGAN-GP analogy drives it" | UNTESTED | K=5 never tested. Theoretical core. |

### Estimated remaining high-value experiments: 2-3

- **Must-run**: Proposal 1 (K=5 budget) + Proposal 2 (adversarial vs solo N=8). Non-negotiable for paper.
- **Conditional**: Proposal 3 or 4 depending on Proposal 1 outcome.
- **After that**: Diminishing returns. Exploitable range is only 0.002.

### Decision matrix after Proposals 1+2

| K=5 result | Adversarial vs Solo | Paper narrative | Next step |
|---|---|---|---|
| Breaks stagnation | Adversarial > solo | "WGAN-GP insight transfers to co-evolutionary program synthesis" | Run coupling isolation (Proposal 3). Strong NeurIPS. |
| Breaks stagnation | Adversarial = solo | "WGAN-GP-inspired MAP-Elites" (no adversarial angle) | Pivot framing. |
| Fails | Adversarial > solo | "Adversarial pressure as regularization" (not WGAN-GP) | Run structured Improver (Proposal 4). |
| Fails | Adversarial = solo | Research line on Heilbronn exhausted | Pivot to HoVer/HotpotQA. |

### Recommendation: CONTINUE for 2-3 experiments, then DECIDE

The most important hypothesis (compute budget) has never been tested. Run Proposals 1+2 in parallel (~48h). Then follow the decision matrix.

---

*Generated by `/experiment-retrospective`. Consumed by `/experiment-design` and `/run-experiment`.*
