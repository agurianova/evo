# Post-refactor `memory=full` vs prior memory runs — compute-matched

**Question:** does the rebuilt dynamic-memory stack (`gigaevo.memory.{read,write,storage}`,
PR #294) match the pre-refactor memory runs, at **equal compute**?

**Why this doc supersedes the earlier framing.** The first pass compared the rebuild's
*terminal* (k=500, ~0.033) against pre-refactor memory's *final* (~0.029). That is unfair:
the pre-refactor **memory** runs (memfix) were SIGKILL'd at 220–261 programs — they never ran
500 steps, so they had no chance to climb further. The only honest comparison is
cumulative-best at a program count **every** run reached.

## Method (identical harness, all runs)

- **Axis = program count** (candidate programs evaluated, sorted by `atomic_counter`).
  This is the number of mutation+eval steps = compute spent, and it is **invariant across
  the refactor**. (The `iteration` field's meaning drifted — old runs have `iteration` >
  progcount, the rebuild is dense `iteration≈progcount` — so iteration-matching is unsafe
  across the refactor. Program-count also reproduces the EVOTAB-A-34 static methodology.)
- **Metric:** cumulative best of strictly-valid fitness (`is_valid==1`, finite, > −1 to drop
  the −1000 invalid sentinel) among the first *k* stored programs. Higher = better
  (heilbron min-triangle-area). Invalid attempts **count as steps** (they cost an LLM call),
  so an arm that burns more invalids is correctly penalised.
- **Validation:** the harness reproduces EVOTAB-A-34 exactly on this axis — static core-6
  0.0309±0.0018 (C6-1 0.03269 / C6-2 0.02917), static tail 0.0229±0.0008. Confirms method.
- Script: `scratchpad/iter_compare_all.py`. All storages survive on disk (re-runnable).

## Runs compared (all heilbron, Qwen3-235B-A22B-Thinking-2507 mutator, num_parents=2, storage=disk)

| campaign | arm | embedder | store | novelty gate | progs (per seed) |
|---|---|---|---|---|---|
| memfix (PRE) | dynamic `memory=full` | MiniLM-L6 | shared_memory/GAM | no | 256/261/237/220 |
| nomem (PRE) | `memory=none` | — | — | — | 284/226/247/264 |
| static core-6 (PRE) | `memory=static` (6 universal levers) | — | — | — | 389/388 |
| static tail (PRE) | `memory=static` (6 rare levers) | — | — | — | 350/355 |
| **rebuild (POST)** | dynamic `memory=full` | **arctic-embed-m-v1.5** | **LocalMemoryStore** | **yes** | 505/505 |

## Fair comparison — cumulative-best by program count (arm mean ± std)

Common floor = **k=220** (memfix S4). At k=220 every run has real data (no caps). k=245 is
shown but memfix S3/S4 are capped there (they ended at 237/220).

| arm | k=50 | k=100 | k=150 | k=200 | **k=220 (fair-end)** | k=245* |
|---|---|---|---|---|---|---|
| static core-6 (PRE) | 0.0185 | 0.0240 | 0.0273 | 0.0286 | **0.0302 ± 0.0010** | 0.0309 |
| no-mem (PRE) | 0.0151 | 0.0242 | 0.0277 | 0.0288 | **0.0297 ± 0.0019** | 0.0307* |
| memfix dynamic `mem=full` (PRE) | 0.0148 | 0.0256 | 0.0270 | 0.0276 | **0.0284 ± 0.0024** | 0.0293* |
| static **tail** — proven-detrimental (PRE) | 0.0180 | 0.0204 | 0.0211 | 0.0224 | **0.0224 ± 0.0004** | 0.0229 |
| **rebuild `mem=full`+novelty (POST)** | 0.0139 | 0.0196 | 0.0220 | 0.0233 | **0.0235 ± 0.0001** | 0.0247 |

\* capped: ≥1 run ended before k=245.

## Verdict

1. **At equal compute, the post-refactor `memory=full` is the slowest-climbing arm across the
   ENTIRE shared trajectory (k=50 → 220), not just at the end.** This is a shape result, not a
   cherry-picked endpoint.
2. **It does NOT reproduce the pre-refactor dynamic memory it was meant to match.** At the
   fair-end k=220 it sits **~0.0049 below** the old dynamic `memory=full` (memfix 0.0284),
   **~0.0062 below** no-mem (0.0297), and **~0.0067 below** the best arm (static core-6 0.0302).
3. **It lands in the detrimental regime.** Its trajectory tracks the static-**tail** arm — the
   block EVOTAB-A-34 proved *hurts* (rare levers injected off-context misfire) — not the
   no-mem / dynamic-parity pack the pre-refactor memory reached.
4. **Terminal (k=500) is not comparable to any prior memory run** — none ran past ~260 steps.
   Whether the rebuild's later climb (R1→0.0335, R2→0.0330 by k=500) would catch up is exactly
   what the **same-recipe no-mem control** (running now, k=500) will settle.

## Leading mechanistic hypothesis

The rebuild adds a **novelty-admission gate** (new; absent from all pre-refactor runs) that by
design suppresses common core-6-type cards and admits *novel* ones. EVOTAB-A-34 showed the rare
"tail" levers are precisely the detrimental ones. So the novelty gate may be steering the
dynamic bank into the tail-lever regime — which would explain why the rebuild underperforms even
the OLD dynamic stack (no gate → no-mem parity). Testable: the running no-mem control isolates
mutator/recipe; a gate-off rebuild run would isolate the gate.

## Confounds (documented, not dismissed)

Identical across all runs: mutator `Qwen3-235B-A22B-Thinking-2507`, memory-LLM `qwen_instruct`,
problem heilbron, `num_parents=2`, `max_mutants=500`. Differences between the POST rebuild and
the PRE dynamic memory: **embedder** (MiniLM-L6 → arctic-embed-m-v1.5), **store architecture**
(shared_memory/GAM → LocalMemoryStore/ResearchShortlister), **novelty gate** (off → on). Any of
the three could carry the regression; the gate is the leading suspect (see above). n=2 (POST) /
n=4 (memfix, no-mem) / n=2 (static) — effect sizes, not powered p.
