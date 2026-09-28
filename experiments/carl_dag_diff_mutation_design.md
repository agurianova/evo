# CARL DAG-diff mutation — design

**Status:** APPROVED (C⁺⁺ language, defaults in §7) — prototype + live probes green 2026-07-02
**Date:** 2026-07-02
**Benchmark:** `carl_pack/summarizer-evolution` (locked by user)
**Protocol:** lightweight paired runs (gigaevo-launch style, JOURNAL + issues log) — provisional, user AFK at decision time

## 1. Goal & causal chain

Evolving CARL chains by letting the LLM rewrite the raw chain JSON breaks structure and wastes tokens. Replace free-form JSON emission with a **pydantic DAG-diff**: a constrained edit language that *manifestly* — by construction, not by post-hoc validation — maps any valid chain to a valid chain.

- **Signal → behaviour → metric (baseline):** free-form JSON emission → malformed JSON / duplicate step numbers / dangling deps / cycles → mutants fail structural validation → `structural failure rate > 0`, tokens wasted per failed mutant ≈ full-genome emission cost.
- **Treatment:** LLM emits a `ChainDagDiff` (structured output); a **total applier** turns (valid chain, any well-formed diff) into a valid chain. Structurally-broken children become unrepresentable.
- **Riskiest link (RESOLVED 2026-07-02):** structured-output reliability of the per-slot diff schema on the proxy Qwen models. Live probe (`experiments/carl_diff_llm_probe.py`, Qwen3-235B-A22B-Instruct-2507): `json_schema` guided decoding **8/8 valid genomes** across all mutation archetypes; `function_calling` unavailable on this deployment (vLLM lacks `--tool-call-parser`, hard 400) → operator must use `structured_output_method: json_schema`.

**Prediction table**

| Metric | Arm A (raw JSON) | Arm B (DAG-diff) |
|---|---|---|
| Structural failure rate / mutation attempt | 5–30 % (to be measured) | **0 %** (hard expectation; any >0 is an applier bug) |
| Output tokens / mutation | full genome (~1–3k) | diff only (~0.2–0.6k) |
| Fitness (ROUGE-L, matched budget) | reference | ≥ Arm A |

## 2. Landscape (what exists)

- **CARL** (`/home/jovyan/carl`): `ReasoningChain` is a plain class; steps are pydantic (`models/steps.py`; summarizer chains use only `llm` steps). Construction validates: non-empty, unique step numbers, deps exist, no cycles (`chain.py:341`). `from_dict`/`from_json` re-run full validation; invalid content raises `ValidationError`/`ValueError`/`ChainFormatNewerError`. `ChainMutator` (`chain_evolution.py:1048`) already uses an "edit cloned spec dict → `from_dict` round-trip → rollback" harness, but is random-pool-driven, not a declarative diff. **User directive: the diff need not be based on carl** — carl round-trip becomes a post-apply *assertion*, not the mechanism.
- **gigaevo:** `Program.code` is just a `str` (`programs/program.py:120`) — a JSON genome is legal, **no Program subclass needed**. Mutation seam: `MutationOperator` ABC (`evolution/mutation/base.py:52`), concrete `LLMMutationOperator` + `MutationAgent` with `MutationStructuredOutput` (`llm/agents/mutation.py:72`) bound via `llm.with_structured_output(...)`; swap via `mutation_operator._target_` (`config/algorithm/_base.yaml:40`). Failure accounting exists: stage failures → `is_valid=0` sentinel; collector rolls up `iter_window_invalid_count`.
- **problems/chains:** existing problems evolve gigaevo-native dicts via Python `entrypoint()`; CARL is execution backend only (`carl_bridge.py`). `chain_runner.run_chain_on_dataset` consumes `ChainSpec` whose steps are **already CARL step descriptions** — reusable for CARL-JSON genomes without the Python layer. No ROUGE metric exists anywhere (net-new). Pipeline stages `ValidateCodeStage`/`CallProgramFunction` assume Python → JSON genome needs one small new stage.
- **carl_pack/summarizer-evolution:** 4 CARL wire-format seed chains (1–4 llm-steps), `data/eval.jsonl` (8 RU cases, `input`/`task`/`expected`), ROUGE-L target metric, final step flagged `is_output_step`.

## 3. Approaches considered

**A. Generic structured-diff operator in the framework + genome-specific changes subclass — RECOMMENDED (placement revised by user 2026-07-02).**
New `StructuredDiffMutationOperator(MutationOperator)` in `gigaevo/evolution/mutation/`, genome-agnostic: injected with one `AllowedChanges` object — a **general ABC** owning the per-call diff schema, parent rendering, and the total applier. Change types differ per genome, so the DAG vocabulary cannot live in the general class: `AllowedDagChanges(AllowedChanges)` for CARL chains lives in a new `gigaevo/chains/` subpackage. Keeps the framework the product (a second genome type = a second subclass).

**B. Everything problem-local.** Operator subclass defined inside `problems/chains/`, wired via `_target_`. Zero framework surface, fastest; but the reusable idea (structured-diff mutation) stays buried in a problem dir. Rejected: the OOP seam is the point of the task.

**C. Extend carl's own `ChainMutator`/`ChainEvolver`.** Rejected: random-pool driven (no LLM guidance), lives in an external pinned library, and the user explicitly decoupled the diff design from carl.

## 4. Design (Approach A)

### 4.1 Genome & problem (shared by both arms)

- Genome = CARL wire-format JSON string in `Program.code`. Both arms share genome, pipeline, validator, metrics — **only the mutation operator differs** (clean A/B).
- New problem `problems/chains/summarizer/`:
  - `initial_programs/`: the 4 seed chains from `carl_pack` as JSON text. `DirectoryProgramLoader` globs `*.py` only → add a `pattern` param (default `"*.py"`, backward-compatible) so seeds can be `.json`.
  - `shared_config.py`: loads `eval.jsonl`; `outer_context_builder(sample) → sample["input"]`; LiteLLM proxy client (Qwen chain-exec model), `remove_thinking` on.
  - `validate.py`: `validate(chain_dict) -> dict`:
    1. `ReasoningChain.from_dict(chain_dict, use_typed_steps=True)` — full CARL validation. On any exception → `{is_valid: 0, structural_ok: 0, fitness: 0}`.
    2. Guards: llm-only step types, `max_steps ≤ 8`.
    3. Build `ChainSpec` directly from the CARL step descriptions → `run_chain_on_dataset` (reuses batched runner, `<think>`-strip, cost tracking). Output = `is_output_step` step's result; applier + validation keep the output step last, matching the runner's last-step convention.
    4. Fitness = mean **ROUGE-L F1** (LCS on lowercased whitespace tokens; small pure function + unit tests — no repo precedent, net-new) of final output vs `expected` over the 8 cases.
  - `metrics.yaml`: `fitness` (ROUGE-L mean, [0,1], max), `is_valid`, `structural_ok`, `n_steps`, `completion_tokens` (aux — cost axis from the EvoC brief).
  - `task_description.txt`: terse bullets — summarization task + CARL chain field semantics (shared truth for both arms). Arm-specific genome-format instructions live in the mutation prompts, not here.
- Pipeline: custom blueprint replacing `ValidateCodeStage` + `CallProgramFunction` with one new stage `ParseJsonProgram` (`json.loads(program.code)` → dict; parse error → stage failure → `is_valid=0` sentinel). Registered in `StageRegistry`; rest of the standard DAG unchanged. Memory OFF both arms (writer + reader off, `pipeline=standard`).

### 4.2 The diff language (carl-agnostic; see `carl_dag_diff_language_brainstorm.md`)

The language design space (op-scripts, snapshot batch edits, declarative skeleton, full re-emit,
combinator DSL) is explored in the companion brainstorm doc; requirements: **complete** (any chain
→ any chain), **sound without silent normalization** (no clamping/filtering of intent), **LLM-friendly**.
An earlier positional op-script draft was retired for relying on clamp/filter normalization.

**Adopted (user decision): declarative skeleton + content delta over positional slots ("C⁺⁺")
— single LLM call, no repair round, soundness by construction.** The diff *is* the final chain:
an ordered sequence of 1..K slots (K = `max_steps`); each slot either keeps a base step by id
(with optional field edits) or introduces a new step with full content. Removals are omissions;
**position is identity** (no slugs); **all wiring is explicit backward slot references** — there
is no dependency inheritance and therefore no bypass rule; apply is pure transcription with zero
resolution logic. Abstract syntax (`gigaevo/chains/dag_changes.py`; the concrete wire schema is
generated per call from the actual parents by `AllowedDagChanges`):

```python
SlotRef_k = Literal["slot_1", ..., "slot_{k-1}"]   # slot k's dep enum — strictly backward; slot 1: []

class KeepStep_k(BaseModel):
    kind: Literal["keep"]
    id: Literal["a1", ..., "aN"]                   # dynamic: ids of the chosen base parent only
    edits: list[FieldEdit] = []
    dependencies: list[SlotRef_k]                  # always explicit

class NewStep_k(BaseModel):
    kind: Literal["new"]; step_type: Literal["llm"]
    title: str; aim: str; stage_action: str; reasoning_questions: str = ""
    dependencies: list[SlotRef_k]

class ChainDagDiff(BaseModel):                     # top level = anyOf(base-A branch, base-B branch)
    reasoning: str                                 # reason first, then emit
    base_parent: Literal["A"]  # or Literal["B"]   # branch discriminator; keep-id enums match branch
    steps: Slots                                   # 1..K slots; wire encoding below
    chain_edits: list[ChainFieldEdit] = []         # frozen for the summarizer runs
```

**Soundness — everything by construction, nothing to repair:**
1. *Existence, ordering, acyclicity* — slot k may cite only `slot_1..slot_{k-1}`: structurally
   present (arrays have no holes) and strictly earlier. Under E3 (chosen encoding, below) the
   dep vocabulary is one shared enum `slot_1..slot_{K-1}` and the strictly-earlier rule is a
   pydantic `model_validator` — enforced at `DiffSchema.validate`, before apply, so forward/self
   refs and cycles remain rejected-before-apply rather than unrepresentable.
2. *Uniqueness* — positions are inherently unique; keeping the same base id twice = **step
   duplication** (defined, legitimate mutation; canonical renumbering disambiguates). No slugs,
   nothing to collide.
3. *Keep-id validity + base selection* — keep ids are a dynamic `Literal` of the actual base
   ids; `base_parent` is a top-level discriminated `anyOf`, so each branch carries only its own
   namespace — a keep of a donor step is unrepresentable (donor = inspiration/graft via
   `NewStep` content, §4.4).
4. *Derived properties* — numbering `1..n` canonical, `is_output_step` := last slot,
   `min_steps`/`max_steps` via `minItems`/`maxItems` (or nesting depth).
5. Post-apply **assertion**: `ReasoningChain.from_dict(...)` round-trip. Provably unreachable;
   kept as a tripwire that counts as a failure if it ever fires — the falsifier for the 0 %
   prediction.

**Wire encodings** (same abstract syntax; E1 picked 2026-07-02, superseded by E3 same day):
- **E1 — flat tuple (retired):** `steps` as a JSON Schema 2020-12 `prefixItems` array
  (per-position item schemas, `items: false`, `minItems: 1`, `maxItems: K`). vLLM honors it
  (35.9 KB schema, 8/8 live probe) but gemini-3.5-flash's grammar compiler rejects the
  per-slot-per-length model explosion with an opaque 400 even after full sanitization
  (raw size is not the limit — a padded 120 KB schema passes).
- **E2 — unrolled nesting (fallback, unused):** `steps` as a K-level cons-list
  `{step, rest?}` with distinct per-level schemas — only nested objects, enums, and nullable
  fields. Identical guarantees (nesting cannot skip levels).
- **E3 — flat list + validator (CHOSEN):** `steps` as a plain array, `items` =
  `anyOf: [keep, new]` shared across positions, `minItems`/`maxItems`, deps drawn from one
  `slot_1..slot_{K-1}` enum; the strictly-earlier rule moves into a `model_validator` (soundness
  item 1). ~4 KB schema; `build_schema` additionally emits gemini-compatible JSON Schema
  ($refs inlined, `const`→single-value `enum`, `discriminator`/`default` metadata dropped —
  gemini hard-rejects `$ref`/`const`). E2E probe 3/3 valid diffs on gemini-3.5-flash; payload
  shape identical to E1, so prompts and failure taxonomy are unchanged.

Enforcement point: decode-time grammar where the stack honors the schema; otherwise pydantic
validation + the standard LLM-call retry (counted `llm_call_error`). Either way no
representable-but-invalid diff exists and nothing invalid is ever applied — "one round" holds:
one mutation call, no error-feedback loop.

Ergonomic cost (accepted): two reference namespaces — keeps cite base ids, wiring cites
new-chain positions. The prompt renders the base chain with ids + current wiring and instructs
slot-relative deps. The theorem shifts residual LLM mistakes from structural failures to
valid-but-different wiring — semantic variation that fitness selects on, which is the point.

Completeness: an all-`NewStep` skeleton reaches any target chain with ≤ K steps (relative to the
covered field surface: editable step fields ∪ chain fields ∪ the `step_type` union). A canonical
op-log (added/removed/edited/rewired/duplicated) is *derived* by the applier from base→child for
logging and the EvoC "decision tree of successful changes" — the LLM never emits ops.

### 4.3 Allowed-changes spec (class hierarchy — user 2026-07-02)

`AllowedDagChanges` is NOT the general class: change vocabularies differ per genome type. The
operator depends only on the general ABC; each genome family subclasses it.

```python
# gigaevo/evolution/mutation/allowed_changes.py — general, genome-agnostic
class AllowedChanges(ABC):
    @abstractmethod
    def build_schema(self, parents: dict[str, str]) -> DiffSchema: ...   # wire JSON schema + validator, per call
    @abstractmethod
    def render_parents(self, parents: dict[str, str]) -> str: ...        # prompt block with id namespaces
    @abstractmethod
    def apply(self, diff: Any, parents: dict[str, str]) -> str: ...      # total: validated diff -> child genome code
    @abstractmethod
    def describe(self) -> str: ...                                       # prompt block: what changes are legal

# gigaevo/chains/dag_changes.py — CARL-chain subclass (positional-slot language, §4.2)
class AllowedDagChanges(AllowedChanges):
    allowed_changes: set[Literal["add", "remove", "edit", "rewire"]]   # capabilities, not schema ops
    editable_fields: set[EditableField]
    editable_chain_fields: set[ChainField] = set()
    frozen_steps: set[str] = set()      # EvoC wishlist: these ids must appear as bare `keep`
    min_steps: int = 1
    max_steps: int = 8
```

Consumed twice: rendered into the mutation prompt (tell the LLM what's legal) and enforced via
the dynamic per-call schema (`edits` field enums narrowed to `editable_fields`; frozen ids
offered only as an edit-free `keep` variant; `min_steps`/`max_steps` as `minItems`/`maxItems`).
One caveat: `frozen_steps` *presence* ("this id must appear somewhere") is existential and not
schema-expressible — when used, it is an apply-time check whose violation counts as a failed
mutation attempt (no repair). Moot here: summarizer runs freeze nothing. All changes allowed,
chain-level fields frozen.

### 4.4 Operator (the OOP extension)

- `StructuredDiffMutationOperator(MutationOperator)` in `gigaevo/evolution/mutation/structured_diff.py`. Injected via Hydra: one `AllowedChanges` object (`_target_: gigaevo.chains.dag_changes.AllowedDagChanges` for the summarizer runs), prompts dir, LLM router. Schema building, parent rendering, and application all go through the `AllowedChanges` interface — the operator never sees CARL.
- Parent semantics (user decision): both parents rendered with disjoint id namespaces (`a1..aN`, `b1..bM`); **the LLM selects the base parent in the same structured call** (as `MutationStructuredOutput.base_parent` already does today). Enforced by construction via the top-level discriminated `anyOf` (§4.2 point 3): each branch's keep-id enums cover only the chosen base — the donor is inspiration/graft material, applied only via `NewStep` content. Same `num_parents=2` in both arms.
- LLM call: `router.with_structured_output(<per-call wire schema>)` (method `json_schema` — probe-mandated, §4.6), via a thin `DiffMutationAgent(LangGraphAgent)` mirroring `MutationAgent`'s build_prompt → call_llm → parse_response flow so LLMCall monitoring/retry conventions carry over; `parse_response` validates via the `AllowedChanges` schema and applies the diff instead of extracting Python.
- Prompts: externalized `prompts/<name>/` files with `{task_description}` placeholder (convention). ⚠ All literal `{`/`}` in JSON examples inside `.txt` prompts must be doubled.
- Arm A operator: existing `LLMMutationOperator`, `mutation_mode=rewrite`, `strip_comments_and_docstrings=false` (AST canonicalization would crash on JSON), prompts instructing full mutated CARL JSON in the `code` field.

### 4.5 Failure accounting (headline metric)

Per mutation attempt, categorized:
- `json_parse_error` (arm A: `ParseJsonProgram` stage failure),
- `carl_validation_error` (arm A: `validate.py` step 1 → `structural_ok=0`),
- `diff_apply_assertion` (arm B: post-apply round-trip failure — expected 0),
- `diff_schema_error` (arm B: post-decoding `TypeAdapter` rejection — expected ~never under guided decoding; counted separately from `llm_call_error` so a proxy that silently stops enforcing the grammar is visible),
- `llm_call_error` (both arms: structured-output failure after retries → `MutationError`, from engine logs / LLMCall events).

Program-level failures land in Redis metrics (`is_valid`, `structural_ok`) → tabular CSV export; operator-level failures from logs. Report failures/attempt + wasted output tokens per arm.

### 4.6 Experiment plan

- Two arms × ≥1 run each (2 replicates per arm if budget allows — variance-floor caveat), identical: seeds (4 chains), `max_mutants` (300–500), algorithm (`single_island_no_distant_parents`), models (proxy Qwen: bigger model mutates, Qwen3-8B executes chains), `num_parents=2`, memory off, `storage=disk`. Only `mutation_operator` config differs.
- Pre-launch smoke: (1) structured-output probe of `ChainDagDiff` on the proxy mutator model — **DONE 2026-07-02**: 8/8 valid genomes on Qwen3-235B-A22B-Instruct-2507 via `json_schema`, 2–5 s/call, mutations semantically on-target (insert/delete/rewire/edit/rewrite/duplicate/grow/free); (2) **encoding probe** — **DONE**: vLLM guided decoding honors `prefixItems` → **E1 chosen**; `tools` mode 400s (no `--tool-call-parser`) → `structured_output_method: json_schema` mandatory; (3) seed chains score ROUGE-L in the expected 0.55–0.65 band (pack README) — else runner/prompt bug. **Remaining before launch.**
- Offline soundness evidence (`experiments/carl_diff_prototype.py`, 2026-07-02): 6 hand-written archetype diffs apply + round-trip valid; 8 illegal-diff classes rejected at the schema layer; **fuzz 2000/2000** random schema-valid diffs → valid CARL chains; schema 35 872 bytes, 35 `$defs`.
- Success: arm B structural failures = 0 **and** fitness trajectory ≥ arm A at matched budget; secondary: token cost per accepted mutant.
- Logging: `experiment_archive/JOURNAL.md` entries per launch/finding; `04_issues_log.md`; Telegram updates at launch/completion.

## 5. Risks

1. **Schema size/adherence on Qwen** — RETIRED 2026-07-02: 35.9 KB schema, `json_schema` guided decode 8/8 on live proxy; `function_calling` is a hard 400 on this deployment (no `--tool-call-parser`) so the operator pins `structured_output_method: json_schema`. With no repair round, decode-retry exhaustion = `llm_call_error` — still watch its rate during the run.
2. **8-sample ROUGE-L noise** — fitness resolution is coarse; failure rate (primary) is unaffected; note when interpreting quality.
3. **Conservatism bias** — the language is complete (all-`NewStep` reaches any chain), but the keep-vs-new framing may bias the LLM toward small edits and under-explore restructures; watch the derived op-log distribution, counter in the prompt if skewed.
4. **`is_output_step` drift** — applier pins output flag to last step; validation enforces exactly one.

## 6. Out of scope

Change-step-type op (llm-only benchmark), cross-graft `CopyStepFromDonor` op (possible follow-up), cascade validation from the EvoC brief, CARE/platform integration, non-llm step types, prompt co-evolution interplay.

## 7. Decisions (user-approved defaults, 2026-07-02)

1. Protocol: lightweight paired runs (no manifest gate).
2. Mutator model: bigger proxy Qwen for both arms; Qwen3-8B executes chains.
3. `max_mutants` = 500 per arm.
4. Clean 2-arm A/B (no A′ full re-emit ablation).
5. Class placement (revised by user 2026-07-02): general `AllowedChanges` ABC next to the operator in `gigaevo/evolution/mutation/`; CARL-chain subclass `AllowedDagChanges` in new `gigaevo/chains/` subpackage — NOT problem-local, and NOT the general class (change vocabularies differ per genome type).
6. Diff language: C⁺⁺ positional slots, single call, no repair round (§4.2); wire encoding **E1 (probe-verified)**; enforcement `structured_output_method: json_schema` (tools mode unavailable on proxy).
7. `chain_edits`: chain-level fields frozen for the summarizer runs.
