# Pre-Registration: K=5 Compute Budget Asymmetry with Loose G/D Coupling

**Date**: 2026-04-16
**Protocol version**: 1.0
**Pre-registration commit**: `7c4a8efe`
**GitHub PR**: TBD (branch: `exp/heilbron/k5-budget-loose`)
**Design doc**: `experiments/heilbron/k5-budget-loose/01_design.md`
**Review doc**: `experiments/heilbron/k5-budget-loose/02_review.md` (verdict: APPROVED)
**Evaluation script**: N/A (no test split for Heilbronn)

---

## Hypothesis

**H0**: K=5 compute budget asymmetry with loose coupling does not change max(G,D) actual_fitness relative to within-experiment control (K=1 symmetric, sync_min_delta=8).

**H1**: K=5 compute budget asymmetry with loose coupling produces max(G,D) actual_fitness meaningfully different from control.

**Primary metric**: max(G, D) actual_fitness per pair, averaged across 3 replicates per arm.

**Significance threshold**: alpha = 0.10 (Welch's t-test, one-sided). Verdict relies on pre-registered effect-size thresholds, not p-values.

### Effect-size thresholds

| max(G,D) actual_fitness (arm mean) | Interpretation |
|---|---|
| >= 0.03649 | STRONG POSITIVE |
| >= 0.03549 | POSITIVE |
| 0.03349 to 0.03549 | NULL |
| < 0.03349 | NEGATIVE |

### Stagnation assessment

Improver acceptance rate > 5% (rolling 10-gen, after gen 20) in >= 2/3 treatment replicates = STAGNATION BROKEN.

---

## Run Design Table

### Treatment arm: K=5 budget + loose coupling (3 pairs)

| Run | Label | DB | Role | max_mutations | sync_min_delta |
|-----|-------|----|------|---------------|----------------|
| 1 | T1_G | 1 | Constructor | 8 | 8 |
| 2 | T1_D | 2 | Improver | 40 | 1 |
| 3 | T2_G | 3 | Constructor | 8 | 8 |
| 4 | T2_D | 4 | Improver | 40 | 1 |
| 5 | T3_G | 5 | Constructor | 8 | 8 |
| 6 | T3_D | 6 | Improver | 40 | 1 |

### Control arm: K=1 symmetric (3 pairs)

| Run | Label | DB | Role | max_mutations | sync_min_delta |
|-----|-------|----|------|---------------|----------------|
| 7 | C1_G | 7 | Constructor | 8 | 8 |
| 8 | C1_D | 8 | Improver | 8 | 8 |
| 9 | C2_G | 9 | Constructor | 8 | 8 |
| 10 | C2_D | 10 | Improver | 8 | 8 |
| 11 | C3_G | 11 | Constructor | 8 | 8 |
| 12 | C3_D | 12 | Improver | 8 | 8 |

All runs: `pipeline=adversarial_asymmetric`, `evolution=steady_state`, `feedback_mode=composition`, `model_name=Qwen3-235B-A22B-Thinking-2507`.

---

## Controlled Variables

| Field | Value |
|-------|-------|
| pipeline | adversarial_asymmetric |
| evolution | steady_state |
| max_generations | 50 |
| max_elites_per_generation | 8 |
| mutation_mode | rewrite |
| num_parents | 1 |
| stage_timeout | 2400 |
| dag_timeout | 2400 |
| significant_change | 0.01 |
| inner_iterations | 1 |
| n_opponents | 1 |
| source_prompt_k | 1 |
| archive_reeval | false |
| feedback_mode | composition |
| d_sees_g_source | true |
| d_archive_persistent | true |

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- LLM sampling temperature in mutation LLM (Qwen3-235B)
- `random.sample` in mutation selection and archive operations
- Non-deterministic GPU floating point across mutation server hardware

**Global seed**: N/A (steady-state engine does not support deterministic seeding)

Cross-experiment comparisons use effect-size thresholds from `01_design.md` rather than exact trajectory matching.

---

## Dataset Checksums

Cryptographic anchor: `dataset_snapshot.json` (47 files, git commit 8aed7da3).

Heilbronn problem: point placement in unit square, no external dataset files. The "dataset" is the geometric evaluation function in `problems/heilbron_adversarial/validate.py`. Checksums cover all problem directory files.

---

## Success Criteria

| Outcome | Criterion |
|---------|-----------|
| STRONG POSITIVE | Treatment mean max(G,D) >= 0.03649 |
| POSITIVE | Treatment mean max(G,D) >= 0.03549 |
| STAGNATION BROKEN | Improver acceptance rate > 5% in >= 2/3 treatment pairs after gen 20 |

---

## Monitoring Plan

`max_generations`: 50

- Gen 5 (~10%): smoke check — all 12 PIDs alive, Redis keys growing, treatment D shows min_delta=1 in logs, D/G program ratio ~5:1 for treatment pairs
- Gen 10 (~20%): first checkpoint — verify D/G ratio, extract best-per-pair, check stagnation metrics
- Gen 25 (~50%): midpoint — futility check (all 3 treatment pairs < 0.030 → stop treatment arm)
- Gen 50 (100%): final — extract all metrics, run analysis

Early termination: all 3 treatment pairs max(G,D) < 0.030 at gen 25.

---

## Decision Matrix

| Treatment | Control validates? | Verdict | Next |
|-----------|-------------------|---------|------|
| STRONG POSITIVE | Yes | K=5 + loose reproduces v1 | Ablation: K=5+tight vs K=1+loose |
| POSITIVE | Yes | Budget helps, below v1 | Dose-response: K=3/5/10 |
| NULL | Yes | Compute budget insufficient | Structured Improver operators |
| NEGATIVE | Yes | Treatment hurts | Close compute budget direction |
| Any | No | Confounded | Relativize to within-experiment |

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| (to be filled at launch) | | | |

Watchdog PID: TBD
Launch commit: TBD

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|
| (to be filled during experiment) | | |

---

## Amendments

### Amendment #1 — 2026-04-16: Drop control arm, add gradient-in-prompt treatment arm

**Change**: Replace 6 control runs (K=1 symmetric, `feedback_mode=composition`) with 4 treatment runs using `feedback_mode=gradient_in_prompt`. Total runs: 12 → 8.

**New run structure**:

| Arm | Pair | Label | DB | feedback_mode | Role | max_mut | sync_min_delta |
|-----|------|-------|----|--------------:|-----:|--------:|---------------:|
| A (composition)   | 1 | A1_G | 1 | composition         | G | 8  | 8 |
| A (composition)   | 1 | A1_D | 2 | composition         | D | 40 | 1 |
| A (composition)   | 2 | A2_G | 3 | composition         | G | 8  | 8 |
| A (composition)   | 2 | A2_D | 4 | composition         | D | 40 | 1 |
| B (gradient)      | 1 | B1_G | 5 | gradient_in_prompt  | G | 8  | 8 |
| B (gradient)      | 1 | B1_D | 6 | gradient_in_prompt  | D | 40 | 1 |
| B (gradient)      | 2 | B2_G | 7 | gradient_in_prompt  | G | 8  | 8 |
| B (gradient)      | 2 | B2_D | 8 | gradient_in_prompt  | D | 40 | 1 |

**Rationale**:

1. **Within-experiment control was redundant**. The K=1 symmetric condition has already been run with high N across prior experiments on the same evaluation function: `heilbron/baseline-repro` (N=4, mean=0.03449, SD=0.00212) and the symmetric arms of `heilbron/asymmetric-iterations-v2`. Using the historical baseline as the reference eliminates ~50% of compute without weakening the comparison — `baseline.reference=heilbron/baseline-repro` is already wired into experiment.yaml.

2. **Gradient-in-prompt is a higher-information-gain comparison**. PATTERNS.md records feedback-mode direction as CLOSED at K=1 (composition ≈ gradient-in-prompt, delta ≈ 0.00066). The amendment converts the freed compute into a direct test of whether the K=5+loose regime re-opens that gap. This is a strictly stronger test: if K=5+loose helps both feedback modes equally, the mechanism is budget+coupling (not feedback-specific); if one dominates under K=5+loose, feedback mode interacts with budget.

3. **No confound introduced**. Composition and gradient-in-prompt arms differ only in `feedback_mode` (and the `post_step_hook` that composition requires on G runs). All other Hydra config is identical across arms. Single-IV-per-comparison discipline is preserved.

**Stopping rule updated**: Futility threshold now applies to all 4 pairs (2 composition + 2 gradient-in-prompt), not "all 3 treatment pairs". Threshold unchanged (max(G,D) < 0.030 at gen 25).

**Power**: N=2 pairs per feedback mode. Volkov's N≥2-per-cell rule is satisfied. With historical baseline as the reference, the primary comparison (arm mean vs 0.03449) has full statistical power; the secondary (composition vs gradient-in-prompt under K=5+loose) is exploratory, reported with effect sizes + 95% CIs rather than p-values.

**Files touched**:
- `experiment.yaml`: `runs[]` rewritten (12 → 8); `stopping_rule` wording updated for 4 pairs; watchdog `comparison` caption updated
- `launch.sh`: regenerated from new `runs[]`
- `03_plan.md`: this amendment

### Amendment #2 — 2026-04-16: Convert to 2x2 factorial (feedback_mode x K budget), N=1 per cell

**Change**: Split the 8 treatment runs into a 2x2 factorial design: feedback_mode (composition vs gradient-in-prompt) x K budget (K=3 vs K=5). N=1 pair per cell (2 runs per cell: one G, one D). Labels renamed from A1/A2/B1/B2 (all K=5) to A3/A5/B3/B5 where the number denotes K.

**New run structure**:

| Arm | Cell | Label | DB | feedback_mode | K | Role | max_mut | sync_min_delta |
|-----|------|-------|----|--------------:|--:|-----:|--------:|---------------:|
| A (composition)        | A3 | A3_G | 1 | composition        | 3 | G | 8  | 8 |
| A (composition)        | A3 | A3_D | 2 | composition        | 3 | D | 24 | 1 |
| A (composition)        | A5 | A5_G | 3 | composition        | 5 | G | 8  | 8 |
| A (composition)        | A5 | A5_D | 4 | composition        | 5 | D | 40 | 1 |
| B (gradient-in-prompt) | B3 | B3_G | 5 | gradient_in_prompt | 3 | G | 8  | 8 |
| B (gradient-in-prompt) | B3 | B3_D | 6 | gradient_in_prompt | 3 | D | 24 | 1 |
| B (gradient-in-prompt) | B5 | B5_G | 7 | gradient_in_prompt | 5 | G | 8  | 8 |
| B (gradient-in-prompt) | B5 | B5_D | 8 | gradient_in_prompt | 5 | D | 40 | 1 |

**Rationale**:

1. **Dose-response on K in the same experiment**. Running both K=3 and K=5 under each feedback mode lets a single 50-gen experiment answer both "does loose coupling help?" and "does the K budget matter?" without needing a follow-up ablation. K=3 keeps D/G throughput ratio at 3:1 (vs 5:1 for K=5), hedging the risk that K=5 is excessive.

2. **2x2 factorial reveals interaction effects**. The comparison A3 vs A5 measures the marginal effect of K at fixed feedback_mode=composition; B3 vs B5 measures the same under gradient_in_prompt. A3 vs B3 and A5 vs B5 measure feedback_mode at fixed K. The four-way interaction (is the K effect feedback-mode-dependent?) is the primary scientific question.

3. **Explicit override of N>=2-per-cell rule**. Researcher explicitly waived the Volkov N>=2 requirement to get 2x coverage of the K dimension within the same compute budget. Consequence: cell-level estimates have no within-cell replicate, so statistical verdicts will rely on effect-size magnitudes and the historical baseline reference (N=4, mean=0.03449), not within-experiment t-tests. This is acknowledged as weaker power in exchange for broader design coverage.

**Stopping rule updated**: Futility threshold now applies to all 4 cells (A3, A5, B3, B5), not "all 4 pairs". Threshold unchanged (max(G,D) < 0.030 at gen 25).

**Files touched**:
- `experiment.yaml`: `runs[]` labels renamed (A1->A3, A2->A5, B1->B3, B2->B5); conditions rewritten; `max_mutations_per_generation=24` in A3_D and B3_D (K=3), `=40` retained in A5_D and B5_D (K=5); stopping_rule wording updated; watchdog captions updated for factorial structure
- `launch.sh`: regenerated from new `runs[]`
- `03_plan.md`: this amendment

### Amendment #3 — 2026-04-16: Align Improver prompt with `d_sees_g_source=true` treatment (gen-0 restart)

**Change**: Edit `problems/heilbron_adversarial/pop_b/task_description.txt` lines 17-21 to acknowledge the live source-code injection treatment. No experiment.yaml or code changes; D's prompt only.

**What was wrong**: The static D prompt (committed pre-launch) instructed:
- "Focus on GENERAL improvement strategies rather than exploiting specific point arrangements"
- "Constructor programs you face change EVERY generation"

Both statements conflict with the actually-deployed treatment:
1. `d_sees_g_source=true` (controlled variable, see line 84 above) injects the SAME Constructor's source code D is being scored against this turn — explicitly inviting white-box exploitation. The prompt told D to ignore exactly this signal.
2. `FetchOpponentIdsStage` has `cache_handler=NO_CACHE` and `OpponentArchiveProvider` re-samples per call — opponents change every MUTATION, not every generation. The frequency was understated by ~K-fold.

**What changed**: Replaced the 5-line "RAPIDLY CHANGING CONTEXT" block with a 16-line block titled "RAPIDLY CHANGING OPPONENTS + WHITE-BOX ACCESS" that:
- States the per-mutation re-sampling cadence correctly
- Acknowledges the source-code injection block explicitly
- Adds a true anchoring statement: the source D sees has already survived competitive selection in G's archive (so naive improvements won't score)
- Instructs D to reason from source about the underlying assumption, then craft an improvement general enough to also help against the next opponent

No method names (e.g. SLSQP, basin-hopping) are prescribed — kept neutral to avoid biasing the search space.

G's prompt (`problems/heilbron_adversarial/pop_a/task_description.txt`) is intentionally NOT touched. Telling G "your code is read by D" risks obfuscation strategies that distort the deep-basin-search objective. Asymmetric awareness (D sees source, G does not know D sees) matches the design.

**Scientific impact**: Negligible (<2% of 50-gen budget discarded). At amendment time the runs were:

| Cell | G gen | G best (norm) | G progs | D gen | D best (norm) | D progs |
|------|------:|--------------:|--------:|------:|--------------:|--------:|
| A3   | 1     | 0.7929        | 25      | 1     | (none)        | 41      |
| A5   | 0     | 0.7573        | 18      | 0     | 0.3833        | 42      |
| B3   | 1     | 0.9057        | 25      | 1     | 0.3497        | 38      |
| B5   | 0     | 0.6469        | 15      | 0     | 0.3407        | 42      |

4/8 runs reached gen 1; 4/8 still at gen 0. All pre-reg measurement anchors (gen-25 futility check, gen-50 final) are far outside the discarded warmup window. The pre-registration record is intact: hypothesis, conditions, controlled variables, decision matrix, dataset checksums all unchanged. Only the static D prompt — which was inconsistent with the controlled variable `d_sees_g_source=true` — is being aligned to its declared treatment.

**Procedure**: Standard `/experiment-restart` with confirmation:
1. Cancel anomaly_detector_cron (0b6d8303) and checkpoint_cron (cf317067)
2. Kill all 8 run PIDs + watchdog (PID 1923500)
3. Flush DBs 1-8 (no archive worth preserving at gen 0)
4. Reset status to `implemented`
5. `/experiment-launch heilbron/k5-budget-loose` — fresh PIDs, new crons

**Files touched**:
- `problems/heilbron_adversarial/pop_b/task_description.txt`: replaced lines 17-21 (RAPIDLY CHANGING CONTEXT block) with the 16-line WHITE-BOX ACCESS block described above
- `04_issues_log.md`: this amendment recorded as a restart event
- `03_plan.md`: this amendment

**Files NOT touched**:
- `experiment.yaml`: no changes to controlled variables or run config
- `01_design.md`, `02_review.md`: no changes — the design always assumed `d_sees_g_source=true`; the prompt was the lagging artifact
