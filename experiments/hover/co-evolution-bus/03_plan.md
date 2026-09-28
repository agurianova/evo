# Pre-Registration: HoVer Co-Evolution Bus

**Date**: 2026-03-22
**Protocol version**: 1.0
**Pre-registration commit**: `01f7dfb`
**GitHub PR**: #109 (branch: `exp/hover-co-evolution-bus`)
**Tracking issue**: #110
**Design doc**: `experiments/hover/co-evolution-bus/01_design.md`
**Review doc**: `experiments/hover/co-evolution-bus/02_review.md` (verdict: APPROVED, Round 2)
**Evaluation script**: `experiments/hover/co-evolution-bus/run_test_eval.sh` (sha256: TBD)

---

## Hypothesis

**H0**: Bus co-evolution with soft fitness produces mean test retrieval coverage <= 54.37% (Cell C reference).
**H1**: Bus co-evolution produces mean test coverage >= 56.37% (Cell C + 2.0pp).
**Primary metric**: Mean discrete test retrieval coverage at gen 25, 300-sample held-out, 5 repeats per run.
**Significance threshold**: alpha = 0.05 (one-sided). Effect-size threshold table is primary decision instrument.

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `problem.name` | Chain LLM | Mutation LLM | Condition |
|-----|-------|------------|-----------|----------------|-----------|-------------|-----------|
| B1 | bus-hover-1 | 9 | standard | chains/hover/static_soft | 10.226.17.25:8001 | 10.226.72.211:8777 | Treatment |
| B2 | bus-hover-2 | 10 | standard | chains/hover/static_soft | 10.225.185.235:8001 | 10.226.15.38:8777 | Treatment |
| B3 | bus-hover-3 | 11 | standard | chains/hover/static_soft | 10.226.17.25:8000 | 10.226.185.47:8777 | Treatment |
| PM | bus-prompt-meta | 12 | prompt_evolution | prompt_evolution_hover | N/A | 10.225.51.251:8777 | Meta-evo hub |

Architecture: 3+1 bus. B1/B2/B3 write prompt_stats; PM aggregates from all 3 and evolves prompts. B1/B2/B3 read PM's champion from DB 12.

Extra overrides (main runs): `prompt_fetcher=coevolved prompt_fetcher.prompt_redis_db=12 prompt_fetcher.prompt_prefix=prompt_evolution_hover`
Extra overrides (PM): `max_elites_per_generation=8 max_mutations_per_generation=8`

---

## Controlled Variables

| Field | Value |
|-------|-------|
| Chain topology | 7-step fixed (3 tool, 4 LLM) |
| Test metric | Discrete retrieval coverage |
| Evolutionary fitness | Soft (fractional: gold_found/3) |
| Chain LLM | Qwen3-8B, thinking ON, max_tokens=32768 |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 |
| num_parents | 1 |
| max_elites (main) | 8 |
| max_mutations (main) | 8 |
| max_generations | 25 |
| stage_timeout | 3000 |
| dag_timeout | 7200 |
| Seed initialization | Cold start |
| Validation N | 300 |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature and nucleus sampling in chain and mutation LLMs
- Non-deterministic GPU floating point across hardware

**Global seed**: N/A

A fresh run with identical config will produce a different fitness trajectory but should
land in a statistically similar fitness range. Cross-experiment comparisons use effect-size
thresholds (from `01_design.md`) rather than exact trajectory matching.

---

## Dataset Checksums

| File | sha256 |
|------|--------|
| `problems/chains/hover/dataset/HoVer_train.jsonl` | `1bfc935d667e405a51cfb0361d1ee672fa3475d82714bcf027fc2d1a2c5cdcfa` |
| `problems/chains/hover/dataset/HoVer_test.jsonl` | `1319ef6d1c16c879f4e8d3675df8ebf93be1387da6ee874d9fcdeaa0d56280a2` |
| `problems/chains/hover/static_soft/test.py` | `b8d193b04ac4a6662642bafd2c21645feb06b7e3e3095e0f4af8a58493fda6e3` |

---

## Success Criteria

| Bus mean test coverage | Verdict | Action |
|------------------------|---------|--------|
| >= 56.37% (all 3 runs) | POSITIVE | Replicate at n>=4 |
| >= 56.37% (2 of 3) | INCONCLUSIVE | Replicate at n>=4 |
| [54.37%, 56.37%) | NULL | Close prompt co-evo line (3rd null) |
| [51.65%, 54.37%) | REGRESSIVE | Close |
| < 51.65% | NEGATIVE | Close |

Trial dilution diagnostic: if avg trials/prompt < 5, closure claim scoped accordingly.
Correlation rule: inter-run SD < 0.5pp -> n=1 primary; >= 1.0pp -> n=3 primary.

---

## Monitoring Plan

`max_generations`: 25

- Gen 3 (~12%): smoke check -- all PIDs alive, Redis keys growing, PM sees stats from all 3 DBs
- Gen 5 (~20%): first checkpoint -- PM archive populated, fallback-to-coevolved transition logged
- Gen 13 (~50%): midpoint checkpoint -- val fitness trajectory, prompt fitness check
- Gen 25 (100%): final evaluation + analysis

Early termination rule:
- Gen-0 val fitness < 0.01 or > 0.20 or = -1000: halt
- Val coverage < 45% at gen 10: halt (infrastructure failure)
- PM archive empty at gen 5: halt all (feedback loop broken)
- No frontier improvement for 10 consecutive gens AND gen >= 15: may terminate early

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

_(None yet. Record any post-registration changes here with numbered amendments.)_
