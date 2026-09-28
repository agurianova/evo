# Pre-Registration: heilbron/adversarial-dynamic-updates

**Date**: 2026-04-09
**Protocol version**: 1.0
**Pre-registration commit**: `ebc12cc3`
**GitHub PR**: #197 (branch: `exp/heilbron/adversarial-dynamic-updates`)
**Tracking issue**: #195
**Design doc**: `experiments/heilbron/adversarial-dynamic-updates/01_design.md`
**Review doc**: `experiments/heilbron/adversarial-dynamic-updates/02_review.md` (verdict: APPROVED)
**Evaluation script**: N/A (Heilbronn is optimization — no held-out test split)

---

## Hypothesis

**Research Question**: Does per-program fingerprint-based archive re-evaluation fix stale fitness, improve parent selection, and break Improver stagnation on the Heilbronn adversarial co-evolution task?

**H₀**: Re-evaluation has no effect. Treatment `actual_fitness` (raw min_area) at gen 75 equals control `actual_fitness` within noise floor (|Δ| < 0.002).

**H₁**: Re-evaluation improves Constructor quality. Treatment `actual_fitness` at gen 75 exceeds control by ≥ 0.002.

**Primary metric**: `actual_fitness` (raw min_area) at gen 75, read from live archive state — NOT from frontier history timeseries. This is the GAN-literature-aligned metric: intrinsic generator quality, decoupled from discriminator state.

**Significance threshold**: N=1 per condition (explicitly exploratory). Verdict is directional/magnitude-based:
- POSITIVE: treatment > control by ≥ 0.002
- NULL: |treatment − control| < 0.002
- NEGATIVE: control > treatment by ≥ 0.002
- Reference noise floor: within-pair variance from heilbron-prover experiments ≈ 0.00168

---

## Run Design Table

**Amendment (v3)**: 2×2 factorial. Soft fitness added as second IV. 8 runs total.

| Run | Label  | `redis.db` | Pop | Re-eval | Soft fitness | `opponent_redis_db` |
|-----|--------|------------|-----|---------|--------------|---------------------|
| 1 | RE_A   | 1 | A (Constructor) | ON  | OFF | 2 |
| 2 | RE_B   | 2 | B (Improver)    | ON  | OFF | 1 |
| 3 | Both_A | 3 | A (Constructor) | ON  | ON  | 4 |
| 4 | Both_B | 4 | B (Improver)    | ON  | ON  | 3 |
| 5 | C_A    | 5 | A (Constructor) | OFF | OFF | 6 |
| 6 | C_B    | 6 | B (Improver)    | OFF | OFF | 5 |
| 7 | SF_A   | 7 | A (Constructor) | OFF | ON  | 8 |
| 8 | SF_B   | 8 | B (Improver)    | OFF | ON  | 7 |

**DBs**: RE=1-2, Both=3-4, C=5-6, SF=7-8. All 8 DBs used. No cross-condition interaction.
**Mutation LLM**: `Qwen3-235B-A22B-Thinking-2507` via `http://10.232.30.185:4000/v1` (LiteLLM proxy).
**Pipeline**: `adversarial_coevo_ss` (steady-state adversarial, no feedback stage, K=0).

---

## Controlled Variables

| Field | Value |
|-------|-------|
| Opponent feedback (K) | K=0 (no opponent code in mutation prompts) |
| `evolution` | `steady_state` |
| `max_in_flight` | 8 |
| `pipeline` | `adversarial_coevo_ss` |
| `problem.name` (Pop A) | `heilbron_adversarial/pop_a` |
| `problem.name` (Pop B) | `heilbron_adversarial/pop_b` |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` |
| `mutation_url` | `http://10.232.30.185:4000/v1` |
| `num_parents` | 1 |
| `max_elites_per_generation` | 8 |
| `max_mutations_per_generation` | 8 |
| `n_opponents` | 5 |
| `per_opponent_timeout` | 300 |
| `stage_timeout` | 3000 |
| `dag_timeout` | 7200 |
| `mutation_mode` | `rewrite` |
| `max_generations` | 75 |
| `significant_change` | 0.01 |
| Initial programs | `initial_programs/baseline.py` (cold start) |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism (documented and accepted):
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature and nucleus sampling in mutation LLM
- Non-deterministic GPU floating point across hardware
- Fitness-proportional random opponent sampling (per-evaluation random seed stored in Program object, not globally controlled)

**Global seed**: N/A (stochastic throughout; per-evaluation seeds stored for re-evaluation fingerprinting).

A fresh run with identical config will produce a different fitness trajectory but should land in a statistically similar fitness range. Cross-experiment comparisons use effect-size thresholds (from `01_design.md`) rather than exact trajectory matching.

**Re-evaluation mechanism**: at epoch step 8 (`_epoch_refresh`, after sync hook at step 4, after mutation gate opens at step 7), `ArchiveReEvaluationHook` re-applies each program's stored eval seed to the current opponent archive. If the sampled opponent set differs from the stored fingerprint, the program is re-evaluated. The stored seed is the reproducibility anchor for individual re-evaluation events.

---

## Dataset Checksums

Heilbronn is a geometric optimization problem with no external dataset — the task is defined entirely by the scoring function (min triangle area). The "dataset" is the problem code and initial programs.

**Reproducibility anchor**: `dataset_snapshot.json` in this directory.
- **Git commit**: `74563405` (commit of `problems/` at pre-registration time)
- **Key files**:

| File | sha256 (first 16 chars) |
|------|------------------------|
| `problems/heilbron_adversarial/pop_a/evaluate.py` | `abba6193c50fa9cb` |
| `problems/heilbron_adversarial/pop_a/helper.py` | `85583ac5c30678c9` |
| `problems/heilbron_adversarial/pop_a/initial_programs/grid.py` | `42664a0ad15a1165` |
| `problems/heilbron_adversarial/pop_a/task_description.txt` | `fa5944403a22a0f8` |
| `problems/heilbron_adversarial/pop_a/metrics.yaml` | `f7c75c758d759231` |
| `problems/heilbron_adversarial/pop_b/evaluate.py` | `4264321f708f8810` |
| `problems/heilbron_adversarial/pop_b/helper.py` | `85583ac5c30678c9` |
| `problems/heilbron_adversarial/pop_b/initial_programs/seed.py` | `f9bd024a6b927eea` |
| `problems/heilbron_adversarial/pop_b/task_description.txt` | `4b05cf1271ee2e80` |
| `problems/heilbron_adversarial/pop_b/metrics.yaml` | `25ed5dc24428711b` |

Full checksums: `experiments/heilbron/adversarial-dynamic-updates/dataset_snapshot.json`

---

## Success Criteria

### Primary (H1 — Constructor actual_fitness at gen 75)

| Verdict | Criterion |
|---------|-----------|
| STRONG POSITIVE | Treatment `actual_fitness` > control by ≥ 0.005 |
| POSITIVE | Treatment `actual_fitness` > control by ≥ 0.002 |
| NULL | \|treatment − control\| < 0.002 |
| NEGATIVE | Control > treatment by ≥ 0.002 |

Throughput check: if treatment `mutations_per_wall_hour` < control by > 20%, note as caveat — re-evaluation overhead may confound.

### Secondary (H2 — Improver stagnation, T1_B vs C1_B)

| Verdict | Criterion |
|---------|-----------|
| POSITIVE | Treatment T1_B acceptance rate > 5%, control C1_B acceptance rate < 2% (rolling 10-gen window, gen 20–75) |
| NULL | Both stagnate (both < 2%) |
| MIXED | One breaks stagnation, other doesn't |

### Secondary (H3 — Archive staleness correction, treatment only)

| Verdict | Criterion |
|---------|-----------|
| ACTIVE | Mean elite turnover rate per re-eval event > 10% |
| MINIMAL | Mean elite turnover rate < 5% |

---

## Monitoring Plan

`max_generations`: 75

- **Gen 7 (~10%)**: smoke check — all 4 PIDs alive, Redis keys growing in all 4 DBs; treatment logs show `[ArchiveReEval] triggered`; control logs show zero re-eval entries; `reeval_count` key present in DBs 1-2, absent in DBs 5-6
- **Gen 15 (~20%)**: first checkpoint — extract best-by-`actual_fitness` from each archive, record metrics; check generation parity between Constructor-Improver pairs (max drift 5 gens); check invalidity rates
- **Gen 37 (~50%)**: midpoint checkpoint — record `actual_fitness` for all 4 runs; check H2 acceptance rate trend; check re-eval elite turnover rate in T1 pair
- **Gen 75 (100%)**: final evaluation — record all DVs from live archive state; run `tools/trajectory.py` for all 4 runs; write 05_results.md

**Futility stop** (gen 30): if treatment `actual_fitness` < control by ≥ 0.005, stop early with NEGATIVE verdict.

**Per-run early termination**:
- Constructor `actual_fitness` < 0.005 at gen 20 → cold start failed
- Invalidity rate > 75% for 5 consecutive generations
- PID dead 2 hours with no generation advance
- Re-evaluation hook crashes 3+ consecutive times → pause hook, log deviation, continue without re-eval

**Generation parity check**: Constructor-Improver pairs (T1_A/T1_B, C1_A/C1_B) should stay within 5 generations of each other throughout. Drift > 5 gens = flag for investigation.

**Archive diversity guard**: if any run's archive < 3 occupied cells for 5 consecutive epochs → pause re-eval hook for that run, log as protocol deviation.

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| T1_A | | | |
| T1_B | | | |
| C1_A | | | |
| C1_B | | | |

Watchdog PID:
Launch commit: `<hash>`

---

## Checkpoint Log

| Gen | Date (UTC) | Run | `actual_fitness` | `fitness` | Acceptance rate | Re-eval events | Notes |
|-----|-----------|-----|-----------------|-----------|-----------------|----------------|-------|
| 7 | | RE_A | | | | | |
| 7 | | Both_A | | | | | |
| 7 | | C_A | | | | N/A | |
| 7 | | SF_A | | | | N/A | |
| 15 | | RE_A | | | | | |
| 15 | | Both_A | | | | | |
| 15 | | C_A | | | | N/A | |
| 15 | | SF_A | | | | N/A | |
| 37 | | RE_A | | | | | |
| 37 | | Both_A | | | | | |
| 37 | | C_A | | | | N/A | |
| 37 | | SF_A | | | | N/A | |
| 75 | | RE_A | | | | | |
| 75 | | Both_A | | | | | |
| 75 | | C_A | | | | N/A | |
| 75 | | SF_A | | | | N/A | |

---

## Amendments

**Amendment 1 (2026-04-09)**: Design expanded from 2×1 (4 runs) to 2×2 factorial (8 runs) by adding soft fitness (Wasserstein analog, issue #192) as second IV. Run labels updated: T1_A/T1_B/C1_A/C1_B → RE_A/RE_B/Both_A/Both_B/C_A/C_B/SF_A/SF_B. DB 3-4 (Both) and 7-8 (SF) added. Sampling bug in `get_opponents()` fixed in same commit: raw `f/total` → softmax with min-max normalization, matching `FitnessProportionalEliteSelector` exactly.

**Pre-authorized amendments** (from 01_design.md Section 7):
1. **Compute throttle**: if re-eval > 120s per trigger, throttle to top-K programs only. Log event as protocol deviation.
2. **Diversity guard**: pause re-eval if archive < 3 occupied cells for 5 consecutive epochs. Log event.
