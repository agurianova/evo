---
name: idea-generate
description: Generate ranked experiment proposals after a retrospective or closeout. Updates IDEAS.yaml with new ideas derived from experiment results, PATTERNS.md, and literature. Invoked automatically by experiment-retrospective Step 5. Not user-invocable directly (use /experiment-retrospective instead).
user-invocable: false
argument-hint: <task> [<completed-experiment-name>]
model: opus
---

# Idea Generate: $ARGUMENTS

Generate new experiment proposals and update IDEAS.yaml. Called after retrospective analysis.

## Step 1 — Read all evidence

Read in order:
1. `experiments/PATTERNS.md` — confirmed/refuted/suggestive patterns
2. `experiments/INDEX.md` — complete experiment history with verdicts
3. `experiments/IDEAS.yaml` — existing ideas (avoid duplicates)
4. `experiments/<task>/CONTEXT.md` — task knowledge and baselines
5. `experiments/<task>/RESEARCH_STRATEGY.md` — retrospective output (if exists)

## Step 2 — Gap analysis

Identify the 3 highest-value information gaps:

A gap is high-value if:
- A confirmed pattern has an obvious extension not yet tested
- A refuted hypothesis suggests an alternative mechanism worth testing
- A suggestive signal (weak evidence) has a clean follow-up design
- Prior literature (from literature briefs) suggests a mechanism not yet tried
- The PATTERNS.md "Open Questions" section names an untested variable

Score each gap by expected information gain × feasibility:
- **Information gain**: How much would a positive/null result change our understanding?
- **Feasibility**: Is this implementable as a config-only change, or does it require new Python?

## Step 3 — Generate ideas

For each top gap, generate one idea in the IDEAS.yaml schema:

```yaml
- id: <task>_<NNN>   # e.g. hover_005 — use next available number
  title: "Short descriptive title (max 80 chars)"
  task: <task>        # hover | hotpotqa | any
  status: queued
  rank: <0.0-1.0>     # your estimate of priority
  hypothesis: >
    One paragraph. What mechanism? Why should it work? What evidence supports this?
  mechanism: "One sentence: which code component + what change"
  expected_effect: "+X-Y pp on primary metric"
  estimated_cost: "N runs × M gen"
  source: retrospective  # or: literature | human
  created: "<today's date>"
  builds_on: []          # list idea IDs or experiment names this extends
  contradicts: []        # list idea IDs or experiment names this challenges
  alternative_to: []     # list idea IDs that test the same gap differently
  notes: >
    Any caveats, Volkov-relevant concerns, or design nuances.
  literature_refs:
    - "Paper (year) — one-line relevance"
```

**Lineage rules** (ADAS pattern):
- If a new idea directly extends a positive result → add the experiment name to `builds_on`
- If a new idea challenges a confirmed pattern → add pattern or experiment to `contradicts`
- If two ideas test the same hypothesis differently → link them via `alternative_to`

This lineage enables research-scheduler to reason about the idea tree, not just a flat list.

## Step 4 — Rank ideas in IDEAS.yaml

After appending new ideas, re-rank ALL queued ideas in IDEAS.yaml using:

**Rank formula** (0-1 scale):
```
rank = 0.4 * expected_effect_score
     + 0.3 * novelty_score          # 1.0 = never tried; 0.0 = tried and null
     + 0.2 * feasibility_score      # 1.0 = config-only; 0.5 = new Python; 0.0 = RED archaeologist
     + 0.1 * lineage_bonus          # 0.2 bonus if builds_on a positive result
```

Normalize so max rank ≤ 1.0. Break ties by expected_effect_score.

## Step 5 — Write to IDEAS.yaml

Append new ideas to `experiments/IDEAS.yaml`. Update `rank` values for existing queued ideas.

Do NOT change status of existing ideas (researcher controls status).

## Step 6 — Report to researcher

Output a summary:
```
IDEAS.yaml updated — N new ideas added, M ideas re-ranked.

Top 3 queued ideas:
1. [rank 0.91] hover_001 — Gradient-signal fitness: LLM critique replaces binary signal
2. [rank 0.88] framework_001 — Agent design evolution: evolve mutation prompts
3. [rank 0.83] hover_002 — Parsed adversarial critique: K=3 with structured parsing

Use /research-scheduler to autonomously pick the top idea and start design.
Or pick manually: /run-experiment hover/<name> <research-question>
```
