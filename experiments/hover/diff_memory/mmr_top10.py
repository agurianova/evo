#!/usr/bin/env python3
"""MMR-rank the top-N programs of a finished pair via paired-bootstrap duels.

Usage: mmr_top10.py <run_root> [--n 10] [--arms MEM_R1,NOMEM_R1]

Both arms score the SAME fixed 300-claim train set, so any two programs can
be compared PAIRED on shared samples (gigaevo.programs.metrics.paired). For
the pooled top-N by stored fitness we compute the full pairwise
P(A beats B) matrix with PairedBootstrap, fit Bradley-Terry strengths
(MM iterations on the soft win counts), and report an Elo-style MMR.
The top-rated program is the "most promising" pick for test evaluation —
single-eval fitness ranks are noise-dominated (sigma ~0.0078).
Appends the full result record to mmr_results.jsonl in this directory.
"""

from datetime import UTC, datetime
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from gigaevo.programs.metrics.paired import COHERENCE_TOL, PairedBootstrap

HERE = Path(__file__).parent


def load_eligible(run_root: Path, arm: str) -> list[dict]:
    progs = []
    for f in sorted(run_root.glob(f"{arm}/storage/*/programs/*.json")):
        p = json.loads(f.read_text())
        fitness = p.get("metrics", {}).get("fitness")
        raw = p.get("metadata", {}).get("per_sample_scores")
        # Discarded challengers stay in the pool — the archive gate's rejection
        # is one paired verdict vs one incumbent; MMR re-adjudicates globally.
        if (
            p.get("state") not in ("done", "discarded")
            or fitness is None
            or raw is None
        ):
            continue
        scores = np.asarray(raw, dtype=float)
        if (
            scores.ndim != 1
            or scores.size == 0
            or not np.isfinite(scores).all()
            or abs(float(scores.mean()) - float(fitness)) > COHERENCE_TOL
        ):
            continue
        progs.append(
            {
                "arm": arm,
                "id": p["id"],
                "file": str(f),
                "iteration": p.get("iteration"),
                "fitness": float(fitness),
                "scores": scores,
            }
        )
    return progs


def bradley_terry(p_matrix: np.ndarray, iters: int = 500) -> np.ndarray:
    """MM fit on soft win counts w[i,j] = P(i beats j), one duel per pair."""
    n = p_matrix.shape[0]
    wins = p_matrix.sum(axis=1) - np.diag(p_matrix)
    s = np.ones(n)
    for _ in range(iters):
        denom = np.array(
            [sum(1.0 / (s[i] + s[j]) for j in range(n) if j != i) for i in range(n)]
        )
        s = np.clip(wins, 1e-9, None) / denom
        s /= np.exp(np.log(s).mean())
    return s


def main():
    argv = sys.argv[1:]
    n_top = 10
    arms = ["MEM_R1", "NOMEM_R1"]
    if "--n" in argv:
        i = argv.index("--n")
        n_top = int(argv[i + 1])
        del argv[i : i + 2]
    if "--arms" in argv:
        i = argv.index("--arms")
        arms = argv[i + 1].split(",")
        del argv[i : i + 2]
    run_root = Path(argv[0]).resolve()

    pool = [p for arm in arms for p in load_eligible(run_root, arm)]
    lengths = {p["scores"].size for p in pool}
    if len(lengths) != 1:
        sys.exit(f"unpaired eval sets across pool: lengths {lengths}")
    pool.sort(key=lambda p: p["fitness"], reverse=True)
    top = pool[:n_top]
    print(f"{len(pool)} eligible programs ({'+'.join(arms)}), ranking top {len(top)}")

    stat = PairedBootstrap(n_resamples=10_000, seed=0)
    n = len(top)
    pm = np.full((n, n), 0.5)
    for i in range(n):
        for j in range(i + 1, n):
            p = stat.probability_better(top[i]["scores"], top[j]["scores"])
            pm[i, j], pm[j, i] = p, 1.0 - p

    strength = bradley_terry(pm)
    mmr = 400.0 * np.log10(strength) + 1500.0
    mean_win = (pm.sum(axis=1) - 0.5) / (n - 1)
    order = np.argsort(-mmr)

    print(
        f"\n{'rk':>2} {'MMR':>6} {'meanP':>6} {'fitness':>8}  {'arm':<9} {'gen':>3}  id"
    )
    for rk, i in enumerate(order, 1):
        p = top[i]
        print(
            f"{rk:>2} {mmr[i]:>6.0f} {mean_win[i]:>6.3f} {p['fitness']:>8.4f}  "
            f"{p['arm']:<9} {p['iteration'] if p['iteration'] is not None else '?':>3}  {p['id']}"
        )

    winner = top[order[0]]
    print(
        f"\nMMR winner: {winner['arm']} {winner['id']} (fitness {winner['fitness']:.4f})"
    )
    print(f"MMR winner file: {winner['file']}")

    rec = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "run_root": str(run_root),
        "arms": arms,
        "n_pool": len(pool),
        "ranking": [
            {
                "rank": rk,
                "mmr": float(mmr[i]),
                "mean_p_better": float(mean_win[i]),
                **{k: top[i][k] for k in ("arm", "id", "file", "iteration", "fitness")},
            }
            for rk, i in enumerate(order, 1)
        ],
        "p_matrix": pm.round(4).tolist(),
    }
    with open(HERE / "mmr_results.jsonl", "a") as fh:
        fh.write(json.dumps(rec) + "\n")


if __name__ == "__main__":
    main()
