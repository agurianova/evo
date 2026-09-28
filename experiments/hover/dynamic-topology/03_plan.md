# Pre-Registration: HoVer Dynamic Topology -- Evolving Chain Structure vs. Fixed 7-Step Topology

**Date**: 2026-03-23
**Protocol version**: 1.0
**Pre-registration commit**: `<hash>` -- commit this file BEFORE any code changes
**GitHub PR**: #<number> (branch: `exp/hover-dynamic-topology`)
**Tracking issue**: N/A
**Design doc**: `experiments/hover/dynamic-topology/01_design.md`
**Review doc**: `experiments/hover/dynamic-topology/02_review.md` (verdict: APPROVED)
**Evaluation script**: `experiments/hover/dynamic-topology/run_test_eval.sh` (sha256: `<hash>`) -- to be created during implementation

---

## Hypothesis

**H0**: Mean discrete test retrieval coverage of the dynamic-topology condition does not exceed mean discrete test retrieval coverage of the static-topology condition by more than 2.0pp. Formally: mu_full - mu_static <= 2.0pp.

**H1**: Mean discrete test retrieval coverage of the dynamic-topology condition exceeds the static-topology condition by more than 2.0pp. The ability to add retrieval hops, adjust step count, and remove frozen-step constraints enables evolutionary search to discover chain structures with higher 3-hop document coverage than the fixed 7-step topology permits.

**H2 (secondary)**: Dynamic-topology runs produce evolved chains whose step counts differ from 7 in at least 50% of the final elite archive programs.

**Primary metric**: Discrete test retrieval coverage at gen 25 on 300-sample held-out test set (5-repeat average per run).
**Significance threshold**: alpha = 0.05 (one-sided Welch's t-test); primary decision via effect-size table.

---

## Run Design Table

| Run | Label | Cell | Wave | `problem.name` | `redis.db` | `pipeline` | Chain LLM URL | Mutation LLM URL |
|-----|-------|------|------|-----------------|-----------|-----------|---------------|------------------|
| D1 | hover-static-1 | Control | 1 | `chains/hover/static_soft` | 9 | `standard` | `http://10.226.17.25:8001/v1` | `http://10.226.72.211:8777/v1` |
| D2 | hover-static-2 | Control | 1 | `chains/hover/static_soft` | 10 | `standard` | `http://10.225.185.235:8001/v1` | `http://10.226.15.38:8777/v1` |
| D3 | hover-static-3 | Control | 2 | `chains/hover/static_soft` | 11 | `standard` | `http://10.226.17.25:8001/v1` | `http://10.226.72.211:8777/v1` |
| D4 | hover-static-4 | Control | 2 | `chains/hover/static_soft` | 12 | `standard` | `http://10.225.185.235:8001/v1` | `http://10.226.15.38:8777/v1` |
| D5 | hover-full-1 | Treatment | 1 | `chains/hover/full` | 13 | `standard` | `http://10.226.17.25:8000/v1` | `http://10.226.185.47:8777/v1` |
| D6 | hover-full-2 | Treatment | 1 | `chains/hover/full` | 14 | `standard` | `http://10.225.185.235:8000/v1` | `http://10.225.51.251:8777/v1` |
| D7 | hover-full-3 | Treatment | 2 | `chains/hover/full` | 15 | `standard` | `http://10.226.17.25:8000/v1` | `http://10.226.185.47:8777/v1` |
| D8 | hover-full-4 | Treatment | 2 | `chains/hover/full` | 1 | `standard` | `http://10.225.185.235:8000/v1` | `http://10.225.51.251:8777/v1` |

---

## Controlled Variables

| Field | Value |
|-------|-------|
| `pipeline` | `standard` (both conditions) |
| `prompts` | `default` |
| Validation samples | 300 (first 300 train) |
| Chain LLM | Qwen/Qwen3-8B, thinking mode ON, context 32768 |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 |
| `num_parents` | 1 |
| `max_elites_per_generation` | 8 |
| `max_mutations_per_generation` | 8 |
| `stage_timeout` | 3000 |
| `dag_timeout` | 7200 |
| `max_generations` | 25 |
| `mutation_mode` | rewrite |
| Seed initialization | Cold start (no program_loader) |
| Evolutionary fitness | Soft (fractional) -- both conditions |
| Test metric | Discrete retrieval coverage (all 3 gold docs = 1, else 0) |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism (document and accept):
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature and nucleus sampling in chain and mutation LLMs
- Non-deterministic GPU floating point across hardware

**Global seed**: N/A (Hydra config does not support global seeding for LLM-based evolution)

A fresh run with identical config will produce a different fitness trajectory but should
land in a statistically similar fitness range. Cross-experiment comparisons use effect-size
thresholds (from `01_design.md`) rather than exact trajectory matching.

---

## Dataset Checksums

Cryptographic anchor for the data used in this experiment.
Compute at pre-registration time and verify before final evaluation.

| File | sha256 |
|------|--------|
| `problems/chains/hover/data/hover_train.jsonl` | To be computed at implementation |
| `problems/chains/hover/data/hover_test.jsonl` | To be computed at implementation |

---

## Success Criteria

| Treatment mean delta vs. Control | Verdict |
|----------------------------------|---------|
| >= +4.0pp | STRONG POSITIVE |
| [+2.0pp, +4.0pp) | POSITIVE |
| (0pp, +2.0pp) | SUGGESTIVE |
| <= 0pp | NULL |

**Replication check**: Control mean within +/-2.0pp of Cell C (54.37%) = replication success.

**MDE at n=4 per cell**: 3.02pp at conservative SD=1.5pp (80% power, one-sided alpha=0.05). At optimistic SD=1.0pp, MDE drops to 2.01pp.

---

## Monitoring Plan

`max_generations`: 25

- Gen 3 (~12%): smoke check -- all PIDs alive, Redis keys growing, treatment runs show n_steps=7 (seed program loaded correctly)
- Gen 5 (~20%): first checkpoint -- check for topology mutations in treatment runs (are step counts changing?), extract val fitness
- Gen 13 (~50%): midpoint checkpoint -- full status, run test eval (hard gate), check topology diversity in treatment archive
- Gen 25 (100%): final evaluation + closeout

Early termination rule:
- Gen-0 val fitness > 0.30 or = sentinel (-1000.0): halt, investigate
- Treatment gen-0 n_steps != 7: halt, seed error
- Invalidity rate > 90% at gen 10: halt, systemic failure
- No fitness improvement for 10+ consecutive gens AND gen >= 15: early plateau (record, do not invalidate)

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|

Watchdog PID:
Launch commit: `<hash>`

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|

---

## Amendments

### A1 (pre-committed): Topology mutation hint

**Trigger**: If no topology change (step addition, removal, or type change) occurs in the first 5 generations across all 3 treatment runs.

**Action**: Add a "topology hint" paragraph to the mutation prompt describing that step count, step types, and dependencies are mutable. This does not change the hypothesis -- it ensures the IV is actually active.

**Rationale**: Risk 1 in Section 12 of 01_design.md. The mutation LLM may not realize topology is mutable without explicit instruction.
