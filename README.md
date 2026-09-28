# pMHC-TCR evolution (based on GigaEvo)

This repository is the public code for *LLM-Guided Evolution Reveals Testable
Design Choices for pMHC-TCR Prediction*. The evolutionary engine is based on
the [open-source GigaEvo core](https://github.com/FusionBrainLab/gigaevo-core)
(MIT licensed). Study-specific predictor code, the frozen split, the expert
prompt, and search configurations live under
[`problems/pmhctcr/`](problems/pmhctcr/README.md).

## What is included

- [`problems/pmhctcr/initial_programs/python_patch_seed.py`](problems/pmhctcr/initial_programs/python_patch_seed.py)
  ??? the 249-line seed cited in Appendix B. Only the marked EVOLVE blocks are mutable.
- [`problems/pmhctcr/expert_hypotheses.txt`](problems/pmhctcr/expert_hypotheses.txt)
  ??? the four expert hypotheses (H1???H4) used in guided search.
- [`problems/pmhctcr/prompts_python_patch_final/mutation_suggestions/system.txt`](problems/pmhctcr/prompts_python_patch_final/mutation_suggestions/system.txt)
  ??? the expert-on mutation-suggestion template that interpolates those hypotheses.
- [`problems/pmhctcr/splits/r0.json`](problems/pmhctcr/splits/r0.json) ??? frozen 12/4/4 split.
- Hydra presets `config/experiment/pmhctcr_python_patch_final.yaml` (expert on)
  and `..._final_off.yaml` (expert off; same template, hypotheses disabled).
- Launchers under `scripts/launch_pmhctcr_final_terra_*.sh`.
- Appendix H and held-out score tables under [`analysis/`](analysis/README.md).
- Table scripts: `scripts/export_mutation_tables.py` rebuilds Appendix H from
  saved traces; `scripts/verify_paper_artifacts.py` checks Tables 2???3 / Figure 4
  when a trace archive is present.

## Install and checks

Python 3.11+:

```bash
pip install -e ".[test]"
ruff check .
ruff format --check .
python -m pytest tests/pmhctcr tests/evolution/test_python_patch_mutation.py
```

`pip install -e ".[pmhctcr]"` adds torch, pyarrow, and transformers for
refit/score. Search also needs a configured LLM route (Hydra `llm` configs).

## Attribution

GigaEvo is MIT-licensed open source:
https://github.com/FusionBrainLab/gigaevo-core
