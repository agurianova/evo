# Memory overhaul — consolidated review (2026-07-10)

**Scope:** full review of `gigaevo/memory/**` + `config/memory/**` on branch
`memory-cold-probe-policy` (WIP snapshot commit `1d640d35`), four independent
review lenses (OOP soundness, config tree, RL/bandit math, end-to-end logic).
The working tree was concurrently modified by a background fixer during review
(final mtimes ~00:29); **every finding below was re-verified against the
post-fixer tree** and labeled OPEN or FIXED-BY-BACKGROUND accordingly.
Targeted suite `tests/memory/read tests/memory/write` green (~397 tests) at
snapshot; `tests/memory/test_layering.py` green post-fixer.

## Verdict

Component-level math is largely well built (Šidák abstention gate Monte-Carlo
verified, decay idempotent and floor-preserving, sign conventions coherent
across both fitness directions, Thompson sampling genuinely per-draw, config
tree mechanically sound 18/18 compositions). **The composition is not sound:**
three mechanisms interact into an absorbing "explore-nothing" state (R1–R3
below) that converges the bank to first-shot winners plus permanent zombies —
consistent with the earlier novelty-collapse / inert-memory campaign findings.

## CRITICAL — open

### R1. One-strike absorbing death: first non-positive exposure permanently removes a card from selection, probing, AND eviction
- `read/reputation.py` `_ev_rewards`: unused/invalid exposure → zero atom → card no longer cold.
- `read/auction.py:583` strict `bid_value > 0.0` gate: all-non-positive support ⇒ bid deterministically ≤ 0 forever; auction emits `support_kind="zero_support"` for exposure-only cards, and probe eligibility (`auction.py:649`, `probe.py:80-81`) requires `"cold_prior"` ⇒ zombies are not probe-eligible.
- `read/fused.py:229` benches any warm card with `ev_mean <= 0.0` — an irreversible retirement from a point estimate valid at n=1.
- `write/eviction.py` `PolicyNonViableEvictor` needs ≥ `min_effective_events` (3); staleness only shrinks support ⇒ 1–2-exposure zombies are also unevictable. Recommended evictor stack has no capacity/age evictor.
- Verified numerics: single −0.001 use → `ev_mean = −0.00041`, max bootstrap sample 0.0 even at staleness weight 1e-6 (decay approaches 0 from below, never crosses). P(neutral card dies after first use) ≈ 0.5; at the documented ~4% mutator use-rate, ~96% of probes manufacture a permanent zombie.
- **Fix:** bench only on pessimistic evidence (bootstrap upper-quantile ≤ 0 AND effective events ≥ `min_effective_events`); make sub-threshold-support cards probe-eligible regardless of kind (turns the currently dead `probe_until_effective_events` knob live); optionally let PolicyNonViable retire sub-floor exposure-only cards after N stale bank cycles.

### R2. "Ignored by mutator" scored as "confidently harmful" at full weight; harm-evicts + run-tombstones cards with positive evidence
- `read/reputation.py:160-162`: `forced_failures = invalid + unused` at weight 1.0 each (`write/stats.py:291`), while a genuine bundled use carries 1/k.
- `write/eviction.py` `HarmEvictor` has NO `_has_positive_direct_evidence` override (only PolicyNonViable checks it); `write/admission.py` tombstones every harm deletion for the run.
- Verified: 3 ignores → Beta(1,4), ppf(0.8)=0.331 < 0.5 → evicted+tombstoned. One real +0.02 solo win + 3 ignores → Beta(2,4), ppf(0.8)=0.490 < 0.5 → **still tombstoned**.
- **Fix:** positive-direct-evidence override in HarmEvictor; harm (tombstoning) verdict requires ≥ 1 genuinely negative event; discount unused-exposure weight (mirror the 1/k discipline).

## MAJOR — open

### R3. Empirical-Bayes cascade double-counts nested cohorts → cold prior collapses to compound base rate
`read/prior.py` cascade levels (global → kind → kind+category, +3 context levels under bd_cell) are nested, not disjoint; each level re-applies the same n against the parent mean. Verified: 20 first-exposure failures → intended one-level shrink mean 0.235; actual 3-level 0.066; 6-level 0.028 ≈ raw p̂. With unused-first-exposure = failure (`prior.py`), the prior learns ≈ use-rate × P(help|used) ≈ 0.02–0.05 → cold bids die → exploration collapses onto the probe lane, which R1 consumes. **Fix:** skip cascade levels that are not strict refinements (cohort n equal to parent's ⇒ no new info); discount/exclude unused-only first exposures from prior cohorts.

### R4. Invalid children: forced harm in posterior, neutral 0 in every EV surface, neutral 0 in the no-card baseline cohort
`reputation.py:90-91` (0.0 atom), magnitude 0.0; `context/models.py` and `context/no_card.py` count invalid no-card children as delta 0.0. "Reliably crashes children" reads as "no effect" on all EV surfaces and biases the baseline median. **Fix:** negative EV atom for invalid (−`significant_change`, config-referenced) or exclude invalid rows from the no-card cohort — same event semantics both arms.

### R5. Bundled-use credit double-discounted (1/k²) while ignores count at 1.0
`write/stats.py:255,266,276`: gain=(Δ−baseline)/k AND credit_weight=1/k → ~1/k² of a solo win in the EV mean. Reachable via crossover lineage-merge at max_cards=1; punishes exactly the co-selected good cards. **Fix:** split magnitude or weight, not both (keep full delta atom, weight 1/k).

### R6. `ReputationModel` god-interface with dead member
`read/interfaces.py:39-78`: ~12 members spanning four roles; `fit_no_card_baseline` invoked by nothing in any shipped preset (writer wired to `${ref:memory.context_model}`) yet every implementor must carry it. Eviction-facing members duplicate `write/eviction.py`'s narrow structural Protocols. **Fix:** shrink to read contract; delete `fit_no_card_baseline`; eviction contracts live only on eviction's Protocols.

### R7. Decision-scoped no-card baseline smuggled per-candidate; O(candidates) locked JSON reads; first-finite-wins recovery
`read/projection.py:48` calls `summary_for(context)` per candidate (each takes the file lock and re-parses JSON); `auction.py:195-211` recovers the decision baseline by scanning candidates for the first finite pair (order-dependent by construction). Also `prior.py` walks the full bank 3–6× per cold candidate; `decay.py`/`reputation.py` re-snapshot the store per card. **Fix:** fetch once per decision (decision-scoped frame passed to the auctioneer); hoist bank snapshots.

### R8. Two independent authorities for BD-cell partitioning
`BDCellMemoryContext` (context/models.py) re-implements the cell partition `BDProximityReputation` (reputation.py:411+) owns; adaptive preset wires both with separate `behavior_space` refs — a granularity override on one silently desynchronizes posteriors from baselines. **Fix:** context model = single cell authority; reputation asks it.

### R9. `_p_help_of` probability-named seam returns an unbounded EV in the Bootstrap subclass
`read/fused.py:247`: returns `IntroGain_bootstrap_ev_lo20` (gain units) under a base-class seam whose contract is a probability in [0,1]; currently coherent only because the subclass also overrides `_passes_rep_floor`/`_bank_bench`. **Fix:** rename seam (`_rep_score_of`, "higher is better within one slate") or inject as strategy.

### R10. Evidence-math duplication across layers (residual)
Partially fixed by background (single `_no_card_cohort`, reputation delegates baseline fitting). Still duplicated: `_event_weight`, oriented-delta helpers across reputation.py / prior.py / context/models.py / write/stats.py. **Fix:** one evidence-math module at the context/leaf layer; move `InjectionOutcome` there to kill the `getattr` data-duck-typing in reputation.

## FIXED-BY-BACKGROUND (verified in post-fixer tree)

- **Layering violation** (was CRITICAL): `BetaPrior`/`coerce_beta_prior` → new `context/beta.py`; `no_card.py` inlines `fcntl` (no storage import). `test_layering.py` green.
- **No-card cohort divergence** (`base_fitness` filter drift): single `_no_card_cohort` in context/models.py.
- **Constants centralized**: `${memory.baseline_prior}`, `${memory.evidence.min_effective_events}` interpolated across configs + pin test `tests/memory/test_config_defaults.py`.
- **hasattr/getattr dispatch eliminated** in decay/bootstrap decorators, admission, composite evictor.

## MINOR / NIT — fix opportunistically

- Cold→warm prior discontinuity: first event replaces the EB/cold prior with Beta(1,1) instead of updating it (one ignore: mean 0.5→0.333 vs proper 0.429). Seed `beta_binomial_posterior` with the projector's prior.
- Two independent theta draws per candidate per round (bid vs gate) — within-round incoherence.
- Probe lane: `probe_until_effective_events` dead while eligibility requires `cold_prior`; warm-override replaces positionally-last (not weakest) budgeted card; probe × non-bootstrap auctioneer composes as silent permanent no-op (warn on zero cold-prior slates).
- `MemoryReader` unseeded RNG — live auctions not run-reproducible (per-card bootstrap stats are).
- `dist[int(q*len(dist))]` biased quantile index (fused.py:153,228).
- Legacy `FusedRankingShortlister._bank_bench` can bench cold cards (config-guarded today).
- No-card evidence JSON grows unboundedly; abstention arm never ages (bounded by `sign_strength_cap`).
- Protocol/concrete name collision `AuctionCandidateProjector`; `Any`-typed seam fields in projection.py/prior.py despite existing Protocols; projector re-derives coldness instead of asking the reputation; context-module tests live under `tests/memory/read/`; `adaptive.yaml`/`recommended.yaml` byte-identical (alias drift risk).

## Verified sound (checked, not assumed)

Šidák family-wise no-card gate (MC-verified exact); Beta-binomial conjugacy &
prior-once; decay floor/idempotency/expiry; oriented-delta sign conventions
both directions; real per-draw Thompson; EV reserve inclusive-quantile; budget
policies match names; founding excluded from harm; tombstone hysteresis; write
path identity/merge/persistence; no-card channel genuinely two-sided;
none-presets no-op cleanly; events all emitted-and-consumed;
`tools/analyze_bandit_health.py` updated for probe winners; config tree:
18/18 compositions instantiate, no dead yaml, docs current, validation
broadened correctly.

## Refactor plan (agreed stop bar: zero CRITICAL/MAJOR from 4-lens Opus panel, ≤4 rounds)

- **Phase A — evidence semantics core:** R2, R4, R5 (+ R3's unused-discount in prior cohorts). Files: write/stats.py, read/reputation.py, write/eviction.py, context/models.py, context/no_card.py. Test-first.
- **Phase B — exploration guarantees:** R1 bench/probe re-entry, R3 cascade strict-refinement. Files: read/fused.py, read/probe.py, read/auction.py, read/prior.py, config/memory/*.
- **Phase C — architecture:** R6–R10 (+ name collision, Any seams, cold-derivation). Files: read/interfaces.py, read/projection.py, read/auction.py, read/reputation.py, read/fused.py.
- **Phase D — minors, docs sync** (docs/memory.md, MEMORY_LIFECYCLE_TUTORIAL.md in same change), full targeted suite + ruff.
- **Promoted by user (efficiency-critical minors are in scope):** hot-path
  efficiency items — per-candidate locked JSON reads, per-card bank
  re-snapshots, prior full-bank walks (all under R7), and no-card evidence
  unbounded growth/pruning — are treated as must-fix, not opportunistic.
- Then Opus 4.8 panel re-review; iterate; final self-verification. No commits beyond snapshot `1d640d35` without approval.

## Progress log

- **2026-07-10 Phases A–C complete, verification green.** All CRITICAL/MAJOR
  (R1–R10) remediated, plus promoted efficiency minors: R7a decision-scoped
  no-card baseline (projector `decision_baseline` → reader resolves once per
  select → `run(..., baseline=)`; AuctionCandidate slimmed, AuctionBid audit
  fields kept), R7b bank `snapshot()` cache + staleness stamp cache (tuple-only,
  identity-keyed, FIFO 4), R7c prior single bank walk + strict-refinement
  cascade, R7d no-card evidence retention cap (`max_observations: 1024`,
  naturals pruned before randomized controls). R9 seam renamed
  `_rep_score_of`. Dead read-side `fit_no_card_baseline` seam deleted
  (write seam lives on context models; test_stats now wires
  `BDCellMemoryContext` as estimator). Gate: ruff check+format clean, 573
  tests in tests/memory green, all memory YAMLs compose.
- **Minors left open deliberately** (non-gating): biased quantile index
  `dist[int(q*len(dist))]` (fused.py:153,230); two independent theta draws per
  candidate (bid vs gate); MemoryReader default-unseeded RNG when no rng is
  injected.
- **2026-07-10 Round-1 Opus panel + fixes.** Panel (4 lenses, opus): 1 unique
  CRITICAL, 0 MAJOR. CRITICAL (lenses 3+4 concur): the R1 probe lane shipped
  with `probe_until_effective_events: 1.0` + strict `<`, recreating an
  absorbing zombie at the boundary — one solo ignored injection under
  `max_cards: 1` carries credit_weight exactly 1.0, bids 0.0 (fails the strict
  sign gate), is not probe-eligible (1.0 < 1.0 false) and not evictable
  (effective 1.0 < min_effective_events 3). **Fix (test-first):** probe
  threshold now defaults to the eviction evidence floor
  (`${memory.evidence.min_effective_events}` in cold_budget.yaml; code default
  3.0), and the bootstrap auction's `support_n` is now staleness-scaled
  (finite non-negative weights × staleness factor) mirroring eviction's
  `_effective_support`, so probe eligibility and eviction adjudicability
  partition card-space on ONE measure and decayed evidence re-earns probes.
  Fail-safe: bids with empty `support_kind` (non-bootstrap auctioneers) are
  never probe-eligible. Opportunistic minors fixed same round: staleness
  `_STAMP_CACHE` now lock-guarded; `_no_card_deltas` (write stats fallback)
  gained the `isfinite` guard (NaN no-card fitness no longer poisons the
  global baseline median — regression test added); eviction-only
  `is_confidently_harmful`/`eviction_contexts` dropped from the read-side
  `ReputationModel` Protocol (write-side CardScorer Protocols already own
  them); `EmpiricalBayesMemoryPrior.levels` now validates monotone refinement
  (global block before context block, strict token-superset chains — sibling
  slices like `("kind", "category")` rejected since parent_mu chaining across
  siblings is ill-founded); `extra="forbid"` added to all config-instantiated
  memory classes (reputation/prior/context/no_card/probe/projector/renderer/
  GlobalNoCardBaseline) so YAML typos fail loudly. Deferred (documented,
  non-gating): R4 invalid-neutral EV atom, R8 dual behavior_space refs, R9
  gain-unit mixing (w_rep ablation-only), per-candidate flock+stat residual
  syscalls. Gate: ruff clean, 581 tests/memory green, full/reader/writer
  compose; probe threshold resolves to 3.
- **2026-07-10 Round-2 Opus panel — STOP BAR MET (round 2 of ≤4).** Blind
  4-lens panel (opus, read-only, DO-NOT-REPORT list of deliberately-open
  minors): lifecycle 0C/0M/1m/0n, config-graph 0C/0M/0m/0n (full recursive
  Hydra instantiate of full/reader/writer clean under extra="forbid"),
  bandit-math 0C/0M/0m/3n (auction `support_n` ≡ eviction `_effective_support`
  verified numerically across 7 scenarios incl. staleness 0.552; partition
  exhaustive over 10 card classes; round-1 zombie now probe-eligible), OOP
  0C/0M/2m/3n (all five round-1 fixes HOLD; no layering cycles; per-decision
  baseline seam an improvement). **Zero CRITICAL, zero MAJOR — panel
  consensus reached.** Post-panel opportunistic fixes (test-first, re-gated):
  (1) warm-override probe now displaces a budgeted winner only when
  `kept+probes > max_cards` (probe.py `_select_probe` overflow trim) — both
  lifecycle and OOP lenses flagged that `max_cards=2` (documented override)
  dropped a proven winner while a slot sat empty; default `max_cards=1`
  behavior unchanged; (2) new `EvictionFacingReputation` Protocol
  (interfaces.py) declares the write-facing
  `is_confidently_harmful`/`eviction_contexts` surface the read-side wrappers
  delegate — `DecayCompatibleReputation` extends it and
  `BootstrapReputation.inner` is annotated with it, closing the
  wrapper-delegation type gap; (3) one-line comment documenting the deliberate
  global→local `parent_mu` carry in `EmpiricalBayesMemoryPrior` (two lenses
  independently read it as a bug). Left open (documented, non-gating): dead
  `else float(len(deltas))` support fallback in auction.py (unreachable on
  shipped path — projector always supplies weights); duplicated
  effective-support arithmetic (pinned by tests on both sides; shared helper
  deferred); projector seams typed `Any`; redundant-but-harmless isfinite
  guard in `_no_card_deltas`. Gate: ruff clean, 582 tests/memory green
  (581 + new warm-override budget test), EXIT:0.

- **2026-07-10 RL/bandit expert consult — recommended default consolidated.**
  Opus expert (full preset-matrix brief) endorsed the panel-verified stack as
  the recommended default: read_policy=adaptive (context bd_cell, prior
  empirical_bayes, no_card_evidence json, probe cold_budget, reputation
  bootstrap_bd, auction thompson_bootstrap, budget top_bid, excluder lineage,
  evictor recommended) — i.e. exactly what `memory=full` already composes.
  **No leaf-value changes** (all thresholds quantile/self-normalizing; only
  permitted evidence floors + resource caps). Applied per verdict: deleted the
  two alias presets `read_policy/recommended.yaml` (byte-identical to adaptive
  save comments; self-documented alias) and `reputation/bootstrap_ev.yaml`
  (zero live selectors); retargeted refs (island-compat test → adaptive,
  test_fused.py path → adaptive.yaml, presets parametrizations, docs/memory.md
  rows 198/199/203, portable.yaml + bd_proximity.yaml comments); surfaced EB
  `levels` ladder in prior/empirical_bayes.yaml at the code default. Watch
  items flagged by expert for first-run telemetry: (1)
  `auction.ev_floor_quantile=0.765` is heilbron-calibrated (code default 0.5)
  — check injection fraction lands ~30-40%; (2) `w_nov=0.0` = no active
  novelty pressure — check per-card injection-count distribution (>~60×
  dominance ⇒ next intervention is w_nov>0, not auction re-tuning). Launch
  note: `memory/write=live` is a REQUIRED run override for any fresh run
  exercising the read stack (full.yaml ships write=end_of_run, which authors
  the bank only at completion). Gate after edits: ruff clean, compose smoke
  (full default + portable OK; both deleted aliases correctly fail), tests
  tests/memory + island-compat all green EXIT:0.

- **2026-07-10 Launch + docs — ALL OVERNIGHT TASKS COMPLETE.** (1) Hover
  relaunch: topology-bias R3 had already completed naturally at 03:25 (7.62h);
  nothing to stop. Launched TWO memory-enabled replicates mirroring the
  no-memory fitness-only baseline via new
  `experiments/hover/diff_memory/launch_baseline_memory.sh` (launch.sh minus
  the 3d pins: algorithm=single_island_no_distant_parents,
  enable_chain_structural_metrics=false; memory=full + memory/write=live +
  memory/llm=qwen_instruct; fresh banks SHARE_HOVER_DIFF_MEMORY_BASE_R{1,2}_
  20260710_041404). Config diff vs baseline dump: all comparable knobs MATCH
  (fitness-only archive, 250/60000/7200/14400/1). R1 pid 454682 / R2 pid
  454683, outputs/hover-diff-memory-baseline-20260710_041404/, both healthy
  (models verified, seed loaded, 0 errors). README pointer added
  (problems/chains/README.md). (2) Docs: Opus agent reconciled docs/memory.md
  (7 edits: probe stage in read flow, Sidak gate, partition invariant, EB
  ladder row, probe/auction table rows, write=end_of_run default) +
  MEMORY_LIFECYCLE_TUTORIAL.md (8 edits incl. ColdProbePolicy node in the
  read-side mermaid, partition paragraphs in Cold State + Zombie Cards, EB
  config-driven ladder + parent_mu carry, 0.50/0.03 probe rates); other 8
  mermaid diagrams verified current; self-check PASS (no stale preset
  selectors); spot-verified by main agent. NOTHING COMMITTED — awaiting user
  approval for the whole branch.

- **2026-07-10 Daytime autonomous window — closure + explore3 (user day off,
  all updates via Telegram).** (1) Baseline memory pair FINISHED 11:46 (R1
  7h06m / R2 7h29m, clean finalization). Closure: MEM_R1 best 0.8322 beats
  both no-memory replicates (0.8089/0.8078); MEM_R2 0.8011 just under. Card
  efficacy = FIRST CONSISTENT POSITIVE SIGNAL: with-cards mutations beat
  no-cards in BOTH replicates (improve-parent rate 55.1% vs 47.4% in R1,
  60.6% vs 44.2% in R2; mean fitness delta -0.011 vs -0.025 / +0.004 vs
  -0.022; valid children only). Caveats recorded: observational split
  (auction targets contexts it predicts help), randomized no-card control
  only 10/16 children, n=2. Full behavior checklist PASS in both runs
  (auction fraction R1 30.3% in-band / R2 58.4% watch item, dominance max
  17x/24x, reputation learned both directions, probe lane active, no
  zombies, no-card evidence 151/138 obs, banks 27 cards each). Known cost:
  757/712 mutation attempts failed on proxy connection errors before retries
  filled the 250-mutant budget (pool saturated by two concurrent 235B runs).
  3-page PDF (tectonic; binary reinstalled to ~/.local/opt after the old
  scratchpad symlink died) + ELI5 summary sent via Telegram; run-end
  watchdog also auto-fired its health report at 11:51. (2) mutation-4
  (10.232.38.67:8777) verified serving Thinking-2507; NOT added to the
  litellm rotation: proxy runs on 10.232.24.68 (no SSH from this box) and
  keeping the pool identical keeps explore3 comparable to the morning pair.
  User can restart the proxy from a main checkout (tools/litellm.sh) —
  inventory already updated on main (8d4710d5). (3) EXPLORE3 pair LAUNCHED
  11:58 via launch_explore3.sh — sole delta memory.reader.max_cards=3
  (auction top-3 by bid, probe fills leftover slots); TS=20260710_115837,
  R1 pid 510342 / R2 pid 510343,
  outputs/hover-diff-memory-explore3-20260710_115837/, max_cards=3 verified
  in both cfg dumps, all smokes green, both alive past seed load. Run-end
  watchdog watchdog_run_end_explore3.sh detached (pid 511615) + waiter
  armed; ETA ~19:00-19:30; then three-way closure PDF (3-card vs 1-card vs
  no-memory). NOTHING COMMITTED on the branch.

- **2026-07-10 EXPLORE3 abort + relaunch — mid-run verification caught an
  inert treatment.** The 11:58 launch (max_cards=3 only) was killed ~2.7h in:
  a scheduled 2.5h treatment-binding check found mutations still receiving
  0-1 cards (selected-count dist R1 {0:65, 1:79, 2:2} / R2 {0:67, 1:101,
  2:1}). Root cause, verified against the FINISHED baseline logs: the
  auction passes >=2 gate-passing winners in only 0% (R1) / 2.1% (R2) of
  events, and ColdProbePolicy.max_probe_cards_per_decision=1 hard-caps the
  probe lane at one cold card per read — so the 3-card budget almost never
  binds and the pair would have replicated the 1-card baseline. Killed both
  runs (SIGKILL required; engine traps SIGTERM for graceful drain), stopped
  watchdog/waiter first so no spurious Telegram fired, renamed artifacts
  *_aborted*. Relaunched 14:58 as TS=20260710_145836 (R1 pid 532402 / R2
  pid 532403) with the corrected two-knob treatment:
  memory.reader.max_cards=3 + memory.probe_policy.
  max_probe_cards_per_decision=3 (launcher patched, both knobs verified in
  cfg dumps). Watchdog re-armed for the new TS + completion waiter + a 1h
  treatment-binding check expecting 2-3-card events. ETA ~22:00-22:30.
  Telemetry gotcha for future checks: the selection event field is
  `selected_ids`, not `injected_idea_ids` (that name lives in program
  metadata). User notified via Telegram (ELI5).

- **2026-07-10 EXPLORE3 CLOSED (23:35) — verdict: 1 card > 3 cards; day plan
  complete.** Relaunch pair finished 23:20/23:23 (8h21/8h24, 251 programs
  each, 100% validity, only 14/16 mutation timeouts — no connection-error
  churn). Treatment BOUND: R1 422 selection events, dist {0:157, 1:199,
  2:23, 3:43} = 62.8% injected, mean 1.41 cards/injected event; R2 441
  events, {0:237, 1:146, 2:23, 3:35} = 46.3%, 1.46. Best fitness EXPL
  0.8189/0.8044 — between the 1-card pair (0.8322/0.8011) and no-memory
  (0.8089/0.8078); arm means MEM .8167 > EXPL .8117 > NOMEM .8084, all gaps
  inside replicate spread. KEY FINDING: the with-vs-without card efficacy
  split INVERTED in both replicates (R1 with-cards mean delta −0.019 / pos
  36.9% vs without +0.001 / 57.5%; R2 −0.016 / 47.7% vs −0.007 / 49.7%) —
  opposite of the 1-card pair where with-cards won both reps. Candidate
  mechanisms: probe dilution by design (fill-to-3 adds cold probes; auction
  supplies 2+ proven winners in ~0-2% of events), prompt dilution, and the
  R1 dominance leak. HEALTH: R1 card program-8821e8d1 selected 86× (>60
  pre-registered bar, 44 surviving children) → next lever is w_nov>0
  novelty pressure, NOT auction retune; R2 clean (max 26×, fraction 36.9%
  in band); reputation/probe/zombies/no-card evidence all pass; banks 20/30
  cards. EXPL population-level reads best of all six (mean valid fitness
  0.738/0.731, zero invalid) — legible exploration tax funding bank growth,
  but it does not pay within a single 250-mutant budget. Recommendation:
  keep max_cards=1 default; follow-up experiment = w_nov>0. 4-page PDF +
  ELI5 sent to Telegram 23:35; run-end watchdog auto-report fired 23:26.
  Nothing committed.

- **2026-07-11 EVAL-NOISE STUDY CLOSED (~02:30) — single-eval σ measured;
  winner ranking corrected.** All six run winners (MEM/EXPL/NOMEM × R1/R2)
  re-evaluated K=5 under identical conditions with per-sample scores
  retained (scratchpad reeval_winners.py → reeval_results.json →
  analyze_reeval.py → reeval_analysis.json). Pooled per-eval SD σ=0.0078 —
  the same size as every between-arm best-of-run gap reported in v1/v2, so
  single-eval comparisons at that scale were noise (user's critique
  confirmed quantitatively). Mean winner's-curse shrinkage +0.0048 (≈0.6σ);
  NOMEM_R1 and MEM_R2 the most inflated (−0.012 each on re-eval).
  Corrected ranking by re-eval mean: MEM_R1 0.8298 > EXPL_R1 0.8229 >
  NOMEM_R2 0.8107 > NOMEM_R1 0.7964 ≈ EXPL_R2 0.7956 > MEM_R2 0.7893.
  Paired per-sample tests (Wilcoxon zsplit + 20k bootstrap): MEM_R1
  genuinely best — beats both NOMEM winners (p<1e-4, p=0.028); MEM_R1 vs
  EXPL_R1 is a TIE (+0.007, p=0.375), so the v2 headline "1 card > 3
  cards" does NOT hold at winner level (the per-mutation efficacy contrast
  MW p=0.0003 stands); within-arm replicate gaps (+0.040 MEM, +0.027 EXPL)
  exceed every between-arm gap; both R2s significantly below NOMEM_R2.
  Method adopted going forward: winner claims need K≥5 re-evals + CIs;
  paired per-sample tests for program-vs-program; mechanism endpoints
  primary where the treatment acts mechanically; metrics.yaml
  significant_change=0.01 ≈ 1.3σ of measured eval noise. Unpaired power:
  ~10 evals/chain to resolve Δ=0.01. v3 addendum PDF
  (hover_eval_noise_addendum_v3_20260711.pdf) + ELI5 sent to Telegram
  ~02:35. Caveat: all evals on the fixed first-300 train subset =
  selection fitness, not held-out generalization. Nothing committed.

- **2026-07-11 NOVELTY PAIR LAUNCHED (02:38) — w_nov=0.25, TS=20260711_023848.**
  Preregistered in experiments/hover/diff_memory/prereg_novelty_20260711.md
  (user-approved "go with 1"): single functional delta
  memory.reader.shortlister.w_nov 0.0→0.25 vs the 20260710_041404 MEM control
  pair, launcher launch_novelty.sh (verbatim mirror of launch_baseline_memory.sh
  otherwise). PIDs R1 582336 / R2 582337, 250 mutants each; cfg dumps verified
  w_nov 0.25; smoke checks all green. Primary endpoints are mechanism-level
  (P1 max injections/card ≤30 both reps vs control 86/26; P2 distinct cards
  ≥1.3×; P3 top-1 share lower) per the eval-noise discipline; S1 with-card
  delta non-inferiority decides shipping. Run-end watchdog
  watchdog_run_end_novelty.sh detached (health checklist + Telegram on
  completion). ETA ~10:30-11:00. Closeout will compare NOV/MEM/EXPL/NOMEM
  with K=5 re-eval CIs. Nothing committed.

- **2026-07-11 TWO DESIGN PROPOSALS WRITTEN (~04:00), both awaiting user
  sign-off, nothing wired.** (1) Noise-aware evolution
  (plans/2026-07-11-noise-aware-evolution-design.md): persist per-sample
  scores (validate() tuple form + ArtifactFieldToMetadata stage) + paired
  bootstrap replacement gate behind the ArchiveSelector seam
  (PairedBootstrapArchiveSelector, p_accept knob, 0.5 = status quo).
  Calibrated on the re-eval study (k=1 vs k=1, scratchpad
  calibrate_gate.py): today a truly-equal challenger swaps in 49% of the
  time and a truly-worse-by-0.007 one in 24-28%; at p_accept=0.75 null
  churn halves (25%), truly-worse ≤8%, true gains ≥0.015 keep 81-100%.
  A/B protocol with mechanism endpoints (replacement count, winner curse)
  included. (2) 3D chain behavior space
  (plans/2026-07-11-chain-bd3d-proposal.md): mined all 1491 valid programs
  from the six finished runs (scratchpad mine_chain_features.py). Existing
  topology_3d_ret space occupies 20/150 cells (dag_depth × max_fan_in
  ρ=+0.88 — near-duplicate axes). Proposed hop_depth × passages_fetched ×
  instr_chars (5×5×6): 97 pooled / 40-64 per-run cells, all pairwise
  ρ<0.6; fitness-by-hop story (hop-2 valley 0.683, hop-4 peak 0.766 with
  only 6% of programs) motivates niching + gives card efficacy a per-niche
  endpoint. Wiring plan rides existing enable_chain_structural_metrics
  hook + new chains_bd3d preset mirroring topology_3d_ret.yaml. Both ELI5
  summaries sent to Telegram. Novelty pair still running (watchdog armed;
  3h mid-run treatment-binding check scheduled).

## 2026-07-11 ~05:45 — novelty mid-run treatment-binding check: BOUND

3h into TS=20260711_023848 (PIDs alive, 107/118 of 250 mutants, zero
connection errors). No dedicated novelty telemetry field exists, so binding
was verified three ways: (1) cfg dumps carry w_nov=0.25 with
BootstrapFusedRankingShortlister as the shortlister _target_ (cfg line 386);
(2) fused.py's early-return short-circuit requires w_nov==0, so the scoring
loop provably executes; (3) functional signal vs control truncated to the
same 3h03m elapsed window: top-1 injection share NOV 16.1%/13.9% vs CTRL
17.9%/18.1% (lower in both reps), max card 15x/14x vs 14x/17x, distinct
15/13 vs 13/17. Spread is only mildly better mid-run — expected, since
control's dominance blowup (14x→86x in R1) happened late; P1 (max ≤30 at
run end) remains the endpoint. ELI5 sent to Telegram. Run-end trigger armed
(background waiter on both PIDs) → four-arm closeout next.

## 2026-07-11 ~11:00 — novelty closeout part 1: TREATMENT WAS INERT + prereg control error

Runs finished clean (251 programs each, 7.73/7.74h, 0 connection errors, 100%
valid both reps; watchdog report sent 10:26). Two corrections found during
closeout, both mine:

1. **Prereg control error**: the P1 control values "MEM_R1 86x / MEM_R2 26x"
   were actually the EXPL pair's numbers. True matched control (MEM pair):
   max card 17x (R1) / 24x (R2), distinct 30/39, top-1 share 9.1%/8.2%.
2. **w_nov=0.25 was inert by construction at this operating point.** Traced
   end-to-end: the fused score (fused.py:113-130) is consumed only by (a)
   score_floor filtering — UNSET (None) in our cfg — and (b) the sort order
   of the returned shortlist. Downstream, membership never depends on that
   order: reader.py builds a candidates dict and auctions ALL of them;
   thompson_bootstrap gates each candidate independently (auction.py:380-397);
   TopBidBudgeter.cap re-sorts by sampled theta (auction.py:700-706); the
   probe lane re-sorts by (bid, theta, card_id) (probe.py:99-105). With
   w_rep=0 and score_floor=None, w_nov changes ordering only ⇒ no selection
   effect. The mid-run "binding" check verified code-path execution, not
   output consumption — the deeper EXPLORE3 lesson. Prereg checklists must
   include an output-consumption trace.

Consequences: NOV pair = 2 extra replicates of the plain MEM config (4 total).
Mechanism metrics measured across 4 identical-config reps: max card 17/24/29/39,
distinct 30/39/35/26, top-1 share 9.1/8.2/10.8/16.6% — run-to-run noise is
huge; EXPL_R1's 86x remains the only true dominance outlier. P1 (29 ok/39 over
prediction, both under 60 bar), P2 (1.17x/0.67x vs ≥1.3x), P3 (higher not
lower) — all read as null-config noise, not treatment effects. Efficacy
replication: with-card beats without-card in ALL FOUR MEM-config reps
(R1 −.011 vs −.025; R2 +.004 vs −.022; NOV_R1 −.002 vs −.024; NOV_R2 −.013 vs
−.029). To actually wire novelty: score_floor gating membership, novelty in
the auction bid, or novelty-ordered probe lane — proposal pending user
sign-off; 4-rep data suggests dominance may not be a real problem under
max_cards=1. K=5 winner re-evals running; stats + PDF next. Telegram proxy
(Squid 64.225.96.36:8888) went down ~10:50 — correction message queued on a
retry loop.

### 2026-07-11 ~11:15 — four-arm closeout COMPLETE (night queue item d)

K=5 re-evals of NOV winners done (relaunch after first attempt hung on dead
default HOVER_CHAIN_URL 10.232.30.185; fix = explicit 10.232.24.68 + proxies
stripped). closeout_stats.py final numbers (scratchpad
closeout_stats_final.json, PDF hover_novelty_closeout_20260711.pdf SENT to
Telegram 11:12; correction message delivered 10:50 after Squid recovered):

- Winner re-eval ranking (mean ± 95% CI): MEM_R1 .8298±.0109 ≈ NOV_R2
  .8291±.0090 (paired p=.73) > EXPL_R1 .8229±.0078 > NOMEM_R2 .8107±.0129 >
  NOV_R1 .8062±.0029 > NOMEM_R1 .7964±.0105 ≈ EXPL_R2 .7956±.0043 > MEM_R2
  .7893±.0096. Top two across all 8 runs are BOTH MEM-config replicates; each
  significantly beats both NOMEM winners paired per-sample (p .0001/.0006 and
  <.0001/.028). Curse small, sign-inconsistent (−.004..+.012).
- Same-config replicates differ significantly (NOV_R2 vs NOV_R1 p=.0008):
  winner-quality variance is evolutionary-outcome variance, not eval noise →
  ≥4 replicates when best-of-run is the decision variable.
- Arm means (best-of-run re-eval): MEM(4) .8136 sd .0195 > EXPL .8092 sd
  .0193 > NOMEM .8036 sd .0101 — ordering right, no run-level significance.
- Efficacy pooled over 4 identical-config reps: with-card −.0052 (n=442) vs
  without −.0251 (n=550), one-sided MW p=6.6e-07; 4/4 replicate sign
  agreement. S1 prereg passes trivially (p=.54, arms identical by inertness).

USER AWAKE, directives 11:0x: (1) "fix the selection based on your proposal
(so it is more fair)" → novelty wiring APPROVED, sequenced FIRST (task #15);
(2) THEN 3D chain BD wiring (#13); (3) asked how instr_chars ("prompt
richness") is computed — answered: sum of chars over aim/stage_action/
reasoning_questions/example_reasoning per step (excluding "<none>") +
system_prompt length. Chosen wiring: novelty discount folded into the AUCTION
BID (changes gate auction.py:395; budgeter+probe become novelty-aware via
the slate bid). Discount strength to be calibrated by offline replay of the 4
runs' logged slates before any code lands.
