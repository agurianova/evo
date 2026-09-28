# carl_tool_chain_diff_ab — Issues Log

## Issue 1 — retrieve tool crashed seed eval: batch fn on legacy per-sample wrapper

**Symptom.** Arm-B smoke (`smoke_235b`) seed baseline eval failed immediately:
```
TypeError: make_retrieve_fn.<locals>.retrieve_fn() got an unexpected keyword argument 'query'
[CallValidatorFunction] SubprocessError FAILED for f7dec679: exec_runner failed (exit=1)
```
Archive stayed empty (`archive_size=0`, `Parents selected: 0`); engine spun with no valid parent.

**Root cause.** `make_retrieve_fn` returns a **batch** fn `retrieve_fn(items: list[dict]) -> list[str]`.
`problems/chains/hover/full7/validate.py` registered it under the **per-sample** `tool_registry`
and called the legacy `run_chain_on_dataset(...)`. The CARL chain-runner port
(`6d2161f7`, #251, 2026-05-21) changed the legacy wrapper's tool dispatch to
per-sample `tool_fn(**resolved_input_mapping)` = `retrieve_fn(query=...)`, which a
batch fn (one positional `list[dict]`) cannot accept. Batch tools now require
`run_chain_on_dataset_stepwise(..., batch_tool_registry=...)`.

full7/validate.py was last touched `525e9b7f` (2026-04-01), **before** the CARL port,
so it never migrated — a latent break since 2026-05-21, surfaced only now because
full7 hadn't been re-run since.

**Fix.** `problems/chains/hover/full7/validate.py`: import + call
`run_chain_on_dataset_stepwise`, pass the retrieve fns as `batch_tool_registry=`
(mirrors every hotpotqa validator). No behaviour change to the chain itself.

**Blast radius (same latent bug, NOT yet fixed).** 8 sibling validators pass a batch
retrieve fn to the legacy wrapper and are broken identically since the CARL port:
`hover/{full, static, static_soft, full_no_deep, static_soft_no_deep, full7_no_deep}`,
`musique_retrieval/{full, static}`. Pure-LLM chains (aime/gsm8k/ifbench) and
per-sample-tool chains are unaffected. **Scope decision (user, 2026-07-03): fix
full7 only; 8 siblings deferred to a separate PR** — left broken intentionally.

**Verified fixed.** Post-fix smoke: seed baseline evaluated end-to-end on 235B —
`fitness=0.7711, is_valid=1.0, n_steps=7, n_tool_steps=3`, frontier cell filled.
Retrieval tool steps dispatch correctly; operator + JSON pipeline sound.

## Issue 2 — bm25s JAX GPU probe OOMs retrieval evals under GPU contention

**Symptom.** In the same smoke, ~5/11 mutant evals died fast (11-27ms) with, from
`bm25s/selection.py:11` at `import bm25s`:
```
_ = jax.lax.top_k(np.array([0] * 5), 1)
jax.errors.JaxRuntimeError: RESOURCE_EXHAUSTED: CUDA_ERROR_OUT_OF_MEMORY   (3x)
jax.errors.JaxRuntimeError: INTERNAL: RET_CHECK ... dnn_support != nullptr  (2x)
```
Intermittent: 12 evals ran full 235B chains (18-59s); the crashes coincided with
two concurrent heilbron 235B-Thinking runs (JAX-on-GPU) saturating GPU memory.

**Root cause.** `bm25s` runs a JAX-on-GPU availability probe at import. bm25s is a
CPU BM25 library — it never needs GPU JAX. Under GPU memory pressure the probe
throws and kills the eval subprocess before the chain runs.

**Fix (launch-script).** `export JAX_PLATFORMS=cpu JAX_PLATFORM_NAME=cpu` in
`launch_smoke.sh` — the exec_runner eval subprocesses inherit it, so the probe
runs trivially on CPU. **Carry this into the 8B A/B launch scripts.**

**Durable option (not applied — full7-only scope):** `os.environ.setdefault(
"JAX_PLATFORMS", "cpu")` before `import bm25s` in
`problems/chains/hover/utils/retrieval.py` would harden every hover/musique
retrieval eval framework-wide. Pending user decision.

## Issue 3 — arm A (free-rewrite) had no chain/tool-aware mutation prompt

**Symptom (latent, pre-launch).** Arm A = `mutation=llm_rewrite` loads its mutation
prompt from `${problem.dir}/prompts/mutation/`, which did not exist on full7 — so it
fell back to the package default (`gigaevo/prompts/mutation/`). That default is
**Python-source-oriented** ("you produce ONE child Python program", `code` is "Python
source, not JSON", LLM-step-only). Under `pipeline=program_is_json` the genome is
wire-JSON with `tool` steps — the default prompt would push the 8B mutator toward
Python and could never express `retrieve`/`retrieve_deep` steps. Arm B (structured
diff) was unaffected: its `structured_diff` prompt is already chain-shaped.

**Fix.** Added `problems/chains/hover/full7/prompts/mutation/{system,user}.txt`,
adapted from the summarizer chain-mutation prompts (already CARL/JSON-native). Three
surgical changes vs the summarizer version, everything else verbatim:
- ROLE: "DAGs of LLM steps" → "DAGs of LLM **and retrieval-tool** steps".
- OUTPUT RULE 3 (genome format): rewritten for the full7 wire format — top level is
  `system_prompt` + `steps` (no summarizer top-level keys), both `llm` and `tool`
  step types, and the step count / tool names / `$`-reference syntax are **deferred to
  CONTEXT** (`{task_description}`) rather than hardcoded, so all HoVer task facts flow
  from `full7/task_description.txt`. Dropped the summarizer `is_output_step` clause
  (full7 has none; harness scores retrieval coverage across all hops).
- RULE-2 causal-hypothesis examples: retargeted from summarization vocabulary to
  chain-generic (input/output/hops), to avoid leaking a specific domain.

Note: `full7/task_description.txt` still frames the genome via Python `entrypoint()`;
RULE 3 explicitly overrides that ("`code` is one COMPLETE wire-format JSON document —
not Python").

## Launch config (real 8B A/B) — `launch_arm.sh`

Both arms identical except `mutation=`; chain executor swapped 235B → **Qwen/Qwen3-8B**:
```
problem.name=chains/hover/full7  pipeline=program_is_json  llm=gemini35_flash
memory=none  num_parents=1  storage=disk  max_tokens=60000  max_mutants=250
  arm A: mutation=llm_rewrite            arm B: mutation=carl_with_retrieval_tools
env: HOVER_CHAIN_MODEL=Qwen/Qwen3-8B  HOVER_CHAIN_URL=http://10.232.89.98:4000/v1
     JAX_PLATFORMS=cpu  OMP/MKL/OPENBLAS=8  NO_PROXY⊇10.232.89.98,10.232.30.185
```
`num_parents=1` isolates single-parent mutation (no crossover confound), matching the
smoke. Analyzer reuse: `carl_dag_diff_ab/analyze_ab.py` hardcodes the
`storage/chains_summarizer/programs` glob — needs the hover storage subdir before it
can score these runs (post-run item).

## Issue 4 — eval `stage_timeout` too tight for heavy genomes; weekend relaunch

**Symptom.** In the first 8B A/B (`arm{A,B}_8b`, ~1h30m), the invalid programs that
were NOT malformed-genome parse failures were **eval timeouts**: decoded
`StageError…TimeoutError()…stage=CallValidatorFunction` — the whole 7-step chain over
`n_samples=300` on the 8B executor can exceed the per-stage budget for a heavy genome
(more steps / more retrieval hops). Arm B's 4 invalids were ALL of this class (genome
parses fine); arm A shared 4 identical timeout invalids on top of its parse failures.
The timeout is operator-independent infra loss, balanced across arms, but it discards
otherwise-valid slow genomes.

**Root cause.** `stage_timeout` defaulted to **3600s (1h)**, firing on
`CallValidatorFunction` (the `asyncio.wait_for` around the 300-sample chain eval).

**Fix (launch-script, weekend run).** Raise the eval budget so slow-but-valid genomes
finish scoring instead of being killed:
- `stage_timeout=3600 → 7200` (per-stage, bounds the 300-sample eval).
- `dag_timeout=7200 → 14400` **(added alongside)** — the whole-program DAG clock was
  also 7200, so a stage allowed 7200s would be cut by the DAG first; 14400 gives the
  raised stage timeout real headroom. Both passed as CLI overrides in `launch_arm.sh`.
- `request_timeout` (per-LLM-request, 600s) left unchanged — the gemini mutator calls
  run 36–70s, nowhere near it.
- `n_samples=300` unchanged (the ask was more time, not cheaper eval).

**Relaunch (2026-07-03 23:05).** Stopped `arm{A,B}_8b` cleanly via SIGTERM (final
counts 53 / 30 program files, **preserved on disk, not deleted**). Relaunched fresh
under tag `wknd` (`arm{A,B}_wknd`, new storage) for one uniform 7200 eval regime — no
mixing of pre/post-change evals in the analyzed set. Same config otherwise
(`max_mutants=250`, Qwen3-8B executor, gemini35_flash mutator).
- Arm A `mutation=llm_rewrite` → **PID 695650**, `runs/armA_wknd/run.log`.
- Arm B `mutation=carl_with_retrieval_tools` → **PID 695653**, `runs/armB_wknd/run.log`.
Both verified healthy at launch: storage lock acquired, seed loaded, no tracebacks.

## Issue 5 — litellm routing imbalance; simple-shuffle + fresh relaunch for fairness

**Symptom.** During the `wknd` runs, the shared LiteLLM proxy (10.232.89.98:4000)
was routing the Qwen3-8B chain-executor traffic to only **3 of 8** backends: three
saturated (one at 80 in-flight) while five sat at **0 in-flight** over minutes.
Verified via each backend's vLLM `/metrics` (`vllm:request_success_total` deltas +
`num_requests_running`). Uneven backend load ⇒ chain evals queue behind the 3 hot
servers, inflating eval wall-time for both arms.

**Root cause.** `tools/litellm.sh` set `routing_strategy: least-busy`. With a single
proxy worker and an **in-process** in-flight counter (no Redis), the counter drifts
under abort/timeout-heavy load: client-aborted and retried requests miss their
decrement, so idle backends read phantom-high and the router starves them — the
inverse of correct least-busy. The idle backends had the *lowest* lifetime
completions yet got zero new traffic, the drift signature. `routing_strategy` is
global across all model groups (also governs the 235B chains).

**Fix (proxy, user-approved).** `tools/litellm.sh` line 217
`least-busy → simple-shuffle` (stateless random spread; per-deployment `rpm` +
`max_parallel_requests` caps remain the overload guard). Rationale comment rewritten
to record the drift finding; latency-based caution (2026-04-22 regression) kept as
history. User restarted the proxy on its dedicated machine
(`tools/litellm.sh --stop` then `--background`, which regenerates the config).

**Relaunch (2026-07-04 00:42, tag `shuf`).** Because the `wknd` runs' evals were
routed under the imbalanced least-busy regime, they were stopped mid-flight (SIGTERM,
final counts 39 / 30 program files preserved) and relaunched fresh so **100% of both
arms' evals run under simple-shuffle** — no mixing of pre/post-routing-change evals in
the analyzed set. Same config otherwise (`max_mutants=250`, Qwen3-8B executor,
gemini35_flash mutator, `stage_timeout=7200`, `dag_timeout=14400`).
- Arm A `mutation=llm_rewrite` → **PID 715596**, `runs/armA_shuf/run.log`.
- Arm B `mutation=carl_with_retrieval_tools` → **PID 715599**, `runs/armB_shuf/run.log`.
Both verified healthy at launch: storage lock acquired, seed loaded. Arm A 0 errors;
arm B's only log errors are a benign `live_profiler` startup render race
(`FileNotFoundError` on `profile_live.html.tmp` → "render failed (will retry next
tick)", self-recovers) — not the eval pipeline.

**Resolution (2026-07-04, Prometheus — FULLY BALANCED, no pathology).** Enabled the
litellm Prometheus `/metrics` endpoint (`tools/litellm.sh`: `pip install
prometheus_client` into the litellm env + `litellm_settings.callbacks: ["prometheus"]`;
core `/metrics` is NOT enterprise-gated in this OSS build — only advanced label-filters
are). This exposes `litellm_deployment_{total_requests,success_responses,failure_responses}_total{api_base}`
= the proxy's OWN per-deployment routing counts.

Two false leads were ruled out with data, not assertion:
- **Not an external consumer.** Cumulative `litellm_deployment_failure_responses_total`
  is **0 on every backend** and `lsucc == ltot` (9242 == 9242), i.e. litellm dispatched
  evenly (963–1277 per backend) and abandoned nothing.
- **Not abandonment.** `lfail=0`, and the chain client timeout is 1200s with
  `stop_after_attempt(3)` (`problems/chains/client.py:31,107`) — far above the ~16–30s
  request latency, so nothing gives up on a slow backend.

A clean 180s same-window comparison of Δproxy (litellm routed) vs Δvllm (each backend's
`vllm:request_success_total`) is flat at **ratio 1.00 on all 8**:

| backend | Δproxy | Δvllm | ratio | in-flight |
|---|---|---|---|---|
| 22.52:8000  | 466 | 465 | 1.00 | 80 |
| 22.52:8001  | 537 | 537 | 1.00 | 40 |
| 22.52:8002  | 560 | 560 | 1.00 | 42 |
| 22.52:8003  | 554 | 554 | 1.00 | 40 |
| 22.171:8000 | 572 | 571 | 1.00 | 49 |
| 22.171:8001 | 545 | 545 | 1.00 | 80 |
| 22.171:8002 | 478 | 477 | 1.00 | 78 |
| 22.171:8003 | 571 | 571 | 1.00 | 80 |

Findings: (1) both layers are **balanced** — proxy dispatch 466–572/180s, vLLM
completion 465–571/180s, ratio 1.00 everywhere (no backend completes anything the
proxy didn't send). (2) An earlier 90s window showed ratio ≈1.7 on two backends; that
was litellm's **async success-counter lagging inside a short window** on the
instantaneously-busiest backends — over 180s it catches up (consistent with the
cumulative `lsucc==ltot`, `lfail=0`). (3) `num_requests_running` is an instantaneous
gauge and its "=80 hot set" **moves** between snapshots (was 22.52:8000+22.171:8002;
later a different four) = transient shuffle-burst variance, nothing pinned. (4) The
original "pinned to 3 backends" alarm was a **ramp-window measurement** (before the
arms reached steady-state throughput) compounded by that counter lag — NOT a
steady-state routing failure.

**Action: none to the proxy.** simple-shuffle is correct and provably balanced; do NOT
revert to least-busy. The A/B is fair at both layers. Prometheus left enabled for
ongoing visibility. Prior drafts of this resolution wrongly blamed an external consumer
then abandonment — both retracted; the counters show plain balance.
`tools/litellm.sh` edit (prometheus callback + corrected startup echo) uncommitted,
awaiting commit approval.

## Issue 6 — completion, A/B resolution, figure-scale bug, executor-token deliverable

**Run outcome.** Both arms ran the full 250 mutants from the same 7-step HoVer seed
(`gemini-3.5-flash` mutator, `Qwen3-8B` executor, `memory=none`, `num_parents=1`).
Analysis in `report_full250/` (`analyze_ab.py` → `ab_stats.json`, `make_figures.py` →
3 PNGs, `report.tex` → `report.pdf`, 7pp).

**Result (over completed evaluations — 14 in-flight children per arm excluded).**
- **Validity:** A `mutation=llm_rewrite` 149/242 valid (61.6%), **91 malformed-JSON
  children (38%)**; B `mutation=carl_with_retrieval_tools` 239/242 valid (98.8%),
  **0 malformed JSON** (3 benign non-parse rejections). gemini's 38% malformed rate ≈
  the weak-llama run's 40% → the free-rewrite failure is **structural to full-document
  re-emission of a tool-bearing chain, not model weakness**. This is the headline.
- **Fitness:** B child mean 0.800 / best 0.858 vs A 0.778 / 0.831 (suggestive, single
  replicate, no variance floor yet; the validity gap is categorical).
- **Structure:** both preserve 7-step topology (B 84%, A 77%); milder divergence than
  the summarizer run (retrieval task rewards keeping tool steps).
- **Tokens (disclosed confound):** both arms sent identical `reasoning.effort:high`, yet
  the provider returned a reasoning channel **only** for B's calls (87% of B output vs
  **0%** of A's). Consequence: B's *content* payload is ~1/7 of A's (~950 vs 6,712
  tokens/call, as designed), but B's *total* output is **+12%** (input +13%) — so on
  this run the diff wins on validity/fitness/legibility, **not** token cost. Cause
  unexplained; flagged in the report, not asserted as mechanism.

**Figure-scale bug (self-caught before publishing).** First `ab_overview.png` draft
clipped the valid cloud off the top: `ax1.set_ylim(-0.03, 0.6)` while hover fitness is
0.66–0.86, so every point rendered on the 0.0 floor (misleading). Fixed to
`ylim(0.59, 0.88)` with invalids drawn as crosses on an explicit floor line at
`FLOOR+0.005`; labels/titles corrected. Also removed a per-arm `n=` from the scatter
legend so the funnel (101/15 raw incl. running) is the single source of truth vs the
scatter (93/3 completed-invalid with sentinel fitness). Verified against `ab_stats.json`
numbers, which were correct all along — the defect was figure-only.

**Invalid-child reconciliation.** Raw `ab_stats.json` "invalid" counts (A 101, B 15)
mix genuine failures with snapshot-timing artifacts. Decoded: A = 93 completed-invalid
(91 `json_parse_error` + 2 other) + 8 still-running; B = 3 completed-invalid (0 parse
errors) + 12 still-running. Clean comparison uses the 242 completed children per arm.

**Executor-token deliverable (the "track CARL token usage" request).** This run has NO
per-candidate executor tokens: chain runners `client.copy()` per concurrent call and the
base `copy()` hands out a fresh `_call_logs`, so usage landed in throwaway copies and
`validate()` discarded it. Only a shared-proxy aggregate (~132M combined, both arms, no
per-arm split) was available. **Fixed forward:** `problems/chains/usage.py`
(`LogAggregatingLLMClient` sharing one log list across the fan-out + `usage_totals()` +
`ZERO_USAGE`) is wired into `full7/validate.py` (success + early-reject paths) and the
summarizer validator; 4 unit tests cover the copy-sharing invariant; lint clean. Future
HoVer runs carry per-candidate `prompt_tokens`/`completion_tokens`/`total_tokens`/
`n_llm_calls`/`llm_cost` in program metrics. **Uncommitted, awaiting commit approval.**

**Deliverables sent:** report PDF + 3 figures + summary to Telegram on completion.

## Issue 7 — Arm A "malformed JSON" was ~94% a harness schema/prompt contradiction (2026-07-04) → arm A RE-RUN

**Symptom.** Arm A (llm_rewrite) showed 91/242 (38%) `json_parse_error` children on the
gemini pair and 29 penalties on the qwen pair — reported as "free-rewrite is
structurally fragile at wire-JSON re-emission".

**Root cause.** `MutationStructuredOutput.code` (gigaevo/llm/agents/mutation.py) carried
the field description "The complete mutated Python source code. Must be valid Python
starting with imports or def statements. NEVER put JSON..." while the full7 mutation
prompt demands "one COMPLETE wire-format JSON document — not Python". The mutator obeyed
the schema over the prompt: 87 of gemini arm A's 91 parse-error children are valid
Python `def entrypoint()` emissions; true JSON breakage is 4/242 ≈ 1.7%. Qwen arm A: 28
of 29 penalties are the same class. This invalidates the malformed-rate attribution in
BOTH arm A runs (armA_shuf, armA_qwen); arm B is unaffected (DiffMutationAgent uses its
own schema).

**Fix (user-approved, applied 2026-07-04).** `code` field description rewritten
format-agnostic: "The complete mutated program, emitted verbatim in the SAME source
format as the parent program(s) — whatever format the task uses (Python source, a JSON
document, ...)". Targeted tests green (93 passed: tool_chain_diff, mutation structured
output, mutation agent, prompt-schema reconciliation). Live runs unaffected (in-memory
code; edit visible only to new launches).

**Also fixed in the same pass:** `tool_chain_diff.py::build_schema` now logs a loguru
WARNING whenever `_compact_payload` silently repairs a non-contiguous slot payload
(previously zero telemetry on repair frequency).

**Re-runs launched 2026-07-04:** `runs/armA_fixed` (gemini, PID 885246) and
`runs/armA_qwen_fixed` (Qwen3-235B-thinking, PID 885249), 250 mutants each, launchers
verbatim except tag. Old arm A runs retained on disk for the harness-artifact analysis
but excluded from the headline A/B; report Part I/II will compare armA_fixed vs
armB_shuf and armA_qwen_fixed vs armB_qwen. Note the fixed arm A runs also benefit from
the mid-run instrumentation fixes (tokens_reasoning emit, per-candidate executor
tokens via usage.py) that the original arm A runs predate.
