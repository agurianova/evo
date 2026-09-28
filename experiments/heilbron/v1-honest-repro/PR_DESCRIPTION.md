## Experiment: heilbron/v1-honest-repro

**Status**: 🟢 Complete
**Branch**: `exp/heilbron/v1-honest-repro`
**Pre-registration commit**: `25470e37`
**Related issue**: N/A

---

### Hypothesis

**H₀**: With v1's fitness-landscape semantics restored verbatim (binary G resistance + linear D scoring) and the post-v1 SBF-LineageStage filter disabled, current main (`25470e37`) reaches `actual_fitness ≥ 0.0364` (within 0.0001 of v1 SOTA `0.03648`) in **at least one** of the 4 G runs.
**H₁**: Even with the v1 landscape restored, current main produces a measurable downward shift in the G `actual_fitness` distribution — the 17-decision interview missed a load-bearing drift element.
**Primary metric**: best-ever `actual_fitness` over the 4 G runs (A1_G, A2_G, C1_G, C2_G)
**Decision threshold**: best G ≥ 0.0364 in ≥1 run → H₀ supported; all G < 0.03574 → H₁ confirmed

---

### Design

| Run | Label | Arm | DB | `pipeline` | Aggregator |
|-----|-------|-----|----|-----------:|-----------:|
| pop_a | A1_G | composition | 1 | heilbron_v1_honest | heilbron_constructor |
| pop_b | A1_D | composition | 2 | heilbron_v1_honest | heilbron_improver |
| pop_a | A2_G | composition | 3 | heilbron_v1_honest | heilbron_constructor |
| pop_b | A2_D | composition | 4 | heilbron_v1_honest | heilbron_improver |
| pop_a | C1_G | gradient_in_prompt | 5 | heilbron_v1_honest | heilbron_constructor |
| pop_b | C1_D | gradient_in_prompt | 6 | heilbron_v1_honest | heilbron_improver |
| pop_a | C2_G | gradient_in_prompt | 7 | heilbron_v1_honest | heilbron_constructor |
| pop_b | C2_D | gradient_in_prompt | 8 | heilbron_v1_honest | heilbron_improver |

`max_generations`: 200 (early-terminated) | `max_mutations_per_generation`: 8 | `num_parents`: 1
`n_opponents`: 1 | `source_prompt_k`: 1 | `inner_iterations`: 1
`pipeline_builder.archive_reeval`: false | `pipeline_builder.lineage_filter`: null | `pipeline_builder.dg_tracker`: null (D-side)

**Docs**: [01_design.md](experiments/heilbron/v1-honest-repro/01_design.md) · [02_review.md](experiments/heilbron/v1-honest-repro/02_review.md) · [03_plan.md](experiments/heilbron/v1-honest-repro/03_plan.md)
**Archives**: [GitHub Release exp/heilbron/v1-honest-repro](https://github.com/KhrulkovV/gigaevo-core-internal/releases/tag/exp/heilbron/v1-honest-repro) (8 per-run tarballs)

---

### Final Result

**Verdict**: SUGGESTIVE (lean H₁)
**Effect (val)**: G-mean **0.03398 [0.03282, 0.03515] 95% CI** vs. v1 baseline mean **0.03574** (Δ ≈ -0.18pp, baseline mean outside upper CI bound)

| Run | Arm | Best `actual_fitness` | Final gen | Trajectory at termination |
|-----|------|----------------------:|----------:|---------------------------|
| A1_G | composition | 0.03368 | 50 | still ascending |
| A2_G | composition | 0.03301 | 52 | still ascending |
| C1_G | gradient_in_prompt | 0.03471 | 56 | plateaued (no improvement gen 28→56) |
| C2_G | gradient_in_prompt | 0.03452 | 58 | plateaued (no improvement gen 17→58) |
| A1_D | composition | **0.03547** | 71 | climbing — frontier across all 8 runs |
| A2_D | composition | 0.03301 | 90 | climbing |
| C1_D | gradient_in_prompt | 0.03499 | 91 | climbing |
| C2_D | gradient_in_prompt | 0.03467 | 85 | climbing |

**Decision-rule application**: 0/4 G runs ≥ 0.0364, 0/4 ≥ 0.03574 → per design Section 4, H₁ confirmed. **But** early termination at G gen ~54 / D gen ~84 (vs. pre-registered max=200) prevents a firm NEGATIVE call: A-arm G runs were still climbing at termination, and D-side runs had crossed 0.0349 with steep slopes.

**Implication**: Library drift between commit `562a1210` (v1) and `25470e37` (current main) — 300+ commits — is load-bearing. The 17-decision interview pinned every parameter that could be pinned; the gap is in the irreducible drift (ConfigurableAggregator under K=1, evaluate.py tuple ABI, and unrelated engine churn). The binary/linear landscape itself is not the issue.

**Deviations**: 5 documented in `05_results.md` § Deviations from Pre-Registration. Most material: early termination, and the launch-time fix `pipeline_builder.dg_tracker=null` for the D-side (more faithful to v1's no-tracker era; not a hypothesis-relevant confound).

**Full analysis**: [05_results.md](experiments/heilbron/v1-honest-repro/05_results.md)
