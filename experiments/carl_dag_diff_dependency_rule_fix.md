# Grammar-enforcing "dependencies reference earlier slots" (probed design)

Status: DESIGN VALIDATED BY PROBE 2026-07-02 — implementation waits for the full100 runs to
finish (no import changes mid-run). User constraint: the rule must live in the schema /
structured output, not in a post-hoc retry or validator-only check.
Context: experiments/carl_dag_diff_mutation_design.md §4.2, gigaevo/chains/dag_changes.py,
probe scripts probe_diff_gemini10..13.py (session scratchpad).

## Problem

In the shipped E3 flat encoding, `steps` is a uniform array of `anyOf:[keep,new]` slots and
every slot shares one dependency enum `slot_1..slot_7`. The DAG rule — slot k may only
reference slots 1..k-1 — lives in a pydantic `model_validator`, so the grammar accepts
payloads the validator then rejects (`diff_schema_error`, ~5% of attempts). All observed
violations are the degenerate case: slot 1 given `['slot_1']` (2/2 in armB_full100, plus the
smoke rejections). A uniform-`items` array fundamentally cannot carry position-dependent
constraints in the portable schema subset; the only portable position-dependent construct is
**object properties**.

## The fix: fixed-key object encoding, single model

Replace `steps: list[slot]` with per-position properties, each with its OWN schema:

```
{"reasoning": str,
 "base_parent": enum["A","B"],
 "slot_1": Keep1 | New1,            # NO dependencies field at all
 "slot_2": Keep2 | New2 | null,     # dependencies enum = ["slot_1"]
 ...
 "slot_8": Keep8 | New8 | null}     # dependencies enum = slot_1..slot_7
```

Self-deps and forward-deps become **unrepresentable** — grammar-enforced, exactly what the
current failure class violates. `min_steps` = first `min` slots non-null.

**Crucial probe finding — no per-parent branching.** The direct port (one branch per parent,
discriminated by base_parent, as E3 does) blows Gemini's grammar-compilation limit. Instead:
ONE model, `base_parent` a plain enum field, and keep-ids in a single global enum (ids are
already parent-namespaced: `a1..`, `b1..`). Consequence: the grammar no longer ties keep-ids
to base_parent — keeps may reference ANY parent's steps. Two ways to read that:

- **Liberalize (recommended)**: define keeps-from-any-parent as legal (free crossover);
  `base_parent` becomes lineage/credit attribution ("the parent you take the most from").
  No rule left to violate.
- Conservative: keep the "keep only from base_parent" rule as a validator — but that
  reintroduces a validator-only rule, against the point of this change.

## Probe evidence (gemini-3.5-flash via OpenRouter, 2026-07-02)

| probe | encoding | size | result |
|---|---|---|---|
| 10 | object, 2-parent branches, `disc-union \| None` (nested unions) | 27.0KB | **400** |
| 11 | object, 2-parent branches, flat `anyOf[keep,new,null]` | 26.8KB | **400** |
| 12 | branched: 1 parent × {2,3,4,6,8} slots; 2 parents × 4 slots; non-null variants | 3.3–13.3KB | all PASS |
| 12 | branched: 2 parents × 8 slots (nullable or not) | ~26.7KB | **400** |
| 13 | branched: 2 parents × {6,7} slots | 19.9 / 23.3KB | PASS (cliff is 7→8) |
| 13 | **single-model, 2 parents, 8 slots** | **13.4KB** | **PASS, 4/4 e2e** |

- The limit is construct/union count, not bytes (padded 120KB simple schema passes; 26.7KB
  with 17 object-unions fails). Single-model has ~2× headroom below the cliff.
- E2E calls returned correct contiguous fills and valid wiring; the trap prompt ("make the
  FIRST step depend on the raw task input") — the exact observed live failure — produced a
  clean slot_1 with no dependencies, because the grammar offers none.

## Residual (validator-tripwire only, expected ≈0)

Two shapes stay expressible and keep a validator as tripwire, not as the enforcement layer:

- **Dangling ref to a nulled slot** (slot_5 references slot_3 = null): requires the model to
  null a slot AND cite it. 0/4 in probes. Note the current array encoding cannot express
  this at all — it is the (small) price of grammar-enforced ordering.
- **Non-contiguous fill** (slot_3 set, slot_2 null): can simply be defined legal — child =
  filled slots in index order (deps still resolve; deterministic semantics, no rewriting of
  the payload). 0/4 in probes; describe() instructs consecutive fill.

Rejected alternatives: relative back-refs (`back_k`) shift the failure to underflow and force
offset arithmetic; per-parent branching at max_steps=7 sits on the cliff and caps chains;
retry-with-error-feedback (user: no post-hoc fixes); clamping/total-reinterpretation of
invalid deps (vetoed auto-repair class); E1 prefixItems / E2 $ref recursion (Gemini rejects).

## Implementation sketch (post-run; new arm, not a patch of live arm B)

All contained in `gigaevo/chains/dag_changes.py` + its tests; wire format changes, so this is
**arm C** for the next run (or the replacement encoding if arm B's results justify adoption):

- `_diff_model` → single `create_model` with slot_1..slot_max fields as above (per-slot
  Keep/New models with position-narrowed dep enums; slot_1 without the field).
- `_deps_reference_earlier_slots` validator DELETED; replace with a dangling-null-ref check.
- `_transcribe` iterates slot fields instead of the list; skips nulls; base = majority-source
  parent unless the conservative rule is kept.
- `describe()` per probe 13 wording; `render_parents` unchanged.
- Schema still emitted through `portable_json_schema`; the portable-subset guard test keeps
  holding; add a schema test asserting slot_k's dep enum is exactly slot_1..slot_{k-1} and
  slot_1 has no dependencies property.

## Predictions

| metric | E3 (now) | object encoding |
|---|---|---|
| self/forward dep violations | ~5% of attempts | 0 (unrepresentable) |
| dangling-null / contiguity rejections | n/a | <1% (0/4 probed) |
| schema size | 8.2KB | 13.4KB (cliff ~27KB) |
| token overhead | — | +null/omitted trailing slots (small) |
