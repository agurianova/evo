# Experimental Design: v1 Replication Under Stacked Fixes (SBF-Lineage + SOFTMAX + I-16/I-17)

**Date**: 2026-04-22
**Researcher**: Claude Opus 4.7 (autonomous launch, user-approved stacked design)
**Status**: Pre-registered
**Predecessor**: `heilbron/adversarial-repro-v1` (NULL verdict, PR #211 merged 2026-04-21)

---

## 1. Research Question

Under v1's exact hyperparameters and structure, do the three improvements landed since v1 closed — taken together — recover signal in the Heilbronn N=11 adversarial co-evolution pipeline?

This is a **deliberately confounded replication**. We stack three changes on top of v1:
1. **`SharedBenchmarkFilteredLineageStage`** on D-side (PR #215) — replaces the base `LineageStage` via `PipelineBuilder.replace_stage("LineageStage", …)`. Filters parent→child transitions by shared-opponent (HoF-invariant) intersection and injects per-metric means over the shared subset into D's mutation prompt.
2. **`OpponentSamplingMode.SOFTMAX` on G runs only** (D runs keep deterministic `TOP_K`) — G gets stochastic fitness-proportional exposure to diverse D improvers for broader exploration; D keeps deterministic top-1-G sampling so its archive is **coherent with respect to the current best G**. Paired with per-role `archive_reeval` (D=true, G=false), this creates an **asymmetric caching invariant**: every time G's top-1 flips, D's opponent_ids change → downstream cache keys miss → FetchOpponentResults + LineageStage + metric stages re-execute across D's archive. Net effect: D is always up-to-date against current top-1 G, while G's historical evaluations stay fixed (stochastic sampling gives G fresh D exposure per gen anyway). See §5a for the full table.
3. **I-16 fix** — `evaluate.py` now correctly returns `(metrics, artifact)` tuple; cached artifact bytes no longer silently become `None` (which in v1 fed empty artifacts to `DGTrackerStage`, BD-axis regression).
4. **I-17 fix** — `CompositionInjectionHook` uses `Program.create_child` so injected D∘G programs get `is_root=False` and `generation=G.generation+1` (v1 stamped every injected program `gen=1, is_root=True`, corrupting gen-1 and is_root archive slices).

**Attribution is intentionally deferred.** If v2 produces signal (or moves the distribution), the direction of effect is informative even without isolating which treatment owns it. Decomposition (ablate SBF-Lineage alone, ablate SOFTMAX alone) is a follow-up experiment conditional on v2 showing movement.

**Positioning vs REDESIGN bundle.** `experiments/PATTERNS.md` identifies the REDESIGN bundle (smoothed tanh fitness + deterministic HoF + K=L=3 + cache_on edges) as the #1-priority open question on heilbron. v2 deliberately runs **before** REDESIGN because it answers a precondition check that is cheap to run and informative either way: does info-flow improvement alone — under the existing hard-floor D fitness — recover any signal? A POSITIVE result would be remarkable and would suggest info-flow was the binding constraint, not D hard-floor (re-prioritizing the research program). A NULL is consistent with the REDESIGN-first hypothesis (D hard-floor scoring is the true bottleneck and must be fixed before info-flow treatments can produce measurable lift). Either way, v2's cost (~18h on one server) is a fraction of REDESIGN's scope.

**Literature-brief scope note.** `experiments/heilbron/adversarial-repro-v2/literature_brief.md` was carried forward from v1 and focuses on replication novelty (CI-based μ comparison, deliberately confounded stacking as a first-order signal probe). It does **not** independently survey the three stacked treatments introduced in v2, because those are new within GigaEvo's experimental program: (a) shared-benchmark-filtered lineage narratives are a within-framework invention (PR #215) with no external baseline; (b) `OpponentSamplingMode.SOFTMAX` paired per-role with `archive_reeval` is a GigaEvo-internal scheduling pattern; (c) the two-pass bucketed refresh with class-level cache token (`_refresh_pass_token`) is engine-layer plumbing, not a research method. No prior heilbron experiment tested any of these three independently — cross-experiment attribution will be possible only when the follow-up ablation experiments land.

---

## 2. Hypotheses

Let **μ_v2_G** = mean best-ever `actual_fitness` across the 4 G runs (A1_G, A2_G, C1_G, C2_G).
Let **μ_v1_G** = 0.03413 (v1 grand mean across 4 G runs post-I-16/I-17 relaunch, per `05_results.md` §5).

**H0**: μ_v2_G ≤ μ_v1_G + 0.0005 (stacked fixes do not move the mean beyond v1-era noise).
**H1**: μ_v2_G ≥ μ_v1_G + 0.002 (stacked fixes recover ≥2pp improvement toward v1-era SOTA 0.03650).

### Effect-size thresholds (4 G runs, 200 gens each)

| μ_v2_G (best-ever actual_fitness) | Verdict |
|-----------------------------------|---------|
| ≥ 0.0365 and ≥ 1/4 G runs at 0.0365 | **POSITIVE** — original-v1 result recovered |
| ≥ 0.0355 and < 0.0365 | **SUGGESTIVE** — directional improvement toward SOTA |
| within 0.001 of μ_v1_G (0.03313–0.03513) | **NULL** — stacked fixes do not help |
| < 0.0330 | **REGRESSIVE** — SOFTMAX stochasticity or SBF-Lineage filtering degrades |

### Abandon direction

If v2 μ_G < 0.0330 **and** no G run reaches 0.0350 across all 800 generations, the SBF-Lineage + SOFTMAX combination is actively harmful in this regime. Next step: individual ablation (SOFTMAX-only vs SBF-only) to find the regressor.

### Interpretation of NULL (stacked-treatment asymmetry)

A v2 NULL does **not** close any of the three individual treatment directions. At N=4 with ~30% power (§7), false-NULL under a real ~0.002pp composite effect is ~70% likely; and even under ideal power, treatments can cancel (e.g., SBF-Lineage +0.003pp while SOFTMAX −0.003pp = net zero).

Localization protocol on NULL (using diagnostics §13.3, §13.4, §13.6):

| Diagnostic pattern | Interpretation | Next experiment |
|--------------------|----------------|-----------------|
| `kept/total` high (>50%) + signal present on D fitness but no G-side transfer | SBF-Lineage works but D improvements don't transfer through SOFTMAX opponent rotation | Ablate SOFTMAX (G=TOP_K, D=TOP_K) with SBF-Lineage only |
| `kept/total` low (<20%) | SBF-Lineage is inert — 93% of lineage calls produce no useful narrative | Drop SBF-Lineage from future experiments; focus on opponent sampling + REDESIGN |
| `kept/total` high + cache miss rate low on D | D is NOT being re-scored against new top-1 G (archive_reeval silently failed) | Fix cache-invalidation wiring before re-running |
| All diagnostics nominal, v2 still NULL | Composite treatment is genuinely inert on the broken D-fitness landscape | Advance to REDESIGN bundle (smoothed tanh, deterministic HoF, K=L=3) |

A v2 NULL is also consistent with the REDESIGN-first hypothesis: info-flow improvements may not be the binding constraint; D hard-floor scoring may be.

### Mechanistic entanglement note

The three treatments are **not independent in mechanism**. Treatment (c) — the two-pass bucketed refresh — exists specifically to make SBF-Lineage's descendant narratives consistent under HoF rotation. If SBF-Lineage is inert, the two-pass refresh is wasted compute rather than an independent treatment. A NULL could indicate either "SBF-Lineage is useless regardless of data freshness" or "SBF-Lineage needs fresh data AND something else (e.g., stronger filter, richer evidence format)." This entanglement is acknowledged up front, not a post-hoc rescue narrative.

---

## 3. Independent Variables (confounded)

Single composite treatment: **{SBF-Lineage ON, SOFTMAX sampling ON, I-16 fix ON, I-17 fix ON}** vs. the v1 historical comparator. No within-experiment IV. Attribution deferred.

| Comparator | μ_G best-ever | Best G | Source |
|------------|---------------|--------|--------|
| **v1 (post-relaunch)** | 0.03413 | 0.03650 (A1_G, gen 5, composition-injected) | v1 `05_results.md` §5, NULL verdict |
| **v1 (pre-relaunch zombie)** | 0.03650 | 0.03650 (b2cc69cd, gen=5 lamarckian) | I-17 contamination — see `04_issues_log.md` I-17 |
| **v0 asymmetric-iterations** | 0.03574 | 0.03650 (C2_G, gen 5) | Historical SOTA, pre-bug-fix library |
| **baseline-repro** | 0.03449 | 0.03610 | Solo MAP-Elites, no adversarial |

---

## 4. Dependent Variables

Primary: **`actual_fitness`** (raw `min_area` from Constructor evaluation; higher is better).
Secondary: G fitness composite, G resistance (binary at n_opponents=1), D fitness, D wins count, SBF-Lineage `kept/total` ratio (diagnostic), SOFTMAX hash-cache hit rate (diagnostic — expect lower than v1's TOP_K).

---

## 5. Controlled Variables (identical to v1)

All of v1's pinned config is preserved:

| Parameter | Value | Source |
|-----------|-------|--------|
| `pipeline` | `heilbron_repro_v1` | Config reused — frozen v1 evaluate.py semantics |
| `num_parents` | 1 | |
| `max_elites_per_generation` | 8 | |
| `max_mutations_per_generation` | 8 | |
| `inner_iterations` | 1 | |
| `n_opponents` | 1 | |
| `source_prompt_k` | 1 | |
| `mutation_mode` | rewrite | |
| `pre_step_hook.drift_cap` | 100_000 | Effectively no-op; preserves v1's asymmetric compute rate |
| `pre_step_hook.sync_every_n_epochs` | 1 | |
| `max_generations` | 200 | |
| `stage_timeout` | 3000s | |
| `dag_timeout` | 7200s | |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` via LiteLLM 10.232.30.185:4000 | |

---

---

## 5a. Per-Role Asymmetric Config (NEW vs v1)

| Parameter | G runs (constructor) | D runs (improver) | Rationale |
|-----------|---------------------|-------------------|-----------|
| `opponent_sampling_mode` | `softmax` | `top_k` | G: broad stochastic exposure. D: deterministic sampling so opponent_ids are a stable function of G's current top-1. |
| `pipeline_builder.archive_reeval` | `false` | `true` | D: `DEFAULT_CACHE` (InputHashCache) on `FetchOpponentResults` — re-eval on opponent_ids change. G: `NO_CACHE` (SOFTMAX IDs shift every gen anyway, no cache stability to preserve). |
| `engine_config.refresh_order` | `fifo` | `generation_bucketed` | D-only fix for cross-program refresh race (see below). G has no shared-store reads in its LineageStage, so fifo is sufficient. |
| `engine_config.refresh_passes` | `1` | `2` | D-only: closes the two-sided race. Pass 1 rewrites `DGImprovementTracker` globally; pass 2 re-runs `SharedBenchmarkFilteredLineageStage` with both ancestor AND descendant tracker data fresh. Cache invalidation between passes via class-level `SharedBenchmarkFilteredLineageStage._refresh_pass_token` (bumped by the engine before each pass, folded into `compute_hash`). Within a pass, normal input-hash caching still deduplicates LLM calls across concurrent siblings. |
| `opponent_result_mode` | `exec` | `cached` | Unchanged from v1 per-role wiring. G actually runs D improvers; D reads G's stored CallProgramFunction output. |
| `population_role` | `constructor` | `improver` | Unchanged. |
| Effective LineageStage | Base `LineageStage` (unfiltered) | `SharedBenchmarkFilteredLineageStage` (PR #215) | `replace_stage` fires only when `population_role=improver`. |

**Invariant (caching)**: D's archive evaluations are always consistent with the current top-1 G. When top-1 G flips:
- D's `FetchOpponentIdsStage` (top_k) produces new opponent_ids → `FetchOpponentResults` cache miss → downstream re-execution via existing `cache_on` edges (`FetchOpponentIdsStage → LineageStage`, `FetchOpponentIdsStage → InsightsStage`; `asymmetric_pipeline.py:_wire_cache_on_edges`).
- Metric scoring stages consume `FetchOpponentResults.output` via data-flow edges → natural invalidation cascade.
- Net: D re-scores against the new top-1 G before next mutation round.

G's archive is **not** re-scored when anything changes — stochastic opponent sampling provides fresh D exposure every generation by construction.

**Invariant (two-pass generation-bucketed refresh, D only)**: The cross-program race on D is *two-sided*:

- **Ancestor side**: a child's `SharedBenchmarkFilteredLineageStage` reads the shared `DGImprovementTracker` for its parent. If the parent's `DGTrackerStage` hasn't landed yet, the child reads stale data.
- **Descendant side**: when building `LineagesToDescendants` gather output, a program at gen *N* reads tracker entries for its children at gen *N+1..N_max*. Even with bucketed **ascending** refresh, by the time gen *N* runs, its gen-*N+1* descendants have not yet been re-evaluated → the descendant tracker snapshot is stale.

Single-pass bucketed ordering closes only the ancestor side. Closing both requires **two passes** per epoch refresh:

1. **Pass 1** — walk ascending generations one bucket at a time, awaiting idle between buckets. Every program is re-evaluated; by the end of pass 1 the shared `DGImprovementTracker` holds current opponent-set metrics for the **entire archive** (both ancestors and descendants of any node). `SharedBenchmarkFilteredLineageStage` also runs here, but its descendant narratives are built against a partially-stale tracker.
2. **Pass 2** — repeat the bucketed walk. `SharedBenchmarkFilteredLineageStage` re-runs with a globally-fresh tracker, so both `lineage_ancestors` and `lineage_descendants` narratives are computed against the true current shared-benchmark set.

**Cache invariant between passes**: Without invalidation, pass 2's `SharedBenchmarkFilteredLineageStage` would hit its input-hash cache from pass 1 and skip the re-run. We close this with a class-level `_refresh_pass_token` that `SteadyStateEvolutionEngine._refresh_archive_programs` bumps before each pass, and that `SharedBenchmarkFilteredLineageStage.compute_hash` folds into the cache key as `…:rp{token}`. Pass 1 and pass 2 therefore have distinct cache keys; within a single pass the token is constant so normal input-hash caching still deduplicates LLM calls across concurrent siblings. `MutationContextStage` re-runs automatically because `LineagesFromAncestors`/`LineagesToDescendants` are `NO_CACHE` — when their source `LineageStage` output changes, the gather outputs change, and `MutationContextStage`'s input hash changes → cache miss.

The implementation lives in `SteadyStateEvolutionEngine._refresh_archive_programs` (dispatches on `SteadyStateEngineConfig.refresh_order` and loops `refresh_passes` times, bumping the token before each pass and awaiting idle between passes). Unit-tested in `tests/evolution/test_steady_state.py::TestBucketedRefresh`, `::TestRefreshPassesConfig`, and `::TestMultiPassRefresh`.

G uses the default `fifo` order and `refresh_passes=1`: its `LineageStage` only reads its own population's archive (no external shared-store handoff within a single generation boundary), so the race is not reachable.

---

## 6. Run Design

8 runs (2 arms × 2 pairs × G/D), identical to v1 structure.

| Label | Role | Arm | DB | Pair-opponent DB | Feedback mode |
|-------|------|-----|----|------------------|---------------|
| A1_G | constructor | Composition | 1 | 2 | composition |
| A1_D | improver | Composition | 2 | 1 | composition |
| A2_G | constructor | Composition | 3 | 4 | composition |
| A2_D | improver | Composition | 4 | 3 | composition |
| C1_G | constructor | Gradient-in-prompt | 5 | 6 | gradient_in_prompt |
| C1_D | improver | Gradient-in-prompt | 6 | 5 | gradient_in_prompt |
| C2_G | constructor | Gradient-in-prompt | 7 | 8 | gradient_in_prompt |
| C2_D | improver | Gradient-in-prompt | 8 | 7 | gradient_in_prompt |

---

## 7. Sample Size Justification

N=2 pairs per arm = same as v1. Two arms × two pairs = 4 G-runs for the primary test. This is the established heilbron adversarial budget; deviating would make cross-experiment comparisons non-monotonic. Statistical power at N=4 is weak (~30% for 0.002pp effect at σ≈0.0012), so results at the SUGGESTIVE margin will not be called POSITIVE — the thresholds above are deliberately wide.

---

## 8. Statistical Test

Primary: **Welch's t-test**, one-sided, on G best-ever actual_fitness across runs, comparing v2 N=4 against v1 post-relaunch N=4. Report effect size (pp delta) + 95% CI via bootstrap (B=10000). Verdict derived from effect-size thresholds (§2), not p-value alone.

---

## 9. Known Confounds and Mitigations

1. **Stacked treatment — attribution deferred**. Mitigation: pre-registered; follow-up ablation experiments conditional on signal.
2. **Redis state carry-over**. Mitigation: flush DBs 1–8 before launch (v1 claims released at closeout).
3. **LiteLLM proxy variance**. Mitigation: same proxy, same model tag, check `opponent_result_mode=exec|cached` log assertions (from v1).
4. **SOFTMAX cache-miss on G is a feature, not a confound**. Since G uses `archive_reeval=false` (NO_CACHE on FetchOpponentResults), stochastic opponent IDs don't inflate runtime — the stage re-executes every call anyway. D uses `archive_reeval=true` with `top_k` so its cache hits are preserved across unchanged-top-1-G ranges; a cache miss there correctly signals "top-1 G changed, re-score against new top-1". Monitor `archive_reeval=true` log on D to confirm the cache path is wired.
5. **SBF-Lineage silent skip (all-parents-filtered)**. `SharedBenchmarkFilteredLineageStage.preprocess()` returns `ProgramStageResult.skipped(…)` when no parent shares a G-opponent with the child. Monitor log line `[LineageStage:SharedBenchmark] kept X/Y parents`; if X/Y < 10% across gens 20+, D's mutation prompt is starved of lineage narratives.
6. **I-17 fix changes archive topology**. Injected D∘G programs now count at `gen=G.gen+1, is_root=False` — this makes `is_root` and gen-1 slice comparisons against v1 not directly meaningful. Mitigation: compare against v1 **post-relaunch** numbers only and document this clearly in 05_results.
8. **Library drift (between-experiment only, symmetric across v2 runs)**. v1 ran on commit `04bd5e69`; v2 runs on the current HEAD of `exp/heilbron/adversarial-repro-v1` which is several merges ahead (PR #215 SBF-Lineage, I-16/I-17 fixes, bucketed refresh mechanism, DGTracker schema unification, metrics-dict tracker, agents factory changes). Only hyperparameters, problem files, and the frozen `evaluate.py` are controlled across v1↔v2 — pipeline builder code, engine scheduling, stage implementations, and mutation prompt formatter are at current HEAD. This confound is **symmetric across all 8 v2 runs** and therefore cannot explain cross-arm differences within v2; it only affects the between-experiment comparison to v1 μ_G=0.03413. Mitigation: (a) `environment_freeze.txt` captures the v2 commit hash and Python env; (b) verdict thresholds (§2) include a 0.001pp NULL band wider than the v1 post-relaunch within-run spread (0.0019pp gen-0 per v1 05_results §3.1); (c) the "Interpretation of NULL" framework (§2) explicitly separates claims that depend on v1 baseline cleanness (fragile) from claims that depend on within-v2 diagnostics (robust).

7. **Two-sided cross-program refresh race on D (pre-existing, fixed in v2)**. Base `SteadyStateEvolutionEngine._refresh_archive_programs` flips ALL archived DONE programs to QUEUED in one batch. With `max_concurrent_dags=8` FIFO scheduling, a child's `SharedBenchmarkFilteredLineageStage.compute()` can execute before its parent's `DGTrackerStage.compute()` writes post-flip metrics to the shared `DGImprovementTracker` (ancestor staleness); and during a single-pass ascending bucketed walk, a program at gen N reads tracker entries for its gen-N+1 descendants before those descendants have been re-evaluated (descendant staleness). **Mitigation (v2 only)**: `engine_config.refresh_order=generation_bucketed` **plus** `engine_config.refresh_passes=2` on D runs — two passes through the bucketed walk, with a class-level `SharedBenchmarkFilteredLineageStage._refresh_pass_token` bumped between passes so pass 2's cache keys differ from pass 1's and the stage actually re-runs with a globally-fresh tracker. Parents always finish writing before children start reading (pass-1 closure of ancestor race), and pass-2 closure of descendant race gives `LineagesToDescendants` a consistent snapshot. Verified by `tests/evolution/test_steady_state.py::TestBucketedRefresh` and `::TestMultiPassRefresh`. G runs keep `fifo` + `refresh_passes=1` (no shared-store handoff within a generation boundary).

   **Process isolation of `_refresh_pass_token`**: the token is a Python class-level attribute on `SharedBenchmarkFilteredLineageStage`, therefore per-OS-process. Each of the 8 v2 runs is a separate `run.py` invocation (separate Python interpreter, separate address space — see `experiments/heilbron/adversarial-repro-v2/launch.sh` once generated by `/experiment-implement`). The 4 D runs each have their own independent `_refresh_pass_token` counter that cannot leak into sibling runs; the 4 G runs never import or touch the subclass (they install the base `LineageStage`). No shared-memory or multiprocessing fork path exists in the engine that could expose the classvar across runs. This is verified structurally: a token leak would require a shared Python runtime, which the deployment topology explicitly forbids.

---

## 10. Stop Criteria

- `stopper=max_generations`, `max_generations=200` (all runs).
- No early-stop per run.
- Full experiment aborts only if: (a) 4+ of 8 processes die within first 2 hours, or (b) watchdog detects `invalidity_rate>0.75` and `stagnation_window>10` on ≥2 G runs.

---

## 11. Compute Budget

- 8 concurrent processes on the single 10.232.30.185 server (same as v1).
- Expected wall-clock: ~18h based on v1's actual runtime; SOFTMAX cache misses may extend this. Hard cap: 28h (anomaly detector alerts, watchdog truncates).
- LLM calls per run: ~200 gens × 8 mutations × (1 constructor + 1 validator + 1 lineage) ≈ 5k completions per G, ~3k per D. Total ~32k completions across all runs.

---

## 12. Treatment Verification

### 12.0 Hydra override --cfg job assertions (pre-launch gate)

Before the 8 runs launch, the rendered Hydra configs for every run are dumped with `--cfg job` and the following must all be present and match the per-role expected values (§12.3). This catches silent Hydra struct-mode rejections of Pydantic-only keys (`engine_config.refresh_order`, `engine_config.refresh_passes` do NOT appear in any YAML config file — they are Pydantic defaults on `SteadyStateEngineConfig`, expected to be absent from the YAML but present in `--cfg job` if the override succeeded).

```bash
# G runs (constructor): SOFTMAX, archive_reeval=false, refresh defaults
for r in A1_G A2_G C1_G C2_G; do
  $GIGAEVO_PYTHON run.py <r-overrides> --cfg job 2>&1 | grep -E \
    'opponent_sampling_mode|archive_reeval|refresh_order|refresh_passes|lineage_filter'
done  # expect 4/4 to show: softmax, false, (refresh fields absent or fifo/1)

# D runs (improver): TOP_K, archive_reeval=true, bucketed + passes=2, lineage_filter pinned
for r in A1_D A2_D C1_D C2_D; do
  $GIGAEVO_PYTHON run.py <r-overrides> --cfg job 2>&1 | grep -E \
    'opponent_sampling_mode|archive_reeval|refresh_order|refresh_passes|lineage_filter'
done  # expect 4/4: top_k, true, generation_bucketed, 2, min_shared=1, inject_shared_evidence=true
```

If any override is missing from `--cfg job`: ABORT launch and investigate Hydra wiring. A Pydantic-only key that collapses to defaults is a soft failure (defaults match intended values for `lineage_filter.*`; it is NOT acceptable for `engine_config.refresh_*` because defaults are `fifo`/`1`, not the D-role treatment values).

### 12.1 Startup verification

```bash
# Per-role sampling asymmetry
grep "opponent_sampling_mode=softmax" run_A1_G.log run_A2_G.log run_C1_G.log run_C2_G.log  # 4/4
grep "opponent_sampling_mode=top_k"   run_A1_D.log run_A2_D.log run_C1_D.log run_C2_D.log  # 4/4
# If any G run shows opponent_sampling_mode=top_k within the first 10 log lines:
# ABORT that run, relaunch the pair (G+D). Continuing would drop treatment (b)
# and silently convert the run to "SBF-Lineage + two-pass refresh only" —
# indistinguishable from a v1 replication in the 05_results.md analysis.

# Per-role archive_reeval asymmetry
grep "archive_reeval=True"  run_A1_D.log run_A2_D.log run_C1_D.log run_C2_D.log  # 4/4 (D uses cache)
grep "archive_reeval=False" run_A1_G.log run_A2_G.log run_C1_G.log run_C2_G.log  # 4/4 (G no-cache)

# Per-role refresh_order asymmetry (bucketed on D to fix cross-program tracker race)
grep "Bucketed refresh"      run_A1_D.log run_A2_D.log run_C1_D.log run_C2_D.log  # ≥1/run after gen 2
! grep "Bucketed refresh"    run_A1_G.log run_A2_G.log run_C1_G.log run_C2_G.log  # 0/4 (G stays fifo)

# Per-role refresh_passes asymmetry (2 on D to close descendant staleness)
grep "Multi-pass refresh done.*2 passes" run_A1_D.log run_A2_D.log run_C1_D.log run_C2_D.log  # ≥1/run after gen 2
! grep "Multi-pass refresh done"         run_A1_G.log run_A2_G.log run_C1_G.log run_C2_G.log  # 0/4 (G passes=1)

# Role and feedback mode
grep "\[AsymmetricPipeline\].*role=(constructor|improver)"                  # 8/8
grep "\[AsymmetricPipeline\].*feedback=(composition|gradient_in_prompt)"   # 8/8
grep "\[ProgressBasedSyncHook\] Init.*drift_cap=100000"                    # 8/8
```

### 12.2 Runtime verification (gen 5+)

```bash
# D runs only (improver): SBF-Lineage must be active and keeping parents
grep "\[LineageStage:SharedBenchmark\] kept" run_A1_D.log run_A2_D.log run_C1_D.log run_C2_D.log
# expect ≥1 hit per D-run log per gen after gen 3, "kept X/Y" with X ≥ 1 for ≥50% of calls

# Base LineageStage log line must be ABSENT on D (replace_stage worked)
! grep "\[LineageStage\] program=" run_A1_D.log

# D cache invalidation working: expect periodic FetchOpponentResults cache-miss bursts
# correlated with top-1 G rotations (diagnostic, not pass/fail)
grep "InputHashCache.*miss" run_A1_D.log
```

### 12.3 Extra overrides per run

Per-role overrides (injected via `experiment.yaml:runs[*].extra_overrides`):

| Override | G runs | D runs |
|----------|--------|--------|
| `opponent_sampling_mode` | `softmax` | `top_k` |
| `pipeline_builder.archive_reeval` | `false` | `true` |
| `engine_config.refresh_order` | `fifo` (default; may be omitted) | `generation_bucketed` |
| `engine_config.refresh_passes` | `1` (default; may be omitted) | `2` |
| `opponent_result_mode` | `exec` | `cached` (v1 setting, preserved) |
| `population_role` | `constructor` | `improver` (v1 setting, preserved) |

### 12.4 Pinned contract

```yaml
pinned:
  pre_step_hook.drift_cap: 100000
  inner_iterations: 1
  n_opponents: 1
  source_prompt_k: 1
  pre_step_hook.sync_every_n_epochs: 1
  num_parents: 1
  max_elites_per_generation: 8
  max_mutations_per_generation: 8
  mutation_mode: rewrite
  max_generations: 200
  pipeline_builder.lineage_filter.min_shared: 1                 # NEW vs v1
  pipeline_builder.lineage_filter.inject_shared_evidence: true  # NEW vs v1
  # opponent_sampling_mode and pipeline_builder.archive_reeval are per-role
  # (see 12.3 extra_overrides table) — NOT in shared pins.
```

---

## 13. Pre-Registered Analysis Plan

### 13.1 Primary

μ_v2_G (best-ever actual_fitness across 4 G runs) vs μ_v1_G=0.03413. Welch t-test, bootstrap 95% CI.

### 13.2 Per-arm breakdown

Split by Composition vs Gradient-in-prompt. Report μ per arm to detect arm-specific signal.

### 13.3 SBF-Lineage efficacy diagnostic

Report `kept/total` ratio per D run per 10-gen bucket. Interpret:
- kept/total high (>50%) + signal improves → SBF-Lineage plausibly helpful
- kept/total low (<20%) + signal improves → SOFTMAX likely owns the delta
- kept/total high + no signal → SBF-Lineage working but not driving signal

### 13.4 D cache-invalidation cadence diagnostic

D runs use `archive_reeval=true` + `top_k` → InputHashCache on FetchOpponentResults. Report cache miss rate per D run per 10-gen bucket and correlate with G's top-1 rotation events (from G's `HOF_ROTATE` log if enabled, or by inspecting G's best-so-far trace). Expected: cache misses cluster around top-1 G flips, indicating D is correctly re-scoring against the new top-1.

### 13.5 I-17 gen-1 archive sanity check

Query each G-DB for `is_root=True ∧ generation=1` programs. Expect small count (gen-1 cold-start mutations only), NOT the 143/144 inflated count from v1 pre-fix.

---

## 14. Deviations from Pre-Registration

None yet. Any deviation will be logged in `04_issues_log.md` before 05_results.md is written.

---

## 15. KF-07 Deadlock Safety

`drift_cap=100000` is deliberately larger than any realistic per-run program count (~200 gens × 8 mutations ≈ 1600 < 100_000). The `ProgressBasedSyncHook` is retained as safety net only — mutual-wait is impossible by construction.

---

## Monitoring

Reuse v1's `control_plane.watchdog` config (plugin=adversarial, arms-race + comparison plots, alert thresholds invalidity_rate=0.75 / stagnation_window=10 / generation_gap_threshold=5). Event suppression list (v1): `HOF_FETCH`, `HOF_ROTATE`, `CELL_PICK`, `TRACKER_WRITE`. Watchdog polls every 1h; rolling PR comment every 24h.

Anomaly detector cron: every 30 min (per user directive).
