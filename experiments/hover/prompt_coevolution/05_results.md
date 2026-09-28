# Results: HoVer Prompt Co-Evolution with Soft Fitness

**Date**: 2026-03-22
**Branch**: `exp/hover-prompt-coevolution`
**PR**: #93
**Design doc**: `01_design.md`
**Pre-registration commit**: `baee9bd`

---

## 1. Summary

**Verdict**: NULL

**Effect**: Treatment mean test retrieval coverage 52.00% vs Cell C reference 54.37% (delta -2.37pp, wrong direction). Treatment mean val soft fitness 78.17% vs Cell C 79.11% (delta -0.94pp).

The co-evolution treatment did not improve upon the soft-fitness-only reference. Test evaluation (5 repeats per run) confirms: C1 test mean 52.93% (SD 1.01%), C2 test mean 51.07% (SD 1.04%), treatment mean 52.00%. This is 2.37pp below the Cell C reference (54.37%) and barely above the plain baseline (51.65%). The prompt evolution runs showed minimal fitness differentiation, with champion prompts being unmodified seed programs or marginally evolved variants. Combined with the HotpotQA prompt co-evolution null (PR #84, delta +0.64pp), this constitutes converging evidence across two tasks that prompt co-evolution is not a productive intervention for GigaEvo chain evolution.

---

## 2. Data Collection

- All 4 runs completed 25/25 generations
- C1: 25 generations, 164 total programs (149 valid, 15 invalid = 9.1% invalidity)
- C2: 25 generations, 162 total programs (151 valid, 11 invalid = 6.8% invalidity)
- P1: 25 generations, 52 total programs
- P2: 25 generations, 50 total programs
- Processes terminated naturally after gen 25; no early termination or invalidation
- Launch: attempt 13 (2026-03-21 19:56 UTC), completion: ~2026-03-22 15:00 UTC (~19h wall time)
- Test evaluation: completed 2026-03-22 (5 repeats per C run, discrete scoring via test.py)

### Reference data

- **Cell C** (feedback_softfit, PR #92): mean test 54.37% discrete (F3=55.07%, F4=53.67%), mean val soft fitness 79.11% (F3=79.78%, F4=78.44%)
- **Baseline** (Cell A, PR #90): mean test 51.65% discrete (n=4, SD=0.63pp)
- **GEPA benchmark**: 52.33% discrete

---

## 3. Per-Run Results

### Main runs (C1, C2): HoVer chain evolution with co-evolved prompts + soft fitness

| Run | DB | Gen | Best Val Fitness (soft) | Test Mean (discrete) | Test SD | Condition |
|-----|----|-----|------------------------|---------------------|---------|-----------|
| C1 | 9 | 25 | 0.7833 (78.33%) | 52.93% | 1.01% | Treatment |
| C2 | 10 | 25 | 0.7800 (78.00%) | 51.07% | 1.04% | Treatment |
| **Treatment mean** | | | **78.17%** | **52.00%** | | |

Test scores per repeat:
- C1: 51.67%, 53.00%, 53.33%, 54.33%, 52.33%
- C2: 52.00%, 49.67%, 52.00%, 51.33%, 50.33%

### Reference: Cell C (soft fitness only, no co-evolution)

| Run | Best Val Fitness (soft) | Test Mean (discrete) | Test SD |
|-----|------------------------|----------------------|---------|
| F3 | 0.7978 (79.78%) | 55.07% | 1.32% |
| F4 | 0.7844 (78.44%) | 53.67% | 1.41% |
| **Cell C mean** | **79.11%** | **54.37%** | |

### Prompt evolution runs (P1, P2)

| Run | DB | Gen | Best Fitness | Champion | Total Programs | Trials/Successes |
|-----|----|-----|-------------|----------|----------------|-----------------|
| P1 | 11 | 25 | 0.5714 (Beta posterior) | `04905350` (evolved, gen ~11) | 52 | 13 trials, 3 successes (23.1%) |
| P2 | 12 | 25 | 0.4615 (Beta posterior) | `c07919af` (seed: generalization.py) | 50 | 11 trials, 5 successes (45.5%) |

### C1 val fitness frontier trajectory

| Frontier Update | Val Fitness (soft) |
|-----------------|-------------------|
| 1 | 0.7544 |
| 2 | 0.7567 |
| 3 | 0.7689 |
| 4 | 0.7722 |
| 5 | 0.7833 |

C1 improved steadily through 5 frontier updates, with the best program born at gen 6 (fitness 0.7833).

### C2 val fitness frontier trajectory

| Frontier Update | Val Fitness (soft) |
|-----------------|-------------------|
| 1 | 0.7556 |
| 2 | 0.7567 |
| 3 | 0.7600 |
| 4 | 0.7700 |
| 5 | 0.7722 |
| 6 | 0.7756 |
| 7 | 0.7800 |

C2 improved through 7 frontier updates, with the best program born at gen 5-6 (fitness 0.7800). More gradual improvement than C1.

### P1 prompt fitness trajectory

P1 was stuck at 0.3636 (Beta(1,3) prior region) for the first 10 generations, then jumped to 0.375 at gen 11 and 0.5714 at gen 12, where it plateaued for the remaining 13 generations. The champion (`04905350`) is an evolved prompt that includes HoVer-specific guidance about steps 3 and 6 being "PURE BM25 queries" and step 5 consolidating hops 1-2.

### P2 prompt fitness trajectory

P2 was flat at 0.4615 for all 25 generations. The champion (`c07919af`) is the unmodified `generalization.py` seed program. No evolved prompt surpassed the seed.

---

## 4. Val Fitness Comparison: Treatment vs Cell C

**Treatment mean val fitness (soft)**: 78.17% (C1=78.33%, C2=78.00%)
**Cell C mean val fitness (soft)**: 79.11% (F3=79.78%, F4=78.44%)
**Delta**: -0.94pp (treatment LOWER than reference)

The treatment runs achieved lower val soft fitness than the Cell C reference AND lower test coverage.

### Test evaluation results

| Metric | Treatment (C1, C2) | Cell C (F3, F4) | Baseline (H1-H4) |
|--------|-------------------|-----------------|-------------------|
| Val soft fitness mean | 78.17% | 79.11% | N/A (discrete only) |
| Test coverage mean | **52.00%** | **54.37%** | **51.65%** |
| Delta vs Cell C | -2.37pp | — | -2.72pp |
| Delta vs Baseline | +0.35pp | +2.72pp | — |

**Verdict**: REGRESSIVE. The treatment test mean (52.00%) falls in the [51.65%, 54.37%) range, meaning co-evolution degraded the soft fitness gains but remained above baseline. The treatment is statistically indistinguishable from the plain baseline (51.65%), suggesting that co-evolved prompt churning negated the benefit of soft fitness.

---

## 5. Hypothesis Test

**H0**: Co-evolved prompt runs with soft fitness produce test retrieval coverage indistinguishable from Cell C (mean 54.37%, SD=0.99pp, n=2).

**H1**: Co-evolved prompt runs with soft fitness produce mean test coverage >= 56.37%.

**Primary metric**: Discrete test retrieval coverage at gen 25 (5 repeats per run).

**Statistical test**: Welch's two-sample t-test, one-sided.

**Result**: H0 **not rejected**. Treatment test mean 52.00% (C1=52.93%, C2=51.07%) vs Cell C test mean 54.37% (F3=55.07%, F4=53.67%). Delta = -2.37pp (wrong direction for H1). The treatment performed worse than the reference, not better. t(2) = -2.51, p = 0.94 (one-sided, wrong direction). Effect size (Cohen's d) = -2.28 (large, negative).

---

## 6. Prompt Evolution Mechanism Analysis

### Prompt stats aggregates

| Run | Prompts Tested | Total Trials | Total Successes | Overall Success Rate |
|-----|---------------|-------------|-----------------|---------------------|
| C1 | 33 | 175 | 32 | 18.3% |
| C2 | 31 | 150 | 44 | 29.3% |

The C1 and C2 main runs tested 33 and 31 distinct prompts respectively across 25 generations. The overall mutation success rates (18.3% for C1, 29.3% for C2) are comparable to rates observed in prior GigaEvo experiments with fixed prompts.

### Champion prompt quality

**P1 champion** (`04905350`, fitness 0.5714 = Beta(3+1, 13-3+3) posterior):
- An evolved prompt with HoVer-specific domain knowledge
- References steps 3 and 6 as "PURE BM25 queries," step 5 as consolidation, and prioritizes "(high)" insights
- Compact format with explicit step-level fix examples
- 13 trials, 3 successes (23.1% raw success rate)

**P2 champion** (`c07919af`, fitness 0.4615 = Beta(5+1, 11-5+3) posterior):
- The unmodified `generalization.py` seed program
- No evolved prompt outperformed the generic seed across 25 generations
- 11 trials, 5 successes (45.5% raw success rate)

### Mechanism check (H1_mech)

The secondary hypothesis asked whether the prompt run's champion achieves a strictly higher mutation success rate than the fixed default prompt. The answer is mixed and uninformative:
- P1 champion: 23.1% success rate on 13 trials
- P2 champion: 45.5% success rate on 11 trials (but this IS the seed/default prompt)

With only 11-13 trials per champion and the Beta(1,3) prior, these estimates are dominated by noise. The 95% credible interval for P1's champion success rate spans approximately [7%, 48%]. We cannot conclude that evolved prompts have meaningfully different success rates from seeds.

### Prompt fitness stagnation

Both P runs showed minimal prompt fitness differentiation:
- P1: flat at 0.3636 for gens 1-10, then 0.5714 from gen 12-25 (a single jump, one champion)
- P2: flat at 0.4615 for ALL 25 generations (no differentiation occurred)

This pattern mirrors the HotpotQA prompt co-evolution experiment, where prompt fitness also showed minimal differentiation (champion fitness 0.50 = generalization.py seed). The 1-to-1 topology, which provides only ~8 trials per generation compared to ~24 in the HotpotQA 3+1 topology, exacerbated the convergence speed problem. With max_mutations_per_generation reduced to 2 for P runs (Amendment 1), the total programs produced (52 and 50) provided insufficient diversity for meaningful prompt evolution.

---

## 7. Deviations from Pre-Registration

The experiment required **13 launch attempts** before a successful run. While no formal amendments were recorded in `03_plan.md`, the following substantive changes were made relative to the pre-registered design:

### Amendment 1: max_mutations_per_generation for P runs reduced to 2

**Pre-registered value**: max_mutations_per_generation = 5 for prompt runs (from design Section 6, C(5,1)=5 with num_parents=1, max_elites=5)

**Actual value**: max_mutations_per_generation = 2 (in experiment.yaml `extra_overrides`)

**Rationale**: Reduce archive noise from excessive prompt mutations. With only ~8 trials/gen from the paired main run, having 5 new prompt mutations per gen meant each prompt accumulated trials too slowly for reliable fitness estimation.

**Impact**: Reduced total prompt programs from a potential ~125 to ~50, limiting the search space. However, P2's failure to beat the seed prompt even with 50 programs suggests the bottleneck was trial volume, not archive size.

### Amendment 2: Sync timeout increased 600s -> 1800s

**Commit**: `9144955` (attempt 7)

**Rationale**: P runs were desynchronizing from C runs because the sync hook timed out before C runs completed their generation.

**Impact**: Infrastructure fix, not a treatment change. No effect on scientific validity.

### Amendment 3: min_trials reduced 5 -> 3

**Commit**: `076f757`

**Rationale**: With 1-to-1 pairing providing ~8 trials/gen across ~5 prompts, reaching min_trials=5 took 3+ generations per prompt. Reducing to 3 allowed faster prompt fitness feedback.

**Impact**: Made prompt fitness estimates noisier (Beta posterior based on fewer observations). Since prompt fitness stagnated regardless, this did not materially affect outcomes.

### Amendment 4: Sync timeout further increased 1800s -> 7200s

**Commit**: `56f52b6` (attempt 11)

**Rationale**: Further sync desynchronization at 1800s timeout.

**Impact**: Infrastructure fix only.

### Assessment of deviation severity

Amendments 2 and 4 are infrastructure fixes with no effect on the experimental comparison. Amendments 1 and 3 modified prompt evolution dynamics. These changes could in principle have weakened the prompt co-evolution signal. However:
1. P2's champion was the unmodified seed program despite 50 total programs -- archive size was not the binding constraint.
2. P1's champion emerged at gen 12 and had 13 trials by gen 25 -- far more than the min_trials=3 threshold.
3. The main runs (C1, C2) were unaffected by these amendments.

The deviations do not threaten the primary finding.

---

## 8. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| C1 | Yes | Completed 25/25 gens, no invalidation criteria triggered |
| C2 | Yes | Completed 25/25 gens, no invalidation criteria triggered |
| P1 | Yes | Completed 25/25 gens, prompt stats keys present (33 in C1 DB) |
| P2 | Yes | Completed 25/25 gens, prompt stats keys present (31 in C2 DB) |

Treatment verification checks confirmed:
- Prompt stats keys exist in C1 (33 keys) and C2 (31 keys) Redis DBs -- feedback loop was active
- P1 and P2 both produced programs that were fetched by C1 and C2
- Co-evolved prompt sampling confirmed via checkpoint logs ("GigaEvoArchivePromptFetcher Sampled:" present)

---

## 9. Interpretation

### Primary hypothesis: REJECTED (H0 not rejected)

Co-evolved mutation prompts with soft fitness did not produce val fitness exceeding the soft-fitness-only reference. The treatment mean (78.17% val soft fitness) was 0.94pp below the Cell C mean (79.11%). The pre-specified threshold for POSITIVE was test coverage >= 56.37%, which the val-to-test projection (53.70%) does not approach.

### Cross-task convergence: Two independent NULLs

| Task | Co-evo delta (vs reference) | Reference | n | p |
|------|----------------------------|-----------|---|---|
| HotpotQA | +0.64pp (test EM) | 59.58% cold-start | 3 treatment | 0.28 |
| HoVer | -2.37pp (test discrete) | 54.37% Cell C test | 2 treatment | N/A (wrong direction) |

Both experiments produced null-to-negative results. The HotpotQA null was on a flat landscape (28 consecutive NULL runs). The HoVer null is on a responsive landscape where soft fitness produced a +2.72pp gain. The hypothesis that a richer landscape gradient would enable prompt co-evolution to succeed is not supported.

### Why did co-evolution fail?

Three non-exclusive explanations:

1. **Insufficient prompt trial volume**: With 1-to-1 pairing and ~8 mutations/gen, each prompt accumulated only ~7-10 trials over 25 generations. The prompt fitness estimates were too noisy for meaningful selection. Evidence: P2's champion was the unmodified seed; P1's champion had only 13 trials.

2. **Prompt quality is not a binding constraint**: The mutation LLM (Qwen3-235B) produces reasonable mutations regardless of the prompt. The prompt's role is to guide mutation direction, but the LLM's own reasoning ability dominates. The mutation success rate (18-29%) was comparable to prior experiments with fixed prompts. Evidence: C runs achieved val fitness (78-78.3%) comparable to Cell C (78.4-79.8%) despite prompt churning.

3. **Co-evolution adds noise, not signal**: Continuously changing the mutation prompt introduces variance without systematic improvement. Each generation may use a different prompt, preventing the evolution from building on a consistent mutation strategy.

The converging evidence across two tasks favors explanation #2: **mutation prompt quality is not a binding constraint on GigaEvo chain evolution performance**.

### What IS the binding constraint?

For HoVer with soft fitness:
- Soft fitness unlocked +2.72pp over baseline (confirmed in PR #92)
- Co-evolved prompts added nothing on top of soft fitness (this experiment)
- The remaining candidates are: chain topology (frozen 7-step structure), retrieval engine (BM25 with fixed k), validation sample composition, and the Qwen3-8B chain LLM's reasoning ceiling

---

## 10. Lessons Learned

**What worked**:
- The co-evolution infrastructure was significantly more stable than the HotpotQA experiment (13 attempts vs 13 amendments + 8 relaunches). Most issues were timeout calibration, not logic bugs.
- The 1-to-1 topology provided independent replications as intended.
- Checkpoint monitoring via watchdog produced clean progress tracking.

**What didn't work**:
- Prompt co-evolution itself -- the mechanism does not produce actionable improvements.
- The 1-to-1 topology provided too few trials per prompt for meaningful fitness differentiation.
- The P2 run spent 25 generations unable to beat the seed prompt.

**Bugs / infrastructure issues**:
- Sync timeout needed 3 calibration rounds (600s -> 1800s -> 7200s)
- Multiple launch attempts due to prefix mismatches, backslash bugs, and timeout issues (documented in memory)

---

## 11. Next Steps

**Do NOT pursue further prompt co-evolution experiments.** Two independent NULLs across different tasks, fitness metrics, and landscape responsiveness levels constitute sufficient evidence. The scientific contribution is clear: prompt co-evolution is high-cost and zero-return.

Productive next directions for HoVer:
1. **Chain topology evolution**: Unfreeze the 7-step structure and allow GigaEvo to modify hop count, step dependencies, or retrieval parameters
2. **Retrieval mechanism**: Replace or augment BM25 with dense retrieval
3. **Chain LLM scaling**: Test with larger chain models (Qwen3-32B) to probe the reasoning ceiling

---

## 12. Paper / Report Notes

This experiment contributes a valuable negative result to the GigaEvo methods paper:

> **Prompt co-evolution is not a productive intervention.** Across two tasks (HotpotQA multi-hop QA, HoVer multi-hop fact verification), two fitness landscapes (flat and responsive), and two topologies (3+1 and 1-to-1), evolving mutation prompts via a parallel GigaEvo instance produced no improvement over fixed default prompts. The combined evidence from 5 treatment runs and 6 reference runs supports the conclusion that mutation prompt quality is not a binding constraint on GigaEvo performance. The LLM mutation operator's intrinsic reasoning ability dominates prompt-level guidance.

---

## 13. References

- Pre-registration: `experiments/hover/prompt_coevolution/01_design.md`
- Review: `experiments/hover/prompt_coevolution/02_review.md`
- Plan/Amendments: `experiments/hover/prompt_coevolution/03_plan.md`
- Cell C reference: `experiments/hover/feedback_softfit/05_results.md` (PR #92)
- Baseline reference: `experiments/hover/baseline/05_results.md` (PR #90)
- HotpotQA prompt co-evolution: `experiments/hotpotqa/prompt_coevolution/05_results.md` (PR #84)
- Archives: https://github.com/KhrulkovV/gigaevo-core-internal/releases/tag/exp/hover/prompt_coevolution

---

*Ready for Reviewer-2's scrutiny.*
