#!/usr/bin/env bash
# Regenerate ALL offline (no-LLM) qwen Part-II artifacts from final-250 storage+logs,
# then stage them into report_fused/ with _qwen suffixes for the fused report's
# \graphicspath. Safe to run from anywhere. Run AFTER both qwen runs hit 250.
#
# CWD discipline (scripts disagree on where they read/write):
#   analyze_ab / extract_tokens / build_pareto : path args resolve from EXP ROOT
#   make_figures / make_pareto                 : read+write bare names in CWD -> qwen_snapshot
#   extract_lineage / make_lineage_viz_qwen    : write via __file__ -> report_fused
#
# What this does NOT do (needs the LLM proxy + a winner-id judgment call): the
# held-out test_eval.py and the Pareto right-panel test_points — see TODO at end.
set -euo pipefail
RF="$(cd "$(dirname "$0")" && pwd)"        # report_fused/
ROOT="$(cd "$RF/.." && pwd)"               # carl_tool_chain_diff_ab/
QS="$ROOT/qwen_snapshot"
PY=/home/jovyan/.mlspace/envs/evo/bin/python3
A="$ROOT/runs/armA_qwen_fixed"
B="$ROOT/runs/armB_qwen"
# armA_qwen_fixed's run.log is frozen (loguru stderr sink died at startup); its
# LLM_CALL lines live only in the shared hydra log, interleaved with armA_fixed
# (gemini). Materialize the model-filtered sidecar that extract_tokens prefers:
HYDRA_LOG="$ROOT/../../outputs/2026-07-04/22-07-28/evolution_20260704_190728.log"
grep '\[LLM_CALL\]' "$HYDRA_LOG" | grep Qwen3-235B > "$A/run.log.mutator"
cd "$ROOT"

echo "== [1/5] validity funnel + fitness + nsteps stats (analyze_ab -> ab_stats.json) =="
"$PY" analyze_ab.py "$A" "$B" --out "$QS"

echo "== [2/5] per-call mutation tokens (extract_tokens) + qwen-suffix copy =="
"$PY" qwen_snapshot/extract_tokens.py "$A" "$B"
cp "$QS/mutation_tokens_per_call.json" "$QS/mutation_tokens_per_call_qwen.json"

echo "== [3/5] overview / nsteps / tokens figures (make_figures, CWD=qwen_snapshot) =="
( cd "$QS" && "$PY" make_figures.py )

echo "== [4/5] arm-B winning lineage DAG (extract_lineage -> make_lineage_viz_qwen) =="
( cd "$RF" && "$PY" extract_lineage.py "$B" --out viz_qwen && "$PY" make_lineage_viz_qwen.py )

echo "== [5/5] Pareto (left panel = cost-to-winner; right panel test-less until test_points filled) =="
"$PY" qwen_snapshot/build_pareto_data.py qwen "$QS/pareto_build_qwen.json"
( cd "$QS" && "$PY" make_pareto.py )

echo "== stage qwen figures into report_fused/ with _qwen suffix =="
for f in ab_overview ab_tokens ab_nsteps ab_pareto ab_waste; do
  cp "$QS/$f.png" "$RF/${f}_qwen.png"
done
# lineage_graph_qwen.png already written into report_fused/ by make_lineage_viz_qwen.py

cat <<'EOF'

======================================================================
OFFLINE qwen artifacts regenerated. REMAINING (need LLM proxy + judgment):
  1. Refresh winner ids in test_eval_spec_qwen.json  (armA/armB best + armB
     lineage gen2) from FINAL storage — winners may have advanced past gen3.
     extract_lineage (step 4 above) prints armB's final chain ids/fitness.
  2. Source env + run held-out eval (Qwen3-8B executor, 300 claims, ~5-10 min):
       source /home/jovyan/gigaevo/.env
       export NO_PROXY="localhost,127.0.0.1,10.232.89.98"
       OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 \
         /home/jovyan/.mlspace/envs/evo/bin/python3 test_eval.py test_eval_spec_qwen.json
       cp test_metrics.json test_metrics_qwen.json
  3. Fill qwen_snapshot/pareto_build_qwen.json "test_points" from test_metrics_qwen.json
     as [{"id": "<8+ char id>", "test": <disc_pct 0-100>, "label": "..."}], then re-run:
       python qwen_snapshot/build_pareto_data.py qwen qwen_snapshot/pareto_build_qwen.json
       ( cd qwen_snapshot && python make_pareto.py )
       cp qwen_snapshot/ab_pareto.png report_fused/ab_pareto_qwen.png
       cp qwen_snapshot/ab_waste.png  report_fused/ab_waste_qwen.png
  4. Fill Part II + cross-model synthesis + abstract + verdict in report.tex from
     ab_stats.json / mutation_tokens.json / pareto_data_qwen.json / test_metrics_qwen.json.
======================================================================
EOF
echo "regen_qwen.sh DONE"
