# Sequential-Landscape Benchmark — Design Spec

**Date:** 2026-06-25
**Status:** design approved (brainstorming), pending implementation plan
**Problem dir:** `problems/sequential_landscape/`

## Goal / research question

Build optimization landscapes whose **disconnectivity (barrier) tree** is *prescribed by hand*, so
that good solutions are reachable only by **sequential discovery of local minima** — you must
descend the chain step by step; shortcutting to a deep basin is walled off.

The point is an **empirical breakdown study**: run a *graded ladder* of landscapes from easy → hard
and find **where each optimizer stops succeeding** — both LLM-evolved optimizers (via gigaevo) and
classical optimizers (scipy / CMA). The deliverable is a per-instance success curve that validates
patterns like "method X cracks caterpillars to length 7 then collapses", "double-funnels defeat
global samplers", etc.

## Background (one paragraph)

A disconnectivity graph is the *tree* of how sublevel-set components of `f` merge as the level
rises: leaves = minima (at their depth), internal nodes = the saddle height where sub-branches
merge. It is always a tree (components only merge). Any **binary** barrier tree is realizable in 1-D
via the Cartesian-tree bijection: in-order traversal gives a list of minima depths and the barriers
between consecutive minima, where the barrier between two minima = the height of their lowest common
ancestor. We realize that 1-D floor along a **winding canyon** embedded in ℝ^d, with steep walls, so
that (a) topology is controlled by the floor and (b) geometry (dim, spatial layout, no-Euclidean-
shortcut) is controlled by the embedding — the two are decoupled.

## Approach (chosen: A — projected-polyline canyon)

```
f(x) = g(s(x)) + W · u(x)²
```
- `s(x)`, `u(x)`: arclength of the nearest point on a polyline centerline, and distance to it.
- `g`: shape-preserving (PCHIP / monotone-cubic) interpolation through the prescribed alternating
  control points (min, barrier, min, barrier, …, min). PCHIP guarantees **no spurious extrema**, so
  the realized tree is *exactly* the target.
- Centerline: **serpentine** (rows snaking back and forth, gap `Δ` between arms) so arclength-distant
  minima that are spatially close are separated by a tall wall → no shortcut.
- No-skip guarantee: choose/auto-scale `W` so `W·(Δ/2)² ≫ max barrier`. Verified, not assumed.

Rejected: B sum-of-Gaussians (only approximate topology), C pure canyon coords (loses the ℝ^d
no-shortcut property).

## Module layout — one self-contained problem dir

```
problems/sequential_landscape/
  landscape.py        # core lib (no gigaevo deps): TreeSpec + GeometrySpec -> Landscape
  diagnose.py         # verifier: recover minima+saddles, rebuild tree, ASSERT == target; render graph
  specs.py            # the graded difficulty LADDER (hand-authored TreeSpecs)
  benchmark.py        # classical optimizers over the ladder -> per-instance results table
  task_description.txt # gigaevo task: evolve optimizer(f, bounds, budget)
  validate.py         # run candidate optimizer over the ladder; partial-credit fitness
  metrics.yaml        # fitness (primary, [0,1]), is_valid
  initial_programs/
    random_restart.py # trivial seed optimizer
```
`validate.py`, `diagnose.py`, `benchmark.py` all import `landscape.py` (intra-problem imports work —
`spherical_codes_improver` already does this).

## Core contracts (`landscape.py`)

```python
@dataclass(frozen=True)
class Leaf:  depth: float                                  # well-bottom value (minimum)
@dataclass(frozen=True)
class Node:  height: float; children: tuple[Leaf|Node, ...]  # saddle height where children merge

@dataclass(frozen=True)
class GeometrySpec:
    dim: int = 2
    arm_gap: float = 3.0            # Δ between serpentine arms
    wall_stiffness: float | None = None   # W; None -> auto-scale to satisfy no-skip
    well_spacing: float = 1.0      # arclength between consecutive minima
    seed: int = 0

class Landscape:                   # produced by build(tree, geom)
    def __call__(self, x) -> float
    bounds: list[tuple[float, float]]
    global_min_value: float
    global_min_x: np.ndarray
    def basin_of(self, x) -> int   # which step (0..K-1) x descends to; for partial credit
    target_tree: Node              # what diagnose.py checks against
```
- Heap-property validation on the tree (parent height ≥ all descendant heights/depths); raise on
  violation.
- n-ary nodes allowed in authoring; split into binary internally (ties perturbed by ε).

## Difficulty ladder (`specs.py`) — initial set, ordered easy → hard

| name | topology | K | dim | what it probes |
|---|---|---|---|---|
| `caterpillar_3` | monotone chain | 3 | 2 | sanity; everything should solve |
| `caterpillar_7` | monotone chain | 7 | 2 | chain length |
| `caterpillar_12` | monotone chain | 12 | 5 | length + dimension |
| `balanced_8` | balanced binary | 8 | 3 | hierarchical (log-depth) commitments |
| `double_funnel_10` | two competing funnels | 10 | 4 | frustration; global hidden in 2nd funnel |
| `deep_caterpillar_20` | monotone chain | 20 | 8 | stress / scaling wall |

Hand-authored, frozen, reproducible (seed in GeometrySpec). Easy to extend later.

## Fitness (`validate.py`) — partial credit for sequential progress

For each landscape in the ladder: build `f`, run candidate `optimizer(f, bounds, budget)` under a
budget cap + SIGALRM timeout (mirror `problems/adversarial/optimizer/pop_a/validate.py`). Map the
returned `x` to `basin_of(x)`. Per-instance score blends:
- `progress = basin_index / (K-1)`  (deepest step reached), and
- `value_gap = normalized closeness of f(x) to global_min`.
Instance score `= 0.5·progress + 0.5·value_gap` ∈ [0,1]. Suite fitness = mean over the ladder.
Reaching step 3/10 scores ≈0.3 → the LLM gets gradient instead of a flat 0. `higher_is_better:
true`, primary, bounds [0,1]. `is_valid` = optimizer callable and ran without crashing.

## Verifier (`diagnose.py`)

- Recover minima by multistart local descent; recover saddles as the maxima of `g` along the
  centerline (1-D scan in `s`). Build the Cartesian tree of recovered barriers.
- Assert recovered tree == `target_tree` within tolerance (heights, ordering). This **certifies**
  the landscape realizes the spec — run it on every ladder instance as a test.
- Render the disconnectivity graph (matplotlib) for visual confirmation; text fallback if needed.

## Classical benchmark (`benchmark.py`)

Run over the same ladder: random restarts (baseline), gradient descent (finite-diff), scipy
`basinhopping`, scipy `differential_evolution`, and CMA-ES (`cma`, both confirmed installed in
`evo`). Emit a per-instance table (rows = optimizers, cols = ladder instances; cell = basin reached
/ global-hit). This is the apples-to-apples comparison against the gigaevo-evolved optimizer and the
core artifact for the breakdown study.

## Testing strategy (TDD)

- `landscape.py`: tree→(depths,barriers) compilation (Cartesian-tree round-trip); heap-property
  rejection; no-skip wall inequality holds; `global_min_x` is the true argmin; `basin_of` correct on
  known points; PCHIP floor has exactly K minima and K-1 maxima at prescribed heights.
- `diagnose.py`: recovered tree == target on every ladder instance.
- `validate.py`: a known-perfect optimizer (returns `global_min_x`) scores 1.0; random scores low;
  non-callable → `is_valid=0`; budget/timeout enforced.
- Run via `/run-tests` targeting the new test dir — never bare pytest.

## Risks / open points

- Polyline projection kinks → rough gradient for gradient-based methods (acceptable; derivative-free
  unaffected). Note in task description.
- Auto-scaling `W` must keep `bounds` reasonable so classical global samplers aren't trivially
  diluted; verifier checks no-skip inequality.
- Canonical-doc touch: new problem dir needs a row/mention per the problems convention; update
  `tools/README.md` only if a CLI/script under `tools/` is added (benchmark lives in the problem dir,
  so likely not).

## Out of scope (YAGNI)

- Procedural difficulty generator and named-preset auto-ladder (core API is explicit tree spec).
- Smooth/analytic landscape variant (B).
- Spiral centerline (serpentine suffices for no-skip).
- Wiring the classical benchmark as a `gigaevo` CLI subcommand.
