# Results: hover/memory (PR #161)

**Date**: 2026-04-05
**Researcher**: KhrulkovV (analysis by Claude)
**Verdict**: **NULL / SUGGESTIVE**

---

## 1. Summary

Memory-augmented mutation does not reliably improve fitness on HoVer dynamic 7-step chains. The treatment effect is **NULL** at the group level: treatment mean val fitness (+0.61pp) and test coverage (+1.87pp mid-run) are driven entirely by a single outlier run (R4). With N=2 per condition, there is no statistical evidence that the memory system provides a reproducible advantage.

**Final val fitness (gen 26)**:

| Condition | Runs | Mean Val Fitness |
|-----------|------|------------------|
| Control | R1 (82.44%), R2 (81.00%) | 81.72% |
| Treatment | R3 (81.56%), R4 (83.11%) | 82.33% |
| **Delta** | | **+0.61pp** |

**Final test eval (gen 26 programs, 5-repeat, 300-sample test set)**:

| Condition | Runs | Mean Test Coverage |
|-----------|------|--------------------|
| Control | R1 (59.27%), R2 (60.27%) | 59.77% |
| Treatment | R3 (59.80%), R4 (62.67%) | 61.23% |
| **Delta** | | **+1.47pp** |

**Verdict**: SUGGESTIVE (0 < delta < +1.5pp for val, +1.47pp for test). The directional signal is present but entirely driven by R4 (treatment), which is the only run that achieved a fitness breakthrough. R3 (treatment) performed indistinguishably from controls. At N=2, this cannot be attributed to the treatment with confidence.

---

## 2. Final Metrics

| Run | Condition | Best Val Fitness | Test Coverage (final) | Total Programs | Archive Size |
|-----|-----------|------------------|-----------------------|----------------|-------------|
| R1 | Control | 82.44% | 59.27% ± 1.16% | 293 | 20 |
| R2 | Control | 81.00% | 60.27% ± 1.09% | 297 | 15 |
| R3 | Treatment | 81.56% | 59.80% ± 1.15% | 290 | 18 |
| R4 | Treatment | 83.11% | 62.67% ± 2.33% | 283 | 11 |

**Baseline / GEPA reference**: GEPA = 52.33% test coverage; hover/7step-dynamic treatment = 85.10% val, 64.20% test.

### Fitness Trajectories

| Run | Gen of Last Improvement | Improvement | Notes |
|-----|-------------------------|-------------|-------|
| R1 | Gen 22 | 81.8% → 82.4% (+0.7pp) | Late-stage breakthrough after 12-gen plateau |
| R2 | Gen 0 | 81.0% (seed, never improved) | 297 programs, 0% acceptance rate |
| R3 | Gen 9 | 81.4% → 81.6% (+0.1pp) | Minor improvement, then plateau |
| R4 | Gen 9 | 80.2% → 83.1% (+2.9pp) | Largest single-gen jump in experiment |

---

## 3. Hypothesis Test

**H₀**: Memory-augmented mutation does not improve best val soft fitness (delta <= 0).
**H₁**: Memory-augmented mutation improves best val soft fitness (delta > 0).
**Primary metric**: Val soft fitness (best frontier) at gen 25.
**Statistical test**: One-sided Welch's t-test, α = 0.10.

### Val Fitness

```
Control:   [82.44, 81.00], mean=81.72, SD=1.02
Treatment: [81.56, 83.11], mean=82.33, SD=1.10

t = (82.33 - 81.72) / sqrt(1.02²/2 + 1.10²/2)
  = 0.61 / sqrt(0.52 + 0.60)
  = 0.61 / 1.06
  = 0.58

df ≈ 2 (Welch-Satterthwaite)
p (one-sided) ≈ 0.31
```

**Result**: t(2) = 0.58, p = 0.31. **H₀ not rejected** at α = 0.10.

### Test Coverage (final, gen 26 programs)

```
Control:   [59.27, 60.27], mean=59.77, SD=0.71
Treatment: [59.80, 62.67], mean=61.23, SD=2.03

t = (61.23 - 59.77) / sqrt(0.71²/2 + 2.03²/2)
  = 1.47 / sqrt(0.25 + 2.06)
  = 1.47 / 1.52
  = 0.96

df ≈ 1.2 (Welch-Satterthwaite)
p (one-sided) ≈ 0.24
```

**Result**: t(1.2) = 0.96, p ≈ 0.24. **H₀ not rejected** at α = 0.10. High within-treatment variance (R3 ≈ controls, R4 is outlier).

---

## 4. Effect Size

- Val fitness delta: +0.61pp (SUGGESTIVE, below +1.5pp threshold for POSITIVE)
- Test coverage delta: +1.47pp (final; SUGGESTIVE range, driven by R4)
- Cohen's d (val): 0.58 (medium effect, but underpowered)

---

## 5. Secondary Observations

### R4 (Treatment): The Outlier

R4 achieved the largest single-generation improvement (+2.9pp at gen 9) and the highest final fitness (83.1% val, 62.67% test). However:
- R3 (also treatment) performed at 81.6% — indistinguishable from controls
- R4's archive was smallest (11 cells vs. 15-20), suggesting early convergence to a strong solution
- Without lineage tracing to specific memory cards, the causal role of memory cannot be established

### R2 (Control): Permanent Plateau

R2 never improved beyond its gen-2 seed (81.0%). Its best program had 35 offspring, none surpassing the parent. This extreme plateau pattern is consistent with prior HoVer experiments.

### R1 (Control): Late-Stage Breakthrough

R1 broke a 12-generation plateau at gen 22 (81.3% → 82.4%), demonstrating stochastic improvements are possible even very late. This weakens arguments that R4's early breakthrough is uniquely attributable to memory.

### Convergence Speed

No convergence speed advantage for treatment. All runs reached ~80% by gen 1 (strong seed). Memory did not accelerate discovery of improvements.

---

## 6. Manipulation Check

Treatment runs (R3, R4) had memory cards correctly injected:
- `MemoryContextStage` logged card selection for every mutation in R3/R4
- `memory_selected_idea_ids` metadata present on treatment programs
- Control runs (R1, R2) used NullMemoryProvider (no memory activity)

The treatment variable was active and correctly applied (verified after Bug #4 fix).

---

## 7. Amendment Impact Assessment

| # | Deviation | Impact on Validity |
|---|-----------|-------------------|
| 1 | Two restarts (Bugs #4, #5: memory not wired, wrong engine) | None — Redis flushed, restarted from scratch |
| 2 | `pipeline=structural_metrics` vs pre-reg `standard` | Required for 3D BC; design doc had correct value |
| 3 | `stage_timeout=3000` vs pre-reg `6000` | No impact — no valid programs hit 3000s |
| 4 | Gen 26 reported (not 25) | SteadyState overshoot by 1; full budget consumed |
| 5 | Mid-run test eval at gen ~14, not final gen 26 | Final test eval pending (R1's 82.4% not in mid-run eval) |

---

## 8. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| R1 | Yes | Completed gen 26, all metrics available |
| R2 | Yes | Completed gen 26, never improved (valid data point) |
| R3 | Yes | Completed gen 26, all metrics available |
| R4 | Yes | Completed gen 26, all metrics available |

---

## 9. Comparison to Baseline

| Experiment | Val Fitness (best) | Test Coverage |
|------------|-------------------|---------------|
| hover/baseline (PR #90) | ~54% | 51.65% |
| hover/7step-dynamic control (PR #144) | 80.05% | 55.87% |
| hover/7step-dynamic treatment (PR #144) | 85.10% | 64.20% |
| hover/no-deep-retrieval (PR #150) | — | ~same as deep |
| **hover/memory control (this)** | **81.72%** | **59.77%** |
| **hover/memory treatment (this)** | **82.33%** | **61.23%** |

---

## 10. Issues Log Summary

| Bug | Severity | Impact | Systemic Fix Needed? |
|-----|----------|--------|---------------------|
| #1: MemoryCard.aliases type mismatch | Medium | Fixed pre-launch | No |
| #2: _card_type() crashes on Pydantic | Medium | Fixed pre-launch | No |
| #3: Lint errors from merge | Low | Fixed pre-launch | No |
| #4: memory_provider not wired | **Critical** | Invalidated first launch | **Yes** — auto-wire in pipeline configs |
| #5: Wrong engine config | **Critical** | Invalidated second launch | **Yes** — template should prompt for engine |

---

## 11. Lessons Learned

**What worked**:
- Memory system is mechanically functional — cards are selected, injected, and consumed by the mutation LLM
- SteadyStateEvolutionEngine + 3D MAP-Elites topology is a robust baseline
- PostRunHook lifecycle for IdeaTracker works cleanly

**What didn't work**:
- Memory cards from Phase A (M0 run, single run) did not produce a statistically significant fitness improvement
- N=2 per condition is insufficient to detect effects below +3.0pp
- The memory system adds complexity without demonstrated benefit on this task

**Bugs / infrastructure issues**:
- Bug #4 was critical — memory_provider silently defaulted to NullMemoryProvider in all pipeline configs, invalidating the first Phase B launch
- Bug #5 was critical — experiment.yaml didn't include engine/algorithm overrides, causing wrong engine type

---

## 12. Next Steps

1. **Qualitative lineage analysis of R4**: Trace R4's best program (83.1%) back through its ancestry to determine if memory cards contributed to the breakthrough mutation
2. **Powered replication**: If lineage analysis shows causal contribution, run at N=4+ per condition (MDE ~2.2pp at 80% power)
3. **Memory card quality**: Test with higher-quality cards from the best-performing topology runs (hover/7step-dynamic treatment at 85.1%)
4. **Different task**: Test on HotpotQA or a continuous-metric task where small improvements are more detectable

---

## 13. Paper / Report Notes

- Memory-augmented evolution is a novel contribution but needs stronger evidence before publication
- R4's 83.1% val / 62.67% test is notable — exceeds GEPA by 10.3pp on test, which is worth investigating regardless of the group-level null result
- The memory system architecture (card-based episodic memory, PostRunHook lifecycle, DAG integration) is publishable as a system contribution even if the fitness effect is null

---

## Appendix A: Final Test Evaluation

**Completed**: 2026-04-05 ~06:12 MSK. Gen 26 best-by-val programs, 300-sample test set, 5 repeats each.

| Run | Condition | Mean Coverage | Std | Individual Repeats |
|-----|-----------|--------------|-----|-------------------|
| R1 | Control | 59.27% | 1.16% | 60.00, 60.00, 59.00, 57.33, 60.00 |
| R2 | Control | 60.27% | 1.09% | 60.67, 60.67, 58.33, 60.67, 61.00 |
| R3 | Treatment | 59.80% | 1.15% | 58.67, 58.67, 60.33, 60.00, 61.33 |
| R4 | Treatment | 62.67% | 2.33% | 63.00, 61.67, 62.33, 66.33, 60.00 |

**Group means**: Control 59.77%, Treatment 61.23%, Delta **+1.47pp**.
