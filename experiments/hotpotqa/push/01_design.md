# Experimental Design: GEPA Push — 4-Run Targeted Attack on 62.3% Test EM

**Date**: 2026-03-07
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Revised (awaiting Phase 2 re-approval)

---

## 1. Research Question

Can GigaEvo exceed GEPA (62.3% test EM on HotpotQA with Qwen3-8B thinking mode) by combining
the two most promising validated signals — F1-protocol fitness and domain-specific NLP mutation
prompts — and by re-opening the unanswered 600-sample validation gate, and by combining F1 fitness
with crossover-level mutation diversity?

The prior experiment series (val_gap, PR #70) established that F1-protocol training is SUGGESTIVE
(Gate E: +4.34pp gap compression, +1.34pp test EM, N=1), that fixed-300 EM is a reproducible
baseline (60.0–60.3% test EM), and that rotation at 300/1000 is consistently harmful across all
conditions. The NLP prompts experiment (PR #69) produced a NULL result but was confounded:
NLP prompts and rotation were applied simultaneously, so NLP prompts on fixed-300 have
never been tested in isolation. This experiment closes four outstanding threads:

- **Thread 1** (Runs A): Does combining F1-protocol fitness with NLP mutation prompts on
  fixed-300 improve test EM beyond 62.3%? The two treatments have never been combined.
- **Thread 2** (Run B): Does 600-sample fixed validation with corrected stage_timeout reduce
  the val-test gap sufficiently to push past GEPA? Gate C is still open.
- **Thread 3** (Run C): Does F1-protocol fitness on 600-sample fixed validation further
  improve test EM beyond Run B (EM) or Run F (F1/300)? The combination of better fitness
  signal AND lower selection noise is untested.
- **Thread 4** (Run D): Does NLP prompts on fixed-600-EM close the gap from a different
  angle — mutation quality improvement at a larger validation sample size?

---

## 2. Hypotheses

### Run A — F1 fitness + NLP prompts (fixed-300)

**H₀(A)**: Combining F1-protocol fitness with NLP mutation prompts on fixed-300 produces
test EM no higher than the F1-only result (Run F, val_gap: 61.67%) — i.e., NLP prompts
provide no additional lift when combined with F1 fitness.

**H₁(A)**: F1 fitness + NLP prompts on fixed-300 achieves test EM ≥ 62.3% (GEPA), beating
the F1-only result by ≥ 0.63pp. Mechanistic logic: NLP prompts target the mutation LLM's
ability to reason about linguistic quality of multi-hop chains; F1 fitness targets the selection
landscape. These act on different points in the pipeline (mutation quality vs. selection signal)
and should combine additively or super-additively. If NLP prompts add even +0.5pp on top of
the F1-protocol +1.34pp gain observed in Run F, the GEPA target is within reach.

**Effect size that matters**: Δ test EM(A vs F) ≥ +0.63pp (enough to cross GEPA). Δ ≥ +2.0pp
would be clearly positive and motivate replication.

---

### Run B — Fixed-600 EM (Gate C re-run, corrected stage_timeout)

**H₀(B)**: A larger fixed validation set (600 samples) does not reduce the val-test gap
relative to fixed-300 EM (Run O). Formally: |gap_O − gap_B| < 2.0pp within-metric EM.

**H₁(B)**: Fixed-600 EM (Run B) reduces the val-test gap by ≥ 2.0pp relative to fixed-300
EM (Run O, val_gap: gap = 6.00pp), AND achieves test EM ≥ 60.0%. The selection noise floor
drops from SE ≈ 2.4pp (n=300, p=0.6) to SE ≈ 1.3pp (n=600), reducing winner's curse in
MAP-Elites archive selection, allowing the archive to converge on programs that are genuinely
better rather than lucky.

**Effect size that matters**: Δ gap ≥ 2.0pp (pre-registered). A POSITIVE verdict on Gate C
motivates adopting static_600 as the new baseline for all future experiments. Δ gap ≥ 4.0pp
(matching Gate E) would elevate Run B to a STRONG POSITIVE.

---

### Run C — Fixed-600 F1 (F1 fitness + larger validation)

**H₀(C)**: Combining F1 fitness with fixed-600 validation produces test EM no higher than
either Run B (EM/600) or Run F (F1/300) individually.

**H₁(C)**: Fixed-600 F1 achieves test EM ≥ 62.3% (GEPA). Logic: F1 fitness reduces val EM
overfit (demonstrated in Run F), and 600-sample validation reduces selection noise (predicted
by Gate C hypothesis). These two gap-reduction mechanisms are independent and should combine:
F1 training keeps val EM from inflating while 600 samples reduce the noise floor, together
producing a val-test gap well under 1pp. If val EM tracks test EM closely (~1pp gap as in
Run F) and evolution finds a 62–63% EM program, GEPA is beatable. Requires new problem
directory `chains/hotpotqa/static_f1_600`.

**Effect size that matters**: test EM(C) ≥ 62.3% (GEPA). Even test EM(C) ≥ 61.7% with a gap
< 1pp would be a POSITIVE result for the combined F1+600 treatment.

---

### Run D — Fixed-600 EM + NLP prompts

**H₀(D)**: NLP mutation prompts with fixed-600 EM produce test EM no higher than fixed-600
EM without NLP prompts (Run B).

**H₁(D)**: NLP prompts improve mutation quality sufficiently that, combined with a reduced-
noise 600-sample fitness signal, test EM exceeds GEPA (62.3%). Mechanistic logic: the
earlier NLP-prompts NULL was confounded with rotation; here NLP prompts are applied on the
fixed-600 baseline, giving the mutation LLM both better domain framing AND the mutation LLM
sees less overfit elites (selection noise is halved), producing better crossover targets for
NLP-guided mutation.

**Effect size that matters**: Δ test EM(D vs B) ≥ +1.0pp is meaningful; D ≥ GEPA (62.3%) is
the primary target.

---

### Cross-run composite hypothesis

**H₁(cross)**: At least one of {A, B, C, D} achieves test EM ≥ 62.3%, confirming that the
GEPA benchmark is beatable with evolutionary optimization on fixed Qwen3-8B. With four
independent attempts each targeting a plausible mechanism, the probability of at least one
success is substantially higher than any individual run.

**Null composite**: All four runs achieve test EM < 62.3%, suggesting that single-parent
stagnation (frontier peaks at birth-gen 4–6) is the binding constraint and no combination
of fitness signal, sample size, or mutation prompt engineering can overcome it without
structural changes (P3 crossover).

### Primary comparison hierarchy

**Run C (F1 × default × 600) is the primary test for the experiment-level verdict.**
Run C combines both validated gap-reduction mechanisms (F1 fitness reduces val-EM overfit;
600-sample validation reduces selection noise) without adding a third simultaneous treatment.
It is the highest-leverage, least-confounded run for the GEPA comparison. If only one run
can exceed 62.3%, it is Run C that determines the experiment-level conclusion.

**Runs A, B, D are secondary.** Each tests a specific mechanism combination:
- Run A (F1 + NLP + 300): deconfounds NLP prompts under F1 fitness; secondary because it adds
  a third treatment (NLP prompts) on top of the Run C combination.
- Run B (EM + default + 600): isolates the 600-sample effect without F1; secondary to Run C.
- Run D (EM + NLP + 600): tests NLP prompts under 600-sample EM; secondary.

The experiment-level conclusion (POSITIVE / SUGGESTIVE / NULL) is determined primarily by
Run C's result. Secondary runs provide mechanism attribution and motivate follow-up experiments
but do not individually determine the experiment-level verdict. If Run C is SUGGESTIVE and Run A
is POSITIVE, the experiment-level verdict remains SUGGESTIVE pending N ≥ 3 replication of A.

---

## 3. Independent Variables

| Variable | Control value | Treatment value(s) | Runs |
|----------|---------------|--------------------|------|
| Fitness metric | EM (binary) | F1 (token-level partial credit) | A, C (F1); B, D (EM) |
| Mutation prompts | `prompts=default` | `prompts=hotpotqa` (NLP-specific) | A, D (NLP); B, C (default) |
| Validation sample size | 300 (fixed) | 600 (fixed) | B, C, D (600); A (300) |

Each run is a specific combination of these three binary variables:

| Run | Fitness | Prompts | Val N | Cell in 2³ design |
|-----|---------|---------|-------|------------------|
| A | F1 | NLP | 300 | F1 × NLP × 300 |
| B | EM | default | 600 | EM × default × 600 |
| C | F1 | default | 600 | F1 × default × 600 |
| D | EM | NLP | 600 | EM × NLP × 600 |

**Reference cells from prior experiments** (not re-run; used for comparison):
- Run O (val_gap): EM × default × 300 → test EM = 60.33%, gap = 6.00pp
- Run F (val_gap): F1 × default × 300 → test EM = 61.67%, gap_EM = 1.66pp (SUGGESTIVE)
- Run K (nlp_prompts): EM × NLP × 300 — but confounded with rotation; excluded
- Run L/M/N (nlp_prompts): EM × NLP × 300 with rotation — excluded (rotation confound)

Note: The EM × default × 300 reference cell (Run O) is fully populated. The F1 × default × 300
cell (Run F) is populated with N=1. No cell involving NLP prompts on fixed-300 without
rotation has been previously measured. No cell involving 600-sample validation has a valid
result (Gate C was invalidated by stage_timeout). All four proposed runs address unexplored
cells in the factorial space.

---

## 4. Dependent Variables

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test EM at gen 50 (best-by-val) | 300-sample held-out test set; EM scoring; thinking mode Qwen3-8B | YES — primary for all runs |
| Val-test gap (within-metric EM) | val EM − test EM; for F1 runs: use `valid_frontier_em` Redis key for val EM | YES — secondary |
| Val frontier trajectory | gen-by-gen val fitness (F1 or EM per run) from Redis `valid_frontier_fitness` | No — diagnostic |
| Invalidity rate at gen 5 | Fraction of invalid programs at gen 5; alert if > 30% | No — monitoring |
| Birth-generation of frontier | Birth-gen of best-by-val program | No — stagnation diagnostic |

**Primary metric**: test EM at gen 50 (best-by-val program), evaluated on fixed 300-sample
test set, thinking mode Qwen3-8B, consistent with all prior experiments and the GEPA benchmark.

**Cross-metric note for Runs A and C (F1 fitness)**: Val fitness is F1, but the primary
metric is test EM. Require `valid_frontier_em` Redis key to be populated by `static_f1` and
`static_f1_600` validate.py files (confirmed for `static_f1`; verify for `static_f1_600`
during dry-run). The within-metric val-test gap uses `valid_frontier_em`, not
`valid_frontier_fitness` (F1), for comparability with prior EM runs.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Chain topology | 6-step fixed (2 tool, 4 LLM) | Unchanged across all experiments |
| Chain LLM | Qwen3-8B, thinking mode ON (default chat template) | Required for GEPA comparison |
| Mutation LLM | Qwen3-235B-A22B-Thinking, one server per run | Consistent with all prior runs |
| `pipeline` | `hotpotqa_asi` | Required for all hotpotqa variants; never `standard` |
| Warm-start seed | `ddce37b4` (val EM 62.7%, test EM 60.0%) | Same seed as O, R, F, K, L, M, N |
| Leapfrog init | Top programs from ddce37b4 run | Standard continuation procedure |
| `max_generations` | 50 for Run A; **25 for Runs B, C, D** | 600-sample runs stagnate by birth-gen 6 (confirmed across all prior runs); 25 gens provides ≥ 4× the stagnation window at half the compute cost. Early completion may apply if stagnation confirmed earlier (see Stop Criteria). |
| `max_elites_per_generation` | 8 | Consistent with val_gap runs O/R/Q/F |
| `max_mutations_per_generation` | 8 | Consistent with val_gap runs O/R/Q/F |
| `num_parents` | 1 | Single-parent mutation (P3 crossover is a separate experiment) |
| Validation protocol | Fixed sequential (first N train samples) | Rotation permanently excluded |
| Test evaluation | Fixed 300-sample test set; `run_test_eval.sh`; thinking mode verified | Consistent with all prior runs |
| Random failure sampling | All failures returned from validate.py; formatter samples 10 with NO_CACHE | Required; cf0cfc1 |
| `dag_timeout` | 7200 for Run A; **9000 for Runs B, C, D** | Per-program DAG timeout must exceed stage_timeout + mutation LLM stages. Calculation: 6000 (validator max) + ~1500 (InsightsStage + LineageStage + MutationContextStage under load) + 1500 headroom = 9000s. Run A uses 300-sample eval (max ~244s validator) + same mutation LLM stages; 7200s is adequate. |
| Redis DB prefix | `chains/hotpotqa/static` (or variant) | Derived from problem.name |

**stage_timeout — run-specific**:
- Run A: `stage_timeout=2400` (300-sample eval; empirical max ~244s; 2400s is adequate)
- Runs B, C, D: `stage_timeout=6000` (600-sample eval; empirical max ~2300s observed in val_gap
  Run Q; 6000s provides 2.6× margin above observed max; safe per Amendment 2 lesson)

Note: `dag_timeout` is a per-program-DAG timeout (not per-generation). Calculation for B/C/D:
stage_timeout (6000s) + InsightsStage + LineageStage + MutationContextStage under load (~1500s
combined) + 1500s headroom = 9000s. This is registered as `dag_timeout=9000` for Runs B, C, D.
Run A uses `dag_timeout=7200` (validator max ~244s + mutation LLM stages + headroom is well within 7200s).

---

## 6. Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | `stage_timeout` | `dag_timeout` | `max_gen` | Mutation LLM | Val N | Fitness |
|-----|-------|-----------|-----------|-----------|----------------|----------------|--------------|----------|-------------|-------|---------|
| A | push-A | 8 | `hotpotqa_asi` | `hotpotqa` | `chains/hotpotqa/static_f1` | 2400 | 7200 | 50 | 10.226.72.211:8777 | 300 | F1 |
| B | push-B | 9 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_600` | 6000 | 9000 | 25 | 10.226.15.38:8777 | 600 | EM |
| C | push-C | 10 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | 6000 | 9000 | 25 | 10.226.185.131:8777 | 600 | F1 |
| D | push-D | 11 | `hotpotqa_asi` | `hotpotqa` | `chains/hotpotqa/static_600` | 6000 | 9000 | 25 | 10.225.51.251:8777 | 600 | EM |

**Chain LLM assignment** (one chain server per run, no sharing):
- Run A: `http://10.226.17.25:8001/v1`
- Run B: `http://10.226.17.25:8000/v1`
- Run C: `http://10.225.185.235:8001/v1`
- Run D: `http://10.225.185.235:8000/v1`

**Required pre-launch actions**:
1. Create `problems/chains/hotpotqa/static_f1_600/` problem directory (Run C): new variant
   combining F1 fitness with 600-sample fixed validation. Must inherit `static_f1/validate.py`
   logic (F1 scoring, `valid_frontier_em` Redis key population) with `static_600`'s
   dataset loading (first 600 train samples). Task description from `static_f1/task_description.txt`
   (F1-objective framing). Metrics yaml from `static_f1/metrics.yaml` (F1 primary).
2. Verify `valid_frontier_em` key is populated by dry-run of Run C (gen-0 check). Expected
   gen-0 val F1 ≈ 68–72%; expected gen-0 val EM ≈ 59–61% (see Section 12, Risk 1). Halt if
   outside these ranges.
3. Verify `hotpotqa_asi.yaml` has `prompts_dir: ${prompts.dir}` in BOTH `evolution_context`
   AND `mutation_operator` blocks (known bug fixed at 920c975 but must be re-confirmed).
   For Runs A and D: `python run.py [overrides] --cfg job` must show **two distinct**
   `prompts_dir` entries in the output — one under `evolution_context` and one under
   `mutation_operator`. A single entry means the bug has re-appeared. Do not launch.
4. Verify stage_timeout wiring for 600-sample runs: inspect exec_runner log at gen 0 and
   confirm that `CallValidatorFunction` stage is completing within 2400–6000s (not timing
   out at 2400s). The `--cfg job` output alone is insufficient — the timeout is set in
   Python code (not YAML), so log inspection at gen 0 is mandatory before proceeding
   to gen 1 for Runs B, C, D.
5. Restart chain servers with `--max-model-len 32768` if not already at 32768 (confirmed for
   val_gap but CONTEXT.md timestamp is 2026-03-05 — re-verify at launch).
6. Flush Redis DBs 8–11 if non-zero keys (DBs 0–7 used by prior experiments; 8–11 should be
   clean but verify).

---

## 7. Sample Size Justification

**n = 1 per cell.** This is the same constraint as all prior GigaEvo HotpotQA experiments.

At n=1, we cannot compute within-experiment variance or formal p-values. The measurement
noise floor for test EM at n=300 samples is SE ≈ sqrt(p×(1−p)/n) ≈ sqrt(0.60×0.40/300) ≈
2.83pp (one standard error) or 95% CI ≈ ±5.5pp per run. This means:

- **Two runs are statistically indistinguishable if |Δ EM| < 5.5pp** at the single-measurement
  level. All within-run comparisons at this sample size are consistent with noise.
- **The noise floor is not our primary concern for GEPA comparison**: GEPA (62.3%) is a
  fixed external reference, not a sample from our distribution. A single run at 62.5% is
  meaningful evidence that GEPA is beatable, even if not conclusive.
- **For Gate C (Run B)**: The within-metric gap comparison (gap_B vs gap_O) is estimated at ±4.0pp
  after noise propagation; Δ gap ≥ 2.0pp is our pre-registered threshold, chosen to be
  detectable at N=1 with reasonable confidence (gap reduction must be > noise floor / 2 to
  be credible). A gap reduction of 4.0pp or more would be STRONGLY POSITIVE.
- **For Run C (F1/600)**: This cell has the smallest expected noise (both F1 fitness and 600
  samples reduce the val-test gap variance), making it the most likely candidate to produce
  a clean signal at N=1.
- **Statistical power context**: The MDE at 80% power, α=0.05, with σ≈2.4pp (within-run
  replication SD from prior work) is ≈6.7pp. We are not powered to detect the 0.63pp gap
  to GEPA reliably. We are running four targeted attacks because: (a) budget permits it,
  (b) each run independently has a non-trivial chance of exceeding GEPA if the hypothesized
  mechanisms are real, and (c) a positive result from any single run is informative even if
  not statistically confirmed at conventional levels.

**The experiment is hypothesis-motivated, not statistically powered.** A single run above
GEPA is treated as SUGGESTIVE requiring follow-up replication (N ≥ 3), consistent with the
SUGGESTIVE→POSITIVE→adoption ladder established in prior experiments. With four runs tested
against the same threshold, the probability of at least one spurious crossing by noise alone
is approximately 4× the single-run probability; the replication requirement directly controls
this multiplicity.

---

## 8. Statistical Test

**Primary test (GEPA comparison, all runs)**:
- Threshold: test EM ≥ 62.3% = GEPA (absolute). This is deterministic (pass/fail), not a
  statistical test. No p-value is computed for a single run vs. a fixed external benchmark.
- Verdict levels:
  - STRONG POSITIVE: test EM ≥ 63.0% (clearly above GEPA + noise margin)
  - POSITIVE: test EM in [62.3%, 63.0%)
  - SUGGESTIVE: test EM in [61.5%, 62.3%) with gap reduction ≥ 2.0pp vs. prior best (Run F)
  - NULL: test EM < 61.5%

**Gate C test (Run B vs. Run O, gap reduction)**:
Pre-registered threshold (carried over from val_gap experiment, Gate C): Δ gap ≥ 2.0pp.
- POSITIVE: gap_B < gap_O − 2.0pp AND test EM(B) ≥ 60.0%
- SUGGESTIVE: Δ gap ∈ [1.0pp, 2.0pp) AND test EM(B) ≥ 60.0%
- NULL: |Δ gap| < 1.0pp
- NEGATIVE: gap_B > gap_O (Run B inflates the gap)

**Gate C supplemental — Run C (F1/600 vs. F1/300)**:
Comparison: test EM(C) vs. test EM(F=61.67%). Run C is the highest-leverage run for GEPA.
- POSITIVE: test EM(C) ≥ 62.3%
- SUGGESTIVE: test EM(C) ∈ [61.7%, 62.3%) with gap_EM(C) < 1.5pp (gap maintained or
  further compressed vs. Run F's 1.66pp)
- NULL: test EM(C) < 61.7%

**Run A test (F1 + NLP combination vs. F1-only)**:
Comparison: test EM(A) vs. test EM(F=61.67%). The deconfounding test for NLP prompts on
F1 fitness.
- POSITIVE: test EM(A) ≥ 62.3%
- SUGGESTIVE: test EM(A) ∈ [61.7%, 62.3%)
- NULL: test EM(A) < 61.7%
- NEGATIVE: test EM(A) < 61.0% (NLP prompts harm F1 fitness runs)

**Significance threshold**: α = 0.05 is not applicable at n=1. All verdicts are
observational classifications under the SUGGESTIVE/POSITIVE/NULL/NEGATIVE ladder.
Follow-up with N ≥ 3 is required before any POSITIVE result crosses to adoption.

**How computed**: All test evaluations use `run_test_eval.sh` with sha256 verification
of evaluation script (carried over from val_gap; document sha256 in 03_plan.md). Thinking
mode verification (presence of `<think>` blocks) required at eval launch. **Binomial 95%
CIs will be computed for all runs regardless of proximity to 62.3%**, reported in
Section 5 of the results document. No bootstrapping is planned (n=300 is adequate for
point estimates via the normal approximation).

---

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| **Compound treatment in Run A** (F1 fitness + NLP prompts simultaneously changed) | Cannot separately attribute any test EM improvement to F1 vs. NLP prompts | Design is intentional — testing the combination, not isolating components. The F1-only reference (Run F, test EM 61.67%) provides the F1-without-NLP baseline; the combination can be measured against it even if components cannot be separated. If A >> F, follow-up decomposition is warranted. |
| **Compound treatment in Run C** (F1 fitness + 600 samples simultaneously changed) | Cannot separately attribute improvement to fitness vs. sample size | Design is intentional — parallel to Run A. Run B provides the 600-only baseline; Run F provides the F1-only baseline. Comparison of {A, B, C, D} to {O, F} allows partial decomposition at the group level even at N=1 per cell. |
| **`static_f1_600` is a new, untested problem directory** | Code errors, missing `valid_frontier_em` key, incorrect fitness computation | Pre-registered mitigation: dry-run verification at gen 0 before full launch. Must confirm val F1 > 0, val EM tracked separately, dataset length = 600 in logs. |
| **Run F as reference has N=1 and 52.4% invalidity** | Run F may have been atypically lucky (single-measurement) | Use Run F as reference for relative comparisons but note the uncertainty. Gate E was SUGGESTIVE, not POSITIVE, precisely because N=1. Runs A/C use F1 fitness on the same seed; if A < F despite being the combination, the signal is clear. |
| **Server load asymmetry** (Runs B/C/D share chain servers that are also used for inference) | Slower eval → higher invalidity rate for 600-sample runs | Monitor invalidity rate at gen 5; alert if > 30%. Each run has a dedicated chain LLM server and a dedicated mutation LLM server. |
| **NLP prompts silent failure** (prompts_dir bug fixed at 920c975) | If pipeline YAML missing `prompts_dir` in `evolution_context`, Runs A/D would silently use default prompts | Explicit verification: `python run.py --cfg job` for Runs A and D must show **two distinct** `prompts_dir: .../hotpotqa` entries — one under `evolution_context` and one under `mutation_operator`. A single entry or any `prompts_dir: null` means the bug has re-appeared. Do not launch. |
| **Stagnation pattern** (confirmed in 7 prior runs, frontier peaks at birth-gen 4–6) | All four runs may stagnate before gen 10, producing test EM ≈ 61.0–61.7% regardless of treatment | Cannot be mitigated within the current single-parent framework. P3 crossover (num_parents=2) is the structural fix; this experiment explores whether prompt/fitness changes can push past the ceiling before P3 is launched. The stagnation confirmation is itself a scientific result. |
| **Warm-start seed ddce37b4 specific to EM fitness** | The ddce37b4 seed was evolved under EM fitness; using it as warm-start for F1 runs (A, C) introduces a fitness-distribution mismatch at gen 0 | Unavoidable with a single warm-start seed. Mitigation: inspect gen-0 val F1 for A and C at dry-run; expected ≈ 70.27% (matching static_f1 gen-0; val F1 and val EM are not comparable numbers). For Run C (600-sample F1), expected gen-0 val F1 ≈ 68–72%. Accepted mismatch. |
| **Chain server context window** | 600-sample runs generate longer history contexts; may exceed 32768 ctx limit | Verify `max_model_len=32768` at chain server restart. 600-sample eval does not change per-sample context; only the number of samples changes. No additional risk for Runs B/C/D vs. A. |

---

## 10. Stop Criteria

### Stagnation-based early completion (600-sample runs B, C, D)

If the frontier val fitness has not improved for ≥ 10 consecutive generations, the run
may be terminated early. Results are reported on the full archive at the point of termination.
This is **not an invalidation** — it is an early completion under the confirmed stagnation
pattern (frontier peaks at birth-gen 4–6 in all prior single-parent runs). The 25-gen
pre-registered cap already reflects this; early completion before gen 25 is permitted if
stagnation is confirmed. Stagnation is confirmed when `valid_frontier_fitness` shows no
improvement for 10 consecutive gens in the Redis history key.

For Run A (300-sample, 50 gens): the same stagnation criterion applies, but at 50 gens the
run is already half the prior budget; allow it to complete to gen 50 unless invalidity rate
triggers early termination.

### Early termination
- **Invalidity rate > 50% at gen 5 for any 600-sample run (B, C, D)**: Pause that run;
  diagnose whether stage_timeout=6000 is being exceeded. If median eval time per program
  exceeds 5000s at gen 5, increase stage_timeout to 8000 before resuming. Do not continue
  past gen 5 with > 50% invalidity — this was the failure mode of Run Q (val_gap).
- **Invalidity rate > 30% at gen 5 for 300-sample runs (A)**: Alert only; do not pause.
  Run O had 24.3% invalidity; Run F had 52.4%. Up to 40% is acceptable for Run A given the
  F1 fitness precedent from Run F.
- **Gen-0 val fitness sanity failure**: If any run shows val fitness = 0.0 or val EM = 0.0
  at gen 0, stop and diagnose before proceeding. Expected: val EM ≈ 60.0% (seed value) for
  all runs at gen 0; val F1 ≈ 70.27% for F1 runs (cf. Run F gen-0 in val_gap).
- **NLP prompts verification failure**: If `python run.py --cfg job` for Run A or D shows
  `prompts_dir` missing from `evolution_context`, do not launch. Fix pipeline YAML and
  re-verify before launch.
- **`static_f1_600` dry-run failure**: If Run C gen-0 does not populate `valid_frontier_em`
  in Redis, do not continue. Fix the validate.py and re-verify before proceeding.

### Run invalidation criteria
A run is invalidated (excluded from all gate analyses) if any of the following apply:
1. Thinking mode not active: `<think>` blocks absent from ≥ 5% of chain outputs at gen 1.
2. `pipeline=standard` used (repr-contamination bug).
3. Invalidity rate > 90% at gen 10 (Run Q precedent: run cycled through 50 gens with
   ~0 valid programs; no useful archive formed).
4. Warm-start seed differs from `ddce37b4`.
5. Val set contamination: test samples observed in val set (must not happen with fixed
   sequential val from train split).
6. `prompts_dir` missing from pipeline YAML for any run using `prompts=hotpotqa` (Runs A, D).

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time (300-sample runs A) | ~25h (50 gens × ~244s/eval / 4 workers × overhead ≈ 24.6h; cf. Run F: 24.62h) |
| Wall time (600-sample runs B, C, D) | **~25h each** (25 gens × 2 phases × ~1412s mean/eval / 4 workers ≈ ~17.7h + overhead; conservative upper bound 30h. Stagnation-based early completion may reduce further.) |
| Total wall time (all 4 runs, parallel) | **~30h wall-clock** (bottleneck: 600-sample runs at 25 gens) |
| Redis DBs | 8, 9, 10, 11 (4 DBs) |
| Mutation LLM servers | 4 × Qwen3-235B-A22B-Thinking (one per run) |
| Chain LLM servers | 4 × Qwen3-8B thinking (one per run, 2 per host) |
| Test eval time | ~5 min each × 4 runs = ~20 min total |
| New code | `problems/chains/hotpotqa/static_f1_600/` (new problem directory, ~1h) |

**Note on 600-sample wall time**: The val_gap Run Q empirical mean was ~1412s per program,
with a max of ~2289s. At 8 mutations/gen, 4 async workers, and 50 generations, the theoretical
minimum is 50 × 2 × 1412s / 4 ≈ 35h. With overhead, dropout, and retry, 50h is a realistic
estimate. 600-sample runs will be the bottleneck; monitor for progress by gen 10.

---

## 12. Open Questions / Risks

### Priority risks

**Risk 1 — `static_f1_600` implementation bug.** This is the highest-risk item. Run C
requires a new problem directory that combines F1 fitness with 600-sample validation.
If the `valid_frontier_em` Redis key is not populated (required for within-metric gap
analysis) or if the F1 computation is applied incorrectly over the 600-sample batch, Run C
is invalidated. Mitigation: implement `static_f1_600` as a clean composition of `static_f1`
and `static_600`, add a unit test for the validate.py, and verify at dry-run with the
following pre-registered expected ranges:

- **Expected gen-0 val F1 ≈ 68–72%** (based on static_f1 gen-0 val F1 = 70.27%; 600-sample
  mean is the same distribution, lower variance, so the point estimate should be near 70.27%
  with tighter noise). Halt and diagnose if gen-0 val F1 < 65% or > 75%.
- **Expected gen-0 val EM ≈ 59–61%** (based on seed program ddce37b4 test EM = 60.0%;
  val EM on the first 600 train samples should closely match). Halt and diagnose if
  gen-0 val EM < 57% or > 63%.
- Verify that val F1 and val EM are computed over the same 600 samples (not a 300-vs-600
  discrepancy from a copy-paste error in `valid_frontier_em` population logic).

**Risk 2 — 600-sample stage_timeout misconfiguration for Runs B/C/D.** Run Q (val_gap) was
invalidated precisely by stage_timeout=2400 being too short. We are using stage_timeout=6000,
which provides 2.6× margin over the observed max of ~2300s. However, if the chain servers
have higher load this time (e.g., higher throughput leads to more LLM variance), individual
programs could exceed 6000s. Mitigation: monitor invalidity rate at gen 5 (alert > 50%);
if needed, re-launch with stage_timeout=8000. Do not proceed past gen 5 with > 50% invalidity.

**Risk 3 — NLP prompts silent failure (prompts_dir missing).** Fixed at 920c975 but must be
re-verified at every launch with `prompts=hotpotqa`. A silent failure here would mean Runs
A and D use default prompts, making them identical to existing runs and producing no new
scientific information. This is a wasted run, not a confound — but it is a costly waste.
The `python run.py --cfg job` verification step is mandatory, not optional.

**Risk 4 — F1+NLP combination is harmful rather than additive.** NLP prompts were designed
around EM task framing. The `static_f1/task_description.txt` provides F1-objective framing
to the mutation LLM. If NLP prompts (designed for the EM landscape) inject conflicting
objectives into the mutation LLM when paired with F1 fitness, Run A could score below Run F.
This is a genuine scientific risk. Mitigation: review the NLP prompt files before launch
to confirm they do not assume EM scoring in ways that conflict with F1 task framing.
If NLP prompts hard-code "maximize exact match" phrases, they must be updated for consistency
with the F1 objective before Run A launches. This constitutes a pre-registered change and
must be documented as Amendment 1 if executed.

### Scientific open questions after this experiment

- If Gates A/C succeed (F1 fitness exceeds GEPA): Does the NLP component in Run A add value
  beyond Run C? Requires comparing test EM(A) vs test EM(C) (both fixed at N=1, but the
  direction of the difference is informative for planning Run-A follow-up).
- If Gate B succeeds (600-sample gap reduction): Does F1+600 (Run C) add further improvement?
  The interaction term (F1 × 600) can be estimated by comparing C vs B (600-only effect under
  F1) and C vs F (600-only effect on top of F1), even at N=1 per cell.
- If all gates fail: This is the strongest evidence yet that single-parent stagnation (birth-gen
  4–6 ceiling) is the binding constraint, and P3 crossover (num_parents=2) should be
  prioritized immediately.

---

## Appendix: Decision Tree

```
After gen-50 test evals:

                          Any run ≥ 62.3%?
                         /                \
                       YES                 NO
                        |                  |
         Identify which run(s)     Check best test EM
                        |                  |
             Run A ≥ 62.3% ?      Best ∈ [61.5, 62.3)?
             → NLP + F1 wins       → SUGGESTIVE; replication
             → replicate (N≥3)       with N≥3 on best config
                        |                  |
             Run C ≥ 62.3% ?      Best < 61.5%?
             → F1 + 600 wins       → NULL; P3 crossover
             → Gate C closed         experiment next
                        |
             Run B ≥ 62.3% ?
             → EM + 600 alone
               sufficient
             → adopt static_600
               as new baseline
```

*Ready for Reviewer-2's scrutiny.*
