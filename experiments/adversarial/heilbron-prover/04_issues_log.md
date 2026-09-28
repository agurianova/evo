# Issues Log

Track ALL errors, crashes, unexpected behavior, and manual interventions during this experiment.

## Format

Each entry should include:
- **When**: timestamp or phase
- **What**: brief description of the issue
- **Category**: run crash | tool bug | config mistake | infra issue | skill bug | watchdog | git | other
- **Impact**: how it affected the experiment
- **Root cause**: why it happened
- **Fix applied**: what was done to resolve it
- **Systemic fix needed**: YES/NO + description

---

### Issue #1: P2_A 75% invalidity — helper.py shape mismatch

- **When**: 2026-04-06, gen 1-9 (first launch)
- **What**: P2_A (Constructor, pair 2) had 75% invalidity (2/8 valid programs in 8 gens). All CallProgramFunction failures were `ValueError: einstein sum subscripts string contains too many subscripts for operand 0` in `is_inside_triangle`.
- **Category**: config mistake
- **Impact**: P2_A replicate effectively wasted (~8 gens of compute). Full restart required.
- **Root cause**: Two compounding issues:
  1. `is_inside_triangle()` in helper.py uses `einsum("ij,j->i", v2, v0)` which requires `points` to be 2D `(N,2)`. When LLM-generated code calls `is_inside_triangle(points[i], A, B, C)` with a single point `(2,)`, the einsum crashes.
  2. The adversarial `task_description.txt` did not document helper function input shapes (unlike `problems/heilbron/task_description.txt` which explicitly states `points (n, 2)`). Without shape hints, the LLM naturally writes per-point calls.
- **Fix applied**:
  1. Added `points = np.atleast_2d(points)` to `is_inside_triangle()` in all 3 helper.py copies (heilbron, pop_a, pop_b). This makes both `(2,)` and `(N,2)` inputs work.
  2. Added full shape documentation to both pop_a and pop_b `task_description.txt`.
  3. Cleared `__pycache__` in problem directories.
- **Systemic fix needed**: YES — When creating adversarial problem variants, always copy the full helper function docstrings/shape annotations from the original problem's task_description.txt. The `tools/wizard/` scaffolding should enforce this.
