## Experiment: heilbron/asymmetric-iterations

**Status**: Pre-registered
**Branch**: `exp/heilbron/asymmetric-iterations`
**Pre-registration commit**: `8ce7ab3f`
**Related issue**: N/A

---

### Hypothesis

**H0**: Asymmetric iteration ratio (K=5) does not change Constructor actual_fitness or Improver acceptance rate.
**H1**: K=5 (40 Improver mutations/gen vs 8) breaks Improver stagnation and/or improves Constructor actual_fitness.
**Primary metric**: Constructor actual_fitness at gen 50
**Decision threshold**: delta >= 0.002 for POSITIVE; Improver acceptance rate > 5% for STAGNATION BROKEN

---

### Design

| Arm | Pairs | Constructor mut/gen | Improver mut/gen | Condition |
|-----|-------|--------------------:|------------------:|-----------|
| Control (K=1) | 3 | 8 | 8 | Standard 1:1 ratio |
| Treatment (K=5) | 3 | 8 | **40** | WGAN-GP analog |

`max_generations`: 50 | Engine: Generational | Pipeline: adversarial_coevo | LLM: Qwen3-235B

**Mechanism**: With `MainRunSyncHook` enforcing generation lockstep, the Constructor blocks while the K=5 Improver churns through 40 mutations -- exactly the WGAN-GP pattern where G is frozen while D trains K steps.

**Docs**: [01_design.md](01_design.md) | [02_review.md](02_review.md) | [03_plan.md](03_plan.md)
**Archives**: *(GitHub Release link -- added after archiving)*

---

### Checkpoint Results

| Gen | Date (UTC) | K=1 mean actual_fitness | K=5 mean actual_fitness | Notes |
|-----|-----------|------------------------|------------------------|-------|
| *(filled during experiment)* | | | | |

---

### Final Result

*(pending)*

**Verdict**: POSITIVE / SUGGESTIVE / NULL / NEGATIVE
**delta**: TBD

| Arm | Condition | Mean Constructor actual_fitness | Mean Improver acceptance rate | Valid? |
|-----|-----------|-------------------------------|------------------------------|--------|
| K=1 | Control | | | |
| K=5 | Treatment | | | |

**Full analysis**: [05_results.md](05_results.md)
