"""Emit numbers.tex — every figure the prose quotes, as LaTeX macros.

The report never types a number by hand; it \\input{}s this file. A macro that
disagrees with the stats JSON is impossible, so the prose cannot drift from the
run the way a transcribed table can.

Usage: python make_numbers.py <arm-slug>:<macro-prefix> ...
"""

import json
from pathlib import Path
import sys

from make_figures import cost_usd
from make_invalid_table import family_counts
import numpy as np

HERE = Path(__file__).parent
VIZ = HERE / "viz"


def neighbour_macros(arm):
    """The capability numbers: proposed, built, supervised, and on the champion."""
    n = json.loads((VIZ / f"{arm}_neighbour.json").read_text())
    valid_n = [
        r for r in n["programs_detail"] if r["has_neighbour"] and r["is_valid"] == 1.0
    ]
    return {
        "NbrBuilt": f"{n['with_neighbour']}",
        "NbrValid": f"{n['valid_with_neighbour']}",
        "NbrSup": f"{n['with_supervised_neighbour']}",
        "NbrMention": f"{n['mentions_neighbour']}",
        "NbrMentionOnly": f"{n['mentions_but_not_built']}",
        "NbrAgg": f"{n['with_aggregate']}",
        "NbrFirst": "n/a"
        if n["first_neighbour_index"] is None
        else f"{n['first_neighbour_index'] + 1}",
        "NbrBest": "n/a"
        if n["best_neighbour_fitness"] is None
        else f"{n['best_neighbour_fitness']:.6f}",
        "NbrChampion": "yes" if n["champion_has_neighbour"] else "no",
        "NbrGenFirst": "n/a"
        if not valid_n
        else f"{min(r['generation'] for r in valid_n)}",
    }


def _spearman(xs, ys):
    """Rank correlation, ties averaged. Small n, so no scipy dependency."""

    def rank(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        out = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    rx, ry = np.array(rank(xs)), np.array(rank(ys))
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def panel_macros(arm):
    """Held-out scores for the whole CV-top, not just the champion."""
    test = json.loads((VIZ / f"{arm}_test.json").read_text())
    panel = test["panel"]
    no_nbr = test["best_no_neighbour"]
    rho = _spearman([r["cv_r2"] for r in panel], [-r["test_rmse"] for r in panel])
    top = max(panel, key=lambda r: r["test_r2"])
    top_rmse = min(panel, key=lambda r: r["test_rmse"])
    return {
        "PanelN": f"{len(panel)}",
        "PanelNbr": f"{sum(r['neighbour'] for r in panel)}",
        "PanelRho": f"{rho:+.2f}",
        "PanelTestMean": f"{np.mean([r['test_r2'] for r in panel]):.6f}",
        "PanelTestMin": f"{min(r['test_r2'] for r in panel):.6f}",
        "PanelTopTest": f"{top['test_r2']:.6f}",
        "PanelTopTestId": top["id"][:8].replace("_", r"\_"),
        "PanelTopTestCVRank": f"{panel.index(top) + 1}",
        "PanelRmseMean": f"{np.mean([r['test_rmse'] for r in panel]):.4f}",
        "PanelRmseWorst": f"{max(r['test_rmse'] for r in panel):.4f}",
        "PanelTopRmse": f"{top_rmse['test_rmse']:.4f}",
        "PanelTopRmseId": top_rmse["id"][:8].replace("_", r"\_"),
        "PanelTopRmseCVRank": f"{panel.index(top_rmse) + 1}",
        "NoNbrCV": "n/a" if not no_nbr else f"{no_nbr['cv_r2']:.6f}",
        "NoNbrTest": "n/a" if not no_nbr else f"{no_nbr['test_r2']:.6f}",
        "NoNbrRmse": "n/a" if not no_nbr else f"{no_nbr['test_rmse']:.4f}",
        "NoNbrGen": "n/a" if not no_nbr else f"{no_nbr['generation']}",
        "NbrGapCV": "n/a"
        if not no_nbr
        else f"{test['best']['cv_r2'] - no_nbr['cv_r2']:+.6f}",
        "NbrGapTest": "n/a"
        if not no_nbr
        else f"{test['best']['test_r2'] - no_nbr['test_r2']:+.6f}",
        "NbrGapRmse": "n/a"
        if not no_nbr
        else f"{test['best']['test_rmse'] - no_nbr['test_rmse']:+.4f}",
    }


def macros(arm, prefix):
    stats = json.loads((VIZ / f"{arm}_stats.json").read_text())
    test = json.loads((VIZ / f"{arm}_test.json").read_text())
    invalid = json.loads((VIZ / f"{arm}_invalid.json").read_text())
    programs = stats["programs"]
    valid = [p for p in programs if p["is_valid"] == 1.0]
    calls = stats["llm_calls"]
    ok = [c for c in calls if c["ok"]]
    best = max(valid, key=lambda p: p["fitness"])

    out = {
        "Model": ok[0]["model"].replace("_", r"\_"),
        "Programs": f"{len(programs)}",
        "Incomplete": f"{stats['incomplete']}",
        "Valid": f"{len(valid)}",
        "Invalid": f"{len(programs) - len(valid)}",
        "ValidPct": f"{len(valid) / len(programs) * 100:.1f}\\%",
        "Wall": f"{stats['run_seconds'] / 60:.1f}",
        "WallWork": f"{max(p['elapsed_s'] for p in programs) / 60:.1f}",
        "SeedCV": f"{test['seed']['cv_r2']:.6f}",
        "SeedTest": f"{test['seed']['test_r2']:.6f}",
        "SeedRmse": f"{test['seed']['test_rmse']:.4f}",
        "BestCV": f"{test['best']['cv_r2']:.6f}",
        "BestTest": f"{test['best']['test_r2']:.6f}",
        "BestRmse": f"{test['best']['test_rmse']:.4f}",
        "BestId": test["best"]["id"][:8].replace("_", r"\_"),
        "BestGen": f"{best['generation']}",
        "BestNodes": f"{best['node_count']:.0f}",
        "BestDepth": f"{best['max_depth']:.0f}",
        "BestFeats": f"{best['feature_count']:.0f}",
        "DeltaCV": f"{test['best']['cv_r2'] - test['seed']['cv_r2']:+.6f}",
        "DeltaTest": f"{test['best']['test_r2'] - test['seed']['test_r2']:+.6f}",
        "DeltaRmse": f"{test['best']['test_rmse'] - test['seed']['test_rmse']:+.4f}",
        "ChildMean": f"{np.mean([p['fitness'] for p in valid]):.6f}",
        "ChildStd": f"{np.std([p['fitness'] for p in valid]):.6f}",
        "NodesMean": f"{np.mean([p['node_count'] for p in valid]):.2f}",
        "NodesMax": f"{max(p['node_count'] for p in valid):.0f}",
        "DepthMean": f"{np.mean([p['max_depth'] for p in valid]):.2f}",
        "DepthMax": f"{max(p['max_depth'] for p in valid):.0f}",
        "DeepPct": f"{np.mean([p['max_depth'] >= 2 for p in valid]) * 100:.1f}\\%",
        "Calls": f"{len(calls)}",
        "CallsFailed": f"{len(calls) - len(ok)}",
        "TokIn": f"{sum(c['tokens_in'] for c in ok):,}",
        "TokOut": f"{sum(c['tokens_out'] for c in ok):,}",
        "TokReason": f"{sum(c['tokens_reasoning'] for c in ok):,}",
        "TokReasonMean": f"{np.mean([c['tokens_reasoning'] for c in ok]):,.0f}",
        "TokOutMean": f"{np.mean([c['tokens_out'] for c in ok]):,.0f}",
        "TokOutMax": f"{max(c['tokens_out'] for c in ok):,}",
        "LatMed": f"{np.median([c['latency_ms'] for c in ok]) / 1000:.1f}",
        "LatPfive": f"{np.percentile([c['latency_ms'] for c in ok], 95) / 1000:.1f}",
        "Spend": f"{cost_usd(ok):.2f}",
        "Malformed": f"{family_counts(arm)['malformed JSON / schema violation']}",
        "InvalidTop": invalid[0][0].split(":", 1)[-1].strip()[:70]
        if invalid
        else "n/a",
        **neighbour_macros(arm),
        **panel_macros(arm),
    }
    return {f"\\{prefix}{k}": v for k, v in out.items()}


def ratios(first, second):
    """Second-arm-over-first-arm ratios the prose quotes as \"N times\"."""
    tests = [json.loads((VIZ / f"{a}_test.json").read_text()) for a in (first, second)]
    stats = [json.loads((VIZ / f"{a}_stats.json").read_text()) for a in (first, second)]
    spend = [cost_usd([c for c in s["llm_calls"] if c["ok"]]) for s in stats]
    gain = lambda t, k: t["best"][k] - t["seed"][k]  # noqa: E731
    work = lambda s: max(p["elapsed_s"] for p in s["programs"])  # noqa: E731
    return {
        "\\ratioCV": f"{gain(tests[1], 'cv_r2') / gain(tests[0], 'cv_r2'):.1f}",
        "\\ratioTest": f"{gain(tests[1], 'test_r2') / gain(tests[0], 'test_r2'):.1f}",
        "\\ratioSpend": f"{spend[1] / spend[0]:.1f}",
        "\\ratioWall": f"{stats[1]['run_seconds'] / stats[0]['run_seconds']:.1f}",
        "\\ratioWallWork": f"{work(stats[1]) / work(stats[0]):.1f}",
    }


def pooled(arms):
    """Numbers the prose quotes across all replicas at once."""
    stats = [json.loads((VIZ / f"{a}_stats.json").read_text()) for a in arms]
    nbrs = [json.loads((VIZ / f"{a}_neighbour.json").read_text()) for a in arms]
    tests = [json.loads((VIZ / f"{a}_test.json").read_text()) for a in arms]
    programs = [p for s in stats for p in s["programs"]]
    valid = [p for p in programs if p["is_valid"] == 1.0]
    calls = [c for s in stats for c in s["llm_calls"] if c["ok"]]
    best = max(tests, key=lambda t: t["best"]["cv_r2"])
    panel = [r for t in tests for r in t["panel"]]
    gaps = [
        t["best"]["test_r2"] - t["best_no_neighbour"]["test_r2"]
        for t in tests
        if t["best_no_neighbour"]
    ]
    rmse_gaps = [
        t["best"]["test_rmse"] - t["best_no_neighbour"]["test_rmse"]
        for t in tests
        if t["best_no_neighbour"]
    ]
    return {
        "\\allPanelScored": f"{len(panel)}",
        "\\allPanelNbr": f"{sum(r['neighbour'] for r in panel)}",
        "\\allPanelTopTest": f"{max(r['test_r2'] for r in panel):.6f}",
        "\\allPanelTestMin": f"{min(r['test_r2'] for r in panel):.6f}",
        "\\allPanelRho": f"{_spearman([r['cv_r2'] for r in panel], [r['test_r2'] for r in panel]):+.2f}",
        "\\allPanelBestRmse": f"{min(r['test_rmse'] for r in panel):.4f}",
        "\\allPanelWorstRmse": f"{max(r['test_rmse'] for r in panel):.4f}",
        "\\allPanelRmseRho": f"{_spearman([r['cv_r2'] for r in panel], [-r['test_rmse'] for r in panel]):+.2f}",
        "\\allNbrGapTestMean": f"{np.mean(gaps):+.6f}",
        "\\allNbrGapTestWins": f"{sum(g > 0 for g in gaps)}",
        "\\allNbrGapRmseMean": f"{np.mean(rmse_gaps):+.4f}",
        "\\allNbrGapRmseWins": f"{sum(g < 0 for g in rmse_gaps)}",
        "\\allReplicas": f"{len(arms)}",
        "\\allPrograms": f"{len(programs)}",
        "\\allValid": f"{len(valid)}",
        "\\allValidPct": f"{len(valid) / len(programs) * 100:.1f}\\%",
        "\\allNbrBuilt": f"{sum(n['with_neighbour'] for n in nbrs)}",
        "\\allNbrSup": f"{sum(n['with_supervised_neighbour'] for n in nbrs)}",
        "\\allNbrMention": f"{sum(n['mentions_neighbour'] for n in nbrs)}",
        "\\allNbrMentionOnly": f"{sum(n['mentions_but_not_built'] for n in nbrs)}",
        "\\allNbrAgg": f"{sum(n['with_aggregate'] for n in nbrs)}",
        "\\allNbrReplicas": f"{sum(n['with_neighbour'] > 0 for n in nbrs)}",
        "\\allChampReplicas": f"{sum(n['champion_has_neighbour'] for n in nbrs)}",
        "\\allBestCV": f"{best['best']['cv_r2']:.6f}",
        "\\allBestTest": f"{best['best']['test_r2']:.6f}",
        "\\allBestRmse": f"{best['best']['test_rmse']:.4f}",
        "\\allSpend": f"{cost_usd(calls):.2f}",
        "\\allCalls": f"{len(calls)}",
    }


def prior_macros(arms):
    """The pre-refactor runs, classified by the same detector as the new ones.

    The claim "the search never reached a neighbour feature" is only worth making
    if the old runs were measured, not remembered, so these come from re-running
    analyze_neighbour_features.py over the 2026-07-21 shakedown run directories.
    """
    nbrs = [json.loads((VIZ / f"{a}_neighbour.json").read_text()) for a in arms]
    return {
        "\\priorPrograms": f"{sum(n['programs'] for n in nbrs)}",
        "\\priorNbrBuilt": f"{sum(n['with_neighbour'] for n in nbrs)}",
        "\\priorNbrMention": f"{sum(n['mentions_neighbour'] for n in nbrs)}",
        "\\priorNbrAgg": f"{sum(n['with_aggregate'] for n in nbrs)}",
    }


def main() -> None:
    lines = ["% generated by make_numbers.py — do not edit"]
    for spec in sys.argv[1:]:
        arm, prefix = spec.split(":")
        for name, value in macros(arm, prefix).items():
            lines.append(f"\\newcommand{{{name}}}{{{value}}}")
    if len(sys.argv) > 3:
        for name, value in pooled([s.split(":")[0] for s in sys.argv[1:]]).items():
            lines.append(f"\\newcommand{{{name}}}{{{value}}}")
    prior = [
        a for a in ("pre_g3f", "pre_g35") if (VIZ / f"{a}_neighbour.json").exists()
    ]
    if prior:
        for name, value in prior_macros(prior).items():
            lines.append(f"\\newcommand{{{name}}}{{{value}}}")
    if len(sys.argv) == 3:
        arms = [spec.split(":")[0] for spec in sys.argv[1:]]
        for name, value in ratios(*arms).items():
            lines.append(f"\\newcommand{{{name}}}{{{value}}}")
    (HERE / "numbers.tex").write_text("\n".join(lines) + "\n")
    print(f"wrote numbers.tex ({len(lines) - 1} macros)")


if __name__ == "__main__":
    main()
