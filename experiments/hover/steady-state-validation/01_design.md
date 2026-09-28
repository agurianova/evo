# Experimental Design: hover/steady-state-validation

**Date**: 2026-03-26
**Researcher**: Dr. Elena Voss (ML Research Methodologist)
**Status**: Draft

---

## 1. Research Question

Does the `SteadyStateEvolutionEngine` produce fitness **non-inferior** to the generational `EvolutionEngine` on the HoVer dynamic-topology task (`chains/hover/full`)?

This is a validation experiment for a new engine implementation that eliminates the generational barrier via continuous mutation/evaluation interleaving. The engine is expected to improve throughput ~8-9x without degrading fitness.

## 2. Hypotheses

**Non-inferiority formulation** (one-sided):

**H₀**: μ_generational − μ_steady_state > δ (steady-state is inferior by more than the margin)
**H₁**: μ_generational − μ_steady_state ≤ δ (steady-state is non-inferior)

**Non-inferiority margin**: δ = 3.0pp validation fitness

**Justification for δ = 3.0pp**:
- Inter-run SD in dynamic-topology was ~1.3pp (treatment) and ~0.3pp (control)
- Even a 3pp fitness loss would keep performance well above GEPA benchmark (52.33% test)
- 3pp is approximately 2× the observed inter-run variability, a clinically meaningful threshold

## 3. Independent Variable(s)

| Variable | Control value | Treatment value |
|----------|---------------|-----------------|
| Evolution engine | `evolution=default` (generational) | `evolution=steady_state` |

**Single IV**: Only the engine type changes. Everything else is held constant.

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Best val fitness (soft fractional) | Best retrieval coverage across 900 val samples | **Yes** |
| Test coverage (discrete) | 5-repeat eval on 300-sample held-out test set | Secondary |
| Throughput (mutants/hour) | Wall clock time / total mutants produced | Secondary (expected: steady-state 3-8x faster; <2x warrants investigation) |
| Time to 80% val fitness | Wall clock hours to first hit 80% | Exploratory |

**Primary metric**: Best validation fitness (soft fractional retrieval coverage) when `engine:total_generations` reaches 25 (epoch 25 for steady-state, generation 25 for generational).

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| `problem.name` | `chains/hover/full` | Dynamic topology — best-performing variant |
| `pipeline` | `standard` | validate.py returns dict |
| `num_parents` | 1 | Match prior experiments |
| `max_elites_per_generation` | 8 | Default |
| `max_mutations_per_generation` | 8 | Default; also epoch size for steady-state |
| `max_generations` | 25 | Match dynamic-topology experiment |
| `llm` | `balanced` | Shared mutation server pool |
| `significant_change` | 0.003 | Match dynamic-topology |
| `stage_timeout` | 3000 | Match dynamic-topology |
| `dag_timeout` | 7200 | Match dynamic-topology |
| Chain servers | Qwen3-8B thinking mode | Same model/config |
| Mutation servers | Qwen3-235B-A22B-Thinking | Via balanced load balancer |
| `max_in_flight` | 8 | Steady-state only; matches `max_mutations_per_generation` |

## 6. Run Design Table

| Run | Label | Condition | `redis.db` | `evolution` | `problem.name` | `chain_url` |
|-----|-------|-----------|------------|-------------|-----------------|-------------|
| 1 | S1 | Control (generational) | 6 | default | chains/hover/full | TBD |
| 2 | S2 | Control (generational) | 7 | default | chains/hover/full | TBD |
| 3 | S3 | Treatment (steady-state) | 8 | steady_state | chains/hover/full | TBD |
| 4 | S4 | Treatment (steady-state) | 9 | steady_state | chains/hover/full | TBD |

**N = 2 per cell, 4 runs total.**

Chain URLs assigned at launch from `experiments/infrastructure.yaml` (1 dedicated chain server per run).

## 7. Sample Size Justification

N=2 per cell is the minimum for a t-test. This is a pragmatic choice driven by:
- 4 available chain server slots
- Each run takes ~15-20h wall time
- This is an engineering validation, not a discovery experiment
- We have strong prior from dynamic-topology (D5/D6 on same problem variant)

**MDE analysis (t-distribution, df=2)**:
- SE = SD × √(1/n₁ + 1/n₂) = 1.5 × √(1/2 + 1/2) = 1.5pp
- t₀.₀₅,df=2 = 2.92
- 90% CI half-width = 2.92 × 1.5 = 4.38pp → **exceeds δ=3.0pp**

At N=2 with SD=1.5pp, the non-inferiority test is almost certainly inconclusive. However, if the observed inter-run SD is closer to the 0.28pp seen in dynamic-topology control, the CI half-width drops to ~0.82pp and the test is well-powered.

**This is an exploratory non-inferiority experiment with pre-committed extension**:
- Wave 1: N=2 per cell (4 runs). If conclusive, stop.
- Wave 2 (expected): Extend to N=3 per cell (2 additional runs) if Wave 1 is inconclusive.
- Extension threshold: 90% CI of (control − treatment) includes both 0 and δ=3.0pp

## 8. Statistical Test

**Test**: One-sided Welch's t-test for non-inferiority
**Null**: μ_control − μ_treatment > 3.0pp
**Significance threshold**: α = 0.05
**How computed**: `scipy.stats.ttest_ind(control, treatment)`, then check if upper bound of (control − treatment) 90% CI < 3.0pp

**Decision rule**:
- If 90% CI upper bound of (control − treatment) < 3.0pp → **Non-inferior** (pass)
- If 90% CI lower bound of (control − treatment) > 0 → **Steady-state is actually worse** (investigate)
- If CI includes both 0 and 3.0pp → **Inconclusive** (extend to N=3)

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| Archive staleness in steady-state | Mechanistic feature — mutants may use stale parent selection between epochs | Not a confound; inherent to steady-state design. Epoch refresh every 8 programs bounds staleness |
| Mutation budget asymmetry | Medium — ghost sweeps in steady-state free slots without counting toward epoch trigger, allowing >8 mutation attempts per epoch | Pre-committed diagnostic: report `total_mutations_attempted` and `total_ghosts_swept` per run at closeout. If steady-state attempts >10% more mutations than generational, acknowledge as confound |
| Ingestion timing within epoch | Mechanistic feature — steady-state ingests individually (earlier mutants influence later parent selection within epoch); generational ingests all 8 simultaneously | Not a confound; inherent to the treatment. Acknowledged as mechanistic difference |
| Ghost program accumulation | Low — orphaned programs waste DagRunner capacity | Monitor via `[SteadyState] Sweeping` log lines; alert if >10% ghosts |
| Server load imbalance | Medium — different chain servers have different latencies | Use balanced LLM load balancer; assign chain servers randomly |
| Dynamic-topology invalidity | High — complex chains produce ~50-80% invalid programs | Same for both conditions; not a confound |
| Comparison to prior D5/D6 | N/A — we compare generational vs steady-state in this experiment, not to prior runs | Prior results are context only |

## 10. Stop Criteria

**Early termination**: None — all runs proceed to 25 generations.

**Run invalidation**: A run is invalidated if:
- PID dies before gen 5 (infrastructure failure)
- Redis DB is corrupted or flushed accidentally
- Chain server is down for >4 consecutive hours during the run
- Treatment verification fails (steady-state engine not actually active)

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Chain GPU hours | 4 × ~16h = ~64h (4 chain servers) |
| Mutation GPU hours | Shared via balanced LLM (existing servers) |
| Wall time | ~16-20h per run |
| Redis DBs used | 4 (DBs 6, 7, 8, 9) |

## 12. Treatment Verification

**What observable evidence proves the treatment is actually applied?**

1. **Log pattern**: Treatment runs (S3, S4) must show `[SteadyState]` log prefix; control runs (S1, S2) must NOT
2. **Hydra cfg dump**: Treatment runs must show `_target_: gigaevo.evolution.engine.SteadyStateEvolutionEngine`; control must show `_target_: gigaevo.evolution.engine.EvolutionEngine`
3. **Runtime behavior**: Treatment runs should produce mutants continuously (no "waiting for idle" pattern between mutations)
4. **Redis run_state**: Both conditions store `engine:total_generations` — comparable metric

**`extra_overrides` per condition**:
- Control (S1, S2): `[]` (no extra overrides — `evolution=default` is the base config)
- Treatment (S3, S4): `[evolution=steady_state]`

## 13. Open Questions / Risks

1. **Pre-launch**: All assigned Redis DBs (6, 7, 8, 9) will be flushed via `tools/flush.py` before launch
2. **First E2E use of SteadyStateEvolutionEngine** — smoke test (gen 3) is critical before full launch
2. **Epoch semantics**: Steady-state epoch ≈ generational step (both process 8 programs). But wall-clock time per epoch may differ significantly — steady-state epochs should complete faster
3. **If steady-state is clearly superior**: This experiment is designed for non-inferiority. If steady-state significantly *exceeds* generational fitness, the non-inferiority test will pass trivially, but the superiority signal may be interesting for future experiments
