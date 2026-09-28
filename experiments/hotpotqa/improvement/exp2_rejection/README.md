# Experiment 2: Reducing Mutant Rejection Rate

**Branch**: `exp/hotpotqa-efficiency`
**Date**: 2026-02-27
**Research question**: Does coarser MAP-Elites binning (`primary_resolution=20` vs 150) reduce the ~70% rejection rate and improve evolution speed?

## Background

The current MAP-Elites archive uses 150 fitness bins over [0, 1]. With ~60 programs in the archive, ~40% of bins are occupied. A mutant must exceed the bin occupant's fitness to enter, so ~70% of mutants are rejected. This wastes LLM compute and slows progress.

Reducing to 20 bins gives 20 fitness ranges of 0.05 width each, allowing more programs to coexist and potentially improving archive diversity.

## Experimental Design

Three parallel conditions (all use non-thinking Qwen3-8B for chain execution):

| Run | DB | primary_resolution | max_mut/gen | max_elites/gen | max_generations | Mutation server |
|-----|----|--------------------|-------------|----------------|-----------------|-----------------|
| A (baseline) | 10 | **150** | 8 | 5 | 10 | 10.226.72.211:8777 |
| B (coarse) | 15 | **20** | 8 | 5 | 10 | 10.226.15.38:8777 |
| C (coarse+more) | 0 | **20** | **16** | **8** | 10 | 10.226.185.131:8777 |

Comparisons:
- **A vs B**: Effect of coarser binning alone (accept rate, diversity, fitness curve)
- **B vs C**: Effect of doubling mutation budget (same binning)
- **A vs C**: Combined effect

## Exact Run Commands

```bash
# Prerequisites
cd /workspace-SR008.fs2/mathemage/gigaevo-core
export NO_PROXY="localhost,127.0.0.1,10.226.17.25"
export no_proxy="localhost,127.0.0.1,10.226.17.25"
PYTHON=/home/jovyan/envs/evo_fast/bin/python

# Run A: Baseline (primary_resolution=150, 8 mutations/gen)
nohup bash -c "
export NO_PROXY='localhost,127.0.0.1,10.226.17.25'
export no_proxy='localhost,127.0.0.1,10.226.17.25'
/home/jovyan/envs/evo_fast/bin/python run.py \
  problem.name=chains/hotpotqa/static \
  redis.db=10 \
  llm_base_url=http://10.226.72.211:8777/v1 \
  max_generations=10
" > experiments/hotpotqa_improvement/exp2_rejection/run_A_db10.log 2>&1 &
echo "Run A PID: $!"

# Run B: Coarse binning (primary_resolution=20, 8 mutations/gen)
nohup bash -c "
export NO_PROXY='localhost,127.0.0.1,10.226.17.25'
export no_proxy='localhost,127.0.0.1,10.226.17.25'
/home/jovyan/envs/evo_fast/bin/python run.py \
  problem.name=chains/hotpotqa/static \
  redis.db=15 \
  llm_base_url=http://10.226.15.38:8777/v1 \
  primary_resolution=20 \
  max_generations=10
" > experiments/hotpotqa_improvement/exp2_rejection/run_B_db15.log 2>&1 &
echo "Run B PID: $!"

# Run C: Coarse binning + more mutants (primary_resolution=20, 16 mutations/gen)
nohup bash -c "
export NO_PROXY='localhost,127.0.0.1,10.226.17.25'
export no_proxy='localhost,127.0.0.1,10.226.17.25'
/home/jovyan/envs/evo_fast/bin/python run.py \
  problem.name=chains/hotpotqa/static \
  redis.db=0 \
  llm_base_url=http://10.226.185.131:8777/v1 \
  primary_resolution=20 \
  max_mutations_per_generation=16 \
  max_elites_per_generation=8 \
  max_generations=10
" > experiments/hotpotqa_improvement/exp2_rejection/run_C_db0.log 2>&1 &
echo "Run C PID: $!"
```

## Expected Runtime

- Initial seed validation: ~2-3 min
- Per generation: ~5 min (validation) + ~25 min (8-16 sequential mutation LLM calls at ~3 min each) + ~2 min (mutant validation, parallel)
- **Total: ~30-45 min/generation × 10 generations ≈ 5-7.5 hours per run**
- Run C will take ~50% longer per generation (16 mutations vs 8)

## Metrics to Compare

1. **Best validation EM** after 10 generations
2. **Acceptance rate**: % mutants entering archive (target: >60% for coarser runs)
3. **Fitness curve slope**: Still improving at gen 10?
4. **Archive size**: How many unique programs in archive by gen 10?

## Results

### Initial Seed Fitness
| Run | DB | Initial EM |
|-----|----|---------  |
| A | 10 | 42.3% |
| B | 15 | 43.0% |
| C | 0 | ~42-43% |

Starting from unoptimized baseline — matches published GEPA baseline (42.3%).

### Generation Results
*TBD — runs started 2026-02-27 ~23:00*
