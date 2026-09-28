# Pre-Registration: heilbron/adversarial-repro-v2

**Date**: 2026-04-22
**Protocol version**: 1.0
**Pre-registration commit**: `eda83033`
**GitHub PR**: `<filled at PR>` (branch: `exp/heilbron/adversarial-repro-v2`)
**Tracking issue**: N/A (add if created)
**Design doc**: `experiments/heilbron/adversarial-repro-v2/01_design.md`
**Review doc**: `experiments/heilbron/adversarial-repro-v2/02_review.md` (verdict: APPROVED after Revision 1)
**Literature brief**: `experiments/heilbron/adversarial-repro-v2/literature_brief.md` (carried forward from v1 — see 01_design.md §1 "Literature-brief scope note" for coverage caveats)
**Codebase map**: `experiments/heilbron/adversarial-repro-v2/codebase_map.md`
**Dataset snapshot**: `experiments/heilbron/adversarial-repro-v2/dataset_snapshot.json`
**Evaluation script**: N/A — Heilbronn N=11 has no test split (geometric optimization)

---

## Hypothesis

**H₀**: μ_v2_G ≤ μ_v1_G + 0.0005 — the three stacked improvements (SharedBenchmarkFilteredLineageStage on D, OpponentSamplingMode.SOFTMAX on G with TOP_K on D + two-pass bucketed D-refresh, I-16/I-17 fixes) do not move the mean best-ever G `actual_fitness` beyond v1-era noise.

**H₁**: μ_v2_G ≥ μ_v1_G + 0.002 — the stacked improvements recover ≥2pp toward v1-era SOTA 0.03650.

**Primary metric**: best-ever `actual_fitness` per G run, averaged across the 4 G runs (A1_G, A2_G, C1_G, C2_G).
**Baseline**: μ_v1_G = 0.03413 (v1 post-relaunch grand mean, `heilbron/adversarial-repro-v1/05_results.md` §5).
**Significance threshold**: No formal α. N=4 gives ~30% power for a 0.002pp effect at σ≈0.0012; primary inference is effect-size vs the bands in 01_design.md §2.

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

All runs also pass: `evolution=steady_state stopper=max_generations max_generations=200`.
Model: `Qwen3-235B-A22B-Thinking-2507` across all runs. LLM proxy: `http://10.232.30.185:4000/v1`.

Pipeline/problem names are inherited verbatim from v1 — the v2 treatments are expressed purely as runtime overrides (no new pipeline YAML, no new problem dir). Redis DBs 1–8 will be flushed cleanly before launch, so `heilbron_repro_v1/pop_{a,b}` key prefixes are safe to reuse.

---

## Controlled Variables

| Field | Value | Source |
|-------|-------|--------|
| `pipeline` | `heilbron_repro_v1` | Same as v1 (sets `drift_cap=100000`, K=1, n_opponents=1, source_prompt_k=1) |
| `evolution` | `steady_state` | v1 |
| `stopper` | `max_generations` | v1 |
| `max_generations` | 200 | v1 |
| `drift_cap` | 100000 | v1 (no-op cap) |
| `sync_every_n_epochs` | 1 | v1 |
| `inner_iterations` | 1 | v1 |
| `n_opponents` | 1 | v1 |
| `source_prompt_k` | 1 | v1 |
| `num_parents` | 1 | v1 |
| `max_elites_per_generation` | 8 | v1 |
| `max_mutations_per_generation` | 8 | v1 |
| `mutation_mode` | rewrite | v1 |
| `model_name` | Qwen3-235B-A22B-Thinking-2507 | v1 |
| `pipeline_builder.lineage_filter.min_shared` | 1 | NEW (v2) — SBF-Lineage default, pinned |
| `pipeline_builder.lineage_filter.inject_shared_evidence` | true | NEW (v2) — SBF-Lineage default, pinned |

### Asymmetric per-role variables (NEW vs v1 — not shared pins)

| Parameter | G runs | D runs |
|-----------|--------|--------|
| `opponent_sampling_mode` | `softmax` | `top_k` |
| `pipeline_builder.archive_reeval` | `false` | `true` |
| `engine_config.refresh_order` | default (`fifo`) | `generation_bucketed` |
| `engine_config.refresh_passes` | default (1) | `2` |

---

## Reproducibility Notes

Same as v1: stochastic LLM-based evolution with `random.sample` failure sampling, temperature=0.6 nucleus sampling, non-deterministic GPU float, proxy-level drift. No global seed. Cross-experiment comparison via effect-size thresholds (01_design.md §2).

**Library drift vs v1** (see 01_design.md §9 confound #8): v1 ran on commit `04bd5e69`; v2 runs on the v2 pre-registration commit (current HEAD of `exp/heilbron/adversarial-repro-v1` + this commit). `environment_freeze.txt` captures the exact v2 commit SHA and the full pip environment. This drift is **symmetric across all 8 v2 runs** — it affects the v1↔v2 between-experiment comparison, not within-v2 arm differences.

---

## Dataset Checksums

Anchor: `experiments/heilbron/adversarial-repro-v2/dataset_snapshot.json` (carried forward from v1; same frozen problem files at `problems/heilbron_repro_v1/pop_{a,b}/`).

Verify integrity before launch:

```bash
/home/jovyan/.mlspace/envs/evo/bin/python3 -c "
import hashlib, json, sys
from pathlib import Path
snap = json.loads(Path('experiments/heilbron/adversarial-repro-v2/dataset_snapshot.json').read_text())
for f, expected in snap['file_checksums'].items():
    actual = hashlib.sha256(Path(f).read_bytes()).hexdigest()[:16]
    if actual != expected:
        sys.exit(f'MISMATCH: {f}  expected={expected}  got={actual}')
print(f'OK — all {len(snap[\"file_checksums\"])} files match snapshot.')
"
```

---

## Success Criteria

Per 01_design.md §2 effect-size thresholds:

| Outcome | Verdict |
|---------|---------|
| μ_G ≥ 0.0365 AND ≥ 1/4 G runs at 0.0365 | **POSITIVE** — original-v1 result recovered |
| μ_G ≥ 0.0355 AND < 0.0365 | **SUGGESTIVE** — directional improvement |
| μ_G within 0.001 of μ_v1_G (0.03313–0.03513) | **NULL** — stacked fixes do not help |
| μ_G < 0.0330 | **REGRESSIVE** — active regression |

**Abandon criterion**: μ_G < 0.0330 AND no G run reaches 0.0350 across all 800 gens → launch individual ablations (SOFTMAX-only, SBF-only).

**Invalidity criteria** (any one → INVALID regardless of fitness):
- Hydra `--cfg job` pre-launch gate (01_design.md §12.0) shows missing/wrong `opponent_sampling_mode`, `archive_reeval`, `refresh_order`, or `refresh_passes` on any run.
- Startup verification (01_design.md §12.1) fails: any G run shows `opponent_sampling_mode=top_k`, or any D run shows `opponent_sampling_mode=softmax`, or D runs do not emit `Multi-pass refresh done.*2 passes` after gen 2.
- `drift_cap=100000` missing from any startup log.
- Fewer than 3/4 G runs reach gen 100.
- Cross-DB Redis key contamination detected.

---

## Monitoring Plan

`max_generations`: 200
`stopper`: `max_generations` (no plateau, no wallclock early-stop)

- **Gen 3 (~2%)**: smoke check — all 8 PIDs alive, Redis keys growing, startup logs show `drift_cap=100000`, `opponent_sampling_mode=softmax|top_k` per role, D logs show `[LineageStage:SharedBenchmark] kept`, D logs show `Bucketed refresh` + `Multi-pass refresh done.*2 passes`.
- **Gen 20 (~10%)**: checkpoint — per-run best `actual_fitness`, SBF-Lineage `kept/total` ratio per D run, D/G generation ratio.
- **Gen 50 (~25%)**: mid-run checkpoint analysis.
- **Gen 100 (~50%)**: midpoint — minimum completion threshold.
- **Gen 200 (100%)**: final analysis — best-ever `actual_fitness` per G run, mean / bootstrap-95% CI, per-arm breakdown, SBF efficacy diagnostic (13.3), D cache-invalidation cadence (13.4), I-17 gen-1 sanity check (13.5).

**Early termination rule**: none per run. Full-experiment abort only if (a) 4+ of 8 processes die within first 2h, or (b) watchdog detects `invalidity_rate>0.75` AND `stagnation_window>10` on ≥2 G runs.

**Treatment verification checks** (all must pass before the experiment is considered validly launched; full list in 01_design.md §12.0 / §12.1 / §12.2):
1. `--cfg job` renders `opponent_sampling_mode=softmax` + `archive_reeval=false` for all 4 G runs; `top_k` + `true` + `refresh_order=generation_bucketed` + `refresh_passes=2` for all 4 D runs.
2. Startup log on every run shows `[ProgressBasedSyncHook] Init.*drift_cap=100000`.
3. Every D log shows `[LineageStage:SharedBenchmark] kept X/Y parents` after gen 3, with X≥1 for ≥50% of calls.
4. Every D log shows `Multi-pass refresh done.*2 passes` after gen 2; no G log shows `Multi-pass refresh done`.
5. No `drift_cap exceeded` anywhere.

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
