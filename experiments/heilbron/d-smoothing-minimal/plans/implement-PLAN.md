# Implementation Plan: heilbron/d-smoothing-minimal

**Goal**: Produce all artifacts needed for smoke test — code edit, metrics metadata update, launch.sh, treatment verification, alignment check, dry-run preview. Smoke test + commit are separate skill steps outside this plan.

**Source docs**:
- `01_design.md` §3 (Treatment), §3.1 (denominator), §3.2 (G-D asymmetry), §5 (controlled variables)
- `02_review.md` — C1 (PASS), M1 (PASS), m1–m6 (PASS)
- `codebase_map.md` — Entry Points table, Silent Fallback Modes, Blast Radius

**Scope boundary**: Plan covers Steps 5a–10b. Steps 11+ (smoke test, watchdog survival, `implemented` gate, commit) are explicit skill steps after plan execution.

---

## Known Failures to Avoid (from PATTERNS.md)

| KF | Risk for this experiment | Mitigation |
|---|---|---|
| **KF-10** | **Frozen `evaluate.py` returning bare dict instead of `(metrics, artifact)` tuple** — would silently disable `DGTrackerStage` / composition injection / gradient-in-prompt | Preserve current `return {}, _artifact()` tuple shape. Verify via Task T1 acceptance check. |
| KF-01 | Missing `evolution=steady_state` — deadlock at gen 0 | Already in all 8 runs' extra_overrides (verified in experiment.yaml). |
| KF-02 | `${}` interpolation refs in extra_overrides need single-quoting at bash emit | `post_step_hook=\${composition_injection_hook}`, `per_opponent_timeout=\${stage_timeout}` — rely on `generate_launch.py` shell-escape. Task T4 grep-verifies. |
| KF-03 | Missing `population_role` — G/D stages mis-dispatch | Already set per-run (constructor/improver). Verified in experiment.yaml. |
| KF-04, KF-11, KF-13 | Composition injection iteration/lineage drops | FIXED on main; not in treatment scope. |
| KF-05, KF-07 | Sync deadlock / min_delta mis-config | Using v2's `drift_cap=100000` (pinned). Not in treatment scope. |

---

## Tasks

### T1 — Treatment code change: pop_b/evaluate.py (tanh smoothing)

**Files**:
- `problems/heilbron_repro_v1/pop_b/evaluate.py`

**Action**:

1. **Happy path (lines 96–99)** — replace hard-floor with tanh:
   ```python
   # BEFORE
   post_q = float(get_smallest_triangle_area(improved))
   raw_delta = post_q - pre_q
   delta = max(raw_delta, 0.0)
   score = min(delta / Q_MAX, 1.0)
   # AFTER
   post_q = float(get_smallest_triangle_area(improved))
   raw_delta = post_q - pre_q
   delta = raw_delta  # signed; downstream DGTrackerStage + mean_improvement_raw use this
   score = 0.5 * (np.tanh(raw_delta / Q_MAX) + 1.0)
   ```

2. **improved-is-None path (lines 91–93)** — raw_delta=0 equivalent under tanh:
   ```python
   # BEFORE
   if improved is None:
       post_q = pre_q
       delta = 0.0
       score = 0.0
   # AFTER
   if improved is None:
       post_q = pre_q
       delta = 0.0
       score = 0.5  # tanh(0)=0 → 0.5 after affine rescale
   ```

3. **Exception path (lines 110–120)** — neutral score 0.5 (design §3 row 2):
   - `scores.append(0.0)` → `scores.append(0.5)`
   - `per_opp_metrics[idx]["score"]: 0.0 → 0.5`
   - `per_opp_metrics[idx]["delta"]: 0.0 → 0.0` (unchanged; raw_delta unknown)

4. **Docstring (line 1)**: change `"binary improvement scoring"` → `"continuous tanh improvement scoring"`.

5. **Module-level comment (line 10)**: drop the `pop_b_soft` legacy reference line (legacy path, no longer relevant — optional tidy).

6. **Preserve invariants**:
   - Return shape: `return {}, _artifact()` (KF-10 guard).
   - `_invalid_opp_metrics()` unchanged — `is_valid=0.0` gates it out of aggregator.
   - `Q_MAX = 0.0365` unchanged.
   - `np` already imported (line 16) — no new imports.

**Acceptance checks**:
```bash
# (a) tanh form present at happy path
grep -n 'np.tanh(raw_delta / Q_MAX)' problems/heilbron_repro_v1/pop_b/evaluate.py

# (b) hard-floor gone
! grep -n 'delta = max(raw_delta, 0.0)' problems/heilbron_repro_v1/pop_b/evaluate.py

# (c) exception-path score = 0.5
grep -nA 8 'except Exception:' problems/heilbron_repro_v1/pop_b/evaluate.py | grep '"score": 0.5'

# (d) KF-10 guard: tuple return preserved
grep -n 'return {}, _artifact()' problems/heilbron_repro_v1/pop_b/evaluate.py
```

**Design reference**: 01_design.md §3 (IV table, rows 1–4), §3.1 (Q_MAX denominator choice).

---

### T2 — Metrics metadata update: pop_b/metrics.yaml

**Files**:
- `problems/heilbron_repro_v1/pop_b/metrics.yaml`

**Action**:

1. **Line 37**: change `mean_improvement_raw.lower_bound: 0.0` → `-0.0365`.
   - Rationale: `delta` field now stores signed `raw_delta`; mean can go negative. `include_in_prompts: false` on this metric → no prompt confound (m2 in 02_review.md).

2. **Explicit non-changes (Volkov C1 freeze)**:
   - `fitness.description` stays verbatim at `"MAP-Elites selection signal: mean over opponent configs of min(improvement / 0.0365, 1). Worsening counts as 0, not negative."` — C1 in 02_review.md requires this text identical to v2.
   - `fitness.lower_bound: 0.0` stays (metadata only; not prompt-rendered per Volkov R2 line 230 observation).
   - All other metrics unchanged.

**Acceptance checks**:
```bash
# (a) mean_improvement_raw lower_bound updated
grep -B 1 -A 9 'mean_improvement_raw:' problems/heilbron_repro_v1/pop_b/metrics.yaml | grep 'lower_bound: -0.0365'

# (b) fitness description FROZEN (C1)
grep 'MAP-Elites selection signal' problems/heilbron_repro_v1/pop_b/metrics.yaml | grep 'Worsening counts as 0, not negative'

# (c) fitness include_in_prompts still true (unchanged)
awk '/^  fitness:/{flag=1} flag && /include_in_prompts/{print; exit}' problems/heilbron_repro_v1/pop_b/metrics.yaml | grep 'true'
```

**Design reference**: 01_design.md §3 (m2 note line 116), §5 (controlled variables row 194–195).

---

### T3 — Run ruff + pytest scope

**Action**:
```bash
/home/jovyan/.mlspace/envs/evo/bin/ruff check problems/heilbron_repro_v1/pop_b/evaluate.py
/home/jovyan/.mlspace/envs/evo/bin/ruff format --check problems/heilbron_repro_v1/pop_b/evaluate.py
```

Use `/run-tests` skill for any existing pop_b tests (narrow scope — do NOT run full suite per feedback_no_full_test_suite).

**Acceptance**: ruff PASS. No new test expected (evaluate.py has no unit test in the repo; behavior is exercised by smoke test T9).

---

### T4 — Regenerate launch.sh via `gigaevo launch --generate-script`

**Files**:
- `experiments/heilbron/d-smoothing-minimal/launch.sh` (new, generated)

**Action**:
```bash
gigaevo -e heilbron/d-smoothing-minimal launch --generate-script
chmod +x experiments/heilbron/d-smoothing-minimal/launch.sh
```

**Acceptance checks**:
```bash
# (a) launch.sh exists + executable
test -x experiments/heilbron/d-smoothing-minimal/launch.sh

# (b) stage_timeout=900 honored (user requirement)
grep -c 'stage_timeout=900' experiments/heilbron/d-smoothing-minimal/launch.sh

# (c) dag_timeout=3600 honored
grep -c 'dag_timeout=3600' experiments/heilbron/d-smoothing-minimal/launch.sh

# (d) KF-02 guard: ${...} interpolation refs single-quoted in bash
grep -c "'post_step_hook=\${composition_injection_hook}'" experiments/heilbron/d-smoothing-minimal/launch.sh
grep -c "'pipeline_builder.per_opponent_timeout=\${stage_timeout}'" experiments/heilbron/d-smoothing-minimal/launch.sh

# (e) 8 runs expanded in launch.sh
grep -cE '^# --- (A1|A2|C1|C2)_[GD] ' experiments/heilbron/d-smoothing-minimal/launch.sh  # expect ~8

# (f) experiment=heilbron (task group) first override
grep 'experiment=heilbron' experiments/heilbron/d-smoothing-minimal/launch.sh | head -1
```

---

### T5 — No test-eval script needed

`problem.has_test_set: false` → skip `run_test_eval.sh`. Documented here for audit trail.

---

### T6 — Treatment verifier agent (Step 10)

Invoke `treatment-verifier` agent with:
- Target experiment: `heilbron/d-smoothing-minimal`
- Treatment variable: D-side fitness formula in `pop_b/evaluate.py`
- IV trace target: `score = 0.5 * (np.tanh(raw_delta / Q_MAX) + 1.0)` at lines ~97–98

Agent MUST confirm:
- No silent fallback path emits `score = 0.0` or `score = min(delta/Q_MAX, 1.0)` in the happy path.
- Treatment is applied unconditionally (no Hydra gate — this is a code-level change, not config).
- `treatment_checks` block in experiment.yaml covers the visible evidence.

**If MISALIGNED**: fix and re-invoke. Hard gate.

---

### T7 — Implementation aligner agent (Step 10b)

Invoke `implementation-aligner` with:
- Design doc: `experiments/heilbron/d-smoothing-minimal/01_design.md`
- Codebase map: `experiments/heilbron/d-smoothing-minimal/codebase_map.md`
- Diff: `git diff main...HEAD -- problems/heilbron_repro_v1/pop_b/`

Agent checks: does the code actually match design §3 (tanh denominator=Q_MAX, exception-path=0.5, metrics.yaml frozen description)?

**If MISALIGNED**: fix gap(s) and re-run. Hard gate.

Record both T6 + T7 completion in manifest:
```bash
gigaevo -e heilbron/d-smoothing-minimal manifest update \
    lifecycle.treatment_verification.completed true
gigaevo -e heilbron/d-smoothing-minimal manifest update \
    lifecycle.treatment_verification.completed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

---

### T8 — Dry-run launch preview (Step 10c)

```bash
gigaevo -e heilbron/d-smoothing-minimal launch --dry-run
```

Generates `experiments/heilbron/d-smoothing-minimal/LAUNCH_PREVIEW.md`. Hard gate:

1. **Status line = PASS** with `0 failed` pin assertions.
2. **Every pinned row = `PASS ✓`** across all 8 runs.
3. **Non-pinned scan** — verify no surprising defaults.
4. **Provenance** — pinned rows should trace to `extra_overrides` or `config.extra`, not accidental task-group default.

Commit the preview:
```bash
rtk git add experiments/heilbron/d-smoothing-minimal/LAUNCH_PREVIEW.md
rtk git commit -m "preflight(heilbron/d-smoothing-minimal): launch preview — pin contract verified"
```

---

## Files to be Created / Modified

| File | Change | Task |
|---|---|---|
| `problems/heilbron_repro_v1/pop_b/evaluate.py` | MODIFY (tanh + exception=0.5 + improved-None=0.5 + docstring) | T1 |
| `problems/heilbron_repro_v1/pop_b/metrics.yaml` | MODIFY (lower_bound -0.0365 on mean_improvement_raw) | T2 |
| `experiments/heilbron/d-smoothing-minimal/launch.sh` | CREATE (generated) | T4 |
| `experiments/heilbron/d-smoothing-minimal/LAUNCH_PREVIEW.md` | CREATE (generated) | T8 |
| `experiments/heilbron/d-smoothing-minimal/experiment.yaml` | UPDATE (lifecycle.treatment_verification.* fields) | T7 |

## Files explicitly NOT touched

- `problems/heilbron_repro_v1/pop_a/` — G-side at main HEAD (PR #219 hotfix); G-D asymmetry accepted per design §3.2.
- `gigaevo/adversarial/*` — SBF-Lineage, opponent providers, stages: inherited verbatim from v2.
- `config/aggregator/heilbron_improver.yaml` — schema-agnostic, reads `score` by name (codebase_map §d=1 blast analysis).
- `problems/heilbron_repro_v1/task_description.txt` — no references to fitness formula (verify once in T1 acceptance).

## Scope contract (Volkov single-IV guard)

Only two files change. Any PR that modifies additional files under `problems/heilbron_repro_v1/` or `gigaevo/` is **out of scope** and fails the single-IV design contract. Implementation aligner (T7) enforces this.
