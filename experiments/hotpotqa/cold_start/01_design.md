# Experimental Design: Cold Start — Basin Escape via n=4 Replication

**Date**: 2026-03-08
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Revised — awaiting Phase 2 approval

---

## 1. Research Question

The crossover experiment (PR #74) closed the last structural hypothesis within the ddce37b4
warm-start framework. Two-parent crossover with 2× throughput did not break stagnation. Run D's
63.00% does not replicate (Run P = 57.33%). Stagnation is now confirmed in 12 consecutive
independent runs across every combination of fitness metric, validation sample size, mutation
prompts, and parent count. The frontier peaks at birth-gen 4–8 in every run without exception.

This pattern is consistent with ddce37b4 being a genuine local optimum in the fitness landscape
as navigated by LLM-guided mutation. The mutation operator explores the neighborhood of the
current archive by reading elite programs and proposing textual modifications. When the archive
converges on programs whose local neighborhood contains no higher-fitness programs, the operator
is trapped — regardless of how many mutations it attempts or how many parents it combines.

**The central unanswered question**: Is the stagnation intrinsic to the HotpotQA static-chain
fitness landscape (i.e., the global optimum is near 57–60% and every start converges there),
or is it specific to the ddce37b4 basin? If cold-start runs from the unoptimized baseline chain
converge to a different, higher plateau, the landscape is multi-modal and ddce37b4 is a
suboptimal attractor. If they converge to the same plateau, the stagnation ceiling is domain-wide.

**Primary research question**: Does initializing the GigaEvo archive from the unoptimized
baseline chain (cold start, no warm-start seed) produce a higher test EM than the warm-start
historical distribution (mean 57.11%, SD 1.68pp, n=3 unconfounded runs), when run under
F1+600 conditions with n=4 independent replications?

With n=4, this experiment also answers for the first time: **what is the cold-start test EM
distribution?** We obtain a mean and inter-run SD, enabling a proper one-sample t-test against
the warm-start historical reference and the GEPA benchmark (62.3%).

---

## 2. Hypotheses

### Primary hypothesis: cold start escapes the ddce37b4 basin

**H0(cold)**: Cold-start runs (initialized from the baseline chain) produce test EM no higher
than the warm-start historical mean of 57.11% (computed from the three unconfounded
F1+600+single-parent warm-start runs: push C=58.67%, crossover P=57.33%, crossover S=55.33%).
The stagnation ceiling is domain-wide, not basin-specific. Cold start converges to the same
quality region as ddce37b4-initialized runs.

**H1(cold)**: The cold-start mean test EM across n=4 runs exceeds 60.0% — the test EM of the
ddce37b4 seed program itself and the upper bound of the warm-start reference range. This
threshold is chosen because any cold-start mean above 60.0% implies that cold start reaches,
on average, at least as good a program as the seed that warm-start runs begin from — indicating
that the stagnation wall of warm-start runs is not a universal landscape ceiling but is specific
to the ddce37b4 attractor. A mean above GEPA (62.3%) would constitute a landmark finding.

**Effect size thresholds** (applied to the n=4 cold-start mean):

| Cold-start mean test EM | Verdict |
|------------------------|---------|
| >= 62.3% (GEPA) | **STRONG POSITIVE** — cold start reliably beats GEPA; ddce37b4 is a suboptimal basin; cold initialization is the recommended default going forward |
| [60.0%, 62.3%) | **POSITIVE** — cold start reaches or exceeds ddce37b4 seed quality on average; distinct basin with higher ceiling than the warm-start attractor |
| [59.51%, 60.0%) | **SUGGESTIVE** — cold start mean exceeds warm-start mean by > noise floor but falls short of ddce37b4 seed quality; evidence for a modestly higher basin |
| [54.71%, 59.51%) | **NULL** — cold start within noise-floor range of warm-start mean; stagnation ceiling is not seed-dependent |
| < 54.71% | **NEGATIVE** — cold start reliably underperforms warm-start; ddce37b4 provides a genuine quality head start that cold start cannot match in 25 gens |

The SUGGESTIVE lower bound of 59.51% = 57.11% + 2.4pp (the empirical noise floor). The
NEGATIVE threshold of 54.71% = 57.11% − 2.4pp.

### Stagnation birth-generation hypothesis (secondary, mechanistic)

**Pre-registered prediction**: Cold-start runs stagnate at birth-gen >= 10 on average, later
than the universal warm-start stagnation pattern (birth-gen 4–8 in all 12 prior runs). The
mechanistic logic: the cold-start archive begins far below any local optimum and must traverse
more of the landscape before convergence. If the fitness gradient is steep, the mutation
operator has a strong signal to follow and will continue improving for more generations.

**Formal threshold**: Mean birth-generation of the best-by-val program across the 4 cold-start
runs >= 10 is classified CONFIRMED (extended exploration observed). Mean < 10 is classified
DISCONFIRMED (cold start stagnates as fast as warm start regardless of initialization quality).

A DISCONFIRMED result would be a significant mechanistic finding: LLM-guided mutation converges
to a basin attractor within 4–8 mutations regardless of starting quality. This would imply that
the effective "step size" of LLM mutation is large — each mutation jumps to a neighborhood
attractor rather than making incremental improvements — and that the landscape topology, not
the starting point, determines convergence speed.

### Informal power note

With n=4 independent replications, this is the first GigaEvo HotpotQA experiment capable of
computing a within-experiment SD and performing a one-sample t-test. The GEPA benchmark (62.3%)
and the warm-start reference mean (57.11%) are both fixed external values, not samples — making
one-sample tests appropriate. See Section 8 for the formal test specification.

---

## 3. Independent Variables

**There is one independent variable in this experiment: seed initialization = cold start
(baseline chain, no program_loader.problem_dir).**

All four runs are identical in every configuration parameter. The experiment is a pure n=4
replication, not a factorial design. The inter-run variance across four identically configured
runs quantifies the test EM distribution under cold-start F1+600 conditions.

**Why not include prompts (NLP vs. default) as a second IV?** NLP prompts showed a null effect
in two prior experiments: nlp_prompts (PR #69, confounded but directionally null) and crossover
(PR #74, P vs S: +2.00pp, McNemar p=0.20, NULL). With three data points pointing toward null,
allocating two of four cold-start slots to a secondary NLP-vs-default comparison would reduce
statistical power on the primary question (cold vs. warm) from n=4 to n=2 per sub-cell — giving
less information about each condition than the historical warm-start record already provides.
The primary question — does cold start escape the basin? — is best answered with maximum
replication in a single fixed condition.

**Why default prompts (not NLP)?** Default prompts are chosen as the fixed condition because
they have the largest unconfounded historical dataset: three warm-start F1+600+single-parent
runs (push C, crossover P, crossover S) with mean 57.11% and SD 1.68pp. This warm-start
reference distribution enables the clearest between-condition comparison.

Note: crossover Run P used NLP prompts (not default), but since NLP showed null effect in that
experiment (P vs S: +2.00pp, p=0.20), Run P is included in the warm-start reference
distribution. This is conservative for H0 (slightly raises the reference mean). However,
a p=0.20 McNemar result at n=1 cannot rule out a NLP effect as large as ~4pp — the 95%
confidence interval for the +2.00pp observed effect spans roughly [−4pp, +8pp]. Run P's
inclusion therefore introduces some reference-mean uncertainty; the pre-registered sensitivity
analysis (Section 8, Test 1) uses the pure-default reference to bound this uncertainty. A
sensitivity analysis excluding Run P (reference mean = 57.00%, n=2 pure-default runs) is
pre-registered and reported in Phase 5.

**Fixed across all four runs**: cold initialization, default prompts (`prompts=default`),
F1 fitness (`chains/hotpotqa/static_f1_600`), 600-sample validation, single-parent mutation
(`num_parents=1`), `pipeline=hotpotqa_asi`.

---

## 4. Dependent Variables

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test EM at gen 25 (best-by-val) | 300-sample held-out test set; EM scoring; thinking mode Qwen3-8B | YES — primary for all runs |
| Val-test gap (within-metric EM) | Val EM (from `valid_frontier_em` Redis key) minus test EM | YES — secondary |
| Inter-run SD of test EM | SD of test EM across the 4 runs | YES — first within-experiment SD estimate for this task |
| Birth-generation of best-by-val program | From `valid_frontier_fitness` Redis key trajectory | NO — stagnation diagnostic |
| Gen-0 val EM | From Redis at gen 0; sanity check for cold-start initialization | NO — initialization verification |
| Val frontier trajectory (gen 1–25) | Per-generation `valid_frontier_fitness` (F1) | NO — convergence diagnostic |
| Val EM trajectory (gen 1–25) | Per-generation `valid_frontier_em` | NO — gap diagnostic |
| Invalidity rate at gen 5 | Fraction of invalid programs per run | NO — monitoring |

**Primary metric**: Test EM at final generation (gen 25), best-by-val program, evaluated on the
fixed 300-sample held-out test set, thinking mode Qwen3-8B. Consistent with all prior
experiments and the GEPA benchmark (62.3%).

**Gen-0 diagnostic**: The unoptimized baseline chain is expected to produce val F1 substantially
below the warm-start starting point. Expected gen-0 val EM ≈ 0.40–0.45 (matching the zero-shot
baseline EM of 42.3%). If gen-0 val EM > 0.55 for any run, the cold start was not correctly
configured — halt and diagnose before proceeding.

**Val EM note**: Val fitness is F1, but the primary metric is test EM. The `valid_frontier_em`
Redis key is populated by `static_f1_600/validate.py` (confirmed working in push Run D and all
four crossover runs). Val EM (not val F1) is used for the val-test gap analysis.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Chain topology | 6-step fixed (2 tool, 4 LLM) | Unchanged across all experiments |
| Fitness metric | F1 (token-level partial credit) | Best gap-compression condition; maximizes comparability to warm-start reference |
| Validation sample size | 600 (fixed, first 600 train samples) | Best gap compression; warm-start reference runs at this setting |
| `problem.name` | `chains/hotpotqa/static_f1_600` | Already implemented and tested in push and crossover |
| `prompts` | `default` | Historical warm-start reference uses default; NLP null in 2 prior experiments |
| Chain LLM | Qwen3-8B, thinking mode ON (default chat template) | Required for GEPA comparison |
| Mutation LLM | Qwen3-235B-A22B-Thinking, one server per run | Consistent with all prior runs |
| `pipeline` | `hotpotqa_asi` | Required for all hotpotqa variants; never `pipeline=standard` |
| Seed initialization | **None** — no `program_loader.problem_dir` | Defines the cold-start condition; absence of this argument is the IV |
| `num_parents` | **1** — requires explicit Hydra override (default = 2) | Single-parent mutation; crossover is a separate concern |
| `max_elites_per_generation` | **8** — requires explicit Hydra override (default = 5) | Consistent with all prior HotpotQA experiments |
| `max_mutations_per_generation` | **8** | With num_parents=1 and max_elites=8: C(8,1)=8, capped at 8 → 8 mutations/gen |
| `mutation_mode` | `rewrite` | Default; compatible with num_parents=1 |
| `parent_selector` | `AllCombinationsParentSelector` | Standard selector; handles num_parents=1 |
| Validation protocol | Fixed sequential (first 600 train samples) | Rotation permanently excluded |
| `stage_timeout` | 6000 | 600-sample eval empirical max ~2300s; 6000 provides 2.6× margin |
| `dag_timeout` | 9000 | stage_timeout (6000) + mutation LLM stages (~1500) + headroom (1500) |
| `max_generations` | 25 (all runs) | Warm-start stagnation confirmed by gen 4–8 in all 12 prior runs; 25 gens provides >= 3× window. If cold-start runs show improvement past gen 15, extension to 40 gens may be pre-registered as an amendment before gen 20 (see Stop Criteria). |
| `step_max_tokens` | 8192 for all LLM steps | Uniform; thinking mode exhausts budget — do not reduce for steps 3/6 |
| Test evaluation | Fixed 300-sample test set; thinking mode verified | Consistent with all prior runs |
| Random failure sampling | All failures returned from validate.py; formatter samples 10 with NO_CACHE | Required; cf0cfc1 |
| HTTP timeout | 600s (`httpx.Timeout(timeout=600.0)`) | Required for 600-sample runs; fixed at c0186a8 |

**[Critical: `num_parents=1`]**: Default in `config/constants/evolution.yaml` is `num_parents: 2`.
All four runs must include `num_parents=1` as an explicit Hydra override. The mandatory `--cfg job`
pre-launch check must confirm `num_parents: 1` for all four runs. Failure converts every run to
a crossover run, invalidating the entire experiment.

**[Critical: `max_elites_per_generation=8`]**: Default is 5. Must appear explicitly in every
launch command. The `--cfg job` check must confirm `max_elites_per_generation: 8` for all runs.

---

## 6. Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | Seed | `num_parents` | `max_elites` | `max_mut` | `stage_timeout` | `dag_timeout` | `max_gen` | Val N | Fitness |
|-----|-------|-----------|-----------|-----------|----------------|------|:-------------:|:------------:|:---------:|:--------------:|:------------:|:--------:|:-----:|:-------:|
| T1 | cold-1 | 0 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | **Cold** | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |
| T2 | cold-2 | 1 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | **Cold** | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |
| T3 | cold-3 | 2 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | **Cold** | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |
| T4 | cold-4 | 3 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | **Cold** | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |

**Bold values require explicit Hydra overrides**: `num_parents=1` (default is 2);
`max_elites_per_generation=8` (default is 5). The cold-start condition requires the
**absence** of `program_loader.problem_dir` — do not pass this argument for any of the four runs.

**Cold-start initialization (all runs)**: Do NOT pass `program_loader.problem_dir`. GigaEvo
initializes the archive from the problem directory's default program (the unoptimized baseline
chain). Verify at gen 0 that val EM < 0.55 for all four runs before proceeding to gen 1.

**Combinatorics verification** (contingent on `max_elites_per_generation=8` override):

| Run | num_parents | max_elites | Parent combos | max_mutations | Actual mut/gen (mature archive) |
|-----|:-----------:|:---------:|:-------------:|:-------------:|:-------------------------------:|
| T1 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| T2 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| T3 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| T4 | 1 | 8 | C(8,1) = 8 | 8 | 8 |

Note: all four runs will have fewer than 8 mutations in early generations while the archive
fills from the single cold-start program. Expected: gen 0 → 1 elite → C(1,1) = 1 mutation;
archive reaches maturity (~8 elites) by gen 3–5. This early-generation throughput deficit
(≈ 15 missed mutations over 25 gens) is symmetric across all four runs — it is an inherent
property of cold start, not a differential confound.

**Chain LLM assignment** (one chain server per run, no sharing):

| Run | Chain LLM URL |
|-----|---------------|
| T1 | `http://10.226.17.25:8001/v1` |
| T2 | `http://10.226.17.25:8000/v1` |
| T3 | `http://10.225.185.235:8001/v1` |
| T4 | `http://10.225.185.235:8000/v1` |

**Mutation LLM assignment** (one per run, from the 4-server pool):

| Run | Mutation LLM URL |
|-----|------------------|
| T1 | `http://10.226.72.211:8777/v1` |
| T2 | `http://10.226.15.38:8777/v1` |
| T3 | `http://10.226.185.131:8777/v1` |
| T4 | `http://10.225.51.251:8777/v1` |

**Redis DBs**: 0, 1, 2, 3. Verify 0 keys in all four DBs before launch. DBs 0–3 were last
used by the crossover experiment (PR #74); confirm flushed via `tools/flush.py --db 0 1 2 3`.

**Warm-start historical reference** (not re-run; used as the comparison distribution for Test 1):

| Run | Condition | Seed | Prompts | Test EM |
|-----|-----------|------|---------|:-------:|
| Push C (PR #73) | F1+default+600, num_parents=1 | warm | default | 58.67% |
| Crossover P (PR #74) | F1+NLP+600, num_parents=1 | warm | NLP | 57.33% |
| Crossover S (PR #74) | F1+default+600, num_parents=1 | warm | default | 55.33% |

Historical warm-start reference: mean = 57.11%, SD = 1.68pp, n=3. Crossover Run P used NLP
prompts (not default), but is included because NLP showed null effect (P vs S: +2.00pp,
p=0.20). Sensitivity analysis excluding Run P is pre-registered (see Section 8).

---

## 7. Sample Size Justification

**N=4 independent replications of a single cold-start condition.** This is the largest
within-cell replication count in any GigaEvo HotpotQA experiment. All prior experiments used
N=1 per cell.

**What N=4 enables that N=1 could not**:

1. **Within-experiment SD estimate**: The inter-run SD across T1–T4 is the first direct measure
   of test EM variance under a fixed GigaEvo condition. This SD is itself a primary result —
   independent of the mean. It allows quantifying how much of the apparent Run D vs. Run P gap
   (63.00% vs. 57.33%, Δ=5.67pp) was systematic vs. random.

2. **One-sample t-test against fixed references**: With N=4, df=3, we compute a one-sample
   t-statistic against the warm-start reference mean (57.11%) and the GEPA benchmark (62.3%).
   The critical t-value for one-sided α=0.05, df=3 is 2.353.

3. **Mean CI**: The cold-start mean gets a t-based 95% CI:
   mean ± t(0.025, df=3) × SD/sqrt(4) = mean ± 3.182 × SD/2.

**Anticipated SD**: The warm-start SD at F1+600+single-parent is 1.68pp over 3 runs. If the
cold-start landscape has similar variance, we expect SD ≈ 2pp.

**Formal power — corrected MDE formula**: The correct MDE for a one-sample t-test at 80%
power is:

    MDE = (t_alpha + t_beta) × sigma / sqrt(N)

where both t-values are evaluated at df = N − 1 = 3: t_alpha = t(0.95, df=3) = 2.353
(one-sided, α=0.05) and t_beta = t(0.80, df=3) = 1.250 (80% power at df=3). At SD=2pp,
N=4:

    MDE = (2.353 + 1.250) × 2 / sqrt(4) = 3.603 × 1 = 3.60pp

At SD=3pp, N=4:

    MDE = (2.353 + 1.250) × 3 / sqrt(4) = 3.603 × 1.5 = 5.40pp

The experiment therefore has approximately **80% power to detect a 3.6pp cold-vs-warm effect
at SD=2pp and N=4**. At SD=3pp, the 80%-power MDE rises to 5.4pp. An earlier draft of this
document incorrectly mixed t and z distributions (using z_{0.80}=0.842 in the denominator
rather than t_{0.80,df=3}=1.250 in the numerator), which understated the MDE. These are the
corrected figures. This is the best-powered design achievable within the 4-run compute budget,
and it substantially exceeds any prior single-cell GigaEvo experiment (all N=1 per cell,
yielding no within-experiment power estimate).

**Noise floor reminder**: The empirical retest noise floor is 2.4pp (measured at
step_max_tokens=2048; borderline zone [+2.4pp, +3.5pp) at step_max_tokens=8192). For the
mean-level t-test (Test 1), the noise floor applies to individual run comparisons but the
t-test itself uses the within-experiment SD and is not dependent on the 2.4pp calibration.

---

## 8. Statistical Tests

### Test 1: One-sample t-test — cold-start mean vs. warm-start reference (primary)

**Comparison**: Mean test EM across T1–T4 vs. warm-start reference mean of 57.11%.

**Test statistic**: t = (cold_mean − 57.11%) / (cold_SD / sqrt(4)), df=3.
One-sided (H1: cold_mean > 57.11%). Pre-registered significance threshold: p < 0.05.

**Verdict table**:

| t-test result | Cold-start mean | Verdict |
|:-------------:|:---------------:|---------|
| p < 0.05 | >= 60.0% | **POSITIVE** — cold start significantly outperforms warm-start reference; basin escape confirmed at this sample size |
| p < 0.05 | [59.51%, 60.0%) | **SUGGESTIVE** — significant improvement over warm-start reference but below ddce37b4 seed quality; replicate |
| p >= 0.05 | >= 60.0% | **SUGGESTIVE** — cold-start mean above ddce37b4 seed quality but not significant at N=4; N >= 8 required |
| p >= 0.05 | [59.51%, 60.0%) | **SUGGESTIVE** — cold-start mean above the noise floor (> 57.11% + 2.4pp) but t-test not significant; N >= 8 required for resolution |
| p >= 0.05 | [54.71%, 59.51%) | **NULL** — cold start indistinguishable from warm-start reference; stagnation ceiling not seed-dependent |
| cold_mean < 54.71% | any | **NEGATIVE** — cold start underperforms warm-start; reported regardless of t-test result |

**Sensitivity analysis**: Test 1 is re-run with reference mean = 57.00% (pure-default warm-start
runs only: push C=58.67%, crossover S=55.33%; n=2, SD=2.36pp). If the verdict changes between
the two reference sets, results are reported as SENSITIVE.

### Test 2: One-sample t-test — cold-start mean vs. GEPA (secondary)

**Test statistic**: t = (cold_mean − 62.3%) / (cold_SD / sqrt(4)), df=3.
One-sided (H1: cold_mean > 62.3%). Pre-registered threshold: p < 0.05.

| t-test result | Any run >= 62.3%? | Verdict |
|:-------------:|:-----------------:|---------|
| p < 0.05 | — | **STRONG POSITIVE** — cold start significantly beats GEPA in expectation; landmark result |
| p >= 0.05 | YES | **POSITIVE (single run)** — at least one cold-start run beats GEPA, but distribution mean does not; cold-start landscape includes GEPA-beating programs but they are not reliable at N=4 |
| p >= 0.05 | NO | **NULL vs GEPA** — cold start does not reliably beat GEPA |

### Test 3: Stagnation birth-generation (exploratory)

**Criterion**: Mean birth-generation of the best-by-val program across T1–T4. Pre-registered
prediction: mean >= 10 (cold start exhibits extended exploration relative to warm-start
pattern of birth-gen 4–8).

| Mean birth-gen | Verdict |
|:--------------:|---------|
| >= 10 | **CONFIRMED** — extended exploration phase observed |
| < 10 | **DISCONFIRMED** — cold start stagnates as fast as warm start despite beginning 20pp below any known local optimum |

This test is exploratory and does not modify the primary verdict from Test 1. A DISCONFIRMED
result — convergence within 4–8 mutations regardless of initialization quality — would be a
significant mechanistic finding warranting dedicated analysis in Phase 5.

### Test 4: Inter-run SD (descriptive, primary secondary result)

The SD of test EM across T1–T4 is reported as a primary scientific output alongside the mean.

| SD | Interpretation |
|----|----------------|
| < 2pp | Tight distribution; cold-start performance is reliable; single-run results at this condition are relatively informative |
| 2–5pp | Similar to or higher than warm-start SD (1.68pp); substantial run-to-run noise; N=4 was necessary |
| > 5pp | Extreme landscape variance; no firm conclusions about the mean without much larger N; multiple attractors may exist |

### Binomial confidence intervals (all runs)

Individual run CIs:
```
CI_lower = test_EM − 1.96 × sqrt(p × (1−p) / 300)
CI_upper = test_EM + 1.96 × sqrt(p × (1−p) / 300)
```

Mean CI (t-based, df=3):
```
CI = cold_mean ± 3.182 × cold_SD / 2
```

Both reported in Section 5 of the results document.

---

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| **Cold-start archive under-utilization in early generations** | All four runs start with 1 elite at gen 0 → only 1 mutation at gen 0. Throughput deficit of ≈ 15 mutations over gens 0–3. | Pre-registered acknowledgment. The deficit is symmetric across all four runs (no differential confound within experiment). By gen 4–5, the archive reaches maturity and throughput equalizes at 8 mut/gen. Report actual mutations/gen from logs at gen 0–5 in Phase 5. If cold-start mean still exceeds warm-start mean despite this deficit, the seed effect dominates. |
| **`num_parents` default = 2** | If `num_parents=1` is omitted from any launch command, that run becomes a crossover run — changing mutation mechanism and throughput. | Mandatory `--cfg job` pre-launch check: confirm `num_parents: 1` for all four runs. This is the single highest-priority verification item. |
| **`max_elites_per_generation` default = 5** | Omission silently reduces mutations to 5/gen (not 8), making all four runs incomparable to the warm-start reference. If some runs have the override and others do not, runs are not identically configured. | Mandatory `--cfg job` check: confirm `max_elites_per_generation: 8` for all four runs before launch. |
| **Cold start accidentally configured as warm start** | If `program_loader.problem_dir` is inadvertently passed for any run, that run is effectively a warm-start run — inflating the apparent cold-start mean. | Mandatory pre-launch: confirm `--cfg job` output for all four runs does NOT contain `program_loader.problem_dir`. Also verify gen-0 val EM < 0.55 for all four runs before proceeding to gen 1. If any run shows gen-0 val EM > 0.55, halt. |
| **`static_f1_600` default program may not be the unoptimized baseline** | If the problem directory was created with the ddce37b4 evolved program as its default (e.g., copy-pasted during push experiment setup), the "cold start" is actually a warm start. | Pre-launch inspection of the default program file in `problems/chains/hotpotqa/static_f1_600/` is mandatory. Must be the unoptimized baseline chain. Expected gen-0 val EM: 0.40–0.45. Halt if > 0.55. |
| **Stale Redis DBs 0–3** | DBs 0–3 were used by the crossover experiment (PR #74). If not flushed, prior run data contaminates new runs. | Mandatory pre-launch: `tools/flush.py --db 0 1 2 3` (preview, then `--confirm`). Must show 0 keys before any run launches. |
| **Server load asymmetry across runs** | T1/T2 share chain LLM host A (10.226.17.25); T3/T4 share host B (10.225.185.235). The paired host structure (T1/T2 on host A; T3/T4 on host B) creates a two-cluster design that technically violates the i.i.d. assumption of the one-sample t-test; however, with identical model weights and configuration across both hosts, the within-host correlation is expected to be negligible relative to the between-run variance driven by stochastic optimization. | Monitor invalidity rates and eval times at gen 5 separately for T1/T2 vs T3/T4. In Phase 5, report host-stratified means (mean of T1/T2 vs. mean of T3/T4) as a diagnostic; flag as a limitation if they differ by > 3pp. A > 3pp host-level divergence would be noted as a potential i.i.d. violation in the results document. |
| **Warm-start reference heterogeneity** | The reference distribution includes one NLP-prompt run (crossover P), included under the null-NLP justification. If NLP actually has a positive effect (~2pp), the reference mean is slightly inflated, reducing apparent cold-start advantage. | Sensitivity analysis: re-run Test 1 using reference mean = 57.00% (pure-default runs only: push C, crossover S). If verdict changes, report as SENSITIVE. Pre-registered above. |

---

## 10. Stop Criteria

### Stagnation-based early completion (all runs)

If `valid_frontier_fitness` shows no improvement for >= 10 consecutive generations AND the
current generation >= 15, the run may be terminated early. This is not an invalidation — it
is early completion consistent with the pre-registered stagnation pattern.

**Cold-start extension rule**: If any run shows frontier improvement past gen 15 (which would
be the first such observation in 12+ GigaEvo runs), that run should be allowed to complete
the full 25 generations. If all four runs are still improving at gen 20, the researcher may
pre-register an amendment extending max_generations to 40 before reaching gen 20. The
amendment must be filed before gen 20 to remain pre-registered.

### Early termination criteria

- **Invalidity rate > 50% at gen 5 for any run**: Pause; diagnose stage_timeout. If median
  eval time exceeds 5000s, increase stage_timeout to 8000 before resuming.
- **Gen-0 val fitness = 0.0 for any run**: Halt; diagnose before proceeding.
- **Gen-0 val EM > 0.55 for any run**: Halt immediately — do not wait for gen 0 to complete
  all mutations before applying this check. The gen-0 val EM check is applied to the **first
  completed program evaluation** (the initial archive entry, before any mutations). In the
  logs this appears as the first recorded `valid_iter_fitness` entry; in Redis, check
  `{prefix}:metrics:history:program_metrics:valid_iter_fitness_mean` after 1 completed
  evaluation and read the EM field. If it exceeds 0.55, stop before further mutations begin.
  Verify that `program_loader.problem_dir` was not passed and inspect the default program
  in `static_f1_600/`. Restart with correct config.

### Run invalidation criteria

A run is excluded from all analyses if any of the following apply:

1. Thinking mode not active: `<think>` blocks absent from >= 5% of chain outputs at gen 1.
2. `pipeline=standard` used (repr-contamination bug).
3. Invalidity rate > 90% at gen 10.
4. Gen-0 val EM > 0.55 (warm-start initialization detected; cold-start condition violated).
5. `max_elites_per_generation` confirmed at 5 (not 8) in post-hoc log inspection.
6. `num_parents` confirmed at 2 (not 1) in post-hoc log inspection.

If one or two runs are invalidated, the remaining valid runs are analyzed and the t-test is
adjusted to the available N (with correspondingly wider CI and higher critical t-value). If
only 1 run remains valid, the t-test is replaced by a descriptive summary and the verdict is
capped at SUGGESTIVE pending replication.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time per run (600-sample, 25 gens) | ~10–17h (25 gens × ~24 min/gen for 600 samples / 4 async workers; stagnation-based early completion may reduce) |
| Total wall time (4 runs parallel) | ~17h wall-clock (all 4 runs identical configuration; bottleneck is uniform) |
| Redis DBs | 4 (DBs 0, 1, 2, 3) |
| Mutation LLM servers | 4 × Qwen3-235B-A22B-Thinking (one per run; all 4 servers assigned) |
| Chain LLM servers | 4 × Qwen3-8B thinking (one per run; all 4 endpoints assigned) |
| Test eval time | ~5 min each × 4 runs = ~20 min total |
| New code required | None — `static_f1_600` already implemented (push). Cold start = absence of `program_loader.problem_dir`. No code changes. |

---

## 12. Open Questions / Risks

### Priority risks

**Risk 1 — Cold start correctly configured (CRITICAL).**
The cold-start condition relies on NOT passing `program_loader.problem_dir`. GigaEvo's archive
initialization behavior when this argument is absent must be confirmed in the codebase during
Phase 3: what program populates the gen-0 archive? Is it the problem directory's default
program? Is there any fallback warm-start behavior? The plan phase must document the exact
code path and confirm that cold start is achievable with the current GigaEvo version. This
is the highest-priority pre-launch verification item.

**Risk 2 — Baseline chain quality in `static_f1_600`.**
The problem directory `problems/chains/hotpotqa/static_f1_600/` was created for the push
experiment. Its default program must be the unoptimized baseline chain, not a copy of any
evolved program. Pre-launch inspection is mandatory. Expected gen-0 val EM: ~0.42.

**Risk 3 — Cold start performs poorly, making 25 gens insufficient.**
The cold start begins from val EM ~42%, roughly 20pp below the warm-start starting point
(~60%). If the fitness gradient is gradual, 25 gens (≈ 200 total program evaluations) may not
be enough to converge to the warm-start quality range. Mitigation: if all four runs are still
improving at gen 20 with no stagnation detected, the researcher may extend to 40 gens by
pre-registering an amendment before gen 20.

**Risk 4 — Large inter-run SD reduces test power.**
If cold_SD > 4pp (possible if different runs land in different basin attractors), the t-test
will have insufficient power to reject H0 at N=4, even if the true cold-start mean is well
above the warm-start reference. This is itself a scientifically important result (extreme
variance), but it precludes strong mean-level conclusions and calls for N >= 8 replication.

### Scientific open questions after this experiment

- **If cold-start mean >= 60.0% (POSITIVE or STRONG POSITIVE)**: ddce37b4 is a suboptimal
  attractor. The landscape has higher-quality basins accessible from the unoptimized baseline.
  Priority follow-up: (a) N >= 8 cold-start runs to narrow the mean CI; (b) qualitative
  inspection of structural differences between cold-start evolved programs and ddce37b4-derived
  programs; (c) test whether warm-starting from a cold-start-evolved program combines basin
  quality with convergence speed.

- **If cold-start mean is in [54.71%, 59.51%) (NULL)**: the stagnation ceiling is largely
  domain-wide. Both warm and cold start converge to similar quality. Next direction: structural
  changes to the chain (topology mutation, new tool steps, re-ranking) or fundamentally
  different search mechanisms (population diversity forcing, simulated annealing with restart).

- **If cold-start mean < 54.71% (NEGATIVE)**: warm-start provides a genuine quality head-start
  advantage. ddce37b4 should remain the standard initialization. The question shifts to whether
  more total evolution steps (50+ gens of cold start) can eventually exceed the warm-start
  plateau, or whether cold start simply converges to a lower basin.

- **If Test 3 (birth-gen) is DISCONFIRMED** (cold stagnates at birth-gen < 10 despite starting
  from ~42%): LLM-guided mutation converges to a basin attractor within 4–8 steps regardless
  of initialization quality. The effective "step size" of LLM mutation is large — the operator
  jumps to a nearby attractor rather than making incremental improvements. This motivates
  random restarts or injection of structurally diverse programs at regular intervals to force
  the archive into new basin exploration.

---

## Appendix A: Code Verification Required Before Launch

The following must be verified against the codebase during the plan phase (before any launch):

1. **Cold-start archive initialization behavior**: Confirm that running `run.py` without
   `program_loader.problem_dir` initializes the archive from the problem directory's default
   program. Identify and document the exact code path responsible for archive initialization.
   Confirm in `03_plan.md`.

2. **`static_f1_600` default program content**: Inspect
   `problems/chains/hotpotqa/static_f1_600/` for the default program file. Confirm it is the
   unoptimized baseline chain. Expected gen-0 val EM when used as cold start: 0.40–0.45.

3. **`num_parents` and `max_elites_per_generation` defaults**: Confirm that
   `config/constants/evolution.yaml` still sets `num_parents: 2` and
   `max_elites_per_generation: 5`. If these have changed, update the launch command notes.

4. **Redis DBs 0–3 empty**: `tools/flush.py --db 0 1 2 3` (preview) must show 0 keys before
   any run launches.

---

## Appendix B: Decision Tree

```
After gen-25 test evals for all 4 runs (T1, T2, T3, T4):

  Compute: cold_mean = mean(T1, T2, T3, T4)
           cold_SD   = SD(T1, T2, T3, T4)
           t1 = (cold_mean − 57.11%) / (cold_SD / 2)   [vs. warm-start ref]
           t2 = (cold_mean − 62.3%)  / (cold_SD / 2)   [vs. GEPA]

                  Test 1: t1 p < 0.05?
                 /                     \
               YES                      NO
                |                       |
        cold_mean >= 60.0%?      cold_mean >= 60.0%?
           /         \              /         \
         YES          NO          YES          NO
          |            |           |           |
       POSITIVE     SUGGEST.   SUGGEST.   cold_mean >= 59.51%?
       (basin        (warm      (N>=8)       /           \
       escape        mean                  YES            NO
       confirmed)    exceeded)              |              |
                                        SUGGEST.         NULL
                                        (above noise     (stagnation
                                        floor, N>=8)     domain-wide)

  Also report:
    Test 2: t2 vs GEPA — any run >= 62.3%?
    Test 3: Mean birth-gen >= 10? (extended exploration vs. fast convergence)
    Test 4: cold_SD — tight (<2pp), moderate (2–5pp), wide (>5pp)?
```

---

*Ready for Reviewer-2's scrutiny.*
