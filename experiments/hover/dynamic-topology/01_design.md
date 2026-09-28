# Experimental Design: HoVer Dynamic Topology -- Evolving Chain Structure vs. Fixed 7-Step Topology

**Date**: 2026-03-23
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft -- awaiting Reviewer-2

---

## 1. Research Question

All prior HoVer experiments have evolved programs within a fixed 7-step chain topology: 3 frozen tool steps (BM25 retrieval at steps 1, 4, 7) interleaved with 4 mutable LLM steps. The prompt fields of LLM steps are the sole evolutionary degrees of freedom. This topology was inherited from the task design and has never been questioned experimentally. Meanwhile, three rounds of prompt co-evolution (PR #84, #93, #109) have been definitively closed as unproductive, and soft fitness is the only confirmed positive intervention (+2.72pp, Cell C from PR #92). The question is: what is the next binding constraint?

The dynamic-topology hypothesis posits that the fixed chain structure itself is the bottleneck. A chain that can grow from 7 to 15 steps, introduce additional retrieval hops, change retrieval strategies (BM25 vs. BM25-deep), remove redundant LLM steps, or reorder dependencies may discover retrieval patterns that are structurally inaccessible to the fixed topology.

**Primary research question**: Does allowing evolution to modify chain topology (step count, step types, step dependencies) yield higher test retrieval coverage than evolving only within the fixed 7-step static topology, when both use soft (fractional) fitness?

**Secondary research question**: Does dynamic topology produce measurably different chain structures (step counts, tool/LLM ratios) relative to the static baseline, and if so, does structural diversity correlate with fitness?

---

## 2. Hypotheses

### Primary hypothesis: dynamic topology improves test retrieval coverage

**H0**: Mean discrete test retrieval coverage of the dynamic-topology condition does not exceed mean discrete test retrieval coverage of the static-topology condition by more than 2.0pp. Formally: mu_full - mu_static <= 2.0pp.

**H1**: Mean discrete test retrieval coverage of the dynamic-topology condition exceeds the static-topology condition by more than 2.0pp. The ability to add retrieval hops, adjust step count, and remove frozen-step constraints enables the evolutionary search to discover chain structures with higher 3-hop document coverage than the fixed 7-step topology permits.

### Secondary hypothesis: topology diversity

**H2**: Dynamic-topology runs produce evolved chains whose step counts differ from 7 in at least 50% of the final elite archive programs. This tests whether evolution actually uses the expanded search space or converges back to the original 7-step structure.

### Effect-size thresholds

All thresholds are defined relative to the Cell C reference mean of 54.37% (soft fitness, static topology, from PR #92).

| Treatment mean | Delta vs. Cell C (54.37%) | Verdict |
|----------------|--------------------------|---------|
| >= 58.37% | >= +4.0pp | **STRONG POSITIVE** |
| [56.37%, 58.37%) | [+2.0pp, +4.0pp) | **POSITIVE** |
| (54.37%, 56.37%) | (0pp, +2.0pp) | **SUGGESTIVE** |
| <= 54.37% | <= 0pp | **NULL** |

Additionally, the control cell (static_soft replication) serves as a replication check against Cell C (54.37%):

| Control mean | Delta vs. Cell C | Interpretation |
|-------------|------------------|---------------|
| [52.37%, 56.37%] | within +/-2.0pp of Cell C | Replication SUCCESS -- Cell C finding is robust |
| < 52.37% or > 56.37% | outside +/-2.0pp of Cell C | Replication CONCERN -- investigate |

**Important**: The primary test metric is always **discrete** retrieval coverage (all 3 gold docs found = 1, else 0) on the 300-sample held-out test set. This ensures direct comparability with all prior experiments and the GEPA benchmark (52.33%). Soft (fractional) fitness is used only for evolutionary selection within both conditions.

---

## 3. Independent Variable(s)

| Variable | Control value | Treatment value |
|----------|---------------|-----------------|
| **Chain validation mode** | `problem.name=chains/hover/static_soft` -- fixed 7-step topology, 3 frozen tool steps, 4 mutable LLM steps; soft fitness for evolution | `problem.name=chains/hover/full` -- free topology up to 15 steps, no frozen steps, allowed types = [llm, tool], available tools = [retrieve, retrieve_deep]; soft fitness with adaptive retrieval scoring |

### What differs between the two problem variants

| Dimension | `static_soft` (control) | `full` (treatment) |
|-----------|------------------------|--------------------|
| Max steps | 7 (fixed) | 15 (configurable via FULL_CHAIN_CONFIG) |
| Frozen steps | Steps 1, 4, 7 are frozen tool steps | No frozen steps -- all steps are mutable |
| Allowed step types | LLM only (tool steps frozen) | LLM and tool |
| Available tools | retrieve, retrieve_deep (frozen) | retrieve, retrieve_deep (evolvable) |
| require_final_llm | N/A (topology fixed) | False |
| Retrieval scoring | Positional (hardcoded step indices 0, 3, 6) | Adaptive (scans ALL tool-step outputs for gold articles) |
| Fitness computation | Soft: gold_found / n_gold per sample | Soft: gold_found / n_gold per sample (identical formula) |
| Seed program | 7-step chain with frozen field on tool steps | 7-step chain with NO frozen field, NO frozen steps |
| Additional metrics | -- | n_steps, n_tool_steps (observational only; `include_in_prompts: false` to avoid hidden IV) |
| validate.py return | dict | dict |
| Pipeline | standard | standard |

### Equivalence of scoring for 7-step chains

For a standard 7-step chain with tools at positions 0, 3, 6, the adaptive scoring in `full` and the positional scoring in `static_soft` produce identical discrete coverage results. This has been verified: both identify the same tool outputs and extract the same gold articles. The adaptive scoring becomes meaningfully different only when topology changes -- e.g., a chain with 4 tool steps at positions 0, 2, 5, 8 would be correctly scored by adaptive scoring but missed by positional scoring. This is exactly the behavior we want: the treatment's scoring adapts to the topology the treatment enables.

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test retrieval coverage at gen 25 (discrete, best-by-val) | 300-sample held-out test set; discrete scoring (all 3 gold docs = 1, else 0); thinking mode Qwen3-8B; 5 repeats per run | **YES -- primary** |
| Val fitness trajectory (gen 0-25, soft) | Per-generation `valid_frontier_fitness` from Redis | YES -- convergence diagnostic |
| Val-test gap (soft val vs. discrete test) | Best val fitness minus mean discrete test coverage | YES -- overfitting diagnostic |
| n_steps of best-by-val program | From program source code | YES (treatment only) -- topology evolution diagnostic |
| n_tool_steps of best-by-val program | From program source code | YES (treatment only) -- retrieval strategy diagnostic |
| Archive topology diversity at gen 25 | Distribution of step counts across elite archive | YES (treatment only) -- H2 diagnostic |
| Birth generation of best-by-val program | From Redis trajectory | NO -- convergence speed |
| Within-run test variance (5-repeat SD) | SD of 5 test evaluations per run | NO -- LLM stochasticity diagnostic |

**Primary metric**: Mean discrete test retrieval coverage (5-repeat average per run) at gen 25 for each condition, compared against each other and against the Cell C historical reference (54.37%).

**Test protocol**: 5 independent repeats of the full 300-sample test evaluation per run, identical to all prior experiments. The 5-repeat mean is the per-run estimate.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| **Test metric** | **Discrete retrieval coverage** (all 3 gold docs = 1, else 0) | Comparable to all prior experiments and GEPA; NOT changed by condition |
| **Evolutionary fitness** | **Soft (fractional)** -- gold_found / n_gold per sample | Both conditions use soft fitness; this is the confirmed positive intervention from PR #92 |
| `pipeline` | `standard` | Both variants return dict from validate.py |
| `prompts` | `default` | No domain-specific prompts; identical to Cell C |
| Validation sample size | 300 (first 300 train samples) | Default; identical to all prior experiments |
| Chain LLM | Qwen/Qwen3-8B, thinking mode ON, context 32768 | Required for GEPA comparison |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507, one server per run | Identical to all prior experiments |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` (explicit override) | Default is OpenRouter -- MUST override |
| `llm_base_url` | Per-run mutation LLM URL (see Run Design Table) | Explicit override; each run gets a dedicated mutation server |
| `num_parents` | 1 (explicit override; default is 2) | Single-parent mutation; identical to Cell C |
| `max_elites_per_generation` | 8 (explicit override; default is 5) | Identical to Cell C |
| `max_mutations_per_generation` | 8 | With num_parents=1, max_elites=8: C(8,1) = 8 mutations/gen |
| `stage_timeout` | 3000 (explicit override) | Identical to Cell C |
| `dag_timeout` | 7200 (explicit override) | Identical to Cell C |
| `max_generations` | 25 | Identical to Cell C |
| Seed initialization | Cold start (no `program_loader.problem_dir`) | Identical to Cell C |
| `mutation_mode` | `rewrite` | Default |
| HTTP timeout | 600s | Consistent with all prior experiments |
| BM25 corpus | wiki17_abstracts.jsonl.passages.pkl (~5.2M passages) | Shared corpus across tasks |

---

## 6. Run Design Table

| Run | Label | Cell | Wave | `problem.name` | `redis.db` | `pipeline` | Chain LLM URL | Mutation LLM URL (`llm_base_url`) |
|-----|-------|------|------|-----------------|-----------|-----------|---------------|-----------------------------------|
| D1 | hover-static-1 | Control | 1 | `chains/hover/static_soft` | 9 | `standard` | `http://10.226.17.25:8001/v1` | `http://10.226.72.211:8777/v1` |
| D2 | hover-static-2 | Control | 1 | `chains/hover/static_soft` | 10 | `standard` | `http://10.225.185.235:8001/v1` | `http://10.226.15.38:8777/v1` |
| D3 | hover-static-3 | Control | 2 | `chains/hover/static_soft` | 11 | `standard` | `http://10.226.17.25:8001/v1` | `http://10.226.72.211:8777/v1` |
| D4 | hover-static-4 | Control | 2 | `chains/hover/static_soft` | 12 | `standard` | `http://10.225.185.235:8001/v1` | `http://10.226.15.38:8777/v1` |
| D5 | hover-full-1 | Treatment | 1 | `chains/hover/full` | 13 | `standard` | `http://10.226.17.25:8000/v1` | `http://10.226.185.47:8777/v1` |
| D6 | hover-full-2 | Treatment | 1 | `chains/hover/full` | 14 | `standard` | `http://10.225.185.235:8000/v1` | `http://10.225.51.251:8777/v1` |
| D7 | hover-full-3 | Treatment | 2 | `chains/hover/full` | 15 | `standard` | `http://10.226.17.25:8000/v1` | `http://10.226.185.47:8777/v1` |
| D8 | hover-full-4 | Treatment | 2 | `chains/hover/full` | 1 | `standard` | `http://10.225.185.235:8000/v1` | `http://10.225.51.251:8777/v1` |

**Run naming convention**: D-prefix for "Dynamic topology" experiment.

**Execution plan**: 4 chain endpoints and 4 mutation endpoints are available. Wave 1 launches D1, D2, D5, D6 (2 control + 2 treatment). When wave 1 completes, wave 2 launches D3, D4, D7, D8 (2 control + 2 treatment). Total wall time: approximately 2x single-run time (16-24h). Each wave contains both conditions in equal numbers to avoid wave-treatment aliasing.

### Host assignment: shuffled to avoid confounds

Each cell has runs distributed across both chain hosts (10.226.17.25 and 10.225.185.235):
- Control: D1 on host A:8001, D2 on host B:8001, D3 on host A:8001, D4 on host B:8001
- Treatment: D5 on host A:8000, D6 on host B:8000, D7 on host A:8000, D8 on host B:8000

Wave 1 uses all 4 endpoints (D1-D2 control, D5-D6 treatment). Wave 2 reuses all 4 endpoints (D3-D4 control, D7-D8 treatment). Ensure wave-1 runs have fully completed and exec_runner workers are killed before launching wave 2. Restart vLLM serving processes between waves.

### Redis DB assignments

DBs 9-15 + DB 1 (8 total). Previous experiment (co-evolution-bus) used DBs 9-12 -- these must be archived and flushed before launch. DBs 13-15 and 1 are fresh.

**Pre-launch**: Archive co-evolution-bus runs from DBs 9-12 using `tools/experiment/archive_run.sh`, then flush all 8 DBs via `tools/flush.py --db 1 9 10 11 12 13 14 15 --confirm`.

### Combinatorics verification

| Run | num_parents | max_elites | Parent combos | max_mutations | Actual mut/gen |
|-----|:-----------:|:---------:|:-------------:|:-------------:|:--------------:|
| D1-D8 | 1 | 8 | C(8,1) = 8 | 8 | 8 |

---

## 7. Sample Size Justification

### Design: n=4 per cell, 8 runs total

This is the maximum utilization of all 4 mutation servers across 2 waves. With n=4 per cell, we obtain:

1. **Within-cell variance estimates** with df=3, sufficient for t-tests.
2. **Welch's two-sample t-test** with n1=4, n2=4 for treatment vs. control.
3. **Substantially better power** than prior experiments (n=2 per cell).

### Power analysis

Using the baseline inter-run SD estimates:
- Cell C (PR #92): inter-run SD ~ 1.0pp (from F3=55.07%, F4=53.67%)
- Baseline (PR #90): inter-run SD ~ 0.63pp (n=4)
- Co-evolution bus (PR #109): inter-run SD ~ 1.41pp (n=3)

Conservative estimate: SD = 1.5pp (upper bound from prior experiments).

**MDE at n=4 per cell (Welch's t, one-sided, alpha=0.05, 80% power)**:

    MDE = (t_alpha + t_beta) * SD * sqrt(1/n1 + 1/n2)
        = (t(0.95, df~6) + t(0.80, df~6)) * 1.5 * sqrt(1/4 + 1/4)
        = (1.943 + 0.906) * 1.5 * 0.707
        = 3.02pp

At SD = 1.0pp (optimistic):

    MDE = (1.943 + 0.906) * 1.0 * 0.707 = 2.01pp

**Conclusion**: At conservative SD=1.5pp, we can detect effects of >= 3.0pp at 80% power, sufficient to detect STRONG POSITIVE effects (+4.0pp). At optimistic SD=1.0pp, the MDE drops to 2.0pp, making even POSITIVE effects detectable. This is the best power achievable with our infrastructure.

### Replication value of the control cell

The control cell (static_soft, n=4) provides an independent replication of Cell C from PR #92 (n=2). If the control cell mean falls within +/-2.0pp of Cell C's 54.37%, we gain confidence that the soft fitness finding is robust and not a lucky draw. With n=4, this is the strongest replication to date. This replication has standalone scientific value regardless of the treatment result.

---

## 8. Statistical Test

### Test 1: Treatment vs. control (PRIMARY)

**Comparison**: Mean discrete test coverage of treatment runs (D5-D8, n=4) vs. control runs (D1-D4, n=4).

**Test**: Welch's two-sample t-test, one-sided (H1: mu_treatment > mu_control).

**Statistic**: t = (mean_treatment - mean_control) / sqrt(s_treatment^2/4 + s_control^2/4)

**Degrees of freedom**: Satterthwaite approximation.

**Significance**: alpha = 0.05 (one-sided). Primary decision criterion is the effect-size table in Section 2.

### Test 2: Treatment vs. Cell C historical reference (SECONDARY)

**Comparison**: Mean discrete test coverage of treatment runs (D5-D8, n=4) vs. Cell C mean (54.37%, n=2, SD=0.99pp).

**Test**: Welch's two-sample t-test, one-sided (H1: mu_treatment > mu_cellC).

**Purpose**: Determines whether dynamic topology improves upon the strongest known HoVer configuration. If treatment beats control but not Cell C, the improvement is within the static_soft noise floor.

### Test 3: Control replication check (SECONDARY)

**Comparison**: Mean discrete test coverage of control runs (D1-D4, n=4) vs. Cell C mean (54.37%, n=2).

**Test**: Welch's two-sample t-test, two-sided.

**Purpose**: If p < 0.05 (two-sided), the control cell does not replicate Cell C. This would indicate instability in the soft fitness finding and complicate interpretation of the treatment comparison. If p >= 0.05, Cell C replicates successfully.

### Test 4: Topology diversity (H2, SECONDARY, treatment only)

**Metric**: Proportion of elite archive programs (at gen 25) with step count != 7, averaged across treatment runs D5-D8.

**Threshold**: H2 requires >= 50%. Reported descriptively with exact counts.

### Test 5: Convergence speed comparison (EXPLORATORY)

**Metric**: Generation at which val fitness first exceeds 70% (soft).

**Comparison**: Treatment runs vs. control runs, descriptive (median, range).

**Significance threshold**: alpha = 0.05 (one-sided for primary Test 1)
**How computed**: scipy.stats.ttest_ind (Welch's), with bootstrapped CI as sensitivity check (10,000 resamples of per-run means).

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Different validate.py code paths** | Treatment uses adaptive retrieval scoring (scans all tool outputs); control uses positional scoring (hardcoded indices 0, 3, 6). These are different code paths that could introduce scoring bugs. | MITIGATED. For 7-step chains (the starting topology), both scoring methods produce identical results (verified). The adaptive scoring diverges only for non-7-step chains, which is the intended behavior. Unit test before launch: run the seed program through both validate.py files and confirm identical fitness. |
| 2 | **Larger search space may slow convergence** | The full-chain mode has a vastly larger search space (up to 15 steps, any combination of tool/LLM, no frozen steps). With only 25 generations and 8 mutations/gen, evolution may not explore this space effectively, producing NULL results that reflect insufficient compute rather than an inherent limit of the approach. | ACKNOWLEDGED. This is a genuine risk. If treatment val fitness at gen 25 is still rising (no plateau), we will note that 25 generations may be insufficient and propose a follow-up with 50 generations. The 25-gen budget was chosen for comparability with Cell C. |
| 3 | **No frozen steps removes a structural prior** | In static_soft, frozen tool steps at positions 1, 4, 7 guarantee 3 retrieval hops. In full mode, evolution could remove retrieval steps entirely, producing degenerate chains (all-LLM, single-tool, etc.). These would score poorly but waste mutation budget on dead-end programs. | MITIGATED by natural selection. Programs that drop retrieval steps score near-zero on retrieval coverage and are immediately eliminated from the archive. The soft fitness gradient ensures that even partial retrieval (1/3 or 2/3 docs) is rewarded. Degenerate programs should be strongly selected against within 1-2 generations. Monitor archive composition at gen 5 for degenerate programs. |
| 4 | **Seed program differs structurally** | The control seed has frozen fields on tool steps; the treatment seed has no frozen fields. Even though both start with the same 7-step topology, the mutation LLM sees different program structures. | LOW RISK. The treatment seed is the same 7-step chain but without frozen annotations. The mutation LLM should treat unfrozen tool steps as additional mutation targets, which is exactly the intended treatment effect. This is a feature of the design, not a confound. |
| 5 | **Host-treatment confound** | If all treatment runs share one chain host, host-level differences confound with treatment. | MITIGATED. Shuffled host assignment: control has runs on both hosts (A, B, A); treatment has runs on both hosts (B, A, B). No systematic host-cell confound. |
| 6 | **Wave execution confound** | D3 and D6 launch in wave 2 after D1, D2, D4, D5 complete. If server conditions change between waves, wave-2 runs may differ from wave-1 runs. | LOW RISK. All servers are dedicated with no contention. Wave 1 has 2 control + 2 treatment; wave 2 has 1 control + 1 treatment. Both conditions are represented in both waves, avoiding wave-treatment aliasing. Post-hoc diagnostic: compare wave-1 vs. wave-2 runs within each condition to bound wave effects. Restart vLLM serving processes between waves as a precaution. |
| 10 | **Val-test selection bias** | Selecting the best program by val fitness and evaluating on test introduces upward bias in the test estimate. | ACCEPTED. This bias is present in all conditions and in the Cell C reference, so it does not differentially affect the treatment comparison. Standard practice across all experiments in this research program. |
| 7 | **Adaptive scoring inflates soft fitness relative to positional scoring** | The adaptive scorer in `full` scans ALL tool outputs, potentially finding gold articles in outputs that the positional scorer in `static_soft` would miss. This could make treatment val fitness appear higher than control val fitness even for equivalent programs. | NOT A CONFOUND for the primary metric. The primary metric is discrete test coverage, which requires ALL 3 gold docs. Whether found by adaptive or positional scoring, the final 0/1 is the same for complete retrieval. For val fitness (soft), the adaptive scorer could give partial credit for articles found in "extra" tool steps, which is the intended behavior -- it reflects the treatment's expanded capability. Report both soft val fitness and discrete test coverage for interpretability. |
| 8 | **Mutation LLM may struggle with topology mutations** | The Qwen3-235B mutation LLM has been trained (implicitly, via GigaEvo prompts) to modify prompt fields within fixed-structure programs. It may not know how to add/remove steps or change step types, producing only prompt-level mutations even in full-chain mode. | ACKNOWLEDGED. This is a genuine risk and would produce a NULL result that reflects mutation LLM limitations, not topology limitations. Monitor the n_steps and n_tool_steps metrics across generations. If step count remains at 7 for all 25 generations in all 3 treatment runs, this confound is binding. Pre-commit: if mean step count across treatment elites at gen 25 is within [6.5, 7.5], flag the result as "LLM mutation ceiling" rather than "topology not helpful." |
| 9 | **Different problem directories = different metrics.yaml** | The `full` variant has additional metrics (n_steps, n_tool_steps) not present in `static_soft`. This changes what Redis tracks but does not affect fitness computation. | NO RISK. Additional metrics are observational only. Fitness is computed identically in both conditions. |

---

## 10. Stop Criteria

### Early termination criteria (per run)

- **Gen-0 val fitness > 0.30 (soft)**: Halt; initialization anomaly. Cold start from the seed program should produce soft fitness in the range [0.10, 0.25] based on Cell C gen-0 data. Investigate.
- **Gen-0 val fitness = sentinel value (-1000.0)**: Halt; execution error.
- **Treatment runs: gen-0 n_steps != 7**: Halt; seed program initialization error. The seed should be the standard 7-step chain.
- **Any run: invalidity rate > 90% at gen 10**: Halt; systemic failure.

### Stagnation-based early completion

If `valid_frontier_fitness` shows no improvement for >= 10 consecutive generations AND current gen >= 15, the run may be terminated early. This is not an invalidation -- it is recorded as "early plateau" and the final gen's results are used.

### Run invalidation criteria

A run is excluded from all analyses if any of the following apply:

1. Thinking mode not active: `<think>` blocks absent from >= 5% of chain outputs at gen 1.
2. Invalidity rate > 90% at gen 10.
3. Gen-0 val fitness > 0.30 (initialization error).
4. `max_elites_per_generation` confirmed at 5 (not 8) in post-hoc Hydra cfg inspection.
5. `num_parents` confirmed at 2 (not 1) in post-hoc Hydra cfg inspection.
6. `pipeline` not `standard` for any run.
7. `problem.name` mismatch: control run pointing to `full` or treatment run pointing to `static_soft`.
8. Test evaluation uses soft metric instead of discrete (metric contamination).
9. Treatment run: `FULL_CHAIN_CONFIG` not active (e.g., fallback to static mode).

If 3+ runs in a cell are invalidated, that cell's hypothesis is UNANSWERABLE.
If 1-2 runs are invalidated, the remaining runs provide a reduced-power estimate (n=3 or n=2).

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time per run (300 val samples, 25 gens, thinking mode) | ~8-12h |
| Total wall time (wave 1: 4 parallel, wave 2: 4 parallel) | ~20-24h |
| Redis DBs | 8 (DBs 1, 9-15) |
| Chain LLM servers | 4 (one per parallel run) |
| Mutation LLM servers | 4 (one per parallel run) |
| Test eval time | ~5 min/repeat * 5 repeats * 8 runs = ~200 min total |
| New code required | (1) `problems/chains/hover/full/` problem variant (validate.py, metrics.yaml, initial_programs/, FULL_CHAIN_CONFIG), (2) test.py for full variant with adaptive scoring + discrete test metric |

**Note**: The `chains/hover/full/` problem variant has already been created. Implementation phase should verify correctness, not build from scratch.

---

## 12. Open Questions / Risks

### Priority risks

**Risk 1 -- Mutation LLM cannot perform topology mutations (HIGH).**
The mutation LLM (Qwen3-235B) has never been asked to add or remove chain steps in a GigaEvo context. The default mutation prompts describe program modification in terms of code-level changes, not structural chain modification. If the LLM only modifies prompt fields (as in static mode), the treatment reduces to static evolution without frozen steps -- a much weaker intervention than intended.

**Mitigation**: Inspect treatment runs at gen 3. If the mutation log shows no topology changes (step additions, removals, or type changes) across all 24 mutations (8 per gen * 3 gens), this risk is realized. Pre-commit: if no topology change occurs in the first 5 generations across all 3 treatment runs, issue Amendment A1 to add a "topology hint" to the mutation prompt (describing that step count and step types are mutable). This amendment does NOT change the hypothesis -- it ensures the IV is actually active.

**Risk 2 -- Larger search space dilutes evolutionary signal (MEDIUM).**
With up to 15 possible steps, 2 step types, 2 tool options, and no frozen constraints, the full-chain search space is combinatorially larger than the static search space. With only 8 mutations per generation and 25 generations (200 total mutations), the search may not cover enough of this space to find improvements.

**Mitigation**: Compare val fitness trajectories. If treatment val fitness is still rising at gen 25 (positive slope in last 5 gens) while control has plateaued, this suggests the search space is productive but underexplored. Pre-commit to a 50-gen follow-up if treatment shows val fitness improvement between gen 20-25 of >= 0.5pp/gen.

**Risk 3 -- Degenerate programs waste budget (LOW-MEDIUM).**
Evolution could produce chains with 0 tool steps (all-LLM), which score 0.0 on retrieval. Each degenerate program wastes one of 8 mutation slots per generation.

**Mitigation**: Natural selection eliminates degenerate programs from the archive. With max_elites=8 and soft fitness, any program with >= 1 gold doc found outcompetes a 0-doc program. Monitor the fraction of degenerate programs (n_tool_steps = 0) at each generation. If > 50% of mutations produce degenerate programs at gen 10, the mutation LLM is not learning from fitness feedback.

**Risk 4 -- Control cell does not replicate Cell C (MEDIUM).**
Cell C was n=2; the control cell replicates with n=3. If the control mean deviates significantly from 54.37%, the Cell C finding may have been a lucky draw, complicating interpretation of the treatment comparison.

**Mitigation**: The control cell serves dual purpose: (a) replication check on Cell C, and (b) contemporaneous comparison for the treatment. Even if the control mean differs from Cell C, the within-experiment control-vs-treatment comparison remains valid.

### Scientific open questions after this experiment

| Result pattern | Interpretation | Next experiment |
|---------------|----------------|-----------------|
| Treatment > control by >= +2.0pp, topology diversity high | Dynamic topology is a productive intervention; chain structure was the binding constraint | Replicate at n=4; analyze what topologies win (more hops? deeper retrieval? fewer LLM steps?) |
| Treatment > control by >= +2.0pp, topology diversity low (step count ~ 7) | Improvement comes from unfreezing tool steps (editable retrieval params), not from topology change per se | Focused experiment: static topology with unfrozen tool steps vs. frozen tool steps |
| Treatment ~ control, topology diversity high | Evolution explores topology but finds no improvement -- the 7-step structure is near-optimal | Close topology line; pivot to retrieval engine (dense retrieval, hybrid BM25+ColBERT) |
| Treatment ~ control, topology diversity low | Mutation LLM cannot perform topology changes -- the IV was not active | Add topology hints to mutation prompt and re-run; or implement explicit topology mutation operators |
| Treatment < control | Free topology actively harms -- removing the 7-step structural prior was destructive | Investigate mechanism: are degenerate programs crowding the archive? Is the mutation LLM introducing structural errors? |
| Control does not replicate Cell C (mean outside +/-2.0pp) | Soft fitness finding is fragile; Cell C may have been a lucky draw | Replicate Cell C at n=4 before any further interventions |

---

## Appendix A: Code Verification Required Before Launch

1. **Seed program identity**: The seed program in `chains/hover/full/initial_programs/` must be functionally identical to the seed in `chains/hover/static_soft/initial_programs/` (same 7-step topology, same prompts). The only structural difference should be the absence of `frozen` fields in the full variant.

2. **Scoring equivalence on seed program**: Run the seed program through both `static_soft/validate.py` (positional scoring) and `full/validate.py` (adaptive scoring) on the same 50-sample subset. Soft fitness values must match to within +/-0.01. Discrete coverage must be identical.

3. **FULL_CHAIN_CONFIG verification**: Confirm that `full/validate.py` (or equivalent config) enforces: max_steps=15, allowed_step_types=[llm, tool], available_tools=[retrieve, retrieve_deep], require_final_llm=False.

4. **Additional metrics present**: Confirm that `full/metrics.yaml` includes `n_steps` and `n_tool_steps` as tracked metrics. Confirm that `static_soft/metrics.yaml` does NOT include these (to avoid false treatment verification failures on the control).

5. **Hydra config verification for all 6 runs**: `--cfg job` check of `num_parents: 1`, `max_elites_per_generation: 8`, `stage_timeout: 3000`, `dag_timeout: 7200`, `model_name: Qwen3-235B-A22B-Thinking-2507`, `pipeline: standard`, and correct `problem.name` per the Run Design Table.

6. **Redis DBs 9-14**: Must show 0 keys after archival and flush.

7. **Gen-0 diagnostic**: After launch, verify gen-0 val fitness is in expected range [0.10, 0.25] for all runs. Treatment runs: verify n_steps=7 at gen 0.

8. **Test.py for full variant**: Confirm that `full/test.py` computes DISCRETE coverage (all 3 gold docs = 1, else 0) as the primary metric, using adaptive scoring that scans all tool outputs. The discrete metric must be present in the output even though evolution uses soft fitness.

---

## Appendix B: Decision Tree

```
After gen-25 evaluations for D1-D6:

  Control mean (D1-D3):     control_mean
  Treatment mean (D4-D6):   treatment_mean
  Cell C reference:         54.37%

  Step 1: Replication check
    |control_mean - 54.37%| <= 2.0pp?
    YES → Cell C replicates; proceed to Step 2
    NO  → Cell C replication CONCERN; report but proceed

  Step 2: Treatment vs. control (PRIMARY)
    delta = treatment_mean - control_mean

                         delta >= +4.0pp?
                        /                \
                      YES                 NO
                       |                   |
                STRONG POSITIVE      delta >= +2.0pp?
                (topology works;      /            \
                 replicate n=4)     YES              NO
                                     |                |
                                 POSITIVE          delta > 0?
                                 (replicate n=4)   /        \
                                                 YES         NO
                                                  |           |
                                             SUGGESTIVE     NULL
                                             (extend to     (close
                                              50 gens if     topology
                                              trajectory     line or
                                              rising)       check H2)

  Step 3: Topology diversity check (H2, treatment only)
    If treatment > control:
      - Analyze which topologies emerged
      - Report n_steps distribution
      - Design follow-up to isolate topology mechanism
    If treatment ~ control AND topology diversity low:
      - Mutation LLM ceiling → add topology hints
    If treatment ~ control AND topology diversity high:
      - 7-step structure is near-optimal → pivot to retrieval engine
```

---

## Appendix C: Why Control Cell Instead of Historical Reference Only?

Prior experiments (feedback_softfit, prompt_coevolution, co-evolution-bus) used Cell C (n=2) as the sole reference baseline. This experiment includes a fresh control cell (n=3) for three reasons:

1. **Replication**: Cell C was n=2. A fresh n=3 replication of static_soft provides independent evidence that soft fitness improves over the discrete baseline. If the control cell does not replicate Cell C, we learn something important about the robustness of the soft fitness finding -- before interpreting any treatment effect.

2. **Contemporaneous comparison**: The treatment comparison is made against a contemporaneous control, not a historical one. This eliminates temporal confounds (server drift, model updates, Redis behavior changes) that accumulate over weeks of experimentation.

3. **Statistical power**: With n=3 control + n=3 treatment, the within-experiment t-test has more power than comparing n=3 treatment against n=2 historical (Cell C). The Satterthwaite df is higher, and both variance estimates come from the same experimental conditions.

The Cell C comparison (Test 2) remains as a secondary analysis to contextualize the result against the strongest known HoVer configuration.

---

## Appendix D: Treatment Verification Checks

These checks should be encoded in `experiment.yaml` under `treatment_checks` for automated verification by `diagnose.py`.

| Check | Type | Target | Expected (Control) | Expected (Treatment) |
|-------|------|--------|--------------------|--------------------|
| `problem.name` in Hydra cfg | `config_override` | All runs | `chains/hover/static_soft` (D1-D3) | `chains/hover/full` (D4-D6) |
| `pipeline` in Hydra cfg | `config_override` | All runs | `standard` | `standard` |
| n_steps metric present in Redis | `redis_key_pattern` | Treatment runs | ABSENT | PRESENT (observational, not in mutation prompts) |
| n_tool_steps metric present in Redis | `redis_key_pattern` | Treatment runs | ABSENT | PRESENT (observational, not in mutation prompts) |
| Frozen field in elite program code | `log_pattern_absent` | Treatment runs | Present (frozen tool steps) | ABSENT (no frozen steps) |
| Step count in elite program code | `program_structure` | Treatment runs | Always 7 | May vary from 3 to 10 |

---

*Ready for Reviewer-2's scrutiny.*
