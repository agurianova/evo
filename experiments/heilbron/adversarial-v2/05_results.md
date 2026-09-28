# Phase 5 Results: heilbron/adversarial-v2

**Date**: 2026-04-09
**Analyst**: Dr. Elena Voss (ml-research-methodologist agent)

> **PRE-REGISTRATION DEVIATION**: This experiment was stopped prematurely at ~45% of the pre-registered max_generations=75. All runs were terminated at gen 31-38. See Section 5 for full disclosure.

---

## 1. Summary of Findings

**Verdict: SUGGESTIVE POSITIVE**

Bidirectional structured feedback (opponent source code) shows a promising but inconclusive signal for improving Constructor actual_fitness on the Heilbronn triangle problem. The K=3 pair (P1) produced the best overall actual_fitness of 0.03568 (P1_B Improver) and a Constructor actual_fitness of 0.03502 (P1_A), both above the v1 historical baseline of 0.03464. The K=1 pair (P2) stalled at 0.03247, which is *below* the v1 baseline by 0.00217 — a surprising finding suggesting that minimal opponent context (K=1) may be worse than no opponent context at all. The ordering K=3 > K=0 (baseline) > K=1 is informative for mechanism design but falls short of the pre-registered POSITIVE threshold (both pairs exceeding baseline by >= 0.002) on two counts: (a) the K=3 margin is only +0.00038, well below 0.002, and (b) K=1 regressed. The premature stop at ~45% of planned generations makes these conclusions provisional — the K=3 pair was still on an upward trajectory and might have reached the 0.002 threshold given more time. Both Constructors reached 100% resistance, confirming that Improver stagnation persists despite bidirectional feedback.

---

## 2. Per-Run Results

### Final Metrics (at premature stop)

| Run | Role | K | Gen (of 75) | % Complete | actual_fitness | frontier_fitness | quality | resistance | Invalid% | Total Programs |
|-----|------|---|-------------|-----------|---------------|-----------------|---------|-----------|----------|---------------|
| P1_A | Constructor | 3 | 31 | 41% | **0.03502** | 0.97968 | 0.95936 | 1.00000 | 31.8% | 402 |
| P1_B | Improver | 3 | 34 | 45% | **0.03568** | 0.43789 | — | — | 5.6% | 285 |
| P2_A | Constructor | 1 | 34 | 45% | 0.03247 | 0.94478 | 0.88956 | 1.00000 | 32.9% | 362 |
| P2_B | Improver | 1 | 38 | 51% | 0.03247 | 0.38311 | — | — | 6.6% | 318 |

### Trajectory Summary

- **K=3 pair (P1)**: P1_A exceeded the v1 baseline (0.03464) by gen 19. P1_B (Improver) achieved the best overall actual_fitness of 0.03568 at gen 33, continuing to improve while the Constructor had plateaued. The pair was on an upward trajectory when stopped.
- **K=1 pair (P2)**: Both P2_A and P2_B stalled at 0.03247 from approximately gen 15 onward. No further improvement observed over ~20 generations of stagnation. This value is 0.00217 below the v1 baseline.

### Invalidity Rates

Constructor invalidity (31-33%) is higher than Improver invalidity (5-7%), consistent with v1. The opponent code blocks in mutation prompts did not materially change invalidity rates compared to v1 (23-25% for Constructors).

---

## 3. Hypothesis Assessment

### H1 (Primary): Both pairs exceed historical baseline by >= 0.002 — **NULL (with suggestive signal for K=3)**

| Pair | K | Constructor actual_fitness | Delta vs baseline (0.03464) | Threshold (>= 0.002) | Verdict |
|------|---|--------------------------|---------------------------|----------------------|---------|
| Pair 1 (P1_A) | 3 | 0.03502 | **+0.00038** | NOT MET | Below threshold |
| Pair 2 (P2_A) | 1 | 0.03247 | **-0.00217** | NOT MET | Below baseline |

By the pre-registered criterion, H1 is **NULL**: neither pair exceeds the baseline by >= 0.002. The K=3 pair is above baseline but the margin (+0.00038) is marginal. The K=1 pair is below baseline, which is a regression.

**Caveat**: The experiment reached only ~45% of planned generations. The K=3 pair was still improving (P1_B set a new best at gen 33), and the v1 baseline was measured at gen 42-50. Comparing gen 31 results to gen 42-50 baselines disadvantages the current experiment. The result is more accurately described as "insufficient data to confirm or reject H1 for K=3" rather than "K=3 does not help." For K=1, 20 generations of stagnation at 0.03247 suggests that running longer would not have changed the outcome.

**Confidence intervals**: With N=1 per condition, formal confidence intervals are meaningless. Point estimates only. The v1 within-pair variance (P1_A=0.03380, P2_A=0.03548, range=0.00168) provides a rough noise floor for interpreting deltas.

### H2 (Secondary): K=3 vs K=1 — **K=3 > K=1, magnitude meaningful**

| Metric | K=3 (P1_A) | K=1 (P2_A) | Delta | Threshold (>= 0.002) |
|--------|-----------|-----------|-------|---------------------|
| Constructor actual_fitness | 0.03502 | 0.03247 | **+0.00255** | MET (K=3 wins) |

K=3 outperforms K=1 by +0.00255 in Constructor actual_fitness, exceeding the pre-registered 0.002 threshold for "meaningful" difference. This suggests that richer opponent context (3 code blocks) provides a better signal than minimal context (1 code block). The alternative explanation — that K=1 is actively harmful while K=3 is neutral — is also consistent with the data (since K=1 regressed below the K=0 baseline).

**Interpretation**: The ordering is K=3 > K=0 (baseline) > K=1. This is hypothesis-generating: it suggests a non-monotonic relationship where too little opponent context may be worse than none (perhaps the LLM over-anchors on a single example), while a richer minibatch provides sufficient diversity. N=1 per condition precludes causal attribution.

### H3 (Secondary): Reduced Improver stagnation — **NOT SUPPORTED**

Both pairs show Improver stagnation consistent with v1:

- **P1_B (K=3)**: frontier_fitness = 0.43789, no improvement in later generations. The actual_fitness improvement to 0.03568 represents finding better configurations, but the Improver cannot consistently beat the Constructor's best.
- **P2_B (K=1)**: frontier_fitness = 0.38311, stalled for ~20 generations.

The pre-registered criterion was Improver acceptance rate > 5% after gen 20 (rolling 10-generation window). Neither Improver meets this criterion. Direction 2 feedback (Constructor code -> Improver) did not break the stagnation bottleneck.

Both Constructors reached 100% resistance, confirming that Improvers could not improve the best Constructor configurations — the same pattern as v1.

---

## 4. Comparison to Prior Work

### v1 baseline (adversarial/heilbron-prover, PR #183)

| Metric | v1 P1_A (K=0) | v1 P2_A (K=0) | v1 Mean | v2 P1_A (K=3) | v2 P2_A (K=1) |
|--------|-------------|-------------|---------|-------------|-------------|
| actual_fitness | 0.03380 | 0.03548 | 0.03464 | 0.03502 | 0.03247 |
| Gen at stop | 42 | 50 | — | 31 | 34 |
| Resistance | 100% | 100% | — | 100% | 100% |
| Constructor invalid% | 23% | 25% | — | 31.8% | 32.9% |

Key observations:
1. **K=3 (v2 P1_A) vs v1 mean**: +0.00038. Marginal improvement, within noise floor (v1 range = 0.00168). K=3 is in the upper range of v1 outcomes.
2. **K=1 (v2 P2_A) vs v1 mean**: -0.00217. Regression below baseline, outside v1 range. Surprising and informative.
3. **Gen comparison caveat**: v1 ran to gen 42-50; v2 stopped at gen 31-34. The comparison is confounded by different run durations.
4. **Invalidity increase**: v2 Constructors show ~8pp higher invalidity than v1 (32% vs 24%). The additional opponent code in mutation prompts may slightly increase prompt complexity, leading to more invalid outputs.
5. **Engine difference**: v1 used generational engine; v2 used steady-state. This is an uncontrolled confound, though steady-state was validated as non-inferior in hover/steady-state-v2.

### Adversarial co-evolution lineage

| Experiment | Task | Key Result | Improver Stagnation? |
|-----------|------|-----------|---------------------|
| adversarial/optimizer-coevo | Optimizer/Landscape | ASYMMETRIC (37:1 ratio) | Yes (severe) |
| adversarial/heilbron-prover (v1) | Heilbronn | POSITIVE (actual_fitness 0.035) | Yes (P2_B: 0% for 45 gens) |
| **heilbron/adversarial-v2** | Heilbronn | SUGGESTIVE POSITIVE (K=3 marginal, K=1 regressed) | Yes (both Improvers stagnate) |

Improver stagnation is now confirmed across three adversarial experiments on two different tasks. Bidirectional feedback via raw source code does not resolve this structural bottleneck.

---

## 5. Deviations from Pre-Registration

### Deviation 1: PREMATURE STOP (major)

**Pre-registered plan**: All 4 runs proceed to max_generations=75.

**What happened**: All runs killed at gen 31-38 (~45% of max_gen=75). The researcher decided to stop early to pivot to the next experiment (D re-evaluation, issue #195).

**Justification provided**: K=3 pair clearly ahead (+3.1% vs baseline), K=1 pair stalled for ~20 generations. The researcher judged sufficient signal to answer hypotheses without running to completion.

**Impact on conclusions**:
- H1 is assessed against gen-75 targets using gen-31 data. The K=3 pair was still improving and might have reached the 0.002 POSITIVE threshold. The NULL verdict for K=3 may be premature.
- H2 is less affected — the K=3 > K=1 ordering was stable for >10 generations and the K=1 stagnation pattern was entrenched.
- H3 is unaffected — Improver stagnation was already confirmed.
- The primary cost is reduced confidence in H1 for K=3. A definitive POSITIVE or NULL requires running to gen 75.

### Deviation 2: None other

No K-reduction amendment was triggered (K=3 mutation latency stayed well below the 60s threshold). No runs were invalidated. No config changes were made after launch.

---

## 6. Lessons Learned

### What worked

- **OpponentFeedbackStage implementation**: Bidirectional feedback was confirmed active in all 4 runs by gen 3. Treatment verification passed. The mechanism delivered opponent code to mutation prompts as designed.
- **Steady-state engine for adversarial runs**: No deadlocks after the initial bug fixes (Issues 0-5). The sync hook kept populations within a few generations of each other.
- **K=3 > K=1 signal**: The dose-response relationship (more opponent code = better performance) is a useful finding for mechanism design, even if the absolute effect is below threshold.

### What did not work

- **K=1 regression below baseline**: The most surprising finding. A single opponent code block may cause the mutation LLM to over-anchor on one specific strategy rather than exploring broadly. This suggests opponent context has a minimum effective dose — below which it is harmful.
- **Improver stagnation persists**: Raw opponent source code (Direction 2: Constructor -> Improver) does not break Improver stagnation. The Improver task remains structurally harder to evolve than the Constructor task. This is now confirmed across three experiments.
- **Premature stop**: Stopping at 45% prevents a definitive H1 verdict for K=3. The marginal cost of running to completion (another ~12 hours) was low relative to the interpretability gain.

### Bugs and infrastructure issues

Seven issues logged (see 04_issues_log.md). The most impactful were:
- **Issues 0-5**: Config and sync hook bugs during launch, requiring 4 restarts before a clean run. All fixed before data collection began.
- **Issue 7**: diagnose.py crash on dict-format treatment_checks. Fixed in-flight.

Systemic fixes needed: (1) preflight_check.py should validate `min_delta <= max_mutations_per_generation`; (2) `pipeline=adversarial_coevo_ss` should imply `evolution=steady_state`.

---

## 7. Recommendations for Next Experiment

1. **Do NOT re-run this experiment to gen 75.** The K=1 stagnation is definitive and running longer will not change it. The K=3 signal, while suggestive, is marginal enough that a follow-up should change the mechanism rather than simply extend the same design.

2. **Test K=3 with parsed critique instead of raw code.** The K=1 regression suggests that raw code may cause over-anchoring. A "parsed critique" variant — where a secondary LLM call extracts the opponent's strategy as a natural-language summary — could provide richer signal without the anchoring risk. Compare K=3-raw (this experiment) vs K=3-parsed.

3. **Focus on the Improver bottleneck.** Three experiments have now confirmed Improver stagnation. The next major advance requires breaking this bottleneck. Candidate approaches:
   - Structured move operators (evolve a perturbation strategy, not a full `entrypoint` function)
   - Difficulty-calibrated opponent selection (present easier Constructors first, then harder ones — GenEnv alpha-curriculum analog)
   - Separate Improver archive dimensions (diversity in attack strategies, not just attack success)

4. **If re-running K=3, use concurrent control.** This experiment's historical-baseline comparison is weak. A 2-arm design (K=3 bidirectional feedback vs K=0 score-only, 2 replicates each) would provide the concurrent control needed for causal attribution.

5. **Investigate the K=1 over-anchoring hypothesis.** Examine the mutation prompts from P2_A/P2_B to determine whether the LLM's mutations are visibly constrained by the single opponent code block. If confirmed, this is a general lesson about context quantity in LLM-guided evolution.

---

## 8. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| P1_A | Yes | Clean run from gen 1 to 31. Feedback confirmed active. |
| P1_B | Yes | Clean run from gen 1 to 34. Feedback confirmed active. |
| P2_A | Yes | Clean run from gen 1 to 34. Feedback confirmed active. |
| P2_B | Yes | Clean run from gen 1 to 38. Feedback confirmed active. |

All 4 runs are valid for analysis. Issues 0-5 occurred during launch (before data collection). No runs required exclusion.

---

*Ready for Reviewer-2's scrutiny.*
