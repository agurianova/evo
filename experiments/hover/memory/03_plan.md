# Pre-Registration: hover/memory

**Date**: 2026-04-03
**Protocol version**: 1.0
**Pre-registration commit**: `<hash>` -- commit this file BEFORE any code changes
**GitHub PR**: #<number> (branch: `exp/hover-memory`)
**Tracking issue**: N/A
**Design doc**: `experiments/hover/memory/01_design.md`
**Review doc**: `experiments/hover/memory/02_review.md` (verdict: APPROVED)
**Evaluation script**: `experiments/hover/memory/run_test_eval.sh` (sha256: TBD)

---

## Hypothesis

**H0**: Memory-augmented mutation does not improve best val soft fitness on dynamic 7-step chains (no deep retrieval) compared to standard mutation (delta <= 0).
**H1**: Memory-augmented mutation improves best val soft fitness (delta > 0).
**Primary metric**: Val soft fitness (best frontier) at gen 25
**Significance threshold**: alpha = 0.10

---

## Run Design Table

### Phase A: Memory Bank Building

| Run | Label | `redis.db` | `pipeline` | `problem.name` | Key overrides |
|-----|-------|------------|-----------|----------------|------|
| M0 | mem-bank | 3 | standard | `chains/hover/full7_no_deep` | `ideas_tracker=true checkpoint_dir=experiments/hover/memory/memory_bank` |

### Phase B: Controlled Experiment

| Run | Label | `redis.db` | `pipeline` | `problem.name` | Key overrides |
|-----|-------|------------|-----------|----------------|------|
| R1 | ctrl-1 | 4 | standard | `chains/hover/full7_no_deep` | (none) |
| R2 | ctrl-2 | 5 | standard | `chains/hover/full7_no_deep` | (none) |
| R3 | mem-1 | 6 | standard | `chains/hover/full7_no_deep` | `memory_enabled=true checkpoint_dir=experiments/hover/memory/memory_bank` |
| R4 | mem-2 | 7 | standard | `chains/hover/full7_no_deep` | `memory_enabled=true checkpoint_dir=experiments/hover/memory/memory_bank` |

---

## Controlled Variables

| Field | Value |
|-------|-------|
| Engine | `evolution=steady_state` |
| Scheduling | `scheduling=lpt_chain` |
| Max generations | 25 |
| Max in-flight | 8 |
| Stage timeout | 6000 |
| DAG timeout | 14400 |
| Chain LLM | LiteLLM proxy (Qwen3-8B, thinking) |
| Mutation LLM | LiteLLM proxy (Qwen3-235B, balanced) |
| MAP-Elites BC | 3D structural (topology_3d_7step.yaml) |
| Seed | `chains/hover/full7_no_deep` baseline |
| Start | Cold start (no program_loader.problem_dir) |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- LLM sampling temperature and nucleus sampling in chain and mutation LLMs
- Non-deterministic GPU floating point across hardware
- Memory card retrieval may vary based on embedding similarity thresholds

**Global seed**: N/A

A fresh run with identical config will produce a different fitness trajectory but should
land in a statistically similar fitness range.

---

## Dataset Checksums

| File | sha256 |
|------|--------|
| `problems/chains/hover/dataset/HoVer_train.jsonl` | `1bfc935d667e405a51cfb0361d1ee672fa3475d82714bcf027fc2d1a2c5cdcfa` |
| `problems/chains/hover/dataset/HoVer_test.jsonl` | `1319ef6d1c16c879f4e8d3675df8ebf93be1387da6ee874d9fcdeaa0d56280a2` |

---

## Success Criteria

| Delta (treatment - control) | Verdict |
|----|---------|
| >= +3.0pp | **STRONG POSITIVE** |
| [+1.5pp, +3.0pp) | **POSITIVE** |
| (0pp, +1.5pp) | **SUGGESTIVE** |
| <= 0pp | **NULL** |

---

## Monitoring Plan

`max_generations`: 25

Phase A:
- Gen 3 (~12%): smoke check -- PID alive, Redis keys growing, ideas tracker config loaded
- Gen 10 (~40%): midpoint -- check val fitness > 70% (minimum viable quality for memory bank)
- Gen 25 (100%): Phase A complete -- verify ideas tracker wrote memory cards to checkpoint_dir

Phase B:
- Gen 3 (~12%): smoke check -- all 4 PIDs alive, treatment runs show memory selector log messages
- Gen 5 (~20%): manipulation check -- treatment runs have programs with `memory_selected_ids` metadata
- Gen 15 (~60%): midpoint checkpoint -- extract trajectories
- Gen 25 (100%): final evaluation + test eval

Early termination: If all treatment runs have lower fitness than all control runs at gen 15.

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
