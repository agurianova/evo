---
name: experiment-literature-search
description: Search for related work before experiment design. Finds competing approaches, baselines, and methodology precedents. Not user-invocable — called by experiment-design Step 2a.
user-invocable: false
context: fork
agent: general-purpose
allowed-tools: "WebSearch WebFetch Read Grep Glob"
model: opus
---

# Literature Search for Experiment Design

Search for related work, competing approaches, and baselines before Elena designs an experiment.

## Input

Receive from experiment-design:
- Research question
- Task name (e.g., "hover", "hotpotqa")
- Experiment name

## Step 1 — Search internal history

Read `experiments/INDEX.md` for all experiments on this task.
Read relevant `experiments/<task>/*/05_results.md` files.
Read `experiments/<task>/CONTEXT.md` for task knowledge and baselines.

Summarize: what's been tried, what worked, what didn't.

## Step 2 — Search external literature

Use web search to find:
- Papers testing the same mechanism or similar approaches
- State-of-the-art baselines on the task
- Methodology precedents (has this general approach been tried? What happened?)

Focus on papers from 2023-2026. Key systems to check:
- AlphaEvolve, FunSearch, OPRO, EvoPrompting (evolutionary)
- AI Scientist v2, AIDE, Agent Laboratory (autonomous research)
- TextGrad, DSPy/MIPROv2 (prompt optimization)
- Task-specific papers (e.g., multi-hop QA for HotpotQA, fact verification for HoVer)

## Step 2a — Update CONTEXT.md benchmarks (if new baselines found)

If the external literature search found baselines NOT already in `experiments/<task>/CONTEXT.md` → Benchmarks table, append them. This keeps CONTEXT.md as the single source of truth for all baselines (internal and external).

Only add baselines that are:
- On the same task and metric
- From a published or well-known system
- Using a comparable evaluation protocol

Add a `Source` column note (paper name + year) so it's traceable.

## Step 3 — Produce structured brief

Write to `experiments/<task>/<name>/literature_brief.md`:

```markdown
# Literature Brief: [Research Question]

## Related External Work
| Paper/System | Year | Mechanism | Result | Relevance |
|---|---|---|---|---|

## Baselines on This Task
| System | Metric | Value | Notes |
|---|---|---|---|

## Prior GigaEvo Experiments
| Experiment | Result | Key Learning | Relevance to Proposal |
|---|---|---|---|

## Novelty Assessment
[Is this novel? Similar to prior work? Already tried?]

## Recommendations for Designer
- Key design considerations from literature
- Suggested baselines to compare against
- Potential confounds found in prior work
- Expected effect size based on similar experiments
```
