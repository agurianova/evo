# Redesign Brief: Heilbron-Adversarial — successor to k5-budget-loose

**Status**: design draft, not yet pre-registered
**Predecessor**: `heilbron/k5-budget-loose` (stopped 2026-04-16, `running → invalid`, PR #207)
**Author**: Claude session 2026-04-16, distilling D-fitness investigation + design discussion
**Owner decisions to date**:
- 2026-04-16: bundle = Smoothed Fitness + deterministic Hall-of-Fame
- 2026-04-16: drop the "random slot" — pure deterministic top-K HoF
- 2026-04-16: cache invalidation via `cache_on` input edges (no base.py change)
- 2026-04-16: apply symmetrically to G (parallel hard-floor flaw discovered in `pop_a/evaluate.py:95`)
- 2026-04-16: keep `Q_MAX=0.0365` at default — no retuning (consistent with baseline, which was also untuned)

---

## Why we are redesigning

`k5-budget-loose` and all prior Heilbron-adversarial experiments showed D failing to achieve nontrivial improvement. Investigation in this session identified two structural flaws — both hard-floor pathologies on the adversarial component of fitness — and one re-evaluation flaw.

### Flaw 1 — D's fitness hard floor (`pop_b/evaluate.py:78`)

```python
scores.append(min(max(delta, 0.0) / Q_MAX, 1.0))
```

Any failed-improvement attempt clamps to `0.0`. With deployed `n_opponents=1`, D's fitness collapses to {win=positive, lose=0.0}. Empirically: 60–90% of D programs sit at fitness=0.0 *exactly* across all 4 D runs at gen ~1–2. MAP-Elites cannot diversify when most cells contain identical-fitness programs.

### Flaw 2 — G's resistance hard floor (`pop_a/evaluate.py:95`) — newly identified

```python
resistance_scores.append(float(delta <= 0))
```

Symmetric pathology, masked by G's intrinsic `quality` term carrying 50% of fitness. Resistance ∈ {0, 1} per opponent, averaging to discrete `{0, 1/K, ..., 1}`. The same MAP-Elites collision dynamics apply on the resistance dimension, just diluted by quality.

### Flaw 3 — re-evaluation noise

`_epoch_refresh` (`steady_state.py:574`) re-DAGs every archive program every epoch. The current `OpponentArchiveProvider.get_opponents` uses **stochastic softmax sampling** (`opponent_provider.py:189`) — different draw every refresh. With K=1, each re-eval is a single noisy trial → cell elites flip-flop on opponent luck rather than program quality.

### What's *already* in our favor

- Existing `OpponentArchiveProvider` is essentially a stochastic Hall-of-Fame (softmax-weighted by fitness). Switching to deterministic top-K is a one-line change (`get_top_k` already exists at `opponent_provider.py:218`).
- `InputHashCache` already gates expensive stages (LLM `InsightsStage`, `LineageStage`). They cache once per program because their inputs (program code, parents) are immutable. We exploit this by adding opponent context as a `cache_on` input.
- `archive_reeval` flag already exists in `AdversarialPipelineBuilder` — flipping to `true` enables `InputHashCache` on `FetchOpponentResultsStage`.

So the design surface is mostly *config + edge wiring*, not new mechanism.

---

## The redesign bundle

| # | Change | Where | Touches |
|---|---|---|---|
| 1 | Smoothed D fitness `tanh(delta/Q_MAX)` | `pop_b/evaluate.py:78` | 1 line |
| 2 | Smoothed G resistance `tanh(-delta/Q_MAX)` | `pop_a/evaluate.py:95` (+ rescale `(resistance+1)/2`) | 1 line |
| 3 | Deterministic HoF: `get_top_k(K)` not `get_opponents(K)` | `FetchOpponentIdsStage` (1 call swap) | 1 line |
| 4 | K = L = 3 (was K=1, L=1) | experiment YAML override | config |
| 5 | `archive_reeval: true` | experiment YAML override | config |
| 6a | New `CacheOnlyInput(StageIO)` model with `cache_on: Any = None` | `gigaevo/programs/stages/common.py` | ~6 LOC |
| 6b | Swap `InputsModel: VoidInput → CacheOnlyInput` for `InsightsStage` and `LineageStage` (required because `VoidInput` forbids extra fields) | `insights.py:35`, `insights_lineage.py:45` | 2 lines |
| 6c | `cache_on` edge: `FetchOpponentIdsStage → InsightsStage`, `→ LineageStage` | `asymmetric_pipeline.py` | 2–4 edges |
| 7 | CIAO master-tournament diagnostic at closeout | new `analysis/ciao.py` | post-hoc only |

**Total estimated diff**: ~40–70 LOC + 2 config files. No `base.py` changes. One small shared model added; no new module-boundary changes.

---

## Detailed implementation

### Change 1 — Smoothed D fitness

**File**: `problems/heilbron_adversarial/pop_b/evaluate.py:78`

```python
# Before:
scores.append(min(max(delta, 0.0) / Q_MAX, 1.0))

# After:
import math  # at top
scores.append(math.tanh(delta / Q_MAX))   # ∈ (−1, 1)
```

Then at line 89:

```python
# Before:
fitness = sum(scores) / len(scores)        # ∈ [0, 1]

# After:
mean_score = sum(scores) / len(scores)     # ∈ (−1, 1)
fitness = (mean_score + 1.0) / 2.0         # ∈ (0, 1) — keep MAP-Elites bounds
```

**Rationale**: continuous gradient through 0; programs that *worsen* a config get a meaningfully-negative score (not erased to 0); same asymptotic behavior at extreme deltas. Matches Wasserstein loss intuition for adversarial training.

### Change 2 — Smoothed G resistance

**File**: `problems/heilbron_adversarial/pop_a/evaluate.py:95`

```python
# Before:
resistance_scores.append(float(delta <= 0))

# After:
import math  # at top
resistance_scores.append(math.tanh(-delta / Q_MAX))   # ∈ (−1, 1); +1 = D failed
```

Then at line 107:

```python
# Before:
fitness = ALPHA * quality + (1.0 - ALPHA) * resistance

# After:
resistance_norm = (resistance + 1.0) / 2.0   # ∈ (0, 1)
fitness = ALPHA * quality + (1.0 - ALPHA) * resistance_norm
```

(`resistance` itself is left in `(−1, 1)` for diagnostics.)

### Change 3 — Deterministic HoF via `get_top_k`

**File**: `gigaevo/adversarial/stages.py` — `FetchOpponentIdsStage.compute()`

Switch the provider call:

```python
# Before:
opponents = await self._provider.get_opponents(self._n)

# After:
opponents = await self._provider.get_top_k(self._n)
```

Both methods already exist on `RedisOpponentArchiveProvider`. No new code needed.

**HoF rotation is organic**: `get_top_k` reads the current archive's top-K each call. As G evolves, top-K membership shifts. Rotation rate slows as the run converges (the natural HoF stability property the user wants).

### Change 4 — K = L = 3

**Config** (in next experiment's `experiment.yaml`):

```yaml
n_opponents: 3
source_prompt_k: 3       # all 3 source codes shown in D's prompt — preserves white-box contract
```

`SourceCodeInjectionStage` (`source_injection.py:89-90`) already ranks K opponents by fitness and shows top-L. With K=L=3 it's a no-op pass-through.

### Change 5 — `archive_reeval: true`

**Config**:

```yaml
archive_reeval: true
```

Effect: `FetchOpponentResultsStage` switches to `InputHashCache` keyed on opponent IDs. Combined with deterministic HoF (Change 3), opponent IDs are stable across epochs whenever HoF is unchanged → cache hit → no opponent re-execution. Pure efficiency gain, no behavioral change.

### Change 6 — `cache_on` edges for analysis stages

**Insight (user 2026-04-16)**: `InsightsStage` and `LineageStage` write metric-deltas-and-transitions into the mutation prompt. Those prompts are stale if the underlying metrics shift due to opponent rotation. We want the cache to invalidate *exactly* when the opponent set rotates.

**Mechanism**: wire `FetchOpponentIdsStage`'s output as an additional input to `InsightsStage` and `LineageStage` via a regular data flow edge. The stage's `compute()` ignores this input; the existing `_compute_inputs_hash` naturally folds it into the cache key.

**File**: `gigaevo/adversarial/asymmetric_pipeline.py`, in both G and D paths:

```python
self.add_data_flow_edge(
    "FetchOpponentIdsStage", "InsightsStage", "cache_on"
)
self.add_data_flow_edge(
    "FetchOpponentIdsStage", "LineageStage", "cache_on"
)
```

**Stage-side (REQUIRED — not optional)**: both `InsightsStage` (`gigaevo/programs/stages/insights.py:35`) and `LineageStage` (`gigaevo/programs/stages/insights_lineage.py:45`) currently declare `InputsModel = VoidInput`. `VoidInput` inherits `StageIO`'s `model_config = {"extra": "forbid"}`, so passing `cache_on` through the DAG edge would fail pydantic validation. Concrete change:

1. Add a shared model in `gigaevo/programs/stages/common.py` (or per-stage if we want layering isolation):

```python
class CacheOnlyInput(StageIO):
    """Inputs that exist purely to participate in cache-key hashing.

    The wired input value flows into `model_dump()` and through the
    SHA256 content hash, but the stage's compute() ignores it.
    """
    cache_on: Any = None
```

2. Swap `InputsModel: type[StageIO] = VoidInput` → `InputsModel: type[StageIO] = CacheOnlyInput` in `InsightsStage` and `LineageStage`.

3. Edge wires `Box[Any]` (FetchOpponentIdsStage's output type) into the `cache_on` slot — pydantic accepts via `Any`. The Box's `data` field (the ID list) is what gets serialized into the hash.

No `compute()` changes — both stages already ignore their `params` (Insights uses agent on `program`; Lineage uses `program.lineage.parents`).

**Verification (DONE 2026-04-16)**: PASS. `Stage.compute_inputs_hash()` (`base.py:149-151`) returns `params.content_hash`, where `StageIO.content_hash` (`core_types.py:24-25`) is `sha256(cloudpickle.dumps(self.model_dump()))[:16]`. `model_dump()` includes all field *values*, not just names. Therefore: adding `cache_on: list[str] | None = None` to the `InputsModel` of `InsightsStage` / `LineageStage` and wiring the edge is sufficient — the opponent ID list changes will flip the hash. **No `base.py` change needed.**

**Cost trajectory**:
- Early run: HoF unstable (population diverging) → opponent IDs change → cache miss → LLM re-runs on lineage/insights.
- Mid/late run: HoF stabilizes → cache hits → near-zero LLM re-run cost.
- Cost shape matches "pay for analysis when it matters."

### Change 7 — CIAO diagnostic (post-hoc)

**New analysis script**: `gigaevo/analysis/ciao.py`

After closeout, for each D run:
1. Sample G programs at milestone gens: 1, N/4, N/2, 3N/4, N (where N = `max_generations`).
2. Sample current best D programs at the same milestones.
3. Compute pairwise fitness D[i] × G[j] → 5×5 matrix.
4. Plot heatmap.

**Interpretation**: D[N] beating G[1..N] uniformly → genuine improvement. D[N] beating only G[N] → drift / Red Queen pathology HoF didn't fully eliminate. Standard coevolution diagnostic (Cliff & Miller 1995).

---

## Related work — where this bundle sits

### Co-evolution literature

| Bundle element | Established practice | Citation |
|---|---|---|
| HoF-3 (deterministic top-K) | Hall of Fame to prevent intransitive cycling | Rosin & Belew 1997 |
| Best-K opponents from archive | Best-response training / fictitious play | Brown 1951; PSRO: Lanctot et al. 2017 |
| Smoothed continuous fitness | Standard in modern co-evolution; binary loss is known-weak signal | Pollack & Blair 1998; Ficici 2004 |
| Opponent-aware cache invalidation (`cache_on`) | Implicit in PSRO's iterated empirical-game updates | Lanctot et al. 2017 |
| CIAO master-tournament diagnostic | Standard cycling/forgetting diagnostic | Cliff & Miller 1995 |

**Closest paradigm match**: PSRO (Policy-Space Response Oracles). Our setup is a *continuous-population PSRO with MAP-Elites quality-diversity*. Standard PSRO carries a flat policy pool; we maintain a behavior-space-diverse archive (Mouret & Clune 2015). QD + co-evolution is the deliberate novelty — the literature has done QD alone (Cully, Mouret) and co-evolution alone (Lanctot, Vinyals); the combination is rarer (POET; Wang et al. 2019, 2020 — different setting).

### GAN training analogues

| Bundle element | GAN analogue |
|---|---|
| Smoothed `tanh` fitness | Wasserstein loss (Arjovsky et al. 2017) — smoother gradient signal |
| Hard-floor `max(delta, 0)` collapse | Vanishing gradient pathology in original GAN — JS saturation |
| HoF-3 to combat forgetting | Replay buffer of past discriminators (Salimans et al. 2016) — stabilization |
| MAP-Elites archive | Anti-mode-collapse via *structural* diversity — vs. GAN's *implicit* tricks (PacGAN, minibatch discrimination) |
| K=L (D sees what D is judged on) | White-box / non-saturating G loss — information-flow analog |

**Where we structurally differ from GANs**: no gradients (fitness is a discrete scalar; mutation is LLM-driven). Smoothing is the only direct import; GAN regularization tricks (spectral norm, R1, optimism) require a parameter manifold we don't have.

### One-line paper framing

> *Continuous-population PSRO with MAP-Elites quality-diversity, smoothed Wasserstein-style fitness, and deterministic Hall-of-Fame opponents — applied to LLM-guided program synthesis under co-evolutionary pressure.*

---

## Resolved decisions (interview 2026-04-16)

| # | Decision | Resolution |
|---|---|---|
| Q_MAX | Retune for `tanh`? | **No.** Keep default `0.0365`. `tanh(1)≈0.762` is in useful gradient range. Baseline was never tuned for Q_MAX → tuning here adds an uncontrolled DoF. |
| HoF size | K = 3 vs 5? | **K = 3** (canonical). Pilot first; revisit only if signal too noisy. |
| Cold start | How to handle `archive_size < K` at gen 0–1? | **`K_eff = min(K, archive_size)`.** Average D fitness over whatever's available. No special INVALID path beyond existing `n_opponents=0` guard. |
| Hash semantics | `_compute_inputs_hash` folds value or presence? | **Verify now, before pre-registration** (see verification section below). Blocks `cache_on` design lock-in. |
| Feedback axis | Vary `feedback_mode` (composition vs gradient_in_prompt)? | **Yes, vary as a factor.** `program update` (composition, mutation_type=d_improvement) vs `prompt injection` (gradient_in_prompt) is too important to fix arbitrarily. |
| Run count | Total runs in next experiment? | **8 runs** (4 G + 4 D, same as k5-budget-loose). |

### Arm matrix (8 runs = 4 conditions × 2 populations)

Given the {bundle vs baseline} × {composition vs gradient_in_prompt} factorial:

| Arm | Fitness | Opponents | Feedback to G | G run | D run |
|---|---|---|---|---|---|
| A1 | linear (status quo) | K=1 stochastic | composition | 1 G run | 1 D run |
| A2 | linear (status quo) | K=1 stochastic | gradient_in_prompt | 1 G run | 1 D run |
| B1 | smoothed (tanh) | K=3 deterministic HoF | composition | 1 G run | 1 D run |
| B2 | smoothed (tanh) | K=3 deterministic HoF | gradient_in_prompt | 1 G run | 1 D run |

**What this measures**:
- A vs B (same column): clean test of {smoothing + HoF} bundle on D's improvement-rate signal.
- 1 vs 2 (same row): test of feedback mechanism for G — does composition (structural) beat gradient_in_prompt (textual)?
- A1 ≈ k5-budget-loose continuation (calibrates against prior data).

**Tradeoff**: smoothing + HoF are bundled (not separately identified). If B clearly wins, follow-up experiment can isolate which intervention matters. Acceptable because both are independently motivated by the literature (Wasserstein loss, Rosin-Belew HoF).

**Open**: HoF size sensitivity (K=3 vs K=5). Reserved for follow-up if B arms don't show signal.

---

## Out of scope (deliberately excluded)

- **Pareto coevolution / DECA / IPCA**: would eliminate drift entirely but requires reworking MAP-Elites archive and selection. Weeks not days. Reconsider only if smoothed+HoF proves insufficient.
- **POET / open-ended adaptive curriculum** (Wang et al. 2019, 2020): different research question; revisit as a separate thread.
- **Opponent-aware *content* in InsightsStage/LineageStage prompts**: i.e., feeding opponent code into the LLM agent. Would improve insight quality but adds a separable evaluation question. Defer to a follow-up; this redesign uses opponent IDs only as a cache key, not as agent-visible content.
- **Random opponent slot**: ruled out 2026-04-16. HoF rotation provides organic diversity through population dynamics; explicit randomization adds noise that defeats the cache-stability win.
- **Sliding-window opponents**: HoF achieves the same drift mitigation more cleanly.
- **Asymmetric inner iterations** (`inner_iterations > 1`): GAN folklore says k>1 inner D steps stabilize; not in scope here, revisit if a future experiment shows D underpowered.

---

## Compute budget delta vs k5-budget-loose

| Cost component | Status quo (K=1, stochastic) | Bundle (K=3, deterministic HoF + cache_on) | Delta |
|---|---|---|---|
| D mutation LLM calls | 1 per program | 1 per program | unchanged |
| D mutation prompt input tokens | 1 source code | 3 source codes | +30–60% |
| Per-program opponent execution (fresh) | 1 | 3 | 3× on first eval |
| Per-program opponent execution (refresh) | 1 (NO_CACHE) | 0 with stable HoF, 3 on rotation | **lower on average** |
| InsightsStage/LineageStage LLM calls | 1 per program (cached forever) | 1 per program × HoF rotation events | small increase, bounded by rotation rate (slows over time) |
| G side | unchanged | symmetric improvements | analogous |

**Net estimate**: ~+30–50% LLM input tokens per D mutation; opponent-execution cost dominated by HoF stability (cheaper at convergence than today). Should fit within k5-budget-loose-equivalent budget. Run a smoke test before final pre-registration to confirm.

---

## Pre-registration checklist

Before opening the next pre-registration:

- [x] Q_MAX retuning decision (kept default).
- [x] HoF size decision (K=3).
- [x] Cold-start policy (`K_eff = min(K, archive_size)`).
- [x] Feedback-mode axis decision (vary as factor).
- [x] Arm structure decision (2×2 factorial, 8 runs).
- [x] **Verify `_compute_inputs_hash` folds edge input *values* into hash** — PASSED 2026-04-16. `content_hash = sha256(cloudpickle(model_dump()))` includes all field values. No base.py change required.
- [ ] Smoke test on 50 D mutants against a fixed G to verify smoothed fitness distribution (no more 0.0 point mass).
- [ ] Smoke test on 50 G programs to verify smoothed resistance distribution.
- [ ] Run 5-min smoke with logging to confirm `get_top_k` returns deterministic IDs across calls and that `archive_reeval=true` actually skips opponent execution on stable IDs.
- [ ] Update `04_issues_log.md` with the G hard-floor finding (parallel to D's, currently only D is logged).

---

## Closing notes

This is the "best easy SOTA shot" within the constraint that we don't rework MAP-Elites or fitness representation entirely. The deliberate simplifications:

- No new module — uses existing `get_top_k`, existing `archive_reeval`, existing edge-wiring.
- No base.py changes (hash-semantics verification PASSED 2026-04-16).
- No randomization in opponent eval — HoF rotation through population dynamics is the only diversity source.
- Symmetric treatment of G and D (smoothing applies to both; same flaw exists in both).

If after this redesign D *still* fails to achieve nontrivial improvement, the next escalation is full Pareto coevolution (DECA-style), which is a multi-week effort.

Researcher should re-read this brief before opening the next pre-registration and update the open questions section with answers before locking the protocol.
