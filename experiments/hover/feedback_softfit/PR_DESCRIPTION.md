## exp: hover/feedback_softfit -- Disentangling Feedback and Soft Fitness

**Status**: Running (gen 0/25)

**Tracking issue**: #89
**Design**: `experiments/hover/feedback_softfit/01_design.md`
**Review**: `experiments/hover/feedback_softfit/02_review.md` (APPROVED R2)
**Pre-registration**: `experiments/hover/feedback_softfit/03_plan.md`

### Hypothesis

Two potential binding constraints on HoVer baseline performance (~51.65%, updated with H4):
1. **Absent failure feedback** -- mutation LLM sees only fitness numbers, not which gold docs were missed or at which hop
2. **Discrete fitness** -- 0/1 scoring discards partial credit (2/3 gold docs = 0)

2x2 factorial design (3 active cells, cell D deferred):

| Cell | Feedback | Fitness | Runs | Status |
|------|----------|---------|------|--------|
| A (Control) | none | discrete | H1-H4 (PR #90) | Complete |
| B | **structured** | discrete | F1, F2 | Running |
| C | none | **soft** | F3, F4 | Running |
| D | structured | soft | (deferred) | -- |

### Run Design

| Run | Cell | DB | Pipeline | Chain LLM | Mutation LLM |
|-----|------|----|----------|-----------|-------------|
| F1 | B | 9 | hover_feedback | 10.226.17.25:8001 | 10.226.72.211 |
| F2 | B | 10 | hover_feedback | 10.225.185.235:8001 | 10.226.15.38 |
| F3 | C | 11 | standard | 10.226.17.25:8000 | 10.226.185.47 |
| F4 | C | 12 | standard | 10.225.185.235:8000 | 10.225.51.251 |

### Primary Metric

Discrete test retrieval coverage (5-repeat mean), 300-sample held-out test set.

### Success Criteria

| delta vs baseline | Verdict |
|-------------------|---------|
| >= +5.0pp | STRONG POSITIVE |
| [+2.0pp, +5.0pp) | POSITIVE |
| (0pp, +2.0pp) | SUGGESTIVE |
| <= 0pp | NULL |

### Checkpoints

| Gen | Date | F1 | F2 | F3 | F4 | Notes |
|-----|------|----|----|----|----|----|
| | | | | | | |

### Final Result

TBD

### Archives

TBD
