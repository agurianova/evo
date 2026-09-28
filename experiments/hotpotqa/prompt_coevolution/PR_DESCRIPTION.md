## Experiment: Prompt Co-Evolution

**Status**: 🔵 Pre-registered (Amendment #8: 3+1 topology)
**Branch**: `exp/prompt_coevolution`
**Pre-registration commit**: `4ccb787`
**Related issue**: #83

---

### Hypothesis

**H₀**: Co-evolved mutation prompts produce test EM indistinguishable from the fixed-prompt cold-start baseline (mean 59.58%, SD=1.00pp, n=4).
**H₁**: Co-evolved mutation prompts produce test EM ≥ 61.58% (mean), +2.00pp above the cold-start reference (2σ).
**Primary metric**: Test EM of best-by-val program at gen 25 on `HotpotQA_test.jsonl` (300 samples).
**Decision threshold**: Treatment mean ≥ 61.58% → POSITIVE (suggestive, n=3; replication at n≥4 required)

---

### Design

4 concurrent processes — 3 treatment main runs + 1 prompt evolution run (1-to-many coupling).
No within-experiment controls; comparison against historical cold-start reference (PR #75, n=4).

| Run | Label | Condition | DB | `pipeline` | Seed |
|-----|-------|-----------|----|-----------:|------|
| X1 | coevo-1 | Treatment (main) | 4 | `hotpotqa_asi` | Cold |
| X2 | coevo-2 | Treatment (main) | 5 | `hotpotqa_asi` | Cold |
| X3 | coevo-3 | Treatment (main) | 8 | `hotpotqa_asi` | Cold |
| P1 | prompt-evo | Prompt evolution (multi-source X1+X2+X3) | 6 | `prompt_evolution_multi` | Cold |

`max_generations`: 25 | `max_mutations_per_generation`: 8 (main), 3 (prompt) | `num_parents`: 1
`problem.name`: `chains/hotpotqa/static_f1_600` | F1 fitness, 600-sample val
**Prior**: Beta(1,3) — untested prompts start at fitness 0.25
**Constraint enforcement**: `required_prefix` validates frozen constraints in all prompt outputs

Infrastructure: `exp/prompt_coevolution` (PR #84)

**Docs**: [01_design.md](01_design.md) · [02_review.md](02_review.md) · [03_plan.md](03_plan.md)
**Archives**: *(GitHub Release link — added after Step 8)*

---

### Checkpoint Results

| Gen | Date (UTC) | X1 val F1 | X2 val F1 | X3 val F1 | X1 test EM | X2 test EM | X3 test EM | P1 archive | Notes |
|-----|-----------|-----------|-----------|-----------|------------|------------|------------|------------|-------|
| *(filled in as experiment progresses)* | | | | | | | | | |

---

### Final Result

*(pending)*

**Verdict**: POSITIVE / NULL / NEGATIVE / INCONCLUSIVE
**Treatment mean test EM**: —

| Run | Condition | Best val F1 | Test EM (final) | Valid? |
|-----|-----------|------------|----------------|--------|
| X1  | Co-evolved |           |                |        |
| X2  | Co-evolved |           |                |        |
| X3  | Co-evolved |           |                |        |

**Historical reference** (cold_start, n=4): mean 59.58%, SD=1.00pp

**Full analysis**: [05_results.md](05_results.md)
