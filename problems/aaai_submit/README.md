# `problems/aaai_submit/` — interface-ablation problem families

Fourteen problem families from the interface-ablation study, kept together here rather
than in `problems/` because they are a submission bundle: they share one grading
harness and one frozen protocol, and they are only comparable to each other while both
stay fixed. A family that drifted onto the framework's own release cadence would stop
being a arm of the study.

| Group | Families | Task |
|---|---|---|
| ACI | `aci_basic`, `aci_improve`, `aci_improve_warm`, `aci_mixed` | antenna selection, N=50k |
| HEX | `hex23_basic`, `hex23_improve`, `hex23_mixed`, `hex26_adapt` | hexagon packing, n=23 / n=26 |
| HEX range | `hex_range_basic`, `hex_range_improve`, `hexagon_pack_general` | hexagon packing over a range of n |
| Spherical | `spherical_basic`, `spherical_improve`, `spherical_mixed` | spherical codes, 14 (dimension, count) configs |

The `_basic` / `_improve` / `_mixed` suffixes are the ablation itself: what interface the
LLM is given — write a solver directly, write an improver over an incumbent, or choose
per proposal.

## `_harness/`

The shared parts, so that three arms of one benchmark cannot quietly become three
different harnesses:

- `common/` — the sandbox each candidate runs in, the controller the improve-arms drive,
  the wall-clock budget, the proposal contracts, the event log
- `benchmarks/` — the benchmark objects and the `grade*()` functions the fitness comes from
- `protocol/` + `protocol.yaml` — the study constants: grading seed, per-benchmark
  evolution instance, candidate/config/startup budgets, sandbox limits, the spherical
  development split, and the frozen Cohn snapshot the spherical arms are scored against

`protocol.yaml` is the single source for every number that has to be identical across
arms. Change one and the arms stop being comparable, so treat it as frozen.

Two seed pools are excluded from ruff in `pyproject.toml` — `hex26_adapt/initial_programs`
and `aci_improve_warm/initial_programs` — because they are byte-frozen artifacts with
recorded provenance hashes, not source. Formatting them would break the identity that
makes them usable as a baseline.

## Running an arm

`problem.dir` defaults to `${hydra:runtime.cwd}/problems/${problem.name}`, which does
not reach into this bundle, so the directory has to be given explicitly:

```bash
python run.py \
  problem.name=hex23_improve \
  'problem.dir=${hydra:runtime.cwd}/problems/aaai_submit/hex23_improve'
```

Requires the `[optimization]` extra (JAX, shapely). The harness spawns candidates as a
subprocess from the repository root, so launch from the repository root.
