"""ImprovEvolve arm of the matched spherical study: generate_config / perturb / improve.

The grading lives in problems.aaai_submit._harness.benchmarks.spherical_grading, shared with the mixed and
basic arms. The only thing this file chooses is the adapter.
"""

from problems.aaai_submit._harness.benchmarks.spherical_grading import grade
from problems.aaai_submit._harness.common.adapters import ModularAdapter


def validate(program_class):
    return grade(ModularAdapter, program_class)
