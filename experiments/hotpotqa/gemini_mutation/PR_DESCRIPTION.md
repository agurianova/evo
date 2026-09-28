## Experiment: gemini_mutation

**Status**: 🟢 Complete
**Branch**: `exp/hotpotqa-gemini-mutation`
**Pre-registration commit**: `2ea4226`
**Related issue**: N/A

---

### Hypothesis

**H₀**: Mean test EM across n=2 Gemini-mutation runs does not improve over cold_start reference (59.58%)
**H₁**: Mean test EM ≥ 61.58% (+2pp), suggesting frontier mutation LLM produces better-evolved programs
**Primary metric**: Test EM at gen 25, best-by-val-EM program, 300-sample test set (thinking Qwen3-8B)
**Decision threshold**: POSITIVE ≥ 61.58%, STRONG ≥ 63.58%

---

### Design

| Run | Label | Condition | DB | `pipeline` | `prompts` | Seed |
|-----|-------|-----------|----|-----------:|----------:|------|
| V1 | gemini-1 | Gemini-3.1-Pro + BM25 + F1 + 600 | 3 | hotpotqa_asi | default+NLP | warm (ddce37b4) |
| V2 | gemini-2 | Gemini-3.1-Pro + BM25 + F1 + 600 | 4 | hotpotqa_asi | default+NLP | warm (ddce37b4) |

`max_generations`: 25 | `max_mutations_per_generation`: 8 | `num_parents`: 1

**Docs**: [01_design.md](01_design.md) · [02_review.md](02_review.md) · [03_plan.md](03_plan.md)
**Archives**: https://github.com/KhrulkovV/gigaevo-core-internal/releases/tag/exp/gemini_mutation

---

### Final Result

**Verdict**: INCONCLUSIVE (NULL)
**gemini_mean**: 59.50% vs cold_start ref 59.58% (Δ = −0.08pp)

| Run | Val F1 | Val EM | Test EM | Val-Test Gap | Valid? |
|-----|--------|--------|---------|:------------:|--------|
| V1 | 74.15% | 66.00% | 58.33% | +7.67pp | Yes |
| V2 | 73.38% | 65.00% | 60.67% | +4.33pp | Yes |
| **Mean** | 73.77% | 65.50% | **59.50%** | +6.00pp | — |

**Full analysis**: [05_results.md](05_results.md)

### Top-10 Val-EM Programs (post-hoc)

5/20 programs ≥ GEPA (62.3%). Best: **63.33%** (V2, gen=19, gap=+1.17pp).
Val-test gap is near-perfect predictor: gap<2pp→62-63%, gap>5pp→56-59%.
Implies selection mechanism (not program quality) is the binding constraint.
