# Memory System v2: Proposal

**Author**: Claude (commissioned by KhrulkovV)
**Date**: 2026-04-05
**Status**: Draft for review
**Scope**: Polish + finish memory system for extensibility and ease of use

---

## Executive Summary

The memory system works — hover/memory proves it. But 14,200 LOC across 50+ files for "select some cards during mutation, extract ideas after a run" is an order of magnitude too much. The existing `memory_refactor_plan.md` (MemoryConfig, MemoryBackend ABC) addresses config spaghetti but doesn't touch the deeper issue: **the architecture is inverted**. The system wraps two vendored ML libraries (A-MEM: 1,755 LOC, GAM: 2,568 LOC) and bends GigaEvo to serve them, when it should be the other way around.

This proposal goes further. It restructures memory into a **thin, composable layer** that GigaEvo owns entirely, with clear extension points.

---

## What's Wrong (Beyond Config)

### 1. Vendored libraries own the architecture

A-MEM (`A_mem/`) and GAM (`GAM_root/`) are vendored research codebases with their own agents, retrievers, prompts, and schemas. They account for 4,323 LOC (30% of the memory system) but are imported by exactly **2 files** (`a_mem_memory_creation.py` and `amem_gam_retriever.py`). The tail wags the dog.

**What A-MEM actually provides**: ChromaDB wrapper + LLM-based memory evolution (analyze content → store/update notes).
**What GAM actually provides**: Multi-retriever search with an "agentic" research loop.
**What GigaEvo actually uses**: Vector search over ~20-50 cards. That's it.

### 2. Dual backend with 90% duplication

`gigaevo/memory/shared_memory/memory.py` (1,312 LOC) and `gigaevo/memory_platform/shared_memory/memory.py` (1,472 LOC) are near-identical. The "platform" variant was forked for an API integration that may never ship.

### 3. Over-engineered card schema

`MemoryCard` has 15+ fields. In the actual mutation prompt, cards are formatted as a text blob. The mutation agent doesn't parse `works_with`, `links`, `usage`, `evolution_statistics`, `aliases`, or `connected_ideas`. It reads the description and maybe keywords. The schema serves the memory system's internal bookkeeping, not the downstream consumer.

### 4. LLM-in-the-loop for every operation

- **Card dedup**: LLM decides add/update/discard (579 LOC). Expensive, non-deterministic, hard to test.
- **Memory evolution**: LLM rewrites cards to incorporate new info. Cool but unnecessary at 20-50 cards.
- **Search synthesis**: LLM summarizes search results. Adds latency, no evidence it helps mutation quality.
- **Idea analysis**: LLM classifies ideas as new/known/updated. This one is valuable.

### 5. Subprocess call for memory writes

`IdeaTracker` shells out to `memory_write_example.py` as a subprocess with environment variable overrides. This was a quick hack to avoid import tangles. It makes testing, error handling, and config flow fragile.

---

## Proposed Architecture

```
gigaevo/memory/
├── __init__.py              # Public API: MemoryStore, MemoryCard, MemoryProvider
├── store.py                 # MemoryStore: save/search/list (replaces AmemGamMemory)
├── card.py                  # MemoryCard, ProgramCard (simplified Pydantic models)
├── provider.py              # MemoryProvider ABC (unchanged — good abstraction)
├── dedup.py                 # Embedding-based dedup (replaces LLM dedup)
├── retriever.py             # VectorRetriever (ChromaDB direct, replaces GAM stack)
├── config.py                # MemoryConfig (Pydantic, from refactor plan)
│
├── ideas_tracker/           # PostRunHook for idea extraction (keep, polish)
│   ├── ideas_tracker.py     # IdeaTracker (simplified)
│   ├── analyzer.py          # IdeaAnalyzer (merged from analyzer.py + analyzer_f.py)
│   ├── records.py           # ProgramRecord + conversion (merged utils)
│   └── enrichment.py        # Keyword extraction, summarization
│
└── cli.py                   # CLI for standalone idea extraction
```

**Total**: ~15 files, ~4,000 LOC (down from 50+ files, 14,200 LOC).

### What gets deleted

| Module | LOC | Why |
|--------|-----|-----|
| `A_mem/` (entire tree) | 1,755 | Replace with direct ChromaDB usage in `retriever.py` |
| `GAM_root/` (entire tree) | 2,568 | Replace with simple vector search in `retriever.py` |
| `memory_platform/` (entire tree) | 1,472 | Merge shared logic into `store.py`, delete duplicate |
| `shared_memory/memory.py` | 1,312 | Rewrite as `store.py` (~300 LOC) |
| `shared_memory/a_mem_memory_creation.py` | 301 | Inline into `retriever.py` (~40 LOC) |
| `shared_memory/amem_gam_retriever.py` | 269 | Inline into `retriever.py` (~60 LOC) |
| `shared_memory/concept_api.py` | ~200 | Keep as `api_client.py` if API needed, else delete |
| `ideas_tracker/components/fabrics/` | ~80 | Hydra instantiation replaces factories |
| `ideas_tracker/utils/cfg_loader.py` | ~160 | MemoryConfig replaces YAML parsing |
| `ideas_tracker/utils/dataframe_loader.py` | ~80 | Program-native (already done) |
| `config.py` (module globals) | ~95 | MemoryConfig replaces |
| `memory_write_config.py` | ~170 | MemoryConfig replaces |
| `runtime_config.py` | ~100 | MemoryConfig replaces |
| `memory_write_example.py` | 702 | Inline into IdeaTracker (no subprocess) |
| **Total deleted** | **~9,264** | **65% of current LOC** |

---

## The Five Changes

### 1. Replace A-MEM + GAM with direct ChromaDB (`retriever.py`)

**Bold claim**: The "agentic" search (ResearchAgent, 1,145 LOC) does multi-step retrieval with LLM routing over a collection of ~20-50 cards. This is a chainsaw for cutting butter. Direct vector similarity search with a threshold gives identical quality at 100x less complexity.

```python
# retriever.py (~100 LOC)
class VectorRetriever:
    """Direct ChromaDB wrapper. No agents, no routing, no LLM synthesis."""

    def __init__(self, persist_dir: Path, collection_name: str = "memory"):
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=SentenceTransformerEmbeddingFunction()
        )

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        results = self._collection.query(query_texts=[query], n_results=top_k)
        return [SearchResult(id=id, text=doc, distance=dist)
                for id, doc, dist in zip(results["ids"][0],
                                          results["documents"][0],
                                          results["distances"][0])]

    def add(self, card_id: str, text: str, metadata: dict | None = None):
        self._collection.upsert(ids=[card_id], documents=[text],
                                 metadatas=[metadata or {}])

    def delete(self, card_id: str):
        self._collection.delete(ids=[card_id])

    def count(self) -> int:
        return self._collection.count()
```

**Migration path**: A-MEM and GAM stay in the repo as `gigaevo/memory/_legacy/` for one release cycle, then get removed. Tests verify `VectorRetriever` returns equivalent results on the existing card corpus.

### 2. Replace LLM-based dedup with embedding similarity (`dedup.py`)

The current 579-LOC dedup module builds multi-field queries, retrieves candidates, scores them with weights, then asks an LLM "should I add, update, or discard this card?" This is slow (~2-5s per card), non-deterministic, and hard to test.

Replace with:

```python
# dedup.py (~80 LOC)
class EmbeddingDedup:
    """Dedup via cosine similarity. Deterministic, fast, testable."""

    def __init__(self, threshold: float = 0.85, merge_threshold: float = 0.92):
        self.threshold = threshold        # below = new card
        self.merge_threshold = merge_threshold  # above = update existing

    def classify(self, new_card: MemoryCard,
                 existing: list[tuple[MemoryCard, float]]) -> DedupDecision:
        if not existing:
            return DedupDecision.ADD

        best_match, best_score = existing[0]
        if best_score >= self.merge_threshold:
            return DedupDecision.UPDATE(target=best_match.id)
        elif best_score >= self.threshold:
            return DedupDecision.DISCARD  # too similar but not worth merging
        else:
            return DedupDecision.ADD
```

**Key insight**: At 20-50 cards, false positives from embedding similarity are rare. The LLM dedup was designed for a future with thousands of cards. We're not there. And if we get there, we can add LLM dedup back as a `DedupStrategy` behind an interface.

### 3. Simplify card schema (`card.py`)

Current `MemoryCard` has 15+ fields. Downstream consumers (mutation prompt) use ~3.

**New schema** — two tiers:

```python
# card.py
class MemoryCard(BaseModel):
    """Core card — what the mutation agent sees."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    card_type: Literal["idea", "program"] = "idea"
    description: str                    # The actual content
    keywords: list[str] = []            # For search boost
    fitness_context: float | None = None  # Best fitness when card was created
    generation: int | None = None       # When it was created
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Extension point — arbitrary metadata without schema bloat
    metadata: dict[str, Any] = {}

class ProgramCard(MemoryCard):
    """Card backed by an actual evolved program."""
    card_type: Literal["program"] = "program"
    program_id: str = ""
    code: str = ""
    fitness: float = 0.0
```

**What moves to `metadata`**: `works_with`, `links`, `usage`, `evolution_statistics`, `aliases`, `connected_ideas`, `strategy`, `task_description_summary`. These are bookkeeping fields that the mutation agent never reads. They stay accessible but don't pollute the core schema.

**Backward compatibility**: A `from_legacy(old_card: dict) -> MemoryCard` function handles migration from the old 15-field schema. Existing card banks (api_index.json) can be loaded without data loss.

### 4. Inline memory writes into IdeaTracker (kill subprocess)

Currently `IdeaTracker.on_run_complete()` → `memory_pipeline.py` → `subprocess.run("python memory_write_example.py")`. This 702-LOC script should be ~50 lines of in-process calls.

```python
# In ideas_tracker.py
async def _write_to_memory(self, ideas: list[MemoryCard],
                            programs: list[ProgramCard]) -> WriteStats:
    store = self._memory_store  # injected via constructor
    stats = WriteStats()
    for card in ideas:
        decision = self._dedup.classify(card, store.find_similar(card, top_k=5))
        if decision == DedupDecision.ADD:
            store.save(card)
            stats.added += 1
        elif isinstance(decision, DedupDecision.UPDATE):
            store.update(decision.target, card)
            stats.updated += 1
        else:
            stats.rejected += 1
    for prog in programs:
        store.save(prog)  # program cards skip dedup
        stats.programs_added += 1
    return stats
```

### 5. Strategy pattern for memory selection (`provider.py`)

The current provider has one strategy: "ask an LLM agent to pick cards." This is the right default but shouldn't be the only option. Add a strategy interface:

```python
# provider.py
class SelectionStrategy(ABC):
    @abstractmethod
    async def select(self, query: str, store: MemoryStore,
                     max_cards: int) -> list[MemoryCard]: ...

class VectorSimilarityStrategy(SelectionStrategy):
    """Fastest: pure embedding similarity. No LLM call."""
    async def select(self, query, store, max_cards):
        return [r.card for r in store.search(query, top_k=max_cards)]

class LLMRankedStrategy(SelectionStrategy):
    """Current default: LLM picks most relevant cards from candidates."""
    async def select(self, query, store, max_cards):
        candidates = store.search(query, top_k=max_cards * 3)
        return await self._llm_rank(query, candidates, max_cards)

class RecencyWeightedStrategy(SelectionStrategy):
    """Prefer recent cards (last N generations) with similarity tiebreaker."""
    async def select(self, query, store, max_cards):
        results = store.search(query, top_k=max_cards * 2)
        return sorted(results, key=lambda r: r.card.generation or 0,
                       reverse=True)[:max_cards]
```

**Hydra config**:
```yaml
# config/memory/local.yaml
memory_provider:
  _target_: gigaevo.memory.provider.SelectorMemoryProvider
  strategy:
    _target_: gigaevo.memory.provider.VectorSimilarityStrategy
  max_cards: 3
  checkpoint_dir: ${checkpoint_dir}
```

This makes it trivial to experiment with different selection approaches without touching engine code.

---

## Implementation Roadmap

### Phase 0: Merge existing refactor plan (MemoryConfig + kill fabrics)
**Effort**: 2-3 sessions
**Prereq**: None
**Deliverable**: Single `MemoryConfig` Pydantic model, config parsed once, fabrics deleted

This is the `memory_refactor_plan.md` already written. Do it first — it unblocks everything else.

### Phase 1: VectorRetriever + simplified store
**Effort**: 3-4 sessions
**Prereq**: Phase 0
**Deliverable**: `store.py` + `retriever.py` replace AmemGamMemory + A-MEM + GAM

Steps:
1. Write `VectorRetriever` with ChromaDB (TDD, ~100 LOC)
2. Write `MemoryStore` wrapping VectorRetriever + JSON index (TDD, ~300 LOC)
3. Verify search quality: load existing card bank, compare search results against current AmemGamMemory
4. Swap `MemorySelectorAgent` to use new `MemoryStore`
5. Move A-MEM + GAM to `_legacy/`, update imports
6. Run full test suite + manual smoke test

### Phase 2: Simplified cards + embedding dedup
**Effort**: 2 sessions
**Prereq**: Phase 1
**Deliverable**: New card schema + `dedup.py`

Steps:
1. Write `card.py` with `from_legacy()` migration (TDD)
2. Write `EmbeddingDedup` (TDD, ~80 LOC)
3. Migrate existing card banks (one-time script)
4. Swap IdeaTracker to use new card schema + dedup
5. Delete old `card_update_dedup.py`, `data_components.py` bloat

### Phase 3: Inline writes + strategy pattern
**Effort**: 2 sessions
**Prereq**: Phase 2
**Deliverable**: No subprocess writes, pluggable selection strategies

Steps:
1. Inline `memory_write_example.py` logic into `IdeaTracker._write_to_memory()`
2. Add `SelectionStrategy` ABC + 2-3 implementations
3. Wire strategies into Hydra config
4. Delete `memory_write_example.py`, `memory_write_config.py`, `memory_pipeline.py`

### Phase 4: Delete legacy + cleanup
**Effort**: 1 session
**Prereq**: Phase 3
**Deliverable**: `_legacy/` removed, dead code purged, docs updated

Steps:
1. Remove `A_mem/`, `GAM_root/`, `memory_platform/`
2. Remove dead helpers, unused test fixtures
3. Update CLAUDE.md memory section
4. Final LOC count verification

---

## Extension Points (Future Use Cases)

The new architecture makes these easy without touching core code:

| Extension | How |
|-----------|-----|
| **New retrieval method** (BM25, hybrid, reranking) | Implement `VectorRetriever` subclass or compose retrievers |
| **Cross-experiment memory** | Share `checkpoint_dir` across experiments, cards accumulate |
| **Memory decay** | Add `expires_at` to `MemoryCard.metadata`, filter in `search()` |
| **Memory quality scoring** | Track `usage_count` + fitness delta in `metadata`, rank by impact |
| **API-backed storage** | Implement `RemoteMemoryStore(MemoryStore)` backed by REST API |
| **Custom card types** | Subclass `MemoryCard`, add to Hydra config |
| **Selective forgetting** | `store.forget(strategy=LowImpactStrategy())` — remove low-usage cards |
| **Memory visualization** | `store.export_graph()` → card similarity network for analysis |

---

## Metrics: Before vs. After

| Metric | Current | Proposed |
|--------|---------|----------|
| Total files | 50+ | ~15 |
| Total LOC | 14,200 | ~4,000 |
| Config entry points | 3+ (independent) | 1 (MemoryConfig) |
| Module globals | 15+ | 0 |
| Vendored libraries | 2 (A-MEM, GAM) | 0 |
| Backend duplicates | 2 (90% overlap) | 1 |
| LLM calls per card write | 1-2 (dedup + evolution) | 0 (embedding only) |
| LLM calls per card read | 1-3 (agent search + synthesis) | 0-1 (optional ranking) |
| Time to add new retrieval strategy | Modify GAM internals | Implement 1 class |
| Time to understand the system | Hours (50+ files, vendored code) | 30 min (15 files, clear flow) |

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Search quality degrades without GAM | A/B test on existing card bank before cutting over. Vector similarity at k=5 is likely equivalent for <100 cards. |
| Embedding dedup misclassifies cards | Tune thresholds on existing dedup decisions (ground truth from LLM dedup logs). Add LLM dedup as fallback strategy if needed. |
| Card migration loses data | `from_legacy()` preserves all fields in `metadata` dict. Round-trip test ensures no data loss. |
| Too aggressive — breaks running experiments | Phase per phase, each independently deployable. Don't start until hover/memory is closed. |

---

## Non-Goals

- **Rewriting IdeaAnalyzer internals** — the LLM-based idea classification is the actual IP. Keep it.
- **Changing the mutation prompt format** — downstream consumers shouldn't notice the refactor.
- **Building a distributed memory service** — if needed later, `RemoteMemoryStore` behind the same interface.
- **Changing how memory is wired into the DAG** — `MemoryContextStage` + `MemoryProvider` are clean.

---

## Decision Required

1. **Kill A-MEM + GAM?** They're 30% of the LOC but provide "agentic" search that may add value at scale. Proposal: kill them now, the interface allows re-adding agentic search later if scale demands it.

2. **Kill `memory_platform/`?** It's 1,472 LOC of duplication with no current users beyond one import in `memory_selector.py`. Proposal: kill it.

3. **Kill LLM dedup?** It's 579 LOC and adds 2-5s per card. Embedding dedup is sufficient at current scale. Proposal: kill it, keep as optional `DedupStrategy` if someone wants it back.

4. **Phase 0 first or skip to Phase 1?** The MemoryConfig refactor (Phase 0) is a clean first step but adds a session of work before the big wins. Could skip to Phase 1 if you want faster results.
