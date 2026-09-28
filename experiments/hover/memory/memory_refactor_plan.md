# Memory System Refactor Plan

## Problem Statement

The memory system (~6,000 LOC) is rigid, non-OOP, and hard to test. Core issues:

1. **Module-level global state** — `config.py` loads settings at import time into module constants (`OPENAI_API_KEY`, `LLM_BASE_URL`, etc.). Cannot be changed, mocked, or tested without module reloads.
2. **Config-by-YAML-path** — 50+ `deep_get(settings, "gam.top_k_by_tool")` calls scattered across codebase. No schema validation, no IDE autocomplete, typos cause silent failures.
3. **Environment variable spaghetti** — 15+ env vars (`MEMORY_API_URL`, `MEMORY_NAMESPACE`, `MEMORY_USE_API`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_BASE_URL`, `BASE_URL`, ...) with multi-level fallback chains: override > env > YAML > hardcoded default. Priority unclear.
4. **Duplicated config loading** — `config.py`, `memory_write_config.py`, and `MemorySelectorAgent._create_memory_backend()` all independently parse the same YAML + env vars with slightly different logic.
5. **Two parallel backends, no shared interface** — `gigaevo/memory/shared_memory/memory.py` (1,312 lines) and `gigaevo/memory_platform/shared_memory/memory.py` (1,100 lines) are ~90% duplicate code with no common base class.
6. **String-based dispatch** — `if config.get("type") == "default"` pattern in fabric modules. No type safety, no exhaustiveness checking.
7. **Lazy dynamic class loading with error suppression** — `AmemGamMemory._load_agentic_classes()` silently catches ImportErrors and sets `_agentic_import_error`. Object may be partially initialized with no signal to caller.
8. **Hardcoded paths and values** — `parents[3]`, `"memory_usage_store/api_exp4"`, `"https://openrouter.ai/api/v1"`, `"initial_programs"` scattered throughout.
9. **Constructor parameter bloat** — `AmemGamMemory.__init__` takes 16+ parameters. No config object.
10. **Factory pattern overuse** — `analyzer_fabric.py` (28 lines) and `postprocessing_fabric.py` (27 lines) are trivial dispatchers that add indirection without value.

## Current Architecture

```
                         Hydra config                    
                             │                           
     ┌───────────────────────┼───────────────────┐       
     ▼                       ▼                   ▼       
config/memory/         config/memory_backend.yaml    .env
  local.yaml           (161 lines, nested YAML)         
  none.yaml                  │                           
     │                       │   ┌──── os.getenv() ────┐ 
     ▼                       ▼   ▼                     │ 
SelectorMemoryProvider  MemorySelectorAgent             │
     │                  (438 lines)                     │
     │                       │                          │
     │              _create_memory_backend()            │
     │              re-parses YAML + env vars           │
     │                       │                          │
     │         ┌─────────────┴─────────────┐            │
     │         ▼                           ▼            │
     │   AmemGamMemory              memory_platform/    │
     │   (1,312 lines)              AmemGamMemory       │
     │   shared_memory/             (1,100 lines)       │
     │         │                    ~90% duplicate       │
     │         │                                        │
     │         ├── config.py ←──────────────────────────┘
     │         │   _SETTINGS (module global)              
     │         │   OPENAI_API_KEY (module global)         
     │         │   LLM_BASE_URL (module global)           
     │         │                                          
     │         ├── memory_write_config.py ←── also reads  
     │         │   SETTINGS (duplicate global)    same YAML
     │         │                                          
     │         └── card_conversion.py                     
     │             ALLOWED_GAM_TOOLS (module constants)    
     │                                                    
     ▼                                                    
IdeaTracker (PostRunHook)                                 
     │                                                    
     ├── fabrics/analyzer_fabric.py (string dispatch)     
     ├── fabrics/postprocessing_fabric.py (string dispatch)
     ├── fabrics/llm_clients_fabric.py (env var magic)    
     └── utils/task_description_loader.py (hardcoded paths)
```

**Problems highlighted:**
- Config parsed in 3+ places independently
- 2 backends, no common interface
- Module globals loaded at import time
- Factories are trivial dispatchers

## Proposed Architecture

```
                    Hydra config
                         │
                         ▼
              MemoryConfig (Pydantic)
              ┌─────────────────────┐
              │ checkpoint_dir: Path│
              │ namespace: str      │
              │ use_api: bool       │
              │ search_limit: int   │
              │ gam: GamConfig      │
              │ llm: LlmConfig      │
              │ dedup: DedupConfig  │
              └────────┬────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
  SelectorMemoryProvider     IdeaTracker
          │                  (PostRunHook)
          │                         │
          ▼                         ▼
  MemorySelectorAgent         MemoryWriter
  (receives config)           (receives config)
          │
          ▼
  MemoryBackend (ABC)
     ┌────┴────┐
     ▼         ▼
  LocalBackend  ApiBackend
  (merged)      (thin client)
```

**Key changes:**
- Single `MemoryConfig` dataclass flows everywhere (no YAML re-parsing)
- One `MemoryBackend` ABC — local and API are two implementations
- No module globals, no env var chains, no `deep_get()`
- Factories replaced by direct instantiation in Hydra config

## Implementation Steps

### Phase 1: MemoryConfig dataclass (eliminates global state + config duplication)

**New file**: `gigaevo/memory/memory_config.py`

```python
from pydantic import BaseModel, Field
from pathlib import Path

class GamConfig(BaseModel):
    enable_bm25: bool = False
    pipeline_mode: str = "default"
    allowed_tools: list[str] = Field(default_factory=lambda: ["page_index", "vector"])
    top_k_by_tool: dict[str, int] = Field(default_factory=dict)

class LlmConfig(BaseModel):
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    model_name: str = "google/gemini-3-flash-preview"
    embedding_model: str = "all-MiniLM-L6-v2"

class DedupConfig(BaseModel):
    enabled: bool = True
    top_k_per_query: int = 10
    final_top_n: int = 10
    min_final_score: float = 0.05

class MemoryConfig(BaseModel):
    checkpoint_dir: Path
    namespace: str = "default"
    use_api: bool = False
    channel: str = "latest"
    author: str | None = None
    search_limit: int = 5
    rebuild_interval: int = 10
    sync_batch_size: int = 100
    sync_on_init: bool = True
    enable_llm_synthesis: bool = False
    enable_memory_evolution: bool = False
    enable_llm_card_enrichment: bool = False
    gam: GamConfig = Field(default_factory=GamConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)
    dedup: DedupConfig = Field(default_factory=DedupConfig)
```

**Changes:**
- `AmemGamMemory.__init__` takes `config: MemoryConfig` instead of 16+ params
- `MemorySelectorAgent.__init__` takes `config: MemoryConfig` (no `_create_memory_backend()` re-parsing)
- Delete `config.py` (module globals), `memory_write_config.py` (duplicate globals)
- `SelectorMemoryProvider.__init__` takes `config: MemoryConfig`
- Hydra YAML instantiates `MemoryConfig` directly

**Files deleted:**
- `gigaevo/memory/config.py` (~95 lines)
- `gigaevo/memory/memory_write_config.py` (~170 lines)

**Files modified:**
- `gigaevo/memory/shared_memory/memory.py` — constructor change
- `gigaevo/llm/agents/memory_selector.py` — remove `_create_memory_backend()` logic
- `gigaevo/memory/provider.py` — pass config to selector
- `config/memory/local.yaml`, `config/memory/api.yaml` — instantiate MemoryConfig

### Phase 2: MemoryBackend ABC (eliminates code duplication)

**New file**: `gigaevo/memory/backend.py`

```python
from abc import ABC, abstractmethod

class MemoryBackend(ABC):
    @abstractmethod
    def search(self, query: str) -> str: ...

    @abstractmethod
    def save_card(self, card: dict) -> str: ...

    @abstractmethod
    def get_card(self, card_id: str) -> dict | None: ...

    @abstractmethod
    def list_cards(self) -> list[dict]: ...
```

- `AmemGamMemory` (local) extends `MemoryBackend`
- `memory_platform.AmemGamMemory` (API) extends `MemoryBackend`
- `MemorySelectorAgent._resolve_memory_backend_class()` deleted — backend injected via config

**Files modified:**
- `gigaevo/memory/shared_memory/memory.py` — add ABC inheritance
- `gigaevo/memory_platform/shared_memory/memory.py` — add ABC inheritance, extract shared logic to base
- `gigaevo/llm/agents/memory_selector.py` — receive backend, don't construct it

### Phase 3: Delete fabric modules (eliminate string-based dispatch)

Replace `create_analyzer({"type": "default", "model": "..."})` with direct Hydra instantiation:

```yaml
# config/ideas_tracker/default.yaml
ideas_tracker:
  _target_: gigaevo.memory.ideas_tracker.ideas_tracker.IdeaTracker
  analyzer:
    _target_: gigaevo.memory.ideas_tracker.components.analyzer.IdeaAnalyzer
    model: google/gemini-3-flash-preview
    base_url: "https://openrouter.ai/api/v1"
```

**Files deleted:**
- `gigaevo/memory/ideas_tracker/components/fabrics/analyzer_fabric.py`
- `gigaevo/memory/ideas_tracker/components/fabrics/postprocessing_fabric.py`
- `gigaevo/memory/ideas_tracker/components/fabrics/llm_clients_fabric.py`

**Files modified:**
- `gigaevo/memory/ideas_tracker/ideas_tracker.py` — receive analyzer/postprocessor as injected deps
- `config/ideas_tracker/default.yaml` — add nested `_target_` blocks

### Phase 4: Cleanup

- Remove `runtime_config.py` helper functions (`deep_get`, `to_bool`, `to_int`, etc.) — no longer needed with Pydantic
- Remove hardcoded env var fallback chains from `MemorySelectorAgent`
- Remove `task_description_loader.py` — IdeaTracker already receives `task_description` as param
- Remove module-level `ALLOWED_GAM_TOOLS` constants from `card_conversion.py` — move to `GamConfig`
- Remove `_load_agentic_classes()` lazy loading from `AmemGamMemory` — fail fast in constructor

## Estimated Impact

| Metric | Before | After |
|--------|--------|-------|
| Config loading locations | 3+ (independent) | 1 (MemoryConfig) |
| Module-level globals | 15+ | 0 |
| Environment variables | 15+ (fallback chains) | 2-3 (API key, base URL) |
| `deep_get()` calls | 50+ | 0 |
| LOC in config/factory modules | ~500 | ~80 (MemoryConfig) |
| Backend duplication | ~2,400 (90% dup) | ~1,800 (shared ABC base) |
| Testability | Requires module reloads | Standard dependency injection |

## Non-Goals

- Rewriting AmemGamMemory internals (search, save_card, GAM pipeline) — that's 1,300 lines of working ML logic
- Changing the memory card schema — works fine
- Changing the IdeaTracker analysis pipeline — recently refactored to PostRunHook
- Unifying local and API backends into one class — they have legitimately different implementations

## Dependencies

- Phase 1 is independent (can start now)
- Phase 2 depends on Phase 1 (needs MemoryConfig)
- Phase 3 depends on Phase 1 (needs Hydra instantiation of components)
- Phase 4 is cleanup after Phases 1-3
