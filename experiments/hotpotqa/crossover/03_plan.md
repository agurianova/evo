# Pre-Registration: crossover — Run D Replication + num_parents=2 Stagnation Attack (4 runs)

**Date**: 2026-03-08
**Pre-registration commit**: `c93e224`
**Design doc**: `experiments/hotpotqa/crossover/01_design.md`
**Review doc**: `experiments/hotpotqa/crossover/02_review.md`
  - Round 1: NEEDS REVISION — Prof. Andrei Volkov, 2026-03-08
  - Round 2: APPROVED — Prof. Andrei Volkov, 2026-03-08

> **Protocol rule**: This file must be committed BEFORE any run launches and BEFORE any
> code changes for this experiment. The commit hash above is the pre-registration anchor.
> Any deviation after this commit requires a numbered Amendment below.

---

## Hypothesis Summary

**Research question 1 (replication)**: Does the F1+NLP+600 configuration reliably produce
test EM above GEPA (62.3%) in a clean, pre-registered single-parent run (Run P) free of
mid-run amendments?

**Research question 2 (crossover)**: Does two-parent crossover (num_parents=2) break the
stagnation wall and push test EM above the single-parent ceiling, when applied to the
best-performing configuration F1+NLP+600 (Run Q vs. Run P)?

Full hypotheses and verdict tables: `01_design.md` §2 and §8.

**Primary tests**:
- Test 1 — Run P replication: test EM(P) >= 62.3% → H1(P) confirmed (GEPA beaten cleanly)
- Test 2 — Run Q vs. Run P crossover: delta >= +2.4pp AND McNemar p < 0.05 → POSITIVE
  (THROUGHPUT CONFOUNDED); delta >= +5.0pp AND p < 0.05 → STRONG POSITIVE
- Test 3 — Run R vs. Run S crossover (default prompts): delta >= +2.4pp AND p < 0.05 →
  POSITIVE (THROUGHPUT CONFOUNDED)
- Test 4 — Stagnation (exploratory): Q frontier improves after birth-gen 10 in >= 5 consec. gens
- Test 5 — Run P vs. Run S NLP-prompt effect: delta >= +2.4pp AND p < 0.05 → POSITIVE

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

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | `num_parents` | `max_elites` | `max_mut` | `stage_timeout` | `dag_timeout` | `max_gen` | Val N | Fitness |
|-----|-------|-----------|-----------|-----------|----------------|--------------|-------------|-----------|----------------|--------------|----------|-------|---------|
| P | cross-P | 0 | `hotpotqa_asi` | `hotpotqa` | `chains/hotpotqa/static_f1_600` | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |
| Q | cross-Q | 1 | `hotpotqa_asi` | `hotpotqa` | `chains/hotpotqa/static_f1_600` | 2 | **8** | 16 | 6000 | 9000 | 25 | 600 | F1 |
| R | cross-R | 2 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | 2 | **8** | 16 | 6000 | 9000 | 25 | 600 | F1 |
| S | cross-S | 3 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |

**Bold values require explicit Hydra overrides** (not defaults):
- `num_parents=1` for Runs P and S — default in `config/constants/evolution.yaml` is **2**
- `max_elites_per_generation=8` for all four runs — default is **5**

**Chain LLM** (`HOTPOTQA_CHAIN_URL` env var, one per run):

| Run | Chain LLM URL |
|-----|---------------|
| P | `http://10.226.17.25:8001/v1` |
| Q | `http://10.226.17.25:8000/v1` |
| R | `http://10.225.185.235:8001/v1` |
| S | `http://10.225.185.235:8000/v1` |

**Mutation LLM** (`llm_base_url` Hydra override, one per run):

| Run | Mutation LLM URL |
|-----|------------------|
| P | `http://10.226.72.211:8777/v1` |
| Q | `http://10.226.15.38:8777/v1` |
| R | `http://10.226.185.131:8777/v1` |
| S | `http://10.225.51.251:8777/v1` |

> **Note on chain URL**: `HOTPOTQA_CHAIN_URL` is consumed by
> `problems/chains/hotpotqa/shared_config.py` at runtime and does NOT appear in
> `--cfg job` output. Verify it by inspecting `shared_config.py` or the gen-0 log.

---

## Config Review Commands

Run these **before** any launch to verify the resolved Hydra config. No execution occurs.
The `--cfg job` flag prints the merged config and exits.

```bash
# ── Run P: F1+NLP+600, num_parents=1 [REPLICATION] ───────────────────────────
# Critical checks: num_parents=1 (NOT 2), max_elites_per_generation=8 (NOT 5),
#   prompts_dir resolves to .../hotpotqa in BOTH evolution_context AND
#   mutation_operator blocks, stage_timeout=6000
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    redis.db=0 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.226.72.211:8777/v1 \
    --cfg job 2>&1 | grep -E "num_parents|max_elites|stage_timeout|dag_timeout|prompts_dir|problem|redis"

# ── Run Q: F1+NLP+600, num_parents=2 [CROSSOVER PRIMARY] ─────────────────────
# Critical checks: num_parents=2, max_elites_per_generation=8,
#   prompts_dir resolves to .../hotpotqa in both blocks, stage_timeout=6000,
#   max_mutations_per_generation=16
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    redis.db=1 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=16 \
    max_elites_per_generation=8 \
    num_parents=2 \
    llm_base_url=http://10.226.15.38:8777/v1 \
    --cfg job 2>&1 | grep -E "num_parents|max_elites|stage_timeout|dag_timeout|prompts_dir|problem|redis"

# ── Run R: F1+default+600, num_parents=2 [CROSSOVER SECONDARY] ───────────────
# Critical checks: num_parents=2, max_elites_per_generation=8,
#   prompts_dir absent or null (default prompts — no NLP), stage_timeout=6000,
#   max_mutations_per_generation=16
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=2 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=16 \
    max_elites_per_generation=8 \
    num_parents=2 \
    llm_base_url=http://10.226.185.131:8777/v1 \
    --cfg job 2>&1 | grep -E "num_parents|max_elites|stage_timeout|dag_timeout|prompts_dir|problem|redis"

# ── Run S: F1+default+600, num_parents=1 [CONCURRENT CONTROL] ────────────────
# Critical checks: num_parents=1 (NOT 2), max_elites_per_generation=8 (NOT 5),
#   prompts_dir absent or null (default prompts), stage_timeout=6000
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
    --cfg job 2>&1 | grep -E "num_parents|max_elites|stage_timeout|dag_timeout|prompts_dir|problem|redis"
```

**What to verify in the output for each run**:

| Parameter | Run P | Run Q | Run R | Run S |
|-----------|-------|-------|-------|-------|
| `num_parents` | **1** | 2 | 2 | **1** |
| `max_elites_per_generation` | **8** | **8** | **8** | **8** |
| `stage_timeout` | 6000 | 6000 | 6000 | 6000 |
| `dag_timeout` | 9000 | 9000 | 9000 | 9000 |
| `max_mutations_per_generation` | 8 | 16 | 16 | 8 |
| `evolution_context.prompts_dir` | `.../hotpotqa` | `.../hotpotqa` | not hotpotqa | not hotpotqa |
| `mutation_operator.prompts_dir` | `.../hotpotqa` | `.../hotpotqa` | not hotpotqa | not hotpotqa |

For Runs P and Q, `prompts_dir` must resolve to the hotpotqa prompts path in **two separate
locations** in the resolved config: once under `evolution_context` (wired in
`config/pipeline/hotpotqa_asi.yaml` line 24) and once under `mutation_operator` (wired in
`config/algorithm/_base.yaml` line 46). A single occurrence means one location is missing
and NLP prompts will be silently inactive. Do not launch P or Q if either `prompts_dir` entry
is missing or does not resolve to the hotpotqa directory.

---

## Pre-Launch Checklist

Complete every item in order before launching any run. Each item is a hard gate — do not
proceed if any check fails.

```
[ ] 1. DATASET INTEGRITY
        sha256sum HotpotQA_train.jsonl → must match 9d8b0ba2...
        sha256sum HotpotQA_test.jsonl  → must match c46bfb18...

[ ] 2. REDIS EMPTY
        PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/flush.py --db 0 1 2 3
        (preview — confirm 0 keys in each DB before proceeding)
        PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/flush.py --db 0 1 2 3 --confirm
        (execute flush + kill any stale exec_runner workers)

[ ] 3. EXEC_RUNNER WORKERS DEAD
        ps aux | grep exec_runner
        (must show no surviving workers from push or prior experiments)
        (tools/flush.py --confirm handles this, but verify afterward)

[ ] 4. CHAIN SERVER HEALTH + CONTEXT WINDOW
        For each of the 4 chain endpoints, verify:
          a. Server responds: curl --noproxy <host> http://<host>:<port>/v1/models
          b. max_model_len=32768:
               curl --noproxy <host> http://<host>:<port>/v1/models | grep -i max
          c. Thinking mode active (test prompt returns <think> blocks):
               curl --noproxy <host> -s -X POST http://<host>:<port>/v1/chat/completions \
                 -H "Authorization: Bearer None" -H "Content-Type: application/json" \
                 -d '{"model":"Qwen/Qwen3-8B","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":100}' \
                 | grep "<think>"

[ ] 5. MUTATION LLM SERVER HEALTH
        For each of the 4 mutation LLM endpoints, verify:
          curl --noproxy <host> http://<host>:8777/v1/models

[ ] 6. CONFIG REVIEW — ALL 4 RUNS
        Run all 4 `--cfg job` commands from the "Config Review Commands" section above.
        Verify every row in the parameter table. Hard stop if any value is wrong.
        Specifically:
          - num_parents=1 for P and S (default is 2 — easy to miss)
          - max_elites_per_generation=8 for all four (default is 5 — easy to miss)
          - prompts_dir resolves to .../hotpotqa in TWO locations for P and Q

[ ] 7. NLP PROMPTS WIRING (Runs P, Q)
        From the `--cfg job` output for Run P and Run Q, confirm:
          evolution_context.prompts_dir: <path-ending-in-/hotpotqa>
          mutation_operator.prompts_dir: <path-ending-in-/hotpotqa>
        Both must appear. One missing entry → do not launch.

[ ] 8. SEED DIRECTORY EXISTS
        ls experiments/hotpotqa/thinking/seeds/ddce37b4/initial_programs/
        (must contain at least one .py file)

[ ] 9. STATIC_F1_600 PROBLEM DIRECTORY
        ls problems/chains/hotpotqa/static_f1_600/
        (must contain validate.py, task_description.txt, metrics.yaml)

[ ] 10. NO_PROXY ENVIRONMENT
        echo $no_proxy
        (must include all 8 IPs: 10.226.17.25, 10.225.185.235,
         10.226.72.211, 10.226.15.38, 10.226.185.131, 10.225.51.251)
        If missing: export no_proxy=localhost,127.0.0.1,10.226.17.25,10.225.185.235,\
        10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251
```

---

## Warm-Start Protocol (ddce37b4)

All 4 runs load the `ddce37b4` seed via `program_loader.problem_dir`. The framework reads
existing programs from the seed directory and populates the archive before gen 0. No separate
seeding step is needed.

```bash
SEED_DIR=/workspace-SR008.fs2/mathemage/gigaevo-core/experiments/hotpotqa/thinking/seeds/ddce37b4
```

All four launch commands include `program_loader.problem_dir="$SEED_DIR"`.

F1 runs (all four) re-score seed programs under the F1 objective at gen 0, since the seed was
evolved under EM. This is expected behaviour: gen-0 val F1 ≈ 68–72%, val EM ≈ 59–61%.

---

## Launch Commands

> **Infrastructure note**: The chain LLM is set via the `HOTPOTQA_CHAIN_URL` environment
> variable, consumed by `problems/chains/hotpotqa/shared_config.py`. It does NOT appear
> in `--cfg job` output. The mutation LLM is set via `llm_base_url=` Hydra override.

```bash
export SEED_DIR=/workspace-SR008.fs2/mathemage/gigaevo-core/experiments/hotpotqa/thinking/seeds/ddce37b4

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251"
export no_proxy="$NO_PROXY"

# ── Run P (cross-P): F1 + NLP prompts + 600-sample, num_parents=1 [REPLICATION]
HOTPOTQA_CHAIN_URL=http://10.226.17.25:8001/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    redis.db=0 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.226.72.211:8777/v1 \
    program_loader.problem_dir="$SEED_DIR" \
    > experiments/hotpotqa/crossover/run_P.log 2>&1 &
echo "Run P PID: $!"

# ── Run Q (cross-Q): F1 + NLP prompts + 600-sample, num_parents=2 [CROSSOVER PRIMARY]
HOTPOTQA_CHAIN_URL=http://10.226.17.25:8000/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    redis.db=1 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=16 \
    max_elites_per_generation=8 \
    num_parents=2 \
    llm_base_url=http://10.226.15.38:8777/v1 \
    program_loader.problem_dir="$SEED_DIR" \
    > experiments/hotpotqa/crossover/run_Q.log 2>&1 &
echo "Run Q PID: $!"

# ── Run R (cross-R): F1 + default prompts + 600-sample, num_parents=2 [CROSSOVER SECONDARY]
HOTPOTQA_CHAIN_URL=http://10.225.185.235:8001/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=2 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=16 \
    max_elites_per_generation=8 \
    num_parents=2 \
    llm_base_url=http://10.226.185.131:8777/v1 \
    program_loader.problem_dir="$SEED_DIR" \
    > experiments/hotpotqa/crossover/run_R.log 2>&1 &
echo "Run R PID: $!"

# ── Run S (cross-S): F1 + default prompts + 600-sample, num_parents=1 [CONCURRENT CONTROL]
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
    program_loader.problem_dir="$SEED_DIR" \
    > experiments/hotpotqa/crossover/run_S.log 2>&1 &
echo "Run S PID: $!"
```

Record all four PIDs immediately after launch for the monitoring script and watchdog.

---

## Gen-0 Verification (immediately after launch)

Before walking away, verify gen-0 health for all four runs.

**Expected gen-0 values** (all runs use `static_f1_600`, F1 fitness, ddce37b4 seed):

| Metric | Expected range | Source |
|--------|---------------|--------|
| Val F1 (gen 0) | 68–72% | Consistent with push Run D gen-0 under F1 objective |
| Val EM (gen 0, `valid_frontier_em` key) | 59–61% | Seed ddce37b4 test EM = 60.0% |

**Hard stops if any run shows**:
- Val fitness = 0.0 at gen 0 → halt that run; diagnose before proceeding
- `valid_frontier_em` Redis key absent after gen 0 → halt; `static_f1_600/validate.py` not
  populating it; diagnose immediately (this key is required for the val-test gap analysis)
- `<think>` blocks absent in chain outputs at gen 1 → thinking mode off; invalidate run

**Check Redis key after gen 0**:

```bash
# Verify valid_frontier_em populated for all 4 runs (all use static_f1_600 prefix)
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python -c "
import redis
for db in [0,1,2,3]:
    r = redis.Redis(db=db)
    key = 'chains/hotpotqa/static_f1_600:metrics:history:program_metrics:valid_frontier_em'
    val = r.lrange(key, -1, -1)
    print(f'DB {db}: valid_frontier_em latest = {val}')
"
```

---

## Monitoring

Create `run_status.sh` immediately after launch with the actual PIDs:

```bash
# experiments/hotpotqa/crossover/run_status.sh  (fill in PIDs after launch)
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/status.py \
    --run chains/hotpotqa/static_f1_600@0:cross-P \
    --run chains/hotpotqa/static_f1_600@1:cross-Q \
    --run chains/hotpotqa/static_f1_600@2:cross-R \
    --run chains/hotpotqa/static_f1_600@3:cross-S \
    --pid L:<run_P_pid> \
    --pid L:<run_Q_pid> \
    --pid L:<run_R_pid> \
    --pid L:<run_S_pid> \
    --watchdog <watchdog_pid>
```

All four runs share the same Redis prefix (`chains/hotpotqa/static_f1_600`) on different DBs.

**Key monitoring thresholds** (from `01_design.md` §10):

| Condition | Run(s) | Action |
|-----------|--------|--------|
| Invalidity > 50% at gen 5 | Any | Pause; diagnose stage_timeout; if median eval > 5000s, increase to 8000 before resuming |
| Invalidity > 90% at gen 10 | Any | Invalidate run |
| Val fitness = 0.0 at gen 0 | Any | Halt; diagnose before proceeding |
| `<think>` blocks absent >= 5% at gen 1 | Any | Invalidate run (thinking mode off) |
| Mutation LLM error rate > 30% at gen 5 | Q, R | Alert; inspect logs for context overflow (2-parent prompts) |
| Stagnation: no frontier improvement >= 10 gens AND gen >= 15 | Any | Early completion permitted (not invalidation) |
| Frontier improving after gen 15 | Q, R | Do NOT terminate early — this is crossover's expected signal |

---

## Phase Gate: Gen-5 Check

Before proceeding past generation 5, confirm:

```
[ ] All 4 runs have produced at least 1 valid program by gen 5
[ ] Invalidity rate < 50% for all runs at gen 5
[ ] Val F1 > 0 and val EM > 0 for all runs at gen 5
[ ] valid_frontier_em key populated in all 4 Redis DBs
[ ] For Runs Q and R: mutations_per_generation at gen 5 ≈ 16 (not 8 or 28)
    (if > 16: max_mutations_per_generation override not applied — stop and fix)
[ ] For Runs P and S: mutations_per_generation at gen 5 ≈ 8
    (if > 8 or = 0: num_parents override likely wrong — stop and fix)
[ ] Thinking mode verified from gen-1 logs (grep for <think> in exec_runner output)
```

If any crossover run (Q or R) shows > 30% mutation LLM errors at gen 5, inspect the mutation
log for prompt size. If mean prompt size exceeds 15,000 tokens, flag as a context overflow
risk and assess whether to continue.

---

## Stop Criteria Summary

| Condition | Run(s) | Action |
|-----------|--------|--------|
| Invalidity > 50% at gen 5 | Any | Pause; diagnose; increase stage_timeout to 8000 if needed |
| Invalidity > 90% at gen 10 | Any | Invalidate — exclude from all analyses |
| Val fitness = 0.0 at gen 0 | Any | Halt; diagnose |
| `valid_frontier_em` absent after gen 0 | Any | Halt; diagnose validate.py |
| `<think>` blocks absent >= 5% at gen 1 | Any | Invalidate (thinking mode off) |
| Warm-start seed != ddce37b4 | Any | Invalidate |
| max_elites confirmed = 5 (not 8) post-hoc | Any | Invalidate — combinatorics wrong |
| prompts_dir missing for P or Q post-hoc | P, Q | Invalidate — NLP prompts silently inactive |
| Mutation LLM error rate > 30% at gen 5 | Q, R | Alert; assess context overflow; do not auto-stop |
| Stagnation (>= 10 gens no improvement) AND gen >= 15 | Any | Early completion permitted |
| Frontier improving after gen 15 | Q, R | Do not terminate — let run complete to gen 25 |

---

## Archive Protocol (after completion)

Run these commands after all runs have completed (or been terminated by stop criteria):

```bash
bash tools/experiment/archive_run.sh --exp crossover --run "chains/hotpotqa/static_f1_600@0:cross-P" --upload
bash tools/experiment/archive_run.sh --exp crossover --run "chains/hotpotqa/static_f1_600@1:cross-Q" --upload
bash tools/experiment/archive_run.sh --exp crossover --run "chains/hotpotqa/static_f1_600@2:cross-R" --upload
bash tools/experiment/archive_run.sh --exp crossover --run "chains/hotpotqa/static_f1_600@3:cross-S" --upload
```

Only after all archives are confirmed may Redis DBs 0–3 be flushed:

```bash
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/flush.py --db 0 1 2 3
# verify counts, then:
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/flush.py --db 0 1 2 3 --confirm
```

---

## Test Evaluation

After all runs complete (gen 25 or early completion), evaluate the best-by-val program from
each run on the fixed 300-sample test set. Create
`experiments/hotpotqa/crossover/run_test_eval.sh`:

```bash
#!/usr/bin/env bash
# Test evaluations for crossover experiment — all 4 runs on fixed 300-sample test set.
# All runs use static_f1_600 prefix and thinking mode Qwen3-8B.
#
# Usage:
#   GIGAEVO_PYTHON=/home/jovyan/envs/evo_fast/bin/python \
#   bash experiments/hotpotqa/crossover/run_test_eval.sh

set -euo pipefail

PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core
PYTHON=${GIGAEVO_PYTHON:-/home/jovyan/envs/evo_fast/bin/python}
export PYTHONPATH="$PROJ"
EVAL_SCRIPT="$PROJ/experiments/hotpotqa/thinking/gen10_test_eval.py"
RESULTS_PATH="$PROJ/experiments/hotpotqa/crossover/test_evals/results.json"
LOG_DIR="$PROJ/experiments/hotpotqa/crossover/test_evals"
mkdir -p "$LOG_DIR"

# Chain servers — same assignment as training to minimise server variance
CHAIN_URL_P="http://10.226.17.25:8001/v1"
CHAIN_URL_Q="http://10.226.17.25:8000/v1"
CHAIN_URL_R="http://10.225.185.235:8001/v1"
CHAIN_URL_S="http://10.225.185.235:8000/v1"

export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251"
export no_proxy="$NO_PROXY"

# ── Preflight: thinking-mode verification ─────────────────────────────────────
echo "[preflight] Verifying thinking mode on all 4 chain endpoints..."
for CHAIN_URL in "$CHAIN_URL_P" "$CHAIN_URL_Q" "$CHAIN_URL_R" "$CHAIN_URL_S"; do
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

# ── Run P: F1+NLP+600, num_parents=1 [REPLICATION] ───────────────────────────
echo "================================================================"
echo "[P] chains/hotpotqa/static_f1_600  db=0  chain=$CHAIN_URL_P"
echo "Test 1 gate: test_EM >= 62.3% → H1(P) confirmed (POSITIVE)"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_P" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label P \
    --redis-db 0 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_P.log"
echo ""

# ── Run Q: F1+NLP+600, num_parents=2 [CROSSOVER PRIMARY] ─────────────────────
echo "================================================================"
echo "[Q] chains/hotpotqa/static_f1_600  db=1  chain=$CHAIN_URL_Q"
echo "Test 2 gate: delta(Q-P) >= +2.4pp AND McNemar p<0.05 → POSITIVE (THROUGHPUT CONFOUNDED)"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_Q" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label Q \
    --redis-db 1 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_Q.log"
echo ""

# ── Run R: F1+default+600, num_parents=2 [CROSSOVER SECONDARY] ───────────────
echo "================================================================"
echo "[R] chains/hotpotqa/static_f1_600  db=2  chain=$CHAIN_URL_R"
echo "Test 3 gate: delta(R-S) >= +2.4pp AND McNemar p<0.05 → POSITIVE (THROUGHPUT CONFOUNDED)"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_R" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label R \
    --redis-db 2 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_R.log"
echo ""

# ── Run S: F1+default+600, num_parents=1 [CONCURRENT CONTROL] ────────────────
echo "================================================================"
echo "[S] chains/hotpotqa/static_f1_600  db=3  chain=$CHAIN_URL_S"
echo "Test 3+5 baseline: expected ~58.67% (consistent with push Run C)"
echo "================================================================"
HOTPOTQA_CHAIN_URL="$CHAIN_URL_S" \
    "$PYTHON" "$EVAL_SCRIPT" \
    --run-label S \
    --redis-db 3 \
    --redis-prefix chains/hotpotqa/static_f1_600 \
    --max-gen 9999 \
    --n-samples 300 \
    --val-subset fixed_300 \
    --results-path "$RESULTS_PATH" \
    2>&1 | tee "$LOG_DIR/test_eval_S.log"
echo ""

echo "================================================================"
echo "All test evals complete."
echo "Results: $RESULTS_PATH"
echo "Logs:    $LOG_DIR/test_eval_{P,Q,R,S}.log"
echo ""
echo "Primary gates:"
echo "  Test 1 (P):   test_EM(P) >= 62.3% → Run D replicates"
echo "  Test 2 (Q-P): delta >= +2.4pp AND McNemar p < 0.05 → crossover effect"
echo "  Test 3 (R-S): delta >= +2.4pp AND McNemar p < 0.05 → crossover robust to prompts"
echo "  Test 5 (P-S): delta >= +2.4pp AND McNemar p < 0.05 → NLP-prompt effect at F1+600"
echo "================================================================"
```

**McNemar tests** (run after all test evals complete; requires item-level predictions from
`results.json` or per-run eval logs):

- Test 2: McNemar on matched 300-item predictions from Q and P
- Test 3: McNemar on matched 300-item predictions from R and S
- Test 5: McNemar on matched 300-item predictions from P and S

All item-level predictions must be saved during eval (verify `gen10_test_eval.py` writes
per-item results, not just aggregate EM, to `results.json`). If only aggregate EM is stored,
McNemar cannot be computed and comparisons are limited to point-estimate deltas — document
this as a limitation in Phase 5.

---

## Closeout Checklist

After all test evals and archives complete:

```bash
bash tools/experiment/check_experiment_complete.sh hotpotqa/crossover
gh pr merge --merge --delete-branch  # NOT --squash — preserves audit trail
```

---

## Amendment Protocol

Any post-registration change requires a numbered amendment in this section. Each amendment
must specify:
- **Type**: No confound / Confound introduced / Run invalidated
- **Change**: exact description of what changed
- **Commit**: commit hash implementing the change
- **Rationale**: why the change was necessary
- **Impact**: effect on validity of each run and on pre-registered tests

_(No amendments at pre-registration time.)_

---

## Phase 3 Gate

This file is committed before any experimental run launches. After commit:

```bash
bash tools/experiment/check_phase_order.sh hotpotqa/crossover
```

Must pass before launch.

---

*Ready for Reviewer-2's scrutiny.*
