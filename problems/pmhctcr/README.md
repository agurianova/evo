# pMHC-TCR manuscript implementation

This directory implements the pMHC-TCR study described in *LLM-Guided Evolution
Reveals Testable Design Choices for pMHC-TCR Prediction*. Its evolutionary
engine is based on the [open-source GigaEvo core](https://github.com/FusionBrainLab/gigaevo-core)
(MIT licensed); the predictor, data contract, and paper-specific configurations
are additions in this repository.

## Study contract

- The frozen split is [`splits/r0.json`](splits/r0.json): 12 training, four
  validation, and four held-out test pMHCs. Receptors can occur in more than
  one fold. The split has 5,378 / 1,786 / 1,772 pairs after filtering for
  complete modalities.
- [`initial_programs/python_patch_seed.py`](initial_programs/python_patch_seed.py)
  is the 249-line seed cited by line number in Appendix B. Only its two marked
  EVOLVE blocks are mutable. It is intentionally excluded from automatic Ruff
  formatting so its published line references remain stable.
- [`evaluate.py`](evaluate.py) computes per-pMHC average precision and
  McClish-standardized ROC-AUC at FPR 0.1, then takes an unweighted mean.
  [`dataset.py`](dataset.py) removes labels from the predictor's score input;
  [`validate.py`](validate.py) fits on training targets and scores validation
  targets during search. Held-out test scoring is a separate call.
- The reported search uses
  [`config/experiment/pmhctcr_python_patch_final.yaml`](../../config/experiment/pmhctcr_python_patch_final.yaml),
  [`config/algorithm/pmhctcr_python_final_2d.yaml`](../../config/algorithm/pmhctcr_python_final_2d.yaml),
  and [`gigaevo/evolution/mutation/python_patch.py`](../../gigaevo/evolution/mutation/python_patch.py).
  The archive has six interaction bins and six parameter-count bins.

## Inputs

Raw data and generated assets are separate from Git. Point `PMHCTCR_DATA` to a
root containing `tables/{samples,mhc,epitope,tcr}.parquet`, `pdb/<complex>.pdb`,
`masif/<complex>/{tcr,pmhc}.npz`, and
`esm2_t6_8M_UR50D/by_id/<sequence-id>.npz`. The ESM cache builder also
requires `sequences.json` at that root, mapping sequence IDs to sequences. The repository contains the frozen
split and an ESM cache script (`scripts/cache_pmhctcr_esm2.py`); it does not
contain the large Boltz-2 or MaSIF output trees. Those inputs are required to
refit or rescore programs. The original 8,936-pair server cohort was checked
for nonempty sequences and file availability for all seven asset-path columns.

## Historical runs

The five primary expert-guided runs were launched as
`pmhctcr_final_terra_expert_on_m100_r1` through `r5`, each with a budget of
100 processed mutants and one mutation in flight. The frozen seed, prompts,
configuration, validator, and launcher scripts are the study implementation.
The paper's quantitative claims refer to saved run artifacts; do not rerun
search when auditing held-out results.


## Validator logs versus Appendix A.3

Every saved child stores 15 `stage_results` keys. Nine of them run the
code/validate/metrics path: `ValidateCodeStage`, `CallProgramFunction`,
`CallValidatorFunction`, `FetchMetrics`, `FetchArtifact`, `FormatterStage`,
`ComputeComplexityStage`, `MergeMetricsStage`, and `EnsureMetricsStage`.
The other six (`EvolutionaryStatisticsCollector`, `MutationContextStage`,
`ArchivePotentialGateStage`, `DescendantProgramIds`, `IntraMemoryStage`,
`MutationSuggestionStage`) record search bookkeeping and mutation context.
They are not archive-eligibility checks.

Appendix A.3's fourteen implementation-level checks are the mutation-apply
and `validate()` gates, grouped into ten reporting categories: patch
application and editable-scope compliance; Python syntax and AST parsing;
preservation of `entrypoint()` and the fit/score interface; isolated import
and instantiation; feature extraction; fitting; prediction length and
finiteness; validation metrics; archive descriptors; and diagnostic context.
A child is archived only when execution succeeds, required metrics are
finite, and both descriptors exist.

## Comparators

`analysis/heldout4_*.tsv` store the published comparator score summaries
(NetTCR-2.2, ATM-TCR, TEIM-Seq, TEPCAM, epiTCR, ERGO-II, TITAN, STAG-LLM,
SageTCR). Those rows use released weights; STAG-LLM and SageTCR used
Boltz-2 substituted structures as in Appendix E. This repository does not
include those external inference pipelines or weights, so the TSV files
verify reported table values and cannot rerun comparator prediction.

## Prompts and seed

The published seed is
[`initial_programs/python_patch_seed.py`](initial_programs/python_patch_seed.py).
The expert prompt is [`expert_hypotheses.txt`](expert_hypotheses.txt).

## Search traces

Compressed traces for Expert-guided, Unguided, Plain, Memory cards, and
Best-of-N are on Google Drive (see [`artifacts/`](../../artifacts/README.md)).
Score tables are in [`analysis/`](../../analysis/README.md).
