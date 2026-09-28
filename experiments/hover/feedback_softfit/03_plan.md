# Pre-Registration: HoVer Feedback + Soft Fitness -- Disentangling Two Mutation Signal Deficits

**Date**: 2026-03-20
**Protocol version**: 1.0
**Pre-registration commit**: `5f07a3b` <- committed BEFORE any code changes
**GitHub PR**: TBD (branch: `exp/hover-feedback-softfit`)
**Tracking issue**: #89 (shared with baseline)
**Design doc**: `experiments/hover/feedback_softfit/01_design.md`
**Review doc**: `experiments/hover/feedback_softfit/02_review.md` (verdict: APPROVED, R2)
**Evaluation script**: `experiments/hover/baseline/run_test_eval.sh` (sha256: `2bc5987e3f150959e45aee0626fa265630c0a80c0d29427369ee4b28abb4d472`)

---

## Hypothesis

**H0**: None of the three treatment conditions (feedback-only, soft-fitness-only,
feedback+soft-fitness) produces a mean test retrieval coverage that exceeds the baseline
mean by more than 2.0pp (the noise floor estimated from baseline inter-run SD).

**H1**: At least one treatment condition produces a mean test retrieval coverage that
exceeds the baseline mean by more than 2.0pp, indicating that the addressed deficit was
indeed a binding constraint on evolutionary performance.

**Primary metric**: Test retrieval coverage at gen 25, best-by-val program, 300-sample
held-out test set, discrete scoring, thinking mode Qwen3-8B, 5 repeats per run.

**Significance threshold**: alpha = 0.05 (one-sided Welch's two-sample t-test)

---

## Run Design Table

| Run | Label | Cell | `redis.db` | `pipeline` | `problem.name` | `model_name` | Mutation LLM URL | Chain LLM URL |
|-----|-------|------|-----------|-----------|----------------|-------------|------------------|---------------|
| F1 | hover-fb-1 | B (feedback) | 9 | `hover_feedback` | `chains/hover/static` | `Qwen3-235B-A22B-Thinking-2507` | `http://10.226.72.211:8777/v1` | `http://10.226.17.25:8001/v1` |
| F2 | hover-fb-2 | B (feedback) | 10 | `hover_feedback` | `chains/hover/static` | `Qwen3-235B-A22B-Thinking-2507` | `http://10.226.15.38:8777/v1` | `http://10.225.185.235:8001/v1` |
| F3 | hover-soft-1 | C (soft) | 11 | `standard` | `chains/hover/static_soft` | `Qwen3-235B-A22B-Thinking-2507` | `http://10.226.185.47:8777/v1` | `http://10.226.17.25:8000/v1` |
| F4 | hover-soft-2 | C (soft) | 12 | `standard` | `chains/hover/static_soft` | `Qwen3-235B-A22B-Thinking-2507` | `http://10.225.51.251:8777/v1` | `http://10.225.185.235:8000/v1` |

**Host shuffling**: F1=host A, F2=host B, F3=host A, F4=host B (eliminates host-treatment confound).

**Baseline (Cell A, n=4)**: H1-H4 from PR #90. Test coverage means: H1=51.20%, H2=52.47%, H3=51.93%, H4=TBD.

---

## Controlled Variables

| Field | Value |
|-------|-------|
| `num_parents` | **1** (default is 2; explicit override required) |
| `max_elites_per_generation` | **8** (default is 5; explicit override required) |
| `max_mutations_per_generation` | 8 |
| `stage_timeout` | **3000** (default is 2400; explicit override) |
| `dag_timeout` | **7200** (explicit override) |
| `max_generations` | 25 |
| `mutation_mode` | `rewrite` |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` (explicit override; default is OpenRouter) |
| Chain LLM | Qwen3-8B, thinking mode ON, max_tokens=32768 |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 |
| Test metric | **Discrete** retrieval coverage for ALL conditions (including cell C) |
| `significant_change` | 0.01 (cells A, B) / 0.003 (cell C -- fractional scoring) |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism (document and accept):
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature and nucleus sampling in chain and mutation LLMs
- Non-deterministic GPU floating point across hardware

**Global seed**: N/A (GigaEvo does not support global seeding)

---

## Dataset Checksums

| File | sha256 |
|------|--------|
| `problems/chains/hover/dataset/HoVer_train.jsonl` | `1bfc935d667e405a51cfb0361d1ee672fa3475d82714bcf027fc2d1a2c5cdcfa` |
| `problems/chains/hover/dataset/HoVer_test.jsonl` | `1319ef6d1c16c879f4e8d3675df8ebf93be1387da6ee874d9fcdeaa0d56280a2` |

## Evaluation Script Checksums

| File | sha256 |
|------|--------|
| `problems/chains/hover/static/test.py` | `95c735868957de483926ca5a317d1b37f853ff534be10fccea755660c2275307` |
| `experiments/hover/baseline/run_test_eval.sh` | `2bc5987e3f150959e45aee0626fa265630c0a80c0d29427369ee4b28abb4d472` |

---

## Success Criteria

| Treatment mean - baseline mean | Verdict |
|-------------------------------|---------|
| >= +5.0pp | **STRONG POSITIVE** |
| [+2.0pp, +5.0pp) | **POSITIVE** |
| (0pp, +2.0pp) | **SUGGESTIVE** |
| <= 0pp | **NULL** |

---

## Monitoring Plan

`max_generations`: 25

- Gen 3 (~12%): smoke check -- all PIDs alive, Redis keys growing, gen-0 coverage check
- Gen 5 (~20%): first checkpoint -- invalidity rate, eval times
- Gen 12 (~50%): midpoint -- run test eval, convergence trajectory
- Gen 25 (100%): final evaluation -- test eval all 4 runs, archive, analysis

Early termination rules:
- Gen-0 val coverage > 20% for any run: HALT (initialization error)
- Invalidity rate > 50% at gen 5: PAUSE and diagnose stage_timeout
- Cell B: validate.py fitness differs from baseline: HALT (code bug)
- No improvement for >= 10 consecutive gens AND current gen >= 15: may terminate early

---

## Pre-launch Verification Checklist

The `--cfg job` output for every run MUST confirm:
- [ ] `num_parents: 1` (NOT 2)
- [ ] `max_elites_per_generation: 8` (NOT 5)
- [ ] `pipeline_builder.stage_timeout: 3000` (NOT 2400)
- [ ] `pipeline_builder.dag_timeout: 7200`
- [ ] `model_name: Qwen3-235B-A22B-Thinking-2507` (NOT `deepseek/deepseek-v3.2`)
- [ ] `llm_base_url` matches per-run mutation LLM URL
- [ ] F1, F2: `pipeline: hover_feedback`
- [ ] F3, F4: `pipeline: standard`
- [ ] F1, F2: `problem.name: chains/hover/static`
- [ ] F3, F4: `problem.name: chains/hover/static_soft`
- [ ] Redis DBs 9-12 show 0 keys
- [ ] Cell B validate.py fitness == baseline validate.py fitness on gen-0 program
- [ ] Cell C `initial_programs/baseline.py` SHA-256 matches Cell A
- [ ] `hover_feedback.yaml` has `prompts_dir: ${prompts.dir}` in both blocks
- [ ] test.py SHA-256 unchanged from baseline

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| F1 | 2597123 | 2026-03-19 23:06 | DB=9, cell=B(feedback), chain=10.226.17.25:8001, mut=10.226.72.211 |
| F2 | 2597124 | 2026-03-19 23:06 | DB=10, cell=B(feedback), chain=10.225.185.235:8001, mut=10.226.15.38 |
| F3 | 2597125 | 2026-03-19 23:06 | DB=11, cell=C(soft), chain=10.226.17.25:8000, mut=10.226.185.47 |
| F4 | 2597126 | 2026-03-19 23:06 | DB=12, cell=C(soft), chain=10.225.185.235:8000, mut=10.225.51.251 |

Watchdog PID: 2597449
Launch commit: `a3f480c`

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|

---

## Amendments

(none yet)
