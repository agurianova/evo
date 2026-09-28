---
name: experiment-design
description: Design a new GigaEvo experiment (Phases 0-2). Creates experiment directory, runs Elena design + Volkov review, fills experiment.yaml, and pre-registers. Triggers on "design experiment", "new experiment", or dispatched by /run-experiment when no experiment.yaml exists.
argument-hint: <task/name> <research-question>
model: opus
---

# Experiment Design: $ARGUMENTS

Design and pre-register a new experiment. Parse $ARGUMENTS as `<task/name> <research-question>`.

## Step 0 — Verify experiment does not exist

```bash
PROJ="$(git rev-parse --show-toplevel)"
EXP=$(echo '$ARGUMENTS' | awk '{print $1}')
TASK=$(echo "$EXP" | cut -d/ -f1)
if [ -f "$PROJ/experiments/$EXP/experiment.yaml" ]; then
  echo "BLOCKED: experiment.yaml already exists for $EXP. Use /run-experiment to continue."
  exit 1
fi
echo "GATE PASSED: no existing experiment.yaml for $EXP"
```

## Step 1 — Create experiment directory from template

```bash
EXP=$(echo '$ARGUMENTS' | awk '{print $1}')
PROJ="$(git rev-parse --show-toplevel)"
mkdir -p "$PROJ/experiments/$EXP"
for f in experiment.yaml 01_design.md 02_review.md 03_plan.md 05_results.md PR_DESCRIPTION.md; do
  [ ! -f "$PROJ/experiments/$EXP/$f" ] && cp "$PROJ/experiments/_template/$f" "$PROJ/experiments/$EXP/$f"
done
echo "Created experiment directory from template"
```

## Step 2 — Read task CONTEXT.md and INDEX.md

Read `experiments/<task>/CONTEXT.md` for benchmarks, infrastructure, task tools, known bugs, and prior art.
Read `experiments/INDEX.md` for the experiment ledger.
These provide institutional memory — read them before designing.

## Step 2a — Literature search (automated, forked context)

Invoke the `/experiment-literature-search` skill with the research question and task name. This runs in a forked context and produces a structured brief covering:
- Related external work (papers, approaches, baselines)
- Prior GigaEvo experiments on the same task
- Novelty assessment
- Recommendations for the designer

The brief is saved to `experiments/$EXP/literature_brief.md`. Elena reads this before designing.

## Step 2b — Codebase reconnaissance (automated, forked context)

Invoke the `code-archaeologist` agent with the research question and task name. This agent:
1. Maps which code components the proposed mechanism will touch
2. Identifies entry points, Hydra wiring, and silent fallback modes
3. Assesses implementation feasibility (GREEN / YELLOW / RED)
4. Recommends a concrete treatment specification with file paths and class names

Output is saved to `experiments/$EXP/codebase_map.md`.

If the archaeologist returns **RED** feasibility: stop and present the specific blocker to the researcher before proceeding. Do NOT design around an infeasible treatment — either simplify the hypothesis or get researcher input on how to decompose it.

Elena reads `codebase_map.md` in Step 3 alongside the literature brief. This ensures the treatment section cites specific code components (file paths, config keys, class names) rather than vague mechanism descriptions.

> *Rationale (R&D-Agent, 2024; AI Scientist v2, 2025)*: Separating codebase reconnaissance from design is the key innovation in R&D-Agent. When the Research agent has a concrete "code map" before designing, the Development agent faces no ambiguity. Without this step, the implementing agent guesses the mapping — which is the root cause of design-implementation gap.

## Step 3 — Phase 1: Invoke Elena (experiment design)

Use the `ml-research-methodologist` agent with:
- The literature brief from Step 2a
- The research question from $ARGUMENTS
- Context from CONTEXT.md, INDEX.md, and PATTERNS.md (shared knowledge stores)
- The 01_design.md template as output target

Elena MUST include a **Treatment Verification** section in 01_design.md that answers:
1. **What observable evidence proves the treatment is actually applied?** (e.g. "prompt_stats Redis keys should appear after gen 3")
2. **What `extra_overrides` will each treatment run use?** (these are automatically verified against the Hydra cfg dump by diagnose.py Check 12)

Elena MUST use `codebase_map.md` (from Step 2b) to write the treatment section. The treatment specification must include:
- **Specific files and classes** that implement the mechanism (from codebase_map.md Entry Points table)
- **Exact Hydra overrides** that activate the treatment (from codebase_map.md Hydra Wiring)
- **What will be isolated** between treatment and control runs

Elena does NOT need to trace silent fallback modes — the `treatment-verifier` agent does that during `/experiment-implement` (Step 10). Elena's job is to write a treatment that the implementing agent can follow precisely without guessing.

**Do NOT wait for researcher approval here** — proceed directly to Volkov (Step 4). The single researcher gate is after Volkov's review (Step 4c).

## Step 4 — Phase 2: Invoke Volkov (adversarial review)

Use the `reviewer-2-adversary` agent with the completed 01_design.md.

Volkov focuses on:
- **Confound detection** — hidden IVs, silent fallback modes, co-varying variables
- **Treatment integrity** — can the treatment silently fail? Is there runtime verification?
- **Design quality** — is the comparison fair? Are controlled variables truly controlled?
- **Information gain** — given prior experiments, is this the highest-value next experiment?
- **Novelty check** — does the literature brief show this was already tried?
- N >= 2 per cell for factorial designs
- No compound confounds (single IV per comparison)
- **Stopping rule is specific and non-vague** — "when results look good" or an empty section are grounds for NEEDS REVISION

Write the review to 02_review.md.

## Step 4a — Auto-resolve Minor concerns

If Volkov's verdict is NEEDS REVISION with **only Minor** concerns (no Major or Critical):
- Elena auto-resolves the Minor concerns in 01_design.md without researcher involvement
- Re-invoke Volkov for a quick re-check
- This avoids unnecessary researcher gates for trivial issues

## Step 4b — Loop on Major/Critical concerns

If Volkov's verdict is NEEDS REVISION with Major or Critical concerns:
- Send Volkov's concerns back to Elena
- Elena revises 01_design.md
- Re-invoke Volkov
- Loop until APPROVED (no cap on rounds)

## Step 4c — RESEARCHER APPROVAL GATE

**This is the single human gate in the design flow.** After Volkov issues APPROVED:

Ask the researcher: "Please review `experiments/$EXP/01_design.md` and `experiments/$EXP/02_review.md`. The Literature Scout → Elena → Volkov chain has completed. Is the design approved? Type 'approved' to proceed with pre-registration."

Do NOT proceed without explicit researcher approval.

## Step 5 — Fill experiment.yaml

Fill the experiment section of experiment.yaml:
- `experiment.name`, `experiment.task`, `experiment.status: preregistered`
- `experiment.max_generations`, `experiment.branch`
- `problem.*` fields (has_test_set, fitness_type, metric_name, etc.)
- Stopping criterion: pick a Hydra stopper from `config/stopper/` (e.g. `max_generations`, `fitness_plateau`, `max_generations_or_fitness_plateau`, `wall_clock`). Document the choice in 01_design.md prose and note the corresponding `stopper=<name>` override for experiment-implement.
- `baseline.*` if a baseline experiment exists

Leave `runs`, `servers`, `launch`, `smoke_test` empty — those are filled in `/experiment-implement`.

**Fill `contract.config` now — this is the declared-intent contract:**
- `contract.config.task_group`: pick from `config/experiment/*.yaml` (e.g. `heilbron`) if a task-level tradition file exists for this task. Emits `experiment=<task_group>` as the first Hydra override at launch. Leave `null` if no matching group.
- `contract.config.extra`: scalar Hydra overrides shared across runs (e.g. `{n_opponents: 3, source_prompt_k: 3}`). These are the parameters that define this experiment's setup.
- `contract.config.pinned`: **assertion contract**. For every parameter named in the design's treatment specification, add it here with the value the design requires. Preflight diffs `pinned` against the resolved Hydra config and fails CRITICAL on drift. Typos in pin keys → CRITICAL. If a pin is present in `pinned` but not yet overridable via the code path, that's a design gap — catch it now, not at launch.

Pinning guidance for Elena:
- **Pin every treatment variable.** If the design says "K=3 opponents per mutation" the manifest must pin `n_opponents: 3`.
- **Pin tacit conventions worth asserting.** If the design relies on `num_parents: 1` (Heilbron tradition), pin it even though the task group provides it — the pin is a contract against the group-file drifting.
- **Do NOT pin every knob** — only parameters the design's hypothesis depends on. Pinning an irrelevant knob creates a false positive when that knob is innocently updated later.
- **Same-named knob, different path:** use dotted paths (e.g. `pipeline_builder.archive_reeval: true`). Preview and preflight check the exact dotted key.

## Step 5a — Propose monitoring configuration

Based on the experiment type, propose a `watchdog:` section for inclusion in experiment.yaml. Include the proposed config in the Monitoring section of 01_design.md so the researcher can review it alongside the design.

**For solo MAP-Elites experiments:**
```yaml
watchdog:
  plugin: solo
  plot_metrics: [primary_metric_from_metrics.yaml]
  plot_commands:
    - command: comparison
      args: {metric: primary_metric, smoothing: ema, window: 5}
      caption: "Fitness comparison"
  alert_thresholds:
    invalidity_rate: 0.75
    stagnation_window: 10
```

**For adversarial pair experiments:**
```yaml
watchdog:
  plugin: adversarial
  plot_metrics: [primary_metric]
  plot_commands:
    - command: arms-race
      args: {metric: primary_metric, paired: "G_label:D_label,..."}
      caption: "Arms-race dynamics"
    - command: comparison
      args: {metric: primary_metric, smoothing: ema, window: 10, annotate-frontier: true, no-frontier-for: "D_labels"}
      caption: "All runs vs SOTA"
  alert_thresholds:
    invalidity_rate: 0.75
    stagnation_window: 10
```

**For prompt co-evolution experiments:**
```yaml
watchdog:
  plugin: prompt_coevo
  plot_metrics: [primary_metric]
  plot_commands:
    - command: comparison
      args: {metric: primary_metric, smoothing: ema, window: 5}
      caption: "Code population comparison"
  alert_thresholds:
    invalidity_rate: 0.75
    stagnation_window: 10
```

Ask the researcher:
1. Which metrics should be plotted? (default: primary metric from metrics.yaml)
2. What alert thresholds? (defaults shown above are usually fine)
3. Any custom plot commands beyond the defaults?

Reference: `gigaevo/monitoring/manifest_schema.py` (`WatchdogSection`, `PlotCommand`, `AlertThresholds`)

## Step 5b — Pin dataset checksums (reproducibility anchor)

Before writing 03_plan.md, capture the git commit hash and file checksums of the evaluation dataset. This anchors the pre-registration to the exact data used — any later dataset change is detectable as a protocol deviation.

```bash
EXP=$(echo '$ARGUMENTS' | awk '{print $1}')
TASK=$(echo "$EXP" | cut -d/ -f1)
PROJ="$(git rev-parse --show-toplevel)"

$GIGAEVO_PYTHON -c "
import hashlib, os, json
from pathlib import Path

# Find dataset files for this task
task = '$TASK'
dataset_dirs = list(Path('$PROJ/problems').rglob('*.jsonl')) + \
               list(Path('$PROJ/problems').rglob('*.json')) + \
               list(Path('$PROJ').glob(f'data/{task}*'))

checksums = {}
for f in sorted(set(dataset_dirs)):
    if f.is_file() and f.stat().st_size < 500_000_000:  # skip >500MB
        h = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
        checksums[str(f.relative_to('$PROJ'))] = h

# Record HEAD commit of the data directory
import subprocess
data_commit = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--', 'problems/', 'data/'], text=True).strip()

snapshot = {'git_commit': data_commit, 'file_checksums': checksums}
out = '$PROJ/experiments/$EXP/dataset_snapshot.json'
import json
Path(out).write_text(json.dumps(snapshot, indent=2))
print(f'Dataset snapshot: {len(checksums)} files, commit={data_commit[:8]}')
print(f'Written to: {out}')
"
```

If no dataset files are found (e.g. dataset is fetched dynamically at eval time), record the API endpoint and version instead. The goal is: anyone re-running the experiment can verify they have the same data.

## Step 6 — Write 03_plan.md

Fill 03_plan.md with hypotheses, conditions, and the pre-registration record. This is the scientific document of record — it is never parsed by automation.

Include the dataset snapshot reference: cite `dataset_snapshot.json` and the git commit hash as the reproducibility anchor.

## Step 7 — Set status to preregistered

```bash
EXP=$(echo '$ARGUMENTS' | awk '{print $1}')
gigaevo -e "$EXP" manifest gate preregistered
```

## Step 8 — Create branch, commit, create PR

```bash
EXP=$(echo '$ARGUMENTS' | awk '{print $1}')
BRANCH="exp/$EXP"
rtk git checkout -b "$BRANCH" 2>/dev/null || rtk git checkout "$BRANCH"
rtk git add "experiments/$EXP/"
rtk git commit -m "preregister: $EXP — $(head -1 experiments/$EXP/01_design.md | sed 's/^# //')"
```

Create PR with `gh pr create`. Record PR number in experiment.yaml.

## Step 9 — Completion check

```bash
EXP=$(echo '$ARGUMENTS' | awk '{print $1}')

# Gate: status must be preregistered
gigaevo -e "$EXP" manifest gate preregistered

# Verify stopper choice documented in 01_design.md
DESIGN_FILE="experiments/$EXP/01_design.md"
if [ -f "$DESIGN_FILE" ] && grep -qi "stopper=" "$DESIGN_FILE"; then
  echo "Stopper choice documented in 01_design.md"
else
  echo "WARNING: No stopper= override documented in 01_design.md — default max_generations will be used"
fi

echo "COMPLETE: experiment-design finished successfully"
```

## Gotchas

- **Always read CONTEXT.md first** — it has task-specific infrastructure, known bugs, and prior art that changes the design.
- **N >= 2 per cell** is a hard requirement. Volkov will reject N=1 factorial designs. Budget accordingly.
- **Single IV per comparison** — if you have 2+ independent variables, use a factorial design where each cell comparison varies exactly one IV.
- **Branch naming**: Always `exp/<task>/<name>` to match experiment.yaml.
- **The prereg_commit field** should be set to the commit hash of the preregistration commit (Step 8). Update experiment.yaml after committing.
- **Treatment verification** — Elena describes what observable evidence proves the treatment is working and lists `extra_overrides`. The `treatment-verifier` agent (run during `/experiment-implement` Step 11) handles the code-level tracing of silent fallback modes. Elena focuses on the scientific level; the verifier handles the engineering level.
