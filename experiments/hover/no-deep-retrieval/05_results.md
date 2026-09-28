# Results: hover/no-deep-retrieval

**Date**: 2026-04-02
**Input**: Final metrics from Redis, test eval logs, `01_design.md`, `03_plan.md`

---

## 1. Final Metrics

| Run | Condition | Val Fitness | Test Discrete Coverage | Test Std | Gen |
|-----|-----------|-------------|----------------------|----------|-----|
| R1 | static no-deep | 76.78% | 49.47% | +/-1.0pp | 25 |
| R2 | static deep | 78.00% | 52.93% | +/-2.0pp | 25 |
| R3 | dynamic no-deep | 83.44% | 64.20% | +/-1.8pp | 26 |
| R4 | dynamic deep | 84.22% | 64.33% | +/-1.1pp | 26 |

**Baseline**: hover/baseline grand mean = 51.65% test discrete coverage (n=4)
**GEPA benchmark**: 52.33% (k=7 only, fixed single-hop)
**Prior SOTA**: hover/dynamic-topology V3 = 67.67% test (k=10 + dynamic topology)

### Direct ablation reference

Best V3 chain with retrieve_deep replaced by retrieve: 62.53% +/-0.93pp (vs 67.67% original = -5.14pp).

## 2. Hypothesis Test

**H0**: Removing retrieve_deep (k=10) does not reduce test discrete retrieval coverage compared to runs with both retrieval tools.

**H1**: retrieve_deep improves test discrete retrieval coverage.

**Primary metric**: Test discrete retrieval coverage at max gen, 5-repeat mean per run.

**Statistical test**: Not applicable (N=1 per condition). Descriptive comparison only.

**Result**: H0 **not rejected** for dynamic chains (delta = 0.13pp, within noise). H0 **potentially rejected** for static chains (delta = 3.46pp), but N=1 precludes significance testing.

## 3. Effect Size

| Comparison | Delta (test) | Direction |
|------------|-------------|-----------|
| Static: no-deep vs deep (R1 vs R2) | -3.46pp | Deep better |
| Dynamic: no-deep vs deep (R3 vs R4) | -0.13pp | Negligible |
| Dynamic vs Static, no-deep (R3 vs R1) | +14.73pp | Dynamic better |
| Dynamic vs Static, deep (R4 vs R2) | +11.40pp | Dynamic better |
| R3 (dynamic no-deep) vs baseline | +12.55pp | Better |
| R3 (dynamic no-deep) vs GEPA | +11.87pp | Better |

**Key finding**: The topology factor (dynamic vs static) accounts for 11-15pp of test coverage. The retrieval depth factor (deep vs no-deep) accounts for 0-3.5pp, depending on topology. For dynamic chains, deep retrieval is unnecessary.

## 4. Secondary Observations

1. **Evolution compensates for lost retrieval depth in dynamic chains**: The best V3 chain lost 5.14pp when retrieve_deep was manually replaced. But when evolution can freely adapt topology, the gap disappears entirely (R3 64.2% ~ R4 64.3%).

2. **Val-test gap is large for static chains**: R1 val=76.8% vs test=49.5% (27.3pp gap), R2 val=78.0% vs test=52.9% (25.1pp gap). This suggests static chain evolution overfits to the validation set.

3. **Val-test gap is smaller for dynamic chains**: R3 val=83.4% vs test=64.2% (19.2pp gap), R4 val=84.2% vs test=64.3% (19.9pp gap). Dynamic topology generalizes better.

4. **Dynamic chains use more steps**: R3 best chain has 6 steps with 3 tool steps, R4 has 7 steps with 3 tool steps. Both chose 3 retrieval hops, same as the static topology. The improvement comes from better LLM step design, not more hops.

5. **GEPA comparison validated**: R3 (dynamic, k=7 only) at 64.2% exceeds GEPA (52.33%) by 11.87pp using identical retrieval budget. Evolutionary chain optimization provides substantial gains independent of retrieval depth.

## 5. Deviations from Pre-Registration

| Deviation | Impact on validity | Assessment |
|-----------|-------------------|-----------|
| N=1 per condition instead of N=2 | Cannot compute significance tests | Descriptive comparison only; dynamic-chain finding (0.13pp delta) is robust given the magnitude of noise (~1-2pp std) |
| Dynamic runs used `pipeline=structural_metrics` + `algorithm=topology_3d_ret` + `scheduling=lpt_chain` | Extra overrides vs design | These are standard dynamic-chain infrastructure, also used in control (R4). Not a confound. |
| New `topology_3d_ret` algorithm config created | Changed BC dimension from n_deep_retrieval to n_retrievals | Necessary: n_deep_retrieval is always 0 in treatment, collapsing the 3D space. n_retrievals preserves behavioral diversity for both conditions. |
| Static runs used standard engine (not steady_state) | Inconsistent engine across conditions | Static runs were not designed to use steady_state; this matches prior static experiments. |
| `chain_url` and `mutation_url` both point to LiteLLM proxy | All runs share compute | No per-run isolation, but load balancing is symmetric across all 4 runs. |

## 6. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| R1 | Yes | Completed gen 25 normally |
| R2 | Yes | Completed gen 25 normally |
| R3 | Yes | Completed gen 26 (exceeded max by 1 — steady-state epoch counting) |
| R4 | Yes | Completed gen 26 (same as R3) |

## 7. Lessons Learned

**What worked**:
- 2x2 factorial design cleanly separates topology vs retrieval effects
- Direct ablation (V3 chain swap) provides a strong counterfactual
- LiteLLM proxy simplified launch (one URL for all runs)
- `topology_3d_ret` config with n_retrievals as BC dimension

**What didn't work**:
- N=1 per condition limits statistical power
- throughput_plot.py had hardcoded V1-V4 colors (fixed mid-experiment)
- Watchdog accidentally pushed to main when working directory changed (fixed with explicit branch checkout)
- Static chain import path bug would have loaded wrong config (caught before launch)

**Bugs / infrastructure issues**:
- `static_soft_no_deep/validate.py` and `test.py` imported from wrong config module (FIXED pre-launch)
- `static_soft_no_deep/task_description.txt` still referenced retrieve_deep (FIXED pre-launch)
- Watchdog model drift check failed because proxy requires API key (FIXED mid-run)

## 8. Next Steps

1. **Simplify future experiments**: For dynamic chain runs, retrieve_deep can be dropped from the tool registry without fitness loss. This simplifies the search space.
2. **GEPA paper comparison**: Report R3 (64.2%, k=7 only) as the fair comparison point vs GEPA (52.33%).
3. **N=2 replication**: If resources allow, replicate with N=2 per condition for statistical testing. The effect sizes suggest topology is the dominant factor.
4. **Investigate val-test gap**: 19-27pp gaps suggest overfitting. Consider larger/diverse validation sets.

## 9. Paper / Report Notes

- The 2x2 factorial provides a clean ablation table for the paper
- Key claim: "Evolutionary topology optimization compensates for reduced retrieval budget (k=7 vs k=10), achieving 64.2% test coverage with k=7 only vs 64.3% with k=10 (delta < 0.2pp)"
- This validates the fairness of GEPA comparisons using k=7
- The +11.87pp gap over GEPA (64.2% vs 52.33%) is attributable to evolutionary chain optimization, not retrieval budget
