# Pre-Registration: HoVer Prompt Co-Evolution with Soft Fitness

**Date**: 2026-03-20
**Protocol version**: 1.0
**Pre-registration commit**: `baee9bd` -- commit this file BEFORE any code changes
**GitHub PR**: #TBD (branch: `exp/hover-prompt-coevolution`)
**Tracking issue**: N/A
**Design doc**: `experiments/hover/prompt_coevolution/01_design.md`
**Review doc**: `experiments/hover/prompt_coevolution/02_review.md` (verdict: APPROVED)
**Evaluation script**: `experiments/hover/prompt_coevolution/run_test_eval.sh` (sha256: TBD)

---

## Hypothesis

**H0**: Co-evolved mutation prompts with soft fitness produce test retrieval coverage (discrete, 300-sample) indistinguishable from the soft-fitness-only reference (Cell C mean 54.37%, SD=0.99pp, n=2).

**H1**: Co-evolved mutation prompts with soft fitness produce mean test retrieval coverage >= 56.37% (Cell C mean + 2.00pp).

**Primary metric**: Discrete test retrieval coverage at gen 25 on 300-sample held-out test set (5 repeats per run).

**Significance threshold**: alpha = 0.05 (one-sided, Test 1 only; Tests 2-4 exploratory)

---

## Run Design Table

### Main runs (soft fitness + co-evolved prompts)

| Run | Label | `redis.db` | `pipeline` | `problem.name` | `prompt_fetcher` | `prompt_redis_db` | Chain LLM | Mutation LLM |
|-----|-------|------------|-----------|-----------------|-------------------|-------------------|-----------|-------------|
| C1 | hover-coevo-1 | 9 | standard | chains/hover/static_soft | coevolved | 11 | 10.226.17.25:8001 | 10.226.72.211:8777 |
| C2 | hover-coevo-2 | 10 | standard | chains/hover/static_soft | coevolved | 12 | 10.225.185.235:8001 | 10.226.15.38:8777 |

### Prompt runs (mutation prompt evolution)

| Run | Label | `redis.db` | `pipeline` | `problem.name` | `main_redis_db` | `main_redis_prefix` | Mutation LLM |
|-----|-------|------------|-----------|-----------------|-----------------|---------------------|-------------|
| P1 | hover-prompt-evo-1 | 11 | prompt_evolution | prompt_evolution_hover | 9 | chains/hover/static_soft | 10.226.185.47:8777 |
| P2 | hover-prompt-evo-2 | 12 | prompt_evolution | prompt_evolution_hover | 10 | chains/hover/static_soft | 10.225.51.251:8777 |

### Historical control (Cell C from feedback_softfit, PR #92)

| Run | Test Mean | Test SD | 5 Scores |
|-----|-----------|---------|----------|
| F3 | 55.07% | 1.32% | 54.0, 56.7, 56.3, 54.3, 54.0 |
| F4 | 53.67% | 1.41% | 56.0, 54.0, 53.0, 52.7, 52.7 |
| **Cell C mean** | **54.37%** | **0.99pp** (inter-run) | |

---

## Controlled Variables

| Field | Value |
|-------|-------|
| `problem.name` (main runs) | `chains/hover/static_soft` |
| `pipeline` (main runs) | `standard` |
| Evolutionary fitness | Soft (fractional: gold_found/3) |
| Test metric | Discrete (all 3 gold docs = 1, else 0) |
| Chain LLM | Qwen3-8B, thinking mode ON |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 |
| `num_parents` | 1 |
| `max_elites_per_generation` | 8 (main), 5 (prompt) |
| `max_generations` | 25 |
| `stage_timeout` | 3000 |
| `dag_timeout` | 7200 |
| Seed initialization | Cold start |
| Val samples | 300 (first 300 train) |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- LLM sampling temperature and nucleus sampling in chain and mutation LLMs
- Non-deterministic GPU floating point across hardware
- Prompt run champion selection timing (depends on Redis race conditions)
- Fallback-to-coevolved transition timing (depends on prompt archive convergence)

**Global seed**: N/A (no deterministic seed support)

A fresh run with identical config will produce a different fitness trajectory but should
land in a statistically similar fitness range. Cross-experiment comparisons use effect-size
thresholds (from `01_design.md`) rather than exact trajectory matching.

---

## Dataset Checksums

```bash
sha256sum problems/chains/hover/dataset/HoVer_train.jsonl problems/chains/hover/dataset/HoVer_test.jsonl
```

| File | sha256 |
|------|--------|
| `HoVer_train.jsonl` | `1bfc935d667e405a51cfb0361d1ee672fa3475d82714bcf027fc2d1a2c5cdcfa` |
| `HoVer_test.jsonl` | `1319ef6d1c16c879f4e8d3675df8ebf93be1387da6ee874d9fcdeaa0d56280a2` |

---

## Success Criteria

| Treatment mean test coverage | Verdict |
|------------------------------|---------|
| >= 56.37% (both runs) | **POSITIVE** |
| >= 56.37% (one run only) | **INCONCLUSIVE** |
| [54.37%, 56.37%) | **NULL** |
| [51.65%, 54.37%) | **REGRESSIVE** |
| < 51.65% | **NEGATIVE** |

---

## Monitoring Plan

`max_generations`: 25

- Gen 3 (~12%): smoke check -- all PIDs alive, Redis keys growing, prompt stats keys exist
- Gen 5 (~20%): first checkpoint -- verify prompt archive has programs, extract best-by-val
- Gen 12 (~50%): midpoint checkpoint -- check val trajectory, prompt fitness differentiation
- Gen 25 (100%): final evaluation + 5-repeat test eval + analysis

Early termination rule:
- Gen-0 val fitness < 0.01 or > 0.20: halt
- Main run val < 0.45 at gen 10: halt (infrastructure failure)
- Prompt run archive empty at gen 5: halt pair (co-evolution broken)
- Val stagnation >= 10 gens AND gen >= 15: may terminate early

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
