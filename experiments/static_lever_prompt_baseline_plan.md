# Static-lever prompt baseline — plan (2026-07-02)

Experiment #1 from the memory deep-analysis shortlist (EVOTAB-A-33 /
`memory_deep_analysis_2026-07-01/FINDINGS.md`). Tests whether the *content* the
memory system distills has any value when injected directly, stripped of the
whole dynamic apparatus (writer, embedder, auction, reputation).

## Question

Dynamic memory ended at no-mem parity (fair-end Δ −0.0004, perm p=0.83). The
deep analysis localized the leak to *redundant content*: 46% of the pool is 6
universal levers every seed rediscovers unaided, while the residual lift sits in
tail levers (+0.0021 matched) that appear in only 1–2 of 4 banks each. If that
diagnosis is right, injecting the core-6 as a fixed prompt block buys nothing,
and injecting the tail levers — knowledge a fresh seed mostly *won't* discover —
buys ≈ +0.002.

## Causal chain (signal → behaviour → metric)

1. **Signal**: a curated block of lever recipes (actual bank card text, distilled
   one recipe per lever) rendered into the same memory slot the dynamic system
   uses. Under `pipeline=intra_extra_memory` that slot is
   `MutationSuggestionStage.memory_cards`: the suggester LLM sees the card
   blocks and distills them into the insights the mutator receives — the
   mutator never sees card text verbatim. This mediation is byte-identical to
   arm D's injection path, so B/C-vs-D isolates content; it also inherits D's
   known dilution mode (suggestion-stage card-obligation can displace native
   insights).
2. **Behaviour**: every child's suggester conditions on mechanism recipes and
   passes them through as mutation directions. For the tail block this
   supplies tactics absent from the seed's own trajectory (13/28 levers are
   seed-unique), removing the discovery latency dynamic memory paid (tail lift
   was late-loaded: +0.0044 late vs −0.0003 early). For the core-6 block it
   supplies only what the seed rediscovers anyway.
3. **Metric**: cumulative-best fitness by per-program `iteration`
   (`final_iter_compare.py` harness): checkpoint table every 25 iters, fair-end
   MW + Welch, exact C(8,4) trajectory permutation per arm pair.

**Riskiest link**: 2 → 3, adherence. Dynamic cards were applied ~66% of the time
when injected one-at-a-time with an auction rationale; a static 6-recipe block
may be skimmed or ignored. Mitigation: render each lever as a separate card-shaped
block (same visual grammar as dynamic injection), and audit `llm_io` logs at
smoke — the lever blocks appear in the **suggestion-stage** prompts (not the
mutator prompts; see step 1): verify the 6 blocks render there and at least
one downstream suggestion/mutation cites a lever mechanism. If the suggestion
LLM call fails it degrades to empty insights while exposure metadata still
records the selection — same failure mode as arm D; watch the smoke logs for
`MutationSuggestionStage` warnings. Second risk: distillation quality —
mitigated by quoting the banks' own best recipe text per lever (recipes beat
principles, per the card-dynamics study), not paraphrasing into abstractions.

## Arms

| Arm | memory | levers file | runs | status |
|---|---|---|---|---|
| A no-mem | `memory=none`, pipeline=standard | — | NM1–4 | DONE (bar 0.0294±0.0018 @245) |
| B static core-6 | `memory=static` | `levers_core6.md` (L1,L3,L4,L6,L11,L13) | C6-1..4 | to launch |
| C static tail | `memory=static` | `levers_tail.md` (L9,L16,L17,L19,L22,L24) | TL-1..4 | to launch |
| D dynamic | `memory=full` (memfix stack) | — | memfix S1–4 | DONE (0.0289±0.0015 @245) |

Only B and C launch: 8 runs, heilbron, 500 mutants each, same box/proxy as
memfix. Both lever files are length-matched (±10%) so B-vs-C is free of the
prompt-length confound; A-vs-{B,C} carries the block's token cost by design
(that IS the treatment).

## Mechanism (built in this PR)

- `StaticLeverMemoryProvider` (`gigaevo/memory/provider.py`) behind the existing
  `MemoryProvider` ABC: loads the levers file once, splits on `---` separators
  into card-shaped blocks, returns the same fixed `MemorySelection` for every
  child (`card_ids` = `static:<stem>:<n>` so gain-event stamping still works for
  post-hoc analysis). Accepts-and-ignores the assembler's component kwargs.
  Fails LOUD at build on a missing/empty file — a typo must not silently run a
  no-mem arm (silent-treatment-fallback bug class).
- `config/memory/static.yaml` + `config/memory/reader/provider/static_levers.yaml`
  (`levers_file: ???` — mandatory). Reader on, writer off, no backend/embedder/
  memory-LLM mounted: zero memory-LLM billing.
- Lever files under `experiments/static_lever_prompt_baseline/`. Each block is
  the verbatim description of the best-evidenced final-bank card that states the
  lever's recipe standalone (ranked by `n_events`/`posterior_mean` from
  `memory_deep_analysis_2026-07-01/csv/cards.csv`; cards with run-config
  numerics like point counts were skipped). Length-matched at 7.3% by chars
  (1919 vs 1778), 4% by words. Provenance:

  | file : block | lever | source card |
  |---|---|---|
  | core6:1 | L1 bottleneck-target | S1/mem-d45b184a49a5 (13 ev, 0.67) |
  | core6:2 | L3 thermal-escape | S4/mem-c7f8189e5887 |
  | core6:3 | L4 dispersed-init | S1/mem-2a62f3633b18 (5 ev, 0.71) |
  | core6:4 | L6 project-to-feasible | S1/mem-19db021b05a0 (9 ev, 0.64) |
  | core6:5 | L11 multi-start | S4/mem-7c9f8a8cc691 (3 ev, 0.60) |
  | core6:6 | L13 adaptive-step | S4/mem-631b81ff96e8 (4 ev, 0.50) |
  | tail:1 | L9 symmetry-enforce | S4/mem-c496fe3d4e9c |
  | tail:2 | L16 multi-bottleneck | S3/mem-fca931c038ef (5 ev, 0.57) |
  | tail:3 | L17 global-move | S4/mem-1fcccb35b910 |
  | tail:4 | L19 greedy-construct | S4/mem-775c3d9006a7 |
  | tail:5 | L22 incremental-eval | S4/mem-288eedff9d6a (3 ev, 0.60) |
  | tail:6 | L24 jacobian/coord-choice | S4/mem-3493a84bbf12 (9 ev, 0.64) |

## Launch recipe (mirror memfix verbatim; delta = memory group only)

```bash
python run.py problem.name=heilbron storage=disk pipeline=intra_extra_memory \
  num_parents=2 memory=static \
  memory.provider.levers_file=$PWD/experiments/static_lever_prompt_baseline/levers_core6.md \
  post_step_hook=null \
  model_name=Qwen3-235B-A22B-Thinking-2507 llm_base_url=http://10.232.30.185:4000/v1 \
  max_mutants=500 pipeline_builder.fresh_context_reorder=true \
  hydra.run.dir=outputs/static_levers_2026-07-02/C6-1
```

Dropped vs the memfix CLI: the `memory/common/*` and `memory/reader/*` leaf
overrides and `memory.provider.shortlist_k` (memory=full leaves that don't exist
under `memory=static`). `post_step_hook=null` replaces
`post_step_hook.refresh_every=10` and is MANDATORY: the pipeline's
`LiveMemoryRefreshHook` needs a writer-enabled tracker and fails fast on the
static preset's `NullPostRunHook` (there is no bank to refresh). Everything
else identical. Tail arm swaps the levers file and run dir. Smoke: 1 run ×
~10 mutants; verify via `llm_io` that the 6 blocks render in the
**suggestion-stage** prompt and at least one suggestion/mutation cites a lever
(see riskiest-link section — the mutator prompt never carries card text).

## Predictions (registered before launch)

| Comparison | Prediction | Kills / confirms |
|---|---|---|
| B core-6 vs A no-mem | Δ fair-end within ±0.001 (parity) | Confirms redundancy: dominant memory content was never worth injecting |
| C tail vs A no-mem | Δ ≥ +0.002; lift onset visibly earlier than dynamic (by iter ~100–150, vs late-loaded in D) | Confirms content-novelty value causally; the +0.0021 residual lift was real |
| C tail vs B core-6 | C > B, ≥3/4 seed-pairs at fair end | The decisive internal contrast (length-controlled) |
| C tail vs D dynamic | C ≥ D | Static tail ≥ full dynamic stack ⇒ apparatus adds nothing over content |
| B core-6 vs D dynamic | B ≈ D | Both ≈ no-mem |

If C ≈ B ≈ A: the exploratory tail lift was noise → content injection is dead
as a lever; next experiment shifts entirely to #2 (mechanism-level novelty-gated
ADMISSION for dynamic memory). Trajectory *shape* counts, not just endpoint:
report the checkpoint-wins column, per feedback conventions.

Note on the A rows: `pipeline=standard` (arm A) wires the same
`IntraMemoryPipelineBuilder` base, so IntraMemoryStage + MutationSuggestionStage
run in ALL four arms. The only structural delta A → B/C is the extra-memory
channel — MemoryContextStage feeding the lever blocks into
`MutationSuggestionStage.memory_cards` (an optional input, absent in A) — and
that channel plus its content IS the treatment. `post_step_hook=null` matches
A's default (`config/constants/evolution.yaml`), so no hook difference either.
B/C-vs-A is therefore a clean content(+slot token cost) contrast; C-vs-B
additionally controls prompt length.

## Analysis & closeout

Reuse `final_iter_compare.py` generalized to 4 arms; same figures (per-run +
mean±std bands). Issues log: `experiments/static_lever_prompt_baseline/04_issues_log.md`.
Archive via `bin/archive_experiment.sh` before any flush; JOURNAL entry at launch
and at finding; publish under EVOTAB-A-21 next to EVOTAB-A-33.
