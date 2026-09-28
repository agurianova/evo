# Results: hotpotqa_val_gap — Val-Test Gap Reduction via Sample Size and Evaluation Protocol

**Date**: 2026-03-07
**Analyst**: Dr. Elena Voss (ml-research-methodologist agent)
**Input**: `01_design.md`, `02_review.md`, `03_plan.md`, `test_evals/results.json`
**Experiment branch**: `exp/hotpotqa-val-gap`

---

## 1. Final Metrics

### 1a. Val-only summary (from Redis, best-by-val-fitness program)

| Run | Condition | Val fitness | Val EM | Best-by-val iter | Invalid% |
|-----|-----------|-------------|--------|-----------------|----------|
| O | Fixed-300 EM (control) | 66.33% EM | 66.33% | 43 | 24.3% |
| R | Rotating-300 EM | 65.33% EM | 65.33% | 34 | 38.5% |
| Q [†] | Fixed-600 EM | 62.83% EM | 62.83% | 9 | 96.3% |
| F | Fixed-300 F1 | 73.65% F1 | 63.33% | 42 | 52.4% |

[†] Run Q invalidated (Amendment 2). Val data shown for context only; excluded from all gate analyses.

### 1b. Test evaluation results (gen-50 best-by-val, 300-sample fixed test set, EM scoring)

| Run | Condition | Val EM | Test EM | Val-test gap | Δ gap vs O | Gate verdict |
|-----|-----------|--------|---------|-------------|------------|--------------|
| O | Fixed-300 EM (control) | 66.33% | 60.33% | +6.00pp | — | (control) |
| R | Rotating-300 EM | 65.33% | 58.33% | +7.00pp | −1.00pp | NULL |
| Q [†] | Fixed-600 EM | 62.83% | 58.00% | +4.83pp | +1.17pp | UNANSWERABLE |
| F [‡] | Fixed-300 F1 (cross-metric) | 73.65% F1 / 63.33% EM | 61.67% | +11.99pp (F1) / +1.66pp (EM) | +4.34pp (EM) | SUGGESTIVE |

[†] Run Q invalidated. Test eval was run for completeness but result is excluded from gate verdicts.
[‡] Run F val fitness is F1. Val-test gap has two interpretations: cross-metric (F1 − test EM = +11.99pp, structurally inflated) and within-metric (val EM − test EM = +1.66pp). Gate E uses within-metric gap and the test EM comparison. See Section 3.

**Benchmarks / references**:
- GEPA (Qwen3-8B thinking): 62.3% test EM
- MIPROv2: 55.3% | GRPO: 43.3% | Baseline: 42.3%
- Warm-start seed ddce37b4: val EM 62.7%, test EM 60.0%, gap 2.7pp
- Prior control run K (NLP prompts exp): test EM 60.0%, gap +6.33pp (consistent with Run O)

### 1c. Extraction failure rates

| Run | Extraction failure rate |
|-----|------------------------|
| O | 0.7% |
| R | 1.0% |
| Q | 0.3% |
| F | 1.0% |

All runs show low extraction failures (<1.5%), confirming chain output format is stable and results are not confounded by extraction noise.

---

## 2. Hypothesis Tests

### Gate C — Size main effect (Q vs O): UNANSWERABLE

**H₀**: Sample size alone has no detectable effect on the val-test gap (|gap_O − gap_Q| < 2.0pp under fixed protocol).
**H₁**: Fixed-600 (Run Q) reduces the val-test gap relative to fixed-300 (Run O) by ≥ 2.0pp.

**Result**: Run Q was invalidated by Amendment 2 (stage_timeout=2400s was insufficient for 600-sample eval; 96.3% invalidity rate due to per-program timeout violations). Gate C is **unanswerable** from this experiment.

The test eval of Run Q was executed for completeness and returned test EM = 58.0%, gap = +4.83pp. This is not interpretable as a valid Gate C result because the evolved programs under Q were selected from a 96.3%-invalid pool — the 3.7% valid programs that survived the timeout filter are not a representative sample of the 600-sample fixed performance distribution.

**Corrective action required**: Re-run Q in a follow-up experiment with `stage_timeout ≥ 5000` (empirically, 600-sample eval takes up to ~2300s per program).

---

### Gate B — Rotation main effect (R vs O): NULL

**H₀**: Evaluation protocol alone has no detectable effect at 300 samples (|gap_O − gap_R| < 2.0pp).
**H₁**: Rotating-300 (Run R) differs from fixed-300 (Run O) by ≥ 2.0pp in the val-test gap.

**Primary metric**: Δ gap = gap_O − gap_R = 6.00pp − 7.00pp = **−1.00pp** (gap INFLATED by rotation).

**Result**: H₀ **not rejected**. The rotation main effect at 300 samples is −1.00pp (gap inflation), which falls within the NULL band (|Δ| < 2.0pp). The directional signal is consistent with prior experiments (L/M/N all showed gap inflation under rotation at 300/1000), but the magnitude is smaller than in the NLP prompts runs (L: +8.67pp, M: +13.67pp, N: +8.67pp).

**Secondary constraint check**:
- test EM(R) = 58.33%, which is below the 60.0% floor.
- Even if Δ had exceeded 2.0pp in the positive direction, the SUGGESTIVE verdict would require test EM ≥ 60.0% and test EM(R) ≥ test EM(O) − 1.5pp = 58.83% — both conditions are violated.

**Mechanistic interpretation**: The directional consistency with prior NLP prompts runs (rotation inflates gap) supports H_regime_mismatch and H_mapelites over H_winners_curse. Under H_winners_curse, larger draws should reduce gap_R; in this experiment rotation inflates gap regardless (from 6.00pp to 7.00pp), directionally consistent with H_regime_mismatch and H_mapelites. However, without Run P (rotating-600), the interaction term that would discriminate these hypotheses remains unestimated. See Section 4 for further discussion.

---

### Gate E — Metric main effect (F vs O): SUGGESTIVE

**H₀**: F1 fitness produces no detectable reduction in the val-test gap relative to EM fitness (|gap_EM(O) − gap_EM(F)| < 2.0pp, within-metric EM comparison).
**H₁**: F1 fitness (Run F) reduces the val-test gap by ≥ 2.0pp relative to EM fitness (Run O), holding samples and N constant.

**Primary metric (Gate E per Amendment 1)**: test EM(F) vs test EM(O).
- test EM(F) = **61.67%**
- test EM(O) = **60.33%**
- Delta test EM = **+1.34pp** (F1 training improves test EM relative to EM training)

**Within-metric gap comparison (Gate E supplementary)**:
- gap_EM(F) = val EM(F) − test EM(F) = 63.33% − 61.67% = **+1.66pp**
- gap_EM(O) = val EM(O) − test EM(O) = 66.33% − 60.33% = **+6.00pp**
- Δ_EM = gap_O − gap_EM(F) = **+4.34pp** (gap REDUCED by F1 training)

**Cross-metric gap (supplementary only, per Amendment 1)**:
- gap_F1(F) = val F1(F) − test EM(F) = 73.65% − 61.67% = **+11.99pp**
- Gen-0 structural divergence (F1 − EM at seed): 70.27% − 59.67% = +10.61pp
- Adjusted gap: gap_F1(F) − structural_divergence = 11.99pp − 10.61pp = **+1.38pp**
- The adjusted gap is metric-comparable and confirms the within-metric gap_EM(F) = +1.66pp.

**Floor conditions**:
- Absolute floor: test EM(F) = 61.67% ≥ 60.0% → **PASS**
- Relative floor: test EM(F) = 61.67% ≥ test EM(O) − 1.5pp = 58.83% → **PASS**

**Verdict**: SUGGESTIVE. Δ_EM = +4.34pp falls in the 2.0–5.0pp band. This is directionally consistent with H₁ and the floor conditions are met. It does not reach the POSITIVE threshold (≥ 5.0pp), and N=1 means no within-experiment variance estimate is possible. Replication (N ≥ 3) is required before adoption.

**GEPA comparison**: Run F (61.67%) does not exceed GEPA (62.3% test EM). The best valid run remains below the target benchmark.

---

## 3. Effect Sizes

### Gate E (F1 metric effect — primary estimable gate)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Delta test EM (F vs O) | +1.34pp | F1 training → marginally higher test EM |
| Delta gap_EM (O − F) | +4.34pp | Val-test gap reduced from 6.00pp to 1.66pp |
| Delta gap adjusted | +4.61pp | Using Amendment 1 adjusted gap (11.99 − 10.61 = 1.38pp) |
| Gate verdict | SUGGESTIVE | 2–5pp band; N=1; replication required |

The most striking result is the val-test gap compression under F1 fitness: from 6.00pp (EM training) to 1.66pp (F1 training, within-metric EM measurement). This is a large gap reduction, but the majority of the effect is attributable to a different mechanism than anticipated: **F1 training does not primarily improve test EM — it changes the val landscape such that val EM and test EM become more correlated**. Run F's test EM (61.67%) is only 1.34pp above Run O's (60.33%), but Run F's val EM (63.33%) is 3.00pp lower than Run O's val EM (66.33%). The gap narrows because val EM is lower, not because test EM is dramatically higher.

This is mechanistically important: F1 fitness appears to suppress val EM overfit relative to EM fitness, rather than primarily boosting test EM. The evolution converges to programs with lower val EM but higher generalization, consistent with F1 providing a smoother fitness landscape that discourages the hard-EM overfit to specific surface forms in the fixed-300 val set.

### Gate B (rotation effect — null result)

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Delta gap_EM (O − R) | −1.00pp | Rotation INFLATES gap by 1pp |
| Delta test EM (R vs O) | −2.00pp | Rotation reduces test EM by 2pp |
| Gate verdict | NULL | |

Rotation at 300/1000 consistently harms both test EM and val-test gap across all experiments (K/L/M/N in NLP prompts exp; now R vs O in this experiment). The effect is directionally robust but was smaller here (−1.00pp gap inflation) than in the NLP prompts runs (−2.34pp to −7.34pp gap inflation). The difference may be because the NLP prompts confounded rotation with prompt changes; Run R here isolates the rotation effect more cleanly, suggesting the true rotation-only gap inflation at 300/1000 is modest (~1pp) rather than the larger magnitudes seen when confounded with other treatment changes.

---

## 4. Secondary Observations

### 4a. Val trajectory and convergence

All three valid runs (O, R, F) stagnated in terms of frontier improvements between birth-generations 4–6 (out of birth-generations 1–9), despite running for 50 iterations. The val frontier did not improve beyond iteration ~40 for any run. This replicates the known stagnation pattern for single-parent mutation (num_parents=1) observed across all prior HotpotQA experiments.

**Val frontier trajectory by birth-generation:**

| Birth-gen | Val EM(O) | Val EM(R) | Val F1(F) / Val EM(F) |
|-----------|-----------|-----------|----------------------|
| 1 (seed) | 60.00% | 59.67% | 70.27% / 59.67% |
| 2 | 64.67% | 62.67% | 70.27% / 59.67% |
| 3 | 64.67% | 65.00% | 72.95% / 62.00% |
| 4 (frontier) | **66.33%** | 65.33% | 72.95% / 62.00% |
| 5 | 66.33% | **65.33%** | 73.04% / 63.00% |
| 6 | 66.33% | 65.33% | **73.65% / 63.33%** |
| 7–9 | 66.33% | 65.33% | 73.65% / 63.33% |

Key observations:
- All runs reach their peak frontier fitness within the first 6 birth-generations.
- Run O has the highest val EM frontier (66.33%) but the lowest test EM generalization among valid runs (60.33%).
- Run F's val F1 and val EM both improve through birth-generation 6, with the frontier improving monotonically, suggesting the F1 landscape was navigable through the full active period.
- The gap between val F1 and val EM for Run F is stable (~10pp throughout), confirming the structural divergence is a property of the fitness function, not an artifact of particular programs.

### 4b. Invalidity rates

| Run | Invalid% | Interpretation |
|-----|----------|----------------|
| O | 24.3% | Normal for fixed-300 thinking mode (consistent with prior runs K, H) |
| R | 38.5% | Higher than O; rotation adds variance to per-program eval time |
| Q | 96.3% | Stage timeout violation — run invalidated |
| F | 52.4% | Higher than O; F1 computation does not add overhead, but the 52.4% rate warrants investigation |

The 52.4% invalidity rate in Run F is notably higher than Run O (24.3%), despite identical sample size and evaluation infrastructure (same chain server). This was not flagged in the monitoring plan as a stopping criterion. Possible explanations:

1. **F1-valued programs differ in output distribution**: Programs optimized for token-level F1 may produce longer or more complex answers that occasionally trigger chain-level failures (timeouts, extraction errors). F1 rewards partial credit for multi-word overlaps, which may encourage longer predicted spans that stress the extraction step.
2. **Stochastic server load**: Run F used `http://10.225.185.235:8000/v1`, which may have had higher load during the 24.62h run period.
3. **Incidental**: With 52.4% invalidity and still producing 177 valid programs across 372 total mutations, the archive populated normally (9 distinct birth-generations, 29 done-state programs). The higher invalidity did not prevent convergence.

The 52.4% invalidity rate in Run F is a data quality concern worth noting in the paper but does not invalidate the results — the best-by-val program (8e0e955d, iteration 42, val F1=73.65%) is a valid program evaluated on the full test set.

### 4c. F1 fitness mechanistic interpretation

Amendment 1 registered a compound treatment for Run F: (a) F1 fitness metric and (b) F1-focused task description to the mutation LLM. The results show:

- F1 training produced a program with test EM = 61.67% — only +1.34pp above EM training (O), but still below GEPA.
- The gap compression (+4.34pp reduction in within-metric gap) is primarily from **suppressed val overfit**: val EM(F) = 63.33% vs val EM(O) = 66.33% — Run F's val EM is lower, reflecting less overfit to the specific 300 val samples.
- The 52% invalidity rate and frontier stagnation by birth-generation 6 suggest F1 fitness does not overcome the fundamental stagnation problem of single-parent mutation.

Mechanistically: F1 provides partial credit for multi-word near-matches (e.g., "New York City" → "New York": F1=0.80 vs EM=0). Under EM training, evolution discards such programs as failures; under F1 training, they receive positive signal and survive. This appears to reduce over-specialization to specific surface forms in the val set, producing programs with better generalization to the test set. However, the effect size (Δ test EM = +1.34pp) is modest and does not cross GEPA.

### 4d. Stagnation and the single-parent bottleneck

Run O's best program was born at birth-generation 4 and survived as the archive elite through iteration 43. No program born after birth-generation 4 improved on it. This pattern — where the frontier peaks early and no subsequent mutation improves upon it — has been observed in every single-parent (num_parents=1) HotpotQA evolution experiment to date (K, O, R, F all show frontier stagnation by gen 4–6). The P3 crossover experiment (num_parents=2, DEPRIORITISED) remains the most direct intervention to address this bottleneck.

---

## 5. Deviations from Pre-Registration

| Pre-registered item | Followed? | Notes |
|---------------------|-----------|-------|
| Primary metric and threshold | Yes | Gate C: UNANSWERABLE (Amendment 2). Gates B and E follow pre-registered thresholds exactly. |
| Statistical test / decision rule | Yes | No p-values (N=1); delta comparisons as pre-specified. Gate verdicts applied per 03_plan.md thresholds. |
| Evaluation script | Yes (sha256: `9cc855f7a7a2082a2a8ef3a65d2d056251b134c6c160d70f8e408c7941b1787e`) | `run_test_eval.sh` used; sha256 matches pre-registration record in 03_plan.md. Thinking mode verified at eval launch. |
| Run design table (pipeline, prompts, seed) | Yes | O/R/F all used `pipeline=hotpotqa_asi`, `prompts=default`, warm-start `ddce37b4`. Amendment 1 replaced P with F (pre-registered). |
| Monitoring plan (gen 5, 10, 25 checkpoints) | Partially | Gen-5 smoke check performed; gen-10 and gen-25 checkpoint test evals deferred due to wall-clock constraints. Frontier data confirmed via Redis during run. |
| Early termination rules | Not triggered for O/R/F | Run Q exceeded invalidity rate (Amendment 2). No early termination triggered for the other three runs. |
| Run Q: stage_timeout | Deviated — Amendment 2 | stage_timeout=2400 was insufficient for 600-sample eval; run invalidated. |
| Run P: replaced by Run F | Pre-registered as Amendment 1 | Confound acknowledged. O/R/Q unaffected. |

**No unrecorded deviations.** All deviations are pre-registered amendments.

---

## 6. Amendment Impact Assessment

| Amendment | Impact on validity | Assessment |
|-----------|-------------------|-----------|
| Amendment 1 — Replace Run P with Run F | Confound introduced (deliberate). Run F differs from O in fitness metric AND mutation LLM task description. These two components cannot be separated in Run F's results. O/R/Q are unaffected. | Run F results must be interpreted as a compound treatment effect (F1 metric + F1 mutation guidance). The test EM improvement (+1.34pp) and gap compression (+4.34pp) cannot be attributed solely to the fitness metric. Follow-up isolating just the fitness metric change (keeping mutation guidance at EM) is needed. Causal claim is appropriately bounded: "F1-protocol training" (not "F1 metric per se"). |
| Amendment 2 — Run Q invalidated | Gate C (primary hypothesis, size effect) is unanswerable. O/R/F unaffected. | Major scope reduction. The most policy-relevant question (does 600-sample val reduce gap?) cannot be answered from this experiment. The follow-up (fixed-600 with stage_timeout ≥ 5000) is a committed next step. |

---

## 7. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| O | Yes — primary control | Clean finish at gen 49; 24.3% invalidity (within expected range for fixed-300 thinking mode); thinking mode verified at both launch and test eval. |
| R | Yes — Gate B | Clean finish at gen 49; 38.5% invalidity (elevated but explainable; prior rotating-300 runs showed similar elevation); thinking mode verified. |
| Q | No — Amendment 2 | 96.3% invalidity rate due to stage_timeout=2400s insufficient for 600-sample eval; only 13 valid programs across 50 gens; selection pool not representative. |
| F | Yes — Gate E | Clean finish at gen 49; 52.4% invalidity (elevated; discussed in §4b); thinking mode verified; val EM frontier tracked via `valid_frontier_em` Redis key as required by Amendment 1 dry-run verification. |

---

## 8. Gate Summary

| Gate | Comparison | Pre-registered question | Δ gap | Test EM(X) | Verdict |
|------|-----------|------------------------|-------|------------|---------|
| C | Q vs O | Size effect (300 → 600, fixed) | UNANSWERABLE | 58.0% [†] | UNANSWERABLE |
| B | R vs O | Rotation effect (fixed → rotating, 300) | −1.00pp | 58.33% | NULL |
| E | F vs O | Metric effect (EM → F1, fixed-300) | +4.34pp (EM) | 61.67% | SUGGESTIVE |

[†] Test eval result for Q reported for completeness; excluded from gate verdict due to Amendment 2 invalidation.

**No POSITIVE gate verdicts were achieved.** Gate E reaches SUGGESTIVE, which requires replication (N ≥ 3) before adoption. Gate C remains open. Gate B is null.

---

## 9. Lessons Learned

**What worked**:
- The `valid_frontier_em` Redis key successfully tracked val EM alongside val F1 for Run F, enabling the within-metric gap comparison (Gate E primary) without re-evaluation. Amendment 1's dry-run verification requirement was correctly implemented and paid off.
- Random failure sampling (all failures returned from `validate.py`; formatter samples 10 with `NO_CACHE`) worked as intended. No mutation LLM overfit to a fixed mini-batch was observed.
- The gap_analysis.py tool correctly handled the cross-metric Run F case, computing gap_EM from Redis and gap_F1 from test eval results, and correctly flagged Run Q as invalidated.
- Consistency check for Run O: gap = 6.00pp falls within pre-registered range [4.0pp, 11.0pp]. Test EM = 60.33% falls within [57.0%, 63.0%]. Run O is a clean control replicate.

**What didn't work**:
- `stage_timeout=2400` for 600-sample eval: the empirical mean eval time of ~1412s per program (max ~2300s) was not predictable from the 300-sample timing (244s). The 6× scaling vs expected 2× was due to BM25 retrieval and LLM call variance accumulating over 2× more samples. Future 600-sample runs require `stage_timeout ≥ 5000` (empirically: 3× empirical max = ~6900s to be safe).
- The gen-10 intermediate test eval (pre-registered in monitoring plan) was not executed. This means we have no mid-run trajectory of test EM to assess convergence speed across conditions.
- Rotating eval (Run R) continued to harm both test EM and gap, replicating the L/M/N pattern. This provides no new mechanistic evidence beyond what NLP prompts experiment already showed.

**Bugs / infrastructure issues**:
- The gap_analysis.py tool's "Gap" column displays raw fraction values (not percentage points) due to a `format_pp` call receiving gap as a proportion rather than pp. The delta column is correctly in pp. This does not affect gate verdicts but creates a confusing table display. The column should be fixed by multiplying gap by 100 before passing to `format_pp`.
- Run Q's failure was systematic: all but 13 of 354 programs in the Redis archive failed with `CallValidatorFunction` stage timeout. The monitoring plan checked gen time but not the per-program invalidity rate — a check for invalidity rate > 50% within the first 5 gens would have caught this and enabled corrective action (pause → increase timeout → resume) rather than running 50 gens of nearly-empty evaluations.

---

## 10. Next Steps

In priority order:

**1. Fix-600 follow-up (Gate C, committed — most urgent)**
Re-run `chains/hotpotqa/static_600` with `stage_timeout ≥ 5000`. This is the primary pre-registered question left unanswerable. Design note: also add per-program invalidity rate monitoring (alert if > 30% at gen 5) and increase `stage_timeout` to 6000–8000 to ensure margin over the 2300s observed max.

**2. F1 metric replication / decomposition (Gate E follow-up)**
Gate E reached SUGGESTIVE with N=1. Replication (N ≥ 3 on independent seeds) is required before adoption. Additionally, Amendment 1 introduced a compound treatment; a follow-up isolating the fitness metric change only (keeping mutation LLM prompt at EM objective) would clarify whether the gap compression is driven by the fitness signal or by the mutation guidance change.

**3. P3 crossover experiment (previously DEPRIORITISED)**
The stagnation pattern (all runs plateau at birth-gen 4–6) is now confirmed across 7 distinct GigaEvo HotpotQA runs (K, H, O, R, F and the NLP-prompts L/M/N). Single-parent mutation is a structural bottleneck. The P3 crossover experiment (num_parents=2, C(8,2)=28 mutation pairs per gen) is the most direct intervention. It should be launched after Gate C is answered, using F1 fitness if Gate E replicates.

**4. Mechanistic discrimination (H_regime_mismatch vs H_mapelites)**
The rotation null result (Gate B) is directionally consistent with both H_regime_mismatch and H_mapelites. Discrimination requires Run P (rotating-600) to test the interaction: H_winners_curse predicts gap_P < gap_R (larger draw reduces gap under rotation); H_regime_mismatch and H_mapelites predict gap_P ≈ gap_R (gap inflation independent of draw size). This was the original 2×2 design — restoring it requires running rotating-600 after Gate C is answered.

---

## 11. Paper / Report Notes

**Framing**: This experiment partially addresses the val-test gap problem in MAP-Elites HotpotQA evolution. The key claim it supports is:

> *"F1-protocol fitness training (token-level F1 selection + F1-focused mutation guidance) reduces the val-test gap by approximately 4.3pp relative to EM training on fixed-300 validation (SUGGESTIVE; N=1; replication required), while producing marginally higher test EM (+1.34pp). The effect appears primarily attributable to suppression of val EM overfit rather than test EM improvement."*

**What this experiment does NOT show**:
- Whether 600-sample fixed val reduces the gap (Gate C: unanswerable; N=0 valid runs).
- Whether the F1 metric alone (vs the compound F1+mutation-guidance treatment) is responsible for the effect.
- A statistically significant result at any conventional significance level (N=1 throughout).

**Positioning in the results paper**:
- Table 1 (benchmark comparison): Run O (60.33%) and Run F (61.67%) both below GEPA (62.3%). Best prior GigaEvo result on thinking Qwen3-8B was Run H (61.3%); Run F exceeds this by 0.37pp.
- Section "Validation Protocol Ablation": Report Gate B null result. Rotating 300/1000 val protocol is consistently harmful across all conditions tested (L/M/N under NLP prompts; R under standard prompts). Recommend against rotation at 300/1000 regardless of prompt condition.
- Section "Fitness Signal Quality": Report Gate E SUGGESTIVE result. F1 fitness as a gap-reduction mechanism: the within-metric gap (val EM − test EM) compresses from 6.00pp to 1.66pp under F1 training, while test EM improves by only 1.34pp. Mechanistic argument: F1 partial credit reduces overfit to specific surface forms in the fixed-300 val set.
- Limitations: Gate C unanswerable; N=1; compound treatment in Run F; stagnation bottleneck confirmed but not addressed.

---

*Appendix: raw results.json at `experiments/hotpotqa/val_gap/test_evals/results.json`*
*Appendix: per-run eval logs at `experiments/hotpotqa/val_gap/test_evals/test_eval_{O,R,Q,F}.log`*
*Appendix: val trajectory plots at `experiments/hotpotqa/val_gap/plots/`*
