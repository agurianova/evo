# Archive Checklist

## Required Order (data loss if skipped)

1. **Run test evaluations** (Step 5) -- while Redis is still live
2. **Archive all runs** (Step 2) -- `archive_run.sh --upload` for each run
3. **Verify GitHub Release** (Step 3) -- at least 1 asset per run
4. **Flush Redis** -- only after archive + merge are complete

## What `archive_run.sh --upload` Produces

Each archive (`<label>_archive.tar.gz` on the GitHub Release) contains:
- `evolution_data.csv` -- all programs, all generations, all metrics
- `programs/*.py` -- source code of every evaluated program
- `top50.json` -- top 50 programs with full metadata

Also uploads `environment.txt` (pip freeze, OS, GPU) once per experiment.

## Parallelization

Archiving each run is independent (different Redis DBs, different archive files). Use `superpowers:dispatching-parallel-agents` for parallel archiving.

## Verification

After archiving, verify the GitHub Release:
```bash
gh release view "exp/$EXP" --json assets -q '.assets | length'
```
Must have at least 1 asset per run.

Also verify `environment_freeze.txt` is committed:
```bash
git log --oneline --max-count=1 -- "experiments/$EXP/environment_freeze.txt"
```

## Critical Rule

**Archive BEFORE flush** -- always run `archive_run.sh --upload` before flushing Redis DBs. Redis is ephemeral; data not exported is gone permanently.
