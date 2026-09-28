# Results: HoVer Baseline -- Cold-Start Retrieval Coverage via n=4 Replication

**Date**: 2026-03-20
**Input**: Final metrics from H1-H4 (5-repeat test eval), `01_design.md`, `03_plan.md`

---

## 1. Final Metrics

| Run | Best val fitness | Val plateau gen | Test coverage (5-repeat mean +/- SD) | 5-repeat scores |
|-----|-----------------|-----------------|--------------------------------------|-----------------|
| H1 | 50.0% | gen 3 | 51.20% +/- 2.01% | 49.0, 53.0, 53.3, 49.3, 51.3 |
| H2 | 55.0% | gen 5 | 52.47% +/- 0.69% | 51.3, 53.0, 52.7, 52.3, 53.0 |
| H3 | 54.0% | gen 5 | 51.93% +/- 1.66% | 50.3, 53.7, 50.0, 53.0, 52.7 |
| H4 | 50.0% | gen 4 | 51.00% +/- 0.78% | 50.3, 50.7, 50.3, 52.0, 51.7 |

**Grand mean test coverage**: 51.65% (inter-run SD: 0.63pp)
**Grand mean within-run SD**: 1.29pp (range: 0.69-2.01pp)

**GEPA benchmark**: 52.33% test coverage (point estimate, no variance reported)

### Val-test gap

| Run | Best val | Test mean | Gap |
|-----|----------|-----------|-----|
| H1 | 50.0% | 51.20% | +1.2pp |
| H2 | 55.0% | 52.47% | -2.5pp |
| H3 | 54.0% | 51.93% | -2.1pp |
| H4 | 50.0% | 51.00% | +1.0pp |

Runs with higher val coverage (H2, H3) show a negative val-test gap of 2-2.5pp,
suggesting some degree of overfitting to val samples. Runs that plateaued at lower
val (H1, H4) show a slight positive gap, consistent with the test set being
marginally easier for those programs.

---

## 2. Hypothesis Test

**H0**: GigaEvo cold-start mean test retrieval coverage across n=4 runs is at most 52.33%
(the GEPA benchmark).

**H1**: GigaEvo cold-start mean test retrieval coverage exceeds 52.33%.

**Primary metric**: Test retrieval coverage (discrete: all 3 gold docs = 1, else 0),
300-sample held-out test set, 5-repeat mean per run.

**Statistical test**: One-sample t-test (one-sided, greater), df=3.

**Result**:
- t(3) = -2.008
- p(one-sided, greater) = 0.931
- 95% CI: [50.57%, 52.73%]
- **H0 not rejected** at alpha = 0.05

The cold-start mean (51.65%) is **below** GEPA (52.33%), so the one-sided test
cannot reject H0. There is no evidence that GigaEvo cold-start exceeds GEPA on HoVer.

---

## 3. Effect Size

**Delta vs GEPA**: -0.68pp (51.65% - 52.33%)

**Cohen's d**: -1.004 (large effect in the *wrong* direction)

| Threshold | Verdict |
|-----------|---------|
| >= +5.0pp above GEPA | STRONG POSITIVE |
| [+2.0pp, +5.0pp) | POSITIVE |
| (0pp, +2.0pp) | SUGGESTIVE |
| <= 0pp | **NULL** <-- this experiment |

**Verdict: NULL**. GigaEvo cold-start does not exceed GEPA on HoVer retrieval
coverage. The cold-start mean is 0.68pp below GEPA, well within the noise floor.

---

## 4. Secondary Observations

### Convergence dynamics

All 4 runs plateaued early:
- H1, H4 plateaued at 50.0% val by gen 3-4 (no improvement over 20+ generations)
- H2, H3 reached 54-55% val by gen 5, then plateaued

This is similar to HotpotQA cold-start (plateau by gen 15-20), but occurs much earlier
on HoVer, suggesting the discrete fitness landscape has very few productive mutation
targets.

### Within-run test variance

The 5-repeat protocol revealed substantial LLM stochasticity:
- Within-run SD ranges from 0.69pp (H2) to 2.01pp (H1)
- Mean within-run SD: 1.29pp
- This is ~2x the inter-run SD (0.63pp), meaning single-shot test evals are unreliable

This confirms that 5-repeat test evaluation was necessary. A single-shot test would
have produced misleading results (e.g., H2 single-shot was 50.0% but 5-repeat mean
was 52.47%).

### Host effects

| Host | Runs | Mean test |
|------|------|-----------|
| Host A (10.226.17.25) | H1 (51.20%), H2 (52.47%) | 51.84% |
| Host B (10.225.185.235) | H3 (51.93%), H4 (51.00%) | 51.47% |

Host effect: 0.37pp (host A > host B). Negligible relative to noise.

### Potential binding constraints identified

1. **Absent failure feedback**: The mutation LLM sees only aggregate fitness numbers,
   not which gold docs were missed or at which hop. This limits targeted improvement.
2. **Discrete fitness**: The 0/1 scoring discards partial credit. Programs finding 2/3
   gold docs score identically to programs finding 0/3.
3. **BM25 first-hop ceiling**: If the initial BM25 query rarely retrieves any gold docs,
   no amount of prompt optimization for later hops can help.

These hypotheses are tested in the follow-up experiment (PR #92, feedback_softfit).

---

## 5. Amendment Impact Assessment

| Amendment | Impact on validity | Assessment |
|-----------|-------------------|-----------|
| 5-repeat test protocol (added mid-experiment) | Positive | Captures within-run variance that single-shot eval missed. Applied uniformly to all 4 runs. |

---

## 6. Run Validity

| Run | Valid for analysis? | Reason if excluded |
|-----|--------------------|--------------------|
| H1 | Yes | Plateaued early but completed normally |
| H2 | Yes | Best performing run |
| H3 | Yes | Second best performing run |
| H4 | Yes | Plateaued early but completed normally |

All 4 runs are valid. No invalidation criteria triggered.

---

## 7. Lessons Learned

**What worked**:
- n=4 replication design: revealed inter-run variability (50-55% val range)
- 5-repeat test protocol: essential for reliable per-run estimates
- Watchdog with hourly PR updates: effective for overnight monitoring

**What didn't work**:
- Cold-start converges too quickly on HoVer (gen 3-5 plateau vs gen 15-20 on HotpotQA)
- Discrete fitness provides very coarse signal for this 3-hop retrieval task
- No failure feedback means mutation LLM cannot target specific retrieval weaknesses

**Infrastructure issues**:
- H4 test eval required endpoint switch (10.225.185.235:8000 was slow; moved to 10.226.17.25:8001)
- NFS slowness (7-15s import times) does not affect accuracy but slows test suite

---

## 8. Next Steps

1. **Follow-up experiment running**: PR #92 (hover/feedback_softfit) is a 2x2 factorial
   testing failure feedback (Cell B) and soft fitness (Cell C) as interventions.
   Launched 2026-03-20, currently at gen 14-16/25.

2. **GEPA comparison limitation**: GEPA's 52.33% is a point estimate with no reported
   variance. A fair comparison would require running GEPA's approach with the same
   5-repeat protocol, but we do not have access to their inference code.

3. **BM25 ceiling analysis**: If feedback_softfit shows NULL results, the next
   investigation should examine whether the BM25 first-hop is the binding constraint
   (i.e., whether gold docs are even retrievable given the claim as query).

---

## 9. Paper / Report Notes

**Key result**: GigaEvo cold-start achieves 51.65% +/- 0.63pp test retrieval coverage
on HoVer, at parity with GEPA (52.33%). The 95% CI [50.57%, 52.73%] brackets GEPA,
indicating no meaningful difference.

**Narrative**: Cold-start evolution on HoVer converges within 3-5 generations to a
plateau, unlike the 15-20 generation convergence on HotpotQA. The discrete fitness
landscape and absent failure feedback are hypothesized binding constraints, tested
in the follow-up experiment.
