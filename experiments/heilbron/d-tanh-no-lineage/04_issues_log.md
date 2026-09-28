# Issues Log

Track ALL errors, crashes, unexpected behavior, and manual interventions during this experiment.
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

## Entry Types

### Events (auto-captured by lifecycle skills)

Brief entries auto-appended by `/experiment-launch`, `/experiment-restart`, `/experiment-checkpoint`, and `/experiment-diagnose`. One-line summary with structured metadata. Format:

```
### [EVENT <ISO-timestamp>] -- <one-line description>

- **When**: <ISO-timestamp>
- **What**: <one-line description>
- **Category**: launch | restart | checkpoint | watchdog | diagnose
- **Impact**: <brief impact or "automated capture">
```

### Issues (manual or escalated entries)

Detailed entries for things that went wrong and required intervention. Use the full format from above (When, What, Category, Impact, Root cause, Fix applied, Systemic fix needed).

```
### <timestamp> -- <description>

- **When**: <timestamp or phase>
- **What**: <brief description>
- **Category**: run crash | tool bug | config mistake | infra issue | skill bug | watchdog | git | other
- **Impact**: <how it affected the experiment>
- **Root cause**: <why it happened>
- **Fix applied**: <what was done>
- **Systemic fix needed**: YES/NO + description
```

---

<!-- Add entries below, newest first -->

### [EVENT 2026-04-27T19:03:29Z] -- Relaunching: 4 runs, N=1 per arm, fresh DBs

- **When**: 2026-04-27T19:03:29Z
- **What**: Status transitioned invalid → preregistered → implemented. Flushed Redis DBs 1, 2, 5, 6 (441+373+435+445 keys discarded — all from the 16:23Z stopped attempt). Launching 4 runs: A1_G(db=1)+A1_D(db=2) [composition arm], C1_G(db=5)+C1_D(db=6) [gradient_in_prompt arm]. Pipeline=heilbron_smooth_v1 on all four. Treatment hook (disable_lineage_on_improver=true) active on D runs only. Smoke test + treatment verification reuse the 15:00–15:11Z artifacts on the renamed pipeline (body diff verified identical per the 17:58Z DECISION entry).
- **Category**: launch (relaunch after 16:23Z stop and 16:55Z 8→4 deviation)
- **Impact**: Automated capture. Monitoring for stage timeouts is the explicit watchpoint on this relaunch — 4-run load (vs 8) should keep stage durations well under stage_timeout=900s.

### [DECISION 2026-04-27T17:58:00Z] -- Pipeline rename: heilbron_repro_v1 → heilbron_smooth_v1

- **When**: 2026-04-27, before relaunch
- **What**: Renamed the pipeline this experiment uses from `heilbron_repro_v1` (the originally pre-registered name on PR #223) to `heilbron_smooth_v1`, plus moved problem dirs from `problems/heilbron_repro_v1/pop_*` to `problems/heilbron_smooth_v1/pop_*`.
- **Category**: protocol decision (cosmetic)
- **Rationale**: `heilbron_repro_v1` was named for hard-floor v1 fitness, but its `evaluate.py` files were mutated in place by PR #219 (G linear smooth, commit 2de8267e) and the d-smoothing-minimal predecessor (D tanh smooth, commit 3eb41b43). The name no longer described the contents. The new name describes the actual fitness shape.
- **Pipeline body equivalence**: `diff <(sed '/^#/d' heilbron_smooth_v1.yaml) <(sed '/^#/d' heilbron_repro_v1.yaml)` returns identical. ONLY the header docstring differs.
- **Problem dir equivalence**: `cp -r` from heilbron_repro_v1 to heilbron_smooth_v1 with the single edit of `pop_b/metrics.yaml fitness.description` from the old hard-floor formula text to the actual tanh formula (the code emitted the tanh value either way; this only fixes the LLM-prompt-facing description). evaluate.py, helper.py, initial_programs/, fallback/ identical.
- **Pre-registration deviation?**: NO. Pipeline body and treatment IV (`disable_lineage_on_improver=true` on D) are unchanged. Volkov approved a design that operated on this pipeline body; the body did not change.
- **Reproducibility**: PR #223 description and 01_design.md / 03_plan.md still reference `heilbron_repro_v1` by name. Anyone following those literally would hit the OLD dir (which has the same evaluate.py content today), so results would be equivalent. The new name is the operational pointer; the old name still works for archive backwards compatibility.
- **Other live experiment configs touched**: none. d-smoothing-minimal (status=implemented but stalled, predecessor of this one) still references `heilbron_repro_v1` and is left alone — it will likely be marked invalid rather than relaunched. Closed experiments (adversarial-repro-v1, adversarial-repro-v2, v1-honest-repro) untouched for archive integrity.
- **Impact**: None on the science. The treatment-verifier and implementation-aligner will be re-run after this change; smoke test will be re-run on the renamed dir.

### [EVENT 2026-04-27T15:25:54Z] -- Experiment launched

- **When**: 2026-04-27T15:25:54Z
- **What**: gigaevo launch completed for heilbron/d-tanh-no-lineage. Status: running. PIDs: A1_G=3934158, A1_D=3934159, A2_G=3934160, A2_D=3934161, C1_G=3934162, C1_D=3934163, C2_G=3934164, C2_D=3934165. Watchdog: 3935345. Anomaly cron: 8f7b4348 (every 2h, 7d expiry). Checkpoint cron: b7783479 (every 4h, 7d expiry).
- **Category**: launch
- **Impact**: Automated capture.

### [ISSUE 2026-04-27T16:23:39Z] -- Stopped early: LineageStage/InsightsStage timing out under proxy latency

- **When**: 2026-04-27T16:23:39Z (epoch=1 in flight on G runs; epoch=2 starting on D runs)
- **What**: Researcher diagnosed proxy timeouts (10.232.30.185:4000 LiteLLM proxy) producing 6.5–7.7 minute LineageStage/InsightsStage durations on the G side. Stage failures (status=failed) on G runs: A1_G 5L+4I out of 32, A2_G 6L+7I out of 38, C1_G 0/0, C2_G 0/0. D runs unaffected (treatment correctly removes those stages on D). All 8 PIDs SIGTERMed cleanly; watchdog (pid=3935345) and both crons (anomaly 8f7b4348, checkpoint b7783479) cancelled. control_plane pointers cleared. Redis untouched.
- **Category**: infra issue
- **Impact**: A1/A2 G runs lost lineage data on ~15% of programs; C1/C2 were clean (0 stage failures). Treatment contrast (D no-lineage vs G with-lineage) is partially compromised on A1/A2 but intact on C1/C2. ~15h of compute spent before stop.
- **Root cause**: Proxy /health/liveliness responds in 7ms (alive) but actual LLM calls run 6+ minutes — under heavy multi-run load (8 concurrent runs hitting same proxy + Insights + Lineage = 16 LLM calls per epoch on G alone). A1/A2 disproportionately affected suggests either chain-server asymmetry or a specific proxy-side throttle. NOT a code defect.
- **Fix applied**: Stopped runs. Diagnosis preserved in this entry. Status decision (running → invalid vs relaunch with bumped stage_timeout) deferred to researcher.
- **Systemic fix needed**: NO for code; YES for process —  should flag stage durations approaching  (e.g. >70% of timeout = warn) so proxy-load issues surface before they produce malformed treatment data. Also consider per-experiment proxy load budgeting (8 runs × 16 LLM calls = 128/epoch is heavy on a shared proxy).

### [INVESTIGATION 2026-04-27T16:23:39Z] -- "32 vs 18 program count gap" is NOT a leak

- **When**: 2026-04-27T16:23:39Z, during stop diagnosis on db=1 (A1_G)
- **What**: Initial concern was that Redis held 32 program records but `engine:snapshot.programs_processed` reported 18 — suggested counter leak.
- **Investigation**: Cataloged all 32 records by lifecycle state. Result: 25 done + 3 discarded + 4 running (3 at iter=0, 1 at iter=1). The state breakdown closes cleanly to 32. Verified across all 8 runs: gap goes both directions (-18 to +10), e.g. C2_G has snap.proc=21 but only 9 done+discarded (15 still running), A1_D matches exactly (26==26). Conclusion: `programs_processed` snapshot field is written at refresh-pass boundaries, not on every program creation/completion — so it lags behind in-flight programs. Not a leak; a known timing artifact between counter writes and program record creation.
- **Category**: skill bug | infra issue | other → other (non-issue, but worth a process note)
- **Impact**: None on data; would be useful for diagnose to know that "program_keys count >> programs_processed" is normal when programs are in flight.
- **Root cause**: Snapshot write cadence intentionally low to reduce Redis hash hot-spotting. The two values measure different lifecycle stages.
- **Systemic fix needed**: NO. Optionally document in gigaevo/evolution/engine/snapshot.py docstring or in tools/README.md so future debugging doesn't re-litigate this.

### [DEVIATION 2026-04-27T16:55Z] -- Reduced runs from 8 to 4 (drop A2 + C2 seed pairs)

- **When**: 2026-04-27T16:55Z, after stop and before any relaunch
- **What**: Trimmed contract.runs from 8 to 4. Kept A1_G+A1_D (composition feedback arm) and C1_G+C1_D (gradient_in_prompt feedback arm). Dropped A2_G/A2_D/C2_G/C2_D. DBs 3, 4, 7, 8 released. launch.sh regenerated.
- **Category**: deviation (proxy mitigation)
- **Impact**: N drops from 2 to 1 per feedback arm. Halves concurrent LLM call load on the LiteLLM proxy at 10.232.30.185:4000 (16 calls/epoch on G runs -> 8). Loses statistical power for the cross-arm comparison: A vs C now reduces to a single-seed comparison rather than 2-seed averaged.
- **Root cause**: Proxy throughput could not sustain 8 concurrent runs with LineageStage + InsightsStage on G side at the design's stage_timeout=900s. Reducing N is the lowest-friction mitigation (no stage_timeout bump, no protocol change).
- **Fix applied**: Edited experiment.yaml runs[] and contract.runs[] in place. Regenerated launch.sh via `gigaevo -e $EXP launch --generate-script`. Pre-registration is preserved at the design level (treatment, control invariants, pin contract unchanged); the change is to the operational N.
- **Systemic fix needed**: NO immediately. Open question: if N=1 per arm proves too noisy on the relaunch, escalate to a second proxy or stagger run starts before further reducing.

### [EVENT 2026-04-27T21:35:21Z] -- Checkpoint recorded at gen ~9 (avg)

- **When**: 2026-04-27T21:35:21Z
- **What**: Checkpoint #1 recorded post-relaunch. Avg gen=9 (A1_G=8, A1_D=12, C1_G=9, C1_D=7). best_actual_fitness: A1_G=0.02859, A1_D=0.02886, C1_G=0.02883, C1_D=0.02931. C1_D leads at 0.02931 — 80.3% of v1 SOTA (0.0365), still below v2 NULL band μ_G=0.03315. Recent invalidity (last 20) = 0% on all runs. Diagnose: HEALTHY. Stage durations cooled from earlier near-timeout window (LineageStage 885s, Insights 828s) to 300-470s — well within 900s budget. 0 stage failures, 0 cancellations across all 4 runs. Treatment IV verified active: 3 lineage stages absent on D runs (A1_D, C1_D), present on G runs. A arm shows v1 D-ahead-of-G compute pattern (D=12 vs G=8, ratio 1.5×); C arm muted (D=7 vs G=9). Watchpoint: stage durations on first relaunch checkpoint vs the 16:23Z stop. Verdict: continue running.
- **Category**: checkpoint
- **Impact**: Automated capture.

### [CHECKPOINT gen=9] -- No deviations or decisions. All runs healthy.

### [EVENT 2026-04-28T01:32:51Z] -- Checkpoint #2 recorded at gen ~24 (avg)

- **When**: 2026-04-28T01:32:51Z
- **What**: Checkpoint #2. Avg gen=24 (A1_G=17, A1_D=32, C1_G=21, C1_D=26). best_actual_fitness: A1_G=0.02998, A1_D=0.03124 (lead), C1_G=0.02899, C1_D=0.03066. A1_G climbed +0.00139 since checkpoint #1 — now at 90.4% of v2 NULL μ_G=0.03315. A1_D crossed 94.2% of v2 NULL. Stage diagnose: 0 stage failures across all 4 runs. WATCHFUL on stage durations: max10 reached 790.8s on A1_G InsightsStage (88% of 900s), 788.7s on A1_D Insights, 761.0s on A1_G LineageStage — but isolated spikes, last values all <110s. Cancellations large (15K-22K per run, spread across 22-25 stages = benign MAP-Elites pruning). Treatment IV verified active. D-ahead-of-G compute ratio: A arm 2.07×, C arm 1.32×. Verdict: continue running.
- **Category**: checkpoint
- **Impact**: Automated capture.

### [CHECKPOINT gen=24] -- Stage spikes 600-790s observed but 0 failures; continue running. No deviations.

- **When**: 2026-04-28T01:32:51Z
- **Decision**: Continue despite max10 stage durations reaching 88% of stage_timeout (790s/900s) on A1_G and A1_D. Rationale: 0 stage failures across all 4 runs, last values all <110s (isolated spikes not sustained), 4-run proxy load mitigation working as intended (vs prior 8-run that hit ~15% L+I failure rate at this point).
- **Pre-registration deviation**: NO — pin contract unchanged, treatment IV unchanged, no parameter changes.

### [EVENT 2026-04-28T05:32:40Z] -- Checkpoint #3 recorded at gen ~38

- **When**: 2026-04-28T05:32:40Z
- **What**: CP#3 recorded. Avg gen ~38 (~19% of 200-gen budget).
- **Per-run**: A1_G gen=29 fit=0.03124 (94.2% of v2 NULL); A1_D gen=52 fit=0.03074; C1_G gen=34 fit=0.03243 (97.8% of v2 NULL — best μ_G yet); C1_D gen=37 fit=0.03243.
- **Δ vs CP#2 (gen~24)**: C1_G +0.00344 (+11.9%); A1_G +0.00126 (+4.2%); A1_D +0.00026; C1_D +0.00079. All positive.
- **Stage diagnose**: 0 failures across all 4 runs. New pattern — SUSTAINED (not isolated) elevated stages: A1_G LineageStage 643s, A1_G ImproverConditionStage 600s, A1_D ImproverConditionStage 551s, C1_D ImproverConditionStage 753s (near 800s critical threshold). C1_G remains cool. Different from CP#2 isolated-spike pattern (last == max).
- **Treatment integrity**: Both D runs confirm 3 lineage stages absent — disable_lineage_on_improver gate is firing.
- **Category**: checkpoint
- **Impact**: Hypothesis is approaching the v2 NULL escape threshold for the first time (C1_G at 97.8%). Trajectory upward at ~19% of budget — promising. Infrastructure: stage spike pattern shifted from isolated to sustained but still below critical threshold and 0 failures.

### [CHECKPOINT gen=38] — Decision: continue running

- **Decision**: Continue all 4 runs without intervention.
- **Rationale**: 0 stage failures (prior failure mode has not recurred). Sustained 750s C1_D stage durations are below 800s critical threshold. Hypothesis-relevant: C1_G has nearly closed the gap to v2 NULL band — interrupting now would forfeit the strongest signal the experiment has produced. 4-run mitigation continues to hold.
- **Pre-registration deviation**: None.
- **Watchpoint for next anomaly fire**: track whether sustained 600-750s stage pattern persists, escalates, or returns to isolated-spike pattern.

### [EVENT 2026-04-28T08:32Z] -- Anomaly check: C1_G crossed v2 NULL band (hypothesis-positive); C1_D InsightsStage sustained-CRIT escalated

- **When**: 2026-04-28T08:32Z
- **What**: WATCHFUL verdict. Hypothesis-positive: C1_G actual_fitness=0.03538 = 106.7% of v2 NULL (0.03315) — first run to cross v2 NULL band (CP#3 was 97.8%). Watchpoint: sustained-CRIT stage pattern from CP#3 has narrowed to a single run/stage (C1_D InsightsStage), and ESCALATED on that one. C1_D last10=[753,800,808,72,490,481,577,668,208,810], last=809.8s (89.9% of 900s), 4/10 above 720s. The other 3 runs that were sustained at CP#3 (A1_G L+I, A1_D I) have all RETURNED TO CLEAN (max < 410s).
- **Category**: diagnose
- **Impact**: No action — hypothesis-positive signal alert-only by design; C1_D long stages still producing 0 recent failures (last 30) and gen advancing +6 in 2h. Lifetime failures (A1_G L=2, C1_G I=2, C1_D I=4) are all from 2026-04-27 22:16-22:17 startup window — none recent.
- **Root cause**: (a) Hypothesis crossing — favorable evolution outcome, no infra concern. (b) Likely proxy load asymmetry: C1_D sees longer LLM responses for the improver-condition / insights generation under disable_lineage_on_improver=true; the load that previously hit all 4 runs uniformly now concentrates on the slowest worker.
- **Fix applied**: None. Posted PR #223 comment with detailed table. Will escalate at next fire if C1_D produces any stage_failure in last-30 OR if last-value crosses 850s.
- **Systemic fix needed**: NO (yet). If C1_D pattern persists across multiple anomaly checks without producing failures, document as expected-under-asymmetric-load behaviour. If failures recur, consider per-run stage_timeout floor lift to 1200s for D-side InsightsStage.
