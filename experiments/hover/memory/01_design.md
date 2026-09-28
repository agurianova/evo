# Experimental Design: Memory-Augmented Evolution on HoVer 7-Step Dynamic Chains (No Deep Retrieval)

**Date**: 2026-04-03
**Researcher**: Dr. Elena Voss (ML Research Methodologist)
**Status**: Draft -- awaiting Reviewer-2

---

## 1. Research Question

Does memory-augmented mutation (episodic card-based memory from prior evolution runs) improve fitness on HoVer dynamic 7-step chains (standard retrieval only, no `retrieve_deep`) compared to standard evolution without memory?

### Motivation

The GigaEvo memory system was recently merged into main. It provides a card-based episodic memory that augments the mutation process with learned insights from prior runs. During evolution, the `MemorySelectorAgent` retrieves relevant memory cards and injects them into the mutation prompt, guiding the LLM to produce better mutations based on historically successful patterns.

We use the `chains/hover/full7_no_deep` variant: dynamic 7-step chains with only standard BM25 retrieval (k=7). The `retrieve_deep` tool (k=10) is excluded because it provides an unfair advantage over the GEPA benchmark (which uses k=7), and the hover/no-deep-retrieval experiment (PR #150) showed that `retrieve_deep` is unnecessary for dynamic chains (only 0.13pp delta). Using standard retrieval only ensures fair GEPA comparison.

The memory system operates in two phases:
1. **Memory bank building**: An initial evolution run with `ideas_tracker=true` extracts insights from the best programs and writes them as memory cards.
2. **Memory-augmented evolution**: Subsequent runs with `memory_enabled=true` read those cards and inject them into mutation prompts.

This experiment tests whether providing the mutation LLM with curated insights from a prior successful run improves convergence speed, final fitness, or both.

### Prior results

| Experiment | Topology | Engine | Val Fitness (soft) | Test Coverage (discrete) |
|------------|----------|--------|--------------------|----|
| hover/baseline (PR #90) | Static 7-step | Generational | ~54% | 51.65% |
| hover/7step-dynamic control (PR #144) | Static 7-step (static_soft) | Steady-state | 80.05% | 55.87% |
| hover/7step-dynamic treatment (PR #144) | Dynamic 7-step (full7) | Steady-state | 85.10% | 64.20% |
| hover/no-deep-retrieval C (PR #150) | Dynamic (full_no_deep) | Steady-state | -- | ~same as deep |

No prior experiment has tested the memory system.

---

## 2. Hypotheses

**H0**: Memory-augmented mutation does not improve best val soft fitness on dynamic 7-step chains compared to standard mutation (delta <= 0).
**H1**: Memory-augmented mutation improves best val soft fitness (delta > 0).

### Effect-size thresholds

| Delta (treatment - control) | Verdict |
|----|---------|
| >= +3.0pp | **STRONG POSITIVE** -- memory is a major advantage |
| [+1.5pp, +3.0pp) | **POSITIVE** -- memory meaningfully helps |
| (0pp, +1.5pp) | **SUGGESTIVE** -- directional but small |
| <= 0pp | **NULL** -- memory does not help |

---

## 3. Independent Variable(s)

| Variable | Control value | Treatment value |
|----------|---------------|-----------------|
| Memory-augmented mutation | `memory_enabled=false` (standard mutation only) | `memory_enabled=true` (mutation LLM receives memory cards from prior run) |

All other variables are held constant: same problem variant (`chains/hover/full7_no_deep`), engine (`steady_state`), scheduling (`lpt_chain`), infrastructure, and hyperparameters.

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Val soft fitness (best at gen 25) | `valid_frontier_fitness` from Redis | **Yes** |
| Test discrete coverage | 5-repeat test eval on 300-sample held-out set | Secondary |
| Convergence speed (gen to 80% val) | First gen where frontier crosses 80% | Secondary |
| Programs with memory metadata | Count of programs with `memory_selected_ids` metadata | Manipulation check |

**Primary metric**: Val soft fitness (best frontier value at gen 25).

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Problem variant | `chains/hover/full7_no_deep` | Dynamic 7-step, standard retrieval only (fair GEPA comparison) |
| Engine | `steady_state` | Proven in 7step-dynamic and SS-v2 |
| Scheduling | `lpt_chain` | Standard for steady-state |
| Max generations | 25 | Matches 7step-dynamic |
| Max in-flight | 8 | Standard steady-state parameter |
| Stage timeout | 6000 | Standard for hover |
| DAG timeout | 14400 | Standard for hover |
| Chain LLM | LiteLLM proxy (Qwen3-8B, thinking) | Shared infrastructure |
| Mutation LLM | LiteLLM proxy (Qwen3-235B, `llm=balanced`) | Shared infrastructure |
| Pipeline | `structural_metrics` | Required for 3D structural BC (computes dag_depth, max_fan_in, n_deep_retrieval) |
| MAP-Elites BC | 3D structural (`topology_3d_7step.yaml`) | Matches 7step-dynamic treatment |
| Seed program | `chains/hover/full7_no_deep` baseline | Same for all runs |
| Cold start | No `program_loader.problem_dir` | Clean start |

---

## 6. Experimental Protocol

This experiment has two sequential phases:

### Phase A: Memory Bank Building (1 run, ~24h)

A single evolution run with `ideas_tracker=true` to build the memory card bank. This run uses the same configuration as the control condition (no memory-augmented mutations). After the run completes, the ideas tracker extracts insights from the top 5% of programs and writes them as memory cards to `checkpoint_dir`.

- Run: M0 (memory bank builder)
- `memory_enabled=false`, `ideas_tracker=true`
- `checkpoint_dir=experiments/hover/memory/memory_bank`
- Redis DB: 3
- This run's fitness data is NOT used in the primary analysis (it is infrastructure for the treatment).

### Phase B: Controlled Experiment (4 runs, ~24h)

Two control runs (standard mutation) and two treatment runs (memory-augmented mutation reading from the Phase A memory bank).

| Run | Label | Cell | `memory_enabled` | `ideas_tracker` | `checkpoint_dir` | `redis.db` |
|-----|-------|------|-------------------|-----------------|-------------------|------------|
| R1 | ctrl-1 | Control | false | false | -- | 4 |
| R2 | ctrl-2 | Control | false | false | -- | 5 |
| R3 | mem-1 | Treatment | true | false | `experiments/hover/memory/memory_bank` | 6 |
| R4 | mem-2 | Treatment | true | false | `experiments/hover/memory/memory_bank` | 7 |

**N = 2 per condition, 2 conditions, 4 runs total.**

All Phase B runs share:
- Engine: `evolution=steady_state`, `scheduling=lpt_chain`
- Chain LLM: LiteLLM proxy at `http://10.232.30.185:4000/v1` (Qwen/Qwen3-8B, thinking mode)
- Mutation LLM: LiteLLM proxy (Qwen3-235B, `llm=balanced`)
- `pipeline=structural_metrics`
- `max_generations=25`, `max_in_flight=8`, `num_parents=1`, `max_elites_per_generation=8`, `max_mutations_per_generation=8`
- `stage_timeout=6000`, `dag_timeout=14400`
- MAP-Elites: `topology_3d_7step.yaml` (3D structural BC)
- Cold start

**Execution plan**: Phase B runs launch simultaneously after Phase A completes. The LiteLLM proxy handles load balancing.

**Redis DB assignments**: DB 3 (Phase A), DBs 4-7 (Phase B). All must be flushed before launch.

### `extra_overrides` per condition

- **Phase A (M0)**: `[evolution=steady_state, scheduling=lpt_chain, problem.name=chains/hover/full7_no_deep, ideas_tracker=true, checkpoint_dir=experiments/hover/memory/memory_bank]`
- **Control (R1, R2)**: `[evolution=steady_state, scheduling=lpt_chain, problem.name=chains/hover/full7_no_deep]`
- **Treatment (R3, R4)**: `[evolution=steady_state, scheduling=lpt_chain, problem.name=chains/hover/full7_no_deep, memory_enabled=true, checkpoint_dir=experiments/hover/memory/memory_bank]`

---

## 7. Sample Size Justification

N=2 per condition, pooled to N=2 per level. Using conservative SD = 1.5pp (from 7step-dynamic treatment: 85.10 +/- 1.56pp):

- SE = 1.5 * sqrt(1/2 + 1/2) = 1.5pp
- MDE at 80% power (t(0.10, df~2), one-sided): ~4.4pp

N=2 can detect STRONG POSITIVE effects (>= +3.0pp). If directional signal is observed but below MDE, a powered follow-up at N=4 per cell can be pre-committed.

---

## 8. Statistical Test

**Test**: One-sided Welch's t-test (H1: treatment > control)
**Significance threshold**: alpha = 0.10
**How computed**: Mean treatment val fitness minus mean control val fitness. Standard two-sample t-test with unequal variance assumption.

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Memory bank quality depends on Phase A run** -- if Phase A produces poor programs, memory cards will be low quality | Medium | Phase A uses proven configuration (full7_no_deep, steady-state, 3D BC). Monitor Phase A fitness before proceeding to Phase B. |
| 2 | **Memory cards may be stale** -- insights from one run may not generalize | Medium | This is part of what we're testing. If memory hurts or doesn't help, it suggests the insights don't transfer well. |
| 3 | **OpenRouter dependency** -- memory system uses OpenRouter for card analysis/dedup (gemini-3-flash-preview) | Low | OpenRouter is used only during ideas_tracker write (Phase A post-processing). Runtime memory retrieval during Phase B uses local embeddings only. |
| 4 | **Additional compute per mutation** -- memory-augmented mutations require MemorySelectorAgent query | Low | The query adds ~1-2s per mutation (local vector search). Negligible vs. chain evaluation time (~10min). Both conditions have the same evaluation budget (25 gens). |
| 5 | **Shared infrastructure contention** -- 4 simultaneous runs on LiteLLM proxy | Low | Both conditions experience identical contention. Noise is symmetric. |

---

## 10. Stop Criteria

**Early termination**: If all treatment runs have lower fitness than all control runs at gen 15, the experiment may be stopped early (descriptive NULL).

**Run invalidation**: A run is invalid if:
- Invalidity rate > 80% at gen 5
- PID dies before gen 10 with no recovery
- Redis corruption or data loss

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time Phase A | ~24h (1 run) |
| Wall time Phase B | ~24h (4 runs in parallel) |
| Total wall time | ~48h |
| Redis DBs | 5 (DBs 3-7) |
| Chain LLM | LiteLLM proxy (shared 8-node Qwen3-8B cluster) |
| Mutation LLM | LiteLLM proxy (Qwen3-235B, `llm=balanced`) |
| Test eval time | ~5 min/repeat x 5 repeats x 4 runs = ~100 min |
| New code | `chains/hover/full7_no_deep` problem variant (7-step max, no retrieve_deep) |

---

## 12. Treatment Verification

### Observable evidence that the treatment is correctly applied

| Check | Type | Control (R1, R2) | Treatment (R3, R4) |
|-------|------|-------------------|---------------------|
| `memory_enabled` in Hydra cfg | `config_override` | `false` | `true` |
| `checkpoint_dir` in Hydra cfg | `config_override` | `null` | `experiments/hover/memory/memory_bank` |
| Memory selector log messages | `log_pattern_present/absent` | ABSENT -- no "Selected ... memory idea(s)" | PRESENT -- "Selected ... memory idea(s) via red agent" |
| Programs with memory metadata | `program_structure` | No `memory_selected_ids` in program metadata | Some programs have `memory_selected_ids` |
| Memory bank exists before Phase B | `precondition` | N/A | `memory_bank/` dir contains card files |

### Manipulation check at gen 5

Count programs in treatment runs that have `memory_selected_ids` in their metadata. If < 10% of programs have memory metadata by gen 5, the memory selector is failing silently.

---

## 13. Open Questions / Risks

1. **Dependency installation**: The memory system requires `sentence-transformers` and access to OpenRouter API. These must be verified during implementation.
2. **Memory card format**: The ideas tracker may produce cards of varying quality. No prior HoVer run has tested the ideas tracker pipeline.
3. **Checkpoint directory lifecycle**: The `checkpoint_dir` must persist between Phase A and Phase B. NFS should handle this, but verify.

---

*Ready for Reviewer-2's scrutiny.*
