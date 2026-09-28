---
name: experiment-retrospective
description: Cross-experiment synthesis. After closeout, analyze patterns across ALL completed experiments on a task. Produces updated research program strategy and ranked next-experiment proposals. Triggers on "retrospective", "what should we try next", "analyze all experiments".
argument-hint: <task>
model: opus
---

# Experiment Retrospective: $ARGUMENTS

Synthesize results across all completed experiments on this task and propose next steps.

## Step 1 — Gather evidence

Read the following shared knowledge stores (in this order):

1. `experiments/INDEX.md` — experiment journal with verdicts, effect sizes, treatment types
2. `experiments/PATTERNS.md` — accumulated cross-cutting patterns (your primary output target)
3. `experiments/$ARGUMENTS/CONTEXT.md` — task knowledge and baselines
4. All `experiments/$ARGUMENTS/*/05_results.md` files for completed experiments

## Step 2 — Invoke Retrospective Analyst

Use the `retrospective-analyst` agent with all gathered evidence. The agent produces:

1. **Hypothesis ranking** — each tested hypothesis ranked by evidence strength (CONFIRMED > SUGGESTIVE > NULL > REFUTED)
2. **Cross-experiment patterns** — what intervention types consistently work/fail
3. **Information gap analysis** — what's unknown, ranked by expected information gain
4. **Next experiment proposals** — 3-5 ranked proposals with design sketches
5. **Research program health** — trajectory assessment and recommendation

## Step 3 — Save output

Write the full retrospective to `experiments/$ARGUMENTS/RESEARCH_STRATEGY.md`.

## Step 4 — Update PATTERNS.md

Update `experiments/PATTERNS.md` with new or revised entries:
- **Confirmed Patterns**: strengthen or add based on new evidence
- **Refuted Hypotheses**: add if new evidence refutes a hypothesis
- **Suggestive Signals**: update based on accumulated results
- **Open Questions**: revise based on what this retrospective revealed

Do NOT update agent-specific memories — all cross-cutting knowledge goes into PATTERNS.md.

## Step 5 — Auto-generate next ideas (ADAS pattern)

Invoke `/idea-generate $ARGUMENTS` to:
1. Generate 3-5 ranked experiment proposals based on this retrospective
2. Append them to `experiments/IDEAS.yaml` with lineage links to the experiments analyzed
3. Re-rank all queued ideas in IDEAS.yaml

This runs automatically — no researcher input needed. The ideas queue is always populated after a retrospective.

## Step 6 — Present to researcher

Show the hypothesis ranking, top 3 next-experiment proposals from IDEAS.yaml, and a 1-line summary of what was added to the queue.

```
Retrospective complete. 3 new ideas added to IDEAS.yaml.

Top 3 queued ideas:
1. [rank X.XX] <task>_NNN — <title>
2. [rank X.XX] <task>_NNN — <title>
3. [rank X.XX] <task>_NNN — <title>

Run /research-scheduler --task $TASK to start the next experiment autonomously.
Or pick manually: /run-experiment <task>/<name> <research-question>
```
