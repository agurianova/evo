# Technical Codebase Map: D-side hard-floor → smooth tanh scoring

## Mechanism Domain

Fitness function formulation — `pop_b/evaluate.py` scoring path only. No topology,
no aggregator config, no archive, no wiring changes.

---

## Entry Points

| Component | File | Symbol | Lines | Role |
|---|---|---|---|---|
| D scoring (CHANGE TARGET) | `problems/heilbron_repro_v1/pop_b/evaluate.py` | `evaluate()` happy path | 96–99 | Computes `raw_delta`, clamps to `delta`, emits `score` into `per_opp_metrics` |
| D scoring — exception path (CHANGE TARGET) | same file | `evaluate()` except branch | 117–118 | Hardcodes `score=0.0` on exception; must also use smooth formula or keep at `0.5` |
| D invalid-slot sentinel (REVIEW) | same file | `_invalid_opp_metrics()` | 42–49 | Returns `score: 0.0` for skipped opponents (`is_valid=0.0`) — gated out by aggregator; semantically safe but see note below |
| D metrics spec (REVIEW) | `problems/heilbron_repro_v1/pop_b/metrics.yaml` | `fitness` spec | 2–9 | Documents `lower_bound: 0.0`, `upper_bound: 1.0`, description still says "Worsening counts as 0, not negative" |
| D aggregator config (READ-ONLY) | `config/aggregator/heilbron_improver.yaml` | `fitness` output | 23–25 | `op: mean, field: score` — schema-agnostic, works with any `score ∈ [-∞, ∞]` |
| G scoring (ASYMMETRY — see §5) | `problems/heilbron_repro_v1/pop_a/evaluate.py` | `evaluate()` | 109–110 | `resistance_score = 1.0 - min(delta / Q_MAX, 1.0)` — linear, NOT tanh |

---

## Hydra Wiring

This change is **config-free** — no new YAML, no Hydra override, no pipeline change.

The `evaluate.py` file is loaded by problem name (`problem.name=heilbron_repro_v1/pop_b`). The treatment activates simply by editing the file. The existing `heilbron_improver.yaml` aggregator reduces `score` via `op: mean` — no YAML edit needed.

To verify correct loading after edit:
```bash
python run.py problem.name=heilbron_repro_v1/pop_b --cfg job 2>&1 | grep evaluate
```

---

## Silent Fallback Modes

Three paths in `evaluate()` that emit `score`; all three must be considered:

| Path | Current behaviour | After smoothing | Risk |
|---|---|---|---|
| Happy path (lines 96–99) | `delta = max(raw_delta, 0.0); score = min(delta/Q_MAX, 1.0)` | Replace with tanh | CHANGE TARGET |
| Exception catch (lines 111–120) | `score = 0.0` | Keep as `0.5` (neutral) or apply `tanh(0)=0.5` explicitly | MUST UPDATE — currently 0.0 will stick out as anomaly after smoothing; consider `score = 0.5 * (np.tanh(0.0 / Q_MAX) + 1.0)` which evaluates to `0.5` |
| `_invalid_opp_metrics()` (lines 42–49) | `score: 0.0, is_valid: 0.0` | Leave as-is | SAFE — `is_valid=0.0` gates this record out of `ConfigurableAggregator.aggregate()` before `field: score` is ever read; the `0.0` value is never consumed |

No try/except wraps the *score assignment itself* — the computation is outside the try block.  
The try/except at line 88 catches `improve_fn()` execution failures; the score path (lines 96–99) is inside the try, so an arithmetic error (e.g. division by zero from Q_MAX=0) would fall to the except and emit `score=0.0`. This is not a concern with the tanh form since tanh is numerically safe everywhere.

---

## Blast Radius

GitNexus reports **zero upstream callers** of `evaluate()` (impact risk: LOW). The function is loaded dynamically by the problem executor — it is never imported by path.

| Depth | Consumers of `score` field | Impact |
|---|---|---|
| d=1 (direct) | `heilbron_improver.yaml`: `fitness: op=mean, field=score` | Score is aggregated to `program.fitness` — range changes from `[0,1]` to `(0,1)` under tanh; mean is still in `(0,1)`. **No schema break.** |
| d=1 (direct) | `DGTrackerStage` (`dg_tracker_stage.py:199`) | Forwards `per_opp_metrics[i]` verbatim to Redis tracker. Reads `delta`, not `score`. **Unaffected.** |
| d=2 (indirect) | MAP-Elites archive | Uses `actual_fitness` (= `max(post_q)`, unchanged) as primary via `MetricsContext`. `fitness` (= mean score) used as the MAP-Elites selection signal — smoothed values still in `(0,1)` and `higher_is_better=True`. **No break.** |
| d=2 (indirect) | `mutation_operator.py:207` | Reads `primary_key` (= `fitness`) from `program.metrics`. Value is still `(0,1)`. **Unaffected.** |
| d=2 (indirect) | `MetricsContext.is_valid()` | Keys off `is_valid` field, not `score`. **Unaffected.** |

No code path checks `score == 0` or `score == 0.0` as a semantic sentinel. The grep across all Python and YAML found zero such checks outside `_invalid_opp_metrics()` (which is itself gated by `is_valid=0.0`).

---

## Feasibility Assessment

**Rating: GREEN**

Rationale:
- Exactly one function's inner three lines change.
- Zero upstream Python importers of `evaluate`.
- `ConfigurableAggregator` is schema-agnostic: reads `score` by field name, no range assumption.
- `metrics.yaml` bounds (`lower_bound: 0.0, upper_bound: 1.0`) are metadata only — used for prompt formatting, not enforcement. Smooth `score ∈ (0,1)` stays within declared bounds.
- `DGTrackerStage` passes `per_opp_metrics` verbatim; reads `delta`, not `score`.
- Archive uses `actual_fitness` (unchanged) as primary dimension.
- Exception-path `score=0.0` is the only gotcha — updating it to `0.5` is a one-liner.

---

## Q_MAX Sensitivity Note

With `tanh(raw_delta / Q_MAX)` and `Q_MAX = 0.0365`:

| `raw_delta` | score |
|---|---|
| `-Q_MAX` | 0.119 |
| `0` | 0.500 |
| `+Q_MAX` | 0.881 |
| `+2*Q_MAX` | 0.982 |

The score saturates quickly: a `raw_delta` at exactly `Q_MAX` already yields 0.88, and at `2*Q_MAX` it reaches 0.98. This is tighter than the original linear form which was still linear at `delta = Q_MAX/2`.

**Recommendation:** Use `2*Q_MAX` as denominator for a wider effective gradient range:

```python
score = 0.5 * (np.tanh(raw_delta / (2 * Q_MAX)) + 1.0)
# raw_delta = +Q_MAX  → 0.731  (still improving, not saturated)
# raw_delta = +2*Q_MAX → 0.881
# raw_delta = 0        → 0.500
# raw_delta = -Q_MAX   → 0.269
```

This gives a gradient signal over the biologically plausible `[-Q_MAX, +2*Q_MAX]` range instead of saturating at `+Q_MAX`. Elena should treat the denominator factor (1× vs 2× vs 3×) as a hyperparameter choice — document it explicitly in the design rather than inheriting `Q_MAX` from the original linear formula.

---

## G-Side Asymmetry (Item 5)

G's current scoring (`pop_a/evaluate.py:110`):
```python
resistance_score = 1.0 - min(delta / Q_MAX, 1.0)   # linear clamp, [0,1]
```

D's proposed scoring:
```python
score = 0.5 * (np.tanh(raw_delta / Q_MAX) + 1.0)   # tanh, (0,1)
```

**These are no longer zero-sum.**

Under the original hard-floor design, `D.score + G.resistance_score = 1.0` only when `delta >= 0` (they were complementary by construction — `D.score = delta/Q_MAX`, `G.resistance = 1 - delta/Q_MAX`).

After D smoothing, the relationship becomes:
- `D.score(raw_delta) = 0.5*(tanh(raw_delta/Q_MAX) + 1)`
- `G.resistance(raw_delta) = 1.0 - min(max(raw_delta,0)/Q_MAX, 1.0)`
- `D.score + G.resistance ≠ 1.0` for any `raw_delta`

This is not a code correctness issue — the two populations use independent fitness signals by design. But it means:
1. The "zero-sum adversarial game" interpretation no longer holds.
2. `raw_delta < 0` (G resists D): D is penalized (score < 0.5), but G gets full `resistance=1.0` (linear did not penalize D at all here, giving G nothing extra for large margins). Under tanh, D gets a softer penalty; G still gets `1.0` regardless of margin.
3. `raw_delta >> Q_MAX` (D dominates): D saturates near 1.0; G saturates near 0.0 (both linear and tanh converge here).

**Recommendation for Elena:** Either (a) accept the asymmetry for this experiment — treating D smoothing in isolation is the `d-smoothing-minimal` scope — or (b) simultaneously update G to `resistance = 0.5*(1.0 - tanh(raw_delta/Q_MAX))` for a consistent tanh-symmetric game. A G-side update requires a separate file edit to `pop_a/evaluate.py` and becomes a two-file change, which contradicts the "exactly one file" constraint. Flag this as a design decision.

---

## Recommended Treatment Specification

**Exact code change** (`pop_b/evaluate.py` lines 96–99):

```python
# Before (lines 96-99):
post_q = float(get_smallest_triangle_area(improved))
raw_delta = post_q - pre_q
delta = max(raw_delta, 0.0)
score = min(delta / Q_MAX, 1.0)

# After:
post_q = float(get_smallest_triangle_area(improved))
raw_delta = post_q - pre_q
delta = raw_delta                                           # no floor — raw delta preserved
score = 0.5 * (np.tanh(raw_delta / Q_MAX) + 1.0)          # smooth, ∈ (0,1), admits negative
```

**Exception path** (lines 117–118): change `score = 0.0` to `score = 0.5` (neutral, consistent with `tanh(0)=0.5`).

**Docstring** (line 7): update "Worsening counts as 0, not negative" to reflect new semantics.

**metrics.yaml** `fitness.description` (line 3): update to remove "Worsening counts as 0, not negative."

**numpy import**: `np` is already imported (`import numpy as np` line 16). No new imports needed.

**No other files change** if scope is kept to D smoothing only.

---

## Existing Code Patterns to Reuse

| Precedent | File | What it did | Reusable? |
|---|---|---|---|
| G smooth resistance (PR #219, commit 2de8267e) | `pop_a/evaluate.py:110` | Replaced binary `float(delta<=0)` with `1.0 - min(delta/Q_MAX, 1.0)` — continuous, zero-sum with D | Partial — same spirit, different form. This used linear+clamp; D proposal uses tanh. |
| `pop_b_soft` sigmoid variant | `problems/heilbron_adversarial/pop_b_soft/evaluate.py` | Sigmoid `_sigmoid(delta / _T)` with `_T = Q_MAX/9`, returns flat `metrics` dict (OLD contract, no artifact/aggregator) | NOT directly portable — old contract, different problem path, different temperature rationale. Read for reference only. |

The `pop_b_soft` pattern confirms the sigmoid/tanh design direction but is a legacy variant (flat metrics dict, no `per_opp_metrics` artifact, different base path). Do not copy it — implement directly in `heilbron_repro_v1/pop_b/evaluate.py`.
