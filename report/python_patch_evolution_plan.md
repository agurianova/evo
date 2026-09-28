# Python genome mutation with the unchanged pMHC-TCR runtime

Only three seams differ from the original pMHC-TCR experiment:

1. `Program.code` is treated as the complete Python genome. Mutable text is
   bounded by `EVOLVE-BLOCK-START/END` comments.
2. `PythonPatchMutationOperator` replaces the deterministic JSON operator. It
   selects one lineage parent and reads other completed programs only as prompt
   inspirations.
3. The operator gives the existing `MutationSuggestionStage` insights to the LLM,
   parses SEARCH/REPLACE blocks, and materializes a complete Python child.

Everything after mutation is the existing pMHC-TCR path:

```text
ValidateCodeStage
  -> CallProgramFunction(entrypoint)
  -> problems/pmhctcr/validate.py:validate
  -> FetchMetrics
  -> ProgramStorage
```

There is no custom `evaluate()` stage, evaluation pipeline, validator, storage,
or problem definition.

The marked seed is `problems/pmhctcr/initial_programs/seed.py`. Its
`entrypoint()` and the pMHC-TCR compiler/validator remain outside the editable
region.

Run the alternative mutator with the existing experiment:

```bash
python run.py experiment=pmhctcr mutation=python_patch
```

The normal `experiment=pmhctcr` command still selects `mutation=pmhctcr` and
therefore preserves the original implementation.
