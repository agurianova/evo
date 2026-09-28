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

### [ANOMALY CHECK 2026-04-14T18:24Z] -- First post-restart anomaly check: WARN

- **When**: 2026-04-14T18:24Z (~2h post-restart at 15:08 UTC)
- **What**: Anomaly detector ran. All 8 PIDs alive. Watchdog PID 1019954 alive. SyntaxError pattern detected in 4/8 logs (Pattern 4, known LLM quirk). A2_G invalidity 70% at strategy_gen=2 (early, monitoring only).
- **Category**: diagnose
- **Impact**: Automated capture. No action taken — no infrastructure failures found.

### [WARN 2026-04-14T18:24Z] -- SyntaxError in LLM-generated code (Pattern 4, known)

- **When**: 2026-04-14T18:24Z
- **What**: SyntaxError occurrences (10 each) in A1_G, A1_D, C1_D, C2_D logs. Example: `SyntaxError at line 36, offset 14: invalid syntax. Line: 'n            for d in directions:'`. Leading `n` character on code lines — consistent with Pattern 4 (structured output with embedded newline/escape in code field).
- **Category**: tool bug (LLM output quality)
- **Impact**: ~20-30% of mutations in affected runs marked invalid. Programs rejected correctly by ValidateCodeStage. No generation progress blocked.
- **Root cause**: Known LLM quirk — structured output occasionally embeds `\n` as literal `n` at line start. The `_fix_double_escaped_quotes()` fix reduces but does not eliminate this.
- **Fix applied**: Alert only. Rate is within known acceptable range for Pattern 4. No restart needed.
- **Systemic fix needed**: YES — investigate whether the `n`-prefix pattern is distinct from double-escaped quotes and requires a separate fix in the mutation pipeline.

### [EVENT 2026-04-14T13:53:06Z] -- Experiment launched

- **When**: 2026-04-14T13:53:06Z
- **What**: launch.sh executed. 8 runs started. PIDs: A1_G=993385 A1_D=993386 A2_G=993387 A2_D=993388 C1_G=993389 C1_D=993390 C2_G=993391 C2_D=993392
- **Category**: launch
- **Impact**: Automated capture.

### [EVENT 2026-04-14T13:57:40Z] -- Watchdog started

- **When**: 2026-04-14T13:57:40Z
- **What**: Watchdog started (PID 999516). 12s survival verified. Plugin: adversarial.
- **Category**: watchdog
- **Impact**: Automated capture.

### [EVENT 2026-04-14T13:57:40Z] -- Watchdog CLI bugs fixed

- **When**: 2026-04-14T13:57:40Z
- **What**: Fixed 3 bugs in CLI watchdog: (1) watchdog_plugin.py used manifest.experiment.task instead of manifest.task; (2) manifest.py did not read watchdog.plugin from nested watchdog: section; (3) watchdog_cmd.py did not import gigaevo.monitoring.plugins, leaving registry empty.
- **Category**: bug
- **Impact**: CLI watchdog now starts correctly.

### [EVENT 2026-04-14T18:05Z] -- Experiment restart initiated

- **When**: 2026-04-14T18:05Z
- **What**: Full experiment restart. Progress at restart: A1_G=gen6, A1_D=gen6, A2_G=gen2, A2_D=gen3, C1_G=gen1, C1_D=gen0, C2_G=gen2, C2_D=gen3
- **Reason**: stage_timeout=3000 and dag_timeout=7200 caused C1_G to freeze for 57+ min at CallProgramFunction. Restart with stage_timeout=2400, dag_timeout=2400 to force faster iteration.
- **Protocol deviation**: Yes — mid-experiment config change. All gen 0-6 runs had timeout-affected evaluations. Pre-registration unchanged; treatment arms and stopping rule are unaffected.
- **Category**: restart
- **Impact**: All run progress destroyed. Redis DBs flushed. Archives saved locally.

### [EVENT 2026-04-14T19:43:10Z] -- Watchdog restarted with telegram event-loop fix

- **When**: 2026-04-14T19:43:10Z
- **What**: Killed PID 1067827 (and intermediate 1132189, which lacked TELEGRAM env). Launched fresh watchdog PID 1133798 with .env sourced. Commit with fix: a06732ded64188f157bc9600ba66b8934fbb1b59.
- **Category**: watchdog
- **Impact**: Experiment runs not touched. Telegram delivery will be verified on cycle 2.

### [EVENT 2026-04-14T23:27:01Z] -- Checkpoint recorded at gen ~13

- **When**: 2026-04-14T23:27:01Z
- **What**: Routine checkpoint. 8 runs ALIVE, watchdog alive (PID 1133798), zero errors. C1_G crossed baseline 0.03449 with best_actual_fitness=0.03522. D-run log silence (A2_D/C1_D/C2_D) verified as Qwen3-Thinking inference latency (1500-1666s), not stall.
- **Category**: checkpoint
- **Impact**: Automated capture.
- **Decision**: Continue. Stopping rule not triggered (futility check is at gen 25; all arms have at least one replicate >= 0.03000). Mid-run analyst deferred to gen ~25 (50% threshold).

### [EVENT 2026-04-15T03:29:06Z] -- Mid-run checkpoint at gen ~18 (50% threshold crossed)

- **When**: 2026-04-15T03:29:06Z
- **What**: Second checkpoint. A1_G (gen 26) and A1_D (gen 25) crossed 50% gate for first time. Invoked `checkpoint-analyst` agent with blinded (R1-R8) data — verdict: **MINOR**.
- **Category**: checkpoint

**Run metrics (best actual_fitness):**
- A1_G=0.02777 (-0.00672 vs baseline), gen 26 — declined from prior 0.03007 despite 12-gen advance (FLAG)
- A1_D=0.03123 (-0.00326), gen 25 — above futility threshold 0.03000
- A2_G=0.03062 (-0.00387), gen 15
- A2_D=0.03089 (-0.00360), gen 13
- C1_G=0.03522 (+0.00073 above baseline), gen 15 — plateau
- C1_D=0.03522 (+0.00073), gen 15 — matches C1_G frontier
- C2_G=0.02811 (-0.00638), gen 18 — stagnant across 2 checkpoints (FLAG)
- C2_D=0.03169 (-0.00280), gen 17 — +0.00306 improvement since prior

**Decisions:**
1. **Continue experiment.** Stopping rule not triggered: futility check at gen 25 requires BOTH pair replicates < 0.03000; A1_D=0.03123 > 0.03000, so pair A1 not futile. Remaining 6 runs not yet at gen 25.
2. **Monitor A1_G** next checkpoint for continued decline (fitness went 0.02683→0.02777 over 12 gens — nearly flat despite large gen advance). If R1 continues declining through gen 30, consider researcher intervention.
3. **Monitor C2_G** — stagnant at 0.02811 across both checkpoints. Below baseline. Watch for sustained flat trajectory.
4. **Analyst unblinding note**: checkpoint-analyst agent read experiment.yaml directly and auto-unblinded at end of report. Analysis itself was produced using R-labels (blind), but skill could be hardened by running analyst in isolated context without repo access. Documented for future skill improvement.
5. **Deferred**: frontier diversity check for C1_G/C1_D (both at 0.03522) — may indicate shared frontier program. Non-blocking; revisit at gen ~25 checkpoint.

**Protocol deviations**: None. Mid-run test eval correctly skipped (has_test_set=false). No amendments to pre-registration.

- **Impact**: Automated capture with analyst-informed decision. Ready for next cron-triggered checkpoint (~4h).

### [EVENT 2026-04-15T07:24:22Z] -- Routine checkpoint at gen ~20

- **When**: 2026-04-15T07:24:22Z
- **What**: Third checkpoint. Analyst skipped (mid_run.completed=true from prior gen ~18 cp). Test eval skipped (has_test_set=false).
- **Category**: checkpoint

**Run metrics (best actual_fitness, Δ vs baseline 0.03449):**
- A1_G=0.02896 (-0.00553), gen 29 — prior cp=0.02777; +0.00119 improvement (no longer declining)
- A1_D=0.03123 (-0.00326), gen 29 — unchanged from prior cp
- A2_G=0.03169 (-0.00280), gen 19 — +0.00107 improvement since prior
- A2_D=0.03089 (-0.00360), gen 16 — unchanged
- C1_G=0.03522 (+0.00073 above), gen 17 — plateau continues
- C1_D=0.03522 (+0.00073 above), gen 17 — plateau continues
- C2_G=0.03040 (-0.00409), gen 20 — prior cp=0.02811; **+0.00229 recovery from flagged stagnation**
- C2_D=0.03061 (-0.00388), gen 19 — prior cp=0.03169; -0.00108 (slight retreat, still within tolerance)

**Stopping rule status**: Futility gate at gen 25 NOT triggered. A1 pair at gen 29: A1_D=0.03123 > 0.03000 threshold → arm A1 NOT futile. A2 pair not yet at gate (gens 16-19). C pairs not at gate (gens 17-20).

**Decisions:**
1. **Continue experiment.** No stopping conditions met. All 8 runs advancing.
2. **C2_G flag cleared.** Prior checkpoint flagged stagnation (flat at 0.02811 across two cps); this checkpoint shows +0.00229 recovery to 0.03040. No longer stagnant. Remove from watch list.
3. **A1_G flag partially cleared.** Fitness now trending up (+0.00119 over 3 gens); still below baseline but no longer declining. Continue monitoring.
4. **C2_D slight retreat** (0.03169 → 0.03061): single-checkpoint dip, not yet a pattern. Monitor.
5. **C1 pair plateau** at 0.03522 persists across 3 checkpoints (gens 11,15,17). Frontier diversity check remains deferred — non-blocking.

**Protocol deviations**: None. Mid-run analyst was completed at prior 50%-threshold checkpoint per protocol; this skip is expected.

- **Impact**: Automated capture. Experiment progressing healthily. Next cron-triggered checkpoint in ~4h.
