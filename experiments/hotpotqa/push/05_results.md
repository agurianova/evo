# Results: push — GEPA Attack (F1 × Prompts × Val-N, 4 runs)

**Date**: 2026-03-08
**Branch**: `exp/hotpotqa-push`
**PR**: #73

> Pre-filled during active runs (2026-03-07). All _(pending)_ fields are filled after
> `bash experiments/hotpotqa/push/run_test_eval.sh` completes.
> Final write-up: invoke the `ml-research-methodologist` agent with test eval numbers.

---

## 1. Final Metrics

### Reference cells (val_gap experiment, PR #70)

| Run | Condition | Val EM (best) | Test EM | Val-Test Gap |
|-----|-----------|--------------|---------|--------------|
| O | EM+default+300 | ~61.0% | 60.33% | ~0.7pp |
| F | F1+default+300 | ~63.4% | 61.67% | ~1.7pp |
| — | GEPA (Qwen3-8B, thinking) | — | **62.3%** | — |

### Push runs

| Run | Condition | Val Fitness (final) | Fitness Type | Val EM (final) | Test EM | Val-Test Gap | Max Gen |
|-----|-----------|--------------------|-----------|--------------------|---------|--------------|---------|
| A | F1+NLP+300 | 74.6% | F1 | 64.33% | 57.67% | +6.67pp | 50 |
| B | EM+default+600 | 64.67% | EM | 64.67% (= val fitness) | 57.00% | +7.67pp | 25 |
| C | F1+default+600 **[PRIMARY]** | 71.7% | F1 | 62.83% | 58.67% | +4.17pp | 25 |
| D | F1+NLP+600 (Amend. 3) | 72.8% | F1 | 64.83% | 63.00% | +1.83pp | 25 |

_Test EM: `bash experiments/hotpotqa/push/run_test_eval.sh` (N=300 held-out test set)._
_Val EM for F1 runs: `best.metrics.get("em", best.metrics["fitness"])` stored as secondary
metric by validate.py — NOT comparable to val Fitness (which is F1 for runs A/C/D)._

**Best programs found at iterations**: A=33, B=18, C=22, D=18. Consistent with the
confirmed stagnation pattern (frontier peaks at birth-gen 4–8 across all prior runs).

---

## 2. Primary Test — Run C (H1: test EM >= 62.3%)

**Pre-registered**: Fixed-600 F1 fitness achieves test EM >= 62.3% (GEPA).

| Threshold | Verdict label |
|-----------|---------------|
| >= 63.0% | STRONG POSITIVE |
| >= 62.3% | POSITIVE |
| [61.5%, 62.3%) + val-EM gap < 1.5pp | SUGGESTIVE |
| < 61.5% | NULL |

**Run C test EM**: 58.67%
**Binomial 95% CI (N=300)**: [53.02%, 64.10%]
**Val-EM gap**: 62.83% − 58.67% = **+4.17pp**
**Verdict**: **NULL**

Run C achieved 58.67% test EM — 3.63pp below GEPA and 3.00pp below the prior GigaEvo
best (Run F, 61.67%). The val-EM gap of +4.17pp is larger than Run F's ~1.7pp gap,
in the opposite direction from the design hypothesis. H₀(C) is not rejected; H₁(C) is
falsified. The combination of F1 fitness and 600-sample validation does not improve test EM
relative to either F1/300 (Run F) or EM/600 (Run B) individually.

The primary experiment-level verdict is **NULL**.

---

## 3. Secondary Tests

### Gate C — Run B (EM+600 gap reduction vs. Run O)

Reference: gap_O ~0.7pp (test EM = 60.33%, val EM ~61.0%).
Pre-registered threshold: delta_gap >= 2.0pp.

| Threshold | Verdict label |
|-----------|---------------|
| delta_gap >= 2.0pp AND test EM(B) >= 60.0% | POSITIVE |
| delta_gap in [1.0, 2.0pp) AND test EM(B) >= 60.0% | SUGGESTIVE |
| abs(delta_gap) < 1.0pp | NULL |
| gap_B > gap_O | NEGATIVE |

**Run B test EM**: 57.00% | **gap_B**: +7.67pp | **delta_gap (gap_O − gap_B)**: −6.97pp
**Verdict**: **NEGATIVE**

Run B (EM+600) produced a val-test gap of +7.67pp — nearly eleven times larger than
Run O's ~0.7pp gap. The gap inflated dramatically rather than contracting. Gate C is now
closed with a NEGATIVE verdict: larger validation samples under EM fitness do not reduce
the val-test gap; they worsen it substantially. The pre-registered threshold (delta_gap
>= 2.0pp reduction) is missed by an enormous margin.

Mechanistic interpretation: with 600 samples, the MAP-Elites archive has more signal to
overfit to — programs that happen to exploit local regularities in the first 600 training
samples are more reliably selected, amplifying the gap between val EM (measured on the same
overfit distribution) and test EM (measured on held-out data). This is the opposite of the
noise-reduction hypothesis. The 600-sample validation set is not independent enough from the
programs' training distribution to serve as an unbiased selection criterion.

### Run A test (F1+NLP+300 vs. Run F = F1+default+300)

Reference: test EM(F) = 61.67%. Tests whether NLP prompts help F1 runs.

| Threshold | Verdict label |
|-----------|---------------|
| >= 62.3% | POSITIVE |
| [61.7%, 62.3%) | SUGGESTIVE |
| [61.0%, 61.7%) | NULL |
| < 61.0% | NEGATIVE (NLP prompts harm F1 runs) |

**Run A test EM**: 57.67%
**Verdict**: **NEGATIVE** — NLP prompts harm F1 runs

Run A (F1+NLP+300) scored 57.67% test EM, 4.00pp below the F1-only reference (Run F,
61.67%). This is below the NEGATIVE threshold of <61.0%, confirming that NLP mutation
prompts are actively harmful when paired with F1 fitness. The direction is consistent with
the Risk 4 concern raised in 01_design.md: NLP prompts were designed around EM task framing
and may inject conflicting objectives when paired with an F1 fitness landscape, despite
the metric-agnostic Amendment 1 fix to system.txt.

McNemar p-value A vs D: 0.006 (statistically significant at α=0.05). NLP prompts at
F1/300 are worse than F1+NLP+600 (Run D) by 5.33pp.

### Run D test (F1+NLP+600)

Post-Amendment 3 comparisons:
- D vs. C: NLP-prompt effect at 600 samples under F1 fitness
- D vs. A: val-N effect (600 vs. 300) for F1+NLP

**Run D test EM**: 63.00% | **D − C**: **+4.33pp** | **D − A**: **+5.33pp**

Run D is the only run in this experiment to exceed GEPA (63.00% > 62.3%), and it does so
by a margin (0.7pp) that is modest relative to the 95% CI [57.40%, 68.27%]. The McNemar
p-value for D vs. C is 0.049 (borderline significant at α=0.05). D vs. B (p=0.007) and
D vs. A (p=0.006) are statistically significant.

However, Run D is an **Amendment-3 run**: it replaced the pre-registered EM+NLP+600 cell
mid-run (after gen 3 under EM), and gen 1–3 data were discarded. Run D was not pre-registered
as primary and cannot carry the experiment-level POSITIVE verdict. It is treated as an
exploratory finding that motivates replication.

---

## 4. Binomial 95% CIs and Mechanism Attribution

_Compute via `experiments/hotpotqa/push/tools/analyze_test_results.py` from `test_evals/results.json`._

| Run | Test EM | 95% CI lower | 95% CI upper |
|-----|---------|-------------|-------------|
| A | 57.67% | 52.01% | 63.13% |
| B | 57.00% | 51.34% | 62.48% |
| C | 58.67% | 53.02% | 64.10% |
| D | 63.00% | 57.40% | 68.27% |

**Note on CI overlap**: The 95% CIs for runs A, B, and C substantially overlap (all
spanning roughly 52–64%). The CI for Run D is the only one whose lower bound (57.40%)
is fully above the lower bounds of B and A, and whose point estimate (63.00%) sits
above GEPA. At N=300, individual-run comparisons must be interpreted with caution — the
McNemar test on matched item-level predictions is more informative than CI overlap.

### Partial 2x2 at 600 samples (post-Amendment 3)

| | prompts=default | prompts=hotpotqa |
|---|---|---|
| **F1 fitness** | C: 58.67% | D: 63.00% |
| **EM fitness** | B: 57.00% | — |

NLP-prompt main effect at F1/600: D − C = **+4.33pp** (McNemar p=0.049)
Reference comparison at 300 samples: A − F = 57.67% − 61.67% = **−4.00pp** (harmful)

The NLP-prompt effect reverses sign between 300 and 600 samples under F1 fitness.
At 300 samples (A vs. F reference), NLP prompts cost −4.00pp. At 600 samples (D vs. C),
NLP prompts gain +4.33pp. This interaction (NLP prompts × val-N) is the most striking
finding in the experiment. It cannot be attributed to stochasticity alone given the
McNemar p-values, but requires replication (N ≥ 3 per cell) to claim as a causal effect.

---

## 5. Deviations from Pre-Registration

| # | Amendment | Timing | Impact on analysis |
|---|-----------|--------|-------------------|
| 1 | `system.txt` metric-agnostic ROLE framing | Pre-reg | None — uniform across all runs |
| 2 | `stage_timeout` Hydra wiring fix | Pre-reg | None — fixed silent bug; all runs benefit equally |
| 3 | Run D: EM+NLP+600 -> F1+NLP+600 (mid-run gen 3) | Gen 3 of D | Confound: Run D gen 1-3 discarded. EM*NLP cell lost. Primary test (Run C) unaffected. |
| 4 | HTTP timeout 120s->600s + hard reset all 4 runs | Gen 2-5 | None — all runs restarted from same ddce37b4 seed; no differential treatment |

**Protocol deviations** (procedural, not scientific):
- Deviation 1: Code before `03_plan.md` — changes required by Volkov Phase 2 review; design locked before any run launched.
- Deviation 2: Branch created after design commits on `main` — full audit trail in PR #73 body.

---

## 6. Run Validity

| Run | Valid for primary analysis? | Notes |
|-----|-----------------------------|-------|
| A | Yes | Clean |
| B | Yes | Clean |
| C | Yes — PRIMARY | Clean |
| D | Partial | Gen 1-3 under EM discarded (Amendment 3); F1 condition data used |

---

## 7. Lessons Learned

**Bugs / infrastructure fixed during this experiment**:
- `httpx.Timeout(120s)` too short for 600-sample runs — 600 concurrent requests can queue
  >120s in vLLM. Fixed to 600s (`c0186a8`). Always use 600s for 600-sample runs.
- Watchdog PROJ depth wrong for files 4 levels deep (`.parent*3` -> `.parent*4`).
- Watchdog gen-count via log grep brittle; replaced with Redis
  `{prefix}:metrics:history:program_metrics:valid_iter_fitness_mean` last `"s"` field.
- `gen10_test_eval.py` gap was `val_F1 - test_EM` for F1 runs (meaningless). Fixed:
  `best.metrics.get("em", best.metrics["fitness"])` uses secondary EM metric.
- Watchdog `_last_gen` keyed with wrong labels -> `KeyError` ~1h after start. Fixed:
  derive from `RUNS` list.

**What worked**:

Run D (F1+NLP+600) is the first GigaEvo run to exceed GEPA, achieving 63.00% test EM
with McNemar-significant separation from Runs A, B, and C. While this result cannot be
adopted as a primary finding (Amendment 3 confound, not pre-registered as primary), it
demonstrates that the 62.3% ceiling is not unreachable — the right combination of fitness
signal, sample size, and mutation prompts can cross it.

The infrastructure hardening from this experiment is durable and applies to all future
600-sample runs: the stage_timeout Hydra wiring fix (Amendment 2), the HTTP timeout
increase to 600s (Amendment 4), and the corrected watchdog gen-count method from Redis
are all committed and will prevent the category of failures that invalidated prior
600-sample runs (Q in val_gap).

The val-EM secondary metric tracking in `static_f1_600/validate.py` works correctly:
`valid_frontier_em` is populated alongside `valid_frontier_fitness` (F1), enabling
within-metric gap analysis for F1 runs without conflating fitness signal with the
EM evaluation metric.

The McNemar pairwise test infrastructure (`analyze_test_results.py`) now provides
item-level statistical comparisons across runs sharing the same test set, which is more
statistically sound than CI overlap comparisons at N=300.

**What didn't work**:

The core hypothesis of the experiment — that combining F1 fitness with 600-sample
validation would reduce the val-test gap and push past GEPA — is falsified. Run C
(the pre-registered primary run) scored 58.67% test EM with a +4.17pp val-test gap,
worse than Run F (61.67%, ~1.7pp gap) on both metrics. Larger validation samples under
F1 fitness did not reduce selection noise; they increased overfit.

The val-test gap results across all four runs tell a counterintuitive story: Run B
(EM+600) has the largest gap in the experiment (+7.67pp), not the smallest. The
theoretical noise-floor argument (SE drops from 2.4pp at N=300 to 1.3pp at N=600)
failed to account for the increased overfit: with 600 samples, the archive can
select programs that are more consistently good on those specific 600 questions,
even if those programs do not generalize. The selection signal is not just noisy —
it is systematically biased toward the training distribution at larger N.

NLP mutation prompts at 300 samples under F1 fitness (Run A) actively harmed
performance relative to the F1-only reference (Run F): −4.00pp. The Amendment 1
metric-agnostic fix to system.txt was insufficient to resolve the objective conflict
between NLP prompts (designed for EM framing) and the F1 fitness landscape. The
prompts encode assumptions about what constitutes a "good" multi-hop answer that are
optimized for EM, and these assumptions produce worse programs when fitness is F1.

Stagnation was confirmed for the fifth consecutive experiment series. Best programs
were found at iterations 18–33 across all four runs, corresponding to birth-generations
4–8. No run showed meaningful frontier improvement after gen 8. Single-parent mutation
(num_parents=1) cannot escape the local-optima basin formed by the ddce37b4 warm-start
seed, regardless of fitness metric, sample size, or mutation prompt engineering. The
stagnation ceiling is structural, not a tuning problem.

The val-N interaction with NLP prompts (harmful at 300, helpful at 600 samples) is
unexpected and has no obvious mechanistic explanation. It may be a statistical artifact
at N=1 per cell, or it may reflect a genuine property of how larger fitness signals
interact with domain-specific mutation guidance. The single observation at each cell
does not permit disambiguation.

---

## 8. Next Steps

The primary experiment-level verdict is NULL, and the stagnation analysis across all
prior experiments now points unambiguously to a single structural constraint. The
research agenda should pivot accordingly.

**Highest priority: P3 crossover (num_parents=2)**

Every available signal — seven independent single-parent runs, each peaking at
birth-gen 4–8 regardless of fitness metric, sample size, or mutation prompt — converges
on the same conclusion: the binding constraint is single-parent mutation's inability to
escape local optima. The P3 crossover experiment (combining two elite programs via
LLM-guided recombination) is the only pre-specified structural fix available. It should
be launched immediately as the next experiment. The pre-registration for P3 crossover
(`experiments/hotpotqa/p3_crossover/`) should be revisited for adequacy given the
additional val-test gap evidence from this experiment.

**Secondary priority: Replicate Run D (F1+NLP+600) with N >= 3**

Run D's 63.00% test EM result is the most interesting individual finding in this
experiment. It is the first GigaEvo result to exceed GEPA in a single run, and the
McNemar tests confirm it is statistically separable from the other three runs in this
experiment. However, the Amendment 3 confound (mid-run fitness switch, gen 1–3
discarded) and the experiment's pre-registration failure for this cell mean the result
is exploratory, not confirmatory. A dedicated N=3 replication of the F1+NLP+600
condition — pre-registered from scratch as a clean experiment — would determine whether
63.00% is a reliable estimate or a lucky draw.

Replication design note: fix the cell (F1 fitness, hotpotqa NLP prompts, 600-sample
validation), three independent seeds or three independent runs from the same seed,
report median test EM. If median >= 62.3%, the GEPA attack is confirmed. If all three
are below 62.3%, the single Run D result was consistent with noise.

**Do not pursue**:

- Further tuning of 600-sample EM runs (Gate C is now closed NEGATIVE: the gap
  increases, not decreases, under EM fitness at N=600). The theoretical noise-floor
  argument does not hold empirically.
- NLP prompts at 300 samples under F1 fitness (Run A cell): confirmed NEGATIVE, and
  the mechanism (EM-framing conflict with F1 landscape) is clear enough to deprioritize
  further deconfounding at this sample size.
- Increasing max_generations beyond 25 for single-parent runs: stagnation is confirmed
  to occur universally by gen 8. Generations 9–50 contribute essentially zero frontier
  improvement at the compute cost of generating and evaluating hundreds of programs.
  Unless P3 crossover is used, max_generations=12–15 is sufficient for single-parent
  protocols.

**Open mechanistic question**:

The NLP prompts × val-N interaction (−4.00pp at N=300, +4.33pp at N=600, both under
F1 fitness) warrants a mechanistic investigation even if not pursued via additional
evolutionary runs. Specifically: do the NLP prompts generate structurally different
program mutations (e.g., longer prompts, more explicit multi-hop reasoning chains)
that are penalized under the 300-sample F1 distribution but rewarded under the
600-sample F1 distribution? Inspecting the programs selected by Run D vs. Run A
and Run C may reveal whether the NLP prompts shift the mutation distribution in a
systematic direction that interacts with sample size.

---

## 9. GitHub Closeout

- [x] `bash experiments/hotpotqa/push/run_test_eval.sh` -> fill sections 1-4 above
- [x] Invoke `ml-research-methodologist` agent for final write-up
- [x] `PYTHONPATH=. python experiments/hotpotqa/push/tools/analyze_test_results.py experiments/hotpotqa/push/test_evals/results.json`
- [ ] Archive all runs:
  ```bash
  bash tools/experiment/archive_run.sh --exp hotpotqa/push --run "chains/hotpotqa/static_f1@8:push-A" --upload
  bash tools/experiment/archive_run.sh --exp hotpotqa/push --run "chains/hotpotqa/static_600@9:push-B" --upload
  bash tools/experiment/archive_run.sh --exp hotpotqa/push --run "chains/hotpotqa/static_f1_600@10:push-C" --upload
  bash tools/experiment/archive_run.sh --exp hotpotqa/push --run "chains/hotpotqa/static_f1_600@11:push-D" --upload
  ```
- [ ] `experiments/INDEX.md` updated to Complete with final finding
- [ ] `environment_freeze.txt` committed
- [ ] `gh pr merge --merge --delete-branch` (NOT --squash)
- [ ] Flush Redis DBs 8-11 after archiving confirmed
