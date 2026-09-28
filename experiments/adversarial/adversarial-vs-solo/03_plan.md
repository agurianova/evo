# Pre-Registration: adversarial/adversarial-vs-solo

**Date**: 2026-04-11
**Protocol version**: 1.0
**Pre-registration commit**: `TBD` -- commit this file BEFORE any code changes
**GitHub PR**: #TBD (branch: `exp/adversarial/adversarial-vs-solo`)
**Tracking issue**: N/A
**Design doc**: `experiments/adversarial/adversarial-vs-solo/01_design.md`
**Review doc**: `experiments/adversarial/adversarial-vs-solo/02_review.md` (verdict: APPROVED)
**Evaluation script**: N/A (no test split -- Heilbronn is an optimization problem)

---

## Hypothesis

**H0**: There is no difference in Constructor actual_fitness between adversarial co-evolution and solo MAP-Elites.
**H1**: Adversarial co-evolution produces different Constructor actual_fitness than solo MAP-Elites.
**Primary metric**: Constructor actual_fitness (raw min_area) at gen 50
**Significance threshold**: alpha = 0.10 (two-sided Welch's t-test)
**Equivalence threshold**: 0.003 (8.7% of baseline 0.03464)

---

## Run Design Table

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

---

## Controlled Variables

| Field | Value |
|-------|-------|
| `max_generations` | 50 |
| `max_elites_per_generation` | 8 |
| `max_mutations_per_generation` | 8 |
| `mutation_mode` | rewrite |
| `model_name` | Qwen3-235B-A22B-Thinking-2507 |
| `llm_base_url` | http://10.232.30.185:4000/v1 |
| `temperature` | 0.6 |
| `max_tokens` | 81920 |
| `island_max_size` | 75 |
| `primary_resolution` | 150 |
| `num_parents` | 1 |
| `stage_timeout` | 3000 |
| `dag_timeout` | 7200 |
| Initial seed program | `grid.py` (identical across all Constructor / solo runs) |
| Engine type | Generational (`EvolutionEngine`) |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism (document and accept):
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature and nucleus sampling in mutation LLM
- Non-deterministic GPU floating point across hardware

**Global seed**: N/A (no deterministic seed support in GigaEvo)

A fresh run with identical config will produce a different fitness trajectory but should
land in a statistically similar fitness range. Cross-experiment comparisons use effect-size
thresholds (from `01_design.md`) rather than exact trajectory matching.

---

## Dataset Checksums

This is an optimization problem (Heilbronn triangle), not a dataset-based evaluation.
Problem definition files are anchored in `dataset_snapshot.json` (42 files, commit `ea30e341`).

Key files:
- `problems/heilbron/validate.py` -- solo arm validator
- `problems/heilbron_adversarial/pop_a/evaluate.py` -- adversarial Constructor evaluator
- `problems/heilbron_adversarial/pop_b/evaluate.py` -- adversarial Improver evaluator

---

## Success Criteria

**Interpretation guide** (from 01_design.md Section 8):

| Outcome | Condition | Action |
|---------|-----------|--------|
| POSITIVE | p < 0.10 AND adversarial > solo | Adversarial adds value. Continue line. |
| NEGATIVE | p < 0.10 AND solo > adversarial | Adversarial actively hurts. Close urgently. |
| SUGGESTIVE NULL | p > 0.10 AND point estimate within 0.001 | Practical equivalence likely. Close line unless new mechanism proposed. |
| INCONCLUSIVE | p > 0.10 AND point estimate > 0.001 | 55% power cannot distinguish. Do NOT close line. Consider increasing N. |

**MDE at 80% power**: ~0.0038 (1.46 * sigma). Effects smaller than 0.0038 cannot be reliably detected.

---

## Monitoring Plan

`max_generations`: 50

- Gen 5 (~10%): smoke check -- all PIDs alive, Redis keys growing, no ERROR in logs
- Gen 10 (~20%): first checkpoint -- verify fitness > 0 in all runs, no sync deadlocks
- Gen 25 (~50%): midpoint checkpoint -- diagnose, verify treatment (adversarial pairs synced)
- Gen 50 (100%): final evaluation + statistical analysis

Early termination rule: None (hard stop at gen 50). Minimum 3/4 runs per arm must reach gen 40 for the arm to be analyzable.

**Run invalidation criteria**:
- Invalidity rate > 90% sustained for 10+ generations
- PID death before gen 10 (restart)
- LLM server unreachable for > 2 hours
- Wall-clock time exceeding 5 days
- Adversarial generation gap > 10 between paired runs

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| _(filled at launch)_ | | | |

Watchdog PID: _(filled at launch)_
Launch commit: `TBD`

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|
| _(filled during monitoring)_ | | |

---

## Amendments

### Amendment 1 — Reuse adversarial arm from heilbron/baseline-repro (2026-04-11)

**Change**: Instead of running 8 new adversarial processes (A1_C/I through A4_C/I), reuse
the 4 Constructor actual_fitness values from `heilbron/baseline-repro` (PR #201) as the
adversarial arm comparison data. Only 4 solo runs (S1-S4) are launched.

**Justification**: `heilbron/baseline-repro` used identical configuration:
- Same model: Qwen3-235B-A22B-Thinking-2507
- Same server: LiteLLM proxy at 10.232.30.185:4000/v1
- Same hyperparameters: max_gen=50, max_elites=8, max_mutations=8, mutation_mode=rewrite,
  stage_timeout=3000, dag_timeout=7200, per_opponent_timeout=300, num_parents=1
- Same pipeline: adversarial_coevo
- Same problem: heilbron_adversarial/pop_a (Constructor)

**Adversarial arm data (from baseline-repro 05_results.md)**:
- P1_A: actual_fitness=0.03400 (gen 46/50)
- P2_A: actual_fitness=0.03276 (gen 30/50, early closeout)
- P3_A: actual_fitness=0.03650 (gen 50/50)
- P4_A: actual_fitness=0.03023 (gen 50/50)
- Mean: 0.03337, SD=0.00261

**Limitation**: Non-contemporaneous comparison. Adversarial data collected ~1 day before
solo runs. Server load and model behavior assumed stable over this window.

**Impact on analysis**: Primary statistical test unchanged (4 vs 4 Welch's t-test). Power
unchanged. The pre-registered alpha=0.10 and equivalence threshold=0.003 still apply.

**Researcher approved**: Yes (2026-04-11).

### Amendment 2 — Use best-overall (max of both populations) as adversarial metric (2026-04-11)

**Change**: The adversarial arm metric is changed from Constructor-only actual_fitness to
**best-overall actual_fitness per pair**: max(Constructor, Improver). This is the value you
actually harvest from an adversarial run — both populations produce solutions.

**Rationale**: Constructor-only penalizes the adversarial arm by ignoring the Improver
population. The fair comparison for "does adversarial add value over solo?" is: what's the
best solution you get from 2 co-evolving populations vs 1 solo population?

**Updated adversarial arm data (best-overall per pair)**:
- Pair 1: actual_fitness=0.03614 (P1_B, Improver, gen 45/50)
- Pair 2: actual_fitness=0.03276 (P2_A, Constructor, gen 30/50)
- Pair 3: actual_fitness=0.03650 (P3_A, Constructor, gen 50/50)
- Pair 4: actual_fitness=0.03255 (P4_B, Improver, gen 50/50)
- Mean: 0.03449, SD=0.00212

**Impact**: Higher adversarial mean (0.03449 vs 0.03337) makes it harder for solo to
match — the bar is now closer to the heilbron-prover baseline (0.03464). If solo matches
0.03449, adversarial overhead is truly unjustified.

**Researcher approved**: Yes (2026-04-11).
