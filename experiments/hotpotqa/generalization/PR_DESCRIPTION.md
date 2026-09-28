## Experiment: generalization

**Status**: 🟢 Complete
**Branch**: `exp/hotpotqa-generalization`
**Pre-registration commit**: `ea0884e`
**Related issue**: #80

---

### Hypothesis

**H₀**: Mean test EM across n=4 held-out-validation runs does not differ from cold-start
reference (59.58%, PR #75, n=4) by more than 1.67pp.

**H₁**: Mean test EM >= 62.00% — held-out validation produces substantially better-generalizing programs.

**Primary metric**: Test EM at gen 25, best-by-held_F1 program, 300-sample test set, Qwen3-8B thinking.

**Decision threshold**: One-sided one-sample t-test vs ref 59.58%, α=0.05, df=3.

---

### Design

| Run | Label | Condition | DB | `pipeline` | `prompts` | Mutation LLM | Seed |
|-----|-------|-----------|----|-----------:|----------:|:------------|------|
| G1 | gen-1 | held_F1 fitness | 0 | hotpotqa_asi | generalization | Qwen3-235B vLLM | cold |
| G2 | gen-2 | held_F1 fitness | 1 | hotpotqa_asi | generalization | Qwen3-235B vLLM | cold |
| G3 | gen-3 | held_F1 fitness | 2 | hotpotqa_asi | generalization | Gemini-3.1-Pro | cold |
| G4 | gen-4 | held_F1 fitness | 3 | hotpotqa_asi | generalization | Gemini-3.1-Pro | cold |

`max_generations`: 25 | `max_mutations_per_generation`: 8 | `num_parents`: 1

**Fitness**: held_F1 on train[700:1000] only — pure unbiased selection signal.
**Evo set**: train[0:700] — failure feedback to mutation LLM only.
**Gap signal**: evo_f1 shown to mutation LLM; large gap (>0.07) triggers generalization-focused mutations.

**Docs**: [01_design.md](01_design.md) · [02_review.md](02_review.md) · [03_plan.md](03_plan.md)
**Archives**: https://github.com/KhrulkovV/gigaevo-core-internal/releases/tag/exp/hotpotqa/generalization

---

### Checkpoint Results

| Gen | Date (UTC) | G1 fitness | G2 fitness | G3 fitness | G4 fitness | Notes |
|-----|-----------|:----------:|:----------:|:----------:|:----------:|-------|
| 1 | 2026-03-14 13:26 UTC | 61.6% | 62.5% | 62.3% | 61.7% | All 4 alive; fitness(held_F1) 55.9–59.3%; gap 3.1–5.8pp (moderate) |
| 21/25 (final) | 2026-03-15 UTC | 66.9% | 66.5% | 72.3% | 74.6% | G1 stopped at gen 21 (Amendment 1). Test EM: G1=55.00%, G2=58.47%, G3=61.00%, G4=59.93% (mean of 5 evals). Mean test EM = 58.60%. |

---

### Final Result

**Verdict**: NULL — mean test EM 58.60% (G1–G4) vs cold-start reference 59.58%; −0.98pp delta; held-out validation fitness did not improve generalization.

**Primary ref**: cold_start 59.58% (PR #75, n=4, SD=1.00pp)

| Run | Mutation LLM | Best held_F1 | val_EM | Test EM (mean±SD, n=5) | Valid? |
|-----|-------------|:------------:|:------:|:----------------------:|--------|
| G1 | Qwen3-235B | 66.94% | 59.30% | 55.00% (n=1) | Yes (gen 21, Amendment 1) |
| G2 | Qwen3-235B | 66.54% | 59.80% | 58.47%±1.41pp | Yes |
| G3 | Gemini-3.1-Pro | 72.34% | 64.40% | 61.00%±1.03pp | Yes |
| G4 | Gemini-3.1-Pro | 74.55% | 64.50% | 59.93%±1.30pp | Yes |

**Full analysis**: [05_results.md](05_results.md)
