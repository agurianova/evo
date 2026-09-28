# Experimental Design: heilbron/adversarial-v2

**Date**: 2026-04-08
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Final (revised — K=1 vs K=3 bidirectional feedback, no control group)

---

## 1. Research Question

Does bidirectional structured feedback improve Constructor `actual_fitness` and reduce Improver stagnation on the Heilbronn problem? Does the amount of opponent context (K=1 vs K=3) matter?

### Motivation

In `adversarial/heilbron-prover` (PR #183), Constructors reached 97% of the Heilbronn target (min_area 0.0355 vs 0.0365). However, Improver stagnation was the primary bottleneck: P2_B had 0.0% acceptance rate for 45 generations. Currently, information flows between populations *only* through the scalar fitness signal. The mutation LLM never sees *how* opponents operate --- it sees only whether they succeeded or failed.

The literature brief identifies Feature Matching (Salimans et al., 2016) as the most actionable GAN analog: replacing a binary pass/fail signal with structured intermediate features. In our setting, the opponent's source code IS the structured critique. The LLM reads the opponent code and extracts the strategy itself --- no problem-specific parsing required.

The key insight is that a **full GAN training loop** requires information flow in **both directions**:
- **D->G (Improver->Constructor)**: The Constructor reads Improver attack strategies and evolves defenses.
- **G->D (Constructor->Improver)**: The Improver reads Constructor defense strategies and evolves targeted attacks.

This experiment assumes bidirectional feedback is the right mechanism (supported by heilbron-prover evidence and GAN theory) and explores **how much opponent context** is needed. K=3 provides a richer "minibatch" of opponent strategies but adds ~1200 tokens to prompts. K=1 provides a single exemplar with minimal context overhead (~400 tokens). The comparison reveals whether richer signal helps or whether context bloat hurts.

### GAN Analogy

| GAN concept | GigaEvo analog |
|---|---|
| Discriminator gradients -> Generator | **Direction 1**: Top-K Improver code -> Constructor mutation prompt |
| Generator outputs -> Discriminator training | **Direction 2**: Top-K Constructor code -> Improver mutation prompt |
| Minibatch size | K (opponents per direction): 1 or 3 |
| Full GAN training loop | Bidirectional feedback (both directions active in all runs) |

### Design Philosophy: Exploration over Control

The researcher's constraint is **4 runs maximum**. Rather than spending 4 runs on a treatment-vs-control comparison (which would yield N=1 per condition and no statistical power), we invest all 4 runs in **exploring the mechanism under two variations**. The implicit baseline is `adversarial/heilbron-prover` results (same problem, score-only feedback). This is a weaker comparison than a concurrent control, but acceptable because:

1. Same problem definition, same mutation LLM
2. The main confound is the steady-state engine (new) --- but it was validated as non-inferior in hover/steady-state-v2
3. N=1 treatment-vs-control would have zero replication; N=1 per K value at least lets us compare two mechanism configurations

### Design choice: Raw code vs parsed critique

The literature brief considers parsed critique (extracting strategies via a separate LLM call). This design deliberately uses **raw opponent source code**. Rationale: (1) adding a critique-parsing LLM step introduces its own failure modes (hallucination, lossy summarization), (2) raw code is problem-agnostic and generalizable, and (3) the Qwen3-235B mutation LLM is capable of reading Python code and extracting strategies. If the result is NULL, "raw code is too noisy; parsed critique would be more effective" is a plausible follow-up hypothesis.

---

## 2. Hypotheses

**H1 (Primary --- Improvement over historical baseline):**
Both K=1 and K=3 pairs achieve higher Constructor `actual_fitness` (raw min_area) than the heilbron-prover historical baseline (mean 0.03464 across pairs) by generation 75.

- **Success criterion (POSITIVE)**: Both pairs exceed the baseline by >= 0.002 (absolute min_area units).
- **Strong success (STRONG POSITIVE)**: Both pairs exceed the baseline by >= 0.005.
- **Failure criterion (NEGATIVE)**: Either pair shows actual_fitness below 0.010 at generation 75 (failure to make meaningful progress from cold start).
- **NULL criterion**: Neither pair exceeds the baseline by >= 0.002. Bidirectional feedback provides no meaningful improvement over score-only.

**H2 (Secondary --- K=3 vs K=1):**
K=3 achieves higher `actual_fitness` than K=1 (more context = better signal). Alternatively, K=1 outperforms K=3 (context bloat hurts). The direction is genuinely uncertain.

- **Measured by**: P1_A (K=3) actual_fitness vs P2_A (K=1) actual_fitness at generation 75, and trajectory shape.
- **Interpretation**: If K=3 > K=1 by >= 0.002, this is consistent with richer context helping. If K=1 > K=3 by >= 0.002, this is consistent with less being more. If |delta| < 0.002, K does not matter much. **H2 is hypothesis-generating only** and cannot support causal conclusions under any analysis, due to N=1 per K condition.

**H3 (Secondary --- Improver stagnation):**
Both pairs show reduced Improver stagnation compared to heilbron-prover. Bidirectional feedback (Direction 2: Constructor code -> Improver) gives Improvers explicit information about resistant Constructor strategies, enabling targeted attacks rather than blind exploration.

- **Success criterion**: Improver acceptance rate > 5% after gen 20 (measured over a rolling 10-generation window), compared to ~0% in heilbron-prover P2_B.
- **NULL criterion**: Both Improvers stagnate similarly to heilbron-prover. Direction 2 does not help.

---

## 3. Independent Variable(s)

| Variable | Pair 1 value | Pair 2 value |
|----------|-------------|-------------|
| K (opponents shown per direction) | **K=3** (full minibatch: 3 opponent code blocks per direction) | **K=1** (minimal context: 1 opponent code block per direction) |

Both pairs receive **bidirectional structured feedback** --- there is no score-only control. The only difference between pairs is K.

All runs use `pipeline=adversarial_coevo_feedback` (the extended pipeline with `OpponentFeedbackStage`). The pipeline is identical across all 4 runs; only K differs.

### Treatment mechanism (detailed)

The treatment modifies the `MutationContextBuilderStage` output for **both** Pop A (Constructor) and Pop B (Improver) runs. After opponent evaluation, `OpponentFeedbackStage` reads opponent programs and appends their source code to `program.metadata[MUTATION_CONTEXT_METADATA_KEY]`. The mutation LLM then sees this context when generating the next variant.

**Direction 1 (Improver -> Constructor):** The additional context block injected into Constructor mutation prompts:

```
## OPPONENT ATTACK REPORT
Your configuration was evaluated against {n} opponent Improvers.
Resistance: {resistance}% (fraction of opponents that failed to improve your configuration)

The top-{K} most effective attackers (by delta_fitness) are shown below.
Study their strategies to evolve configurations that resist these specific attacks.

### Attacker 1 (delta_fitness: {delta})
```python
{improver_source_code}
```

[... K-1 more attackers if K=3 ...]

Use this information to understand HOW opponents try to improve your configuration,
and evolve configurations that are resistant to these specific attack strategies.
```

**Direction 2 (Constructor -> Improver):** The additional context block injected into Improver mutation prompts:

```
## TARGET ANALYSIS REPORT
Your improvement strategy was tested against {n} opponent Constructors.
Success rate: {success_rate}% (fraction of Constructors you successfully improved)

The top-{K} most resistant targets (that you FAILED to crack) are shown below.
Study their construction strategies to evolve targeted attacks against these defenses.

### Target 1 (resistance: {resistance})
```python
{constructor_source_code}
```

[... K-1 more targets if K=3 ...]

Use this information to understand WHY these configurations resist improvement,
and evolve strategies that specifically target these defensive patterns.
```

**Cold-start behavior**: During the first 1-3 generations, the opponent archive may be empty. When `OpponentFeedbackStage` calls `OpponentArchiveProvider.get_opponents()` and receives an empty list (or fewer than K opponents), the stage **skips the feedback block entirely** --- no placeholder, no header. This means all runs are feedback-free during the cold-start window. The feedback becomes active once opponent archives are populated (typically by gen 2-3). This cold-start window is documented and expected; it affects all 4 runs equally and reduces the effective treatment duration by at most 2-3 generations out of 75.

### Parameters

| Parameter | Pair 1 | Pair 2 | Rationale |
|-----------|--------|--------|-----------|
| K (opponents per direction) | 3 | 1 | Tests whether richer context (minibatch) helps or hurts vs minimal exemplar. |
| Code presentation | Full source, no truncation | Full source, no truncation | Same across pairs. |
| Opponent selection (Direction 1) | Top-K by delta_fitness | Top-1 by delta_fitness | Highest-information attackers. |
| Opponent selection (Direction 2) | Top-K by resistance | Top-1 by resistance | Hardest targets. |
| Amendment pre-authorization | If K=3 mutation latency exceeds 60s mean (over a 10-generation window), drop to K=2 | N/A (K=1 is already minimal) | Documented amendment. If K is reduced, the generation at which the change occurs and the reason are logged in 04_issues_log.md. Results analysis separates pre-amendment and post-amendment windows. |

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| `actual_fitness` | Raw min_area of Constructor output, tracked per-generation in Redis metrics | **Yes** |
| `fitness` | Composite 0.5*quality + 0.5*resistance (MAP-Elites selection metric) | No (secondary) |
| `resistance` | 1 - mean(normalized improvement by opponents) | No (secondary) |
| `quality` | min(min_area / 0.0365, 1.0) | No (secondary) |
| Improver acceptance rate | Fraction of valid Improver programs accepted into archive (per generation window) | No (H3, secondary) |

**Primary metric**: `actual_fitness` (raw min_area) of Constructor runs at generation 75, compared against the heilbron-prover historical baseline (mean 0.03464).

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Bidirectional feedback | **ON** (all runs) | Both directions active in all runs; this is not an IV |
| `evolution` | `steady_state` | Steady-state engine (SteadyStateEvolutionEngine). Validated as non-inferior in hover/steady-state-v2. All runs use the same engine. |
| `max_in_flight` | 8 | Steady-state backpressure limit; same for all runs |
| `pipeline` | `adversarial_coevo_feedback` | All runs use the feedback pipeline; K is the only difference |
| `problem.name` (Pop A) | `heilbron_adversarial/pop_a` | Same Constructor problem |
| `problem.name` (Pop B) | `heilbron_adversarial/pop_b` | Same Improver problem |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` | Same mutation LLM for all runs |
| `mutation_url` | `http://10.232.30.185:4000/v1` | LiteLLM proxy, same for all |
| `num_parents` | 1 | Single-parent mutation |
| `max_elites_per_generation` | 8 | Same archive pressure |
| `max_mutations_per_generation` | 8 | Same throughput per epoch |
| `n_opponents` | 5 | Same number of opponents evaluated |
| `per_opponent_timeout` | 300 | Same timeout (from heilbron-prover) |
| `stage_timeout` | 3000 | Same stage timeout |
| `dag_timeout` | 7200 | Same DAG timeout |
| `mutation_mode` | `rewrite` | Same mutation mode |
| `max_generations` | 75 | Extended from 50 (heilbron-prover P1_A was still improving at gen 42) |
| `prompts` | `default` | Same mutation prompt template (feedback injected via metadata, not prompt template) |
| `significant_change` | 0.01 | Same archive acceptance threshold |
| Initial programs | Default `initial_programs/baseline.py` from problem directory (cold start) | Same seed program for all runs |
| `OPENAI_API_KEY` | `sk-gigaevo` | Same auth |

### Prompt parity check

The `metrics.yaml` for Pop A includes `include_in_prompts: true` for `fitness`, `is_valid`, `actual_fitness`, and `resistance`. These are identical across all 4 runs. The ONLY prompt difference is the number of opponent code blocks (K=3 vs K=1) injected via `mutation_context` metadata.

---

## 6. Run Design Table

**2x1 factorial: K=1 vs K=3 bidirectional feedback. 4 runs total.**

| Run | Label | `redis.db` | Pop | K | `opponent_redis_db` | Seed | Notes |
|-----|-------|------------|-----|---|---------------------|------|-------|
| 1 | P1_A | 1 | A (Constructor) | 3 | 2 | cold start (baseline.py) | K=3 Constructor |
| 2 | P1_B | 2 | B (Improver) | 3 | 1 | cold start (baseline.py) | K=3 Improver |
| 3 | P2_A | 3 | A (Constructor) | 1 | 4 | cold start (baseline.py) | K=1 Constructor |
| 4 | P2_B | 4 | B (Improver) | 1 | 3 | cold start (baseline.py) | K=1 Improver |

**Total: 4 runs** (2 Constructor + 2 Improver) across 4 Redis DBs (DBs 1-4).

### 6.1 Implicit baseline: heilbron-prover

There is no concurrent control group. The comparison baseline is `adversarial/heilbron-prover` (PR #183), which used the same problem and score-only feedback (also cold start):

| heilbron-prover run | Pop | actual_fitness | Notes |
|---------------------|-----|----------------|-------|
| P1_A | Constructor | 0.03380 | Last improvement gen 37, still improving at gen 42 |
| P2_A | Constructor | 0.03548 | Reached near target |
| P1_B | Improver | *from archive* | — |
| P2_B | Improver | *from archive* | 0% acceptance rate for 45 gens (severe stagnation) |

**Mean Constructor actual_fitness**: 0.03464. This is the baseline for H1.

**Acknowledged weakness**: Historical comparison is weaker than concurrent control. The main confounds are: (1) steady-state engine (new) — validated as non-inferior in hover/steady-state-v2; (2) cold start here vs cold start in heilbron-prover means both started from scratch, making the comparison cleaner. If both pairs exceed the baseline by >= 0.002, the result is informative. If only one pair exceeds, the signal is ambiguous.

### 6.2 Cold start

All 4 runs use the default `initial_programs/baseline.py` from their respective problem directories. No warm-start from prior experiments. Both pairs start from the same seed programs, eliminating seed variance as a confound for the K=1 vs K=3 comparison (H2).

### 6.3 Pipeline DAG topology

All 4 runs use the same pipeline (`adversarial_coevo_feedback`) with `OpponentFeedbackStage` active. The only parameter difference is K.

```
ValidateCodeStage
    |
    +---> CallProgramFunction ----> CallValidatorFunction(evaluate.py)
    |                                       ^
    +---> FetchOpponentResultsStage --------+
    |         (data flow: "context")
    |         |
    |         +---> OpponentFeedbackStage  (K=3 or K=1)
    |                     |
    ... (standard mutation context stages) ...
    |                     |
    v                     v
MutationContextStage  -->  (mutation prompt WITH opponent code block)
```

**OpponentFeedbackStage data flow:**

`OpponentFeedbackStage` receives the list of `OpponentProgram` objects from `FetchOpponentResultsStage` via a data flow edge. The stage selects the top-K opponents by the relevant criterion (delta_fitness for Direction 1, resistance for Direction 2) and appends their source code to `program.metadata[MUTATION_CONTEXT_METADATA_KEY]`.

The stage is **population-aware**: it reads the current population type (Pop A or Pop B) from the pipeline configuration and selects the appropriate feedback template and opponent ranking criterion:
- Pop A (Constructor): Uses "OPPONENT ATTACK REPORT" template, ranks opponents by delta_fitness (highest = most effective attacker)
- Pop B (Improver): Uses "TARGET ANALYSIS REPORT" template, ranks opponents by resistance (highest = hardest to crack)

**Implementation**: `AdversarialFeedbackPipelineBuilder` extends `AdversarialPipelineBuilder` and adds exactly one stage (`OpponentFeedbackStage`) with:
1. One data flow edge: `FetchOpponentResultsStage` -> `OpponentFeedbackStage` (opponent program data)
2. One data flow edge: `OpponentFeedbackStage` -> `MutationContextStage` (feedback metadata)
3. One execution dependency: `OpponentFeedbackStage` depends on `FetchOpponentResultsStage` success

K is configured via `pipeline.opponent_feedback_k` (Hydra override). The same pipeline YAML is used for all 4 runs; only the K parameter differs.

---

## 7. Context Budget

Bidirectional feedback adds opponent code to mutation prompts in both directions. The token cost varies by K:

| Component | K=3 (Pair 1) | K=1 (Pair 2) |
|---|---|---|
| Baseline mutation prompt (insights, lineage, metrics, archetype) | ~2000-3000 | ~2000-3000 |
| Opponent code block per direction: K opponents x ~200 tokens each | ~600 | ~200 |
| Template overhead (headers, instructions) per direction | ~100 | ~100 |
| **Extra tokens per direction** | **~700** | **~300** |
| **Extra tokens total (both directions)** | **~1400** | **~600** |
| **Total mutation prompt** | **~3400-4400** | **~2600-3600** |
| Qwen3-235B context window | 32,768 | 32,768 |

Both K values are well within the 32K context window.

**Latency impact**: K=3 adds ~7-14 seconds to mutation LLM inference (1400 extra tokens at ~100 tokens/second). K=1 adds ~3-6 seconds. Both are negligible relative to the ~600-second evaluation stage.

**Pre-authorized amendment**: If K=3 mean mutation latency exceeds 60 seconds (measured over a 10-generation window), drop from K=3 to K=2. This reduces the opponent code block while preserving a richer signal than K=1. This amendment is pre-authorized and does not require a design revision.

---

## 8. Sample Size Justification

With N=1 pair per K value, this experiment is exploratory. It measures effect magnitude against a historical baseline (heilbron-prover) and compares two mechanism configurations. There is no concurrent control and no within-condition replication.

**What we can detect**:
- **H1 (vs historical baseline)**: If both pairs exceed the baseline mean (0.03464) by >= 0.002, this is consistent evidence that bidirectional feedback helps. With N=2 data points above threshold, the probability of both exceeding by chance (assuming no effect) depends on the noise distribution, but two independent pairs both exceeding is stronger than one.
- **H2 (K=3 vs K=1)**: A single comparison with no replication. Both pairs start from the same cold-start seed, so seed variance is eliminated. We can observe the magnitude and direction of the difference, but N=1 per K condition limits causal attribution. This is exploratory and hypothesis-generating.
- **H3 (Improver stagnation)**: If both Improvers show > 5% acceptance rate where heilbron-prover P2_B showed 0%, the signal is clear.

**We acknowledge honestly**: This is a 4-run exploration, not a controlled experiment. The results will be interpreted as preliminary evidence to guide future factorial designs, not as definitive causal conclusions.

---

## 9. Statistical Test

**H1 (vs historical baseline)**:
- Per-pair delta: P1_A actual_fitness - 0.03464 and P2_A actual_fitness - 0.03464 at generation 75.
- Verdict: POSITIVE if both deltas >= 0.002; SUGGESTIVE if one delta >= 0.002 and the other >= 0; NULL if both deltas < 0.002; NEGATIVE if either pair shows actual_fitness below 0.010 at gen 75.

**H2 (K=3 vs K=1)**:
- Delta: P1_A actual_fitness - P2_A actual_fitness at generation 75.
- Interpretation: Report magnitude and direction. Both pairs share the same cold-start seed, so the comparison is direct. No statistical test at N=1. H2 is hypothesis-generating only; N=1 per K condition precludes causal attribution.

**H3 (Improver stagnation)**:
- Per-pair: Improver acceptance rate in rolling 10-generation window from gen 20 onward.
- Verdict: POSITIVE if both Improvers show > 5% acceptance rate. NULL if both stagnate. MIXED if one de-stagnates and the other does not.

---

## 10. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| No concurrent control (historical baseline only) | HIGH | Same problem, same cold start, same mutation LLM. Main confound is steady-state engine, validated as non-inferior in hover/steady-state-v2. |
| Prompt length difference between K=3 and K=1 | LOW-MEDIUM | K=3 prompts are ~800 tokens longer than K=1 per direction. If the LLM's mutation quality degrades with longer prompts (attention dilution), this biases against K=3. |
| LLM server load variance | LOW | All runs use same LiteLLM proxy. 4 runs (down from 8 in the previous design) is well within proxy capacity. |
| Stale opponent cache | LOW | `cache_ttl=30.0` in OpponentArchiveProvider means opponents refresh every 30s. All runs have the same cache TTL. |
| Cold start requires more generations to converge | LOW | 75 generations provides ample headroom. heilbron-prover reached 0.035 in 50 gens from cold start. |
| Cold-start window (no feedback for first 1-3 gens) | LOW | All 4 runs affected equally. Feedback becomes active once opponent archives populate (gen 2-3). |
| Steady-state engine vs generational engine | MEDIUM | All runs use steady-state. Comparison against heilbron-prover (generational) is confounded by engine type. Mitigated by hover/steady-state-v2 validation showing non-inferiority. |

### Residual confound: Prompt length (K=3 vs K=1)

K=3 injects ~1400 extra tokens across both populations; K=1 injects ~600. If we observe K=1 > K=3, prompt length is an alternative explanation (context bloat). If K=3 > K=1, the richer signal overcomes the length penalty, making the result stronger.

---

## 11. Stop Criteria

**Early termination (per-run)**:
- Constructor frontier best `actual_fitness` (`valid_frontier_fitness` in Redis) < 0.005 at gen 20 (cold start failed to make initial progress)
- Invalidity rate > 75% for 5 consecutive generations (evaluate.py or helper bug)
- PID dead with no generation advance for 2 hours

**Stagnation alert**: If any Constructor shows zero `actual_fitness` improvement in frontier best (`valid_frontier_fitness`) for 15 consecutive generations after gen 10, the watchdog posts a WARNING to the PR. This is an alert, not a termination --- the researcher decides whether to intervene.

**No experiment-level early stop**: Without a concurrent control arm, there is no basis for experiment-level early termination. All 4 runs proceed to generation 75.

**Run invalidation criteria**:
- Redis corruption (keys missing, duplicate program IDs)
- Wrong thinking mode on mutation LLM (verify at launch with `--cfg job`)
- Treatment verification failure: Any run's prompt dumps show NO feedback block by gen 5 (feedback mechanism not working)
- K mismatch: P1 prompts show != 3 opponent blocks, or P2 prompts show != 1 opponent block

---

## 12. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| GPU hours | ~100 hours (4 runs x 75 epochs x ~20 min/epoch, with steady-state parallelism) |
| Wall time | ~25 hours (75 epochs x ~20 min/epoch) |
| Redis DBs used | 4 (DBs 1-4) |
| Mutation LLM | Qwen3-235B via LiteLLM proxy (4 backend servers) |
| Chain LLM | None (no chain servers needed for adversarial experiments) |

Note: 4 runs (down from 8 in the previous design). Steady-state engine eliminates the generational barrier, so "generation" above means "epoch" (a batch of `max_mutations_per_generation` evaluations). Actual wall time depends on LLM throughput rather than sequential generation boundaries.

---

## 13. Treatment Verification

Since all 4 runs receive bidirectional feedback (no control arm), verification focuses on confirming feedback is active and K is correct.

### What proves the mechanism is applied?

1. **All Constructor runs** (P1_A, P2_A): The mutation prompt must contain an "OPPONENT ATTACK REPORT" section with Improver source code. Verify by:
   - Checking prompt dump files (MutationAgent dumps prompts to disk)
   - Searching for "OPPONENT ATTACK REPORT" in the prompt dump at gen 1-2
   - Confirming Improver code snippets appear (e.g., `def entrypoint(` from Improver programs)

2. **All Improver runs** (P1_B, P2_B): The mutation prompt must contain a "TARGET ANALYSIS REPORT" section with Constructor source code. Verify by:
   - Checking prompt dump files for "TARGET ANALYSIS REPORT"
   - Confirming Constructor code snippets appear

3. **K verification**: Count the number of "### Attacker" or "### Target" headers in prompt dumps:
   - P1_A and P1_B: exactly 3 opponent blocks per prompt (K=3)
   - P2_A and P2_B: exactly 1 opponent block per prompt (K=1)

### Runtime treatment verification

- **Gen 3 feedback gate**: At gen 3, the watchdog checks all 4 runs for their respective feedback headers ("OPPONENT ATTACK REPORT" for Constructors, "TARGET ANALYSIS REPORT" for Improvers). If absent, the watchdog posts a WARNING to the PR. If still absent at gen 5, the run is flagged for investigation.
- **Gen 5 K verification gate**: At gen 5, the watchdog counts opponent blocks in the most recent prompt dump for each run. P1 runs must show 3 blocks; P2 runs must show 1 block. Mismatch triggers a WARNING.

These checks are implemented in the experiment's `run_watchdog.py`.

### Preflight treatment checks

Preflight checks (`tools/experiment/preflight_check.py`) verify before launch:

1. **All 4 runs**: Config dumps show `pipeline_builder._target_` = `AdversarialFeedbackPipelineBuilder`.
2. **P1 runs**: Config dumps show `pipeline.opponent_feedback_k=3`.
3. **P2 runs**: Config dumps show `pipeline.opponent_feedback_k=1`.

### Preflight treatment checks (for experiment.yaml `treatment_checks`)

```yaml
treatment_checks:
  - type: log_pattern_present
    runs: [P1_A, P2_A]
    pattern: "OPPONENT ATTACK REPORT"
    description: "All Constructor prompts contain Improver code feedback (Direction 1)"
    gen_gate: 3
  - type: log_pattern_present
    runs: [P1_B, P2_B]
    pattern: "TARGET ANALYSIS REPORT"
    description: "All Improver prompts contain Constructor code feedback (Direction 2)"
    gen_gate: 3
  - type: config_check
    runs: [P1_A, P1_B, P2_A, P2_B]
    check: "pipeline_builder._target_ contains 'AdversarialFeedbackPipelineBuilder'"
    description: "All runs use the feedback pipeline"
  - type: opponent_count_check
    runs: [P1_A, P1_B]
    expected_k: 3
    pattern: "### (Attacker|Target) \\d+"
    description: "K=3 runs show exactly 3 opponent blocks per prompt"
    gen_gate: 5
  - type: opponent_count_check
    runs: [P2_A, P2_B]
    expected_k: 1
    pattern: "### (Attacker|Target) \\d+"
    description: "K=1 runs show exactly 1 opponent block per prompt"
    gen_gate: 5
  - type: generation_parity
    groups: [[P1_A, P1_B], [P2_A, P2_B]]
    max_drift: 5
    description: "Constructor-Improver pairs stay within 5 generations of each other"
  - type: config_check
    runs: [P1_A]
    check: "opponent_redis_db == 2"
    description: "P1_A (Constructor K=3) reads opponents from DB 2 (P1_B Improver)"
  - type: config_check
    runs: [P1_B]
    check: "opponent_redis_db == 1"
    description: "P1_B (Improver K=3) reads opponents from DB 1 (P1_A Constructor)"
  - type: config_check
    runs: [P2_A]
    check: "opponent_redis_db == 4"
    description: "P2_A (Constructor K=1) reads opponents from DB 4 (P2_B Improver)"
  - type: config_check
    runs: [P2_B]
    check: "opponent_redis_db == 3"
    description: "P2_B (Improver K=1) reads opponents from DB 3 (P2_A Constructor)"
```

---

## 14. Open Questions / Risks

### Implementation risks

1. **K parameterization**: `OpponentFeedbackStage` must accept K as a configurable parameter (not hardcoded). Implementation: `pipeline.opponent_feedback_k` Hydra override, read by the stage at initialization.

2. **Prompt token budget**: K=3 adds ~1400 extra tokens across both populations. K=1 adds ~600. Both are well within Qwen3-235B's 32K context window (Section 7). Monitor actual token counts at gen 1.

3. **4 concurrent runs**: Reduced from 8 in the previous design. The LiteLLM proxy with 4 backend servers should handle this easily.

### Scientific risks

4. **No concurrent control**: The comparison against heilbron-prover is confounded by engine type (steady-state vs generational). If results are ambiguous (one pair improves, one does not), we cannot distinguish "bidirectional feedback helps" from "steady-state engine helps on certain seeds."

5. **Cold-start convergence time**: Starting from scratch means the first 10-20 generations are spent on basic optimization before the feedback mechanism becomes meaningful (opponents must first produce non-trivial programs). This reduces the effective window for measuring feedback impact to gens ~20-75.

6. **LLM ignores opponent code**: The mutation LLM may not effectively parse and use opponent source code. If the result is NULL, "LLM ignores the feedback" is a plausible explanation, and a follow-up could test explicit archetype instructions.

7. **Stochastic cold-start divergence**: Even with identical seeds, cold-start runs diverge due to stochastic mutation. Any K=3 vs K=1 difference at gen 75 must exceed run-to-run noise. heilbron-prover within-pair variance (0.00168) provides a rough noise floor.

### Follow-up experiments (contingent on results)

- If POSITIVE on H1 (both pairs exceed baseline): Design a proper controlled experiment with K as IV and concurrent score-only control. This gives causal evidence.
- If K=3 > K=1 on H2: Test K=5 to explore whether even more context helps.
- If K=1 > K=3 on H2: Context bloat is real. Test parsed critique (summary instead of raw code) as a way to provide rich signal in fewer tokens.
- If POSITIVE on H3 (Improver de-stagnation): Bidirectional feedback breaks the stagnation bottleneck. This is the most important mechanistic finding.
- If NULL on both H1 and H3: Abandon raw-code feedback. Consider parsed critique or difficulty-calibrated opponent selection (GenEnv alpha-curriculum).
- If NEGATIVE (regression): Investigate whether the feedback destabilizes co-evolutionary dynamics. Check for mode collapse or cycling.

---

*Ready for Reviewer-2's scrutiny.*
