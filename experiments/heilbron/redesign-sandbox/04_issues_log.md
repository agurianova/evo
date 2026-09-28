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

### [EVENT 2026-04-17T04:40:00Z] -- Sandbox A_G CLOSE-WAIT recurrence — fix validation & systemic remediation

- **When**: 2026-04-17 ~04:40 UTC (gen 1/8, ~35 min into 2nd run)
- **What**: A_G (PID 2219156) recurrence of CLOSE-WAIT to litellm proxy (fd=78). B_G (PID 2219158) also has a CLOSE-WAIT (fd=29). Both arms have last log activity ~13 min before detection; main thread in ep_poll, all 156 worker threads in futex_wait_queue_me.
- **Category**: infra (recurring)
- **Impact**: Before stall, `opponent_provider.get_programs_by_ids` fix validated:
  - A_G gen=1, archive=7, **dg_injected=6** (composition injections ARE firing)
  - B_G gen=1, archive=14, dg_improvements=20 (gradient arm firing)
  - All 4 arms: dg_improvements > 0 (DGTracker works)
  - A_D mean fitness ≈ 0.49, B_D similar (smoothed tanh produces non-trivial range)
- **Root cause**: Same as prior incident — httpx/openai SDK does not detect peer-closed TCP socket; no inactivity timeout configured. Default `request_timeout=None` on `ChatOpenAI`.
- **Fix applied**:
  - `config/llm/single.yaml`: added `request_timeout: 600` and `max_retries: 2`.
  - Running sandbox arms will NOT see this config (Hydra already loaded) — they will either unblock when stage_timeout (1800s) fires, or remain stuck with dg counters captured in Redis as-is (sufficient for redesign validation).
  - Future experiments launched after this commit will cap LLM stalls at 600s.
- **Systemic fix needed**: YES — done via single.yaml timeout. A follow-up could use `httpx.AsyncClient(http2=True, timeout=httpx.Timeout(connect=10, read=600, write=60, pool=60))` for finer control; not essential given the 600s ceiling above.

### [EVENT 2026-04-17T01:05:00Z] -- Sandbox A_G stalled on CLOSE_WAIT to litellm proxy

- **When**: 2026-04-17 ~01:05 UTC (gen 2/8, ~95 min into run)
- **What**: A_G (PID 2158977) DAG hung after `DGTrackerStage` started at 03:13:41 MSK. Process alive in epoll_wait, RSS 856MB, 172 threads. Single CLOSE_WAIT TCP connection to 10.232.30.185:4000 (litellm proxy) — peer closed but httpx didn't.
- **Category**: infra (transient proxy/network glitch)
- **Impact**: A_G stalled while A_D / B_G / B_D progressed normally. Killed all 4 to restart cleanly.
- **Root cause**: openai/httpx client did not detect peer-closed socket; no inactivity timeout fires within DAG stage_timeout (1800s).
- **Fix applied**: kill -TERM all 4 PIDs; relaunch sandbox.
- **Systemic fix needed**: consider adding `httpx` keepalive ping or shorter idle-recv timeout on LLM client; outside scope of sandbox.
