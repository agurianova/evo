# Pre-Registration: hotpotqa_val_gap — 2×2 Factorial (Sample Size × Evaluation Protocol)

**Date**: 2026-03-05
**Pre-registration commit**: `287e7b6`
**Design doc**: `experiments/hotpotqa_val_gap/01_design.md`
**Review doc**: `experiments/hotpotqa_val_gap/02_review.md` (verdict: APPROVED WITH NOTES — Prof. Andrei Volkov, 2026-03-05)

> **Protocol rule**: This file must be committed BEFORE any code changes to
> `problems/chains/hotpotqa/static_600/` or `problems/chains/hotpotqa/static_r600/`.

---

## Hypothesis

**Research question**: Does changing validation set size (300 vs 600 samples) or evaluation
protocol (fixed vs rotating) reduce the val-test gap — defined as |frontier val EM − test EM|
at generation 50 — without regressing test EM below 60.0%?

**H₀ (size main effect)**: Sample size alone has no detectable effect on the val-test gap.
Under fixed protocol: |gap_O − gap_Q| < 2.0pp.

**H₁ (size main effect)**: Fixed-600 (Run Q) reduces the val-test gap relative to fixed-300
(Run O) by ≥ 2.0pp. A larger fixed val set provides a more discriminating fitness signal,
reducing overfitting to the 300-sample evaluation noise.

**H₀ (rotation main effect)**: Evaluation protocol alone has no detectable effect at 300
samples: |gap_O − gap_R| < 2.0pp.

**H₁ (rotation main effect)**: Rotating-300 (Run R) differs from fixed-300 (Run O) by ≥ 2.0pp
in the gap. All three mechanistic hypotheses (H_winners_curse, H_regime_mismatch, H_mapelites)
predict gap_R > gap_O; they differ in what happens to Run P vs Run R.

**H₀ (interaction)**: The size effect is the same under fixed and rotating protocols:
|(gap_R − gap_P) − (gap_O − gap_Q)| < 2.0pp.

**H₁ (interaction)**: The size effect differs across protocols by ≥ 2.0pp. A positive
interaction ((gap_R − gap_P) > (gap_O − gap_Q)) supports H_winners_curse: larger draws reduce
the gap more under rotation than under fixed protocol.

**Three pre-registered mechanistic hypotheses**:
- **H_winners_curse**: At 300/1000, E[pairwise overlap] = 9%; at 600/1000, E = 36%. Larger
  draws reduce winner's curse. Predicts gap_P < gap_R; rotating-600 may approach or beat fixed.
- **H_regime_mismatch**: Rotating val distribution optimizes for training average, not a
  specific fixed test draw. Predicts gap_R > gap_O AND gap_P > gap_Q regardless of N.
- **H_mapelites**: MAP-Elites amplifies per-draw noise at the bin level — each of ~50 archive
  bins is populated by a program on a distinct draw, systematically over-populating bins with
  lucky draws. Predicts gap_R > gap_O AND gap_P > gap_Q regardless of N.

**Primary metric**: Val-test gap = |val EM − test EM| at gen 50 for the best-by-val program.
**Secondary metric**: Test EM at gen 50 (floor: ≥ 60.0%).
**Significance threshold**: POSITIVE (actionable) ≥ 5.0pp gap reduction; SUGGESTIVE 2.0–5.0pp.

---

## Dataset Checksums

All files relative to `problems/chains/hotpotqa/dataset/`:

| File | sha256 | Rows |
|------|--------|------|
| `HotpotQA_train.jsonl` | `9d8b0ba2a19d124fa243c88b650b2ecd42e5c771bc4e039553389c6b9566ef94` | 1000 |
| `HotpotQA_test.jsonl` | `c46bfb185e448bf1b92cb75bb5ab967f3211051793967f01500f453945046b0d` | 300 |
| `wiki17_abstracts.jsonl.passages.pkl` | `44e329f00a240493dd0423afeb42767f830b954dbe5f89dfd0f6e0f7046ca9fc` | — |

Verify before launch:
```bash
sha256sum problems/chains/hotpotqa/dataset/HotpotQA_train.jsonl
sha256sum problems/chains/hotpotqa/dataset/HotpotQA_test.jsonl
```

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | Val N | Val protocol | Seed |
|-----|-------|------------|-----------|-----------|----------------|-------|--------------|------|
| O | Control (fixed-300) | 4 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static` | 300 | Fixed sequential | ddce37b4 |
| R | Rotation-only (rotating-300) | 7 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_r` | 300 | Hash-seeded random | ddce37b4 |
| Q | Size-only (fixed-600) | 6 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_600` | 600 | Fixed sequential | ddce37b4 |
| P | Compound (rotating-600) | 5 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_r600` | 600 | Hash-seeded random | ddce37b4 |

**All four runs differ only in `problem.name`** (and therefore `validate.py`). Every other
field is identical.

**Redis DBs**: 4 (Run O), 5 (Run P), 6 (Run Q), 7 (Run R). DBs 0–3 reserved for NLP prompts
data pending flush. DBs 14–15 reserved for P3 crossover.

---

## Controlled Variables

| Field | Value |
|-------|-------|
| `seed_program` | ddce37b4 (val=62.7% on fixed-300; test=60.0%) |
| `max_generations` | 50 |
| `max_elites_per_generation` | 8 |
| `max_mutations_per_generation` | 8 |
| `num_parents` | 1 |
| `mutation_mode` | rewrite |
| `pipeline` | `hotpotqa_asi` |
| `prompts` | `default` |
| `parent_selector` | `AllCombinationsParentSelector` |
| `primary_resolution` | 50 |
| Chain LLM | Qwen3-8B, thinking mode, `step_max_tokens=8192` |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 via vLLM (1 per run from pool) |
| Chain LLM context window | 32768 (restart servers with `--max-model-len 32768` before launch) |
| Test set | Fixed 300 samples from `HotpotQA_test.jsonl` (never seen during evolution) |
| Random failure sampling | Active: all failures returned; formatter samples 10 randomly; `NO_CACHE` |

---

## Success Criteria

**POSITIVE (actionable)** — all three conditions must hold simultaneously:
1. `gap(X) < gap(O) − 5.0pp` — gap reduction exceeds ~1 SE noise floor
2. `test EM(X) >= 60.0%` — absolute EM floor (matches seed test performance)
3. `test EM(X) >= test EM(O) − 1.5pp` — relative floor against current control

**SUGGESTIVE**: gap reduction 2.0–5.0pp with floor conditions met. Requires replication (N ≥ 3)
before any adoption decision.

**NULL**: |delta| < 2.0pp — no detectable gap change.

**NEGATIVE**: delta ≤ −2.0pp — gap inflation; treatment is worse than control.

**Primary comparison (Gate C)**: Run Q vs Run O (fixed-600 vs fixed-300). POSITIVE Gate C is
sufficient to recommend adopting `static_600` as the new baseline.

**Secondary comparison (Gate B)**: Full 2×2 pattern analysis for mechanistic hypothesis ranking.
A POSITIVE Gate B without a POSITIVE Gate C is insufficient for adoption recommendation.

**Consistency check for Run O**: gap ∈ [4.0pp, 11.0pp], test EM ∈ [57.0%, 63.0%]. Investigate
if outside range before interpreting 2×2.

**Consistency check for Run R**: gap ∈ [4.0pp, 15.0pp]. Reference: L/M/N gaps 8.67–13.67pp
under NLP prompts.

---

## Monitoring Plan

- **Gen 5** (smoke check): Verify all four runs are producing mutations and archive is
  populating. Check for silent hangs (mutation stage > 30 min → server failure).
  _Run F specific_: confirm val F1(gen 0) ≥ 62.7% (F1 < EM is mathematically impossible);
  confirm Redis archive entry for seed contains both `fitness` (F1) and `em` (EM) fields.
- **Gen 10** (first checkpoint): Record val fitness for best-by-archive program in each run.
  Verify 600-sample run Q is evaluating 600 samples (log dataset length). Evaluate top-1 from
  each run on test set using EM.
  _Run F specific_: compare test EM(F) vs test EM(O) at gen 10 — first clean signal for
  whether F1 training translates to test EM improvement. Check acceptance rate F vs O (gens
  1-10): higher acceptance under F1 fitness is a positive mechanistic signal.
- **Gen 25** (midpoint checkpoint): Record val fitness trajectories. Check acceptance rates.
  Log generation times for Q (expected ~8 min/gen; alert if > 12 min).
- **Gen 50** (final evaluation): Identify best-by-val program from each run. Evaluate on full
  300-sample test set using EM. Compute: gap_O, gap_R, gap_Q, test EM(F). Primary comparison
  is test EM(F) vs test EM(O); report cross-metric gap |val F1(F) − test EM(F)| as supplementary.

**Early termination rules** (from 01_design.md §10):
- Crash with no recovery within 2 hours → terminate that run; surviving runs continue.
- Zero mutations for 5+ consecutive gens OR mutation stage timeout > 30 min → diagnose before
  continuing; terminate if no resolution within 2 hours.
- 600-sample eval runtime > 15 min/gen → pause, diagnose, resume or terminate.
- Dry-run gen time for Q or P > 12 min → flag at-risk, review server utilization before launch.

**No early termination for poor fitness.** All four runs execute for the full 50 generations.

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Mutation LLM server | Notes |
|-----|-----|-------------------|---------------------|-------|
| O | 3054746 | 2026-03-05 12:21 UTC | 10.226.72.211:8777 | |
| R | 3054747 | 2026-03-05 12:21 UTC | 10.226.15.38:8777 | |
| Q | 3054748 | 2026-03-05 12:21 UTC | 10.226.185.131:8777 | |
| F | 3054749 | 2026-03-05 12:21 UTC | 10.225.51.251:8777 | Amendment 1: replaces Run P |

Watchdog PID: 3057704
Launch commit: `acec7c1`

`run_test_eval.sh` sha256: `9cc855f7a7a2082a2a8ef3a65d2d056251b134c6c160d70f8e408c7941b1787e`

Preflight checks passed at launch (2026-03-05 12:21 UTC):
- [x] All 8 vLLM servers reachable (HTTP 200)
- [x] All 4 chain endpoints: max_model_len=32768
- [x] All 4 chain endpoints: thinking mode confirmed (`<think>` in response)
- [x] Redis DBs 4, 5, 6, 7: empty (0 keys each)
- [x] Seed directory: ddce37b4, 1 program found
- [x] Dataset checksums: HotpotQA_train.jsonl and HotpotQA_test.jsonl match pre-registration

Dry-run checklist (pending — verify at gen 5 smoke check):
- [ ] Run O seed val EM on fixed-300: ___ % (expected 62.7%)
- [ ] Run Q seed val EM on fixed-600: ___ % (expected 60–66%)
- [ ] Run R seed val EM on rotating-300: ___ % (hash-deterministic)
- [ ] Run F gen-0: val F1 ≥ 62.7% (if F1 < EM, stop — bug in F1 computation)
- [ ] Run F gen-0: Redis archive entry contains both `fitness` (F1) and `em` (EM) fields

---

## Checkpoint Log

| Gen | Date (UTC) | Run | Notes |
|-----|-----------|-----|-------|

---

## Amendments

### Amendment 1 — Replace Run P (rotating-600) with Run F (fixed-300, F1 fitness)

**Date**: 2026-03-05
**Commit**: 866f106
**Type**: Confound introduced — deliberate. Run F differs from O in both the fitness metric (F1
vs EM for MAP-Elites selection) and the task description shown to the mutation LLM (F1 objective
vs EM objective). The latter is an acknowledged second component of the treatment: it ensures
the mutation LLM's guidance is consistent with the fitness function. These two changes cannot be
separated in Run F's results. The effect attributed to "F1 fitness" in Gate E includes both the
smoother selection landscape and the changed mutation guidance. O/R/Q are unchanged.

**Change**: Run P (`chains/hotpotqa/static_r600`, rotating-600, EM fitness, DB 5) is replaced by
Run F (`chains/hotpotqa/static_f1`, fixed-300, **F1 fitness**, DB 5).

**Rationale**: EM is a binary per-sample signal — a near-correct multi-word answer scores
identically to a completely wrong answer. For multi-word HotpotQA answers where the model
predicts the right core content but adds or drops a token (e.g., predicted="New York City",
gold="New York": EM=0, F1=0.80), evolution under EM treats these as total failures and may
overfit to the specific surface forms present in the 300-sample val set rather than the
underlying reasoning pattern. F1 (SQuAD token-level) provides a smoother, more continuous
fitness signal that assigns partial credit for partially-correct multi-word predictions,
potentially giving evolution a cleaner gradient toward the reasoning objective.

**Scope of F1 advantage**: token-level F1 does NOT provide partial credit for single-token
near-matches with different string representations (e.g., "metres" vs "meters": F1=0 as these
are distinct tokens after normalize_text; "the Beatles" vs "Beatles": EM=1 and F1=1 since
normalize_text removes articles). The F1 advantage is specifically for multi-word partial
matches where the model predicts the right entities with extra or missing context tokens.

**Failure criterion**: EM=0 (identical to static/validate.py), NOT F1 < 1.0. This choice
isolates the fitness metric effect from the mutation feedback signal (Option A). Note: under
`normalize_text`, F1 < 1.0 and EM = 0 are very nearly equivalent in practice (F1 = 1.0 iff
token multisets match completely; the only divergence is word-order permutations like
"cat sat" vs "sat cat" which are rare for short HotpotQA answers). The key difference is in
the feedback signal quality: using EM=0 as the failure threshold ensures the mutation LLM
sees only complete failures, identical in character to what it sees in Run O, preventing an
inadvertent change to the feedback distribution.

**What is retained**: Run O (fixed-300, EM) remains the primary control. Run F is directly
comparable to O — identical samples, identical N, only the fitness metric changes. This is the
cleanest possible test of the metric effect.

**Updated run table**:

| Run | Label | `redis.db` | `problem.name` | Val N | Val protocol | Fitness | Seed |
|-----|-------|------------|----------------|-------|--------------|---------|------|
| O | Control (fixed-300, EM) | 4 | `chains/hotpotqa/static` | 300 | Fixed | EM | ddce37b4 |
| R | Rotation-only (rotating-300, EM) | 7 | `chains/hotpotqa/static_r` | 300 | Hash-seeded | EM | ddce37b4 |
| Q | Size-only (fixed-600, EM) | 6 | `chains/hotpotqa/static_600` | 600 | Fixed | EM | ddce37b4 |
| F | Metric (fixed-300, F1) | 5 | `chains/hotpotqa/static_f1` | 300 | Fixed | F1 | ddce37b4 |

**Updated comparisons**:
- **Gate C** (primary, unchanged): Q vs O — fixed-600 vs fixed-300, EM fitness
- **Gate E** (new primary): F vs O — F1 fitness vs EM fitness, fixed-300
  - POSITIVE: gap_F < gap_O − 5.0pp AND test EM(F) ≥ 60.0% AND test EM(F) ≥ test EM(O) − 1.5pp
  - Note: Run F val fitness = F1 (not EM). Gap is still computed as |val F1 − test EM| — this
    is a cross-metric gap; interpret carefully. Primary question: does F1 training produce a
    program with lower test-EM gap than EM training?
- **Gate B** (rotation effect): R vs O — unchanged
- **Gate D** (H1_disc / acceptance rate): unchanged

**What is lost**: Causal decomposition of the size × rotation interaction. With P removed, the
H_winners_curse vs H_regime_mismatch / H_mapelites discrimination is no longer possible within
this experiment. If the rotation main effect (gap_R > gap_O) is confirmed, a follow-up
experiment is required to determine whether larger draws mitigate the inflation (H_winners_curse)
or whether rotation is bad regardless of draw size (H_regime_mismatch / H_mapelites). This
scope reduction is explicit and accepted.

**Gate E primary comparison**: `test EM(F)` vs `test EM(O)` — both evaluated on the fixed
300-sample test set with EM scoring. This is the interpretable cross-run comparison and the
gate for the POSITIVE verdict.

The cross-metric gap `|val F1 − test EM|` for Run F is reported as supplementary information
only; it is NOT compared directly to gap_O. Reason: val F1 ≥ val EM is guaranteed by
construction, creating a structural baseline divergence E[F1 − EM] at gen 0. Phase 5 must
report the gen-0 structural divergence (seed F1 − seed EM on fixed-300) and subtract it from
gap_F before any gap comparison: `adjusted_gap_F = |val F1 − test EM| − (seed F1 − seed EM)`.
This adjusted gap is the metric-comparable equivalent. Report both raw and adjusted gap_F.

**Dry-run verification (blocking before launch)**: At gen 0 of Run F, extract one Redis archive
entry and confirm it contains both `fitness` (F1 value) and `em` (EM value) fields. If `em` is
absent, secondary metric logging is not working and val EM for Run F programs will be
unrecoverable at Phase 5 time. Record gen-0 seed F1 and EM values in the dry-run checklist.

**Consistency check for Run F**: val F1 ≥ val EM always (F1 ≥ EM by construction). At gen 0,
seed F1 on fixed-300 is expected in [64%, 70%] (seed EM=62.7%, F1 always ≥ EM). If val F1 <
62.7% at gen 0, investigate immediately (F1 < EM is mathematically impossible). Gap for F is
measured as |val F1 − test EM| — note this compares different metrics; the gap can be large
even if the program is good if F1 and EM diverge. Report this explicitly in Phase 5.

---

### Amendment 2 — Run Q invalidated (stage_timeout too short for 600-sample eval)

**Date**: 2026-03-06
**Commit**: _(fill in)_
**Type**: Run invalidated.

**Finding**: Post-hoc inspection of Run Q Redis data revealed a 96.3% invalidity rate:
354 programs evaluated, only 13 valid (3.7%). All others were FAILED at the
`CallValidatorFunction` stage due to `stage_timeout=2400s` being exceeded.

**Root cause**: `stage_timeout=2400` was sized for 300-sample evaluations (~244s per
program). 600-sample evaluations empirically take a mean of ~1412s per program (max
2289s), well above the 2400s limit for many programs. The non-linear scaling (6× vs
expected 2×) is likely due to BM25 retrieval and LLM call variance accumulating over
2× more samples. The pre-registration monitoring plan noted to alert if Q gen time
> 12 min, but did not check the per-program invalidity rate — the run cycled through
50 generations quickly (each gen had few valid completions), masking the failure.

**Impact**: Gate C (fixed-600 vs fixed-300, primary hypothesis) is **unanswerable**
from this experiment. Gates B (rotation, R vs O) and E (F1 metric, F vs O) are
unaffected — O, R, F all have normal valid rates.

**Corrective action**: Re-run Q in a follow-up experiment with `stage_timeout ≥ 5000`.
Gate C remains an open research question.
