# Artifact manifest

| Path | Role |
|---|---|
| `graphs/raw.json` | Neutral raw-feature control |
| `graphs/catboost.json` | CV-selected CatBoost FeatureGraph |
| `graphs/tabm.json` | CV-selected paper-tuned Higgs TabM FeatureGraph |
| `provenance.json` | Program IDs, CV metrics, source hashes, graph hashes |
| `results/cross_eval.json` | All 30 seed-level held-out evaluations |
| `results/summary.json` | Validated derived matrix and paired gains |
| `results/*.csv` | Performance, semantic-count, and correlation tables |
| `freeze_champions.py` | Validated winner-freezing utility |
| `run_cross_eval.sh` | Exact five-seed matrix launcher |
| `make_figures.py` | Result validation, analysis, figures, and TeX rows |
| `figures/*.pdf` | Vector report figures |
| `figures/*.png` | Raster previews |
| `REPORT.tex` | Report source |
| `REPORT.pdf` | Compiled research report |

The authoritative graph SHA-256 digests are stored in `provenance.json` and are
checked against every seed-level record by `make_figures.py`.
