from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage

from gigaevo.evolution.mutation.python_patch import (
    PythonPatchMutationOperator,
    PythonSourceGenome,
    SearchReplace,
    parse_search_replace,
)
from gigaevo.exceptions import MutationError
from gigaevo.programs.program import Program
from gigaevo.programs.program_state import ProgramState


SOURCE = """\
CONSTANT = 10

# EVOLVE-BLOCK-START algorithm
def score(x):
    return x + 1
# EVOLVE-BLOCK-END algorithm

def entrypoint():
    return {"fitness": float(score(CONSTANT))}
"""


def test_genome_applies_unique_patch_inside_editable_region():
    genome = PythonSourceGenome(SOURCE)
    child = genome.apply(
        [SearchReplace("def score(x):\n    return x + 1\n", "def score(x):\n    return x * 2\n")]
    )

    assert "return x * 2" in child.source
    assert "CONSTANT = 10" in child.source


def test_genome_rejects_patch_outside_editable_region():
    genome = PythonSourceGenome(SOURCE)

    with pytest.raises(MutationError, match="outside an EVOLVE block"):
        genome.apply([SearchReplace("CONSTANT = 10", "CONSTANT = 20")])


def test_parser_supports_multiple_search_replace_blocks():
    patch = """\
<<<<<<< SEARCH
old one
=======
new one
>>>>>>> REPLACE
<<<<<<< SEARCH
old two
=======
new two
>>>>>>> REPLACE
"""

    assert parse_search_replace(patch) == [
        SearchReplace("old one\n", "new one\n"),
        SearchReplace("old two\n", "new two\n"),
    ]


def test_python_patch_seed_applies_bounded_code_edit():
    root = Path(__file__).parents[2]
    source = (
        root / "problems/pmhctcr/initial_programs/python_patch_seed.py"
    ).read_text()

    child = PythonSourceGenome(source).apply(
        [
            SearchReplace(
                'REGIONS = {name: "full" for name in CHAINS}',
                'REGIONS = {name: "cdr3" if name.startswith("tcr") else "full" for name in CHAINS}',
            )
        ]
    )

    assert "name.startswith(\"tcr\")" in child.source
    assert "def entrypoint():" in child.source


@pytest.mark.asyncio
async def test_operator_keeps_one_parent_and_records_db_inspirations():
    parent = Program(code=SOURCE, metrics={"fitness": 11.0})
    inspiration = Program(
        code=SOURCE.replace("return x + 1", "return x + 2"),
        metrics={"fitness": 12.0},
        state=ProgramState.DONE,
    )
    storage = AsyncMock()
    storage.get_all_by_status.return_value = [parent, inspiration]
    llm = AsyncMock()
    llm.get_last_model = Mock(return_value=None)
    llm.ainvoke.return_value = AIMessage(
        content="""\
<<<<<<< SEARCH
def score(x):
    return x + 1
=======
def score(x):
    return x * 2
>>>>>>> REPLACE
"""
    )
    operator = PythonPatchMutationOperator(
        llm_wrapper=llm,
        program_storage=storage,
        num_inspirations=2,
        random_seed=0,
    )

    spec = await operator.mutate_single([parent])

    assert spec is not None
    assert spec.parents == [parent]
    assert "return x * 2" in spec.code
    assert spec.metadata["parent_program_id"] == parent.id
    assert spec.metadata["inspiration_program_ids"] == [inspiration.id]
    prompt = llm.ainvoke.call_args.args[0]
    assert "parent_program" in prompt[1].content
    assert inspiration.id in prompt[1].content
