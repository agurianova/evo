# Reviewer-2 Report: D-Side Fitness Smoothing (Minimal REDESIGN Isolation)

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Date**: 2026-04-24
**Design document**: `experiments/heilbron/d-smoothing-minimal/01_design.md`
**Round**: 1

---

## Summary of Design

This experiment isolates the D-side fitness smoothing component of the REDESIGN bundle (adversarial_019 in IDEAS.yaml). The single IV is the replacement of the hard-floor D fitness formula (`max(raw_delta, 0.0) / Q_MAX`) with a continuous tanh form (`0.5 * (tanh(raw_delta / Q_MAX) + 1.0)`) in `pop_b/evaluate.py`. The comparison is against v2's historical data (mu_G=0.03315, N=4). This is the first adversarial experiment under dual-smoothed fitness, since G-side smoothing (PR #219) landed on main the same day. Well-motivated by confirmed root cause (D hard-floor producing 60-90% point mass at fitness=0.0 across 11 experiments).

---

## Summary Assessment

This is a well-motivated, carefully scoped experiment that targets the confirmed root cause of D-population stagnation across 11 prior experiments. The design document is thorough, the confound analysis is unusually transparent, and the choice to isolate D-smoothing from the full REDESIGN bundle is scientifically sound. Elena has clearly learned from the v1 and v2 cycles.

That said, I have identified one critical concern, one major concern, and several minor issues that must be addressed before this design can proceed.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|----------------|
| C1 | metrics.yaml description change is a hidden IV (prompt content confound) | **Critical** | Freeze metrics.yaml text identical to v2, or add as explicit confound |
| M1 | Pre-registered mechanistic claim is definitionally true (tautology) | **Major** | Relabel as treatment verification check |
| m1 | Exception-path score 0.0->0.5 weakens crash penalty incentive | Minor | Document behavioral consequence; monitor exception rate |
| m2 | `delta` field semantics change understated (signed vs clamped) | Minor | Fix `lower_bound: 0.0` on `mean_improvement_raw` in metrics.yaml |
| m3 | NULL band definition makes REGRESSIVE verdict unreachable | Minor | Acknowledge in text |
| m4 | 28h wall-clock cap adequacy undocumented | Minor | State expected gen depth; confirm partial runs acceptable |
| m5 | Smoke test threshold too generous (< 50% at gen 3) | Minor | Tighten to < 5% or check median in [0.3, 0.7] |
| m6 | Power analysis uses inconsistent "pp" notation | Minor | Use raw units or relative terms |

---

## Critical Concerns

### C1. Metrics.yaml Description Is a Hidden IV (Confound with Mutation Prompt Content)

**Severity: CRITICAL**

The design (Section 3, row 5) specifies that D's `metrics.yaml` fitness description must change from `"...Worsening counts as 0, not negative."` to describe tanh semantics. I have verified the current `problems/heilbron_repro_v1/pop_b/metrics.yaml` line 3: `include_in_prompts: true` for the `fitness` metric.

This is not a cosmetic edit. The `fitness` description is injected verbatim into the LLM mutation prompt for every D program. Changing the text of this description changes the mutation prompt -- the instructions the LLM receives when generating D candidates. Under v2, the LLM was told "Worsening counts as 0, not negative." Under this experiment, the LLM will be told something about tanh semantics.

This means the IV is not "D fitness function form" alone. The IV is "D fitness function form + D mutation prompt content." These two changes co-vary perfectly with the treatment and both plausibly affect the DV (D program quality, which in turn affects G's mu_G). This is a textbook confound -- one I have flagged repeatedly in this experiment series (see PATTERNS.md: `include_in_prompts` as hidden IV, status ACTIVE).

The design lists this change in Section 3 (row 5 of the IV table) but does not acknowledge it as a confound in Section 9. It is presented as a simple documentation update, when in fact it is a change to the LLM's instruction set.

**Required fix**: Either (a) do NOT change the metrics.yaml description -- keep the v2 wording exactly, accepting that it will be technically inaccurate but prompt-identical to v2; or (b) add this as Confound #8 in Section 9 with an honest assessment of its impact; or (c) set `include_in_prompts: false` on the fitness metric for D, which would eliminate the prompt confound but would itself be a difference from v2. Of these, option (a) is the cleanest: keep the v2 description verbatim. The fitness description's inaccuracy is irrelevant to D program behavior -- the LLM does not compute tanh internally. A D program's mutation quality depends on the prompt it receives, not on the mathematical accuracy of the metric description. The tanh function is applied by the evaluator after the program runs.

---

## Major Concerns

### M1. The Pre-Registered Mechanistic Claim (Section 2.2) Is Definitionally True and Therefore Uninformative

**Severity: MAJOR**

Section 2.2 pre-registers that "the fraction of D-archive programs with fitness exactly 0.000 must be < 10% across all 4 D runs" at gen 5. The design itself explains precisely why this must be true: "Under tanh scoring, `raw_delta = 0` maps to score 0.500... The point mass at exactly 0.000 should vanish by construction" (lines 51-52).

The only way this claim can fail is if the treatment code was not applied (a code-verification failure) or if an exception produces `score=0.0` (which the design also proposes to change to 0.5). In other words, this is not a scientific prediction about D-population dynamics. It is a tautology: "if we change the fitness function so that 0.0 is not a possible output, then we will not observe 0.0." The gen 5 timing adds no information -- the claim is equally true at gen 1, gen 50, or gen 200.

I do not object to including this as a treatment verification check (which is what it actually is). But pre-registering it as a "mechanistic claim" alongside the primary hypothesis inflates the appearance of scientific content. If both the primary hypothesis (mu_G) is NULL and the mechanistic claim PASSes, the design would report "D collapse is broken but G is still not lifting" -- which is useful information. But the mechanistic claim contributes no independent evidence because its outcome is determined by whether `np.tanh` is present in the code, not by any evolutionary dynamics.

**Required fix**: Relabel Section 2.2 from "Pre-Registered Mechanistic Claim" to "Treatment Verification Check" or "Code-Application Diagnostic." Acknowledge in the text that the < 10% threshold is definitionally satisfied if the code change is correctly applied. The true mechanistic question is not whether point-mass vanishes (it must, by construction) but what the D fitness *distribution shape* looks like at gen 5/25/50 -- which is already covered by Section 8.3 (D Fitness Histogram). Elevate Section 8.3 to the mechanistic prediction role: pre-register an expected distribution shape (unimodal near 0.5 at gen 5, potentially shifting rightward by gen 25 as D programs learn to improve) rather than a threshold that is satisfied by construction.

---

## Minor Concerns

### m1. Exception-Path Score Change (0.0 to 0.5) Has a Subtle Incentive Consequence

Section 3, row 2: the exception-path score changes from 0.0 to 0.5. The design justifies this as "neutral, consistent with tanh(0)." This is mathematically correct but creates a subtle incentive change.

Under v2, a D program that throws an exception on an opponent gets `score=0.0` and `is_valid=1.0` (line 114-120 of current `pop_b/evaluate.py`). The aggregator includes this record in the mean fitness computation, dragging fitness down. Under the tanh treatment, the same exception produces `score=0.5`, which is the *neutral* score. This means a D program that throws exceptions is no longer penalized relative to a program that tries and fails to improve (raw_delta=0 also gives 0.5).

I have verified that the `_invalid_opp_metrics` path (lines 37-49 of `pop_b/evaluate.py`) uses `is_valid=0.0`, which means it IS correctly filtered by the `ConfigurableAggregator`'s validity gate (line 217 of `aggregators.py`). But the exception handler at lines 110-120 uses `is_valid=1.0` -- so exception-path records ARE included in fitness. The incentive to produce robust (non-crashing) code is weakened under the treatment.

This is not a confound (the change is part of the treatment). But it should be documented as a known behavioral consequence. If exception rates are high, the tanh treatment may produce systematically higher D fitness not because D programs improve configurations better, but because crashing programs are no longer penalized. Add D exception rate to the secondary diagnostics.

### m2. `per_opp_metrics.delta` Semantics Change: Downstream Impact Understated

Section 3, row 3 notes that `delta` changes from `max(raw_delta, 0.0)` (clamped) to `raw_delta` (signed). I have traced the downstream consumers:

1. **`DGTrackerStage` (dg_tracker_stage.py, lines 200-208)**: reads `record["delta"]` and routes to `dg_d_wins` if `delta > 0` and `dg_g_resisted` if `delta <= 0`. Under v2, all deltas were >= 0, so `dg_g_resisted` was populated only when `delta == 0` exactly. Under treatment, negative deltas flow into `dg_g_resisted`. This changes its semantics from "D tried and tied" to "D tried and made things worse." This is arguably *more correct* but is a behavioral change.

2. **`DGImprovementTracker.record_batch` (dg_tracker.py, lines 200-215)**: routes `delta > 0` to sorted sets with `gt=True`. Negative deltas get stored in `dg_metrics` hash but NOT in `dg_improvements` or `dg_best_pairs`. Correct behavior -- no breakage.

3. **`mean_improvement_raw` in the aggregator config**: reduces via `op: mean, field: delta`. Under v2 this was `mean(max(raw, 0))` -- always non-negative. Under tanh treatment, this becomes `mean(raw_delta)` -- potentially negative. The pop_b metrics.yaml `lower_bound: 0.0` on `mean_improvement_raw` (line 39-41) is now technically wrong.

None of these produce a runtime failure or a confound. But the `lower_bound: 0.0` metadata inaccuracy on `mean_improvement_raw` should be corrected. Since `include_in_prompts: false` for this metric, it does not trigger the C1 prompt-content concern.

### m3. The NULL Band Definition (Section 2.1) Is Generous

The NULL band is [0.03200, 0.03449). The design defines 0.03200 as the REGRESSIVE boundary. However, v2's bootstrap 95% CI lower bound was 0.03001. A result at mu_G=0.03250 -- inside v2's CI and clearly within sampling noise -- would be classified as NULL rather than REGRESSIVE. This makes the REGRESSIVE verdict essentially unreachable with N=4 sampling noise. Acknowledge this explicitly.

### m4. Wall-Clock Cap Adequacy

Section 10 sets a 28h hard cap. v2 early-terminated at ~23h reaching G gens 36-55 (well below the 200 target). The design does not state the expected generation depth at 28h or whether partial runs (G at gen ~40 out of 200) are acceptable for the primary analysis. If D-smoothing accelerates D's generation turnover (plausible under a non-degenerate fitness landscape), the D/G dynamics may shift. State explicitly: (a) expected G generation depth at 28h based on v2's rate, and (b) that partial runs are included in the primary analysis at their achieved depth.

### m5. Smoke Test Threshold Is Weak

Section 11.3 requires "< 50% fitness < 0.001" at gen 3. Given that the tanh function makes `score=0.0` essentially unreachable for valid programs (only via `is_valid=0.0` paths which are gated out of fitness), ANY valid D program should have fitness well above 0.001. A threshold of < 50% is too generous to be a meaningful treatment verification. Tighten to < 5% at gen 3, or better: check that the median D fitness falls in [0.3, 0.7] (the expected range for neutral-to-modest improvers under tanh).

### m6. Power Analysis Notation

Section 7 states "~80% power for a 0.005pp effect (mu_G = 0.0382)." The suffix "pp" (percentage points) is inconsistent with the scale: 0.005 in raw actual_fitness units corresponds to a ~15% relative increase from v2's mean, not 0.005 percentage points. Use either raw delta notation ("raw delta of 0.005") or relative terms ("15% relative increase"). This is a presentation issue only.

---

## Hypothesis and Falsifiability

- [x] H0 clearly stated (mu_G <= 0.03449)
- [x] H1 falsifiable and directional (mu_G > 0.03449)
- [x] Primary metric pre-specified (best-ever actual_fitness, grand mean across 4 G runs)
- [x] Success criteria numeric and unambiguous (five-tier threshold table in Section 2.1)

**Notes**: The five-tier threshold system (POSITIVE strong / POSITIVE / SUGGESTIVE / NULL / REGRESSIVE) is well-calibrated. The SUGGESTIVE tier at baseline-repro parity (0.03449) is a reasonable bar for a first experiment under dual-smoothed fitness.

## Confound Analysis

- [x] Controlled variables genuinely controlled (Section 5 is comprehensive)
- [ ] IV isolated -- **FAILS** on C1 (metrics.yaml prompt content co-varies with treatment)
- [x] Known confounds mitigated or acknowledged (Section 9, Confounds 1-7)
- [x] Val/test split not applicable (Heilbronn is a synthetic optimization task)

**Unaddressed confounds**: C1 (metrics.yaml description change as prompt content IV). All other confounds are appropriately handled.

## Statistical Validity

- [x] Sample size honestly stated (N=4, underpowered for small effects, acknowledged)
- [x] Statistical test appropriate (bootstrap CI, not formal hypothesis testing -- correct for N=4)
- [x] Significance threshold replaced by effect-size thresholds (appropriate)
- [x] Multiple comparison correction not applicable

**Notes**: The power analysis (Section 7) is honest about the limitations. I appreciate that Elena does not pretend N=4 supports formal inference. The emphasis on effect magnitude and cross-run consistency is correct for this sample size.

## Evaluation Protocol

- [x] Metric computed identically across conditions (actual_fitness from pop_a evaluation, unchanged)
- [x] Val/test distinction not applicable (Heilbronn synthetic)
- [x] No post-hoc metric selection (primary metric pre-registered)
- [x] Thinking mode consistent (same LLM, same proxy, same model)

**Notes**: The G-side evaluation is completely unchanged -- actual_fitness is computed by `pop_a/evaluate.py` which is not modified by this experiment. The DV is clean.

---

## Required Changes Before Approval

1. **C1 (Critical)**: Resolve the metrics.yaml prompt content confound. Recommended: freeze `pop_b/metrics.yaml` fitness description identical to v2 text. Do not update it to describe tanh semantics.
2. **M1 (Major)**: Relabel Section 2.2 from "Pre-Registered Mechanistic Claim" to "Treatment Verification Check." Acknowledge the tautological nature of the < 10% threshold. Elevate Section 8.3's D fitness histogram to the mechanistic prediction role with a pre-registered expected distribution shape.

---

## Verdict

**[x] NEEDS REVISION**

One critical concern (C1: metrics.yaml description as hidden IV) and one major concern (M1: tautological mechanistic claim) must be resolved. Both fixes are straightforward and require no redesign. The minor concerns (m1-m6) should be addressed but do not individually block approval.

**Reviewer notes**: This is among the strongest designs in the heilbron series. The scoping discipline -- isolating D-smoothing from the full REDESIGN bundle -- is exactly right. The confound analysis in Section 9 is the most thorough I have reviewed in this project. The G-smoothing confound (Confound 1) is handled with appropriate intellectual honesty rather than being dismissed or hidden. Once C1 and M1 are resolved, I expect to approve on the next round.

*The science demands nothing less.*

---

## Round 2 Review (2026-04-24)

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Round**: 2
**Scope**: Convergence check on C1, M1, m1-m6. No new concerns unless introduced by revision.

---

### Fix Verification Checklist

**C1 (Critical): metrics.yaml prompt text as hidden IV -- PASS**

Elena removed the metrics.yaml description change from the IV table (Section 3 no longer lists a row for the fitness description). The description text is now listed in Section 5 (Controlled Variables) at line 194 with the exact v2 wording: `"MAP-Elites selection signal: mean over opponent configs of min(improvement / 0.0365, 1). Worsening counts as 0, not negative."` and is explicitly marked **Frozen identical to v2**. Section 3 (line 105) states plainly: "metrics.yaml fitness description is NOT changed." I verified the current `pop_b/metrics.yaml` on main: the `fitness` metric has `include_in_prompts: true` and the description matches the v2 text verbatim. The design correctly notes that the description is technically inaccurate under tanh but that keeping it identical preserves prompt content parity. This is exactly the fix I recommended (option (a) from Round 1). The confound is eliminated.

Additionally, Section 5 line 195 notes that `mean_improvement_raw.lower_bound` will change from `0.0` to `-0.0365`, but that metric has `include_in_prompts: false`, so no prompt content change results. I confirmed `include_in_prompts: false` at line 39 of the actual `metrics.yaml`. Clean.

**M1 (Major): mechanistic claim was definitional -- PASS**

Section 2.2 has been relabeled to "Treatment Verification Check (Code-Application Diagnostic)" with an explicit acknowledgment: "This is a code-application diagnostic, not a scientific prediction." The text at line 66 now states that the < 10% threshold "is definitionally satisfied by the tanh formula" and that failure "can only occur if the treatment code was not applied." This is exactly what I asked for.

More importantly, Elena added Section 2.2a ("Pre-Registered Mechanistic Prediction (D Fitness Distribution Shape)") with quantitative thresholds at three checkpoints:

- **Gen 5**: fraction in [0.1, 0.9] > 70%; median in [0.35, 0.65]; variance > 0.01.
- **Gen 20**: fraction in [0.1, 0.9] > 60%; median >= 0.45; no single bin > 40% of mass.
- **Gen 50**: variance > 0.005; distribution retains structure (SD > 0.07).

These are genuine predictions about evolutionary dynamics, not tautologies. The thresholds are specific enough to fail (e.g., if D fitness clusters at the boundary or collapses to a narrow mode). The PASS criteria require 3-of-4 D runs at all checkpoints. Section 8.3 provides the corresponding diagnostic with the same thresholds. Section 14.2a pre-registers the analysis. This is a substantial improvement over Round 1 -- the mechanistic prediction now carries independent information beyond the treatment verification.

**m1 (Minor): exception-path incentive -- PASS**

Section 3 (lines 107-108) now documents the behavioral consequence of `score=0.5` on exception: "This weakens the incentive to produce robust (non-crashing) D code." Section 8.7 adds D exception rate as a secondary diagnostic with a 20% threshold for investigation. The exception-path change is correctly identified as "NOT a confound" (part of the treatment) but as a "known behavioral consequence." Adequate.

**m2 (Minor): delta semantics / lower_bound -- PASS**

Section 3, lines 113-116, now documents the full downstream impact of the signed `delta` change, including the `DGTrackerStage` semantics shift and the `mean_improvement_raw` aggregator behavior change. Line 116 explicitly states: "update `pop_b/metrics.yaml` field `mean_improvement_raw.lower_bound` from `0.0` to `-0.0365`" with the note that `include_in_prompts: false` eliminates any prompt confound. The Revision Log entry (line 15) confirms this was addressed.

**m3 (Minor): REGRESSIVE unreachable -- PASS**

Section 2.1, lines 56 (the paragraph beginning "Note on REGRESSIVE reachability") explicitly acknowledges that the REGRESSIVE threshold "falls below v2's bootstrap 95% CI lower bound" and states it is "effectively unreachable under normal variance." The threshold is retained for completeness. This is exactly the level of intellectual honesty I requested.

**m4 (Minor): wall-clock adequacy -- PASS**

Section 10, lines 359 states: "v2 reached G gens 36--55 (mean ~45) and D gens 38--91 (mean ~60) in ~23h. At the same per-gen rate, 28h should yield G gens ~44--67 (mean ~55) and D gens ~46--110 (mean ~73)." It further confirms: "mu_G is computed from best-ever actual_fitness, which is a monotone function of generation depth." All three mechanistic checkpoints (gen 5, 20, 50) are confirmed reachable within 28h. This addresses the concern completely.

**m5 (Minor): smoke test tightened -- PASS**

Section 11.3 (line 399) now requires "< 5%" at `fitness < 0.001` (tightened from the original < 50%) AND "Median D fitness must fall in [0.3, 0.7]." Both conditions are evaluated at gen 3. The dual criterion (near-zero fraction + median range check) provides a meaningful treatment verification that would catch both code deployment failures and unexpected interaction effects. Good.

**m6 (Minor): power notation -- PASS**

Section 7 (line 276-279) now uses "raw delta of 0.005" / "raw delta of 0.003" / "raw delta of 0.001" instead of the incorrect "pp" notation. The relative percentages are provided parenthetically ("~15% relative increase", etc.) for interpretability. Clean.

---

### New Concerns Introduced by Revision

None. The revision is conservative -- each fix addresses exactly the flagged concern without introducing new variables, new confounds, or new design complexity. The added Section 2.2a is the most substantive change; its quantitative thresholds are well-calibrated and falsifiable.

One observation (not a concern): the `fitness` metric in `pop_b/metrics.yaml` currently has `lower_bound: 0.0` (line 7). Under tanh scoring, the actual lower bound of the fitness metric is `0.5 * (tanh(-1) + 1) = 0.119` for `raw_delta = -Q_MAX`, and approaches 0.0 only asymptotically. This `lower_bound` field has `include_in_prompts: true` if it is rendered into prompts. However, inspecting the metrics.yaml schema, `lower_bound` is metadata for the aggregator's validity check, not prompt-rendered text. If I am wrong about this and `lower_bound` IS included in prompt text, this would be a prompt-invisible metadata change that Elena's revision explicitly acknowledges as acceptable (line 195: "prompt-invisible bits (like `lower_bound`) may still change"). I flag this as an observation for the implementer, not as a review concern.

---

## Verdict: APPROVED

All critical and major concerns from Round 1 are resolved. All six minor concerns are addressed. The revision is disciplined: fixes land exactly where requested, with no scope creep and no new confounds. Section 2.2a elevates the design by providing genuine mechanistic predictions with falsifiable quantitative thresholds -- a material improvement over the already-strong Round 1 design.

This experiment is ready for researcher sign-off and pre-registration.

*The science demands nothing less.*
