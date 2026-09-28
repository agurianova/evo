# Design review — standard pipeline intra-memory + suggestion machinery (2026-07-02)

Scope: `pipeline=standard` chain — `DescendantProgramIds` → `IntraMemoryStage`
(diff generation, LLM clustering, Python aggregation, plateau signal) →
`MutationSuggestionStage` (trail + stats + prescription) → mutator PROGRAM
INSIGHTS. Design-reasonability review, not a does-it-run audit (it runs; live
llm_io shows cards rendered, cited, applied).

Files: `gigaevo/programs/stages/lineage_memory.py`,
`gigaevo/programs/stages/mutation_suggestions.py`,
`gigaevo/llm/agents/mutation_suggestions.py`, `gigaevo/llm/agents/insights.py`,
`gigaevo/entrypoint/lineage_memory_pipeline.py`,
`gigaevo/prompts/mutation_suggestions/*.txt`, `gigaevo/prompts/mutation/system.txt`,
`gigaevo/programs/stages/ancestry_selector.py`.

## Verdict

The architecture is genuinely well factored — the descriptive/prescriptive
split, the LLM-membership/Python-numerics division, the cache design, and the
end-to-end provenance chain (anchor → mechanism_source → card_id →
insights_used) are better than most LLM-pipeline code. But the analysis layer
has two validity-breaking design flaws (unoriented deltas; fitness-biased child
sampling sold to the LLM as complete history), one unacknowledged confound
(crossover diff attribution under the num_parents=2 default), and an
unmeasured ~3× strong-LLM cost multiplier. The complexity is defensible only
if the standard-vs-legacy ablation ever shows it pays.

## What is well designed (keep)

- **LLM does membership + labels, Python does every number** (`_merge_intra_card`,
  lineage_memory.py:588). The LLM cannot fabricate `mean_delta`/`verdict`;
  out-of-range indices are dropped, duplicates first-claim-wins, and missing
  indices land in an `unassigned` catch-all so counts always reconcile
  (lineage_memory.py:634). This is the right trust boundary.
- **Diff-vs-full-code triage** (`_select_code_form`, lineage_memory.py:172):
  full code for invalid children (error line refs stay resolvable), for empty
  diffs, and when the diff isn't smaller than the file. All three fallbacks are
  reasoned, not defensive noise.
- **Oriented ancestral trail** (`collect_ancestral_trail`,
  lineage_memory.py:54): multi-parent BFS with dedup, oriented `step_delta`
  with an explicit comment on why raw subtraction is wrong for minimize
  metrics, bounded depth/size, no hardcoded "breakthrough" threshold —
  direction judgment delegated to the LLM against the metric's scale.
- **Cache design**: `InputHashCache` on children-ids for the expensive card;
  suggester overrides `compute_hash` with a *quantized* stats signature using
  `MetricSpec.significant_change` (mutation_suggestions.py:103) so noise-level
  stats churn doesn't re-fire the LLM but real momentum shifts do. Thoughtful.
- **Structured insight schema v2** (insights.py:19): `anchor_quote` +
  `evidence_source` + `mechanism_source` + `card_id` + `substitute` — the
  schema itself prevents ungrounded suggestions, and the mutator-side contract
  closes the loop (`prompts/mutation/system.txt:14`: act on insight 1 or
  justify; `card_ids_used` credits cards). Producer and consumer prompts
  agree — rare.
- **Paid-call gating**: both strong-LLM stages gate on validator success and
  (optionally) archive acceptance (lineage_memory_pipeline.py:247-292) —
  tokens are never spent on programs that can't become parents.
- **Soft-fail everywhere**: LLM failure → empty card / empty insights, prompt
  slots collapse cleanly, run survives. Correct posture for an advisory
  subsystem.
- **Card-obligation remediation already landed**: the suggester's MUST-transpose
  rule is now evidence-gated to `(confident)` positive-median cards
  (`prompts/mutation_suggestions/system.txt:30`) — addresses the documented
  displacement finding.

## Findings (ranked)

### F1 — Child deltas are unoriented; every sibling component orients. HIGH

`_collect_evaluated` emits raw `delta = child_fitness - parent_fitness`
(lineage_memory.py:890) and `_bucket_delta` maps positive→"improving"
(lineage_memory.py:560). On a lower-is-better primary metric every label
inverts: improvements are counted `catastrophic`, regressions `improving`,
cluster verdicts flip, and `_derive_intra_signal` then reports `exhausted`
for healthy lineages (forcing structural pivots via the system-prompt rule)
and `healthy` for exhausted ones. The analyst prompt even asserts the wrong
semantics to the LLM ("+ better, − worse", lineage_memory.py:225), and the
`best_delta` Field doc claims "sign-oriented" while the code takes a raw
`max()` (lineage_memory.py:335 vs :706).

The inconsistency is the damning part: `collect_ancestral_trail` orients with
a comment explaining exactly this failure mode (lineage_memory.py:83-88,110),
and the extra-memory efficacy line is documented direction-neutral
(`prompts/mutation_suggestions/system.txt:14`). The intra card is the one
component that skipped it. Harmless on heilbron (maximize); wrong on any
minimize task (e.g. spherical-codes max-cos) in a framework whose stated
identity is domain-agnostic.

Fix shape: orient once in `_collect_evaluated` with the same
`sign = ±1` the trail uses, present `delta` as oriented in the payload, and
update the prompt table row to say so.

### F2 — Analyst sees a fitness-ranked top-24 sample but is told it sees everything. HIGH

The builder wires `DescendantProgramIds` with
`AncestrySelector(strategy="best_fitness", max_selected=24)`
(lineage_memory_pipeline.py:150). The analyst system prompt says it reads
"EVERY child the algorithm has produced from it so far"
(lineage_memory.py:209), and the rendered card states "has been mutated
N time(s)" from the windowed count (lineage_memory.py:486).

Consequences once a parent exceeds 24 children:
- **Survivorship bias by construction**: invalid children carry the fitness
  sentinel (-1000) and worst children rank last, so the failure inventory —
  `failure_signature`, `n_failed`, `catastrophic` — is erased exactly on the
  most-explored parents, where "what failed" is the card's main value.
- **Signal drifts optimistic with exploration**: `cond_b`
  (`improving == 0 and catastrophic + n_failed >= 2`,
  lineage_memory.py:769) can un-fire as bad children fall out of the window,
  flipping `exhausted`→`healthy` precisely when the lineage is most exhausted.
- **Chronology is lost**: children arrive rank-ordered, so "recent attempts"
  is unrecoverable; the suggester gets ancestor momentum but zero child
  recency.

Either the sampling should be recency-based (`children[-24:]` matches both
the prompt's claim and the stage docstring's DONE→QUEUED narrative), or
stratified (keep failures), or the prompt/render must stop claiming
completeness. Note `IntraMemoryStage.max_children=32` vs the builder's 24 —
the stage-side `child_ids[-32:]` re-slice (lineage_memory.py:923) suggests
the stage *expects* chronological input that the selector doesn't deliver.

### F3 — Crossover makes "what the code changed" mis-attributed; unacknowledged. MEDIUM-HIGH

With the framework default `num_parents=2`, every child appears in BOTH
parents' children lists, and its diff is computed against each parent alone
(lineage_memory.py:894). Against parent A, all of parent B's contributed
material reads as "the mutation's move" — clusters and anchors then encode
the other parent's code as a tried strategy, and the same child is
double-counted (often "improving" for the weaker parent and "catastrophic"
for the stronger, compounding F1). The trail half of this file explicitly
handles multi-parent DAGs; the diff half never mentions crossover — a design
blind spot, not a decision. Cheap mitigations: include the child's other-parent
ids in the payload so the analyst can discount merges, or diff against the
base parent (the mutator's explicit base/donor choice,
`prompts/mutation/system.txt:5`, is recorded in mutation metadata).

### F4 — ~3× strong-LLM calls per mutant, value never isolated. MEDIUM

Steady-state per new child: the child's own DAG runs the suggester (~1 call),
and ParentRefresher requeues each of 2 parents → 2 intra re-renders (each
carrying parent code + up to 24 child diffs — cumulative payload per parent
grows O(k²) until the cap) + 2 suggester re-runs. Plus the mutator: ≈6
strong-LLM calls per mutant vs 2 for `pipeline=legacy`
(mutator + InsightsStage). Each new child also re-clusters the whole lineage
from scratch — labels are regenerated, so cluster identity is unstable across
re-renders and any `evidence_refs` cluster labels from earlier suggestions
silently dangle.

The A-arm bar (0.0294, WITH this machinery) has never been compared to a
legacy-pipeline bar on the same task; iter-matched no-mem parity results say
nothing about whether intra+suggester itself pays for its 3× call budget.
This is the single highest-information cheap experiment available on the
standard pipeline: 2× `pipeline=legacy` heilbron replicates against NM1-4.

### F5 — Hardcoded noise floor duplicates an existing seam. MEDIUM

`_DELTA_NOISE_FLOOR = 1e-4` is justified in-comment by "current pipelines
work in fitness ≈ 0.02–0.05 bands" (lineage_memory.py:553) — a heilbron-band
constant in a domain-agnostic framework (wrong scale for R²≈0.7 tabular, for
integer-valued metrics, etc.). The correct seam already exists and is used
20 lines away in the sibling stage: `MetricSpec.significant_change`
(mutation_suggestions.py:117). Bucketing should use the per-metric quantum
and fall back to 1e-4 only when unset.

### F6 — Signal side-channel + stale module docstring. LOW-MEDIUM

The plateau signal travels via `program.metadata[intra_memory_signal]` read
inside the agent (agents/mutation_suggestions.py:120) rather than through the
DAG edge that carries the card — two sources of truth for one artifact. The
exec-dep keeps them coherent in practice, but a failed `storage.update`
(soft-absorbed, lineage_memory.py:979) leaves a silently stale signal next to
a fresh card, and nothing in the cache key covers it independently. Also the
module docstring (lineage_memory.py:6-9) still claims an optional
`memory_cards` input that `IntraMemoryInputs` no longer has, and the
suggester docstring claims trail changes "ride on the children-id change"
(mutation_suggestions.py:31) — a parent's *ancestor* trail is actually frozen
at creation; the claim is vacuously safe but wrong as stated.

### F7 — Nits. LOW

- `median = sorted[n//2]` is the upper median for even n (lineage_memory.py:659).
- Trail entries carry no ancestor ids — the suggester can cite
  `depth_back` values in `evidence_refs` but nothing downstream can resolve
  them.
- Intra card is delivered to the mutator twice: verbatim via
  `MutationContextStage.memory` AND digested via the suggester's insights
  (lineage_memory_pipeline.py:233). Deliberate (mutator may cite clusters
  directly) but it double-spends tokens on the same evidence and lets the two
  renditions disagree; worth an explicit decision note.

## Interaction with documented findings

- Suggester output on the parent is overwritten on re-eval and not copied
  into the child's mutation_context (memory: `mutation_suggestion_state_loss`,
  ~80% drift; overwrite is by design per `stage_results_recompute_is_design`).
  Design consequence: the F4 ablation can't be audited retroactively — which
  suggestion produced which child is unrecoverable unless snapshotting is on.
- Card-obligation displacement (`project_card_usefulness_investigation`) is
  addressed in the current evidence-gated prompt; the A/B for it is still owed.

## Recommended order of action

1. F1 orientation fix (small, test-first: minimize-metric fixture asserting
   bucket labels + signal severity) — correctness.
2. F2 sampling decision (recency window or stratified; align prompt claim) —
   analysis validity.
3. F4 legacy-vs-standard ablation (2 runs, reuses NM harness) — decides
   whether F3/F5/F6 polish is worth doing at all.
4. F5 significant_change-driven bucketing alongside any F1 edit (same lines).
5. F3/F6/F7 as opportunistic cleanups with the above.

## Addendum — F1/F2/F3 fixed (2026-07-02, this commit)

F1, F2, and F3 are fixed on `feat/gain-event-context-timestamp-parentid`,
test-first, converged through a two-reviewer loop (subagent + codex, both
SHIP):

- **F1**: `_collect_evaluated` orients child deltas
  (`(child - parent) * sign`) with the same convention as
  `collect_ancestral_trail`; buckets/verdicts/renders consume oriented values;
  prompt + card text updated to say "+ = improvement".
- **F2**: `DescendantProgramIds` switched from `best_fitness` to a new
  `recent` AncestrySelector strategy (chronological tail, no fitness
  filtering — failures stay visible); prompt/render/schema describe a recency
  window instead of claiming complete history.
- **F3**: crossover children carry `crossover_role` ("base"/"donor") resolved
  from the `memory_base_id` stamp, falling back to the mutator's 1-based
  `mutation_output["base_parent"]` index, then `parents[0]` (matching
  `freeze_base_parent_snapshot`).
- **Bonus (found in review)**: the mutator self-report was read from a
  never-written `"mutation"` metadata key — now reads `"mutation_output"`
  (`MUTATION_OUTPUT_METADATA_KEY`), so `mutation_archetype`/`justification`
  actually reach the analyst payload.

Cache versioning for stale pre-fix cards on resumed runs was considered and
explicitly rejected by the owner (accepted risk; the id-list change from the
`best_fitness`→`recent` switch re-keys most parents on first visit anyway).
F4 (legacy-vs-standard ablation) is moot: the legacy pipeline is unused.
F5-F7 remain open as polish.

Tests: `tests/stages/test_intra_memory_payload_semantics.py` (new, 12 cases),
`TestRecentStrategy` in `tests/stages/test_ancestry_selector.py`.
