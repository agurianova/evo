# Experimental Design: Prompt Co-Evolution

**Date**: 2026-03-16
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft

---

## 1. Research Question

Twenty-five consecutive independent HotpotQA runs have confirmed a stagnation ceiling at 59--60% test EM. Every intervention tested so far -- fitness metric (F1 vs EM), validation size (300 vs 600), mutation prompts (default vs NLP), crossover (1 vs 2 parents), retriever (BM25 vs ColBERT), feedback granularity (title-only vs passage-level), mutation LLM capability (Qwen3-235B vs Gemini-3.1-Pro), and held-out regularization -- has produced NULL or NEGATIVE results. The cold-start mean (59.58%, SD=1.00pp, n=4) is the canonical reference.

One constant across all 25 runs: **the mutation prompts were fixed**. Whether default GigaEvo prompts or hand-written NLP prompts, they were static text files read once and reused verbatim for every generation. The nlp_prompts experiment (PR #69) showed that swapping one fixed set for another made no difference -- but it tested exactly two prompt variants chosen a priori. The space of possible mutation prompts is combinatorially vast. Perhaps the problem is not *which* prompt to use, but that the prompt itself should adapt as the chain population evolves.

Prompt co-evolution is a qualitatively different intervention from all prior experiments. Instead of optimizing the mutation prompt by hand, we run a second GigaEvo instance that evolves mutation prompt programs in parallel, using the main run's mutation success rate as fitness signal. This creates a co-evolutionary dynamic: as the chain population evolves and the "easy" improvements are exhausted, the prompt population can adapt its guidance to the current difficulty frontier.

**Primary research question**: Does co-evolving mutation prompts via a parallel GigaEvo instance improve HotpotQA test EM relative to the fixed-prompt cold-start baseline (59.58%, SD=1.00pp)?

**Secondary research question**: Does the prompt run discover prompts whose mutation success rate exceeds that of the default fixed prompts? (This is a mechanism question: even if test EM does not improve, prompt adaptation might be measurable in terms of mutation success rate.)

---

## 2. Hypotheses

### Primary hypothesis: co-evolved prompts improve test EM

**H0**: Co-evolved mutation prompt runs produce test EM indistinguishable from the fixed-prompt cold-start baseline (mean 59.58%, SD=1.00pp). Formally: mu_coevo <= 59.58%.

**H1**: Co-evolved mutation prompt runs produce test EM above 61.58% (mean), representing a +2.00pp improvement over the cold-start reference. The 2.00pp threshold corresponds to 2 sigma of the cold-start distribution (SD=1.00pp) and is consistent with the significance threshold pre-specified in all prior experiments.

**Effect size thresholds** (applied to the n=2 co-evolution treatment mean):

| Co-evo mean test EM | Verdict |
|---------------------|---------|
| >= 61.58% (both runs) | **POSITIVE** -- co-evolution improves test EM at >= 2sigma |
| >= 61.58% (one run only) | **INCONCLUSIVE** -- requires follow-up experiment at n>=4 |
| [59.58%, 61.58%) | **NULL** -- within noise band of baseline |
| < 59.58% | **NEGATIVE** -- co-evolution hurts test EM |

### Secondary hypothesis: prompt adaptation is measurable

**H0_mech**: The prompt run's champion at gen 25 has mutation success rate <= the success rate of the fixed default prompt (measured on the same main run).

**H1_mech**: The prompt run's champion achieves a strictly higher mutation success rate than the fixed default prompt. This is evaluated descriptively from Redis stats -- no formal statistical test due to the non-independence of trials within a run. **Limitation**: High champion fitness is necessary but not sufficient evidence for prompt quality -- temporal autocorrelation between prompt usage timing and the main run's improvement phase can inflate success rates regardless of intrinsic prompt quality (see Section 9, Confound #7).

---

## 3. Independent Variable(s)

| Variable | Control value | Treatment value |
|----------|---------------|-----------------|
| Mutation prompt source | Fixed (FixedDirPromptFetcher, `prompt_fetcher=fixed`) | Co-evolved (GigaEvoArchivePromptFetcher, `prompt_fetcher=coevolved`) |

This is a single-factor experiment with one IV. The treatment runs a parallel prompt GigaEvo instance; the historical control (cold_start experiment, PR #75) used fixed prompts. No within-experiment control runs are included (see Section 7).

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test EM | Exact match on 300-sample test set, best-by-val program at final gen | **Yes** |
| Val EM | Best val EM across all generations | No (diagnostic) |
| Val-test gap | val_EM - test_EM | No (diagnostic: overfitting) |
| Birth generation | Generation at which the best-by-val program was born | No (diagnostic: stagnation) |
| Prompt champion success rate | Fitness of the prompt run's best program at final gen | No (mechanism) |
| Prompt champion text | Qualitative: what did the evolved prompt converge to? | No (exploratory) |

**Primary metric**: Test EM of the best-by-val program at gen 25 (main run).

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| `problem.name` | `chains/hotpotqa/static_f1_600` | F1 fitness + 600 val samples -- canonical cold-start config |
| `pipeline` | `hotpotqa_asi` (main runs only; prompt runs use `pipeline=prompt_evolution`) | Required for all HotpotQA variants (tuple validate.py) |
| `prompts` | `default` | Default GigaEvo prompts for insights/lineage/scoring (only mutation system+user are co-evolved in treatment) |
| `num_parents` | 1 | Single-parent mutation (cold-start canonical config) |
| `max_elites_per_generation` | 8 | Standard HotpotQA override |
| `max_mutations_per_generation` | 8 | Matches num_parents=1 + max_elites=8 |
| `max_generations` | 25 | Matches cold-start reference (PR #75); cold-start stagnation onset at birth-gen 11-19 is well within 25 gens |
| `stage_timeout` | 6000 | Safe for 600-sample eval |
| `dag_timeout` | 9000 | Safe for 600-sample eval |
| Chain LLM | Qwen3-8B, thinking mode ON | Required for GEPA comparison |
| Mutation LLM | Qwen3-235B-A22B-Thinking | Canonical mutation LLM |
| Initialization | Cold start (no warm-start seed) | Canonical cold-start config |
| Failure sampling | Random (cf0cfc1 fix) | Prevents mini-batch overfitting |
| HTTP timeout | 600s | Required for 600-sample runs |

---

## 6. Run Design Table

### Main runs (HotpotQA chain evolution)

| Run | Label | `redis.db` | `prompt_fetcher` | `prompt_fetcher.prompt_redis_db` | Chain LLM | Mutation LLM | Condition |
|-----|-------|------------|-------------------|----------------------------------|-----------|-------------|-----------|
| X1 | coevo-1 | 4 | coevolved | 6 | 10.226.17.25:8001 | 10.226.72.211:8777 | Treatment |
| X2 | coevo-2 | 5 | coevolved | 7 | 10.226.17.25:8000 | 10.226.15.38:8777 | Treatment |

### Prompt runs (mutation prompt evolution)

| Run | Label | `redis.db` | `pipeline` | `main_redis_db` | `main_redis_prefix` | Mutation LLM | Paired with |
|-----|-------|------------|-----------|-----------------|---------------------|-------------|-------------|
| P1 | prompt-evo-1 | 6 | prompt_evolution | 4 | chains/hotpotqa/static_f1_600 | 10.226.185.131:8777 | X1 |
| P2 | prompt-evo-2 | 7 | prompt_evolution | 5 | chains/hotpotqa/static_f1_600 | 10.225.51.251:8777 | X2 |

### Historical control (no within-experiment control runs)

The comparison baseline is the cold-start reference distribution from the cold_start experiment (PR #75):
- **Mean test EM**: 59.58%, **SD**: 1.00pp, **n**: 4
- **Config**: identical to this experiment (static_f1_600, hotpotqa_asi, cold start, num_parents=1, max_elites=8, Qwen3-8B thinking, Qwen3-235B mutation)
- **Individual runs**: T1=59.33%, T2=60.67%, T3=58.33%, T4=60.00%

**Prompt run configuration details**:
- `problem.name=prompt_evolution`
- `pipeline=prompt_evolution`
- `num_parents=1`, `max_elites_per_generation=5` (smaller archive is appropriate for the prompt space: 4 seed programs + LLM mutations; 5 elites avoids sparsity in the prompt_length behavior dimension)
- `max_generations=25` (same as main run; prompt run is fast, no chain eval)

**Mutation LLM allocation**: Each of the 4 processes (X1, X2, P1, P2) has a dedicated mutation LLM endpoint. No endpoint sharing occurs. The prompt run's entrypoint() evaluation is near-zero cost (returns strings); the prompt run's own mutations use its dedicated endpoint independently of the paired main run.

**DB allocation**: Treatment main: DBs 4-5. Treatment prompt: DBs 6-7. Total: 4 DBs.

---

## 7. Sample Size Justification

**n=2 treatment runs (total 2 main runs + 2 prompt runs = 4 concurrent processes). No within-experiment controls.**

Treatment runs are compared against the historical cold-start reference distribution (mean=59.58%, SD=1.00pp, n=4) from the cold_start experiment (PR #75, completed 2026-03-09).

This design is driven by three considerations:

1. **Compute efficiency**: Each treatment pair requires 2 concurrent processes (main + prompt run), each with a dedicated mutation LLM endpoint. With 4 mutation LLM endpoints available, we can run exactly 2 treatment pairs (4 processes) concurrently. Allocating all 4 endpoints to treatment maximizes statistical information about the co-evolution intervention, which is the novel element under test.

2. **Historical controls are sufficient**: The cold-start reference (n=4, mean=59.58%, SD=1.00pp) was collected under identical configuration (static_f1_600, hotpotqa_asi, cold start, num_parents=1, max_elites=8, same LLM models). The tight SD (1.00pp) makes this a reliable baseline. Burning 2 endpoints on redundant drift-check controls would halve our treatment sample without adding proportional information.

3. **Statistical power**: With n=2, no formal hypothesis test achieves adequate power. Results are interpreted descriptively. If both treatment runs individually exceed 61.58% (2sigma above reference), the evidence is suggestive, requiring replication at n>=4. If both fall within [59.58%, 61.58%), verdict is NULL. Mixed results are INCONCLUSIVE and require follow-up. **A POSITIVE verdict at n=2 warrants a follow-up confirmatory experiment at n>=4.**

**Why no within-experiment controls?** (a) The cold-start reference is fresh (7 days old at time of design) and was run on the same infrastructure with the same codebase. (b) Each treatment pair requires 2 dedicated mutation LLM endpoints (one for the main run, one for the prompt run), consuming all 4 available endpoints. (c) The cold_start experiment already provides n=4 controls -- adding n=2 more would contribute marginally to a reference whose SD is already tight at 1.00pp.

**Limitation acknowledged**: Without within-experiment controls, infrastructure drift (model weight changes, proxy behavior shifts, server hardware changes) between the cold_start experiment and this experiment is undetectable. This is mitigated by a pre-launch health check (see Section 9, Confound #5).

---

## 8. Statistical Test

**Test**: Compare treatment mean test EM against the cold-start reference distribution (59.58%, SD=1.00pp, n=4).

**Significance threshold**: alpha = 0.05 (one-sided). Treatment mean >= 61.58% for POSITIVE verdict.

**How computed**:

1. **Primary gate**: Treatment mean (n=2) versus the cold-start reference (59.58%, SD=1.00pp, n=4). With n=2, we report the point estimate and the range (max - min). If both treatment runs individually exceed 61.58%, the evidence is suggestive but requires replication at n>=4 for confirmation. If neither does, verdict is NULL.

2. **Infrastructure drift check**: Without within-experiment controls, infrastructure drift is undetectable from the experiment data alone. If the treatment mean deviates drastically from the reference in a direction not explained by co-evolution (e.g., both treatment runs at 57% or below), flag as a potential infrastructure change rather than a co-evolution effect. In such a case, a post-hoc control run (single cold-start, fixed prompts) would be required to disambiguate.

3. **McNemar (exploratory)**: If both treatment runs exceed the reference mean, pairwise McNemar test between the best treatment program and the best cold-start program T2 (60.67%, the strongest historical control) on 300 test samples. This provides per-sample statistical power beyond run-level aggregation.

4. **Mechanism check**: Report prompt run champion fitness (success rate) and compare descriptively against the implicit success rate of the fixed prompt (estimated from mutation logs in the main run's early gens when fallback fixed prompts are still in use).

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Cold-start prompt fitness lag** | The prompt run starts from seed programs with no fitness data. For the first N gens (until min_trials=5 mutations have occurred), PromptFitnessStage returns fitness=0.0 for all prompts. The prompt run cannot evolve meaningfully until the main run has generated sufficient mutation statistics. | The main run falls back to fixed default prompts while the prompt archive is empty (GigaEvoArchivePromptFetcher fallback mechanism). Expected: first 2-3 gens use fixed prompts, then switch to co-evolved. This is a known asymmetry vs. historical control (historical controls used fixed prompts for ALL gens). The first 2-3 gens are typically the highest-improvement period (cold-start birth-gen 11-19 in prior experiments), so the lag may not matter for final outcome. |
| 2 | **Prompt fitness noise** | Success rate (successes / trials) is noisy with small denominators. At 8 mutations/gen, after 5 gens a prompt has ~40 trials -- marginally reliable. The prompt MAP-Elites archive may be dominated by lucky prompts rather than genuinely better ones. | min_trials=5 threshold prevents premature fitness assignment. Prompt_length as behavior dimension provides diversity pressure. Acknowledge: prompt fitness signal is inherently noisier than chain fitness (300-sample EM). |
| 3 | **Infrastructure novelty risk** | PR #82 code has never been tested in production. Bugs in GigaEvoArchivePromptFetcher, PromptFitnessStage, or RedisPromptStatsProvider could silently break co-evolution without obvious errors. | (a) Pre-launch: run a 3-gen smoke test of one treatment pair to verify end-to-end data flow. After gen 3, verify: (i) at least one `chains/hotpotqa/static_f1_600:prompt_stats:{prompt_id}` key exists in the main run's Redis DB, and (ii) the prompt run's archive contains at least one program with fitness > 0.0. (b) Monitoring: watchdog checks prompt run Redis for archive size and stats key count every 60s. (c) Invalidation criterion: if prompt run archive remains empty after gen 5 of the main run, the treatment run is invalidated. |
| 4 | **Temporal coupling** | The prompt run and main run must be co-temporal. If the prompt run crashes or stalls, the main run reverts to fallback fixed prompts permanently. If the main run crashes, the prompt run has no new stats to update fitness. | Watchdog monitors both processes. If either crashes, restart within 2 gens. If restart fails, document the gap and assess whether the run is salvageable. |
| 5 | **No within-experiment control** | Without concurrent control runs, infrastructure drift since the cold_start experiment (2026-03-09) is undetectable. Model weights, Squid proxy behavior, server hardware, or software updates could shift the baseline without our knowledge. | (a) Pre-launch health check: verify chain LLM thinking mode on all endpoints, confirm mutation LLM responsiveness, check model version strings. (b) Pre-launch smoke test must explicitly verify Redis key name match: directly query both sides of the stats channel -- confirm that the key written by the main run's fetcher (`{prefix}:prompt_stats:{prompt_id}`) is readable by the prompt run's RedisPromptStatsProvider using the same prefix string. (c) If both treatment runs fall below 57.58% (2sigma below reference), flag as potential infrastructure drift and run a post-hoc single control to disambiguate. (d) The cold_start reference is only 7 days old at design time; infrastructure changes are unlikely but not impossible. |
| 6 | **Co-evolution may increase val-test gap** | The co-evolved prompt may specialize toward mutations that improve val performance without generalizing. This is the same overfitting pattern observed with ColBERT feedback and Gemini mutation. | Val-test gap is a tracked diagnostic metric. If treatment val-test gap > 4.0pp (double the cold-start mean of 2.58pp), flag overfitting concern in results regardless of test EM outcome. |
| 7 | **Temporal autocorrelation of prompt fitness** | Prompts used during the early high-gradient phase of the main run accumulate artificially high success rates because mutations are more likely to succeed when the population is far from any local optimum. Prompts used during the stagnation phase appear useless regardless of their intrinsic quality. The mechanism check (H1_mech) cannot distinguish prompt quality from phase correlation. | Acknowledge this limitation explicitly: high champion fitness is necessary but not sufficient evidence for prompt quality. If possible, report per-generation success rates for the champion prompt to check whether its advantage persists into the stagnation phase (gens 15-25) or is concentrated in the early improvement phase (gens 3-10). |
| 8 | **Fallback period stats gap** | During the first ~3 gens, the main run uses fallback fixed prompts (prompt_id=None), so no stats are written to Redis. The prompt run starts effectively blind -- it must discover fitness differences after the main run's highest-improvement window has already passed. This reduces the effective co-evolution window from 25 gens to ~20 gens. | Document the actual fallback-to-coevolved transition generation for each treatment pair. If the transition occurs after gen 10 (past the typical improvement window), flag as a threat to the treatment's viability. The `main_redis_db` constructor fix (see Section 12, item 7) ensures stats begin flowing as soon as the first co-evolved prompt is fetched. |

---

## 10. Stop Criteria

**Early termination**:
- If both main runs show val EM < 50% at gen 10: terminate all runs (infrastructure failure).
- If a treatment main run's val EM < 55% at gen 15 AND the paired prompt run archive is empty: invalidate and terminate that pair (co-evolution infrastructure failure).

**Run invalidation** (assessed post-hoc):
- Thinking mode not confirmed (no `<think>` blocks in chain LLM output).
- Pipeline misconfiguration: `pipeline != hotpotqa_asi` for main runs.
- Prompt run never produced a champion that was fetched by the main run (verified via fetcher stats in logs: `cache_hits > 0` and `has_champion = true`).
- More than 50% of generations in a main run had > 30% invalid programs (infrastructure issue).
- Redis corruption or data loss during run.

**Completion criteria**:
- Both main runs reach gen 25 OR are terminated/invalidated per above criteria.
- Both prompt runs reach gen 25 OR the paired main run completes first (prompt run may be stopped after main run finishes).

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time | ~3.5h (25 gens x 8 min/gen for main runs; prompt runs are negligible) |
| Chain LLM endpoints | 2 (X1 and X2; prompt runs do not use chain LLMs) |
| Mutation LLM endpoints | 4 (one dedicated per process: X1, X2, P1, P2) |
| Redis DBs used | 4 (DBs 4, 5, 6, 7) |
| Total concurrent processes | 4 (2 main runs + 2 prompt runs) |

---

## 12. Open Questions / Risks

1. **Is the prompt fitness signal sufficient?** The prompt run's fitness is mutation success rate -- a ratio computed from a small number of trials. The signal-to-noise ratio may be too low for MAP-Elites to discover genuinely better prompts within 25 gens. If the prompt archive shows no fitness differentiation (all prompts at similar success rates), this is an informative null result about the viability of co-evolutionary prompt optimization.

2. **What should the prompt run's generation cadence be?** The prompt run's "evaluation" (reading stats from Redis) is near-instant. It could run many generations per main-run generation. However, the stats accumulate slowly (8 mutations/gen in the main run). Running the prompt run faster than the stats accumulate means most prompt generations see identical fitness data. The default `loop_interval=1.0` and `max_generations=25` should be adequate -- the prompt run will naturally be rate-limited by waiting for new stats.

3. **Chicken-and-egg problem**: The prompt run needs the main run to generate stats; the main run needs the prompt run to supply prompts. The fallback mechanism (fixed prompts until first champion) breaks the cycle, but the first few generations of the main run are effectively operating under control conditions. This means the treatment effect, if any, can only manifest after gen ~3-5. With stagnation typically hitting at birth-gen 11-19 for cold starts, there is a window of approximately 6-14 generations for co-evolution to make a difference (within 25 total gens).

4. **Novel infrastructure risk**: This is the first production run of PR #82. The smoke test (3-gen pre-launch) is mandatory. If the smoke test fails, the experiment cannot proceed until the infrastructure bugs are fixed. Fixing bugs requires a code change, which must be documented as an amendment if it occurs after pre-registration.

5. **Prompt evolution search space**: The initial prompt programs (generic, hotpotqa, minimal, generalization) provide reasonable seed diversity. But the prompt run's own mutation LLM uses the same default GigaEvo mutation prompts (meta-level). Whether an LLM can effectively mutate prompt-returning Python programs is an untested assumption. If the prompt run produces only syntactically valid but semantically trivial variations, the co-evolution adds no value.

6. **Fallback behavior is asymmetric**: Treatment runs use fixed prompts for the first few gens, then switch to co-evolved prompts. This means the treatment condition is strictly a superset of the historical control condition in terms of prompt variation -- it uses fixed prompts PLUS co-evolved prompts over the course of a run. If the null hypothesis holds, this asymmetry is benign. But if co-evolved prompts are *worse* than fixed prompts (actively harmful), the treatment could underperform the historical baseline. This would be a NEGATIVE result and highly informative.

7. **`set_main_redis_db` bug (RESOLVED)**: The original `GigaEvoArchivePromptFetcher` implementation relied on a `set_main_redis_db()` lifecycle hook that was never called by the pipeline, leaving `_redis_main_sync = None` and silently disabling all stats writes. This has been fixed: `main_redis_db` is now a constructor parameter wired from `${redis.db}` in Hydra config (`config/prompt_fetcher/coevolved.yaml`). Stats writes are active from the first `record_outcome()` call. The broken `set_main_redis_db()` hook has been removed. This fix is critical for co-evolution to function at all -- without it, the prompt run would never receive fitness signal.

---

*Ready for Reviewer-2's scrutiny.*
