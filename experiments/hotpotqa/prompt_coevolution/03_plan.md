# Pre-Registration: Prompt Co-Evolution

**Date**: 2026-03-16
**Protocol version**: 1.0
**Pre-registration commit**: `4ccb787`
**GitHub PR**: #84
**Tracking issue**: #83
**Design doc**: `experiments/hotpotqa/prompt_coevolution/01_design.md`
**Review doc**: `experiments/hotpotqa/prompt_coevolution/02_review.md` (verdict: APPROVED, Round 2)
**Evaluation script**: `experiments/hotpotqa/prompt_coevolution/run_test_eval.sh` (sha256: `6cbcac26a2743249046f2d91fa229c06a61aa4911ccd11ca301d29309615e2c2`) *(see Amendment #1)*

---

## Hypothesis

**H₀**: Co-evolved mutation prompt runs produce test EM indistinguishable from the fixed-prompt
cold-start baseline (mean 59.58%, SD=1.00pp, n=4). Formally: mu_coevo ≤ 59.58%.

**H₁**: Co-evolved mutation prompt runs produce test EM ≥ 61.58% (mean), representing a +2.00pp
improvement over the cold-start reference (2σ above baseline SD=1.00pp).

**Primary metric**: Test EM of the best-by-val program at gen 25 (main run), evaluated on
`HotpotQA_test.jsonl` (300 samples).

**Significance threshold**: α = 0.05 (one-sided). Treatment mean ≥ 61.58% → POSITIVE.

**Verdict table** (applied to treatment mean of n=3 runs):

| Co-evo mean test EM | Verdict |
|---------------------|---------|
| ≥ 61.58% (majority of runs above threshold) | POSITIVE (suggestive; replication at n≥4 required) |
| [59.58%, 61.58%) | NULL |
| < 59.58% | NEGATIVE |
| Mixed results across runs | INCONCLUSIVE (follow-up at n≥4 required) |

With n=3, no formal hypothesis test has adequate power. Results are interpreted descriptively.
A POSITIVE verdict at n=3 warrants a follow-up confirmatory experiment at n≥4.

---

## Run Design Table

### Main runs (HotpotQA chain evolution)

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | Chain LLM | Mutation LLM | `prompt_fetcher` | `prompt_fetcher.prompt_redis_db` |
|-----|-------|------------|-----------|-----------|----------------|-----------|-------------|-----------------|----------------------------------|
| X1 | coevo-1 | 4 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | `10.226.17.25:8001` | `10.226.72.211:8777` | `coevolved` | 6 |
| X2 | coevo-2 | 5 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | `10.226.17.25:8000` | `10.226.15.38:8777` | `coevolved` | 6 |
| X3 | coevo-3 | 8 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | `10.225.185.235:8001` | `10.226.185.47:8777` | `coevolved` | 6 |

### Prompt run (mutation prompt evolution — 1-to-many coupling)

| Run | Label | `redis.db` | `pipeline` | `problem.name` | Mutation LLM | `main_run_sources` |
|-----|-------|------------|-----------|----------------|-------------|-------------------|
| P1 | prompt-evo | 6 | `prompt_evolution_multi` | `prompt_evolution` | `10.225.51.251:8777` | `[{db:4,prefix:chains/hotpotqa/static_f1_600},{db:5,prefix:chains/hotpotqa/static_f1_600},{db:8,prefix:chains/hotpotqa/static_f1_600}]` |

### Historical control (no within-experiment controls)

Reference: cold_start experiment (PR #75), mean=59.58%, SD=1.00pp, n=4.
Individual runs: T1=59.33%, T2=60.67%, T3=58.33%, T4=60.00%.
Config: identical (`static_f1_600`, `hotpotqa_asi`, cold start, `num_parents=1`, Qwen3-8B thinking, max_gen=25).

---

## Controlled Variables

| Field | Value |
|-------|-------|
| `problem.name` (main runs) | `chains/hotpotqa/static_f1_600` |
| `pipeline` (main runs) | `hotpotqa_asi` |
| `pipeline` (prompt runs) | `prompt_evolution` |
| `prompts` | `default` |
| `num_parents` | 1 |
| `max_elites_per_generation` (main) | 8 |
| `max_mutations_per_generation` | 8 |
| `max_generations` | 25 (matches cold-start reference) |
| `stage_timeout` | 6000 |
| `dag_timeout` | 9000 |
| Chain LLM | Qwen3-8B thinking ON (`10.226.17.25:8001/8000`) |
| Mutation LLM | Qwen3-235B-A22B-Thinking (dedicated per process) |
| Initialization | Cold start (no warm-start seed) |
| Val set | First 600 samples of `HotpotQA_train.jsonl` (fixed) |
| Failure sampling | Random (cf0cfc1 fix) |
| HTTP timeout | 600s (c0186a8 fix) |
| Prompt run `max_elites_per_generation` | 3 *(was 5, reduced in Amendment #5)* |
| Prompt run `max_mutations_per_generation` | 3 *(was 8, reduced in Amendment #5)* |
| Prompt run `max_generations` | 25 |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature and nucleus sampling in chain and mutation LLMs
- Non-deterministic GPU floating point across hardware

Cross-experiment comparisons use pre-specified effect-size thresholds rather than exact trajectory matching.

---

## Dataset Checksums

| File | sha256 |
|------|--------|
| `HotpotQA_train.jsonl` | `9d8b0ba2a19d124fa243c88b650b2ecd42e5c771bc4e039553389c6b9566ef94` |
| `HotpotQA_test.jsonl` | `c46bfb185e448bf1b92cb75bb5ab967f3211051793967f01500f453945046b0d` |

Reference (CONTEXT.md): train `9d8b0ba2...`, test `c46bfb18...` ✓

---

## Success Criteria

**POSITIVE**: Treatment mean (X1+X2+X3) test EM ≥ 61.58%. Majority of runs above threshold.
**NULL**: Treatment mean in [59.58%, 61.58%).
**NEGATIVE**: Treatment mean < 59.58%.
**INCONCLUSIVE**: Mixed results across runs.
**Infrastructure failure / run invalidation**: prompt run archive empty after gen 5 of main run (`cache_hits == 0` in fetcher stats at end of run).

---

## Mandatory Pre-Launch Smoke Test (3 gens, pair X1+P1)

Before launching all 4 processes, run X1+P1 for 3 generations and verify:

1. Key `chains/hotpotqa/static_f1_600:prompt_stats:{prompt_id}` exists in DB 4 (main run Redis)
2. Prompt run archive (DB 6) contains at least one program with `fitness > 0.0`
3. Main run fetcher logs show `has_champion = True` by gen 3
4. Key pattern match verified: prompt_id written by main run's fetcher is readable by P1's `RedisPromptStatsProvider`

If any check fails: stop, diagnose, fix, document as amendment.

---

## Monitoring Plan

`max_generations`: 25

- **Gen 3** (12%): Smoke check — all 4 PIDs alive, Redis keys growing, prompt archive non-empty, stats keys exist
- **Gen 5** (20%): First checkpoint — best-by-val for X1/X2/X3, record val F1, verify `cache_hits > 0`
- **Gen 13** (52%): Midpoint — `tools/top_programs.py --save-dir archives/`, val F1 + test EM
- **Gen 25** (100%): Final — full test eval, archive all runs, record all metrics

Early termination: if all X1/X2/X3 show val F1 < 0.50 at gen 10, terminate (infrastructure failure).

---

## Actual Launch Record

*(Filled in at launch time — not pre-registered)*

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| X1  | 3121921 | 2026-03-16 18:30 UTC | ~~full launch~~ killed at gen 4, feedback loop broken (Amendment #4) |
| X2  | 3121923 | 2026-03-16 18:30 UTC | ~~full launch~~ killed at gen 3, feedback loop broken (Amendment #4) |
| P1  | 3121922 | 2026-03-16 18:30 UTC | ~~full launch~~ died at gen 3 after ~8 min (Amendment #4) |
| P2  | 3121924 | 2026-03-16 18:30 UTC | ~~full launch~~ died at gen 3 after ~8 min (Amendment #4) |

~~Watchdog PID: 3122250~~
~~Launch commit: `b154502`~~

**Relaunch after Amendment #4** *(killed — feedback loop broken, see Amendment #5)*

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| X1  | 3226263 | 2026-03-16 20:22 UTC | ~~full launch~~ killed at gen 7, prompt fitness stuck at 0.01 (Amendment #5) |
| X2  | 3226265 | 2026-03-16 20:22 UTC | ~~full launch~~ killed at gen 9, prompt fitness stuck at 0.01 (Amendment #5) |
| P1  | 3226264 | 2026-03-16 20:22 UTC | ~~full launch~~ killed at gen 15, raced ahead due to sync timeout (Amendment #5) |
| P2  | 3226266 | 2026-03-16 20:22 UTC | ~~full launch~~ killed at gen 15, raced ahead due to sync timeout (Amendment #5) |

**Relaunch after Amendment #5** *(killed — stale archive, see Amendment #6)*

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| X1  | 3502527 | 2026-03-17 01:12 UTC | full launch, max_gen=25 |
| X2  | 3502529 | 2026-03-17 01:12 UTC | full launch, max_gen=25 |
| P1  | 3502528 | 2026-03-17 01:12 UTC | full launch, max_gen=25, max_mut=3, max_elites=3 |
| P2  | 3502530 | 2026-03-17 01:12 UTC | full launch, max_gen=25, max_mut=3, max_elites=3 |

Watchdog PID: 3504635
Launch commit: `b154502`

**Relaunch after Amendment #6** *(with corrected seed prompts)*

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| X1  | 3544971 | 2026-03-17 02:30 UTC | full launch, max_gen=25, seed prompts inlined |
| X2  | 3544973 | 2026-03-17 02:30 UTC | full launch, max_gen=25, seed prompts inlined |
| P1  | 3544972 | 2026-03-17 02:30 UTC | full launch, max_gen=25, max_mut=3, max_elites=3, seed prompts inlined |
| P2  | 3544974 | 2026-03-17 02:30 UTC | full launch, max_gen=25, max_mut=3, max_elites=3, seed prompts inlined |

Watchdog PID: 3545444
Launch commit: `<pending>`

**Relaunch after Amendment #10 (attempt 1)** *(FAILED — missing HOTPOTQA_CHAIN_URL env var)*

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| X1  | 3931621 | 2026-03-17 18:32 UTC | ~~FAILED~~ missing HOTPOTQA_CHAIN_URL, all 25 gens in ~10 min with 0 archive entries |
| X2  | 3931781 | 2026-03-17 18:32 UTC | ~~FAILED~~ same issue |
| X3  | 3931923 | 2026-03-17 18:32 UTC | ~~FAILED~~ same issue |
| P1  | 3932104 | 2026-03-17 18:33 UTC | killed — dependent on failed main runs |

**Relaunch after Amendment #10 (attempt 2)** *(with correct env vars)*

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| X1  | 3938921 | 2026-03-17 18:47 UTC | full launch, max_gen=25, HOTPOTQA_CHAIN_URL + NO_PROXY correct |
| X2  | 3938922 | 2026-03-17 18:47 UTC | full launch, max_gen=25, HOTPOTQA_CHAIN_URL + NO_PROXY correct |
| X3  | 3938923 | 2026-03-17 18:47 UTC | full launch, max_gen=25, HOTPOTQA_CHAIN_URL + NO_PROXY correct |
| P1  | 3938924 | 2026-03-17 18:47 UTC | full launch, max_gen=25, max_mut=3, max_elites=3 |

Watchdog PID: 3941582
Launch commit: `c16ccff` (Amendment #10)

**Relaunch after Amendment #11** *(stale insights/lineage cache fix + prompt logging)*

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| X1  | 207068 | 2026-03-17 23:07 UTC | Amendment #11, GIGAEVO_PROMPT_LOG_DIR enabled |
| X2  | 207069 | 2026-03-17 23:07 UTC | Amendment #11, GIGAEVO_PROMPT_LOG_DIR enabled |
| X3  | 207070 | 2026-03-17 23:07 UTC | Amendment #11, GIGAEVO_PROMPT_LOG_DIR enabled |
| P1  | 207071 | 2026-03-17 23:07 UTC | Amendment #11, PromptInsightsStage/PromptLineageStage with cache invalidation |

Watchdog PID: 208970
Launch commit: `920a5c3` (Amendment #11)

**Post-mortem**: All runs failed. Mutation LLM servers were redeployed with model ID `Qwen3-235B-A22B-Thinking-2507` but config had `model_name: deepseek/deepseek-v3.2`. Every LLM call (mutation, insights, lineage) returned 404. X1/X2 completed 25 gens with 0 successful mutations. X3 stuck at gen 0 (chain endpoint temporarily unreachable). P1 stuck at gen 1.

**Relaunch after Amendment #12** *(model_name fix)*

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| X1  | 252287 | 2026-03-17 23:32 UTC | Amendment #12, model_name=Qwen3-235B-A22B-Thinking-2507 |
| X2  | 252288 | 2026-03-17 23:32 UTC | Amendment #12, model_name=Qwen3-235B-A22B-Thinking-2507 |
| X3  | 252289 | 2026-03-17 23:32 UTC | Amendment #12, model_name=Qwen3-235B-A22B-Thinking-2507 |
| P1  | 252290→313578 | 2026-03-17 23:32 / 00:20 UTC | Amendment #12→#13, PromptFitnessStage→InsightsStage edge fix |

Watchdog PID: 253256
Launch commit: TBD (Amendment #12)

---

## Checkpoint Log

| Gen | Date (UTC) | X1 val F1 | X2 val F1 | X3 val F1 | X1 test EM | X2 test EM | X3 test EM | P1 archive | Notes |
|-----|-----------|-----------|-----------|-----------|------------|------------|------------|------------|-------|

---

## Amendments

**Amendment #10** — task description injection + hallucination fix (no confound)

During Amendment #7-#9 runs, the evolved mutation prompts hallucinated about BM25 parameters being tunable (e.g., "tune k1, b parameters") when BM25 is actually a fixed bag-of-words retrieval tool with no adjustable parameters. Root cause: the meta-evolution LLM (P1's mutation operator) had no knowledge of the downstream HotpotQA chain structure, so it made guesses about what's evolvable vs frozen.

**Fixes**:

1. **Task description injection** (`problems/prompt_evolution/task_description.txt`): Completely rewrote the meta-prompt task description from abstract framework guidance to concrete HotpotQA domain knowledge. Now includes:
   - Full 6-step chain topology (step 1 & 4 BM25 frozen, steps 2/3/5/6 LLM-evolvable)
   - Explicit domain constraints: BM25 is a fixed bag-of-words tool, step 3 output used VERBATIM as query, system_prompt context cost (4× multiplier), step dependencies
   - Runtime context available (parent code, insights, lineage, failure analysis with per-hop retrieval coverage)
   - Four explicit contracts evolved prompts MUST satisfy: (1) placeholders in system/user, (2) JSON output with "code" field, (3) double-brace escaping

2. **Removed SYSTEM_CONSTRAINTS module** (`gigaevo/prompts/hotpotqa/mutation/frozen.py` import + validation):
   - Deleted `required_prefix` parameter from `PromptExecutionStage`, `GigaEvoArchivePromptFetcher`, `PromptEvolutionPipelineBuilder`
   - Removed validation checks that verified frozen constraints appeared in evolved prompts
   - Removed `required_prefix` from all pipeline YAML configs (`prompt_evolution.yaml`, `prompt_evolution_multi.yaml`, `coevolved.yaml`)
   - Rationale: Constraints are now in the task description, and the validation was a hard constraint that prevented legitimate mutations. Task description is the better mechanism.

3. **Updated all seed programs** (`generic.py`, `hotpotqa.py`, `minimal.py`, `generalization.py`):
   - Removed: `from gigaevo.prompts.hotpotqa.mutation.frozen import SYSTEM_CONSTRAINTS` import + concatenation pattern
   - Now directly use: `{task_description}` and `{metrics_description}` in system prompt, `{parent_blocks}` in user prompt
   - Seed strategy text simplified and now informed by injected task description rather than external frozen constraints

4. **Fixed watchdog display** (`experiments/hotpotqa/prompt_coevolution/run_watchdog.py`):
   - P1 fitness row was showing `valid_frontier_fitness` (MAP-Elites frontier metric, meaningless for meta-prompts)
   - Changed to query P1's archive directly via `get_prompt_archive_stats()`, showing actual best fitness + elite count
   - Prompt fitness plot now only plots P1 (removed nonexistent P2/DB7 reference)

5. **Test suite**: Updated `/run-tests` skill to exclude benchmark tests (`--ignore=tests/benchmarks`), fixing test command hanging issue

**Why applied uniformly**: Meta-prompt quality improvement applies to P1 only (no main run changes). All 3 main runs (X1/X2/X3) benefit equally from improved prompt fitness signals.

**Previous data preserved**: No main run data invalidated. P1 archive from Amendment #9 relaunch is discarded (trained without proper task context); DBs 4/5/8 (main runs) preserved.

Files changed: `problems/prompt_evolution/task_description.txt`, `problems/prompt_evolution/initial_programs/generic.py`, `problems/prompt_evolution/initial_programs/hotpotqa.py`, `problems/prompt_evolution/initial_programs/minimal.py`, `problems/prompt_evolution/initial_programs/generalization.py`, `gigaevo/prompts/coevolution/stages.py`, `gigaevo/prompts/coevolution/pipeline.py`, `gigaevo/prompts/fetcher.py`, `config/pipeline/prompt_evolution.yaml`, `config/pipeline/prompt_evolution_multi.yaml`, `config/prompt_fetcher/coevolved.yaml`, `experiments/hotpotqa/prompt_coevolution/run_watchdog.py`, `tests/prompts/test_coevolution_pipeline.py`, `.claude/skills/run-tests/SKILL.md`.

**No confound**: Improvements apply uniformly. Task description injection enhances meta-prompt quality without changing main run behavior or fitness computation. All three main runs use same seed selection and inherit same benefit from improved mutation prompts.

**Amendment #11** — stale insights/lineage cache fix + prompt logging (no confound)

InsightsStage and LineageStage used `InputHashCache` with `VoidInput`, so their cache key never changed once computed. In the prompt evolution pipeline, fitness starts as a Beta(1,3) prior (0.25, trials=0) and updates as main runs report outcomes. Insights computed at fitness=0.25 were cached forever — never re-run when fitness rose to 0.60+. This created misleading insights ("this prompt performs poorly") that distorted the mutation model.

**Fixes**:

1. **PromptInsightsStage / PromptLineageStage** (`gigaevo/prompts/coevolution/stages.py`):
   - Subclasses of InsightsStage / LineageStage with `FitnessMetricsInput` (optional `fitness_metrics: FloatDictContainer | None`)
   - DataFlowEdge from EnsureMetricsStage carries validated metrics dict → included in cache key → cache invalidates when trials/fitness change
   - When `trials=0`: stage skips with "fitness is Beta prior, deferred" — avoids generating insights from dummy fitness
   - When `trials>0`: delegates to parent class for normal LLM analysis with real data

2. **Pipeline DAG update** (`gigaevo/prompts/coevolution/pipeline.py`):
   - Added DataFlowEdges: EnsureMetricsStage → InsightsStage, EnsureMetricsStage → LineageStage (input_name="fitness_metrics")
   - Removed redundant ExecutionOrderDependency (ordering now implicit via DataFlowEdge)
   - Node factories use PromptInsightsStage / PromptLineageStage instead of base classes

3. **Prompt logging for verification** (`gigaevo/prompts/fetcher.py`, `gigaevo/llm/agents/mutation.py`):
   - Fetcher logs sampled prompt templates (system + user, first 300 chars) at INFO level
   - MutationAgent logs formatted system prompt preview (first 200 chars) at INFO level
   - Enables offline verification that placeholders are correctly substituted

4. **Test update** (`tests/prompts/test_coevolution_pipeline.py`):
   - Updated `test_insights_after_metrics` and `test_lineage_after_metrics` to check DataFlowEdge instead of explicit ExecutionOrderDependency

Files changed: `gigaevo/prompts/coevolution/stages.py`, `gigaevo/prompts/coevolution/pipeline.py`, `gigaevo/prompts/fetcher.py`, `gigaevo/llm/agents/mutation.py`, `tests/prompts/test_coevolution_pipeline.py`.

**No confound**: Fix applies to P1 pipeline only. Main runs (X1/X2/X3) are unaffected — they don't use InsightsStage/LineageStage for prompt fitness. All runs benefit equally from non-stale insights in P1.

**Amendment #12** — model_name fix for redeployed vLLM servers (no confound)

The vLLM mutation servers were redeployed with model ID `Qwen3-235B-A22B-Thinking-2507` (previously `Qwen/Qwen3-235B-A22B-Thinking`). The Hydra config `config/constants/endpoints.yaml` had been changed to `model_name: deepseek/deepseek-v3.2` (for OpenRouter usage), but the launch script only overrode `llm_base_url` without overriding `model_name`. Result: every LLM call returned 404 ("model does not exist").

**Fix**: Added `model_name=Qwen3-235B-A22B-Thinking-2507` to all 6 Hydra override blocks in `launch.sh` (2 config verification + 4 launch commands). Does not modify the global `endpoints.yaml` config (used by other experiments like vartodd with OpenRouter).

**Previous data invalidated**: All runs produced 0 successful mutations. DBs 4/5/6/8 flushed, full restart.

Files changed: `experiments/hotpotqa/prompt_coevolution/launch.sh`.

**No confound**: Infrastructure fix only — corrects model routing. No change to prompts, fitness computation, or pipeline logic.

**Amendment #13** — fix fitness_metrics DataFlowEdge source for InsightsStage/LineageStage (no confound)

The DataFlowEdge for `fitness_metrics` sourced from `EnsureMetricsStage`, which filters output to MetricsContext-defined keys only (fitness, is_valid, prompt_length). The `trials` field was excluded, causing `PromptInsightsStage.compute()` to always see `trials=0` and skip. Prompts with real trial data never got LLM-generated insights.

**Fix**: Changed DataFlowEdge source from `EnsureMetricsStage` to `PromptFitnessStage` which outputs the full metrics dict including `trials`, `successes`, `mean_child_fitness`, and `main_*` metrics. P1 only restart (X1/X2/X3 unaffected — they don't use PromptInsightsStage).

Files changed: `gigaevo/prompts/coevolution/pipeline.py`, `tests/prompts/test_coevolution_pipeline.py`.

**No confound**: Fix applies to P1 pipeline only. Main runs continue uninterrupted. P1 DB 6 flushed and restarted to pick up the fix.

**Amendment #9** — per-mutation prompt sampling (no confound)

The prompt fetcher cached a single sampled prompt for 30s (cache TTL), so all mutations dispatched within that window used the same co-evolved prompt. With ~2-8 mutants per generation dispatched in <1s, most prompts in the P1 archive accumulated zero trials despite the main runs completing multiple generations.

Fix: split `_refresh_champion()` into `_refresh_candidates()` (caches candidate list from Redis with TTL) and `_sample_prompt()` (fitness-proportional sample on every `fetch("mutation", "system")` call). System+user calls within one mutation are paired via `_current_pack`. Each mutation now independently samples a prompt from the P1 archive.

Files changed: `gigaevo/prompts/fetcher.py`, `tests/prompts/test_fetcher.py`.

**Previous data invalidated**: Early gens (0-4) collected with biased prompt sampling — most prompts had 0 trials. DBs 4/5/6/8 flushed, full restart.

**No confound**: Fix applies uniformly to all 3 main runs. No change to prompt evolution run (P1) or fitness computation.

**Amendment #8** — switch from 2+2 to 3+1 topology (no confound)

Changed from 2 main + 2 prompt runs (1-to-1 pairing) to 3 main + 1 prompt run (1-to-many coupling). P1 now uses `prompt_evolution_multi` pipeline, aggregating stats from X1 (DB 4), X2 (DB 5), and X3 (DB 8) via `main_run_sources`. All 3 main runs share the same P1 prompt archive (DB 6) for co-evolved mutation prompts.

Rationale: 3× trial data for prompt fitness means faster convergence of Bayesian posterior. The single prompt run sees mutations tested across 3 independent main runs, reducing noise in prompt fitness estimates.

New X3: chain LLM `10.225.185.235:8001`, mutation LLM `10.226.185.47:8777`, DB 8. P2 (DB 7) removed.

Run design table, launch.sh, and run_watchdog.py updated. No prior data — clean start.

**No confound**: All main runs use identical config except chain/mutation LLM endpoint. P1 aggregates uniformly across all sources.

**Amendment #7** — scientific soundness audit fixes: constraint enforcement, pessimistic prior, metrics denominator, prompt ID hashing (no confound)

A methodology expert audit identified 2 critical and 2 major issues in the prompt co-evolution system. All four are fixed before any valid data collection:

1. **C1: Constraint enforcement** (`stages.py`, `fetcher.py`, `pipeline.py`): Added `required_prefix` validation — `PromptExecutionStage.compute()` and `GigaEvoArchivePromptFetcher._execute_entrypoint()` now verify that `SYSTEM_CONSTRAINTS` appears in the system prompt text. Without this, the mutation LLM could evolve away the frozen constraints, conflating "better strategy" with "removed safety rules".

2. **C2: Pessimistic prior** (`stages.py`, `pipeline.py`, both YAML configs): Changed default from Beta(1,1) → Beta(1,3). Untested prompts now start at fitness=0.25 instead of 0.50. This prevents archive churn where untested prompts evict mediocre-but-tested ones before accumulating data.

3. **M1: metrics_count denominator** (`fetcher.py`, `stats.py`): `mean_metrics` was dividing by `total_trials` but not all trials contribute metrics (e.g., REJECTED_ACCEPTOR has no metrics). Now tracks `metrics_count` separately and uses it as denominator.

4. **M4: prompt_id includes user text** (`stats.py`, `stages.py`, `fetcher.py`): `prompt_text_to_id()` now hashes both system and user text. Previously, two programs with the same system prompt but different user prompts got the same ID, conflating their stats.

**Previous data invalidated**: C2 changes fitness computation for all existing archive entries. M4 changes prompt ID hashing, making existing `prompt_stats:*` keys orphaned. All data from Amendment #6 relaunch discarded — DBs 4-7 flushed.

Files changed: `gigaevo/prompts/coevolution/stages.py`, `gigaevo/prompts/coevolution/stats.py`, `gigaevo/prompts/fetcher.py`, `gigaevo/prompts/coevolution/pipeline.py`, `config/pipeline/prompt_evolution.yaml`, `config/pipeline/prompt_evolution_multi.yaml`, `tests/prompts/test_coevolution_pipeline.py`, `tests/prompts/test_coevolution_stages.py`, `tests/prompts/test_fetcher.py`.

**No confound**: All fixes apply uniformly to both treatment pairs (X1+P1, X2+P2). No prior valid data existed — prior relaunch (Amendment #6) produced X1 gen 25 + X2 gen 16, but fitness computation was flawed (Beta(1,1) prior + system-only prompt IDs). Full restart required.

**Amendment #6** — seed prompts updated to inline production mutation prompts (no confound)

The initial seed programs (`generic.py`, `hotpotqa.py`) used stubs instead of the actual tested production mutation prompts from `gigaevo/prompts/mutation/`. This prevented the mutation LLM from seeing or evolving the real prompt templates that guide the mutation strategy.

**Fixes**:
1. **generic.py**: Now inlines production `gigaevo/prompts/mutation/system.txt` + `user.txt` verbatim
2. **hotpotqa.py**: Now inlines HotpotQA-specific `gigaevo/prompts/hotpotqa/mutation/system.txt` + default `user.txt` (domain knowledge about chain, retrieval constraints, prompt engineering principles)
3. **Brace escaping bug fixed**: JSON example in user prompt template was using `{{{{` instead of `{{` (no f-string expansion needed in raw string)

These changes allow P1/P2 to see and improve the actual mutation prompts that guide the chain evolution, rather than generic stubs. The seeds provide domain context (HotpotQA case includes BM25 retrieval constraints, multi-hop reasoning patterns, prompt engineering principles for query generation and answer extraction).

**Why applied uniformly**: Both treatment pairs (X1+P1, X2+P2) use identical seed selection logic and benefit equally from accurate seeds. This is a data quality fix, not a differential treatment.

**Previous runs discarded**: Third relaunch using corrected seeds. All prior data from Amendment #4 and #5 launches flushed (DBs 4-7 cleared).

Files changed: `problems/prompt_evolution/initial_programs/generic.py`, `problems/prompt_evolution/initial_programs/hotpotqa.py`.

**No confound**: Seed quality improvement applied uniformly. No algorithmic changes.

**Amendment #5** — fix prompt fitness feedback loop; full restart (no confound)

Four bugs prevented the prompt co-evolution feedback loop from producing meaningful selection pressure:

1. **PromptFitnessStage cached forever**: Default `InputHashCache` cached the stage result after first execution. Since the stage's DAG inputs (prompt text) never change, fitness was locked to the initial value (0.01) forever, regardless of accumulating trial data. Fix: `cache_handler = NeverCached()`.
2. **Pessimistic initialization killed new prompts**: New prompts with 0 trials got fitness=0.01, immediately losing to any prompt with real data. They were evicted from the archive before ever being tested. Fix: Bayesian posterior mean with Beta(1,1) prior: `fitness = (successes+1)/(trials+2)`. New prompts start at 0.50, converging to true success rate as trials accumulate.
3. **Sync timeout too short**: `MainRunSyncHook` had 600s timeout; X1/X2 take 30-60 min/gen. P1/P2 timed out repeatedly and raced ahead (P1 at gen 15, X1 at gen 7). Fix: timeout increased to 7200s.
4. **Prompt population explosion**: P1/P2 produced ~73 prompt programs with `max_mutations=8, max_elites=5`, but X1/X2 could only test ~8 prompts/gen. Trial data was spread too thin across too many candidates. Fix: reduced prompt run `max_mutations_per_generation=3, max_elites_per_generation=3`.
5. **Archive not reindexed after fitness updates**: After Phase 5 refresh re-ran `PromptFitnessStage` with updated stats, the archive cell placements were stale — programs with degraded fitness still occupied cells, blocking better prompts. Fix: added Phase 7 `strategy.reindex_archive()` after refresh DAGs complete, which clears and re-inserts all programs with current metrics.

X1/X2 ran 7/9 gens but with a completely non-functional prompt feedback loop (all prompt fitness stuck at 0.01). No meaningful co-evolution occurred. All data discarded — DBs 4-7 flushed.

Files changed: `gigaevo/prompts/coevolution/stages.py`, `gigaevo/prompts/coevolution/sync.py`, `gigaevo/evolution/engine/core.py`, `gigaevo/evolution/strategies/base.py`, `gigaevo/evolution/strategies/multi_island.py`, `experiments/hotpotqa/prompt_coevolution/launch.sh`.

**No confound**: all fixes apply uniformly to both treatment pairs (X1+P1, X2+P2). No prior co-evolution data existed to be affected.

**Amendment #4** — fix 5 co-evolution coupling bugs; full restart (no confound)

Five bugs made the co-evolution feedback loop completely non-functional:

1. **prompt_id mismatch** (fetcher.py): write side derived ID from `sha256(program_UUID)`, read side from `sha256(prompt_text)` — IDs never matched, so P1/P2 always read 0 trials. Fix: both sides now use `prompt_text_to_id()`.
2. **Dead archive**: all prompts got fitness=0.0 (consequence of bug 1), so no new mutant could displace seeds. Fix: `PromptFitnessStage` returns 0.01 default when `trials < min_trials`.
3. **Champion-only selection**: fetcher always picked the single best-fitness prompt — only one prompt ever accumulated trial data. Fix: fitness-proportional stochastic sampling across all archive programs.
4. **Timing mismatch**: P1/P2 ran ~5× faster than X1/X2 and exhausted `max_gen=25` in ~8 min. Fix: added `MainRunSyncHook` (`pre_step_hook` on EvolutionEngine) that polls main run's gen counter and blocks until it advances.
5. **P1/P2 early death**: both prompt runs terminated after ~8 min (gen 3). DB 6/7 ended up empty.

X1/X2 ran 4/3 gens respectively on static fallback prompts (no co-evolution occurred). No `prompt_stats` keys were written. All data from this initial launch is discarded — DBs 4-7 flushed, all 4 processes killed and restarted.

Files changed: `gigaevo/prompts/fetcher.py`, `gigaevo/prompts/coevolution/stages.py`, `gigaevo/evolution/engine/core.py`, `config/constants/evolution.yaml`, `config/evolution/default.yaml`, `config/pipeline/prompt_evolution.yaml`. New file: `gigaevo/prompts/coevolution/sync.py`.

**No confound**: all fixes apply uniformly to both treatment pairs (X1+P1, X2+P2). No prior co-evolution data existed to be affected.

**Amendment #3** — fix `metrics.yaml` top-level key `metrics:` → `specs:` (no confound)

`problems/prompt_evolution/metrics.yaml` used `metrics:` as the top-level key; the framework expects `specs:`. P1 crashed at startup. Fixed before any generation ran — no data affected. Both X1 and X2 main runs unaffected (they use a different problem's metrics.yaml). **No confound**.

**Amendment #2** — P1 mutation LLM corrected to `10.226.185.47:8777` (no confound)

Pre-registration recorded `10.226.185.131:8777` for P1 (typo in IP address). The actual available server is `10.226.185.47:8777`. All 4 mutation LLM endpoints remain distinct (no sharing). **No confound**: same hardware/model, correct IP only.

**Amendment #1** — `run_test_eval.sh` re-created (no confound)

The `run_test_eval.sh` file was present in the working directory during pre-registration but was never committed to git (untracked). It was lost on context reset and re-created from scratch with identical methodology: same eval script (`experiments/hotpotqa/thinking/gen10_test_eval.py`), same chain URLs (X1: 10.226.17.25:8001, X2: 10.226.17.25:8000), same Redis DBs (4, 5), same prefix (`chains/hotpotqa/static_f1_600`), same test set (300 samples). New sha256: `6cbcac26a2743249046f2d91fa229c06a61aa4911ccd11ca301d29309615e2c2`. **No confound** — evaluation methodology unchanged.
