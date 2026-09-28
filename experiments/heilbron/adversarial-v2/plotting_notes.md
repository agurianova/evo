# Adversarial Plotting Requirements

## Problem

Standard GigaEvo plots use `cummax(frontier_fitness)` — monotonically increasing frontier. This is WRONG for adversarial experiments because adversarial fitness is non-stationary (depends on current opponent population).

- **Constructor adversarial fitness**: resistance component changes as Improvers evolve. cummax freezes a snapshot against opponents that no longer exist.
- **Improver fitness**: mean normalized improvement across opponent configs. As Constructors harden, even a better Improver scores lower. Declining line ≠ regression.
- **actual_fitness (raw min_area)**: objective, stationary. cummax is fine here.

## Required Plots

### Tier 1 — Watchdog + Checkpoint (every hourly PR comment)

| Plot | X | Y | cummax? | Notes |
|------|---|---|---------|-------|
| actual_fitness trajectory | gen | frontier actual_fitness | YES (monotonic) | Ground truth metric |
| Adversarial fitness (current) | gen | frontier adversarial fitness | NO — current value | Drops = opponents got stronger |
| Resistance trajectory | gen | Constructor frontier resistance | NO — current value | Arms race progress |
| Improver acceptance rate | gen | rolling 10-gen window % accepted | NO | 0% = dead population |

### Tier 2 — Closeout Analysis

| Plot | What it shows |
|------|---------------|
| Constructor actual_fitness vs Improver acceptance rate (dual-axis) | Coupling between populations |
| Generation parity (paired runs) | Sync hook health |
| n_opponents over time | Archive growth/saturation |
| Adversarial fitness decomposition: quality vs resistance (stacked) | Which component drives changes |

### Tier 3 — Feedback Mechanism Monitoring (new for v2)

| Plot | What it shows |
|------|---------------|
| Mutation prompt token count over time | Context bloat (K=3 vs K=1) |
| Mutation latency over time | LLM slowdown from longer prompts |

## Tools to Fix During /experiment-implement

1. **`comparison.py`**: Add `--adversarial` flag that plots current-gen metrics instead of cummax frontier. Default remains cummax for backward compat.
2. **`trajectory.py`**: Fix "Last improvement" line — for adversarial fitness it should say "Last improvement (adversarial, non-monotonic)" or suppress the line entirely when the metric is non-stationary.
3. **Watchdog (`run_watchdog.py`)**: Generate the 3-panel Tier 1 view (actual_fitness cummax, adversarial fitness current, Improver acceptance rate) instead of single cummax line.
4. **`status.py`**: Already shows current-gen — no change needed.

## Key Principle

For adversarial games, visualize **two interacting time series**, not one monotonic frontier. The watchdog comment should make the co-evolutionary dynamics legible at a glance.
