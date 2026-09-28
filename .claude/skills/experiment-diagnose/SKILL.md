---
name: experiment-diagnose
description: Health-check a running GigaEvo experiment. Runs at every checkpoint — not just on visible failures. Catches subtle issues: wrong prompts silently loaded, asymmetric server behavior, config drift, stall patterns. Use proactively. Triggers on "diagnose experiment", "debug experiment", "check experiment health", "why is the run stuck", "something looks wrong with experiment X". Also dispatched automatically by /experiment-checkpoint Step 4.
argument-hint: <task/name>
context: fork
agent: Explore
allowed-tools: "Read Grep Glob Bash(redis-cli *) Bash(PYTHONPATH=*) Bash(source *) Bash(cat *) Bash(tail *) Bash(head *)"
model: haiku
---

# Experiment Diagnose

Health-check a running GigaEvo experiment. This skill runs every checkpoint — not just when something is visibly broken. Subtle issues (wrong prompts silently loaded, asymmetric server behavior, early stall patterns, config drift) are the most dangerous because they corrupt results without raising alarms.

When issues are found: fix infrastructure problems, escalate hypothesis-relevant ones, and never confuse "the treatment arm is losing" with "something is broken." Every action must preserve experiment validity and respect compute budget.

## When to use

- **Every checkpoint** — called automatically by `/experiment-checkpoint` as Step 4
- A run's iteration count is stuck
- Invalidity rate is unusually high
- Fitness is not improving
- A process crashed or appears hung
- You suspect a config mismatch
- Proactive health check when everything *seems* fine

## Possible outcomes

This skill can conclude:

1. **HEALTHY** — all checks pass, no action needed. Say so clearly and return.
2. **MINOR issues** — note them in the report, continue the checkpoint.
3. **MAJOR issues** — note them, flag for the user, continue with caution.
4. **CRITICAL issues** — stop, fix infrastructure or escalate to user before continuing.

## Inputs

The user provides one of:
1. **A run label + experiment path** (e.g., "diagnose F1 from hover/feedback_softfit")
2. **A Redis DB + prefix** (e.g., "diagnose db=9 prefix=chains/hover/static")
3. **Just "diagnose the runs"** — you figure out the details from context

## Step 0 — Understand the experiment hypothesis

Before diagnosing anything, read the experiment design so you know what's being tested.

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
cat "$PROJ/experiments/$EXP/experiment.yaml"   # hypothesis, treatment, controls
cat "$PROJ/experiments/$EXP/01_design.md"       # full design rationale
```

Extract and hold in mind:
- **Hypothesis**: What causal claim is being tested?
- **Treatment variable**: What differs between runs?
- **Control invariants**: What must stay the same across runs?
- **Success metric**: What metric decides the outcome?

This context is CRITICAL for every decision below. A "fix" that changes the treatment variable invalidates the experiment. A "fix" that changes a control invariant introduces confounds.

## Step 1 — Gather run parameters

If the experiment has `experiment.yaml`, read it:
```bash
gigaevo -e "EXPERIMENT_NAME" manifest get runs
gigaevo -e "EXPERIMENT_NAME" manifest get max_generations
```

If no experiment.yaml (old experiment), gather from:
- `launch.sh` or the launch commit message for DB numbers, prefixes, PIDs
- `CONTEXT.md` for server IPs
- The run log filenames for labels

## Step 2 — Run the automated diagnostic script

For each run:
```bash
PROJ="$(git rev-parse --show-toplevel)"
PYTHONPATH="$PROJ" $GIGAEVO_PYTHON \
  "$PROJ/.claude/skills/experiment-diagnose/scripts/diagnose.py" \
  --db DB_NUMBER \
  --prefix PREFIX \
  --label LABEL \
  --pid PID \
  --log "experiments/TASK/EXPERIMENT/run_LABEL.log" \
  --chain-url "http://CHAIN_IP:PORT/v1" \
  --mutation-url "http://MUTATION_IP:PORT/v1" \
  --max-gen MAX_GENERATIONS \
  --pipeline PIPELINE_NAME \
  --problem-dir "problems/PREFIX" \
  --cfg-file "experiments/TASK/EXPERIMENT/cfg_run_LABEL.txt" \
  --extra-overrides OVERRIDE1 OVERRIDE2 ... \
  --experiment TASK/EXPERIMENT
```

Pass `--extra-overrides` with the full list of extra_overrides from experiment.yaml. Check 12 (override verification) verifies each override's leaf key=value appears in the resolved Hydra cfg dump.

Pass `--experiment` with the experiment path. Check 13 (declarative treatment verification) reads `treatment_checks` from experiment.yaml and executes them. These checks are experiment-specific and defined at design time — no hardcoded per-experiment logic in the script.

The script runs 13 check groups and exits with: 0=healthy, 1=major issues, 2=critical.

## Step 3 — Read the Hydra config (critical for task-mismatch bugs)

This is the most important diagnostic step for non-obvious failures. The `--cfg job` output is the **ground truth** for what Hydra actually composed.

If `cfg_run_LABEL.txt` exists, read it and verify:

1. **`pipeline_builder._target_`** — Does the PipelineBuilder match the task?
   - `ASIPipelineBuilder` = hotpotqa only
   - `HoVerFeedbackPipelineBuilder` = hover only
   - `DefaultPipelineBuilder` = any task (standard pipeline)

2. **`prompts_dir`** — Is it null (defaults), or pointing to the right task's prompts?
   - `prompts/hotpotqa` should NOT be used with hover runs
   - `null` is safe (uses package defaults)

3. **`problem.dir`** — Does it resolve to an existing path with validate.py?

4. **`llm_base_url` / `mutation_url`** — Matches the intended server?

5. **`model_name`** — Matches what's actually loaded on the server?

6. **`stage_timeout` / `dag_timeout`** — Reasonable for the problem?

If no cfg file exists, generate one:
```bash
$GIGAEVO_PYTHON run.py \
  problem.name=PREFIX pipeline=PIPELINE \
  [other overrides from launch.sh] \
  --cfg job > experiments/TASK/EXPERIMENT/cfg_run_LABEL.txt 2>&1
```

## Step 4 — Check task-specific failure modes

Based on the task, check these additional items:

### HoVer chains (chains/hover/*)
- **Pipeline must be `hover_feedback`** (for `chains/hover/static`) or **`standard`** (for `chains/hover/static_soft`)
- `validate.py` in `chains/hover/static` returns `(metrics, failures)` — needs feedback pipeline
- `validate.py` in `chains/hover/static_soft` returns dict — needs standard pipeline
- `formatter.py` must exist in problem dir for feedback pipelines
- `HOVER_CHAIN_URL` env var needed if chain uses external retrieval server

### HotpotQA chains (chains/hotpotqa/*)
- **Pipeline must be `hotpotqa_asi`** (never `standard` — repr-contamination bug PR #67)
- Prompts should be `prompts=hotpotqa` or `prompts=default` (not hover prompts)
- ColBERT variants need ColBERT server running and accessible

### Non-chain problems (optimization tasks)
- Pipeline should be `standard` or `auto`
- No formatter needed
- No feedback loop

## Step 5 — Trace root cause to code (use superpowers:systematic-debugging)

Use `superpowers:systematic-debugging` to trace every CRITICAL or MAJOR finding to its root cause. Do NOT stop at the symptom. For every CRITICAL or MAJOR finding:

1. **Read the actual traceback** — last 100 lines of the log file, not just the pattern match
2. **Follow the stack trace into source code** — read the file and line number where the error originated
3. **Understand WHY the code fails**, not just WHAT failed
4. **Identify the minimal fix** — the smallest change that addresses the root cause

Example of WRONG diagnosis:
> "LLM call failed: ConnectionError. Fix: check server status."

Example of RIGHT diagnosis:
> "LLM call failed because `mutation_url` resolved to `http://10.0.0.5:8001/v1` but the mutation server moved to port 8002 after restart. The URL comes from `experiments/hover/prompt_coevolution/experiment.yaml` line 34. Fix: update the port in experiment.yaml and relaunch affected runs."

If the diagnostic script reports all healthy and you find no issues in Steps 3-4, skip this step.

## Step 6 — Classify each issue: infrastructure vs. hypothesis-relevant

For every finding, answer these questions:

### Is this an infrastructure problem or a hypothesis-relevant problem?

**Infrastructure problems** (safe to fix):
- Server down/unreachable, wrong port, network issues
- Redis connection failures, wrong DB number
- Process OOM, disk full, NFS hang
- Typos in config paths
- Missing files that should exist

**Hypothesis-relevant problems** (DANGEROUS to fix naively):
- Fitness not improving → may be the actual experimental result (null hypothesis is true)
- High invalidity → may indicate the treatment doesn't work
- Mutation quality poor → may be what the experiment is measuring
- One treatment arm performing worse than control → THAT IS DATA, NOT A BUG

### Decision matrix

| Issue type | Affects all runs equally? | Fix preserves treatment variable? | Action |
|---|---|---|---|
| Infrastructure | Yes | N/A | Fix and continue |
| Infrastructure | No (asymmetric) | N/A | Fix, but flag as potential confound. May need to restart affected runs. |
| Hypothesis-relevant | Yes | N/A | This is likely a design flaw. Escalate to user — may need to abort and redesign. |
| Hypothesis-relevant | No (treatment vs control differ) | N/A | **THIS IS YOUR DATA. DO NOT FIX IT.** Report it as an experimental observation. |

If no findings reached CRITICAL or MAJOR, skip this step — the experiment is healthy.

### NEVER do these:
- Change mutation prompts to "fix" low fitness in one arm — that's the treatment variable
- Add error handling that masks failures differently across treatment/control
- Tune hyperparameters mid-experiment to "help" a struggling run
- Restart only the worst-performing runs (survivorship bias)
- Apply a code fix that changes behavior for treatment but not control (or vice versa)

## Step 7 — Assess resource cost and recovery

Only relevant if a run needs restarting or the experiment needs aborting. Skip if healthy.

```bash
# How many iterations completed vs target?
# Returns a JSON blob; its `programs_processed` field is the progress counter.
redis-cli -n DB hget "PREFIX:run_state" "engine:snapshot"

# How long has the run been going?
stat experiments/TASK/EXPERIMENT/run_LABEL.log

# How long per iteration? (from metric timestamps)
redis-cli -n DB lrange "PREFIX:metrics:history:program_metrics:valid_iter_fitness_mean" -3 -1
```

Then decide:

| Situation | Iterations done | Recommendation |
|---|---|---|
| Infrastructure fix, run still alive | Any | Fix config/infra, run continues automatically |
| Infrastructure fix, run dead | <10% of max_gen | Fix and relaunch — little data lost |
| Infrastructure fix, run dead | 10-50% of max_gen | Fix and relaunch. Archive partial data first. Lost compute = (iters_done / iters_per_hour) hours. |
| Infrastructure fix, run dead | >50% of max_gen | **Ask user**: relaunch (loses 50%+ compute) or accept partial data? |
| Hypothesis-relevant, all runs affected | Any | **Abort experiment**. The design has a flaw. Fix the flaw, pre-register again, start fresh. Do not patch mid-run. |
| Hypothesis-relevant, asymmetric | Any | **Escalate to user** with full context. This may invalidate results. |
| Everything healthy but fitness flat | >30% of max_gen | Report as observation. This may be the answer (null result). Do NOT try to "improve" it. |

**Always state the cost**: "Restarting run F2 will waste ~4 hours of compute (47 iterations at ~5 min/iter)."

## Step 8 — Report

Summarize findings as:

```
## Diagnosis: EXPERIMENT_NAME

**Hypothesis**: [one-line from experiment.yaml]
**Treatment variable**: [what differs between runs]

### Run LABEL (db=X, iter=Y/Z)

**Status**: HEALTHY / DEGRADED / CRITICAL

**Findings**:
- [CRITICAL] ...
- [MAJOR] ...
- [MINOR] ...
(or: No issues found.)

**Root cause**: [traced to specific code/config, not just symptom]
(or: N/A — run is healthy.)

**Classification**: infrastructure / hypothesis-relevant / N/A

**Resource cost**: X iterations completed, ~Y hours of compute.

**Recommended action**: [specific, with exact commands or code changes]
(or: No action needed — continue experiment.)

**Risk to experiment validity**: [none / low / HIGH — explain why]
```

### After reporting:
- If everything is healthy → say so and return. The checkpoint continues normally.
- If the fix is infrastructure-only and preserves all experimental invariants → proceed with the fix
- If the fix could affect the hypothesis → STOP and ask the user
- If the experiment should be aborted → say so clearly with reasoning
- If everything is healthy but the user expected better results → say "the experiment is working correctly; the data is the data"

## Issues log

After diagnosing, auto-capture the diagnosis as an event in the issues log:

```bash
EXP='$ARGUMENTS'
PROJ="$(git rev-parse --show-toplevel)"
LOG="$PROJ/experiments/$EXP/04_issues_log.md"
[ ! -f "$LOG" ] && cp "$PROJ/experiments/_template/04_issues_log.md" "$LOG"

cat >> "$LOG" << ENTRY

### [EVENT $(date -u +%Y-%m-%dT%H:%M:%SZ)] -- Diagnose completed: <VERDICT>

- **When**: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- **What**: Diagnosis completed. Verdict: <HEALTHY|MINOR|MAJOR|CRITICAL>. <one-line summary of findings or "No issues found">
- **Category**: diagnose
- **Impact**: <brief impact or "No issues">
ENTRY
```

Replace `<VERDICT>` and other placeholders with the actual diagnosis outcome from Step 8.

If any CRITICAL or MAJOR issues were found (or any manual fix was applied), ALSO append a detailed ISSUE entry (not just an EVENT) with the full format: When, What, Category, Impact, Root cause, Fix applied, Systemic fix needed. This builds a per-experiment record for post-mortem reflection.

## Reference files

- `references/failure-modes.md` — 8-layer failure catalog with symptoms, log patterns, and fixes
- `scripts/diagnose.py` — Automated 13-check diagnostic script
- `tools/README.md` — Redis key schema and tool reference
- `experiments/<task>/CONTEXT.md` — Task-specific infrastructure and known bugs
