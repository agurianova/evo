# California estimator baselines — 2026-07-23

Six independent 100-mutation FeatureGraph runs completed successfully:
RealMLP-TD, TabICLv2, TabPFN v3, TabFM 1.0, LightGBM 4.6, and XGBoost 2.1.
Each run used Gemini 3.5 Flash for mutation, Qwen Instruct for Memory V2,
`tabular/2d_local_ood`, the canonical three-fold evaluator, and a ten-node
limit. CatBoost and TabM were not repeated because their California campaigns
were already complete.

The exact command is encapsulated by the tracked launcher:

```bash
experiments/dag_tabular/launch_california_baselines.sh
```

The original five-run campaign, logs, storage, manifests, and source hashes
remain under
`experiments/dag_tabular/artifacts/campaigns/tabular_baselines_california_g35_qwen_20260723/`.
The later TabFM run is under
`experiments/dag_tabular/artifacts/campaigns/tabfm_california_g35_qwen_20260723/`.
The original evolution source snapshot matches local implementation commit
`1b6c0184`; its rebased implementation commit in the merge branch is
`6a406435`.
Exact graph hashes, held-out source revisions, package versions, and foundation
checkpoint hashes are recorded in [`MANIFEST.md`](MANIFEST.md). The absolute
paths inside generated result JSONs are historical execution metadata; use the
tracked graph hashes to identify their inputs.

## Evolutionary results

Each champion was selected only by maximum valid CV fitness. The test split was
not read before the six champions were frozen.

| Evaluator | Valid programs | Raw CV R² | Champion CV R² ± fold SD | ΔR² | Nodes / depth / features |
|---|---:|---:|---:|---:|---:|
| RealMLP-TD | 91/101 | 0.823277 | 0.868687 ± 0.002248 | +0.045410 | 3 / 2 / 17 |
| TabICLv2 | 98/101 | 0.872979 | 0.886244 ± 0.002770 | +0.013264 | 6 / 2 / 15 |
| TabPFN v3 | 96/101 | 0.881001 | 0.890186 ± 0.001594 | +0.009185 | 4 / 1 / 14 |
| TabFM 1.0 | 84/101 | 0.892570 | **0.892727 ± 0.003696** | +0.000157 | 4 / 1 / 7 |
| LightGBM 4.6 | 97/101 | 0.845503 | 0.874066 ± 0.003745 | +0.028563 | 5 / 2 / 16 |
| XGBoost 2.1 | 95/101 | 0.840245 | 0.874561 ± 0.004165 | +0.034316 | 7 / 1 / 32 |

All runs stored one neutral seed plus 100 mutations and exited with code zero.

## Held-out results

After freezing, each model evaluated both the raw graph and its own champion
over estimator seeds 0–4. Values below are means ± sample standard deviations
(`ddof=1`). Only the estimator seed varies; graph and split stay fixed.

| Evaluator | Raw test RMSE | Champion test RMSE | RMSE reduction | Champion test R² |
|---|---:|---:|---:|---:|
| RealMLP-TD | 0.460883 ± 0.004302 | 0.399547 ± 0.000798 | 13.31% | 0.877574 ± 0.000489 |
| TabICLv2 | 0.397645 ± 0.000364 | 0.370803 ± 0.000296 | 6.75% | 0.894555 ± 0.000169 |
| TabPFN v3 | 0.378814 ± 0.000720 | 0.363973 ± 0.000636 | 3.92% | 0.898404 ± 0.000355 |
| TabFM 1.0 | **0.359967 ± 0.000220** | **0.358948 ± 0.000148** | 0.28% | **0.901190 ± 0.000081** |
| LightGBM 4.6 | 0.431290 ± 0.000000 | 0.386492 ± 0.000000 | 10.39% | 0.885444 ± 0.000000 |
| XGBoost 2.1 | 0.441843 ± 0.000000 | 0.390425 ± 0.000000 | 11.64% | 0.883101 ± 0.000000 |

LightGBM and XGBoost are deterministic under their fixed recipes, hence zero
between-seed variance. These are diagonal results—each graph is consumed by
the evaluator that evolved it—not a full graph-by-evaluator transfer matrix.

The exact per-seed outputs are in [`test_5seeds`](test_5seeds/). They were
produced with the shared comparison command; for example:

```bash
python -m problems.tabular_dag_baselines.compare_matrix \
  --graph realmlp=experiments/dag_tabular/findings/california_20260723/champions/realmlp.json \
  --evaluator realmlp \
  --seeds 0 1 2 3 4 \
  --phase test \
  --output /tmp/realmlp_test.json
```

## Frozen champions

| Evaluator | Program id | Iteration / generation | Graph SHA-256 |
|---|---|---:|---|
| RealMLP-TD | `b6f63387-1866-42e1-9ce1-15c8af621829` | 62 / 3 | `4d239c46c4471857b5ebbc418e3af406e92dd6cf444279a9b66b5ed3effc8bb5` |
| TabICLv2 | `48aebfa0-1cb2-4b8d-a1a5-e2fb4352a303` | 98 / 6 | `ab8df0bdf2563868be1a9a58771af225ee9a7bf3fd31a4d224960d1ad6c9dd4c` |
| TabPFN v3 | `33eca639-01ba-4b68-a68d-7ab4e3f296a6` | 71 / 6 | `8755fc2919c9663d5bdc3ca6d0405597cf1663f5e16e5d04ba747db20ba75336` |
| TabFM 1.0 | `91a927a7-88f8-46d4-a89d-b08bed464e14` | 92 / 5 | `95e44f3454fa04a2f43504b1a996b76c8580a70e5548b167d66b0e5e5058b271` |
| LightGBM 4.6 | `732d8c5d-133d-4e92-9707-0d07469a9bf2` | 88 / 7 | `a275bde3203176db241f48917cf4822d30cb866e7818d6f4524aa1ad9e5716fb` |
| XGBoost 2.1 | `bf50d9ab-2f7a-466d-8153-e245585937c8` | 93 / 8 | `9847d9e5e31e61da216038ab8b4b866636532d300f80dc5442250d812062c331` |

The executable graphs are preserved in [`champions`](champions/), alongside
the shared empty/raw graph used for controls.
