# dag_tab: let the model use the whole machine

2026-07-21. Follow-up to `experiments/dag_tab_pr306_california_20260721/knn_capability_investigation.md`.
Joint plan: my analysis + codex verdict (rollout `019f8624`, 5-section audit, 10 remediation
items), then revised against codex's adversarial review of this plan (rollout `019f8653`,
9 sections). That review opened *"the plan should not ship as written"* and refuted five
load-bearing claims; every refutation is folded in below and attributed.

## Objective

A competent feature engineer, dropped into this ABI, should be able to write whatever
they would normally write. Today they cannot: several ordinary spellings are killed by
static rules that are not enforcing anything semantic, and the one thing that *is*
semantically load-bearing (frozen-fit purity, own-target invariance) is never explained
well enough to satisfy on the first attempt.

Constraints set by the owner, binding on this plan:

1. Capability is communicated through **three surfaces that must work in synergy** —
   task description, graph structured output, graph diff. Nothing else. (Superseding the
   owner's earlier "two points"; codex reviewed against the two-surface wording and
   scored S2 as a constraint violation on that basis — see G1.)
2. **No enumerated guidance menu.** The model must be creative inside a described
   capability envelope, not pick from a list of feature families.
3. Fix the **hardcoded rules** that block operations the model already knows how to write.

## The three surfaces, and why they currently fight each other

The model meets this problem through three artefacts, and they must agree:

| # | surface | what it is | what it should own |
|---|---|---|---|
| S1 | `task_description.txt` | prose ABI, prepended with the dataset's TASK/DATASET/COLUMNS | **the capability envelope and the invariants** — what a node receives, what it may fit, what is enforced |
| S2 | the genome — `graph.py` `FeatureGraph`/`FeatureNode` | the JSON the model *reads*: its parent | **what each field means in the object being read** |
| S3 | the diff — `allowed_changes.py` schema + `describe()` | the JSON the model *writes* | **how to express a change**: slots, keep/new, dependencies, structural_intent, repair semantics |

Today none of them owns anything exclusively. The rowwise/aggregate ABI alone is stated
**seven** times, in seven different vocabularies, every one of them narrower than what
the runtime actually permits:

| location | wording |
|---|---|
| `task_description.txt:16-17` | "Statistics and vocabularies must be fitted only from df_fit" |
| `graph.py:50` (`kind`) | "rowwise transforms each row **without fitted statistics**; aggregate **learns statistics**" |
| `graph.py:77` (`code`) | "aggregate code **learns only from df_fit** and applies the learned transform" |
| `allowed_changes.py:110` (`_NODE_CODE_DESCRIPTION`) | "aggregate nodes may **fit only on df_fit**, then apply row-by-row" |
| `allowed_changes.py:128` (`NodeEdits.node_kind`) | "rowwise uses df; aggregate uses df_fit, y_fit, df" |
| `allowed_changes.py:247` (new slot `node_kind`) | "rowwise uses df; aggregate **fits on df_fit** then applies to df" |
| `allowed_changes.py:494` (`describe()`) | "aggregate is for fitted transforms: learn only from df_fit/y_fit and apply to df. **Never estimate from df.**" |

Five of the seven say *statistics* or *learn*; the search returned statistics. None
mentions that `df`'s first `len(df_fit)` rows are `df_fit`. And `describe()`'s "Never
estimate from df" is, read literally, false — every aggregate node necessarily *computes*
from `df`; what is forbidden is fitting *state* from it. A model that takes that sentence
at face value cannot write any non-trivial aggregate at all.

### The vocabulary breaks between what is read and what is written

Beyond the ABI restatements, the same concept has a different name or meaning in S2 and
S3. Each row is a place where a model that correctly understood its parent still emits an
invalid child:

| concept | in the genome it reads (S2) | in the diff it writes (S3) | consequence |
|---|---|---|---|
| node ABI | `kind: "rowwise" \| "aggregate"` | `node_kind` — because `kind` is taken by the slot discriminator `"keep" \| "new"` | the word `kind` means two different things depending on direction |
| node identity | the semantic id, e.g. `fe_geo_ratio` | `Literal["a1","a2",…]` — lowercased parent namespace + 1-based position in that parent's `nodes` array (`allowed_changes.py:178`), so two parents give `a1…` and `b1…` | the mapping is never stated; the model must count array entries. The rendered parent does print `node_id=` alongside (`allowed_changes.py:431`), but never says the address is positional |
| edges | `dependencies: [node_id, ...]` | `dependencies: ["slot_k", ...]` referring to the child's own slots | same field name, different referent, never contrasted |
| code budget | `max_length=6000` | `max_length=2000` | the model cannot write back what it can read |
| rationale | `max_length=1000`, "counterfactual feature hypothesis: what signal, why this operation, what is lost" | `max_length=500`, "at most 2 short plain-text sentences" | two definitions of one field |
| ABI default | `kind` defaults `"rowwise"` (needed: persisted genomes omit it, e.g. `baseline.json:15`) | `node_kind` defaults `"rowwise"` | the persistence default leaked into the generation schema, and makes the aggregate ABI the road not taken |

### The synergy contract this plan adopts

1. **Each fact is stated once, on the surface that owns it.** The node ABI is S1's. S2
   and S3 refer to it in *its* words and add only what is specific to reading or writing.
2. **A concept keeps its name across surfaces**, or the difference is stated explicitly
   in `describe()` where the model is being asked to write.
3. **No surface may state a bound the runtime does not enforce**, and no surface may
   state one narrower than another surface's.
4. A **guard test** asserts 1 and 3 mechanically, following the prompt↔schema
   single-source convention already used in this repo — the load-bearing ABI clauses live
   in one module-level constant, S3's descriptions are built from it, and the test asserts
   S1's text contains it. Drift then fails CI instead of silently costing a search.

## The organising principle

Three layers currently police node code:

| layer | what it can prove | what it does today |
|---|---|---|
| `literal_frame_reads` (AST, mutation transcription) | which columns a node *provably* reads | **raises** on anything unprovable, killing the whole child |
| `validate_node_code` + frame slicing (runtime) | the node only ever receives `input_cols` — a column it did not declare is not present to be read | unavoidable, but see R1: it fails *silently* for whole-frame operations |
| `assert_split_invariant` (behavioural probes) | determinism, batch purity, own-target invariance | unavoidable, but **sampled**, not exhaustive — see R2 |

Layer 1 is *syntactic*, and the first draft of this plan claimed it "is not a safety
boundary at all". **Codex refuted that as written**, and the refutation shapes C1:

- It has one production caller (`_transcribe:613`) but its result feeds **three**
  consumers, not one: reject unavailable/forward reads (`:615`), repair `input_cols`
  (`:623`), repair `dependencies` (`:637`). So it is a declared *rejection* boundary
  today, not merely an inference helper.
- Two transcription tests — `test_allowed_changes.py:562-593` — assert that it raises
  for aliasing and for `.iloc`. Those are not "additional C4 tests" territory; they are
  **deliberate replacements**, and the plan must say so.

The claim that survives is the narrower one: layer 1 is not a *confidentiality* boundary.
A column a node did not declare is not present in the frame it receives (layer 2), so
nothing it rejects can leak data that layers 2 and 3 would have admitted. What its
rejections actually buy is a louder failure for a subset of spellings — at the cost of
killing the whole child for spellings that are perfectly correct.

Codex's audit makes the same point from the other side, and shows how arbitrary the
line is: `df_fit[["x6","x7"]].to_numpy()` passes only because the receiver of
`.to_numpy` is a `Subscript` rather than the `Name` `df_fit`, while the semantically
identical `df_fit.to_numpy()` dies.

**So: demote layer 1 to best-effort inference.** But the first draft also claimed
layers 2 and 3 were "exact and unavoidable" and could therefore be left alone. Codex
refuted that too, and the two refutations change what has to ship alongside C1.

### R1 — whole-frame operations fail *silently*, not loudly (refutes a plan claim)

`node_input = result.loc[:, node.input_cols].copy()` (`execution.py:406`). A node that
writes `df.to_numpy()`, `.values`, `.get(...)`, or `reindex(...)` therefore receives
**only its declared columns**, with no error — it does not read anything undeclared, it
silently computes on a narrower matrix than its author intended. Codex's four
counterexamples, all of which pass static validation (which only recognises direct
literal `df[...]`/`df_fit[...]` subscripts, `execution.py:232`) and all output checks
(`:428`), under `input_cols=["x0"]`:

```python
df["fe"] = df.get("x1", 0)                                   # silently synthesises 0
df["fe"] = df.reindex(columns=["x1"], fill_value=0)["x1"]    # silently synthesises 0
df["fe"] = df.to_numpy().sum(axis=1)                         # silently sums x0 alone
df["fe"] = df.filter(like="x").sum(axis=1)                   # silently sums x0 alone
```

Positional reads are the same hazard in another spelling: `.iloc[:, 2]` indexes the
**sliced** `input_cols` order, not the raw frame's layout. Today the attribute whitelist
bans all of these outright, so the hazard does not exist. C1 would introduce it. So C1's
own claim — that under-declaration always surfaces as an evaluation error — is **false**,
and the risk register and C4 are corrected accordingly.

This does not weaken the case for C1; it adds a required clause to it. The contract is
perfectly well-defined once it is *stated*, and stating it is free because it belongs on
S1 and B1 anyway:

> Your node receives exactly the columns listed in `input_cols`, in that order, and
> nothing else. `df` is that slice — `df.to_numpy()` is your declared inputs as a matrix,
> not the whole dataset.

With that sentence, whole-frame operations become a usable idiom instead of a trap.
Without it, C1 ships a silent-wrong-answer mode. **The sentence is a hard prerequisite of
C1, not a nicety** — mark it blocking in the implementation order.

### R2 — the own-target probe is sampled, not exhaustive (refutes a plan claim)

`assert_split_invariant` perturbs `y_fit` at three positions only —
`{0, len//2, len-1}` (`execution.py:563`) — and compares only `graph.estimator_columns`
minus raw columns. So leakage that does not surface at those three rows, or that lives in
an intermediate node whose effect is masked downstream, passes.

That was already true before this plan. It matters more *after* it, because the whole
point is to make fitted supervised state easy to write, which makes this probe the
load-bearing guard. Added as item **C5** below.

---

## Surface S1 — `problems/dag_tab/task_description.txt`

Three edits. Net effect: state the *capability envelope* and the *two real invariants*,
and delete the closed menu.

### A1 — `NODE ABI` (lines 15-18): describe what an aggregate node actually receives

The current text ("Statistics and vocabularies must be fitted only from df_fit and then
applied to df") is read at face value: every one of the 14 aggregate nodes the search
produced was literally a group statistic or a vocabulary. It also omits three facts
about the calling convention that the model cannot guess and that caused two of the
three model-written kNN nodes to die.

Replace lines 16-18 with:

Replacement text (revised clause-by-clause against codex's section 7, which found four
factual errors in the first draft — each correction is noted after the block):

```
Your node receives exactly the columns listed in input_cols, in that order, and nothing
else. df is that slice: df.to_numpy() is your declared inputs as a matrix, not the whole
dataset, and a column you read but did not declare is not there to be read.

rowwise code may be either a transform(df) function or its function body. It is called
once per row block, so a row's output must depend on that row alone.

aggregate code may be either a transform(df_fit, y_fit, df) function or its function
body, and is called once per graph execution. df_fit is the frozen fitting frame; y_fit
is its target, supplied as a one-dimensional numpy.ndarray during scored evaluation; df
is every row to be featurised, and its first len(df_fit) rows are the rows of df_fit, in
order. Any deterministic state may be fitted from df_fit and, when supervised, from
y_fit -- summary statistics, vocabularies, estimators, search structures, reference sets
-- and then queried for each row of df. State is fitted from the fitting rows only:
there is no validation split and no y for any later row. Third-party libraries installed
in the environment may be imported and used.

Two invariants are required, and validation probes them by re-executing your graph. A
row's output may depend on any row of df_fit, but never on which other rows of df happen
to be present. And for the first len(df_fit) rows -- rows at positions below len(df_fit)
are fitting rows, and you may test that positionally -- a supervised output must not
change when only that row's own y_fit changes; exclude each fitting row's own
contribution, by position or by fold. Rows at or beyond that position may use state
fitted from all fitting targets.

Both kinds must return a DataFrame with unchanged row count and index, preserve all
declared inputs unchanged, and create exactly their declared outputs. Code runs as
trusted Python under static and behavioral validation, not as a security sandbox.
```

Corrections codex forced, each of which was a real falsehood in the draft:

| draft said | why it was wrong | now says |
|---|---|---|
| aggregate "is called exactly once" | validation, determinism probes, own-target perturbations and the final refit each execute the graph again | "once per graph execution" |
| "y_fit is its target as a one-dimensional numpy.ndarray" | true for scored evaluation (`validate.py:194`); `execute_graph` and direct tests pass `y_fit=None` | "supplied as … during scored evaluation" |
| "enforced by re-execution, not by inspection" | they are **probed**, not enforced: one fixed batch subset, three fitting positions, estimator columns only | "required, and validation probes them by re-executing" |
| "you cannot detect at run time whether you are being called on fitting rows" | flatly false, and contradicts the prefix guarantee published two paragraphs above. The repo's own passing LOO test does `row.name < len(df_fit)` (`test_graph_execution.py:541`) | states the positional test explicitly, which is *better* guidance — it is how self-exclusion is actually written |

The `len(df_fit)`-prefix guarantee itself is the one major claim codex **confirmed**, with
an exhaustive call graph: `_execute_on_combined` has a single caller
(`execute_graph_triplet:491`), concatenates `[fit, validation, query]` with
`ignore_index=True`, and hands the node `result.iloc[:fit_stop]` as `df_fit`. It holds on
every path — probes at `execution.py:538-573` vary only the *query* frame, and the final
refit at `validate.py:315-320` concatenates train+validation as the fit frame and passes
query separately. *"I found no path where the prefix guarantee fails."* Publishing it
turns leave-one-out from a guessing game into two lines.

### A2 — line 13: drop the promise that unprovable reads are rejected

Currently: *"Literal df/df_fit column reads synchronize input_cols and dependencies
during mutation transcription; dynamic, aliased, and positional frame reads are
rejected."* After the layer-1 change this becomes false. Replace with:

```
Each node declares id, kind, dependencies, input_cols, output_cols, output_types, code,
rationale, and is_output. Generated inputs must come from declared earlier dependencies.
input_cols and dependencies are synchronized from literal df/df_fit column reads where
those can be read off the code; otherwise your declaration is taken as written, and a
column you read but did not declare is simply not present at run time.
```

### A3 — `SEARCH GUIDANCE` (line 29): delete the menu

Remove the sentence:

> Useful compositions include aggregate/frequency encoding followed by a bounded
> transform, a protected ratio followed by a monotonic transform, a generated spatial
> distance followed by proximity decay, and interactions between earlier generated
> features.

It is replaced by nothing. Evidence that it functions as a closed option set rather than
as illustration: the search produced exactly its four archetypes and nothing else, and
"a generated spatial distance followed by proximity decay" is precisely the
distance-to-landmark family that both arms converged on. The rest of `SEARCH GUIDANCE`
(structural_intent semantics, producer/consumer wiring, node budget) is mechanical and
stays.

---

## Surface S3 — the diff schema (`problems/dag_tab/allowed_changes.py`)

(Referred to as "Surface B" in the item numbering below, which the codex review cites.)

### B1 — `_NODE_CODE_DESCRIPTION` (line ~107): state the environment and the two invariants

This description is attached to every `code` field the model fills. Today it says
"Imports are legal" without naming a single available package, and states the
own-target rule in five words at the end. Replace with:

```
Trusted Python: either a transform function or its bare body. Explicitly create every
declared output and end with `return df`. Your node receives exactly its declared
input_cols and nothing else. numpy as np, pandas as pd and math are in scope; any
installed third-party library may be imported, including scikit-learn and scipy. Every
stochastic operation must be seeded: the graph is re-executed and must reproduce
identical outputs.
rowwise nodes see one row block of df and cannot reference df_fit or y_fit. aggregate
nodes are called once per graph execution with the frozen fitting frame df_fit, its
target y_fit, and the full frame df whose first len(df_fit) rows are df_fit in order;
any deterministic state fitted from df_fit and, when supervised, from y_fit --
statistics, vocabularies, estimators, search structures -- may then be queried per row
of df. y_fit is a one-dimensional numpy.ndarray, never a pandas object: do not use
y_fit.groupby, .iloc, .loc, .name, or .values; when pandas alignment is needed, first
construct target_fit = pd.Series(np.asarray(y_fit), index=df_fit.index, name='target').
A row's output must not depend on which other rows of df are present. A supervised
output for a row at a position below len(df_fit) must not depend on that row's own
y_fit: exclude its own contribution by position or by fold. The reserved sample_weight
output sets finite non-negative CatBoost row weights, applied to both the training rows
and the early-stopping eval set; query-row weights are discarded and the column is
stripped from features.
```

Codex's section-7 corrections applied here too: the opening no longer says "transform
body" (which contradicted A1 and `describe()`, both of which accept a whole function);
the fitted-state clause no longer drops `y_fit` (A1 had it, B1 did not); "called once"
is qualified; and `sample_weight` is described accurately — it feeds *both* the fit
weights and the eval-set weights of the early-stopping fit (`validate.py:232`, `:258`),
not just training.

### B2 — remove the `node_kind` default on new slots (line ~243)

```python
node_kind=(
    Literal["rowwise", "aggregate"],
    Field(
        ...,
        description=(
            "rowwise receives only df and computes each row independently. "
            "aggregate additionally receives the frozen fitting frame df_fit and its "
            "target y_fit, so it can fit state on the training rows and query it for "
            "every row."
        ),
    ),
),
```

`"rowwise"` as a default makes it the zero-effort choice in structured decoding: arm A
emitted 429 nodes and **zero** aggregates. Making the field required forces one explicit
token of choice; the description states what the choice buys. Same description on
`NodeEdits.node_kind`, which stays optional (absent = unchanged, which is correct there).

**Cost, which the draft understated.** It said "nothing omits it". Codex enumerated 22
call sites that do: new-slot constructions at `test_allowed_changes.py:52, 245, 254, 368,
377, 387, 397, 441, 463, 490, 517, 546, 581, 602, 624, 633, 672, 693, 717, 742, 763` (only
the aggregate fixture at `:825` supplies it) and the integration payload at
`test_structured_diff_integration.py:29`. There is no checked-in *production* payload that
omits it — the seed loader emits a node-less graph (`seed_loader.py:21`) and `baseline.json`
is persistence, guarded by the separate `FeatureNode.kind` default which stays. So B2 is a
deliberate **schema migration**, not a no-op: 22 fixtures to update, and any replayed
historical structured response will fail to parse.

### B3 — raise the mutation code cap to the genome's

`NodeEdits.code` and the new-slot `code` cap at `max_length=2000`; `FeatureNode.code`
allows 6000 (`graph.py:73`). Raise both to 6000. No stated justification for the
asymmetry, and it biases every generated node toward the one-liner end.

**Not free, contra the draft's "a ceiling is not a target".** Codex found the 2000 figure
is load-bearing in the completion budget, not just in the schema:

- `config/.../gemini3_flash.yaml:20` budgets twelve slots as `2000 code + 500 rationale`;
- `test_config.py:113` hardcodes that same arithmetic and would keep passing while proving
  the wrong bound;
- default mutation capacity is 12 nodes (`structured_diff_dag_tab.yaml:16`), so 12
  maximum-sized `code`+`rationale` fields is ~78k characters ≈ 19.5k tokens *before* JSON
  overhead, evidence fields, or reasoning;
- the Qwen budget test deliberately leaves only 8k non-reasoning tokens
  (`test_config.py:78`), sized for the old ceiling;
- retained parent code is rendered in full with no truncation (`allowed_changes.py:427`),
  so bigger genomes inflate the *input* prompt too, multiplied by parent count.

So B3 ships **with** the budget comment, `test_config.py:113`, and the Qwen bound updated.
If the recomputed budget does not fit, the resolution is a smaller raise (e.g. 4000), not
a silently wrong comment.

### B4 — ~~state the structural_intent depth rule in `describe()`~~ **dropped**

The draft adopted codex's earlier item 9 (add "a standalone fitted aggregate is
`local_edit`" to `describe()`). Codex's review of the plan then dropped it on inspection:
`describe()` **already** states that `extend_chain` must increase depth and `compose_chain`
must reach depth ≥ 2, and `allowed_changes.py:470` verifies it in Python. The sentence
would restate an existing fact. Expected effect ≈ zero; cut it.

The open question it was attached to survives and is still an **owner decision, not
defaulted on**: whether to demote the `extend_chain`/`compose_chain` hard-fail
(`allowed_changes.py:684`) to a logged relabel, on the grounds that `structural_intent` is
descriptive metadata and killing an otherwise-valid genome over a wrong label is punitive.
Default here remains codex's position: keep the check.

---

### B5 — `describe()` stops re-explaining the node ABI, and states what it alone knows

`describe()` (line ~462) is the prose that ships with the diff schema. Two changes.

**Delete** its restatement of the node ABI at line 494-497 — the `node_kind` field
descriptions (B2) and S1 now carry that, in one vocabulary. In particular delete
*"Never estimate from df"*: read literally it forbids every aggregate node, since an
aggregate node's whole job is computing outputs for the rows of `df`. What it was
reaching for — do not fit state from `df` — is already stated once, correctly, in S1.

Also amend the existing `input_cols` synchronization sentence, which after C1 is no
longer accurate: *"Python synchronizes input_cols from literal df/df_fit reads when every
missing column is raw or produced by an earlier slot... Unavailable or forward reads are
rejected."* becomes a statement that synchronization is best-effort and that an
undeclared column is simply absent at run time.

### B6 — one definition of `rationale`

`NodeEdits.rationale`/new-slot `rationale` cap at 500 with "at most 2 short plain-text
sentences"; `FeatureNode.rationale` caps at 1000 and defines the field as a counterfactual
hypothesis (what signal, why this operation, what is lost without it). Keep the tighter
500-char bound for generation, but use the genome's *definition* so the model is not
answering two different questions depending on which schema it is looking at.

### B7 — rename the slot discriminator (owner decision, not defaulted on)

The reason `node_kind` exists at all is that `kind` is taken by the slot discriminator
(`"keep" | "new"`). Renaming that discriminator to `slot_action` would let `kind` mean the
same thing in both directions and delete the `edits["kind"] = edits.pop("node_kind")`
remapping at `allowed_changes.py:580`.

Cost: it changes the response schema shape, so it touches `_repair_payload`, the compaction
path, and every diff fixture in `tests/dag_tab/`. Benefit is real but second-order next to
B1/B2. **Recommendation: defer**, and close the gap with the one-line B5 sentence for now.

---

## Surface S2 — the genome schema (`problems/dag_tab/graph.py`)

**Codex's position: drop S2 from this plan entirely** — on two grounds. First, it scored
G1/G2 as violating the owner's two-surface constraint. That ground is stale: the owner
subsequently named three components, the second of which is the graph structured output,
so S2 is in scope by instruction. Codex was reviewing against the older wording.

The second ground stands and is a fact I had only half-stated: **the model never sees
these descriptions, at all.** The mutation agent sends exactly `task_description`,
`allowed_changes.describe()`, the diff schema, and `render_parents()` output
(`structured_diff.py:59, :70`). `FeatureNode`'s field descriptions reach no prompt on any
path.

So G1's expected search effect is **zero**, and it is kept only for what it *is*: the
definitional source that S1 and S3 are checked against, and the anchor for the G2 guard.
It ships as documentation hygiene, sequenced last, and nothing in the acceptance gate
depends on it. If it costs a single review round it should be cut.

### G1 — `kind` and `code` descriptions defer to the ABI (zero search effect; hygiene only)

```python
kind: FeatureKind = Field(
    default="rowwise",
    description=(
        "Execution ABI. rowwise receives only df. aggregate additionally receives the "
        "frozen fitting frame df_fit and its target y_fit, and may query any "
        "deterministic state fitted from them."
    ),
)
```

and for `code`, drop "aggregate code learns only from df_fit and applies the learned
transform to df" in favour of the same sentence. `default="rowwise"` **stays** here — old
genomes omit the field and must keep deserializing. That is exactly why the generation-side
default (B2) has to go: it is a persistence concern that leaked into a generation schema.

### G2 — the guard test

One test in `tests/dag_tab/` asserting the synergy contract: the ABI clause constant is a
substring of `task_description.txt`, of both `node_kind` descriptions, and of
`FeatureNode.kind`'s; and that the mutation-side `code` bound is not tighter than
`FeatureNode.code`'s. Cheap, and it is the only thing that keeps seven copies from
re-diverging the next time someone edits one of them.

## Hardcoded-rule fixes

### C1 — `literal_frame_reads` stops raising (`execution.py:120-192`)

Delete four rejections and the whitelist that drives the fifth:

| rejected today | verdict |
|---|---|
| `x = df` → *"aliased frame reads cannot be synchronized; use .copy()"* | drop. `df` is already a private copy of the node's input slice. |
| `df_fit[cols]` where `cols` is a variable | drop. Falls back to "reads not provable". |
| `df.iloc[...]` → *"positional reads cannot be synchronized"* | drop. Positional access is how leave-one-out over the `df_fit` prefix is written; batch purity is enforced by the probe, exactly. |
| dynamic `.loc` | drop the raise; keep the `.loc[rows, literal_cols]` inference. |
| any attribute outside the 9-name `_FRAME_API_ATTRIBUTES` whitelist | delete the whitelist and the entire second `ast.walk` loop. It only raises; it contributes no reads. `.to_numpy()`, `.values`, `.apply()`, `.equals()`, `.merge()` all become legal. |

The function keeps its signature and its job: return the set of provably-read columns.
It simply returns a smaller set instead of raising when it cannot see through the code.
Docstring becomes *"Return the frame reads we can prove; unprovable access forms yield
no reads rather than an error."*

Consequence in `_transcribe`: `missing_declared_reads` is computed from a possibly
incomplete set, so a model that under-declares `input_cols` in unprovable code gets a
`FeatureExecutionError` at evaluation instead of a silent repair. That is the correct
failure — it is a real bug in the candidate, reported against the candidate.

### C2 — infer through single-assignment literal column lists

Codex's item 5, adopted. Extend `_literal_frame_columns` so a name bound once to a
literal list/tuple of strings is resolved like an inline literal. This restores exact
`input_cols` repair for `cols = ["x6", "x7"]; df_fit[cols]`, the single most common
spelling C1 would otherwise leave unprovable. Pure inference improvement; no rejection
path.

### C3 — `_extract_function_body` accepts helper functions and module-level setup

Today (`execution.py:34-46`), code containing *any* `def` must contain *only* imports and
that one `def transform`. A model that writes a helper, or a module-level constant next
to its `def transform`, loses the child with
*"code containing a function must contain only imports and def transform(...)"* — this
killed one of the three model-written kNN nodes outright.

**The draft's design was hoisting — refuted, and replaced.** It proposed emitting
`[other top-level statements] + [transform's body]`. Codex showed that is not
semantics-preserving, with two counterexamples:

```python
counter = 0
def transform(df):
    global counter          # hoisted: `counter = 0` lands *before* `global counter`
    counter += 1            # -> SyntaxError at compile time
```

```python
cache = {}
def helper(values):
    cache["calls"] = cache.get("calls", 0) + 1
    return values
def transform(df):
    df["fe"] = helper(df["x0"]); return df
```

As authored, `cache` is initialised once and shared. Hoisted, it becomes a local prelude
reset on every call — and rowwise transforms are called once per block, fit/validation/
query (`execution.py:412`), so the difference is observable. The same extractor also
serves target transforms (`execution.py:65`), where module state plus
`inverse`/`inverse_transform` has the identical defect.

**Redesign: stop extracting, and compile the module as written.** When the code contains
a `def` with an allowed name, `normalize_node_code` returns the module source unchanged
(after the existing exactly-one-allowed-def and no-decorator checks), and
`_compile_transform` execs that module in the node namespace and binds
`namespace["transform"]` instead of wrapping a body. The bare-body form keeps today's
wrap. Module-level state then means exactly what Python means by it: initialised once per
compile, therefore shared across the three row blocks of one graph execution and *not*
across executions — which is the honest semantics, and is what C6 below must also respect.

Cost, and why it is still worth doing: `validate_node_code`, `literal_frame_reads` and
`_wrapped_source` must all accept both stored forms rather than assuming a bare body. That
is more work than the draft implied. **If it does not fit the change budget, the fallback
is to keep rejecting module-level statements but replace the error text** with one that
says how to fix it ("move module-level setup inside transform"), since the unactionable
message is most of the harm. What must *not* ship is the hoisting.

Note for expectations: the model-written node this unblocks (gemini-3-flash #1) would
then die anyway — it branches on `df.equals(df_fit)`, which can never be true, so it
falls through to the no-self-exclusion path and is correctly rejected for own-target
leakage. C3 buys the *general* case, not that node.

### C5 — strengthen the own-target probe (from R2; blocking with C1)

Two changes to `assert_split_invariant`, both cheap:

- **Check every generated column**, not only `graph.estimator_columns` minus raw. An
  intermediate node with `is_output=false` can leak into a downstream output through a
  transform that masks the perturbation at the sampled row; checking the intermediate
  directly catches it at the source and names the guilty node.
- **Sample more fitting positions.** Three fixed positions is a token gesture once
  supervised aggregates are easy to write. Spread the sample across the fit block rather
  than pinning endpoints and midpoint, sized as a fraction of the probe frame so it scales
  with the data rather than a fixed count.

Each extra position costs one re-execution of the graph on the fit frame, so measure the
added validation latency before choosing the sample size — this sits on the hot path of
every evaluation. If it is material, prefer widening the column coverage (free) over
widening the position sample (not free).

This is the one place the plan makes a guard *stricter*. It is the correct trade for
making the expressive surface wider.

### C6 — `y_fit` is shared mutable state across nodes (pre-existing bug, blocking)

Found by codex, missed by this plan and by the earlier audit. Every aggregate node
receives **the same `y_fit` array object** (`execution.py:409`); `np.asarray` at
`execution.py:491` does not copy an array that is already an ndarray. `df_fit` is a fresh
`.copy()` per node; `y_fit` is not. So one aggregate node can mutate the targets in place
— `y_fit -= y_fit.mean()`, `y_fit.sort()`, `y_fit[mask] = 0` — and silently change what
every later node fits on, what the probes then compare against, and potentially the labels
downstream.

That is a science-boundary hole, not an ergonomics one, and it gets *more* reachable
under this plan, whose entire purpose is to make supervised fitted state routine. Fix is
one line at the call site — pass a copy per node, or set `writeable=False` on the array
handed to node code so an in-place write raises instead of corrupting silently. Prefer
read-only: it fails loudly and costs nothing. Add a test that mutating `y_fit` in node 1
cannot change node 2's output.

### C4 — regression tests

Codex's item 10, plus the C1/C3 spellings, plus the two negative-control classes its
review of this plan added:

- transcription round-trip for each spelling C1 unblocks (`.to_numpy()`, `.values`,
  variable column list, `.iloc`, aliasing) — each must transcribe *and* evaluate;
- **deliberate replacement, not addition**: `test_allowed_changes.py:562-593` currently
  asserts transcription *raises* for aliasing and for `.iloc`. Those two tests invert
  under C1 and must be rewritten to assert best-effort inference, with the change called
  out in the PR description — silently deleting an assertion that a rejection fires is
  exactly how a guard rots;
- **silent-fallback controls (from R1)**: `df.get("x1", 0)`, `df.reindex(columns=["x1"],
  fill_value=0)`, `df.to_numpy().sum(axis=1)` and `df.filter(like="x")` under a narrow
  `input_cols` must be pinned to their *actual* behaviour, so the day someone tries to
  turn them into an error, the test says what changed;
- module-form normalization: a helper `def` and a module-level constant must round-trip
  with module semantics intact — including the `global` counterexample, which must compile;
- a fitted-neighbour aggregate with positional self-exclusion, asserted through
  transcription → static validation → import → batch-purity → own-target probe, on a
  frame containing duplicate coordinates;
- `y_fit` immutability across nodes (C6);
- **positive controls that the semantic guards did not move**: a supervised aggregate
  without self-exclusion must still be rejected for own-target leakage, and a
  query-batch-dependent feature must still be rejected for split dependence.

---

## What this plan still does not unlock

Codex was asked the most valuable question directly — *after these fixes, what would a
professional feature engineer still be unable to do?* Its answer, verified against the
code, is that the plan closes the single-node kNN gap but not the "whole machine" claim.
Summarised verdict: **kNN in one aggregate node becomes expressible; a reusable fitted
preprocessing pipeline still does not.** None of these are in scope for this change; they
are named so the plan does not overclaim.

| # | still blocked | mechanism |
|---|---|---|
| 1 | **Cross-node fitted-state reuse.** A fitted estimator, neighbour index, vocabulary, or covariance factorisation cannot be passed to a later node. | Each node compiles into a fresh namespace and receives fresh frame copies (`execution.py:398`); only declared *output columns* transfer (`:467`). The only workaround is a multi-output node that fits once and emits every derived column — and `is_output` is node-wide (`graph.py:210`), so there is no per-output export choice. |
| 2 | **Validation-aware feature fitting.** No early stopping or hyperparameter selection inside a learned feature. | Search execution puts `X_val` inside `df` but exposes no validation boundary and no `y_val`; only the fit prefix is identified. Correct for leakage, but asymmetric: the fixed CatBoost *does* get validation labels. If this is intentional, the ABI should say aggregate fitting is training-only including model selection — the A1 text above now does. |
| 3 | **Target-derived row weights.** Class weights or target-dependent robust weights. | `sample_weight` is in `estimator_columns` (`graph.py:221`), so the own-target probe treats it as a feature; any weight that legitimately moves with the row's own label is rejected. The schema advertises `sample_weight` without stating this. |
| 4 | **Persistent state across graph executions.** | Nothing carries over between executions; C3's module-form compile must not be read as implying it. Multiple passes, cross-fitting and iteration *within* one aggregate call are all fine. |
| 5 | **Predictable categorical handling.** | Generated categoricals are limited to str/int/bool (`execution.py:349`); CatBoost prep fits the vocabulary on fitting rows and rewrites unseen values to `__UNKNOWN__` (`validate.py:170`). Neither ABI clause states this, and it changes how a professional would encode. |
| 6 | **A comfortable shape for large-pipeline edits.** | The diff defaults to 12 slots while the genome permits 16 nodes; every mutation re-emits the whole child and omission means deletion. Arbitrary DAGs are representable, but retaining/reordering a big pipeline is error-prone. This is the same positional-slot schema whose *size* already breaks Gemini's `responseSchema` limit above ~8 nodes; the durable fix (flatten to a single array) would address both, and is out of scope here. |

## Deliberately not done

- **No feature families named anywhere.** Codex's remediation item 2 ("put neighbour
  features in the enumerated search menu") is rejected — it is the opposite of the
  brief. The menu is being deleted, not extended.
- **No dataset STRATEGY injection.** Codex found that
  `problems/tabular/california/task_description.txt:34` names kNN in a `STRATEGY`
  section that `DagTabProblemContext` never selects (it takes `TASK`, `DATASET`,
  `COLUMNS` only). Leave it stripped. Injecting it would hand the model a
  dataset-specific answer key and would make any subsequent gain unattributable to the
  framework. The fix has to be capability-general or it is not a fix.
- **No weakening of the behavioural probes**, the runtime `input_cols` slicing, or
  `validate_node_code`. Nothing that protects the science gets looser; C5 makes the
  own-target probe *stricter*, and C4 adds positive controls proving the semantic
  rejections still fire.

## Verification

1. `/run-tests tests/dag_tab/` — must stay green, plus the C4 additions and the G2 guard.
   The guard is the one that keeps this fix from decaying: seven copies of the ABI drifted
   apart once already, and nothing in CI noticed.
2. **Replay gate.** The seven candidate nodes already collected in
   `scratchpad/knn_probe/` (four hand-written, three model-written verbatim) re-run
   through the new gates. Expected, precisely: the `cols`-variable death becomes a pass
   (C2); the module-form death stops dying at *normalization* (C3) and then dies at
   own-target leakage instead, because it branches on `df.equals(df_fit)` which is never
   true; and the existing own-target-leakage death **must remain a death**. Any other
   movement is a bug in this change.
3. **A/B on california** — the acceptance gate, below.

## Acceptance criterion

Set by the owner: **after the fixes, the search designs graphs with kNN and beats the
previous champions.** Made falsifiable:

### The bar

| reference | CV R² | role |
|---|---|---|
| neutral seed | 0.848628 | floor |
| arm A best (100 mutations) | 0.857602 | previous champion, gemini-3-flash |
| arm B best (100 mutations) | 0.862133 | previous champion, gemini-3.5-flash |
| 2026-07-16 reference run | **0.864554** | **best genome any dag_tab search has ever produced — this is the bar** |
| seed + one hand-written kNN node | 0.865573 | oracle: what one node of the missing family is worth |

### Pass conditions

**Primary — must hold, or the fix has not worked:**

1. In **≥ 2 of 3 seeds**, the champion genome contains a *neighbour-structured aggregate
   node* that is actually on the scoring path (`is_output=true`, or consumed by a node
   that is).
2. **Best-of-3 CV R² > 0.864554**, strictly, under the existing tabular evaluation
   protocol unchanged — same splits, same CatBoost, same CV.

**Secondary — the search is doing the professional's job, not stumbling into it:**

3. **Mean-of-3 > 0.862133** (the better previous champion), so the result is not one lucky
   seed.
4. **Best-of-3 ≥ 0.865573** — the search reaches what a single hand-written node reaches.
   Below this, the family was found but implemented badly (wrong k, wrong feature subspace,
   leaky or over-smoothed LOO), which is an iteration-budget question, not a contract one.

### "kNN" defined so it cannot be gamed

A node counts as neighbour-structured if it builds a per-row neighbour set over `df_fit`
and derives its output from that set — detected as either an import from
`sklearn.neighbors` / `scipy.spatial`, or an explicit distance/`argsort`/`searchsorted`
construction over fit-frame columns — **and confirmed by reading the node**. At the volume
involved (a handful of champion nodes) this is a manual read, not a regex verdict. A node
that merely names a variable `knn` does not count; a hand-rolled band or ball query does.

Nothing in S1, S2 or S3 will name kNN, neighbours, distances, or any other feature family,
so anything found is the model's own choice — that is what makes this criterion meaningful
rather than an instruction-following test.

### Design

Primary model **gemini-3.5-flash, reasoning high** — arm B produced all 14 aggregate
nodes and the better champion, and its own kNN node passed every gate, so it is the
configuration with the least excuse. 3 seeds, 100 mutations, everything else mirroring the
shakedown CLI verbatim. Pre-launch: verify `gigaevo.__file__` and the config echo, fresh
output root, `OMP/MKL/OPENBLAS_NUM_THREADS=8`, run dirs on local disk, `service_tier: flex`.
Fitness read with `gigaevo top`, never scraped from logs.

**Recommended: 3 control seeds on unmodified `main` at the same seeds and model** (6 runs
total). The gate above does not strictly need them — the bar is historical — but without a
control, a pass cannot be attributed to this change rather than to seed luck, and a failure
cannot be told apart from "california is saturated near 0.865". Cuttable to 2+2 on budget.

### Diagnostics reported either way

Share of nodes with `kind="aggregate"`; share of mutations dying at transcription;
first-attempt success rate; per-seed best and mean ± std. These are what distinguish the
failure modes below, and they cost nothing extra.

### If the gate fails

The ladder, in order — and note that **re-adding a feature menu is not on it**, since that
converts the criterion into an instruction-following test and forfeits the finding:

1. **Aggregate share still near zero.** The contract is no longer the constraint; the
   proposal distribution is. Recall that 239 mutation prompts contained zero mentions of
   any neighbour concept — the analyst upstream never puts it on the table. Lever: mutation
   operator / suggester diversity.
2. **Aggregates up, neighbour nodes present, fitness flat.** Compare against the 0.865573
   oracle: if evolved neighbour nodes exist but score below it, the family was found and
   implemented poorly — lever is iteration budget or a stronger reasoning model, not the
   contract.
3. **Aggregates up, fitness up, but under 0.864554.** Partial credit; report as such and
   do not round it up to a pass.

The honest prior: this plan removes the barriers and states the capability, but nothing in
it *makes* the model reach for fitted structure. Outcome 1 is a live possibility and would
be a real finding — that the contract was never the binding constraint — rather than a
failure to be papered over.

## Implementation order

Ranked by expected effect against breakage risk, merging codex's section-9 ranking with
the blocking dependencies established above.

| order | item | effect / risk | note |
|---|---|---|---|
| 1 | **R1 clause** on S1 and B1 | — | **blocking prerequisite for C1**; ship in the same commit or C1 introduces a silent-wrong-answer mode |
| 2 | A1 + B1 (corrected wording) | very high / low | the core capability communication |
| 3 | C5 + C6 | none / low, guard-strengthening | ship *before* the expressive changes land, not after |
| 4 | B2 required `node_kind` | high / low–moderate | + 22 fixtures |
| 5 | C2 literal-list inference | med-high / low | must be scope-aware: respect function scopes and reassignment |
| 6 | C1 best-effort reads | high / moderate | needs 1, 3, and the C4 replacements |
| 7 | A2 + B5 (corrected `a1`/`b1`) | medium / low | |
| 8 | A3 menu deletion | uncertain positive / very low | binding owner decision |
| 9 | B3 6000-char cap | medium / moderate | only with the budget comment + `test_config.py` updated |
| 10 | B6 rationale alignment | low / low | |
| 11 | C3 module compiler | medium / high | drop to the error-message fallback if the budget is tight |
| 12 | G1 + G2 | zero search effect / low | hygiene; cut on any review friction |
| — | B4 | dropped | already stated by `describe()` |
| — | B7 | deferred | schema-shape change; B5's sentence covers the gap |

## Risk register

| risk | mitigation |
|---|---|
| C1 lets an under-declared node through to evaluation | For *literal* reads it fails there with an exact error. For whole-frame and `.get`/`reindex` spellings it does **not** — R1, confirmed by codex with four counterexamples. Mitigated only by publishing the `input_cols` slice on S1 and B1, which is why that clause is blocking, plus the C4 silent-fallback controls. |
| ~~C3's statement hoisting changes semantics of existing genomes~~ | Withdrawn. The draft argued no such genomes exist so hoisting was safe. Codex refuted the *design*, not the exposure: hoisting breaks `global` (SyntaxError) and resets module state that Python would share. C3 is redesigned as a module compiler; the risk is now implementation surface in three validators, with a stated fallback. |
| B2 makes `node_kind` required, changing the response schema | Requiredness does not change schema *size*, which is the known Gemini `responseSchema` failure mode. But it *is* a migration: 22 fixtures, and replayed historical responses that omit the field will no longer parse. |
| B3's 6000-char cap inflates prompts | Not free — it invalidates a completion-budget comment and two config tests, and inflates input prompts via untruncated parent rendering. Ships only with the budget recomputed; fall back to a smaller raise if it does not fit. |
| Guards look stricter on paper than they are | They are **probes**: one fixed batch subset, three fitting positions, estimator columns only. C5 widens both; the A1/B1 text no longer claims "enforced". |
| A later node silently corrupts `y_fit` for earlier-fitted state | C6 — pre-existing, unrelated to this plan's edits, fixed here because the plan makes it reachable. |
| More expressive nodes are slower to evaluate | Existing per-evaluation timeouts unchanged; C5's extra probe positions are on the hot path and are sized after measuring. |
```
