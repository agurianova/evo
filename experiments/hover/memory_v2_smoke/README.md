# Memory v2 HoVer Smoke

This is the bounded real-problem gate for the first memory-v2 iteration. It
uses disk program storage, `chains_bd3d` MAP-Elites, paired-bootstrap archive
replacement, the vectorized HoVer evaluator, live v1 card writing, and the v2
causal reader.

The pre-run technical and ELI5 explanation is in
`docs/memory_v2_bayesian_system_report.md`.

Run from the memory-v2 worktree:

```bash
MAX_MUTANTS=16 bash experiments/hover/memory_v2_smoke/run.sh
```

The launcher starts with an empty card bank and an empty causal ledger so the
smoke exercises authoring, admission, later selection, and credit end to end. It
refuses to reuse a checkpoint containing cards, evidence, or a write ledger. It
uses `google/gemini-3.5-flash` through OpenRouter for both mutation and memory
librarian calls, with minimal reasoning and without the deferred `flex` tier; the
vectorized HoVer evaluator uses `LOCAL_LLM_PROXY` from the primary checkout's
`.env`. The launcher sources that file without copying secrets into the worktree.
Override `LLM_CONFIG`, `LLM_BASE_URL`, `MODEL_NAME`, `MEMORY_LLM_CONFIG`,
`MEMORY_LLM_BASE_URL`, `MEMORY_MODEL_NAME`, `HOVER_CHAIN_URL`, `RUN_DIR`, or
`MEMORY_SEED` as needed. `OFFER_PROBABILITY` defaults to the balanced validation
value `0.50`; normal v2 runs use `0.70`. `CONFIG_ONLY=1` performs only the Hydra
composition gate.

Analyze an old bank independently of this empty-bank smoke:

```bash
python experiments/hover/memory_v2_smoke/analyze_bank.py \
  --cards /path/to/checkpoint/cards.json \
  --write-ledger /path/to/checkpoint/write_ledger.jsonl \
  --output-dir outputs/memory_v2_seed_bank_analysis
```

The bank report treats v1 gain events as descriptive lifecycle data only. They
are never written to the v2 causal ledger or used to warm the v2 posterior.

The analyzer treats `<run>/memory/memory_v2_selection_evidence.sqlite3` as the causal
source of truth. It validates SQLite and payload hashes, policy mass, conditional
and joint propensities, overlap, finite-world proposal uncertainty, safety-set
membership, bounded outcomes, optimizer diagnostics, immutable parent/reward
contracts, terminal timestamps, and evidence accounting. It writes CSV traces,
`summary.json`, `report.md`, `memory_v2_dashboard.png`, and
`offer_calibration.png` under `<run>/memory_v2_analytics`. The gate also requires
nonempty candidates, proposals, both offer arms, eligible closed terminals, and at
least one posterior update. Conditional-offer DR reward/risk sensitivity is written
to `ope_report.json`, `ope_trace.csv`, and `ope_sensitivity.png`.

## Historical v1 shadow replay

Historical v1 runs do not contain the immutable v2 assignment/outcome ledger.
Use the separate fail-fast replay tool to reconstruct decisions from selection
events, ContextStage results, mutation links, and frozen child metadata:

```bash
python experiments/hover/memory_v2_smoke/replay_v1.py \
  --run-dir /path/to/historical/MEM_R1 \
  --output-dir outputs/memory_v2_historical_replay
```

The tool aggregates all children under their original assignment episode and
uses selection plus ContextStage logs as the assignment source of truth. It
does not trust v1's mutable `memory_no_card_control` field. It writes an
assignment funnel, reconstructed-control confusion matrix, clustered outcome
sensitivities, prior/shadow posterior comparisons, prefix replay, conditional-
offer counterfactual sensitivity, CSV traces, and a Markdown report.

Every reconstructed row is marked `training_eligible=false`; the tool never
opens or writes a v2 causal ledger. Historical proposal propensities, frozen
q-hats, exact archive state, and revision snapshots are unavailable, so the
results cannot support full-policy IPS/SNIPS/DR, production posterior updates,
or card promotion. They are intended for integrity checks and posterior
numerical stress testing only.
