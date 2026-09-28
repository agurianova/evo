"""Opt-in evolution of complete Python files through bounded SEARCH/REPLACE patches."""

from __future__ import annotations

import ast
from collections.abc import Sequence
from dataclasses import dataclass
import random
import re
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from gigaevo.evolution.mutation.base import MutationOperator, MutationSpec
from gigaevo.evolution.mutation.constants import MUTATION_CONTEXT_METADATA_KEY
from gigaevo.exceptions import MutationError
from gigaevo.programs.program import Program
from gigaevo.programs.program_state import ProgramState

if TYPE_CHECKING:
    from gigaevo.database.program_storage import ProgramStorage


EVOLVE_BLOCK_START = "# EVOLVE-BLOCK-START"
EVOLVE_BLOCK_END = "# EVOLVE-BLOCK-END"

_MARKER_RE = re.compile(
    r"(?m)^[ \t]*# EVOLVE-BLOCK-(START|END)[ \t]+([A-Za-z0-9_.-]+)[ \t]*$"
)
_PATCH_RE = re.compile(
    r"(?ms)^[ \t]*<{7}[ \t]+SEARCH[ \t]*\n"
    r"(.*?)"
    r"^[ \t]*={7}[ \t]*\n"
    r"(.*?)"
    r"^[ \t]*>{7}[ \t]+REPLACE[ \t]*(?:\n|$)"
)


@dataclass(frozen=True)
class EditableRegion:
    """A named half-open character range containing mutable source."""

    name: str
    start: int
    end: int


@dataclass(frozen=True)
class SearchReplace:
    search: str
    replace: str


class PythonSourceGenome:
    """Validated full-source genome with immutable code outside marked regions."""

    def __init__(self, source: str, *, entry_function: str = "entrypoint"):
        self.source = source
        self.entry_function = entry_function
        self.regions = self._parse_regions(source)
        self._validate_python(source)

    @staticmethod
    def _parse_regions(source: str) -> tuple[EditableRegion, ...]:
        regions: list[EditableRegion] = []
        open_region: tuple[str, int] | None = None
        names: set[str] = set()

        for marker in _MARKER_RE.finditer(source):
            kind, name = marker.groups()
            if kind == "START":
                if open_region is not None:
                    raise MutationError("EVOLVE blocks cannot be nested")
                if name in names:
                    raise MutationError(f"Duplicate EVOLVE block name: {name}")
                open_region = (name, marker.end())
                names.add(name)
                continue

            if open_region is None:
                raise MutationError(f"EVOLVE block {name!r} ends without a start")
            open_name, content_start = open_region
            if name != open_name:
                raise MutationError(f"EVOLVE block {open_name!r} closed as {name!r}")
            regions.append(
                EditableRegion(name=name, start=content_start, end=marker.start())
            )
            open_region = None

        if open_region is not None:
            raise MutationError(f"EVOLVE block {open_region[0]!r} is not closed")
        if not regions:
            raise MutationError(
                "Python genome has no '# EVOLVE-BLOCK-START name' regions"
            )
        return tuple(regions)

    def _validate_python(self, source: str) -> None:
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise MutationError(f"Mutated Python does not compile: {exc}") from exc

        functions = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        if self.entry_function not in functions:
            raise MutationError(
                f"Python genome must define top-level {self.entry_function}()"
            )

    def editable_source(self) -> str:
        chunks = []
        for region in self.regions:
            chunks.append(
                f"### {region.name}\n{self.source[region.start : region.end].strip()}"
            )
        return "\n\n".join(chunks)

    def apply(self, patches: Sequence[SearchReplace]) -> PythonSourceGenome:
        if not patches:
            raise MutationError("LLM returned no SEARCH/REPLACE blocks")

        source = self.source
        for index, patch in enumerate(patches, start=1):
            if not patch.search:
                raise MutationError(f"Patch {index} has an empty SEARCH section")
            if "EVOLVE-BLOCK-" in patch.replace:
                raise MutationError(f"Patch {index} attempts to alter EVOLVE markers")

            current = PythonSourceGenome(source, entry_function=self.entry_function)
            occurrences = [
                match.start() for match in re.finditer(re.escape(patch.search), source)
            ]
            if len(occurrences) != 1:
                raise MutationError(
                    f"Patch {index} SEARCH must match exactly once; "
                    f"matched {len(occurrences)} times"
                )
            start = occurrences[0]
            end = start + len(patch.search)
            if not any(
                region.start <= start and end <= region.end
                for region in current.regions
            ):
                raise MutationError(f"Patch {index} SEARCH is outside an EVOLVE block")
            source = source[:start] + patch.replace + source[end:]

        return PythonSourceGenome(source, entry_function=self.entry_function)


def parse_search_replace(text: str) -> list[SearchReplace]:
    """Parse Aider-style SEARCH/REPLACE blocks, optionally inside a code fence."""

    patches = [
        SearchReplace(search=match.group(1), replace=match.group(2))
        for match in _PATCH_RE.finditer(text)
    ]
    if not patches:
        raise MutationError(
            "Expected at least one <<<<<<< SEARCH / ======= / >>>>>>> REPLACE block"
        )
    return patches


def _message_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


class PythonPatchMutationOperator(MutationOperator):
    """Mutate one parent while sampling separate inspiration programs from storage."""

    def __init__(
        self,
        *,
        llm_wrapper: Any,
        program_storage: ProgramStorage,
        num_inspirations: int = 3,
        entry_function: str = "entrypoint",
        random_seed: int | None = None,
    ):
        if num_inspirations < 0:
            raise ValueError("num_inspirations must be non-negative")
        self.llm_wrapper = llm_wrapper
        self.program_storage = program_storage
        self.num_inspirations = num_inspirations
        self.entry_function = entry_function
        self._random = random.Random(random_seed)

    async def _select_inspirations(self, parent: Program) -> list[Program]:
        if self.num_inspirations == 0:
            return []
        candidates = await self.program_storage.get_all_by_status(
            ProgramState.DONE.value
        )
        candidates = [
            program
            for program in candidates
            if program.id != parent.id and program.code != parent.code
        ]
        compatible = []
        for program in candidates:
            try:
                PythonSourceGenome(program.code, entry_function=self.entry_function)
            except MutationError:
                continue
            compatible.append(program)
        count = min(self.num_inspirations, len(compatible))
        return self._random.sample(compatible, count)

    def _build_prompt(
        self,
        parent: Program,
        inspirations: Sequence[Program],
    ) -> list[Any]:
        inspiration_blocks = []
        for index, program in enumerate(inspirations, start=1):
            try:
                editable = PythonSourceGenome(
                    program.code, entry_function=self.entry_function
                ).editable_source()
            except MutationError:
                editable = "<incompatible genome omitted>"
            inspiration_blocks.append(
                f"=== Inspiration {index} id={program.id} ===\n"
                f"metrics={program.metrics}\n{editable}"
            )

        insights = parent.metadata.get(MUTATION_CONTEXT_METADATA_KEY) or ""
        inspiration_text = (
            "\n\n".join(inspiration_blocks)
            if inspiration_blocks
            else "No inspirations available."
        )
        system = f"""You evolve a complete Python program by editing marked regions only.
Return only one or more patches in this exact format:
<<<<<<< SEARCH
exact text copied from the parent
=======
replacement text
>>>>>>> REPLACE

SEARCH must match exactly once and must be wholly inside an EVOLVE block.
Never edit EVOLVE markers or code outside them. Keep top-level
{self.entry_function}() working and returning an object with fit()/score().
Insights describe a Python code change — translate them into SEARCH/REPLACE on
real source. Ignore any OPERATOR=/CHANGE_*/CREATE_*/NOOP JSON-genotype language.
The predictor's active_modalities tuple is a runtime MAP-Elites contract. When
adding or removing actual sequence, structure, or surface use, update that tuple
in the same mutation to match what fit()/score() consume.
Use inspirations as ideas, not as patch targets."""
        user = f"""=== parent_program id={parent.id} ===
metrics={parent.metrics}
insights:
{insights}

```python
{parent.code}
```

{inspiration_text}
"""
        return [SystemMessage(content=system), HumanMessage(content=user)]

    async def mutate_single(
        self,
        selected_parents: list[Program],
        memory_instructions: str | None = None,
    ) -> MutationSpec | None:
        if len(selected_parents) != 1:
            raise MutationError(
                "PythonPatchMutationOperator requires exactly one parent_program; "
                "inspirations are selected separately from storage"
            )
        parent = selected_parents[0]
        genome = PythonSourceGenome(parent.code, entry_function=self.entry_function)
        inspirations = await self._select_inspirations(parent)
        response = await self.llm_wrapper.ainvoke(
            self._build_prompt(parent, inspirations)
        )
        patch_text = _message_text(response)
        patches = parse_search_replace(patch_text)
        child = genome.apply(patches)
        model_name = (
            self.llm_wrapper.get_last_model()
            if hasattr(self.llm_wrapper, "get_last_model")
            else None
        )

        metadata: dict[str, Any] = {
            "python_patch": patch_text,
            "parent_program_id": parent.id,
            "inspiration_program_ids": [program.id for program in inspirations],
            "editable_regions": [region.name for region in child.regions],
            MutationSpec.META_OUTPUT: {
                "base_parent": 1,
                "inspiration_program_ids": [program.id for program in inspirations],
            },
        }
        if model_name:
            metadata[MutationSpec.META_MODEL] = model_name
        logger.info(
            "[PythonPatchMutationOperator] parent={} inspirations={} patches={}",
            parent.short_id,
            len(inspirations),
            len(patches),
        )
        return MutationSpec(
            code=child.source,
            parents=[parent],
            name="LLM Python SEARCH/REPLACE mutation",
            metadata=metadata,
        )
