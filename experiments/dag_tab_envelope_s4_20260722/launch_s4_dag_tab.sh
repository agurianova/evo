#!/bin/bash
# S4 — capability-envelope refactor, 3 replicas x 100 mutations on dag_tab/california.
#
# Mirrors arm B of the 2026-07-21 shakedown verbatim (JOURNAL.md "Queued: run 2"),
# which is the configuration the plan names: gemini-3.5-flash, reasoning high, flex.
# The ONLY intended difference is the refactored mutation surface itself.
#
#   llm=gemini35_flash                            reasoning.effort=high + service_tier=flex;
#                                                 structured_output_method=function_calling is now
#                                                 the config default (json_schema is the 400 path)
#   llm.models.0.max_tokens=32768                 ${max_tokens}=81920 exceeds gemini-3.5-flash's
#                                                 65536 output ceiling; 32768 matches arm A's budget
#
# Fitness is 3-fold CV (tabular default). GIGAEVO_TABULAR_CV_FOLDS is deliberately
# UNSET: the 0.864554 bar and the 0.848628 seed both reproduce at folds=3, and the
# 5-fold variant in launch_dag_tab_california.sh belongs to a different experiment.
#
# Run dirs live under the persistent campaign archive in ~/gigaevo. The
# non-blocking log sink keeps NFS writes off the asyncio event loop.
#
# Replica labels 101/202/303 only name run dirs — gigaevo has no global RNG seed knob,
# so replica variation comes from LLM sampling.
#
# USAGE
#   ./launch_s4_dag_tab.sh [CONC] [START] [END]     e.g. ./launch_s4_dag_tab.sh 3 1 3
set -u

REPO=/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/gigaevo-core-internal/.claude/worktrees/pr306-rebase
cd "$REPO" || exit 1

set -a
source /home/jovyan/gigaevo/.env
set +a
export GIGAEVO_TABULAR_DATA=/home/jovyan/tabm-data/data
export OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8
export PYTHONPATH="$REPO"

PY=/home/jovyan/.mlspace/envs/evo/bin/python3
LABELS=( 101 202 303 )
CONC="${1:-3}"
START="${2:-1}"
END="${3:-3}"

TS="$(date +%Y%m%d_%H%M%S)"
RUNS_ROOT=/home/jovyan/gigaevo/experiments/dag_tab_envelope_s4_20260722/runs
OUT="${RUN_ROOT:-$RUNS_ROOT/no_memory/california/gemini35_flash/$TS}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
DRIVER="$OUT/driver.log"

# Code lineage: every launch must prove which checkout is actually executing.
{
  echo "=== lineage ==="
  $PY -c "import gigaevo, problems.dag_tab.validate as v; print('gigaevo :', gigaevo.__file__); print('dag_tab :', v.__file__)" 2>&1
  git -C "$REPO" rev-parse --abbrev-ref HEAD 2>&1
  git -C "$REPO" rev-parse --short HEAD 2>&1
  echo "=== output root: $OUT ==="
} | tee -a "$DRIVER"

run_one() {
  local label="$1"
  local rundir="$OUT/r${label}"
  local log="$OUT/r${label}.log"
  echo "=== $(date -Is) LAUNCH r${label} -> $rundir" | tee -a "$DRIVER"
  $PY -u run.py \
    problem.name=dag_tab \
    program_format=json_document \
    pipeline=guided \
    memory=none \
    mutation=structured_diff_dag_tab \
    mutation_operator.allowed_changes.max_nodes=10 \
    llm=gemini35_flash \
    llm.models.0.max_tokens=32768 \
    num_parents=1 \
    max_mutants=100 \
    algorithm=tabular/2d_local_ood \
    hydra.run.dir="${rundir}" \
    > "$log" 2>&1
  echo "=== $(date -Is) DONE   r${label} exit=$?" | tee -a "$DRIVER"
}

i=$START
while [ "$i" -le "$END" ]; do
  pids=()
  for ((k=0; k<CONC && i<=END; k++, i++)); do
    run_one "${LABELS[$((i-1))]}" &
    pids+=($!)
  done
  for pid in "${pids[@]}"; do wait "$pid"; done
done

echo "=== $(date -Is) ALL REPLICAS COMPLETE ===" | tee -a "$DRIVER"
