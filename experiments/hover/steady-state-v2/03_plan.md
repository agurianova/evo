# Pre-Registration: hover/steady-state-v2

**Date**: 2026-03-27
**Protocol version**: 1.0
**Pre-registration commit**: `3e4faf3`
**GitHub PR**: #138 (branch: `exp/hover-steady-state-v2`)
**Tracking issue**: N/A
**Design doc**: `experiments/hover/steady-state-v2/01_design.md`
**Review doc**: `experiments/hover/steady-state-v2/02_review.md` (verdict: APPROVED)
**Evaluation script**: `experiments/hover/steady-state-v2/run_test_eval.sh` (sha256: TBD) — or N/A if no test split

---

## Hypothesis

**H₀**: μ_generational − μ_steady_state > 3.0pp (steady-state + LPT is inferior)
**H₁**: μ_generational − μ_steady_state ≤ 3.0pp (steady-state + LPT is non-inferior)
**Primary metric**: Best val fitness (soft fractional retrieval coverage) at gen/epoch 25
**Secondary metric**: Best val fitness at matched wall time (LOCF)
**Significance threshold**: α = 0.05

---

## Run Design Table

| Run | Label | Condition | `redis.db` | `evolution` | `scheduling` | `problem.name` | Extra overrides |
|-----|-------|-----------|------------|-------------|--------------|-----------------|-----------------|
| V1 | ctrl-1 | Control (generational + FIFO) | 3 | default | fifo | chains/hover/full | `[]` |
| V2 | ctrl-2 | Control (generational + FIFO) | 4 | default | fifo | chains/hover/full | `[]` |
| V3 | treat-1 | Treatment (steady-state + LPT) | 5 | steady_state | lpt | chains/hover/full | `[evolution=steady_state, scheduling=lpt]` |
| V4 | treat-2 | Treatment (steady-state + LPT) | 6 | steady_state | lpt | chains/hover/full | `[evolution=steady_state, scheduling=lpt]` |

All runs: `llm_base_url=http://10.232.30.185:4000/v1`, `model_name=Qwen3-235B-A22B-Thinking-2507`, `pipeline=standard`

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
| `llm_base_url` | `http://10.232.30.185:4000/v1` |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` |
| Chain server | LiteLLM proxy → 8-node Qwen3-8B (10.232.45.196:8000) |
| Mutation servers | LiteLLM proxy → 4x Qwen3-235B (port 8777) |
| `max_in_flight` | 5 (treatment only) |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature and nucleus sampling in chain and mutation LLMs
- Non-deterministic GPU floating point across hardware
- LiteLLM proxy routing (least-busy) introduces request-order non-determinism

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
| `problems/chains/hover/full/test.py` | `09bdd8cac1702c17f3a12cc17a2664b2a9f3b68503ba57c2a53b3736b467a6b6` |

---

## Success Criteria

- **Non-inferiority (primary)**: 90% CI upper bound of (control − treatment) < 3.0pp at gen/epoch 25
- **Non-inferiority (secondary)**: Same test at matched wall time T
- **If inconclusive**: Extend to N=3 per cell (Wave 2, DBs 7-8)
- **Throughput**: Report mutants/hour for both conditions; LPT expected to improve treatment throughput vs v1

---

## Monitoring Plan

`max_generations`: 25

- Gen 3 (~12%): smoke check — all PIDs alive, Redis keys growing, treatment shows `[SteadyState]` logs
- Gen 5 (~20%): first checkpoint — extract best-by-val, verify LPT active in cfg dump
- Gen 13 (~50%): midpoint checkpoint — compare fitness trajectories
- Gen 25 (100%): final evaluation + test eval + statistical analysis

Early termination rule: None — all runs proceed to gen 25. Run invalidated if PID dies before gen 5, Redis corrupted, or proxy down >4h.

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
