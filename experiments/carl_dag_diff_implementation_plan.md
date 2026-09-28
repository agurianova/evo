# CARL DAG-Diff Mutation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve CARL reasoning-chain JSONs in GigaEvo two ways — arm A mutates raw wire JSON with the stock LLM mutator, arm B emits schema-constrained positional-slot diffs that are valid by construction — and show arm B's structural failure rate drops to ~zero at equal-or-better quality.

**Architecture:** A genome-agnostic `AllowedChanges` ABC lives in `gigaevo/evolution/mutation/allowed_changes.py`; the CARL-chain subclass `AllowedDagChanges` lives in a new `gigaevo/chains/` subpackage (per user decision: the operator must not depend on chain-specific types). `StructuredDiffMutationOperator` + `DiffMutationAgent` do one LLM call with `method="json_schema"` guided decoding (the proxy vLLM 400s on function_calling — probed 2026-07-02, 8/8 valid genomes via json_schema), then apply the diff by pure transcription with a `ReasoningChain.from_dict` round-trip tripwire. A shared `problems/chains/summarizer/` problem scores chains by ROUGE-L F1 on 8 Russian summarization samples via the Qwen3-8B chain endpoint; `ParseJsonProgram` replaces the Python-exec stages so JSON genomes flow through the standard pipeline.

**Tech Stack:** Python 3.11 (`/home/jovyan/.mlspace/envs/evo/bin/python3`), pydantic v2 (`create_model`/`TypeAdapter` per-call schemas), mmar-carl 0.3.0 (`ReasoningChain`, `LLMStepDescription`), LangGraph agents, Hydra config groups, existing `problems/chains/` runner stack (`LLMClient`, `run_chain_on_dataset`, `ChainSpec`).

**Reference documents (read before starting a task if unsure):**
- Approved design: `experiments/carl_dag_diff_mutation_design.md` (§4.2 diff language, §4.3 class hierarchy, §4.5 failure taxonomy, §4.6 experiment plan)
- Working prototype (source of truth for the port in Task 2): `experiments/carl_diff_prototype.py` — ran green: fuzz 2000/2000 valid, 8 illegal classes schema-rejected
- Live LLM probe: `experiments/carl_diff_llm_probe.py` — json_schema 8/8 ok, tools mode hard-400
- Seeds + eval data: `carl_pack/summarizer-evolution/`

## Global Constraints

- Python: always `/home/jovyan/.mlspace/envs/evo/bin/python3`; ruff at `/home/jovyan/.mlspace/envs/evo/bin/ruff`.
- Tests: **only** via the `/run-tests` skill, always targeting specific files. Never `pytest tests/` (hangs). `pytest.ini` has `asyncio_mode = auto` — plain `async def test_*` works, no marks.
- Commits: **wait for the user's explicit commit approval before every commit**; use `rtk git`, never plain `git`.
- Structured output: `method="json_schema"` hardcoded — the LiteLLM proxy (10.232.89.98:4000, model `Qwen/Qwen3-235B-A22B-Instruct-2507`, key `sk-gigaevo` via `OPENAI_API_KEY`) rejects `tools`/function_calling with a hard 400 (no `--tool-call-parser`). Never "fix" this by switching methods.
- Networking: `NO_PROXY` must include `10.232.89.98` for any command touching the proxy; `HTTPS_PROXY` required for Telegram.
- Prompts: literal `{`/`}` in `.txt` prompt files must be doubled (`.format()` KeyError = silent run death). The prompt files below contain no literal braces — keep it that way.
- Code style: zero comments except a one-line WHY for the non-obvious; loguru for logging; exceptions inherit from `gigaevo/exceptions.py`; no `hasattr`/`getattr`-probing dispatch; no planning markers in code/docstrings.
- Live experiments are running on this box (static-lever blast, sequential_unlock). All new code is additive (new files/params); do not touch modules on live hot paths beyond what each task specifies, and never restart or flush anything without the user.
- Minimum-viable: `AllowedDagChanges` ships with only `min_steps`/`max_steps` knobs. The design's extra knobs (`allowed_changes` list, `editable_fields`, `frozen_steps`) are a documented deviation — summarizer runs freeze nothing (design §4.3 "Moot here"); do not add them.
- Docs rule (project CLAUDE.md): the same PR that adds the subpackage/config groups must update `docs/ARCHITECTURE.md` (Task 9).

---

### Task 1: `AllowedChanges` contract

**Files:**
- Create: `gigaevo/evolution/mutation/allowed_changes.py`
- Test: `tests/evolution/test_allowed_changes.py`

**Interfaces:**
- Produces: `DiffSchema` (frozen dataclass: `json_schema: dict[str, Any]`, `validate: Callable[[Any], Any]`) and abstract `AllowedChanges` with methods `build_schema(parents: dict[str, str]) -> DiffSchema`, `render_parents(parents: dict[str, str]) -> str`, `apply(diff: Any, parents: dict[str, str]) -> str`, `describe() -> str`. Tasks 2–4 depend on these exact names.

- [ ] **Step 1: Write the failing test**

```python
"""Tests for the genome-agnostic AllowedChanges diff contract."""

from __future__ import annotations

import dataclasses

import pytest

from gigaevo.evolution.mutation.allowed_changes import AllowedChanges, DiffSchema


def test_abc_cannot_be_instantiated():
    with pytest.raises(TypeError):
        AllowedChanges()


def test_diff_schema_is_frozen():
    schema = DiffSchema(json_schema={"type": "object"}, validate=lambda x: x)
    with pytest.raises(dataclasses.FrozenInstanceError):
        schema.json_schema = {}


def test_minimal_subclass_satisfies_contract():
    class Echo(AllowedChanges):
        def build_schema(self, parents):
            return DiffSchema(json_schema={"type": "object"}, validate=lambda x: x)

        def render_parents(self, parents):
            return "\n".join(f"{ns}: {code}" for ns, code in parents.items())

        def apply(self, diff, parents):
            return str(diff)

        def describe(self):
            return "echo"

    changes = Echo()
    assert changes.build_schema({"A": "{}"}).json_schema == {"type": "object"}
    assert changes.apply({"k": 1}, {"A": "{}"}) == "{'k': 1}"
```

- [ ] **Step 2: Run test to verify it fails**

Use the `/run-tests` skill targeting `tests/evolution/test_allowed_changes.py`.
Expected: FAIL — `ModuleNotFoundError: No module named 'gigaevo.evolution.mutation.allowed_changes'`.

- [ ] **Step 3: Write the implementation**

`gigaevo/evolution/mutation/allowed_changes.py`:

```python
"""Genome-agnostic diff contract for StructuredDiffMutationOperator.

A subclass owns one genome family (e.g. CARL chain DAGs in gigaevo/chains/)
and defines which changes are representable; the operator never inspects
genome internals. Parents are keyed by prompt namespace ("A", "B", ...) to
genome code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DiffSchema:
    json_schema: dict[str, Any]
    validate: Callable[[Any], Any]


class AllowedChanges(ABC):
    @abstractmethod
    def build_schema(self, parents: dict[str, str]) -> DiffSchema:
        """Per-call wire schema (guided decoding) + validator for these parents."""

    @abstractmethod
    def render_parents(self, parents: dict[str, str]) -> str:
        """Render parent genomes for the mutation prompt, with stable step ids."""

    @abstractmethod
    def apply(self, diff: Any, parents: dict[str, str]) -> str:
        """Transcribe a validated diff into child genome code; MutationError on failure."""

    @abstractmethod
    def describe(self) -> str:
        """Prose description of the diff language for the system prompt."""
```

- [ ] **Step 4: Run test to verify it passes**

Use the `/run-tests` skill targeting `tests/evolution/test_allowed_changes.py`. Expected: 3 passed.

- [ ] **Step 5: Lint, then commit (after user approval)**

Run: `/home/jovyan/.mlspace/envs/evo/bin/ruff check gigaevo/evolution/mutation/allowed_changes.py tests/evolution/test_allowed_changes.py && /home/jovyan/.mlspace/envs/evo/bin/ruff format --check gigaevo/evolution/mutation/allowed_changes.py tests/evolution/test_allowed_changes.py`

Ask the user for commit approval. After approval:

```bash
rtk git add gigaevo/evolution/mutation/allowed_changes.py tests/evolution/test_allowed_changes.py
rtk git commit -m "feat(mutation): genome-agnostic AllowedChanges diff contract"
```

---

### Task 2: `AllowedDagChanges` — CARL positional-slot diffs in `gigaevo/chains/`

**Files:**
- Create: `gigaevo/chains/__init__.py`
- Create: `gigaevo/chains/dag_changes.py`
- Test: `tests/chains/__init__.py` (empty), `tests/chains/test_dag_changes.py`

**Interfaces:**
- Consumes: `AllowedChanges`, `DiffSchema` from Task 1; `MutationError` from `gigaevo/exceptions.py:111`.
- Produces: `AllowedDagChanges(min_steps: int = 1, max_steps: int = 8)` implementing the four ABC methods. `apply()` returns the child genome as pretty-printed JSON (`ensure_ascii=False, indent=2`). Failure labels: `carl_validation_error:` (unparseable parent), `diff_apply_assertion:` (transcription/round-trip failure) — both raised as `MutationError`.

This is a faithful port of `experiments/carl_diff_prototype.py` (verified: fuzz 2000/2000). Do not redesign; only repackage as a class.

- [ ] **Step 1: Write the failing tests**

`tests/chains/__init__.py`: empty file.

`tests/chains/test_dag_changes.py`:

```python
"""Tests for AllowedDagChanges: schema-valid diffs -> valid chains by construction."""

from __future__ import annotations

import json
import random

import pytest
from mmar_carl.chain import ReasoningChain
from mmar_carl.models.steps import LLMStepDescription
from pydantic import ValidationError

from gigaevo.chains.dag_changes import CONTENT_FIELDS, AllowedDagChanges
from gigaevo.exceptions import MutationError


def make_genome(n_steps: int) -> str:
    steps = [
        LLMStepDescription(
            number=i + 1,
            dependencies=[i] if i else [],
            title=f"step {i + 1}",
            aim=f"aim {i + 1}",
            stage_action=f"action {i + 1}",
        )
        for i in range(n_steps)
    ]
    wire = ReasoningChain(
        steps=steps, max_workers=1, enable_progress=False, metadata={}
    ).to_dict()
    wire["task_description"] = "summarize the text"
    wire["steps"][-1]["is_output_step"] = True
    return json.dumps(wire, ensure_ascii=False)


@pytest.fixture
def parents() -> dict[str, str]:
    return {"A": make_genome(2), "B": make_genome(3)}


@pytest.fixture
def changes() -> AllowedDagChanges:
    return AllowedDagChanges()


ARCHETYPES = {
    "edit": {
        "reasoning": "sharpen the final step",
        "base_parent": "A",
        "steps": [
            {"kind": "keep", "id": "a1"},
            {
                "kind": "keep",
                "id": "a2",
                "dependencies": ["slot_1"],
                "edits": {"aim": "one crisp final sentence"},
            },
        ],
    },
    "insert": {
        "reasoning": "add a verification step",
        "base_parent": "A",
        "steps": [
            {"kind": "keep", "id": "a1"},
            {
                "kind": "new",
                "title": "Verify facts",
                "aim": "Cross-check the draft against the source",
                "dependencies": ["slot_1"],
            },
            {"kind": "keep", "id": "a2", "dependencies": ["slot_2"]},
        ],
    },
    "delete": {
        "reasoning": "single-shot summarizer",
        "base_parent": "A",
        "steps": [{"kind": "keep", "id": "a2"}],
    },
    "duplicate": {
        "reasoning": "two drafts then merge",
        "base_parent": "A",
        "steps": [
            {"kind": "keep", "id": "a1"},
            {"kind": "keep", "id": "a1", "dependencies": []},
            {"kind": "keep", "id": "a2", "dependencies": ["slot_1", "slot_2"]},
        ],
    },
    "rewire": {
        "reasoning": "parallel off the raw input",
        "base_parent": "B",
        "steps": [
            {"kind": "keep", "id": "b1"},
            {"kind": "keep", "id": "b2", "dependencies": []},
            {"kind": "keep", "id": "b3", "dependencies": ["slot_1", "slot_2"]},
        ],
    },
    "full_rewrite": {
        "reasoning": "all-new skeleton",
        "base_parent": "B",
        "steps": [
            {"kind": "new", "title": "Extract entities", "aim": "Name actors and event"},
            {
                "kind": "new",
                "title": "Compose summary",
                "aim": "One sentence from the entities",
                "dependencies": ["slot_1"],
            },
        ],
    },
}

REJECTS = {
    "forward dep": {
        "reasoning": "x",
        "base_parent": "A",
        "steps": [
            {"kind": "keep", "id": "a1"},
            {"kind": "keep", "id": "a2", "dependencies": ["slot_5"]},
        ],
    },
    "dangling keep id": {
        "reasoning": "x",
        "base_parent": "A",
        "steps": [{"kind": "keep", "id": "a9"}],
    },
    "donor keep under base A": {
        "reasoning": "x",
        "base_parent": "A",
        "steps": [{"kind": "keep", "id": "b1"}],
    },
    "self dep on slot 1": {
        "reasoning": "x",
        "base_parent": "A",
        "steps": [{"kind": "keep", "id": "a1", "dependencies": ["slot_1"]}],
    },
    "empty chain": {"reasoning": "x", "base_parent": "A", "steps": []},
    "empty aim on new step": {
        "reasoning": "x",
        "base_parent": "A",
        "steps": [{"kind": "new", "title": "t", "aim": ""}],
    },
    "edit aim to empty": {
        "reasoning": "x",
        "base_parent": "A",
        "steps": [{"kind": "keep", "id": "a1", "edits": {"aim": ""}}],
    },
    "9th slot": {
        "reasoning": "x",
        "base_parent": "A",
        "steps": [{"kind": "keep", "id": "a1"}]
        + [
            {"kind": "new", "title": "t", "aim": "a", "dependencies": []}
            for _ in range(8)
        ],
    },
}


@pytest.mark.parametrize("label", sorted(ARCHETYPES))
def test_archetype_diffs_yield_valid_child_genomes(changes, parents, label):
    schema = changes.build_schema(parents)
    diff = schema.validate(ARCHETYPES[label])
    child_code = changes.apply(diff, parents)
    child = ReasoningChain.from_dict(json.loads(child_code), use_typed_steps=True)
    assert len(child.steps) == len(ARCHETYPES[label]["steps"])
    assert json.loads(child_code)["steps"][-1]["is_output_step"] is True


@pytest.mark.parametrize("label", sorted(REJECTS))
def test_illegal_diffs_are_schema_unrepresentable(changes, parents, label):
    schema = changes.build_schema(parents)
    with pytest.raises(ValidationError):
        schema.validate(REJECTS[label])


def test_edit_overrides_kept_field(changes, parents):
    schema = changes.build_schema(parents)
    diff = schema.validate(ARCHETYPES["edit"])
    child = json.loads(changes.apply(diff, parents))
    assert child["steps"][1]["aim"] == "one crisp final sentence"
    assert child["steps"][0]["aim"] == "aim 1"


def test_dependencies_are_renumbered_and_deduped(changes, parents):
    schema = changes.build_schema(parents)
    diff = schema.validate(
        {
            "reasoning": "x",
            "base_parent": "A",
            "steps": [
                {"kind": "keep", "id": "a1"},
                {"kind": "keep", "id": "a2", "dependencies": ["slot_1", "slot_1"]},
            ],
        }
    )
    child = json.loads(changes.apply(diff, parents))
    assert child["steps"][1]["dependencies"] == [1]


def test_single_parent_schema_works(changes):
    parents = {"A": make_genome(2)}
    schema = changes.build_schema(parents)
    diff = schema.validate(ARCHETYPES["delete"])
    changes.apply(diff, parents)


def test_unparseable_parent_raises_carl_validation_error(changes):
    with pytest.raises(MutationError, match="carl_validation_error"):
        changes.build_schema({"A": "not json"})


def test_render_parents_lists_ids_and_deps(changes, parents):
    rendered = changes.render_parents(parents)
    for sid in ("a1", "a2", "b1", "b2", "b3"):
        assert sid in rendered
    assert "step 1" in rendered


def test_describe_mentions_slots_and_bounds():
    text = AllowedDagChanges(min_steps=1, max_steps=8).describe()
    assert "slot" in text.lower()
    assert "8" in text


def test_invalid_bounds_rejected():
    with pytest.raises(ValueError):
        AllowedDagChanges(min_steps=0)
    with pytest.raises(ValueError):
        AllowedDagChanges(min_steps=5, max_steps=4)


def test_fuzz_schema_valid_diffs_always_apply(changes, parents):
    schema = changes.build_schema(parents)
    chains = {ns: ReasoningChain.from_dict(json.loads(c), use_typed_steps=True) for ns, c in parents.items()}
    rng = random.Random(7)
    words = "draft polish verify extract merge rank filter compress".split()
    for i in range(300):
        ns = rng.choice(list(parents))
        ids = [f"{ns.lower()}{j + 1}" for j in range(len(chains[ns].steps))]
        n_slots = rng.randint(1, 8)
        steps = []
        for k in range(1, n_slots + 1):
            deps = (
                {}
                if k == 1
                else {
                    "dependencies": rng.sample(
                        [f"slot_{j}" for j in range(1, k)], k=rng.randint(0, k - 1)
                    )
                }
            )
            if rng.random() < 0.6:
                edits = (
                    {"edits": {rng.choice(CONTENT_FIELDS): rng.choice(words)}}
                    if rng.random() < 0.4
                    else {}
                )
                steps.append({"kind": "keep", "id": rng.choice(ids), **edits, **deps})
            else:
                steps.append(
                    {
                        "kind": "new",
                        "title": rng.choice(words),
                        "aim": rng.choice(words),
                        **deps,
                    }
                )
        diff = schema.validate(
            {"reasoning": f"fuzz {i}", "base_parent": ns, "steps": steps}
        )
        child_code = changes.apply(diff, parents)
        ReasoningChain.from_dict(json.loads(child_code), use_typed_steps=True)
```

- [ ] **Step 2: Run tests to verify they fail**

Use the `/run-tests` skill targeting `tests/chains/test_dag_changes.py`.
Expected: FAIL — `ModuleNotFoundError: No module named 'gigaevo.chains'`.

- [ ] **Step 3: Write the implementation**

`gigaevo/chains/__init__.py`:

```python
from gigaevo.chains.dag_changes import AllowedDagChanges

__all__ = ["AllowedDagChanges"]
```

`gigaevo/chains/dag_changes.py` (port of `experiments/carl_diff_prototype.py` — keep the logic byte-equivalent where shown):

```python
"""Positional-slot DAG-diff vocabulary for CARL reasoning chains.

Genomes are CARL wire JSON (ReasoningChain.to_dict plus the platform extras
task_description / is_output_step). A diff IS the full child chain as 1..max_steps
positional slots (keep-by-id or new), so schema-valid diffs transcribe into valid
chains by construction. Design: experiments/carl_dag_diff_mutation_design.md S4.2.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal, Union

from mmar_carl.chain import ReasoningChain
from mmar_carl.models.steps import LLMStepDescription
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, create_model

from gigaevo.evolution.mutation.allowed_changes import AllowedChanges, DiffSchema
from gigaevo.exceptions import MutationError

CONTENT_FIELDS = tuple(
    name
    for name in ("title", "aim", "stage_action", "reasoning_questions", "example_reasoning")
    if name in LLMStepDescription.model_fields
)

# aim/title must stay non-empty or LLMStepDescription's validator rejects the chain;
# min_length pushes that invariant into the schema so it is unrepresentable-to-break
_EDIT_FIELD_DEFS = {
    name: (
        str | None,
        Field(default=None, min_length=1) if name in ("title", "aim") else Field(default=None),
    )
    for name in CONTENT_FIELDS
}
StepEdits = create_model("StepEdits", __config__=ConfigDict(extra="forbid"), **_EDIT_FIELD_DEFS)


def _base_ids(ns: str, chain: ReasoningChain) -> list[str]:
    return [f"{ns.lower()}{i + 1}" for i in range(len(chain.steps))]


class AllowedDagChanges(AllowedChanges):
    def __init__(self, *, min_steps: int = 1, max_steps: int = 8):
        if not 1 <= min_steps <= max_steps:
            raise ValueError(f"invalid step bounds: min={min_steps} max={max_steps}")
        self.min_steps = min_steps
        self.max_steps = max_steps

    def build_schema(self, parents: dict[str, str]) -> DiffSchema:
        chains, _ = self._parse(parents)
        adapter = self._build_adapter(chains)
        schema = {"title": "chain_dag_diff", **adapter.json_schema()}
        return DiffSchema(json_schema=schema, validate=adapter.validate_python)

    def render_parents(self, parents: dict[str, str]) -> str:
        chains, extras = self._parse(parents)
        blocks = []
        for ns, chain in chains.items():
            lines = [f"=== Parent {ns} ==="]
            if extras[ns]:
                lines.append(f"chain task_description: {extras[ns]}")
            for sid, step in zip(_base_ids(ns, chain), chain.steps):
                deps = [f"{ns.lower()}{d}" for d in step.dependencies]
                lines.append(f"{sid} | deps={deps or '[]'} | title: {step.title}")
                for field in ("aim", "stage_action", "reasoning_questions", "example_reasoning"):
                    value = getattr(step, field, "")
                    if value:
                        lines.append(f"    {field}: {value}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def apply(self, diff: Any, parents: dict[str, str]) -> str:
        chains, extras = self._parse(parents)
        try:
            wire = self._transcribe(diff, chains, extras)
            reparsed = ReasoningChain.from_dict(json.loads(json.dumps(wire)), use_typed_steps=True)
            if len(reparsed.steps) != len(wire["steps"]):
                raise ValueError(
                    f"round-trip step count {len(reparsed.steps)} != {len(wire['steps'])}"
                )
        except MutationError:
            raise
        except Exception as e:
            raise MutationError(f"diff_apply_assertion: {e}") from e
        return json.dumps(wire, ensure_ascii=False, indent=2)

    def describe(self) -> str:
        return (
            "POSITIONAL-SLOT CHAIN DIFF\n"
            "- Choose base_parent (one of the rendered parent letters). You may only 'keep' "
            "step ids belonging to that parent; other parents are inspiration — re-create "
            "their steps as 'new' slots if wanted.\n"
            f"- 'steps' is the FULL child chain, an ordered list of {self.min_steps}..{self.max_steps} "
            "slots. Any base step you omit is deleted. Keeping the same base id twice duplicates it.\n"
            "- Slot forms: keep = reuse a base step by id, optionally overriding fields via 'edits'; "
            "new = a fresh LLM step with title/aim/stage_action/reasoning_questions.\n"
            "- Wiring is explicit: every slot after the first declares 'dependencies' — earlier "
            "slots ('slot_1'..'slot_<k-1>') whose outputs it consumes. Slot 1 has no dependencies "
            "field. Dependencies always refer to slot positions in the NEW chain, never to base ids.\n"
            "- The last slot is the output step; its answer is what gets scored."
        )

    def _parse(self, parents: dict[str, str]) -> tuple[dict[str, ReasoningChain], dict[str, str]]:
        chains: dict[str, ReasoningChain] = {}
        extras: dict[str, str] = {}
        for ns, code in parents.items():
            try:
                doc = json.loads(code)
                chains[ns] = ReasoningChain.from_dict(doc, use_typed_steps=True)
            except Exception as e:
                raise MutationError(f"carl_validation_error: parent {ns}: {e}") from e
            extras[ns] = doc.get("task_description", "")
        return chains, extras

    def _build_adapter(self, chains: dict[str, ReasoningChain]) -> TypeAdapter:
        branches = []
        for ns, chain in chains.items():
            ids = _base_ids(ns, chain)
            slot_models: list[Any] = []
            for k in range(1, self.max_steps + 1):
                if k == 1:
                    dep_field: dict[str, Any] = {}
                else:
                    slot_ref = Literal[tuple(f"slot_{j}" for j in range(1, k))]
                    dep_field = {"dependencies": (list[slot_ref], ...)}
                keep = create_model(
                    f"Keep_{ns}_{k}",
                    __config__=ConfigDict(extra="forbid"),
                    kind=(Literal["keep"], ...),
                    id=(Literal[tuple(ids)], ...),
                    edits=(StepEdits, StepEdits()),
                    **dep_field,
                )
                new = create_model(
                    f"New_{ns}_{k}",
                    __config__=ConfigDict(extra="forbid"),
                    kind=(Literal["new"], ...),
                    step_type=(Literal["llm"], "llm"),
                    title=(str, Field(..., min_length=1)),
                    aim=(str, Field(..., min_length=1)),
                    stage_action=(str, ""),
                    reasoning_questions=(str, ""),
                    **dep_field,
                )
                slot_models.append(Annotated[Union[keep, new], Field(discriminator="kind")])
            steps_type = Union[
                tuple(
                    tuple[*slot_models[:n]]
                    for n in range(self.min_steps, self.max_steps + 1)
                )
            ]
            branches.append(
                create_model(
                    f"ChainDagDiff_{ns}",
                    __config__=ConfigDict(extra="forbid"),
                    reasoning=(str, ...),
                    base_parent=(Literal[ns], ...),
                    steps=(steps_type, ...),
                )
            )
        if len(branches) == 1:
            return TypeAdapter(branches[0])
        return TypeAdapter(Annotated[Union[tuple(branches)], Field(discriminator="base_parent")])

    def _transcribe(
        self,
        diff: BaseModel,
        chains: dict[str, ReasoningChain],
        extras: dict[str, str],
    ) -> dict:
        base = chains[diff.base_parent]
        by_id = dict(zip(_base_ids(diff.base_parent, base), base.steps))
        steps = []
        for k, slot in enumerate(diff.steps, start=1):
            raw_deps = [
                int(ref.removeprefix("slot_")) for ref in getattr(slot, "dependencies", [])
            ]
            deps = sorted(set(raw_deps))
            if slot.kind == "keep":
                data = {f: getattr(by_id[slot.id], f) for f in CONTENT_FIELDS}
                data |= slot.edits.model_dump(exclude_none=True)
            else:
                data = {f: getattr(slot, f, "") for f in CONTENT_FIELDS}
            steps.append(LLMStepDescription(number=k, dependencies=deps, **data))
        child = ReasoningChain(
            steps=steps,
            max_workers=base.max_workers,
            enable_progress=base.enable_progress,
            metadata=dict(base.metadata),
        )
        wire = child.to_dict()
        # platform extras that carl's round-trip drops: derived, never LLM-emitted
        wire["task_description"] = extras[diff.base_parent]
        wire["steps"][-1]["is_output_step"] = True
        return wire
```

Note: `getattr(slot, "dependencies", [])` and `getattr(slot, f, "")` iterate over dynamically created pydantic models where the field set varies by slot position/kind — this is data access on `create_model` products, not method-probing dispatch; keep as in the prototype.

`describe()` covers only the diff-language mechanics (a deliberate deviation from the prototype's SYSTEM constant, which ended with a "fill reasoning first" line): guidance for the `reasoning` field lives in the Task 3 system prompt's OUTPUT RULES 1–2, so the two texts compose without overlap when the prompt embeds `{allowed_changes}`.

- [ ] **Step 4: Run tests to verify they pass**

Use the `/run-tests` skill targeting `tests/chains/test_dag_changes.py`. Expected: all pass (6 archetypes + 8 rejects + 7 others).

- [ ] **Step 5: Lint, then commit (after user approval)**

Run: `/home/jovyan/.mlspace/envs/evo/bin/ruff check gigaevo/chains tests/chains && /home/jovyan/.mlspace/envs/evo/bin/ruff format --check gigaevo/chains tests/chains`

Ask the user for commit approval. After approval:

```bash
rtk git add gigaevo/chains tests/chains
rtk git commit -m "feat(chains): AllowedDagChanges positional-slot diff vocabulary for CARL chains"
```

---

### Task 3: `DiffMutationAgent` + `structured_diff` prompts

**Files:**
- Create: `gigaevo/prompts/structured_diff/system.txt`
- Create: `gigaevo/prompts/structured_diff/user.txt`
- Create: `gigaevo/llm/agents/structured_diff.py`
- Test: `tests/llm/test_structured_diff_agent.py`

**Interfaces:**
- Consumes: `AllowedChanges`/`DiffSchema` (Task 1), `LangGraphAgent` (`gigaevo/llm/agents/base.py`), `FixedDirPromptFetcher`/`PromptFetcher` (`gigaevo/prompts/fetcher.py`), `MUTATION_CONTEXT_METADATA_KEY` (`gigaevo/evolution/mutation/constants.py`), `MetricsFormatter`.
- Produces: `DiffMutationAgent(llm, allowed_changes, task_description, metrics_context, prompts_dir=None, prompt_fetcher=None)` with `async arun(*, parents: list[Program], parents_map: dict[str, str], diff_schema: DiffSchema) -> dict` returning `{"code": str, "diff": dict, "metadata": dict}`. Task 4 depends on this exact signature.

- [ ] **Step 1: Write the prompt files**

Both files are near-copies of the stock non-schema mutation prompts `gigaevo/prompts/mutation/{system,user}.txt` — same section skeleton (ROLE / EVIDENCE INPUTS / ARCHETYPE / EXECUTION PRINCIPLES / OUTPUT RULES / CONTEXT), same gates and citation discipline. They diverge only where the output medium differs: the diff schema has a single free-text field (`reasoning`), so the stock `insights_used`/`card_ids_used`/`insight_ids_used`/`changes`/`justification` rules fold into `reasoning` rules, and OUTPUT RULE 3 ("`code` is Python source, not JSON") becomes the diff language — `{allowed_changes}` (= `AllowedDagChanges.describe()`) is that rule's body. Rule-2 examples are chain-flavored replacements for the stock tabular ones (no dataset names, no numerics).

`gigaevo/prompts/structured_diff/system.txt`:

```
## ROLE

You are the **mutation operator** in an LLM-guided evolutionary algorithm. Each call gives you one or more labeled parent reasoning chains (in the user message) — DAGs of LLM steps executed by a small model — and an evidence pack about their lineage and the run. You produce ONE child chain, expressed as a diff in the DIFF LANGUAGE under OUTPUT RULE 3 — when given a single parent, a *targeted edit* of that parent; when given ≥2 parents, a *coherent crossover* that selects exactly one focal base and borrows only evidence-justified, cited mechanisms from one or more remaining donors — not a from-scratch rewrite — plus a `reasoning` field explaining the edit. Evidence drives the edit; do not invent.

When ≥2 parents are present, **parent order is arbitrary** (sampling order, not fitness or quality). Choose exactly one parent as the *base* — set `base_parent` to its letter and preserve its overall step structure and wiring — and treat every other parent as a *donor*. Donor steps cannot be kept by id: re-create each borrowed donor mechanism as a `new` slot and cite it in `reasoning` as `parent:<letter> step:<id>`.

The TASK the chains are solving is described in CONTEXT at the bottom. You are NOT designing a fresh chain for that task; you are improving from the parent(s).

## EVIDENCE INPUTS (user message)

Absent slots are omitted — do not fabricate content.

- **Chain listing** — each `=== Parent <letter> ===` block lists that parent's steps with stable ids (`a1`, `b2`, …), their dependencies, and their content fields. `keep` slots reference these ids.
- **Evaluation context** — a per-parent `=== Parent <letter> evaluation context ===` block with the standard evidence pack:
  - **Program Metrics** — parent's measured metrics with target direction (↑/↓ better). Fitness drives selection.
  - **Program Insights** — numbered `N. [type][tag][severity]` items from an upstream analyst, each carrying an anchor, a mechanism hypothesis, and a concrete substitute. The list is priority-ordered: item 1 is the analyst's top recommendation. **If the list is non-empty, act on insight 1 or state in `reasoning` why not and act on another. If the list is empty, cite ≥1 other evidence item (intra cluster / stats trigger) instead.** A `card: <id>` attribution marks a cross-population transposition, not a lever proven on this parent — if a better-grounded parent-native insight fits, act on that and say so in `reasoning`. Tag → action: `beneficial` → PRESERVE / EXTEND; `harmful` → REMOVE / REPLACE; `fragile` → ROBUSTIFY / add guards; `rigid` → PARAMETERIZE / TUNE; `neutral` → low priority.
  - **Evolutionary Statistics** — run-level signals: trend (rising/flat/falling), iters-since-best, archive percentile (100=best, direction-aware), invalid streak (max consecutive in window), archive worst/median/best. The archive line and percentile appear only once enough valid programs exist.
  - **Intra Memory** — this parent's lineage card: tried-strategy clusters with verdicts (improved/neutral/regressed/failed) and failure notes.

**Insights are the primary driver of WHAT to change; archetype only constrains HOW MUCH structural novelty to introduce.**

## ARCHETYPE — apply gates FIRST, then pick exactly ONE

**Gates (apply in order; a hard gate overrides the frontier-awareness shaper below):**
- Archive percentile <25 → Exploration only (refining a known-inferior basin is wasted budget).
- Archive percentile ≥75 → all archetypes eligible per evidence.
- Middle band (25 ≤ percentile <75) → prefer Hybrid; pick Exploitation only when intra shows a verified `improved` cluster that has not yet been pushed further.
- Frontier awareness: use the archive worst/median/best and current program percentile to judge early vs frontier phase. Top-percentile parents may still pick structural archetypes when the archive is shallow. Do not derive hard thresholds from task-context prose.
- Noise filter: a `falling`/`flat` trend flagged as having too few valid iterations for a reliable signal is noise — do NOT force Exploration on that basis alone.

**Pick exactly ONE archetype from the gate-permitted set:**

EXPLOITATION:
1. **Precision Optimization** — fine-tune proven patterns; minimal risk (targeted `edits` on kept steps).
2. **Proven Pattern Extension** — generalise an already-improved strategy.
3. **Harmful Pattern Removal** — eliminate a documented failure mode (drop or replace the offending step).

EXPLORATION:
4. **Computational Reinvention** — novel chain topology or decomposition of the task.
5. **Solution Space Exploration** — change the SET of admissible solutions (serial↔parallel wiring, single draft↔competing drafts, add/remove a verification pass).
6. **Approach Synthesis** — combine two distinct evidence-backed mechanisms (e.g. two insights, or an insight + an intra cluster) into one coherent design.

HYBRID:
7. **Guided Innovation** — preserve a proven element, add ONE targeted novelty.
8. **Component Substitution** — replace ONE step (extractor, drafter, verifier, merger, polisher) with an alternative of the same kind in the same slot.

## EXECUTION PRINCIPLES

- One coherent edit per archetype; don't mix Exploit + Explore. Multiple donors do not license multiple independent edits — one coherent edit per archetype still holds across the full parent set.
- Don't re-apply a `regressed`/`failed` cluster without a clear corrective mechanism that addresses the named failure mode.
- High `invalid_streak` → simplify (fewer steps, tighter aims) before broader restructures.
- Step aims must be concrete and executable by a small model; avoid vague instructions.
- Write step content in the same language as the parent steps.

## OUTPUT RULES

Output must be a single JSON object conforming to the structured-output schema — a chain diff in the language of rule 3. No prose outside the object, no preamble, no markdown/code fences. Beyond what the schema already states:

1. **Cite, never invent.** The diff schema has no dedicated citation fields, so `reasoning` carries the citations. Reference real evidence by its label/anchor:
   - `"insight: <type> — <anchor>"` (primary; expected on most mutations)
   - `"tried: <label>"` (intra cluster to extend or correct)
   - `"plateau: <trigger>"` / `"invalid_streak: <n>"` (stats trigger)
   - `"parent:<letter> step:<id>"` (≥2-parent mode; names the donor step a `new` slot re-creates)
   In ≥2-parent mode, `reasoning` must include at least one evidence citation from the chosen base parent and one `parent:<letter> step:<id>` citation for each donor mechanism used. Never cite evidence that is not present in the user message.
2. **`reasoning` is a falsifiable causal hypothesis, not a description of the diff.** One short paragraph: the archetype, the citations (rule 1), then `<what changed, including old→new>: <why-it-transfers>` — the why-clause must link a specific problem property to why the change bites.
   - **Tautology test**: *would the clause still be true if the cited property were absent?* If yes, rewrite.
   - Two patterns that satisfy: **failure-mode bypass** — name the failure pattern the change escapes (e.g. `the extract step emits terse fragments that starve the drafter of context`); **constraint match** — name the property that makes the new structure correct (e.g. `the executor is a small model, so multi-purpose aims in one step get partially ignored`).
   - Draw the trigger from TASK CONTEXT / METRICS (or run stats like `invalid_streak`). Prefer a concrete value or context key over a qualitative descriptor.
   - Forbidden — these *describe the action* instead of *explaining why it works*: tautology (`verification improves faithfulness`), restatement of the diff (`adds a step`), goal restatement (`improves the score`).
   - Pure aim-wording tweaks with no problem-property hypothesis must say so explicitly: `rewords <step> aim; weak transfer-evidence`.

   GOOD: `"Component Substitution; insight: structure — final step. Rewired the final polish step to read the raw source text alongside the draft: each paraphrase hop drifts from source wording that the metric scores; re-grounding the last hop restores it."`
   BAD:  `"Added a quality-check step: makes the summary more faithful."`
3. **The child chain is expressed ONLY in this diff language — never emit raw chain JSON:**

{allowed_changes}

## CONTEXT (the TASK the CHAINS are solving — background for understanding the parents)

{task_description}

Available metrics:
{metrics_description}
```

`gigaevo/prompts/structured_diff/user.txt`:

```
Produce the next-generation chain for the parent(s) below. Use the evidence packed into each parent block (chain listing, then evaluation context: Program Metrics → Program Insights → Evolutionary Statistics → Intra Memory).

{parent_blocks}

---

Pick ONE archetype, cite the specific insights / stats triggers that motivated the change in `reasoning`, and emit a single coherent mutation as one diff object following the OUTPUT RULES in the system prompt.
```

Fit check for `{allowed_changes}` (run mentally against `AllowedDagChanges.describe()` from Task 2): the describe() block opens with its own `POSITIONAL-SLOT CHAIN DIFF` header and speaks of "rendered parent letters", matching the `=== Parent <letter> ===` chain listing; its "other parents are inspiration — re-create their steps as 'new' slots" line restates ROLE's base/donor contract; it contains no `reasoning` guidance (owned by rules 1–2 above). No literal `{`/`}` anywhere in either template outside the three placeholders; describe() is substituted as a format *value*, so its content is never re-formatted.

- [ ] **Step 2: Write the failing test**

`tests/llm/test_structured_diff_agent.py`:

```python
"""Tests for DiffMutationAgent with a fake structured-output router."""

from __future__ import annotations

import json

import pytest

from gigaevo.chains.dag_changes import AllowedDagChanges
from gigaevo.exceptions import MutationError
from gigaevo.llm.agents.structured_diff import DiffMutationAgent
from gigaevo.programs.metrics.context import MetricsContext, MetricSpec
from gigaevo.programs.program import Program
from tests.chains.test_dag_changes import make_genome


class FakeStructuredRouter:
    def __init__(self, payload):
        self.payload = payload
        self.schema_seen = None
        self.kwargs_seen = None
        self.messages_seen = None

    def with_structured_output(self, schema, **kwargs):
        self.schema_seen = schema
        self.kwargs_seen = kwargs
        return self

    async def ainvoke(self, messages):
        self.messages_seen = messages
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def _metrics_context() -> MetricsContext:
    return MetricsContext(
        specs={
            "fitness": MetricSpec(
                description="Mean ROUGE-L F1",
                higher_is_better=True,
                is_primary=True,
                lower_bound=0.0,
                upper_bound=1.0,
                decimals=3,
            )
        }
    )


DIFF_PAYLOAD = {
    "reasoning": "add a verification step",
    "base_parent": "A",
    "steps": [
        {"kind": "keep", "id": "a1"},
        {
            "kind": "new",
            "title": "Verify facts",
            "aim": "Cross-check the draft",
            "dependencies": ["slot_1"],
        },
        {"kind": "keep", "id": "a2", "dependencies": ["slot_2"]},
    ],
}


def _make_agent(payload):
    changes = AllowedDagChanges()
    router = FakeStructuredRouter(payload)
    agent = DiffMutationAgent(
        llm=router,
        allowed_changes=changes,
        task_description="Summarize Russian news in one sentence.",
        metrics_context=_metrics_context(),
    )
    return agent, router, changes


async def test_arun_returns_valid_child_code_and_diff():
    agent, router, changes = _make_agent(DIFF_PAYLOAD)
    parents_map = {"A": make_genome(2), "B": make_genome(3)}
    parents = [
        Program(code=parents_map["A"], iteration=0),
        Program(code=parents_map["B"], iteration=0),
    ]
    schema = changes.build_schema(parents_map)
    result = await agent.arun(parents=parents, parents_map=parents_map, diff_schema=schema)
    child = json.loads(result["code"])
    assert len(child["steps"]) == 3
    assert result["diff"] == DIFF_PAYLOAD
    assert router.kwargs_seen == {"method": "json_schema"}
    assert router.schema_seen["title"] == "chain_dag_diff"


async def test_prompt_contains_parents_and_diff_language():
    agent, router, changes = _make_agent(DIFF_PAYLOAD)
    parents_map = {"A": make_genome(2), "B": make_genome(3)}
    parents = [Program(code=c, iteration=0) for c in parents_map.values()]
    schema = changes.build_schema(parents_map)
    await agent.arun(parents=parents, parents_map=parents_map, diff_schema=schema)
    system, user = router.messages_seen
    assert "POSITIONAL-SLOT CHAIN DIFF" in system.content
    assert "Summarize Russian news" in system.content
    assert "a1" in user.content and "b3" in user.content


async def test_router_parse_failure_raises():
    agent, _, changes = _make_agent(ValueError("Structured output parse failed"))
    parents_map = {"A": make_genome(2)}
    parents = [Program(code=parents_map["A"], iteration=0)]
    schema = changes.build_schema(parents_map)
    with pytest.raises(ValueError, match="parse failed"):
        await agent.arun(parents=parents, parents_map=parents_map, diff_schema=schema)


async def test_schema_invalid_payload_raises_diff_schema_error():
    agent, _, changes = _make_agent({"reasoning": "x", "base_parent": "A", "steps": []})
    parents_map = {"A": make_genome(2)}
    parents = [Program(code=parents_map["A"], iteration=0)]
    schema = changes.build_schema(parents_map)
    with pytest.raises(MutationError, match="diff_schema_error"):
        await agent.arun(parents=parents, parents_map=parents_map, diff_schema=schema)
```

- [ ] **Step 3: Run tests to verify they fail**

Use the `/run-tests` skill targeting `tests/llm/test_structured_diff_agent.py`.
Expected: FAIL — `ModuleNotFoundError: No module named 'gigaevo.llm.agents.structured_diff'`.

- [ ] **Step 4: Write the implementation**

`gigaevo/llm/agents/structured_diff.py`:

```python
"""LangGraph agent that emits a schema-constrained DAG diff instead of raw genome text."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from gigaevo.evolution.mutation.allowed_changes import AllowedChanges, DiffSchema
from gigaevo.evolution.mutation.constants import MUTATION_CONTEXT_METADATA_KEY
from gigaevo.exceptions import MutationError
from gigaevo.llm.agents.base import LangGraphAgent
from gigaevo.llm.models import get_last_token_usage, get_selected_model
from gigaevo.llm.token_tracking import llm_stage_context
from gigaevo.monitoring.emit import emit as _emit_event
from gigaevo.monitoring.events import LLMCall
from gigaevo.programs.metrics.context import MetricsContext
from gigaevo.programs.metrics.formatter import MetricsFormatter
from gigaevo.programs.program import Program
from gigaevo.prompts.fetcher import FixedDirPromptFetcher, PromptFetcher


class DiffMutationState(TypedDict, total=False):
    parents: list[Program]
    parents_map: dict[str, str]
    diff_schema: DiffSchema
    messages: list[BaseMessage]
    llm_response: Any
    child_code: str
    diff_payload: dict[str, Any]
    metadata: dict[str, Any]


class DiffMutationAgent(LangGraphAgent):
    StateSchema = DiffMutationState

    def __init__(
        self,
        *,
        llm: Any,
        allowed_changes: AllowedChanges,
        task_description: str,
        metrics_context: MetricsContext,
        prompts_dir: str | Path | None = None,
        prompt_fetcher: PromptFetcher | None = None,
    ):
        self._allowed = allowed_changes
        fetcher = prompt_fetcher or FixedDirPromptFetcher(prompts_dir)
        self._user_template = fetcher.fetch("structured_diff", "user").text
        self._system_prompt = fetcher.fetch("structured_diff", "system").text.format(
            task_description=task_description,
            metrics_description=MetricsFormatter(metrics_context).format_metrics_description(),
            allowed_changes=allowed_changes.describe(),
        )
        super().__init__(llm)

    def build_prompt(self, state: DiffMutationState) -> DiffMutationState:
        blocks = [self._allowed.render_parents(state["parents_map"])]
        for ns, program in zip(state["parents_map"], state["parents"]):
            context = str(program.metadata.get(MUTATION_CONTEXT_METADATA_KEY) or "").strip()
            if context:
                blocks.append(f"=== Parent {ns} evaluation context ===\n{context}")
        state["messages"] = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=self._user_template.format(parent_blocks="\n\n".join(blocks))),
        ]
        return state

    async def acall_llm(self, state: DiffMutationState) -> DiffMutationState:
        # json_schema is the only structured-output transport the vLLM proxy serves
        # (function_calling 400s without --tool-call-parser; probed 2026-07-02)
        structured = self.llm.with_structured_output(
            state["diff_schema"].json_schema, method="json_schema"
        )
        t0 = time.monotonic()
        error_type: str | None = None
        ok = False
        try:
            with llm_stage_context(self.__class__.__name__):
                state["llm_response"] = await structured.ainvoke(state["messages"])
            ok = True
            if "metadata" not in state:
                state["metadata"] = {}
            model_used = get_selected_model()
            if model_used:
                state["metadata"]["model_used"] = model_used
            return state
        except Exception as exc:
            error_type = type(exc).__name__
            raise
        finally:
            try:
                usage = get_last_token_usage()
                _emit_event(
                    LLMCall(
                        stage=self.__class__.__name__,
                        endpoint="",
                        model=str(get_selected_model() or "unknown"),
                        attempt=1,
                        ok=ok,
                        latency_ms=(time.monotonic() - t0) * 1000.0,
                        tokens_in=usage.context if usage else 0,
                        tokens_out=usage.generated if usage else 0,
                        error_type=error_type,
                    )
                )
            except Exception:
                pass

    def parse_response(self, state: DiffMutationState) -> DiffMutationState:
        payload = state["llm_response"]
        try:
            diff = state["diff_schema"].validate(payload)
        except Exception as e:
            raise MutationError(f"diff_schema_error: {e}") from e
        state["child_code"] = self._allowed.apply(diff, state["parents_map"])
        state["diff_payload"] = payload if isinstance(payload, dict) else diff.model_dump()
        return state

    async def arun(
        self,
        *,
        parents: list[Program],
        parents_map: dict[str, str],
        diff_schema: DiffSchema,
    ) -> dict[str, Any]:
        state: DiffMutationState = {
            "parents": parents,
            "parents_map": parents_map,
            "diff_schema": diff_schema,
            "metadata": {},
        }
        final = await self.graph.ainvoke(state)
        return {
            "code": final["child_code"],
            "diff": final["diff_payload"],
            "metadata": final.get("metadata", {}),
        }
```

Implementation notes:
- The per-call `with_structured_output(...)` is built inside `acall_llm` from state (never assigned to `self.llm`) — the agent instance is shared across concurrent mutations; mutating `self.llm` would race.
- `MultiModelRouter.with_structured_output` bypasses auto-negotiation entirely when `"method"` is in kwargs (verified in `gigaevo/llm/models.py`); the wrapped `_StructuredOutputRouter.ainvoke(messages)` returns the parsed dict for dict schemas or raises `ValueError("Structured output parse failed...")`.
- The `finally` block replicates `LangGraphAgent.acall_llm`'s LLMCall emission so monitoring parity holds.

- [ ] **Step 5: Run tests to verify they pass**

Use the `/run-tests` skill targeting `tests/llm/test_structured_diff_agent.py`. Expected: 4 passed.

- [ ] **Step 6: Lint, then commit (after user approval)**

Run: `/home/jovyan/.mlspace/envs/evo/bin/ruff check gigaevo/llm/agents/structured_diff.py tests/llm/test_structured_diff_agent.py && /home/jovyan/.mlspace/envs/evo/bin/ruff format --check gigaevo/llm/agents/structured_diff.py tests/llm/test_structured_diff_agent.py`

Ask the user for commit approval. After approval:

```bash
rtk git add gigaevo/prompts/structured_diff gigaevo/llm/agents/structured_diff.py tests/llm/test_structured_diff_agent.py
rtk git commit -m "feat(llm): DiffMutationAgent with json_schema-guided DAG-diff output"
```

---

### Task 4: `StructuredDiffMutationOperator` + mutation config group

**Files:**
- Create: `gigaevo/evolution/mutation/structured_diff.py`
- Create: `config/mutation/structured_diff_chains.yaml`
- Test: `tests/evolution/test_structured_diff_operator.py`

**Interfaces:**
- Consumes: `MutationOperator`/`MutationSpec` (`gigaevo/evolution/mutation/base.py`), `AllowedChanges` (Task 1), `DiffMutationAgent.arun` (Task 3), `ProblemContext` (`gigaevo/problems/context.py` — only `.task_description` and `.metrics_context` are read).
- Produces: `StructuredDiffMutationOperator(llm_wrapper, allowed_changes, problem_context, prompts_dir=None, prompt_fetcher=None)`; `mutate_single` assigns namespaces `A, B, ...` by parent order and returns `MutationSpec(name="structured_diff")` with the raw diff payload under `MutationSpec.META_OUTPUT` and model under `MutationSpec.META_MODEL`. Launched via `+mutation=structured_diff_chains`.

- [ ] **Step 1: Write the failing test**

`tests/evolution/test_structured_diff_operator.py`:

```python
"""Tests for StructuredDiffMutationOperator with a fake structured-output router."""

from __future__ import annotations

import json

import pytest

from gigaevo.chains.dag_changes import AllowedDagChanges
from gigaevo.evolution.mutation.base import MutationSpec
from gigaevo.evolution.mutation.structured_diff import StructuredDiffMutationOperator
from gigaevo.exceptions import MutationError
from gigaevo.programs.metrics.context import MetricsContext, MetricSpec
from gigaevo.programs.program import Program
from tests.chains.test_dag_changes import make_genome
from tests.llm.test_structured_diff_agent import DIFF_PAYLOAD, FakeStructuredRouter


class _Ctx:
    task_description = "Summarize Russian news in one sentence."
    metrics_context = MetricsContext(
        specs={
            "fitness": MetricSpec(
                description="Mean ROUGE-L F1",
                higher_is_better=True,
                is_primary=True,
                lower_bound=0.0,
                upper_bound=1.0,
                decimals=3,
            )
        }
    )


def _operator(payload):
    return StructuredDiffMutationOperator(
        llm_wrapper=FakeStructuredRouter(payload),
        allowed_changes=AllowedDagChanges(),
        problem_context=_Ctx(),
    )


async def test_mutate_single_returns_spec_with_diff_metadata():
    operator = _operator(DIFF_PAYLOAD)
    parents = [
        Program(code=make_genome(2), iteration=0),
        Program(code=make_genome(3), iteration=0),
    ]
    spec = await operator.mutate_single(parents)
    assert spec is not None
    assert spec.name == "structured_diff"
    assert spec.parents == parents
    assert len(json.loads(spec.code)["steps"]) == 3
    assert spec.metadata[MutationSpec.META_OUTPUT] == DIFF_PAYLOAD


async def test_no_parents_returns_none():
    operator = _operator(DIFF_PAYLOAD)
    assert await operator.mutate_single([]) is None


async def test_schema_invalid_payload_surfaces_mutation_error():
    operator = _operator({"reasoning": "x", "base_parent": "A", "steps": []})
    parents = [Program(code=make_genome(2), iteration=0)]
    with pytest.raises(MutationError, match="diff_schema_error"):
        await operator.mutate_single(parents)


async def test_router_failure_wrapped_as_llm_call_error():
    operator = _operator(ValueError("Structured output parse failed: boom"))
    parents = [Program(code=make_genome(2), iteration=0)]
    with pytest.raises(MutationError, match="llm_call_error"):
        await operator.mutate_single(parents)
```

- [ ] **Step 2: Run test to verify it fails**

Use the `/run-tests` skill targeting `tests/evolution/test_structured_diff_operator.py`.
Expected: FAIL — `ModuleNotFoundError: No module named 'gigaevo.evolution.mutation.structured_diff'`.

- [ ] **Step 3: Write the implementation**

`gigaevo/evolution/mutation/structured_diff.py`:

```python
"""Mutation operator that asks the LLM for a schema-constrained diff, never raw genome text."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from gigaevo.evolution.mutation.allowed_changes import AllowedChanges
from gigaevo.evolution.mutation.base import MutationOperator, MutationSpec
from gigaevo.exceptions import MutationError
from gigaevo.llm.agents.structured_diff import DiffMutationAgent
from gigaevo.problems.context import ProblemContext
from gigaevo.programs.program import Program

if TYPE_CHECKING:
    from gigaevo.prompts.fetcher import PromptFetcher


class StructuredDiffMutationOperator(MutationOperator):
    """`AllowedChanges` builds the per-call schema, renders parents, and applies diffs;
    this operator stays genome-agnostic."""

    def __init__(
        self,
        *,
        llm_wrapper,
        allowed_changes: AllowedChanges,
        problem_context: ProblemContext,
        prompts_dir: str | Path | None = None,
        prompt_fetcher: PromptFetcher | None = None,
    ):
        self.allowed_changes = allowed_changes
        self.agent = DiffMutationAgent(
            llm=llm_wrapper,
            allowed_changes=allowed_changes,
            task_description=problem_context.task_description,
            metrics_context=problem_context.metrics_context,
            prompts_dir=prompts_dir,
            prompt_fetcher=prompt_fetcher,
        )
        logger.info(
            "[StructuredDiffMutationOperator] Initialized with {}",
            type(allowed_changes).__name__,
        )

    async def mutate_single(
        self,
        selected_parents: list[Program],
        memory_instructions: str | None = None,
    ) -> MutationSpec | None:
        if not selected_parents:
            logger.warning("[StructuredDiffMutationOperator] No parents provided")
            return None
        parents_map = {
            chr(ord("A") + i): parent.code for i, parent in enumerate(selected_parents)
        }
        try:
            schema = self.allowed_changes.build_schema(parents_map)
            result = await self.agent.arun(
                parents=selected_parents, parents_map=parents_map, diff_schema=schema
            )
        except MutationError:
            raise
        except Exception as e:
            raise MutationError(f"llm_call_error: {e}") from e
        metadata: dict = {MutationSpec.META_OUTPUT: result["diff"]}
        model_used = result["metadata"].get("model_used")
        if model_used:
            metadata[MutationSpec.META_MODEL] = model_used
        return MutationSpec(
            code=result["code"],
            parents=selected_parents,
            name="structured_diff",
            metadata=metadata,
        )
```

`config/mutation/structured_diff_chains.yaml`:

```yaml
# @package _global_
# Structured DAG-diff mutation for CARL chain genomes (arm B of the carl_dag_diff A/B).
# Launch: python run.py ... +mutation=structured_diff_chains

mutation_operator:
  _target_: gigaevo.evolution.mutation.structured_diff.StructuredDiffMutationOperator
  llm_wrapper: ${ref:llm}
  allowed_changes:
    _target_: gigaevo.chains.dag_changes.AllowedDagChanges
    min_steps: 1
    max_steps: 8
  problem_context: ${problem_context}
  prompts_dir: ${prompts.dir}
  prompt_fetcher: ${prompt_fetcher}
```

(Appended group override: `+mutation=structured_diff_chains` replaces the `mutation_operator` node that `config/algorithm/_base.yaml` defines inline. `${ref:llm}`, `${problem_context}`, `${prompts.dir}`, `${prompt_fetcher}` mirror `_base.yaml`'s existing `mutation_operator` node verbatim.)

- [ ] **Step 4: Run tests to verify they pass**

Use the `/run-tests` skill targeting `tests/evolution/test_structured_diff_operator.py`. Expected: 4 passed.

- [ ] **Step 5: Lint, then commit (after user approval)**

Run: `/home/jovyan/.mlspace/envs/evo/bin/ruff check gigaevo/evolution/mutation/structured_diff.py tests/evolution/test_structured_diff_operator.py && /home/jovyan/.mlspace/envs/evo/bin/ruff format --check gigaevo/evolution/mutation/structured_diff.py tests/evolution/test_structured_diff_operator.py`

Ask the user for commit approval. After approval:

```bash
rtk git add gigaevo/evolution/mutation/structured_diff.py config/mutation/structured_diff_chains.yaml tests/evolution/test_structured_diff_operator.py
rtk git commit -m "feat(mutation): StructuredDiffMutationOperator + structured_diff_chains config group"
```

---

### Task 5: `ParseJsonProgram` stage

**Files:**
- Create: `gigaevo/programs/stages/json_genome.py`
- Test: `tests/stages/test_json_genome.py`

**Interfaces:**
- Consumes: `Stage` (`gigaevo/programs/stages/base.py` — ctor is `__init__(self, *, timeout: float)`), `VoidInput` (`gigaevo/programs/core_types.py`), `Box` (`gigaevo/programs/stages/common.py`), `StageRegistry` (`gigaevo/programs/stages/stage_registry.py`).
- Produces: `ParseJsonProgram(timeout=...)` with `InputsModel = VoidInput`, `OutputModel = Box[Any]`; `compute(program)` returns `Box[Any](data=<parsed json>)` or raises `ValueError` prefixed `json_parse_error:` (arm A's failure-accounting grep key).

- [ ] **Step 1: Write the failing test**

`tests/stages/test_json_genome.py`:

```python
"""Tests for ParseJsonProgram: JSON-document genomes parse instead of executing."""

from __future__ import annotations

import pytest

from gigaevo.programs.program import Program
from gigaevo.programs.stages.json_genome import ParseJsonProgram


def _stage() -> ParseJsonProgram:
    return ParseJsonProgram(timeout=30.0)


async def test_parses_json_document_into_box():
    out = await _stage().compute(Program(code='{"steps": [{"number": 1}]}', iteration=0))
    assert out.data == {"steps": [{"number": 1}]}


async def test_invalid_json_raises_labeled_error():
    with pytest.raises(ValueError, match="json_parse_error"):
        await _stage().compute(Program(code="{'steps': 1}", iteration=0))


async def test_empty_code_raises():
    with pytest.raises(ValueError, match="empty"):
        await _stage().compute(Program(code="   ", iteration=0))
```

- [ ] **Step 2: Run test to verify it fails**

Use the `/run-tests` skill targeting `tests/stages/test_json_genome.py`.
Expected: FAIL — `ModuleNotFoundError: No module named 'gigaevo.programs.stages.json_genome'`.

- [ ] **Step 3: Write the implementation**

`gigaevo/programs/stages/json_genome.py`:

```python
"""Stage for JSON-document genomes: parse Program.code instead of executing it."""

from __future__ import annotations

import json
from typing import Any

from gigaevo.programs.core_types import VoidInput
from gigaevo.programs.program import Program
from gigaevo.programs.stages.base import Stage
from gigaevo.programs.stages.common import Box
from gigaevo.programs.stages.stage_registry import StageRegistry


@StageRegistry.register(description="Parse a JSON-document genome into a dict")
class ParseJsonProgram(Stage):
    """Replaces both ValidateCodeStage (parse is the syntax gate) and
    CallProgramFunction (the parsed document is the validator payload) for
    genomes that are data, not Python."""

    InputsModel = VoidInput
    OutputModel = Box[Any]

    async def compute(self, program: Program) -> Box[Any]:
        code = program.code or ""
        if not code.strip():
            raise ValueError("Genome is empty")
        try:
            payload = json.loads(code)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"json_parse_error: line {e.lineno} col {e.colno}: {e.msg}"
            ) from e
        return self.OutputModel(data=payload)
```

If `@StageRegistry.register` or the `compute` signature differs from `gigaevo/programs/stages/validation.py`'s `ValidateCodeStage` (the reference implementation), mirror `validation.py` exactly.

- [ ] **Step 4: Run tests to verify they pass**

Use the `/run-tests` skill targeting `tests/stages/test_json_genome.py`. Expected: 3 passed.

- [ ] **Step 5: Lint, then commit (after user approval)**

Run: `/home/jovyan/.mlspace/envs/evo/bin/ruff check gigaevo/programs/stages/json_genome.py tests/stages/test_json_genome.py && /home/jovyan/.mlspace/envs/evo/bin/ruff format --check gigaevo/programs/stages/json_genome.py tests/stages/test_json_genome.py`

Ask the user for commit approval. After approval:

```bash
rtk git add gigaevo/programs/stages/json_genome.py tests/stages/test_json_genome.py
rtk git commit -m "feat(stages): ParseJsonProgram for JSON-document genomes"
```

---

### Task 6: `DirectoryProgramLoader` glob pattern parameter

**Files:**
- Modify: `gigaevo/problems/initial_loaders.py` (the `DirectoryProgramLoader` class, ~lines 17-40)
- Modify: `config/loader/directory.yaml`
- Test: `tests/problems/test_initial_loaders.py`

**Interfaces:**
- Produces: `DirectoryProgramLoader(problem_dir, pattern: str = "*.py")` — default unchanged for every existing problem; `pattern: "*.json"` is set by `config/pipeline/summarizer_json.yaml` in Task 8.

- [ ] **Step 1: Write the failing test**

`tests/problems/test_initial_loaders.py`:

```python
"""Tests for DirectoryProgramLoader glob pattern."""

from __future__ import annotations

from gigaevo.problems.initial_loaders import DirectoryProgramLoader


class _Storage:
    def __init__(self):
        self.added = []

    async def add(self, program):
        self.added.append(program)


def _make_problem_dir(tmp_path):
    initial = tmp_path / "initial_programs"
    initial.mkdir()
    (initial / "seed.py").write_text("def entrypoint(): return 1\n")
    (initial / "chain.json").write_text('{"steps": []}')
    return tmp_path


async def test_default_pattern_loads_only_python(tmp_path):
    problem_dir = _make_problem_dir(tmp_path)
    programs = await DirectoryProgramLoader(problem_dir).load(_Storage())
    assert [p.metadata["strategy_name"] for p in programs] == ["seed"]


async def test_json_pattern_loads_only_json(tmp_path):
    problem_dir = _make_problem_dir(tmp_path)
    loader = DirectoryProgramLoader(problem_dir, pattern="*.json")
    programs = await loader.load(_Storage())
    assert [p.metadata["strategy_name"] for p in programs] == ["chain"]
    assert programs[0].code == '{"steps": []}'


async def test_missing_dir_returns_empty(tmp_path):
    assert await DirectoryProgramLoader(tmp_path, pattern="*.json").load(_Storage()) == []
```

- [ ] **Step 2: Run test to verify it fails**

Use the `/run-tests` skill targeting `tests/problems/test_initial_loaders.py`.
Expected: FAIL — `TypeError: DirectoryProgramLoader.__init__() got an unexpected keyword argument 'pattern'`.

- [ ] **Step 3: Implement**

In `gigaevo/problems/initial_loaders.py`, change only these lines of `DirectoryProgramLoader`:

```python
class DirectoryProgramLoader:
    def __init__(self, problem_dir: str | Path, pattern: str = "*.py"):
        self.problem_dir = Path(problem_dir)
        self.pattern = pattern

    async def load(self, storage: ProgramStorage) -> list[Program]:
        initial_dir = self.problem_dir / "initial_programs"
        if not initial_dir.exists():
            return []
        python_files = list(initial_dir.glob(self.pattern))
```

(The rest of `load()` — the tqdm loop, metadata dict, silent `continue` — stays byte-identical.)

`config/loader/directory.yaml` becomes:

```yaml
# @package _global_

program_loader:
  _target_: gigaevo.problems.initial_loaders.DirectoryProgramLoader
  problem_dir: ${problem.dir}
  pattern: "*.py"
```

- [ ] **Step 4: Run tests to verify they pass**

Use the `/run-tests` skill targeting `tests/problems/test_initial_loaders.py`. Expected: 3 passed.

- [ ] **Step 5: Lint, then commit (after user approval)**

Run: `/home/jovyan/.mlspace/envs/evo/bin/ruff check gigaevo/problems/initial_loaders.py tests/problems/test_initial_loaders.py && /home/jovyan/.mlspace/envs/evo/bin/ruff format --check gigaevo/problems/initial_loaders.py tests/problems/test_initial_loaders.py`

Ask the user for commit approval. After approval:

```bash
rtk git add gigaevo/problems/initial_loaders.py config/loader/directory.yaml tests/problems/test_initial_loaders.py
rtk git commit -m "feat(problems): configurable glob pattern for DirectoryProgramLoader"
```

---

### Task 7: `rouge_l_f1`

**Files:**
- Create: `problems/chains/summarizer/rouge.py`
- Test: `tests/problems/test_summarizer_rouge.py`

**Interfaces:**
- Produces: `rouge_l_f1(candidate: str, reference: str) -> float` — word-level LCS F1, lowercased whitespace tokenization. Task 8's `validate.py` imports it as `from problems.chains.summarizer.rouge import rouge_l_f1`.

- [ ] **Step 1: Write the failing test**

`tests/problems/test_summarizer_rouge.py`:

```python
"""Tests for word-level ROUGE-L F1."""

from __future__ import annotations

import pytest

from problems.chains.summarizer.rouge import rouge_l_f1


def test_identical_is_one():
    assert rouge_l_f1("the cat sat", "the cat sat") == pytest.approx(1.0)


def test_disjoint_is_zero():
    assert rouge_l_f1("alpha beta", "gamma delta") == 0.0


def test_partial_overlap():
    assert rouge_l_f1("the cat sat", "the cat") == pytest.approx(0.8)


def test_empty_strings_are_zero():
    assert rouge_l_f1("", "the cat") == 0.0
    assert rouge_l_f1("the cat", "") == 0.0
    assert rouge_l_f1("", "") == 0.0


def test_case_insensitive():
    assert rouge_l_f1("The Cat", "the cat") == pytest.approx(1.0)


def test_subsequence_not_substring():
    assert rouge_l_f1("a x b y c", "a b c") == pytest.approx(0.75)


def test_russian_tokens():
    assert rouge_l_f1("кот сидел на крыше", "кот сидел на крыше") == pytest.approx(1.0)
```

(`test_partial_overlap`: LCS=2, precision 2/3, recall 1 → F1 = 0.8. `test_subsequence_not_substring`: LCS=3, precision 3/5, recall 1 → F1 = 0.75.)

- [ ] **Step 2: Run test to verify it fails**

Use the `/run-tests` skill targeting `tests/problems/test_summarizer_rouge.py`.
Expected: FAIL — `ModuleNotFoundError: No module named 'problems.chains.summarizer'`.

- [ ] **Step 3: Write the implementation**

`problems/chains/summarizer/rouge.py`:

```python
"""Word-level ROUGE-L F1 (LCS over lowercased whitespace tokens)."""

from __future__ import annotations


def rouge_l_f1(candidate: str, reference: str) -> float:
    cand = candidate.lower().split()
    ref = reference.lower().split()
    if not cand or not ref:
        return 0.0
    dp = [[0] * (len(ref) + 1) for _ in range(len(cand) + 1)]
    for i, c in enumerate(cand):
        for j, r in enumerate(ref):
            dp[i + 1][j + 1] = dp[i][j] + 1 if c == r else max(dp[i][j + 1], dp[i + 1][j])
    lcs = dp[-1][-1]
    if lcs == 0:
        return 0.0
    precision = lcs / len(cand)
    recall = lcs / len(ref)
    return 2 * precision * recall / (precision + recall)
```

- [ ] **Step 4: Run tests to verify they pass**

Use the `/run-tests` skill targeting `tests/problems/test_summarizer_rouge.py`. Expected: 7 passed.

- [ ] **Step 5: Lint, then commit (after user approval)**

Run: `/home/jovyan/.mlspace/envs/evo/bin/ruff check problems/chains/summarizer/rouge.py tests/problems/test_summarizer_rouge.py && /home/jovyan/.mlspace/envs/evo/bin/ruff format --check problems/chains/summarizer/rouge.py tests/problems/test_summarizer_rouge.py`

Ask the user for commit approval. After approval:

```bash
rtk git add problems/chains/summarizer/rouge.py tests/problems/test_summarizer_rouge.py
rtk git commit -m "feat(summarizer): word-level ROUGE-L F1 metric"
```

---

### Task 8: `problems/chains/summarizer/` problem + pipeline config + arm-A prompts

**Files:**
- Create: `problems/chains/summarizer/shared_config.py`
- Create: `problems/chains/summarizer/validate.py`
- Create: `problems/chains/summarizer/metrics.yaml`
- Create: `problems/chains/summarizer/task_description.txt`
- Create: `problems/chains/summarizer/pipeline.py`
- Create: `problems/chains/summarizer/prompts/mutation/system.txt` + `user.txt` (arm A only)
- Copy in: `problems/chains/summarizer/initial_programs/chain_{1,2,3,4}step.json`, `problems/chains/summarizer/data/eval.jsonl`
- Create: `config/pipeline/summarizer_json.yaml`
- Test: `tests/problems/test_summarizer_problem.py`

**Interfaces:**
- Consumes: `rouge_l_f1` (Task 7), `ParseJsonProgram` (Task 5), `run_chain_on_dataset` (`problems/chains/chain_runner.py`, sync wrapper: `(chain, client, dataset, outer_context_builder, tool_registry=None, ..., max_concurrent=300, runner_config=None)`), `LLMClient`/`CallLog` (`problems/chains/client.py`), `ChainSpec` (`problems/chains/types.py`).
- Produces: launchable problem `problem.name=chains/summarizer` with `pipeline=summarizer_json`. `validate(chain_doc: dict) -> (metrics, artifact)` per the frozen evaluate/validate tuple contract; no prints (route detail via the artifact).

- [ ] **Step 1: Copy seeds and eval data**

```bash
mkdir -p problems/chains/summarizer/initial_programs problems/chains/summarizer/data problems/chains/summarizer/prompts/mutation
cp carl_pack/summarizer-evolution/chains/chain_1step.json carl_pack/summarizer-evolution/chains/chain_2step.json carl_pack/summarizer-evolution/chains/chain_3step.json carl_pack/summarizer-evolution/chains/chain_4step.json problems/chains/summarizer/initial_programs/
cp carl_pack/summarizer-evolution/data/eval.jsonl problems/chains/summarizer/data/eval.jsonl
```

- [ ] **Step 2: Write the failing test**

`tests/problems/test_summarizer_problem.py`:

```python
"""Structural tests for the summarizer problem package (no network)."""

from __future__ import annotations

import json
from pathlib import Path

from mmar_carl.chain import ReasoningChain

from gigaevo.chains.dag_changes import AllowedDagChanges
from problems.chains.summarizer.shared_config import load_dataset, outer_context_builder
from problems.chains.summarizer.validate import INVALID_METRICS, validate

PROBLEM_DIR = Path("problems/chains/summarizer")


def test_seed_genomes_parse_and_carry_platform_extras():
    seeds = sorted(PROBLEM_DIR.glob("initial_programs/*.json"))
    assert len(seeds) == 4
    for seed in seeds:
        doc = json.loads(seed.read_text())
        chain = ReasoningChain.from_dict(doc, use_typed_steps=True)
        assert chain.steps
        assert doc["task_description"]
        assert doc["steps"][-1]["is_output_step"] is True


def test_seeds_are_valid_diff_parents():
    changes = AllowedDagChanges()
    parents = {
        "A": (PROBLEM_DIR / "initial_programs" / "chain_2step.json").read_text(),
        "B": (PROBLEM_DIR / "initial_programs" / "chain_3step.json").read_text(),
    }
    schema = changes.build_schema(parents)
    assert schema.json_schema["title"] == "chain_dag_diff"
    assert changes.render_parents(parents)


def test_dataset_rows_have_required_keys():
    rows = load_dataset()
    assert len(rows) == 8
    for row in rows:
        assert row["input"] and row["task"] and row["expected"]
        context = outer_context_builder(row)
        assert row["input"] in context and row["task"] in context


def test_validate_rejects_broken_genome_without_network():
    metrics, artifact = validate({"steps": "garbage"})
    assert metrics == INVALID_METRICS
    assert artifact["error"].startswith("carl_validation_error")
```

- [ ] **Step 3: Run test to verify it fails**

Use the `/run-tests` skill targeting `tests/problems/test_summarizer_problem.py`.
Expected: FAIL — `ModuleNotFoundError: No module named 'problems.chains.summarizer.shared_config'`.

- [ ] **Step 4: Write the problem package**

`problems/chains/summarizer/shared_config.py`:

```python
"""Shared config for the CARL summarizer chain problem."""

from __future__ import annotations

import json
import os
from pathlib import Path

PROBLEM_DIR = Path(__file__).resolve().parent

_CHAIN_URL = os.environ.get("SUMMARIZER_CHAIN_URL", "http://10.232.30.185:4000/v1")

LLM_CONFIG = {
    "model": "Qwen/Qwen3-8B",
    "max_cost": 10.0,
    "model_pricing": {"prompt": 0.05, "completion": 0.25},
    "generation_kwargs": {
        "temperature": 0.6,
        "top_p": 0.95,
        "max_tokens": 8192,
        "extra_body": {"top_k": 20},
    },
    "client_kwargs": {"api_key": "sk-gigaevo", "base_url": _CHAIN_URL},
}


def get_llm_config() -> dict:
    return dict(LLM_CONFIG)


def load_dataset() -> list[dict]:
    rows = []
    with (PROBLEM_DIR / "data" / "eval.jsonl").open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def outer_context_builder(sample: dict) -> str:
    return f"Задание: {sample['task']}\n\nТекст:\n{sample['input']}"
```

(Chain-executor endpoint mirrors `problems/chains/hover/shared_config.py`; before launch, Task 10 verifies the URL serves `Qwen/Qwen3-8B` and adjusts `SUMMARIZER_CHAIN_URL` per `experiments/infrastructure.yaml` if that box was reassigned.)

`problems/chains/summarizer/validate.py`:

```python
"""Score a CARL chain wire-JSON genome: mean ROUGE-L F1 on the summarizer eval set."""

from __future__ import annotations

from statistics import mean

from mmar_carl.chain import ReasoningChain

from problems.chains.chain_runner import run_chain_on_dataset
from problems.chains.client import LLMClient
from problems.chains.summarizer.rouge import rouge_l_f1
from problems.chains.summarizer.shared_config import (
    get_llm_config,
    load_dataset,
    outer_context_builder,
)
from problems.chains.types import ChainSpec

INVALID_METRICS = {
    "fitness": 0.0,
    "is_valid": 0,
    "n_steps": 0,
    "completion_tokens": 0,
}


def validate(chain_doc: dict):
    try:
        chain = ReasoningChain.from_dict(chain_doc, use_typed_steps=True)
        if not chain.steps:
            raise ValueError("chain has no steps")
    except Exception as e:
        return (dict(INVALID_METRICS), {"error": f"carl_validation_error: {e}"})

    dataset = load_dataset()
    client = LLMClient(**get_llm_config())
    spec = ChainSpec(
        system_prompt=chain_doc.get("task_description", ""),
        steps=list(chain.steps),
    )
    results = run_chain_on_dataset(
        spec, client, dataset, outer_context_builder, max_concurrent=8
    )

    scores = [
        rouge_l_f1(result.final_output or "", sample["expected"])
        for sample, result in zip(dataset, results)
    ]
    metrics = {
        "fitness": mean(scores) if scores else 0.0,
        "is_valid": 1,
        "n_steps": len(chain.steps),
        "completion_tokens": sum(log.completion_tokens for log in client.call_logs),
    }
    artifact = {
        "per_sample": [
            {"score": round(score, 4), "output": (result.final_output or "")[:200]}
            for score, result in zip(scores, results)
        ]
    }
    return (metrics, artifact)
```

`problems/chains/summarizer/metrics.yaml`:

```yaml
specs:
  fitness:
    description: "Mean ROUGE-L F1 of the chain's final output vs the reference summary"
    decimals: 3
    is_primary: true
    higher_is_better: true
    lower_bound: 0.0
    upper_bound: 1.0
    include_in_prompts: true
    significant_change: 0.005
    sentinel_value: -1000.0
  is_valid:
    description: "Whether the genome parsed into a CARL chain and executed (1 valid, 0 invalid)"
    decimals: 0
    is_primary: false
    higher_is_better: true
    lower_bound: 0.0
    upper_bound: 1.0
    include_in_prompts: true
    significant_change: 1.0
    sentinel_value: 0.0
  n_steps:
    description: "Number of steps in the chain"
    decimals: 0
    is_primary: false
    higher_is_better: false
    lower_bound: 0.0
    upper_bound: 8.0
    include_in_prompts: true
    significant_change: 1.0
    sentinel_value: 0.0
  completion_tokens:
    description: "Total completion tokens spent executing the chain on the eval set"
    decimals: 0
    is_primary: false
    higher_is_better: false
    include_in_prompts: true
    significant_change: 500.0
    sentinel_value: 0.0
```

`problems/chains/summarizer/task_description.txt`:

```
- Genome: a CARL reasoning-chain wire JSON — steps with title/aim/stage_action/reasoning_questions, explicit dependencies between steps, 1..8 steps, last step is the output step.
- The chain is executed by a small LLM over 8 Russian text-summarization samples; the final step's answer is the produced summary.
- Goal: chains whose final outputs match the reference summaries as closely as possible.
- Prefer cheaper chains (fewer steps, fewer completion tokens) at equal quality.
```

`problems/chains/summarizer/pipeline.py`:

```python
"""Pipeline builder for JSON chain genomes: parse instead of execute."""

from gigaevo.entrypoint.constants import DEFAULT_SIMPLE_STAGE_TIMEOUT
from gigaevo.entrypoint.default_pipelines import DefaultPipelineBuilder
from gigaevo.entrypoint.evolution_context import EvolutionContext
from gigaevo.programs.stages.json_genome import ParseJsonProgram


class JsonChainPipelineBuilder(DefaultPipelineBuilder):
    """ValidateCodeStage and CallProgramFunction both become ParseJsonProgram:
    parsing is the syntax gate, and the parsed document is the validator payload."""

    def __init__(
        self,
        ctx: EvolutionContext,
        *,
        dag_timeout: float = 3600.0,
        stage_timeout: float = DEFAULT_SIMPLE_STAGE_TIMEOUT,
    ):
        super().__init__(ctx, dag_timeout=dag_timeout, stage_timeout=stage_timeout)
        self.replace_stage(
            "ValidateCodeStage", lambda: ParseJsonProgram(timeout=self._stage_timeout)
        )
        self.replace_stage(
            "CallProgramFunction", lambda: ParseJsonProgram(timeout=self._stage_timeout)
        )
```

`config/pipeline/summarizer_json.yaml` (modeled verbatim on `config/pipeline/spherical_general.yaml`):

```yaml
# @package _global_
# Pipeline: default evolution pipeline for JSON chain genomes — ValidateCodeStage and
# CallProgramFunction are swapped for ParseJsonProgram, and initial programs load as *.json.
# Launch: python run.py problem.name=chains/summarizer pipeline=summarizer_json ...

evolution_context:
  _target_: gigaevo.entrypoint.evolution_context.EvolutionContext
  problem_ctx: ${problem_context}
  llm_wrapper: ${ref:llm}
  storage: ${program_storage}
  prompts_dir: ${prompts.dir}
  prompt_fetcher: ${prompt_fetcher}
  memory_provider: ${ref:memory::provider}

pipeline_builder:
  _target_: problems.chains.summarizer.pipeline.JsonChainPipelineBuilder
  ctx: ${evolution_context}
  stage_timeout: ${stage_timeout}
  dag_timeout: ${dag_timeout}

dag_blueprint:
  _target_: gigaevo.config.helpers.build_dag_from_builder
  builder: ${pipeline_builder}

program_loader:
  pattern: "*.json"
```

Arm-A prompt overrides (the package-default `gigaevo/prompts/mutation/system.txt` mandates "code is Python source, not JSON", so raw-JSON evolution needs its own mutation prompts; every other agent falls back to package defaults per-file). Both files are near-copies of the stock `gigaevo/prompts/mutation/{system,user}.txt` — ROLE / EVIDENCE INPUTS / OUTPUT RULES 1–2 essentially verbatim (the stock structured-output schema with `insights_used`/`card_ids_used`/`insight_ids_used`/`changes`/`justification` applies unchanged, since arm A runs the stock `LLMMutationOperator`). Deltas: "Python program" → "chain genome (CARL wire JSON)" in ROLE and CONTEXT; the same light chain adaptations to ARCHETYPE items 4/5/8 and EXECUTION PRINCIPLES as arm B's prompt (the two arms' shared sections match each other exactly — mirror-baseline rule); rule-2 examples swapped from tabular to the same chain-flavored ones as arm B; and rule 3 replaced by the wire-JSON genome format:

`problems/chains/summarizer/prompts/mutation/system.txt`:

```
## ROLE

You are the **mutation operator** in an LLM-guided evolutionary algorithm. Each call gives you one or more labeled parent chain genomes (in the user message) — CARL reasoning-chain wire-JSON documents, DAGs of LLM steps executed by a small model — and an evidence pack about their lineage and the run. You produce ONE child chain genome — when given a single parent, a *targeted edit* of that parent; when given ≥2 parents, a *coherent crossover* that selects exactly one focal base and borrows only evidence-justified, cited mechanisms from one or more remaining donors — not a from-scratch rewrite — plus structured fields explaining the edit. Evidence drives the edit; do not invent.

When ≥2 parents are present, **parent order is arbitrary** (sampling order, not fitness or quality). Choose exactly one parent as the *base* — the one whose top-level organization, step structure, and wiring you preserve — and treat every other parent as a *donor*. Make the choice explicit by citation: `insights_used` must include at least one base-parent evidence item (insight / intra cluster / metric / stats trigger) and one `parent:<N> code:<symbol-or-anchor>` for each mechanism borrowed from any donor.

The TASK the chain is solving is described in CONTEXT at the bottom. You are NOT writing a fresh solution to that task; you are improving from the parent(s).

## EVIDENCE INPUTS (user message)

Absent slots are omitted — do not fabricate content.

- **Program Metrics** — parent's measured metrics with target direction (↑/↓ better). Fitness drives selection.
- **Program Insights** — numbered `N. [type][tag][severity]` items from an upstream analyst, each carrying a code anchor (with its source), a mechanism hypothesis (`mechanism(<source>): …`, sometimes with a `card: <id>` attribution), and a concrete substitute. The list is priority-ordered: item 1 is the analyst's top recommendation. **If the list is non-empty, act on insight 1 or state in `justification` why not and act on another; `insights_used` lists which. If the list is empty, the mutation must instead cite ≥1 other evidence item (intra cluster / stats trigger) in `insights_used`.** A `card: <id>` attribution marks a cross-population transposition, not a lever proven on this parent — it earns no precedence over a better-grounded parent-native insight, so if insight 1 is card-sourced and a native insight fits this parent better, act on the native one and record that in `justification`. Tag → action:
  - `beneficial` → PRESERVE / EXTEND
  - `harmful` → REMOVE / REPLACE
  - `fragile` → ROBUSTIFY / add guards
  - `rigid` → PARAMETERIZE / TUNE
  - `neutral` → low priority
- **Evolutionary Statistics** — run-level signals: trend (rising/flat/falling), iters-since-best, archive percentile (100=best, direction-aware), invalid streak (max consecutive in window), archive worst/median/best. The archive line and percentile appear only once enough valid programs exist.
- **Intra Memory** — per-parent lineage card (under its own `## Intra Memory` header): this parent's tried-strategy clusters with verdicts (improved/neutral/regressed/failed) and failure notes. This card also conditions which cross-population memory cards the analyst was shown, so any `card: <id>` attribution above was already filtered against this lineage — treat such cards as lineage-aware, not generic.
- **Task Artifact** — optional final un-headed block: task-specific evidence rendered by the evaluation harness (only on problems that emit artifacts).

**Insights are the primary driver of WHAT to change; archetype only constrains HOW MUCH structural novelty to introduce.**

## ARCHETYPE — apply gates FIRST, then pick exactly ONE

**Gates (apply in order; a hard gate overrides the frontier-awareness shaper below):**
- Archive percentile <25 → Exploration only (refining a known-inferior basin is wasted budget).
- Archive percentile ≥75 → all archetypes eligible per evidence.
- Middle band (25 ≤ percentile <75) → prefer Hybrid; pick Exploitation only when intra shows a verified `improved` cluster that has not yet been pushed further.
- Frontier awareness: use the archive worst/median/best and current program percentile to judge early vs frontier phase. Top-percentile parents may still pick structural archetypes when the archive is shallow. Do not derive hard thresholds from task-context prose.
- Noise filter: a `falling`/`flat` trend flagged as having too few valid iterations for a reliable signal is noise — do NOT force Exploration on that basis alone.

**Pick exactly ONE archetype from the gate-permitted set:**

EXPLOITATION:
1. **Precision Optimization** — fine-tune proven patterns; minimal risk (targeted edits to existing steps).
2. **Proven Pattern Extension** — generalise an already-improved strategy.
3. **Harmful Pattern Removal** — eliminate a documented failure mode (drop or replace the offending step).

EXPLORATION:
4. **Computational Reinvention** — novel chain topology or decomposition of the task.
5. **Solution Space Exploration** — change the SET of admissible solutions (serial↔parallel wiring, single draft↔competing drafts, add/remove a verification pass).
6. **Approach Synthesis** — combine two distinct evidence-backed mechanisms (e.g. two insights, or an insight + an intra cluster) into one coherent design.

HYBRID:
7. **Guided Innovation** — preserve a proven element, add ONE targeted novelty.
8. **Component Substitution** — replace ONE step (extractor, drafter, verifier, merger, polisher) with an alternative of the same kind in the same slot.

## EXECUTION PRINCIPLES

- One coherent edit per archetype; don't mix Exploit + Explore. Multiple donors do not license multiple independent edits — one coherent edit per archetype still holds across the full parent set.
- Don't re-apply a `regressed`/`failed` cluster without a clear corrective mechanism that addresses the named failure mode.
- High `invalid_streak` → simplify (fewer steps, tighter aims) before broader restructures.
- Step aims must be concrete and executable by a small model; avoid vague instructions.
- Write step content in the same language as the parent steps.

## OUTPUT RULES

Output must be a single JSON object conforming to the structured-output schema, which defines every field and its meaning. No prose, no preamble, no markdown/code fences. Beyond what the schema already states:

1. **Cite, never invent.** Every `insights_used` entry references real evidence:
   - `"insight: <type> — <anchor>"` (primary; expected on most mutations)
   - `"tried: <label>"` (intra cluster to extend or correct)
   - `"plateau: <trigger>"` / `"invalid_streak: <n>"` (stats trigger)
   - `"parent:<N> code:<symbol-or-anchor>"` (≥2-parent mode; proves the donor mechanism exists, not that it works)
   Same for `justification` and each `changes[i].explanation`: cite the item by its label/anchor. In ≥2-parent mode, `insights_used` must include at least one evidence citation from the chosen base parent and one `parent:<N> code:<symbol-or-anchor>` citation for each donor mechanism used; every such donor citation must be paired with a non-code evidence citation justifying the borrow. Do not list uncited donor mechanisms in `changes`. Whenever you act on an insight that carries a `card: <id>` attribution, copy that id into `card_ids_used` — that field is the only signal that credits the memory card, and `insights_used` does not echo it. Whenever you act on a numbered `## Program Insights` item, also cite it in `insight_ids_used` as its parent number (per the `=== Parent N ===` label) plus the insight's `N.` number in that parent's list — each parent's list numbers from 1, so both parts are required. Never invent numbers.
2. **Each `changes[i].description` is a *falsifiable causal hypothesis*, not a description of the diff.**

   Form: one short sentence (~20 words) shaped `<what changed, including old→new>: <why-it-transfers>`. Use a natural verb that fits the operation (`added`, `dropped`, `rewired`, `rewrote`, `merged`, …) and name the actual step/wiring touched.

   `<why-it-transfers>` must state a falsifiable causal hypothesis linking a specific problem property to why the lever bites.
   - **Tautology test**: *would the clause still be true if the cited property were absent?* If yes, rewrite.
   - Two patterns that satisfy:
     - **Failure-mode bypass** — name the failure pattern the lever escapes (e.g. `the extract step emits terse fragments that starve the drafter of context`).
     - **Constraint match** — name the property that makes the new structure correct (e.g. `the executor is a small model, so multi-purpose aims in one step get partially ignored`).
   - Draw the trigger from TASK CONTEXT / METRICS (or run stats like `invalid_streak`). Prefer a concrete value or context key over a qualitative descriptor.
   - Trigger source classes: value bound, input/reference structure, step-interaction effect, optimization landscape, metric/evaluation quirk, computational constraint, domain constraint.

   Forbidden — these *describe the action* instead of *explaining why it works*:
   - Tautology (true regardless of cited property): `verification improves faithfulness`, `prevents drift`, `makes aims clearer`.
   - Restatement of the diff: `adds a step`, `merges two steps`, `rewires dependencies`.
   - Goal restatement: `improves the score`, `produces better summaries`, `aligns output with reference`.

   Pure aim-wording tweaks with no problem-property hypothesis must say so explicitly: `rewords <step> aim; weak transfer-evidence`.

   GOOD: `"Rewired the final polish step to read the raw source text alongside the draft: each paraphrase hop drifts from source wording that the metric scores; re-grounding the last hop restores it."`
   GOOD: `"Dropped the keyword-extraction step and fed its consumer the raw text: the extractor emits terse fragments that starve the drafter of context; drafting from the source keeps entity coverage."`

   BAD→GOOD pair:
   BAD:  `"Added a verification step after drafting: improves summary faithfulness."` (goal restatement)
   GOOD: `"Added a verify step comparing draft to source: the small executor invents connective facts on long inputs; an explicit check forces re-grounding before output."`

   When ≥2 distinct changes go together, emit ≥2 separate items in `changes`, one per change. A coherent rewrite of one step's content fields is ONE item.
3. **`code` is one COMPLETE CARL wire-format JSON document — not Python, not a fragment, not a diff.** Strict JSON: double quotes, no comments, no trailing commas, no embedded templates or format examples. The document has a top-level `steps` array; every step carries `number` (1-based, contiguous — renumber after inserts/deletes), `title`, `aim`, `stage_action`, `reasoning_questions`, `example_reasoning`, `dependencies` (array of earlier step numbers only), and `step_type` set to `llm`. The last step carries `is_output_step` set to true. Chains have 1 to 8 steps; `title` and `aim` must be non-empty. Copy every other top-level key (`format_version`, `carl_version`, `version`, `max_workers`, `enable_progress`, `task_description`, `search_config`, `metadata`) unchanged from the base parent.

## CONTEXT (the TASK the CHAIN is solving — background for understanding the parent)

{task_description}

Available metrics:
{metrics_description}
```

`problems/chains/summarizer/prompts/mutation/user.txt`:

```
Produce the next-generation chain for the parent(s) below. Use the evidence packed into each parent block (Program Metrics → Program Insights → Evolutionary Statistics → Intra Memory).

{parent_blocks}

---

Pick ONE archetype, cite the specific insights / stats triggers that motivated each change in `insights_used` and `justification`, and emit a single coherent mutation following the OUTPUT RULES in the system prompt — the child as one complete JSON document in `code`.
```

(No literal `{`/`}` beyond the placeholders in either file — rule 3 deliberately describes the genome keys in prose with backticks instead of showing a JSON example, both to respect brace-escaping and the no-hardcoded-examples-in-prompts rule.)

- [ ] **Step 5: Run tests to verify they pass**

Use the `/run-tests` skill targeting `tests/problems/test_summarizer_problem.py`. Expected: 4 passed.

If `test_seed_genomes_parse_and_carry_platform_extras` fails on a missing `is_output_step` or `task_description` in a pack seed, fix the copied seed files in `initial_programs/` (add the missing key, mirroring `chain_2step.json` which is known-good) — do not weaken the test.

- [ ] **Step 6: Lint, then commit (after user approval)**

Run: `/home/jovyan/.mlspace/envs/evo/bin/ruff check problems/chains/summarizer tests/problems/test_summarizer_problem.py && /home/jovyan/.mlspace/envs/evo/bin/ruff format --check problems/chains/summarizer tests/problems/test_summarizer_problem.py`

Ask the user for commit approval. After approval:

```bash
rtk git add problems/chains/summarizer config/pipeline/summarizer_json.yaml tests/problems/test_summarizer_problem.py
rtk git commit -m "feat(problems): CARL summarizer chain problem with JSON-genome pipeline"
```

---

### Task 9: Docs sync

**Files:**
- Modify: `docs/ARCHITECTURE.md`
- Modify: `experiments/carl_dag_diff_mutation_design.md` (§4.5)

**Interfaces:** none (documentation).

- [ ] **Step 1: Update `docs/ARCHITECTURE.md`**

Read the package-layout section and add entries matching its existing format (bullet/table style as found):

- `gigaevo/chains/` — genome-family diff vocabularies for structured mutation; currently `AllowedDagChanges` (CARL reasoning-chain positional-slot diffs).
- Under the mutation description: `StructuredDiffMutationOperator` (`gigaevo/evolution/mutation/structured_diff.py`) — single-call, schema-constrained diff mutation behind the genome-agnostic `AllowedChanges` contract (`gigaevo/evolution/mutation/allowed_changes.py`); enabled with `+mutation=structured_diff_chains`.
- Under stages (if a stage inventory exists in the doc): `ParseJsonProgram` — JSON-document genomes; wired by `pipeline=summarizer_json`.

While in the file, polish (don't append) any stale text in the sections you touch, per the project doc-drift rule.

- [ ] **Step 2: Update the design doc's failure taxonomy**

In `experiments/carl_dag_diff_mutation_design.md` §4.5, add the label `diff_schema_error` (post-decoding `TypeAdapter` rejection — expected ~never under guided decoding; counted separately from `llm_call_error` so a proxy that silently stops enforcing the grammar is visible).

- [ ] **Step 3: Commit (after user approval)**

Ask the user for commit approval. After approval:

```bash
rtk git add docs/ARCHITECTURE.md experiments/carl_dag_diff_mutation_design.md
rtk git commit -m "docs: architecture entries for gigaevo/chains + structured diff mutation"
```

---

### Task 10: Smoke gauntlet (config, executor endpoint, seed band, 5-mutant runs)

**Files:**
- Create: `experiments/carl_diff_smoke_seed_rouge.py`

No new framework code; this task gates the launch. Run everything from the repo root with:

```bash
export OPENAI_API_KEY=sk-gigaevo
export NO_PROXY="$NO_PROXY,10.232.89.98,10.232.30.185"
PY=/home/jovyan/.mlspace/envs/evo/bin/python3
```

- [ ] **Step 1: Config previews for both arms**

```bash
$PY run.py problem.name=chains/summarizer pipeline=summarizer_json memory=none max_mutants=5 --cfg job > /tmp/claude-1000/-mnt-virtual-ai0001071-04017-SR004-nfs1-CFS-SR008-workspace-mathemage-gigaevo-core-internal/909a1a0b-417f-4fc2-9999-55e9dc07e616/scratchpad/armA_cfg.yaml
$PY run.py problem.name=chains/summarizer pipeline=summarizer_json memory=none max_mutants=5 +mutation=structured_diff_chains --cfg job > /tmp/claude-1000/-mnt-virtual-ai0001071-04017-SR004-nfs1-CFS-SR008-workspace-mathemage-gigaevo-core-internal/909a1a0b-417f-4fc2-9999-55e9dc07e616/scratchpad/armB_cfg.yaml
diff /tmp/claude-1000/-mnt-virtual-ai0001071-04017-SR004-nfs1-CFS-SR008-workspace-mathemage-gigaevo-core-internal/909a1a0b-417f-4fc2-9999-55e9dc07e616/scratchpad/armA_cfg.yaml /tmp/claude-1000/-mnt-virtual-ai0001071-04017-SR004-nfs1-CFS-SR008-workspace-mathemage-gigaevo-core-internal/909a1a0b-417f-4fc2-9999-55e9dc07e616/scratchpad/armB_cfg.yaml
```

Checks: arm A's `mutation_operator._target_` is `...LLMMutationOperator`, arm B's is `...StructuredDiffMutationOperator` with the `AllowedDagChanges` node; `program_loader.pattern` is `*.json` in both; `pipeline_builder._target_` is `JsonChainPipelineBuilder`; the diff between arms is ONLY the mutation_operator node. Record the resolved storage settings shown in the preview for the runbook.

- [ ] **Step 2: Verify the chain-executor endpoint**

```bash
curl -s http://10.232.30.185:4000/v1/models | head -c 400
```

Expected: a model list including `Qwen/Qwen3-8B`. If the box no longer serves it, consult `experiments/infrastructure.yaml`, pick the current Qwen3-8B server, and set `SUMMARIZER_CHAIN_URL` accordingly in every later command (do not edit `shared_config.py` defaults for a box move — the env var exists for this).

- [ ] **Step 3: Seed ROUGE band**

`experiments/carl_diff_smoke_seed_rouge.py`:

```python
"""Smoke: run validate() on each summarizer seed; expect mid-band ROUGE (design S4.6)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from problems.chains.summarizer.validate import validate  # noqa: E402

SEEDS = sorted(Path("problems/chains/summarizer/initial_programs").glob("*.json"))

failures = 0
for seed in SEEDS:
    metrics, artifact = validate(json.loads(seed.read_text()))
    ok = metrics["is_valid"] == 1 and metrics["fitness"] > 0.15
    failures += 0 if ok else 1
    print(
        f"{seed.name:<20} fitness={metrics['fitness']:.3f} "
        f"n_steps={metrics['n_steps']} tokens={metrics['completion_tokens']} "
        f"{'OK' if ok else 'FAIL'}"
    )
    if not ok:
        print(f"  detail: {json.dumps(artifact, ensure_ascii=False)[:400]}")
sys.exit(1 if failures else 0)
```

Run: `$PY experiments/carl_diff_smoke_seed_rouge.py`
Expected: 4 lines, all OK, fitness roughly in the 0.3–0.7 band (design predicts 0.55–0.65 for good seeds; the 0.15 gate only catches broken plumbing). If all four score < 0.15, suspect the executor endpoint or `outer_context_builder` before touching the metric.

- [ ] **Step 4: 5-mutant end-to-end run per arm**

Storage: use the disk/db settings recorded from Step 1's preview; give each arm its own target (e.g. two scratch Redis DBs confirmed free via `gigaevo status`, or two disk dirs). Do NOT flush anything without explicit user approval. Then:

```bash
$PY run.py problem.name=chains/summarizer pipeline=summarizer_json memory=none max_mutants=5 \
  llm_base_url=http://10.232.89.98:4000/v1 model_name="Qwen/Qwen3-235B-A22B-Instruct-2507" \
  <storage overrides for arm A> 2>&1 | tee /tmp/claude-1000/-mnt-virtual-ai0001071-04017-SR004-nfs1-CFS-SR008-workspace-mathemage-gigaevo-core-internal/909a1a0b-417f-4fc2-9999-55e9dc07e616/scratchpad/smokeA.log

$PY run.py problem.name=chains/summarizer pipeline=summarizer_json memory=none max_mutants=5 \
  +mutation=structured_diff_chains \
  llm_base_url=http://10.232.89.98:4000/v1 model_name="Qwen/Qwen3-235B-A22B-Instruct-2507" \
  <storage overrides for arm B> 2>&1 | tee /tmp/claude-1000/-mnt-virtual-ai0001071-04017-SR004-nfs1-CFS-SR008-workspace-mathemage-gigaevo-core-internal/909a1a0b-417f-4fc2-9999-55e9dc07e616/scratchpad/smokeB.log
```

(`llm_base_url`/`model_name` are the required Qwen proxy overrides — the default endpoint 401s. `<storage overrides>` = the exact keys observed in Step 1's preview; fill them in when writing the runbook entry, they are environment state, not code.)

Checks per arm:
- run completes; `gigaevo top -n 3` against each arm's storage shows programs with `fitness > 0` and `is_valid = 1`;
- arm B log contains `[StructuredDiffMutationOperator] Initialized with AllowedDagChanges` and zero `diff_schema_error` / `diff_apply_assertion` lines;
- arm A log shows mutants flowing through `ParseJsonProgram` (any `json_parse_error` lines here are DATA — the baseline failure mode — not a bug to fix);
- inspect one arm-B child via `gigaevo top -n 1` — its code must be pretty-printed chain JSON.

- [ ] **Step 5: Report smoke results to the user + Telegram**

Send a Telegram status (`tools.telegram_notify`, Python API, `parse_mode=None`, `HTTPS_PROXY` set) summarizing: seed fitness per chain, both smoke runs' best fitness, and arm-B failure counts (expected 0). Then commit the smoke script after user approval:

```bash
rtk git add experiments/carl_diff_smoke_seed_rouge.py
rtk git commit -m "chore(experiments): summarizer seed ROUGE smoke probe"
```

---

### Task 11: A/B launch runbook (500 mutants/arm)

**Files:**
- Create: `experiments/carl_diff_ab/README.md` (launch record: exact commands, storage targets, PIDs, log paths)
- Create: `experiments/carl_diff_ab/04_issues_log.md` (every experiment gets one; append issues as they arise)

Preconditions (hard gates, in order):
1. Tasks 1–10 all green; full targeted test sweep passes: `/run-tests` over `tests/chains/`, `tests/evolution/test_allowed_changes.py`, `tests/evolution/test_structured_diff_operator.py`, `tests/llm/test_structured_diff_agent.py`, `tests/stages/test_json_genome.py`, `tests/problems/test_initial_loaders.py`, `tests/problems/test_summarizer_rouge.py`, `tests/problems/test_summarizer_problem.py`.
2. All work committed (user-approved) — never change imports while an experiment runs.
3. Telegram `gate_launch_confirmation` — block on the user's go.

- [ ] **Step 1: Launch both arms (after the Telegram gate)**

Same commands as Task 10 Step 4 with `max_mutants=500`, fresh storage targets, `nohup ... &` with logs to `experiments/carl_diff_ab/logs/arm{A,B}.log`, PIDs recorded in `README.md`. Identical CLI between arms except `+mutation=structured_diff_chains` and the storage target (mirror-baseline rule). Confirm both PIDs alive via `lsof experiments/carl_diff_ab/logs/armA.log` (rtk truncates `ps`). Append a dated launch entry to `experiment_archive/JOURNAL.md` and send a Telegram launch confirmation.

- [ ] **Step 2: Monitor**

Periodically (and on completion): best fitness via `gigaevo top -n 1` per arm (never scrape logs for fitness); anomalies → `post_anomaly_alert`.

- [ ] **Step 3: Failure accounting (the experiment's primary deliverable)**

Per arm, over the full run:

```bash
for label in json_parse_error carl_validation_error diff_schema_error diff_apply_assertion llm_call_error "Structured output parse failed"; do
  printf "%-32s A=%-6s B=%s\n" "$label" \
    "$(grep -c "$label" experiments/carl_diff_ab/logs/armA.log)" \
    "$(grep -c "$label" experiments/carl_diff_ab/logs/armB.log)"
done
```

Plus per-arm program-level stats from storage: total programs, `is_valid=0` count, best/median fitness, median `n_steps`, total `completion_tokens`. Success criteria (design §4.6): arm B structural failures ≈ 0 (target: 0 `diff_apply_assertion`, ~0 `diff_schema_error`); arm A's structural failure rate is the headline baseline number; arm B fitness trajectory ≥ arm A (trajectory shape, not just best-at-end).

- [ ] **Step 4: Close out**

Write results to `experiments/carl_diff_ab/RESULTS.md` (failure table, fitness trajectories, tokens); dated finding entry in `experiment_archive/JOURNAL.md`; archive via `bin/archive_experiment.sh` BEFORE any flush; Telegram `gate_results_signoff` with the failure table and fitness numbers. Commit the experiment records after user approval.

---

## Self-Review (completed)

- **Spec coverage:** §4.2 language → Task 2 (verbatim prototype port); §4.3 hierarchy incl. the user's ABC-in-`gigaevo/evolution/mutation` + subclass-in-`gigaevo/chains` correction → Tasks 1–2; §4.4 operator/agent → Tasks 3–4; §4.5 taxonomy → labels wired in Tasks 2/3/4/5 + doc update in Task 9 + accounting in Task 11; §4.6 experiment → Tasks 8/10/11 (baseline arm A raw-JSON prompts in Task 8; seed-band smoke in Task 10; paired 500-mutant runs in Task 11).
- **Placeholder scan:** the only deliberately unfilled values are environment state that must be read at execution time (exact storage override keys from the `--cfg job` preview, free DB/dir targets) — Task 10 Step 1 produces them and Task 11 records them; everything else is complete code/commands.
- **Type consistency:** `DiffSchema{json_schema, validate}` and `AllowedChanges.{build_schema, render_parents, apply, describe}` used identically in Tasks 1/2/3/4; `arun(parents, parents_map, diff_schema) → {"code","diff","metadata"}` matches between Tasks 3 and 4; `make_genome` imported from `tests/chains/test_dag_changes.py` by Tasks 3/4; `rouge_l_f1` signature matches between Tasks 7 and 8; `ParseJsonProgram(timeout=...)` matches `Stage.__init__(*, timeout)`.
- **Prompt parity (user directive 2026-07-02):** both arms' mutation prompts (Tasks 3 and 8) are near-copies of the stock `gigaevo/prompts/mutation/{system,user}.txt` — identical section skeleton, gates, citation discipline, and identical chain-adapted archetype/example wording between the two arms. Divergence is confined to the output medium: arm A replaces OUTPUT RULE 3 with the complete-wire-JSON-in-`code` rule (stock schema fields otherwise verbatim); arm B folds the citation/hypothesis rules into `reasoning` (the diff schema's only free-text field) and makes `{allowed_changes}` = `AllowedDagChanges.describe()` the body of rule 3. describe() carries only diff-language mechanics (its `reasoning` guidance line was removed in Task 2) so it embeds without overlapping or contradicting rules 1–2.
