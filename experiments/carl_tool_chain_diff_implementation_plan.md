# CARL tool-aware DAG-diff — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or
> subagent-driven-development) to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `AllowedToolChainChanges`, a positional-slot DAG-diff `AllowedChanges`
impl for the `problems/chains` `RawChainSpec` genome (LLM **and** tool steps), so
`StructuredDiffMutationOperator` can mutate HoVer multi-hop retrieval chains.

**Architecture:** A new self-contained module `problems/chains/tool_chain_diff.py`
implements the four `AllowedChanges` methods against `RawChainSpec`. Each slot is a
three-form union — `keep` (reuse an LLM step by id + edits), `new_llm`, `new_tool`
(a `tool_name` from `available_tools` + one `query_source`). The transcriber emits
**absolute** `$history[N]` from the renumbered query-source position, so reordering
can never mis-wire a retrieve. Neither `dag_changes.py` nor the operator changes.

**Tech stack:** Python (pydantic v2 `create_model` guided-decoding schemas,
`portable_json_schema`), Hydra `_target_` config, pytest.

**Design doc:** `experiments/carl_tool_chain_diff_design.md`.

## Global Constraints

- Python / pytest: `/home/jovyan/.mlspace/envs/evo/bin/python3` (`$GIGAEVO_PYTHON`).
  Ruff: `/home/jovyan/.mlspace/envs/evo/bin/ruff`.
- **Tests via `/run-tests` skill**, never raw `pytest tests/`. Lint gate:
  `ruff check . && ruff format --check .`.
- **Commits await explicit user approval** — implement and leave uncommitted; the
  commit steps below are the intended boundaries, not permission to commit.
- No cache-version salts / `compute_hash` overrides. Structured output only —
  never regex-scrub. No new exceptions/enums (`MutationError` already covers all
  failure paths). Zero prose comments unless a one-line WHY is non-obvious. Match
  the style of `gigaevo/chains/dag_changes.py` and `tests/chains/test_dag_changes.py`.
- The class touches **no existing file** (parity for the live summarizer A/B is
  automatic); only new files + one new config.

## File Structure

- Create `problems/chains/tool_chain_diff.py` — `AllowedToolChainChanges` + local
  helpers (`_slots_contiguous`, `StepEdits`, id map, query translation).
- Create `tests/chains/test_tool_chain_diff.py` — schema/parse/render/apply tests,
  mirroring `tests/chains/test_dag_changes.py`.
- Create `config/mutation/structured_diff_hover.yaml` — wires the operator to
  `AllowedToolChainChanges` for HoVer `full7`.

Consumed from existing code (imports, unchanged):
`gigaevo.evolution.mutation.allowed_changes.{AllowedChanges,DiffSchema,DiffStructuredOutputBase}`,
`gigaevo.llm.schema_compat.portable_json_schema`, `gigaevo.exceptions.MutationError`,
`problems.chains.types.{RawChainSpec,LLMStep,ToolStep}`,
`problems.chains.chain_validation.validate_chain_spec` (tests only),
`problems.chains.chain_runner._resolve_reference` (tests only),
`problems.chains.hover.full7.config.{load_baseline,FULL_CHAIN_CONFIG}` (tests/config).

---

### Task 1: Parse + render (tool-aware, no LLM-only rejection)

**Files:**
- Create: `problems/chains/tool_chain_diff.py`
- Test: `tests/chains/test_tool_chain_diff.py`

**Interfaces:**
- Produces: `AllowedToolChainChanges(*, min_steps=1, max_steps, available_tools,
  outer_context_token="$outer_context")`; methods `_parse(parents) -> dict[str,
  RawChainSpec]`, `render_parents(parents) -> str`, `_llm_id_map(ns, spec) ->
  dict[str, LLMStep]`.

- [ ] **Step 1: Write the failing test** (`tests/chains/test_tool_chain_diff.py`)

```python
"""Tests for AllowedToolChainChanges: schema-valid diffs -> valid RawChainSpec chains."""

from __future__ import annotations

import json

import pytest

from problems.chains.hover.full7.config import FULL_CHAIN_CONFIG, load_baseline
from problems.chains.tool_chain_diff import AllowedToolChainChanges

TOOLS = FULL_CHAIN_CONFIG["available_tools"]


@pytest.fixture
def hover_parent() -> dict[str, str]:
    return {"A": json.dumps(load_baseline())}


@pytest.fixture
def changes() -> AllowedToolChainChanges:
    return AllowedToolChainChanges(max_steps=7, available_tools=TOOLS)


def test_parse_accepts_tool_steps(changes, hover_parent):
    specs = changes._parse(hover_parent)
    assert len(specs["A"].steps) == 7


def test_render_lists_llm_ids_and_tool_sources(changes, hover_parent):
    rendered = changes.render_parents(hover_parent)
    assert "a1" in rendered  # first llm step gets a keepable id
    assert "retrieve" in rendered
    assert "query=outer_context" in rendered
```

- [ ] **Step 2: Run to verify it fails** — `/run-tests tests/chains/test_tool_chain_diff.py`
  Expected: `ModuleNotFoundError: problems.chains.tool_chain_diff`.

- [ ] **Step 3: Implement module skeleton + `_parse` + `render_parents`**

```python
"""Tool-aware positional-slot DAG-diff for problems/chains RawChainSpec genomes.

Extends the LLM-only positional-slot pattern (gigaevo/chains/dag_changes.py) to
chains whose genome is RawChainSpec — {system_prompt, steps:[LLMStep | ToolStep]}
— so retrieval steps are first-class. Each slot is keep (reuse an LLM step by id
+ edits), new_llm, or new_tool (tool_name from available_tools + one query
source). Tool query wiring is emitted as absolute $history[N] from the renumbered
source position, so a reordering diff can never point a retrieve at the wrong
upstream output. Design: experiments/carl_tool_chain_diff_design.md.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    create_model,
    model_validator,
)

from gigaevo.evolution.mutation.allowed_changes import (
    AllowedChanges,
    DiffSchema,
    DiffStructuredOutputBase,
)
from gigaevo.exceptions import MutationError
from gigaevo.llm.schema_compat import portable_json_schema
from problems.chains.types import LLMStep, RawChainSpec, ToolStep

_LLM_EDIT_FIELDS = ("title", "aim", "stage_action", "reasoning_questions")

# aim/stage_action must stay non-empty or RawChainSpec's LLMStep rejects the chain;
# min_length pushes that invariant into the schema so it is unrepresentable-to-break
_EDIT_FIELD_DEFS: dict[str, Any] = {
    name: (
        str | None,
        Field(default=None, min_length=1)
        if name in ("title", "aim", "stage_action")
        else Field(default=None),
    )
    for name in _LLM_EDIT_FIELDS
}
StepEdits = create_model(
    "ToolChainStepEdits", __config__=ConfigDict(extra="forbid"), **_EDIT_FIELD_DEFS
)


class ToolChainDiffBase(DiffStructuredOutputBase):
    """Static shape of the per-call diff model; _diff_model narrows the enums."""


def _slots_contiguous(diff: BaseModel) -> BaseModel:
    empty = None
    for name in type(diff).model_fields:
        if not name.startswith("slot_"):
            continue
        if getattr(diff, name) is None:
            empty = name
        elif empty is not None:
            raise ValueError(
                f"{name} is filled after empty {empty}; fill slots consecutively from slot_1"
            )
    return diff


def _query_source_text(step: ToolStep) -> str:
    ref = step.step_config.input_mapping.get("query", "")
    if ref == "$outer_context":
        return "outer_context"
    if ref == "$history[-1]":
        return "output of the preceding step"
    if ref.startswith("$history[") and ref.endswith("]"):
        idx = ref[len("$history[") : -1]
        if idx.lstrip("-").isdigit() and not idx.startswith("-"):
            return f"output of step {int(idx) + 1}"
    return ref


class AllowedToolChainChanges(AllowedChanges):
    def __init__(
        self,
        *,
        min_steps: int = 1,
        max_steps: int,
        available_tools: list[str],
        outer_context_token: str = "$outer_context",
    ):
        if not 1 <= min_steps <= max_steps:
            raise ValueError(f"invalid step bounds: min={min_steps} max={max_steps}")
        if not available_tools:
            raise ValueError("available_tools must be non-empty")
        self.min_steps = min_steps
        self.max_steps = max_steps
        self.available_tools = list(available_tools)
        self.outer_context_token = outer_context_token

    def _parse(self, parents: dict[str, str]) -> dict[str, RawChainSpec]:
        if not parents:
            raise MutationError("carl_validation_error: no parents provided")
        specs: dict[str, RawChainSpec] = {}
        for ns, code in parents.items():
            try:
                specs[ns] = RawChainSpec.model_validate_json(code)
            except Exception as e:
                raise MutationError(
                    f"carl_validation_error: parent {ns}: {e}"
                ) from e
        return specs

    def _llm_id_map(self, ns: str, spec: RawChainSpec) -> dict[str, LLMStep]:
        out: dict[str, LLMStep] = {}
        for step in spec.steps:
            if isinstance(step, LLMStep):
                out[f"{ns.lower()}{len(out) + 1}"] = step
        return out

    def render_parents(self, parents: dict[str, str]) -> str:
        specs = self._parse(parents)
        blocks = []
        for ns, spec in specs.items():
            lines = [f"=== Parent {ns} ==="]
            if spec.system_prompt:
                lines.append(f"system_prompt: {spec.system_prompt}")
            sid_by_number = {
                step.number: sid
                for sid, step in self._llm_id_map(ns, spec).items()
            }
            for step in sorted(spec.steps, key=lambda s: s.number):
                deps = [sid_by_number.get(d, str(d)) for d in step.dependencies]
                if isinstance(step, LLMStep):
                    sid = sid_by_number[step.number]
                    lines.append(f"{sid} | deps={deps or '[]'} | title: {step.title}")
                    for field in ("aim", "stage_action", "reasoning_questions"):
                        value = getattr(step, field, "")
                        if value:
                            lines.append(f"    {field}: {value}")
                else:
                    lines.append(
                        f"[tool step, reproduce via new_tool] "
                        f"tool={step.step_config.tool_name} "
                        f"query={_query_source_text(step)}"
                    )
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)
```

- [ ] **Step 4: Run tests to verify parse/render pass** —
  `/run-tests tests/chains/test_tool_chain_diff.py` — Expected: 3 passed
  (`build_schema`/`apply`/`describe` still abstract-unimplemented → those come
  next; if pytest errors on abstract-method instantiation, keep only the two
  render/parse tests until Task 2 lands `build_schema`, or stub the three methods
  to `raise NotImplementedError`). Add the stubs in Step 3 if needed:

```python
    def build_schema(self, parents: dict[str, str]) -> DiffSchema:
        raise NotImplementedError

    def apply(self, diff: Any, parents: dict[str, str]) -> str:
        raise NotImplementedError

    def describe(self) -> str:
        raise NotImplementedError
```

- [ ] **Step 5: Commit (await approval)** — `problems/chains/tool_chain_diff.py`,
  `tests/chains/test_tool_chain_diff.py`.

---

### Task 2: `build_schema` / `_diff_model` (three slot forms) + `describe`

**Files:**
- Modify: `problems/chains/tool_chain_diff.py`
- Test: `tests/chains/test_tool_chain_diff.py`

**Interfaces:**
- Consumes: `_parse`, `_llm_id_map` (Task 1).
- Produces: `build_schema(parents) -> DiffSchema`; `describe() -> str`. Slot union
  branch order per position: `keep` (only if any LLM ids), `new_llm`, `new_tool`.

- [ ] **Step 1: Write failing tests**

```python
from gigaevo.llm.schema_compat import nonportable_keys

EVIDENCE = {"archetype": "Guided Innovation", "justification": "act on insight 1"}


def _object_branches(prop: dict) -> list[dict]:
    return [b for b in prop.get("anyOf", [prop]) if b.get("type") == "object"]


def test_emitted_schema_is_portable(changes, hover_parent):
    assert nonportable_keys(changes.build_schema(hover_parent).json_schema) == set()


def test_slot_has_three_forms_and_narrowed_enums(changes, hover_parent):
    schema = changes.build_schema(hover_parent).json_schema
    for k in range(1, changes.max_steps + 1):
        branches = _object_branches(schema["properties"][f"slot_{k}"])
        kinds = {b["properties"]["kind"]["enum"][0] for b in branches}
        assert kinds == {"keep", "new_llm", "new_tool"}
        tool = next(b for b in branches if b["properties"]["kind"]["enum"][0] == "new_tool")
        assert set(tool["properties"]["tool_name"]["enum"]) == set(TOOLS)
        qsrc = set(tool["properties"]["query_source"]["enum"])
        assert qsrc == {"outer_context", *[f"slot_{j}" for j in range(1, k)]}


def test_describe_mentions_tool_wiring(changes):
    text = changes.describe().lower()
    assert "new_tool" in text
    assert "query_source" in text
    assert "retrieve" in text  # available_tools listed


def test_schema_validates_a_tool_slot(changes, hover_parent):
    schema = changes.build_schema(hover_parent)
    schema.validate(
        {
            **EVIDENCE,
            "base_parent": "A",
            "slot_1": {"kind": "new_tool", "tool_name": "retrieve", "query_source": "outer_context"},
        }
    )
```

- [ ] **Step 2: Run to verify failure** — `NotImplementedError` on `build_schema`.

- [ ] **Step 3: Implement `_slot_forms`, `_diff_model`, `build_schema`, `describe`**

```python
    def _slot_forms(self, k: int, all_ids: tuple[str, ...]) -> list[type]:
        dep_field: dict[str, Any] = {}
        qsrc = ["outer_context"]
        if k > 1:
            dep_ref: Any = Literal[tuple(f"slot_{j}" for j in range(1, k))]
            dep_field = {
                "dependencies": (
                    list[dep_ref],  # type: ignore[valid-type]
                    Field(default_factory=list, max_length=k - 1),
                )
            }
            qsrc += [f"slot_{j}" for j in range(1, k)]
        forms: list[type] = []
        if all_ids:
            forms.append(
                create_model(
                    f"Keep{k}",
                    __config__=ConfigDict(extra="forbid"),
                    kind=(Literal["keep"], ...),
                    id=(Literal[all_ids], ...),
                    edits=(StepEdits, Field(default_factory=StepEdits)),
                    **dep_field,
                )
            )
        forms.append(
            create_model(
                f"NewLlm{k}",
                __config__=ConfigDict(extra="forbid"),
                kind=(Literal["new_llm"], ...),
                title=(str, Field(..., min_length=1)),
                aim=(str, Field(..., min_length=1)),
                stage_action=(str, Field(..., min_length=1)),
                reasoning_questions=(str, ""),
                **dep_field,
            )
        )
        forms.append(
            create_model(
                f"NewTool{k}",
                __config__=ConfigDict(extra="forbid"),
                kind=(Literal["new_tool"], ...),
                tool_name=(Literal[tuple(self.available_tools)], ...),
                query_source=(Literal[tuple(qsrc)], ...),
            )
        )
        return forms

    def _diff_model(
        self, specs: dict[str, RawChainSpec]
    ) -> type[ToolChainDiffBase]:
        all_ids = tuple(
            sid for ns, spec in specs.items() for sid in self._llm_id_map(ns, spec)
        )
        slot_fields: dict[str, Any] = {}
        for k in range(1, self.max_steps + 1):
            union: Any = self._slot_forms(k, all_ids)[0]
            for form in self._slot_forms(k, all_ids)[1:]:
                union = union | form
            if k <= self.min_steps:
                slot_fields[f"slot_{k}"] = (union, ...)
            else:
                slot_fields[f"slot_{k}"] = (union | None, None)
        return create_model(
            "ToolChainDiff",
            __base__=ToolChainDiffBase,
            base_parent=(Literal[tuple(specs)], ...),
            **slot_fields,
            __validators__={
                "check_contiguous": model_validator(mode="after")(_slots_contiguous)  # type: ignore[dict-item]
            },
        )

    def build_schema(self, parents: dict[str, str]) -> DiffSchema:
        specs = self._parse(parents)
        adapter = TypeAdapter(self._diff_model(specs))
        schema = portable_json_schema(
            {**adapter.json_schema(), "title": "tool_chain_diff"}
        )
        return DiffSchema(json_schema=schema, validate=adapter.validate_python)

    def describe(self) -> str:
        tools = ", ".join(self.available_tools)
        return (
            "POSITIONAL-SLOT CHAIN DIFF (LLM + tool steps)\n"
            f"- The child chain is slot_1..slot_{self.max_steps}, filled consecutively: "
            f"use {self.min_steps}..{self.max_steps} steps and set every unused trailing "
            "slot to null (no gaps). slot_1 is required.\n"
            "- base_parent = the parent whose lineage this child continues.\n"
            "- Slot forms: keep = reuse a rendered LLM step by id (parent-prefixed) with "
            "optional 'edits'; new_llm = a fresh LLM step with title/aim/stage_action/"
            "reasoning_questions; new_tool = a retrieval step choosing tool_name from "
            f"[{tools}] and one query_source.\n"
            "- Tool steps are re-expressed via new_tool (not kept by id): a tool step is "
            "fully defined by its tool_name and query_source, so nothing is lost.\n"
            "- query_source is 'outer_context' (the raw task input) or an EARLIER slot "
            "whose output becomes the retrieval query; the schema offers only earlier "
            "slots, so wiring is always backward and reorder-safe.\n"
            "- For LLM steps, 'dependencies' lists the earlier slots whose outputs feed "
            "the step; slot_1 takes none. Any base step you omit is deleted."
        )
```

- [ ] **Step 4: Run tests** — `/run-tests tests/chains/test_tool_chain_diff.py`
  Expected: all Task-1 + Task-2 tests pass.

- [ ] **Step 5: Commit (await approval)** — same two files.

---

### Task 3: `apply` / `_transcribe` (reorder-safe wiring) + validity round-trips

**Files:**
- Modify: `problems/chains/tool_chain_diff.py`
- Test: `tests/chains/test_tool_chain_diff.py`

**Interfaces:**
- Consumes: `_parse`, `_llm_id_map`, `build_schema` (Tasks 1–2).
- Produces: `apply(diff, parents) -> str` (RawChainSpec JSON); transcription rule
  `query_source="slot_j" -> input_mapping {"query":"$history[j-1]"}`,
  `dependencies=[j]`; `"outer_context" -> {"query":"$outer_context"}`, `deps=[]`.

- [ ] **Step 1: Write failing tests**

```python
from problems.chains.chain_runner import _resolve_reference
from problems.chains.chain_validation import validate_chain_spec


def _rebuild_baseline_diff() -> dict:
    # Reconstruct the 7-step baseline through the diff grammar: 3 new_tool +
    # 4 keeps (the baseline's LLM steps are #2,#3,#5,#6 -> ids a1..a4).
    return {
        **EVIDENCE,
        "base_parent": "A",
        "slot_1": {"kind": "new_tool", "tool_name": "retrieve", "query_source": "outer_context"},
        "slot_2": {"kind": "keep", "id": "a1", "dependencies": ["slot_1"]},
        "slot_3": {"kind": "keep", "id": "a2", "dependencies": ["slot_2"]},
        "slot_4": {"kind": "new_tool", "tool_name": "retrieve", "query_source": "slot_3"},
        "slot_5": {"kind": "keep", "id": "a3", "dependencies": ["slot_2", "slot_4"]},
        "slot_6": {"kind": "keep", "id": "a4", "dependencies": ["slot_5"]},
        "slot_7": {"kind": "new_tool", "tool_name": "retrieve_deep", "query_source": "slot_6"},
    }


def test_apply_on_baseline_round_trips_full_chain(changes, hover_parent):
    schema = changes.build_schema(hover_parent)
    diff = schema.validate(_rebuild_baseline_diff())
    child = json.loads(changes.apply(diff, parents=hover_parent))
    spec = validate_chain_spec(child, mode="full_chain", full_chain_config=FULL_CHAIN_CONFIG)
    assert len(spec.steps) == 7
    assert sum(1 for s in child["steps"] if s["step_type"] == "tool") == 3


def test_tool_query_wiring_is_absolute_and_reorder_safe(changes, hover_parent):
    schema = changes.build_schema(hover_parent)
    diff = schema.validate(
        {
            **EVIDENCE,
            "base_parent": "A",
            "slot_1": {"kind": "keep", "id": "a1"},
            "slot_2": {"kind": "new_tool", "tool_name": "retrieve", "query_source": "slot_1"},
        }
    )
    child = json.loads(changes.apply(diff, parents=hover_parent))
    tool = child["steps"][1]
    assert tool["step_config"]["input_mapping"]["query"] == "$history[0]"
    assert tool["dependencies"] == [1]
    # the absolute ref resolves to slot_1's output regardless of ordering
    assert _resolve_reference("$history[0]", "ctx", ["out-of-step-1"]) == "out-of-step-1"


def test_new_tool_first_slot_reads_outer_context(changes, hover_parent):
    schema = changes.build_schema(hover_parent)
    diff = schema.validate(
        {
            **EVIDENCE,
            "base_parent": "A",
            "slot_1": {"kind": "new_tool", "tool_name": "retrieve", "query_source": "outer_context"},
        }
    )
    child = json.loads(changes.apply(diff, parents=hover_parent))
    assert child["steps"][0]["step_config"]["input_mapping"]["query"] == "$outer_context"
    assert child["steps"][0]["dependencies"] == []


def test_keep_edit_overrides_llm_field(changes, hover_parent):
    schema = changes.build_schema(hover_parent)
    diff = schema.validate(
        {
            **EVIDENCE,
            "base_parent": "A",
            "slot_1": {"kind": "keep", "id": "a1", "edits": {"aim": "crisp new aim"}},
        }
    )
    child = json.loads(changes.apply(diff, parents=hover_parent))
    assert child["steps"][0]["aim"] == "crisp new aim"


def test_forward_and_self_refs_unrepresentable(changes, hover_parent):
    from pydantic import ValidationError

    schema = changes.build_schema(hover_parent)
    with pytest.raises(ValidationError):
        schema.validate(
            {
                **EVIDENCE,
                "base_parent": "A",
                "slot_1": {"kind": "new_tool", "tool_name": "retrieve", "query_source": "slot_1"},
            }
        )
```

- [ ] **Step 2: Run to verify failure** — `NotImplementedError` on `apply`.

- [ ] **Step 3: Implement `_transcribe` + `apply`**

```python
    @staticmethod
    def _slot_deps(slot: Any, k: int) -> list[int]:
        refs = getattr(slot, "dependencies", []) if k > 1 else []
        return sorted({int(r.removeprefix("slot_")) for r in refs})

    def _transcribe(self, diff: ToolChainDiffBase, specs: dict[str, RawChainSpec]) -> dict:
        by_id = {
            sid: step
            for ns, spec in specs.items()
            for sid, step in self._llm_id_map(ns, spec).items()
        }
        base = specs[diff.base_parent]
        steps: list[dict] = []
        for k in range(1, self.max_steps + 1):
            slot = getattr(diff, f"slot_{k}")
            if slot is None:
                break
            if slot.kind == "keep":
                data = by_id[slot.id].model_dump(
                    exclude={"number", "dependencies", "step_type", "frozen"}
                )
                data |= slot.edits.model_dump(exclude_none=True)
                steps.append(
                    {
                        "number": k,
                        "step_type": "llm",
                        "dependencies": self._slot_deps(slot, k),
                        **data,
                    }
                )
            elif slot.kind == "new_llm":
                steps.append(
                    {
                        "number": k,
                        "step_type": "llm",
                        "dependencies": self._slot_deps(slot, k),
                        "title": slot.title,
                        "aim": slot.aim,
                        "stage_action": slot.stage_action,
                        "reasoning_questions": slot.reasoning_questions,
                    }
                )
            else:
                if slot.query_source == "outer_context":
                    ref, deps = self.outer_context_token, []
                else:
                    j = int(slot.query_source.removeprefix("slot_"))
                    ref, deps = f"$history[{j - 1}]", [j]
                steps.append(
                    {
                        "number": k,
                        "step_type": "tool",
                        "dependencies": deps,
                        "title": f"{slot.tool_name} (step {k})",
                        "step_config": {
                            "tool_name": slot.tool_name,
                            "input_mapping": {"query": ref},
                        },
                    }
                )
        return {"system_prompt": base.system_prompt, "steps": steps}

    def apply(self, diff: Any, parents: dict[str, str]) -> str:
        specs = self._parse(parents)
        try:
            wire = self._transcribe(diff, specs)
            RawChainSpec.model_validate(wire)
        except MutationError:
            raise
        except Exception as e:
            raise MutationError(f"diff_apply_assertion: {e}") from e
        return json.dumps(wire, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Run tests** — `/run-tests tests/chains/test_tool_chain_diff.py`
  Expected: every test passes. Also confirm the `keep` model_dump excludes the
  discriminator/frozen keys so re-validation as `step_type:"llm"` is clean (the
  round-trip test enforces this).

- [ ] **Step 5: Commit (await approval)** — same two files.

---

### Task 4: HoVer mutation config + offline preview (live A/B deferred)

**Files:**
- Create: `config/mutation/structured_diff_hover.yaml`

**Interfaces:**
- Consumes: `AllowedToolChainChanges` (Tasks 1–3). Mirrors
  `config/mutation/structured_diff_chains.yaml`; only `allowed_changes` + bounds
  change. `max_steps` / `available_tools` copied from `FULL_CHAIN_CONFIG`
  (`problems/chains/hover/full7/config.py`) — hardcoded here because Hydra can't
  import the Python dict; keep the two in sync if HoVer's tool set changes.

- [ ] **Step 1: Write the config**

```yaml
# @package _global_
# Tool-aware structured DAG-diff mutation for HoVer full_chain genomes (arm B).
# Launch: python run.py problem.name=chains/hover/full7 ... mutation=structured_diff_hover
# max_steps / available_tools mirror problems/chains/hover/full7/config.FULL_CHAIN_CONFIG.

mutation_operator:
  _target_: gigaevo.evolution.mutation.structured_diff.StructuredDiffMutationOperator
  llm_wrapper: ${ref:llm}
  allowed_changes:
    _target_: problems.chains.tool_chain_diff.AllowedToolChainChanges
    min_steps: 1
    max_steps: 7
    available_tools: [retrieve, retrieve_deep]
  problem_context: ${problem_context}
  prompts_dir: ${prompts.dir}
  prompt_fetcher: ${prompt_fetcher}
```

- [ ] **Step 2: Offline config preview** — from repo root:

```bash
$GIGAEVO_PYTHON run.py problem.name=chains/hover/full7 mutation=structured_diff_hover --cfg job 2>&1 | sed -n '1,40p'
```

Expected: config composes; `mutation_operator._target_` resolves to
`StructuredDiffMutationOperator` with `allowed_changes._target_` =
`AllowedToolChainChanges`. (Full composition may need the same base overrides the
summarizer arm uses — mirror the live `carl_dag_diff` launch command's flags; do
**not** launch, proxy busy.)

- [ ] **Step 3: Lint** — `ruff check . && ruff format --check .`.

- [ ] **Step 4: Commit (await approval)** — `config/mutation/structured_diff_hover.yaml`.

---

## Deferred (out of scope for this plan — needs the seed chain + free proxy)

- Paired A/B on HoVer `full7`: arm A = free-rewrite `MutationAgent`, arm B =
  `mutation=structured_diff_hover`, same seed / 500-mutant budget. The existing
  `experiments/carl_dag_diff_ab/{analyze_ab,extract_tokens,make_figures,trace_lineage}.py`
  already tally `DiffMutationAgent`, so reuse them verbatim; only `problem.name`
  and the `mutation` config change.
- Smoke probe (`method="json_schema"`, Qwen3-8B) before the A/B, per the
  glm/structured-output launch discipline.

## Self-Review

- **Spec coverage:** §5 grammar → Task 2 (`_slot_forms`, three flat forms, enums);
  §6 reorder-safe wiring → Task 3 (`_transcribe` absolute `$history[j-1]` +
  resolver test); §7 applier/validation → Task 3 (`RawChainSpec.model_validate`
  guard + `validate_chain_spec(full_chain)` round-trip); §8 seam/no-modify → new
  module + Task 4 config, zero edits to `dag_changes.py`/operator; §11 test plan →
  Tasks 1–3 tests one-for-one. §3 fully-evolvable = `new_tool` present + tools not
  frozen. §10 `require_final_llm` not enforced (full7 = False) — noted.
- **Placeholder scan:** none — every step has runnable code/commands.
- **Type consistency:** `AllowedToolChainChanges.__init__(max_steps, available_tools)`
  used identically in tests and the Task-4 `_target_`; `_slot_deps`/`_transcribe`/
  `apply` signatures match their call sites; slot union branch kinds
  (`keep`/`new_llm`/`new_tool`) match the Task-2 schema test assertions and the
  Task-3 diff payloads.
- **Known risk to verify at execution:** `LLMStep.model_dump()` on a `keep` source
  must round-trip cleanly after re-adding `step_type:"llm"` — the baseline
  round-trip test (Task 3 Step 4) is the gate; if `stop_condition:None` or
  `example_reasoning` trip `extra="forbid"`, narrow the `exclude=` set there.
