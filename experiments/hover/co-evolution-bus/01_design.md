# Experimental Design: HoVer Co-Evolution Bus -- High-Throughput Prompt Meta-Evolution

**Date**: 2026-03-22
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft -- awaiting Reviewer-2

---

## 0. Preamble: Why This Experiment Exists Despite Two NULLs

Two independent prompt co-evolution experiments have produced null results:

1. **HotpotQA** (PR #84): 3+1 topology, test EM 60.22% vs 59.58% baseline (delta +0.64pp, p=0.28). ~24 trials/gen for the prompt run. Prompt champion was a seed variant. NULL.
2. **HoVer** (PR #93): 1-to-1 topology, test 52.00% vs Cell C 54.37% (delta -2.37pp, wrong direction). ~8 trials/gen for the prompt run. P2 champion was unmodified seed. NULL/REGRESSIVE.

The Phase 5 results document for HoVer prompt co-evolution (PR #93) explicitly states: "Do NOT pursue further prompt co-evolution experiments." This recommendation was based on the convergence of two NULLs across different tasks and topologies.

**Why revisit?** The principal researcher has proposed a specific architectural hypothesis that was NOT tested in either prior experiment. The two NULLs share a diagnostic signature: **prompt fitness stagnation due to insufficient trial volume and mutation diversity in the prompt evolution run**. In PR #93, P1 had 13 trials on its champion across 25 generations; P2 never beat the seed. In PR #84, the prompt run produced 39 programs across 23 generations but achieved marginal differentiation from seeds. The proposed "co-evolution bus" architecture directly attacks this failure mode by:

- **Tripling trial throughput**: 3 main runs feeding 1 prompt run = ~24 trials/gen (matching HotpotQA 3+1, but on HoVer's responsive landscape)
- **Increasing prompt mutation diversity**: 8 prompt mutations per generation (vs 2 in PR #93's amended design, vs 5 in the original design)
- **Operating on a responsive landscape**: HoVer + soft fitness, where Cell C demonstrated +2.72pp over baseline (p~0.03)

The scientific question is sharp: **Is the prompt co-evolution failure mode attributable to insufficient meta-evolution throughput (trial volume x mutation diversity), or is prompt quality genuinely not a binding constraint?** If higher throughput still fails, the case against prompt co-evolution becomes definitive. If it succeeds, the prior NULLs are explained by an engineering deficit (underpowered meta-evolution), not a mechanistic one.

This is the last prompt co-evolution experiment I would recommend. The evidence threshold is correspondingly high: the result must exceed Cell C by >= 2.0pp to justify the investment.

---

## 1. Research Question

**Primary**: Does a high-throughput prompt co-evolution bus (3 main HoVer runs feeding 1 prompt meta-evolution run with 8 mutations/gen), combined with soft fitness, improve test retrieval coverage relative to soft fitness alone (Cell C mean 54.37%, SD=0.99pp, n=2)?

**Secondary (mechanism)**: Does the high-throughput bus produce measurably better prompt fitness differentiation than the 1-to-1 topology from PR #93? Specifically: does the prompt run's champion at gen 25 have (a) more trials, (b) higher fitness, and (c) greater fitness gap over the seed prompts than observed in PR #93?

**Tertiary (definitive closure)**: If this higher-throughput architecture also produces a null result, does the combined evidence from three independent experiments (two topologies, two tasks, two throughput levels) definitively rule out prompt co-evolution as a productive GigaEvo intervention?

---

## 2. Hypotheses

### Primary hypothesis: high-throughput bus improves test coverage beyond soft fitness alone

**H0**: Bus co-evolution runs with soft fitness produce mean test retrieval coverage (discrete, 300-sample held-out, 5 repeats per run) no higher than the Cell C reference. Formally: mu_bus <= 54.37%.

**H1**: Bus co-evolution runs produce mean test retrieval coverage >= 56.37% (Cell C mean + 2.00pp), representing a meaningful improvement beyond soft fitness alone. The 2.00pp threshold is consistent with all prior GigaEvo experiments.

**Effect size thresholds** (applied to the n=3 treatment mean):

| Bus mean test coverage | Verdict |
|------------------------|---------|
| >= 56.37% (all 3 runs) | **POSITIVE** -- high-throughput bus works; prompt co-evolution has an engineering-not-mechanism problem |
| >= 56.37% (2 of 3 runs) | **INCONCLUSIVE** -- replicate at n>=4 |
| [54.37%, 56.37%) | **NULL** -- third independent null; prompt co-evolution is definitively ruled out |
| [51.65%, 54.37%) | **REGRESSIVE** -- bus disrupts soft fitness gains (as in PR #93) |
| < 51.65% | **NEGATIVE** -- bus destroys baseline performance |

### Secondary hypothesis: prompt fitness differentiation improves with throughput

**H0_mech**: The bus prompt run's champion at gen 25 has <= 13 trials (matching PR #93's P1) and fitness gap over seed <= 0.11 (matching PR #93's P1: 0.5714 - 0.4615 = 0.11).

**H1_mech**: The bus prompt run's champion has > 30 trials AND fitness gap over best seed > 0.15. These thresholds are set at roughly 2x the PR #93 values, reflecting the ~3x throughput increase.

### Cross-experiment meta-hypothesis

If this experiment produces a NULL result:
- Three experiments, two tasks, two topologies (1-to-1 and 3-to-1), three throughput levels (8, 24, 24 trials/gen), two prompt mutation rates (2 and 8 mutations/gen)
- All null or regressive
- **Conclusion**: Prompt quality is not a binding constraint on GigaEvo performance. Period.
- **Trial dilution caveat**: If average trials-per-prompt at gen 25 is < 5 (below min_trials), the closure claim is weakened. In that scenario, the null may reflect trial dilution from the 8 mutations/gen setting rather than a genuine mechanistic failure. The combination (3+1 topology, 5 mutations/gen, responsive landscape) would remain untested. However, given the weight of three independent nulls across two tasks, further prompt co-evolution experiments would NOT be recommended even in the dilution scenario -- the expected value is too low to justify the engineering cost.
- **Cross-experiment confound acknowledgment**: This experiment changes prompt mutations/gen (8 vs 5 in PR #84, vs 2 in PR #93) simultaneously with task/landscape. The combination (3+1, 5 mut/gen, responsive HoVer landscape) is untested. This gap does not justify further experiments given three convergent nulls, but it should be disclosed in any "definitive closure" claim.

If this experiment produces a POSITIVE result:
- The mechanism works, but requires high throughput (>= 24 trials/gen) AND high prompt mutation diversity (8 mutations/gen) AND a responsive landscape (soft fitness)
- The prior NULLs are explained by engineering deficits, not mechanistic ones
- Follow-up: replicate at n>=4 with fresh PM

---

## 3. Independent Variable(s)

| Variable | Control value (Cell C reference) | Treatment value (this experiment) |
|----------|----------------------------------|-----------------------------------|
| Mutation prompt source | Fixed (FixedDirPromptFetcher, implicit default) | Co-evolved via bus (GigaEvoArchivePromptFetcher, `prompt_fetcher=coevolved`) |

This is a single-factor experiment. All other variables are held constant at their Cell C values. The "bus" is a specific implementation of co-evolution: 3 main runs connected to 1 shared prompt run.

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test retrieval coverage at gen 25 (best-by-val, discrete) | 300-sample held-out test set; discrete scoring; thinking mode Qwen3-8B; 5 repeats per run | **YES** |
| Val coverage trajectory (gen 0-25) | Per-generation `valid_frontier_fitness` from Redis (soft) | Yes -- convergence |
| Val-test gap | Best val soft fitness minus mean test discrete coverage | Yes -- overfitting |
| Prompt champion fitness at gen 25 | Beta(1,3) posterior from Redis | Yes -- mechanism check |
| Prompt champion trial count | Total trials accumulated | Yes -- throughput validation |
| Prompt archive diversity | Number of programs with >= 5 trials, fitness range | No -- health check |
| Birth-generation of best-by-val program | From Redis trajectory | No -- convergence speed |

**Primary metric**: Mean test retrieval coverage (discrete, 5-repeat average per run) across the n=3 treatment runs, compared against Cell C reference (54.37%, SD=0.99pp, n=2).

**Test protocol**: 5 independent repeats of the full 300-sample test set per run, identical to feedback_softfit and prompt_coevolution protocols.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Chain topology | 7-step fixed (3 tool, 4 LLM) | HoVer static mode |
| Test metric | Discrete retrieval coverage (all 3 gold docs = 1, else 0) | GEPA comparability |
| Evolutionary fitness | Soft (fractional: gold_found/3) | Cell C configuration |
| `problem.name` (main) | `chains/hover/static_soft` | Identical to Cell C |
| `pipeline` (main) | `standard` | Correct for static_soft |
| `prompts` | `default` | Default prompts (overridden by co-evolved when available) |
| Chain LLM | Qwen3-8B, thinking mode ON, max_tokens=32768 | GEPA comparability |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 | Identical to Cell C |
| `num_parents` | 1 | Single-parent mutation |
| `max_elites_per_generation` (main) | 8 | Identical to Cell C |
| `max_mutations_per_generation` (main) | 8 | C(8,1) = 8 |
| `max_generations` | 25 | Standard |
| `stage_timeout` | 3000 | Identical to Cell C |
| `dag_timeout` | 7200 | Identical to Cell C |
| Seed initialization | Cold start | Identical to Cell C |
| BM25 retrieval k | 7 (hops 1-2), 10 (hop 3) | Frozen |
| Validation sample size | 300 | Default |

---

## 6. Run Design Table

### Architecture: 3+1 Bus Topology

```
     B1 ------\
               \
     B2 --------+---> PM (prompt meta-evolution, DB 12)
               /      reads prompt_stats from B1+B2+B3
     B3 ------/       writes champion prompts to archive
               \
     B1,B2,B3 <--- read champion prompt from PM's archive (DB 12)
```

The "bus" is the shared prompt meta-evolution run (PM). All 3 main runs (B1, B2, B3) write `prompt_stats` to their own Redis DBs (or to a shared DB -- see Open Question 1). PM reads and aggregates prompt stats from all 3 sources. Each main run reads PM's champion prompt from PM's Redis DB (12).

**Key difference from PR #93 (1-to-1)**: Trial throughput to PM is ~24/gen (3 runs x 8 mutations/gen) instead of ~8/gen.

**Key difference from PR #84 (HotpotQA 3+1)**: (a) HoVer landscape is responsive (soft fitness +2.72pp), (b) prompt mutations = 8/gen instead of 5/gen, (c) HoVer-specific prompt seeds available (from PR #93 implementation).

### Main runs (HoVer chain evolution with soft fitness + bus co-evolved prompts)

| Run | Label | `redis.db` | `problem.name` | `pipeline` | `prompt_fetcher` | `prompt_fetcher.prompt_redis_db` | Chain LLM URL | Mutation LLM URL |
|-----|-------|------------|-----------------|-----------|-------------------|----------------------------------|---------------|------------------|
| B1 | bus-hover-1 | 9 | chains/hover/static_soft | standard | coevolved | 12 | http://10.226.17.25:8001/v1 | http://10.226.72.211:8777/v1 |
| B2 | bus-hover-2 | 10 | chains/hover/static_soft | standard | coevolved | 12 | http://10.225.185.235:8001/v1 | http://10.226.15.38:8777/v1 |
| B3 | bus-hover-3 | 11 | chains/hover/static_soft | standard | coevolved | 12 | http://10.226.17.25:8000/v1 | http://10.226.185.47:8777/v1 |

### Prompt meta-evolution run

| Run | Label | `redis.db` | `problem.name` | `pipeline` | Mutation LLM URL | Reads stats from |
|-----|-------|------------|-----------------|-----------|------------------|------------------|
| PM | bus-prompt-meta | 12 | prompt_evolution_hover | prompt_evolution | http://10.225.51.251:8777/v1 | DBs 9, 10, 11 (B1, B2, B3) |

### Prompt run configuration

| Field | Value | Rationale |
|-------|-------|-----------|
| `problem.name` | `prompt_evolution_hover` | HoVer-specific; created for PR #93 |
| `pipeline` | `prompt_evolution` | Standard for prompt meta-evolution |
| `num_parents` | 1 | Single-parent mutation |
| `max_elites_per_generation` | 8 | Larger archive than PR #93 (was 5); more prompt diversity |
| `max_mutations_per_generation` | 8 | **Key treatment parameter**: 8 new prompts/gen (vs 2 amended in PR #93) |
| `max_generations` | 25 | Same as main runs |
| `stage_timeout` | 3000 | Standard |
| `dag_timeout` | 7200 | Learned from PR #93 (sync timeout issues at lower values) |
| `prior_beta` | 3.0 | Beta(1,3) pessimistic prior |
| `min_trials` | 5 | Restored to original value (was reduced to 3 in PR #93 Amendment 3; higher throughput makes 5 feasible here) |
| Seed programs | 4 (generic.py, minimal.py, generalization.py, hover.py) | Same seeds as PR #93 |

### Multi-DB stats aggregation for PM

The current `GigaEvoArchivePromptFetcher` writes `prompt_stats` keys to the main run's Redis DB. PM must read stats from all 3 main run DBs (9, 10, 11) and aggregate trial/success counts. This requires a design decision.

**Option A (Multi-DB aggregation)**: Extend `PromptStatsProvider` to accept a list of `(db, prefix)` pairs. PM iterates over all 3 DBs and sums trial + success counts. Clean separation; requires code change and unit tests.

**Option B (Shared stats DB)**: All 3 main runs write `prompt_stats` to DB 12 (PM's DB) by setting `prompt_fetcher.main_redis_db=12`. PM reads from its own DB natively. Requires zero code change IF the `prompt_stats` writes use atomic Redis operations (HINCRBY) so concurrent writes from 3 runs do not race. If writes use GET-then-SET, this option has race conditions.

**Resolution**: Check `GigaEvoArchivePromptFetcher` implementation during Phase 3 (implementation). If atomicity holds, prefer Option B for simplicity. Otherwise, implement Option A.

### Chain LLM allocation

**Critical constraint**: 4 chain LLM endpoints exist (2 hosts x 2 ports), but only 3 are needed (PM does not evaluate chains).

| Run | Chain LLM endpoint | Host | Port |
|-----|-------------------|------|------|
| B1 | 10.226.17.25:8001 | A | 8001 |
| B2 | 10.225.185.235:8001 | B | 8001 |
| B3 | 10.226.17.25:8000 | A | 8000 |

**B1 and B3 share host A** (different ports: 8001 and 8000). B2 has host B exclusively. Each port serves an independent vLLM instance on a separate GPU, so GPU compute is not shared. The asymmetry is at the network level only (shared NIC bandwidth), which is unlikely to be a bottleneck for inference workloads.

**Confound assessment**: Since all 3 runs are treatment (no within-run treatment-vs-control comparison), host speed differences affect replication variance but do not confound the treatment-vs-reference comparison. Report per-run generation wall time. If B1 or B3 show > 30% slower generation times than B2, flag.

### Historical reference: Cell C (no within-experiment control)

| Source | Mean test (discrete) | SD | n | Config |
|--------|---------------------|-----|---|--------|
| Cell C (PR #92) | 54.37% | 0.99pp | 2 | chains/hover/static_soft, standard, fixed prompts, cold start |
| Individual: F3 | 55.07% | 1.32% (5-repeat) | | |
| Individual: F4 | 53.67% | 1.41% (5-repeat) | | |

### Mutation LLM allocation

| Process | Mutation LLM endpoint |
|---------|----------------------|
| B1 | 10.226.72.211:8777 |
| B2 | 10.226.15.38:8777 |
| B3 | 10.226.185.47:8777 |
| PM | 10.225.51.251:8777 |

Each process has a dedicated mutation LLM endpoint.

### Redis DB allocation

| DB | Run | Purpose |
|----|-----|---------|
| 9 | B1 | Main run archive + prompt stats write-back |
| 10 | B2 | Main run archive + prompt stats write-back |
| 11 | B3 | Main run archive + prompt stats write-back |
| 12 | PM | Prompt meta-evolution archive (B1/B2/B3 read champion from here) |

### Combinatorics verification

| Run | num_parents | max_elites | Parent combos | max_mutations | Actual mut/gen |
|-----|:-----------:|:---------:|:-------------:|:-------------:|:--------------:|
| B1 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| B2 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| B3 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| PM | 1 | 8 | C(8,1) = 8 | 8 | 8 |

### Trial throughput comparison across all co-evolution experiments

| Experiment | Topology | Main runs | Trials/gen for prompt | Prompt mut/gen | Prompt max_elites | Est. total trials (25 gens) |
|------------|----------|:---------:|:---------------------:|:--------------:|:-----------------:|:---------------------------:|
| HotpotQA PR #84 | 3+1 | 3 | ~24 | 5 | 5 | ~454 across 39 prompts |
| HoVer PR #93 | 1-to-1 | 1 per P | ~8 | 2 (amended) | 5 | ~175 per pair |
| **This experiment** | **3+1 bus** | **3** | **~24** | **8** | **8** | **~600 estimated** |

---

## 7. Sample Size Justification

**n=3 treatment runs + 1 prompt meta-evolution run (4 processes total). No within-experiment control.**

### Why n=3

1. **Infrastructure fit**: 4 mutation LLM endpoints, 4 chain LLM endpoints (3 needed for main, PM needs none). The natural allocation is 3 main + 1 prompt.

2. **Power improvement over PR #93 (n=2)**: With n_treatment=3 vs n_reference=2, the MDE for Welch's t-test at alpha=0.05 (one-sided) and 80% power is:

    Assuming SD=0.99pp (from Cell C), with t_alpha = t(0.95, df~3) = 2.353 and t_beta = t(0.80, df~3) = 0.978:
    MDE = (t_alpha + t_beta) * SD * sqrt(1/n1 + 1/n2)
        = (2.353 + 0.978) * 0.99 * sqrt(1/3 + 1/2)
        = 3.331 * 0.99 * 0.913
        = 3.01pp

    The 2.0pp POSITIVE threshold is NOT achievable at 80% power with n1=3, n2=2 even under optimistic SD assumptions. The experiment is **exploratory-powered** for the stated criterion. The effect-size threshold table (Section 2) is the primary decision instrument, not p < 0.05.

    **MDE sensitivity table** (80% power, one-sided alpha=0.05, n1=3, n2=2):

    | Assumed SD | MDE |
    |-----------|-----|
    | 0.99pp (Cell C estimate) | 3.01pp |
    | 1.50pp | 4.56pp |
    | 2.00pp | 6.08pp |
    | 2.50pp | 7.60pp |

    **Pre-commitment**: When treatment SD exceeds 2.0pp, interpretation relies exclusively on the effect-size threshold table. P-values from the Welch t-test are reported but treated as descriptive only.

3. **SD uncertainty caveat**: Cell C SD (0.99pp) is from n=2. The 95% CI for the population SD extends from ~0.50pp to infinity (chi-squared, df=1). The 0.99pp estimate is essentially a single-degree-of-freedom estimate and should be treated as a lower bound on the true MDE. Results should be interpreted with this uncertainty.

### Independence caveat

The 3 treatment runs share PM's evolved prompts. They are NOT independent replications (see Confound #3 and #10 in Section 9). The effective sample size is between n=1 (fully correlated) and n=3. The formal t-test assumes independence; the effect-size threshold table does not.

### Follow-up design (pre-committed)

| Result | Action |
|--------|--------|
| All 3 runs >= 56.37% | POSITIVE -- replicate at n>=4 with fresh PM |
| 2 of 3 >= 56.37% | INCONCLUSIVE -- replicate at n=4 |
| All 3 in [54.37%, 56.37%) | NULL -- definitively close prompt co-evolution |
| Any run < 51.65% | REGRESSIVE/NEGATIVE -- close prompt co-evolution, investigate disruption |

---

## 8. Statistical Test

### Test 1: Treatment vs. Cell C reference (primary)

**Comparison**: Mean test retrieval coverage of bus treatment (n=3) vs Cell C reference (n=2, mean=54.37%, SD=0.99pp).

**Test**: Welch's two-sample t-test, one-sided (H1: treatment_mean > reference_mean).

**Statistic**: t = (treatment_mean - 54.37) / sqrt(s_treatment^2/3 + 0.99^2/2)

**Degrees of freedom**: Satterthwaite approximation (~3 with n1=3, n2=2).

**Significance threshold**: alpha = 0.05 (one-sided). The primary decision criterion is the effect-size threshold table (Section 2), not p < 0.05.

**Conservative analysis**: Because treatment runs are not independent (Confound #3), also report the result treating the treatment mean as a single observation (n=1) compared against Cell C (n=2). This eliminates the independence assumption but provides zero power -- it serves as a lower bound on confidence.

**Correlation-adjusted interpretation rule**: If inter-run SD < 0.5pp, the conservative n=1 analysis is primary (runs are highly correlated through PM). If inter-run SD >= 1.0pp (comparable to Cell C SD), the n=3 analysis is primary (runs show meaningful independent variation). For intermediate values (0.5-1.0pp), report both and interpret conservatively.

### Test 2: Treatment vs. baseline (secondary)

**Comparison**: Treatment mean (n=3) vs baseline mean (Cell A, n=4, mean=51.65%, SD=0.63pp).

**Purpose**: Verify bus + soft fitness remains above baseline.

### Test 3: Treatment vs. PR #93 treatment (exploratory)

**Comparison**: Bus mean (n=3) vs PR #93 mean (52.00%, n=2).

**Purpose**: Determine whether bus architecture improves on 1-to-1 co-evolution.

### Test 4: Per-run test evaluation (5-repeat protocol)

Report per-repeat scores and within-run SD for all 3 runs. Compare within-run SD across treatment and Cell C reference.

### Mechanism check: prompt fitness analysis

Report at gen 25:
- PM archive size, total programs, total trials, trials per prompt
- **Average trials per prompt** (pre-committed diagnostic: if < 5, trial dilution failure mode is triggered; see Section 2 cross-experiment meta-hypothesis)
- Champion fitness (Beta(1,3) posterior) vs best seed fitness
- Fitness gap: champion - best_seed
- Compare against PR #93 benchmarks: P1 (52 programs, 13 champion trials, fitness 0.5714, gap 0.11) and P2 (50 programs, 11 trials, champion = unmodified seed)
- Compare against PR #84 benchmark: 39 prompts, 454 trials, 11.6 trials/prompt average

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Cold-start prompt fitness lag** | Main runs fall back to fixed prompts for first 2-3 gens until PM has a champion. | With 3 main runs x 8 mut/gen = 24 trials/gen, PM reaches min_trials=5 within 1-2 gens. Log fallback-to-coevolved transition generation for all 3 runs. If transition > gen 5, flag. |
| 2 | **Host A contention (B1 + B3)** | Two main runs share host A's NIC. | Separate vLLM instances on separate GPUs. NIC bottleneck unlikely for inference. Monitor gen wall time. |
| 3 | **Non-independent treatment runs (CRITICAL)** | All 3 main runs share PM's champion prompt. If PM evolves badly, all 3 suffer simultaneously. Correlated failure. | **Acknowledged as fundamental limitation.** Cannot be mitigated without reverting to 1-to-1 (which failed due to insufficient throughput). Report inter-run SD; if < 0.5pp, note that apparent precision is an artifact of correlation. |
| 4 | **Infrastructure drift from Cell C** | Cell C completed 2026-03-20; launch may be delayed. | Pre-launch health check. 72h time-gate: if launch > 2026-03-23, add concurrent within-experiment control (sacrifice B3 -> control). |
| 5 | **Multi-DB stats aggregation correctness** | PM must correctly aggregate stats from 3 DBs. Bugs = distorted prompt fitness. | Code prereq: unit test for aggregation (Option A) or atomicity verification (Option B). 3-gen smoke test verifies PM sees stats from all 3 DBs. |
| 6 | **PM archive bloat** | 8 prompts/gen x 25 gens = 200 candidate prompts. With 24 trials/gen, average 3 trials/prompt. Many may not reach min_trials=5. | max_elites=8 prunes aggressively. After gen 5, archive should stabilize. Monitor archive size at gen 5, 15, 25. |
| 7 | **Temporal autocorrelation of prompt fitness** | Early-phase prompts accumulate inflated success rates. | Acknowledge. Report per-generation success rates. Mechanism check is descriptive. |
| 8 | **Soft fitness + co-evolution overfitting** | Prompts targeting soft improvements (1/3 -> 2/3) may not improve discrete test coverage. | Val-test gap tracked. Report both soft val and discrete test. |
| 9 | **PM prompt_prefix mismatch** | `prompt_fetcher.prompt_prefix` must be `prompt_evolution_hover`. | Pre-launch `--cfg job` check. |
| 10 | **Within-treatment correlation inflates apparent precision** | If all 3 runs are highly correlated, SD from n=3 understates uncertainty. Welch t-test produces unreliable p-values. | Report inter-run SD. If < 0.5pp, also report conservative n=1 analysis (treatment mean as single observation). Effect-size table is primary. |
| 11 | **Port parity between Cell C (8000) and bus runs (8000 + 8001)** | Cell C used ports 8000; B1/B2 use port 8001. If 8001 instances differ in config, chain outputs may differ. | Pre-launch port parity check: verify identical model IDs and max_model_len on both ports of host A. Run 10-sample eval on both ports; if scores differ > 5pp, switch all to port 8000. |
| 12 | **Prompt mutation rate (8/gen) as implicit second IV in cross-experiment comparisons** | This experiment uses 8 prompt mutations/gen vs 5 in PR #84 and 2 in PR #93. In cross-experiment interpretation, mutation rate co-varies with task/landscape. The combination (3+1, 5 mut/gen, responsive HoVer landscape) remains untested. | Acknowledged as a gap. If the result is NULL AND average trials/prompt < 5 (trial dilution triggered), the closure claim must be scoped: "prompt co-evolution at 8 mut/gen on responsive landscape" rather than "prompt co-evolution in general." However, given three convergent nulls, further experiments to fill this gap are not recommended. |
| 13 | **Temporal coupling: PM champion changes mid-generation** | If PM evolves a new champion while a main run is mid-generation, different mutations within the same generation may use different prompts. Cell C's fixed prompts provide a stable mutation signal; the bus treatment is time-varying. | This is by design (per-mutation prompt sampling). Acknowledge that temporal instability adds noise that could mask a genuine signal. Report whether PM champion changed during main run generations (from champion transition timestamps). |

### Independence assumption: explicit warning

**The 3+1 bus topology sacrifices run independence for prompt trial throughput.** In the 1-to-1 topology (PR #93), runs C1+P1 and C2+P2 were fully independent replications. In the bus, B1/B2/B3 are coupled through PM. An unlucky PM evolution degrades all 3 runs; a lucky one benefits all 3. The n=3 treatment sample does NOT provide 3 independent observations.

**Statistical consequence**: The formal t-test assumes independence. The effect-size threshold table (Section 2) remains valid regardless. Both are reported; interpretation should weight the threshold table over the p-value.

---

## 10. Stop Criteria

### Time-gate for historical control validity

Cell C data collected 2026-03-20. If launch > 72h after Cell C completion (after 2026-03-23 ~15:00 UTC), reconfigure: B3 becomes a concurrent control (soft fitness, fixed prompts, no co-evolution) + PM feeds only B1+B2. Trial throughput drops to ~16/gen.

### Early termination criteria (per run)

- **Gen-0 val fitness < 0.01 (soft)**: Halt; BM25 first hop failure.
- **Gen-0 val fitness > 0.20 (soft)**: Halt; initialization error.
- **Gen-0 val fitness = sentinel (-1000.0)**: Halt; execution error.
- **Main run val coverage < 45% at gen 10 (soft)**: Halt; infrastructure failure.
- **PM archive empty at gen 5 of main runs**: Halt all; feedback loop broken.

### Stagnation-based early completion

If `valid_frontier_fitness` shows no improvement for >= 10 consecutive gens AND current gen >= 15, a main run may be terminated early. Not an invalidation.

### Run invalidation criteria

1. Thinking mode not active: `<think>` blocks absent from >= 5% of chain outputs at gen 1.
2. Invalidity rate > 90% at gen 10.
3. Gen-0 val coverage > 20% (soft).
4. `max_elites_per_generation` != 8 in post-hoc (main runs).
5. `num_parents` != 1 in post-hoc.
6. `pipeline` mismatch: main not `standard`, PM not `prompt_evolution`.
7. `problem.name` mismatch: main not `chains/hover/static_soft`.
8. Test evaluation uses soft metric instead of discrete.
9. PM never produced a champion fetched by any main run (prompt_stats keys: count > 0, at least one prompt_id with trials >= 5).
10. Redis corruption or data loss.
11. PM did not receive stats from all 3 main run DBs (verified at gen 3 smoke test).

### Completion criteria

- All 3 main runs reach gen 25 OR are terminated/invalidated.
- PM reaches gen 25 OR the last main run completes first.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time per main run (300-sample, 25 gens) | ~8-12h |
| Total wall time (4 processes parallel) | ~12h wall-clock |
| Chain LLM endpoints | 3 (B1, B2, B3) |
| Mutation LLM endpoints | 4 (B1, B2, B3, PM) |
| Redis DBs | 4 (DBs 9, 10, 11, 12) |
| Test eval time | ~5 min/repeat x 5 repeats x 3 runs = ~75 min |
| New code required | Multi-DB stats aggregation or shared-stats-DB verification; unit tests |

---

## 12. Open Questions / Risks

### Open Question 1: Multi-DB stats aggregation vs. shared stats DB

PM needs trial data from all 3 main runs. Two paths:

**Option A (Multi-DB aggregation)**: Modify `PromptStatsProvider` to accept `main_redis_dbs: [9, 10, 11]`. PM iterates and sums. Requires code change + unit tests.

**Option B (Shared stats DB)**: All 3 main runs set `prompt_fetcher.main_redis_db=12`, writing prompt_stats to PM's DB. Zero code change IF writes use atomic Redis ops (HINCRBY). Race-condition risk if writes use GET-then-SET.

**Resolution**: Inspect `GigaEvoArchivePromptFetcher` source during implementation. Prefer Option B if atomicity confirmed.

### Open Question 2: Is 3+1 with 8 mutations/gen qualitatively different from prior attempts?

The HotpotQA 3+1 had ~24 trials/gen and 5 prompt mutations/gen, producing 39 prompts across 23 gens. This experiment has ~24 trials/gen and 8 prompt mutations/gen, expected to produce ~200 prompts across 25 gens. The difference is 5x more prompt candidates competing for similar trial volume. This COULD improve selection pressure (more diverse candidates) or COULD dilute trials per prompt (fewer trials per candidate).

**Expected trial budget**: ~600 trials across ~100-200 prompts = 3-6 trials/prompt on average. With min_trials=5, many prompts will not have fitness computed. The max_elites=8 cap ensures that only the 8 best survive each generation, concentrating trials on promising candidates.

**Risk level**: MEDIUM-HIGH. This is an incremental parameter change, not a qualitative architectural difference. The most likely outcome remains NULL.

### Open Question 3: What if the result is NULL?

Three NULLs across the following grid would be definitive:

| Dim | PR #84 | PR #93 | This |
|-----|--------|--------|------|
| Task | HotpotQA | HoVer | HoVer |
| Landscape | Flat | Responsive | Responsive |
| Topology | 3+1 | 1-to-1 | 3+1 |
| Trials/gen | ~24 | ~8 | ~24 |
| Prompt mut/gen | 5 | 2 | 8 |
| Result | NULL | NULL/REG | ? |

Conclusion: **Mutation prompt quality is not a binding constraint.** The remaining candidates for the binding constraint on HoVer: chain topology (frozen 7-step), retrieval engine (BM25), chain LLM ceiling (Qwen3-8B).

### Open Question 4: What if the result is POSITIVE?

The prior NULLs explained by: HotpotQA = flat landscape; HoVer 1-to-1 = insufficient throughput. The bus succeeds because it combines responsive landscape + high throughput + high mutation diversity. Follow-up: replicate at n>=4 with fresh PM, and test whether the effect persists with 1-to-1 at 8 mutations/gen (isolating mutation rate from topology).

---

## Appendix A: Code Prerequisites Before Launch

1. **Stats aggregation resolution**: Check atomicity of prompt_stats writes in `GigaEvoArchivePromptFetcher`. If atomic (HINCRBY), configure Option B (shared stats DB). If non-atomic, implement and test Option A (multi-DB aggregation).

2. **Verify `prompt_evolution_hover` exists**: Confirm problem variant with HoVer task_description.txt and seed programs (created for PR #93).

3. **`--cfg job` verification for all 4 runs**:
   - B1/B2/B3: `prompt_fetcher.prompt_redis_db=12`, `prompt_fetcher.prompt_prefix=prompt_evolution_hover`, `prompt_fetcher.main_redis_prefix=chains/hover/static_soft`
   - PM: `problem.name=prompt_evolution_hover`, `pipeline=prompt_evolution`, max_elites=8, max_mutations=8

4. **Redis DBs 9-12**: 0 keys after archiving.

5. **Chain LLM port parity**: Verify identical model on ports 8000 and 8001 of host A.

6. **test.py discrete scoring**: SHA-256 of static_soft/test.py matches static/test.py.

7. **3-gen smoke test (mandatory)**: Launch all 4 processes for 3 gens. Verify:
   - (i) prompt_stats keys exist in expected location
   - (ii) PM archive has >= 1 program
   - (iii) At least 1 main run fetched champion from PM (not fallback)
   - (iv) PM aggregated stats from all 3 DBs (total trials > 20 at gen 3)

---

## Appendix B: Decision Tree

```
After gen-25 evaluations for B1, B2, B3:

  Cell C reference mean: 54.37% (SD=0.99pp, n=2)
  Baseline mean (Cell A): 51.65% (SD=0.63pp, n=4)
  PR #93 treatment mean: 52.00% (n=2)

  Bus treatment mean: bus_mean
  Delta vs Cell C: delta_c = bus_mean - 54.37%

                       delta_c >= +2.0pp?
                      /                \
                    YES                 NO
                     |                   |
              All 3 runs >= 56.37%?   delta_c >= 0?
              /                \      /          \
            YES                NO   YES           NO
             |                  |    |             |
         POSITIVE          INCONCLUSIVE  NULL    bus_mean >= 51.65%?
         replicate n=4     replicate n=4   |     /          \
                                           |   YES           NO
                                           |    |             |
                              3rd NULL:   REGRESSIVE     NEGATIVE
                              CLOSE       bus hurts      bus destroys
                              prompt      soft gains
                              co-evo
                              research
                              line
```

---

## Appendix C: Comparison with Prior Co-Evolution Designs

| Dimension | HotpotQA PR #84 | HoVer 1-to-1 PR #93 | **HoVer Bus (this)** |
|-----------|-----------------|----------------------|----------------------|
| Task | HotpotQA | HoVer | **HoVer** |
| Landscape | Flat (59-60%) | Responsive (+2.72pp) | **Responsive** |
| Topology | 3+1 shared | 1-to-1 independent | **3+1 bus** |
| Main runs (n) | 3 | 2 | **3** |
| Trials/gen for prompt | ~24 | ~8 | **~24** |
| Prompt mutations/gen | 5 | 2 (amended) | **8** |
| Prompt max_elites | 5 | 5 | **8** |
| min_trials | 5 | 3 (amended) | **5** |
| Reference | Cold-start 59.58% | Cell C 54.37% | **Cell C 54.37%** |
| Run independence | No | Yes | **No** |
| MDE (80% power) | N/A | 4.26pp | **2.13pp** |
| Result | NULL | NULL/REGRESSIVE | **?** |

---

## Appendix D: Treatment Verification Checklist

Observable evidence that the treatment is active (check at gen 5 and gen 25):

| Check | Method | Expected value | Failure mode |
|-------|--------|----------------|-------------|
| PM archive populated | `HLEN prompt_evolution_hover:archive:programs` in DB 12 | > 10 programs by gen 5 | PM crashed or misconfigured |
| Main runs using PM prompts | prompt_stats keys with PM-originated prompt_ids, trial count > 0 | >= 3 distinct prompt_ids with trials >= 5 by gen 10 | Prompt fetcher stuck in fallback |
| PM fitness differentiation | PM champion fitness (Beta posterior) > 0.50 | Gap over best seed > 0.05 | Stagnation (PR #93 failure mode) |
| Aggregated trial volume | Total trials across all prompt_stats keys | > 200 by gen 15 (~24/gen x 15 = 360 expected) | Stats pipeline broken |
| All 3 DBs contributing | Distinct prompt_stats sources from DBs 9, 10, 11 | All 3 present | Aggregation bug |

If any check fails at gen 10, pause and diagnose before continuing.

---

*Ready for Reviewer-2's scrutiny.*
