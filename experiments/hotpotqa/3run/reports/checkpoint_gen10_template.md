## Checkpoint Report: Generation 10 — {{REPORT_DATE_UTC}}

**Branch**: `exp/hotpotqa-efficiency` | **Git HEAD**: `{{GIT_COMMIT_HASH}}`

---

### Per-Run Status

| | **Run A (Control)** | **Run B (High Budget)** | **Run C (Warm Start)** |
|--|---|---|---|
| **Current generation** | {{RUN_A_GEN}} | {{RUN_B_GEN}} | {{RUN_C_GEN}} |
| **Best val EM** | {{RUN_A_BEST_VAL_EM}}% | {{RUN_B_BEST_VAL_EM}}% | {{RUN_C_BEST_VAL_EM}}% |
| **Improvement over seed** | +{{RUN_A_DELTA}} pp | +{{RUN_B_DELTA}} pp | +{{RUN_C_DELTA}} pp |
| **Archive size** | {{RUN_A_ARCHIVE_SIZE}} | {{RUN_B_ARCHIVE_SIZE}} | {{RUN_C_ARCHIVE_SIZE}} |
| **Fitness curve trend** | {{RUN_A_TREND}} | {{RUN_B_TREND}} | {{RUN_C_TREND}} |

Trend: **Rising** (improvement in last 3 gens), **Flat** (no improvement in last 5 gens), **Stagnant** (8+ gens).

### Pairwise Comparisons

| Comparison | Delta (val EM) | Signal | Interpretation |
|------------|---------------|--------|----------------|
| B vs A (mutation budget) | {{B_MINUS_A}} pp | {{B_A_SIGNAL}} | {{B_A_INTERPRETATION}} |
| C vs A (warm start) | {{C_MINUS_A}} pp | {{C_A_SIGNAL}} | {{C_A_INTERPRETATION}} |

Signal: **Strong** (> 5 pp), **Suggestive** (3–5 pp), **Noise** (< 3 pp).

### Best Program (Run {{BEST_RUN_LABEL}}, {{BEST_VAL_EM}}% val EM)

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

**Next checkpoint**: Generation 20 — estimated {{NEXT_CHECKPOINT_ETA_UTC}} UTC.
