# California cross-model FeatureGraph transfer — 2026-07-23

This is the complete five-seed cross-evaluation of eight frozen California
FeatureGraphs under eight tabular estimators. Rows are evaluators; columns are
the models against which the graph was evolved. The matrix contains 64
engineered-graph cells plus eight raw controls, or 360 seed-level test records.
No evolution or LLM calls were made during cross-evaluation.

The polished report is [`REPORT.pdf`](REPORT.pdf); its editable source is
[`REPORT.tex`](REPORT.tex).

## Main findings

- Fifty-seven of 64 graph/evaluator cells beat the corresponding raw control
  on every matched seed. The seven exceptions are every older graph consumed
  by TabFM.
- The CatBoost graph wins five evaluator rows—CatBoost, TabM, RealMLP, TabICL,
  and TabPFN—and is top-three in seven of eight.
- The 14-feature TabPFN graph wins LightGBM and XGBoost and retains the largest
  mean RMSE reduction on foreign evaluators.
- TabFM's seven-feature native graph wins the TabFM row and improves all seven
  older evaluators over raw, though it ranks last in each older row.
- Exact feature-name overlap is very low (2.7% median pairwise Jaccard). All
  graphs discover geography and household normalization; unlike the other
  seven, TabFM selects no supervised neighbourhood feature.
- The differences are mainly in allocation. CatBoost is broad and
  compositional; TabM is densely multi-scale; RealMLP uses radial bases and
  stacked predictions; TabICL uses coastal gating; TabPFN is compact and
  robust; LightGBM is a small balanced portfolio; XGBoost learns centroid
  bases and many local covariates.

The complete numerical interpretation, colored RMSE and uplift matrices,
paired native/foreign deltas, family analysis, and per-graph feature inventory
are in the PDF.

## Artifact map

- `graphs/`: the raw control and eight exact executable graph JSON files.
- `results/combined_matrix.json`: all per-seed records, summaries, revisions,
  graph hashes, and paired deltas.
- `results/*.csv`: RMSE, uplift, rank, donor, family, paired, and similarity
  tables.
- `figures/`: vector PDF and high-resolution PNG versions of every report
  figure.
- `make_figures.py`: rebuilds figures and derived tables from the frozen
  matrix and graphs.

The JSON files are normally ignored repository-wide, so they are deliberately
force-tracked here as immutable research artifacts.

## Rebuild the report

From this directory in the isolated `evo_torch` environment:

```bash
python make_figures.py
tectonic REPORT.tex
```

The plotting script validates that every manually classified semantic feature
count equals the exact number of outputs in its graph before producing the
figures.

## Re-run one transfer cell

The matrix predates the universal TabM default. Its TabM graph was evolved and
all TabM evaluator cells were measured with the historical paper-tuned
California TabM-mini recipe: `k=32`, three 576-wide blocks, dropout
0.2405049535, learning rate 2.992624e-4, no weight decay, 30 PLE bins, and
independent member batches. This is an intentional provenance boundary, not
the current cross-dataset baseline.

Use the local compatibility wrapper to reproduce a cell with that exact TabM
recipe:

```bash
cd experiments/dag_tabular/findings/california_transfer_20260723
./compare_historical.sh \
  --graph catboost=graphs/catboost.json \
  --evaluator realmlp \
  --output /tmp/california-cell.json
```

It defaults to test phase and seeds 0–4. Use `--phase cv` instead when
developing or screening; the held-out matrix in this report has already
consumed the California test split and must not become a model-selection loop.
Ordinary new runs should use `experiments/dag_tabular/compare_matrix.sh` and
the universal full-TabM default.

## Provenance

Forty-two original missing cells were evaluated at
`26ab5fe3b64ce34cf579a4be14866441e54224a8`. Four existing CatBoost/TabM cells
use `4d4a6cfc457e80f8076376e10722dec6d9352e78`; two RealMLP raw/native cells
use `680cbedec2b298c2af080b045c60361d1614c821`; and eight other raw/native cells
use `9d23221dab73cde6bed8e49d5e265a9790178aac`. Every per-seed record retains
its exact revision in `combined_matrix.json`. The 16 TabFM-extension cells
(80 seed-level records) were evaluated at
`05e278512b2ed4b26df60a5cd4d87817db65b214`.

Only the estimator seed varies. The sample SD is therefore training-randomness
dispersion, not uncertainty across datasets, samples, splits, or evolution
trajectories. LightGBM and XGBoost are deterministic under their fixed recipes
and consequently report zero seed SD.
