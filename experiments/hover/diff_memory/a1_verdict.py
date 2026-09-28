#!/usr/bin/env python3
"""Prereg A1 acceptance verdict for the ALL-IN pair.

A1: the best pooled winner's K=5 val re-eval mean must exceed 0.8298 AND be
paired-per-sample significant (p<.05) vs BOTH prior champions MEM_R1 (.8298)
and NOV_R2 (.8291). Pre-declared asymmetry: WIN => genuine; NO-WIN =/=> worse.

Pairing follows the eval-noise study exactly: per-claim vector = mean over the
K evals' 300-claim scores (same load_context(n_samples=300) subset), Wilcoxon
zero_method="zsplit" + 20k-bootstrap CI on per-claim diffs; SIG iff the CI
excludes 0 AND p < .05. Writes a1_verdict.json.
"""

import json
from pathlib import Path

import numpy as np
import scipy.stats as ss

HERE = Path(__file__).parent
A1_BAR = 0.8298
PRIORS = {
    "MEM_R1": ("prior_reeval/reeval_results.json", "MEM_R1"),
    "NOV_R2": ("prior_reeval/reeval_results_nov.json", "NOV_R2"),
}

rng = np.random.default_rng(0)


def summarize(rec: dict) -> dict:
    fits = np.array([e["fitness"] for e in rec["evals"]])
    return {
        "program_id": rec["program_id"],
        "in_run": rec["in_run_fitness"],
        "k": len(fits),
        "reeval_mean": float(fits.mean()),
        "reeval_sd": float(fits.std(ddof=1)),
        "ci95_half": float(1.96 * fits.std(ddof=1) / np.sqrt(len(fits))),
    }


def per_claim(rec: dict) -> np.ndarray:
    return np.mean([e["scores"] for e in rec["evals"]], axis=0)


def paired(da: np.ndarray, db: np.ndarray) -> dict:
    diff = da - db
    w = ss.wilcoxon(da, db, zero_method="zsplit")
    boots = [rng.choice(diff, len(diff)).mean() for _ in range(20_000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    sig = bool((lo > 0 or hi < 0) and w.pvalue < 0.05)
    return {
        "mean_diff": float(diff.mean()),
        "ci95": [float(lo), float(hi)],
        "wilcoxon_p": float(w.pvalue),
        "sig": sig,
    }


def main():
    new = json.loads((HERE / "reeval_results_vec.json").read_text())
    priors = {
        label: json.loads((HERE / path).read_text())[key]
        for label, (path, key) in PRIORS.items()
    }

    out = {"a1_bar": A1_BAR, "winners": {}, "priors": {}, "paired": {}}
    for label, rec in priors.items():
        out["priors"][label] = summarize(rec)
    for label, rec in sorted(new.items()):
        s = summarize(rec)
        out["winners"][label] = s
        print(
            f"{label:<16} in-run {s['in_run']:.4f} | re-eval {s['reeval_mean']:.4f} "
            f"± {s['ci95_half']:.4f} (sd {s['reeval_sd']:.4f}, k={s['k']})"
        )

    prior_vecs = {label: per_claim(rec) for label, rec in priors.items()}
    for label, rec in sorted(new.items()):
        vec = per_claim(rec)
        for plabel, pvec in prior_vecs.items():
            r = paired(vec, pvec)
            out["paired"][f"{label}_vs_{plabel}"] = r
            print(
                f"{label} vs {plabel}: diff {r['mean_diff']:+.4f} "
                f"CI[{r['ci95'][0]:+.4f},{r['ci95'][1]:+.4f}] "
                f"p={r['wilcoxon_p']:.4f} {'SIG' if r['sig'] else 'ns'}"
            )

    best = max(out["winners"], key=lambda x: out["winners"][x]["reeval_mean"])
    beats_bar = out["winners"][best]["reeval_mean"] > A1_BAR
    sig_both = all(out["paired"][f"{best}_vs_{p}"]["sig"] for p in PRIORS)
    pos_both = all(out["paired"][f"{best}_vs_{p}"]["mean_diff"] > 0 for p in PRIORS)
    out["best"] = best
    out["a1_win"] = bool(beats_bar and sig_both and pos_both)
    print(
        f"\nbest={best} reeval_mean={out['winners'][best]['reeval_mean']:.4f} "
        f"bar>{A1_BAR}: {beats_bar} | sig vs both priors: {sig_both} "
        f"(positive: {pos_both})"
    )
    print(
        f"A1 VERDICT: {'WIN' if out['a1_win'] else 'NO-WIN (=/=> worse, prereg asymmetry)'}"
    )

    (HERE / "a1_verdict.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
