# Experimental Design: P3 Crossover (num_parents=2) for HotpotQA Static Chain Evolution

**Date**: 2026-03-04
**Researcher**: Dr. Elena Voss (ML Research Methodologist)
**Status**: Revised — resubmitted for review

> Prior analysis: `docs/plans/2026-03-01-p3-crossover-analysis.md`
> Protocol reference: `docs/protocol/01_design.md`

---

## 1. Research Question

Does two-parent crossover (`num_parents=2`) improve best-of-run test Exact Match on HotpotQA static chain evolution beyond single-parent mutation (`num_parents=1`), when throughput is equalized at 8 mutations per generation, within 50 generations from the ddce37b4 warm start?

---

## 2. Hypotheses

**H0**: The best-of-run test EM of the `num_parents=2` condition (Run J) is within +/- 2.4 percentage points of the `num_parents=1` condition (Run I). Two-parent crossover provides no detectable benefit beyond single-parent mutation when throughput is held constant.

**H1**: The best-of-run test EM of `num_parents=2` (Run J) exceeds that of `num_parents=1` (Run I) by >= 3.0 percentage points. Two-parent crossover enables the mutation LLM to combine complementary strategies from distinct parent programs, producing offspring that escape the ddce37b4 fitness basin more effectively than single-parent mutation alone.

**Rationale for 3.0pp threshold**: The noise floor for N=1 comparisons on this benchmark is approximately 2.4pp, measured as the same-program retest noise from Run B (re-evaluating ddce37b4 twice on the same n=300 test set). This captures the irreducible EM sampling variance from LLM non-determinism and finite test set size, independent of any evolutionary run dynamics. A 3.0pp difference exceeds this noise floor and constitutes a scientifically meaningful improvement (approximately 9 additional correct answers out of 300 test samples).

**Secondary hypothesis (exploratory)**:
- **H1_stag**: `num_parents=2` reduces stagnation, defined as stretches of >= 10 consecutive generations with zero archive replacements.

---

## 3. Independent Variable(s)

| Variable | Control value | Treatment value(s) |
|----------|---------------|--------------------|
| `num_parents` | 1 (single-parent mutation) | 2 (two-parent crossover) |

This is a single-factor, 2-cell experiment. All other variables are held constant.

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test EM (gen 50) | Evaluate best-of-archive program on 300 held-out test samples at generation 50 | **Yes** |
| Val EM trajectory | Best-of-archive val EM recorded per generation (from Redis) | No |
| Test EM (gen 10, 25) | Evaluate best-of-archive at intermediate checkpoints | No |
| Val-test gap (gen 50) | |val EM - test EM| at generation 50 | No |
| Acceptance rate | Fraction of 8 mutants per generation that enter the archive, computed as the mean over generations 10-50 (excluding the ramp-up period where throughput is asymmetric between conditions) | No |
| Archive diversity | Number of distinct archive cells occupied at gen 50 | No |
| Stagnation episodes | Count and length of consecutive-gen stretches with 0 archive replacements | No |
| Mutation prompt size | Mean and max input tokens per generation (from mutation LLM logs) | No |

**Primary metric**: Best-of-archive test EM at generation 50, evaluated on the fixed 300-sample held-out test set.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| `seed_program` | ddce37b4 (val 62.7%, test 55.3%, thinking mode) | Identical warm start for both runs |
| `max_generations` | 50 | Standard horizon; sufficient for archive maturity |
| `max_elites_per_generation` | 8 | Matches prior experiments |
| `max_mutations_per_generation` | **8** | Equalizes throughput: num_parents=1 produces C(8,1)=8; num_parents=2 produces C(8,2)=28 capped at 8. Isolates crossover quality from throughput confound. |
| `primary_resolution` | 50 | Test eval at final generation |
| `mutation_mode` | rewrite | Required; diff mode is incompatible with num_parents=2 |
| `problem.name` | `chains/hotpotqa/static` | Fixed 300-sample validation set (P1 rotation OFF -- see Section 9) |
| `pipeline` | **Decision rule below** | Depends on NLP prompts experiment outcome |
| `prompts` | **Decision rule below** | Depends on NLP prompts experiment outcome |
| Chain LLM | Qwen3-8B (thinking mode, step_max_tokens 2048-4096) | Standard chain execution model |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 via vLLM | Standard mutation model |
| `llm_base_url` | Shared 4-server pool (assigned at launch) | Same infrastructure for both runs |
| Validation set | Fixed first 300 train samples | Static, not rotated |
| Test set | 300 held-out test samples | Identical across runs |
| Random failure sampling | Active (validate.py returns all failures; formatter samples 10 randomly per generation; `cache_handler = NO_CACHE`) | Inherited from cf0cfc1; prevents mutation overfitting to fixed failure subset |
| `parent_selector` | `AllCombinationsParentSelector` | Standard selector; handles num_parents=2 with built-in fallback for small archives |

### Baseline Selection Decision Rule (pipeline + prompts)

The `pipeline` and `prompts` settings depend on the outcome of the NLP prompts experiment (K/L/M/N, currently at gen ~24-26/50, expected completion ~2026-03-05 to 2026-03-06). The decision rule is:

| NLP prompts outcome | `pipeline` | `prompts` | Rationale |
|---------------------|-----------|-----------|-----------|
| **Treatment wins** (L/M/N mean test EM > K test EM by >= 3pp) | `hotpotqa_asi` | `hotpotqa` | NLP prompts are the validated superior config |
| **Suggestive** (1-3pp advantage for treatment) | `hotpotqa_asi` | `default` | ASI pipeline confirmed useful; NLP prompts unresolved, so use conservative default |
| **Null or negative** (treatment <= K or within noise) | `hotpotqa_asi` | `default` | ASI pipeline is the validated standard; default prompts are the safe baseline |

In all cases, `pipeline=hotpotqa_asi` is used because the ASI formatter is required for correct failure formatting (the repr-contamination bug makes `pipeline=standard` invalid when validate.py returns tuples). The only variable is whether `prompts=hotpotqa` or `prompts=default`.

**Both runs I and J use identical pipeline/prompts settings.** The decision is made once, applied uniformly.

---

## 6. Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | `llm_base_url` | Seed | Val set |
|-----|-------|------------|-----------|-----------|----------------|----------------|------|---------|
| I | Control (1-parent) | 14 | `hotpotqa_asi` | Decision rule (Section 5) | `chains/hotpotqa/static` | Shared pool (assigned at launch) | ddce37b4 | Fixed 300 |
| J | Treatment (2-parent) | 15 | `hotpotqa_asi` | Decision rule (Section 5) | `chains/hotpotqa/static` | Shared pool (assigned at launch) | ddce37b4 | Fixed 300 |

**Only difference between I and J**: `num_parents=1` vs. `num_parents=2`.

**Why Run I is a fresh control (not reusing K)**: Run K from the NLP prompts experiment uses a potentially different codebase version, different server allocation timing, and `prompts=default` which may not match the P3 baseline selection. Running I and J simultaneously on the same infrastructure eliminates temporal and infrastructure confounds. Additionally, Run I provides a second independent replication of the best configuration, adding statistical value given N=1 in prior experiments.

---

## 7. Sample Size Justification

**N=1 per condition (2 runs total).**

This is an acknowledged limitation. With N=1, we cannot compute within-experiment p-values or confidence intervals. Our justification:

1. **Compute constraint**: Each run consumes ~24-28 hours wall time on dedicated GPU servers. Running 4+ replications per condition (minimum for a t-test) would require 8+ runs = ~200+ GPU-hours and 1+ week wall time, which is not feasible given the shared infrastructure and research timeline.

2. **External reference distribution**: We have 4 valid prior num_parents=1 runs from the ddce37b4 seed (Runs B, D, F, H; E and G are excluded due to repr-contamination) that provide a reference distribution for the control condition. Run J can be compared against this distribution. If J exceeds the max of the 4-run distribution, that constitutes strong (though not definitive) evidence.

3. **Calibrated effect-size thresholds**: The noise floor is 2.4pp, derived from a same-program retest of ddce37b4 on the n=300 test set (Run B). This measures the irreducible EM sampling variance from LLM non-determinism and finite sample size — it is a *within-program* measurement, not inter-run spread, and is independent of the validity of any evolutionary run.

   **Reference distribution provenance**:
   - **Program**: seed program at commit `ddce37b4`, thinking mode, `step_max_tokens=2048`
   - **Experiment**: HotpotQA thinking-mode baseline (prior to P1×P2)
   - **Run label**: B, Redis DB: _(to be filled from run records)_
   - **Test set**: fixed 300-sample held-out set (same set used in all HotpotQA experiments)
   - **Evaluation 1**: test EM = 55.3% (eval 1 result; command: `bash experiments/hotpotqa_p1p2/run_test_eval.sh` or equivalent)
   - **Evaluation 2**: test EM = _(to be filled from run records)_
   - **Observed spread**: 2.4pp = |eval2 − eval1|
   - **Chain LLM**: Qwen3-8B, thinking mode ON (default chat template), `step_max_tokens=2048`
   - _(Note: exact run records should be verified against `experiments/hotpotqa_p1p2/03_plan.md` checkpoint log before P3 launch)_ For reference, the 95% confidence interval for a proportion at EM ~0.60, n=300 is +/-5.49pp (i.e., one SE ~2.80pp), so the 2.4pp threshold corresponds to roughly 0.44 standard errors — a moderately conservative filter that distinguishes signal from metric-level noise without demanding classical statistical significance. Effects are classified as:
   - **< 2.4pp**: Indistinguishable from metric sampling noise. No conclusion possible.
   - **2.4 - 5.0pp**: Suggestive. Exceeds retest noise but within ~1 SE. Warrants replication before claiming an effect.
   - **> 5.0pp**: Likely real. Exceeds retest noise by 2x and approaches ~2 SE.

4. **What N=1 CAN establish**: A clear positive or negative signal (> 5pp) that justifies or rules out further investment in crossover. **What N=1 CANNOT establish**: Precise effect sizes, interaction effects, or statistical significance at conventional alpha levels.

---

## 8. Statistical Test

**Test**: Calibrated effect-size comparison (not a formal hypothesis test).

**Significance threshold**: Not applicable in the traditional sense. Instead, pre-specified decision thresholds (Section 10) classify the observed effect size.

**How computed**:
1. At generation 50, evaluate the best-of-archive program from each run on the fixed 300-sample test set.
2. Compute the difference: delta = (Run J test EM) - (Run I test EM).
3. Classify delta against pre-specified thresholds (see Decision Gates, Section 10).
4. As a secondary check, compute where Run J's test EM falls in the distribution of the 4 valid prior num_parents=1 runs (B, D, F, H). If above the max of that distribution, the evidence is strengthened.

**Bootstrap sensitivity analysis (post-hoc, exploratory)**: If delta is in the suggestive range (2.4-5pp), resample the 300 test predictions with replacement (10,000 iterations) to estimate the variability of the EM difference. This does not address inter-run variance but quantifies test-set sampling noise.

---

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| **Throughput confound** | num_parents=2 with AllCombinationsParentSelector produces C(8,2)=28 candidate mutations vs. C(8,1)=8 for num_parents=1. If uncapped, Run J would generate 2x more mutations per generation, making it impossible to attribute gains to crossover vs. search volume. | **Both runs use `max_mutations_per_generation=8`**. At archive maturity, both runs generate exactly 8 mutations per generation. This isolates crossover quality from throughput. The cost is that Run J discards 20 of 28 potential crossover combinations, but this is necessary for a clean comparison. |
| **P1 x P3 fitness comparability** | With validation rotation (P1=ON), two parents may have been evaluated on different 300-sample subsets, making their fitness scores non-comparable. The mutation LLM sees both fitness values and may incorrectly weight the "better" parent. | **P1 is OFF for this experiment** (`problem.name=chains/hotpotqa/static`, fixed validation set). Both parents are always evaluated on the same 300 samples, making fitness scores directly comparable. |
| **Early-generation throughput deficit** | With archive_size=1 at gen 0, num_parents=2 produces C(1,2)=0 valid pairs. The AllCombinationsParentSelector fallback yields the single parent as a 1-element tuple, producing 1 mutation. Run I (num_parents=1) also produces 1 mutation at archive_size=1. But for archive_size 2-4, Run J produces fewer mutations than Run I (C(2,2)=1 < C(2,1)=2; C(3,2)=3 = C(3,1)=3; C(4,2)=6 > C(4,1)=4). | Accept the asymmetry. The ddce37b4 warm-start gives a strong initial program; archive should reach size 5+ within ~5-8 generations, after which both runs produce 8 mutations/gen (capped). The early-gen difference amounts to ~10-15 fewer total mutations for Run J, negligible over 50 generations (~400 mutations total). Monitor and report actual mutations per generation. **Verified fallback behavior**: When `AllCombinationsParentSelector` yields a 1-element parent list under `num_parents=2` config, the mutation operator handles it gracefully in rewrite mode. Specifically, `mutation.py build_prompt()` (lines 177-193) iterates over whatever parents it receives, building one block per parent and setting `count=len(parents)`. With 1 parent, the prompt reads "Mutate 1 parent programs" (slightly awkward grammar but semantically correct). The mutation LLM produces a rewrite of the single parent — functionally identical to `num_parents=1` behavior. No crash, no malformed prompt. Note: diff mode (lines 251-253) would raise `ValueError` on `len(parents) != 1`, but `mutation_mode=rewrite` is configured for this experiment, so that code path is never triggered. |
| **Parent similarity** | FitnessProportionalEliteSelector biases toward top-fitness programs. With num_parents=2, the top 2 programs are frequently paired. If they are structurally similar (common in early evolution from a single seed), crossover degenerates into near-duplication. | Monitor archive diversity (occupied cells) per generation. If Run J shows diversity collapse (fewer occupied cells than Run I by gen 25), this will be reported as a potential mechanism for crossover underperformance. No mid-run intervention planned; this is an observational diagnostic. |
| **Context length pressure** | Two-parent prompts are ~9,700 tokens (with ASI) vs. ~5,250 for single-parent. While within the 32k window, the additional context may degrade mutation LLM reasoning quality by leaving less headroom for thinking tokens. | Token budget analysis (Section 1 of prior analysis) shows ~19k tokens remaining for thinking + output, which is adequate. Monitor actual prompt sizes from mutation logs. If mean prompt size exceeds 12k tokens (indicating program growth beyond estimates), this will be flagged as a validity concern. |
| **Server allocation variance** | Different mutation LLM servers may have slightly different latency/throughput characteristics. | Both runs share the same 4-server pool and are launched simultaneously. Server assignment is logged. If one run consistently uses a slower server, this will be noted but is unlikely to affect EM quality (only wall time). |
| **Mutation prompt quality asymmetry** | The 2-parent prompt is not simply "more context" — it asks the mutation LLM to perform a qualitatively different cognitive task (combine two programs vs. improve one). The LLM may have been trained more heavily on single-improvement tasks than on merging tasks, introducing a systematic bias unrelated to the crossover mechanism itself. | Not addressable within current infrastructure. Acknowledged as a potential explanation for negative results. If Run J underperforms, this confound should be investigated via qualitative analysis of mutation outputs (do 2-parent mutations actually attempt cross-program synthesis, or do they ignore the second parent?). |
| **N=1 limitation** | Any observed difference could be due to random seed trajectory divergence rather than the intervention. | Acknowledged. This experiment is designed as a screening study. Decision gates (Section 10) are calibrated conservatively. Any positive result requires replication before publication. |

---

## 10. Stop Criteria and Decision Gates

### Early Termination

- **Crash with no recovery**: If a run crashes and cannot be resumed from the last checkpoint within 2 hours, the run is terminated. The surviving run continues; the experiment is degraded to single-arm.
- **Context overflow**: If mutation LLM logs show truncated prompts or error rates > 50% for 5+ consecutive generations in Run J, terminate Run J and investigate. This would indicate the token budget analysis was incorrect.
- **Zero mutations for 5+ consecutive generations**: Indicates a selector or configuration bug. Terminate and debug.

No early termination for poor fitness. Both runs execute for the full 50 generations regardless of val EM trajectory.

### Run Invalidation

A completed run is excluded from analysis if:
- Post-hoc inspection reveals a configuration error (wrong pipeline, wrong seed, wrong problem.name).
- The repr-contamination bug was active (pipeline=standard with tuple-returning validate.py).
- Redis corruption caused missing generation data for > 5 generations.

### Pre-registered Decision Gates

These thresholds are applied to the primary metric (delta = Run J test EM - Run I test EM) at generation 50:

| Classification | Criterion | Interpretation | Next action |
|---------------|-----------|----------------|-------------|
| **POSITIVE** | delta >= +3.0pp AND Run J test EM >= 60.0% AND Run J acceptance rate >= Run I acceptance rate | Crossover produces higher-quality mutations. The 60% floor represents a meaningful improvement over the seed's test EM of 55.3% and approaches GEPA's 62.3% test EM, ensuring the gain is not an artifact of both runs collapsing. The acceptance rate check (mean over generations 10-50) confirms crossover is not merely noisier. | Replicate with 2 additional seeds. Then test throughput bonus (uncap to max_mutations=16 for num_parents=2). |
| **SUGGESTIVE** | +1.0pp <= delta < +3.0pp | Possible benefit, but within noise floor. Cannot distinguish from random trajectory divergence. | Run 2 additional replications (same seed, same config) to resolve ambiguity. |
| **NULL** | -2.4pp < delta < +1.0pp | No detectable effect. Crossover neither helps nor hurts. | Deprioritize crossover. Consider testing dedicated merge operator (explicit cross-hop instruction) as an alternative approach. |
| **NEGATIVE** | delta <= -2.4pp | Crossover hurts. Likely cause: context bloat degrades mutation LLM reasoning, or parent similarity produces degenerate offspring. | Investigate: (a) compare prompt sizes and mutation quality between runs; (b) test with reduced failure cases (5 per parent) to free context; (c) test with RandomParentSelector to increase parent diversity. |

### Secondary/Exploratory Analysis (no impact on primary verdict)

Stagnation analysis (H1_stag) is reported separately and does not influence the primary verdict classification above. Stagnation is defined as stretches of >= 10 consecutive generations with zero archive replacements.

| Metric | Comparison | Interpretation |
|--------|-----------|----------------|
| Max consecutive stagnation length | Run J vs. Run I | If Run J shows >= 5 fewer consecutive stagnation generations, this is suggestive evidence that crossover improves search diversity. Reported as an exploratory finding only. |
| Number of stagnation episodes | Run J vs. Run I | Directional comparison; no pre-registered threshold. |

This analysis is exploratory. A favorable stagnation result with a NULL primary verdict does **not** upgrade the classification to SUGGESTIVE. The decision gates are based solely on the primary metric (test EM delta).

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| GPU hours (mutation LLM) | ~48h total (2 runs x ~24h; 8 mutations/gen x ~3 min/mutation x 50 gens = ~20h active + overhead) |
| GPU hours (chain LLM) | ~40h total (2 runs x ~5 min/validation x 50 gens = ~8h active + mutation candidate eval) |
| Wall time | ~24-28h per run (runs execute in parallel; total wall time ~28h) |
| Redis DBs used | 2 (DB 14 for Run I, DB 15 for Run J) |
| Test evaluation | 2 evaluations x ~5 min each = ~10 min (negligible; run at gen 50 only unless intermediate checkpoints needed) |
| Mutation servers | 2 of 4 available (1 per run, from shared pool) |
| Chain servers | 2 of 4 available (1 per run, from shared pool) |

---

## 12. Open Questions / Risks

1. **Baseline selection is pending.** The pipeline/prompts configuration depends on the NLP prompts experiment (K/L/M/N), which is at gen ~24-26/50 as of 2026-03-04. Expected completion: 2026-03-05 to 2026-03-06. The decision rule in Section 5 is unambiguous, but if the NLP experiment is invalidated (e.g., by a newly discovered bug), the default fallback is `pipeline=hotpotqa_asi, prompts=default`.

2. **AllCombinationsParentSelector fallback behavior at archive_size=1 has not been empirically verified on this codebase version.** The prior analysis documents the expected behavior (yields single parent), but a preflight dry-run is required before launch. This is a Phase 3 (pre-launch) checklist item, not a design blocker.

3. **Program growth beyond estimates.** The token budget analysis assumes evolved programs are ~2,100 tokens (based on ddce37b4). After 50 generations of evolution, programs may grow to 3,000+ tokens each. With 2 parents, this adds ~1,800 tokens to the prompt. The budget has headroom for this (~19k available), but actual sizes must be monitored. If programs from the NLP experiment (gen 50) exceed 12,000 chars (~3,000 tokens), the feasibility assessment should be re-run before P3 launch.

4. **Interaction with random failure sampling.** Random failure sampling (cf0cfc1) means each generation sees a different random subset of 10 failures. With num_parents=2, each parent's failure context is sampled independently. The two failure sets are **not** deduplicated in the current implementation — when parents share many failures (likely in early evolution from a common seed), the mutation LLM may see near-duplicate examples across the two parent blocks, wasting context without adding information. Deduplication is a potential optimization for follow-up but is not implemented for this experiment; the current behavior is accepted as-is and applies uniformly to all 2-parent mutations in Run J. The actual number of unique failures across both parent blocks will be monitored from mutation logs.

5. **No formal statistical power.** With N=1, there is a non-trivial probability (~30-40%, estimated from prior run variance) that a true 3pp effect will fall in the "suggestive" or "null" band due to random trajectory noise. The experiment is designed as a screening study, not a definitive test. This is an acceptable trade-off given compute constraints, but must be stated transparently in any write-up.

6. **Baseline selection may place both runs at a suboptimal fitness plateau.** If the NLP prompts experiment later confirms that `prompts=hotpotqa` is beneficial (e.g., a suggestive 1-3pp advantage that fell short of the "treatment wins" threshold), both P3 runs will use `prompts=default` — potentially a lower fitness plateau where the fitness landscape may behave differently than at the frontier. This does not invalidate the within-experiment comparison (both runs use identical settings), but limits the generalizability of the result: crossover effects observed at a lower plateau may not transfer to a higher one, and vice versa.

---

## Appendix A: Pre-Launch Checklist (for Phase 3)

- [ ] NLP prompts experiment (K/L/M/N) completed and analyzed; baseline selection rule applied
- [ ] Dry-run gen 0 with `num_parents=2` on a scratch Redis DB; confirm >= 1 mutation generated. Specifically verify that with archive_size=1, the AllCombinationsParentSelector fallback yields a 1-element parent list and `build_prompt()` produces a valid 1-parent rewrite prompt (no crash, no malformed output). Inspect the generated prompt text to confirm it reads "Mutate 1 parent programs" and contains a single parent block.
- [ ] Verify `mutation_mode=rewrite` in config
- [ ] Verify `max_mutations_per_generation=8` for both runs
- [ ] Verify `problem.name=chains/hotpotqa/static` (not static_r) for both runs
- [ ] Verify `prompts_dir: ${prompts.dir}` is present in `evolution_context` block of pipeline YAML (critical config bug fix 920c975)
- [ ] Flush Redis DBs 14, 15
- [ ] Kill any stale exec_runner workers from prior runs
- [ ] Verify mutation server and chain server availability (2 + 2 free)
- [ ] Extract actual token counts from NLP experiment gen-50 mutation logs; confirm 2-parent prompt fits within 13k input tokens
- [ ] Update launch script and watchdog with Run I/J PIDs and DB numbers

---

## Appendix B: Relationship to Prior Experiments

| Experiment | Runs | Status | Relevance to P3 |
|-----------|------|--------|-----------------|
| HotpotQA thinking-mode baseline | B, D | Complete | Established ddce37b4 seed (val 62.7%); provides reference distribution points for num_parents=1 |
| P1xP2 factorial | E, F, G, H | Complete (E+G invalid due to repr bug; F+H valid, N=1/cell) | F+H validated ASI pipeline; informed pipeline choice for P3 |
| NLP prompts | K, L, M, N | In progress (gen ~24-26/50) | Determines prompts setting (default vs. hotpotqa) for P3 baseline |
| **P3 crossover** | **I, J** | **This experiment** | First test of num_parents=2 on HotpotQA |

**GEPA comparison benchmarks** (Qwen3-8B, thinking mode):

| Method | Test EM |
|--------|---------|
| GEPA | 62.3% |
| MIPROv2 | 55.3% |
| GRPO | 43.3% |
| Baseline | 42.3% |
| GigaEvo seed (ddce37b4) | 55.3% (test); 62.7% (val) |
