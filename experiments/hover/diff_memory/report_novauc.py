#!/usr/bin/env python3
"""NOVAUC closeout PDF: prereg endpoints, fitness stats, D1 re-evals,
trajectories. Reuses closeout_novauc.py's replay + loaders (one code path)."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from closeout_novauc import ARMS, ROOT, fitness_deltas, load_programs, replay, share
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import mannwhitneyu

HERE = Path(__file__).parent
OUT = HERE / "novauc_closeout_20260711.pdf"


def trajectory(label):
    rows = []
    for f in (ROOT / ARMS[label] / "storage/chains_hover_full7/programs").glob(
        "*.json"
    ):
        d = json.loads(f.read_text())
        fit = d.get("metrics", {}).get("fitness")
        if fit is not None and d.get("metrics", {}).get("is_valid") == 1.0:
            rows.append((d.get("created_at", ""), fit))
    rows.sort()
    best, out = 0.0, []
    for _, fit in rows:
        best = max(best, fit)
        out.append(best)
    return out


def main():
    rep = {label: replay(label, ARMS[label]) for label in ("NOVAUC_R1", "NOVAUC_R2")}
    deltas, pops = {}, {}
    for label, relpath in ARMS.items():
        progs = load_programs(relpath)
        deltas[label] = fitness_deltas(progs)
        pops[label] = [
            p["fitness"]
            for p in progs.values()
            if p["valid"] and p["fitness"] is not None
        ]
    nov_w = deltas["NOVAUC_R1"][0] + deltas["NOVAUC_R2"][0]
    nov_wo = deltas["NOVAUC_R1"][1] + deltas["NOVAUC_R2"][1]
    mem_w = deltas["MEM_R1"][0] + deltas["MEM_R2"][0]
    mem_wo = deltas["MEM_R1"][1] + deltas["MEM_R2"][1]
    p_s1 = mannwhitneyu(nov_w, mem_w, alternative="two-sided").pvalue
    p_within = mannwhitneyu(nov_w, nov_wo, alternative="two-sided").pvalue

    reeval = {}
    sink = HERE / "reeval_results.jsonl"
    if sink.exists():
        for line in sink.read_text().splitlines():
            r = json.loads(line)
            reeval[r["label"]] = r

    with PdfPages(OUT) as pdf:
        # Page 1: endpoint table
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis("off")
        lines = [
            "NOVAUC closeout — novelty-discounted auction bid (power=0.5), TS=20260711_115748",
            "Prereg: prereg_novelty_auction_20260711.md.  Control: MEM pair 20260710_041404.",
            "",
            "MECHANISM (own power=0 counterfactual replay; sanity 0 mismatched rounds both reps):",
        ]
        for label in ("NOVAUC_R1", "NOVAUC_R2"):
            r = rep[label]
            a_s, a_card, a_tot = share(r["actual"])
            c_s, _, c_tot = share(r["counterfactual"])
            lines += [
                f"  {label}: top-card share {c_s:.1%} -> {a_s:.1%} "
                f"(rel drop {(c_s - a_s) / c_s:+.1%});  volume {c_tot} -> {a_tot} "
                f"({a_tot / c_tot - 1:+.1%});  distinct {len(r['counterfactual'])} -> {len(r['actual'])};  "
                f"top={a_card[:36]}",
            ]
        lines += [
            "",
            "  P1 dominance:  CONFIRMED  (share lower both reps; rel drops -40.9% / -10.1%, both cf>12%)",
            "  P2 volume:     FALSIFIED in R1 (+19.1% vs bar ±10%; grew, did not shrink). R2 +0.5% ok.",
            "  P3 coverage:   CONFIRMED  (30>=27, 31>=31 distinct winners)",
            "  P4 dominance (cross-run, descriptive): max card 47x (R1) / 34x (R2) vs control 17/26.",
            "     ABOVE control range, below the >52 falsification bar. Probe lane active both reps",
            "     (66 / 65 fills; probe share of injections 22%/24% vs control 53%/27% — auction",
            "     volume grew, so probe fills fewer empty rounds).",
            "",
            "FITNESS (per-mutation delta = child - frozen parent fitness, valid children):",
            f"  NOVAUC with-card : n={len(nov_w)}  mean={np.mean(nov_w):+.4f}  sd={np.std(nov_w, ddof=1):.4f}",
            f"  NOVAUC without   : n={len(nov_wo)}  mean={np.mean(nov_wo):+.4f}  sd={np.std(nov_wo, ddof=1):.4f}",
            f"  MEM    with-card : n={len(mem_w)}  mean={np.mean(mem_w):+.4f}  sd={np.std(mem_w, ddof=1):.4f}",
            f"  MEM    without   : n={len(mem_wo)}  mean={np.mean(mem_wo):+.4f}  sd={np.std(mem_wo, ddof=1):.4f}",
            f"  S1 (NOVAUC-with vs MEM-with): MW p={p_s1:.3f} -> formally non-inferior (bar p<0.05),",
            "     but directionally worse, and the within-arm with-vs-without advantage",
            f"     collapsed (MW p={p_within:.3f}; control advantage was +0.021).",
            "",
            "  S2 valid-population fitness:",
        ]
        for label in ARMS:
            a = np.asarray(pops[label])
            lines += [
                f"    {label}: n={len(a)} mean={a.mean():.4f} sd={a.std(ddof=1):.4f}"
            ]
        lines += [
            "",
            "D1 best-of-run K=5 re-eval (controls: MEM 0.8298±0.0109 / 0.7893):",
        ]
        for label in ("NOVAUC_R1", "NOVAUC_R2"):
            r = reeval.get(label)
            if r:
                lines += [
                    f"  {label}: stored {r['stored_fitness']:.4f} -> re-eval "
                    f"{r['mean']:.4f} ± {r['sd']:.4f} (95% CI ±{r['ci95']:.4f}, K={r['k']})"
                ]
            else:
                lines += [f"  {label}: (re-eval pending)"]
        lines += [
            "",
            "VERDICT: mechanism works (P1/P3), but the redistribute-not-shrink property failed",
            "live in R1 (volume +19%) and the with-card fitness advantage collapsed — consistent",
            "with the prereg's riskiest link (rotation outpacing reputation sorting).",
            "DO NOT promote thompson_bootstrap_novelty to preset default; revisit the",
            "ev_floor_quantile coupling (tax drags the floor down -> extra marginal injections).",
        ]
        ax.text(
            0.02, 0.98, "\n".join(lines), va="top", family="monospace", fontsize=8.2
        )
        pdf.savefig(fig)
        plt.close(fig)

        # Page 2: trajectories
        fig, ax = plt.subplots(figsize=(11, 6))
        for label, color in zip(
            ARMS, ("tab:red", "tab:orange", "tab:blue", "tab:cyan")
        ):
            ax.plot(trajectory(label), label=label, color=color)
        ax.set_xlabel("valid program # (by created_at)")
        ax.set_ylabel("running best fitness")
        ax.set_title("Running best fitness — NOVAUC (novelty tax) vs MEM control")
        ax.legend()
        ax.grid(alpha=0.3)
        pdf.savefig(fig)
        plt.close(fig)

        # Page 3: with-card delta distributions
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
        for ax_i, (name, w, wo) in zip(
            axes, [("NOVAUC", nov_w, nov_wo), ("MEM control", mem_w, mem_wo)]
        ):
            bins = np.linspace(-0.5, 0.5, 41)
            ax_i.hist(w, bins=bins, alpha=0.6, label=f"with-card (n={len(w)})")
            ax_i.hist(wo, bins=bins, alpha=0.6, label=f"without (n={len(wo)})")
            ax_i.axvline(0, color="k", lw=0.8)
            ax_i.set_title(f"{name}: per-mutation fitness delta")
            ax_i.set_xlabel("child - parent fitness")
            ax_i.legend(fontsize=8)
        pdf.savefig(fig)
        plt.close(fig)

    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
