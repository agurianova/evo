# Issues log — heilbron/adversarial-repro-v2

Running record of bugs, broken commands, stale docs, and workflow friction encountered
during implement → launch → run. For systemic fixes see `/post-experiment-fixes`.

## 2026-04-23 — running phase

### I-18 `Program.create_child` drops `iteration` → injected G programs pile up at step=0 on frontier/plots
- **Where**: `gigaevo/programs/program.py:252-267` (`Program.create_child`) and `gigaevo/programs/program.py:134-138` (`iteration: int = Field(default=0, ge=0)`).
- **Symptom**: The `comparison` plot for A1_G / A2_G shows the best-fitness line "starting immediately" at ~0.034 at x=0, which is impossible for early generations. Raw Redis frontier (`heilbron_repro_v1/pop_a:metrics:history:program_metrics:valid_frontier_actual_fitness`) on DB 3 (A2_G): `[{s:0, v:0.03385}, {s:1, v:0.03385}, ..., {s:16, v:0.03385}]` — flat from step 0.
- **Root cause**: `create_child` correctly sets `lineage.generation = max(parent.gen)+1` (that was the I-17 fix) but never touches the top-level `iteration` field, which defaults to `0`. `CompositionInjectionHook` (`gigaevo/adversarial/composition_injection.py:167`) calls `Program.create_child(parents=[g_prog], code=composed_code, mutation="d_improvement")` → the injected G program ships with `iteration=0` even though its parent G is at iteration 10+ and its `lineage.generation` is correctly N+1. `metrics_tracker._process_program` (`gigaevo/utils/metrics_tracker.py:241`) reads `iteration = program.iteration` and writes the frontier/per-iter stats at `step=0`. `_recompute_and_write_frontier` (`metrics_tracker.py:332-379`) then sorts by `iteration` and the iteration=0 injected program wins at step=0, producing a running-best series that is flat at the breakthrough fitness from step 0 onward.
- **Evidence**:
  - A2_G gen=8 best program `05788771` — `mutation=d_improvement`, `injected=True`, `iteration=0`, `lineage.generation=8`, `metrics.actual_fitness=0.03385`.
  - A2_G gen=2 injected program `9c4d68de` — `iteration=0`, `atomic_counter=503`, `lineage.generation=2`, `metrics.actual_fitness=0.02104`, `metadata.g_source_id=1849ce49` (parent G).
  - All 4 G runs (A1_G/A2_G/C1_G/C2_G) show the same `iter=0` signature on every `d_improvement`-mutation program in the archive.
- **Impact**:
  - Plots lie at low x. "Max fitness at gen 0 = 0.034" in the watchdog comparison is a pileup of composition-injected programs with real `lineage.generation` ∈ {2..9}, all mapped to x=0.
  - Frontier *series* is step-indexed by a broken counter. Downstream consumers that read `valid_frontier_fitness` and interpret `s` as generation (checkpoint analyst, diagnose.py, 05_results tables, Telegram PR comments) will mis-attribute the breakthrough moment.
  - Per-iter mean/std stats (`valid/iter/{key}/mean`, `valid/iter/{key}/std`) are polluted by the same pileup.
- **NOT affected**:
  - `lineage.generation` is correct (I-17 holds).
  - Program IDs, fitness values, parent links, pair-level outcomes are all fine — the raw program blobs are good data.
  - Per-gen stats (`valid/gen/{key}/mean`) use `generation = program.generation` (line 242) and are indexed correctly.
- **Workaround (during run)**: none applied — raw program data is correct; only the x-axis of plots and frontier series is wrong. Plots can be regenerated post-hoc from program blobs using `lineage.generation` as the x-axis.
- **Fix (DO NOT apply while v2 is running — per `feedback_no_import_changes_mid_run.md`)**:
  1. Update `Program.create_child` to propagate iteration from parents:
     ```python
     iteration = max((p.iteration for p in parents), default=0)
     return cls(code=code, lineage=lineage, name=name, iteration=iteration)
     ```
  2. `CompositionInjectionHook` (`composition_injection.py:158-167`) should ALSO set `program.iteration` to the engine's current iteration (if accessible via `ctx`) to avoid the off-by-one between "parent's iteration" and "time of injection".
  3. Audit other `Program.create_child` / `Program.from_mutation_spec` callers — mutation pipeline likely sets iteration explicitly via the engine's atomic counter; verify by grepping for `program.iteration = ` in `gigaevo/evolution/`.
  4. TDD test in `tests/adversarial_pipeline/test_composition_injection.py`: `test_injected_program_iteration_matches_g_parent` — asserts `child.iteration >= g_prog.iteration`.
  5. Consider whether the plot + frontier should use `lineage.generation` (correct, monotone per program) or `iteration` (correct IF all callers set it, which is what this bug violates). Current key `valid_frontier_<metric>` is documented as iteration-indexed — don't change the schema without a migration plan.
- **Systemic fix needed**: YES — promote to `PATTERNS.md` Known Failure at closeout. The class of bug is "construction helper silently drops a metadata field, downstream consumer silently fills with default". Affected types: adversarial_asymmetric (and any solo experiment using composition hooks). Status: ACTIVE (to be FIXED at closeout or in a separate PR after v2 completes).
- **Impact on v2 hypothesis**: NONE on the scientific claim. The v2 vs v1 comparison uses `lineage.generation` through the archive, not the iteration-indexed frontier. Only cosmetic for watchdog plots. 05_results analysis should rebuild fitness trajectories from program blobs keyed by `lineage.generation` and flag this bug as a known plotting confound.
