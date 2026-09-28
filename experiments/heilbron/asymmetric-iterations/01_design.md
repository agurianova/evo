# Experimental Design: Structured Improver-Constructor Information Flow with K=5 Inner Iterations

**Date**: 2026-04-12
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Draft -- awaiting Reviewer-2
**Supersedes**: Pre-registered WGAN-GP iteration ratio design (commit 8ce7ab3f). This is a fundamentally different mechanism, not an amendment.

---

## 1. Research Question

Does structured Improver-Constructor information flow -- where the Improver (D) sees Constructor (G) source code as a dynamic task description and runs K=5 inner MAP-Elites iterations per outer generation -- break Improver stagnation and improve Constructor actual_fitness on the Heilbronn N=11 triangle problem, and does the feedback mode (Composition vs Gradient-in-prompt) affect the outcome?

**Context**: Six adversarial experiments (32+ runs) have established that Improver stagnation is structural, not feedback-dependent: every prior intervention changed the *information* flowing to the Improver but never the *compute budget* or *information architecture*. The current design changes both simultaneously. The Improver receives G's source code (not just output arrays) as its dynamic task description, giving it white-box access to the Constructor's strategy. It then runs K=5 inner MAP-Elites iterations against this richer representation, producing a persistent archive of improvement strategies that carries forward across outer generations. The two arms test how D's discoveries flow back to G: direct code injection (Composition, Arm A) vs textual signal in G's mutation prompt (Gradient-in-prompt, Arm C).

**Key departure from prior design**: The original pre-registration (commit 8ce7ab3f) tested a simple WGAN-GP K:1 ratio by setting Improver `max_mutations_per_generation=40` while keeping everything else identical. That design changed only the Improver's compute budget. This redesign changes the Improver's *information architecture* (white-box access to G source code), *evaluation protocol* (collective evaluation against N_opp=5 opponents), *archive semantics* (persistent across outer generations), and *feedback channel to G* (Composition vs Gradient-in-prompt). It is a fundamentally different experiment that reuses the same branch name for logistical convenience.

No pure within-experiment control arm is included. The historical baseline from heilbron/baseline-repro (mean best-overall actual_fitness = 0.03449, N=4, SD=0.00212) serves as the reference point.

---

## 1a. Implementation Scope

This design requires new pipeline code, not just Hydra config overrides. The existing `adversarial_coevo` pipeline does not support inner iterations, source code injection, composition injection, or gradient-in-prompt feedback. A new pipeline config (`adversarial_asymmetric`) and supporting stage implementations must be built before launch.

**New components required:**

1. **Inner iteration loop within D's evaluation** -- D runs K=5 inner MAP-Elites iterations per outer generation. This requires a loop controller that invokes the mutation-evaluation cycle K times before signaling outer generation completion. No existing code produces the `[InnerIteration]` log lines referenced in Section 13.
2. **Source code injection stage (G to D)** -- A stage that reads G's current best `solve()` source code from G's Redis archive and injects it into D's mutation prompt as a dynamic task description. This replaces D's current information channel (output arrays only) with white-box access to G's strategy.
3. **Composition injection stage (D to G, Arm A)** -- A stage that takes D's best improvement program and submits it as a tagged mutation candidate (`mutation_type="d_improvement"`) into G's next generation, going through G's full DAG pipeline (validation, fitness eval). No existing code produces the `[CompositionInjection]` log lines referenced in Section 13.
4. **Gradient-in-prompt mutation prompt modification (Arm C)** -- A mutation prompt extension that embeds D's best improvement source code verbatim into G's mutation LLM prompt as a structured "Improvement Strategy from Opponent" section. This extends the existing `OpponentFeedbackStage` pattern but with a different injection point (mutation prompt vs formatted context).
5. **Persistent archive semantics for D** -- D's MAP-Elites archive must carry forward across outer generations without reset. The standard archive persists in Redis by default, but the inner iteration loop must avoid clearing or resetting it between inner iterations or between outer generations.

**Verification table references**: The log line patterns in Section 13 (`[InnerIteration]`, `[CollectiveEval]`, `[CompositionInjection]`) must be implemented in the new pipeline code. They are specifications for what the implementation must produce, not references to existing code.

---

## 2. Hypotheses

**H0**: Neither feedback mode (Composition nor Gradient-in-prompt) with K=5 inner iterations changes Constructor actual_fitness relative to the historical baseline (0.03449).

**H1**: At least one feedback mode produces Constructor actual_fitness meaningfully different from the historical baseline.

### Effect-size thresholds (raw actual_fitness, no normalization)

| Constructor actual_fitness (mean over replicates) | Interpretation |
|---|---|
| >= 0.03649 (baseline + 0.002) | **STRONG POSITIVE** -- structured information flow improves beyond baseline noise |
| >= 0.03449 and < 0.03649 | **POSITIVE** -- at least matches baseline, warrants investigation of dose-response |
| within 0.001 of baseline (0.03349 to 0.03549) | **NULL** -- no meaningful effect detected at this sample size |
| < 0.03249 (baseline - 0.002) | **NEGATIVE** -- structured information flow actively hurts |

| Improver acceptance rate (rolling 10-gen window, after gen 20) | Interpretation |
|---|---|
| > 5% in >= 2/2 replicates of either arm | **STAGNATION BROKEN** -- first intervention to achieve this |
| > 5% in 1/2 replicates | **SUGGESTIVE** -- partial evidence, warrants replication |
| <= 5% in all replicates | **STAGNATION PERSISTS** -- information architecture + budget insufficient |

### Cross-arm comparison

| Arm A vs Arm C (Constructor actual_fitness) | Interpretation |
|---|---|
| Difference >= 0.002 favoring either arm | **FEEDBACK MODE MATTERS** -- Lamarckian transfer (Arm A) differs from textual gradient (Arm C). **Caveat**: Arm A's injected candidates are pre-vetted through D's evaluation pipeline and represent additional candidate volume; this comparison cannot isolate the injection mechanism from the combined quantity + quality advantage (see Section 9 Confound #3). |
| Difference < 0.002 | **FEEDBACK MODE NEUTRAL** -- both channels equivalent at this effect size |

---

## 3. Independent Variable(s)

| Variable | Arm A (Composition) | Arm C (Gradient-in-prompt) |
|----------|---|---|
| **Feedback mode** (primary IV) | D's best improvement of each G program is submitted as a mutation candidate in G's next generation, going through G's normal DAG pipeline (validation, fitness eval). Tagged with `mutation_type="d_improvement"` for lineage tracking. Lamarckian evolution: acquired improvements enter G's gene pool directly. | D's best improvement source code is shown verbatim in G's mutation LLM prompt for the next generation. G's LLM sees "here is an improvement strategy that worked" as textual gradient signal (TextGrad analogy). No direct code injection. |

Both arms share:
- **D sees G source code**: D receives G's source code as a dynamic task description (white-box access)
- **K=5 inner iterations**: Per outer generation, D runs K=5 inner MAP-Elites iterations against its opponents
- **Collective evaluation**: D evaluates against all N_opp=5 opponents simultaneously (fitness = mean improvement)
- **Persistent D archive**: D's archive carries improvement strategies across outer generations

**Single IV**: Feedback mode. Everything else is controlled.

### Baseline information access (adversarial_coevo, as used in baseline-repro)

In the baseline adversarial pipeline (`adversarial_coevo`), D receives opponent information exclusively via `FetchOpponentResultsStage`. This stage executes each opponent G program's `entrypoint()` function in a subprocess and returns the **output arrays** (11x2 point configurations). D's `evaluate.py` receives these output arrays as `opponent_results` and computes fitness as mean improvement across opponent configurations. D never sees G's source code -- it sees only G's output (point placements). There is no `OpponentFeedbackStage` in the baseline heilbron pipeline; the feedback stage exists only in the `hover_feedback` pipeline variant.

When opponent feedback is enabled (K>0, as in some HoVer experiments), the `OpponentFeedbackStage` shows opponent **source code** in the mutation prompt. But baseline-repro does not use this stage. D's mutation LLM receives no information about G's strategy -- only the fitness signal from evaluating D's own `improve()` function against G's output arrays.

**In this design**: D receives G's full `solve()` source code as a dynamic task description, giving white-box access to G's strategy. This is a qualitative change in information architecture: D can now reason about *how* G places points (algorithmic strategy), not just *where* G places them (output arrays). This is the core mechanism hypothesized to break Improver stagnation.

---

## 4. Dependent Variable(s)

| Metric | How measured | Primary? |
|--------|-------------|----------|
| Constructor actual_fitness | Best raw min_area from Constructor (Pop A) at gen 50 | **Yes** |
| Improver acceptance rate | Rolling 10-gen window: fraction of D's mutation attempts that produce an accepted elite, after gen 20 | Secondary (stagnation diagnostic) |
| Best-overall actual_fitness | max(Constructor, Improver best-over-all-gens) per pair at gen 50 | Secondary (continuity with baseline-repro) |
| D inner iteration acceptance rate | Per-gen: accepted / total across K=5 inner iterations | Secondary (D search efficiency) |
| Composition acceptance rate (Arm A only) | Fraction of D-injected mutation candidates that survive G's DAG validation + enter G's archive | Exploratory (Lamarckian transfer efficiency) |
| Wall-clock time per outer generation | Log timestamps | Exploratory (compute cost) |

**Primary metric**: Constructor actual_fitness at gen 50, averaged across 2 replicates per arm.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| `max_generations` (outer) | 50 | Match baseline-repro and heilbron-prover |
| K (inner iterations per outer gen) | 5 | Fixed across both arms; isolates feedback mode |
| N_opp (opponents per D evaluation) | 5 | Match adversarial_coevo default |
| D `max_mutations_per_generation` (per inner iteration) | 8 | Standard budget per inner iteration |
| G `max_mutations_per_generation` | 8 | Match baseline-repro |
| `max_elites_per_generation` | 8 | Match baseline-repro (both populations) |
| D archive persistence | TRUE | Carries forward across outer generations in both arms |
| `mutation_mode` | rewrite | Match baseline-repro |
| `model_name` | Qwen3-235B-A22B-Thinking-2507 | Same mutation LLM across all runs |
| `llm_base_url` | http://10.232.30.185:4000/v1 | LiteLLM proxy |
| `temperature` | 0.6 | Match baseline-repro |
| `max_tokens` | 81920 | Match baseline-repro |
| `island_max_size` | 75 | Match baseline-repro |
| `primary_resolution` | 150 | Match baseline-repro |
| `num_parents` | 1 | Match baseline-repro (independent mutation, no crossover) |
| `stage_timeout` | 3000 | Match baseline-repro |
| `dag_timeout` | 7200 | Match baseline-repro |
| Initial seed | `grid.py` (Constructor), `seed.py` (Improver) | Identical across arms |
| Engine type | Generational (`EvolutionEngine`) | Confirmed: generational > steady-state for adversarial |
| `archive_reeval` | false | Archive re-evaluation confirmed NEGATIVE in adversarial-dynamic-updates |
| `pipeline` | New pipeline config (see Section 13) | Same pipeline for both arms, parameterized by feedback_mode |
| D evaluates G source code | TRUE | Both arms; D sees G's `solve()` function, not just output arrays |

### Inner iteration / generation counter / sync hook interaction

The K=5 inner iteration mechanism introduces a loop within D's outer generation that must interact correctly with the engine's generation counter and the `MainRunSyncHook`. The following invariants are specified:

1. **D's inner iterations do NOT increment `engine:total_generations`**. The K=5 inner MAP-Elites iterations within a single outer generation are internal to D's evaluation loop. They produce mutations, evaluate them, and update D's archive, but they do not advance D's outer generation counter.

2. **Only D's outer generation completion increments the generation counter**. After all K=5 inner iterations complete for one outer generation, D's engine advances `engine:total_generations` by 1 (as in the standard generational engine).

3. **The `MainRunSyncHook` fires on outer generation boundaries only**. G's `pre_step_hook` polls D's `engine:total_generations` via Redis. Since D's inner iterations do not increment this counter, G blocks during D's entire inner loop (all K=5 iterations) and resumes only when D completes its outer generation and increments the counter.

4. **G blocks during D's inner loop and resumes when D's outer generation counter advances**. This means each outer generation takes approximately 5x longer than a baseline generation for the pair (D runs 5 inner iterations while G waits). This is the intended compute asymmetry.

5. **Verification**: G and D `engine:total_generations` must remain within 1 of each other at all times. During the 3-gen smoke test (Section 13), verify at gen 5 that both G and D show the same outer generation count (within 1). If D's inner iterations leak into the generation counter, G will desynchronize rapidly (advancing 5x faster or 5x slower than intended).

---

## 6. Run Design Table

### Arm A: Composition (D_best injected as G mutation candidate) -- 2 pairs

| Run | Label | `redis.db` | Role | `feedback_mode` | Notes |
|-----|-------|------------|------|-----------------|-------|
| 1 | A1_G | 1 | Constructor (G) | composition | Receives D_best(G_i) as tagged mutation candidate |
| 2 | A1_D | 2 | Improver (D) | composition | K=5 inner iterations; sees G source code |
| 3 | A2_G | 3 | Constructor (G) | composition | Replicate |
| 4 | A2_D | 4 | Improver (D) | composition | Replicate |

### Arm C: Gradient-in-prompt (D_best code shown in G's mutation prompt) -- 2 pairs

| Run | Label | `redis.db` | Role | `feedback_mode` | Notes |
|-----|-------|------------|------|-----------------|-------|
| 5 | C1_G | 5 | Constructor (G) | gradient_in_prompt | G's mutation LLM sees D's best improvement code |
| 6 | C1_D | 6 | Improver (D) | gradient_in_prompt | K=5 inner iterations; sees G source code |
| 7 | C2_G | 7 | Constructor (G) | gradient_in_prompt | Replicate |
| 8 | C2_D | 8 | Improver (D) | gradient_in_prompt | Replicate |

**Total**: 8 runs (4 Constructors + 4 Improvers). 8 Redis DBs (1-8).

### Shared overrides (all runs)

```
problem.name=heilbron_adversarial/pop_a  (G) or heilbron_adversarial/pop_b  (D)
pipeline=adversarial_asymmetric          (new pipeline config)
inner_iterations=5
n_opponents=5
d_sees_g_source=true
d_archive_persistent=true
archive_reeval=false
```

### Per-arm overrides

| Override | Arm A | Arm C |
|----------|-------|-------|
| `feedback_mode` | composition | gradient_in_prompt |

### Per-pair overrides (opponent wiring)

Each pair wires G<->D via `opponent_redis_db` and `opponent_redis_prefix`, identical to prior adversarial experiments.

---

## 7. Sample Size Justification

N=2 pairs per arm (4 pairs total, 8 runs). From baseline-repro (N=4): SD(best-overall actual_fitness) = 0.00212. With N=2 per arm, a Welch's t-test at alpha=0.10 two-sided detects effects of d >= 0.00424 (2.0 sigma) with approximately 50% power. The minimum detectable effect at 80% power would require N >= 6 per arm, which exceeds available Redis DBs.

**With N=2 runs per condition, this experiment measures effect magnitude and consistency. Formal statistical testing would require N >= 6 runs per condition.** The design prioritizes observing whether the mechanism works at all (effect direction and magnitude) over precise effect-size estimation. If both replicates of an arm show consistent improvement over baseline, that is informative regardless of p-values; if they disagree, we learn about mechanism reliability.

The absence of a within-experiment control arm is deliberate: 4 pairs allocated to 2 treatment arms maximizes information about the feedback mode comparison. The historical baseline (N=4) provides the reference.

---

## 8. Statistical Test

**Primary comparison**: Each arm's mean Constructor actual_fitness at gen 50 vs historical baseline (0.03449).

**Cross-arm comparison**: Welch's two-sample t-test (alpha=0.10, two-sided) comparing Arm A vs Arm C on Constructor actual_fitness. Report Cohen's d, 90% CI, and p-value. With N=2/arm, acknowledge that this test is severely underpowered and the result is descriptive.

**Stagnation assessment**: Descriptive. D breaks stagnation if rolling 10-gen Improver acceptance rate > 5% after gen 20 in >= 2/2 replicates of at least one arm. Report actual acceptance rate trajectories for all D runs.

**Effect magnitude**: Report per-run values, arm means, grand mean, and range. The primary inferential method is observing effect direction consistency across replicates, not p-values.

---

## 9. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| **No within-experiment control** | HIGH | Historical baseline (0.03449, N=4, SD=0.00212) from baseline-repro on same infrastructure, same model, same hyperparameters. Any improvement beyond baseline+2*SD (0.03873) would be compelling regardless. |
| **Compound treatment** (multiple simultaneous changes from baseline) | HIGH | Both arms share the same compound treatment (source code access + K=5 + collective eval + persistent archive). The IV is feedback_mode only. The compound treatment vs baseline comparison is descriptive, not causal for any single component. |
| **Composition arm gets extra mutations of systematically higher quality** (D_best injected into G) | MEDIUM | This IS the treatment difference. Arm A's G population receives strictly more mutation candidates than Arm C's G. Moreover, Arm A's injected candidates have been pre-selected through D's evaluation pipeline: they are D's *best* improvements, already validated against D's archive and shown to improve upon G's current programs. Arm C's Constructor receives the same 8 standard mutations as always, plus a textual hint. Arm A receives extra candidates that are pre-vetted for both validity and quality. The Arm A vs Arm C comparison can therefore determine whether "Lamarckian transfer (quantity + quality confounded) differs from textual gradient" -- but cannot isolate the injection mechanism per se from the extra pre-vetted candidate volume. If Arm A wins, a follow-up experiment controlling for volume (e.g., injecting random D programs rather than D's best) would be needed to isolate the quality selection effect. |
| **Gradient-in-prompt contamination** (D's code may mislead G's LLM) | MEDIUM | Monitor: if Arm C shows Constructor regression (below 0.034), the textual gradient may be adversarial noise. Compare G invalidity rates between arms. |
| **K=5 compute asymmetry** (D does 5x work per outer gen) | LOW | This is the designed mechanism. Wall-clock time per gen is an exploratory DV. Constructor evolves at same rate in both arms. |
| **LLM server load** (8 concurrent runs on shared proxy) | MEDIUM | Same proxy, same model. Stagger launches by 2 minutes per pair. Monitor latency via LiteLLM dashboard. |
| **Historical baseline drift** (infrastructure changes since baseline-repro) | LOW | Same LiteLLM proxy, same model weights, same hardware. No known changes. |
| **D archive persistence may cause overfitting** | LOW | D archive carries strategies across outer gens -- it may accumulate stale strategies optimized for earlier G versions. Monitor D archive diversity and staleness. |
| **Generation semantics** (D's effective total mutations = 50 gens x 5 inner x 8 mut = 2000 vs G's 50 x 8 = 400) | LOW | D's compute asymmetry is the point. Analysis uses outer generation as x-axis. |

---

## 10. Stop Criteria

**Hard stop**: `max_generations=50` (outer).

**Futility at gen 25**: If both replicates of an arm have Constructor actual_fitness < 0.03000 (significantly below any prior result), stop that arm early.

**Minimum completion**: >= 1/2 pairs per arm must reach gen 40 for the arm to be analyzable. If both pairs of an arm fail before gen 40, report as INVALID for that arm.

**Run invalidation criteria** (any one triggers exclusion):
- Invalidity rate > 90% for 10+ consecutive outer generations
- PID death before gen 10 with no restart
- Outer generation gap > 10 between paired G and D runs (sync hook failure)
- Redis corruption or key collision between runs

---

## 11. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| GPU hours (LLM inference) | ~200h (each pair: G does 50x8=400 mutations, D does 50x5x8=2000 mutations, plus evaluations. 4 pairs total.) |
| Wall time | ~96h (D's K=5 inner iterations serialize; G blocks on sync hook during D's inner loop) |
| Redis DBs used | 8 (DBs 1-8) |
| LLM calls (total) | ~14,400 (4 pairs x (400 G mutations + 2000 D mutations + evaluations + feedback generation)) |

**Note**: Wall time is substantially longer than baseline-repro (~48h for 4 pairs) because D runs 5 inner iterations per outer generation. The sync hook means G is idle during D's inner loop, so total LLM load is sequential within each pair, not parallel.

---

## 12. Open Questions / Risks

1. **Compound treatment vs single mechanism**: This experiment changes four things relative to baseline (source code access, K=5, collective eval, persistent archive) plus adds a feedback channel (Composition or Gradient-in-prompt). If the result is POSITIVE, we cannot attribute the effect to any single component. This is an intentional tradeoff: we first check whether the full stack works before ablating components.

2. **Composition may create runaway feedback loops**: If D_best(G_i) is injected and immediately becomes G's new best, D then sees this improved G and may produce an even better improvement, creating a Lamarckian cascade. This could be beneficial (rapid adaptation) or harmful (mode collapse to a narrow strategy). Monitor Constructor archive diversity.

3. **Gradient-in-prompt may be noise**: If D's improvement code is too complex or too specific to a particular G program, G's mutation LLM may ignore or misinterpret it. The textual gradient signal has no formal guarantees. Monitor whether G's mutation outputs show evidence of incorporating D's strategies (qualitative analysis of mutation prompts/outputs).

4. **K=5 may be wrong for MAP-Elites**: The WGAN-GP K=5 ratio was tuned for continuous optimization with Wasserstein distance. MAP-Elites archive dynamics are discrete and may need a different ratio. If the result is POSITIVE but weak, a follow-up dose-response (K=3, K=5, K=10) is warranted.

5. **D archive persistence is untested**: Prior adversarial experiments reset D's context each generation. Persistent archives may accumulate stale strategies. If D's inner acceptance rate degrades over time (monotonic decrease), persistence is harmful.

6. **Collective evaluation semantics**: D evaluates against all N_opp=5 opponents simultaneously (fitness = mean improvement). This is analogous to a GAN mini-batch. If one outlier G program dominates the mean, D may over-specialize. Monitor per-opponent improvement distribution.

---

## 13. Treatment Verification

Treatment verification must confirm that each arm's mechanism is active and correctly configured. The following evidence is required before the experiment is considered validly launched.

### Shared verification (all 8 runs)

| Check | Observable evidence | Tool |
|-------|-------------------|------|
| D sees G source code | D's mutation prompt contains G's `solve()` function text (not just output arrays) | Inspect mutation prompt in D's log at gen >= 2 |
| K=5 inner iterations | D log shows 5 inner iteration cycles per outer generation (log line: `[InnerIteration] k=1/5`, ..., `k=5/5`) | `grep "InnerIteration" run_*_D.log | head -20` |
| Persistent D archive | D's archive size is non-decreasing across outer generations; no `[ArchiveReset]` log lines | `gigaevo -r ... trajectory` shows cumulative valid count |
| Collective evaluation | D evaluates each mutation against N_opp=5 opponents (log line: `[CollectiveEval] n_opponents=5`) | `grep "CollectiveEval" run_*_D.log | head -5` |
| Outer generation sync | G and D generation counts remain within 1 of each other throughout the run | `gigaevo -e heilbron/asymmetric-iterations status` |
| archive_reeval=false | `--cfg job` shows `archive_reeval: false` | Pre-launch config check |
| archive_reeval resolved in pipeline_builder | `--cfg job` shows `pipeline_builder.archive_reeval: false` in the resolved config (not just a top-level override that may not be wired through) | Pre-launch config check |
| No archive re-evaluation at runtime | No `[ArchiveReeval]` log lines appear during the 3-gen smoke test | `grep "ArchiveReeval" run_*.log` |

### Arm A (Composition) verification

| Check | Observable evidence | Tool |
|-------|-------------------|------|
| D_best injection | G's log shows `[CompositionInjection] mutation_type=d_improvement` at least once per gen (after gen 2) | `grep "CompositionInjection" run_*_G.log | head -10` |
| Tagged lineage | G's Redis archive contains programs with `mutation_type: d_improvement` in metadata | `gigaevo -r ... top -n 5 --code` (inspect metadata) |
| Injection goes through full DAG | Injected programs are validated (some may fail validation and be discarded) | Compare injection count vs accepted count in G's log |

### Arm C (Gradient-in-prompt) verification

| Check | Observable evidence | Tool |
|-------|-------------------|------|
| D_best code in G's prompt | G's mutation prompt contains a section like `## Improvement Strategy from Opponent` with D's code | Inspect G's mutation prompt in log at gen >= 3 |
| No direct code injection | G's Redis archive does NOT contain programs with `mutation_type: d_improvement` | `grep "d_improvement" run_*_G.log` should return empty |
| G's LLM output references D's strategy | Qualitative: G's mutation output at gen >= 5 shows evidence of incorporating D's signal | Manual inspection of 3-5 mutation outputs |

### Hydra override verification (pre-launch, `--cfg job`)

| Run type | Key config fields to verify |
|----------|---------------------------|
| All G runs | `problem.name: heilbron_adversarial/pop_a`, `pipeline: adversarial_asymmetric`, `max_mutations_per_generation: 8`, `archive_reeval: false` |
| All D runs | `problem.name: heilbron_adversarial/pop_b`, `pipeline: adversarial_asymmetric`, `inner_iterations: 5`, `n_opponents: 5`, `d_sees_g_source: true`, `d_archive_persistent: true` |
| Arm A G runs | `feedback_mode: composition` |
| Arm A D runs | `feedback_mode: composition` |
| Arm C G runs | `feedback_mode: gradient_in_prompt` |
| Arm C D runs | `feedback_mode: gradient_in_prompt` |

### Smoke test protocol (3-gen, mandatory before full launch)

Because this experiment requires substantial new pipeline code (Section 1a), a 3-gen smoke test must verify each novel mechanism before committing to the full 8-run launch. The smoke test runs one pair from each arm (A1_G + A1_D, C1_G + C1_D) for 3 outer generations on dedicated Redis DBs (not the production DBs 1-8).

**Pass criteria** (all must hold for each pair):

| Mechanism | Pass criterion |
|-----------|---------------|
| D inner iterations | D log shows `[InnerIteration] k=1/5` through `k=5/5` for each of the 3 outer generations |
| D source code access | D's mutation prompt at gen >= 2 contains G's `solve()` function text (not output arrays) |
| Persistent D archive | D's archive size is non-decreasing across all 3 outer generations |
| Collective evaluation | D log shows `[CollectiveEval] n_opponents=5` |
| Generation sync | G and D `engine:total_generations` differ by at most 1 at gen 3 |
| No archive re-evaluation | No `[ArchiveReeval]` log lines in any run log |
| Composition injection (Arm A only) | G's log shows at least one `[CompositionInjection] mutation_type=d_improvement` by gen 3 |
| Gradient-in-prompt (Arm C only) | G's mutation prompt at gen >= 2 contains "Improvement Strategy from Opponent" section |
| No crashes | All 4 smoke-test processes alive at gen 3 |

If any mechanism fails the smoke test, diagnose and fix before launching. Do not proceed to the full 8-run launch with a known mechanism failure.

---

*Ready for Reviewer-2's scrutiny.*
