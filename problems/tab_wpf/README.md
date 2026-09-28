# Tab-WPF: Reverse-SCM predictor evolution

`tab_wpf` evolves a feature-agnostic JSON PredictorDAG of closed TabPFN-inspired operators. Unlike `dag_tab`, the graph does not name raw columns and does not hand features to CatBoost. A hidden GeneratorDAG creates a frozen bank of synthetic tasks once; it is not evolved and is never shown to the predictor. The evolved graph receives only `(X_context, y_context, X_query)` and returns `y_hat_query`.

## Architecture

- **Genome**: `Program.code` is a complete `PredictorGraph` JSON document.
- **Encoder**: fit-only z-score with mean-imputed missing values, missing indicators, frequency encoding, and smoothed cross-fitted target probabilities/means for categoricals.
- **Operators**: closed numpy/sklearn catalog (`identity`, `standardize`, `quantile`, `affine_activation`, `rbf_features`, `pairwise_product`, `column_gate`).
- **Inner-loop weights**: PCA, ridge, and logistic parameters are fit on each CV fold inside Python. Supervised nodes expose cross-fitted features to the readout.
- **Outer-loop evolution**: graph topology, operator choice, params, gates, readout alpha, and raw-feature inclusion via structured diff mutation. The readout family itself is fixed by task type.
- **Graph validity**: every node must reach the final readout; disconnected or non-readout leaves are rejected as dead code.
- **Synthetic evaluation**: one frozen bank has 10 GeneratorDAG families × 10 tasks, with a family-stratified 60/20/20 meta-train/meta-valid/meta-test split. Evolution sees only meta-train.
- **Real evaluation**: delegates CV and test scoring to `problems/tabular` through `fit_predict`.
- **Readout selection**: a labeled context subset selects among `alpha/10`, `alpha`, and `10*alpha`, then the graph is refit on all context rows.
- **Fitness unit**: one complete synthetic task. Query R2 is clipped to `[-1, 1]`, averaged within family, then equally across families.
- **Structural archive**: MAP-Elites uses `(graph_node_count, graph_max_depth)`. With at most 12 nodes, 79 cells are reachable; fitness decides replacement within each cell.

There is intentionally **no** `context.py` in this problem. Dataset semantics are merged at runtime through `TabWpfProblemContext`.

All productive DAG nodes execute in topological order. The runtime does not pick a single path: every `is_readout` output is concatenated, optionally together with encoded raw features, before the final ridge/logistic head. Dead nodes are rejected.

## Neutral seed

```json
{
  "schema_version": 1,
  "nodes": [],
  "readout": {"kind": "ridge", "alpha": 1.0, "include_raw": true}
}
```

The seed loader creates this graph at runtime. It is a raw-readout baseline: encoded features go directly to ridge/logistic.

## Generate the frozen 100-task bank

Generation is deterministic and refuses to overwrite a non-empty directory.
Each task stores its hidden GeneratorDAG for audit, but the evolution validator
passes only public episode arrays to the PredictorDAG.

```bash
python scripts/generate_tab_wpf_task_bank.py \
  /path/to/task_banks/tab_wpf_synthetic_v2_seed20260819

python scripts/generate_tab_wpf_task_bank.py \
  /path/to/task_banks/tab_wpf_synthetic_v2_seed20260819 \
  --verify-only
```

The manifest must report exactly 100 tasks, 10 per family, split 60/20/20 and
6/2/2 inside every family. SHA256 checksums bind every GeneratorDAG, array, the
exact generator source, and the complete manifest. A second identity-blind
content checksum rejects duplicate tasks even when their ids or outer splits
differ.

## Launch synthetic evolution

The guarded launcher always binds the validator to `meta_train`. Use a new run
directory for every model/routing/protocol change.

```bash
export OPENAI_API_KEY=...
export TAB_WPF_TASK_BANK=/path/to/task_banks/tab_wpf_synthetic_v2_seed20260819
export TAB_WPF_RUN_DIR=/path/to/runs/tab_wpf_synthetic_r1
export TAB_WPF_MAX_MUTANTS=200
export TAB_WPF_LLM_BASE_URL=http://your-openai-compatible-endpoint/v1
export TAB_WPF_MODEL_NAME=your-served-model-id
scripts/run_tab_wpf_synthetic_evolution.sh
```

`TAB_WPF_ARCHIVE_SELECTOR=point` is the default. Set it to
`paired_bootstrap` to gate archive replacement with the stable vector of 60
per-task scores. The launcher resolves paths to absolute paths and performs a
strict bank verification before starting evolution.

Evaluate a selected graph on meta-valid, or deliberately unseal meta-test only
for final reporting:

```bash
python scripts/evaluate_tab_wpf_synthetic.py champion.json \
  --bank "$TAB_WPF_TASK_BANK" --split meta_valid

python scripts/evaluate_tab_wpf_synthetic.py champion.json \
  --bank "$TAB_WPF_TASK_BANK" --split meta_test --allow-meta-test
```

## Restricted classification sandbox

The first classification prototype uses a separate, deliberately narrow prior;
it does not replace or modify the regression bank above. The full v2 bank
freezes exactly 12,600 tasks from four GeneratorDAG families: `linear`, `tree`,
`mlp`, and `mixed`. Its 252 primary strata are the Cartesian product of family,
2--8 DAG nodes, 2/3/5 classes, and target oracle quality 0.35/0.55/0.75. Each
stratum contains 50 independently generated tasks and is split 30/10/10 into
meta-train/meta-valid/sealed meta-test. The resulting global split is
7,560/2,520/2,520 and remains exactly balanced across families and primary
strata.

Raw columns are GeneratorDAG inputs and are not counted as nodes.  Each hidden
graph has 2--8 productive composition blocks including the final class-logit
head. A tree block may contain 1--15 internal splits and an MLP block may have
4--16 hidden units, so this block count is a topology limit rather than an
equal-compute comparison across families.  The controlled support is:

- total rows: `256`, `512`, or `1024`, split 75/25 into context/query;
- features: `4`, `8`, `16`, or `24`;
- categorical fraction: `0`, `0.25`, or `0.5`;
- maximum categorical cardinality: `2`, `4`, or `8`;
- classes: `2`, `3`, or `5`.

Rows, width, categorical fraction, cardinality, and eligible-feature fraction
are distributed inside every primary stratum by deterministic randomized Latin
coordinates. They are controls rather than extra fully crossed axes; fully
crossing all controls would create a large amount of redundant computation.

The task score is
`clip(1 - model_log_loss / Laplace_context_prior_log_loss, -1, 1)`.
Thus zero is a legal no-feature baseline and one is perfect.  Fitness is the
mean within each of the four families followed by an equal mean across
families.  Calibration uses an independent, discarded sample.  Saved query
rows never calibrate logits or fit the predictor; generation-time acceptance
only enforces the declared class and categorical-support contract.

First generate the 1,260-task pilot (five tasks per primary stratum), then the
12,600-task full bank (50 per stratum). Generation is deterministic, parallel,
and refuses to overwrite a non-empty directory:

```bash
python scripts/generate_tab_wpf_sandbox_bank.py \
  /path/to/task_banks/tab_wpf_sandbox_classifier_v2_pilot1260_seed20260819 \
  --tasks-per-primary-stratum 5 --workers 16

python scripts/generate_tab_wpf_sandbox_bank.py \
  /path/to/task_banks/tab_wpf_sandbox_classifier_v2_full12600_seed20260819 \
  --tasks-per-primary-stratum 50 --workers 16

python scripts/generate_tab_wpf_sandbox_bank.py \
  /path/to/task_banks/tab_wpf_sandbox_classifier_v2_full12600_seed20260819 \
  --verify-only
```

Evaluating all 7,560 meta-train tasks for every mutation is usually wasteful.
The deterministic sampler can freeze a family-balanced cohort. A cohort of 252
visits every primary stratum exactly once:

```bash
python scripts/sample_tab_wpf_sandbox_bank.py \
  --bank /path/to/task_banks/tab_wpf_sandbox_classifier_v2_full12600_seed20260819 \
  --split meta_train --size 252 --seed 0 \
  --output /path/to/cohorts/tab_wpf_sandbox_v2_train_n252_seed0.json
```

Evaluate the neutral graph on meta-valid without an LLM:

```bash
python scripts/evaluate_tab_wpf_sandbox.py \
  problems/tab_wpf/initial_programs/baseline.json \
  --bank /path/to/task_banks/tab_wpf_sandbox_classifier_v2_full12600_seed20260819 \
  --split meta_valid --sample-size 252 --sample-seed 0
```

Launch evolution only after the bank has passed strict verification.  The
guarded launcher always binds evolution to meta-train and refuses a non-empty
run directory:

```bash
export OPENAI_API_KEY=...
export TAB_WPF_TASK_BANK=/path/to/task_banks/tab_wpf_sandbox_classifier_v2_full12600_seed20260819
export TAB_WPF_RUN_DIR=/path/to/runs/tab_wpf_sandbox_r1
export TAB_WPF_MAX_MUTANTS=200
export TAB_WPF_LLM_BASE_URL=http://your-openai-compatible-endpoint/v1
export TAB_WPF_MODEL_NAME=your-served-model-id
export TAB_WPF_SAMPLE_SIZE=252
export TAB_WPF_SAMPLE_SEED=0
scripts/run_tab_wpf_sandbox_evolution.sh
```

The launcher records the cohort size and seed in the memory task key. Leaving
`TAB_WPF_SAMPLE_SIZE` empty evaluates the entire selected split. Changing the
cohort or model/routing configuration requires a new run directory.

This restricted prior is a debugging benchmark, not evidence of real-data
generalization.  The final graph must be selected without repeatedly opening
meta-test and then evaluated on frozen real datasets.

## Launch the legacy single-real-dataset mode

Required environment: `GIGAEVO_TABULAR_DATA` and LLM credentials. The current
GigaEvo entrypoint initializes and verifies its LLM router even when
`max_mutants=0`; use the offline command below for a truly LLM-free evaluator
smoke test.

```bash
python run.py experiment=tab_wpf problem.dataset=california algorithm=tabular/2d_local_ood max_mutants=100
```

The guarded launcher exports `GIGAEVO_TABULAR_EVAL_DATASET` from
`TAB_WPF_DATASET` for validator subprocess routing. When invoking `run.py`
directly, set that environment variable yourself and keep it equal to
`problem.dataset`.

The guarded launcher requires a dedicated run directory and makes the endpoint,
model, dataset, and budget explicit:

```bash
export GIGAEVO_TABULAR_DATA=/path/to/tabm-data/data
export OPENAI_API_KEY=...  # token for the selected OpenAI-compatible endpoint
export TAB_WPF_RUN_DIR=/path/to/runs/tab_wpf_california_r1
export TAB_WPF_DATASET=california
export TAB_WPF_MAX_MUTANTS=100
export TAB_WPF_LLM_BASE_URL=https://openrouter.ai/api/v1
export TAB_WPF_MODEL_NAME=google/gemini-3-flash-preview
export TAB_WPF_MAX_IN_FLIGHT=2
export TAB_WPF_MAX_TOKENS=8192
scripts/run_tab_wpf_evolution.sh
```

Use a new `TAB_WPF_RUN_DIR` when changing the dataset, model, endpoint, or
protocol. This mode is retained for direct real-data checks; it is separate
from synthetic meta-training.

For an evaluator-only smoke test, create deterministic toy data in the same
layout as the real TabM datasets. These files are testing fixtures, not an
experimental benchmark:

```bash
python scripts/create_tab_wpf_smoke_data.py /tmp/tab_wpf_smoke_data
GIGAEVO_TABULAR_DATA=/tmp/tab_wpf_smoke_data \
  python -m pytest tests/tab_wpf -q
GIGAEVO_TABULAR_DATA=/tmp/tab_wpf_smoke_data \
  python -m problems.tab_wpf.test \
  problems/tab_wpf/initial_programs/baseline.json --dataset california
```

## Offline test scoring

```bash
python -m problems.tab_wpf.test problems/tab_wpf/initial_programs/baseline.json --dataset california
```

## Tests

```bash
python -m pytest tests/tab_wpf -q
```

## Protocol boundary

- GeneratorDAGs and the complete selected bank are frozen before evolution.
- PredictorDAG mutation cannot read GeneratorDAG JSON, task seed, family label,
  split identity, or `y_query`.
- `meta_valid` is for model selection and diagnostics; `meta_test` is sealed
  until a final graph is chosen.
- The current prototype enforces this seal at the predictor API and launcher
  protocol, not cryptographically: a shell user who can read the bank can also
  read its stored query labels and hidden generator JSON. Public/adversarial
  evaluation requires moving meta-test labels into evaluator-only storage.
- The next phase evaluates the chosen synthetic-trained graph on the canonical
  real tabular datasets without changing its topology.

See [AGENTS.md](AGENTS.md) for coding-agent instructions.
