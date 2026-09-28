# Adversarial Review: adversarial/optimizer-coevo

**Reviewer**: Prof. Andrei Volkov
**Date**: 2026-04-06
**Design version**: 1

## Overall Assessment

This is a well-structured PoC design for a genuinely novel extension of GigaEvo -- the first adversarial co-evolution experiment in a program that has run 34 single-population experiments. Dr. Voss is appropriately scoped: toy domain, fast evaluations, infrastructure validation as the primary goal. The confound analysis is thorough and honest. The decision tree in Appendix B is exemplary -- every outcome maps to a concrete next step.

The design has two major concerns and five minor issues. None are fatal to a PoC of this nature, but the major concerns must be addressed or explicitly acknowledged before launch.

---

## Section-by-Section Review

### Section 1: Research Question

Well-motivated. The progression from static fitness landscapes to co-evolving adversaries is a natural research direction, and choosing a tractable toy domain before scaling to NLP is correct methodology. The distinction between infrastructure validation (primary) and arms race detection (secondary) is clearly drawn.

### Section 2: Hypotheses

**H1 (arms race)**: Falsifiable and directional. The operationalization -- both populations must show positive fitness improvement from gen 1 to final gen -- is clean.

**H2 (zero-sum coupling)**: Described as a secondary hypothesis but has no formal test or even a pre-committed threshold. The design says "Pearson correlation of per-generation frontier fitness deltas" with expected sign negative, "reported descriptively -- no formal test at N=2." This is acceptable for an exploratory hypothesis at this sample size.

**Effect-size thresholds**: The table is clear and pre-committed. However, the 0.05 and 0.15 thresholds are stated in absolute fitness units (not percentage points of the [0,1] fitness scale). Since both fitness metrics are on [0,1], these correspond to 5pp and 15pp. This is fine but should be stated explicitly to avoid ambiguity in the results document. *(Minor.)*

### Section 3: Independent Variable(s)

Single-condition experiment with no control. Appendix D provides four cogent reasons for omitting a control. I accept all four. For a PoC infrastructure validation, the question "does it work at all?" precedes "does it work better than X?"

### Section 4: Dependent Variables

The DV list is comprehensive and well-organized. The separation between primary (fitness improvement), infrastructure validation (n_opponents, gen parity), and qualitative (program inspection) is appropriate.

**Concern**: `n_opponents` is returned by both `evaluate.py` files but is NOT declared in either `metrics.yaml`. I inspected both files: `pop_a/metrics.yaml` and `pop_b/metrics.yaml` each declare only `fitness` and `is_valid`. The `n_opponents` value will be stored in program metadata but will NOT appear as a tracked metric in Redis history, will NOT be displayed by `status.py --experiment`, and will NOT be available in `trajectory.py` or `comparison.py` output. The design document lists `n_opponents per generation` as an infrastructure validation metric (Section 4, Section 8 Test 4), but the current `metrics.yaml` configuration makes it invisible to all standard monitoring tools.

**Required action**: Either add `n_opponents` to both `metrics.yaml` files (with `include_in_prompts: false` to avoid biasing mutation), or document how `n_opponents` will be monitored during the run (e.g., ad-hoc Redis queries on program metadata, custom analysis script). Without this, the infrastructure validation check "n_opponents > 0 at gen >= 1" has no systematic way to be evaluated during the run. *(Major.)*

### Section 5: Controlled Variables

Thorough. All four processes share identical overrides, mutation LLM, archive configuration, and timeouts. I verified the Hydra config against `config/pipeline/adversarial_coevo.yaml` -- the wiring is correct: `n_opponents: 5`, `per_opponent_timeout: 10.0`, `stage_timeout: ${stage_timeout}`, `dag_timeout: ${dag_timeout}`, `cache_ttl: 30.0`.

One observation: the design states `MAP-Elites archive: Single island (fitness_island), 150 bins`. The `RedisOpponentArchiveProvider` reads from `island_fitness_island:archive`. If the archive key prefix differs from `island_fitness_island` in the actual GigaEvo archive implementation, the opponent provider will read an empty archive forever and fall back to fallback opponents indefinitely. Appendix A item 8 ("Gen-0 diagnostic: n_opponents should equal 3 at gen 0") is the correct check for this failure mode, so it is already covered by the verification plan.

### Section 6: Run Design Table

Clean. The DB assignments (1-4) are non-overlapping. The opponent wiring is correct: P1-A reads from DB 2 (P1-B), P1-B reads from DB 1 (P1-A), and similarly for Pair 2. No cross-pair contamination is possible by construction.

**Observation**: The memory file notes "HoVer experiments used DBs 4-15" and the design says "adversarial experiments reclaim DBs 1-4." If any HoVer data remains in DB 4, the pre-launch flush must include DB 4. The design does call for flushing DBs 1-4, so this is covered. However, DB 4 overlap with prior experiments is worth noting in the issues log if anything unexpected appears during gen 0. *(Informational, no action required.)*

### Section 7: Sample Size Justification

This is the section I scrutinized most carefully, and it is where the design is most vulnerable.

**N=2 pairs is the bare minimum.** The design acknowledges this. The justification -- LLM contention at N=3+ with 4 mutation servers -- is pragmatic but should be validated: with toy domain evaluations taking seconds and LLM mutations dominating wall time, 6 concurrent processes would mean ~1.5 processes per server. This is likely sustainable since mutation calls are serialized within each process, but I accept the conservative choice for a first-ever adversarial run.

**The paired sign test claim (p=0.0625 with alpha=0.10)**: This requires careful examination.

The design states: "For each pair, compute (fitness_final - fitness_gen1) for both populations. Under H0 (no improvement), the probability of positive improvement in both populations in both pairs = (0.5)^4 = 0.0625."

This calculation treats the 4 observations (2 pops x 2 pairs) as independent. The two populations WITHIN a pair are not independent -- they are adversarially coupled. Pop A's fitness is measured against Pop B's landscape archive; Pop B's fitness is measured against Pop A's optimizer archive. If Pop B happens to produce weak landscapes, Pop A gets high fitness trivially. The two populations within a pair share a causal link that violates the independence assumption.

The 4 observations are: (Pop A Pair 1, Pop B Pair 1, Pop A Pair 2, Pop B Pair 2). Under H0, we need P(improvement > 0) for each. The sign test assumes independence. Within-pair dependence means the effective degrees of freedom are less than 4. The true p-value under H0 is somewhere between 0.0625 (if fully independent) and 0.25 (if within-pair results are perfectly correlated, giving effectively 2 independent observations with p = 0.5^2).

**Required action**: Acknowledge the within-pair dependence in the sign test. The test should be framed as: "If we consider each PAIR as one observation (arms race = both populations improve), and we have 2 pairs, the sign test p-value is 0.5^2 = 0.25 (not significant at any conventional alpha). The (0.5)^4 = 0.0625 calculation assumes independence between populations within a pair, which is violated by the adversarial coupling." This does not change the experimental plan -- the analysis is primarily descriptive anyway -- but the current framing overstates the statistical evidence available from N=2 pairs. *(Minor -- since the design already labels this test as "secondary" and the primary analysis is descriptive, this is a precision issue, not a validity issue.)*

### Section 8: Statistical Tests

**Test 1 (arms race detection)**: Descriptive, pre-committed decision table. Clean.

**Test 2 (paired sign test)**: See concern above. The p=0.0625 claim assumes independence that is violated.

**Test 3 (cross-correlation)**: Appropriately labeled exploratory. No issues.

**Test 4 (infrastructure validation)**: Pass/fail criteria are concrete and verifiable. The generation parity check (<= 2 gen gap) is well-calibrated for the MainRunSyncHook timeout behavior I verified in the source code.

### Section 9: Known Confounds and Mitigations

Eight confounds identified, all with mitigations. This is a strong confound analysis.

**Confound 5 (opponent cache staleness)**: The design says "The lockstep mechanism ensures that opponent programs are at most 1 generation behind." This is not quite right. The sync hook ensures that the opponent HAS ADVANCED by one generation before this population starts its next generation. But within a generation, the opponent may produce new programs that are not yet in the cache due to the 30s TTL. More precisely: the opponent archive may contain programs from the opponent's current generation that were not present when the cache was last refreshed. This is a minor precision issue -- the practical impact is negligible. *(Minor.)*

**Confound 7 (program execution isolation)**: The design says "Broken programs are excluded from the average." I verified this in `pop_a/evaluate.py`: if a landscape tuple is malformed, the `continue` statement skips it; if the optimizer crashes, `scores.append(0.0)`. So broken landscapes ARE excluded (not counted in the denominator), but broken optimizer evaluations score 0.0 (counted in the denominator). This is asymmetric.

In `pop_b/evaluate.py`: if an opponent optimizer is not callable, `scores.append(1.0)` (max deceptiveness). If it crashes, `scores.append(1.0)`. So broken optimizers give the landscape maximum fitness, while in `pop_a/evaluate.py`, broken landscapes are silently skipped.

This asymmetry means:
- Pop B benefits from broken opponent optimizers (high fitness = "you're deceptive if they can't even run").
- Pop A is partially shielded from broken opponent landscapes (they're excluded from the average, reducing n_opponents).

This could bias the arms race if one population produces more broken programs than the other. However, for a PoC where the primary question is "does any arms race occur at all?" this asymmetry is acceptable. *(Minor -- document it in the limitations section of 05_results.md.)*

**Missing confound: Fitness incomparability across generations.** The design acknowledges this in Risk 5 (Section 12) but does NOT list it as a confound in Section 9. This is arguably the single most important methodological limitation of the entire design. If Pop A's fitness at gen 15 is 0.7, we cannot compare it to Pop A's fitness at gen 5 (also 0.7) because the opponent landscape has changed. A fitness trajectory that appears flat may actually represent continuous improvement against increasingly deceptive opponents. Conversely, a rising trajectory may simply mean opponents are getting weaker.

The design's primary metric -- `fitness_final - fitness_gen1` -- is directly affected by this. If Pop B evolves much better landscapes by gen 20, Pop A's final fitness may be LOWER than gen 1 even if Pop A's optimizer has genuinely improved. The design would classify this as "Pop A stagnates" when in reality Pop A may have improved substantially against a harder challenge.

**Required action**: Move this from an "open question" in Section 12 to a named confound in Section 9, with explicit mitigation: the qualitative inspection of top programs at gen 1, 10, 20 (Section 4, already planned) is the primary way to assess genuine capability improvement independent of the fitness metric's non-stationarity. Pre-commit to reporting this qualitative analysis alongside the quantitative trajectory in 05_results.md. *(Major.)*

### Section 10: Stop Criteria

Appropriate. The early termination criteria are concrete and pre-committed. The stagnation diagnostic correctly identifies asymmetric improvement as an interesting finding rather than a termination trigger. The run invalidation criteria are well-defined.

One note: criterion "Sync hook blocks for > 60 minutes" (Section 10) is inconsistent with the sync hook timeout of 7200s (Section 5). The stop criterion says halt at 60 min; the sync hook itself only logs a warning at 7200s (2 hours). Should the human operator halt the process manually after 60 min, or does the hook auto-timeout at 2h? The answer is: the design wants the operator to investigate at 60 min, but the hook auto-proceeds at 2h. This is fine but should be explicit. *(Minor.)*

### Section 11: Compute Budget

Realistic. Toy domain with pure Python evaluation and LLM-dominated mutation cost. The 3-5h estimate for 2 pairs in parallel seems right given 8 mutations/gen, ~2-8 min/mutation, 20 gens.

### Section 12: Open Questions / Risks

Five priority risks, all well-analyzed. The decision table at the end is the strongest part of the entire design -- every outcome pattern maps to a specific interpretation and next step.

### Appendix A: Code Verification

Eight verification items, all concrete. One additional item should be added: verify that `n_opponents` is actually observable at runtime (see Section 4 concern above).

### Appendix B: Decision Tree

Exemplary. Every branch terminates in a clear verdict and next step.

### Appendix C: Treatment Verification Checks

Appropriate for a single-condition experiment. The checks verify correct wiring of the adversarial infrastructure.

### Appendix D: Why No Control Condition?

Persuasive. All four arguments are valid. The pre-commitment to a controlled follow-up if the PoC succeeds (point 4) is the key.

---

## Severity Summary

| # | Severity | Section | Issue |
|---|----------|---------|-------|
| 1 | **Major** | 4 (DVs) | `n_opponents` not in `metrics.yaml` -- infrastructure validation metric is invisible to all monitoring tools. Add to metrics.yaml (with `include_in_prompts: false`) or document alternative monitoring approach. |
| 2 | **Major** | 9 (Confounds) | Fitness incomparability across generations is listed as an "open question" (Section 12, Risk 5) but not as a named confound. This directly affects the primary metric. Promote to confound with explicit mitigation (qualitative program inspection at gen 1/10/20). |
| 3 | Minor | 7 (Sample size) | Paired sign test p=0.0625 assumes independence between Pop A and Pop B within a pair, which is violated by adversarial coupling. True p-value is between 0.0625 and 0.25. Acknowledge the dependence. |
| 4 | Minor | 9 (Confound 7) | Asymmetric treatment of broken opponents: Pop A skips broken landscapes (excluded from average), Pop B scores broken optimizers as 1.0 (counted). Document in limitations. |
| 5 | Minor | 2 (Hypotheses) | Effect-size thresholds (0.05, 0.15) should explicitly state units are on the [0,1] fitness scale to avoid ambiguity with percentage points. |
| 6 | Minor | 10 (Stop criteria) | 60-min halt criterion vs 7200s sync hook timeout: clarify that 60-min is an operator-initiated investigation threshold, not an automatic termination. |
| 7 | Minor | 9 (Confound 5) | "Opponent programs are at most 1 generation behind" is imprecise. The sync hook ensures opponent has completed prior generation, but within-generation cache staleness (30s TTL) means evaluation may use a partially-updated archive. Precision fix only. |

---

## Verdict: APPROVED

Both major concerns are addressable without redesign:

1. **Add `n_opponents` to both `metrics.yaml` files** with `include_in_prompts: false`, `higher_is_better: true`, `is_primary: false`, `lower_bound: 0.0`. This is a 5-minute fix.

2. **Promote "fitness incomparability across generations"** from Section 12 Risk 5 to Section 9 as Confound #9, with pre-committed mitigation: qualitative program inspection at gen 1/10/20 as supplementary evidence alongside the fitness trajectory.

The minor concerns (sign test independence, broken-opponent asymmetry, terminology precision) should be fixed for completeness but do not block launch. This is a well-designed PoC for a first-ever adversarial co-evolution experiment. The toy domain is correctly chosen, the infrastructure validation checks are concrete, and the decision tree accounts for all plausible outcomes.

Fix the two major items before launch.

*The science demands nothing less.*
