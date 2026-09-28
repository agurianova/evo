# Ablation: Standard vs Deep Retrieval in HoVer

**Date**: 2026-03-31
**Researcher**: Dr. Elena Voss (ML Research Methodologist)
**Status**: Draft -- awaiting Reviewer-2

---

## Research Question

Does removing `retrieve_deep` (BM25 k=10) from the tool registry and using only `retrieve` (BM25 k=7) affect evolved chain fitness on HoVer? And does the answer depend on whether the chain topology is static (fixed 7-step) or dynamic (free topology)?

This is a 2x2 factorial ablation: {static, dynamic} x {standard retrieval only, standard + deep retrieval}.

---

## Background & Motivation

All prior HoVer experiments provide two BM25 retrieval tools: `retrieve` (k=7, returning 7 candidate passages) and `retrieve_deep` (k=10, returning 10 candidates). The GEPA benchmark -- our primary external reference at 52.33% test discrete coverage -- uses only k=7 retrieval. Every GigaEvo experiment has made `retrieve_deep` available, and the best-performing evolved chains (hover/dynamic-topology D5/D6: 60.78% test) use `retrieve_deep` for at least one hop.

This creates a fairness concern: if GigaEvo's gains over GEPA are primarily driven by the deeper retrieval budget (43% more candidates per query), the comparison overstates the contribution of evolutionary chain optimization. The question has two dimensions:

1. **GEPA comparison fairness**: If restricting GigaEvo to k=7 (matching GEPA) still produces gains over GEPA's 52.33%, the evolutionary approach adds value beyond retrieval budget. If the gains vanish, the comparison was confounded by retrieval depth.

2. **Simplification opportunity**: If `retrieve_deep` provides no meaningful benefit, the tool registry can be simplified, the search space for dynamic topology runs is reduced, and future experiments need not carry two retrieval variants.

The 2x2 factorial design separates two mechanisms:
- **Static chains**: Deep retrieval matters only at the frozen Step 7 (third hop). The static seed uses `retrieve_deep` at Step 7, `retrieve` at Steps 1 and 4. Removing `retrieve_deep` forces Step 7 to use `retrieve` (k=7 instead of k=10). This is a clean ablation of retrieval depth at the final hop.
- **Dynamic chains**: The mutation LLM can freely assign `retrieve` or `retrieve_deep` to any tool step. Removing `retrieve_deep` from the registry constrains the search space. If dynamic chains compensate by adding more retrieval hops (each at k=7), the depth reduction may be offset by breadth.

### Prior results

| Experiment | Retrieval tools | Topology | Test discrete coverage |
|------------|----------------|----------|------------------------|
| GEPA benchmark | k=7 only | Fixed (single-hop) | 52.33% |
| hover/baseline (PR #90) | k=7 + k=10 | Static 7-step | 51.65% (grand mean, n=4) |
| hover/feedback_softfit (PR #92) | k=7 + k=10 | Static 7-step | 54.37% (Cell C mean, n=2) |
| hover/dynamic-topology D5/D6 (PR #116) | k=7 + k=10 | Dynamic (up to 15 steps) | 60.78% (best run) |
| hover/steady-state-v2 (PR #138) | k=7 + k=10 | Dynamic (full) | 85.2% val soft (best run) |

No prior experiment has tested k=7-only retrieval.

---

## Design (2x2 factorial)

| Factor | Level A | Level B |
|--------|---------|---------|
| **Topology** | Static (fixed 7-step, `chains/hover/static_soft`) | Dynamic (free topology, `chains/hover/full`) |
| **Retrieval** | Standard only (`retrieve` k=7) | Standard + deep (`retrieve` k=7, `retrieve_deep` k=10) |

The topology factor is manipulated via `problem.name`, which selects the validate.py code path and chain validation mode. The retrieval factor is manipulated by the tool registry in validate.py: the "no-deep" variants register only `retrieve`; the "deep" variants register both `retrieve` and `retrieve_deep`.

**New problem variants needed**:
- `chains/hover/static_soft_no_deep` -- identical to `chains/hover/static_soft` except: (a) tool registry has only `retrieve`, no `retrieve_deep`; (b) seed program uses `retrieve` at Step 7 instead of `retrieve_deep`.
- `chains/hover/full_no_deep` -- identical to `chains/hover/full` except: (a) tool registry has only `retrieve`, no `retrieve_deep`; (b) `FULL_CHAIN_CONFIG["available_tools"]` lists only `["retrieve"]`; (c) seed program uses `retrieve` at Step 7 instead of `retrieve_deep`.

The existing `chains/hover/static_soft` and `chains/hover/full` serve as the deep-retrieval conditions without modification.

---

## Conditions Table

| Run | Label | Cell | Topology | Retrieval | `problem.name` | `redis.db` | Engine |
|-----|-------|------|----------|-----------|-----------------|------------|--------|
| R1 | static-std-1 | A (static + standard) | Static | Standard only | `chains/hover/static_soft_no_deep` | 3 | steady_state |
| R2 | static-std-2 | A (static + standard) | Static | Standard only | `chains/hover/static_soft_no_deep` | 4 | steady_state |
| R3 | static-deep-1 | B (static + deep) | Static | Standard + deep | `chains/hover/static_soft` | 5 | steady_state |
| R4 | static-deep-2 | B (static + deep) | Static | Standard + deep | `chains/hover/static_soft` | 6 | steady_state |
| R5 | dynamic-std-1 | C (dynamic + standard) | Dynamic | Standard only | `chains/hover/full_no_deep` | 7 | steady_state |
| R6 | dynamic-std-2 | C (dynamic + standard) | Dynamic | Standard only | `chains/hover/full_no_deep` | 8 | steady_state |
| R7 | dynamic-deep-1 | D (dynamic + deep) | Dynamic | Standard + deep | `chains/hover/full` | 9 | steady_state |
| R8 | dynamic-deep-2 | D (dynamic + deep) | Dynamic | Standard + deep | `chains/hover/full` | 10 | steady_state |

**N = 2 per condition, 4 conditions, 8 runs total.**

All runs share:
- Engine: `evolution=steady_state`, `scheduling=lpt_chain`
- Chain LLM: LiteLLM proxy at `http://10.232.30.185:4000/v1` (Qwen/Qwen3-8B, thinking mode)
- Mutation LLM: LiteLLM proxy (Qwen3-235B, `llm=balanced`)
- `pipeline=standard`
- `max_generations=25`, `max_in_flight=8`, `num_parents=1`, `max_elites_per_generation=8`, `max_mutations_per_generation=8`
- `stage_timeout=6000`, `dag_timeout=14400`
- Cold start (no `program_loader.problem_dir`)

**Execution plan**: All 8 runs launch simultaneously. The LiteLLM proxy handles load balancing for both chain and mutation LLMs, eliminating host-treatment confounds. If infrastructure cannot support 8 concurrent runs, split into two waves of 4, each wave containing one run from every condition (R1+R3+R5+R7 in wave 1; R2+R4+R6+R8 in wave 2) to avoid wave-condition aliasing.

**Redis DB assignments**: DBs 3-10. All must be archived (if occupied) and flushed before launch.

**`extra_overrides` per condition**:
- Cell A (R1, R2): `[evolution=steady_state, scheduling=lpt_chain, problem.name=chains/hover/static_soft_no_deep]`
- Cell B (R3, R4): `[evolution=steady_state, scheduling=lpt_chain, problem.name=chains/hover/static_soft]`
- Cell C (R5, R6): `[evolution=steady_state, scheduling=lpt_chain, problem.name=chains/hover/full_no_deep]`
- Cell D (R7, R8): `[evolution=steady_state, scheduling=lpt_chain, problem.name=chains/hover/full]`

---

## Primary Metric

**Test discrete retrieval coverage** (all 3 gold docs found = 1, else 0) on the 300-sample held-out test set, using the best-by-val program from each run. 5 independent repeats per run; the 5-repeat mean is the per-run estimate.

This is the same metric used across all prior HoVer experiments and is directly comparable to the GEPA benchmark (52.33%).

### Analysis plan

The 2x2 design enables three planned comparisons:

1. **Main effect of retrieval depth** (PRIMARY): Mean test coverage of standard-only runs (R1+R2+R5+R6, n=4) vs. deep runs (R3+R4+R7+R8, n=4). Welch's t-test, one-sided (H1: deep > standard), alpha = 0.10. This answers: does `retrieve_deep` improve fitness across topologies?

2. **Interaction: does topology moderate the retrieval effect?** Compare the retrieval effect within static (Cell A vs. Cell B) and within dynamic (Cell C vs. Cell D). If the gap is large in static but small in dynamic (or vice versa), there is an interaction. Assessed descriptively at N=2 per cell (formal interaction test is underpowered).

3. **GEPA-fair comparison**: Mean test coverage of dynamic + standard-only (Cell C: R5+R6) vs. GEPA benchmark (52.33%). One-sample t-test, one-sided (H1: Cell C > 52.33%). This answers: does GigaEvo beat GEPA even when restricted to the same retrieval budget?

### Effect-size thresholds (retrieval main effect: deep minus standard)

| Delta | Verdict |
|-------|---------|
| >= +4.0pp | **STRONG POSITIVE** -- deep retrieval is a major advantage; GEPA comparison is confounded |
| [+2.0pp, +4.0pp) | **POSITIVE** -- deep retrieval helps meaningfully |
| (0pp, +2.0pp) | **SUGGESTIVE** -- directional but small; GEPA comparison is approximately fair |
| <= 0pp | **NULL** -- deep retrieval provides no benefit; GEPA comparison is fair |

### Sample size justification

N=2 per cell, pooled to N=4 per retrieval level for the primary comparison. Using conservative SD = 1.5pp (upper bound from prior experiments):

- SE = 1.5 * sqrt(1/4 + 1/4) = 1.06pp
- MDE at 80% power (t(0.10, df~6), one-sided): (1.440 + 0.906) * 1.06 = 2.49pp
- MDE at 80% power with optimistic SD = 0.8pp: 1.33pp

The primary test (pooled n=4 per level) can detect effects of >= 2.5pp at conservative SD. This is sufficient to detect POSITIVE and STRONG POSITIVE effects. Within-cell comparisons (n=2 per cell) have MDE ~ 4.4pp and serve as directional diagnostics only.

---

## Secondary Metrics

| Metric | How measured | Purpose |
|--------|-------------|---------|
| Val soft fitness trajectory (gen 0-25) | `valid_frontier_fitness` from Redis | Convergence diagnostic; detect if standard-only converges slower |
| Val-test gap | Best val soft fitness minus mean discrete test coverage | Overfitting diagnostic |
| n_steps of best-by-val program (dynamic runs) | From program source | Does removing `retrieve_deep` cause evolution to add more retrieval hops? |
| n_tool_steps of best-by-val program (dynamic runs) | From program source | Retrieval strategy diagnostic |
| n_deep_retrieval of best-by-val program (deep runs) | From program source | How many `retrieve_deep` calls does the best chain actually use? |
| Gen-0 fitness per cell | Seed program val fitness | Quantifies the gen-0 handicap from removing deep retrieval |
| Invalidity rate at gen 5 (dynamic runs) | Fraction of invalid mutations | Detects if the mutation LLM generates `retrieve_deep` references in no-deep runs |
| Throughput (programs/hour) | Total evaluated / wall hours | Infrastructure diagnostic |

---

## Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time per run | ~20-30h (based on steady-state-v2 timings) |
| Total wall time | ~30h (8 runs in parallel) or ~60h (2 waves of 4) |
| Redis DBs | 8 (DBs 3-10) |
| Chain LLM | LiteLLM proxy (shared 8-node Qwen3-8B cluster) |
| Mutation LLM | LiteLLM proxy (Qwen3-235B servers, `llm=balanced`) |
| Test eval time | ~5 min/repeat x 5 repeats x 8 runs = ~200 min total |
| New code required | (1) `chains/hover/static_soft_no_deep/` problem variant, (2) `chains/hover/full_no_deep/` problem variant -- minimal forks of existing variants |

---

## Treatment Verification

### Observable evidence that the treatment is correctly applied

| Check | Type | Standard-only runs (R1,R2,R5,R6) | Deep runs (R3,R4,R7,R8) |
|-------|------|-----------------------------------|--------------------------|
| `problem.name` in Hydra cfg | `config_override` | `chains/hover/static_soft_no_deep` (R1,R2) or `chains/hover/full_no_deep` (R5,R6) | `chains/hover/static_soft` (R3,R4) or `chains/hover/full` (R7,R8) |
| `pipeline` in Hydra cfg | `config_override` | `standard` | `standard` |
| `retrieve_deep` in tool registry | `log_pattern_absent` / `log_pattern_present` | ABSENT -- tool not registered | PRESENT -- tool registered |
| `retrieve_deep` in elite program code | `program_structure` | ABSENT (tool does not exist; any reference causes runtime error) | May be present |
| `evolution` in Hydra cfg | `config_override` | `steady_state` | `steady_state` |
| `scheduling` in Hydra cfg | `config_override` | `lpt` | `lpt` |

### How the ablation is enforced

The retrieval ablation is enforced at two levels:

1. **Tool registry** (runtime enforcement): The no-deep validate.py constructs `tool_registry = {"retrieve": make_retrieve_fn(..., k=7)}` with no `retrieve_deep` entry. If a chain references `retrieve_deep`, the chain runner raises a KeyError, the program scores 0, and it is eliminated.

2. **Chain validation** (structural enforcement, dynamic only): `full_no_deep/config.py` sets `FULL_CHAIN_CONFIG["available_tools"] = ["retrieve"]`. `validate_chain_spec` in `full_chain` mode rejects programs with tool steps referencing tools not in `available_tools`, returning `is_valid=0` before runtime. This catches invalid programs earlier and avoids wasting chain LLM budget.

3. **Seed program** (initialization): Both no-deep seed programs use `retrieve` at Step 7 (replacing `retrieve_deep`). For static runs, tool steps are frozen, so this change persists throughout evolution. For dynamic runs, the seed establishes the initial tool vocabulary that the mutation LLM sees.

4. **Task description** (prompt-level): The `task_description.txt` for no-deep variants must NOT mention `retrieve_deep`. Only `retrieve` (k=7) is described as an available tool.

---

## Success Criteria

### Primary decision: does deep retrieval matter?

| Outcome | Interpretation | Action |
|---------|----------------|--------|
| Deep > standard by >= +4.0pp (main effect) | `retrieve_deep` is a major advantage; GEPA comparison is partially confounded | Report STRONG POSITIVE. Quantify how much of the GEPA delta is retrieval budget vs. chain optimization. Future GEPA comparisons must use k=7 only for fairness. |
| Deep > standard by [+2.0pp, +4.0pp) | `retrieve_deep` helps but is not the sole driver | Report POSITIVE. GEPA comparison is somewhat confounded. Report both k=7 and k=10 results in publications. |
| Deep > standard by (0pp, +2.0pp) | Small or no practical benefit | Report SUGGESTIVE/NULL. GEPA comparison is approximately fair. `retrieve_deep` can be dropped from future experiments for simplicity. |
| Standard >= deep | Deep retrieval provides no benefit | Report NULL. Drop `retrieve_deep` from all future experiments. Simplify tool registry. |

### Exploratory diagnostic: topology x retrieval interaction

**Note**: N=2 per cell is insufficient for a formal interaction test. The following table is an exploratory diagnostic — directional only. If strong signal is observed, a powered follow-up (N=4 per cell, 16 runs) can be designed.

| Pattern | Interpretation |
|---------|----------------|
| Deep helps static but not dynamic | Dynamic topology compensates for lower retrieval depth (adds more hops at k=7) |
| Deep helps dynamic but not static | Deep retrieval amplifies flexible topology (synergistic) |
| Deep helps both equally | Retrieval depth is orthogonal to topology (additive) |
| Deep helps neither | `retrieve_deep` is inert — drop from all conditions |

### GEPA-fair benchmark

If Cell C (dynamic + standard only) mean > 52.33%: GigaEvo adds value beyond retrieval budget. The evolutionary approach improves chain quality even at matched retrieval depth. This is the strongest fairness claim for the paper.

If Cell C mean <= 52.33%: GigaEvo's advantage over GEPA is driven entirely by the retrieval budget difference. This would be a critical finding that reframes all prior claims.

**Caveat (M2)**: GEPA's 52.33% is treated as a known constant. The one-sample test's p-value is conditional on this assumption — GEPA's own variance is unknown. Interpret the comparison as directional evidence, not a definitive superiority claim.

### Replication check (M3): Cell B vs historical baseline

Cell B (static + deep) replicates prior baseline conditions (static chain, retrieve + retrieve_deep, soft fitness). If Cell B test coverage falls outside the historical range of 51-54% (hover/baseline: 51.65%, hover/feedback_softfit: 54.37%), investigate whether the steady-state engine or infrastructure differences explain the deviation before interpreting the ablation.

---

## Risks & Mitigations

| # | Risk | Severity | Mitigation |
|---|------|----------|-----------|
| 1 | **Standard-only seed program underperforms at gen 0** -- replacing `retrieve_deep` with `retrieve` at Step 7 reduces retrieval candidates from 10 to 7 for the hardest (third) hop, lowering gen-0 fitness. | Medium | ACCEPTED. This is the ablation. Compare gen-0 fitness across conditions as a diagnostic. If the gap narrows over generations, evolution compensates for the retrieval handicap. If it widens, deep retrieval provides a compounding advantage. |
| 2 | **Dynamic standard-only chains waste budget on `retrieve_deep` references** -- the mutation LLM has seen `retrieve_deep` in training data from prior experiments and may generate programs referencing it, which fail validation. | Medium | Enforced by `FULL_CHAIN_CONFIG["available_tools"] = ["retrieve"]` in `full_no_deep`. `validate_chain_spec` rejects programs with unknown tools before runtime (returns `is_valid=0`). Monitor invalidity rate at gen 5; if > 80% of mutations are invalid in Cell C (vs. Cell D), the mutation LLM is not adapting to the restricted tool set. |
| 3 | **N=2 per cell is underpowered for the interaction test** -- the 2x2 interaction requires 4 cell means with n=2 each; the formal interaction test has essentially no power. | High | ACKNOWLEDGED. The interaction is assessed descriptively (point estimates and CIs). The primary test pools across topologies (n=4 per retrieval condition) for adequate power on the main effect. If directional signal suggests an interaction, a powered follow-up at N=4 per cell (16 runs) can be pre-committed. |
| 4 | **Shared infrastructure contention with 8 simultaneous runs** -- the LiteLLM proxy serves 8 concurrent runs, doubling the load compared to prior 4-run experiments. | Medium | Both retrieval conditions experience identical contention. Noise is symmetric. If proxy latency exceeds 2x baseline during the first hour, split into 2 balanced waves (1 run per condition per wave). |
| 5 | **Static runs with steady-state engine are novel** -- prior static experiments used the generational engine. Steady-state on static topology has not been validated. | Low | The SS engine is topology-agnostic; it manages mutation/ingestion loops regardless of chain validation mode. `static_soft` validate.py returns the same dict format. However, if Cell B (static + deep) fails to replicate prior baseline results (~51-54% test), investigate the engine-topology interaction before interpreting the ablation. |
| 6 | **`task_description.txt` mentions `retrieve_deep`** -- if the no-deep variants inherit a task description that references `retrieve_deep`, the mutation LLM will attempt to use it. | Medium | The no-deep `task_description.txt` must be reviewed and edited to remove all `retrieve_deep` references. Only `retrieve` (k=7) should be described as available. Verify during implementation. |
| 8 | **`full/validate.py` pipeline compatibility** -- verify during implementation that the full (dynamic) validate.py returns a plain dict compatible with `pipeline=standard`. If it returns a tuple (like HotpotQA ASI), a different pipeline is needed. | Medium | Check return type before launch; prior dynamic-topology experiments used `pipeline=standard` successfully. |
| 7 | **Problem variant proliferation** -- creating 2 new problem directories adds maintenance burden. | Low | Both are minimal forks: validate.py differs in 1 line (tool registry), config.py differs in 1 line (`available_tools`), seed differs in 1 word (Step 7 tool name). If k=7-only becomes the default, refactor to a config flag rather than separate directories. |

---

*Ready for Reviewer-2's scrutiny.*
