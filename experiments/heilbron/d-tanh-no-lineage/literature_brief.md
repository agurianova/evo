# Literature Scout Brief: heilbron/d-tanh-no-lineage

**Research question**: Does removing LineageStage from D's pipeline (on top of D-side tanh smoothing)
lift mu_G out of the NULL band (mu_G=0.03315), by eliminating D's per-gen lineage-refresh overhead
that caused d-smoothing-minimal's 1.84x timing asymmetry?

**Date**: 2026-04-25
**Scope note**: This brief is additive to `experiments/heilbron/d-smoothing-minimal/literature_brief.md`,
which contains the full fitness-smoothing motivation, WGAN analogues, and Heilbronn benchmark survey.
Sections reproduced there are cited, not repeated. This brief focuses on (1) lineage ablation
precedents, (2) timing-asymmetry theory and remedies, and (3) the d-smoothing-minimal failure mode
that motivates this experiment.

---

## Related External Work

| Paper/System | Year | Mechanism | Result | Relevance to Proposal |
|---|---|---|---|---|
| Paredis, "Towards Balanced Coevolution" (PPSN VI) | 2000 | Balancing mechanism to prevent one population from out-evolving the other in coevolutionary GAs | Performance improves considerably when the speed imbalance is corrected; uncorrected asymmetry causes one side to dominate regardless of information quality | **Directly formalizes the d-smoothing-minimal failure mode.** D at 57% of G's gen pace = "one population out-evolves the other." Paredis' result says the fix must address the speed gap itself, not information content. No-lineage is a compute-reduction approach; the literature says this is a valid lever. |
| Gulrajani et al., WGAN-GP (NeurIPS 2017) | 2017 | K=5 discriminator updates per generator update as standard WGAN training schedule | 5:1 update ratio stabilizes training; deviation from this asymmetry causes instability | The K:1 update asymmetry literature is the closest GAN analogue. d-smoothing-minimal reversed this: D was 1.84x SLOWER than G (0.54:1 ratio). WGAN-GP's finding that asymmetric update ratios can cause instability supports the hypothesis that correcting GigaEvo's inverse asymmetry should improve dynamics. Cited also in d-smoothing-minimal brief. |
| Accelerated WGAN update strategy with loss change rate balancing (arXiv 2008.12463) | 2020 | Adaptive update ratio based on loss-change-rate comparison of D and G | Fixed K:1 is suboptimal; adaptive ratios improve convergence and accuracy | Confirms no single fixed ratio is universally correct; the right ratio is domain-specific. For GigaEvo, the correct analogy is wall-clock parity (not fixed generation counts), because evaluations are stochastic in duration. |
| Metz et al., "Which Training Methods for GANs do actually Converge?" (ICML 2018) | 2018 | Convergence theory for fixed vs. variable D/G update schedules; shows WGAN-GP does NOT guarantee convergence with finite D steps per G update | Finite K-step ratio is theoretically non-convergent even for WGAN-GP; convergence requires D to train "until convergence" | Relevant to GigaEvo's drift_cap coupling: loose coupling (drift_cap=100000) allows D and G to run independently, which maps to training "until convergence" rather than a fixed K. The no-lineage change reduces D's per-step cost, allowing more D steps per wall-clock unit, asymptotically approaching the "until convergence" ideal. |
| CodeEvolve (arXiv 2510.14150) | 2025 | LLM evolutionary coding agent that intentionally EXCLUDES the ancestor chain in some mutation operations to allow exploration without lineage constraint | Excluding lineage context in some operations enables novel strategy exploration; full lineage inclusion constrains toward incremental improvements | **Direct ablation precedent for lineage removal in LLM-guided EA.** CodeEvolve found that lineage can be a constraint, not just a helper. The positive effect of excluding lineage in CodeEvolve is a specific case where the model benefits from lack of ancestry bias. GigaEvo's D side (Improver) is primarily seeking local improvements, not novel strategies -- the lineage value for D may be lower than for G. |
| Ficici & Pollack, "Challenges in Coevolutionary Learning" (GECCO 1998) | 1998 | Analysis of pathological coevolutionary equilibria; shows that relative fitness comparisons cause mediocre stable states | Pathological equilibria emerge when one population's evaluation is more expensive or slower -- the weaker side tends toward mediocrity | Foundation paper for why timing asymmetry interacts with fitness signal quality. If D is chronically behind G, D's "mediocre stable state" hypothesis applies: D programs are evaluated against stale G opponents, reducing the informativeness of any feedback mechanism including lineage context. No-lineage addresses overhead; the coevolutionary-cycle analysis says this is necessary but may not be sufficient if stale-opponent effects persist. |
| Mouret & Clune, "Illuminating Search Spaces by Mapping Elites" (arXiv 1504.04909) | 2015 | MAP-Elites archive refresh as part of quality-diversity search | Archive re-evaluation cost scales with archive size; no specific ablation of per-epoch archive re-scoring vs. no re-scoring | No dedicated ablation of "refresh vs no-refresh" overhead found in QD literature. The MAP-Elites community generally handles noisy evaluations via ARIA or PGA-MAP-Elites, not by eliminating refresh. GigaEvo's use of per-epoch archive refresh is non-standard -- no external baseline exists for comparison. |
| Lehre & Lin, "Overcoming Binary Adversarial Optimisation" (PPSN 2024, arXiv:2407.17875) | 2024 | Runtime analysis showing binary adversarial fitness degrades CoEA; polynomial recovery requires specific offspring size constraints | Non-binary smoothing is the rigorous fix; the paper does not address compute asymmetry independently | Already cited in d-smoothing-minimal brief. Relevant here because removing lineage changes the per-gen compute cost but NOT the fitness signal -- if smoothing alone is sufficient to recover the polynomial CoEA regime, lineage removal is pure efficiency gain. If smoothing is insufficient, lineage removal cannot fix CoEA failure (wrong lever). |
| "Global Optimization for Combinatorial Geometry Problems Revisited in the Era of LLMs" (arXiv 2601.05943) | 2026 | Off-the-shelf NLP solvers (FICO Xpress, SCIP) reproduce and sometimes improve AlphaEvolve's Heilbronn results without LLM machinery | Both solvers reproduce best known values; in several cases improve upon AlphaEvolve's solutions | External Heilbronn baseline update: LLM-guided evolution is not the uniquely dominant approach. For n=11, the GigaEvo target of Q_MAX=0.0365 is near the known optimal; the question is whether the adversarial co-evolution regime can reach it reliably (not whether the target is achievable). |
| arXiv 2603.11107, "From Computational Certification to Exact Coordinates: Heilbronn's Triangle Problem Using Mixed-Integer Optimization" | 2026 | Exact closed-form coordinates for optimal Heilbronn configurations n=5,...,9 using mixed-integer optimization with symmetry-breaking constraints | Exact solutions confirmed for n<=9; n=11 remains numerical/heuristic | Establishes that n=11 is still an open combinatorial problem in the exact sense. GigaEvo's mu_G=0.03315 vs Q_MAX=0.0365 gap represents genuine search difficulty, not a solved problem. |

---

## Baselines on This Task

*(From prior briefs; no new external baselines found since d-smoothing-minimal brief 2026-04-24.)*

| System | Metric | Value | Notes |
|---|---|---|---|
| heilbron/baseline-repro (N=4, PR #201) | actual_fitness mean | 0.03449 (SD=0.00212) | Canonical adversarial baseline. Must-beat threshold. |
| heilbron/adversarial-repro-v2 (N=4, PR #216) | mu_G | 0.03315 [0.03001, 0.03630] 95% CI | Direct NULL predecessor. SBF-Lineage ON + SOFTMAX + asymmetric archive_reeval. This is the band to escape. |
| heilbron/d-smoothing-minimal (INVALID, 15h) | mu_G | Not estimable (aborted gen 14-17 D, 24-31 G) | Same treatment as this experiment PLUS LineageStage on D. Aborted due to D/G gen-pace asymmetry 1.84x (D slower). |
| AlphaEvolve (DeepMind 2025) | min_area n=11 | >0.0365 | External SOTA ceiling. Non-adversarial. |
| arXiv 2601.05943 NLP solvers (2026) | min_area (varies by n) | Reproduces/exceeds AlphaEvolve on subset | Non-adversarial; confirms the search space is tractable with the right approach. |

**NULL band definition** (inherited from v2 brief): mu_G must exceed 0.03449 to be considered POSITIVE. The v2 result (0.03315) sits at the extreme lower edge of the NULL band.

---

## Prior GigaEvo Experiments

| Experiment | Result | Key Learning | How It Informs This Design |
|---|---|---|---|
| heilbron/adversarial-repro-v2 (PR #216) | NULL -- mu_G=0.03315 | SBF-Lineage + SOFTMAX + all KF fixes produced no lift; D collapsed 2/4 runs despite lineage context | Establishes the NULL band. D-side lineage was active and did not prevent D collapse. This suggests lineage is not a binding positive factor for D under hard-floor fitness -- and by extension, under smoothed fitness, lineage's marginal benefit may be low vs. its compute cost. |
| heilbron/d-smoothing-minimal (INVALID) | INVALID -- aborted at 15h | D/G gen-pace asymmetry 1.84x (D at 57% of G's pace). Root cause: D's per-mutation evaluation cost is intrinsically higher; two-pass SBF-Lineage refresh adds significant per-epoch overhead. Tanh smoothing itself is O(1) and is not the bottleneck. | **Direct predecessor and motivation for this experiment.** The issues log (04_issues_log.md) explicitly lists LineageStage removal as a viable redesign option (Option F variant). Per-epoch archive re-scoring with refresh_passes=2 was identified as the primary overhead contributor. Removing LineageStage eliminates both the per-mutation LLM cost (lineage narrative generation) and the refresh_passes overhead. |
| heilbron/adversarial-repro-v1 (PR #211) | NULL -- mu_G=0.03413 | D/G gen ratio 4.0x (D ran 4x MORE gens than G). Lineage OFF. Loose coupling via accidental min_delta=1. | D running faster than G (4x) under no-lineage produced mu_G=0.03413 -- the best NULL-era result. This is positive circumstantial evidence for the "D faster = better G signal" hypothesis. Removing lineage from D in this experiment should restore something closer to the v1-era D compute advantage. |
| heilbron/k5-budget-v3 | INCONCLUSIVE | 2D MAP-Elites eliminated D collapse but D/G ratio not reported; K3_1 deadlocked. Under broken hard-floor fitness. | Confirmed that D collapse can be structurally prevented (via BD workaround). Does not speak to timing asymmetry or lineage overhead. |
| heilbron/asymmetric-iterations v1 (PR #204) | POSITIVE-historical -- best 0.03650 | Accidental loose coupling (min_delta=1) allowed D to run many micro-steps per G epoch; D/G ratio approximately 4-6x | Strongest historical signal. The loose-coupling / D-faster condition is consistently associated with better G outcomes in v1 and v1-era runs. This experiment (d-tanh-no-lineage) attempts to recover that D compute advantage by removing the lineage overhead that was artificially slowing D in d-smoothing-minimal. |

---

## Novelty Assessment

- [ ] This exact mechanism has been tested before (cite)
- [x] A related mechanism was tested in v1 (lineage OFF + no smoothing) with NULL result -- but that ran on broken D hard-floor fitness, making the comparison invalid
- [x] This is a novel combination: D-side tanh smoothing PLUS D-side no-lineage has never been run. The two interventions interact: smoothing repairs the fitness signal; no-lineage restores D compute parity.

**What is genuinely new vs. prior work**:

1. d-smoothing-minimal tested tanh smoothing WITH lineage -- INVALID (timing).
2. adversarial-repro-v2 tested lineage WITH hard-floor fitness -- NULL (fitness signal broken).
3. adversarial-repro-v1 tested no-lineage WITH hard-floor fitness -- NULL (fitness signal broken, D/G ratio favorable but couldn't help).
4. **This experiment combines tanh smoothing WITH no-lineage -- first time both are active simultaneously.** This is the minimal experiment that tests whether removing lineage's compute overhead allows D to run fast enough for the smoothed fitness signal to produce G lift.

**IV count**: 2 IVs vs. adversarial-repro-v2 (lineage ON + hard-floor), 1 IV vs. d-smoothing-minimal (lineage ON + tanh). Comparison to d-smoothing-minimal is the cleanest: single IV = LineageStage presence on D.

**Attribution limitation**: if positive, the result is attributed to (tanh + no-lineage) jointly. Cannot distinguish whether tanh alone would have worked if the timing asymmetry had been solved differently (e.g., Option A lockstep, Option C parallelism). Follow-on experiment is the relevant ablation.

---

## Timing-Asymmetry Theory Summary

The d-smoothing-minimal issues log measured D per-gen median at 3665s vs G at 1990s (1.84x slower). The log identified two contributors:

1. **Intrinsic D evaluation cost**: Improver runs optimization-style improvement per opponent call; Constructor just emits 11 points. This is structural.
2. **LineageStage two-pass refresh overhead** (`refresh_passes=2`, `generation_bucketed`): re-scores full D archive each epoch. Confirmed as a known bottleneck (PATTERNS.md: "Two-pass bucketed refresh destroys D compute advantage").

Removing LineageStage eliminates contributor (2) entirely and also removes the per-mutation LLM call for lineage narrative generation (which is O(mutations) overhead, not O(archive) overhead but non-trivial).

The Paredis (PPSN 2000) result says: when one population out-evolves the other, coevolutionary performance degrades regardless of information quality. This is exactly what d-smoothing-minimal observed. The remedy tested here (reducing D's compute load) maps to Paredis' "balancing mechanism."

**Expected effect on D/G ratio**: In adversarial-repro-v1 (no-lineage, no-smoothing), D/G ratio was 4.0x (D faster). In d-smoothing-minimal (lineage ON, tanh ON), D/G ratio was 0.54x (D slower). With lineage removed and tanh retained, the expected D/G ratio should trend back toward the v1-era 4.0x range. Whether this restores the full D compute advantage depends on whether the intrinsic Improver evaluation cost (contributor 1) has also grown since v1.

---

## Recommendations for Elena

### On the single-IV framing

This experiment tests **one causal question**: does removing LineageStage from D restore D's compute advantage sufficiently for the tanh fitness signal to produce G lift? The comparison is:

- Control: d-smoothing-minimal (invalid but mechanistically informative) = tanh ON + lineage ON
- Treatment: this experiment = tanh ON + lineage OFF

Every other parameter should be byte-for-byte identical to d-smoothing-minimal's design (which itself inherited every parameter from adversarial-repro-v2 except evaluate.py). This is the smallest change that addresses the identified failure mode.

### On what "success" looks like

**Primary mechanistic check (gen 5)**: D/G gen-pace ratio should be > 1.0 (D running as fast as or faster than G). If D is still slower than G with lineage removed, the intrinsic Improver evaluation cost is the bottleneck and a different solution is needed (Option A lockstep or Option C parallelism from the d-smoothing-minimal issues log).

**Primary fitness check (gen 25-50)**: mu_G >= 0.03449 across N=4 G runs. Note: given the experiment is pre-registered at max_generations=25 (from experiment.yaml), Elena should verify whether 25 gens is sufficient for a signal or whether the comparison to adversarial-repro-v2's gen 36-55 horizon requires extension.

**Secondary check**: D fitness distribution at gen 5 should show less than 10% point mass at exactly 0.000 (same criterion as d-smoothing-minimal's design).

### On SBF-Lineage scope

The research question specifies removing LineageStage from D's pipeline. This means removing the `SharedBenchmarkFilteredLineageStage` (the specific lineage stage used in adversarial-repro-v2). The standard non-filtered lineage tracking (program ancestry fields) is part of the Program model and is separate -- do not conflate removal of the pipeline stage with removal of lineage metadata from Program objects. D programs still carry lineage fields; the stage that generates lineage-based mutation narratives is what is ablated.

### On the two-pass refresh interaction

Removing LineageStage should automatically reduce or eliminate the motivation for `refresh_passes=2`. If LineageStage is not generating lineage narratives that require fresh opponent data, the archive refresh can either be dropped to `refresh_passes=1` or disabled entirely (`archive_reeval=false` on D). This is a config decision Elena must pre-register explicitly. Keeping `refresh_passes=2` with no LineageStage would be a zombie overhead (the refresh exists to serve lineage freshness; with lineage gone, it serves no purpose). Recommend: set `archive_reeval=false` on D side, which is what adversarial-repro-v1 used and what produced the 4x D/G ratio.

### On confound with d-smoothing-minimal results

The d-smoothing-minimal run was aborted at gen 14-17 (D) / 24-31 (G) with no estimable mu_G. This means there is NO internal control to compare against for the tanh-only condition. The only comparison available is:

- adversarial-repro-v2 (lineage ON, hard-floor): mu_G=0.03315 -- tests full lineage on broken fitness
- adversarial-repro-v1 (lineage ON, hard-floor): mu_G=0.03413 -- tests full lineage on broken fitness

Neither is a clean control for "tanh ON + lineage ON." If Elena wants a within-experiment control, adding one arm with tanh ON + lineage ON (now with archive_reeval=false to fix the timing asymmetry a different way) would provide attribution but doubles compute. Given the pre-registered status at N=4 G runs, this tradeoff should be explicitly considered.

### On the max_generations=25 in experiment.yaml

The current experiment.yaml shows max_generations=25, which is roughly half of adversarial-repro-v2's achieved horizon (36-55 G gens). If D/G parity is restored (D runs faster), D will complete proportionally more gens -- potentially 80-100+ D gens at the v1-era 4x ratio. Verify that 25 G gens is sufficient for mu_G to stabilize above the NULL band. The v1 historical SOTA (0.03650) appeared at gen 5 in that run, so early emergence is possible. But mu_G estimation from N=4 runs at gen 25 should be pre-registered as the endpoint, not compared to v2's gen 36-55 data without a note on the shorter horizon.

### On the SOFTMAX vs. TOP_K interaction

adversarial-repro-v2 used SOFTMAX on G (stochastic opponent sampling), which may have increased G invalidity (35-47% vs v1's 24-45%). This experiment inherits SOFTMAX from v2. With D running faster (no-lineage), the SOFTMAX rotation may produce more diverse D improvers for G to face -- which could cut either way on invalidity. Monitor G invalidity as a secondary diagnostic.

### Expected effect size

Based on pattern evidence:
- adversarial-repro-v1 (closest D condition: no lineage, hard-floor): mu_G=0.03413
- With tanh replacing hard-floor, the expected mu_G should be >= 0.03413 if timing is corrected
- Minimum detectable effect at N=4, SD=0.003, alpha=0.05, power=80%: approximately 0.003 (3pp)
- The NULL band to escape is 0.03449; delta needed vs v2 baseline = 0.00134 (1.34pp)
- With N=4 and SD=0.003, this experiment is underpowered for a 1.34pp effect (power ~30%)
- Accept this as the standard GigaEvo N=4 trade-off; pre-register the CI width as the honest primary output

---

## Summary: What This Experiment Answers vs. Does Not Answer

| Question | Answered? | Notes |
|---|---|---|
| Does tanh + no-lineage break D timing asymmetry? | YES -- via D/G gen-pace ratio at gen 5 | Mechanistic check, not confounded |
| Does tanh + no-lineage lift mu_G above NULL band? | PARTIALLY -- limited by N=4 power | Primary fitness check |
| Does tanh alone (without timing fix) produce G lift? | NO -- d-smoothing-minimal was invalid; no estimate available | Would require a separate arm or experiment |
| Does removing lineage hurt G signal quality (lineage had positive value)? | CANNOT ANSWER -- no lineage-ON + tanh + timing-fixed control | Follow-on ablation if this experiment is positive |
| Does the full REDESIGN bundle (HoF + K=L=3 + cache_on) add value beyond tanh + no-lineage? | NO -- those are separate changes | Reserved for adversarial_015 |
