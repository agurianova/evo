# CARL DAG-diff A/B — issues log

## 2026-07-02 — build phase

- **Stale-key merge bug (config)**: `+mutation=structured_diff_chains` merged onto the inline
  `mutation_operator` node in `algorithm/_base.yaml`, leaking `mutation_mode` and
  `strip_comments_and_docstrings` into `StructuredDiffMutationOperator` kwargs (would crash at
  instantiation). Fixed by promoting `mutation` to a real config group: default
  `config/mutation/llm_rewrite.yaml` (node moved out of `algorithm/_base.yaml`, wired in
  `experiment/base.yaml` defaults); arm B now selects `mutation=structured_diff_chains` (no `+`),
  which replaces the group wholesale.
- **Loader pattern clobber (config)**: explicit `pattern: "*.py"` in `config/loader/directory.yaml`
  composed AFTER `pipeline=summarizer_json` and clobbered its `pattern: "*.json"`. Fixed by
  dropping the explicit default from the loader config (Python signature default carries it).
- **Arm-A prompt fairness**: OUTPUT RULE 3 didn't state that `reasoning_questions` is ONE string
  (plural name invites a JSON array, which `ReasoningChain.from_dict` rejects) and presented
  `example_reasoning` as mandatory with no types/semantics. Rewritten as a faithful field-by-field
  syntax description so arm-A failures measure the format burden, not prompt under-specification.
- **completion_tokens always 0**: `run_chain_on_dataset` wraps every LLM call in `client.copy()`
  (fresh `_call_logs`), so usage was logged into throwaway copies. Fixed locally in
  `problems/chains/summarizer/validate.py` with `_LogAggregatingClient` (copies share the parent
  log list; asyncio single-threaded, safe). Shared `LLMClient.copy()` untouched —
  `problems/prompts/utils.py` relies on copy isolation.
- **Chain progress lines** (`[chain] step …`) go to `sys.__stderr__`, not stdout — compliant with
  the validate-no-print rule; no change.

- **Problem-local prompts not loaded (caught in first smoke)**: `prompts.dir` defaulted to null,
  so arm A mutated with the STOCK Python-flavored `gigaevo/prompts/mutation/system.txt` instead of
  the chain-faithful problem prompt. First 5-mutant smoke pair killed (~21:08, PIDs 267966/268038)
  and dirs wiped. Fixed structurally: `config/pipeline/summarizer_json.yaml` now sets
  `prompts.dir: ${problem.dir}/prompts` (per-file fallback keeps arm B's `structured_diff/*` on
  package defaults). Relaunched smoke verified both arms load from the right source.

- **JSON genome rejected by mutation agent guard (arm A, caught in smoke)**: the template-echo
  guard in `gigaevo/llm/agents/mutation.py` rejected ANY code starting with `{`, killing every
  chain-genome mutation. Narrowed: only reject parsed JSON objects carrying both `code` and
  `archetype` keys (the structured-output template's signature).
- **LangChain KeyError 'parameters' on union-root schema (arm B)**: passing the raw diff schema
  dict to `with_structured_output` routed through `convert_to_openai_function`, which requires
  top-level `properties`. Fixed in `gigaevo/llm/agents/structured_diff.py` by passing the
  `{"name", "schema"}` form with `method="json_schema"`.
- **Gemini-3.5-flash 400s on the tuple-union diff schema (arm B, blocked 100-iter launch)**:
  probes isolated two independent causes — (1) Gemini hard-rejects `const` and `$ref`/`$defs`
  (opaque INVALID_ARGUMENT; fine when `const`→single-value `enum` and refs inlined), and
  (2) the positional tuple-union encoding (per-slot-per-length-per-parent models, ~87KB inlined)
  exceeds Gemini's grammar-compilation limits even fully sanitized, while raw size is NOT the
  issue (padded 120KB schema accepted). Fixed in `gigaevo/chains/dag_changes.py`: `steps` is now
  a flat array of `anyOf: [keep, new]` slots (~4KB schema) and the "dependencies reference
  earlier slots only" rule moved from the grammar into a pydantic `model_validator` (still
  rejected at `DiffSchema.validate`, before apply); `build_schema` output is sanitized
  ($ref-inlined, `const`→`enum`, `discriminator`/`default` metadata dropped). E2E probe: 3/3
  gemini calls returned valid diffs that validated and applied.

- **Engine `int('A')` crash killed every arm-B mutant (caught in smoke)**: `generate_one_mutation`
  assumed the mutator output's `base_parent` is a 1-based int (stock wire-JSON convention), but
  diff payloads use namespace letters — `int("A")` raised pre-persist, so all 119 diff mutants
  died and the 5-mutant stopper never advanced (run spun to gen 129 with 0 mutants; killed).
  All gemini calls were `ok:true`, only 3 benign validator rejections — the failure was entirely
  engine-side. Fixed in `gigaevo/evolution/engine/mutation.py` with `base_parent_index()`
  (int or namespace letter; garbage falls back to parent 1 with a warning) + unit tests.
  Arm-B smoke rerun required before the 100-iter launch.

## Smoke results

- Seed ROUGE band (chain_2step vs proxy Qwen-235B-Instruct, 8 samples): fitness 0.375 / 0.365
  across two runs (band 0.15–0.7 → PASS), per-sample 0.10–0.71, ~2 s wall, 589 completion tokens.

## E4 rerun findings (2026-07-02/03)

- **Degenerate dependency repetition (armB_e4full100, 2/108 calls)**: gemini-3.5-flash locked
  into a sampling loop and emitted `"slot_1"` ~70x inside one `dependencies` array; items ~70
  deep came back as `'slot'`/`''` — the provider's enum enforcement lapses far into long arrays
  (calls did NOT hit token ceilings: 2413/1738 tokens out). Pydantic backstop caught both;
  nothing persisted. Fixed grammar-level in `gigaevo/chains/dag_changes.py`:
  `Field(max_length=k-1)` → `maxItems: k-1` on slot k's dependency array (portable; Gemini
  accepts — smoke-verified). Also 1 transient `llm_call_error` (empty response); no retry layer
  exists in the LLM agents (`attempt` hardcoded 1) — engine refills the budget, so a transient
  blip wastes a call, not a slot.
- **Final run armB_e4v2full100 (855s): CLEAN** — 106 calls, 0 schema errors, 0 LLM errors,
  0 generation failures; 103 persisted, 100 evaluated, 100 valid, 0 invalid-after-eval.
  3 calls + 3 evals cut by the shutdown sweep at budget (all 3 unevaluated children parse as
  valid chains). Tokens: out 714,864 (−11% vs arm A) / in 1,219,183 (+46%; 13.7KB schema
  charged as input on every call ≈360K). Output savings are run-variant (E3 −42%, E4v1 −27%,
  E4v2 −11%) — the reasoning channel dominates the small diff payloads.

## Wrong pipeline in first 250v250 launch (2026-07-03)

- First armA_v250/armB_v250 launch ran on the legacy pipeline: `JsonChainPipelineBuilder`
  subclassed `DefaultPipelineBuilder` (InsightsStage + LineageStage machinery), so
  IntraMemoryStage and MutationSuggestionStage never fired. User caught it ~9 min in;
  both runs stopped and archived as runs/arm{A,B}_v250_wrongpipe_aborted.
  (All earlier runs in this experiment — full100, e4full100, e4v2full100 — used the same
  legacy base, consistently across arms.)
- Fix: `JsonChainPipelineBuilder` now subclasses `IntraMemoryPipelineBuilder`
  (`pipeline=standard` builder) with only the two ParseJsonProgram swaps;
  `config/pipeline/summarizer_json.yaml` mirrors standard.yaml's builder params.
  Both arms now get the intra card + prescriptive suggester; arm B's diff agent reads them
  via the parent's `mutation_context` metadata, same as arm A's mutation prompt.
- Verified: ruff clean; 203 tests green (tests/chains + tests/integration); 5-mutant arm B
  smoke armB_stdsmoke — 0 schema errors, 0 LLM errors, IntraMemoryStage +
  MutationSuggestionStage firing, legacy InsightsStage absent; 1 child fully evaluated
  (fitness 0.373), 4 cut by the budget shutdown sweep (expected at smoke size).
- Relaunched 250v250 on the fixed pipeline 2026-07-03 02:21 (armA_v250 PID 422961,
  armB_v250 PID 422964).

## Iteration-matched persist-window bias in analyze_ab.py (2026-07-05)

- `scan_log(first_ok=N)` originally stopped at the Nth ok=true mutation call. Review
  found two successive bugs: (1) an ok=true call can still die downstream (arm B's
  diff_schema_error is raised AFTER the LLM_CALL ok=true emit), so stopping at the Nth
  ok line undercounts arm B's window by its retries; (2) the first fix wrongly treated
  every non-llm_call_error failure as downstream-of-ok — but arm A's no_code_extracted
  failures follow ok=FALSE calls, so the window never closed for arm A and silently
  fell back to the full-log tally (144 vs true 139 on armA_np1_250).
- Final semantics: each "Failed to generate/persist mutation" line is paired with the
  ok value of the most recent mutation-call line; only failures after ok=true extend
  the window; the window closes at the NEXT call line. A stderr warning fires if the
  window never closes. Same pairing applied to report_np1_250/extract_tokens.py.
- Residual bias: a failure line can escape the window if a concurrent call line lands
  in the 1-3-line gap between a call and its failure line (undercount of at most one
  failure; ~2-3 ms gap observed).
- Verified against ground truth: armA_aligned100@100 -> 104 attempts, armB_e4full100@100
  -> 103 (all 3 failures), armA_np1_250@100 -> 139, armB_np1_250@100 -> 101 (captures
  the 1 diff_schema_error the Nth-ok rule missed); full-log tallies 108/144 unchanged.
- Downstream corrections: report_np1_250 ab_stats.json + mutation_tokens.json + figures
  regenerated; report.tex arm B numbers corrected (101 calls / one retry; tokens in
  483,088 (+4.9%); tokens out 42,463; -27% calls). Headline conclusions unchanged.
