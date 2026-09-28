# Preregistration: paired-bootstrap archive gate (p_accept=0.75) — hover full7

Date: 2026-07-11 (pre-launch). Branch: memory-cold-probe-policy (uncommitted).
Launcher: `launch_noise_gate.sh` (verbatim mirror of
`launch_baseline_memory.sh`; cfg diff verified — exactly three functional
deltas, all serving ONE treatment: `problem.name=chains/hover/full7_vectorized`
+ `pipeline=memory_guided_noise` + `archive_selector=paired_bootstrap`).
User approval: PENDING (launch gated on Telegram go; recommend launching after
the live NOVAUC pair finishes to avoid contention on the 8 chain backends).

## Question

Hover single-eval fitness carries σ≈0.0078 run-level noise, so the point rule
(`new > current`) lets lucky draws displace genuinely good elites. Does gating
archive replacement on P(paired mean per-claim diff > 0) ≥ 0.75 — computed
from each program's ~300 per-claim coverage scores over the SAME eval set —
protect elites from noise-driven churn without blocking real improvements?

## Treatment

`PairedBootstrapArchiveSelector` (subclass of production `SumArchiveSelector`;
delegates to the point rule whenever either side lacks a coherent vector).
`full7_vectorized/validate.py` is a verbatim copy of full7 except it emits the
per-claim score vector under the reserved `_program_metadata` namespace;
`pipeline=memory_guided_noise` routes it onto `program.metadata` before any
prompt/artifact consumer sees it. Fitness scoring is IDENTICAL to full7, so
the existing MEM control pair remains a valid fitness comparator.

Provenance (all pre-launch, 2026-07-11):
- Offline stats smoke (200 trials, real validate + real selectors): pure-noise
  elite churn 51% (point) → 23% (paired); worse-by-0.007 challenger accepted
  30% → 10%; genuine gains accepted 99% under both; twin → P=0.500 → REJECT.
- Live synthetic pair (14 programs/arm): transport 14/14, vector↔fitness
  coherence ≤1e-4, zero prompt leaks, zero gate fallbacks; 17 flips on stored
  live vectors (e.g. challenger 0.407 vs incumbent 0.398 → P(better)=0.61 →
  keep incumbent where the point rule would swap).
- Four-axis Opus review: all confirmed findings fixed, 93 scoped tests green.
- `run.py` compat guard rejects the paired selector under any pipeline that
  does not route `_program_metadata` (inert-treatment protection).

## Arms

- NOISE_R1 / NOISE_R2 — new pair, paired gate p_accept=0.75, 250 mutants each.
- Control: MEM_R1 / MEM_R2 (outputs/hover-diff-memory-baseline-20260710_041404),
  point rule, same launcher otherwise. K=5 re-evals of final best already on
  file: 0.8298 / 0.7893.

## Causal chain

Vector rides `program.metadata` into MAP-Elites insertion → occupied-cell
challenges run the paired bootstrap on ~300 paired per-claim diffs (shared
eval set pairs out per-claim difficulty; SE of the paired mean ≪ marginal
noise) → challengers whose mean edge is within noise are REJECTed instead of
displacing the incumbent → (a) elite churn per challenge drops, (b) archive
elites accumulate only replicable gains, so the single-eval "best fitness"
loses its lucky-draw inflation → (c) K=5 re-eval of the final best matches or
beats control even if the in-run reported best looks flatter.

## Riskiest link

p_accept=0.75 at hover's noise scale may be too conservative: if typical real
mutation gains (~0.005–0.02) sit below the gate's detection threshold at
n≈300 paired samples, hill-climbing stalls — few elite updates, flat
trajectory, S1 worse than control. That is a legitimate negative result: the
knob is `archive_selector.p_accept` and the OFF position (0.5) recovers the
point rule exactly (bit-identical decisions, verified offline).

## Endpoints & predictions

| ID | Prediction | Measure | Falsified if |
|---|---|---|---|
| P1 | transport intact | every scored program carries the ~300-len vector; mean↔fitness ≤1e-4; 0 gate fallback lines | any fallback / missing vector (treatment partially inert) |
| P2 | gate consumed live | >0 `P(better)=` decisions; ≥1 in-run flip (REJECT where challenger mean > incumbent) across 250 mutants | 0 flips — gate never disagreed with point rule → treatment behaviorally inert at this noise scale |
| P3 | churn drops | occupied-cell ACCEPT rate < control's point-rule accept rate (from logs, same counting script both arms) | ACCEPT rate ≥ control |
| S1 | replicable fitness | K=5 re-eval of final best (with CIs) ≥ control's 0.8298/0.7893, directional at n=2 | re-eval best clearly below control both replicas |
| D1 | inflation removed | in-run single-eval best may sit BELOW control's — expected consequence of removing selection bias, judged only via S1 | n/a (interpretation guard, not a gate) |

Mechanism endpoints P1–P3 are log-derived and deterministic; fitness S1 is
directional only at n=2 (single-eval σ≈0.0078; hence K=5 re-evals with CIs).

## Decision rule

Ship (adopt gate as hover default): P1–P3 hold AND S1 not worse. Park + retune
p_accept: P1–P2 hold but P3/S1 show over-conservatism (stalled updates, flat
trajectory). Investigate before any verdict: P1 fails (integrity bug, not a
result).
