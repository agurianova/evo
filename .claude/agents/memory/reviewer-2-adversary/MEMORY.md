# Reviewer-2 — Agent Memory

Proactive review patterns only. Experiment results live in `experiments/INDEX.md`. Platform failure modes and recurring flaws live in `experiments/PATTERNS.md`.

---

## Review Calibration Notes

- **Contemporaneous controls are mandatory** — shared-baseline designs (comparing to historical Cell C) introduce temporal confounds. Always require a fresh control cell.
- **`--cfg job` is the ground truth** — never trust experiment.yaml overrides without verifying they appear in the Hydra config dump. Silent fallback is the #1 GigaEvo confound.
- **Check metrics.yaml prompt parity** — if treatment and control use different problem variants, `include_in_prompts: true` on extra metrics creates a hidden IV. Caught this in hover/dynamic-topology.
- **Best-by-val selection bias** — selecting the top program by validation fitness and evaluating on test inflates reported effects. Acknowledge in every design.

## Critique Patterns

- **MDE formula**: Designs consistently omit the t_beta power term. True MDE is ~1.4x the reported value at N=2. Flag every time until template is fixed.
- **Wave allocation**: Check that treatment and control are balanced within each wave, not just overall.
- **Server assignment**: Persistent server state (GPU memory, process residue) can correlate with condition if not randomized.

## What I Don't Review (with N=2-4)

- Statistical test selection (underpowered regardless)
- Power calculations (decorative at this N)
- Multiple comparison corrections (not enough data)
- Confidence interval format (report magnitude and consistency instead)
