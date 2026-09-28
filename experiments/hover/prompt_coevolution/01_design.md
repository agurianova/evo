# Experimental Design: HoVer Prompt Co-Evolution with Soft Fitness

**Date**: 2026-03-20
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft -- awaiting Reviewer-2

---

## 1. Research Question

The HotpotQA prompt co-evolution experiment (PR #84) tested whether evolving mutation prompts via a parallel GigaEvo instance improves chain performance. The result was NULL: mean test EM 60.22% vs cold-start 59.58% (delta +0.64pp, p=0.28). However, this null was observed on a landscape where 28 consecutive runs had confirmed a 59-60% stagnation ceiling. Every intervention tested within the static-chain framework -- fitness metric, validation size, mutation prompts, crossover, retriever, feedback, mutation LLM, held-out validation, and prompt co-evolution itself -- produced NULL or NEGATIVE results. In that context, the prompt co-evolution null may reflect the landscape's unresponsiveness rather than a deficiency in the co-evolution mechanism.

The HoVer landscape tells a different story. The feedback_softfit experiment (PR #92) demonstrated that soft (fractional) fitness scoring breaks through the baseline ceiling: Cell C mean 54.37% vs baseline 51.65%, a +2.72pp gain (p~0.03). This is the first statistically significant positive result in the GigaEvo research program since thinking mode was adopted. Soft fitness provides a finer gradient by scoring partial document retrieval (0/3, 1/3, 2/3, 3/3) instead of binary all-or-nothing (0/1). The hypothesis driving this experiment is that on a landscape where the evolutionary signal is richer (soft fitness), prompt co-evolution may become effective where it previously was not.

The mechanistic argument is as follows. Soft fitness and co-evolved prompts address complementary deficits: soft fitness provides the evolutionary archive with a finer selection gradient (which programs survive and are selected for mutation), while co-evolved prompts provide the mutation operator with adaptive guidance (how to mutate the selected program). On HotpotQA's flat landscape, neither lever had room to operate. On HoVer's responsive landscape, the richer gradient may create headroom for adaptive mutation prompts to exploit.

**Primary research question**: Does co-evolving mutation prompts via a parallel GigaEvo instance, combined with soft fitness, improve HoVer test retrieval coverage relative to soft fitness alone (Cell C mean 54.37%, n=2)?

**Secondary research question**: Does the prompt run discover prompts whose mutation success rate exceeds that of the default fixed prompts? (Mechanism question -- tests whether prompt adaptation is measurable, even if chain performance does not improve.)

**Tertiary research question**: Is the HoVer landscape genuinely more responsive to prompt co-evolution than HotpotQA's? A null result here, combined with the HotpotQA null, would provide converging evidence that prompt co-evolution is ineffective regardless of landscape responsiveness.

---

## 2. Hypotheses

### Primary hypothesis: co-evolved prompts improve test coverage beyond soft fitness alone

**H0**: Co-evolved prompt runs with soft fitness produce test retrieval coverage (discrete, 300-sample held-out) indistinguishable from the soft-fitness-only reference (Cell C mean 54.37%, SD=0.99pp, n=2). Formally: mu_coevo <= 54.37%.

**H1**: Co-evolved prompt runs with soft fitness produce mean test retrieval coverage >= 56.37% (Cell C mean + 2.00pp), representing a meaningful improvement beyond soft fitness alone. The 2.00pp threshold is consistent with the significance thresholds pre-specified across all prior GigaEvo experiments.

**Effect size thresholds** (applied to the n=2 treatment mean):

| Co-evo mean test coverage | Verdict |
|---------------------------|---------|
| >= 56.37% (both runs) | **POSITIVE** -- co-evolution improves test coverage at >= 2pp above soft-fitness-only |
| >= 56.37% (one run only) | **INCONCLUSIVE** -- requires follow-up at n>=4 |
| [54.37%, 56.37%) | **NULL** -- within noise band of soft-fitness-only reference |
| [51.65%, 54.37%) | **REGRESSIVE** -- co-evolution degrades soft fitness gains (but still above baseline) |
| < 51.65% | **NEGATIVE** -- co-evolution destroys both soft fitness gains and baseline performance |

### Secondary hypothesis: prompt adaptation is measurable

**H0_mech**: The prompt run's champion at gen 25 has mutation success rate <= the success rate of the fixed default prompt (measured from the main run's early generations when fallback prompts are in use).

**H1_mech**: The prompt run's champion achieves a strictly higher mutation success rate than the fixed default prompt. Evaluated descriptively from Redis prompt stats. **Limitation**: Temporal autocorrelation (Confound #7 from HotpotQA design) inflates early-phase success rates regardless of intrinsic prompt quality. This was documented in the HotpotQA experiment and applies equally here.

### Comparison with HotpotQA null

The HotpotQA prompt co-evolution treatment mean was 60.22% vs reference 59.58% (delta +0.64pp). If the HoVer treatment delta is also < 2.00pp, the combined evidence (two independent NULLs across different tasks and landscapes) would strongly support the conclusion that prompt co-evolution is not a productive intervention for GigaEvo chain evolution.

---

## 3. Independent Variable(s)

| Variable | Control value | Treatment value |
|----------|---------------|-----------------|
| Mutation prompt source | Fixed (FixedDirPromptFetcher, `prompt_fetcher=fixed`, implicit default) | Co-evolved (GigaEvoArchivePromptFetcher, `prompt_fetcher=coevolved`) |

This is a single-factor experiment with one IV. Soft fitness is held constant (both treatment and reference use `problem.name=chains/hover/static_soft`). The treatment introduces a parallel prompt GigaEvo instance; the historical control (Cell C from feedback_softfit, PR #92) used fixed default prompts.

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test retrieval coverage at gen 25 (best-by-val, discrete) | 300-sample held-out test set; discrete scoring (all 3 gold docs = 1, else 0); thinking mode Qwen3-8B; 5 repeats per run | **YES -- primary** |
| Val coverage trajectory (gen 0-25) | Per-generation `valid_frontier_fitness` from Redis | Yes -- convergence diagnostic |
| Val-test gap | Best val soft fitness minus mean test discrete coverage | Yes -- overfitting diagnostic (note: metrics differ between val and test) |
| Birth-generation of best-by-val program | From Redis trajectory | No -- convergence speed |
| Prompt champion success rate | Bayesian fitness (Beta(1,3) posterior) of the prompt run's best program | No -- mechanism check |
| Prompt champion text | Qualitative: what did the evolved prompt converge to? | No -- exploratory |
| Prompt archive size and trial counts | Total programs in archive, total trials aggregated | No -- co-evolution health check |

**Primary metric**: Mean test retrieval coverage (discrete, 5-repeat average per run) at gen 25 for the treatment condition, compared against Cell C reference mean (54.37%).

**Test protocol**: 5 independent repeats of the full 300-sample test evaluation per run, identical to feedback_softfit protocol. Within-run SD from feedback_softfit ranged from 1.32-1.41pp.

**Critical**: All test evaluations use **discrete** retrieval coverage, identical to baseline and GEPA. Soft fitness affects evolution only.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Chain topology | 7-step fixed (3 tool, 4 LLM) | HoVer static mode; identical to all prior HoVer runs |
| **Test metric** | **Discrete retrieval coverage** (all 3 gold docs = 1, else 0) | Comparable to baseline, Cell C, and GEPA |
| **Evolutionary fitness** | **Soft** (fractional: gold_found/3 per sample) | Held constant -- both treatment and reference use soft fitness |
| `problem.name` | `chains/hover/static_soft` | Soft fitness variant; identical to Cell C |
| `pipeline` | `standard` (main runs) | Correct for static_soft (returns plain dict, no feedback artifact) |
| `prompts` | `default` | Default GigaEvo mutation prompts (overridden by co-evolved prompts in treatment, but used as fallback and for insights/lineage/scoring) |
| Chain LLM | Qwen3-8B, thinking mode ON, max_tokens=32768 | Required for GEPA comparison |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507, one server per run | Canonical mutation LLM |
| `num_parents` | 1 | Single-parent mutation; identical to Cell C |
| `max_elites_per_generation` | 8 | Identical to Cell C |
| `max_mutations_per_generation` | 8 | C(8,1) = 8 with num_parents=1 |
| `max_generations` | 25 | Identical to Cell C |
| `stage_timeout` | 3000 | Identical to Cell C |
| `dag_timeout` | 7200 | Identical to Cell C |
| Seed initialization | Cold start (no warm-start seed) | Identical to Cell C |
| HTTP timeout | 600s | Consistent with all prior runs |
| BM25 retrieval k | 7 (hops 1-2), 10 (hop 3) | Frozen in chain topology |
| Validation sample size | 300 (first 300 train samples) | Default; identical to Cell C |

---

## 6. Run Design Table

### Main runs (HoVer chain evolution with soft fitness + co-evolved prompts)

| Run | Label | `redis.db` | `problem.name` | `pipeline` | `prompt_fetcher` | `prompt_fetcher.prompt_redis_db` | Chain LLM URL | Mutation LLM URL | Condition |
|-----|-------|------------|-----------------|-----------|-------------------|----------------------------------|---------------|------------------|-----------|
| C1 | hover-coevo-1 | 9 | chains/hover/static_soft | standard | coevolved | 11 | http://10.226.17.25:8001/v1 | http://10.226.72.211:8777/v1 | Treatment |
| C2 | hover-coevo-2 | 10 | chains/hover/static_soft | standard | coevolved | 12 | http://10.225.185.235:8001/v1 | http://10.226.15.38:8777/v1 | Treatment |

### Prompt runs (mutation prompt evolution)

| Run | Label | `redis.db` | `problem.name` | `pipeline` | `main_redis_db` | `main_redis_prefix` | Mutation LLM URL | Paired with |
|-----|-------|------------|-----------------|-----------|-----------------|---------------------|------------------|-------------|
| P1 | hover-prompt-evo-1 | 11 | prompt_evolution_hover | prompt_evolution | 9 | chains/hover/static_soft | http://10.226.185.47:8777/v1 | C1 |
| P2 | hover-prompt-evo-2 | 12 | prompt_evolution_hover | prompt_evolution | 10 | chains/hover/static_soft | http://10.225.51.251:8777/v1 | C2 |

### Historical control (no within-experiment control runs)

The comparison reference is Cell C from the feedback_softfit experiment (PR #92):
- **Mean test coverage**: 54.37% (discrete, 5-repeat), **SD**: 0.99pp, **n**: 2
- **Config**: chains/hover/static_soft, pipeline=standard, prompt_fetcher=fixed, cold start, num_parents=1, max_elites=8, Qwen3-8B thinking, Qwen3-235B mutation
- **Individual runs**: F3=55.07% (SD=1.32%), F4=53.67% (SD=1.41%)

### Chain LLM allocation

Only main runs (C1, C2) need chain LLMs. Prompt runs do not evaluate chains.

| Run | Chain LLM endpoint |
|-----|-------------------|
| C1 | 10.226.17.25:8001 (host A) |
| C2 | 10.225.185.235:8001 (host B) |

**Host shuffling**: C1 uses host A, C2 uses host B. This mirrors the Cell C allocation (F3=host A:8000, F4=host B:8000) and eliminates any systematic host-treatment confound. Note: different ports (8001 vs 8000) are used because 8000 ports may be occupied by other experiments. Both ports serve identical Qwen3-8B models. **Pre-launch port parity verification is mandatory** (see Appendix A, item 8).

### Time-gate for historical control validity

Cell C data was collected on 2026-03-20. If launch of this experiment occurs **more than 72 hours** after Cell C completion, a concurrent within-experiment control run is required to guard against infrastructure drift. The reconfigured allocation would be: n=1 treatment (C1 + P1, 2 mutation endpoints) + n=1 concurrent control (soft fitness, fixed prompts, 1 chain LLM, 1 mutation endpoint) + 1 idle mutation endpoint. This sacrifices replication for drift detection.

### Mutation LLM allocation (all 4 processes)

| Process | Mutation LLM endpoint |
|---------|----------------------|
| C1 (main) | 10.226.72.211:8777 |
| C2 (main) | 10.226.15.38:8777 |
| P1 (prompt) | 10.226.185.47:8777 |
| P2 (prompt) | 10.225.51.251:8777 |

Each of the 4 processes has a dedicated mutation LLM endpoint. No endpoint sharing occurs.

### Redis DB allocation

| DB | Run | Purpose |
|----|-----|---------|
| 9 | C1 | Main run archive + prompt stats write-back |
| 10 | C2 | Main run archive + prompt stats write-back |
| 11 | P1 | Prompt run archive (C1 reads champion from here) |
| 12 | P2 | Prompt run archive (C2 reads champion from here) |

DBs 9-12 must be flushed before launch (after archiving feedback_softfit data).

### Topology: 1-to-1 pairing (not 1-to-many)

This experiment uses **1-to-1 pairing** (each main run coupled to its own dedicated prompt run), unlike the HotpotQA experiment which used 3+1 topology. Rationale:

1. **Independence**: With 1-to-1 pairing, runs C1+P1 and C2+P2 are fully independent replications. Under 1-to-many, all main runs share prompt evolution noise from a single prompt run.
2. **Infrastructure**: We have exactly 4 mutation LLM endpoints and need 2 main + 2 prompt processes. The 1-to-1 allocation is natural.
3. **Lower prompt trial rate**: Each prompt run receives stats from only 1 main run (~8 mutations/gen), versus 3 in the HotpotQA 3+1 topology (~24 mutations/gen). This means slower prompt fitness convergence. With min_trials=5 and 8 trials/gen, the first fitness estimate appears at gen ~1 (if one prompt is selected for all 8 mutations) but may take 2-3 gens for diverse prompt sampling. This is a known tradeoff accepted for the independence benefit.

### Prompt run configuration

| Field | Value |
|-------|-------|
| `problem.name` | `prompt_evolution_hover` (new variant -- see Section 12, Open Question #1) |
| `pipeline` | `prompt_evolution` |
| `num_parents` | 1 |
| `max_elites_per_generation` | 5 (smaller archive appropriate for prompt space) |
| `max_generations` | 25 (same as main run) |
| `stage_timeout` | 3000 |
| `dag_timeout` | 7200 |
| `prior_beta` | 3.0 (Beta(1,3) pessimistic prior for untested prompts) |
| Seed programs | 4 (generic.py, minimal.py, generalization.py, hover.py) |

### Combinatorics verification

| Run | num_parents | max_elites | Parent combos | max_mutations | Actual mut/gen |
|-----|:-----------:|:---------:|:-------------:|:-------------:|:--------------:|
| C1 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| C2 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| P1 | 1 | 5 | C(5,1) = 5 | 5 | 5 |
| P2 | 1 | 5 | C(5,1) = 5 | 5 | 5 |

---

## 7. Sample Size Justification

**n=2 treatment runs (total 4 concurrent processes: 2 main + 2 prompt). No within-experiment controls.**

Treatment runs are compared against the historical Cell C reference (mean=54.37%, SD=0.99pp, n=2) from the feedback_softfit experiment (PR #92, completed 2026-03-20).

### Why n=2

1. **Compute constraint**: Each treatment pair requires 2 concurrent processes (main + prompt run), each with a dedicated mutation LLM endpoint. With 4 mutation LLM endpoints, we can run exactly 2 treatment pairs.

2. **Historical control is recent and well-characterized**: Cell C was run under identical configuration (chains/hover/static_soft, pipeline=standard, cold start, num_parents=1, max_elites=8, same LLM models) and completed on the same day as this design. The SD (0.99pp, n=2) is comparable to the HoVer baseline SD (0.63pp, n=4).

3. **Statistical power**: With n_treatment=2 vs n_reference=2, the MDE for a two-sample t-test at alpha=0.05 (one-sided) and 80% power is:

    MDE = t(0.95, df~2) * SD * sqrt(1/n1 + 1/n2)
        = 4.303 * 0.99 * sqrt(1/2 + 1/2)
        = 4.303 * 0.99 * 1.0
        = 4.26pp

    This is a large MDE. Effects in the +2-4pp range will not reach formal significance. The experiment is designed as a **directional probe**, not a definitive test. A POSITIVE signal (both treatment runs individually exceeding 56.37%) warrants follow-up at n>=4.

    **Caveat**: The MDE estimate itself is uncertain because the reference SD (0.99pp) is estimated from only n=2 observations. The true population SD could plausibly be 1.5-2.5x larger (the baseline SD from n=4 was 0.63pp, suggesting the HoVer landscape has low inter-run variance, but this cannot be confirmed from n=2). If the true SD is 2.0pp, the MDE approximately doubles to ~8.5pp. Results should be interpreted with this uncertainty in mind.

4. **Why not pool with baseline?** We could compare treatment (n=2) against a pooled reference of Cell A + Cell C (n=6, grand mean ~52.56%). This would increase power but confound the comparison: the pooled reference includes runs without soft fitness, and any observed improvement could be attributed to soft fitness rather than co-evolution. The clean comparison is treatment (soft + coevo) vs Cell C (soft only), isolating the co-evolution effect.

### Follow-up design (pre-committed)

If both treatment runs exceed 56.37%: replicate at n=4 for definitive power.
If one treatment run exceeds 56.37% and the other does not: INCONCLUSIVE; replicate at n=4.
If both treatment runs are in [54.37%, 56.37%): NULL; do NOT pursue further prompt co-evolution experiments.
If both treatment runs fall below 54.37%: REGRESSIVE; investigate whether co-evolution disrupts soft fitness gains.

---

## 8. Statistical Test

### Test 1: Treatment vs. Cell C reference (primary)

**Comparison**: Mean test retrieval coverage of treatment runs (n=2) vs Cell C reference (n=2, mean=54.37%, SD=0.99pp).

**Test**: Welch's two-sample t-test, one-sided (H1: treatment_mean > reference_mean).

**Statistic**: t = (treatment_mean - 54.37) / sqrt(s_treatment^2/2 + 0.99^2/2)

**Degrees of freedom**: Satterthwaite approximation. With n1=n2=2, df will be approximately 2, yielding very wide confidence intervals.

**Significance threshold**: alpha = 0.05 (one-sided), applied **only to Test 1** (the primary comparison). Tests 2-4 are exploratory; their p-values, if reported, should be interpreted descriptively without formal significance claims. Given n=2 per condition, even Test 1 is severely underpowered. The primary decision criterion is the effect-size threshold table in Section 2, not p < 0.05.

### Test 2: Treatment vs. baseline (secondary, broader context)

**Comparison**: Treatment mean (n=2) vs baseline mean (Cell A, n=4, mean=51.65%, SD=0.63pp).

**Purpose**: Verify that co-evolution + soft fitness remains above baseline. A treatment mean below 51.65% would indicate that co-evolution destroys baseline performance, which would be a NEGATIVE result stronger than the HotpotQA null.

### Test 3: Cross-task comparison (exploratory)

**Comparison**: HoVer co-evolution delta (treatment_mean - 54.37%) vs HotpotQA co-evolution delta (+0.64pp).

**Purpose**: Determine whether the HoVer landscape is more responsive to prompt co-evolution. If both deltas are near zero, the combined evidence rules out prompt co-evolution as a productive intervention across tasks.

### Test 4: Per-run test evaluation (5-repeat protocol)

Each run's test coverage is the mean of 5 independent evaluations on the 300-sample test set. Report per-repeat scores and within-run SD. Compare within-run SD between treatment and Cell C reference to assess whether co-evolution affects LLM stochasticity.

### Mechanism check: prompt fitness analysis

Report the prompt run's archive at gen 25:
- Number of programs, total trials, trials per prompt
- Top prompt fitness (Beta(1,3) posterior) vs best seed fitness
- Qualitative description of the champion prompt's content
- Per-generation success rate breakdown (if available from Redis stats), to assess temporal autocorrelation

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Cold-start prompt fitness lag (chicken-and-egg)** | The prompt run starts from seed programs with no fitness data. For the first N gens (until min_trials=5 mutations occur), PromptFitnessStage returns fitness=0.0 for all prompts. The main run falls back to fixed default prompts during this period. The highest-gradient phase of evolution may occur before co-evolved prompts are available. | GigaEvoArchivePromptFetcher falls back to fixed prompts until the prompt archive has a champion. Expected: first 2-3 gens use fixed prompts. Document the actual fallback-to-coevolved transition generation. If transition occurs after gen 10, flag as a threat. With 1-to-1 pairing (8 trials/gen), the lag may be slightly longer than the HotpotQA 3+1 topology (24 trials/gen). |
| 2 | **Prompt fitness noise** | With 1-to-1 pairing, each prompt run receives ~8 trials/gen. After 5 gens, a prompt has ~40 trials -- marginally reliable. The Beta(1,3) posterior may be dominated by lucky prompts rather than genuinely better ones. | min_trials=5 threshold prevents premature fitness assignment. The 1-to-1 topology accepts noisier prompt fitness for the benefit of independent replications. |
| 3 | **HotpotQA-specific seed prompts** | The existing prompt_evolution seed programs (generic.py, hotpotqa.py, minimal.py, generalization.py) reference HotpotQA-specific concepts (6-step chain, "step 3 query", EM/F1 metrics). Using them for HoVer may produce suboptimal starting points. | Create a new `prompt_evolution_hover` problem variant with a HoVer-specific task_description.txt and at least one HoVer-specific seed (hover.py). The generic.py and minimal.py seeds are task-agnostic enough to serve as-is. Replace hotpotqa.py with hover.py (3-hop chain, retrieval coverage, 7-step topology). |
| 4 | **Infrastructure drift from Cell C** | Cell C (F3, F4) was run on 2026-03-20. If this experiment launches days later, model weights, server behavior, or proxy configuration could differ. | (a) Pre-launch health check: verify chain LLM thinking mode, mutation LLM model version strings, Redis connectivity. (b) If both treatment runs fall below 52.37% (2pp below baseline), flag as potential infrastructure drift. (c) Cell C data is same-day as this design -- launch promptly to minimize drift. |
| 5 | **Co-evolution infrastructure bugs (PR #82)** | The HotpotQA experiment required 13 amendments and 8 relaunches to reach a functional co-evolution system. Many bugs were fixed, but new ones may emerge with the HoVer variant (different prefix, different fitness metric, different stats aggregation patterns). | (a) Mandatory 3-gen smoke test before full launch. After gen 3, verify: (i) at least one `chains/hover/static_soft:prompt_stats:{prompt_id}` key exists in the main run's Redis DB, (ii) the prompt run's archive contains at least one program. (b) If smoke test fails, fix bugs and document as amendments before re-launching. |
| 6 | **Fallback period creates asymmetric comparison** | Treatment runs use fixed prompts for the first ~2-3 gens (fallback), then switch to co-evolved prompts. Cell C used fixed prompts for ALL 25 gens. The treatment is strictly a superset of the control in terms of prompt variation. If co-evolved prompts are worse than fixed prompts, the treatment could underperform Cell C -- this would be a REGRESSIVE result and highly informative. | Document the transition generation. If the fallback period exceeds 5 gens, the effective co-evolution window (gens 6-25) may be too short for meaningful adaptation. |
| 7 | **Temporal autocorrelation of prompt fitness** | Prompts used during the early high-gradient phase of evolution accumulate artificially high success rates. Late-phase prompts appear worse regardless of intrinsic quality. This confound was identified and documented in the HotpotQA design (Confound #7) and confirmed in the results. | Acknowledge limitation explicitly. If possible, report per-generation success rates for the champion prompt. The mechanism check (H1_mech) is descriptive, not confirmatory. |
| 8 | **Soft fitness + co-evolution interaction may overfit** | Co-evolved prompts that exploit the soft fitness gradient (targeting easy partial-retrieval improvements) may produce programs that score well on soft val but do not improve discrete test coverage. The soft fitness landscape rewards 1/3 and 2/3 retrieval, but the test metric requires 3/3. | Val-test gap is a tracked diagnostic. Since val uses soft scoring and test uses discrete, the gap is not directly comparable to Cell C. Report both soft val fitness and an approximate discrete val coverage (from the last gen's evaluation) for each treatment run. |
| 9 | **Port difference (8001 vs 8000)** | Cell C used chain LLM ports 8000; this experiment uses ports 8001. Both serve identical Qwen3-8B models, but if the 8001 instances have different quantization, batching, or configuration, chain outputs could differ systematically. This co-varies with the IV. | Pre-launch port parity verification (Appendix A, item 8): (a) query `/v1/models` on both ports of at least one host and confirm identical model IDs, (b) confirm `max_model_len` matches, (c) run a trivial 10-sample evaluation on both ports and compare scores. If parity fails, use ports 8000 instead. |
| 10 | **No within-experiment control** | Without concurrent soft-fitness-only runs (no co-evolution), infrastructure drift is undetectable. **Any result other than a large positive signal will be ambiguous with respect to infrastructure drift.** Non-extreme results (e.g., treatment mean in [52%, 55%]) cannot distinguish a genuine co-evolution effect from baseline shift. | Cell C data is fresh (same day as design). A 72-hour time-gate is enforced (Section 6): if launch is delayed beyond 72h, a concurrent control run is required. If treatment mean deviates drastically from reference (e.g., both runs below 50%), run a post-hoc single control (soft fitness, fixed prompts) to disambiguate. |

---

## 10. Stop Criteria

### Early termination criteria (per run)

- **Gen-0 val fitness < 0.01 (soft)**: Halt; BM25 first hop is not finding any gold docs. Investigate.
- **Gen-0 val fitness > 0.20 (soft)**: Halt; initialization error. Cold start should produce near-0.33 soft fitness at most.
- **Gen-0 val fitness = sentinel value (-1000.0)**: Halt; execution error.
- **Main run val coverage < 45% at gen 10 (soft)**: Halt; infrastructure failure. Cell C achieved soft val fitness ~0.78 by gen 25; if the run is below 0.45 at gen 10, something is wrong.
- **Prompt run archive empty at gen 5 of the main run**: Halt that treatment pair; co-evolution feedback loop is broken. Diagnose.

### Stagnation-based early completion

If `valid_frontier_fitness` shows no improvement for >= 10 consecutive generations AND current gen >= 15, the run may be terminated early. This is not an invalidation.

### Run invalidation criteria

A run is excluded from all analyses if any of the following apply:

1. Thinking mode not active: `<think>` blocks absent from >= 5% of chain outputs at gen 1.
2. Invalidity rate > 90% at gen 10.
3. Gen-0 val coverage > 20% (soft) -- initialization error.
4. `max_elites_per_generation` confirmed at 5 (not 8) in post-hoc inspection (main runs only).
5. `num_parents` confirmed at 2 (not 1) in post-hoc inspection.
6. `pipeline` mismatch: main runs not using `standard`, or prompt runs not using `prompt_evolution`.
7. `problem.name` mismatch: main runs not using `chains/hover/static_soft`.
8. Test evaluation uses soft metric instead of discrete (metric contamination).
9. Prompt run never produced a champion that was fetched by the main run (verified via `prompt_stats` keys in Redis: count > 0 and at least one prompt_id with trials >= 5).
10. Redis corruption or data loss during run.

### Completion criteria

- Both main runs reach gen 25 OR are terminated/invalidated per above criteria.
- Both prompt runs reach gen 25 OR the paired main run completes first (prompt run may be stopped after main run finishes, as in the HotpotQA experiment where P1 reached gen 23/25).

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time per main run (300-sample, 25 gens) | ~8-12h (same as Cell C) |
| Total wall time (4 processes parallel) | ~12h wall-clock |
| Chain LLM endpoints | 2 (C1 and C2; prompt runs do not use chain LLMs) |
| Mutation LLM endpoints | 4 (one per process: C1, C2, P1, P2) |
| Redis DBs | 4 (DBs 9, 10, 11, 12) |
| Test eval time | ~5 min/repeat x 5 repeats x 2 runs = ~50 min total |
| New code required | (1) `prompt_evolution_hover/` problem variant with HoVer-specific task_description.txt and hover.py seed, (2) Unit tests for new seed program |

---

## 12. Open Questions / Risks

### Open Question 1: HoVer-specific prompt evolution problem variant

The existing `prompt_evolution` problem has a `task_description.txt` written entirely for HotpotQA (6-step chain, EM/F1 metrics, "step 3 query generation" guidance). Using it unchanged for HoVer would provide the meta-evolution LLM with incorrect domain knowledge about the downstream chain.

**Resolution**: Create `problems/prompt_evolution_hover/` with:
- `task_description.txt`: Adapted for HoVer (7-step chain, 3-hop retrieval, retrieval coverage metric, "steps 3 and 6 generate second/third-hop queries", soft vs discrete fitness distinction)
- `initial_programs/hover.py`: HoVer-specific seed prompt mentioning 3-hop retrieval coverage, claim verification, and the 7-step topology
- `initial_programs/generic.py`: Copied from prompt_evolution (task-agnostic)
- `initial_programs/minimal.py`: Copied from prompt_evolution (task-agnostic)
- `initial_programs/generalization.py`: Copied from prompt_evolution (task-agnostic)
- `metrics.yaml`: Identical to prompt_evolution (success_rate metric)

This is a code prerequisite, not an amendment. It must be completed before launch.

### Open Question 2: Is 1-to-1 prompt fitness convergence fast enough?

The HotpotQA experiment used 3+1 topology, providing ~24 trials/gen to the prompt run. With 1-to-1, each prompt run gets ~8 trials/gen. At min_trials=5 and 5 elites in the prompt archive, each prompt needs 5 trials before its fitness is computed. With 8 trials/gen spread across 5 prompts (random sampling), each prompt accumulates ~1.6 trials/gen. It takes ~3 gens for a single prompt to reach min_trials=5.

With 25 gens and ~8 trials/gen = 200 total trials across all prompts, and 5 elites + evolved variants (say 20-30 total prompts by gen 25), the average trials per prompt is ~7-10. This is comparable to the HotpotQA experiment's 11.6 trials/prompt (454 trials across 39 prompts). The prompt fitness estimates will be noisy but not critically worse than HotpotQA.

**Risk level**: MEDIUM. If prompt fitness convergence is too slow, the co-evolved prompts may never differentiate meaningfully from seeds. This would manifest as a prompt archive with near-uniform fitness values -- which is a diagnosable outcome, not a silent failure.

### Open Question 3: Does the co-evolution mechanism interact with soft fitness differently than discrete?

On HotpotQA (discrete EM fitness), a "successful" mutation was one that increased val EM by any amount. On HoVer with soft fitness, a "successful" mutation increases soft val coverage by any amount. Soft fitness has a finer gradient -- small improvements (e.g., one sample going from 1/3 to 2/3 gold docs) register as successes that would be invisible under discrete scoring. This means the mutation success rate itself may be higher under soft fitness, providing the prompt run with a richer fitness signal.

**Implication**: If this is correct, the prompt co-evolution system has a structural advantage on HoVer-with-soft-fitness that it lacked on HotpotQA. This is actually the core hypothesis of the experiment -- that the HoVer landscape is more responsive. If the null hypothesis holds despite this advantage, the evidence against prompt co-evolution becomes very strong.

### Open Question 4: Infrastructure maturity

The HotpotQA prompt co-evolution experiment required 13 amendments. The infrastructure bugs identified (prompt_id mismatch, cached-forever fitness, stale insights, DataFlowEdge filtering, model_name mismatch) were fixed as part of PR #82 and subsequent patches. However, the HoVer variant introduces new configuration surface (different prefix `chains/hover/static_soft`, different fitness metric, different problem variant `prompt_evolution_hover`). Any prefix mismatch between the main run's stats write-back and the prompt run's stats read would silently break the feedback loop.

**Mitigation**: The 3-gen smoke test (Section 10) explicitly verifies that the prompt stats key prefix matches between writer and reader. The prefix is `chains/hover/static_soft` (from `main_redis_prefix: ${problem.name}` in coevolved.yaml). This must match the `prefix` in the prompt_evolution pipeline's `prompt_stats_provider`.

### Open Question 5: What if the result is NULL?

A null result here, combined with the HotpotQA null, would establish prompt co-evolution as ineffective across two tasks with different fitness landscapes (flat vs responsive). The scientific contribution would be:

1. **Prompt quality is not a binding constraint on GigaEvo performance** -- confirmed across tasks, fitness metrics, and landscape responsiveness levels.
2. **The binding constraint is elsewhere** -- for HotpotQA, it is chain topology (28 runs confirmed). For HoVer, the binding constraint under soft fitness is unknown but is not mutation prompt quality.
3. **Co-evolutionary systems are high-cost, low-return** -- the 13-amendment HotpotQA debugging experience plus a second null on HoVer would make a strong case against investing further in this approach.

This would be a valuable negative result for the GigaEvo methods paper.

---

## Appendix A: Code Prerequisites Before Launch

1. **Create `problems/prompt_evolution_hover/`**: New problem variant with HoVer-specific task_description.txt, metrics.yaml, and seed programs (hover.py + generic.py + minimal.py + generalization.py). The task_description.txt must describe the 7-step HoVer chain topology, 3-hop retrieval, retrieval coverage fitness (soft), and the contracts (placeholders, JSON output format, double-brace escaping).

2. **Verify coevolved.yaml prefix interpolation**: Run `python run.py problem.name=chains/hover/static_soft pipeline=standard prompt_fetcher=coevolved prompt_fetcher.prompt_redis_db=11 --cfg job` and confirm that `main_redis_prefix` resolves to `chains/hover/static_soft`.

3. **Verify prompt_evolution pipeline prefix**: Run `python run.py problem.name=prompt_evolution_hover pipeline=prompt_evolution redis.db=11 main_redis_db=9 main_redis_prefix=chains/hover/static_soft --cfg job` and confirm that the `prompt_stats_provider.prefix` matches `chains/hover/static_soft`.

4. **Verify test.py discrete scoring**: SHA-256 hash of `problems/chains/hover/static_soft/test.py` must match `problems/chains/hover/static/test.py`. Both use discrete retrieval evaluation for the test metric.

5. **Verify initial program identity**: `chains/hover/static_soft/initial_programs/baseline.py` must be byte-for-byte identical to `chains/hover/static/initial_programs/baseline.py`.

6. **Redis DBs 9-12**: Must show 0 keys after feedback_softfit archival.

8. **Chain LLM port parity verification**: Query `/v1/models` on both `:8000` and `:8001` of at least one host (e.g., 10.226.17.25). Confirm: (a) identical model IDs, (b) identical `max_model_len`. Then run a trivial 10-sample evaluation of the baseline program on both ports and compare scores. If scores differ by more than 5pp or model configs do not match, switch treatment runs to port 8000 (matching Cell C).

9. **3-gen smoke test** (mandatory): Launch one treatment pair (C1 + P1) for 3 generations. After gen 3, verify:
   - (i) At least one `chains/hover/static_soft:prompt_stats:{prompt_id}` key exists in Redis DB 9
   - (ii) The prompt run's archive (DB 11) contains at least one program
   - (iii) The main run's logs show `has_champion = true` or `cache_hits > 0` from the prompt fetcher
   - If any check fails, diagnose and fix before full launch. Document fixes as amendments.

---

## Appendix B: Decision Tree

```
After gen-25 evaluations for C1, C2 (plus Cell C reference F3=55.07%, F4=53.67%):

  Cell C reference mean: 54.37% (SD=0.99pp, n=2)
  Baseline mean (Cell A, H1-H4): 51.65% (SD=0.63pp, n=4)
  GEPA benchmark: 52.33%

  Treatment mean (C1, C2): treatment_mean
  Delta vs Cell C: delta_c = treatment_mean - 54.37%
  Delta vs baseline: delta_b = treatment_mean - 51.65%

                       delta_c >= +2.0pp?
                      /                \
                    YES                 NO
                     |                   |
              Both runs >= 56.37%?   delta_c >= 0?
              /                \      /          \
            YES                NO   YES           NO
             |                  |    |             |
         POSITIVE          INCONCLUSIVE  NULL    delta_b >= 0?
         (replicate n=4)   (replicate n=4)       /          \
                                               YES           NO
                                                |             |
                                           REGRESSIVE     NEGATIVE
                                           (coevo hurts   (coevo destroys
                                            soft gains)    everything)

  Cross-task decision:
    - If HoVer NULL + HotpotQA NULL: Do NOT pursue prompt co-evolution further
    - If HoVer POSITIVE: Investigate why HoVer responds (landscape gradient hypothesis)
    - If HoVer REGRESSIVE: Investigate whether co-evolution disrupts soft fitness mechanism
```

---

## Appendix C: Comparison with HotpotQA Prompt Co-Evolution Design

| Dimension | HotpotQA (PR #84) | HoVer (this experiment) |
|-----------|-------------------|-------------------------|
| Landscape | Flat (59-60% ceiling, 28 NULL runs) | Responsive (soft fitness +2.72pp, p~0.03) |
| Evolutionary fitness | Discrete (F1, then EM) | Soft (fractional retrieval coverage) |
| Test metric | Discrete (EM) | Discrete (retrieval coverage) |
| Topology | 3+1 (3 main + 1 shared prompt run) | 1-to-1 (2 independent pairs) |
| Reference | Cold-start mean 59.58% (SD=1.00pp, n=4) | Cell C mean 54.37% (SD=0.99pp, n=2) |
| Trials/gen for prompt run | ~24 (from 3 main runs) | ~8 (from 1 main run) |
| Treatment n | 3 | 2 |
| Chain topology | 6-step (2 tool + 4 LLM) | 7-step (3 tool + 4 LLM) |
| Seed prompts | HotpotQA-specific | HoVer-specific (new) |
| Infrastructure maturity | First production use (13 amendments) | Second use (bugs should be fixed) |

The key scientific difference is the landscape: HotpotQA's flat landscape gave co-evolution no room to operate; HoVer's responsive landscape (demonstrated by soft fitness gains) provides the headroom that the hypothesis requires. If co-evolution fails on a responsive landscape, the mechanism itself is insufficient -- not just the landscape.

---

*Ready for Reviewer-2's scrutiny.*
