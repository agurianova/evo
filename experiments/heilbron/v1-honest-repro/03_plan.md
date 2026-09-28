# Pre-Registration: heilbron/v1-honest-repro

**Date**: 2026-04-26
**Protocol version**: 1.0
**Pre-registration commit**: `25470e37` (main HEAD at branch-off; updated post-commit on `exp/heilbron/v1-honest-repro`)
**GitHub PR**: TBD (branch: `exp/heilbron/v1-honest-repro`)
**Tracking issue**: N/A
**Design doc**: `experiments/heilbron/v1-honest-repro/01_design.md`
**Review doc**: `experiments/heilbron/v1-honest-repro/02_review.md` (verdict: APPROVED — researcher gate, post-17-question interview)
**Evaluation script**: N/A (Heilbronn task has no held-out test split; primary metric is best-ever `actual_fitness` from training-time MAP-Elites archive)

---

## Hypothesis

**H₀ (null / reproduction-supports)**: With v1's fitness-landscape semantics restored
verbatim (binary G resistance + linear D scoring) and the post-v1 SBF-LineageStage
filter disabled, current main (`25470e37`) reaches `actual_fitness ≥ 0.0364` (within
0.0001 of v1 SOTA 0.03648) in **at least one** of the 4 G runs.

**H₁ (alt / drift-load-bearing)**: Even with the v1 landscape restored, current main
produces a measurable downward shift in the G `actual_fitness` distribution — the
17-decision interview missed a load-bearing drift element. Candidate culprits:
- ConfigurableAggregator's `mean(resistance_score)` reduction over K=1
- post-v1 mandatory `(metrics, artifact)` evaluate.py contract
- 300+ commits of unrelated engine churn between `562a1210` and `25470e37`

**Primary metric**: best-ever `actual_fitness` over 200 generations across the 4 G
runs (A1_G, A2_G, C1_G, C2_G), recorded as `max` over Redis list
`{prefix}:metrics:history:program_metrics:valid_frontier_fitness`.

**Significance threshold**: this is a **descriptive reproducibility stress test**,
not a hypothesis test. N=4 G runs is too small for power-style testing. Effect
sizes are reported against the v1 historical 4-G-run distribution (mean 0.03574,
SOTA 0.03648 hit 3-of-4). No α threshold; the decision rule below replaces it.

---

## Run Design Table

| Run  | Label | `redis.db` | `pipeline`            | `prompts` | `problem.name`              | `llm_base_url`                 | Seed | Val set |
|------|-------|------------|------------------------|-----------|-----------------------------|--------------------------------|------|---------|
| 1    | A1_G  | 1          | `heilbron_v1_honest`   | default   | `heilbron_v1_honest/pop_a`  | http://10.232.30.185:4000/v1   | N/A  | live archive |
| 2    | A1_D  | 2          | `heilbron_v1_honest`   | default   | `heilbron_v1_honest/pop_b`  | http://10.232.30.185:4000/v1   | N/A  | live archive |
| 3    | A2_G  | 3          | `heilbron_v1_honest`   | default   | `heilbron_v1_honest/pop_a`  | http://10.232.30.185:4000/v1   | N/A  | live archive |
| 4    | A2_D  | 4          | `heilbron_v1_honest`   | default   | `heilbron_v1_honest/pop_b`  | http://10.232.30.185:4000/v1   | N/A  | live archive |
| 5    | C1_G  | 5          | `heilbron_v1_honest`   | default   | `heilbron_v1_honest/pop_a`  | http://10.232.30.185:4000/v1   | N/A  | live archive |
| 6    | C1_D  | 6          | `heilbron_v1_honest`   | default   | `heilbron_v1_honest/pop_b`  | http://10.232.30.185:4000/v1   | N/A  | live archive |
| 7    | C2_G  | 7          | `heilbron_v1_honest`   | default   | `heilbron_v1_honest/pop_a`  | http://10.232.30.185:4000/v1   | N/A  | live archive |
| 8    | C2_D  | 8          | `heilbron_v1_honest`   | default   | `heilbron_v1_honest/pop_b`  | http://10.232.30.185:4000/v1   | N/A  | live archive |

Pair structure (G⇄D mirroring matches v1):
- Pair A1: A1_G(db=1) ⇄ A1_D(db=2), Arm = Composition
- Pair A2: A2_G(db=3) ⇄ A2_D(db=4), Arm = Composition
- Pair C1: C1_G(db=5) ⇄ C1_D(db=6), Arm = Gradient-in-prompt
- Pair C2: C2_G(db=7) ⇄ C2_D(db=8), Arm = Gradient-in-prompt

All 8 runs on server `10.232.30.185`. Mutation/chain LLM via LiteLLM proxy on the
same host (NO_PROXY required so traffic doesn't egress).

---

## Controlled Variables

| Field                         | Value                                                | Source                                |
|-------------------------------|------------------------------------------------------|---------------------------------------|
| Model                         | `Qwen3-235B-A22B-Thinking-2507`                      | identical to v1                       |
| temperature / top_p / top_k   | 0.6 / 0.95 / 20                                      | `config/experiment/base.yaml`         |
| max_tokens                    | 81920                                                | identical to v1                       |
| max_elites_per_generation     | 8                                                    | `heilbron` task_group                 |
| max_mutations_per_generation  | 8                                                    | identical to v1                       |
| num_parents                   | 1                                                    | `heilbron` task_group (pinned)        |
| primary_resolution (MAP-Elites)| 150                                                 | identical to v1                       |
| inner_iterations              | 1                                                    | pinned                                |
| n_opponents                   | 1                                                    | pinned                                |
| source_prompt_k               | 1                                                    | pinned                                |
| archive_reeval                | false                                                | pinned (Q5)                           |
| refresh_passes                | 1 (engine default)                                   | Q6                                    |
| refresh_order                 | fifo                                                 | Q7                                    |
| disable_lineage_on_improver   | false                                                | Q8 (LineageStage on D matches v1)     |
| lineage_filter                | null                                                 | Q16 (standard LineageStage, no SBF)   |
| opponent_sampling_mode        | top_k                                                | Q3 (current default)                  |
| drift_cap                     | 100000                                               | pinned (no-op vs realistic ~400 progs)|
| sync_every_n_epochs           | 1                                                    | pinned                                |
| stage_timeout                 | 900                                                  | Q1                                    |
| dag_timeout                   | 3600                                                 | Q2                                    |
| max_generations               | 200                                                  | pinned                                |
| evolution                     | steady_state                                         | shared override                       |
| stopper                       | max_generations                                      | shared override                       |
| mutation_mode                 | rewrite                                              | pinned                                |
| significant_change            | 0.01                                                 | pinned                                |
| Aggregator (G runs)           | `heilbron_constructor` (mean reduction over K=1)     | Q15 (mandatory on current code)       |
| Aggregator (D runs)           | `heilbron_improver` (mean reduction over K=1)        | Q15                                   |
| Resistance scoring (G)        | binary `1.0 if delta<=0 else 0.0`                    | Q13 — v1 verbatim, evaluate.py:105    |
| Improvement scoring (D)       | linear `min(max(δ,0)/Q_MAX, 1.0)`                    | already current; v1 verbatim          |
| Task description prose        | restored from `562a1210`                             | Q11, Q12                              |
| metrics.yaml                  | restored from `562a1210`                             | Q13, Q14                              |

Full pinned manifest in `experiment.yaml:contract.config.pinned`. Preflight checks
each pin against the resolved Hydra config and fails CRITICAL on drift.

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction
is not possible.** Indeed, the *whole point* of this experiment is to test whether
a fresh run on current main lands in the v1 historical fitness distribution despite
trajectory non-determinism — that's the reproducibility claim being evaluated.

Known sources of non-determinism (documented and accepted):
- LLM sampling (temperature 0.6, top_p 0.95, top_k 20) in mutation and chain LLMs
- `random.sample` in `FormatterStage` failure-example sampling
- Non-deterministic GPU floating point (`Qwen3-235B-A22B-Thinking-2507` served via vLLM)
- MAP-Elites cell-pick ordering depends on the wallclock interleaving of the 2
  paired runs through Redis (`opponent_redis_db` cross-reads)

**Global seed**: N/A. Hydra config does not expose a deterministic seed for the
mutation LLM, and the live archive cross-coupling between G and D would defeat
single-process determinism even if it did. The reproducibility claim is **statistical**:
under v1's landscape, current main should land near v1's historical mean (0.03574)
and have non-trivial probability of hitting SOTA (0.0364+). Decision rule below
captures this directly.

---

## Dataset Checksums

The Heilbronn task has no external dataset — the "data" is the forked problem
directory (`problems/heilbron_v1_honest/`) containing task descriptions, metrics
schema, evaluate.py implementations, helper utilities, fallback programs, and
seed initial programs. Cryptographic anchor for **all** of these:

```bash
sha256sum problems/heilbron_v1_honest/{pop_a,pop_b}/{task_description.txt,metrics.yaml,evaluate.py,helper.py} \
          problems/heilbron_v1_honest/{pop_a,pop_b}/fallback/* \
          problems/heilbron_v1_honest/{pop_a,pop_b}/initial_programs/*
```

| File | sha256 |
|------|--------|
| (all anchored in `dataset_snapshot.json`) | see `experiments/heilbron/v1-honest-repro/dataset_snapshot.json` |

The snapshot file is computed at pre-registration time (Step 5b of experiment-design).
On launch, preflight diffs the live forked problem dir against the snapshot — any
unrecorded edit fails CRITICAL.

---

## Success Criteria

Decision rule on best-ever `actual_fitness` across the 4 G runs (A1_G, A2_G, C1_G, C2_G):

| Outcome                                                              | Verdict                                |
|----------------------------------------------------------------------|----------------------------------------|
| Best G `actual_fitness` ≥ 0.0364 in **≥ 1** run                       | **H₀ supported** — drift not load-bearing; current main reproduces v1 SOTA under v1 landscape |
| Best G ∈ [0.03574, 0.0364) in 0 runs above 0.0364, **≥ 2** runs ≥ mean | **partial reproduction** — current main matches v1 baseline mean but not SOTA tail; suggests stochastic-tail loss, not landscape drift |
| Best G < 0.03574 across **all 4** runs                               | **H₁ confirmed** — drift IS load-bearing; the 17-decision interview missed something. Trigger follow-up bisect on the 3 known irreducibles (aggregator reduction, evaluate.py tuple ABI, library churn) |
| Mixed (e.g. 1 SOTA, 3 below baseline mean)                           | **inconclusive** — report descriptively; do not auto-classify |

Secondary metrics (descriptive only, no decision threshold):
- Count of G runs reaching ≥ 0.0365 (compare to v1's 3-of-4)
- Generation rate ratio D/G at wallclock budget exhaustion (≥ ~1.5 = D-faster signal,
  consistent with the structural D-vs-G compute asymmetry observed in the relaunch-v2
  failure that motivated the d-tanh-no-lineage program)

---

## Monitoring Plan

`max_generations`: **200** (per run; same as v1)

- Gen 20 (~10%): smoke check via watchdog plot — all 8 PIDs alive, Redis fitness
  history growing, no drift_cap exceeded events, treatment-check log patterns
  present (binary resistance, lineage_filter=null, aggregator=heilbron_*)
- Gen 40 (~20%): first checkpoint — extract best-by-actual_fitness per run, post
  rolling PR comment with arms-race + comparison plots, telegram update
- Gen 100 (~50%): midpoint checkpoint — same artifacts; preliminary decision
  signal (any G already at ≥ 0.0364?)
- Gen 200 (100%): final evaluation. Compute the decision rule above. Write 05_results.md.

Watchdog poll interval: 3600 s (every hour). Plots: `arms-race` per pair, `comparison`
across all G with frontier annotation (D excluded from frontier line).

Alert thresholds (auto-pause via watchdog):
- `invalidity_rate` > 0.75 across 100 candidates → flag
- `stagnation_window` ≥ 10 with no fitness improvement → flag
- `generation_gap_threshold` ≥ 5 between paired G/D → flag (drift_cap engaging
  unexpectedly)

**Early termination rule**: NONE on plateau or success. The whole question is
"does current main reach v1's outcome distribution **at 200 generations**". Early-stop
on success would systematically inflate the SOTA hit rate vs v1's historical record
(which also ran to 200 generations). Pre-registered: run all 8 to gen 200 unless
hard infrastructure failure (server down, Redis OOM, model proxy unreachable).

---

## Actual Launch Record

| Run  | PID | Launch time (UTC) | Notes |
|------|-----|--------------------|-------|
| A1_G | _(filled at launch)_ | _(filled at launch)_ | DB 1 |
| A1_D | _(filled at launch)_ | _(filled at launch)_ | DB 2 |
| A2_G | _(filled at launch)_ | _(filled at launch)_ | DB 3 |
| A2_D | _(filled at launch)_ | _(filled at launch)_ | DB 4 |
| C1_G | _(filled at launch)_ | _(filled at launch)_ | DB 5 |
| C1_D | _(filled at launch)_ | _(filled at launch)_ | DB 6 |
| C2_G | _(filled at launch)_ | _(filled at launch)_ | DB 7 |
| C2_D | _(filled at launch)_ | _(filled at launch)_ | DB 8 |

Watchdog PID: _(filled at launch)_
Launch commit: _(filled at launch — head of `exp/heilbron/v1-honest-repro` at `gigaevo launch` time)_

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|------------|-------|
| _(filled at each milestone)_ | | |

---

## Amendments

_(Add numbered entries here for any post-registration changes.)_
