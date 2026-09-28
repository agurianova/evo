# Experimental Design: D-Side Fitness Smoothing (Minimal REDESIGN Isolation)

**Date**: 2026-04-24
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft (revised)
**Predecessor**: `heilbron/adversarial-repro-v2` (NULL verdict, PR #216, mu_G=0.03315)

## Revision Log

| Date | Item | Change |
|---|---|---|
| 2026-04-24 | C1 (metrics.yaml text frozen) | Removed metrics.yaml description change from IV table. Fitness description text frozen identical to v2 (`"...Worsening counts as 0, not negative."`). Added as explicit controlled variable. |
| 2026-04-24 | M1 (mechanistic claim relabeled) | Relabeled Section 2.2 from "Pre-Registered Mechanistic Claim" to "Treatment Verification Check (Code-Application Diagnostic)." Added Section 2.2a with primary mechanistic prediction: D fitness distribution shape (variance, non-degeneracy, fraction in [0.1, 0.9] at gen 20). |
| 2026-04-24 | m1 (exception-path incentive) | Documented behavioral consequence of exception score 0.5 in Section 3. Added D exception rate as secondary diagnostic in Section 8.7. |
| 2026-04-24 | m2 (delta semantics / lower_bound) | Noted `mean_improvement_raw.lower_bound` must be updated from 0.0 to -0.0365 in metrics.yaml. No prompt confound (`include_in_prompts: false`). |
| 2026-04-24 | m3 (REGRESSIVE unreachable) | Acknowledged in Section 2.1 that REGRESSIVE verdict is effectively unreachable at N=4 given v2's bootstrap CI. |
| 2026-04-24 | m4 (wall-clock adequacy) | Section 10 now states expected G generation depth at 28h (~40-55 gens based on v2 rate) and confirms partial runs are included in primary analysis. |
| 2026-04-24 | m5 (smoke test tightened) | Tightened smoke test from < 50% to < 5% at fitness < 0.001; added median fitness check in [0.3, 0.7]. |
| 2026-04-24 | m6 (power notation) | Replaced "pp" with "raw delta" notation in Section 7. |

---

## 1. Research Question

Does replacing the D-side hard-floor fitness formula (`delta = max(raw_delta, 0.0); score = min(delta / Q_MAX, 1.0)` at `problems/heilbron_repro_v1/pop_b/evaluate.py:97-99`) with a continuous tanh form (`score = 0.5 * (np.tanh(raw_delta / Q_MAX) + 1.0)`) lift mu_G out of the NULL band established by `heilbron/adversarial-repro-v2` (mu_G=0.03315, N=4 G runs), given that the G-side smoothing hotfix (PR #219, commit `2de8267e`, 2026-04-24) already landed on main?

This is a **single-IV experiment**: the only change relative to v2 is the D fitness function. All other configuration -- SBF-Lineage, SOFTMAX opponent sampling, asymmetric archive_reeval, drift_cap, seeds, feedback mode arms -- are inherited verbatim from v2. This isolation is deliberate: if D-smoothing alone produces signal, the root-cause hypothesis (H3 in `RESEARCH_STRATEGY.md`) is confirmed actionable. If it does not, the binding constraint lies elsewhere and the full REDESIGN bundle (`adversarial_015`: deterministic HoF + K=L=3 + cache_on edges) becomes the logical next step.

**Positioning vs adversarial_015 (full REDESIGN bundle)**: adversarial_015 stacks D-smoothing + deterministic HoF + K=L=3 + cache_on edges in a factorial design. This experiment (adversarial_019 in IDEAS.yaml) isolates the D-smoothing component only. A positive result here would mean D-smoothing alone is sufficient to break D collapse, simplifying the remaining research program. A null result would implicate the auxiliary REDESIGN components and justify the full bundle.

**First experiment under dual-smoothed fitness**: This is the first adversarial experiment where both G and D sides have continuous fitness signals. All 11 prior experiments ran under hard-floor D fitness; all 11 ran under binary G resistance (pre-PR #219). The combination of G-side linear-clip resistance (PR #219, now on main) and D-side tanh scoring (this experiment's treatment) has never been tested.

---

## 2. Hypotheses

Let **mu_G** = grand mean of best-ever `actual_fitness` across the 4 G runs (A1_G, A2_G, C1_G, C2_G).

**H0**: mu_G <= 0.03449 (baseline-repro mean). D-smoothing alone does not lift G above baseline parity.
**H1**: mu_G > 0.03449. D-smoothing breaks D collapse and enables meaningful G improvement.

### 2.1 Effect-Size Thresholds

Anchored to prior experiment means and the Q_MAX theoretical ceiling:

| mu_G range | Verdict | Rationale |
|---|---|---|
| >= 0.0365 (Q_MAX ceiling) | **POSITIVE (strong)** | At least 1/4 G runs at SOTA, grand mean at ceiling. Arms race functional. |
| >= 0.03550, < 0.0365 | **POSITIVE** | Exceeds all prior adversarial means (v1: 0.03413, v2: 0.03315, baseline-repro: 0.03449). Clear directional improvement. |
| >= 0.03449, < 0.03550 | **SUGGESTIVE** | At or above baseline-repro mean but below decisive threshold. Warrants follow-up with larger N or REDESIGN bundle. |
| >= 0.03200, < 0.03449 | **NULL** | Within the band spanned by v1 (0.03413) and v2 (0.03315). D-smoothing alone is insufficient. |
| < 0.03200 | **REGRESSIVE** | Below v2's lower bound. Treatment is actively harmful. |

The NULL band (0.03200--0.03449) is wide because it must contain both the v1 and v2 point estimates. A result inside this band is uninformative about D-smoothing's value; it merely replicates the prior NULL envelope.

**Note on REGRESSIVE reachability**: The REGRESSIVE threshold (< 0.03200) falls below v2's bootstrap 95% CI lower bound (0.03001). With N=4 sampling noise at sigma=0.003, a grand mean below 0.03200 would require all 4 runs to regress simultaneously. This makes REGRESSIVE effectively unreachable under normal variance. The threshold is retained for completeness -- if reached, it would represent a strong signal of treatment harm -- but the realistic verdict space is {NULL, SUGGESTIVE, POSITIVE, POSITIVE (strong)}.

### 2.2 Treatment Verification Check (Code-Application Diagnostic)

**This is a code-application diagnostic, not a scientific prediction.** At gen 5, the fraction of D-archive programs with fitness exactly 0.000 must be **< 10%** across all 4 D runs.

Baseline for comparison:
- k5-budget-loose (broken D): 60--90% at 0.000 across all 4 D runs (gen 1--2).
- adversarial-repro-v2 (broken D): 2/4 D runs at engine fitness 0.000 at closeout.

Under the tanh treatment, `raw_delta = 0` maps to score 0.500 (not 0.000), and `raw_delta < 0` maps to (0.0, 0.500). The point mass at exactly 0.000 vanishes **by construction** if the code change is correctly applied. The < 10% threshold is definitionally satisfied by the tanh formula; a failure (>= 10% at exactly 0.000) can only occur if the treatment code was not applied, was overridden at runtime, or if an unexpected code path bypasses the tanh scoring. This check verifies correct code deployment, not evolutionary dynamics.

### 2.2a Pre-Registered Mechanistic Prediction (D Fitness Distribution Shape)

**This is the primary mechanistic hypothesis.** If D-smoothing breaks the structural collapse, the D fitness distribution should become non-degenerate and evolve over time, reflecting genuine variation in D program quality.

Pre-registered predictions at three checkpoints:

| Checkpoint | Prediction | Rationale |
|---|---|---|
| Gen 5 | D fitness distribution is unimodal with median in [0.35, 0.65]; variance > 0.01 (SD > 0.1). Fraction of D-archive programs with fitness in [0.1, 0.9] exceeds **70%**. | Early generations: most programs have near-zero raw_delta (tanh(0) = 0.5). Some variation from exceptions (`score=0.5`) and from programs that worsen (score < 0.5) or modestly improve (score > 0.5). Distribution should cluster around the neutral point. |
| Gen 20 | Fraction of D-archive programs with fitness in [0.1, 0.9] exceeds **60%**. Median fitness >= 0.45 (not collapsing below neutral). KDE of D fitness is non-degenerate (no single bin contains > 40% of mass). | If D programs are learning, the distribution should spread rightward from the neutral point. If they are not, it should remain clustered near 0.5. Either outcome is non-degenerate and informative -- the key test is that the distribution is NOT a point mass or bimodal with a mode at the boundary. |
| Gen 50 | D fitness variance has not collapsed to < 0.005 (SD < 0.07). The distribution retains structure (2+ distinct modes or smooth unimodal with SD > 0.07). | Long-run stability: if fitness variance collapses, it suggests convergence to a single D strategy, which may or may not lift G. If variance is maintained, MAP-Elites is providing diversity. |

**PASS criteria**: All three checkpoints must hold across >= 3 of 4 D runs. If any checkpoint fails on 2+ D runs, the mechanistic prediction FAILS -- meaning D fitness distribution has degenerated despite the tanh treatment, and the collapse mechanism is deeper than the fitness formula.

**Comparison to v2**: Under v2, D fitness was bimodal (60-90% point mass at 0.0, scattered positives above 0.0). The tanh treatment should eliminate the point mass entirely and produce a qualitatively different distribution. Section 8.3 (D Fitness Histogram) provides the visual evidence; this section pre-registers the quantitative thresholds.

### 2.3 Abandon Direction

If the treatment verification check passes (Section 2.2: < 10% at 0.000, confirming code is applied) AND the mechanistic prediction passes (Section 2.2a: non-degenerate D distribution) AND mu_G remains NULL (< 0.03449), then D-smoothing alone is insufficient despite eliminating the structural defect. The binding constraint is elsewhere. Next step: proceed to `adversarial_015` (full REDESIGN bundle: deterministic HoF + K=L=3 + cache_on edges) or library-drift bisection if adversarial_015 also fails.

If the treatment verification check fails (>= 10% at 0.000), the treatment was not correctly applied. Debug code path before re-running.

If the mechanistic prediction fails (D distribution degenerates despite tanh), the collapse mechanism is deeper than the fitness formula -- investigate whether D programs are converging to a single strategy or whether MAP-Elites selection pressure is overwhelming the tanh gradient.

---

## 3. Independent Variable

**Single IV**: D-side fitness function form.

| Variable | v2 (comparator) | d-smoothing-minimal (treatment) |
|---|---|---|
| D scoring formula | `delta = max(raw_delta, 0.0); score = min(delta / Q_MAX, 1.0)` | `score = 0.5 * (np.tanh(raw_delta / Q_MAX) + 1.0)` |
| D exception-path score | `score = 0.0` | `score = 0.5` (neutral, consistent with tanh(0)) |
| D per_opp_metrics `delta` field | Stores `max(raw_delta, 0.0)` (clamped) | Stores `raw_delta` (signed, unclamped) |
| D docstring (line 1) | "binary improvement scoring" | "continuous tanh improvement scoring" |

**Note: metrics.yaml fitness description is NOT changed** (see Section 5, controlled variables). The v2 wording (`"...Worsening counts as 0, not negative."`) is preserved verbatim to avoid changing the mutation prompt content. The description is technically inaccurate under tanh scoring, but the LLM does not compute the fitness function -- it writes D programs, and the evaluator applies the tanh mapping after execution. Keeping the description identical to v2 ensures the IV is purely the fitness function code, not the mutation prompt text.

**Exception-path incentive change (behavioral consequence)**: Under v2, a D program that throws an exception on an opponent receives `score=0.0` with `is_valid=1.0`. The `is_valid=1.0` flag means the exception record passes the `ConfigurableAggregator` validity gate and is included in the fitness mean, dragging fitness down. Under the tanh treatment, the same exception produces `score=0.5` (neutral), which is no longer penalized relative to a program that attempts an improvement but achieves `raw_delta=0` (also scoring 0.5). This weakens the incentive to produce robust (non-crashing) D code. This is NOT a confound (the change is an integral part of the treatment), but it is a known behavioral consequence. D exception rate is monitored as a secondary diagnostic (Section 8.7). If D exception rates are elevated relative to v2, this mechanism may contribute to systematic D fitness inflation without genuine improvement quality.

The comparison is against v2's historical data (mu_G=0.03315, N=4), not a concurrent control arm. This is justified because: (a) the v2 configuration is inherited verbatim except for the D evaluate.py, so a concurrent control arm would be an exact replication of v2 at additional cost; (b) v2's results are fresh (2026-04-22) and the infrastructure is unchanged; (c) v2's confidence interval is well-characterized (bootstrap 95% CI: [0.03001, 0.03630]).

**Note on G-side code**: G's `pop_a/evaluate.py` is at main HEAD (commit `2de8267e`, PR #219), which uses continuous `resistance_score = 1.0 - min(delta / Q_MAX, 1.0)`. This is NOT the same code that v2 ran under (v2 used binary `float(delta <= 0)`). This is a confound relative to v2's historical data -- see Section 9 (Confound 1) for assessment.

**Note on `delta` field semantics change (m2)**: The `per_opp_metrics.delta` field changes from `max(raw_delta, 0.0)` (always non-negative) to `raw_delta` (signed, potentially negative). Downstream consumers are affected:
1. **`DGTrackerStage`**: routes `delta > 0` to `dg_d_wins` and `delta <= 0` to `dg_g_resisted`. Under v2, `dg_g_resisted` was populated only when `delta == 0` (ties). Under treatment, negative deltas (D made things worse) also flow into `dg_g_resisted`. This changes its semantics from "D tried and tied" to "D tried and did not improve" -- arguably more correct.
2. **`DGImprovementTracker.record_batch`**: routes `delta > 0` to sorted sets. Negative deltas are stored in `dg_metrics` hash but not in `dg_improvements`. Correct behavior.
3. **`mean_improvement_raw` in aggregator config**: reduces via `op: mean, field: delta`. Under v2 this was `mean(max(raw, 0))` (non-negative). Under treatment, this becomes `mean(raw_delta)` (potentially negative). **Action required at implementation**: update `pop_b/metrics.yaml` field `mean_improvement_raw.lower_bound` from `0.0` to `-0.0365`. Since `include_in_prompts: false` for this metric, the change does not trigger a prompt content confound.

### 3.1 Design Decision: tanh Denominator

**Choice: Q_MAX (1x), not 2x Q_MAX.**

The codebase map recommends `2 * Q_MAX` as denominator for a wider gradient region. The literature brief recommends `Q_MAX`. I choose Q_MAX for the following reasons:

1. **Matches REDESIGN.md spec (Change 1)** -- the implementation is pre-reviewed and the denominator is locked in the design document.
2. **Gradient properties are favorable at Q_MAX**: `tanh'(0) = 1/Q_MAX = 27.4`. Programs at the current G population quality (0.033--0.035) sit in the linear regime of tanh. Saturation occurs at `raw_delta >> Q_MAX`, which is the correct behavior: programs that massively outperform their opponent should saturate near score=1.0.
3. **`tanh(1) = 0.762`** for `raw_delta = Q_MAX`. This means a full-Q_MAX improvement scores 0.881 (after affine rescale). The gradient is still non-zero -- the scorer is not saturated at the operationally relevant range.
4. **Confound avoidance**: changing the effective denominator would introduce a second free parameter (the temperature) alongside the functional form change. With Q_MAX, the only change is the shape of the mapping, not its scale.

The `2 * Q_MAX` alternative would produce `tanh(raw_delta / (2 * Q_MAX))` with a wider linear region: score at `raw_delta = Q_MAX` would be 0.731 instead of 0.881. This is a valid alternative but introduces an additional DoF that confounds the functional-form interpretation. If the Q_MAX denominator produces excessive saturation (detectable as score clustering near 0.88--1.0 for all non-collapsed D programs), the 2x variant is a well-defined follow-up.

### 3.2 Design Decision: G-D Asymmetry

**Choice: Accept the asymmetry. Do NOT update G's evaluate.py.**

After this experiment's treatment:
- G resistance: `1.0 - min(delta / Q_MAX, 1.0)` -- linear clip, range [0, 1]
- D fitness: `0.5 * (tanh(raw_delta / Q_MAX) + 1.0)` -- smooth tanh, range (0, 1)

These are **not zero-sum** (D.score + G.resistance != 1.0 for any raw_delta). The relationship is:
- `raw_delta = 0`: D gets 0.500, G gets 1.000. Sum = 1.500.
- `raw_delta = Q_MAX`: D gets 0.881, G gets 0.000. Sum = 0.881.
- `raw_delta = -Q_MAX`: D gets 0.119, G gets 1.000. Sum = 1.119.

This asymmetry is acceptable because:

1. **Scope constraint**: updating G to tanh would modify `pop_a/evaluate.py`, violating the "one file" rule. G's evaluate.py was JUST changed (PR #219, same day); stacking another change would confound the G-smoothing hotfix assessment with the D-smoothing experiment.
2. **Architectural independence**: G and D fitness signals are consumed independently by their respective `ConfigurableAggregator` instances. No code path computes or depends on D.score + G.resistance.
3. **Strictly better than v2**: Under v2, the asymmetry was worse: G had binary {0, 1} resistance while D had hard-floor {0, positive-clip}. Both sides had degenerate regions. Now G has continuous linear resistance and D has continuous tanh. The asymmetry is between two continuous forms, not between continuous and degenerate.
4. **Follow-up path**: if symmetrizing to tanh on both sides matters, `adversarial_021` (Arm B: G-only smoothed vs Arm C: both smoothed) can test it.

---

## 4. Dependent Variables

| Metric | How measured | Primary? | Direction |
|---|---|---|---|
| `actual_fitness` | Best-ever `max(post_q)` from G runs via `pop_a` evaluation | **Yes** | Higher is better |
| D fitness distribution shape | Fraction in [0.1, 0.9], variance, median at gen 5/20/50 | **Mechanistic (pre-registered, Section 2.2a)** | Non-degenerate is better |
| D point-mass fraction at gen 5 | Fraction of D-archive programs with fitness exactly 0.000 | **Treatment verification (Section 2.2)** | Lower is better (< 10% = PASS) |
| D mean engine fitness | Mean `fitness` across D-archive programs at closeout | Secondary | Higher is better |
| SBF-Lineage `kept/total` ratio | From D run logs per 10-gen bucket | Secondary (diagnostic) | Higher is better (>50% means SBF working) |
| G invalidity rate | Invalid / Total programs per G run | Secondary (diagnostic) | Compare to v1 (24--45%) and v2 (35--47%) |
| D invalidity rate | Invalid / Total programs per D run | Secondary (diagnostic) | Compare to v2 (10--17%) |
| D exception rate | Exceptions / Total evaluations per D run | Secondary (diagnostic) | Compare to v2; elevated rate may indicate weakened crash penalty (see Section 3 exception-path note) |
| D/G generation ratio | Engine gens at closeout | Secondary (diagnostic) | Compare to v2 (1.29x) and v1 (4.00x) |

---

## 5. Controlled Variables

All of v2's pinned configuration is preserved identically. The ONLY change is the D evaluate.py formula (Section 3).

| Parameter | Value | Source |
|---|---|---|
| `pipeline` | `heilbron_repro_v1` | Frozen v1 pipeline; shared across all runs |
| `num_parents` | 1 | No crossover |
| `max_elites_per_generation` | 8 | |
| `max_mutations_per_generation` | 8 | |
| `inner_iterations` | 1 | |
| `n_opponents` | 1 | K=1 opponent context |
| `source_prompt_k` | 1 | L=1 source prompt |
| `mutation_mode` | rewrite | |
| `pre_step_hook.drift_cap` | 100000 | Effectively no-op; preserves v2's loose coupling |
| `pre_step_hook.sync_every_n_epochs` | 1 | |
| `max_generations` | 200 | Same target as v2 |
| `stage_timeout` | 900 | 15 min; matches v2's actual launch.sh values |
| `dag_timeout` | 3600 | 60 min; matches v2's actual launch.sh values |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` via LiteLLM 10.232.30.185:4000 | Same mutation LLM |
| `pipeline_builder.lineage_filter.min_shared` | 1 | SBF-Lineage filter (v2 setting) |
| `pipeline_builder.lineage_filter.inject_shared_evidence` | true | SBF-Lineage evidence injection (v2 setting) |
| `stopper` | `max_generations` | No early-stop per run |
| `evolution` | `steady_state` | |
| Git commit for `pop_a/evaluate.py` | `2de8267e` (PR #219) or later on main | G-side smoothing hotfix; inherited as-is |
| `pop_b/metrics.yaml` fitness description | `"MAP-Elites selection signal: mean over opponent configs of min(improvement / 0.0365, 1). Worsening counts as 0, not negative."` | **Frozen identical to v2** -- technically inaccurate under tanh but preserves prompt content parity. `include_in_prompts: true`, so any text change would alter the D mutation prompt (PATTERNS.md: `include_in_prompts` as hidden IV). |
| `pop_b/metrics.yaml` all other fields | Identical to v2 except `mean_improvement_raw.lower_bound` (see Section 3 m2 note) | Non-prompt fields; `include_in_prompts: false` on affected metrics |

**Timeout note**: v2's `experiment.yaml` recorded `stage_timeout: 3000` and `dag_timeout: 7200`, but v2's actual `launch.sh` used 900/3600. This experiment uses the launch.sh values (900/3600) to match v2's actual runtime behavior, not its manifest metadata. The discrepancy in v2 is documented in v2's `04_issues_log.md`.

---

## 5a. Per-Role Asymmetric Config

Inherited verbatim from v2 (Section 5a of v2's `01_design.md`):

| Parameter | G runs (constructor) | D runs (improver) | Rationale |
|---|---|---|---|
| `opponent_sampling_mode` | `softmax` | `top_k` | G: broad stochastic exposure. D: deterministic sampling. |
| `pipeline_builder.archive_reeval` | `false` | `true` | D re-scores on opponent_ids change. G: stochastic IDs shift each gen. |
| `engine_config.refresh_order` | `fifo` (default) | `generation_bucketed` | D-only fix for cross-program tracker race. |
| `engine_config.refresh_passes` | `1` (default) | `2` | D-only: closes two-sided refresh race for SBF-Lineage. |
| `opponent_result_mode` | `exec` | `cached` | G runs D improvers; D reads G's stored output. |
| `population_role` | `constructor` | `improver` | |
| Effective LineageStage | Base `LineageStage` | `SharedBenchmarkFilteredLineageStage` (PR #215) | SBF-Lineage on D only. |

---

## 6. Run Design

8 runs (2 arms x 2 pairs x G/D), identical structure to v2. Same seeds, same prefixes, same DBs.

| Label | Role | Arm | DB | Pair-opponent DB | Feedback mode |
|---|---|---|---|---|---|
| A1_G | constructor | Composition | 1 | 2 | composition |
| A1_D | improver | Composition | 2 | 1 | composition |
| A2_G | constructor | Composition | 3 | 4 | composition |
| A2_D | improver | Composition | 4 | 3 | composition |
| C1_G | constructor | Gradient-in-prompt | 5 | 6 | gradient_in_prompt |
| C1_D | improver | Gradient-in-prompt | 6 | 5 | gradient_in_prompt |
| C2_G | constructor | Gradient-in-prompt | 7 | 8 | gradient_in_prompt |
| C2_D | improver | Gradient-in-prompt | 8 | 7 | gradient_in_prompt |

The 2-arm structure (Composition vs Gradient-in-prompt) is retained for consistency with v2, even though feedback mode is confirmed NULL (PATTERNS.md: "Direction CLOSED", 9 experiments, 20+ pairs). This enables direct cell-by-cell comparison against v2's results and provides an internal sanity check: cross-arm delta should remain < 0.002 in raw actual_fitness units.

### 6.1 Extra Overrides per Run

Identical to v2's `experiment.yaml` runs[*].extra_overrides. The treatment (D tanh scoring) is implemented via code change to `pop_b/evaluate.py`, not via Hydra override.

**G runs** (A1_G, A2_G, C1_G, C2_G):
```yaml
- aggregator=heilbron_constructor
- evolution=steady_state
- stopper=max_generations
- opponent_redis_db=<paired D db>
- opponent_redis_prefix=heilbron_repro_v1/pop_b
- feedback_mode=<composition|gradient_in_prompt>
- population_role=constructor
- post_step_hook=\${composition_injection_hook}  # (Composition arm only)
- opponent_result_mode=exec
- opponent_sampling_mode=softmax
- pipeline_builder.archive_reeval=false
- pipeline_builder.per_opponent_timeout=\${stage_timeout}
```

**D runs** (A1_D, A2_D, C1_D, C2_D):
```yaml
- aggregator=heilbron_improver
- evolution=steady_state
- stopper=max_generations
- opponent_redis_db=<paired G db>
- opponent_redis_prefix=heilbron_repro_v1/pop_a
- feedback_mode=<composition|gradient_in_prompt>
- population_role=improver
- opponent_result_mode=cached
- opponent_sampling_mode=top_k
- pipeline_builder.archive_reeval=true
- engine_config.refresh_order=generation_bucketed
- engine_config.refresh_passes=2
```

---

## 7. Sample Size and Power

**N=4 G runs** for the primary metric, same as v1 and v2. This is the established heilbron adversarial budget.

With N=4 per condition and estimated sigma=0.003 (from v2's SD=0.00295), a one-sided Welch t-test comparing against v2's mu=0.03315 has approximately:
- **~80% power** for a raw delta of 0.005 (mu_G = 0.0382, ~15% relative increase) -- large effect, unlikely
- **~50% power** for a raw delta of 0.003 (mu_G = 0.0362, ~9% relative increase) -- moderate effect near POSITIVE threshold
- **~20% power** for a raw delta of 0.001 (mu_G = 0.0342, ~3% relative increase) -- small effect near SUGGESTIVE threshold

This experiment is adequately powered to detect a POSITIVE result (strong D-smoothing effect) but poorly powered to distinguish SUGGESTIVE from NULL. This is acceptable because the primary question is whether D-smoothing produces any directional movement, not whether it produces a precisely estimated small effect. The mechanistic prediction (D fitness distribution shape, Section 2.2a) provides a complementary signal that does not depend on mu_G power.

With N=4, formal statistical testing has limited value. Results will be reported as effect magnitude and consistency across runs, with bootstrap confidence intervals. The verdict is derived from the pre-registered thresholds (Section 2.1), not from p-values.

---

## 8. Diagnostics and Monitoring

### 8.1 Treatment Verification Diagnostic: D Point-Mass Fraction

At gen 5, query each D run's archive for the fraction of programs with `fitness` exactly equal to 0.000 (within floating-point epsilon of 1e-8). This is a **code-application check** (Section 2.2), not a mechanistic prediction -- the < 10% threshold is satisfied by construction if the tanh code is correctly applied.

| Run | Expected fraction (v2 baseline) | Success criterion |
|---|---|---|
| All 4 D runs | 60--90% at 0.000 (k5-budget-loose empirical) | **< 10% at 0.000** |

Under tanh scoring, `raw_delta = 0` maps to score 0.500, and `raw_delta < 0` maps to (0.0, 0.500). The ONLY way to get score exactly 0.000 is via `_invalid_opp_metrics()` (gated by `is_valid=0.0`, excluded from fitness by the aggregator). The point mass at 0.000 vanishes by construction. A failure here indicates a code deployment issue, not an evolutionary dynamics finding.

**Implementation**: After gen 5 completes on each D run, query Redis:
```bash
gigaevo -r "heilbron_repro_v1/pop_b@<db>" archive --metric fitness --filter "fitness < 0.001" --count
```
Report the ratio relative to total archive size. If any D run shows > 10% at fitness < 0.001, flag as treatment verification failure.

### 8.2 Arms-Race Plot

Paired actual_fitness trajectories (G vs D per pair), same format as v2's watchdog `arms-race` command. Look for:
- **D trajectories rising** (broken D collapse) -- expected positive signal
- **G trajectories rising in response** -- expected secondary signal if arms race engages
- **Cross-pair consistency** -- all 4 pairs should show qualitatively similar dynamics

### 8.3 D Fitness Histogram at Gen 5, 20, 50 (Primary Mechanistic Evidence)

**This diagnostic provides the visual evidence for the pre-registered mechanistic prediction (Section 2.2a).** Histogram of D archive `fitness` values at three checkpoints (gen 5, 20, 50). Compare shape against v2's bimodal distribution (point mass at 0.0 + scattered positives).

Quantitative thresholds from Section 2.2a are evaluated here:
- **Gen 5**: fraction in [0.1, 0.9] > 70%; median in [0.35, 0.65]; variance > 0.01.
- **Gen 20**: fraction in [0.1, 0.9] > 60%; median >= 0.45; no single histogram bin > 40% of mass.
- **Gen 50**: variance > 0.005 (SD > 0.07); distribution retains structure.

Under tanh treatment, expect a unimodal distribution centered near 0.5 at gen 5 (the neutral point for `raw_delta = 0`), potentially spreading or shifting rightward by gen 20-50 as D programs learn to improve opponent configurations.

### 8.4 SBF-Lineage Efficacy (kept/total)

Monitor D run logs for `[LineageStage:SharedBenchmark] kept X/Y parents`. Report kept/total per 10-gen bucket. Under v2 (broken D), SBF-Lineage may have been starved of useful content because D's mutation context carried binary fitness. Under smoothed D, SBF-Lineage should have richer narratives. If kept/total rises substantially from v2's baseline, this is a secondary interaction effect.

### 8.5 G Invalidity Rate

v2 showed 35--47% G invalidity (elevated vs v1's 24--45%). The literature brief hypothesizes this may be a SOFTMAX-under-broken-D artifact. If D is now healthy, SOFTMAX may perform better. Monitor for a return to v1-level invalidity rates (24--45% or lower) as a secondary signal.

### 8.6 D/G Generation Ratio

v2's two-pass bucketed refresh crushed D's speed advantage (1.29x vs v1's 4.00x). This experiment inherits the same refresh config. Monitor to confirm similar ratio. A dramatic shift would indicate infrastructure variance.

### 8.7 D Exception Rate

Monitor the fraction of D per-opponent evaluations that hit the exception path (`except Exception` block in `pop_b/evaluate.py`). Under v2, exceptions produced `score=0.0` (penalizing). Under the tanh treatment, exceptions produce `score=0.5` (neutral). If the exception rate is elevated relative to v2, the tanh treatment may be inflating D fitness by removing the crash penalty rather than by enabling genuine improvement. Compare per-D-run exception rate to v2's baseline. If exception rate exceeds 20% on any D run, flag for investigation.

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|---|---|---|
| 1 | **G-side code differs from v2**: v2 ran under binary `float(delta<=0)` G resistance; this experiment runs under PR #219's continuous `1.0 - min(delta/Q_MAX, 1.0)`. | **MODERATE** -- the G-side change could independently affect mu_G, confounding the D-smoothing attribution. | (a) The G change is monotonic: continuous resistance is strictly more informative than binary resistance, so any G-side lift is directionally aligned with the D-smoothing hypothesis (both remove degenerate fitness regions). (b) The G change landed as a hotfix on main; reverting it would create a separate branch divergence confound. (c) If the experiment is POSITIVE, the attribution is "D-smoothing + G-smoothing together lift mu_G" -- which is the dual-smoothing result we want for the paper. If NULL, D-smoothing alone is insufficient even with G-smoothing, which is also informative. (d) `adversarial_021` can retrospectively test G-only vs both-smoothed if needed. |
| 2 | **Library drift from v2**: Several merges between v2's launch commit (`532ac3e5`) and current HEAD. | **LOW** -- symmetric across all 8 runs; cannot explain between-run variance. | `environment_freeze.txt` captures exact commit. Drift is identical to v2's Confound 8 analysis: only hyperparameters, problem files, and frozen evaluate.py are controlled cross-experiment; engine code is at HEAD. |
| 3 | **Redis state carry-over**: v2's data may persist in DBs 1--8. | **LOW** -- standard mitigation. | Flush DBs 1--8 via `gigaevo flush --db N --confirm` before launch. Startup assertion: if DB is non-empty, abort. |
| 4 | **stage_timeout/dag_timeout discrepancy**: v2's manifest said 3000/7200 but launch.sh used 900/3600. | **NONE** -- explicitly controlled. | This experiment uses 900/3600, matching v2's actual runtime values. Documented in Section 5. |
| 5 | **SOFTMAX + D-collapse interaction (v2 suggestive signal)**: SOFTMAX may have degraded G mutation quality when D was collapsed. Under smoothed D, this confound may be LIFTED. | **POSITIVE confound** -- if D health improves SOFTMAX efficacy, the lift is attributable to the D-smoothing treatment (which enabled SOFTMAX to work). Not a threat to internal validity. | Monitor G invalidity rate as secondary diagnostic (Section 8.5). |
| 6 | **Historical comparator, not concurrent control**: v2 data is the control arm, not a simultaneously-run control. | **LOW** -- v2 ran 2 days ago on the same server, same model, same proxy. | The concurrent-control alternative would double compute cost (16 runs) to replicate an already-characterized NULL result. The risk is LLM/proxy drift over 2 days, which is negligible given LiteLLM proxy uses deterministic model routing. |
| 7 | **Two-pass refresh overhead on D**: v2 showed D/G ratio of 1.29x vs v1's 4.00x. D's slow refresh could limit D's ability to diversify under smoothed fitness. | **MODERATE** -- D may not explore the newly-opened fitness landscape fast enough. | Accepted as controlled variable (same config as v2). If D trajectories show improvement but are sluggish, refresh overhead is a candidate for the next experiment's IV. |

---

## 10. Stop Criteria

- **Per-run stop**: `stopper=max_generations`, `max_generations=200`. No programmatic early-stop.
- **Experiment-level abort**: if 4+ of 8 processes die within first 2 hours, or if watchdog detects `invalidity_rate > 0.75` AND `stagnation_window > 10` on >= 2 G runs simultaneously.
- **Wall-clock cap**: 28 hours hard cap (same as v2). If 28h is reached, terminate all runs uniformly and analyze at achieved generation depth. Any early termination must be recorded as an amendment in `03_plan.md` BEFORE results analysis (protocol gap identified in v2 Deviation 2). **Expected generation depth at 28h**: v2 reached G gens 36--55 (mean ~45) and D gens 38--91 (mean ~60) in ~23h. At the same per-gen rate, 28h should yield G gens ~44--67 (mean ~55) and D gens ~46--110 (mean ~73). Partial runs at these generation depths are acceptable for the primary analysis: mu_G is computed from best-ever actual_fitness, which is a monotone function of generation depth. The mechanistic prediction (Section 2.2a) has checkpoints at gen 5, 20, and 50 -- all reachable within 28h based on v2's rate.
- **Treatment verification failure**: if any D run shows > 5% of programs at `fitness < 0.001` at gen 3, halt that D run and its paired G run. Investigate code path. If 2+ pairs fail treatment verification, abort experiment entirely and debug.

---

## 11. Treatment Verification

### 11.1 Code-Change Observable Evidence

The treatment is applied via code edit to `problems/heilbron_repro_v1/pop_b/evaluate.py`, not via Hydra override. Observable evidence that the treatment is active:

1. **File diff**: `pop_b/evaluate.py` contains `np.tanh` on the scoring line. Verify via `git diff` between v2 branch and this experiment's branch.
2. **D fitness histogram at gen 5**: non-zero mass below the median (scores distributed around 0.5, not piled at 0.0). This is the treatment verification diagnostic (Section 8.1) and the first checkpoint of the mechanistic prediction (Section 8.3).
3. **D per_opp_metrics artifact**: `delta` field contains signed (possibly negative) values, not floor-clamped values. Verify by inspecting a sample D program's artifact in Redis after gen 1.
4. **Exception-path score**: if any D program's `improve_fn` throws an exception, the per_opp_metrics for that slot should show `score = 0.5` (not 0.0). Verify in D run logs.

### 11.2 Hydra Override Verification

Extra overrides per run are IDENTICAL to v2 because the D fitness change is a code-level treatment, not a config-level treatment. The `--cfg job` pre-launch gate from v2 (Section 12.0 of v2 `01_design.md`) applies unchanged:

```bash
# G runs: verify softmax, archive_reeval=false
for r in A1_G A2_G C1_G C2_G; do
  $GIGAEVO_PYTHON run.py <r-overrides> --cfg job 2>&1 | grep -E \
    'opponent_sampling_mode|archive_reeval|refresh_order|refresh_passes'
done  # expect: softmax, false, (refresh absent or fifo/1)

# D runs: verify top_k, archive_reeval=true, bucketed + passes=2
for r in A1_D A2_D C1_D C2_D; do
  $GIGAEVO_PYTHON run.py <r-overrides> --cfg job 2>&1 | grep -E \
    'opponent_sampling_mode|archive_reeval|refresh_order|refresh_passes'
done  # expect: top_k, true, generation_bucketed, 2
```

### 11.3 Smoke Test Contract

Before full launch, run a paired smoke test on DBs 11/12 for 3 generations:

1. Launch A1_G (DB 11) + A1_D (DB 12) with `max_generations=3`.
2. After gen 3, query D's archive:
   - `fitness < 0.001` fraction must be **< 5%** (tight threshold -- under tanh, only `is_valid=0.0` paths produce score near 0.0, and those are gated out of the fitness aggregation).
   - **Median D fitness must fall in [0.3, 0.7]** -- the expected range for neutral-to-modest improvers under tanh. A median outside this range at gen 3 would indicate an unexpected interaction.
   - At least one D program must have `fitness` in range (0.4, 0.6) -- indicating scores near the neutral point.
3. Inspect a sample D program's per_opp_metrics artifact: `delta` field should be a signed float (possibly negative), not clamped to zero.
4. If smoke passes, flush DBs 11/12 and proceed to full launch on DBs 1--8.

---

## 12. Compute Budget

| Resource | Estimated |
|---|---|
| Wall time | ~18--24h (v2 took ~23h to reach gen 36--55 G / 38--91 D) |
| Hard cap | 28h |
| Server | 10.232.30.185 (8 concurrent processes) |
| Redis DBs | 1--8 (production), 11--12 (smoke test) |
| LLM calls | ~32k completions across all runs (same estimate as v2) |
| Mutation LLM | Qwen3-235B-A22B-Thinking-2507 via LiteLLM proxy |

---

## 13. Reproducibility

### 13.1 Predecessor Commits

| Component | Commit | Note |
|---|---|---|
| v2 launch | `532ac3e5` | v2's exact launch commit |
| G-smoothing hotfix | `2de8267e` (PR #219) | Continuous G resistance; now on main |
| D hard-floor scoring (pre-change) | `2de8267e` or later | `pop_b/evaluate.py` still has hard-floor on main |
| This experiment's branch | TBD (pre-registration commit) | Will contain the D tanh change |

### 13.2 Dataset Snapshot

Heilbronn N=11 problem uses synthetic point configurations generated at evaluation time by the Constructor population. No fixed dataset. The Q_MAX=0.0365 value is the known Heilbronn optimum for n=11 (hardcoded in both `pop_a` and `pop_b` evaluate.py files). No dataset snapshot required beyond the problem file checksums.

### 13.3 Environment

- Python: `/home/jovyan/.mlspace/envs/evo/bin/python3`
- LiteLLM proxy: `http://10.232.30.185:4000/v1`
- Model: `Qwen3-235B-A22B-Thinking-2507`
- Auth: `Bearer sk-gigaevo`
- `environment_freeze.txt` will be generated at launch time (pip freeze + git commit hash)

---

## 14. Pre-Registered Analysis Plan

### 14.1 Primary

mu_G (best-ever actual_fitness across 4 G runs) compared against:
- v2 historical comparator: mu_G=0.03315
- baseline-repro: mu_G=0.03449

Report bootstrap 95% CI (B=10000). Verdict from effect-size thresholds (Section 2.1).

### 14.2 Treatment Verification

D point-mass fraction at gen 5 (Section 8.1). Report per-D-run and mean. Binary outcome: PASS (< 10%) or FAIL (>= 10%). This is a code-application check, not a scientific prediction (Section 2.2).

### 14.2a Mechanistic Prediction

D fitness distribution shape at gen 5, 20, 50 (Section 2.2a, Section 8.3). Report per-D-run: fraction in [0.1, 0.9], median, variance, KDE shape. Outcome: PASS (thresholds met on >= 3 of 4 D runs at all checkpoints) or FAIL. This is the primary mechanistic evidence for whether D-smoothing produces a non-degenerate fitness landscape.

### 14.3 Per-Arm Breakdown

Split by Composition vs Gradient-in-prompt. Cross-arm raw delta should be < 0.002 in actual_fitness units (confirmation of feedback-mode NULL). If cross-arm delta exceeds 0.005, flag as anomalous.

### 14.4 D Trajectory Analysis

D mean fitness trajectory over generations (10-gen buckets). Compare shape against v2's collapsed trajectory. Expected: monotonically increasing or stable around 0.5, not collapsing to 0.0.

### 14.5 Secondary Diagnostics

Report SBF-Lineage kept/total, G invalidity rate, D exception rate, D/G generation ratio per Section 8.

---

*Ready for Reviewer-2's scrutiny.*
