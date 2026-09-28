# Memory-subsystem review fixes — plan (2026-07-12)

Source: adversarial Codex review (gpt-5.6-sol xhigh, thread 019f5779-f344) of
`gigaevo/memory/` (7,872 lines). 10 findings: 8 MAJOR, 2 MINOR, 0 CRITICAL.
Config-seam category clean; probe/eviction lane-partition arithmetic verified
identical on both sides (no drift). All 10 findings independently verified
line-accurate by the orchestrator; deep checks confirmed the load-bearing
mechanics:

- `gate.admit()` (admission.py:221) wholesale-replaces a known id ("known id
  replaced") → F3 evidence wipe is real.
- `retire_twin` → `retire_exemplar` = plain `_store.delete` + ledger row; no
  evidence transfer → F4 orphaning is real.
- `_preserve_external_event` (stats.py:539) returns False for
  `attribution=None` events → F6 legacy-evidence erasure is real.
- `_stat_token` = `(st_mtime_ns, st_size)` → F9 real.
- `absorbed_ids` already has the right consumers (exclusion.py:13, stats.py
  event folding :529 + orphan resolution :610, merge) → F4's aliasing fix
  plugs into existing machinery. NOTE: stats.py:529 folds absorbed events for
  INSIGHT cards only, so F4 copies events directly in the librarian instead of
  relying on fold-time aliasing for PROGRAM cards.

Live np2 run (pid 991543) is unaffected by source edits: its process loaded
modules at startup and workers fork. New runs pick up the fixes.

Branch: `memory-review-fixes` off `main`. Test-first per finding: failing test
demonstrating the bug, then the minimal fix. Commit only with user approval.

## PR-1 — lifecycle evidence loss (F3, F4, F6) — highest priority

Production-relevant now: matches the two zero-event program-exemplar cards
observed in the np2 bank; F6 hits any shared/legacy bank restamp.

- **F3** (writer.py:543 → librarian.admit_program): re-admitting an existing
  `program-<id>` must not erase evidence. Fix in `admit_program`: if the store
  already holds the incoming id, copy its `gain_events` and `absorbed_ids`
  onto the replacement card before `gate.admit`. Failing test: admit exemplar,
  stamp a gain event, re-admit same program → event survives.
- **F4** (librarian.py:286 twin replacement): supersession must not orphan the
  twin's evidence or id. Fix: before admitting the incoming card, union the
  twins' `gain_events` onto it and extend `absorbed_ids` with each twin's id +
  absorbed chain (dedup, never self-referencing per cards.py:321 validator).
  Failing test: evidenced `program-old`, code-identical better `program-new` →
  new card carries old events; `program-old` resolvable via absorbed_ids
  (orphan-resolution at stats.py:610 and exclusion.py:13 both see it).
- **F6** (stats.py:539 `_preserve_external_event`): unattributed
  (`attribution=None`) non-founding events must be preserved when external
  preservation is enabled — they cannot be proven to belong to the current
  pool. Failing test: card with attribution-None non-founding event + a
  preserve set → event survives restamp; founding events keep current
  behavior; attributed in-pool events still replaced.

## PR-2 — contract/robustness quick wins (F1, F10, F2, F9)

- **F1** (crediting.py:113): wrap `comparison.estimate()` + `.se` coercion in
  try/except → `self._degrade(outcome, "comparison_error")`; a raising
  estimator must never abort the restamp sweep (documented degrade-never-raise
  contract). Validate `n_resamples > 0` at PairedBootstrap construction.
- **F10** (bank.py:162): on reload, validate payload key == embedded card id;
  raise `MemoryStorageError` on mismatch. No migration script (convention).
- **F2** (probe.py:90 / auction.py:681): recompute
  `probe_eligible = bool(support_kind) and support_n < floor` for EVERY slate
  row (including selected ones); derive unselected probe candidates from the
  marked rows. Telemetry-truth fix; decision behavior unchanged.
- **F9** (bank.py:178): stat token becomes
  `(st_mtime_ns, st_size, st_dev, st_ino)` — atomic replace always changes
  inode.

## PR-3 — concurrency / transactional writes (F7, F8, F5)

Multi-process-conditional (shared cross-run banks); design pass before code.

- **F7** (stats.py:608 + storage/local.py:79): add atomic
  `update(card_id, transform)` on the store protocol (behind-seam extension);
  restamp uses it instead of snapshot→save. Read-modify-write must happen
  under the exclusive bank lock.
- **F8** (admission.py:312 sweep): recompute the eviction verdict on the
  freshly-loaded card under the exclusive lock before delete.
- **F5** (live eviction race): DESIGN DECIDED 2026-07-13 (orchestrator, per
  Codex design memo on thread 019f580c-6fef). Split into PR-4 (engine-touching
  breadth). Architecture: process-local thread-safe (threading.RLock — writer
  sweeps run in to_thread) `InFlightSelectionRegistry` +
  `SelectionLease` in new `gigaevo/memory/selection_leases.py`, refcounted
  (attempt->cards, parent->attempts, child->cards, card->owner count);
  `LeasedMemoryProvider` decorator (existence re-check + acquire under the
  same eviction_guard the gate uses); attempt lease opened in run_one_mutant
  (mutant_task.py:52), coalesced-fresh safeguard after refresh (:60-84),
  transfer to child id right after storage.add (mutation.py:210, retain
  BASE_SELECTED ids only), unconditional release in run_one_mutant's existing
  finally (:140); ingestor abandon hook for leaked_ids (ingestor.py:53);
  terminal-child release after gate.sweep in restamp_and_sweep (stats.py:636)
  = self-normalizing bound of one full writer refresh, no time constants;
  enforcement in CardAdmissionGate sweep/admit/merge under eviction_guard
  (check + delete inside ONE guard). Dataless alternative REJECTED (no durable
  selection epoch; NO_CACHE requeues overwrite metadata; failed mutations look
  in-flight forever). Registry is process-local: closes the flagged in-process
  race; cross-process residual = signal loss bounded by F8 + orphan handling
  (Phase 4 audit item).

Paranoia-grade tests for PR-3/PR-4 (concurrent restamp+evict,
rescue-before-delete, cancellation mid-LLM, vanished-child lease abandon).

**PR-4 STATUS: DONE + ACCEPTED 2026-07-13** (Codex thread 019f583f-4e30, verified
by orchestrator). Implementation matches the decided design exactly; extras
found sound on inspection: (a) lock ordering is uniformly registry RLock →
store lock (reentrant `is_leased` inside sweep's update() transform is safe);
(b) `merge()` aborts BEFORE any mutation when the absorbed partner is leased,
and skips the harm-union double-delete if either card is leased; (c)
`_preserve_external_event` now preserves unattributed events under a supplied
preserve-set — correct for shared banks since every current-run stamper writes
`EvidenceAttribution` (stats.py:155/301/318/337), so only foreign/legacy
evidence is protected; single-run (None) semantics unchanged; (d) terminal
release loops over the whole crediting pool — no-op re-releases, and releasing
never-creditable children avoids a permanent lease leak; (e) singleton wiring
via top-level `${ref:selection_leases}` consumed by engine + provider + gate +
updater, asserted in test_config_defaults.py; non-full presets keep plain
ReaderMemoryProvider and None defaults. Gate: ruff clean, tests/memory +
tests/evolution + tests/integration all green (EXIT:0, 3 known skips).

PARKED finding (engine, from F5 memo): `DAG._run_internal()` (dag.py:114) has
no outer finally cancelling/awaiting pending_tasks — DAG timeout/cancellation
can leave stage tasks detached. Fix after PR-4 if goal scope allows.

## Phase 4 — cross-task shared-bank consensus audit (user directive 2026-07-12)

Future scenario to certify: multiple evolution runs, DIFFERENT tasks, ONE shared
memory bank. Cards written under task A must be retrievable, adjudicable, and
creditable under task B — machinery wired for transfer, no silent task silo.
EXTENDED 2026-07-13 (user): the runs may also execute CONCURRENTLY — multiple
processes writing to and reading from the same bank at the same time, not just
sequentially. Cross-process safety is first-class, not conditional.
Consensus required (orchestrator + adversarial Codex audit) that the system
works before closing the goal.

Orchestrator recon (verified in code):
- Retrieval transfer wiring PRESENT: `_where` (index.py:316) filters only
  kind + exclude_ids — no task filter; `nearest_scope` default `desc_expl`
  deliberately excludes task_description (config.py:41); `desc_task` exists as
  the task-conditioned channel; embed-fingerprint guard (index.py:92) protects
  shared persist dirs from mixed embedding configs.
- Cross-task crediting legitimacy OPEN: `DecisionContext` (cards.py:38) has no
  task identity — only parent_metrics/parent_id/timestamp; parent_metrics keys
  and scales are task-specific, so bd_proximity reputation and per-context harm
  eviction pool incomparable contexts across tasks; ContextualGain.gain is a
  raw fitness delta on the writing task's scale.

Audit scope (adversarial, read-only, after PR-1..3 land):
A. Retrieval/embeddings: research planner query formation + reflection/
   shortlist judging cross-task candidates; twin search scope in librarian
   (cross-task code-twin collisions); consolidation near-dup merge folding
   cards from different tasks (merge keeps target task_description — is the
   union legit?); MMR diversity across task clusters.

   AREA A VERDICT (Codex audit 2026-07-13, thread 019f5823-bd39, all
   load-bearing claims re-verified by orchestrator): NOT transfer-ready.
   1. Query/reflection — BROKEN (MAJOR): planner queries bake in current-task
      entities (live telemetry: 193/200 steps queried desc_task, 4/200
      task-agnostic description); reflector prompt ranks "task fit first",
      prefers matching task_description_summary, and gates on same
      parameter/component/algorithm-family naming → analogical foreign-task
      cards culled post-retrieval (retrieval_reflection/system.txt:19).
   2. Write-time shaping — WIRED-BUT-UNTESTED (MAJOR): reconcile/author
      prompts demand transferable mechanisms (good) but nothing enforces it;
      reconcile-LLM failure admits the raw mutation note VERBATIM as an
      indexed card (librarian.py:126) → task-specific vocabulary in bank.
   3. Rendering — BROKEN (MAJOR): efficacy lines strip task provenance;
      task-A gain events render as "expected improvement +x (confident)" on
      task B (scale incomparable; direction IS normalized); program cards
      render raw exemplar fitness (render.py:27,47) which is meaningless
      under another task's metric; mutation_suggestions prompt obligates
      transposing confident-positive cards.
   4. Twin/consolidation — BROKEN (CRITICAL): program twins matched globally
      by code hash with no task check (librarian.py:328); winner picked by
      CURRENT run's higher_is_better on raw cross-task fitness
      (librarian.py:294); global exemplar cap (writer.py:573
      _prune_program_exemplars) sorts the whole shared shelf by raw fitness
      in the current run's direction → a minimize-task writer retires a
      maximize-task's best exemplars; insight desc-twins + consolidation
      merge pool evidence across tasks while keeping the target's
      task_description (merge.py:98).
   5. Exclusion/lineage — WORKS: program-local applied-card ids, UUID id
      spaces, alias expansion correct across runs.
   6. MMR/staleness/ranking — BROKEN (MAJOR): mmr_lambda documented as not
      consumed by the research loop; staleness is bank-event-count-relative
      (staleness.py:50) so a fast foreign run ages everyone's cards;
      auction bids pool raw oriented deltas; EB prior + no-card observations
      + BD context keys have no task namespace (prior.py:205, no_card.py:108,
      models.py:224).
B. Reputation/crediting: event pooling across tasks with incomparable gain
   scales; bd_proximity distance on disjoint metric dicts (garbage vs neutral);
   quantile/self-normalizing thresholds normalized over a mixed-task bank;
   staleness across runs with different sweep cadences.
C. Eviction: global delete on task-A harm evidence killing a card helpful for
   task B; whether eviction_contexts machinery can partition by task.
D. Identity/persistence: program-<id> and card id namespace collisions across
   runs; F7-F10 multi-process correctness as the shared-bank substrate.
E. Concurrent multi-run operation (added 2026-07-13, user directive): two+ live
   writer processes on one bank — exclusive bank lock arbitration across
   processes (lock file semantics, stray/0-byte .lock handling, crash-release);
   interleaved restamp sweeps double-crediting or clobbering each other (F7 is
   necessary — is it sufficient?); concurrent eviction sweeps + admission twin
   races (two processes admitting code-twins simultaneously); consolidation
   running in two processes at once (merge targets vanishing mid-merge);
   events.jsonl append + reader races across processes; Chroma persist dir
   concurrent access (VectorIndex lock is threading.Lock — process-LOCAL);
   reload cadence via F9 stat token (does a reader see a torn bank state?);
   F5 lease registry is process-local by design — cross-process in-flight
   selection eviction remains a signal-loss residual, quantify acceptability.
Verdict per area: WORKS / WIRED-BUT-UNTESTED / BROKEN (with failure scenario).
MAJOR findings get fixed (delegated, test-first); repeat until consensus.

ARCHITECTURE CONSTRAINT (user 2026-07-13): the cross-task system must be a
clear EXTENSION of current machinery, wired through the existing OOP seams —
subclasses / decorators / policy objects behind the established Protocols and
Hydra _target_ config entries. No if-task_key branches sprinkled through core
classes; single-task behavior stays the unchanged default composition.
Verified seam map (each PR must land through these):
- Card / DecisionContext (cards.py): additive optional fields (task_key,
  default "") — legacy banks/events parse unchanged.
- Write-side twin/dedup/cap: DedupPolicy + ProgramExemplarPolicy are already
  _target_ policy objects (config/memory/full.yaml:124,132) — task-local
  variants extend these policies, librarian/writer code paths unchanged.
- Eviction: Evictor protocol + CompositeEvictor member list (evictor/
  recommended.yaml) — task-scoping lands as a wrapper/decorator member or
  scorer variant, injected via ${ref:memory.reputation} like today.
- Reputation: ReputationModel / EvictionFacingReputation /
  DecayCompatibleReputation Protocols (read/interfaces.py:30-88) with an
  existing subclass stack (BetaBinomialReputation → BDProximityReputation;
  BootstrapReputation) — task-gated + sign-only-foreign behavior is a new
  subclass/decorator in that stack.
- Prior: MemoryPrior Protocol (prior.py:19) — task ladder level extends
  EmpiricalBayesMemoryPrior via subclass/config, FixedMemoryPrior untouched.
- Read selection: Auctioneer / CandidateProjector / ProbePolicy / Budgeter /
  Shortlister Protocols — any task-aware filtering composes as decorators.
- Rendering: CardRenderer Protocol + EfficacyCardRenderer _target_
  (full.yaml:82) — provenance-aware rendering is a renderer subclass swap.
- Provider: MemoryProvider ABC decorator pattern (LeasedMemoryProvider from
  PR-4 is the template) for read-side lease/existence concerns.
- Prompts: externalized prompt files (retrieval_planner, retrieval_reflection,
  consolidate) — cross-task judging changes are prompt-file edits, no code.
- Storage: MemoryStore ABC additive methods (PR-3 update() is the template).

Proposed transfer-fix ladder (orchestrator draft 2026-07-13, from Area A;
sequenced after PR-3/PR-4; each PR delegated test-first):
- PR-5 (substrate — task identity): stable `task_key` on Card and on
  DecisionContext (evidence provenance). Optional field, default "" — legacy
  cards/events parse unchanged (no migration scripts, per convention). This
  unlocks every scoping fix below and closes the Phase-4B "no task identity"
  root cause.
  **PR-5 STATUS: DONE + ACCEPTED 2026-07-13** (Codex thread 019f587d-9140,
  verified by orchestrator). `task_key` on Card (cards.py:262) +
  DecisionContext (cards.py:48); stamping threaded through MemoryWriter →
  librarian (authored + reconcile-fallback), program exemplars (writer.py:560),
  founding + outcome events (stats.py), no-card observations
  (no_card.py), read-context models (GlobalMemoryContext/BDCellMemoryContext —
  the BD model now builds its context directly with self.task_key instead of
  delegating to the fallback, behaviorally identical since fallback is typed
  GlobalMemoryContext); merge survivor explicitly keeps target.task_key
  (merge.py:113); consolidation proposal preserves target provenance.
  Config: context_model.task_key + writer.task_key = ${problem.name} in
  full/reader/writer presets. Scope guard held: grep shows ZERO task_key
  branching in gigaevo/. `card_gain_events_from_programs` has no live
  production caller (docstring only) — no unstamped path. Gate re-run by
  orchestrator: ruff clean, tests/memory + tests/integration EXIT:0.
  NOTE: working branch is `memory-review-fixes` (not memory-cold-probe-policy);
  banks written before PR-5 are legacy (task_key "") per no-migration
  convention — cross-era twin collapse is not guaranteed.

- PR-6 (write-side task-locality — kills the CRITICAL): program twin search
  and desc-twin collapse become task-local; exemplar cap prunes ONLY the
  writer's own task's exemplars (own direction, own scale); retire_twin
  likewise task-local. Consolidation may still merge cross-task (that is the
  transfer goal) but the arbiter prompt must see BOTH originating tasks and
  the merge must keep multi-task provenance rather than the target's task
  fields silently winning. PROVENANCE-UNION RESOLUTION (orchestrator
  2026-07-13): no new card-level structure needed — after PR-5, every gain
  event carries its own context.task_key, so a merged card's evidence set
  keeps per-event task provenance through merges (PR-8 partitions on the
  EVENT's task_key, not the card's). Card.task_key stays single-valued =
  authoring task, used for twin/cap locality and rendering only; the arbiter
  seeing both tasks is a consolidate-prompt edit.
  SCOPING MECHANISM DECISION (orchestrator 2026-07-13): DedupPolicy /
  ProgramExemplarPolicy are frozen knob objects — the twin/cap LOGIC lives in
  librarian/writer code. Task-locality lands as an unconditional same-task_key
  predicate inside the twin-candidate filter and the exemplar-cap ranking
  (part of the DEFINITION of comparability, like direction), NOT as a config
  flag or mode branch — single-task banks are behavior-identical by
  construction (all cards share one task_key), which satisfies both the
  no-if-task_key-mode-branches constraint and minimum-viable-design. The
  exemplar cap becomes per-task residency (writer prunes ONLY its own task's
  shelf; foreign exemplars neither counted nor pruned). Insight-side neighbor
  recall stays cross-task (transfer goal); the reconcile/consolidate arbiter
  prompts gain card task provenance so the LLM judges mergeability across
  tasks knowingly.
  STATUS: DONE + ACCEPTED (Codex task-mriehquq-cjxml2, gpt-5.6-sol xhigh,
  2026-07-13; orchestrator inspection + gate re-run). Delta verified line by
  line against the mixed tree (PR-2/4/5 changes co-resident):
  * `_program_twins` (librarian.py:336-343) gains the unconditional
    `other.task_key != card.task_key → skip` predicate; `_best_by_fitness` /
    `_strictly_better` have NO other callers (grep), so every fitness
    comparison is now same-task. retire_twin task-locality follows from the
    filtered twin list; PR-4 leased-skip composes (extended
    test_twin_retirement_skips_leased_program_card with explicit task_key).
  * `_prune_program_exemplars` (writer.py:591-596) counts/prunes only
    `c.task_key == self._task_key` PROGRAM cards; ProgramExemplarPolicy
    .max_cards description now says "Per-task hard cap".
  * Arbiter provenance via new `arbiter_card_brief` / `_with_origin_task`
    (reconcile.py:142-149): reconcile neighbors + submitted note and both
    consolidate candidates render "origin task: <task_key>" ONLY when
    nonempty — empty-key prompts byte-identical (asserted in new
    tests/memory/write/test_arbiter_prompts.py, 4 tests). Librarian passes
    task_key to ReconcileAgent.arun (librarian.py:124).
  * Scope guard held: admission.py has ZERO task_key references (gate merge
    path untouched); consolidation.py's only touch is the PR-5 proposal
    preserve; neighbor recall unfiltered; no config flags, no new policy
    classes.
  * Tests: cross-task twin non-interference + foreign-fitness direction
    non-corruption (test_librarian.py:781-812, shared code hash "x = 1"),
    cap ignores-foreign + prunes-own-only (test_writer.py:539-613, foreign
    -100 fitness untouched), arbiter provenance (new file), leased extension.
    Existing legacy-expectation tests unmodified. Gate re-run by
    orchestrator: ruff clean, tests/memory + tests/integration EXIT:0.
  * DELIBERATE DEVIATION from the sketch above: `_desc_twin` (exact-prose
    degrade-path collapse) stays CROSS-task — byte-identical prose is
    task-agnostic by construction, bump_provenance does no fitness
    comparison, and post-PR-5 the folded evidence keeps per-event task_key;
    task-localizing it would mint duplicate cards consolidation would just
    re-merge. "Merge keeps multi-task provenance" is satisfied by the
    provenance-union resolution (event-level task_key), not card fields.
  * CARRY-IN → PR-7: the optional one-sentence arbiter guidance ("merging
    across tasks is acceptable only when the mechanism genuinely transfers")
    was not added (builders-only change); add it to the reconcile +
    consolidate system prompts in PR-7 alongside the other prompt edits.
- PR-7 (read-side transfer enablement): reflector prompt — mechanism fit
  stays the gate but drop "task fit first" + task_description_summary
  preference (analogical foreign-task cards must be selectable); planner
  prompt — require at least one task-agnostic mechanism query per plan;
  render — append explicit provenance when card.task_key != current task
  ("evidence from a different task") and suppress raw exemplar-fitness line
  for foreign-task program cards.
  STATUS: DONE + ACCEPTED 2026-07-13 (Codex task-mrifidhj-l72k5n, gpt-5.6-sol
  xhigh; spec scratchpad/pr7_prompt.txt). Scope additions vs the sketch:
  (a) candidate_brief (gigaevo/memory/storage/research.py:195) gains
  origin_task when card.task_key nonempty — without it the reflector rule
  has nothing to consume (output-consumption check); (b) renderer FOREIGN
  check = BOTH renderer.task_key and card.task_key nonempty AND differ
  (legacy "" never claims "different task"); renderer task_key wired
  ${problem.name} in full.yaml+reader.yaml; (c) PR-6 carry-in: one
  origin-task sentence each in reconcile + consolidate system prompts;
  (d) foreign fitness handled in the reflector by prompt rule (ignore,
  non-comparable) — payload suppression deferred to PR-8. Prompt edits
  line-targeted only (standing no-wholesale-rewrite rule).
  VERIFIED DELTA (orchestrator, line-by-line): render.py —
  EfficacyCardRenderer.task_key field (default ""), foreign =
  bool(self.task_key and card.task_key and self.task_key != card.task_key),
  foreign PROGRAM suppresses format_block_efficacy, any foreign appends
  "evidence from a different task (<key>)"; format_block_efficacy itself
  UNCHANGED (single-source contract intact, tests/llm efficacy contract
  untouched). research.py candidate_brief: origin_task inserted after kind
  iff card.task_key nonempty. Prompts (all line-targeted, BEFORE→AFTER in
  Codex report): reflector — origin_task bullet; "Rank by task fit first"
  REPLACED by mechanism-fit-is-the-gate cross-task selectability rule;
  foreign fitness = different scale, ignore-not-compare;
  task_description_summary = understand-where-it-worked, not match filter.
  Planner — one rule requiring a task-agnostic mechanism query per plan.
  Reconcile + consolidate — one origin-task guidance sentence each (PR-6
  carry-in CLOSED). Configs: reader.renderer.task_key: ${problem.name} in
  full.yaml + reader.yaml. Tests verified: test_render.py 6 new cases
  (foreign program/insight/same-task/unstamped/legacy), prompt guard tests
  assert exact sentences, test_research origin_task iff nonempty,
  test_config_defaults renderer wiring. Test-first failure shown in report
  (extra_forbidden on task_key pre-implementation). Gate re-run by
  orchestrator: ruff clean + pytest tests/memory tests/llm
  tests/integration EXIT:0 (2 known skips).
  PR-8 SPEC READY (scratchpad/pr8_prompt.txt, orchestrator-verified file
  map): single split_events_by_task helper; card_stats seam partitions
  magnitude native-only + folds foreign sign into the Beta-Binomial via
  existing Phi soft-counts; CardStatsBlock gains foreign help/total counts;
  bootstrap support native-only; BD-proximity bucketing native-only; EB
  ladder gains a "task" token (sign-based counting stays globally pooled);
  staleness partitions per task on BOTH read and write sides; no-card
  summary_for filters by task; harm/catastrophic eviction native-only with
  the probe/eviction lane LOCKSTEP invariant as acceptance criterion (task-A
  harm can never delete task-B's helper); render adds foreign help-rate
  line. Derived stats verified computed-from-events at read/sweep time (no
  stamped-posterior last-writer-wins hazard). Launch strictly AFTER PR-7
  acceptance (one --write Codex task at a time; PR-7 and PR-8 both touch
  render.py).
- PR-8 (statistical scoping) — REQUIRED for consensus, not caveat-able (user
  2026-07-13: "fitness diff and context seem meaningless across tasks"):
  ContextualGain.gain is a raw delta on the writing task's scale and
  DecisionContext.parent_metrics is a task-specific metric dict — pooling
  either across tasks is statistically illegitimate.
  DECIDED (user 2026-07-13): cross-task evidence is consumed as BINARY
  "gain / no gain" only — never magnitude. This is well-posed because gains
  are already stored direction-normalized (positive = improvement regardless
  of metric direction; extraction negates for minimize), so the sign is the
  task-comparable projection. Mapping onto existing machinery:
  * magnitude-based quantities (bootstrap EV bids, IntroGain medians, harm
    soft-counts vs task scale, catastrophic-loss eviction against
    significant_change) consume ONLY same-task_key events;
  * foreign-task events feed the Beta-Binomial p(help) pathway as
    success/failure counts — sign-based, threshold 0, optionally
    significance-aware via the existing Phi(gain/se) soft-count (no new
    constants);
  * EB prior ladder gains a task level (global → task → kind/category →
    context) so cold cross-task borrowing is shrinkage, not scale mixing;
  * bd_proximity is task-gated: cross-task contexts fall back to the coarser
    prior level, never a distance over disjoint metric dicts;
  * staleness event-counting and no-card control summaries partition by
    task_key;
  * rendering (PR-7 overlap): foreign-task evidence lines report help rate
    ("helped in k of n uses on other tasks"), never a fitness delta.
- Consensus test (with PR ladder): A-write/B-read end-to-end test — card
  written under task A, retrieved+selected+rendered+credited under task B;
  plus cross-task twin/cap non-interference tests.
  STATUS 2026-07-13: PR-8 DONE + ACCEPTED (Codex task-mrig5b8k-m4oql2, thread
  019f58bd-973a-7602-93c7-35ae4efc72c7, gpt-5.6-sol xhigh; spec
  scratchpad/pr8_prompt.txt). VERIFIED DELTA (orchestrator, line-by-line):
  split_events_by_task in context/evidence.py:17 (exact equality, ""=="" ,
  order-preserving, pure); CardStatsBlock foreign_help/total_events
  (cards.py:235) with unset-default serializer → legacy blocks roundtrip
  byte-identical; reputation.py — _foreign_sign_counts reuses _harm_mass
  Phi soft-count at threshold 0 (invalid=failure, founding/unused skipped),
  _block_from_partition folds foreign ONLY into posterior_a/b +
  p_help_mean/lo20, efficacy_confident still requires NATIVE intros>0 +
  positive native magnitude; bootstrap support methods (event_deltas/
  weights/events/ses) native-only; BDProximity buckets native-first with
  global foreign sign fold; decay.py:82 harm floor gates on native
  intro_events (foreign mass can't make a card harm-ripe); staleness.py
  task-partitioned with cache keyed (id(bank), task_key) + strong-ref
  identity check; population rule CORRECTED post-PR-9 (the original
  vacuous-len(bank)/mixed-event-count branch was NOT benign — see PR-9
  defect #2): now branch-free card-based population = cards with native
  evidence plus never-evented cards; no-foreign banks keep len(bank)
  EXACTLY (legacy identity), and foreign traffic on evented cards can
  never shift a task's half-life;
  no_card summary_for filters exact task; projection _use_count native
  (feeds novelty-discounted EV bid — magnitude decision); render
  format_block_efficacy appends sign-only "helped in k of n uses on other
  tasks" iff foreign_total>0; eviction.py — Harm/PolicyNonViable/
  BirthFailure evictors take task_key, verdicts native-only,
  _writer_context stamps reputation reads; configs — evictor/harm.yaml +
  recommended.yaml (3 evictors) task_key: ${problem.name}; EB prior gains
  "task" token, default ladder kind → kind+category → task+kind+category →
  context → context+kind → context+kind+category →
  task+context+kind+category (monotone in both validator blocks;
  task levels skipped for unstamped contexts); ONE line-targeted prompt
  edit (mutation_suggestions/system.txt documents the foreign line as
  binary-only). SCOPE GUARD verified: zero task refs in auction.py,
  crediting.py, admission.py, probe.py, shortlist.py, fused.py.
  LOCKSTEP TEST verified (test_eviction.py:428): shared mixed-task fixture,
  slate support_n == evictor._effective_support, probe_eligible ==
  (support < floor), foreign magnitude 1000.0 excluded, below-floor not
  evictable. Legacy/byte-identical regressions present (test_reputation.py:
  286 et al.). Gate re-run by orchestrator: ruff clean + pytest
  tests/memory tests/llm tests/integration EXIT:0 (2 known skips); nothing
  staged, HEAD unchanged 86d9390c.
  MINOR RESIDUAL: foreign PROGRAM help-line suppression — FIXED as PR-9
  defect #1 (below).

### PR-9 — cross-task consensus e2e test — STATUS: DONE + ACCEPTED (2026-07-13)

- Codex (gpt-5.6-sol xhigh) delivered tests/memory/test_cross_task_shared_bank.py
  (520 lines, test-only, untracked): real writer/librarian/gate/Chroma/
  reputation/renderer with fake LLM/embeddings; scenarios: A-write/B-read
  retrieval reachability + origin_task brief; foreign stats magnitude-empty
  + sign folds; probe-lane below-floor for foreign-only support; render
  provenance; task-B restamp isolation; per-task eviction; twin/cap smoke;
  legacy "" coexistence. Instructed to STOP on first production defect —
  it did, twice. Both defects were REAL and are now fixed (orchestrator
  edits, verified against the e2e + unit suites):
  DEFECT #1 (render.py): PR-7's blanket efficacy suppression for foreign
  PROGRAM cards also dropped the legitimate sign-only foreign help-rate
  line. FIX: render foreign programs through a fitness-less model_copy so
  single-source format_block_efficacy emits only the foreign line
  (render.py:85-92). PR-7 render tests unaffected (no-block path
  unchanged).
  DEFECT #2 (staleness.py): _task_bank_stamps population flipped from
  len(bank) (vacuous branch) to native-EVENT count when the first foreign
  event arrived, changing H → native staleness weight → bootstrap EV
  mean/lo20 for the OTHER task (test_3 caught task-A EV drifting
  -1.2708 → -1.8229 after a task-B restamp). The PR-8 note calling this
  "benign" was WRONG. FIX: branch-free card-based population
  (cards with native evidence + never-evented cards) — legacy len(bank)
  identity exact on no-foreign banks; foreign traffic on evented cards
  cannot move any task's half-life. Known corner (documented, accepted):
  an eventless card gaining its FIRST foreign event leaves other tasks'
  populations — transient, conservative, rare post-F3.
  Regression pins: test_staleness.py
  test_foreign_traffic_does_not_change_native_half_life (old branch gives
  2^(-2/3), fix gives 2^(-2/2)); consensus module runs to completion.
  Gate: ruff clean + pytest tests/memory tests/llm tests/integration
  EXIT:0 (2 known skips). Nothing staged; HEAD unchanged 86d9390c.

### Phase 4 D+E audit — DELIVERED 2026-07-13, verdict: NOT SAFE (yet)

- Codex read-only audit (gpt-5.6-sol xhigh, thread 019f58f8-321e) of Areas
  D/E + B/C re-verify. Orchestrator independently CONFIRMED both CRITICALs
  and the eviction MAJOR at code level before acting.
- CRITICAL E3 — eviction self-deadlock (CONFIRMED): sweep() revalidates
  verdicts inside store.update()'s EXCLUSIVE flock (admission.py:354-378;
  local.py:104); memory=full wires ${ref:memory.reputation} as the
  evictors' scorer and BOTH DecayingReputation (decay.py:124) and
  BootstrapReputation (reputation.py:815) call store.snapshot() from
  staleness — a SHARED flock on a new fd; flock treats fds as distinct
  owners even in-process → wedges forever. Armed in the default stack;
  hasn't fired live only because no sweep candidate has surfaced yet.
- CRITICAL E4 — concurrent merges can delete BOTH cards (CONFIRMED):
  gate.merge() = get → pure fold → apply_merges(survivor) → delete(partner)
  in separate lock scopes (admission.py:238-308); opposite-direction merges
  from two processes each delete the other's survivor; stale-read fold also
  clobbers concurrently restamped evidence.
- MAJOR C — native-only harm verdict + GLOBAL physical delete: task A's
  harm evidence can delete a card with strong task-B wins (eviction.py:67
  filter, admission.py:354 delete). Needs task-local retirement vs global
  deletion split.
- MAJOR D4/E5 — shared Chroma dir (checkpoint/chroma): fingerprint guard
  has a concurrent-first-open race (no CAS/lock, index.py:92) and the
  process-local index lock (index.py:68) does not guard cross-process
  rebuilds; bank/Chroma are not one observable transaction. Note: bank is
  source of truth, embeddings are LOCAL SentenceTransformer, and every
  cross-process bank change already triggers a full local index rebuild —
  chosen fix = process-local in-memory index, killing both findings.
- MAJOR E6 — no-card store: global 1024-row cap lets a fast task prune
  another task's controls (no_card.py:235); dedup keyed by program id only.
- BROKEN E2 — restamp sweep loses evidence when another process merges a
  card mid-sweep (update → not_found → event dropped; stats.py:622).
- MINOR (FIXED directly by orchestrator): staleness population counted
  eventless FOREIGN-AUTHORED cards into every task's population — a card-
  authoring flood by task B slowed task A's decay. Now eventless cards
  count only for their authoring task_key (staleness.py; regression test
  test_eventless_foreign_authored_cards_do_not_inflate_population).
- MINOR accepted/documented (not fixed): program UUID4 reuse via cloned
  DBs/replays (negligible in normal operation); mem-* ids 48 random bits
  (bump candidate); same-task concurrent twin double-admission (equal-
  fitness twins persist; consolidation eventually merges); write_ledger
  shared append unlocked (torn audit rows only, not decision state); NFS
  advisory-lock caveats; WORKS verdicts: E1 bank flock, D3 per-run
  events.jsonl.

FIX LADDER (sequential Codex write tasks, one at a time):
- PR-10 (DONE + ACCEPTED 2026-07-13, task-mrij7tjf-rnxdk7): E3 + E4 fixed
  as specified. Delivered: reentrant thread-owned bank lock in
  LocalMemoryStore (threading.local depth/mode; nested acquisition no-op —
  no new fd; shared→exclusive upgrade raises StorageError; disk refresh
  skipped at depth>1 for a stable in-transaction view); atomic
  MemoryStore.merge_retire(target_id, partner_id, fold) → frozen
  MergeRetireResult{merged,retired,target_missing,aborted} with
  in-transaction alias sanity (identical-id, reverse-merge via
  absorbed_ids, survivor self-absorption) and survivor-id validation;
  MergeAborted exception (gigaevo/exceptions.py, subclass of gigaevo
  MemoryError); admission.merge() rewired onto a fold closure (fresh-
  target evidence, lease checks inside the transaction, harm verdict via
  should_evict under the reentrant lock); apply_merges DELETED (zero
  references; consolidation + librarian both route through gate.merge()).
  Tests: tests/memory/storage/test_transactions.py (upgrade guard,
  fresh-target evidence, vanished target/partner, 20-iteration two-store
  opposite-merge race with at-least-one-survivor disk invariant, harm
  fold clears index, abort byte-identical bank, alias cycles, survivor-id
  ValueError) + tests/memory/write/test_transaction_regressions.py (E3
  deadlock pin: same-store BootstrapReputation sweep in a thread, 10s
  join) + lease-path admission tests; FakeStore mirrors the contract.
  Accepted delta: lease-protected harm-merge now ledgers DISCARDED
  instead of REJECTED_HARM (storage effects identical; pinned by test).
  Note: Codex task ended status="failed" only because the final report
  turn hit model capacity AFTER one last file change; orchestrator
  re-verified the tree line-by-line and re-ran the full gate — ruff clean
  + tests/memory tests/llm tests/integration all green (2 known skips).
- PR-11 (DONE + ACCEPTED 2026-07-13, task-mrik2xf8-hs31rp): Area C + E2
  fixed. Delivered: shared sign-fold helpers moved to
  context/evidence.py (split_events_by_task, harm_mass, sign_help_counts
  — old reputation-local copies removed, arithmetic identical, pinned by
  test_cross_task_guard_and_reputation_share_foreign_sign_fold); frozen
  CrossTaskRetentionGuard evictor decorator (delegates native verdict;
  vetoes physical deletion iff ANY foreign task's sign evidence has
  total_mass >= min_effective_events AND help_mass > 0.5*total_mass;
  empty-task_key events never count as foreign; per-task grouping sorted
  for determinism; veto appended to eviction_reason); config: every
  deleting evictor in evictor/recommended.yaml + evictor/harm.yaml
  individually wrapped, floor reuses ${memory.evidence.min_effective_events},
  task_key=${problem.name} — no new constants. E2: restamp update →
  not_found now reconciles via _reconcile_vanished_restamp (fresh
  snapshot → absorber via absorbed_ids → restamp transform applied to
  survivor — stamper already folds absorbed-alias events by contract;
  multi-hop bounded by bank size, cycle guard, warnings on multi-hop,
  debug drop when genuinely evicted; redirected/dropped summary logged).
  Tests: guard family in test_eviction.py (vacuous single-task, foreign-
  majority veto, support floor, legacy identity, shared-fold parity),
  real two-store merge/delete race in test_stats.py
  (test_restamp_redirects_vanished_card_event_to_merge_survivor),
  instantiated config coverage in test_config_defaults.py (composed
  recommended stack = guards wrapping the right inners). Orchestrator
  fix on top: renamed sweep()'s inverted `retained` local to `evictable`.
  Full gate re-run by orchestrator: ruff clean + tests/memory tests/llm
  tests/integration all green (2 known skips).
- PR-12 (DONE + ACCEPTED 2026-07-13, task-mrikqgp4-d7fyug): D4+E5 killed
  by construction. Delivered: VectorIndex on chromadb.EphemeralClient()
  with per-instance uuid4 collection namespaces (Chroma 1.5.7 shares
  ephemeral backends within a process); rebuild() is DIFF-SYNC (stale ids
  deleted, only missing/changed documents re-embedded — cross-process
  refresh over an unchanged bank is cheap); StoreConfig.index_dir +
  _FINGERPRINT_FILE + persist-dir machinery removed, zero stale
  references repo-wide (existing chroma/ dirs = ignored dead data, no
  migration); docs/memory.md + MEMORY_LIFECYCLE_TUTORIAL.md +
  gigaevo/memory/README.md + memory_write_system.tex rewritten in place.
  Tests: startup rebuild from pre-existing cards.json, cross-store
  refresh serves from the second store's index, eviction removes from
  index, same-path stores' index state fully isolated (the E5 failure
  mode), shared-bank no-clobber; the forked bank-locking regression uses
  a child-process-local no-op index (forking an initialized Chroma
  runtime hangs; parent unaffected, original bank-atomicity assertion
  intact). Perf sanity (saturated box, conservative): model+init ~114s
  once per process; first full 50-card rebuild ~259s; steady-state
  refreshes only re-embed changed cards. Full gate re-run by
  orchestrator: ruff clean + tests/memory tests/llm tests/integration
  all green (2 known skips).
- PR-13 (DONE + ACCEPTED 2026-07-13, task-mrimlh3e-jgx18o): E6 + MINORs
  fixed. Delivered: no_card.py retention cap now PER-TASK (_pruned
  partitions by task_key, max_observations applies within each
  partition, naturals-before-controls priority preserved per partition,
  file order = age order preserved); dedup keyed by (task_key, id) — a
  fast task can no longer evict or overwrite a slow task's controls;
  mem-*/memsel- ids now full uuid4 hex (128 bits, bank.py:19 +
  events.py:54, no consumer assumed the old length); WriteLedger appends
  flock-guarded via sibling .lock (_WriteLedgerFileLock, failures still
  log-and-swallow — never blocks the write path); stale writer.py
  checkpoint_dir docstring corrected (ledger lives under the SHARED
  checkpoint dir alongside the bank). Tests: bidirectional retention-
  flood isolation, cross-task duplicate-id coexistence + task-scoped
  summary, 32-hex id shape/uniqueness, paranoia ledger stress (3 forked
  processes + 8 threads, exact row count + unique record ids), lock-
  failure and unwritable-path swallow paths. Full gate re-run by
  orchestrator: ruff clean + tests/memory tests/llm tests/integration
  all green (2 known skips).
- RE-REVIEW ROUND 2 (2026-07-13, task-mrinj5g0-4bp1zq, gpt-5.6-sol xhigh,
  read-only): verdict NOT SAFE. Per-item: E3 CLOSED, D4+E5 CLOSED, E6
  CLOSED; E4 / Area C / E2 PARTIALLY CLOSED; PR-8 NOT CLOSED. Six new
  findings, ALL VERIFIED REAL by orchestrator at code level:
  - N1 (critical): sign_help_counts (evidence.py:62) is a soft
    Phi(gain/se) count, not hard sign — foreign magnitude/SE leak into
    the foreign posterior bump (reputation.py:279) and the retention
    veto (eviction.py:124). Violates the user's binary sign-only
    contract. Native harm_mass consumer (reputation.py:185) is separate
    and stays soft. Fix: hard sign (help iff finite gain >= 0.0,
    weighted; invalid → total only) — matches the existing se=0
    indicator and prior.py's _first_non_founding_exposure convention.
  - N2 (critical): selection leases are process-local in-memory
    (selection_leases.py) while deletion is bank-global — process B can
    delete a card process A has in flight; A's credit later drops via
    E2 reconciliation (no absorber for a plain delete). Fix: durable
    flock-guarded lease sidecar consulted inside deletion transactions.
  - N3 (critical): gate.merge fold (admission.py:292) merges the STALE
    submitted closure card, ignoring the fresh partner merge_retire
    loaded; consolidation (consolidation.py:120-146) builds the
    submitted card from a pre-transaction snapshot — a concurrent
    restamp on the partner is silently discarded when the fresh partner
    is deleted. E2 reconciliation never runs (the restamp succeeded).
    Librarian idea-merge path is safe (id="" fresh card, partner None).
  - N4 (high): bump_provenance (admission.py:362) is get→save — a
    whole-card overwrite that clobbers concurrent event stamps.
  - N5 (high): retire_exemplar/retire_twin (admission.py:337-360;
    callers writer.py:615 pruning, librarian admit_program twin
    replacement) delete directly — no CrossTaskRetentionGuard veto, and
    admit_program folds twin evidence from stale snapshots.
  - N6 (high, NARROWED by orchestrator): EB prior context-bearing
    levels WITHOUT the task token (prior.py:320-344 local=True path)
    bucket foreign events by comparing foreign parent_metrics against
    the querying task's BD tessellation (models.py:281-285) —
    cross-task metric comparison is meaningless; foreign raw metrics
    select cohort membership. Global non-context levels are FINE
    (hard-sign pooling via gain >= 0.0, contract-compliant).
- PR-14 (fix N1, N3, N4, N5, N6 — one write task): binary foreign
  sign fold; fresh-partner evidence in gate.merge; transactional
  bump_provenance; retire_exemplar foreign-retention veto + fresh-card
  revalidation + evidence-preserving twin retirement via merge_retire;
  native-only cohort membership at context-bearing prior levels.
  DONE + ACCEPTED (task-mrio9e49-pt4lkx). Verified line-by-line:
  evidence.py sign_help_counts hard sign (gain >= 0.0, weighted);
  admission.py known-id/merge/retire_exemplar/retire_twin/
  bump_provenance all fold on fresh cards inside store.update /
  store.merge_retire; eviction.py module-level foreign_retention_veto
  shared by guard + gate; writer/config wiring
  min_effective_events=${memory.evidence.min_effective_events};
  prior.py _card_counts native split when task_local OR local.
  New regression tests pin each failure: interleaved second-store
  restamps survive merge/bump/readmit/twin-retire
  (test_transaction_regressions.py); veto invariant to magnitude/SE
  (1e±300, se 0 vs 1e300); context cohort excludes foreign metrics,
  global keeps hard sign. Full gate green (ruff + tests/memory
  tests/llm tests/integration, 2 known skips).
  Residual nit for re-verify pass: admit() known+harmful branch
  deletes on the submitted card's verdict without fresh revalidation —
  practically unreachable (exemplar re-admits evidence-free; insight
  admits are new-id).
- PR-15 (fix N2 — one write task): durable cross-process selection
  leases behind the existing config seam (config.yaml selection_leases
  _target_), sidecar under ${checkpoint_dir}, pid-liveness + TTL
  fallback expiry, fail-closed deletion checks.
  DONE + ACCEPTED (task-mrip66u9-3imjta). Verified line-by-line:
  SharedSelectionRegistry subclass syncs the owner-block JSON sidecar
  after every lease mutation (atomic tmp+os.replace under exclusive
  CardBankFileLock on sibling .lock); lock order bank-flock → registry
  RLock → sidecar-flock (innermost, no ABBA); is_leased/leased_ids
  union in-memory with live foreign owner blocks; is_leased fails
  CLOSED on unreadable sidecar (leased_ids fails open but has zero
  production consumers — test diagnostics only); every deletion
  decision (sweep/merge/retire_exemplar/retire_twin/known-id admit)
  checks fail-closed is_leased on the FRESH card inside the store
  transaction; same-host liveness exact via os.kill(pid,0)
  (PermissionError → live), foreign-host TTL fallback (7200 s),
  dead/expired owners pruned on every sync; lazy sidecar creation;
  strict owner schema validation; sync failures log-and-continue
  (local lease retained). config.yaml:24-27 default registry switched
  to SharedSelectionRegistry with path
  ${checkpoint_dir}/selection_leases.json (composition pinned by
  test_composed_config_instantiates_shared_selection_registry).
  Tests are real cross-process: forked child lease visible to a second
  registry; two gates on one LocalMemoryStore with sweep/merge blocked
  until release; dead-pid + expired-foreign pruning; corrupt-sidecar
  fail-closed + heal; write-failure local retention; atomicity stress.
  Full gate green (ruff + tests/memory tests/llm tests/integration
  tests/evolution). Accepted residuals: reverify-vs-foreign-delete
  instant window loses one credit event (logged by stats drop path);
  same-host pid-reuse could keep a stale lease alive until any sync
  prunes it first (narrow window, one-box deployment).
RE-VERIFY PASS (task-mriq6lhu-oc7ady, read-only, gpt-5.6-sol xhigh):
- N1, N3, N4, N5, N6: CLOSED (independent file:line verification +
  arithmetic spot-check: identical posterior for tiny/noisy vs
  huge/exact foreign gains).
- N2: PARTIALLY CLOSED — normal path correct, but two new HIGH defects
  in the PR-15 semantics (both traced to the orchestrator's own PR-15
  spec, which said "log-and-continue on write failure"):
  - R1 (HIGH): fail-open lease publication — _sync_locked swallows
    write failures (selection_leases.py:280,311), so acquisition
    returns a locally-held lease no foreign process can see; process B
    can delete the card process A is rendering with. Silent treatment
    degradation.
  - R2 (HIGH): corrupt-sidecar auto-heal erases foreign leases —
    on ValueError the next sync writes owners={} + own state
    (selection_leases.py:283-291), wiping live foreign owners'
    published leases; fail-closed reads only protect until the first
    "heal".
  - R3 (LOW, availability): same-host liveness is pid-only; a recycled
    pid keeps a stale lease alive indefinitely.
- NIT: PARTIALLY CLOSED — production-unreachable today (insight admits
  id="", exemplar re-admits evidence-free) but the public gate path is
  real: admit() judges harm on the SUBMITTED card and plain-deletes
  the known id (admission.py:254-264) — a concurrent restamp rescue is
  destroyed. Its own regression test exercises the branch.
- Overall re-verify verdict: NOT SAFE until R1/R2 (+ NIT hardening)
  land.
- PR-16 (fix R1, R2, R3, NIT — one write task): fail-closed lease
  publication (acquisition paths attach_cards /
  attach_cards_for_parent / reverify_cards roll back the attach delta
  and raise MemoryStorageError when the sidecar sync fails; blast
  radius = one aborted mutant attempt, verified at call sites
  provider.py:127 / mutant_task.py:90; transfer/release/abandon stay
  best-effort — they never add exposure); never write the sidecar when
  its read failed (no auto-heal; corrupt sidecar keeps deletions
  fail-closed until operator removes the file; documented recovery);
  owner blocks gain pid_start (/proc/<pid>/stat field 22) so same-host
  liveness is pid+start-identity; admit() known-id decide-delete-or-
  replace becomes one store.update fold judging harm on the
  fresh∪submitted evidence union.

PR-16 — DONE + ACCEPTED (2026-07-13). Verified line-by-line:
- R1: `_attach_locked` returns the exact delta set
  (selection_leases.py:163-171), `_rollback_attach_locked` is its
  inverse (:173-179); all three acquisition paths funnel through
  `_publish_acquisition_locked` (:310-319) which on sync failure rolls
  back every attached delta and raises MemoryStorageError. No path
  returns normally holding an unpublished lease. transfer/release/
  abandon go through `_sync_best_effort_locked` (:321-323) — stale
  entries only over-protect. Double-attach by two attempts of one
  process is safe: deltas are per-attempt-id and refcounted.
- R2: `_sync_locked` (:325-362) returns False on any owners-read
  failure other than FileNotFoundError and NEVER writes; corrupt bytes
  preserved on disk (test pins byte-for-byte); is_leased stays
  fail-closed; acquisitions raise. Auto-heal gone from code and tests.
- R3: owner blocks carry pid_start (validated int >= 0,
  :406-448); `_read_pid_start` parses /proc/<pid>/stat after the LAST
  ')' and takes post-comm index 19 = stat field 22 starttime (:31-44);
  `_owner_is_live` (:450-467): dead pid → dead, live pid + start
  mismatch → dead, pid_start 0 or unreadable /proc → conservative
  live. Foreign-host TTL branch unchanged.
- NIT: admit() known-id path is one store.update fold
  (admission.py:242-326): harm judged on merged card (submitted prose
  + fresh∪submitted gain_events/absorbed_ids); leased fresh kept
  (fail-closed is_leased inside the fold) with REJECTED_HARM
  leased-skip; delete only on fresh harmful verdict + tombstone;
  unknown-id path untouched. Regression tests pin both rescue
  (test_transaction_regressions.py:154) and still-harmful delete
  (:181) under interleaved second-store restamps.
- Lock order re-checked: acquisition = registry RLock → sidecar
  exclusive flock (innermost); eviction path = registry RLock →
  bank flock → RLock (reentrant) → sidecar shared flock (innermost).
  No inversion.
- Full gate: LINT_OK; tests/memory + tests/llm + tests/integration
  green. One failure in tests/evolution
  (TestLPTReducesMakespan::test_lpt_no_worse_for_uniform_programs) —
  wall-clock makespan assertion; ruled environment flake, NOT a
  regression: PR-16 diff is memory-only with zero import overlap with
  gigaevo/evolution/scheduling / dag_runner; same suite passed the
  PR-15 gate; on rerun the class passed in isolation then BOTH LPT
  tests failed in a file-level run (nondeterministic) with box load
  average 86-121 (reseed rerun + np2 live run saturating the host).
## Final consensus (2026-07-13)

Independent read-only re-check (gpt-5.6-sol xhigh, thread
019f59ed-ccee-7bc3-98d8-b1a4616becbe) confirmed R1, R2, R3 and the
admit() NIT all CLOSED with file:line evidence, found NO new defects
in the PR-16 diff (reentrancy, lock order registry → bank flock →
sidecar flock, owner-schema validation, base-registry single-process
behavior all clean), and issued the verdict:

**SAFE for multi-task, multi-process shared-bank deployment**, given
the documented accepted residuals.

Fix ladder PR-1..PR-16 complete: every finding from the adversarial
review rounds is either fixed+verified or explicitly accepted below.

Cross-task contract (user decision): foreign-task gain evidence is
BINARY sign-only (help iff finite gain >= 0.0, event-weighted), never
magnitude, never gain_se; native evidence keeps soft-count semantics.
Single source: sign_help_counts (context/evidence.py); consumers:
reputation foreign-posterior bump, eviction foreign_retention_veto.

Accepted residuals (documented, low-severity):
1. Reverify-vs-delete instant window: a card deleted between a
   mutant's lease release and credit logging loses one logged credit
   event (evidence under-count, never corruption).
2. Foreign-host liveness is TTL-coarse (7200 s): a crashed foreign
   run's leases over-protect its cards until the deadline lapses.
3. Same-host pid_start fallback: if /proc is unreadable or a
   recorded pid_start is 0, liveness falls back to pid-probe-only
   (conservative live — over-protection, never under-protection).
4. Aborted acquisition (sidecar publish failure) kills one mutant
   attempt; the dispatcher never awaits producer tasks, so the
   exception surfaces only via asyncio's unretrieved-exception log at
   GC — pre-existing engine pattern.
5. Corrupt sidecar = operator event: deletions freeze bank-wide and
   acquisitions raise until selection_leases.json (+ .lock) is
   removed after runs quiesce (docs/memory.md).

Status: ALL work uncommitted on branch memory-review-fixes, pending
user commit approval.

## Constraints (all PRs)

Match existing style; comments only one-line WHY; loguru + gigaevo/exceptions;
no hasattr dispatch; no absolute calibrated constants; no migration scripts;
surgical diffs — nothing beyond the findings. Tests via /run-tests
(tests/memory + tests/integration). Known issues explicitly OUT of scope:
usage id-mismatch, novelty pressure, p_help saturation, lineage-merge leak.
