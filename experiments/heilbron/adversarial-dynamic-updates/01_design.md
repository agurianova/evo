# Experimental Design: heilbron/adversarial-dynamic-updates

**Date**: 2026-04-09
**Researcher**: Dr. Elena Voss (ml-research-methodologist agent)
**Status**: Revised v3 — amendment adds soft fitness (Wasserstein analog) as second IV; 2×2 factorial, 8 runs

---

## 1. Research Question

Does per-program fingerprint-based archive re-evaluation --- re-evaluating archived programs against the current opponent archive only when their sampled opponent set has changed --- fix stale fitness, improve parent selection, and break Improver stagnation on the Heilbronn adversarial co-evolution task?

### Motivation

In adversarial co-evolution, each program is evaluated once against a sampled set of opponent archive programs at evaluation time, and the resulting fitness is frozen. As the opponent population evolves, this fitness becomes **stale**: an Improver that scored 38% against gen-3 Constructors may score 0% against gen-15 Constructors, but MAP-Elites still selects it as a parent based on the stale 38%. This creates a **phantom elite** problem — wrong parent selection leading to wasted mutations.

**GAN training analogy**: This is the discriminator staleness problem. In WGAN-GP (Gulrajani et al., 2017), the discriminator is updated 5 times per generator step precisely because a stale discriminator gives wrong gradient signal. Our analog: D's archived fitness must stay current with G's evolution. Heusel et al. (2017 TTUR) proved that asynchronous update rates are acceptable only when each component stays informed about the other's current state.

**QD literature analogy**: Deep-Grid (Flageat et al., 2023) continuously "questions" archive elites by re-evaluation, preventing lucky stale elites from dominating cells. Co-evolutionary staleness is a structured version of this noisy-evaluation problem.

### Mechanism: per-program fingerprint with stored seed

**Core idea**: When a D program is evaluated, the random seed used to sample opponents is stored. At each epoch boundary, the same seed is applied to the **current** opponent archive. If the resulting opponent set differs from the stored fingerprint, the program is re-evaluated against the new set.

This is more efficient than global archive-change triggers:
- Programs whose sampled set is stable (same programs win the draw) are never re-evaluated
- Only programs whose evaluation context has genuinely changed get re-evaluated
- The random seed preserves evaluation diversity (different programs sample different subsets)

**Symmetry**: Both G and D archives are re-evaluated. G's `resistance` component depends on D, so G re-evaluation keeps resistance scores current. However, G's `actual_fitness` (raw min_area) is intrinsic geometry and does NOT depend on opponents — it never changes under re-evaluation.

### Why K=0 (no opponent feedback), not K=3

GAN literature supports isolating the discriminator update frequency mechanism before testing information-channel enhancements:
- D re-evaluation = discriminator update frequency fix (WGAN-GP foundational principle)
- K=3 opponent code = feature matching (Salimans et al., 2016 — additive, not synergistic)

adversarial-v2 showed K=3 alone gave marginal +0.00038 gain. Combining K=3 with D re-evaluation would prevent causal attribution. K=0 gives clean signal; K=3 can be added in a follow-up if D re-evaluation works.

---

## 2. Hypotheses

**H1 (Primary --- Constructor actual_fitness):**
Treatment pair (re-eval ON) achieves higher Constructor `actual_fitness` (raw min_area) than control pair (re-eval OFF) at generation 75.

- **Success criterion (POSITIVE)**: Treatment > control by >= 0.002.
- **Strong success (STRONG POSITIVE)**: Treatment > control by >= 0.005.
- **NULL criterion**: |treatment - control| < 0.002.
- **NEGATIVE criterion**: Control > treatment by >= 0.002.

**Why `actual_fitness`, not composite `fitness`** (GAN literature, Heusel et al. 2017):
FID/IS are opponent-independent quality metrics in GAN papers — decoupled from discriminator judgment. `actual_fitness` (raw min_area) is the direct analog: intrinsic geometry, opponent-independent, stable across time. `fitness` (0.5*quality + 0.5*resistance) confounds the measurement — if D gets better, G's resistance drops and `fitness` falls even if G's actual configuration didn't change.

**H2 (Secondary --- Improver stagnation):**
Treatment Improver shows higher acceptance rate after gen 20 than control Improver.

- **Success criterion**: Treatment Improver acceptance rate > 5% (rolling 10-gen window), control < 2%.
- **NULL criterion**: Both stagnate.

**H3 (Secondary --- Archive staleness correction):**
Re-evaluation produces measurable elite turnover: programs with stale high fitness are displaced.

- **Measured by**: Fraction of archive cells where the elite changes after re-evaluation.
- **Success criterion**: Mean elite turnover rate > 10% per re-evaluation event.

---

## 3. Independent Variables (2×2 Factorial)

**Amendment (v3)**: Soft fitness added as second IV after researcher approval. 2×2 factorial, 8 runs total.

| IV | Level 0 (OFF) | Level 1 (ON) |
|----|---------------|--------------|
| **IV1: Archive re-evaluation** | Fitness frozen at evaluation time | Per-program fingerprint re-eval when sampled opponent set changes |
| **IV2: Soft fitness** | Binary improvement scoring (current `max(delta, 0) / Q_MAX`) | Continuous sigmoid scoring (`sigmoid(delta / T)`, T=0.004) |

**Design**:

```
                    Soft Fitness OFF    Soft Fitness ON
                  ┌──────────────────┬─────────────────┐
  Re-eval OFF    │  C (control)      │  SF only         │
                 │  DBs 5-6          │  DBs 7-8         │
                 ├──────────────────┼─────────────────┤
  Re-eval ON     │  RE only          │  Both            │
                 │  DBs 1-2          │  DBs 3-4         │
                 └──────────────────┴─────────────────┘
```

**Estimable effects**:
- Main effect of re-eval: `(RE + Both) - (C + SF)` → isolates re-evaluation signal
- Main effect of soft fitness: `(SF + Both) - (C + RE)` → isolates soft fitness signal
- Interaction: `Both - RE - SF + C` → whether the combination exceeds either alone

**No compound confounds**: each cell comparison varies exactly one IV.

### Treatment mechanism (detailed)

**Step 1 — At evaluation time**: When program P is evaluated, the random seed `s` used to softmax-sample N opponents is stored alongside P's metrics:

```python
# Inside FetchOpponentResultsStage.compute():
s = random.randint(0, 2**31)  # unique per evaluation
random.seed(s)
# Softmax sampling: min-max normalize fitnesses → softmax(arr/temp), sample w/o replacement
# (mirrors FitnessProportionalEliteSelector._compute_weights exactly — see _softmax_weights())
opponents = get_opponents_with_seed(archive, n=5, seed=s)
P.eval_seed = s
P.eval_fingerprint = frozenset(o.program_id for o in opponents)
# evaluation proceeds normally with these opponents
```

**Step 2 — At epoch boundary (step 8 of _epoch_refresh, AFTER sync hook)**:

```python
class ArchiveReEvaluationHook:
    def on_post_refresh(self, own_archive, opponent_archive):
        for program in own_archive.get_all_programs():
            # Re-apply stored seed to CURRENT archive
            current_opponents = sample_with_seed(
                opponent_archive, n=5, seed=program.eval_seed
            )
            current_fp = frozenset(o.program_id for o in current_opponents)

            if current_fp == program.eval_fingerprint:
                continue  # evaluation context unchanged, skip

            # Re-evaluate against the new opponent set
            reeval_metrics = dag_runner.evaluate_with_opponents(
                program, opponents=current_opponents
            )
            own_archive.update_fitness(program, reeval_metrics)
            program.eval_fingerprint = current_fp  # update fingerprint
            # eval_seed stays the same

            reeval_logger.record(
                program_id=program.id,
                old_fitness=program.metrics["fitness"],
                new_fitness=reeval_metrics["fitness"],
                elite_changed=archive_cell_changed(program),
            )
```

**Epoch lifecycle placement** (after Volkov C1 review):

```
_epoch_refresh():
  Step 3a: Publish programs_processed → Redis   ← sync hook reads this
  Step 4:  ProgressBasedSyncHook fires           ← resolves based on 3a counter
  Step 6:  _refresh_archive_programs()           ← lineage/insights stages
  Step 7:  mutation_gate.set()                   ← GATE OPENS
  Step 8:  _await_idle() + reindex               ← NEW: re-eval hook runs here
           *** ArchiveReEvaluationHook ***        ← concurrent with new mutations
  Step 9:  Increment epoch counter
```

Re-evaluation at step 8: mutation gate is **open**, sync hook is **resolved**, no deadlock possible. Re-eval competes with new mutation DAGs for runner slots but Heilbronn evaluation is CPU-bound (~0.5s/program) vs mutation (~60s LLM inference) — minimal contention.

**Stored seed re-sampling semantics**: Applying seed `s` to the current archive uses the same softmax sampling algorithm (`_softmax_weights`: min-max normalize, softmax with auto-temperature) on the current programs with current fitness values. If programs have been added/removed or fitnesses have shifted, the same seed draws different opponents. This is the trigger: "under the same random draw with current fitness weights, do I now hit different opponents?"

### Soft fitness mechanism (IV2)

**Motivation** (GAN analogy: Wasserstein distance vs JS divergence): Binary improvement scoring (`max(delta, 0) / Q_MAX`) gives zero gradient when the Improver is close to zero improvement — saturated signal, exactly analogous to JS divergence saturation in vanilla GANs. Sigmoid scoring provides continuous gradient everywhere.

**Changes to `evaluate.py`** (applied only in SF and Both conditions via config flag `adversarial.soft_fitness=true`):

```python
# Pop B — current (binary):
delta = max(post_q - pre_q, 0.0)
credit = min(delta / Q_MAX, 1.0)  # 0 for no improvement

# Pop B — soft (Wasserstein analog):
delta = post_q - pre_q          # allow negative (worsening gets low credit)
credit = sigmoid(delta / T)     # T=0.004 ≈ Q_MAX/9; sigmoid(0)=0.5 at zero improvement

# Pop A resistance — current (binary):
resistance_i = float(delta_i <= 0)     # 1 if opponent failed, 0 if opponent succeeded

# Pop A resistance — soft:
resistance_i = sigmoid(-delta_i / T)   # continuous: near 1 for delta≤0, near 0 for large delta
```

**Temperature T = 0.004** (≈ Q_MAX/9):
- delta=0 → sigmoid(0) = 0.50 (neutral — zero improvement gets partial credit)
- delta=+0.004 → sigmoid(1) ≈ 0.73 (modest improvement gets 73% credit)
- delta=+0.01 → sigmoid(2.5) ≈ 0.92 (strong improvement)
- delta=-0.004 → sigmoid(-1) ≈ 0.27 (worsening gets penalised)

**Soft fitness is activated by `adversarial.soft_fitness=true`** config flag. Control conditions use `soft_fitness=false` (current binary behavior). Only `evaluate.py` changes — no pipeline or architecture changes.

---

## 4. Dependent Variables

| Metric | How measured | Primary? |
|--------|-------------|----------|
| `actual_fitness` | Raw min_area of Constructor output; read from archive at gen 75 | **Yes** |
| `fitness` | Composite 0.5*quality + 0.5*resistance | No (secondary) |
| `resistance` | 1 - mean(normalized improvement by opponents) | No |
| Improver acceptance rate | Fraction valid Improver programs accepted into archive (rolling 10-gen window) | No (H2) |
| Elite turnover rate | Fraction of archive cells where elite changed after re-evaluation | No (H3, treatment only) |
| Re-evaluation events | Count per epoch | No (treatment verification) |
| Re-eval fitness delta | Mean |new_fitness - old_fitness| across re-evaluated programs | No (staleness measure) |
| Mutations per wall-hour | Total mutations / wall-clock hours | No (throughput confound check) |
| Archive occupied cells | Distinct occupied cells after each epoch | No (diversity monitor) |

**Primary DV**: `actual_fitness` (raw min_area) read from archive state at gen 75 (live Redis query), **not** from frontier history. This is the GAN-literature-aligned metric: intrinsic generator quality, decoupled from discriminator state.

---

## 5. Controlled Variables

| Field | Value | Rationale |
|-------|-------|-----------|
| Opponent feedback (K) | K=0 | Isolates re-eval mechanism (GAN: test discriminator frequency before feature matching) |
| `evolution` | `steady_state` | Consistent with all recent adversarial experiments |
| `max_in_flight` | 8 | Same backpressure |
| `pipeline` | `adversarial_coevo_ss` | No feedback stage |
| `problem.name` (Pop A) | `heilbron_adversarial/pop_a` | Same |
| `problem.name` (Pop B) | `heilbron_adversarial/pop_b` | Same |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` | Same mutation LLM |
| `mutation_url` | `http://10.232.30.185:4000/v1` | Same LiteLLM proxy |
| `num_parents` | 1 | Same |
| `max_elites_per_generation` | 8 | Same |
| `max_mutations_per_generation` | 8 | Same |
| `n_opponents` | 5 | Same |
| `per_opponent_timeout` | 300 | Same |
| `stage_timeout` | 3000 | Same |
| `dag_timeout` | 7200 | Same |
| `mutation_mode` | `rewrite` | Same |
| `max_generations` | 75 | Same as adversarial-v2 |
| `significant_change` | 0.01 | Same |
| Initial programs | `initial_programs/baseline.py` (cold start) | Same seed |
| `OPENAI_API_KEY` | `sk-gigaevo` | Same |

---

## 6. Run Design Table

**2×2 factorial. N=1 pair per condition (exploratory). 8 runs total.**

| Run | Label | `redis.db` | Pop | Condition | Re-eval | Soft fitness | `opponent_redis_db` |
|-----|-------|------------|-----|-----------|---------|--------------|---------------------|
| 1 | RE_A  | 1 | A (Constructor) | RE only  | ON  | OFF | 2 |
| 2 | RE_B  | 2 | B (Improver)    | RE only  | ON  | OFF | 1 |
| 3 | Both_A| 3 | A (Constructor) | Both     | ON  | ON  | 4 |
| 4 | Both_B| 4 | B (Improver)    | Both     | ON  | ON  | 3 |
| 5 | C_A   | 5 | A (Constructor) | Control  | OFF | OFF | 6 |
| 6 | C_B   | 6 | B (Improver)    | Control  | OFF | OFF | 5 |
| 7 | SF_A  | 7 | A (Constructor) | SF only  | OFF | ON  | 8 |
| 8 | SF_B  | 8 | B (Improver)    | SF only  | OFF | ON  | 7 |

**Total: 8 runs.** DB pairs: RE=1-2, Both=3-4, C=5-6, SF=7-8. No cross-condition interaction.

### 6.1 Concurrent control

All four conditions run simultaneously. Single-observation-per-condition comparison (N=1). Explicitly exploratory — no within-condition replication. See Section 8 for power acknowledgement.

### 6.2 Metrics isolation (Volkov M1)

Re-evaluation writes to a **separate `reeval_*` metrics namespace** — the primary `valid_frontier_*` and `valid_program_*` namespaces are written ONLY on first evaluation. This preserves the temporal record of genuine discoveries. The `_refresh_changed_fitness()` path in `MetricsTracker` is gated: re-evaluation-triggered changes do not rewrite the primary frontier history.

### 6.3 Archive diversity guard (Volkov M2)

Track `archive_occupied_cells` after each re-evaluation. If any run's archive shrinks below 3 occupied cells for 5 consecutive epochs: pause re-evaluation hook for that run, log as protocol deviation, continue run without re-eval.

---

## 7. Re-Evaluation Compute Budget

| Parameter | Estimate |
|-----------|----------|
| Archive size (typical) | 10-30 programs |
| Opponents per re-evaluation | 5 |
| Per-opponent eval time | ~0.5s (CPU-bound numpy geometry) |
| Per-program re-eval time | ~2.5s |
| Full archive re-eval cost | ~25-75s |
| Re-eval frequency | Only when sampled fingerprint changes |
| Expected epochs with re-eval | ~40-60% (top-5 is stable when G archive plateaued) |

**Efficiency of fingerprint approach vs naive**: If the top-5 G programs are stable for 10 epochs (G frontier has plateaued), ZERO re-evaluations occur for D during those epochs. Naive approach (any archive change → re-eval all) would re-evaluate every epoch. Fingerprint approach saves ~40-60% of epochs.

**Pre-authorized amendments**:
1. **Compute throttle**: If re-evaluation > 120s per trigger, throttle to top-K programs only. Log event.
2. **Diversity guard**: See Section 6.3.

---

## 8. Sample Size Justification

N=1 pair per condition. This is **explicitly exploratory**. No within-condition replication.

**What we can detect**: Direction and magnitude of effect (treatment vs control). The comparison is a single observation per condition, not a replicated experiment. Results are interpreted as: "consistent with re-evaluation helping / not helping," not as causal proof.

**Why N=1 is appropriate here**: Re-evaluation is a measurement fix, not a training technique (issue #195 language). If the mechanism works, the effect should be large and clear (archive fitness changes visibly, acceptance rate changes from ~0% to >5%). A subtle effect that requires N>1 to detect would suggest the mechanism is marginal and warrants a follow-up with proper replication.

**Acknowledged limitation**: If both pairs happen to have unusual trajectories (cold-start variance), the comparison is confounded. heilbron-prover within-pair variance was 0.00168; a 0.002 treatment effect is marginally above noise at N=1.

---

## 9. Statistical Analysis

**H1 (main effects)**: `actual_fitness` at gen 75 for each of the 4 Constructor runs (RE_A, Both_A, C_A, SF_A).

- **Re-eval main effect**: `(RE_A + Both_A) / 2 - (C_A + SF_A) / 2`
  - POSITIVE if > 0.002; NULL if < 0.002
- **Soft fitness main effect**: `(SF_A + Both_A) / 2 - (C_A + RE_A) / 2`
  - POSITIVE if > 0.002; NULL if < 0.002
- **Interaction**: `Both_A - RE_A - SF_A + C_A` (positive = synergy, negative = interference)
- Reference noise floor: heilbron-prover within-pair variance ≈ 0.00168

**H2 (Improver stagnation)**: Acceptance rate (gen 20-75, rolling 10-gen window) for RE_B, Both_B, C_B, SF_B.
- POSITIVE per condition if rate > 5% (vs 0% in adversarial-v2 control).

**H3 (Archive staleness)**: Elite turnover rate in RE pair and Both pair (re-eval ON conditions only).
- ACTIVE if > 10% per epoch; MINIMAL if < 5%.

No formal hypothesis testing (t-test inappropriate at N=1). All analysis is directional/magnitude-based.

---

## 10. Known Confounds and Mitigations

| Confound | Risk | Mitigation |
|----------|------|-----------|
| Cold-start stochasticity | MEDIUM | N=1 accepted as exploratory. Compare to within-pair variance from prior experiments. |
| Re-eval throughput overhead | LOW | Runs at step 8 concurrent with mutations. CPU-bound <75s. Report mutations_per_wall_hour. |
| Sync hook interaction | LOW | Re-eval fires at step 8, after sync hook (step 4). Sync hook reads programs_processed from step 3a — unaffected by re-eval. |
| Metrics history rewriting | LOW | Separate reeval_* namespace. Primary namespace gated. |
| Archive diversity collapse | LOW | Monitored metric + amendment trigger (Section 6.3). |
| Stored seed semantics | LOW | Same seed applied to current archive may occasionally sample the same programs by coincidence, suppressing a deserved re-eval. Negligible in practice — archive composition changes continuously. |

---

## 11. Stop Criteria

**Stopping rule**: `max_generations=75 OR actual_fitness<0.005_at_gen20 OR invalidity>75pct_for_5_consecutive_gens OR futility_at_gen30`

**Per-run early termination**:
- Constructor `actual_fitness` < 0.005 at gen 20 (cold start failed)
- Invalidity rate > 75% for 5 consecutive generations
- PID dead 2 hours with no generation advance
- Re-evaluation hook crashes 3+ consecutive times → pause hook, continue without re-eval

**Futility stop** (gen 30): If treatment `actual_fitness` < control `actual_fitness` by >= 0.005, stop early with NEGATIVE verdict.

**No within-condition early stop**: Both treatment and control run to the same stopping condition.

---

## 12. Compute Budget

| Resource | Estimated usage |
|----------|----------------|
| GPU hours | ~200 hours (8 runs x 75 epochs x ~20 min/epoch) |
| Wall time | ~25 hours (8 runs concurrent) |
| Redis DBs used | 8 (DBs 1-8) |
| Mutation LLM | Qwen3-235B via LiteLLM proxy |
| Chain LLM | None |
| Re-eval overhead | <5% (CPU-bound, fingerprint-gated) |
| Soft fitness overhead | Negligible (sigmoid vs max in evaluate.py) |

---

## 13. Treatment Verification

### What proves the mechanism is applied?

1. **Log**: Treatment runs show `[ArchiveReEval] triggered` after gen 3
2. **Redis**: `{prefix}:reeval_count` non-zero and incrementing in treatment
3. **Metrics**: `reeval_elite_turnover` present in treatment, absent in control
4. **Control purity (log)**: Control runs show zero `[ArchiveReEval]` entries
5. **Control purity (Redis)**: `{prefix}:reeval_count` absent or zero in control runs

### Preflight checks

```yaml
treatment_checks:
  - type: config_check
    runs: [T1_A, T1_B]
    check: "archive_reeval == true"
    description: "Treatment runs have re-evaluation enabled"
  - type: config_check
    runs: [C1_A, C1_B]
    check: "archive_reeval == false"
    description: "Control runs have re-evaluation disabled"
  - type: log_pattern_present
    runs: [T1_A, T1_B]
    pattern: "[ArchiveReEval] triggered"
    description: "Treatment runs show re-evaluation activity"
    gen_gate: 5
  - type: log_pattern_absent
    runs: [C1_A, C1_B]
    pattern: "[ArchiveReEval] triggered"
    description: "Control runs do NOT show re-evaluation activity"
    gen_gate: 5
  - type: redis_key_absent
    runs: [C1_A, C1_B]
    key_pattern: "{prefix}:reeval_count"
    description: "Control runs have no re-evaluation counter in Redis"
    gen_gate: 10
  - type: config_check
    runs: [T1_A]
    check: "opponent_redis_db == 2"
    description: "T1_A reads opponents from DB 2"
  - type: config_check
    runs: [T1_B]
    check: "opponent_redis_db == 1"
    description: "T1_B reads opponents from DB 1"
  - type: config_check
    runs: [C1_A]
    check: "opponent_redis_db == 6"
    description: "C1_A reads opponents from DB 6"
  - type: config_check
    runs: [C1_B]
    check: "opponent_redis_db == 5"
    description: "C1_B reads opponents from DB 5"
  - type: generation_parity
    groups: [[T1_A, T1_B], [C1_A, C1_B]]
    max_drift: 5
    description: "Constructor-Improver pairs stay within 5 generations of each other"
```

### Soft fitness treatment verification

5. **Config check**: SF_A, SF_B, Both_A, Both_B have `adversarial.soft_fitness=true`
6. **Config check**: C_A, C_B, RE_A, RE_B have `adversarial.soft_fitness=false`
7. **Metric check**: Pop B fitness in SF/Both conditions does NOT saturate at 0.0 in gen 1-5 (sigmoid gives partial credit even for failed improvers)
8. **Smoke test**: `evaluate.py` with soft_fitness=true produces `fitness ∈ (0, 1)` for a D program that makes zero improvement (should be ~0.5, not 0.0)

### Phase 4 implementation gate (Volkov M3 + amendment)

Before launch, the implementation must pass:
1. Unit test: hook fires at epoch step 8 (after sync hook, after mutation gate opens)
2. Unit test: re-evaluated programs have updated fitness in archive
3. Unit test: `programs_processed` counter is NOT incremented by re-evaluation
4. Integration test: both populations re-evaluate simultaneously without deadlock
5. Unit test: soft fitness `evaluate.py` returns ~0.5 for zero-delta improvement (not 0.0)
6. Unit test: soft fitness `evaluate.py` returns > 0.5 for positive delta, < 0.5 for negative delta

---

## 14. Open Questions / Follow-up Experiments

### Implementation risks

1. **Stored seed re-sampling**: The seed must be stored in the Program object or Redis. Requires a schema addition to the Program data model.
2. **`archive_update_fitness` atomicity**: Re-evaluation must update the program in Redis and the archive cell atomically (or accept brief inconsistency).
3. **MetricsTracker gating** (Volkov advisory A1): `_refresh_changed_fitness()` race condition risk — implementation must guard this path before re-eval-triggered metric changes.

### Scientific risks

4. **Stored seed sampling may suppress valid re-evals**: If the seed happens to draw the same programs from a changed archive (unlikely but possible), a deserved re-eval is skipped. Effect is minimal in expectation.
5. **Root cause may not be stale fitness**: Improver stagnation may reflect fundamental difficulty asymmetry (binary improvement signal near Constructor optima). H2 directly tests this.

### Follow-up contingent on results

- If POSITIVE on H1 + H2: Add K=3 feedback (test the combination PATTERNS.md flags as highest value)
- If POSITIVE on H1 but NULL on H2: Re-eval helps G but Improver stagnation is structural. Consider move-operator specialisation for D.
- If NULL: Stale fitness is not the bottleneck. Examine difficulty asymmetry directly.
- If NEGATIVE: Re-eval is destabilising. Check diversity collapse (archive_occupied_cells).

---

*Ready for researcher approval (single human gate). See 02_review.md for Volkov APPROVED verdict.*
