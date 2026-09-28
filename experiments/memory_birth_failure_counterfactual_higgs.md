# Memory Birth-Failure Counterfactual

Primary significant-change scale: `0.01`; default birth-failure multiplier: `2.0`.

### `SHARE_TABULAR_MEMORY`

- Cards: 49 total, 40 insights, 9 program exemplars.
- Birth-failure threshold: `-0.02000`.
- Founding-only insights: 35 total, 31 negative, 1 catastrophic.
- Any catastrophic founding insight: 2; would delete: 2.
- Founding min distribution: min `-0.115240`, median `-0.001097`.

| card | min founding | founding n | later evidence n | note |
|---|---:|---:|---:|---|
| `mem-4e20dda7ddcc` | `-0.115240` | 2 | 0 | Use out-of-fold or leave-one-out target encoding for spatial or density-adaptive region... |
| `mem-85f7ac4a80b4` | `-0.027828` | 1 | 1 | Weight base models by inverse validation error in the logit or transformed space when b... |

### `SHARE_TABULAR_MEMORY_2`

- Cards: 48 total, 37 insights, 11 program exemplars.
- Birth-failure threshold: `-0.02000`.
- Founding-only insights: 27 total, 22 negative, 8 catastrophic.
- Any catastrophic founding insight: 11; would delete: 11.
- Founding min distribution: min `-0.264538`, median `-0.003371`.

| card | min founding | founding n | later evidence n | note |
|---|---:|---:|---:|---|
| `mem-7a10b468c891` | `-0.264538` | 1 | 0 | Replace a multi-model ensemble with a single high-capacity model when domain physics im... |
| `mem-023588ab947a` | `-0.065593` | 3 | 4 | Compute quantile bin edges from combined training and validation data to stabilize disc... |
| `mem-87dd8c8f0902` | `-0.065593` | 1 | 0 | Omit high-cardinality categorical expansions from linear models to prevent feature dilu... |
| `mem-55d3e6a006f7` | `-0.051189` | 7 | 2 | Construct multiplicative interaction terms between high-signal continuous features, esp... |
| `mem-c51e72909ca0` | `-0.051189` | 4 | 0 | Standardize inputs with heterogeneous scales before any magnitude-sensitive operation —... |
| `mem-ebbd63380cd8` | `-0.042012` | 7 | 2 | Augment global models with a cross-validated kNN target encoding derived from spatial o... |
| `mem-eb0f1469e77a` | `-0.031988` | 2 | 0 | Ensemble a regularized linear model with a tree-based model to balance global parametri... |
| `mem-029edfefd6c4` | `-0.024888` | 1 | 0 | Replace kNN-based spatial smoothing with RBF features centered at data-adaptive spatial... |
| `mem-4ee9e7d79511` | `-0.023778` | 1 | 0 | Replace kNN-based spatial smoothing with a grid-based aggregation that bins geographic ... |
| `mem-e80ea7e19790` | `-0.023778` | 1 | 0 | Derive inverse occupancy ratios such as people per room or people per bedroom from popu... |
| `mem-eb88904575ae` | `-0.021129` | 1 | 0 | Use a low-depth decision tree as a meta-learner to capture non-linear error correlation... |

### `SHARE_TABULAR_MEMORY_HIGGS_SOTA_R1_20260708_004349`

- Cards: 41 total, 29 insights, 12 program exemplars.
- Birth-failure threshold: `-0.02000`.
- Founding-only insights: 19 total, 14 negative, 0 catastrophic.
- Any catastrophic founding insight: 1; would delete: 1.
- Founding min distribution: min `-0.211869`, median `-0.000924`.

| card | min founding | founding n | later evidence n | note |
|---|---:|---:|---:|---|
| `mem-d9ea3e61b8ec` | `-0.211869` | 1 | 2 | Use leave-one-out target encoding for categorical features in the training set to preve... |

### `SHARE_TABULAR_MEMORY_HIGGS_SOTA_R2_20260708_004349`

- Cards: 29 total, 19 insights, 10 program exemplars.
- Birth-failure threshold: `-0.02000`.
- Founding-only insights: 13 total, 12 negative, 3 catastrophic.
- Any catastrophic founding insight: 3; would delete: 3.
- Founding min distribution: min `-0.023314`, median `-0.001211`.

| card | min founding | founding n | later evidence n | note |
|---|---:|---:|---:|---|
| `mem-460b3ba35e54` | `-0.023314` | 1 | 0 | Apply one-hot encoding to discrete categorical features with non-ordinal labels before ... |
| `mem-8aa02bed81f7` | `-0.023314` | 1 | 0 | Standardize continuous features to a common scale when using distance- or gradient-sens... |
| `mem-c067ff9ca4b8` | `-0.023314` | 2 | 0 | Use callback-based early stopping with validation monitoring to halt training when gene... |

