---
name: run-experiment
description: Full lifecycle orchestrator for GigaEvo experiments. Runs design → implement → launch → background automation → closeout, pausing only at three researcher approval gates. Triggers on "run experiment", "start experiment", "continue experiment", "what phase is X at".
argument-hint: <task/name> [research-question]
model: opus
---

# Run Experiment: $ARGUMENTS

Full lifecycle orchestrator. Runs every phase in sequence, pausing only at the three mandatory approval gates below. Everything else is automated.

## The Three Approval Gates

| Gate | When | What to review |
|------|------|----------------|
| **Gate 1 — Design** | After Elena + Volkov complete | `01_design.md`: hypothesis, N, stopping rule, treatment |
| **Gate 2 — Launch** | After config dumps captured | `cfg_run_*.txt`: every override correct, no copy-paste errors |
| **Gate 3 — Results** | After closeout generates results | `05_results.md`: CIs, verdict, deviations section |

Do NOT proceed past a gate without explicit researcher approval ("approved" or equivalent).

---

## Step 0 — Validate arguments

If `$ARGUMENTS` is empty or whitespace-only, ask:

> "Which experiment should I run? Provide `<task>/<name>` (e.g. `hover/dynamic-topology`) and optionally a research question."

Do not proceed until a non-empty experiment path is provided.

---

## Step 1 — Determine current status

```bash
EXP=$(echo '$ARGUMENTS' | awk '{print $1}')
STATUS=$(gigaevo -e "$EXP" manifest get status 2>/dev/null || echo "new")
echo "STATUS=$STATUS"
if [ "$STATUS" != "new" ]; then
  gigaevo -e "$EXP" manifest get name 2>/dev/null
  gigaevo -e "$EXP" manifest get branch 2>/dev/null
  gigaevo -e "$EXP" manifest get max_generations 2>/dev/null
fi
```

Route by status:

| Status | Action |
|--------|--------|
| `new` | Proceed to **Phase A — Design** below |
| `preregistered` | Skip to **Phase B — Implement** |
| `implemented` | Skip to **Phase C — Launch** |
| `running` | Skip to **Phase D — Running** |
| `complete` | Skip to **Phase E — Closeout** |
| `invalid` | Print: "Experiment invalid. Reset with `gigaevo -e <exp> manifest reset-status preregistered --reason '...'`" and stop |

If the user said "restart", dispatch `/experiment-restart $ARGUMENTS` regardless of status.

---

## Phase A — Design

*Skip if status is not `new`.*

### A1 — Run experiment-design skill

```
/experiment-design $ARGUMENTS
```

This creates the experiment directory, runs Elena (design) + Volkov (adversarial review), writes `01_design.md`, fills `experiment.yaml`, and creates the PR.

### A2 — Gate 1: Design approval (Telegram async)

Extract summary from `experiments/$EXP/01_design.md`:
- Hypothesis (one sentence)
- Conditions and N per arm
- Primary metric and stopping rule
- Feasibility rating from codebase_map.md (GREEN/YELLOW/RED)

Fire Gate 1 via Telegram (async, LangGraph checkpoint pattern):

```bash
EXP='$ARGUMENTS'
# Save gate state to manifest so session can resume after Telegram approval
gigaevo -e "$EXP" manifest update gates.gate1_pending true
gigaevo -e "$EXP" manifest update gates.gate1_sent_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Gate 1 state saved"

# Send Telegram notification
$GIGAEVO_PYTHON -c "
from tools.telegram_notify import gate_design_approval
result = gate_design_approval('$EXP')
if result.timed_out:
    print('GATE_TIMEOUT')
elif result.approved:
    print('GATE_APPROVED')
else:
    print(f'GATE_FEEDBACK:{result.text}')
"
```

- **GATE_APPROVED**: proceed to Phase B
- **GATE_TIMEOUT** (after 48h): warn in 04_issues_log.md, block — do not auto-proceed
- **GATE_FEEDBACK**: iterate on design (re-run Elena/Volkov), re-fire Gate 1

**If Telegram is not configured** (TELEGRAM_BOT_TOKEN not set): fall back to interactive terminal prompt.

---

## Phase B — Implement

*Skip if status is `implemented`, `running`, or `complete`.*

### B1 — Run experiment-implement skill

```
/experiment-implement $ARGUMENTS
```

This writes code, configs, and the smoke test. It ends with `status=implemented` and a passing smoke test.

Implementation is **not a gate** — if the smoke test passes, proceed automatically to Phase C.

If the smoke test fails, fix the issue and re-run B1. Do not proceed to launch with a failing smoke test.

---

## Phase C — Launch

*Skip if status is `running` or `complete`.*

### C1 — Launch experiment

Launch via experiment-launch skill (runs checks, claims DBs, launches runs, starts watchdog):

```
/experiment-launch $ARGUMENTS
```

The launch skill will pause at **Step 6 (researcher confirms launch)**. That pause IS Gate 2 — handle it here.

### C2 — Gate 2: Launch confirmation (Telegram async)

Build a 1-paragraph cfg summary from the cfg_run_*.txt files (key overrides only — pipeline, problem, DB, treatment).

Fire Gate 2 via Telegram:

```bash
PROJ="$(git rev-parse --show-toplevel)"
EXP='$ARGUMENTS'
CFG_SUMMARY=$(head -20 "experiments/$EXP/cfg_run_R1.txt" 2>/dev/null || echo "cfg not found")

$GIGAEVO_PYTHON -c "
from tools.telegram_notify import gate_launch_confirmation
result = gate_launch_confirmation('$EXP', '''$CFG_SUMMARY''')
if result.timed_out:
    print('GATE_TIMEOUT')
elif result.approved:
    print('GATE_APPROVED')
else:
    print(f'GATE_FEEDBACK:{result.text}')
"
```

- **GATE_APPROVED**: signal launch to experiment-launch skill
- **GATE_TIMEOUT** (after 24h): block — do not auto-launch (GPU compute risk)
- **GATE_FEEDBACK**: fix configs, regenerate, re-fire Gate 2

### C3 — Confirm background automation active

After launch completes, verify crons are running:

```bash
EXP='$ARGUMENTS'
echo "anomaly_detector_cron_id: $(gigaevo -e "$EXP" manifest get control_plane.anomaly_detector_cron_id 2>/dev/null || echo 'MISSING')"
echo "checkpoint_cron_id:       $(gigaevo -e "$EXP" manifest get control_plane.checkpoint_cron_id 2>/dev/null || echo 'MISSING')"
echo "watchdog_pid:             $(gigaevo -e "$EXP" manifest get control_plane.watchdog_pid 2>/dev/null || echo 'MISSING')"
```

If any field is MISSING: create the missing cron(s) via CronCreate and record their IDs in experiment.yaml before continuing.

Then notify via Telegram AND inform the researcher in terminal:

```bash
$GIGAEVO_PYTHON -c "
from tools.telegram_notify import notify
notify('🚀 *$EXP* launched\n\nBackground automation active:\n• Watchdog: hourly Telegram fitness updates\n• Checkpoint every 4h (automated)\n• Anomaly detector every 2h\n\nYou will be pinged for Gate 3 when runs complete.')
"
```

> **Experiment `$EXP` is running.**
>
> Background automation active:
> - Watchdog: hourly Telegram + PR comments with fitness table + plot
> - Checkpoint cron: every 4 hours (automated, goal-drift check included)
> - Anomaly detector: every 2 hours (auto-fixes infrastructure, triggers closeout on completion)
>
> **No further action needed until you receive the Gate 3 Telegram notification.**

---

## Phase D — Running

*Reached when status is already `running` and no restart was requested.*

### D1 — Show current status

```bash
EXP='$ARGUMENTS'
gigaevo -e "$EXP" status
```

### D2 — Confirm background automation

Run the same cron check as C3. If any cron is missing, recreate it.

### D3 — Offer manual checkpoint

Ask:

> Experiment is running with background automation active. Want me to run a checkpoint now? Reply "yes" to checkpoint, or "no" to leave the crons running.

If "yes": dispatch `/experiment-checkpoint $EXP`.

---

## Phase E — Closeout

*Reached when status is `complete`, or dispatched by anomaly-detector when runs finish.*

### E1 — Run experiment-closeout skill

```
/experiment-closeout $ARGUMENTS
```

This archives all runs, runs test evaluation, and writes `05_results.md` with CIs and verdict.

### E2 — Gate 3: Results sign-off (Telegram async)

Extract from `experiments/$EXP/05_results.md`:
- Verdict (POSITIVE / NULL / NEGATIVE / SUGGESTIVE)
- Primary effect size with 95% CI
- Whether result clears the pre-registered MDE

Fire Gate 3 via Telegram:

```bash
PROJ="$(git rev-parse --show-toplevel)"
EXP='$ARGUMENTS'
VERDICT=$(grep "^Verdict:" "experiments/$EXP/05_results.md" | head -1 | cut -d: -f2 | xargs)
EFFECT=$(grep "^Primary effect:" "experiments/$EXP/05_results.md" | head -1 | cut -d: -f2 | xargs)

$GIGAEVO_PYTHON -c "
from tools.telegram_notify import gate_results_signoff
result = gate_results_signoff('$EXP', '$VERDICT', '$EFFECT')
if result.timed_out:
    print('GATE_TIMEOUT')
elif result.approved:
    print('GATE_APPROVED')
else:
    print(f'GATE_FEEDBACK:{result.text}')
"
```

- **GATE_APPROVED**: proceed to E3 (merge)
- **GATE_TIMEOUT** (after 72h): block — do not auto-merge
- **GATE_FEEDBACK**: iterate on results presentation, re-fire Gate 3

### E2b — Paper draft (automated, before merge)

After Gate 3 approval, auto-generate paper draft sections:

```
/experiment-paper-draft $TASK $EXP
```

This runs automatically. The draft is saved to `experiments/$TASK/paper_draft.md` before merge.

### E3 — Merge PR

On approval:

```bash
EXP='$ARGUMENTS'
PR_NUM=$(gigaevo -e "$EXP" manifest get contract.identity.pr_number)
gh pr merge "$PR_NUM" --merge --delete-branch
```

Then update `experiments/INDEX.md` with the experiment result (closeout skill handles this).

---

## Gotchas

- **Gate order is fixed** — never skip a gate, even if you think the answer is obvious. The researcher must explicitly approve.
- **Background automation is the default** — after Gate 2, the researcher can walk away. Crons handle everything until completion.
- **Restart does not need Gate 2 again** if the config hasn't changed (only code was fixed). Use `/experiment-restart` and re-enter Phase D.
- **If a cron is missing after launch** — always recreate it. A missing cron means silent experiment death.
- **Multiple calls are safe** — calling `/run-experiment` on a running experiment just shows status and confirms crons. It does not restart or double-launch anything.
