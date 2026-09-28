# Heilbron-Adversarial Sandbox — Infrastructure Explained Like You're Five

**Audience:** anyone who needs to understand what the sandbox is doing without reading code first.
**Style:** ASCII diagrams. Plain words. Every parameter named. Every code file cited.
**Lens:** Red Queen / co-evolution. We are running an arms race in a Petri dish.

---

## 1. The Red Queen, In One Picture

> *"It takes all the running you can do to keep in the same place."* — Lewis Carroll, *Through the Looking-Glass*

Van Valen (1973) repurposed this for biology: a species' fitness against its environment can be flat **even when it is improving fast**, because every other species is also improving. The classic picture:

```
            FITNESS LANDSCAPE (with co-evolving opponent)

  fitness  │        opponent gets stronger
   (your   │       ↗                 ↗
   score   │     /     YOU IMPROVE      \
   vs      │   /  ↗   but stay flat     ↗
   them)   │ /                            \
           │                                ↗
           │_________________________________________→ time
                  "running just to stand still"
```

In a single-population evolutionary algorithm there is **no Red Queen** — your fitness function is fixed and improvements compound. In our setup the fitness function for G is *D's reaction to G*, and the fitness function for D is *G's behavior against D*. Both move. That is what we are testing.

---

## 2. The Two Players

We are evolving point configurations for the Heilbron triangle problem (place 11 points in the unit triangle to maximize the smallest sub-triangle). Two populations:

```
  ┌──────────────────────────────┐         ┌──────────────────────────────┐
  │  G  (Constructor / Pop A)    │         │  D  (Improver / Pop B)       │
  │                              │         │                              │
  │  Outputs: list[(11,2) pts]   │         │  Outputs: improve(pts)→pts'  │
  │  "Generate hard configs"     │         │  "Take any config, push min  │
  │                              │         │   triangle area higher"      │
  │  Wants: high min_area AND    │         │  Wants: large positive Δ     │
  │         resistance to D      │         │         on G's configs       │
  │                              │         │                              │
  │  problems/heilbron_adversarial/         │  problems/heilbron_adversarial/
  │    pop_a/evaluate.py         │         │    pop_b/evaluate.py         │
  └──────────────────────────────┘         └──────────────────────────────┘
                ▲                                          │
                │  D's fitness: "how much did             │
                │  I improve G's configs?"                │
                │                                          ▼
                └──────────────  cross-play  ──────────────┘
                       (each gen, K opponents are sampled
                        from the other side's Hall of Fame)
```

**G's job:** make point configurations that are already good (high `min_area`) **and** that no D can easily improve.
**D's job:** take any incoming config and produce a strictly better one (higher `min_area`).

If G stays still, D learns to crush G's configs and D's fitness skyrockets.
If D stays still, G learns to dodge D and G's resistance score skyrockets.
Neither can stay still ⇒ Red Queen.

---

## 3. The 2×2 Design (Why Four Runs)

The sandbox runs **four** processes simultaneously, in **two arms × two roles**:

```
                     │   FEEDBACK MODE: composition  │  FEEDBACK MODE: gradient_in_prompt
                     │   (Lamarckian — code transfer)│  (Baldwinian — only words)
  ───────────────────┼───────────────────────────────┼─────────────────────────────
  ROLE: Constructor  │   A_G                         │   B_G
  (Pop A, Redis db=1 │   Redis db=1                  │   Redis db=3
   or db=3)          │   Sees D's *code*             │   Sees D's *natural-lang
                     │   injected verbatim           │   gradient* in mutation
                     │                               │   prompt
  ───────────────────┼───────────────────────────────┼─────────────────────────────
  ROLE: Improver     │   A_D                         │   B_D
  (Pop B, Redis db=2 │   Redis db=2                  │   Redis db=4
   or db=4)          │   sees G source +             │   sees G source +
                     │   evaluates K=3 G opponents   │   evaluates K=3 G opponents
                     │   (no code injection on D)    │   (no code injection on D)
  ───────────────────┴───────────────────────────────┴─────────────────────────────
```

The two arms test *how G receives information about D*. Arm A is **Lamarckian** (D's actual code becomes part of G's gene pool via `CompositionInjectionHook`). Arm B is **Baldwinian** (G only learns *about* D's strategies through prompt text via `GradientInPromptStage`). Both arms see the same number of opponents (K=3) and the same population sizes.

**Code locations of the two feedback modes:**
- `gigaevo/adversarial/composition_injection.py` — `CompositionInjectionHook` (arm A)
- `gigaevo/adversarial/stages.py` → `GradientInPromptStage` (arm B)

---

## 4. Topology (Where Things Live)

```
             ┌───────────────────────────────────────────────────────────┐
             │                  REDIS (one server, 16 DBs)               │
             │                                                           │
             │   db=1: pop_a   db=2: pop_b   db=3: pop_a   db=4: pop_b   │
             │   ┌──────┐     ┌──────┐      ┌──────┐      ┌──────┐      │
             │   │ A_G  │     │ A_D  │      │ B_G  │      │ B_D  │      │
             │   │ HoF  │◄────│ fetches      │ HoF  │◄────│ fetches      │
             │   │      │     │ K=3 from     │      │     │ K=3 from     │
             │   │      │────►│ db=1         │      │────►│ db=3         │
             │   │      │     │      ├─────►│      │     │      ├─────► │
             │   │ pulls│     │ HoF  │      │ pulls│     │ HoF  │       │
             │   │ K=3  │     │      │      │ K=3  │     │      │       │
             │   │ from │     │      │      │ from │     │      │       │
             │   │ db=2 │     │      │      │ db=4 │     │      │       │
             │   └──────┘     └──────┘      └──────┘      └──────┘      │
             │      ▲             ▲             ▲             ▲          │
             └──────┼─────────────┼─────────────┼─────────────┼──────────┘
                    │             │             │             │
                    │ each run    │ runs in     │ in its own  │
                    │ is its own  │ python      │ Hydra dir   │
                    │ Python proc │ process     │ for logs    │
                    │             │             │             │
            ┌───────┴───┐ ┌───────┴───┐ ┌───────┴───┐ ┌───────┴───┐
            │ PID       │ │ PID       │ │ PID       │ │ PID       │
            │ 2140082   │ │ 2140083   │ │ 2140084   │ │ 2140085   │
            └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
                  │             │             │             │
                  └─────────────┴──────┬──────┴─────────────┘
                                       │
                                       ▼
                  ┌──────────────────────────────────────┐
                  │  litellm proxy at 10.232.30.185:4000 │
                  │  model: Qwen3-235B-A22B-Thinking-2507│
                  │  (single LLM, all 4 runs share it)   │
                  └──────────────────────────────────────┘
```

**Why separate Redis DBs per arm?** So arm A and arm B do not share Hall of Fame entries. The two arms are independent universes.

**Why one shared LLM proxy?** So both arms experience the same generator — the only thing that differs is the feedback mode and population role.

---

## 5. The Hall of Fame and the Opponent Cache

When A_D fetches "the K=3 best G's from db=1 right now", it goes through this stack:

```
  ┌─────────────────────────────────────────────────────────┐
  │  RedisOpponentArchiveProvider                           │
  │  (gigaevo/adversarial/opponent_provider.py)             │
  │                                                         │
  │  ┌────────────────────────┐                             │
  │  │ get_top_k(3)           │  ← deterministic            │
  │  │ ZRANGEBYSCORE on the   │    (replaces previous       │
  │  │ pop_a archive sorted-  │    random get_opponents)    │
  │  │ set, descending fitness│                             │
  │  │ tiebreak by program_id │                             │
  │  └────────────┬───────────┘                             │
  │               │                                         │
  │               ▼                                         │
  │  ┌────────────────────────┐                             │
  │  │ in-process LRU cache   │  ← cache_ttl = 2.0s         │
  │  │ keyed by (k, db, pfx)  │    short enough that HoF    │
  │  └────────────┬───────────┘    rotations propagate;     │
  │               │                long enough to absorb    │
  │               ▼                bursts inside one gen    │
  │  ┌────────────────────────┐                             │
  │  │ FetchOpponentIdsStage  │  → emits Box[list[id]]      │
  │  └────────────┬───────────┘                             │
  │               │                                         │
  │               ▼                                         │
  │  ┌────────────────────────┐                             │
  │  │ FetchOpponentResultsSt │  → resolves IDs to programs │
  │  │ age (per-opponent      │    runs each opponent's     │
  │  │ executor pool)         │    program against parent   │
  │  └────────────┬───────────┘                             │
  │               │                                         │
  │               ▼                                         │
  │       opponent_results: list[program output]            │
  │       ↓                                                 │
  │       fed into the local population's evaluate.py       │
  └─────────────────────────────────────────────────────────┘
```

**Files:**
- `gigaevo/adversarial/opponent_provider.py` — `RedisOpponentArchiveProvider.get_top_k`
- `gigaevo/adversarial/stages.py:FetchOpponentIdsStage` (line ~66 — the `get_top_k` call)
- `gigaevo/adversarial/stages.py:FetchOpponentResultsStage`

---

## 6. Why HoF Rotations Need Cache Invalidation (the `cache_on` story)

Two stages do expensive LLM work whose value depends on **which opponents are in play**:

- `InsightsStage` (`gigaevo/programs/stages/insights.py`) — analyzes a program against context
- `LineageStage` (`gigaevo/programs/stages/insights_lineage.py`) — analyzes how parents → child changed

Before the redesign, both stages had `InputsModel = VoidInput`. The DAG cache key did **not** depend on the opponent set. Result: when D's HoF rotated and a new K=3 set of opponents was selected, InsightsStage **kept returning cached output from the previous opponent set**. Stale insights → stale prompts → no Red Queen.

**Fix:** new input class `CacheOnlyInput` in `gigaevo/programs/stages/common.py`. Its only purpose is to fold a value into the cache hash without participating in `compute()`:

```
  Before                                    After
  ──────                                    ─────

  InsightsStage(VoidInput)                  InsightsStage(CacheOnlyInput)
       │                                          │
       │  ◄── cache hit always when               │  ◄── cache hit ONLY when
       │      same program, regardless            │      same program AND
       │      of opponents                        │      same opponent IDs
       ▼                                          ▼

       (LLM never re-runs                         (LLM re-runs the moment
        post HoF rotation)                         HoF rotates — Red Queen
                                                   feedback closes the loop)
```

Wired in `gigaevo/adversarial/asymmetric_pipeline.py:_wire_cache_on_edges` — adds a `cache_on` data flow edge from `FetchOpponentIdsStage` to `InsightsStage` and `LineageStage` for both G and D pipelines.

---

## 7. The Smoothed Fitness — Why `tanh`

This is **the** structural fix from REDESIGN.md.

### 7.1 D fitness (Pop B / Improver) — what was wrong

Old D fitness for one opponent G config:

```
  delta = post_q - pre_q     (post = improved area, pre = original area)
  score = max(delta, 0) / Q_MAX     ← hard floor at zero
  fitness = mean(scores)
```

**Failure mode:** any D that doesn't beat the input gets score=0. In practice ~60-90% of D programs have delta ≤ 0 on most opponents (improving Heilbron configs is genuinely hard). Result:

```
  fitness distribution (old, hard-floored)

       count
        ▲
        │ ▓
        │ ▓
        │ ▓                                         this point mass
        │ ▓                                         contains everything;
        │ ▓                                         MAP-Elites cannot
        │ ▓ ░ ░ ░ ░ . . . . . . . . . . .          tell programs apart
        └─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─┴─→
          0  fitness                    1
```

### 7.2 D fitness (new) — `tanh`-smoothed, rescaled to (0, 1)

```
  delta = post_q - pre_q     (sign preserved!)
  score = tanh(delta / Q_MAX)              ← smooth, ∈ (-1, 1)
  mean_score = mean(scores)
  fitness = (mean_score + 1) / 2           ← rescaled to (0, 1)
```

The shape of `tanh(x)` rescaled:

```
  fitness
     1.0 │                                       _____ saturates
         │                                  ___/
         │                              ___/
         │                          ___/
     0.5 │                      ___/         ← D-did-nothing or exec failed
         │                  ___/                (delta = 0 → tanh(0) = 0
         │              ___/                     → fitness = 0.5)
         │          ___/
         │      ___/
     0.0 │__/                                ← D made things much worse
         └────┬────┬────┬────┬────┬────┬────→ delta / Q_MAX
            -3   -2   -1    0    1    2    3
```

**What this buys us:**
- A D that improves a little is **distinguishable** from a D that did nothing.
- A D that breaks things is distinguishable from a D that did nothing.
- The point mass at 0 vanishes. MAP-Elites can rank D's again.
- D-cold-start and D-failure both land at fitness=0.5 (neutral) — this is by design.

Code: `problems/heilbron_adversarial/pop_b/evaluate.py:120` (the `math.tanh(delta / Q_MAX)` line) and `:147` (the `(mean_score + 1.0) / 2.0` rescale).

### 7.3 G fitness (Pop A / Constructor)

G's fitness combines two things:

```
  fitness = 0.5 * quality + 0.5 * resistance
            ─────────────   ─────────────────
            "is this config  "did opponents
             intrinsically    fail to improve
             good?"           it?"

  quality   = min(min_area / 0.0365, 1.0)         ← bounded normalization
  resistance = (mean(tanh(-delta_i / Q_MAX)) + 1) / 2
                          ↑
                      negative because we want HIGH resistance
                      when delta is SMALL
```

When **all opponents** fail (callable raises) or there are no opponents (cold start), `resistance = 1.0` and `fitness = 0.5*q + 0.5`. This keeps the cold-start branch **consistent with the post-rescale formula** (R7 in the redesign risk register).

Code: `problems/heilbron_adversarial/pop_a/evaluate.py:65` (cold-start) and `:94-107` (smoothed resistance).

---

## 8. The Per-Generation Loop (One Tick)

```
    G side (every gen)                       D side (every gen)
  ──────────────────────                  ───────────────────────
                                          
   1. Pick parent from MAP-Elites          1. Pick parent from MAP-Elites
       (`gigaevo/evolution/strategies`)       
                                          
   2. FetchOpponentIdsStage:                2. FetchOpponentIdsStage:
       get_top_k(3) from D's archive          get_top_k(3) from G's archive
                                          
   3. FetchOpponentResultsStage:            3. FetchOpponentResultsStage:
       run each D opponent on this G         run G opponent's program → 11×2 pts
                                          
   4. (arm B only) GradientInPromptStage:   4. (arm A only) ─ no special stage ─
       look up DGTracker.get_top_pairs        D never sees code from G;
       inject natural-lang summary into       it just sees the *configs* G produced.
       mutation prompt
                                          
   5. MutationOperator: LLM rewrites G      5. MutationOperator: LLM rewrites D
                                          
   6. evaluate.py(opponent_results,         6. evaluate.py(opponent_results,
                  program_output) →                       program_output) →
        (metrics, artifact)                    (metrics, artifact)
        ↑ artifact carries per-               ↑ artifact carries per-
        opponent fitness deltas               opponent fitness deltas
                                          
   7. DGTrackerStage (F31):                 7. DGTrackerStage (F31):
       record (D_id, G_id, +delta) into       record (D_id, G_id, +delta) into
       Redis sorted set                       Redis sorted set
                                          
   8. MAP-Elites adds child to grid         8. MAP-Elites adds child to grid
                                          
   9. (arm A only) post-step hook:
       CompositionInjectionHook scans
       D archive, picks the best D per G,
       injects D∘G as a NEW G program
       (Lamarckian code transfer)
       — guarded by dg_injected_pairs SET
       to prevent duplicate injection
```

**Files for each stage in the per-gen loop:**
- `gigaevo/adversarial/stages.py` — `FetchOpponentIdsStage`, `FetchOpponentResultsStage`, `GradientInPromptStage`
- `gigaevo/adversarial/asymmetric_pipeline.py` — `AdversarialAsymmetricPipelineBuilder` (assembles all of the above)
- `gigaevo/adversarial/dg_tracker.py` — `DGImprovementTracker` (the Redis sorted-set storage)
- `gigaevo/adversarial/dg_tracker_stage.py` — `DGTrackerStage` (the pipeline node that writes into the tracker)
- `gigaevo/adversarial/composition_injection.py` — `CompositionInjectionHook` (the arm-A post-step hook)
- `gigaevo/programs/stages/insights.py` — `InsightsStage` (one of the cache_on consumers)
- `gigaevo/programs/stages/insights_lineage.py` — `LineageStage` (the other cache_on consumer)

---

## 9. The DG Improvement Tracker (Per-Pair Memory)

Every time D improves a G config by amount `delta > 0`, we record the pair:

```
   Redis sorted set:  <prefix>:dg_best_pairs
   ─────────────────────────────────────────
        member                    score
   ┌───────────────────┐    ┌───────────┐
   │ D_id_42 ‖ G_id_99 │ →  │  0.00831  │
   │ D_id_19 ‖ G_id_88 │ →  │  0.00604  │
   │ D_id_7  ‖ G_id_53 │ →  │  0.00451  │
   │ ...                │    │   ...     │
   └───────────────────┘    └───────────┘

   Redis SET:         <prefix>:dg_injected_pairs
   ─────────────────────────────────────────────
   { "D_id_42 ‖ G_id_99", ... }   ← permanent dedup
                                    once injected, never injected again

   Files:
     gigaevo/adversarial/dg_tracker.py
       - record_improvement(D_id, G_id, delta)   → ZADD dg_best_pairs
       - get_best_pairs(n)                       → ZREVRANGE dg_best_pairs
       - is_pair_injected(D_id, G_id)            → SISMEMBER dg_injected_pairs
       - mark_pair_injected(D_id, G_id)          → SADD     dg_injected_pairs
```

**Why we need the dedup SET:** without it, the post-step hook would re-inject the same `(D, G)` composition every generation, and G's archive would fill with duplicates of the same concept.

---

## 10. The Smoothed-Fitness Rescue, Visualized End-to-End

```
   Old D fitness                    New D fitness
   distribution                     distribution
   (point mass at 0)                (smoothed, MAP-Elites-friendly)

      ▓▓                                     ░
      ▓▓                                  ░░░░░░░
      ▓▓                                ░░░       ░░
      ▓▓                              ░░             ░░
      ▓▓ . . . .                    ░░                 ░░
      ▓▓ . . . . . . . .         ░░                       ░░
   ───┴──┴──┴──┴──┴──┴──┴───  ──┴──┴──┴──┴──┴──┴──┴──┴──┴──
   0.0  0.1  ...    1.0       0.0  0.25  0.5  0.75    1.0
                                                  ^
                                                  D-cold-start lives here
                                                  (delta=0 → tanh(0) → 0.5)

                          ↓ MAP-Elites can now rank ↓

       ┌──────────────────────────────────────────────────┐
       │   Insertion criterion is not "did you beat 0"    │
       │   but "are you in the top-K of your behavior     │
       │   cell?"  Smooth fitness gives every D a real    │
       │   ranking, so the archive fills with diverse     │
       │   strategies instead of "all the not-zeros".     │
       └──────────────────────────────────────────────────┘
```

---

## 11. Every Parameter We Set, In One Table

| Parameter | Value | Where set | Why |
|---|---|---|---|
| `max_generations` | 8 | `experiment.yaml:max_generations` + CLI | Sandbox is short — we only need to verify the bundle works end-to-end, not push fitness. |
| `max_mutations_per_generation` (G) | 8 | CLI override | G has only 8 children/gen so per-gen cost ≈ 8 LLM calls × K=3 opponents each. |
| `max_mutations_per_generation` (D) | 24 | CLI override | D evolves faster than G to keep up with G's archive growth (asymmetric pipeline pattern). |
| `max_elites_per_generation` | 8 | CLI override | MAP-Elites cell limit per gen — bounded growth. |
| `num_parents` | 1 | CLI override | One-parent mutation only; no crossover. |
| `mutation_mode` | `rewrite` | CLI override | LLM gets the parent and writes a complete new function (not a patch). |
| `evolution` | `steady_state` | CLI override | Asynchronous insertion; no generational gating. Required by the dual-engine adversarial pipeline. |
| `model_name` | `Qwen3-235B-A22B-Thinking-2507` | CLI override | The single LLM behind all 4 runs (litellm proxy). |
| `llm_base_url` | `http://10.232.30.185:4000/v1` | CLI override | The internal litellm proxy (per `experiments/infrastructure.yaml`). |
| `pipeline` | `adversarial_asymmetric` | CLI override + `config/pipeline/adversarial_asymmetric.yaml` | The G/D dual-builder pipeline. |
| `n_opponents` (K) | 3 | CLI override | Each program is evaluated against 3 opponents from the other side's HoF. |
| `source_prompt_k` (L) | 3 | CLI override | The mutation prompt sees 3 source examples (parents/insights) per call. K=L=3 by REDESIGN.md. |
| `pipeline_builder.archive_reeval` | `true` | CLI override (dotted path — required by Hydra struct mode) | Sets the cache handler on `FetchOpponentResultsStage`. `true` → `InputHashCache` (re-fetch only when opponent IDs change). `false` → `NeverCached` (re-fetch every DAG run). Combined with `_refresh_archive_programs()` requeuing all DONE → QUEUED at every epoch (`gigaevo/evolution/engine/core.py:602`), this means archived programs ARE re-scored against the current HoF whenever HoF rotates. See §12.5. |
| `opponent_provider.cache_ttl` | `2.0s` | CLI override | LRU cache on `get_top_k` — short enough that HoF rotations propagate within ~2s, long enough to absorb intra-gen call bursts (F20). |
| `feedback_mode` | `composition` (arm A) / `gradient_in_prompt` (arm B) | CLI override | The treatment variable. Arm A = Lamarckian, arm B = Baldwinian. |
| `population_role` | `constructor` (G) / `improver` (D) | CLI override | Which side of the asymmetric pipeline this run plays. |
| `d_sees_g_source` | `true` (D-side only) | CLI override | D's mutation prompt includes G's source code (as opposed to only G's outputs). Helps D reason about what kind of configs G produces. |
| `d_archive_persistent` | `true` (D-side only) | CLI override | D's MAP-Elites archive persists across HoF rotations (no re-init). |
| `sync_min_delta` | `1` (D-side only) | CLI override | The D engine syncs HoF every gen (min 1 gen between syncs). |
| `post_step_hook` | `${composition_injection_hook}` (A_G only) | CLI override | Runs `CompositionInjectionHook` after each step on the G side of arm A. |
| `redis.db` | 1 / 2 / 3 / 4 | CLI override | Per-arm DB isolation. |
| `opponent_redis_db` | 2 / 1 / 4 / 3 | CLI override | Each side reads opponents from the *other* side's DB within the same arm. |
| `opponent_redis_prefix` | `heilbron_adversarial/pop_a` or `pop_b` | CLI override | Per-population key namespace within a DB. |
| `stage_timeout` / `dag_timeout` | 1800s / 1800s | CLI override | Per-stage and per-DAG timeout — generous because LLM calls and exec sandboxes can be slow. |
| `hydra.run.dir` | `outputs/sandbox/<RUN_TS>/<label>/` | CLI override (added in `launch.sh`) | **Per-arm Hydra dir** — fixes the second-resolution timestamp collision in `setup_logger` so each arm has its own loguru file sink. |

---

## 12. Why This Design Tests Red Queen, Not Just "Two Optimizers"

A naive setup might just train two networks with cross-entropy gradients and call it co-evolution. We do **four** things that make it Red Queen-ish in the technical sense:

1. **Cross-play with sampling, not full pairing.** Each program sees only K=3 opponents per evaluation. This injects opponent-set noise — a program's fitness can move even if the program is unchanged. Like Red Queen species sampled in a finite ecosystem.

2. **HoF, not full archive, drives pressure.** D's opponents are not "every G ever" but "the K best G's right now". When G discovers a new mode, D suddenly faces it — a discrete environmental shift, like a predator's prey switching strategy.

3. **`archive_reeval=true` + `_refresh_archive_programs()` keep the archive coherent across HoF rotations.** Two interacting mechanisms: (a) every epoch, `_refresh_archive_programs()` flips every archived program DONE → QUEUED so it re-traverses the DAG (`gigaevo/evolution/engine/core.py:602`); (b) `FetchOpponentResultsStage` uses `InputHashCache`, so it cache-hits when opponent IDs are unchanged and cache-misses when D's HoF rotated, which then propagates to the evaluator and re-scores the program. Net effect: the archive stays self-consistent against the current HoF — see §12.5 for the details and the price.

4. **Smoothed fitness preserves selection gradient on both sides.** If D fitness collapses to 0 (old setup), the Red Queen *halts* on the D side: there is no signal to climb, so D drifts and G wins by default. Smoothing keeps both sides' gradients alive simultaneously.

The four together create the conditions for the sustained arms race **at the offspring level**. Verifying that those conditions actually hold in our infrastructure is what the sandbox checks (SANDBOX_CHECKS.md sections C1–C20) measure.

### 12.5 How the archive actually stays coherent against a rotating HoF

Two pieces interact to keep archived programs scored against the *current* HoF — neither alone is sufficient.

**Piece A — `_refresh_archive_programs()`** (`gigaevo/evolution/engine/core.py:602`).
Runs once per epoch as step 6 of `_epoch_refresh()` (`gigaevo/evolution/engine/steady_state.py:573`). It batch-transitions every archived program from `DONE` → `QUEUED`, putting them back into the DAG executor. Every stage's cache handler then decides whether to actually re-execute.

**Piece B — per-stage cache handlers.**
- `FetchOpponentIdsStage`: `NeverCached` — always re-runs, calls `get_top_k()` against the current D HoF.
- `FetchOpponentResultsStage`: `InputHashCache` when `archive_reeval=true`. Cache key = hash of opponent ID list.
  - Same IDs (HoF unchanged) → cache hit → no opponent re-execution → downstream stages also hit their caches → archive unchanged.
  - Different IDs (HoF rotated) → cache miss → re-fetch and re-run opponents → evaluator's input hash changes → re-score → MAP-Elites can replace the cell with the new score.
- `InsightsStage` / `LineageStage` (after Step 5 of the redesign): `cache_on` edge from `FetchOpponentIdsStage` → InputsModel is `CacheOnlyInput` → opponent IDs are folded into the input hash. Same invalidation rule.

**Timeline:**
```
   epoch t:    G_42 in archive, fitness=f(G_42, D_HoF@t)=0.78
   epoch t+1:  D_HoF unchanged → G_42 stays at 0.78 (cache hit, free)
   epoch t+2:  D_HoF rotates → G_42 re-scored to f(G_42, D_HoF@t+2)=0.62
                MAP-Elites cell may be replaced or kept depending on smoothed fitness
```

**Cost / behavior to be aware of:**
- Compute cost grows with archive size × HoF rotation rate. With `archive_reeval=true` (`InputHashCache`), only programs whose opponent IDs changed pay the cost. With `archive_reeval=false` (`NeverCached`) the cost is paid by every archived program every epoch.
- A program can move cells (or get evicted) when re-scored — MAP-Elites stickiness is *not* permanent.
- `actual_fitness` columns in the archive are kept current, not historical.
- Insights/lineage analyses also re-run when the HoF changes (cache_on), so the LLM context for descendants is built on fresh opponent semantics.

This is the design that makes the offspring-level Red Queen **and** the interior of the archive evolve together against the rotating HoF.

---

## 13. Where to Look If Something Is Weird

| Symptom | Open this file |
|---|---|
| D fitness stuck at 0.5 for everyone | `problems/heilbron_adversarial/pop_b/evaluate.py` (smoothing math) |
| G resistance always 1.0 | `problems/heilbron_adversarial/pop_a/evaluate.py:65` (cold-start branch) |
| Insights are stale across HoF rotations | `gigaevo/adversarial/asymmetric_pipeline.py:_wire_cache_on_edges` (was the edge added?) |
| D never sees new G's | `gigaevo/adversarial/opponent_provider.py:get_top_k` + `cache_ttl` (is the TTL too long?) |
| Compositions never get injected | `gigaevo/adversarial/composition_injection.py` + `dg_injected_pairs` SET |
| Tracker is empty | `gigaevo/adversarial/dg_tracker_stage.py` + check artifact has `per_opp_delta` |
| Per-arm log frozen | Each arm now has its own Hydra dir under `outputs/sandbox/<RUN_TS>/<label>/`; loguru file sink lives there. The nohup-redirected `run_<label>.log` only captures the bootstrap window. |

---

## 14. The Diagram of the Full Sandbox, One Shot

```
                        ┌──────────────────────────────────┐
                        │      sandbox launch.sh           │
                        │  flush DBs 1-4, assert SCARDs    │
                        │  one Hydra dir per arm           │
                        └────────────────┬─────────────────┘
                                         │
            ┌────────────┬───────────────┼─────────────┬───────────┐
            ▼            ▼               ▼             ▼           
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │ A_G (db=1)  │  │ A_D (db=2)  │  │ B_G (db=3)  │  │ B_D (db=4)  │
   │ composition │  │ composition │  │  gradient   │  │  gradient   │
   │ constructor │  │  improver   │  │ constructor │  │  improver   │
   │             │  │             │  │             │  │             │
   │ +post_step_ │  │ d_sees_g_   │  │             │  │ d_sees_g_   │
   │  hook =     │  │  source=T   │  │             │  │  source=T   │
   │  composition│  │             │  │             │  │             │
   │  _injection │  │             │  │             │  │             │
   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
          │                │                │                │
          └─cross-play─────┘                └─cross-play─────┘
            within arm A                      within arm B
          (db=1 ↔ db=2)                     (db=3 ↔ db=4)
          
                                ▼ end of run
                    ┌────────────────────────────┐
                    │  post_run_gate.sh (F35)    │
                    │  greps per-arm logs for    │
                    │  injection events,         │
                    │  asserts dg_injected_pairs │
                    │  SCARD > 0 on A_G (db=1)   │
                    └────────────────────────────┘
                                ▼
                    ┌────────────────────────────┐
                    │  SANDBOX_CHECKS.md C1–C20  │
                    │  pass table goes into      │
                    │  pre-registration PR       │
                    └────────────────────────────┘
```

That is the entire sandbox — what runs, where it lives, why each parameter is what it is, and how it tests Red Queen co-evolution.
