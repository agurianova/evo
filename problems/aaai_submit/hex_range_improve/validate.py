"""ImprovEvolve arm of the matched range-generalization study (Exp G):
generate_config / perturb / improve, graded independently at every train size.

The grading lives in problems.aaai_submit._harness.benchmarks.hex_range_grading, shared with the
basic arm. The only thing this file chooses is the adapter.
"""

from problems.aaai_submit._harness.benchmarks.hex_range_grading import (
    grade_range_controller,
)
from problems.aaai_submit._harness.common.adapters import ModularAdapter


def validate(program_class):
    return grade_range_controller(ModularAdapter, program_class)
