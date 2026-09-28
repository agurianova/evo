# Paper analysis tables

- Appendix H TSVs were derived from saved validation traces. They contain
  program identifiers, the 96-parent background table, class eligibility, and
  exact p-values with Holm correction. Rebuild them with
  `scripts/export_mutation_tables.py` when the corresponding expert-on traces
  are available (not stored in this Git repository).
- The heldout4 TSV files preserve per-target and macro score summaries for the
  published predictor comparison. These are descriptive scores from external
  published weights, with Boltz-2 substitutions for the two structure-aware
  predictors. Comparator inference pipelines and weights are not included; the
  TSV files allow checking reported table values, not repeating those predictions.
- Full search logs and LLM I/O traces are omitted here because of size. If a
  public trace archive is posted later, `scripts/verify_paper_artifacts.py`
  checks Table 2, Table 3, and Figure 4 summaries against it.

Search logs are not in this Git snapshot. They will be linked from [`artifacts/README.md`](../artifacts/README.md) after they are checked against the paper and posted separately.
