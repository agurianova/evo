"""UnifiedEvolve arm of the matched ACI study: one propose() operator.

The grading lives in problems.aaai_submit._harness.benchmarks.aci_grading, shared with the improve and
basic arms. The only thing this file chooses is the adapter.
"""

from problems.aaai_submit._harness.benchmarks.aci_grading import grade_controller
from problems.aaai_submit._harness.common.adapters import UnifiedAdapter


def validate(program_class):
    return grade_controller(UnifiedAdapter, program_class)
