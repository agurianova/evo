"""Gate 0 — Spearman ρ(quality, resistance) on v2 G archives.

Pulls archive members from each G-side Redis DB, loads program JSON,
extracts metric_quality and metric_resistance, computes ρ per run and
pooled across runs.

Gate criterion (plan §7):
    |ρ| < 0.7  → v3 G primary BD (quality, resistance) approved.
    |ρ| ≥ 0.7  → fallback to (quality, g_tracker_coverage_count).
"""

from __future__ import annotations

import json

import redis
from scipy.stats import spearmanr

RUNS = [
    ("A3_G", 1),
    ("A5_G", 3),
    ("B3_G", 5),
    ("B5_G", 7),
]
PREFIX = "heilbron_adversarial/pop_a"
ISLAND_ID = "fitness_island"
ARCHIVE_KEY = f"island_{ISLAND_ID}:archive"


def load_run(db: int) -> list[tuple[str, float, float, float]]:
    r = redis.Redis(host="localhost", port=6379, db=db, decode_responses=True)
    pids = list(r.hvals(ARCHIVE_KEY))
    if not pids:
        return []
    pipe = r.pipeline(transaction=False)
    for pid in pids:
        pipe.get(f"{PREFIX}:program:{pid}")
    raw = pipe.execute()
    rows: list[tuple[str, float, float, float]] = []
    for pid, blob in zip(pids, raw):
        if blob is None:
            continue
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        m = data.get("metrics", {})
        q, res = m.get("quality"), m.get("resistance")
        fit = m.get("fitness")
        if q is None or res is None:
            continue
        try:
            q = float(q)
            res = float(res)
            fit = float(fit) if fit is not None else float("nan")
        except (TypeError, ValueError):
            continue
        rows.append((pid, q, res, fit))
    return rows


def summarize(label: str, rows: list[tuple[str, float, float, float]]) -> None:
    n = len(rows)
    if n < 3:
        print(f"  {label:6s} n={n:4d}  (too few for Spearman)")
        return
    q = [x[1] for x in rows]
    r = [x[2] for x in rows]
    rho, p = spearmanr(q, r)
    q_min, q_max = min(q), max(q)
    r_min, r_max = min(r), max(r)
    gate = "PASS (primary OK)" if abs(rho) < 0.7 else "FAIL (use fallback)"
    print(
        f"  {label:6s} n={n:4d}  ρ(q,r)={rho:+.3f}  p={p:.2e}  "
        f"q∈[{q_min:.4f},{q_max:.4f}]  r∈[{r_min:.3f},{r_max:.3f}]  → {gate}"
    )


def main() -> None:
    print("=" * 92)
    print("Gate 0 — Spearman ρ(quality, resistance) on v2 G archives")
    print("Pass threshold: |ρ| < 0.7  (plan §7)")
    print("=" * 92)

    pooled: list[tuple[str, float, float, float]] = []
    for label, db in RUNS:
        rows = load_run(db)
        summarize(label, rows)
        for pid, q, r, fit in rows:
            pooled.append((f"{label}:{pid}", q, r, fit))

    print("-" * 92)
    summarize("POOLED", pooled)
    print("=" * 92)

    n = len(pooled)
    if n >= 3:
        rho_fit_q, _ = spearmanr([p[3] for p in pooled], [p[1] for p in pooled])
        rho_fit_r, _ = spearmanr([p[3] for p in pooled], [p[2] for p in pooled])
        print(
            f"Bonus: pooled ρ(fitness, quality)={rho_fit_q:+.3f}  "
            f"ρ(fitness, resistance)={rho_fit_r:+.3f}"
        )


if __name__ == "__main__":
    main()
