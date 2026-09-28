"""UnifiedEvolve arm of the matched spherical study: one propose() operator.

The grading lives in problems.aaai_submit._harness.benchmarks.spherical_grading, shared with the improve and
basic arms. The only thing this file chooses is the adapter.
"""

from problems.aaai_submit._harness.benchmarks.spherical_grading import grade
from problems.aaai_submit._harness.common.adapters import UnifiedAdapter


def validate(program_class):
    return grade(UnifiedAdapter, program_class)
