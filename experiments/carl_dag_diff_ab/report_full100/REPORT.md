# CARL DAG-diff mutation A/B — full100 report

Date: 2026-07-02. Runs: `runs/armA_full100`, `runs/armB_full100` (launched 22:20, both hit
the 100-mutant stopper by ~22:31). Data: `ab_stats.json`, `mutation_tokens.json`,
figures `ab_overview.png`, `ab_nsteps.png`.

## Setup

Both arms evolve CARL reasoning-chain genomes (wire JSON) on `problems/chains/summarizer`
(ROUGE-L fitness over the carl_pack eval set), same 4 seeds, same engine config,
mutation model gemini-3.5-flash (OpenRouter, reasoning effort high), chain executor
Qwen3-235B-Instruct (LiteLLM proxy), storage=disk, memory=none, 100 mutants each.

- **Arm A — full wire-JSON rewrite**: stock `LLMMutationOperator`; the LLM emits the entire
  child chain as free-form JSON text; chain-faithful problem prompt.
- **Arm B — structured slot diff**: `StructuredDiffMutationOperator` + `AllowedDagChanges`;
  the LLM emits a schema-constrained positional-slot diff (keep/new slots, dependency enum),
  validated and applied pre-persist.

## Headline: validity funnel

| | arm A (rewrite) | arm B (diff) |
|---|---|---|
| mutation LLM calls | 107 | 108 |
| generation failures (pre-persist) | 2 — `no_code_extracted` | 3 — `diff_schema_error` |
| children persisted | 100 | 101 |
| **invalid after evaluation** | **5 — all `json_parse_error`** | **0** |
| valid children | 95 | 101 |
| valid yield per persisted mutant | 95.0% | **100%** |
| valid yield per LLM call | 88.8% | 93.5% |

The arms fail at different stages, with very different costs:

- **Arm A defects pass mutation silently** (the operator only extracts a string) and die
  during evaluation: 5 mutants (5% of the budget) were persisted with malformed JSON
  (truncated / bad quoting), each burning a mutant slot plus a full evaluation pipeline
  before being marked invalid.
- **Arm B defects are caught before persisting**: 3 diffs rejected at `DiffSchema.validate`
  for the cost of one mutation call each; no mutant budget, no evaluation spent. Nothing
  structurally invalid can reach the population — 0 invalid stored, by construction.

## Fitness — parity, no signal either way

| | arm A | arm B |
|---|---|---|
| seed best (re-evaluated) | 0.4807 | 0.4887 |
| child mean | 0.392 | 0.389 |
| child best | 0.551 | 0.475 |

Child means are indistinguishable. Arm A's single 0.551 child is a one-off top sample in a
single replicate per arm; the same 4 seeds score 0.008 apart across the two runs purely from
executor sampling noise, and we have no same-config variance floor for this problem — so no
fitness conclusion beyond parity is warranted. Trajectories in `ab_overview.png`.

## Structural exploration

Chain-length distribution of valid children (`ab_nsteps.png`):

- arm A: 1–3 steps only (51× 2-step).
- arm B: 1–8 steps, including 2× 4-step and 4× 8-step chains — the slot vocabulary makes
  larger DAGs cheap to express, and the schema guarantees they arrive well-formed.

## Cost (mutation side, gemini-3.5-flash)

| | arm A | arm B |
|---|---|---|
| calls | 107 | 108 |
| tokens in | 833,947 | 673,546 (−19%) |
| tokens out | 804,569 | **468,420 (−42%)** |

Diffs are much cheaper to emit than full rewrites; the executor side is comparable
(84K vs 108K completion tokens across stored programs — arm B's longer chains cost more
to run, which is exploration, not overhead).

## Residual failure class and its fix

All 3 arm-B rejections are the **same degenerate violation**: slot 1 emitted
`dependencies: ["slot_1"]` (self-reference), caught by the pydantic validator — the one
DAG rule (dependencies may only reference earlier slots) that the shipped flat-array
encoding cannot express in the grammar.

Probed fix (2026-07-02, see `experiments/carl_dag_diff_dependency_rule_fix.md`): a
**fixed-key object encoding** — `slot_1..slot_8` as separate properties, each with a
position-narrowed dependency enum and slot_1 with no dependencies field at all — makes
self- and forward-references *unrepresentable*. Gemini rejects the per-parent-branched
variant (grammar-complexity cliff between 7 and 8 slots) but accepts a **single-model**
variant (global keep-id enum, base_parent as plain enum; 13.4KB, ~2× headroom): 4/4 e2e
probe calls valid, including a trap prompt reproducing the observed failure. Proposed as
arm C / next-run encoding.

## Verdict

The experiment's hypothesis — structured diff mutation reduces validation failures — is
**supported end-to-end**: invalid persisted programs 5 → 0, valid-per-mutant 95% → 100%,
at 42% lower mutation token cost and equal fitness, with a wider structural search to boot.
The remaining 2.8%-of-calls validator rejections are a single degenerate pattern with a
probe-validated grammar-level fix.

## Issues encountered

See `04_issues_log.md` (config merge bugs, prompt fairness, engine `int('A')` base-parent
crash — all fixed pre-launch). All code UNCOMMITTED pending approval.
