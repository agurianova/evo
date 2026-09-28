# Are the banked ideas too trivial? Does the mutator already know them? (2026-07-03)

**Question (user):** *"arent ideas too trivial? does qwen already know them? … Maybe we need to
sharpen the librarian so if the idea is trivial / known — do not add it."*

**Answer, in one line:** Yes. On the R1/R2 `memory=full` heilbron banks, **~24 of 27 insight cards are
prior-redundant** — the Qwen mutator reproduces them *cold* from the task description alone, including
the single lever that looked non-trivial (bottleneck repair). The bank adds ~no information the model
lacks, and it *reinforces* a shared wrong bias (anti-boundary) instead of correcting it. This is the
mechanism behind the A≈D fitness parity: memory that only restates the model's prior can't move fitness.

## Method (three LLM probes, blind where it matters)

1. **Cold prior baseline — Claude, blind.** Given ONLY `problems/heilbron/task_description.txt` (no cards),
   list the heuristics a strong optimizer already knows. → 20 STANDARD + 7 genuinely-non-obvious levers.
   File: `scratchpad/cold_prior_baseline.md`.
2. **Ground-truth probe — the actual Qwen mutator, cold.** One `Qwen/Qwen3-235B-A22B-Instruct-2507`
   call via the LiteLLM proxy, task description only, "list your go-to heuristics before coding."
   → 20 named techniques. File: `scratchpad/qwen_cold_probe_output.md`. **This is the literal
   "does Qwen know them" test** — spontaneous generation, no card injection.
3. **Per-card triviality rubric — Claude judge.** Scores every card on triviality / task-specificity /
   prior-known and classes it REDUNDANT vs CARRIES-SIGNAL + a WRONG flag. File: `scratchpad/triviality_rubric.md`.

## The decisive result: the mutator generates the banked ideas unprompted

Qwen's cold list (task description only, **never shown a single card**) already contains:

| Qwen cold item | Banked card(s) it pre-empts |
|---|---|
| #4 SA w/ geometric cooling, #5 adaptive step-size | R1-0, R1-3, R1-6, R2-0, R2-13 (5× "SA temperature schedule") |
| #1 lattice init, #10 barycentric k-means++, #14 barycentric parameterization | R1-1, R2-6, R2-8, R2-14 |
| #15 local jitter, accept only if min-area improves | R1-4, R1-7, R2-3, R2-4 (perturb + greedy accept) |
| #7 barrier / #15 feasibility check / #14 intrinsic coords | R1-5, R1-11, R2-1, R2-5, R2-7 (containment / clamp) |
| #18 near-collinear cross-product monitor + nudge | R1-8, R2-10, R2-11 (degeneracy guards) |
| #2 farthest-point (min-distance) sampling | R1-9 (min pairwise distance) |
| **#9 worst-triangle-driven gradient ascent**, **#12 remove & reinsert the smallest-triangle point** | **R1-10, R2-12 (bottleneck repair)** |
| #16 multi-start, #13 exploit symmetry | R2-2 (extremal/vertex init), general |

The line that matters is the **bottleneck-repair** row. Across the prior audits and both cold baselines,
"perturb only the current minimum-area triplet" (R1-10 / R2-12) was the *one* card that read as
non-obvious, task-specific signal. **Qwen emits it cold, twice** (#9 and #12). If the mutator already
reaches for the best idea in the bank without being handed it, the bank is not teaching the mutator anything.

## The boundary paradox — the bank is worse than empty on the one lever that matters

The genuinely non-obvious Heilbronn lever (from the blind Claude baseline, item NON-OBVIOUS #2) is:
**the optimum pushes points ONTO the boundary — occupy the 3 corners + edge midpoints.** Standard spread
heuristics *avoid* boundaries; this is the counter-intuitive, high-value insight.

- **Neither the bank nor Qwen has it.** Qwen's cold list actively goes the *wrong* way — item #6
  "soft penalties for proximity to boundaries." R2-2 gestures at "boundary-anchored seeds (vertices)"
  but only as *initialization headroom*, not as the target geometry.
- **Several cards encode the WRONG (anti-boundary) bias** and thus *reinforce* the model's misconception:
  R1-1 ("edge effects that undermine minimum area"), R1-4 ("boundary-favoring axes … suppress minimum
  triangle area"), R1-11 (boundary "collapse"), and the "boundary proximity ⇒ take smaller steps"
  framing in R2-1/R2-3/R2-5/R2-7. The bank is even **internally contradictory**: R2-2 wants points on
  the boundary, R1-1/R1-4 warn against it.

So on the single lever where memory *could* have added value, the bank instead parrots — and amplifies —
the mutator's own error. This is a stronger indictment than mere redundancy.

## Per-card verdict — two lenses, and why they disagree

**Lens 1 — triviality rubric (task-specificity axis).** The blind judge scored each card on
triviality / task-specificity / prior-known and classed it:
- **REDUNDANT: 19** (pure metaheuristic boilerplate the mutator emits cold — 5× SA schedules,
  keep-best, greedy hill-climb, clamp/containment, barycentric-construction restated 3×).
- **CARRIES-SIGNAL: 8** — R1-10, R1-11, R2-1, R2-2, R2-6, R2-8, R2-9, R2-12 (3 strong: R1-10, R2-9,
  R2-12; 4 moderate geometry-detail cards; 1 signal-but-harmful). Collapsing the R1-10≡R2-12 duplicate
  and dropping the wrong card ⇒ **~6–7 distinct useful ideas across 27 cards**.
- **WRONG: 1** — R1-11 (anti-boundary clamp; keeps points off the edges the optimum needs).

**Lens 2 — priorness (Qwen ground-truth probe).** This is the lens the rubric can't see, and it is
*more* damning: **the rubric's strongest signal cards are exactly what Qwen produces cold.** R1-10/R2-12
"perturb the current smallest triangle" ⇒ Qwen #9 + #12. R2-9 "select on area not distance" ⇒ Qwen holds
*both* the distance proxy (#2) and the area-aware move (#9), so only the framing is sharper. So of the
rubric's 8 "signal" cards, the 3 strong ones are **prior-known** — task-specific, yes, but not
information the mutator lacks. What survives *both* lenses (task-specific AND above the model's prior) is
only the thin band of geometry-implementation details — R2-8 (width-aware rows), R2-6 (hex stagger),
R2-1 (√k step scaling) — none of which is high-value, and the one high-value non-obvious lever
(boundary occupancy) is **absent from the bank entirely**.

**Bottom line:** rubric says 70% redundant; the priorness probe pushes the *effective* redundancy toward
~85–90%, because "names a triangle" (spec=5) is not the same as "the mutator wouldn't do it anyway."
Distinct ideas behind all 27 cards ≈ 8, and **every headline idea is in the mutator's cold prior.**

## Why this matters — it is the A≈D parity mechanism

The live R1/R2 runs exist to test whether the rebuilt `memory=full` stack beats no-mem (bar A, 0.0294) /
dynamic-memfix (bar D, 0.0289). Prior closeouts already found A≈D parity (memory buys no fitness).
This analysis supplies the *why*: **a card only moves fitness if it carries a lever the mutator would not
otherwise apply.** At 89% prior-redundancy — with the best card prior-known and the one true insight
absent — the expected fitness lift is ~0 by construction. Card *quality*, not card plumbing (dedup,
reputation, retrieval), is the binding constraint.

## Recommendation — sharpen the librarian with a novelty-vs-prior admission gate (design only; needs user pull)

The user's instinct is right: **reject trivial/known ideas at write time.** Concretely, add an LLM
admission judge in the librarian that asks, per candidate card, *"would a strong code model already do
this for this task, unprompted?"* and admits only cards that clear a novelty bar. Shape (not yet built):

- **Seam, not a branch.** New `AdmissionJudge` Protocol consumed by `CardAdmissionGate`; default
  `NullAdmissionJudge` (admit-all, current behavior). An `LLMPriorNoveltyJudge` implementation is wired
  in the `memory=full` arm only. (Per *new-impl-behind-seams* + *minimum-viable-design*.)
- **LLM rule, not a Python predicate.** The judge is a structured-output LLM call (keep/reject + reason),
  given the card + task summary — **no hardcoded "is this SA?" detectors** (per *llm-rules-over-hardcoded*).
  Prompt lives under `gigaevo/prompts/admission_novelty/` with a `{task_description}` placeholder
  (per *reuse-conventions*).
- **Grounding the "prior" cheaply.** Two options for what the judge compares against: (a) a static
  rubric ("is this textbook metaheuristic boilerplate that applies to any optimizer?"), or (b) a
  per-task cached *cold-prior list* generated once by the mutator model (exactly probe #2 above) and
  passed to the judge as the "already-known" set. (b) is sharper and directly operationalizes
  "does the mutator already know it," at one extra call per task (cached).
- **Bounded + fail-open.** Timeout/error → admit (never block the write path), mirroring the
  consolidation graceful-degrade we just shipped.

**Tradeoff to weigh before building:**
1. *It shrinks the bank hard but doesn't add signal.* At this redundancy the gate strips ~70–90% of
   cards (net-positive for distractor load — fewer neutral cards diluting retrieval / burning mutator
   context, the novelty-collapse finding) but it does **not** manufacture the missing boundary-occupancy
   insight. A smaller bank of prior-known cards is still prior-known.
2. *Novelty ≠ correctness.* A pure "is this obvious?" gate would **pass R1-11** — it is genuinely
   non-obvious (triv=2) yet **wrong** (anti-boundary). Filtering on novelty removes the boilerplate but
   lets a non-obvious-but-harmful card through, so the gate needs a *second* axis — a correctness /
   anti-boundary check on cards that clear the novelty bar — not novelty alone.
3. *The higher-leverage fix is upstream authoring.* Get the librarian to author cards that encode what
   the mutator got WRONG (mine the gap between the model's anti-boundary prior and the boundary-occupancy
   optimum) — contrastive/error-driven cards, not faithful summaries of what already worked. The gate
   removes noise; error-driven authoring adds the signal the bank is currently missing.

Recommend surfacing all three to the user and letting them choose scope — the gate is the cheap win,
error-driven authoring is the real one.

## Artifacts
- `scratchpad/cold_prior_baseline.md` — blind Claude prior (20 standard + 7 non-obvious).
- `scratchpad/qwen_cold_probe_output.md` — **Qwen mutator cold list** (20 techniques) + `qwen_cold_probe.py`.
- `scratchpad/triviality_rubric.md` — per-card rubric judge.
- `scratchpad/{all_insight_cards.json, R1_insight_cards.txt, R2_insight_cards.txt}` — the 27 cards.
