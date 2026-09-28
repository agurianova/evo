# Pre-Registration: hover/steady-state-validation

**Date**: 2026-03-26
**Protocol version**: 1.0
**Pre-registration commit**: `<hash>` ← filled after commit
**GitHub PR**: #TBD (branch: `exp/hover-steady-state-validation`)
**Tracking issue**: TBD
**Design doc**: `experiments/hover/steady-state-validation/01_design.md`
**Review doc**: `experiments/hover/steady-state-validation/02_review.md` (verdict: APPROVED)
**Evaluation script**: `experiments/hover/steady-state-validation/run_test_eval.sh` (sha256: TBD)

---

## Hypothesis

**H₀**: μ_generational − μ_steady_state > 3.0pp (steady-state is inferior)
**H₁**: μ_generational − μ_steady_state ≤ 3.0pp (steady-state is non-inferior)
**Primary metric**: Best soft fractional validation retrieval coverage at `engine:total_generations` = 25
**Significance threshold**: α = 0.05 (one-sided Welch's t-test for non-inferiority)

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `problem.name` | `evolution` | Chain Server |
|-----|-------|------------|-----------|-----------------|------------|-------------|
| 1 | S1 | 6 | standard | chains/hover/full | default | 10.226.17.25:8001 |
| 2 | S2 | 7 | standard | chains/hover/full | default | 10.226.17.25:8000 |
| 3 | S3 | 8 | standard | chains/hover/full | steady_state | 10.225.185.235:8001 |
| 4 | S4 | 9 | standard | chains/hover/full | steady_state | 10.225.185.235:8000 |

Mutation: `llm=balanced` (shared pool of 4 mutation servers for all runs)

---

## Controlled Variables

| Field | Value |
|-------|-------|
| `problem.name` | `chains/hover/full` |
| `pipeline` | `standard` |
| `num_parents` | 1 |
| `max_elites_per_generation` | 8 |
| `max_mutations_per_generation` | 8 |
| `max_generations` | 25 |
| `significant_change` | 0.003 |
| `stage_timeout` | 3000 |
| `dag_timeout` | 7200 |
| `llm` | `balanced` |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature and nucleus sampling in chain and mutation LLMs
- Non-deterministic GPU floating point across hardware

**Global seed**: N/A (stochastic LLM evolution)

A fresh run with identical config will produce a different fitness trajectory but should
land in a statistically similar fitness range. Cross-experiment comparisons use effect-size
thresholds (from `01_design.md`) rather than exact trajectory matching.

---

## Dataset Checksums

| File | sha256 |
|------|--------|
| `problems/chains/hover/dataset/HoVer_train.jsonl` | `1bfc935d667e405a51cfb0361d1ee672fa3475d82714bcf027fc2d1a2c5cdcfa` |
| `problems/chains/hover/dataset/HoVer_test.jsonl` | `1319ef6d1c16c879f4e8d3675df8ebf93be1387da6ee874d9fcdeaa0d56280a2` |
| `problems/chains/hover/full/test.py` | `e70408c04d40719ded076e5eff513f99e6a88c167614938cdb61cb693c6e9423` |

---

## Success Criteria

**Non-inferiority (primary)**: 90% CI upper bound of (control − treatment) < 3.0pp
**Throughput (secondary)**: Steady-state runs achieve ≥3x throughput (mutants/hour) vs generational
**Extension trigger**: If Wave 1 (N=2) is inconclusive, extend to N=3 per cell

---

## Monitoring Plan

`max_generations`: 25

- Gen 3 (~12%): smoke check — all PIDs alive, Redis keys growing, `[SteadyState]` log prefix present in S3/S4
- Gen 5 (~20%): first checkpoint — extract best-by-val, compare conditions
- Gen 13 (~50%): midpoint checkpoint — invoke checkpoint-analyst
- Gen 25 (100%): final evaluation + analysis

Early termination rule: None — all runs proceed to 25 generations.

---

## Pre-committed Diagnostics

At closeout, report per run:
- `total_mutations_attempted`
- `total_ghosts_swept`
- Interpretation rule: if steady-state attempts >10% more mutations than generational, acknowledge as confound

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

_(None yet. Post-registration changes require numbered entries here.)_
