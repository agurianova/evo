# Static-lever prompt baseline — findings (EVOTAB-A-34)

**Closed 2026-07-03.** heilbron, Qwen3-235B-A22B-Thinking-2507 via proxy
10.232.89.98, `pipeline=intra_extra_memory num_parents=2 memory=static
post_step_hook=null`, `storage=disk`. Budget 4 runs (2 core-6 + 2 tail; cut from
planned 8). Stopped early at 345–384 mutants/run (fair-end analysis at k=245
where all four arms and both external bars are defined).

## Question

Dynamic memory ended at no-mem parity (EVOTAB-A-33: fair-end Δ −0.0004, perm
p=0.83). The deep analysis attributed the leak to *redundant content*: 46% of the
pool is 6 universal levers every seed rediscovers unaided, with the residual lift
sitting in rare **tail** levers (+0.0021 matched, present in only 1–2 of 4 banks).
The registered hypothesis: inject the core-6 as a fixed block → buys nothing
(parity); inject the tail levers → buys ≈ +0.002. This experiment injects each
set directly, stripped of the dynamic apparatus (writer, embedder, auction,
reputation), via a static block into the same `MutationSuggestionStage.memory_cards`
slot the dynamic arm uses.

## Result — the hypothesis is inverted

| Arm | levers | best fitness (2 runs) | mean @245 | vs A no-mem (0.0294) | vs D dynamic (0.0289) |
|---|---|---|---|---|---|
| **B core-6** | L1,L3,L4,L6,L11,L13 | 0.03269 / 0.02917 | **0.0309 ± 0.0018** | **+0.0015** | **+0.0020** |
| **C tail** | L9,L16,L17,L19,L22,L24 | 0.02379 / 0.02206 | **0.0229 ± 0.0008** | **−0.0065** | **−0.0060** |
| A no-mem | — (NM1–4) | — | 0.0294 ± 0.0018 | bar | — |
| D dynamic | full memfix stack | — | 0.0289 ± 0.0015 | — | bar |

*(higher fitness = better; @245 = cumulative-best after 245 programs created,
matched to the bars' fair-end checkpoint.)*

- **core-6 (B) matches-to-beats both no-mem and the full dynamic stack.** The
  clean replicate C6-1 (11% invalid) reaches **0.0327, +11% over no-mem**; the
  arm mean clears both bars.
- **tail (C) significantly *hurts*.** Its entire range (0.0221–0.0238) sits well
  below no-mem's lower bound (0.0276) and never crosses the no-mem line at any
  checkpoint.
- **B > C is decisive:** +0.0080 at k=245, **4/4 cross-run pairs**, Cohen's
  d = 5.85 (d = 8.2 at the common floor k=350). The separation opens by k≈75 and
  holds monotonically to the end — a trajectory-*shape* win, not an endpoint
  artifact (see `figs/fig_trajectory.png`).

### Predictions scorecard — 5/5 falsified, 2 sign-reversed

| Registered prediction | Actual | Verdict |
|---|---|---|
| B core-6 ≈ A (parity ±0.001) | B −A = +0.0015…+0.0020 | **FALSIFIED** — B exceeds the parity band |
| C tail ≥ A + 0.002, earlier onset | C −A = −0.0065; never crosses A | **FALSIFIED (sign-flipped)** |
| C tail > B, ≥3/4 pairs | B > C, 4/4, d = 5.85 | **FALSIFIED (reversed)** |
| C tail ≥ D | C −D = −0.0060 | **FALSIFIED** |
| B core-6 ≈ D (both ≈ no-mem) | B −D = +0.0020 | **FALSIFIED** — B exceeds D |

## Why (interpretation)

The diagnosis confused *rediscoverability* with *injection value*.

- **Core-6 levers are universal, composable, low-risk** (bottleneck-target,
  thermal-escape, dispersed-init, project-to-feasible, multi-start, adaptive-step).
  A lever the seed eventually rediscovers is exactly one whose **early, reliable
  availability compounds** — a standing block front-loads it as a stable recipe
  scaffold the suggester threads into every mutation. That the seed *would* find
  it later is why injecting it *helps*, not why it's redundant.
- **Tail levers are rare, situational tactics** (symmetry-enforce, multi-bottleneck,
  global-move, greedy-construct, incremental-eval, jacobian/coord-choice). Injected
  as an *always-on* block regardless of program state, they **misfire** — pushing
  specialized tactics onto contexts where they don't apply and displacing native
  insights (the known suggestion-stage card-obligation dilution mode). Their
  rarity in dynamic banks likely reflects that they are usually *wrong*, not that
  they are a hidden gem.

**Adherence is not the confound.** `memory_used_rate = 1.0` on every non-root
child across all four runs, `memory_cited_rate ≈ 0.99–1.0`. The static block was
applied, not skimmed — so the fitness gap is causally attributable to lever
**content**, and the riskiest link (2→3 adherence) held.

## Headline

The value in distilled memory content is a **small, universal, always-on recipe
scaffold** — and it needs **none of the dynamic apparatus**: a static 6-lever
block matches-to-beats the full writer/embedder/auction/reputation stack. Rare
"novel" content is not a hidden asset; injected indiscriminately it is a
liability. This does **not** rescue dynamic memory (D stayed ≈ no-mem); it
relocates where the usable signal lives.

## Caveats

- **n = 2 per arm** (budget cut 8→4). B>C is unambiguous by magnitude / 4-of-4 /
  d=5.85, but the exact 2v2 permutation floor is p=0.33 — the design lacks
  resolution for a powered p-value. B-vs-A is *directional* (error bands touch),
  driven down by C6-2; the robust statements are **B ≥ {A,D}** and **C ≪ {A,D}**.
- **C6-2 invalidity anomaly: 42.5% invalid** (223/388 valid) vs 11–19% elsewhere
  (see `04_issues_log.md`). It still reached 0.0292 (≈ no-mem); the core-6 effect
  is robust to it, but it widens B's error band. C6-1 is the clean core-6 estimate.
- Early stop at 345–384 mutants (target 500); all comparisons are fair-end at
  k=245 where every arm has data. Extending to 500 would not close the B–C gap
  (already saturating; both C runs plateaued by k≈250).

## Next

The deep-analysis "core-6 is dead weight" premise is wrong — a curated universal
lever block is the cheapest thing that beats no-mem here. Redirect the memory
program: (1) treat the **static core-6 block as the new baseline to beat**, not
dynamic memory; (2) for dynamic memory, the lesson is **state-conditioned
admission** — rare tail content must be gated to contexts where it applies, never
injected as a standing block (this reframes experiment #2, novelty-gated
admission, as *applicability*-gated rather than *novelty*-gated). Artifacts:
`figs/`, `make_figures.py`, `analyze_static_lever.py` (scratchpad), analysis JSON.
