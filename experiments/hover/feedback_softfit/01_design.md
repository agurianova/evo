# Experimental Design: HoVer Feedback + Soft Fitness -- Disentangling Two Mutation Signal Deficits

**Date**: 2026-03-20
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft -- awaiting Reviewer-2

---

## 1. Research Question

The HoVer baseline experiment (PR #90) established that GigaEvo cold-start reaches a mean
test retrieval coverage of approximately 51.87% (H1-H3), which is at parity with the GEPA
benchmark of 52.33% -- not above it. Two runs (H1, H4) plateaued at 50% validation coverage
from generation 3 onward, showing zero improvement over 22 generations. The baseline
experiment's design document pre-identified two leading explanatory candidates for poor
convergence: (1) **absent failure feedback** -- the mutation LLM sees fitness numbers but
no structured analysis of why programs fail (which gold documents were missed, which hop's
retrieval was inadequate), and (2) **discrete fitness** -- the 0/1 per-sample scoring (all
3 gold docs found or nothing) provides coarse gradient signal that may not distinguish
"almost correct" (2/3 gold docs found) from "completely wrong" (0/3 gold docs found).

These two deficits are partially confounded in the baseline: both contribute to reduced
mutation guidance, and a NULL result cannot distinguish which is the binding constraint.
This experiment disentangles them.

**Primary research question**: Does structured per-hop failure feedback, soft (fractional)
fitness scoring, or their combination increase test retrieval coverage beyond the baseline
mean of ~51.87%?

**Secondary research question**: Which deficit is binding -- absent feedback, discrete
fitness, or both? The 2x2 factorial design allows estimating main effects and their
interaction.

---

## 2. Hypotheses

### Primary hypothesis: at least one treatment improves test coverage

**H0**: None of the three treatment conditions (feedback-only, soft-fitness-only,
feedback+soft-fitness) produces a mean test retrieval coverage that exceeds the baseline
mean by more than 2.0pp (the noise floor estimated from baseline inter-run SD).

**H1**: At least one treatment condition produces a mean test retrieval coverage that
exceeds the baseline mean by more than 2.0pp, indicating that the addressed deficit was
indeed a binding constraint on evolutionary performance.

### Directional sub-hypotheses (pre-registered, exploratory)

**H1a (Feedback)**: Structured per-hop failure feedback increases test coverage relative
to the no-feedback control, holding fitness metric constant. The mutation LLM's ability to
see *which* gold documents were missed and at *which hop* enables targeted prompt
improvements that blind mutation cannot achieve.

**H1b (Soft fitness)**: Fractional retrieval coverage (e.g., 2/3 = 0.667 instead of 0)
increases test coverage relative to discrete fitness, holding feedback constant. Finer
fitness resolution allows the evolutionary archive to retain "almost correct" programs
that discrete scoring would discard.

**H1c (Interaction)**: Feedback and soft fitness are complementary -- their combination
exceeds either treatment alone. Feedback tells the mutation LLM *what* to fix; soft
fitness rewards partial progress. Without soft fitness, even well-targeted mutations that
recover 1 of 3 missing docs register no fitness improvement.

### Effect size thresholds

We define treatment effects relative to the baseline mean (~51.87% from H1-H3; will be
updated with H4 data when available).

| Treatment mean - baseline mean | Verdict |
|-------------------------------|---------|
| >= +5.0pp | **STRONG POSITIVE** -- treatment substantially improves retrieval coverage |
| [+2.0pp, +5.0pp) | **POSITIVE** -- treatment reliably improves coverage beyond noise floor |
| (0pp, +2.0pp) | **SUGGESTIVE** -- directionally positive but within noise floor |
| <= 0pp | **NULL** -- treatment does not improve coverage |

**Important**: The primary test metric remains **discrete retrieval coverage** (all 3 gold
docs found = 1, else 0) on the 300-sample held-out test set. This ensures direct
comparability with the baseline and GEPA benchmark. Soft fitness changes the *evolutionary
selection signal* only -- test evaluation uses the same discrete metric for all conditions.

---

## 3. Independent Variables

| Variable | Levels | Values |
|----------|--------|--------|
| **Failure feedback** | 2 | `none` (baseline: FormatterStage receives None, mutation LLM sees only fitness numbers) vs. `structured` (per-hop failure analysis: which gold docs missed, at which hop, what queries were generated) |
| **Fitness metric** | 2 | `discrete` (baseline: 0/1 per sample, all 3 gold docs or nothing) vs. `soft` (fractional: gold_found / 3 per sample, e.g., 2/3 = 0.667) |

This is a **2x2 factorial design** with 4 cells.

### Why 2x2 factorial instead of the proposed 2-condition design

The researcher's original proposal (Condition A: feedback, Condition B: soft fitness)
confounds the two treatments: we could not determine whether an effect is due to feedback,
soft fitness, or their interaction. The 2x2 factorial costs the same 4 runs but provides
orthogonal estimates of both main effects plus their interaction. The baseline experiment's
4 runs serve as the control cell (no feedback, discrete fitness), eliminating the need for
new control runs.

| Cell | Feedback | Fitness | Runs | Source |
|------|----------|---------|------|--------|
| A (Control) | none | discrete | H1-H4 | Baseline experiment (PR #90) -- already complete |
| B | **structured** | discrete | F1, F2 | New -- this experiment |
| C | none | **soft** | F3, F4 | New -- this experiment |
| D | **structured** | **soft** | (none) | Deferred -- see justification below |

### Why cell D is deferred (3 cells, not 4)

With only 4 available endpoints, we face a choice: run all 4 cells at n=1 each, or run
3 cells at n=2 for treatments (with n=4 from baseline as control). The n=1 design is
scientifically unacceptable -- it provides no within-cell variance estimate and makes the
factorial interaction term unestimable. The n=2 design for B and C, combined with n=4
from baseline for cell A, allows:

1. Two-sample t-tests of each treatment against the baseline mean (underpowered but
   directionally informative)
2. A pooled comparison of "any feedback" (B) vs. "no feedback" (A+C) and "soft fitness"
   (C) vs. "discrete fitness" (A+B)
3. Decision-gating for cell D: if BOTH B and C show positive effects, cell D (the
   interaction) becomes the highest-priority follow-up. If only one shows an effect, cell D
   adds less scientific value than replicating the effective treatment at higher N.

This is a **decision-stage experiment**: its purpose is to identify which treatment(s)
merit further investment, not to produce a definitive factorial analysis.

---

## 4. Dependent Variables

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test retrieval coverage at gen 25 (best-by-val, discrete) | 300-sample held-out test set; discrete coverage scoring (all 3 gold docs = 1, else 0); thinking mode Qwen3-8B; 5 repeats per run | **YES -- primary** |
| Val coverage trajectory (gen 0-25) | Per-generation `valid_frontier_fitness` from Redis | YES -- convergence diagnostic |
| Val-test gap | Best val coverage minus mean test coverage | YES -- overfitting diagnostic |
| Birth-generation of best-by-val program | From Redis trajectory | NO -- convergence speed |
| Within-run test variance (5-repeat SD) | SD of 5 test evaluations for each run | NO -- LLM stochasticity diagnostic |

**Primary metric**: Mean test retrieval coverage (discrete, 5-repeat average per run) at
gen 25 for each treatment condition, compared against baseline mean.

**Test protocol**: 5 independent repeats of the full 300-sample test evaluation per run,
identical to the baseline protocol. This is essential because the baseline showed
within-run SD of 0.69-2.01pp. The 5-repeat mean is the per-run estimate.

**Critical**: All conditions use **discrete** test coverage for the primary metric,
including cell C (soft fitness). Cell C changes the evolutionary fitness signal only --
the test metric must remain comparable across all conditions and to GEPA.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Chain topology | 7-step fixed (3 tool, 4 LLM) | HoVer static mode; identical to baseline |
| **Test metric** | **Discrete retrieval coverage** (all 3 gold docs = 1, else 0) | Comparable to baseline and GEPA; NOT changed by soft fitness treatment |
| Validation sample size | 300 (first 300 train samples) | Default; identical to baseline |
| `problem.name` | `chains/hover/static` (cells A, B) / `chains/hover/static_soft` (cells C) | See Section 6 notes |
| `prompts` | `default` | No HoVer-specific prompts; identical to baseline |
| Chain LLM | Qwen3-8B, thinking mode ON, max_tokens=32768 | Required for GEPA comparison |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507, one server per run | Identical to baseline |
| **`model_name`** | **`Qwen3-235B-A22B-Thinking-2507`** (explicit override) | Default is `deepseek/deepseek-v3.2` on OpenRouter -- MUST override. Identical for all 4 runs. |
| **`llm_base_url`** | Per-run mutation LLM URL (see Run Design Table) | Explicit override required; default routes to OpenRouter. Each run gets a dedicated mutation server. |
| `num_parents` | **1** (explicit override; default is 2) | Single-parent mutation; identical to baseline |
| `max_elites_per_generation` | **8** (explicit override; default is 5) | Identical to baseline |
| `max_mutations_per_generation` | 8 | With num_parents=1, max_elites=8: C(8,1)=8 |
| `stage_timeout` | **3000** (explicit override) | Identical to baseline |
| `dag_timeout` | **7200** (explicit override) | Identical to baseline |
| `max_generations` | 25 | Identical to baseline |
| Seed initialization | **Cold start** (no `program_loader.problem_dir`) | Identical to baseline |
| `mutation_mode` | `rewrite` | Default |
| HTTP timeout | 600s | Consistent with baseline |
| BM25 retrieval k | 7 (hops 1-2), 10 (hop 3) | Frozen in chain topology |

---

## 6. Run Design Table

| Run | Label | Cell | Feedback | Fitness | `redis.db` | `pipeline` | `model_name` | Chain LLM URL | Mutation LLM URL (`llm_base_url`) |
|-----|-------|------|----------|---------|-----------|-----------|-------------|---------------|-----------------------------------|
| F1 | hover-fb-1 | B | **structured** | discrete | 9 | **`hover_feedback`** | Qwen3-235B-A22B-Thinking-2507 | `http://10.226.17.25:8001/v1` | `http://10.226.72.211:8777/v1` |
| F2 | hover-fb-2 | B | **structured** | discrete | 10 | **`hover_feedback`** | Qwen3-235B-A22B-Thinking-2507 | `http://10.225.185.235:8001/v1` | `http://10.226.15.38:8777/v1` |
| F3 | hover-soft-1 | C | none | **soft** | 11 | `standard` | Qwen3-235B-A22B-Thinking-2507 | `http://10.226.17.25:8000/v1` | `http://10.226.185.47:8777/v1` |
| F4 | hover-soft-2 | C | none | **soft** | 12 | `standard` | Qwen3-235B-A22B-Thinking-2507 | `http://10.225.185.235:8000/v1` | `http://10.225.51.251:8777/v1` |

**Run naming convention**: F-prefix for "Feedback/Fitness" experiment.

**Bold values** differ from baseline and require explicit implementation/overrides.

**Baseline (Cell A, n=4)**: Runs H1-H4 from PR #90 -- already complete. Test coverage
means: H1=51.20%, H2=52.47%, H3=51.93%, H4=TBD. These serve as the control condition.
No new baseline runs are needed.

### Implementation requirements per cell

#### Cell B (F1, F2): Structured failure feedback, discrete fitness

**Code changes required**:

1. **`validate.py` modification**: The existing `chains/hover/static/validate.py` will
   be modified **in place** to return `(metrics_dict, failures_list)` instead of
   `metrics_dict`. The failures list contains per-sample failure details: which gold
   titles were missed, at which hop, and what queries were generated. This follows the
   exact pattern established by HotpotQA's `static_a/validate.py` (lines 150-176).

   **Impact analysis of the in-place modification**:
   - **(a) Cell A (baseline, historical)**: Not affected. H1-H4 data was collected with
     the original dict-returning validate.py and is already archived. The modification
     occurs after baseline archival.
   - **(b) Cell C (soft fitness)**: Not affected. Cell C uses `problem.name=chains/hover/static_soft`,
     which has its own independent `validate.py` returning a plain dict.
   - **(c) Infrastructure side-effect**: After this modification, any future run that uses
     `pipeline=standard` with `problem.name=chains/hover/static` will have
     `FetchArtifact` return the failures list (not `None`). The default `FormatterStage`
     will call `format_value()` on this list, producing a `repr()` string in the
     mutation context -- i.e., **repr-contamination**, the same failure mode documented
     in PR #67 (HotpotQA). Future `pipeline=standard` runs on `chains/hover/static`
     must either (i) use `pipeline=hover_feedback` to get properly formatted feedback,
     or (ii) be aware that the mutation context will contain raw repr output. This
     side-effect is acceptable because no future experiment should use `pipeline=standard`
     on this problem variant without explicitly choosing a feedback strategy.

2. **`HoVerFeedbackFormatter` class**: A `FormatterStage` subclass (analogous to
   `HotpotQAASIFormatter` in `problems/chains/hotpotqa/static_a/formatter.py`) that
   renders failure cases into structured markdown for the mutation LLM. Key fields:
   - Claim text
   - Gold supporting documents (titles)
   - Per-hop retrieval results: which gold docs found/missing at each of 3 hops
   - Queries generated at each hop
   - Random sample of 10 failures per generation (non-cacheable)

3. **`HoVerFeedbackPipelineBuilder` class**: Extends `DefaultPipelineBuilder` by calling
   `replace_stage("FormatterStage", HoVerFeedbackFormatter)` -- identical pattern to
   `ASIPipelineBuilder` in `problems/chains/hotpotqa/static_a/pipeline.py`.

4. **`config/pipeline/hover_feedback.yaml`**: Pipeline config pointing to the new builder.

**Fitness metric**: Unchanged (discrete). The `validate.py` change adds failure details
as an artifact but does NOT change the fitness calculation.

#### Cell C (F3, F4): Soft (fractional) fitness, no feedback

**Code changes required**:

1. **New problem variant `chains/hover/static_soft/`**: Copy of `chains/hover/static/`
   with a modified `validate.py` that computes fractional retrieval coverage:
   ```python
   # Instead of: scores.append(discrete_retrieval_eval(gold_titles, found_titles))
   # Use:        scores.append(len(normalized_gold & found_titles) / len(normalized_gold))
   ```
   This gives 0.0, 0.333, 0.667, or 1.0 per sample (0/3, 1/3, 2/3, 3/3 gold docs found).

2. **Updated `metrics.yaml`**: The fitness metric description should note fractional
   scoring. The `significant_change` can remain at 0.01 (the minimum detectable change
   is 1/(3*300) = 0.0011 for one sample improving by one doc).

3. **Pipeline**: `standard` (same as baseline). No failure feedback -- validate.py returns
   a plain dict, FetchArtifact gets None, FormatterStage skips.

**Critical**: The `test.py` evaluation MUST use **discrete** scoring for the primary
metric, regardless of what fitness metric the evolutionary loop uses. The test script
calls `discrete_retrieval_eval` which is unchanged. Soft fitness affects evolution only.

### Chain LLM and Mutation LLM assignments

| Run | Cell | Chain LLM server | Mutation LLM server |
|-----|------|------------------|---------------------|
| F1 | B (feedback) | 10.226.17.25:8001 (host A) | 10.226.72.211 |
| F2 | B (feedback) | 10.225.185.235:8001 (host B) | 10.226.15.38 |
| F3 | C (soft) | 10.226.17.25:8000 (host A) | 10.226.185.47 |
| F4 | C (soft) | 10.225.185.235:8000 (host B) | 10.225.51.251 |

**Shuffled host assignment** (adopted per Reviewer-2 recommendation): Each treatment
cell has one run on host A and one on host B, eliminating the host-treatment confound.
The baseline showed <1.3pp host effect (H1/H2 on host A vs H3/H4 on host B), which is
within noise but is 65% of the +2.0pp POSITIVE threshold. Shuffling removes this
confound at zero cost.

### Redis DB assignments

DBs 9-12 (same as baseline). Must be flushed after baseline data is archived.

**Pre-launch**: Archive baseline runs using `tools/experiment/archive_run.sh`, then flush DBs 9-12
via `tools/flush.py --db 9 10 11 12`.

### Combinatorics verification

| Run | num_parents | max_elites | Parent combos | max_mutations | Actual mut/gen |
|-----|:-----------:|:---------:|:-------------:|:-------------:|:--------------:|
| F1 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| F2 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| F3 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| F4 | 1 | 8 | C(8,1) = 8 | 8 | 8 |

---

## 7. Sample Size Justification

### Within this experiment: n=2 per treatment cell

With n=2 per cell, we cannot compute meaningful within-cell variance or individual
cell-level p-values. This is a known and accepted limitation.

**What n=2 per cell enables**:

1. **Direction check**: If both F1 and F2 (feedback) exceed all 4 baseline runs, or both
   F3 and F4 (soft fitness) exceed all 4 baseline runs, this is strong directional
   evidence even without formal significance.

2. **Two-sample t-test (exploratory, very low power)**: Treatment (n=2) vs. baseline
   (n=4), Welch's t-test with Satterthwaite df. At SD=2pp (baseline SD estimate), the
   MDE for a two-sample t with n1=2, n2=4 at alpha=0.05 (one-sided) and 80% power is
   approximately 5.2pp. This means we can only detect large effects.

3. **Pooled comparison (higher power)**: Feedback main effect = mean(B) vs. mean(A+C);
   Soft fitness main effect = mean(C) vs. mean(A+B). With n_feedback=2 vs. n_no_feedback=6,
   and n_soft=2 vs. n_discrete=6, power improves modestly.

### Combined with baseline: n=4 (control) + n=2 (each treatment)

The key statistical comparison is treatment-vs-control with the baseline providing the
control. With baseline n=4 and treatment n=2, the pooled MDE at SD=2pp is:

    MDE = t(alpha,df) * SD * sqrt(1/n1 + 1/n2) = t(0.95,df=4) * 2 * sqrt(1/4 + 1/2)
        = 2.132 * 2 * 0.866 = 3.69pp

At SD=1pp (optimistic, near baseline H2's tight within-run variance):

    MDE = 2.132 * 1 * 0.866 = 1.85pp

**Conclusion**: With n=2 treatment + n=4 control, we can detect a ~3.7pp improvement at
SD=2pp (80% power, one-sided alpha=0.05). The POSITIVE threshold of +2.0pp is below this
MDE, meaning marginal improvements will not reach significance. Effects of +5.0pp (STRONG
POSITIVE) are detectable. This power limitation is acceptable for a decision-stage
experiment whose purpose is to identify promising directions, not to produce definitive
significance.

### Why not n=4 per treatment?

We have 4 endpoints. Running n=4 for one treatment means 0 for the other. The 2x2 design
with n=2 per treatment tests both hypotheses simultaneously, which is more valuable for
decision-gating than testing one hypothesis conclusively.

### Follow-up design (pre-committed)

If either treatment shows a positive effect (mean >= baseline + 2.0pp, regardless of
significance), the follow-up experiment will:
- Run n=4 of that treatment (full replication)
- Run n=2 of cell D (feedback + soft fitness) if both B and C are positive
- This provides the statistical power the current experiment lacks

---

## 8. Statistical Test

### Test 1: Treatment vs. baseline (primary, per-cell)

**For each treatment cell (B, C)**:

**Comparison**: Mean test retrieval coverage of treatment runs (n=2) vs. baseline mean
(n=4, from H1-H4).

**Test**: Welch's two-sample t-test, one-sided (H1: treatment_mean > baseline_mean).

**Statistic**: t = (treatment_mean - baseline_mean) / sqrt(s_treatment^2/n_treatment + s_baseline^2/n_baseline)

**Degrees of freedom**: Satterthwaite approximation.

**Significance**: alpha = 0.05 (one-sided). Given n=2 per treatment, p-values are
informative but underpowered. The primary decision criterion is the effect-size table
in Section 2, not p < 0.05. Two primary one-sided tests (cell B vs. baseline, cell C
vs. baseline) yield a family-wise error rate of approximately 0.0975 under the global
null. Formal Bonferroni correction is not applied because the experiment is
decision-stage with low power, and inflating the alpha threshold further would render
the tests unable to detect even large effects.

**Note on baseline SD**: With n=2 per treatment cell, the within-cell SD estimate has
only df=1, which is extremely unreliable. The baseline SD (from n=4) is the more
trustworthy variance estimate. If treatment SD is implausibly different from baseline
SD (>3x), report but do not use the pooled estimate.

### Test 2: Factorial main effects (exploratory)

**Feedback main effect**: mean(F1, F2) - mean(F3, F4, H1, H2, H3, H4)
(feedback_yes vs. feedback_no, ignoring fitness metric)

**Soft fitness main effect**: mean(F3, F4) - mean(F1, F2, H1, H2, H3, H4)
(soft_yes vs. soft_no, ignoring feedback)

These are exploratory because the cells are not balanced (n=4 control, n=2 per treatment,
n=0 for the interaction cell D). Report effect sizes and 95% CIs but do not gate
conclusions on p-values. **Caveat**: The pooled "no feedback" reference (cell A + cell C)
includes cell C, which has soft fitness. If soft fitness itself affects coverage, the
pooled "no feedback" mean is biased -- inflated if soft fitness helps, deflated if it
hurts. This is inherent to the partial factorial design and does not invalidate the
exploratory analysis, but the feedback main-effect estimate should be interpreted with
this caveat.

### Test 3: Convergence speed comparison (secondary)

**Metric**: Generation at which val coverage first exceeds 45% (or 50%, whichever baseline
median was).

**Comparison**: Treatment runs vs. baseline runs, descriptive (median, range).

If soft fitness enables faster convergence (because partial credit provides a gradient
from gen 0), this will be visible as earlier first-crossing times.

### Test 4: Per-run test evaluation (5-repeat protocol)

Each run's test coverage is the mean of 5 independent evaluations on the 300-sample test
set. Report per-repeat scores and within-run SD for each of the 4 new runs. Compare
within-run SD across conditions to assess whether treatment affects LLM stochasticity.

**Significance threshold**: alpha = 0.05 (one-sided for primary comparisons)
**How computed**: scipy.stats.ttest_ind (Welch's), with bootstrapped CI as sensitivity
check (10,000 resamples of per-run means).

---

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| **Host-treatment confound** | If both runs in a treatment cell share one chain host, host-level differences confound with treatment. | MITIGATED. Shuffled host assignment adopted: F1=host A, F2=host B, F3=host A, F4=host B. Each treatment cell has one run on each host, eliminating the confound. Report host-stratified means in Phase 5. |
| **Unbalanced factorial** | Cell D (feedback + soft) is empty. Cannot estimate interaction. | Accepted. This is a decision-stage experiment. Cell D is pre-committed as follow-up if both B and C show effects. The 3-cell design is more informative than a balanced 4-cell at n=1. |
| **Baseline as historical control** | Baseline runs (H1-H4) were conducted at a different time under potentially different server loads. | LOW RISK. All servers are dedicated. No other experiments running on these endpoints. Chain LLM and mutation LLM deployments are unchanged. Verify model versions at launch. |
| **Two code changes per condition** | Cell B requires validate.py change (failure return) + new formatter + new pipeline. If any code change introduces a bug, cell B is invalidated. | Write unit tests for the formatter and validate.py changes before launch. Verify that cell B's validate.py produces identical fitness values to baseline (the metrics dict is unchanged; only the artifact tuple element is new). |
| **Soft fitness changes the archive composition** | Under soft fitness, programs scoring 0.667 (2/3 docs) survive in the archive, whereas under discrete fitness they score 0 and are eliminated. This changes which programs are mutated, not just how they are scored. | This is the intended mechanism, not a confound. Document the archive composition at gen 5, 15, 25 for all cells. |
| **Val-test gap under soft fitness** | Soft fitness may show a different val-test gap because the val metric (soft) differs from the test metric (discrete). Val coverage numbers across cells are NOT directly comparable during evolution. | Report val coverage in both soft and discrete metrics for cell C runs. The primary comparison is always discrete test coverage. |
| **Cold start variability** | Baseline showed high inter-run variance (50.0-55.0% val). With n=2, one unlucky run could mask a treatment effect. | The 5-repeat test protocol reduces per-run noise. Report per-run test means with CIs. If one treatment run appears anomalous (>2 SD below baseline mean), flag but do not exclude unless invalidation criteria are met. |
| **Discrete fitness metric in metrics.yaml** | Cell C (soft fitness) uses a different `metrics.yaml` with fractional fitness. The `significant_change` field affects archive behavior. | Set `significant_change: 0.003` for soft fitness (approximately 1 sample improving by 1 doc: 1/(3*300) = 0.0011, rounded up). Baseline uses `significant_change: 0.01`. Both are small enough that any real improvement registers. |
| **Formatter overhead** | Cell B's formatter processes ~150+ failure cases per generation and renders 10. This adds ~0.1s per generation -- negligible vs. the ~15-25 min gen time. | No mitigation needed. Confirm in post-hoc timing analysis. |
| **`pipeline=standard` for soft fitness (cell C)** | Cell C uses `pipeline=standard` because validate.py returns a plain dict (no failure artifact). The mutation LLM still sees no failure feedback. | Correct by design. Cell C tests soft fitness IN ISOLATION from feedback. The interaction (feedback + soft) is cell D (deferred). |

---

## 10. Stop Criteria

### Early termination criteria (per run)

- **Gen-0 val coverage > 20%**: Halt; initialization error. Cold start should produce
  near-0% discrete coverage (or near-0.33 soft fitness). Investigate.
- **Gen-0 val fitness = sentinel value (-1000.0)**: Halt; execution error.
- **Cell B: validate.py returns different fitness than baseline at gen 0**: Halt; the
  feedback change must not alter the metrics dict. Run both validate.py versions on the
  gen-0 program and verify identical fitness.
- **Cell C: gen-0 soft fitness < 0.01**: Pause. If soft fitness is near-0 even with
  fractional credit, the BM25 first-hop is not finding ANY gold docs. Inspect.

### Stagnation-based early completion

If `valid_frontier_fitness` shows no improvement for >= 10 consecutive generations AND
current gen >= 15, the run may be terminated early. This is not an invalidation.

### Run invalidation criteria

A run is excluded from all analyses if any of the following apply:

1. Thinking mode not active: `<think>` blocks absent from >= 5% of chain outputs at gen 1.
2. Invalidity rate > 90% at gen 10.
3. Gen-0 val coverage > 20% (initialization error).
4. `max_elites_per_generation` confirmed at 5 (not 8) in post-hoc inspection.
5. `num_parents` confirmed at 2 (not 1) in post-hoc inspection.
6. `pipeline` mismatch: cell B not using `hover_feedback`, or cell C not using `standard`.
7. Cell B: validate.py fitness differs from baseline validate.py on same program (code bug).
8. Cell C: test evaluation uses soft metric instead of discrete (metric contamination).

If both runs in a treatment cell are invalidated, that cell's hypothesis is UNANSWERABLE.
If one run is invalidated, the remaining run provides a single-point estimate capped at
SUGGESTIVE.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time per run (300-sample, 25 gens) | ~8-12h (same as baseline) |
| Total wall time (4 runs parallel) | ~12h wall-clock |
| Redis DBs | 4 (DBs 9, 10, 11, 12) |
| Mutation LLM servers | 4 (one per run) |
| Chain LLM servers | 4 (one per run) |
| Test eval time | ~5 min/repeat * 5 repeats * 4 runs = ~100 min total |
| New code required | (1) `hover/static_soft/` variant with fractional validate.py, (2) `HoVerFeedbackFormatter` class, (3) `HoVerFeedbackPipelineBuilder` class, (4) `config/pipeline/hover_feedback.yaml`, (5) unit tests for all new code |

---

## 12. Open Questions / Risks

### Priority risks

**Risk 1 -- Soft fitness may not change the archive meaningfully (MEDIUM).**
If most samples are either "all 3 gold docs found" (score 1.0) or "0 gold docs found"
(score 0.0), soft fitness adds no new information. The intermediate states (1/3, 2/3)
must occur with non-trivial frequency for soft fitness to provide a gradient. The baseline
showed ~50% val coverage (discrete), meaning ~150 of 300 samples scored 0. If most of
those 150 also scored 0/3 (not 1/3 or 2/3), soft fitness is equivalent to discrete.

**Mitigation**: At gen 0, compute the distribution of per-sample soft scores for the
baseline program: {0/3, 1/3, 2/3, 3/3}. If > 80% of failures are 0/3, soft fitness
provides minimal additional gradient, and this finding itself is scientifically valuable
(it means the BM25 first-hop is the binding constraint, not incremental doc recovery).

**Risk 2 -- Feedback formatter code correctness (MEDIUM).**
The HoVer failure formatter must correctly identify which gold docs were missed at each of
3 hops (not 2 as in HotpotQA). Bugs in title matching or hop indexing could produce
misleading failure analyses that degrade rather than improve mutation quality. The
HotpotQA colbert_feedback experiment (PR #76) demonstrated that rich feedback can cause
*negative* transfer if the information misleads the mutation LLM.

**Mitigation**: Write a focused test that runs the feedback validate.py on the baseline
program and verifies: (a) failure list is non-empty, (b) each failure has all required
fields, (c) gold titles match known ground truth, (d) hop indices are correct (0, 3, 6
for the 3 tool steps). Run this test before launch.

**Risk 3 -- Soft fitness archive contamination for test eval (LOW but critical).**
If the test evaluation script accidentally uses soft scoring instead of discrete, cell C
results are incomparable with baseline and GEPA. The test script (`test.py`) currently
calls `discrete_retrieval_eval` which is unaffected by the soft fitness change in
validate.py. But if the test script is inadvertently modified, this confound is catastrophic.

**Mitigation**: Freeze the existing `test.py` and verify its SHA-256 hash before AND after
the experiment. All test evaluations for all 4 new runs use the SAME `test.py` as the
baseline runs used.

**Risk 4 -- n=2 power deficit (HIGH for significance, acceptable for decision-gating).**
With n=2 per treatment, we have ~80% power to detect a ~5.2pp effect at SD=2pp. Effects
in the +2-4pp range (POSITIVE but not STRONG POSITIVE) will likely not reach significance.
This means a genuinely effective treatment might be classified as SUGGESTIVE rather than
POSITIVE based on p-values alone.

**Mitigation**: Use effect-size thresholds (Section 2) as the primary decision criterion.
Reserve p-values for calibrating confidence. If effect sizes are in the POSITIVE range
(+2-5pp) but p > 0.05, classify as SUGGESTIVE and pre-commit to n=4 replication.

### Scientific open questions after this experiment

| Result pattern | Interpretation | Next experiment |
|---------------|----------------|-----------------|
| B > baseline, C ~ baseline | Failure feedback is binding, fitness granularity is not | n=4 replication of cell B; then test cell D to see if soft fitness adds on top of feedback |
| B ~ baseline, C > baseline | Soft fitness is binding, feedback is not | n=4 replication of cell C; investigate archive composition to understand mechanism |
| B > baseline, C > baseline | Both deficits were binding (independently) | Run cell D (interaction); if D > max(B,C), the combination is synergistic |
| B ~ baseline, C ~ baseline | Neither deficit is binding at current N; the bottleneck is elsewhere (BM25 ceiling? chain topology?) | BM25 ceiling analysis; consider topology mutation (additional hops, different k values) |

---

## Appendix A: Code Verification Required Before Launch

1. **Cell B validate.py correctness**: Run baseline program through both (a) original
   `validate.py` (dict return) and (b) feedback `validate.py` (tuple return). Fitness
   values must be identical. Failure list must be non-empty and well-structured.

2. **Cell B formatter correctness**: Run `HoVerFeedbackFormatter.format_value()` on the
   failure list from step 1. Verify output is well-formatted markdown with per-hop
   retrieval diagnostics for all 3 hops.

3. **Cell B pipeline correctness**: Run `--cfg job` with `pipeline=hover_feedback` and
   verify `pipeline_builder._target_` points to `HoVerFeedbackPipelineBuilder`. Also
   verify `hover_feedback.yaml` wiring: (a) `prompts_dir: ${prompts.dir}` is present in
   both the `evolution_context` and `mutation_operator` blocks (silent failure if missing --
   custom prompts will be ignored), (b) `stage_timeout: ${stage_timeout}` and
   `dag_timeout: ${dag_timeout}` are present in the `pipeline_builder` block (otherwise
   defaults to constants/pipeline.yaml values). Reference pattern: `hotpotqa_asi.yaml`.

4. **Cell C soft validate.py correctness**: Run baseline program through soft validate.py.
   Verify soft fitness >= 0.0 and <= 1.0. Compare against manual calculation on a few
   samples.

5. **Cell C initial program identity**: `chains/hover/static_soft/initial_programs/baseline.py`
   must be byte-for-byte identical (SHA-256 match) to `chains/hover/static/initial_programs/baseline.py`.
   Cold-start initialization must be identical across cells A, B, and C.

6. **Cell C test.py unchanged**: SHA-256 of test.py must match baseline's test.py.
   Test evaluations use discrete scoring regardless of evolutionary fitness metric.

7. **All runs**: `--cfg job` verification of `num_parents: 1`, `max_elites_per_generation: 8`,
   `stage_timeout: 3000`, `dag_timeout: 7200`, `model_name: Qwen3-235B-A22B-Thinking-2507`,
   `llm_base_url` matching the per-run mutation LLM URL from the Run Design Table.

8. **Redis DBs 9-12**: Must show 0 keys after baseline archival.

9. **Gen-0 diagnostic for all 4 runs**: Val coverage < 20% (discrete) / val fitness < 0.20
   (soft).

---

## Appendix B: Decision Tree

```
After gen-25 evaluations for F1-F4 (plus baseline H1-H4 from PR #90):

  Baseline mean (H1-H4): ~51.87% (update with H4 data)
  Cell B mean (F1, F2):  feedback_mean
  Cell C mean (F3, F4):  soft_mean

  For each treatment cell:
    delta = treatment_mean - baseline_mean

                       delta >= +5.0pp?
                      /                \
                    YES                 NO
                     |                   |
              STRONG POSITIVE      delta >= +2.0pp?
              (treatment works;      /            \
               replicate n=4)     YES              NO
                                   |                |
                               POSITIVE          delta > 0?
                               (replicate n=4)   /        \
                                               YES         NO
                                                |           |
                                           SUGGESTIVE     NULL
                                           (replicate     (try
                                            if p<0.10)    cell D
                                                          or new
                                                          direction)

  Decision gate for cell D (feedback + soft fitness):
    - If B=POSITIVE AND C=POSITIVE: run cell D as top priority
    - If B=POSITIVE XOR C=POSITIVE: replicate the positive cell at n=4
    - If B=NULL AND C=NULL: pivot to BM25 ceiling analysis or topology mutation
```

---

## Appendix C: Why Not Warm-Start from Baseline Best?

The researcher asked whether one condition should warm-start from the baseline's best
program. The answer is **no**, for three reasons:

1. **Confound with seed quality**: Warm-starting one condition and cold-starting another
   introduces a confound: any improvement could be due to the better starting point rather
   than the treatment. Both conditions must start from the same initial state.

2. **Archive diversity**: Warm-starting from a single program produces a homogeneous
   initial archive. Cold start allows the archive to develop diversity through early
   generations, which may be important for exploring the fitness landscape.

3. **Comparability with baseline**: The baseline runs were cold-start. Treatment runs must
   also be cold-start for direct comparison. A warm-start treatment that outperforms a
   cold-start baseline tells us nothing about the treatment effect.

If a warm-start experiment is warranted, it should be a separate follow-up with its own
cold-start vs. warm-start factorial (treatment x seed = 2x2).

---

*Ready for Reviewer-2's scrutiny.*
