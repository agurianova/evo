# Experimental Design: D-Side Tanh Smoothing + LineageStage Removal from D Pipeline

**Date**: 2026-04-25
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft
**Predecessor**: `heilbron/d-smoothing-minimal` (INVALID, aborted at 15h due to D/G timing asymmetry 1.84x)
**Comparators**: `heilbron/adversarial-repro-v2` (NULL, mu_G=0.03315, PR #216), `heilbron/adversarial-repro-v1` (NULL, mu_G=0.03413, PR #211)

---

## 1. Research Question

Does removing the `SharedBenchmarkFilteredLineageStage` from D's pipeline -- on top of the D-side tanh fitness smoothing carried over from `heilbron/d-smoothing-minimal` -- lift mu_G out of the v2 NULL band (mu_G=0.03315), by eliminating D's per-generation lineage-refresh overhead that caused d-smoothing-minimal to abort after 15 hours with D at 57% of G's generation pace?

The comparison structure serves two distinct purposes -- quantitative effect-size estimation and mechanistic validity checking -- which must not be conflated:

| Comparator | Relationship | IVs that differ | Purpose |
|---|---|---|---|
| `adversarial-repro-v2` (NULL, mu_G=0.03315) | **Primary quantitative comparator** | 2 IVs: (1) D fitness function (hard-floor to tanh), (2) LineageStage presence on D | Effect-size estimation for mu_G. Both conditions have complete data. Attribution to individual IVs requires a follow-up isolating one. |
| `d-smoothing-minimal` (INVALID) | Mechanistic / validity predecessor | 1 IV: LineageStage presence on D (treatment removes it) | Binary question: does removing LineageStage prevent the timing-asymmetry abort (D/G ratio 0.57x) that killed the predecessor? Does NOT produce an effect-size estimate -- d-smoothing-minimal has no usable mu_G data point. |
| `adversarial-repro-v1` (NULL, mu_G=0.03413) | Historical no-lineage regime | Treatment shares no-lineage on D with v1, but differs in fitness function (v1 had hard-floor, treatment has tanh) and in G-side evaluate.py (v1 had binary resistance, treatment has continuous) | Historical calibration of D/G ratio under no-lineage conditions (v1: 4.00x). |

**Primary quantitative comparison** (vs v2): The effect size (delta mu_G) is measured against v2's complete data (mu_G=0.03315, D fitness distributions, arms-race trajectories). This comparison has 2 confounded IVs (tanh + no-lineage). If POSITIVE, the result is attributed to the compound treatment; decomposition requires a follow-up experiment isolating one IV. If NULL, both IVs together were insufficient.

**Mechanistic / validity comparison** (vs d-smoothing-minimal): This answers a binary question -- does removing LineageStage prevent the timing-asymmetry abort that killed d-smoothing-minimal? The d-smoothing-minimal predecessor was aborted at 15h with G gens 24--31 and D gens 14--17. It has no estimable mu_G, no D fitness distribution at gen 50, and no complete arms-race trajectory. The "comparison" is a validity-status check (did we avoid invalidation?), not an effect-size comparison. A NULL result here cannot be cleanly compared to d-smoothing-minimal's untestable outcome.

---

## 2. Hypotheses

Let **mu_G** = grand mean of best-ever `actual_fitness` across the 4 G runs (A1_G, A2_G, C1_G, C2_G).

**H0**: mu_G <= 0.03449 (baseline-repro mean). D-smoothing + D-no-lineage does not lift G above baseline parity.
**H1**: mu_G > 0.03449. D-smoothing + D-no-lineage breaks the timing asymmetry and enables meaningful G improvement.

### 2.1 Effect-Size Thresholds

| mu_G range | Verdict | Rationale |
|---|---|---|
| >= 0.03550 | **POSITIVE** | Exceeds all prior adversarial means (baseline-repro: 0.03449, v1: 0.03413, v2: 0.03315). Clear directional improvement that must-beats baseline-repro. |
| >= 0.03449, < 0.03550 | **SUGGESTIVE** | At or above baseline-repro mean but below decisive threshold. Warrants follow-up with larger N or REDESIGN bundle. |
| >= 0.03200, < 0.03449 | **NULL** | Within the band spanned by v1 (0.03413) and v2 (0.03315). D-smoothing + no-lineage is insufficient. |
| < 0.03200 | **REGRESSIVE** | Below v2's lower bound. Treatment is actively harmful. |

**Note on REGRESSIVE reachability**: The REGRESSIVE threshold (< 0.03200) falls below v2's bootstrap 95% CI lower bound (0.03001). With N=4 sampling noise at sigma~0.003, a grand mean below 0.03200 would require all 4 runs to regress simultaneously. REGRESSIVE is effectively unreachable under normal variance. The threshold is retained for completeness.

### 2.2 Treatment Verification Check (Code-Application Diagnostic)

Two code-level treatments must be verified at runtime:

**Check A -- Tanh scoring active on D (carried from d-smoothing-minimal)**:
At gen 3, the fraction of D-archive programs with fitness exactly 0.000 must be **< 5%** across all 4 D runs. Under the tanh formula, `raw_delta = 0` maps to score 0.500. The only way to get score exactly 0.000 is via `_invalid_opp_metrics()` with `is_valid=0.0`, which is gated out by the `ConfigurableAggregator` validity filter. A failure here means the tanh code is not active (stale pyc, wrong evaluate.py).

**Check B -- LineageStage absent on D (new treatment)**:
After gen 1, D run logs must NOT contain `[LineageStage:SharedBenchmark]` stage markers. G run logs MUST still contain `[LineageStage]` markers. D Redis must NOT contain `:lineage_state:` keys (or equivalent keys written by `SharedBenchmarkFilteredLineageStage`). If any D run shows LineageStage log lines, the `disable_lineage_on_improver` flag was not applied. Abort and debug.

Both checks are code-application diagnostics, not scientific predictions. Their outcomes are determined by correct deployment, not by evolutionary dynamics.

### 2.2a Pre-Registered Mechanistic Predictions

#### D Fitness Distribution Shape (carried from d-smoothing-minimal)

| Checkpoint | Prediction | Pass criteria |
|---|---|---|
| Gen 5 | D fitness fraction in [0.1, 0.9] >= 50%; median in [0.3, 0.6]; D fitness < 0.001 fraction < 20%; D fitness variance >= 0.01 | >= 3 of 4 D runs |
| Gen 20 | D fitness fraction in [0.1, 0.9] >= 50%; median >= 0.45; no single histogram bin > 40% of mass | >= 3 of 4 D runs |

#### D/G Gen-Pace Ratio (PRIMARY new prediction)

This is the primary mechanistic check for this experiment. The d-smoothing-minimal failure was D at 57% of G's pace (ratio 0.57x, equivalently D was 1.84x slower). Removing LineageStage eliminates the per-mutation LLM lineage-narrative call and the two-pass refresh overhead for `SharedBenchmarkFilteredLineageStage`. However, d-smoothing-minimal's 1.84x slowdown had two contributors: (1) intrinsic D evaluation cost (Improver runs optimization-style improvement per opponent; Constructor just emits 11 points -- structural, permanent) and (2) LineageStage overhead (eliminable). The fraction attributable to each is unknown. If LineageStage contributed 60% of the overhead, removing it recovers the ratio to ~1.4x. If it contributed only 30%, the ratio recovers to ~0.8x -- a substantial improvement (40% faster D) that nonetheless leaves D somewhat behind G.

**Graded D/G gen-pace ratio gate at gen 5** (checked across all 4 pairs):

| Zone | Ratio range | Criterion | Action |
|---|---|---|---|
| **Green (PASS)** | >= 0.90 across >= 3 of 4 pairs | Treatment is mechanistically active and time-symmetric. D can keep pace with G. | Continue. No amendment needed. |
| **Yellow (CONTINUE WITH AMENDMENT)** | [0.70, 0.90) across >= 3 of 4 pairs | Treatment partially recovered timing. D is still behind G but dramatically improved from d-smoothing-minimal's 0.57x. | Continue, but record an amendment in `04_issues_log.md` at first observation. Scientific interpretation of mu_G is conditional on the residual timing gap: a NULL verdict cannot be cleanly attributed to "tanh + no-lineage is insufficient" because D's slower pace may have prevented full D evolutionary pressure. |
| **Red (ABORT)** | < 0.70 across >= 3 of 4 pairs | Removing LineageStage was not enough; intrinsic Improver evaluation cost is the binding constraint. A ratio below 0.70 represents only ~24% improvement over d-smoothing-minimal's 0.57x -- insufficient structural recovery. | Transition `running -> invalid`. A different timing fix is needed (Option A lockstep, Option C parallelism, Option E per-pop stoppers per the d-smoothing-minimal issues log). |

**Justification for 0.70 cutoff**: d-smoothing-minimal's actual ratio was 0.54x (inverted from its reported 1.84x slowdown). A ratio of 0.70 represents a ~29% improvement over 0.54x. While not negligible, 0.70 leaves D structurally unable to keep up with G -- at gen 50, D would be at gen ~35, creating a 30% generation deficit that undermines adversarial pressure quality. The 0.90 green threshold is justified by v2's own precedent: v2's C2 pair had a D/G ratio of 0.80x and v2 was not invalidated, but v2 was also NULL. We set the green threshold at 0.90 rather than 0.80 to be more demanding than the NULL-producing v2 regime.

**Historical reference**: adversarial-repro-v1 (no-lineage, hard-floor fitness) had D/G ratio of 4.00x (range 2.28x--6.66x). adversarial-repro-v2 (lineage ON) had D/G ratio of 1.29x (range 0.80x--1.65x). With lineage removed, we expect the ratio to trend back toward the v1-era range (2x--4x), though the tanh evaluation adds trivial O(1) overhead.

**What would be SURPRISING**: A ratio below 1.5x at gen 5 would suggest that intrinsic D evaluation cost is the dominant bottleneck and that LineageStage removal alone is insufficient to restore v1-era D compute advantage. This would not trigger abort (unless < 0.70) but would significantly weaken the mechanistic story that LineageStage was the primary timing culprit.

#### D Archive Size

D archive size at gen 10 should be similar to or smaller than v2's archive (v2 D archives ranged 171--194 programs at ~gen 15). With no archive refresh churn from LineageStage, the archive should not be inflated by refresh-driven reprocessing.

### 2.3 Abandon Direction

If the treatment verification checks pass (Section 2.2: tanh active, lineage absent) AND the D/G gen-pace ratio is in the Green zone (>= 0.90, Section 2.2a: timing fixed) AND the mechanistic prediction passes (D fitness non-degenerate) AND mu_G remains NULL (< 0.03449), then D-smoothing + no-lineage is insufficient despite fixing both the fitness signal and the timing asymmetry. The binding constraint is elsewhere. Next step: proceed to `adversarial_015` (full REDESIGN bundle: deterministic HoF + K=L=3 + cache_on edges).

If D/G gen-pace ratio falls in the Yellow zone ([0.70, 0.90), Section 2.2a), the experiment continues with an amendment. A NULL verdict under Yellow-zone timing carries a caveat: the residual timing gap may have prevented full D evolutionary pressure, so "insufficient" cannot be cleanly concluded. A POSITIVE verdict under Yellow-zone timing is still informative (the compound treatment lifts mu_G even without full timing parity).

If D/G gen-pace ratio falls in the Red zone (< 0.70, Section 2.2a), the experiment transitions to `running -> invalid`. Removing LineageStage was not enough; intrinsic Improver evaluation cost is the binding constraint and a different timing solution is needed (Option A lockstep, Option C parallelism, Option E per-pop stoppers per the d-smoothing-minimal issues log).

---

## 3. Independent Variables

**Compound treatment vs adversarial-repro-v2**: 2 IVs (D fitness function form + LineageStage presence on D).
**Single treatment vs d-smoothing-minimal**: 1 IV (LineageStage presence on D).

### IV 1: D-Side Fitness Function Form (carried from d-smoothing-minimal)

| Parameter | v2 (comparator) | Treatment |
|---|---|---|
| D scoring formula (`pop_b/evaluate.py`) | `delta = max(raw_delta, 0.0); score = min(delta / Q_MAX, 1.0)` | `score = 0.5 * (np.tanh(raw_delta / Q_MAX) + 1.0)` |
| D exception-path score | `score = 0.0` | `score = 0.5` (neutral, consistent with tanh(0)) |
| D per_opp_metrics `delta` field | Stores `max(raw_delta, 0.0)` (clamped) | Stores `raw_delta` (signed, unclamped) |

This IV is byte-for-byte identical to d-smoothing-minimal's treatment. The `pop_b/evaluate.py` change is carried forward without modification.

**Note: metrics.yaml fitness description is NOT changed** (see Section 5, controlled variables). The v2 wording (`"...Worsening counts as 0, not negative."`) is preserved verbatim to avoid changing the mutation prompt content. The description is technically inaccurate under tanh scoring, but keeping it identical preserves prompt content parity (Volkov C1 from d-smoothing-minimal review).

### IV 2: LineageStage Presence on D (new)

| Parameter | d-smoothing-minimal / v2 | Treatment |
|---|---|---|
| D pipeline stages | `SharedBenchmarkFilteredLineageStage` + `LineagesToDescendants` + `LineagesFromAncestors` present | All three stages removed via `PipelineBuilder.remove_stage()` |
| D mutation context lineage fields | `lineage_ancestors` and `lineage_descendants` populated by lineage stages | `lineage_ancestors = None`, `lineage_descendants = None` (MutationContextStage silently skips `FamilyTreeMutationContext` when both are None) |
| G pipeline stages | Base `LineageStage` + `LineagesToDescendants` + `LineagesFromAncestors` present | **UNCHANGED** -- G keeps all lineage stages |

**Implementation mechanism**: A new boolean kwarg `disable_lineage_on_improver: bool = False` is added to `AdversarialAsymmetricPipelineBuilder.__init__` (`gigaevo/adversarial/asymmetric_pipeline.py`). When `True` and `population_role == "improver"`, the builder calls `remove_stage("LineageStage")`, `remove_stage("LineagesToDescendants")`, `remove_stage("LineagesFromAncestors")` before the existing `_replace_lineage_with_filtered()` block. This short-circuits the entire D-side lineage wiring.

**Feasibility**: GREEN per codebase_map.md. `PipelineBuilder.remove_stage()` is already implemented (cascades edge/dep removal). `MutationContextStage` declares lineage inputs as `Optional[TransitionAnalysisList]` and is null-safe. The `_wire_cache_on_edges()` method guards `if "LineageStage" in self._nodes` -- safe after removal. Total change: ~10--15 LOC in one file.

**Hydra override on D runs**: `pipeline_builder.disable_lineage_on_improver=true` in each D run's `extra_overrides`. G runs omit this override (Python default `False` applies).

### 3.1 Controlled-Variable Adjustments Triggered by IV 2 (NOT Independent Variables)

The removal of LineageStage changes the effective behavior of two v2-era per-role configs. `archive_reeval=true` stays at its v2 value (load-bearing under no-lineage, see below). `refresh_passes=2` is set to `1` because its sole consumer is removed (verified by grep + code reading); leaving it at `2` would cost O(archive_size) per epoch in DAG-runner bookkeeping with zero behavioural payoff. Both adjustments are **derived consequences of IV 2** -- they are not additional IVs because the v2 vs this-experiment behavioural delta is fully accounted for by the lineage removal.

**`archive_reeval=true` on D (v2 value, kept, load-bearing)**:
v2's D runs had `pipeline_builder.archive_reeval=true` with `engine_config.refresh_order=generation_bucketed` and `engine_config.refresh_passes=2`. This experiment keeps all three values identical to v2.

**Cache-semantics note (the flag is named backwards).** Per `gigaevo/adversarial/pipeline.py:204-205` and `gigaevo/adversarial/stages.py:131-159`, `archive_reeval=true` selects `InputHashCache` (cached evaluator: re-runs only when opponent IDs change), while `archive_reeval=false` selects `NO_CACHE` (always re-runs). Read the flag as "let the input-hash cache decide", not "always re-evaluate". With `archive_reeval=true`, the cache key includes the opponent-config IDs, so when the top-1 G HoF flips the D evaluator cache-misses on every archive program and the per-opponent metrics (`mean_post_quality`, `max_post_quality`, `mean_improvement_raw`, etc.) are recomputed against the new G frontier. This is the load-bearing path that keeps D's archive scores fresh as G advances -- and it is **independent of `LineageStage`**: cache invalidation lives on the evaluator, not on lineage.

This is the conservative choice. Setting `archive_reeval=false` on D would force NO_CACHE re-evaluation every epoch (more expensive, not less), and would also be a 3rd IV vs v2. Since v2's D runs had `archive_reeval=true`, keeping it `true` ensures (1) the only differences between this experiment and d-smoothing-minimal are LineageStage removal and the tanh treatment, and (2) D's archive remains responsive to G's evolving frontier via opponent-ID-keyed cache invalidation. We accept that retaining `archive_reeval=true` on D leaves D below v1's 4.0x D/G ratio (v1 ran under `archive_reeval=false` -- and per the cache-semantics note above, that meant *more* eval work per epoch, not less, so the 4.0x ratio came from v1's lack of lineage, not from skipping the cache). If D/G ratio is >= 0.90 but substantially below 4.0x, the toggle to `archive_reeval=false` is a candidate IV for a follow-up.

**`refresh_passes=2 → 1` on D (CHANGED from v2)**:
Per `gigaevo/evolution/engine/steady_state.py:780-900` and `gigaevo/adversarial/shared_benchmark_lineage.py:60-159`, the two-pass mechanism's sole purpose is to invalidate `SharedBenchmarkFilteredLineageStage` between passes. The engine bumps an `EngineSnapshot.refresh_pass` counter via `_write_snapshot` before each pass; only stages whose `compute_hash` reads that counter cache-invalidate. **A `grep -rn "refresh_pass" gigaevo/`** confirms only `SharedBenchmarkFilteredLineageStage.compute_hash` reads the counter -- no other stage in the codebase keys on it.

With `LineageStage` removed on D (IV 2), the pass-2 consumer is removed. Tracing the D pipeline DAG (`FetchOpponentIds → FetchOpponentResults → CallValidatorFunction → DGTrackerStage → InsightsStage → MutationContextStage`, plus `LineagesFromAncestors`/`LineagesToDescendants` removed) and each stage's cache mode:

| Stage | Cache mode | Pass-2 behaviour with no-lineage |
|---|---|---|
| `FetchOpponentIdsStage` | `NO_CACHE` | Re-samples; D's `top_k` is deterministic so IDs identical to pass 1 |
| `FetchOpponentResultsStage` | `InputHashCache` (when `archive_reeval=true`) | Cache hit (same IDs as pass 1) -- skipped |
| `CallValidatorFunction` | `InputHashCache` | Cache hit (same inputs) -- skipped, no improver re-execution |
| `InsightsStage` | `InputHashCache` + `cache_on=FetchOpponentIdsStage` | Cache hit (same `cache_on` value) -- skipped, **no LLM call** |
| `DGTrackerStage` | `NO_CACHE` | Re-runs (idempotent ZADD GT, cheap Redis) |
| `MutationContextStage` | `NO_CACHE` | Re-runs (re-formats from same inputs, cheap CPU) |

Pass 2 with no-lineage is therefore a no-op of meaningful work: only `DGTrackerStage` (idempotent) and `MutationContextStage` (cheap, deterministic re-format) actually do anything, and what they do is identical to what they already did in pass 1. The DAG-runner overhead per archive-program flip × 170-190 D archive programs × per-epoch is a non-trivial scheduling cost that buys zero behavioural change.

**The load-bearing archive-freshness mechanism is in pass 1, not pass 2.** When the paired G archive's top-1 HoF flips, `FetchOpponentIdsStage` produces a different ID set on the D archive program's pass-1 re-run. That:
- invalidates `FetchOpponentResultsStage`'s cache (opponent ID hash changes)
- cascades to `CallValidatorFunction` cache miss → improver re-executes against new opponents → new fitness/per-opp metrics
- cascades to `InsightsStage` cache miss via `cache_on` → **LLM-bearing per-program insights re-run** (this is the load-bearing path that keeps D adversarially responsive to G's evolving frontier)

All of this fires in pass 1. Pass 2 has nothing left to invalidate. Setting `refresh_passes=1` is strictly safer + cheaper with no behavioural change.

**Summary**:
- `archive_reeval=true` (kept at v2 value, load-bearing): drives `FetchOpponentResultsStage`'s `InputHashCache` and downstream cache-miss cascade when G HoF flips, including `InsightsStage` LLM re-evaluation. **Independent of `LineageStage`.**
- `refresh_passes=1` (changed from v2's `2`): the lone consumer of pass 2 (`SharedBenchmarkFilteredLineageStage`) is removed by IV 2; pass 2 reduces to vestigial bookkeeping. Drop it.

The mechanism that lifts D's per-gen wall time is, in order of magnitude: (1) elimination of the per-program lineage LLM call on every DAG run (the dominant v2 cost), (2) elimination of pass-2's redundant DAG sweep over the archive. Both are derived consequences of IV 2.

### 3.2 Design Decision: Compound Treatment vs v2

This experiment tests two IVs simultaneously vs v2 (tanh + no-lineage). This is defended by three observations:

1. **d-smoothing-minimal aborted on infrastructure, not on hypothesis.** The predecessor tested tanh-only (with lineage) and was invalidated due to D/G timing asymmetry -- a compute problem, not a fitness-signal problem. The timing issue is caused by lineage overhead. We cannot decompose the two IVs because the lineage overhead prevents the tanh treatment from being evaluated.

2. **The no-lineage axis was tested in v1.** adversarial-repro-v1 ran no-lineage (implicitly) with hard-floor fitness. D/G ratio was 4.00x, mu_G=0.03413. Historical evidence that no-lineage enables D compute advantage.

3. **Adding a lineage-ON control arm would split N=4 across 2 arms.** At N=2 per arm, power drops below any useful threshold.

**Attribution limitation**: If POSITIVE, the result is attributed to (tanh + no-lineage) jointly. Follow-on ablation can decompose if needed.

---

## 4. Dependent Variables

| Metric | How measured | Primary? | Direction |
|---|---|---|---|
| `actual_fitness` (best-ever per G run) | `max(post_q)` from Constructor evaluation via `pop_a/evaluate.py` | **Yes** | Higher is better |
| D/G gen-pace ratio at gen 5 | Engine generation counters per run at wall-clock gen-5 mark | **Mechanistic (primary)** | Graded: Green >= 0.90; Yellow [0.70, 0.90); Red < 0.70 |
| D fitness distribution shape | Fraction in [0.1, 0.9], variance, median at gen 5/20 | **Mechanistic (secondary)** | Non-degenerate is better |
| D point-mass fraction at gen 3 | Fraction of D-archive with fitness < 0.001 | **Treatment verification** | < 5% = PASS |
| D mean engine fitness | Mean `fitness` across D-archive at closeout | Secondary | Higher is better |
| G invalidity rate | Invalid / Total programs per G run | Secondary (diagnostic) | Compare to v2 (35--47%) |
| D invalidity rate | Invalid / Total programs per D run | Secondary (diagnostic) | Compare to v2 (10--17%) |
| D exception rate | Exceptions / Total evaluations per D run | Secondary (diagnostic) | Monitor for inflation from score=0.5 exception path |

**Primary metric**: mu_G = grand mean of best-ever `actual_fitness` across 4 G runs. This is the identical metric used in v2 and all prior heilbron adversarial experiments. The G-side evaluation is completely unchanged -- `pop_a/evaluate.py` at main HEAD (PR #219, continuous resistance).

---

## 5. Controlled Variables

All of v2's pinned configuration is preserved identically. The changes are ONLY (1) D evaluate.py formula and (2) `disable_lineage_on_improver=true` on D runs.

| Parameter | Value | Source |
|---|---|---|
| `pipeline` | `heilbron_repro_v1` | Frozen v1 pipeline; shared across all runs |
| `num_parents` | 1 | No crossover |
| `max_elites_per_generation` | 8 | v2 pinned |
| `max_mutations_per_generation` | 8 | v2 pinned |
| `inner_iterations` | 1 | v2 pinned |
| `n_opponents` | 1 | K=1 opponent context |
| `source_prompt_k` | 1 | L=1 source prompt |
| `mutation_mode` | rewrite | v2 pinned |
| `pre_step_hook.drift_cap` | 100000 | Effectively no-op; preserves v2's loose coupling |
| `pre_step_hook.sync_every_n_epochs` | 1 | v2 pinned |
| `max_generations` | 200 | Same target as v2 |
| `stage_timeout` | 900 | 15 min; matches v2's actual launch.sh values (see d-smoothing-minimal Section 5 note on v2's manifest vs launch discrepancy) |
| `dag_timeout` | 3600 | 60 min; matches v2's actual launch.sh values |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` via LiteLLM 10.232.30.185:4000 | Same mutation LLM |
| `pipeline_builder.lineage_filter.min_shared` | 1 | SBF-Lineage filter config (v2 pinned). Config still passed but LineageStage absent on D; unused on G (base `LineageStage`). |
| `pipeline_builder.lineage_filter.inject_shared_evidence` | true | Same as above. |
| `stopper` | `max_generations` | No early-stop per run |
| `evolution` | `steady_state` | |
| Git commit for `pop_a/evaluate.py` | `2de8267e` (PR #219) or later on main | G-side continuous resistance; same as d-smoothing-minimal |
| `pop_b/metrics.yaml` fitness description | `"MAP-Elites selection signal: mean over opponent configs of min(improvement / 0.0365, 1). Worsening counts as 0, not negative."` | **Frozen identical to v2** -- technically inaccurate under tanh but preserves prompt content parity (Volkov C1). |
| `pop_b/metrics.yaml` all other fields | Identical to v2 except `mean_improvement_raw.lower_bound` (changed from `0.0` to `-0.0365`; `include_in_prompts: false`, no prompt confound) | |

### 5a. Per-Role Asymmetric Config

Inherited verbatim from v2 with one addition (`disable_lineage_on_improver`):

| Parameter | G runs (constructor) | D runs (improver) | Rationale |
|---|---|---|---|
| `opponent_sampling_mode` | `softmax` | `top_k` | G: broad stochastic exposure. D: deterministic sampling. Inherited from v2. |
| `pipeline_builder.archive_reeval` | `false` | `true` | D re-scores on opponent_ids change. G: stochastic IDs shift each gen. **Kept identical to v2.** See Section 3.1 for derived-consequence analysis. |
| `engine_config.refresh_order` | `fifo` (default) | `generation_bucketed` | D-only fix for cross-program tracker race. **Kept identical to v2.** |
| `engine_config.refresh_passes` | `1` (default) | **`1`** (CHANGED from v2's `2`) | D-only: v2 used `2` to invalidate `SharedBenchmarkFilteredLineageStage` via the `refresh_pass` counter. **Only `SharedBenchmarkFilteredLineageStage` reads that counter** (verified via grep across `gigaevo/`). With LineageStage absent on D, pass 2 has no LLM consumer for the bump and becomes O(archive_size) no-op bookkeeping. Set to `1`. The load-bearing archive-freshness path -- `InsightsStage` cache_on `FetchOpponentIdsStage` + `archive_reeval=true` evaluator cache -- already fires in pass 1 when opponent IDs change. See Section 3.1. |
| `opponent_result_mode` | `exec` | `cached` | G runs D improvers; D reads G's stored output. Inherited from v2. |
| `population_role` | `constructor` | `improver` | Inherited from v2. |
| Effective LineageStage | Base `LineageStage` (unfiltered) | **ABSENT** (removed by `disable_lineage_on_improver=true`) | **NEW vs v2**: v2 had `SharedBenchmarkFilteredLineageStage` on D. This experiment removes it entirely. |
| `pipeline_builder.disable_lineage_on_improver` | `false` (default, omitted) | `true` | **NEW**: D runs add this override; G runs do not. |

---

## 6. Run Design

8 runs (2 arms x 2 pairs x G/D), identical structure to v2 and d-smoothing-minimal.

| Label | Role | Arm | DB | Pair-opponent DB | Feedback mode |
|---|---|---|---|---|---|
| A1_G | constructor | Composition | 1 | 2 | composition |
| A1_D | improver | Composition | 2 | 1 | composition |
| A2_G | constructor | Composition | 3 | 4 | composition |
| A2_D | improver | Composition | 4 | 3 | composition |
| C1_G | constructor | Gradient-in-prompt | 5 | 6 | gradient_in_prompt |
| C1_D | improver | Gradient-in-prompt | 6 | 5 | gradient_in_prompt |
| C2_G | constructor | Gradient-in-prompt | 7 | 8 | gradient_in_prompt |
| C2_D | improver | Gradient-in-prompt | 8 | 7 | gradient_in_prompt |

The 2-arm structure (Composition vs Gradient-in-prompt) is a calibration axis (feedback mode confirmed NULL, PATTERNS.md: "Direction CLOSED"). Cross-arm delta should be < 0.002; if > 0.005, flag as anomalous.

### 6.1 Extra Overrides per Run

**G runs** (A1_G, A2_G, C1_G, C2_G) -- identical to v2:
```yaml
- aggregator=heilbron_constructor
- evolution=steady_state
- stopper=max_generations
- opponent_redis_db=<paired D db>
- opponent_redis_prefix=heilbron_repro_v1/pop_b
- feedback_mode=<composition|gradient_in_prompt>
- population_role=constructor
- post_step_hook=\${composition_injection_hook}  # (Composition arm only)
- opponent_result_mode=exec
- opponent_sampling_mode=softmax
- pipeline_builder.archive_reeval=false
- pipeline_builder.per_opponent_timeout=\${stage_timeout}
```

**D runs** (A1_D, A2_D, C1_D, C2_D) -- v2 overrides + `disable_lineage_on_improver`:
```yaml
- aggregator=heilbron_improver
- evolution=steady_state
- stopper=max_generations
- opponent_redis_db=<paired G db>
- opponent_redis_prefix=heilbron_repro_v1/pop_a
- feedback_mode=<composition|gradient_in_prompt>
- population_role=improver
- opponent_result_mode=cached
- opponent_sampling_mode=top_k
- pipeline_builder.archive_reeval=true
- engine_config.refresh_order=generation_bucketed
- engine_config.refresh_passes=1   # CHANGED from v2 (was 2): pass-2 consumer (SharedBenchmarkFilteredLineageStage) removed by disable_lineage_on_improver -> pass-2 becomes O(archive_size) no-op of meaningful work
- pipeline_builder.disable_lineage_on_improver=true   # NEW
```

---

## 7. Sample Size and Power

**N=4 G runs** for the primary metric (same as v1, v2, d-smoothing-minimal, baseline-repro). This is the established heilbron adversarial budget.

With N=4 and estimated sigma=0.003 (from v2's SD=0.00295), a one-sided comparison against v2's mu=0.03315 has approximately:

- **~80% power** for a raw delta of 0.005 (mu_G = 0.0382) -- large effect, near POSITIVE (strong) territory
- **~50% power** for a raw delta of 0.003 (mu_G = 0.0362) -- moderate effect, near POSITIVE threshold
- **~30% power** for a raw delta of 0.00134 (mu_G = 0.03449) -- small effect at SUGGESTIVE threshold

With N=4, this experiment is systematically underpowered for the SUGGESTIVE threshold (~30% power). This is the accepted GigaEvo N=4 tradeoff (PATTERNS.md: "Protocol Gap: N=2-4 systematically underpowered -- ACCEPTED, acknowledge honestly"). Results will be reported as effect magnitude and 95% CI width, not as binary hypothesis tests. The bootstrap 95% CI is the primary honest output.

---

## 8. Statistical Test

**Primary**: Bootstrap 95% CI (B=10000) on mu_G (best-ever actual_fitness across 4 G runs). Verdict derived from effect-size thresholds (Section 2.1), not p-value.

**Secondary**: Welch's t-test, one-sided, comparing against v2 historical mu_G=0.03315 (N=4). Report effect size (raw delta) + 95% CI.

**Mechanistic**: D/G gen-pace ratio at gen 5 (graded outcome: >= 0.90 across 3+ pairs = Green/PASS; [0.70, 0.90) across 3+ pairs = Yellow/CONTINUE WITH AMENDMENT; < 0.70 across 3+ pairs = Red/ABORT -> `running -> invalid`). See Section 2.2a for zone definitions and justification.

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|---|---|---|
| 1 | **Compound treatment vs v2** (tanh + no-lineage): cannot attribute a POSITIVE to either IV alone. | **MODERATE** -- limits scientific attribution. | Defended in Section 3.2: d-smoothing-minimal was invalidated by timing (a lineage overhead problem), so the two IVs are mechanistically entangled. If POSITIVE, attribute to the compound. If NULL, both IVs together were insufficient. Follow-up ablation can decompose if needed. |
| 2 | **G-side code differs from v2**: v2 ran under binary `float(delta<=0)` G resistance; this experiment runs under PR #219's continuous `1.0 - min(delta/Q_MAX, 1.0)`. | **MODERATE** -- the G-side change could independently affect mu_G. | G change landed as hotfix on main; reverting creates branch divergence. G-side code is identical to d-smoothing-minimal (preserving 1-IV relationship). A POSITIVE result is "D-smoothing + D-no-lineage + G-smoothing together lift mu_G" -- the dual-smoothed result we need. |
| 3 | **Library drift from v2 and d-smoothing-minimal**: Several merges between v2's launch commit (`532ac3e5`) and current HEAD. The `disable_lineage_on_improver` code change is the only new library modification. | **LOW** -- symmetric across all 8 runs; cannot explain between-run variance. | `environment_freeze.txt` captures exact commit. The only functional library change is the `disable_lineage_on_improver` kwarg in `asymmetric_pipeline.py`, which defaults to `False` and only activates when explicitly overridden. |
| 4 | **Redis state carry-over** from d-smoothing-minimal or v2. | **LOW** -- standard mitigation. | Flush DBs 1--8 via `gigaevo flush --db N --confirm` before launch. Startup assertion: if DB is non-empty, abort. |
| 5 | **Multi-pass refresh overhead** | **NONE** -- mitigation pre-applied. | `refresh_passes` set to `1` on D (down from v2's `2`). Verified: only `SharedBenchmarkFilteredLineageStage` reads the `refresh_pass` counter, and that stage is removed by IV 2. Pass 2 had no LLM consumer to invalidate, so dropping it has zero behavioural impact. Eliminates O(archive_size) per-epoch DAG-runner bookkeeping. See Section 3.1. |
| 6 | **Historical comparator, not concurrent control**: v2 data (mu_G=0.03315) is the control, not a simultaneously-run control arm. | **LOW** -- v2 ran 3 days ago on the same server, same model, same proxy. | Same justification as d-smoothing-minimal: the concurrent-control alternative would double compute cost (16 runs) to replicate an already-characterized NULL result. |
| 7 | **`archive_reeval` and `refresh_passes` adjustments on D** triggered by LineageStage removal (Section 3.1). `archive_reeval=true` kept at v2 value (load-bearing: drives `InsightsStage` LLM re-eval on opponent-ID change via cache_on edge); `refresh_passes` reduced from v2's `2` to `1` (its sole consumer `SharedBenchmarkFilteredLineageStage` is removed by IV 2, verified by grep). | **LOW** -- both are derived consequences of IV 2, not independent variables. The behaviour delta vs v2 is fully accounted for by lineage removal. | Documented in Section 3.1 with stage-level cache-mode trace. `archive_reeval=true` value is byte-identical to v2; `refresh_passes=1` is the only value that produces no behavioural change vs `2` (pass 2 was already a no-op after IV 2). The DAG re-evaluation that keeps D archive responsive to G's evolving frontier (opponent-ID-keyed cache invalidation cascade through `FetchOpponentResultsStage` → `CallValidatorFunction` → `InsightsStage`) all fires in pass 1. |
| 8 | **Exception-path incentive change on D** (score 0.0 -> 0.5 weakens crash penalty). | **LOW** -- integral part of IV 1 (tanh treatment), not independent. | D exception rate is monitored as a secondary diagnostic. If exception rate exceeds 20% on any D run, flag for investigation. Same as d-smoothing-minimal Confound m1. |

### 9.1 Volkov-Targeted Preempts

**Preempt: "Compound treatment vs v2 -- why not decompose?"**
Decomposition requires a lineage-ON arm with working timing. d-smoothing-minimal was that arm and it was invalidated by timing. The ONLY way to get a lineage-ON + tanh + working-timing arm is to fix the timing without removing lineage (Options A/C/F from the d-smoothing-minimal issues log). Each of those options is itself a separate intervention with its own confounds. Running this experiment first is the minimum-cost path to an informative result: if POSITIVE, the compound works; if NULL, we know tanh + no-lineage is insufficient even with good timing.

**Preempt: "Hidden IV on `archive_reeval` and `refresh_passes`."**
`archive_reeval=true` kept at v2 value (byte-identical). The flag is named backwards: it selects `InputHashCache` (cache, invalidate on opponent-ID change), not "always re-evaluate" (verified at `gigaevo/adversarial/pipeline.py:204-205`, `gigaevo/adversarial/stages.py:131-159`). The cache lives on `FetchOpponentResultsStage` and cascades misses to `CallValidatorFunction` and `InsightsStage` (`cache_on=FetchOpponentIdsStage`, `asymmetric_pipeline.py:309-312`). This is the load-bearing archive-freshness path -- **independent of `LineageStage`**.

`refresh_passes` set to `1` (down from v2's `2`). Verified by `grep -rn "refresh_pass" gigaevo/`: only `SharedBenchmarkFilteredLineageStage.compute_hash` reads the `EngineSnapshot.refresh_pass` counter (`shared_benchmark_lineage.py:88-98`). With LineageStage removed by IV 2, pass 2 has no consumer for the counter bump and reduces to: `FetchOpponentIdsStage` re-sample (deterministic top_k -> same IDs) → all cache-keyed stages cache-hit → only `DGTrackerStage` (idempotent) and `MutationContextStage` (cheap) actually do work. Pass 2's behavioural delta is zero; its bookkeeping cost is O(archive_size) per epoch. Setting `refresh_passes=1` eliminates the cost while preserving identical behaviour. This is **strictly safer + cheaper than `2`** under no-lineage; it is not an independent IV because the lineage-driven re-runs (which `2` was designed to enable) are gone. See Section 3.1 for the per-stage cache-mode table.

**Preempt: "Power at N=4 is ~30% for the SUGGESTIVE threshold."**
Acknowledged. This is the standard GigaEvo N=4 tradeoff. The 95% CI is the honest primary output. If the point estimate is SUGGESTIVE but the CI spans NULL, the verdict is SUGGESTIVE with a noted CI caveat. Formal statistical testing would require N >= 12 runs per condition (Section 7).

---

## 10. Stop Criteria

**Per-run stop**: `stopper=max_generations`, `max_generations=200`. No programmatic early-stop.

**D/G gen-pace ratio gate (gen 5, PRIMARY)**: At gen 5 for each pair, compute D_gen/G_gen. Graded outcome per Section 2.2a: Green (>= 0.90 across 3+ pairs: continue), Yellow ([0.70, 0.90) across 3+ pairs: continue with amendment in `04_issues_log.md`), Red (< 0.70 across 3+ pairs: transition `running -> invalid`). This gate is checked by the researcher or watchdog at the gen-5 checkpoint, not automated.

**Experiment-level abort**: If 4+ of 8 processes die within first 2 hours, or if watchdog detects `invalidity_rate > 0.75` AND `stagnation_window > 15` on >= 2 G runs simultaneously.

**Wall-clock cap**: 28 hours hard cap (same as v2 and d-smoothing-minimal). With D running faster (no-lineage), we expect deeper generation penetration than d-smoothing-minimal's aborted 14--31 gens. G per-gen pace was ~33 min in d-smoothing-minimal (G pipeline is unchanged), so G reaches gen 50 at ~27.5h and gen ~51 at 28h. If D/G ratio returns to v1-era 2x--4x, G becomes the wall-clock bottleneck and D may reach gen 100--200+ within 28h. The mechanistic prediction checkpoints (gen 5, 20) are comfortably reachable. Gen 50 D histogram checkpoint is contingent on D reaching gen 50, which is expected within 28h even in the Yellow-zone scenario (D at 0.7--0.9x G pace would reach gen ~35--45 by 28h).

**Any early termination must be recorded as an amendment in `03_plan.md` BEFORE results analysis** (protocol lesson from v2 Deviation 2).

---

## 11. Treatment Verification

### 11.1 Observable Evidence: D LineageStage Removal

**D run logs must NOT contain**:
- `[LineageStage:SharedBenchmark]` (the SharedBenchmarkFilteredLineageStage log prefix)
- `[LineageStage] program=` (the base LineageStage log prefix)
- Any `SharedBenchmarkFilteredLineageStage` class name in stage execution logs

**D Redis must NOT contain**:
- `:lineage_state:` keys (or equivalent keys written by LineageStage during compute)

**G run logs MUST contain** (control invariant):
- `[LineageStage] program=` (the base LineageStage log prefix, since G uses unfiltered LineageStage)

**D run logs MUST contain** (positive activation indicator):
- A log line indicating lineage stages were removed, in the exact format: `[AsymmetricPipeline] disable_lineage_on_improver=true: removed LineageStage, LineagesToDescendants, LineagesFromAncestors` -- the implementer MUST add this log line at the point where the three `remove_stage` calls execute. Absence of this log line on any D run means the flag was not applied. Abort and debug.

**D run logs MUST NOT contain** (ordering invariant violation check):
- `lineage_filter.aggregator required` -- this is the exact `ValueError` message text from `_resolve_lineage_filter`. Its presence in any D log indicates the ordering invariant was violated (the `disable_lineage_on_improver` gate fired after `_resolve_lineage_filter` was called). The run is corrupted; abort and fix the implementation.

### 11.2 Observable Evidence: D Tanh Scoring

Same as d-smoothing-minimal Section 11.1:
- `pop_b/evaluate.py` contains `np.tanh` on the scoring line (verify via `git diff`)
- D fitness histogram at gen 3 shows non-zero mass below the median (scores distributed around 0.5, not piled at 0.0)
- D per_opp_metrics artifact: `delta` field contains signed (possibly negative) values
- Exception-path score = 0.5 (not 0.0)

### 11.3 Hydra Override Verification (`--cfg job`)

Before the 8 runs launch, rendered Hydra configs must show:

```bash
# G runs: verify softmax, archive_reeval=false, NO disable_lineage_on_improver
for r in A1_G A2_G C1_G C2_G; do
  $GIGAEVO_PYTHON run.py <r-overrides> --cfg job 2>&1 | grep -E \
    'opponent_sampling_mode|archive_reeval|refresh_order|refresh_passes|disable_lineage'
done  # expect: softmax, false, (refresh absent or fifo/1), disable_lineage absent or false

# D runs: verify top_k, archive_reeval=true, bucketed + passes=1, disable_lineage=true
for r in A1_D A2_D C1_D C2_D; do
  $GIGAEVO_PYTHON run.py <r-overrides> --cfg job 2>&1 | grep -E \
    'opponent_sampling_mode|archive_reeval|refresh_order|refresh_passes|disable_lineage'
done  # expect: top_k, true, generation_bucketed, 1, disable_lineage_on_improver=true
```

### 11.4 Smoke Test Contract

Before full launch, run a paired smoke test on DBs 11/12 for 3 generations:

1. Launch A1_G (DB 11) + A1_D (DB 12) with `max_generations=3`.
2. After gen 3, verify on D:
   - `fitness < 0.001` fraction < 5% (tanh treatment active)
   - Median D fitness in [0.3, 0.7] (neutral band)
   - At least one D program with `fitness` in (0.4, 0.6) (near neutral point)
   - D log does NOT contain `[LineageStage:SharedBenchmark]` (lineage removed)
   - D log does NOT contain `[LineageStage] program=`
3. Verify on G:
   - G log DOES contain `[LineageStage]` (control invariant -- G keeps lineage)
4. Inspect a sample D program's per_opp_metrics artifact: `delta` field should be signed float
5. If smoke passes, flush DBs 11/12 and proceed to full launch on DBs 1--8

### 11.5 Treatment Checks Block Schema

```yaml
treatment_checks:
  redis_key_pattern_present:
    # G-side lineage keys must exist
    - pattern: "{prefix}:lineage_state:*"
      applies_to: [A1_G, A2_G, C1_G, C2_G]
      note: "G runs keep LineageStage; lineage keys should be written"
  redis_key_pattern_absent:
    # D-side lineage keys must NOT exist
    - pattern: "{prefix}:lineage_state:*"
      applies_to: [A1_D, A2_D, C1_D, C2_D]
      note: "D runs have LineageStage removed; no lineage keys should exist"
  log_pattern_present:
    # Positive activation indicator: lineage was disabled on D (MUST appear)
    - pattern: "disable_lineage_on_improver=true: removed LineageStage"
      applies_to: [A1_D, A2_D, C1_D, C2_D]
      severity: "ABORT if absent -- flag was not applied"
    # G-side lineage must still be active
    - pattern: "\\[LineageStage\\] program="
      applies_to: [A1_G, A2_G, C1_G, C2_G]
  log_pattern_absent:
    # D logs must not show SharedBenchmarkFilteredLineageStage activity
    - pattern: "\\[LineageStage:SharedBenchmark\\]"
      applies_to: [A1_D, A2_D, C1_D, C2_D]
    - pattern: "SharedBenchmarkFilteredLineageStage"
      applies_to: [A1_D, A2_D, C1_D, C2_D]
    # Ordering invariant violation: _resolve_lineage_filter fired before disable gate
    - pattern: "lineage_filter.aggregator required"
      applies_to: [A1_D, A2_D, C1_D, C2_D]
      severity: "ABORT -- ordering invariant violated, run corrupted"
```

---

## 12. Literature Review

### 12.1 Timing-Asymmetry Theory

The d-smoothing-minimal issues log measured D per-gen median at 3665s vs G at 1990s (1.84x slower, or D at 57% of G's pace). Two contributors were identified:

1. **Intrinsic D evaluation cost**: Improver runs optimization-style improvement per opponent call; Constructor just emits 11 points. This is structural and cannot be eliminated by any config change.
2. **LineageStage two-pass refresh overhead**: `refresh_passes=2` + `generation_bucketed` re-scores the full D archive each epoch, with `SharedBenchmarkFilteredLineageStage` performing an LLM call per program during each refresh pass. Confirmed as a known bottleneck (PATTERNS.md: "Two-pass bucketed refresh destroys D compute advantage").

Removing LineageStage eliminates contributor (2) entirely and also removes the per-mutation LLM call for lineage narrative generation (which is O(mutations) overhead per generation).

Paredis (PPSN 2000) provides the theoretical framework: when one population out-evolves the other in a coevolutionary system, performance degrades regardless of information quality. This is exactly what d-smoothing-minimal observed. The remedy tested here (reducing D's compute load by removing lineage) maps to Paredis' "balancing mechanism."

### 12.2 Lineage Ablation Precedents

CodeEvolve (arXiv 2510.14150, 2025) intentionally excludes the ancestor chain in some mutation operations, finding that lineage can be a constraint rather than a helper in LLM-guided evolutionary agents. The positive effect of excluding lineage enables novel strategy exploration. For GigaEvo's D side (Improver), which primarily seeks local improvements rather than novel strategies, the lineage value may be lower than for G.

### 12.3 WGAN-GP Analogy

WGAN-GP (Gulrajani et al. 2017) uses K=5 discriminator updates per generator update. d-smoothing-minimal reversed this (D at 0.54:1). Removing lineage should restore something closer to the v1-era 4.0x D/G ratio, approaching the "train D until convergence" ideal (Metz et al. ICML 2018).

### 12.4 Archive Re-evaluation in QD Literature

No dedicated "refresh vs no-refresh" ablation exists in MAP-Elites literature (Mouret & Clune 2015). GigaEvo's per-epoch archive refresh is non-standard. Full citation details in `experiments/heilbron/d-tanh-no-lineage/literature_brief.md`.

---

## 13. Treatment Mechanism (Code-Level Specification)

### 13.1 File: `gigaevo/adversarial/asymmetric_pipeline.py`

**Change 1 -- New constructor kwarg** (line ~168):
```python
def __init__(
    self,
    ...
    lineage_filter: LineageFilterConfig | DictConfig | None = None,
    disable_lineage_on_improver: bool = False,   # NEW
    ...
):
```

**Change 2 -- Gate the D-side lineage block** (lines 206--215):

**ORDERING INVARIANT**: When `disable_lineage_on_improver=True` AND `population_role=="improver"`, the builder MUST skip the `_resolve_lineage_filter` + `_replace_lineage_with_filtered` block AND MUST call `self.remove_stage("LineageStage")`, `remove_stage("LineagesToDescendants")`, `remove_stage("LineagesFromAncestors")` BEFORE any code path that resolves `lineage_filter`. The `_resolve_lineage_filter` function (lines 80--113) contains an explicit guard: `raise ValueError("lineage_filter.aggregator required -- no silent fallback")`. If the `disable_lineage_on_improver` check is placed AFTER `_resolve_lineage_filter` is called, the `ValueError` fires when `lineage_filter` is null or misconfigured and crashes D runs. The `disable_lineage_on_improver` gate must short-circuit BEFORE `_resolve_lineage_filter` is ever invoked.

```python
# Current code (v2):
if dg_tracker is not None:
    ...
    if population_role == "improver":
        resolved_filter = _resolve_lineage_filter(...)
        self._replace_lineage_with_filtered(...)

# Treatment code:
if dg_tracker is not None:
    ...
    if population_role == "improver":
        if disable_lineage_on_improver:
            self.remove_stage("LineageStage")
            self.remove_stage("LineagesToDescendants")
            self.remove_stage("LineagesFromAncestors")
        else:
            resolved_filter = _resolve_lineage_filter(
                lineage_filter, ctx.problem_ctx.metrics_context
            )
            self._replace_lineage_with_filtered(
                ctx, dg_tracker, resolved_filter, stage_timeout,
            )
```

**Required unit test**: `test_no_lineage_on_improver_skips_filter_resolution` -- instantiate `AdversarialAsymmetricPipelineBuilder` with `disable_lineage_on_improver=True` and `lineage_filter=None` (or omitted). Assert: (1) no `ValueError` is raised, (2) `"LineageStage"` is absent from `self._nodes`, (3) `"LineagesToDescendants"` and `"LineagesFromAncestors"` are absent from `self._nodes`. This test protects against future refactors that might move `_resolve_lineage_filter` outside the guard or invert the conditional ordering.

**Blast radius**: LOW. `remove_stage()` is already implemented in `PipelineBuilder` (lines 87--97 of `default_pipelines.py`); it strips the node + all data-flow edges + exec deps. `MutationContextStage` receives `None` for `lineage_ancestors` and `lineage_descendants` -- handled by its `Optional` typing and null-safe `compute()`. `_wire_cache_on_edges()` is guarded by `if "LineageStage" in self._nodes` (line 313--314 of `asymmetric_pipeline.py`). No shared framework code changes needed.

### 13.2 File: `problems/heilbron_repro_v1/pop_b/evaluate.py`

Tanh scoring change carried from d-smoothing-minimal. Byte-for-byte identical to d-smoothing-minimal's treatment. No additional changes.

### 13.3 Carry-Forward Note

The d-smoothing-minimal branch (`exp/heilbron/d-smoothing-minimal`, commit `be9ec33f`) contains the `pop_b/evaluate.py` tanh change. This experiment's branch must include both:
1. `pop_b/evaluate.py` tanh change (from d-smoothing-minimal)
2. `asymmetric_pipeline.py` `disable_lineage_on_improver` kwarg (new for this experiment)

These touch non-overlapping files and compose cleanly.

---

## 14. Pre-Registered Analysis Plan

### 14.1 Primary

mu_G (best-ever actual_fitness across 4 G runs) compared against:
- v2 historical comparator: mu_G=0.03315
- baseline-repro: mu_G=0.03449

Report bootstrap 95% CI (B=10000). Verdict from effect-size thresholds (Section 2.1).

### 14.2 D/G Gen-Pace Ratio (Primary Mechanistic)

At gen 5, report D_gen/G_gen per pair. Graded outcome per Section 2.2a: Green (>= 0.90 across 3+ pairs: PASS), Yellow ([0.70, 0.90) across 3+ pairs: CONTINUE WITH AMENDMENT), Red (< 0.70 across 3+ pairs: ABORT -> `running -> invalid`). Compare to d-smoothing-minimal (0.57x) and v1 (4.00x). If Yellow, record the amendment in `04_issues_log.md` and note the interpretive caveat in `05_results.md`.

### 14.3 Treatment Verification

D point-mass fraction at gen 3 (Section 11.4 check 2). Binary: PASS (< 5%) or FAIL. D log pattern absent/present checks (Section 11.5). Binary: PASS or FAIL.

### 14.4 Mechanistic Prediction: D Fitness Distribution Shape

At gen 5 and gen 20, report per-D-run: fraction in [0.1, 0.9], median, variance. PASS criteria from Section 2.2a (>= 3 of 4 D runs at each checkpoint).

### 14.5 Per-Arm Breakdown

Split by Composition vs Gradient-in-prompt. Cross-arm raw delta should be < 0.002 (confirmation of feedback-mode NULL). If cross-arm delta exceeds 0.005, flag as anomalous.

### 14.6 D Trajectory Analysis

D mean fitness trajectory over generations (10-gen buckets). Compare shape against:
- v2's collapsed trajectory (2/4 D runs at fitness=0.000)
- Expected: stable around 0.5 or increasing, not collapsing

### 14.7 Secondary Diagnostics

Report G invalidity rate (compare to v2's 35--47%), D invalidity rate (compare to v2's 10--17%), D exception rate (new for tanh; monitor for inflation from score=0.5 exception path), D/G gen-pace ratio over full run (trajectory, not just gen-5 snapshot).

---

## 15. Monitoring and Watchdog

### 15.1 Watchdog Config

```yaml
watchdog:
  plugin: adversarial
  plot_metrics: [actual_fitness, fitness, mean_post_quality]
  plot_commands:
    - command: arms-race
      args: {metric: actual_fitness, paired: "A1_G:A1_D,A2_G:A2_D,C1_G:C1_D,C2_G:C2_D"}
      caption: "Arms-race: G actual_fitness vs D mean_post_quality"
    - command: comparison
      args: {metric: actual_fitness, smoothing: ema, window: 10, annotate-frontier: true, no-frontier-for: "A1_D,A2_D,C1_D,C2_D"}
      caption: "All G runs vs SOTA"
  alert_thresholds:
    invalidity_rate: 0.75
    stagnation_window: 15
```

### 15.2 D/G Gen-Pace Ratio Gate (Gen 5)

At the gen-5 checkpoint (expected ~2.5--5 hours into the run), the researcher or checkpoint skill computes D_gen/G_gen per pair:

| Pair | D gen | G gen | Ratio | Zone |
|---|---|---|---|---|
| A1 | (observed) | (observed) | D/G | Green (>= 0.90) / Yellow ([0.70, 0.90)) / Red (< 0.70) |
| A2 | (observed) | (observed) | D/G | (same) |
| C1 | (observed) | (observed) | D/G | (same) |
| C2 | (observed) | (observed) | D/G | (same) |

**Green (>= 3 of 4 pairs >= 0.90)**: Continue. No amendment.
**Yellow (>= 3 of 4 pairs in [0.70, 0.90))**: Continue with amendment in `04_issues_log.md`. Scientific interpretation conditional on residual timing gap.
**Red (>= 3 of 4 pairs < 0.70)**: Transition `running -> invalid`. Record in `04_issues_log.md` and `03_plan.md` amendment.

### 15.3 Checkpoint Milestones

| Milestone | Expected wall-clock | Primary check |
|---|---|---|
| Gen 5 (all pairs) | ~2.5--5h | D/G gen-pace ratio gate + treatment verification |
| Gen 20 (G runs) | ~10--15h | D fitness distribution shape (Section 2.2a gen 20) |
| Gen 50 (G runs) | ~20--28h | mu_G trajectory assessment; decide if continuing past 28h is warranted |

---

## 16. Compute Budget

| Resource | Estimated |
|---|---|
| Wall time | ~18--28h. G per-gen pace was ~33 min in d-smoothing-minimal (G pipeline is unchanged); at 33 min/gen, G reaches gen 50 at ~27.5h, close to the 28h hard cap. If D runs 2--4x faster than G (expected v1-era regime), G becomes the wall-clock bottleneck. Expected G depth at 28h: ~50 gens. |
| Hard cap | 28h |
| Server | 10.232.30.185 (8 concurrent processes) |
| Redis DBs | 1--8 (production), 11--12 (smoke test) |
| LLM calls | ~20--25k completions across all runs (reduced from v2's ~32k estimate because D runs skip lineage LLM calls entirely; G runs retain lineage) |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 via LiteLLM proxy |

---

## 17. Reproducibility

### 17.1 Predecessor Commits

| Component | Commit | Note |
|---|---|---|
| v2 launch | `532ac3e5` | v2's exact launch commit |
| d-smoothing-minimal launch | `be9ec33f` | d-smoothing-minimal's launch commit (INVALID) |
| G-smoothing hotfix | `2de8267e` (PR #219) | Continuous G resistance; now on main |
| D hard-floor scoring (pre-change) | main HEAD | `pop_b/evaluate.py` still has hard-floor on main |
| This experiment's branch | TBD (pre-registration commit) | Will contain both the D tanh change and the `disable_lineage_on_improver` change |

### 17.2 Dataset Snapshot

Heilbronn N=11 problem uses synthetic point configurations generated at evaluation time. No fixed dataset. Q_MAX=0.0365 hardcoded in both `pop_a` and `pop_b` evaluate.py. No dataset snapshot required.

### 17.3 Environment

- Python: `/home/jovyan/.mlspace/envs/evo/bin/python3`
- LiteLLM proxy: `http://10.232.30.185:4000/v1`
- Model: `Qwen3-235B-A22B-Thinking-2507`
- Auth: `Bearer sk-gigaevo`
- `environment_freeze.txt` will be generated at launch time

---

## 18. Deviations from Pre-Registration

None yet. Any deviation will be logged in `04_issues_log.md` and as an amendment in `03_plan.md` before `05_results.md` is written.

---

## 19. Revision Log

### Round 1 -> Round 2 (2026-04-25)

Revisions in response to Volkov's `02_review.md` (verdict: NEEDS REVISION) and a researcher factual correction.

| Item | Severity | Change summary | Sections modified |
|---|---|---|---|
| **C1**: D/G ratio threshold >= 1.0 is uncalibrated | Critical | Replaced binary >= 1.0 gate with graded Green/Yellow/Red zones (>= 0.90 / [0.70, 0.90) / < 0.70). Green continues without amendment. Yellow continues with amendment and interpretive caveat. Red aborts. Justified 0.70 cutoff against d-smoothing-minimal's 0.54x and 0.90 green threshold against v2's 0.80x precedent. Added "what would be SURPRISING" bound (< 1.5x). | 2.2a, 2.3, 4 (DV table), 8, 10, 14.2, 15.2 |
| **M1**: d-smoothing-minimal comparison framing | Major | Reframed comparison hierarchy. v2 is now the primary quantitative comparison (complete data, 2 confounded IVs). d-smoothing-minimal is the mechanistic/validity comparison (binary: did we avoid invalidation?). Removed "cleanest comparison" language. | 1 |
| **M2**: Implementation ordering hazard | Major | Added explicit ordering invariant: `disable_lineage_on_improver` gate must short-circuit BEFORE `_resolve_lineage_filter`. Required unit test: `test_no_lineage_on_improver_skips_filter_resolution`. Added `log_pattern_absent` for `"lineage_filter.aggregator required"` as runtime ordering-violation detector. Promoted D activation log from SHOULD to MUST with exact format. | 11.1, 11.5, 13.1 |
| **Researcher correction**: `archive_reeval=true` / `refresh_passes=2` are load-bearing | Factual fix | Rewrote Section 3.1 to frame both as load-bearing controlled variables, not "dead config" or "zombie overhead." `archive_reeval=true` re-scores D archive programs against latest top-1 G HoF; `refresh_passes=2` drives the rescoring loop twice per epoch. Removing LineageStage eliminates only the LLM lineage-agent call, not the archive-rescoring path. Updated Confound 7 and Volkov-Targeted Preempt accordingly. | 3.1, 5a (refresh_passes row), 9 (Confound 7), 9.1 (Preempt) |
| **m1**: `refresh_passes=2` zombie overhead | Minor | Addressed in the revised Section 3.1: acknowledged the O(archive_size) scheduling overhead per epoch; flagged as secondary observation target if D/G ratio is marginal. | 3.1 |
| **m2**: Wall-clock estimate optimistic | Minor | Updated Section 16 with G per-gen wall-clock assumption (~33 min/gen) and derived G depth at 28h (~50 gens). Acknowledged G as wall-clock bottleneck if D runs 2--4x faster. Updated Section 10 with Yellow-zone D depth estimate. | 10, 16 |
| **m3**: D/G ratio expectation not a falsifiable bound | Minor | Added explicit "what would be SURPRISING" statement in Section 2.2a: ratio below 1.5x at gen 5 would suggest intrinsic D evaluation cost is the dominant bottleneck. | 2.2a |
| **m4**: Missing positive log-line specification | Minor | Promoted SHOULD to MUST in Section 11.1. Specified exact log line format: `[AsymmetricPipeline] disable_lineage_on_improver=true: removed LineageStage, LineagesToDescendants, LineagesFromAncestors`. Added corresponding entry in Section 11.5 `log_pattern_present` with `severity: "ABORT if absent"`. | 11.1, 11.5 |
| **m5**: Literature scout `archive_reeval=false` not addressed | Minor | Added direct response in revised Section 3.1: "We accept that retaining `archive_reeval=true` on D reduces D's effective speed advantage relative to v1...If D/G ratio is >= 0.90 but substantially below v1's 4.0x, `archive_reeval` is a candidate IV for a follow-up experiment." | 3.1 |

### Round 2 -> Round 3 (2026-04-25)

Code-verified semantic corrections to Section 3.1, prompted by researcher's "double check it" directive after Round 2's framing of `archive_reeval`/`refresh_passes` was insufficiently precise.

| Item | Severity | Change summary | Sections modified |
|---|---|---|---|
| **Researcher correction (cache semantics)**: `archive_reeval` flag is named backwards | Factual fix | Verified against `gigaevo/adversarial/pipeline.py:204-205` and `gigaevo/adversarial/stages.py:131-159`: `archive_reeval=true` selects `InputHashCache` (cache, invalidate when opponent IDs change), NOT "always re-evaluate". Added explicit cache-semantics paragraph; corrected v1 reasoning (v1's `archive_reeval=false` meant *more* eval work per epoch, so v1's 4.0x ratio came from no-lineage, not from skipping the cache). Made the "load-bearing path" claim precise: opponent-ID-keyed cache invalidation on the evaluator is what keeps D fresh as G advances, and that path is **independent of `LineageStage`**. | 3.1 |
| **Researcher correction (pass-2 semantics)**: pass-2 fires no LLM under no-lineage | Factual fix | Researcher quote: "pass-2 does not fire LLM, it only updates mutation context." Verified against `gigaevo/evolution/engine/steady_state.py:780-900` and `gigaevo/adversarial/shared_benchmark_lineage.py:60-159`: normal pass-2 re-runs filtered LineageStage with globally-fresh tracker; with `LineageStage` removed on D, pass-2 reduces to a `MutationContextStage` refresh (no LLM, O(archive_size) bookkeeping). Section 3.1 now states explicitly that the dominant per-refresh cost (lineage LLM) is eliminated and the cheap pass-2 work (mutation-context update) is preserved. The mechanism that lifts D's per-gen wall time is identified as the elimination of pass-2's lineage LLM call, not any change to `archive_reeval` or `refresh_passes`. | 3.1 |

### Round 3 -> Round 4 (2026-04-25)

After researcher requested code-level study of which stages re-run on the D refresh, the per-stage cache-mode trace was completed and one configuration was changed.

**Stage-level trace performed**:
- `FetchOpponentIdsStage`: `NO_CACHE` (`stages.py:56`)
- `FetchOpponentResultsStage`: `InputHashCache` (when `archive_reeval=true`) (`stages.py:159`)
- `CallValidatorFunction`: `InputHashCache` (default)
- `DGTrackerStage`: `NO_CACHE` (`dg_tracker_stage.py:64`)
- `InsightsStage`: `InputHashCache` + `cache_on=FetchOpponentIdsStage` (`insights.py:31-33`, `asymmetric_pipeline.py:309-312`)
- `MutationContextStage`: `NO_CACHE` (`mutation_context.py:67`)
- `LineagesFromAncestors` / `LineagesToDescendants`: `NO_CACHE` (`insights_lineage.py:100,160`) -- removed by IV 2 anyway

`grep -rn "refresh_pass" gigaevo/` confirmed only `SharedBenchmarkFilteredLineageStage.compute_hash` reads the engine `refresh_pass` counter.

| Item | Severity | Change summary | Sections modified |
|---|---|---|---|
| **Configuration change**: `refresh_passes` on D set to `1` (down from v2's `2`) | Pre-launch optimisation | With `LineageStage` removed by IV 2, pass 2's sole consumer (`SharedBenchmarkFilteredLineageStage`) is gone. Per-stage trace shows pass 2 cache-hits on `FetchOpponentResults`/`CallValidatorFunction`/`InsightsStage` (D uses deterministic `top_k`, so `FetchOpponentIdsStage` produces identical IDs across passes within an epoch) and only the cheap NO_CACHE stages (`DGTrackerStage` idempotent, `MutationContextStage` deterministic re-format) actually re-run. Pass 2 had zero behavioural payoff; setting to `1` strictly removes O(archive_size) per-epoch DAG-runner bookkeeping with no behavioural change. Not an additional IV vs v2 because pass 2 was already a no-op after IV 2; the lineage-driven re-runs that pass 2 was designed to enable are gone. | 3.1, 5a (refresh_passes row), 6.1 (D extra_overrides), 9 (Confound 5, Confound 7), 9.1 (Preempt #2), 11.3 (Hydra verify regex expectation: 2 -> 1) |
| **Identification of load-bearing pass-1 path**: `InsightsStage` LLM cost gates on opponent-ID change | Documentation precision | Section 3.1 now identifies the actual LLM-bearing D refresh path: when paired G HoF flips, opponent IDs change in pass 1's `FetchOpponentIdsStage` re-sample, cascading cache misses through `FetchOpponentResultsStage` -> `CallValidatorFunction` -> `InsightsStage` (the LLM call). This is what keeps D adversarially responsive. Removing `archive_reeval` would break this; keeping `refresh_passes=2` does nothing for it. | 3.1, 9.1 (Preempt #2) |

---

*Ready for Reviewer-2's scrutiny.*
