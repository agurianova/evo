# Pre-Registration: HoVer Baseline -- Cold-Start Retrieval Coverage via n=4 Replication

**Date**: 2026-03-18
**Protocol version**: 1.0
**Pre-registration commit**: `9bcb905` <- committed BEFORE any code changes
**GitHub PR**: #90 (branch: `exp/hover-baseline`)
**Tracking issue**: #89
**Design doc**: `experiments/hover/baseline/01_design.md`
**Review doc**: `experiments/hover/baseline/02_review.md` (verdict: APPROVED, R2)
**Evaluation script**: `experiments/hover/baseline/run_test_eval.sh` (sha256: `875450b9d175e4ac51cb7d6026295d4ca155057d9bca5851b29c481fa1d08f80`)

---

## Hypothesis

**H0**: GigaEvo cold-start mean test retrieval coverage across n=4 runs is at most 52.33%
(the GEPA benchmark). Evolution does not reliably improve retrieval coverage beyond the
GEPA reference on this task.

**H1**: GigaEvo cold-start mean test retrieval coverage exceeds 52.33%. LLM-guided
mutation of the 7-step chain produces retrieval strategies that outperform GEPA's
fixed approach.

**Primary metric**: Test retrieval coverage at gen 25, best-by-val program, 300-sample
held-out test set, thinking mode Qwen3-8B.

**Significance threshold**: alpha = 0.05 (one-sided one-sample t-test, df=3)

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | `model_name` | `llm_base_url` | Seed | Val N |
|-----|-------|-----------|-----------|-----------|----------------|-------------|----------------|------|:-----:|
| H1 | hover-cold-1 | 9 | `standard` | `default` | `chains/hover/static` | `Qwen3-235B-A22B-Thinking-2507` | `http://10.226.72.211:8777/v1` | **Cold** | 300 |
| H2 | hover-cold-2 | 10 | `standard` | `default` | `chains/hover/static` | `Qwen3-235B-A22B-Thinking-2507` | `http://10.226.15.38:8777/v1` | **Cold** | 300 |
| H3 | hover-cold-3 | 11 | `standard` | `default` | `chains/hover/static` | `Qwen3-235B-A22B-Thinking-2507` | `http://10.226.185.47:8777/v1` | **Cold** | 300 |
| H4 | hover-cold-4 | 12 | `standard` | `default` | `chains/hover/static` | `Qwen3-235B-A22B-Thinking-2507` | `http://10.225.51.251:8777/v1` | **Cold** | 300 |

**Chain LLM assignment** (one per run):

| Run | `HOVER_CHAIN_URL` |
|-----|-------------------|
| H1 | `http://10.226.17.25:8001/v1` |
| H2 | `http://10.226.17.25:8000/v1` |
| H3 | `http://10.225.185.235:8001/v1` |
| H4 | `http://10.225.185.235:8000/v1` |

---

## Controlled Variables

| Field | Value |
|-------|-------|
| `num_parents` | **1** (default is 2; explicit override required) |
| `max_elites_per_generation` | **8** (default is 5; explicit override required) |
| `max_mutations_per_generation` | 8 |
| `stage_timeout` | **3000** (default is 2400; explicit override) |
| `dag_timeout` | **7200** (matches default; set explicitly for auditability) |
| `max_generations` | 25 |
| `mutation_mode` | `rewrite` |
| Chain LLM | Qwen3-8B, thinking mode ON, max_tokens=32768 |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism (document and accept):
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature and nucleus sampling in chain and mutation LLMs
- Non-deterministic GPU floating point across hardware

**Global seed**: N/A (GigaEvo does not support global seeding)

A fresh run with identical config will produce a different fitness trajectory but should
land in a statistically similar fitness range. Cross-experiment comparisons use effect-size
thresholds (from `01_design.md`) rather than exact trajectory matching.

---

## Dataset Checksums

Cryptographic anchor for the data used in this experiment.
Compute at pre-registration time and verify before final evaluation.

| File | sha256 |
|------|--------|
| `problems/chains/hover/dataset/HoVer_train.jsonl` | `1bfc935d667e405a51cfb0361d1ee672fa3475d82714bcf027fc2d1a2c5cdcfa` |
| `problems/chains/hover/dataset/HoVer_test.jsonl` | `1319ef6d1c16c879f4e8d3675df8ebf93be1387da6ee874d9fcdeaa0d56280a2` |

---

## Success Criteria

| Cold-start mean test coverage | Verdict |
|-------------------------------|---------|
| >= 60.0% (p < 0.05) | **STRONG POSITIVE** |
| [55.0%, 60.0%) (p < 0.05) | **POSITIVE** |
| (52.33%, 55.0%) (p < 0.05) | **SUGGESTIVE-SIG** |
| > 52.33% (p >= 0.05) | **SUGGESTIVE-NS** |
| <= 52.33% (p >= 0.05) | **NULL** |
| < 45.0% (any p) | **NEGATIVE** |

---

## Monitoring Plan

`max_generations`: 25

- Gen 3 (~12%): smoke check -- all PIDs alive, Redis keys growing, val coverage < 20% at gen 0
- Gen 5 (~20%): first checkpoint -- extract best-by-val, check invalidity rate, monitor eval times per host
- Gen 12 (~50%): midpoint checkpoint -- run test eval, check convergence trajectory
- Gen 25 (100%): final evaluation -- test eval all 4 runs, archive, analysis

Early termination rules:
- Gen-0 val coverage > 20% for any run: HALT (initialization error)
- Invalidity rate > 50% at gen 5: PAUSE and diagnose stage_timeout
- No improvement for >= 10 consecutive gens AND current gen >= 15: may terminate early (not invalidation)

---

## Pre-launch Verification Checklist

The `--cfg job` output for every run MUST confirm:
- [ ] `num_parents: 1` (NOT 2)
- [ ] `max_elites_per_generation: 8` (NOT 5)
- [ ] `pipeline_builder.stage_timeout: 3000` (NOT 2400)
- [ ] `pipeline_builder.dag_timeout: 7200`
- [ ] `model_name: Qwen3-235B-A22B-Thinking-2507` (NOT `deepseek/deepseek-v3.2`)
- [ ] `llm_base_url: http://<mutation_ip>:8777/v1` (NOT OpenRouter)
- [ ] `pipeline: standard`
- [ ] `problem.name: chains/hover/static`
- [ ] Redis DBs 9-12 show 0 keys (`tools/flush.py --db 9 10 11 12`)

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| H1 | ~~1923022~~ 1961916 | 2026-03-18 22:04 | DB=9, chain=10.226.17.25:8001, mut=10.226.72.211 (relaunch) |
| H2 | ~~1923023~~ 1961917 | 2026-03-18 22:04 | DB=10, chain=10.226.17.25:8000, mut=10.226.15.38 (relaunch) |
| H3 | ~~1923024~~ 1961918 | 2026-03-18 22:04 | DB=11, chain=10.225.185.235:8001, mut=10.226.185.47 (relaunch) |
| H4 | ~~1923025~~ 1961919 | 2026-03-18 22:04 | DB=12, chain=10.225.185.235:8000, mut=10.225.51.251 (relaunch) |

Watchdog PID: ~~1923422~~ 1962352
Launch commit: `97eed62`

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|

---

## Amendments

### Amendment 1: Redis DBs changed from 0-3 to 9-12

**Date**: 2026-03-19
**Reason**: Redis DBs 0-8 occupied by active vartodd circuit_evolve experiment. Cannot flush.
**Change**: H1=DB9, H2=DB10, H3=DB11, H4=DB12 (was 0,1,2,3).
**Confound**: No confound — DB number has no effect on evolution behavior.
All 4 runs still use distinct, empty DBs. Change applied uniformly to all runs.

### Amendment 2: Full relaunch after accidental exec worker kill

**Date**: 2026-03-19 22:04 UTC
**Reason**: User accidentally killed all exec_runner workers. Runs were at gen 2-3 but
appeared stalled (no gen progress in 60s). Clean restart chosen over resume to avoid
partial-generation artifacts.
**Change**: Flushed DBs 9-12, relaunched all 4 runs from cold start (gen 0).
New PIDs: H1=1961916, H2=1961917, H3=1961918, H4=1961919. Watchdog=1962352.
**Confound**: No confound — all 4 runs restart identically from gen 0. ~30 min of
wall time lost (gens 0-2). No data from the aborted runs is used.
