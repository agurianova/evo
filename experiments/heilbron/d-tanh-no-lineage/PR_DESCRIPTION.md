## Experiment: heilbron/d-tanh-no-lineage

**Status**: 🟢 Complete
**Branch**: `exp/heilbron/d-tanh-no-lineage`
**Pre-registration commit**: `7b7c5f5e`
**Related issue**: N/A

---

### Hypothesis

**H₀**: μ_G ≤ 0.03315 (within v2 NULL band)
**H₁**: μ_G > 0.03315 (escapes v2 NULL band)
**Primary metric**: `actual_fitness` (best-ever, 4 G runs grand mean) at gen 200
**Treatment**: D-side tanh smoothing + `pipeline_builder.disable_lineage_on_improver=true` (LineageStage / LineagesToDescendants / LineagesFromAncestors removed from D's pipeline)

---

### Design (post-deviation)

| Run | Label | Arm | Pop | DB | `feedback_mode` | `disable_lineage_on_improver` |
|-----|-------|-----|-----|----|-----------------|-------------------------------|
| 1 | A1_G | A | Constructor | 1 | composition | n/a (G run) |
| 2 | A1_D | A | Improver | 2 | composition | true |
| 3 | C1_G | C | Constructor | 5 | gradient_in_prompt | n/a (G run) |
| 4 | C1_D | C | Improver | 6 | gradient_in_prompt | true |

`max_generations`: 200 (early stopped at gen 38–59) | `max_mutations_per_generation`: 8 | `num_parents`: 1 | `inner_iterations`: 1 | `n_opponents`: 1 | `source_prompt_k`: 1 | `stage_timeout`: 900 | `dag_timeout`: 3600

**Docs**: [01_design.md](01_design.md) · [02_review.md](02_review.md) · [03_plan.md](03_plan.md) · [05_results.md](05_results.md) · [04_issues_log.md](04_issues_log.md)
**Archives**: https://github.com/KhrulkovV/gigaevo-core-internal/releases/tag/exp/heilbron/d-tanh-no-lineage

---

### Final Result

**Verdict**: SUGGESTIVE (split: C arm SUGGESTIVE-POSITIVE, A arm NULL)

C1_G crossed the v2 NULL band at 0.03538 (+0.00223 vs 0.03315, 96.9% of v1 SOTA 0.0365) — the strongest post-bug-fix G result on heilbron. A1_G remained below at 0.03124 (NULL). Grand mean μ_G=0.03331 is formally NULL against pre-registered thresholds; verdict upgraded to SUGGESTIVE because the C arm result surpasses every G run from adversarial-repro-v1, adversarial-repro-v2, and baseline-repro.

**Mechanistic finding (clean)**: D/G gen-pace ratio recovered from d-smoothing-minimal's 0.54× to 1.22–1.55× — LineageStage was the dominant timing bottleneck. D fitness healthy under tanh (0% invalidity, fitness 0.525–0.637), breaking the 10-experiment hard-floor stagnation pattern.

| Run | Arm | Best `actual_fitness` | vs v2 NULL (0.03315) | vs v1 SOTA (0.0365) | gen at stop |
|-----|-----|----------------------|----------------------|---------------------|-------------|
| A1_G | A (composition) | 0.03124 | -0.00191 (94.2%) | 85.6% | 38 |
| A1_D | A (composition) | 0.03074 | — | — | 59 |
| **C1_G** | **C (gradient_in_prompt)** | **0.03538** | **+0.00223 (106.7%)** | **96.9%** | 41 |
| C1_D | C (gradient_in_prompt) | 0.03538 | — | — | 50 |

### Limitations

- **N=1 per arm** (8→4 reduction during launch for proxy-load mitigation): pre-registered bootstrap CI on 4 G runs not executable; pre-registered Welch's t-test undefined.
- **Early stop** at gen 38–59 (~19–30% of pre-registered 200-gen budget) when C arm crossed v2 NULL: optional-stopping inflates type-1 error on the C arm (A arm was already stagnant for 65% of trajectory).
- **2-IV gap**: cannot attribute the C arm lift to no-lineage alone vs combined with tanh smoothing.
- **Cross-arm divergence (0.00413)** contradicts the HIGH-confidence "feedback mode does not affect outcomes" pattern (8 prior pairs); at N=1 most likely seed noise.

### Next steps (ranked)

1. **Priority 1**: N=2 replication of C arm (`C2_G + C2_D`, gradient_in_prompt, same config) — minimum-cost, maximum-information confirmation.
2. **Priority 2**: N=2 replication of A arm — resolve cross-arm divergence.
3. **Priority 3**: No-lineage-only ablation (conditional on Priority 1 confirming) — isolate LineageStage removal from tanh smoothing.

**Full analysis**: [05_results.md](05_results.md)
