# Implementation Plan — heilbron/d-tanh-no-lineage

**Status:** PROPOSED (awaiting researcher approval at Step 4b)
**Scope:** Steps 5a–10b of `/experiment-implement` — produce all artifacts needed for smoke test.
**Out of scope:** Smoke test (Step 11), watchdog survival (Step 12), status flip (Step 13), commit (Step 14), completion check (Step 15) — remain explicit skill steps.

---

## Sources of truth

- `experiments/heilbron/d-tanh-no-lineage/01_design.md` §11, §13, §3.1, §6.1
- `experiments/heilbron/d-tanh-no-lineage/codebase_map.md` (Entry Points, Hydra Wiring, Recommended Treatment Specification)
- `experiments/heilbron/d-tanh-no-lineage/02_review.md` (Volkov, APPROVED round 4 + one Minor m1 recorded)
- `experiments/PATTERNS.md` Known Failures (KF-01..KF-13)

## Volkov concerns to address (from 02_review.md)

| Concern | Round | Status entering implementation |
|---|---|---|
| C1 — D/G ratio threshold uncalibrated | round 1 | RESOLVED in 01_design.md §2.2a/§10/§14.2/§15.2 (graded zones); implementation MUST surface gen-5 ratio in checkpoint output (covered by watchdog config in experiment.yaml — already filled). |
| M1 — d-smoothing-minimal comparison framing | round 1 | RESOLVED in design §1; no implementation work required. |
| M2 — implementation ordering hazard | round 1 | **IMPLEMENTATION-CRITICAL** — see Code task C1 below. The `disable_lineage_on_improver` gate MUST short-circuit BEFORE `_resolve_lineage_filter` is called. |
| Researcher correction (cache semantics) | round 2 | DOC-only fix in §3.1. No code work. |
| Researcher correction (pass-2 semantics) | round 3 | DOC-only fix in §3.1. No code work. |
| `refresh_passes` 2→1 derivation | round 4 | Encoded in experiment.yaml D extra_overrides (`engine_config.refresh_passes=1`). Verified by `--cfg job` in Step 10c. |
| m1 — `get_top_k` 30s cache TTL race | round 4 | Minor, non-confounding (uniform across all D runs). No code change; documented as accepted. |

---

## Tasks

Each task lists: **files**, **action**, **acceptance**, **KF references**.

### C1 — Add `disable_lineage_on_improver` kwarg + ordering-safe gate

- **File:** `gigaevo/adversarial/asymmetric_pipeline.py` (lines 162, 187–215)
- **Action:**
  1. Add new keyword-only kwarg to `AdversarialAsymmetricPipelineBuilder.__init__` after the existing `lineage_filter` param:
     ```python
     lineage_filter: LineageFilterConfig | DictConfig | None = None,
     disable_lineage_on_improver: bool = False,   # NEW
     ```
  2. **Ordering-safe gate** in the `if population_role == "improver":` block (lines 206–215). Wrap the existing two-call body so `disable_lineage_on_improver=True` short-circuits **before** `_resolve_lineage_filter` is invoked (Volkov M2):
     ```python
     if population_role == "improver":
         if disable_lineage_on_improver:
             self.remove_stage("LineageStage")
             self.remove_stage("LineagesToDescendants")
             self.remove_stage("LineagesFromAncestors")
             logger.info(
                 "[AsymmetricPipeline] disable_lineage_on_improver=true: "
                 "removed LineageStage, LineagesToDescendants, LineagesFromAncestors"
             )
         else:
             resolved_filter = _resolve_lineage_filter(
                 lineage_filter, ctx.problem_ctx.metrics_context
             )
             self._replace_lineage_with_filtered(
                 ctx, dg_tracker, resolved_filter, stage_timeout,
             )
     ```
- **Acceptance:**
  - `grep -n "disable_lineage_on_improver" gigaevo/adversarial/asymmetric_pipeline.py` → 4 hits (kwarg, gate, log, end).
  - `python -c "from gigaevo.adversarial.asymmetric_pipeline import AdversarialAsymmetricPipelineBuilder; import inspect; assert 'disable_lineage_on_improver' in inspect.signature(AdversarialAsymmetricPipelineBuilder.__init__).parameters"` → exit 0.
  - Log line text exactly matches treatment_check `log_pattern_present` regex `\[AsymmetricPipeline\] disable_lineage_on_improver=true: removed LineageStage,`.
- **GitNexus impact:** before edit, run `gitnexus_impact({target: "AdversarialAsymmetricPipelineBuilder.__init__", direction: "upstream"})`. New kwarg defaults to `False` → callers unaffected by construction.
- **Known failures touched:** KF-01 (steady_state present in extra_overrides — verify), KF-03 (population_role required — verified in experiment.yaml).

### C2 — Hydra config wiring for `disable_lineage_on_improver`

- **File:** `config/pipeline/adversarial_asymmetric.yaml` (around line 124, the `pipeline_builder:` block)
- **Action:** Add `disable_lineage_on_improver: false` as a default under `pipeline_builder:` so Hydra override `pipeline_builder.disable_lineage_on_improver=true` resolves without `+` prefix. Mirrors the existing `archive_reeval: false` default at line 124.
- **Why this is required:** experiment.yaml D extra_overrides use `pipeline_builder.disable_lineage_on_improver=true` without `+`. Hydra raises `ConfigKeyError` if the key is absent at compose time.
- **Acceptance:**
  - `grep -n "disable_lineage_on_improver" config/pipeline/adversarial_asymmetric.yaml` → 1 hit, value `false`.
  - Smoke test (Step 11) passes `--cfg job` inspection without `+`.
- **Blast radius (GitNexus):** YAML-only; affects all pipelines that inherit `adversarial_asymmetric` (heilbron_repro_v1 ✓, others). Default `false` → no behavioural change for any existing experiment.

### T1 — Unit test for ordering invariant

- **File:** `tests/adversarial_pipeline/test_disable_lineage_on_improver.py` (NEW)
- **Action:** Add three tests as specified in 01_design.md §13.1 ("Required unit test"):
  1. `test_no_lineage_on_improver_skips_filter_resolution`: instantiate `AdversarialAsymmetricPipelineBuilder` with `population_role="improver"`, `disable_lineage_on_improver=True`, `lineage_filter=None`. Assert no `ValueError` raised; `"LineageStage"`, `"LineagesToDescendants"`, `"LineagesFromAncestors"` absent from `builder._nodes`.
  2. `test_default_false_preserves_v2_behavior`: same fixture but `disable_lineage_on_improver=False` (default), `lineage_filter=<valid LineageFilterConfig>`. Assert lineage stages remain wired (e.g. `"LineageStage" in builder._nodes` after `_replace_lineage_with_filtered`).
  3. `test_constructor_role_unaffected`: `population_role="constructor"`, `disable_lineage_on_improver=True`. Assert `"LineageStage"` still present (treatment is D-only).
- **Acceptance:**
  - `/run-tests tests/adversarial_pipeline/test_disable_lineage_on_improver.py` → 3 passed.
  - Tests must instantiate the real builder (no monkey-patching of `_resolve_lineage_filter`); ordering invariant is the contract under test.
- **KF reference:** Volkov M2 — this test is the regression harness against future refactors that might re-order the gate.

### V1 — Run full test suite (skill Step 6)

- **Command:** `/run-tests tests/adversarial_pipeline/`
- **Acceptance:** all tests in `tests/adversarial_pipeline/` pass. Hard gate per skill Step 6.
- **Failure ⇒ KF-precedent:** never run `pytest tests/` — see memory `feedback_no_full_test_suite.md`. Target the directory.

### V2 — Code review (skill Step 6a)

- Invoke `superpowers:requesting-code-review` for the asymmetric_pipeline.py + adversarial_asymmetric.yaml diff (C1 + C2 + T1).
- **Acceptance:** review approved or comments addressed.

### S1 — Verify experiment.yaml runs/servers/watchdog (skill Steps 7, 7a)

- **File:** `experiments/heilbron/d-tanh-no-lineage/experiment.yaml`
- **Action:** Already pre-filled (PR #223). Read-only verification:
  - `runs[]` contains 8 entries (4 G + 4 D, paired arms A1/A2/C1/C2).
  - All D runs have `pipeline_builder.disable_lineage_on_improver=true` AND `engine_config.refresh_passes=1` AND `pipeline_builder.archive_reeval=true` AND `opponent_result_mode=cached` AND `opponent_sampling_mode=top_k` AND `engine_config.refresh_order=generation_bucketed`.
  - All G runs do **not** have `disable_lineage_on_improver` override (default false applies).
  - All runs have `population_role` set (KF-03), `evolution=steady_state` or pipeline default (KF-01), and `aggregator=heilbron_constructor|heilbron_improver` (per role).
  - Watchdog `plugin: adversarial`, `paired:` strings include all 4 G:D pairs, alert thresholds `invalidity_rate: 0.75`, `stagnation_window: 15` (matches design §15.1).
- **Acceptance:** `gigaevo -e heilbron/d-tanh-no-lineage manifest gate preregistered` → exit 0.

### S2 — Generate launch.sh (skill Step 8)

- **Command:** `gigaevo -e heilbron/d-tanh-no-lineage launch --generate-script`
- **Acceptance:** `experiments/heilbron/d-tanh-no-lineage/launch.sh` exists and is `chmod +x`. Spot-check that all 8 runs appear, single-quoted Hydra `${}` interpolations are preserved (KF-02), and `population_role` overrides emit literally for each run.
- **No hand-editing** — regenerate if wrong.

### S3 — Test eval script (skill Step 9)

- **Action:** **SKIP.** Heilbron N=11 is synthetic (`problem.has_test_set: false` per design §17.2 and dataset_snapshot.json note). No `run_test_eval.sh` needed.
- **Acceptance:** N/A.

### V3 — Treatment-verifier agent (skill Step 10, hard gate, iterative)

- **Action:** Invoke `treatment-verifier` agent with `EXP=heilbron/d-tanh-no-lineage` and the full treatment specification from 01_design.md §11 + §13.
- **Iteration loop:** Repeat until all CRITICAL silent fallbacks are covered by `treatment_checks` block in experiment.yaml. The 7 d_treatment_checks already in experiment.yaml may be sufficient — verifier will confirm or extend.
- **Acceptance:** `gigaevo -e heilbron/d-tanh-no-lineage manifest update lifecycle.treatment_verification.completed true` succeeds; verifier returns no CRITICAL gaps.

### V4 — Implementation-aligner agent (skill Step 10b, hard gate)

- **Action:** Invoke `implementation-aligner` with the design's treatment specification and `git diff main...HEAD`.
- **Acceptance:** Verdict **ALIGNED**. If MISALIGNED, fix the gap and re-run before proceeding.
- **Likely alignment matrix to verify:**
  | Design requirement | Code change |
  |---|---|
  | New kwarg `disable_lineage_on_improver: bool = False` | C1 (asymmetric_pipeline.py:162) |
  | Gate before `_resolve_lineage_filter` | C1 (asymmetric_pipeline.py:206–215) |
  | Activation log line exact text | C1 logger.info |
  | Hydra default exists for override resolution | C2 (adversarial_asymmetric.yaml) |
  | Ordering invariant test | T1 |
  | D extra_overrides include disable_lineage + refresh_passes=1 + archive_reeval=true | S1 (already in experiment.yaml) |
  | G extra_overrides do NOT include disable_lineage | S1 (already in experiment.yaml) |
  | pop_b/evaluate.py tanh change present | inherited from PR #222 commit 3eb41b43 |

### V5 — Dry-run launch preview (skill Step 10c, hard gate)

- **Command:** `gigaevo -e heilbron/d-tanh-no-lineage launch --dry-run`
- **Acceptance:** `LAUNCH_PREVIEW.md` shows status `PASS`, `0 failed` pin assertions; every pinned row green; provenance column correct (treatment-specific values from `extra_overrides`, not group defaults).
- **Commit preview:** `rtk git add experiments/heilbron/d-tanh-no-lineage/LAUNCH_PREVIEW.md && rtk git commit -m "preflight(heilbron/d-tanh-no-lineage): launch preview — pin contract verified"`.

---

## Plan boundary

After V5 completes, this plan is **DONE**. The skill resumes at:
- Step 11 (3-gen smoke on DB 11/12, treatment-check verification, flush smoke DB)
- Step 12 (60s watchdog survival)
- Step 13 (`status=implemented`)
- Step 14 (GitNexus scope check + final commit)
- Step 15 (completion gate)

Each post-plan step is atomic, idempotent, and explicit in the skill body — no plan needed.

---

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Hydra `ConfigKeyError` on D launch (key missing) | LOW (caught at smoke/dry-run) | C2 adds default to `adversarial_asymmetric.yaml`. |
| Ordering invariant violation (gate after `_resolve_lineage_filter`) | LOW | T1 unit test + treatment_check `log_pattern_absent: lineage_filter.aggregator required`. |
| `MutationContextStage` chokes on `None` lineage inputs | VERY LOW | codebase_map.md confirms `Optional[...]` typing + null-safe compute. T1 indirectly validates via builder construction. |
| `_wire_cache_on_edges` breaks because `LineageStage` removed | VERY LOW | `_wire_cache_on_edges` already guards `if "LineageStage" in self._nodes` at line 313–314. |
| Activation log line missed by treatment-check regex | LOW | Acceptance criterion in C1 verifies exact regex match. |
| KF-09 (engine:total_generations=0 not persisted) pollutes early checkpoints | LOW | OPEN platform issue, not specific to this experiment. Watchdog reads from `:run_state` after first step completes. |

---

## Estimated scope

- **Files modified:** 2 (`asymmetric_pipeline.py`, `adversarial_asymmetric.yaml`)
- **Files added:** 1 (`tests/adversarial_pipeline/test_disable_lineage_on_improver.py`)
- **LOC:** ~10–15 production + ~40 test
- **Pre-launch artefacts:** `launch.sh`, `LAUNCH_PREVIEW.md`
- **Atomic commits:** 4 (`feat: kwarg + gate`, `feat: hydra default`, `test: ordering invariant`, `preflight: launch preview`)

---

*Plan generated 2026-04-25. Awaits researcher approval at /experiment-implement Step 4b.*
