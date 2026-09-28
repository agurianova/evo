# Phase 2 Review: heilbron/adversarial-v2

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary agent)
**Date**: 2026-04-08
**Review round**: R3 (re-review of final design --- K=1 vs K=3 bidirectional, 4 runs, no control)
**Design reviewed**: `experiments/heilbron/adversarial-v2/01_design.md` (Final)

---

## Summary of Design

Dr. Voss proposes a 4-run exploratory experiment comparing K=1 vs K=3 bidirectional opponent feedback on the Heilbronn adversarial co-evolution task. All 4 runs receive bidirectional structured feedback; the sole independent variable is K (number of opponent code blocks injected per direction). There is no concurrent control group. The implicit baseline is `adversarial/heilbron-prover` (historical, score-only feedback). The researcher has explicitly chosen exploration over control given a hard constraint of 4 runs.

This is a further revision from R2 (8-run design with treatment/control). The 8-run design was sound but exceeded the researcher's capacity. The 4-run design sacrifices concurrent control for within-mechanism exploration. I evaluate it on its own terms.

---

## Resolution of R2 Concerns

### R2 C1: Improver population variance --- SUPERSEDED

The 8-run treatment-vs-control design required comparing Treatment Improvers against Control Improvers. The 4-run design has no control, so cross-arm Improver variance is no longer a confound. All Improvers receive feedback. **No remaining concern.**

### R2 M1: Pipeline YAML does not exist yet --- CARRIED (MINOR)

Still true. `adversarial_coevo_feedback.yaml` and `OpponentFeedbackStage` do not exist. The design specifies the DAG topology (Section 6.3), data flow edges, and population-aware behavior with sufficient precision for implementation. **Carried as Minor.**

### R2 m5: Generation parity across arms --- SUPERSEDED

No treatment/control arms. Parity checks are now within-pair only (P1_A/P1_B and P2_A/P2_B), which is correct. The `treatment_checks` YAML (Section 13) includes `generation_parity` for these groups with `max_drift: 5`. **No remaining concern.**

### R2 m6: Opponent selection criteria asymmetry --- CARRIED (MINOR)

Still relevant. Direction 1 ranks by `delta_fitness`, Direction 2 ranks by `resistance`. The design specifies this (Section 3, Parameters table; Section 6.3, "population-aware"). Implementation must map Pop A -> `delta_fitness`, Pop B -> `resistance`. **Carried as Minor.**

### R2 m7: `gen_gate` field in treatment_checks YAML --- CARRIED (MINOR)

Still relevant. The `gen_gate` field is not part of the current `treatment_checks` schema. The prose assigns gen-3 and gen-5 gates to `run_watchdog.py`, but the YAML block mixes preflight and watchdog checks. **Carried as Minor.**

---

## New Concerns for 4-Run Design

### Major 1: Warm-start seed asymmetry is an uncontrolled confound for H2

Section 6.2 states: "Pair 1 (K=3) and Pair 2 (K=1) use **different** warm-start seeds (from different heilbron-prover pairs)." Pair 1 Constructor starts at 0.03380 (P1_A) and Pair 2 Constructor starts at 0.03548 (P2_A). The delta is 0.00168 --- nearly as large as the H1 success threshold of 0.002.

Section 9 proposes "adjusting for different warm-start starting points by computing improvement-over-seed." This accounts for starting fitness but not for **remaining improvability**. P2_A at 0.03548 may sit closer to a local optimum with less room to improve. Improvement-over-seed cannot correct for this.

The H2 verdict criteria in Section 9 --- "If K=3 > K=1 by >= 0.002, richer context helps" --- read as if a causal conclusion will be drawn. With different warm-start seeds and N=1 per K condition, H2 cannot support causal claims under any analysis.

**Required action**: (a) Add an explicit statement to Section 8 or Section 9 that H2 is **hypothesis-generating only** and cannot support causal conclusions, even with improvement-over-seed adjustment. (b) Soften the H2 verdict language in Section 9 from "richer context helps" / "less is more" to "consistent with richer context helping" / "consistent with less being more."

### Major 2: Stopping rule for actual_fitness regression is under-specified

Section 11 states: "actual_fitness < 0.030 at gen 20 (warm-start regression --- something is broken)." Two issues:

(a) **Which metric exactly?** "actual_fitness" could refer to frontier best, mean of valid programs, or the latest evaluated program. Specify that this is `valid_frontier_fitness` (the frontier best in Redis).

(b) **No stagnation detection.** The stopping rule fires only on regression below 0.030, but does not detect complete stagnation. If the frontier best remains at the warm-start value for 20 generations (zero archive turnover for Constructors), the run is wasting compute. The existing rule tolerates this silently.

**Required action**: (a) Specify that "actual_fitness" in the stopping rule refers to frontier best (`valid_frontier_fitness` in Redis). (b) Add a stagnation alert: if Constructor frontier `actual_fitness` shows zero improvement for 15 consecutive generations after gen 10, the watchdog posts a WARNING to the PR. This is an alert, not a termination --- the researcher decides whether to intervene.

### Minor 1: Pre-authorized amendment (K=3 -> K=2) lacks reporting protocol

Section 3 pre-authorizes dropping K from 3 to 2 if mutation latency exceeds 60 seconds mean. This is sensible. However, the design does not specify: (a) whether "60s mean" is computed over a fixed window or cumulatively, (b) whether the amendment is logged in `04_issues_log.md` with the exact generation number, or (c) whether results reporting separates the K=3 and K=2 phases.

**Required action**: Specify (1) the latency measurement window (Section 7 mentions "10-generation window" --- confirm this applies to the amendment trigger), (2) the amendment must be logged in `04_issues_log.md` with the generation at which K changed, and (3) `05_results.md` must report any K change and separate analysis by phase if it fires.

### Minor 2: `opponent_redis_db` not in preflight treatment checks

The run design table (Section 6) specifies opponent DB wiring: P1_A reads from DB 2, P1_B from DB 1, P2_A from DB 4, P2_B from DB 3. A misconfigured `opponent_redis_db` would silently cause a Constructor to evolve against the wrong Improver --- the run proceeds, but the co-evolutionary pairing is broken.

Section 13's `treatment_checks` verify pipeline builder, K value, feedback presence, and generation parity. They do **not** verify `opponent_redis_db` mapping. The `generation_parity` check would detect extreme drift but not a cross-wired opponent DB producing plausible dynamics.

**Required action**: Add a `config_check` entry to the `treatment_checks` YAML that verifies `opponent_redis_db` for each run matches the run design table.

### Minor 3: Baseline mean arithmetic

Section 6.1 reports "Mean Constructor actual_fitness: 0.03462" from P1_A (0.03380) and P2_A (0.03548). The arithmetic mean is (0.03380 + 0.03548) / 2 = 0.03464, not 0.03462. The discrepancy is 0.00002 --- immaterial for the 0.002 threshold, but the value should be correct.

**Required action**: Verify and correct the baseline mean to 0.03464, or confirm the source values.

---

## Design Structure Verification

| Check | Status |
|---|---|
| 4 runs total (hard constraint) | PASS |
| K is the sole IV between pairs | PASS: Section 3, all other variables in Section 5 |
| Bidirectional feedback active in ALL runs (not an IV) | PASS: Section 5, row 1 |
| Opponent wiring strictly within-pair | PASS: P1_A <-> P1_B (DBs 1-2), P2_A <-> P2_B (DBs 3-4) |
| Pipeline identical across all 4 runs | PASS: `adversarial_coevo_feedback` for all |
| `evolution=steady_state` controlled | PASS: Section 5 |
| Warm-start seed difference acknowledged | PASS: Section 6.2, Section 10 |
| Historical baseline correctly identified | PASS: heilbron-prover mean 0.03462 (pending arithmetic correction) |
| No hidden IVs in `include_in_prompts` | PASS: Section 5, "Prompt parity check" confirms identical metrics.yaml |
| Cold-start window documented and symmetric | PASS: Section 3, affects all 4 runs equally |

---

## Hypothesis and Falsifiability

| Check | Status |
|---|---|
| H1 clearly stated with numeric thresholds | PASS: >= 0.002 POSITIVE, >= 0.005 STRONG POSITIVE |
| H1 NULL criterion pre-specified | PASS: neither pair exceeds by >= 0.002 |
| H1 NEGATIVE criterion pre-specified | PASS: either pair regresses below warm-start seed |
| H2 stated as genuinely uncertain (direction unknown) | PASS |
| H2 measured as improvement-over-seed, not raw | PASS (Section 9) |
| H3 has explicit acceptance rate threshold | PASS: > 5% in rolling 10-gen window |
| Follow-up experiments specified for all verdict paths | PASS: Section 14 covers POSITIVE, NULL, NEGATIVE, and per-hypothesis combinations |

---

## Confound Analysis

| Check | Status |
|---|---|
| No concurrent control acknowledged | PASS: Section 1, Section 6.1, Section 10 (rated HIGH risk) |
| Steady-state engine confound acknowledged | PASS: Sections 6.1, 10, with hover/steady-state-v2 cross-validation |
| Warm-start seed difference acknowledged | PASS: Sections 6.2, 10 (rated MEDIUM risk) |
| Prompt length as alternative explanation for H2 | PASS: Section 10, "Residual confound" subsection |
| LLM server load controlled | PASS: 4 runs, same proxy, within capacity |
| `include_in_prompts` parity | PASS: Section 5 |
| Cold-start parity | PASS: Section 3 |
| Ceiling effect risk | PASS: Section 14, item 5 (heilbron-prover P1_A still improving at gen 42) |

---

## Treatment Verification Assessment

The treatment verification plan (Section 13) is the strongest element of this design:

1. **Preflight**: Config dumps verify pipeline builder `_target_`, K values.
2. **Gen 3 watchdog**: Verifies feedback headers present in all 4 runs (both directions).
3. **Gen 5 watchdog**: Counts opponent blocks (K=3 -> 3 blocks, K=1 -> 1 block).
4. **Generation parity**: Within-pair drift capped at 5 generations.
5. **`treatment_checks` YAML**: Machine-verifiable, 6 specific checks.

This is thorough. The missing `opponent_redis_db` check (Minor 2) is the only gap.

---

## Stopping Rules Assessment

Section 11 specifies per-run early termination (3 criteria), run invalidation (4 criteria), and correctly states that no experiment-level early stop exists without a control arm. The criteria are specific and numeric.

The under-specification of the regression threshold metric (Major 2a) and the absence of a stagnation alert (Major 2b) are the gaps.

---

## Items I Do NOT Flag

- **Lack of concurrent control**: Researcher's explicit decision, documented with tradeoff analysis. Accepted.
- **N=1 per K condition**: Best allocation given 4-run constraint. Accepted.
- **Statistical tests**: Section 9 correctly uses effect-magnitude comparison, not formal tests. Appropriate at N=1.
- **Raw code vs parsed critique**: Reasonable choice with clear follow-up path (Section 14).
- **Steady-state engine for all runs**: Consistent across conditions, validated elsewhere.

---

## Verdict: APPROVED

**APPROVED**

The 4-run design is internally consistent. The sole IV (K) is cleanly isolated. Bidirectional feedback is uniformly applied. Confounds are honestly acknowledged, with the historical baseline weakness rated HIGH risk and the warm-start seed asymmetry rated MEDIUM --- both correct assessments. Treatment verification is comprehensive (5-layer defense in depth). The follow-up experiment table covers all verdict paths. The design will produce interpretable results for H1 (both pairs vs baseline) and H3 (Improver stagnation), and hypothesis-generating observations for H2 (K comparison).

Both Major concerns are resolvable by text edits to the existing design. Neither requires structural redesign.

**Conditions for approval** (all resolvable by the researcher without redesign):

1. **Major 1**: Soften H2 verdict language in Section 9 to "consistent with" rather than causal claims. Add explicit statement that H2 is hypothesis-generating only. *(Text edit in Sections 8-9.)*
2. **Major 2**: Specify frontier best as the stopping rule metric. Add stagnation alert (15 gens with zero Constructor frontier improvement -> watchdog WARNING). *(Text edit in Section 11.)*
3. **Minor 1**: Specify amendment logging protocol for K=3->K=2 (measurement window, issues log entry, results separation). *(Text edit in Section 3 or 7.)*
4. **Minor 2**: Add `opponent_redis_db` config check to `treatment_checks` YAML. *(One YAML block addition in Section 13.)*
5. **Minor 3**: Correct baseline mean to 0.03464 or verify source values. *(Arithmetic fix.)*

Carried from R2 (no action needed before launch):
- Pipeline YAML sketch omitted (sufficient specification elsewhere)
- Opponent selection criterion mapping (implementation-time verification)
- `gen_gate` field schema (watchdog implementation detail)

*The science demands nothing less.*
