# heilbron/k5-budget-v3 — Final Design Document

MAP-Elites redesign for the G/D adversarial co-evolution loop. Locked 2026-04-18 after iteration against k5-budget-loose/REDESIGN.md, three reference papers (GAME, DRQ, Rainbow Teaming), and the Gate 0 empirical-premise check on v2 G archives.

## 0. Locked Decisions

- **Target**: `heilbron/k5-budget-v3`.
- **2D role-specific BDs** on both populations. GAME ISAL 2025 pattern.
- **Structurally asymmetric BDs, symmetric y-axis naming.** G's BD is `(actual_fitness, wins)`; D's BD is `(fitness, wins)`. `wins` is the career-coverage statistic on both sides (same key name, role-specific semantics). The x-axes differ because the roles differ: G has a *separate intrinsic objective* (raw min_area) distinct from its adversarial outcome (resistance); D's adversarial outcome IS its objective. Forcing a symmetric x-axis would either re-introduce scalarization on G or invent a non-existent intrinsic metric for D. See §3 for the full rationale; still 1:1 transferable to HoVer/HotpotQA modulo the same structural question per task.
- **`fitness` is the intra-cell tie-break on both sides, not a universal BD axis.**
  - pop_a `fitness` = tanh-smoothed resistance against the current K=3 D HoF: `(tanh(−mean_delta/Q_MAX)+1)/2` ∈ [0, 1]. Pure selector key — NOT on G's BD.
  - pop_a `actual_fitness` = raw `min_area` (paper reporting scalar AND G's BD x-axis).
  - pop_b `fitness` = tanh-smoothed mean Δ across K=3 G HoF: `(tanh(mean(delta/Q_MAX))+1)/2` ∈ [0, 1]. Both D's BD x-axis AND intra-cell tie-break (dual-role — see §3.2).
  - Both sides: `wins` = career count via `DGImprovementTracker` inverted indices.
- **Gate 0 FAIL on `(quality, resistance)`** — pooled `|ρ(q,r)| = 0.78`, p ≈ 0 on v2 G archives; all four individual runs fail the `|ρ| < 0.7` threshold. The original `resistance` axis is rejected as a BD axis because it is collinear with quality (see `gate0_spearman.md`). `resistance` is retained as G's `fitness` (intra-cell tie-break only); v3's `wins` axis (career count) is count-valued → orthogonal to any monotone transform of fitness; PSRO row/column sums on both sides.
- **Niche-structured selection — drop `fitness = ALPHA·quality + (1-ALPHA)·resistance` entirely.** ALPHA is removed from the codebase. Quality pressure on G now lives on the BD x-axis (`actual_fitness`) via MAP-Elites' "fill new cells" rule; resistance pressure lives in G's `fitness` (intra-cell tie-break). All four G-selector slots and all four D-selector slots key on each side's own `fitness`. Gate 0's `ρ(fitness_v2, quality) = +0.996` confirms empirically that the scalarized v2 `fitness` was a monotone transform of `quality` anyway, carrying no additional selection pressure — v3 restores that pressure by routing quality onto its own BD axis instead.
- **Opponent sampling reuses the existing `OpponentArchiveProvider` ABC.** v3 adds one new concrete subclass (`CellStratifiedRedisOpponentArchiveProvider`) — Hydra swap, no new abstractions.
- **Career coverage via `DGImprovementTracker`** with two inverted indices (D-keyed for D's `wins`, G-keyed for G's `wins`). Same tracker, symmetric PSRO row/column statistics. 24h TTL = effectively infinite for active programs + dead-program GC (not a sliding window).
- **Adversarial feedback = D-in-prompt only.** `GradientInPromptStage` shows top-1 per-G D improver (with per-G delta) in G's mutation prompt; if no per-G tracker entry exists, **no D is injected** (no global-top-1 fallback). DoG composition (`CompositionInjectionHook`) is disabled for v3 to keep archive cell occupancy reflecting genuine evolutionary dynamics, not synthetic (D∘G) injections.

## 1. Motivation in One Paragraph

k5-budget-loose collapsed (D: 60–90% at fitness=0.0; 55–79% per-gen offspring rejected by cell collisions) because the archive is 1D-on-`fitness` for a 2-metric problem. Ficici & Pollack (GECCO 2003) prove the collapse theoretically; GAME (ISAL 2025), DRQ (Sakana 2026), and Rainbow Teaming (NeurIPS 2024) all prescribe role-specific 2D BDs + niche-structured (non-scalarized) selection as the canonical fix. v3 applies that prescription to our existing MAP-Elites + Redis tracker infrastructure with minimal code change.

## 1.5 Research Question, Primary DV, Decision Criteria (addresses 02_review.md C2)

**Research question.** Under v3's 2D MAP-Elites + niche-structured selection (no ALPHA scalarization), does a larger HoF lag `K=5` produce better final G configurations than the tighter `K=3`, on the Heilbronn n=11 adversarial coevolution task? (v2's 1D-on-scalarized-fitness pipeline at `K=3` serves as an archived external baseline — on disk under `heilbron/k5-budget-v2`, DBs 1/3/5/7 — against which "2D-vs-1D" is reported post-hoc but is not a live arm of v3.)

**Primary dependent variable.** Best `actual_fitness` (raw min_area) achieved by any G in the pop_a archive at `max_generations=50`, pooled across runs within an arm.

**Secondary DVs (reported, not decisive).**
- Archive occupancy: fraction of 225 G cells populated at gen 50 (diversity proxy).
- D adversarial pressure proxy: mean D `fitness` against current G HoF at gen 50 (confirms D didn't collapse).
- Cell-collision rejection rate: fraction of offspring rejected for landing in an occupied, lower-fitness cell (v2's killer metric; should drop from 55–79% → <30%).
- `ρ(G.actual_fitness_gen50, G.wins_gen50)` on the final archive (confirms the y-axis resolves niches).
- Mean per-eval wall-clock time per arm (K=5 costs 5/3× more LLM calls per eval; efficiency accounting matters).

**Run matrix (k-lag study — addresses 02_review.md C5).**

| Arm | K | Runs | Labels | DBs | Processes |
|---|---|---|---|---|---|
| **k=3** | 3 | 4 | `k3A, k3B, k3C, k3D` | 1, 2, 3, 4 | 8 (pop_a + pop_b per DB) |
| **k=5** | 5 | 4 | `k5A, k5B, k5C, k5D` | 5, 6, 7, 8 | 8 (pop_a + pop_b per DB) |

Both arms run the IDENTICAL v3 pipeline — `algorithm=single_island_2d_g` on pop_a / `single_island_2d_d` on pop_b, `CellStratifiedRedisOpponentArchiveProvider` with asymmetric `fitness_key` (§8.3), tracker inverted indices, `SharedBenchmarkLineageStage` on D (§3.5), prompt-hiding for G metrics (§3.5), `GradientInPromptStage` per-G delta (§6.2). The ONLY difference is `opponent_provider.k` (and the corresponding `k` threaded into evaluate.py's HoF size). Independent Redis DBs, independent seeds, shared LLM proxy.

**Success criterion (pre-registered).** Mean best `actual_fitness` at gen 50 of ONE arm exceeds the other arm's mean by at least `2 × pooled_stdev`, pooled from the 8 runs. The directional hypothesis is that K=5 > K=3 (more stable lag → better signal fidelity), but a K=3 > K=5 outcome also constitutes a decisive result (K=3 preferred for throughput). Either direction returns a DECISIVE verdict.

**Failure criterion (pre-registered).** Both arms collapse (D `fitness` monotonically → 0 in any run, OR G archive occupancy <10% at gen 50). Returns a NEGATIVE verdict for v3 overall; both k-values are non-viable and v3 is refuted irrespective of which k was better.

**INCONCLUSIVE.** Effect between ±1σ and ±2σ gap between arms → weak directional signal, reported but does not bless a default k. Subsequent experiments should explore finer k resolution.

**v2-vs-v3 post-hoc reporting (not a live arm).** v3 gen-50 archives are compared against v2's archived gen-50 archives on the same Heilbronn n=11 task. Caveat: v2 ran at different generation counts (varied by arm), used different metric semantics (hard-floor scoring, v2 bug), and a different LLM temperature schedule. Any v2-vs-v3 claim is reported as *supporting* evidence only, with the full list of confounds spelled out.

## 2. Design Summary

```
                        G population                        D population
                        =============                        =============
BD axis x               actual_fitness                       fitness
                        raw min_area ∈ [0, 0.0365]           (tanh(mean(delta/Q_MAX))+1)/2 ∈ [0,1]
                        (paper scalar, intrinsic quality)    (per-eval mean improvement)

BD axis y               wins                                 wins
                        (SCARD dg_g_resisted:{g_id})         (SCARD dg_d_wins:{d_id})
                        career # of D's this G has resisted  career # of G's this D has beaten

Binning                 adaptive (linear over observed)      adaptive (linear over observed)
Resolution              15 × 15 = 225 cells                  15 × 15 = 225 cells

intra-cell tie-break    fitness = resistance                 fitness = mean_improvement
                        (tanh(−mean_delta/Q_MAX)+1)/2        (same as BD x-axis, dual-role)
                        NOT on BD

archive_selector        SumArchiveSelector                   SumArchiveSelector
                        fitness_keys: [fitness]              fitness_keys: [fitness]
                        (G.fitness = resistance)             (D.fitness = mean_improvement)
archive_remover         FitnessArchiveRemover                FitnessArchiveRemover
                        fitness_key: fitness                 fitness_key: fitness
elite_selector          FitnessProportionalEliteSelector     FitnessProportionalEliteSelector
                        fitness_key: actual_fitness          fitness_key: wins
                        (quality drives reproduction)        (career coverage drives reproduction)
migrant_selector        TopFitnessMigrantSelector            TopFitnessMigrantSelector
                        fitness_key: actual_fitness          fitness_key: wins

opponent_provider       CellStratifiedRedisOpponentArchiveProvider (NEW)
                        fitness_key: fitness                 fitness_key: fitness
                        k: 3                                 k: 3
                        — returns one elite per distinct BD cell, descending by fitness_key
                        (G side: hardest-to-improve G per cell; D side: strongest improver per cell)

adversarial feedback    D-in-prompt only (GradientInPromptStage)
                        per-G top-1 D with per-G delta in header; no injection when tracker has no per-G entry.
                        DoG composition (CompositionInjectionHook) disabled for v3.
```

**Structural asymmetry on x-axis, symmetric elsewhere.** G has three distinct signals: intrinsic quality (`actual_fitness` = raw min_area), per-eval adversarial resistance (`fitness`), and career adversarial coverage (`wins`). D has two: per-eval mean improvement (`fitness`) and career coverage (`wins`). The BD assigns G's *primary* objective (quality) to x, its *career* objective (coverage) to y, and its *transient* objective (resistance) to the intra-cell tie-break — exactly NSGA-II's rank + intra-rank decomposition (§II.A) mapped onto MAP-Elites. D has no separate intrinsic metric, so its `fitness` plays dual duty as both x-axis and tie-break.

Unchanged: `tanh`-smoothed D fitness, deterministic HoF, `archive_reeval=true`, `cache_on(FetchOpponentIdsStage → EnsureMetricsStage)` edge. All inherited from REDESIGN.md.

Unchanged: `tanh`-smoothed D fitness, deterministic HoF, `archive_reeval=true`, `cache_on(FetchOpponentIdsStage → EnsureMetricsStage)` edge. All inherited from REDESIGN.md.

## 3. Behavior Descriptors

### 3.1 G — `(actual_fitness, wins)`; `fitness` is intra-cell tie-break

G has three distinct signals; each maps to a different selection surface:

| signal | role | source | emitted as |
|---|---|---|---|
| intrinsic quality | BD x-axis | `pop_a/evaluate.py` — raw `min_area` | `actual_fitness` (also the paper reporting scalar) |
| career adversarial coverage | BD y-axis | `SCARD({prefix}:dg_g_resisted:{g_id})` — career # of D's this G has resisted (`delta ≤ 0`) | `wins` |
| per-eval adversarial resistance | intra-cell tie-break (selector `fitness_key`) | `(tanh(−mean_delta/Q_MAX)+1)/2` against current K=3 D HoF | `fitness` |

BD axes:

| axis | bounds | bins |
|---|---|---|
| actual_fitness | adaptive over `[0, 0.0365]` (v2 observed max ≈ 0.0345) | 15 |
| wins | adaptive over `[0, 150]` (v2 extrapolated `[0, ~48]` for G; grows with D population size) | 15 |

**Three-signal decomposition, no scalarization.** This is NSGA-II (§II.A) mapped onto MAP-Elites:
- **Primary objective = cell rank along x.** Higher `actual_fitness` lands G in a better x-cell. MAP-Elites' "fill new cells" rule is the quality ladder — every new high-quality region of the min_area landscape opens a new unoccupied cell, rewarding G directly for raising raw min_area. No weighted sum needed.
- **Secondary objective = cell rank along y.** Higher `wins` lands G in a better y-cell. This is the PSRO column sum (Lanctot 2017 §3.2), rewarding broad resistance across D lineages rather than repeated wins against the same D.
- **Tertiary tie-break = intra-cell `fitness`.** Within a fixed `(actual_fitness, wins)` cell, the G that most resists the *current* K=3 D HoF wins. This is the transient adversarial pressure: it keeps G's mutation under selection toward "hard against today's improvers" without letting transient wins dominate the stable quality/coverage objectives.

**Why `resistance` is not a BD axis.** Gate 0 FAIL (`gate0_spearman.md`): pooled `|ρ(quality, resistance)| = 0.778`, all four v2 runs over threshold. A `(quality, resistance)` BD would waste resolution along the diagonal. Routing resistance into the tie-break instead (`fitness = resistance`) preserves the pressure without the collinearity penalty: resistance now shapes selection conditional on cell, not independently of it. Count-valued `wins` is orthogonal to any monotone transform of `fitness` by construction (Lanctot 2017 §3.2).

### 3.2 D — `(fitness, wins)`; `fitness` is dual-role (BD x AND intra-cell tie-break)

D has no separate intrinsic metric analogous to G's `actual_fitness`: D's value IS its ability to improve G configurations. So D's `fitness` plays dual duty — BD x-axis AND intra-cell tie-break — without ambiguity (within a cell, all members share a bin on `fitness`, so intra-cell tie-break discriminates on the *raw* fitness value within that bin).

| axis | source | bounds | bins |
|---|---|---|---|
| fitness | `pop_b/evaluate.py` — `(tanh(mean(delta/Q_MAX))+1)/2` across K=3 G HoF | adaptive over `[0, 1]` (v2 observed `[0.18, 0.49]`) | 15 |
| wins | `SCARD({prefix}:dg_d_wins:{d_id})` — career # of G's this D has beaten (`delta > 0`) | adaptive over `[0, 250]` (v2 observed max = 202) | 15 |

v2 empirical support: 172 unique D improvers with win-counts min=1, p50=25, p75=45, p90=66, max=202 → ~11.5 D's/bin on a 15-bin adaptive partition. Narrow `fitness` range on D is fine: adaptive binning auto-scales; no empty-bin collapse. `wins` upper bound raised to 250 to comfortably exceed v2 max (was 150 in an earlier draft — 150 < 202 was a self-contradiction, flagged in 02_review.md).

**Why D's BD has no quality x-axis.** There is no intrinsic D metric. "How good is this improver in isolation" is undefined — an improver's value is defined only relative to the configurations it acts on. Mean improvement against the K=3 HoF is the canonical measurement; we already put it on x. Introducing, say, code complexity or random-perturbation magnitude as an x-axis would amount to inventing a spurious intrinsic objective. So D's BD is two-dimensional: transient performance × career coverage.

### 3.5 Lineage / Insights HoF-stability fix (NEW — addresses prior silent race condition)

#### 3.5.1 The race

`InsightsStage` and `LineageStage` (`gigaevo/programs/stages/insights_lineage.py`) take a program's metrics-history and its parent/descendants' metrics-history to compute "this mutation improved parent by +X.XXXXX" trend lines, which feed directly into the mutation prompt. The race:

```python
# gigaevo/llm/agents/lineage.py:165-172
parent_fitness = parent.metrics[primary_key]   # stored at parent's last eval
child_fitness  = child.metrics[primary_key]    # stored at child's eval
delta          = child_fitness - parent_fitness  # spurious if HoF rotated between them
```

If the K=3 opponent HoF rotates between a parent's evaluation and the child's, `parent.metrics["fitness"]` reflects parent's performance against *opponents_t₀* while `child.metrics["fitness"]` reflects child's performance against *opponents_t₁`. The delta is meaningless — we're subtracting scores from different games. The prompt then says "parent→child Δ=+0.03, KEEP THIS STRATEGY" when the child might actually be worse under a fair head-to-head.

Impact is not academic: v2 ran 700+ generations with lineage insights active; the ALPHA·quality decomposition made the effect partially invisible because `actual_fitness` is HoF-independent and carried most of the `fitness` signal (confirmed by Gate 0's `ρ(fitness_v2, quality) = +0.996`). v3 de-scalarizes `fitness`, which exposes this race.

#### 3.5.2 Two-pronged fix

**Prong 1 — G: hide HoF-dependent metrics from prompts.** In `problems/heilbron_adversarial/pop_a/metrics.yaml`, set:

```yaml
fitness:        {include_in_prompts: false}   # HoF-dependent → unsafe across HoF rotations
wins:           {include_in_prompts: false}   # monotone career count → uninformative for trend
actual_fitness: {include_in_prompts: true}    # HoF-independent → stable across time
```

Effect on G's prompts:
- `InsightsStage` trend lines use `actual_fitness` (raw min_area). A G whose parent had min_area=0.020 and child has 0.025 sees a true delta, regardless of D-HoF state.
- `LineageStage` "ancestors/descendants" columns show only `actual_fitness`. The HoF-dependent signals (`fitness`, `wins`) are routed entirely into the BD structure + selector keys, not into prompts.
- Net: `InsightsStage`/`LineageStage` remain cached on `cache_on=opponent_ids`, but the content they produce is now invariant to HoF rotation — so even if the cache is invalidated by HoF churn and re-run, the trend lines are stable.

**Prong 2 — D: shared-benchmark lineage comparison.** D has no `actual_fitness` analog (D's value is HoF-dependent by definition — see §3.2). Prong 1's approach doesn't apply. Instead, add a new stage `SharedBenchmarkLineageStage` that uses the `DGImprovementTracker` as ground-truth payoff matrix:

1. For program D₁ and its parent D₀, look up the set of G-opponents each has faced (`SCARD({prefix}:dg_d_faced:{d_id})` — NEW inverted index, §5).
2. Compute the intersection `shared = dg_d_faced(D₁) ∩ dg_d_faced(D₀)`.
3. For each `g_id ∈ shared`, fetch `(delta(D₁, g_id), delta(D₀, g_id))` from the tracker payoff matrix (`{prefix}:dg_improvements:{g_id}` — existing sorted set, keyed by d_id with delta as score).
4. Lineage trend = mean over shared G's of `(delta(D₁, g_id) - delta(D₀, g_id))`. This is the controlled experiment: same opponent, two improvers, direct comparison.
5. If `|shared| < MIN_SHARED` (default 2), skip lineage injection for this program — no dishonest delta.

Pseudo-code:

```python
# gigaevo/programs/stages/shared_benchmark_lineage.py (NEW)
class SharedBenchmarkLineageStage(Stage):
    OutputModel = LineageOutput
    cache_handler = NO_CACHE  # tracker state drifts independently of program code

    def __init__(self, *, dg_tracker, resolver, min_shared=2, **kwargs):
        super().__init__(**kwargs)
        self._tracker = dg_tracker
        self._resolver = resolver          # SharedBenchmarkResolver protocol
        self._min_shared = min_shared

    async def compute(self, program: Program) -> LineageOutput:
        parent = await self._load_parent(program)
        if parent is None:
            return LineageOutput(trend=None)
        shared = await self._resolver.shared_benchmark(program.id, parent.id)
        if len(shared) < self._min_shared:
            return LineageOutput(trend=None)
        pairs = await self._tracker.get_deltas_against(program.id, parent.id, shared)
        trend = sum(c - p for c, p in pairs) / len(pairs)
        return LineageOutput(trend=trend, n_shared=len(shared))


# gigaevo/adversarial/shared_benchmark_resolver.py (NEW)
class SharedBenchmarkResolver(Protocol):
    async def shared_benchmark(self, d_id_a: str, d_id_b: str) -> list[str]: ...

class DGTrackerSharedOpponentResolver:
    """Concrete resolver using the new dg_d_faced inverted index."""
    def __init__(self, dg_tracker): self._t = dg_tracker
    async def shared_benchmark(self, d_id_a: str, d_id_b: str) -> list[str]:
        a = await self._t.faced_by_d(d_id_a)
        b = await self._t.faced_by_d(d_id_b)
        return sorted(a & b)
```

**Key property.** `SharedBenchmarkLineageStage` produces honest trend signals even across HoF rotations because it compares improvers on the *same* G's. The trend is a true "D₁ improves this specific G better than D₀ did" measurement, not a cross-game score comparison.

**Tracker extension required.** `DGImprovementTracker` gets one more inverted index:

```python
_D_FACED_KEY_TEMPLATE = "{prefix}:dg_d_faced:{d_id}"   # NEW — Redis SET, d_id → set of g_ids faced
```

Written on every G↔D pair evaluation (not just "wins"), so lineage comparisons have a full opponent-overlap picture.

**Design asymmetry is fine.** G uses prong 1 (stable intrinsic metric in prompts); D uses prong 2 (shared-benchmark). This mirrors the §8.3 asymmetry — G has an HoF-independent metric, D does not, and the lineage logic reflects that structural fact.

## 4. Selector Architecture

**Key reframing: we are not inventing new selectors.** The four MAP-Elites selector slots (archive / remover / elite / migrant) already exist, already have `fitness_key` as a parameter, and work correctly. v3 just passes a different key value.

v3 routes DIFFERENT keys into each selector slot depending on whether the slot is **cell-internal** (archive_selector / archive_remover — decide who holds or gets killed per cell; read transient performance) or **archive-external** (elite_selector / migrant_selector — decide who reproduces or migrates across the whole archive; read the long-horizon signal). Same split on both sides, different key choices:

```yaml
# v3 selector key routing:
#
#                      G population                     D population
# archive_selector     fitness (resistance)             fitness (mean_improvement)
# archive_remover      fitness                          fitness
# elite_selector       actual_fitness (quality)         wins
# migrant_selector     actual_fitness                   wins
```

Rationale:
- **Cell-internal slots on `fitness`** — who holds a cell, and which cell dies when the archive is full, is a decision about transient adversarial performance. Within a `(actual_fitness, wins)` cell, G's transient resistance discriminates. Within a `(fitness, wins)` D cell, D's transient mean improvement discriminates (sub-bin resolution).
- **Archive-external slots on the long-horizon signal** — parent sampling and cross-island migration are decisions about who *carries the lineage forward*. The long-horizon signal on G is raw quality (`actual_fitness`); on D, career coverage (`wins`). Sampling parents proportional to transient `fitness` dilutes the signal we just routed onto the BD x-axis; sampling proportional to the durable signal reinforces it.

This split is standard in the newer QD literature (QDax, DCG-MAP-Elites): cell-internal vs archive-external slots serve different purposes, keying them on the same scalar is convenient but not principled. v3 takes the ~5 lines of YAML to split them correctly.

### 4.1 Opponent sampling also IS a selector-shaped problem

`OpponentArchiveProvider` (`gigaevo/adversarial/opponent_provider.py:53-107`) is the existing ABC for "give me opponents from an archive." Its `get_top_k(k)` method is conceptually identical to `TopFitnessMigrantSelector.select()` but serves the adversarial pipeline instead of cross-island migration.

The v3 change is a **new concrete subclass** of `OpponentArchiveProvider`, not a new abstraction:

```python
# gigaevo/adversarial/opponent_provider.py — NEW subclass
class CellStratifiedRedisOpponentArchiveProvider(RedisOpponentArchiveProvider):
    """Top-K with the constraint that no two picks share a BD cell.

    When the archive has ≥ k populated cells, returns one elite per cell,
    descending by fitness_key. Otherwise falls back to plain top-K-by-fitness_key
    (identical to parent behavior — no regressions when archive is sparse).

    Motivation: GAME ISAL 2025 §3.2 — diverse-opponent HoF dominates homogeneous
    top-K for co-evolutionary reward quality. Under v3's 2D BD, top-K-by-fitness
    clusters opponents in one BD cell; cell-stratified sampling forces behavioral
    diversity in the HoF, giving the ego population richer training signal.
    """

    def __init__(self, *args, fitness_key: str, **kwargs):
        super().__init__(*args, **kwargs)
        self._fitness_key = fitness_key

    async def get_top_k(self, k: int, *, higher_is_better: bool = True) -> list[OpponentProgram]:
        cells = await self._archive.list_cells_sorted_by_fitness(
            key=self._fitness_key, descending=higher_is_better,
        )
        picked: list[OpponentProgram] = []
        seen_cells: set[tuple[int, ...]] = set()
        for cell, elite_id in cells:
            if cell in seen_cells or len(picked) >= k:
                continue
            prog = await self._load_program(elite_id)
            if prog is not None:
                picked.append(prog)
                seen_cells.add(cell)
        if len(picked) < k:
            # Sparse-archive fallback: top up with plain top-K-by-fitness
            extra = await super().get_top_k(k - len(picked), higher_is_better=higher_is_better)
            picked += [p for p in extra if p.program_id not in {x.program_id for x in picked}]
        return picked[:k]
```

**Determinism requirement (load-bearing for cache invalidation).** `list_cells_sorted_by_fitness` and the resulting HoF ordering MUST be deterministic: cells sorted descending by `fitness_key`, ties broken by a stable secondary key (canonical choice: `program_id` ascending). The downstream cache contract treats the returned opponent-id *list* as a cache fingerprint — non-deterministic tie-breaking would silently invalidate (or worse, not invalidate) `LineageStage`/`InsightsStage` caches. A unit test asserts that two calls with the same archive state return byte-identical id lists.

Wired via Hydra (ASYMMETRIC — see §8.3 for the full rationale):

```yaml
# pop_a (G) side — samples D opponents, ranked by D's `fitness`
opponent_provider:
  _target_: gigaevo.adversarial.opponent_provider.CellStratifiedRedisOpponentArchiveProvider
  fitness_key: fitness                 # D's transient mean improvement
  higher_is_better: true
  k: 3

# pop_b (D) side — samples G opponents, ranked by G's `actual_fitness`
opponent_provider:
  _target_: gigaevo.adversarial.opponent_provider.CellStratifiedRedisOpponentArchiveProvider
  fitness_key: actual_fitness          # G's HoF-independent intrinsic quality (min_area)
  higher_is_better: true
  k: 3
```

Training-signal semantics:
- **G side (samples D opponents):** D's `fitness` = mean improvement → HoF is "strongest current improvers, one per (D.fitness, D.wins) cell" → G faces a diverse slate of strong D's. Resistance against this slate is then a meaningful signal.
- **D side (samples G opponents):** G's `actual_fitness` = raw min_area (HoF-independent) → HoF is "hardest configurations by intrinsic quality, one per (G.actual_fitness, G.wins) cell" → D faces a diverse, task-grounded slate. D's mean improvement against this slate is the headline training signal. Avoids the circularity of ranking G's by G's own resistance against past D's.

Backwards-compatible escape hatch: set `_target_` back to `RedisOpponentArchiveProvider` and you have the current K=3 top-fitness behavior exactly.

### 4.2 Why niche-structured selection gives quality pressure without weighted sums

The critical property: **quality is selected structurally, by cell identity**, not by appearing in the `fitness` scalar.

For G specifically:
- Cell rank along `actual_fitness` rewards raw min_area directly. A G with `min_area = 0.030` lands in a better x-cell than a G with `min_area = 0.020`, regardless of `fitness` (resistance). MAP-Elites' "fill new cells" rule ensures that any new region of the quality landscape — any unprecedented min_area value that opens a new cell — survives. That IS the quality gradient, delivered by the archive structure.
- Cell rank along `wins` rewards broad resistance career — PSRO column sum (Lanctot 2017 §3.2).
- Intra-cell `fitness` (resistance) rewards transient hardness against today's HoF.

So the incentive for G to improve raw min_area is: **open a new high-x cell that no current G occupies, and survive forever as its elite**. This is exactly the quality pressure the v2 scalarization delivered via `ALPHA·quality` — but now it lives in the archive topology rather than a weighted sum. Rainbow Teaming §3.3 shows this pattern works on LLM red-teaming without any diversity term in the loss. NSGA-II §II.A proves scalarization is strictly dominated by the rank-then-crowding decomposition; v3 is the MAP-Elites analogue of that proof.

For D: the x-axis is `fitness` itself, so intra-cell tie-break is somewhat redundant-by-construction (all members in a cell are in the same `fitness` bin). This is a real asymmetry — see §3.2 rationale. It's acceptable because D has no natural second performance metric.

Biological reading: a brittle-optimal G vs a robust-mediocre G are *different niches*, not competitors on a weighted-sum fitness. Ecology textbook (Rosenzweig 1995 ch. 7): speciation happens along one primary life-history axis (quality for G); predator-specific resistance is a secondary niche phenomenon (transient adversarial outcome) that shapes tie-breaks, not the primary fitness gradient.

## 5. Tracker Extensions

`DGImprovementTracker` gets two inverted indices mirroring its existing per-G sorted set. Zero behavioral change for existing consumers.

```python
class DGImprovementTracker:
    _KEY_TEMPLATE                 = "{prefix}:dg_improvements:{g_id}"     # existing
    _GLOBAL_PAIRS_KEY_TEMPLATE    = "{prefix}:dg_best_pairs"              # existing
    _INJECTED_PAIRS_KEY_TEMPLATE  = "{prefix}:dg_injected_pairs"          # existing
    _D_WINS_KEY_TEMPLATE          = "{prefix}:dg_d_wins:{d_id}"           # NEW — Redis SET
    _G_RESISTED_KEY_TEMPLATE      = "{prefix}:dg_g_resisted:{g_id}"       # NEW — Redis SET

    async def record_batch(self, pairs: list[tuple[str, str, float]]) -> int:
        pipe = self._redis.pipeline(transaction=False)
        d_wins: dict[str, set[str]] = {}
        g_resisted: dict[str, set[str]] = {}
        for d_id, g_id, delta in pairs:
            # existing per-G sorted set + global best-pairs writes (unchanged)...
            if delta > 0:
                d_wins.setdefault(d_id, set()).add(g_id)
            else:
                g_resisted.setdefault(g_id, set()).add(d_id)
        for d_id, g_set in d_wins.items():
            key = self._d_wins_key(d_id)
            pipe.sadd(key, *g_set)
            pipe.expire(key, self._ttl)
        for g_id, d_set in g_resisted.items():
            key = self._g_resisted_key(g_id)
            pipe.sadd(key, *d_set)
            pipe.expire(key, self._ttl)
        await pipe.execute()
        return sum(len(v) for v in d_wins.values())

    async def count_g_beaten_by_d(self, d_id: str) -> int:
        return int(await self._redis.scard(self._d_wins_key(d_id)))

    async def count_d_resisted_by_g(self, g_id: str) -> int:
        return int(await self._redis.scard(self._g_resisted_key(g_id)))
```

**TTL semantics (explicit)**: 24h wall-clock, refreshed on every write. For any program that keeps being evaluated (directly or via `archive_reeval=true`), the set never expires — `tracker_coverage_count` is effectively a career statistic. TTL only fires for fully dead programs, which is desired (dead-D/dead-G GC, not a sliding window).

## 6. DAG Stages

### 6.1 Coverage-count stages (NEW)

Two light stages, both `cache_handler = NO_CACHE` (tracker state drifts independently of program inputs):

```python
# gigaevo/adversarial/tracker_coverage_stages.py  (NEW file)

class ComputeDWinsCountStage(Stage):
    """Writes `wins` into D's metrics dict for BD axis y (§3.2)."""
    OutputModel = VoidOutput
    cache_handler = NO_CACHE

    def __init__(self, *, dg_tracker, **kwargs):
        super().__init__(**kwargs)
        self._tracker = dg_tracker

    async def compute(self, program: Program) -> None:
        program.metrics["wins"] = (
            await self._tracker.count_g_beaten_by_d(program.id)
        )


class ComputeGResistedCountStage(Stage):
    """Writes `wins` into G's metrics dict for BD axis y (§3.1)."""
    # ... same pattern, calls count_d_resisted_by_g, writes to program.metrics["wins"]
```

Both stages write to the **same key name `wins`** on their respective population's metrics dict. The key is disambiguated by population (pop_a writes G's resistance count; pop_b writes D's win count) — symmetric BD schema, no per-side key plumbing required.

Wired in `gigaevo/adversarial/asymmetric_pipeline.py` for each side's DAG. Position: **after** `DGTrackerStage` (so current-eval pairs are recorded) and **before** `EnsureMetricsStage` (so the BD value is in the metrics dict at bin time).

### 6.2 `GradientInPromptStage` amendments (D-in-prompt adversarial feedback)

Two changes to `gigaevo/adversarial/gradient_prompt.py`:

1. **Per-G delta in header.** When `dg_tracker.get_best_d_for_g(g_id)` returns a `(d_id, delta)` pair, thread `delta` into `_GRADIENT_HEADER` alongside D's intrinsic `fitness`. The prompt then tells G honestly: "this D improved *you* by +X.XXXXX", which is the signal G's mutation should be responding to, not D's general-purpose fitness against other Gs.

2. **No-data skip (drop global fallback).** If the tracker has no per-G entry for this G, `_select_best_d` returns `None` and `GradientInPromptStage` injects nothing. The previous behavior — falling back to `opponent_provider.get_top_k(1)` which returns the global-top-1 D by fitness — is removed. Rationale: a D that is generically strong but has never specifically improved *this* G provides a misleading signal; better a cleaner prompt than a dishonest one.

```python
# gigaevo/adversarial/gradient_prompt.py — pseudo-diff
_GRADIENT_HEADER = (
    "## Adversarial gradient signal\n"
    "A peer program with the following **improver fitness** {fitness:.5f} "
    "**improved *this* program by Δ = {delta:+.5f}** on a direct comparison. "
    "Study its implementation; consider where it out-performs yours.\n"
)

async def _select_best_d(self, program: Program) -> tuple[OpponentProgram, float] | None:
    result = await self._dg_tracker.get_best_d_for_g(program.id)
    if result is None:
        return None  # No per-G data → skip injection entirely (no global fallback)
    d_id, delta = result
    prog = await self._load_program(d_id)
    return (prog, delta) if prog is not None else None
```

DoG composition (`CompositionInjectionHook`) is **disabled** in v3's experiment.yaml — not deleted from the codebase, just not wired. This keeps v3's archive cell occupancy a pure reflection of evolutionary dynamics (no synthetic `D∘G` programs crowding cells).

## 7. Validation Gates

**Gate 0 — Empirical premise check. ✅ COMPLETE (FAIL verdict).**
Executed 2026-04-18 on v2 G archives (DBs 1/3/5/7, n=164 pooled). Pooled `|ρ(quality, resistance)| = 0.778` (p≈0); all four individual runs fail the `|ρ| < 0.7` threshold (range 0.71–0.83). Bonus finding: `ρ(fitness, quality) = +0.996` empirically confirms v3's scalarization critique. See `gate0_spearman.md` for verdict, interpretation, and reproducibility metadata; script at `gate0_spearman.py`. **Action**: fallback promoted to primary (see §0, §3.1).

**Gate 1 — D coverage sanity. ✅ COMPLETE (PASS, via tracker analytics).**
Planned axis `opponent_coverage_count` is superseded by the stronger `tracker_coverage_count` axis; viability check run 2026-04-18 on v2 tracker state (see §3.2 for distribution). 172 unique D improvers, pooled win-count p50=25 p90=66 max=202 — healthy multi-modal spread, no monomodal collapse at 0 or at K. Script: `/tmp/v2_gate0/flip_tracker.py` (D-centric flip of G-keyed tracker). Analytics script: `/tmp/v2_gate0/tracker_analytics.py`.

**Gate 2 — Smoke run (~30 min on a single node).** Fixed opponent HoF on both sides, 50 programs × 1 generation:
- G and D 2D archives fill > 20 cells each.
- `CellStratifiedRedisOpponentArchiveProvider.get_top_k(3)` returns programs from 3 distinct cells when ≥ 3 cells are populated.
- `cache_on(FetchOpponentIdsStage → EnsureMetricsStage)` invalidates when HoF rotates.
- Tracker inverted indices stay consistent with main per-G sorted set under random write sequences.
- `GradientInPromptStage` injects nothing when tracker has no per-G entry (no global fallback).

**Gate 3 — Pre-registration.** Standard GigaEvo flow: `experiment-implement` → `experiment-launch` → `experiment-checkpoint`.

**Post-experiment analysis.** Archive occupancy heatmaps at gen {0, 10, 25, 50} on `(fitness, wins)`; CIAO diagnostic; resistance-pressure proxy (mean `wins` on G over generations) to verify adversarial pressure survived the ALPHA removal; per-side `wins` histograms to confirm the y-axis resolves niches.

## 8. Config Surface

### 8.1 `problems/heilbron_adversarial/pop_{a,b}/metrics.yaml` — schema

Both sides share the same key names; descriptions differ per role. Only `fitness`, `is_valid`, `actual_fitness` (pop_a only), and `wins` carry `include_in_prompts: true`.

```yaml
# pop_a (G)
fitness: {is_primary: true, higher_is_better: true, lower_bound: 0.0, upper_bound: 1.0, include_in_prompts: true, significant_change: 0.01}
wins:    {is_primary: false, higher_is_better: true, lower_bound: 0.0, upper_bound: 150.0, include_in_prompts: true, significant_change: 1.0}
# + is_valid, actual_fitness (min_area paper scalar), mean_improvement (reporting), best_post_improvement, n_opponents

# pop_b (D)
fitness: {is_primary: true, higher_is_better: true, lower_bound: 0.0, upper_bound: 1.0, include_in_prompts: true, significant_change: 0.01}
wins:    {is_primary: false, higher_is_better: true, lower_bound: 0.0, upper_bound: 150.0, include_in_prompts: true, significant_change: 1.0}
# + is_valid, actual_fitness (best post-improvement min_area), mean_improvement_raw, mean_pre_quality, mean_post_quality, max_post_quality, n_opponents
```

### 8.2 Per-side algorithm configs (two files)

The BD x-axis and the reproduction keys differ per role, so v3 ships **two** algorithm configs. The selector YAML structure is identical; only the `behavior_space.keys`, `behavior_space.bounds`, and the external-slot `fitness_key` values differ.

#### `config/algorithm/single_island_2d_g.yaml` (NEW)

```yaml
defaults: [single_island, _self_]

behavior_space:
  _target_: gigaevo.config.helpers.build_behavior_space
  keys: [actual_fitness, wins]
  bounds: [[0.0, 0.0365], [0, 150]]
  resolutions: [15, 15]
  binning_types: [linear, linear]

archive_selector:
  _target_: gigaevo.evolution.strategies.selectors.SumArchiveSelector
  fitness_keys: [fitness]             # G.fitness = resistance
  fitness_key_higher_is_better: [true]
archive_remover:
  _target_: gigaevo.evolution.strategies.removers.FitnessArchiveRemover
  fitness_key: fitness
  higher_is_better: true
elite_selector:
  _target_: gigaevo.evolution.strategies.elite_selectors.FitnessProportionalEliteSelector
  fitness_key: actual_fitness         # quality drives reproduction
  higher_is_better: true
migrant_selector:
  _target_: gigaevo.evolution.strategies.migrant_selectors.TopFitnessMigrantSelector
  fitness_key: actual_fitness
  higher_is_better: true
```

#### `config/algorithm/single_island_2d_d.yaml` (NEW)

```yaml
defaults: [single_island, _self_]

behavior_space:
  _target_: gigaevo.config.helpers.build_behavior_space
  keys: [fitness, wins]
  bounds: [[0.0, 1.0], [0, 250]]
  resolutions: [15, 15]
  binning_types: [linear, linear]

archive_selector:
  _target_: gigaevo.evolution.strategies.selectors.SumArchiveSelector
  fitness_keys: [fitness]             # D.fitness = mean_improvement
  fitness_key_higher_is_better: [true]
archive_remover:
  _target_: gigaevo.evolution.strategies.removers.FitnessArchiveRemover
  fitness_key: fitness
  higher_is_better: true
elite_selector:
  _target_: gigaevo.evolution.strategies.elite_selectors.FitnessProportionalEliteSelector
  fitness_key: wins                   # career coverage drives reproduction
  higher_is_better: true
migrant_selector:
  _target_: gigaevo.evolution.strategies.migrant_selectors.TopFitnessMigrantSelector
  fitness_key: wins
  higher_is_better: true
```

Pipeline wiring: `experiments/heilbron/k5-budget-v3/experiment.yaml` selects `algorithm=single_island_2d_g` for pop_a runs and `algorithm=single_island_2d_d` for pop_b runs.

### 8.3 Opponent provider wiring (ASYMMETRIC — each side picks the task-grounded key for its opponents)

The selection key passed to `CellStratifiedRedisOpponentArchiveProvider` determines *which elite per cell is promoted to the K-sized HoF when the archive has more populated cells than K*. The correct key differs by side because G has an intrinsic task-grounded metric (`actual_fitness` = min_area) while D does not — D is a perturbation operator defined *relative* to G, so its quality signal is irreducibly HoF-dependent.

```yaml
# pop_a (G) — samples D opponents; rank by D's mean improvement
opponent_provider:
  _target_: gigaevo.adversarial.opponent_provider.CellStratifiedRedisOpponentArchiveProvider
  fitness_key: fitness              # D.fitness = tanh-smoothed mean Δ vs current G HoF
  higher_is_better: true
  k: 3
  # host/port/db/prefix inherited from base config

# pop_b (D) — samples G opponents; rank by G's intrinsic quality
opponent_provider:
  _target_: gigaevo.adversarial.opponent_provider.CellStratifiedRedisOpponentArchiveProvider
  fitness_key: actual_fitness       # G.actual_fitness = raw min_area (HoF-independent)
  higher_is_better: true
  k: 3
```

**Why the asymmetry** (locked 2026-04-18):

1. **G's `fitness` is circular as a D-side key.** G's fitness = resistance against the current D-HoF. Using it to pick G's for D would mean "pick opponents that *past* D couldn't crack" — a moving target that drifts with D-HoF rotation. It tells D nothing about today's cracking ability.
2. **`actual_fitness` is the only HoF-invariant signal G offers.** A G with min_area=0.030 is intrinsically harder to improve than one at 0.020, full stop. Ranking D's HoF by G's `actual_fitness` forces D to demonstrate competence on the actual Heilbronn problem, not on yesterday's weakest G's.
3. **D has no `actual_fitness` analog.** D's `actual_fitness` in metrics.yaml is "best post-improvement min_area" — still G-HoF-dependent. `wins` is career-stable but cold-starts new strong D's at 0. `fitness` is the most informative adversarial signal D can offer; cell-stratification on (fitness, wins) already delivers diversity, so `fitness` as the ranking key just means "pick the currently-most-effective D per cell."
4. **Stability downstream.** D-side lineage/shared-benchmark logic becomes tractable: "the elite of cell C under `actual_fitness`" does not wobble when D mutates. This is load-bearing for the §3.5 lineage fix.

## 9. Code Delta

### 9.1 Functional code changes

| File | Change | Approx LOC |
|---|---|---|
| `gigaevo/adversarial/dg_tracker.py` | Add THREE inverted-index key templates (`dg_d_wins`, `dg_g_resisted`, `dg_d_faced`), dual-write in `record_batch`, add `count_g_beaten_by_d` / `count_d_resisted_by_g` / `faced_by_d` / `get_deltas_against` methods | ~60 |
| `gigaevo/adversarial/opponent_provider.py` | Add `CellStratifiedRedisOpponentArchiveProvider` subclass. Determinism contract: ties broken by `(fitness_key DESC, program_id ASC)`; `get_top_k()` returns byte-identical id lists for identical archive states | ~60 |
| `gigaevo/adversarial/tracker_coverage_stages.py` (NEW) | `ComputeDWinsCountStage`, `ComputeGResistedCountStage` | ~50 |
| `gigaevo/adversarial/shared_benchmark_resolver.py` (NEW) | `SharedBenchmarkResolver` Protocol + `DGTrackerSharedOpponentResolver` concrete impl | ~40 |
| `gigaevo/programs/stages/shared_benchmark_lineage.py` (NEW) | `SharedBenchmarkLineageStage` — D-side honest lineage trend via payoff intersection | ~80 |
| `gigaevo/llm/agents/shared_benchmark_lineage.py` (NEW) | Agent + prompt template wired to the new stage | ~60 |
| `gigaevo/adversarial/asymmetric_pipeline.py` | (a) Wire coverage stages (after `DGTrackerStage`, before `EnsureMetricsStage`); (b) replace D's `LineageStage` with `SharedBenchmarkLineageStage`; (c) keep G's `LineageStage` (uses `actual_fitness` which is HoF-invariant) | ~30 |
| `gigaevo/adversarial/gradient_prompt.py` | (a) thread per-G `delta` into `_GRADIENT_HEADER`; (b) drop global-top-1 fallback — return `None` when tracker has no per-G entry | ~20 |
| `problems/heilbron_adversarial/pop_a/evaluate.py` | v3 clean-up: drop ALPHA / quality / resistance; keep tanh-smoothed resistance as `fitness`; emit raw min_area as `actual_fitness` | ~20 |
| `problems/heilbron_adversarial/pop_a/metrics.yaml` | `include_in_prompts: false` on `fitness`, `wins`; `include_in_prompts: true` on `actual_fitness`. (§3.5 Prong 1.) | ~5 |
| `problems/heilbron_adversarial/pop_b/metrics.yaml` | `include_in_prompts: true` stays on `fitness` (D has no HoF-independent alternative); also on `wins` | ~5 |
| `config/algorithm/single_island_2d_g.yaml` (NEW) | G-side 2D config; cell-internal slots → `fitness`, external slots → `actual_fitness` | ~50 |
| `config/algorithm/single_island_2d_d.yaml` (NEW) | D-side 2D config; cell-internal slots → `fitness`, external slots → `wins` | ~50 |
| `experiments/heilbron/k5-budget-v3/experiment.yaml` | 8 pair-runs across 4×k=3 (DBs 1–4) + 4×k=5 (DBs 5–8); asymmetric `opponent_provider.fitness_key`; `CompositionInjectionHook` disabled | ~40 |

### 9.2 Logging additions (mandatory — log-based verification contract depends on these, see §14)

| File | Added log events | Why |
|---|---|---|
| `gigaevo/adversarial/stages.py` (`FetchOpponentIdsStage`) | `[HOF_FETCH]`, `[HOF_ROTATE]` | Prove K-sized HoF fetched + rotation detection |
| `gigaevo/adversarial/opponent_provider.py` (`CellStratifiedRedisOpponentArchiveProvider`) | `[CELL_PICK]` with `{picks:[{cell,id,fitness}], fallback_used}` | Prove cell-stratified selection (not plain top-K) |
| `gigaevo/programs/stages/base.py` (cache path) | `[CACHE_HIT]` / `[CACHE_MISS]` with `{stage, program_id, content_hash, cache_on_ids}` | Prove cache invalidates on HoF rotation |
| `gigaevo/programs/stages/shared_benchmark_lineage.py` | `[LINEAGE_TREND]` with `{program_id, parent_id, n_shared, trend, skipped_reason}` | Prove shared-benchmark resolver in use; count skips |
| `gigaevo/programs/stages/insights_lineage.py` (G path) | `[LINEAGE_TREND_G]` with `{program_id, parent_id, metric, delta}` | Confirm G uses `actual_fitness` for trend |
| `gigaevo/adversarial/dg_tracker.py` | `[TRACKER_WRITE]` with `{pairs_count, d_wins_added, g_resisted_added, d_faced_added}` | Prove all three inverted indices populated |
| `gigaevo/adversarial/tracker_coverage_stages.py` | `[METRIC_EMIT]` with `{side, program_id, fitness, actual_fitness, wins, n_opponents, gen}` | Prove BD axis values emitted |
| `gigaevo/adversarial/gradient_prompt.py` | `[GRADIENT_INJECT]` with `{program_id, injected_d_id, delta, skipped_reason}` | Prove per-G delta in header; no global fallback |
| `gigaevo/evolution/strategies/selectors.py` (`SumArchiveSelector`) + `removers.py` (`FitnessArchiveRemover`) | `[ARCHIVE_MOVE]` with `{program_id, cell, fitness_key, fitness, action, displaced_id}` | Prove niche-structured selection (vs scalarized) |
| `gigaevo/evolution/mutation/prompt_composer.py` (or equivalent) | `[PROMPT_META]` with `{program_id, side, metrics_shown:[...], metrics_hidden:[...]}` | Prove G prompts exclude fitness/wins per §3.5 |

All log events MUST be structured with the prefix in square brackets, a stable key order, and machine-parsable payloads (prefer `logger.info("[{}] {}", tag, json.dumps(payload, sort_keys=True))`). Explicit contract — ad-hoc string interpolation is not acceptable because §14 flow reconstruction depends on grep-able, parseable output.

### 9.3 Tests (belt-and-braces, not primary verification)

| File | Change | Approx LOC |
|---|---|---|
| `tests/adversarial/test_dg_tracker.py` | Tests for three inverted indices (consistency + atomicity) | ~80 |
| `tests/adversarial/test_opponent_provider.py` | `CellStratifiedRedisOpponentArchiveProvider` — distinct cells, sparse fallback, determinism (byte-identical output) | ~70 |
| `tests/adversarial/test_shared_benchmark_lineage.py` (NEW) | Pipeline test: D parent/child with known shared G's produces correct trend | ~80 |
| `tests/adversarial_pipeline/test_gradient_prompt.py` | Update: per-G delta in header; no injection without per-G entry | ~40 |
| `tests/evolution/test_2d_mapelites_integration.py` (NEW) | Pipeline test: two D programs with same `fitness` but different `wins` land in different cells | ~60 |
| `tests/logging/test_log_events.py` (NEW) | Smoke test asserting all 10 log event types emit well-formed payloads under a 2-program fixture | ~100 |

Tests verify units in isolation; the real verification happens via §14 log-based flow reconstruction on the smoke run.

**Total ~900 LOC.**

## 10. Literature Mapping

| v3 decision | Reference | Finding |
|---|---|---|
| Role-specific 2D BDs per population | GAME (ISAL 2025, arXiv:2505.06617) Fig 2; DRQ (Sakana 2026, arXiv:2601.03335) §4.2 | Coupled-population QD requires per-role descriptors, not shared global BD |
| Outcome-based BDs (reject AST / geometric features) | DRQ §4.2; Enhanced POET (ICML 2020, arXiv:2003.08536) §4.2 Table 2 | Execution outcomes produce 2–3× richer niches than source-code features; also needed for task-portability |
| Niche-structured selection, drop scalarization | NSGA-II (Deb et al. IEEE TEC 2002) §II.A; MAP-Elites (arXiv:1504.04909) §3; Rainbow Teaming (NeurIPS 2024, arXiv:2402.16822) §3.3 | "Quality stored in the cell, diversity enforced by the grid, not by any diversity term in the loss." |
| Career coverage as BD axis | PSRO (NeurIPS 2017, arXiv:1711.00832) §3.2; Ranking Diversity (PPSN 2024) §5 | Payoff-matrix row/column sums are canonical diversity statistics; binary coverage anti-cycles 1.7× faster than magnitude |
| Cell-stratified opponent sampling | GAME §3.2 | Diverse-opponent HoF dominates homogeneous top-K for co-evolutionary reward quality |
| Hand-crafted (not learned) BDs | MAP-Elites §5; AURORA (arXiv:1905.11874) §6 | Learned BDs need 10⁴+ cheap rollouts; LLM evals too expensive |
| Stop at 2D | CVT-MAP-Elites (IEEE TEC 2018, arXiv:1610.05729) Fig 4; internal `hover/map-elites-topology` NULL | Archive occupancy drops exponentially in BD dimensionality at fixed budget |
| 1D-on-fitness is structurally wrong | Ficici & Pollack (GECCO 2003); Cartlidge & Bullock (GECCO 2004) | Single-scalar competitive coevolution provably converges to mediocre stable states |

## 11. Risks

| Risk | Mitigation |
|---|---|
| Dropping ALPHA removes resistance pressure on G → G "forgets" adversarial hardening | Resistance pressure is preserved via cell identity on G's `wins` axis (a G that resists many D's occupies a high-y cell, and MAP-Elites elite-fill rewards new cells). Verify post-hoc with mean-`wins`-over-generations plot; abort if it declines monotonically |
| D's `fitness` (tanh-smoothed mean Δ) selector over-weights transient HoF wins | Second axis (`wins`) orthogonalizes: a D that one-shots one weak G lands in a different cell than a D that has beaten 50 G. Intra-cell tie-break stays honest |
| `CellStratifiedRedisOpponentArchiveProvider` degenerates when archive has < k cells early-gen | Graceful fallback to plain top-K-by-fitness via `super().get_top_k()`; identical to baseline in that regime |
| Tracker inverted indices out of sync with main sorted set | Dual-write inside same Redis pipeline; unit test asserts `SCARD(dg_d_wins:d)` matches the set of G's where `d` appears in `dg_improvements:g` |
| Tracker TTL purges an active program's set mid-run | Won't happen: TTL refreshed on every write + `archive_reeval=true` keeps archive members rewriting. Purge fires only for fully dead programs, which is desired |
| `N_g` / `N_d` upper bounds wrong on other tasks | Declared per-task in `metrics.yaml.upper_bound`; adaptive binning auto-scales to observed range, so mis-set bounds cost resolution rather than correctness |
| Top bin of tracker axis saturates | Adaptive binning grows the range; saturation only possible if the observed max clamps at `upper_bound`. 150 ceiling is comfortably above v2's observed 202 pooled D-wins — expected to rarely bite. If it does, bump ceiling |
| Both populations drift into `wins ≈ 0` (collapse of the y-axis on either side) | `GradientInPromptStage` (D-in-prompt) provides direct adversarial signal; tracker writes only happen when G↔D interactions occur, so y-axis resolution tracks actual adversarial activity. Gate 2 smoke run verifies y-axis has > 0 spread on both sides |
| `GradientInPromptStage` no-data-skip yields mostly empty prompts in gen 0 | Expected and desirable. Gen 0 has no tracker data; prompt injection ramps up as tracker fills. Verified in Gate 2 |
| `cache_on` edge regression | Hard PR gate: grep `asymmetric_pipeline.py` for the `FetchOpponentIdsStage → EnsureMetricsStage` edge; reject PR if missing |

## 12. Out of Scope (Deferred to v4+)

- **Original G BD `(quality, resistance)`** — rejected by Gate 0 (pooled `|ρ| = 0.778`); retained as a candidate for future tasks where the correlation may not hold. Would require revalidating Gate 0 per-task.
- **DoG composition injection (`CompositionInjectionHook`)** — parallel adversarial-feedback mechanism. Deliberately disabled for v3 to keep cell occupancy reflecting evolutionary dynamics, not synthetic (D∘G) injections. Revisit after v3 reveals baseline 2D archive dynamics without composition confounders.
- **Cell-targeted mutation prompting** (Rainbow Teaming §3.4) — independent hypothesis; would confound v3's 2D BD validation. Defer.
- **"Attempted" vs "beaten" coverage** (DRQ failed-attack insight) — no clean 2D home; could be a third axis in v5.
- **Full Pareto / DECA coevolution** — multi-week effort per REDESIGN.md.
- **Learned BDs (AURORA/TAXONS)** — eval cost prohibits.
- **CVT-MAP-Elites** — keep as fallback if 2D grid aspect ratio turns out awkward.

## 13. Log-Based Verification Contract (HARD GATE — every success/failure criterion is reduced from smoke-run logs)

End-to-end tests can obfuscate data flow (monkey-patching, fixture leakage, spy-object drift). Log-based reconstruction does not: the log is what the production process actually emitted. v3 treats the smoke-run log as the single source of truth for verification. Any criterion in §1.5, §3.5, §4, §6, §8.3 that cannot be reduced to a grep/jq predicate on the log is not a v3 criterion.

### 13.1 The 10 canonical log events

Every run emits these events with stable prefixes and structured JSON payloads (see §9.2 for the emission sites):

| Event | Payload keys | Emitted per |
|---|---|---|
| `[HOF_FETCH]` | `program_id, gen, side, selection_key, k, opponent_ids` | each program evaluation |
| `[HOF_ROTATE]` | `side, prev_ids, new_ids, added, removed, gen` | each HoF change detected in `FetchOpponentIdsStage` |
| `[CELL_PICK]` | `side, k_requested, picks:[{cell, id, fitness}], fallback_used, n_populated_cells` | each `CellStratifiedRedisOpponentArchiveProvider.get_top_k` call |
| `[CACHE_HIT]` / `[CACHE_MISS]` | `stage, program_id, content_hash, cache_on_ids` | each `LineageStage`/`InsightsStage`/`SharedBenchmarkLineageStage` entry |
| `[LINEAGE_TREND]` | `program_id, parent_id, n_shared, trend, skipped_reason` | each D lineage computation |
| `[LINEAGE_TREND_G]` | `program_id, parent_id, metric, delta` | each G lineage computation (G uses `actual_fitness`) |
| `[TRACKER_WRITE]` | `gen, pairs_count, d_wins_added, g_resisted_added, d_faced_added` | each `record_batch` call |
| `[METRIC_EMIT]` | `side, program_id, gen, fitness, actual_fitness, wins, n_opponents` | each program's final metrics dict |
| `[GRADIENT_INJECT]` | `program_id, injected_d_id, delta, skipped_reason` | each `GradientInPromptStage.compute` call |
| `[ARCHIVE_MOVE]` | `program_id, cell, fitness_key, fitness, action, displaced_id` | each archive insertion/rejection |
| `[PROMPT_META]` | `program_id, side, metrics_shown, metrics_hidden` | each mutation-prompt composition |

### 13.2 Reduction of each criterion to a log predicate

Each row is a grep/jq predicate sufficient to pass/fail the criterion without invoking any test.

| Criterion (from §) | Log predicate | Pass condition |
|---|---|---|
| §1.5 Primary DV — max G `actual_fitness` at gen 50 | `grep '\[METRIC_EMIT\]' \| jq 'select(.side=="g" and .gen==50) \| .actual_fitness' \| max` | reported per-run; arm means computed offline |
| §3.5 P1 — G prompts hide fitness/wins | `grep '\[PROMPT_META\]' \| jq 'select(.side=="g") \| .metrics_hidden'` | MUST include `fitness` AND `wins` for ALL g-side entries; `metrics_shown` MUST include `actual_fitness` |
| §3.5 P2 — D lineage uses shared-benchmark | `grep '\[LINEAGE_TREND\]' \| jq 'select(.trend!=null) \| .n_shared'` | `n_shared >= 2` for every non-null trend; `skipped_reason` ∈ {`no_parent`, `insufficient_shared`} otherwise |
| §4 Selector routing — cell-internal on `fitness` | `grep '\[ARCHIVE_MOVE\]' \| jq 'select(.action=="evict") \| .fitness_key'` | MUST be `"fitness"` for every evict (both sides) |
| §4 Selector routing — elite/migrant external key | gen-0 config dump + first `[ARCHIVE_MOVE]` with `action=add`: `fitness_key` matches config | pop_a: external slots ranked by `actual_fitness`; pop_b: by `wins` |
| §4.1 CellStratified determinism | diff `[CELL_PICK]` payloads across two fetches at same gen (when archive unchanged) | byte-identical `picks` list |
| §6 Cache invalidation on HoF rotation | temporal predicate: for program X, if `[HOF_ROTATE]` fires between two consecutive `[CACHE_*]` events for X, the second MUST be `[CACHE_MISS]` | 100% compliance |
| §8.3 Asymmetric fitness_key | `grep '\[HOF_FETCH\]' \| jq '{side, selection_key}' \| sort -u` | exactly two entries: `(pop_a, fitness)` and `(pop_b, actual_fitness)` |
| §6.2 GradientInPromptStage — no global fallback | `grep '\[GRADIENT_INJECT\]' \| jq '.skipped_reason' \| sort -u` | set MUST be subset of {`null`, `"no_per_g_entry"`, `"tracker_empty"`} — never `"global_fallback"` |
| Tracker inverted-index consistency | `grep '\[TRACKER_WRITE\]' \| jq '.d_wins_added + .g_resisted_added + .d_faced_added'` per gen; cross-check with `redis-cli SCARD` at gen end | sum matches SCARD deltas |
| Archive occupancy > 10% at gen 50 | count distinct `cell` values in `[ARCHIVE_MOVE]` action=add within gen 50 window | ≥ 23 (for a 225-cell archive) |
| Cell-collision rejection rate drops | `grep '\[ARCHIVE_MOVE\]' \| jq '.action' \| grep -c reject / total` | treatment < 0.30 (baseline v2: 0.55-0.79) |

### 13.3 Flow reconstruction test (the smoke-run deliverable)

After the smoke run completes, running the following reduces the entire adversarial co-evolution flow from the log and asserts it matches design:

```bash
# gigaevo experiment log-audit heilbron/k5-budget-v3 --smoke
# (NEW tool; spec below)
```

Minimum viable implementation: a Python script `tools/experiment/log_audit.py` that:
1. Tails the smoke-run log file.
2. Parses each `[EVENT]` line into a structured record.
3. For each criterion in §13.2, runs its predicate and emits PASS/FAIL with the offending lines.
4. Outputs a Markdown report: `experiments/heilbron/k5-budget-v3/LOG_AUDIT.md`.
5. Exits non-zero if any criterion fails.

This is the actual smoke-test acceptance gate (replaces the smoke-test assertion block in §Phase F).

### 13.4 Non-negotiable logging principles

- Every log event used by §13.2 MUST appear with its exact bracketed prefix. Refactors that rename or shorten the prefix are a hard PR-rejection gate.
- Payload keys MUST be stable. Renaming a key = breaking the audit. If a new field is needed, add alongside the existing schema.
- Structured JSON is mandatory for every event listed here. Freeform f-strings are disallowed for audit-relevant emissions.
- Logging at DEBUG level is not acceptable for these events — they MUST be INFO or higher so they survive default log level filters.
- The log-audit script is version-locked: `LOG_AUDIT_SCHEMA_VERSION` constant asserts event schemas match those the audit expects; bumping schema requires bumping the audit.

## 14. Handoff Checklist

- [x] v2 closeout complete (INDEX.md row set to `complete`; commit `158bc4b9`).
- [x] Gate 0 Spearman analysis complete — `gate0_spearman.md` + `gate0_spearman.py`.
- [x] Gate 1 tracker-coverage viability verified — §3.2 distribution.
- [ ] §9.2 logging emissions implemented + `tools/experiment/log_audit.py` in place.
- [ ] Gate 2 smoke run artifact attached (LOG_AUDIT.md = PASS).
- [ ] `/experiment-implement heilbron k5-budget-v3` → scaffolds `experiments/heilbron/k5-budget-v3/` with 00–04 artifacts.
- [ ] Per-role configs land in `config/algorithm/`.
- [ ] `CellStratifiedRedisOpponentArchiveProvider` + tests + tracker inverted-index extension land in one PR.
- [ ] `gradient_prompt.py` amendments (per-G delta header + no-data-skip) + tests in the same PR.
- [ ] `SharedBenchmarkLineageStage` + `DGTrackerSharedOpponentResolver` + tests in the same PR.
- [ ] 8 pair-runs wired in `experiment.yaml` (4×k=3 DBs 1-4, 4×k=5 DBs 5-8).
- [ ] Pre-registration issue on project board before any launch.
