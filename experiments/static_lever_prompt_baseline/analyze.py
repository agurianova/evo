"""Static-lever blast closeout: 4-arm fair-end analysis (B core-6 vs C tail vs A/D bars).

Reads the four disk-run full CSVs, builds cumulative-best trajectories on the
program-count axis (running max of strictly-valid fitness), checkpoints every 25
programs, and scores the registered predictions. n=2 per arm (budget cut 8->4),
so stats are effect-size + exact 2v2 permutation + checkpoint-wins, not powered p.
"""

from __future__ import annotations

import csv
from itertools import combinations
import json
import math
import sys

# dir holding {C6-1,C6-2,TL-1,TL-2}_full.csv from `gigaevo export csv`
S = sys.argv[1] if len(sys.argv) > 1 else "."
RUNS = {"C6-1": "B", "C6-2": "B", "TL-1": "C", "TL-2": "C"}
ARMS = {"B": ["C6-1", "C6-2"], "C": ["TL-1", "TL-2"]}
# External bars (fair-end @ program 245), from EVOTAB-A-33 memory deep-analysis.
BAR = {"A_nomem": (0.0294, 0.0018), "D_dynamic": (0.0289, 0.0015)}
SENTINEL = {-1.0, -999.0, 0.0}


def truthy(x: str) -> bool:
    return str(x).strip().lower() not in (
        "",
        "none",
        "false",
        "0",
        "0.0",
        "[]",
        "{}",
        "nan",
    )


def load(run: str):
    rows = list(csv.DictReader(open(f"{S}/{run}_full.csv")))
    rows.sort(key=lambda r: int(r["atomic_counter"]))
    prog = []  # (count_index, valid_fitness_or_None, is_nonroot, mem_used, mem_cited)
    for i, r in enumerate(rows, start=1):
        f = r["metric_fitness"]
        v = r["metric_is_valid"]
        fit = None
        if f not in ("", "None") and v in ("1", "1.0", "True", "true"):
            fv = float(f)
            if math.isfinite(fv) and fv not in SENTINEL:
                fit = fv
        nonroot = r["is_root"] not in ("1", "1.0", "True", "true")
        prog.append(
            (
                i,
                fit,
                nonroot,
                truthy(r.get("metadata_memory_used", "")),
                truthy(r.get("metadata_memory_selected_idea_ids", "")),
            )
        )
    return prog


DATA = {run: load(run) for run in RUNS}


def cumbest_at(prog, k: int):
    best = None
    for idx, fit, *_rest in prog:
        if idx > k:
            break
        if fit is not None and (best is None or fit > best):
            best = fit
    return best


TOTALS = {run: len(DATA[run]) for run in RUNS}
FLOOR = min(TOTALS.values())  # common program-count floor across the 4 runs
CHECKPOINTS = list(range(25, FLOOR + 1, 25))
if 245 not in CHECKPOINTS:
    CHECKPOINTS = sorted(set(CHECKPOINTS + [245]))


def arm_stats_at(arm: str, k: int):
    vals = [cumbest_at(DATA[run], k) for run in ARMS[arm]]
    vals = [v for v in vals if v is not None]
    m = sum(vals) / len(vals)
    sd = (sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5 if len(vals) > 1 else 0.0
    return m, sd, vals


def perm_p_2v2(bvals, cvals):
    """Exact permutation on 4 values, C(4,2)=6 label assignments; two-sided |mean diff|."""
    pool = bvals + cvals
    obs = abs(sum(bvals) / 2 - sum(cvals) / 2)
    hits = tot = 0
    for combo in combinations(range(4), 2):
        b = [pool[i] for i in combo]
        c = [pool[i] for i in range(4) if i not in combo]
        if abs(sum(b) / 2 - sum(c) / 2) >= obs - 1e-12:
            hits += 1
        tot += 1
    return obs, hits / tot


report = {"totals": TOTALS, "floor": FLOOR, "checkpoints": {}}

# Checkpoint table
for k in CHECKPOINTS:
    row = {}
    for run in RUNS:
        row[run] = cumbest_at(DATA[run], k)
    bm, bsd, _ = arm_stats_at("B", k)
    cm, csd, _ = arm_stats_at("C", k)
    row["B_mean"], row["B_sd"] = bm, bsd
    row["C_mean"], row["C_sd"] = cm, csd
    report["checkpoints"][k] = row

# Fair-end at 245 (matched to bars) and at common floor
for label, k in [("fairend_245", 245), (f"floor_{FLOOR}", FLOOR)]:
    bm, bsd, bvals = arm_stats_at("B", k)
    cm, csd, cvals = arm_stats_at("C", k)
    obs, p = perm_p_2v2(bvals, cvals)
    pooled_sd = (((bsd**2) + (csd**2)) / 2) ** 0.5 or float("nan")
    # cross-pairs B_i vs C_j (4 pairs): count B>C
    cross = [
        (bi, cj, bv > cv)
        for bi, bv in zip(ARMS["B"], bvals)
        for cj, cv in zip(ARMS["C"], cvals)
    ]
    report[label] = {
        "k": k,
        "B": {"runs": dict(zip(ARMS["B"], bvals)), "mean": bm, "sd": bsd},
        "C": {"runs": dict(zip(ARMS["C"], cvals)), "mean": cm, "sd": csd},
        "B_minus_C_mean": bm - cm,
        "perm_obs_absdiff": obs,
        "perm_p": p,
        "cohens_d_BvC": (bm - cm) / pooled_sd
        if pooled_sd == pooled_sd and pooled_sd > 0
        else None,
        "B_minus_A": bm - BAR["A_nomem"][0],
        "C_minus_A": cm - BAR["A_nomem"][0],
        "B_minus_D": bm - BAR["D_dynamic"][0],
        "C_minus_D": cm - BAR["D_dynamic"][0],
        "cross_pairs_BgtC": sum(1 for *_x, w in cross for _ in [0] if w),
        "cross_pairs": [(a, b, w) for a, b, w in cross],
    }

# Onset: earliest checkpoint where arm mean crosses A bar (0.0294)
A0 = BAR["A_nomem"][0]
for arm in ("B", "C"):
    onset = None
    for k in CHECKPOINTS:
        m, _sd, _v = arm_stats_at(arm, k)
        if m is not None and m >= A0:
            onset = k
            break
    report.setdefault("onset_cross_A", {})[arm] = onset

# Adherence + invalidity audit
audit = {}
for run in RUNS:
    prog = DATA[run]
    nonroot = [p for p in prog if p[2]]
    valid = [p for p in prog if p[1] is not None]
    mem_used = [p for p in nonroot if p[3]]
    mem_cited = [p for p in nonroot if p[4]]
    audit[run] = {
        "n_programs": len(prog),
        "n_nonroot": len(nonroot),
        "n_valid": len(valid),
        "invalid_rate": round(1 - len(valid) / len(prog), 3),
        "mem_used_rate": round(len(mem_used) / len(nonroot), 3) if nonroot else None,
        "mem_cited_rate": round(len(mem_cited) / len(nonroot), 3) if nonroot else None,
    }
report["audit"] = audit
report["bars"] = BAR

json.dump(report, open(f"{S}/static_lever_analysis.json", "w"), indent=2)


# ---- human-readable ----
def f(x):
    return "  --  " if x is None else f"{x:.5f}"


print("STATIC-LEVER BLAST — 4-arm fair-end analysis")
print(f"program totals: {TOTALS}  common floor={FLOOR}")
print("\nCheckpoint table (cumulative-best fitness, higher=better):")
print(
    f"{'k':>4} | {'C6-1':>8} {'C6-2':>8} | {'B mean±sd':>17} | {'TL-1':>8} {'TL-2':>8} | {'C mean±sd':>17}"
)
for k in CHECKPOINTS:
    r = report["checkpoints"][k]
    print(
        f"{k:>4} | {f(r['C6-1'])} {f(r['C6-2'])} | {r['B_mean']:.5f}±{r['B_sd']:.5f} | "
        f"{f(r['TL-1'])} {f(r['TL-2'])} | {r['C_mean']:.5f}±{r['C_sd']:.5f}"
    )

for label in ("fairend_245", f"floor_{FLOOR}"):
    d = report[label]
    print(f"\n=== {label} (k={d['k']}) ===")
    print(f"  B core-6: {d['B']['runs']}  mean={d['B']['mean']:.5f}±{d['B']['sd']:.5f}")
    print(f"  C tail  : {d['C']['runs']}  mean={d['C']['mean']:.5f}±{d['C']['sd']:.5f}")
    print(
        f"  B-C mean Δ={d['B_minus_C_mean']:+.5f}  perm_p={d['perm_p']:.3f}  cohens_d={d['cohens_d_BvC']}"
    )
    print(
        f"  B-A={d['B_minus_A']:+.5f}  C-A={d['C_minus_A']:+.5f}  (A no-mem bar {BAR['A_nomem'][0]})"
    )
    print(
        f"  B-D={d['B_minus_D']:+.5f}  C-D={d['C_minus_D']:+.5f}  (D dynamic bar {BAR['D_dynamic'][0]})"
    )
    print(f"  cross-pairs B>C: {d['cross_pairs_BgtC']}/4  {d['cross_pairs']}")

print(f"\nonset cross A(0.0294): {report['onset_cross_A']}")
print("\nadherence + invalidity audit:")
for run, a in audit.items():
    print(f"  {run} [{RUNS[run]}]: {a}")
