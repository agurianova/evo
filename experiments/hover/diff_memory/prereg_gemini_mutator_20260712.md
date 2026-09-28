# Prereg: mutator-model lever — gemini-3.5-flash under the ALL-IN recipe

Status: APPROVED 2026-07-12 — user directive "run the top-1 recommended arm
using gemini 3.5 flash" (terminal, = launch approval). SINGLE MEM run — the
recommended arm from the closeout defaults — not the 1 MEM + 1 NOMEM pair of
the original draft. Part I bar re-eval stays pending (artifacts not located;
published numbers are the fallback bar, see below).
Launcher: `launch_gemini_mem.sh`; watchdog: `watchdog_gemini.sh`.

## Research question

The ALL-IN machinery (BD3D archive + paired-bootstrap gate + paired
crediting) was validated under the Qwen3-235B-Thinking mutator and beat all
prior Qwen-mutator finals on TEST (62.7 vs 56.7–59.0) — but the old
gemini-3.5-flash campaign (Part I, no memory, 1D fitness archive) reached
67.3/68.0 TEST hard. Does the ALL-IN machinery COMPOSE with the stronger
mutator, or was Part I's result mutator-dominated?

## Treatment (exactly one lever)

Mutator swap: `llm=gemini35_flash` (google/gemini-3.5-flash via OpenRouter,
flex tier, reasoning.effort=high — existing preset `config/llm/gemini35_flash.yaml`)
replacing the internal Qwen3-235B-Thinking route. EVERYTHING else identical
to the MEM arm of `launch_bd3d_noise_allin.sh`: single MEM run,
`chains/hover/full7_vectorized`, `chains_bd3d`, `paired_bootstrap`,
`memory_guided_noise` + `memory/crediting=paired`, num_parents=1, 250
mutants, same chain executor (Qwen3-8B backends — UNCHANGED, so fitness
evaluation is comparable across campaigns). `memory/llm=qwen_instruct` also
unchanged (memory authoring is not the lever). No NOMEM twin this launch
(user directive); the no-memory contrast is cross-campaign only.

## Causal chain (signal → behaviour → metric)

1. **Signal**: gemini-3.5-flash produces higher-quality CARL diffs — Part I
   arm B (same mutation=carl_with_retrieval_tools schema) hit 68.0 vs Part II
   Qwen's 56.7 on identical no-memory 1D-archive setups. The mutator is the
   only differing component in that comparison.
2. **Behaviour**: better diffs → higher paired-gate accept rate and/or larger
   per-accept fitness deltas; BD3D occupancy fills faster and deeper (Qwen
   pairs: 27–41 cells, accept 19–37%). In the MEM arm, better children also
   sharpen paired crediting (bigger |gain| at same se).
3. **Metric**: pooled-MMR winner's K=5 val re-eval and TEST hard exceed the
   Part I winner re-evaluated under the same protocol.

**Riskiest link**: 2→3. The paired gate could interact badly with a mutator
whose edits are larger per step (fewer, bolder diffs may be rejected against
strong incumbents → archive stalls despite better raw material). This is
observable mid-run: accept rate + best-so-far trajectory at T+1h/T+3h.
Secondary risk: OpenRouter flex-tier latency inflates wall-clock (mitigate:
stage_timeout=7200 already generous; watchdog hard gate only checks
treatment liveness, not speed).

## Target bar (prerequisite before launch)

Locate the Part I winner chain specs (arm A 67.3, arm B 68.0 — artifacts NOT
in this checkout's outputs/; likely the older campaign archive — ASK USER for
the path) and re-evaluate the better one under our protocol: K=5 val
(vectorized, per-claim vectors → enables paired tests) + K=5 TEST hard.
That re-evaluated number is the bar; the published 67.3/68.0 (single-shot
protocol) is the fallback bar if artifacts are unrecoverable (with the
winner's-curse caveat noted — Part I numbers are NOT curse-corrected; our
re-evals showed curses of −.010 to −.024).

## Preregistered endpoints

- **G1 (primary)**: MMR winner of this run, K=5 TEST hard, vs the Part I
  bar. If Part I artifacts surface: paired per-claim test vs the re-evaluated
  Part I winner, WIN = mean above AND p<.05. Fallback (published bar): WIN =
  K=5 TEST hard mean − 1 SE above 68.0 (single-shot, not curse-corrected —
  so demand the margin). Same asymmetry as A1: WIN ⇒ machinery composes;
  NO-WIN ⇏ machinery useless (mutator may dominate).
- **G2 (cross-campaign, replaces the in-pair MEM/NOMEM contrast)**: this
  run's winner vs the Qwen ALL-IN pair's winners (MEM 62.7±1.9 / NOMEM
  55.4 TEST hard, K=5) — quantifies the mutator lever under identical
  machinery. Confounds acknowledged: no same-mutator NOMEM twin this launch.
- **T1–T6**: same treatment sweeps via `check_allin_progress.py`, same 1h
  hard gate + watchdog (`watchdog_gemini.sh`). T7 (NOMEM purity) is
  inapplicable — no NOMEM arm. T6 injection band stays 30–55% (known to run
  hot; WATCH not abort).
- **Cost/ops guard**: OpenRouter spend logged per run; abort if projected
  run cost exceeds ~3× the Part I per-run spend.

## Prediction table

| Outcome (MMR winner, K=5 TEST hard) | Reading |
|---|---|
| > bar (≈68) significantly | Machinery composes; ALL-IN + strong mutator is the new recipe |
| ≈ bar (66–68, ns) | Mutator-dominated; machinery neutral at this ceiling — pivot to problem-side levers |
| 63–66 | Partial: above Qwen-ALL-IN, below Part I — gate/mutator interaction is costing headroom; inspect accept rates |
| < 63 (below Qwen-ALL-IN best) | Negative interaction (riskiest link fired); autopsy gate decisions on rejected high-delta diffs |

Prediction (stated before launch): composes — MEM arm lands 68–71.

## Ops notes

- OpenRouter needs `OPENROUTER_API_KEY` + Squid proxy (`HTTPS_PROXY`) while
  the chain executor needs `NO_PROXY` for the internal backends — the
  launcher must set BOTH, per-route (mutator via proxy, executor direct).
  This is the exact trap that hung the A1 re-eval; verify with a 1-call
  smoke per route before launch.
- Same watchdog/night-queue/waiter automation as ALL-IN; new TS namespace
  `hover-diff-memory-gemini-*`.
