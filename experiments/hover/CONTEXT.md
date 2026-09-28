# HoVer — Task Context

This directory is the parent context for the entire HoVer research line.
Individual experiments live in subdirectories: `experiments/hover/<name>/`.

---

## Part 1 — Stable Task Knowledge

### Benchmarks (Qwen3-8B, thinking mode)

| Method | Test Retrieval Coverage |
|--------|------------------------|
| GEPA | 52.33% |
| GigaEvo baseline (zero-shot) | 51.65% (SD 0.63pp, n=4, PR #90) |

**ALL results must use thinking Qwen3-8B.** GEPA benchmark uses the default chat template
(thinking ON). Non-thinking runs are INVALID for GEPA comparison.

---

### Task Description

HoVer (Hover Over Wikipedia) — multi-hop fact verification. Given a claim, retrieve
supporting documents from Wikipedia to verify or refute it. The task uses 3-hop claims
that require evidence from exactly 3 Wikipedia articles.

**Fitness metric**: Retrieval coverage — discrete score (1 if ALL gold supporting documents
are found across all retrieval hops, 0 otherwise). This is NOT classification accuracy;
it measures whether the chain retrieves the right evidence documents.

---

### Dataset

| Split | File | Rows | Labels | sha256 |
|-------|------|------|--------|--------|
| Train (val draws from here) | `problems/chains/hover/dataset/HoVer_train.jsonl` | 1000 | SUPPORTED=548, NOT_SUPPORTED=452 | `1bfc935d667e405a51cfb0361d1ee672fa3475d82714bcf027fc2d1a2c5cdcfa` |
| Test (held out) | `problems/chains/hover/dataset/HoVer_test.jsonl` | 300 | SUPPORTED=158, NOT_SUPPORTED=142 | `1319ef6d1c16c879f4e8d3675df8ebf93be1387da6ee874d9fcdeaa0d56280a2` |
| BM25 corpus | `problems/chains/hover/dataset/wiki17_abstracts.jsonl.passages.pkl` (symlink to hotpotqa) | ~5.2M passages | — | (same as hotpotqa) |

All samples are 3-hop (exactly 3 gold supporting facts / Wikipedia articles per claim).
Validation set = first N samples of train split (default N=300).
Test set is never seen during evolution.

Source: https://github.com/hover-nlp/hover — train_release_v1.1 + dev_release_v1.1, filtered to num_hops=3.

---

### Chain Structure (fixed 7-step topology)

```
Step 1 (TOOL, frozen)  — BM25 retrieve k=7: query = claim
Step 2 (LLM)           — Summarize first-hop evidence
Step 3 (LLM)           — Generate second-hop search query
Step 4 (TOOL, frozen)  — BM25 retrieve k=7: query = Step 3 output
Step 5 (LLM)           — Combine first-hop + second-hop evidence
Step 6 (LLM)           — Generate third-hop search query
Step 7 (TOOL, frozen)  — BM25 retrieve_deep k=10: query = Step 6 output
```

Static mode = evolve LLM step structured fields (aim, stage_action, reasoning_questions,
example_reasoning) + chain-level system_prompt. Topology is fixed.
Fitness = retrieval coverage (discrete: all gold docs found = 1, else 0).

Key difference from HotpotQA: 3 retrieval hops (not 2), 7 steps (not 6), and
fitness is retrieval coverage (not EM/F1 on answer text).

---

### Problem Variants

| `problem.name` | Val N | Fitness | Pipeline | Notes |
|----------------|-------|---------|----------|-------|
| `chains/hover/static` | 300 | Retrieval coverage | `hover_feedback` | Canonical — with failure feedback (tuple return) |
| `chains/hover/static_soft` | 300 | Retrieval coverage | `standard` | Plain dict return, no feedback |

**Pipeline rules**:
- `chains/hover/static` with feedback: `pipeline=hover_feedback` (validate.py returns tuple)
- `chains/hover/static_soft`: `pipeline=standard` (validate.py returns plain dict)

---

### Key Hydra Overrides

```bash
problem.name=chains/hover/static      # with feedback (tuple return)
pipeline=hover_feedback               # REQUIRED for chains/hover/static
prompts=default                       # generic GigaEvo mutation prompts
redis.db=N                            # unoccupied DB number

# OR for static_soft (no feedback, plain dict):
problem.name=chains/hover/static_soft
pipeline=standard
```

Config review (no execution): `python run.py problem.name=chains/hover/static --cfg job`

---

### Known Bugs and Patterns

#### Squid proxy (shared with HotpotQA)
`shared_config.py` includes the NO_PROXY fix at module top. Any standalone script
that imports from `problems.chains.hover.shared_config` inherits the fix automatically.
If writing a new script, import `shared_config` before any HTTP calls.

---

### Environment Variable

Chain LLM URL is passed via env var. All experiments now use the LiteLLM proxy:
```bash
export HOVER_CHAIN_URL="http://10.232.30.185:4000/v1"
```
Must be set before launching `run.py`. The LiteLLM proxy load-balances across all chain servers (see `infrastructure.yaml`).

---

## Part 2 — Infrastructure (current state — update before each launch)

_Last updated: 2026-04-07_

**Canonical server inventory**: `experiments/infrastructure.yaml`
All server IPs, ports, models, and status are maintained there. Verify before each launch:

```bash
# Quick liveness check — LiteLLM proxy (primary)
curl -s http://10.232.30.185:4000/v1/models -H "Authorization: Bearer sk-gigaevo" | python3 -c "import sys,json; d=json.load(sys.stdin); print([m['id'] for m in d['data']])" 2>/dev/null || echo "PROXY UNREACHABLE"

# Direct chain server check (see infrastructure.yaml for full list)
for port in 8000 8001 8002 8003 8004 8005 8006 8007; do
  curl -s http://10.232.45.196:$port/v1/models | python3 -c "import sys,json; print(f'10.232.45.196:$port', json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || echo "10.232.45.196:$port UNREACHABLE"
done
```

### Chain Execution LLMs (Qwen3-8B, thinking mode ON)

See `experiments/infrastructure.yaml` → `chain_servers` for current endpoints.
8 slots: chain-0 through chain-7 (10.232.45.196:8000-8007). Context window: 32768.

### Mutation / Insights LLMs (Qwen3-235B-A22B-Thinking)

See `experiments/infrastructure.yaml` → `mutation_servers` for current endpoints.
6 active endpoints. Port 8777.

### BM25 Corpus

Symlinked from HotpotQA: `wiki17_abstracts.jsonl.passages.pkl` (~1.5GB pickle).
BM25s index also symlinked: `bm25s_index/` (same params: k1=0.9, b=0.4).
Both problems use the same Wikipedia 2017 abstracts dump.
