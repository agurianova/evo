## Checkpoint Report: Generation {{CHECKPOINT_GEN}} — {{REPORT_DATE_UTC}}

**Branch**: `exp/hotpotqa-efficiency` | **Git HEAD**: `{{GIT_COMMIT_HASH}}`

---

### Per-Run Status

| | **Run A (Control)** | **Run B (High Budget)** | **Run C (Warm Start)** |
|--|---|---|---|
| **Current generation** | {{RUN_A_GEN}} | {{RUN_B_GEN}} | {{RUN_C_GEN}} |
| **Best val EM** | {{RUN_A_BEST_VAL_EM}}% | {{RUN_B_BEST_VAL_EM}}% | {{RUN_C_BEST_VAL_EM}}% |
| **Best test EM** | {{RUN_A_BEST_TEST_EM}}% | {{RUN_B_BEST_TEST_EM}}% | {{RUN_C_BEST_TEST_EM}}% |
| **Val–test gap** | {{RUN_A_GAP}} pp | {{RUN_B_GAP}} pp | {{RUN_C_GAP}} pp |
| **Improvement over seed** | +{{RUN_A_DELTA}} pp | +{{RUN_B_DELTA}} pp | +{{RUN_C_DELTA}} pp |
| **Archive size** | {{RUN_A_ARCHIVE_SIZE}} | {{RUN_B_ARCHIVE_SIZE}} | {{RUN_C_ARCHIVE_SIZE}} |
| **Fitness curve trend** | {{RUN_A_TREND}} | {{RUN_B_TREND}} | {{RUN_C_TREND}} |

### Cumulative Progress

| Checkpoint | Run A Val EM | Run A Test EM | Run B Val EM | Run B Test EM | Run C Val EM | Run C Test EM |
|------------|-------------|---------------|-------------|---------------|-------------|---------------|
| Gen 0 (seed) | {{A_G0_VAL}}% | — | {{B_G0_VAL}}% | — | {{C_G0_VAL}}% | — |
| Gen 10 | {{A_G10_VAL}}% | — | {{B_G10_VAL}}% | — | {{C_G10_VAL}}% | — |
{{ADDITIONAL_CHECKPOINT_ROWS}}

### Comparison to Published Benchmarks

| Method | Test EM | Delta vs Best Run |
|--------|---------|-------------------|
| GEPA (target) | 62.3% | {{DELTA_VS_GEPA}} pp |
| MIPROv2 | 55.3% | {{DELTA_VS_MIPRO}} pp |
| Baseline | 42.3% | — |
| **Best run ({{BEST_RUN_LABEL}})** | **{{BEST_TEST_EM}}%** | — |

### Pairwise Comparisons (Test EM)

| Comparison | Delta | Signal | Interpretation |
|------------|-------|--------|----------------|
| B vs A (mutation budget) | {{B_MINUS_A_TEST}} pp | {{B_A_SIGNAL}} | {{B_A_INTERPRETATION}} |
| C vs A (warm start) | {{C_MINUS_A_TEST}} pp | {{C_A_SIGNAL}} | {{C_A_INTERPRETATION}} |

### Overfitting Check

| Run | Val EM | Test EM | Gap | Status |
|-----|--------|---------|-----|--------|
| A | {{RUN_A_BEST_VAL_EM}}% | {{RUN_A_BEST_TEST_EM}}% | {{RUN_A_GAP}} pp | {{RUN_A_OVERFIT_STATUS}} |
| B | {{RUN_B_BEST_VAL_EM}}% | {{RUN_B_BEST_TEST_EM}}% | {{RUN_B_GAP}} pp | {{RUN_B_OVERFIT_STATUS}} |
| C | {{RUN_C_BEST_VAL_EM}}% | {{RUN_C_BEST_TEST_EM}}% | {{RUN_C_GAP}} pp | {{RUN_C_OVERFIT_STATUS}} |

Status: **Clean** (gap < 2 pp), **Acceptable** (2–4 pp), **Concerning** (> 4 pp).

### Best Program (Run {{BEST_RUN_LABEL}}, {{BEST_TEST_EM}}% test EM)

<details>
<summary>Program snippet</summary>

```python
{{BEST_PROGRAM_SNIPPET}}
```
</details>

### Decision per Run

| Run | Decision | Rationale |
|-----|----------|-----------|
| A | {{RUN_A_DECISION}} | {{RUN_A_RATIONALE}} |
| B | {{RUN_B_DECISION}} | {{RUN_B_RATIONALE}} |
| C | {{RUN_C_DECISION}} | {{RUN_C_RATIONALE}} |

### Overall Assessment

{{OVERALL_ASSESSMENT}}

{{NEXT_STEPS}}
