# Pre-Registration: cold_start — Basin Escape via n=4 Cold-Start Replication

**Date**: 2026-03-08
**Pre-registration commit**: `$(git rev-parse HEAD)`
**Design doc**: `experiments/hotpotqa/cold_start/01_design.md`
**Review doc**: `experiments/hotpotqa/cold_start/02_review.md`
  - Round 1: NEEDS REVISION — Prof. Andrei Volkov, 2026-03-08
  - Round 2: APPROVED — Prof. Andrei Volkov, 2026-03-08

> **Protocol rule**: This file must be committed BEFORE any run launches and BEFORE any
> code changes for this experiment. The commit hash above is the pre-registration anchor.
> Any deviation after this commit requires a numbered Amendment below.

---

## Hypothesis Summary

**Research question**: Does initializing the GigaEvo archive from the unoptimized baseline
chain (cold start — no `program_loader.problem_dir`) produce a higher test EM than the
warm-start historical distribution (mean 57.11%, SD 1.68pp, n=3 unconfounded runs under
F1+600+single-parent), when run with n=4 independent replications under identical conditions?

The ddce37b4 warm-start seed is confirmed to be at a local optimum in the HotpotQA static-chain
fitness landscape: stagnation has been observed in 12 consecutive independent runs at birth-gen
4–8, with no post-stagnation improvement regardless of fitness metric, val sample size, mutation
prompts, parent count, or crossover. This experiment tests whether that ceiling is basin-specific
(cold start escapes it) or domain-wide (cold start converges to the same plateau).

Full hypotheses and verdict tables: `01_design.md` §2 and §8.

**Primary tests** (all from `01_design.md` §8):

- **Test 1** — One-sample t-test: cold_mean vs. warm-start reference (57.11%).
  - t = (cold_mean − 57.11%) / (cold_SD / sqrt(4)), df=3, one-sided α=0.05
  - cold_mean >= 60.0% AND p < 0.05 → **POSITIVE** (basin escape confirmed)
  - cold_mean >= 60.0% AND p >= 0.05 → **SUGGESTIVE** (N >= 8 required)
  - cold_mean in [59.51%, 60.0%) AND p < 0.05 → **SUGGESTIVE** (above noise floor, replicate)
  - cold_mean in [59.51%, 60.0%) AND p >= 0.05 → **SUGGESTIVE** (above noise floor, N >= 8)
  - cold_mean in [54.71%, 59.51%) → **NULL** (stagnation ceiling domain-wide)
  - cold_mean < 54.71% → **NEGATIVE** (warm-start quality advantage survives 25 gens)
- **Test 2** — One-sample t-test vs. GEPA (62.3%): secondary absolute benchmark
- **Test 3** — Mean birth-generation of best-by-val program >= 10: stagnation timing (exploratory)
- **Test 4** — Inter-run SD: primary secondary result; characterises landscape variance

**MDE (80% power)**: 3.60pp at SD=2pp, N=4 (formula: (t_alpha + t_beta) × sigma / sqrt(N)
= (2.353 + 1.250) × 2 / sqrt(4)); 5.40pp at SD=3pp.

---

## Dataset Checksums

All files relative to `problems/chains/hotpotqa/dataset/`:

| File | sha256 | Rows |
|------|--------|------|
| `HotpotQA_train.jsonl` | `9d8b0ba2a19d124fa243c88b650b2ecd42e5c771bc4e039553389c6b9566ef94` | 1000 |
| `HotpotQA_test.jsonl` | `c46bfb185e448bf1b92cb75bb5ab967f3211051793967f01500f453945046b0d` | 300 |

Verify before launch:

```bash
sha256sum problems/chains/hotpotqa/dataset/HotpotQA_train.jsonl
sha256sum problems/chains/hotpotqa/dataset/HotpotQA_test.jsonl
```

Both must match the table above exactly. Any mismatch is a hard stop — do not launch.

---

## Appendix A Verification: Cold-Start Archive Initialization

Before launch, confirm the following in the codebase (required by `01_design.md` Appendix A):

**A1 — Cold-start behavior**: Running `run.py` without `program_loader.problem_dir` must
initialize the archive from the problem directory's default program (the unoptimized baseline
chain). Confirm the code path responsible and document it here:

```
Code path: [researcher to fill in during Phase 3 — e.g., gigaevo/evolution/archive/init.py]
Confirmed: [ ]
```

**A2 — `static_f1_600` default program is unoptimized baseline**:

```bash
# Inspect the default program in the problem directory
ls problems/chains/hotpotqa/static_f1_600/
cat problems/chains/hotpotqa/static_f1_600/<default_program_file>
# Must NOT contain evolved prompts from ddce37b4 or any other evolved run
# Confirmed: [ ]
```

Expected gen-0 val EM: 0.40–0.45 (matching zero-shot baseline of 42.3%). If the default
program produces gen-0 val EM > 0.55, it is an evolved program — halt and replace with the
true baseline before any launch.

**A3 — Hydra defaults still hold**:

```bash
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=99 \
    --cfg job 2>&1 | grep -E "num_parents|max_elites"
# Expected: num_parents: 2   max_elites_per_generation: 5
# Confirmed: [ ]
```

---

## Run Design Table

All four runs are identical in every configuration parameter. The experiment is a pure n=4
replication of the cold-start F1+default+600 condition.

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | Seed | `num_parents` | `max_elites` | `max_mut` | `stage_timeout` | `dag_timeout` | `max_gen` | Val N | Fitness |
|-----|-------|-----------|-----------|-----------|----------------|------|:-------------:|:------------:|:---------:|:--------------:|:------------:|:--------:|:-----:|:-------:|
| T1 | cold-1 | 0 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | **Cold** | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |
| T2 | cold-2 | 1 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | **Cold** | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |
| T3 | cold-3 | 2 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | **Cold** | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |
| T4 | cold-4 | 3 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | **Cold** | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |

**Bold values require explicit Hydra overrides** (not defaults):
- `num_parents=1` — default in `config/constants/evolution.yaml` is **2**
- `max_elites_per_generation=8` — default is **5**

**Cold-start condition**: Do NOT pass `program_loader.problem_dir` in any launch command.
The absence of this argument is what defines the cold-start condition.

**Chain LLM** (`HOTPOTQA_CHAIN_URL` env var, one per run):

| Run | Host | Chain LLM URL |
|-----|------|---------------|
| T1 | 10.226.17.25 (host A) | `http://10.226.17.25:8001/v1` |
| T2 | 10.226.17.25 (host A) | `http://10.226.17.25:8000/v1` |
| T3 | 10.225.185.235 (host B) | `http://10.225.185.235:8001/v1` |
| T4 | 10.225.185.235 (host B) | `http://10.225.185.235:8000/v1` |

**Mutation LLM** (`llm_base_url` Hydra override, one per run):

| Run | Mutation LLM URL |
|-----|------------------|
| T1 | `http://10.226.72.211:8777/v1` |
| T2 | `http://10.226.15.38:8777/v1` |
| T3 | `http://10.226.185.131:8777/v1` |
| T4 | `http://10.225.51.251:8777/v1` |

> **Note on host clustering**: T1 and T2 share chain LLM host A; T3 and T4 share chain LLM
> host B. This two-cluster structure is a pre-registered known limitation (see `01_design.md`
> §9, server load asymmetry). Report host-stratified means (mean of T1/T2 vs. mean of T3/T4)
> in Phase 5 as a diagnostic; flag if they differ by > 3pp.

> **Note on chain URL**: `HOTPOTQA_CHAIN_URL` is consumed by
> `problems/chains/hotpotqa/shared_config.py` at runtime and does NOT appear in `--cfg job`
> output. Verify it by inspecting `shared_config.py` or the gen-0 execution log.

---

## Config Review Commands

Run these **before** any launch to verify the resolved Hydra config. No execution occurs.
The `--cfg job` flag prints the merged config and exits.

Because all four runs are identical in configuration (differing only in `redis.db` and
`llm_base_url`), verifying one run's `--cfg job` output confirms the config for all four.
However, run the check for all four to detect any copy-paste error in the launch commands.

```bash
# ── T1: cold-1 — verify config ────────────────────────────────────────────────
# Critical checks: num_parents=1 (NOT 2), max_elites_per_generation=8 (NOT 5),
#   NO program_loader.problem_dir, stage_timeout=6000, dag_timeout=9000,
#   max_mutations_per_generation=8, prompts=default (no hotpotqa prompts_dir)
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=0 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.226.72.211:8777/v1 \
    --cfg job 2>&1 | grep -E "num_parents|max_elites|stage_timeout|dag_timeout|max_mutations|problem|redis|program_loader|prompts_dir"

# ── T2: cold-2 ────────────────────────────────────────────────────────────────
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=1 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.226.15.38:8777/v1 \
    --cfg job 2>&1 | grep -E "num_parents|max_elites|stage_timeout|dag_timeout|max_mutations|problem|redis|program_loader|prompts_dir"

# ── T3: cold-3 ────────────────────────────────────────────────────────────────
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=2 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.226.185.131:8777/v1 \
    --cfg job 2>&1 | grep -E "num_parents|max_elites|stage_timeout|dag_timeout|max_mutations|problem|redis|program_loader|prompts_dir"

# ── T4: cold-4 ────────────────────────────────────────────────────────────────
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=3 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.225.51.251:8777/v1 \
    --cfg job 2>&1 | grep -E "num_parents|max_elites|stage_timeout|dag_timeout|max_mutations|problem|redis|program_loader|prompts_dir"
```

**What to verify in the output for each run**:

| Parameter | T1 | T2 | T3 | T4 |
|-----------|:--:|:--:|:--:|:--:|
| `num_parents` | **1** | **1** | **1** | **1** |
| `max_elites_per_generation` | **8** | **8** | **8** | **8** |
| `max_mutations_per_generation` | 8 | 8 | 8 | 8 |
| `stage_timeout` | 6000 | 6000 | 6000 | 6000 |
| `dag_timeout` | 9000 | 9000 | 9000 | 9000 |
| `program_loader.problem_dir` | **absent** | **absent** | **absent** | **absent** |
| `evolution_context.prompts_dir` | not hotpotqa | not hotpotqa | not hotpotqa | not hotpotqa |
| `mutation_operator.prompts_dir` | not hotpotqa | not hotpotqa | not hotpotqa | not hotpotqa |

`program_loader.problem_dir` must be **absent** from the resolved config for all four runs.
If it appears (e.g., resolving to the ddce37b4 seed directory), the run is a warm-start run —
do not launch until corrected.

---

## Pre-Launch Checklist

Complete every item in order before launching any run. Each item is a hard gate — do not
proceed if any check fails.

```
[ ] 1. DATASET INTEGRITY
        sha256sum problems/chains/hotpotqa/dataset/HotpotQA_train.jsonl
        → must match 9d8b0ba2a19d124fa243c88b650b2ecd42e5c771bc4e039553389c6b9566ef94
        sha256sum problems/chains/hotpotqa/dataset/HotpotQA_test.jsonl
        → must match c46bfb185e448bf1b92cb75bb5ab967f3211051793967f01500f453945046b0d

[ ] 2. APPENDIX A VERIFICATION COMPLETE
        A1: cold-start archive init code path confirmed and documented above
        A2: static_f1_600 default program inspected — confirmed unoptimized baseline
        A3: Hydra defaults confirmed (num_parents: 2, max_elites_per_generation: 5)

[ ] 3. REDIS EMPTY
        PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/flush.py --db 0 1 2 3
        (preview — confirm 0 keys in each DB before proceeding)
        PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/flush.py --db 0 1 2 3 --confirm
        (execute flush + kill any stale exec_runner workers)

[ ] 4. EXEC_RUNNER WORKERS DEAD
        ps aux | grep exec_runner
        (must show no surviving workers from crossover or prior experiments)
        (tools/flush.py --confirm handles this, but verify afterward)

[ ] 5. CHAIN SERVER HEALTH + THINKING MODE
        For each of the 4 chain endpoints, verify:
          a. Server responds:
               curl --noproxy <host> http://<host>:<port>/v1/models
          b. Thinking mode active (response must contain <think> blocks):
               curl --noproxy <host> -s -X POST http://<host>:<port>/v1/chat/completions \
                 -H "Authorization: Bearer None" -H "Content-Type: application/json" \
                 -d '{"model":"Qwen/Qwen3-8B","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":200}' \
                 | grep "<think>"
          c. Context window >= 32768:
               curl --noproxy <host> http://<host>:<port>/v1/models | grep -i max_model_len
        Endpoints: 10.226.17.25:8001, 10.226.17.25:8000,
                   10.225.185.235:8001, 10.225.185.235:8000

[ ] 6. MUTATION LLM SERVER HEALTH
        For each of the 4 mutation LLM endpoints, verify:
          curl --noproxy <host> http://<host>:8777/v1/models
        Endpoints: 10.226.72.211:8777, 10.226.15.38:8777,
                   10.226.185.131:8777, 10.225.51.251:8777

[ ] 7. CONFIG REVIEW — ALL 4 RUNS
        Run all 4 --cfg job commands from the "Config Review Commands" section above.
        Verify every row in the parameter table. Hard stop if any value is wrong.
        Critical checks (all 4 runs):
          - num_parents=1  (default is 2 — easy to miss)
          - max_elites_per_generation=8  (default is 5 — easy to miss)
          - program_loader.problem_dir is ABSENT  (present → warm start, not cold start)
          - max_mutations_per_generation=8
          - stage_timeout=6000 / dag_timeout=9000

[ ] 8. NO PROGRAM_LOADER IN LAUNCH COMMANDS
        Visually inspect all 4 launch commands below.
        Confirm that none contains "program_loader" in any form.
        This is the defining check for the cold-start condition.

[ ] 9. STATIC_F1_600 PROBLEM DIRECTORY
        ls problems/chains/hotpotqa/static_f1_600/
        (must contain validate.py, task_description.txt, metrics.yaml)
        cat <default program file> — must be unoptimized baseline (Appendix A2)

[ ] 10. NO_PROXY ENVIRONMENT
        echo $no_proxy
        (must include all 8 server IPs: 10.226.17.25, 10.225.185.235,
         10.226.72.211, 10.226.15.38, 10.226.185.131, 10.225.51.251)
        If missing:
          export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,\
          10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251"
          export no_proxy="$NO_PROXY"

[ ] 11. PHASE ORDER CHECK
        bash tools/experiment/check_phase_order.sh hotpotqa/cold_start
        (must pass before launch)
```

---

## Launch Commands

> **Infrastructure note**: The chain LLM is set via the `HOTPOTQA_CHAIN_URL` environment
> variable, consumed by `problems/chains/hotpotqa/shared_config.py`. It does NOT appear in
> `--cfg job` output. The mutation LLM is set via `llm_base_url=` Hydra override.
>
> **COLD START**: None of these commands include `program_loader.problem_dir`.
> This is intentional and defines the cold-start condition. Do not add it.

```bash
export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251"
export no_proxy="$NO_PROXY"

# ── T1 (cold-1): F1 + default prompts + 600-sample, num_parents=1 ─────────────
# Host A, chain port 8001, mutation LLM 10.226.72.211
HOTPOTQA_CHAIN_URL=http://10.226.17.25:8001/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=0 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.226.72.211:8777/v1 \
    > experiments/hotpotqa/cold_start/run_T1.log 2>&1 &
echo "T1 PID: $!"

# ── T2 (cold-2): F1 + default prompts + 600-sample, num_parents=1 ─────────────
# Host A, chain port 8000, mutation LLM 10.226.15.38
HOTPOTQA_CHAIN_URL=http://10.226.17.25:8000/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=1 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.226.15.38:8777/v1 \
    > experiments/hotpotqa/cold_start/run_T2.log 2>&1 &
echo "T2 PID: $!"

# ── T3 (cold-3): F1 + default prompts + 600-sample, num_parents=1 ─────────────
# Host B, chain port 8001, mutation LLM 10.226.185.131
HOTPOTQA_CHAIN_URL=http://10.225.185.235:8001/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=2 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.226.185.131:8777/v1 \
    > experiments/hotpotqa/cold_start/run_T3.log 2>&1 &
echo "T3 PID: $!"

# ── T4 (cold-4): F1 + default prompts + 600-sample, num_parents=1 ─────────────
# Host B, chain port 8000, mutation LLM 10.225.51.251
HOTPOTQA_CHAIN_URL=http://10.225.185.235:8000/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=3 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.225.51.251:8777/v1 \
    > experiments/hotpotqa/cold_start/run_T4.log 2>&1 &
echo "T4 PID: $!"
```

Record all four PIDs immediately after launch for the monitoring script and watchdog.

---

## Gen-0 Verification (immediately after launch — hard gate)

This is the critical cold-start confirmation step. Do not walk away until gen-0 is verified.

**Expected gen-0 values** (cold start from unoptimized baseline chain, F1 fitness):

| Metric | Expected range | Warm-start baseline (reference) | Action if violated |
|--------|---------------|--------------------------------|--------------------|
| Val EM (first completed evaluation) | 0.40–0.45 | ~0.60 (ddce37b4 seed) | > 0.55 → ABORT |
| Val F1 (gen-0 frontier) | ~0.55–0.65 | ~0.70 (ddce37b4 re-scored) | 0.0 → ABORT |
| `valid_frontier_em` Redis key | populated after gen 0 | populated | absent → diagnose |

**The gen-0 val EM check applies to the first completed program evaluation** (the initial
archive entry, before any mutations). In the logs this appears as the first recorded
`valid_iter_fitness` entry. In Redis, after 1 completed evaluation, read:

```bash
# Check val EM from first completed evaluation — do this within 10 minutes of launch
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python -c "
import redis, json
for db in [0, 1, 2, 3]:
    r = redis.Redis(db=db)
    # valid_iter_fitness_mean contains per-generation records with 'em' field
    key = 'chains/hotpotqa/static_f1_600:metrics:history:program_metrics:valid_iter_fitness_mean'
    latest = r.lrange(key, -1, -1)
    if latest:
        entry = json.loads(latest[0])
        print(f'DB {db}: gen={entry.get(\"s\")}, val_em={entry.get(\"em\")}, val_f1={entry.get(\"v\")}')
    else:
        print(f'DB {db}: no data yet')
"
```

**If val EM > 0.55 for any run at gen 0**: ABORT that run immediately. The cold-start
condition was violated — `program_loader.problem_dir` was applied despite not being in the
launch command (check for shell variable bleed or Hydra defaults). Diagnose before restarting.

**If val EM is in 0.40–0.45**: cold start confirmed. Continue monitoring normally.

**Additional gen-0 checks**:

```bash
# Confirm valid_frontier_em key populated for all 4 runs
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python -c "
import redis
for db in [0, 1, 2, 3]:
    r = redis.Redis(db=db)
    key = 'chains/hotpotqa/static_f1_600:metrics:history:program_metrics:valid_frontier_em'
    val = r.lrange(key, -1, -1)
    print(f'DB {db}: valid_frontier_em latest = {val}')
"
# Expected: a non-empty list entry for each DB.
# Absent key → static_f1_600/validate.py not populating valid_frontier_em → diagnose.
```

---

## Monitoring

Create `experiments/hotpotqa/cold_start/run_status.sh` immediately after launch with actual PIDs:

```bash
#!/usr/bin/env bash
# experiments/hotpotqa/cold_start/run_status.sh  (fill in PIDs after launch)
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/status.py \
    --run chains/hotpotqa/static_f1_600@0:cold-1 \
    --run chains/hotpotqa/static_f1_600@1:cold-2 \
    --run chains/hotpotqa/static_f1_600@2:cold-3 \
    --run chains/hotpotqa/static_f1_600@3:cold-4 \
    --pid L:<T1_pid> \
    --pid L:<T2_pid> \
    --pid L:<T3_pid> \
    --pid L:<T4_pid> \
    --watchdog <watchdog_pid>
```

All four runs share the same Redis prefix (`chains/hotpotqa/static_f1_600`) on different DBs.

**Key monitoring thresholds** (from `01_design.md` §10):

| Condition | Run(s) | Action |
|-----------|--------|--------|
| Val EM > 0.55 at gen 0 (first eval) | Any | ABORT — warm start detected |
| Val fitness = 0.0 at gen 0 | Any | Halt; diagnose |
| `<think>` blocks absent >= 5% at gen 1 | Any | Invalidate run (thinking mode off) |
| Invalidity > 50% at gen 5 | Any | Pause; diagnose stage_timeout; if median eval > 5000s, increase to 8000 |
| Invalidity > 90% at gen 10 | Any | Invalidate run |
| Stagnation: no frontier improvement >= 10 gens AND gen >= 15 | Any | Early completion permitted |
| Frontier still improving at gen 20 | Any | Do NOT terminate; may pre-register extension to 40 gens (must register before gen 20) |

**Cold-start convergence note**: Early generations will have low mutation throughput (1 mutation
at gen 0, ramping to 8/gen by gen 3–5 as the archive fills). Report actual mutations/gen from
logs at gen 0–5 in Phase 5.

---

## Phase Gate: Gen-5 Check

Before proceeding past generation 5, confirm for all four runs:

```
[ ] All 4 runs have produced at least 1 valid program by gen 5
[ ] Invalidity rate < 50% for all runs at gen 5
[ ] Val EM > 0 and val F1 > 0 for all runs
[ ] valid_frontier_em key populated in all 4 Redis DBs
[ ] Gen-0 cold-start confirmed: val EM at gen 0 was 0.40–0.45 for all runs
[ ] mutations_per_generation at gen 5 is approaching 8 for all runs
    (gen-0 will be 1; gen-1 will be small; by gen 3–5 should be 6–8)
[ ] Thinking mode verified from gen-1 logs (grep "<think>" in exec_runner output)
[ ] Host-stratified progress check: T1/T2 and T3/T4 at comparable gen counts
```

---

## Stop Criteria Summary

| Condition | Run(s) | Action |
|-----------|--------|--------|
| Val EM > 0.55 at gen 0 (first eval) | Any | ABORT — cold-start condition violated |
| Val fitness = 0.0 at gen 0 | Any | Halt; diagnose |
| `valid_frontier_em` absent after gen 0 | Any | Halt; diagnose validate.py |
| `<think>` blocks absent >= 5% at gen 1 | Any | Invalidate (thinking mode off) |
| Invalidity > 50% at gen 5 | Any | Pause; diagnose; increase stage_timeout to 8000 if needed |
| Invalidity > 90% at gen 10 | Any | Invalidate — exclude from all analyses |
| max_elites confirmed = 5 (not 8) post-hoc | Any | Invalidate — combinatorics wrong |
| num_parents confirmed = 2 (not 1) post-hoc | Any | Invalidate — crossover not single-parent |
| program_loader.problem_dir applied post-hoc | Any | Invalidate — warm start, not cold start |
| Stagnation (>= 10 gens no improvement) AND gen >= 15 | Any | Early completion permitted |
| All 4 runs still improving at gen 20 | All | Pre-register 40-gen extension amendment before gen 20 |

If 1 or 2 runs are invalidated: adjust t-test to available N (wider CI, higher critical t).
If only 1 run is valid: replace t-test with descriptive summary; cap verdict at SUGGESTIVE.

---

## Archive Protocol (after completion)

Run these commands after all runs have completed (or been terminated by stop criteria).
Archive before flushing Redis.

```bash
bash tools/experiment/archive_run.sh --exp cold_start --run "chains/hotpotqa/static_f1_600@0:cold-1" --upload
bash tools/experiment/archive_run.sh --exp cold_start --run "chains/hotpotqa/static_f1_600@1:cold-2" --upload
bash tools/experiment/archive_run.sh --exp cold_start --run "chains/hotpotqa/static_f1_600@2:cold-3" --upload
bash tools/experiment/archive_run.sh --exp cold_start --run "chains/hotpotqa/static_f1_600@3:cold-4" --upload
```

Only after all four archives are confirmed uploaded may Redis DBs 0–3 be flushed:

```bash
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/flush.py --db 0 1 2 3
# verify 0 keys, then:
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/flush.py --db 0 1 2 3 --confirm
```

---

## Test Evaluation

After all runs complete (gen 25 or early completion), evaluate the best-by-val program from
each run on the fixed 300-sample test set.

Create `experiments/hotpotqa/cold_start/run_test_eval.sh`:

```bash
#!/usr/bin/env bash
# Test evaluations for cold_start experiment — 4 runs on fixed 300-sample test set.
# All runs use static_f1_600 prefix and thinking mode Qwen3-8B.
# Primary result: cold_mean, cold_SD, one-sample t-test vs. 57.11% reference.
#
# Usage:
#   GIGAEVO_PYTHON=/home/jovyan/envs/evo_fast/bin/python \
#   bash experiments/hotpotqa/cold_start/run_test_eval.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-/home/jovyan/envs/evo_fast/bin/python}
export PYTHONPATH="$PROJ"
EVAL_SCRIPT="$PROJ/experiments/hotpotqa/thinking/gen10_test_eval.py"
RESULTS_PATH="$PROJ/experiments/hotpotqa/cold_start/test_evals/results.json"
LOG_DIR="$PROJ/experiments/hotpotqa/cold_start/test_evals"
mkdir -p "$LOG_DIR"

# Chain servers — same assignment as training
CHAIN_URL_T1="http://10.226.17.25:8001/v1"
CHAIN_URL_T2="http://10.226.17.25:8000/v1"
CHAIN_URL_T3="http://10.225.185.235:8001/v1"
CHAIN_URL_T4="http://10.225.185.235:8000/v1"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251"
export no_proxy="$NO_PROXY"

# ── Preflight: thinking-mode verification ─────────────────────────────────────
echo "[preflight] Verifying thinking mode on all 4 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_T1" "$CHAIN_URL_T2" "$CHAIN_URL_T3" "$CHAIN_URL_T4"; do
    HOST="${CHAIN_URL#http://}"; HOST="${HOST%%/*}"; HOST="${HOST%%:*}"
    RESPONSE=$(curl --noproxy "$HOST" -s --connect-timeout 10 --max-time 90 \
        -X POST "$CHAIN_URL/chat/completions" \
        -H "Authorization: Bearer None" \
        -H "Content-Type: application/json" \
        -d '{"model":"Qwen/Qwen3-8B","messages":[{"role":"user","content":"What is 2+2? Answer:"}],"max_tokens":200,"temperature":0.1}' \
        2>/dev/null || echo "CURL_FAIL")
    if echo "$RESPONSE" | grep -q "<think>"; then
        echo "[preflight] OK: $CHAIN_URL (thinking mode confirmed)"
    else
        echo "[preflight] FAIL: $CHAIN_URL NOT in thinking mode — aborting."
        exit 1
    fi
done
echo "[preflight] All 4 chain endpoints verified."
echo ""

# ── T1 (cold-1): DB 0, host A port 8001 ──────────────────────────────────────
echo "================================================================"
echo "[T1] chains/hotpotqa/static_f1_600  db=0  chain=$CHAIN_URL_T1"
echo "cold-1: one of 4 independent cold-start runs"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_T1" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label T1 \
    --redis-db 0 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_T1.log"
echo ""

# ── T2 (cold-2): DB 1, host A port 8000 ──────────────────────────────────────
echo "================================================================"
echo "[T2] chains/hotpotqa/static_f1_600  db=1  chain=$CHAIN_URL_T2"
echo "cold-2: one of 4 independent cold-start runs"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_T2" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label T2 \
    --redis-db 1 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_T2.log"
echo ""

# ── T3 (cold-3): DB 2, host B port 8001 ──────────────────────────────────────
echo "================================================================"
echo "[T3] chains/hotpotqa/static_f1_600  db=2  chain=$CHAIN_URL_T3"
echo "cold-3: one of 4 independent cold-start runs"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_T3" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label T3 \
    --redis-db 2 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_T3.log"
echo ""

# ── T4 (cold-4): DB 3, host B port 8000 ──────────────────────────────────────
echo "================================================================"
echo "[T4] chains/hotpotqa/static_f1_600  db=3  chain=$CHAIN_URL_T4"
echo "cold-4: one of 4 independent cold-start runs"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_T4" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label T4 \
    --redis-db 3 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_T4.log"
echo ""

echo "================================================================"
echo "All test evals complete."
echo "Results: $RESULTS_PATH"
echo "Logs:    $LOG_DIR/test_eval_{T1,T2,T3,T4}.log"
echo ""
echo "Primary analysis (compute after all 4 evals):"
echo "  cold_mean = mean(T1, T2, T3, T4)"
echo "  cold_SD   = SD(T1, T2, T3, T4)"
echo "  t1 = (cold_mean - 57.11) / (cold_SD / 2)  [df=3, one-sided alpha=0.05, crit=2.353]"
echo "  t2 = (cold_mean - 62.3)  / (cold_SD / 2)  [vs GEPA]"
echo "  cold_mean >= 60.0% AND p<0.05 -> POSITIVE (basin escape confirmed)"
echo "  cold_mean >= 60.0% AND p>=0.05 -> SUGGESTIVE (N>=8 required)"
echo "  cold_mean < 54.71% -> NEGATIVE"
echo ""
echo "Host-stratified diagnostic:"
echo "  host_A_mean = mean(T1, T2)  [10.226.17.25]"
echo "  host_B_mean = mean(T3, T4)  [10.225.185.235]"
echo "  flag as i.i.d. concern if |host_A_mean - host_B_mean| > 3pp"
echo "================================================================"
```

---

## Statistical Analysis Plan

All analyses are pre-specified in `01_design.md` §8. Summary for the results analyst:

### Test 1 — One-sample t-test (primary)

```python
import numpy as np
from scipy import stats

# Fill in test EM values after evaluation
results = {
    "T1": ...,  # test EM for cold-1
    "T2": ...,  # test EM for cold-2
    "T3": ...,  # test EM for cold-3
    "T4": ...,  # test EM for cold-4
}

em_values = list(results.values())
cold_mean = np.mean(em_values)
cold_sd   = np.std(em_values, ddof=1)  # sample SD, ddof=1

# Test 1: vs. warm-start reference (57.11%)
ref_mean = 57.11
t1, p1 = stats.ttest_1samp(em_values, popmean=ref_mean, alternative="greater")
# df = 3, critical t = 2.353 for one-sided alpha=0.05

# Test 2: vs. GEPA (62.3%)
t2, p2 = stats.ttest_1samp(em_values, popmean=62.3, alternative="greater")

# Mean 95% CI (t-based, df=3)
t_crit_95 = stats.t.ppf(0.975, df=3)  # = 3.182 two-sided
ci_half = t_crit_95 * cold_sd / np.sqrt(4)
ci = (cold_mean - ci_half, cold_mean + ci_half)

print(f"cold_mean={cold_mean:.2f}%, cold_SD={cold_sd:.2f}pp")
print(f"Test 1: t={t1:.3f}, p={p1:.4f}  [vs ref 57.11%]")
print(f"Test 2: t={t2:.3f}, p={p2:.4f}  [vs GEPA 62.3%]")
print(f"95% CI: ({ci[0]:.2f}%, {ci[1]:.2f}%)")
```

### Sensitivity analysis (Test 1 re-run with pure-default reference)

```python
# Pure-default warm-start reference (push C=58.67%, crossover S=55.33%; n=2)
ref_mean_pure = 57.00
t1_sens, p1_sens = stats.ttest_1samp(em_values, popmean=ref_mean_pure, alternative="greater")
print(f"Sensitivity (ref=57.00%): t={t1_sens:.3f}, p={p1_sens:.4f}")
# If verdict changes between ref=57.11% and ref=57.00%, report as SENSITIVE
```

### Binomial CIs (individual runs)

```python
for label, em in results.items():
    p = em / 100
    se = np.sqrt(p * (1 - p) / 300)
    ci_lo, ci_hi = (p - 1.96*se)*100, (p + 1.96*se)*100
    print(f"{label}: {em:.2f}%  95% CI [{ci_lo:.2f}%, {ci_hi:.2f}%]")
```

### Host-stratified diagnostic

```python
host_A_mean = np.mean([results["T1"], results["T2"]])
host_B_mean = np.mean([results["T3"], results["T4"]])
host_diff = abs(host_A_mean - host_B_mean)
print(f"Host A (T1/T2): {host_A_mean:.2f}%")
print(f"Host B (T3/T4): {host_B_mean:.2f}%")
print(f"|diff| = {host_diff:.2f}pp  {'FLAG: > 3pp i.i.d. concern' if host_diff > 3 else 'OK'}")
```

### Test 3 — Birth-generation (exploratory)

From Redis `valid_frontier_fitness` trajectory: record the generation number of the
best-by-val program for each run (the generation where the frontier was last updated before
test evaluation). Mean birth-gen >= 10 → CONFIRMED (extended exploration).

### Test 4 — Inter-run SD

Report `cold_SD` and classify:
- < 2pp: tight distribution
- 2–5pp: moderate (similar to warm-start historical)
- > 5pp: wide (possible multiple attractors)

---

## Amendment Protocol

Any post-registration change requires a numbered amendment in this section before the change
is implemented. Each amendment must specify:
- **Type**: No confound / Confound introduced / Run invalidated
- **Change**: exact description of what changed
- **Commit**: commit hash implementing the change
- **Rationale**: why the change was necessary
- **Impact**: effect on validity of each run and on pre-registered tests

_(No amendments at pre-registration time.)_

---

## Closeout Checklist

After all test evals and archives complete:

```bash
bash tools/experiment/check_experiment_complete.sh hotpotqa/cold_start
gh pr merge --merge --delete-branch  # NOT --squash — preserves audit trail
```

---

*Pre-registration complete. The commit hash of this file is the experiment anchor.*
