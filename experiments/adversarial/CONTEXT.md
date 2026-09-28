# Adversarial Co-Evolution — Task Context

This directory is the parent context for the adversarial co-evolution research line.
Individual experiments live in subdirectories: `experiments/adversarial/<name>/`.

---

## Part 1 — Stable Task Knowledge

### What Is Adversarial Co-Evolution

Two MAP-Elites populations evolve in parallel. Each population's fitness depends on performance
against the other population's archive, creating an arms race that drives both toward better solutions.

See `docs/adversarial_coevolution.md` for the full architecture guide.

**Pipeline**: `pipeline=adversarial_coevo` — extends standard pipeline with `FetchOpponentResultsStage` and `MainRunSyncHook`.

---

### Key Characteristics

- **No chain servers** — adversarial experiments are pure code evolution (no LLM chain execution). `chain_url=null` in experiment.yaml.
- **Mutation-only LLM** — uses Qwen3-235B via LiteLLM proxy at `10.232.30.185:4000/v1`.
- **Paired runs** — always run in pairs (Pop A + Pop B). Each pair shares opponent references via `opponent_redis_db` and `opponent_redis_prefix` overrides.
- **No test set** — `has_test_set: false`. Fitness is continuous, evaluated against opponent archive.
- **Auth required** — LiteLLM proxy requires `Authorization: Bearer sk-gigaevo` for `/v1/models` checks. Key stored in `experiment.yaml custom_env.OPENAI_API_KEY`.

---

### Problem Variants

| Problem directory | Pop A role | Pop B role | Experiment |
|---|---|---|---|
| `adversarial/optimizer_v2/pop_a`, `pop_b` | Optimizer | Landscape | `adversarial/optimizer-coevo` |
| `heilbron_adversarial/pop_a`, `pop_b` | Constructor | Improver/Prover | `adversarial/heilbron-prover`, `heilbron/adversarial-v2` |
| `heilbron_solo` | Solo (no opponent) | — | `adversarial/adversarial-vs-solo` |

---

### Heilbronn Benchmarks

| Experiment | Feedback | Constructor actual_fitness | Notes |
|---|---|---|---|
| `adversarial/heilbron-prover` (v1) | K=0 (score only) | 0.03380 / 0.03548 (mean 0.03464) | Gen 42-50 |
| `heilbron/adversarial-v2` (K=3) | K=3 bidirectional code | 0.03502 (Constructor), 0.03568 (best via Improver) | Premature stop gen 31-34 |
| `heilbron/adversarial-v2` (K=1) | K=1 bidirectional code | 0.03247 | Stalled, below v1 baseline |
| `heilbron/baseline-repro` (N=4) | K=0 (score only) | 0.03337 mean (Constructor), 0.03449 mean (best-overall) | 95% CI [0.029, 0.038] Constructor, [0.031, 0.038] best-overall. 3 near-Q_MAX: P3_A=0.0365, P1_B=0.0361 |
| `adversarial/adversarial-vs-solo` (N=4) | Solo (no opponent) | 0.03267 mean | SD=0.00300, bimodal: S1=0.03538, S3=0.03458 (adversarial-level) vs S2=0.03199, S4=0.02872 (below) |

**Target**: min_area = 0.0365 (known Heilbronn optimum for n=11)

---

### Known Bugs and Patterns

#### Helper shape mismatch (heilbron-prover)
Pop A had 75% invalidity while Pop B had ~0%. Root cause: `helper.py` expected `(N,2)` array
but LLM-generated code passed `(2,)`. Fix: `atleast_2d()` in helper. Always check if one pop
has drastically different invalidity — asymmetric invalidity is the signature of a shape/API bug.

#### MainRunSyncHook deadlock at max_gen (heilbron/baseline-repro Issue #3)
When one run in a pair completes max_gen and exits, the remaining run's MainRunSyncHook polls for
an opponent state update that will never come. Self-resolves after ~21 min (timeout fallback), but
can stall the final generation. Systemic fix needed: skip wait when opponent gen >= max_generations.

#### Generation parity
Paired runs should stay within 2 generations of each other. Larger gaps indicate one population
is stalled (dead PID, stuck on validation, or server issue). The anomaly detector agent checks this.

#### Restart scope
For adversarial experiments, **always restart the full pair** (both populations). Single-run
restart creates asymmetric archive state.

#### K=1 opponent context regression (adversarial-v2)
Showing K=1 opponent code block produced Constructor actual_fitness 0.03247 — *below* the K=0 baseline (0.03464). K=3 was above baseline (0.03502). The ordering K=3 > K=0 > K=1 suggests a minimum effective dose for opponent context: too little (K=1) may cause the LLM to over-anchor on a single strategy, which is worse than no context at all. Use K≥3 for opponent code feedback, or use parsed critique instead of raw code.

#### Improver stagnation (structural, confirmed across 3 experiments)
Improvers stagnate in all adversarial experiments regardless of task or feedback mechanism. Both Constructors in v1 and v2 reached 100% resistance. Root cause unknown but hypotheses: (1) Improver task is structurally harder (finding improvements vs generating from scratch), (2) binary fitness signal (improvement found or not) provides zero gradient near optimum. Next experiment should test D re-evaluation (issue #195) to keep Improver fitness current as Constructors improve.

---

## Part 2 — Infrastructure (current state — update before each launch)

_Last updated: 2026-04-07_

**Canonical server inventory**: `experiments/infrastructure.yaml`

### Mutation LLMs (Qwen3-235B-A22B-Thinking)

All access via LiteLLM proxy: `http://10.232.30.185:4000/v1`
Auth: `Bearer sk-gigaevo` (set in `custom_env.OPENAI_API_KEY` in experiment.yaml)

Backend mutation servers: see `infrastructure.yaml` → `mutation_servers` (4 endpoints on port 8777).

### No Chain Servers Needed

Adversarial experiments don't use chain execution LLMs. `chain_url: null` in all runs.

### Verification

```bash
# Check LiteLLM proxy
curl -s http://10.232.30.185:4000/v1/models -H "Authorization: Bearer sk-gigaevo" | python3 -c "import sys,json; d=json.load(sys.stdin); print([m['id'] for m in d['data']])" 2>/dev/null || echo "PROXY UNREACHABLE"

# Check mutation servers directly
for ip in 10.232.90.109 10.232.38.220 10.232.22.232 10.232.21.74; do
  curl -s http://$ip:8777/v1/models | python3 -c "import sys,json; print(f'$ip:8777', json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || echo "$ip:8777 UNREACHABLE"
done
```

### Completed Experiments

| Experiment | Result | Key finding |
|---|---|---|
| `adversarial/optimizer-coevo` (PR #169) | ASYMMETRIC | Landscapes improve (+67.7pp), optimizers stagnate (+1.8pp). Arms race hypothesis not supported. |
| `adversarial/heilbron-prover` (PR #183) | POSITIVE | Constructors reach 97% of Heilbronn target (min_area 0.0355). actual_fitness STRONG POSITIVE (+0.03462 mean). Arms race asymmetric: Constructors 96-99%, Improvers stagnate (40-65%). 100% resistance = genuine local optima. |
| `heilbron/adversarial-v2` (PR #188) | SUGGESTIVE POSITIVE | K=3 bidirectional code feedback marginal (+0.00038 vs baseline). K=1 regressed below baseline (-0.00217). Best overall 0.03568 (K=3 Improver). Premature stop at 45%. Improver stagnation persists. |
| `heilbron/baseline-repro` (PR #201) | SUGGESTIVE | Baseline reproducible on best-overall (mean=0.03449 vs 0.03464, -0.4%). Constructor-only CI wide [0.029, 0.038]. 3 near-Q_MAX discoveries (P3_A=0.0365). Improver polishing exceeds Constructor in 3/4 pairs. |
| `adversarial/adversarial-vs-solo` (PR #203) | INCONCLUSIVE | Solo mean 0.03267 vs adversarial 0.03449 (+0.00182, p=0.365, d=0.70). Underpowered at N=4 (55% power). Solo bimodal: 2/4 matched adversarial, 2/4 well below. Adversarial tighter SD (0.00212 vs 0.00300). Line should not be closed. |
