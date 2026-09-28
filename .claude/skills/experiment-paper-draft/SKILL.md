---
name: experiment-paper-draft
description: Generate a paper draft from completed experiment results. Builds paper_data.json from experiment results, PATTERNS.md, and literature, then invokes paper-section-writer for each section. Produces a NeurIPS-ready Markdown/LaTeX draft. Triggers on "draft paper", "write paper", "generate paper", or called by experiment-closeout.
argument-hint: <task> [<experiment-names...>]
model: opus
---

# Experiment Paper Draft: $ARGUMENTS

Synthesize completed experiments into a research paper draft.

## Step 0 — Parse arguments

`$ARGUMENTS` = `<task> [exp1 exp2 ...]`
- If experiment names are given: use those specific experiments
- If only task given: use all POSITIVE/SUGGESTIVE experiments on that task

## Step 1 — Gather experiment data

For each experiment to include:
1. Read `experiments/<task>/<name>/01_design.md` — hypothesis, treatment, conditions
2. Read `experiments/<task>/<name>/05_results.md` — verdict, effect sizes, CIs
3. Read `experiments/<task>/<name>/literature_brief.md` — related work citations
4. List available plots in `experiments/<task>/<name>/plots/`

Read task-level:
- `experiments/<task>/CONTEXT.md` — baselines
- `experiments/PATTERNS.md` — confirmed patterns (key findings)
- `experiments/INDEX.md` — full experiment ledger for null results context

## Step 2 — Build paper_data.json

Construct the structured JSON document:

```python
paper_data = {
  "metadata": {
    "title": "<generated from task + key findings>",
    "venue": "NeurIPS 2026",
    "task": "<task>",
    "primary_metric": "<from CONTEXT.md>",
    "hypothesis": "<overarching hypothesis linking all included experiments>"
  },
  "experiments": [
    {
      "name": "<task>/<name>",
      "verdict": "<from 05_results.md>",
      "primary_effect": "<e.g. +8.5pp>",
      "ci_95": "<e.g. [+5.2, +11.8]pp>",
      "n_runs": <N>,
      "key_finding": "<one sentence>",
      "null_results": ["<experiment names with NULL verdicts>"]
    }
  ],
  "patterns": ["<confirmed patterns from PATTERNS.md>"],
  "baselines": [{"system": "...", "metric": "...", "value": "..."}],
  "figures": [
    {"id": "fig_fitness_curves", "path": "<relative path>", "caption": "<from 05_results.md>"}
  ],
  "sections": {
    "abstract":      {"outline": "<3-sentence outline>"},
    "introduction":  {"outline": "<4-point outline>"},
    "method":        {"outline": "<3-part outline>"},
    "experiments":   {"outline": "<structure: setup, results, ablation>"},
    "related_work":  {"outline": "<3 themes>"},
    "conclusion":    {"outline": "<findings + limitations + future work>"}
  }
}
```

Save to `experiments/<task>/paper_data.json`.

## Step 3 — Generate sections

Invoke `paper-section-writer` agent for each section in order:

1. **method** — write first (grounds the rest)
2. **experiments** — write second (main contribution)
3. **related_work** — write third (positions the work)
4. **introduction** — write fourth (now can reference results)
5. **conclusion** — write fifth
6. **abstract** — write last (summarizes everything)

For each section: pass `paper_data.json` + section name → agent returns prose.

Save each section to `experiments/<task>/paper_sections/<section>.md`.

## Step 4 — Assemble draft

Concatenate sections in NeurIPS order into `experiments/<task>/paper_draft.md`:

```markdown
# <title>

## Abstract
[abstract prose]

## 1. Introduction
[introduction prose]

## 2. Method
[method prose]

## 3. Experiments
[experiments prose]

## 4. Related Work
[related_work prose]

## 5. Conclusion
[conclusion prose]
```

## Step 5 — Self-review via reviewer-2-adversary

Invoke `reviewer-2-adversary` agent on `paper_draft.md` with role: "You are Reviewer 2. Find all factual errors, missing comparisons, and unsubstantiated claims. Be harsh."

Write review to `experiments/<task>/paper_review.md`.

Revise the draft to address Critical and Major concerns. Do not revise for stylistic preferences.

## Step 6 — Report to researcher

```
Paper draft complete.

Files:
  experiments/<task>/paper_data.json   — structured data
  experiments/<task>/paper_draft.md    — assembled draft (~3500 words)
  experiments/<task>/paper_review.md   — Reviewer 2 critique + responses

Status:
  Sections: 6/6
  Self-review concerns addressed: N/M

Next steps:
  1. Review paper_draft.md and paper_review.md
  2. Add figures (paths in paper_data.json)
  3. Convert to LaTeX: pandoc paper_draft.md -o paper.tex
  4. Submit to NeurIPS 2026 (deadline: <date>)
```

## Gotchas

- **Null results must appear** — papers with only positive results are not credible. Include null results in the experiments section.
- **Do not exaggerate** — use exact effect sizes from 05_results.md. Never round up.
- **Cite only what you have** — do not invent citations. Use only papers from literature_brief.md files.
- **paper_data.json is the source of truth** — if a fact is not in paper_data.json, it should not appear in the paper.
