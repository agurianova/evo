# Adversarial Review: heilbron/adversarial-repro-v2

**Date**: 2026-04-22
**Reviewer**: A. Volkov (reviewer-2-adversary)
**Input**: `experiments/heilbron/adversarial-repro-v2/01_design.md`

---

## Summary of Design

This experiment stacks three treatments on top of the v1 replication (which returned NULL in PR #211): (a) SharedBenchmarkFilteredLineageStage on D-side, (b) OpponentSamplingMode.SOFTMAX on G with TOP_K retained on D, and (c) D-side two-pass bucketed refresh (generation_bucketed + refresh_passes=2). The I-16/I-17 bug fixes carry over from v1. Attribution is intentionally deferred; the goal is to detect whether any combination of these treatments unlocks signal. N=4 G-runs (2 arms x 2 pairs) at max_generations=200. Primary DV is mean best-ever actual_fitness compared against v1's post-relaunch mu_G=0.03430.

The design is explicitly a "deliberately confounded replication." This framing is honest and appropriate for an exploratory probe. The two-pass bucketed refresh mechanism is carefully specified with a rigorous treatment of the cache-invalidation invariant. The treatment verification protocol (section 12) is unusually thorough.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|---------------|
| 1 | Baseline reference value mu_v1_G inconsistent with v1 results | **Major** | Correct the baseline or explain the discrepancy |
| 2 | Stacked treatment interpretation under N=4 | **Major** | Add explicit null-interpretation guard |
| 3 | SBF-Lineage silent fallback via lineage_filter config wiring | Minor | Add --cfg job verification for lineage_filter.min_shared |
| 4 | refresh_passes/refresh_order not in any YAML config file | Minor | Document how Hydra override reaches Pydantic defaults |
| 5 | G-side treatments not fully enumerated | **Major** | Clarify what changed on G between v1 and v2 |
| 6 | Literature brief is stale (written for v1, not updated for v2) | Minor | Update or note the gap |

---

## Concern 1: Baseline Reference Discrepancy (Major)

The design states in section 2: "Let **mu_v1_G** = 0.03430 (v1 grand mean across 4 G runs post-I-16/I-17 relaunch, per `05_results.md` section 5)."

However, the v1 `05_results.md` reports **mean best-ever = 0.03413**, not 0.03430. The difference (0.00017, or 0.17pp) is small in absolute terms but non-trivial relative to the NULL band width (0.001pp = 0.0338-0.0348). A shifted baseline changes which verdict band the observed v2 mean falls into.

The origin of 0.03430 is unclear. It may be a typographical error, a different averaging window, or computed from a different subset of runs. Whatever the source, the pre-registered baseline value must match the v1 results document exactly, or the deviation must be documented and justified.

**Recommendation**: Correct mu_v1_G to 0.03413 (matching v1 05_results.md line 119), OR explain the discrepancy and cite the exact source of 0.03430. Recalculate all verdict thresholds in section 2 accordingly.

---

## Concern 2: Stacked Treatment Under N=4 -- Risk of Uninformative NULL (Major)

The design correctly acknowledges this is "deliberately confounded." What it does not adequately address is the *interpretive asymmetry* of a null result.

- **If v2 shows signal**: The composite treatment works. Decomposition follows. This is informative.
- **If v2 is NULL**: We learn that the *specific combination* {SBF-Lineage + SOFTMAX + two-pass bucketed refresh} fails. But we cannot rule out that any individual treatment works -- it could be that one treatment helps (+0.003pp) while another hurts (-0.003pp), and they cancel. A NULL here would NOT close any of the three individual research directions.

With N=4 and power ~30% for a 0.002pp effect (section 7), there is a substantial probability of a false-NULL even if the composite treatment has a real positive effect. The design needs to state explicitly what a NULL result closes and what it does not close.

Moreover, the three treatments are not independent in their mechanism: SBF-Lineage changes D's mutation prompt, SOFTMAX changes G's opponent exposure, and two-pass bucketed refresh changes D's archive consistency. Treatment (c) is mechanistically entangled with treatment (a) -- the two-pass refresh exists specifically to make SBF-Lineage's descendant narratives consistent. If SBF-Lineage has no effect, the two-pass refresh is wasted compute. This is not a confound per se (both apply to D), but it means a NULL could indicate either "SBF-Lineage is useless regardless of data freshness" or "SBF-Lineage needs fresh data AND something else." The design should acknowledge this entanglement explicitly.

**Recommendation**: Add a subsection to section 2 (or section 9) titled "Interpretation of NULL" that specifies: (i) a v2 NULL does NOT close any of the three individual treatment directions; (ii) a v2 NULL with the SBF-Lineage kept/total diagnostic showing high ratios (>50%) would implicate SOFTMAX as the cancellation source; (iii) a v2 NULL with low kept/total (<20%) would implicate SBF-Lineage as inert. The diagnostic protocol in section 13.3 already supports this, but the interpretation framework is missing.

---

## Concern 3: SBF-Lineage Silent Fallback (Minor)

The `lineage_filter` config is defined in `adversarial_asymmetric.yaml` (lines 126-129) with `min_shared: 1` and `inject_shared_evidence: true`. The design pins these values in section 12.4. However, the pinned contract format (`pipeline_builder.lineage_filter.min_shared: 1`) uses a dotted Hydra path that must correctly resolve through the `_target_` instantiation chain.

I traced the code: `LineageFilterConfig` is a dataclass with defaults (`min_shared=1`, `inject_shared_evidence=True`). Even if the Hydra override fails silently, the defaults happen to match the intended treatment. This means a wiring failure would be invisible -- the treatment would still apply, but through defaults rather than explicit configuration. This is not a validity threat (the treatment is the same either way), but it weakens the treatment verification claim.

**Recommendation**: Add `lineage_filter.min_shared` and `lineage_filter.inject_shared_evidence` to the `--cfg job` verification checklist in section 12.1. If the values appear in the dump, the wiring is confirmed. If they do not appear (because Hydra collapsed the `_target_` to defaults), note that the defaults match the intended values.

---

## Concern 4: refresh_passes/refresh_order Override Path (Minor)

The `engine_config` section in `config/evolution/steady_state.yaml` does not include `refresh_order` or `refresh_passes` keys. These are Pydantic-only defaults on `SteadyStateEngineConfig` (default `fifo` and `1` respectively). The design specifies them as `engine_config.refresh_order=generation_bucketed` and `engine_config.refresh_passes=2` via `extra_overrides`.

Hydra's `OmegaConf` can inject keys into a dict that feeds a `_target_` constructor, and Pydantic will accept them. This should work. But the mechanism is fragile: if Hydra's struct flag is set on the `engine_config` node, the override would be rejected silently (Hydra struct mode rejects unknown keys). I did not find an explicit `struct: true` on this node, so the override likely succeeds. However, this is worth a `--cfg job` confirmation.

**Recommendation**: Add `engine_config.refresh_order` and `engine_config.refresh_passes` to the `--cfg job` verification checklist. Document that these are Pydantic-only defaults that do not appear in any YAML config file, so their absence from config files is expected and NOT evidence of a wiring failure.

---

## Concern 5: G-Side Treatment Enumeration Incomplete (Major)

Section 5a lists per-role asymmetric configs, and section 1 lists four changes. However, the full treatment delta between v1 and v2 on the **G side** is not completely enumerated. Specifically:

1. **SOFTMAX sampling on G** -- listed (change b). This changes G's opponent IDs every generation.
2. **archive_reeval=false on G** -- listed as unchanged from v1. Correct.
3. **I-16 fix (evaluate.py artifact tuple)** -- listed. Affects G's artifact flow to DGTrackerStage.
4. **I-17 fix (CompositionInjectionHook lineage)** -- listed. Affects G's archive topology.

But consider: v1 ran on the **old library** (commit 04bd5e69). v2 runs on the **current library**. The codebase map (section 10, post-closeout note) explicitly states that `SharedBenchmarkLineageStage` was replaced by `SharedBenchmarkFilteredLineageStage`. What other library-level changes exist between the v1 commit and the current branch?

The design pins hyperparameters (section 5) and problem files (frozen evaluate.py) but does **not** control for library drift in pipeline builder logic, stage implementations, or engine scheduling. The codebase map acknowledges this as "residual gap #2" but only in the literature brief, not in the design's own confound analysis (section 9). Section 9 lists 7 confounds; library drift is absent.

This matters because the design claims to test whether "three improvements ... recover signal." If the library has also changed in ways that degrade performance (e.g., different DAG scheduling, different mutation prompt formatting), a positive result would be attenuated, and a NULL would be ambiguous between "treatments failed" and "library drift canceled the treatment effect."

**Recommendation**: Add library drift as confound #8 in section 9. Specify: (i) only hyperparameters and problem files are frozen; pipeline builder code, engine scheduling, and stage implementations are at current HEAD; (ii) a full library diff from 04bd5e69 to current HEAD affecting `gigaevo/programs/stages/`, `gigaevo/adversarial/`, and `gigaevo/engine/` should be generated and archived as a reproducibility artifact; (iii) this confound is shared across all v2 runs (not varying between conditions) and therefore cannot explain cross-arm differences, only between-experiment differences.

---

## Concern 6: Literature Brief Staleness (Minor)

The literature brief in the experiment directory was written for v1 (`"Experiment: heilbron/adversarial-repro-v1"`, dated 2026-04-19). It does not discuss the three v2-specific treatments (SBF-Lineage, SOFTMAX sampling, bucketed refresh) in its novelty assessment or related work. The codebase map also carries a v1 header.

This is a documentation hygiene issue, not a validity threat. The literature brief's related work (PSRO, WGAN-GP, Ficici & Pollack) is still relevant. However, the novelty assessment section ("Has the exact mechanism been tested?") is answering the wrong question -- it assesses v1 replication novelty, not v2 stacked-treatment novelty.

**Recommendation**: Either update the literature brief to assess v2-specific novelty or add a note in the design document (section 1) acknowledging that the literature brief covers the v1 replication framing and that v2's additional treatments are novel within the GigaEvo experimental program (no prior experiment has tested SBF-Lineage, SOFTMAX, or two-pass bucketed refresh).

---

## Hypothesis and Falsifiability

- [x] H0 clearly stated
- [x] H1 falsifiable and directional
- [x] Primary metric pre-specified
- [x] Success criteria numeric and unambiguous (with the baseline caveat in Concern 1)

**Notes**: The verdict thresholds (section 2) are well-structured and span the outcome space (POSITIVE / SUGGESTIVE / NULL / REGRESSIVE). The abandon-direction criterion (section 2, final paragraph) is specific and actionable. The one-sided framing (H1 tests improvement only) is appropriate for an exploratory probe after a NULL predecessor.

---

## Confound Analysis

- [x] Controlled variables genuinely controlled (section 5 is thorough)
- [ ] IV isolated -- **deliberately not isolated; acknowledged**
- [x] Known confounds mitigated or acknowledged (7 listed; 1 missing per Concern 5)
- [x] Val/test split not contaminated (no test set in Heilbronn; actual_fitness IS the DV)

**Unaddressed confounds**:

1. **Library drift** (Concern 5) -- absent from section 9. Not varying between conditions but affects the between-experiment comparison to v1.
2. **Class-level `_refresh_pass_token` is shared across all D runs** -- `SharedBenchmarkFilteredLineageStage._refresh_pass_token` is a **class variable**, not instance-level. If multiple D runs share the same Python process (e.g., via a shared worker pool), token bumps from one D run would invalidate caches in another. The design specifies 8 concurrent processes on a single server (section 11). If each run is a separate process, the class variable is process-local and this is not a confound. If runs share a process, it is. The design should confirm that each run is an independent OS process.

---

## Statistical Validity

- [x] Sample size justified (N=4, honestly acknowledged as weak; section 7)
- [x] Statistical test appropriate (Welch t-test + bootstrap CI)
- [x] Significance threshold pre-specified (effect-size thresholds, not p-value)
- [x] Multiple comparison correction not needed (single primary comparison)

**Notes**: At N=4 with ~30% power, the Welch t-test is decorative. The verdict will be driven by effect-size thresholds, which is the correct approach at this sample size. I do not object to this design. The honest acknowledgment in section 7 is appreciated.

---

## Evaluation Protocol

- [x] Metric computed identically across conditions (frozen evaluate.py)
- [x] Val/test sets fixed (Heilbronn has no val/test split; actual_fitness is computed directly)
- [x] No post-hoc metric selection (primary DV pre-specified; secondary DVs listed in section 4)
- [x] Thinking mode consistent (same model, same proxy)

**Notes**: The evaluation protocol is clean. The frozen evaluate.py (hard-floor fitness) is identical across all 8 runs and matches the v1 scoring. This is one of the design's strengths.

---

## Treatment Integrity Assessment

**SBF-Lineage (treatment a)**: Traced through the codebase. `_replace_lineage_with_filtered` is called at `asymmetric_pipeline.py:150` only when `population_role == "improver"`. The `lineage_filter` config is wired from `adversarial_asymmetric.yaml:126-129`. The stage constructor rejects `min_shared=0`. Treatment application is conditioned on `population_role` and `dg_tracker is not None` -- both must be correct for the stage to install. The verification protocol (section 12.2, grep for `[LineageStage:SharedBenchmark] kept`) correctly detects whether the treatment is active. **Integrity: GOOD** -- treatment can be verified at runtime and fails noisily if `population_role` is wrong.

**SOFTMAX sampling (treatment b)**: `opponent_sampling_mode` defaults to `"top_k"` in `adversarial_asymmetric.yaml:88`. The G-run override to `"softmax"` comes via `extra_overrides`. `AdversarialPipelineBuilder.__init__` logs the sampling mode (line 112-117). The verification protocol (section 12.1, grep for `opponent_sampling_mode=softmax`) correctly detects the override. If the override fails silently, G falls back to `top_k` -- which is v1 behavior. This fallback would eliminate treatment (b) while preserving treatments (a) and (c). **Integrity: ADEQUATE** -- log verification catches the failure. However, the design does not specify what to do if the override fails (abort the run? continue and note the confound?). Add an action item.

**Two-pass bucketed refresh (treatment c)**: The override path (`engine_config.refresh_order=generation_bucketed`, `engine_config.refresh_passes=2`) goes through Hydra into `SteadyStateEngineConfig` Pydantic defaults. The design specifies verification via `grep "Bucketed refresh"` and `grep "Multi-pass refresh done.*2 passes"` in D logs (section 12.1). The cache invariant is ensured by the class-level `_refresh_pass_token` mechanism, which is unit-tested (`TestMultiPassRefresh`, `TestRefreshPassesConfig`). **Integrity: GOOD** -- log verification catches the failure; unit tests cover the mechanism.

---

## Cross-Program Cache Invariant (Detailed Trace)

The design's cache-invalidation argument (section 5a) is the most technically complex claim. I traced it through the code:

1. `SharedBenchmarkFilteredLineageStage._refresh_pass_token` is a class-level `int`, initialized to 0. `bump_refresh_pass()` increments it by 1. `compute_hash()` appends `:rp{token}` to the base hash.

2. `SteadyStateEvolutionEngine._refresh_archive_programs()` loops `self._ss_config.refresh_passes` times. Before each pass, it calls `SharedBenchmarkFilteredLineageStage.bump_refresh_pass()`.

3. Pass 1 generates cache keys with token `T`. Pass 2 generates cache keys with token `T+1`. Since the token differs, all `SharedBenchmarkFilteredLineageStage` computations re-execute in pass 2.

4. `MutationContextStage` consumes `LineagesFromAncestors` and `LineagesToDescendants` gather outputs. These are `NO_CACHE`. When the source `LineageStage` output changes (due to the re-execution in pass 2), the gather outputs change, and `MutationContextStage`'s input hash changes, triggering a cache miss.

**Assessment**: The cache-invalidation chain is sound. The class-level token mechanism correctly forces re-execution in pass 2. The downstream propagation through NO_CACHE gathers to MutationContextStage is correct by construction (data-flow edges with NO_CACHE gathers propagate output changes).

**One subtlety the design should note**: The `_refresh_pass_token` is class-level, not instance-level. If the engine is somehow re-instantiated within the same process (e.g., a retry mechanism that creates a new engine), the token continues from its prior value, which is correct (it only needs to differ between consecutive passes, not be globally unique). However, if multiple engines share the same class namespace in one process (hypothetical but worth ruling out), they would interfere. The design's 8-process architecture makes this impossible. Document this assumption.

---

## Between-Experiment Comparison Validity

The primary comparison is v2 mu_G vs v1 mu_G=0.03430 (or 0.03413 per the actual v1 results -- see Concern 1). This is a between-experiment comparison across different commits, different run dates, and a different library state.

**Threats**:
1. Library drift (Concern 5) -- uncontrolled between-experiment variable.
2. LLM proxy state -- same proxy but potentially different load, caching, or routing.
3. Redis server state -- design mandates flush; if executed correctly, this is controlled.
4. Run duration -- v1 ran 200 gens post-relaunch; v2 also runs 200 gens. This is matched.

**Assessment**: The between-experiment comparison is inherently weaker than a within-experiment comparison. The design has no contemporaneous control arm (no "v1 config with v2 library" control). This is acceptable for an exploratory probe -- the goal is "does anything move?" not "did treatment X cause the movement?" -- but the design should explicitly state that the between-experiment comparison is not a controlled test and that the verdict thresholds account for this by being wide (0.001pp NULL band).

---

## Information Gain Assessment

**Given v1 NULL, what does v2 tell us?**

- **If POSITIVE**: At least one of the three treatments (or their interaction) works. This reopens the Heilbronn adversarial research line and motivates decomposition experiments. High information gain.
- **If SUGGESTIVE**: Directional evidence that the composite treatment helps. Worth a replication at higher N. Moderate information gain.
- **If NULL**: The composite treatment fails. Does NOT close individual treatment directions (Concern 2). Low information gain unless the diagnostic decomposition (section 13.3, 13.4) reveals which component is inert. The design's diagnostic protocol salvages some information from a NULL.
- **If REGRESSIVE**: SOFTMAX stochasticity or SBF-Lineage filtering actively harms. High information gain (closes the composite and strongly implicates one component).

**Comparison to REDESIGN bundle**: PATTERNS.md identifies the REDESIGN bundle (smoothed tanh fitness + deterministic HoF + K=L=3 + cache_on edges) as the "#1 PRIORITY" open question. The v2 experiment does not address the D hard-floor fitness defect -- it deliberately preserves it. If the D hard-floor is the binding constraint (as 10 prior experiments suggest), then v2's treatments operate on a broken fitness landscape and are unlikely to produce signal. The design acknowledges this implicitly (section 1, "I-16 fix" and the literature brief's D-collapse discussion) but does not explicitly position v2 relative to the REDESIGN bundle priority.

**Recommendation**: Add a brief note to section 1 explaining why v2 is run before the REDESIGN bundle. The justification exists (v2 tests whether info-flow improvements alone suffice under the existing fitness landscape, which is a precondition check before committing to the REDESIGN bundle), but it should be stated explicitly.

---

## Novelty Check

The literature brief does not cover v2's specific treatments. Checking against PATTERNS.md and INDEX.md:

1. **SharedBenchmarkFilteredLineageStage**: Novel. No prior experiment has tested filtered lineage narratives based on shared-opponent evaluation benchmarks.
2. **SOFTMAX sampling**: Novel in the Heilbronn adversarial context. No prior heilbron experiment used stochastic opponent sampling.
3. **Two-pass bucketed refresh**: Novel mechanism. No prior experiment used multi-pass refresh.

The combination has never been tested. There is no risk of redundancy with prior experiments.

---

## Required Changes Before Approval

1. **(Major)** Correct the baseline reference. mu_v1_G is stated as 0.03430 but v1's 05_results.md reports 0.03413. Either correct the value and recalculate verdict thresholds, or cite the exact source of 0.03430 and justify the discrepancy.

2. **(Major)** Add an "Interpretation of NULL" subsection. A v2 NULL does not close any individual treatment direction. State this explicitly and describe how the SBF-Lineage diagnostic (section 13.3) and cache-invalidation diagnostic (section 13.4) will be used to localize failure to a specific component.

3. **(Major)** Add library drift as confound #8 in section 9. Specify that pipeline builder code, engine scheduling, and stage implementations are at current HEAD (not frozen at v1 commit). Note that this confound is shared across all runs (symmetric) and therefore does not affect within-experiment arm comparisons, only the between-experiment comparison to v1.

4. **(Minor)** Add `lineage_filter.min_shared`, `lineage_filter.inject_shared_evidence`, `engine_config.refresh_order`, and `engine_config.refresh_passes` to the `--cfg job` verification checklist in section 12.1.

5. **(Minor)** Add a note that each of the 8 runs is an independent OS process, confirming that the class-level `_refresh_pass_token` is process-local and cannot leak between D runs.

6. **(Minor)** State what action to take if the SOFTMAX override verification (section 12.1, grep for `opponent_sampling_mode=softmax`) fails on any G run: abort and relaunch, or continue and note the confound.

7. **(Minor)** Add a brief note to section 1 positioning v2 relative to the REDESIGN bundle priority: v2 tests info-flow improvements on the existing (broken) fitness landscape; a positive result would be remarkable and would suggest info-flow was the binding constraint, not D hard-floor. A NULL is consistent with the REDESIGN-first hypothesis.

---

## Verdict

**[x] NEEDS REVISION**

Three major concerns require resolution: (1) the baseline reference discrepancy, (2) the missing null-interpretation framework, and (3) the missing library-drift confound. None of these are fatal to the design -- all can be addressed by adding or correcting text in the existing document. The four minor concerns should be addressed but do not block approval.

The underlying experimental design is sound. The three-treatment stack is an appropriate exploratory strategy after a NULL predecessor. The cache-invalidation mechanism is well-engineered and well-tested. The treatment verification protocol is thorough. The diagnostic decomposition plan (section 13.3-13.4) is a genuine strength that partially compensates for the stacked-treatment confound. Once the three major concerns are resolved, I expect to approve.

*The science demands nothing less.*

---

## Follow-up Review (2026-04-22)

**Reviewer**: A. Volkov (reviewer-2-adversary)
**Scope**: Targeted verification of 3 Major + 4 Minor concerns from initial review.

---

### Major #1 — Baseline correction (0.03430 to 0.03413)

**Addressed.** Section 2 now reads `mu_v1_G = 0.03413 (v1 grand mean across 4 G runs post-I-16/I-17 relaunch, per 05_results.md section 5)`. The NULL band is recalculated as 0.03313-0.03513 (symmetric 0.001 around the corrected mean). REGRESSIVE threshold at < 0.0330 is consistent. All verdict thresholds track the corrected baseline.

### Major #2 — NULL interpretation framework

**Addressed.** Section 2 now contains two new subsections: "Interpretation of NULL (stacked-treatment asymmetry)" with a four-row diagnostic-pattern table mapping kept/total ratio and cache-miss patterns to specific next experiments, and "Mechanistic entanglement note" explicitly acknowledging that the two-pass refresh is mechanistically coupled to SBF-Lineage. The false-NULL probability (~70% at ~30% power) is stated. This is thorough work.

### Major #3 — Library drift confound

**Addressed.** Section 9 confound #8 specifies the v1 commit (04bd5e69) vs current HEAD, lists the categories of uncontrolled code (pipeline builder, engine scheduling, stage implementations, mutation prompt formatter), and correctly notes the confound is symmetric across all 8 v2 runs. The three mitigations (environment_freeze.txt, wider NULL band, fragile-vs-robust claim separation) are appropriate. The note that library drift "cannot explain cross-arm differences within v2; it only affects the between-experiment comparison to v1" is exactly the framing I requested.

### Minor #3/#4 — Hydra override gate

**Addressed.** New section 12.0 provides explicit `--cfg job` grep assertions for `opponent_sampling_mode`, `archive_reeval`, `refresh_order`, `refresh_passes`, and `lineage_filter`. The ABORT instruction on missing overrides is present. Section 12.1 now includes a clear ABORT-on-SOFTMAX-failure action with the specific failure mode described (run silently converts to v1 replication).

### Minor #5 — Process isolation of `_refresh_pass_token`

**Addressed.** Section 9 confound #7 (final paragraph) explicitly states each run is a separate `run.py` invocation with separate Python interpreter and address space, that no shared-memory or multiprocessing fork path exists, and that a token leak would require a shared Python runtime which the deployment topology forbids.

### Minor #6 — Literature brief staleness

**Addressed.** Section 1 includes a "Literature-brief scope note" paragraph identifying that the v1-era brief does not independently survey the three v2 treatments and noting all three are novel within GigaEvo's experimental program with no prior independent testing.

### Minor #7 — REDESIGN positioning

**Addressed.** Section 1 includes a "Positioning vs REDESIGN bundle" paragraph explaining v2 as a cheap precondition check: positive implies info-flow was binding (remarkable), null is consistent with the REDESIGN-first hypothesis.

---

### Verdict

**Overall Verdict: APPROVED**

All three major concerns and all four minor concerns have been resolved with appropriate specificity. The design is ready for pre-registration.

*The science demands nothing less.*
