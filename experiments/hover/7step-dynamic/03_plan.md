# Pre-Registration: hover/7step-dynamic

**Date**: 2026-03-30
**Protocol version**: 1.0
**Pre-registration commit**: `f55a8a1`
**GitHub PR**: #TBD (branch: `exp/hover-7step-dynamic`)
**Design doc**: `experiments/hover/7step-dynamic/01_design.md` (R1)
**Review doc**: `experiments/hover/7step-dynamic/02_review.md` (verdict: NEEDS REVISION → R1 addresses all concerns)

---

## Hypothesis

**H0**: mu_treatment - mu_control <= 0 (topology flexibility within a 7-step budget does not improve best val fitness)
**H1**: mu_treatment - mu_control > 0 (topology flexibility within a 7-step budget improves best val fitness)
**Primary metric**: Best `valid_frontier_fitness` at gen 25 (or last completed epoch if gen 25 not reached within 48h)
**Significance threshold**: alpha = 0.10 (one-sided Welch's t-test)

**Secondary (H_div)**: Treatment maintains more distinct (dag_depth, max_fan_in, n_deep_retrieval) cells + higher Shannon entropy. Descriptive only, no multiplicity adjustment.

**3D Behavior Space (treatment)**:
- `dag_depth` [1,7], 4 bins
- `max_dependency_fan_in` [1,6], 3 bins
- `n_deep_retrieval` [0,4], 5 bins
- Total: 4 × 3 × 5 = 60 cells (matches control's 60 fitness bins)

---

## Run Design Table

| Run | Label | Condition | `redis.db` | `problem.name` | `extra_overrides` |
|-----|-------|-----------|------------|-----------------|-------------------|
| 1 | V1 | Control | 3 | `chains/hover/static_soft` | `evolution=steady_state scheduling=lpt primary_resolution=60` |
| 2 | V2 | Control | 4 | `chains/hover/static_soft` | `evolution=steady_state scheduling=lpt primary_resolution=60` |
| 3 | V3 | Treatment | 5 | `chains/hover/full7` | `evolution=steady_state scheduling=lpt algorithm=topology_3d_7step` |
| 4 | V4 | Treatment | 6 | `chains/hover/full7` | `evolution=steady_state scheduling=lpt algorithm=topology_3d_7step` |

All runs: `pipeline=structural_metrics`, `llm=balanced`, mutation via LiteLLM proxy.
**N = 2 per condition, 4 runs total.**

---

## Controlled Variables

| Field | Value |
|-------|-------|
| Engine | `evolution=steady_state` |
| Scheduling | `scheduling=lpt` |
| Pipeline | `structural_metrics` (ChainStructuralMetricsStage on ALL arms) |
| Mutation LLM | Qwen3-235B via LiteLLM proxy |
| Chain LLM | Qwen3-8B thinking via LiteLLM proxy |
| max_in_flight | 8 |
| max_generations | 25 |
| island_max_size | 75 |
| Val set | First 300 samples of HoVer train |
| Max step budget | 7 (both conditions) |

---

## Manipulation Check (R1, per Reviewer-2)

At gen 5: compute fraction of treatment programs whose `(n_steps, n_tool_steps, dag_depth)` differs from seed `(7, 3, 7)`. If < 10%, flag IV as potentially inactive.

---

## Success Criteria

- **Primary**: Treatment mean val fitness > control mean val fitness (one-sided p < 0.10)
- **Secondary (descriptive)**: Treatment shows more occupied cells and higher Shannon entropy
- **Exploratory**: Test coverage improvement

**Effect-size thresholds**:

| Delta | Verdict | Detectable at N=2? |
|-------|---------|-------------------|
| >= +3.0pp | STRONG POSITIVE | Marginally |
| +1.5 to +3.0pp | POSITIVE | No (requires N=4) |
| 0 to +1.5pp | INCONCLUSIVE | No (requires N=4) |
| <= 0pp | NULL | Yes |

---

## N=4 Extension Protocol

**Trigger**: delta > +1.0pp but p > 0.10 at N=2.
**Analysis**: Welch's t-test at alpha=0.10 (one-sided) on all 8 runs.
**N=2 result**: Descriptive only.
**Limitation (R1)**: Effective Type I error rate of this sequential procedure not analytically computed.
**Extension DBs**: 7, 8, 9, 10.

---

## Generation-Count Normalization (R1)

If generation counts differ by > 3 across conditions at 48h cutoff, analysis uses minimum completed generation across all runs.

---

## Monitoring Plan

`max_generations`: 25
**Wall time budget**: 48h

- Gen ~5 (~20%): manipulation check — are treatment programs structurally diverging from seed?
- Gen ~13 (~50%): midpoint checkpoint — fitness, archive diversity, test eval
- Gen 25 (100%) or 48h: final evaluation + analysis

---

## New Artifacts Required

1. `problems/chains/hover/full7/` — copy of `full/` with `max_steps=7`
2. `config/algorithm/topology_3d_7step.yaml` — copy of `topology_3d.yaml` with bounds adjusted for 7-step chains

---

## Dataset Checksums

| File | sha256 |
|------|--------|
| `problems/chains/hover/dataset/HoVer_train.jsonl` | `1bfc935d667e405a51cfb0361d1ee672fa3475d82714bcf027fc2d1a2c5cdcfa` |
| `problems/chains/hover/dataset/HoVer_test.jsonl` | `1319ef6d1c16c879f4e8d3675df8ebf93be1387da6ee874d9fcdeaa0d56280a2` |
| `problems/chains/hover/full/test.py` | `09bdd8cac1702c17f3a12cc17a2664b2a9f3b68503ba57c2a53b3736b467a6b6` |

---

## Amendments

_(Add numbered entries here for any post-registration changes.)_
