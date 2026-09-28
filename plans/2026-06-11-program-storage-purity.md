# Program Storage Abstraction Purity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `ProgramStorage` becomes the single, complete storage abstraction: every storage operation (including read-only enforcement) lives on the ABC — consolidating/refactoring overlapping ABC methods where that simplifies the contract — concrete `RedisProgramStorage` construction happens only in Hydra config + one factory module, all other code receives storage by reference typed against the ABC, all `redis_*` names denoting *abstract* storage are renamed, and the storage test suite is parametrized over backends.

**Architecture:** Five moves: (1) lift every storage-touching method onto the ABC (`size`, `has_data`, `remove`, `flushdb`→`clear`, `read_only` + `require_writable`, `key_prefix`, async-context-manager) and consolidate redundant ABC surface, leaving ZERO impl-only public methods (`with_redis` goes private as `_with_redis` — purely Redis-internal, consumed only by `RedisArchiveStorage`); (2) backend-parametrized contract tests (`tests/database/storage_backends.py` registry) so any future backend runs the same suite; (3) inject a Hydra-wired `ArchiveStorageFactory` so strategies contain zero Redis imports; (4) confine concrete construction to `config/redis/default.yaml` + new `gigaevo/database/factory.py` (sole non-Hydra construction point, used by CLI run-locators); (5) rename abstract-storage `redis_*` names (`redis_storage` node → `program_storage`, `IslandConfig.redis_prefix` → `archive_prefix`, `RedisTopProgramsLoader` → `TopProgramsLoader`, `flushdb` → `clear`, delete `utils/redis.py`).

**Tech Stack:** Python 3.12, Pydantic, Hydra/OmegaConf, redis.asyncio, pytest + fakeredis, ruff, gitnexus (impact/rename).

---

## ⚠️ Execution constraints

1. **Live runs:** db11/db12 House experiments may still be RUNNING. Per `feedback_no_import_changes_mid_run`, do NOT edit the tree live runs launched from. Execute on branch `storage-purity` in a **git worktree**; merge only after they finish (verify via `lsof` on live logfiles, not `ps`).
2. **GitNexus:** `gitnexus_impact({target: "<symbol>", direction: "upstream"})` before editing each listed symbol; `gitnexus_rename(..., dry_run: true)` before every symbol rename; `gitnexus_detect_changes()` before each commit. Do NOT run `gitnexus analyze` (user manages reindexing).
3. **Tests:** always via `/run-tests` targeting specific paths — never bare `pytest tests/`.
4. **Commits:** wait for user commit approval before every commit. "Commit" below means stage + request approval + commit on approval.
5. **Ruff:** `/home/jovyan/.mlspace/envs/evo/bin/ruff check . && /home/jovyan/.mlspace/envs/evo/bin/ruff format --check .` before each commit.
6. **Exceptions:** reuse `StorageError` lineage from `gigaevo/exceptions.py` (per `feedback_logging_exceptions`); the read-only guard already raises `StorageError` — keep that type.

## Verified inventory (2026-06-11)

**Impl-only public methods** (from `inspect` diff): `flushdb`, `has_data`, `remove`, `size`, `with_redis`. Impl-only dunders worth lifting: `__aenter__`/`__aexit__`. Read-only guard: `RedisProgramStorage._check_write_allowed` (`redis_program_storage.py:86-92`) raises `StorageError`; ABC has no `read_only`/`key_prefix` concept. ABC `__init__` (`program_storage.py:143-144`) only sets `self.snapshot`.

**Leaks:**

| Leak | Location |
|---|---|
| Concrete type-hints + non-ABC calls in entry path | `run.py:12,37,41,54,72` |
| Dead `check_redis_resume` typed on concrete class | `gigaevo/utils/experiment.py` |
| Loader Protocol + loaders typed on concrete class; inline source construction | `gigaevo/problems/initial_loaders.py:9-17,24,72-82` |
| Strategies require concrete class to build `RedisArchiveStorage` | `gigaevo/evolution/strategies/island.py:8,55,69-75`, `multi_island.py:8,31,42` |
| `archive_storage.py` reads `program_storage.config.key_prefix` (concrete attr) | `gigaevo/evolution/storage/archive_storage.py` |
| Inline read-only constructions | `gigaevo/utils/redis.py:31-43`, `gigaevo/memory/ideas_tracker/redis_loader.py:32-39`, `tools/lineage.py:37`, `tools/profiler.py:136`, `initial_loaders.py:73` |
| Hydra node `redis_storage` (21 `${ref:}` in 12 YAMLs) + code refs | `config/redis/default.yaml:15`, `run.py:41`, `gigaevo/monitoring/emit.py:73` |
| Ugly abstract-storage `redis_*` names | `IslandConfig.redis_prefix` (island.py:55), `RedisTopProgramsLoader`, `flushdb`, module `gigaevo/utils/redis.py`, `config/loader/redis_selection.yaml` |

**Redis-honest names — KEEP (backend-specific by nature, listed so the rename sweep doesn't overreach):** `config/redis/` group + `cfg.redis.*` connection fields (host/port/db/resume select the Redis backend); `RedisRunConfig` run locator + CLI `-r prefix@db` addressing (moves into `gigaevo/database/factory.py` but keeps its name); ideas_tracker CLI `--redis-prefix` flags; `utils/dataframes.py` frontier readers (metrics-tracker keys, not ProgramStorage); `prompts/fetcher.py` `main_redis_prefix` (prompt co-evolution, out of scope); `config/pipeline/adversarial*.yaml` `opponent_redis_prefix` (out of scope); `"redis_storage"` telemetry label in `gigaevo/database/redis/metrics.py:25` (metric-path consumers depend on it); `RedisArchiveStorage` internals — it is the Redis impl pairing and may call the private `_with_redis` hook (renamed from public `with_redis` in Task 1).

**Non-goals:** migration bus, metrics tracker backends, memory backend internals, prompt co-evolution sync, `cli/flush_ops.py` raw-client flush (administers a whole DB, inherently backend-level), disk backend implementation (separate project — this plan makes it *pluggable*).

---

### Task 0: Worktree + baseline

**Files:** none (setup)

- [ ] **Step 1: Confirm no live run uses this tree** — locate db11/db12 run logfiles (tmux panes / experiment manifests), `lsof <logfile>` to find live PIDs and their CWDs. Record findings.
- [ ] **Step 2: Create worktree** via `superpowers:using-git-worktrees`, branch `storage-purity`.
- [ ] **Step 3: Baseline tests** — `/run-tests` targeting `tests/database tests/evolution tests/utils tests/config`. Record pass count; later tasks must keep these green.

---

### Task 1: Complete the ABC — every storage operation lives on `ProgramStorage`

**Files:**
- Modify: `gigaevo/database/program_storage.py` (ABC `__init__` + new methods; consolidation pass)
- Modify: `gigaevo/database/redis_program_storage.py` (delegate guard, rename `flushdb`→`clear`, add `key_prefix` property, pass `read_only` to super)
- Modify: `tests/database/test_redis_storage.py:559` (`flushdb` call site)
- Test: `tests/database/test_program_storage_defaults.py` (create)

- [ ] **Step 1: Impact checks** — `gitnexus_impact` upstream on `ProgramStorage`, `RedisProgramStorage`, `flushdb`, `remove`, `with_redis`. Report blast radius. Confirm via grep that `flushdb`/`remove` callers are only `tests/database/test_redis_storage.py` (verified 2026-06-11: lines 60, 341, 550, 559, 1020, 1044, 1064) and internal, and that `with_redis` callers are only `archive_storage.py`.

- [ ] **Step 2: Consolidation audit (refactoring the ABC is in scope)** — list the ABC's transition/query surface (`transition_status`, `atomic_state_transition`, `fast_state_transition`, `batch_transition_*`, `get_all_by_status` vs `get_ids_by_status` vs `count_by_status`) and their callers via `gitnexus_context` on each. Where two methods are strict subsets (one always derivable from the other with no performance loss at existing call sites), merge: keep the general one abstract, re-express the narrow one as a default implementation on the ABC (NOT deleted — call sites stay valid). Produce a short table (method → keep-abstract / demote-to-default / unchanged + caller count) and apply it. Rule: zero call-site signature changes; consolidation only moves implementations onto the ABC as defaults. If the audit finds nothing safely mergeable, record that and move on — do not force it.

- [ ] **Step 3: Check async test convention** — open `tests/database/test_redis_storage.py`, note the async marker style; mirror it below.

- [ ] **Step 4: Write the failing test**

```python
"""Default implementations and contracts on the ProgramStorage ABC."""

from __future__ import annotations

from typing import Any

import pytest

from gigaevo.database.program_storage import ProgramStorage
from gigaevo.exceptions import StorageError


class _StubStorage(ProgramStorage):
    """Minimal concrete subclass: only get_all_program_ids is functional."""

    def __init__(self, ids: list[str], *, read_only: bool = False) -> None:
        super().__init__(read_only=read_only)
        self._ids = ids
        self.closed = False

    @property
    def key_prefix(self) -> str:
        return "stub"

    async def add(self, program) -> None: raise NotImplementedError
    async def update(self, program) -> None: raise NotImplementedError
    async def get(self, program_id: str): raise NotImplementedError
    async def mget(self, program_ids, *, exclude=None): raise NotImplementedError
    async def exists(self, program_id: str) -> bool: raise NotImplementedError
    async def remove(self, program_id: str) -> None: raise NotImplementedError
    async def clear(self) -> None: raise NotImplementedError
    async def publish_status_event(self, status: str, program_id: str, extra: dict[str, Any] | None = None) -> None: raise NotImplementedError
    async def get_all(self, *, exclude=None): raise NotImplementedError
    async def get_all_by_status(self, status: str, *, exclude=None): raise NotImplementedError
    async def get_ids_by_status(self, status: str): raise NotImplementedError
    async def count_by_status(self, status: str) -> int: raise NotImplementedError
    async def transition_status(self, program_id: str, old, new) -> None: raise NotImplementedError
    async def atomic_state_transition(self, program, old_state, new_state) -> None: raise NotImplementedError
    async def acquire_instance_lock(self) -> bool: return True
    async def release_instance_lock(self) -> None: pass
    async def renew_instance_lock(self) -> bool: return True

    async def close(self) -> None:
        self.closed = True

    async def get_all_program_ids(self) -> list[str]:
        return list(self._ids)


@pytest.mark.asyncio
async def test_size_defaults_to_program_id_count():
    assert await _StubStorage(["a", "b", "c"]).size() == 3


@pytest.mark.asyncio
async def test_has_data_reflects_emptiness():
    assert await _StubStorage(["a"]).has_data() is True
    assert await _StubStorage([]).has_data() is False


def test_require_writable_raises_when_read_only():
    s = _StubStorage([], read_only=True)
    assert s.read_only is True
    with pytest.raises(StorageError, match="read-only"):
        s.require_writable("add")


def test_require_writable_noop_when_writable():
    _StubStorage([]).require_writable("add")


@pytest.mark.asyncio
async def test_async_context_manager_closes():
    async with _StubStorage([]) as s:
        assert s.closed is False
    assert s.closed is True
```

(If Step 2's consolidation demoted any method the stub overrides, drop that override accordingly. If `StorageError` lives elsewhere than `gigaevo/exceptions.py`, import from wherever `redis_program_storage.py` imports it — keep the existing class, do not invent a new one.)

- [ ] **Step 5: Run test, verify it fails** — `/run-tests` targeting `tests/database/test_program_storage_defaults.py`. Expected: FAIL (`__init__` rejects `read_only` kwarg; `remove`/`clear`/`key_prefix` not abstract on ABC yet).

- [ ] **Step 6: Extend the ABC** — in `gigaevo/database/program_storage.py`:

Replace `__init__` (lines 143-144):

```python
    def __init__(self, *, read_only: bool = False) -> None:
        self.snapshot = PopulationSnapshot()
        self.read_only = read_only
```

Add alongside the other abstract methods (mirror surrounding style):

```python
    @property
    @abstractmethod
    def key_prefix(self) -> str:
        """Namespace prefix isolating this run's data within the backend."""

    @abstractmethod
    async def remove(self, program_id: str) -> None: ...

    @abstractmethod
    async def clear(self) -> None:
        """Delete ALL data for this storage (programs, indices, locks)."""

    async def size(self) -> int:
        """Total number of stored programs. Override for a faster backend path."""
        return len(await self.get_all_program_ids())

    async def has_data(self) -> bool:
        """True if any program exists. Override for a faster backend path."""
        return await self.size() > 0

    def require_writable(self, operation: str) -> None:
        """Raise StorageError if a write is attempted on a read-only instance."""
        if self.read_only:
            raise StorageError(
                f"Cannot perform '{operation}' in read-only mode. "
                f"Create storage without read_only=True for write operations."
            )

    async def __aenter__(self) -> "ProgramStorage":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()
```

Add the `StorageError` import (same source module `redis_program_storage.py` uses). Apply the Step-2 consolidation table here too.

- [ ] **Step 7: Update `RedisProgramStorage`** — in `gigaevo/database/redis_program_storage.py`:
  - `__init__`: call `super().__init__(read_only=config.read_only)` (currently bare `super().__init__()` — find and adjust; KEEP `self.config.read_only` as the config field).
  - Add property:

```python
    @property
    def key_prefix(self) -> str:
        return self.config.key_prefix
```

  - `_check_write_allowed` (lines 86-92) → delete; replace its ~10 call sites with `self.require_writable("<op>")` (the lifted guard preserves the exact `StorageError` text).
  - Rename `flushdb` → `clear` (gitnexus_rename dry-run first; expect call sites: internal `redis_program_storage.py:795` region + `tests/database/test_redis_storage.py:559`).
  - Rename `with_redis` → `_with_redis` (gitnexus_rename dry-run first; verified callers 2026-06-11: 9 sites, all in `gigaevo/evolution/storage/archive_storage.py` — lines 109, 115, 121, 127, 236, 257, 286, 314, 334 — plus the def itself; it is purely Redis-internal plumbing, not ABC surface, and `RedisArchiveStorage` is the Redis impl pairing so calling the private hook is sanctioned. Update the method's docstring: it is no longer a "compatibility shim for external code" — external code must use the ABC).
  - Delete the impl's own `__aenter__`/`__aexit__` ONLY if byte-equivalent to the ABC defaults — read them first; if they do extra work (e.g. eager connect), keep the override.
  - Delete any impl methods the Step-2 consolidation demoted to ABC defaults, unless the impl version is a genuinely faster backend path (pipelined/batched) — then keep it as an override.

- [ ] **Step 8: Verify completeness** — rerun the inspect diff:

```bash
/home/jovyan/.mlspace/envs/evo/bin/python3 - <<'EOF'
import inspect
from gigaevo.database.program_storage import ProgramStorage
from gigaevo.database.redis_program_storage import RedisProgramStorage
abc_m = {n for n,_ in inspect.getmembers(ProgramStorage, inspect.isfunction)}
impl_m = {n for n,_ in inspect.getmembers(RedisProgramStorage, inspect.isfunction)}
print(sorted(n for n in impl_m - abc_m if not n.startswith('_')))
EOF
```

Expected: `[]` — zero impl-only public methods; the concrete class's public surface IS the ABC. (`_with_redis` is private and exempt by the filter.)

- [ ] **Step 9: Run tests** — `/run-tests` targeting `tests/database/`. Expected: all PASS (including renamed `clear` call).

- [ ] **Step 10: Ruff + commit** — `refactor(storage): lift size/has_data/remove/clear/read-only/key_prefix onto ProgramStorage ABC`

---

### Task 2: Backend-parametrized storage contract tests

**Files:**
- Create: `tests/database/storage_backends.py`
- Create: `tests/database/test_storage_contract.py`
- Modify: `tests/conftest.py` (existing `fakeredis_storage` fixture delegates to the registry)

- [ ] **Step 1: Read the existing fixture** — open `tests/conftest.py`, find `fakeredis_storage`; note exactly how it builds `RedisProgramStorage` over fakeredis (patching/injection mechanism, prefix, teardown).

- [ ] **Step 2: Create the backend registry** — `tests/database/storage_backends.py`:

```python
"""Registry of ProgramStorage backends the contract suite runs against.

Adding a backend = appending one StorageBackend entry; the entire
contract suite in test_storage_contract.py then applies to it.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Callable

from gigaevo.database.program_storage import ProgramStorage


@dataclass(frozen=True)
class StorageBackend:
    id: str
    make: Callable[..., "AsyncIterator[ProgramStorage]"]  # kwargs: read_only=False


@asynccontextmanager
async def _fakeredis_storage(*, read_only: bool = False) -> AsyncIterator[ProgramStorage]:
    # Lift the construction + teardown body of the existing
    # `fakeredis_storage` fixture (tests/conftest.py) here verbatim,
    # adding read_only passthrough to RedisProgramStorageConfig.
    ...


BACKENDS: list[StorageBackend] = [
    StorageBackend(id="redis-fake", make=_fakeredis_storage),
]
```

The `...` body is filled from Step 1's reading — existing code being moved, not new design. Then rewrite the `fakeredis_storage` fixture in `tests/conftest.py` to delegate:

```python
@pytest_asyncio.fixture
async def fakeredis_storage():
    from tests.database.storage_backends import _fakeredis_storage

    async with _fakeredis_storage() as storage:
        yield storage
```

(match the project's actual async-fixture decorator from Step 1; keep the old fixture name so the ~10 dependent test files need zero edits).

- [ ] **Step 3: Write the contract suite** — `tests/database/test_storage_contract.py`:

```python
"""Behavioral contract every ProgramStorage backend must satisfy."""

from __future__ import annotations

import pytest

from gigaevo.exceptions import StorageError
from gigaevo.programs.program import Program

from tests.database.storage_backends import BACKENDS, StorageBackend


@pytest.fixture(params=BACKENDS, ids=lambda b: b.id)
def backend(request) -> StorageBackend:
    return request.param


def _program(code: str = "def f(): return 1") -> Program:
    return Program(code=code, iteration=0)


@pytest.mark.asyncio
async def test_add_get_roundtrip(backend):
    async with backend.make() as storage:
        prog = _program()
        await storage.add(prog)
        fetched = await storage.get(prog.id)
        assert fetched is not None and fetched.id == prog.id
        assert fetched.code == prog.code


@pytest.mark.asyncio
async def test_exists_and_remove(backend):
    async with backend.make() as storage:
        prog = _program()
        await storage.add(prog)
        assert await storage.exists(prog.id) is True
        await storage.remove(prog.id)
        assert await storage.exists(prog.id) is False


@pytest.mark.asyncio
async def test_size_and_has_data(backend):
    async with backend.make() as storage:
        assert await storage.has_data() is False
        await storage.add(_program("def a(): return 1"))
        await storage.add(_program("def b(): return 2"))
        assert await storage.size() == 2
        assert await storage.has_data() is True


@pytest.mark.asyncio
async def test_clear_wipes_everything(backend):
    async with backend.make() as storage:
        await storage.add(_program())
        await storage.clear()
        assert await storage.has_data() is False


@pytest.mark.asyncio
async def test_get_all_returns_added_programs(backend):
    async with backend.make() as storage:
        ids = set()
        for i in range(3):
            p = _program(f"def f(): return {i}")
            await storage.add(p)
            ids.add(p.id)
        assert {p.id for p in await storage.get_all()} == ids


@pytest.mark.asyncio
async def test_read_only_rejects_writes(backend):
    async with backend.make(read_only=True) as storage:
        with pytest.raises(StorageError):
            await storage.add(_program())


@pytest.mark.asyncio
async def test_key_prefix_is_exposed(backend):
    async with backend.make() as storage:
        assert isinstance(storage.key_prefix, str) and storage.key_prefix
```

(Adjust `Program(...)` construction to match factories used in `tests/database/test_redis_storage.py` if it requires more fields; check how the existing read-only tests at `test_redis_storage.py:540-565` arrange data and mirror that.)

- [ ] **Step 4: Add status-transition contract coverage** — port these three existing tests from `tests/database/test_redis_storage.py` into the contract file, replacing the `fakeredis_storage` fixture with `backend.make()`: the basic `transition_status` happy-path test, the `atomic_state_transition` conflict test, and the `count_by_status` test (locate by grepping those method names in the file; copy bodies, keep assertions identical). These exercise `ProgramState` semantics every backend must honor.

- [ ] **Step 5: Run** — `/run-tests` targeting `tests/database/`. Expected: contract suite passes for `redis-fake`; pre-existing suites green (fixture delegation is behavior-preserving).

- [ ] **Step 6: Ruff + commit** — `test(storage): backend-parametrized ProgramStorage contract suite`

---

### Task 3: Entry path (`run.py`) + `check_storage_resume` against the ABC

**Files:**
- Modify: `gigaevo/utils/experiment.py` (full rewrite)
- Modify: `run.py:12,37,41,54-73,107-108`
- Test: `tests/utils/test_experiment.py` (create)

- [ ] **Step 1: Impact check** — `gitnexus_impact` on `check_redis_resume` (expect zero callers — dead) and `run_experiment`.

- [ ] **Step 2: Write the failing test**

```python
"""check_storage_resume behavior against a fake ProgramStorage."""

from __future__ import annotations

import pytest

from gigaevo.utils.experiment import check_storage_resume


class _FakeStorage:
    def __init__(self, has_data: bool) -> None:
        self._has_data = has_data

    async def has_data(self) -> bool:
        return self._has_data


@pytest.mark.asyncio
async def test_raises_when_data_exists_and_no_resume():
    with pytest.raises(RuntimeError, match="not empty"):
        await check_storage_resume(
            _FakeStorage(True), resume=False,
            location="Redis DB 0 at localhost:6379",
            flush_hint="gigaevo flush --db 0 --confirm",
        )


@pytest.mark.asyncio
async def test_resumes_when_data_exists_and_resume_set():
    assert await check_storage_resume(
        _FakeStorage(True), resume=True, location="db", flush_hint="hint",
    ) is True


@pytest.mark.asyncio
async def test_fresh_start_when_empty():
    assert await check_storage_resume(
        _FakeStorage(False), resume=False, location="db", flush_hint="hint",
    ) is False
    assert await check_storage_resume(
        _FakeStorage(False), resume=True, location="db", flush_hint="hint",
    ) is False
```

- [ ] **Step 3: Run test, verify it fails** — Expected: `ImportError: cannot import name 'check_storage_resume'`.

- [ ] **Step 4: Rewrite `gigaevo/utils/experiment.py`** (the dead `check_redis_resume` + `REDIS_NOT_EMPTY_ERROR` are deleted):

```python
"""Experiment lifecycle utilities."""

from __future__ import annotations

from loguru import logger

from gigaevo.database.program_storage import ProgramStorage

STORAGE_NOT_EMPTY_ERROR = """
ERROR: program storage is not empty!

  {location} contains existing programs.

To prevent accidental data loss, flush it manually:
  {flush_hint}

Or set resume=true to continue with existing data:
  python run.py redis.resume=true ...
"""


async def check_storage_resume(
    storage: ProgramStorage,
    *,
    resume: bool,
    location: str,
    flush_hint: str,
) -> bool:
    """Decide fresh-start vs resume; refuse to clobber existing data.

    Returns True iff existing data should be resumed.
    Raises RuntimeError if storage has data and resume is False.
    """
    has_data = await storage.has_data()
    if has_data and not resume:
        logger.error(
            STORAGE_NOT_EMPTY_ERROR.format(location=location, flush_hint=flush_hint)
        )
        raise RuntimeError(f"{location} is not empty. Flush manually to proceed.")
    if has_data:
        logger.info("Resuming experiment: {} has existing data", location)
    elif resume:
        logger.info("Resume requested but {} is empty. Starting fresh.", location)
    return has_data
```

- [ ] **Step 5: Run test, verify pass.**

- [ ] **Step 6: Rewire `run.py`** —
  - line 12: `from gigaevo.database.redis_program_storage import RedisProgramStorage` → `from gigaevo.database.program_storage import ProgramStorage`; add `from gigaevo.utils.experiment import check_storage_resume`.
  - lines 37, 41: local var `redis_storage` → `storage`, typed `ProgramStorage | None` / `ProgramStorage`; attribute read becomes `config_with_instances.program_storage` after Task 5's node rename (if executing this task first, keep `.redis_storage` here and flip it in Task 5 Step 3, which lists it).
  - replace lines 54-62 with:

```python
        resume = await check_storage_resume(
            storage,
            resume=bool(cfg.redis.get("resume", False)),
            location=f"Redis DB {cfg.redis.db} at {cfg.redis.host}:{cfg.redis.port}",
            flush_hint=f"gigaevo flush --db {cfg.redis.db} --confirm",
        )
        if resume:
```

  keeping the existing resume body under `if resume:` and the `else:` seed branch unchanged; rename remaining `redis_storage` references (lines 52, 65, 72, 75, 107-108) to `storage`.
  (`cfg.redis.*` reads stay: the `redis` config group selects the Redis backend and is the right home for its connection/resume knobs. The flush hint switches from raw `redis-cli` to canonical `gigaevo flush`.)

- [ ] **Step 7: Smoke** — `/home/jovyan/.mlspace/envs/evo/bin/python3 run.py problem.name=tabular/california --cfg job > /dev/null`. Expected: exit 0.

- [ ] **Step 8: Ruff + commit** — `refactor(run): entry path depends on ProgramStorage ABC; consolidate resume check`

---

### Task 4: Loaders — ABC types + Hydra-built source (`TopProgramsLoader`)

**Files:**
- Modify: `gigaevo/problems/initial_loaders.py`
- Modify: `config/loader/redis_selection.yaml` → rename to `config/loader/top_programs.yaml`
- Test: extend `tests/` coverage only if a loader test exists (`grep -rln initial_loaders tests/`)

- [ ] **Step 1: Impact + config recon** — `gitnexus_impact` on `RedisTopProgramsLoader`, `InitialProgramLoader`. Read `config/loader/redis_selection.yaml` fully (current knobs: source host/port/db, key_prefix, metric_key, …). Grep selectors: `grep -rn "redis_selection" config/ docs/ experiments/ --include='*.yaml' --include='*.md'`.

- [ ] **Step 2: Retype + inject source** — rewrite `gigaevo/problems/initial_loaders.py` imports and signatures:

```python
from gigaevo.database.program_storage import ProgramStorage
```

(drop the `RedisProgramStorage`/`RedisProgramStorageConfig` import entirely)

```python
class InitialProgramLoader(Protocol):
    async def load(self, storage: ProgramStorage) -> list[Program]: ...
```

`DirectoryProgramLoader.load` → `storage: ProgramStorage`.

`RedisTopProgramsLoader` → rename class to `TopProgramsLoader` (gitnexus_rename dry-run first) and replace constructor + load:

```python
class TopProgramsLoader:
    """Seed a run with the top-N programs of another run's storage."""

    def __init__(
        self,
        *,
        source: ProgramStorage,
        metric_key: str,
        higher_is_better: bool,
        top_n: int = 50,
    ):
        self.source = source
        self.metric_key = metric_key
        self.higher_is_better = higher_is_better
        self.top_n = top_n

    async def load(self, storage: ProgramStorage) -> list[Program]:
        async with self.source as source:
            all_programs = await source.get_all()
            ...
```

The `...` is the EXISTING selection/copy body from `initial_loaders.py:84-120` unchanged (sentinel sort, lineage filtering, `await storage.add(copy)`), with two edits: metadata `"source_db": self.source_db` → `"source_prefix": source.key_prefix` (db number no longer known here; prefix identifies the source run), and the manual `try/finally close` deleted (the `async with` from Task 1 owns lifecycle).

- [ ] **Step 3: Rewrite the loader config** — create `config/loader/top_programs.yaml` (delete `redis_selection.yaml`; legacy configs are not migrated per standing feedback), preserving every existing knob/default from Step 1's reading, with the source built by Hydra:

```yaml
# Seed from the top-N programs of another run.
program_loader:
  _target_: gigaevo.problems.initial_loaders.TopProgramsLoader
  source:
    _target_: gigaevo.database.redis_program_storage.RedisProgramStorage
    config:
      _target_: gigaevo.database.redis_program_storage.RedisProgramStorageConfig
      redis_url: redis://<source_host>:<source_port>/<source_db>
      key_prefix: <source_prefix>
      read_only: true
  metric_key: <metric_key>
  higher_is_better: <higher_is_better>
  top_n: <top_n>
```

⚠️ The `<...>` placeholders MUST become the same interpolation style (`${...}` roots, `# @package` directive) and knob names that `redis_selection.yaml` uses today — copy its structure, swap only the `_target_` shape (it currently passes host/port/db as scalars to the loader; now they feed the nested storage node). Verify with `--cfg job` before moving on.

- [ ] **Step 4: Run + smoke** — `/run-tests` on any loader-covering tests from Step 1; `python run.py problem.name=tabular/california loader=top_programs <required source knobs> --cfg job` resolves.

- [ ] **Step 5: Docs** — grep `docs/USAGE.md`, `tools/README.md`, `README.md` for `redis_selection` / `RedisTopProgramsLoader`; update mentions in this commit (canonical-doc rule).

- [ ] **Step 6: Ruff + commit** — `refactor(loaders): TopProgramsLoader takes an injected ProgramStorage source (Hydra-built)`

---

### Task 5: Hydra node rename `redis_storage` → `program_storage`

**Files:**
- Modify: `config/redis/default.yaml:15` (+ comment at lines 9-12)
- Modify: 21 `${ref:redis_storage}` refs in: `config/algorithm/{multi_island,single_island,single_island_2d,single_island_no_distant_parents,topology_3d,topology_3d_ret}.yaml`, `config/algorithm/tabular/2d_local_ood.yaml`, `config/evolution/{default,steady_state}.yaml`, `config/pipeline/{custom,auto,adversarial_asymmetric,intra_extra_memory}.yaml`, `config/runner/default.yaml`
- Modify: `run.py:41`, `gigaevo/monitoring/emit.py:73`

- [ ] **Step 1: Exhaustive ref list** — `grep -rn "redis_storage" config/ run.py gigaevo/ tools/ experiments/ bin/ docs/ tests/ --include='*.yaml' --include='*.py' --include='*.md' --include='*.sh' | grep -v fakeredis_storage | grep -v 'database/redis/metrics.py'`. Every hit gets renamed here or is explicitly excluded (telemetry label; archived experiment dirs under `experiments/` are historical records — leave).
- [ ] **Step 2: Rename node + refs** — `config/redis/default.yaml` `redis_storage:` → `program_storage:`; mechanical `${ref:redis_storage}` → `${ref:program_storage}` across the 12 files.
- [ ] **Step 3: Code refs** — `run.py:41` (`.redis_storage` → `.program_storage`, if not already flipped in Task 3), `gigaevo/monitoring/emit.py:73` (`cfg.redis_storage.config.key_prefix` → `cfg.program_storage.config.key_prefix`), plus any test/helper hits from Step 1.
- [ ] **Step 4: Docs** — update Step-1 hits in `docs/`, `tools/README.md`, `gigaevo/experiment/README.md` in this commit.
- [ ] **Step 5: Verify** — `python run.py problem.name=tabular/california --cfg job > /dev/null` and `... algorithm=tabular/2d_local_ood --cfg job > /dev/null`; `/run-tests` targeting `tests/config/`.
- [ ] **Step 6: Ruff + commit** — `refactor(config): rename redis_storage node to program_storage`

---

### Task 6: ArchiveStorageFactory — Hydra-wired, strategies go Redis-free

**Files:**
- Modify: `gigaevo/evolution/storage/archive_storage.py` (factory classes; `key_prefix` attr access)
- Modify: `gigaevo/evolution/strategies/island.py` (ABC types, required factory, `redis_prefix` → `archive_prefix`)
- Modify: `gigaevo/evolution/strategies/multi_island.py` (ABC types, factory passthrough)
- Modify: `config/redis/default.yaml` (new `archive_storage_factory:` node)
- Modify: 7 algorithm YAMLs (factory ref)
- Modify: test call sites (~15, listed in Step 8)
- Test: `tests/evolution/test_archive_storage_factory.py` (create)

- [ ] **Step 1: Impact checks** — `gitnexus_impact` upstream on `MapElitesIsland`, `MapElitesMultiIsland`, `RedisArchiveStorage`, `IslandConfig.redis_prefix`. Check re-exports: `grep -rn "MapElitesIsland\|RedisArchiveStorage" gigaevo/evolution/strategies/__init__.py gigaevo/evolution/__init__.py gigaevo/evolution/storage/__init__.py 2>/dev/null`.

- [ ] **Step 2: Write the failing test**

```python
"""ArchiveStorageFactory construction and prefix scoping."""

from __future__ import annotations

import pytest

from gigaevo.evolution.storage.archive_storage import (
    RedisArchiveStorage,
    RedisArchiveStorageFactory,
)

from tests.database.storage_backends import _fakeredis_storage


@pytest.mark.asyncio
async def test_factory_builds_redis_archive_with_explicit_prefix():
    async with _fakeredis_storage() as storage:
        archive = RedisArchiveStorageFactory(storage)("island_0")
        assert isinstance(archive, RedisArchiveStorage)
        assert archive._hash_key == "island_0:archive"


@pytest.mark.asyncio
async def test_factory_falls_back_to_storage_prefix():
    async with _fakeredis_storage() as storage:
        archive = RedisArchiveStorageFactory(storage)()
        assert archive._hash_key == f"{storage.key_prefix}:archive"
```

(Verify `RedisArchiveStorage`'s actual key attribute name — if not `_hash_key`, read `archive_storage.py:60-100` and assert on the real one.)

- [ ] **Step 3: Run test, verify it fails** — Expected: `ImportError: RedisArchiveStorageFactory`.

- [ ] **Step 4: Implement factories** — append to `archive_storage.py` (add `Protocol` to typing imports); also replace its internal `program_storage.config.key_prefix` read with `program_storage.key_prefix` (Task 1 property):

```python
class ArchiveStorageFactory(Protocol):
    """Builds prefix-scoped ArchiveStorage instances (one per island)."""

    def __call__(self, key_prefix: str | None = None) -> ArchiveStorage: ...


class RedisArchiveStorageFactory:
    """Default factory: archives share the program storage's Redis connection."""

    def __init__(self, program_storage: RedisProgramStorage) -> None:
        self._program_storage = program_storage

    def __call__(self, key_prefix: str | None = None) -> RedisArchiveStorage:
        return RedisArchiveStorage(
            program_storage=self._program_storage, key_prefix=key_prefix
        )
```

Export from the package `__init__` if Step 1 found re-exports.

- [ ] **Step 5: Run test, verify pass.**

- [ ] **Step 6: Strategies go Redis-free** — `island.py`:
  - imports: `from gigaevo.database.program_storage import ProgramStorage`; `from gigaevo.evolution.storage.archive_storage import ArchiveStorageFactory` (NO Redis imports remain in this file).
  - `IslandConfig.redis_prefix` (line 55) → rename to `archive_prefix` via `gitnexus_rename` (dry-run first; known users: `island.py:73`; the computed value `island_{id}` is unchanged, so Redis key layout and resume compatibility are untouched).
  - constructor (factory is required — config wiring makes it always available):

```python
    def __init__(
        self,
        config: IslandConfig,
        program_storage: ProgramStorage,
        archive_storage_factory: ArchiveStorageFactory,
    ):
        self.config = config
        self.program_storage = program_storage
        self.archive_storage = archive_storage_factory(config.archive_prefix)
        self.state_manager = ProgramStateManager(program_storage)
        logger.info("Island {} init (max_size={})", config.island_id, config.max_size)
```

  `multi_island.py`: import ABC + `ArchiveStorageFactory`; `__init__` gains required `archive_storage_factory: ArchiveStorageFactory` parameter (place it directly after `program_storage`); island construction (line 42) → `MapElitesIsland(cfg, program_storage, archive_storage_factory)`; retype `program_storage: ProgramStorage`. Scan both files for any other `Redis*` annotation and retype to the ABC.

- [ ] **Step 7: Hydra wiring** — `config/redis/default.yaml`, after the `program_storage:` node:

```yaml
archive_storage_factory:
  _target_: gigaevo.evolution.storage.archive_storage.RedisArchiveStorageFactory
  program_storage: ${ref:program_storage}
```

In each of the 7 algorithm YAMLs (`multi_island.yaml:108`, `single_island.yaml:52`, `single_island_2d.yaml:56`, `tabular/2d_local_ood.yaml:55`, `single_island_no_distant_parents.yaml:53`, `topology_3d.yaml:61`, `topology_3d_ret.yaml:61`), next to the existing `program_storage: ${ref:program_storage}` line add:

```yaml
  archive_storage_factory: ${ref:archive_storage_factory}
```

(match each file's indentation/key position; `evolution/`, `pipeline/`, `runner/` refs point at storage for other components — only strategy constructors need the factory; verify by checking each ref's enclosing `_target_`.)

- [ ] **Step 8: Update test call sites** — add `archive_storage_factory=RedisArchiveStorageFactory(<storage var>)` (import from `gigaevo.evolution.storage.archive_storage`) at every direct construction: `tests/benchmarks/conftest.py:290`, `tests/benchmarks/test_collector_scaling.py:33`, `tests/benchmarks/test_strategy_ops.py:32`, `tests/benchmarks/test_generation_e2e.py:73`, `tests/concurrency/test_deadlock_prevention.py:96`, `tests/evolution/test_resume.py:204,219,235,251,268`, `tests/evolution/test_resume_e2e.py:218,301`, `tests/evolution/test_island_edge_cases.py:103,115` — then `grep -rn "MapElitesIsland(\|MapElitesMultiIsland(" tests/ gigaevo/ | grep -v __pycache__` to catch any site this list missed.

- [ ] **Step 9: Verify Redis-free strategies** — `grep -rn "Redis" gigaevo/evolution/strategies/*.py` → expected: zero hits.

- [ ] **Step 10: Run tests + smoke** — `/run-tests` targeting `tests/evolution/ tests/benchmarks/ tests/concurrency/`; `python run.py problem.name=tabular/california --cfg job > /dev/null`.

- [ ] **Step 11: Ruff + commit** — `refactor(strategies): Hydra-wired ArchiveStorageFactory; strategies depend only on ProgramStorage ABC`

---

### Task 7: Confine construction — `database/factory.py`, kill `utils/redis.py`

**Files:**
- Create: `gigaevo/database/factory.py`
- Test: `tests/database/test_factory.py` (create)
- Modify: `gigaevo/utils/dataframes.py` (absorb `fetch_evolution_dataframe`)
- Delete: `gigaevo/utils/redis.py`
- Modify: `gigaevo/cli/export.py:23-41`, `gigaevo/cli/plot_group.py:14-30,114-119`, `gigaevo/memory/ideas_tracker/redis_loader.py:32-39`, `tools/lineage.py:37`, `tools/profiler.py:136`, `gigaevo/experiment/lock.py:55` (docstring)

- [ ] **Step 1: Recon** — read `gigaevo/utils/redis.py` fully (the `RedisRunConfig` dataclass at lines 17-28 + `fetch_evolution_dataframe` at 31+); `grep -rn "from gigaevo.utils.redis import\|gigaevo\.utils\.redis" gigaevo/ tools/ tests/ docs/ --include='*.py' --include='*.md'` for the complete caller list (known: `cli/export.py`, `cli/plot_group.py`, `utils/dataframes.py:17` re-export, `experiment/lock.py:55` docstring).

- [ ] **Step 2: Write the failing test**

```python
"""build_readonly_redis_storage returns a correctly configured storage."""

from __future__ import annotations

from gigaevo.database.factory import RedisRunConfig, build_readonly_redis_storage
from gigaevo.database.redis_program_storage import RedisProgramStorage


def test_builds_readonly_storage_with_url_and_prefix():
    storage = build_readonly_redis_storage(
        host="localhost", port=6379, db=3, key_prefix="myprob"
    )
    assert isinstance(storage, RedisProgramStorage)
    assert storage.read_only is True
    assert storage.key_prefix == "myprob"
    assert "localhost:6379/3" in str(storage.config.redis_url)


def test_run_config_round_trips_through_factory():
    cfg = RedisRunConfig(redis_db=3, redis_prefix="myprob")
    storage = build_readonly_redis_storage(
        host=cfg.redis_host, port=cfg.redis_port, db=cfg.redis_db,
        key_prefix=cfg.redis_prefix,
    )
    assert storage.key_prefix == "myprob"
```

(Adjust `RedisRunConfig` field names to the dataclass moved in Step 3 — Step 1 establishes them; if it lacks host/port defaults, supply them in the test.)

- [ ] **Step 3: Implement `gigaevo/database/factory.py`** — move the `RedisRunConfig` dataclass verbatim from `utils/redis.py` (it keeps its Redis-honest name: it *locates a run inside a Redis DB*), plus:

```python
"""Single non-Hydra construction point for ProgramStorage backends.

Production engines get storage from Hydra (config/redis/default.yaml).
CLI tools and offline analytics that resolve runs dynamically
(prefix@db) construct read-only instances HERE — nowhere else.
"""

from __future__ import annotations

from gigaevo.database.program_storage import ProgramStorage
from gigaevo.database.redis_program_storage import (
    RedisProgramStorage,
    RedisProgramStorageConfig,
)

# (RedisRunConfig dataclass moved verbatim from gigaevo/utils/redis.py)


def build_readonly_redis_storage(
    *,
    host: str,
    port: int,
    db: int,
    key_prefix: str,
    max_connections: int = 50,
    connection_pool_timeout: float = 30.0,
    health_check_interval: int = 60,
) -> ProgramStorage:
    """Read-only storage for analytics/CLI paths. Never use for a live engine."""
    return RedisProgramStorage(
        RedisProgramStorageConfig(
            redis_url=f"redis://{host}:{port}/{db}",  # type: ignore[arg-type]
            key_prefix=key_prefix,
            max_connections=max_connections,
            connection_pool_timeout=connection_pool_timeout,
            health_check_interval=health_check_interval,
            read_only=True,
        )
    )
```

(If `RedisProgramStorageConfig`'s defaults differ from these, mirror the config's own defaults instead — read the Pydantic model first.)

- [ ] **Step 4: Run test, verify pass.**

- [ ] **Step 5: Move `fetch_evolution_dataframe`** into `gigaevo/utils/dataframes.py` with a storage-by-reference signature:

```python
async def fetch_evolution_dataframe(
    storage: ProgramStorage, *, add_stage_results: bool = False
) -> pd.DataFrame:
```

Body = existing body minus the inline `RedisProgramStorage(...)` construction and minus close/teardown (callers own lifecycle via `async with`). The "No programs found" error message uses `storage.key_prefix` instead of `config.redis_prefix`/`config.url()`. Delete `gigaevo/utils/redis.py` and the `utils/dataframes.py:17` re-export shim.

- [ ] **Step 6: Update the callers** — pattern for `cli/export.py:23-41` and `cli/plot_group.py` (preserve each file's local helper shape):

```python
from gigaevo.database.factory import RedisRunConfig, build_readonly_redis_storage
from gigaevo.utils.dataframes import fetch_evolution_dataframe

    storage = build_readonly_redis_storage(
        host=spec.host, port=spec.port, db=spec.db, key_prefix=spec.prefix,
    )

    async def _fetch():
        async with storage:
            return await fetch_evolution_dataframe(storage, add_stage_results=False)

    return asyncio.run(_fetch())
```

(exact `spec` field names come from each file's existing `RedisRunConfig(...)` construction — keep them). Then route the remaining inline constructions through `build_readonly_redis_storage(...)`, preserving every non-default kwarg each passes today: `gigaevo/memory/ideas_tracker/redis_loader.py:32` (keeps its `async with` usage — now an ABC feature), `tools/lineage.py:37`, `tools/profiler.py:136`. Fix the `experiment/lock.py:55` docstring reference. ⚠️ If any site passes a param the factory lacks, add the param to the factory — never special-case the site.

- [ ] **Step 7: Verify confinement** — `grep -rn "RedisProgramStorageConfig(" gigaevo/ tools/ run.py --include='*.py' | grep -v __pycache__ | grep -v "gigaevo/database/"` → expected: **zero hits** (Hydra instantiates via `_target_` strings, not Python call sites).

- [ ] **Step 8: Run tests + live-tool smoke** — `/run-tests` targeting `tests/database/ tests/utils/` (+ `tests/cli/` if it exists); real-infra check (per `feedback_thorough_testing`): `gigaevo top -n 1 -r <prefix>@<idle-db>` and `gigaevo export csv -r <prefix>@<idle-db>` against an archived DB (e.g. db0) — both must work.

- [ ] **Step 9: Docs** — `tools/README.md` documents CLI/tools; grep it for `utils/redis` / `RedisRunConfig` mentions and fix in this commit.

- [ ] **Step 10: Ruff + commit** — `refactor(database): single construction point in database/factory; storage passed by reference everywhere`

---

### Task 8: Final rename sweep, docs, verification

**Files:** discovered by audit (expected: `docs/ARCHITECTURE.md`, `tools/README.md`)

- [ ] **Step 1: Concrete-type audit** — `grep -rn "RedisProgramStorage" gigaevo/ tools/ run.py --include='*.py' | grep -v __pycache__ | grep -v "gigaevo/database/"`. Expected remaining hits, each justified: `evolution/storage/archive_storage.py` (`RedisArchiveStorageFactory.__init__` — the Redis impl pairing). Anything else = missed leak; fix.
- [ ] **Step 2: Name audit** — `grep -rin "redis" gigaevo/evolution/strategies/ gigaevo/problems/initial_loaders.py gigaevo/utils/experiment.py run.py | grep -v __pycache__`. Expected: only `run.py`'s `cfg.redis.*` connection-group reads and its frontier-compare URL helper (`run.py:184` — metrics tracker, out of scope). Then `grep -rn "flushdb\|redis_prefix\|redis_selection\|RedisTopProgramsLoader\|check_redis_resume\|utils\.redis" gigaevo/ tools/ tests/ config/ docs/ run.py | grep -v __pycache__` — every hit must be in the Redis-honest KEEP list (header) or fixed.
- [ ] **Step 3: Docs** — update `docs/ARCHITECTURE.md` storage section: ABC contract (incl. read-only + `key_prefix` + any Task-1 consolidation), `program_storage`/`archive_storage_factory` Hydra nodes, `database/factory.py` as the sole non-Hydra construction point, backend-parametrized contract tests. Sync `tools/README.md` for anything Tasks 4-7 touched that Step 1-2 greps surface.
- [ ] **Step 4: Full targeted suite** — `/run-tests` targeting `tests/database tests/evolution tests/utils tests/config tests/dag tests/benchmarks tests/concurrency`. Expected: Task-0 baseline + new tests, all green.
- [ ] **Step 5: GitNexus scope check** — `gitnexus_detect_changes({scope: "compare", base_ref: "main"})`; confirm only expected symbols/flows changed.
- [ ] **Step 6: Final smokes** — `--cfg job` for default, `algorithm=tabular/2d_local_ood`, and `loader=top_programs` variants; optionally a 2-minute live smoke run on a free DB if the user approves.
- [ ] **Step 7: Commit + PR** — branch `storage-purity`; PR links this plan; **do not merge while db11/db12 are live** (re-verify via `lsof`).

---

## Self-review

- **Spec coverage:** "all storage methods abstract on ABC" → Task 1 (inspect-diff gate: zero impl-only public methods; `with_redis` privatized to `_with_redis`); "ABC refactor/consolidation allowed" → Task 1 Step 2 (audit table, demote-to-default rule, zero call-site changes); "readonly on ABC" → Task 1 `read_only`/`require_writable` + contract test; "storage built only via Hydra, passed by reference" → Tasks 4 (loader source), 6 (factory node), 7 (confinement gate: zero `RedisProgramStorageConfig(` calls outside `database/`); "no redis name leaks" → Tasks 3/5/6/7 renames + Task 8 name audit with explicit KEEP list; "rename ugly redis_ names safely" → gitnexus_rename dry-runs for `flushdb`→`clear`, `redis_prefix`→`archive_prefix`, `RedisTopProgramsLoader`→`TopProgramsLoader`; "tests support all storage types" → Task 2 backend registry + contract suite (new backends = one registry entry).
- **Type consistency:** `check_storage_resume(storage, *, resume, location, flush_hint) -> bool` identical in Task 3 Steps 2/4/6; `ArchiveStorageFactory.__call__(key_prefix=None)` matches `factory(config.archive_prefix)`; `build_readonly_redis_storage` keyword-only signature matches all Task-7 routings; `_fakeredis_storage` context manager shared by Tasks 2 and 6 tests; `key_prefix` property defined Task 1, consumed Tasks 4/6/7.
- **Deliberate impurities (documented in header KEEP list):** `cfg.redis.*` group reads in `run.py`, `RedisArchiveStorageFactory`'s concrete pairing (incl. its private `_with_redis` calls), telemetry label, CLI Redis run locators.
- **User-visible behavior changes:** not-empty error suggests `gigaevo flush`; Hydra node renamed; `loader=redis_selection` → `loader=top_programs` with restructured source knobs; `flushdb()` → `clear()` (Python API); old configs are legacy per standing feedback — no migration shims.
- **Data compatibility:** `archive_prefix` rename changes no Redis key layout (`island_{id}:archive` unchanged); resume of existing DBs unaffected.
