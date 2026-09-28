# ETA computation audit — 2026-08-04

**Question:** is the live `[eta]` estimate computed incorrectly?

**Answer:** yes. The single ETA implementation is `gigaevo/monitoring/eta_ticker.py`
(wired at `run.py:118`, the only consumer of `EvolutionStopper.estimate_remaining`).
Three defects, one severe. All stem from how throughput is derived, not from
the stopper's remaining-work arithmetic.

**Status: fixed** in the same PR — see [Resolution](#resolution). Everything below
describes the code *as it stood before* that fix; line references are pre-fix.

## The mechanism

`eta_ticker._tick` (`gigaevo/monitoring/eta_ticker.py:41-71`):

```python
ctx = engine.build_stop_context()
throughput = EngineThroughput(
    mutants_per_second=ctx.total_mutants / ctx.elapsed_seconds,   # line 50
    ...
)
est_remaining = engine.stopper.estimate_remaining(ctx, throughput)
```

and `MaxMutantsStopper.estimate_remaining` (`gigaevo/evolution/engine/stopper.py:63-69`)
divides the remaining mutant count by that rate.

The rate is a **cumulative lifetime average**: numerator and denominator must
cover the same interval for it to be meaningful. They don't.

`build_stop_context` (`gigaevo/evolution/engine/core.py:690-701`):

```python
elapsed = time.monotonic() - self._run_start_time
return StopContext(total_mutants=self.metrics.mutations_created, elapsed_seconds=elapsed, ...)
```

---

## Bug 1 — SEVERE: on resume the numerator carries history, the denominator does not

`run.py:97` calls `restore_state()`, which sets
`metrics.mutations_created = snapshot.total_mutants` (`core.py:677`) — the
**all-time** mutant count across every prior run.

`_run_start_time` is set fresh at `SteadyStateEngine.run()`
(`gigaevo/evolution/engine/steady_state.py:84`) and is written nowhere else
(only 4 references repo-wide). So `elapsed_seconds` covers **this process only**.

Rate = (all-time mutants) / (this-run seconds) → inflated by roughly the ratio
of restored work to new work.

**Worked example** — resume a `max_mutants=500` run at 400 done, true rate 2/min:

| | value |
|---|---|
| after 10 min | `mutations_created=420`, `elapsed=600s` |
| computed rate | 420/600 = 0.70/s = **42/min** (true: 2/min — 21× inflated) |
| reported ETA | 80 / 0.70 = 114s → **`ETA=1m54s`** |
| actual | 80 / 2 = **40 min** |

The error decays only as the new run's share grows; a resume near the cap stays
wrong for essentially its whole duration. No test covers the resumed path
(`tests/monitoring/test_eta_ticker.py` builds every `StopContext` by hand).

Note `WallClockStopper` is *not* affected in the same way — its
`estimate_remaining` ignores throughput and uses `budget_seconds - elapsed`,
which matches its own `should_stop`. So on resume the wall-clock ETA stays
self-consistent (the budget simply restarts), while the `rate=` and
`remaining=` fields on the same log line are still inflated.

## Bug 2 — the initial-seed drain is permanently baked into the denominator

`_run_start_time` is set at `steady_state.py:84`, **before** Phase 0:
`_await_idle()` at line 97 drains the initial seed population. Seeds are loaded
by the program loader, not by `mutant_task`, so `mutations_created` stays 0
throughout — but the clock is already running.

Those seconds never leave `elapsed_seconds`. The module docstring
(`eta_ticker.py:4-5`) claims the warmup guard handles this:

> Skips log while warming up (< 3 mutants) to avoid noisy early estimates
> dominated by initial evaluation.

The guard (`_tick:43-44`) only suppresses the first few *log lines*. It does not
remove initial-eval time from the denominator, so the bias persists for the
whole run and decays only asymptotically. The docstring describes a mitigation
that isn't implemented.

**Worked example** — `max_mutants=500`, 15 min seed drain, then 2 mutants/min:

| | value |
|---|---|
| at t=45 min | `total_mutants=60`, `elapsed=2700s` |
| computed rate | 1.33/min (true: 2/min) |
| reported ETA | 440 / 0.0222 = **5:30:00** |
| actual | 440 / 2 = **3:40:00** |

50% overestimate. This hits chain tasks (HoVer/HotpotQA) hardest — their seed
evaluation is the most expensive.

Same root cause, more generally: a lifetime average can't track a throughput
that changes (endpoint slowdowns, CPU starvation). A windowed/EWMA rate over
recent mutants would fix both this and shorten Bug 1's tail.

## Bug 3 — `CompositeStopper(mode="all")` under-reports when a child is unbounded

`stopper.py:162-176` filters to bounded children, then returns `max(...)` for
`mode="all"`. But "all" means the run continues until **every** child fires — if
any child is unbounded, the true remaining time is unknown, and the max over the
bounded subset is a lower bound reported as if it were the answer.

The sibling method gets this right (`stopper.py:178-185`): `remaining_dispatches`
returns `None` for `"all"` unless *every* child is bounded. The two methods
disagree — good evidence the `estimate_remaining` branch is the wrong one.

Latent: no shipped config uses `mode="all"` (`config/stopper/` has only the
`mode: any` composite), and no test covers it.

## Also noted (cosmetic / unreachable)

`_unbounded_label` (`eta_ticker.py:74-100`) probes children with a dummy
throughput of `0.0`. `MaxMutantsStopper.estimate_remaining` returns `None` when
`mutants_per_second <= 0` (`stopper.py:66-67`), so a *bounded* MaxMutants child
would be reported as "the unbounded one". Currently unreachable — the label is
only used when the composite already returned `None`, which given `tp > 0`
implies no bounded child exists — but it's a fragile probe.

## Smaller semantic gap

ETA measures time to the last mutant **dispatch**. `mutations_created` is
incremented at the post-persist handoff (`mutant_task.py:309`), and the run then
waits in `_await_terminal_drain()` (`steady_state.py:138`) for all in-flight DAG
evaluations. So the ETA converges to 0 while roughly one pipeline-depth
(~2 × `max_in_flight`) of evaluation is still outstanding. Arguably "time to last
dispatch" is the intended quantity, but the line is labelled `ETA`.

## Suggested fixes, in priority order

1. **Bug 1** — measure throughput over this run only: snapshot
   `mutations_created` alongside `_run_start_time` and divide the *delta* by
   elapsed. Cheapest correct fix; needs a `StopContext` field or an engine-side
   baseline, since `_tick` currently can't see the restored offset.
2. **Bug 2** — either start the clock after the Phase 0 drain, or (better,
   fixes both 1 and 2) switch to a windowed/EWMA rate over recent mutant
   completions.
3. **Bug 3** — return `None` from `estimate_remaining` under `mode="all"` when
   any child is unbounded, matching `remaining_dispatches`.
4. Correct the `eta_ticker` docstring — the warmup guard does not do what it
   claims.

Tests to add: resumed-run tick, post-seed-drain tick, `mode="all"` composite
with a mixed bounded/unbounded child set.

## Resolution

Bugs 1 and 2 share one fix: `ThroughputWindow` in `eta_ticker.py` keeps
`(elapsed_seconds, total_mutants)` samples and reports the delta across a
trailing 600s window. Differencing two cumulative samples cancels the restored
offset outright (Bug 1) and ages the seed drain out one window after it ends
(Bug 2); it also lets the rate follow a real throughput change instead of
smearing it. No engine change was needed — the fix is contained in the
monitoring module.

Bug 3 fixed in `CompositeStopper.estimate_remaining`: `mode="all"` now returns
`None` unless every child is bounded, matching `remaining_dispatches`.

`_unbounded_label` now probes children with the live ctx and throughput rather
than a synthetic zero-rate context, so a bounded child that declines to estimate
under a degenerate rate is no longer mislabelled as the unbounded one.

The stale docstring is rewritten to explain the window and why a lifetime
average is wrong.

**Deliberately not fixed:**

- The drain-tail gap (["Smaller semantic gap"](#smaller-semantic-gap)) — closing
  it means modelling in-flight evaluation latency, which is a different piece of
  work from correcting the rate.
- `EngineThroughput.elapsed_seconds` still carries run elapsed, not the span, so
  `mutants_per_second * elapsed_seconds` no longer equals `total_mutants`. The
  field is documented rather than repurposed; changing it would silently alter a
  public contract for every stopper.
- No guards against counter or clock regression: `elapsed_seconds` comes from
  `time.monotonic()` and `mutations_created` only ever increments, so such a
  guard would be unreachable code.
