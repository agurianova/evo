# Static-lever prompt baseline — issues log

Append-only. One dated entry per issue encountered (infra, config, anomaly),
with resolution. Plan: `../static_lever_prompt_baseline_plan.md`.

## 2026-07-02 — build phase

- No issues. Provider + configs + lever files built and verified pre-launch:
  38 memory tests + `tests/integration/` green, `--cfg job` composition
  correct, both lever files parse to 6 blocks (length mismatch 7.3%, within
  the ±10% gate).
- Known upstream config drift found during design (not an issue of this
  experiment, fixed on this branch): `config/memory/writer/tracker/librarian.yaml`
  pinned `consolidation_eps: 0.05` contradicting the DedupPolicy default 0.2;
  irrelevant here since `memory=static` mounts no writer.
- Plan caveat corrected (user-caught): the plan briefly claimed arm A
  (`pipeline=standard`) lacks the intra/suggester apparatus. Wrong —
  `standard` wires `IntraMemoryPipelineBuilder`, so IntraMemoryStage +
  MutationSuggestionStage run in all four arms (the apparatus-free builder is
  `pipeline=legacy`). Only the extra channel (MemoryContextStage →
  `memory_cards`) differs, which strengthens B/C-vs-A: it is a clean
  content(+slot) contrast, not an apparatus confound.

## 2026-07-03 — close / analysis

- **Early stop (intentional):** all 4 runs SIGTERM'd cleanly at 345–384 mutants
  (target 500) to free the proxy for the memory-rebuild smoke. Storage intact
  post-stop (`gigaevo top` stable, no corruption). Fair-end analysis pinned at
  k=245 (checkpoint all four arms + both external bars share); both C runs had
  already plateaued by k≈250, so the untaken 120–150 mutants would not move the
  B–C verdict.
- **C6-2 invalidity anomaly:** 42.5% invalid (223/388 valid) vs 11–19% in the
  other three runs (C6-1 11.3%, TL-1 19.1%, TL-2 14.4%). Cause not root-caused
  (higher mutator rejection under the core-6 block on this seed; no infra death —
  PID alive throughout, memory_used_rate=1.0). Impact: drags B's arm mean down
  and widens its error band, yet C6-2 still reached 0.0292 (≈ no-mem) so the
  core-6 ≥ no-mem conclusion is robust; C6-1 (clean, 0.0327) is the unconfounded
  core-6 estimate. Flagged, not blocking.
- **n=2 per arm** (budget 8→4, pre-registered): B>C is unambiguous by
  effect-size (d=5.85) and 4/4 cross-pairs, but the exact 2v2 permutation floor
  is p=0.33 — no powered p-value is obtainable at this n. Reported as effect-size
  + checkpoint-wins per feedback conventions.
