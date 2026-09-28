# Results: hover/7step-dynamic

**Date**: 2026-04-01
**Analyst**: Dr. Elena Voss (ML Research Methodologist)
**Verdict**: **STRONG POSITIVE** (+5.05pp val, +8.33pp test)

---

## 1. Summary

Topology flexibility within a 7-step budget significantly improves retrieval coverage over static prompt-only evolution. The treatment (dynamic topology + 3D structural MAP-Elites) outperforms the control (frozen topology + 1D fitness binning) by **+5.05pp** on validation fitness and **+8.33pp** on held-out test coverage.

The primary hypothesis is supported at p=0.061 (one-sided Welch's t-test, alpha=0.10). This answers the motivating question: **the dynamic-topology gain is not purely a step-budget effect**. Even when both conditions are limited to 7 steps, topology freedom produces substantially better chains.

---

## 2. Per-Run Results

### Validation Fitness (soft fractional, best at gen 25)

| Run | Condition | Val Fitness | Gen |
|-----|-----------|-------------|-----|
| V1 | Control | 79.8% | 26 |
| V2 | Control | 80.3% | 26 |
| V3 | Treatment | 86.2% | 26 |
| V4 | Treatment | 84.0% | 26 |

| Condition | Mean | SD | N |
|-----------|------|----|---|
| Control | 80.05% | 0.35pp | 2 |
| Treatment | 85.10% | 1.56pp | 2 |
| **Delta** | **+5.05pp** | | |

### Test Coverage (discrete, 5-repeat mean on 300-sample held-out set)

| Run | Condition | Test Mean | Test SD | Per-repeat |
|-----|-----------|-----------|---------|------------|
| V1 | Control | 56.27% | 2.37pp | 56.0, 53.7, 56.7, 60.0, 55.0 |
| V2 | Control | 55.47% | 1.76pp | 54.7, 57.7, 57.0, 54.3, 53.7 |
| V3 | Treatment | 67.67% | 0.78pp | 67.7, 68.0, 66.3, 68.0, 68.3 |
| V4 | Treatment | 60.73% | 1.44pp | 60.0, 62.7, 60.3, 61.7, 59.0 |

| Condition | Mean | SD | N |
|-----------|------|----|---|
| Control | 55.87% | 0.57pp | 2 |
| Treatment | 64.20% | 4.91pp | 2 |
| **Delta** | **+8.33pp** | | |

---

## 3. Hypothesis Test

**H0**: mu_treatment - mu_control <= 0 (topology flexibility within a 7-step budget does not improve best val fitness)
**H1**: mu_treatment - mu_control > 0

### Primary: val fitness superiority

- **Test**: One-sided Welch's t-test
- **t** = 4.477, **p** = 0.061 (one-sided)
- **Decision**: p < 0.10 and delta > 0 => **REJECT H0**
- **Cohen's d** = 4.48 (very large effect)
- **Verdict**: **STRONG POSITIVE** (delta >= +3.0pp per pre-registered thresholds)

### Test coverage

- **t** = 2.385, **p** = 0.124 (one-sided)
- **Cohen's d** = 2.38 (very large effect)
- Not significant at alpha=0.10, driven by V3/V4 variance (67.7% vs 60.7%). The effect is directionally consistent with val fitness but high inter-run variance on treatment reduces power.

### Secondary: architecture diversity (H_div, descriptive only)

| Condition | Occupied Cells (gen 25) | Detail |
|-----------|------------------------|--------|
| Control | 33, 34 (mean 33.5) | 1D fitness bins |
| Treatment | 29, 27 (mean 28.0) | 3D structural cells |

Treatment occupies fewer cells than control. However, this comparison is confounded by the different archive indexing (1D fitness vs 3D structural) — acknowledged as Confound #1 in the design. The manipulation check confirms the IV was active.

---

## 4. Manipulation Check (Pre-registered, Section 10)

At gen 5, the fraction of treatment programs whose `(n_steps, n_tool_steps, dag_depth)` triple differed from the seed's `(7, 3, 7)`:

- **V3**: >50% of valid programs had non-seed triples (dominant: `(7, 4, 7)` — 4 tool steps)
- **V4**: >50% had non-seed triples (dominant: `(7, 4, 7)`)

**IV was active**: topology mutations were occurring. The 10% threshold was exceeded.

---

## 5. Architecture Analysis

### Best chains discovered

Top chains across both treatment runs converged on: **4-hop alternating TOOL-LLM with cumulative skip connections**.

**V3 best (86.2% val, 67.7% test):**
```
(claim)-->[1:TD]-->[2:L(1)]-->[3:TD]-->[4:L(1,3)]-->[5:TD]-->[6:L(1,3,5)]-->[7:TD]-->(out)
```

**V4 best (84.0% val, 60.7% test):**
```
(claim)-->[1:TD]-->[2:L(1)]-->[3:TD]-->[4:L(1,2,3)]-->[5:TD]-->[6:L(1,2,3,4,5)]-->[7:TD]-->(out)
```

Key architectural innovations (impossible in the static control):

1. **4 retrieval hops** (vs 3 in static): By eliminating the synthesis LLM step, the chain fits 4 `retrieve_deep` (k=10) hops in 7 steps.
2. **Cumulative skip connections**: Later LLM query-generation steps see all prior retrieval outputs, enabling evidence-aware query refinement.
3. **All retrieve_deep**: Every retrieval step uses k=10 (the static chain uses k=7 for 2 of 3 hops).

The V3 winner's selective pattern `L(1), L(1,3), L(1,3,5)` — feeding only retrieval outputs — outperformed V4's maximum fan-in `L(1,2,3,4,5)` by +2.2pp val and +7.0pp test, suggesting intermediate LLM text dilutes the context.

### What the control cannot express

The static chain has 3 frozen tool steps at positions 1, 4, 7 with fixed dependencies. It cannot:
- Add a 4th retrieval hop
- Switch from `retrieve` (k=7) to `retrieve_deep` (k=10) on frozen steps
- Create skip connections across non-adjacent steps
- Reallocate the step budget (fewer LLM steps, more tool steps)

---

## 6. Comparison to Baselines

| Method | Test Coverage | Delta vs GEPA |
|--------|-------------|---------------|
| GEPA benchmark | 52.33% | -- |
| HoVer baseline (n=4) | 51.65% | -0.68pp |
| This experiment: control mean | 55.87% | +3.54pp |
| This experiment: treatment mean | 64.20% | **+11.87pp** |
| This experiment: V3 best | 67.67% | **+15.34pp** |
| hover/dynamic-topology treatment (10-step) | 60.37% | +8.04pp |

The 7-step treatment **exceeds the 10-step dynamic-topology result** (+3.83pp test), despite having 3 fewer steps available.

---

## 7. Deviations from Pre-Registration

### D1. Treatment runs restarted (MAJOR)

Treatment runs V3/V4 were restarted after ~6 hours due to a bug in `task_description.txt` (Issue #2 in 04_issues_log.md). The task description said "Maximum 10 steps" instead of 7, causing 97% invalidity. After fixing and flushing DBs 5-6, treatment was restarted from gen 0. **No data contamination**: DBs were flushed to 0 keys before restart.

### D2. Different archive indexing between conditions (pre-registered as Confound #1)

Control uses 1D fitness binning (60 bins); treatment uses 3D structural BC (60 cells). Documented in 01_design.md Section 3.

### D3. Redis MISCONF during treatment runs (MINOR)

Redis disk persistence failed at ~hour 15 due to full disk (Issue #3). Fix applied immediately. No data loss.

### D4. Generation-count normalization not needed

All 4 runs completed gen 25 (technically 26 due to off-by-one in steady-state termination). No normalization needed.

---

## 8. Limitations

1. **N=2 per condition**: Primary t-test is marginally significant (p=0.061). Test coverage not significant (p=0.124). N=4 extension warranted.

2. **Two bundled IVs**: Topology mutability AND archive indexing differ. Prior null result for archive-only (map-elites-topology) supports topology as the driver, but interaction cannot be fully ruled out.

3. **Frozen-step removal confound**: Treatment removes frozen annotations, allowing `retrieve` -> `retrieve_deep` changes on tool steps. Part of the gain may come from unfreezing rather than topology rewiring. Post-hoc: best V3 chain has non-seed topology (4 tool + 3 LLM vs seed's 3 tool + 4 LLM), confirming topology change occurred.

4. **V3/V4 asymmetry**: V3 (67.7% test) substantially outperforms V4 (60.7% test). This 7pp gap is larger than control inter-run spread (0.8pp), suggesting stochastic search found a strong local optimum in V3 that V4 missed.

---

## 9. Run Validity

| Run | Valid for analysis? | Notes |
|-----|--------------------|--------------------|
| V1 | Yes | Completed gen 26 |
| V2 | Yes | Completed gen 26 |
| V3 | Yes | Restarted (D1), completed gen 26 |
| V4 | Yes | Restarted (D1), completed gen 26 |

---

## 10. Next Steps

1. **N=4 extension**: Per pre-registered protocol (Section 8), the directional signal warrants 4 additional runs (DBs 7-10) with formal test at alpha=0.10 on all 8 runs.

2. **Freeze the 4-hop skip-connection architecture**: Test the V3 winner as a new static baseline. If it outperforms the current 3-hop static chain when frozen, the gain is from the architecture itself.

3. **Selective vs maximum fan-in**: Investigate why `L(1,3,5)` beats `L(1,2,3,4,5)` — context dilution from intermediate LLM outputs.

---

## 11. Lessons Learned

**What worked**:
- Steady-state engine produced strong chains within 7-step budget
- 4-hop architecture with cumulative skip connections is a novel discovery
- Treatment found architectures that exceed 10-step chains despite tighter budget

**What didn't work**:
- task_description.txt copy-paste error caused 6h wasted compute (Issue #2)
- Redis disk full caused transient write failures (Issue #3)

**Bugs / infrastructure issues**:
- See 04_issues_log.md for full details
- Systemic fix needed: preflight check should verify task_description step limits match config

---

## 12. Raw Data

### Archives

GitHub Release: `exp/hover/7step-dynamic`
- V1_archive.tar.gz (DB 3, control)
- V2_archive.tar.gz (DB 4, control)
- V3_archive.tar.gz (DB 5, treatment)
- V4_archive.tar.gz (DB 6, treatment)
