# Noise-aware evolution: paired replacement gate

Date: 2026-07-11 (night queue item f). Status: **BUILT** (C0+C1, new files
only, uncommitted; dormant until a `pipeline=memory_guided_noise` +
`full7_vectorized` run). User ask: "maybe we can take variance of a single
chain eval into account somehow? … maybe bootstrap mean or whatever. your
call." + generalization ask (OOP/architecture memos consulted) + "shuffling
metadata seems a little ugly … designing new stages seems better" → the
transport was reworked from a mid-pipeline artifact-mover stage to a
validator-stage subclass that strips at source (see C0).

## Problem (measured, not hypothesized)

Single-eval σ on hover full7 fitness = **0.0078** (6 winners × K=5 re-evals,
2026-07-11 study). Archive replacement is a raw point comparison —
`SumArchiveSelector.__call__` returns `new_sum > current_sum`
(`gigaevo/evolution/strategies/selectors.py:51`) on single-eval metrics. The
archive is therefore a max-of-noisy-draws ratchet:

- a truly-equal challenger displaces the incumbent ~49% of the time (measured,
  calibration below), and each swap re-rolls the stored fitness — cells drift
  upward without true improvement;
- a challenger truly worse by 0.007 still wins 24–28% of challenges;
- in-run "records" are curse-inflated (+0.0048 mean, up to +0.012), so
  parent selection and reporting both prefer lucky evals.

Per-sample scores — the raw material for noise-aware decisions — are computed
and thrown away (`problems/chains/hover/full7/validate.py:120-121` keeps only
the mean; `FetchArtifact` stores `None` because validate returns a plain dict).

## Design (minimum viable, behind existing seams)

### C0 — persist per-sample scores (AS BUILT)

1. **Problem side**: `problems/chains/hover/full7_vectorized/` — verbatim
   copy of full7 except `validate()` returns the already-supported tuple form
   (`CallValidatorFunction.parse_output`,
   `gigaevo/programs/stages/python_executors/execution.py:275-287`):
   `return metrics, {"_program_metadata": {"per_sample_scores": [...]}}`.
   full7 itself is untouched (control arm stays bit-identical; no mid-run
   validator edits). The reserved `_program_metadata` namespace is the
   generic contract: any validator can ship program metadata this way.
2. **Framework side**: `ProgramMetadataValidatorStage(CallValidatorFunction)`
   in `gigaevo/programs/stages/validator_metadata.py` pops the namespace from
   the artifact *at eval time* (inside the validator node, right after
   `parse_output`) and writes each field to `program.metadata` (collision
   guard: existing keys never overwritten; non-dict namespace dropped with a
   warning; empty-after-pop artifact → `None`, so `FormatterStage` skips
   exactly as on dict-only returns). The vector therefore never enters the
   artifact stream — no prompt exposure, no stage-payload bloat, nothing for
   downstream consumers to see. Earlier draft (a mid-pipeline
   `ArtifactMetadataStage` on the FetchArtifact→FormatterStage edge) was
   scrapped per user review — strip-at-source needs no edge rewiring and no
   gate exec-dep, because the archive gate already runs after the validator
   node.
3. **Wiring**: `NoiseAwareMemoryGuidedPipelineBuilder`
   (`gigaevo/entrypoint/noise_aware_pipeline.py`, config
   `config/pipeline/memory_guided_noise.yaml`) = MemoryGuided builder +
   `ProgramMetadataValidatorFeature`, which `replace_stage`s the
   `CallValidatorFunction` node with the subclass. Same node name ⇒ DAG is
   wire-identical to `pipeline=memory_guided` (asserted in
   `tests/entrypoint/test_noise_aware_pipeline.py`).
   `Program.metadata` is `dict[str, Any]`, storage-opaque
   (`gigaevo/programs/program.py:131`), and archive/selector code paths fetch
   programs with `exclude=None`, so vectors are visible at compare time.
   Cost: 300 floats ≈ 2.4 KB/program ≈ 0.6 MB/run.

### C1 — paired bootstrap replacement gate (AS BUILT)

Statistic layer: `gigaevo/programs/metrics/paired.py` (bottom-layer package,
importable by evolution/ and memory/ alike — the C4 crediting extension
injects the same comparator):

- `PairedComparison` Protocol (`probability_better(challenger, incumbent)`)
  — the seam; any exceedance-probability statistic plugs in.
- `PairedBootstrap` (frozen dataclass, n_resamples=2000, seed=0): fixed-seed
  fresh RNG per call ⇒ identical resample-index matrix for (a,b) and (b,a) ⇒
  exact antisymmetry p(a,b)+p(b,a)=1; ties counted half so identical vectors
  score exactly 0.5.
- `get_per_sample_scores` / `get_paired_scores`: validated extraction —
  missing/non-numeric/non-1d/empty/non-finite vectors, length mismatch, or
  coherence violation `|mean(scores) − metrics[key]| > 1e-4` ⇒ None (logged)
  ⇒ caller falls back. The coherence guard catches silent contract drift
  between the vector and the gated metric.

Selector: `PairedBootstrapArchiveSelector(SumArchiveSelector)` in NEW module
`gigaevo/evolution/strategies/paired_selectors.py` (behind the existing
`ArchiveSelector` seam; `selectors.py` untouched). Single-key only
(constructor raises on weighted multi-key sums); lower-is-better handled by
negating both vectors.

```
diff = new_scores - current_scores          # paired on shared samples
P    = bootstrap probability(mean(diff) > 0)   # 2000 resamples, seeded rng
accept iff P >= p_accept                       # p_accept: config knob
```

- **Correction from expert memos**: `p_accept = 0.5` does NOT reproduce
  today's rule via the bootstrap (resampling discreteness + tie handling), so
  OFF is implemented *by construction*: at `p_accept=0.5` the comparator is
  never built and `__call__` delegates to `SumArchiveSelector.__call__` —
  bit-identical point rule (tested against the stock selector on a value
  grid). Knob remains dimensionless/self-normalizing.
- Empty-cell fills unchanged (gate never fires — `add_elite` only consults
  the selector when an incumbent exists).
- Fallback contract (explicit, logged, not hasattr-dispatch): any extraction
  failure above → point comparison, i.e. today's rule. Seeds and legacy
  programs just work.
- `ArchiveGate` (`gigaevo/programs/stages/archive_gate.py`) reuses the same
  selector predicate, so expensive-stage skipping stays consistent for free —
  and since the vector lands on metadata inside the validator node, it is
  already present when the gate runs (gate deps:
  `on_success(CallValidatorFunction)`). Re-indexing after behavior-space
  changes (`island.py:339`) also inherits it.
- Cost: numpy bootstrap on 300 paired diffs ≈ 10 ms per contested insertion —
  negligible against minutes-long chain evals. Zero extra LLM calls.

Tests (all green, 2026-07-11): `tests/test_metrics_paired.py`,
`tests/evolution/test_paired_selectors.py`,
`tests/stages/test_validator_metadata.py` (incl. real-subprocess end-to-end:
tmp validate.py → vector on metadata, artifact None),
`tests/entrypoint/test_noise_aware_pipeline.py` (wire-parity vs parent),
`tests/config/test_memory_pipeline_compat.py::test_memory_guided_noise_composes_like_memory_guided`.

### Calibration (measured on the re-eval study, k=1 vs k=1 evals — exactly the in-loop case)

Acceptance rate of a single-eval challenger vs a single-eval incumbent, by
true gap (re-eval means), scratchpad `calibrate_gate.py`:

| true gap (challenger − incumbent) | @0.5 (today) | @0.65 | @0.75 | @0.85 |
|---|---|---|---|---|
| 0 (same program, null) | 0.49 | 0.38 | 0.25 | 0.17 |
| −0.007 (truly worse) | 0.24–0.28 | 0.04–0.12 | 0.00–0.08 | 0.00–0.04 |
| +0.005..0.015 (small true gain) | 0.80 | 0.65 | 0.50 | 0.39 |
| +0.015..0.025 | 0.91 | 0.84 | 0.81 | 0.75 |
| ≥ +0.025 | 1.00 | 1.00 | 1.00 | 0.99 |

**Proposed default `p_accept = 0.75`**: halves null churn (49→25%), nearly
eliminates truly-worse swaps (24–28% → ≤8%), keeps ≥81% of true gains
≥0.015, at the cost of catching only 50% of true +0.005–0.015 gains per
attempt (those recur across generations, so the per-attempt loss compounds
less than it looks — see riskiest link).

### C2 (deferred) — K-eval confirmation of would-be records

In-loop re-evaluation of new global bests needs DAG re-entry machinery;
NOT built now. The offline discipline already adopted (winner claims require
K≥5 re-evals; closeouts with CIs) covers reporting. Revisit only if C1's A/B
shows records still curse-inflated.

### C3 (documentation only) — significant_change

`metrics.yaml significant_change=0.01` ≈ 1.3σ of measured eval noise. It
feeds the auction cold-gain scale (`gigaevo/memory/read/auction.py:292`) and
the suggestion quantum. Leave the value; add the σ context where it is
documented. No mid-campaign change (comparability).

## Causal chain

Persisted per-sample vectors (signal) → replacement decisions test the
paired difference instead of two noisy points (behaviour) → fewer
noise-driven swaps, archive fitness stops ratcheting on lucky draws, stored
elites' point estimates stay honest (metric: replacement count, curse
shrinkage of final winners) → parent selection and best-of-run reflect true
quality (metric: K=5 re-eval mean of final winner non-inferior, curse ≈ 0).

## Riskiest link

If evolution's progress is mostly a staircase of true +0.005–0.01 steps,
gating at 0.75 halves the per-attempt acceptance of exactly those steps and
could slow the trajectory more than honesty is worth. This is falsifiable in
the A/B: population-fitness trajectory + final best (re-evaled) vs control.
If S1/S2 degrade significantly → lower to 0.65 (which still cuts
truly-worse swaps 3×) rather than abandoning.

## A/B protocol (when slots free up; prereg before launch)

- NOISE pair: C0+C1, `p_accept=0.75`, best memory setup at launch time
  (w_nov=0.25 if the novelty experiment ships it), 250 mutants × 2.
  Treatment overrides (on top of the mirrored control launcher):
  ```
  problem.name=chains/hover/full7_vectorized \
  pipeline=memory_guided_noise \
  archive_selector=paired_bootstrap
  ```
  (`archive_selector` is a Hydra group: `point` default in config.yaml,
  `paired_bootstrap` carries p_accept=0.75 — tune via
  `archive_selector.p_accept=0.65`. All single-key algorithm configs bind
  `islands[*].archive_selector: ${archive_selector}`; multi_island's
  simplicity island stays inline because the group is single-key by
  contract. Compose-tested in `tests/config/test_archive_selector_group.py`.)
- Control: the matching memory pair (same everything: `problem.name=chains/hover/full7`,
  `pipeline=memory_guided`, stock point-comparison selector).
- Treatment-consumption check (within ~1h): storage programs carry
  `metadata["per_sample_scores"]` (len 300); DEBUG log shows
  `[PairedBootstrapArchiveSelector] … REJECT` on at least one challenge the
  point rule would have accepted — the gate must change decisions, not just
  code paths.
- Endpoints, variance-disciplined:
  - **M1 (mechanism, primary)**: FRONTIER IMPROVED replacement events per
    run. Predict 25–50% fewer than control; falsified if ≈ control (gate
    inert → check wiring).
  - **M2 (mechanism, primary)**: winner's curse of final best,
    |in-run − K=5 re-eval mean|. Predict ≤ 0.004 both reps (control mean
    +0.0048, worst +0.012).
  - **S1**: final best K=5 re-eval mean non-inferior to control (paired
    per-sample test, bar: no significant deficit).
  - **S2**: population mean fitness of valid programs, mean±SD — descriptive
    trajectory check for the riskiest link.

## C4 — paired idea crediting (extension, same C0 data; separate A/B)

Added 2026-07-11 (user: "make metric more robust for more faithful map
elites selection AND idea crediting").

Problem: a card's gain event is `oriented_delta(child_fit, base_fit)` —
the difference of two single evals (σ√2 ≈ 0.011), thresholded at
`neutral_gain=0.0` into help/harm by the beta-binomial posterior. For
typical true effects (|Δ| ≤ 0.01) the sign is near coin-flip; this is the
mechanism behind the posterior-inflation loophole (neutral cards saturating
p_help ≈ 0.9) and slow harm detection.

Design: in `compute_contextual_gains`, when BOTH child and base carry
`metadata["per_sample_scores"]` of equal length, compute the paired
per-claim delta and store on the event: `p_help` (paired bootstrap
P(mean diff > 0), seeded) and the paired mean delta as `gain`. Reputation's
posterior updates with confidence-weighted soft counts (weight
`|2·p_help − 1|`, direction `sign(p_help − 0.5)`) instead of raw signs.
Fallback: either vector missing → today's scalar rule (explicit, logged).
Credit split for k-card bundles unchanged (credit_weight=1/k).

Predictions (for its own prereg): neutral-card p_help trajectories hover
at ~0.5 instead of drifting to 0.9; harmful-card identification in fewer
events; auction EV bids track re-eval ground truth more closely.

Sequencing: SEPARATE follow-up A/B after C0+C1 ships — one treatment at a
time, else selection-fix and crediting-fix effects are confounded.

## Out of scope (deliberately)

Bayesian posteriors per cell, UCB/optimistic archives, adaptive K re-eval
schedulers, changes to removers/elite-selectors (they act on point
estimates too, but replacement is where the ratchet lives), any change to
the eval budget (paired statistics extract the robustness that is already
paid for; no extra evals, no bigger eval set).
