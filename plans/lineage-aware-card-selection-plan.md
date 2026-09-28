# Lineage-Aware Card Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the shared-bank read path from re-serving cards already applied up a program's lineage by pruning them from GAM's candidate pool *before* GAM ranks, so its single relevance pick is automatically lineage-fresh.

**Architecture:** Filter-first → retrieve. (A) A new birth-time metadata key freezes each program's lineage-applied card closure. (B) A `CardExcluder` strategy on the provider reads that closure and threads an `exclude_ids` set down the existing read chain to one hard guard inside the vendored GAM agent (`_build_retrieved_ideas`), strictly before the selector-LLM. Control (`excluder=null`) is byte-identical to today.

**Tech Stack:** Python 3.12, Hydra configs, Pydantic, pytest, loguru. Spec: `plans/lineage-efficacy-selector.md`.

**Gating (operational, not part of the code plan):** Implementation edits to `gigaevo/` happen only after the live db7 run is stopped (`feedback_no_import_changes_mid_run` — eval workers re-import). The new run (`excluder=lineage`) launches only after E1's `rank−prod` clears and tests are green.

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `gigaevo/evolution/mutation/constants.py` | modify | add `MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY` |
| `gigaevo/evolution/engine/mutation.py` | modify | `lineage_applied_closure()` helper + stamp it at child birth |
| `gigaevo/memory/core/protocols.py` | modify | add `CardExcluder` Protocol |
| `gigaevo/memory/core/excluder.py` | create | `NullExcluder`, `LineageExcluder` |
| `gigaevo/memory/core/__init__.py` | modify | export the new symbols |
| `gigaevo/memory/core/read_pipeline.py` | modify | thread `exclude_ids` through `select`/`_select` → `research` |
| `gigaevo/memory/core/retriever.py` | modify | `GamRetriever.research(..., exclude_ids=...)` |
| `gigaevo/memory/shared_memory/memory.py` | modify | store `research(..., exclude_ids=...)` |
| `gigaevo/memory/_vendor/GAM_root/gam/agents/research_agent.py` | modify | thread `exclude_ids` → guard in `_build_retrieved_ideas` |
| `gigaevo/memory/provider.py` | modify | `SelectorMemoryProvider` holds `excluder`, computes `exclude_ids` in `select_cards` |
| `gigaevo/memory/system.py` | modify | `excluder` kwarg, pass into provider partial |
| `config/memory/excluder/null.yaml` | create | `NullExcluder` leaf (default) |
| `config/memory/excluder/lineage.yaml` | create | `LineageExcluder` leaf (treatment) |
| `config/memory/full.yaml` | modify | add `- excluder: null` to defaults |
| `tests/evolution/test_lineage_applied_metadata.py` | create | Task 1 |
| `tests/memory/test_card_excluder.py` | create | Task 2 |
| `tests/memory/test_read_pipeline_exclude_ids.py` | create | Task 3 |
| `tests/memory/test_gam_exclude_ids.py` | create | Task 4 |
| `tests/memory/test_provider_excluder.py` | create | Task 5 |

---

## Task 1: Component A — birth-time lineage-applied closure

The exclude set must be sourced from **frozen** metadata only. `memory_injected_idea_ids` is frozen at birth (`constants.py:12-16`); a program's own `memory_selected_idea_ids` is overwritten on NO_CACHE requeue, so it is NOT used. We add one new frozen key holding the transitive closure: `lineage_applied(C) = injected_ids(C) ∪ ⋃ parents' lineage_applied`.

**Files:**
- Modify: `gigaevo/evolution/mutation/constants.py`
- Modify: `gigaevo/evolution/engine/mutation.py:65-76`
- Test: `tests/evolution/test_lineage_applied_metadata.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/evolution/test_lineage_applied_metadata.py
from __future__ import annotations

from gigaevo.evolution.engine.mutation import lineage_applied_closure
from gigaevo.evolution.mutation.constants import (
    MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY,
)


class _FakeParent:
    def __init__(self, lineage_applied: list[str]) -> None:
        self._m = {MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY: lineage_applied}

    def get_metadata(self, key: str):
        return self._m.get(key)


def test_closure_unions_parent_lineage_with_child_injection():
    parents = [_FakeParent(["a", "b"]), _FakeParent(["b", "c"])]
    assert lineage_applied_closure(injected_ids=["d"], parents=parents) == [
        "a",
        "b",
        "c",
        "d",
    ]


def test_root_no_parents_no_injection_is_empty():
    assert lineage_applied_closure(injected_ids=[], parents=[]) == []


def test_grandparent_card_survives_two_hops():
    # a parent whose own closure already carries a grandparent card
    parent = _FakeParent(["gp_card"])
    assert lineage_applied_closure(injected_ids=[], parents=[parent]) == ["gp_card"]


def test_missing_parent_metadata_is_treated_as_empty():
    class _Legacy:
        def get_metadata(self, key):
            return None

    assert lineage_applied_closure(injected_ids=["x"], parents=[_Legacy()]) == ["x"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$GIGAEVO_PYTHON -m pytest tests/evolution/test_lineage_applied_metadata.py -q`
Expected: FAIL — `ImportError: cannot import name 'lineage_applied_closure'`.

- [ ] **Step 3: Add the constant**

In `gigaevo/evolution/mutation/constants.py`, after the `MUTATION_MEMORY_USED_METADATA_KEY` block (line 20):

```python
#: Frozen onto a child at birth: sorted transitive closure of every card id
#: applied to this program or any ancestor — ``injected_ids(child)`` unioned with
#: each parent's own lineage-applied closure. Read by the lineage card-excluder so
#: a mutation never re-serves a card already used up the ancestry. Sourced only
#: from frozen keys (a program's own selected-ids are overwritten on requeue).
MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY = "memory_lineage_applied_ids"
```

- [ ] **Step 4: Add the pure helper + stamp it at birth**

In `gigaevo/evolution/engine/mutation.py`, add the import to the existing `constants` import block (lines 8-13):

```python
from gigaevo.evolution.mutation.constants import (
    MUTATION_MEMORY_INJECTED_IDS_METADATA_KEY,
    MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY,
    MUTATION_MEMORY_SELECTED_IDS_METADATA_KEY,
    MUTATION_MEMORY_USED_METADATA_KEY,
    MUTATION_PARENT_STAGE_OUTPUTS_METADATA_KEY,
)
```

Add the module-level helper (above `generate_one_mutation`):

```python
def lineage_applied_closure(
    *, injected_ids: list[str], parents: list[Program]
) -> list[str]:
    """Transitive closure of every card applied to this child or any ancestor.

    Built from frozen inputs only: the child's just-computed ``injected_ids``
    unioned with each parent's own (birth-frozen) lineage-applied closure.
    """
    closure: set[str] = {cid for cid in injected_ids if cid}
    for parent in parents:
        for cid in parent.get_metadata(MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY) or []:
            if cid:
                closure.add(cid)
    return sorted(closure)
```

Then stamp it right after the existing `injected_ids` stamp (`mutation.py:75-76`):

```python
        program.set_metadata(MUTATION_MEMORY_INJECTED_IDS_METADATA_KEY, injected_ids)
        program.set_metadata(MUTATION_MEMORY_USED_METADATA_KEY, bool(injected_ids))
        program.set_metadata(
            MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY,
            lineage_applied_closure(injected_ids=injected_ids, parents=parents),
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `$GIGAEVO_PYTHON -m pytest tests/evolution/test_lineage_applied_metadata.py -q`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
rtk git add gigaevo/evolution/mutation/constants.py gigaevo/evolution/engine/mutation.py tests/evolution/test_lineage_applied_metadata.py
rtk git commit -m "feat(memory): freeze birth-time lineage-applied card closure"
```

---

## Task 2: CardExcluder protocol + Null/Lineage implementations

**Files:**
- Modify: `gigaevo/memory/core/protocols.py`
- Create: `gigaevo/memory/core/excluder.py`
- Modify: `gigaevo/memory/core/__init__.py`
- Test: `tests/memory/test_card_excluder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/memory/test_card_excluder.py
from __future__ import annotations

from gigaevo.evolution.mutation.constants import (
    MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY,
)
from gigaevo.memory.core import LineageExcluder, NullExcluder


class _Prog:
    def __init__(self, lineage_applied):
        self._m = {MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY: lineage_applied}

    def get_metadata(self, key):
        return self._m.get(key)


def test_null_excluder_excludes_nothing():
    assert NullExcluder().exclude_for(_Prog(["a", "b"])) == frozenset()


def test_lineage_excluder_returns_the_closure():
    assert LineageExcluder().exclude_for(_Prog(["a", "b"])) == frozenset({"a", "b"})


def test_lineage_excluder_legacy_program_without_key_is_empty():
    class _Legacy:
        def get_metadata(self, key):
            return None

    assert LineageExcluder().exclude_for(_Legacy()) == frozenset()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$GIGAEVO_PYTHON -m pytest tests/memory/test_card_excluder.py -q`
Expected: FAIL — `ImportError: cannot import name 'LineageExcluder'`.

- [ ] **Step 3: Add the protocol**

In `gigaevo/memory/core/protocols.py`, after the `CardRetriever` Protocol (line 65), add:

```python
@runtime_checkable
class CardExcluder(Protocol):
    """Decides which card ids must be pruned from the candidate pool BEFORE
    retrieval ranks them (filter-first lineage gate)."""

    def exclude_for(self, program: Any) -> frozenset[str]: ...
```

- [ ] **Step 4: Implement the excluders**

```python
# gigaevo/memory/core/excluder.py
"""Pre-retrieval card excluders (filter-first lineage gate).

The provider asks an excluder "which ids must not be retrieved for this program?"
and threads the answer into the GAM research pass, so the selector-LLM ranks only
over lineage-fresh candidates. ``NullExcluder`` is the default (byte-identical to
the un-gated read path); ``LineageExcluder`` reads the birth-frozen closure.
"""

from __future__ import annotations

from typing import Any

from gigaevo.evolution.mutation.constants import (
    MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY,
)


class NullExcluder:
    """Excludes nothing — the control arm."""

    def exclude_for(self, program: Any) -> frozenset[str]:
        return frozenset()


class LineageExcluder:
    """Excludes every card applied to this program or any ancestor."""

    def exclude_for(self, program: Any) -> frozenset[str]:
        applied = program.get_metadata(
            MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY
        )
        return frozenset(applied or ())
```

- [ ] **Step 5: Export the symbols**

In `gigaevo/memory/core/__init__.py`: add the import (after the `deduplicator` import, line 18):

```python
from gigaevo.memory.core.excluder import LineageExcluder, NullExcluder
```

Add `"CardExcluder"`, `"LineageExcluder"`, `"NullExcluder"` to `__all__`, and add `CardExcluder` to the `from gigaevo.memory.core.protocols import (...)` block (line 20-30).

- [ ] **Step 6: Run test to verify it passes**

Run: `$GIGAEVO_PYTHON -m pytest tests/memory/test_card_excluder.py -q`
Expected: PASS (3 passed). (A circular import would surface here — `evolution.mutation.constants` imports only `typing`, so none exists.)

- [ ] **Step 7: Commit**

```bash
rtk git add gigaevo/memory/core/protocols.py gigaevo/memory/core/excluder.py gigaevo/memory/core/__init__.py tests/memory/test_card_excluder.py
rtk git commit -m "feat(memory): CardExcluder strategy (null + lineage)"
```

---

## Task 3: Thread `exclude_ids` through the read pipeline (gigaevo side)

Default `frozenset()` at every hop keeps all existing callers and goldens unchanged.

**Files:**
- Modify: `gigaevo/memory/core/read_pipeline.py:55-114`
- Modify: `gigaevo/memory/core/retriever.py:49-54`
- Modify: `gigaevo/memory/shared_memory/memory.py:443-462`
- Test: `tests/memory/test_read_pipeline_exclude_ids.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/memory/test_read_pipeline_exclude_ids.py
from __future__ import annotations

import pytest

from gigaevo.memory._vendor.GAM_root.gam.schemas import ResearchOutput
from gigaevo.memory.core import (
    BetaBinomialReputation,
    EfficacyCardRenderer,
    MemoryReadPipeline,
    ThompsonAuctioneer,
    TopThetaBudgeter,
)


class _RecordingRetriever:
    def __init__(self):
        self.seen_exclude = "UNSET"

    def research(self, query, *, planning_request=None, exclude_ids=frozenset()):
        self.seen_exclude = exclude_ids
        return ResearchOutput(integrated_memory="", raw_memory={"final_decision": {"top_ideas": []}})

    def get_card(self, card_id):
        return None


class _Selector:
    def build_core_request(self, **k):
        return "req"

    def build_query(self, **k):
        return "q"

    def shortlist(self, raw_memory):
        return []


def _pipeline(retriever):
    return MemoryReadPipeline(
        retriever=retriever,
        selector=_Selector(),
        auctioneer=ThompsonAuctioneer(),
        budgeter=TopThetaBudgeter(),
        renderer=EfficacyCardRenderer(),
        reputation=BetaBinomialReputation(),
    )


@pytest.mark.asyncio
async def test_exclude_ids_reach_the_retriever():
    retr = _RecordingRetriever()
    await _pipeline(retr).select(
        parents=[object()],
        mutation_mode="rewrite",
        task_description="",
        metrics_description="",
        max_cards=1,
        exclude_ids=frozenset({"stale"}),
    )
    assert retr.seen_exclude == frozenset({"stale"})


@pytest.mark.asyncio
async def test_default_select_passes_empty_exclude():
    retr = _RecordingRetriever()
    await _pipeline(retr).select(
        parents=[object()],
        mutation_mode="rewrite",
        task_description="",
        metrics_description="",
        max_cards=1,
    )
    assert retr.seen_exclude == frozenset()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$GIGAEVO_PYTHON -m pytest tests/memory/test_read_pipeline_exclude_ids.py -q`
Expected: FAIL — `select()` rejects unexpected `exclude_ids` kwarg / retriever never receives it.

- [ ] **Step 3: Thread through `MemoryReadPipeline`**

In `read_pipeline.py`, add `exclude_ids: frozenset[str] = frozenset()` to `select` (after `max_cards`, line 62) and to `_select` (line 91). Forward it in the `select`→`_select` call (line 71-77). In `_select`, pass it to the retriever call (line 112-114):

```python
        async with self._lock:
            result = await asyncio.to_thread(
                retriever.research,
                query,
                planning_request=core_request,
                exclude_ids=exclude_ids,
            )
```

- [ ] **Step 4: Thread through `GamRetriever` and the store**

`retriever.py:49-54`:

```python
    def research(
        self,
        query: str,
        *,
        planning_request: str | None = None,
        exclude_ids: frozenset[str] = frozenset(),
    ) -> Any:
        if self.backend is None:
            raise RuntimeError(
                "GamRetriever.research called before bind(); no backend attached"
            )
        return self.backend.research(
            query, planning_request=planning_request, exclude_ids=exclude_ids
        )
```

`memory.py:443-462` (the store's `research`): add `exclude_ids: frozenset[str] = frozenset()` to the signature and forward it to `self.research_agent.research(query, memory_state=..., planning_request=..., exclude_ids=exclude_ids)`. The local-cards fallback (line 468) needs no change — it returns `raw_memory=None`, so `shortlist` yields no ids and nothing can leak.

- [ ] **Step 5: Update the `CardRetriever` protocol signature**

In `protocols.py`, update `CardRetriever.research` (line 63) to:

```python
    def research(
        self,
        query: str,
        *,
        planning_request: str | None = None,
        exclude_ids: frozenset[str] = frozenset(),
    ) -> Any: ...
```

- [ ] **Step 6: Run test to verify it passes**

Run: `$GIGAEVO_PYTHON -m pytest tests/memory/test_read_pipeline_exclude_ids.py -q`
Expected: PASS (2 passed).

- [ ] **Step 7: Run the frozen control goldens (no regression)**

Run: `$GIGAEVO_PYTHON -m pytest tests/memory/test_core_read_pipeline.py -q`
Expected: PASS (unchanged — default empty exclude is a no-op).

- [ ] **Step 8: Commit**

```bash
rtk git add gigaevo/memory/core/read_pipeline.py gigaevo/memory/core/retriever.py gigaevo/memory/shared_memory/memory.py gigaevo/memory/core/protocols.py tests/memory/test_read_pipeline_exclude_ids.py
rtk git commit -m "feat(memory): thread exclude_ids through read pipeline to GAM research"
```

---

## Task 4: GAM guard — prune excluded ids before the selector-LLM

Thread `exclude_ids` through the experimental path and drop excluded hits in `_build_retrieved_ideas` — one guard covering both vector and page_index tools (all hits flow through `sorted_hits`), per-iteration (excluded ids never enter the accumulator), strictly before `_reflection_experimental` ranks.

**Files:**
- Modify: `gigaevo/memory/_vendor/GAM_root/gam/agents/research_agent.py` (lines 218-237, 294-317, 360, 831-833, 928, 421-454)
- Test: `tests/memory/test_gam_exclude_ids.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/memory/test_gam_exclude_ids.py
from __future__ import annotations

from gigaevo.memory._vendor.GAM_root.gam.agents.research_agent import ResearchAgent
from gigaevo.memory._vendor.GAM_root.gam.schemas.search import Hit


def _bare_agent(card_map):
    agent = object.__new__(ResearchAgent)
    agent._card_map_by_id = lambda: card_map  # type: ignore[method-assign]
    return agent


def _ideas(agent, hits, **kw):
    return [i["card_id"] for i in agent._build_retrieved_ideas(hits, **kw)]


CARD_MAP = {
    "card_a": {"id": "card_a", "description": "alpha"},
    "card_b": {"id": "card_b", "description": "beta"},
}
HITS = [
    Hit(page_id="card_a", snippet="a", source="vector"),
    Hit(page_id="card_b", snippet="b", source="page_index"),
]


def test_excluded_card_id_is_dropped_from_both_tools():
    agent = _bare_agent(CARD_MAP)
    assert _ideas(agent, HITS, exclude_ids=frozenset({"card_a"})) == ["card_b"]


def test_empty_exclude_keeps_all():
    agent = _bare_agent(CARD_MAP)
    assert _ideas(agent, HITS) == ["card_a", "card_b"]


def test_all_excluded_yields_empty_pool():
    agent = _bare_agent(CARD_MAP)
    assert _ideas(agent, HITS, exclude_ids=frozenset({"card_a", "card_b"})) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$GIGAEVO_PYTHON -m pytest tests/memory/test_gam_exclude_ids.py -q`
Expected: FAIL — `_build_retrieved_ideas()` got an unexpected keyword argument `exclude_ids`.

- [ ] **Step 3: Add the guard in `_build_retrieved_ideas`**

`research_agent.py:421` signature and the loop body (after the `seen_ids` check, line 428-430):

```python
    def _build_retrieved_ideas(
        self, hits: list[Hit], *, exclude_ids: frozenset[str] = frozenset()
    ) -> list[dict[str, Any]]:
        card_map = self._card_map_by_id()
        ideas: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for hit in hits:
            card_id = str(hit.page_id or "").strip()
            if not card_id or card_id in seen_ids:
                continue
            if card_id in exclude_ids:
                continue
            seen_ids.add(card_id)
```

- [ ] **Step 4: Thread `exclude_ids` to the guard**

`_search_no_integrate` (line 831-833) — add the param and pass it at the `_build_retrieved_ideas` call (line 928):

```python
    def _search_no_integrate(
        self,
        plan: SearchPlan,
        result: Result,
        question: str,
        *,
        exclude_ids: frozenset[str] = frozenset(),
    ) -> Result:
        ...
        ideas = self._build_retrieved_ideas(sorted_hits, exclude_ids=exclude_ids)
```

`_research_experimental` (line 294-299) — add the param and pass it at the `_search_no_integrate` call (line 317):

```python
    def _research_experimental(
        self,
        request: str,
        memory_state: str | None = None,
        planning_request: str | None = None,
        *,
        exclude_ids: frozenset[str] = frozenset(),
    ) -> ResearchOutput:
        ...
            retrieved = self._search_no_integrate(
                plan, Result(), request, exclude_ids=exclude_ids
            )
```

Public `research` (line 218-237) — add the param and forward to the experimental branch (line 227-232):

```python
    def research(
        self,
        request: str,
        memory_state: str | None = None,
        planning_request: str | None = None,
        *,
        exclude_ids: frozenset[str] = frozenset(),
    ) -> ResearchOutput:
        self._update_retrievers()

        if self.pipeline_mode == "experimental":
            return self._research_experimental(
                request,
                memory_state=memory_state,
                planning_request=planning_request,
                exclude_ids=exclude_ids,
            )
        return self._research_default(
            request,
            memory_state=memory_state,
            planning_request=planning_request,
        )
```

(`_research_default` is the dead non-experimental path — the provider forces `experimental` — and does not use `_build_retrieved_ideas`; it needs no change.)

- [ ] **Step 5: Run test to verify it passes**

Run: `$GIGAEVO_PYTHON -m pytest tests/memory/test_gam_exclude_ids.py -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Run existing GAM tests (no regression)**

Run: `$GIGAEVO_PYTHON -m pytest tests/memory/test_gam_research_agent.py tests/memory/test_gam_search_plumbing.py tests/memory/test_gam_reflection_error_logging.py -q`
Expected: PASS (default empty exclude is a no-op).

- [ ] **Step 7: Commit**

```bash
rtk git add gigaevo/memory/_vendor/GAM_root/gam/agents/research_agent.py tests/memory/test_gam_exclude_ids.py
rtk git commit -m "feat(memory): GAM filter-first lineage prune before selector-LLM"
```

---

## Task 5: Wire the excluder into provider + MemorySystem + Hydra

**Files:**
- Modify: `gigaevo/memory/provider.py:79-107,167-181`
- Modify: `gigaevo/memory/system.py:24-62`
- Create: `config/memory/excluder/null.yaml`, `config/memory/excluder/lineage.yaml`
- Modify: `config/memory/full.yaml`
- Test: `tests/memory/test_provider_excluder.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/memory/test_provider_excluder.py
from __future__ import annotations

import pytest

from gigaevo.evolution.mutation.constants import (
    MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY,
)
from gigaevo.memory.core import LineageExcluder, NullExcluder
from gigaevo.memory.core.selection import MemorySelection
from gigaevo.memory.provider import SelectorMemoryProvider


class _Prog:
    def __init__(self, applied):
        self._m = {MUTATION_MEMORY_LINEAGE_APPLIED_IDS_METADATA_KEY: applied}

    def get_metadata(self, key):
        return self._m.get(key)


class _RecordingPipeline:
    def __init__(self):
        self.seen_exclude = "UNSET"

    async def select(self, *, exclude_ids=frozenset(), **kw):
        self.seen_exclude = exclude_ids
        return MemorySelection(cards=[], card_ids=[])


def _provider(excluder):
    p = SelectorMemoryProvider(backend=object(), excluder=excluder)
    p._pipeline = _RecordingPipeline()  # skip the heavy lazy build
    return p


@pytest.mark.asyncio
async def test_lineage_excluder_feeds_closure_to_pipeline():
    p = _provider(LineageExcluder())
    await p.select_cards(_Prog(["c1", "c2"]), task_description="", metrics_description="")
    assert p._pipeline.seen_exclude == frozenset({"c1", "c2"})


@pytest.mark.asyncio
async def test_default_provider_excludes_nothing():
    p = _provider(None)  # None -> NullExcluder
    await p.select_cards(_Prog(["c1"]), task_description="", metrics_description="")
    assert p._pipeline.seen_exclude == frozenset()


def test_provider_defaults_to_null_excluder():
    assert isinstance(SelectorMemoryProvider(backend=object())._excluder, NullExcluder)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `$GIGAEVO_PYTHON -m pytest tests/memory/test_provider_excluder.py -q`
Expected: FAIL — `SelectorMemoryProvider.__init__` got an unexpected keyword argument `excluder`.

- [ ] **Step 3: Add `excluder` to the provider**

`provider.py` — import `CardExcluder`, `NullExcluder` from `gigaevo.memory.core` (extend the existing import block, lines 17-31). Add the constructor param (after `reputation`, line 92) and store it:

```python
        reputation: ReputationModel | None = None,
        excluder: CardExcluder | None = None,
    ) -> None:
        ...
        self._reputation = (
            reputation if reputation is not None else BetaBinomialReputation()
        )
        self._excluder = excluder if excluder is not None else NullExcluder()
```

Compute and pass `exclude_ids` in `select_cards` (lines 174-181):

```python
        pipeline = await self._ensure_pipeline()
        return await pipeline.select(
            parents=[program],
            mutation_mode="rewrite",
            task_description=task_description,
            metrics_description=metrics_description,
            max_cards=self._max_cards,
            exclude_ids=self._excluder.exclude_for(program),
        )
```

- [ ] **Step 4: Pass the excluder through MemorySystem**

`system.py` — add `excluder: Any = None` to `__init__` (after `provider`, line 39) and forward it into the reader-side provider partial (lines 55-62):

```python
        if reader_enabled:
            self.provider = provider(
                backend=backend,
                retriever=retriever,
                selector=selector,
                auctioneer=auction,
                budgeter=budget,
                reputation=reputation,
                excluder=excluder,
            )
```

- [ ] **Step 5: Add the Hydra leaves + default**

`config/memory/excluder/null.yaml`:

```yaml
# Default read-side excluder: prune nothing (byte-identical to the un-gated path).
_target_: gigaevo.memory.core.excluder.NullExcluder
```

`config/memory/excluder/lineage.yaml`:

```yaml
# Treatment: prune every card already applied up the parent's lineage so GAM's
# single relevance pick is lineage-fresh. Reads the birth-frozen closure metadata.
_target_: gigaevo.memory.core.excluder.LineageExcluder
```

`config/memory/full.yaml` — add to the `defaults:` list (after `- provider: selector`):

```yaml
  - excluder: null
```

- [ ] **Step 6: Run test to verify it passes**

Run: `$GIGAEVO_PYTHON -m pytest tests/memory/test_provider_excluder.py -q`
Expected: PASS (3 passed).

- [ ] **Step 7: Hydra smoke-build both arms**

Run:
```bash
$GIGAEVO_PYTHON -c "import hydra; from hydra import compose, initialize_config_dir; \
initialize_config_dir(config_dir='$(pwd)/config', version_base=None); \
from hydra.utils import instantiate; \
import omegaconf; \
[print(k, type(instantiate(compose(config_name='config', overrides=[f'memory={p[0]}','problem=tabular/california',f'memory/excluder={p[1]}']).memory).provider._excluder).__name__) for p in (('full','null'),('full','lineage'))]"
```
Expected: prints `NullExcluder` then `LineageExcluder` (confirms the leaf wires into the live provider). If the compose entrypoint differs, fall back to the project's standard Hydra smoke (`tools/`/`bin/` launch with `--cfg job --resolve` and grep `excluder`).

- [ ] **Step 8: Commit**

```bash
rtk git add gigaevo/memory/provider.py gigaevo/memory/system.py config/memory/excluder/ config/memory/full.yaml tests/memory/test_provider_excluder.py
rtk git commit -m "feat(memory): wire CardExcluder into provider + MemorySystem (excluder=null|lineage)"
```

---

## Task 6: Green gate

**Files:** none (verification only)

- [ ] **Step 1: Lint**

Run: `ruff check . && ruff format --check .`
Expected: clean.

- [ ] **Step 2: Targeted test suites**

Run: `$GIGAEVO_PYTHON -m pytest tests/memory/ tests/evolution/ -q -p no:warnings`
Expected: all pass.

- [ ] **Step 3: Grep guard — exactly one prune point**

Run: `grep -rn "exclude_ids" gigaevo/memory/_vendor/GAM_root/gam/agents/research_agent.py`
Expected: appears in `research`, `_research_experimental`, `_search_no_integrate`, `_build_retrieved_ideas` — and the only `in exclude_ids` membership test is inside `_build_retrieved_ideas`.

- [ ] **Step 4: Confirm control is inert**

Run: `$GIGAEVO_PYTHON -m pytest tests/memory/test_core_read_pipeline.py tests/memory/test_provider.py -q`
Expected: pass unchanged (the default `excluder=null` path is byte-identical to pre-change behaviour).

---

## Post-merge operational step (NOT part of this plan, gated on E1)

Once E1's `rank−prod` clears and this branch is green + merged:
1. Stop the live memory run (find PID via `lsof` on its logfile — `rtk_ps_truncation_trap`; never corrupt the bank).
2. Launch the treatment run mirroring the live launch verbatim (`feedback_mirror_baseline_exactly`), swapping only `problem.name` + `redis.db` + output dir, and adding `memory/excluder=lineage`.
3. Optionally launch a matched `memory/excluder=null` control on a second db for the whole-run A/B.
4. Instrument empty-injection rate per arm (the riskiest-link guardrail). Auto-send the PDF checkpoint to Telegram on completion.

---

## Self-Review

- **Spec coverage:** Component A (Task 1), `CardExcluder` abstraction (Task 2), `exclude_ids` plumbing + GAM guard (Tasks 3-4), provider/MemorySystem/Hydra wiring + `null`/`lineage` arms (Task 5), green gate (Task 6). All spec sections mapped.
- **Type consistency:** `exclude_ids: frozenset[str] = frozenset()` is the single type at every hop; `exclude_for(program) -> frozenset[str]` matches what `select_cards` forwards; `lineage_applied_closure(*, injected_ids, parents) -> list[str]` matches the stamp call and the `LineageExcluder` read of the same key.
- **No placeholders:** every code step shows real code; every run step shows the command and expected result.
- **Control safety:** default-empty exclude at every hop + `excluder: null` default ⇒ the un-gated path is unchanged, verified in Tasks 3/4/6.
