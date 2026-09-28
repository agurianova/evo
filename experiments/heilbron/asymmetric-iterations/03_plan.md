# Pre-Registration: heilbron/asymmetric-iterations (Redesign)

**Date**: 2026-04-12
**Protocol version**: 1.0
**Supersedes**: Pre-registration commit `8ce7ab3f` (WGAN-GP K:1 ratio design — replaced by structured information flow design)
**Pre-registration commit**: *(to be filled after commit)*
**GitHub PR**: #204 (branch: `exp/heilbron/asymmetric-iterations`)
**Tracking issue**: N/A
**Design doc**: `experiments/heilbron/asymmetric-iterations/01_design.md`
**Review doc**: `experiments/heilbron/asymmetric-iterations/02_review.md` (verdict: APPROVED, Round 3)
**Evaluation script**: N/A (no test set -- continuous optimization)
**Dataset snapshot**: `experiments/heilbron/asymmetric-iterations/dataset_snapshot.json` (commit `4f8d4741`)

---

## Hypothesis

**H0**: Neither feedback mode (Composition nor Gradient-in-prompt) with K=5 inner iterations changes Constructor actual_fitness relative to the historical baseline (0.03449).

**H1**: At least one feedback mode produces Constructor actual_fitness meaningfully different from the historical baseline.

**Primary metric**: Constructor actual_fitness at gen 50
**Significance threshold**: alpha = 0.10 (two-sided), acknowledging severe underpowering at N=2/arm
**Historical baseline**: heilbron/baseline-repro mean best-overall actual_fitness = 0.03449 (N=4, SD=0.00212)

---

## Run Design Table

| Run | Label | `redis.db` | `pipeline` | `problem.name` | Role | `feedback_mode` | Condition |
|-----|-------|------------|-----------|----------------|------|-----------------|-----------|
| 1 | A1_G | 1 | adversarial_asymmetric | heilbron_adversarial/pop_a | Constructor | composition | Arm A: Composition, pair 1 |
| 2 | A1_D | 2 | adversarial_asymmetric | heilbron_adversarial/pop_b | Improver | composition | Arm A: Composition, pair 1 |
| 3 | A2_G | 3 | adversarial_asymmetric | heilbron_adversarial/pop_a | Constructor | composition | Arm A: Composition, pair 2 |
| 4 | A2_D | 4 | adversarial_asymmetric | heilbron_adversarial/pop_b | Improver | composition | Arm A: Composition, pair 2 |
| 5 | C1_G | 5 | adversarial_asymmetric | heilbron_adversarial/pop_a | Constructor | gradient_in_prompt | Arm C: Gradient-in-prompt, pair 1 |
| 6 | C1_D | 6 | adversarial_asymmetric | heilbron_adversarial/pop_b | Improver | gradient_in_prompt | Arm C: Gradient-in-prompt, pair 1 |
| 7 | C2_G | 7 | adversarial_asymmetric | heilbron_adversarial/pop_a | Constructor | gradient_in_prompt | Arm C: Gradient-in-prompt, pair 2 |
| 8 | C2_D | 8 | adversarial_asymmetric | heilbron_adversarial/pop_b | Improver | gradient_in_prompt | Arm C: Gradient-in-prompt, pair 2 |

---

## Controlled Variables

| Field | Value |
|-------|-------|
| `max_generations` (outer) | 50 |
| K (inner iterations per outer gen) | 5 |
| N_opp (opponents per D evaluation) | 5 |
| D `max_mutations_per_generation` (per inner iter) | 8 |
| G `max_mutations_per_generation` | 8 |
| `max_elites_per_generation` | 8 |
| D archive persistence | TRUE |
| `mutation_mode` | rewrite |
| `model_name` | Qwen3-235B-A22B-Thinking-2507 |
| `llm_base_url` | http://10.232.30.185:4000/v1 |
| `temperature` | 0.6 |
| `num_parents` | 1 |
| `archive_reeval` | false |
| Engine | Generational (`EvolutionEngine`) |
| `pipeline` | adversarial_asymmetric |
| Seed | grid.py (Constructor), seed.py (Improver) |

---

## Key Design Features

1. **D sees G source code**: Improver receives Constructor's `solve()` source code as dynamic task description (white-box access), replacing output-array-only information channel.
2. **K=5 inner iterations**: Per outer generation, D runs 5 inner MAP-Elites iterations. D's inner iterations do NOT increment `engine:total_generations`. G blocks during D's inner loop via `MainRunSyncHook`.
3. **Collective evaluation**: D evaluates against all N_opp=5 G opponents simultaneously; fitness = mean improvement across opponents.
4. **Persistent D archive**: D's MAP-Elites archive carries improvement strategies across outer generations.
5. **Two feedback modes (single IV)**:
   - **Arm A (Composition)**: D_best(G_i) submitted as mutation candidate in G's next gen, tagged `mutation_type="d_improvement"`, goes through G's normal DAG pipeline.
   - **Arm C (Gradient-in-prompt)**: D_best source code shown verbatim in G's mutation LLM prompt.

---

## Reproducibility Notes

**This experiment uses stochastic LLM-based evolution. Exact trajectory reproduction is not possible.**

Known sources of non-determinism:
- LLM sampling temperature and nucleus sampling in mutation LLM
- MAP-Elites parent selection (random among elites)
- `random.sample` in FormatterStage
- D's inner iteration dynamics (archive-dependent selection)

**Global seed**: N/A (not supported for adversarial co-evolution)

A fresh run with identical config will produce a different fitness trajectory but should land in a statistically similar fitness range. Cross-experiment comparisons use effect-size thresholds rather than exact trajectory matching.

---

## Dataset Checksums

N/A -- Heilbronn is a continuous optimization problem with no external dataset. Point configurations are generated by evolved programs. The only fixed inputs are the initial seed programs (`grid.py`, `seed.py`), which are version-controlled in `problems/heilbron_adversarial/pop_a/initial_programs/` and `pop_b/initial_programs/`.

See `experiments/heilbron/asymmetric-iterations/dataset_snapshot.json` for file checksums (commit `4f8d4741`).

---

## Success Criteria

| Outcome | Criterion | Action |
|---------|-----------|--------|
| STRONG POSITIVE | Either arm mean actual_fitness >= 0.03649 AND acceptance rate > 5% in 2/2 replicates | Write paper section. Ablate compound treatment components. |
| POSITIVE | Either arm mean >= 0.03449 (baseline) AND acceptance rate > 5% | Continue this line. Dose-response (K=3/5/10). Component ablation. |
| NULL | Both arms within 0.001 of baseline, acceptance rate stays 0% | Stagnation is search space, not budget or information. Proceed to adversarial_003 (structured Improver). |
| NEGATIVE | Both arms < 0.03249 (baseline - 0.002) | Structured information flow destabilizes dynamics. Close this line. |
| FEEDBACK MODE MATTERS | Arm difference >= 0.002 | Follow up with volume-controlled comparison (random D injection vs best D injection). |
| INCONCLUSIVE | Mixed results across replicates within arm | Underpowered. Replicate at N=4/arm. |

---

## Monitoring Plan

`max_generations` (outer): 50

- Gen 3 (~6%): smoke check -- all PIDs alive, D inner iterations visible in logs, sync hook working
- Gen 5 (~10%): verify D sees G source code, K=5 inner iterations confirmed, generation sync within 1
- Gen 10 (~20%): first checkpoint -- D archive growing, Arm A shows composition injections, Arm C shows gradient-in-prompt
- Gen 25 (~50%): midpoint checkpoint -- extract Constructor actual_fitness per arm, compare to baseline
- Gen 25: futility check -- if both replicates of an arm < 0.03000, stop that arm
- Gen 50 (100%): final evaluation + analysis

---

## Actual Launch Record

| Run | PID | Launch time (UTC) | Notes |
|-----|-----|-------------------|-------|
| *(to be filled at launch)* | | | |

Watchdog PID: *(to be filled)*
Launch commit: *(to be filled)*

---

## Checkpoint Log

| Gen | Date (UTC) | Notes |
|-----|-----------|-------|

---

## Amendments

1. **2026-04-12**: Complete redesign. Replaced WGAN-GP K:1 ratio design (commit 8ce7ab3f) with structured Improver-Constructor information flow design. See 01_design.md for rationale. Old design tested a single config override (`max_mutations_per_generation=40`); new design introduces source code access, K=5 inner iterations, persistent D archive, and two feedback modes (Composition vs Gradient-in-prompt).
