# Research Strategy: Heilbronn Adversarial Co-Evolution (v2)

**Generated**: 2026-04-27 (post v1-honest-repro closeout)
**Supersedes**: v1 strategy (2026-04-19, post k5-budget-v3 closeout) -- v1 preserved in git history
**Experiments analyzed**: 12 heilbron-domain + 3 adversarial-domain = 15 total (9 closed heilbron + 3 closed adversarial + 3 new-since-v1 heilbron)
**Total runs across program**: 96+

**Delta since 2026-04-19 (v1 strategy)**:
- `heilbron/adversarial-repro-v1` (PR #211, **NULL**): v1 recipe under bug-fixed library; mu_G=0.0341 [0.0306, 0.0377] 95% CI. Confounded by `redis.resume=false` not flushing DBs + I-16/I-17 bugs.
- `heilbron/adversarial-repro-v2` (PR #216, **NULL**): Stacked treatments SBF-Lineage + SOFTMAX-G + I-16/I-17 fixes; mu_G=0.03315 [0.03001, 0.03630] 95% CI, Delta=-0.10pp vs v1 baseline (p=0.692). D collapse persists. Information-flow hypothesis exhausted.
- `heilbron/v1-honest-repro` (PR #224, **SUGGESTIVE lean H1**): v1 binary G + linear D landscape on current main; mu_G=0.03398 [0.03282, 0.03515] 95% CI. v1 baseline mean 0.03574 outside upper CI bound. 0/4 G runs >= 0.03574. Implies ~300 commits of library drift are load-bearing.

---

## 0. Headline

**Three consecutive restoration attempts have failed. The v1 SOTA is not recoverable by small interventions on the current library -- the research program now faces a fork between two P1 paths.**

Since the v1 strategy (2026-04-19), three experiments have tested orthogonal "minimal change" hypotheses against the v1 baseline (0.03574): adversarial-repro-v1 restored loose coupling and v1 hyperparameters (NULL, mu=0.03413); adversarial-repro-v2 stacked information-flow enhancements (NULL, mu=0.03315); v1-honest-repro restored the v1 fitness landscape itself -- binary G resistance, linear D scoring, SBF disabled -- producing mu=0.03398 with v1 baseline outside the 95% CI upper bound [0.03282, 0.03515]. The cumulative implication is stark: even when every configurable parameter is pinned to v1 values, the current library cannot reproduce v1-era performance. The gap is in the ~300 commits of engine churn between `562a1210` and `25470e37`, not in the fitness landscape or the coupling dynamics.

This creates two P1-tier paths forward. **Path A (REDESIGN bundle)** attacks the identified structural root cause: smoothed tanh fitness to break D-collapse + deterministic HoF + K=L=3 + cache_on edges. This path does not require understanding the drift -- it bypasses it by fundamentally improving the fitness signal. The in-flight `d-tanh-no-lineage` pre-registration already tests a SUBSET of this bundle (D tanh smoothing alone), making it the lowest-cost probe of whether fitness smoothing moves the needle. **Path B (library-drift bisection)** attacks the reproduction gap directly: 8-10 git-bisect rounds between `562a1210` and `25470e37` to identify which commit(s) broke the v1 recipe. This path is slower and more expensive but answers whether v1 SOTA is recoverable on the modern codebase.

The recommended sequencing: let `d-tanh-no-lineage` run to completion first. If D smoothing alone eliminates collapse and lifts G above baseline, Path A (full REDESIGN bundle) becomes unambiguous P1 and Path B is deprioritized. If D smoothing is insufficient, Path A and Path B both remain viable -- the researcher must choose where to allocate the next compute window. Under no scenario should both P1 candidates run concurrently; information from one should inform the decision to invest in the other.

---

## 1. Hypothesis Ranking

Evidence from 12 closed heilbron experiments + 3 closed adversarial-domain experiments. Effect sizes and 95% CIs cited from each experiment's `05_results.md`.

| # | Hypothesis | Strength | Experiments | Effect Size / CI | Direction | Testable? |
|---|---|---|---|---|---|---|
| H1 | Adversarial co-evolution produces genuine actual_fitness improvement | **CONFIRMED** | All 12 heilbron + 3 adversarial | Best-overall range 0.031-0.036 across experiments. Peak 0.03650 (above Q_MAX=0.0365). adversarial-vs-solo: +0.00182 (p=0.365, d=0.70) | Positive | Tested |
| H2 | Improver stagnation is structural -- ROOT CAUSE: D hard-floor fitness | **CONFIRMED** | All 12 heilbron; retroactive for all 3 adversarial | 60-90% D fitness point mass at 0.0 (k5-budget-loose empirical). D strategy rejection 56-79% vs 0-14% on G. v1-honest-repro A2_D normalized fitness 0.00095 | Causal structural | ROOT CAUSE |
| H3 | D hard-floor fitness (`max(delta,0)`) causes D collapse | **CONFIRMED** | k5-budget-loose (empirical), retroactive 11 others. v1-honest-repro D fitness [0.001, 0.382] confirms collapse persists under v1 semantics | 60-90% at fitness=0.0 across all experiments with D populations | Binding constraint | Fix UNTESTED |
| H4 | G hard-floor resistance masks adversarial signal | **SUGGESTIVE** | k5-budget-loose (code analysis), k5-budget-v3 (indirect) | Binary `float(delta<=0)` per opponent. Point masses hidden by 50% quality weight | Structural, not tested for fix | Blocked on REDESIGN |
| H5 | 2D MAP-Elites BD eliminates D collapse (structurally) | **CONFIRMED** | k5-budget-v3 | All 4 D pops fitness [0.520, 0.680]. Grand mean G 3.3% below v2 baseline (diversity cost) | Positive structural | Tested |
| H6 | Archive re-evaluation hurts in adversarial settings | **CONFIRMED** | adversarial-dynamic-updates | Control - treatment = 0.01083 [0.007, 0.015] 95% CI bootstrapped. 5.5x NEGATIVE threshold | Negative | Tested (CLOSED) |
| H7 | Pure GAN resistance causes mode collapse | **CONFIRMED** | adversarial-dynamic-updates | GAN_C_A 99.6% resistance, actual_fitness 0.02854 | Negative | Tested (CLOSED) |
| H8 | Loose coupling (min_delta=1) outperforms tight (min_delta=8) | **WEAKENED** | asymmetric-iterations v1 (loose, >=105% SOTA), v2 (tight, 98-104%), adversarial-repro-v1 (loose via drift_cap=100000, NULL at 0.03413) | v1 vs v2 delta: +0.00081 mean. repro-v1 vs v2: +0.00030 (indistinguishable) | Confounded with library drift | Blocked on REDESIGN |
| H9 | Feedback mode (composition vs gradient-in-prompt) matters | **REFUTED** | asymmetric-iterations, asymmetric-iterations-v2, adversarial-repro-v1, adversarial-repro-v2, v1-honest-repro | 10+ experiments, 24+ paired runs. Cross-arm deltas: 0.00081, 0.00066, 0.00350 (confound), 0.00041, 0.00127. Excluding confounded repro-v1: all < 0.002 | **CLOSED** | CLOSED |
| H10 | Opponent context has minimum effective dose (K>=3) | **SUGGESTIVE** | adversarial-v2 | K=3: 0.03502, K=0 (baseline): 0.03464, K=1: 0.03247. Ordering: K=3 > K=0 > K=1. N=1 per condition | Possible non-monotonic | Blocked on REDESIGN |
| H11 | K=5 compute budget breaks Improver stagnation | **CONFOUNDED-TESTED** | k5-budget-v3 | Effect -0.00164 [-0.00393, +0.00065] 95% CI (bootstrap). Confounded: deadlock + N=2 + broken fitness | No directional signal | Blocked on REDESIGN |
| H12 | REDESIGN bundle breaks D-collapse and lifts G actual_fitness | **UNTESTED** | -- | -- | -- | **P1 candidate A** |
| H13 | ProgressBasedSyncHook deadlock is K-dependent | **SUGGESTIVE (tentative)** | k5-budget-v3 | N=1 occurrence in K3_1, 0 in K=5 pairs | Possibly yes | Fixed (KF-07 drift-cap redesign) |
| H14 | Source code access accelerates early optimization | **WEAKENED (further)** | asymmetric-iterations v1 (+), v2 (not reproduced), adversarial-repro-v1 (not reproduced), v1-honest-repro (not reproduced) | v1 >=105% SOTA gen 8-12. Three subsequent experiments with source code access failed to reproduce acceleration | Confounded with library drift + coupling | Deprioritized |
| H15 | Adversarial beats solo MAP-Elites | **SUGGESTIVE** | adversarial-vs-solo | +0.00182 (p=0.365, d=0.70). 55% power at N=4 | Positive but underpowered | Blocked on REDESIGN |
| H16 | Structured Improver operators break stagnation | **UNTESTED** | -- | -- | -- | Blocked on REDESIGN |
| H17 (NEW) | Library drift (~300 commits) is the primary cause of v1 non-reproduction | **SUGGESTIVE** | v1-honest-repro | mu_G=0.03398 [0.03282, 0.03515] vs v1 baseline 0.03574 (outside upper CI bound). 0/4 G >= 0.03574 | Negative (current main regressed) | **P1 candidate B** |
| H18 (NEW) | Information-flow improvements are insufficient under hard-floor fitness | **CONFIRMED** | adversarial-repro-v1 (NULL, 0.03413), adversarial-repro-v2 (NULL, 0.03315) | Two consecutive NULL results with progressively richer info-flow. Downward trend from 0.03574 to 0.03413 to 0.03315 (not significant, CIs overlap) | Information flow CLOSED as standalone | CLOSED until REDESIGN |
| H19 (NEW) | SBF-Lineage + SOFTMAX do not break D stagnation under hard-floor fitness | **CONFIRMED** | adversarial-repro-v2 | 2/4 D runs collapsed to fitness=0.000 despite SBF-Lineage. mu_G=0.03315 [0.03001, 0.03630], p=0.692 vs v1 | Null, directionally negative | CLOSED until REDESIGN |

---

## 2. Cross-Experiment Patterns

### Intervention Category Analysis

**Fitness function (2 experiments, 1 CONFIRMED structural defect + 1 partial fix)**
- `k5-budget-loose`: root-cause discovery. D hard-floor creates 60-90% point mass at 0.0.
- `k5-budget-v3`: 2D MAP-Elites BD diversifies niches; D fitness maintained > 0.50 but underlying formula unchanged.
- `adversarial-dynamic-updates`: SOFT > GAN (0.03186 vs 0.02854); GAN caused mode collapse.
- **v2 update**: `v1-honest-repro` confirms the D hard-floor pathology persists even under v1 binary/linear semantics: D normalized fitness as low as 0.00095 (A2_D).
- **Meta-pattern UNCHANGED**: Fitness function is the dominant explanation for Improver stagnation. All prior NULLs in information/coupling/budget categories are expected under H3.

**Information flow (9 experiments, 0 stagnation breakthroughs)**
- K=0/1/3, source-code access, composition injection, gradient-in-prompt, bidirectional code, SBF-Lineage, SOFTMAX sampling. None broke stagnation.
- **v2 update**: Two sequential replication attempts (adversarial-repro-v1, adversarial-repro-v2) explicitly tested info-flow under v1 recipe and under stacked enhancements. Both NULL. H18 CONFIRMED: information flow is NOT the binding constraint. This category is now **CLOSED** as a standalone research direction until REDESIGN resolves the fitness landscape.

**Coupling granularity (3 experiments, WEAKENED)**
- v1 loose -> >=105% SOTA; v2 tight -> 98-104% baseline.
- **v2 update**: adversarial-repro-v1 restored loose coupling (drift_cap=100000) and produced mu=0.03413, indistinguishable from v2's tight-coupling mean (0.03383). Delta between loose and tight coupling: +0.03pp [-0.33, +0.39] 95% CI. The v1/v2 gap is NOT explained by coupling alone. H8 downgraded from SUGGESTIVE (strengthened) to WEAKENED.

**Landscape restoration (1 experiment, SUGGESTIVE)**
- **NEW category from v1-honest-repro**: pinned v1 binary/linear landscape on current main. mu_G=0.03398, v1 baseline 0.03574 outside upper CI [0.03282, 0.03515]. The landscape is not the gap; the engine is.

### Effect Size Patterns

- Typical positives remain small (+0.00038 to +0.00182; 1-5% of baseline).
- Best all-time result (0.03650 from asymmetric-iterations v1) has **not been deliberately reproduced** in 5 subsequent experiments.
- **v2 update**: The progression of grand means across the three replication attempts is: repro-v1 0.03413, repro-v2 0.03315, v1-honest-repro 0.03398. All cluster in the 0.033-0.034 band, consistently below the v1 reference (0.03574) and baseline-repro (0.03449). The replication series has converged on a new de facto performance band under the current library.
- Negatives remain larger and more reliable: re-eval -0.011, K=1 -0.00217. Still easier to hurt than help.
- **Outlier signal**: C1_G in adversarial-repro-v2 reached 0.03650 (1/4 G runs, matching v1 SOTA). Stochastic, not systematic -- the other three G runs averaged 0.03203.

### Infrastructure Fragility

Each experiment continues to discover 2-5 new infrastructure issues:
- adversarial-repro-v1: I-16 (evaluate.py artifact contract), I-17 (CompositionInjectionHook lineage labeling), KF-10/KF-11/KF-12.
- adversarial-repro-v2: I-18 (Program.create_child iteration drop), KF-13. Two-pass bucketed refresh overhead not characterized pre-launch.
- v1-honest-repro: I-03 (dg_tracker coupling), I-04 (yaml quote-stripping, KF-14), I-06 (LiteLLM proxy hang, KF-15), I-07 (post-recovery process wedge, KF-16).
- **Meta-pattern**: Infrastructure discovery rate shows no sign of diminishing. Each experiment uncovers novel failure modes. The framework is not yet mature enough for lights-out operation.

### Baseline Drift

- v1 strategy reported baseline stable at 0.03449 (N=4, SD=0.00212 from baseline-repro).
- **v2 update**: Three new experiments all produce means in 0.033-0.034, consistently below baseline-repro's 0.03449. The de facto achievable band on the current library appears to be 0.033-0.034, not 0.034-0.035. This 1pp drift is not explained by any single parameter change -- it is distributed across the ~300 commits of library evolution.

### Reproducibility Wall (NEW)

Three sequential restoration attempts, each controlling for more confounds than the last, all sub-baseline:

| Experiment | Treatment | mu_G | 95% CI | vs v1 baseline (0.03574) |
|---|---|---|---|---|
| adversarial-repro-v1 | v1 recipe + drift_cap=100000 | 0.03413 | [0.0306, 0.0377] | -0.16pp |
| adversarial-repro-v2 | +SBF-Lineage +SOFTMAX +I-16/I-17 fixes | 0.03315 | [0.0300, 0.0363] | -0.26pp |
| v1-honest-repro | v1 binary G + linear D + SBF off | 0.03398 | [0.03282, 0.03515] | -0.18pp |

Each experiment eliminated a different class of hypothesis for the gap: repro-v1 tested coupling, repro-v2 tested information quality, v1-honest-repro tested the fitness landscape itself. None recovered v1 performance. The residual lives in the engine code path, not in any tunable parameter. This "reproducibility wall" is the most important new finding in the v2 strategy period.

---

## 3. Information Gap Analysis

Re-ranked from v1 strategy. The top two positions are now co-equal candidates, not a single BLOCKING priority.

| Rank | Question | Info Gain | Why |
|---|---|---|---|
| 1A | **Does the REDESIGN bundle (smoothed tanh fitness + det HoF + K=L=3 + cache_on) break D-collapse and lift G above baseline?** | **CRITICAL** | Unchanged from v1. Targets root cause (H3). 12 experiments tested on broken landscape. In-flight `d-tanh-no-lineage` tests a subset (D smoothing only); positive there strengthens P1A, null there weakens but does not refute (HoF + K=L=3 still untested). |
| 1B | **Which commits between `562a1210` and `25470e37` are load-bearing for the 5pp v1 regression?** | **CRITICAL (NEW)** | v1-honest-repro proved the gap is not in the landscape configuration. Bisecting the 300+ commits identifies whether v1 SOTA is recoverable or permanently lost. If recoverable, the REDESIGN bundle can be tested on a v1-level baseline instead of the depressed 0.033-0.034 band. If not, the REDESIGN bundle must overcome both the drift AND the fitness defect. Candidate culprits: ConfigurableAggregator introduction, DGImprovementTracker/cache_on wiring (commit `1d25a9a8`), evaluate.py tuple-contract migration. |
| 2 | Does D smoothing alone (without HoF/K=L/cache_on) eliminate collapse? | **HIGH** | **Partially answered by in-flight `d-tanh-no-lineage`**. Do NOT propose a duplicate. Wait for result. If positive, the REDESIGN bundle becomes a layered ablation series (smoothing first, then add HoF, then K=L, then cache_on). If null, the full bundle is needed. |
| 3 | Under a working fitness function, does K=5 outperform K=3? | HIGH | k5-budget-v3 confounded by deadlock + N=2 + broken fitness. Re-test contingent on REDESIGN positive. KF-07 now fixed. |
| 4 | Does loose coupling (min_delta dose-response) matter under REDESIGN? | MED-HIGH | H8 weakened by repro-v1 showing loose coupling alone is insufficient. Still the most suggestive signal in the program. Contingent on REDESIGN. |
| 5 | Does adversarial reliably beat solo at N=8? | MEDIUM | Paper-critical. d=0.70 at p=0.365 unresolved. Confounded by H3 -- prior runs under broken fitness. Re-test under REDESIGN. |
| 6 | Is 2D BD necessary under smoothed fitness, or does smoothing alone suffice with 1D? | MEDIUM | v3 coupled 2D BD with broken fitness. Under smoothed fitness, 1D may suffice (no diversity tax). Contingent on REDESIGN. |

**Key insight (unchanged but sharpened)**: Questions 2-6 are all contingent on Question 1A resolving positively. Testing them under the current broken fitness function wastes compute. Question 1B is independent of 1A and can run in parallel, but at high compute cost.

---

## 4. Next Experiment Proposals (ranked)

### P1-A: REDESIGN Bundle Test [HIGHEST PRIORITY -- BLOCKING]

**Research question**: Does smoothed tanh fitness + deterministic HoF + K=L=3 + cache_on edges break D-collapse and lift G actual_fitness above baseline (0.03449)?

**Hypothesis tested**: H12 (REDESIGN bundle breaks D-collapse). Secondary: H3 (D hard-floor is the root cause).

**Expected information gain**: CRITICAL. Positive result reopens the entire intervention space. Negative result implies fundamental ceiling, triggers Pareto coevolution escalation.

**Design sketch**: 2x2 factorial from `experiments/heilbron/k5-budget-loose/REDESIGN.md`. Factor 1: Fitness (linear hard-floor vs smoothed tanh). Factor 2: Feedback mode (composition vs gradient-in-prompt) as known-NULL calibration axis. 4 arms x 1 pair = 8 runs; N=2 per fitness level (pooling feedback modes). Primary: D fitness distribution at gen 25 (is 0.0 point mass eliminated?). Secondary: G actual_fitness at gen 50. Pre-registered success: D fitness NOT point-mass AND G mean >= 0.03449. Failure: smoothed arms still show D collapse OR G < 95% baseline. Cost: 8 runs x gen 50, ~24h. Prerequisites: KF-08 archive fix, KF-09 gen-0 persistence. Note: `d-tanh-no-lineage` (in-flight) tests D smoothing alone. If that branch returns positive, P1-A narrows to testing the REMAINING bundle components (HoF + K=L + cache_on) rather than the full factorial.

### P1-B: Library-Drift Bisection [CRITICAL -- INDEPENDENT OF P1-A]

**Research question**: Which specific commits between `562a1210` (v1) and `25470e37` (current main) are responsible for the 5pp G actual_fitness regression observed in v1-honest-repro?

**Hypothesis tested**: H17 (library drift is the primary cause of v1 non-reproduction).

**Expected information gain**: CRITICAL. If the breaking commit is a single identifiable change (e.g., ConfigurableAggregator mean-reduction, DGImprovementTracker wiring), it can be reverted or the REDESIGN bundle can be applied on the pre-regression commit. If the regression is distributed across many small changes, v1 SOTA is permanently unrecoverable and the REDESIGN bundle must achieve its gains from the depressed 0.033-0.034 baseline.

**Design sketch**: Git-bisect over ~300 commits between `562a1210` and `25470e37`. At each bisect midpoint, run the v1-honest-repro pipeline (v1 binary G, linear D, SBF off, drift_cap=100000) with N=2 G-only runs. Decision threshold: if mu_G >= 0.035 at the midpoint, the regression is AFTER that commit; if mu_G < 0.034, the regression is BEFORE. 8-10 bisect rounds. Cost per round: ~12h (2 G runs x gen 50). Total: ~10 weekends or ~5 weekdays of continuous compute. Candidate culprits to check first (accelerated bisect): ConfigurableAggregator introduction, commit `1d25a9a8` (DGImprovementTracker/cache_on wiring), evaluate.py tuple-contract migration.

### P2: D-Side Compute Optimization [MEDIUM -- INFRASTRUCTURE]

**Research question**: Can the per-generation D compute overhead (observed at ~1.84x G in d-smoothing-minimal logs) be reduced to enable longer D horizons within fixed wall-clock budgets?

**Hypothesis tested**: No fitness hypothesis -- pure infrastructure. The d-smoothing-minimal branch revealed that D-side overhead is high enough to constrain experiment throughput.

**Expected information gain**: MEDIUM. Does not change any fitness hypothesis but enables higher-generation experiments with better statistical convergence. Required before any experiment targeting gen 100+.

**Design sketch**: Profile D-side pipeline to identify hot path (likely two-pass bucketed refresh mechanism observed in adversarial-repro-v2 at D/G ratio 1.29x vs v1's 4.00x). Benchmark single-pass vs two-pass refresh. If two-pass is the bottleneck, make it configurable (single-pass default, two-pass opt-in). No separate experiment needed -- engineering task.

### P3: min_delta Dose-Response [MEDIUM -- CONTINGENT ON P1-A POSITIVE]

**Research question**: Under REDESIGN bundle, does min_delta in {1, 4, 8} affect search effectiveness?

**Hypothesis tested**: H8 (loose coupling outperforms tight coupling) -- now WEAKENED but not refuted.

**Expected information gain**: MEDIUM. v1/v2 comparison confounded by library drift AND broken fitness. H8 needs a clean test under a working landscape. Already queued as `adversarial_014`.

**Design sketch**: 3-arm, N=3/arm, REDESIGN bundle on all arms. min_delta as sole IV. Pre-registered wall-clock cap. KF-07 drift-cap semantics ensure no deadlock. Cost: 18 runs x gen 50, ~54h. Contingent on REDESIGN positive.

### P4: Pareto Coevolution Escalation [CONTINGENT ON P1-A NULL]

**Research question**: If fitness smoothing cannot break stagnation, can Pareto-front multi-objective coevolution (DECA/IPCA-style) decouple fitness from resistance and create a viable evolutionary gradient?

**Hypothesis tested**: Escalation from H12 failure. If smoothed fitness is insufficient, the adversarial co-evolution approach may require fundamentally different selection mechanics rather than better fitness functions.

**Expected information gain**: HIGH only if P1-A is NULL. 2-4 weeks engineering + 48h runs. REDESIGN.md explicitly marks this as the escalation path. Only pursue if P1-A shows smoothed fitness is insufficient.

### P5: Task Pivot to HoVer/HotpotQA Adversarial [LONG-SHOT]

**Research question**: Does the adversarial co-evolution framework transfer to multi-hop QA tasks where the search space is less constrained than Heilbronn geometry?

**Expected information gain**: LOW for the Heilbronn program, HIGH for the NeurIPS paper's generality claims. Only pursue after P1-A/P1-B resolve.

---

## 5. Research Program Health

**Trajectory**: **Understanding improving, results declining.** The three new experiments have not improved the best result; instead they have progressively tightened the evidence that v1 SOTA is not recoverable via parameter restoration. The mean G actual_fitness across the last three experiments (0.03413, 0.03315, 0.03398) clusters around 0.034, approximately 5pp below v1's 0.03574. The program has moved from "how do we beat v1" to "why can't we reproduce v1" -- this is scientifically honest but not the trajectory that produces a strong NeurIPS submission.

**Paper readiness**: **Regresses from 50-55% to ~40%.** The reproducibility wall finding is scientifically valuable but complicates the narrative. The paper cannot claim "designed co-evolution beats baselines" when the best result was accidental (v1 loose coupling) and has not been reproduced in 5 attempts. The paper CAN claim "we identified and fixed the root cause of improver stagnation in adversarial co-evolution" IF the REDESIGN bundle works. A positive P1-A result rescues the paper. A null P1-A result forces a pivot to a different narrative (e.g., "lessons from a failed adversarial co-evolution program").

**Saturation**: **NOT saturated but approaching a critical decision point.** The fitness-function dimension is newly opened (v1 strategy finding, unchanged). Library-drift bisection is a new dimension. But the number of remaining HIGH-value experiments is small: P1-A (the bundle), P1-B (the bisection), and then contingent follow-ups. If both P1 candidates return null, the Heilbronn adversarial line should be closed.

**Remaining high-value experiments**: 2-3 (P1-A and P1-B are both high-value; contingent experiments P2-P5 depend on P1 outcomes).

**Recommendation**: **Blocked on REDESIGN bundle OR library-drift bisection. Research progress requires deciding which path gets compute budget.** The in-flight `d-tanh-no-lineage` pre-registration is a low-cost partial-bundle probe testing D tanh smoothing alone -- it should run to completion before allocating to either full P1 candidate. If d-tanh-no-lineage is positive, commit to P1-A (full REDESIGN bundle). If null, weigh P1-A (still viable -- HoF + K=L + cache_on components untested) against P1-B (drift bisection may reveal a simpler fix). Do NOT launch K-value re-tests, min_delta dose-response, or any other contingent experiment until one P1 path resolves positively.

---

## 6. Infrastructure Debt (pre-launch fixes for next experiment)

### Framework-Side (affects all experiments)

| ID | Fix | Why | Status |
|---|---|---|---|
| KF-07 | ProgressBasedSyncHook drift-cap redesign | K3_1 deadlocked 2h in k5-budget-v3. Replaced with asymmetric drift-cap semantics. | **FIXED** |
| KF-08 | Archive pipeline: `extra="forbid"` -> `"ignore"`, pickle fallback, CSV-emptiness guard | Bugs A1-A5 in k5-budget-v3 silently produced empty CSVs. | **OPEN** |
| KF-09 | `EvolutionEngine.run()` persists `engine:total_generations=0` before first `step()` | Checkpoint records polluted with `best_fitness=0.0`, `gen=null`. | **OPEN** |
| KF-12 | Redis DB flush assertion at relaunch | `redis.resume=false` does not flush DBs. Broken-phase programs contaminated adversarial-repro-v1. | **OPEN** |
| KF-14 | yaml.dump quote-strip for hex commit strings | `25470e37` parsed as scientific-notation float. Recurring in v1-honest-repro (I-04). | **ACTIVE** |
| KF-15 | LiteLLM proxy hang detection (Pattern 10 surfacing) | Proxy front door healthy, backend dead. Runs see "Request timed out" loops. v1-honest-repro I-06. | **ACTIVE** |
| KF-16 | Post-recovery process wedge detection | After multi-hour upstream outage, run processes do not resume. v1-honest-repro I-07. | **ACTIVE** |

### Experiment-Side (required before P1-A launch)

| Fix | Why |
|---|---|
| Pre-registered `max_runtime_hours` cap in experiment.yaml | Three of the last four experiments required unregistered early termination. |
| Smoke test exercises BOTH G and D roles for adversarial-asymmetric experiments | v1-honest-repro I-03 caught dg_tracker coupling crash only at full launch. |
| Treatment verification assertion: non-zero `dg_best_pairs` Redis key within first N steps | I-16 in adversarial-repro-v1 was silent for 6.5h. |

---

*Generated by `/experiment-retrospective` 2026-04-27. Consumed by experiment-design, reviewer-2-adversary, and retrospective-analyst agents. Do not duplicate this content in agent memories.*
