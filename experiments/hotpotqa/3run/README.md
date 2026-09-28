# 3-Run Parallel HotpotQA Evolution Experiment

**Start date**: 2026-02-27
**Branch**: `exp/hotpotqa-efficiency`
**Research plan**: `docs/plans/2026-02-27-3run-experiment-plan.md`
**PR**: [#65](https://github.com/KhrulkovV/gigaevo-core-internal/pull/65) (experiment log in PR comments)
**Current status**: Attempt 5 ACTIVE — Run A relaunched 2026-02-28 08:18 UTC (fixed vLLM confound; see Incident below)

## Research Question

Can GigaEvo's evolutionary prompt optimization for HotpotQA static chains, starting from the non-thinking baseline (42.3% EM), reach or exceed GEPA's 62.3% test EM within 7 days?

## Environment

| Component | Value |
|-----------|-------|
| Python interpreter | `/home/jovyan/envs/evo_fast/bin/python` |
| Working directory | `/workspace-SR008.fs2/mathemage/gigaevo-core` |
| Git branch | `exp/hotpotqa-efficiency` |
| Git HEAD (Attempt 5) | `10057ee` |
| Chain execution LLM | Qwen3-8B (non-thinking), `10.226.17.25:8001` |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 (3 servers, see Design table) |
| Validation dataset | 300 train samples (Exact Match) |
| Test dataset | 300 test samples (Exact Match) |
| Redis | localhost:6379, DBs 10/11/12 |

## Design

Three parallel runs, each varying ONE factor against a shared baseline (Run A) -- OFAT design:

| | **Run A** | **Run B** | **Run C** |
|--|-----------|-----------|-----------|
| **Role** | Control | High mutation budget | Warm-start seed |
| **Redis DB** | 10 | 11 | 12 |
| **Mutation server** | 10.226.72.211:8777 | 10.226.15.38:8777 | 10.226.185.131:8777 |
| **primary_resolution** | 10 | 10 | 10 |
| **max_mutations/gen** | 8 | **16** | 8 |
| **max_elites/gen** | 5 | **8** | 5 |
| **Seed programs** | baseline.py (42.3%) | baseline.py (42.3%) | baseline.py + warmstart_56pct.py (56.3%) |
| **max_generations** | 50 | 50 | 50 |
| **Tests** | -- | Mutation budget effect | Warm-start effect |
| **Log** | `run_a.log` | `run_b.log` | `run_c.log` |

## How to Launch (Reproducibility)

**Authoritative launch script**: `experiments/hotpotqa_3run/launch.sh`

Never hand-type run commands. The script handles:
1. Setting `NO_PROXY` with all required server IPs
2. Preflight HTTP connectivity checks for all 4 servers
3. Verifying Redis DBs 10/11/12 are empty
4. Verifying warm-start seed is NOT in `initial_programs/` prematurely
5. Staggered launch (A at t=0, B at t+5min, C at t+10min)
6. Injecting warm-start seed into `initial_programs/` only during Run C's window, then removing it

```bash
# Full launch (all preflight checks, staggered starts)
bash experiments/hotpotqa_3run/launch.sh

# Prerequisites before launch:
# 1. Redis DBs must be empty:
redis-cli -n 10 FLUSHDB; redis-cli -n 11 FLUSHDB; redis-cli -n 12 FLUSHDB
# 2. warmstart_56pct.py must exist at experiments/hotpotqa_3run/warmstart_56pct.py
# 3. warmstart_56pct.py must NOT be in problems/chains/hotpotqa/static/initial_programs/
# 4. All 4 LLM servers must be running (script checks this automatically)
```

### Resolved Launch Commands (Attempt 5)

All runs share: `NO_PROXY=localhost,127.0.0.1,10.226.17.25,10.226.72.211,10.226.15.38,10.226.185.131`

```bash
# Run A -- Control (launched at 22:36 UTC)
/home/jovyan/envs/evo_fast/bin/python run.py \
  problem.name=chains/hotpotqa/static \
  redis.db=10 \
  llm_base_url=http://10.226.72.211:8777/v1 \
  primary_resolution=10 \
  max_mutations_per_generation=8 \
  max_elites_per_generation=5 \
  max_generations=50

# Run B -- High mutation budget (launched at 22:41 UTC, +5 min stagger)
/home/jovyan/envs/evo_fast/bin/python run.py \
  problem.name=chains/hotpotqa/static \
  redis.db=11 \
  llm_base_url=http://10.226.15.38:8777/v1 \
  primary_resolution=10 \
  max_mutations_per_generation=16 \
  max_elites_per_generation=8 \
  max_generations=50

# Run C -- Warm-start (launched at 22:46 UTC, +10 min stagger)
# warmstart_56pct.py injected into initial_programs/ at 22:46, removed at 22:51
/home/jovyan/envs/evo_fast/bin/python run.py \
  problem.name=chains/hotpotqa/static \
  redis.db=12 \
  llm_base_url=http://10.226.185.131:8777/v1 \
  primary_resolution=10 \
  max_mutations_per_generation=8 \
  max_elites_per_generation=5 \
  max_generations=50
```

## Expected Runtime

- ~8-14 min/generation (mutations are parallel via asyncio.gather; validation ~2 min batched)
- 50 generations = **7-12 hours** per run
- Run B may take slightly longer per generation (16 mutations vs 8)

## Checkpoint Protocol

At generations 10, 20, 30, and 50 -- extract best program and evaluate on test set:
```bash
# Extract top program from each run
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/top_programs.py --db=10 --top=3 --save-dir experiments/hotpotqa_3run/top_programs_a/
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/top_programs.py --db=11 --top=3 --save-dir experiments/hotpotqa_3run/top_programs_b/
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/top_programs.py --db=12 --top=3 --save-dir experiments/hotpotqa_3run/top_programs_c/

# Evaluate best program on test set
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python \
  problems/chains/hotpotqa/static/validate.py \
  --program experiments/hotpotqa_3run/top_programs_a/rank01_*.py \
  --split test --llm-base-url http://10.226.17.25:8001/v1
```

Checkpoint reports are generated by `experiments/hotpotqa_3run/checkpoint_daemon.py` (PID 1420198 in Attempt 5) and stored in `experiments/hotpotqa_3run/reports/`.

## Stopping/Extension Rules

- **Normal**: stop at generation 50
- **Early stop**: 10 consecutive gens with no improvement AND best EM < 50%
- **Extension**: `redis.resume=true` is **broken** for MAP-Elites archive reinit. Use "leapfrog" continuation instead:
  1. Extract top-3 programs: `tools/top_programs.py --db=N --top=3`
  2. Copy to `initial_programs/`
  3. Start fresh run on NEW Redis DB with `redis.resume=false max_generations=50`
  4. This loses archive diversity/lineage but preserves best solutions as seeds

**Constraint discovered 2026-02-27 23:45 UTC**: `redis.resume=true` does not correctly reinitialize MAP-Elites archive. The original research plan's extension mechanism (Section 8.3) is invalidated. `max_generations` revised from 30 to 50.

## Decision Matrix at Generation 10

| Best Val EM | Curve | Action |
|-------------|-------|--------|
| >= 55% | Rising | Continue. Strong signal. |
| 50-55% | Rising | Continue. On track. |
| 45-50% | Rising | Continue to gen 20, re-evaluate. |
| 45-50% | Flat | Check mutation quality and archive diversity. |
| < 45% | Any | Debug immediately. |

## Attempt History

Full details with exact launch commands for every attempt are in the [PR #65 Experiment Log comment](https://github.com/KhrulkovV/gigaevo-core-internal/pull/65).

| Attempt | Date (UTC) | Status | Root Cause | Best Metric | Fix |
|---------|-----------|--------|------------|-------------|-----|
| 1 | 2026-02-27 23:23 | ABORTED | `NO_PROXY` missing mutation server IPs | 0 mutations | Added all IPs to `NO_PROXY` |
| 2 | 2026-02-27 (after #1) | ABORTED | `DynamicBehaviorSpace._can_accept_program` bug | 56.3% val EM (Run C) | Commit `4eea967` |
| 3 | 2026-02-28 01:06 | ABORTED | `NO_PROXY` re-typed, missing chain server IP | 0 validations | Created `launch.sh` (commit `a08c020`) |
| 4 | 2026-02-28 ~22:26 | ABORTED | Warm-start seed in `initial_programs/` at launch (OFAT violation) | Not recorded | Commit `10057ee` (timed injection) |
| 5 | 2026-02-28 22:36 | **ACTIVE** | -- | In progress | -- |

## Incident: vLLM Version Heterogeneity (Run A, 2026-02-28)

Discovered during monitoring that the three mutation servers were running **different vLLM versions**:

| Server | Run | vLLM version (original) | Reasoning chars (test) |
|--------|-----|--------------------------|------------------------|
| 10.226.72.211 | A | 0.14.0rc1.dev140 ⚠️ OLD | 301 chars (severely suppressed) |
| 10.226.15.38  | B | 0.16.0rc2.dev221 ✓ | 988 chars (good) |
| 10.226.185.131 | C | 0.10.1.dev377 | 576 chars (adequate) |

The old vLLM on server A was spending tokens on response content rather than internal reasoning,
yielding weaker mutations. This **confounds the A vs B and A vs C comparisons**.

**Resolution**: User relaunched server A with vLLM 0.16.0rc2.dev221 (same build as B).
Quality test confirmed parity (A=604, B=295, C=439 reasoning chars — all adequate).
Old Run A (PID 1411630) was terminated. Redis DB 10 flushed. Run A relaunched at 2026-02-28 08:18 UTC.

**Impact on data**: Run A gens 1–{generation from original run that was aborted} are **INVALID** and excluded from analysis.
Comparison between B and C (same vLLM version within acceptable range) is unaffected.

---

## Results

### Attempt 5 (Active)

**PIDs (original)**: A=1411630 (terminated), B=1415664, C=1418523, checkpoint_daemon=1420198 (restarted)
**PIDs (after Run A relaunch)**: A=1512530, checkpoint_daemon=1513580

| Run | Confirmed Seeds | Seed EM | Note |
|-----|----------------|---------|------|
| A | 1/1 (baseline only) | ~42-43% | Relaunched 2026-02-28 08:18 UTC; fresh DB |
| B | 1/1 (baseline only) | ~42-43% | Continuing from gen 21 |
| C | 2/2 (baseline + warmstart_56pct) | 42-43% / 56.3% | Continuing from gen 17 |

### Generation Checkpoints (Attempt 5)

| Gen | Run A Val EM | Run A Test EM | Run B Val EM | Run B Test EM | Run C Val EM | Run C Test EM |
|-----|-------------|---------------|-------------|---------------|-------------|---------------|
| 10 | | | | | | |
| 20 | | | | | | |
| 30 | | | | | | |
| 50 | | | | | | |

### Final Results
*TBD -- experiment in progress*

## Key Files

| File | Purpose |
|------|---------|
| `launch.sh` | Authoritative launch script (preflight checks, staggered starts) |
| `launch.log` | Runtime log from launch.sh (PIDs, timestamps) |
| `warmstart_56pct.py` | Warm-start seed (56.3% val EM, from Attempt 2 Run C) |
| `run_a.log` | Run A stdout/stderr |
| `run_b.log` | Run B stdout/stderr |
| `run_c.log` | Run C stdout/stderr |
| `checkpoint_daemon.py` | Automated checkpoint reporting at gen 10/20/30/50 |
| `reports/` | Checkpoint reports (gen 10, 20, etc.) |
| `plots/` | Fitness curve comparisons |
