# Implementation Plan: Dynamic Re-Evaluation
# `heilbron/adversarial-dynamic-updates`

**Audience**: Researcher review before design finalisation.
**Purpose**: Nail down exactly what is fed where, how opponent selection works,
what fitness means, and how the new mechanism changes things.

---

## Part 1 — The Heilbronn Task (ELI5)

The **Heilbronn triangle problem**: place 11 points inside a unit triangle
so that the smallest triangle formed by any 3 of them is as large as possible.
The known bound is ~0.0365. Larger min_area = better configuration.

```
Unit triangle:        Best known (Heilbronn bound):
   A                  Points spread apart evenly → no
   /\                 3 points form a tiny triangle
  /  \                min_area ≈ 0.0365
 /    \
B------C
       ← 11 points inside, avoid small triangles →
```

**Two populations compete:**

```
┌─────────────────────────────────────────┐
│  Pop A — CONSTRUCTOR (G)                │
│  "Build hard-to-improve configurations" │
│  program_output: 11×2 numpy array       │
│  entrypoint() → [[x1,y1], ..., [x11,y11]]│
│  Goal: maximize min_area AND resist D   │
└─────────────────────────────────────────┘
              ↕  competes with
┌─────────────────────────────────────────┐
│  Pop B — IMPROVER (D)                   │
│  "Find a better arrangement of any G"   │
│  program_output: callable improve()     │
│  entrypoint() → callable that takes     │
│  a 11×2 config and returns better one   │
│  Goal: increase min_area of G configs   │
└─────────────────────────────────────────┘
```

---

## Part 2 — Current Evaluation Pipelines

### 2A: Evaluating a Constructor (G) program

```
NEW G PROGRAM (source code)
         │
         ▼
┌─────────────────────┐
│ ValidateCodeStage   │  Compile + syntax check
│ [cached]            │  → raises if bad code
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ CallProgramFunction │  Run entrypoint() → get 11×2 array
│ [cached]            │  (G's point configuration)
└─────────────────────┘
         │  program_output = 11×2 array
         │
         │         ┌──────────────────────────┐
         │         │ FetchOpponentResultsStage│  ← NO_CACHE
         │         │ [NO_CACHE]               │
         │         │ • reads D archive from   │
         │         │   Redis (opponent_db)    │
         │         │ • picks n=5 D programs   │
         │         │   (fitness-proportional) │
         │         │ • runs each D's          │
         │         │   entrypoint()           │
         │         │ • returns list of 5      │
         │         │   improve() callables    │
         │         └──────────────────────────┘
         │                    │
         │           opponent_results =
         │           [improve_fn_1, ..., improve_fn_5]
         │                    │
         └────────────────────┘
                    │
                    ▼
┌─────────────────────────────────┐
│ CallValidatorFunction           │  calls evaluate.py(pop_a)
│ (= pop_a/evaluate.py)           │
│                                 │
│ for each improve_fn in D_fns:   │
│   improved = improve_fn(G_pts)  │
│   delta = improved.min_area     │
│          - G_pts.min_area       │
│                                 │
│ resistance = 1 - mean(deltas)   │
│ quality    = min_area / 0.0365  │
│ fitness    = 0.5*Q + 0.5*R      │
│ actual_fitness = raw min_area   │
└─────────────────────────────────┘
         │
         ▼
  ┌──────────────────┐
  │ Fitness metrics  │
  │ fitness          │ ← MAP-Elites uses this for archive
  │ actual_fitness   │ ← primary DV for paper
  │ quality          │
  │ resistance       │
  └──────────────────┘
```

### 2B: Evaluating an Improver (D) program

```
NEW D PROGRAM (source code)
         │
         ▼
┌─────────────────────┐
│ ValidateCodeStage   │  Compile + syntax check
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ CallProgramFunction │  Run entrypoint() → get improve() callable
└─────────────────────┘
         │  program_output = improve() callable
         │
         │         ┌──────────────────────────┐
         │         │ FetchOpponentResultsStage│  ← NO_CACHE
         │         │ [NO_CACHE]               │
         │         │ • reads G archive from   │
         │         │   Redis (opponent_db)    │
         │         │ • picks n=5 G programs   │
         │         │   (fitness-proportional) │
         │         │ • runs each G's          │
         │         │   entrypoint()           │
         │         │ • returns list of 5      │
         │         │   11×2 point configs     │
         │         └──────────────────────────┘
         │                    │
         │           opponent_results =
         │           [config_1, ..., config_5]
         │           (five 11×2 arrays from G)
         │                    │
         └────────────────────┘
                    │
                    ▼
┌─────────────────────────────────┐
│ CallValidatorFunction           │  calls evaluate.py(pop_b)
│ (= pop_b/evaluate.py)           │
│                                 │
│ for each config in G_configs:   │
│   improved = improve_fn(config) │
│   delta = improved.min_area     │
│          - config.min_area      │
│                                 │
│ fitness = mean(normalized_delta)│
│ actual_fitness = best post-improv│
└─────────────────────────────────┘
         │
         ▼
  ┌──────────────────┐
  │ Fitness metrics  │
  │ fitness          │ ← MAP-Elites uses this for archive
  │ actual_fitness   │
  │ mean_improvement │
  └──────────────────┘
```

---

## Part 3 — Fitness Formulas with Numbers

### Constructor (G) fitness

```
G program outputs: [[0.1, 0.2], [0.3, 0.4], ..., [0.9, 0.1]]  ← 11 points
G's min_area (raw quality): 0.0320

5 Improvers evaluate G, each tries to improve:
  D1: improved to 0.0340 (+0.0020)
  D2: improved to 0.0330 (+0.0010)
  D3: failed to improve (0.0320, +0.0000)
  D4: improved to 0.0325 (+0.0005)
  D5: improved to 0.0350 (+0.0030)

mean_improvement_raw = (0.0020+0.0010+0.0000+0.0005+0.0030)/5 = 0.00130
mean_delta_norm      = 0.00130 / 0.0365 = 0.0356
resistance           = 1 - 0.0356  = 0.9644   ← hard to improve = good
quality              = min(0.0320 / 0.0365, 1) = 0.8767
fitness              = 0.5*0.8767 + 0.5*0.9644 = 0.9206   ← MAP-Elites key
actual_fitness       = 0.0320                              ← paper reporting
```

### Improver (D) fitness

```
D program's improve() callable is tested against 5 G configs:
  G1 (min_area=0.0280): improved to 0.0340  delta_norm = (0.0060/0.0365) = 0.164
  G2 (min_area=0.0320): improved to 0.0345  delta_norm = (0.0025/0.0365) = 0.068
  G3 (min_area=0.0300): failed (0.0300)     delta_norm = 0.000
  G4 (min_area=0.0310): improved to 0.0360  delta_norm = (0.0050/0.0365) = 0.137
  G5 (min_area=0.0350): failed (0.0350)     delta_norm = 0.000

fitness        = mean([0.164, 0.068, 0.000, 0.137, 0.000]) = 0.0738
actual_fitness = max post-improvement = 0.0360
```

---

## Part 4 — Opponent Selection: How It Currently Works

`OpponentArchiveProvider.get_opponents(n=5)`:

```
G archive (MAP-Elites grid, e.g. 10 occupied cells):
┌────┬────┬────┬────┬────┐
│ G1 │    │ G3 │    │ G5 │
│.94 │    │.89 │    │.92 │
├────┼────┼────┼────┼────┤
│    │ G7 │    │ G9 │    │
│    │.85 │    │.91 │    │
├────┼────┼────┼────┼────┤
│G11 │    │G13 │    │G15 │
│.88 │    │.93 │    │.86 │
└────┴────┴────┴────┴────┘
(fitness values shown)

Step 1: Read ALL program IDs from archive → [G1, G3, G5, G7, G9, G11, G13, G15]
Step 2: Fetch ALL programs from Redis
Step 3: FITNESS-PROPORTIONAL SAMPLING (weighted random):
  weights = [0.94, 0.89, 0.92, 0.85, 0.91, 0.88, 0.93, 0.86]
  total = 7.18
  probs = [0.131, 0.124, 0.128, 0.118, 0.127, 0.122, 0.129, 0.120]
  → randomly sample 5 without replacement using these weights
  → might return [G1, G5, G9, G13, G15] in one call
  → might return [G3, G7, G9, G11, G13] in another call
  (RANDOM — different each time)

Step 4: Execute each selected G's entrypoint() in parallel subprocesses
Step 5: Return results (5 point configurations)
```

**Cache**: The opponent list is cached for 30 seconds. Within that window,
repeated calls return the SAME set (same random draw). After 30s, re-sample.

---

## Part 5 — The MAP-Elites Archive

Each population has its own MAP-Elites grid stored in Redis:

```
G Archive (Pop A, redis db=1 in a pair):
┌─────────────────────────────────────────────────────┐
│ KEY: island_fitness_island:archive                  │
│ TYPE: Redis HASH { cell_id: program_id }            │
│                                                     │
│  "cell_0_0" → "g_abc123"   ← best G for cell (0,0) │
│  "cell_0_1" → "g_def456"                           │
│  "cell_1_0" → "g_ghi789"                           │
│  ...                                                │
│                                                     │
│ Behavior characterization (BC) = ???                │
│ (for Heilbronn: likely quality + resistance axes)   │
│                                                     │
│ Program data: PREFIX:program:PROGID                 │
│  → JSON: {code, metrics: {fitness, actual_fitness,  │
│              resistance, quality, ...}}             │
└─────────────────────────────────────────────────────┘

D Archive (Pop B, redis db=2 in same pair):
┌─────────────────────────────────────────────────────┐
│ Same structure, but stores Improver programs        │
│ metrics: {fitness, actual_fitness, mean_improvement}│
└─────────────────────────────────────────────────────┘
```

---

## Part 6 — The Staleness Problem (Why Improvers Stagnate)

```
Timeline of a typical run (current behavior, no re-eval):

GEN 5:
  G archive: {G1(min_area=0.030), G2(0.028), G3(0.026)}
  D archive: {D1 evaluated against G1,G2,G3 → fitness=0.42}
                        ↑
                   D1 scored well because G5/G3 were easy to improve

GEN 15:
  G archive: {G1(0.030), G2(0.028), G7(0.034), G8(0.035), G9(0.033)}
             ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑
             G has evolved MUCH better configs now!
  D archive: {D1 still shows fitness=0.42}
                               ↑↑↑↑↑↑↑↑
                               STALE! D1 was evaluated against GEN-5 G programs.
                               Against GEN-15 G programs, D1 might score 0.00.

  MAP-Elites selects D1 as a parent (high fitness=0.42)
  Generates mutations of D1...
  Those mutations are also weak against GEN-15 G (they inherit D1's strategy)
  → Improver stagnates: keeps generating children of a stale elite
```

**The symptom**: D's archive fills with programs that LOOK good (high archived
fitness) but ARE NOT GOOD against the current G frontier. Mutations of these
programs all fail → acceptance rate drops to 0%.

---

## Part 7 — The Proposed Fix: Per-Program Fingerprint Re-Evaluation

### The Key Change: Deterministic Top-N Selection

Current: fitness-proportional random sampling (different opponents each time)
Proposed for re-eval: **deterministic top-N by fitness** — always pick the same
N opponents for a given archive state.

Why: we need to know deterministically "which opponents WOULD be picked" to
compute a fingerprint. Random sampling can't produce a stable fingerprint.

```
Current sampling (fitness-proportional random):
  Call 1 → [G1, G5, G9, G13, G15]
  Call 2 → [G3, G7, G9, G11, G13]  ← different every time

Proposed deterministic top-N:
  Always take top-5 by fitness from archive:
  Archive: G7(0.93), G1(0.94), G13(0.93), G3(0.89), G5(0.92), G9(0.91)...
  Top-5:  [G1(0.94), G7(0.93), G13(0.93), G5(0.92), G9(0.91)]  ← stable
```

**Note**: The random sampling (fitness-proportional) is STILL used for new
program evaluations. Deterministic top-N is only used for fingerprinting and
for re-evaluation of archived programs. This keeps mutation diversity intact.

### Per-Program Fingerprint

When a D program is evaluated, store its "evaluation context":

```
D program D1 gets evaluated:
  Opponents sampled (deterministic top-5 at that moment):
  {G_abc123, G_def456, G_ghi789, G_jkl012, G_mno345}
                   ↑
  Store as D1.eval_fingerprint = frozenset of these 5 IDs

Later, at epoch boundary, recompute "what would be top-5 NOW":
  current_top5 = {G_abc123, G_def456, G_pqr678, G_stu901, G_vwx234}
                                          ↑↑↑↑↑↑↑↑  ↑↑↑↑↑↑↑↑
                                          NEW programs entered archive

  D1.eval_fingerprint   = {abc, def, ghi, jkl, mno}
  current_top5          = {abc, def, pqr, stu, vwx}
  DIFFERENT → re-evaluate D1 against the new top-5

  D2.eval_fingerprint   = {abc, def, pqr, stu, vwx}  (same as current)
  SAME → skip, D2's fitness is already current
```

### Symmetry: Same Logic for G

```
G program G1's stored fingerprint: {D_111, D_222, D_333, D_444, D_555}
Current top-5 Improvers: {D_111, D_222, D_333, D_666, D_777}  ← D_666, D_777 new

Different → re-evaluate G1 against new top-5 Improvers
  → G1's resistance score updates (maybe new Improvers can beat it)
  → G1's fitness = 0.5*quality + 0.5*resistance_against_CURRENT_D updates
```

---

## Part 8 — Where the Hook Fits in the Epoch Lifecycle

```
_epoch_refresh() steps (steady_state.py lines 517-645):

Step 1:  _draining = True
         (prevents new epoch triggers during refresh)

Step 2:  Snapshot drain_set = current in_flight program IDs

Step 3:  _drain_scoped(): wait for drain_set programs to finish
         (mutations + ingestion CONTINUE during this)

Step 3a: Publish programs_processed to Redis
         ← SYNC HOOK reads THIS counter (set BEFORE sync hook fires)

Step 4:  ProgressBasedSyncHook fires
         ← blocks until opponent population has processed min_delta more programs
         ← resolves based on programs_processed from step 3a (NOT affected by re-eval)

Step 5:  Snapshot bump (population stats refresh)

Step 6:  _refresh_archive_programs() — re-run archived programs through
         LINEAGE/INSIGHTS stages (mutation context building, NOT fitness re-eval)

Step 7:  *** mutation_gate.set() ← GATE OPENS HERE ***
         (new mutations start flowing immediately)
         Carry-forward drain-phase count, reset epoch counters

Step 8:  _await_idle() — wait for refresh DAGs (steps 5-6) + reindex
         Mutations from step 7 continue CONCURRENTLY

         *** NEW: ArchiveReEvaluationHook runs HERE (step 8 extension) ***
         ← mutation gate is OPEN (new mutations running concurrently)
         ← sync hook ALREADY resolved (can't deadlock)
         ← re-eval runs as normal DAG evaluations, same as new programs

Step 9:  Increment epoch counter, save to Redis

Step 10: Log epoch summary
```

### Why Step 8 is the Right Place

```
                     MUTATION GATE STATUS:
Step 1-3:  [OPEN]   mutations continue
Step 3:    [OPEN]   draining completes (mutations continue)
Step 4:    [CLOSED] mutation_gate.clear() ← happens at step 3
           Actually: gate closes at step 3 (before drain starts)
                    re-reading code... mutation_gate.clear() is at line 555
                    which is step 3 (after drain, before sync hook)
Step 4-6:  [CLOSED]
Step 7:    [OPEN]   mutation_gate.set()  ← opens here
Step 8:    [OPEN]   re-evaluation runs concurrent with new mutations
Step 9-10: [OPEN]

Re-evaluation at step 8:
✓ Sync hook already resolved → no deadlock possible
✓ Mutation gate open → no throughput blocking
✓ Concurrent with new mutations → minimal wall-time overhead
✓ Completes before epoch counter increments → fresh archive before epoch N+1
```

**Overhead note**: Re-evaluation at step 8 competes with new mutation DAGs for
the DAG runner's concurrency slots. But Heilbronn evaluation is CPU-bound
(numpy geometry, ~0.5s/program), not LLM-bound. Each re-eval task is much
faster than a new mutation (which includes ~60s of LLM inference). Contention
is minimal.

---

## Part 9 — Efficiency: How Much Re-Evaluation Actually Happens

### Worst case (all programs change every epoch):
```
Archive size:    20 programs
Opponents used:  5 per program
Re-eval cost:    ~0.5s per opponent × 5 = ~2.5s per program
Archive re-eval: 20 × 2.5s = 50s per epoch (sequential)
                 or ~10s if run with 5-way parallelism
```

### Realistic case (most fingerprints stable):
```
In a typical epoch:
  - 8 new mutations evaluated → 8 new programs enter archive (or fewer)
  - Maybe 2-3 displace existing elites in the G archive
  - Top-5 G programs change: maybe 1-2 new ones enter top-5
  - Only D programs whose top-5 G opponents changed need re-eval

If top-5 changes by 1 program:
  All D programs in archive need re-eval (their fingerprint changed)
  BUT: only the ones WHERE THOSE TOP-5 PROGRAMS ACTUALLY AFFECTED THE RESULT
  need updating. The fingerprint approach is conservative: re-eval all.

If top-5 is STABLE for 10 consecutive epochs (G archive plateaued):
  → ZERO re-evaluations for those 10 epochs
  → This is exactly when it doesn't matter (G is stagnant)
```

### Comparison: naive vs fingerprint approach

```
Archive: 20 D programs, 20 G programs

NAIVE (any archive change → re-eval everything):
  If 1 new G program enters archive each epoch:
  Re-eval ALL 20 D programs every epoch
  Cost: 20 × 2.5s = 50s EVERY epoch

FINGERPRINT (only re-eval if top-5 for that program changed):
  If new G program is NOT in top-5:
  Re-eval: 0 D programs (fingerprints unchanged)
  Cost: 0s

  If new G program enters top-5 (displaces weakest):
  Re-eval: all 20 D programs (fingerprints all changed by 1 entry)
  Cost: 50s — same as naive THIS epoch

  ADVANTAGE: fingerprint skips re-eval in epochs where archive grows
  but top-5 doesn't change (typical for stable/mature G archive)
  Expected savings: ~40-60% of epochs skip re-evaluation
```

---

## Part 10 — The 4-Run Design

### Run layout

```
TREATMENT PAIR (T1): Archive re-evaluation ON
┌──────────────────┐           ┌──────────────────┐
│  T1_A            │←opponents─│  T1_B            │
│  Constructor (G) │           │  Improver (D)    │
│  DB: 1           │─opponents→│  DB: 2           │
│  re-eval ON      │           │  re-eval ON      │
└──────────────────┘           └──────────────────┘

CONTROL PAIR (C1): Archive re-evaluation OFF
┌──────────────────┐           ┌──────────────────┐
│  C1_A            │←opponents─│  C1_B            │
│  Constructor (G) │           │  Improver (D)    │
│  DB: 5           │─opponents→│  DB: 6           │
│  re-eval OFF     │           │  re-eval OFF     │
└──────────────────┘           └──────────────────┘

No cross-pair interaction. T and C pairs are completely isolated.
```

### What each run sees

```
T1_A (Constructor, Treatment):
  - Runs pop_a/evaluate.py
  - Evaluates OWN point configurations
  - FetchOpponentResultsStage reads from DB=2 (T1_B Improver archive)
  - Re-evaluation hook: when top-N D programs in T1_B archive change,
    re-evaluate all T1_A archived G programs against new top-N
  - Fitness: 0.5*quality + 0.5*resistance  (from current D opponents)

T1_B (Improver, Treatment):
  - Runs pop_b/evaluate.py
  - Evaluates OWN improve() callable
  - FetchOpponentResultsStage reads from DB=1 (T1_A Constructor archive)
  - Re-evaluation hook: when top-N G programs in T1_A archive change,
    re-evaluate all T1_B archived D programs against new top-N
  - Fitness: mean normalized improvement over current G opponents

C1_A (Constructor, Control):
  - Identical to T1_A EXCEPT: no re-evaluation hook
  - Fitness frozen at evaluation time

C1_B (Improver, Control):
  - Identical to T1_B EXCEPT: no re-evaluation hook
  - Fitness frozen at evaluation time
```

### Opponent flow (arrows show who reads from whom)

```
DB 1: T1_A archive (G configs)
  ↑ evaluated by T1_A
  ↓ read by T1_B FetchOpponentResultsStage for D evaluation

DB 2: T1_B archive (improve() callables)
  ↑ evaluated by T1_B
  ↓ read by T1_A FetchOpponentResultsStage for G evaluation

DB 5: C1_A archive (G configs)
  ↑ evaluated by C1_A
  ↓ read by C1_B FetchOpponentResultsStage

DB 6: C1_B archive (improve() callables)
  ↑ evaluated by C1_B
  ↓ read by C1_A FetchOpponentResultsStage

T and C pairs are completely isolated: T1 never reads from C1 and vice versa.
```

---

## Part 11 — Worked Example: One Epoch of T1_B (Treatment Improver)

```
START of epoch:
  T1_A archive (G configs): [G1, G2, G3, G7, G9, G11, G13, G15]  (8 programs)
  Top-3 by fitness: [G1(0.94), G13(0.93), G7(0.93)]
    (using top-3 for this example instead of top-5 for simplicity)

  T1_B archive (D improve() callables): [D1, D4, D6, D8]  (4 programs)
  Their stored fingerprints:
    D1.fingerprint = frozenset({G1_id, G13_id, G7_id})   ← evaluated last epoch
    D4.fingerprint = frozenset({G1_id, G13_id, G7_id})   ← same top-3 as D1
    D6.fingerprint = frozenset({G2_id, G3_id, G9_id})    ← evaluated 5 epochs ago
    D8.fingerprint = frozenset({G1_id, G13_id, G11_id})  ← G11 was in top-3 then

DURING the epoch:
  8 new mutations run. Results:
    2 new G programs enter T1_A archive (G16, G17 — displacing G11, G2)
  T1_A archive now: [G1, G3, G7, G9, G13, G15, G16, G17]
  New top-3: [G1(0.94), G13(0.93), G7(0.93)]  ← SAME top-3 (G16, G17 not top-3)

EPOCH REFRESH (step 8 — after mutation gate opens):
  ArchiveReEvaluationHook runs for T1_B:
  
  Compute current top-3: frozenset({G1_id, G13_id, G7_id})
  
  Check each archived D program:
    D1: fingerprint={G1,G13,G7} == current top-3 → SKIP ✓
    D4: fingerprint={G1,G13,G7} == current top-3 → SKIP ✓
    D6: fingerprint={G2,G3,G9}  != current top-3 → RE-EVALUATE!
    D8: fingerprint={G1,G13,G11}!= current top-3 → RE-EVALUATE!
  
  Re-evaluate D6 against [G1, G13, G7]:
    D6 used to score 0.38 (against G2, G3, G9 — easier targets)
    D6 scores 0.09 against [G1, G13, G7] (much harder targets)
    → D6's archive fitness drops from 0.38 to 0.09
    → Archive re-insertion: D6 may be displaced from its cell
    → D6.fingerprint updated to frozenset({G1_id, G13_id, G7_id})
  
  Re-evaluate D8 against [G1, G13, G7]:
    D8 used to score 0.41 (when G11 was in top-3 — easier)
    D8 scores 0.12 against [G1, G13, G7]
    → D8's archive fitness drops from 0.41 to 0.12
    → Archive re-insertion
    → D8.fingerprint updated

RESULT:
  T1_B archive is now honest about which D programs are ACTUALLY good
  against the current best G configurations.
  
  Next epoch: MAP-Elites selects parents from D1, D4 (still valid)
  and maybe D6/D8 if they're still competitive at their honest fitness.
  Mutations of D1/D4 explore around the best current Improvers.
```

---

## Part 12 — Open Questions for Researcher

Before finalizing the design, please confirm:

**Q1: Opponent selection for re-evaluation: deterministic top-N vs fitness-proportional**

Current proposal: deterministic top-N for fingerprinting and re-eval.
This means re-evaluation always uses the SAME N opponents for all archived
programs. This is efficient but may reduce evaluation diversity.

Alternative: keep fitness-proportional sampling, but use the SAME random seed
for a given archive state (reproducible sampling). This preserves diversity
but requires storing the seed alongside the fingerprint.

**Q2: Symmetric re-evaluation of G**

The proposal re-evaluates BOTH G (when D archive's top-N changes) and D
(when G archive's top-N changes). The value for G is updating `resistance`
scores. Do you want G re-evaluation symmetric, or only D re-evaluation?

Note: G's `actual_fitness` (raw min_area of its point config) does NOT
depend on opponents at all — it's intrinsic geometry. Only `resistance`
and the composite `fitness` change when D opponents change. So G re-evaluation
updates `fitness` but NOT `actual_fitness` (the paper DV).

**Q3: What to use as primary DV**

If we re-evaluate G, the `fitness` values change throughout the run.
The `actual_fitness` (raw min_area) is opponent-independent and more stable.

Options:
- Primary DV = `actual_fitness` (raw min_area) — opponent-independent, clean
- Primary DV = `fitness` (composite) — reflects current opponent quality

The previous design uses `actual_fitness`. Confirm this is what you want.

**Q4: N=1 pair per condition**

The previous design had N=2 per condition (8 runs). Your feedback: N=1 (4 runs).
This is exploratory (N=1, no within-condition replication). The comparison
is treatment pair vs control pair — single observation each.

Confirmed? Volkov will note this as underpowered, which we accept for an
exploratory run.

**Q5: K=0 (no feedback) vs K=3 feedback**

Current design: K=0 (isolate re-eval mechanism).
Alternative: K=3 feedback + re-eval (test the combo that PATTERNS.md flags
as highest value). Risk: confounds the re-eval signal with K=3 signal.

Which do you want?

---

## Part 13 — Summary: What Actually Changes

```
CURRENT (all prior adversarial experiments):
  D program evaluated once → fitness frozen
  MAP-Elites selects parents based on stale fitness
  → Improver stagnation

PROPOSED (this experiment, treatment arm):
  D program evaluated once → fitness stored WITH fingerprint
  At each epoch:
    Compute current top-N G programs (deterministic)
    For each D in archive: if fingerprint != current top-N → re-evaluate
    Update D's fitness and fingerprint
  MAP-Elites selects parents based on CURRENT fitness
  → Hypothesis: reduces stagnation

CONTROL arm:
  Runs identically to current behavior (no fingerprinting, no re-eval)
  Direct comparison within same experimental run
```

---

*Prepared for researcher review. Respond to Q1-Q5 to finalize the design.*
