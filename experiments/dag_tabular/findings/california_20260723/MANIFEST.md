# California baseline findings manifest

This manifest identifies the immutable inputs behind the tracked summary.
Historical absolute paths in the generated JSON files describe the host on
which a command ran; they are not expected to resolve elsewhere.

## Protocol

- Dataset: `california`
- Frozen split and frozen FeatureGraph within every result cell
- Estimator seeds: `0, 1, 2, 3, 4`
- Reported uncertainty: sample standard deviation (`ddof=1`)
- Evolution selection: maximum valid three-fold CV fitness
- Held-out labels read only after all six champions were frozen

## Source provenance

The campaign started from parent revision `5295e008` before its implementation
was committed. Its recorded source hashes match local implementation snapshot
`1b6c0184`; the rebased equivalent in the merge branch is `6a406435`.
The later TabFM evolution ran from `10fe5018`; its held-out comparison ran
from the squash-equivalent merged revision `05e27851`.

| Held-out files | Recorded evaluator revision |
|---|---|
| `test_5seeds/{raw,champions}/realmlp.json` | `680cbedec2b298c2af080b045c60361d1614c821` |
| The other eight `test_5seeds` JSON files | `9d23221dab73cde6bed8e49d5e265a9790178aac` |
| `test_5seeds/{raw,champions}/tabfm.json` | `05e278512b2ed4b26df60a5cd4d87817db65b214` |

The four later clean-branch checks reproduce the original campaign statistics
at the reported precision. The RealMLP files retain the already completed
original five-seed evaluation; no duplicate RealMLP fit is needed to interpret
the table.

## Frozen graph identities

| Graph | SHA-256 |
|---|---|
| Raw | `a08f6e89573958de4b7291ae6a7d6b2975ddb28fbd993db3aa2afc35b6b699c3` |
| RealMLP | `4d239c46c4471857b5ebbc418e3af406e92dd6cf444279a9b66b5ed3effc8bb5` |
| TabICL | `ab8df0bdf2563868be1a9a58771af225ee9a7bf3fd31a4d224960d1ad6c9dd4c` |
| TabPFN | `8755fc2919c9663d5bdc3ca6d0405597cf1663f5e16e5d04ba747db20ba75336` |
| TabFM | `95e44f3454fa04a2f43504b1a996b76c8580a70e5548b167d66b0e5e5058b271` |
| LightGBM | `a275bde3203176db241f48917cf4822d30cb866e7818d6f4524aa1ad9e5716fb` |
| XGBoost | `9847d9e5e31e61da216038ab8b4b866636532d300f80dc5442250d812062c331` |

## Environment and checkpoints

The isolated environment used Python 3.12.13 with these packages:

| Package | Version |
|---|---:|
| PyTorch | 2.13.0 |
| TabM | 0.0.3 |
| rtdl-num-embeddings | 0.0.12 |
| PyTabKit | 1.7.3 |
| TabICL | 2.1.1 |
| TabPFN | 8.1.0 |
| TabFM | 1.0.1 |
| LightGBM | 4.6.0 |
| XGBoost | 2.1.4 |

California used the following frozen foundation checkpoints:

| Model | Repository / checkpoint | SHA-256 |
|---|---|---|
| TabICLv2 | `jingang/TabICL` / `tabicl-regressor-v2-20260212.ckpt` | `0db9cb538f114e79026bf08f45f41ad8dd7ad2de2aaca9a5ca8cd3bd9748ae7a` |
| TabPFN v3 | `Prior-Labs/tabpfn_3` / `tabpfn-v3-regressor-v3_20260417_mediumdata.ckpt` | `06a1daeebbc19f8d9478bd6fdf8753859c68abc9abfe53e8216b1067b7e0bc21` |
| TabFM 1.0 | `google/tabfm-1.0.0-pytorch@77cb9cc1` / `regression/model.safetensors` | `bd5a615b0322a8f04a895038de6df6fbd71430eca750e1d792f31048654674a9` |
