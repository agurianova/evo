"""ImprovEvolve arm of the matched ACI study: generate_config / perturb / improve.

The grading lives in problems.aaai_submit._harness.benchmarks.aci_grading, shared with the mixed and
basic arms. The only thing this file chooses is the adapter.
"""

from problems.aaai_submit._harness.benchmarks.aci_grading import grade_controller
from problems.aaai_submit._harness.common.adapters import ModularAdapter


def validate(program_class):
    return grade_controller(ModularAdapter, program_class)
