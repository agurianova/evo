# Pre-Registration: heilbron/adversarial-repro-v1

**Date**: 2026-04-19
**Protocol version**: 1.0
**Pre-registration commit**: `<filled at commit>` ← commit this file BEFORE any runs start
**GitHub PR**: `<filled at PR>` (branch: `exp/heilbron/adversarial-repro-v1`)
**Tracking issue**: N/A (add if created)
**Design doc**: `experiments/heilbron/adversarial-repro-v1/01_design.md`
**Review doc**: `experiments/heilbron/adversarial-repro-v1/02_review.md` (verdict: APPROVED after Revision 1)
**Literature brief**: `experiments/heilbron/adversarial-repro-v1/literature_brief.md`
**Codebase map**: `experiments/heilbron/adversarial-repro-v1/codebase_map.md` (feasibility: YELLOW; no RED blockers)
**Dataset snapshot**: `experiments/heilbron/adversarial-repro-v1/dataset_snapshot.json` (15 frozen problem files)
**Evaluation script**: N/A — Heilbronn N=11 has no test split (geometric optimization; fitness = min-area)

---

## Hypothesis

**H₀**: Under the current bug-fixed library with v1 hyperparameters + frozen v1 hard-floor fitness + `drift_cap=100000`, mean best-ever `actual_fitness` across the 4 G runs is not meaningfully higher than v2's G mean (~0.03383) or baseline-repro's mean (0.03449).

**H₁**: Restoring v1's effective loose coupling via `drift_cap=100000` recovers v1-level performance: mean best-ever `actual_fitness` across 4 G runs ≥ 0.03574 (v1 grand mean), with at least 1/4 G runs reaching `actual_fitness` ≥ 0.0365.

**Primary metric**: best-ever `actual_fitness` per G run, averaged across the 4 G runs (A1_G, A2_G, C1_G, C2_G).
**Significance threshold**: No formal p-value. N=4 G runs is underpowered for formal testing. Primary inference is descriptive comparison of mean and per-run distribution against three historical reference points (v1, v2, baseline-repro) per the effect-size table in 01_design.md §2.

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `problem.name` | `feedback_mode` | `population_role` | Opponent DB | `llm_base_url` |
|-----|-------|------------|-----------|----------------|-----------------|-------------------|-------------|----------------|
| 1 | A1_G | 1 | heilbron_repro_v1 | heilbron_repro_v1/pop_a | composition | constructor | 2 | http://10.232.30.185:4000/v1 |
| 2 | A1_D | 2 | heilbron_repro_v1 | heilbron_repro_v1/pop_b | composition | improver | 1 | http://10.232.30.185:4000/v1 |
| 3 | A2_G | 3 | heilbron_repro_v1 | heilbron_repro_v1/pop_a | composition | constructor | 4 | http://10.232.30.185:4000/v1 |
| 4 | A2_D | 4 | heilbron_repro_v1 | heilbron_repro_v1/pop_b | composition | improver | 3 | http://10.232.30.185:4000/v1 |
| 5 | C1_G | 5 | heilbron_repro_v1 | heilbron_repro_v1/pop_a | gradient_in_prompt | constructor | 6 | http://10.232.30.185:4000/v1 |
| 6 | C1_D | 6 | heilbron_repro_v1 | heilbron_repro_v1/pop_b | gradient_in_prompt | improver | 5 | http://10.232.30.185:4000/v1 |
| 7 | C2_G | 7 | heilbron_repro_v1 | heilbron_repro_v1/pop_a | gradient_in_prompt | constructor | 8 | http://10.232.30.185:4000/v1 |
| 8 | C2_D | 8 | heilbron_repro_v1 | heilbron_repro_v1/pop_b | gradient_in_prompt | improver | 7 | http://10.232.30.185:4000/v1 |

All runs also pass: `evolution=steady_state stopper=max_generations max_generations=50`.
Model: `Qwen3-235B-A22B-Thinking-2507` across all runs.
Opponent prefix: `heilbron/adversarial-repro-v1/pop_b` for G runs; `heilbron/adversarial-repro-v1/pop_a` for D runs.

---

## Controlled Variables

| Field | Value | Source |
|-------|-------|--------|
| `pipeline` | `heilbron_repro_v1` | Layer-3 config that sets `drift_cap=100000` and K=1 / n_opponents=1 / source_prompt_k=1 |
| `evolution` | `steady_state` | v1's actual operating mode post KF-01 |
| `stopper` | `max_generations` | Researcher decision — no plateau, no wallclock |
| `max_generations` | 50 | Full horizon (v1 died at 8–29 due to bugs) |
| `drift_cap` | 100000 | No-op — emulates v1's effectively unthrottled sync |
| `sync_every_n_epochs` | 1 | Retained from `adversarial_coevo_ss` parent |
| `inner_iterations` | 1 | v1's actual K (no-op config key per codebase_map; pinned for provenance) |
| `n_opponents` | 1 | v1 setting |
| `source_prompt_k` | 1 | D sees exactly 1 G source code |
| `archive_reeval` | false | Matches v1; independently confirmed NEGATIVE in adversarial-dynamic-updates |
| `num_parents` | 1 | Task-group tradition (`config/experiment/heilbron.yaml`) |
| `max_elites_per_generation` | 8 | Task-group tradition |
| `max_mutations_per_generation` | 8 | v1 setting |
| `mutation_mode` | rewrite | v1 setting |
| `model_name` | Qwen3-235B-A22B-Thinking-2507 | Same family as v1; proxy defaults may differ (acknowledged residual gap) |
| `temperature` | 0.6 | v1 setting |
| `max_tokens` | 81920 | v1 setting |
| `island_max_size` | 75 | v1 setting |
| `primary_resolution` | 150 | v1 setting |
| `stage_timeout` / `dag_timeout` | 3000 / 7200 | v1 setting |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism (documented and accepted):
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature (0.6) and nucleus sampling in the mutation LLM
- Non-deterministic GPU floating point on the proxy's inference backend
- Proxy-level changes since v1 commit `04bd5e69` (uncontrollable residual gap)

**Global seed**: N/A — the framework does not thread a deterministic seed into the mutation LLM calls; this is the same condition under which v1 ran.

A fresh run with identical config will produce a different fitness trajectory but should land in a statistically similar fitness distribution. Cross-experiment comparison uses the effect-size thresholds in 01_design.md §2, not exact trajectory matching.

---

## Dataset Checksums

The "dataset" for Heilbronn N=11 is the frozen problem directory `problems/heilbron_repro_v1/pop_{a,b}/`, which carries v1's original hard-floor `evaluate.py` (later refactored to smoothed tanh in commit `e10ed3d1` — NOT used here).

Full SHA-256 checksums for all 15 frozen files: see `dataset_snapshot.json` (machine-readable anchor).

Verify integrity before launch:

```bash
/home/jovyan/.mlspace/envs/evo/bin/python3 -c "
import hashlib, json, sys
from pathlib import Path
snap = json.loads(Path('experiments/heilbron/adversarial-repro-v1/dataset_snapshot.json').read_text())
for f, expected in snap['file_checksums'].items():
    actual = hashlib.sha256(Path(f).read_bytes()).hexdigest()[:16]
    if actual != expected:
        sys.exit(f'MISMATCH: {f}  expected={expected}  got={actual}')
print(f'OK — all {len(snap[\"file_checksums\"])} files match snapshot.')
"
```

**Reproducibility anchor**: any future re-run must pass this checksum verification before launch. If the script fails, the frozen problem files have drifted and the replication is invalid.

---

## Success Criteria

Per 01_design.md §2 — effect-size thresholds on mean best-ever `actual_fitness` across the 4 G runs:

| Outcome | Verdict |
|---|---|
| mean ≥ 0.0360 AND ≥ 1/4 G runs at 0.0365 | **POSITIVE** — v1 reproduced; loose coupling confirmed as active mechanism |
| mean ≥ 0.03449 AND < 0.0360 | **SUGGESTIVE** — loose coupling helps directionally but does not fully recover v1 |
| mean within 0.001 of v2 mean (0.0334–0.0354) | **NULL** — loose coupling insufficient; library drift or longer runs are the culprit |
| mean < 0.0330 | **NEGATIVE** — active regression under loose coupling |

**Abandon criterion**: if mean < 0.0340 (below v2 and baseline), loose coupling under the current library is actively harmful, and the REDESIGN bundle (smoothed tanh fitness) becomes the sole viable path forward for Heilbronn.

**Invalidity criteria** (any one → experiment is INVALID regardless of fitness numbers):
- D/G generation ratio at end is ~1.0 (lockstep) instead of ~2.0–2.5 — `drift_cap=100000` did not produce the intended asymmetry.
- Any startup log does NOT show `drift_cap=100000`.
- Fewer than 3/4 G runs reach gen 25.
- Cross-DB Redis key contamination detected.

---

## Monitoring Plan

`max_generations`: 50
`stopper`: `max_generations` (no plateau, no wallclock)

- **Gen 3 (~6%)**: smoke check — all 8 PIDs alive, Redis keys growing, startup logs show `drift_cap=100000` for all runs, `[SourceCodeInjection]` visible in D logs only.
- **Gen 10 (~20%)**: first checkpoint — record per-run best `actual_fitness`, D fitness point-mass fraction, D/G generation ratio.
- **Gen 12 (~24%)**: **key diagnostic checkpoint** — this is v1's G ceiling. Record per-run `best_fitness_by_gen_12` for the pre-registered diagnostic split (01_design.md §13.3).
- **Gen 25 (~50%)**: midpoint checkpoint — minimum completion threshold; if fewer than 3/4 G runs reach this gen, the experiment is INVALID.
- **Gen 50 (100%)**: final analysis — best-ever `actual_fitness` per G run, mean/stderr, per-arm breakdown, gen-12-vs-gen-50 delta, D-collapse rate, compute ratio.

**Early termination rule**: none (per researcher decision). Runs exhaust their 50-generation horizon regardless of early convergence.

**Treatment verification checks** (must all pass before the experiment is considered validly launched — see 01_design.md §12 for full list):
1. Startup log shows `[ProgressBasedSyncHook] Init ... drift_cap=100000` for all 8 runs.
2. `--cfg job` preview shows `pipeline: heilbron_repro_v1` and `problem.name: heilbron_repro_v1/pop_{a,b}`.
3. D run logs show `[SourceCodeInjection] showing 1 programs` at gen 3+.
4. G run logs show NO `[SourceCodeInjection]` lines.
5. No `drift_cap exceeded` log lines over the full run (sync hook never blocks).
6. At gen 12, each D run is at gen ~27 ± 3 (≈2.2× G's gen count).

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
Launch commit: `<hash>`

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|
| _tbd_ | _tbd_ | _tbd_ |

---

## Amendments

_(Add numbered entries here for any post-registration changes. Every amendment must explain why the pre-registered design was insufficient.)_

### Amendment A1 (2026-04-19) — Redis key prefix convention

**Change**: Opponent Redis prefixes use `heilbron_repro_v1/pop_{a,b}` (matching `problem.name`) rather than `heilbron/adversarial-repro-v1/pop_{a,b}` as literally written in 01_design.md §12.3.

**Why the pre-registered design was insufficient**: The literal text in §12.3 deviates from the established convention (`prefix == problem_name`) used in v1 (`heilbron_adversarial/pop_{a,b}`) and v2 (`heilbron_adversarial/pop_{a,b}`). Applying the literal design text would:
1. Decouple program/metrics keys from dataset provenance (checksums in `dataset_snapshot.json` are keyed by problem path).
2. Break the Redis watchdog plugin's opponent-pair matching, which expects `pop_a`/`pop_b` suffixes at the same namespace level.
3. Make cross-experiment key inspection inconsistent with all prior heilbron adversarial runs.

**What is unchanged**: The experiment-directory namespace is still tracked in Redis by `experiments:heilbron/adversarial-repro-v1:*` watchdog keys (set by the monitoring plugin). Treatment verification check #1 (`drift_cap=100000` in startup log) is unaffected. Checks #2 and #3 (opponent_redis_prefix) are updated to `heilbron_repro_v1/pop_{a,b}`.
