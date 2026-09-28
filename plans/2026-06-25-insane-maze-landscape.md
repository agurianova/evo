# The Insane Maze Landscape

**Goal:** optimization landscapes that off-the-shelf global optimizers (differential
evolution, CMA-ES, basin-hopping, random restart) **provably cannot solve**, while a
privileged sequential path-follower (the oracle) solves them at ~1.0. The only winning
strategy is to model the problem as *sequential discovery of basins along a winding,
branching canyon with backtracking* — i.e. extremely sophisticated bespoke engineering.

This supersedes the equal-volume ladder in `plans/2026-06-25-sequential-landscape-benchmark.md`
(those instances are solved by `diff_evolution` at 0.75–1.0 — too easy). The chain
`Landscape` stays as the *easy* baseline; the insane construction is a NEW module
(`maze.py`) behind its own spec/builder seam — no rewrite of the green chain code.

## Why DE/CMA-ES win today, and the five mechanisms that kill them

DE/CMA win because basins are **equal-volume**: a Sobol/population init drops a point in
(or near) every basin including the global, and selection walks downhill. The sequential
structure is decorative — recombination teleports across it. Each mechanism removes one
crutch:

1. **Geometrically shrinking footprints (needle-in-needle).** Lane width and tube radius
   at tree-depth `d` scale `~ r^d` (r<1). Uniform/Sobol/random hit probability for a
   depth-`d` basin `~ r^(d·D)` → astronomically zero. Search-by-volume costs `r^(N·D)`;
   search-by-path costs `O(N)`. That gap is the entire problem.
2. **Measure-zero winding canyon in high-D.** Feasible corridor is a thin curved tube;
   the average of two on-tube points is off-tube (canyon nonconvex) → slammed by the wall
   penalty. Directly breaks DE crossover and CMA's Gaussian model. Off-centerline
   finite-difference gradients just measure the wall → gradient methods dead on arrival.
3. **Randomized per-instance turn directions.** Switchback waypoints with per-instance
   pseudo-random angles ⇒ basin k+1's direction is unpredictable from basins 0..k. Kills
   "fit the valley trend and extrapolate."
4. **Buried mouths + deceptive floor.** The corridor to a child opens only at the *bottom*
   of the parent basin (must fully descend to find it); barriers **rise** toward the global
   (going deeper looks locally worse). Greedy "go where it's lower" gets trapped early.
5. **Decoy branches (general tree) ⇒ backtracking.** Dead-end branches are deep-but-not-
   global. A depth-first follower commits to a decoy and dies; the solver must detect dead
   ends and backtrack. Needs memory + search strategy, not descent.

## Construction

Decouple **topology** (a barrier *tree*; internal nodes = saddles/barriers, leaves =
minima) from **geometry** (a 1-D tree skeleton embedded in 2D + `D-2` confined nuisance
dims).

- **Layout:** tidy (Reingold–Tilford-style) tree layout. `y = depth · row_gap`. Leaf x
  positions spaced by a per-depth lane width `lane(d) = base · r^d`; internal node x =
  mean of children. Guarantees non-crossing branches with min spatial separation between
  non-adjacent edges (the no-skip invariant: `stiffness·(sep/2)² ≫ max_barrier`).
- **Winding edges:** each parent→child segment is replaced by `K` switchback waypoints
  with per-instance random lateral offsets (amplitude `< lane(d)/3` to stay in-lane).
- **Floor on the skeleton:** value defined on the tree. Along edge parent(saddle)→child,
  PCHIP from barrier-height down to child's representative value (leaf depth, or child
  saddle height). No spurious extrema per edge.
- **Confinement / shrinking tube:** `f(x) = floor(proj) + stiffness(d) · (perp² + Σ extra²)`
  where `proj` = nearest skeleton point, `d` = depth of the edge it lands on,
  `stiffness(d) = base_stiffness / r^(2d)` so tube radius `~ r^d`.

`MazeSpec(dim, branch_factor, depth, shrink_rate r, lane_base, row_gap, switchbacks,
turn_jitter, decoy_depth_frac, floor_drop, barrier_rise, base_stiffness, seed)`.

## Fitness — graph-path-based (value is gameable here)

With decoys, "deepest value reached" rewards diving into a deep dead end. Credit =
progress along the **unique tree path root→global leaf**:
`score = (index of deepest on-true-path basin actually entered) / (true path length)`.
A point "enters basin b" if its nearest skeleton edge is on b's subtree path and perp
penalty is below the basin's barrier. Secondary diagnostic: value-based normalized depth
(kept for reporting, not for the gate).

## Adversarial insanity gate (the success criterion)

`diagnose.py` gains a certifier per instance:
- **Faithfulness:** realized tree matches the spec (minima count, barriers = LCA heights,
  no spurious extrema, no-skip separation holds).
- **Hardness:** run DE / CMA-ES / basin-hopping / random at the instance budget and ASSERT
  every classical score `< HARD_THRESH` (e.g. 0.1).
- **Solvability:** the oracle path-follower (privileged: uses ground-truth skeleton + tree
  path) scores `≥ 0.95`. Proves the instance is solvable by sequential discovery, not
  merely impossible/buggy.

An instance that any classical method solves is **rejected as too easy**; one the oracle
can't solve is **rejected as broken**. Hardness becomes a certified property, not a vibe.

## Difficulty ladder (insanity dial)

Knobs: `shrink_rate`, `tube_radius/base_stiffness`, `depth/branch_factor` (⇒ chain length
N), `dim`, `turn_jitter`, `decoy count/depth`, `barrier_rise`. Ladder from "DE scrapes
~0.2" to "all classics pinned at 0.00, oracle 1.0". Built/tuned by running the gate and
tightening knobs until classics fail.

## Build order (TDD; gate is the loop)

1. `maze.py`: tidy layout + tree skeleton + winding edges + per-depth stiffness + tree
   floor + `__call__`/`basin_of`/`true_path`. RED→GREEN per piece.
2. Path-based fitness in `validate.py` (new `MazeLandscape` branch; chain path untouched).
3. Oracle path-follower (skeleton-aware) — existence proof.
4. Adversarial certifier in `diagnose.py` (faithful + hard + solvable).
5. `specs.py`: maze ladder.
6. Tune knobs via the gate until classics fail + oracle wins; benchmark table.

## Risks

- **Geometry collisions** when winding edges + tidy lanes overlap ⇒ false shortcuts.
  Mitigation: switchback amplitude `< lane(d)/3`; verifier asserts min non-adjacent
  segment separation.
- **Oracle too weak** ⇒ can't certify solvability. Mitigation: oracle is privileged
  (ground-truth skeleton), not a fair optimizer.
- **CMA accidentally follows smooth valleys.** Mitigation: turn_jitter + shrink_rate are
  the knobs we tighten until it fails; that's what the gate is for.
- **Over-tuning to these 4 classics.** Note in report: gate proves "beats *these*
  baselines", not "unconditionally unsolvable". Honest framing.
