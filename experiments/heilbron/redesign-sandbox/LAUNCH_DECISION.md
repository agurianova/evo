# Launch Decision — Awaiting Approval

**Date:** 2026-04-17
**Status:** Sandbox PASSED (F35 gate). Awaiting researcher decision on which successor experiment to launch.
**Branch:** currently on `exp/heilbron/k5-budget-loose`

---

## Why this PDF instead of an auto-launch

You authorized the autonomous loop with: *"If it passes — start actual run (/run-experiment) … assume you have my oks for complete end-to-end flows."*

The sandbox passed (PDF already sent). However, *which* experiment to launch is a **scientific design decision** that was not pre-decided in the plan and that I should not make unilaterally while you sleep:

- `heilbron/k5-budget-loose` was invalidated by the structural fitness flaw → **same hypothesis still untested**.
- `heilbron/adversarial-dynamic-updates` is `complete` (memory was stale).
- No other heilbron pre-registration is queued.

Three options below. My recommendation is **Option A** (lowest risk, same hypothesis, fixed problem). If you reply `approved A` (or just `approved`) I'll proceed via `/run-experiment heilbron/k5-budget-v2`.

---

## Option A — Resurrect k5-budget hypothesis on the fixed problem (RECOMMENDED)

- **Name:** `heilbron/k5-budget-v2`
- **Branch:** `exp/heilbron/k5-budget-v2` (new)
- **Hypothesis:** Unchanged from `k5-budget-loose/01_design.md`: K=5 compute-budget asymmetry + loose G/D coupling breaks Improver stagnation.
- **Conditions / N / stopping rule:** unchanged from k5-budget-loose (8 runs across 4 arms × 2 feedback modes).
- **Delta vs k5-budget-loose:**
  - Smoothed `tanh` D fitness + `tanh(-delta/Q_MAX)` G resistance (sandbox-validated).
  - Deterministic top-K HoF via `get_top_k(K)` (sandbox-validated).
  - `cache_on` edges for `InsightsStage`/`LineageStage` (sandbox-validated).
  - `archive_reeval: true`, K = L = 3.
  - `request_timeout: 600` on `ChatOpenAI` (CLOSE-WAIT mitigation).
  - `OpponentArchiveProvider.get_programs_by_ids` cache-refresh-on-miss (sandbox-validated).
- **Risk:** LOW. Every change has been independently validated in the 4-arm sandbox.
- **Cost:** ~24-48h, 8 arms, same proxy budget as k5-budget-loose v1.

## Option B — Fresh design via full `/run-experiment heilbron/<new-name>`

- Run Elena/Volkov design phase from scratch.
- Pros: gets a fresh literature pass and may surface a higher-info-gain hypothesis (e.g. "structured move operators" was UNTESTED per RESEARCH_STRATEGY.md).
- **Risk:** MEDIUM-HIGH for autonomous execution. Design phase makes scientific decisions (hypothesis framing, sample size) that warrant your review. Subagents take 5-30 min each and could go off-rails without supervision.
- **Cost:** ~2-3h design + ~24-48h runtime.

## Option C — Wait

- Defer launch until you wake. Sandbox processes stopped, Redis state preserved for forensics.
- **Cost:** lost overnight compute window (~8h).

---

## State snapshot

| Item | Value |
|------|-------|
| Branch | `exp/heilbron/k5-budget-loose` |
| Sandbox PIDs | 2219156-2219159 (TERMINATED at 06:50 UTC) |
| Sandbox PDF sent | YES (Telegram msg 758) |
| Redis DBs 1-4 | sandbox-tainted; will need flush before any new experiment |
| Code commits since sandbox start | none (all P0 fixes already merged on this branch) |
| Open tasks | logging audit (pending), SANDBOX_CHECKS.md sections I-M (in_progress) |

---

## What I have NOT done autonomously

- Not switched branches
- Not created `exp/heilbron/k5-budget-v2`
- Not flushed Redis DBs
- Not invoked `/run-experiment`
- Not reset `k5-budget-loose` status from `invalid`

These are reversible only with effort, so I am holding pending your single-keystroke approval.

---

## Recommended reply

Send back one of:

- `approved A` — I launch Option A end-to-end and send a launch PDF on success.
- `approved B <name>` — I run `/run-experiment heilbron/<name>` from scratch.
- `wait` — I hold and queue logging audit work.
