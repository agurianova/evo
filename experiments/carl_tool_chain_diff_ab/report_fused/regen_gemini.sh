#!/usr/bin/env bash
# Regenerate Part-I (gemini) artifacts from armA_fixed vs armB_shuf into
# gemini_fixed_snapshot/, then stage bare-name figures into report_fused/ where
# \graphicspath{{./}{../report_full250/}} shadows the frozen pre-fix copies.
# Part I's arm B (armB_shuf) is unchanged: lineage_graph.png and the B-side
# held-out test numbers stay frozen in report_full250/. Run AFTER armA_fixed
# hits 250.
#
# Script provenance: extract_tokens/make_figures/build_pareto_data from
# qwen_snapshot (latest, run.log.mutator-aware); make_pareto from report_full250
# (full two-panel version with the held-out test panel; skips absent models).
set -euo pipefail
RF="$(cd "$(dirname "$0")" && pwd)"           # report_fused/
ROOT="$(cd "$RF/.." && pwd)"                  # carl_tool_chain_diff_ab/
GS="$ROOT/gemini_fixed_snapshot"
PY=/home/jovyan/.mlspace/envs/evo/bin/python3
A="$ROOT/runs/armA_fixed"
B="$ROOT/runs/armB_shuf"
mkdir -p "$GS"
for s in extract_tokens.py make_figures.py build_pareto_data.py; do
  cp -f "$ROOT/qwen_snapshot/$s" "$GS/$s"
done
cp -f "$ROOT/report_full250/make_pareto.py" "$GS/make_pareto.py"
cd "$ROOT"

echo "== [1/5] validity funnel + fitness + nsteps stats (analyze_ab -> ab_stats.json) =="
"$PY" analyze_ab.py "$A" "$B" --out "$GS"

echo "== [2/5] per-call mutation tokens (extract_tokens) + gemini-suffix copies =="
"$PY" "$GS/extract_tokens.py" "$A" "$B"
cp "$GS/mutation_tokens_per_call.json" "$GS/mutation_tokens_per_call_gemini.json"
cp "$GS/mutation_tokens.json" "$GS/mutation_tokens_gemini.json"

echo "== [3/5] overview / nsteps / tokens figures (make_figures, CWD=$GS) =="
( cd "$GS" && "$PY" make_figures.py )

echo "== [4/5] Pareto (A test_points empty until held-out eval on armA_fixed winner) =="
"$PY" "$GS/build_pareto_data.py" gemini "$GS/pareto_build_gemini.json"
( cd "$GS" && "$PY" make_pareto.py )

echo "== [5/5] stage bare-name figures into report_fused/ (shadow frozen copies) =="
for f in ab_overview ab_tokens ab_nsteps ab_pareto ab_waste; do
  cp "$GS/$f.png" "$RF/$f.png"
done

cat <<'EOF'

======================================================================
Part-I offline artifacts regenerated. REMAINING (needs LLM proxy):
  1. Held-out eval of the armA_fixed winner (B-side numbers stay frozen from
     report_full250/test_metrics.json — armB_shuf unchanged): add the winner to
     a spec mirroring report_full250/test_eval_spec.json, run test_eval.py.
  2. Fill A-side test_points in gemini_fixed_snapshot/pareto_build_gemini.json
     from that eval, re-run steps [4/5].
======================================================================
EOF
echo "regen_gemini.sh DONE"
