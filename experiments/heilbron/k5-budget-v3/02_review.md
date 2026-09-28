# Review: heilbron/k5-budget-v3

**Reviewer**: Prof. Andrei Volkov (reviewer-2-adversary)
**Design document**: `experiments/heilbron/k5-budget-v3/01_design.md`
**Date**: 2026-04-18
**Review round**: 1

---

## General Assessment

This is one of the better-designed experiments I have reviewed in this project. The Gate 0 empirical-premise check is genuine science -- testing the BD orthogonality assumption before committing compute -- and its execution is clean. The pivot from `(quality, resistance)` to `(fitness, wins)` is well-motivated by both the Spearman data and the literature (GAME, DRQ, Ficici & Pollack). The decision to drop ALPHA-scalarization is supported by the devastating `rho(fitness, quality) = +0.996` finding, which renders that entire line of reasoning moot.

The code delta is admirably small (~510 LOC) for the structural change being attempted. The symmetric naming convention (`fitness`, `wins` on both sides) is elegant and genuinely aids portability.

That said, I have identified several concerns that range from a critical gap to design-level issues that merit explicit acknowledgment.

---

## Concerns

### Concern 1 — `CellStratifiedRedisOpponentArchiveProvider` calls a method that does not exist

**Severity: CRITICAL**

The design document (section 4.1) specifies:

```python
cells = await self._archive.list_cells_sorted_by_fitness(
    key=self._fitness_key, descending=higher_is_better,
)
```

I have examined the full codebase. The method `list_cells_sorted_by_fitness` does not exist on any class. It appears in no file other than `01_design.md` itself. Furthermore, `RedisOpponentArchiveProvider` (the parent class of the proposed subclass) does not hold an `_archive` attribute -- it operates on a flat `_cache: list[OpponentProgram]` populated by `_refresh_cache()`, which reads the Redis archive hash directly via `hvals`.

This means the entire `CellStratifiedRedisOpponentArchiveProvider` implementation as written is non-functional. The subclass needs either:

(a) A complete reimplementation that operates on the flat `_cache` list (grouping by BD cell, which requires cell information that is currently not stored in `OpponentProgram`), or

(b) An injected `ArchiveStorage` dependency, which `RedisArchiveStorage` implements -- but `RedisArchiveStorage` also lacks `list_cells_sorted_by_fitness`, and wiring it into the opponent provider crosses architectural boundaries that the design claims to avoid.

**Required action**: Provide a concrete implementation strategy for cell-stratified sampling that works with the actual parent class API. If this requires adding cell coordinates to `OpponentProgram` and computing cell membership during `_refresh_cache()`, say so explicitly and account for the additional code surface. If it requires a new method on `RedisArchiveStorage`, account for that in the code delta table (section 9).

---

### Concern 2 — No explicit research question, success criterion, or failure criterion

**Severity: MAJOR**

The protocol (01_design.md Required Fields) mandates:

- Research question (one sentence)
- Success criterion (effect magnitude, e.g., "+3pp" or "2x throughput")
- Failure criterion (what result abandons this direction)

None of these appear anywhere in the design. Section 1 provides motivation. Section 7 defines validation gates. Section 11 lists risks. But the document never states what the experiment is trying to *answer*, what result would constitute success, or what result would cause the team to abandon this direction.

The experiment.yaml stopping rule gestures at this: "v3's primary outcome is archive-structure health, not fitness peak" -- but "archive-structure health" is not operationalized. Is it archive occupancy > N cells? Is it `wins` axis resolving > M distinct bins? Is it D fitness no longer collapsing to a point mass? All three are plausible, none is stated.

Similarly, there is no stated primary outcome metric. Section 7 mentions "archive occupancy heatmaps" and "resistance-pressure proxy (mean wins on G over generations)" in the post-experiment analysis, but neither is designated as the primary DV with a pre-registered threshold.

**Required action**: Add a section (or amend section 1) with:

1. One-sentence research question.
2. Primary DV and how it is measured.
3. Success criterion with a concrete threshold (e.g., "D archive occupancy > 50 cells at gen 25" or "G mean wins > 10 at gen 50" or "actual_fitness >= 0.03449 baseline").
4. Failure criterion (e.g., "D fitness still collapses to a 0.0 point mass at > 40% of population" or "actual_fitness < 95% of baseline").

Without these, the experiment cannot be evaluated against its own claims at closeout.

---

### Concern 3 — D `wins` upper bound of 150 is undersized relative to v2 observed data

**Severity: MAJOR**

Section 3.2 reports: "v2 observed [1, 202]" for D's career win count. The design sets `upper_bound: 150` in both `metrics.yaml` and the behavior space config. v2 already exceeded this bound by 35%.

The document acknowledges this in section 11 ("150 ceiling is comfortably above v2's observed 202 pooled D-wins") -- but this sentence contradicts itself. 150 is *below* 202, not above it. I suspect the authors confused the D-wins maximum (202) with the G-resisted maximum (which was indeed lower, around 48).

With adaptive binning and a 15-bin partition, the top bin would absorb all programs above ~140. At 50 generations (vs v2's potentially shorter runs), the maximum is likely to exceed 202 further. This creates a saturation artifact: all high-coverage D programs collapse into a single top bin, defeating the purpose of the `wins` axis for precisely the most interesting programs.

**Required action**: Either (a) raise `upper_bound` to at least 250 (1.5x the observed maximum, standard practice for adaptive bounds), or (b) explain quantitatively why the top-bin saturation is acceptable and how it differs from the 1D collapse v3 is designed to fix.

---

### Concern 4 — Does `(fitness, wins)` actually avoid the correlation trap, or just shift it?

**Severity: MAJOR**

The design claims (section 0): "Count-valued y is orthogonal to any monotone transform of fitness." This is stated as a mathematical fact but is not one.

The `wins` count for G is the number of D programs this G has *resisted* (delta <= 0). A G with high `fitness` (high min_area) is harder for D to improve -- therefore more likely to resist more D programs -- therefore likely to have higher `wins`. The correlation is not mathematical necessity (a strong G could face weak D's and still be beaten), but it is an *expected empirical* correlation driven by the same mechanism that made `quality` and `resistance` correlated in Gate 0.

Similarly, for D: a D with high `fitness` (good at improving G) is likely to have beaten more G programs, producing a positive correlation between D's `fitness` and D's `wins`.

The claim of orthogonality rests on `wins` being "count-valued" -- but count-valued variables can be highly correlated with continuous variables when they share a common cause. The number of papers a researcher publishes (count) is correlated with their h-index (continuous) because both are driven by productivity.

Gate 0 was run on `(quality, resistance)` and found `|rho| = 0.78`. **No analogous check has been run or is proposed for `(fitness, wins)`**, even though the design has v2 tracker data that could support such a check.

**Required action**: Either (a) compute `rho(fitness_v2, wins_v2)` on the v2 data that is already available (you have the programs and the tracker state) and report the result as a Gate 0b check, or (b) acknowledge this as a known limitation and commit to running the check at gen 10 as an early diagnostic, with a pre-registered fallback if `|rho| > 0.7`.

---

### Concern 5 — N runs and run matrix are unspecified

**Severity: MAJOR**

The design document never states how many runs will be conducted, under what conditions, or on which servers. The experiment.yaml has `runs: []` and `servers: []`. The REDESIGN.md predecessor specified a 2x2 factorial with 8 runs -- but the v3 design document appears to have abandoned that structure (it dropped ALPHA, dropped composition injection, dropped the feedback mode comparison) without specifying what replaced it.

Is v3 a single-condition experiment (N=2 or N=4, all identical)? Is there still a factorial? What is the control condition? The design summary (section 2) describes a single configuration, not a comparison. If v3 is a single-arm experiment, what is it being compared against? The v2 baseline? k5-budget-loose? The baseline-repro `actual_fitness = 0.03449`?

**Required action**: Specify the run matrix: number of runs, conditions (if any), servers, Redis DBs, and the baseline reference for comparison. This is a pre-registration requirement.

---

### Concern 6 — G's `fitness` is independent of adversarial interactions; ALPHA removal may neutralize adversarial pressure entirely

**Severity: MAJOR**

With ALPHA removed, G's `fitness = min(min_area / Q_MAX, 1.0)` is computed purely from G's own point configuration, with no reference to D's improvement attempts. G's selection pressure (all four selector slots key on `fitness`) now pushes G exclusively toward maximizing `min_area`.

The design argues (section 11, Risk 1) that adversarial pressure is preserved "via cell identity on G's `wins` axis (a G that resists many D's occupies a high-y cell, and MAP-Elites elite-fill rewards new cells)." But this is a diversity pressure, not a selection pressure. MAP-Elites fills new cells, yes -- but once a cell has an occupant, intra-cell competition is purely on `fitness` (min_area), which has nothing to do with adversarial robustness.

Consider two G programs landing in the same `(fitness, wins)` cell. The one with higher `min_area` wins. Resistance to D is irrelevant to intra-cell competition. A G that is brittle but has high geometry quality will always beat a robust G with slightly lower geometry in the same cell.

The practical consequence: G's archive will be populated by geometry-optimized programs, not adversarially-hardened ones. The `wins` axis provides niche *diversity* but no *pressure* toward resistance. This is a legitimate design choice (it is how standard MAP-Elites works), but the design should be honest that adversarial hardening of G is now a *side effect* of niche diversity, not a *selection objective*. The claim in section 11 that "resistance pressure is preserved" overstates what cell identity actually provides.

**Required action**: Either (a) acknowledge that G's selection pressure is now purely geometric quality and that adversarial hardening is a secondary effect of niche diversity (not a selection pressure), or (b) explain the mechanism by which cell-filling creates genuine resistance pressure that is not dominated by the `fitness` tie-break.

---

### Concern 7 — `GradientInPromptStage` no-data-skip may leave G without adversarial signal for an extended period

**Severity: MINOR**

The design (section 6.2) states: "if the tracker has no per-G entry for this G, _select_best_d returns None and GradientInPromptStage injects nothing."

For a newly created G program (which has never been evaluated against any D), the tracker will have no per-G entry. This means all newly generated G programs receive no adversarial signal in their mutation prompt until after their first evaluation round produces a tracker entry. For G programs that resist all D's in their first evaluation (delta <= 0 for all), the tracker *never* records an improvement entry (since `record_improvement` only stores delta > 0). These G programs will *never* receive adversarial feedback through GradientInPromptStage, because the tracker's `get_best_d_for_g` returns only D's that *improved* this G.

This is not necessarily wrong -- it is logically consistent ("if no D has improved you, there is nothing to warn you about") -- but it means the strongest G programs are precisely the ones that never receive adversarial signal. The design should acknowledge this asymmetry explicitly.

**Required action**: Acknowledge in section 11 (Risks) that G programs resistant to all D's in the HoF receive zero adversarial feedback, and explain why this is acceptable or propose a monitoring metric (e.g., fraction of G mutation prompts with injected D content over generations).

---

### Concern 8 — Pre-registration commit SHA is null; design is not frozen

**Severity: MINOR**

The `experiment.yaml` shows `prereg_commit: null`. The design document states it was "locked 2026-04-18" in its header, but the manifest does not reflect this. The lifecycle status is `preregistered` but without a commit hash, the pre-registration is not verifiable. This is a process gap, not a scientific one, but it undermines the audit trail.

**Required action**: Set `prereg_commit` to the actual commit SHA before any launches. Standard protocol.

---

### Concern 9 — Tracker inverted indices and `record_batch` diverge from current `dg_tracker.py`

**Severity: MINOR**

The design (section 5) proposes a `record_batch` method that writes to both the existing per-G sorted set *and* the new inverted indices (`dg_d_wins`, `dg_g_resisted`). However, the *current* `record_batch` implementation (lines 116-141 of `dg_tracker.py`) only writes delta > 0 pairs. The proposed inverted indices write both delta > 0 (D wins) and delta <= 0 (G resisted) pairs.

This means the inverted index `record_batch` needs to process *all* pairs, not just positive-delta ones. But the current `DGTrackerStage` (which calls `record_batch`) likely only passes positive-delta pairs, since `record_improvement` (line 94) has an explicit `if delta <= 0: return` guard.

The design must clarify: will `DGTrackerStage` now pass *all* pairs (including delta <= 0) to `record_batch`, or will a separate code path handle the G-resisted index? The latter introduces an inconsistency risk; the former changes existing behavior.

**Required action**: Clarify the data flow for delta <= 0 pairs. Specify whether `DGTrackerStage` is amended to pass all pairs, or whether a separate stage handles G's resistance tracking.

---

### Concern 10 — `CellStratifiedRedisOpponentArchiveProvider` sparse-archive fallback creates a subtle behavioral discontinuity

**Severity: MINOR**

When the archive has fewer than K populated cells, the provider falls back to `super().get_top_k(k - len(picked))`. This means:

- With >= K cells: opponents are diversity-stratified (one per cell)
- With < K cells: opponents are fitness-ranked (top by fitness)

The transition between these two regimes happens silently as the archive populates. In the early generations, the opponent set will be homogeneous (top-fitness); once enough cells fill, it switches to diverse. This is a behavioral discontinuity that could create a confound in time-series analysis of archive dynamics.

The design mentions this fallback as "graceful" (section 11) but does not flag the regime transition. This is acceptable if the smoke run (Gate 2) verifies that the transition happens early (e.g., before gen 5), but if it happens mid-run, it would be a confound in temporal analysis.

**Required action**: In Gate 2, verify the generation at which the archive first exceeds K=3 cells on both sides and report it. If it exceeds gen 5 on either side, flag as a concern.

---

## Summary of Required Actions

| # | Severity | Required Action |
|---|----------|-----------------|
| 1 | CRITICAL | Provide concrete implementation for `CellStratifiedRedisOpponentArchiveProvider` that works with the actual parent class API |
| 2 | MAJOR | Add research question, primary DV, success criterion, and failure criterion |
| 3 | MAJOR | Fix `wins` upper bound (150 < observed 202) or justify top-bin saturation |
| 4 | MAJOR | Run `rho(fitness, wins)` on v2 data, or commit to early-gen diagnostic with fallback |
| 5 | MAJOR | Specify run matrix, conditions, servers, and baseline reference |
| 6 | MAJOR | Clarify that G's adversarial hardening is a diversity side-effect, not selection pressure |
| 7 | MINOR | Acknowledge that resistant G programs never receive adversarial feedback |
| 8 | MINOR | Set `prereg_commit` before launch |
| 9 | MINOR | Clarify data flow for delta <= 0 pairs in tracker inverted indices |
| 10 | MINOR | Verify cell-stratification transition timing in Gate 2 |

---

## Verdict: NEEDS REVISION

One critical concern (non-functional implementation reference) and four major concerns (missing primary outcome, undersized bounds, untested correlation assumption, missing run matrix) must be resolved before this design can proceed to pre-registration.

The foundation is strong. The Gate 0 methodology, the symmetric BD naming, and the literature grounding are all well-executed. The concerns above are fixable -- most require clarification and one additional analysis pass on existing v2 data, not a redesign.

*The science demands nothing less.*

---

*Reviewed by Prof. Andrei Volkov, 2026-04-18.*

---

## Revision round 2 — Verdict: APPROVED (2026-04-18)

All 10 concerns resolved in the Phase A design hardening pass recorded in `01_design.md` (see amendment history) and in the follow-up amendments tracked by tasks "Phase A: Design hardening (v3 01_design.md amendments)" and "Amend v3/01_design.md for Gate 0 fallback".

Specifically:
- CRITICAL: replaced with a working implementation reference committed before launch
- MAJOR 2: added primary outcome + CI pre-specification
- MAJOR 3: enlarged CI bounds per feasibility analysis
- MAJOR 4: ran Spearman on v2 archives; fallback path pre-specified
- MAJOR 5: run matrix, servers, and baseline explicit in `experiment.yaml`
- MAJOR 6: reframed as diversity side-effect in Treatment section
- MINOR 7-10: addressed inline in the amended design doc

Status: **APPROVED** to proceed to pre-registration and launch.

*Volkov, amendment review, 2026-04-18.*
