# Preregistration: BD3D behavior space + paired gate, memory vs no-memory — hover full7

Date: 2026-07-11 (pre-launch). Branch: memory-cold-probe-policy (uncommitted).
Launcher: `launch_bd3d_noise.sh` (verbatim mirror of `launch_noise_gate.sh`
extended to 4 runs). Supersedes the staged fitness-bin noise launch
(`prereg_noise_gate_20260711.md`, never launched): fitness bins make the gate
near-vacuous (`archive_storage.py:198` consults the selector only for occupied
cells, and a 150-bin fitness space rarely re-hits a cell), and they ignore the
domain. Design doc: `plans/2026-07-11-chain-bd3d-proposal.md`.
User approval: combined design approved in principle ("Let us run both
changes: B3D + noise change together (+memory and no-memory)"); launch still
gated on Telegram go after the NOVAUC pair frees the 8 chain backends.

## Question

Two coupled questions on one foundation:
1. Does niching on chain-strategy axes (hop_depth × passages_fetched ×
   instr_chars — `algorithm=chains_bd3d`) instead of fitness bins let hop-2/3
   lineages survive the fitness valley and reach the hop-4 region, with the
   paired-bootstrap gate now consulted often enough to filter noise-driven
   replacement where it actually occurs?
2. On that foundation, does memory (cards + GAM) help — measured as the
   preregistered MEM vs NOMEM contrast under identical conditions?

## Arms (2 arms × 2 reps, 250 mutants each, launched together)

Shared: `algorithm=chains_bd3d` + `enable_chain_structural_metrics=true` +
`program_format=json_document` + `problem.name=chains/hover/full7_vectorized`
+ `archive_selector=paired_bootstrap` (p_accept=0.75).

- MEM_R1 / MEM_R2: `pipeline=memory_guided_noise memory=full memory/write=live`.
- NOMEM_R1 / NOMEM_R2: `pipeline=guided_noise memory=none` (campaign no-mem
  convention on the noise-routing DAG; `guided_noise` = guided +
  `_program_metadata` routing, no memory anywhere).

The one-treatment rule is satisfied by the arm contrast itself; all shared
deltas vs older pairs are foundation, not treatment. Comparisons vs the
fitness-bin pairs (MEM 20260710_041404, NOMEM 20260709_164213) are
observational only — the space change confounds them.

## Treatment provenance (all pre-launch)

- BD3D axes mined from 1491 hover programs of finished runs: hop_depth
  (transitive tool-closure depth), passages_fetched (k-weighted: retrieve=7,
  retrieve_deep=10), instr_chars (STRUCTURED_FIELDS + system_prompt).
  5×5×6=150 cells, dynamic bounds; same populations occupy 40–64 cells on
  these axes vs 13–16 on the old topology axes.
- Features parsed with the CARL parse-layer models
  (`problems.chains.types.RawChainSpec`); schema-invalid specs → zeros;
  `algorithm_requires` in the preset makes run.py fail at config time if the
  producing stage or json_document format is missing (inert-treatment
  protection, generic mechanism).
- Paired gate provenance carries over from `prereg_noise_gate_20260711.md`
  (offline stats smoke, live synthetic pair, four-axis review — all green).
- 10 semantic extractor tests + 6 algorithm_requires compose tests green;
  168 config+scheduling tests green.

## Causal chain

Niche on strategy axes instead of fitness bins (signal) → hop-2/3 lineages
survive the fitness valley; deep-hop and guidance-style diversity persists in
the archive (behaviour: occupancy M1, hop-share M2) → occupied-cell challenges
become common, so the paired gate is consulted where noise matters (G1) and
elites accumulate only replicable gains (P-churn) → evolution reaches the
hop-4 region more often; in the MEM arm, cards transfer mechanisms into
protected niches (S2) → higher true best fitness (S1, K=5 re-eval CIs), and
the MEM−NOMEM delta is the memory effect on this foundation.

## Riskiest link

The hop-4 fitness peak (mean 0.766, n=91, vs global 0.733) is
**observational** — chains that got good may have grown deep rather than depth
causing quality. If the hop-2 valley is intrinsic, protected hop-2/3 cells
hold weak elites and ~2/5 of the archive budget never pays off within 250
mutants. Falsified if M2 rises but hop≥3 elites' re-eval fitness stays below
hop-1 elites at run end — then the axis is a cost, not a ladder, and the next
lever is a different strategy axis, not more bins.

## Endpoints & predictions

| ID | Prediction | Measure | Falsified if |
|---|---|---|---|
| P1 | transport intact | every scored program carries the ~300-len vector; mean↔fitness ≤1e-4; 0 gate fallback lines | any fallback / missing vector |
| M1 | occupancy jumps | distinct occupied cells per run ≥35 (fitness-space control: 13–16; offline replay: 40–64) | <25 cells — axes don't spread live populations |
| M2 | depth protected | share of valid programs with hop_depth≥3 ≥1.5× pooled control (12.7%) | ≤ control share |
| G1 | gate consulted | fraction of archive inserts hitting an occupied cell ≫ fitness-bin runs'; >0 in-run flips (REJECT where point rule would swap) | 0 flips → gate behaviorally inert even on BD3D |
| P-churn | churn drops | occupied-cell ACCEPT rate < point-rule rate from prior pairs (same counting script) | ACCEPT rate ≥ control |
| S1 | memory effect, replicable | K=5 re-eval mean ± CI of final best: MEM ≥ NOMEM (directional at n=2/arm) | MEM clearly below NOMEM both reps |
| S2 | context shines in deep niches (MEM arm) | with-card per-mutation fitness delta in hop≥3 cells > in hop≤1 cells | delta ≤ hop≤1 delta — cards don't exploit protected niches |

Mechanism endpoints (P1, M1, M2, G1, P-churn) are log/archive-derived and
deterministic; fitness endpoints are directional only at n=2 per arm
(single-eval σ≈0.0078; hence K=5 re-evals with CIs).

## 1h treatment check (replaces the deleted config-time-only safety)

At T+1h on each run: (a) occupancy >5 distinct cells (else the space is
degenerate — abort all four, investigate extractor on live programs);
(b) P1 transport spot-check; (c) MEM arm writes cards / NOMEM arm has zero
memory artifacts. Any failure → abort before burning backend budget.

## Decision rule

- Adopt BD3D as the hover default space: M1+M2 hold AND S1 (either arm) not
  worse than the observational fitness-bin baselines' re-evals.
- Memory verdict: S1 MEM vs NOMEM with CIs is the primary contrast; S2
  explains mechanism if positive.
- Park + retune: M1 holds but M2 fails → axis is a cost (riskiest-link
  outcome); G1 fails → gate stays optional, churn analysis observational.
- Investigate before any verdict: P1 or the 1h check fails (integrity bug,
  not a result).
