---
name: protocol-quick-ref
description: Quick reference for the GigaEvo experimental protocol — phases, gates, template fields, amendment rules. Knowledge skill for agent preloading, not user-invocable.
user-invocable: false
---

# GigaEvo Experimental Protocol — Quick Reference

## 5 Phases (must complete in order, no exceptions)

| Phase | File | Actor | Gate |
|---|---|---|---|
| 0 | `00_github.md` | Researcher | GitHub Issue created |
| 1 | `01_design.md` | Elena (ml-research-methodologist) | Researcher approves design |
| 2 | `02_review.md` | Volkov (reviewer-2-adversary) | Verdict = APPROVED |
| 3 | `03_plan.md` | Researcher | Committed to git; branch + PR created |
| 4 | `04_launch.md` | Researcher + Claude Code | Preflight green, runs launched |
| 5 | `05_results.md` | Elena + Researcher | Written, merged, INDEX.md updated |

## 3 Human Approval Gates

1. **Design gate** (Phase 1→2): Researcher reads `01_design.md`, approves handoff to Volkov
2. **Launch gate** (Phase 3→4): Researcher approves pre-registration, preflight passes
3. **Results gate** (Phase 5→merge): Researcher reviews `05_results.md`, merges PR

## 01_design.md Required Fields

- Research question (one sentence)
- Success criterion (effect magnitude, e.g., "+3pp" or "2x throughput")
- Failure criterion (what result abandons this direction)
- Independent variable (treatment vs control)
- Controlled variables (what's held constant)
- Dependent variable (metric, how measured)
- Expected N runs (typically 2-4)
- Stopping rule (when to halt early)
- Baseline reference (from CONTEXT.md or prior experiments)

## 02_review.md Verdict Options

- **APPROVED** — proceed to pre-registration
- **NEEDS REVISION** — Elena revises, loop until APPROVED (no cap on rounds)

## 02_review.md Key Review Criteria

- Confound detection (hidden independent variables)
- Treatment integrity (is treatment actually different from control?)
- Design quality (fair comparison, controlled variables truly controlled)
- Information gain (given prior results, is this the highest-value experiment?)

## 03_plan.md (Pre-registration)

Locked before any code changes. Fields:
- Experiment config (pipeline, problem.name, Redis DBs, servers)
- Run matrix (N runs × conditions)
- Max generations
- Stopping rule (copied from design)

## Amendment Protocol

When pre-registered plan changes after registration:
1. Record in `03_plan.md` under **Amendments** section
2. Include: what changed, why, commit hash, impact:
   - **No confound** — uniform across all runs
   - **Confound introduced** — document and assess
   - **Run invalidated** — exclude from analysis

## 05_results.md Required Fields

- Effect magnitude per run and grand mean
- Cross-run consistency
- Verdict: POSITIVE / NEGATIVE / NULL
- Deviations from pre-registration (mandatory even if none)
- What we learned, what to try next
- INDEX.md entry

## experiment.yaml Status Machine

`new` → `preregistered` → `implemented` → `running` → `complete`

## Directory Layout

```
experiments/<task>/<name>/
  01_design.md, 02_review.md, 03_plan.md
  04_issues_log.md (runtime issues)
  05_results.md
  experiment.yaml (manifest)
  launch.sh, run_watchdog.py
  test_evals/, archives/
```

## Key Rules

- Merge with `--merge` (not `--squash`) to preserve audit trail
- Archive all runs before flushing Redis (`archive_run.sh --upload`)
- Every experiment gets `04_issues_log.md` — log ALL errors
- `experiments/INDEX.md` is the cross-experiment ledger — update at closeout
