# Experimental Design: Adversarial vs Solo MAP-Elites on Heilbronn N=11

**Date**: 2026-04-11
**Researcher**: Volkov
**Status**: Draft

---

## 1. Research Question

Does adversarial co-evolution (Constructor vs Improver) improve actual_fitness (raw min_area) on the Heilbronn N=11 triangle problem compared to standard (non-adversarial) MAP-Elites?

**Context**: Five adversarial experiments (28 runs, ~800 GPU-hours) have established that adversarial co-evolution reliably drives Constructors to 93-100% of Q_MAX (0.0365). However, this has never been compared to standard MAP-Elites without opponents. If solo MAP-Elites achieves comparable actual_fitness, the adversarial overhead (paired runs, sync hooks, opponent evaluation) is unjustified.

This is identified as the HIGHEST PRIORITY experiment in `RESEARCH_STRATEGY.md` (Gap 1, 2026-04-11).

## 2. Hypotheses

**H₀**: There is no difference in Constructor actual_fitness between adversarial co-evolution and solo MAP-Elites.

**H₁**: Adversarial co-evolution produces different Constructor actual_fitness than solo MAP-Elites.

**Practically meaningful difference**: 0.003 (8.7% of baseline). Below this, any difference is not worth the adversarial engineering overhead. Chosen because: (a) comparable to inter-pair SD (0.0026 from baseline-repro), (b) smaller than the gap between best adversarial result (0.03548) and Q_MAX (0.0365). A 0.003 improvement in min_area would shift a solution from 94.5% to 103% of Q_MAX coverage -- the difference between "close" and "solved." The adversarial engineering cost (doubled runs, sync hooks, paired launch, deadlock risk) is only justified by gains at this scale.

## 3. Independent Variable(s)

| Variable | Control value (Solo) | Treatment value (Adversarial) |
|----------|---------------------|------------------------------|
| Evolution mode | Standard MAP-Elites, no opponent | Adversarial co-evolution (Constructor + Improver paired) |

**Single IV**: presence vs absence of adversarial opponent. All other variables held constant.

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Constructor actual_fitness | Best raw min_area from Constructor population at gen 50 | **Yes** |
| Best-overall actual_fitness | Best raw min_area from either Constructor or Improver at gen 50 | Secondary |
| Frontier fitness trajectory | Gen-by-gen best fitness from Redis metrics history | Exploratory |

**Primary metric**: Constructor actual_fitness at gen 50. For solo runs, this is the `fitness` metric (= raw min_area). For adversarial runs, this is the `actual_fitness` metric from the Constructor (Pop A) run only.

**Why Constructor-only is primary**: Taking max(Constructor, Improver) for adversarial inflates the expected value by ~0.56*sigma ~= 0.0015 due to order-statistics bias (taking the max of two correlated observations). This is 50% of the equivalence threshold and would produce a spurious advantage. Constructor-only provides an apples-to-apples comparison: one population's best solution vs one population's best solution.

**Secondary: best-overall** tracks max(Constructor, Improver) as before, for continuity with baseline-repro reporting.

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| `max_generations` | 50 | Match heilbron-prover and baseline-repro |
| `max_elites_per_generation` | 8 | Match heilbron-prover |
| `max_mutations_per_generation` | 8 | Match heilbron-prover |
| `mutation_mode` | rewrite | Match heilbron-prover |
| `model_name` | Qwen3-235B-A22B-Thinking-2507 | Same mutation LLM for both arms |
| `llm_base_url` | http://10.232.30.185:4000/v1 | Same LiteLLM proxy |
| `temperature` | 0.6 | Match heilbron-prover |
| `max_tokens` | 81920 | Match heilbron-prover |
| `island_max_size` | 75 | Match heilbron-prover |
| `primary_resolution` | 150 | Match heilbron-prover |
| `num_parents` | 1 | Match heilbron-prover |
| `stage_timeout` | 3000 | Match heilbron-prover |
| `dag_timeout` | 7200 | Match heilbron-prover |
| Initial seed program | `grid.py` (identical across all runs) | Eliminate seed diversity confound |
| `helper.py` | Identical between solo and adversarial | Verified: `diff` shows no difference |
| Engine type | Generational (`EvolutionEngine`) | Match heilbron-prover; confirmed pattern: simpler is better |

## 6. Run Design Table

### Arm A: Solo MAP-Elites (4 runs)

| Run | Label | `redis.db` | `pipeline` | `problem.name` | Seed |
|-----|-------|------------|-----------|----------------|------|
| 1 | S1 | TBD | standard | heilbron_solo | grid.py |
| 2 | S2 | TBD | standard | heilbron_solo | grid.py |
| 3 | S3 | TBD | standard | heilbron_solo | grid.py |
| 4 | S4 | TBD | standard | heilbron_solo | grid.py |

### Arm B: Adversarial Co-Evolution (4 pairs = 8 runs)

| Run | Label | `redis.db` | `pipeline` | `problem.name` | Seed | Opponent |
|-----|-------|------------|-----------|----------------|------|---------|
| 1a | A1_C | TBD | adversarial_coevo | heilbron_adversarial/pop_a | grid.py | A1_I |
| 1b | A1_I | TBD | adversarial_coevo | heilbron_adversarial/pop_b | seed.py | A1_C |
| 2a | A2_C | TBD | adversarial_coevo | heilbron_adversarial/pop_a | grid.py | A2_I |
| 2b | A2_I | TBD | adversarial_coevo | heilbron_adversarial/pop_b | seed.py | A2_C |
| 3a | A3_C | TBD | adversarial_coevo | heilbron_adversarial/pop_a | grid.py | A3_I |
| 3b | A3_I | TBD | adversarial_coevo | heilbron_adversarial/pop_b | seed.py | A3_C |
| 4a | A4_C | TBD | adversarial_coevo | heilbron_adversarial/pop_a | grid.py | A4_I |
| 4b | A4_I | TBD | adversarial_coevo | heilbron_adversarial/pop_b | seed.py | A4_C |

**Total**: 12 runs (4 solo + 8 adversarial). 12 Redis DBs required.

**Problem variant note**: A new `problems/heilbron_solo/` directory must be created for the solo arm, containing:
- `validate.py` -- identical to `problems/heilbron/validate.py`
- `helper.py` -- identical to `problems/heilbron/helper.py` (already identical to adversarial)
- `metrics.yaml` -- identical to `problems/heilbron/metrics.yaml`
- `task_description.txt` -- identical to `problems/heilbron/task_description.txt`
- `initial_programs/grid.py` -- ONLY `grid.py` (identical to `problems/heilbron_adversarial/pop_a/initial_programs/grid.py`)

This ensures: (a) seed program parity with the adversarial Constructor arm, (b) no extra initial diversity confound from the 5-seed solo variant.

## 7. Sample Size Justification

N=4 per arm (4 solo runs, 4 adversarial pairs).

**From baseline-repro (N=4)**: SD(best-overall) ~ 0.0026. For a two-sample t-test with alpha=0.10 (one-sided), N=4/arm detects effect size d=0.003 (1.15 sigma) with power ~ 0.55. Not powered for definitive null -- but sufficiently powered to detect the effect size needed to justify the adversarial program (0.003 = 8.7% of baseline).

**Practical constraint**: 12 Redis DBs required. 14 available after flushing stale adversarial-dynamic-updates data (DBs 1-8). Feasible.

## 8. Statistical Test

**Test**: Welch's two-sample t-test (unequal variance), **two-sided**. H1: mu_adversarial != mu_solo.

**Significance threshold**: alpha = 0.10 (relaxed due to N=4/arm).

**How computed**: Compare mean Constructor actual_fitness at gen 50 between arms. Report effect size (Cohen's d), 90% CI, and two-sided p-value.

**Why two-sided**: Evidence from adversarial-dynamic-updates (NEGATIVE, all cells below baseline) demonstrates that adversarial mechanisms can actively harm performance. A one-sided test would discard this possibility, contradicting empirical evidence.

**Interpretation guide**:
- **p < 0.10 AND adversarial > solo**: POSITIVE -- adversarial adds value. Continue line.
- **p < 0.10 AND solo > adversarial**: NEGATIVE -- adversarial actively hurts. Close urgently.
- **p > 0.10 AND point estimate within 0.001**: SUGGESTIVE NULL -- practical equivalence likely. Close line unless new mechanism proposed.
- **p > 0.10 AND point estimate > 0.001**: INCONCLUSIVE -- 55% power cannot distinguish true null from small effect. Do NOT close the line based on this result alone. Consider increasing N.

**Minimum detectable effect (MDE)**: At N=4/arm, alpha=0.10 two-sided, 80% power: MDE ~= 0.0038 (1.46*sigma). Effects smaller than 0.0038 cannot be reliably detected. This is reported alongside results.

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| Seed diversity (solo 5 vs adversarial 1) | HIGH | Create `heilbron_solo/` with only `grid.py`. Verified identical to adversarial Constructor seed. |
| Compute budget asymmetry (adversarial gets 2x runs per pair) | MEDIUM | Track wall-clock time per pair. Adversarial has 2 LLM calls/gen (C+I) but solo has 1. Report throughput-normalized comparison. |
| Pipeline differences (standard vs adversarial_coevo) | LOW | Pipeline only differs in opponent evaluation stage. Core mutation, MAP-Elites strategy identical. |
| `include_in_prompts` hidden IV (**ACTIVE failure mode per PATTERNS.md**) | HIGH | Solo LLM sees 2 metrics in mutation prompts (`fitness`, `is_valid`). Adversarial LLM sees 4 (`fitness`, `is_valid`, `actual_fitness`, `resistance`). The extra metrics -- especially `resistance` -- provide implicit optimization hints about solution robustness. **Decision**: We do NOT modify the adversarial `metrics.yaml` because this experiment tests the full heilbron-prover configuration as-is, not a modified version. Any result should be attributed to "the adversarial package" (opponents + framing + composite fitness + richer prompts), not to opponent pressure alone. This is an **acknowledged limitation**, not a mitigated confound. |
| Task description divergence | HIGH | Adversarial `task_description.txt` is 40% longer, contains GAN analogy, explicit strategy guidance ("aim for DEEP local optima"), and game-theoretic framing absent from solo. **Decision**: Same as above -- we test the full adversarial package. A third arm (adversarial framing, no opponents) would isolate the framing effect but is beyond scope. Acknowledged limitation. |
| `pre_step_hook` sync overhead | LOW | Adversarial uses `MainRunSyncHook` (5s poll). Solo uses null hook. Sync overhead is small relative to LLM call latency (~30s). |
| LLM server load (12 concurrent vs 8 concurrent) | MEDIUM | All runs share same LiteLLM proxy. Monitor throughput. If contention detected, stagger launches. |
| Stale Redis data from prior experiments | LOW | Flush DBs 1-8 (stale adversarial-dynamic-updates data) before launch. |

## 10. Stop Criteria

**Stopping rule**: `max_generations=50` (hard stop). No early termination.

**Minimum completion threshold**: At least 3/4 runs per arm must reach gen 40 for the arm to be analyzable. If fewer than 3 complete, the arm is marked INCOMPLETE and the experiment verdict is INCONCLUSIVE.

**Run invalidation**:
- Invalidity rate > 90% sustained for 10+ generations -> investigate, potentially invalidate
- PID death before gen 10 -> restart pair (adversarial) or run (solo)
- LLM server unreachable for > 2 hours -> investigate
- Wall-clock time exceeding 5 days for any run -> investigate contention

**Pair invalidation (adversarial only)**:
- Generation gap > 10 between Constructor and Improver -> sync hook failure, investigate

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| GPU hours | ~100h (4 solo x ~5h + 4 pairs x ~10h each) |
| Wall time | ~48h (solo and adversarial can run concurrently) |
| Redis DBs used | 12 (4 solo + 8 adversarial) |
| LLM calls | ~6400 (400 mutations x 12 runs + overhead) |

## 12. Open Questions / Risks

1. **This experiment tests the adversarial PACKAGE, not opponent pressure alone.** The adversarial arm differs from solo in: (a) actual opponent evaluation, (b) richer mutation prompts (4 vs 2 metrics), (c) adversarial task description with optimization hints, (d) composite fitness function. A positive result means "the full adversarial config works better," not "opponents help." Isolating opponent pressure would require a third arm (adversarial framing + metrics, no opponents) -- beyond scope.

2. **Compute asymmetry**: Adversarial pairs consume ~800 LLM calls vs ~400 for solo (2x per replicate), plus opponent evaluation overhead. If adversarial wins, a secondary "compute-normalized" analysis should compare adversarial at gen 50 vs solo extrapolated to gen 100 (or rerun solo to gen 100 if feasible). The primary result is "per generation" comparison, which is what matters for algorithm selection.

3. **55% power**: This experiment can detect effects >= 0.0038 with 80% power. Effects between 0.001 and 0.0038 will likely appear as INCONCLUSIVE. This is accepted -- the experiment is designed to detect the large effects that would justify continued investment, not to prove small effects.

4. **Fallback opponents**: Adversarial Pop A has 2 fallback improvers loaded at startup (from `pop_a/fallback/`). Solo has no equivalent mechanism. This provides a warm-start advantage for the adversarial arm that is minor but nonzero. Documented, not mitigated.

## 13. Treatment Verification

### What observable evidence proves the treatment is applied?

**Solo arm**:
- `pipeline_builder` in `--cfg job` output shows `DefaultPipelineBuilder` (NOT `AdversarialPipelineBuilder`)
- No `opponent_redis_db` or `opponent_redis_prefix` in resolved config
- No `FetchOpponentResultsStage` in DAG
- `pre_step_hook` is `NullPreStepHook` or absent
- Redis keys: NO `opponent_*` keys present

**Adversarial arm**:
- `pipeline_builder` in `--cfg job` output shows `AdversarialPipelineBuilder`
- `opponent_redis_db` and `opponent_redis_prefix` correctly set to partner run
- `pre_step_hook` is `MainRunSyncHook`
- Redis keys: opponent fitness evaluation metrics present
- Generation parity within 2 between paired runs

### Extra overrides per arm

**Solo (S1-S4)**:
```
pipeline=standard
problem.name=heilbron_solo
pre_step_hook=null
```

**Adversarial (A1_C-A4_C, A1_I-A4_I)**:
```
pipeline=adversarial_coevo
problem.name=heilbron_adversarial/pop_a  (or pop_b for Improvers)
opponent_redis_db=<partner_db>
opponent_redis_prefix=<partner_prefix>
pipeline_builder.per_opponent_timeout=300
```
