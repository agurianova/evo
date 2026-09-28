"""Rebuild Appendix H tables from saved expert-on validation traces.

Run scripts/unpack_paper_artifacts.py first. No test scores are read.
"""

from __future__ import annotations

from collections import defaultdict
import csv
from pathlib import Path
import statistics
import sys

from scipy.stats import binomtest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "blue_dream" / "code"))
import cluster_expert_on_similar_mutations as cluster  # noqa: E402
import expert_hypothesis_mutation_gains as expert  # noqa: E402

OUT = REPO / "analysis"
EXPERT = {
    "H1": "h1_surface",
    "H2": "h2_vregion",
    "H3": "h3_states",
    "H4": "h4_confidence",
}
AUTONOMOUS = {
    "A1": (
        "self.key = torch.nn.ModuleList",
        "self.value = torch.nn.ModuleList",
        "range(states)",
    ),
    "A2": ("for group in np.unique", "softplus", "mhc_epitope_id"),
}
EXPECTED = {
    "H1": (29, 19, 12),
    "H2": (20, 7, 2),
    "H3": (32, 13, 5),
    "H4": (69, 34, 16),
    "A1": (17, 8, 6),
    "A2": (18, 16, 9),
}


def write_table(name: str, fields: tuple[str, ...], rows: list[dict]) -> None:
    OUT.mkdir(exist_ok=True)
    with (OUT / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in fields} for row in rows)


def main() -> None:
    raw = [row for run in cluster.RUNS for row in cluster.load_run(run)]
    scored = [row for row in raw if row["scored"]]
    assert len(raw) == 500 and len(scored) == 435
    ids = {(r["run"], r["short"]): r["id"] for r in raw}
    parents = {(r["run"], r["parent_short"]): r["parent"] for r in raw}
    background = defaultdict(list)
    for row in scored:
        background[(row["run"], row["parent"])].append(row["delta"])
    assert len(background) == 96
    background_rows = []
    for (run, parent), values in sorted(background.items()):
        delta = statistics.median(values)
        background_rows.append(
            {
                "run": run,
                "parent_id": parent,
                "children": len(values),
                "median_delta": delta,
                "improved": int(delta > 0),
            }
        )
    successes = sum(row["improved"] for row in background_rows)
    assert successes == 35
    write_table(
        "parent_background.tsv",
        ("run", "parent_id", "children", "median_delta", "improved"),
        background_rows,
    )
    candidates = []
    for row in expert.load_all():
        if not row["scored"]:
            continue
        for name, label in EXPERT.items():
            if label in row["suggestion"] and label in row["code"]:
                candidates.append(
                    {
                        "class": name,
                        "run": row["run"],
                        "parent_id": parents[(row["run"], row["parent"])],
                        "child_id": ids[(row["run"], row["id"])],
                        "delta": row["delta"],
                    }
                )
    for row in scored:
        if len(cluster.tokens_of(row["added"])) < 12:
            continue
        for name, fragments in AUTONOMOUS.items():
            if all(fragment in row["added"] for fragment in fragments):
                candidates.append(
                    {
                        "class": name,
                        "run": row["run"],
                        "parent_id": row["parent"],
                        "child_id": row["id"],
                        "delta": row["delta"],
                    }
                )
    candidates.sort(key=lambda r: (r["class"], r["run"], r["parent_id"], r["child_id"]))
    write_table(
        "mutation_classes.tsv",
        ("class", "run", "parent_id", "child_id", "delta"),
        candidates,
    )
    grouped = defaultdict(list)
    for row in candidates:
        grouped[(row["class"], row["run"], row["parent_id"])].append(row["delta"])
    parent_rows = []
    for (name, run, parent), values in sorted(grouped.items()):
        delta = statistics.median(values)
        parent_rows.append(
            {
                "class": name,
                "run": run,
                "parent_id": parent,
                "children": len(values),
                "median_delta": delta,
                "improved": int(delta > 0),
            }
        )
    write_table(
        "parent_mutation_classes.tsv",
        ("class", "run", "parent_id", "children", "median_delta", "improved"),
        parent_rows,
    )
    summary = []
    for name in EXPECTED:
        members = [row for row in candidates if row["class"] == name]
        group = [row for row in parent_rows if row["class"] == name]
        improved = sum(row["improved"] for row in group)
        got = (len(members), len(group), improved)
        assert got == EXPECTED[name], (name, got)
        medians = {
            run: statistics.median(
                row["median_delta"] for row in group if row["run"] == run
            )
            for run in sorted({row["run"] for row in group})
        }
        raw_p = binomtest(improved, len(group), successes / len(background)).pvalue
        summary.append(
            {
                "class": name,
                "mutations": len(members),
                "parents": len(group),
                "improved": improved,
                "raw_p": raw_p,
                "holm_p": None,
                **{f"r{run}_median": medians.get(run) for run in range(1, 6)},
            }
        )
    order = sorted(range(len(summary)), key=lambda index: summary[index]["raw_p"])
    adjusted = 0.0
    for rank, index in enumerate(order):
        adjusted = max(
            adjusted,
            min(1.0, (len(summary) - rank) * summary[index]["raw_p"]),
        )
        summary[index]["holm_p"] = adjusted
    write_table(
        "class_summary.tsv",
        (
            "class",
            "mutations",
            "parents",
            "improved",
            "raw_p",
            "holm_p",
            "r1_median",
            "r2_median",
            "r3_median",
            "r4_median",
            "r5_median",
        ),
        summary,
    )
    assert round(min(row["holm_p"] for row in summary), 3) == 0.172
    print(
        "Appendix H reproduced:",
        len(candidates),
        "class mutations,",
        len(parent_rows),
        "class parents,",
        len(background_rows),
        "background parents",
    )


if __name__ == "__main__":
    main()
