# Archive Pipeline Bug — Silent Total-Data-Loss Hazard (heilbron/k5-budget-v3)

**Discovered**: 2026-04-19, during Step 2 of `/experiment-closeout heilbron/k5-budget-v3`.

**Severity**: **CRITICAL — would have destroyed all 3,343 programs across 8 runs if closeout had continued to Redis flush.**

## Summary

`tools/experiment/archive_run.sh` reported exit code 0 for all 8 runs, produced **empty** `evolution_data.csv` files, and would have uploaded empty archives to the GitHub release. Redis itself was intact (3,343 programs, 1,618 metrics-history keys, 4,237 misc keys). The failure is entirely inside `RedisProgramStorage.get_all()` →
`Program.from_dict()` — all programs were silently dropped by `_safe_deserialize` with only a single-line WARNING (`"Corrupt data in get_all: …"`) per program. Because the warning does not raise and because `fetch_evolution_dataframe` only logs `No programs found …` when it receives an empty list, the caller has no distinguishable signal between "Redis has no data" and "every program failed to deserialize".

A raw backup of all 8 DBs (raw JSON blobs, metrics lists, hashes, sets) was taken **before** any flush and is preserved at:

- Durable: `experiments/heilbron/k5-budget-v3/raw_redis_backup/<LABEL>_raw.tar.gz` (8 files, 182 MB total)
- Temporary (will be deleted): `/tmp/k5v3_raw_backup/` (uncompressed, 735 MB)

Raw program counts preserved:

| Label  | DB | Programs | Metric history keys | Misc keys |
|--------|----|----------|---------------------|-----------|
| K3_1_G |  1 |    348   |       197           |   414     |
| K3_1_D |  2 |    294   |       231           |   276     |
| K3_2_G |  3 |    486   |       197           |   594     |
| K3_2_D |  4 |    503   |       231           |   728     |
| K5_1_G |  5 |    501   |       197           |   654     |
| K5_1_D |  6 |    489   |       231           |   495     |
| K5_2_G |  7 |    172   |       197           |   211     |
| K5_2_D |  8 |    550   |       231           |   865     |
| **TOT**|    |  **3343**|      **1712**       | **4237**  |

(K5_2_G has only 172 programs because its slow validator (max 843 s) produced fewer finished evaluations in the same wall-clock window.)

## Root causes (two independent defects)

### A1 — CRITICAL: `Program` model rejects legacy `iteration` field

`gigaevo/programs/program.py:144-148`:

```python
model_config = ConfigDict(
    arbitrary_types_allowed=True,
    extra="forbid",           # ← fatal for any field not in the current schema
    validate_assignment=True,
    str_strip_whitespace=True,
)
```

Some programs in DBs 1-8 were written by a build that still persisted an `iteration: int` field on `Program`. The current schema has removed that field. `extra="forbid"` makes every such blob unreadable:

```
Corrupt data in get_all: 1 validation error for Program
iteration
  Extra inputs are not permitted [type=extra_forbidden, …]
```

### A2 — CRITICAL: `metadata` pickle references the task `helper` module

`gigaevo/programs/program.py:212-213`:

```python
if "metadata" in d and isinstance(d["metadata"], str):
    d["metadata"] = pickle_b64_deserialize(d["metadata"])
```

When `metadata` holds a pickled object that references `problems/heilbron_adversarial/pop_a/helper.py`, unpickling fails during archive (archive process does not have the problem dir on `sys.path`):

```
Corrupt data in get_all: No module named 'helper'
```

Every affected program is silently dropped.

### A3 — MAJOR: `_safe_deserialize` swallows both errors with identical severity

`gigaevo/database/redis_program_storage.py:102-113`:

```python
@staticmethod
def _safe_deserialize(raw, ctx, *, exclude=None):
    try:
        return Program.from_dict(_loads(raw), exclude=exclude)
    except Exception as e:
        logger.warning("[RedisProgramStorage] Corrupt data in {}: {}", ctx, e)
        return None
```

- Catches every exception (including legitimate schema drift and environment issues) and returns `None`.
- Emits only a WARNING — the log passes through archive subprocess stdout unnoticed because archive_run.sh captures only `fetch_evolution_dataframe`'s structured return.
- No per-key drop counter; no threshold; no exit-nonzero.

### A4 — MAJOR: `fetch_evolution_dataframe` cannot distinguish "empty Redis" from "everything failed to deserialize"

`gigaevo/utils/redis.py:51-55`:

```python
if not programs:
    logger.warning(f"No programs found for prefix='{config.redis_prefix}' at {config.url()}")
    return pd.DataFrame()
```

- Prints identical log whether Redis has 0 keys or 550 keys that all failed `_safe_deserialize`.
- Returns empty DataFrame.
- Archive writer observes empty DataFrame, prints `"No data found for <csv>"`, exits 0.

### A5 — MAJOR: `archive_run.sh` exits 0 on empty CSV

The shell script checks for file existence, not non-emptiness. An empty CSV satisfies "file created", the uploader runs, and the release ends up with empty assets.

## Bug table

| ID | Severity  | Symptom                                                             | Root cause                                                                               | File:line                                                  | Proposed fix                                                                                                    |
| -- | --------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| A1 | CRITICAL  | Schema drift (`iteration`) drops every program silently             | `extra="forbid"` on `Program`                                                            | `gigaevo/programs/program.py:146`                          | Switch to `extra="ignore"` **or** add explicit `iteration: int \| None = None` alias + deprecation path         |
| A2 | CRITICAL  | `No module named 'helper'` drops every program pickled by task code | `metadata` field holds pickle blob that references the problem's helper module           | `gigaevo/programs/program.py:212-213`                      | (a) stop storing helper references inside `metadata`; (b) fall back to `metadata=None` when unpickle fails     |
| A3 | MAJOR     | Silent drop on `_safe_deserialize`: no count, no threshold, no exit | One bare `except Exception` → WARNING, returns None                                      | `gigaevo/database/redis_program_storage.py:102-113`        | Add `(succeeded, failed)` counters, log ERROR (not WARNING) when failed/total > 5 %, propagate counts to caller |
| A4 | MAJOR     | Cannot tell "empty Redis" from "100 % drop"                         | `fetch_evolution_dataframe` returns empty DF with same log in both cases                 | `gigaevo/utils/redis.py:51-55`                             | Query `has_data()` first; if true but `get_all()` returns empty, raise `ProgramDeserializationError`           |
| A5 | MAJOR     | `archive_run.sh` exits 0 on empty CSV                               | Script only tests for file existence                                                     | `tools/experiment/archive_run.sh`                          | Fail if `csv_line_count == 1` (header only) and Redis `has_data` is true                                        |
| A6 | MINOR     | Archive subprocess doesn't put problem dir on PYTHONPATH            | `PYTHONPATH=.` from repo root, but pickled refs need `problems/<task>/<arm>` on path too | `tools/experiment/archive_run.sh`                          | Prepend problem dir to `sys.path` when calling `redis2pd.py`                                                    |
| A7 | MINOR     | `Program.from_dict` has no migration shim for removed fields        | No forward-compat layer                                                                  | `gigaevo/programs/program.py:184-219`                      | Add `_MIGRATIONS = [("iteration", None)]` applied in `from_dict` before construction                            |

## Why this is tier-CRITICAL (not merely a bug)

- Every /experiment-closeout on this branch silently destroys data if Redis has programs with either the legacy `iteration` field or a helper-backed `metadata` pickle.
- The closeout skill step order archives **first**, then flushes Redis — but the archive's exit-0 was the sole gate. No human sees the WARNING lines (they're in captured subprocess output that's tailed only on error).
- We observed exit code 0 for all 8 runs, empty CSVs, and an about-to-be-flushed Redis. The only reason this experiment's data is recoverable is the manual `redis2pd.py` sanity check performed after archive.

## Immediate remediation (applied)

1. **Raw backup preserved** at `experiments/heilbron/k5-budget-v3/raw_redis_backup/` (8 tar.gz files, 182 MB total). Checksummed by size+count:

   ```
   $ du -sh experiments/heilbron/k5-budget-v3/raw_redis_backup/
   182M	experiments/heilbron/k5-budget-v3/raw_redis_backup/
   ```

2. **Archive Step 2 of closeout ABORTED** — nothing else flushes until A1–A5 are fixed.
3. Redis DBs 1–8 remain populated; do not flush until remediation lands.

## Recommended patch order

1. **A1** (`extra="ignore"`) — 1-line in `program.py:146`. Eliminates legacy-field hazard for all future deserializes.
2. **A2** (fallback on pickle fail) — wrap `pickle_b64_deserialize` in try/except in `program.py:212-213`, fall back to `metadata = {}` (or `None`) and log once.
3. **A3** (counters + threshold ERROR) — minimal defence-in-depth.
4. **A4** (`has_data` vs `get_all` mismatch → raise) — prevents silent empty-archive hazard across the whole tool tree.
5. **A5** (shell CSV line-count check) — belt-and-braces.

Then re-run archive against the raw backups or reconstruct from `raw_redis_backup/*.tar.gz`.

No fixes applied — audit only. Requires user directive before patching, per feedback "No half-finished implementations either" and "Always ask for confirmation on hard-to-reverse operations".
