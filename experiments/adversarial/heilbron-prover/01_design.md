# Experimental Design: Adversarial Co-Evolution -- Prover/Improver on the Heilbronn Triangle Problem

**Date**: 2026-04-06
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft -- awaiting Reviewer-2

---

## 1. Research Question

The first adversarial co-evolution experiment in GigaEvo (adversarial/optimizer-coevo, PR #169) validated the pipeline infrastructure but revealed a critical asymmetry: landscapes dominated optimizers by a 37:1 margin (+67.7pp vs +1.8pp). The root cause was structural -- evolving a deceptive function (Pop B) is a generative task with many valid outputs, while evolving a general-purpose optimizer (Pop A) is an algorithmic task requiring sophisticated logic. The two tasks had fundamentally different difficulty, producing a lopsided arms race.

This experiment tests whether a **structurally different adversarial dynamic** -- the Prover/Improver pattern -- avoids this asymmetry on a well-defined combinatorial optimization problem.

### The Heilbronn triangle problem

Place 11 points inside a unit-area equilateral triangle (vertices A=(0,0), B=(1.5197,0), C=(0.7598,1.3161)) to maximize the minimum triangle area among all C(11,3) = 165 triplets. The target is min_area >= 0.0365. This is a hard combinatorial geometry problem with a sharp, rugged fitness landscape: small perturbations can dramatically change which triplet is the worst, local optima are plentiful, and no closed-form solution is known for n=11.

### The Prover/Improver dynamic (GAN analogy)

The two populations play complementary roles, analogous to a Generative Adversarial Network:

- **Pop A (Constructors, "Generator")**: Evolve programs that produce (11,2) point configurations. These programs are rewarded for *both* raw quality (high min_area) *and* resistance to improvement by opponents.
- **Pop B (Improvers, "Discriminator")**: Evolve programs that take an existing configuration and improve it (increase min_area). These programs are rewarded for finding improvements that Constructors failed to find -- proving that opponent configurations are suboptimal.

The key insight: this is **zero-sum at the margin**. Every improvement an Improver finds on a Constructor's configuration simultaneously lowers the Constructor's resistance score and raises the Improver's fitness. The Constructor must evolve toward genuine local optima where no perturbation strategy can increase min_area. The Improver must evolve increasingly powerful optimization heuristics to find improvements that simpler methods miss.

Unlike the optimizer-vs-landscape experiment where the two tasks had vastly different difficulty (generating functions vs. writing algorithms), the Prover/Improver pattern ensures both populations face comparable challenges: Pop A must solve a hard placement problem; Pop B must solve a hard local improvement problem. Both operate over the same 22-dimensional space (11 points x 2 coordinates). Neither task is trivially reducible to the other.

### Why `actual_fitness` is critical

This is the **first GigaEvo experiment with a tracked `actual_fitness` metric that is distinct from the adversarial `fitness`**. The adversarial `fitness` (0.5 * quality + 0.5 * resistance) drives MAP-Elites selection but is non-stationary -- its meaning changes as opponents evolve. The `actual_fitness` (raw min_area) is the **ground-truth scientific metric**: it measures absolute progress on the Heilbronn problem regardless of opponent strength. All primary scientific claims use `actual_fitness`; `fitness` is an internal selection signal only.

**Primary research question**: Does the Prover/Improver adversarial dynamic produce an arms race where Constructor `actual_fitness` (raw min_area) improves over generations, driven by adversarial pressure from co-evolving Improvers?

**Secondary research questions**:
1. Does the Prover/Improver dynamic avoid the 37:1 asymmetry observed in the optimizer-vs-landscape experiment?
2. Do Improvers develop increasingly powerful optimization strategies over generations (qualitative)?
3. Does Constructor resistance increase over time, indicating convergence toward genuine local optima?
4. What is the best `actual_fitness` (min_area) achieved, and how does it compare to the 0.0365 target?

---

## 2. Hypotheses

### H1: Primary -- actual_fitness improvement (SCIENTIFIC)

**H0 (null)**: Adversarial co-evolution does NOT improve Constructor `actual_fitness`. The frontier `actual_fitness` at the final generation is no better than at generation 1:

    actual_fitness_final - actual_fitness_gen1 <= 0

averaged across replicate pairs.

**H1 (alternative)**: Adversarial co-evolution improves Constructor `actual_fitness`:

    actual_fitness_final - actual_fitness_gen1 > 0

averaged across replicate pairs.

**Note**: `actual_fitness` is the raw min_area value (not the adversarial fitness). This is the paper-reportable metric. Improvement here means Constructors are producing objectively better Heilbronn configurations over time.

### H2: Arms race -- both populations improve

**H0**: At least one population shows no adversarial `fitness` improvement between generation 1 and the final generation.

**H2 (alternative)**: Both populations show adversarial `fitness` improvement. Pop A frontier `fitness` increases AND Pop B frontier `fitness` increases from gen 1 to the final gen, averaged across replicate pairs.

### H3: Convergence -- resistance increases over time

**H0**: Constructor resistance does not increase over generations.

**H3 (alternative)**: Constructor frontier `resistance` at the final generation exceeds resistance at generation 5 (after cold-start effects dissipate), indicating that Constructors are converging toward genuine local optima that Improvers cannot easily break.

### Effect-size thresholds for `actual_fitness`

Since `actual_fitness` is measured in min_area units (range approximately 0.001 to 0.0365), thresholds are in absolute units:

| Pop A `actual_fitness` improvement (mean across pairs) | Verdict |
|--------------------------------------------------------|---------|
| Both pairs >= +0.010 | **STRONG POSITIVE** -- approaching Heilbronn target |
| Both pairs >= +0.005 | **POSITIVE** -- adversarial pressure materially helps |
| One pair improves >= +0.005, other does not | **SUGGESTIVE** -- inconsistent across replicates |
| Neither pair improves >= +0.005 | **NULL** -- adversarial pressure does not help |

| Pop A best `actual_fitness` achieved | Interpretation |
|--------------------------------------|---------------|
| >= 0.030 | Excellent -- within striking distance of 0.0365 target |
| >= 0.020 | Good -- significant improvement over grid seed |
| >= 0.010 | Moderate -- basic improvement |
| < 0.010 | Poor -- not much progress beyond seed |

### Symmetry assessment (addresses optimizer-coevo finding)

| Pop A/Pop B fitness improvement ratio | Verdict |
|---------------------------------------|---------|
| Both pairs in [0.2, 5.0] | **BALANCED** -- Prover/Improver avoids the 37:1 problem |
| Either pair outside [0.2, 5.0] | **ASYMMETRIC** -- structural fix insufficient |

### Infrastructure validation thresholds

| Metric | Threshold | Interpretation |
|--------|-----------|---------------|
| Generation parity (max gen gap within pair) | <= 2 | MainRunSyncHook working |
| n_opponents at gen 1 | > 0 for both populations | FetchOpponentResultsStage functional |
| n_opponents at gen 5 | >= 3 for both populations | Opponent archive growing |
| Both populations reach max_generations | YES | No deadlocks or infinite waits |
| `actual_fitness` tracked and distinct from `fitness` | YES | Dual-metric infrastructure works |

---

## 3. Independent Variable(s)

This is a **single-condition experiment** (adversarial co-evolution with Prover/Improver dynamic). There is no non-adversarial control arm.

| Variable | Value | Notes |
|----------|-------|-------|
| **Co-evolution mode** | Adversarial (`pipeline=adversarial_coevo`) | Both populations evaluate against live opponent archive |
| **Pop A task** | `heilbron_adversarial/pop_a` | Evolves Constructor programs: `entrypoint() -> (11,2) ndarray` |
| **Pop B task** | `heilbron_adversarial/pop_b` | Evolves Improver programs: `entrypoint() -> improve(points) -> (11,2) ndarray` |
| **Adversarial dynamic** | Prover/Improver (GAN-like) | Pop B proves Pop A suboptimal by constructing improvements |
| **Coupling** | Lockstep via MainRunSyncHook | Each population waits for opponent to advance before next generation |

### Rationale for no control arm

1. **This experiment validates a concept**, not compares treatments. The question is whether the Prover/Improver dynamic produces a balanced arms race and improves `actual_fitness`, not whether it outperforms a static baseline.
2. **No prior Heilbronn experiments exist in GigaEvo.** There is no established baseline to compare against. The non-adversarial `problems/heilbron/` exists but has never been run as an experiment.
3. **Resource efficiency.** Adding a static control (Pop A evolving against fixed Improvers) doubles compute cost for a PoC.
4. **Pre-committed follow-up.** If this PoC succeeds, a controlled comparison (adversarial vs static evolution on Heilbronn) is the natural next experiment.

---

## 4. Dependent Variable(s)

| Metric | Population | How measured | Primary? |
|--------|------------|-------------|----------|
| **`actual_fitness`** (raw min_area) | Pop A | `valid_frontier_actual_fitness` from Redis | **YES -- PRIMARY SCIENTIFIC METRIC** |
| `fitness` (adversarial: 0.5*quality + 0.5*resistance) | Pop A | `valid_frontier_fitness` from Redis | No -- internal selection signal only |
| `quality` (normalized min_area / 0.0365) | Pop A | `valid_frontier_quality` from Redis | Secondary -- component of adversarial fitness |
| `resistance` (1 - mean normalized improvement) | Pop A | `valid_frontier_resistance` from Redis | Secondary -- H3 convergence diagnostic |
| `mean_improvement` (raw delta in min_area units) | Pop A | `valid_program_mean_improvement` per program | Secondary -- arms race dynamic |
| `best_post_improvement` (best min_area opponents achieve) | Pop A | Per-program metric | Secondary |
| `fitness` (mean normalized improvement) | Pop B | `valid_frontier_fitness` from Redis | Secondary -- Improver population fitness |
| `actual_fitness` (best post-improvement min_area) | Pop B | `valid_frontier_actual_fitness` from Redis | Secondary -- Improver quality |
| `mean_pre_quality` / `mean_post_quality` | Pop B | Per-program metrics | Secondary -- improvement margin |
| `n_opponents` | Both | Per-program metric from evaluate.py | Infrastructure validation |
| Invalidity rate | Both | programs_invalid_count / programs_total_count | Diagnostic |
| Generation parity (max gen gap within pair) | Per pair | `engine:total_generations` from both runs | Infrastructure validation |
| Wall-clock time per generation | Both | Timestamps from Redis metrics history | Throughput diagnostic |

**Primary metric**: Pop A frontier `actual_fitness` (raw min_area) improvement from generation 1 to the final generation. This is the ground-truth measure of whether adversarial co-evolution produces better Heilbronn configurations.

**Critical distinction**: `fitness` drives MAP-Elites selection but is adversarial and non-stationary. `actual_fitness` is the absolute, stationary, paper-reportable metric. When this document refers to "improvement" in the context of scientific claims, it means `actual_fitness`. When it refers to "adversarial fitness," it means the composite `fitness = 0.5 * quality + 0.5 * resistance`.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| `pipeline` | `adversarial_coevo` | Required for adversarial infrastructure (validated in PR #169) |
| `max_generations` | 20 | Evaluations are CPU-only (numpy + optional scipy); 20 gens sufficient for signal |
| `max_elites_per_generation` | 8 | Default MAP-Elites config |
| `max_mutations_per_generation` | 8 | With num_parents=1: C(8,1) = 8 mutations/gen |
| `num_parents` | 1 | Single-parent mutation, consistent with all GigaEvo experiments |
| `mutation_mode` | `rewrite` | Full program rewrite per mutation |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 via LiteLLM proxy (10.232.30.185:4000) | Shared across all runs |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` | Explicit override |
| `llm_base_url` | `http://10.232.30.185:4000/v1` | LiteLLM proxy for load-balanced mutation |
| MAP-Elites archive | Single island (fitness_island), 150 bins | Default configuration |
| `n_opponents` | 5 | Opponents sampled per evaluation (from adversarial_coevo.yaml) |
| `per_opponent_timeout` | 60.0s | **Generous** -- allows scipy.optimize and multi-start local search within Improver programs |
| `stage_timeout` | 3000 | Standard GigaEvo config |
| `dag_timeout` | 7200 | Standard GigaEvo config |
| Sync hook timeout | 7200s | MainRunSyncHook waits up to 2h for opponent advancement |
| Sync hook `poll_interval` | 5.0s | Polling frequency for opponent generation counter |
| `cache_ttl` (opponent provider) | 30.0s | Opponent archive refresh interval |
| ALPHA (fitness blend) | 0.5 | Equal weight to quality and resistance (Pop A evaluate.py) |
| Q_MAX (normalization target) | 0.0365 | Known Heilbronn target for n=11 |
| Cold start (Pop A) | 2 fallback Improvers: jitter (30 rounds, sigma=0.01) and local_search (Nelder-Mead, 500 iters) | Provide initial adversarial pressure at gen 0 |
| Cold start (Pop B) | 3 fallback Constructors: grid, random, fan configurations | Provide initial configs for Improvers to practice on at gen 0 |
| Allowed libraries | numpy, scipy, sklearn, standard library | Specified in task_description.txt for both populations |

### `per_opponent_timeout` = 60s rationale

Pop B Improvers can use `scipy.optimize.minimize`, basin-hopping, simulated annealing, and multi-start local search. These algorithms need substantial wall time to converge on a 22-dimensional optimization problem (11 points x 2 coordinates). The 10s timeout used in optimizer-coevo was appropriate for simple function evaluations but would starve sophisticated Improver strategies. 60s is generous enough for Nelder-Mead (~500 iterations), basin-hopping (~10 restarts), or targeted perturbation strategies that identify the worst triplet and optimize its vertices.

---

## 6. Run Design Table

Each "run" is a **co-evolution pair**: two coupled GigaEvo processes (Pop A + Pop B) sharing a Redis-mediated adversarial loop. Populations within a pair interact via FetchOpponentResultsStage; populations across pairs are completely independent (different Redis DBs, no shared state).

| Pair | Pop | Label | `problem.name` | `redis.db` | `opponent_redis_db` | `opponent_redis_prefix` | Role |
|------|-----|-------|-----------------|------------|---------------------|-------------------------|------|
| 1 | A | P1-A | `heilbron_adversarial/pop_a` | 1 | 2 | `heilbron_adversarial/pop_b` | Constructor ("Generator") |
| 1 | B | P1-B | `heilbron_adversarial/pop_b` | 2 | 1 | `heilbron_adversarial/pop_a` | Improver ("Discriminator") |
| 2 | A | P2-A | `heilbron_adversarial/pop_a` | 3 | 4 | `heilbron_adversarial/pop_b` | Constructor ("Generator") |
| 2 | B | P2-B | `heilbron_adversarial/pop_b` | 4 | 3 | `heilbron_adversarial/pop_a` | Improver ("Discriminator") |

**Total**: 4 GigaEvo processes (2 pairs x 2 populations), using Redis DBs 1-4.

### Shared overrides for all 4 processes

```
pipeline=adversarial_coevo
max_generations=20
llm_base_url=http://10.232.30.185:4000/v1
model_name=Qwen3-235B-A22B-Thinking-2507
num_parents=1
max_elites_per_generation=8
max_mutations_per_generation=8
stage_timeout=3000
dag_timeout=7200
mutation_mode=rewrite
pipeline_builder.per_opponent_timeout=60.0
```

### Per-process overrides

| Process | `problem.name` | `redis.db` | `opponent_redis_db` | `opponent_redis_prefix` |
|---------|-----------------|------------|---------------------|-------------------------|
| P1-A | `heilbron_adversarial/pop_a` | 1 | 2 | `heilbron_adversarial/pop_b` |
| P1-B | `heilbron_adversarial/pop_b` | 2 | 1 | `heilbron_adversarial/pop_a` |
| P2-A | `heilbron_adversarial/pop_a` | 3 | 4 | `heilbron_adversarial/pop_b` |
| P2-B | `heilbron_adversarial/pop_b` | 4 | 3 | `heilbron_adversarial/pop_a` |

### Execution plan

All 4 processes launch simultaneously. The LiteLLM proxy handles mutation LLM load balancing across backend servers. Evaluations are CPU-only (numpy/scipy, no LLM chain calls), so there is no chain server dependency. Each pair is self-contained: P1-A reads only from P1-B's archive (DB 2), never from P2-B (DB 4).

### Redis DB assignments

DBs 1-4. Must be verified empty (0 keys) before launch.

**Pre-launch**: `PYTHONPATH=. python tools/flush.py --db 1 2 3 4 --confirm`

### Combinatorics verification

| Process | num_parents | max_elites | Parent combos | max_mutations | Actual mut/gen |
|---------|:-----------:|:---------:|:-------------:|:-------------:|:--------------:|
| All | 1 | 8 | C(8,1) = 8 | 8 | 8 |

---

## 7. Sample Size Justification

### Design: N=2 replicate pairs, 4 processes total

This is a proof-of-concept validating the Prover/Improver adversarial dynamic on a real combinatorial optimization problem. The primary question is whether the dynamic produces a balanced arms race and improves `actual_fitness`, not whether it outperforms a baseline by a specific margin.

**Why N=2 pairs (not N=1)**:
1. **Reproducibility**: A single pair cannot distinguish a genuine arms race from a lucky trajectory. With N=2, we observe whether the pattern replicates.
2. **Reviewer-2 minimum**: N >= 2 per cell is the floor for any experimental claim in this research program.
3. **Asymmetry comparison**: With N=2, we can compare the fitness improvement ratio (Pop A delta / Pop B delta) across pairs to assess whether the Prover/Improver dynamic is consistently balanced.
4. **Precedent**: The optimizer-coevo experiment (PR #169) used N=2 and showed consistent patterns across both pairs (both showed landscape dominance), validating that N=2 is sufficient for qualitative pattern detection.

**Why not N=3+**: Each pair requires 2 Redis DBs and 2 concurrent processes competing for mutation LLM bandwidth. With 4 processes and 60s per-opponent timeouts, evaluation is already non-trivial. Adding a third pair (6 processes, DBs 1-6) would increase LLM contention at the mutation stage. If the PoC succeeds, a powered follow-up can scale to N=4+.

### Statistical approach for N=2

With N=2 pairs, formal hypothesis testing has very low power. The analysis is primarily **descriptive**:

1. **`actual_fitness` improvement detection**: Report whether Pop A frontier `actual_fitness` increased from gen 1 to final gen in BOTH pairs. If yes in both = reproducible improvement. If yes in one but not the other = non-reproducible.

2. **Effect size**: Report the mean and range of `actual_fitness` improvement across pairs. Compare the best `actual_fitness` achieved against the 0.0365 target.

3. **Symmetry assessment**: Compute fitness improvement ratio (|Pop A adversarial delta| / |Pop B adversarial delta|) for each pair. If ratio is within [0.2, 5.0], the dynamic is balanced.

4. **Paired sign test** (secondary): For each quantity (Pop A `actual_fitness` improvement, Pop B `fitness` improvement, across 2 pairs), all 4 positive gives p = 0.5^4 = 0.0625 < 0.10.

---

## 8. Statistical Test

### Test 1: `actual_fitness` improvement detection (PRIMARY, descriptive)

**Metric**: Pop A frontier `actual_fitness` improvement = `actual_fitness_final_gen` - `actual_fitness_gen1`, computed for each pair.

**Decision rule**: Improvement is declared if BOTH pairs show positive `actual_fitness` improvement.

| Pair 1 delta | Pair 2 delta | Verdict |
|:---:|:---:|---------|
| > 0 | > 0 | **POSITIVE** -- reproducible `actual_fitness` improvement |
| > 0 | <= 0 | **SUGGESTIVE** -- non-reproducible |
| <= 0 | > 0 | **SUGGESTIVE** -- non-reproducible |
| <= 0 | <= 0 | **NULL** -- no `actual_fitness` improvement |

### Test 2: Arms race detection (SECONDARY)

**Metric**: Adversarial `fitness` improvement for BOTH populations (Pop A frontier `fitness` and Pop B frontier `fitness`), gen 1 to final gen.

**Decision rule**: Arms race declared if ALL FOUR improvements (2 pops x 2 pairs) are positive.

### Test 3: Symmetry ratio (SECONDARY -- addresses optimizer-coevo asymmetry)

**Metric**: Per-pair ratio = |Pop A adversarial fitness improvement| / |Pop B adversarial fitness improvement|.

**Assessment**:
- Ratio in [0.2, 5.0] for both pairs: **BALANCED** -- Prover/Improver avoids the 37:1 problem.
- Ratio > 5.0 or < 0.2 in either pair: **ASYMMETRIC** -- structural fix insufficient.
- Report exact ratios for both pairs alongside the optimizer-coevo comparison (37:1).

### Test 4: Resistance trend (EXPLORATORY, H3)

**Metric**: Pop A frontier `resistance` at gen 15-20 vs gen 3-5 (smoothed over window to reduce noise).

**Expected**: Resistance increases over time as Constructors evolve toward genuine local optima.

**Method**: Spearman rank correlation between `resistance` and generation number. Report rho and direction.

### Test 5: Infrastructure validation (PASS/FAIL)

| Check | Pass criterion |
|-------|---------------|
| Generation parity | max(gen_A - gen_B) <= 2 within each pair at all times |
| Opponent flow | n_opponents > 0 for both populations at gen >= 1 |
| Completion | All 4 processes reach max_generations=20 |
| No deadlocks | No process blocks for > 30 minutes on sync hook |
| `actual_fitness` tracked | `actual_fitness` appears in Redis metrics for all 4 processes |
| `actual_fitness` != `fitness` | Values differ for Pop A (quality-resistance blend != raw min_area) |

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Improver saturation via scipy baseline** -- The fallback Improver already uses `scipy.optimize.minimize` (Nelder-Mead, 500 iterations). If this already finds near-optimal improvements on any configuration, evolved Improvers have no room to improve, collapsing the arms race. Pop B fitness would plateau from gen 1. | High | MONITORED. Compare Pop B gen-1 fitness (against fallback configs) with Pop B gen-10+ fitness. If Pop B delta < 0.02 across all generations, Improvers have saturated. However, Nelder-Mead is only one local search strategy -- basin-hopping, simulated annealing, and targeted perturbation (identify the worst triplet, move its vertices) may find improvements that Nelder-Mead misses. The 60s timeout enables these heavier strategies. If saturation occurs, it is itself a finding: scipy-grade local search is sufficient for Heilbronn improvement, and the adversarial arms race is limited by the improvement ceiling. |
| 2 | **Cold start asymmetry** -- Gen 0 uses fallback opponents. Pop A has 2 fallback Improvers (jitter, local_search); Pop B has 3 fallback Constructors (grid, random, fan). The number, quality, and diversity of fallbacks differ between populations. | Medium | ACCEPTED. Gen 0 is excluded from the primary analysis (improvement measured from gen 1, when real cross-play begins). By gen 1, both populations have real opponents from the co-evolved archive. The asymmetry in fallback count (2 vs 3) affects only the cold-start generation. |
| 3 | **Non-stationary adversarial fitness** -- `fitness` changes meaning as opponents evolve. A fitness of 0.8 at gen 5 may represent a different difficulty level than 0.8 at gen 15 (if opponents have evolved). Raw fitness trajectory is not directly comparable across generations. | Medium | MITIGATED by design. This is exactly why `actual_fitness` (raw min_area) exists as a separate, stationary metric. All scientific claims use `actual_fitness`, not adversarial `fitness`. The adversarial `fitness` is reported only for arms race dynamics analysis. |
| 4 | **Alpha sensitivity** -- ALPHA=0.5 gives equal weight to quality and resistance. If quality dominates, Constructors optimize for raw min_area while ignoring resistance (weak adversarial pressure). If resistance dominates, Constructors produce low-quality but hard-to-improve configurations (degenerate local optima). | Medium | ACCEPTED for PoC. ALPHA=0.5 is the natural symmetric choice. Track `quality` and `resistance` separately to diagnose whether one dominates. If post-hoc analysis shows severe decoupling, a follow-up can test ALPHA in {0.3, 0.5, 0.7}. |
| 5 | **Evaluation noise from opponent sampling** -- Each program is evaluated against 5 opponents sampled from the archive. Different programs within the same generation may face different opponent subsets, introducing noise in resistance and improvement estimates. | Medium | ACCEPTED. n_opponents=5 balances evaluation cost against noise. With the 60s per-opponent timeout, evaluating 5 opponents costs up to 300s per program. By gen 10, archive has ~50+ programs (8 elites/gen x 10 gens), so sampling 5/50 introduces moderate variance. Noise is symmetric across both populations and both pairs. |
| 6 | **Lockstep throughput loss** -- If Pop B (Improvers) takes longer per evaluation than Pop A (Constructors) due to the 60s optimization budget, Pop A idles waiting for Pop B to finish each generation. | Medium | MONITORED. Track wall-clock time per generation for both populations. Asymmetry is expected: Pop A evaluation runs 5 Improvers (each up to 60s), while Pop B evaluation just fetches 5 configs (instant). Pop A's FetchOpponentResultsStage is the bottleneck, not Pop B's. If throughput asymmetry exceeds 3x, report as a finding. |
| 7 | **LLM prior on optimization algorithms** -- Qwen3-235B has strong knowledge of scipy, gradient descent, CMA-ES, particle swarm, etc. Pop B (Improvers) may converge quickly to standard scipy patterns. Pop A (Constructors) may converge to known good lattice configurations from the optimization literature. | Low | ACCEPTED. LLM prior knowledge accelerating evolution is a feature, not a bug. The question is whether adversarial pressure pushes beyond what LLM prior alone would produce. |
| 8 | **Quality-resistance decoupling** -- A Constructor could have high quality (good min_area) but low resistance (easily improved), or low quality but high resistance (stuck at a bad local optimum). The blended fitness may not always select for the most scientifically interesting programs. | Low | MONITORED. Track `quality` and `resistance` frontiers separately. If the best-by-`actual_fitness` program has very low resistance, it means opponents can improve it further -- the Constructor has not reached a true local optimum. This is itself informative about the optimization landscape. |

---

## 10. Stop Criteria

### Normal completion

All 4 processes run to max_generations=20.

### Early termination criteria (per process)

- **Invalidity rate > 80% at gen 5**: Halt the process. The mutation LLM is failing to produce valid programs. Investigate task_description.txt clarity.
- **`actual_fitness` = 0.0 or `fitness` = -1.0 for all programs through gen 5**: Halt. evaluate.py is rejecting everything. Likely a bug in the evaluate/validate interface.
- **Sync hook blocks for > 60 minutes**: Halt the blocking process. Diagnose the opponent process first.

### Early completion (whole experiment)

If both populations in BOTH pairs have plateaued (no frontier improvement for >= 5 consecutive generations) AND current gen >= 10, the experiment may be terminated early. Record the final generation and use it for analysis.

### Stagnation diagnostic

If Pop A's `actual_fitness` plateaus while Pop B's `fitness` continues improving, this means Improvers are becoming stronger against configurations that Constructors cannot improve. This is an interesting finding (Improver sophistication exceeds Constructor placement quality), not a termination criterion. Continue to max_generations.

### Run invalidation criteria

A run pair is excluded from the primary analysis if:

1. **Deadlock**: Either population never advances past gen 2 (sync hook failure).
2. **Data loss**: Redis DB flushed or corrupted mid-run.
3. **Config mismatch**: Post-hoc Hydra cfg dump shows `pipeline != adversarial_coevo` or incorrect `opponent_redis_db` / `opponent_redis_prefix`.
4. **PID death before gen 5**: Either process in the pair dies before gen 5 with no recovery.
5. **n_opponents = 0 for all programs at gen 5**: FetchOpponentResultsStage is non-functional.
6. **`actual_fitness` not tracked**: If `actual_fitness` is missing from Redis metrics, the dual-metric infrastructure failed.

If one pair is invalidated, the experiment has N=1 (descriptive only, no replication claim). If both pairs are invalidated, the experiment is UNANSWERABLE -- diagnose and re-run.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| GPU hours | **0** (CPU-only numpy/scipy evaluations) |
| Wall time per pair (20 gens) | ~6-12h (dominated by LLM mutation time + 60s per-opponent timeouts) |
| Total wall time (2 pairs in parallel) | ~12-24h |
| Redis DBs | 4 (DBs 1-4) |
| Chain LLM servers | **None** (no LLM chain calls in evaluation) |
| Mutation LLM | LiteLLM proxy (Qwen3-235B-A22B-Thinking, shared backend servers) |
| Test eval time | **N/A** (`has_test_set: false` -- no held-out test set for Heilbronn) |
| LLM mutation calls | ~640 total (8 mutations/gen x 20 gens x 4 processes) |
| New code required | None -- `heilbron_adversarial/pop_a`, `pop_b`, evaluate.py, helper.py, fallback programs, and adversarial pipeline are already implemented |

### Cost breakdown per pair per generation

| Step | Estimated time | Resource | Notes |
|------|---------------|----------|-------|
| LLM mutation (8 mutations per pop) | ~2-8 min | Mutation LLM | Bottleneck; 1-3 min per mutation |
| CallProgramFunction (Pop A: generate points) | ~0.1-1s | CPU | Pure numpy |
| CallProgramFunction (Pop B: return improve callable) | ~0.1s | CPU | Returns a function object |
| FetchOpponentResultsStage (Pop A: run 5 Improvers on config) | 5-300s | CPU | Up to 60s each; most finish in 5-30s |
| FetchOpponentResultsStage (Pop B: fetch 5 configs) | ~instant | CPU | Just reads (11,2) arrays from Redis |
| CallValidatorFunction (evaluate.py cross-play scoring) | ~0.1-5s | CPU | Computes min_area, deltas, fitness |
| Sync hook wait | 0-300s | Idle | Waiting for opponent to finish its generation |

**Bottleneck**: LLM mutation dominates wall time. Per-opponent execution on Pop A's side can take up to 300s (5 opponents x 60s each), but most Improvers will finish well under the timeout. The sync hook wait depends on how closely the two populations track in throughput.

---

## 12. Treatment Verification

Since this is a single-condition experiment, treatment verification confirms that the adversarial infrastructure is correctly wired and that the dual-metric system (`fitness` vs `actual_fitness`) is operational.

### Observable evidence

| Check | Type | Expected | Applies to |
|-------|------|----------|------------|
| `pipeline` in Hydra cfg | `config_override` | `adversarial_coevo` | All 4 processes |
| `opponent_redis_db` in Hydra cfg | `config_override` | 2 (P1-A), 1 (P1-B), 4 (P2-A), 3 (P2-B) | Per-process |
| `opponent_redis_prefix` in Hydra cfg | `config_override` | Correct opponent prefix | Per-process |
| `pipeline_builder.per_opponent_timeout` | `config_override` | 60.0 | All 4 processes |
| FetchOpponentResultsStage in DAG | `dag_structure` | Present as a pipeline stage | All 4 processes |
| MainRunSyncHook in engine | `config_override` | `pre_step_hook._target_` = `...MainRunSyncHook` | All 4 processes |
| n_opponents > 0 at gen >= 1 | `runtime_metric` | > 0 | All 4 processes |
| `actual_fitness` metric present | `runtime_metric` | Tracked in Redis metrics history | All 4 processes |
| `actual_fitness` != `fitness` for Pop A | `runtime_metric` | Values differ (blend != raw min_area) | Pop A processes |
| resistance < 1.0 from gen 1 | `runtime_metric` | Opponents found improvements | Pop A processes |
| Generation counter advances | `runtime_metric` | gen increases to max_generations | All 4 processes |

### Gen-0 diagnostic (verify after launch)

- Pop A gen-0 `actual_fitness` in reasonable range (0.001 to 0.020 for a grid seed)
- Pop A gen-0 `resistance` < 1.0 (fallback Improvers found improvements on the grid seed)
- Pop B gen-0 `fitness` > 0 (seed Improver achieved some improvement on fallback configs)
- n_opponents = 2 for Pop A at gen 0 (2 fallback Improvers: jitter + local_search)
- n_opponents = 3 for Pop B at gen 0 (3 fallback Constructors: grid + random + fan)

---

## Appendix A: Fitness Formulas

### Pop A (Constructor, "Generator")

```
quality         = min(min_area(points) / 0.0365, 1.0)
delta_k         = max(min_area(I_k(points)) - min_area(points), 0.0)
resistance      = 1.0 - mean_k(min(delta_k / 0.0365, 1.0))
fitness         = 0.5 * quality + 0.5 * resistance
actual_fitness  = min_area(points)  [raw, stationary, for paper]
```

Where:
- `points` = (11, 2) ndarray from the Constructor program's `entrypoint()`
- `I_k` = k-th opponent Improver callable (from Pop B archive or fallback)
- `min_area(X)` = minimum triangle area among all C(11,3) = 165 triplets of X
- `0.0365` = Q_MAX normalization target for n=11
- Cold start (no opponents): `fitness = quality`, `resistance = 1.0`

### Pop B (Improver, "Discriminator")

```
delta_k         = max(min_area(improve(P_k)) - min_area(P_k), 0.0)
fitness         = mean_k(min(delta_k / 0.0365, 1.0))
actual_fitness  = max_k(min_area(improve(P_k)))  [best absolute result achieved]
```

Where:
- `improve` = callable returned by the Improver program's `entrypoint()`
- `P_k` = k-th opponent Constructor's (11,2) point configuration (from Pop A archive or fallback)
- Cold start (no opponents): INVALID (Improvers require opponent configs to evaluate against)

### Zero-sum coupling

For each (Constructor config, Improver callable) evaluation pair:
```
resistance_contribution = 1.0 - min(delta / Q_MAX, 1.0)
improvement_contribution = min(delta / Q_MAX, 1.0)

resistance_contribution + improvement_contribution = 1.0  [always]
```

When an Improver finds a large delta (improvement), the Constructor's resistance drops by the same normalized amount. This zero-sum mechanism creates the adversarial pressure that pushes Constructors toward genuine local optima.

---

## Appendix B: Comparison with optimizer-coevo (PR #169)

| Dimension | optimizer-coevo (PR #169) | heilbron-prover (this experiment) |
|-----------|---------------------------|-----------------------------------|
| Domain | 5D function optimization | 2D point placement (22 variables) |
| Pop A task | Evolve optimizer algorithm | Evolve point configuration |
| Pop B task | Evolve deceptive function | Evolve improvement operator |
| Task symmetry | LOW -- generating functions is easy, writing algorithms is hard | HIGH -- both optimize over same geometric space |
| Observed asymmetry | 37:1 (landscapes +67.7pp, optimizers +1.8pp) | TBD |
| `actual_fitness` | Not tracked (adversarial fitness was the only metric) | **Tracked separately** -- raw min_area (stationary) |
| `per_opponent_timeout` | 10s | 60s (allows scipy optimization) |
| Evaluation cost | Milliseconds (pure Python math) | Seconds to minutes (scipy in Improvers) |
| Allowed libraries | Pure Python + math only | numpy, scipy, sklearn |
| Cold start (Pop A) | 3 static landscapes | 2 Improver programs (jitter, local_search) |
| Cold start (Pop B) | 3 static optimizers | 3 Constructor configs (grid, random, fan) |

The key structural difference: in optimizer-coevo, Pop A (optimizers) had to write algorithms while Pop B (landscapes) just generated functions -- a fundamental task-type mismatch. In heilbron-prover, both populations operate on the same geometric space (11 points in a triangle). Pop A produces configurations; Pop B transforms configurations. The complexity is comparable: Pop A must solve a global placement problem; Pop B must solve a local improvement problem. Neither is trivially reducible to the other.

---

## Appendix C: Decision Tree

```
After gen-20 evaluations for both pairs:

  For each pair k in {1, 2}:
    delta_actual_k  = frontier_actual_fitness_A_gen20 - frontier_actual_fitness_A_gen1
    delta_A_k       = frontier_fitness_A_gen20 - frontier_fitness_A_gen1
    delta_B_k       = frontier_fitness_B_gen20 - frontier_fitness_B_gen1
    ratio_k         = |delta_A_k| / |delta_B_k|   [symmetry ratio]

  Step 1: Infrastructure validation
    All 4 processes reached gen 20?
    n_opponents > 0 at gen 1 for all 4 processes?
    actual_fitness tracked for all 4 processes?
    Max gen gap <= 2 within each pair?
    YES -> proceed to Step 2
    NO  -> INFRASTRUCTURE FAILURE -- diagnose before interpreting metrics

  Step 2: actual_fitness improvement detection (PRIMARY)
    Both delta_actual_1 > 0 AND delta_actual_2 > 0?
    YES -> POSITIVE (reproducible actual_fitness improvement); proceed to Step 3
    NO  -> check details

    If one positive, one non-positive:
      -> SUGGESTIVE (non-reproducible; need N=4)
    If both non-positive:
      -> NULL (adversarial pressure does not improve Heilbronn configs)

  Step 3: Effect-size classification (if POSITIVE)
    mean_delta_actual = (delta_actual_1 + delta_actual_2) / 2
    best_actual = max(frontier_actual_fitness across all Pop A processes)

    mean_delta_actual >= 0.010?     -> STRONG POSITIVE
    mean_delta_actual >= 0.005?     -> POSITIVE
    mean_delta_actual > 0?          -> WEAK POSITIVE
    best_actual >= 0.0365?          -> TARGET REACHED (headline result)

  Step 4: Symmetry assessment (addresses optimizer-coevo finding)
    Both ratio_1 and ratio_2 in [0.2, 5.0]?
    YES -> BALANCED -- Prover/Improver avoids 37:1 asymmetry
    NO  -> ASYMMETRIC (report which population dominated and by how much)

  Step 5: Arms race classification
    All 4 adversarial deltas (delta_A_1, delta_A_2, delta_B_1, delta_B_2) > 0?
    YES -> FULL ARMS RACE (both populations improve in both pairs)
    NO  -> check which deltas are negative

    If all Pop A deltas > 0 but some Pop B deltas <= 0:
      -> Constructors improve, Improvers stagnate (possible Improver saturation)
    If all Pop B deltas > 0 but some Pop A deltas <= 0:
      -> Improvers improve, Constructors stagnate
    If mixed:
      -> NO CONSISTENT PATTERN

  Step 6: Qualitative analysis
    Inspect best Pop A Constructor at gen 20:
      - Does it use geometric optimization (lattice structures, symmetry)?
      - Does it exhibit structural properties (boundary utilization, uniform spacing)?
      - Compare min_area vs grid seed min_area.
    Inspect best Pop B Improver at gen 20:
      - Does it use sophisticated strategies (targeted worst-triplet fix,
        basin-hopping, simulated annealing, multi-start)?
      - Or just variations on random jitter?
      - How does it compare to the fallback local_search.py (Nelder-Mead)?

  Step 7: Next experiment decision
    STRONG POSITIVE + BALANCED    -> Paper claim validated; apply to NLP domain
    POSITIVE + BALANCED           -> Prover/Improver works; try more gens or larger archive
    POSITIVE + ASYMMETRIC         -> Partial success; investigate bottleneck population
    SUGGESTIVE                    -> Run N=4 pairs to assess variability
    NULL                          -> Debug evaluate.py; try different ALPHA; consider domain change
    INFRASTRUCTURE FAILURE        -> Fix before any further adversarial experiments
```

---

## Appendix D: Seed and Fallback Program Summary

### Pop A (Constructor) seed: `grid.py`

Places 11 points in a triangular grid pattern (5 rows) with tiny random perturbation (sigma=0.001). This is a reasonable but suboptimal starting configuration: the grid provides regular spacing but is not optimized for the min-area objective. Expected `actual_fitness` (min_area) in the range 0.001-0.010.

### Pop A fallback opponents (2 Improvers, used at gen 0):

1. **`jitter.py`**: 30 rounds of random single-point perturbation (sigma=0.01), greedy accept. Lightweight baseline that can find easy improvements.
2. **`local_search.py`**: Scipy Nelder-Mead on the flattened 22-variable vector (500 iterations, penalty for leaving triangle). More powerful -- can find local optima that jitter misses.

These two provide qualitatively different improvement strategies: stochastic local search vs gradient-free optimization.

### Pop B (Improver) seed: `seed.py`

Random single-point perturbation with greedy accept (50 rounds, sigma=0.02). Simple but provides a baseline improvement capability. Expected to find modest improvements on any non-optimized configuration.

### Pop B fallback opponents (3 Constructor configs, used at gen 0):

1. **`grid.py`**: Triangular grid (same structure as Pop A seed). Regular spacing, moderate quality.
2. **`random_arr.py`**: 11 random points via barycentric sampling. Low quality -- easy to improve.
3. **`fan.py`**: Fan pattern from centroid to edge midpoints. Moderate quality, irregular spacing.

These provide diverse initial configurations for Improvers to practice on during cold start, ranging from easy (random) to moderate (grid, fan) improvement targets.

---

## Appendix E: Code Verification Required Before Launch

1. **Pipeline config**: Verify `config/pipeline/adversarial_coevo.yaml` contains `AdversarialPipelineBuilder`, `RedisOpponentArchiveProvider`, `FetchOpponentResultsStage`, and `MainRunSyncHook` with correct `${opponent_redis_db}` and `${opponent_redis_prefix}` interpolation.

2. **Evaluate.py interface**: Both `pop_a/evaluate.py` and `pop_b/evaluate.py` must accept `(opponent_results, program_output)` and return dicts containing `fitness`, `is_valid`, `actual_fitness`, and `n_opponents`.

3. **`per_opponent_timeout` override**: Verify that `pipeline_builder.per_opponent_timeout=60.0` correctly overrides the default 10.0 in the Hydra cfg dump.

4. **Fallback programs**: Verify all 5 fallback programs execute without error:
   - Pop A fallbacks (2 Improvers): each `entrypoint()` returns a callable `improve(points) -> points`.
   - Pop B fallbacks (3 Constructors): each `entrypoint()` returns an (11, 2) ndarray inside the triangle.

5. **Seed programs**: Verify both seed programs execute and produce valid outputs:
   - Pop A seed (`grid.py`): returns (11, 2) ndarray, all points inside triangle, min_area > 0.
   - Pop B seed (`seed.py`): returns callable `improve(points)` that returns valid (11, 2) ndarray.

6. **Cross-play smoke test**: Run Pop B seed's `improve()` on Pop A seed's output. Verify `min_area(improved) >= min_area(original)` and the improvement is valid (all points inside triangle).

7. **Hydra config verification**: `--cfg job` for all 4 processes confirming: `pipeline: adversarial_coevo`, correct `problem.name`, correct `redis.db`, correct `opponent_redis_db`, correct `opponent_redis_prefix`, `model_name: Qwen3-235B-A22B-Thinking-2507`, `pipeline_builder.per_opponent_timeout: 60.0`.

8. **Redis DBs 1-4**: Must show 0 keys after flush.

---

*Ready for Reviewer-2's scrutiny.*
