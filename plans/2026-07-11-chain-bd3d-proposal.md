# 3D chain behavior space: hop_depth × passages_fetched × instr_chars (design, awaiting sign-off)

Date: 2026-07-11 (night queue item e; upgraded to full design on user request
"let us also design proper chain-adapted 3d map-elites while these runs
finish"). Status: DESIGN — needs user sign-off on (a) the axes and (b) the
sequencing decision in §Sequencing before any wiring. Original ask: "design a
new task dependent behavior space so context gets a chance to shine … there
already is chain features but I do not like them; try to come up with a
reasonable 3d behavior space for chains with modest binning (5x5x6 for
instance) … this also requires wiring chain features into dag."

## Data basis

All 1491 valid programs from the six finished hover full7 runs (MEM / EXPL /
NOMEM × R1/R2, 250 mutants each), chain specs parsed semantically (JSON, not
regex). Script: scratchpad `mine_chain_features.py` →
`chain_feature_mining.json`.

## Why the existing chain features fail (measured)

The existing 3D space (`topology_3d_ret.yaml`: dag_depth ×
max_dependency_fan_in × n_retrievals, 5×5×6) occupies **20 of 150 cells**
pooled across all 1491 programs — 13–16 cells per run. Root cause: the axes
are near-duplicates on real populations (Spearman dag_depth ×
max_fan_in **ρ=+0.88**), so the "3D" space is effectively a thin diagonal.
It niches on how the DAG is drawn, not on what the chain does.

## Proposed axes

| axis | definition | bins | data grounding |
|---|---|---|---|
| **hop_depth** | length of the retrieve→reason→retrieve chain: max over tool steps of 1 + #tool steps strictly upstream in the dependency DAG | 5 integer bins: 0,1,2,3,4+ | the strategy axis of HoVer. Fitness by hop: 1 → 0.734 (n=1120), 2 → **0.683 valley** (n=158), 3 → 0.726 (n=99), 4 → **0.766 peak** (n=91). The best region (hop 4) holds 6% of programs; greedy fitness selection must cross the hop-2 valley to reach it — exactly what niching protects. |
| **passages_fetched** | total evidence budget = 7·(#retrieve) + 10·(#retrieve_deep) | 5 bins, dynamic bounds (observed p10–p90 = 20–37, max 41) | breadth strategy; distinguishes thrifty vs wide-evidence chains and shallow-vs-deep retrieval mix (finer than n_retrievals: 16 distinct values vs 6). |
| **instr_chars** | total characters of aim + stage_action + reasoning_questions + example_reasoning across steps + system_prompt | 6 bins, dynamic bounds (p10–p90 = 878–1846, max 11.8k) | the prompt-engineering style axis: terse vs heavily-guided chains. 670 distinct values; the only rich axis orthogonal to topology (all pairwise ρ vs A/B < 0.6). |

5 × 5 × 6 = 150 cells — same capacity as single_island's 150 fitness bins,
directly comparable.

**Occupancy on real populations** (pooled / per-run distinct non-empty cells):

| space | pooled | per-run |
|---|---|---|
| existing dag_depth×fan_in×n_ret | 20 | 13–16 |
| **proposed hop×passages×instr** | **97** | **40–64** |

Pairwise redundancy of the proposed triple: all |ρ| < 0.6 (vs 0.88 in the
existing triple). Runner-up combos considered and beaten on occupancy:
hop×n_ret×instr (60), dag_depth×n_ret×instr (55), hop×passages×n_guided (82).

## Why this gives context a chance to shine

Memory cards carry transferable mechanisms ("generate the second-hop query
from the entity the first hop surfaced", "deep-retrieve only after
disambiguation"). Under fitness-only selection the hop-2 valley kills those
lineages before the mechanism pays off (hop≥2 population share is 23%, and
hop-2 sits 0.05 below hop-1). With hop_depth niched, deep-hop cells are
protected long enough for card-injected mutations to act on them — and the
closeout can measure card efficacy *per hop niche* (with-card delta in
hop≥3 cells), a sharper mechanism endpoint than pooled deltas.

## Interaction with the paired noise gate (user's "awkward" observation)

The paired-bootstrap archive selector adjudicates **occupied-cell challenges
only**: `RedisArchiveStorage.add_elite` consults the selector iff the cell
already holds an elite (`gigaevo/evolution/storage/archive_storage.py:198-200`);
empty-cell colonization is unconditional. What a "cell" is therefore decides
what the gate can protect.

**Under fitness bins** (`single_island_no_distant_parents`: behavior key =
`${primary_key}` = fitness, 150 dynamic bins) the gate is nearly vacuous:

- Every fitness improvement big enough to matter lands in a *different* bin →
  new-cell insert → **never gated**. Lucky single-eval draws (σ≈0.0078,
  ~2–3 bin widths at ~0.003/bin over hover's observed range) jump bins and
  colonize unchallenged — the exact inflation the gate was built to stop.
- The only gated events are within-bin challenges, whose deltas are smaller
  than one bin width *by construction* — sub-noise, so the gate rejects
  nearly all of them. Net effect: within-bin churn drops (prereg P3 still
  reads out), but the fitness endpoint S1 has a broken causal link.

**Under BD3D** cell identity is strategy, not score: fitness varies freely
within a cell, so **every** fitness-based replacement passes through the
selector, and a lucky draw must beat the incumbent on ~300 paired per-claim
scores to displace it. Bonus synergy: pairing gains power from correlated
errors, and same-cell programs share a strategy — the paired test is
strongest exactly where BD3D routes the comparisons.

**Composition is pure config** — no new code beyond BD3D itself:
`chains_bd3d` binds `archive_selector: ${archive_selector}` (as
`topology_3d_ret.yaml` already does) and `memory_guided_noise.yaml:56`
already threads `enable_chain_structural_metrics`. The combined run is
`algorithm=chains_bd3d archive_selector=paired_bootstrap
pipeline=memory_guided_noise problem.name=chains/hover/full7_vectorized
enable_chain_structural_metrics=true`.

## Sequencing (DECIDED 2026-07-11)

**User decision: combined.** BD3D + paired noise gate together as the new
baseline foundation, with **memory vs no-memory** as the arm contrast
("this seems like an overall more reasonable setup rather than having
150-bin fitness space which ignores domain"). The staged
noise-on-fitness-bins launch (`prereg_noise_gate_20260711.md`, task #20;
staged but never launched) is SUPERSEDED.

- Both arms share `algorithm=chains_bd3d` + `archive_selector=paired_bootstrap`
  + `problem.name=chains/hover/full7_vectorized` +
  `enable_chain_structural_metrics=true`; the one-treatment rule is satisfied
  by the arm contrast itself (memory on/off), and backend contention is fair
  because all four runs launch together under identical conditions.
- MEM arm: `pipeline=memory_guided_noise memory=full memory/write=live` — the
  campaign's memory recipe on the new foundation.
- NOMEM arm: `pipeline=guided_noise memory=none` — requires a new
  `NoiseAwareGuidedPipelineBuilder` + `config/pipeline/guided_noise.yaml`
  (guided DAG + metadata-routing validator), mirroring the campaign's
  no-memory convention (`pipeline=guided memory=none`,
  cfg_nomemory_fitness_metrics_20260709_164213).
- Comparisons vs the old fitness-bin pairs (MEM 20260710_041404, NOMEM
  20260709_164213) are observational only — the space change confounds them;
  the preregistered contrast is memory vs no-memory within this experiment.

## Wiring plan — IMPLEMENTED 2026-07-11 (all behind existing seams; uncommitted)

1. DONE — `ChainFeatureExtractor`
   (`gigaevo/evolution/scheduling/feature_extractor.py`) computes the three
   features by parsing the spec with the CARL parse-layer models
   (`problems.chains.types.RawChainSpec`; guidance fields from
   `STRUCTURED_FIELDS`) via a lazy import (mmar-carl is an optional
   3.12-gated extra). Non-JSON / schema-invalid specs yield zeros — no
   regex fallback (user redirect: derive schema from CARL classes, not
   hand-rolled rules). Per-tool k's (`retrieve`=7, `retrieve_deep`=10) stay
   as an extractor map: they are call-site literals in each problem's
   `validate.py`, no class-spec home exists.
2. DONE — three keys added as `SEMANTIC_CHAIN_METRIC_KEYS` folded into
   `STRUCTURAL_METRIC_KEYS` (`gigaevo/programs/stages/chain_structural.py`);
   stage description updated to 7 metrics. Superset is harmless to existing
   presets; the stage defaults off.
3. DONE — config-time enforcement is generic, not a chain-specific run.py
   guard (user redirect: no domain hardcoding in general run.py). Algorithm
   presets declare `algorithm_requires: {<dotted.cfg.path>: <value>}` in
   yaml (default `{}` in `config/algorithm/_base.yaml`);
   `validate_algorithm_requirements` (`gigaevo/config/validation.py`, called
   from `run.py`) compares via `OmegaConf.select`. `chains_bd3d` requires
   `enable_chain_structural_metrics: true` + `program_format.id:
   json_document`; `topology_3d`/`topology_3d_ret` gained the
   structural-metrics requirement too (fixes their latent
   KeyError-at-first-insert footgun).
4. DONE — `config/algorithm/chains_bd3d.yaml`, drop-in mirror of
   `single_island_no_distant_parents` island machinery with the new keys,
   bounds [0,5]/[0,45]/[0,2500], 5/5/6 resolutions, `dynamic: true`. Keeps
   `archive_selector: ${archive_selector}`.
5. DONE — NOMEM arm plumbing: `NoiseAwareGuidedPipelineBuilder`
   (`gigaevo/entrypoint/noise_aware_pipeline.py`) +
   `config/pipeline/guided_noise.yaml` (`routes_program_metadata: true`, so
   the generic paired-selector guard passes).
6. DONE — tests: 10 semantic extractor tests on schema-valid specs
   (hop-closure, passage arithmetic, `<none>` handling, schema-invalid →
   zeros; skipped when mmar_carl absent) in
   `tests/evolution/test_scheduling.py`; 6 compose tests of the
   `algorithm_requires` mechanism in
   `tests/config/test_structural_behavior_keys.py`; guided_noise pairing in
   `tests/config/test_archive_selector_group.py`. 168 config+scheduling
   tests green, lint clean.
7. Timing constraint held: gigaevo/ modules are imported once by live runs
   (safe to edit); problem-side files were not touched while NOVAUC runs.

## Blast experiment (after sign-off; ladder per §Sequencing A)

- Step 1 pair: best memory setup at launch time + `algorithm=chains_bd3d` +
  `enable_chain_structural_metrics=true`, 250 mutants × 2 reps, launcher
  mirrored from the memory baseline verbatim except these overrides.
  Control: MEM pair 20260710_041404 (fitness-binned).
- Step 2 pair: step 1 + `archive_selector=paired_bootstrap` +
  `pipeline=memory_guided_noise` + `problem.name=chains/hover/full7_vectorized`.
  Control: step 1 pair. Prereg for this step reuses
  `prereg_noise_gate_20260711.md` endpoints P1–P3/S1/D1 re-baselined on BD3D.
- Endpoints for step 1 (variance-disciplined, prereg before launch):
  - **M1 (mechanism)**: distinct occupied cells per run. Predict ≥35
    (control on the old 3d space: 13–16; same populations on the new axes
    already show 40–64).
  - **M2 (mechanism)**: share of valid programs with hop_depth ≥ 3.
    Predict ≥ 1.5× control (control pooled: 12.7%).
  - **S1**: best-of-run, K=5 re-eval mean ± CI vs control pair. Prediction:
    non-inferior; upside case = beats control (hop-4 region mean 0.766 vs
    global 0.733) — but see riskiest link.
  - **S2**: card efficacy by hop niche — with-card per-mutation delta in
    hop≥3 cells vs hop≤1 cells (the "context shines" endpoint).
  - **G1 (step 2 only)**: fraction of archive inserts hitting an occupied
    cell (= gate-consult rate). Predict ≫ fitness-bin runs' rate; if G1 is
    low, BD3D occupancy is too sparse for the gate to matter and step 2
    reverts to a churn-only readout.

## Causal chain

Niche on strategy axes instead of DAG-drawing counters (signal) → hop-2/3
lineages survive the fitness valley, deep-hop and guidance-style diversity
persists in the archive (behaviour: occupancy, hop-share) → evolution
reaches the hop-4 region more often and cards transfer mechanisms into
protected niches (metric: M2, S2) → higher true best fitness (metric: S1
with K=5 re-eval CIs). Step 2 adds: occupied-cell challenges now dominate
inserts (G1) → paired gate filters noise-driven replacements where they
actually occur → replicable-fitness gains (step-2 S1).

## Riskiest link

The hop-4 fitness peak (0.766, n=91) is **observational** — chains that got
good may have grown deep, rather than depth causing quality. If the hop-2
valley is intrinsic (deeper chains genuinely worse until very refined),
protected hop-2/3 cells hold weak elites and ~2/5 of the archive budget is
spent on a region that never pays off within 250 mutants. Falsified if M2
rises but hop≥3 elites' re-eval fitness stays below hop-1 elites at run end
— that outcome says the axis is a cost, not a ladder, and the next lever is
a different strategy axis (e.g. n_guided_llm_steps), not more bins.

## Explicitly not proposed

Changing fitness, archive size (island_max_size stays 75), elite/migrant
selectors, or memory config in the same experiment. The noise-aware selector
is NOT blended into step 1 — it arrives only as step 2's single treatment on
top of a settled BD3D baseline.
