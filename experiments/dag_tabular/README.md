# DAG-tabular experiments

This is the single home for estimator-controlled FeatureGraph experiments:
CatBoost (`dag_tab`) plus the TabM, RealMLP, TabICL, TabPFN, TabFM, LightGBM,
and XGBoost baselines under `problems/tabular_dag_baselines`.

Bare `experiment=tabular_dag/<model>` runs are no-memory controls. Memory is an
explicit, orthogonal treatment; for example, add
`pipeline=memory_guided memory=v2 memory/llm=qwen_instruct`.

The TabM preset uses one dataset-independent recipe from the repository's
official end-to-end example (full TabM + PLE, `k=32`, 2x512 backbone). Named
paper reproductions may override it explicitly, but the normal baseline never
selects architecture or optimizer hyperparameters per dataset.

- `JOURNAL.md` is the append-only cross-campaign log.
- `artifacts/campaigns/` contains complete campaign snapshots, including available raw runs and reports.
- `artifacts/plans/` contains the associated design and investigation plans.
- `artifacts/docs/` contains the research summary.

The artifact archive is intentionally ignored by Git because it contains raw runs and generated binaries. Its persistent host path is:

```text
/home/jovyan/gigaevo/experiments/dag_tabular/artifacts/
```

New DAG-tabular campaigns and their raw outputs should be stored under
`artifacts/campaigns/<campaign-name>/`; record every launch, completion,
correction, and major finding in `JOURNAL.md`.

Run the complete California baseline campaign with:

```bash
experiments/dag_tabular/launch_california_baselines.sh
```

The launcher records the resolved environment and source hashes, gives each
model its own Hydra directory, and runs RealMLP, TabICL, TabPFN, TabFM,
LightGBM, and XGBoost concurrently. CatBoost and TabM are excluded because
their California campaigns are already complete. GPU-backed evaluators
coordinate through the shared randomized four-GPU lease pool.

The completed 2026-07-23 California findings, frozen champions, and exact
five-seed held-out outputs are in
[`findings/california_20260723`](findings/california_20260723/).

The subsequent eight-graph by eight-evaluator transfer study, including all
360 seed-level test records, colored matrices, semantic graph analysis, and a
polished PDF report, is in
[`findings/california_transfer_20260723`](findings/california_transfer_20260723/).

The Higgs-small CatBoost/TabM two-by-two transfer study contains 30 matched-seed
test fits, colored accuracy/AUC matrices, and a semantic/correlation analysis of
the physics-inspired features:
[`findings/higgs_transfer_20260723`](findings/higgs_transfer_20260723/).

The standard study has two explicit phases. First, evolve one graph per fixed
evaluator with `python run.py experiment=tabular_dag/<model>`. Then freeze the
selected graph JSON files and use the experiment-level comparison launcher:

```bash
experiments/dag_tabular/compare_matrix.sh \
  --graph catboost=catboost.json \
  --graph tabm=tabm.json \
  --evaluator catboost \
  --evaluator tabm \
  --output cross_eval.json
```

This is a short frontend for
`python -m problems.tabular_dag_baselines.compare_matrix`; repeat `--graph`
and `--evaluator` to extend the matrix. It defaults to estimator seeds 0–4 and
reports their sample standard deviation. The graph and dataset split remain
fixed, so this SD measures only estimator-training randomness.

LightGBM and XGBoost intentionally have zero seed SD under the fixed recipes.
Both receive the requested seed, but use deterministic histogram training with
all rows and all columns (`subsample=1`, `colsample=1`); changing
`random_state` therefore leaves their predictions bit-for-bit identical. This
is not sampling uncertainty. Estimating split or dataset uncertainty requires
repeated splits or a bootstrap study rather than relabeling deterministic
replicates as independent variation.

Full launch and comparison details are in
[`problems/tabular_dag_baselines/README.md`](../../problems/tabular_dag_baselines/README.md).
