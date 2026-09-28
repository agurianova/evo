# PR #69 — NLP-specific mutation prompts for HotpotQA chain evolution

**Status**: 🟢 Complete (Phase 5 — results analysis done)
**Branch**: `exp/hotpotqa-nlp-prompts`
**Experiment**: `hotpotqa_nlp_prompts`
**Dates**: Launched 2026-03-03 · Completed 2026-03-05
**Archives**: https://github.com/KhrulkovV/gigaevo-core-internal/releases/tag/exp%2Fhotpotqa_nlp_prompts

---

## Hypothesis

**H₁**: NLP-chain-specific mutation prompts (domain-specific insights/lineage/mutation system rewriting) improve test EM on HotpotQA beyond the ddce37b4 seed baseline (60.0%) within 50 generations.

---

## Design

| Run | Label | Prompts | Val Set | DB | Chain Server |
|-----|-------|---------|---------|-----|--------------|
| K | Control | `default` | fixed-300 (`static`) | 0 | 10.226.17.25:8001 |
| L | NLP-1 | `hotpotqa` | rotation-300 (`static_r`) | 1 | 10.226.17.25:8000 |
| M | NLP-2 | `hotpotqa` | rotation-300 (`static_r`) | 2 | 10.225.185.235:8001 |
| N | NLP-3 | `hotpotqa` | rotation-300 (`static_r`) | 3 | 10.225.185.235:8000 |

All runs: seed=ddce37b4, `pipeline=hotpotqa_asi`, `num_parents=1`, `max_elites=8`, `max_mutations=8/gen`, `max_generations=50`, random failure sampling (Amendment 4).

**Compound treatment**: NLP prompts AND rotation val set changed simultaneously between K and L/M/N.

---

## Results

| Run | Best Gen | Val EM (frontier) | Test EM | Val-Test Gap |
|-----|----------|-------------------|---------|--------------|
| K (control) | 43 | 66.33% | **60.00%** | +6.33pp |
| L (NLP-1) | 40 | 68.00% | **59.33%** | +8.67pp |
| M (NLP-2) | 20 | 70.67% | **57.00%** | +13.67pp |
| N (NLP-3) | 26 | 69.67% | **61.00%** | +8.67pp |

| Metric | Value |
|--------|-------|
| Treatment mean test EM | **59.11%** |
| Control test EM | 60.00% |
| Seed test EM (gen 0) | 60.00% |
| GEPA target | 62.3% |
| Treatment − control | −0.89pp |

---

## Gate Verdicts (pre-registered)

| Gate | Criterion | Result | Verdict |
|------|-----------|--------|---------|
| 1 — vs. seed | Treatment mean > 62.0% | 59.11% | **NULL** |
| 2 — vs. control | Treatment − control ≥ 4.2pp | −0.89pp | **NULL** |
| 3 — control validity | K within Run E ±2.4pp | 60.0% ✓ | **VALID** |
| 4 — val-test gap | Treatment gap < 7pp | 8.67–13.67pp | **CONCERNING** |

**Overall: NULL result. H₁ not supported.**

---

## Key Findings

1. **NULL at all gates.** Treatment mean (59.11%) is indistinguishable from the seed (60.0%) and control (60.0%). No run exceeded GEPA (62.3%).

2. **Val-test gap explosion on treatment.** Rotation val set inflated frontier val EM by 2–5pp relative to control with zero corresponding test EM gain. M's 13.67pp gap is the largest in GigaEvo history on HotpotQA. Run G (P1×P2, rotation-only) showed a similar pattern (9.7pp gap). This is now a validated finding: **rotation val set (static_r at 300/1000) inflates val EM without improving test generalisation.**

3. **Compound confound limits causal attribution.** Since NLP prompts and rotation val set changed simultaneously, we cannot determine whether (a) NLP prompts are ineffective, (b) rotation val set degraded selection, or (c) both. The correct conclusion is: the compound treatment failed, not that NLP prompts specifically failed.

4. **Programme length inflation.** One L programme (#2 by val) exceeded the 16,384 token context window (8,193 input + 8,192 max_output). NLP-framed prompts appear to encourage longer chain instructions. **Chain servers must be restarted with larger context window before next experiment.**

5. **Early stagnation.** All treatment runs reached 0% archive acceptance by gen 30–43. Best programmes found at gen 20–43, not 50. Evolution exhausted search space quickly.

---

## Pre-registration Amendments

| # | Filed | Summary |
|---|-------|---------|
| 1 | 2026-03-03 | `pipeline=standard` → `pipeline=hotpotqa_asi` (repr-contamination fix) |
| 2 | 2026-03-03 | `step_max_tokens` unified to 8192 |
| 3 | 2026-03-04 | Third launch is first with all NLP prompts active (prompts_dir bug) |
| 4 | 2026-03-04 | Random failure sampling in formatters (Amendment 4) — fourth launch valid |

---

## Reviewer Assessments

**Dr. Elena Voss (Analyst)**: NULL verdict confirmed across all gates. Rotation val set inflation is the strongest mechanistic finding — stronger than the prompt experiment itself. Next action per Gate 5 decision matrix: **proceed to P3 crossover** (`num_parents=2`, fixed val, `prompts=default`).

**Prof. Andrei Volkov (Adversarial Review)**: "INTERPRETABLE NULL — with significant qualification on causal attribution." Three major concerns: (1) compound confound makes prompt-specific attribution impossible; (2) 62% power means a real ≤3pp effect could easily be missed; (3) historical control (Run E) was repr-contaminated, so effective control is K only. Full review: `experiments/hotpotqa_nlp_prompts/results_review.md`.

---

## Next Steps (Gate 5 Decision Matrix)

Pre-registered action for **NULL/NULL** (Gate 1 NULL, Gate 2 NULL):

> *"Move to P3 crossover (structural intervention). Accept prompt-only ceiling."*

**Immediate actions before P3 launch**:
- [ ] Archive K/L/M/N runs (`tools/experiment/archive_run.sh --upload` for all 4 DBs)
- [ ] Restart chain servers with `--max-model-len 32768` (current 16384 too small)
- [ ] P3 design: `num_parents=2` vs `num_parents=1`, `pipeline=hotpotqa_asi`, `prompts=default`, **fixed val** (`static`), equalised throughput (`max_mutations=8` both cells)

---

## Analysis Documents

- `experiments/hotpotqa_nlp_prompts/05_results.md` — Full Phase 5 results (Dr. Voss)
- `experiments/hotpotqa_nlp_prompts/results_review.md` — Adversarial review (Prof. Volkov)
- `docs/plans/2026-03-03-nlp-prompts-experiment.md` — Pre-registration and amendments

---

🤖 Analysis by Claude Code / Dr. Elena Voss / Prof. Andrei Volkov
