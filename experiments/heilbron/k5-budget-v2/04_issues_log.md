# Issues Log: heilbron/k5-budget-v2

(File seeded from k5-budget-loose; entries below the v2 separator are inherited and refer to the prior invalidated experiment. v2-specific entries appear above.)

| # | Date (UTC) | Severity | Description | Resolution | Systemic? |
|---|-----------|----------|-------------|------------|-----------|
| *(to be filled during experiment)* | | | | | |

---

## v2 entries (heilbron/k5-budget-v2)

### 2026-04-17T10:34Z -- Silent treatment bug: n_opponents/source_prompt_k=1 instead of 3 (CAUGHT POST-LAUNCH)

- **When**: launch + first ~25 min (PIDs 2283482-2283489 — now dead)
- **What**: First v2 launch ran with `n_opp=1 source_prompt_k=1` (per `[AsymmetricPipeline] role=...` log line at 10:26:55), not the K=3 the experiment is named after. The whole hypothesis depends on K=3 (HoF size = composition source pool size).
- **Category**: config mistake / silent treatment fallback
- **Impact**: ~25 min of compute wasted on K=1 baseline-equivalent runs. No scientific harm — caught before any meaningful generation completed; Redis flushed before relaunch.
- **Root cause**: `gigaevo/experiment/launch_generator.py:_build_run_cmd` only injects a hand-picked subset of `contract.config.extra` keys (`stage_timeout`, `dag_timeout`, `max_*_per_generation`, `num_parents`, `mutation_mode`). It does NOT inject `n_opponents`, `source_prompt_k`, `archive_reeval`, `inner_iterations`, `significant_change`. The k5-budget-v2 manifest declared K=3 in `extra:` expecting it to propagate, but it never did. The sandbox only worked because its `launch.sh` was hand-written with `n_opponents=3 source_prompt_k=3` as direct Hydra overrides.
- **Fix applied**:
  1. SIGTERM all 8 PIDs + watchdog (graceful, ~12s).
  2. Added `n_opponents=3` and `source_prompt_k=3` to every arm's `extra_overrides` (16 entries total).
  3. Reset `lifecycle.status` to `implemented`, cleared launch metadata.
  4. Flushed Redis DBs 1-8.
  5. Released DB claims.
  6. Relaunched. New PIDs 2291939-2291946 + watchdog 2292454.
  7. Verified: `[AsymmetricPipeline] role=constructor feedback=composition n_opp=3 source_prompt_k=3 dg_tracker=yes` in all 8 logs at 10:34:51 — K=3 now actually loaded.
- **Systemic fix needed**: YES — `_build_run_cmd` should pass through ALL `contract.config.extra` keys as Hydra overrides, not a hand-picked subset. At minimum, it should warn when unrecognized keys are present (silent dropping is dangerous). The treatment-verifier agent should also grep `launch.sh` for the specific overrides the design depends on (`n_opponents`, `source_prompt_k`, etc.) before allowing launch.

### [EVENT 2026-04-17T10:34:34Z] -- Experiment relaunched after K=3 fix

- **When**: 2026-04-17T10:34:34Z
- **What**: Second launch of heilbron/k5-budget-v2. PIDs A3_G=2291939, A3_D=2291940, A5_G=2291941, A5_D=2291942, B3_G=2291943, B3_D=2291944, B5_G=2291945, B5_D=2291946. Watchdog PID 2292454. Anomaly cron 70c6e6d3 (every 2h at :23) and checkpoint cron dc2ae03d (every 4h at :47) were already in flight from the first launch and continue to apply.
- **Category**: launch
- **Impact**: Automated capture. K=3 verified post-init via log grep.

---

## Inherited entries (from k5-budget-loose, retained for context)


### [EVENT 2026-04-16T16:33:07Z] -- Experiment launched

- **When**: 2026-04-16T16:33:07Z
- **What**: gigaevo launch completed for heilbron/k5-budget-loose. Status: running. 8 runs (A3/A5/B3/B5 × {G,D}) on DBs 1-8. Watchdog PID 1914415.
- **Category**: launch
- **Impact**: Automated capture. Preflight required manual flush of DBs 3-8 (stale keys from pre-Amendment iterations).

### [EVENT 2026-04-16T17:04:29Z] -- Amendment #3: D prompt aligned with `d_sees_g_source=true` (gen-0 restart)

- **When**: 2026-04-16 (gen 0-1 across all 8 runs at amendment time: A3_G/D=gen1, A5_G/D=gen0, B3_G/D=gen1, B5_G/D=gen0; <2% of 50-gen budget; pre-reg anchors at gen 25 and 50 untouched)
- **What**: Static D prompt (`problems/heilbron_adversarial/pop_b/task_description.txt`) said "focus on GENERAL improvement strategies rather than exploiting specific point arrangements" and "Constructor programs change EVERY generation". Both conflict with the deployed treatment: `d_sees_g_source=true` (controlled variable, see 03_plan.md line 84) injects G's source code, and `FetchOpponentIdsStage.cache_handler=NO_CACHE` re-samples opponents per mutation, not per generation. Replaced lines 17-21 with a 16-line block acknowledging white-box source access and per-mutation cadence; added true anchoring (D sees archive survivors, so naive improvements have already been discarded). Method-neutral — no SLSQP/basin-hopping prescriptions. G prompt intentionally untouched (asymmetric awareness preserved).
- **Category**: amendment / protocol-deviation (gen 0 — zero scientific data discarded)
- **Impact**: Restart requires killing 8 PIDs + watchdog (1923500), cancelling crons (anomaly 0b6d8303, checkpoint cf317067), flushing DBs 1-8, status `running → implemented`, then `/experiment-launch`. Documented in 03_plan.md Amendment #3.

### [EVENT 2026-04-16T17:04:29Z] -- Experiment restart initiated

- **When**: 2026-04-16T17:04:29Z
- **What**: Full experiment restart. Progress at restart: A3_G=gen1 A3_D=gen1 A5_G=gen0 A5_D=gen0 B3_G=gen1 B3_D=gen1 B5_G=gen0 B5_D=gen0 (<2% of 50-gen budget).
- **Category**: restart
- **Impact**: All run progress destroyed. Redis DBs 1-8 flushed. Crons 0b6d8303 + cf317067 cancelled. Cause: Amendment #3 (D prompt alignment with `d_sees_g_source=true`).

### [EVENT 2026-04-16T20:17:37Z] -- Experiment re-launched (post Amendment #3)

- **When**: 2026-04-16T20:17:37Z
- **What**: gigaevo launch completed for heilbron/k5-budget-loose. Status: running. New PIDs A3_G=1961646 A3_D=1961647 A5_G=1961648 A5_D=1961649 B3_G=1961650 B3_D=1961651 B5_G=1961652 B5_D=1961653. Watchdog PID 1962169. Preflight passed; DBs 1-8 freshly claimed.
- **Category**: launch
- **Impact**: Automated capture. Crons (anomaly + checkpoint) to be re-scheduled.

### [EVENT 2026-04-16T20:48:00Z] -- Checkpoint recorded at gen ~1

- **When**: 2026-04-16T20:48:00Z
- **What**: First checkpoint after re-launch. All 8 runs alive, gen 1-2/50. Frontier values: A3_G=0.836, A3_D=0.173, A5_G=0.894, A5_D=0.221, B3_G=0.392, B3_D=0.428, B5_G=0.844, B5_D=0.137. Recent invalidity (last 20) = 0% across all runs.
- **Category**: checkpoint
- **Impact**: Automated capture. Diagnose flagged 1 MAJOR per run (false-positive about evolution config-group dump) and MINOR strategy-rejection on B3_D (33) / B5_D (51) — expected for improver D-role early on. No real issues.

### [DECISION 2026-04-16T20:48:00Z] -- Diagnose MAJOR treated as false-positive

- **When**: 2026-04-16T20:48:00Z (gen ~1 checkpoint)
- **Decision**: Continue running despite 1 MAJOR per run from diagnose: "Config group override may not be applied: evolution=steady_state".
- **Rationale**: The cfg dump format does not expose config-group sections like `evolution:`. The runs are demonstrably executing the steady-state strategy: programs are being generated, validated, mutated, and contributing to the frontier. The diagnose check is a known false-positive of the dump-introspection method, not a real config drift.
- **Pre-registration deviation?** No. No protocol changes. Logged for transparency at closeout.
- **Follow-up**: Open a tracker for improving the diagnose script so it does not flag this false-positive on adversarial-asymmetric runs.

### [DECISION 2026-04-16T20:48:00Z] -- D-role strategy-rejection MINOR accepted (all 4 D runs, not just flagged 2)

- **When**: 2026-04-16T20:48:00Z (gen ~1 checkpoint)
- **Decision**: Continue without intervention despite "Strategy rejection high" MINOR on D runs.
- **Observed cross-run rates** (added / strategy-rejected / rate):
  - G runs: A3_G 25/3 (10.7%), A5_G 18/3 (14.3%), B3_G 21/0 (0%), B5_G 21/2 (8.7%)
  - D runs: A3_D 24/41 (63.1%), A5_D 30/52 (63.4%), B3_D 26/33 (55.9%), B5_D 15/57 (79.2%)
- **Mechanism**: `MapElitesIsland.add()` (gigaevo/evolution/strategies/island.py:80-167) returns False when a program lands in a fitness cell already occupied by an equal-or-better elite. The diagnose hint "may need to lower significant_change config" is misleading — `significant_change` is a metric-formatter constant unrelated to strategy.add. Strategy rejection is "did not displace existing cell elite," not "missed a delta threshold."
- **Correction (supersedes prior bin-grid-asymmetry explanation in this entry's history).** Behavior space is `DynamicBehaviorSpace` (`gigaevo/evolution/strategies/models.py:170`) — bounds tighten to the observed range with `expansion_buffer_ratio=0.1`. So range asymmetry between G and D is NOT the driver of bin collisions. The real mechanism is the D fitness function combined with the K=1 evaluation contract.

- **Real mechanism — D fitness has a hard floor at 0.0 producing a massive point mass** (`problems/heilbron_adversarial/pop_b/evaluate.py:78,89`):
  ```python
  scores.append(min(max(delta, 0.0) / Q_MAX, 1.0))   # clamped at 0 below
  fitness = sum(scores) / len(scores)                # mean across opponents
  ```
  - `n_opponents=1` in this experiment (`config/pipeline/adversarial_asymmetric.yaml:75`, confirmed in `experiment.yaml`). So `scores` has length 1 and `fitness = single_score`.
  - Per-program fitness pulled from Redis at gen ~1-2 (4 D runs, 88-104 programs each):
    - A3_D: **68% at fitness=0.0 exactly**, 21 unique values
    - A5_D: **75% at fitness=0.0 exactly**, 19 unique values
    - B3_D: **61% at fitness=0.0 exactly**, 20 unique values
    - B5_D: **90% at fitness=0.0 exactly**, 10 unique values
  - With 60-90% of D programs sharing the EXACT value `0.0`, dynamic binning cannot help — they all land in the same cell. `island_max_size=75`, `SumArchiveSelector` keyed on fitness → only one program holds the cell, the other 50-80+ get strategy-rejected.
  - The `mean(scores)` framing is vestigial: code is written for K>1 but K=1 is deployed, so each D program gets a single 1-vs-1 trial. Outcome is essentially binary: lose (`delta ≤ 0` → fitness=0.0) or win (`delta > 0` → fitness in continuous tail).

- **Compounding factor — stale-elite calcification.** `archive_reeval=false` (`config/pipeline/adversarial_asymmetric.yaml:109`) + `d_archive_persistent=true`: a D program's stored fitness is computed once at mutation time against whichever G opponents existed THEN. Survivors are never re-scored. Old D programs keep their cells with fitnesses earned against weaker early-gen G opponents. New D programs facing stronger current G must beat those calcified scores.

- **K=1 white-box contract is intact.** D sees the source code of the single G opponent it is judged against (`source_injection.py:89-90` ranks by fitness, takes top-L; with K=L=1, the only opponent IS the prompt source). Bumping K with L fixed would break this contract because D would face K-L unseen opponents, weakening the white-box treatment. So the fix space is narrower than "just raise K".

- **Real failure signal would be `added → 0` (frontier stagnation).** All 4 D runs are still adding programs (15-30 each). No action warranted on operational grounds.

- **Pre-registration deviation?** No.

- **Follow-ups**:
  - Diagnose script is miscalibrated for improver-role runs with persistent archive: threshold `rs > 10` (absolute count, ignores `added`) flags every healthy D run after a few epochs. Should switch to recent-window rate AND check `added` is also growing. Open a tracker.
  - Diagnose hint text "may need to lower significant_change config" is wrong: `significant_change` is a metric-formatter constant unrelated to strategy.add. Real driver is **fitness function point mass at 0.0** (60-90% of D programs share fitness=0.0 exactly under K=1 + hard floor). Update hint.
  - **Design implication for next Heilbron-adversarial experiment.** Two non-overlapping fixes available — they cannot both be cheap:
    - **Fix 1: smooth D fitness (cheap, preserves white-box contract).** Replace `max(delta, 0.0)` with `tanh(delta / Q_MAX)` (or sigmoid). Single-trial losses spread continuously in [-1, 1] instead of collapsing to 0.0. 1-line change in `evaluate.py:78`. Single-opponent variance remains, but the point mass is broken.
    - **Fix 2: K=L=k for k>1 (expensive, preserves contract).** D plays k opponents AND sees k source codes. Prompt grows by ~k× source-code tokens (~100-300 tokens per G program at Heilbron sizes). Fitness becomes ∈ {0/k, 1/k, ..., k/k} + continuous tail. Adds `n_improved` as a meaningful behavior dimension. Costs ~30-50% more input tokens per D mutation.
    - **Do not combine K>L (cheap-looking but breaks contract).** D sees L sources but is judged on K opponents — selection rewards generic improvers, not source-aware exploits. Would silently undermine the `d_sees_g_source=true` treatment.

### [DECISION 2026-04-16T??:??:??Z] -- Experiment scientific viability under review

- **When**: 2026-04-16, post gen ~1 mechanism investigation
- **Decision pending**: whether to stop `heilbron/k5-budget-loose` mid-flight and pivot to a redesigned experiment with smoothed D fitness, OR let it complete and treat its D arm as a pre-registered null result.
- **Rationale**:
  - The K=1 + hard-floor + `archive_reeval=false` + `d_archive_persistent=true` combination produces a D fitness landscape where 60-90% of programs collapse to fitness=0.0 exactly. This is structural, not a transient gen-1 artifact.
  - Researcher reports the same symptom across **all previous Heilbron-adversarial experiments**: D consistently struggles to achieve nontrivial improvement. The pattern is now mechanistically explained — D's fitness function does not provide gradient for "almost improved" or "tried hard but didn't beat the elite". Evolution effectively cannot climb out of the 0.0 plateau via LLM mutation noise alone.
  - All four arms in this experiment (A3/A5/B3/B5) share the same broken D fitness. Therefore the *between-arm comparison* on the D side is comparing four variants of a fitness function that doesn't evolve. The G side may still produce valid signal (G's fitness has no analogous floor), but the joint claim about asymmetric co-evolution depends on D actually evolving.
- **Options under consideration**:
  - **(a) Stop now, redesign.** Kill 8 PIDs + watchdog, mark `running → invalid` with the structural-flaw reason recorded, pre-register a new experiment with Fix 1 (tanh/sigmoid D fitness) + the same arm structure. Cost: ~24h compute already spent on flawed runs.
  - **(b) Let it complete, analyze G side only.** D arm becomes a pre-registered null. G arm still informative if treatments differ on G's behavior. Risk: paper claim shifts from "asymmetric co-evolution" to "G evolution under varied feedback" — narrower.
  - **(c) Let it complete, analyze both, document the D-side flaw at closeout.** Still useful as a calibration / failure-mode study but not the originally pre-registered hypothesis test.
- **Pre-registration deviation?** Stopping mid-flight (option a) is a deviation requiring `running → invalid` transition with documented cause. Continuing (b/c) is not a deviation but the interpretation must acknowledge the D fitness is structurally broken.
- **Researcher decision (2026-04-16T18:55:05Z): option (a) — stop now, redesign later.** Stopping mid-flight to avoid burning further compute on a structurally flawed D fitness. Redesign deferred (researcher wants thinking time before committing to a specific fix).

### [EVENT 2026-04-16T18:55:05Z] -- Experiment stopped (running → invalid) due to structural D-fitness flaw

- **When**: 2026-04-16T18:55:05Z
- **What**: Mid-flight stop. Status `running → invalid`. Killed: 8 run PIDs (1961646–1961653) + watchdog (1962169). Cancelled: anomaly cron 759ce97f, checkpoint cron c07535f1. **Redis DBs 1-8 NOT flushed** — preserving fitness data for redesign analysis.
- **Progress at stop**: gen ~1-2 across all 8 runs (well under the original 50-gen budget). Frontier values from last checkpoint: A3_G=0.836, A3_D=0.173, A5_G=0.894, A5_D=0.221, B3_G=0.392, B3_D=0.428, B5_G=0.844, B5_D=0.137.
- **Category**: stop / protocol-deviation
- **Impact**: Pre-registration deviation. Cause: D fitness function (`max(delta, 0)/Q_MAX` mean over K=1 opponents) produces 60-90% point mass at fitness=0.0, eliminating evolutionary gradient for D. Documented in this issues log (DECISION above) and now a known structural issue across all Heilbron-adversarial experiments to date. Redesign pending researcher decision on Fix 1 (smoothed fitness, 1-line change) vs Fix 2 (K=L=k>1, prompt cost) vs other options.

### [EVENT 2026-04-17T14:32:08Z] -- Checkpoint recorded at gen ~12

- **When**: 2026-04-17T14:32:08Z
- **What**: Checkpoint recorded. Avg gen=12 (A3:15, A5:13, A5_D:12, B3:11, B3_D:12, B5_G:10, B5_D:11). Diagnose: HEALTHY.
- **Category**: checkpoint
- **Impact**: Automated capture. Nothing beats baseline 0.03449 yet; A3_D leads at 0.03257 (94%). A-arms (composition) dominate B-arms (gradient_in_prompt).

### [CHECKPOINT gen=12] -- No deviations or decisions. All runs healthy.

- Pre-registration: intact.
- Stopping rule: all cells gen<25, futility check deferred.
- Protocol decisions: none.
- Mutation/gen ratio note (from earlier inspection): G runs overshoot budget target=8 (doing 10-15/gen), compressing A5 actual D:G ratio to ~3.3:1 instead of pre-registered 5:1. Not a protocol deviation (budget was pre-registered as ceiling, not floor); flagged for closeout discussion.

### [EVENT 2026-04-17T19:31:56Z] -- Checkpoint #2 recorded at gen ~18

- **When**: 2026-04-17T19:31:56Z
- **What**: 2nd checkpoint. Avg gen=18 (A3:20/20, A5:21/21, B3:16/17, B5:13/14). All 8 PIDs alive (~12h uptime).
- **Category**: checkpoint
- **Impact**: B5_G advanced 0.02681→0.03346 (78%→97% baseline) — now the closest arm to beating SOTA. A-arms still dominate on average but B5_G individual run overtook them.

### [CHECKPOINT gen=18] -- No deviations or decisions. All runs healthy.

- Stopping rule: deferred (all cells gen<25).
- No protocol decisions this checkpoint.
- Skipped full /experiment-diagnose this cycle (ran 15 min ago, HEALTHY, confirmed alive via ps + Redis progression). Would re-run if any signal changed.
