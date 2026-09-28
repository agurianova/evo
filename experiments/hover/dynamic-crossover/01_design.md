# Experimental Design: HoVer Dynamic Crossover -- Multi-Parent Crossover vs. Single-Parent Mutation in the Dynamic Topology Setting

**Date**: 2026-03-25
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Revised -- Reviewer-2 concerns addressed (IV NOT REALIZED outcome, ramp-up period, D5 reference)

---

## 1. Research Question

The previous experiment `hover/dynamic-topology` (PR #116) established that allowing evolution to modify chain topology (step count, step types, dependencies) yields substantially higher retrieval coverage than fixed-topology evolution. The best evolved chain (D5) achieved 60.78% discrete test coverage, +8.45pp over GEPA (52.33%) and +6.65pp over the static-topology control mean (54.13%). These chains grew from 7 to 9-10 steps with 5 retrieval hops, discovering that retrieval breadth matters more than reasoning depth for 3-hop fact verification.

All prior HoVer experiments, including dynamic-topology, used single-parent mutation (`num_parents=1`). In this mode, each generation selects one elite program at a time, and the mutation LLM modifies it independently. The GigaEvo framework supports multi-parent crossover (`num_parents=2`), where the `AllCombinationsParentSelector` generates all C(n,2) pairs from the elite archive and the mutation LLM receives both parent programs simultaneously, enabling it to combine structural elements from both into a child program.

The dynamic topology setting is a particularly interesting context for crossover because evolved chains differ structurally -- different step counts, different tool/LLM compositions, different dependency patterns. With `num_parents=1`, a chain with an effective 5-hop retrieval pattern and a chain with an effective query-generation strategy can never be combined; each must independently rediscover the other's innovation. With `num_parents=2`, the mutation LLM sees both programs and can synthesize a child that inherits the retrieval pattern from one parent and the query strategy from the other.

**Primary research question**: Does multi-parent crossover (`num_parents=2`) improve test retrieval coverage compared to single-parent mutation (`num_parents=1`) in the dynamic topology setting (`chains/hover/full`)?

**Secondary research question**: Does crossover produce qualitatively different chain architectures (step counts, tool/LLM ratios) compared to single-parent mutation, and does crossover accelerate convergence to high-fitness regions of the topology search space?

---

## 2. Hypotheses

### Primary hypothesis: crossover improves test retrieval coverage

**H0**: Mean discrete test retrieval coverage of the crossover condition (`num_parents=2`) does not exceed mean discrete test retrieval coverage of the single-parent condition (`num_parents=1`) in the dynamic topology setting. Formally: mu_crossover - mu_single <= 0pp.

**H1**: Mean discrete test retrieval coverage of the crossover condition exceeds the single-parent condition. The ability to combine structural innovations across parent chains (different step counts, retrieval patterns, query strategies) enables evolutionary search to discover higher-fitness programs than independent mutation alone.

### Secondary hypothesis: crossover accelerates convergence

**H2**: The crossover condition reaches a given validation fitness threshold (e.g., 80% soft val fitness) in fewer generations than the single-parent condition. The mechanism is that crossover combines partial solutions from different parents rather than requiring each lineage to independently discover all necessary components.

### Effect-size thresholds

Reference points from `hover/dynamic-topology`:
- Dynamic topology single-parent control mean: 54.13% test (n=2, static_soft)
- Dynamic topology single-parent treatment (D5): 60.15% test (n=1, `chains/hover/full`)
- D6 (degraded): 54.41% test (worker leak, partially valid)
- GEPA benchmark: 52.33%

Since both conditions in this experiment use `chains/hover/full` (dynamic topology), the relevant baseline is the dynamic-topology treatment performance. D5 achieved 60.15% (the only clean dynamic-topology run). As a conservative reference, we use the D5 result but acknowledge the extremely small sample (n=1).

| Crossover test mean | Delta vs. control mean | Verdict |
|---------------------|----------------------|---------|
| >= control + 4.0pp | >= +4.0pp | **STRONG POSITIVE** |
| [control + 2.0pp, control + 4.0pp) | [+2.0pp, +4.0pp) | **POSITIVE** |
| (control, control + 2.0pp) | (0pp, +2.0pp) | **SUGGESTIVE** |
| <= control mean | <= 0pp | **NULL** |
| Any delta, but crossover diagnostic shows >80% one-parent dominance | N/A | **IV NOT REALIZED** — the mutation LLM did not perform true crossover; result is uninformative about the crossover hypothesis regardless of delta |

**Note**: With n=1 control and n=2 treatment, these thresholds serve as descriptive benchmarks, not hypothesis-test decision boundaries. The experiment is exploratory.

---

## 3. Independent Variable(s)

| Variable | Control value | Treatment value |
|----------|---------------|-----------------|
| **`num_parents`** | 1 (single-parent mutation) | 2 (multi-parent crossover) |

### Mechanistic difference

| Dimension | `num_parents=1` (control) | `num_parents=2` (treatment) |
|-----------|--------------------------|----------------------------|
| Parent selector | `AllCombinationsParentSelector` yields C(8,1)=8 single-parent selections | `AllCombinationsParentSelector` yields C(8,2)=28 parent pairs, capped at `max_mutations_per_generation=8` |
| Mutation LLM input | One parent program (code + mutation context) | Two parent programs (both code + mutation context), formatted as `=== Parent 1 ===` and `=== Parent 2 ===` blocks |
| Mutation task | Modify a single program | Combine/synthesize elements from two programs into one child |
| Effective mutations/gen | 8 (all unique parents, deterministic) | 8 (sampled from 28 possible pairs, shuffled) |
| Parent diversity per mutation | None -- each mutation sees one program | High -- each mutation sees two structurally different programs |

### What is identical between conditions

Both conditions use `chains/hover/full` (dynamic topology). The only difference is whether the mutation LLM sees one parent or two per mutation call. The mutation prompt template, system prompt, insights, failure analysis, and all other pipeline components are identical.

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test retrieval coverage at gen 25 (discrete, best-by-val) | 300-sample held-out test set; discrete scoring (all 3 gold docs = 1, else 0); thinking mode Qwen3-8B; 5 repeats per run | **YES -- primary** |
| Val fitness trajectory (gen 0-25, soft) | Per-generation `valid_frontier_fitness` from Redis | YES -- convergence diagnostic |
| Val-test gap (soft val vs. discrete test) | Best val fitness minus mean discrete test coverage | YES -- overfitting diagnostic |
| n_steps of best-by-val program | From program source code | YES -- topology evolution diagnostic |
| n_tool_steps of best-by-val program | From program source code | YES -- retrieval strategy diagnostic |
| Archive topology diversity at gen 25 | Distribution of step counts across elite archive | YES -- structural diversity diagnostic |
| Generation at which val fitness first exceeds 80% (soft) | From Redis trajectory | YES -- H2 convergence speed diagnostic |
| Within-run test variance (5-repeat SD) | SD of 5 test evaluations per run | NO -- LLM stochasticity diagnostic |

**Primary metric**: Mean discrete test retrieval coverage (5-repeat average per run) at gen 25 for each condition.

**Test protocol**: 5 independent repeats of the full 300-sample test evaluation per run, identical to all prior experiments. The 5-repeat mean is the per-run estimate.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| **`problem.name`** | `chains/hover/full` | Dynamic topology for ALL runs; this is not the IV |
| **Test metric** | **Discrete retrieval coverage** (all 3 gold docs = 1, else 0) | Comparable to all prior experiments and GEPA |
| **Evolutionary fitness** | **Soft (fractional)** -- gold_found / n_gold per sample | Both conditions use soft fitness; confirmed positive from PR #92 |
| `pipeline` | `standard` | Both variants return dict from validate.py |
| `prompts` | `default` | No domain-specific prompts |
| Validation sample size | 300 (first 300 train samples) | Default; identical to all prior experiments |
| Chain LLM | Qwen/Qwen3-8B, thinking mode ON, context 32768 | Required for GEPA comparison |
| Chain LLM endpoints | Load balanced via `HOVER_CHAIN_URL` (4 endpoints, random selection per worker) | All runs share the same pool; no per-run host confound |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 | Identical to all prior experiments |
| Mutation LLM endpoints | Load balanced via `llm=balanced` (3 endpoints, Redis-coordinated routing on DB 15) | All runs share the same pool; no per-run host confound |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` (explicit override) | Default is OpenRouter -- MUST override |
| `max_elites_per_generation` | 8 (explicit override; default is 5) | Identical to dynamic-topology experiment |
| `max_mutations_per_generation` | 8 | With num_parents=1: C(8,1)=8; with num_parents=2: C(8,2)=28, capped at 8 |
| `stage_timeout` | 5000 (explicit override) | Learned from dynamic-topology Amendment A1; complex chains need longer timeouts |
| `dag_timeout` | 7200 (explicit override) | Identical to dynamic-topology |
| `max_generations` | 25 | Identical to dynamic-topology |
| `mutation_mode` | `rewrite` | Default |
| Seed initialization | Cold start (no `program_loader.problem_dir`) | Identical to dynamic-topology |
| HTTP timeout | 600s | Consistent with all prior experiments |
| BM25 corpus | wiki17_abstracts.jsonl.passages.pkl (~5.2M passages) | Shared corpus across tasks |

---

## 6. Run Design Table

| Run | Label | Cell | `num_parents` | `redis.db` | `problem.name` |
|-----|-------|------|:-------------:|:----------:|-----------------|
| X1 | hover-full-single | Control | 1 | 3 | `chains/hover/full` |
| X2 | hover-full-cross-1 | Treatment | 2 | 4 | `chains/hover/full` |
| X3 | hover-full-cross-2 | Treatment | 2 | 5 | `chains/hover/full` |

**Run naming convention**: X-prefix for "crossover" experiment.

**Execution plan**: All 3 runs launch simultaneously. With `llm=balanced`, all runs share the 3 mutation server endpoints via Redis-coordinated least-loaded routing (DB 15). Chain LLM endpoints are shared via comma-separated `HOVER_CHAIN_URL` with random per-worker selection. No per-run host assignment needed.

### Infrastructure: load-balanced, shared pool

Unlike prior experiments that assigned one mutation server per run, this experiment uses the `llm=balanced` config. All 3 runs draw from the same pool of 3 mutation servers (10.226.15.38:8777, 10.226.185.47:8777, 10.225.51.251:8777). The load balancer on Redis DB 15 routes each request to the least-loaded endpoint with a 60-second cooldown. This eliminates the per-run host confound entirely.

Chain LLM endpoints (4 total: 10.226.17.25:8001, 10.226.17.25:8000, 10.225.185.235:8001, 10.225.185.235:8000) are similarly shared via `HOVER_CHAIN_URL` with per-worker random selection.

### Combinatorics verification

| Run | num_parents | max_elites | Parent combos | max_mutations | Actual mut/gen |
|-----|:-----------:|:---------:|:-------------:|:-------------:|:--------------:|
| X1 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| X2 | 2 | 8 | C(8,2) = 28 | 8 | 8 (capped) |
| X3 | 2 | 8 | C(8,2) = 28 | 8 | 8 (capped) |

All runs produce the same number of mutations per generation (8). The difference is whether each mutation sees one parent or two. With `num_parents=2`, the 28 possible pairs are shuffled and the first 8 are used. Different generations see different subsets.

### Redis DB assignments

DBs 3, 4, 5 (verified free). DB 15 is used by the mutation load balancer.

---

## 7. Sample Size Justification

### Design: n=1 control, n=2 treatment, 3 runs total

This is an exploratory experiment constrained by mutation server availability (3 servers). The design prioritizes treatment replication (n=2) over control replication because:

1. We already have a historical reference for single-parent dynamic topology from D5 (60.15% test, n=1). The control run X1 provides a contemporaneous replication of this result with the exact same infrastructure (load-balanced LLM, worker leak fix applied).
2. Crossover is the novel intervention with unknown variance. Two treatment runs provide a minimal estimate of within-treatment variability.
3. With only 3 servers available, the alternative (n=2 control, n=1 treatment) would give us even less information about the treatment.

### Power analysis

**This experiment has no statistical power for formal hypothesis testing.** With n=1 control and n=2 treatment, there are no degrees of freedom for a within-control variance estimate, making t-tests impossible. The experiment is purely descriptive and exploratory.

**What we can determine**:
- Whether both treatment runs exceed the control run (directional consistency)
- Whether treatment runs exceed the D5 historical reference (60.15%)
- Whether crossover produces qualitatively different chain architectures
- The magnitude and direction of the effect for planning a powered follow-up

**Follow-up required**: If the result is SUGGESTIVE or POSITIVE, a powered replication with n>=3 per cell (6 runs total) is needed before any scientific claim can be made. If NULL, the result is informative for closing the crossover research line.

---

## 8. Statistical Approach

Given the impossibility of formal inference with n=1 control, the analysis is entirely descriptive.

### Analysis 1: Treatment vs. control (PRIMARY)

**Comparison**: Discrete test coverage of treatment runs (X2, X3) vs. control run (X1).

**Method**: Report X1 test mean (5 repeats), X2 test mean (5 repeats), X3 test mean (5 repeats), treatment cell mean (average of X2 and X3 per-run means), and delta (treatment mean - control mean). Apply effect-size thresholds from Section 2.

**Interpretation constraint**: Any observed delta could be due to inter-run variance rather than a treatment effect. The inter-run SD from dynamic-topology was not estimable (n=1 clean treatment run), but from static-topology experiments it ranged from 0.63pp to 1.41pp. A delta < 2pp is indistinguishable from noise at these sample sizes.

### Analysis 2: Treatment vs. D5 historical reference (SECONDARY)

**Comparison**: Treatment mean vs. D5 test coverage (60.15%).

**Purpose**: Determines whether crossover improves upon the best known dynamic-topology result. If treatment mean exceeds 60.15%, crossover may unlock performance beyond what single-parent mutation achieved.

### Analysis 3: Control replication of D5 (SECONDARY)

**Comparison**: X1 test coverage vs. D5 (60.15%).

**Purpose**: Verifies that the dynamic-topology result replicates with the current infrastructure (load-balanced LLM, worker leak fix). If X1 substantially differs from D5, infrastructure changes may confound the treatment comparison.

### Analysis 4: Convergence speed (H2, EXPLORATORY)

**Metric**: Generation at which val fitness first exceeds 80% (soft), for each run.

**Method**: Descriptive comparison of convergence generation across runs.

### Analysis 5: Architecture comparison (EXPLORATORY)

**Metric**: n_steps and n_tool_steps of best-by-val program, and archive diversity at gen 25.

**Method**: Compare topology distributions between control and treatment. Do crossover-evolved chains have different structure than single-parent-evolved chains?

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **n=1 control prevents variance estimation** | Any observed delta could be inter-run noise. We cannot compute a p-value. | ACKNOWLEDGED. This is the fundamental limitation. The experiment is exploratory. Pre-commit to a powered follow-up if the result is directionally positive. Historical inter-run SD (0.63-1.41pp) provides a rough calibration for interpreting observed deltas. |
| 2 | **Mutation LLM may ignore the second parent** | When given two parent programs, the mutation LLM might focus on one parent and ignore the other, producing mutations indistinguishable from single-parent mode. This would make the treatment functionally identical to the control. | DIAGNOSABLE. Post-hoc analysis of mutation logs: for treatment runs, compare the child program's structural similarity to each parent (step count, tool positions, prompt text overlap). If >80% of children are structurally identical to one parent, the LLM is not performing true crossover. |
| 3 | **Load balancer introduces shared-resource contention** | All 3 runs share 3 mutation servers. If one run monopolizes a fast server, others may be disadvantaged. This does not differentially affect treatment vs. control, but adds inter-run variance. | LOW RISK. The load balancer uses least-loaded routing with 60-second cooldown, distributing requests evenly. All runs have equal priority. Monitor per-run mutation throughput (mutations/hour) to confirm parity. |
| 4 | **Different parent pair sampling across treatment runs** | With C(8,2)=28 possible pairs and only 8 used per generation, X2 and X3 see different subsets of parent pairs (shuffled independently). This adds within-treatment variance. | ACCEPTED. This is inherent to the `AllCombinationsParentSelector` design and reflects the stochasticity of the evolutionary search. Two treatment runs provide a minimal estimate of this variance. |
| 5 | **Early-generation ramp-up period** | At gen 0, there is only 1 program (the seed). With `num_parents=1`, the seed is mutated 8 times. With `num_parents=2`, only 1 parent is available, so `AllCombinationsParentSelector` yields the seed as a single-element list -- effectively falling back to single-parent mode. Even at gen 1, if only 2-3 elites exist, C(n,2) produces fewer than 8 pairs. The treatment reaches full parent-pair diversity only when the archive has 4+ programs (C(4,2)=6, approaching the cap of 8). | LOW RISK. The treatment ramp-up spans approximately gens 0-3 (until the archive reaches 4+ programs). This is a 3-4 generation transient out of 25. Monitor per-generation parent pair counts in mutation logs to confirm when full crossover diversity kicks in. |
| 6 | **D5 used dedicated mutation server; X1 uses load balancer** | The control replication of D5 uses a different mutation LLM routing strategy (shared pool vs. dedicated server). Throughput differences could affect convergence. | ACKNOWLEDGED. If X1's mutation throughput (mutations/hour) differs substantially from D5's, note this as a potential confound in the replication comparison. The within-experiment comparison (X1 vs. X2/X3) is not affected because all runs use the same load balancer. |
| 7 | **stage_timeout differs from D5** | D5 launched with `stage_timeout=3000` (amended to 5000 mid-run via A1). X1-X3 launch with `stage_timeout=5000` from the start. Programs that would have timed out in D5's early generations survive in X1-X3. | LOW RISK. The 5000s timeout is more permissive, which could help all runs equally. This favors replication success (X1 should match or exceed D5) and does not differentially affect the treatment comparison. |
| 8 | **Worker leak fix applied** | D6 was severely degraded by the worker pool leak bug. X1-X3 benefit from the fix (per-stage worker pools, CancelledError handling). | LOW RISK. The fix removes a source of run degradation, making all runs cleaner. This is a controlled variable improvement, not a confound. |
| 9 | **Crossover may increase invalidity rate** | Combining elements from two structurally different parent chains may produce syntactically or semantically invalid children more often than single-parent mutation. Higher invalidity wastes mutation budget. | DIAGNOSABLE. Compare invalidity rates (invalid programs / total programs) between control and treatment at gen 25. If treatment invalidity is substantially higher (>2x control), this is an important finding about the difficulty of LLM-driven crossover for complex programs. |

---

## 10. Stop Criteria

### Early termination criteria (per run)

- **Gen-0 val fitness > 0.30 (soft)**: Halt; initialization anomaly. Cold start should produce soft fitness in [0.10, 0.25].
- **Gen-0 val fitness = sentinel value (-1000.0)**: Halt; execution error.
- **Gen-0 n_steps != 7 for any run**: Halt; seed program initialization error.
- **Any run: invalidity rate > 95% at gen 10**: Halt; systemic failure. (Threshold raised from 90% to 95% because dynamic topology inherently produces higher invalidity than static -- D5 had 15%, D6 had 87% due to a bug now fixed.)

### Stagnation-based early completion

If `valid_frontier_fitness` shows no improvement for >= 10 consecutive generations AND current gen >= 15, the run may be terminated early. This is recorded as "early plateau" and the final generation's results are used.

### Run invalidation criteria

A run is excluded from all analyses if any of the following apply:

1. Thinking mode not active: `<think>` blocks absent from >= 5% of chain outputs at gen 1.
2. Invalidity rate > 95% at gen 10 (systemic failure, not evolutionary noise).
3. Gen-0 val fitness > 0.30 (initialization error).
4. `num_parents` mismatch: control run confirmed at 2 or treatment run confirmed at 1 in Hydra cfg dump.
5. `problem.name` not `chains/hover/full` for any run.
6. `pipeline` not `standard` for any run.
7. `max_elites_per_generation` confirmed at 5 (not 8) in post-hoc Hydra cfg inspection.
8. Test evaluation uses soft metric instead of discrete (metric contamination).
9. `FULL_CHAIN_CONFIG` not active (fallback to static mode).

If the control run (X1) is invalidated, the experiment is UNANSWERABLE -- there is no within-experiment comparison possible.
If 1 treatment run is invalidated, the remaining treatment run provides a point estimate (n=1 vs. n=1) with no variance information.
If both treatment runs are invalidated, the treatment hypothesis is UNANSWERABLE.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time per run (300 val samples, 25 gens, thinking mode) | ~8-12h |
| Total wall time (all 3 runs in parallel) | ~10-14h |
| Redis DBs | 3 (DBs 3, 4, 5) + DB 15 for load balancer |
| Chain LLM servers | 4 (shared pool via HOVER_CHAIN_URL) |
| Mutation LLM servers | 3 (shared pool via llm=balanced) |
| Test eval time | ~5 min/repeat x 5 repeats x 3 runs = ~75 min total |
| New code required | None -- all infrastructure exists from dynamic-topology experiment |

---

## 12. Open Questions / Risks

### Priority risks

**Risk 1 -- Mutation LLM cannot perform meaningful crossover (HIGH).**
The default mutation prompt instructs the LLM to "mutate" parent programs. With two parents, the LLM sees both code blocks labeled `=== Parent 1 ===` and `=== Parent 2 ===` but receives no explicit instruction to combine them. The LLM may simply pick the higher-fitness parent and apply a standard mutation, ignoring the second parent entirely. In this case, `num_parents=2` provides no advantage over `num_parents=1` and wastes the second parent's context window space.

**Diagnostic**: Analyze mutation logs for treatment runs. For each child program, compute structural similarity to each parent (Jaccard similarity of step types and positions, edit distance of prompt fields). If >80% of children are structurally closer to one parent than the other by a large margin, the LLM is not crossovering.

**Risk 2 -- Crossover produces more invalid programs (MEDIUM).**
Combining structural elements from two different-topology chains may produce programs that are syntactically valid Python but semantically broken (e.g., dependency references to non-existent steps, tool calls with wrong input formats). This would increase the invalidity rate and waste mutation budget.

**Diagnostic**: Compare invalidity rates at gen 10 and gen 25 between control and treatment. If treatment invalidity is >2x control, report this as a structural finding about LLM crossover difficulty.

**Risk 3 -- Load balancer starvation with 3 runs on 3 servers (LOW-MEDIUM).**
With 3 runs sharing 3 mutation servers, each run gets roughly 1 server equivalent of throughput. With `num_parents=1` and `num_parents=2` both producing 8 mutations per generation, throughput should be balanced. However, if crossover mutations take longer (because the LLM processes two programs instead of one), treatment runs may have lower throughput.

**Diagnostic**: Compare mutation latency (seconds per mutation call) between control and treatment. If crossover mutations take >1.5x longer, this reduces the effective compute budget for treatment runs within the 25-generation limit.

### Scientific open questions after this experiment

| Result pattern | Interpretation | Next experiment |
|---------------|----------------|-----------------|
| Treatment > control by >= +2.0pp, crossover diagnostic positive (true recombination) | Crossover is a productive operator for dynamic-topology evolution; structural diversity in the archive enables meaningful recombination | Powered replication at n>=3 per cell; analyze which parent combinations produce the highest-fitness offspring |
| Treatment > control by >= +2.0pp, crossover diagnostic negative (one-parent dominance) | Improvement is from seeing two programs (richer context for the LLM) rather than true crossover; the LLM uses the second parent as inspiration, not as a structural donor | Test whether providing two parents as read-only context (but asking for mutation of only one) achieves the same effect |
| Treatment ~ control, crossover diagnostic positive | Crossover produces structurally novel children but they are no fitter than single-parent mutations; structural recombination does not add value in this search space | Close crossover line for HoVer dynamic topology |
| Treatment ~ control, crossover diagnostic negative | **IV NOT REALIZED** -- LLM ignores second parent; `num_parents=2` is operationally equivalent to `num_parents=1`; result is uninformative about crossover | Test explicit crossover prompts that instruct the LLM to combine specific elements from each parent |
| Treatment > control, crossover diagnostic negative | **IV NOT REALIZED** -- improvement comes from richer context (seeing two programs), not from structural recombination; distinct from true crossover | Test providing two parents as read-only context with single-parent mutation instruction |
| Treatment < control | Crossover actively harms -- combining structures from different parents produces worse programs than refining a single parent | Investigate mechanism: higher invalidity? degenerate recombinations? conflicting design patterns? |

---

## Appendix A: Code Verification Required Before Launch

1. **`num_parents` override verification**: `python run.py problem.name=chains/hover/full pipeline=standard llm=balanced num_parents=1 --cfg job | grep num_parents` must show `1` for control; same with `num_parents=2` for treatment. Verify that `AllCombinationsParentSelector` is the parent selector class in both cases.

2. **`llm=balanced` config verification**: Confirm `balanced.yaml` contains exactly 3 endpoints (10.226.15.38:8777, 10.226.185.47:8777, 10.225.51.251:8777) and uses `BalancedChatOpenAI` with `pool_name: mutation` on Redis DB 15.

3. **`HOVER_CHAIN_URL` verification**: Confirm all 4 chain endpoints are reachable and serving Qwen3-8B in thinking mode. Test with a sample query.

4. **`chains/hover/full` problem variant**: Confirm it exists and is unchanged from the dynamic-topology experiment. Verify seed program is the standard 7-step chain with no frozen fields.

5. **Worker leak fix verification**: Confirm the `finally` block + `returned` flag pattern is present in `wrapper.py` and per-stage worker pools are active.

6. **Redis DBs 3, 4, 5**: Must show 0 keys before launch. DB 15 must be accessible for the load balancer.

7. **Hydra config verification for all 3 runs**: `--cfg job` check of `max_elites_per_generation: 8`, `stage_timeout: 5000`, `dag_timeout: 7200`, `model_name: Qwen3-235B-A22B-Thinking-2507`, `pipeline: standard`, `problem.name: chains/hover/full`, and correct `num_parents` per the Run Design Table.

8. **Gen-0 diagnostic**: After launch, verify gen-0 val fitness is in expected range [0.10, 0.25] for all runs. Verify n_steps=7 at gen 0 for all runs.

---

## Appendix B: Decision Tree

```
After gen-25 evaluations for X1-X3:

  Control (X1):        x1_test
  Treatment mean:      (x2_test + x3_test) / 2
  D5 reference:        60.15%

  Step 1: Control replication check
    Is X1 test within +/-5pp of D5 (60.15%)?
    YES -> D5 replicates under new infrastructure; proceed
    NO  -> Infrastructure confound; interpret with caution

  Step 2: Treatment vs. control (PRIMARY)
    delta = treatment_mean - x1_test

                         delta >= +4.0pp?
                        /                \
                      YES                 NO
                       |                   |
                STRONG POSITIVE      delta >= +2.0pp?
                (plan n>=3 repl)      /            \
                                   YES              NO
                                    |                |
                                POSITIVE          delta > 0?
                                (plan n>=3 repl)  /        \
                                                YES         NO
                                                 |           |
                                            SUGGESTIVE     NULL
                                            (assess if     (close
                                             follow-up     crossover
                                             warranted)    line)

  Step 3: Crossover diagnostic (treatment only, BEFORE interpreting delta)
    Analyze parent-child structural similarity for treatment runs.
    If >80% of children dominated by one parent:
      -> IV NOT REALIZED (regardless of delta)
      -> Next: explicit crossover prompts or structural crossover operators
    If true recombination confirmed:
      -> Proceed to interpret delta from Step 2
      If treatment >= control:
        - Determine mechanism (recombination vs. richer context)
      If treatment < control:
        - Report invalidity rate comparison
        - Analyze degenerate recombinations
```

---

## Appendix C: Why n=1 Control?

The asymmetric design (n=1 control, n=2 treatment) is unusual and warrants justification.

1. **Infrastructure constraint**: Only 3 mutation servers are available. With `llm=balanced` load balancing, all 3 runs share all servers, so the constraint is on total parallel runs (3), not on servers per run.

2. **Historical reference available**: D5 from `hover/dynamic-topology` provides a historical point estimate for single-parent dynamic-topology performance (60.15% test). X1 serves primarily as a contemporaneous replication of D5 under the current infrastructure (load balancer, worker leak fix), not as the sole baseline.

3. **Treatment variance is unknown**: Crossover has never been tested in the dynamic topology setting. Two treatment runs provide a minimal estimate of within-treatment variability, which is essential for planning a powered follow-up.

4. **Exploratory framing**: This experiment is explicitly exploratory. It is designed to estimate the direction and approximate magnitude of the crossover effect, not to provide definitive evidence. A powered follow-up (n>=3 per cell) would be needed regardless of the outcome to make a scientific claim.

The alternative (n=2 control, n=1 treatment) would provide slightly better replication of D5 but would give us zero variance information about the novel intervention, making follow-up planning impossible.

---

## Appendix D: Treatment Verification Checks

These checks should be encoded in `experiment.yaml` under `treatment_checks` for automated verification by `diagnose.py`.

| Check | Type | Target | Expected (Control X1) | Expected (Treatment X2, X3) |
|-------|------|--------|-----------------------|----------------------------|
| `num_parents` in Hydra cfg | `config_override` | All runs | `1` | `2` |
| `problem.name` in Hydra cfg | `config_override` | All runs | `chains/hover/full` | `chains/hover/full` |
| `pipeline` in Hydra cfg | `config_override` | All runs | `standard` | `standard` |
| `max_elites_per_generation` in Hydra cfg | `config_override` | All runs | `8` | `8` |
| Parent count in mutation logs | `log_pattern_present` | Treatment runs | N/A | `Running mutation agent for 2 parents` |
| Parent count in mutation logs | `log_pattern_present` | Control run | `Running mutation agent for 1 parents` | N/A |
| n_steps metric present in Redis | `redis_key_pattern` | All runs | PRESENT | PRESENT |

---

*Ready for Reviewer-2's scrutiny.*
