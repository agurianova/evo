# The DAG-diff language — design-space brainstorm

**Status:** DRAFT for discussion — companion to `carl_dag_diff_mutation_design.md`
**Date:** 2026-07-02

The diff language is the key object of the whole effort. This doc explores the design space
and lands on a recommendation. The earlier draft (positional op-script with clamping/filtering)
is retired: it was sound only via *silent normalization*, which corrupts LLM intent — the model
asks for X, gets X′, and the fitness signal attributes X′'s outcome to X.

## 1. Properties a candidate language is scored against

| # | Property | Meaning |
|---|---|---|
| P1 | **Completeness** | any valid chain → any valid chain is expressible (within the covered field surface) |
| P2 | **Soundness** | every well-formed diff yields a valid chain. Grades: **(a)** by construction › **(b)** checked + repair round › **(c)** normalized/clamped |
| P3 | **Intent preservation** | the applied change is exactly what the LLM stated — no silent reinterpretation (rules out P2-grade (c)) |
| P4 | **LLM ergonomics** | no mental simulation of intermediate states; references match what the prompt showed; shallow schema; reasoning-before-payload field order |
| P5 | **Token efficiency** | emission cost scales with the *change*, not the chain |
| P6 | **Diff legibility** | the change is analyzable/loggable as "what happened" — feeds the EvoC brief's "save successful chain-changes into a decision tree", and later gigaevo memory cards |
| P7 | **Extensibility** | new step types (tool/mcp/...), chain-level fields, frozen-step masks slot in without redesign |

Two structural insights up front:

- **Numbers, `is_output_step`, and acyclicity-by-ordering should be *derived*, never stated.**
  If the applier canonically renumbers `1..N` from an ordered step list and pins the output flag
  to the last step, three whole error classes (duplicate numbers, missing/multiple output steps,
  forward refs) become *unrepresentable* — the strongest form of soundness, with zero intent loss
  (these are bookkeeping, not intent).
- **Defined operational semantics ≠ silent normalization.** "Removing a step bypasses it: its
  dependents inherit its dependencies" is a *language rule* the LLM can rely on and exploit
  (like a compiler's well-defined behavior). "Your dangling dep was dropped" is a *fallback* that
  hides an error. Keep the former, ban the latter.

## 2. Candidate paradigms

### A. Imperative op-script (the retired draft)

A sequence of ops (`add_step`, `remove_step`, `edit_step`, `set_dependencies`) with positional
addressing, applied left-to-right.

- P1 ✓ (remove-all + add-all). P2 only via (c)-grade clamping/filtering → P3 ✗.
- P4 ✗✗ — the killer: after op 1 changes positions, the LLM must *simulate the intermediate
  chain* to address op 2 correctly. Autoregressive models are demonstrably bad at this kind of
  stateful bookkeeping; every op multiplies the aliasing risk.
- P5 ✓ (pay only for changes). P6 ✓ (ops read as intentions).

Fixable by switching to stable names + snapshot addressing (→ B), but the sequential-application
semantics remains a footgun (op 2 edits a step op 1 removed — conflict policies needed).

### B. Snapshot-addressed batch edit

All ops reference the *base* chain by stable step ids; applied as one atomic batch
(`removals: {ids}`, `additions: [...]`, `edits: {id: ...}`, `rewires: {id: deps}`).

- Solves the intermediate-state problem (P4 ~✓), keeps P5/P6.
- Residual cross-field constraints that no JSON schema can express: dep targets must exist in the
  *final* graph and respect an ordering; edit/rewire keys must not collide with removals; insert
  anchors ("after s3") can name a removed step. Each needs conflict policy → either (b)-grade
  checks + repair, or back to (c)-grade normalization.
- Verdict: workable, but the final topology is *implicit* — computed from four op sets — so the
  LLM never states (and the schema never sees) the thing that must be valid.

### C. Declarative skeleton + content delta — **RECOMMENDED**

Terraform/Kubernetes lesson: imperative change-scripts are only correct relative to an assumed
starting state and can strand the system in undeclared intermediate states; so both tools have
the author declare the **desired final state** and let the engine *derive* the operations
(`terraform plan`; K8s reconciliation). Deletion is omission; partial edits use defined merge
rules (strategic merge patch: unmentioned fields = unchanged); dependency ordering is derived
from references, never hand-sequenced. A wrong declaration still yields a *valid* state, and
validating a state document is cheap, whereas validating a script requires simulating it. We
borrow the authoring interface, not the reconciliation loop: declare the **skeleton** in full
(cheap; carries the DAG invariants), and *diff* the part that carries the bulk (the prompt
content) — desired-state for structure, merge-patch for content. The diff **is** the final chain's skeleton, where each slot either keeps a
base step (by id, with optional field edits) or introduces a new one (full content):

```python
EditableField = Literal["title", "aim", "stage_action", "reasoning_questions", "example_reasoning"]
ChainField    = Literal["task_description"]          # chain-level surface, extensible

class FieldEdit(BaseModel):
    field: EditableField
    value: str

class KeepStep(BaseModel):
    kind: Literal["keep"]
    id: str                                  # base-chain step key, e.g. "s2" — as rendered in the prompt
    edits: list[FieldEdit] = []
    dependencies: list[str] | None = None    # None → keep base deps (removed deps resolve by bypass rule)

class NewStep(BaseModel):
    kind: Literal["new"]
    slug: str                                # fresh name; referenceable in later deps
    step_type: Literal["llm"]                # union seam for tool/mcp/... later
    title: str
    aim: str
    stage_action: str
    reasoning_questions: str = ""
    dependencies: list[str] = []             # ids/slugs of *earlier* entries in `steps`

class ChainDagDiff(BaseModel):
    reasoning: str                                    # first field: reason, then emit
    steps: list[KeepStep | NewStep]                   # THE final chain, in order; omissions = removals
    chain_edits: list[ChainFieldEdit] = []
```

**Apply semantics (all defined, none fallback):**
1. `steps` *is* the final ordered chain. Steps of the base absent from it are removed.
2. Canonical renumber `1..N` in list order; `is_output_step` := last step. (Derived, unrepresentable-to-break.)
3. `dependencies: None` on a `KeepStep` = inherit base deps, with the **bypass rule**: a dep on a
   removed step is replaced by that step's own (transitively surviving) deps. Explicit
   `dependencies` lists are taken literally — no filtering.
4. Acyclicity: explicit deps must reference strictly-earlier entries of `steps`.

**Residual semantic checks** (cross-field, impossible to schema-encode; violations → *reject with
a crisp machine-readable message + one repair round*, never normalize):
- R1: explicit dep references an entry not in `steps` or not earlier than the referrer;
- R2: duplicate `id`/`slug` entries in `steps`;
- R3: `KeepStep.id` not present in the base chain (largely killed by the dynamic-schema trick below).

**Scoring:** P1 ✓ (an all-`NewStep` skeleton reaches any target — completeness proof is one line;
relative to the covered surface: `EditableField` ∪ `ChainField` ∪ the `step_type` union).
P2 (a) for numbering/output/removals/ordering, (b) for R1–R3. P3 ✓ (bypass is a rule, not a
repair; everything else literal). P4 ✓✓ — the model states the new pipeline top-to-bottom exactly
as it thinks about it ("segment → extract → draft → polish"), references match the rendered
prompt, no state simulation. P5 ✓ — unchanged steps cost ~4 tokens (`{"kind":"keep","id":"s3"}`);
skeleton restatement is O(N) with a tiny constant. P6 ✓ via a free bonus: since we hold base and
child, the applier *derives* a canonical op-log (added/removed/edited/rewired) mechanically —
legible ops for logging/decision-trees without asking the LLM to emit them. P7 ✓ — `step_type`
union, `ChainField` enum, and frozen steps = "this id must appear as bare `keep` with no edits".

### D. Constrained full re-emit (schema-bound whole chain)

Bind structured output to a full pydantic chain model; no diff at all.

- P1 ✓, P2 partial (syntax guaranteed; dangling deps/cycles/duplicates still expressible),
  P5 ✗ (full genome every time), P6 ✗ (change must be reverse-engineered), and it invites
  *prompt drift* — the LLM re-types every unchanged step, mutating them incidentally.
- Not a candidate for arm B, but a cheap **ablation arm A′** worth remembering: it isolates how
  much of arm A's failure rate is JSON syntax vs. graph semantics.

### E. Combinator DSL (graph-rewrite rules)

High-level total operators: `insert_between(a, b, step)`, `parallelize(a, b)`, `fuse(a, b)`,
`wrap_with_critic(a)` … each preserving validity by construction (true P2-(a) everywhere).

- The most "manifestly sound" option and the most semantically legible (P6 ✓✓) — combinators are
  exactly the EvoC brief's reusable "successful chain-change" units.
- But P1 is a *theorem per combinator set* (easy to leave gaps), the schema is a wide union
  (P4 risk on 8–32B models), and design cost is high. **Park as a v2 layer**: once C exists,
  combinators can be macros that *compile to* skeleton diffs — soundness inherited, no new applier.

## 3. Cross-cutting soundness toolbox (orthogonal to paradigm)

1. **Static schema** — enums, required fields, `min_length`, discriminated unions.
2. **Dynamic per-call schema** — build the pydantic model *at mutation time* with
   `id: Literal["s1", ..., "sN"]` from the actual base chain: dangling `keep` refs die at decode
   time, and the id namespace is guaranteed to match the prompt rendering (this repo has been
   bitten by id-namespace mismatch before — memory `usage` tracking died exactly that way).
3. **Derived properties** — numbering, output flag, removal-by-omission (see §1).
4. **Reject + repair round** — machine-readable R1–R3 errors fed back once; repair rounds are
   *counted and reported* (they are the honest residual of the 0%-failures claim, not hidden).
5. ~~Normalization/clamping~~ — banned (P3).

Micro-variant worth one line: **atomic mutations** (exactly one change per child) would let the
dynamic schema enforce *everything* (full P2-(a)) and might suit MAP-Elites' many-cheap-mutants
regime — but contradicts the EvoC brief ("change one or several fields") and halves mutation
richness per LLM call. Not for this experiment; cheap follow-up ablation.

## 3.5 Can R1/R2 be fixed *by design*? — mostly yes

**Why they resisted at first:** "every named reference resolves to an earlier declaration" is a
*context-sensitive* property. JSON Schema and grammar-constrained decoding (xgrammar & co.) are
at most context-free, so **no single-pass schema over free names can make dangling/forward refs
unrepresentable**. The escapes are: remove the names, stage the generation, or change the binding
semantics. All three are viable:

**R2 (duplicate ids/slugs) — fully fixable, two independent ways:**
- *Reframe as semantics:* a repeated `keep` of the same base step is not an error — it is **step
  duplication**, a legitimate mutation (canonical renumbering already disambiguates the copies).
- *Binding rule for references:* name references bind to the **nearest preceding** declaration
  (lexical shadowing, as in every programming language). With either move R2 stops being an error
  class at all.

**R1 (dangling / forward deps) — three escalating routes:**

- **C (single call, named refs — current):** dynamic `Literal` for base ids + a *pre-declared
  slug pool* (`NewStep.slug: Literal["n1",…,"n8"]`, deps: `Literal[base ids ∪ pool]`) makes
  *nonexistent names* unrepresentable; shadowing kills ambiguity. The residual is exactly
  **reference-before-declaration** — and SSA-style emission keeps it rare by construction: when
  the model writes a dep list, every valid target is already in its own just-emitted output.
  Rare, not impossible → needs the repair round.
- **C⁺ (two-pass):** call 1 emits skeleton + content (the expensive part); call 2 emits *only
  wiring* under a schema built from call 1's result — one field per step, each with its own
  `Literal` enum of **strictly earlier** step ids. Different fields may carry different enums, so
  ordering, existence, and acyclicity are all schema-enforced. **Theorem-level soundness**; costs
  one extra short LLM call (~tens of tokens) per mutant.
- **C⁺⁺ (single call, positional slots):** encode `steps` as a *tuple-typed array*
  (JSON Schema `prefixItems`): position k's schema allows deps only from
  `enum ["slot_1",…,"slot_{k-1}"]` (slot 1: `maxItems: 0`). Positions are inherently unique
  (kills R2), arrays have no holes (no dangling slots), enums are strictly backward (no cycles,
  no forward refs). **Theorem-level soundness in one call**, complete for chains ≤ K slots
  (K = `max_steps`). Two costs: (i) `prefixItems` support in the constrained-decoding stack
  (vLLM/xgrammar via the proxy) is unverified → **add to the pre-launch smoke probe**; pydantic
  won't emit variable-length per-position schemas natively → hand-built schema (or an `anyOf`
  of K tuple lengths, mechanical, fine at K=8); (ii) ergonomics: deps refer to *new-chain
  positions* while `keep` refs use *base ids* — two namespaces in one head; prompt must render
  both clearly.

**Verdict — DECIDED (user): C⁺⁺, single call, no repair round, no two-pass.** The 0 % claim
becomes a theorem; the round-trip assertion stays as a pure tripwire. Two further consequences
worked out after the decision:
- **`prefixItems` demoted from load-bearing to cosmetic.** The slot design has a second wire
  encoding using only universally-supported constructs: an *unrolled cons-list* — `steps` as a
  K-level nested `{step, rest?}` with distinct per-level schemas (nesting cannot skip levels, so
  contiguity is structural; per-level dep enums give strictly-backward refs). The smoke probe now
  picks the encoding (E1 flat tuple via `prefixItems`, else E2 nesting), not the soundness mode.
- **Simplifications the positional design unlocks:** slugs deleted (position is identity);
  dependency inheritance + the bypass rule deleted (deps always explicit slot refs → apply is
  pure transcription, zero resolution logic); base-parent choice made sound by construction via
  a top-level discriminated `anyOf` whose branches carry only the chosen base's keep-id enums
  (donor keeps unrepresentable — kills the last R-check from §4).
Residual honesty: `frozen_steps` *presence* is existential, not schema-expressible — apply-time
check when used (unused in the summarizer runs). And the theorem shifts LLM slips from
structural failures to valid-but-different wiring — semantic variation fitness selects on.

## 4. Base-parent selection

The existing `MutationStructuredOutput` already has the LLM choose `base_parent`; the diff call
keeps that: both parents are rendered with disjoint id namespaces (`a1..aN`, `b1..bM`) and the
top level is a discriminated `anyOf` on `base_parent` — each branch's keep-id enums cover only
the chosen base, so a `keep` into the donor is **unrepresentable** (was an R-check; now by
construction, see §3.5). Donor content is inspiration; grafting donor steps is expressed as
`NewStep` content, or a dedicated `graft` entry kind as a v2 extension.

## 5. Recommendation

**DECIDED: Paradigm C in its C⁺⁺ positional-slot form** (§3.5 verdict) — declarative skeleton +
content delta, single call, all structural properties by construction, **no repair round**
(decode-retry exhaustion counts as `llm_call_error`; nothing invalid is ever applied). Op-log
legibility recovered by deriving the structural delta in the applier. Combinator DSL (E) parked
as a macro layer compiling to C. Arm A′ (schema-bound full re-emit) noted as an optional
ablation between arm A and arm B.

Open questions for review:
1. ~~Repair round~~ — DECIDED: 0, by construction (user).
2. `chain_edits` surface for the summarizer runs: expose `task_description` or freeze all
   chain-level fields (recommended: freeze; the eval prompt contract shouldn't drift)?
3. Arm A′ ablation — run it (3 arms) or keep the clean 2-arm A/B?
