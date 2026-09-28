---
name: run-tests
description: Run the GigaEvo test suite and linter once, report results. Use when you need to verify code changes are correct before committing or launching an experiment.
argument-hint: [tests/path/or/file]
model: claude-haiku-4-5-20251001
---

# Run Tests: $ARGUMENTS

Run the test suite **once**. Do not re-run on failure — report what failed and stop.

## Step 1 — Determine scope

If `$ARGUMENTS` is provided, use it directly as the test path (skip to Step 2).

If `$ARGUMENTS` is empty, determine the **minimal test scope** from changed files:

```bash
# Get changed files (staged + unstaged)
CHANGED=$(git diff --name-only HEAD 2>/dev/null; git diff --name-only --cached 2>/dev/null) && CHANGED=$(echo "$CHANGED" | sort -u)
echo "Changed files:" && echo "$CHANGED"
```

Map changed source files to test directories:

| Changed path pattern | Test path |
|---------------------|-----------|
| `gigaevo/evolution/engine/` | `tests/evolution/` |
| `gigaevo/database/` | `tests/database/ tests/evolution/` |
| `gigaevo/runner/` | `tests/runner/ tests/evolution/` |
| `gigaevo/programs/stages/collector` | `tests/stages/test_collector*.py tests/evolution/` |
| `gigaevo/programs/stages/` | `tests/stages/` |
| `gigaevo/programs/` | `tests/programs/` |
| `gigaevo/evolution/strategies/` | `tests/strategies/` |
| `gigaevo/evolution/mutation/` | `tests/evolution/` |
| `gigaevo/llm/` | `tests/llm/` |
| `tests/` (direct test changes) | the changed test files themselves |
| `gigaevo/utils/` | `tests/` (full suite — utils are cross-cutting) |
| `config/` or `problems/` | `tests/integration/` |

If only test files changed, run just those files. If nothing maps, fall back to `tests/`.

Add `tests/integration/` if ANY source under `gigaevo/` changed (integration tests catch cross-module breaks).

Deduplicate and join paths into `$TEST_PATHS`.

## Step 2 — Run linter first (fast gate)

```bash
ruff check . && ruff format --check .
```

If linter fails, report and stop — no point running tests with lint errors.

## Step 3 — Run tests

```bash
$GIGAEVO_PYTHON -m pytest ${ARGUMENTS:-$TEST_PATHS} -x -m "not benchmark" --tb=short -q -p no:warnings 2>&1 | tee /tmp/pytest_results.txt; echo "EXIT:$?"
```

Key flags:
- `-x` — stop on first failure (saves minutes on NFS)
- `-m "not benchmark"` — skip benchmarks
- `-q -p no:warnings` — compact output

**Do not use `rtk` here** — RTK cannot accept an absolute path as a subcommand and will fail.

**Reading output**: Pytest `-q` prints dots (`.`) for passing tests, `F` for failures, `E` for errors. If the output is all dots with no `F` or `E` characters, all tests pass.

Extract the summary line:

```bash
grep -E "passed|failed|error" /tmp/pytest_results.txt | tail -3
```

## Step 4 — Report

Report in this format:

```
Lint  : clean  (or list violations)
Tests : X passed, Y failed  (or "all passed")
Scope : <test paths that were run>
```

If any tests failed, list each `FAILED tests/path::TestClass::test_name` with the short traceback from `/tmp/pytest_results.txt`. Do not re-run.

If all tests pass and lint is clean, say so and stop.
