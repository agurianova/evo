# Experimental Design: K=5 Compute Budget Asymmetry with Loose G/D Coupling

**Date**: 2026-04-16
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft -- awaiting Reviewer-2

---

## 1. Research Question

Does K=5 compute budget asymmetry (Improver processes 40 mutations/epoch vs Constructor 8) combined with loose G/D coupling (sync_min_delta=1) break Improver stagnation and match or exceed v1's 105% SOTA peak (0.03650) on the Heilbronn triangle problem (n=11)?

**Context**: Eight adversarial experiments (64+ runs) have established that Improver stagnation is structural: K=0/1/3 opponent context, bidirectional code access, soft fitness, GAN resistance, archive re-evaluation, source code injection, composition feedback, gradient-in-prompt feedback, loose coupling, and tight coupling have all failed to break it. Every prior intervention changed the *information* flowing to the Improver, the *information architecture*, or the *coupling granularity* -- but none changed the *compute budget*. Compute budget asymmetry is the single remaining untested intervention class.

The strongest empirical signal comes from the v1/v2 comparison: v1 (accidental min_delta=1) produced peaks at 0.03648/0.03650 (>=105% SOTA) by generation 8-12, while v2 (intentional min_delta=8) produced only 0.03588 (104% baseline) despite running 4-6x more generations. The most parsimonious explanation: loose coupling gave D many micro-steps per G epoch, creating implicit compute budget asymmetry favoring D. This experiment makes that implicit asymmetry explicit (D: 40 mutations/epoch) and combines it with the known-good loose coupling (sync_min_delta=1).

Feedback mode is NOT an IV. The direction is CLOSED (8 pairs, 16 runs across v1+v2, cross-arm delta < 0.001). All runs use composition (simplest config).

---

## 2. Hypotheses

**H0**: K=5 compute budget asymmetry with loose coupling does not change max(G,D) actual_fitness relative to the within-experiment control (K=1 symmetric, sync_min_delta=8).

**H1**: K=5 compute budget asymmetry with loose coupling produces max(G,D) actual_fitness meaningfully different from the control.

### Effect-size thresholds (pre-registered)

| max(G,D) actual_fitness (mean over replicates) | Interpretation |
|---|---|
| >= 0.03649 (matches v1 peak) | **STRONG POSITIVE** -- budget asymmetry + loose coupling reproduces/exceeds v1 |
| >= 0.03549 (baseline + 0.001) | **POSITIVE** -- meaningful improvement over baseline |
| 0.03349 to 0.03549 (within 0.001 of baseline) | **NULL** -- no meaningful effect detected |
| < 0.03349 (baseline - 0.001) | **NEGATIVE** -- treatment actively hurts |

**Baseline reference**: 0.03449 (heilbron/baseline-repro mean best-overall, N=4, SD=0.00212).

### Stagnation assessment

| Improver acceptance rate (rolling 10-gen window, after gen 20) | Interpretation |
|---|---|
| > 5% in >= 2/3 treatment replicates | **STAGNATION BROKEN** -- first intervention to achieve this |
| > 5% in 1/3 treatment replicates | **SUGGESTIVE** -- partial evidence, warrants replication |
| <= 5% in all treatment replicates | **STAGNATION PERSISTS** -- compute budget insufficient; search-space hypothesis promoted |

---

## 3. Independent Variable(s)

| Variable | Control value | Treatment value |
|----------|---------------|-----------------|
| **Compute budget asymmetry** (combined) | D: max_mutations_per_generation=8, sync_min_delta=8 (symmetric, tight coupling) | D: max_mutations_per_generation=40, sync_min_delta=1 (K=5 budget, loose coupling) |

**Single IV**: The treatment is a combined intervention -- compute budget asymmetry (40 vs 8 mutations/epoch for D) plus loose coupling (sync_min_delta=1 vs 8 for D). These are deliberately bundled because:

1. The v1/v2 comparison provides evidence that loose coupling is the performance-enabling condition. Testing K=5 with tight coupling would likely reproduce v2's underperformance.
2. A 2x2 factorial (budget x coupling) would require 4 arms at N=3/arm = 24 runs, exceeding available resources.
3. If the combined treatment works, a follow-up ablation (K=5 with tight coupling, K=1 with loose coupling) can decompose the contributions.

**All G runs are identical across conditions.** Only D runs differ. G receives `max_mutations_per_generation=8` and `sync_min_delta=8` (defaults) in both arms.

### What changes between conditions

| Parameter | Control D | Treatment D | G (both arms) |
|-----------|-----------|-------------|---------------|
| max_mutations_per_generation | 8 | 40 | 8 |
| sync_min_delta | 8 (default) | 1 | 8 (default) |
| Expected D/G program ratio | ~1:1 | ~5.26:1 | -- |
| D blocking fraction | ~50% | ~0% | -- |
| G blocking fraction | ~50% | ~80% | -- |

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| max(G, D) actual_fitness per pair | Best actual_fitness from either population across all generations | **Yes** |
| Improver acceptance rate after gen 20 | Rolling 10-gen window: fraction of D mutation attempts producing accepted elites, gen 20-50 | Secondary (stagnation diagnostic) |
| D/G program production ratio | `engine:programs_processed` from D Redis / G Redis at experiment end | Secondary (treatment verification) |
| Constructor actual_fitness at gen 50 | Best actual_fitness from G population alone | Secondary (continuity with prior experiments) |
| Wall-clock time per generation | Log timestamps | Exploratory |
| Invalidity rate per run | Invalid / (valid + invalid) mutations, cumulative | Exploratory |

**Primary metric**: max(G, D) actual_fitness per pair, averaged across 3 replicates per arm. This metric was adopted starting with asymmetric-iterations-v2 because in 3/4 baseline-repro pairs, Improver's best actual_fitness >= Constructor's. Using max(G, D) captures the best from either population and avoids the arbitrary choice of which population's frontier to report.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| `pipeline` | `adversarial_asymmetric` | Same pipeline as v1/v2; battle-tested across 16 runs |
| `evolution` | `steady_state` | Required for adversarial_asymmetric (KF-01) |
| `max_generations` | 50 | Match v1/v2 and baseline-repro; stopper enforced |
| `stopper` | `max_generations` with `max_generations=50` | Hard stop at gen 50 |
| G `max_mutations_per_generation` | 8 | Identical across all 12 runs (6 G runs) |
| G `sync_min_delta` | 8 (default, not overridden) | G behavior identical in both arms |
| `max_elites_per_generation` | 8 | Match baseline-repro; identical across all 12 runs |
| `mutation_mode` | rewrite | Match baseline-repro |
| `model_name` | Qwen3-235B-A22B-Thinking-2507 | Same mutation LLM across all runs |
| `llm_base_url` | http://10.232.30.185:4000/v1 | LiteLLM proxy, single endpoint |
| `num_parents` | 1 | Independent mutation, no crossover |
| `stage_timeout` | 2400 | Match v2 (reduced from 3000 in v1) |
| `dag_timeout` | 2400 | Match v2 |
| `significant_change` | 0.01 | Match all prior heilbron experiments |
| `inner_iterations` | 1 | No inner iteration loop (K=5 is via epoch size, not inner loops) |
| `n_opponents` | 1 | Match v2; single opponent per evaluation |
| `source_prompt_k` | 1 | Match v2 |
| `archive_reeval` | false | Archive re-eval confirmed NEGATIVE (adversarial-dynamic-updates) |
| `feedback_mode` | composition | Feedback mode is CLOSED (NULL); use simplest config |
| `d_sees_g_source` | true | D sees G source code in both arms (match v1/v2) |
| `d_archive_persistent` | true | Match v1/v2 |
| Initial seed | `grid.py` (G), `seed.py` (D) | Identical across all runs, both arms |
| Problem name | `heilbron_adversarial/pop_a` (G), `heilbron_adversarial/pop_b` (D) | Match all prior heilbron adversarial experiments |
| Server | 10.232.30.185 (LiteLLM proxy) | All runs through same proxy |

### Mechanism clarification: K=5 via epoch size, not inner iterations

Prior designs (heilbron/asymmetric-iterations) conceived K=5 as an inner iteration loop where D runs K=5 inner MAP-Elites iterations per outer generation. That mechanism required new pipeline code and was never implemented (the v1 amendment reduced K to 1).

This design achieves the same effective compute ratio through a simpler mechanism: increasing D's `max_mutations_per_generation` from 8 to 40. Since each "epoch" in the steady-state engine processes `max_mutations_per_generation` programs before triggering the sync hook, D processes 40 programs per epoch while G processes 8. Combined with `sync_min_delta=1` on D (D unblocks after G processes just 1 program), D effectively runs ~5 epochs for every 1 G epoch. This is mechanistically equivalent to K=5 inner iterations but requires zero new code -- it is a config-only treatment.

Verified by simulation (200 reps): D produces ~5.26x more programs than G (95% CI: [5.24, 5.28]). Control (both at 8/8): ratio 1.02 (essentially 1:1).

---

## 6. Run Design Table

### Treatment arm: K=5 budget + loose coupling -- 3 pairs (6 runs)

| Run | Label | DB | Role | max_mutations_per_generation | sync_min_delta | Condition |
|-----|-------|----|------|------------------------------|----------------|-----------|
| 1 | T1_G | 1 | Constructor (G) | 8 (default) | 8 (default) | Treatment pair 1, G |
| 2 | T1_D | 2 | Improver (D) | 40 | 1 | Treatment pair 1, D |
| 3 | T2_G | 3 | Constructor (G) | 8 (default) | 8 (default) | Treatment pair 2, G |
| 4 | T2_D | 4 | Improver (D) | 40 | 1 | Treatment pair 2, D |
| 5 | T3_G | 5 | Constructor (G) | 8 (default) | 8 (default) | Treatment pair 3, G |
| 6 | T3_D | 6 | Improver (D) | 40 | 1 | Treatment pair 3, D |

### Control arm: K=1 symmetric (v2 replication) -- 3 pairs (6 runs)

| Run | Label | DB | Role | max_mutations_per_generation | sync_min_delta | Condition |
|-----|-------|----|------|------------------------------|----------------|-----------|
| 7 | C1_G | 7 | Constructor (G) | 8 (default) | 8 (default) | Control pair 1, G |
| 8 | C1_D | 8 | Improver (D) | 8 (default) | 8 (default) | Control pair 1, D |
| 9 | C2_G | 9 | Constructor (G) | 8 (default) | 8 (default) | Control pair 2, G |
| 10 | C2_D | 10 | Improver (D) | 8 (default) | 8 (default) | Control pair 2, D |
| 11 | C3_G | 11 | Constructor (G) | 8 (default) | 8 (default) | Control pair 3, G |
| 12 | C3_D | 12 | Improver (D) | 8 (default) | 8 (default) | Control pair 3, D |

**Total**: 12 runs (6 pairs), DBs 1-12.

### Extra overrides per condition

**Treatment D runs (T1_D, T2_D, T3_D)**:
```
evolution=steady_state
max_mutations_per_generation=40
sync_min_delta=1
opponent_redis_db=<G_DB>
opponent_redis_prefix=heilbron_adversarial/pop_a
feedback_mode=composition
population_role=improver
d_sees_g_source=true
d_archive_persistent=true
```

**Control D runs (C1_D, C2_D, C3_D)**:
```
evolution=steady_state
opponent_redis_db=<G_DB>
opponent_redis_prefix=heilbron_adversarial/pop_a
feedback_mode=composition
population_role=improver
d_sees_g_source=true
d_archive_persistent=true
```

Note: Control D runs do NOT override `max_mutations_per_generation` or `sync_min_delta`, so they inherit defaults (8 and 8 respectively) from `config/constants/evolution.yaml`.

**All G runs (T1_G through C3_G)**:
```
evolution=steady_state
opponent_redis_db=<D_DB>
opponent_redis_prefix=heilbron_adversarial/pop_b
feedback_mode=composition
population_role=constructor
post_step_hook=\${composition_injection_hook}
```

G runs are identical across treatment and control. This is the key design property: the only difference between arms is D's config.

---

## 7. Sample Size Justification

N=3 pairs per arm (6 pairs total, 12 runs). From baseline-repro (N=4): SD(best-overall actual_fitness) = 0.00212. The exploitable range between baseline (0.03449) and Q_MAX (0.0365) is only 0.002, making effect detection particularly challenging.

**Minimum detectable effect at N=3**: With sigma=0.00212, a two-sample t-test at alpha=0.10 one-sided with N=3 per arm has approximately 60% power to detect an effect of d=0.002 (Cohen's d ~0.94). At N=2 per arm (prior experiments), power drops below 40%. N=3 is the minimum viable sample size for this narrow effect window.

**With N=3 runs per condition, this experiment measures effect magnitude and consistency. Formal statistical testing would require N >= 8 runs per condition at 80% power.** The design prioritizes three properties: (1) observing whether the treatment reproduces v1's peaks (0.03650), (2) measuring within-experiment treatment-control difference, and (3) assessing cross-replicate consistency. If all 3 treatment replicates exceed the best control replicate, that is informative regardless of p-values.

### Why a within-experiment control (not just historical baseline)

The v2 experiment changed the config infrastructure (sync_min_delta decoupled from max_mutations_per_generation). A within-experiment control ensures:
1. The control arm reproduces v2 behavior under the new config, confirming no regression from the decoupling change.
2. The treatment-control comparison is concurrent (same servers, same LLM proxy load, same time period), eliminating temporal confounds.
3. Historical baseline comparison (to 0.03449) remains secondary.

---

## 8. Statistical Test

**Primary comparison**: Treatment arm mean max(G,D) vs Control arm mean max(G,D). Welch's two-sample t-test (alpha=0.10, one-sided: treatment > control). Report Cohen's d, 90% CI, and p-value. The test is underpowered at N=3/arm; the verdict relies on pre-registered effect-size thresholds, not p-values.

**Effect magnitude**: Report per-pair max(G,D), arm means, grand mean, and range. The primary inferential method is observing: (a) whether all treatment replicates exceed 0.03549 (POSITIVE threshold), and (b) whether the treatment arm mean exceeds the control arm mean by at least 0.001.

**Secondary**: Each arm's mean max(G,D) vs historical baseline (0.03449). If the control arm mean is within 0.001 of 0.03449, the within-experiment baseline is validated. If it deviates by > 0.002, the historical baseline comparison is unreliable and all conclusions are relativized to the within-experiment control.

**Stagnation assessment**: Descriptive. Report Improver acceptance rate trajectories for all 6 D runs. Compare treatment vs control rates after gen 20.

---

## 9. Known Confounds and Mitigations

| # | Confound | Risk | Mitigation |
|---|----------|------|-----------|
| 1 | **Compound treatment** (K=5 budget + loose coupling bundled) | MEDIUM | Deliberate bundling. The v1/v2 evidence suggests loose coupling is necessary for budget asymmetry to be effective. Testing them separately would require a 2x2 factorial (24 runs). If the combined treatment is POSITIVE, a follow-up ablation (K=5+tight vs K=1+loose) can decompose contributions. If NULL, both components fail together and neither warrants solo investigation. |
| 2 | **D compute advantage may cause D overfitting** | MEDIUM | GAN literature warns that training D too much causes D to overfit to current G. In GigaEvo, D "overfitting" would manifest as high D acceptance rate early but declining over time, with D's improvements not transferring to G. Monitor: D acceptance rate trajectory, composition injection acceptance rate, D archive diversity. |
| 3 | **LLM server load asymmetry** | LOW | Treatment D runs process 40 mutations/epoch (vs 8 for control D), generating 5x more LLM calls. This could cause proxy congestion affecting G's mutation quality. Mitigation: all 12 runs share the same LiteLLM proxy with 6 mutation backend servers. At 12 concurrent runs with staggered epochs, the proxy should handle the load. Monitor: per-run LLM latency from logs. |
| 4 | **Wall-clock time asymmetry** | LOW | Treatment pairs will take longer per epoch (D processes 40 programs vs 8). At gen 50, treatment D may have processed ~2000 programs vs ~400 for control D. This is the intended mechanism, not a confound. The comparison uses gen 50 as the x-axis (identical outer generations), not wall time or total programs processed. G processes identical total programs in both arms (50 x 8 = 400); the blocking fraction difference (~50% control vs ~80% treatment) affects only wall-clock pacing, not per-program mutation quality. |
| 5 | **Config decoupling regression** | LOW | The sync_min_delta decoupling is new code. If the decoupling fails silently (sync_min_delta still reads max_mutations_per_generation), treatment D gets min_delta=40 (very tight coupling, opposite of intent). Mitigation: verify resolved config with `--cfg job` pre-launch; verify D log shows `min_delta=1` post-launch. |
| 6 | **Control arm may not reproduce v2** | LOW | The control arm uses the same config as v2 but runs on potentially different infrastructure state. If control mean deviates from v2's 0.03458 by more than 0.002, flag as confound. |
| 7 | **Stale workers from prior experiments** | LOW | Redis DBs 1-12 may contain data from prior runs. Mitigation: flush all DBs before launch using `gigaevo flush --db N --confirm` for N=1..12. |

---

## 10. Stop Criteria

**Hard stop**: `stopper=max_generations` with `max_generations=50`.

**Futility at gen 25**: If all 3 treatment pairs have max(G,D) < 0.030 at gen 25, stop the treatment arm early. Rationale: 0.030 is well below baseline (0.03449) and below the worst-performing pair in any prior experiment. If 3/3 treatment pairs are below this threshold at the halfway point, the treatment is likely harmful.

**Minimum completion**: >= 2/3 pairs per arm must reach gen 40 for the arm to be analyzable. If fewer than 2 pairs of an arm reach gen 40, report that arm as UNDERPOWERED (not INVALID -- partial data is still informative).

**Run invalidation criteria** (any one triggers exclusion from analysis):
- Invalidity rate > 90% for 10+ consecutive generations
- PID death before gen 10 with no automatic restart
- G/D generation gap > 15 (for treatment pairs, where some gap is expected due to asymmetric epochs)
- G/D generation gap > 5 (for control pairs, where tight coupling should maintain parity)
- Redis corruption or key collision between runs
- D log shows `min_delta=8` instead of `min_delta=1` (treatment D) -- config verification failure
- D log shows `min_delta=40` instead of `min_delta=1` (treatment D) -- sync_min_delta coupling regression

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| Wall time | ~48h (treatment pairs slower per epoch but D processes more programs per wall-clock hour; control pairs similar to v2) |
| LLM calls (total) | ~10,800 (3 treatment pairs: G 50x8=400, D 50x40=2000 each = 3x2400 = 7200; 3 control pairs: G 50x8=400, D 50x8=400 each = 3x800 = 2400; total = 9600 mutations + ~1200 evals) |
| Redis DBs | 12 (DBs 1-12) |
| Concurrent runs | 12 (6 pairs, 2 runs per pair) |

**Note on LLM load**: Treatment D runs generate 5x more mutation calls than control D runs. The 6-node mutation server cluster behind the LiteLLM proxy should handle 12 concurrent runs (2 runs per mutation server on average). If proxy latency exceeds 3000s per mutation call, consider staggering treatment pair launches by 30 minutes.

---

## 12. Open Questions / Risks

1. **Is K=5 too much?** WGAN-GP's n_critic=5 was tuned for continuous Wasserstein distance estimation. MAP-Elites archive dynamics are discrete. K=5 may be too aggressive (D overfits to current G) or too conservative (MAP-Elites needs K=10+ to escape local optima). If the result is POSITIVE but weak, a dose-response (K=3, K=5, K=10) follow-up is warranted. If NULL or NEGATIVE, K>5 is unlikely to help and the search-space hypothesis (structured Improver operators) becomes primary.

2. **Interaction between epoch size and sync granularity**: With treatment D at 40 mutations/epoch and sync_min_delta=1, D processes its entire 40-program epoch before checking sync. G, at 8 programs/epoch with min_delta=8, blocks until D processes 8 programs (trivially satisfied since D processes 40). The net effect is that D runs nearly free while G blocks most of the time. This is the intended dynamics, but the GAN analogy (D updates 5x per G update with interleaved checking) is imperfect -- here D runs entire 40-program epochs autonomously.

3. **Control arm purpose**: The control arm replicates v2's config. If the control arm outperforms v2's historical results, the treatment-control difference shrinks and the v1-style peaks may be attributable to the control condition's loose coupling rather than the treatment's K=5 budget. However, control D runs have `sync_min_delta=8` (tight coupling), matching v2. Any deviation from v2's performance would indicate temporal confounds.

4. **After this experiment**: If POSITIVE -- the compute budget hypothesis is confirmed, and the roadmap is: ablation (loose coupling alone vs K=5 alone), dose-response (K=3/5/10), then structured Improver operators. **A POSITIVE result cannot distinguish whether the effect is driven by K=5, loose coupling, or their interaction. The follow-up ablation is essential for mechanism attribution.** If NULL -- both information and compute interventions have failed, making the stagnation a search-space problem. The next direction becomes structured move operators that constrain D's mutation space to geometrically meaningful perturbations.

---

## 13. Treatment Verification

Treatment verification must confirm that each arm's mechanism is active and correctly configured. The following evidence is required before the experiment is considered validly launched.

### Pre-launch config verification (`--cfg job`)

| Run type | Key fields to verify | Expected value |
|----------|---------------------|----------------|
| Treatment D runs | `engine_config.max_mutations_per_generation` | 40 |
| Treatment D runs | `pre_step_hook.min_delta` | 1 |
| Control D runs | `engine_config.max_mutations_per_generation` | 8 |
| Control D runs | `pre_step_hook.min_delta` | 8 |
| All G runs | `engine_config.max_mutations_per_generation` | 8 |
| All G runs | `pre_step_hook.min_delta` | 8 |
| All runs | `pipeline` | adversarial_asymmetric |
| All runs | `evolution` | steady_state |
| All runs | `feedback_mode` | composition |
| All D runs | `d_sees_g_source` | true |
| All D runs | `d_archive_persistent` | true |
| All runs | `archive_reeval` | false |
| All runs | `max_elites_per_generation` | 8 (platform default is 5; must be overridden in config.extra) |

### Post-launch log verification (within first 3 generations)

| Check | Observable evidence | Expected for Treatment D | Expected for Control D |
|-------|---------------------|-------------------------|----------------------|
| Sync hook init | `[ProgressBasedSyncHook] Init \| ... min_delta=X` | min_delta=1 | min_delta=8 |
| Epoch size | Programs processed per epoch (first 3 epochs) | ~40 per epoch | ~8 per epoch |
| D/G program ratio | `engine:programs_processed` D / G after gen 5 | ~5:1 | ~1:1 |
| Engine type | Log shows `SteadyStateEvolutionEngine` | Yes | Yes |
| Composition injection | G log: `[CompositionInjection]` after gen 2 | Yes | Yes |

### D/G program ratio verification (treatment verification metric)

At gen 10, verify from Redis:
- Treatment pairs: D `engine:programs_processed` / G `engine:programs_processed` in range [4.5, 6.0]. If outside this range, the budget asymmetry is not working as designed.
- Control pairs: ratio in range [0.8, 1.2]. If outside, the control is not symmetric.

### Failure modes from codebase_map.md

| ID | Risk | Detection | Impact if missed |
|----|------|-----------|-----------------|
| KF-01 | Missing `evolution=steady_state` | Deadlock at gen 0 | Fatal -- all runs stuck |
| KF-02 | Shell expansion of `\${composition_injection_hook}` | Empty `post_step_hook` in launch.sh | G receives no composition injection; feedback channel broken |
| KF-05 | sync_min_delta not overridden on treatment D | D log shows `min_delta=8` not `min_delta=1` | Treatment identical to control; experiment has no IV |
| -- | model_name config drift | `--cfg job` shows wrong model | Wrong LLM for mutations |
| -- | sync_min_delta still coupled to max_mutations_per_generation | Treatment D shows `min_delta=40` | D waits for G to process 40 programs (impossible since G epoch=8); deadlock or severe blocking |

---

## 14. Monitoring

```yaml
watchdog:
  plugin: adversarial
  sentinel_value: -1.0
  plot_metrics: [actual_fitness]
  poll_interval_s: 3600
  alert_thresholds:
    invalidity_rate: 0.75
    stagnation_window: 10
    generation_gap_threshold: 5
  plot_commands:
    - command: arms-race
      args:
        metric: actual_fitness
        smoothing: ema
        window: 10
        bands: true
        show-max: true
        annotate-frontier: true
        max-annotations: 3
      output_name: arms_race.png
      caption: "Arms-race dynamics (G vs D per pair, max(G,D) overlay)"
    - command: comparison
      args:
        metric: actual_fitness
        smoothing: ema
        window: 10
        annotate-frontier: true
        max-annotations: 3
      output_name: evolution_runs_comparison.png
      caption: "All 12 runs vs SOTA baseline (treatment vs control)"
```

Additional monitoring:
- **D/G program ratio plot**: At each checkpoint, compute and report D/G programs_processed ratio for each pair. Treatment pairs should show ~5:1; control should show ~1:1.
- **Improver acceptance rate**: Track per-D-run acceptance rate in rolling 10-gen windows. Compare treatment vs control D acceptance rates.
- **LLM latency**: Monitor mean/p95 LLM call duration per run. Flag if any run's p95 exceeds 2x the median across all runs (proxy congestion).

---

*Ready for Reviewer-2's scrutiny.*
