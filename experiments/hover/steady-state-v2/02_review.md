# Reviewer 2 -- Adversarial Review

**Experiment**: hover/steady-state-v2
**Date**: 2026-03-27

## Verdict: APPROVED (with notes)

## Issues Found

**1. Compound treatment confound -- engine + scheduling bundled (MAJOR)**

The treatment combines two independent changes: `evolution=steady_state` and `scheduling=lpt`. The design acknowledges this (Section 3) and argues it is deliberate because LPT was designed to fix steady-state tail latency. This is acceptable for an engineering validation experiment, but it weakens the scientific interpretation: if the treatment is inferior, you cannot determine whether the engine or the scheduler is responsible. If the treatment is non-inferior, you cannot determine whether LPT is load-bearing or inert.

The argument that "separating them would require a 2x2 factorial" is correct but understates the alternative: a 3-cell design (generational+FIFO, steady-state+FIFO, steady-state+LPT) at N=2 each (6 runs total) would isolate LPT's contribution while keeping the generational+FIFO baseline. This would use DBs 3-8, which are available. Granted, 6 concurrent runs on the shared cluster increase contention, so the pragmatic case for 4 runs is defensible.

**Disposition**: Not fatal. The design is transparent about this limitation and commits to a follow-up if treatment is non-inferior. Acceptable for an engineering validation.

**2. `max_in_flight` changed from 8 (v1) to 5 (v2) without justification (MINOR)**

Section 5 lists `max_in_flight = 5` with the note "Steady-state config default; controls backpressure." V1 used `max_in_flight = 8` (matching `max_mutations_per_generation`). This is a silent parameter change between v1 and v2. If v2 treatment is slower or faster than v1 treatment, this parameter change is a candidate explanation. The design should document why 5 was chosen over 8 and whether this was tested.

**Disposition**: Not fatal, but add a sentence to Section 5 justifying the choice. If 5 is the new code default, state that. If it was tuned, state based on what evidence.

**3. MDE analysis honestly admits likely inconclusiveness at N=2 (NOTE -- positive)**

The MDE analysis is refreshingly honest: at conservative SD = 1.5pp, the 90% CI half-width (4.38pp) exceeds the non-inferiority margin (3.0pp), making Wave 1 likely inconclusive. The pre-committed extension protocol (Wave 2 to N=3) is well-defined with a clear trigger condition. This is good experimental practice.

However, the "optimistic" scenario (SD ~ 0.63pp, CI half-width ~ 1.84pp) relies on the HoVer baseline inter-run SD, which was measured under different conditions (generational engine on old infrastructure). The new shared-infrastructure setup may introduce additional variance. The design should not lean too heavily on the optimistic scenario.

**Disposition**: Acceptable. The extension protocol handles the likely outcome.

**4. Wall-time comparison protocol relies on interpolation -- method unspecified (MINOR)**

Section 8 states: "At wall time T, interpolate fitness for each run." The interpolation method is not specified. For fitness trajectories that are step functions (fitness only changes when a new best program is found), linear interpolation between jumps may be misleading. The appropriate method is last-observation-carried-forward (LOCF): at time T, the fitness is the best value achieved before or at T.

**Disposition**: Specify LOCF interpolation in the protocol. This is a minor documentation fix.

**5. experiment.yaml is still a template -- not yet populated (MINOR)**

The `experiment.yaml` file contains placeholder values (`<task>/<name>`, `<metric>`, empty `runs:` list). This must be populated before the experiment transitions from "preregistered" to "implemented." Not a design flaw, but noted for the implementation phase.

**Disposition**: Fill during `/experiment-implement`.

**6. LiteLLM proxy as single point of failure -- invalidation criterion may be too lenient (MINOR)**

The stop criteria (Section 10) invalidate a run if "LiteLLM proxy is down for >4 consecutive hours." Since all 4 runs share the proxy, a proxy outage affects all runs equally -- but 4 hours of stalled evolution mid-run could introduce systematic bias (e.g., stale archive effects in steady-state are asymmetric with generational). A shorter threshold (e.g., 2 hours) or a requirement that total proxy downtime across the run stays below some fraction of wall time would be more conservative.

**Disposition**: Not fatal. The symmetric-impact argument is reasonable. Consider tightening to 2 hours.

**7. No smoke test mentioned in design (MINOR)**

V1 explicitly mentioned a smoke test (gen 3) as critical before full launch. V2 does not mention a smoke test, despite introducing a new scheduling component (LPT) on new infrastructure. The `experiment.yaml` template has a `smoke_test` section, so the mechanism exists.

**Disposition**: Add a smoke test requirement to the design. LPT + LiteLLM proxy + steady-state is a new combination that warrants a 2-3 generation smoke test before committing to 25 generations.

**8. N >= 2 per cell (PASS)**

N=2 per cell with a pre-committed extension to N=3. Meets the hard requirement.

**9. Treatment verification is thorough (NOTE -- positive)**

Four independent verification checks (log pattern, Hydra cfg engine target, Hydra cfg scheduling target, absence checks on controls). This is more thorough than v1 and covers the new LPT scheduling component. Well done.

**10. Problem variant changed from v1 without explicit justification (MINOR)**

V1 used `chains/hover/full` (dynamic topology). V2 uses `chains/hover/static` (canonical). The design notes that results are "NOT directly comparable to v1" (Section 1), but does not explain why the variant changed. If the goal is to validate the steady-state engine in the simplest possible setting, `static` is the right choice -- but this should be stated explicitly.

**Disposition**: Add one sentence to Section 1 or 5 explaining why `static` was chosen over `full`.

## Verdict Justification

The design is methodologically sound for an engineering validation experiment. The core structure -- non-inferiority test, N=2 with pre-committed extension, shared infrastructure eliminating host confounds, dual metrics (generation-count + wall-time) -- is well-reasoned and addresses the key lessons from v1.

The compound treatment (engine + scheduling) is the most significant weakness, but the design is transparent about it and commits to a follow-up. The remaining issues are documentation gaps (interpolation method, `max_in_flight` justification, variant choice rationale, smoke test) that should be addressed before implementation but do not require redesign.

## Required Changes Before Phase 3

1. Add justification for `max_in_flight = 5` vs v1's 8 (Issue 2)
2. Specify LOCF interpolation for wall-time comparison (Issue 4)
3. Add smoke test requirement (Issue 7)
4. Add one sentence explaining why `chains/hover/static` was chosen over `chains/hover/full` (Issue 10)

APPROVED. Address items above before proceeding to Phase 3 (plan).
