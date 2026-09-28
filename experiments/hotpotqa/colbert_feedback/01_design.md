# Experimental Design: ColBERT + Rich Feedback — Closing the GEPA Gap

**Date**: 2026-03-10
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Revised — addressing Phase 2 review (Prof. Andrei Volkov, 2026-03-10)

---

## 1. Research Question

Does replacing BM25s retrieval with ColBERTv2 AND providing richer failure feedback (full
"Title | passage text" for missing gold documents instead of titles only) increase test EM
above the established cold-start ceiling (mean 59.58%, CI [58.00%, 61.17%]) and, if so, does
the combined intervention reach or exceed GEPA (62.3% test EM) — when run under the same
Qwen3-8B chain + Qwen3-235B mutation setup with n=4 independent cold-start replications?

---

## 2. Hypotheses

### Primary hypothesis: combined intervention breaks the 59.58% cold-start ceiling

**H0(combined)**: The mean test EM across n=4 ColBERT+rich-feedback cold-start runs does not
exceed the established cold-start reference mean of 59.58% (PR #75, T1–T4, n=4, SD=1.00pp)
by more than the noise floor (2.4pp). That is, the ColBERT retriever and richer failure
feedback confer no net benefit over BM25s+title-only feedback at this sample size and
evaluation setup.

**H1(combined)**: The combined intervention mean test EM exceeds the cold-start BM25 reference
mean of 59.58% by at least +2.42pp (i.e., mean >= 62.00%), closing the gap with GEPA (62.3%).
The mechanistic rationale is additive: (a) ColBERT improves first- and second-hop retrieval
recall relative to BM25s on multi-hop questions, giving the chain better raw passages to
reason over; (b) richer failure feedback (full passage text for missing gold documents)
gives the mutation LLM more actionable signal per generation, enabling it to diagnose
retrieval failures and design prompts that better bridge the gap between retrieved and gold
passages. Together these changes address two independent failure modes that BM25s+title-only
feedback cannot fix through prompt evolution alone.

**Effect size threshold**:

| Mean test EM | Verdict |
|:------------:|---------|
| >= 62.3% (GEPA) | **STRONG POSITIVE** — ColBERT+feedback reliably matches or beats GEPA; BM25 gap is the binding constraint |
| >= 62.00% | **POSITIVE** — Combined intervention exceeds cold-start BM25 reference and approaches GEPA; MDE reached, H0 rejected |
| [59.51%, 62.00%) | **SUGGESTIVE** — Mean exceeds BM25 cold-start reference noise floor but below MDE; t-test may or may not be significant |
| [57.18%, 59.51%) | **NULL** — Mean indistinguishable from cold-start BM25 reference; ColBERT+feedback confers no advantage |
| < 57.18% | **NEGATIVE** — Combined intervention underperforms cold-start BM25 reference |

The MDE lower bound of 62.00% is set to approximately +2.42pp above the 59.58% reference
(just above the 2.4pp noise floor), ensuring that any POSITIVE verdict clears the noise floor
with margin. The SUGGESTIVE lower bound of 59.51% = 59.58% − 0.07pp is effectively the
reference mean (within floating-point); any mean above this but below the MDE is SUGGESTIVE
pending replication.

*Note on collapsed BORDERLINE row*: The previous draft included a BORDERLINE row spanning
[61.98%, 62.00%), a 0.02pp interval that is entirely within binomial measurement noise on 300
samples (SE ~2.8pp). This row has been collapsed into POSITIVE, per reviewer concern m1.

### Design choice: bundled intervention

This experiment tests ColBERT retrieval and richer failure feedback **bundled together** in a
single new problem variant (`static_colbert_f1_600`), rather than separating the two
interventions into distinct experiment arms.

**Justification for bundling**:

The two interventions are strongly complementary and co-motivated. ColBERT improves retrieval
quality, which changes which documents are missing (and thus changes the failure cases the
mutation LLM sees). Richer feedback makes those failure cases more actionable. Separating them
would require 8+ runs total (n=4 per arm), consuming the entire remaining GPU budget on a
2-arm design where the feedback-only arm (BM25+rich feedback) has unclear scientific value on
its own: if we know BM25 retrieves different documents than the gold, richer titles for
documents that are never retrieved anyway is of limited use.

Critically, the null of interest for this project is whether GigaEvo can close the GEPA gap
under a fixed static topology — and GEPA uses ColBERT, so the combined treatment is the natural
parity condition. A null result on the bundled treatment tells us that the remaining gap is not
in the retriever or feedback mechanism; a positive result tells us it is. Either conclusion is
scientifically interpretable.

**What is sacrificed**: We cannot attribute a positive result exclusively to ColBERT or
exclusively to feedback. The post-hoc attribution requires follow-up. This is explicitly
acknowledged as a limitation.

**What separating would require**: If the reviewer mandates separation, the compute budget
doubles to n=8 runs minimum (4 ColBERT-only, 4 bundled), requiring a 2-week extension. The
Phase 2 reviewer's recommendation will determine whether separation is necessary to achieve
Phase 2 approval.

---

## 3. Independent Variables

There is one compound independent variable in this experiment: **retriever + feedback bundle**
(BM25+title-only vs. ColBERT+full-passage).

| Variable | Control value | Treatment value |
|----------|---------------|-----------------|
| Retriever | BM25s (existing `static_f1_600`) | ColBERTv2 (`static_colbert_f1_600`) |
| Failure feedback depth | Title only for missing gold docs | "Title \| passage text" for missing gold docs |
| Problem variant | `chains/hotpotqa/static_f1_600` | `chains/hotpotqa/static_colbert_f1_600` |

All other variables are held constant at the cold-start F1+600 configuration established in PR
#75 (cold_start experiment), making the cold-start BM25 reference (mean 59.58%, n=4) the
natural control distribution.

**Why not also vary prompts (NLP vs. default)?** NLP prompts showed null effects in two prior
experiments (crossover P vs S: +2.00pp, p=0.20; nlp_prompts experiment). Default prompts
maximize comparability with the cold_start reference. The question of NLP×ColBERT interaction
is pre-registered as a follow-up if this experiment yields a POSITIVE or STRONG POSITIVE
result.

**Why cold start (not warm start)?** Cold start produces higher test EM (+2.47pp, p=0.008,
PR #75) than warm-start from ddce37b4. Since we want to test the ceiling achievable with
ColBERT+feedback under GigaEvo evolution, cold start from the baseline chain is the correct
initialization for the new problem variant. Warm-starting from a BM25-evolved program into a
ColBERT evaluation environment risks confounding — the program's prompt strategies were
optimized for BM25 retrieval patterns and may actively conflict with ColBERT's higher-recall,
different-passage-ordering outputs.

---

## 4. Dependent Variables

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test EM at gen 25 (best-by-val) | 300-sample held-out test set; EM scoring; thinking mode Qwen3-8B | YES — primary for H0/H1 |
| Val-test EM gap | Val EM (`valid_frontier_em` Redis key) minus test EM | YES — secondary; GEPA shows a reduced gap from better retrieval |
| Inter-run SD of test EM | SD across the 4 runs | YES — distribution estimate; compare to cold-start BM25 SD=1.00pp |
| Birth-generation of best-by-val | From `valid_frontier_fitness` trajectory | NO — stagnation diagnostic |
| Gen-0 val EM | From Redis at gen 0 | NO — cold-start initialization verification |
| Val F1 frontier trajectory (gen 1–25) | Per-generation `valid_frontier_fitness` (F1) | NO — convergence diagnostic |
| Invalidity rate at gen 5 | Fraction of invalid programs per run | NO — monitoring |
| Retrieval recall@7 at gen 0 | Fraction of gold docs retrieved in first 7 results (spot-check) | NO — ColBERT quality verification; pre-registered minimum threshold >= 0.40; if observed recall@7 < 0.40 at gen 0 across all 4 runs, ColBERT retrieval is considered defective and runs are invalidated per criterion 7 |

**Primary metric**: Test EM at final generation (gen 25), best-by-val program, evaluated on
the fixed 300-sample held-out test set, thinking mode Qwen3-8B. Consistent with all prior
experiments and the GEPA benchmark (62.3%).

**Gen-0 diagnostic**: The unoptimized baseline chain with ColBERT retrieval is expected to
produce gen-0 val EM in the range 0.40–0.55. If ColBERT substantially improves retrieval, the
baseline chain may already score noticeably above the BM25 cold-start gen-0 value (~0.42 in
PR #75). A gen-0 val EM > 0.55 is not necessarily a cold-start configuration failure — it may
reflect ColBERT's retrieval advantage on the unoptimized chain. The halt criterion for
misconfiguration is gen-0 val EM > 0.65 (implying an evolved program was used), not > 0.55.
This is a deliberate relaxation from the cold_start criterion (which was > 0.55) to
accommodate ColBERT's expected baseline uplift.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Chain topology | 6-step fixed (2 tool, 4 LLM) | Unchanged across all experiments; static mode |
| Fitness metric | F1 (token-level partial credit) | Consistent with cold_start reference (PR #75) |
| Validation sample size | 600 (fixed, first 600 train samples) | Consistent with cold_start reference (PR #75) |
| Val set protocol | Fixed sequential (first 600 train samples) | No rotation; rotation permanently excluded |
| `prompts` | `default` | Consistent with cold_start reference; NLP null in 2 prior experiments |
| `pipeline` | `hotpotqa_colbert` | Required for `static_colbert_f1_600`; uses `ColBERTPipelineBuilder` and `HotpotQAColBERTFormatter` for full-passage feedback; never `pipeline=standard` or `pipeline=hotpotqa_asi` |
| Seed initialization | **Cold** — no `program_loader.problem_dir` | New problem variant `static_colbert_f1_600` baseline program must be the unoptimized chain |
| Chain LLM | Qwen3-8B, thinking mode ON (default chat template) | Required for GEPA comparison |
| Mutation LLM | Qwen3-235B-A22B-Thinking, one server per run | Consistent with all prior runs |
| `num_parents` | **1** (explicit override; default = 2) | Single-parent mutation; consistent with cold_start |
| `max_elites_per_generation` | **8** (explicit override; default = 5) | Consistent with all prior HotpotQA experiments |
| `max_mutations_per_generation` | **8** | C(8,1)=8, capped at 8 → 8 mutations/gen |
| `mutation_mode` | `rewrite` | Default; compatible with num_parents=1 |
| `parent_selector` | `AllCombinationsParentSelector` | Standard selector |
| `stage_timeout` | 6000 | 600-sample eval empirical max ~2300s; 6000 provides 2.6× margin |
| `dag_timeout` | 9000 | stage_timeout (6000) + mutation LLM stages (~1500) + headroom (1500) |
| `max_generations` | 25 (all runs) | Consistent with cold_start; stagnation confirmed by gen 11–19 at latest |
| `step_max_tokens` | 8192 for all LLM steps | Uniform; thinking mode exhausts budget — do not reduce for steps 3/6 |
| Test evaluation | Fixed 300-sample test set; thinking mode verified | Consistent with all prior runs |
| Random failure sampling | All failures returned from validate.py; formatter samples 10 with NO_CACHE | Required; cf0cfc1 |
| HTTP timeout | 600s (`httpx.Timeout(timeout=600.0)`) | Required for 600-sample runs; fixed at c0186a8 |
| `step_max_tokens` uniformity | 8192 for all steps | Do NOT reduce for steps 3/6 |

**[Critical: `pipeline=hotpotqa_colbert`]**: The correct pipeline for this experiment is
`pipeline=hotpotqa_colbert`, which uses `ColBERTPipelineBuilder` (from
`static_colbert_f1_600/pipeline.py`) and `HotpotQAColBERTFormatter`. This formatter provides
full "Title | passage text" feedback for missing gold documents, which is the richer-feedback
half of the bundled intervention. Using `pipeline=hotpotqa_asi` (which instantiates
`HotpotQAASIFormatter` — title-only feedback) would silently zero out the feedback-depth IV
with no error, no warning, and no post-hoc detectability from logs. This is experiment-
invalidating. The `config/pipeline/hotpotqa_colbert.yaml` file explicitly warns: "NEVER use
pipeline=standard or pipeline=hotpotqa_asi for this variant." This warning is enforced via
pre-launch `--cfg job` verification (Appendix A item 4) and run-invalidation criterion 2.

**[Critical: `num_parents=1`]**: Default in `config/constants/evolution.yaml` is `num_parents:
2`. All four runs must include `num_parents=1` as an explicit Hydra override. Mandatory `--cfg
job` pre-launch check.

**[Critical: `max_elites_per_generation=8`]**: Default is 5. Must appear explicitly in every
launch command. Mandatory `--cfg job` pre-launch check.

**[Critical: ColBERT retriever]**: `shared_config.RETRIEVER` must be `"colbert"` in the new
problem variant `static_colbert_f1_600/`. This is a per-problem-dir setting — it must NOT
change any existing problem dirs (backward compatibility). The `COLBERT_INDEX_DIR` in
`shared_config.py` currently resolves to `experiments/colbert_index/` at repo root, which does
not exist. The index being built is at `experiments/hotpotqa/indexes/colbert_index/`. The plan
phase must resolve this path discrepancy and confirm via the Python-import-based preflight
check in Appendix A item 5.

---

## 6. Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | Seed | `num_parents` | `max_elites` | `max_mut` | `stage_timeout` | `dag_timeout` | `max_gen` | Val N | Fitness |
|-----|-------|-----------|-----------|-----------|----------------|------|:-------------:|:------------:|:---------:|:--------------:|:------------:|:--------:|:-----:|:-------:|
| U1 | colbert-1 | 0 | `hotpotqa_colbert` | `default` | `chains/hotpotqa/static_colbert_f1_600` | Cold | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |
| U2 | colbert-2 | 1 | `hotpotqa_colbert` | `default` | `chains/hotpotqa/static_colbert_f1_600` | Cold | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |
| U3 | colbert-3 | 2 | `hotpotqa_colbert` | `default` | `chains/hotpotqa/static_colbert_f1_600` | Cold | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |
| U4 | colbert-4 | 3 | `hotpotqa_colbert` | `default` | `chains/hotpotqa/static_colbert_f1_600` | Cold | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |

**Bold values require explicit Hydra overrides**: `num_parents=1` (default is 2);
`max_elites_per_generation=8` (default is 5).

**Combinatorics verification**:

| Run | num_parents | max_elites | Parent combos | max_mutations | Actual mut/gen (mature archive) |
|-----|:-----------:|:---------:|:-------------:|:-------------:|:-------------------------------:|
| U1 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| U2 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| U3 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| U4 | 1 | 8 | C(8,1) = 8 | 8 | 8 |

Early generations (archive filling from cold start): expected gen 0 → 1 elite → 1 mutation;
maturity (~8 elites) by gen 3–5. Same early-generation deficit as in cold_start experiment —
symmetric across all four runs.

**Chain LLM assignment** (one chain server per run, no sharing):

| Run | Chain LLM URL |
|-----|---------------|
| U1 | `http://10.226.17.25:8001/v1` |
| U2 | `http://10.226.17.25:8000/v1` |
| U3 | `http://10.225.185.235:8001/v1` |
| U4 | `http://10.225.185.235:8000/v1` |

**Mutation LLM assignment** (one per run, from the 4-server pool):

| Run | Mutation LLM URL |
|-----|------------------|
| U1 | `http://10.226.72.211:8777/v1` |
| U2 | `http://10.226.15.38:8777/v1` |
| U3 | `http://10.226.185.131:8777/v1` |
| U4 | `http://10.225.51.251:8777/v1` |

**Redis DBs**: 0, 1, 2, 3. DBs 0–3 were confirmed flushed after the cold_start experiment
(PR #75). Verify 0 keys in all four DBs immediately before launch.

**BM25 cold-start reference** (historical, not re-run — used as the comparison distribution
for Test 1):

| Run | Experiment | Retriever | Feedback | Test EM |
|-----|-----------|-----------|----------|:-------:|
| T1 (PR #75) | cold_start | BM25s | Title only | 59.33% |
| T2 (PR #75) | cold_start | BM25s | Title only | 60.67% |
| T3 (PR #75) | cold_start | BM25s | Title only | 58.33% |
| T4 (PR #75) | cold_start | BM25s | Title only | 60.00% |

BM25 cold-start reference: mean = 59.58%, SD = 1.00pp, n=4.

---

## 7. Sample Size Justification

**N=4 independent replications of a single ColBERT+feedback cold-start condition.** This
mirrors the cold_start experiment design (PR #75), enabling direct comparison using a
one-sample t-test against the BM25 cold-start reference distribution.

**What N=4 enables**:

1. **One-sample t-test against fixed reference mean**: With N=4, df=3, one-sided α=0.05,
   t_critical = 2.353. This is the same test structure as PR #75, enabling symmetric reporting.

2. **Within-experiment SD estimate**: Quantifies whether ColBERT+feedback changes the
   inter-run variance relative to the BM25 SD=1.00pp baseline. If the ColBERT landscape has
   higher variance (multiple distinct basins), SD > 2pp would indicate that N=4 is
   insufficient for strong mean-level conclusions.

3. **Mean CI**: t-based 95% CI: mean ± 3.182 × SD/2.

**Formal power — MDE calculation**:

The cold_start reference SD was 1.00pp (n=4, F1+600+np=1). If the ColBERT landscape has
similar variance (expected, since the evolution mechanism is unchanged), the anticipated SD
is ~1–2pp.

MDE formula for one-sample t-test at 80% power:

    MDE = (t_alpha + t_beta) × sigma / sqrt(N)

where t_alpha = t(0.95, df=3) = 2.353 (one-sided α=0.05) and t_beta = t(0.80, df=3) = 0.978
(80% power at df=3).

At SD=1.00pp (matching BM25 cold-start variance), N=4:

    MDE = (2.353 + 0.978) × 1.00 / sqrt(4) = 3.331 × 0.500 = 1.666pp

At SD=2.00pp, N=4:

    MDE = (2.353 + 0.978) × 2.00 / sqrt(4) = 3.331 × 1.000 = 3.331pp

The experiment therefore has **80% power to detect a ColBERT vs. BM25 delta of 1.666pp at
SD=1pp** (the observed BM25 variance). The pre-registered POSITIVE threshold is +2.42pp above
the reference mean (62.00%), which exceeds the corrected 1.666pp MDE at SD=1pp by 0.754pp —
meaning the experiment is adequately powered for H1 at the expected variance level. At SD=2pp,
the MDE is 3.331pp, requiring the mean to reach 62.91% to achieve 80% power, which is close to
GEPA; in this case the experiment may observe a POSITIVE result (mean >= 62.00%) without 80%
power, and the CI will be wide. This is acknowledged in Section 12 (Risk 3).

*Note on t_beta correction*: A previous draft stated t_beta = 1.250, which is t(0.85, df=3),
not t(0.80, df=3). The correct value 0.978 = t(0.80, df=3) is used throughout. The stated MDE
of 1.80pp in the prior draft was overstated by 8.1%. The error was conservative (actual power
at the stated MDE exceeded 80%), and no decision threshold is affected: the POSITIVE threshold
of 2.42pp above reference exceeds the corrected MDE of 1.666pp at SD=1pp by 0.754pp.

**Why not N=8?** The compute budget permits 4 runs (4 DBs, 4 mutation LLM servers, 4 chain LLM
endpoints). N=8 would require two sequential batches (8+ days wall-clock) or coordination with
additional GPU resources. Given the BM25 cold-start SD=1.00pp is the tightest ever observed in
GigaEvo HotpotQA runs, N=4 is expected to be adequate. If the observed SD exceeds 3pp, a
follow-up N=8 experiment is pre-registered as a recommended next step.

---

## 8. Statistical Tests

### Test 1: One-sample t-test — ColBERT+feedback mean vs. BM25 cold-start reference (primary)

**Comparison**: Mean test EM across U1–U4 vs. BM25 cold-start reference mean of 59.58%.

**Test statistic**: t = (colbert_mean − 59.58%) / (colbert_SD / sqrt(4)), df=3.
One-sided (H1: colbert_mean > 59.58%). Pre-registered significance threshold: p < 0.05.

**Verdict table**:

| t-test result | colbert_mean | Verdict |
|:-------------:|:------------:|---------|
| p < 0.05 | >= 62.00% (MDE) | **POSITIVE** — ColBERT+feedback significantly outperforms BM25 cold-start; combined intervention is effective |
| p < 0.05 | [59.51%, 62.00%) | **SUGGESTIVE** — significant improvement over BM25 reference but below pre-registered MDE; replication with N=8 required |
| p < 0.05 | >= 62.3% (GEPA) | **STRONG POSITIVE** (special case of POSITIVE) — ColBERT+feedback GigaEvo reaches GEPA in expectation |
| p >= 0.05 | >= 62.00% | **SUGGESTIVE** — mean above MDE but not significant at N=4; wider CI; N=8 required |
| p >= 0.05 | [59.51%, 62.00%) | **SUGGESTIVE** — mean above noise floor but t-test not significant; N=8 required |
| p >= 0.05 | [57.18%, 59.51%) | **NULL** — ColBERT+feedback indistinguishable from BM25 cold-start reference |
| colbert_mean < 57.18% | any | **NEGATIVE** — ColBERT+feedback underperforms BM25 cold-start; reported regardless of t-test |

### Test 2: One-sample t-test — ColBERT+feedback mean vs. GEPA benchmark (secondary)

**Test statistic**: t = (colbert_mean − 62.3%) / (colbert_SD / sqrt(4)), df=3.
One-sided (H1: colbert_mean > 62.3%). Pre-registered threshold: p < 0.05.

| t-test result | Any run >= 62.3%? | Verdict |
|:-------------:|:-----------------:|---------|
| p < 0.05 | — | **STRONG POSITIVE** — ColBERT+feedback GigaEvo significantly beats GEPA in expectation |
| p >= 0.05 | YES | **POSITIVE (single run)** — at least one run beats GEPA, but distribution mean does not |
| p >= 0.05 | NO | **NULL vs GEPA** — ColBERT+feedback does not reliably reach GEPA |

### Test 3: Stagnation birth-generation (exploratory)

**Criterion**: Mean birth-generation of best-by-val program across U1–U4.

**Pre-registered prediction**: Mean birth-gen >= 10 (consistent with cold-start exploration
confirmed in PR #75, mean birth-gen 16.5). If ColBERT+richer feedback provides clearer
improvement signal, stagnation may occur earlier (< 10) or later (> 16.5). Either deviation
from the cold-start BM25 pattern is reported as a mechanistic finding.

| Mean birth-gen | Verdict |
|:--------------:|---------|
| >= 10 | **CONSISTENT WITH COLD-START PATTERN** |
| < 10 | **FASTER CONVERGENCE** — better feedback signal reduces exploration phase |
| > 20 | **EXTENDED EXPLORATION** — ColBERT landscape has higher-quality basin further from baseline |

### Test 4: Inter-run SD vs. BM25 cold-start SD (descriptive)

SD of test EM across U1–U4 compared to BM25 cold-start SD = 1.00pp.

| ColBERT SD | Interpretation |
|:----------:|----------------|
| < 1.5pp | Similar or tighter than BM25; landscape is comparably regular; N=4 adequate |
| 1.5–3pp | Moderately higher variance; N=4 marginally adequate; CI will be wider |
| > 3pp | ColBERT landscape substantially more variable; N=4 insufficient; N >= 8 required |

### Binomial confidence intervals (individual runs)

```
CI = test_EM ± 1.96 × sqrt(p × (1−p) / 300)
```

Mean CI (t-based, df=3):

```
CI = colbert_mean ± 3.182 × colbert_SD / 2
```

Both reported in Phase 5.

---

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| **Bundled intervention — attribution ambiguity** | A positive result cannot be attributed to ColBERT alone or feedback depth alone. A null result also cannot rule out that one component helped while the other hurt. | Pre-registered limitation; explicitly stated in Phase 5. If POSITIVE, follow-up experiment (feedback-only arm with BM25) is pre-registered as priority next step. If NULL, the bundled null rules out the combination but not the components. |
| **ColBERT index incompleteness** | The ColBERT index at `experiments/hotpotqa/indexes/colbert_index/` currently contains only `plan.json` — the build is in progress. If the index is incomplete at launch time, all four runs will fail at retrieval or produce degenerate results. | **Hard gate (Section 12)**: Verify ColBERT index is fully built before any Phase 3 code changes. Confirm all 210 `.pt` chunk files are present and run `verify_colbert.py` end-to-end. Do NOT proceed until this gate passes. |
| **COLBERT_INDEX_DIR path mismatch** | `shared_config.COLBERT_INDEX_DIR` resolves to `experiments/colbert_index/` (repo root level, does not exist at runtime), but the index is at `experiments/hotpotqa/indexes/colbert_index/`. The guard `if not index_dir.exists()` will raise `FileNotFoundError` before any Searcher is constructed, failing every run immediately. | **Hard gate (Section 12)**: Import `shared_config` from within Python and print `COLBERT_INDEX_DIR`; confirm the resolved path exists on disk. Fix the path discrepancy in Phase 3 before any other code changes. Add the Python-import preflight check to `launch.sh` (Appendix A item 5). |
| **Silent BM25 fallback in `static_colbert_f1_600`** | `shared_config.py` also defines `BM25S_INDEX_DIR` and `CORPUS_PATH`; if `_ensure_colbert_initialized` raises an exception that is swallowed upstream, the chain could silently fall back to BM25 retrieval. | Run-invalidation criterion 7 covers post-hoc detection. Active preflight: `verify_colbert.py` must succeed end-to-end before launch; any silent fallback would produce non-empty BM25 results, which `verify_colbert.py` would catch if it validates the retriever type. |
| **`pipeline=hotpotqa_colbert` required; `pipeline=hotpotqa_asi` is experiment-invalidating** | Using `pipeline=hotpotqa_asi` instantiates `HotpotQAASIFormatter` (title-only feedback), silently zeroing out the feedback-depth IV with no error or warning and no post-hoc detectability from logs. | Mandatory `--cfg job` pre-launch check: confirm `_target_: problems.chains.hotpotqa.static_colbert_f1_600.pipeline.ColBERTPipelineBuilder` in output for every run. Run-invalidation criterion 2 catches this post-hoc. |
| **`num_parents` default = 2** | Omission of `num_parents=1` converts any run to a crossover run. | Mandatory `--cfg job` pre-launch check: confirm `num_parents: 1` for all four runs. |
| **`max_elites_per_generation` default = 5** | Omission silently reduces mutations to 5/gen and breaks comparability with cold_start reference (8/gen). | Mandatory `--cfg job` pre-launch check: confirm `max_elites_per_generation: 8` for all four runs. |
| **BM25 chain evolved programs used as cold start** | If the new problem variant `static_colbert_f1_600` is created by copying `static_f1_600` and the `initial_programs/` directory is not reset to the unoptimized baseline, the cold start may begin from a BM25-evolved program that is incompatible with ColBERT retrieval patterns. | **Phase 3 mandatory**: Inspect `static_colbert_f1_600/initial_programs/` (or equivalent). Must contain only the unoptimized baseline chain. Expected gen-0 val EM: 0.40–0.55 (allowing for ColBERT baseline uplift). Halt if gen-0 val EM > 0.65. |
| **ColBERT memory / latency at 600 samples** | ColBERT loads a large in-process index (~several GB). With 4 concurrent runs (one per exec_runner), ColBERT inference may saturate GPU memory or slow down eval to > 8 min/gen. The 600-sample stage_timeout of 6000s may be insufficient. | Phase 3: Benchmark a single 600-sample ColBERT evaluation pass before launch. Amendment 0 criteria defined in Section 12. |
| **ColBERT per-worker GPU memory contention** | Each exec_runner subprocess loads the ColBERT index independently. With 4 workers × 4 runs = 16 concurrent ColBERT index loads on 4 GPU servers (4 loads per server), GPU OOM may occur. **Pre-registered halt criterion**: if any exec_runner subprocess fails to load the ColBERT index (raises `RuntimeError` or `FileNotFoundError` at `_ensure_colbert_initialized`), halt the affected run immediately and reduce `num_workers` from 4 to 2 via Amendment before resuming. | Phase 3: Confirm ColBERT loads in CPU-only mode (retrieval only; no training) or confirm VRAM headroom on each chain LLM server. Monitor exec_runner logs at gen 0–1 for index-load failures. |
| **Retrieval parity with GEPA** | Even with ColBERT, GigaEvo's retrieval setup may differ from GEPA's in subtle ways (different passage segmentation, different k, different index build parameters). Exact parity with GEPA's ColBERT setup is not guaranteed. | Acknowledged as residual confound. `shared_config.py` uses `colbert-ir/colbertv2.0` checkpoint matching GEPA. k=7 is standard. Document index build parameters in Phase 3 for reproducibility. |
| **Richer feedback content correctness** | The new failure feedback format ("Title \| passage text") must correctly match gold documents from the HotpotQA supporting facts, not just any retrieved passage. If the feedback formatter returns the wrong passage text, the mutation LLM receives misleading signal. | Phase 3: Unit-test the new failure formatter on 5 sample failures. Verify that the passage text returned corresponds to gold supporting facts, not retrieved-but-wrong passages. |
| **Server load asymmetry** | U1/U2 share host A (10.226.17.25); U3/U4 share host B (10.225.185.235). Same two-cluster structure as cold_start. | Same mitigation as cold_start: monitor host-stratified means in Phase 5; flag if divergence > 3pp. |

---

## 10. Stop Criteria

### Stagnation-based early completion

If `valid_frontier_fitness` (F1) shows no improvement for >= 10 consecutive generations AND
the current generation >= 15, the run may be terminated early. Consistent with cold_start
protocol. If any run still improves past gen 20, consider a pre-registered extension to 40 gens
(amendment required before gen 20).

### Early termination criteria

- **ColBERT index returns empty results** at gen 0 for any run: Halt immediately. Diagnose
  index path and completeness. Do not proceed until retrieval is verified.
- **Invalidity rate > 50% at gen 5 for any run**: Pause; diagnose stage_timeout. If median
  eval time exceeds 5000s, increase stage_timeout to 9000 before resuming.
- **Gen-0 val EM = 0.0 for any run**: Halt; diagnose before proceeding.
- **Gen-0 val EM > 0.65 for any run**: Halt — likely a BM25-evolved warm start was used.
  Verify `static_colbert_f1_600/initial_programs/` and restart with correct config.
- **exec_runner ColBERT index-load failure**: If any exec_runner subprocess fails to load the
  ColBERT index (logged as `FileNotFoundError` or `RuntimeError` in `_ensure_colbert_initialized`),
  halt the affected run and reduce `num_workers` from 4 to 2 before resuming (Amendment required).

### Run invalidation criteria

A run is excluded from all analyses if any of the following apply:

1. Thinking mode not active: `<think>` blocks absent from >= 5% of chain outputs at gen 1.
2. `pipeline=hotpotqa_asi` or `pipeline=standard` used (repr-contamination / title-only-feedback bug).
3. Invalidity rate > 90% at gen 10.
4. Gen-0 val EM > 0.65 (warm-start or BM25-evolved initialization detected).
5. `max_elites_per_generation` confirmed at 5 (not 8) in post-hoc log inspection.
6. `num_parents` confirmed at 2 (not 1) in post-hoc log inspection.
7. ColBERT retrieval confirmed non-functional (empty passages returned) at any generation, or
   retrieval recall@7 < 0.40 at gen 0 across all 4 runs.

If one or two runs are invalidated, the remaining valid runs are analyzed with adjusted df.
If only 1 run remains valid, the t-test is replaced by a descriptive summary and the verdict
is capped at SUGGESTIVE pending replication.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time per run (600-sample, 25 gens) | ~10–17h (25 gens × ~24 min/gen for 600 samples / 4 async workers, assuming ColBERT eval latency comparable to BM25; may increase — see Risk 2) |
| Total wall time (4 runs parallel) | ~17h wall-clock |
| Redis DBs | 4 (DBs 0, 1, 2, 3) |
| Mutation LLM servers | 4 × Qwen3-235B-A22B-Thinking (one per run) |
| Chain LLM servers | 4 × Qwen3-8B thinking (one per run) |
| Test evaluation | ~5 min each × 4 runs = ~20 min total; must use `static_colbert_f1_600` problem variant (not any BM25 variant); `run_test_eval.sh` must be implemented and verified before launch (Appendix A item 3) |
| New code required | New problem variant `static_colbert_f1_600/`; set `RETRIEVER="colbert"` in its config; update failure formatter to emit full passage text for missing gold docs; fix `COLBERT_INDEX_DIR` path. Estimated ~1–2 days engineering. |
| ColBERT index build | Already initiated (in progress); `plan.json` exists (210 chunks required). Full build time ~hours on GPU. Must be complete and verified before any Phase 3 code changes. |

---

## 12. Open Questions / Risks

### Mandatory hard gate: ColBERT index and path verification (before any Phase 3 code changes)

**This gate must pass before any Phase 3 code changes are made.** It is not merely a risk —
it is a pre-registration blocker. Three conditions must all be confirmed:

**(a) `COLBERT_INDEX_DIR` resolves to an existing directory on disk.**
Run the following from the repo root:
```bash
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python -c \
  "from problems.chains.hotpotqa.shared_config import COLBERT_INDEX_DIR; print(COLBERT_INDEX_DIR)"
```
Confirm the printed path exists on disk (`ls <printed_path>` returns files). If it does not
exist, fix `COLBERT_INDEX_DIR` in `shared_config.py` first. The current path
(`experiments/colbert_index/` at repo root) does not exist; the actual index location is
`experiments/hotpotqa/indexes/colbert_index/`. This path discrepancy causes
`_ensure_colbert_initialized` to raise `FileNotFoundError` before any Searcher is constructed,
failing all four runs immediately at first retrieval call.

**(b) The directory contains all 210 `.pt` chunk files matching `plan.json`'s `num_chunks`.**
Run:
```bash
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python -c "
import json, pathlib
from problems.chains.hotpotqa.shared_config import COLBERT_INDEX_DIR
index_dir = pathlib.Path(COLBERT_INDEX_DIR)
plan = json.loads((index_dir / 'plan.json').read_text())
num_chunks = plan['num_chunks']
pt_count = len(list(index_dir.glob('*.pt')))
print(f'num_chunks (plan.json): {num_chunks}')
print(f'.pt files found: {pt_count}')
assert pt_count == num_chunks, f'FAIL: {pt_count} != {num_chunks}'
print('PASS')
"
```
A result of "more than one file" is not sufficient — the check must confirm all 210 chunk
files are present. Until the index build completes, ColBERT cannot retrieve anything.

**(c) End-to-end retrieval confirmed by running `verify_colbert.py` successfully.**
`verify_colbert.py` must construct the Searcher, issue test queries, and return non-empty
results. This confirms both that the path is correct and that the Searcher's Run-context
resolution (which maps to `root/experiment/indexes/index_name`) is consistent with the
`COLBERT_INDEX_DIR` guard. Pass (a) and (b) first; then run `verify_colbert.py`.

**Do not proceed to any code changes until all three checks pass.**

### Pre-registered latency benchmark and 300-sample fallback specification (Amendment 0 trigger)

**Amendment 0 trigger — latency criterion**: Before launch, run `verify_colbert.py` on a
representative batch of queries. If the **single-query latency** (averaged over the test
batch) exceeds **500ms per query**, Amendment 0 is filed before launch, reducing val N from
600 to 300 samples and adjusting stage_timeout accordingly. The 500ms/query threshold is
chosen because 600 samples × 2 hops × 500ms = 600s retrieval time alone per eval pass, which
combined with LLM inference would exceed the 6000s stage_timeout. At 300 samples, 300 × 2 ×
500ms = 300s retrieval time, remaining within a 6000s stage_timeout with adequate headroom.

**Fallback comparison baseline if val N reduced to 300 samples**: The BM25 cold-start reference
(mean 59.58%, SD 1.00pp, n=4, PR #75) was computed at 600 samples. No BM25 300-sample
reference exists for the F1+cold-start condition — the BM25 runs in PR #75 all used 600
samples, and the 300-sample distribution cannot be reliably estimated from existing data. If
Amendment 0 is triggered:

- The pre-registered POSITIVE threshold of 62.00% (calibrated against the 600-sample reference)
  no longer applies under the 300-sample fallback.
- A POSITIVE verdict under 300-sample fallback **requires a concurrent BM25 control run** at
  300 samples (one additional run, same F1+cold-start+np=1 protocol) to establish the reference
  distribution under matched conditions. Without a concurrent control, the maximum attainable
  verdict under the 300-sample fallback is **SUGGESTIVE**, pending replication under matched
  conditions.
- Amendment 0 must be filed before launch and must specify the concurrent control run if the
  300-sample path is activated.

### Priority risks (resolved in Phase 3)

**Risk 1 — ColBERT index completeness (CRITICAL — now a mandatory gate above).**
The ColBERT index at `experiments/hotpotqa/indexes/colbert_index/` currently contains only
`plan.json`. A complete index requires 210 `.pt` chunk files plus `doclens`, `ivf.pid.pt`,
`centroids.npy`, etc. Until the build completes, no ColBERT retrieval is possible. This is
the single highest-priority blocker. The mandatory hard gate above enforces this as a code-
change blocker, not merely a launch-time check.

**Risk 2 — ColBERT eval latency at 600 samples (HIGH).**
BM25s retrieval is O(N) with a pre-built sparse index and takes ~1–2s for 600 queries. ColBERT
is a dense retrieval model that loads ~several GB of compressed embeddings and runs FAISS
search. `ColBERTRetriever.batch_retrieve` iterates queries sequentially (one
`_colbert_searcher.search(query, k=k)` call per query); at 600 samples with two retrieval
steps (hop-1 and hop-2), the validator makes 1200 sequential calls per evaluation pass. Per-
query latency of 50–500ms yields 60–600s per hop or 120–1200s total for retrieval alone —
before any LLM inference. Phase 3 must benchmark 600-sample ColBERT retrieval before
finalizing the design. Amendment 0 criteria are pre-registered above (> 500ms/query triggers
300-sample fallback).

**Risk 3 — Large ColBERT inter-run SD reducing test power (MEDIUM).**
If ColBERT introduces more landscape variance than BM25 (SD > 3pp), the t-test will be
underpowered at N=4. With SD=3pp and N=4, the 80%-power MDE is 4.997pp — requiring
colbert_mean >= 64.58% to achieve both p<0.05 and 80% power. In this scenario, SUGGESTIVE is
the best attainable verdict at N=4, and N >= 8 replication would be required for resolution.
The cold_start SD=1.00pp gives grounds for optimism, but if the ColBERT landscape has richer
multi-modal structure, variance may be higher. Phase 5 will report this explicitly.

**Risk 4 — Attribution of null result (MEDIUM).**
If the bundled experiment yields NULL, we cannot determine whether ColBERT alone would help,
feedback depth alone would help, or neither would help. A null on the bundle is actionable
(rules out the most natural parity condition with GEPA) but leaves open the question of whether
the components individually have value. This is an inherent cost of the bundled design and is
acceptable given the compute budget constraint.

**Risk 5 — Richer feedback content accuracy (LOW-MEDIUM).**
The new failure formatter must correctly identify the full passage text for gold supporting
documents. If HotpotQA's supporting_facts field points to documents not always present in the
ColBERT-indexed corpus (possible for very short abstracts or documents with truncation in the
wiki17_abstracts.jsonl corpus), the formatter may silently return partial text or empty strings.
This degrades the feedback quality and may produce a NEGATIVE result even when ColBERT is
providing better retrieval. Phase 3 unit tests for the formatter are mandatory.

### Scientific open questions after this experiment

- **If STRONG POSITIVE or POSITIVE**: Which of the two components drives the gain? Pre-register
  a 2-arm follow-up: BM25+rich-feedback (feedback only) vs. ColBERT+title-only (retriever only),
  n=2 each, to decompose the effect. With a large combined effect, n=2 per arm may be
  sufficient to attribute the majority of the gain.
- **If NULL**: Does the static prompt-evolution framework have a hard ceiling near 59–62%
  regardless of retriever quality? If ColBERT+full-feedback cannot clear 62.3%, the ceiling
  is likely in the chain reasoning steps, not in retrieval — motivating structural topology
  changes or step-level learned components.
- **If NEGATIVE**: Does ColBERT's different passage ordering confuse the evolved BM25-style
  prompts in the baseline chain, requiring more generations to adapt? Consider warm-starting
  from a BM25 cold-start evolved program (T2 or T4 from PR #75) for ColBERT to see if the
  baseline chain is the bottleneck.

---

## Appendix A: Code Changes Required (Phase 3 Checklist)

The following must be implemented and verified in Phase 3 before launch.

**PREREQUISITE — Mandatory hard gate (before any item below)**:
The ColBERT index gate from Section 12 must pass in full ((a) `COLBERT_INDEX_DIR` path exists,
(b) all 210 `.pt` chunk files present, (c) `verify_colbert.py` succeeds end-to-end) before
any code changes listed below are made.

1. **Create `problems/chains/hotpotqa/static_colbert_f1_600/`** as a new problem variant.
   - Copy `static_f1_600/` as the starting point.
   - Set `RETRIEVER = "colbert"` in the variant's shared config (or a local override).
   - Verify `COLBERT_INDEX_DIR` resolves to the correct completed index path (gate above).
   - Confirm `initial_programs/` contains only the unoptimized baseline chain.

2. **Update failure formatter** (in `validate.py` or the formatter class used by
   `hotpotqa_colbert` pipeline for this problem variant):
   - Change missing-gold-doc feedback from `[title, ...]` list to `"Title | passage text"` format.
   - Add a lookup from title → full passage text using the wiki17_abstracts corpus.
   - Unit-test on 5 sample failures: verify passage text is non-empty and matches the title.

3. **Implement and verify `run_test_eval.sh`** before launch:
   - The test eval script must invoke the `static_colbert_f1_600` problem variant, NOT any
     BM25 variant (`static_f1_600`, `static_a`, etc.). Using a BM25 problem variant for test
     evaluation would score the best-by-val ColBERT program against a BM25 retriever, silently
     invalidating test EM results.
   - Confirm the script is not stubbed with `exit 1` before launch day.
   - Run a dry-run test evaluation against 1–5 samples to confirm the ColBERT pipeline is active.

4. **Verify `pipeline=hotpotqa_colbert` compatibility**:
   - Run `PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py problem.name=chains/hotpotqa/static_colbert_f1_600 pipeline=hotpotqa_colbert --cfg job` and verify no config errors.
   - Confirm `--cfg job` output contains `_target_: problems.chains.hotpotqa.static_colbert_f1_600.pipeline.ColBERTPipelineBuilder`. Any reference to `HotpotQAASIFormatter` in this output indicates the wrong pipeline is active and must be corrected before launch.
   - Confirm `prompts_dir: ${prompts.dir}` appears in both `evolution_context` and `mutation_operator` blocks in `--cfg job` output (per CLAUDE.md Critical Config Bug note).

5. **Preflight checks in `launch.sh`**:
   - **(a) Confirm `COLBERT_INDEX_DIR` via Python import**: Run
     ```bash
     COLBERT_INDEX_DIR=$(PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python -c \
       "from problems.chains.hotpotqa.shared_config import COLBERT_INDEX_DIR; print(COLBERT_INDEX_DIR)")
     echo "COLBERT_INDEX_DIR=${COLBERT_INDEX_DIR}"
     ```
     Verify the printed path exists on disk.
   - **(b) Confirm chunk-file count equals `num_chunks` from `plan.json`**: Run
     ```bash
     PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python -c "
     import json, pathlib
     from problems.chains.hotpotqa.shared_config import COLBERT_INDEX_DIR
     index_dir = pathlib.Path(COLBERT_INDEX_DIR)
     plan = json.loads((index_dir / 'plan.json').read_text())
     num_chunks = plan['num_chunks']
     pt_count = len(list(index_dir.glob('*.pt')))
     print(f'num_chunks (plan.json): {num_chunks}')
     print(f'.pt files found: {pt_count}')
     assert pt_count == num_chunks, f'FAIL: {pt_count} != {num_chunks}'
     print('PASS: all chunk files present')
     "
     ```
   - Assert `RETRIEVER == "colbert"` in the new problem variant's config.
   - Confirm `num_parents: 1`, `max_elites_per_generation: 8` in all `--cfg job` outputs.
   - Confirm `program_loader.problem_dir` is NOT present in `--cfg job` output for any run.
   - Confirm `pipeline=hotpotqa_colbert` (never `hotpotqa_asi` or `standard`) in all `--cfg job` outputs.

---

*Ready for Reviewer-2's scrutiny.*
