## Experiment: heilbron/d-smoothing-minimal

**Status**: Pre-registered
**Branch**: `exp/heilbron/d-smoothing-minimal`
**Pre-registration commit**: *(added after merge)*
**Idea**: `adversarial_019` in `experiments/IDEAS.yaml`
**Predecessor**: `heilbron/adversarial-repro-v2` (NULL, PR #216, mu_G=0.03315)
**Related hotfix**: PR #219 (G-side resistance smoothing, commit `2de8267e`)

---

### Hypothesis

**H0**: mu_G ≤ 0.03449. D-side fitness smoothing alone does not lift G above baseline parity.
**H1**: mu_G > 0.03449. Replacing hard-floor D fitness with tanh-smoothed scoring breaks the D-collapse pathology and enables G improvement above the pre-adversarial baseline.

**Primary metric**: `actual_fitness` (best-ever, grand mean across 4 G runs) at final generation.
**Decision threshold**: POSITIVE ≥ 0.03550 · SUGGESTIVE ≥ 0.03449 · NULL 0.03200-0.03449 · REGRESSIVE < 0.03200.

---

### Treatment (single IV)

Replace `problems/heilbron_repro_v1/pop_b/evaluate.py:97-99`:

```python
# Before (hard-floor, current main)
raw_delta = post_q - pre_q
delta = max(raw_delta, 0.0)
score = min(delta / Q_MAX, 1.0)

# After (tanh smoothing, this experiment)
raw_delta = post_q - pre_q
score = 0.5 * (np.tanh(raw_delta / Q_MAX) + 1.0)
delta = raw_delta  # stored signed for diagnostics
```

Also: exception-path `score` changes `0.0 → 0.5` (neutral); `per_opp_metrics["delta"]` stores signed `raw_delta`; `metrics.yaml` `mean_improvement_raw.lower_bound` updates `0.0 → -0.0365`.

All other v2 wiring (SBF-Lineage, SOFTMAX-G / TOP_K-D, `refresh_passes=2`, `refresh_order=generation_bucketed`, `archive_reeval` asymmetric, `drift_cap=100000`, `stage_timeout=900`) is **pinned identical to v2**.

---

### Design

8 runs, 4 G / 4 D, factorial: {Arm A: composition feedback, Arm C: gradient-in-prompt feedback} × {pair 1, pair 2}.

| Run   | Role | Arm | DB | Feedback            | Sampling |
|-------|------|-----|----|---------------------|----------|
| A1_G  | G    | A   | 1  | composition         | softmax  |
| A1_D  | D    | A   | 2  | composition         | top_k    |
| A2_G  | G    | A   | 3  | composition         | softmax  |
| A2_D  | D    | A   | 4  | composition         | top_k    |
| C1_G  | G    | C   | 5  | gradient_in_prompt  | softmax  |
| C1_D  | D    | C   | 6  | gradient_in_prompt  | top_k    |
| C2_G  | G    | C   | 7  | gradient_in_prompt  | softmax  |
| C2_D  | D    | C   | 8  | gradient_in_prompt  | top_k    |

`max_generations: 200` · `max_mutations_per_generation: 8` · `num_parents: 1` · `stage_timeout: 900s (15 min)` · `dag_timeout: 3600s`.

**Docs**: [01_design.md](01_design.md) · [02_review.md](02_review.md) · [03_plan.md](03_plan.md) · [literature_brief.md](literature_brief.md) · [codebase_map.md](codebase_map.md) · [dataset_snapshot.json](dataset_snapshot.json)

---

### Mechanistic Predictions (pre-registered)

At generation 20 in D populations (A1_D, A2_D, C1_D, C2_D):

| Prediction                                           | Threshold       |
|------------------------------------------------------|-----------------|
| Fraction of D programs with fitness in [0.1, 0.9]    | ≥ 50 %          |
| Median D fitness                                     | in [0.3, 0.6]   |
| Fraction at fitness < 0.001 (degeneracy floor)       | < 20 %          |
| Variance of D fitness distribution                   | ≥ 0.01          |

Failure to hit these by gen 20 = treatment not mechanistically active; see Section 2.2a of `01_design.md`.

**Smoke test** (3 gens on DB 11): < 5 % of D programs at fitness < 0.001 AND median in [0.3, 0.7].

---

### Volkov Review

2 rounds; **APPROVED** after Round 2. See `02_review.md`:
- C1 (Critical): metrics.yaml prompt text was a hidden IV → **frozen verbatim identical to v2**.
- M1 (Major): pre-registered mechanistic claim was definitional, not falsifiable → **replaced** with quantitative Section 2.2a (distribution-shape predictions above).
- m1–m6 (Minor): all addressed; see Revision Log in `01_design.md`.

---

### Checkpoint Results

| Gen | Date (UTC) | mu_G (4 G runs) | D degeneracy fraction | Notes |
|-----|-----------|------------------|------------------------|-------|
| *(filled as experiment progresses)* | | | | |

---

### Final Result

*(pending)*

**Verdict**: POSITIVE / SUGGESTIVE / NULL / REGRESSIVE
**mu_G**: XX.XX (grand mean across A1_G, A2_G, C1_G, C2_G best-ever `actual_fitness`)

**Full analysis**: [05_results.md](05_results.md)
