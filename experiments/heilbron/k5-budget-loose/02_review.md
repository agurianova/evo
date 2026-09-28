# Peer Review: K=5 Compute Budget Asymmetry with Loose G/D Coupling

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Date**: 2026-04-16
**Design**: `experiments/heilbron/k5-budget-loose/01_design.md`
**Round**: 1

---

## Overall Assessment

This is the most carefully prepared Heilbronn design I have reviewed. The research question is sharply stated. The compound treatment is honestly acknowledged and adequately justified by resource constraints. The within-experiment control is the correct design choice. The treatment verification section (Section 13) is exemplary -- it is the first design in this series that specifies pre-launch, post-launch, and runtime verification checks with concrete expected values and failure modes.

I have no critical or major concerns. Four minor concerns are noted below.

---

## 1. Confound Detection

### 1.1 Explicit IVs -- WELL HANDLED

The design lists exactly two parameter changes between arms (D's `max_mutations_per_generation`: 40 vs 8; D's `sync_min_delta`: 1 vs 8) and correctly identifies these as a deliberately bundled compound treatment. The G configuration is identical across all 12 runs. I verified this against the pipeline YAML: `adversarial_asymmetric.yaml` line 67 wires `min_delta: ${sync_min_delta}`, and both pipeline YAMLs read from the decoupled `sync_min_delta` constant. The decoupling test (`tests/test_config.py:220-276`) confirms independence. The config wiring is clean.

### 1.2 Hidden IV: `max_elites_per_generation` default mismatch

The design specifies `max_elites_per_generation=8` as a controlled variable (Section 5). However, `config/constants/evolution.yaml` sets the default to **5**, not 8. This means `max_elites_per_generation=8` must be explicitly set via `config.extra` or per-run overrides. The `codebase_map.md` section "Recommended Treatment Specification" correctly includes it in `config.extra`. This is not a confound because it will be uniform across all runs, but if the implementer misses this override, the experiment runs with `max_elites_per_generation=5` -- different from the stated design but still uniform across arms (a protocol deviation, not a confound). **Add `max_elites_per_generation=8` to the Section 13 pre-launch config verification table.**

**Severity**: Minor.

### 1.3 Hidden IV: G run `sync_min_delta` inheritance -- NO ISSUE

The design states that G runs use `sync_min_delta=8 (default, not overridden)`. I verified this is correct: G runs inherit from `config/constants/evolution.yaml:7` where `sync_min_delta: 8`. Since only treatment D runs override `sync_min_delta=1`, G runs in both arms get `min_delta=8`. The asymmetry in G's blocking fraction (~0% treatment vs ~50% control) is an intended consequence, not a hidden IV. Well analyzed.

### 1.4 No `include_in_prompts` concern

Both arms use identical problem names (`heilbron_adversarial/pop_a` and `pop_b`), so metrics.yaml and prompt content are identical. No hidden IV from prompt parity.

### 1.5 Server/Redis assignment -- NO ISSUE

All 12 runs use the same LiteLLM proxy, same Redis host, DBs 1-12 with no sharing. No server-condition correlation.

---

## 2. Treatment Integrity

### 2.1 Can the treatment silently fail? -- WELL ADDRESSED

Section 13 specifies three layers of verification: (a) pre-launch `--cfg job` check for resolved config values, (b) post-launch log verification for `[ProgressBasedSyncHook] Init | ... min_delta=1`, and (c) runtime D/G program ratio verification at gen 10. This is the strongest treatment verification protocol in the Heilbronn series.

The design identifies the two most dangerous failure modes: (1) `sync_min_delta` not overridden on treatment D (treatment collapses to control), and (2) `sync_min_delta` still coupled to `max_mutations_per_generation` (treatment D gets `min_delta=40`, causing severe blocking). Both are detectable from logs and the `--cfg job` dump.

### 2.2 Run invalidation criteria gap for `min_delta=40` failure

Section 10 includes "D log shows `min_delta=8` instead of `min_delta=1` (treatment D)" as a run invalidation criterion. The converse failure mode -- `min_delta=40` from a coupling regression -- is listed in Section 13's failure mode table but is NOT in Section 10's run invalidation criteria. **Add "D log shows `min_delta=40` instead of `min_delta=1` (treatment D) -- config coupling regression" to Section 10.**

**Severity**: Minor.

---

## 3. Design Quality

### 3.1 Within-experiment control -- EXCELLENT

The decision to include a concurrent control (replicating v2's config) rather than relying solely on the historical baseline (0.03449) is the correct choice. The new `sync_min_delta` decoupling code introduces a config infrastructure change; the concurrent control validates that this change does not regress v2 behavior. This also eliminates temporal confounds.

### 3.2 Compound treatment justification -- ADEQUATE

The compound treatment (K=5 budget + loose coupling) is honestly acknowledged in Section 3 and justified on three grounds: (1) v1/v2 evidence that loose coupling is necessary, (2) a 2x2 factorial would require 24 runs, and (3) a follow-up ablation is planned if POSITIVE. I accept this justification.

However, the design should be more explicit about what a POSITIVE result would and would not tell us. **Add a sentence to Section 12 (Open Questions) explicitly stating: "A POSITIVE result cannot distinguish whether the effect is driven by K=5, loose coupling, or their interaction. The follow-up ablation is essential for mechanism attribution."**

**Severity**: Minor.

### 3.3 G blocking fraction asymmetry

The design notes in Section 3 that G's blocking fraction is ~50% in control vs ~80% in treatment. Section 9 (Confound 4, wall-clock time) dismisses this because "the comparison uses gen 50 as the x-axis." I considered whether this constitutes a confound -- specifically, whether G's idle time between epochs could affect mutation quality through temporal factors (e.g., KV cache state, opponent information recency).

After analysis, I am satisfied this is not a meaningful confound. G processes identical total programs (50 x 8 = 400) in both arms under identical per-program conditions. The sync hook spaces out G's epochs differently, but the MAP-Elites algorithm is generation-indexed, not time-indexed. **However, Confound 4 would benefit from a sentence clarifying that G processes the same total programs in both arms and that the blocking fraction difference affects only wall-clock pacing, not per-program mutation quality.**

**Severity**: Minor.

### 3.4 Evaluation protocol consistency -- NO ISSUE

Both arms use the same evaluation: `actual_fitness` from the Heilbronn validator, same `significant_change=0.01`, same `mutation_mode=rewrite`, same model. The DV (max(G,D) actual_fitness) is correctly motivated by the baseline-repro finding. No concerns.

---

## 4. Information Gain -- HIGHEST VALUE

I consulted PATTERNS.md and INDEX.md. Eight experiments have tested information-level, information-architecture, and coupling-granularity interventions. All have failed to break Improver stagnation. Compute budget asymmetry is explicitly listed as "the single remaining untested intervention class" in PATTERNS.md. The v1/v2 natural experiment provides the strongest internal evidence for this direction.

If NULL, it closes the compute budget hypothesis and promotes the search-space hypothesis (structured Improver operators). If POSITIVE, it opens an ablation program. Either outcome is highly informative. This is the correct next experiment.

---

## 5. Stopping Rule Specificity -- GOOD

- **Hard stop**: `stopper=max_generations` with `max_generations=50`. Enforced programmatically.
- **Futility at gen 25**: Threshold (0.030) is well below baseline and below any prior experiment's worst pair. Conservative and appropriate.
- **Minimum completion**: >= 2/3 pairs per arm must reach gen 40. Clear and enforceable. The UNDERPOWERED (not INVALID) classification for partial arms is the right framing.

---

## 6. Sample Size -- ADEQUATE

N=3 per arm is an improvement over prior N=2 experiments. The design correctly notes that formal testing requires N >= 8 and relies on pre-registered effect-size thresholds rather than p-values. This is honest and appropriate.

I note for the record that the MDE formula omits the t_beta power term (recurring design flaw, see PATTERNS.md). The true MDE is approximately 1.4x the reported value. This does not affect the verdict logic because the pre-registered thresholds are magnitude-based.

---

## 7. Compound Treatment -- ADEQUATELY JUSTIFIED

The bundling of K=5 budget with loose coupling is justified by: (1) the v1/v2 evidence that loose coupling is necessary for budget asymmetry to be effective, (2) a 2x2 factorial exceeding available resources, and (3) an ablation follow-up plan. The Literature Scout brief (Recommendation 3) correctly flags that min_delta=1 may be the dominant effect. This is an acceptable trade-off for a first probe of the compute budget hypothesis.

---

## Summary of Concerns

| # | Concern | Severity | Section | Action Required |
|---|---------|----------|---------|-----------------|
| 1 | `max_elites_per_generation=8` not in Section 13 pre-launch verification table (default is 5) | Minor | 13 | Add to verification table |
| 2 | `min_delta=40` coupling regression not in Section 10 run invalidation criteria | Minor | 10 | Add invalidation criterion |
| 3 | A POSITIVE result cannot decompose K=5 vs loose coupling -- not stated in Section 12 | Minor | 12 | Add clarifying sentence |
| 4 | Confound 4 (G blocking fraction) could clarify G processes identical total programs | Minor | 9 | Add one clarifying sentence |

No critical concerns. No major concerns.

---

## Hypothesis and Falsifiability

- [x] H0 clearly stated
- [x] H1 falsifiable and directional
- [x] Primary metric pre-specified (max(G,D) actual_fitness)
- [x] Success criteria numeric and unambiguous (4-tier threshold table)

## Confound Analysis

- [x] Controlled variables genuinely controlled (verified against config YAMLs)
- [x] IV isolated (compound treatment acknowledged and justified)
- [x] Known confounds mitigated or acknowledged (7 confounds listed with mitigations)
- [x] Val/test split not contaminated (single metric, no val/test distinction for Heilbronn)

## Evaluation Protocol

- [x] Metric computed identically across conditions
- [x] Val/test sets fixed and identical for all runs (Heilbronn n=11 point set)
- [x] No post-hoc metric selection
- [x] Thinking mode consistent across evaluations (same model, same proxy)

---

## Verdict

**[x] APPROVED**

This design is methodologically sound. The research question is the highest-value next experiment given 8 prior null/inconclusive results on information-level interventions. The compound treatment is honestly acknowledged and pragmatically justified. The within-experiment control is the correct design choice. The treatment verification protocol is the strongest in the Heilbronn series. The stopping rules are specific and enforceable. The four minor issues should be addressed before pre-registration but do not block approval.

*The science demands nothing less.*

---

*Reviewed by: Prof. Andrei Volkov, 2026-04-16*
