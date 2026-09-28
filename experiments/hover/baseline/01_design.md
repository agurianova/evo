# Experimental Design: HoVer Baseline -- Cold-Start Retrieval Coverage via n=4 Replication

**Date**: 2026-03-18
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft -- awaiting Reviewer-2

---

## 1. Research Question

This is the first GigaEvo experiment on HoVer (multi-hop claim verification via retrieval
coverage). There is no prior GigaEvo data on this task, no warm-start seed, and no
established performance distribution. The task differs fundamentally from HotpotQA: fitness
is discrete retrieval coverage (all 3 gold supporting documents found = 1, else 0), the
chain has 7 steps (not 6), and 3 retrieval hops (not 2).

GEPA achieves 52.33% test retrieval coverage on this task. The HotpotQA cold-start
experiment (PR #75) demonstrated that GigaEvo cold start from an unoptimized baseline chain
reaches a stable performance plateau within 15-20 generations, with mean test EM of 59.58%
(SD=1.00pp, n=4). That experiment used the same evolutionary engine, mutation LLM, and
chain LLM as we will use here.

**Primary research question**: What is the cold-start test retrieval coverage distribution
when GigaEvo evolves the HoVer 7-step static chain for 25 generations with n=4 independent
replications? Specifically: does the cold-start mean test retrieval coverage exceed the GEPA
benchmark of 52.33%?

This is an **exploratory baseline** experiment. We have no prior distribution to compare
against (unlike HotpotQA cold_start, which had a warm-start reference). The outputs are:
(1) the mean and SD of test retrieval coverage under cold-start conditions, (2) whether
GigaEvo can beat GEPA on this task, and (3) convergence dynamics (birth-generation of the
best program, trajectory shape).

---

## 2. Hypotheses

### Primary hypothesis: GigaEvo cold start exceeds GEPA on HoVer

**H0**: GigaEvo cold-start mean test retrieval coverage across n=4 runs is at most 52.33%
(the GEPA benchmark). Evolution does not reliably improve retrieval coverage beyond the
GEPA reference on this task.

**H1**: GigaEvo cold-start mean test retrieval coverage exceeds 52.33%. LLM-guided
mutation of the 7-step chain produces retrieval strategies that outperform GEPA's
fixed approach.

**Effect size thresholds** (applied to the n=4 cold-start mean):

| Cold-start mean test coverage | Verdict |
|-------------------------------|---------|
| >= 60.0% | **STRONG POSITIVE** -- GigaEvo substantially exceeds GEPA (+7.67pp); cold start is highly effective on HoVer |
| [55.0%, 60.0%) | **POSITIVE** -- GigaEvo reliably beats GEPA; meaningful improvement in retrieval quality |
| (52.33%, 55.0%) | **SUGGESTIVE-SIG / SUGGESTIVE-NS** -- mean above GEPA but improvement modest (<2.67pp); significance depends on SD |
| [45.0%, 52.33%] | **NULL** -- GigaEvo does not reliably beat GEPA; evolution may not be effective for retrieval coverage optimization |
| < 45.0% | **NEGATIVE** -- evolution degrades performance below the empty-prompt baseline region; possible fitness landscape pathology |

The SUGGESTIVE/POSITIVE boundary at 55.0% is chosen as the GEPA benchmark + 2.67pp,
mirroring the approximate noise floor observed in HotpotQA experiments (~2.4pp). The STRONG
POSITIVE boundary at 60.0% represents a 7.67pp improvement over GEPA, which would be an
unambiguous signal.

### Secondary hypothesis: convergence dynamics

**Pre-registered prediction**: The best-by-val program emerges at birth-generation >= 10
on average, consistent with HotpotQA cold-start behavior (birth-gen 11-19 across 4 runs).
The 7-step chain with 3 retrieval hops has a larger search space than the 6-step HotpotQA
chain, which may slow convergence further.

**Threshold**: Mean birth-generation >= 10 is CONFIRMED (normal cold-start convergence);
< 10 is EARLY (faster convergence than expected, possibly due to the discrete fitness
landscape providing fewer gradient signals).

### Distribution characterization (primary secondary result)

The inter-run SD of test retrieval coverage is a primary output. This is the first
measurement of GigaEvo run-to-run variance on HoVer. Expected: SD between 1-4pp based
on HotpotQA cold-start (SD=1.00pp). However, the discrete fitness metric (0/1 per sample)
may produce higher variance than the continuous EM metric.

---

## 3. Independent Variables

**There are no independent variables in this experiment.** All four runs are identically
configured. This is a pure n=4 replication to establish the cold-start performance
distribution on HoVer.

The scientific value lies entirely in characterizing the baseline distribution: mean, SD,
convergence trajectory, and comparison against the GEPA benchmark. This mirrors the design
philosophy of the HotpotQA cold_start experiment (PR #75), which demonstrated that n=4
replication of a single condition yields more scientific value than n=1 per cell across
multiple conditions when no prior distribution exists.

---

## 4. Dependent Variables

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test retrieval coverage at gen 25 (best-by-val) | 300-sample held-out test set; discrete coverage scoring; thinking mode Qwen3-8B | **YES** -- primary |
| Val-test gap | Val coverage (from Redis `valid_frontier_fitness`) minus test coverage | YES -- secondary |
| Inter-run SD of test coverage | SD of test coverage across the 4 runs | YES -- first within-experiment SD estimate for HoVer |
| Birth-generation of best-by-val program | From `valid_frontier_fitness` Redis key trajectory | NO -- convergence diagnostic |
| Gen-0 val coverage | From Redis at gen 0; cold-start initialization check | NO -- sanity check |
| Val frontier trajectory (gen 1-25) | Per-generation `valid_frontier_fitness` | NO -- convergence diagnostic |

**Primary metric**: Test retrieval coverage at final generation (gen 25), best-by-val
program, evaluated on the fixed 300-sample held-out test set, thinking mode Qwen3-8B.
This is the same metric reported for GEPA (52.33%).

**Gen-0 diagnostic**: The unoptimized baseline chain with empty-prompt LLM steps is
expected to produce val coverage near 0.0% (the 3-sample baseline test showed 0/3 = 0.0%
coverage). If gen-0 val coverage exceeds 20% for any run, pause and verify the
initialization is correct before proceeding.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Chain topology | 7-step fixed (3 tool, 4 LLM) | HoVer static mode; 3 retrieval hops |
| Fitness metric | Retrieval coverage (discrete: all 3 gold docs found = 1, else 0) | The only fitness metric for HoVer; defined in `metrics.yaml` |
| Validation sample size | 300 (first 300 train samples, hardcoded in `validate.py`) | Default; `load_context(n_samples=300)` |
| `problem.name` | `chains/hover/static` | The only HoVer problem variant |
| `prompts` | `default` | No HoVer-specific prompts exist; default GigaEvo optimizer prompts |
| `pipeline` | `standard` | Correct for HoVer; validate.py returns `dict` (not tuple) |
| Chain LLM | Qwen3-8B, thinking mode ON (default chat template), max_tokens=32768 | Required for GEPA comparison |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507, one server per run | Consistent with all HotpotQA experiments |
| `model_name` | **`Qwen3-235B-A22B-Thinking-2507`** -- requires explicit Hydra override (default is `deepseek/deepseek-v3.2`) | Must match deployed model name on local Qwen3-235B servers |
| `llm_base_url` | **`http://<mutation_ip>:8777/v1`** -- requires explicit Hydra override per run (default is OpenRouter) | One mutation LLM per run; see Section 6 for assignments |
| Seed initialization | **Cold start** -- no `program_loader.problem_dir` | Defines the cold-start condition; baseline.py in `initial_programs/` |
| `num_parents` | **1** -- requires explicit Hydra override (default = 2) | Single-parent mutation; mirrors HotpotQA cold_start design |
| `max_elites_per_generation` | **8** -- requires explicit Hydra override (default = 5) | Mirrors HotpotQA cold_start design; 8 elites = 8 mutations/gen |
| `max_mutations_per_generation` | **8** | With num_parents=1 and max_elites=8: C(8,1)=8, capped at 8 |
| `mutation_mode` | `rewrite` | Default; compatible with num_parents=1 |
| `parent_selector` | `AllCombinationsParentSelector` | Standard selector |
| `stage_timeout` | 3000 | Default is 2400s. The 7-step chain (vs 6-step HotpotQA) with 300 val samples needs margin. 3000s provides 1.25x over default. See Section 12 for risk analysis. |
| `dag_timeout` | **7200** -- set as explicit Hydra override for auditability | Matches default; stage_timeout (3000) + mutation stages (~2000) + headroom (2200). Explicit override ensures `--cfg job` verification captures it. |
| `max_generations` | 25 | HotpotQA cold-start stagnation at birth-gen 11-19; 25 gens provides >= 1.3x margin |
| `step_max_tokens` | 32768 (client default for Qwen3-8B) | Not overridden; Qwen3-8B default from `LLMClient.DEFAULT_GENERATION_KWARGS` |
| Test evaluation | Fixed 300-sample test set; thinking mode verified | `test.py --mode redis` |
| HTTP timeout | 600s (`httpx.Timeout(timeout=600.0)`) | Consistent with HotpotQA experiments |

**[Critical: `num_parents=1`]**: Default in `config/constants/evolution.yaml` is
`num_parents: 2`. All four runs must include `num_parents=1` as an explicit Hydra override.
The mandatory `--cfg job` pre-launch check must confirm `num_parents: 1` for all four runs.

**[Critical: `max_elites_per_generation=8`]**: Default is 5. Must appear explicitly in
every launch command. The `--cfg job` check must confirm `max_elites_per_generation: 8`
for all runs.

**[Critical: `pipeline=standard`]**: HoVer's `validate.py` returns a plain dict
(`{"fitness": ..., "is_valid": 1}`), not a tuple. The `standard` pipeline is correct.
Do NOT use `pipeline=hotpotqa_asi` -- that is HotpotQA-specific and would fail or produce
incorrect behavior on HoVer.

---

## 6. Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | Seed | `num_parents` | `max_elites` | `max_mut` | `stage_timeout` | `dag_timeout` | `max_gen` | Val N | `model_name` | `llm_base_url` |
|-----|-------|-----------|-----------|-----------|----------------|------|:-------------:|:------------:|:---------:|:--------------:|:------------:|:--------:|:-----:|-------------|----------------|
| H1 | hover-cold-1 | 9 | `standard` | `default` | `chains/hover/static` | **Cold** | **1** | **8** | 8 | **3000** | **7200** | 25 | 300 | **Qwen3-235B-A22B-Thinking-2507** | **`http://10.226.72.211:8777/v1`** |
| H2 | hover-cold-2 | 10 | `standard` | `default` | `chains/hover/static` | **Cold** | **1** | **8** | 8 | **3000** | **7200** | 25 | 300 | **Qwen3-235B-A22B-Thinking-2507** | **`http://10.226.15.38:8777/v1`** |
| H3 | hover-cold-3 | 11 | `standard` | `default` | `chains/hover/static` | **Cold** | **1** | **8** | 8 | **3000** | **7200** | 25 | 300 | **Qwen3-235B-A22B-Thinking-2507** | **`http://10.226.185.47:8777/v1`** |
| H4 | hover-cold-4 | 12 | `standard` | `default` | `chains/hover/static` | **Cold** | **1** | **8** | 8 | **3000** | **7200** | 25 | 300 | **Qwen3-235B-A22B-Thinking-2507** | **`http://10.225.51.251:8777/v1`** |

**Bold values require explicit Hydra overrides**: `num_parents=1` (default is 2);
`max_elites_per_generation=8` (default is 5); `stage_timeout=3000` (default is 2400);
`dag_timeout=7200` (matches default but set explicitly for auditability);
`model_name=Qwen3-235B-A22B-Thinking-2507` (default is `deepseek/deepseek-v3.2`);
`llm_base_url=http://<mutation_ip>:8777/v1` (default is OpenRouter).
The cold-start condition requires the **absence** of `program_loader.problem_dir`.

**Run naming convention**: H-prefix for HoVer (distinguishing from T-prefix HotpotQA
cold_start runs).

**Cold-start initialization (all runs)**: Do NOT pass `program_loader.problem_dir`.
GigaEvo initializes the archive from the problem directory's `initial_programs/baseline.py`
program. The baseline has an empty system_prompt and minimal LLM step fields. Verify at
gen 0 that val coverage < 20% for all four runs before proceeding.

**Combinatorics verification** (contingent on `max_elites_per_generation=8` override):

| Run | num_parents | max_elites | Parent combos | max_mutations | Actual mut/gen (mature archive) |
|-----|:-----------:|:---------:|:-------------:|:-------------:|:-------------------------------:|
| H1 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| H2 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| H3 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| H4 | 1 | 8 | C(8,1) = 8 | 8 | 8 |

Note: early generations will have fewer than 8 mutations while the archive fills (gen 0:
1 elite, 1 mutation). Archive reaches maturity (~8 elites) by gen 3-5. This early-generation
throughput deficit is symmetric across all four runs.

**Chain LLM assignment** (one chain server per run, no sharing):

| Run | Chain LLM URL (`HOVER_CHAIN_URL`) |
|-----|-----------------------------------|
| H1 | `http://10.226.17.25:8001/v1` |
| H2 | `http://10.226.17.25:8000/v1` |
| H3 | `http://10.225.185.235:8001/v1` |
| H4 | `http://10.225.185.235:8000/v1` |

**Mutation LLM assignment** (one per run, from the 4-server pool):

| Run | Mutation LLM URL |
|-----|------------------|
| H1 | `http://10.226.72.211:8777/v1` |
| H2 | `http://10.226.15.38:8777/v1` |
| H3 | `http://10.226.185.47:8777/v1` |
| H4 | `http://10.225.51.251:8777/v1` |

**Redis DBs**: 9, 10, 11, 12. Verify 0 keys in all four DBs before launch via
`tools/flush.py --db 9 10 11 12`. (DBs 0-8 occupied by vartodd circuit_evolve runs.)

---

## 7. Sample Size Justification

**N=4 independent replications of a single cold-start condition.** This mirrors the
HotpotQA cold_start experiment design (PR #75) and is the standard GigaEvo replication
count for baseline characterization.

**What N=4 enables**:

1. **Within-experiment SD estimate**: The inter-run SD across H1-H4 is the first direct
   measure of test retrieval coverage variance under a fixed GigaEvo condition on HoVer.
   This SD is itself a primary result.

2. **One-sample t-test against GEPA**: With N=4, df=3, we compute a one-sample
   t-statistic against the GEPA benchmark (52.33%). The critical t-value for one-sided
   alpha=0.05, df=3 is 2.353.

3. **Mean CI**: The cold-start mean gets a t-based 95% CI:
   mean +/- t(0.025, df=3) * SD/sqrt(4) = mean +/- 3.182 * SD/2.

**Anticipated SD**: HotpotQA cold-start had SD=1.00pp (n=4). HoVer's discrete fitness
metric (0/1 per sample) may produce higher variance. We conservatively estimate SD=2-4pp.

**Formal power -- MDE formula**: The MDE for a one-sample t-test at 80% power is:

    MDE = (t_alpha + t_beta) * sigma / sqrt(N)

where t_alpha = t(0.95, df=3) = 2.353 and t_beta = t(0.80, df=3) = 1.250. At SD=2pp:

    MDE = (2.353 + 1.250) * 2 / sqrt(4) = 3.603 * 1 = 3.60pp

At SD=4pp:

    MDE = (2.353 + 1.250) * 4 / sqrt(4) = 3.603 * 2 = 7.21pp

The experiment has ~80% power to detect a 3.6pp improvement over GEPA at SD=2pp (i.e.,
detectable if true mean >= 55.93%). At SD=4pp, we need a true mean >= 59.54% for 80%
power. The POSITIVE threshold (55.0%) is within the detectable range at SD=2pp.

**Why not N>4?** We have exactly 4 chain LLM endpoints. Running all 4 in parallel
minimizes wall time. N=8 (two sequential waves of 4) would double wall time for marginal
power gain when the primary goal is establishing the baseline distribution.

---

## 8. Statistical Test

### Test 1: One-sample t-test -- cold-start mean vs. GEPA (primary)

**Comparison**: Mean test retrieval coverage across H1-H4 vs. GEPA benchmark of 52.33%.

**Test statistic**: t = (cold_mean - 52.33%) / (cold_SD / sqrt(4)), df=3.
One-sided (H1: cold_mean > 52.33%). Pre-registered significance threshold: p < 0.05.

**Verdict table**:

| t-test result | Cold-start mean | Verdict |
|:-------------:|:---------------:|---------|
| p < 0.05 | >= 60.0% | **STRONG POSITIVE** -- GigaEvo substantially and significantly beats GEPA |
| p < 0.05 | [55.0%, 60.0%) | **POSITIVE** -- GigaEvo significantly beats GEPA |
| p < 0.05 | (52.33%, 55.0%) | **SUGGESTIVE-SIG** -- statistically significant but modest improvement; effect size may not be practically meaningful |
| p >= 0.05 | > 52.33% | **SUGGESTIVE-NS** -- directionally above GEPA but not significant at N=4; underpowered; needs N>=8 to resolve |
| p >= 0.05 | <= 52.33% | **NULL** -- no evidence GigaEvo beats GEPA on HoVer |
| cold_mean < 45.0% | any | **NEGATIVE** -- reported regardless of p-value |

### Test 2: Convergence dynamics (exploratory)

**Criterion**: Mean birth-generation of the best-by-val program across H1-H4.

| Mean birth-gen | Verdict |
|:--------------:|---------|
| >= 10 | **CONFIRMED** -- normal cold-start convergence, consistent with HotpotQA pattern |
| < 10 | **EARLY** -- faster convergence than HotpotQA; possibly due to discrete fitness |

### Test 3: Inter-run SD (descriptive, primary secondary result)

| SD | Interpretation |
|----|----------------|
| < 2pp | Tight distribution; cold-start performance is reliable; consistent with HotpotQA |
| 2-5pp | Moderate variance; N=4 was necessary for mean estimation |
| > 5pp | High variance; discrete fitness landscape may produce multi-modal outcomes; N>=8 needed |

### Binomial confidence intervals (all runs)

Individual run CIs (Wilson score interval, 300 test samples):
```
p_hat = successes / 300
z = 1.96
denom = 1 + z^2/300
centre = (p_hat + z^2/(2*300)) / denom
margin = z * sqrt(p_hat*(1-p_hat)/300 + z^2/(4*300^2)) / denom
CI = [centre - margin, centre + margin]
```
At p=0.52: CI ~ [46.4%, 57.5%]. At p=0.60: CI ~ [54.3%, 65.4%].
Wilson score interval chosen over Wald for better coverage probability near
boundary values (0 or 1), which may occur at gen 0.

Mean CI (t-based, df=3):
```
CI = cold_mean +/- 3.182 * cold_SD / 2
```

Both reported in the Phase 5 results document.

**Significance threshold**: alpha = 0.05
**How computed**: One-sample t-test (scipy.stats.ttest_1samp), one-sided. Bootstrapped CI
as sensitivity check: resample H1-H4 test coverage values with replacement (10,000
iterations), report 2.5th and 97.5th percentiles.

---

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| **Cold-start archive under-utilization in early generations** | All runs start with 1 elite at gen 0, producing only 1 mutation. Throughput deficit of ~15 mutations over gens 0-3. | Pre-registered acknowledgment. Deficit is symmetric across all 4 runs (no differential confound). By gen 4-5, archive reaches maturity at 8 mut/gen. Report actual mutations/gen from logs at gen 0-5 in Phase 5. |
| **`num_parents` default = 2** | If `num_parents=1` is omitted from any launch command, that run becomes a crossover run with different mutation mechanism and throughput. | Mandatory `--cfg job` pre-launch check: confirm `num_parents: 1` for all four runs. Highest-priority verification item. |
| **`max_elites_per_generation` default = 5** | Omission silently reduces mutations to 5/gen (not 8), making runs incomparable to HotpotQA cold_start reference. | Mandatory `--cfg job` check: confirm `max_elites_per_generation: 8` for all four runs before launch. |
| **Discrete fitness landscape** | Retrieval coverage is 0/1 per sample. With 300 val samples, fitness resolution is 1/300 = 0.33%. This coarse signal may cause the mutation LLM to receive less informative failure feedback than HotpotQA's continuous EM/F1 scores. | Acknowledged as a fundamental task property. If convergence is notably slower or noisier than HotpotQA, this is a scientific finding about discrete vs. continuous fitness landscapes for LLM-guided mutation. |
| **Server load asymmetry** | H1/H2 share chain LLM host A (10.226.17.25); H3/H4 share host B (10.225.185.235). Two-cluster design technically violates i.i.d. assumption. | Monitor eval times per host at gen 5. Report host-stratified means in Phase 5. Flag if host-level divergence > 3pp. |
| **BM25 retrieval ceiling** | BM25 with k=7 (hops 1-2) and k=10 (hop 3) has a fixed recall ceiling. If the gold documents are not in BM25's top-k for ANY reasonable query, no amount of prompt optimization can find them. | This is a known upper bound on performance. In Phase 5, report the fraction of test samples where at least one gold doc is unreachable by BM25 (if feasible to compute). This is a characteristic of the task, not a confound of the experiment. |
| **`pipeline=standard` correctness** | Standard pipeline uses `DefaultPipelineBuilder` which handles dict-returning validate.py. If validate.py were to return a tuple (like HotpotQA), results would be corrupted. | Verified: HoVer validate.py returns `{"fitness": ..., "is_valid": 1}` (plain dict). Standard pipeline is correct. Pre-launch: confirm `pipeline: standard` in `--cfg job` output. |
| **7-step chain evaluation time** | The 7-step chain with 3 tool calls (BM25 retrieval) per sample may be slower than HotpotQA's 6-step chain. 300 samples in thinking mode could exceed `stage_timeout`. | Set `stage_timeout=3000` (vs. default 2400). Monitor eval time at gen 1. If median eval time > 2500s, increase to 4000 via amendment before gen 5. |
| **Stale Redis DBs** | DBs 9-12 may contain data from prior experiments. | Mandatory pre-launch: `tools/flush.py --db 9 10 11 12` (preview, then `--confirm`). Must show 0 keys. |
| **No warm-start reference** | Unlike HotpotQA cold_start (which compared against a warm-start distribution), we have no prior HoVer reference. All conclusions are relative to the GEPA benchmark only. | Acknowledged as inherent to being the first HoVer experiment. The GEPA benchmark (52.33%) is a fixed external reference, making the one-sample t-test appropriate. |
| **Thinking mode verification** | If Qwen3-8B falls back to non-thinking mode, results are invalid for GEPA comparison. | Check for `<think>` blocks in chain outputs at gen 1. Invalidate any run where < 95% of outputs contain thinking blocks. |
| **No failure feedback in mutation context** | The `standard` pipeline's `FormatterStage` receives `None` from `FetchArtifact` (because `validate.py` returns a simple dict, not a tuple with failure analysis). The mutation LLM's `formatted` field is empty — it sees fitness scores but no structured analysis of what went wrong on failed samples. This is partially confounded with the discrete fitness signal: both contribute to reduced mutation guidance. A NULL result cannot distinguish whether poor performance is due to discrete fitness, absent failure feedback, or both. | Intentional for the baseline — adding a failure formatter is a natural treatment condition for the next experiment. In Phase 5, explicitly discuss this confound when interpreting results: if NULL, the absence of failure feedback is a leading explanatory candidate alongside discrete fitness. If POSITIVE despite no feedback, that strengthens the case that the fitness signal alone is sufficient for this task. |

---

## 10. Stop Criteria

### Early termination criteria

- **Gen-0 val coverage > 20% for any run**: Halt; the baseline chain should produce near-0%
  coverage. Val coverage > 20% suggests the initialization is not the unoptimized baseline.
  Verify `program_loader.problem_dir` was NOT passed and inspect the gen-0 program.
- **Gen-0 val coverage = exactly 0.0% AND gen-3 val coverage = exactly 0.0%**: If no
  improvement after 3 generations, pause and inspect mutation logs. The discrete fitness
  signal may be too sparse for the mutation LLM. This is an important diagnostic but NOT
  an automatic invalidation -- the run may recover.
- **Invalidity rate > 50% at gen 5 for any run**: Pause; diagnose `stage_timeout`. If
  median eval time exceeds 2500s, increase `stage_timeout` to 4000 before resuming.
- **Gen-0 val fitness = sentinel value (-1000.0) for any run**: Halt; execution error.

### Stagnation-based early completion

If `valid_frontier_fitness` shows no improvement for >= 10 consecutive generations AND the
current generation >= 15, the run may be terminated early. This is not an invalidation.

### Run invalidation criteria

A run is excluded from all analyses if any of the following apply:

1. Thinking mode not active: `<think>` blocks absent from >= 5% of chain outputs at gen 1.
2. Invalidity rate > 90% at gen 10.
3. Gen-0 val coverage > 20% (initialization error detected).
4. `max_elites_per_generation` confirmed at 5 (not 8) in post-hoc log inspection.
5. `num_parents` confirmed at 2 (not 1) in post-hoc log inspection.
6. `pipeline` confirmed as anything other than `standard` in post-hoc inspection.

If one or two runs are invalidated, the remaining valid runs are analyzed and the t-test
is adjusted to the available N. If only 1 run remains valid, the t-test is replaced by a
descriptive summary and the verdict is capped at SUGGESTIVE pending replication.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time per run (300-sample, 25 gens) | ~8-12h (25 gens * ~15-25 min/gen for 300 samples / 4 async workers; 7-step chain ~17% more steps than HotpotQA 6-step) |
| Total wall time (4 runs parallel) | ~12h wall-clock (all 4 runs in parallel; bottleneck is uniform) |
| Redis DBs | 4 (DBs 9, 10, 11, 12) |
| Mutation LLM servers | 4 * Qwen3-235B-A22B-Thinking (one per run) |
| Chain LLM servers | 4 * Qwen3-8B thinking (one per run) |
| Test eval time | ~5 min each * 4 runs = ~20 min total |
| New code required | None -- `chains/hover/static` already implemented with validate.py and test.py |

---

## 12. Open Questions / Risks

### Priority risks

**Risk 1 -- Discrete fitness signal may impede mutation (MEDIUM).**
HotpotQA used continuous metrics (EM, F1) that provide granular feedback: a mutation that
improves answer quality on even one sample produces a measurable fitness change. HoVer's
fitness is 0/1 per sample -- a mutation must improve retrieval coverage on at least 1 of
300 samples to register any fitness improvement (delta = 1/300 = 0.33%). If most samples
are either "easily solvable" (gold docs in BM25 top-7 regardless of query) or "unsolvable"
(gold docs unreachable by BM25), only a narrow band of "improvable" samples exists. The
mutation LLM may receive failure analyses showing the same failures repeatedly with no
signal about what change would help.

**Mitigation**: This is acknowledged but not addressable within the baseline design. If
convergence is poor (< 30% val coverage at gen 10), this risk is likely realized and
future experiments should consider (a) adding partial-credit fitness (e.g., fraction of
gold docs found), or (b) enriching failure feedback with which specific gold docs were
missed.

**Risk 2 -- BM25 retrieval ceiling (MEDIUM).**
The 3-hop chain retrieves 7+7+10=24 passages total. If a gold document's title/content
does not match any plausible query well enough to appear in BM25's top-k, it is
unreachable. The GEPA baseline at 52.33% may already be close to the BM25 ceiling for
this task. There is no dense retriever (ColBERT) fallback.

**Mitigation**: Report the BM25 ceiling analysis in Phase 5 if feasible. If the experiment
produces POSITIVE results despite this ceiling, it demonstrates that query generation
quality (not retriever quality) is the binding constraint.

**Risk 3 -- `stage_timeout` may be insufficient (LOW-MEDIUM).**
The 7-step chain has 3 BM25 retrieval calls and 4 LLM calls per sample. Each BM25 call
loads the ~1.5GB pickle index. With 300 samples and thinking mode (which increases LLM
latency), total eval time per generation could approach 2400s (the default). We set
`stage_timeout=3000` as a precaution.

**Mitigation**: Monitor eval time at gen 1. If median > 2500s, file an amendment to
increase `stage_timeout` to 4000 before gen 5.

**Risk 4 -- No existing HoVer failure formatter (LOW).**
The `standard` pipeline uses GigaEvo's default failure formatting (repr of the result
dict). Unlike HotpotQA's ASI formatter, there is no HoVer-specific structured failure
analysis. The mutation LLM receives raw failure dicts, which may be less informative.
**See Section 9 "No failure feedback in mutation context"** for the full confound analysis
and its partial confounding with the discrete fitness signal.

**Mitigation**: This is intentional for the baseline. If the baseline produces NULL results,
a domain-specific HoVer failure formatter (showing which gold docs were missed, what
queries were generated, etc.) would be a natural treatment condition for the next experiment.

### Scientific open questions after this experiment

- **If POSITIVE or STRONG POSITIVE**: GigaEvo is effective on retrieval coverage tasks.
  Next: (a) HoVer-specific failure formatter (structured analysis of missed documents),
  (b) partial-credit fitness (fraction of gold docs found instead of all-or-nothing),
  (c) topology mutation (allow adding retrieval hops or changing k values).

- **If NULL**: The question is whether the ceiling is BM25-limited or mutation-limited.
  Next: (a) BM25 ceiling analysis (what fraction of gold docs are reachable?), (b)
  partial-credit fitness to provide gradient signal, (c) if BM25 ceiling is high (>70%),
  the binding constraint is query generation quality and richer failure feedback is needed.

- **If NEGATIVE**: Evolution may actively degrade retrieval by producing queries that are
  less effective than the empty-prompt baseline. Inspect evolved chains qualitatively to
  understand the failure mode. The discrete fitness landscape may create deceptive gradients.

---

## Appendix A: Code Verification Required Before Launch

1. **Cold-start archive initialization behavior**: Confirm that running `run.py` without
   `program_loader.problem_dir` initializes from `initial_programs/baseline.py`. Verify
   the code path in `03_plan.md`.

2. **Baseline program content**: Inspect `problems/chains/hover/static/initial_programs/baseline.py`.
   **VERIFIED**: Empty system_prompt, minimal LLM step fields ("aim" and "stage_action"
   with generic text, "reasoning_questions" and "example_reasoning" set to "<none>").
   Expected gen-0 val coverage: ~0-5%.

3. **`num_parents` and `max_elites_per_generation` defaults**: **VERIFIED**: defaults are
   `num_parents: 2` and `max_elites_per_generation: 5` in
   `config/constants/evolution.yaml`. Both require explicit Hydra overrides.

4. **Redis DBs 9-12 empty**: `tools/flush.py --db 9 10 11 12` must show 0 keys before launch.

5. **`pipeline=standard` compatibility**: **VERIFIED**: HoVer `validate.py` returns
   `{"fitness": ..., "is_valid": 1}` (plain dict). Standard pipeline's
   `DefaultPipelineBuilder` handles this correctly.

6. **`stage_timeout` passthrough**: Confirm that `stage_timeout=3000` Hydra override is
   picked up by the standard pipeline's `DefaultPipelineBuilder`. The constructor accepts
   `stage_timeout` parameter which defaults to `DEFAULT_SIMPLE_STAGE_TIMEOUT` (2400s).
   Must verify that the Hydra override reaches this constructor. **VERIFIED**: `standard.yaml`
   now wires `stage_timeout: ${stage_timeout}` and `dag_timeout: ${dag_timeout}` to
   `pipeline_builder`.

7. **`model_name` and `llm_base_url` overrides**: The `--cfg job` output for each run must
   show `model_name: Qwen3-235B-A22B-Thinking-2507` (not `deepseek/deepseek-v3.2`) and
   `llm_base_url: http://<mutation_ip>:8777/v1` (not OpenRouter). These are the two most
   critical overrides — without them, the mutation LLM will attempt to reach OpenRouter via
   Squid proxy, which will either fail or produce degraded results. Verify for all 4 runs.

8. **`dag_timeout` explicit override**: The `--cfg job` output must show `dag_timeout: 7200`.
   While this matches the default, it is set explicitly for auditability.

---

## Appendix B: Decision Tree

```
After gen-25 test evals for all 4 runs (H1, H2, H3, H4):

  Compute: cold_mean = mean(H1, H2, H3, H4)
           cold_SD   = SD(H1, H2, H3, H4)
           t1 = (cold_mean - 52.33%) / (cold_SD / 2)   [vs. GEPA]

                  Test 1: t1 p < 0.05?
                 /                     \
               YES                      NO
                |                       |
        cold_mean >= 60.0%?      cold_mean > 52.33%?
           /         \              /         \
         YES          NO          YES          NO
          |            |           |           |
       STRONG       cold_mean   SUGGEST-NS   NULL
       POSITIVE     >= 55.0%?   (not sig;    (GigaEvo
                    /      \     N>=8)        does not
                 YES        NO               beat GEPA)
                  |          |
              POSITIVE    SUGGEST-SIG
                          (sig, modest)

  Also report:
    Test 2: Mean birth-gen >= 10? (convergence dynamics)
    Test 3: cold_SD -- tight (<2pp), moderate (2-5pp), wide (>5pp)?
```

---

*Ready for Reviewer-2's scrutiny.*
