# Pre-Registration: heilbron/d-smoothing-minimal

**Date**: 2026-04-24
**Protocol version**: 1.0
**Pre-registration commit**: `<filled at commit>`
**GitHub PR**: `<filled at PR>` (branch: `exp/heilbron/d-smoothing-minimal`)
**Tracking issue**: N/A (add if created)
**Design doc**: `experiments/heilbron/d-smoothing-minimal/01_design.md`
**Review doc**: `experiments/heilbron/d-smoothing-minimal/02_review.md` (verdict: APPROVED after Round 2)
**Literature brief**: `experiments/heilbron/d-smoothing-minimal/literature_brief.md` (Lehre & Lin 2024, Liapis 2025)
**Codebase map**: `experiments/heilbron/d-smoothing-minimal/codebase_map.md` (feasibility: GREEN)
**Dataset snapshot**: `experiments/heilbron/d-smoothing-minimal/dataset_snapshot.json`
**Evaluation script**: N/A — Heilbronn N=11 has no test split (geometric optimization)

---

## Hypothesis

**H₀**: μ_G ≤ μ_v2_G + 0.0005 — replacing D-side hard-floor scoring with tanh smoothing does not move the mean best-ever G `actual_fitness` beyond v2-era noise (0.03315).

**H₁**: μ_G ≥ μ_v2_G + 0.0020 — D-side fitness smoothing lifts the G-population mean at least 2pp toward SOTA (0.0365).

**Primary metric**: best-ever `actual_fitness` per G run, averaged across the 4 G runs (A1_G, A2_G, C1_G, C2_G).

**Baseline**: μ_v2_G = 0.03315 (adversarial-repro-v2 grand mean, 4 G runs, `heilbron/adversarial-repro-v2/05_results.md`).

**Secondary baselines** (for threshold anchoring):
- μ_v1_G = 0.03413 (adversarial-repro-v1)
- μ_baseline-repro = 0.03449 (solo MAP-Elites, no adversarial)
- asymmetric-iterations peaks: 0.03648 (A1_G, gen 8), 0.03650 (C2_G, gen 10) — SOTA reference

**Significance threshold**: No formal α. N=4 gives ~30–40% power for a 0.002 raw-delta effect at σ≈0.0012; primary inference is effect-size vs the bands in 01_design.md §2.1.

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `problem.name` | `feedback_mode` | `population_role` | Opp DB | Extra per-role overrides |
|-----|-------|-----------|-----------|---------------|-----------------|-------------------|--------|--------------------------|
| 1 | A1_G | 1 | heilbron_repro_v1 | heilbron_repro_v1/pop_a | composition | constructor | 2 | `opponent_sampling_mode=softmax pipeline_builder.archive_reeval=false` |
| 2 | A1_D | 2 | heilbron_repro_v1 | heilbron_repro_v1/pop_b | composition | improver | 1 | `opponent_sampling_mode=top_k pipeline_builder.archive_reeval=true engine_config.refresh_order=generation_bucketed engine_config.refresh_passes=2` |
| 3 | A2_G | 3 | heilbron_repro_v1 | heilbron_repro_v1/pop_a | composition | constructor | 4 | same as A1_G |
| 4 | A2_D | 4 | heilbron_repro_v1 | heilbron_repro_v1/pop_b | composition | improver | 3 | same as A1_D |
| 5 | C1_G | 5 | heilbron_repro_v1 | heilbron_repro_v1/pop_a | gradient_in_prompt | constructor | 6 | same as A1_G |
| 6 | C1_D | 6 | heilbron_repro_v1 | heilbron_repro_v1/pop_b | gradient_in_prompt | improver | 5 | same as A1_D |
| 7 | C2_G | 7 | heilbron_repro_v1 | heilbron_repro_v1/pop_a | gradient_in_prompt | constructor | 8 | same as A1_G |
| 8 | C2_D | 8 | heilbron_repro_v1 | heilbron_repro_v1/pop_b | gradient_in_prompt | improver | 7 | same as A1_D |

All runs also pass: `evolution=steady_state stopper=max_generations max_generations=200 stage_timeout=900 dag_timeout=3600`.
Model: `Qwen3-235B-A22B-Thinking-2507` across all runs. LLM proxy: `http://10.232.30.185:4000/v1`.

Pipeline/problem names inherited verbatim from v1 — the treatment (D fitness smoothing) is a **code change** to `problems/heilbron_repro_v1/pop_b/evaluate.py`, not a runtime override. Redis DBs 1–8 will be flushed cleanly before launch.

---

## The Treatment — One File, Four Touch-Points

**File**: `problems/heilbron_repro_v1/pop_b/evaluate.py`

| Touch-point | Current (v2) | Proposed |
|---|---|---|
| Lines 96–99 (happy path) | `delta = max(raw_delta, 0.0); score = min(delta/Q_MAX, 1.0)` | `delta = raw_delta; score = 0.5 * (np.tanh(raw_delta / Q_MAX) + 1.0)` |
| Lines 117–118 (exception branch) | `score = 0.0` | `score = 0.5` (neutral under tanh — prevents re-introducing the hole; see 01_design.md §3 m1 behavioral note) |
| Line 7 docstring | "binary improvement scoring" | updated to reflect tanh smoothing |
| `per_opp_metrics["delta"]` | clamped (≥0) | signed `raw_delta` (admits negative gradient) |

**Frozen (deliberately not changed)**:
- `problems/heilbron_repro_v1/pop_b/metrics.yaml` fitness description text — **kept verbatim from v2** (prompt-visible, `include_in_prompts: true`; any change would be a hidden second IV).
- `mean_improvement_raw.lower_bound` in `metrics.yaml`: updated from `0.0` to `-0.0365` (not prompt-visible; `include_in_prompts: false`; required for the signed `delta` semantics change).

---

## Controlled Variables (identical to v2 except stage_timeout)

| Field | Value | Source |
|-------|-------|--------|
| `pipeline` | `heilbron_repro_v1` | v2 |
| `evolution` | `steady_state` | v2 |
| `stopper` | `max_generations` | v2 |
| `max_generations` | 200 | v2 |
| `stage_timeout` | **900** (15 min) | **v2 actual launch.sh** (manifest said 3000; user-confirmed 900) |
| `dag_timeout` | **3600** (1h) | **v2 actual launch.sh** (manifest said 7200; user-confirmed 3600) |
| `drift_cap` | 100000 | v2 (no-op cap) |
| `sync_every_n_epochs` | 1 | v2 |
| `inner_iterations` | 1 | v2 |
| `n_opponents` | 1 | v2 |
| `source_prompt_k` | 1 | v2 |
| `num_parents` | 1 | v2 |
| `max_elites_per_generation` | 8 | v2 |
| `max_mutations_per_generation` | 8 | v2 |
| `mutation_mode` | rewrite | v2 |
| `model_name` | Qwen3-235B-A22B-Thinking-2507 | v2 |
| `pipeline_builder.lineage_filter.min_shared` | 1 | v2 (SBF-Lineage) |
| `pipeline_builder.lineage_filter.inject_shared_evidence` | true | v2 (SBF-Lineage) |

### Asymmetric per-role variables (unchanged from v2)

| Parameter | G runs | D runs |
|-----------|--------|--------|
| `opponent_sampling_mode` | `softmax` | `top_k` |
| `pipeline_builder.archive_reeval` | `false` | `true` |
| `engine_config.refresh_order` | default (`fifo`) | `generation_bucketed` |
| `engine_config.refresh_passes` | default (1) | `2` |

---

## Confounds (declared)

1. **G-smoothing hotfix already landed (commit 2de8267e, PR #219, 2026-04-24)** — this is the first experiment running on the smoothed G form `resistance_score = 1.0 - min(delta/Q_MAX, 1.0)` at `pop_a/evaluate.py:110`. Any μ_G lift over v2 could be attributed to (G-smoothing alone) OR (D-smoothing alone) OR (both). Clean attribution to D requires `adversarial_021` (3-arm with rolled-back G). This experiment reports the combined-treatment effect.

2. **Library drift vs asymmetric-iterations (SOTA comparator)** — asymmetric-iterations ran on `04bd5e69`; this experiment runs on the current HEAD (`2de8267e`+). Drift is symmetric across all 8 runs within the experiment but affects the cross-experiment SOTA comparison.

3. **Signed `delta` semantics** — `per_opp_metrics["delta"]` changes from clamped-nonnegative to signed. Downstream consumers traced in 01_design.md §3 m2: `DGTrackerStage`, `DGImprovementTracker.record_batch`, `mean_improvement_raw` aggregator. Bound update required on `mean_improvement_raw.lower_bound` (0.0 → -0.0365).

---

## Reproducibility Notes

Stochastic LLM-based evolution (`random.sample` failure sampling, temperature=0.6 nucleus, non-deterministic GPU float, proxy-level drift). No global seed.

**Code state anchor**: `dataset_snapshot.json` pins SHA-256 of 15 files under `problems/heilbron_repro_v1/` at commit `2de8267e` (current main, post-G-hotfix). The treatment commit will modify `pop_b/evaluate.py` only; verify integrity of other 14 files post-implementation.

---

## Dataset Checksums

```bash
/home/jovyan/.mlspace/envs/evo/bin/python3 -c "
import hashlib, json, sys
from pathlib import Path
snap = json.loads(Path('experiments/heilbron/d-smoothing-minimal/dataset_snapshot.json').read_text())
mismatches = []
for f, expected in snap['file_checksums'].items():
    actual = hashlib.sha256(Path(f).read_bytes()).hexdigest()[:16]
    if actual != expected:
        mismatches.append(f'{f}  expected={expected}  got={actual}')
if mismatches:
    sys.exit('MISMATCH:\n' + '\n'.join(mismatches))
print(f'OK — all {len(snap[\"file_checksums\"])} files match snapshot.')
"
```

At implementation time, `pop_b/evaluate.py` will mismatch (by design — that's the treatment). `pop_b/metrics.yaml` may also mismatch for the `mean_improvement_raw.lower_bound` update (required by signed-delta semantics). All other 13 files must match.

---

## Success Criteria

Per 01_design.md §2.1 effect-size thresholds:

| μ_G (best-ever actual_fitness) | Verdict |
|---|---|
| ≥ 0.03550 | **POSITIVE** — D-smoothing is the binding lever; D point-mass broken |
| ≥ 0.03449 AND < 0.03550 | **SUGGESTIVE** — directional improvement past baseline-repro mean |
| 0.03200 – 0.03449 | **NULL** — D-smoothing alone insufficient |
| < 0.03200 | **REGRESSIVE** — acknowledged unreachable at N=4, σ=0.003 |

**Pre-registered mechanistic prediction (01_design.md §2.2a)** — D fitness distribution shape:

| Checkpoint | D-archive fraction in [0.1, 0.9] | Median D fitness | Variance floor | KDE non-degeneracy |
|---|---|---|---|---|
| gen 5 | ≥ 30% | in [0.3, 0.7] | σ² ≥ 0.005 | ≥ 3 modes or continuous |
| gen 20 | ≥ 50% | in [0.35, 0.75] | σ² ≥ 0.01 | continuous distribution |
| gen 50 | ≥ 60% | in [0.4, 0.8] | σ² ≥ 0.015 | continuous distribution |

**Treatment verification (code-application, definitional pass — 01_design.md §2.2)**:
- D-archive fraction at `fitness < 0.001` must be < **5%** at gen 5 across all 4 D runs.
- Median D fitness must fall in [0.3, 0.7].

**Abandon criterion**: If D point-mass drops below 5% (treatment applied) AND μ_G remains NULL (< 0.03449) → D-smoothing is not the binding lever. Next step: `adversarial_015` (full REDESIGN bundle) or library-drift bisection against asymmetric-iterations commit `04bd5e69`.

**Invalidity criteria** (any one → INVALID regardless of fitness):
- Hydra `--cfg job` pre-launch gate shows missing/wrong `opponent_sampling_mode`, `archive_reeval`, `refresh_order`, `refresh_passes` on any run.
- Startup verification fails: any G run shows `opponent_sampling_mode=top_k`, any D run shows `opponent_sampling_mode=softmax`, D runs do not emit `Multi-pass refresh done.*2 passes` after gen 2.
- `drift_cap=100000` missing from any startup log.
- `np.tanh` absent from `problems/heilbron_repro_v1/pop_b/evaluate.py` at launch time (treatment not applied).
- Smoke-test D-archive shows > 5% at fitness < 0.001 at gen 3 (tanh not taking effect).
- Fewer than 3/4 G runs reach gen 100.
- Cross-DB Redis key contamination detected.

---

## Monitoring Plan

`max_generations`: 200. `stopper`: `max_generations`. Wall-clock soft cap: 28h.

- **Gen 3 (~1.5%)**: smoke check — all 8 PIDs alive, Redis keys growing, startup logs show `drift_cap=100000`, `opponent_sampling_mode=softmax|top_k` per role, D logs show `[LineageStage:SharedBenchmark] kept`, D logs show `Bucketed refresh` + `Multi-pass refresh done.*2 passes`. **Treatment-specific**: D-fitness histogram < 5% at `fitness < 0.001`, median in [0.3, 0.7].
- **Gen 5**: mechanistic-prediction checkpoint #1 — D-archive fraction in [0.1, 0.9] ≥ 30%; variance σ² ≥ 0.005.
- **Gen 20 (~10%)**: mechanistic-prediction checkpoint #2 — distribution shape thresholds; SBF-Lineage `kept/total` ratio per D run; D/G generation ratio.
- **Gen 50 (~25%)**: mechanistic-prediction checkpoint #3 + mid-run checkpoint analysis (decision: continue or early-abandon based on primary metric trajectory).
- **Gen 100 (~50%)**: midpoint — minimum completion threshold.
- **Gen 200 (100%)** or **wall-clock 28h**: final analysis — best-ever `actual_fitness` per G run, mean / bootstrap-95% CI, per-arm breakdown, D point-mass fraction trajectory, D exception rate, SBF efficacy diagnostic, D cache-invalidation cadence.

**Early termination rule**: none per run (preserves v2 symmetry). Full-experiment abort only if (a) 4+ of 8 processes die within first 2h, or (b) watchdog detects `invalidity_rate>0.75` AND `stagnation_window>10` on ≥2 G runs.

**Treatment verification checks** (all must pass before experiment is considered validly launched; full list in 01_design.md §11):
1. `git diff` on launch commit shows `np.tanh` in `problems/heilbron_repro_v1/pop_b/evaluate.py`.
2. `--cfg job` renders correct per-role overrides.
3. Startup log on every run shows `[ProgressBasedSyncHook] Init.*drift_cap=100000`.
4. Every D log shows `[LineageStage:SharedBenchmark] kept X/Y parents` after gen 3.
5. Every D log shows `Multi-pass refresh done.*2 passes` after gen 2; no G log shows `Multi-pass refresh done`.
6. D-archive fitness histogram at gen 3: < 5% at `fitness < 0.001`, median in [0.3, 0.7].

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| A1_G | _tbd_ | _tbd_ | |
| A1_D | _tbd_ | _tbd_ | |
| A2_G | _tbd_ | _tbd_ | |
| A2_D | _tbd_ | _tbd_ | |
| C1_G | _tbd_ | _tbd_ | |
| C1_D | _tbd_ | _tbd_ | |
| C2_G | _tbd_ | _tbd_ | |
| C2_D | _tbd_ | _tbd_ | |

Watchdog PID: _tbd_
Anomaly detector cron ID: _tbd_
Launch commit: _tbd_

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|
| _tbd_ | _tbd_ | _tbd_ |

---

## Amendments

_(Add numbered entries here for any post-registration changes. Every amendment must explain why the pre-registered design was insufficient.)_
