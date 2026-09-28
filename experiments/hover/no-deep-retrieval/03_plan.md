# Pre-Registration: hover/no-deep-retrieval

**Date**: 2026-04-01
**Protocol version**: 1.0
**Pre-registration commit**: `952476a56c6b598d7b437f670842f267d591edfb` ← filled after commit
**GitHub PR**: #150 (branch: `exp/hover-no-deep-retrieval`)
**Design doc**: `experiments/hover/no-deep-retrieval/01_design.md`
**Review doc**: `experiments/hover/no-deep-retrieval/02_review.md` (verdict: APPROVED)
**Evaluation script**: `experiments/hover/no-deep-retrieval/run_test_eval.sh` (sha256: TBD)

---

## Hypothesis

**H₀**: Removing `retrieve_deep` (k=10) does not reduce test discrete retrieval coverage compared to runs with both retrieval tools.
**H₁**: `retrieve_deep` improves test discrete retrieval coverage (deep > standard).
**Primary metric**: Test discrete retrieval coverage at gen 25, 5-repeat mean per run.
**Significance threshold**: α = 0.10 (one-sided Welch's t-test)

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `problem.name` | Condition | Engine | Scheduling |
|-----|-------|------------|-----------|-----------------|-----------|--------|-----------|
| R1 | static-std-1 | 3 | standard | `chains/hover/static_soft_no_deep` | A: static + standard | steady_state | lpt_chain |
| R2 | static-std-2 | 4 | standard | `chains/hover/static_soft_no_deep` | A: static + standard | steady_state | lpt_chain |
| R3 | static-deep-1 | 5 | standard | `chains/hover/static_soft` | B: static + deep | steady_state | lpt_chain |
| R4 | static-deep-2 | 6 | standard | `chains/hover/static_soft` | B: static + deep | steady_state | lpt_chain |
| R5 | dynamic-std-1 | 7 | standard | `chains/hover/full_no_deep` | C: dynamic + standard | steady_state | lpt_chain |
| R6 | dynamic-std-2 | 8 | standard | `chains/hover/full_no_deep` | C: dynamic + standard | steady_state | lpt_chain |
| R7 | dynamic-deep-1 | 9 | standard | `chains/hover/full` | D: dynamic + deep | steady_state | lpt_chain |
| R8 | dynamic-deep-2 | 10 | standard | `chains/hover/full` | D: dynamic + deep | steady_state | lpt_chain |

All runs: LiteLLM proxy for chain + mutation LLMs. `max_generations=25`, `max_in_flight=8`.

---

## Controlled Variables

| Field | Value |
|-------|-------|
| `num_parents` | 1 |
| `max_elites_per_generation` | 8 |
| `max_mutations_per_generation` | 8 |
| `stage_timeout` | 6000 |
| `dag_timeout` | 14400 |
| `mutation_mode` | rewrite |
| Chain LLM | Qwen/Qwen3-8B (thinking mode) via LiteLLM proxy |
| Mutation LLM | Qwen3-235B via LiteLLM proxy (`llm=balanced`) |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- LLM sampling temperature and nucleus sampling
- `random.sample` in FormatterStage
- Non-deterministic GPU floating point

**Global seed**: N/A

---

## Dataset Checksums

| File | sha256 |
|------|--------|
| `problems/chains/hover/dataset/HoVer_train.jsonl` | `1bfc935d667e405a51cfb0361d1ee672fa3475d82714bcf027fc2d1a2c5cdcfa` |
| `problems/chains/hover/dataset/HoVer_test.jsonl` | `1319ef6d1c16c879f4e8d3675df8ebf93be1387da6ee874d9fcdeaa0d56280a2` |

---

## Success Criteria

### Effect-size thresholds (deep minus standard, pooled)

| Delta | Verdict |
|-------|---------|
| >= +4.0pp | STRONG POSITIVE — deep is major advantage, GEPA comparison confounded |
| [+2.0pp, +4.0pp) | POSITIVE — deep helps meaningfully |
| (0pp, +2.0pp) | SUGGESTIVE — directional but small |
| <= 0pp | NULL — deep provides no benefit, drop from future experiments |

### Replication check

Cell B (static + deep) test coverage must fall in 51-54% (historical baseline range). If not, investigate before interpreting ablation.

### GEPA-fair comparison

Cell C (dynamic + standard) mean > 52.33% → GigaEvo adds value beyond retrieval budget.

---

## Monitoring Plan

`max_generations`: 25

- Gen 3 (~12%): smoke check — all PIDs alive, Redis keys growing
- Gen 5 (~20%): first checkpoint — extract best-by-val, check invalidity rates
- Gen 12 (~50%): midpoint checkpoint
- Gen 25 (100%): final evaluation + analysis

Early termination rule: If invalidity rate > 90% in any no-deep dynamic run (R5/R6) at gen 5, the mutation LLM cannot adapt to the restricted tool set. Pause and investigate task_description.txt.

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|

Watchdog PID:
Launch commit: `952476a56c6b598d7b437f670842f267d591edfb`

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|

---

## Amendments

_(Add numbered entries here for any post-registration changes.)_
