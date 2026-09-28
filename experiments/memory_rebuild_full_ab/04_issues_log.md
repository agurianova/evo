# memory=full rebuild replicate pair — issues log

Append-only. One dated entry per issue (infra, config, anomaly), with
resolution. Purpose: behavioral sign-off that the rebuilt dynamic memory stack
(`refactor/memory-rebuild`, PR #294) reproduces the prior memfix recipe at
scale — 2 replicate `memory=full` heilbron runs (R1/R2), 500 mutants each.

## 2026-07-03 — launch

- **Recipe.** `memory=full memory/llm=qwen_instruct num_parents=2` on heilbron,
  `pipeline=intra_extra_memory`, `storage=disk`, mutator
  `Qwen3-235B-A22B-Thinking-2507`, memory-LLM `Qwen/Qwen3-235B-A22B-Instruct-2507`,
  both via proxy `10.232.89.98:4000`. `max_mutants=500`. Launched from the
  worktree so `import gigaevo` + config resolve to the rebuild branch (verified
  `gigaevo.__file__` → worktree). R1 PID 636039, R2 PID 636330.
- **Config defaults flipped this session (user directive).** `config/memory/full.yaml`
  defaults changed `reputation: beta_binomial → bd_proximity` and
  `excluder: none → lineage` so the dynamic recipe the user wants (BD-cell
  reputation + lineage card filter) is the `memory=full` default, not a CLI
  override. Header comment updated to match; BD-proximity requires a
  single-island algorithm (fail-fast on multi_island) — consistent with the
  framework's single-island default.
- **`ev_floor` audit (user-caught).** The live default is `ev_floor: 0.0`
  (`config/memory/auction/thompson_ev.yaml`) — non-positive expected gain
  abstains, no problem-dependent magic constant. Cold cards borrow the in-round
  warm-magnitude median, else the primary metric's `significant_change` from
  `metrics_context`. The `0.01` was only a bad illustrative value in the
  `full.yaml` header comment; replaced with a dimensionless leaf example
  (`memory.reader.max_cards=2`).
- **Startup validated live (staggered launch).** R1 launched first; confirmed it
  cleared startup before firing R2. Both models verified on the proxy; both
  loaded 5 seed programs; R1's read path fired a `RetrievalPlannerAgent` call
  `ok:true` with structured-output method auto-resolved to `json_schema` (the
  method the Qwen-235B proxy requires); write path (LiveMemoryRefreshHook +
  MemoryWriter) auto-wired under `memory=full`. No island-compat error →
  bd_proximity + LineageExcluder instantiated cleanly.
- **Expected heilbron invalidity.** First-mutant `QhullError` ("Initial simplex
  is flat") on a degenerate point config = normal heilbron validator reject
  (the 11–42% per-run invalidity seen in prior heilbron runs), not infra.
- **Monitoring.** `monitor.py` nohup'd (PID 636710, `monitor.log`,
  `monitor_state.json`) — every 1.5h posts one compact Telegram update
  (per-run alive/programs/best via `gigaevo top` on disk storage), anomaly-alerts
  once per run on early death (<500 programs) or count stall, completion ping
  per run, exits when both finish. PID-reuse-guarded via /proc cmdline.
  Survives Claude session end; restart-safe (state file).
- **Config committed.** `config/memory/full.yaml` defaults flip committed
  `ac3898fe` on `refactor/memory-rebuild` (push to PR #294 still held per user).

## 2026-07-03 — warmup latency (health check ~23 min in)

Both runs ALIVE and progressing but SLOW; program count still 5 (seeds only) at
~23 min — no mutant finalized yet. Cause is latency, not a stall:
- **Thinking mutator is the dominant cost.** `MutationSuggestionAgent`
  (`Qwen3-235B-A22B-Thinking-2507`) calls run **137s / 329s / 356s / 472s** each,
  emitting 7k–21k output tokens (long reasoning traces). Expected for a Thinking
  model; caps throughput hard.
- **Memory-read latency spikes under proxy contention.** Early `RetrievalPlanner`
  calls (empty bank) were ~4–5s; once 8 concurrent Thinking mutations saturate
  the shared proxy, one `RetrievalPlannerAgent` call clocked **898s (~15 min)**
  and `MEMORY_READ_SELECTION` `research` timing hit 90–112s. The memory-LLM
  (Instruct) is starving behind the mutator on the same `10.232.89.98:4000`
  proxy. Watch item — not fatal (read fails-to-empty), but it inflates per-mutant
  wall time.
- **Research returns `outcome:"empty"` (`research_empty`) early — expected.** Bank
  is unpopulated until the writer banks its first cards; candidates appear only
  after that. Not a defect.
- **One `ParentRefresher: timed out waiting for 2 parents — aborting mutant`**
  (10-min wait, 18:38→18:48). Consequence of `num_parents=2` against a tiny early
  population; aborts a mutant rather than stalling the loop. Watch the recurrence
  rate — if frequent it wastes budget, but it is the requested recipe, not a bug.
- Net: at this rate warmup is slow; revisit throughput at the 1.5h monitor tick.

## 2026-07-03 — health check (~1h13m in)

Both runs ALIVE, past warmup, finalizing mutants. Status is throughput-bound,
not a correctness problem.
- **Counts.** R1 16 programs (11 mutants), R2 21 (16 mutants) — up from 5/5
  seeds. Best fitness on BOTH = the seed **0.00165**; no mutant has beaten the
  seed yet (gen 1–2, normal heilbron early). R1 lags R2 ~2×.
- **Throughput ceiling = Thinking mutator + shared-proxy contention.**
  `MutationSuggestionAgent` calls 69–465s each (R1 saw 366s/465s traces; R2
  69–182s). Backpressure saturated: `in_flight 8/8`, `llm_active` only 0–2 → 8
  mutation DAGs queued but few actually on the LLM. Two replicates compete for
  the same 3 Thinking nodes (mutation-3/4/7) through one proxy, so the pair is
  contention-limited. R1's extra ParentRefresher timeouts (5 vs 3) + longer
  Thinking traces explain its lag; not a bug.
- **Read path healthy; 898s spike did NOT recur.** RetrievalPlanner/Reflection
  `ok:true` at ~1–3s now; `MEMORY_RESEARCH_STEP` steps ~3s. The warmup 898s
  starvation looks transient — watch item eased.
- **Write path wired but not yet fired — EXPECTED.** 0 cards banked, no memory
  dir on disk, research `outcome=empty` (42–52×). Root cause is cadence, not a
  wiring gap: resolved `.hydra/config.yaml` wires `post_step_hook →
  LiveMemoryRefreshHook` with `tracker: ${ref:memory.writer}`
  (`gigaevo.memory.write.writer.MemoryWriter`) and `refresh_every: 10`. The hook
  banks only every 10 ingestor sweeps that land a program and returns silently
  below that; batch ingest means 16–21 programs arrived in <10 sweeps, so
  neither run has hit its first refresh. Until it does, `memory=full`
  legitimately reads an empty bank (≈ no-mem). The startup TypeError guard
  (needs an `IncrementalPostRunHook`) did not trip → writer is attached.
- **Rough ETA (post-warmup rates, ~50 min productive window).** R2 ~0.32
  mut/min, R1 ~0.22 → to the k=245 fair-end: **R2 ~12h, R1 ~17h** from now; to
  the monitor's full 500-mutant completion, roughly 2×. We only need k=245 for
  the A/D comparison, so the run can be stopped early once both clear ~245
  programs rather than waiting for 500.

## 2026-07-03 — best-fitness correction + write path firing (~2h15m in)

Supersedes the "~1h13m in" note that read best = seed 0.00165: that was a
mid-warmup artifact (only ~16–21 programs then, all gen 1–2). Ground truth from
disk / `gigaevo top`:
- **R1** 66 programs, best **0.01627** (id 22283940, gen 3).
- **R2** 59 programs, best **0.02181** (id 9fd6ecc3, gen 5).
Both ~10–13× above the seed — mutants have long since beaten it; the runs are
climbing normally.

- **Write path is firing end-to-end** (the milestone the ~1h13m note was still
  waiting on). Both banks populated with `mem-*` insight cards + `program-*`
  cards; `MEMORY_RESEARCH outcome:"ok"` and full auctions run every read.
  Reputation is now moving off the Beta(1,1) prior vs Beta(3,3) baseline
  (e.g. R2 `mem-267f507d12df` at Beta(2,3); R1 best-program card
  `program-22283940` correctly unselected on negative donor magnitude −0.0033) —
  the rebuilt read↔write↔reputation loop is behaving.

## 2026-07-03 — litellm restart: no impact on R1/R2 (~2h15m in)

User relaunched litellm ~20:42 (to repair the unrelated Qwen3-8B *chain* alias,
which had been routed to two dead endpoints — orthogonal to this experiment; the
chain alias is not used by heilbron memory runs). Confirmed the restart did NOT
interrupt R1/R2:
- PIDs 636039/636330 alive; **zero** APIConnectionError/connection/refused/
  timeout in the 20:43→20:59 window (the only "timed out" lines are benign
  DagScheduler cleanup + the expected num_parents=2 ParentRefresher aborts).
- Fresh `ok:true` calls on both at 20:59 — R1 MutationSuggestionAgent (Thinking,
  73.8s), R2 RetrievalReflectionAgent (Instruct, 3.7s). Mutation + instruct
  aliases routed cleanly throughout; no recovery was required.
- Progress toward the k=245 fair-end: R1 66/245 (27%), R2 59/245 (24%). Settling
  into a ~1h health-check cadence (background monitor 636710 owns the 1.5h
  Telegram updates + anomaly alerts).

## 2026-07-03 — STOPPED + RELAUNCHED with novelty gate (supersedes the pre-gate pair)

Per user directive ("relaunch them with the latest fixes and memory novelty
admitter"), the pre-gate pair was stopped and a fresh pair launched on the
committed novelty-admission code.

- **Stopped the pre-gate pair.** SIGKILL'd R1 636039 (139 programs at stop), R2
  636330 (133 programs) and their `exec_runner` workers; killed monitor 636710
  first so it could not fire a false early-death anomaly alert. Both runs were
  well short of the k=245 fair-end, so little compute was lost. Their partial
  outputs stay under `memory_rebuild_full_ab_2026-07-03/{R1,R2}` for reference.
  (SIGTERM was ignored by the engine; SIGKILL was decisive.)
- **New code committed** `7bafdf48` on `refactor/memory-rebuild` (push to PR #294
  still held per user): novelty-admission gate on freshly-authored idea cards
  (`writer.novelty_admission_gate=true`, on only in `memory=full`) + inline
  intra-batch consolidation (`ConsolidationScheduler.consolidate_written`) +
  drop of the unused `program_twin_eps` dedup knob. 581 tests green, ruff clean.
- **Relaunched at a FRESH root** `memory_rebuild_full_ab_novelty_2026-07-03/{R1,R2}`
  (not reusing the old R1/R2 dirs) so each run builds its card bank from scratch
  under the gate — reusing the pre-gate disk storage would let ungated cards
  contaminate the new bank. Recipe byte-identical to the pre-gate launch; the
  gate + inline consolidation come from the committed code, not CLI overrides.
  **R1 PID 693967, R2 PID 693970.** `launch_full.sh` in the new root.
- **Gate confirmed live in the resolved config** (not just the source): both
  runs' `.hydra/config.yaml` show `memory.writer.novelty_admission_gate: true` on
  `MemoryWriter`, alongside `LineageExcluder` and `consolidation_every_n: 32`.
- **Startup validated.** Both alive and stable; engine built single-island
  (`max_size=75`, bd_proximity-compatible), 5 seed programs loaded, prompts
  resolved from the worktree (rebuild branch), zero errors through init. Read/
  write path + gate firing pending the slow Thinking-mutator warmup (the pre-gate
  pair took ~23 min to its first mutant and **~1h35m–1h50m to first write-path
  bank** — same expected here). **Watch item:** first observation of the gate
  rejecting a prior-known card once the writer banks its first idea cards.
- **Monitoring.** New `monitor.py` nohup'd (**PID 694728**, same 1.5h Telegram
  cadence + anomaly/stall/completion alerts, PID-reuse-guarded on the novelty
  root path). Old monitor 636710 stopped.

## 2026-07-03 — CORRECTION: elapsed-time figures were inflated ~3h by MSK/UTC mix-up

The "~5.5h to first write-path bank" figures in the earlier notes and the
relaunch entry above were **wrong** — a timezone bug, now fixed in place. Ground
truth from the pre-gate run's own artifacts:

- **First write-path bank (first `write_ledger` `outcome:"added"` = first
  `MEMORY_STORE_WRITE`, cross-agreeing to the second):** R1 at **17:19:28 UTC /
  20:19:28 MSK = +1h49m** after launch; R2 at **17:05:43 UTC / 20:05:43 MSK =
  +1h35m**. So ~1.5h, not ~5.5h.
- **Root cause.** The box runs in **MSK (UTC+3)**. Loguru console lines
  (`launch.out`) print **local MSK**; the JSON events' `timestamp_utc` and the
  monitor's `time.strftime(..., time.gmtime())` are **UTC** (−3h). Subtracting a
  UTC event timestamp from an MSK wall-clock (or vice-versa) inflates elapsed by
  exactly +3h: the real ~2h15m health check read as "~5.5h."
- **Sanity bound.** The pre-gate pair launched 18:29:53 MSK and was SIGKILL'd at
  ~22:56 MSK (checkpoint mtimes) → max age **~4h27m**. "5.5h in" was structurally
  impossible, which is the tell.
- **Fixed above:** the two "(~5.5h in)" section headers → "(~2h15m in)"; the
  relaunch prediction → "~1h35m–1h50m to first write-path bank." The `~1h13m in`
  health-check note was already correct (its label used the local clock
  consistently). No behavioral impact on the runs — logging/labels only.

## 2026-07-04 — health tick ~1h32m: reputation loop closed (R1), gate reproducing prior-redundancy

Both alive; R1 58/245, R2 66/245; **0** real conn/timeout errors; llm_io 630/642
calls all `error=None`. Clean, no anomalies. Two substantive behaviors:

- **Novelty gate — R1 20 rejections vs R2 2 (0 fail-open either).** R1's rejections
  are DIVERSE generic metaheuristics — simulated annealing / cooling schedules,
  Metropolis acceptance, population+crossover GA, hill-climbing, adaptive step-size,
  budget extension, structured-grid init, rejection-sampling feasibility — NOT a
  stuck re-proposal loop. A live reproduction of the ~89%-prior-redundant finding:
  R1's writer keeps reaching for the standard optimizer repertoire unprompted and
  the gate strips all of it. The R1-much-greater-than-R2 asymmetry tracks authoring
  content — R2 locked onto task-specific structural levers (barycentric density,
  greedy maximin) early, R1 keeps proposing generic scaffolds; the gate handles both.
- **Reputation loop closed on R1: first 3 gain_events** (schema
  `{context, gain, invalid}`) with honest signed deltas — −0.00031 (child worse),
  0.0/`invalid=true`, and **+0.00204** vs parent. read→auction→improve→restamp works
  end-to-end and records negatives/invalids, not just wins. **Caveat:** the gains are
  on program EXEMPLAR cards; insight cards still 0 gain_events on both runs — "does an
  authored insight lever ever earn a gain" remains the open signal.
- Best fitness R1 0.01083, R2 0.02193 (R2 leads). k=245 ~overnight out.

## 2026-07-04 — ~1h47m: insight-card reputation FLOWING (open signal closed) + R1/R2 divergence

Both alive; R1 72/245 best 0.01744, R2 68/245 best 0.02193; 0 errors.

- **Open signal CLOSED — an authored INSIGHT card earned reputation.** R1
  `mem-2eba21f31dfb` ("enforce a minimum inter-point distance during stochastic
  generation/mutation to prevent numerical degeneracy") now carries 3 gain_events
  incl. **+0.00589** and −0.00035 — selected → injected → child improved → credited.
  read→auction→inject→restamp closes for authored levers, not just program exemplars.
- **Bank re-expanded — consolidation NOT over-collapsing.** R1 grew 1→6 insight
  (+9 program); the earlier collapse-to-1 concern is resolved. The 6 are diverse
  Heilbronn-specific levers (opposite-longest-edge vertex perturbation, worst-config
  participation aggregation, signed-area gradient scaling+normalization, step-decay
  with feasibility retry, min inter-point distance). R2 lean at 3 insight + 1 program.
- **Selection loop active:** R1 136 READ_SELECTION (69 injected: 30 insight + 39
  program), 90 auctions; R2 112 (37 injected: 29 insight + 8 program), 49 auctions.
  Insight cards are being selected/injected on both, not banked-and-ignored.
- **Divergence to watch:** R2 LEADS fitness (0.0219 vs 0.0174) with a lean 3-card bank
  and **0 gains credited yet**; R1 trails but holds the rich, reputation-active bank.
  Early sign memory-richness ≠ fitness lead here — R2's early greedy-maximin exemplar
  carries it. Watch whether R1's active reputation closes the gap. R2 gains pending
  (fewer injections / later restamp), not broken.

## 2026-07-04 — ~2h: bank crispness scan (recurring) — banks crisp + on-target, but reputation ⊥ crispness

Full subagent audit of both banks (banks live at `<run>/memory/cards.json`, NOT under
`storage/`). R1 = 6 insight + 9 program; R2 = 3 insight + 1 program.

- **Crispness good.** 5 crisp / 4 borderline / 0 mushy across 9 insight cards. R1 crisp:
  signed-area sign+normalize gradient (aa53), opposite-longest-edge vertex push (48be),
  top-k-worst-triplet targeting (76352). R2 crisp: greedy-maximin grid construction (c3d6),
  area-preserving barycentric sampling (86d25). Borderline = generic guards (min-dist
  repulsion 2eba, step-decay+retry f5e7, grid-init 2aa5, simplex-clamp ba47). One soft
  near-dup pair R1 2aa5~2eba (Jaccard 0.36; distinct mechanisms, not a merge).
- **Banks capture the winners.** R1 crisp cards = the winning GA+gradient-polish strategy
  exactly; R2 c3d6 = one-to-one with the greedy-maximin-grid all 3 top programs run. The
  write path is banking the right levers, and the novelty gate is keeping the banks lean.
- **KEY FINDING — reputation ⊥ crispness.** 8/9 insight cards (incl. EVERY winner-aligned
  crisp card) have 0 gain_events; the ONLY card with gains is R1 2eba (+0.0055 net) — the
  least-crisp generic repulsion guard. Reputation has started but is attributed to a broad
  generic card, not the crisp specific ones. Likely transient (2eba is early-banked → more
  selection→restamp cycles) — BUT if crisp winner-aligned cards stay at 0 gains as the run
  matures, it points to the gain channel rewarding BREADTH over SPECIFICITY (cf.
  [[memory_card_posterior_inflation_loophole]], [[memory_no_novelty_pressure_in_card_selection]]).
  The recurring scan tracks it.
- **Program hygiene (mutator, not bank).** R1 rank2 (0.01708) BLOATED — mutation block
  triplicated (mirror-symmetry copy-paste), local_search verbatim-copied, 268 lines. R2
  rank1≈rank2 byte-near-dup programs both 0.02193 (differ only in distinctness threshold +
  n_refine); rank1/rank3 marked `discarded` (dedup/lifecycle kept the `done` near-dup).
  Not a memory issue; noted for the trajectory record.

## 2026-07-04 — ~2h15m: VERIFIED — reputation throttle is the mutator's `card_ids_used` declare-rate, not selection/merge

Traced an idea's full lifecycle from event logs + the program pool (both runs).
Corrects the earlier snapshot-based "reputation ⊥ crispness" read.

- **"Ideas not selected" is FALSE.** Read path works: crisp cards win auctions
  (win-rate 0.38–0.71, no cold-start lockout on the beta/Thompson auction vs a (3,3)
  baseline) and inject heavily (R1 aa53 won22, 48be won15, 76352 won23/sel14; R2 c3d6
  won29/sel18, ba47 won31/sel17).
- **Credit gate = base_selected_ids ∩ card_ids_used** (stats.py:130): a card earns a
  gain event only when injected for the mutator's NAMED BASE parent AND self-declared
  used. Verified over the pool:
  - R1: 94 mutated children → 50 base-injected, **39 (41%) declared any card used,
    22 (23%) credited**; credit-rate vs injected instances = 44%.
  - R2: 81 → 34 base-injected, **23 (28%) declared used, 16 (20%) credited**; 47%.
- **Two leaks, per-card:** (1) injected-but-not-declared — `mem-aa53` (crisp
  signed-area) inj=4 **used=0 credit=0**; `mem-76352` (crisp top-k-worst) inj=6
  **used=1 credit=0** — heavily selected, mutator never declared applying it. (2)
  donor-side injections don't credit (num_parents=2): 76352 sel=14 vs base-inj=6 gap
  = donor-side, structurally uncreditable.
- **Reputation DOES reach crisp cards when declared:** 48be credit=4, c3d6 credit=5,
  2eba credit=3, f5e7 credit=3, 86d25 credit=2. Crispness↔reputation is rate-limited
  by the ~28–41% declare-rate, NOT decoupled.
- **Merge is NOT a leak.** merge_cards unions gain_events (merge.py:70); restamp folds
  absorbed_ids→survivor (stats.py:220-223), re-aliasing since-merged ids so credit
  doesn't orphan. R1's 50 merges churn ids, not reputation.
- **Rejection funnel:** author (~82 R1 insight ledger writes + 25 novelty rejects) →
  novelty gate rejects generic (25) → admit → consolidation merges near-dups (~50) →
  ~6 survive. Bank stays small by gate+merge+eviction, not lack of authoring.
- Matches known [[project_memory_idea_lifecycle_funnel_finding]] (mutator use-rate) +
  [[memory_card_repeat_use_verified_findings]]. Actionable lever for tighter
  reputation↔contribution coupling: the mutator's `card_ids_used` self-report (or
  injection-based attribution) — NOT selection/auction/merge. No change mid-run.

## 2026-07-04 — CORRECTION (the prior "leak" framing is WITHDRAWN): under-declaration is HONEST non-use

Verified child-vs-base-parent code for the aa53/76352 "0-credit despite injection" cases.
The earlier entry called `used=0` a self-report "leak" — that is WRONG for these cards.

- **mem-76352 (top-k-worst):** children run single-worst targeting
  (`get_smallest_triangle_triplet`/`_area`), NOT the multi-worst participation
  aggregation the card advocates. Mutator genuinely did not apply the card's mechanism
  → `used=0` HONEST, 0 credit deserved.
- **mem-aa53 (signed-area gradient):** the mechanism IS in all 4 children's code
  (`signed_area`, `sign * grad`, `/ np.linalg.norm`) — but it was **INHERITED from the
  base parent in 4/4** (base_mech=True every time; e.g. child e9b9a0e7 ← base c96e9c18,
  both have it, fit 0.0102→0.0174). The card describes a strategy already endemic to its
  own lineage (the librarian authored it FROM that lineage's diff), so injecting it back
  into descendants applies nothing new. `used=0` is HONEST.
- **Reframe:** the credit gate is behaving CORRECTLY — it credits causal contribution
  (the card changed the base parent's behavior), not mere presence. Crisp,
  winner-distilled cards earn the LEAST reputation precisely because the strategy is
  already baked into the winning lineage they were distilled from. This re-expresses the
  prior-redundancy theme [[project_idea_triviality_priorness_analysis]] at the reputation
  layer: a card that re-describes what search already found cannot earn incremental credit.
- **Net:** reputation flows only when a card gives the base parent a mechanism it LACKED
  (genuine novel application). That is the correct, desired behavior — nothing to fix.
  The R1 top program (e9b9a0e7, 0.0174) came from the signed-area lineage, yet aa53
  rightly gets no credit for a mechanism it did not introduce. Known limitation (not a
  bug): honest attribution cannot credit a card for *reinforcing* an already-present good
  behavior, since there is no counterfactual — acceptable.

## 2026-07-04 01:42 MSK — HOURLY AUDIT LOOP tick #1 (subagents A+B) — all machinery GREEN

First tick of the standing hourly subagent audit (`idea_quality_loop_spec.md`): two
read-only general-purpose subagents, A=idea-quality, B=machinery-integrity, over both
runs. **DEVIATIONS: NONE (A and B).** Runs ~3h in, both healthy, PIDs alive.
R1 = 117 progs / best 0.01744 (gen 6); R2 = 96 progs / best 0.02206 (gen 4). Neither at
k=245 (bars A 0.0294 / D 0.0289) — fitness below the fair-end line is expected at <½ budget.

**B · machinery — 7/7 PASS both runs.** Merge/restamp union invariant confirmed on a live
survivor (R1 mem-48be absorbed 3 ids, re-aliased survivor=3/absorbed=0, not orphaned).
Retrieval warms as bank grows (research_empty 40%→1% R1 / 70%→8% R2). Auction fair (no
monopoly: top card 9%/23% of wins; cold cards win ~48–50%). Credit gate in-band
(R1 40% declare/21% credited, R2 33%/23%; ~42–51% of injected instances credited).
Restamp passes growing (R1 credited_card_count →10, R2 →4). Only infra blip = a single
isolated 01:04 MSK APIConnection burst (7 R1 / 5 R2), fail-open, fully recovered, no
recurrence; exec_runner tracebacks = invalid mutants (handled).

**A · idea-quality.** Crispness — R1: 2 crisp / 1 borderline / 2 mushy; R2: 1 crisp /
2 borderline / 0 mushy. Crisp cards are structural (R1 aa53 coordinated sign-corrected
min-area gradient, 4a92 symmetric-generator mirror; R2 86d2 sqrt-barycentric anti-clustering);
mushy = generic feasibility hygiene (R1 48be epsilon-scaling, e698 multi-scale perturbation).
Mild redundancy clusters (both runs: a symmetry/degeneracy-init pair). Novelty gate
calibrated: 29 R1 / 11 R2 rejections, **0 fail-opens both**, every sampled reason cites
novelty-vs-prior on a generic move (step-scaling, SA, farthest-point, fp-tolerance) and
explicitly contrasts the structural levers it does NOT exploit; scanned ALL rejections —
**no genuinely Heilbronn-structural lever was rejected.**

**Reputation honesty (code-checked, the key rigor).** Every 0/low-credit insight card is
INHERITED or NOT-USED — **no UNDER-REPORT in either run.** Confirms the credit gate credits
causal contribution, not presence: crisp winner-distilled cards earn least precisely because
their strategy is already endemic to the lineage they were distilled from (re-confirms the
2026-07-04 CORRECTION above). Snapshot 0-gains on R2 mem-000d is restamp lag (children
postdate the 01:15 cards.json flush; restamp authoritative), not orphaning.

**Standing observation to watch (behavior, not a fault):** R2 authors ~⅓ the cards of R1
(6 vs ~large live set) and has ~3× the invalid-mutant rate, yet currently LEADS on fitness
(0.0221 vs 0.0174) — a run-to-run asymmetry, consistent with memory buying no fitness at
this scale. No Telegram sent (no deviation, no k=245 crossing). Next tick ~02:37 MSK.

## 2026-07-04 02:49 MSK — HOURLY AUDIT LOOP tick #2 (subagents A+B) — all machinery GREEN

**DEVIATIONS: NONE (A and B).** Runs ~4h in, both healthy, PIDs alive.
R1 = 165 progs / best 0.02161 (gen 10); R2 = 132 progs / best 0.02245 (gen 8). Neither at
k=245. Both fitnesses ticked up vs tick #1 (R1 0.01744→0.02161, R2 0.02206→0.02245);
R2 still leads but R1 closed most of the gap.

**B · machinery — 7/7 PASS both runs.** Credit rate is RISING, not crashing: R1 46% declare
/ 27% credited / 47% of injected instances; R2 44% / 31% / 58% — both at/above the ~40%/20-25%
baseline. Merge/restamp union re-confirmed on a fresh survivor (R1 mem-2aa5 absorbed 3 ids
[2eba,e732,8f9b]; 6 pool children carry survivor+absorbed in base_selected, credited ones fold
onto the survivor's 4 gain_events — re-homed, not dropped). Retrieval keeps warming
(research_empty 46→3 R1 / 63→7 R2). Auction fair (top winner 7%/14%; cold cards ~49-50%;
abstain-w/-candidates 18-19% = normal below-floor Thompson). Restamp counts climbing
(R1 credited_card_count →21, R2 →10). Only infra event = one ~11s 22:04 UTC proxy blip
(R1×7 / R2×~77 ConnErr), fully recovered, none since; exec_runner "FAILED" = invalid mutants.

**A · idea-quality.** Crispness — R1: 1 crisp / 6 borderline / 2 mushy (n=9); R2: 1 crisp /
4 borderline / 1 mushy (n=6). As banks grow, structural crispness stays at ONE card per bank
(R1 mem-49148 min-area-triplet + longest-edge-normal move; R2 mem-c3d6 min-area-vertex
perturbation) surrounded by generic feasibility/init/annealing filler. Novelty gate calibrated:
R1 38 rej / R2 23 rej, **0 fail-opens both**, ~45-52% admit rate (not collapsing), and it
rejected NO genuinely structural lever (all min-area/collinearity/signed-area cards admitted).

**Cross-run convergence (notable, reinforces prior-redundancy theme):** both independent banks
rediscover the SAME tiny useful core — min-area-triplet targeting {R1 mem-49148 ≈ R2 mem-c3d6},
barycentric feasibility {R1 1f8f ≈ R2 866f}, annealing {R1 ea1f ≈ R2 b1d0}. The useful memory
signal is a small universal recipe, echoing [[project_static_lever_baseline]]'s core-6 finding.

**Reputation honesty (code-checked) — no UNDER-REPORT, but ONE structural nuance surfaced.**
R1 mem-49148 (crisp, inj 4 / credit 1): child 1303d594 DOES apply the mechanism (absent in base
a719b8b3 AND crossover donor 87d28b5b) — but a **co-injected PROGRAM card `program-9b9834b0`
encodes the identical smallest-triangle→opposite-vertex-along-longest-edge move**, and the child's
`card_ids_used=['program-9b9834b0']` credited the twin. So the mechanism WAS credited — the
insight card lost the attribution race to its program-card duplicate. Not a leak (credit landed
on the twin), but a standing observation: **insight/program card duplication can split/misattribute
reputation between two cards describing the same lever.** Worth watching if it recurs; the two
card kinds are not deduped against each other. Everything else honest (INHERITED/NOT-USED, e.g.
R1 mem-e698 clamp block verbatim in base cc013f10). No Telegram (no deviation, no k=245).

## 2026-07-04 04:03 MSK — HOURLY AUDIT LOOP tick #3 (subagents A+B) — GREEN + 3 emerging threads

**DEVIATIONS: NONE (A and B).** Runs ~5h in, both healthy, PIDs alive.
R1 = 204-208 progs / best 0.02316 (gen 9); R2 = 182-185 progs / best 0.02309 (gen 11).
**The two runs have CONVERGED** (R1 0.01744→0.02161→0.02316; R2 0.02206→0.02245→0.02309 — R1
caught R2). Neither at k=245.

**B · machinery — 7/7 PASS both runs.** Union invariant confirmed EXACTLY this tick: R1 survivor
mem-2aa5 banked 5 gain_events = self 1 + absorbed mem-2eba 3 + mem-8f9b 1. Credit rates hold
at/above baseline (R1 49% declare / 31% credited / 48% of injected instances; R2 48% / 35% /
62%). Retrieval still warming (research_empty 47%→1% R1 / 66%→2% R2). Auction fair (top 38/47
of 400/294 runs, no monopoly; cold cards win 659/494×). Restamp growing (R1 credited_card_count
→26 / R2 →17). Infra clean (200/200 llm ok; the lone 01:04 blip never recurred).

**A · idea-quality.** Crispness — **R1: 3 crisp / 8 borderline / 2 mushy (n=13); R2: 0 crisp /
9 borderline / 2 mushy (n=11).** R1 GAINED structural cards this tick (smallest-triangle
refinement cluster mem-1726/62f4/d61b: signed-area gradient aggregation, longest-edge-opposite
move, min-area+collinearity veto). Novelty gate calibrated: R1 45 rej / R2 41 rej, **0 fail-opens
both**, no structural lever rejected (all min-area/collinearity/signed-area cards admitted).
No genuine UNDER-REPORT — the one structural-looking candidate (R1 mem-475086) is an
ATTRIBUTION-SPLIT (credit landed on co-injected program twin).

**THREE emerging threads to watch (none are deviations; logging for trend):**
1. **R2 bank has drifted FULLY GENERIC — 0 structural-crisp cards** vs R1's 3. Both still ≈tied
   on fitness, so structural bank quality is NOT tracking fitness at this scale — reinforces the
   "memory buys no fitness / small universal core is all that's usable" theme
   [[project_static_lever_baseline]]. R2's most-used card (mem-c3d6, 13 gains) is generic
   barycentric feasibility, not a structural lever.
2. **Merge RE-ENRICHMENT degraded two R2 cards** — mem-83989683650e drifted min-**area**→min-
   **distance** (farthest-point), and mem-bc9c7dd120b0's claim FLIPPED to self-contradiction
   (linear-param-good → root-scaled-good) across merges. The consolidation LLM re-enrichment can
   corrupt/flip a card's mechanism claim. Card-quality concern, not a machinery fault (events
   still union correctly). WATCH: if it spreads, the librarian re-enrichment prompt is the lever.
3. **Attribution-split twins RECUR + spread** — the tick-2 pair (mem-49148 ≡ program-9b9834b0)
   recurs, PLUS a new R1 pair (mem-475086 ≡ program-bb48546e, GA→gradient-refinement). Insight
   and program cards are not deduped against each other, so a lever's reputation splits across two
   cards; credit consistently lands on the program twin (correct, but fragments the signal).

**Minor (not a deviation):** novelty gate is stochastically permeable to the SA/annealing lever
(admits some SA cards while rejecting others) — judge variance, not a fail-open. **Mutant-health
asymmetry:** R2 invalid-mutant exec crashes ~3.7× R1 (104 vs 28) — for the idea-quality/mutant
side, not machinery. No Telegram (no deviation, no k=245). Next tick ~05:00 MSK.

## 2026-07-04 05:15 MSK — HOURLY AUDIT LOOP tick #4 (subagents A+B) — GREEN; k=245 IMMINENT, tracking BELOW bars

**DEVIATIONS: NONE (A and B).** Runs ~6h in, both healthy, PIDs alive.
**R1 = 244 progs, best 0.02366 (gen 14) — ONE away from k=245.** R2 = 226 progs, best 0.02321 (gen 11).

**⚠ HEADLINE (preliminary, confirm at the crossing):** both best-fitness values (~0.0237) sit
**~0.005 BELOW both comparison bars** (A no-mem 0.0294±0.0018 / D dynamic-memfix 0.0289±0.0015).
R1's best is effectively locked for the k=245 point, so rebuilt `memory=full` looks to be landing
BELOW both no-mem and dynamic-memfix at the fair-end — NOT the expected D≈no-mem parity. Holding
Telegram until R1 actually crosses 245 (next tick) so the reported number is the locked k=245 value.
Caveat: n=2 replicates, single runs; fitness may keep climbing past 245 but the COMPARISON is fixed
at k=245 to match the bars. This is the experiment's money question — watch the crossing.

**B · machinery — 7/7 PASS both runs.** Union invariant confirmed EXACTLY (R1 survivor mem-1076
5==5; R2 survivor mem-57e9 13==13). Credit rates RISING (R1 49% declare / 31% credited / 47%
instances; R2 51% / 36% / 57%). Retrieval warm (research_empty →1.5%/2.1%). Auction fair (top
5.2%/6.8%; cold cards win 766/634×). Restamp monotone (R1 credited-set →37, R2 →23). 0 fail-opens.

**A · idea-quality.** Crispness — R1: 3 crisp / 11 borderline / 1 mushy (n=15); R2: 1 crisp / 8
borderline / 1 mushy (n=10). R1 RECOVERED structural crispness (mem-03cb signed-area gradient
accumulation, mem-62f4 longest-edge-opposite move, mem-48be geometry-scaled distinctness). Novelty
gate calibrated: R1 54 rej / R2 45 rej, **0 fail-opens**, no structural lever rejected. No genuine
UNDER-REPORT (all non-use INHERITED / NOT-USED / ATTRIBUTION-SPLIT / used-but-child-invalid).

**Emerging threads update:**
- (a) **R2 generic drift PERSISTS (slightly worse)** — R2 structural-crisp 1 vs R1 3; R2's
  highest-credit card mem-57e9 (9 gains) got re-summarized AWAY from min-area/collinearity toward
  generic "grid-quantization error." Structural bank quality still not tracking fitness (both ≈tied).
- (b) **Merge re-enrichment claim-slide PERSISTS** — no current internal self-contradiction (the
  tick-3 bc9c flip resolved), but card identities keep sliding OFF their gain-earning mechanism
  across re-enrichment (mem-57e9 min-area→grid-quant; mem-27d5 low-discrepancy→grid). Cosmetic-to-
  moderate; the librarian re-enrichment prompt is the lever if we ever act on it.
- (c) **Attribution-split BROADENED into program mega-clusters** — NEW observation: program cards
  are barely deduped. R1 has ~20 near-clone program cards ("grid/asym init + GA + gradient refine"),
  R2 has ALL 15 program cards as near-duplicates ("greedy min-area/min-dist insertion via barycentric
  grid"). Each insight lever has a program-card twin (or 20) that wins the credit. Correct per rule,
  but reputation for a lever is fragmented across a large duplicate program family. This — not insight
  cards — is where the bank's bulk and redundancy actually live.

No Telegram (no deviation; k=245 not yet crossed). Next tick ~06:15 MSK — expect R1 past k=245;
will Telegram the locked A/D comparison then.

## 2026-07-04 06:30 MSK — HOURLY AUDIT LOOP tick #5 — ★ DECISIVE k=245 CROSSING ★ memory=full BELOW both bars

**Both runs crossed k=245.** LOCKED fair-end value = max fitness among the first 245 programs
by `iteration` (NOT best-so-far — that includes post-245 progs; `atomic_counter` is a different
namespace and must not be used as the ≤245 filter):

| Run | progs | progs iter≤245 | **LOCKED k=245** | best-so-far | verdict |
|---|---|---|---|---|---|
| R1 | 289 | 246 | **0.02366** | 0.02632 | BELOW (−0.00524 vs D ≈ 3.5 D-std) |
| R2 | 264 | 245 | **0.02337** | 0.02337 | BELOW (−0.00553 vs D ≈ 3.7 D-std) |

Bars: **A no-mem 0.0294±0.0018, D dynamic-memfix 0.0289±0.0015** (D-parity band [0.0274,0.0304]).
**Both replicates land ~0.005 below BOTH baselines** — rebuilt `memory=full` under the novelty
gate does NOT reproduce the expected D≈no-mem parity; it underperforms both at the fair-end.
Trajectory: R1 still climbing through 245 (peaks 0.02632 by ~iter275); R2 plateaued by ~iter150
(flat, best-so-far == k=245 lock). R2 valid-yield 69% vs R1 88% (more invalid mutants → lower plateau).
**This is a genuine EFFICACY result, not an integrity failure** (see machinery below — all clean).

**B · machinery — 7/7 PASS both runs, DEVIATIONS: NONE.** Union invariant exact (R1 survivor
mem-6acdf 5==5; R2 survivor mem-57e9 17==17). Credit rates hold ≥ baseline (R1 51% declare / 31%
credited / 45% instances; R2 53% / 36% / 53%). Retrieval warm (research_empty →2%/3%). Auction fair
(top 5%/6%; 73/76 & 40/42 cards win ≥1). Restamp monotone (R1 credited-set →42, R2 →30). **0 fail-opens.**

**A · idea-quality.** Crispness — R1: 4 crisp / 8 borderline / 2 mushy (structural-crisp 4); R2: 0
crisp / 9 borderline / 1 mushy (structural-crisp 0). Novelty gate: R1 61 rej / R2 55 rej, **0
fail-opens** (earlier "4/3 fail-open" was a false grep on reason-prose; word-boundary confirms 0),
no structural lever wrongly rejected. **0 genuine UNDER-REPORT** (all non-use INHERITED / NOT-USED /
ATTRIBUTION-SPLIT / used-but-child-invalid).

**★ KEY MECHANISTIC FINDING — thread (b) escalated from cosmetic drift to MECHANISM CONFLATION:**
R2's TOP reputation card **mem-57e9c88177d8 (17 gains)** is described as "temperature-controlled
acceptance = simulated annealing", but it ABSORBED mem-c3d6 (Sobol-QMC greedy) + mem-86d2 (non-SA),
and **only 4 of its 18 credited children (22%) actually implement SA** — the other 78% earned credit
under absorbed Sobol-QMC/greedy ids (e.g. child 36479475 = `qmc.Sobol` + greedy max-min-area, zero
annealing). The merge unions gain_events CORRECTLY (machinery-intact), but consolidation re-enriches
the survivor's DESCRIPTION to only one absorbed mechanism → **the highest-reputation card's injected
text no longer matches what earned its reputation.** This is a plausible CAUSAL contributor to the
below-bars result: the mutator is fed a high-credit SA description that does not reproduce the
Sobol-QMC/greedy behavior that actually worked. Lever = librarian/consolidation re-enrichment prompt
(do NOT act mid-run). Milder same-class slide on mem-f97bed (dispersion-proxy text vs direct-area credit).

**Threads (a)/(c):** (a) R2 generic drift WORSE — structural-crisp 0 (was 1) vs R1 4; R2's top card is
generic SA. (c) program mega-clusters GREW — R1 GA-clone family 20→25, R2 greedy family 15→19 (100%
mono-cluster); insight/program twins persist, credit lands on the program twin. Bank bulk+redundancy
live in program cards, still undeduped against insights.

**DECISION-GRADE CAVEAT before concluding "memory hurts":** the A/D bars are from EVOTAB-A-33; MUST
confirm they were measured with THIS exact mutator recipe (Qwen3-235B-Thinking, num_parents=2,
pipeline=intra_extra_memory) — a same-recipe no-mem control is the clean isolation. n=2 replicates.
**Telegram SENT** (decisive k=245 readout + machinery-clean + conflation candidate + caveat). Runs
continue to k=500 for trajectory shape; loop continues hourly. Next tick ~07:30 MSK.

## 2026-07-04 07:45 MSK — HOURLY AUDIT LOOP tick #6 — DEVIATIONS: NONE (k=245 LOCKED, unchanged)

Both runs LIVE (R1 693967 / R2 693970 cmdline-confirmed on the novelty root, max_mutants=500).
Progress: R1 333 progs / max_iter 332 (~66% of 500), best-so-far 0.02976; R2 308 progs / max_iter
308 (~62%), best-so-far 0.02523.

**k=245 fair-end now LOCKED (window full both runs) — identical to tick #5:**

| Run | progs iter<245 | valid in window | **LOCKED k=245** | vs tick#5 | vs D 0.0289 | vs A 0.0294 |
|---|---|---|---|---|---|---|
| R1 | 245 (win full) | 220/245 | **0.02366** | = | −0.0052 | −0.0057 |
| R2 | 244 (~full)    | 170/245 | **0.02337** | = | −0.0055 | −0.0060 |

Both stay **below both bars** (A lower-bound 0.0276, D lower-bound 0.0274). R2's window carries a
heavier early-invalid load (75 invalid in first 245 vs R1's 25) — its low plateau is partly a
valid-yield effect. Decisive A/D readout already Telegrammed at tick #5; NOT re-sent.

**B · machinery — 7/7 PASS both runs, DEVIATIONS: NONE.**
Infra: both alive, recent LLM error_type=null (only a stale 01:04 APIConnErr blip, recovered).
Gate: R1 69 rejects / R2 62 rejects, **fail-open 0** both. Merge: R1 247 merged / R2 140; union
invariant EXACT — R1 survivor mem-3b7714 (8 absorbed, none orphaned) 5==5; R2 survivor mem-17beeb
(3 absorbed) 1==1. Retrieval warming (research_empty share R1 13→2%, R2 20→4%). Auction fair (R1
82 distinct winners top 5%, R2 52 top 6%; no monopoly). Credit ≥ baseline (R1 declare 49% / cred
29% / instances 42%; R2 53% / 36% / 53%). Restamp monotone (R1 credited-set →47, R2 →35).

**A · idea-quality.** Crispness — R1: 4 crisp / 7 borderline / 1 mushy (structural-crisp **4**, holds);
R2: 1 crisp / 13 borderline / 1 mushy (structural-crisp **1**, marginal — the greedy-max-min-area
card mem-17beeb that oscillates 0↔1; R2 still generic-dominated, its top-credit card is generic
step-control). Novelty gate healthy: **0 fail-open** both, no Heilbronn-structural lever rejected;
notably R2's gate now correctly rejects NEW "adaptive step size by acceptance rate" cards — the very
lever mem-57e9's description drifted toward (gate tightened). **0 genuine UNDER-REPORT** (every
0/low-credit case INHERITED / NOT-USED / ATTRIBUTION-SPLIT / used-but-invalid).

**Threads:** (a) structural-crispness flat (R1 4, R2 1-marginal) — bank quality still not tracking
fitness. (b) **mechanism-conflation persists AND generalizes:** mem-57e9 (17 gains) still only 4/17
(24%) SA-implementing children, 76% credit via absorbed Sobol-QMC/non-SA ids — UNCHANGED. NEW
same-class survivors this tick: mem-27d5 (desc "global optimization" but credit via absorbed
mem-7375c8), mem-708498 (desc isotropic/polar but credited children use plain perturbation),
mem-f97bed (desc min-distance but credited children triangle-area-centric). Consolidation
re-enrichment consistently collapses the survivor DESCRIPTION to ONE mechanism that mismatches the
(correctly-unioned) gain_events — a card-description-quality pattern, NOT an integrity fault (credit
rule + union invariant both verified correct). (c) program mega-clusters GREW: R1 GA/greedy/gradient
family 25→~31 (of 39 program cards), R2 greedy family 19→23 (~96%, one mono-cluster). Twins persist:
mem-475086 (insight 0 gains) ≡ program-bb48546e (6 gains) and mem-49148 ≡ program-9b9834b0 — credit
lands on the program twin (ATTRIBUTION-SPLIT, honest). Program cards still undeduped vs insights.

No Telegram (no NEW deviation; k=245 unchanged & already reported). Runs continue to k=500 for
trajectory shape; loop continues hourly. Next tick ~08:45 MSK.

## 2026-07-04 08:59 MSK — HOURLY AUDIT LOOP tick #7 — DEVIATIONS: NONE (k=245 LOCKED; runs DIVERGING post-245)

Both runs LIVE (R1 693967 / R2 693970 cmdline-confirmed, max_mutants=500). Progress: R1 384 progs /
max_iter 385 (~77% of 500), best-so-far **0.03213**; R2 350 progs / max_iter 352 (~70%), best-so-far
**0.02535**.

**k=245 fair-end LOCKED, unchanged from ticks #5/#6:**

| Run | progs iter≤245 | invalid in window | **LOCKED k=245** | best-so-far | vs D 0.0289 | vs A 0.0294 |
|---|---|---|---|---|---|---|
| R1 | 246 | 25 | **0.02366** | 0.03213 | −0.0052 | −0.0057 |
| R2 | 245 | 75 | **0.02337** | 0.02535 | −0.0055 | −0.0060 |

**★ Post-245 divergence is now clear:** R1 best-so-far climbed 0.02976→**0.03213** (now ABOVE both bar
centers) while R2 plateaued 0.02523→**0.02535**. This does NOT change the fair-end verdict (k=245 is
locked below bars for both), but the LATE trajectory shows R1 recovering strongly past the fair window
and R2 flat. R2's low plateau tracks its heavier invalid burn (75/245 invalid in window, 92 total, vs
R1 25/245, 35 total). Watch whether R1's late climb is memory-driven or seed variance — the fair-end
comparison stays the decisive readout; do NOT re-Telegram (already sent tick #5).

**B · machinery — 7/7 PASS both runs, DEVIATIONS: NONE.**
Infra: both alive, 0 NEW errors (only the stale 01:04 API burst, recovered). Gate: R1 79 rejects /
R2 69, **fail-open 0** both. Merge: R1 269 merged / R2 159; union invariant EXACT — R1 survivor
mem-3b7714 (9 absorbed) 5==5 (self 0 + mem-1f8fce 1 + mem-48beb 4); R2 survivor mem-00d5a9 (2 absorbed)
3==3 (self 1 + mem-b89ee 2). Retrieval warming (research_empty R1 11→2.5%, R2 18→3.8%). Auction fair
(R1 99 distinct winners top 4.9%, R2 65 top 5.2%; no monopoly). Credit ≥ baseline (R1 declare 50% /
cred 28% / instances 40%; R2 55% / 37% / 52%). Restamp monotone (R1 credited-set →55, R2 →41).

**A · idea-quality.** Crispness — R1: 3 crisp / 9 borderline / 1 mushy (structural-crisp **3**, down from
4: mem-1699 collinearity-jitter merged out, honest turnover — jitter was never strictly crisp, so 3 is
the honest count); R2: 1 crisp / 14 borderline / 1 mushy (structural-crisp **1**, but IDENTITY UPGRADED —
the crisp card moved from the oscillating farthest-point mem-17beeb to the unambiguous min-area-triplet
coordinated-perturbation card **mem-0a18de7522de**; R2's structural card is now stronger). Novelty gate
healthy: **0 fail-open** both, no Heilbronn-structural lever rejected (min-area-triplet lever mem-0a18de
IS admitted; near-collinearity DETECTION correctly rejected as trivial objective-hygiene). **0 genuine
UNDER-REPORT.**

**Threads:** (a) structural-crispness roughly flat (R1 3, R2 1-but-upgraded); still not tracking fitness.
(b) **mechanism-conflation persists/strengthens:** mem-57e9 (17 gains, all re-homed self_credit=False)
now only **2/9 credited children (~18%) implement SA/Metropolis** — majority earned via absorbed
candidate-gen cards mem-c3d6/mem-86d25. NEW re-enrichment flip: **mem-f97bed description changed
min-distance → "adaptive grid resolution"** yet only 1/3 unioned gain children implement grid-res — the
same consolidation-collapses-to-one-mechanism pattern, honest (union correct) but the injected text keeps
drifting off its reputation basis. mem-27d5 still mismatched, mem-708498 consistent. (c) **program
mega-clusters GREW sharply:** R1 program cards 51→**59**, GA+greedy+gradient hybrid family ≈**49/59 (83%)**;
R2 program cards **31** stable, greedy/gradient(±SA) family ≈**24/31**. Both program banks near-monocultures.
Twins: mem-475086≡program-bb48546e CONFIRMED (credit on program twin 6 vs insight 0); mem-49148≡
program-9b9834b0 REVERSED this tick (insight 1 / twin 0). ATTRIBUTION-SPLIT, honest.

No Telegram (no NEW deviation; k=245 unchanged & reported). Runs continue to k=500; watch R1's late
climb vs R2 plateau for the trajectory-shape readout. Loop continues hourly. Next tick ~09:59 MSK.

## 2026-07-04 10:12 MSK — HOURLY AUDIT LOOP tick #8 — DEVIATIONS: NONE (k=245 LOCKED; R2 late-recovers, both best-so-far now above bar centers)

Both runs LIVE (R1 693967 / R2 693970 cmdline-confirmed, max_mutants=500). Progress: R1 433 progs /
max_iter 432 (~86% of 500), best-so-far **0.03310**; R2 396 progs / max_iter 396 (~79%), best-so-far
**0.03079**.

**k=245 fair-end LOCKED, unchanged from ticks #5–#7:**

| Run | progs iter≤245 | valid in window | **LOCKED k=245** | best-so-far | vs D 0.0289 | vs A 0.0294 |
|---|---|---|---|---|---|---|
| R1 | 246 | 220 | **0.02366** | 0.03310 | −0.0052 | −0.0057 |
| R2 | 245 | 170 | **0.02337** | 0.03079 | −0.0055 | −0.0060 |

**★ Trajectory-shape update — R2 NO LONGER FLAT:** best-so-far this tick R1 0.03213→**0.03310** (+0.0010,
late climb continues) and **R2 0.02535→0.03079 (+0.0054)** — R2 recovered materially and now also sits
above both bar centers post-245. So BOTH runs' late (post-fair-window) best-so-far now exceed the A/D
bars, while the LOCKED k=245 fair-end stays below for both. Reading: the fair-end verdict (memory=full
below no-mem/dynamic at matched k=245) is unchanged and decisive; the late over-bar climb is post-245
and NOT iteration-matched to the bars, so it does not overturn it — but it means the below-bars result
is specifically an EARLY-EFFICIENCY deficit, not a terminal-fitness one. Both runs ultimately reach
competitive fitness; memory just gets there slower per the matched-k window. Do NOT re-Telegram (k=245
decisive readout already sent tick #5; this is trajectory colour, not a new deviation).

**B · machinery — 7/7 PASS both runs, DEVIATIONS: NONE.**
Infra: both alive, 0 new API errors (stale 01:04 burst only). Gate: R1 92 rejects / R2 71, **fail-open 0**
both. Merge: R1 304 merged / R2 208; union invariant EXACT — R1 survivor mem-3cc52b (1 absorbed) 1==1;
R2 survivor mem-0a18de (3 absorbed) 2==2 (self 1 + absorbed 1). Retrieval warming (research_empty R1
6.3%, R2 10.5%). Auction fair (R1 max single card 8% of wins, R2 11%; cold cards still winning ~half).
Credit ≥ baseline, flat (R1 declare 50% / cred 29% / instances 40%; R2 56% / 37% / 50%). Restamp
monotone (R1 credited-set →64, R2 →50).

**A · idea-quality.** Crispness — R1: 4 crisp / 8 borderline / 4 mushy (structural-crisp **3** stable:
mem-731f, mem-8639, mem-b5d7); R2: 3 crisp / 8 borderline / 2 mushy (structural-crisp **3**, up from 1 —
mem-0a18de anchor + mem-e871 Voronoi-min-area + mem-9e36 degenerate-filter now all structural). Novelty
gate healthy: **0 fail-open** both, no Heilbronn-structural lever rejected (novel min-area levers mem-e871/
mem-b5d7/mem-8639 all ADMITTED; generic degeneracy hygiene correctly rejected). **0 genuine UNDER-REPORT.**

**Threads:** (a) structural-crispness now 3/3 (R2 improved). (b) **mechanism-conflation self-resolved via
absorption:** the prior mismatched survivors got MERGED — mem-f97bed + mem-d29c65 absorbed INTO mem-57e9
(whose description broadened to an "adapt step/resolution" umbrella that now loosely fits its heterogeneous
children — less falsifiable but no clean mismatch); mem-27d5 absorbed into mem-17beeb. mem-57e9 strong-SA
share 3/20 (~15%, ≈flat). mem-708498 still consistent. No NEW mismatched survivor. New minor drift watch:
mem-0a18de description near-inverted framing (single-worst-triangle → all-near-bottleneck-vars), mem-6a15
drifted structural→generic. (c) **program mega-clusters near-total:** R1 GA/greedy/gradient family
**62/65**, R2 insertion/greedy-refine family **40/40** (entire program-card population). Insight cards are
pure (codelen=0). Twins confirmed: mem-475086≡program-bb48546e (credit on program twin, 6 vs 0);
mem-49148≡program-9b9834b0 (insight 1 / twin 0). ATTRIBUTION-SPLIT, honest.

No Telegram (no NEW deviation; k=245 unchanged). Runs ~79–86% to k=500; both late-climbing above bars.
Loop continues hourly. Next tick ~11:12 MSK.

## 2026-07-04 11:26 MSK — HOURLY AUDIT LOOP tick #9 — DEVIATIONS: NONE (k=245 LOCKED; both still running, near k=500; R1 structural bank enriches)

Both runs LIVE, NOT yet complete (R1 693967 iter 480 / 480 progs, ~96% of 500; R2 693970 iter 441 /
440 progs, ~88%, ETA ~2h). Best-so-far: R1 **0.03310** (flat vs tick #8), R2 **0.03159** (+0.0008).

**k=245 fair-end LOCKED, unchanged from ticks #5–#8:** R1 **0.02366** (246 progs iter≤245, 220 valid),
R2 **0.02337** (245 progs, 170 valid). Both below bars A 0.0294±0.0018 / D 0.0289±0.0015. Verdict firm.

**B · machinery — 7/7 PASS both runs, DEVIATIONS: NONE.**
Infra: both alive, 300/300 recent LLM ok, 0 new errors. Gate: R1 96 rejects / R2 80/83, **fail-open 0**
both. Merge: R1 353 merged / R2 255; union invariant EXACT — R1 survivor mem-876166 (12 absorbed) 5==5
(self 0 + absorbed 5); R2 survivor mem-17beeb (9 absorbed) 3==3 (self 1 + absorbed 2). Retrieval healthy
(research_empty a minority: R1 67, R2 101). Auction fair (top-1 share R1 3.8%, R2 4.3%; cold cards win
~1729/1369). Credit steady ≥ baseline (R1 declare 50% / cred 29% / instances 40%; R2 56% / 36% / 49%).
Restamp monotone (R1 credited-set →72, R2 →57).

**A · idea-quality.** Crispness — R1: 10 crisp / 7 borderline / 1 mushy (**structural-crisp 9**, up from 3);
R2: 4 crisp / 8 borderline / 2 mushy (structural-crisp **4**). R1's jump is real accumulation of the
min-area/signed-area gradient family {mem-8a4285, mem-a5743d, mem-b13432, mem-b5d7bb, mem-ec310b} plus
init/geometry structural cards {mem-3f2d52, mem-8639f1, mem-c658d3, mem-da1149} — partly rubric
sensitivity, flagged not a deviation. R1 bank is now the structurally RICHER of the two (matches R1's
stronger trajectory). Novelty gate healthy: **0 fail-open** both, no Heilbronn-structural lever rejected;
R2 now correctly rejects further SA variants as prior-known (mem-57e9 already banked). **0 genuine
UNDER-REPORT** (all 0-credit injections INHERITED/NOT-USED, code-verified).

**Threads:** (a) structural-crispness R1 9 / R2 4 (R1 enriched). Two intra-bank CONTRADICTIONS surfaced
(informational): R1 mem-3f2d (break symmetry) vs mem-450d (enforce symmetry); R2 mem-17beeb (impose
symmetry) vs new mem-578e40 (avoid symmetry) — the bank holds mutually-opposing levers, plausibly part
of why injected memory doesn't compound cleanly. mem-0a18de now evicted/merged (framing-inversion moot);
mem-6a15 merged into mem-295d74. (b) **mechanism-conflation persists + NEW survivor:** mem-57e9 SA share
now 6/20=30% (still 70% non-SA children earning credit under an SA-narrow description — the SA card is a
magnet for generic step-adaptation children); NEW mismatch **mem-295d742a** re-enriched to a generic
step-size umbrella after absorbing mem-6a15 (adaptive *sampling-resolution*, a candidate-gen mechanism its
new description no longer names). mem-27d5 stays absorbed into mem-17beeb. (c) **program mega-clusters
near-total:** R1 GA/greedy/gradient 68/71, R2 52/52 (entire population; SA in 39/52). Twin pairing DRIFTED:
program-bb48546e (7 gains) now content-matches mem-49148 (population-seed), not mem-475086; credit
concentrates on the program-card twin bb48546e (7) over insight mem-49148 (1) and program-9b9834b0 (0) —
consistent with the insight's injections being INHERITED (mechanism already in base programs). ATTRIBUTION-
SPLIT, honest.

No Telegram (no NEW deviation; k=245 unchanged). Both runs near k=500 (R1 ~96%, R2 ~88%) — next tick
likely captures R1 completion; loop continues, will produce FINAL comparison + one Telegram when BOTH
finish. Next tick ~12:26 MSK.

## 2026-07-04 12:40 MSK — HOURLY AUDIT LOOP tick #10 — ★ R1 COMPLETED ★ (R2 ~5 short); DEVIATIONS: NONE

**★ R1 COMPLETED cleanly** — PID exited, launch.out finalize: Duration 46432.9s (12.90h), 505 programs,
6027 LLM events, profile_live.html + frontier_fitness.png rendered, no traceback. **R1 terminal
best = 0.03350.** R2 still RUNNING (PID 693970 alive, iter ~495 / 495 progs, ~5 mutants short of 500,
ETA minutes). Loop continues until R2 also completes.

**k=245 fair-end LOCKED, unchanged (final for R1):** R1 **0.02366** (246 progs iter≤245, 220 valid),
R2 **0.02337** (245 progs, 170 valid). Both below bars A 0.0294±0.0018 / D 0.0289±0.0015.

**Terminal-vs-fair picture (R1 final; R2 near-final):**
| Run | LOCKED k=245 | terminal/near best-so-far | vs A center | vs D center |
|---|---|---|---|---|
| R1 (DONE) | 0.02366 | **0.03350** | +0.0041 | +0.0046 |
| R2 (iter~495) | 0.02337 | 0.03302 | +0.0036 | +0.0041 |

So both runs' TERMINAL fitness lands ABOVE the A/D bar centers, while the matched-k=245 fair-end stays
BELOW — confirming the finding shape: rebuilt memory=full has an EARLY-EFFICIENCY deficit (slower to
reach a given fitness within the fair window) but NO terminal-fitness deficit. Caveat unchanged: the A/D
bars are k=245 values from EVOTAB-A-33; there is no terminal (k=500) A/D bar to compare against, so the
"above-bar terminal" is only vs the fair-end bars, not a matched terminal comparison.

**B · machinery — 7/7 PASS both runs, DEVIATIONS: NONE.** R1 final ledger: added 179 / merged 396 /
updated 402 / evicted 14 / rej_harm 4; novelty-rejects 102, **fail-open 0**. R2: added 138 / merged 288 /
novelty-rejects 86, **fail-open 0**. Union invariant EXACT — R1 survivor mem-876166 (14 absorbed) 5==5;
R2 survivor mem-17beeb (9 absorbed) 3==3. Retrieval healthy (research_empty minority both). Auction fair
(top-1 share R1 3.6%, R2 3.8%; cold cards win ~1802/1563). Credit ≥ baseline (R1 declare 49% / cred 29% /
instances 40%; R2 56% / 36% / 50%). Restamp monotone (R1 →77 credited cards, R2 growing).

**A · idea-quality.** Crispness — R1: 6 crisp / 9 borderline / 2 mushy (structural-crisp **6**, down from 9
— consolidation absorbed several structurals into vaguer umbrellas, incl. RESOLVING the mem-3f2d↔mem-450d
symmetry contradiction by folding both into umbrella mem-01243c); R2: 7 crisp / 11 borderline / 2 mushy
(structural-crisp **7**, up from 4 — 3 fresh min-area-triplet structural cards authored this hour). Novelty
gate healthy: R1 102 rejects / R2 91, **0 fail-open** both, no Heilbronn-structural lever rejected.
**0 genuine UNDER-REPORT** (all 0-credit injections INHERITED — mechanism byte-identical in base parent,
code-verified).

**Threads:** (a) structural-crispness R1 6 / R2 7; symmetry CONTRADICTION persists — R2 mem-17beeb (impose
symmetry) ↔ mem-acc203/mem-8e6f56 (break symmetry); R1 new edge-vs-centroid projection contradiction
(mem-24249 project-to-edge ↔ mem-fca62c project-to-centroid) and boundary-vs-interior init (mem-c658d3 ↔
mem-01243c). Bank holds mutually-opposing levers — a plausible reason injected memory doesn't compound.
(b) mechanism-conflation: mem-57e9 SA share **stable ~30%** (20 credits, 70% non-SA children under an
SA-narrow description = over-credit, not under-report); mem-295d742a now MATCHES its gains (3/3 children
implement decaying step-size — the prior mismatch resolved); no NEW mismatched survivor. (c) program
mega-clusters TOTAL: R1 74/75, **R2 67/67 (100%)** — notably R2 has ZERO population/GA programs (all
greedy-construction + gradient/SA-refine) while R1 retains 67 population programs. Twin credit: GA credit
lands on program-bb48546e (7 gains, 7/14 credited) not insight mem-49148 (1/17); local-search-depth
mechanism (mem-475086 / program-9b9834b0) credits NEITHER twin (inherited, undeclared on both). ATTRIBUTION-
SPLIT, honest.

Artifacts: only auto-rendered R1/R2 frontier_fitness.png so far; NO monitor PDF yet (monitor PID 694728
last checked @08:04, hasn't observed R1's completion — its next tick should flag it). No Telegram this
tick (R1 completion is expected, not a deviation; final A/D Telegram + memory update fire when R2 ALSO
completes). Shortening next wakeup to ~20min to catch R2's imminent finish. Next tick ~13:00 MSK.

## 2026-07-04 13:05 MSK — HOURLY AUDIT LOOP tick #11 — ★★ BOTH RUNS COMPLETE — FINALIZATION ★★ DEVIATIONS: NONE — LOOP CLOSED

**★★ R2 COMPLETED cleanly** — PID 693970 exited (12:45 MSK), launch.out finalize: Duration 49641.7s
(13.79h), 505 programs, 6052 LLM events, [SteadyState] Stopped, profile_live.html + frontier_fitness.png
rendered, no traceback. **R2 terminal best = 0.03302** (id 20dfbf29, Gen23). R1 already done (tick #10:
505 progs, terminal 0.03350). **BOTH RUNS DONE → this is the FINAL tick; loop stops re-scheduling.**

**FINAL trajectory comparison (LOCKED k=245 vs terminal, both runs, vs bars A/D):**
| Run | LOCKED k=245 (valid/window) | terminal best (k=500) | k=245 vs A center | k=245 vs D center | terminal vs A/D centers |
|---|---|---|---|---|---|
| R1 | **0.02366** (220/245) | **0.03350** | −0.00574 (−3.19 A-std) | −0.00524 (−3.49 D-std) | +0.0041 / +0.0046 |
| R2 | **0.02337** (170/245) | **0.03302** | −0.00603 (−3.35 A-std) | −0.00553 (−3.69 D-std) | +0.0036 / +0.0041 |
| **bar A** (no-mem) | 0.0294 ± 0.0018 | — | | | |
| **bar D** (dyn-memfix) | 0.0289 ± 0.0015 | — | | | |

**DECISIVE VERDICT (both replicates, stable across all 11 ticks):** rebuilt `memory=full` + novelty gate
lands **BELOW both no-mem bars at the matched k=245 fair-end** — R1 0.02366, R2 0.02337, ~3.5–3.7 D-std
(3.2–3.4 A-std) under. It does NOT reproduce the old stack's D≈no-mem parity at the fair window. BUT both
runs' TERMINAL fitness (0.03350 / 0.03302) climbs ABOVE the bar centers → the deficit is **EARLY-EFFICIENCY,
not terminal**: memory is slower to reach a given fitness inside the fair window but is not capped below
no-mem at k=500. (Caveat: A/D bars are k=245 from EVOTAB-A-33; there is NO terminal (k=500) A/D bar, so the
"terminal above bar" is only vs the fair-end bars, not a matched-terminal comparison.)

**Context stats (characterizing R2's heavier invalid burn):**
| | R1 | R2 |
|---|---|---|
| invalid (−1000) | 52/505 (10.3%) | **99/505 (19.6%)** |
| valid median | 0.01355 | 0.01907 |
| valid mean | 0.01422 | 0.01687 |
R2 burned ~2× the invalid mutants (99 vs 52; 41 vs 7 APIConnectionError, 13.79h vs 12.90h) yet its *valid*
central tendency ran higher — the extra invalid burn does not explain the k=245 gap (both runs land at the
same fair-end within noise).

**B · machinery — FINAL: 7/7 PASS both runs across ALL 11 ticks, DEVIATIONS: NONE.** Both launch.out
finalize clean (no traceback; mid-run tracebacks are all CallValidatorFunction subprocess = invalid mutants).
R1 final ledger: added 179 / merged 396 / updated 402 / evicted 14 / rej_harm 4; novelty-rejects 102,
**fail-open 0**. R2: added 155 / merged 338 / updated 403 / evicted 14 / rej_harm 3; novelty-rejects 96,
**fail-open 0**. Union invariant EXACT (final spot-check): R1 survivor mem-876166 (14 absorbed) banked 5 ==
self 0 + absorbed 5; R2 survivor mem-1f5a71553afa (10 absorbed) banked 20 == self 0 + absorbed 20. Retrieval
healthy (research_empty minority: R1 5.8%, R2 9.4%). Auction fair (top-1 share 4% both; 128/111 distinct
winners; cold cards win). Credit ≥ baseline (R1 inj 72.7% / declare 48.7% / cred 29.1% / instances 40.1%;
R2 72.5% / 56.4% / 35.4% / 48.9%). Restamp monotone (R1 →77 credited, R2 →70).

**A · idea-quality — FINAL: NO DEVIATION.** R1: 6 crisp / 10 borderline / 1 mushy (structural-crisp 6);
R2: 4 crisp / 10 borderline / 1 mushy (structural-crisp 4). Novelty gate: R1 102 rejects / R2 96, **0
fail-open** both; every geometry-mentioning rejection is a *generic* move using geometry as context —
**no min-area-triplet / signed-area / collinearity / boundary-occupancy structural lever rejected in either
run** across the whole experiment. **0 genuine UNDER-REPORT** both runs — every 0/low-credit injection
classifies INHERITED or NOT-USED (child+base code read); distinctive-mechanism sweep found 0 cases of
mechanism-in-child-absent-in-base-and-undeclared. Credit machinery (base∩used, merge re-homing) faithful.

**Leading mechanistic candidates for the early-efficiency deficit (all honest card-quality patterns, NOT
integrity faults):**
1. **Mechanism-conflation.** mem-57e9c88177d8 (SA-narrow description) did NOT survive standalone — it was
   MERGED into survivor mem-1f5a71553afa (12:45 delete = absorbed-id removal; survivor's absorbed_ids lists
   it). Survivor final rep = 29 inj / 20 credited, but only **5/20 (25%) of credited children actually
   implement simulated annealing** — the other 15 are generic perturb/hill-climb children self-declaring the
   broadly-worded card. Reputation honest per credit rule, but the *description* mismatches the mechanisms
   that earned it. Injected memory reads as "SA works" when the reputation was earned by generic moves.
2. **Contradictory-lever bank.** The bank simultaneously holds mutually-opposing levers: R1 edge-vs-centroid
   projection (mem-24249f4 ↔ mem-fca62c6) + boundary-vs-interior init (mem-c658d3 ↔ mem-01243c); R2
   impose-vs-break symmetry (mem-17beeb ↔ mem-0c498e/mem-8e6f56). Injecting opposing levers can't compound.
3. **Program-card monoculture.** Near-total redundancy: R1 69/75 (~92%), **R2 70/70 (100%)** collapse into
   one Heilbronn-constructive-solver cluster (R2 has ZERO population/GA programs). Twin credit lands on the
   concrete program-bb48546e (7 gains, 5 positive, +0.0131) not its over-abstracted insight twin mem-49148e9c
   ("multiple independently evolving lineages" — over-generalized a single-pop GA into an island model → 17
   inj / 1 credit / −0.0092, inert).

**Caveats carried to closeout:** n=2 replicates; A/D bars are k=245 from EVOTAB-A-33 with NO terminal bar;
**must confirm the A/D bars share this exact mutator recipe** (Qwen3-235B-Thinking, num_parents=2,
pipeline=intra_extra_memory) before concluding memory HURTS — a same-recipe no-mem control is the clean
isolation.

**FINAL Telegram SENT** (decisive fair-end verdict + terminal-vs-fair nuance + machinery intact + 3
mechanistic candidates + caveats; R1/R2 frontier_fitness.png attached; no PDF exists). Project memory file
`project_memory_rebuild_full_ab.md` updated; JOURNAL.md FINDING entry appended. **Push to PR #294 remains
HELD** per user. **LOOP CLOSED — no further ScheduleWakeup.**

## 2026-07-04 13:50 MSK — SAME-RECIPE NO-MEM CONTROL launched (N1/N2) — startup CLEAN

The clean isolation the FINAL finding called for. Question: does no-mem AT THE TREATMENT'S EXACT mutator
recipe land at bar A (~0.0294 @245 → memory=full genuinely underperforms) or at ~0.0234 like memory=full
(→ the k=245 deficit is the Qwen3-Thinking/num_parents=2 recipe, not memory)?

- **Runs:** N1 PID 765463, N2 PID 765477; root `outputs/memory_rebuild_nomem_control_2026-07-04/{N1,N2}`;
  `launch_nomem.sh` + `monitor.py` (PID 767648, 1.5h Telegram cadence). From the worktree.
- **Recipe = launch_full.sh with ONLY the memory knob flipped:** `memory=none` (NullMemoryProvider +
  NullPostRunHook, no memory LLM), mutator Qwen3-235B-A22B-Thinking-2507, num_parents=2, storage=disk,
  max_mutants=500, heilbron — all identical to the treatment.
- **Pipeline forced standard (not intra_extra_memory) — correct, not a compromise.** First attempt kept
  `pipeline=intra_extra_memory memory=none`; passed `--cfg job` but **fail-fasted at instantiation**:
  `LiveMemoryRefreshHook needs an IncrementalPostRunHook (got NullPostRunHook) … use pipeline=standard, or
  switch to memory=full`. LESSON: `--cfg job` checks composition, NOT the `${ref:}` instantiation guard —
  intra_extra_memory cannot run no-mem. `pipeline=standard` is the canonical no-mem benchmark (standard.yaml
  line 18) and bar A's recipe: keeps the intra suggester (same as treatment's intra channel), drops only the
  extra bank + live writer hook. So control vs treatment differ by EXACTLY the dynamic memory bank. Failed
  dirs (0 programs) cleared; relaunched.
- **Startup CLEAN both runs:** resolved `.hydra/config.yaml` = NullMemoryProvider + NullPostRunHook +
  IntraMemoryPipelineBuilder; model verified on proxy; single-island max_size=75; MaxMutantsStopper; 5 seeds;
  **no memory bank dir** (memory=none writes no cards); 0 errors/tracebacks; both stepping mutation DAGs
  within ~7 min (`MutationSuggestionStage STARTED`, `intra_signal=absent` = intra live, no extra injection).
- **Compare at:** LOCKED k=245 vs memory=full R1 0.02366 / R2 0.02337 and bars A 0.0294±0.0018 /
  D 0.0289±0.0015. ~13h ETA. Push to PR #294 HELD.

## 2026-07-04 14:40 MSK — COMPUTE-MATCHED comparison vs prior memory runs (corrects earlier framing)

Prompted by the user: the earlier "terminal ABOVE bar centers" nuance was an UNFAIR comparison — it
put the rebuild's k=500 terminal against pre-refactor **memory** (memfix) whose runs were SIGKILL'd
at 220–261 programs and never ran 500 steps. Redone properly: one identical harness over every run's
on-disk programs, **program-count axis** (candidate programs evaluated = compute spent; refactor-
invariant — the `iteration` field's meaning drifted, old runs iteration>progcount, rebuild dense).
Full writeup + trajectory figure: `05_prior_memory_comparison.md` + `fig_mem_vs_prior_compute_matched.png`.
Harness reproduces EVOTAB-A-34 static numbers EXACTLY (core-6 0.0309, tail 0.0229) → method validated.

**Fair common horizon k=220 (memfix S4 cap). Arm-mean cumulative-best @220:**
static core-6 0.0302±0.0010 > no-mem 0.0297±0.0019 > memfix dyn mem=full 0.0284±0.0024 >>
**rebuild mem=full+novelty 0.0235±0.0001** ≈ static-**tail** (proven-detrimental) 0.0224±0.0004.
**The rebuild is the slowest-climbing arm at EVERY k=50→220, not just the end** — a shape result. It
is ~0.0049 below the old dynamic memory it was meant to reproduce, ~0.0062 below no-mem, and rides
in the detrimental static-tail regime. Terminal (k=500) is NOT comparable to any prior memory run
(none ran past ~260).

**Leading hypothesis:** the novelty-admission gate (NEW; absent from all pre-refactor runs) suppresses
common core-6-type cards and admits novel ones — and EVOTAB-A-34 proved the rare "tail" levers are the
detrimental ones. So the gate may be steering the dynamic bank into the tail regime, explaining why the
rebuild underperforms even the OLD gate-less stack. Confounds vs memfix: embedder (MiniLM-L6→arctic),
store arch (shared_memory/GAM→LocalMemoryStore), AND the gate.

## 2026-07-04 14:47 MSK — no-mem control STOPPED; GATE-OFF memory=full pair launched (G1/G2)

User directive: "stop current run and run it WITHOUT novelty filter … more fair comparison with memfix
dynamic mem=full." Rationale is exact: **memfix never had a novelty gate**, so gate-OFF makes the rebuilt
`memory=full` an apples-to-apples reproduction of memfix (remaining diffs = embedder + store arch only),
AND it isolates the leading hypothesis above.

- **Stopped** the same-recipe no-mem control (N1 765463 / N2 765477, ~6 progs each) + monitor 767648 —
  SIGTERM→SIGKILL, verified dead, no strays. (Its question — recipe vs memory — is now secondary; can
  relaunch later.)
- **Launched** gate-off pair: **G1 PID 782817, G2 PID 782822**, root
  `outputs/memory_rebuild_full_nogate_2026-07-04/{G1,G2}`, `launch_nogate.sh` + `monitor.py` (PID 783370,
  1.5h Telegram cadence). From the WORKTREE. Recipe = treatment `launch_full.sh` BYTE-IDENTICAL except
  `+ memory.writer.novelty_admission_gate=false` and fresh root.
- **Startup CLEAN:** `--cfg job` pre-check showed `novelty_admission_gate: false` (key resolves, no
  override error); both resolved `.hydra/config.yaml` confirm gate=false + LocalMemoryStore +
  ReaderMemoryProvider + MemoryWriter + IntraExtraMemoryPipelineBuilder + Qwen3-235B-Thinking; both
  models verified on proxy; fresh bank (MEMORY_STORE_SYNC rebuild ok, card_count 0); single-island
  max_size=75 + StandardEvolutionAcceptor + MaxMutantsStopper; 5 seeds each; 0 errors.
- **Decisive test:** does gate-off climb back to memfix/no-mem parity (~0.028–0.029 @k=220)?
  YES → the novelty gate caused the regression. NO → it's the embedder/store rebuild. ~13h ETA.
  Push to PR #294 HELD.

### 2026-07-04 14:57 MSK — T0 baseline + HOURLY sweep loop armed (metrics + card scan via subagents)

Per user directive "let runs cook; every hour watch metrics and scan cards using subagents." The passive
`monitor.py` (PID 783370, 1.5h Telegram) stays as the anomaly/completion backstop; ON TOP an **hourly
subagent sweep** does the richer analysis the monitor can't: cumulative-best on the program-count axis +
card-quality judgment (novelty / core-6-vs-tail character / contradiction / monoculture).

- **Harness (both persisted at the nogate ROOT):** `sweep.py` (deterministic — program-count-axis
  cumulative-best-valid, valid/invalid/mutant counts, per-program card injection via
  `metadata.memory_selected_idea_ids`, bank card_count, event mix, dag_errors/build_failures peak);
  `sweep_subagent_prompt.md` (the reusable card-scan analyst brief — sources: `llm_io/memory.jsonl`
  librarian authoring calls, `memory/chroma/chroma.sqlite3`, `memory/memory_events.jsonl`).
- **T0 baseline (~15 min in, my own sweep):** G1 & G2 both ALIVE, 5 seeds (4 valid / 1 invalid), 0
  mutants, cumulative-best = 0.00165 (seed), **0 cards** (write path lands ~1.5–2h in per the pre-gate
  pair), read-path already firing (MEMORY_RESEARCH into empty bank), **dag_errors peak=0,
  build_failures peak=0**. Clean warmup. First subagent card-scan is scheduled +1h (nothing to scan
  yet at T0).
- **Cadence:** hourly until both runs hit 500 programs or DIE (~13h). Each tick: run `sweep.py`,
  dispatch the card-scan subagent, relay + append findings here, re-arm +1h. Push to PR #294 HELD.

### 2026-07-04 16:07 MSK — tick #1 (~1h in): both ALIVE, banks filling in the CORE-6 regime (good sign for the gate hypothesis)

Metrics (program-count axis, sweep.py): **G1** 21 progs (18 valid / 3 invalid / 16 mutants), cum-best-valid
**0.00785** @k=11, 6 distinct cards (5 insight / 1 program). **G2** 21 progs (16 valid / 5 invalid / 16
mutants), cum-best-valid **0.01905** @k=8, 4 distinct cards (3 insight / 1 program). Both dag_errors &
build_failures **peak 0**. No stall (5→21 both). Still warmup — fitness far below any bar (this early it's
meaningless; bars are k=220). Fixed sweep.py this tick: mutant count (source=None IS a mutant) + card_count
now = DISTINCT card ids (chroma stores ~3 embed-scope rows/card, so the raw "18 rows" = 6 cards).

Card scan (subagent, G1's 6 cards; G2 had just started writing): **healthy core-6 regime, NOT the
fragmented/contradictory tail regime.** The 6 map ~1:1 to the heilbron good-lever set — barycentric-clamp
boundary projection (mem-2a09), odd-rotational-symmetry init (mem-61e6), closest-pair bottleneck repair
(mem-985c), SA escape (mem-e37f), feasibility-guard move-accept (mem-e206), one composite program
(program-8983 = clamp+SA+centroid-seed). Mechanism-grounded, NOT over-abstract twins; near-duplication LOW;
**zero contradictory pairs**; **no monoculture** (injection spread across 4 distinct cards {2a09×2, 985c×2,
e206×1, 61e6×1}). budget cap = max_cards=1/program but rotates the kept card.

**Read so far:** with the gate OFF the ungated bank is the GOOD common-lever bank the hypothesis predicted —
so the gated rebuild's 0.0235 is NOT (yet) explained by bad card content. Too early for the fitness verdict
(warmup, k=21). The k=220 cum-best is what decides gate-off vs memfix 0.0284. Re-armed +1h. PR #294 HELD.

### 2026-07-04 17:12 MSK — tick #2 (~2h in): core-6 regime HOLDS at 13 cards; card quality does NOT track the fitness gap

Metrics (sweep.py): **G1** 50 progs (45 valid / 5 invalid / 45 mutants), cum-best-valid **0.01510** @k=40,
13 cards (9 insight / 4 program), 36/50 progs carried cards, 10 distinct injected. **G2** 48 progs (41
valid / 7 invalid / 43 mutants), cum-best-valid **0.02435** @k=42, 13 cards (9 insight / 4 program), 32/48
carried, 10 distinct injected. Both dag_errors/build_failures **peak 0**; no stall (both 21→~49);
invalidity G1 10% / G2 15%. Consolidation active (MEMORY_CONSOLIDATION_PASS=4 each; G2 1 EVICTION_SWEEP).

Card scan (subagent, both banks): **core-6 regime HELD as banks grew 6→13.** G1 = clean spread of good
common levers (barycentric clamp+centroid fallback, feasibility guard, symmetry-matched init, closest-pair
anti-cluster, min-triangle bottleneck repair, SA, adaptive perturbation, low-discrepancy init) + 4 DISTINCT
composite program cards; low redundancy; only a lone dtype-hygiene card (1/9) and a SOFT init-symmetry
tension (aperiodic mem-33b5 vs lattice mem-61e6); no monoculture (top mem-2a09 ~12%). G2 = core levers
present but **SA-recipe-redundant** — 3 SA-knob insights + 4 near-duplicate SA program twins (~7/13
SA-flavored); higher redundancy than G1; 1 cap-driven eviction (mem-79c5, a superseded early card, not a
lost good lever); top mem-a51f ~17%, still no single-card monoculture.

**KEY CROSS-CUT:** card diversity does NOT track fitness — G2 is the MORE redundant bank yet is AHEAD on
fitness (0.02435 vs 0.01510). So at this stage the ungated cards look **memfix-quality common levers**, and
the rebuild's depressed ~0.0235 is **not** explained by bad card content — pointing the depression at
retrieval/injection/apparatus (or embedder/store), not what the bank holds. Consolidation is deduping, not
accreting. Still k≈50 (bar is k=220) — fitness verdict pending. Re-armed +1h. PR #294 HELD.

### 2026-07-04 18:19 MSK — tick #3 (~3h in): G1 bank-shrink = healthy dedup; G2 plateau = search difficulty, not memory

Metrics (sweep.py): **G1** 70 progs (62 valid / 8 invalid / 65 mutants), cum-best-valid **0.01814** @k=66
(k50=0.01545), bank **10 distinct (5 insight / 5 program)** — down from 13. **G2** 69 progs (58 valid / 11
invalid / 64 mutants), cum-best-valid **0.02435** @k=67 (k50=0.02245) — FLAT since k=42 (~27-prog plateau),
bank 13 distinct (9 insight / 4 program). Both dag_errors/build_failures **peak 0**; no stall (both
~48→~70); invalidity G1 11% / G2 16%. (Note: cum-best@k50 nudged 0.01510→0.01545 for G1 as an in-flight
early program finalized — expected with concurrent DAGs; settles by final.)

Card scan (subagent, both banks): **(a) G1 13→10 is HEALTHY dedup compression** — ledger shows 49
"librarian merge" near-dup folds + 1 "confidently harmful" eviction (mem-12e2); 5 distinct init strategies
survive (Sobol / perturbed-circular / structured / trisection / circular+min-pair), full core-6 lever set
intact, no monoculture → core-6 HELD, not lever collapse. **(b) G2 plateau is NOT bank-crowding** — despite
SA-recipe redundancy (4 near-clone SA program cards + 3 SA-schedule sibling insights), injection is
dominated by the STRUCTURAL levers (structured-init 13×, bottleneck-repair 12×), the SA clones rank lower
(7/6/3/3×) and are NOT crowding out structural cards; the plateau reads as search difficulty. Harm evictor
working: even a popular attractor (G2 mem-79c5, injected 4×) got culled as confidently harmful.

**Read STRENGTHENS:** the fitness-LEADER (G2, 0.02435) has the LESS diverse / more SA-redundant bank; the
more structurally diverse bank (G1, 0.01814) trails — "card diversity ≠ fitness gap" holds. Ungated cards
stayed good common levers in both (core levers intact, near-dups deduped, harmful culled, no monoculture, no
blocking contradiction) → consistent with the crux that the rebuild's ~0.0235 depression is
retrieval/injection/apparatus, not bank content. Both still below memfix 0.0284 — but k≤70, bar is k=220.
Re-armed +1h. PR #294 HELD.

---

### 2026-07-04 — CODE CHANGE (not in live G1/G2 build): founding gain event + harm-eviction fix

Two commits on `refactor/memory-rebuild` (PR #294), landed AFTER the live G1/G2 A/B was launched — a
follow-up to the "cards are zero-evidence at birth" gap surfaced by the card-dynamics work. Recorded here
because it changes the memory apparatus this experiment evaluates; the next rebuild run should carry it.

- `0aba53b1  feat(memory): seed insight cards with a founding gain event`
- `5de7921e  fix(memory): exclude founding events from harm-eviction`

**Feature.** A freshly-authored *insight* card is born with one **founding** `ContextualGain` carrying the
TRUE signed parent→child fitness delta of the mutation it was distilled from (negated for minimize
objectives → positive always means improvement). `ContextualGain` gains a `founding: bool = False` flag.
The card now bids in the auction on its own origin evidence from the first sweep instead of starting cold;
a card distilled from a regression bids *low*. The founding event is preserved across the from-scratch
restamp in `stamp_gain_events` (it can never be recomputed — its child predates the card) and rides card
merges onto the survivor. Program exemplars keep the zero-evidence-at-birth path.

**Review — round 1 (self via chaos-hacker subagent + codex peer).**
- chaos-hacker confirmed the founding-delta math (orientation, restamp preservation, absorbed-id fold) and
  independently surfaced a real defect: `card.gain_events` feeds BOTH the auction bid (`card_magnitude` via
  `card_stats → block_from_events`) AND harm-eviction (`is_confidently_harmful` via `intro_events` +
  downside posterior). Founding deltas are frequently negative (`extract()` has no improvement filter),
  never decay, and accumulate through merges → a card could be **harm-evicted on its origin delta, before
  use-attribution ever credits it** (empirically 3 negative founding events trip the harm gate). Verified
  against source + an empirical probe.
- codex (round 1) flagged a pre-existing librarian fallback quirk (Finding 1, see disposition below).

**Fix — round 2 (user chose "Exclude from eviction").** `HarmEvictor.should_evict` now routes the card
through `_harm_evidence()`, which strips founding events before the harm verdict; the auction **bid still
reads the full `gain_events`**. Eviction becomes usage-based, and the signed founding delta only
de-prioritizes a regression-born card in the BID (preserving the "TRUE signed delta" property and its
tests). Verified: the only `is_confidently_harmful` caller is inside `should_evict`, and all eviction entry
points (`should_evict`, `sweep`, `admission.admit`, `admission.merge`) route through `HarmEvictor`, so the
strip is total; the bid path (`card_stats(full card)`) is untouched. Test-first: added
`test_founding_events_never_trigger_eviction` (3 losing founding events → NOT evicted; 3 losing *use*
events → evicted) and `test_founding_events_do_not_lower_the_harm_bar` (founding events don't count toward
`harm_min_events`).

**Re-review of the fix (round 2, independent chaos-hacker + codex).** chaos-hacker attacked all five
surfaces (completeness, BD-cell partition leak, `_harm_evidence` correctness, positive-founding asymmetry,
model round-trip/merge/analytics) against the real classes incl. the actual `memory=full` BDProximity
wiring: **0 correctness bugs, fix complete and correct.** It surfaced one LOW test-coverage gap — the two
new tests use `BetaBinomialReputation`, but production `memory=full` wires `BDProximityReputation` as the
harm scorer; the strip holds only because `should_evict` calls `card_stats` with no context (→ `_in_cell`
returns `None` → fallback over already-stripped events), which is untested. Closed by adding
`test_founding_strip_holds_under_bd_proximity_scorer` (founding-only survives / use-only evicts under the
production scorer). 120 write tests + tests/memory green.

**codex Finding 1 disposition (NOT bundled — pre-existing, tracked separately).** A card whose merged form
is harm-rejected in `admission.merge` (target deleted, `""` returned) can be re-admitted as NEW via the
librarian fallback `if not fid and item.decision != "NEW"`. This is a pre-existing USE-event control-flow
quirk, fully decoupled from founding events after the fix (founding no longer causes merge harm-rejection).
Low severity; left out of the founding commit for scope discipline, flagged to the user.

**Docs updated in-PR** (canonical-doc rule): `docs/memory.md` "Cards and gain events" section (founding
seeds the bid, not eviction; usage-based harm) and `gigaevo/memory/README.md` module-map rows for
`cards.py` / `write/stats.py` / `write/eviction.py`.

**codex Finding 1 FIXED (2026-07-04) — typed write-path verdict replaces the `""` sentinel.** User flagged
the dual-meaning `""` return as a code smell: `CardAdmissionGate.merge/admit/bump_provenance` returned `""`
for BOTH a benign no-op (target missing/ineligible/store-fail — caller should re-author) and a harmful
rejection (merged union confidently harmful → target deleted — caller must NOT re-author). The librarian
fallback `if not fid and item.decision != "NEW"` conflated them and re-admitted the harm-rejected card as a
fresh NEW, resurrecting a card the gate had just deleted. Fix: the gate now returns a typed
`WriteResult(outcome: WriteOutcome, card_id: str)` (frozen Pydantic, `.landed` / `.rejected_harm`
properties); the previously-dead `WriteOutcome.DISCARDED` member is repurposed as the benign no-op verdict
(recorded to no ledger row). The librarian routes DUPLICATE/MERGE verdicts through a new `_land_dedup`
helper: `rejected_harm` → drop (logged), `landed` → use `card_id`, benign no-op (`None`/`DISCARDED`) →
re-author as NEW through the novelty gate. `consolidation.py` reads `result.landed`. Test-first: added
`test_merge_ruled_harmful_is_not_reauthored_as_new` (failing → green); all `test_admission.py` assertions
migrated from string returns to `.outcome` / `.card_id`; benign vs harm now asserted distinctly at the gate
level (`DISCARDED` vs `REJECTED_HARM`). 121 write tests + 288 tests/memory + 328 tests/llm green; ruff clean
repo-wide. Committed `06be8a45`.

**Hardening from peer review (2026-07-04) — whitelist the benign no-op.** Two review rounds (self +
codex): round 1 both SHIP, chaos-hacker raised one 🟢 LOW — `_land_dedup` decided re-author-vs-drop by
*blacklisting* `REJECTED_HARM`, so any future non-landed verdict that is not `REJECTED_HARM` (an `EVICTED`
sweep result if ever routed here) would fall through and launder confidently-harmful content back in as a
fresh NEW card — the exact resurrection class the fix closes. Inert today (`sweep()` returns `list[str]`
and discards its `WriteResult`), but the safe form is a *whitelist*: re-author only the two genuinely benign
cases (empty target id, or a `DISCARDED` gate no-op); drop every other non-landed verdict. Added
`WriteResult.benign_noop` (symmetric with `.landed`/`.rejected_harm`) and a truth-table test pinning that
`EVICTED` is not a benign no-op. 122 write + 289 tests/memory green; ruff clean. Committed `395f9d6a`.
Round 2 both SHIP (codex 0 findings, self-review 0 defects) → converged. Both commits pushed to
`origin/refactor/memory-rebuild` (PR #294).

## 2026-07-05 — gate-OFF pair (G1/G2) closeout

- Stopped at user-specified k=245 horizon (not max_mutants=500): SIGTERM 782817/782822 at
  00:35 UTC, 246/263 programs; both exited cleanly (launch.out clean, zero dag_errors).
  Telegram monitor 783370 stopped after the runs.
- No issues during the run window covered here: no proxy stalls, no dag_build_failures,
  cards flowed on both runs (189/246 and 209/263 programs carried injections).
- Convention gap: `bin/archive_experiment.sh` / `experiment_archive/JOURNAL.md` (memory
  conventions) do not exist on this box; disk storage dirs + MANIFEST.md in the run ROOT
  serve as the durable record. No Redis flush involved.
- Results: `06_gateoff_closeout.md` — gate-OFF mean 0.0285 @k=220 = memfix parity;
  novelty gate confirmed as the rebuild regression. Published to YouTrack (EVOTAB-A-21
  child article) + Telegram.
