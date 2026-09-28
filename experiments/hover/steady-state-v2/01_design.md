# Experimental Design: hover/steady-state-v2

**Date**: 2026-03-27
**Researcher**: Dr. Elena Voss (ML Research Methodologist)
**Status**: Draft

---

## 1. Research Question

Does the steady-state evolution engine with LPT (Longest Processing Time first) scheduling produce fitness **non-inferior** to the standard generational engine with FIFO scheduling on the HoVer task, when deployed on the new server infrastructure with LiteLLM load balancing?

This is a v2 follow-up to `hover/steady-state-validation` (v1), which ran on the old infrastructure with dedicated per-run chain/mutation servers. V1 revealed that steady-state epochs are ~3x slower in wall time than generational generations, making generation-count comparisons misleading. V2 addresses this by (a) introducing LPT scheduling to reduce tail latency, (b) running on the new 8-node chain cluster with LiteLLM proxy, and (c) pre-committing to wall-time comparisons as a secondary metric.

**Important**: Results from v2 are NOT directly comparable to v1 due to different infrastructure (8-node chain cluster vs. dedicated per-run chain servers, LiteLLM proxy vs. direct endpoints, `llm=balanced` mutation load balancing vs. dedicated mutation servers).

---

## 2. Hypotheses

**Non-inferiority formulation** (one-sided):

**H0**: mu_generational - mu_steady_state > delta (steady-state is inferior by more than the margin)
**H1**: mu_generational - mu_steady_state <= delta (steady-state is non-inferior)

**Non-inferiority margin**: delta = 3.0pp validation fitness

**Justification for delta = 3.0pp**:
- Inter-run SD in the HoVer baseline was 0.63pp (N=4); in dynamic-topology control it was ~0.3pp
- A 3.0pp margin is approximately 5x the observed inter-run SD -- a generous threshold that accommodates the engine change
- Even a 3pp fitness loss would leave performance well above the GEPA benchmark (52.33% test) and the baseline grand mean (51.65%)
- Consistent with v1 design, enabling methodological comparability

**Secondary hypothesis (wall-time efficiency)**:

**H_wt**: At equal wall time (T hours), the steady-state engine with LPT scheduling produces validation fitness within delta = 3.0pp of the generational engine. V1 showed steady-state epochs are ~3x slower than generational generations; LPT scheduling is expected to narrow but not necessarily eliminate this gap.

---

## 3. Independent Variable(s)

| Variable | Control value | Treatment value |
|----------|---------------|-----------------|
| Evolution engine | `evolution=default` (generational, FIFO) | `evolution=steady_state` + `scheduling=lpt` |

**Two IVs bundled as a single treatment**: The steady-state engine and LPT scheduling are introduced together. This is deliberate -- LPT scheduling is specifically designed to address the tail-latency problem observed in v1's steady-state runs. Separating them would require a 2x2 factorial (4 cells) which exceeds our compute budget. If the treatment is non-inferior, a follow-up experiment can isolate the LPT contribution.

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Best val fitness at gen/epoch 25 (soft fractional) | Best `valid_frontier_fitness` when `engine:total_generations` reaches 25 | **YES -- primary** |
| Val fitness at equal wall time T | Best `valid_frontier_fitness` at wall time T = min(control_completion, treatment_completion) | **YES -- secondary** |
| Throughput (mutants/hour) | Total mutants produced / wall clock hours | Secondary |
| Time per generation/epoch | Wall clock time per generation (control) or epoch (treatment) | Secondary |
| Test coverage (discrete) | 5-repeat eval on 300-sample held-out test set; best-by-val program | Exploratory |
| Time to 70% val fitness | Wall clock hours to first hit 70% soft val fitness | Exploratory |

**Primary metric**: Best validation fitness (soft fractional retrieval coverage) when `engine:total_generations` reaches 25 (epoch 25 for steady-state, generation 25 for generational).

**Secondary metric**: Best validation fitness at matched wall time. This addresses the v1 finding that steady-state epochs take ~3x longer than generational generations, making generation-count comparisons potentially misleading. The wall-time comparison asks: given the same compute budget, which engine achieves higher fitness?

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| `problem.name` | `chains/hover/full` | Dynamic topology — best-performing variant, matches v1 |
| `pipeline` | `standard` | validate.py returns dict |
| `num_parents` | 1 | Match prior experiments |
| `max_elites_per_generation` | 8 | Default |
| `max_mutations_per_generation` | 8 | Default; also epoch size for steady-state |
| `max_generations` | 25 | Match prior experiments |
| `llm_base_url` | `http://10.232.30.185:4000/v1` | LiteLLM proxy handles load balancing for mutation LLM |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` | Standard vLLM model name via proxy |
| `significant_change` | 0.003 | Match prior experiments |
| `stage_timeout` | 3000 | Match prior experiments |
| `dag_timeout` | 7200 | Match prior experiments |
| Chain server | LiteLLM proxy at 10.232.30.185:4000 | All runs share the proxy; 8-node Qwen3-8B cluster behind it |
| Mutation servers | 4x Qwen3-235B via LiteLLM proxy | Load-balanced by proxy across all runs |
| `max_in_flight` | 5 | Steady-state config default (reduced from v1's 8); 5 provides tighter backpressure on shared infrastructure where all runs contend for the same proxy. Lower in-flight count reduces proxy queue depth. |
| Seed initialization | Cold start (no `program_loader.problem_dir`) | Identical starting point |
| Val set | 300 samples from train split | Default |
| Test set | 300 samples held out | Default |

---

## 6. Run Design Table

| Run | Label | Condition | `redis.db` | `evolution` | `scheduling` | Extra overrides |
|-----|-------|-----------|------------|-------------|--------------|-----------------|
| V1 | ctrl-1 | Control (generational + FIFO) | 3 | default | fifo (default) | `[]` |
| V2 | ctrl-2 | Control (generational + FIFO) | 4 | default | fifo (default) | `[]` |
| V3 | treat-1 | Treatment (steady-state + LPT) | 5 | steady_state | lpt | `[evolution=steady_state, scheduling=lpt]` |
| V4 | treat-2 | Treatment (steady-state + LPT) | 6 | steady_state | lpt | `[evolution=steady_state, scheduling=lpt]` |

**N = 2 per cell, 4 runs total.**

All runs share:
- Chain: LiteLLM proxy at `http://10.232.30.185:4000/v1` (model: `Qwen/Qwen3-8B`)
- Mutation: LiteLLM proxy (4x Qwen3-235B servers load-balanced by the proxy)
- `problem.name=chains/hover/full`, `pipeline=standard`

**Run naming convention**: V-prefix for "V2" (steady-state validation, version 2).

**Redis DB assignments**: DBs 3-6. Avoids DB 0-2 (system). DBs 7-8 are reserved for potential wave-2 extension.

**All 4 runs launch simultaneously** -- no wave sequencing needed. The LiteLLM proxy handles load balancing across all chain and mutation servers, so there is no per-run server assignment. This eliminates the host-treatment confound present in prior experiments.

---

## 7. Sample Size Justification

N=2 per cell is the minimum for a t-test. This is a pragmatic choice driven by:

- This is an engineering validation experiment, not a discovery experiment
- The primary question is non-inferiority (does the new engine NOT break things), which requires less power than superiority testing
- We have strong priors from v1 (steady-state fitness was competitive at 80-83% val)
- Compute budget: 4 simultaneous runs is feasible; more would contend for shared chain/mutation resources

**MDE analysis (t-distribution, df=2)**:
- Conservative SD estimate: 1.5pp (upper bound from prior experiments)
- SE = SD * sqrt(1/n1 + 1/n2) = 1.5 * sqrt(1/2 + 1/2) = 1.5pp
- t(0.05, df=2) = 2.92
- 90% CI half-width = 2.92 * 1.5 = 4.38pp -- exceeds delta = 3.0pp

At N=2 with SD=1.5pp, the non-inferiority test is likely inconclusive. However:
- If inter-run SD is closer to the 0.63pp observed in the HoVer baseline, CI half-width = 2.92 * 0.63 = 1.84pp, and the test is well-powered
- If both conditions converge to similar fitness (as expected for a non-inferiority test), the observed SD will be small

**Pre-committed extension protocol**:
- Wave 1: N=2 per cell (4 runs). If conclusive, stop.
- Wave 2: Extend to N=3 per cell (2 additional runs on DBs 7-8) if Wave 1 is inconclusive.
- Extension threshold: 90% CI of (control - treatment) includes both 0 and delta = 3.0pp.

---

## 8. Statistical Test

**Test**: One-sided Welch's t-test for non-inferiority
**Null**: mu_control - mu_treatment > 3.0pp
**Significance threshold**: alpha = 0.05
**How computed**: `scipy.stats.ttest_ind(control, treatment)`, then check if upper bound of (control - treatment) 90% CI < 3.0pp

**Decision rule (primary -- at gen/epoch 25)**:
- If 90% CI upper bound of (control - treatment) < 3.0pp --> **Non-inferior** (PASS)
- If 90% CI lower bound of (control - treatment) > 0 --> **Steady-state is actually worse** (investigate)
- If CI includes both 0 and 3.0pp --> **Inconclusive** (extend to N=3)

**Decision rule (secondary -- at matched wall time)**:
- Same non-inferiority framework applied to fitness values at equal wall time T
- T = min(mean_control_completion_time, mean_treatment_completion_time)
- If treatment completes faster but with non-inferior fitness --> evidence for throughput advantage

**Wall-time comparison protocol**:
1. Record wall clock start time and completion time for each run
2. Extract val fitness trajectory with timestamps (from Redis `metrics:history` with logged timestamps)
3. At wall time T, use last-observation-carried-forward (LOCF) to determine fitness (i.e., best fitness achieved at or before time T)
4. Apply non-inferiority test to fitness-at-T values

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Shared chain server contention** | Medium -- all 4 runs share the same LiteLLM proxy and 8-node chain cluster. Higher contention than v1 which had dedicated servers per run. | ACKNOWLEDGED. This is a design choice that reflects real deployment. Both conditions experience identical contention. Monitor proxy queue depth during the run. |
| 2 | **LPT + steady-state bundled as single treatment** | Low -- cannot distinguish LPT contribution from steady-state contribution | ACCEPTED. This is deliberate (see Section 3). If treatment is non-inferior, a follow-up can isolate LPT. |
| 3 | **Archive staleness in steady-state** | Mechanistic feature -- mutants use stale parent selection between epochs | Not a confound; inherent to steady-state design. Epoch refresh every 8 programs bounds staleness. |
| 4 | **Mutation budget asymmetry** | Medium -- ghost sweeps in steady-state free slots without counting toward epoch trigger, allowing >8 mutation attempts per epoch | Pre-committed diagnostic: report `total_mutations_attempted` and `total_ghosts_swept` per run at closeout. |
| 5 | **Infrastructure difference from v1** | High -- v2 results are not directly comparable to v1 | ACKNOWLEDGED explicitly in Section 1. V2 is a standalone experiment; v1 provides qualitative context only. |
| 6 | **LiteLLM proxy load imbalance** | Low -- the proxy distributes mutation calls across 4 servers, but transient imbalance is possible | Both conditions use the same proxy; imbalance affects both equally. |
| 7 | **Epoch != generation in wall time** | High -- v1 showed ~3x difference. LPT scheduling should reduce but may not eliminate. | MITIGATED by secondary wall-time comparison metric. Primary metric (gen 25) is supplemented by fitness-at-equal-wall-time. |

---

## 10. Stop Criteria

**Smoke test**: Before full launch, run 1 control + 1 treatment to gen/epoch 3 on a scratch DB. Verify: (a) treatment shows `[SteadyState]` logs, (b) LPT scheduling is active in Hydra cfg dump, (c) LiteLLM proxy handles concurrent requests without errors. Only then launch all 4 runs.

**Early termination**: None -- all runs proceed to 25 generations/epochs.

**Run invalidation**: A run is invalidated if:
- PID dies before gen/epoch 5 (infrastructure failure)
- Redis DB is corrupted or flushed accidentally
- LiteLLM proxy is down for >4 consecutive hours during the run
- Treatment verification fails (steady-state engine or LPT scheduling not actually active)
- Gen-0 val fitness is a sentinel value (-1000.0), indicating execution error

**Extension trigger**: If N=2 is inconclusive (90% CI of control - treatment spans both 0 and 3.0pp), extend to N=3 per cell using reserved DBs 7-8.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Chain GPU hours | Shared 8-node cluster, ~16-20h wall time |
| Mutation GPU hours | Shared via balanced LLM (4x Qwen3-235B, existing servers) |
| Wall time per run | ~16-20h (control); ~20-30h (treatment, based on v1 epoch speed) |
| Total wall time | ~20-30h (all 4 runs in parallel) |
| Redis DBs used | 4 (DBs 3, 4, 5, 6); 2 reserved for extension (DBs 7, 8) |
| Test eval time | ~5 min/repeat * 5 repeats * 4 runs = ~100 min total |

**Note on treatment wall time**: V1 showed steady-state epochs taking ~57 min vs. ~5-7 min per generational generation. With LPT scheduling and shared infrastructure, we expect improvement but conservatively budget 1.5-2x the control wall time for treatment runs. If treatment runs are still dramatically slower, this is itself an important finding.

---

## 12. Treatment Verification

**What observable evidence proves the treatment is actually applied?**

1. **Log pattern (treatment only)**: Treatment runs (V3, V4) must show `[SteadyState]` log prefix; control runs (V1, V2) must NOT show this pattern.

2. **Hydra cfg dump -- engine**: Treatment runs must show `_target_: gigaevo.evolution.engine.SteadyStateEvolutionEngine`; control runs must show `_target_: gigaevo.evolution.engine.EvolutionEngine`.

3. **Hydra cfg dump -- scheduling**: Treatment runs must show `_target_: gigaevo.evolution.scheduling.LPTPrioritizer`; control runs must NOT show this target.

4. **Runtime behavior**: Treatment runs should produce mutants continuously (no "waiting for idle" pattern between mutations); control runs show clear generational barriers in logs.

5. **Redis run_state**: Both conditions store `engine:total_generations` -- comparable epoch/generation counter.

**`extra_overrides` per condition**:
- Control (V1, V2): `[]` (no extra overrides — defaults are generational + FIFO)
- Treatment (V3, V4): `[evolution=steady_state, scheduling=lpt]`

**Automated treatment checks** (for `experiment.yaml` `treatment_checks`):

| Check | Type | Target | Expected (Control) | Expected (Treatment) |
|-------|------|--------|--------------------|--------------------|
| `evolution_engine._target_` in Hydra cfg | `config_override` | All runs | `gigaevo.evolution.engine.EvolutionEngine` | `gigaevo.evolution.engine.SteadyStateEvolutionEngine` |
| `prioritizer._target_` in Hydra cfg | `config_override` | Treatment runs | ABSENT | `gigaevo.evolution.scheduling.LPTPrioritizer` |
| `[SteadyState]` in run log | `log_pattern_present` | Treatment runs | ABSENT | PRESENT |
| `[SteadyState]` NOT in control log | `log_pattern_absent` | Control runs | ABSENT | N/A |

---

## 13. Open Questions / Risks

### Priority risks

**Risk 1 -- LPT scheduling degrades fitness (LOW).**
LPT scheduling changes evaluation order (longest-predicted programs first) but not which programs are evaluated. The only mechanism for fitness degradation is if evaluation order interacts with steady-state ingestion timing (earlier-ingested programs influence later parent selection within an epoch). This is a second-order effect bounded by the epoch refresh mechanism.

**Mitigation**: Compare treatment val fitness trajectory to control. If treatment shows a systematic downward trajectory relative to control at equal generations, LPT ordering may be detrimental.

**Risk 2 -- Shared infrastructure introduces noise (MEDIUM).**
All 4 runs share the LiteLLM proxy. If the proxy becomes a bottleneck, all runs slow down together, but the steady-state engine (which issues more frequent, smaller requests) may be disproportionately affected compared to the generational engine (which issues batch requests between generations).

**Mitigation**: Monitor proxy latency metrics during the run. If median response latency exceeds 2x the no-contention baseline, note as a confound. Both conditions experience the same proxy -- noise is symmetric in expectation.

**Risk 3 -- Treatment wall time exceeds budget (MEDIUM).**
V1 showed steady-state epochs at ~57 min each. At 25 epochs, that would be ~24h. With LPT scheduling, we hope for improvement, but if epochs still take ~30-40 min, the run could take 12-17h. This is within budget but worth monitoring.

**Mitigation**: Checkpoint at epoch 5 (~2-4h). If epoch time is not meaningfully better than v1's 57 min, the LPT scheduling benefit is marginal for this task. Record but continue -- the non-inferiority question is still answered at gen 25.

**Risk 4 -- N=2 is inconclusive (HIGH).**
The MDE analysis shows that at conservative SD=1.5pp, the 90% CI will likely span both 0 and 3.0pp, rendering the non-inferiority test inconclusive.

**Mitigation**: Pre-committed extension to N=3 (Wave 2, DBs 7-8). If Wave 1 inter-run SD is small (<0.8pp), N=2 may suffice. The extension protocol is defined in Section 7.

### Relationship to v1

This experiment does NOT supersede v1. V1 tests steady-state without LPT on old infrastructure; v2 tests steady-state with LPT on new infrastructure. If both show non-inferiority, the combined evidence is stronger. If they disagree, the infrastructure difference is the primary suspect.

### What we learn regardless of outcome

| Result | Interpretation | Next step |
|--------|----------------|-----------|
| Non-inferior at gen 25 AND at equal wall time | Steady-state + LPT is a viable replacement for generational engine | Adopt as default engine for future experiments |
| Non-inferior at gen 25 BUT inferior at equal wall time | Steady-state converges per-epoch but epochs are slower; LPT did not fully close the gap | Investigate epoch overhead; consider max_in_flight tuning |
| Inferior at gen 25 BUT non-inferior at equal wall time | Steady-state is slower per epoch but competitive per hour | Increase max_generations for steady-state in future experiments |
| Inferior at both | Steady-state + LPT hurts fitness on HoVer | Investigate mechanism; may be task-specific (HoVer's high invalidity rate wastes steady-state slots) |

---

*Ready for Reviewer-2's scrutiny.*
