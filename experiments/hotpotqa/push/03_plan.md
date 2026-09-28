# Pre-Registration: push — GEPA Attack (F1 × Prompts × Val-N, 4 runs)

**Date**: 2026-03-07
**Pre-registration commit**: `9173c10`
**Design doc**: `experiments/hotpotqa/push/01_design.md`
**Review doc**: `experiments/hotpotqa/push/02_review.md`
  - Round 1: NEEDS REVISION — Prof. Andrei Volkov, 2026-03-07
  - Round 2: APPROVED — Prof. Andrei Volkov, 2026-03-07

> **Protocol rule**: This file must be committed BEFORE any run launches.
> Code changes made before this commit are recorded as Amendments 1–2 below.

---

## Protocol Deviation Note

Two deviations from the standard 5-phase protocol occurred in this experiment:

**Deviation 1 — Code before pre-registration.**
The protocol requires `03_plan.md` to be committed before any code changes. In this
experiment, code fixes were committed at `55772ba` (stage_timeout wiring + system.txt
metric-agnostic framing) before this file was written. The fixes were required by
Volkov's Phase 2 review (Critical and Major concerns) and could not be deferred without
blocking the review approval. All changes are documented as Amendments 1–2 below. No code
changes affected the experiment after this file was committed.

**Deviation 2 — Branch created after experiment commits.**
The experiment branch (`exp/hotpotqa-push`) was created after all design, review, and
pre-registration commits had already landed on `main`. The branch was created at the
same commit as `main` and diverges only from `run_status.sh` onward. PR #73 therefore
does not show the full experiment history in its diff — the audit trail exists on `main`
via the commit log (`55772ba` through `f47847f`).

**Impact assessment**: Both deviations are procedural, not scientific. The experimental
design was fully locked (Phase 2 APPROVED) before any run launched. The code changes were
externally required (Phase 2 review), not post-hoc optimizations. No run results are
affected.

---

## Amendment 1 — Pre-registration (committed before any run)

**Type**: No confound — change applied uniformly.

**Change**: `gigaevo/prompts/hotpotqa/mutation/system.txt` ROLE line updated to
metric-agnostic framing. Previous text: "evaluated based on their exact match accuracy
on multi-hop question answering." New text: "evaluated on multi-hop question answering."

**Commit**: `55772ba` (fix: wire stage_timeout through DefaultPipelineBuilder + validation speedup)

**Rationale**: The old framing conflicted with the F1 task_description for Runs A and C.
Metric-agnostic framing is consistent with all run types (EM and F1) and removes an
internal contradiction identified at design time (Volkov Concern 2). Applied uniformly
to all runs — EM runs (B, D) are not affected since the task_description still specifies EM.

---

## Amendment 2 — Pre-registration (committed before any run)

**Type**: No confound — change applied uniformly.

**Change**: `stage_timeout` Hydra override is now mechanically wired to
`CallValidatorFunction` for `pipeline=hotpotqa_asi`. Previously hardcoded to
`DEFAULT_SIMPLE_STAGE_TIMEOUT=2400` regardless of Hydra override.

**Commit**: `55772ba`

**Files changed**:
- `gigaevo/entrypoint/default_pipelines.py`: `DefaultPipelineBuilder` now accepts
  `stage_timeout` parameter, stores as `self._stage_timeout`, passes to all stages.
- `problems/chains/hotpotqa/static_a/pipeline.py`: `ASIPipelineBuilder` forwards
  `stage_timeout` to `DefaultPipelineBuilder`.
- `config/pipeline/hotpotqa_asi.yaml`: Added `stage_timeout: ${stage_timeout}` and
  `dag_timeout: ${dag_timeout}` to `pipeline_builder` block.

**Rationale**: Without this fix, `stage_timeout=6000` Hydra override was silently inert.
Runs B/C/D would have replicated Run Q's 96.3% invalidity rate (Amendment 2 from val_gap).

---

## Amendment 4 — Hard reset + timeout fix (2026-03-07, after gen 2–5)

**Type**: No confound — change applied uniformly to all runs; hard reset from shared seed.

**Change**: `problems/chains/client.py` — `httpx.Timeout(timeout=120.0)` → `httpx.Timeout(timeout=600.0)`.
All 4 runs killed (A=3374246, B=3374247, C=3374248, D=3417569), Redis DBs 8–11 flushed,
restarted from `ddce37b4` seed with new PIDs (A=3422378, B=3422379, C=3422380, D=3422381).
Watchdog restarted (PID=3423165).

**Root cause**: At 600 samples, up to 600 concurrent HTTP requests are fired at each LLM
step. Under load, later-queued requests could wait > 120s for the vLLM server to begin
generating their response, triggering `openai.APITimeoutError`. This caused Run C to show
67% invalidity at gen 2 despite `stage_timeout=6000` being sufficient for the total eval.

**Impact**: Gen 1–5 data from the pre-reset runs is discarded (no archiving — runs were too
early for meaningful programs). Hard reset from `ddce37b4` seed is equivalent to a clean
launch. The fix is applied uniformly across all runs — no differential treatment.

---

## Amendment 3 — Mid-run (2026-03-07, after gen 3 of Run D)

**Type**: Confound introduced — Run D condition changed; Run D gen 1–3 data discarded.

**Change**: Run D replaced from **EM+NLP+600** (`chains/hotpotqa/static_600`, `prompts=hotpotqa`,
`fitness_is_f1=False`) to **F1+NLP+600** (`chains/hotpotqa/static_f1_600`, `prompts=hotpotqa`,
`fitness_is_f1=True`). New PID: 3417569 (old PID 3374249 killed). Redis DB 11 flushed.
Run D gen 1–3 results under the original EM condition (best val EM 63.7%) are discarded
and excluded from all analyses.

**Rationale**: The original EM+NLP+600 cell was replaced to create a cleaner 2×2 comparison
at 600 samples:

| | `prompts=default` | `prompts=hotpotqa` |
|---|---|---|
| F1 fitness | Run C | Run D (new) |
| EM fitness | Run B | — |

The new design directly isolates the NLP-prompts effect under F1 fitness at 600 samples
(C vs D), and the 300-vs-600 sample size effect for F1+NLP (A vs D). The original 2³
factorial is no longer complete; interpretation of Run B (EM+default+600) is unchanged
but EM×NLP interaction cannot be estimated.

**Impact on primary test**: Run C remains the primary test (H₁: test EM ≥ 62.3%).
Amendment does not affect Run C, Run B, or Run A.

**Watchdog/monitoring**: `run_watchdog.py` and `run_status.sh` updated with new prefix
(`chains/hotpotqa/static_f1_600`), `fitness_is_f1=True`, and new PID 3417569.

---

## Hypothesis

**Research question**: Can GigaEvo exceed GEPA (62.3% test EM on HotpotQA with Qwen3-8B
thinking mode) by combining validated gap-reduction mechanisms — F1-protocol fitness,
domain-specific NLP mutation prompts, and larger validation sample size?

**Primary test — Run C (F1 × default × 600)**:

H₀(C): Fixed-600 F1 fitness produces test EM no higher than either Run B (EM/600) or
Run F (F1/300) individually.

H₁(C): Fixed-600 F1 achieves test EM ≥ 62.3% (GEPA). Threshold for SUGGESTIVE:
test EM ∈ [61.7%, 62.3%) with val EM gap < 1.5pp. F1 fitness reduces val EM overfit
(Gate E, SUGGESTIVE) and 600-sample validation reduces selection noise (Gate C, re-opened);
both mechanisms are independent and expected to combine.

**Secondary tests (A, B, D)** — see 01_design.md §2 for full hypotheses. Run C is the
primary test for the experiment-level verdict; secondary runs provide mechanism attribution.

**Documentation note (Volkov Concern 8)**: The SUGGESTIVE threshold for Run C in §8 of
01_design.md includes the condition val EM gap < 1.5pp; this condition does not appear
verbatim in H₁(C) in §2. The intent is that SUGGESTIVE requires BOTH a near-GEPA test EM
AND a maintained gap compression (consistent with the Gate E finding in val_gap). This note
documents the alignment between §2 and §8 for Phase 5 interpretation.

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

## Test Evaluation Script Checksum

| File | sha256 |
|------|--------|
| `experiments/hotpotqa/push/run_test_eval.sh` | `e8a38b14462ce1eba3087536bdb8ff14c379a4d6519afc1087072fb459fe5b5b` |

Verify before test eval:
```bash
sha256sum experiments/hotpotqa/push/run_test_eval.sh
```

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | `stage_timeout` | `dag_timeout` | `max_gen` | Val N | Fitness | Seed |
|-----|-------|-----------|-----------|-----------|----------------|----------------|--------------|----------|-------|---------|------|
| A | push-A | 8 | `hotpotqa_asi` | `hotpotqa` | `chains/hotpotqa/static_f1` | 2400 | 7200 | 50 | 300 | F1 | ddce37b4 |
| B | push-B | 9 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_600` | 6000 | 9000 | 25 | 600 | EM | ddce37b4 |
| C | push-C | 10 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | 6000 | 9000 | 25 | 600 | F1 | ddce37b4 |
| D | push-D | 11 | `hotpotqa_asi` | `hotpotqa` | `chains/hotpotqa/static_600` | 6000 | 9000 | 25 | 600 | EM | ddce37b4 |

**Chain LLM assignment** (one chain server per run, no sharing):
- Run A: `http://10.226.17.25:8001/v1`
- Run B: `http://10.226.17.25:8000/v1`
- Run C: `http://10.225.185.235:8001/v1`
- Run D: `http://10.225.185.235:8000/v1`

**Mutation LLM assignment** (one per run):
- Run A: `http://10.226.72.211:8777/v1`
- Run B: `http://10.226.15.38:8777/v1`
- Run C: `http://10.226.185.131:8777/v1`
- Run D: `http://10.225.51.251:8777/v1`

---

## Launch Commands

> **Pre-launch checks** (mandatory for all runs before launch):
> 1. `sha256sum` dataset files and `run_test_eval.sh` match table above
> 2. `PYTHONPATH=. python tools/flush.py --db 8 9 10 11` → 0 keys each
> 3. Verify `max_model_len=32768` on all 4 chain LLM servers (curl /v1/models)
> 4. Verify stage_timeout wiring: inspect exec_runner log at gen 0; confirm
>    `CallValidatorFunction` does not time out at 2400s for 600-sample runs (B/C/D)

### Config review (no execution — mandatory before each run)

> **Note**: `llm_base_url` is the correct top-level Hydra override for the mutation LLM.
> The chain LLM is set via `HOTPOTQA_CHAIN_URL` environment variable — it does not appear
> in `--cfg job` output because it is consumed by the problem's `validate.py` at runtime.

```bash
# Run A
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    redis.db=8 \
    stage_timeout=2400 \
    dag_timeout=7200 \
    max_generations=50 \
    llm_base_url=http://10.226.72.211:8777/v1 \
    --cfg job 2>&1 | grep -E "stage_timeout|dag_timeout|prompts_dir|problem|redis"

# Verify two distinct prompts_dir entries appear (evolution_context AND mutation_operator)

# Run B
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=9 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    llm_base_url=http://10.226.15.38:8777/v1 \
    --cfg job 2>&1 | grep -E "stage_timeout|dag_timeout|problem|redis"

# Run C
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=10 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    llm_base_url=http://10.226.185.131:8777/v1 \
    --cfg job 2>&1 | grep -E "stage_timeout|dag_timeout|problem|redis"

# Run D
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_600 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    redis.db=11 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    llm_base_url=http://10.225.51.251:8777/v1 \
    --cfg job 2>&1 | grep -E "stage_timeout|dag_timeout|prompts_dir|problem|redis"

# Verify two distinct prompts_dir entries for Run D
```

### Actual launch commands

> **Key points**:
> - Chain LLM is set via `HOTPOTQA_CHAIN_URL` env var prefix (not a Hydra override)
> - Mutation LLM uses `llm_base_url=...` top-level Hydra override (NOT `llm.base_url`)
> - Warm-start seed is loaded via `program_loader.problem_dir=<seed_dir>` Hydra override
> - See `experiments/hotpotqa/push/launch.sh` for the canonical launch script with
>   preflight checks. Commands below show the logical structure only.

```bash
SEED_DIR=/workspace-SR008.fs2/mathemage/gigaevo-core/experiments/hotpotqa/thinking/seeds/ddce37b4

# Run A (push-A): F1 + NLP prompts + 300-sample
HOTPOTQA_CHAIN_URL=http://10.226.17.25:8001/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    redis.db=8 \
    stage_timeout=2400 \
    dag_timeout=7200 \
    max_generations=50 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.226.72.211:8777/v1 \
    program_loader.problem_dir="$SEED_DIR" \
    > experiments/hotpotqa/push/run_A.log 2>&1 &
echo "Run A PID: $!"

# Run B (push-B): EM + default + 600-sample
HOTPOTQA_CHAIN_URL=http://10.226.17.25:8000/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=9 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.226.15.38:8777/v1 \
    program_loader.problem_dir="$SEED_DIR" \
    > experiments/hotpotqa/push/run_B.log 2>&1 &
echo "Run B PID: $!"

# Run C (push-C): F1 + default + 600-sample [PRIMARY]
HOTPOTQA_CHAIN_URL=http://10.225.185.235:8001/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=default \
    redis.db=10 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.226.185.131:8777/v1 \
    program_loader.problem_dir="$SEED_DIR" \
    > experiments/hotpotqa/push/run_C.log 2>&1 &
echo "Run C PID: $!"

# Run D (push-D): EM + NLP prompts + 600-sample
HOTPOTQA_CHAIN_URL=http://10.225.185.235:8000/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_600 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    redis.db=11 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    max_generations=25 \
    max_mutations_per_generation=8 \
    max_elites_per_generation=8 \
    num_parents=1 \
    llm_base_url=http://10.225.51.251:8777/v1 \
    program_loader.problem_dir="$SEED_DIR" \
    > experiments/hotpotqa/push/run_D.log 2>&1 &
echo "Run D PID: $!"
```

> **Post-launch (gen 0 verification)**:
> - Confirm `<think>` blocks present in chain outputs (thinking mode active)
> - For Run A/D: verify val F1 ≈ 70.27% (Run A); val EM ≈ 60% at gen 0
> - For Run C: verify val F1 ≈ 68–72%, val EM ≈ 59–61% at gen 0 (halt if outside range)
> - For Runs B/C/D: inspect exec_runner log for `CallValidatorFunction` timing —
>   confirm completion within 2400–6000s, not timing out at 2400s

---

## Warm-Start Protocol (from ddce37b4)

All 4 runs use seed `ddce37b4` as warm-start. The seed programs are loaded via the
`program_loader.problem_dir` Hydra override, which points `run.py` at a directory
containing pre-existing seed programs. The framework reads them at startup and populates
the archive before gen 0 begins — no separate seeding step is needed.

```bash
# Seed directory (contains initial_programs/*.py from ddce37b4 run):
SEED_DIR=experiments/hotpotqa/thinking/seeds/ddce37b4

# This override is included in every launch command above:
program_loader.problem_dir="$SEED_DIR"
```

F1 runs (A, C) re-score seed programs under the F1 objective at gen 0 since the seed
was evolved under EM. This is expected and does not require separate handling.

---

## Monitoring

Create `run_status.sh` after launch with pre-filled PIDs and labels:

```bash
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python tools/status.py \
    --run chains/hotpotqa/static_f1@8:push-A \
    --run chains/hotpotqa/static_600@9:push-B \
    --run chains/hotpotqa/static_f1_600@10:push-C \
    --run chains/hotpotqa/static_600@11:push-D \
    --pid L:<run_A_pid> \
    --pid L:<run_B_pid> \
    --pid L:<run_C_pid> \
    --pid L:<run_D_pid> \
    --watchdog <watchdog_pid>
```

**Key monitoring thresholds**:
- Invalidity rate > 50% at gen 5 for B/C/D → pause and diagnose stage_timeout
- Invalidity rate > 30% at gen 5 for A → alert only
- val F1 = 0.0 or val EM = 0.0 at gen 0 for any run → halt
- Stagnation (frontier no improvement for ≥ 10 gens) → early completion for B/C/D

---

## Stop Criteria Summary

| Condition | Run(s) | Action |
|-----------|--------|--------|
| Invalidity > 50% at gen 5 | B, C, D | Pause; diagnose stage_timeout; increase to 8000 if median eval > 5000s |
| Invalidity > 90% at gen 10 | Any | Invalidate run |
| val fitness = 0.0 at gen 0 | Any | Halt; diagnose before proceeding |
| `<think>` blocks absent ≥ 5% at gen 1 | Any | Invalidate run (thinking mode off) |
| Stagnation: no frontier improvement ≥ 10 gens | B, C, D | Early completion (not invalidation) |
| `prompts_dir` missing from evolution_context | A, D | Do not launch; fix and re-verify |
| static_f1_600 gen-0 outside 68–72% F1 or 59–61% EM | C | Halt; diagnose |

---

## Archive Protocol (after completion)

```bash
bash tools/experiment/archive_run.sh --exp push --run "chains/hotpotqa/static_f1@8:push-A" --upload
bash tools/experiment/archive_run.sh --exp push --run "chains/hotpotqa/static_600@9:push-B" --upload
bash tools/experiment/archive_run.sh --exp push --run "chains/hotpotqa/static_f1_600@10:push-C" --upload
bash tools/experiment/archive_run.sh --exp push --run "chains/hotpotqa/static_600@11:push-D" --upload
```

Only after archiving all runs may Redis DBs 8–11 be flushed.

---

## Phase 3 Gate

This file is committed before any experimental run launches. After commit:

```bash
bash tools/experiment/check_phase_order.sh hotpotqa/push
```

Must pass before launch.
