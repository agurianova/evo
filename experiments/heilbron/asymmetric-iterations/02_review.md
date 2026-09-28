# Adversarial Review: heilbron/asymmetric-iterations (Redesign)

**Date**: 2026-04-12
**Input**: `experiments/heilbron/asymmetric-iterations/01_design.md`
**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary agent)
**Review round**: 3 (re-review of revisions addressing Round 2 concerns)

---

## Round 2 Recap

Round 2 issued NEEDS REVISION with 2 Critical, 4 Major, 1 Minor concerns. Three items (Critical #1 yaml/plan mismatch, Minor #6 stopping rule, Minor #7 DB allocation) were deferred to later skill steps (experiment.yaml and 03_plan.md updates). Five items were to be addressed in the design document itself. This Round 3 review evaluates those five.

---

## Re-check of Addressed Concerns

### Concern 2 (was CRITICAL): Pipeline does not exist

**Round 2**: The design referenced `pipeline=adversarial_asymmetric` and log lines (`[InnerIteration]`, `[CollectiveEval]`, `[CompositionInjection]`) that no existing code produces, without acknowledging the implementation scope.

**Resolution in revision**: The design now includes Section 1a ("Implementation Scope"), which explicitly enumerates five new components required:

1. Inner iteration loop within D's evaluation
2. Source code injection stage (G to D)
3. Composition injection stage (D to G, Arm A)
4. Gradient-in-prompt mutation prompt modification (Arm C)
5. Persistent archive semantics for D

The section concludes with an explicit statement: "The log line patterns in Section 13 [...] must be implemented in the new pipeline code. They are specifications for what the implementation must produce, not references to existing code."

Section 13 now includes a mandatory 3-gen smoke test protocol with nine pass criteria covering each novel mechanism (inner iterations, source code access, persistent archive, collective evaluation, generation sync, no archive re-evaluation, composition injection, gradient-in-prompt, and crash-freedom). The smoke test runs on dedicated Redis DBs separate from production.

**Verdict on this concern**: RESOLVED. The implementation scope is clearly acknowledged, and the smoke test protocol provides a credible pre-launch gate. The nine pass criteria are specific, observable, and cover all novel mechanisms. This is well done.

---

### Concern 3 (was MAJOR): archive_reeval default

**Round 2**: Risk of silent `archive_reeval: true` from pipeline inheritance, which would confound results given the confirmed NEGATIVE effect from adversarial-dynamic-updates.

**Resolution in revision**: Section 13 now includes two new verification rows:

1. "`--cfg job` shows `pipeline_builder.archive_reeval: false` in the resolved config (not just a top-level override that may not be wired through)"
2. "No `[ArchiveReeval]` log lines appear during the 3-gen smoke test"

The first check catches silent YAML wiring failures (the override exists but is not plumbed through). The second check catches runtime activation regardless of config resolution. Together, they form a defense-in-depth verification.

**Verdict on this concern**: RESOLVED. The two-layer check (config resolution + runtime log absence) is exactly what I requested. The parenthetical note about "not just a top-level override" demonstrates awareness of the specific failure mode.

---

### Concern 4 (was MAJOR): Quality confound in Arm A vs Arm C comparison

**Round 2**: The design acknowledged the volume confound (Arm A gets more candidates) but not the quality confound (Arm A's injected candidates are pre-vetted through D's evaluation pipeline, systematically higher quality than random mutations).

**Resolution in revision**: Section 9 Confound #3 now reads (in relevant part):

> "Moreover, Arm A's injected candidates have been pre-selected through D's evaluation pipeline: they are D's *best* improvements, already validated against D's archive and shown to improve upon G's current programs. [...] The Arm A vs Arm C comparison can therefore determine whether 'Lamarckian transfer (quantity + quality confounded) differs from textual gradient' -- but cannot isolate the injection mechanism per se from the extra pre-vetted candidate volume."

Section 2 (cross-arm comparison table) now includes a caveat:

> "**Caveat**: Arm A's injected candidates are pre-vetted through D's evaluation pipeline and represent additional candidate volume; this comparison cannot isolate the injection mechanism from the combined quantity + quality advantage (see Section 9 Confound #3)."

**Verdict on this concern**: RESOLVED. The quality confound is now explicitly named alongside the volume confound, and the interpretation table in Section 2 flags the limitation directly. A follow-up experiment (injecting random D programs rather than D's best) is suggested as the path to isolating the quality selection effect. This is honest and precise.

---

### Concern 5 (was MAJOR): Baseline information access unspecified

**Round 2**: The design did not clarify what D currently sees about G in the baseline pipeline (adversarial_coevo), making it impossible to assess whether the "white-box access" treatment is genuinely novel.

**Resolution in revision**: Section 3 now includes a "Baseline information access" subsection that specifies:

- In baseline (adversarial_coevo, as used in baseline-repro), D receives opponent information exclusively via `FetchOpponentResultsStage`
- This stage executes G's `entrypoint()` in a subprocess and returns **output arrays** (11x2 point configurations)
- D's `evaluate.py` receives these as `opponent_results` and computes fitness as mean improvement
- D never sees G's source code -- it sees only G's output (point placements)
- There is no `OpponentFeedbackStage` in the baseline heilbron pipeline
- The redesign changes this to full `solve()` source code access -- a qualitative change in information architecture

**Verdict on this concern**: RESOLVED. The baseline information channel is now clearly specified (output arrays only, no source code, no feedback stage). The contrast with the new design (full source code as dynamic task description) is unambiguous. This makes the novelty of the treatment assessable.

---

### Concern 8 (was MAJOR): Sync hook interaction with inner iterations

**Round 2**: The design did not specify how D's K=5 inner iterations interact with the generation counter and the `MainRunSyncHook`. If inner iterations increment `engine:total_generations`, the pair would desynchronize catastrophically.

**Resolution in revision**: Section 5 now includes a "Inner iteration / generation counter / sync hook interaction" subsection with five explicit invariants:

1. D's inner iterations do NOT increment `engine:total_generations`
2. Only D's outer generation completion increments the counter
3. `MainRunSyncHook` fires on outer generation boundaries only
4. G blocks during D's entire inner loop and resumes when D's outer counter advances
5. Verification: G and D `engine:total_generations` must remain within 1 at all times; verify at gen 5 during smoke test

The smoke test protocol (Section 13) includes "Generation sync: G and D `engine:total_generations` differ by at most 1 at gen 3" as a pass criterion.

**Verdict on this concern**: RESOLVED. The five invariants are specific, testable, and address the exact failure mode I identified. The causal chain is clear: inner iterations are internal to D's evaluation, do not touch the generation counter, and therefore do not trigger the sync hook prematurely. The smoke test check at gen 3 would catch a violation immediately (D would show gen 15 vs G's gen 3 if inner iterations leaked into the counter).

---

## Deferred Concerns (not re-checked here)

The following concerns were deferred to later skill steps (experiment.yaml and 03_plan.md updates) and are expected to be resolved when those artifacts are updated:

- **Concern 1 (CRITICAL)**: experiment.yaml and 03_plan.md describe old experiment -- will be updated in Steps 5-6
- **Concern 6 (MINOR)**: Stopping rule inconsistency between design doc and experiment.yaml -- will be resolved when yaml is refreshed
- **Concern 7 (MINOR)**: DB allocation mismatch -- will be resolved when yaml is updated

These do not block approval of the design document. They are implementation prerequisites that must be completed before launch.

---

## Assessment of Revised Design

The revised design addresses all five concerns that were within scope for this revision. The additions are substantive, not cosmetic:

- **Section 1a** transforms the design from one that could be mistaken for a config-only change into one that honestly acknowledges substantial implementation work and provides a credible pre-launch gate (9-criterion smoke test).
- **The archive_reeval verification** employs defense-in-depth (config resolution + runtime log absence), which is the correct approach for a known silent-failure mode.
- **The quality confound acknowledgment** is refreshingly honest about what the Arm A vs Arm C comparison can and cannot tell us, and names the follow-up needed to isolate the mechanism.
- **The baseline information access subsection** closes the gap that made treatment novelty unassessable.
- **The sync hook invariants** are the most critical addition. They specify the single most dangerous implementation detail in language precise enough to serve as an implementation specification.

I have no new concerns arising from the revisions. The changes do not introduce new confounds or weaken existing controls.

---

## Verdict

**[x] APPROVED**

**[ ] NEEDS REVISION**

**[ ] REJECTED**

**Reviewer notes**: All five concerns addressed in this revision are resolved to my satisfaction. The design document now accurately represents the implementation scope, specifies the critical inner-iteration/sync-hook interaction, closes the baseline information gap, honestly acknowledges the quality confound in the cross-arm comparison, and provides defense-in-depth verification for archive_reeval. The three deferred concerns (experiment.yaml/03_plan.md mismatch, stopping rule inconsistency, DB allocation) must be resolved before launch but do not affect the design's scientific validity.

This is a well-constructed compound-intervention experiment that honestly acknowledges what it can and cannot conclude. The dual interpretation framework (Constructor actual_fitness for effectiveness, Improver acceptance rate for stagnation diagnosis) extracts maximum information from N=2/arm. The smoke test protocol is a model for future experiments requiring novel pipeline code.

Proceed to experiment.yaml and 03_plan.md updates (deferred Concerns 1, 6, 7), then implementation.

*The science demands nothing less.*
