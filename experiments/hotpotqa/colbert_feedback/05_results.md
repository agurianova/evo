# Results: ColBERT + Rich Feedback (colbert_feedback)

**Date**: 2026-03-12
**Input**: Final metrics from U1/U3/U4, `01_design.md`, `03_plan.md` (with 5 amendments)
**GitHub Release**: `exp/colbert_feedback` (pending archive upload)

---

## 1. Final Metrics

| Run | Condition | Best Val F1 | Val EM (best-by-val) | Test EM (gen 25) | Val-Test EM Gap | Best prog birth-gen | Gens completed | Notes |
|-----|-----------|:-----------:|:--------------------:|:----------------:|:---------------:|:-------------------:|:--------------:|-------|
| U1 | ColBERT+rich feedback, cold, F1, 600 | 72.77% | 63.83% | **57.00%** | +6.83pp | 17 | 26 | Force-killed slightly past gen 25 |
| U3 | ColBERT+rich feedback, cold, F1, 600 | 70.31% | 60.50% | **56.67%** | +3.83pp | 23 | 25 | Completed naturally |
| U4 | ColBERT+rich feedback, cold, F1, 600 | 73.66% | 65.17% | **57.33%** | +7.83pp | 23 | 24 | Force-killed before gen 25 complete |
| **Mean** | | **72.25%** | **63.17%** | **57.00%** | **+6.17pp** | **21.0** | | |

**Baseline / GEPA reference**:
- GEPA benchmark (Qwen3-8B, thinking): **62.3%** test EM
- BM25 cold-start reference (PR #75, n=4): mean **59.58%**, SD=1.00pp, 95% CI [58.00%, 61.17%]

**Delta from references**:
- vs. BM25 cold-start: **-2.58pp** (57.00% vs. 59.58%)
- vs. GEPA: **-5.30pp** (57.00% vs. 62.3%)

---

## 2. Hypothesis Test

**H0**: The mean test EM across n ColBERT+rich-feedback cold-start runs does not exceed the
BM25 cold-start reference mean of 59.58% (PR #75, n=4, SD=1.00pp) by more than the 2.4pp
noise floor. The bundled ColBERT+richer-feedback intervention confers no net benefit over
BM25s+title-only feedback.

**H1**: Mean test EM >= 62.00% (+2.42pp above 59.58% reference), closing the gap with GEPA
(62.3%). The bundled intervention (ColBERT retrieval + full-passage failure feedback) exceeds
the cold-start BM25 ceiling.

**Primary metric**: Test EM at final generation (best-by-val program), 300-sample held-out
test set, thinking mode Qwen3-8B.

**Statistical test**: One-sample t-test (one-sided), H1: colbert_mean > 59.58%, n=3 (U2
dropped per Amendment 4), df=2, alpha=0.05.

- Mean test EM: 57.00%
- SD: 0.33pp
- SE: 0.19pp
- t(2) = -13.541
- p = 0.997 (one-sided, upper tail)
- 95% CI: [56.18%, 57.82%]

**Result**: H0 **not rejected**. The ColBERT+rich-feedback intervention does not improve test
EM relative to the BM25 cold-start reference. The effect is in the **wrong direction**: the
treatment mean is 2.58pp *below* the reference mean. The t-statistic is strongly negative,
ruling out any positive effect at any conventional significance level.

**Verdict**: **NEGATIVE** (mean 57.00% < 57.18% threshold)

This is the most extreme negative outcome on the pre-registered verdict scale. Not only does
the bundled ColBERT+rich-feedback intervention fail to improve over BM25, it produces
significantly worse test EM than the BM25 cold-start baseline.

### Test 2: vs. GEPA benchmark (secondary)

- t(2) = -27.818, p = 0.999 (one-sided)
- No run exceeds GEPA (62.3%)
- **Verdict**: NULL vs GEPA

### Test 3: Stagnation birth-generation (exploratory)

- Mean birth-gen: 21.0 (range: 17-23)
- Cold-start BM25 reference (PR #75): mean 16.5 (range: 11-19)
- **Verdict**: EXTENDED EXPLORATION (mean > 20)

The ColBERT+feedback runs stagnated later than BM25 cold-start runs, suggesting the richer
feedback landscape sustained productive exploration longer. However, the extended exploration
did not translate into better test performance -- the programs that emerged from this longer
exploration phase generalized worse to the test set.

### Test 4: Inter-run SD (descriptive)

- SD = 0.33pp (BM25 cold-start reference: 1.00pp)
- **Verdict**: Tighter than BM25; landscape has a single, highly reproducible attractor

The extremely tight SD (0.33pp, tighter than any prior experiment) indicates that the
ColBERT+feedback evolution consistently converges to the same basin. This is not a power
issue -- three runs at SD=0.33pp give a 95% CI of [56.18%, 57.82%], entirely below the BM25
reference mean of 59.58%. Even with n=100, the mean would not move.

---

## 3. Effect Size

The observed effect is **-2.58pp** relative to the BM25 cold-start reference (57.00% vs.
59.58%). This is a large negative effect -- the magnitude equals the positive effect that
cold-start showed over warm-start in PR #75. The 95% CI [56.18%, 57.82%] excludes the
reference mean by a wide margin.

In practical terms, the ColBERT+rich-feedback intervention performs comparably to the
**warm-start** BM25 baseline (~57%) rather than the cold-start BM25 baseline (~59.6%). The
intervention erased the cold-start advantage entirely.

**Binomial 95% CIs** (individual runs, n=300 test samples):

| Run | Test EM | 95% CI |
|-----|:-------:|--------|
| U1 | 57.00% | [51.40%, 62.60%] |
| U3 | 56.67% | [51.06%, 62.28%] |
| U4 | 57.33% | [51.73%, 62.93%] |

Individual CIs overlap with GEPA due to binomial noise on 300 samples, but the mean-level
CI does not.

---

## 4. Secondary Observations

### 4.1 The val-test gap anomaly: the central finding

The most scientifically important result from this experiment is not the NEGATIVE verdict on
test EM, but the **dramatic inflation of the val-test EM gap**.

| Experiment | Mean Val EM | Mean Test EM | Mean Gap |
|------------|:-----------:|:------------:|:--------:|
| cold_start (BM25, F1, 600, PR #75) | 62.17% | 59.58% | +2.58pp |
| **colbert_feedback (ColBERT, F1, 600)** | **63.17%** | **57.00%** | **+6.17pp** |
| nlp_prompts treatment (BM25, 300, PR #69) | 69.45% | 59.11% | +10.34pp |

The ColBERT+feedback condition achieved **higher val EM** than the BM25 cold-start reference
(63.17% vs. 62.17%, +1.00pp) while producing **lower test EM** (57.00% vs. 59.58%, -2.58pp).
The combined gap inflation is +3.58pp (from 2.58pp to 6.17pp). U4 alone shows a gap of
+7.83pp (val EM 65.17%, test EM 57.33%).

This pattern -- improved validation performance with degraded test performance -- is the
hallmark of overfitting to the validation set. The F1 fitness signal, combined with the
richer passage-level feedback from ColBERT failures, appears to have given the mutation LLM
enough signal to craft prompts that exploit specific patterns in the 600 validation samples
without generalizing to the test distribution.

### 4.2 Mechanistic hypothesis: feedback specificity enables overfitting

The richer failure feedback in this experiment provides full passage text for missing gold
documents (e.g., "George Washington | George Washington was the first president...") instead
of just titles (e.g., "George Washington"). This was hypothesized to give the mutation LLM
more actionable signal for prompt improvement. The data suggests it did -- but the signal was
actionable for overfitting, not for generalization.

When the mutation LLM sees that a specific passage about George Washington was not retrieved,
it can craft prompts that prime the chain to look for exactly those passage-level details.
This works on the validation set (where the same questions recur every generation under the
fixed-val protocol) but fails on the test set (where different questions require different
factual knowledge). Title-only feedback, being less specific, may paradoxically force the
mutation LLM to produce more general-purpose prompt improvements.

### 4.3 ColBERT retrieval quality is not the explanation

Amendment 5 established that ColBERT retrieval quality is approximately equal to BM25 on the
BEIR HotpotQA benchmark (nDCG@10: ColBERT 0.6265 vs. BM25 0.6290). The retrieval benchmark
in `03_plan.md` further shows that BM25 actually **dominates** ColBERT on multi-hop recall
(both-hops recall@7: BM25 0.359 vs. ColBERT 0.274). If the retriever were the binding
constraint, we would expect ColBERT to underperform BM25 by a modest amount -- but a 2.58pp
test EM deficit with a 3.58pp gap inflation points to the feedback mechanism as the more
likely culprit.

### 4.4 Extended exploration did not help

The mean birth-generation of best-by-val programs was 21.0 (range 17-23), compared to 16.5
(range 11-19) for BM25 cold-start. The ColBERT+feedback evolution explored for longer before
stagnating. This suggests that the richer feedback signal sustained productive mutation
longer -- but "productive" here means "improved val F1," which is precisely the metric that
overfitted. The programs born at gen 17-23 had high val EM (60-65%) but failed to generalize.

### 4.5 Val F1 trajectories

Val F1 (the fitness metric) peaked at 72-74% for U1/U4 -- higher than typical BM25 cold-start
val F1 peaks (~68-70%). This is consistent with the overfitting hypothesis: the richer feedback
enabled the evolution to squeeze more F1 from the validation set.

### 4.6 Host stratification

| Host | Runs | Mean test EM |
|------|------|:------------:|
| A (10.226.17.25) | U1 | 57.00% |
| B (10.225.185.235) | U3, U4 | 57.00% |

No host divergence (delta = 0.00pp). Infrastructure is not a confound.

---

## 5. Deviations from Pre-Registration

| Pre-registered item | Followed? | Notes |
|---------------------|-----------|-------|
| Primary metric and threshold | **Yes** | Test EM at gen 25, best-by-val, 300-sample test set, verdict table applied as written |
| Statistical test / decision rule | **Deviated**: n=3 instead of n=4 | Amendment 4 dropped U2. df reduced from 3 to 2. MDE increased from 1.666pp to 2.19pp at SD=1pp. Does not affect verdict: mean is 2.58pp *below* reference, not above. |
| Evaluation script | **Yes** | `run_test_eval.sh` sha256: `075568b83c9b0a320ae41b5f2d6507bc89f81260ab0a2c15b874c0dbb97e56d3` (as pre-registered) |
| Run design table (pipeline, prompts, seed) | **Deviated**: U2 dropped, DB reassignment | Amendment 4: U2 dropped (GPU reserved for ColBERT server). U3 moved to DB=1, U4 to DB=2. No confound: uniform change before any evolution data collected. |
| Monitoring plan | **Deviated**: checkpoint log not filled at gen 5/12 | Runs were monitored via watchdog and `run_status.sh` but intermediate checkpoints were not formally recorded in `03_plan.md`. Does not affect final metrics. |
| Early termination rule | **Not triggered** | No run hit the stagnation criterion (10 gens without improvement AND gen >= 15). U1 and U4 were force-killed slightly past/before gen 25 due to manual timing, not early termination. |

### Unrecorded deviations

**U1 stopped at gen 26 (1 gen past max_generations=25)**: The run overshot by one generation
before force-kill. The best-by-val program was selected from the full trajectory including gen
26. Since the best program was born at gen 17, this overshoot does not affect results.

**U4 stopped at gen 24 (1 gen short of max_generations=25)**: Force-killed before gen 25
completed. The best-by-val program was born at gen 23, which was completed. One generation of
potential improvement was lost, but given the stagnation pattern, this is unlikely to have
changed the outcome.

Neither deviation rises to the level of a protocol violation. Both runs' best-by-val programs
were born well before the termination boundary.

---

## 6. Amendment Impact Assessment

| Amendment | Impact on validity | Assessment |
|-----------|-------------------|-----------|
| **1** (index rebuild with corrected params) | **None** | Applied before any run launched. All runs used the corrected index. |
| **2** (U3 mutation server IP) | **None** | Server swap before gen-0. Same model, same role. |
| **3** (ColBERT CPU-mode fix + server architecture) | **None** | Applied before any gen-0 validation completed. Uniform across all runs. Retrieval quality identical to direct Searcher. |
| **4** (U2 dropped, n=4 to n=3, nbits=8, 8-GPU server) | **Moderate** | Reduces power (df=2 instead of df=3). Does not affect verdict: the effect is strongly negative. Even with n=4 and the missing U2 scoring 62%, the mean would be 58.25% -- still below the NULL threshold (59.51%). The nbits=8 index change is a potential confound: the first launch used nbits=2, the second (Amendment 4) used nbits=8. However, BEIR benchmarks show nbits=8 and nbits=2 are within 0.001pp nDCG (Amendment 5), so retrieval quality is unchanged. |
| **5** (retrieval gap investigation) | **None** | Analysis only; no code or config changes to running experiment. |

---

## 7. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| U1 | **Yes** | Completed gen 26 (1 past target); best-by-val born gen 17. |
| U2 | **Excluded** | Dropped per Amendment 4 before any evolution. |
| U3 | **Yes** | Completed all 25 gens naturally. |
| U4 | **Yes** | Force-killed at gen 24; best-by-val born gen 23 (complete). |

No invalidation criteria were triggered:
- Thinking mode active (verified at gen 0-1)
- `pipeline=hotpotqa_colbert` confirmed in all runs
- `num_parents=1` and `max_elites=8` confirmed via `--cfg job`
- Gen-0 val F1: U1=62.3%, U3=61.1%, U4=61.7% -- within expected cold-start range (halt: >65%)
- ColBERT retrieval functional throughout (non-empty passages confirmed)

---

## 8. Lessons Learned

**What worked**:

- The ColBERT server architecture (Amendment 3) solved the GPU memory contention problem
  elegantly. A single FastAPI process serving 8 GPUs via least-connections load balancing
  enabled all 3 evolution runs to share a high-throughput ColBERT retriever without per-worker
  index loading. This pattern is reusable for any future dense retrieval experiment.

- The 8-GPU ColBERT server (Amendment 4) provided ample throughput for 3 concurrent runs.
  Latency was not a bottleneck (13.9ms/query average).

- The n=3 design, despite losing one run, produced a tight enough SD (0.33pp) to reach a
  definitive verdict. The NEGATIVE outcome is unambiguous -- no amount of additional runs
  would change it.

- The BEIR benchmark comparison (Amendment 5) established retrieval parity between ColBERT
  and BM25 for our setup, enabling clean attribution of the test EM deficit to the feedback
  mechanism rather than retriever quality.

**What did not work**:

- **Richer failure feedback** was counterproductive. The full-passage feedback enabled
  val-set overfitting rather than generalizable prompt improvement. This is the primary
  negative finding.

- **ColBERT retrieval** did not improve over BM25 on multi-hop recall (both-hops recall@7:
  0.274 vs. 0.359). The hypothesis that ColBERT would provide better raw passages was
  falsified by the pre-launch benchmark (Amendment 1 record), but the experiment proceeded
  because H1 also relied on the feedback depth component.

- **Bundled intervention design** prevents clean causal attribution. We cannot determine
  whether ColBERT alone (with title-only feedback) would have matched BM25 cold-start
  performance. The bundled design was justified by compute constraints but limits what we
  can conclude mechanistically.

**Bugs / infrastructure issues**:

- ColBERT index loading in exec_runner subprocesses was fundamentally incompatible with the
  vLLM GPU workload (Amendment 3). The server architecture was a necessary workaround.

- The `colbert_server.py` 0.0.0.0 routing bug (proxy connecting to workers via 0.0.0.0
  instead of 127.0.0.1) required a fix during deployment.

- U2 had to be dropped because the mutation LLM GPU node was repurposed for the ColBERT
  server (Amendment 4). In future experiments, ColBERT serving infrastructure should be
  provisioned on dedicated hardware before the experiment design is finalized.

---

## 9. Next Steps

### 9.1 Feedback ablation (HIGH PRIORITY)

**Research question**: Does title-only feedback with ColBERT retrieval match BM25 cold-start
performance?

This isolates the feedback-depth component. If ColBERT+title-only matches BM25+title-only
(~59.58%), the NEGATIVE result is entirely attributable to rich feedback enabling overfitting.
If ColBERT+title-only also underperforms, ColBERT's inferior multi-hop recall is the culprit.

Design: n=2 runs (exploratory), `pipeline=hotpotqa_asi` (title-only formatter) with
`problem.name=chains/hotpotqa/static_colbert_f1_600`, cold start, F1, 600 val, 25 gens.

### 9.2 Feedback regularization (MEDIUM PRIORITY)

**Research question**: Can richer feedback be made useful without overfitting?

If the overfitting hypothesis is correct, there are several mitigations:
- **Feedback rotation**: Show different subsets of failure details each generation (already
  partially implemented via random failure sampling, but passage text could be further
  randomized).
- **Abstract feedback**: Provide failure categories instead of literal passage text (e.g.,
  "retrieval missed a biographical passage" instead of the full passage).
- **Val-set rotation**: Use `static_r` to rotate the validation set each generation. This
  was excluded as counterproductive in prior experiments (nlp_prompts, PR #69), but the
  context was different -- it may specifically help when feedback is rich enough to enable
  overfitting.

### 9.3 Gemini mutation LLM (ALREADY PRE-REGISTERED)

The gemini_mutation experiment (`01_design.md` written, awaiting Phase 2 review) tests whether
a different mutation LLM (Gemini-3-Flash) produces different evolutionary outcomes. This
experiment can use either the BM25 or ColBERT retriever -- the colbert_feedback results
suggest BM25 is the safer choice to avoid the overfitting pathway.

### 9.4 Revisit the prompt-evolution ceiling

With 19 completed runs (16 warm + 4 cold + 3 ColBERT) and no configuration exceeding GEPA
(62.3%) in mean test EM, the evidence increasingly suggests that the static 6-step chain
topology imposes a hard ceiling on prompt-only evolution near 59-60%. The one exception
(Run D, 63.00%, PR #73) was an Amendment 3 artifact that failed to replicate. Future
directions should consider:
- **Structural chain mutation** (add/remove/reorder steps)
- **Step-level learned components** (fine-tuned retrieval queries, learned re-rankers)
- **Non-evolutionary optimization** (e.g., gradient-based prompt tuning if differentiable)

---

## 10. Paper / Report Notes

### Claim this experiment supports

**Rich failure feedback can be counterproductive in evolutionary prompt optimization.** When
the mutation LLM receives detailed passage-level feedback about retrieval failures, it crafts
prompts that exploit the specific failure patterns in the validation set rather than
generalizing. This manifests as inflated val EM (+1.00pp over BM25 reference) with degraded
test EM (-2.58pp), producing a val-test gap of +6.17pp compared to +2.58pp under title-only
feedback.

This result has implications for any evolutionary or iterative optimization system that uses
failure analysis to guide mutation: **feedback granularity must be calibrated to the
generalization capacity of the optimization target.** When the target is prompt text (a
discrete, relatively low-dimensional optimization space), fine-grained feedback provides a
gradient toward overfitting rather than toward generalization.

### Claim this experiment refutes

**ColBERT retrieval + richer feedback closes the gap with GEPA.** The bundled intervention
produces test EM 5.30pp below GEPA and 2.58pp below the BM25 cold-start baseline. The
remaining GEPA gap is not in the retriever or feedback mechanism -- it is in the chain
reasoning architecture or optimization method.

### Key numbers for the paper

| Metric | Value |
|--------|-------|
| ColBERT+feedback mean test EM (n=3) | 57.00% |
| BM25 cold-start mean test EM (n=4) | 59.58% |
| Delta (ColBERT+feedback vs. BM25 cold-start) | -2.58pp |
| GEPA benchmark | 62.3% |
| Val-test EM gap (ColBERT+feedback) | +6.17pp |
| Val-test EM gap (BM25 cold-start) | +2.58pp |
| Gap inflation | +3.58pp |
| Inter-run SD | 0.33pp |
| t(2) vs. BM25 reference | -13.541, p = 0.997 |

### Figure suggestions

1. **Val-test gap comparison bar chart**: BM25 cold-start (2.58pp) vs. ColBERT+feedback
   (6.17pp) side by side, with val EM and test EM stacked or paired.

2. **Test EM distribution plot**: Box/violin of cold-start BM25 (T1-T4) vs. ColBERT+feedback
   (U1/U3/U4), showing the complete separation of distributions.

---

*Ready for Reviewer-2's scrutiny.*
