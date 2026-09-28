# Experimental Design: Val-Test Gap — 2×2 Factorial (Sample Size × Evaluation Protocol)

**Date**: 2026-03-05
**Researcher**: Dr. Elena Voss (ML Research Methodologist)
**Status**: Revised v3 — second-review fixes (2026-03-05)

> Protocol reference: `docs/protocol/01_design.md`
> Prior review: `experiments/hotpotqa_val_gap/02_review.md` (Prof. Andrei Volkov, NEEDS REVISION)

---

## 1. Research Question

Does changing the validation set size (300 vs 600 samples) or evaluation protocol (fixed vs rotating) reduce the val-test gap in GigaEvo HotpotQA evolution — defined as |frontier val EM − test EM| at generation 50 — without regressing test EM below 60.0%?

This is a **2×2 factorial experiment** crossing two binary factors:
- **Factor A (sample size)**: 300 samples vs 600 samples
- **Factor B (evaluation protocol)**: fixed (same samples every evaluation) vs rotating (hash-seeded draw per chain_spec)

The four cells are:

| | Fixed | Rotating |
|---|---|---|
| **300 samples** | **O** — control; `chains/hotpotqa/static` | **R** — rotation-only effect; `chains/hotpotqa/static_r` |
| **600 samples** | **Q** — size-only effect; `chains/hotpotqa/static_600` | **P** — compound (size + rotation); `chains/hotpotqa/static_r600` |

This design enables full causal decomposition that the prior 2-cell design could not provide:
- **Size main effect**: O vs Q (fixed protocol; 300 vs 600 samples)
- **Rotation main effect**: O vs R (same sample size; fixed vs rotating)
- **Interaction**: is the size effect different under rotation vs fixed? Estimated as (gap_R − gap_P) − (gap_O − gap_Q)

**Why Run R is needed despite L/M/N data**: Runs L, M, N used `prompts=hotpotqa` (NLP prompts), not `prompts=default`. They formed a compound treatment that cannot serve as a clean rotating-300 control for this factorial. Run R uses `prompts=default`, making it directly comparable to Runs O, Q, and P under identical codebase and infrastructure. The L/M/N data is retained as an external reference distribution for Run R (expected range 8.67–13.67pp gap), not as a substitute.

**Three pre-registered mechanistic hypotheses** — each predicts a distinct pattern in the 2×2 result:

**H_winners_curse**: At 300/1000 draws, expected pairwise overlap between any two program evaluations is E[|A∩B|] = 300 × 300 / 1000 = 90 samples (9%). Programs win archive entry partly by drawing easier-than-average subsets. At 600/1000, E[|A∩B|] = 360 samples (36%), halving the draw-variance and substantially reducing the selection advantage from lucky draws. Prediction: rotating-600 (Run P) shows smaller gap than rotating-300 (Run R); the size effect is positive under rotating protocol (larger draws reduce the winner's curse). Rotation need not be worse than fixed if the draw size is large enough.

**H_regime_mismatch**: Programs evolved under a rotating val distribution optimize for the average of many draws, not for any specific draw. The fixed test set represents one specific draw from the test distribution. Programs optimizing for the training draw average will systematically underperform on the fixed test set if the test distribution differs from the training draw distribution. Prediction: both rotating runs (P and R) show larger gaps than their fixed counterparts (O and Q respectively), regardless of sample size. Sample size modulates the magnitude but does not reverse the sign of the rotation penalty.

**H_mapelites** (MAP-Elites bin-level amplification): Under fixed evaluation, all ~50 MAP-Elites archive bins are populated by programs evaluated on the same samples — fitness comparisons across bins are coherent. Under rotating evaluation, each archive bin is populated by a program evaluated on a distinct draw. The archive diversity mechanism ensures heterogeneous programs across bins, which under rotating evaluation means heterogeneous draws across bins. If evaluation difficulty varies across draws (some subsets are harder due to question difficulty variation in HotpotQA_train.jsonl), the archive systematically over-populates bins where programs happened to receive easier draws — not because those bins contain genuinely better programs, but because the easier draws produced inflated fitness scores that cleared the bin threshold. This MAP-Elites-specific amplification of per-draw noise is absent from simpler selection algorithms and operates regardless of draw size. Prediction: both rotating runs (P and R) show larger gaps than their fixed counterparts (O and Q), regardless of sample size. This hypothesis is consistent with the L/M/N pattern: all three rotating-300 runs showed gap > fixed-300 Run K.

**Run R as the discriminating test**: H_regime_mismatch and H_mapelites both predict gap_R > gap_O. H_winners_curse does not necessarily predict this (at 300/1000, the winner's curse is strong, so it also predicts gap_R > gap_O — all three hypotheses agree that rotating-300 should be worse than fixed-300). The critical discriminating comparison is between H_winners_curse and the other two: H_winners_curse predicts gap_P < gap_R (larger draws reduce the gap under rotation), while H_regime_mismatch and H_mapelites predict gap_P ≈ gap_R (rotation is bad regardless of draw size, though the magnitude may differ). The 2×2 pattern of all four gap values will allow Phase 5 to rank the hypotheses.

---

## 2. Hypotheses

### Primary Hypotheses (2×2 main effects and interaction)

**H₀ (size main effect)**: Sample size alone has no detectable effect on the val-test gap. Under fixed protocol: |gap_O − gap_Q| < 2.0pp.

**H₁ (size main effect)**: Fixed-600 (Run Q) reduces the val-test gap relative to fixed-300 (Run O) by >= 2.0pp. A larger fixed val set provides a more discriminating fitness signal, reducing overfitting of the archive to the specific 300-sample evaluation noise.

**H₀ (rotation main effect)**: Evaluation protocol alone has no detectable effect. At 300 samples: |gap_O − gap_R| < 2.0pp.

**H₁ (rotation main effect)**: Rotating-300 (Run R) differs from fixed-300 (Run O) by >= 2.0pp in the gap. Direction is not pre-specified: H_winners_curse, H_regime_mismatch, and H_mapelites all predict gap_R > gap_O (rotating-300 is worse), but the magnitude differs. The direction of the Run P vs Run R comparison discriminates H_winners_curse from the other two.

**H₀ (interaction)**: The size effect is the same under fixed and rotating protocols: |(gap_R − gap_P) − (gap_O − gap_Q)| < 2.0pp.

**H₁ (interaction)**: The size effect differs across protocols by >= 2.0pp. A positive interaction ((gap_R − gap_P) > (gap_O − gap_Q)) would indicate that increasing sample size specifically reduces the gap under rotation (supporting H_winners_curse), while having less effect under fixed protocol.

### Secondary Hypothesis (exploratory)

**H1_disc**: The rotating-600 run (Run P) will show a higher mean archive acceptance rate (mean over gens 10-50) than the fixed-300 control (Run O) by >= 5.0pp, because lower-variance fitness estimates better discriminate genuinely better programs from lucky-draw beneficiaries.

Formally: mean_acceptance_rate(P, gens 10-50) >= mean_acceptance_rate(O, gens 10-50) + 5.0pp.

This does not contribute to the primary verdict and is reported as a mechanistic observation only.

### Primary Comparison for Adoption Verdict

**Primary comparison**: Run Q vs. Run O (fixed-600 vs. fixed-300, Gate C). This is the cleanest single-factor comparison — size only, no rotation confound, no regime-mismatch ambiguity — and its result directly answers whether a larger fixed val set should be adopted as the new default validation protocol. A POSITIVE Gate C result (gap_Q < gap_O − 5.0pp, test EM floor met) is sufficient to recommend adopting `static_600` as the new baseline, independent of Gates B and D.

**Secondary comparison**: Run P vs. Run O (rotating-600 vs. fixed-300, Gate B). This tests the compound treatment (size + rotation together) and remains pre-registered, but it is secondary to Gate C for the adoption decision. A POSITIVE Gate B result without a POSITIVE Gate C result means rotating-600 outperforms fixed-300, but the causal mechanism is unresolved; a POSITIVE Gate B without Gate C is therefore insufficient to recommend rotating-600 adoption as the new default.

**Mechanistic interpretation layer**: The full 2×2 pattern analysis (Gate B Step 2) is the third layer — reported after Gates C and B, and used to rank the three mechanistic hypotheses. The adoption recommendation follows Gate C only; the mechanistic ranking follows the full 2×2 pattern. Phase 5 must report all three layers in this order.

---

### Threshold Rationale

**2.0pp directional threshold**: The val-test gap is measured as a single quantity per run. At n=300 test samples and p~0.60, binomial SE = 2.83pp. Treating val and test errors as independent (conservative): SE(gap_fixed-300) ≈ sqrt(2.83² + 2.83²) = 4.0pp; SE(gap_fixed-600) ≈ sqrt(2.0² + 2.83²) = 3.47pp. The 2.0pp threshold is below one SE — at N=1 per cell, this experiment cannot statistically confirm a 2.0pp effect. The threshold is a practical filter for directionality and minimum magnitude, not a statistical significance threshold. It is applied consistently across all four pairwise comparisons.

**5.0pp POSITIVE actionability threshold**: A gap reduction >= 5.0pp (approximately > 1 SE for the fixed-300 gap) is classified POSITIVE (actionable). A reduction of 2.0–5.0pp is SUGGESTIVE. This resolves the inconsistency in the prior design version where 2.0pp (below the noise floor by the design's own analysis) was labeled POSITIVE. The two categories have distinct next-action requirements: POSITIVE warrants adoption pending N >= 3 replication; SUGGESTIVE requires replication before any adoption decision.

---

## 3. Independent Variable(s)

| Factor | Level 1 | Level 2 |
|--------|---------|---------|
| **A: Sample size** | 300 training samples | 600 training samples |
| **B: Evaluation protocol** | Fixed (same samples every evaluation) | Rotating (hash-seeded draw per chain_spec) |

**2×2 crossing**:

| Run | Sample size | Protocol | `problem.name` |
|-----|-------------|----------|----------------|
| O | 300 | Fixed | `chains/hotpotqa/static` |
| R | 300 | Rotating | `chains/hotpotqa/static_r` |
| Q | 600 | Fixed | `chains/hotpotqa/static_600` |
| P | 600 | Rotating | `chains/hotpotqa/static_r600` |

**Operational definition — fixed protocol**: `validate.py` loads `raw_samples[:N]` sequentially from HotpotQA_train.jsonl. Every call for every chain_spec uses the same N samples. N=300: first 300 samples; N=600: first 600 samples.

**Operational definition — rotating protocol**: `validate.py` computes a SHA-256 hash of the serialized `chain_spec` dict (mechanism: `hashlib.sha256(json.dumps(chain_spec, sort_keys=True, default=str).encode())`), seeds `random.Random(spec_seed)`, and calls `rng.sample(raw_all, N)` where raw_all is all 1000 training samples. The draw is **deterministic per chain_spec** — the same chain_spec always receives the same N-sample draw, regardless of how many times validate.py is called. Two programs differing by even one character receive distinct but reproducible draws. N=300: `static_r` (existing directory); N=600: `static_r600` (new directory; only change from `static_r/validate.py` is `rng.sample(raw_all, 600)` instead of `rng.sample(raw_all, 300)`).

**Expected pairwise overlap by protocol**:
- Fixed-300: |A∩B| = 300 for all pairs (100% — all programs evaluated on identical samples)
- Rotating-300: E[|A∩B|] = 300 × 300 / 1000 = 90 samples (9%)
- Fixed-600: |A∩B| = 600 for all pairs (100%)
- Rotating-600: E[|A∩B|] = 600 × 600 / 1000 = 360 samples (36%)

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Val-test gap at gen 50 | \|frontier val EM − test EM\| where frontier val EM is the best-by-val program's val score under its own protocol, and test EM is its evaluation on the fixed 300-sample test set | **Yes (gap)** |
| Test EM at gen 50 | Best-by-val program evaluated on fixed 300-sample test set | **Yes (EM floor)** |
| Val EM trajectory (gens 1-50) | Best-of-archive val EM per generation from Redis | No (diagnostic) |
| Test EM at gen 10, 25 | Intermediate checkpoints; best-by-val program | No |
| Archive acceptance rate | Fraction of mutations entering the archive, mean over gens 10-50 | No (mechanistic) |
| Archive size trajectory | Number of programs in archive per generation | No |
| Best program generation | Generation producing the val-best program | No |
| Extraction failure rate | Fraction of test answers where `extract_answer()` returns None | No |

**Primary metric 1 (gap)**: Val-test gap = |best-by-val val EM − test EM| at generation 50. The primary question is whether the gap varies systematically across the 2×2 cells.

**Primary metric 2 (test EM floor)**: A gap reduction achieved by degrading test EM is not a success.

**Joint success criterion** (for declaring any run POSITIVE relative to Run O):
1. gap(X) < gap(O) − 5.0pp (gap reduction is actionable — exceeds the ~1 SE noise floor)
2. test EM(X) >= 60.0% (absolute floor; matches seed test performance)
3. test EM(X) >= test EM(O) − 1.5pp (relative floor; prevents classifying as POSITIVE when Run O is anomalously weak and the treatment passes the absolute floor only by comparison to a poor control)

All three conditions must hold simultaneously for a POSITIVE verdict. Condition 3 is pre-registered here with its motivation and applies to the decision gate in Section 10; the two are now identical.

**Note on best-by-val identification for rotating runs (R and P)**: Each program's val EM score in the Redis archive reflects a single deterministic evaluation on the draw fixed by its SHA-256-hashed chain_spec. The program with the highest archived val EM is selected as "best-by-val." This score is not the program's expected accuracy under the draw distribution — it is the program's accuracy on its specific draw. The upward selection bias from choosing the maximum over 50 generations of distinct programs makes gap_R and gap_P upper-bound estimates: any measured gap reduction for rotating runs is conservative (the true gap under the winner's curse bias is likely larger, not smaller). A sensitivity check — re-evaluating the top-5 programs by archive val EM on the fixed test set and selecting by test EM — is exploratory and does not replace the pre-registered primary analysis, but will be reported in Phase 5.

**Val EM comparability across runs**: Fixed-protocol runs (O, Q) have comparable val EM values within their run (all programs on identical samples). Rotating-protocol runs (R, P) have val EM values measured on program-specific draws and are not comparable across programs or to fixed-protocol runs. Only the gap (val EM − test EM) is a valid cross-condition comparison metric; raw val EM values must always be reported with their protocol and N.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| `seed_program` | ddce37b4 (val=62.7% on fixed-300; test=60.0%) | Identical warm start for all four runs |
| `max_generations` | 50 | Standard horizon; consistent with all prior HotpotQA experiments |
| `max_elites_per_generation` | 8 | Matches prior experiments |
| `max_mutations_per_generation` | 8 | Standard throughput; consistent with K, I/J |
| `num_parents` | 1 | Single-parent mutation; isolates validation protocol effects |
| `mutation_mode` | rewrite | Standard for this problem |
| `pipeline` | `hotpotqa_asi` | Required for tuple-returning validate.py; repr-contamination bug makes standard invalid |
| `prompts` | `default` | NLP prompts were a NULL result in K/L/M/N; default is the validated baseline. All four runs use default to ensure cross-cell comparability. Run R specifically uses `prompts=default` to be cleanly comparable to O, Q, and P — this is the key difference from L/M/N which used `prompts=hotpotqa`. |
| `llm_base_url` | Shared 4-server pool (1 per run; assigned at launch) | Same infrastructure for all runs |
| Chain LLM | Qwen3-8B (thinking mode, step_max_tokens 8192 for all LLM steps) | Required for GEPA benchmark comparability |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 via vLLM | Standard mutation model |
| Test set | Fixed 300 samples from HotpotQA_test.jsonl | Identical across all four runs; never seen during evolution |
| Random failure sampling | Active: validate.py returns all failures; formatter samples 10 randomly per generation; `cache_handler = NO_CACHE` | Inherited from cf0cfc1; prevents mutation overfitting |
| `parent_selector` | `AllCombinationsParentSelector` | Standard selector |
| `primary_resolution` | 50 | Standard MAP-Elites fitness bins |

---

## 6. Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | Val N | Val protocol | Seed |
|-----|-------|------------|-----------|-----------|----------------|-------|--------------|------|
| O | Control (fixed-300) | 4 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static` | 300 | Fixed sequential | ddce37b4 |
| R | Rotation-only (rotating-300) | 7 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_r` | 300 | Hash-seeded random | ddce37b4 |
| Q | Size-only (fixed-600) | 6 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_600` | 600 | Fixed sequential | ddce37b4 |
| P | Compound (rotating-600) | 5 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_r600` | 600 | Hash-seeded random | ddce37b4 |

**All four runs differ only in `problem.name`** (and therefore `validate.py`). Every other field is identical.

**Redis DBs**: 4 (Run O), 5 (Run P), 6 (Run Q), 7 (Run R). DBs 0–3 are reserved for prior NLP prompts data pending flush. DBs 14–15 are reserved for P3 crossover. DBs 4–7 are confirmed available.

**Why a fresh Run O instead of reusing Run K**: Launching all four runs simultaneously on the same codebase and infrastructure eliminates temporal confounds across the 2×2 cells. Run O also provides an independent replication of the fixed-300 control, adding to the reference distribution (K=6.33pp gap).

**Why a fresh Run R instead of reusing L/M/N**: Runs L/M/N used `prompts=hotpotqa`, not `prompts=default`. They cannot serve as the rotating-300 cell for this factorial. Run R provides the missing default-prompt rotating-300 data point.

**Seed val EM under each protocol — determinism note**: All seed val EM values are deterministic per protocol:
- Fixed-300 (O): val EM = 62.7% (measured; reproducible).
- Fixed-600 (Q): val EM = deterministic on first 600 samples. Measure at pre-launch dry-run; expected 60–66%.
- Rotating-300 (R): val EM = deterministic value fixed by SHA-256 hash of seed's chain_spec; realized on one specific 300-sample draw. **Re-evaluating the same chain_spec always yields the same draw.** Measure at dry-run.
- Rotating-600 (P): val EM = deterministic value fixed by SHA-256 hash of seed's chain_spec; realized on one specific 600-sample draw. **Re-evaluating the same chain_spec always yields the same draw** — not a per-call random subset. Measure at dry-run; expected 60–66%.

---

## 7. Sample Size Justification

**N=1 per cell (4 runs total).**

This is an acknowledged limitation. Full justification follows.

**Why N=1 is the only feasible option**: Each run requires ~20-32 hours of wall time. Running 4 replications per cell (minimum for a t-test) would require 16 runs = 400+ GPU-hours and ~2 weeks of wall time, which is infeasible given the shared infrastructure.

**What N=1 per cell in a 2×2 ENABLES**: With four data points (gap_O, gap_R, gap_Q, gap_P), we can estimate the sign and rough magnitude of both main effects and the interaction without replication. The 2×2 structure also provides internal consistency checks: a mechanistic hypothesis that predicts both rotating runs worse than their fixed counterparts (H_regime_mismatch, H_mapelites) makes two falsifiable predictions (gap_R > gap_O AND gap_P > gap_Q), not one. Consistency across both predictions is more compelling than a single pairwise comparison at N=1.

**External reference distributions**:
- Run K (fixed-300, default prompts, ddce37b4 seed): test EM=60.0%, gap=6.33pp — primary precedent for Run O.
- Runs L/M/N (rotating-300, NLP prompts): gaps 8.67–13.67pp (mean 10.34pp) — external reference for Run R direction; expected range under default prompts is uncertain but the directional pattern (gap > fixed-300) is the pre-registered prediction of all three hypotheses.
- Seed ddce37b4 intrinsic gap: 2.7pp at gen 0; evolution adds ~3.6pp under fixed-300 (K).

**Noise floor**: Gap differences of < 2.0pp are indistinguishable from sampling noise at N=1 per cell (Section 2). The 2×2 design improves interpretive power not by reducing the per-cell noise floor, but by providing four data points whose pattern is checked against pre-registered hypotheses. A pattern where both rotating runs show worse gap than their fixed counterparts — if both differences exceed 2.0pp — is consistent with two cells independently exceeding the noise floor in the same predicted direction, which is more compelling than a single exceeding-noise-floor result.

---

## 8. Statistical Test

**Test**: Pre-specified 2×2 effect-size analysis. No formal null hypothesis significance test is conducted; N=1 per cell does not support valid p-value computation.

**How computed**:

1. At generation 50, identify the best-by-val program from each of the four runs (highest val EM in the Redis archive across all generations 1-50).
2. Evaluate each best-by-val program on the fixed 300-sample test set.
3. Compute for each run: `gap_X` = val EM(X) − test EM(X).
4. Compute main effects and interaction:
   - **Size main effect (fixed protocol)**: `delta_size_fixed` = gap_O − gap_Q
   - **Size main effect (rotating protocol)**: `delta_size_rot` = gap_R − gap_P
   - **Rotation main effect (300 samples)**: `delta_rot_300` = gap_O − gap_R
   - **Rotation main effect (600 samples)**: `delta_rot_600` = gap_Q − gap_P
   - **Interaction**: `interaction` = delta_size_rot − delta_size_fixed = (gap_R − gap_P) − (gap_O − gap_Q)
5. Classify each comparison using the POSITIVE / SUGGESTIVE / NULL / NEGATIVE scale from Section 10.
6. Rank the three mechanistic hypotheses against the observed 2×2 pattern using the interpretation table in Section 10, Gate B.

**Consistency check for Run O**: gap_O should fall within [4.0pp, 11.0pp] and test_EM(O) within [57.0%, 63.0%]. Upper bound is 11.0pp (widened from 9.0pp per the review; Run H at ~9.7pp should not trigger a false anomaly, and the prior 9.0pp bound was too narrow). If Run O falls outside this range, investigate before interpreting the 2×2.

**Consistency check for Run R**: gap_R should fall within [5.0pp, 15.0pp], informed by L/M/N (8.67–13.67pp under NLP prompts). If gap_R < 5.0pp, Run R substantially outperforms L/M/N — investigate. If gap_R > 15.0pp, investigate.

**Winner's curse directional qualifier on rotating gap measurements**: For rotating runs (R and P), val EM(X) is realized on the program-specific draw that may be easier than average, upward-biasing val EM. This makes gap_R and gap_P upper-bound estimates: the measured gap is biased toward appearing smaller than the true gap. A measured gap increase for rotating runs (gap_R > gap_O or gap_P > gap_Q) cannot be attributed to this bias — it acts in the direction of underestimating, not overestimating, the gap. Phase 5 should report this directional qualifier alongside all rotating-run gap comparisons.

**Bootstrap sensitivity (exploratory, post-hoc)**: For any delta in the SUGGESTIVE range (2.0–5.0pp), resample the 300 test predictions with replacement (10,000 iterations) to estimate test-set sampling noise. Reported as sensitivity analysis; does not change the primary verdict.

---

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| **MAP-Elites bin-level winner's curse (H_mapelites)** | Under rotating evaluation, each of the ~50 MAP-Elites archive bins is populated by a program evaluated on a distinct draw. The archive diversity mechanism ensures heterogeneous draws across bins. Bins where programs happen to receive easier draws are over-represented in the archive — not because those bins contain genuinely better programs, but because easier draws produce inflated fitness scores. This MAP-Elites-specific amplification of per-draw noise is absent from simple elitist selection and operates regardless of draw size, predicting gap inflation under any rotating protocol. This is consistent with the L/M/N pattern. | Pre-registered as H_mapelites. The 2×2 design directly tests it: if both rotating runs (R and P) show gap > their fixed counterparts (O and Q), the pattern is consistent with H_mapelites (and H_regime_mismatch). If only rotating-300 (R) shows inflation and rotating-600 (P) does not, H_winners_curse is better supported. Reported as a mechanistic finding, not an artifact to eliminate. |
| **Winner's curse within rotating archive (selection bias on val EM)** | The best-by-val program in a rotating run is selected as the program with the highest archived val EM. This score may be realized on an easier-than-average draw. The reported val EM is upward-biased relative to the program's expected accuracy, making gap_R and gap_P conservative upper-bound estimates. | Acknowledged in Sections 4 and 8. Bias direction means gap reductions under rotating protocols are understated (conservative). Sensitivity check (re-evaluate top-5 by test EM) is exploratory. Does not affect the fixed-protocol comparisons (O vs Q). |
| **Fitness comparability within rotating archives** | Programs in the same rotating archive were evaluated on different draws — their val EM scores are not on a common scale. MAP-Elites bin placement is determined by fitness scores that are not comparable across programs. | Inherent to the rotating-evaluation treatment. Not addressable without changing the treatment. Part of what this experiment tests. |
| **Richer failure pool at 600 samples** | At ~60% EM with 600 samples, expected failures are ~240 (vs ~120 with 300). The formatter samples 10 randomly from this pool. With 240 failures, the random sample of 10 covers more of the failure taxonomy (retrieval errors, reasoning errors, extraction failures) than with 120. This is a qualitative change in the mutation signal content, not just a noise reduction. If Runs Q or P show improved test EM, it is ambiguous whether this came from (a) larger val set reducing overfitting, (b) rotation effects, or (c) higher-quality failure diagnostics driving better mutations. | Acknowledged as a genuine confound co-varying with the sample-size factor. The 2×2 structure allows partial separation: comparing Q vs O isolates the combined size + failure-pool effect under fixed protocol. The failure-pool mechanism will be discussed as a limiting interpretive caveat for the size main effect in Phase 5. Cannot be fully controlled without a separate experiment that varies failure pool size independently of val set size. |
| **Evaluation time asymmetry** | Fixed-300 and rotating-300 (O, R): ~5 min/gen. Fixed-600 and rotating-600 (Q, P): ~8 min/gen (projected; verify at dry-run). Q and P complete ~150 min later than O and R if all launched simultaneously. | All four runs execute to gen 50 with no wall-time cutoff. Monitor gen count at 24h checkpoint. No early termination based on timing differential. |
| **Seed draw determinism** | For rotating runs (R, P), the seed's initial val EM is deterministic (fixed by SHA-256 hash of chain_spec). The realized draw may be easier or harder than average by ~2pp (binomial SE). A particularly hard seed draw could slow early evolution for R or P. | Measure all four seed val EM values at pre-launch dry-run. If any rotating seed val EM is > 4pp below the fixed-300 seed val EM (62.7%), investigate the draw before launch. |
| **N=1 trajectory variance** | Any observed gap difference could reflect random evolutionary trajectory differences. | Acknowledged. The 2×2 structure provides internal consistency checks: a mechanistic hypothesis predicting a directional pattern (e.g., both rotating runs worse than fixed) makes two testable predictions. Consistency across both strengthens the evidence beyond a single pairwise comparison. Screening study; any positive result requires N >= 3 replication. |
| **Test EM floor risk** | Gap reduction with degraded test EM is not a success. | Joint success criterion (Section 4) requires test EM >= 60.0% AND test EM >= test_EM(O) − 1.5pp for any POSITIVE verdict. Both conditions must hold. |

---

## 10. Stop Criteria and Decision Gates

### Early Termination

- **Crash with no recovery**: If a run crashes and cannot be resumed within 2 hours, terminate. Surviving runs continue; the 2×2 degrades to an incomplete factorial. Analysis is adjusted to interpret available cells only, with the missing cell noted as a limitation.
- **Zero mutations for 5+ consecutive generations, OR mutation stage timeout > 30 min for any run**: Zero mutations indicates a selector or configuration bug; a 30-min mutation stage timeout with no output indicates mutation LLM server failure (the run.py process will not crash — it will hang silently, and the generation counter may not advance). Diagnose the mutation LLM server before continuing. If the server cannot be restored within 2 hours, terminate the affected run. The surviving three runs continue; the 2×2 degrades to an incomplete factorial. Record which cell is lost and adjust Phase 5 analysis accordingly. Do NOT attempt to infer the missing cell from the remaining three runs.
- **Mutation server failure (server unreachable > 30 min)**: If one of the four assigned mutation LLM servers becomes unreachable for > 30 minutes, pause the affected run and attempt to reassign to a backup server. If no backup is available (all four servers are assigned and one fails), terminate the affected run. With N=1 per cell, losing one run degrades the 2×2 to an incomplete factorial — record which comparison is lost and adjust Phase 5 analysis accordingly. Do NOT attempt to infer the missing cell from other runs.
- **validate.py runtime > 15 min/gen for 600-sample runs (Q or P)**: If 600-sample evaluation exceeds 15 min/gen (approximately 2× the ~8 min estimate), this indicates server contention or infrastructure failure. Pause, diagnose, resume if resolvable within 4 hours; otherwise terminate. If dry-run gen time for Q or P exceeds 12 min before launch, flag as at-risk and review server utilization before proceeding.

No early termination for poor fitness. All four runs execute for the full 50 generations regardless of val EM trajectory.

### Run Invalidation

A completed run is excluded from the 2×2 analysis if:
- Post-hoc inspection reveals a configuration error (wrong pipeline, wrong seed, wrong problem.name, wrong val protocol, wrong prompts setting).
- The repr-contamination bug was active (pipeline=standard with tuple-returning validate.py).
- A 600-sample validate.py was silently loading only 300 samples due to a code error — verified at dry-run by logging dataset length before the first evaluation call.
- Redis corruption caused missing generation data for > 5 generations.
- Chain LLM operated in non-thinking mode (absence of `<think>` blocks in outputs).
- `prompts=hotpotqa` was active instead of `prompts=default` — verified at dry-run via `[PROMPT FILES]` section of dry-run output.

### Pre-Registered Decision Gates

**Gate A: Consistency checks — all four runs**

| Run | Acceptance range (gap) | Acceptance range (test EM) | Anomaly action |
|-----|------------------------|---------------------------|----------------|
| O (fixed-300) | [4.0pp, 11.0pp] | [57.0%, 63.0%] | Investigate before interpreting 2×2 |
| R (rotating-300) | [4.0pp, 15.0pp] | [55.0%, 63.0%] | Note: L/M/N reference is 8.67–13.67pp under NLP prompts |
| Q (fixed-600) | [3.0pp, 9.0pp] | [57.0%, 65.0%] | Lower bound is 3.0pp — above seed's gen-0 intrinsic gap (2.7pp); a gap < 3.0pp at gen 50 would be a positive anomaly requiring verification before any POSITIVE verdict |
| P (rotating-600) | [4.0pp, 15.0pp] | [55.0%, 65.0%] | Lower bound is 4.0pp — rotating protocols have not produced gaps below 8.67pp in prior experiments; a gap < 4.0pp would contradict all prior rotating-protocol data and warrants investigation before declaring a POSITIVE result |

If any run fails Gate A, analysis proceeds for remaining valid runs with the incomplete factorial noted.

**Gate B: Primary verdict — 2×2 pattern classification**

**Step 1: Classify each pairwise comparison using the effect-size scale:**

| Classification | Criterion | Scientific standing |
|---------------|-----------|-------------------|
| **POSITIVE** (actionable) | delta >= +5.0pp AND all three joint success conditions from Section 4 | > ~1 SE gap reduction; warrants adoption pending N >= 3 replication |
| **SUGGESTIVE** | delta in [+2.0pp, +5.0pp) AND test EM floor conditions met | Directionally consistent; below noise floor at N=1; requires replication before adoption |
| **NULL** | abs(delta) < 2.0pp | No detectable gap change; within sampling noise |
| **NEGATIVE** | delta <= -2.0pp (gap increased) | Gap inflation; treatment is worse than control |

**Step 2: Mechanistic hypothesis ranking from the 2×2 pattern:**

| Observed pattern | Supported hypothesis | Interpretation |
|-----------------|---------------------|----------------|
| gap_R > gap_O AND gap_P > gap_Q (both rotating worse than fixed) | H_regime_mismatch or H_mapelites | Rotation inflates gap at any sample size. Use fixed val sets. Consider gap-penalized fitness next. |
| gap_R > gap_O AND gap_P < gap_R (rotating-300 worse; rotating-600 better than rotating-300) | H_winners_curse (partial) | Sample size within rotating protocol helps; winner's curse partially reduced at 600/1000. gap_P vs gap_O determines whether rotating-600 also beats fixed-300. |
| gap_R > gap_O AND gap_P ≈ gap_O (rotating-300 worse; rotating-600 matches fixed-300) | H_winners_curse (strong) | 600/1000 coverage fully compensates for winner's curse. Rotating-600 is a viable alternative to fixed-300. |
| gap_R > gap_O AND gap_P < gap_O (rotating-300 worse; rotating-600 better than fixed-300) | H_winners_curse (strongest) | At 600/1000, rotating evaluation outperforms fixed-300 — draw diversity provides additional benefit beyond mere noise reduction. |
| gap_Q < gap_O (fixed-600 reduces gap) regardless of rotation pattern | Size main effect confirmed | Larger fixed val set reduces overfitting. Consider adopting fixed-600 as baseline. |
| gap_R <= gap_O (rotating-300 matches or beats fixed-300) | H_winners_curse strongly supported at 300/1000; H_mapelites falsified | Unexpected — contradicts L/M/N empirical pattern (all three rotating-300 runs showed gap > K). Possible explanation: the clean default-prompts control exposes a qualitatively different evolutionary dynamic than the NLP-prompt runs (no prompt-rotation interaction). Flag as anomaly requiring investigation. Do not adopt rotating-300 based on this result alone without replication at N >= 3. |
| All comparisons NULL | No detectable effect | Neither factor affects gap at the tested ranges. Pursue gap-penalized fitness or larger val sets (N=1000). |

**Gate C: Individual POSITIVE verdict for Run Q (cleanest single-factor test)**

Run Q (fixed-600) tests the size effect under fixed protocol — the cleanest isolation of sample size with no rotation confound. A POSITIVE verdict for Run Q requires all three conditions from Section 4:
1. gap_Q < gap_O − 5.0pp
2. test EM(Q) >= 60.0%
3. test EM(Q) >= test EM(O) − 1.5pp

If Gate C is POSITIVE, `static_600` is recommended as the new baseline val set for future experiments (cleaner fitness signal, no rotation complexity).

**Gate D: Secondary exploratory analysis (H1_disc / acceptance rate)**

Compute mean acceptance rate over gens 10-50 for all four runs. If acceptance_rate(P) >= acceptance_rate(O) + 5.0pp, this is consistent with H1_disc. Does NOT upgrade any NULL Gate B verdict; reported as a mechanistic observation only.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| GPU hours (mutation LLM) | ~96h total (4 runs × ~24h; 8 mutations/gen × ~3 min/mutation × 50 gens = ~20h active + overhead per run) |
| GPU hours (chain LLM — Runs O, R) | ~20h each (50 gens × ~5 min/gen + mutation candidate evals) |
| GPU hours (chain LLM — Runs Q, P) | ~28h each (50 gens × ~8 min/gen projected + mutation candidate evals; 600 samples ≈ 1.6× longer — **verify at dry-run**) |
| Wall time (Runs O, R) | ~20-24h each |
| Wall time (Runs Q, P) | ~26-32h each |
| Wall time (total, concurrent) | ~30-36h (limited by Q and P; all 4 runs launched simultaneously) |
| Redis DBs used | 4 (DB 4: Run O; DB 5: Run P; DB 6: Run Q; DB 7: Run R) |
| Test evaluation | 4 evaluations × ~5 min each = ~20 min (run at gen 50 only) |
| New problem directories | 2: `problems/chains/hotpotqa/static_600/` (fixed-600) and `problems/chains/hotpotqa/static_r600/` (rotating-600) |
| Existing problem directories | 2: `chains/hotpotqa/static` (Run O) and `chains/hotpotqa/static_r` (Run R) — no changes required |
| Mutation servers | 4 of 4 available (1 per run; all four servers assigned) |
| Chain servers | 4 of 4 available (1 per run; all four ports assigned) |

**Runtime estimate for 600-sample validation**: ~8 min/gen projected (linear scaling from 300-sample ~5 min mean). This is an assumption to be verified at dry-run before launch. If dry-run gen time for Q or P exceeds 12 min, flag as at-risk and review mutation server utilization before proceeding.

**All four mutation LLM servers are consumed by this experiment**. No other experiments (including P3 crossover) can run concurrently without server contention. P3 crossover has been deprioritised pending resolution of the val-test gap; schedule this experiment first.

---

## 12. Open Questions / Risks

1. **Two new problem directories required.** `static_600/` requires a `validate.py` that loads `raw_samples[:600]` sequentially (only change from `static/validate.py`). `static_r600/` requires a `validate.py` that calls `rng.sample(raw_all, 600)` instead of `rng.sample(raw_all, 300)` (only change from `static_r/validate.py`). Both must be committed before Phase 3 launch and verified at dry-run by logging dataset length at the first validation call. The formatter, config, and initial_programs directories are identical to their respective parent directories.

2. **Causal decomposition is now fully internal to this design.** With the 2×2 expansion, all four factorial cells are present. The questions "is the effect due to size or rotation?" and "do the two factors interact?" are answerable from the four data points without any external follow-up experiment. Phase 5 reports all six pairwise comparisons plus the interaction estimate.

3. **H_mapelites makes a falsifiable prediction that this design can test.** If gap_R > gap_O AND gap_P > gap_Q (both rotating runs worse than fixed), the pattern is consistent with H_mapelites predicting gap inflation under any rotating protocol regardless of draw size. If gap_R > gap_O AND gap_P < gap_R (but gap_P still > gap_Q), the pattern is more consistent with H_winners_curse providing partial mitigation. Distinguishing H_mapelites from H_regime_mismatch requires a follow-up experiment testing MAP-Elites specifically (e.g., replacing MAP-Elites with simple elitism under rotating evaluation) — this is out of scope but noted for the research roadmap.

4. **Run R fills a gap in the experimental record.** Runs L/M/N established rotating-300 gaps of 8.67–13.67pp under `prompts=hotpotqa`. Run R will establish rotating-300 gap under `prompts=default`. If gap_R is substantially lower than the L/M/N mean (e.g., < 7pp), this suggests NLP prompts interact with rotation to inflate the gap — a secondary finding relevant to interpreting the NLP prompts null result. This is a secondary observation; it does not affect the 2×2 primary analysis.

5. **Run O replicates K but is not identical to it.** Same config, seed, and val set; different time and infrastructure state. Expected result: within [57.0%, 63.0%] test EM and [4.0pp, 11.0pp] gap. A significant deviation from K (60.0% test EM, 6.33pp gap) requires investigation via Gate A before the other three runs are interpreted.

6. **All four mutation LLM servers are required for concurrent execution.** Launching fewer than 4 simultaneously (e.g., O and R first, then Q and P) introduces a temporal confound across cells in the factorial. Strongly recommend launching all four simultaneously. If only 2 servers are available, launch O and R first (300-sample runs, shorter wall time), then Q and P — but document the temporal confound and assess it in Phase 5.

7. **GEPA comparison note.** GEPA achieves 62.3% test EM. This experiment targets gap reduction. However, if any run achieves test EM > 62.3%, it is the first GigaEvo result to beat GEPA and warrants reporting regardless of the primary gap verdict. Probability is low given K's 60.0% result under identical config, but should not be overlooked in Phase 5.

---

## Appendix A: Pre-Launch Checklist (for Phase 3)

- [ ] Create `problems/chains/hotpotqa/static_600/` directory; verify `validate.py` loads `raw_samples[:600]` (not 300); confirm all other logic is identical to `static/validate.py`
- [ ] Create `problems/chains/hotpotqa/static_r600/` directory; verify `validate.py` uses `rng.sample(raw_all, 600)` (not 300); confirm all other logic is identical to `static_r/validate.py`
- [ ] Verify both new directories: `validate.py` returns `(metrics, failures)` tuple (required for `pipeline=hotpotqa_asi`)
- [ ] Verify `hotpotqa_asi.yaml` has `prompts_dir: ${prompts.dir}` in BOTH `evolution_context` AND `mutation_operator` blocks (config bug 920c975 — silent failure if missing)
- [ ] Dry-run all four runs (on scratch DBs or DBs 4–7 after confirming empty):
  - Run O: `problem.name=chains/hotpotqa/static`, `redis.db=4`; verify logged dataset length = 300
  - Run R: `problem.name=chains/hotpotqa/static_r`, `redis.db=7`; verify logged dataset length = 300
  - Run R (Amendment 4 verification): verify `static_r/validate.py` returns ALL failures with no `[:10]` cap — run `grep 'failures\[' problems/chains/hotpotqa/static_r/validate.py` and confirm no slice is present in the return statement; verify both formatter classes (`HotpotQAASIFormatter`, `HotpotQAFailureFormatter`) use `random.sample(failures, min(10, len(failures)))` with `cache_handler = NO_CACHE` (Amendment 4, cf0cfc1, must be active)
  - Run Q: `problem.name=chains/hotpotqa/static_600`, `redis.db=6`; verify logged dataset length = 600
  - Run P: `problem.name=chains/hotpotqa/static_r600`, `redis.db=5`; verify logged dataset length = 600
  - For all runs: verify full resolved config matches design table (pipeline=hotpotqa_asi, prompts=default, num_parents=1, max_mutations=8, seed=ddce37b4)
- [ ] Verify `[PROMPT FILES]` section in dry-run output shows `[default]` for all prompts on all four runs (NLP overrides must NOT be present)
- [ ] Measure seed's initial val EM for all four protocols at dry-run; document; verify rotating draws are not anomalously hard (> 4pp below fixed-300 seed val EM of 62.7%)
- [ ] If dry-run gen time for Q or P exceeds 12 min, flag as at-risk and review server utilization before launching
- [ ] Confirm DBs 4, 5, 6, 7 are empty (flush with `tools/flush.py --db 4 5 6 7 --confirm` after killing exec_runners)
- [ ] Verify chain servers have 32k context window (`--max-model-len 32768`; required per prior experiment memory)
- [ ] Kill any stale exec_runner workers from prior runs (`ps aux | grep exec_runner`)
- [ ] Implement watchdog: `_last_gen` derived from `RUNS` list (not hardcoded) — prior watchdog crash caused by hardcoded labels; verify 60s functional test
- [ ] Confirm all four runs will launch simultaneously (1 mutation server per run; all four chain server ports assigned)
- [ ] Confirm `bash tools/experiment/check_phase_order.sh hotpotqa_val_gap` passes before launch

---

## Appendix B: Relationship to Prior Experiments

| Experiment | Runs | Status | Relevance to val-gap |
|-----------|------|--------|----------------------|
| HotpotQA thinking-mode baseline | B, D | Complete | Established ddce37b4 seed (val 62.7% on fixed-300; test 60.0%) |
| P1xP2 factorial | E, F, G, H | Complete (E+G invalid) | H: best test EM 61.3% / gap ~9.7pp. First evidence of large val-test gap in production runs. |
| NLP prompts | K, L, M, N | Complete — NULL | K (fixed-300, default): gap=6.33pp — primary anchor for Run O. L/M/N (rotating-300, NLP prompts): gaps 8.67–13.67pp — external reference for Run R direction; confounded with NLP prompts treatment. |
| P3 crossover | I, J | Designed (DBs 14/15) | Deprioritised pending val-gap resolution. No scheduling interaction with this experiment (uses DBs 14/15). |
| **val-gap (2×2)** | **O, R, Q, P** | **This experiment** | First full factorial test of {sample size} × {evaluation protocol} on val-test gap magnitude |

**Benchmarks for context**:

| Method | Test EM |
|--------|---------|
| GEPA (Qwen3-8B thinking) | 62.3% |
| GigaEvo best (Run H) | 61.3% |
| GigaEvo seed ddce37b4 | 60.0% |
| MIPROv2 | 55.3% |
| GRPO | 43.3% |
| Baseline | 42.3% |

**Val-test gap reference data (all prior runs and this experiment)**:

| Run | Val protocol | Val N | Val EM (frontier) | Test EM | Gap | Notes |
|-----|-------------|-------|-------------------|---------|-----|-------|
| seed ddce37b4 | Fixed | 300 | 62.7% | 60.0% | 2.7pp | Gen 0; intrinsic gap |
| K (nlp ctrl) | Fixed | 300 | 66.33% | 60.00% | 6.33pp | Default prompts; primary anchor for Run O |
| H (p1p2 best) | Fixed | 300 | ~71% | 61.33% | ~9.7pp | ASI formatting; upper bound for fixed-300 range |
| L (nlp-1) | Rotating | 300 | 68.00% | 59.33% | 8.67pp | NLP prompts; external reference for Run R |
| M (nlp-2) | Rotating | 300 | 70.67% | 57.00% | 13.67pp | NLP prompts; external reference for Run R |
| N (nlp-3) | Rotating | 300 | 69.67% | 61.00% | 8.67pp | NLP prompts; external reference for Run R |
| **O** | **Fixed** | **300** | **TBD** | **TBD** | **TBD** | Control cell |
| **R** | **Rotating** | **300** | **TBD** | **TBD** | **TBD** | Rotation-only cell; default prompts |
| **Q** | **Fixed** | **600** | **TBD** | **TBD** | **TBD** | Size-only cell |
| **P** | **Rotating** | **600** | **TBD** | **TBD** | **TBD** | Compound cell |

**Scientific context**: The 2×2 design tests all four combinations of sample size and evaluation protocol simultaneously. The three pre-registered mechanistic hypotheses (H_winners_curse, H_regime_mismatch, H_mapelites) make distinct predictions about the 2×2 gap pattern, making this experiment interpretable regardless of outcome — every possible result advances understanding of the val-test gap mechanism and informs the correct approach for future experiments. This is the scientific payoff of factorial designs over one-factor-at-a-time comparisons.

---

*Ready for Reviewer-2's scrutiny.*

**— Dr. Elena Voss**
