"""Regenerate report figures from ab_stats.json.

Usage: python make_figures.py  (run inside report_full100/)
Invalid children carry sentinel fitness -1000; they are drawn as crosses at y=0,
not on the fitness scale.
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLORS = {"A": "#B42318", "B": "#1F4E79"}
LABELS = {"A": "arm A (full wire-JSON rewrite)", "B": "arm B (structured slot diff)"}

stats = json.load(open("ab_stats.json"))
arms = {"A": stats["A_full_rewrite"], "B": stats["B_structured_diff"]}

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

for key, s in arms.items():
    children = [t for t in s["trajectory"] if not t["is_seed"]]
    xs_valid, ys_valid, xs_bad, best_line = [], [], [], []
    best = max(t["fitness"] for t in s["trajectory"] if t["is_seed"])
    for i, t in enumerate(children, start=1):
        if t["fitness"] < 0:
            xs_bad.append(i)
        else:
            xs_valid.append(i)
            ys_valid.append(t["fitness"])
            best = max(best, t["fitness"])
        best_line.append(best)
    ax1.scatter(
        xs_valid, ys_valid, s=14, alpha=0.55, color=COLORS[key], label=LABELS[key]
    )
    ax1.plot(range(1, len(children) + 1), best_line, color=COLORS[key], lw=1.8)
    if xs_bad:
        ax1.scatter(
            xs_bad,
            [0.0] * len(xs_bad),
            marker="x",
            s=40,
            color=COLORS[key],
            label=f"invalid child (arm {key})",
        )
ax1.set_xlabel("persisted child #")
ax1.set_ylabel("ROUGE-L fitness")
ax1.set_title("Per-child fitness (dots) and best-so-far (line)")
ax1.set_ylim(-0.03, 0.6)
ax1.legend(fontsize=8, loc="lower right")
ax1.grid(alpha=0.25)

funnel = [
    ("mutation\nattempts", "mutation_attempts_logged"),
    ("persisted\nchildren", "children_stored"),
    ("valid\nchildren", "children_valid"),
]
x = range(len(funnel))
w = 0.38
for off, key in ((-w / 2, "A"), (w / 2, "B")):
    vals = [arms[key][f] for _, f in funnel]
    bars = ax2.bar([i + off for i in x], vals, w, color=COLORS[key], label=LABELS[key])
    ax2.bar_label(bars, fontsize=9)
ax2.set_xticks(list(x), [n for n, _ in funnel])
ax2.set_title("Validity funnel")
ax2.set_ylim(0, 125)
ax2.legend(fontsize=8, loc="lower left")

fig.tight_layout()
fig.savefig("ab_overview.png", dpi=160)

fig2, ax = plt.subplots(figsize=(7, 3.6))
lengths = range(1, 9)
for off, key in ((-w / 2, "A"), (w / 2, "B")):
    counts = [arms[key]["n_steps"].get(str(n), 0) for n in lengths]
    bars = ax.bar(
        [n + off for n in lengths], counts, w, color=COLORS[key], label=LABELS[key]
    )
    ax.bar_label(bars, fontsize=8, labels=[c or "" for c in counts])
ax.set_xlabel("chain length (steps)")
ax.set_ylabel("valid children")
ax.set_title("Structural exploration: chain-length distribution")
ax.set_xticks(list(lengths))
ax.legend(fontsize=8)
fig2.tight_layout()
fig2.savefig("ab_nsteps.png", dpi=160)

calls = json.load(open("mutation_tokens_per_call.json"))
fig3, (ax3, ax4) = plt.subplots(1, 2, figsize=(12, 4.5))
for key in ("A", "B"):
    xs = range(1, len(calls[key]) + 1)
    outs = [c["tokens_out"] for c in calls[key]]
    ins = [c["tokens_in"] for c in calls[key]]
    ax3.scatter(xs, outs, s=14, alpha=0.55, color=COLORS[key], label=LABELS[key])
    window = 10
    roll = [
        sum(outs[max(0, i - window) : i]) / len(outs[max(0, i - window) : i])
        for i in range(1, len(outs) + 1)
    ]
    ax3.plot(xs, roll, color=COLORS[key], lw=1.8)
    cum_out, cum_in, t_out, t_in = [], [], 0, 0
    for c in calls[key]:
        t_out += c["tokens_out"]
        t_in += c["tokens_in"]
        cum_out.append(t_out / 1000)
        cum_in.append(t_in / 1000)
    ax4.plot(xs, cum_out, color=COLORS[key], lw=1.8, label=f"{LABELS[key]} — out")
    ax4.plot(
        xs, cum_in, color=COLORS[key], lw=1.2, ls="--", label=f"{LABELS[key]} — in"
    )
ax3.set_xlabel("mutation call #")
ax3.set_ylabel("output tokens")
ax3.set_title("Mutation output tokens per call (line: 10-call rolling mean)")
ax3.legend(fontsize=8)
ax3.grid(alpha=0.25)
ax4.set_xlabel("mutation call #")
ax4.set_ylabel("cumulative tokens (thousands)")
ax4.set_title("Cumulative mutation tokens")
ax4.legend(fontsize=8, loc="upper left")
ax4.grid(alpha=0.25)
fig3.tight_layout()
fig3.savefig("ab_tokens.png", dpi=160)
print("wrote ab_overview.png, ab_nsteps.png, ab_tokens.png")
