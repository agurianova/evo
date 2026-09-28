## Experiment: HoVer Baseline -- Cold-Start Retrieval Coverage

**Status**: 🟡 Running (gen 0/25)
**Branch**: `exp/hover-baseline`
**Pre-registration commit**: `9bcb905`
**Related issue**: #89

---

### Hypothesis

**H0**: GigaEvo cold-start mean test retrieval coverage across n=4 runs <= 52.33% (GEPA benchmark).
**H1**: GigaEvo cold-start mean test retrieval coverage > 52.33%.
**Primary metric**: Test retrieval coverage at gen 25 on 300-sample held-out test set (thinking Qwen3-8B).
**Decision threshold**: POSITIVE if mean >= 55.0% with p < 0.05; STRONG POSITIVE if >= 60.0%.

---

### Design

| Run | Label | Condition | DB | `pipeline` | `prompts` | Seed | Mutation LLM URL |
|-----|-------|-----------|----|-----------|-----------|------|------------------|
| H1 | hover-cold-1 | Cold start | 9 | `standard` | `default` | Cold | `http://10.226.72.211:8777/v1` |
| H2 | hover-cold-2 | Cold start | 10 | `standard` | `default` | Cold | `http://10.226.15.38:8777/v1` |
| H3 | hover-cold-3 | Cold start | 11 | `standard` | `default` | Cold | `http://10.226.185.47:8777/v1` |
| H4 | hover-cold-4 | Cold start | 12 | `standard` | `default` | Cold | `http://10.225.51.251:8777/v1` |

`max_generations`: 25 | `max_mutations_per_generation`: 8 | `num_parents`: 1

**Docs**: [01_design.md](experiments/hover/baseline/01_design.md) · [02_review.md](experiments/hover/baseline/02_review.md) · [03_plan.md](experiments/hover/baseline/03_plan.md)
**Archives**: *(GitHub Release link -- added after Step 8)*

---

### Checkpoint Results

| Gen | Date (UTC) | H1 val cov | H2 val cov | H3 val cov | H4 val cov | Notes |
|-----|-----------|-----------|-----------|-----------|-----------|-------|
| *(filled in as experiment progresses)* | | | | | | |

---

### Final Result

*(pending)*

**Verdict**: POSITIVE / SUGGESTIVE / NULL / NEGATIVE
**Mean test coverage**: X.XX% vs GEPA 52.33%

| Run | Label | Best val coverage | Test coverage (final) | Valid? |
|-----|-------|------------------|----------------------|--------|
| H1 | hover-cold-1 | | | |
| H2 | hover-cold-2 | | | |
| H3 | hover-cold-3 | | | |
| H4 | hover-cold-4 | | | |

**Full analysis**: [05_results.md](experiments/hover/baseline/05_results.md)
