# Live Reporting Bugs — Root-Cause Audit (heilbron/k5-budget-v3)

**Scope**: Investigated by `general-purpose` agent during `/experiment-closeout heilbron/k5-budget-v3`, in response to user directive: *"we need to doagose all bugs in reporting yes"* and follow-up *"and sometimes reports show fitness N/A or gen N/A"*.

**Trigger observations**:
- K5_2_G showed `Gen: null` in live status despite being ALIVE with 440 Redis keys and the slowest validator timings (347 s mean, 843 s max). After kill the same run reported Gen=52 correctly.
- Across runs, Fitness and/or Gen intermittently show as `N/A` / `null`.

## Executive Summary

Twelve reporting bugs collapse to **one dominant cause plus several amplifiers**. Dominant cause: `EvolutionEngine.run()` (`gigaevo/evolution/engine/core.py:164-166`) never writes `engine:total_generations=0` to Redis before entering `step()`. `SteadyStateEvolutionEngine` does this correctly (`steady_state.py:108-111`), so this is an EvolutionEngine-only regression. For slow-validator runs like K5_2_G the first generation can take 30–60 minutes with the `{prefix}:run_state` hash field entirely absent; every reader sees `hget(...) → None` and either prints `?`/`null` or silently coerces to `0`/`0.0`, which pollutes recorded checkpoints. Amplifiers: no Redis socket timeout (B3), one bare `except Exception` that wipes the whole status row on any failure (B4), `None → 0/0.0` coercions that write zeros into `experiment.yaml` (B5/B6), and watchdog stall detection that self-defeats when gen reads 0 (B7).

## Bug Table

| ID  | Severity | Symptom                                                         | Root cause                                                                                           | File:line                                                                              | Proposed fix                                                                                  |
| --- | -------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| B1  | CRITICAL | `Gen=null` / `gen=0` despite ALIVE process + keys (K5_2_G case) | `EvolutionEngine.run()` never persists `engine:total_generations=0` before first `step()`           | `gigaevo/evolution/engine/core.py:164-166`                                             | Add `await self.storage.save_run_state(_RUN_STATE_TOTAL_GENERATIONS, …)` after `_running=True` |
| B2  | MAJOR    | `Fitness=?/N/A` on runs with valid programs but no improvement  | `valid_frontier_<metric>` only appended on improvement; `lindex -1` returns None when list empty     | `tools/status.py:108-116`; `_template/run_watchdog.py:109-113`                          | Fall back to `valid_iter_<metric>_mean` last entry; mark "(no frontier yet)"                  |
| B3  | MAJOR    | Transient `Gen=null` under Redis load                           | `redis.Redis(host,port,db)` has no `socket_timeout`; recv blocks trip `except Exception`             | `tools/status.py:92`                                                                   | Add `socket_timeout=5, socket_connect_timeout=2`                                              |
| B4  | MAJOR    | One dead lookup blanks the entire row                           | Single bare `except Exception` wraps `dbsize` + all `hget`/`lindex` calls                            | `tools/status.py:165-177`                                                              | Per-metric try/except; surface `status["error"]` separately                                   |
| B5  | MAJOR    | Checkpoint records `best_fitness=0.0` pollution in yaml         | `fitness = json.loads(raw)['v'] if raw else 0.0` silently coerces None→0.0                           | `.claude/skills/experiment-checkpoint/SKILL.md:197`                                     | `... if raw else None`, preserve null through serializer                                      |
| B6  | MAJOR    | Closeout prints `0/52` for runs whose counter never flushed     | `gen = int(r.hget(...) or 0)` coerces missing key to 0                                               | `.claude/skills/experiment-closeout/SKILL.md:26`; checkpoint:122,195                    | Branch on raw None as "unknown" vs raw "0"                                                    |
| B7  | MAJOR    | Watchdog posts `gen=0`; stall detection can't fire              | `get_generation` returns 0 on exception; `stalled = … and gen > 0` masks the stall                   | `experiments/_template/run_watchdog.py:100-102` + 14 derived copies                    | Return `int \| None`; stall logic treats None separately                                       |
| B8  | MINOR    | Metric-name drift: reader queries new name, Redis has old       | `status.py` reads metric_name from yaml at read-time, not from engine write-time                     | `tools/status.py:45-67`; `_template/run_watchdog.py:66`                                 | Write `primary_metric=<name>` to `run_state` at engine start; readers prefer that             |
| B9  | MINOR    | `check_invalidity` hardcoded to `valid_iter_fitness_mean`       | Literal string ignores `METRIC_NAME` already read from manifest                                      | `experiments/_template/run_watchdog.py:123`                                             | `f"...:valid_iter_{METRIC_NAME}_mean"`                                                        |
| B10 | MINOR    | `get_val_fitness` hardcoded to `valid_frontier_fitness`         | Literal string ignores `METRIC_NAME`                                                                 | `experiments/_template/run_watchdog.py:109`                                             | `f"...:valid_frontier_{METRIC_NAME}"`                                                        |
| B11 | MINOR    | "stage_timeout too short" warning suppressed when B1 active     | `gen = status["gen"] or 0`; guard `gen >= 3` never true when gen None                                | `tools/status.py:406-412`                                                              | When gen is None, estimate from `len(valid_gen_<metric>_mean)`                                 |
| B12 | MINOR    | `diagnose.py` misattributes B1 as MAJOR "Generation count is 0" | Same `int(gen) if gen else 0` coercion                                                               | `.claude/skills/experiment-diagnose/scripts/diagnose.py:119-120`, `:1374-1384`          | Treat None separately; downgrade severity; cross-link to B1                                    |

## Detailed Analysis

### B1 — K5_2_G "alive but Gen=null" (CRITICAL)

`EvolutionEngine.run()` at `gigaevo/evolution/engine/core.py:153-200`:
- Line 164-166 sets `self._running = True` and reads in-memory `self.metrics.total_generations` but **does not** call `save_run_state`.
- `step()` at line 202-262 runs phases 1-7, increments at line 259, and persists at line 260-262.

Contrast `gigaevo/evolution/engine/steady_state.py:108-111`:

```python
# Persist initial epoch counter so status tools can read it immediately
await self.storage.save_run_state(
    _RUN_STATE_TOTAL_GENERATIONS, self.metrics.total_generations
)
```

Consequence for K5_2_G:
- Validator mean 347 s / max 843 s → a single generation easily takes tens of minutes.
- The entire duration of each `step()` leaves `{prefix}:run_state` without `engine:total_generations`.
- `r.hget(f"{prefix}:run_state", "engine:total_generations")` returns `None`; `if raw_gen:` at `tools/status.py:99` is False; `gen` stays None; status prints `?` (user terminal rendered as "null").
- Programs, metrics history, archive keys all present (→ 440 keys) because those go through other write paths.

### B2/B3/B4 — "Fitness=N/A" and silent-swallow amplifiers

`tools/status.py:108-116` returns None whenever `valid_frontier_<metric>` is empty (no improvement yet) — expected early in adversarial D-runs where the seed is optimal and deltas floor at 0. The outer bare `except Exception` at `:165-177` wraps the whole function body — a single slow `dbsize()` under local contention raises, everything returns None. The client has no `socket_timeout`, so it can block indefinitely.

### B5/B6 — None→0 corruption in reporters

`experiment-checkpoint/SKILL.md:197` writes `best_fitness=0.0` into `experiment.yaml`'s `checkpoints:` array whenever the frontier list is empty, indistinguishable from real 0.0. Over a 52-gen run this produces spurious flat-zero segments in later plots. Closeout SKILL.md:26 uses `or 0` on the gen read, turning "counter never flushed" into "gen 0/52" — exactly K5_2_G's false diagnosis.

### B7 — Watchdog stall-detection self-defeat

`experiments/_template/run_watchdog.py:93-102` returns 0 on any Redis exception. Line 377: `stalled = (gen == _last_gen[run['label']]) and gen > 0`. When gen reads 0 (from exception or B1) stall detection can't fire because `gen > 0` is false — watchdog cheerfully posts "gen 0/52" every hour with no alarm.

### B8/B9/B10 — Metric-name drift and hardcoded suffixes

`git status` on this branch shows `problems/heilbron_adversarial/pop_{a,b}/metrics.yaml` modified during the experiment window. `_template/run_watchdog.py` reads `METRIC_NAME` from manifest on line 66 but hardcodes `valid_frontier_fitness` / `valid_iter_fitness_mean` at 109/123.

### B11/B12 — Diagnose/warning suppression under B1

`tools/status.py:406` `gen = status["gen"] or 0` and `:408` `if inv is not None and inv > 0.75 and gen >= 3:` — when B1 hides gen, the "stage_timeout too short" warning that would have explained K5_2_G's slow validator never fires. `diagnose.py:119-120, :1374` share the coercion and report "Generation count is 0 (MAJOR)" as a misleading root cause.

## Recommended Patch Order

1. **B1** — 1-line insert in `gigaevo/evolution/engine/core.py:166`, eliminates the dominant cause.
2. **B3** — 1-line Redis-client kwargs in `tools/status.py:92`.
3. **B7** — template fix + backport to 14 per-experiment `run_watchdog.py` copies via `/post-experiment-fixes`.
4. **B5, B6** — SKILL.md edits to preserve None.
5. **B2** — iter-mean fallback in `status.py` and watchdog template.
6. **B4** — narrow the `except Exception` in `status.py:165-177`.
7. **B8** — persist `primary_metric` to `run_state` at engine start.
8. **B9, B10** — parameterise hardcoded suffixes in watchdog template.
9. **B11, B12** — None-aware branches in warnings and diagnose severity.

No fixes applied — diagnosis only.
