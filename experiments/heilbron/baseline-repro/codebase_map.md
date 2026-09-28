# Codebase Map — heilbron/baseline-repro

Pure replication of adversarial/heilbron-prover (PR #183). No new code.

## Entry Points

- **Constructor**: `problems/heilbron_adversarial/pop_a/` (Population A)
- **Improver**: `problems/heilbron_adversarial/pop_b/` (Population B)
- **Pipeline**: `config/pipeline/adversarial_coevo.yaml`
- **Engine**: generational (default `EvolutionEngine`)

## Hydra Wiring

Each run uses:
- `problem.name=heilbron_adversarial/pop_a` or `pop_b`
- `pipeline=adversarial_coevo`
- `opponent_redis_db=<paired DB>`, `opponent_redis_prefix=<paired prefix>`
- `pipeline_builder.per_opponent_timeout=300`
- LiteLLM proxy: `http://10.232.30.185:4000/v1`

## Treatment

REPLICATION only — no treatment/control. All 4 pairs run identical configs. IV is pair identity (replicates 1-4).

## Feasibility: GREEN

All components validated in PR #183.
