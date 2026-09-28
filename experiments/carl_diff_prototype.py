"""Prototype of the positional-slot DAG-diff language for CARL chains.

Design: experiments/carl_dag_diff_mutation_design.md (S4.2, "C++" variant).
Builds a dynamic per-call pydantic schema from real base chains, applies diffs by
pure transcription into mmar_carl objects (whose constructors run full chain
validation), and fuzzes the schema space to check the by-construction soundness
claim: every schema-valid diff must yield a chain that ReasoningChain.from_dict
accepts. Also demonstrates that structural errors (forward deps, dangling ids,
empty aim) are unrepresentable — rejected at the schema layer, not at apply time.

Run: /home/jovyan/.mlspace/envs/evo/bin/python3 experiments/carl_diff_prototype.py
"""

from __future__ import annotations

import json
from pathlib import Path
import random
from typing import Annotated, Any, Literal, Union

from mmar_carl.chain import ReasoningChain
from mmar_carl.models.steps import LLMStepDescription
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    create_model,
)

PACK_CHAINS = (
    Path(__file__).resolve().parent.parent
    / "carl_pack"
    / "summarizer-evolution"
    / "chains"
)
MAX_STEPS = 8

CONTENT_FIELDS = tuple(
    name
    for name in (
        "title",
        "aim",
        "stage_action",
        "reasoning_questions",
        "example_reasoning",
    )
    if name in LLMStepDescription.model_fields
)
assert len(CONTENT_FIELDS) == 5, f"carl step surface changed: {CONTENT_FIELDS}"

# aim/title must stay non-empty or LLMStepDescription's validator rejects the chain;
# min_length pushes that invariant into the schema so it is unrepresentable-to-break
_EDIT_FIELD_DEFS = {
    name: (
        str | None,
        Field(default=None, min_length=1)
        if name in ("title", "aim")
        else Field(default=None),
    )
    for name in CONTENT_FIELDS
}
StepEdits = create_model(
    "StepEdits", __config__=ConfigDict(extra="forbid"), **_EDIT_FIELD_DEFS
)


def base_ids(ns: str, chain: ReasoningChain) -> list[str]:
    return [f"{ns.lower()}{i + 1}" for i in range(len(chain.steps))]


def build_diff_model(
    bases: dict[str, ReasoningChain], max_steps: int = MAX_STEPS
) -> TypeAdapter:
    branches = []
    for ns, chain in bases.items():
        ids = base_ids(ns, chain)
        slot_models: list[type[BaseModel]] = []
        for k in range(1, max_steps + 1):
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
            slot_models.append(Annotated[keep | new, Field(discriminator="kind")])
        steps_type = Union[  # noqa: UP007 — union built at runtime from a dynamic tuple
            tuple(tuple[*slot_models[:n]] for n in range(1, max_steps + 1))
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
    return TypeAdapter(Annotated[tuple(branches), Field(discriminator="base_parent")])


def apply_diff(
    diff: BaseModel, bases: dict[str, ReasoningChain], extras: dict[str, str]
) -> dict:
    base = bases[diff.base_parent]
    by_id = dict(zip(base_ids(diff.base_parent, base), base.steps))
    steps = []
    for k, slot in enumerate(diff.steps, start=1):
        raw_deps = [
            int(ref.removeprefix("slot_")) for ref in getattr(slot, "dependencies", [])
        ]
        deps = sorted(set(raw_deps))  # deps are a set; duplicates carry no meaning
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


def assert_valid_genome(wire: dict) -> ReasoningChain:
    reparsed = ReasoningChain.from_dict(
        json.loads(json.dumps(wire)), use_typed_steps=True
    )
    assert len(reparsed.steps) == len(wire["steps"])
    return reparsed


def show(label: str, wire: dict) -> None:
    parts = [
        f"{s['number']}:{s['title'][:26]!r}<-{s['dependencies']}" for s in wire["steps"]
    ]
    print(f"  {label:<14} {' | '.join(parts)}")


def render_for_prompt(ns: str, chain: ReasoningChain) -> str:
    lines = []
    for sid, step in zip(base_ids(ns, chain), chain.steps):
        deps = [f"{ns.lower()}{d}" for d in step.dependencies]
        lines.append(
            f"{sid} (deps={deps or '[]'}): {step.title} -- aim: {step.aim[:60]}"
        )
    return "\n".join(lines)


def demo(
    adapter: TypeAdapter, bases: dict[str, ReasoningChain], extras: dict[str, str]
) -> None:
    print("== base chains as the mutation prompt would render them ==")
    for ns, chain in bases.items():
        print(f"[parent {ns}]")
        print(render_for_prompt(ns, chain))
    cases = {
        "edit": {
            "reasoning": "sharpen the polish step",
            "base_parent": "A",
            "steps": [
                {"kind": "keep", "id": "a1"},
                {
                    "kind": "keep",
                    "id": "a2",
                    "dependencies": ["slot_1"],
                    "edits": {
                        "aim": "Deliver one crisp final sentence with zero filler words"
                    },
                },
            ],
        },
        "insert": {
            "reasoning": "add a fact-check between draft and polish",
            "base_parent": "A",
            "steps": [
                {"kind": "keep", "id": "a1"},
                {
                    "kind": "new",
                    "title": "Verify facts",
                    "aim": "Cross-check the draft against the source",
                    "stage_action": "List any claim in the draft not supported by the Data section.",
                    "dependencies": ["slot_1"],
                },
                {"kind": "keep", "id": "a2", "dependencies": ["slot_2"]},
            ],
        },
        "delete": {
            "reasoning": "collapse to a single-shot summarizer",
            "base_parent": "A",
            "steps": [{"kind": "keep", "id": "a2"}],
        },
        "duplicate": {
            "reasoning": "two independent drafts, then polish the pair",
            "base_parent": "A",
            "steps": [
                {"kind": "keep", "id": "a1"},
                {"kind": "keep", "id": "a1", "dependencies": []},
                {"kind": "keep", "id": "a2", "dependencies": ["slot_1", "slot_2"]},
            ],
        },
        "rewire": {
            "reasoning": "run facts and draft in parallel off the raw input",
            "base_parent": "B",
            "steps": [
                {"kind": "keep", "id": "b1"},
                {"kind": "keep", "id": "b2", "dependencies": []},
                {"kind": "keep", "id": "b3", "dependencies": ["slot_1", "slot_2"]},
            ],
        },
        "full_rewrite": {
            "reasoning": "completeness check: all-new skeleton",
            "base_parent": "B",
            "steps": [
                {
                    "kind": "new",
                    "title": "Extract key entities",
                    "aim": "Name the actors and the event",
                },
                {
                    "kind": "new",
                    "title": "Compose summary",
                    "aim": "One sentence from the entities",
                    "dependencies": ["slot_1"],
                },
            ],
        },
    }
    print("\n== hand-written diffs -> child genomes (all must validate) ==")
    for label, payload in cases.items():
        wire = apply_diff(adapter.validate_python(payload), bases, extras)
        assert_valid_genome(wire)
        show(label, wire)

    print("\n== unrepresentable-by-construction: schema must reject ==")
    rejects = {
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
    for label, payload in rejects.items():
        try:
            adapter.validate_python(payload)
        except ValidationError as e:
            print(f"  rejected ok    {label:<28} ({e.error_count()} schema errors)")
        else:
            raise AssertionError(f"schema ACCEPTED invalid diff: {label}")


def fuzz(
    adapter: TypeAdapter,
    bases: dict[str, ReasoningChain],
    extras: dict[str, str],
    n: int = 2000,
) -> None:
    rng = random.Random(7)
    words = (
        "draft polish verify extract merge rank filter compress compare restate".split()
    )
    for i in range(n):
        ns = rng.choice(list(bases))
        ids = base_ids(ns, bases[ns])
        n_slots = rng.randint(1, MAX_STEPS)
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
                edits = {}
                if rng.random() < 0.4:
                    edits = {"edits": {rng.choice(CONTENT_FIELDS): rng.choice(words)}}
                steps.append({"kind": "keep", "id": rng.choice(ids), **edits, **deps})
            else:
                steps.append(
                    {
                        "kind": "new",
                        "title": rng.choice(words),
                        "aim": rng.choice(words),
                        "stage_action": rng.choice(words),
                        **deps,
                    }
                )
        diff = adapter.validate_python(
            {"reasoning": f"fuzz {i}", "base_parent": ns, "steps": steps}
        )
        assert_valid_genome(apply_diff(diff, bases, extras))
    print(
        f"\n== fuzz: {n} random schema-valid diffs applied, {n}/{n} valid child chains, 0 failures =="
    )


def schema_report(adapter: TypeAdapter) -> None:
    schema = adapter.json_schema()
    blob = json.dumps(schema)
    print("\n== wire schema stats (what function_calling would carry) ==")
    print(
        f"  bytes={len(blob)}  prefixItems_used={'prefixItems' in blob}  defs={len(schema.get('$defs', {}))}"
    )


def main() -> None:
    seeds = {
        "A": json.loads((PACK_CHAINS / "chain_2step.json").read_text()),
        "B": json.loads((PACK_CHAINS / "chain_3step.json").read_text()),
    }
    bases = {
        ns: ReasoningChain.from_dict(d, use_typed_steps=True) for ns, d in seeds.items()
    }
    extras = {ns: d["task_description"] for ns, d in seeds.items()}
    adapter = build_diff_model(bases)
    demo(adapter, bases, extras)
    fuzz(adapter, bases, extras)
    schema_report(adapter)


if __name__ == "__main__":
    main()
