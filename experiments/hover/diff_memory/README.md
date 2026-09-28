# HoVer Diff-Memory Runs

This package launches two independent copies of the HoVer CARL tool-diff setup
with external memory enabled.

## What It Runs

Both copies use:

- Problem: `chains/hover/full7`
- Pipeline: `memory_guided`
- Program format: `json_document`
- Mutation: `carl_with_retrieval_tools`
- Mutation LLM: `Qwen3-235B-A22B-Thinking-2507`
- Memory LLM: `Qwen/Qwen3-235B-A22B-Instruct-2507`
- Chain executor model: `Qwen/Qwen3-8B`
- Memory mode: `memory=full memory/write=live`
- Algorithm: `topology_3d_ret`
- Chain topology metrics: `enable_chain_structural_metrics=true`

The two copies are independent at the memory layer:

- R1 writes and reads `SHARE_HOVER_DIFF_MEMORY_1`
- R2 writes and reads `SHARE_HOVER_DIFF_MEMORY_2`

## Launch

```bash
cd /mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal
OPENAI_API_KEY=sk-gigaevo ./experiments/hover/diff_memory/launch.sh
```

Useful overrides:

```bash
DRY_RUN=1 ./experiments/hover/diff_memory/launch.sh
MAX_MUTANTS=500 ./experiments/hover/diff_memory/launch.sh
HOVER_CHAIN_URL=http://10.232.22.184:8000/v1 ./experiments/hover/diff_memory/launch.sh
RUN1_MEMORY_BANK=$PWD/SHARE_HOVER_DIFF_MEMORY_A \
RUN2_MEMORY_BANK=$PWD/SHARE_HOVER_DIFF_MEMORY_B \
  ./experiments/hover/diff_memory/launch.sh
```

`DRY_RUN=1` performs endpoint smoke checks and writes the resolved Hydra configs
without starting long-running evolution processes.

By default, chain execution goes through the LiteLLM proxy at
`http://10.232.24.68:4000/v1`, which advertises `Qwen/Qwen3-8B`. The launcher
also probes the direct backend endpoints on `10.232.22.184:8000-8007` before
starting runs, so stale proxy/backend wiring fails before spending mutation
tokens.

## Outputs

After launch:

- `latest.env` records the timestamp, model routes, run dirs, banks, and PID file.
- `pids_<timestamp>.txt` records run labels, PIDs, logs, output dirs, and banks.
- `cfg_R1_<timestamp>.yaml` and `cfg_R2_<timestamp>.yaml` are Hydra resolved
  config checks.
- Launcher stdout/stderr logs are under `experiments/hover/diff_memory/logs/`.
- Main evolution logs are under each Hydra output directory.
- Hydra run outputs default to `outputs/hover-diff-memory-<timestamp>/R1` and
  `outputs/hover-diff-memory-<timestamp>/R2`.

## Quick Status

```bash
source experiments/hover/diff_memory/latest.env
cat "$PIDS_FILE"
tail -n 80 experiments/hover/diff_memory/logs/R1_${TS}.log
tail -n 80 experiments/hover/diff_memory/logs/R2_${TS}.log
ls "$RUN_ROOT"/R*/evolution_*.log
```

The key resolved-config checks are:

- `pipeline.id: memory_guided`
- `program_format.id: json_document`
- `mutation_operator: StructuredDiffMutationOperator`
- `allowed_changes: AllowedToolChainChanges`
- `memory.capabilities.read: true`
- `memory.capabilities.write: true`
- `memory.llm.models.0.model: Qwen/Qwen3-235B-A22B-Instruct-2507`
- `dag_blueprint.nodes.ChainStructuralMetricsStage` exists, so
  `dag_depth`, `max_dependency_fan_in`, and `n_retrievals` are populated before
  archive admission.
