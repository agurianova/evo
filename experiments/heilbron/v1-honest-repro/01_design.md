# Experimental Design: heilbron/v1-honest-repro

**Date**: 2026-04-26
**Researcher**: Khrulkov V.
**Status**: Approved (researcher gate, post-17-question interview)
**Branch**: `exp/heilbron/v1-honest-repro`
**Prereg commit**: `25470e37` (main HEAD at branch-off)

---

## 1. Research Question

Does v1's adversarial co-evolution setup (PR #204 / commit `04bd5e69`,
heilbron/asymmetric-iterations) reproduce the SOTA result `actual_fitness ≈ 0.03648`
**on current main code without commit revert**, given that we restore v1's
fitness-landscape semantics (binary G resistance + linear D scoring) and disable
the post-v1 SBF-LineageStage filter?

This is a **reproducibility stress test**, not a hypothesis test. We are
identifying which library drift between commit `562a1210` (v1 prereg) and
`25470e37` (current main) is load-bearing for the v1 SOTA result.

## 2. Hypotheses

- **H₀ (null)**: With the v1 fitness landscape restored verbatim and SBF disabled,
  current main code reaches 0.03648 in at least one G run (matches v1 SOTA).
- **H₁ (alt)**: Even with the v1 landscape restored, current main produces a
  measurable shift in the G actual_fitness distribution — implying that some
  drift element NOT covered by the 17-decision interview (e.g. the
  ConfigurableAggregator's mean-reduction over K=1, the now-mandatory
  `(metrics, artifact)` evaluate.py contract, or unrelated engine churn) is
  load-bearing.

## 3. Independent Variable(s)

This is **not an IV experiment**. We are pinning every parameter we can identify
to v1's value, then running and comparing distributions. The "treatment" is
"current main + v1 landscape pins"; the "control" is the v1 historical record
(`heilbron/asymmetric-iterations` PR #204 = `actual_fitness=0.03648`).

| Pinned-to-v1 element | v1 value | New experiment value |
|----------------------|----------|----------------------|
| Resistance scoring (G) | binary `1.0 if delta<=0 else 0.0` | binary (Q13 scoped edit at evaluate.py:105) |
| Improvement scoring (D) | linear `min(max(δ,0)/Q_MAX, 1.0)` | linear (already current; docstring fixed) |
| Task description prose | v1 verbatim from `562a1210` | restored from git (Q11, Q12) |
| metrics.yaml | v1 verbatim from `562a1210` | restored from git (Q13, Q14) |
| `archive_reeval` | false | false (Q5) |
| `disable_lineage_on_improver` | (kwarg didn't exist; default behavior) | false (Q8 — keep LineageStage on D, matching v1) |
| `lineage_filter` (SBF) | (kwarg didn't exist; no SBF filter) | `null` (Q16 — standard LineageStage, no SBF) |
| `opponent_sampling_mode` | (kwarg didn't exist; effective top_k) | top_k (Q3, current default) |
| `refresh_passes` | (field didn't exist; engine did 1 sweep) | 1 (Q6, current default) |
| `refresh_order` | fifo | fifo (Q7) |
| `n_opponents` / `source_prompt_k` | 1 / 1 | 1 / 1 |
| `inner_iterations` | 1 | 1 |
| `drift_cap` | 100000 (no-op) | 100000 |
| `stage_timeout` | 3000 | 900 (Q1 — explicit shorter budget) |
| `dag_timeout` | 7200 | 3600 (Q2 — explicit shorter budget) |
| `aggregator` | (didn't exist; raw dict) | `heilbron_constructor` / `heilbron_improver` (Q15 — mandatory on current code; mean-reduction over K=1 ≡ v1 scalar) |

**Known irreducible drift** (cannot pin to v1 — current main only):
1. `ConfigurableAggregator` infrastructure (added post-v1; mandatory now). Under
   K=1 opponent, `mean(resistance_score)` = the v1 scalar — semantically equivalent.
2. evaluate.py `(metrics, artifact)` tuple contract (added post-v1). Same data,
   different ABI.
3. Library code churn between `562a1210` and `25470e37` (300+ commits). Not
   individually pinnable.

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| best-ever `actual_fitness` per G run | `max` over `metrics:history:program_metrics:valid_frontier_fitness` Redis list | YES |
| Count of G runs reaching 0.0365 | comparison against v1's 3-out-of-4 SOTA-hit rate | secondary |
| Generation rate ratio D/G | `total_generations` D / total_generations G at wallclock budget exhaustion | secondary (drift diagnostic) |

**Primary metric**: best-ever `actual_fitness` across the 4 G runs (A1_G, A2_G, C1_G, C2_G).

**Decision rule**:
- Best G ≥ 0.0364 (within 0.0001 of v1 SOTA) in ≥1 run → **H₀ supported** (drift not load-bearing).
- Best G ≥ 0.0364 in 0 runs but median G ≥ v1 baseline mean (0.03574) → **partial reproduction**.
- Best G < 0.03574 across all 4 runs → **H₁ confirmed** (drift IS load-bearing).

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Model | Qwen3-235B-A22B-Thinking-2507 | identical to v1 |
| temperature / top_p / top_k | 0.6 / 0.95 / 20 | identical to v1 (`config/experiment/base.yaml`) |
| max_tokens | 81920 | identical to v1 |
| max_elites_per_generation | 8 | identical to v1 (heilbron task_group) |
| max_mutations_per_generation | 8 | identical to v1 |
| num_parents | 1 | identical to v1 |
| primary_resolution (MAP-Elites) | 150 | identical to v1 |
| LLM proxy URL | `http://10.232.30.185:4000/v1` | identical to v1 |
| max_generations | 200 | identical to v1 |
| Number of runs | 8 (4 pairs × 2 arms) | identical to v1 |
| Server | 10.232.30.185 | identical to v1 |

## 6. Run Design Table

| Label | DB | Prefix | Role | Arm | Opponent DB | Aggregator |
|-------|----|----|-----|------|-----|-----|
| A1_G | 1 | heilbron_v1_honest/pop_a | constructor | composition | 2 | heilbron_constructor |
| A1_D | 2 | heilbron_v1_honest/pop_b | improver | composition | 1 | heilbron_improver |
| A2_G | 3 | heilbron_v1_honest/pop_a | constructor | composition | 4 | heilbron_constructor |
| A2_D | 4 | heilbron_v1_honest/pop_b | improver | composition | 3 | heilbron_improver |
| C1_G | 5 | heilbron_v1_honest/pop_a | constructor | gradient_in_prompt | 6 | heilbron_constructor |
| C1_D | 6 | heilbron_v1_honest/pop_b | improver | gradient_in_prompt | 5 | heilbron_improver |
| C2_G | 7 | heilbron_v1_honest/pop_a | constructor | gradient_in_prompt | 8 | heilbron_constructor |
| C2_D | 8 | heilbron_v1_honest/pop_b | improver | gradient_in_prompt | 7 | heilbron_improver |

**Why this layout matches v1**: same 4 G/D pairs across the same 2 arms (Composition,
Gradient-in-prompt), same DB pairing (G⇄D mirror), same prefixes (modulo `heilbron_repro_v1` →
`heilbron_v1_honest` rename), same server.

## 7. Statistical Plan

N=4 G runs per condition is too small for power-style testing. Treat as
**descriptive comparison** against v1's historical 4-G-run distribution
(0.03648, 0.0365×, 0.0365×, plus the C2_G under 0.0357 outlier).

Report: best-ever per run, mean ± std across 4 G runs, count reaching ≥0.0364.

## 8. Stopping Rule

Pre-registered stopping rule: `stopper=max_generations`, `max_generations=200`.

No early-stop on plateau; no early-stop on success. The whole question is
"does current main reach v1's outcome distribution at 200 generations".

## 9. Treatment Verification

Implementation provides observable evidence the v1-honest treatment is applied:

| Check | Evidence | Where verified |
|-------|----------|---------------|
| pipeline=heilbron_v1_honest | Hydra cfg dump line `pipeline: heilbron_v1_honest` | `LAUNCH_PREVIEW.md` + `cfg_run_*.txt` + log grep |
| binary resistance | `resistance_score` values in Redis are exactly 0.0 or 1.0 (no intermediate floats) | `treatment_checks` smoke-test inspection |
| linear D score | `score` values match `min(max(δ,0)/Q_MAX, 1.0)` | smoke check |
| SBF disabled | log absent of `SharedBenchmarkFilteredLineageStage` and `SBF-Lineage` strings | `treatment_checks.log_pattern_absent` |
| LineageStage present | log emits `[AsymmetricPipeline] adding LineageStage` (or equivalent) | smoke verification |
| v1 task_description | sha256 of forked `task_description.txt` matches v1's `562a1210` checksum | `dataset_snapshot.json` |
| aggregator routing active | log emits `[ParseMetricsStage] aggregator=heilbron_constructor` (or improver) | smoke verification |
| drift_cap=100000 | `[ProgressBasedSyncHook] Init.*drift_cap=100000` | `treatment_checks.log_pattern_present` |

## 10. Codebase Map

**Treatment-touching files (created/modified)**:
- `problems/heilbron_v1_honest/pop_a/evaluate.py` — pop_a/evaluate.py:105 binary `resistance_score = float(delta <= 0.0)`
- `problems/heilbron_v1_honest/pop_a/{task_description.txt, metrics.yaml}` — restored from `562a1210`
- `problems/heilbron_v1_honest/pop_b/evaluate.py` — already linear; docstring fixed
- `problems/heilbron_v1_honest/pop_b/{task_description.txt, metrics.yaml}` — restored from `562a1210`
- `config/pipeline/heilbron_v1_honest.yaml` — new pipeline; `lineage_filter: null`, drift_cap=100000

**Reused unchanged**:
- `config/aggregator/heilbron_constructor.yaml` (existing — `mean(resistance_score)` over K=1 ≡ v1 binary scalar)
- `config/aggregator/heilbron_improver.yaml` (existing — `mean(score)` over K=1 ≡ v1 linear scalar)
- `gigaevo/adversarial/asymmetric_pipeline.py` (`AdversarialAsymmetricPipelineBuilder` — `lineage_filter=None` branch routes to standard LineageStage)
- `gigaevo/adversarial/sync.py` (`ProgressBasedSyncHook` — drift_cap=100000 path)
- `gigaevo/adversarial/composition_injection.py` (Arm A G post-step hook)
- `config/pipeline/adversarial_asymmetric.yaml` (parent of heilbron_v1_honest.yaml)

## 11. Monitoring (watchdog)

Plugin: `adversarial`. Plot commands: arms-race (per pair) + comparison (G runs
with frontier annotation up to 3, D runs excluded from frontier line).
Alert thresholds: invalidity_rate=0.75, stagnation_window=10,
generation_gap_threshold=5. Excluded events: HOF_FETCH, HOF_ROTATE, CELL_PICK,
TRACKER_WRITE.

## 12. Deviations Anticipated

None pre-registered.

### 12a. Deviation discovered at launch (2026-04-26 03:09 UTC)

**Additional D-side override required: `pipeline_builder.dg_tracker=null`.**

The original Q16 spec stated only `pipeline_builder.lineage_filter: null` would
disable SBF on D and reproduce v1 behaviour. At the current main commit
(25470e37), `AdversarialAsymmetricPipelineBuilder` couples `dg_tracker` and
`lineage_filter` for the improver role: when role=improver and
`dg_tracker is not None`, `_resolve_lineage_filter` rejects `lineage_filter=None`
with `ValueError('lineage_filter.aggregator required — no silent fallback')`.

The parent yaml `config/pipeline/adversarial_asymmetric.yaml` wires
`pipeline_builder.dg_tracker: ${dg_tracker}` (a real `DGImprovementTracker`).
Hydra's leaf-level override means the child yaml's
`pipeline_builder.lineage_filter: null` does not turn off `dg_tracker`, so all
4 D runs crashed at instantiation in the first launch attempt.

**Fix**: appended `- pipeline_builder.dg_tracker=null` to all 4 D-side
`extra_overrides` in `experiment.yaml`. This is arguably MORE faithful to v1
(commit 7c70e7d4), which had no `DGImprovementTracker` at all — but it represents
a deeper rip-out than originally pre-registered. Re-launched 03:23:12 UTC; all
4 D runs now log `[AsymmetricPipeline] role=improver ... dg_tracker=no`,
zero errors, all 8 PIDs alive, all 8 Redis DBs populating.

Composition-injection hook on G is unaffected: it uses G's own `dg_tracker`
under G's Redis prefix, not D's. D's `dg_tracker` writes were unused by the
composition path, so disabling them is a true no-op for the hypothesis-relevant
behaviour.

See `04_issues_log.md#I-03` for full root-cause analysis. To be reported in
the Deviations section of `05_results.md`.
