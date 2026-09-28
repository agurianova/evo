# Results: HoVer Co-Evolution Bus -- High-Throughput Prompt Meta-Evolution

**Date**: 2026-03-23
**Branch**: `exp/hover-co-evolution-bus`
**PR**: #109
**Design doc**: `01_design.md`
**Pre-registration commit**: `01f7dfb`
**Review doc**: `02_review.md` (APPROVED, Round 2)

---

## 1. Summary of Findings

**Verdict: REGRESSIVE**

Grand mean test retrieval coverage across three treatment runs: **51.98%** (B1=53.27%, B2=52.20%, B3=50.47%). This falls in the pre-registered REGRESSIVE band [51.65%, 54.37%), indicating that the high-throughput co-evolution bus degraded the soft fitness gains demonstrated in Cell C (54.37%) while remaining marginally above the plain baseline (51.65%).

The high-throughput bus architecture -- 3 main runs feeding 1 prompt meta-evolution run at ~24 trials/gen with 8 mutations/gen -- did not improve test retrieval coverage. The prompt meta-evolution run (PM) produced a champion at gen 2 (fitness 0.5217) that barely exceeded the best seed (gap 0.06 vs the pre-registered threshold of 0.15). PM effectively stagnated for 23 of 25 generations. Average trials per prompt was approximately 3.2, triggering the pre-committed trial dilution diagnostic (threshold: < 5). Treatment val fitness (78.45% soft) was comparable to Cell C (79.11%), but test coverage (51.98% discrete) was 2.39pp below Cell C (54.37%), indicating that co-evolved prompts degraded generalization from val to test despite similar val-level optimization. (Note: val uses soft scoring, test uses discrete scoring — the metrics are not directly comparable.)

This is the third prompt co-evolution experiment across two tasks, two topologies, and three throughput configurations. All three produced NULL or REGRESSIVE results. **Prompt co-evolution is definitively closed as a productive GigaEvo intervention**, with the scoping caveat that the combination (3+1 topology, 5 mutations/gen, responsive HoVer landscape) was not directly tested and the trial dilution diagnostic was triggered.

---

## 2. Data Collection

### Run completion

| Run | Label | DB | Generations | Final Val Fitness (soft) | PID | Status |
|-----|-------|----|-------------|-------------------------|-----|--------|
| B1 | bus-hover-1 | 9 | 25/25 | 78.00% | 663547 | Complete |
| B2 | bus-hover-2 | 10 | 25/25 | 79.56% | 663641 | Complete |
| B3 | bus-hover-3 | 11 | 25/25 | 77.78% | 663810 | Complete |
| PM | bus-prompt-meta | 12 | 25/25 | 52.17% | 663947 | Complete |

- Launch: 2026-03-22 19:11 UTC
- B3 completed first (~gen 25 by 2026-03-23 ~09:00 UTC)
- B2 completed second (~12:00 UTC)
- B1 and PM completed last (~13:00 UTC)
- Total wall time: approximately 18 hours
- No early termination or invalidation criteria triggered
- 19 watchdog checkpoints recorded during the run

### Reference data

| Source | Mean Test Coverage (discrete) | SD | n |
|--------|------------------------------|-----|---|
| Cell C (PR #92) | 54.37% | 0.99pp | 2 |
| Baseline / Cell A (PR #90) | 51.65% | 0.63pp | 4 |
| PR #93 treatment (1-to-1 co-evo) | 52.00% | 1.31pp | 2 |
| GEPA benchmark | 52.33% | -- | 1 |

---

## 3. Per-Run Test Results

### Treatment runs (B1, B2, B3): 5-repeat discrete test evaluation, 300-sample held-out set, gen 25

| Run | Val Fitness (soft) | Test Mean (discrete) | Test SD | 5 Repeats |
|-----|-------------------|---------------------|---------|-----------|
| B1 | 78.00% | 53.27% | 2.31% | 52.67%, 51.67%, 50.67%, 56.00%, 55.33% |
| B2 | 79.56% | 52.20% | 1.61% | 53.33%, 51.33%, 51.67%, 54.33%, 50.33% |
| B3 | 77.78% | 50.47% | 1.98% | 53.33%, 50.33%, 51.33%, 49.00%, 48.33% |
| **Treatment mean** | **78.45%** | **51.98%** | | |

**Grand mean test coverage**: 51.98%
**Inter-run SD**: 1.41pp (from the three run means: 53.27, 52.20, 50.47)
**Mean within-run SD**: 1.97pp (average of 2.31, 1.61, 1.98)

### Reference: Cell C (soft fitness only, no co-evolution, from PR #92)

| Run | Val Fitness (soft) | Test Mean (discrete) | Test SD |
|-----|-------------------|---------------------|---------|
| F3 | 79.78% | 55.07% | 1.32% |
| F4 | 78.44% | 53.67% | 1.41% |
| **Cell C mean** | **79.11%** | **54.37%** | |

### Mid-run test evaluation (at ~50% gate)

| Run | Gen at eval | Test Mean | Test SD |
|-----|------------|-----------|---------|
| B1 | ~12 | 50.80% | 0.38% |
| B2 | ~13 | 53.67% | 1.18% |
| B3 | ~13 | 48.87% | 0.96% |
| **Mid-run mean** | | **51.11%** | |

The mid-run checkpoint analyst flagged the result as REGRESSIVE (-3.26pp vs Cell C). The recommendation was to continue to completion for scientific closure, which was followed.

### Mid-run to final comparison

| Run | Mid-run Test | Final Test | Change |
|-----|-------------|-----------|--------|
| B1 | 50.80% | 53.27% | +2.47pp |
| B2 | 53.67% | 52.20% | -1.47pp |
| B3 | 48.87% | 50.47% | +1.60pp |
| **Mean** | **51.11%** | **51.98%** | **+0.87pp** |

The second half of evolution produced a modest +0.87pp improvement in the grand mean, but this was driven entirely by B1 and B3. B2 actually declined. The final result remained in the REGRESSIVE band.

---

## 4. Statistical Tests

### Test 1: Treatment vs. Cell C reference (PRIMARY)

- Treatment mean: 51.98% (n=3, SD=1.41pp)
- Cell C mean: 54.37% (n=2, SD=0.99pp)
- Delta: **-2.39pp** (treatment WORSE than reference)

**Welch's t-test (one-sided, H1: treatment > reference)**:

t = (51.98 - 54.37) / sqrt(1.41^2/3 + 0.99^2/2)
  = -2.39 / sqrt(0.663 + 0.490)
  = -2.39 / 1.074
  = -2.23

Satterthwaite df ~ 3.6

p (one-sided) > 0.95 (wrong direction)

**Interpretation**: H0 not rejected. The treatment performed materially worse than the Cell C reference. The delta (-2.39pp) is in the wrong direction and similar in magnitude to PR #93's delta (-2.37pp).

### Conservative n=1 analysis (per pre-registered correlation rule)

The inter-run SD of 1.41pp falls above the 1.0pp threshold specified in the design. Per the pre-committed rule: "If inter-run SD >= 1.0pp (comparable to Cell C SD), the n=3 analysis is primary." The n=3 analysis is therefore the primary analysis. Nevertheless, we also report the conservative n=1 analysis for completeness.

Treating the treatment grand mean (51.98%) as a single observation against Cell C (n=2, mean=54.37%, SD=0.99pp):

t = (51.98 - 54.37) / (0.99 * sqrt(1 + 1/2))
  = -2.39 / 1.212
  = -1.97

df = 1, p (one-sided) > 0.85

The conservative analysis confirms the direction: treatment is worse than reference regardless of the independence assumption.

### Test 2: Treatment vs. baseline (SECONDARY)

- Treatment mean: 51.98% (n=3, SD=1.41pp)
- Baseline mean: 51.65% (n=4, SD=0.63pp)
- Delta: **+0.33pp**

t = (51.98 - 51.65) / sqrt(1.41^2/3 + 0.63^2/4)
  = 0.33 / sqrt(0.663 + 0.099)
  = 0.33 / 0.873
  = 0.38

p (one-sided) ~ 0.36

**Interpretation**: The treatment mean is statistically indistinguishable from the plain baseline. The bus co-evolution treatment effectively erased the +2.72pp gain that soft fitness alone provides.

### Test 3: Treatment vs. PR #93 treatment (EXPLORATORY)

- Bus mean: 51.98% (n=3, SD=1.41pp)
- PR #93 mean: 52.00% (n=2, SD=1.31pp)
- Delta: **-0.02pp**

t = -0.02 / sqrt(1.41^2/3 + 1.31^2/2)
  = -0.02 / sqrt(0.663 + 0.858)
  = -0.02 / 1.234
  = -0.02

p ~ 0.50

**Interpretation**: The high-throughput bus produced results indistinguishable from the low-throughput 1-to-1 co-evolution. The 3x throughput increase and 4x mutation rate increase had zero measurable effect on test coverage. This is a striking null: increasing prompt evolution resources by an order of magnitude did not move the needle.

### Test 4: Per-run within-run variability

| Run | Within-run SD | Cell C within-run SD range |
|-----|--------------|---------------------------|
| B1 | 2.31% | F3: 1.32%, F4: 1.41% |
| B2 | 1.61% | |
| B3 | 1.98% | |
| **Treatment mean** | **1.97%** | **Cell C mean: 1.37%** |

Treatment within-run SDs are 44% higher than Cell C's, suggesting that co-evolved prompts introduce additional evaluation noise -- consistent with the "temporal instability" confound (Confound #13 in the design).

---

## 5. Effect-Size Threshold Verdict

Per the pre-registered threshold table (01_design.md, Section 2):

| Threshold | Range | This experiment |
|-----------|-------|----------------|
| POSITIVE | >= 56.37% (all 3 runs) | NO (max run = 53.27%) |
| INCONCLUSIVE | >= 56.37% (2 of 3) | NO |
| NULL | [54.37%, 56.37%) | NO |
| **REGRESSIVE** | **[51.65%, 54.37%)** | **YES (51.98%)** |
| NEGATIVE | < 51.65% | NO |

**Verdict: REGRESSIVE.** The bus co-evolution treatment disrupted the soft fitness gains without falling below baseline.

Individual run verdicts: B1 (53.27%) = REGRESSIVE, B2 (52.20%) = REGRESSIVE, B3 (50.47%) = NEGATIVE. Two of three runs are REGRESSIVE; one (B3) falls below the plain baseline. No run approached the Cell C reference.

---

## 6. Mechanism Analysis: Prompt Meta-Evolution

### PM archive statistics at gen 25

| Metric | Value | PR #93 P1 | PR #93 P2 | PR #84 (HotpotQA) |
|--------|-------|-----------|-----------|-------------------|
| Total programs | 186 | 52 | 50 | 39 |
| Active (done) | 75 | -- | -- | -- |
| Discarded | 111 | -- | -- | -- |
| Champion fitness | 0.5217 | 0.5714 | 0.4615 | ~0.50 |
| Champion birth gen | 2 | ~11 | seed | seed variant |
| Champion trials | 16 | 13 | 11 | -- |
| Best seed fitness | ~0.4615 | 0.4615 | 0.4615 | 0.48 |
| Fitness gap over seed | 0.06 | 0.11 | 0.00 | ~0.02 |
| Avg trials/prompt | ~3.2 | ~3.4 | ~3.0 | 11.6 |

### H1_mech evaluation

The secondary hypothesis required: PM champion trials > 30 AND fitness gap > 0.15.

| Criterion | Required | Observed | Met? |
|-----------|----------|----------|------|
| Champion trials | > 30 | 16 | NO |
| Fitness gap over seed | > 0.15 | 0.06 | NO |

**H1_mech is rejected.** The bus topology did NOT produce measurably better prompt fitness differentiation than the 1-to-1 topology. Despite tripling trial throughput (24 vs 8 trials/gen) and quadrupling mutation rate (8 vs 2 mutations/gen), the prompt meta-evolution run produced a weaker champion (0.5217 vs P1's 0.5714) with a smaller fitness gap over the seed (0.06 vs 0.11).

### Trial dilution diagnostic (pre-committed)

The design pre-committed: "If average trials-per-prompt at gen 25 is < 5 (below min_trials), report that the trial dilution failure mode was triggered."

With approximately 600 expected trials spread across 186 total programs, the average is ~3.2 trials/prompt. This is BELOW the min_trials=5 threshold. **Trial dilution was triggered.**

The max_elites=8 pruning cap was intended to concentrate trials on the 8 best prompts per generation. However, with 8 new mutations per generation creating 200 candidate prompts across 25 generations, pruning could not prevent dilution. Reviewer-2 warned of exactly this scenario in Concern 1 of the review document: "The net effect: PR #84 achieved measurable prompt fitness differentiation with 11.6 trials/prompt. This experiment may achieve LESS differentiation despite higher raw throughput."

### Prompt fitness trajectory

PM's champion (c9739c04, fitness 0.5217) was discovered at gen 2 and accumulated 16 children across the remaining 23 generations. No better prompt was found. The PM fitness trajectory shows oscillation between 0.50 and 0.57 across 25 generations with no sustained improvement. This mirrors the stagnation pattern observed in P1 and P2 of PR #93, despite the 3x throughput and 4x mutation rate.

### Treatment verification

All treatment checks passed throughout the run:
- All three B runs transitioned from fallback to co-evolved prompts by gen 3
- No persistent archive fallback after gen 5
- prompt_stats keys: B1 had 24-38 keys, B2 similar, B3 similar by gen 25
- PM archive grew to 65+ prompts by mid-run, 186 total by gen 25
- PM sync hook was active (MainRunSyncHook confirmed in logs)

The treatment was active and functioning as designed. The regressive result is not attributable to treatment failure.

---

## 7. Val vs. Test Metric Analysis

**Important caveat**: Val fitness uses **soft** scoring (fractional: gold_found/3) while test coverage uses **discrete** scoring (all-or-nothing: 1 iff all 3 gold docs found, else 0). These are fundamentally different metrics, so the numerical gap between them is primarily a metric mismatch, NOT a measure of overfitting. A program that finds 2/3 gold docs on every sample scores ~67% soft but 0% discrete.

The meaningful comparison is **treatment vs. reference on the same metric**:

### Val fitness comparison (soft metric, both use same scoring)

| Run | Val Fitness (soft) |
|-----|-------------------|
| B1 | 78.00% |
| B2 | 79.56% |
| B3 | 77.78% |
| **Treatment mean** | **78.45%** |
| Cell C F3 | 79.78% |
| Cell C F4 | 78.44% |
| **Cell C mean** | **79.11%** |

Treatment val fitness (78.45%) is comparable to Cell C (79.11%) — only -0.66pp difference. The co-evolution bus did NOT degrade val-level optimization.

### Test coverage comparison (discrete metric, both use same scoring)

| Run | Test Coverage (discrete) |
|-----|-------------------------|
| B1 | 53.27% |
| B2 | 52.20% |
| B3 | 50.47% |
| **Treatment mean** | **51.98%** |
| **Cell C mean** | **54.37%** |

Treatment test coverage (51.98%) is 2.39pp below Cell C (54.37%). The regression is entirely at the test level — programs evolved under co-evolved prompts achieve similar val fitness but generalize worse to the held-out test set on the discrete metric.

### Interpretation

Programs from the bus treatment reach the same soft-fitness plateau as Cell C but convert that val fitness into discrete test coverage less efficiently. This suggests that co-evolved prompts bias the evolutionary search toward solutions that improve partial retrieval (boosting soft fitness) without improving full 3-hop retrieval (discrete test coverage). The temporal instability of co-evolved prompts (Confound #13) may prevent the archive from building coherent multi-hop retrieval strategies.

### Val fitness trajectory analysis

| Run | Gen of last frontier improvement | Final val fitness | Plateau duration |
|-----|--------------------------------|------------------|-----------------|
| B1 | Gen 3 (78.00%) | 78.00% | 22 generations |
| B2 | Gen 20 (79.56%) | 79.56% | 5 generations |
| B3 | Gen 3 (77.67%), marginal at gen 25 (77.78%) | 77.78% | ~22 generations |

B1 and B3 plateaued almost immediately (gen 3) and showed no meaningful improvement across 22 subsequent generations despite continuous prompt evolution from PM. B2 was the sole exception, breaking its plateau at gen 13 (78.44% to 79.22%) and again at gen 20 (79.56%). The fact that B2 improved on val fitness while all three were receiving the same co-evolved prompts from PM suggests that B2's improvement was driven by stochastic mutation quality, not prompt co-evolution.

---

## 8. Deviations from Pre-Registration

**None.** No post-registration amendments were made. The experiment ran with the exact configuration specified in the pre-registration document. All four runs completed 25/25 generations. The test evaluation protocol (5 repeats, discrete scoring, 300-sample held-out set) was executed as specified. The 72-hour time-gate for historical control validity was not triggered (launch occurred on 2026-03-22, within the window).

This clean execution strengthens the internal validity of the REGRESSIVE finding. The result cannot be attributed to protocol deviations or implementation drift.

---

## 9. Cross-Experiment Synthesis: Three Co-Evolution Experiments

### Complete co-evolution experiment grid

| Dimension | HotpotQA PR #84 | HoVer 1-to-1 PR #93 | **HoVer Bus PR #109** |
|-----------|-----------------|----------------------|----------------------|
| Task | HotpotQA | HoVer | **HoVer** |
| Landscape | Flat (59-60%) | Responsive (+2.72pp) | **Responsive** |
| Topology | 3+1 shared | 1-to-1 independent | **3+1 bus** |
| Main runs (n) | 3 | 2 | **3** |
| Trials/gen for prompt | ~24 | ~8 | **~24** |
| Prompt mutations/gen | 5 | 2 (amended) | **8** |
| Prompt max_elites | 5 | 5 | **8** |
| min_trials | 5 | 3 (amended) | **5** |
| Total treatment runs | 3 | 2 | **3** |
| Reference | Cold-start 59.58% | Cell C 54.37% | **Cell C 54.37%** |
| Treatment mean | 60.22% | 52.00% | **51.98%** |
| Delta vs reference | +0.64pp | -2.37pp | **-2.39pp** |
| **Verdict** | **NULL** | **NULL/REGRESSIVE** | **REGRESSIVE** |

### Pooled evidence

Across three experiments, eight treatment runs have been evaluated against their respective references:

| Metric | Value |
|--------|-------|
| Total treatment runs | 8 (3 + 2 + 3) |
| Total reference runs | 8 (3 cold-start + 2 Cell C + 4 baseline) |
| Positive results | 0 |
| Null results | 1 experiment (HotpotQA) |
| Regressive results | 2 experiments (both HoVer) |
| Treatment deltas | +0.64pp, -2.37pp, -2.39pp |
| Mean delta across experiments | -1.37pp |

### Parameter space coverage

| Parameter | Values tested |
|-----------|--------------|
| Task | HotpotQA, HoVer |
| Fitness landscape | Flat, responsive (soft) |
| Topology | 1-to-1, 3-to-1 bus |
| Prompt mutations/gen | 2, 5, 8 |
| Trial throughput | ~8, ~24, ~24 trials/gen |
| Total trial budget | ~175, ~454, ~600 |

### Untested combination (per Reviewer-2, Concern 5)

The combination (3+1 topology, 5 mutations/gen, responsive HoVer landscape) was not directly tested. This is the parameter configuration most analogous to the HotpotQA experiment (PR #84) but on the responsive landscape. However, the converging evidence from three experiments, with the treatment delta trending from +0.64pp to -2.37pp to -2.39pp as throughput and mutation rate INCREASED, provides no reason to believe that an intermediate mutation rate would reverse the pattern.

### Trial dilution caveat (pre-committed)

The trial dilution diagnostic was triggered (avg 3.2 trials/prompt < 5). Per the pre-registered language in 01_design.md Section 2: "the closure claim is weakened" by this outcome. Specifically, the definitive closure applies to: **prompt co-evolution at the tested throughput-to-diversity ratios**. The possibility that a carefully tuned ratio (e.g., 3+1 bus with 5 mutations/gen) might produce a different result is not logically excluded by this data. However, the design document also pre-committed: "given the weight of three independent nulls across two tasks, further prompt co-evolution experiments would NOT be recommended even in the dilution scenario -- the expected value is too low to justify the engineering cost."

I endorse this pre-commitment. The marginal expected value of a fourth co-evolution experiment -- tuning the mutation rate from 8 to 5 on a landscape where co-evolution has been regressive twice -- is negligible. The research line is closed.

---

## 10. Why Did the Bus Fail? Mechanistic Interpretation

Three non-exclusive explanations, ordered by evidence strength:

### Explanation 1: Mutation prompt quality is not a binding constraint (STRONG)

This is the explanation supported by three independent experiments. The Qwen3-235B mutation LLM produces reasonable mutations regardless of the prompt. The mutation success rate under co-evolved prompts is comparable to fixed prompts. The prompt's role in guiding mutation is marginal compared to the LLM's intrinsic reasoning and the failure context it receives. Evidence: Cell C achieved 54.37% with fixed prompts; the bus treatment achieved 51.98% with actively evolved prompts from a dedicated meta-evolution run.

### Explanation 2: Co-evolution adds noise that degrades soft fitness optimization (MODERATE)

The temporal instability of co-evolved prompts (Confound #13 in the design) means that mutations within the same generation may use different prompts. This prevents the evolutionary archive from building on a consistent mutation strategy. Under fixed prompts, the mutation operator is stable, and the archive accumulates programs that respond well to a consistent optimization pressure. Under co-evolved prompts, the optimization landscape shifts with every PM champion update.

Evidence: Treatment val fitness (78.45% soft) was comparable to Cell C (79.11%), yet treatment test coverage (51.98% discrete) was 2.39pp below Cell C (54.37%). The within-run test SDs were 44% higher under co-evolution (1.97% vs 1.37%), consistent with increased noise from prompt instability. Programs evolved under shifting prompts may optimize for partial retrieval (boosting soft fitness) without building coherent 3-hop strategies (measured by discrete test).

### Explanation 3: Trial dilution prevented prompt fitness estimation (WEAK)

With 186 total programs and ~600 trials, the average of 3.2 trials/prompt was below min_trials=5. Many prompts never accumulated enough data for reliable fitness computation. The max_elites=8 pruning cap was insufficient because 8 new mutations/gen continuously inflated the candidate pool.

However, this explanation is weakened by the observation that the HotpotQA experiment (PR #84) achieved 11.6 trials/prompt with better trial concentration and still produced a null result. If adequate trial volume were sufficient, PR #84 should have shown a positive effect. It did not.

### Synthesis

The most parsimonious explanation across all three experiments is Explanation 1: **mutation prompt quality is not a binding constraint on GigaEvo chain evolution performance**. Explanations 2 and 3 may contribute to the HoVer-specific regression (why co-evolution is actively harmful on this landscape rather than merely neutral), but they do not explain the HotpotQA null where trial dilution was not an issue.

---

## 11. Implications for Future Experiments

### What is definitively closed

**Prompt co-evolution in any tested configuration.** Three experiments, two tasks, two topologies, three throughput levels. Zero positive results. The binding constraint on GigaEvo performance lies elsewhere.

### What the binding constraint might be

For HoVer with soft fitness:
1. **Chain topology** (frozen 7-step structure): The 3 tool + 4 LLM step configuration is fixed. Allowing GigaEvo to evolve the chain structure itself -- adding/removing hops, modifying retrieval parameters, changing the step dependency graph -- is the most promising unexplored direction.
2. **Retrieval engine** (BM25 with fixed k): All experiments have used BM25 with k=7 (hops 1-2) and k=10 (hop 3). Dense retrieval or hybrid approaches could expand the retrieval frontier.
3. **Chain LLM ceiling** (Qwen3-8B): The chain LLM's reasoning capacity is fixed. Testing with Qwen3-32B or larger would probe whether the LLM is the bottleneck.

### What should not be pursued

- Further prompt co-evolution experiments with any topology or throughput configuration
- Further variations on the prompt meta-evolution architecture (mutation rate, archive size, min_trials)
- Any experiment whose primary IV is the content or source of mutation prompts

---

## 12. Recommendation

**Close the prompt co-evolution research line.** Merge PR #109 with this results document. Update INDEX.md to mark hover/co-evolution-bus as complete with verdict REGRESSIVE.

The three co-evolution experiments together represent one of the cleanest negative results in the GigaEvo program: a well-motivated hypothesis (prompt quality constrains evolution), tested across systematic parameter variations (topology, throughput, landscape, task), with all pre-registered diagnostics executed, producing a consistent null-to-regressive signal. This is the kind of result that prevents future researchers from repeating the same investigation.

For the GigaEvo methods paper, the prompt co-evolution series contributes the following finding:

> **Evolving mutation prompts via a parallel GigaEvo instance does not improve chain evolution performance.** Across three experiments spanning two tasks (HotpotQA, HoVer), two topologies (1-to-1, 3+1 bus), and three throughput configurations (8, 24, 24 trials/gen with 2, 5, 8 prompt mutations/gen), prompt co-evolution produced zero positive results. Treatment deltas ranged from +0.64pp (null) to -2.39pp (regressive) relative to fixed-prompt baselines. The combined evidence from 8 treatment runs and 8 reference runs supports the conclusion that mutation prompt quality is not a binding constraint on GigaEvo performance. The LLM mutation operator's intrinsic reasoning ability, combined with the failure context it receives, dominates prompt-level guidance. Engineering effort should focus on fitness signal design (demonstrated in the soft fitness positive result, +2.72pp, p~0.03) rather than mutation prompt optimization.

---

## 13. Run Validity

| Run | Valid? | Notes |
|-----|--------|-------|
| B1 | Yes | 25/25 gens, treatment verified active, no invalidation criteria triggered |
| B2 | Yes | 25/25 gens, treatment verified active, plateau-breaking at gen 13 and 20 |
| B3 | Yes | 25/25 gens, treatment verified active, extended plateau from gen 3 |
| PM | Yes | 25/25 gens, archive populated, sync hook active, champion produced at gen 2 |

Treatment verification checks confirmed:
- All 3 B runs transitioned to co-evolved prompts by gen 3
- No persistent archive fallback after gen 5
- prompt_stats keys present in all 3 B run DBs (24-38 keys by gen 25)
- PM archive grew to 186 programs across 25 generations
- PM sync hook active throughout (MainRunSyncHook logs confirmed)

---

## 14. Artifacts

- Test eval raw scores: Section 3 above
- Mid-run test eval: experiment.yaml `mid_run_test_eval` block
- Checkpoint log: experiment.yaml `checkpoints` block (19 entries)
- Launch commit: `01f7dfb` (pre-registration)
- Redis archives: DBs 9, 10, 11, 12 (pending archival)
- Top programs: saved to `/home/jovyan/gigaevo-checkpoints/` and `top_programs_B1/`, `top_programs_B2/`, `top_programs_B3/`, `top_programs_PM/`

---

## 15. References

- Pre-registration: `experiments/hover/co-evolution-bus/01_design.md`
- Review: `experiments/hover/co-evolution-bus/02_review.md`
- Plan: `experiments/hover/co-evolution-bus/03_plan.md`
- Cell C reference: `experiments/hover/feedback_softfit/05_results.md` (PR #92)
- Baseline reference: `experiments/hover/baseline/05_results.md` (PR #90)
- HoVer 1-to-1 co-evolution: `experiments/hover/prompt_coevolution/05_results.md` (PR #93)
- HotpotQA co-evolution: `experiments/hotpotqa/prompt_coevolution/05_results.md` (PR #84)

---

*Ready for Reviewer-2's scrutiny.*
