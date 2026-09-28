# Experimental Design: Crossover — Run D Replication + num_parents=2 Stagnation Attack

**Date**: 2026-03-08
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Revised — resubmitted for Phase 2 approval (addresses C1, M1, M2, m1–m5 from
`02_review.md`; adds Run S as concurrent single-parent control for Run R)

---

## 1. Research Question

The push experiment (PR #73) produced two results that demand follow-up: (1) Run D (F1+NLP+600,
num_parents=1) achieved 63.00% test EM — the first GigaEvo result above GEPA (62.3%) — but is
exploratory due to Amendment 3's mid-run fitness switch; (2) stagnation was confirmed for the
11th consecutive independent run, with every frontier peak occurring at birth-generation 4–8
regardless of fitness metric, sample size, or mutation prompt. Single-parent mutation cannot
escape the local-optima basin. This experiment addresses both findings with a single, focused
design.

**Primary research question 1 (replication)**: Does the F1+NLP+600 configuration reliably
produce test EM above GEPA (62.3%) in a clean, pre-registered single-parent run free of
mid-run amendments?

**Primary research question 2 (crossover)**: Does two-parent crossover (num_parents=2) break
the stagnation wall and push test EM above the confirmed single-parent ceiling (63.00%), when
applied in the best-performing configuration (F1+NLP+600)?

**Secondary research question 1**: Does two-parent crossover in the default-prompt configuration
(F1+default+600) outperform its concurrent single-parent control (Run S), providing evidence
that crossover's benefit is robust to the choice of mutation prompts?

**Secondary research question 2**: Does F1+NLP+600 outperform F1+default+600 at 600-sample
validation with num_parents=1, giving a clean within-experiment estimate of the NLP-prompt
effect at this resolution?

---

## 2. Hypotheses

### Run P — Clean Run D Replication (F1+NLP+600, num_parents=1)

**H0(P)**: A clean, pre-registered single-parent run under F1+NLP+600 conditions produces
test EM <= 62.3% (GEPA). That is, Run D's 63.00% was a statistical artifact of the Amendment 3
confound (discarded gen 1–3 data, mid-run fitness switch) and/or single-measurement noise, and
does not replicate cleanly.

**H1(P)**: A clean F1+NLP+600 single-parent run achieves test EM >= 62.3% (GEPA), confirming
that Run D's result was not an artifact. The mechanistic claim: F1 fitness suppresses val EM
overfit (Gate E, SUGGESTIVE), NLP prompts improve mutation quality at 600-sample resolution
(observed D–C gap = +4.33pp, McNemar p=0.049), and their combination on a low-noise 600-sample
fitness signal reliably reaches the GEPA frontier.

**Effect size that matters**: Test EM >= 62.3% is the minimum meaningful threshold. Test EM >=
63.0% (matching Run D) would be STRONG POSITIVE. Test EM in [61.5%, 62.3%) is SUGGESTIVE if
the val-test gap is <= 2.0pp (pattern consistent with Run D), and PARTIAL NULL if gap > 2.0pp
(near-GEPA on EM but gap-suppression mechanism failed).

### Run Q — F1+NLP+600, num_parents=2 (crossover in best config)

**H0(Q)**: Two-parent crossover under F1+NLP+600 conditions produces test EM no higher than
the single-parent counterpart (Run P). Formally: test EM(Q) - test EM(P) <= 0pp.

**H1(Q)**: F1+NLP+600 with num_parents=2 exceeds the single-parent result by >= 2.4pp (test
EM(Q) - test EM(P) >= +2.4pp). Mechanistic logic: single-parent mutation is trapped in the
ddce37b4 fitness basin (confirmed: all 11 prior runs peak at birth-gen 4–8 with no subsequent
improvement). With num_parents=2 and max_elites=8, AllCombinationsParentSelector generates
C(8,2)=28 pair combinations per generation (capped at max_mutations=16), each asking the
mutation LLM to synthesize two distinct elite programs. This recombination creates offspring
that sample combinatorially new regions of program space that are inaccessible via single-parent
mutation — enabling post-stagnation frontier improvement.

**Effect size that matters**: Delta >= +2.4pp (exceeds the empirical retest noise floor; see
Section 7). Delta >= +5.0pp (approaches 2 SEs at n=300) would constitute strong evidence for
the crossover mechanism. Note: due to throughput non-equivalence (16 vs. 8 mutations/gen), a
result in the range [+2.4pp, +5.0pp) is classified as throughput-confounded and requires
follow-up to isolate the crossover quality effect; see Section 8 Test 2.

**Secondary stagnation hypothesis (H1_stag_Q)**: Run Q exhibits frontier improvement after
birth-gen 10 in at least 5 consecutive generations, whereas Run P (single-parent) stagnates
by gen 8. Stagnation is measured from the `valid_frontier_fitness` Redis key trajectory.

### Run R — F1+default+600, num_parents=2 (crossover without NLP prompts)

**H0(R)**: Two-parent crossover under F1+default+600 conditions produces test EM no higher
than the concurrent single-parent control under the same conditions (Run S). Formally:
test EM(R) - test EM(S) <= 0pp.

**H1(R)**: F1+default+600 with num_parents=2 exceeds the concurrent single-parent result
(Run S) by >= 2.4pp. Mechanistic logic: crossover's benefit (combinatorial offspring diversity)
is independent of mutation prompt choice. If crossover adds value in the NLP-prompt setting
(Run Q > Run P), it should also add value in the default-prompt setting (Run R > Run S),
confirming that the mechanism is structural (recombination) rather than prompt-specific.

**Effect size that matters**: Delta (R - S) >= +2.4pp (minimum detectable, noise-floor criterion).
Delta >= +5.0pp would strongly support the crossover mechanism independently of the NLP-prompt
interaction.

### Run S — F1+default+600, num_parents=1 (concurrent control for Run R)

**H0(S)**: There is no pre-specified null for Run S in isolation — it functions as a concurrent
control for Run R and as the default-prompt baseline for comparison with Run P.

**H1(S)** (informal, for power planning): Test EM(S) should be consistent with push Run C's
58.67% (same condition, same seed, same infrastructure). A large deviation in either direction
(|test EM(S) - 58.67%| > 5pp) would indicate infrastructure instability or dataset drift and
would be reported as an anomaly.

### Informal composite summary (not a pre-registered test)

Across Runs P, Q, R, S, the overarching ambition is: (a) confirm Run D's 63.00% as replicable,
and (b) demonstrate that crossover pushes the frontier beyond what single-parent mutation can
reach. At least one crossover run (Q or R) exceeding its matched single-parent control by >=
+2.4pp, AND at least one absolute result >= 63.5%, would constitute a landmark pair of findings.
This is an informal characterization of the experiment's ambition, not a pre-registered test.
Individual verdicts are determined by Tests 1–5 in Section 8.

### Primary comparison hierarchy

**Run P is the experiment-level primary for the replication question.** Its verdict determines
whether Run D's result enters the confirmed GigaEvo knowledge base.

**Run Q vs. Run P is the experiment-level primary for the crossover question.** The
within-experiment comparison (Q - P) is the cleanest isolation of the crossover effect because
P and Q share all conditions except num_parents and max_mutations, and run simultaneously on
the same infrastructure.

**Run R vs. Run S is the primary secondary comparison for crossover robustness.** Run S runs
concurrently under the same condition as Run R but with num_parents=1, eliminating the
cross-experiment confound that the previous draft carried by using push Run C as the reference.

**Run P vs. Run S is the secondary NLP-prompt test at 600 samples.** Both are single-parent
runs on the same infrastructure; their comparison directly estimates the NLP-prompt effect at
F1+600 without the Amendment 3 confound of push Run D vs. push Run C.

---

## 3. Independent Variables

| Variable | Control value | Treatment value(s) | Runs |
|----------|---------------|--------------------|------|
| `num_parents` | 1 (single-parent mutation) | 2 (two-parent crossover, AllCombinations) | P, S (control); Q, R (treatment) |
| `prompts` | `default` (generic GigaEvo optimizer) | `hotpotqa` (NLP-specific) | S, R (`default`); P, Q (`hotpotqa`) |

This is a complete 2×2 factorial at F1+600 fitness:

|  | `prompts=hotpotqa` | `prompts=default` |
|---|---|---|
| **num_parents=1** | P (new) | S (new) |
| **num_parents=2** | Q (new) | R (new) |

All four cells are filled by concurrent runs on the same infrastructure. Push Run C
(F1+default+600, num_parents=1, 58.67%) is a reference data point for context; Run S
supersedes it as the within-experiment control.

**Fixed across all new runs**: F1 fitness (`chains/hotpotqa/static_f1_600`), 600-sample
validation, `pipeline=hotpotqa_asi`. The fitness × sample-size cell is fixed at the
configuration established by push Run D as optimal.

**Why not also test EM fitness with crossover?** The push experiment established that EM fitness
at 600 samples produces a large val-test gap (+7.67pp for Run B) and lower test EM than F1
fitness at 600 samples. EM+600+crossover would inherit that gap-inflation mechanism. All four
chain server endpoints are now consumed by the 2×2 F1+600 factorial, which covers the
scientifically highest-value cells.

---

## 4. Dependent Variables

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Test EM at gen 25 (best-by-val) | 300-sample held-out test set; EM scoring; thinking mode Qwen3-8B | YES — primary for all runs |
| Val-test gap (within-metric EM) | val EM (from `valid_frontier_em` Redis key) minus test EM | YES — secondary |
| Val frontier trajectory (gen 1–25) | Per-generation `valid_frontier_fitness` (F1) from Redis | No — stagnation diagnostic |
| Val EM trajectory (gen 1–25) | Per-generation `valid_frontier_em` from Redis | No — gap diagnostic |
| Birth-generation of frontier program | Birth-gen of best-by-val program at run end | No — stagnation diagnostic |
| Post-stagnation improvement indicator | Whether val frontier improves after birth-gen 10 | No — crossover mechanism test |
| Invalidity rate at gen 5 | Fraction of invalid programs per run | No — monitoring |
| Mutations per generation (Q, R only) | Actual vs. expected (cap at 16; verify via logs) | No — crossover throughput verification |

**Primary metric**: Test EM at final generation (gen 25), best-by-val program, evaluated on
the fixed 300-sample held-out test set, thinking mode Qwen3-8B. Consistent with all prior
experiments and the GEPA benchmark (62.3%).

**Val EM note for all runs (F1 fitness)**: Val fitness is F1, but the primary metric is test
EM. The `valid_frontier_em` Redis key is populated by `static_f1_600/validate.py` (confirmed
working in push Run D). Val EM (not val F1) is used for the within-metric gap analysis.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Chain topology | 6-step fixed (2 tool, 4 LLM) | Unchanged across all experiments |
| Fitness metric | F1 (token-level partial credit) | Best-performing push condition; fixed for all 4 runs |
| Validation sample size | 600 (fixed, first 600 train samples) | Best-performing push condition; fixed for all 4 runs |
| `problem.name` | `chains/hotpotqa/static_f1_600` | Required for F1+600; already implemented and tested in push |
| Chain LLM | Qwen3-8B, thinking mode ON (default chat template) | Required for GEPA comparison |
| Mutation LLM | Qwen3-235B-A22B-Thinking, one server per run | Consistent with all prior runs |
| `pipeline` | `hotpotqa_asi` | Required for all hotpotqa variants; never `standard` |
| Warm-start seed | `ddce37b4` (val EM 62.7%, test EM 60.0%) | Same seed as all prior runs; leapfrog continuation |
| Leapfrog init | Top programs from ddce37b4 run, re-scored under F1 fitness at gen 0 | Standard continuation; F1 re-scoring at gen 0 is expected (seed evolved under EM) |
| `max_elites_per_generation` | **8** — **requires explicit Hydra override** | Default in `config/constants/evolution.yaml` is **5**, not 8. Must set `max_elites_per_generation=8` explicitly in every launch command. See C1 note below. |
| `max_mutations_per_generation` | **16 for Q and R** (crossover); **8 for P and S** (single-parent) | See throughput note below |
| `mutation_mode` | `rewrite` | Required; `diff` mode raises `MutationError` for multiple parents |
| `parent_selector` | `AllCombinationsParentSelector` | Standard; handles both num_parents=1 and num_parents=2 with built-in fallback |
| Validation protocol | Fixed sequential (first 600 train samples) | Rotation permanently excluded |
| `stage_timeout` | 6000 (all runs) | 600-sample eval empirical max ~2300s; 6000 provides 2.6× margin |
| `dag_timeout` | 9000 (all runs) | stage_timeout (6000) + mutation LLM stages (~1500) + headroom (1500) |
| `max_generations` | 25 (all runs) | Stagnation confirmed by gen 8 in all 11 prior single-parent runs; 25 gens provides 3× the stagnation window. Crossover-driven improvement should be detectable by gen 20 if the mechanism is real. |
| Test evaluation | Fixed 300-sample test set; thinking mode verified | Consistent with all prior runs |
| Random failure sampling | All failures returned from validate.py; formatter samples 10 with NO_CACHE | Required; cf0cfc1 |
| HTTP timeout | 600s (`httpx.Timeout(timeout=600.0)`) | Required for 600-sample runs; fixed at c0186a8 |
| `step_max_tokens` | 8192 for all LLM steps | Uniform; thinking mode exhausts budget — do not reduce for steps 3/6 |

**[C1] Note on `max_elites_per_generation=8` — explicit override required**:

`config/constants/evolution.yaml` sets `max_elites_per_generation: 5` as the default. The
value 8 has been used in all prior HotpotQA experiments (push, val_gap) via an explicit Hydra
override in the launch command. If this override is omitted, all four runs will execute with
max_elites=5, not 8. The consequences:

- Runs Q and R (num_parents=2): C(5,2)=10 parent pairs, capped at 16 → 10 mutations/gen
  (not 16). The throughput ratio vs. single-parent becomes 10:5 rather than 16:8.
- Runs P and S (num_parents=1): 5 mutations/gen (capped at 8 → 5), not 8.

Every launch command must include `max_elites_per_generation=8`. The mandatory `--cfg job`
pre-launch check must confirm `max_elites_per_generation: 8` in the resolved config for all
four runs. This is the highest-priority verification item alongside `num_parents=1` for Runs
P and S.

**Throughput note on `max_mutations_per_generation` for crossover runs (Q, R)**:

The prior p3_crossover design (2026-03-04) capped both single-parent and crossover runs at
8 mutations/gen to equalize throughput. This design makes a different choice: crossover runs
(Q, R) use max_mutations=16, while single-parent runs (P, S) use max_mutations=8.

Rationale: the scientific question here is *whether crossover breaks stagnation in practice*,
not whether crossover quality per mutation is superior under equalized throughput. With
num_parents=2 and max_elites=8, AllCombinationsParentSelector generates C(8,2)=28 parent pairs;
capping at 16 admits roughly the first 16 shuffled combinations. This gives crossover its
natural throughput advantage (2x), making stagnation-breaking behavior easier to detect. The
throughput confound is real and acknowledged (see Section 9 and Section 8 Test 2 verdict labels).
A positive result (Q > P or R > S by >= 2.4pp) triggers a throughput-equalized follow-up
(max_mutations=8 for all four num_parents values) to isolate crossover quality from search volume.

**This is a pre-registered design choice, not a post-hoc rationalization.** Section 8 Test 2
verdict labels are harmonized with this note: a delta in [+2.4pp, +5.0pp) with McNemar p < 0.05
is labeled "POSITIVE (THROUGHPUT CONFOUNDED)" — not a plain POSITIVE — and requires
throughput-equalized follow-up before the crossover mechanism claim can be made.

---

## 6. Run Design Table

| Run | Label | `redis.db` | `pipeline` | `prompts` | `problem.name` | `num_parents` | `max_elites` | `max_mut` | `stage_timeout` | `dag_timeout` | `max_gen` | Val N | Fitness |
|-----|-------|-----------|-----------|-----------|----------------|--------------|-------------|-----------|----------------|--------------|----------|-------|---------|
| P | cross-P | 0 | `hotpotqa_asi` | `hotpotqa` | `chains/hotpotqa/static_f1_600` | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |
| Q | cross-Q | 1 | `hotpotqa_asi` | `hotpotqa` | `chains/hotpotqa/static_f1_600` | 2 | **8** | 16 | 6000 | 9000 | 25 | 600 | F1 |
| R | cross-R | 2 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | 2 | **8** | 16 | 6000 | 9000 | 25 | 600 | F1 |
| S | cross-S | 3 | `hotpotqa_asi` | `default` | `chains/hotpotqa/static_f1_600` | **1** | **8** | 8 | 6000 | 9000 | 25 | 600 | F1 |

**Bold values require explicit Hydra overrides** (not defaults): `num_parents=1` for P and S
(default is 2); `max_elites_per_generation=8` for all four runs (default is 5).

**Combinatorics verification** (contingent on `max_elites_per_generation=8` override):

| Run | num_parents | max_elites | Parent combinations | max_mutations | Actual mut/gen at archive maturity |
|-----|------------|-----------|---------------------|--------------|----------------------------------|
| P | 1 | 8 | C(8,1) = 8 | 8 | 8 |
| Q | 2 | 8 | C(8,2) = 28 | 16 | 16 (capped) |
| R | 2 | 8 | C(8,2) = 28 | 16 | 16 (capped) |
| S | 1 | 8 | C(8,1) = 8 | 8 | 8 |

Throughput ratio (crossover vs. single-parent): 16:8 = 2× (Q vs. P; R vs. S).

**Chain LLM assignment** (one chain server per run, no sharing):

| Run | Chain LLM URL |
|-----|---------------|
| P | `http://10.226.17.25:8001/v1` |
| Q | `http://10.226.17.25:8000/v1` |
| R | `http://10.225.185.235:8001/v1` |
| S | `http://10.225.185.235:8000/v1` |

**Mutation LLM assignment** (one per run, from the 4-server pool):

| Run | Mutation LLM URL |
|-----|------------------|
| P | `http://10.226.72.211:8777/v1` |
| Q | `http://10.226.15.38:8777/v1` |
| R | `http://10.226.185.131:8777/v1` |
| S | `http://10.225.51.251:8777/v1` |

**Redis DBs**: 0, 1, 2, 3. Verify 0 keys in all four DBs before launch (DBs 0–3 were used by
nlp_prompts experiment PR #69; flushed per memory notes but must be re-confirmed).

**Reference (not re-run, for context only)**:
- Push Run C (F1+default+600, num_parents=1): test EM = 58.67%, val EM = 62.83%, gap = +4.17pp
- Push Run D (F1+NLP+600, num_parents=1, Amendment 3): test EM = 63.00%, val EM = 64.83%, gap = +1.83pp

---

## 7. Sample Size Justification

**N=1 per cell.** This is the same constraint as all prior GigaEvo HotpotQA experiments.

At n=300 test samples with p~0.62, the binomial SE is approximately sqrt(0.62×0.38/300) ≈
2.80pp per run. The 95% CI width is approximately ±5.5pp per run, making individual-run
comparisons unreliable for small effects (< 3pp).

**Noise floor calibration — and its limitation**:

The empirical retest noise floor of 2.4pp cited in the p3_crossover design (2026-03-04) was
measured as the spread between two evaluations of the ddce37b4 seed program on the same n=300
test set, with `step_max_tokens=2048`. The current experiment uses `step_max_tokens=8192`
throughout. Under thinking mode, larger token budgets allow longer reasoning chains, which can
produce different LLM non-determinism patterns: longer thoughts may improve consistency on
simpler questions (reducing sampling variance) while introducing new variance on complex
multi-hop items where extended reasoning explores divergent paths.

**The 2.4pp threshold is therefore a calibration transfer across evaluation configurations.**
The direction of the bias is unknown. Concretely:

- If the true noise floor at step_max_tokens=8192 is higher (e.g., 3.5pp), then a delta of
  +3.0pp would be below the actual noise floor despite being classified POSITIVE (THROUGHPUT
  CONFOUNDED) under the pre-registered table.
- If the true noise floor is lower (more consistent thinking chains), the 2.4pp threshold is
  conservative and safe.

**Mitigation**: Results in the borderline zone delta ∈ [+2.4pp, +3.5pp) will be flagged with
an explicit cautionary note in the Phase 5 results document: "Delta is above the 2.4pp retest
noise floor measured at step_max_tokens=2048, but within a plausible noise range for
step_max_tokens=8192. This result should be treated as SUGGESTIVE pending same-setting
recalibration." The McNemar test (item-level, not affected by the noise floor assumption) is
the primary statistical instrument precisely because it does not rely on calibrated thresholds.
Results with McNemar p < 0.05 provide evidence independent of the noise-floor transfer.

**What N=1 can establish**:

1. **Replication verdict for Run P**: Test EM(P) >= 62.3% confirms that Run D's result
   replicates under clean pre-registration. Test EM(P) < 61.5% indicates Amendment 3 was
   material. N=1 limits causal claims but the pre-registration itself is the scientific
   contribution — any outcome advances the knowledge state.

2. **Crossover verdict for Q vs. P and R vs. S**: Within-experiment, concurrent comparisons
   on identical infrastructure. If Q - P >= +2.4pp (McNemar p < 0.05), the result exceeds
   the noise floor and provides evidence for the crossover mechanism (subject to throughput
   confound; see Section 9).

3. **NLP-prompt effect at F1+600**: P vs. S (concurrent) gives the cleanest within-experiment
   estimate of the NLP-prompt effect at 600 samples under num_parents=1.

4. **McNemar test**: Item-level comparison on the shared 300-sample test set is more powerful
   than CI overlap for detecting small true differences. It is the primary statistical instrument
   for Tests 2, 3, and 5.

**Formal power**: Approximately 20–30% at N=1 for a true 2.4pp effect. This experiment is
a targeted screening study, not a confirmatory test. All POSITIVE results require throughput-
equalized replication before mechanism claims can be published.

---

## 8. Statistical Test

### Test 1: Run P replication verdict

Threshold comparison against GEPA (62.3%) — deterministic classification, no p-value.

| Test EM(P) | Val-test gap | Verdict |
|-----------|-------------|---------|
| >= 63.0% | any | STRONG POSITIVE — Run D result confirmed and exceeded |
| [62.3%, 63.0%) | any | POSITIVE — Run D result confirmed; GEPA beaten cleanly |
| [61.5%, 62.3%) | <= 2.0pp | SUGGESTIVE — near-GEPA; gap consistent with Run D's low-gap pattern |
| [61.5%, 62.3%) | > 2.0pp | PARTIAL NULL — near-GEPA on EM but gap-suppression mechanism failed; F1+NLP+600 does not reliably produce the low-gap regime observed in Run D |
| < 61.5% | any | NULL — Run D result does not replicate; Amendment 3 was material |

### Test 2: Crossover verdict — Run Q vs. Run P

**Test**: McNemar's test on matched item-level predictions (300 items, binary EM scores).
One-sided (Q better than P). Pre-registered significance threshold: p < 0.05.

**Effect size classification** (delta = test EM(Q) - test EM(P)):

| Delta | McNemar p | Verdict |
|-------|-----------|---------|
| >= +5.0pp | p < 0.05 | STRONG POSITIVE — crossover clearly breaks stagnation ceiling; throughput advantage alone cannot explain a 5pp gain |
| [+2.4pp, +5.0pp) | p < 0.05 | **POSITIVE (THROUGHPUT CONFOUNDED)** — crossover exceeds noise floor under 2× throughput advantage. Requires throughput-equalized follow-up (max_mutations=8 for both) to attribute gain to crossover quality vs. search volume. |
| [+2.4pp, +5.0pp) | p >= 0.05 | SUGGESTIVE — exceeds retest noise floor but McNemar non-significant; replicate |
| (-2.4pp, +2.4pp) | any | NULL — no detectable crossover benefit at this sample size and throughput |
| <= -2.4pp | any | NEGATIVE — crossover harms performance |

**Borderline caution zone [+2.4pp, +3.5pp)**: Due to the noise-floor calibration transfer
(2.4pp measured at step_max_tokens=2048, this experiment uses 8192), results in this sub-range
carry additional uncertainty. See Section 7. Such results will be explicitly flagged in Phase 5
regardless of the verdict category.

**Note**: McNemar p < 0.05 without delta >= +2.4pp would be classified NULL — statistical
significance is not sufficient without exceeding the noise floor. Both conditions are required
for any POSITIVE classification.

### Test 3: Crossover verdict — Run R vs. Run S (within-experiment)

**Test**: McNemar's test on matched item-level predictions (R and S share the same test set;
both evaluated after gen 25). One-sided (R better than S). Pre-registered threshold: p < 0.05.

| Delta = test EM(R) - test EM(S) | McNemar p | Verdict |
|---------------------------------|-----------|---------|
| >= +5.0pp | p < 0.05 | STRONG POSITIVE — crossover effect robust to default prompts |
| [+2.4pp, +5.0pp) | p < 0.05 | **POSITIVE (THROUGHPUT CONFOUNDED)** — crossover effect in default-prompt setting; throughput-equalized follow-up required |
| [+2.4pp, +5.0pp) | p >= 0.05 | SUGGESTIVE |
| (-2.4pp, +2.4pp) | any | NULL — no crossover benefit in default-prompt condition |
| <= -2.4pp | any | NEGATIVE |

**Push Run C as supplementary reference**: Push Run C (58.67%, same condition as Run S) is
reported as context in the Phase 5 results. If test EM(S) differs from 58.67% by > 5pp, this
anomaly is flagged as a potential infrastructure instability indicator.

### Test 4: Stagnation test (exploratory, H1_stag_Q)

**Criterion**: Does the `valid_frontier_fitness` (F1) trajectory for Run Q show improvement
after birth-gen 10 in at least 5 consecutive generations?

The birth-gen 10 threshold is deliberately conservative — two generations beyond the empirical
stagnation ceiling of birth-gen 4–8 — to avoid conflating early-phase exploration (where even
single-parent runs occasionally produce frontier improvements in gens 6–9) with genuine
post-stagnation recovery. The conservative threshold reduces false positives for H1_stag_Q at
the cost of missing crossover-driven improvements that occur between birth-gens 8 and 10; this
trade-off is accepted because the primary verdict comes from Test 2 (test EM comparison), not
from the stagnation trajectory alone.

For Run P (single-parent reference): expected stagnation by gen 8 (consistent with all 11
prior runs). If Run P stagnates by gen 8 AND Run Q continues improving past gen 10, the
stagnation test is POSITIVE — independent of the test EM comparison.

This is exploratory and does not influence the primary verdict classification of Test 2.

### Test 5: NLP-prompt effect at 600 samples — Run P vs. Run S (within-experiment)

**Test**: McNemar's test on matched item-level predictions (P and S share the same test set;
both num_parents=1). One-sided (P better than S). Pre-registered threshold: p < 0.05.

| Delta = test EM(P) - test EM(S) | McNemar p | Verdict |
|---------------------------------|-----------|---------|
| >= +2.4pp | p < 0.05 | POSITIVE — NLP prompts add value at F1+600+single-parent; confirms Run D vs C direction without Amendment 3 confound |
| [+2.4pp, ...) | p >= 0.05 | SUGGESTIVE |
| (-2.4pp, +2.4pp) | any | NULL — no detectable NLP-prompt effect at this sample size under F1+600 |
| <= -2.4pp | any | NEGATIVE — NLP prompts harm performance in default-prompt F1+600 setting |

Push Run D vs. push Run C showed +4.33pp (McNemar p=0.049), but was confounded by Amendment 3.
The P vs. S comparison is the first clean, pre-registered isolation of this effect.

### Binomial CIs

Binomial 95% CIs are computed for all four new runs regardless of proximity to GEPA or the
noise floor:

```
CI_lower = test_EM - 1.96 * sqrt(p*(1-p)/300)
CI_upper = test_EM + 1.96 * sqrt(p*(1-p)/300)
```

Reported in Section 5 of the results document.

---

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| **Throughput confound (Runs Q, R)** | With max_mutations=16 vs. 8 for P and S, Runs Q and R generate 2× more programs per generation. Any test EM gain could be attributed to increased search volume rather than crossover recombination quality. | Pre-registered design choice (not an oversight). Throughput is deliberately set to natural crossover capacity to give the mechanism its best opportunity to break stagnation. Analytical mitigation: inspect per-generation frontier improvement — if Q's frontier improvement occurs at birth-gens 10–20 rather than 1–8, this is mechanistically consistent with recombination regardless of throughput. Section 8 Test 2 labels results in [+2.4pp, +5.0pp) as POSITIVE (THROUGHPUT CONFOUNDED), triggering a throughput-equalized follow-up. |
| **`max_elites_per_generation` default is 5, not 8** | If the Hydra override `max_elites_per_generation=8` is omitted from any launch command, actual mutations per generation drop to C(5,2)=10 for crossover runs and 5 for single-parent runs, silently changing all combinatorics claims. | Mandatory `--cfg job` pre-launch check for all four runs: confirm `max_elites_per_generation: 8` in the resolved config. If any run shows 5, do not launch. Documented in Section 6 and in the pre-launch checklist. |
| **`num_parents` default is 2, not 1** | If the Hydra override `num_parents=1` is omitted for Run P or Run S, they silently become crossover runs, invalidating Tests 2, 3, and 5. | Mandatory `--cfg job` check: confirm `num_parents: 1` for P and S, `num_parents: 2` for Q and R. |
| **F1+NLP prompt compatibility** | Push experiment showed NLP prompts harmful at 300 samples under F1 fitness (Run A: −4.00pp vs. Run F), but beneficial at 600 samples (Run D: +4.33pp vs. Run C). Run P extends the 600-sample F1+NLP cell with N=2. If the positive result was a fluctuation, Run P could fall below 62.3%. | Pre-specified NULL verdict for Run P < 61.5%. P vs. S (Test 5) provides a cleaner concurrent estimate of the NLP-prompt effect. |
| **Early-generation throughput asymmetry for crossover** | With archive_size < 8 in gens 0–2, AllCombinationsParentSelector generates fewer than 16 mutations (C(k,2) for k < 6). C(2,2)=1; C(4,2)=6; C(6,2)=15; C(7,2)=21. | Accept. The ddce37b4 warm-start populates multiple archive slots at gen 0. Monitor actual mutations/gen from logs; report in results. The ramp-up asymmetry (<15 total missed mutations) is negligible over 400 total mutation opportunities. |
| **NLP prompts silent failure** | If `prompts_dir` is not correctly wired for Runs P and Q, they silently use default prompts — producing no scientific information on NLP-prompt effects but being charged as valid runs. | Mandatory pre-launch check (see m5 fix below): confirm `prompts_dir: .../hotpotqa` appears in the `evolution_context` block of `hotpotqa_asi.yaml` (line 24; present per 920c975). Confirm `mutation_operator.prompts_dir` resolves to the hotpotqa path in the `--cfg job` output (this field is configured in `config/algorithm/_base.yaml` line 46, not in `hotpotqa_asi.yaml`). These are two separate locations; both must be confirmed. |
| **Stale exec_runner workers or non-empty Redis DBs** | DBs 0–3 were used by nlp_prompts (PR #69); flushed per memory notes but must be re-verified. Stale workers could corrupt new runs. | Mandatory pre-launch: `tools/flush.py --db 0 1 2 3` (preview) then `--confirm`. Kill all exec_runner workers before flushing. |
| **Context length under crossover (Runs Q, R)** | Two-parent prompts are approximately 2× single-parent prompts. If evolved programs have grown beyond the ddce37b4 seed size after 25 push gens, 2-parent prompts could approach the mutation LLM's reasoning limit. | Monitor mutation LLM error rate at gen 5 for Q and R; alert if > 30% (likely context overflow). Pre-inspect push gen-25 programs for token count; flag if > 3000 tokens per program. |
| **Run S vs. push Run C anomaly** | Run S (concurrent F1+default+600, num_parents=1) should produce results close to push Run C (58.67%). A large deviation (>5pp) would indicate infrastructure instability. | Report deviation in Phase 5; flag as anomaly if test EM(S) deviates by > 5pp from push Run C. Run S is primarily a concurrent control for Run R; anomalous deviation does not invalidate Tests 2 or 3 but must be reported. |

---

## 10. Stop Criteria

### Stagnation-based early completion (all runs — pre-specified at 25 gens)

If `valid_frontier_fitness` shows no improvement for >= 10 consecutive generations AND the
current generation >= 15, the run may be terminated early. Results are reported on the full
archive at the time of termination. This is **not an invalidation** — it is early completion
under the confirmed stagnation pattern.

For crossover runs Q and R: if the frontier shows improvement after gen 15, the run should
complete the full 25 gens to capture the trajectory.

### Early termination criteria

- **Invalidity rate > 50% at gen 5 for any run**: Pause; diagnose stage_timeout. If median
  eval time exceeds 5000s, increase stage_timeout to 8000 before resuming. Do not continue
  past gen 5 with > 50% invalidity.
- **Val fitness = 0.0 at gen 0 for any run**: Halt; diagnose before proceeding. Expected:
  gen-0 val F1 ≈ 68–72% (consistent with push Run D's starting point); gen-0 val EM ≈ 59–61%.
- **Mutation LLM error rate > 30% at gen 5 for Q or R**: Alert; inspect mutation logs for
  context overflow. If prompt sizes exceed 15,000 tokens, this is a throughput risk.
- **NLP prompts verification failure**: If `python run.py --cfg job` for Run P or Q shows
  `prompts_dir` unresolved or defaulting to non-hotpotqa path, do not launch. Fix and
  re-verify.

### Run invalidation criteria

A run is excluded from all analyses if any of the following apply:

1. Thinking mode not active: `<think>` blocks absent from >= 5% of chain outputs at gen 1.
2. `pipeline=standard` used (repr-contamination bug).
3. Invalidity rate > 90% at gen 10.
4. Warm-start seed differs from `ddce37b4`.
5. `prompts_dir` not correctly wired for Runs P or Q (NLP prompt silent failure confirmed
   post-hoc from logs showing identical mutation outputs to a default-prompt run).
6. `static_f1_600` validate.py does not populate `valid_frontier_em` Redis key at gen 0
   (required for within-metric gap analysis).
7. `max_elites_per_generation` confirmed at 5 (not 8) in post-hoc log inspection — run's
   archive dynamics differ from design intent; all combinatorics claims invalid.

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time per run (600-sample, 25 gens) | ~10–17h (25 gens × ~24 min/gen for 600 samples / 4 async workers; stagnation-based early completion may reduce) |
| Total wall time (4 runs parallel) | ~17h wall-clock (all 4 runs are 600-sample; bottleneck is uniform) |
| Redis DBs | 4 (DBs 0, 1, 2, 3) |
| Mutation LLM servers | 4 × Qwen3-235B-A22B-Thinking (one per run; all 4 servers now assigned) |
| Chain LLM servers | 4 × Qwen3-8B thinking (one per run; all 4 endpoints now assigned) |
| Test eval time | ~5 min each × 4 runs = ~20 min total |
| New code required | None — `static_f1_600` already implemented (push); `num_parents` and `max_elites` are Hydra overrides only |

**Note on num_parents and max_elites defaults**:
- `num_parents: 2` is the default (`config/constants/evolution.yaml`). Runs Q and R need no
  override; Runs P and S require explicit `num_parents=1`.
- `max_elites_per_generation: 5` is the default. **All four runs** require explicit
  `max_elites_per_generation=8`. This override must appear in every launch command.

---

## 12. Open Questions / Risks

### Priority risks

**Risk 1 — `max_elites_per_generation` default is 5, not 8 (CRITICAL — C1).**
The most likely silent failure. Every run must include `max_elites_per_generation=8` as an
explicit Hydra override. The `--cfg job` check must confirm this for all four runs before
any run is launched. A run with max_elites=5 produces silently different archive dynamics and
is not comparable to prior experiments (all of which used max_elites=8).

**Risk 2 — `num_parents` default is 2, not 1 (CRITICAL).**
`config/constants/evolution.yaml` sets `num_parents: 2`. Run P and Run S must explicitly
override with `num_parents=1`. The `--cfg job` check must confirm `num_parents: 1` for P and
S, and `num_parents: 2` for Q and R. Failure to set this for P or S invalidates Tests 2, 3,
and 5 simultaneously.

**Risk 3 — Run D's 63.00% may not replicate (fundamental scientific uncertainty).**
Run D's result was based on effective gens 4–25 under F1+NLP+600 after Amendment 3 discarded
gens 1–3. If the true distribution for this condition is centered around 61.0–62.0%, Run P
will fall short of 63.00% and possibly below GEPA. This is not a methodological risk — it
is the scientific question Run P answers. The pre-registered NULL verdict (< 61.5%) is the
appropriate conclusion if replication fails.

**Risk 4 — Crossover may be harmful rather than neutral.**
The p3_crossover design document (2026-03-04) identified two-parent context length as a risk:
prompts are ~2× single-parent size. If push evolution grew programs significantly, the 2-parent
prompt could degrade mutation LLM reasoning quality. A NEGATIVE verdict (Q < P - 2.4pp or
R < S - 2.4pp) would confirm this risk and motivate reduced failure-case counts per parent in
any future crossover run.

**Risk 5 — Redis DBs 0–3 stale from nlp_prompts experiment (PR #69).**
Memory notes indicate these were flushed, but verification is mandatory. `tools/flush.py
--db 0 1 2 3` must show 0 keys before launch.

### Scientific open questions after this experiment

- If Run P replicates (>= 62.3%) AND Q - P >= +2.4pp (McNemar p < 0.05): crossover merits
  a throughput-equalized follow-up (max_mutations=8 for all runs) to isolate quality from
  search volume. This is the highest-priority follow-up.
- If Run P replicates AND Q ≈ P (NULL for crossover): single-parent F1+NLP+600 is a reliable
  above-GEPA configuration; focus shifts to whether any structural change can push further.
- If Run P does NOT replicate (< 61.5%): Run D's 63.00% was not representative. The
  F1+NLP+600 condition needs additional replications (N >= 3) to characterize its distribution.
- If P vs. S (Test 5) is POSITIVE (NLP prompts add >= +2.4pp at F1+600): this confirms the
  600-sample NLP-prompt interaction first observed in push (D vs. C, confounded). This is an
  important mechanistic finding for the mutation-prompt engineering literature.
- If R vs. S (Test 3) is POSITIVE but Q vs. P (Test 2) is NULL: crossover benefits only the
  default-prompt setting, possibly because NLP prompts already provide sufficient mutation
  diversity through linguistic quality improvements. This crossover × prompt interaction would
  be a novel and actionable finding.
- The NLP prompts × val-N interaction (harmful at 300 samples under F1, beneficial at 600
  samples) remains unexplained. Qualitative inspection of programs from P (positive at 600)
  vs. push Run A (negative at 300) may reveal whether NLP prompts systematically shift
  program structure toward longer retrieval chains that require more evaluation samples to
  stabilize.

---

## Appendix A: Code Verification Summary

The following were verified against the current codebase before writing this design:

1. **`AllCombinationsParentSelector` behavior**: `gigaevo/evolution/mutation/parent_selector.py`
   confirmed. With `num_parents=2`, generates all C(n,2) combinations from `available_parents`,
   shuffled. Capped at `max_mutations_per_generation` by the `generate_mutations()` loop in
   `gigaevo/evolution/engine/mutation.py` (line 47: `if len(parent_selections) >= limit: break`).
   With max_elites=8 and num_parents=2: C(8,2)=28 pairs, capped at 16 → 16 mutations/gen.
   **Contingent on `max_elites_per_generation=8` override being applied.**

2. **`num_parents` and `max_elites_per_generation` defaults**: `config/constants/evolution.yaml`
   sets `num_parents: 2` and `max_elites_per_generation: 5`. Both require explicit Hydra
   overrides for this experiment: `num_parents=1` for P and S; `max_elites_per_generation=8`
   for all four runs.

3. **`mutation_operator.prompts_dir` location**: `config/algorithm/_base.yaml` line 46:
   `prompts_dir: ${prompts.dir}`. This is separate from the `evolution_context.prompts_dir`
   at `config/pipeline/hotpotqa_asi.yaml` line 24. Both must resolve to the hotpotqa prompts
   directory for Runs P and Q. The pre-launch check for NLP prompt wiring must verify the
   `--cfg job` output shows `mutation_operator.prompts_dir` resolving to `.../hotpotqa`,
   not just check the pipeline YAML file directly.

4. **`mutation_mode` restriction**: `LLMMutationOperator.mutate_single()` in
   `gigaevo/evolution/mutation/mutation_operator.py` (line 105) raises `MutationError` if
   `diff` mode is used with multiple parents. All runs use `mutation_mode=rewrite` (default
   in `config/constants/evolution.yaml`).

5. **`static_f1_600` problem directory**: Already implemented and tested in push experiment.
   `valid_frontier_em` Redis key confirmed populated in push Run D. No new code required.

6. **NLP prompt metric-agnosticism**: `gigaevo/prompts/hotpotqa/mutation/system.txt` and
   related files use `{task_description}` injection. `problems/chains/hotpotqa/static_f1_600/
   task_description.txt` correctly describes F1 fitness as the objective. No hardcoded
   "exact match accuracy" framing present (confirmed in 02_review.md verified claims).

---

## Appendix B: Decision Tree

```
After gen-25 test evals for all 4 runs:

              Run P test EM?
             /               \
         >= 62.3%             < 61.5%
            |                    |
  Run D REPLICATES          Run D was NOISE
  (POSITIVE or STRONG)      (Amendment 3 material)
            |                    |
   Q - P delta?             Report NULL(P)
   /      |      \
>= +5pp  +2.4 to  < +2.4pp
  |       +5pp        |
STRONG  POSITIVE   NULL/NEG
POS.   (THROUGH-  (single-parent
       PUT CONF.) at ceiling)
         |
  Throughput-equalized
  follow-up next

Also check concurrently:

  R - S delta?           P - S delta?
  (Test 3: crossover     (Test 5: NLP-prompt
   in default prompts)    effect at 600 samples)

  + Stagnation test (Test 4):
    Q frontier improves after birth-gen 10?
```

---

*Ready for Reviewer-2's scrutiny.*
