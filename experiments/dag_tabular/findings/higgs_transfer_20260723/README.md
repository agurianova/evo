# Higgs-small CatBoost ↔ TabM FeatureGraph transfer

This directory freezes the CV-selected CatBoost and paper-tuned Higgs
TabM-mini FeatureGraphs, evaluates both graphs with both estimators over seeds
0–4, and reports held-out accuracy, ROC AUC, and a semantic comparison of the
generated features.

The matrix contains the 2×2 engineered cells plus one raw control per
evaluator: 30 fresh test fits in total. The feature graph and official split
are fixed; the reported sample SD is estimator-seed dispersion only.

## Reproduce

From the repository root:

```bash
source /home/jovyan/.mlspace/envs/evo_torch/bin/activate
export GIGAEVO_TABULAR_DATA=/home/jovyan/tabm-data/data
```

The frozen graph files and `provenance.json` are already present. To rerun the
held-out matrix with the exact historical Higgs TabM-mini recipe:

```bash
experiments/dag_tabular/findings/higgs_transfer_20260723/run_cross_eval.sh
```

Build validated derived tables and figures, then compile the report:

```bash
report_dir=experiments/dag_tabular/findings/higgs_transfer_20260723
python "$report_dir/make_figures.py"
(cd "$report_dir" && tectonic REPORT.tex)
```

`run_cross_eval.sh` intentionally exports every TabM setting used during the
Higgs evolution campaign. Ordinary `experiment=tabular_dag/tabm` runs use the
single dataset-independent full-TabM baseline recipe instead.

The absolute graph and evaluator paths inside `results/cross_eval.json` record
the launch-time worktree. They are historical provenance, not required live
paths: the tracked relative graph files are authoritative, and
`make_figures.py` verifies their hashes against every seed-level record.

## Main result

| Evaluator | Raw accuracy | CatBoost graph | TabM graph |
|---|---:|---:|---:|
| CatBoost | 72.728 ± 0.083% | 73.525 ± 0.075% | **74.010 ± 0.071%** |
| TabM | 73.770 ± 0.113% | 74.181 ± 0.098% | **74.871 ± 0.161%** |

The TabM graph wins both evaluator rows. Its generated output names have zero
literal overlap with the CatBoost graph, but the semantic/code audit finds four
shared mechanisms and two exact rank-equivalent angular-distance features.

See [REPORT.pdf](REPORT.pdf) for the full protocol, colored matrices, paired
gains, graph inventories, feature-correlation analysis, caveats, and
interpretation.
