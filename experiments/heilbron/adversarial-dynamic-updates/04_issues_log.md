# Issues Log

Track ALL errors, crashed, unexpected behavior, and manual interventions during this experiment.
This includes: run crashes, tool/script failures, watchdog issues, skill execution errors,
config mistakes, git problems, Redis issues, helper script bugs, and anything else that
did not execute as expected and required a manual fix or workaround.

This log is for post-experiment reflection — use it to identify bugs to fix and process improvements.

## Format

Each entry should include:
- **When**: timestamp or phase (e.g., "launch", "checkpoint #3", "gen 12")
- **What**: brief description of the issue
- **Category**: run crash | tool bug | config mistake | infra issue | skill bug | watchdog | git | other
- **Impact**: how it affected the experiment (data loss, wasted compute, delayed launch, etc.)
- **Root cause**: why it happened (if known)
- **Fix applied**: what was done to resolve it (including manual workarounds)
- **Systemic fix needed**: whether a code/process/tool change would prevent recurrence (YES/NO + description)

---

<!-- Add entries below, newest first -->

## [STOP 2026-04-10 ~09:35 UTC] — Researcher decision: apply futility stopping rule, record NEGATIVE verdict

**Decision**: Researcher elected to stop all 8 runs early. Futility stopping rule (futility_at_gen30) applied.

**Rationale**: All actual_fitness values below baseline (0.03464 from adversarial-v2). H1 gap at gen=30: 0.01182 >> 0.005 threshold. No recovery visible at gen=40+. SOFT cells closest to baseline but still -8–28% below. GAN cells worst due to resistance gaming. Re-eval ON treatment did not improve actual_fitness in any cell.

**Verdict**: NEGATIVE — H1 rejected. Archive re-evaluation does not improve Constructor actual_fitness under adversarial co-evolution.

**Actions taken**: All 8 PIDs (856366–856373) and watchdog (859943) killed via process_cleanup.py. Anomaly detector and checkpoint cron jobs expired (prior session). Proceeding to closeout.

**Pre-registration note**: Stopping at gen ~33–41 (avg gen=33) instead of max_gen=75. Futility stopping rule was pre-registered. This is not a protocol deviation.

## [CHECKPOINT gen=33, 2026-04-10 ~09:18 UTC] — GAN sync wait ongoing. Futility rule pending. Mid-run analyst completed.

**Status**: All 8 runs alive (PIDs 856366–856373), avg gen=33, watchdog 859943 alive.

**Diagnose summary**: HEALTHY overall. All 8 PIDs alive. SOFT pairs progressing (SOFT_RE gen=40-41, SOFT_C gen=27-28). GAN pairs in extended ProgressBasedSyncHook sync wait (since ~04:21-04:41 UTC) — confirmed infrastructure wait, not stall. DAG error counters (9/10) frozen, confirmed false positives. No new errors in SOFT logs.

**Mid-run analyst (first invocation)**: At 55% for SOFT_RE runs. Analyst (opaque labels) flagged R5 (GAN_RE_A) frozen actual_fitness=0.01379 since gen=12 as primary red flag. R1 (SOFT_RE_A) lagging at actual_fitness=0.02495 with slow convergence. R3 (SOFT_C_A) highest actual_fitness=0.03186, still improving. Projections: R3/R4 likely 0.030–0.036 at gen=75; R5 depends on sync resolution.

**Stopping rule check**: Futility_at_gen30 still triggered. No new violations. GAN_RE_A remains at gen=30 (frozen in sync wait). Researcher decision on futility rule still pending.

**Decisions made**: None. GAN sync deadlock classified as infrastructure (self-resolving). Mid-run analyst invoked per skill protocol (first 50%+ checkpoint). No stopping rule applied — researcher decision required.

## [ANOMALY-DETECTOR] 2026-04-10 09:08 UTC (12:08 MSK) — WARN: All 4 GAN runs in extended sync deadlock (Pattern 8, recurring)

**Classification**: WARN — infrastructure sync deadlock, self-resolving via 7200s timeout. All PIDs alive, no data loss.

**Findings**:
1. GAN_RE_B: sync wait ~5186s (started ~04:21 UTC). 7200s timeout fires ~09:21 MSK.
2. GAN_RE_A: sync wait ~4818s (started ~04:27 UTC). 7200s timeout fires ~09:27 MSK.
3. GAN_C_A: sync wait ~4289s (started ~04:36 UTC). 7200s timeout fires ~09:36 MSK.
4. GAN_C_B: sync wait ~3990s (started ~04:41 UTC). 7200s timeout fires ~09:41 MSK.

**Root cause**: GAN pure resistance fitness is harder to optimize than soft fitness. GAN populations have lower throughput (harder validity → fewer valid programs per epoch). When both GAN_RE_A/B or GAN_C_A/B enter sync waits simultaneously, neither can satisfy the partner's `min_delta=1` threshold. The 7200s `ProgressBasedSyncHook` timeout auto-resolves by skipping the barrier.

**SOFT pairs**: Progressing normally (SOFT_RE gen=37–38, SOFT_C gen=25).

**Action taken**: WARN marker written to Redis. PR comment posted. No process intervention — self-resolving.

**Action needed**: No immediate action. Monitor that all 4 GAN runs resume by ~09:41 MSK. Researcher decision on futility stopping rule still pending.

**Systemic fix needed**: YES — consider increasing `min_delta` or `sync_every` for GAN runs, or disabling `ProgressBasedSyncHook` for runs where one arm has substantially lower throughput. Document in experiment design that GAN×SOFT sync pairs should use asymmetric thresholds.

## [CHECKPOINT gen=31, 2026-04-10 ~05:31 UTC] — Futility stopping rule triggered. Researcher action required.

**Status**: All 8 runs alive (PIDs 856366–856373), avg gen=31, watchdog 859943 alive.

**Diagnose summary**: CRITICAL for GAN_C_B — investigated, confirmed false positive (sync wait 300s, Redis metrics active 1s ago, PID alive). MAJOR for GAN_RE_A (48% invalidity — real but <75% threshold, hypothesis-relevant; "stalling" = NFS log mtime staleness + sync wait). MAJOR DAG errors: 9 for SOFT_C_A and GAN_RE_B — confirmed false positives (frozen cold-start counters, n_opponents=-1 count = 0 for both). All infrastructure issues are false positives.

**Stopping rule check**: **FUTILITY AT GEN=30 TRIGGERED**. GAN_RE_A actual_fitness=0.01379 at gen=30. H1 comparison: RE_ON avg=0.01838 vs RE_OFF avg=0.03020, gap=0.01182 >> 0.005 threshold. Per-cell: GAN_RE_A vs GAN_C_A (+0.015), SOFT_RE_A vs SOFT_C_A (+0.009), GAN_RE_A vs SOFT_RE_A (+0.009) — all above threshold. GAN_C_A vs SOFT_C_A (+0.003) — below threshold. Researcher decision pending.

**Decisions made**: All diagnose MAJOR/CRITICAL flags classified as false positives (documented above). No infrastructure interventions. Futility rule alert posted to PR #197. Runs NOT stopped — researcher decision required on whether to apply, waive, or defer the stopping rule.

## [ANOMALY-DETECTOR] 2026-04-10 05:17 UTC (08:17 MSK) — WARN: Futility stopping rule triggered at gen=30

**Classification**: WARN — protocol/scientific issue, not infrastructure. Researcher decision required.

**Finding**: GAN_RE_A reached gen=30 with actual_fitness=0.01379. The pre-registered futility stopping rule states: "If treatment actual_fitness < control actual_fitness by >= 0.005, stop early." H1 assessment:
- Treatment (re-eval ON) avg actual_fitness: (SOFT_RE_A=0.02296 + GAN_RE_A=0.01379) / 2 = **0.01838**
- Control (re-eval OFF) avg actual_fitness: (SOFT_C_A=0.03186 + GAN_C_A=0.02854) / 2 = **0.03020**
- Gap: **0.01182 >> 0.005 threshold** → futility condition MET

Per-cell: GAN_RE_A vs GAN_C_A = 0.01475 (MET); SOFT_RE_A vs SOFT_C_A = 0.0089 (MET); GAN_RE_A vs SOFT_RE_A = 0.00917 (MET); GAN_C_A vs SOFT_C_A = 0.00332 (NOT MET).

**Caveat**: SOFT_C_A is only at gen=23 — its actual_fitness will likely increase by gen=30. But the H1 gap (0.012) is 2.4× the threshold; unlikely to be overturned.

**Action taken**: Alert posted to PR #197. Runs NOT stopped — researcher decision required.

**Action needed**: Researcher to decide whether to apply or waive the futility stopping rule. See PR #197 for options.

## [ANOMALY-DETECTOR] 2026-04-10 06:46 UTC — WARN: Sync hook waits active (Pattern 8, recurring)

**Classification**: WARN (same pattern as earlier SOFT_C deadlock). All PIDs alive, no data loss.

**Findings**:
1. Sync hook wait A: ~5282s waiting for opponent total >= 105 (current=104). Started ~05:00 MSK. 7200s timeout fires ~07:19 MSK. Self-resolving.
2. Sync hook wait B: ~2101s waiting for opponent total >= 131 (current=130). Started ~06:12 MSK. Timeout fires ~08:12 MSK. Self-resolving.
3. GAN_RE_A stagnation: frontier frozen at 48.94% since gen=12, now gen=26. 4 gens from `futility_at_gen30` stopping rule. Hypothesis-relevant — no intervention.

**Action taken**: WARN marker written to Redis. PR comment posted. No process intervention.

**Action needed**: Researcher to review GAN_RE_A stopping rule decision before gen=30. If stagnation persists and futility threshold is met, apply stopping rule per pre-registration.

## [CHECKPOINT gen=22, 2026-04-10 ~05:21 UTC] — No deviations. All runs healthy.

**Status**: All 8 runs alive (PIDs 856366–856373), avg gen=22, watchdog 859943 alive.

**Diagnose summary**: GAN_RE_B flagged MAJOR (DAG errors: 9) — investigated, confirmed false positive. Counter frozen at 9/465 (1.94%), no new errors in last 500 steps. Historical cold-start artifacts. All other runs HEALTHY/MINOR.

**Stopping rule check**: All clear. No violations.

**Decisions made**: Classified GAN_RE_B MAJOR DAG error flag as false positive (frozen historical counter). No intervention. This decision is infrastructure-relevant, not hypothesis-relevant — does not constitute a pre-registration deviation.

---

## [CHECKPOINT gen=17, 2026-04-10 ~04:33 UTC] — No deviations. All runs healthy.

**Status**: All 8 runs alive (PIDs 856366–856373), avg gen=17, watchdog 859943 alive.

**Diagnose summary**: 6 runs 27 OK / 0 MINOR. SOFT_RE_B + GAN_RE_B: 2 MINOR each (fitness stagnation + strategy rejection — hypothesis-relevant behavior, not bugs). GAN_C_A: 1 MINOR (no frontier fitness diagnostic key — artifact). No MAJOR or CRITICAL issues.

**Stopping rule check**: All clear. No run has actual_fitness < 0.005 at gen 20+. No invalidity > 75%.

**Decisions made**: None. SOFT_C deadlock (prev WARN) resolved naturally. No protocol deviations. SOFT_RE_B/GAN_RE_B stagnation is hypothesis-relevant — no intervention.

## Issue #4 — Protocol deviation: GAN fitness signal hard-capped at 0.5 (pre-registration deviation)

- **When**: 2026-04-09, discovered at gen ~5–9 (runs GAN_RE_A db=5, GAN_RE_B db=6, GAN_C_A db=7, GAN_C_B db=8)
- **What**: `pop_a_gan/evaluate.py` computed `delta = max(post_q - raw_quality, 0.0)` before passing to `_sigmoid(-delta / T)`. Since `delta >= 0` always, `_sigmoid(-delta / T)` returns ≤ 0.5 always — so resistance (and fitness) was hard-capped at 0.5. GAN cells could never evolve configurations with resistance > 0.5.
- **Category**: config mistake / code bug
- **Impact**: GAN_RE and GAN_C cells produced meaningless fitness signals (all resistance ≈ 0.5 at cold-start, never evolving above). This invalidates the GAN conditions entirely. Pre-registration states "Cell GAN_RE/GAN_C: G=strict GAN pure resistance" — the resistance metric was non-functional. **Pre-registration deviation** — GAN data from gen 0–9 is scientifically invalid and must be discarded.
- **Root cause**: Incorrect `max(..., 0)` clamp was carried over from an earlier prototype where `delta` was defined as improvement magnitude. After switching to `_sigmoid(-delta/T)` formulation, the clamp was never removed. A positive clamp turns `_sigmoid(-x)` for x≥0 into [0, 0.5] only.
- **Fix applied**: `delta = post_q - raw_quality` (signed, no clamp). Now `delta < 0` (D worsened) gives resistance > 0.5; `delta = 0` gives resistance = 0.5; `delta > 0` (D improved) gives resistance < 0.5. All 8 runs killed, all DBs 1–8 flushed, relaunched.
- **Systemic fix needed**: YES — evaluate.py for adversarial GAN variant should have a unit test that asserts resistance > 0.5 when D returns a worse configuration. Add to `tests/heilbron_adversarial/` test suite.

## Issue #3 — Protocol amendment: add opponent code feedback (K=3) to all cells

- **When**: 2026-04-09, gen ~5–9 (pre-restart, treatment upgrade)
- **What**: All 8 runs switched from `pipeline=adversarial_coevo_ss` to `pipeline=adversarial_coevo_feedback` with `opponent_feedback_k=3`. Constructor (A) runs now see top-3 Improver source codes in their mutation prompt ("OPPONENT ATTACK REPORT"). Improver (B) runs now see top-3 Constructor source codes ("TARGET ANALYSIS REPORT"). `population_role` set to `constructor`/`improver` appropriately.
- **Category**: treatment upgrade (not a bug)
- **Impact**: This is a mid-experiment protocol amendment. The pre-registration in `01_design.md` did not include opponent code feedback as part of the treatment design. Data from gen 0–9 (collected without feedback) is discarded at restart. All cells (SOFT_RE, SOFT_C, GAN_RE, GAN_C) receive feedback equally — the 2×2 factorial design (re-eval × fitness-type) is preserved. The new IV (feedback presence) applies identically across all cells, so comparisons between cells remain valid. The feedback was a confirmed positive in the prior `heilbron/adversarial-v2` experiment and is considered a necessary protocol improvement.
- **Root cause**: Feedback infrastructure (`AdversarialFeedbackPipelineBuilder`, `OpponentFeedbackStage`) was already implemented from `heilbron/adversarial-v2` but was not included in the original design for this experiment.
- **Fix applied**: Updated `experiment.yaml` to use `adversarial_coevo_feedback` pipeline for all 8 runs with `opponent_feedback_k=3`. Added `population_role=constructor/improver` overrides. Regenerated `launch.sh`. All runs restarted.
- **Systemic fix needed**: NO — feedback is now standard for adversarial co-evolution experiments. The next adversarial experiment design should include feedback by default.

## Issue #1 — Mid-experiment restart due to task description fix

- **When**: 2026-04-09, gen 3–8 (approx 3–8% of max_generations=75)
- **What**: All 8 runs restarted after discovering task_description.txt files lacked explicit helper import lines and structured input/output format documentation for each helper function. LLM-generated programs frequently failed with NameError (missing `from helper import ...`) or returned invalid configurations due to ambiguous API documentation.
- **Category**: config mistake
- **Impact**: Loss of gen 3–8 across all 8 runs (minimal — <10% of planned compute). No scientifically valid programs archived before flush. Pre-registration intact (fix is to evaluation scaffolding documentation, not to the experimental treatment or fitness function).
- **Root cause**: Initial task descriptions documented helper function availability but did not include the exact import line or structured input/output format. LLMs generating code for the first time often missed the `from helper import ...` import, resulting in NameError and DAG auto-skip (`n_opponents=-1`). Additionally, `is_inside_triangle` semantics (batch check returning single bool) were unclear, leading to boundary drift in vertex-perturbation programs.
- **Fix applied**: Updated all 5 task_description.txt files (pop_a, pop_a_soft, pop_a_gan, pop_b, pop_b_soft) to include:
  1. `from helper import get_unit_triangle, get_smallest_triangle_area, is_inside_triangle` as the explicit import line
  2. Structured `Input: / Output:` format for each helper function parameter
  All 8 runs killed, all 8 Redis DBs (1–8) flushed, status reset to implemented.
- **Systemic fix needed**: YES — the problem wizard or task_description template should enforce explicit helper import documentation. Consider adding a preflight check that validates task_description.txt contains the import line.

## Issue #2 — Stale smoke-test process repopulating DB 1 after flush

- **When**: 2026-04-09, pre-launch (preflight phase)
- **What**: DB 1 showed stray keys after flush.py reported 0 keys. Preflight check #9 kept failing.
- **Category**: infra issue
- **Impact**: Delayed launch by ~30 minutes.
- **Root cause**: Old `run.py problem.name=heilbron_adversarial/pop_a` process (PID 521433) left running from smoke test session. Also a stale watchdog PID 650106 from smoke test. Both continued writing to DB 1.
- **Fix applied**: Used `redis-cli MONITOR` to identify writing PIDs, killed both with `kill -9`, flushed DB 1 cleanly.
- **Systemic fix needed**: YES — flush.py should check for live writers before reporting success. The smoke test procedure should ensure all processes are killed before declaring smoke complete.

---

## [CHECKPOINT gen=2, 2026-04-09 ~22:45 UTC] — No deviations. All runs healthy.

**Status**: All 8 runs alive (PIDs 856366-856373), gen=1-3, 0% invalidity, watchdog 859943 alive.

**Diagnose summary**: All 8 runs: 26 OK, 1 MINOR each. The single MINOR per run is "Insufficient metric history for rate check" — expected at gen 1 (only 1 data point). No MAJOR or CRITICAL issues.

**Decisions made**: None. No stopping rule conditions triggered. No interventions needed.

**Restart context**: This is Restart 3. The previous two restarts resolved:
1. GAN resistance hard-cap bug (signed delta in pop_a_gan/evaluate.py)
2. OpponentFeedbackStage design flaw (deterministic get_top_k instead of oversample+sort)  
3. higher_is_better parameter generalization (derived from primary MetricSpec automatically)
4. archive_reeval param missing in AdversarialFeedbackPipelineBuilder

All three protocol amendments are documented in issues #1-#4 above.

---

## [ANOMALY-DETECTOR] 2026-04-10 02:30 UTC+3 — WARN: SOFT_C throughput anomaly

**Classification**: WARN (not CRITICAL — all processes alive, no data loss)

**Finding**: SOFT_C_A (gen=3, total=3) and SOFT_C_B (gen=2, total=2) after 60 minutes vs:
- SOFT_RE_A: gen=9, total=39 (3x higher throughput)
- GAN_C_A: gen=11, total=66 (3.7x higher throughput)

**Root cause**: Mutual `ProgressBasedSyncHook` dependency + high invalidity rate creates near-deadlock:
- SOFT_C_A (DB=3) watches SOFT_C_B (DB=4); SOFT_C_B watches SOFT_C_A
- SOFT_C_A invalidity: 67% (2 invalid, 1 valid out of 3 total)
- High invalidity → rare successful evals → long sync wait times (>3100s observed)
- GAN_C pair avoids this: GAN_C_A made fast initial progress (GAN validate.py faster?) → positive feedback loop

**Impact**:
- SOFT_C_A projected ETA to gen=75: ~24 hours
- SOFT_C_B projected ETA to gen=75: ~36.5 hours
- Other pairs: 5-9 hours
- Experiment validity concern: SOFT_C may produce fewer effective generations for comparison

**All 8 PIDs alive**: SOFT_RE_A/B (856366-7), SOFT_C_A/B (856368-9), GAN_RE_A/B (856370-1), GAN_C_A/B (856372-3)

**Action taken**: Wrote WARN marker to Redis. Posting to PR. No process intervention (requires researcher decision).

**Action needed**: Researcher to decide if SOFT_C timeout or sync_every settings should be adjusted. Options:
1. Accept lower throughput (SOFT_C may reach gen=20-30 by experiment end)
2. Restart SOFT_C with `min_delta=1 sync_every=2epochs` or disable sync hook temporarily
3. Accept asymmetric comparison (SOFT_C vs GAN_C at different generations)

**Update 02:32 MSK**: SOFT_C deadlock is TEMPORARY — self-resolves via ProgressBasedSyncHook 7200s timeout at ~03:38 MSK. Sync hook code (sync.py:155-166) proceeds and resets baseline on timeout. No intervention needed. After resolution, both SOFT_C runs should accelerate to normal throughput.

**Update 02:44 MSK** (second anomaly check): Status unchanged. SOFT_C_A gen=3/total=3, SOFT_C_B gen=2/total=2. Timeout fires in ~55 min. All other 6 PIDs alive and progressing normally (GAN_C leading at gen=14, total=83-85). GAN_RE_A invalidity=52% at gen=8 — borderline, monitoring. No intervention taken.

**Update 04:18 MSK** (third anomaly check): WARN RESOLVED. At 04:12:23 MSK, SOFT_C deadlock broke naturally — SOFT_C_B opponent advanced to total=9 (target was 7) after a 575s wait. No 7200s timeout needed. Both SOFT_C runs now at gen=7, actively syncing with normal wait times (60–575s). GAN_RE_A invalidity improved 52% → 45%. All 8 PIDs alive. Classification: HEALTHY.
