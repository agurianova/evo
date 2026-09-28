"""Fold the per-message invalid buckets into a families table for the report.

The report's claim is about *which layer* rejected a child, not about individual
messages, so the families are defined by the guard that fired. A message that no
family matches lands in "other" rather than being silently dropped — an
undercounted taxonomy would make the malformed-JSON row look better than it is.

Usage: python make_invalid_table.py <arm-slug>:<label> ...
"""

import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).parent
VIZ = HERE / "viz"

FAMILIES = [
    ("malformed JSON / schema violation", r"ValidationError|JSONDecode|malformed"),
    (
        "target transform/inverse: undefined or unbound name",
        r"target (transform|inverse): (name|cannot access local)",
    ),
    (
        "target transform/inverse: wrong output shape",
        r"target (transform|inverse): expected one-dimensional",
    ),
    ("target transform/inverse: no round-trip", r"round-trip"),
    ("node: declared columns not produced", r"missing declared outputs"),
    ("node: undeclared columns produced", r"created undeclared columns"),
    ("node: declared numerical, produced non-numeric", r"non-numeric dtype"),
    ("node: removed pre-existing columns", r"removed pre-existing columns"),
    (
        "own-target leakage (probe)",
        r"own-target leakage|split-dependent behavior",
    ),
    # Last: anything the executor raised from inside a node body that no specific
    # guard above claims. Ordinary Python errors in model-written code, not a
    # contract violation, so they must not inflate the contract rows.
    ("node body: Python error at execution", r"FeatureExecutionError: node "),
]


def family_counts(arm):
    buckets = json.loads((VIZ / f"{arm}_invalid.json").read_text())
    counts = dict.fromkeys([name for name, _ in FAMILIES] + ["other"], 0)
    for message, n in buckets:
        for name, pattern in FAMILIES:
            if re.search(pattern, message):
                counts[name] += n
                break
        else:
            counts["other"] += n
    return counts


def main() -> None:
    specs = [a.split(":", 1) for a in sys.argv[1:]]
    arms = [s[0] for s in specs]
    labels = [s[1] if len(s) > 1 else s[0] for s in specs]
    per_arm = [family_counts(a) for a in arms]

    rows = [
        "\\begin{tabular}{l" + "r" * len(labels) + "}",
        "\\toprule",
        "rejecting guard & " + " & ".join(labels) + " \\\\",
        "\\midrule",
    ]
    for name in list(dict.fromkeys([n for n, _ in FAMILIES] + ["other"])):
        cells = [str(c[name]) for c in per_arm]
        if all(v == "0" for v in cells) and name == "other":
            continue
        label = (
            name
            if name != "malformed JSON / schema violation"
            else "\\textbf{malformed JSON / schema violation}"
        )
        rows.append(f"{label} & " + " & ".join(cells) + " \\\\")
    rows.append("\\midrule")
    rows.append(
        "total invalid & " + " & ".join(str(sum(c.values())) for c in per_arm) + " \\\\"
    )
    rows.append("\\bottomrule")
    rows.append("\\end{tabular}")
    (HERE / "invalid_table.tex").write_text("\n".join(rows) + "\n")
    print("\n".join(rows))


if __name__ == "__main__":
    main()
