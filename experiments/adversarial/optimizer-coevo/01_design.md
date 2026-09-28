# Experimental Design: Adversarial Co-Evolution -- Optimizers vs Deceptive Landscapes

**Date**: 2026-04-06
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft -- awaiting Reviewer-2

---

## 1. Research Question

GigaEvo has run 34 experiments to date, all using a single MAP-Elites population optimized against a static evaluation function. In this paradigm, the fitness landscape is fixed: the same validation set, the same scoring rubric, the same test distribution. Programs that score well on the fixed evaluator stay at the top of the archive forever. There is no selective pressure to produce general, robust solutions -- only ones that fit the specific evaluation harness.

Adversarial co-evolution replaces the static evaluator with a co-evolving adversary. Two MAP-Elites populations compete: Population A evolves black-box optimizers; Population B evolves deceptive optimization landscapes designed to trap those optimizers. Each population's fitness is measured against the current opponent population, not a fixed target. This creates a Red Queen dynamic where both populations must continually improve to maintain their fitness.

This experiment is the **first adversarial co-evolution run in GigaEvo**. It validates (a) the new `pipeline=adversarial_coevo` infrastructure (AdversarialPipelineBuilder, FetchOpponentResultsStage, RedisOpponentArchiveProvider, MainRunSyncHook for lockstep generation advancement), and (b) whether adversarial co-evolution produces an observable arms race on a tractable toy domain.

The domain -- optimizer vs deceptive landscape -- is chosen for tractability: evaluations are pure Python (no LLM chain calls, no external API), each evaluation completes in seconds (not minutes), and the fitness signal is continuous and interpretable (distance-to-optimum for optimizers, distance-from-optimum for landscapes). This makes it possible to run 20 generations in hours rather than days, enabling rapid iteration on the adversarial infrastructure before scaling to more expensive NLP domains.

**Primary research question**: Does adversarial co-evolution between two MAP-Elites populations -- one evolving black-box optimizers, the other evolving deceptive landscapes -- produce an arms race where both populations' fitness improves over generations?

**Secondary research questions**:
1. Does the co-evolution produce qualitatively different programs compared to the fallback seeds (sophisticated optimization strategies vs. simple random search; multi-modal deception vs. shifted Rastrigin)?
2. Does the lockstep synchronization mechanism (MainRunSyncHook) maintain generation parity between the two populations throughout the run?
3. Does the opponent sampling mechanism (FetchOpponentResultsStage reading from opponent's MAP-Elites archive via Redis) produce non-trivial cross-play evaluations (n_opponents > 0 after gen 0)?

---

## 2. Hypotheses

### Primary hypothesis: arms race (H1)

**H0 (null)**: Adversarial co-evolution does NOT produce an arms race. Specifically, at least one of the two populations shows no fitness improvement between generation 1 and the final generation. Formally:

    max(fitness_A_final - fitness_A_gen1, 0) = 0
    OR max(fitness_B_final - fitness_B_gen1, 0) = 0

where fitness_A = Pop A frontier fitness (mean optimization quality across opponent landscapes) and fitness_B = Pop B frontier fitness (mean deceptiveness across opponent optimizers), averaged across replicate pairs.

**H1 (alternative)**: Adversarial co-evolution DOES produce an arms race. Both populations show fitness improvement between generation 1 and the final generation:

    fitness_A_final - fitness_A_gen1 > 0
    AND fitness_B_final - fitness_B_gen1 > 0

averaged across replicate pairs.

### Secondary hypothesis: zero-sum coupling (H2)

**H2**: The fitness trajectories of the two populations are negatively correlated within each pair. When Pop B improves (landscapes become more deceptive), Pop A's fitness temporarily drops (optimizers fail on harder landscapes), and vice versa. This oscillation is the signature of genuine adversarial coupling as opposed to independent improvement.

### Effect-size thresholds

Since this is the first adversarial experiment with no baseline to compare against, we define thresholds relative to the seed (gen 0) performance. The seed optimizer is a naive random-search-plus-local-search; the seed landscape is a shifted Rastrigin with a hidden basin. Both should be easy to improve upon.

| Pop A (optimizer) frontier improvement | Pop B (landscape) frontier improvement | Verdict |
|----------------------------------------|----------------------------------------|---------|
| Both >= +0.15 (15pp) | Both >= +0.15 (15pp) | **STRONG ARMS RACE** -- clear bidirectional improvement |
| Both >= +0.05 (5pp) | Both >= +0.05 (5pp) | **ARMS RACE** -- detectable bidirectional improvement |
| One >= +0.05, other < +0.05 | | **ASYMMETRIC** -- one population improves, other stagnates |
| Both < +0.05 | Both < +0.05 | **NULL** -- no meaningful improvement in either population |
| Either DECREASES by >= 0.10 | | **COLLAPSE** -- co-evolutionary failure (cycling, loss of gradient) |

### Infrastructure validation thresholds

| Metric | Threshold | Interpretation |
|--------|-----------|---------------|
| Generation parity (max gen difference between Pop A and Pop B within a pair) | <= 2 | MainRunSyncHook is working |
| n_opponents at gen 1 | > 0 for both populations | FetchOpponentResultsStage + RedisOpponentArchiveProvider functional |
| n_opponents at gen 5 | >= 3 for both populations | Opponent archive is populated and growing |
| Both populations reach max_generations | YES | No deadlocks, no infinite waits in sync hook |

---

## 3. Independent Variable(s)

This is a **single-condition experiment** (adversarial co-evolution). There is no control condition -- there is no non-adversarial comparison. The experiment validates that the adversarial machinery works and produces an arms race on a toy domain. A future experiment may compare adversarial co-evolution against static evaluation.

| Variable | Value | Notes |
|----------|-------|-------|
| **Co-evolution mode** | Adversarial (pipeline=adversarial_coevo) | Both populations evaluate against live opponent archive |
| **Pop A task** | `adversarial/optimizer_v2/pop_a` | Evolves `optimizer(f, bounds, budget) -> x_best` |
| **Pop B task** | `adversarial/optimizer_v2/pop_b` | Evolves `(objective, bounds, optimum, budget)` tuples |
| **Coupling** | Lockstep via MainRunSyncHook | Each population waits for opponent to advance before its next generation |

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Pop A frontier fitness trajectory (gen 0 to final) | `valid_frontier_fitness` from Redis, per generation | **YES** -- primary arms race indicator for optimizers |
| Pop B frontier fitness trajectory (gen 0 to final) | `valid_frontier_fitness` from Redis, per generation | **YES** -- primary arms race indicator for landscapes |
| Pop A fitness improvement (final - gen 1) | Frontier fitness at final gen minus frontier fitness at gen 1 | **YES** -- primary statistical quantity |
| Pop B fitness improvement (final - gen 1) | Frontier fitness at final gen minus frontier fitness at gen 1 | **YES** -- primary statistical quantity |
| n_opponents per generation (both pops) | `n_opponents` metric from evaluate.py, per program | YES -- infrastructure validation |
| Generation parity (max gen gap within pair) | `engine:total_generations` from both runs in a pair | YES -- sync hook validation |
| Invalidity rate (both pops) | programs_invalid_count / programs_total_count | YES -- program quality diagnostic |
| Pop A best program strategy (qualitative) | Inspect top-1 program source code at final gen | Secondary -- qualitative arms race evidence |
| Pop B best program deception mechanism (qualitative) | Inspect top-1 program source code at final gen | Secondary -- qualitative arms race evidence |
| Within-pair cross-correlation of Pop A / Pop B fitness trajectories | Pearson correlation of per-gen frontier delta series | Secondary -- H2 diagnostic |
| Wall-clock time per generation | Timestamps from Redis metrics history | Secondary -- throughput diagnostic |

**Primary metric**: Fitness improvement from gen 1 to final gen, measured separately for each population, averaged across replicate pairs. Gen 0 is excluded because it uses fallback opponents (cold start); gen 1 is the first generation with real cross-play.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| `pipeline` | `adversarial_coevo` | Required for adversarial infrastructure (FetchOpponentResultsStage + evaluate.py) |
| `max_generations` | 20 | Toy domain -- evaluations are fast (~seconds), 20 gens sufficient for arms race detection |
| `max_elites_per_generation` | 8 | Default MAP-Elites config; shared across all GigaEvo experiments |
| `max_mutations_per_generation` | 8 | With num_parents=1, max_elites=8: C(8,1) = 8 mutations/gen |
| `num_parents` | 1 | Single-parent mutation; consistent with prior experiments |
| `mutation_mode` | `rewrite` | Default; full program rewrite per mutation |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 via LiteLLM proxy (10.232.30.185:4000) | Shared across all runs |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` | Explicit override to avoid OpenRouter default |
| `llm_base_url` | `http://10.232.30.185:4000/v1` | LiteLLM proxy for load-balanced mutation access |
| MAP-Elites archive | Single island (fitness_island), 150 bins | Default configuration |
| `n_opponents` | 5 | Number of opponents sampled per evaluation (from adversarial_coevo.yaml) |
| `per_opponent_timeout` | 10.0s | Timeout per individual opponent execution |
| `stage_timeout` | 3000 | Consistent with standard GigaEvo config |
| `dag_timeout` | 7200 | Consistent with standard GigaEvo config |
| Sync hook timeout | 7200s | MainRunSyncHook waits up to 2h for opponent advancement |
| Sync hook poll_interval | 5.0s | Polling frequency for opponent generation counter |
| `cache_ttl` (opponent provider) | 30.0s | Opponent archive refreshed at most every 30s |
| Cold start | Fallback opponents for gen 0 | Pop A fallback: 3 static landscapes (Rastrigin, Griewank, Schwefel); Pop B fallback: 3 static optimizers (random search, Nelder-Mead, diff evolution) |
| Problem domain | 5-dimensional, bounds [-10, 10] or [-5.12, 5.12], budget 500 | Defined by task_description.txt and seed programs |
| External libraries | None (pure Python + math module only) | Constraint in task_description.txt |

---

## 6. Run Design Table

Each "run" in this experiment is a **co-evolution pair**: two coupled GigaEvo processes (Pop A + Pop B) sharing a Redis-mediated adversarial loop. The two populations within a pair interact via FetchOpponentResultsStage; populations across pairs are completely independent (different Redis DBs, no shared state).

| Pair | Pop | Label | `problem.name` | `redis.db` | `opponent_redis_db` | `opponent_redis_prefix` | Condition |
|------|-----|-------|-----------------|------------|---------------------|-------------------------|-----------|
| 1 | A | P1-A | `adversarial/optimizer_v2/pop_a` | 1 | 2 | `adversarial/optimizer_v2/pop_b` | Co-evolution (optimizer) |
| 1 | B | P1-B | `adversarial/optimizer_v2/pop_b` | 2 | 1 | `adversarial/optimizer_v2/pop_a` | Co-evolution (landscape) |
| 2 | A | P2-A | `adversarial/optimizer_v2/pop_a` | 3 | 4 | `adversarial/optimizer_v2/pop_b` | Co-evolution (optimizer) |
| 2 | B | P2-B | `adversarial/optimizer_v2/pop_b` | 4 | 3 | `adversarial/optimizer_v2/pop_a` | Co-evolution (landscape) |

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
```

### Per-process overrides

| Process | `problem.name` | `redis.db` | `opponent_redis_db` | `opponent_redis_prefix` |
|---------|-----------------|------------|---------------------|-------------------------|
| P1-A | `adversarial/optimizer_v2/pop_a` | 1 | 2 | `adversarial/optimizer_v2/pop_b` |
| P1-B | `adversarial/optimizer_v2/pop_b` | 2 | 1 | `adversarial/optimizer_v2/pop_a` |
| P2-A | `adversarial/optimizer_v2/pop_a` | 3 | 4 | `adversarial/optimizer_v2/pop_b` |
| P2-B | `adversarial/optimizer_v2/pop_b` | 4 | 3 | `adversarial/optimizer_v2/pop_a` |

### Execution plan

All 4 processes launch simultaneously. The LiteLLM proxy handles load balancing across 4 mutation servers. Evaluations are pure Python (no chain server needed), so there is no chain server contention. Each pair is self-contained: P1-A only reads from P1-B's archive (DB 2), not from P2-B (DB 4).

### Redis DB assignments

DBs 1-4. Must be verified empty (0 keys) before launch. These DBs should be available (HoVer experiments used DBs 4-15; adversarial experiments reclaim DBs 1-4).

**Pre-launch**: Flush DBs 1-4 via `PYTHONPATH=. python tools/flush.py --db 1 2 3 4 --confirm`.

### Combinatorics verification

| Process | num_parents | max_elites | Parent combos | max_mutations | Actual mut/gen |
|---------|:-----------:|:---------:|:-------------:|:-------------:|:--------------:|
| All | 1 | 8 | C(8,1) = 8 | 8 | 8 |

---

## 7. Sample Size Justification

### Design: N=2 replicate pairs, 4 processes total

This is a proof-of-concept infrastructure validation experiment, not a treatment-vs-control comparison. The primary question is whether adversarial co-evolution produces an arms race at all (both populations improve), not whether it outperforms a baseline by a specific margin.

**Why N=2 pairs (not N=1)**:
1. **Reproducibility**: A single pair cannot distinguish a genuine arms race from a lucky trajectory. With N=2, we observe whether the arms race pattern replicates.
2. **Reviewer-2 requirement**: N >= 2 per cell is the minimum for any experimental claim in this research program.
3. **Variance estimation**: With N=2, we can compute a (crude) standard deviation of the fitness improvement, bounding the variability of the co-evolutionary dynamic.

**Why not N=3+**: This is a PoC. Each pair requires 2 Redis DBs and 2 concurrent processes competing for mutation LLM bandwidth. With 4 mutation servers and 4 concurrent processes, we are at ~1 process per server. Adding a third pair (6 processes) would introduce LLM contention that could confound timing-sensitive lockstep synchronization. If the PoC succeeds, a powered follow-up can scale to N=4+ with dedicated resources.

### Statistical approach for N=2

With only N=2 pairs, formal hypothesis testing has very low power. Instead, the analysis is primarily **descriptive**:

1. **Arms race detection**: Report whether both populations' frontier fitness increased from gen 1 to final gen in BOTH pairs. If yes in both pairs = reproducible arms race. If yes in one pair but not the other = non-reproducible. If no in both = NULL.

2. **Effect size**: Report the mean and range of fitness improvement across the 2 pairs, separately for Pop A and Pop B.

3. **Paired sign test** (secondary): For each pair, compute (fitness_final - fitness_gen1) for both populations. Under H0 (no improvement), the probability of positive improvement in both populations in both pairs = (0.5)^4 = 0.0625. This is a conservative one-sided p-value without distributional assumptions. If all 4 quantities (2 pops x 2 pairs) are positive, p = 0.0625 < 0.10.

---

## 8. Statistical Test

### Test 1: Arms race detection (PRIMARY, descriptive)

**Metric**: Frontier fitness improvement = fitness_final_gen - fitness_gen1, computed separately for Pop A and Pop B within each pair.

**Decision rule**: Arms race is declared if ALL FOUR improvements (2 populations x 2 pairs) are positive.

**Interpretation table**:

| Pop A Pair 1 | Pop A Pair 2 | Pop B Pair 1 | Pop B Pair 2 | Verdict |
|:---:|:---:|:---:|:---:|---------|
| + | + | + | + | **ARMS RACE** (reproducible) |
| + | + | + | - | Asymmetric / non-reproducible |
| + | - | + | + | Asymmetric / non-reproducible |
| + | + | - | - | Pop A improves, Pop B stagnates |
| - | - | + | + | Pop B improves, Pop A stagnates |
| mixed | mixed | mixed | mixed | **NULL** |

### Test 2: Paired sign test (SECONDARY)

**Test**: One-sided sign test across 4 independent observations (2 pops x 2 pairs).
**Null hypothesis**: P(improvement > 0) = 0.5 for each observation.
**p-value if all 4 positive**: 0.5^4 = 0.0625.
**Significance threshold**: alpha = 0.10 (relaxed for PoC with N=2).

### Test 3: Cross-correlation (EXPLORATORY, H2)

**Metric**: Pearson correlation of per-generation frontier fitness deltas between Pop A and Pop B within each pair.
**Expected sign**: Negative (when Pop B improves, Pop A's fitness temporarily drops).
**Reported descriptively** -- no formal test at N=2.

### Test 4: Infrastructure validation (PASS/FAIL)

| Check | Pass criterion |
|-------|---------------|
| Generation parity | max(gen_A - gen_B) <= 2 within each pair at all times |
| Opponent flow | n_opponents > 0 for both populations at gen >= 1 |
| Completion | All 4 processes reach max_generations=20 |
| No deadlocks | No process blocks for > 30 minutes on sync hook |

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Cold start asymmetry** -- Gen 0 uses fallback opponents (static landscapes for Pop A, static optimizers for Pop B). The quality and diversity of fallbacks determines the initial fitness landscape and may bias early evolution. | Medium | ACCEPTED. Fallbacks are hand-crafted to provide reasonable initial challenge. Pop A fallbacks: 3 classic landscapes (Rastrigin, Griewank, Schwefel) with known optima. Pop B fallbacks: 3 simple optimizers (random search, Nelder-Mead, differential evolution). Gen 0 is excluded from the primary analysis (fitness improvement measured from gen 1, when real cross-play begins). |
| 2 | **Lockstep deadlock** -- If one population stagnates (all mutations invalid), the other blocks forever waiting for it to advance. | Medium | MITIGATED. MainRunSyncHook has a 7200s timeout -- after 2 hours of waiting, the population proceeds anyway. Monitor generation parity at every checkpoint. If one population falls 3+ generations behind, investigate. Toy domain has low invalidity risk (pure Python, no external dependencies). |
| 3 | **LLM contention** -- 4 concurrent processes sharing the LiteLLM proxy (4 mutation servers). Under high load, mutation latency increases and throughput drops. This affects both pairs equally but may slow the experiment. | Low | ACCEPTED. The toy domain's evaluation is CPU-bound (pure Python), not LLM-bound. The mutation LLM is the bottleneck only during mutation generation (1 LLM call per mutation). With 8 mutations/gen and 4 concurrent processes, the proxy handles ~32 mutations per generation cycle across all 4 processes. This is well within the proxy's capacity (4 servers x ~1 req/min each). |
| 4 | **Fitness-proportional sampling bias** -- RedisOpponentArchiveProvider uses fitness-proportional sampling to select opponents. This biases cross-play toward high-fitness opponents, potentially making evaluation harder/easier than uniform sampling. | Low | ACCEPTED by design. Fitness-proportional sampling is intentional: it forces programs to be tested against the strongest opponents, not random ones. This accelerates the arms race by creating stronger selective pressure. |
| 5 | **Opponent cache staleness** -- OpponentArchiveProvider caches opponent programs for 30s. During that window, a population may be evaluated against outdated opponent programs (from the previous generation). | Low | ACCEPTED. The 30s TTL is short relative to generation time (minutes). In the worst case, a few evaluations per generation use slightly outdated opponents. The lockstep mechanism ensures that opponent programs are at most 1 generation behind. |
| 6 | **Evaluation noise from opponent sampling** -- Each program is evaluated against a sample of 5 opponents (not the full archive). Different programs within the same generation may face different opponent subsets, introducing evaluation noise. | Medium | ACCEPTED. n_opponents=5 is a trade-off between evaluation cost and noise. With archive size growing to ~50+ programs by gen 10 (8 elites/gen * 10 gens), sampling 5 out of 50 introduces moderate variance. This noise is symmetric across both populations and both pairs. Monitor fitness trajectory smoothness -- if highly noisy, consider increasing n_opponents in follow-up. |
| 7 | **Program execution isolation** -- Opponent programs are executed via `run_exec_runner` (subprocess sandbox). If an opponent program crashes, hangs, or produces garbage, it counts as a failed evaluation (score 0.0 for optimizer, score 1.0 for landscape). A population of mostly-broken opponents gives the other population artificially high/low fitness. | Low | MITIGATED by validation in evaluate.py. Pop B's evaluate.py validates that the landscape's optimum is actually the minimum (200 random spot-checks). Pop A's evaluate.py checks that the optimizer returns a valid point. Broken programs are excluded from the average. |
| 8 | **Asymmetric difficulty** -- Evolving a good optimizer may be harder than evolving a deceptive landscape (or vice versa). The LLM's prior knowledge of optimization algorithms vs. landscape design may create an inherent asymmetry. | Medium | ACKNOWLEDGED. Qwen3-235B has strong knowledge of optimization algorithms (gradient descent, CMA-ES, particle swarm, etc.) and reasonable knowledge of deceptive functions (Rastrigin, Ackley, Schwefel, etc.). If one population evolves much faster than the other, this reflects a genuine difficulty asymmetry in the domain, not a confound in the experimental setup. Report the asymmetry as a finding. |
| 9 | **Non-stationary fitness** -- Each population's fitness is measured against the current opponent archive, which changes every generation. A fitness of 0.7 at gen 5 may represent a harder challenge than 0.7 at gen 1. The primary metric (fitness_final - fitness_gen1) conflates true improvement with opponent difficulty drift. | High | MITIGATED by (a) qualitative program inspection at gen 1, 10, 20 to verify that strategies genuinely improved, (b) reporting the trajectory as-is with the caveat that difficulty scales with opponent quality, (c) supplementing with cross-evaluation of final programs against fixed benchmark functions (Rastrigin, Schwefel, Griewank) to measure absolute improvement independent of opponent strength. This is inherent to adversarial evaluation and is itself a research finding. |

---

## 10. Stop Criteria

### Early termination criteria (per process)

- **Invalidity rate > 80% at gen 5**: Halt the process; the mutation LLM is failing to produce valid programs for this population. Investigate task_description.txt clarity.
- **Fitness = 0.0 for all programs through gen 5**: Halt; evaluate.py is rejecting everything. Likely a bug in the evaluate/validate interface.
- **Sync hook blocks for > 60 minutes**: Halt the blocking process; the opponent has stalled. Diagnose the opponent process first.

### Early completion (whole experiment)

If both populations in BOTH pairs have plateaued (no frontier improvement for >= 5 consecutive generations) AND current gen >= 10, the experiment may be terminated early. Record the final generation and use it for analysis.

### Stagnation diagnostic

If one population plateaus while the other continues improving, this is an interesting finding (asymmetric arms race), not a termination criterion. Continue to max_generations.

### Run invalidation criteria

A run pair is excluded from the primary analysis if:

1. **Deadlock**: One population never advances past gen 2 (sync hook failure).
2. **Data loss**: Redis DB is flushed or corrupted mid-run.
3. **Config mismatch**: Post-hoc Hydra cfg dump shows `pipeline != adversarial_coevo` or incorrect `opponent_redis_db` / `opponent_redis_prefix`.
4. **PID death before gen 5**: Either process in the pair dies before gen 5 with no recovery.
5. **n_opponents = 0 for all programs at gen 5**: FetchOpponentResultsStage is non-functional.

If one pair is invalidated, the experiment has N=1 and can only report descriptive results (no replication claim). If both pairs are invalidated, the experiment is UNANSWERABLE -- diagnose and re-run.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time per pair (20 gens, toy domain, ~seconds per eval) | ~2-4h (dominated by LLM mutation time, not evaluation) |
| Total wall time (2 pairs in parallel) | ~3-5h |
| Redis DBs | 4 (DBs 1-4) |
| Chain LLM servers | **None** (pure Python evaluation, no chain server needed) |
| Mutation LLM | LiteLLM proxy (Qwen3-235B-A22B-Thinking, 4 backend servers shared) |
| Test eval time | **N/A** (no test set; `has_test_set: false`) |
| New code required | None -- all infrastructure (AdversarialPipelineBuilder, FetchOpponentResultsStage, RedisOpponentArchiveProvider, problem directories, evaluate.py, launch.sh) is already implemented on the `feat/adversarial-coevo` branch |

### Cost breakdown per pair per generation

| Step | Estimated time | Resource |
|------|---------------|----------|
| LLM mutation (8 mutations) | ~2-8 min (1-3 min each, depends on queue) | Mutation LLM |
| CallProgramFunction (execute evolved program) | ~1-5s (pure Python) | CPU |
| FetchOpponentResultsStage (execute 5 opponents) | ~5-50s (5 opponents x 1-10s each) | CPU |
| CallValidatorFunction (evaluate.py cross-play) | ~1-10s (pure Python, 5 opponent results) | CPU |
| Sync hook wait | 0-60s (waiting for opponent to finish its generation) | Idle |

Bottleneck is LLM mutation, not evaluation. With 4 mutation servers and 4 processes, expect ~1 mutation server per process.

---

## 12. Open Questions / Risks

### Priority risks

**Risk 1 -- Mutation LLM cannot evolve effective optimizers (MEDIUM).**
The mutation LLM must generate increasingly sophisticated pure-Python optimization algorithms within a 500-evaluation budget. The task description provides hints (random restarts, adaptive step sizes, population-based approaches), but the LLM may struggle with the no-numpy constraint and the need to implement complex algorithms from scratch.

**Mitigation**: The seed optimizer (random search + local search) is deliberately naive. Even modest improvements (adding restarts, reducing step size more aggressively, implementing a simple genetic algorithm) should produce measurable fitness gains. If Pop A frontier fitness doesn't improve past 0.3 by gen 5, inspect mutations for common failure patterns (numpy imports, budget overuse, etc.).

**Risk 2 -- Mutation LLM cannot evolve deceptive landscapes (MEDIUM).**
Evolving a landscape that is both valid (optimum is the true minimum) and deceptive (optimizers get trapped far away) is a non-trivial constraint satisfaction problem. The validate.py spot-check (200 random points) may reject many attempted landscapes.

**Mitigation**: The seed landscape (shifted Rastrigin with hidden basin) demonstrates the pattern. The LLM should be able to vary the deception strategy (different basin shapes, multiple decoys, different optimum locations). If Pop B invalidity rate > 50% at gen 3, the spot-check may be too strict -- consider relaxing the tolerance in a follow-up.

**Risk 3 -- Co-evolutionary cycling instead of arms race (MEDIUM).**
Classic co-evolutionary failure: populations oscillate between strategies without net improvement. Optimizer A beats Landscape B; Landscape B' beats Optimizer A; Optimizer A' beats Landscape B' but loses to Landscape B; cycle repeats. MAP-Elites diversity should prevent this (multiple strategies survive in different archive cells), but it's not guaranteed.

**Mitigation**: Monitor fitness trajectory for oscillation patterns. If frontier fitness oscillates with period <= 3 generations and no upward trend over 10 generations, cycling is occurring. Report as a finding. MAP-Elites should provide some resilience -- even if the frontier oscillates, the archive should accumulate diverse strategies.

**Risk 4 -- Lockstep synchronization causes throughput loss (LOW-MEDIUM).**
If one population finishes its generation much faster than the other (e.g., Pop B's landscape validation is faster than Pop A's optimizer execution), the faster population idles waiting for the slower one. With 8 mutations/gen and potentially different evaluation times, this could reduce effective throughput by up to 50%.

**Mitigation**: Both populations have similar evaluation pipelines (FetchOpponentResultsStage + CallValidatorFunction). The dominant cost is LLM mutation, which is comparable for both. Monitor wall-clock time per generation for asymmetry. If one population consistently finishes 3x faster, the sync overhead is high but acceptable for a PoC.

**Risk 5 -- Fitness values are not comparable across generations (MEDIUM).**
Pop A's fitness is measured against Pop B's current archive, which changes every generation. A fitness of 0.7 at gen 5 may represent a harder challenge than 0.7 at gen 1 (if Pop B has evolved more deceptive landscapes by gen 5). This makes raw fitness trajectory non-comparable across generations.

**Mitigation**: This is inherent to adversarial evaluation and is part of what we're studying. To address interpretability: (a) Report the trajectory as-is, acknowledging that the difficulty scales with opponent quality. (b) Supplement with qualitative analysis of the best programs at gen 1, gen 10, and gen 20 to show that strategies genuinely improved, not just that difficulty stagnated. (c) In follow-up experiments, evaluate final programs against a fixed benchmark suite (not the co-evolved opponents) to measure absolute improvement.

### Open questions after this experiment

| Result pattern | Interpretation | Next step |
|---------------|----------------|-----------|
| Arms race in both pairs, both populations improve 15pp+ | Infrastructure works; adversarial co-evolution is productive on toy domain | Scale to NLP domain (adversarial test generation for HoVer/HotpotQA) |
| Arms race in both pairs, improvement 5-15pp | Infrastructure works; arms race is detectable but modest | Investigate whether more generations or larger archives produce stronger arms race |
| Arms race in one pair but not the other | Arms race is not reliably reproducible with N=2 | Run N=4 pairs to assess variability; investigate what differs between pairs |
| Pop A improves, Pop B stagnates | LLM is better at evolving optimizers than landscapes | Improve landscape task description; add more landscape seeds; or switch domain |
| Pop B improves, Pop A stagnates | LLM is better at evolving landscapes than optimizers | Improve optimizer task description; add more optimizer seeds |
| Neither improves | Infrastructure may work but domain is too easy/hard; or evaluate.py is broken | Debug evaluate.py scoring; check opponent flow; try different seeds |
| Deadlocks or sync failures | Infrastructure bug | Fix MainRunSyncHook or FetchOpponentResultsStage before any further experiments |

---

## Appendix A: Code Verification Required Before Launch

1. **Pipeline config**: Verify `config/pipeline/adversarial_coevo.yaml` contains `AdversarialPipelineBuilder`, `RedisOpponentArchiveProvider`, `FetchOpponentResultsStage`, and `MainRunSyncHook` with correct `${opponent_redis_db}` and `${opponent_redis_prefix}` interpolation.

2. **Evaluate.py interface**: Both `pop_a/evaluate.py` and `pop_b/evaluate.py` must accept `(opponent_results, program_output)` as arguments and return `{"fitness": float, "is_valid": float, "n_opponents": float}`.

3. **Fallback programs**: Verify all 6 fallback programs execute without error:
   - Pop A fallbacks (3 landscapes): each must return `(objective, bounds, optimum, budget)` tuple from `entrypoint()`.
   - Pop B fallbacks (3 optimizers): each must return a callable `optimizer(f, bounds, budget)` from `entrypoint()`.

4. **Seed programs**: Verify both seed programs execute and return valid outputs:
   - Pop A seed: returns callable optimizer.
   - Pop B seed: returns (objective, bounds, optimum, budget) where objective(optimum) is the minimum.

5. **Cross-play smoke test**: Run Pop A seed against Pop B seed manually. The optimizer should find a point, evaluate.py should compute a distance, and the fitness should be in (0, 1).

6. **Hydra config verification**: `--cfg job` for all 4 processes confirming: `pipeline: adversarial_coevo`, correct `problem.name`, correct `redis.db`, correct `opponent_redis_db`, correct `opponent_redis_prefix`, `model_name: Qwen3-235B-A22B-Thinking-2507`, `num_parents: 1`, `max_elites_per_generation: 8`, `max_mutations_per_generation: 8`, `max_generations: 20`.

7. **Redis DBs 1-4**: Must show 0 keys after flush.

8. **Gen-0 diagnostic**: After launch, verify gen-0 fitness is in expected range [0.1, 0.5] for Pop A (optimizer vs fallback landscapes) and [0.2, 0.8] for Pop B (landscape vs fallback optimizers). n_opponents should equal 3 (fallback count) at gen 0.

---

## Appendix B: Decision Tree

```
After gen-20 evaluations for both pairs:

  For each pair k in {1, 2}:
    delta_A_k = frontier_fitness_A_gen20 - frontier_fitness_A_gen1
    delta_B_k = frontier_fitness_B_gen20 - frontier_fitness_B_gen1

  Step 1: Infrastructure validation
    All 4 processes reached gen 20?
    n_opponents > 0 at gen 1 for all 4 processes?
    Max gen gap <= 2 within each pair?
    YES → proceed to Step 2
    NO  → INFRASTRUCTURE FAILURE — diagnose before interpreting fitness

  Step 2: Arms race detection (PRIMARY)
    All 4 deltas (delta_A_1, delta_A_2, delta_B_1, delta_B_2) > 0?
    YES → ARMS RACE DETECTED (proceed to effect-size classification)
    NO  → check which deltas are negative

    If all Pop A deltas > 0 but some Pop B deltas <= 0:
      → ASYMMETRIC: optimizers improve, landscapes stagnate
    If all Pop B deltas > 0 but some Pop A deltas <= 0:
      → ASYMMETRIC: landscapes improve, optimizers stagnate
    If mixed:
      → NULL (no consistent pattern)

  Step 3: Effect-size classification (if arms race detected)
    mean_delta_A = (delta_A_1 + delta_A_2) / 2
    mean_delta_B = (delta_B_1 + delta_B_2) / 2

    Both >= 0.15?   → STRONG ARMS RACE
    Both >= 0.05?   → ARMS RACE
    Otherwise        → WEAK ARMS RACE (improvement is real but small)

  Step 4: Qualitative analysis
    Inspect best Pop A optimizer at gen 20 vs seed:
      - Did it develop sophisticated strategies (CMA-ES, multi-restart, etc.)?
      - Or just minor variations on random search?
    Inspect best Pop B landscape at gen 20 vs seed:
      - Did it develop novel deception (multiple decoy basins, rugged gradients)?
      - Or just parameter tweaks on shifted Rastrigin?

  Step 5: Next experiment decision
    STRONG ARMS RACE → scale to NLP domain
    ARMS RACE        → scale to NLP domain (with more generations)
    ASYMMETRIC       → investigate bottleneck, improve weaker population's setup
    NULL             → debug infrastructure, try different domain, or close line
```

---

## Appendix C: Treatment Verification Checks

Since this is a single-condition experiment (no control), treatment verification confirms that the adversarial infrastructure is correctly wired, not that treatment differs from control.

| Check | Type | Expected | Process |
|-------|------|----------|---------|
| `pipeline` in Hydra cfg | `config_override` | `adversarial_coevo` | All 4 |
| `opponent_redis_db` in Hydra cfg | `config_override` | 2 (P1-A), 1 (P1-B), 4 (P2-A), 3 (P2-B) | Per-process |
| `opponent_redis_prefix` in Hydra cfg | `config_override` | Correct opponent prefix | Per-process |
| FetchOpponentResultsStage in DAG | `dag_structure` | Present as a stage | All 4 |
| evaluate.py used (not validate.py) | `dag_structure` | CallValidatorFunction calls `evaluate` function | All 4 |
| MainRunSyncHook in engine | `config_override` | `pre_step_hook._target_` = `...MainRunSyncHook` | All 4 |
| n_opponents > 0 at gen >= 1 | `runtime_metric` | > 0 | All 4 |
| Generation counter advances | `runtime_metric` | gen increases to max_generations | All 4 |

---

## Appendix D: Why No Control Condition?

This experiment does not include a non-adversarial control (e.g., optimizers evolving against fixed landscapes, or landscapes evolving against fixed optimizers). The reasons:

1. **Infrastructure validation is the primary goal.** The question is "does the adversarial machinery work at all?" not "does adversarial co-evolution outperform static evolution?" A working PoC is prerequisite to any comparison.

2. **No meaningful baseline exists.** These problem directories (`adversarial/optimizer_v2/pop_a`, `pop_b`) are new. There are no prior runs with `pipeline=standard` on these problems to compare against. Creating a static-evaluation control would require designing a fixed test suite of landscapes/optimizers, which is itself a non-trivial design choice.

3. **Resource efficiency.** Adding a 2-arm comparison (co-evolved vs. static) at N=2 per arm requires 8 additional processes (4 static-pop-A + 4 static-pop-B). This doubles the compute cost for a PoC that may reveal infrastructure bugs requiring a re-run.

4. **Planned follow-up.** If the PoC succeeds (arms race detected), the next experiment will include a static-evaluation control arm to quantify the benefit of adversarial co-evolution over static evaluation. This is pre-committed in the decision tree (Appendix B, Step 5).

---

*Ready for Reviewer-2's scrutiny.*
