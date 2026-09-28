# ML Research Methodologist — Agent Memory

Methodology insights only. Experiment results live in `experiments/INDEX.md`. Cross-cutting patterns live in `experiments/PATTERNS.md`. Task knowledge lives in `experiments/<task>/CONTEXT.md`.

---

## Methodology Lessons

- **Always pair feedback with fitness function changes** — feedback alone is NULL (-0.18pp on HoVer). The fitness function is the stronger lever.
- **Topology-level interventions dominate prompt-level** — 3 prompt co-evolution experiments across 2 tasks yielded 0 positive results. Structure > content.
- **Soft fitness enables smoother optimization** — fractional scoring (gold_found/3) provides gradient signal that discrete (0/1) does not. Consider soft variants for any binary metric.
- **Val-test gap is systematic** — 4-8pp gaps observed across many HoVer experiments. Soft fitness exacerbates this (26.47pp in co-evolution-bus). Always report and monitor gap, but don't optimize for it.

## Design Process Notes

- **Pre-commit diagnostics for novel mechanisms** — e.g., trial dilution threshold, prompt fitness gap, champion emergence rate. Design these before launch, not ad-hoc during monitoring.
- **One IV at a time** — bundled interventions (colbert_feedback: ColBERT + rich feedback) prevent causal attribution. Exception: deliberate factorial designs with N≥2 per cell.
- **Read Literature Scout brief before designing** — external baselines and related work prevent wasted experiments.

## Research Direction Rankings (as of 2026-04-08)

1. Topology interventions (strongest evidence, +6-8pp effects)
2. Fitness function engineering (moderate evidence, +2-3pp effects)
3. Adversarial co-evolution (early stage, asymmetric results)
4. Memory mechanisms (suggestive only, needs stronger design)
5. ~~Prompt co-evolution~~ — CLOSED, do not pursue
