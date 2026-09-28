---
name: experiment-implement
description: Implement a pre-registered experiment (Phase 4 Steps 0-3). Writes code, configs, launch script, watchdog, runs smoke test, and validates. Triggers on "implement experiment" or dispatched by /run-experiment when status is preregistered.
argument-hint: <task/name>
model: opus
---

# Experiment Implement: $ARGUMENTS

Implement code and configuration for a pre-registered experiment.

## Step 0 — Gate check: status must be preregistered

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest gate preregistered
```

## Step 1 — Read CONTEXT.md

Read `experiments/<task>/CONTEXT.md` for task tools, eval timing, infrastructure, known bugs.

## Step 2 — Read and address review concerns

Read `experiments/$EXP/01_design.md` and `experiments/$EXP/02_review.md`. Enumerate every Volkov concern from 02_review.md and verify each is addressed in the implementation.

## Step 3 — Run check_phase_order.sh

```bash
PROJ="$(git rev-parse --show-toplevel)"
bash $PROJ/tools/experiment/check_phase_order.sh "$EXP"
```

Hard gate — fix issues before continuing.

## Step 4 — Research existing patterns (if needed)

If the experiment uses a novel technique, use local search (`rg`, existing experiment directories, and relevant docs) to find related code patterns before implementing.

## Step 4a — Generate GSD implementation plan

Read `experiments/$EXP/01_design.md` and `experiments/$EXP/codebase_map.md` (if exists from design phase).
Read `experiments/PATTERNS.md` section "Known Failures" for failure patterns relevant to this experiment type.

Create the plan directory and generate a structured implementation plan:

```bash
EXP='$ARGUMENTS'
PROJ="\$(git rev-parse --show-toplevel)"
mkdir -p "\$PROJ/experiments/$EXP/plans"
```

Generate `experiments/$EXP/plans/implement-PLAN.md` following the GSD plan format. Parse 01_design.md to create tasks in these categories:

1. **Code tasks**: Create/modify experiment-specific code (pipeline configs, validate.py, prompts). Map from the Treatment specification section of 01_design.md.
2. **Config tasks**: Fill experiment.yaml fields (runs, servers, config, custom_env). Map from the Config specification section.
3. **Script tasks**: Generate launch.sh, write watchdog config, write test eval script.
4. **Verification tasks**: Treatment verification checks, implementation alignment check. Map from the Control invariants and Treatment verification sections.

Each task must have:
- Explicit file paths (from `codebase_map.md` if available, otherwise from 01_design.md treatment specification)
- Concrete acceptance criteria (what grep/command proves the task is done)
- Known failure avoidance (reference KF-XX entries from PATTERNS.md that apply to this experiment type)

**Plan scope boundary**: The plan covers the work currently in Steps 5a through 10b (code, config, manifest, launch.sh, watchdog, treatment verification, alignment check). Steps 11+ (smoke test, status update, commit) remain as explicit skill steps OUTSIDE the plan. The plan's goal is: "produce all artifacts needed for smoke test."

## Step 4b — Researcher approves implementation plan

Present the generated plan summary to the researcher:
- Number of tasks and estimated scope
- Files to be created/modified
- Known failure mitigations included (which KF-XX entries were addressed)
- Plan scope: "This plan covers implementation through treatment verification. Smoke test and commit are separate skill steps after plan execution."

Ask: "Implementation plan generated at `experiments/$EXP/plans/implement-PLAN.md`. Review and approve? (yes / revise / abort)"

- **yes**: Proceed to Step 4c
- **revise**: Incorporate feedback and regenerate the plan, then re-present
- **abort**: Stop the skill entirely

Do NOT proceed without explicit approval. This is a human gate (D-04).

## Step 4c — Execute implementation plan

Execute each task in `experiments/$EXP/plans/implement-PLAN.md` sequentially. For each task:
1. Read the task specification (files, action, acceptance criteria)
2. Implement the change as specified
3. Run the verification check from the task
4. If the task modifies files, commit atomically with message: `feat($EXP): <task description>`

After all plan tasks complete, create `experiments/$EXP/plans/implement-SUMMARY.md` documenting:
- Tasks completed (count and names)
- Files created/modified
- Known failures avoided
- Any deviations from the plan

Then continue to Step 5 (local impact review) as normal.

## Step 5 — Local impact review

Before modifying shared code, map the likely callers and configuration entry points with local search:

```bash
rg -n "SymbolName|config_key|class_name" gigaevo config experiments tests
```

If the search shows broad shared-code impact, summarize the affected callers and ask the researcher before continuing. For experiment-local files, document the expected scope in the implementation summary.

## Step 5a — Implement code and config

Write experiment-specific code: pipeline YAML, validate.py changes, prompt files, chain components. See `references/config-patterns.md` for pipeline selection rules, prompts_dir placement, and Hydra config patterns.

## Step 6 — Run tests

Use `/run-tests` — hard gate. All tests must pass.

## Step 6a — Code review (use `superpowers:requesting-code-review`)

Review implementation code from Step 5. Skip if only minor config changes (no new Python code).

## Step 7 — Complete experiment.yaml (with auto resource assignment)

Manually pick servers and Redis DBs. See `experiments/infrastructure.yaml` for available resources.

```bash
EXP='$ARGUMENTS'
# Check how many runs are defined (if any)
gigaevo -e "$EXP" manifest get runs --format json | jq length
```

Review available servers and free Redis DBs in `experiments/infrastructure.yaml`. Assign resources manually based on the number of runs needed (default: 4 — 2 treatment + 2 control).

Fill in: `runs[]` (with chosen DBs), `servers[]` (with chosen servers), `config{}`, `custom_env{}`, `tools[]`.

## Step 7a — Configure watchdog monitoring

Write the `watchdog:` section in experiment.yaml using the design doc proposal and auto-detection:

1. Read `experiments/$EXP/01_design.md` for the proposed monitoring config (from design Step 5a)
2. Auto-detect plugin from run prefixes:
   - Runs with `pop_a`/`pop_b` prefixes → `plugin: adversarial`
   - Runs with `prompt_evolution` in prefix → `plugin: prompt_coevo`
   - Otherwise → `plugin: solo`
3. Confirm with researcher: "The design proposes these plot metrics and alert thresholds. Should I adjust anything?"
   - Which metrics to plot (from `metrics.yaml`)
   - Alert thresholds (`invalidity_rate`, `stagnation_window`)
   - Plot commands (`arms-race`/`comparison`/`trajectory` with specific args)
4. Write the `watchdog:` section in experiment.yaml with confirmed values
5. Validate the manifest:

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest gate preregistered
```

Reference: `gigaevo/monitoring/manifest_schema.py` (`WatchdogSection` schema)

## Step 8 — Generate launch.sh

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" launch --generate-script
```

`--generate-script` writes `experiments/$EXP/launch.sh` (chmod +x) from `experiment.yaml` and exits without preflight, DB claims, or exec. Review the generated launch.sh to verify correctness.

## Step 9 — Write test eval (watchdog is CLI-driven)

The watchdog runs via `gigaevo -e <task>/<name> watchdog` — no per-experiment
Python entry point is needed. The CLI reads `control_plane.watchdog` from
`experiment.yaml` (already filled in Step 7a) and auto-resolves the plugin.

- `run_test_eval.sh` — copy from `experiments/_template/` only if
  `problem.has_test_set` is true

## Step 10 — Treatment verification (hard gate, iterative)

Run the `treatment-verifier` agent. Repeat until all CRITICAL fallbacks are covered. See `references/treatment-verification.md` for the full workflow, treatment_checks schema, and common silent fallback modes.

## Step 10b — Implementation alignment check (hard gate)

Run the `implementation-aligner` agent. This checks: **does the code actually implement what `01_design.md` describes?**

The implementation-aligner:
1. Reads the treatment specification from `experiments/$EXP/01_design.md`
2. Reads `experiments/$EXP/codebase_map.md` (from design phase) if it exists
3. Diffs all code changes introduced by this experiment branch (`git diff main...HEAD`)
4. Produces an alignment matrix: for each design requirement, is there a corresponding code change?
5. Issues verdict: **ALIGNED** or **MISALIGNED** with specific gaps

**If MISALIGNED**: Fix each gap reported and re-run the implementation-aligner. This is a hard gate — do NOT proceed to smoke test with a MISALIGNED verdict.

Common gap patterns to fix:
- Design says "treatment runs use X" but config change affects ALL runs → scope to treatment config file
- Design says "extra_overrides include Z" but Z is not in experiment.yaml → add to runs[].extra_overrides
- Codebase_map identified entry point A but implementing agent modified B instead → re-read codebase_map
- Code adds feature unconditionally; design says treatment-only → add Hydra config branching

Record alignment check result:
```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest update lifecycle.treatment_verification.alignment_check_completed true
gigaevo -e "$EXP" manifest update lifecycle.treatment_verification.alignment_check_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Implementation alignment check recorded in experiment.yaml"
```

> *Rationale (AIDE, 2025; AI Scientist v2, 2025)*: AIDE's solution tree uses metric feedback to prune bad branches before expensive evaluation. The implementation-aligner is the GigaEvo equivalent: if design≠code, the branch dies before wasting GPU compute. This fixes the "agent implemented the wrong thing" failure mode — the most common cause of wasted experiment runs.

Record treatment verification:
```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest update lifecycle.treatment_verification.completed true
gigaevo -e "$EXP" manifest update lifecycle.treatment_verification.completed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Treatment verification recorded in experiment.yaml"
```

## Step 10c — Dry-run launch preview (hard gate)

Generate `LAUNCH_PREVIEW.md` and verify every pin resolves correctly:

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" launch --dry-run
```

This runs preflight (including the pin-match + fingerprint checks) and writes `experiments/$EXP/LAUNCH_PREVIEW.md`. Exits non-zero on any CRITICAL.

**Hard gate** — open `LAUNCH_PREVIEW.md` and verify:
1. **Status line reads `PASS`** with `0 failed` pin assertions. A `FAIL` means the resolved Hydra config does not match `contract.config.pinned` — fix `contract.config.extra`, `runs[].extra_overrides`, or the pin itself before proceeding.
2. **Every pinned row shows `PASS ✓`** in the Match column for every run.
3. **Scan non-pinned rows** — if a value looks wrong for the study (e.g. `num_parents: 2` when the task traditionally uses 1), decide: add a pin, add an override, or accept.
4. **Provenance column** — for each pinned row, the "winning source" column (extra_overrides / config.extra / task group) should match the design's intent. If treatment-specific, the winner should be `extra_overrides` or `config.extra`, not the task group default.

Commit the preview as a pre-launch artifact:

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
cd "$PROJ"
rtk git add "experiments/$EXP/LAUNCH_PREVIEW.md"
rtk git commit -m "preflight($EXP): launch preview — pin contract verified"
```

Do NOT proceed to Step 11 (smoke test) if `LAUNCH_PREVIEW.md` shows any `FAIL ✗` row.

## Step 11 — Smoke test (3 iterations)

Run ONE run for 3 iterations with minimal config. See `references/smoke-test-checklist.md` for verification criteria and common failures.

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
cd "$PROJ"

# 1. Read first run's config from experiment.yaml
gigaevo -e "$EXP" manifest get runs --format json | jq -r '.[0] | "PREFIX=\(.Prefix)\nDB=\(.DB)\nPIPELINE=\(.Pipeline)"'

# 2. Launch smoke run (replace <prefix>, <db>, <pipeline>, <problem> with values above)
nohup $GIGAEVO_PYTHON run.py \
    problem.name=<problem> \
    pipeline=<pipeline> \
    redis.db=<db> \
    max_mutants=3 \
    > experiments/$EXP/smoke.log 2>&1
```

Verify smoke run — check errors, Redis keys, fitness plausibility, custom prompts, treatment checks, then flush smoke DB. See `references/smoke-test-checklist.md` for the full checklist.

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"

# a) No ERROR/CRITICAL in log
grep -c "ERROR\|CRITICAL" experiments/$EXP/smoke.log || echo "0 errors"

# b) Redis has expected keys (replace <db> and <prefix>)
$GIGAEVO_PYTHON -c "
import redis, json
r = redis.Redis(db=<db>)
prefix = '<prefix>'
_raw = r.hget(f'{prefix}:run_state', 'engine:snapshot')
run_state = json.loads(_raw)['programs_processed'] if _raw else None
fitness_hist = r.llen(f'{prefix}:metrics:history:program_metrics:valid_frontier_fitness')
programs = r.keys(f'{prefix}:program:*')
print(f'Programs processed: {run_state}')
print(f'Fitness history entries: {fitness_hist}')
print(f'Programs stored: {len(programs)}')
assert run_state is not None, 'FAIL: run_state missing'
assert fitness_hist > 0, 'FAIL: no fitness history'
print('Redis keys: OK')
"

# c) Fitness plausibility
$GIGAEVO_PYTHON -c "
import redis, json
r = redis.Redis(db=<db>)
prefix = '<prefix>'
entries = [json.loads(v)['v'] for v in r.lrange(f'{prefix}:metrics:history:program_metrics:valid_frontier_fitness', 0, -1)]
print(f'Fitness values: {entries}')
assert all(v > 0 for v in entries), 'FAIL: all-zero fitness'
print('Fitness plausibility: OK')
"

# d) Custom prompts (if applicable)
grep -i "prompts_dir\|loaded prompt\|custom prompt" experiments/$EXP/smoke.log | head -5 || echo "(no custom prompt log lines)"

# e) Treatment checks (HARD GATE)
$GIGAEVO_PYTHON -c "
import yaml, redis, subprocess
with open('experiments/$EXP/experiment.yaml') as f:
    raw = yaml.safe_load(f)
checks = raw.get('treatment_checks', {})
prefix = '<prefix>'
db = <db>
r = redis.Redis(db=db)
failed = []
for pattern in checks.get('redis_key_pattern', []):
    key = pattern.replace('{prefix}', prefix)
    if not r.exists(key):
        failed.append(f'REDIS KEY MISSING: {key}')
for pat in checks.get('log_pattern_present', []):
    result = subprocess.run(['grep', '-c', pat, 'experiments/$EXP/smoke.log'], capture_output=True, text=True)
    if result.returncode != 0:
        failed.append(f'LOG PATTERN NOT FOUND: {pat}')
for pat in checks.get('log_pattern_absent', []):
    result = subprocess.run(['grep', '-c', pat, 'experiments/$EXP/smoke.log'], capture_output=True, text=True)
    if result.returncode == 0:
        failed.append(f'LOG PATTERN SHOULD BE ABSENT: {pat}')
if failed:
    print('TREATMENT CHECKS FAILED (HARD GATE):')
    for f in failed:
        print(f'  {f}')
    raise SystemExit(1)
else:
    print(f'Treatment checks PASSED')
"

# Flush smoke DB
gigaevo flush --db <db> --confirm
```

Update experiment.yaml:
```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest update lifecycle.smoke_test.completed true
gigaevo -e "$EXP" manifest update lifecycle.smoke_test.completed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
gigaevo -e "$EXP" manifest update lifecycle.smoke_test.log_path smoke.log
echo "Smoke test recorded in experiment.yaml"
```

## Step 12 — Watchdog 60s survival test

```bash
EXP='$ARGUMENTS'
timeout 60 gigaevo -e "$EXP" watchdog &
sleep 65
$GIGAEVO_PYTHON -c "
import redis; r = redis.Redis(db=0)
hb = r.get('experiments:$EXP:watchdog_heartbeat')
print(f'Heartbeat: {hb}')
assert hb is not None, 'Watchdog did not write heartbeat'
print('Watchdog survival test PASSED')
"
```

## Step 13 — Set status to implemented

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" manifest update status implemented
```

## Step 14 — Diff scope check + Commit

Verify the diff is scoped to what you intended:

```bash
git status --short
git diff --cached --name-status
git diff --cached --stat
```

```bash
EXP='$ARGUMENTS'
rtk git add "experiments/$EXP/" "config/" "chains/" 2>/dev/null
rtk git commit -m "feat($EXP): implement experiment — code, config, launch, watchdog"
```

## Step 15 — Completion check (use superpowers:verification-before-completion)

```bash
EXP='$ARGUMENTS'

# Gate: status must be implemented
gigaevo -e "$EXP" manifest gate implemented

# Verify runs and servers are defined
RUNS_COUNT=$(gigaevo -e "$EXP" manifest get runs --format json | jq length)
echo "Runs: $RUNS_COUNT"
if [ "$RUNS_COUNT" -eq 0 ]; then
  echo "INCOMPLETE: no runs defined"
  exit 1
fi

# Verify smoke test completed
SMOKE=$(gigaevo -e "$EXP" manifest get lifecycle.smoke_test.completed)
if [ "$SMOKE" != "True" ]; then
  echo "INCOMPLETE: smoke test not completed"
  exit 1
fi

echo "COMPLETE: experiment-implement finished successfully"
```

## Gotchas

- **Issues log** — Log failures to `experiments/$EXP/04_issues_log.md`
- **Read 02_review.md** — skipping Volkov's concerns leads to repeated failures
- **Pipeline must match validate.py** — see `references/config-patterns.md`
- **Treatment verification before smoke** — Step 10 defines checks, Step 11 verifies them
- **Smoke test is mandatory** — launch checks reject without it
- **Flush smoke DB** — stale data contaminates real runs
- **Never hand-edit launch.sh** — regenerate with `gigaevo -e $EXP launch`
- **Treatment verification is a hard gate** — launch checks require `treatment_verification.completed=true`
