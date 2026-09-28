# Pre-Registration: Adversarial Co-Evolution — Optimizers vs Deceptive Landscapes

**Date**: 2026-04-06
**Protocol version**: 1.0
**Pre-registration commit**: `172a83e`
**GitHub PR**: #169 (branch: `feat/adversarial-coevo`)
**Tracking issue**: N/A
**Design doc**: `experiments/adversarial/optimizer-coevo/01_design.md`
**Review doc**: `experiments/adversarial/optimizer-coevo/02_review.md` (verdict: APPROVED)
**Evaluation script**: N/A (no test split; `has_test_set: false`)

---

## Hypothesis

**H0**: Adversarial co-evolution does NOT produce an arms race. At least one population shows no fitness improvement (delta <= 0) from gen 1 to final gen, averaged across replicate pairs.

**H1**: Adversarial co-evolution DOES produce an arms race. Both populations show positive fitness improvement from gen 1 to final gen.

**Primary metric**: Frontier fitness improvement (fitness_final - fitness_gen1), separately for Pop A and Pop B
**Significance threshold**: alpha = 0.10 (relaxed for PoC with N=2)

---

## Run Design Table

| Pair | Pop | Label | `redis.db` | `pipeline` | `problem.name` | `opponent_redis_db` | `opponent_redis_prefix` |
|------|-----|-------|------------|-----------|----------------|---------------------|-------------------------|
| 1 | A | P1-A | 1 | adversarial_coevo | adversarial/optimizer_v2/pop_a | 2 | adversarial/optimizer_v2/pop_b |
| 1 | B | P1-B | 2 | adversarial_coevo | adversarial/optimizer_v2/pop_b | 1 | adversarial/optimizer_v2/pop_a |
| 2 | A | P2-A | 3 | adversarial_coevo | adversarial/optimizer_v2/pop_a | 4 | adversarial/optimizer_v2/pop_b |
| 2 | B | P2-B | 4 | adversarial_coevo | adversarial/optimizer_v2/pop_b | 3 | adversarial/optimizer_v2/pop_a |

All 4 processes use: `llm_base_url=http://10.232.30.185:4000/v1`, `model_name=Qwen3-235B-A22B-Thinking-2507`

---

## Controlled Variables

| Field | Value |
|-------|-------|
| pipeline | adversarial_coevo |
| max_generations | 20 |
| num_parents | 1 |
| max_elites_per_generation | 8 |
| max_mutations_per_generation | 8 |
| mutation_mode | rewrite |
| stage_timeout | 3000 |
| dag_timeout | 7200 |
| n_opponents | 5 |
| per_opponent_timeout | 10.0s |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 via LiteLLM proxy |
| MAP-Elites | Single island (fitness_island), 150 bins |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- LLM sampling temperature in mutation generation
- `random.sample` in opponent selection (fitness-proportional)
- `random.sample` in `FormatterStage` (failure sampling per generation)
- Process scheduling affecting lockstep timing

**Global seed**: N/A (no deterministic seed support)

A fresh run with identical config will produce a different fitness trajectory but should
show the same qualitative pattern (arms race vs null). Cross-pair comparison provides
the reproducibility check (N=2 replicate pairs).

---

## Dataset Checksums

N/A — no dataset. This is a pure optimization task with procedurally generated landscapes.

---

## Success Criteria

Arms race declared if ALL FOUR fitness improvements (2 pops x 2 pairs) are positive.

| Pattern | Verdict |
|---------|---------|
| All 4 positive, both pops mean >= 15pp | STRONG ARMS RACE |
| All 4 positive, both pops mean >= 5pp | ARMS RACE |
| All 4 positive, at least one pop mean < 5pp | WEAK ARMS RACE |
| Mixed positive/negative | ASYMMETRIC or NULL |
| Both negative | COLLAPSE |

Infrastructure validation PASS if: generation parity <= 2, n_opponents > 0 at gen 1, all processes reach gen 20.

---

## Monitoring Plan

`max_generations`: 20

- Gen 2 (~10%): smoke check — all PIDs alive, Redis keys growing, n_opponents > 0
- Gen 5 (~25%): first checkpoint — extract frontier fitness for all 4 processes, check invalidity rate
- Gen 10 (~50%): midpoint checkpoint — assess trajectory direction for both populations
- Gen 20 (100%): final evaluation + qualitative program inspection + analysis

Early termination rule: invalidity > 80% at gen 5, or fitness = 0.0 for all programs through gen 5, or sync hook blocks > 60 min.

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
