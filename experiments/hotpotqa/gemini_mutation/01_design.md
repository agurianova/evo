# Experimental Design: Gemini-3-Flash as Mutation LLM

**Date**: 2026-03-12
**Researcher**: mathemage
**Agent**: Dr. Elena Voss (ml-research-methodologist)
**Status**: Draft

---

## 1. Research Question

Does replacing the locally-hosted mutation LLM (Qwen3-235B-A22B-Thinking) with a frontier
API model (google/gemini-3-flash-preview via OpenRouter) improve test EM on HotpotQA, when
all other variables are held fixed to the colbert_feedback experiment configuration (ColBERT
retriever, rich failure feedback, F1 fitness, 600-sample validation, cold start, 25
generations)?

The mutation LLM is the model that reads failure analyses and proposes modified chain prompts
between generations. It is the "creative engine" of the evolutionary loop. The chain execution
LLM (Qwen3-8B, thinking mode, local vLLM) is NOT changed -- it runs the 6-step QA chain
during validation and remains identical across all conditions.

This experiment isolates a single component substitution: the intelligence and capability of
the model that drives mutation. If a more capable mutation LLM produces better-evolved
programs, this establishes that the current stagnation ceiling (cold-start mean 59.58%, 16+
consecutive runs) is at least partly attributable to the mutation operator's reasoning
capacity, not solely to the fitness landscape topology. If the result is null, the stagnation
is confirmed as a landscape or framework limitation that better mutation models cannot
circumvent.

---

## 2. Hypotheses

### Framing: exploratory experiment (n=2)

With n=2 runs, formal one-sample t-tests are effectively unusable: df=1 requires t > 6.314
for one-sided p < 0.05, which demands an effect size exceeding 4.5 x SD -- practically
unachievable. This experiment is therefore **pre-registered as exploratory**. The verdicts
below are descriptive thresholds applied to the observed mean, not inferential conclusions.
Any non-null signal requires follow-up replication at n >= 4 before being treated as a
confirmed finding.

### Descriptive hypothesis: Gemini mutation improves evolutionary outcomes

**H0(descriptive)**: The mean test EM across n=2 Gemini-mutation runs falls within the
established cold-start reference distribution (mean 59.58%, SD 1.00pp, n=4, PR #75 using
Qwen3-235B mutation), indicating that replacing the mutation LLM with a frontier model confers
no detectable advantage at this sample size.

**H1(descriptive)**: The mean test EM across n=2 Gemini-mutation runs exceeds the cold-start
reference upper bound (reference mean + 2 x reference SD = 61.58%), suggesting that a more
capable mutation LLM produces higher-quality evolved programs. The mechanistic rationale:
Gemini-3-Flash (a frontier-class model, March 2026) may generate more diverse, more
contextually appropriate, and more precisely targeted prompt mutations than Qwen3-235B,
because (a) it has stronger instruction-following and code-generation capabilities, (b) it
may better understand the multi-hop reasoning structure of HotpotQA failure cases, and (c) its
higher-quality text generation may produce chain prompts that more effectively steer Qwen3-8B's
thinking-mode reasoning.

### Effect size thresholds (applied to the n=2 Gemini-mutation mean)

The primary comparison is Gemini-mutation mean test EM vs. colbert_feedback mean test EM
(if available) or vs. the cold_start BM25 reference (mean 59.58%, SD=1.00pp, n=4, PR #75).
The thresholds below are anchored to the reference mean ("ref"):

| Gemini mean test EM | Verdict |
|:-------------------:|---------|
| >= ref + 4pp | **STRONG SIGNAL** -- both runs substantially outperform reference; mutation LLM quality is likely a binding constraint; priority replication at n=4 |
| [ref + 2pp, ref + 4pp) | **POSITIVE SIGNAL** -- mean shows a meaningful advantage; suggestive that frontier mutation LLM breaks the stagnation ceiling; requires n=4 replication |
| [ref - 2pp, ref + 2pp) | **INCONCLUSIVE** -- mean within the expected inter-run noise band (+/- 2SD at SD=1pp); no signal detected at n=2 |
| [ref - 4pp, ref - 2pp) | **NEGATIVE SIGNAL** -- Gemini-mutation underperforms; possible prompt style mismatch or format incompatibility |
| < ref - 4pp | **STRONG NEGATIVE** -- frontier mutation LLM substantially worse; API model unsuitable for GigaEvo mutation |

The +/-2pp noise band is calibrated from cold_start SD=1.00pp (2 SD covers ~95% of single-run
deviations from the true mean under normality). The +/-4pp threshold reflects a practically
meaningful effect -- approximately 12 additional correct answers on the 300-sample test set.

**Why not formal NHST**: With n=2 and df=1, the critical t-value for one-sided alpha=0.05 is
6.314. Even a 4pp effect at SD=1pp yields t = 4pp / (1pp / sqrt(2)) = 5.66 < 6.314. Formal
significance testing at n=2 is essentially impossible except for implausibly large effects.
Reporting means and ranges is the honest approach.

### Comparison to colbert_feedback reference (conditional)

If the colbert_feedback experiment (PR #76, currently running, n=3 with Qwen3-235B mutation)
completes before this experiment's Phase 5 analysis, its mean test EM becomes the **primary**
comparison reference, since it uses the identical problem variant, pipeline, and all controlled
variables except the mutation LLM. The cold-start BM25 reference (PR #75, mean 59.58%,
SD=1.00pp) remains the **secondary** reference for cross-experiment context.

**Pre-registered conditional reference selection**:

| Condition | Primary reference | Secondary reference |
|-----------|------------------|---------------------|
| colbert_feedback complete, n >= 2 valid runs | colbert_feedback mean (Qwen3-235B + ColBERT) | cold_start mean (59.58%, Qwen3-235B + BM25) |
| colbert_feedback incomplete or all runs invalid | cold_start mean (59.58%) | N/A |

The Phase 5 analysis will report both comparisons when possible: (a) Gemini vs.
colbert_feedback (same problem variant, isolates mutation LLM effect), and (b) Gemini vs.
cold_start (cross-variant, provides absolute performance context).

**Pre-registered decision rule for discordant verdicts (M2)**: When the two references yield
different verdicts (e.g., POSITIVE SIGNAL vs. cold_start but INCONCLUSIVE vs. colbert_feedback),
the **primary reference governs the main verdict and escalation decision**. The secondary
reference is reported for context only. Discordant verdicts themselves are a finding and will
be discussed in Phase 5.

**Pre-registered inter-run spread guard (M3)**: If |V1 - V2| > 4pp, the maximum attainable
verdict is capped at **INCONCLUSIVE** regardless of the mean — a spread this large indicates
the two runs landed in different basins, and the mean is not a reliable summary of the
treatment effect. n=4 replication is still recommended to characterise the distribution.

---

## 3. Independent Variables

There is **one independent variable**: the mutation LLM.

| Variable | Control value (reference) | Treatment value |
|----------|--------------------------|-----------------|
| Mutation LLM | Qwen3-235B-A22B-Thinking (local vLLM) | google/gemini-3-flash-preview (OpenRouter) |
| LLM config override | `llm_base_url=http://<local-ip>:8777/v1` | `llm=gemini3_flash` |

All other variables are held fixed to the colbert_feedback experiment configuration:

- Problem variant: `chains/hotpotqa/static_colbert_f1_600` (ColBERT retriever + rich feedback)
- Pipeline: `hotpotqa_colbert` (ColBERTPipelineBuilder + HotpotQAColBERTFormatter)
- Prompts: `default`
- Fitness: F1
- Val N: 600
- Seed: cold start
- Chain LLM: Qwen3-8B, thinking mode
- num_parents: 1, max_elites: 8, max_mutations: 8
- 25 generations

**Why not also vary the problem variant (BM25 vs. ColBERT)?** The goal is to isolate the
mutation LLM effect under the best-available retriever condition. The colbert_feedback
experiment already tests ColBERT + Qwen3-235B. Adding a BM25 arm would create a 2x2 design
requiring n=4 additional runs -- exceeding the cost budget and deviating from the single-
substitution design. If the Gemini mutation result is non-null, a BM25 + Gemini arm is a
natural follow-up.

---

## 4. Dependent Variables

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test EM at gen 25 (best-by-val) | 300-sample held-out test set; EM scoring; thinking mode Qwen3-8B | YES -- primary |
| Val-test EM gap | Val EM (`valid_frontier_em` Redis key) minus test EM | YES -- secondary |
| Birth-generation of best-by-val | From `valid_frontier_fitness` trajectory | NO -- stagnation diagnostic |
| Gen-0 val EM | From Redis at gen 0 | NO -- cold-start initialization verification |
| Val F1 frontier trajectory (gen 1-25) | Per-generation `valid_frontier_fitness` (F1) | NO -- convergence diagnostic |
| Invalidity rate at gen 5, 10, 25 | Fraction of invalid programs per run per generation | NO -- mutation quality diagnostic |
| Mutation LLM latency per generation | Wall-clock time per mutation call (from logs) | NO -- cost/latency diagnostic |
| OpenRouter API cost (total) | From OpenRouter dashboard after runs complete | NO -- cost-effectiveness |
| API error rate | Count of 429/500/timeout errors in mutation logs | NO -- infrastructure reliability |

**Primary metric**: Test EM at final generation (gen 25), best-by-val program, evaluated on
the fixed 300-sample held-out test set, thinking mode Qwen3-8B. Consistent with all prior
experiments and the GEPA benchmark (62.3%).

**Gen-0 diagnostic**: Same as colbert_feedback: expected gen-0 val EM 0.40-0.55. Halt if
gen-0 val EM > 0.65 (implies evolved program used as cold start).

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Chain topology | 6-step fixed (2 tool, 4 LLM) | Unchanged across all experiments; static mode |
| Fitness metric | F1 (token-level partial credit) | Consistent with colbert_feedback and cold_start |
| Validation sample size | 600 (fixed, first 600 train samples) | Consistent with colbert_feedback |
| Val set protocol | Fixed sequential (first 600 train samples) | No rotation; rotation permanently excluded |
| `prompts` | `default` | Consistent with colbert_feedback reference |
| `pipeline` | `hotpotqa_colbert` | Required for `static_colbert_f1_600`; uses ColBERTPipelineBuilder and HotpotQAColBERTFormatter |
| `problem.name` | `chains/hotpotqa/static_colbert_f1_600` | Identical to colbert_feedback |
| Seed initialization | **Cold** -- no `program_loader.problem_dir` | Identical to colbert_feedback |
| Chain LLM | Qwen3-8B, thinking mode ON (default chat template) | Required for GEPA comparison; NOT changed |
| `num_parents` | **1** (explicit override; default = 2) | Single-parent mutation; consistent with colbert_feedback |
| `max_elites_per_generation` | **8** (explicit override; default = 5) | Consistent with all prior HotpotQA experiments |
| `max_mutations_per_generation` | **8** | C(8,1)=8, capped at 8 -> 8 mutations/gen |
| `mutation_mode` | `rewrite` | Default; compatible with num_parents=1 |
| `parent_selector` | `AllCombinationsParentSelector` | Standard selector |
| `stage_timeout` | 6000 | 600-sample eval empirical max ~2300s; 6000 provides 2.6x margin |
| `dag_timeout` | 9000 | stage_timeout (6000) + mutation LLM stages (~1500) + headroom (1500) |
| `max_generations` | 25 | Consistent with colbert_feedback and cold_start |
| `step_max_tokens` | 8192 for all LLM steps | Uniform; thinking mode exhausts budget |
| Test evaluation | Fixed 300-sample test set; thinking mode verified | Consistent with all prior runs |
| Random failure sampling | All failures returned from validate.py; formatter samples 10 with NO_CACHE | Required; cf0cfc1 |
| HTTP timeout | 600s (`httpx.Timeout(timeout=600.0)`) | Required for 600-sample runs; fixed at c0186a8 |

**[Critical: Chain LLM is NOT the mutation LLM]**: The chain execution LLM (Qwen3-8B, local
vLLM) is completely separate from the mutation LLM (the model being varied). The chain LLM
runs the 6-step QA chain during validation -- it is the "test-taker." The mutation LLM is
the "coach" that reads failure analyses and proposes improvements to the chain's prompts.
Changing only the mutation LLM tests whether a better coach improves the test-taker's
performance, without changing the test-taker itself.

**[Critical: `pipeline=hotpotqa_colbert` required]**: Same as colbert_feedback. Using
`pipeline=hotpotqa_asi` would silently downgrade feedback to title-only format. Run
invalidation criterion 2 covers this.

**[Critical: `num_parents=1` and `max_elites_per_generation=8`]**: Both require explicit
Hydra overrides. Mandatory `--cfg job` pre-launch check.

**[Critical: `llm=gemini3_flash` override]**: The Gemini mutation LLM is configured via the
Hydra override `llm=gemini3_flash`, which loads `config/llm/gemini3_flash.yaml`. This config
routes all mutation/insights/lineage LLM calls to OpenRouter's `google/gemini-3-flash-preview`
endpoint. The `OPENAI_API_KEY` environment variable must be set to the OpenRouter API key
(not a local vLLM key). Verify via `--cfg job` that `llm.models[0].model` is
`google/gemini-3-flash-preview` and `base_url` is `https://openrouter.ai/api/v1`.

---

## 6. Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | `llm` config | Seed | `num_parents` | `max_elites` | `max_mut` | `stage_timeout` | `dag_timeout` | `max_gen` | Val N | Fitness |
|-----|-------|-----------|-----------|-----------|----------------|-------------|------|:-------------:|:------------:|:---------:|:--------------:|:------------:|:--------:|:-----:|:-------:|
| V1 | gemini-1 | 3 | `hotpotqa_colbert` | `default` | `chains/hotpotqa/static_colbert_f1_600` | `gemini3_flash` | Cold | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |
| V2 | gemini-2 | 4 | `hotpotqa_colbert` | `default` | `chains/hotpotqa/static_colbert_f1_600` | `gemini3_flash` | Cold | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |

**Bold values require explicit Hydra overrides**: `num_parents=1` (default is 2);
`max_elites_per_generation=8` (default is 5).

**Redis DBs**: 3 and 4. colbert_feedback uses DBs 0, 1, 2 (U1, U3, U4). DBs 3 and 4 are
unoccupied. Verify 0 keys before launch.

**Combinatorics verification**:

| Run | num_parents | max_elites | Parent combos | max_mutations | Actual mut/gen (mature archive) |
|-----|:-----------:|:---------:|:-------------:|:-------------:|:-------------------------------:|
| V1 | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| V2 | 1 | 8 | C(8,1) = 8 | 8 | 8 |

**Chain LLM assignment** (one chain server per run, no sharing):

| Run | Chain LLM URL |
|-----|---------------|
| V1 | `http://10.226.17.25:8000/v1` |
| V2 | `http://10.225.185.235:8000/v1` |

Note: 10.226.17.25:8000 was freed by colbert_feedback Amendment 4 (U2 dropped). If V2's
chain server (10.225.185.235:8000) is still used by colbert_feedback U4 at launch time,
either (a) wait for colbert_feedback to complete, (b) assign V2 to a different chain
endpoint, or (c) accept shared chain server usage (vLLM handles concurrent requests).
Chain server sharing is not ideal but is not experiment-invalidating -- it adds latency noise
but does not affect the mutation LLM IV.

**Mutation LLM assignment** (both runs use the same stateless API endpoint):

| Run | Mutation LLM | Endpoint |
|-----|-------------|----------|
| V1 | google/gemini-3-flash-preview | `https://openrouter.ai/api/v1` |
| V2 | google/gemini-3-flash-preview | `https://openrouter.ai/api/v1` |

Both runs share the same OpenRouter API. The API is stateless and horizontally scaled by
Google. No per-run server assignment is needed. Rate limiting is handled by OpenRouter; at
8 mutations/gen with ~5-15s per call, the two runs will generate at most ~16 concurrent
requests per generation cycle, well within standard API rate limits.

**Reference runs** (historical, not re-run):

| Source | Mutation LLM | Retriever | Feedback | n | Mean test EM | SD |
|--------|-------------|-----------|----------|---|:----------:|:---:|
| cold_start (PR #75) | Qwen3-235B | BM25 | Title only | 4 | 59.58% | 1.00pp |
| colbert_feedback (PR #76) | Qwen3-235B | ColBERT | Full passage | 3 | TBD | TBD |

---

## 7. Sample Size Justification

**N=2 independent replications.** This is an exploratory screening experiment constrained by
API cost and by the novelty of the research question (no prior evidence for the effect
direction or magnitude).

### Cost estimate

Gemini-3-Flash via OpenRouter: $0.50/M input, $3.00/M output.

Each mutation call: ~3,000 input tokens + ~500 output tokens (estimated from colbert_feedback
mutation log token counts). GigaEvo also makes insights and lineage LLM calls; conservatively
estimate ~250 total LLM calls per run (200 mutation + 50 auxiliary).

| Item | Per run | 2 runs |
|------|---------|--------|
| Mutation calls | ~200 | ~400 |
| Aux calls (insights, lineage) | ~50 | ~100 |
| Input tokens (total) | ~0.75M | ~1.5M |
| Output tokens (total) | ~0.25M | ~0.5M |
| Input cost ($0.50/M) | ~$0.38 | ~$0.75 |
| Output cost ($3.00/M) | ~$0.75 | ~$1.50 |
| **Total** | **~$1.13** | **~$2.25** |

Total estimated cost: **~$2-6** (depending on actual output token length; Gemini may produce
longer mutations than Qwen3-235B). This is manageable for an exploratory probe.

### What N=2 enables and does not enable

**Enables**:

1. **Descriptive mean and range**: The mean of 2 runs and the spread |V1 - V2| provide a
   rough estimate of the treatment effect and its variability.

2. **Signal detection via directional consistency**: If both runs independently exceed the
   reference upper bound (ref + 2SD), this constitutes directional evidence that is unlikely
   under H0 (probability ~2.3% under normal approximation). Not a formal test but a coherence
   check.

3. **Cost-effectiveness screening**: If both runs score below ref - 2SD, the experiment
   provides strong evidence against investing $12+ in a full N=4 replication.

4. **Qualitative comparison**: Examination of evolved programs, invalidity rates, and
   convergence trajectories between Gemini-mutation and Qwen3-235B-mutation runs.

**Does NOT enable**:

- Formal one-sample t-test (df=1, critical t = 6.314 for p < 0.05)
- Reliable SD estimate (chi-squared df=1 has extreme sampling variance)
- Meaningful confidence intervals (t-based CI at df=1 spans +/- 12.706 x SE)

### Why not N=1

A single run cannot distinguish a Gemini effect from stochastic run-to-run variation. With
GigaEvo inter-run SD of ~1pp (cold_start), a single datapoint is uninterpretable. N=2 at
least provides a range and directional consistency check.

### Pre-registered escalation path

If the gemini_mean >= ref + 2pp (POSITIVE SIGNAL or STRONG SIGNAL), a follow-up N=4
replication is recommended to achieve formal inferential power (t-test at alpha=0.05, df=3,
MDE ~1.67pp at SD=1pp).

---

## 8. Statistical Tests

### Test 1: Descriptive comparison -- Gemini mean vs. reference thresholds (primary)

**Comparison**: Mean test EM across V1-V2 vs. pre-registered thresholds from Section 2.

**Procedure**: Compute gemini_mean = (V1 + V2) / 2. Compute delta = gemini_mean - ref. Apply
the verdict table.

**Reported quantities**:
1. Individual test EM for V1 and V2 (with binomial 95% CI each).
2. Mean test EM (gemini_mean).
3. Range |V1 - V2|.
4. Delta from primary reference (colbert_feedback mean, if available).
5. Delta from secondary reference (cold_start mean = 59.58%).
6. Whether both V1 and V2 fall above, below, or straddle the reference mean.

No p-value is computed. The verdict is descriptive, not inferential.

### Test 2: Individual run comparison to GEPA (descriptive)

For each run, report whether test EM >= 62.3% (GEPA). With n=2:

| Runs >= GEPA | Interpretation |
|:------------:|----------------|
| 2/2 | Strong directional evidence; Gemini mutation reaches GEPA reliably |
| 1/2 | Ambiguous; landscape variance or run-level noise |
| 0/2 | No evidence of GEPA-level performance |

### Test 3: Head-to-head with colbert_feedback (conditional, descriptive)

If colbert_feedback (PR #76, Qwen3-235B mutation) completes with n >= 2 valid runs, report:

- gemini_mean vs. colbert_mean (point difference, which directly isolates the mutation LLM)
- Overlap of individual run ranges: do all Gemini runs exceed all colbert_feedback runs?
  (If yes, directional evidence is strong despite n=2.)

This is the most informative comparison because it holds the problem variant fixed and isolates
the mutation LLM variable.

### Test 4: Stagnation birth-generation (exploratory)

Mean birth-generation of best-by-val program across V1-V2. Compare to cold-start Qwen3-235B
reference (mean 16.5, range 11-19, n=4, PR #75).

| Mean birth-gen | Interpretation |
|:--------------:|----------------|
| < 10 | **FASTER CONVERGENCE** -- frontier mutation LLM finds good programs sooner |
| 10-20 | **CONSISTENT WITH COLD-START PATTERN** -- stagnation timing unchanged |
| > 20 | **EXTENDED EXPLORATION** -- frontier LLM explores longer before converging |

### Binomial confidence intervals (individual runs)

```
CI = test_EM +/- 1.96 x sqrt(p x (1-p) / 300)
```

Reported for each run in Phase 5.

---

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| **Mutation LLM prompt format mismatch** | GigaEvo's default mutation prompts were designed and iterated with Qwen3-235B. Gemini-3-Flash may respond with different output formats (code fences, preamble text, thinking traces) that confuse the mutation parser, inflating invalidity rate. | Phase 3: Run a manual single-mutation test through Gemini before launch. If the parser rejects the output, add format instructions (amendment) or report NEGATIVE verdict. |
| **OpenRouter latency and rate limits** | OpenRouter adds network latency and may rate-limit concurrent requests. If rate-limited, mutations queue and wall-clock time increases. | Pre-launch: burst-test 16 concurrent requests. If median latency > 30s or 429 errors occur, stagger launches. Monitor per-mutation latency at gen 0-1. |
| **API model version drift** | OpenRouter's `google/gemini-3-flash-preview` may be updated mid-run. Unlike locally hosted Qwen3-235B (fixed checkpoint), the API model could change behavior. | V1 and V2 launch simultaneously. Record model snapshot ID from response headers at gen 0 and gen 25. If IDs differ and behavior changes are suspected, note as amendment. |
| **Temperature / sampling parity** | `gemini3_flash.yaml` uses `${temperature}` and `${max_tokens}` from Hydra defaults. These values are passed identically, but Gemini may interpret temperature differently than Qwen3-235B (different effective randomness). | Accept as residual confound -- this is part of the "full mutation-LLM package" being tested. Verify via `--cfg job` that temperature and max_tokens values match the colbert_feedback config. |
| **Thinking mode in mutation LLM** | Qwen3-235B uses thinking traces (`<think>` blocks). Gemini-3-Flash may or may not use extended thinking. If GigaEvo's mutation parsing depends on `<think>` blocks from the mutation LLM (distinct from the chain LLM's thinking), Gemini output may be misparsed. | Phase 3: Verify mutation parsing does not depend on `<think>` blocks from the mutation LLM. The mutation output is parsed as a program/prompt string, not a chain execution output. |
| **OpenRouter content filtering** | Gemini may refuse certain mutation requests if failure feedback triggers safety filters. | Monitor refusal rate. If > 5% of mutations are refused, file amendment. HotpotQA content is factual/encyclopedic -- low risk. |
| **Chain LLM server contention** | If colbert_feedback is still running, some chain servers may be shared. | Assign chain servers not used by active colbert_feedback runs. 10.226.17.25:8000 freed by U2 drop. Delay launch if no server is available. |
| **ColBERT server load** | 5 concurrent runs (3 colbert_feedback + 2 gemini_mutation) may overload the 8-GPU ColBERT server. | 8-GPU server handles ~80 concurrent queries. 5 runs x 4 workers x ~2 retrievals = ~40 concurrent queries at peak. Within capacity. Monitor at gen 0-1. |
| **`num_parents` default = 2** | Omission converts runs to crossover. | Mandatory `--cfg job` pre-launch check. |
| **`max_elites_per_generation` default = 5** | Omission reduces mutations/gen from 8 to 5. | Mandatory `--cfg job` pre-launch check. |
| **`pipeline=hotpotqa_colbert` required** | Using `hotpotqa_asi` silently downgrades feedback. | Mandatory `--cfg job` pre-launch check. |
| **Cost overrun** | If Gemini outputs are unexpectedly long (> 5K tokens/call), per-run cost could exceed $10. | Monitor OpenRouter dashboard after V1 gen 5. If cumulative cost exceeds $3 by gen 5, file amendment to reduce max_tokens. |
| **API key exposure** | `OPENAI_API_KEY` contains the OpenRouter key. | Set via shell env var, not config file. Verify key does not appear in `--cfg job` output. Do not commit to git. |

---

## 10. Stop Criteria

### Stagnation-based early completion

Same as colbert_feedback: if `valid_frontier_fitness` (F1) shows no improvement for >= 10
consecutive generations AND the current generation >= 15, the run may be terminated early.

### Early termination criteria

- **API authentication failure at gen 0**: Halt immediately. Verify OPENAI_API_KEY and
  OpenRouter endpoint accessibility. Do not proceed until a test mutation call succeeds.
- **Sustained API errors (> 50% of mutation calls fail in any 3 consecutive generations)**:
  Halt the affected run. File amendment. Resume after API recovery.
- **Invalidity rate > 50% at gen 5 for any run**: Pause; diagnose whether Gemini's output
  format is incompatible with GigaEvo's program parser. If systematic, amend or abandon with
  NEGATIVE verdict.
- **Gen-0 val EM = 0.0 for any run**: Halt; diagnose before proceeding.
- **Gen-0 val EM > 0.65 for any run**: Halt -- likely warm-start misconfiguration.
- **Cumulative OpenRouter cost exceeds $8 per run by gen 10**: File amendment to reduce
  max_tokens or terminate.
- **ColBERT server crash**: Halt runs; restart server; resume (amendment not required for
  outages < 30 min).

### Run invalidation criteria

A run is excluded from all analyses if any of the following apply:

1. Thinking mode not active on chain LLM: `<think>` blocks absent from >= 5% of chain
   outputs at gen 1.
2. `pipeline` != `hotpotqa_colbert` confirmed in post-hoc log inspection.
3. `llm` != `gemini3_flash` confirmed in post-hoc log inspection (wrong mutation LLM used).
4. Invalidity rate > 90% at gen 10 (Gemini output systematically unparseable).
5. Gen-0 val EM > 0.65 (warm-start initialization detected).
6. `num_parents` confirmed at 2 (not 1) or `max_elites_per_generation` confirmed at 5
   (not 8) in post-hoc log inspection.
7. ColBERT retrieval confirmed non-functional (empty passages returned) at any generation.
8. OpenRouter API calls failed for > 50% of all mutation attempts across the entire run
   (sustained systematic failure, not per-generation).

If one run is invalidated, the remaining single run is reported descriptively with the
maximum attainable verdict capped at **INCONCLUSIVE** regardless of the remaining run's
test EM.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time per run (600-sample, 25 gens) | ~10-20h (chain eval ~24 min/gen; Gemini mutation latency may add 1-5 min/gen vs. local Qwen3-235B) |
| Total wall time (2 runs parallel) | ~20h wall-clock |
| Redis DBs | 2 (DBs 3 and 4) |
| Chain LLM servers | 2 x Qwen3-8B thinking (one per run) |
| Mutation LLM | google/gemini-3-flash-preview via OpenRouter (both runs, stateless API) |
| Mutation LLM servers (local) | 0 -- all mutation via API |
| ColBERT server | 1 (shared; port 8889, 8-GPU; same as colbert_feedback) |
| OpenRouter API cost | ~$2-6 total (see Section 7) |
| Test evaluation | ~5 min each x 2 runs = ~10 min total |
| New code required | None -- `config/llm/gemini3_flash.yaml` already exists; `static_colbert_f1_600` problem variant already implemented for colbert_feedback |

---

## 12. Open Questions / Risks

### Risk 1 -- Gemini mutation output format compatibility (CRITICAL)

GigaEvo's mutation parsing expects the mutation LLM to output a modified Python function.
The prompts were developed and tested exclusively with Qwen3-235B. Gemini-3-Flash may:
- Wrap code in different markdown fences or use different delimiters.
- Include preamble explanations that confuse the parser.
- Use different Python idioms that are valid but structurally unexpected.
- Produce `<think>`-like reasoning blocks that interfere with extraction.

**Pre-launch gate**: One successful end-to-end mutation (GigaEvo mutation prompt -> Gemini ->
parsed program) must be confirmed before launch. If the parser rejects the output, diagnose
and either adapt the parser (amendment required) or report NEGATIVE verdict and abort.

### Risk 2 -- OpenRouter reliability over 20+ hours (HIGH)

A 20-hour experiment requires sustained API availability. Transient failures (1-2 per gen)
are expected and tolerable -- they reduce mutations/gen by 1-2 but do not invalidate the run.
Sustained outages (> 3 consecutive gens with > 50% failure) trigger the early termination
criterion.

### Risk 3 -- Mutation quality vs. mutation format confound (MEDIUM)

A positive result could reflect either genuinely better mutations or a stylistic difference
(e.g., Gemini produces more verbose prompts that happen to work with Qwen3-8B). A null result
could reflect true equivalence or format mismatch masking superior reasoning. This confound
is inherent to the single-substitution design and is partially addressed by examining
invalidity rates (format issue) vs. converged-but-flat trajectories (quality issue).

### Risk 4 -- dag_timeout may need increase (MEDIUM)

The dag_timeout of 9000s assumes mutation LLM responds within ~1500s. Gemini via OpenRouter
may have different per-call latency. If 8 mutations x 120s/call = 960s mutation time + 6000s
eval = 6960s, still within 9000s. If latency exceeds 120s/call consistently, file amendment
to increase dag_timeout to 12000s.

### Risk 5 -- Proxy/network configuration (LOW)

OpenRouter requests go through public internet. Verify `curl https://openrouter.ai/api/v1/models`
works from the experiment host. The `NO_PROXY` setting lists only internal IPs and should not
interfere with external HTTPS requests.

### Scientific open questions after this experiment

- **If POSITIVE SIGNAL or STRONG SIGNAL**: The mutation LLM is a binding constraint on
  GigaEvo performance. Priority follow-ups: (a) N=4 replication to confirm effect, (b) test
  other frontier models (Claude, GPT-4o) to determine if the improvement is Gemini-specific
  or general, (c) compare mutation diversity (edit distance between parent and child programs)
  between Gemini and Qwen3-235B to identify the mechanism.

- **If INCONCLUSIVE (NULL)**: The stagnation ceiling is not attributable to the mutation LLM's
  reasoning capacity. The bottleneck is either (a) the fitness landscape topology, (b) the
  feedback mechanism, or (c) the MAP-Elites archive convergence dynamics. Next direction:
  structural chain changes (topology mutation, new steps) or fundamentally different search
  mechanisms.

- **If NEGATIVE SIGNAL**: Gemini mutations are worse for this task. Investigate: (a) invalidity
  rates (format mismatch), (b) mutation output style (verbose vs. concise), (c) whether
  GigaEvo prompts need model-specific adaptation. A NEGATIVE result with low invalidity is
  more informative than one with high invalidity (the former suggests genuine quality
  difference; the latter suggests engineering issue).

---

## Appendix A: Phase 3 Pre-Launch Checklist

Minimal code changes are required -- the `gemini3_flash.yaml` config and `static_colbert_f1_600`
problem variant already exist.

1. **Verify `llm=gemini3_flash` config loads**:
   ```bash
   PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
       problem.name=chains/hotpotqa/static_colbert_f1_600 \
       pipeline=hotpotqa_colbert \
       llm=gemini3_flash \
       redis.db=3 \
       num_parents=1 \
       max_elites_per_generation=8 \
       max_mutations_per_generation=8 \
       max_generations=25 \
       stage_timeout=6000 \
       dag_timeout=9000 \
       --cfg job
   ```
   Confirm output shows `model: google/gemini-3-flash-preview`, `base_url: https://openrouter.ai/api/v1`,
   `num_parents: 1`, `max_elites_per_generation: 8`, `pipeline: hotpotqa_colbert`.

2. **Confirm `_target_`**: `--cfg job` must show
   `_target_: problems.chains.hotpotqa.static_colbert_f1_600.pipeline.ColBERTPipelineBuilder`.

3. **Confirm `prompts_dir`**: Must appear in both `evolution_context` and `mutation_operator`
   blocks of `--cfg job` output.

4. **Manual mutation test**: Invoke one mutation call through Gemini via OpenRouter with the
   actual GigaEvo mutation prompt. Verify output is parseable.

5. **OpenRouter connectivity**: `curl https://openrouter.ai/api/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`
   returns valid JSON.

6. **max_tokens verification (M1)**: `gemini3_flash.yaml` passes `max_tokens: ${max_tokens}`
   (default 81920). Gemini-3-Flash-Preview is a thinking model supporting up to 64K+ output tokens.
   Pre-launch: confirm the first mutation call completes without an API error referencing output
   limit. If the API rejects 81920, add an explicit `max_tokens: 32768` override and file an
   amendment.

7. **Redis DBs 3 and 4 empty**: Verify 0 keys.

8. **Chain LLM availability**: Confirm at least 2 chain endpoints are free.

9. **ColBERT server running**: Verify port 8889 responsive.

10. **API key safety**: Confirm `OPENAI_API_KEY` does not appear in `--cfg job` output.

11. **Implement/adapt `run_test_eval.sh`**: Must use `static_colbert_f1_600` with
    `llm=gemini3_flash` (or verify test eval does not invoke the mutation LLM -- if test eval
    only runs the chain, the mutation LLM config is irrelevant at test time).

12. **Watchdog**: Adapt from colbert_feedback. Should additionally monitor OpenRouter API
    health (mutation call success rate).

---

## Appendix B: Decision Tree

```
After gen-25 test evals for both runs (V1, V2):

  Compute: gemini_mean = (V1 + V2) / 2
           gemini_range = |V1 - V2|

  Obtain reference:
    IF colbert_feedback complete with n >= 2: ref = colbert_feedback mean
    ELSE: ref = 59.58% (cold_start, PR #75)

                  gemini_mean >= ref + 4pp?
                 /                         \
               YES                          NO
                |                            |
          STRONG SIGNAL                gemini_mean >= ref + 2pp?
          (n=4 replication)               /                \
                                        YES                NO
                                         |                  |
                                   POSITIVE SIGNAL    gemini_mean >= ref - 2pp?
                                   (n=4 replication)     /                \
                                                       YES                NO
                                                        |                  |
                                                  INCONCLUSIVE       gemini_mean >= ref - 4pp?
                                                  (no follow-up)       /                \
                                                                     YES                NO
                                                                      |                  |
                                                                NEGATIVE SIGNAL    STRONG NEGATIVE
                                                                (investigate       (API model
                                                                 mismatch)         unsuitable)

  Also report:
    - Test 2: Individual runs vs GEPA (62.3%)
    - Test 3: Head-to-head vs colbert_feedback (if available)
    - Test 4: Birth-gen (stagnation diagnostic)
    - Invalidity rates, mutation latency, API cost
```

---

*Ready for Reviewer-2's scrutiny.*
