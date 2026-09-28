# Pre-Registration: heilbron/adversarial-v2

**Date**: 2026-04-08
**Protocol version**: 1.0
**Pre-registration commit**: `24b6b1b297427431389d6f0bf78594fa8778697f`
**GitHub PR**: #188 (branch: `exp/heilbron/adversarial-v2`)
**Tracking issue**: N/A
**Design doc**: `experiments/heilbron/adversarial-v2/01_design.md`
**Review doc**: `experiments/heilbron/adversarial-v2/02_review.md` (verdict: APPROVED)
**Evaluation script**: N/A (no test split; continuous fitness)

---

## Hypothesis

**H1 (Primary)**: Both K=1 and K=3 bidirectional feedback pairs achieve Constructor `actual_fitness` exceeding the heilbron-prover baseline (0.03464) by >= 0.002 at generation 75.

**H2 (Secondary, hypothesis-generating)**: K=3 achieves different actual_fitness than K=1. Direction uncertain.

**H3 (Secondary)**: Both Improvers show acceptance rate > 5% after gen 20 (vs ~0% in heilbron-prover P2_B).

**Primary metric**: Constructor `actual_fitness` (raw min_area) at generation 75.
**Significance threshold**: N/A at N=1 per K. Effect magnitude and direction consistency.

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | K | `problem.name` | `mutation_url` | Seed |
|-----|-------|------------|-----------|---|----------------|----------------|------|
| 1 | P1_A | 1 | adversarial_coevo_feedback | 3 | heilbron_adversarial/pop_a | LiteLLM proxy | cold start |
| 2 | P1_B | 2 | adversarial_coevo_feedback | 3 | heilbron_adversarial/pop_b | LiteLLM proxy | cold start |
| 3 | P2_A | 3 | adversarial_coevo_feedback | 1 | heilbron_adversarial/pop_a | LiteLLM proxy | cold start |
| 4 | P2_B | 4 | adversarial_coevo_feedback | 1 | heilbron_adversarial/pop_b | LiteLLM proxy | cold start |

---

## Controlled Variables

| Field | Value |
|-------|-------|
| evolution | steady_state (SteadyStateEvolutionEngine) |
| max_in_flight | 8 |
| model_name | Qwen3-235B-A22B-Thinking-2507 |
| mutation_url | http://10.232.30.185:4000/v1 |
| chain_url | null (no chain servers) |
| num_parents | 1 |
| max_elites_per_generation | 8 |
| max_mutations_per_generation | 8 |
| n_opponents | 5 |
| per_opponent_timeout | 300 |
| stage_timeout | 3000 |
| dag_timeout | 7200 |
| max_generations | 75 |
| bidirectional feedback | ON (all runs) |
| initial programs | cold start (baseline.py) |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- LLM sampling temperature in mutation LLM (Qwen3-235B)
- `random.sample` in opponent selection (fitness-proportional sampling)
- Co-evolutionary dynamics (opponent populations diverge stochastically)
- Steady-state engine: asynchronous evaluation ordering

**Global seed**: N/A (no deterministic seed support in adversarial co-evolution)

A fresh run with identical config will produce a different fitness trajectory but should land in a statistically similar fitness range. Cross-experiment comparisons use effect-size thresholds (from `01_design.md`) rather than exact trajectory matching.

---

## Dataset Checksums

See `experiments/heilbron/adversarial-v2/dataset_snapshot.json` for full file checksums.
Git commit of problem files at pre-registration: `c1eca7c3`.

No external dataset — fitness is computed from program output (point configurations) via `evaluate.py`.

---

## Success Criteria

| Hypothesis | Criterion | Verdict |
|-----------|-----------|---------|
| H1 | Both pairs actual_fitness > 0.03464 + 0.002 = 0.03664 | POSITIVE |
| H1 | Both pairs actual_fitness > 0.03464 + 0.005 = 0.03964 | STRONG POSITIVE |
| H1 | Both pairs actual_fitness delta < 0.002 | NULL |
| H1 | Either pair actual_fitness < 0.010 at gen 75 | NEGATIVE |
| H2 | |P1_A - P2_A| >= 0.002 at gen 75 | Directional signal |
| H2 | |P1_A - P2_A| < 0.002 | K does not matter |
| H3 | Both Improver acceptance rate > 5% after gen 20 | POSITIVE |
| H3 | Both Improvers stagnate (~0%) | NULL |

---

## Monitoring Plan

`max_generations`: 75

- Gen 5 (~7%): smoke check — all PIDs alive, Redis keys growing, treatment verification (feedback blocks present, K correct)
- Gen 15 (~20%): first checkpoint — actual_fitness trajectory, Improver acceptance rate, generation parity
- Gen 37 (~50%): midpoint checkpoint — full analysis, compare against heilbron-prover trajectory at same gen
- Gen 75 (100%): final evaluation + analysis

Early termination rule:
- Per-run: actual_fitness < 0.005 at gen 20, invalidity > 75% for 5 consecutive gens, dead PID for 2 hours
- Stagnation alert: zero actual_fitness improvement for 15 consecutive gens after gen 10 → watchdog WARNING

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|

Watchdog PID:
Launch commit: `<hash>`

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|

---

## Amendments

_(Add numbered entries here for any post-registration changes.)_
- Pre-authorized: If K=3 mutation latency exceeds 60s mean (10-gen window), reduce to K=2. Log in 04_issues_log.md, separate pre/post-amendment analysis windows.
