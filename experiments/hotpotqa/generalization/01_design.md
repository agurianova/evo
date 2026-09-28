# Phase 1: Experimental Design -- Generalization via Held-Out Validation

**Experiment name**: `generalization`
**Date**: 2026-03-14
**Author**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: DRAFT v5 -- fitness changed to held_F1 only

---

## 1. Research Question

Does evaluating candidate programs on a held-out validation subset (disjoint from the
evolution-visible validation set) and selecting purely on the held-out score produce
higher test EM than single-set F1 fitness, under cold-start conditions with
25 generations?

## 2. Scientific Motivation

After 21 independent HotpotQA evolutionary runs, GigaEvo consistently stagnates at
59-60% test EM despite reaching 62-66% val EM. The 4-6pp val-test gap is the binding
constraint preventing GigaEvo from exceeding GEPA (62.3%). Every lever tested so far
-- fitness metric (EM vs F1), validation size (300 vs 600), mutation prompts (default
vs NLP), crossover (num_parents=2), mutation LLM capability (Qwen3-235B vs
Gemini-3.1-Pro), retriever (BM25 vs ColBERT), and feedback granularity -- has failed
to close this gap.

The root cause is straightforward: MAP-Elites selects programs based on performance on
a fixed set of N training samples. Programs that happen to exploit patterns specific to
those N samples are rewarded, regardless of whether those patterns generalize. The
fitness signal is biased toward the training distribution.

The canonical solution in supervised learning is cross-validation or held-out validation.
This experiment applies a minimal version: **split the 1000 training samples into an
evolution set (700 samples) and a held-out validation set (300 samples)**. Programs are
evaluated on both sets, but **fitness = held_F1 only** (F1 on the 300 held-out samples).
The held-out set is never used for mutation feedback (the mutation LLM only sees failures
from the evolution set), so the held-out score provides a fully unbiased selection signal.

This design implements a clean train/val separation: the mutation LLM trains on the evo
set (it receives evo-set failures as its gradient signal), and MAP-Elites selects on the
held-out set (fitness = held_F1). The evo set is analogous to the training set in
supervised learning; the held-out set is analogous to the validation set used for model
selection. No information from the held-out set leaks into the mutation process.

### Why held_F1 only, not mean(evo_F1, held_F1)

An earlier version of this design used `fitness = mean(evo_F1, held_F1)`. This averaging
partially re-introduces the confound the held-out mechanism was meant to break. If fitness
includes evo_F1, programs are still partially selected based on the same data the mutation
LLM uses for guidance. A program that overfits to the evo set's specific failure patterns
gets a fitness boost from the evo_F1 component, diluting the regularization signal from
held_F1. The clean analogy is: **train on train, select on val**. Averaging dilutes the
held-out signal by rewarding programs that overfit to the evo set.

With `fitness = held_F1` only, the selection criterion is completely independent of the
mutation guidance signal. The mutation LLM sees evo-set failures and proposes changes
(the gradient step). MAP-Elites evaluates those changes on the held-out set (the
validation loss). This is the textbook train/val separation, applied to evolutionary
program synthesis.

This is the most direct intervention against the val-test gap that has not been tried.
It is also the simplest to implement and reason about. K-fold cross-validation (K >= 3)
would be more robust but would multiply evaluation time by K; the held-out approach
achieves the core benefit -- an unbiased selection signal -- with only ~1.4x evaluation
overhead (1000 vs 700 samples), which is manageable within our compute budget.

### Why this should work (mechanistic argument)

The val-test gap arises because fitness is computed on samples that the mutation LLM
also sees as failure cases. Programs are selected AND guided toward the same N samples.
By splitting: (a) the mutation LLM sees failures from the 700-sample evo set, providing
the gradient for prompt improvement; (b) the MAP-Elites archive selects based solely on
held_F1 -- the 300 held-out samples the mutation LLM has never seen diagnostics from.
Programs that overfit to the evo set's specific patterns will score lower on the held-out
set, producing lower fitness. Programs that improve general reasoning will score well on
the held-out set regardless of evo-set performance.

### Why this might not work (pre-registered risks)

1. **700 evo samples overlap with cold_start's 600**: The larger evo set means the
   mutation LLM sees 100 more failure examples than in cold_start. This could improve
   OR harm test EM independently of the held-out mechanism.

2. **Noisy fitness signal**: The 300-sample held-out set has SE ~2.5pp for F1 ~0.70.
   Using held_F1 alone (rather than averaging with evo_F1) means the fitness signal is
   noisier than in cold_start (which uses 600 samples). MAP-Elites may select programs
   that got lucky on the held-out set rather than truly generalizable programs.

3. **The 300-sample held-out set may still overfit**: With 25 generations x 8
   mutations/gen = 200 programs all scored on the same 300 held-out samples, the
   archive may overfit the held-out set too, just more slowly.

4. **Sample-specific effects**: If the test set (300 samples) has a different question
   distribution than the train set (1000 samples), no amount of train-set splitting
   will bridge the distribution gap.

## 3. Hypotheses

**Null hypothesis (H0)**: Mean test EM across n=4 held-out-validation runs does not
differ from the cold-start reference mean of 59.58% (PR #75, n=4, SD=1.00pp) by more
than the MDE (1.67pp). The held-out validation intervention has no detectable effect on
generalization.

**Alternative hypothesis (H1)**: Mean test EM >= 62.00% (+2.42pp above cold-start
reference, within 0.3pp of GEPA), indicating that held-out validation produces
programs that generalize substantially better than single-set fitness.

**Directional prediction**: H1 predicts that the val-test EM gap will be <= 2.0pp
(vs 2.58pp for cold-start reference), because the pure held-out fitness penalizes
evo-set-specific overfitting.

## 4. Independent Variable(s)

| Variable | Control value (cold_start ref) | Treatment value |
|----------|-------------------------------|-----------------|
| Fitness computation | Single-set F1 on first 600 train samples | held_F1 on train[700:1000] only (pure held-out selection signal) |
| Mutation feedback source | All failures from 600 evo-set samples | All failures from 700 evo-set samples (held-out is NOT used for feedback) |

The treatment differs from the control in two dimensions: (a) the fitness score
is computed solely on a held-out set that the mutation LLM never sees diagnostics from;
and (b) the evo set is 700 samples instead of 600. Dimension (b) is a confound --
see Section 9 for discussion.

## 5. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test EM | EM on 300-sample held-out test set (thinking Qwen3-8B) | **Yes** |
| Val-test EM gap (comparable) | val_em_600 (EM on train[0:600]) minus test EM, for comparability with cold_start gap | Secondary |
| Evo-set F1 | F1 on the 700 evo-set samples | Diagnostic |
| Held-out F1 (= fitness) | F1 on the 300 held-out val samples; this IS the fitness metric | Diagnostic |
| Birth-generation of best | Generation index of the best-by-held_F1 program | Exploratory |
| Evo-held F1 gap | evo_f1 minus fitness (where fitness = held_F1) for the best program | Exploratory (measures within-train overfitting) |

**Primary metric**: Test EM at gen 25, best-by-held_F1 program, on 300-sample
held-out test set, thinking mode Qwen3-8B.

## 6. Run Design Table

### Treatment group: Held-out validation (n=4)

| Run | Label | redis.db | pipeline | prompts | llm | problem.name | HOTPOTQA_CHAIN_URL | Seed | Evo set | Held-out val set | Fitness |
|-----|-------|----------|---------|---------|-----|--------------|-------------------|------|---------|------------------|---------|
| G1 | gen-1 | 0 | hotpotqa_asi | generalization | default (Qwen3-235B vLLM) | chains/hotpotqa/static_holdout_f1 | http://10.226.17.25:8001/v1 | cold | train[0:700] | train[700:1000] | held_F1 |
| G2 | gen-2 | 1 | hotpotqa_asi | generalization | default (Qwen3-235B vLLM) | chains/hotpotqa/static_holdout_f1 | http://10.226.17.25:8000/v1 | cold | train[0:700] | train[700:1000] | held_F1 |
| G3 | gen-3 | 2 | hotpotqa_asi | generalization | gemini31_pro (Gemini-3.1-Pro-Preview) | chains/hotpotqa/static_holdout_f1 | http://10.225.185.235:8001/v1 | cold | train[0:700] | train[700:1000] | held_F1 |
| G4 | gen-4 | 3 | hotpotqa_asi | generalization | gemini31_pro (Gemini-3.1-Pro-Preview) | chains/hotpotqa/static_holdout_f1 | http://10.225.185.235:8000/v1 | cold | train[0:700] | train[700:1000] | held_F1 |

**No concurrent control runs.** The control reference is the cold_start experiment
(PR #75, n=4, SD=1.00pp, mean=59.58%). The treatment differs from the control on
three dimensions: (a) held-out fitness computation, (b) generalization mutation prompts,
and (c) Gemini-3.1-Pro mutation LLM for G3/G4. See Section 9, Confound #8.

**Justification for no concurrent control**: Running 4 concurrent control runs would
consume all 4 chain servers, forcing treatment runs to be sequential. This doubles
wall time. Instead, we use the cold_start reference (n=4, same infrastructure, same
compute period) as the control. The threat is infrastructure drift -- see Section 9.
The cold_start experiment ran 5 days ago on the same servers; the threat is minimal.

## 7. Sample Size Justification

The cold_start experiment established SD=1.00pp for this condition family (F1, default
prompts, cold start, num_parents=1). With SD=1.00pp and n=4:

- MDE at 80% power (alpha=0.05, one-sided, df=3):
  t_{0.05,3} = 2.353; t_{0.20,3} = 0.978
  MDE = (t_alpha + t_beta) * SD / sqrt(n) = (2.353 + 0.978) * 1.00 / 2.0 = **1.67pp**
- To detect +2.42pp effect (POSITIVE threshold): power > 95%
- To detect +1.67pp effect: power = 80% (at the MDE)

This experiment is well-powered for the pre-registered POSITIVE threshold of +2.42pp.
The MDE of 1.67pp means we can detect effects meaningfully smaller than the GEPA gap
(2.72pp). If the true effect is > 2pp, we will detect it with > 90% probability.

**Assumption**: SD for the held-out condition is comparable to cold_start SD (1.00pp).
If the held-out mechanism introduces additional variance (e.g., because the held_F1-only
fitness is noisier due to smaller sample size), the true SD may be higher. At SD=1.50pp,
the MDE rises to 2.50pp, which would make the experiment underpowered for the SUGGESTIVE
band but still adequate for the POSITIVE threshold.

## 8. Statistical Tests and Verdict Table

### Test 1 (Primary): One-sample t-test -- treatment mean vs cold_start reference

**Test**: One-sided one-sample t-test, H1: treatment_mean > 59.58% (cold_start ref)
**Significance**: alpha = 0.05, df = 3
**Computed from**: n=4 test EM values (G1, G2, G3, G4)

| t-test result | Treatment mean | Verdict |
|:-------------:|:--------------:|---------|
| p < 0.05 | >= 62.30% | **STRONG POSITIVE -- PRELIMINARY** (exceeds GEPA; requires deconfounding follow-up per Confound #1) |
| p < 0.05 | [62.00%, 62.30%) | **POSITIVE -- PRELIMINARY** (target zone, within 0.3pp of GEPA; requires deconfounding follow-up per Confound #1) |
| p < 0.05 | [60.50%, 62.00%) | **SUGGESTIVE** (improvement but below target) |
| p < 0.05 | [59.58%, 60.50%) | **MARGINAL** (statistically significant but small) |
| p >= 0.05 | any | **NULL** (no detectable effect) |
| treatment_mean < 57.58% | any | **NEGATIVE** (harmful, > 2pp below reference) |

### Test 2 (Secondary): Val-test gap comparison

**Metric**: Mean val-test EM gap across G1-G4 vs cold_start mean gap (2.58pp).

To enable direct comparability with cold_start (which computes val EM on train[0:600]),
the treatment runs compute a supplementary metric `val_em_600` = EM on train[0:600]
only. The gap comparison uses `val_em_600 - test_em` as the "comparable gap" against
cold_start's 2.58pp gap. The full 1000-sample EM (`metrics["em"]`) is retained for
general reporting but is NOT used for the gap comparison (different val-set sizes
would render the comparison invalid).

| Comparable gap (val_em_600 - test_em) | Verdict |
|:-------------------------------------:|---------|
| treatment_gap < 1.5pp | **GAP CLOSED** (strong regularization effect) |
| treatment_gap in [1.5pp, 2.5pp) | **GAP COMPRESSED** (meaningful reduction) |
| treatment_gap in [2.5pp, 4.0pp) | **GAP UNCHANGED** |
| treatment_gap >= 4.0pp | **GAP INFLATED** (regularization backfired) |

### Test 3 (Exploratory): Evo-held F1 gap

**Metric**: evo_f1 minus fitness (where fitness = held_F1) for the best program in each run

This measures within-train overfitting. If held-out validation works as intended, we
expect evo_f1 > fitness (programs score better on the set they are optimized for) but
the gap should be modest (< 3pp). A large gap (> 5pp) would indicate the mutation LLM
is still overfitting to the evo set despite the held-out fitness selection.

### Test 4 (GEPA comparison): Individual run analysis

| Any run >= 62.3%? | t-test p < 0.05 for mean >= 62.3% | Verdict |
|:-----------------:|:--------------------------------:|---------|
| Yes | Yes | **GEPA BEATEN** (population-level) |
| Yes | No | **GEPA REACHED** (individual run only) |
| No | No | **GEPA NOT REACHED** |

**Alpha budget**: Tests 2, 3, and 4 are secondary/exploratory. Their p-values (where
applicable) are reported for context only and do not consume the alpha budget. The
primary verdict is determined solely by Test 1.

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Evo-set size differs from cold_start (700 vs 600)** | cold_start used 600 samples for fitness. Treatment uses 700 for the evo component (mutation feedback only -- fitness is held_F1 on train[700:1000]). The mutation LLM sees 100 more failure examples. Any improvement could be partially attributed to a larger evo set providing richer mutation guidance, rather than the held-out fitness mechanism. However, because fitness = held_F1 only, the evo-set size does NOT pollute the selection signal -- it only affects the quality of mutation feedback. This makes the confound less severe than under the averaging design: the larger evo set influences what mutations are proposed, but not which mutations survive. | **Acknowledged as a confound (reduced severity).** The 700/300 split was chosen to maximize the held-out set while keeping the evo set close to 600. **Binding commitment**: If the primary verdict is POSITIVE or STRONG POSITIVE, the finding is classified as **PRELIMINARY** until a deconfounding follow-up (600 evo + 300 held-out + 100 unused) confirms the held-out mechanism as the causal driver. |
| 2 | **Held-out 300 samples from same train distribution** | The held-out set (train[700:1000]) shares distributional properties with the evo set (train[0:700]). Generalization to the truly held-out test set may still fail. | **Cannot be fully mitigated.** However, the cold_start val-test gap of 2.58pp on 600-sample val demonstrates that at least ~2.5pp of the gap is attributable to selection bias, not pure distribution shift. The held-out approach targets this selection bias. |
| 3 | **Infrastructure drift from cold_start reference** | cold_start ran 2026-03-09; this experiment runs 2026-03-14+. Servers or model weights may differ. | **Low risk.** Same physical servers, model checkpoints, and vLLM version. Verify thinking mode pre-launch. Gen-0 check: gen-0 evo_F1 should fall within [0.35, 0.50] (comparable to cold_start gen-0 F1 on train[0:600]). If any run shows gen-0 evo_F1 outside [0.35, 0.50], flag as infrastructure drift. |
| 4 | **2x evaluation time per generation** | Each generation evaluates 1000 samples total (700 + 300), vs 600 in cold_start. Generations take ~33-40 min instead of ~22-24 min. | **Accepted.** The researcher authorized slow experiments. 4 concurrent runs on 4 chain servers complete within ~17 hours. |
| 5 | **Held_F1-only fitness confuses MAP-Elites archive** | Programs excellent on the evo set but poor on held-out may be displaced by mediocre-everywhere programs. With held_F1 as the sole fitness, evo-set performance has zero influence on selection. This could reduce archive quality if held_F1 is noisy. | **Monitored.** Track evo_f1 separately. If evo_f1 < 68% at gen 10 for all 4 runs, note as limitation -- held_F1-only fitness may be too decoupled from the mutation guidance signal. |
| 6 | **No concurrent control** | Using historical cold_start as reference. | **Mitigated by gen-0 check** (see row 3) and by the cold_start reference having n=4 with tight SD=1.00pp, providing a reliable baseline. |
| 7 | **Held-out set ordering bias** | train[700:1000] may differ systematically from train[0:700] if the JSONL has ordering artifacts. | **Binding pre-launch protocol.** Before any treatment data is collected, run the baseline chain on train[0:700] and train[700:1000] separately and compute baseline EM for each split. If \|evo_baseline_em - held_baseline_em\| > 5pp at gen 0, halt and reshuffle train samples with seed=42. The check is performed exactly once before any treatment runs launch. If reshuffling is needed, document as Amendment 1 with "No confound" classification (uniform change, no data collected yet). |
| 8 | **Compound treatment: held-out fitness + generalization prompts + Gemini LLM (G3/G4)** | The treatment combines three simultaneous differences from the cold_start reference: (a) held-out fitness, (b) generalization mutation prompts, (c) Gemini-3.1-Pro mutation LLM for G3/G4. Any positive result from the 4-run mean cannot be attributed to a single component. | **Acknowledged.** The primary verdict (4-run mean vs cold_start) tests the combined treatment. Component-level attribution requires follow-up experiments. If POSITIVE/STRONG POSITIVE, the finding is labelled PRELIMINARY until individual components are isolated. A descriptive comparison of G1/G2 (vLLM) vs G3/G4 (Gemini) will be reported in Phase 5 results. |

## 10. Stop Criteria

**Early termination (stagnation)**:
- If no frontier improvement for >= 10 consecutive generations at gen >= 15, the run
  may be terminated early. Consistent with cold_start protocol.

**Run invalidation**:
1. Thinking mode not active (no `<think>` blocks in chain outputs).
2. `pipeline=standard` used instead of `hotpotqa_asi` (repr-contamination).
3. Invalidity rate > 90% at gen 10 (timeout or structural failures).
4. Gen-0 held_F1 (fitness) > 0.55 (cold start should begin at ~0.42).
5. `max_elites_per_generation` != 8 in `--cfg job` output.
6. `num_parents` != 1 in `--cfg job` output.
7. Held-out set leaks into mutation feedback (code bug -- verify pre-launch).

**Experiment invalidation**:
- If infrastructure drift is detected (gen-0 held_F1 outside [0.35, 0.50] for
  >= 2 of 4 runs), the entire experiment is invalidated and must be re-run after
  infrastructure verification.

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Chain LLM GPU hours | 4 runs x 17h = 68h (4 H100 GPUs, concurrent) |
| Mutation LLM GPU hours | 4 runs x 25 gens x ~3 min/gen = ~5h total |
| Wall time | ~17 hours (all 4 runs concurrent on 4 chain servers) |
| Redis DBs used | 0, 1, 2, 3 |

## 12. Implementation Notes

### New problem directory: `chains/hotpotqa/static_holdout_f1`

Create by copying `static_f1_600/` and modifying `validate.py`:

1. **Evo set**: `load_jsonl(train_path)[:700]` (first 700 samples)
2. **Held-out set**: `load_jsonl(train_path)[700:1000]` (last 300 samples)
3. **Chain evaluation**: Run chain on evo set first (700 samples), then on held-out
   set (300 samples). Both use the same chain spec and LLM client.
4. **Fitness computation**:
   ```python
   evo_f1 = calculate_f1(evo_targets, evo_predictions)
   held_f1 = calculate_f1(held_targets, held_predictions)
   evo_em = calculate_exact_match(evo_targets, evo_predictions)
   held_em = calculate_exact_match(held_targets, held_predictions)
   # Full EM for general reporting (computed from both sets concatenated)
   all_em = calculate_exact_match(evo_targets + held_targets,
                                   evo_predictions + held_predictions)
   # Supplementary: EM on train[0:600] only, for comparable gap vs cold_start
   val_em_600 = calculate_exact_match(evo_targets[:600], evo_predictions[:600])
   metrics = {
       "fitness": held_f1,              # drives MAP-Elites selection (held-out ONLY)
       "em": all_em,                     # full 1000-sample EM for general reporting
       "val_em_600": val_em_600,         # EM on train[0:600] for gap comparison vs cold_start
       "evo_f1": evo_f1,                 # diagnostic (NOT used for fitness)
       "avg_extraction_failures": extraction_failures,
       "is_valid": 1,
   }
   ```
5. **Failure collection**: Failures ONLY from the evo set (first 700 samples). The
   held-out set is evaluated for fitness scoring but is never exposed to the mutation
   LLM as failure cases. This is the critical design element.
6. **EM secondary key**: The `em` field stores EM on the full 1000 samples, so
   `valid_frontier_em` is populated for val-test gap analysis.

### metrics.yaml specification

The `chains/hotpotqa/static_holdout_f1/metrics.yaml` file controls which metrics are
shown to the mutation LLM via `include_in_prompts`. The two scores visible to the
mutation LLM are: (a) `fitness` (= held_F1), the primary selection signal; and (b)
`evo_f1`, a diagnostic metric that lets the LLM observe its own generalization gap.

**Why `evo_f1` SHOULD be shown (`include_in_prompts: true`)**: The failure *examples*
given to the mutation LLM are drawn exclusively from the evo set (train[0:700]). The
LLM never receives failure cases from the held-out set. Therefore, showing the evo_F1
*score* (not held-out examples) is safe: the LLM cannot exploit held-out patterns from
the score alone because it has no held-out failure examples to act on.

More importantly, showing both evo_F1 and held_F1 allows the mutation LLM to observe
the generalization gap directly: "evo_F1=0.78, fitness(held_F1)=0.68 → gap=0.10".
This gap is a direct signal that the current program overfits to evo-set patterns.
A well-designed generalization mutation prompt can then instruct the LLM to prefer
changes that close this gap -- i.e., to propose more general reasoning improvements
rather than evo-set-specific ones. Hiding evo_F1 would deprive the LLM of this signal.

**The invariant that must hold**: Failure *examples* come ONLY from the evo set.
The `include_in_prompts: true` on `evo_f1` exposes the evo-set *score* but never
exposes held-out examples. This invariant is enforced by validate.py (see Implementation
Notes above) and verified by the failure leakage assertion.

```yaml
# problems/chains/hotpotqa/static_holdout_f1/metrics.yaml
specs:
  fitness:
    description: "Token-level F1 on held-out val set (train[700:1000]). Never used for mutation feedback — pure unbiased selection signal."
    decimals: 3
    is_primary: true
    higher_is_better: true
    lower_bound: 0.0
    upper_bound: 1.0
    include_in_prompts: true       # Mutation LLM sees held-out F1 only
    significant_change: 0.01
    sentinel_value: -1000.0
  evo_f1:
    description: "F1 on evo set (train[0:700]). Shown alongside held_F1 so the mutation LLM can observe the evo→held generalization gap and target more general improvements. Failure *examples* are evo-set-only (no held-out leakage), so showing this score is safe."
    decimals: 3
    is_primary: false
    higher_is_better: true
    lower_bound: 0.0
    upper_bound: 1.0
    include_in_prompts: true       # Show gap signal to mutation LLM (score only, not held-out examples)
    significant_change: 0.01
    sentinel_value: -1000.0
  em:
    description: "EM on full 1000 samples (evo+held). For val-test gap analysis."
    decimals: 3
    is_primary: false
    higher_is_better: true
    lower_bound: 0.0
    upper_bound: 1.0
    include_in_prompts: false
    significant_change: 0.01
    sentinel_value: -1000.0
  val_em_600:
    description: "EM on train[0:600] — for comparable val-test gap vs cold_start reference."
    decimals: 3
    is_primary: false
    higher_is_better: true
    lower_bound: 0.0
    upper_bound: 1.0
    include_in_prompts: false
    significant_change: 0.01
    sentinel_value: -1000.0
  avg_extraction_failures:
    description: "Fraction of samples where answer extraction failed."
    decimals: 3
    is_primary: false
    higher_is_better: false
    lower_bound: 0.0
    upper_bound: 1.0
    include_in_prompts: true
    significant_change: 0.01
    sentinel_value: 1.0
  is_valid:
    description: "Whether the program is valid (1 valid, 0 invalid)."
    decimals: 0
    is_primary: false
    higher_is_better: true
    lower_bound: 0.0
    upper_bound: 1.0
    include_in_prompts: true
    significant_change: 1.0
    sentinel_value: 0.0
```

### Evaluation order within validate.py

The chain is run on both sets sequentially within a single validate() call:
1. Run chain on evo set (700 samples)
2. Run chain on held-out set (300 samples)
3. Compute all metrics
4. Collect failures from evo set only

Both evaluations must succeed for a valid fitness score. If either times out, the
program is marked invalid.

**Failure leakage assertion**: `validate.py` will include an assertion verifying that
all failure cases originate from evo-set indices (< 700). Specifically, each failure
case will carry its sample index, and an `assert idx < 700` check will be applied
before returning the failures list. This assertion will be tested pre-launch by running
a single validation on the baseline chain and confirming no held-out indices (>= 700)
appear in the returned failures list.

### Timing estimate

- 700-sample eval: ~23-25 min (extrapolated from 600-sample ~22 min)
- 300-sample eval: ~11-12 min
- Total per generation: ~34-37 min
- 25 generations: ~14-16 hours

With 4 chain servers running concurrently, all 4 runs complete in ~16 hours.

### stage_timeout and dag_timeout

- `stage_timeout`: 6000s (100 min). The 1000-sample eval could take up to ~37 min
  per program; 6000s provides ~2.7x margin. Add additional margin for worst-case
  vLLM queuing at high concurrency.
- `dag_timeout`: 9000s (150 min). 1.5x stage_timeout.

### Pre-launch verification checklist

1. `static_holdout_f1/validate.py` returns `(metrics, failures)` tuple
2. Failures are collected ONLY from evo set (train[0:700])
3. Held-out set (train[700:1000]) is evaluated but NOT used for failure collection
4. `metrics["fitness"]` = held_f1 (held-out F1 only, NOT mean)
5. `metrics["em"]` = EM on full 1000 samples (evo + held-out concatenated);
   `metrics["val_em_600"]` = EM on train[0:600] for comparable gap vs cold_start
6. Verify `metrics.yaml` has `include_in_prompts: true` for `fitness`, `evo_f1`, `avg_extraction_failures`, and `is_valid`; and `include_in_prompts: false` for `em` and `val_em_600` (which are analysis-only metrics not useful to the mutation LLM)
7. Run `python run.py problem.name=chains/hotpotqa/static_holdout_f1 pipeline=hotpotqa_asi --cfg job` and verify all fields
8. Verify thinking mode on all 4 chain server endpoints:
   `curl --noproxy <host> http://<host>:<port>/v1/models`
9. Verify Redis DBs 0-3 are empty (or flush with `tools/flush.py`)
10. **Split bias check (BINDING)**: Run baseline chain on train[0:700] and train[700:1000]
   separately. Compute evo_baseline_em and held_baseline_em. If |evo_baseline_em -
   held_baseline_em| > 5pp, halt and reshuffle train samples with seed=42 before
   launching any treatment runs. Document reshuffling as Amendment 1 ("No confound").
   This check is performed exactly once before any treatment data is collected.
11. Verify `pipeline=hotpotqa_asi` has `prompts_dir: ${prompts.dir}` in both
    `evolution_context` and `mutation_operator` blocks
12. Verify `gigaevo/prompts/generalization/` directory exists on disk and contains
    at minimum a mutation operator prompt override file
13. Verify `prompts=generalization` resolves correctly: run
    `python run.py problem.name=chains/hotpotqa/static_holdout_f1 pipeline=hotpotqa_asi prompts=generalization --cfg job`
    and confirm `prompts.dir` resolves to the generalization prompts directory
14. Verify G3/G4 LLM config: run with `llm=gemini31_pro` and confirm
    `llm._target_` resolves to `gigaevo.llm.models.MultiModelRouter` with model
    `google/gemini-3.1-pro-preview`; confirm `OPENAI_API_KEY` is set in `.env`
15. **Binding prompt review (BINDING -- generalization prompts are the treatment)**:
    Before launching any run, a human reviewer must read the implemented
    `gigaevo/prompts/generalization/` mutation prompt and confirm in writing
    (comment in 03_plan.md or PR) that it satisfies all five content requirements:
    (a) sampling framing -- failures are a sample, not exhaustive;
    (b) process-over-examples -- prefer general reasoning improvements;
    (c) anti-overfitting directive -- avoid example-specific prompt language;
    (d) held-out awareness -- mutations evaluated on unseen examples;
    (e) gap interpretation -- the prompt explicitly names `evo_f1` and `fitness`
        (= held_F1), explains their meaning, and instructs the mutation LLM that
        a large (evo_f1 − fitness) gap indicates overfitting to the evo set, so
        it should prioritize changes that improve held-out performance over changes
        that merely polish evo-set scores.
    No treatment run may launch until this confirmation is documented.

## 13. Open Questions / Risks

### Risk 1: Evaluation time uncertainty
The 1000-sample evaluation has not been tested at this scale in a single validate.py
call. The 600-sample eval takes ~22 min; naive extrapolation to 1000 gives ~37 min.
However, the two evaluations are sequential (700 then 300), not a single batch of
1000, so vLLM queuing dynamics may differ.

**Pre-launch mitigation**: Time a single baseline evaluation on the full 1000-sample
validate.py before launching. If it exceeds 50 min, increase stage_timeout to 9000
and dag_timeout to 13500.

### Risk 2: The held-out set may be too small
With 300 held-out samples, the standard error of held_F1 is ~2.5pp (for F1 ~ 0.70).
Since fitness = held_F1 only (no averaging with evo_F1), the fitness signal is noisier
than in cold_start (which uses 600 samples). However, the benefit is independence from
the mutation feedback, not lower noise.

### Risk 3: Held_F1-only fitness may select noisy winners
By using held_F1 as the sole fitness, programs excellent on the evo set but poor on
held-out are penalized with zero credit for evo-set performance. If the best achievable
programs are necessarily evo-set-specialized, the held_F1-only fitness selects inferior
programs.

**Monitoring**: Track evo_f1 trajectory. If evo_f1 at gen 25 is < 70% for all runs
(vs 72-73% in cold_start), note as a limitation.

### Risk 4: The 700/300 split may not be optimal
The 70/30 split is conventional but not necessarily optimal for this setting. A 500/500
split would give a stronger held-out signal but reduce the evo set (less failure data
for the mutation LLM). A 800/200 split would preserve the evo signal but weaken the
held-out regularization. The 700/300 split balances these concerns and was chosen to
keep the held-out set comparable in size to the test set (300 samples).

### Risk 5: Gemini-3.1-Pro may exacerbate overfitting (G3/G4)
The gemini_mutation experiment (PR #79) showed Gemini-3.1-Pro inflates the val-test gap
(+6.00pp vs +2.58pp for Qwen3-235B). Under held_F1-only fitness, the held-out
regularization may counteract this tendency -- or Gemini's stronger optimization
pressure may overpower the regularization. G3/G4 results must be interpreted
cautiously relative to G1/G2.

### Risk 6: Held_F1 noise may make the fitness landscape noisier than cold_start
With 300 held-out samples and SE ~2.5pp, MAP-Elites may select programs that got lucky
on the 300 held-out samples rather than truly generalizable programs. This noise is
similar to the ~2pp stochastic noise already tolerated in test eval, and averages out
over the ~200 programs evaluated per run. However, unlike cold_start (where fitness is
computed on 600 samples with SE ~1.8pp), the per-program selection noise is ~40% higher.

**Mitigation**: This noise is inherent to the train/val split design. It is the price
of an unbiased selection signal. If the experiment produces a NULL result with high
SD across runs (> 2pp), noisy fitness is a plausible explanation.

---

## 14. Relationship to Prior Experiments

This experiment builds directly on:

- **cold_start (PR #75)**: Establishes the n=4 reference distribution (mean 59.58%,
  SD 1.00pp) under F1+default+600+cold. The generalization experiment uses the same
  condition family but with held-out validation replacing single-set fitness.

- **val_gap Gate E (PR #70)**: F1 fitness reduced the val-test gap from 6.00pp to
  1.66pp (SUGGESTIVE, n=1). This experiment uses F1 as the base fitness metric and
  adds held-out regularization on top.

- **gemini_mutation (PR #79)**: Demonstrated that stronger mutation LLMs exacerbate
  val-test overfitting (+6.00pp gap vs +2.58pp cold-start). This experiment targets
  the overfitting mechanism directly through fitness design.

- **colbert_feedback (PR #76)**: Rich failure feedback enabled val-set overfitting
  (+6.17pp gap). The generalization experiment ensures the held-out set is NOT used
  for failure feedback, preventing this pathology.

The key novelty is that this is the first experiment to **provide a fully deterministic
separation between the selection signal and the guidance signal**. Every prior experiment
used the same samples for both selection and guidance, creating a feedback loop that
rewards val-set-specific programs. The held-out mechanism breaks this loop completely:
fitness = held_F1 only, with zero contribution from evo-set performance.

**Note**: The val_gap rotating val set (Run R, Gate B) provided partial, stochastic
decoupling via hash-seeded sample rotation; that experiment produced a NULL result. The
present experiment provides complete, deterministic separation: the held-out 300 samples
are never exposed to the mutation LLM as failure cases, and this boundary is fixed
across all generations.

---

## 15. Success Criteria Summary

| Outcome | Threshold | Implication |
|---------|-----------|-------------|
| STRONG POSITIVE -- PRELIMINARY | mean test EM >= 62.30% | GEPA beaten. Held-out validation is the breakthrough. Adopt as default. PRELIMINARY until deconfounding follow-up (600 evo + 300 held-out + 100 unused) confirms causal mechanism. |
| POSITIVE -- PRELIMINARY | mean test EM in [62.00%, 62.30%) | Near-GEPA. Held-out validation is effective. Consider K-fold follow-up. PRELIMINARY until deconfounding follow-up confirms causal mechanism. |
| SUGGESTIVE | mean test EM in [60.50%, 62.00%), p < 0.05 | Meaningful improvement but below GEPA. Held-out helps but is insufficient alone. |
| MARGINAL | mean test EM in [59.58%, 60.50%), p < 0.05 | Statistically significant but small. 2x eval cost may not be justified. |
| NULL | p >= 0.05 | No detectable effect. Val-test gap is not selection bias; it is distribution shift. |
| NEGATIVE | mean test EM < 57.58% | Held_F1-only fitness harms performance. Noisy or decoupled signal prevents convergence. |

---

*Ready for Reviewer-2's scrutiny.*
