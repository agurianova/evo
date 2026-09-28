# Idea-quality + machinery-integrity hourly loop — subagent spec

Read-only analysis apparatus for the live `memory=full` novelty A/B (R1/R2). Each hourly
tick dispatches TWO subagents against this spec: **A · idea quality** and **B · machinery
integrity**. Neither modifies, deletes, or signals any process. Favor signal over prose —
this runs every hour; report only current state + DEVIATIONS from expected.

## Runs & paths
- Root: `/home/jovyan/gigaevo/outputs/memory_rebuild_full_ab_novelty_2026-07-03`
- Runs: `R1` (PID 693967), `R2` (PID 693970). Storage `<run>/storage`, bank `<run>/memory`.
- Bank: `<run>/memory/cards.json` = `{"cards": {id: card}}`. `kind` ∈ {insight, program};
  ids `mem-*` = insight, `program-*` = program. Card fields: description,
  explanation_summary, keywords, gain_events (list), absorbed_ids.
- Events: `<run>/memory/memory_events.jsonl`; type is under key **`event`**.
- Ledger: `<run>/memory/write_ledger.jsonl`; row `outcome` ∈ {added,updated,merged,rejected_harm,evicted}.
  Novelty-gate rejections are **LOG-ONLY** (not in ledger): `grep "novelty gate rejected" <run>/launch.out`.
- Program pool: `<run>/storage/heilbron/programs/*.json`. Top-level: `code`, `metrics`,
  `lineage.parents`, `created_at`. `metadata.*` keys:
  `mutation_output` (dict; `.card_ids_used`, `.base_parent` 1-indexed, `.changes`, `.archetype`),
  `memory_base_selected_idea_ids`, `memory_base_id`, `memory_base_metrics` (dict; `.fitness`),
  `memory_injected_idea_ids`, `memory_lineage_applied_ids`, `memory_selected_idea_ids`.
- Fitness: **higher is better** (`gigaevo -r <run>/storage:<run> top -n K`; JSON list starts at first `[`).
- Env: python `/home/jovyan/.mlspace/envs/evo/bin/python3`, gigaevo `/home/jovyan/.mlspace/envs/evo/bin/gigaevo`.

## Code contracts (what "expected" means)
- **Credit rule** (stats.py): a card earns a gain event for a child iff
  `card ∈ base_selected_ids ∩ card_ids_used` — injected for the mutator's NAMED BASE parent
  AND self-declared used. Injection alone earns nothing. Credit = base-relative fitness delta
  (invalid child → one forced-harm event gain=0.0 invalid=True). Restamp is authoritative
  per sweep (rebuilds from the live pool).
- **Merge** (merge.py): survivor unions `gain_events` and records absorbed ids in
  `absorbed_ids`; restamp folds events attributed to `absorbed_ids` onto the survivor
  (since-merged ids re-alias, don't orphan). So merges re-home reputation, never drop it.
- **Novelty gate**: LLM judge on freshly-authored INSIGHT cards; rejects levers a strong
  optimizer LLM would reach for unprompted (novelty-vs-prior, NOT quality); program cards
  bypass; fails OPEN (logs `fail-open`, admits). On only in memory=full.

## Subagent A — IDEA QUALITY
For each run:
1. **Crispness.** Score every insight card CRISP / BORDERLINE / MUSHY (one-line reason):
   (a) specific actionable mechanism not vague; (b) exploits Heilbronn structure (min-area
   triplet, collinearity/degeneracy, boundary occupancy, signed area) vs a generic optimizer
   move (clamp/rejection-sample, hill-climb, grid-jitter, domain-aware step scaling,
   farthest-point) → generic = at best BORDERLINE; (c) portable (no hardcoded coords/N);
   (d) not tautological/trace/factoid; (e) distinct from siblings — flag redundancy CLUSTERS (ids).
2. **Reputation honesty (KEY — do NOT call 0-credit a "leak" without this check).** For each
   insight card with injections but 0/low credit, classify WHY, by reading child + base code:
   - Find children with the card in `memory_base_selected_idea_ids`. For each, check whether
     the card's mechanism appears in the child code AND in the base parent (`memory_base_id`) code.
   - **INHERITED** (mechanism in child AND base) → honest non-use; card redundant with its lineage.
   - **NOT-USED** (mechanism absent from child) → honest non-use.
   - **UNDER-REPORT** (mechanism in child, ABSENT in base, `card_ids_used` excludes it) →
     REAL gap — flag it. This is the only genuine reporting leak.
3. **Novelty gate sanity.** Count rejections + fail-opens (expect fail-open = 0). Sample 3-4
   recent reject reasons; confirm they cite novelty-vs-prior and are reasonable (generic move,
   not a structural lever). Flag any rejection of a genuinely Heilbronn-structural lever.
Output: per-run crispness table (id|verdict|reason|gains), redundancy clusters, reputation-honesty
verdicts for 0-credit cards, novelty-gate summary. End: counts crisp/borderline/mushy + any DEVIATION.

## Subagent B — MACHINERY INTEGRITY (expected vs observed, PASS / DEVIATION per stage)
For each run, from events + ledger + pool:
1. **Infra.** PID alive (`/proc/<pid>/cmdline` contains `..._novelty_2026-07-03/<run>`); recent
   llm_io `error` fields None; no NEW `APIConnectionError`/refused/timeout in `evolution_*.log`
   (exclude benign `[DagScheduler] Cleaned up N finished + 0 timed out` and `ParentRefresher …
   timed out waiting`). Program count `find <run>/storage/heilbron/programs -name '*.json' | wc -l`
   + `gigaevo top -n 1`. Flag ≥245 (k=245 A/D comparison, bars A 0.0294 / D 0.0289).
2. **Authoring→gate→admit.** Ledger outcome counts by kind; novelty rejects (log). PASS = cards
   being authored + admitted; DEVIATION = fail-open > 0, or admits collapse to ~0 while authoring continues.
3. **Consolidation/merge.** merged-count; spot-check ONE current survivor with non-empty
   `absorbed_ids` — its `gain_events` should include events plausibly from absorbed ids (union
   invariant). DEVIATION = a survivor lost its absorbed ids' events.
4. **Retrieval.** READ_SELECTION `empty_reason` distribution (`research_empty` vs `auction_rejected`).
   Expected: research_empty share DECLINES as the bank grows. DEVIATION = ~100% research_empty with a non-empty bank.
5. **Auction.** From AUCTION_RUN: per-insight-card win-rate spread; cold cards (posterior_a=b=1)
   still win sometimes. DEVIATION = one card monopolizes all wins, or all cards abstain despite candidates.
6. **Injection→credit.** Over the pool: %children with ≥1 base-injected card, %declaring any used,
   %credited (base∩used). Baseline this session: ~40% declare, ~20-25% credited, ~44% of injected
   instances credited. DEVIATION = credit-rate crashes toward 0.
7. **Restamp.** GAIN_RESTAMP passes present and growing; credited card set non-empty. DEVIATION = 0 passes after cards banked + children evaluated.
Output: per-run PASS/DEVIATION table for stages 1-7, one line each, with the observed number.

## Escalation (Telegram, parse_mode="", sparingly — user may be away)
Send ONLY on: any DEVIATION in B; a genuine UNDER-REPORT or structural-lever rejection in A;
a k=245 crossing; or a run death/error. Otherwise append a dated tick to `04_issues_log.md` and stay silent.
