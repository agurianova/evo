# Pre-Registration: hover/map-elites-topology

**Date**: 2026-03-29
**Protocol version**: 1.0
**Pre-registration commit**: `<hash>` (to be filled after commit)
**GitHub PR**: #TBD (branch: `exp/hover-map-elites-topology`)
**Tracking issue**: TBD
**Design doc**: `experiments/hover/map-elites-topology/01_design.md` (R1)
**Review doc**: `experiments/hover/map-elites-topology/02_review.md` (verdict: APPROVED)
**Evaluation script**: `experiments/hover/map-elites-topology/run_test_eval.sh` (to be created during implementation)

---

## Hypothesis

**H0**: mu_treatment - mu_control <= 0 (3D structural BC binning does not improve best val fitness)
**H1**: mu_treatment - mu_control > 0 (3D structural BC binning improves best val fitness)
**Primary metric**: Best `valid_frontier_fitness` at gen 25 (or last completed epoch if gen 25 not reached within 48h) on val set (soft fractional retrieval coverage)
**Significance threshold**: alpha = 0.10 (one-sided Welch's t-test)

**Secondary (H_div)**: Treatment maintains more distinct (dag_depth, max_fan_in, n_deep_retrieval) cells + higher Shannon entropy of cell-occupancy distribution. Descriptive only, no multiplicity adjustment.

**3D Behavior Space (treatment)**:
- `dag_depth` [1,11], 5 bins — sequential chain length
- `max_fan_in` [1,9], 5 bins — evidence gathering pattern
- `n_deep_retrieval` [0,5], 6 bins — retrieval aggressiveness
- Total: 5 x 5 x 6 = 150 cells (matches control's 150 fitness bins)

---

## Run Design Table

| Run | Label | Condition | `redis.db` | `pipeline` | `problem.name` | `extra_overrides` |
|-----|-------|-----------|------------|-----------|----------------|-------------------|
| 1 | V1 | Control | 3 | standard | chains/hover/full | `evolution=steady_state scheduling=lpt` |
| 2 | V2 | Control | 4 | standard | chains/hover/full | `evolution=steady_state scheduling=lpt` |
| 3 | V3 | Treatment | 5 | standard | chains/hover/full | `evolution=steady_state scheduling=lpt algorithm=topology_3d` |
| 4 | V4 | Treatment | 6 | standard | chains/hover/full | `evolution=steady_state scheduling=lpt algorithm=topology_3d` |

All runs use: `llm=balanced`, mutation LLM via LiteLLM proxy at `10.232.30.185:4000/v1`.
**N = 2 per condition, 4 runs total.**

---

## Controlled Variables

| Field | Value |
|-------|-------|
| Engine | `evolution=steady_state` (SteadyStateEvolutionEngine) |
| Scheduling | `scheduling=lpt` (LPTPrioritizer) |
| Problem | `chains/hover/full` (dynamic topology, soft fitness, max 10 steps) |
| Pipeline | `standard` |
| Mutation LLM | Qwen3-235B-A22B-Thinking via LiteLLM proxy |
| Chain LLM | Qwen3-8B thinking via LiteLLM proxy (8 endpoints) |
| max_in_flight | 8 |
| max_generations | 25 |
| island_max_size | 75 |
| Val set | First 300 samples of HoVer train |
| ChainStructuralMetricsStage | Runs on ALL runs (control + treatment) to avoid pipeline confound |
| DB-to-condition assignment | V1/V2 (DBs 3,4) = control, V3/V4 (DBs 5,6) = treatment (non-randomized) |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature and nucleus sampling in chain and mutation LLMs
- Non-deterministic GPU floating point across hardware
- Steady-state engine: evaluation order depends on wall-clock timing of LLM responses

**Global seed**: N/A (stochastic LLM evolution)

---

## Dataset Checksums

| File | sha256 |
|------|--------|
| `problems/chains/hover/dataset/HoVer_train.jsonl` | `1bfc935d667e405a51cfb0361d1ee672fa3475d82714bcf027fc2d1a2c5cdcfa` |
| `problems/chains/hover/dataset/HoVer_test.jsonl` | `1319ef6d1c16c879f4e8d3675df8ebf93be1387da6ee874d9fcdeaa0d56280a2` |
| `problems/chains/hover/full/test.py` | `09bdd8cac1702c17f3a12cc17a2664b2a9f3b68503ba57c2a53b3736b467a6b6` |

---

## Success Criteria

- **Primary**: Treatment mean val fitness > control mean val fitness (one-sided p < 0.10)
- **Secondary (descriptive)**: Treatment shows more occupied cells and higher Shannon entropy than control
- **Exploratory**: Test coverage improvement over SS-v2 baseline (~83.8%)

**Effect-size thresholds** (with N=2 detectability):

| Delta | Verdict | Detectable at N=2? |
|-------|---------|-------------------|
| >= +3.0pp | STRONG POSITIVE | Marginally |
| +1.5 to +3.0pp | POSITIVE | No (requires N=4) |
| 0 to +1.5pp | SUGGESTIVE | No (requires N=4) |
| <= 0pp | NULL | Yes |

---

## N=4 Extension Protocol

**Trigger**: delta > +1.0pp but p > 0.10 at N=2.
**Analysis**: Welch's t-test at alpha=0.10 (one-sided) on all 8 runs (4 per condition).
**N=2 result**: Descriptive only. Not used in the N=4 formal test.
**Alpha adjustment**: None (N=2 result is non-binding).
**Extension DBs**: 7, 8, 9, 10.

---

## Monitoring Plan

`max_generations`: 25
**Wall time budget**: 48h

- Epoch ~3 (~12%): smoke check -- all PIDs alive, Redis keys growing, treatment has dag_depth/max_fan_in/n_deep_retrieval in program.metrics
- Epoch ~5 (~20%): first checkpoint -- extract best-by-val, check archive diversity (occupied cells, Shannon entropy)
- Epoch ~13 (~50%): midpoint checkpoint -- run test eval on best-by-val programs
- Epoch 25 (100%) or 48h wall time: final evaluation + analysis

**Early termination**: If treatment runs show no `dag_depth` in program.metrics by epoch 3, the structural metrics stage is broken -- stop, debug, restart.

**Endpoint if gen 25 not reached**: Use fitness at last completed epoch. This is pre-registered.

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
