# Pre-Registration: ColBERT + Rich Feedback (colbert_feedback)

**Date**: 2026-03-10
**Protocol version**: 1.0
**Pre-registration commit**: `20c8314`
**GitHub PR**: #76 (branch: `exp/hotpotqa-colbert-feedback`)
**Tracking issue**: N/A
**Design doc**: `experiments/hotpotqa/colbert_feedback/01_design.md`
**Review doc**: `experiments/hotpotqa/colbert_feedback/02_review.md` (verdict: APPROVED)
**Evaluation script**: `experiments/hotpotqa/colbert_feedback/run_test_eval.sh` (sha256: `075568b83c9b0a320ae41b5f2d6507bc89f81260ab0a2c15b874c0dbb97e56d3`)

---

## Hypothesis

**H0**: Mean test EM across n=4 ColBERT+rich-feedback cold-start runs does not exceed the
BM25 cold-start reference mean of 59.58% (PR #75, n=4, SD=1.00pp) by more than the 2.4pp
noise floor. I.e., the bundled ColBERT+richer-feedback intervention confers no net benefit
over BM25s+title-only feedback.

**H1**: Mean test EM >= 62.00% (+2.42pp above 59.58% reference), closing the gap with GEPA
(62.3%). The bundled intervention (ColBERT retrieval + full-passage failure feedback) exceeds
the cold-start BM25 ceiling by at least the pre-registered MDE of 1.666pp at SD=1pp.

**Primary metric**: Test EM at gen 25 (best-by-val program), 300-sample held-out test set,
thinking mode Qwen3-8B. Consistent with all prior experiments and GEPA benchmark (62.3%).

**Significance threshold**: alpha = 0.05 (one-sided one-sample t-test vs. reference mean 59.58%)

**Effect size thresholds**:

| Mean test EM | Verdict |
|:------------:|---------|
| >= 62.3% (GEPA) | **STRONG POSITIVE** |
| >= 62.00% | **POSITIVE** |
| [59.51%, 62.00%) | **SUGGESTIVE** |
| [57.18%, 59.51%) | **NULL** |
| < 57.18% | **NEGATIVE** |

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | `llm_base_url` (chain) | Seed | Val set |
|-----|-------|------------|-----------|-----------|----------------|------------------------|------|---------|
| U1 | colbert-1 | 0 | `hotpotqa_colbert` | `default` | `chains/hotpotqa/static_colbert_f1_600` | `http://10.226.17.25:8001/v1` | Cold | 600 train |
| U2 | colbert-2 | 1 | `hotpotqa_colbert` | `default` | `chains/hotpotqa/static_colbert_f1_600` | `http://10.226.17.25:8000/v1` | Cold | 600 train |
| U3 | colbert-3 | 2 | `hotpotqa_colbert` | `default` | `chains/hotpotqa/static_colbert_f1_600` | `http://10.225.185.235:8001/v1` | Cold | 600 train | (chain unchanged; mutation URL updated — see Amendment 2) |
| U4 | colbert-4 | 3 | `hotpotqa_colbert` | `default` | `chains/hotpotqa/static_colbert_f1_600` | `http://10.225.185.235:8000/v1` | Cold | 600 train |

**Mutation LLM assignment** (one per run):

| Run | Mutation LLM URL |
|-----|------------------|
| U1 | `http://10.226.72.211:8777/v1` |
| U2 | `http://10.226.15.38:8777/v1` |
| U3 | `http://10.226.185.47:8777/v1` |
| U4 | `http://10.225.51.251:8777/v1` |

---

## Controlled Variables

| Field | Value |
|-------|-------|
| `num_parents` | 1 (explicit override; default = 2) |
| `max_elites_per_generation` | 8 (explicit override; default = 5) |
| `max_mutations_per_generation` | 8 |
| `max_generations` | 25 |
| `stage_timeout` | 6000 |
| `dag_timeout` | 9000 |
| `step_max_tokens` | 8192 for all LLM steps |
| Chain LLM | Qwen3-8B, thinking mode ON (default chat template) |
| Mutation LLM | Qwen3-235B-A22B-Thinking |
| Fitness metric | F1 (token-level partial credit) |
| Validation sample size | 600 (first 600 train samples) |
| Seed initialization | Cold (no `program_loader.problem_dir`) |
| `prompts` | `default` |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism (document and accept):
- `random.sample` in `HotpotQAColBERTFormatter` (failure sampling per generation)
- LLM sampling temperature and nucleus sampling in chain and mutation LLMs
- Non-deterministic GPU floating point across hardware

**Global seed**: N/A (GigaEvo does not expose a global seed)

A fresh run with identical config will produce a different fitness trajectory but should land
in a statistically similar fitness range. Cross-experiment comparisons use effect-size
thresholds (from `01_design.md`) rather than exact trajectory matching.

---

## Dataset Checksums

```bash
sha256sum problems/chains/hotpotqa/dataset/HotpotQA_train.jsonl \
           problems/chains/hotpotqa/dataset/HotpotQA_test.jsonl
```

| File | sha256 |
|------|--------|
| `HotpotQA_train.jsonl` (train/val) | `9d8b0ba2a19d124fa243c88b650b2ecd42e5c771bc4e039553389c6b9566ef94` |
| `HotpotQA_test.jsonl` (test) | `c46bfb185e448bf1b92cb75bb5ab967f3211051793967f01500f453945046b0d` |

---

## Success Criteria

**POSITIVE** verdict: one-sample t-test p < 0.05 AND mean test EM >= 62.00% across U1-U4.

**STRONG POSITIVE** verdict: as above with mean >= 62.3% (GEPA).

**SUGGESTIVE** verdict: mean in [59.51%, 62.00%) — below MDE or t-test not significant at N=4.

**NULL** verdict: mean in [57.18%, 59.51%) — indistinguishable from BM25 cold-start reference.

---

## Monitoring Plan

`max_generations`: 25

- Gen 2 (~10%): smoke check — all 4 PIDs alive, Redis keys growing, no ColBERT index errors
- Gen 5 (~20%): first checkpoint — extract best-by-val, run test eval, record metrics
- Gen 12 (~50%): midpoint checkpoint — extract best-by-val, run test eval, record metrics
- Gen 25 (100%): final evaluation + analysis

**Critical monitoring checks at gen 0-1:**
- Gen-0 val EM for each run: expected 0.40-0.55. Halt if > 0.65 (warm-start detected) or 0.0 (retrieval failure).
- exec_runner logs: watch for `FileNotFoundError` or `RuntimeError` in `_ensure_colbert_initialized`.
- Invalidity rate: halt if > 50% at gen 5.

Early termination rule: if `valid_frontier_fitness` shows no improvement for >= 10 consecutive
generations AND current gen >= 15, run may be terminated early (consistent with cold_start).

---

## Launch Commands

All four runs use identical config except `redis.db` and LLM URLs.
Run `--cfg job` first for each and verify before launching.

```bash
export NO_PROXY="localhost,127.0.0.1,10.226.17.25,10.225.185.235,10.226.72.211,10.226.15.38,10.226.185.131,10.225.51.251"
export no_proxy="$NO_PROXY"
PYTHON=/home/jovyan/envs/evo_fast/bin/python
PROJ=/workspace-SR008.fs2/mathemage/gigaevo-core

# Config review (do this for each run before launching):
PYTHONPATH=$PROJ $PYTHON $PROJ/run.py \
    problem.name=chains/hotpotqa/static_colbert_f1_600 \
    pipeline=hotpotqa_colbert \
    prompts=default \
    redis.db=0 \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    max_generations=25 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    --cfg job

# U1 (after --cfg job passes):
PYTHONPATH=$PROJ $PYTHON $PROJ/run.py \
    problem.name=chains/hotpotqa/static_colbert_f1_600 \
    pipeline=hotpotqa_colbert \
    prompts=default \
    redis.db=0 \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    max_generations=25 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    2>&1 | tee run_U1.log &

# U2: redis.db=1, chain_url=10.226.17.25:8000, mutation_url=10.226.15.38:8777
# U3: redis.db=2, chain_url=10.225.185.235:8001, mutation_url=10.226.185.131:8777
# U4: redis.db=3, chain_url=10.225.185.235:8000, mutation_url=10.225.51.251:8777
```

**Mandatory `--cfg job` checks for each run**:
- `_target_: problems.chains.hotpotqa.static_colbert_f1_600.pipeline.ColBERTPipelineBuilder`
- `num_parents: 1`
- `max_elites_per_generation: 8`
- No `program_loader.problem_dir` present (cold start)
- `pipeline: hotpotqa_colbert` (never `hotpotqa_asi` or `standard`)
- `prompts_dir: ${prompts.dir}` in both `evolution_context` and `mutation_operator` blocks

---

## Index Build Record

ColBERT index rebuilt 2026-03-11 on H100 (GPU 0, CUDA_VISIBLE_DEVICES=0):
- Location: `experiments/hotpotqa/indexes/colbert_index/`
- Passages: 5,233,235 | Embeddings: 309,270,867 | Centroids: 262,144
- Build time: ~50 min (k-means: 7 min GPU, encoding: 44 min GPU)
- **kmeans_niters=20** (restored to ColBERTv2 original default; changed to 4 in Jun 2022)
- **doc_maxlen=220** (explicit override of parser.py default=180; avg_doclen=59 so no truncation)
- verify_kmeans.py: ALL PASS — PyTorch k-means bit-equivalent to faiss CPU (error ~1e-8)
- Technical note: faiss-gpu incompatible with NumPy 2.4.2; patched `compute_faiss_kmeans`
  in colbert source with PyTorch batched GPU k-means (see commit on branch)
- Technical note: global metadata.json `num_embeddings` bug in ColBERT (written before
  IVF build completes); fixed by re-reading actual codes.pt totals (309,270,867)

**Benchmark vs BM25 (n=1000, build_colbert_index.py, train split):**

| Metric | ColBERT | BM25 | Δ |
|--------|---------|------|---|
| Hop-1 recall@7 | 0.601 | 0.638 | -0.038 |
| Both-hops recall@7 | 0.274 | 0.359 | -0.085 |
| MRR | 0.835 | 0.822 | +0.013 |
| Oracle 2nd-hop recall@10 | 0.399 | 0.491 | -0.093 |
| Latency | 13.9ms/q | 5.5ms/q | 2.5× slower |

BM25 dominates on multi-hop recall (both-hops, oracle 2nd-hop). ColBERT has marginal MRR edge.
The experiment hypothesis requires richer feedback to compensate for ColBERT's retrieval deficit.

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| ColBERT server | 152204 | 2026-03-11 ~14:30 UTC | port 8889; running as independent nohup process |
| U1 | 600609 | 2026-03-11 16:08 UTC | DB=0, chain=10.226.17.25:8001, mut=10.226.72.211 |
| U2 | 600610 | 2026-03-11 16:08 UTC | DB=1, chain=10.226.17.25:8000, mut=10.226.15.38 |
| U3 | 600611 | 2026-03-11 16:08 UTC | DB=2, chain=10.225.185.235:8001, mut=10.226.185.47 |
| U4 | 600612 | 2026-03-11 16:08 UTC | DB=3, chain=10.225.185.235:8000, mut=10.225.51.251 |

Watchdog PID: 624688
Launch commit: `a8f4e9a` (HEAD at launch)

---

## Checkpoint Log

| Gen | Date (UTC) | Run | Val EM (best-by-val) | Test EM | Notes |
|-----|-----------|-----|:--------------------:|:-------:|-------|
| 5 | | U1 | | | |
| 5 | | U3 | | | |
| 5 | | U4 | | | |
| 12 | | U1 | | | |
| 12 | | U3 | | | |
| 12 | | U4 | | | |
| 25 (final) | | U1 | | | |
| 25 (final) | | U3 | | | |
| 25 (final) | | U4 | | | |

---

## Amendments

**Amendment 3 (2026-03-11): ColBERT CPU-mode fix for exec_runner workers**

- **No confound** — applied before any gen-0 validation completed; all 4 runs use identical code.
- ColBERT Searcher in exec_runner subprocesses required permanent module-level patches to run on CPU:
  1. `colbert.modeling.base_colbert.DEVICE = cpu` — prevents BERT checkpoint from being moved to
     GPU (would cause OOM; all H100 VRAM occupied by vLLM).  This local binding is separate from
     `colbert.parameters.DEVICE` (patching the latter is ineffective due to `from … import`).
  2. `ColBERTConfig.total_visible_gpus = 0` — disables GPU scoring at CALL TIME (class attribute
     is read at call time, not init time; restoring after Searcher init re-enables GPU scoring and
     causes `pids[scores_sorter.indices]` device mismatch).
- `MAX_MEMORY_MB` raised 32 GB → 64 GB to accommodate full 210-chunk index load (~15 GB RSS).
  System has 1.4 TB RAM; 16 workers × 15 GB = 240 GB total — well within capacity.
- exec_runners are isolated subprocesses; permanent patches do not affect the main process.
- Gen-0 val F1: U1=62.3%, U2=61.7%, U3=61.1%, U4=61.7% — expected cold-start range confirmed.

---

**Amendment 2 (2026-03-11): Mutation server IP corrected for U3**

- **No confound** — U3 mutation server `10.226.185.131` was offline at launch time; replaced
  with `10.226.185.47` (same role, same model: Qwen3-235B-A22B-Thinking-2507, same port 8777).
  All four runs use a distinct mutation server; no sharing. Quality unaffected.

---

**Amendment 3 (2026-03-11): ColBERT search server architecture**

- **No confound** — applies uniformly to all 4 runs before gen-0.
- **Root cause**: Loading the ColBERT index (309M embeddings, ~15–20 GB) in each exec_runner
  worker subprocess exceeded the 32 GB `MAX_MEMORY_MB` limit (`MemoryLimitExceeded`) and
  triggered CUDA OOM / mixed-device tensor errors when workers shared GPU with vLLM.
- **Change**: Introduced a dedicated `colbert_server.py` FastAPI process (PID 152204, port 8889)
  that loads the index once with GPU. exec_runner workers query it via HTTP using a new
  `ColBERTServerRetriever` class (`utils/retrieval.py`). `build_retriever()` in `shared_config.py`
  and `validate.py` both respect `HOTPOTQA_COLBERT_SERVER_URL` env var to select the server path.
- **Effect on experiment**: Retrieval quality is identical — same index, same search logic.
  Workers use no GPU (CPU-only subprocesses), GPU is owned by vLLM + colbert_server.
- **Gen-0 smoke check passed**: U1=0.623 F1, U2=0.617, U3=0.611 (✅ added to frontier);
  U4 baseline code rejected on gen-0 but advanced to gen=1 normally.

---

**Amendment 1 (2026-03-11): ColBERT index rebuilt with corrected parameters**

- **No confound** — applies uniformly before any run launched.
- `kmeans_niters` corrected from 4 (parser.py default) to 20 (ColBERTv2 original default,
  consistent with the Stanford-hosted server used in GEPA and all published ColBERTv2 results).
- `doc_maxlen` explicitly set to 220 (was implicitly 180 via parser.py override of settings.py).
  avg_doclen=59 tokens — no passage is truncated at either value; quality unchanged.
- PyTorch k-means verified bit-equivalent to faiss CPU k-means (verify_kmeans.py, ALL PASS).
- Retrieval benchmark (n=1000) shows **BM25 > ColBERT** on both-hops recall at all k values
  (e.g., k=7: BM25 0.359 vs ColBERT 0.274). ColBERT has marginal MRR edge (+0.013) but is
  2.5× slower. This makes H1 harder to achieve — richer feedback must compensate.
- ColBERT metadata.json bug: global `num_embeddings` written before IVF completes, resulting
  in wrong total; patched to match actual codes.pt sum (309,270,867).

---

**Amendment 4 (2026-03-12): U2 dropped; nbits=8 index; 8-GPU ColBERT server; DB reassignment**

- **Confound: n=4 → n=3** — Run U2 (chain URL 10.226.17.25:8000, mutation LLM 10.226.15.38)
  dropped. Node 10.226.15.38 is dedicated to GPU ColBERT serving via the 8-GPU colbert_server.py
  (see below); using it simultaneously as a mutation LLM would cause GPU OOM on that node.
  Revised success criterion: one-sample t-test (n=3, df=2) p < 0.05 AND mean test EM >= 62.00%
  vs reference 59.58% (PR #75). Lower n reduces power; MDE at n=3 = 2.19pp (80% power, SD=1pp).
  The first launch (PIDs 600609–600612) was aborted and Redis DBs 0–2 flushed before any
  gen-1 frontier was established — no evolution data was lost.

- **DB reassignment (no confound)**: U3 now uses DB=1 (was DB=2). U4 now uses DB=2 (was DB=3).
  U1 unchanged (DB=0). Required because DB=1 (U2's slot) is freed and DBs were flushed.

- **Index rebuild: nbits=8 (no confound)** — ColBERT index rebuilt with nbits=8 (256 levels per
  dimension) and kmeans_niters=20 on H100 GPU. Final index: 210 chunks, 310,680,776 embeddings,
  262,144 centroids. Build time: ~85 min on H100 (k-means: ~35 min GPU, encoding: ~47 min GPU).
  Rationale: test whether higher quantization fidelity closes gap to paper's ColBERTv2 (0.667 nDCG).

- **BEIR HotpotQA benchmarks** (MTEB test split, 7,405 queries, fuzzy title+80-char matching):

  | Metric | ColBERT nbits=8 | BM25s | Paper ColBERTv2 (nbits=2) |
  |--------|:---------------:|:-----:|:-------------------------:|
  | nDCG@10 | **0.6265** | **0.6290** | 0.667 |
  | Recall@10 | 0.6461 | 0.6530 | — |
  | MAP@10 | 0.5265 | 0.5356 | — |

  **Finding**: ColBERT nbits=8 ≈ BM25s (Δ nDCG = −0.0025). Both trail paper by ~4pp. The
  quantization gap over nbits=2 (≈0.625) is negligible (+0.001pp). The paper's 0.667 advantage
  is not explained by nbits alone — likely due to retrieval parameter or corpus differences.
  H1 remains plausible: richer full-passage failure feedback may compensate.

- **8-GPU ColBERT server (no confound)**: colbert_server.py updated to support `--num-gpus N`
  mode — a router process on port 8889 dispatches to N worker subprocesses on ports 8890+.
  Each worker holds one GPU via CUDA_VISIBLE_DEVICES. Router uses least-connections load
  balancing with a 30s background health monitor. Allows all 8 H100s on 10.226.15.38 to
  serve search concurrently; reduces latency under load from the 3 evolution runs.

---

## Amendment 4 Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| ColBERT server | 1673139 | 2026-03-12 00:30 UTC | port 8889, --num-gpus 8, 8-GPU router |
| U1 | 1676589 | 2026-03-12 00:30 UTC | DB=0, chain=10.226.17.25:8001, mut=10.226.72.211 |
| U3 | 1676590 | 2026-03-12 00:30 UTC | DB=1, chain=10.225.185.235:8001, mut=10.226.185.47 |
| U4 | 1676591 | 2026-03-12 00:30 UTC | DB=2, chain=10.225.185.235:8000, mut=10.225.51.251 |

Watchdog PID: 1679457
Launch commit: c89adf6

---

## Amendment 5: ColBERT Retrieval Gap Investigation (2026-03-12)

**No confound** — analysis only; no code or config changes.

Post-launch investigation into the 4pp gap: ColBERT nbits=8 = 0.6265 vs paper's 0.667.

### Exhaustive parameter sweep (full 7,405 BEIR queries each)

| Phase | Parameter | Values tested | nDCG@10 range |
|-------|-----------|--------------|---------------|
| 1 | `centroid_score_threshold` | 0.0, 0.1, 0.2, 0.3, 0.4, 0.45 | 0.6259–0.6262 |
| 2 | `ndocs` | 8192, 16384, 32768 | 0.6262 (flat) |
| 3 | `search_k` | 10, 100 | 0.6262 (flat) |
| 4 | `ncells` | 32, 64, 128 (with ndocs=32768) | 0.6261 (flat) |

All 14 configurations: **0.6259–0.6262**. Ceiling is absolute.

### Root cause investigation

| Hypothesis | Test | Result |
|------------|------|--------|
| IVF threshold filters good centroids | threshold=0.0 (probe all centroids) | 0.6259 — NOT the cause |
| Too few IVF cells probed | ncells=128 with ndocs=32768 | 0.6261 — NOT the cause |
| Too few document candidates | ndocs=32768 | 0.6262 — NOT the cause |
| PyTorch 2.9 produces wrong embeddings | New conda env: PyTorch 2.1.2+cu121 | cosine>0.9999999, MaxSim Δ<2e-6 — NOT the cause |
| Corpus coverage gaps | 13,783 relevant passages in qrels | 13,772/13,783 reachable (99.92%) — NOT the cause |
| Wrong checkpoint | Verified colbert-ir/colbertv2.0 snapshot | Correct checkpoint confirmed |
| Wrong doc_maxlen | Index metadata.json | doc_maxlen=300 (per paper Appendix F) |

### Confirmed reference number
ColBERTv2 paper Table 5 (NAACL 2022) reports HotpotQA nDCG@10 = **66.7** (confirmed from PDF).
Our result of 62.62 is a genuine 4pp gap with no identified technical cause.

### Conclusion
The 4pp gap is not explainable by search parameters, library version, corpus coverage, or
model config. Likely causes (not yet tested):
1. We indexed wiki17_abstracts; the paper likely indexed BeIR/hotpotqa corpus — ~218 relevant
   passages exist in our index with slightly different text, shifting embedding similarity marginally
2. HotpotQA multi-hop structure may inherently limit single-hop dense retrieval
3. Our BM25s = 62.9 already outperforms the paper's BM25 = 59.3 (+3.6pp), confirming our
   evaluation is not broken; ColBERT simply does not improve over BM25s here

**Implication for experiment**: H1 (richer feedback helps) is unaffected. ColBERT and BM25s
are at retrieval parity (~0.626–0.629 nDCG), so the experiment tests whether failure specificity
(full-passage context vs title-only) drives evolution improvement, independent of retrieval quality.
Results saved: `/tmp/threshold_sweep_results.json`.
