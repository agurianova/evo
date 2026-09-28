# Pre-Registration: heilbron/d-tanh-no-lineage

**Date**: 2026-04-25
**Protocol version**: 1.0
**Pre-registration commit**: `<filled at PR-creation time>`
**GitHub PR**: #<number> (branch: `exp/heilbron/d-tanh-no-lineage`)
**Tracking issue**: TBD
**Design doc**: `experiments/heilbron/d-tanh-no-lineage/01_design.md`
**Review doc**: `experiments/heilbron/d-tanh-no-lineage/02_review.md` (Volkov verdict: **APPROVED**, round 4)
**Evaluation script**: N/A — Heilbron N=11 has no held-out test split (`problem.has_test_set: false`)

---

## Hypothesis

**H₀** — *Removing LineageStage from D's pipeline (on top of D-side tanh smoothing) does not lift G-side best-ever `actual_fitness` above the v2 NULL band.* Operationally: μ_G (mean across the 4 G runs of best-ever `actual_fitness` at gen 200) is statistically indistinguishable from the v2 baseline μ_G^v2 = 0.03315 (4 G runs).

**H₁** — *Removing LineageStage from D's pipeline (on top of D-side tanh smoothing) lifts μ_G above the v2 NULL band by closing the per-gen-rate asymmetry that aborted d-smoothing-minimal, allowing the tanh-induced D pressure to act on a non-stale G frontier.*

**Primary metric**: `actual_fitness` — best-ever min_area achieved across D opponent configs, reported as the 4-G-run mean at gen 200 (μ_G).

**Significance threshold**: α = 0.05 on a two-sample bootstrap of (4 G runs of this experiment) vs (4 G runs of v2). Practical-significance bar: μ_G − 0.03315 ≥ +0.0010 (≈ 1pp on the 0–0.0365 scale) with 95% CI excluding 0.

**Decision rule**:
- **POSITIVE** if μ_G − 0.03315 ≥ +0.0010 with 95% CI > 0
- **NEGATIVE/NULL** if 95% CI for the delta straddles 0 or μ_G ≤ 0.03315
- **REGRESSIVE** if μ_G < 0.03315 with 95% CI < 0

---

## Run Design Table

8 runs total: 4 G (constructor) + 4 D (improver), in 4 paired arms (A1, A2, C1, C2). All runs use the same `Qwen3-235B-A22B-Thinking-2507` model on `http://10.232.30.185:4000/v1` (LiteLLM proxy).

| Run   | Label | `redis.db` | `pipeline`              | `problem.name`                | `feedback_mode`     | Pair partner |
|-------|-------|------------|-------------------------|-------------------------------|---------------------|--------------|
| 1     | A1_G  | 1          | `heilbron_repro_v1`     | `heilbron_repro_v1/pop_a`     | composition         | A1_D (db=2)  |
| 2     | A1_D  | 2          | `heilbron_repro_v1`     | `heilbron_repro_v1/pop_b`     | composition         | A1_G (db=1)  |
| 3     | A2_G  | 3          | `heilbron_repro_v1`     | `heilbron_repro_v1/pop_a`     | composition         | A2_D (db=4)  |
| 4     | A2_D  | 4          | `heilbron_repro_v1`     | `heilbron_repro_v1/pop_b`     | composition         | A2_G (db=3)  |
| 5     | C1_G  | 5          | `heilbron_repro_v1`     | `heilbron_repro_v1/pop_a`     | gradient_in_prompt  | C1_D (db=6)  |
| 6     | C1_D  | 6          | `heilbron_repro_v1`     | `heilbron_repro_v1/pop_b`     | gradient_in_prompt  | C1_G (db=5)  |
| 7     | C2_G  | 7          | `heilbron_repro_v1`     | `heilbron_repro_v1/pop_a`     | gradient_in_prompt  | C2_D (db=8)  |
| 8     | C2_D  | 8          | `heilbron_repro_v1`     | `heilbron_repro_v1/pop_b`     | gradient_in_prompt  | C2_G (db=7)  |

**Server**: `10.232.30.185` (single host for all 8 PIDs).
**Seed**: not set globally — Hydra config does not expose a single global seed; non-determinism sources documented below.
**Val set**: full Heilbron N=11 evaluator (no train/val split — synthetic optimization problem).

---

## Controlled Variables

Pinned identical to v2 except where IV 1 (D tanh smoothing) and IV 2 (D no-lineage) require derived adjustments. See `01_design.md` §3 for the IV/CV table; the scalar pins below are asserted by `experiment.yaml :: contract.config.pinned`.

| Field                                               | Value     | Source                                  |
|-----------------------------------------------------|-----------|-----------------------------------------|
| `pre_step_hook.drift_cap`                           | 100000    | v2 lineage                              |
| `pre_step_hook.sync_every_n_epochs`                 | 1         | v2 lineage                              |
| `inner_iterations`                                  | 1         | v2 lineage                              |
| `n_opponents`                                       | 1         | v2 lineage                              |
| `source_prompt_k`                                   | 1         | v2 lineage                              |
| `num_parents`                                       | 1         | Heilbron tradition                      |
| `max_elites_per_generation`                         | 8         | v2 lineage                              |
| `max_mutations_per_generation`                      | 8         | v2 lineage                              |
| `mutation_mode`                                     | rewrite   | v2 lineage                              |
| `max_generations`                                   | 200       | v2 lineage                              |
| `pipeline_builder.lineage_filter.min_shared`        | 1         | v2 lineage (G-only, D removes stage)    |
| `pipeline_builder.lineage_filter.inject_shared_evidence` | true | v2 lineage (G-only, D removes stage)    |
| `stage_timeout`                                     | 900       | v2 lineage                              |
| `dag_timeout`                                       | 3600      | v2 lineage                              |

**Per-run extras** (not pinned, asserted via run-level `extra_overrides`):
- All G: `archive_reeval=false`, `opponent_result_mode=exec`, `opponent_sampling_mode=softmax`, lineage stages active.
- All D: `archive_reeval=true`, `opponent_result_mode=cached`, `opponent_sampling_mode=top_k`, `engine_config.refresh_passes=1`, `pipeline_builder.disable_lineage_on_improver=true`.

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism (documented and accepted):
- LLM sampling temperature and nucleus sampling on the mutation LLM (`Qwen3-235B-A22B-Thinking-2507`) and any chain LLMs.
- `random.sample` in `FormatterStage` for failure sampling per generation.
- `random.choices` weighted draw inside `softmax` opponent sampling on G runs (D uses deterministic `top_k`).
- Non-deterministic GPU floating point across hardware.
- Time-of-arrival ordering of G writes vs D reads on the cross-population Redis DBs (paired-arm coupling).

**Global seed**: N/A (Hydra config does not expose a single global seed).

A fresh run with identical config will produce a different fitness trajectory but should land in a statistically similar μ_G range. Cross-experiment comparisons use the effect-size threshold above (μ_G − 0.03315 ≥ +0.0010, 95% CI excluding 0) rather than exact trajectory matching.

---

## Dataset Checksums

Cryptographic anchor for the task definition. **Heilbron N=11 has no external dataset** — the task definition files (evaluate.py, helper.py, metrics.yaml, task_description.txt, fallbacks, initial programs) ARE the reproducibility anchor. Full snapshot at `dataset_snapshot.json`:

- `git_commit`: `3eb41b43f42d0be09a94b0782143eb871e54a9c2` (HEAD of `problems/heilbron_repro_v1/` at pre-registration time)
- `dataset_snapshot.json`: 15 file checksums covering both `pop_a/` (Constructor) and `pop_b/` (Improver) trees

Critical files (sha256 truncated to 16 hex chars; full SHA256 available via `sha256sum` re-run from snapshot):

| File                                                          | sha256 (16 chars)  |
|---------------------------------------------------------------|--------------------|
| `problems/heilbron_repro_v1/pop_a/evaluate.py`                | `3e428c859bb656cf` |
| `problems/heilbron_repro_v1/pop_a/helper.py`                  | `85583ac5c30678c9` |
| `problems/heilbron_repro_v1/pop_a/metrics.yaml`               | `1883767df932e163` |
| `problems/heilbron_repro_v1/pop_a/task_description.txt`       | `5f03e79f20fe027b` |
| `problems/heilbron_repro_v1/pop_b/evaluate.py`                | `b18dc4b3d2c2b2ac` |
| `problems/heilbron_repro_v1/pop_b/helper.py`                  | `85583ac5c30678c9` |
| `problems/heilbron_repro_v1/pop_b/metrics.yaml`               | `6c196edda4715b50` |
| `problems/heilbron_repro_v1/pop_b/task_description.txt`       | `39a0a814be99c772` |

**Verification**: at closeout time, re-run the snapshot script and diff against `dataset_snapshot.json`. Any divergence = protocol deviation, must be logged in `04_issues_log.md`.

---

## Success Criteria

1. **All 8 runs reach gen 200** without `running → invalid` transition (i.e. no infrastructure abort like d-smoothing-minimal at gen ~15-30).
2. **D per-gen pace is within 1.3× of G** at the gen-50 checkpoint. The d-smoothing-minimal abort happened because D was at 0.57× of G's pace; lineage removal must close this gap. **If D is still at < 0.7× of G's pace by gen 50, the experiment is at infrastructure risk** and Phase 5 analysis must explicitly diagnose whether residual asymmetry came from `archive_reeval` (InsightsStage LLM re-evals) or some other source.
3. **All `treatment_checks` pass at smoke and at every checkpoint**. The 7 `d_treatment_checks` entries (3 lineage-removal + 4 tanh-smoothing + 1 stale-pyc) all gate launch and analysis.
4. **Decision rule above** determines POSITIVE / NEGATIVE / NULL / REGRESSIVE verdict.

---

## Monitoring Plan

`max_generations`: 200

| Gen | Wall (rough) | Action                                                                                       |
|-----|--------------|----------------------------------------------------------------------------------------------|
| 3   | smoke        | Pre-real-launch: 1-run smoke at `evolution.max_generations=3` on a flush DB; verify all `treatment_checks` PASS, then flush smoke DB |
| 20  | ~10%         | Smoke check on the real runs — all 8 PIDs alive, Redis keys growing, D pace ≥ 0.7× G pace    |
| 40  | ~20%         | First checkpoint — extract best-by-`actual_fitness` per run, log μ_G, log μ_D, log per-run pace |
| 100 | ~50%         | Midpoint checkpoint — same metrics + adversarial-watchdog plots (arms-race + comparison)     |
| 200 | 100%         | Final evaluation + Elena Phase 5 analysis (`05_results.md`)                                  |

**Watchdog**: `gigaevo -e heilbron/d-tanh-no-lineage watchdog` (plugin=`adversarial`), poll_interval=3600s. Telegram + PR rolling comments enabled.

**Early termination rule**: if at gen 30 D is still at < 0.6× of G's pace, abort with `running → invalid` and log to `04_issues_log.md` exactly as d-smoothing-minimal did. Lineage removal is the proposed fix; if it doesn't close the gap, the design has missed a load-bearing source of D-side cost (likely `archive_reeval` triggering LLM InsightsStage re-evals on opponent-ID changes).

**Alert thresholds** (in `experiment.yaml :: control_plane.watchdog.alert_thresholds`):
- `invalidity_rate > 0.75` for any run
- `stagnation_window` = 10 generations of zero `actual_fitness` improvement
- `generation_gap_threshold` = 5 (max-min gen across the 8 runs)

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| A1_G  | _(filled at launch)_ | _(filled at launch)_ | |
| A1_D  | _(filled at launch)_ | _(filled at launch)_ | |
| A2_G  | _(filled at launch)_ | _(filled at launch)_ | |
| A2_D  | _(filled at launch)_ | _(filled at launch)_ | |
| C1_G  | _(filled at launch)_ | _(filled at launch)_ | |
| C1_D  | _(filled at launch)_ | _(filled at launch)_ | |
| C2_G  | _(filled at launch)_ | _(filled at launch)_ | |
| C2_D  | _(filled at launch)_ | _(filled at launch)_ | |

Watchdog PID: _(filled at launch)_
Launch commit: `<filled at launch>`

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|

---

## Amendments

_(Add numbered entries here for any post-registration changes. Each entry must reference a commit hash and explain the deviation from the pre-registered protocol.)_
