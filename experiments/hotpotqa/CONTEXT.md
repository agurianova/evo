# HotpotQA — Task Context

This directory is the parent context for the entire HotpotQA research line.
Individual experiments live in subdirectories: `experiments/hotpotqa/<name>/`.

---

## Part 1 — Stable Task Knowledge

### Benchmarks (Qwen3-8B, thinking mode)

| Method | Test EM |
|--------|---------|
| GEPA | 62.3% |
| MIPROv2 | 55.3% |
| GRPO | 43.3% |
| Baseline (zero-shot) | 42.3% |
| GigaEvo best (Run D, push, exploratory) | 63.0% |
| GigaEvo seed ddce37b4 | 60.0% |

**ALL results must use thinking Qwen3-8B.** GEPA benchmark uses the default chat template
(thinking ON). Non-thinking runs are INVALID for GEPA comparison.

---

### Dataset

| Split | File | Rows | sha256 |
|-------|------|------|--------|
| Train (val draws from here) | `problems/chains/hotpotqa/dataset/HotpotQA_train.jsonl` | 1000 | `9d8b0ba2a19d124fa243c88b650b2ecd42e5c771bc4e039553389c6b9566ef94` |
| Test (held out) | `problems/chains/hotpotqa/dataset/HotpotQA_test.jsonl` | 300 | `c46bfb185e448bf1b92cb75bb5ab967f3211051793967f01500f453945046b0d` |
| BM25 corpus | `problems/chains/hotpotqa/dataset/wiki17_abstracts.jsonl.passages.pkl` | — | `44e329f00a240493dd0423afeb42767f830b954dbe5f89dfd0f6e0f7046ca9fc` |

Validation set = first N samples of train split (for fixed protocols) or hash-seeded
random draw (for rotating protocols). Test set is never seen during evolution.

---

### Chain Structure (fixed 6-step topology)

```
Step 1 (TOOL, frozen)  — BM25 retrieve: query = question
Step 2 (LLM)          — Summarize first-hop passages
Step 3 (LLM)          — Generate second-hop search query
Step 4 (TOOL, frozen)  — BM25 retrieve: query = Step 3 output
Step 5 (LLM)          — Combine first-hop summary + second-hop passages
Step 6 (LLM)          — Final answer: must output "Answer: <answer>"
```

Static mode = evolve LLM step prompts + system_prompt only. Topology is fixed.
Fitness = EM or F1 (depends on problem variant). Output format: `Answer: <answer>`.

---

### Problem Variants

| `problem.name` | Val N | Val protocol | Fitness | Notes |
|----------------|-------|--------------|---------|-------|
| `chains/hotpotqa/static` | 300 | Fixed (first 300 train) | EM | Canonical baseline |
| `chains/hotpotqa/static_r` | 300 | Hash-seeded (per-program) | EM | P1 rotation variant |
| `chains/hotpotqa/static_a` | 300 | Fixed | EM | ASI formatter (P2) |
| `chains/hotpotqa/static_ra` | 300 | Hash-seeded | EM | P1+P2 combined |
| `chains/hotpotqa/static_600` | 600 | Fixed (first 600 train) | EM | val_gap Run Q; push Run B |
| `chains/hotpotqa/static_f1` | 300 | Fixed | F1 | val_gap Run F — F1 fitness |
| `chains/hotpotqa/static_f1_600` | 600 | Fixed (first 600 train) | F1 | push Run C — F1 + 600 samples |
| `chains/hotpotqa/static_colbert_f1_600` | 600 | Fixed (first 600 train) | F1 | colbert_feedback — ColBERT retrieval + rich feedback |
| `chains/hotpotqa/static_r600` | 600 | Hash-seeded (per-program) | EM | rotation + 600 samples |
| `chains/hotpotqa/static_holdout_f1` | 300 | Holdout split (no train overlap) | F1 | generalization — held-out val set |

**Required pipeline for all hotpotqa variants**: `pipeline=hotpotqa_asi`
(validate.py returns `tuple[dict, list[dict]]`; `pipeline=standard` calls `repr()` on
the tuple — see repr-contamination bug below).

---

### Warm-Start Seed

**`ddce37b4`** — val EM 62.7% (fixed-300), test EM 60.0%. Thinking mode, Qwen3-8B.
Location: `experiments/hotpotqa/thinking/seeds/ddce37b4/`

Use leapfrog continuation when restarting (extract top programs → fresh run on new DB).
Do **not** use `redis.resume=true` — broken for MAP-Elites archive.

---

### Validation Performance

- ~244s per 300-sample evaluation in thinking mode (after step_max_tokens fix)
- Was ~1304s before fix (5.35× speedup)
- `step_max_tokens` minimum: 2048 (tight), 4096 (comfortable), 8192 (generous)
- 600-sample eval: ~8 min/gen expected; alert if > 12 min

---

### Key Hydra Overrides

```bash
problem.name=chains/hotpotqa/static   # which problem variant
pipeline=hotpotqa_asi                  # REQUIRED for all hotpotqa (never standard)
prompts=default                        # generic GigaEvo mutation prompts
prompts=hotpotqa                       # NLP-specific prompts (gigaevo/prompts/hotpotqa/)
redis.db=N                             # unoccupied DB number
```

Config review (no execution): `python run.py [overrides] --cfg job`

---

### Known Bugs and Patterns

#### repr-contamination (fixed 0663598)
`pipeline=standard` calls `repr()` on the `(metrics, failures)` tuple returned by
`validate.py`, injecting raw Python repr strings into mutation prompts for all 50
generations. **Always use `pipeline=hotpotqa_asi`** for any hotpotqa problem variant.

#### prompts_dir missing from evolution_context (fixed 920c975; extended to all pipelines)
Pipeline YAMLs were missing `prompts_dir: ${prompts.dir}` in the `evolution_context`
block. Without it, InsightsStage and LineageStage ignore `prompts=hotpotqa` silently.
Originally fixed in `hotpotqa_asi.yaml`/`hotpotqa_reflective.yaml`; later extended to
the standard context-aware builders, optimization pipelines, and `custom.yaml`.
**Always verify** that `prompts_dir: ${prompts.dir}` appears in BOTH `evolution_context`
AND `mutation_operator` blocks in any custom pipeline YAML.

#### Random failure sampling (fixed cf0cfc1)
Both formatter classes (`HotpotQAASIFormatter`, `HotpotQAFailureFormatter`) must use
`random.sample(failures, min(10, len(failures)))` with `cache_handler = NO_CACHE`.
Without this, the mutation LLM sees the same 10 failure cases every generation across
50 generations — equivalent to overfitting a fixed mini-batch.

#### num_parents / throughput
- `AllCombinationsParentSelector` + `num_parents=1` + `max_elites=8` → max **8 mutations/gen**
- `num_parents=2` + `max_elites=8` → C(8,2)=28 → capped at `max_mutations` → **16 mutations/gen**
- Set `max_mutations_per_generation=8` when `num_parents=1` to match actual throughput

#### Chain LLM HTTP timeout too short for 600-sample runs (fixed push experiment)
`problems/chains/client.py` `get_async_client()` sets `httpx.Timeout(timeout=120.0)`.
With 600 samples, up to 600 concurrent requests are fired at each LLM step. Later-queued
requests can wait > 120s for vLLM to begin generating, triggering `openai.APITimeoutError`
and high invalidity (observed: 67% in Run C at gen 2). Fix: `timeout=600.0` (10 min).
**Always use 600s timeout for 600-sample runs.** Confirmed fixed at commit `c0186a8`.

#### Watchdog gen-count via log grep (fixed push experiment; canonical source updated e7648ab)
`grep -c "Phase 1: Idle confirmed"` is brittle — depends on log message format and breaks
if PROJ path is wrong. Use Redis instead: `hget {prefix}:run_state engine:total_generations`.
This is the canonical gen-count source (commit `e7648ab`), written by `EvolutionEngine` after
every generation and surviving restarts. Consistent with `tools/status.py` and `tools/README.md`.
`valid_iter_fitness_mean` last `"s"` is deprecated for gen count (lags under high throughput).

#### Watchdog PROJ depth wrong (fixed push experiment)
`PROJ = Path(__file__).parent.parent.parent` resolves to `experiments/` not the project
root when the watchdog lives at `experiments/hotpotqa/push/`. Use `.parent.parent.parent.parent`
(4 levels) for files 4 levels deep from project root.

#### Watchdog _last_gen crash (~1h after start)
`_last_gen` keyed with wrong labels (copy-pasted from prior experiment) → `KeyError`.
Always derive `_last_gen` from the `RUNS` list, never hardcode:
```python
_last_gen: dict[str, int] = {run["label"]: -1 for run in RUNS}
```

---

### Environment Variable

Chain LLM URL is passed via env var, not Hydra config:
```bash
export HOTPOTQA_CHAIN_URL="http://10.232.30.185:4000/v1"
```
Must be set before launching `run.py`. The LiteLLM proxy load-balances across all chain servers (see `infrastructure.yaml`).

---

## Part 2 — Infrastructure (current state — update before each launch)

_Last updated: 2026-04-07_

**Canonical server inventory**: `experiments/infrastructure.yaml`
All server IPs, ports, models, and status are maintained there. Verify before each launch.

### LiteLLM Proxy (primary access method)

All experiments use the LiteLLM proxy at `10.232.30.185:4000` for load-balanced access.
Start with `bash tools/litellm.sh --background`. Auth: `Bearer sk-gigaevo`.

### Chain Execution LLMs (Qwen3-8B, thinking mode ON)

See `experiments/infrastructure.yaml` → `chain_servers` for current endpoints.
8 slots on `10.232.45.196` (ports 8000-8007). Context window: 32768.
Thinking confirmed by `<think>` blocks appearing in `choices[0].message.content`.

### Mutation / Insights LLMs (Qwen3-235B-A22B-Thinking — assign one per run)

See `experiments/infrastructure.yaml` → `mutation_servers` for current endpoints.
6 active endpoints. Port 8777.

### Squid Proxy / NO_PROXY

The system Squid proxy intercepts Python HTTP to internal IPs but not shell `curl`.
With LiteLLM proxy, most clients only need `NO_PROXY=10.232.30.185,localhost`.
See `experiments/infrastructure.yaml` → `no_proxy_hosts` for the full list.

`shared_config.py` handles NO_PROXY automatically. For standalone scripts, import
`shared_config` before any HTTP calls, or set NO_PROXY manually.
