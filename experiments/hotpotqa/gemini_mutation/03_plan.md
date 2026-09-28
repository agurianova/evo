# Pre-Registration: Gemini-3-Flash as Mutation LLM (gemini_mutation)

**Date**: 2026-03-12
**Protocol version**: 1.0
**Pre-registration commit**: _TBD — commit hash added after push_
**GitHub PR**: _TBD_
**Design doc**: `experiments/hotpotqa/gemini_mutation/01_design.md`
**Review doc**: `experiments/hotpotqa/gemini_mutation/02_review.md` (verdict: APPROVED)
**Evaluation script**: `experiments/hotpotqa/gemini_mutation/run_test_eval.sh`

---

## Hypothesis

**H0 (descriptive)**: The mean test EM across n=2 Gemini-mutation runs falls within ±2pp of
the primary reference (colbert_feedback mean, or cold_start 59.58%), indicating no detectable
advantage from substituting the mutation LLM.

**H1 (descriptive)**: The mean test EM across n=2 Gemini-mutation runs exceeds the primary
reference by ≥2pp, suggesting that a more capable frontier mutation LLM produces better-evolved
programs.

**Primary metric**: Test EM at gen 25 (best-by-val program), 300-sample held-out test set,
thinking mode Qwen3-8B. Consistent with all prior experiments and GEPA benchmark (62.3%).

**Framing**: Exploratory (n=2). No formal NHST. Verdicts are descriptive thresholds.

**Effect size thresholds** (applied to gemini_mean = (V1+V2)/2 vs. ref):

| gemini_mean vs. ref | Verdict |
|:-------------------:|---------|
| ≥ ref + 4pp | **STRONG SIGNAL** — priority n=4 replication |
| [ref+2pp, ref+4pp) | **POSITIVE SIGNAL** — suggestive; n=4 replication recommended |
| [ref−2pp, ref+2pp) | **INCONCLUSIVE** — within noise band |
| [ref−4pp, ref−2pp) | **NEGATIVE SIGNAL** — investigate format/quality mismatch |
| < ref−4pp | **STRONG NEGATIVE** — API model unsuitable |

**Spread guard (M3)**: If |V1 − V2| > 4pp, verdict capped at **INCONCLUSIVE** regardless
of mean; n=4 replication still recommended.

**Discordant reference rule (M2)**: Primary reference governs main verdict and escalation.
Secondary reference reported for context only.

**Reference selection** (updated by Amendment 3):

**Primary reference: cold_start mean 59.58% (PR #75, n=4, SD=1.00pp, BM25+F1+600, Qwen3-235B mutation).**
Run D (63.00%) is demoted to secondary aspirational benchmark — it is n=1 and non-replicating
(Run P, same config cold-start, achieved only 57.33%; observed spread 5.67pp).
Anchoring the primary verdict to an unreliable n=1 outlier would be indefensible.

| Condition | Primary ref | Secondary ref |
|-----------|------------|---------------|
| Always | cold_start 59.58% (n=4, SD=1.00pp) | Run D 63.00% (n=1, non-replicating, aspirational) |

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | `llm` | `llm_base_url` (chain) | Seed | Val N |
|-----|-------|-----------|-----------|-----------|----------------|-------|------------------------|------|-------|
| V1 | gemini-1 | 3 | `hotpotqa_asi` | `hotpotqa` | `chains/hotpotqa/static_f1_600` | `gemini3_flash` | `http://10.226.17.25:8000/v1` | ddce37b4 warm | 600 |
| V2 | gemini-2 | 4 | `hotpotqa_asi` | `hotpotqa` | `chains/hotpotqa/static_f1_600` | `gemini3_flash` | `http://10.225.185.235:8000/v1` | ddce37b4 warm | 600 |

**Mutation LLM** (both runs): `google/gemini-3-flash-preview` via OpenRouter
(`https://openrouter.ai/api/v1`). Requires `OPENAI_API_KEY` env var = OpenRouter key.

**Warm-start seed**: `experiments/hotpotqa/thinking/seeds/ddce37b4` — identical to Run D (push, PR #73).

---

## Launch Commands

```bash
SEED_DIR=experiments/hotpotqa/thinking/seeds/ddce37b4

# Config review (run before each launch)
PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    llm=gemini3_flash \
    program_loader.problem_dir="$SEED_DIR" \
    redis.db=3 \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    max_generations=25 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    --cfg job

# V1 — DB=3, chain=10.226.17.25:8000
HOTPOTQA_CHAIN_URL=http://10.226.17.25:8000/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    llm=gemini3_flash \
    program_loader.problem_dir="$SEED_DIR" \
    redis.db=3 \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    max_generations=25 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    > experiments/hotpotqa/gemini_mutation/run_V1.log 2>&1 &

# V2 — DB=4, chain=10.225.185.235:8000
HOTPOTQA_CHAIN_URL=http://10.225.185.235:8000/v1 \
nohup /home/jovyan/envs/evo_fast/bin/python run.py \
    problem.name=chains/hotpotqa/static_f1_600 \
    pipeline=hotpotqa_asi \
    prompts=hotpotqa \
    llm=gemini3_flash \
    program_loader.problem_dir="$SEED_DIR" \
    redis.db=4 \
    num_parents=1 \
    max_elites_per_generation=8 \
    max_mutations_per_generation=8 \
    max_generations=25 \
    stage_timeout=6000 \
    dag_timeout=9000 \
    > experiments/hotpotqa/gemini_mutation/run_V2.log 2>&1 &
```

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
| Mutation LLM | google/gemini-3-flash-preview (OpenRouter) |
| Fitness metric | F1 (token-level partial credit) |
| Validation sample size | 600 (first 600 train samples) |
| Seed initialization | Warm — ddce37b4 (`experiments/hotpotqa/thinking/seeds/ddce37b4`) |
| `prompts` | `hotpotqa` (NLP prompts) |
| Retriever | BM25s (`static_f1_600`) |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature in chain LLM and mutation LLM
- API model non-determinism (OpenRouter Gemini)

Cross-experiment comparisons use effect-size thresholds rather than exact trajectory matching.

---

## Dataset Checksums

Same dataset as all prior HotpotQA experiments. Verified at colbert_feedback pre-registration.

---

## Pre-Launch Checklist

- [ ] `--cfg job` confirms: `model: google/gemini-3-flash-preview`, `base_url: https://openrouter.ai/api/v1`, `num_parents: 1`, `max_elites_per_generation: 8`, `pipeline: hotpotqa_asi`
- [ ] `--cfg job` confirms: `prompts_dir` in both `evolution_context` and `mutation_operator` blocks
- [ ] Redis DBs 3 and 4 empty (0 keys each)
- [ ] Chain LLM endpoints verified (thinking mode — `<think>` in response)
- [ ] OpenRouter connectivity: `curl https://openrouter.ai/api/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"` returns JSON
- [ ] max_tokens verification (M1): first mutation call succeeds without API error; if rejected, file amendment to cap at 32768
- [ ] Manual mutation test: one end-to-end mutation call parses cleanly
- [ ] `OPENAI_API_KEY` not visible in `--cfg job` output
- [ ] Gen-0 val EM: halt if < 0.0 or > 0.65

---

## Invalidation Criteria

A run is excluded if:
1. `pipeline` ≠ `hotpotqa_asi` (confirmed in log)
2. `llm` ≠ `gemini3_flash` (wrong mutation LLM used)
3. Thinking mode absent from ≥5% of chain outputs at gen 1
4. Invalidity rate > 90% at gen 10 (Gemini output systematically unparseable)
5. Gen-0 val F1 < 0.60 (seed not loaded correctly — warm-start expected ~0.70)
6. `num_parents` = 2 or `max_elites_per_generation` = 5 confirmed in log
7. OpenRouter API failed for > 50% of all mutation attempts across the run

If one run invalidated: remaining run reported with verdict capped at INCONCLUSIVE.

---

## Monitoring Plan

`max_generations`: 25

- Gen 3 (~10%): smoke check — PIDs alive, Redis keys growing, gen-0 EM within expected range, no API errors
- Gen 5: first checkpoint — extract best-by-val, confirm invalidity rate < 50%, monitor OpenRouter cost
- Gen 12 (~50%): midpoint checkpoint — record val F1/EM, compare to colbert_feedback trajectory
- Gen 25 (100%): final evaluation — run test eval, record results

Early termination: no frontier improvement for ≥10 consecutive gens AND gen ≥15.

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| V1 | 1886025 | 2026-03-12 23:06 UTC | DB=3, chain=10.226.17.25:8000, seed=ddce37b4, prompts=hotpotqa — STOPPED at gen 4 (OpenRouter credits exhausted) |
| V2 | 1886026 | 2026-03-12 23:06 UTC | DB=4, chain=10.225.185.235:8000, seed=ddce37b4, prompts=hotpotqa — STOPPED at gen 4 (OpenRouter credits exhausted) |
| V1 | 1903813 | 2026-03-13 12:25 UTC | DB=3 flushed + relaunched from gen 0 (resume not supported) |
| V2 | 1903871 | 2026-03-13 12:25 UTC | DB=4 flushed + relaunched from gen 0 (resume not supported) |

Watchdog PID: 1985306 (PR #79)
Launch commit: _TBD_

---

## Checkpoint Log

| Gen | Date (UTC) | V1 val F1 | V2 val F1 | Notes |
|-----|-----------|-----------|-----------|-------|

---

## Results Tracking

| Run | Val F1 | Val EM | Birth-gen | Test EM | Notes |
|-----|--------|--------|-----------|---------|-------|
| V1 | TBD | TBD | TBD | TBD | |
| V2 | TBD | TBD | TBD | TBD | |
| **Mean** | | | | TBD | |
| **ref (cold_start)** | | | | 59.58% | **primary** (n=4, SD=1.00pp) |
| **ref (Run D)** | | | | 63.00% | secondary aspirational (n=1, non-replicating) |
| **Verdict** | | | | TBD | vs. cold_start primary ref |

---

## Amendments

### Amendment 3: Primary reference corrected to cold_start 59.58% (2026-03-12)

**No confound** — analysis framing only; no code or config changes. Filed pre-gen-1 frontier.

**Reason**: Posthoc consultation with Dr. Elena Voss (ml-research-methodologist) and
Prof. Andrei Volkov (reviewer-2-adversary) identified that the Amendment 2 reference
selection (Run D = 63.00% as primary) is scientifically indefensible:
- Run D is n=1 with observed non-replication: Run P (same config, cold-start) achieved
  only 57.33% — a 5.67pp spread indicating the Run D result is highly variable.
- An n=1, non-replicating result has unknown variance and cannot serve as a primary
  reference for verdict determination.
- Prof. Volkov verdict: **CONCERNS-NOTED** — three simultaneous variable changes
  (retriever + seed + prompts) mean the Phase 2 approval no longer covers the live
  configuration; the minimum condition for scientific validity is using cold_start as
  primary reference.

**Changes**:
- Primary reference: Run D 63.00% → **cold_start 59.58% (n=4, SD=1.00pp, PR #75)**
- Secondary reference: cold_start → Run D 63.00% (aspirational, reported descriptively only)
- Reference selection table in Hypothesis section updated accordingly
- Results Tracking table updated to reflect corrected primary/secondary roles
- Invalidation criterion 5 corrected for warm-start (halt if gen-0 val F1 < 0.60,
  not > 0.65 as written for cold-start runs)

**Implication for Phase 5**: Verdicts applied against cold_start 59.58% using the
pre-registered ±2pp/±4pp thresholds. Run D comparison reported as secondary context only.
If gemini_mean ≥ 61.58% (cold_start + 2pp): POSITIVE SIGNAL, n=4 replication recommended.
If both runs individually exceed 63.00%: noteworthy but not the primary verdict criterion.

### Amendment 2: Warm-start (ddce37b4) + NLP prompts — replicate Run D (2026-03-12)

**No confound** — applied uniformly to both V1 and V2 before any gen-0 data produced.

**Reason**: Run D (push, PR #73) achieved 63.00% test EM (best GigaEvo result, exceeding
GEPA 62.3%) using warm-start ddce37b4 + NLP prompts (`prompts=hotpotqa`) + F1+600. The
cold-start cold runs (V1/V2, stopped at gen 0) produced no useful data. Pivoting to an
exact replication of Run D's setup with Gemini as mutation LLM gives a cleaner and more
ambitious test: does a frontier mutation LLM push beyond 63.00%?

**Changes**:
- Seed: cold start → warm start ddce37b4 (`program_loader.problem_dir=experiments/hotpotqa/thinking/seeds/ddce37b4`)
- Prompts: `default` → `hotpotqa` (NLP mutation prompts, same as Run D)
- Primary reference updated: Run D test EM = 63.00% (primary); cold_start 59.58% (secondary)
- Gen-0 verification: warm-start gen-0 val F1 expected ~70% (not ~40-55% as for cold start); halt if < 60% or > 85%

**Comparison value**: This is now a direct mutation-LLM substitution test on top of the
best known GigaEvo configuration. If Gemini improves over 63.00% it's a genuine SOTA advance.

### Amendment 1: Pivot from ColBERT to BM25 retriever (2026-03-12)

**No confound** — applied uniformly to both V1 and V2 before any run starts.

**Reason**: colbert_feedback (PR #76) completed with verdict NEGATIVE (mean test EM 57.00%
vs cold_start reference 59.58%, −2.58pp). Key finding: ColBERT+rich-failure-feedback caused
severe val-test overfitting (+6.17pp mean val-test gap vs ~2-3pp typical). The mutation LLM
exploited high-information passage-level feedback to overfit prompts to the 600-sample
validation set. Switching to BM25 avoids this dynamic.

**Changes**:
- `problem.name`: `chains/hotpotqa/static_colbert_f1_600` → `chains/hotpotqa/static_f1_600`
- `pipeline`: `hotpotqa_colbert` → `hotpotqa_asi`
- Removed `HOTPOTQA_COLBERT_SERVER_URL` from launch commands (no ColBERT server needed)
- Primary reference updated: cold_start 59.58% (same BM25+F1+600 setup)
- Invalidation criterion 7 (ColBERT non-functional) removed

**Comparison value**: This pivot means gemini_mutation now directly replicates the
cold_start setup (BM25+F1+600, `hotpotqa_asi`) with only the mutation LLM changed
(Gemini-3-Flash vs Qwen3-235B). This is a cleaner isolation of the mutation LLM effect
than the originally planned ColBERT variant.

### Amendment 4: Upgrade mutation LLM to Gemini-3.1-Pro-Preview (2026-03-13)

**No confound** — applied uniformly to both V1 and V2 before any gen-0 data produced.

**Reason**: After observing 50–56% invalidity rate with Gemini-3-Flash (step 6 dependency
mismatch: Flash systematically drops the step 2 dependency, linearising the DAG), the decision
was made to upgrade to the more capable `google/gemini-3.1-pro-preview` model, which is expected
to follow the dependency-structure constraints more reliably. Flash runs (gen 0–4) were stopped
and DBs 3+4 flushed. No frontier data from Flash runs is used.

**Changes**:
- `llm`: `gemini3_flash` → `gemini31_pro` (`google/gemini-3.1-pro-preview` via OpenRouter)
- New config: `config/llm/gemini31_pro.yaml`
- Flash runs discarded (gen 0–4, invalidity 50–58%, no test eval run)

**Launch record update**:

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| V1 | 1963615 | 2026-03-13 13:48 UTC | DB=3, chain=10.226.17.25:8000, llm=gemini31_pro |
| V2 | 1963784 | 2026-03-13 13:48 UTC | DB=4, chain=10.225.185.235:8000, llm=gemini31_pro |
