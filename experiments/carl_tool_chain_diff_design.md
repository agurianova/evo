# CARL tool-aware DAG-diff schema — design

**Status:** proposal, pending user approval (no implementation until sign-off).
**Date:** 2026-07-03
**Owner surface:** `StructuredDiffMutationOperator` + a new `AllowedChanges` impl.
**Companion docs:** `experiments/carl_dag_diff_mutation_design.md` (LLM-only diff),
`experiments/carl_dag_diff_dependency_rule_fix.md` (slot dependency grammar).

## 1. Goal

Let the structured positional-slot DAG-diff mutation run on chains that contain
**tool / retrieval steps**, so we can battle-test structured-diff mutation on the
real **HoVer** multi-hop task (fitness = soft retrieval coverage). The current
`AllowedDagChanges` (`gigaevo/chains/dag_changes.py`) is LLM-step-only and hard
-rejects any tool step at parse time.

One-line contract: a new `AllowedChanges` subclass that parses a chain genome
containing `step_type:"tool"` steps, exposes a diff grammar able to add / drop /
reorder / retype retrieval steps and rewire their query source, and transcribes a
validated diff back into a genome the HoVer `full_chain` validator accepts.

## 2. The genome reality (why this is a NEW class, not an extension)

There are **two different chain wire formats** in the tree, and the diff operator
is genome-agnostic by construction (`AllowedChanges.build_schema/render_parents/
apply/describe`, keyed by parent letter → genome `code`):

| Task | Genome `code` wire | Parsed by | Tool steps? |
|---|---|---|---|
| `chains_summarizer` | `mmar_carl` `ReasoningChain.to_dict()` (+ platform extras `task_description`, `is_output_step`) | `AllowedDagChanges._parse` → `ReasoningChain.from_dict(use_typed_steps=True)` | no (rejected) |
| `chains/hover/*` | `problems/chains` `RawChainSpec` = `{system_prompt, steps:[LLMStep\|ToolStep]}` | `problems/chains/chain_validation.validate_chain_spec` | **yes** |

`problems/chains/types.py` is explicit about the layering: `RawChainSpec` /
`LLMStep` / `ToolStep` are the **parse layer** (the genome the LLM emits and we
mutate); `to_carl_step()` lowers them to `mmar_carl` execution types only at run
time. HoVer's mutated `code` is therefore `RawChainSpec` JSON — a flatter,
different format than the summarizer's `ReasoningChain` wire.

**Consequence:** the tool-aware diff is a *parallel* `AllowedChanges`
implementation for the `RawChainSpec` genome family. It **reuses the
positional-slot diff *pattern*** from `dag_changes.py` but not its parsing/emit
code, and it touches **neither `dag_changes.py` nor the operator** — so the live
summarizer A/B keeps byte-identical behaviour with zero parity risk. This is the
"new impl behind the existing seam" shape, not "add a branch to the abstraction".

## 3. Design decision — tool freedom (flagged for veto)

**Chosen: fully-evolvable tool steps.** The diff can add / remove / reorder
tool steps, choose `retrieve` vs `retrieve_deep`, and rewire each retrieve's
query source. Rationale: HoVer fitness is *retrieval coverage*, and the
full-rewrite baseline arm can restructure retrieval freely — so anything less
than fully-evolvable tools makes the battle-test not apples-to-apples (the diff
would be handicapped on exactly the axis that moves fitness).

Rejected alternative "frozen retrieval scaffold" (keep tool steps as fixed
positional anchors, evolve only the LLM steps around them) would be a smaller
grammar but a weaker, non-comparable experiment. If you want that instead, it is
a one-line narrowing of the grammar (drop the `new_tool` form, add tool ids to
the keep enum) — say so and I'll flip it.

## 4. Approaches considered

- **A — Frozen tool anchors.** Tool steps kept by id only, never created/edited;
  matches the existing `hover/static` variant. *Rejected:* not comparable to the
  free-rewrite arm; can't restructure retrieval.
- **B — Fully-evolvable tools via a third slot form (RECOMMENDED).** Add a
  `new_tool` slot form alongside `keep` / `new_llm`; reorder-safe wiring via
  absolute `$history[N]` derived from the renumbered query-source position.
- **C — B + general multi-param `input_mapping` editing.** Over-scoped: HoVer's
  `retrieve` / `retrieve_deep` take a single `query`. Deferred as future work; the
  grammar leaves room (query source is already a first-class slot field).

Recommendation: **B**.

## 5. The diff grammar (RawChainSpec, tool-aware)

Same positional-slot skeleton as `dag_changes.py`: the child chain **is** the
fields `slot_1 .. slot_max`, filled consecutively (a `_slots_contiguous`
model-validator forbids gaps), unused trailing slots `null`, plus the
`DiffStructuredOutputBase` evidence fields (`archetype`, `justification`,
`insights_used`, `insight_ids_used`, `card_ids_used`, `changes`, `base_parent`).

Each slot at position `k` is a union of **three flat forms** (`| None` when
`k > min_steps`):

1. **`keep`** — reuse a rendered **LLM** parent step by id, optional field edits.
   `{kind:"keep", id: Literal[<llm-step ids>], edits: StepEdits, dependencies: [<earlier slots>]}`
   (`StepEdits` = optional `title/aim/stage_action/reasoning_questions`, each
   non-empty when present). Keep is LLM-only; tool steps are re-expressed via
   `new_tool` (a tool step is fully specified by `tool_name` + query source, so
   there is no fidelity loss and the keep enum stays small).
2. **`new_llm`** — a fresh LLM step.
   `{kind:"new_llm", title, aim, stage_action, reasoning_questions, dependencies:[…]}`
   — `aim` **and** `stage_action` required non-empty (RawChainSpec `LLMStep`
   requires both, unlike the summarizer genome where `stage_action` was optional).
3. **`new_tool`** — a fresh tool step.
   `{kind:"new_tool", tool_name: Literal[<available_tools>], query_source: Literal["outer_context", <earlier slots>]}`
   No explicit `dependencies` field — the DAG dependency is **derived** from
   `query_source` (a retrieve consumes exactly one query), which keeps the
   grammar small and makes the wiring self-consistent by construction.

`dependencies` / `query_source` enums offer **only earlier slots** (position 1
has none → its only tool query source is `outer_context`), so forward- and
self-references are unrepresentable — same guarantee as the LLM-only grammar.
`keep` ids form one global parent-prefixed enum across all rendered parents
(crossover); `base_parent` is lineage attribution. Emitted via
`gigaevo.llm.schema_compat.portable_json_schema` on the guided-decoding path
(Qwen3-8B, `json_schema` method) — three flat forms per slot stays under the
grammar-complexity cliff at `max_steps = 7`.

Concrete example (2-hop retrieval, seed-shaped):

```json
{"archetype":"Guided Innovation","base_parent":"A",
 "justification":"insight 1: add a second retrieval hop on the refined query",
 "insights_used":["insight 1"],"insight_ids_used":[{"parent":"A","insight":1}],
 "card_ids_used":[],"changes":[{"description":"…","explanation":"…"}],
 "slot_1":{"kind":"new_tool","tool_name":"retrieve","query_source":"outer_context"},
 "slot_2":{"kind":"keep","id":"a2","dependencies":["slot_1"]},
 "slot_3":{"kind":"new_tool","tool_name":"retrieve_deep","query_source":"slot_2"},
 "slot_4":{"kind":"new_llm","title":"Verdict","aim":"…","stage_action":"…",
           "reasoning_questions":"","dependencies":["slot_3"]},
 "slot_5":null,"slot_6":null,"slot_7":null}
```

## 6. Reorder-safe wiring (riskiest link)

Tool `input_mapping` `$`-refs resolve against raw `step_outputs` in **execution
order**, decoupled from `dependencies` (confirmed in `chain_runner._resolve_reference`:
`$history[N]` = `step_outputs[N]`, **0-based absolute**; `$outer_context` = sample
context). A relative `$history[-1]` would follow *position*, so a reordering diff
could silently point a retrieve at the wrong upstream output — valid chain, quietly
degraded coverage.

**Resolution:** the transcriber emits **absolute** refs. Slots fill contiguously
and renumber `1..k`, so a `query_source = slot_j` becomes step `j` (1-based) whose
output is `step_outputs[j-1]`:
- `query_source = "outer_context"` → `input_mapping = {"query":"$outer_context"}`, `dependencies = []`
- `query_source = "slot_j"` → `input_mapping = {"query":"$history[j-1]"}`, `dependencies = [j]`

This is reorder-safe by construction (absolute index tied to the renumbered
source), and a unit test asserts the emitted ref resolves to the intended step's
output under `_resolve_reference`.

## 7. Applier & validation alignment

`apply(diff, parents)` transcribes each filled slot into a `RawChainSpec` step
dict, renumbers `1..k`, wires dependencies/`$`-refs per §6, sets the child
`system_prompt` from `base_parent`, and returns `json.dumps(wire)`. Round-trip
guard: `RawChainSpec.model_validate(wire)` (catches transcription bugs →
`MutationError`, counted as a generation failure and retried). Full semantic /
topology validation stays where it already runs — the HoVer eval pipeline's
`ValidateCodeStage` calls `validate_chain_spec(mode="full_chain",
full_chain_config=FULL_CHAIN_CONFIG)` — mirroring how `dag_changes.apply` defers
CARL validation to the pipeline.

Every `full_chain` rule is satisfied **by grammar construction**, so the
transcribed child is always valid unless the LLM's *content* is (e.g. an empty
edit — already blocked by `min_length`):

| `_validate_full_chain` / `_validate_dag` rule | Guaranteed by |
|---|---|
| `len(steps) ≤ max_steps` | slots `1..max_steps` |
| `step_type ∈ {llm,tool}` | only `keep`/`new_llm`/`new_tool` emitted |
| `tool_name ∈ available_tools` | `new_tool.tool_name` = `Literal[available_tools]` |
| DAG acyclic / no forward deps | dep & query-source enums offer earlier slots only |
| `input_mapping` values are `$`-refs | transcriber always emits `$…` |
| `require_final_llm` (False for full7) | not enforced; see §10 |

## 8. Module layout & seam

- **New, self-contained:** `problems/chains/tool_chain_diff.py` →
  `class AllowedToolChainChanges(AllowedChanges)` (name open to bikeshed).
  `__init__(*, min_steps=1, max_steps, available_tools, outer_context_token="$outer_context")`
  — values sourced from `FULL_CHAIN_CONFIG` at wire time.
- **Reused as-is (imports):** `AllowedChanges`, `DiffSchema`,
  `DiffStructuredOutputBase` (`gigaevo/evolution/mutation/allowed_changes.py`);
  `portable_json_schema` (`gigaevo/llm/schema_compat`); `RawChainSpec` /
  `LLMStep` / `ToolStep` / `ToolConfig` (`problems/chains/types.py`);
  `validate_chain_spec` is **not** imported by the class (the pipeline runs it).
- **Duplicated locally (tiny, deliberate):** the `_slots_contiguous` validator
  and the parent-id helper (~15 lines total) are re-implemented rather than
  imported from `dag_changes.py`, to keep the new module self-contained and touch
  no existing file. (If we later want DRY, extract to a shared `slot_diff`
  helper then — minimum-viable now.)
- **Unchanged:** `StructuredDiffMutationOperator`, `dag_changes.py`, the
  summarizer A/B. The new class drops into the operator's `allowed_changes`
  constructor arg via config `_target_`.

## 9. Battle-test framing (downstream — needs the seed baseline chain)

Not part of this schema's implementation; recorded so the design is falsifiable.

- **Signal:** a positional slot-diff grammar constrains the mutation LLM to a
  structured edit vocabulary instead of free wire-JSON rewriting.
- **Behaviour:** on HoVer the LLM restructures retrieval (add/drop hops,
  `retrieve` vs `retrieve_deep`, rewire query sources) and edits query-gen LLM
  steps, emitting fewer malformed-JSON / invalid-DAG children than free rewrite.
- **Metric:** (a) validity funnel — higher valid-child rate + lower
  generation-failure rate vs arm A; (b) fitness (soft coverage) trajectory ≥
  arm A at iteration-matched budget; (c) structural exploration — chain-length &
  tool-count distributions show retrieval structure actually moved.
- **Riskiest link:** §6 reorder-safe `$`-ref wiring (mitigated by absolute refs +
  a resolver test).
- **Prediction:** arm B generation-success ≥ arm A; arm B invalid-child rate <
  arm A; arm B best fitness within ±1 seed-variance of arm A, at lower output
  tokens/mutant (the summarizer result shape). The existing `analyze_ab.py` /
  `extract_tokens.py` already tally `DiffMutationAgent`, so the A/B harness is
  reused verbatim; only `problem.name` + the `allowed_changes` target change.

## 10. Open questions / decisions for you

1. **Tool freedom** — confirm §3 (fully-evolvable) vs frozen-anchor. *Default:
   fully-evolvable.*
2. **`require_final_llm`** — HoVer `full7` sets it `False`, so a chain may end on
   a retrieve and the grammar needn't enforce a final LLM step. If we later target
   a variant with `require_final_llm=True`, add a constructor flag that constrains
   the last filled slot's union to LLM forms. *Default: don't enforce (matches
   full7); carry the flag only if needed.*
3. **Class / module name** — `AllowedToolChainChanges` in
   `problems/chains/tool_chain_diff.py`. Rename freely.
4. **Tool-step title** — `new_tool` has no `title` field; the transcriber derives
   `title` from `tool_name` (+ slot). Add an optional title field only if the
   history rendering reads it meaningfully. *Default: derived, no LLM field.*

## 11. Test plan (mirrors the existing diff-operator suite)

- schema builds & is `portable_json_schema`-clean for a HoVer parent containing
  tool steps (no `_parse` rejection);
- `new_tool` transcribe: `outer_context` and `slot_j` sources produce
  `$outer_context` / `$history[j-1]` and matching `dependencies`; the child
  round-trips through `validate_chain_spec(mode="full_chain")` as valid;
- reorder safety: emitted `$history[j-1]` resolves to the intended source step's
  output under `_resolve_reference` after renumber;
- `keep` still edits an LLM step; forward/self refs unrepresentable (enum assert);
- `apply` end-to-end on the `hover/full7` baseline yields a valid full_chain;
- `describe()` mentions `new_tool`, `query_source`, and `available_tools`;
- (parity) `dag_changes.py` untouched ⇒ existing `test_diff_output_parity` /
  `test_structured_diff_operator` stay green with no change.
