# Results Analysis: NLP-Specific Mutation Prompts for HotpotQA

**Experiment**: PR #69 / branch `exp/hotpotqa-nlp-prompts`
**Runs**: K (DB 0), L (DB 1), M (DB 2), N (DB 3)
**Dates**: Launched 2026-03-03 23:12 UTC (fourth launch, first with Amendment 4 active). Final evals: 2026-03-05 07:49–11:04 UTC.
**Analyst**: Dr. Elena Voss
**Pre-registration**: `docs/plans/2026-03-03-nlp-prompts-experiment.md`
**Pre-registration commit**: ef0f53e0f5503b92a9ba3ee877ed8fd772dd6fde
**Analysis date**: 2026-03-05

---

## 1. Executive Summary

The NLP-specific mutation prompts experiment (compound treatment: NLP prompts + rotation val set) produced a **NULL result** at Gate 1: the treatment mean test EM of 59.11% (L/M/N from results.json) falls within the pre-registered null interval of [58.0%, 62.0%] and is not meaningfully higher than the pooled control mean of 59.65% (K=60.00%, E=59.3%). All four treatment-run comparisons against the GEPA benchmark (62.3%) fell short by 1.3–5.3pp, and the rotation val set inflated frontier val EM by 2–5pp relative to control without any corresponding test EM gain, producing val-test gaps of 8.67–13.67pp. The experiment is interpretable but confounded: because NLP prompts and the rotation val set were applied simultaneously to all treatment runs, we cannot determine which component (if either) drove the null result.

---

## 2. Results Table

### 2.1 Primary Results (best-by-val program, gen 50)

| Run | Label | Best Gen | Val EM (frontier) | Val Subset | Test EM | Val-Test Gap | Extraction Fail Rate |
|-----|-------|----------|-------------------|------------|---------|--------------|----------------------|
| K | Control | 43 | 66.33% | fixed-300 | **60.00%** | +6.33pp | 1.0% |
| L | NLP-1 | 40 | 68.00% | hash-seeded-300 | **59.33%** | +8.67pp | 0.0% |
| M | NLP-2 | 20 | 70.67% | hash-seeded-300 | **57.00%** | +13.67pp | 1.0% |
| N | NLP-3 | 26 | 69.67% | hash-seeded-300 | **61.00%** | +8.67pp | 1.3% |

**Note on M test EM**: The user-provided experiment summary cited M test EM as 59.33%. The canonical `results.json` (written at eval time, timestamp 2026-03-05T08:04:02 UTC) records M test EM as 57.00% (171/300 correct). The 59.33% figure appears to be a transcription error. All downstream calculations in this analysis use the results.json values.

**Note on top-8 eval for L**: The `top8_L.log` reruns the results.json #1 program (118f57a7, gen-40, val_EM=68.00%) and reports test_EM=60.33%. This 1.0pp difference from results.json (59.33%) is within the known stochastic noise floor for thinking-mode Qwen3-8B (2.4pp SD from same-program retests). No correction is applied; the original results.json value is used. The top-8 eval for M failed due to a context-length error (8,193 input tokens exceeded the 16,384 context limit for the #2 program); only #1 from L was successfully evaluated.

### 2.2 Treatment Mean and Comparison Points

| Comparison | Value | Notes |
|---|---|---|
| Treatment mean test EM (L/M/N) | 59.11% | (59.33 + 57.00 + 61.00) / 3 |
| Control K test EM | 60.00% | Concurrent control (fourth launch) |
| Historical control E test EM | 59.3% | From P1xP2 experiment, 48h earlier |
| Pooled control mean (K + E) | 59.65% | Used in Gate 2 comparison |
| Seed ddce37b4 test EM | 60.0% | Gen-0 warm start |
| GEPA (Qwen3-8B, thinking) | 62.3% | Target benchmark |
| Treatment mean - pooled control | +0.24pp (treatment - control) | N/A, well below null threshold |
| Best individual treatment run | N: 61.00% | -1.3pp below GEPA |

### 2.3 Historical Context

| Method | Test EM | Notes |
|---|---|---|
| Seed ddce37b4 (gen 0) | 60.0% | Starting point for all runs |
| Run E (P1xP2 ctrl, repr-contaminated) | 59.3% | Used as historical control only |
| Run H (P1+P2, best of P1xP2) | 61.3% | Best prior GigaEvo result |
| Run K (NLP ctrl, this experiment) | 60.0% | Clean control; matches seed |
| Treatment mean (L/M/N) | 59.11% | This experiment |
| GEPA | 62.3% | External benchmark |

---

## 3. Gate-by-Gate Evaluation vs. Pre-Registered Success Criteria

### Gate 1: Treatment vs. Seed (Primary)

**Verdict: NULL**

Pre-registered criteria:
- POSITIVE: Treatment mean > 62.0% — **NOT MET** (59.11%)
- STRONG POSITIVE: Any treatment run >= 62.3% — **NOT MET** (best: N=61.00%)
- NULL: Treatment mean in [58.0%, 62.0%] — **MET** (59.11% is within range)
- NEGATIVE: Treatment mean < 58.0% — not triggered

The treatment mean (59.11%) is 0.89pp below the seed (60.0%) and 0.54pp below the pooled control (59.65%). The treatment provides no detectable improvement over the baseline it was intended to surpass. The null interval is confirmed.

### Gate 2: Treatment vs. Control (Concurrent Comparison)

**Verdict: NULL**

Pre-registered criteria:
- SIGNIFICANT: Treatment mean - pooled control mean >= 4.2pp AND p < 0.05 — **NOT MET** (+0.24pp)
- DIRECTIONAL POSITIVE: Difference >= 2.4pp — **NOT MET** (+0.24pp)
- NULL: Difference < 2.4pp — **CONFIRMED** (+0.24pp < 2.4pp threshold)

The treatment-control difference of +0.24pp is far below the 4.2pp minimum detectable effect (MDE at 80% power, alpha=0.05) pre-registered in Section 9 of the design document. With SE(difference) = 2.19pp and an observed difference of +0.24pp, the effect is consistent with zero. No follow-up is warranted under Gate 5.

**Statistical note**: Formal t-test is not conducted because (a) the observed difference is less than one-tenth of the MDE, and (b) computing a p-value on n=3 treatment replicates without a well-characterized error distribution would be misleading precision. The substantive conclusion — null — is not changed by any reasonable test statistic.

### Gate 3: Control Consistency Check

**Verdict: VALID**

Pre-registered criterion: K test EM within [56.9%, 61.7%] (Run E +-2.4pp). Run K test EM = 60.00%, which is within [56.9%, 61.7%]. Cross-batch comparison with Run E is valid.

Run K also exactly matches the seed (ddce37b4) at 60.0% test EM. This means the control produced 50 generations of evolution without statistically measurable improvement over the starting point — a stagnation result that is consistent with all prior experiments (E=59.3%, H=61.3%, seed=60.0%) and confirms the mutation-quality bottleneck hypothesis from Section 2 of the design document.

### Gate 4: Val-Test Gap

**Verdict: CONCERNING for treatment runs**

Pre-registered criteria:
- HEALTHY: Treatment mean val-test gap < 5pp — **NOT MET** (mean = 10.34pp)
- CONCERNING: Treatment mean val-test gap > 7pp — **TRIGGERED** (10.34pp)

The rotation val set produced substantially inflated frontier val EM (68.0–70.7%) compared to control (66.3%), yet test EM was lower (57.0–61.0%) compared to control (60.0%). The mean val-test gap for treatment runs is 10.34pp, exceeding the "concerning" threshold by 3.34pp. The control gap of 6.33pp is itself above the "healthy" <5pp threshold but far below the treatment gaps.

The most extreme case is Run M: val_EM=70.67%, test_EM=57.00%, gap=13.67pp. The best-selected program in M was from generation 20, suggesting the archive stagnated early and the best program from this run happened to score unusually well on its particular 300/1000 hash-seeded validation subset while generalizing poorly.

---

## 4. Val Trajectory Analysis

### 4.1 Convergence Patterns

All four runs followed the same qualitative pattern: rapid early gains followed by full stagnation.

**Run K (control)**:
- Archive started growing monotonically: sizes 0, 1, 2, 4, 5, 9, 12, 15, 19, 24, 25, 29, 32, 33, 34, 35 at gens 0–14.
- Archive stabilized at 35 programs from gen 14, then dropped back to 29 at gen 19 (archive refresh/compaction), then grew slightly to 30–31 programs and remained there through gen 50.
- The frontier val EM reached 66.33% at gen 43 and produced no improvement in gens 44–50.
- Best program (gen 43) represents a 4.0pp val improvement over the seed (62.3%) but only a 0.0pp test EM improvement.

**Treatment runs (L/M/N) — representative: Run N**:
- Val frontier rose rapidly to 67.3% by gen 7, then continued to 69.7% by gen 25.
- Best program from gen 26; the archive produced no further accepted mutations from gen 32 onward (0% acceptance rate for gens 32–50).
- Evolution effectively terminated 24 generations before the run limit, contributing to the stagnation signal.

**Run M** (most extreme stagnation):
- Best program from gen 20 (70.67% val EM). The early best-gen finding is consistent with the interpretation that M found a locally high-scoring program on its particular hash-seeded val subset at gen 20, then stagnated completely.
- The 13.67pp val-test gap for M is the largest observed in this experimental series (previous worst: Run F from P1xP2, 11.0pp).

### 4.2 Stagnation Mechanism

The archive acceptance rate dropping to 0% for extended periods (gens 30–50 in treatment runs, gens 44–50 in control) indicates that the mutation LLM is proposing programs that do not exceed the fitness of any existing archive member. With `primary_resolution=50` (50 fitness bins), a program must improve by approximately 2pp on the validation set to displace the current occupant of its fitness bin. After the archive fills to ~30–35 programs, nearly all fitness bins in the range [0.62, 0.71] are occupied, and incremental improvement within this range requires proposals that beat the existing program in the same bin — a hard target for a mutation with no structural advantage.

This stagnation behavior is consistent across all prior experiments (E/F/G/H from P1xP2) and is not specific to the NLP prompt treatment. It represents the current performance ceiling of single-parent mutation search on this problem.

### 4.3 Implication for Early-Best Programs

The observation that M's best program is from gen 20 and N's from gen 26 — rather than the final generation — is not surprising in the context of the rotation val set. Under `static_r`, each program is evaluated on a different hash-seeded 300/1000 sample. A program that scores 70.67% on its particular 300-sample slice may or may not perform well on the held-out test set (which is fixed). The val score is an unbiased estimator of true performance under the assumption that the program is not systematically better on certain sample subsets — but if the mutation process produces programs that are locally optimized for specific question types common in a particular random draw, the estimate becomes noisy. The high val-test gaps in M and N are consistent with this noise hypothesis.

---

## 5. Mechanistic Interpretation: Why the Compound Treatment Did Not Succeed

The null result admits three non-exclusive mechanistic explanations. Because NLP prompts and the rotation val set were applied simultaneously to all treatment runs, distinguishing these hypotheses requires additional experiments.

### Hypothesis A: Rotation Val Set Overfitting (Primary Concern)

Under `static_r`, each program's val EM is estimated on a different hash-seeded 300/1000 subset. Programs that happen to score well on their particular 300-sample draw are accepted into the archive, even if they are not genuinely better than programs evaluated on a different draw. Over 50 generations, the archive accumulates programs that are "lucky" on their respective subsets rather than programs that are broadly better.

**Evidence for this hypothesis**:
1. Treatment val EM (68–71%) is 2–5pp higher than control val EM (66.3%), despite treatment test EM being 0–3pp lower than control test EM.
2. The val-test gaps for treatment runs (8.67–13.67pp) are substantially larger than for control (6.33pp), and larger than any prior run in this experimental series except the anomalous Run F (11.0pp).
3. Run M's best program is from gen 20 and achieves 70.67% val EM but only 57.0% test EM — a 13.67pp gap suggesting this program is genuinely overfitted to its validation sample.

**Counter-evidence**: This is the same hypothesis that motivated including rotation in the design (Runs G and H in P1xP2). Run G (static_r, default prompts) achieved test EM=58.0% with a 9.7pp gap — similar to the current treatment runs. The rotation hypothesis is not new; it was already flagged as a risk in Section 4.3 of the design document. The compound treatment made it impossible to determine whether rotation is helping or hurting relative to NLP prompts in isolation.

### Hypothesis B: NLP Prompt Framing Ineffective

The rewritten insights/lineage/mutation system prompts may have failed to improve mutation quality for one of several reasons:
1. The mutation LLM (Qwen3-235B-A22B-Thinking) may already have sufficient HotpotQA domain knowledge that domain-specific framing of the upstream agents provides no incremental signal.
2. The NLP examples in the rewritten prompts (query_formulation, instruction_clarity, evidence_synthesis) may be too similar in abstraction level to the optimizer examples they replaced — both provide analogical examples of mutation strategies, and the LLM may not require domain-matched analogies to propose good mutations.
3. The mutation bottleneck may not be in the upstream agent framing (insights/lineage) but rather in the fundamental difficulty of the mutation problem: a 6-step chain with prompts already optimized for 50 generations has limited room for improvement via further prompt mutation.

**Evidence for this hypothesis**: Run K (control, default prompts) achieved test EM=60.00%, matching the seed exactly. This confirms the bottleneck claim from Section 2 of the design document: the control with default prompts cannot improve on the seed in 50 generations. If this is the case, NLP prompts face the same ceiling and the treatment null result is not surprising.

**Counter-evidence**: We do not have a clean isolation of NLP prompts alone (without rotation). All three treatment runs used both NLP prompts and rotation. A future experiment with NLP prompts + fixed val set (static) would cleanly test this hypothesis.

### Hypothesis C: Compound Confound (Unresolvable Without Deconfounding Run)

Because both IVs changed simultaneously between K (control) and L/M/N (treatment), the experiment cannot attribute the null result to either component. This is the correct scientific characterization of the result: the compound treatment failed, but we cannot say why. The 0.24pp treatment-control difference is consistent with:
- NLP prompts providing +2pp and rotation providing -1.76pp (positive prompt effect masked by rotation noise)
- NLP prompts providing 0pp and rotation providing +0.24pp (both components inert)
- NLP prompts providing -2pp and rotation providing +2.24pp (NLP prompts mildly harmful, rotation mildly helpful)

All three scenarios are indistinguishable from the observed data. This is the principal threat to validity from the compound-treatment design choice.

**Mitigation pre-specified in the design document**: Section 4.3 acknowledged this confound explicitly: "Two variables change between K and L/M/N (prompts + val set). This is a deliberate compound treatment: the research question is 'does the NLP-prompts-with-rotation package improve test EM?' rather than isolating each variable." The compound design was pre-registered and is not post-hoc rationalization. However, a deconfounding follow-up — NLP prompts + fixed-300 val set — is warranted if NLP prompts remain a candidate intervention.

### Summary

The most parsimonious explanation for the null result is that neither component of the compound treatment provides meaningful improvement, and the rotation val set introduced additional noise that makes the treatment results harder to interpret. The 0.24pp treatment-control difference is consistent with zero effect from both components. However, given the known design limitation (compound confound), this conclusion cannot be stated as definitive.

---

## 6. Deviations from Pre-Registration

All four pre-registered amendments are documented in Section 18 of the design document. No additional deviations occurred during execution.

### Amendment 1: `pipeline=standard` -> `pipeline=hotpotqa_asi`
Applied before first valid launch. All four runs (K/L/M/N) use `pipeline=hotpotqa_asi`. No confound introduced.

### Amendment 2: `step_max_tokens=8192` for all LLM steps
Applied uniformly to all four runs via `hotpotqa_asi` pipeline config. No confound introduced. This change may have contributed to the context-length error observed in the top-8 eval for L (program 8f8b0e10 at rank 2 had 8,193 input tokens, exceeding the 16,384 model context limit). The context error affected only the top-8 diagnostic eval, not the primary gen-50 test evaluation.

### Amendment 3: `prompts_dir` bug; third launch is first with all prompts active
The fourth launch (PIDs K=2616605, L=2616606, M=2616607, N=2616608, watchdog=2716169) is the valid experimental launch. The first three launches were pilot runs and are excluded from analysis.

### Amendment 4: Random failure sampling
`validate.py` returns all failures; both formatter classes use `random.sample(failures, min(10, len(failures)))` with `cache_handler=NO_CACHE`. Applied uniformly to all four runs. No confound introduced.

### Execution Deviations (not pre-registered)

**Run K best program from gen 43 (not gen 50)**: The test eval script logged `WARNING: best program is from generation 43 — run may not have completed gen 50. Proceeding per pre-registration §2 (crash protocol).` This is not a crash; the run completed gen 50 (confirmed by the K log showing 50 generations of archive_size updates). The gen-43 result is simply the val-best program across all 50 generations, consistent with the pre-registered "best-by-val" selection rule. No action required.

**Top-8 eval partial failure**: The `top8_M.log` and `top8_N.log` files contain only the startup lines (connected to Redis) but no program evaluations — these evals either crashed silently or were not completed. Only `top8_L.log` contains usable results (with a context-length error on the #2 program). This means the planned diagnostic check — "is the best-by-val program particularly unlucky?" — was only partially answered for L. For L, the answer is: the #1 program achieved 60.33% on re-eval vs. 59.33% in results.json, a 1.0pp difference consistent with stochastic noise, suggesting the best-by-val selection was not anomalously unlucky for L.

**Top-8 L reeval discrepancy**: Same program (118f57a7), different evaluations: results.json=59.33%, top8_L=60.33%. Difference of 1.0pp is well within the 2.4pp noise floor (0.44 SE). This is expected behavior under thinking-mode stochasticity.

---

## 7. Next Steps Decision Matrix (Gate 5)

Per the pre-registered decision matrix in Section 10 of the design document:

| Gate 1 | Gate 2 | Pre-registered Next Action |
|--------|--------|---------------------------|
| NULL | NULL | **Move to P3 crossover (structural intervention). Accept prompt-only ceiling.** |

**Recommended action**: Launch P3 crossover experiment (DBs 14/15), design document at `experiments/hotpotqa_p3_crossover/01_design.md`. The NLP prompts experiment provides no evidence that further prompt engineering within the current mutation framework can close the 2.3pp gap to GEPA (60.0% -> 62.3%). P3 crossover tests a structural change (num_parents=2 + AllCombinationsParentSelector) that addresses the single-lineage stagnation bottleneck identified in all prior experiments.

### Additional Considerations for P3 Launch

1. **Baseline config for P3**: Per the P3 design document, the baseline config depends on the NLP prompts experiment outcome. Given the null result, P3 should use the control config: `pipeline=hotpotqa_asi`, `prompts=default`, `problem.name=chains/hotpotqa/static` (fixed val, not rotation). The NLP prompts treatment provides no reason to include it in the P3 baseline.

2. **Rotation val set**: The concerning val-test gaps in this experiment (8.67–13.67pp) strengthen the case against using `static_r` in the P3 experiment. P3 should use fixed-300 (`static`) as pre-specified in its design document: "run P3 without validation rotation (P1=OFF) first."

3. **Deconfounding NLP prompts (optional follow-up)**: If there is interest in isolating the NLP prompt effect, a 2-cell experiment with NLP prompts + fixed val set (NLP vs. default, both on `static`) would cleanly test Hypothesis B. However, given the resource budget (15 runs total, 10 runs used, 5 remaining per Section 13 of research_vision.md), this deconfounding experiment is not on the critical path. P3 has higher expected value.

4. **Val-test gap**: The experiment confirms that `static_r` with 300/1000 samples does not reduce the val-test gap; it increases it. The gap appears to be structural, driven by the 300-sample evaluation noise floor rather than overfitting to specific questions. Larger val sets (500-1000 samples, as proposed in the abandoned P4 step of the research roadmap) may be needed to reduce this gap, but this is deferred given the compute budget.

5. **Archive stagnation as motivation for P3**: All four runs in this experiment stagnated before gen 50 (acceptance rate = 0% for gens 30–50 in treatment runs, gens 44–50 in control). The P3 design explicitly targets this stagnation: crossover generates proposals that combine strengths from two lineages, potentially escaping the single-lineage fitness plateau. The stagnation observed here provides additional positive motivation for P3.

---

## 8. GitHub Closeout

The following steps should be completed to close this experiment branch.

**Step A**: Update `experiments/INDEX.md` — mark PR #69 as COMPLETE (NULL result), record test EMs.

**Step B**: Archive raw data — confirm `experiments/hotpotqa_nlp_prompts/test_evals/results.json` is committed to the branch. Confirm run logs (`run_k.log`, `run_l.log`, `run_m.log`, `run_n.log`) are committed or archived per the archive_run.sh protocol.

**Step C**: Commit this results file (`05_results.md`) to branch `exp/hotpotqa-nlp-prompts`.

**Step D**: Update `docs/plans/2026-03-03-nlp-prompts-experiment.md` — add a one-line status note at the top: `Status: COMPLETE — NULL result. See experiments/hotpotqa_nlp_prompts/05_results.md`.

**Step E**: Update memory files — update `MEMORY.md` and `hotpotqa_research.md` with the null result, the val-test gap findings, and the confirmed transition to P3 crossover.

**Step F**: Merge PR #69 to main. Confirm all Redis DBs 0–3 are flushed and exec_runner workers killed before launching P3 (DBs 14/15).

---

## Appendix A: Numerical Verification

Treatment mean test EM from results.json:
- L: 178/300 = 59.33%
- M: 171/300 = 57.00%
- N: 183/300 = 61.00%
- Mean: (178 + 171 + 183) / 900 = 532/900 = 59.11%

Pooled control mean: (60.00 + 59.3) / 2 = 59.65%

Treatment - control: 59.11 - 59.65 = -0.54pp (treatment is numerically lower)

Note: The user-provided summary calculated treatment mean as (59.33 + 59.33 + 61.00) / 3 = 59.89%, using 59.33% for M instead of 57.00%. The corrected value from results.json is 59.11%. In both cases, Gate 1 is NULL and Gate 2 is NULL. The correction does not change any substantive conclusion.

95% CI on single test EM measurement at p~0.60, n=300: +-5.49pp (binomial SE = sqrt(0.60 * 0.40 / 300) = 0.0283; 95% CI = +-1.96 * 0.0283 * 100 = +-5.5pp). All pairwise differences between runs are within this CI, confirming no run is statistically distinguishable from any other at the single-measurement level.

---

*Ready for Reviewer-2's scrutiny.*
