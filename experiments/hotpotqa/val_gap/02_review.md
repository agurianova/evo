# Adversarial Review: Val-Test Gap Reduction via Rotating 600-Sample Validation Set

**Date**: 2026-03-05
**Reviewer**: Prof. Andrei Volkov
**Input**: `experiments/hotpotqa_val_gap/01_design.md`

---

## Summary of Design

A 2-cell screening experiment (Runs O and P) comparing a fixed-300-sample validation protocol
(control, replicating Run K) against a rotating-600-sample validation protocol (treatment,
new `static_r600` problem directory) to test whether increasing validation coverage from
300/1000 to 600/1000 reduces the val-test gap observed across all prior HotpotQA evolution
runs. The primary metric is the val-test gap at generation 50; the secondary constraint is
that test EM must not drop below 60.0%. N=1 per condition; n=300 fixed test set.

---

## Methodological Concerns

| # | Concern | Severity | Recommendation |
|---|---------|----------|---------------|
| 1 | **Compound treatment confound is stated but its consequence for the decision gates is inconsistent.** The design correctly identifies that Run P changes two variables simultaneously: sample size (300 → 600) and evaluation protocol (fixed → rotating). However, the POSITIVE gate is defined as `delta_gap >= +2.0pp AND test_EM(P) >= 60.0% AND test_EM(P) >= test_EM(O) - 1.5pp`. A POSITIVE verdict says "rotating-600 produces a smaller val-test gap." But Section 4 explicitly states: "A SUCCESS verdict means 'rotating-600 vs fixed-300.' It does NOT mean 'sample size effect' or 'rotation effect.'" These statements are correct and honest. The problem is that Section 12 says Run Q (fixed-600) should be proposed "immediately if Gate B returns POSITIVE" — but then classifies Run Q as requiring its own "Phase 1-5 process," implying it is an independent experiment. If Run Q is the necessary complement to interpret a POSITIVE result, it should be pre-committed as the mandatory next step in Phase 3 planning, not left contingent on Gate B as an "optional" follow-up. A POSITIVE result without Run Q leaves the primary mechanistic question (size vs. rotation) unanswerable, and the research program risks stalling. | **Major** | Strengthen Section 12 item 2: state explicitly that a POSITIVE Gate B verdict REQUIRES proposing Run Q in the Phase 5 results write-up as an immediate, committed follow-up, not merely a suggestion. The current language "should be proposed as a follow-up immediately" is insufficiently binding. Also add a pre-commitment sentence to the decision gate text: "A POSITIVE verdict without Run Q provides only a compound-treatment conclusion, which is insufficient to recommend adoption of rotating-600 as the new default." |
| 2 | **The "best-by-val" selection procedure for Run P is not equivalent to the same procedure for Run O, but the gap comparison treats them as equivalent.** In Run O (fixed-300), "best-by-val" means the program with the highest EM score on the same 300 samples evaluated identically each time — a consistent, low-noise selection criterion. In Run P (rotating-600), "best-by-val" means the program with the highest val EM score on its own unique 600-sample draw, compared to OTHER programs' val EM scores on THEIR own unique 600-sample draws. This comparison is across non-identical evaluation sets. A program selected as "best-by-val" in Run P may have appeared best precisely because its particular 600-sample draw happened to be easier (lower question difficulty, higher BM25 retrieval precision). This is the winner's curse mechanism — but the design implicitly treats the resulting val EM (from that lucky draw) as a valid numerator in the gap calculation, which inflates gap_P relative to its counterfactual value on a representative draw. The design acknowledges this in Section 9 ("Winner's curse in rotating evaluation") but does not acknowledge that the gap measurement itself is contaminated: val EM(P) is the max over 50 generations of program-specific lucky draws, not a consistent measure. | **Major** | Add to Section 8 a clarification that `gap_P` as defined is an **upper bound estimate** of the true gap, because val EM(P) is drawn from the lucky-draw distribution of the best-of-archive program rather than the program's expected accuracy. State explicitly that comparing gap_P directly to gap_O understates the winner's curse effect — if anything, the measured gap_P is biased upward (gap appears smaller than it would be under repeated evaluation of the same program on the full 600-sample draw distribution). The direction of this bias actually strengthens H₁ interpretations (a lower gap_P is more, not less, impressive if you account for the upward bias). This should be noted in the Phase 5 interpretation section as a directional qualifier. |
| 3 | **The "best-by-val" definition is ambiguous for Run P across generations.** Section 8 states: "the program with the highest val EM recorded anywhere in the evolution (generations 1-50)." In Run O, each program's val EM is reproducible — if you re-evaluate the best-by-val program, you get the same score. In Run P, each program's val EM is its score on a single draw at the generation it was evaluated. If you re-evaluate the best-by-val program from Run P on a new 600-sample draw, you get a different score. The "highest val EM recorded" in Run P is thus a max over stochastic measurements, not a max over deterministic program quality. Two direct consequences: (a) The reported val EM for Run P's "best-by-val" program is upward-biased relative to the program's expected accuracy on any given draw. (b) The program selected as "best-by-val" may not be the program with the highest expected test EM. The design should acknowledge that the best-by-val program in Run P may not be the "true best" program in any principled sense, and that test-evaluating the best-by-val program under rotating eval introduces an additional source of measurement uncertainty. | **Minor** | Add to Section 4 ("Dependent Variables"): "Note: for Run P, the 'best-by-val program' is identified by the maximum val EM score in the Redis archive. This score was realized on a single 600-sample draw at the generation the program was first inserted into the archive. It is not the program's expected accuracy under the draw distribution. A sensitivity check (if feasible) would re-evaluate the top-5 programs by archive val EM on the fixed test set and select the best by test EM; this check is exploratory and does not replace the pre-registered primary analysis." |
| 4 | **MAP-Elites archive diversity complicates the winner's curse analysis presented in Section 1.** The winner's curse argument rests on the claim that programs are "selected because they were lucky on their particular draw" — a statement appropriate for simple greedy selection with a single elite. MAP-Elites uses bin-based selection: a program enters the archive if it is the best in its behavioral bin, not if it is globally the best. This means the archive can simultaneously contain programs that were lucky on their draws AND programs that are genuinely better within their behavioral niche. The winner's curse is therefore diluted across the 50 behavioral bins (primary_resolution=50). Furthermore, under rotating evaluation, programs in different bins were evaluated on different 600-sample draws — the archive contains 50 programs each evaluated on a distinct draw, with no common reference frame. The expected-overlap calculation (360/1000 between any two programs) understates the structural problem: the archive diversity mechanism actually ensures that the archive includes programs from MANY different lucky draws, not just one. This may explain why rotating-300 was consistently worse than fixed-300 across all three runs (L, M, N): MAP-Elites amplified, rather than averaged out, the draw-dependent noise. The design's mechanistic analysis does not engage with this MAP-Elites-specific effect. | **Major** | Add to Section 1 ("Connection to prior findings") and Section 9 ("Fitness comparability within the archive") a MAP-Elites-specific analysis: under rotating evaluation, the 50 archive bins are populated by programs evaluated on 50 distinct draws. Bin-to-bin fitness comparisons are across non-identical evaluation sets. The archive may densely populate bins where programs happened to receive easy draws, starving bins where programs received hard draws — not because those bins have genuinely fewer high-quality programs, but because of evaluation noise. This mechanism predicts that rotating evaluation amplifies, not reduces, selection noise in MAP-Elites, regardless of draw size. State this as a third mechanistic hypothesis (H_mapelites: MAP-Elites amplifies per-draw noise) alongside the winner's curse and regime-mismatch hypotheses. This hypothesis predicts gap WORSE under rotating-600 than fixed-300 for any sample size, and would be consistent with the L/M/N pattern. |
| 5 | **The `static_r600` problem directory does not yet exist, and the hash seeding specification in the design leaves one critical ambiguity unresolved.** Section 3 states: "hash-seeded random draw of 600/1000 training samples per chain_spec." The existing `static_r/validate.py` confirms the mechanism: `hashlib.sha256(json.dumps(chain_spec, sort_keys=True, default=str).encode())`. This is per-program-specification, not per-generation and not per-evaluation-call. Two programs with identical specifications receive identical draws; two programs that differ by one character receive different draws. This is correct and clean. However: the design does not specify what happens when the same `chain_spec` is re-evaluated (e.g., at gen 10, 25, 50 checkpoints for test evaluation). The `static_r/validate.py` code uses a deterministic hash — so re-evaluating the same `chain_spec` yields the same 600-sample draw. This is good for reproducibility, but it means that a program's val EM is deterministic across all calls to `validate.py` (no per-call randomness beyond the hash). The design's statement that "the seed's val EM will differ per evaluation" (Section 6) is therefore INCORRECT: the seed's val EM is deterministic for a given `chain_spec` once the hash is fixed. This is not a flaw — it is actually better than per-call randomness — but the design misstates the mechanism. | **Minor** | Correct Section 6: the seed's val EM under rotating-600 is deterministic (not variable per evaluation call). The single realized draw is fixed by the SHA-256 hash of the seed's `chain_spec`. This means the seed's initial val EM is a single deterministic number, not a sample from a distribution. The sentence "each call to validate.py draws a different 600-sample subset" should be corrected to "the same chain_spec always receives the same 600-sample subset, determined by the SHA-256 hash of the serialized specification." |
| 6 | **The POSITIVE decision gate adds a third conjunctive criterion (`test_EM(P) >= test_EM(O) - 1.5pp`) that appears in Section 10 but is NOT defined in Section 2's Hypotheses or Section 4's joint success criterion.** Section 4 states: "Joint success criterion: Run P is declared a SUCCESS only if BOTH conditions hold: (1) gap(P) < gap(O) - 2.0pp (2) test EM(P) >= 60.0%." Section 10 adds a third condition: `test_EM(P) >= test_EM(O) - 1.5pp`. This third condition is not pre-specified in the hypotheses. It appears for the first time in the decision gate. This is a pre-registration inconsistency: the hypothesis section and the decision gate use different success criteria. If Run P achieves gap reduction >= 2.0pp and test EM >= 60.0% but test_EM(P) < test_EM(O) - 1.5pp, the decision gate classifies the result differently from what Section 4 would suggest. Which takes precedence? | **Major** | Harmonize Sections 2, 4, and 10. Either (a) add the `test_EM(P) >= test_EM(O) - 1.5pp` condition to Section 4's joint success criterion with a brief motivation (preventing a scenario where Run P's absolute test EM is fine but it dramatically underperforms relative to Run O), or (b) remove it from the decision gate in Section 10. The three-condition gate is arguably better science (it prevents Run O from being an anomalously poor control while Run P still gets classified POSITIVE by the absolute floor alone), but it must be pre-registered in the hypothesis section to be legitimate. |
| 7 | **The 2.0pp gap reduction threshold is classified as POSITIVE but is below one SE of the gap estimate, with no correction for the fact that the decision gate is one-sided.** The design acknowledges this honestly in Section 2 ("a 2.0pp threshold is below one SE — this experiment cannot statistically confirm a 2.0pp effect from N=1"). However, classifying a sub-1-SE one-sided comparison as POSITIVE risks misleading downstream readers. The word "POSITIVE" carries scientific weight beyond what the design's own SE analysis supports. The design's own noise classification (Section 7) says "< 2.0pp reduction: indistinguishable from sampling noise." Yet Gate B classifies >= 2.0pp as POSITIVE, not as "suggestive." This is internally inconsistent: the design simultaneously tells us that 2.0pp is indistinguishable from noise AND that it constitutes a POSITIVE result. | **Major** | Relabel the Gate B "POSITIVE" category as "SUGGESTIVE-STRONG" or use the language "Directionally POSITIVE" with explicit language: "This result cannot be distinguished from sampling noise at N=1, but is directionally consistent with H₁ and warrants N >= 3 replications before adoption." Reserve the label "POSITIVE (actionable)" for results >= 5.0pp gap reduction (> 1 SE). Alternatively, align the decision gate language with the noise classification in Section 7: if the design says < 2.0pp is noise, then 2.0pp should be the bottom of "SUGGESTIVE," not the bottom of "POSITIVE." The current SUGGESTIVE band ([1.0pp, 2.0pp)) is narrower than makes sense given that 2.0pp is itself below the noise floor. |
| 8 | **The validation runtime estimate for Run P may be significantly optimistic, with no contingency plan if it exceeds the budget.** Section 11 estimates 600-sample eval at ~8 min/gen ("linear scaling from the 300-sample ~5 min mean"). However, linear scaling assumes identical computational structure — but with 600 samples at ~60% EM, the failure pool is ~240 samples (vs. ~120 for 300-sample fixed). The random failure sampler draws 10 per evaluation call. With 600 samples, there are more results to collect, store, and pass to the formatter. The bottleneck in thinking-mode evaluation is the LLM inference time per sample, which IS linear in sample count. But the storage and failure-collection overhead is not guaranteed linear. The estimate of 1.6× (8 min vs 5 min) should be stated as an assumption to be verified at dry-run, with a fallback if actual gen time exceeds 12 min (50 gens × 12 min = 600 min → 10h just for validation, plus mutation overhead → >30h). The early-termination criterion of "20 min per gen" (Section 10) is 2.5× the estimate — an unusually wide tolerance for a budget-constrained experiment. | **Minor** | In Section 11, state the runtime estimate as a projection to be verified at dry-run, not a given. In Section 10's early-termination criterion, lower the threshold from 20 min to 15 min per gen (approximately 2× the estimate), and add a note that if dry-run gen time exceeds 12 min, the experiment should be considered at risk and the researcher should consult the mutation server utilization before launching. |
| 9 | **The archive acceptance rate hypothesis (H1_disc) is not connected to the decision gates.** Section 2 defines H1_disc as: "mean_acceptance_rate(P) >= mean_acceptance_rate(O)." Section 10's Gate C defines: "acceptance_rate(P) >= acceptance_rate(O) + 5pp" for a positive H1_disc result. The 5pp offset in Gate C is not pre-specified in Section 2's H1_disc definition — Section 2 says "mean_acceptance_rate(P) >= mean_acceptance_rate(O)" (i.e., any positive difference), while Gate C requires >= 5pp. This is the same pre-registration inconsistency pattern as Concern #6. Minor but should be harmonized. | **Minor** | Align Section 2's H1_disc statement with Gate C's 5pp threshold. Update H1_disc to: "mean_acceptance_rate(P) >= mean_acceptance_rate(O) + 5.0pp" or remove the 5pp offset from Gate C and use the simple comparison. Either fix is acceptable; the inconsistency must be resolved. |
| 10 | **The consistency check range for Run O (Gate A) is calibrated against a heterogeneous set of prior results without acknowledging their variance.** Gate A accepts gap_O in [4.0pp, 9.0pp]. The lower bound (4.0pp) is well below any observed gap (seed 2.7pp is at gen-0, not gen-50; gen-50 minimum is K=6.33pp). The upper bound (9.0pp) is chosen based on Run H (~9.7pp). But Run H used ASI formatter improvements as part of its experimental condition — it is not a clean control run under identical config to Run O. If Run O (no ASI formatter differences from H) produced a gap of, say, 10pp, Gate A would flag this as an anomaly. But 10pp is within the range of valid fixed-300 outcomes given the H result. The [4.0pp, 9.0pp] range may be too narrow, causing false anomaly flags that delay analysis. | **Minor** | Widen the Gate A upper bound to [4.0pp, 11.0pp] to include the H result (9.7pp) as a valid reference point. Add a note that Run H's gap may have been inflated by the ASI-specific failure formatting, so the [4.0pp, 9.0pp] range for a baseline-config run is reasonable. The current choice (9.0pp) splits H's result (9.7pp) from the acceptance band by only 0.7pp, creating unnecessary risk of a false anomaly trigger. |

---

## Hypothesis and Falsifiability

- [x] H₀ is clearly stated
- [x] H₁ is falsifiable and directional
- [x] Primary metric is pre-specified and sufficient to test H₁
- [ ] Success criteria are numeric and unambiguous

**Notes**:

H₀ and H₁ are directional, pre-specified, and the two competing mechanistic explanations
(winner's curse vs. regime mismatch) give the hypotheses genuine interpretive structure —
either outcome is informative. The secondary mechanistic hypothesis H1_disc is appropriate
as an exploratory diagnostic.

The failure on "success criteria unambiguous" stems from Concern #6: the POSITIVE gate in
Section 10 adds a third criterion (`test_EM(P) >= test_EM(O) - 1.5pp`) that is absent from
Section 4's joint success criterion. A researcher reading Section 4 and a researcher reading
Section 10 will apply different criteria for the same result. This inconsistency must be
resolved before pre-registration.

The 2.0pp threshold classification as POSITIVE (Concern #7) creates an additional ambiguity:
the design's own noise analysis says 2.0pp is indistinguishable from sampling noise, yet the
same 2.0pp triggers POSITIVE in the decision gate. The thresholds must be consistent with the
design's own SE analysis.

---

## Confound Analysis

- [x] All controlled variables are genuinely controlled
- [x] IV is isolated (no other differences between conditions)
- [x] Known confounds are mitigated or acknowledged
- [ ] Val/test split is not contaminated

**Unaddressed confounds**:

The val/test split concern (checked unchecked above) is specific to the gap measurement for
Run P, as analyzed in Concern #2. The fixed-300 test set is never seen during evolution —
there is no direct contamination. However, the gap measurement for Run P is not equivalent to
the gap measurement for Run O in a subtle but important sense: val EM(P) comes from a
program selected as "best" across 50 generations of per-program stochastic draws, which
inflates val EM(P) relative to the program's expected accuracy. This is not contamination
in the traditional sense, but it means gap_P is not a symmetric quantity to gap_O. The
design acknowledges the mechanism but does not acknowledge its effect on the gap measurement.

**Three confounds requiring more thorough treatment**:

**Confound A: MAP-Elites bin-level lucky draws (Concern #4).** This is the most important
unaddressed structural issue. Under fixed-300, all 50 archive bins are populated by programs
evaluated on the same 300 samples — fitness comparisons across bins are coherent. Under
rotating-600, the 50 archive bins are populated by programs each evaluated on a distinct
600-sample draw. The archive diversity mechanism ensures heterogeneous draws, not homogeneous
draws. If evaluation difficulty varies across draws (some 600-sample subsets are harder than
others), the archive will be systematically biased toward programs in behavioral niches where
easier draws happened to be assigned. This is a MAP-Elites-specific amplification of the
winner's curse that is absent from simpler evolutionary algorithms. The design presents the
winner's curse as a single-program phenomenon (lucky program → enters archive) but it is
also a multi-program, cross-bin phenomenon (lucky draw in bin X → that bin is populated by
the beneficiary of a favorable draw, regardless of true quality).

**Confound B: Richer failure pool changes mutation signal content (acknowledged in Section 9
as "Richer failure pool").** The design acknowledges this mechanism but classifies it as
"a possible contributor to any test EM improvement" rather than a confound. This is too
generous. The failure pool doubles from ~120 to ~240 expected failures. The formatter samples
10 randomly from each pool. With 240 failures, the random sample of 10 is more diverse across
the failure taxonomy (retrieval errors, reasoning errors, extraction failures) than with 120.
This is a systematic difference in the mutation signal quality — not just a noise change but
a qualitative change in what the mutation LLM is asked to fix. If Run P shows improved test
EM, it is genuinely unclear whether this came from (a) reduced winner's curse, (b) rotation
regime mismatch, or (c) higher-quality failure diagnostics driving better mutations. All three
co-vary with the treatment. The design should name (c) as a third mechanism in Section 1, not
relegate it to a footnote in Section 9.

**Confound C: Context-window pressure at 600 samples.** The chain LLM context window was
identified in prior experiments as critically constrained at 16,384 tokens (now proposed at
32,768). With 600 samples, the total output volume from Run P's validation calls is 2× that
of Run O, and the failure list passed to the mutation LLM contains 2× as many candidates.
If the mutation LLM context window approaches saturation on longer failure descriptions,
the 10 randomly sampled failures from a 240-failure pool may trigger different truncation
behavior than 10 from a 120-failure pool. This is not accounted for in the design.

---

## Statistical Validity

- [x] Sample size is justified
- [x] Statistical test is appropriate for the data
- [ ] Significance threshold is pre-specified
- [x] Multiple comparison correction applied if testing multiple hypotheses

**Notes**:

The N=1 justification is honest and structurally sound. The external reference distributions
from K (fixed-300 control) and L/M/N (rotating-300 treatment) are the correct framing — using
prior runs to calibrate expectations is the right approach for this compute-constrained setting.

The significance threshold concern is not a deficiency in the traditional sense: the design
correctly notes that no formal p-value is computable at N=1. However, Concern #7 identifies an
internal inconsistency between the SE analysis (which says 2.0pp is below the noise floor) and
the decision gate (which classifies 2.0pp as POSITIVE). This inconsistency is a threshold
miscalibration that must be resolved.

The multiple-comparison concern is absent here — the primary test is a single directional
comparison of gap_P vs gap_O. Secondary analyses (H1_disc, acceptance rate, test EM
trajectory) are correctly labeled exploratory and do not interact with the primary verdict.
This is well-handled.

The bootstrap sensitivity note (Section 8) for the 2.0–5.0pp range is appropriate and adds
methodological value. The design correctly limits this to test-set sampling noise and does
not overclaim that it addresses inter-run trajectory variance.

---

## Evaluation Protocol

- [x] Metric is computed identically across all conditions
- [ ] Val set and test set are fixed and identical for all runs
- [x] No metric is cherry-picked post-hoc
- [x] Thinking mode is consistent across all evaluations

**Notes**:

The val set is, by design, NOT identical across runs: Run O uses fixed-300 and Run P uses
rotating-600. The unchecked box reflects this intentional difference, not an error. The test
set is fixed and identical (300-sample HotpotQA_test.jsonl). The design handles this
correctly by specifying that only the gap (not the raw val EM) is a cross-condition comparable
metric. This framing is correct.

Thinking mode consistency is specified: Qwen3-8B in thinking mode for all chain LLM calls,
step_max_tokens=8192 for all LLM steps. This is correct.

One evaluation protocol concern (Concern #5): the design's statement that "each call to
validate.py draws a different 600-sample subset" is factually incorrect given the
deterministic hash mechanism in `static_r/validate.py`. The hash is per-`chain_spec`, not
per-call. This is a documentation error in the design, not a protocol flaw — the actual
mechanism (deterministic per-spec) is superior to per-call randomness.

---

## Required Changes Before Approval

1. **[Major, Concern #6]** Harmonize Sections 2, 4, and 10 on the POSITIVE success criterion.
   The third conjunctive condition (`test_EM(P) >= test_EM(O) - 1.5pp`) appears only in the
   decision gate, not in the pre-registered hypotheses or joint success criterion. Either add
   it to Section 4 with a brief justification, or remove it from the Gate B definition. These
   sections must state identical criteria.

2. **[Major, Concern #7]** Resolve the internal inconsistency between the SE analysis
   (Section 2/7: "2.0pp is below one SE — indistinguishable from sampling noise") and the
   decision gate (Section 10: "delta_gap >= +2.0pp" = POSITIVE). Relabel the current POSITIVE
   category as "SUGGESTIVE-POSITIVE" or "Directionally POSITIVE" and state explicitly that
   it cannot be distinguished from sampling noise at N=1. Reserve actionable-POSITIVE language
   for >= 5.0pp (> 1 SE) or restructure the thresholds to be consistent with the noise floor
   described in Section 7.

3. **[Major, Concern #4]** Add to Section 1 and Section 9 a MAP-Elites-specific mechanistic
   analysis of how bin-level winner's curse differs from the single-program winner's curse
   described. Specifically: under rotating evaluation, each of the 50 archive bins is populated
   by a program evaluated on a distinct draw. This means the archive diversity mechanism
   amplifies, rather than averages out, draw-dependent evaluation noise. This is a third
   mechanistic hypothesis (call it H_mapelites or H_diversity) that predicts gap worsening
   under rotating evaluation regardless of sample size, consistent with the L/M/N pattern.
   This hypothesis should be explicitly stated so the Phase 5 analysis can evaluate it.

4. **[Major, Concern #1]** Strengthen Section 12 item 2 language around Run Q. Replace "should
   be proposed" with a binding statement: "A POSITIVE Gate B verdict requires Run Q
   (fixed-600) as the mandatory next experiment to isolate the causal mechanism. A POSITIVE
   result without Run Q is interpretively incomplete and insufficient to justify adopting
   rotating-600 as the new default validation protocol." This language must also appear in
   the Gate B POSITIVE cell in Section 10's decision table.

5. **[Minor, Concern #9]** Align Section 2's H1_disc definition with Gate C's 5pp threshold.
   The hypothesis currently says "mean_acceptance_rate(P) >= mean_acceptance_rate(O)"; the
   gate requires "acceptance_rate(P) >= acceptance_rate(O) + 5pp." Pick one and use it
   consistently.

6. **[Minor, Concern #5]** Correct the factual error in Section 6: "each call to validate.py
   draws a different 600-sample subset" is wrong. The draw is deterministic per-chain_spec
   (SHA-256 hash), not per-call. Correct to: "the seed's 600-sample draw is determined by
   the SHA-256 hash of its chain_spec and is fixed across all evaluation calls." This is
   actually a stronger guarantee than the design claims — document it as such.

---

## Verdict

**[ ] APPROVED**

**[x] NEEDS REVISION** — address required changes, re-submit for review

**[ ] REJECTED**

**Reviewer notes**:

This design is substantially better than most screening studies I see in this research
program. The compound treatment acknowledgment is front-and-center rather than buried. The
external reference distributions from K, L, M, N are the right scaffold for interpreting
N=1 results. The competing mechanistic hypotheses (winner's curse vs. regime mismatch) give
the experiment genuine interpretive power regardless of outcome. The pre-launch checklist is
thorough. The failure to adopt a fresh Run O (rather than reusing K) is scientifically
sound — temporal confounds are real.

However, four major concerns must be addressed before this can proceed.

Concern #6 (criterion inconsistency between Sections 4 and 10) is the most urgent: a
pre-registered design cannot have two different success criteria for the same verdict. If this
inconsistency is not resolved before Phase 3, the researcher will face an interpretive
ambiguity that cannot be resolved after the fact without appearing to cherry-pick.

Concern #7 (POSITIVE label at sub-1-SE threshold) is a labeling issue but not a trivial one.
The design's own SE analysis shows that 2.0pp is indistinguishable from noise. Calling such
a result POSITIVE would mislead anyone who reads the Phase 5 report without reading the fine
print. The decision gate language must match the statistical reality the design itself
acknowledges.

Concern #4 (MAP-Elites bin-level winner's curse) is the deepest scientific concern. The
design's mechanistic analysis treats the winner's curse as a single-program phenomenon and
does not engage with the MAP-Elites-specific interaction. The fact that L, M, and N all
showed gap inflation under rotating-300 — consistently — is exactly what the MAP-Elites
amplification hypothesis predicts. The design needs to acknowledge this as a pre-registered
alternative hypothesis, or it will be unable to distinguish between "winner's curse reduced"
and "MAP-Elites amplification reduced" as explanations for any gap improvement.

Concern #1 (Run Q commitment) is about research program integrity: without a binding
commitment to Run Q on a POSITIVE result, the causal question posed by the compound treatment
will be answered by a single ambiguous data point, and the research program may adopt
rotating-600 as the new default based on undecomposed evidence.

The four required changes are tractable. None requires redesign. Concerns #5 and #9 are
documentation fixes. I expect revision, not redesign.

The science demands nothing less.

---

*Prof. Andrei Volkov*

---

## Second Review — Revision Evaluation

**Date**: 2026-03-05
**Reviewer**: Prof. Andrei Volkov
**Input**: `experiments/hotpotqa_val_gap/01_design.md` (revised v2, 2×2 factorial)
**Prior review**: First review above (NEEDS REVISION, 4 major + 6 minor concerns)

---

### Summary of Revision

The revision makes a structural choice that is scientifically sound: rather than patch the
2-cell design with a post-hoc Run Q commitment, it expands to a full 2×2 factorial (Runs O,
R, Q, P) crossing sample size (300 vs 600) against evaluation protocol (fixed vs rotating).
This makes Run Q part of the primary design, eliminates the compound-treatment causal
limitation that motivated Concern #1, and adds internal consistency checks impossible with
only two cells. The expansion is methodologically defensible and materially improves the
scientific value of the experiment.

I will now assess each required change in order, then examine new issues introduced by the
2×2 expansion.

---

### Assessment of Required Changes

**Required Change 1 [Major, original Concern #1]: Run Q commitment**

RESOLVED. The original problem was that Run Q appeared only as an optional contingency
follow-up requiring its own Phase 1-5 process. The revision incorporates Run Q as cell (600,
fixed) in the 2×2 primary design. Section 12, item 2 now states: "Causal decomposition is
now fully internal to this design. With the 2×2 expansion, all four factorial cells are
present." This is correct. The commitment is now structural rather than linguistic —
Run Q is not an optional follow-up but a primary cell. The binding language concern is fully
satisfied by the design change itself.

**Required Change 2 [Major, original Concern #7]: POSITIVE threshold raised to 5.0pp**

RESOLVED. Section 2 now defines two distinct categories with a clear threshold: "5.0pp
POSITIVE actionability threshold" at > ~1 SE, and 2.0–5.0pp as SUGGESTIVE. The section
explicitly states: "This resolves the inconsistency in the prior design version where 2.0pp
(below the noise floor by the design's own analysis) was labeled POSITIVE." Gate B in Section
10 correctly implements this: delta >= +5.0pp = POSITIVE (actionable); delta in
[+2.0pp, +5.0pp) = SUGGESTIVE; abs(delta) < 2.0pp = NULL. The SE analysis in Section 2
is now internally consistent with the thresholds: both main effects use the 2.0pp directional
filter, and 5.0pp is the actionability threshold stated to be "approximately > 1 SE for the
fixed-300 gap." Concern #7 is fully addressed.

**Required Change 3 [Major, original Concern #4]: H_mapelites added**

RESOLVED. Section 1 adds H_mapelites as the third pre-registered mechanistic hypothesis with
a precise statement: "Under fixed evaluation, all ~50 MAP-Elites archive bins are populated
by programs evaluated on the same samples — fitness comparisons across bins are coherent.
Under rotating evaluation, each archive bin is populated by a program evaluated on a distinct
draw. [...] Bins where programs happen to receive easier draws are over-represented in the
archive." Section 9's confound table adds a dedicated H_mapelites row with the same
mechanism. Crucially, Section 1 explains how the 2×2 design tests H_mapelites against
H_winners_curse: if gap_R > gap_O AND gap_P > gap_Q (both rotating worse than fixed), that
is consistent with H_mapelites; if gap_R > gap_O AND gap_P < gap_R (rotation penalty
shrinks with larger sample size), H_winners_curse has more support. This is precisely the
analysis required. Concern #4 is fully and correctly addressed.

**Required Change 4 [Major, original Concern #6]: POSITIVE criterion harmonization**

RESOLVED. Section 4 now defines the joint success criterion with all three conditions:
(1) gap(X) < gap(O) - 5.0pp, (2) test EM(X) >= 60.0%, (3) test EM(X) >= test EM(O) -
1.5pp. Section 4 explicitly states: "Condition 3 is pre-registered here with its motivation
and applies to the decision gate in Section 10; the two are now identical." Gate B in Section
10 confirms: "delta >= +5.0pp AND all three joint success conditions from Section 4." Gate C
(Run Q specific) also lists all three conditions explicitly and consistently. The
pre-registration inconsistency from the first design is gone. Concern #6 is fully addressed.

**Required Change 5 [Minor, original Concern #9]: H1_disc / Gate D threshold alignment**

RESOLVED. Section 2 now defines H1_disc as: "mean_acceptance_rate(P, gens 10-50) >=
mean_acceptance_rate(O, gens 10-50) + 5.0pp" — matching Gate D's threshold exactly.
Concern #9 is fully addressed.

**Required Change 6 [Minor, original Concern #5]: Deterministic hash mechanism**

RESOLVED. Section 3 now explicitly states: "The draw is deterministic per chain_spec — the
same chain_spec always receives the same N-sample draw, regardless of how many times
validate.py is called." Section 6 confirms for each rotating run: "Re-evaluating the same
chain_spec always yields the same draw." The first review's factual correction has been
applied accurately throughout the document. The mechanism is now described correctly.
Concern #5 is fully addressed.

All six required changes are satisfied. The revision has also addressed the two minor concerns
from the first review that were not listed as "required": original Concern #3 (best-by-val
upward bias for rotating runs) is now explicitly acknowledged in Section 4 with the direction
of the bias stated, and original Concern #8 (runtime estimate) is now stated as a projection
to be verified at dry-run with a 15 min/gen termination threshold rather than 20 min.

---

### New Issues Introduced by the 2×2 Expansion

**New Concern A: The interaction estimate is defined using sign conventions that may
systematically mislead the mechanistic interpretation.**

Section 8 defines: `interaction = (gap_R − gap_P) − (gap_O − gap_Q)`. A positive
interaction means the size effect is larger under rotating protocol than under fixed protocol.
This is described as: "A positive interaction ((gap_R − gap_P) > (gap_O − gap_Q)) would
indicate that increasing sample size specifically reduces the gap under rotation (supporting
H_winners_curse)." This is correct as stated.

However, the interpretation table in Gate B does not include a row for the case where the
interaction is positive but the rotation main effect is negative (gap_R < gap_O, meaning
rotating-300 actually HELPS). If both H_regime_mismatch and H_mapelites are wrong and
rotating-300 turns out to reduce the gap, the interaction interpretation breaks down. The
table as written assumes gap_R > gap_O in all rows. The Phase 5 analysis should report the
interaction estimate regardless of the rotation main effect direction.

**Severity**: Minor. The interpretation table is incomplete for the case where rotating-300
outperforms fixed-300. Given that the prior data (L/M/N) makes this outcome unlikely, this
is a documentation gap rather than a design flaw. Recommendation: add a row to the Gate B
interpretation table for "gap_R <= gap_O (rotating-300 matches or beats fixed-300)" with the
interpretation that H_winners_curse is strongly supported and the MAP-Elites amplification
hypothesis is falsified.

**New Concern B: The decision gate specifies which comparison triggers POSITIVE for the
overall 2×2 experiment ambiguously — the primary verdict could be read as requiring ANY one
run to be POSITIVE or ALL runs to show improvement.**

Gate B Step 1 classifies each pairwise comparison individually. Gate B Step 2 provides a
pattern interpretation. Gate C provides a specific POSITIVE verdict for Run Q (the cleanest
single-factor test). But nowhere does the design state the primary verdict rule: under what
circumstances is the experiment-level outcome classified POSITIVE?

A researcher reading the design could interpret "POSITIVE" in at least two ways:
- If Run P (rotating-600) is POSITIVE vs Run O (fixed-300): the original 2-cell hypothesis
  is confirmed, and the experiment recommends adopting rotating-600.
- If Run Q (fixed-600) is POSITIVE vs Run O (fixed-300) via Gate C: the size effect is
  confirmed, and the experiment recommends adopting fixed-600.
- If any one of the six pairwise comparisons is POSITIVE: the experiment has at least one
  actionable finding.

These three readings lead to different adoption recommendations. The design needs to specify
which comparison(s) are primary for the experiment-level POSITIVE verdict. Run Q (fixed-600
vs fixed-300) is explicitly identified as "the cleanest single-factor test" and has its own
Gate C. The design is implicitly treating Gate C as the primary test for whether to adopt a
new baseline. But this is not stated. And a POSITIVE for Run P under Gate B but a NULL for
Run Q under Gate C (or vice versa) would require a specific interpretation protocol that
is not currently pre-registered.

**Severity**: Major. The experiment now has four cells and six pairwise comparisons. Without
a pre-registered primary comparison, the Phase 5 analysis will face an implicit multiple
comparison problem: whichever comparison shows the largest gap reduction will appear most
"interesting," and the researcher (or reader) may unconsciously prioritize it. The design
must state: "The primary pre-registered comparison for the experiment-level POSITIVE verdict
is [specify: Q vs O? P vs O? any one of the four cells vs O?]."

Recommendation: Designate the comparison Q vs O (Gate C) as the primary test for adoption
of a new baseline val set, on the grounds that it is the cleanest single-factor isolation
(size only, no rotation confound, no regime-mismatch ambiguity). The comparison P vs O
remains pre-registered but secondary. The 2×2 pattern analysis (Gate B Step 2) is
pre-registered as the mechanistic interpretation, not the adoption criterion. This hierarchy
should be stated in Section 2 (Hypotheses) and reflected in Gate B.

**New Concern C: Four mutation LLM servers consuming the full pool with no slack is a
legitimate operational risk that the design acknowledges too briefly.**

Section 11 correctly states: "All four mutation LLM servers are consumed by this experiment.
No other experiments (including P3 crossover) can run concurrently without server contention."
Section 12, item 6 adds: "Strongly recommend launching all four simultaneously. If only 2
servers are available, launch O and R first [...] but document the temporal confound."

The concern is not that this is wrong, but that the risk is understated. With four mutation
servers each assigned to one run, a single server failure during evolution does not pause the
affected run — it typically causes that run's mutation stage to hang, time out, or produce
zero mutations per generation until the issue is diagnosed and resolved. Unlike a DB conflict
(which is detectable at launch), server failures during a 24-32h run may not be detected
immediately if the watchdog only monitors generation count.

More critically: if a server fails mid-run, the researcher faces a decision about whether to
continue the other three runs or pause the entire experiment. The design has an early
termination criterion for "crash with no recovery" but that criterion applies to the running
process, not to the mutation server. If the vLLM mutation server process dies after generation
10, run.py will not crash — it will hang or produce 0-mutation generations silently until
timeout. The watchdog based on `_last_gen` would not catch this if the generation index
advances on a timer even when no mutations complete.

**Severity**: Minor in design terms — this is primarily a Phase 4 operational risk. However,
the design should add to the early-termination criteria: "Zero mutations for 5+ consecutive
generations OR mutation stage timeout > 30 min for any run — indicates mutation LLM server
failure. Terminate the affected run and assess whether the remaining 3-run incomplete
factorial is still interpretable before continuing." The current criterion only says "Zero
mutations for 5+ consecutive generations: indicates a selector or configuration bug." A
selector bug and a mutation server failure are both covered by this criterion, but the
distinction matters for diagnosis and recovery.

**New Concern D: Run R uses `chains/hotpotqa/static_r` which exists and was used in L/M/N.
The design correctly explains the difference from L/M/N (prompts=default vs prompts=hotpotqa).
However, the design does not verify whether `static_r/validate.py` has been modified since
L/M/N ran, and if so, whether those modifications are compatible with this experiment.**

The `static_r/validate.py` was the subject of Amendment 4 (random failure sampling, cf0cfc1)
in the NLP prompts experiment. The design states "Existing problem directories: 2
(`chains/hotpotqa/static` (Run O) and `chains/hotpotqa/static_r` (Run R)) — no changes
required." This is correct as a design claim. But the pre-launch checklist should explicitly
verify that `static_r/validate.py` is at the expected state (Amendment 4 applied: returns
all failures, not `failures[:10]`; formatter samples 10 randomly with NO_CACHE).

The code inspection confirms this: `static_r/validate.py` returns `(metrics, failures)` at
line 190 (all failures, not sliced), and the docstring's stale `failures[:10]` annotation is
the amendment residue. The code state is correct. But if a future commit modifies
`static_r/validate.py` between now and launch, Run R's failure signal would change without
a design amendment. The pre-launch checklist already verifies `[PROMPT FILES]` and dataset
length; it should also verify the failure-return behavior of `static_r/validate.py` by
checking that the formatter's random sampling is active.

**Severity**: Minor. The risk is low given that the current code state is correct and the
repository has version control. Recommendation: add to the pre-launch checklist for Run R:
"Verify `static_r/validate.py` returns all failures (not `failures[:10]`); verify formatter
uses `random.sample(failures, min(10, len(failures)))` with `cache_handler = NO_CACHE`
(Amendment 4 from cf0cfc1 must be active)."

**New Concern E: The consistency-check acceptance ranges for Runs Q and P (Gate A) have
lower bounds that may be too low and lack an empirical basis.**

Gate A sets:
- Run Q (fixed-600): gap acceptance range [2.0pp, 9.0pp]
- Run P (rotating-600): gap acceptance range [3.0pp, 15.0pp]

The lower bound of 2.0pp for Run Q is lower than the seed's intrinsic gap at gen 0 (2.7pp).
It is implausible that a fixed-600 run would produce a SMALLER gap than the seed's starting
gap after 50 generations of evolution — if anything, evolution typically inflates the gap
beyond the seed's intrinsic gap (K: 6.33pp vs seed: 2.7pp). A gap of 2.0pp at gen 50 would
require evolution to REDUCE the gap below the seed's starting point, which would itself be
a remarkable finding worth investigating rather than accepting as a normal outcome.

Similarly, the lower bound of 3.0pp for Run P has no empirical anchor — the rotating-600
regime has never been tested, but rotating-300 produced gaps of 8.67–13.67pp. A gap of
3.0pp for rotating-600 would mean rotating-600 outperforms fixed-300 (6.33pp) substantially,
which is a POSITIVE result that should trigger analysis rather than pass silently through
Gate A's consistency check.

**Severity**: Minor. The Gate A lower bounds should be set above the seed's intrinsic gap at
gen 0 (2.7pp). Recommendation: set lower bounds as Run Q [4.0pp, 9.0pp] and Run P [4.0pp,
15.0pp]. If a run produces a gap below 4.0pp, that is a positive anomaly worth investigating
as a potential measurement error (e.g., test set contamination, wrong val set used for the
final program) before declaring a POSITIVE result.

---

### Checklist Review (Revised Design)

**Hypothesis and Falsifiability**

- [x] H₀ is clearly stated for all three factorial comparisons (size, rotation, interaction)
- [x] H₁ is falsifiable and directional for all three comparisons
- [x] Primary metric is pre-specified and sufficient to test all three hypotheses
- [ ] Primary comparison for the experiment-level POSITIVE verdict is pre-registered

**Notes**: Three mechanistic hypotheses are pre-registered and make distinct predictions
about the 2×2 pattern. This is strong design. The gap is New Concern B: the design does not
state which comparison is the primary test for the experiment-level adoption decision.

**Confound Analysis**

- [x] All controlled variables are genuinely controlled across all four cells
- [x] The only difference across cells is problem.name (and therefore validate.py)
- [x] H_mapelites and the richer-failure-pool confound are acknowledged and named
- [x] Winner's curse directional bias in rotating runs is acknowledged with correct direction

**Statistical Validity**

- [x] N=1 per cell is justified with reference to the 2×2 consistency-check argument
- [x] No formal NHST attempted; effect-size classification is appropriate
- [x] POSITIVE threshold (5.0pp) is now consistent with the SE analysis
- [x] Multiple comparison concern acknowledged (six pairwise comparisons reported but
     not all treated as primary)

**Evaluation Protocol**

- [x] Test set identical across all four runs
- [x] Thinking mode and step_max_tokens identical across all four runs
- [x] Deterministic hash mechanism correctly described
- [x] Val EM cross-condition comparability limitation correctly stated

**Operational Risks**

- [x] Full mutation server pool acknowledged
- [ ] Primary comparison for POSITIVE verdict not pre-registered (New Concern B — Major)
- [ ] Gate A lower bounds may be too permissive for Runs Q and P (New Concern E — Minor)
- [ ] Interaction interpretation table incomplete for rotating-300 gap <= fixed-300 gap case
     (New Concern A — Minor)

---

### Required Changes Before Approval

1. **[Major, New Concern B]** Pre-register the primary comparison for the experiment-level
   POSITIVE verdict. The 2×2 design has six pairwise comparisons. A Phase 5 reader
   encountering multiple comparisons — some POSITIVE, some SUGGESTIVE, some NULL — needs a
   pre-specified hierarchy to determine which comparison drives the experiment-level verdict.
   Recommended formulation: "The primary pre-registered comparison for the experiment-level
   adoption verdict is Gate C (Run Q vs Run O: fixed-600 vs fixed-300), on the grounds that
   it isolates the sample-size effect without rotation confound. A POSITIVE Gate C verdict
   recommends adopting `static_600` as the new baseline val set. The comparison P vs O
   (rotating-600 vs fixed-300) is the secondary pre-registered comparison. The full 2×2
   pattern analysis (Gate B) is the mechanistic interpretation layer. These three layers
   must be reported in order; the adoption recommendation follows the primary comparison
   only." This hierarchy must appear in Section 2 (Hypotheses) and be reflected in the
   ordering of Gate B and Gate C in Section 10.

**Note on the three remaining minor concerns**: New Concerns A, C, D, and E are minor and
do not individually block approval. However, they should be addressed in revision. Specific
language:

- **New Concern A**: Add a row to the Gate B interpretation table for "gap_R <= gap_O
  (rotating-300 matches or beats fixed-300): H_winners_curse strongly supported at 300/1000;
  H_mapelites falsified. Investigate whether the MAP-Elites archive configuration in R differs
  from L/M/N sufficiently to explain the discrepancy."

- **New Concern C**: Extend the early-termination criterion for "Zero mutations" to also
  cover mutation server failure: "OR mutation stage timeout > 30 min for any run — diagnose
  mutation LLM server before continuing."

- **New Concern D**: Add to the pre-launch checklist for Run R: "Verify `static_r/validate.py`
  returns all failures (not sliced); verify formatter uses random sampling with NO_CACHE
  (Amendment 4, cf0cfc1, must be active)."

- **New Concern E**: Raise Gate A lower bounds for Run Q to [4.0pp, 9.0pp] and Run P to
  [4.0pp, 15.0pp]. Document that a gap < 4.0pp at gen 50 is a positive anomaly requiring
  verification before any POSITIVE verdict is recorded.

---

### Verdict

**[ ] APPROVED**

**[x] NEEDS REVISION** — one major concern; four minor concerns

**[ ] REJECTED**

**Reviewer notes**:

The 2×2 expansion is the correct response to the first review. It is not a minimal patch; it
is a genuine improvement in experimental structure. Five of the six required changes are
resolved correctly and completely. The deterministic-hash description is now accurate
throughout. The POSITIVE threshold is aligned with the SE analysis. H_mapelites is properly
pre-registered with testable predictions. The criterion inconsistency between Sections 4 and
10 is gone.

The one remaining major concern (New Concern B) is a consequence of the 2×2 expansion itself.
With six pairwise comparisons and three decision gates, the design needs a stated hierarchy
for which comparison drives the adoption verdict. Without this, a researcher choosing to
emphasize Run Q's Gate C POSITIVE while ignoring Run P's Gate B NULL — or vice versa — is
not acting dishonestly; they are simply choosing among pre-registered tests that the design
has left unranked. This ambiguity is not hypothetical: it will arise when the four gap values
are in hand and two comparisons point in different directions. The fix is a single sentence
in Section 2 establishing the primary comparison. It does not require redesign.

The four minor concerns (A, C, D, E) are documentation gaps, not design flaws. None
individually invalidates the experiment. Together they represent a modest list of cleanups
appropriate to include in the same revision pass.

I have no further structural objections. A revision addressing New Concern B and the four
minor items can return for final approval.

The science demands nothing less.

---

*Prof. Andrei Volkov*

---

## Third Review — v3 Evaluation

**Date**: 2026-03-05
**Reviewer**: Prof. Andrei Volkov
**Input**: `experiments/hotpotqa_val_gap/01_design.md` (revised v3, "second-review fixes")
**Prior review**: Second review above (NEEDS REVISION, 1 major + 4 minor concerns)

---

### Assessment of the Five Required Changes

**Fix 1 [Major, New Concern B]: Primary comparison hierarchy designated in Section 2**

RESOLVED — with one residual documentation precision issue noted below.

Section 2 now contains an explicit "Primary Comparison for Adoption Verdict" subsection
stating: "Primary comparison: Run Q vs. Run O (fixed-600 vs. fixed-300, Gate C) [...] is
sufficient to recommend adopting `static_600` as the new baseline, independent of Gates B
and D. Secondary comparison: Run P vs. Run O (rotating-600 vs. fixed-300, Gate B). [...]
A POSITIVE Gate B without Gate C is therefore insufficient to recommend rotating-600
adoption as the new default. [...] The full 2×2 pattern analysis (Gate B Step 2) is the
third layer — reported after Gates C and B."

The hierarchy is explicit and unambiguous. Gate C is designated the adoption criterion;
Gate B is secondary; the 2×2 pattern is mechanistic interpretation. Phase 5 is instructed
to report in this order. The major concern from the second review is resolved.

**Residual precision issue**: Gate B's decision table in Section 10 still lists its
POSITIVE category as "warrants adoption pending N >= 3 replication" without the Section 2
qualification. A researcher reading Gate B's table row in isolation would conclude that a
Gate B POSITIVE result recommends adoption. Section 2 says otherwise. The two are not in
logical conflict — Section 2 takes precedence as the pre-registered statement — but the
inconsistency between the table row's phrasing and the Section 2 hierarchy creates
unnecessary ambiguity for a Phase 5 analyst reading the gates directly. This should be
corrected in Phase 3 by adding a parenthetical to the Gate B POSITIVE row such as: "(for
Run P: establishes rotating-600 outperforms fixed-300; adoption requires Gate C POSITIVE
per Section 2 hierarchy)." This is a minor documentation issue, not a pre-registration
flaw.

**Fix 2 [Minor, New Concern A]: Interaction table covers gap_R <= gap_O**

RESOLVED. Gate B Step 2 now includes the row: "gap_R <= gap_O (rotating-300 matches or
beats fixed-300) — H_winners_curse strongly supported at 300/1000; H_mapelites falsified.
Unexpected — contradicts L/M/N empirical pattern. [...] Do not adopt rotating-300 based on
this result alone without replication at N >= 3." The row is present, the interpretation is
correct, and the replication requirement is appropriately noted. New Concern A is fully
resolved.

**Fix 3 [Minor, New Concern C]: Mutation server failure in early-termination criteria**

RESOLVED. Section 10 now contains two distinct criteria covering this failure mode:
(1) a combined criterion for "Zero mutations for 5+ consecutive generations, OR mutation
stage timeout > 30 min for any run" with explicit text that "run.py will not crash — it
will hang silently, and the generation counter may not advance" and instructions to
diagnose before continuing; and (2) a separate "Mutation server failure (server unreachable
> 30 min)" criterion with protocols for attempted reassignment and fallback to incomplete
factorial. The diagnostic distinction between selector bug and server failure is now
captured. New Concern C is fully resolved.

**Fix 4 [Minor, New Concern D]: Amendment 4 verification for Run R in Appendix A**

RESOLVED. Appendix A now includes a specific verification step for Run R: "verify
`static_r/validate.py` returns ALL failures with no `[:10]` cap — run `grep 'failures\\['
problems/chains/hotpotqa/static_r/validate.py` and confirm no slice is present in the
return statement; verify both formatter classes (`HotpotQAASIFormatter`,
`HotpotQAFailureFormatter`) use `random.sample(failures, min(10, len(failures)))` with
`cache_handler = NO_CACHE` (Amendment 4, cf0cfc1, must be active)." The specific grep
command and formatter-class verification are the correct level of specificity for a
pre-launch checklist. New Concern D is fully resolved.

**Fix 5 [Minor, New Concern E]: Gate A lower bounds raised**

PARTIALLY RESOLVED.

The second review's specific recommendation: "set lower bounds as Run Q [4.0pp, 9.0pp]
and Run P [4.0pp, 15.0pp]." The v3 response:

- Run R (rotating-300): [4.0pp, 15.0pp] — meets the requirement. Correct.
- Run P (rotating-600): [4.0pp, 15.0pp] — meets the requirement. Correct.
- Run Q (fixed-600): [3.0pp, 9.0pp] — does NOT meet the requirement. The recommendation
  was 4.0pp; the v3 implements 3.0pp. The design's own note says "a gap < 3.0pp at gen 50
  would be a positive anomaly requiring verification." This is accurate — but 3.0pp is only
  0.3pp above the seed's gen-0 intrinsic gap of 2.7pp. No gen-50 fixed-protocol run in this
  program has ever produced a gap below 6.33pp (Run K). A gap of 3.0–4.0pp at gen 50 would
  be historically unprecedented and should trigger investigation, not pass Gate A silently.
  The 3.0pp lower bound is technically above the seed's starting gap but provides almost no
  practical protection against anomalously positive results that might indicate a measurement
  error (e.g., wrong val set used for test evaluation, test-set leakage).
- Run O (fixed-300): [4.0pp, 11.0pp] — unchanged and correct.

I note this partial compliance. I will not block approval for this single remaining minor
issue; the reasoning follows below.

---

### Full-Document Scan: New Issues

**Scan result 1: Gate B "warrants adoption" language is inconsistent with Section 2
hierarchy (pre-registered under Fix 1 above).**

Gate B Step 1 POSITIVE row: "warrants adoption pending N >= 3 replication." Section 2
hierarchy: "A POSITIVE Gate B without Gate C is [...] insufficient to recommend
rotating-600 adoption." The Section 2 text is binding and takes precedence over table
phrasing, so this is a documentation precision issue rather than a pre-registration
conflict. Recommend adding a parenthetical qualifier to the Gate B POSITIVE row in
Phase 3.

**Scan result 2: Section 8's sign convention for rotation main effects is asymmetric and
may confuse Phase 5 analysis.**

Section 8 defines `delta_rot_300 = gap_O − gap_R` and `delta_rot_600 = gap_Q − gap_P`.
Under this convention, a POSITIVE delta_rot means the fixed run has a larger gap —
i.e., rotation helps. Under all three mechanistic hypotheses, delta_rot_300 is expected to
be NEGATIVE (rotation inflates the gap). Gate B's NEGATIVE category label reads "Gap
inflation; treatment is worse than control." For rotation comparisons, treatment is the
rotating run; a negative delta (fixed > rotating is false, i.e., gap_R > gap_O) means
the rotating treatment is worse — which maps correctly to Gate B's NEGATIVE label. The
convention is internally consistent.

However, the asymmetry between size comparisons (POSITIVE delta = treatment is better in
the natural direction) and rotation comparisons (NEGATIVE delta = treatment is worse in the
expected direction) creates a cognitive hazard when reading a table of six delta values
in Phase 5. The design should add a sentence to Section 8 noting: "For rotation main
effects, the expected direction under all three mechanistic hypotheses is a NEGATIVE
delta (gap_fixed < gap_rotating, i.e., rotation inflates the gap). Gate B's NEGATIVE
classification therefore represents the expected outcome, not a failure." This is a
documentation clarity note; it does not affect the pre-registration validity.

**Scan result 3: The Section 2 threshold rationale understates the SE for the primary Gate
C comparison.**

The rationale states: "5.0pp POSITIVE actionability threshold — approximately > 1 SE for
the fixed-300 gap." SE(gap_fixed-300) ≈ 4.0pp is computed for a single run on n=300 val
and n=300 test. The Gate C comparison is delta = gap_O − gap_Q. If gap_O and gap_Q are
measured on independent programs (which they are — different runs), then assuming
independence: SE(delta_size_fixed) ≈ sqrt(SE(gap_O)² + SE(gap_Q)²) ≈ sqrt(4.0² + 3.47²)
≈ 5.3pp. The 5.0pp POSITIVE threshold is therefore slightly below 1 SE for the designated
primary comparison (Gate C), not "approximately > 1 SE." The design correctly acknowledges
throughout that N=1 is a screening study and the threshold is a practical filter rather
than a significance level, so this understatement in the rationale does not invalidate the
threshold. But "approximately > 1 SE" should be "approximately 1 SE" or the rationale should
explicitly distinguish between the SE for a single-run gap and the SE for the between-run
difference.

This is a minor precision issue. It does not affect the threshold value, the decision gates,
or any pre-registered comparison.

---

### Checklist

- [x] Fix 1: Primary comparison hierarchy present and unambiguous in Section 2
- [x] Fix 2: Interaction table includes gap_R <= gap_O row with correct interpretation
- [x] Fix 3: Mutation server failure covered in early-termination criteria
- [x] Fix 4: Amendment 4 verification present for Run R in Appendix A
- [~] Fix 5: Gate A lower bounds partially raised (R and P correct; Q at 3.0pp, not 4.0pp)
- [x] No new pre-registration inconsistencies introduced by v3 changes
- [x] Six pairwise comparisons reportable without implicit cherry-picking (hierarchy stated)
- [x] DB assignments confirmed available (4, 5, 6, 7 — no conflict with prior or reserved)
- [x] All controlled variables identical across four cells
- [x] Thinking mode, step_max_tokens, pipeline, prompts consistent across all runs
- [x] Deterministic hash mechanism correctly described throughout

---

### Verdict

**[x] APPROVED WITH NOTES**

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**:

The v3 design is ready to proceed to Phase 3. All four minor fixes are completely resolved.
The one major fix (primary comparison hierarchy) is resolved in substance: Section 2
contains a clear, binding pre-registration of Gate C as the adoption criterion. The residual
documentation inconsistency between Section 2 and Gate B's table row is a phrasing issue
that can be corrected in Phase 3 without requiring a fourth review cycle.

Fix 5 (Gate A lower bounds) was partially implemented. Run Q's lower bound at 3.0pp rather
than 4.0pp is a minor concern. I accept it conditionally: the design's own note flags gaps
below 3.0pp as anomalies requiring verification before a POSITIVE verdict, and any gap in
the 3.0–4.0pp range that drove a POSITIVE Gate C result would still face the N >= 3
replication requirement. The safety net is adequate even if the tripwire is set 1pp lower
than recommended.

Three documentation precision issues were identified in the full-document scan: the Gate B
table's "warrants adoption" phrasing (minor conflict with Section 2 hierarchy), the sign
convention note for rotation main effects in Section 8 (cognitive clarity), and the SE
rationale understatement for the Gate C comparison. None affects pre-registration validity.
All three should be addressed as Phase 3 amendments if the researcher chooses to revise
the analysis protocol document; none requires returning to review.

This is now a well-constructed screening design for a constrained compute environment.
The factorial structure recovers causal decomposition that the original 2-cell design
lacked. The three mechanistic hypotheses are pre-registered with testable predictions.
The decision hierarchy is explicit. The confounds are named. The failure modes from prior
experiments (repr-contamination, prompts_dir silent failure, winner's curse measurement
bias) are specifically checked in the pre-launch protocol.

Proceed to Phase 3.

The science demands nothing less.

---

*Prof. Andrei Volkov*
