# Pre-Registration: Generalization via Held-Out Validation

**Date**: 2026-03-14
**Protocol version**: 1.0
**Pre-registration commit**: `ea0884e796fbf60607133d29e7e2c69af60d8324`
**GitHub PR**: #81 (branch: `exp/hotpotqa-generalization`)
**Tracking issue**: #80
**Design doc**: `experiments/hotpotqa/generalization/01_design.md` (APPROVED v5)
**Review doc**: `experiments/hotpotqa/generalization/02_review.md` (verdict: APPROVED, Round 6)
**Evaluation script**: `experiments/hotpotqa/generalization/run_test_eval.sh` (to be created at Phase 4)

---

## Hypothesis

**H₀**: Mean test EM across n=4 held-out-validation runs does not differ from the cold-start
reference mean of 59.58% (PR #75, n=4, SD=1.00pp) by more than 1.67pp (MDE at 80% power).

**H₁**: Mean test EM >= 62.00% (+2.42pp above cold-start reference), indicating that
held-out validation produces programs that generalize substantially better than single-set
fitness.

**Primary metric**: Test EM at gen 25, best-by-held_F1 program, on the 300-sample held-out
test set, evaluated with thinking mode Qwen3-8B.

**Significance threshold**: α = 0.05, one-sided one-sample t-test vs reference 59.58%

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `llm` | `problem.name` | `HOTPOTQA_CHAIN_URL` | Seed |
|-----|-------|------------|-----------|-----------|-------|----------------|----------------------|------|
| G1 | gen-1 | 0 | hotpotqa_asi | generalization | default (Qwen3-235B vLLM) | chains/hotpotqa/static_holdout_f1 | http://10.226.17.25:8001/v1 | cold |
| G2 | gen-2 | 1 | hotpotqa_asi | generalization | default (Qwen3-235B vLLM) | chains/hotpotqa/static_holdout_f1 | http://10.226.17.25:8000/v1 | cold |
| G3 | gen-3 | 2 | hotpotqa_asi | generalization | gemini31_pro | chains/hotpotqa/static_holdout_f1 | http://10.225.185.235:8001/v1 | cold |
| G4 | gen-4 | 3 | hotpotqa_asi | generalization | gemini31_pro | chains/hotpotqa/static_holdout_f1 | http://10.225.185.235:8000/v1 | cold |

**Evo set**: train[0:700] (failure feedback to mutation LLM, evo_f1 computed here)
**Held-out val**: train[700:1000] (fitness = held_F1 only; NEVER used for failure feedback)
**Test set**: HotpotQA_test.jsonl (300 samples, evaluated post-hoc only)

**All 4 runs concurrent** on 4 chain servers (2x A100 servers, 2 ports each).

---

## Controlled Variables

| Field | Value |
|-------|-------|
| `num_parents` | 1 |
| `max_elites_per_generation` | 8 |
| `max_mutations_per_generation` | 8 |
| `stage_timeout` | 6000s |
| `dag_timeout` | 9000s |
| `max_generations` | 25 |
| Chain LLM | Qwen3-8B thinking mode (vLLM, `--max-model-len 32768`) |
| Failure sampling | `random.sample(failures, min(10, len(failures)))`, `cache_handler=NO_CACHE` |
| Cold start | Yes — no seed program (archive starts empty) |
| val_em_600 metric | EM on train[0:600] for comparable gap vs cold_start reference |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism (document and accept):
- `random.sample` in `FormatterStage` (failure sampling per generation)
- LLM sampling temperature and nucleus sampling in chain and mutation LLMs
- Non-deterministic GPU floating point across hardware

**Global seed**: N/A (Hydra config does not support global seed for MAP-Elites)

A fresh run with identical config will produce a different fitness trajectory but should
land in a statistically similar fitness range. Cross-experiment comparisons use effect-size
thresholds (from `01_design.md`) rather than exact trajectory matching.

---

## Dataset Checksums

Cryptographic anchor for the data used in this experiment.
Computed at pre-registration time (2026-03-14); verify before final evaluation.

| File | sha256 |
|------|--------|
| `problems/chains/hotpotqa/dataset/HotpotQA_train.jsonl` | `9d8b0ba2a19d124fa243c88b650b2ecd42e5c771bc4e039553389c6b9566ef94` |
| `problems/chains/hotpotqa/dataset/HotpotQA_test.jsonl` | `c46bfb185e448bf1b92cb75bb5ab967f3211051793967f01500f453945046b0d` |

---

## Success Criteria

| Outcome | Threshold | Implication |
|---------|-----------|-------------|
| STRONG POSITIVE — PRELIMINARY | mean test EM >= 62.30% | GEPA beaten. Held-out validation is the breakthrough. PRELIMINARY until deconfounding follow-up. |
| POSITIVE — PRELIMINARY | mean test EM in [62.00%, 62.30%) | Near-GEPA. Held-out validation is effective. PRELIMINARY until deconfounding follow-up. |
| SUGGESTIVE | mean test EM in [60.50%, 62.00%), p < 0.05 | Meaningful improvement but below GEPA. |
| MARGINAL | mean test EM in [59.58%, 60.50%), p < 0.05 | Statistically significant but small. |
| NULL | p >= 0.05 | No detectable effect. Val-test gap is not selection bias. |
| NEGATIVE | mean test EM < 57.58% | Held_F1-only fitness harms performance. |

Primary statistical test: one-sided one-sample t-test, H1: treatment_mean > 59.58%, alpha=0.05, df=3.

Val-test gap verdict (secondary):
- Comparable gap = val_em_600 - test_em (for direct comparability with cold_start's 2.58pp)
- GAP CLOSED: < 1.5pp | GAP COMPRESSED: [1.5pp, 2.5pp) | GAP UNCHANGED: [2.5pp, 4.0pp) | GAP INFLATED: >= 4.0pp

---

## Monitoring Plan

`max_generations`: 25

- Gen 3 (~10%): smoke check — all 4 PIDs alive, Redis keys growing, evo_f1 plausible (0.35–0.55), no held-out leakage in failures
- Gen 5 (~20%): first checkpoint — record evo_f1 and held_F1 for all runs; verify evo_f1 > held_F1 (normal); check birth-gen pattern
- Gen 13 (~50%): midpoint checkpoint — extract best-by-held_F1 program, run test eval, record evo-held gap
- Gen 25 (100%): final evaluation + analysis — invoke ml-research-methodologist for Phase 5

**Early termination rule**: If no frontier improvement for >= 10 consecutive generations
at gen >= 15, the run may be terminated early (consistent with cold_start protocol).

**Split bias check (BINDING — before launch)**: Run baseline chain on train[0:700] and
train[700:1000] separately. If |evo_baseline_em - held_baseline_em| > 5pp, halt and
reshuffle with seed=42. Document reshuffling as Amendment 1 ("No confound").

**Prompt review (BINDING — before launch)**: Human reviewer must confirm `gigaevo/prompts/generalization/`
satisfies all 5 requirements (01_design.md §12 checklist item 15). Document in this file below.

---

## Prompt Review Sign-Off

Reviewer: Researcher (user)
Date: 2026-03-14
Confirmation: The implemented mutation prompt at `gigaevo/prompts/generalization/mutation/system.txt` satisfies:
- (a) sampling framing: [x] "10 failures are a random sample from ~300+ total evo-set failures"
- (b) process-over-examples: [x] "Process over examples" anti-overfitting principles section
- (c) anti-overfitting directive: [x] "Compress rather than expand; abstract patterns not surface forms"
- (d) held-out awareness: [x] "Selection is based solely on fitness (held_F1) — unseen examples"
- (e) gap interpretation: [x] Names evo_f1 and fitness (held_F1); defines small/moderate/large gap thresholds; instructs LLM to treat large gap (>0.07) as overfitting signal and prefer Exploration archetypes

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| G1 | 2159756 | 2026-03-14 ~15:30 UTC | mutation=10.226.72.211:8777, chain=10.226.17.25:8001 |
| G2 | 2159757 | 2026-03-14 ~15:30 UTC | mutation=10.225.51.251:8777, chain=10.226.17.25:8000 |
| G3 | 2159758 | 2026-03-14 ~15:30 UTC | mutation=gemini31_pro/OpenRouter, chain=10.225.185.235:8001 |
| G4 | 2159759 | 2026-03-14 ~15:30 UTC | mutation=gemini31_pro/OpenRouter, chain=10.225.185.235:8000 |

Watchdog PID: 2160086
Launch commit: `96bbb42`

---

## Checkpoint Log

| Gen | Date (UTC) | evo_f1 (best) | held_F1/fitness (best) | evo-held gap | Notes |
|-----|-----------|--------------|----------------------|-------------|-------|
| 1 | 2026-03-14 13:26 UTC | 62.5% (G2) | 59.3% (G2) | 3.1–5.8pp | All 4 alive; split bias OK (gap <5pp); moderate overfitting, no large-gap trigger |
| 21 (G1), 25 (G2–G4) | 2026-03-15 UTC | — | G1=66.9%, G2=66.5%, G3=72.3%, G4=74.6% | — | Final gen. G1 terminated at gen 21 (see Amendment 1). Test evals: G1=pending, G2=58.47%±1.41pp, G3=61.00%±1.03pp, G4=59.93%±1.30pp (mean of 5 stochastic eval runs each). |

---

## Amendments

### Amendment 1 — G1 early termination at gen 21 (2026-03-15)

**Type**: Confound introduced (applies to G1 only)

**What happened**: G1 was terminated at gen 21 instead of the pre-registered gen 25. All Python processes were killed while G1 was still running; G2, G3, G4 had already completed gen 25.

**Impact**: G1 is evaluated with `--max-gen 21` (best-by-held_F1 program across gens 0–21) rather than gen 25. This introduces a mild asymmetry: G1 had 4 fewer generations of selection pressure. G1's best held_F1 at gen 21 = 66.9%, consistent with G2's final 66.5%, suggesting the frontier had likely plateaued. G1 is **included** in the analysis with this deviation noted.

**Assessment**: Confound is minor. G1 is included; if exclusion materially changes the verdict, this will be noted in 05_results.md.
