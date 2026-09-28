"""Score an arm's finalists on the untouched test split.

Runs the same `problems.dag_tab.validate.score_on_test` entry point the framework
ships, so the reported test numbers come from the delegated `problems/tabular`
protocol rather than a re-implementation in the report.

Beyond the seed and the champion, this scores the top-K genomes by CV plus the
best genome that contains NO neighbour feature. If the run records grounded Memory
V2 citations, it also scores the best explicitly card-assisted genome. Selection
ran against CV, so the champion's test number alone cannot separate "the capability
generalises" from "one lucky draw out of a hundred": the panel shows whether the
whole CV-top of the run holds up out of sample, and the best-without-neighbour entry
is the head-to-head the capability claim actually rests on.

Must be run from the gigaevo checkout that produced the run (imports the problem
package) with GIGAEVO_TABULAR_DATA set.

Usage: python score_finalists.py <run_dir> <arm-slug> <report_dir> [top_k]
"""

import json
from pathlib import Path
import sys

from analyze_neighbour_features import classify_node

from problems.dag_tab.validate import score_on_test

TOP_K = 10


def load_programs(run_dir: Path) -> list[dict]:
    root = run_dir / "storage" / "dag_tab" / "programs"
    return [json.loads(f.read_text()) for f in root.glob("*.json")]


def has_neighbour(program: dict) -> bool:
    graph = json.loads(program["code"])
    return any(
        classify_node(node.get("code", ""))["tier"] in ("library", "handrolled")
        for node in graph.get("nodes", [])
    )


def memory_card_ids_used(program: dict) -> list[str]:
    """Return grounded card citations recorded by the structured mutator."""

    mutation = program.get("metadata", {}).get("mutation_output", {})
    return list(mutation.get("card_ids_used") or [])


def score(program: dict) -> dict:
    return {
        "id": program["id"],
        "cv_r2": program["metrics"]["fitness"],
        "generation": program["lineage"].get("generation"),
        "neighbour": has_neighbour(program),
        "memory_card_ids_used": memory_card_ids_used(program),
        **score_on_test(json.loads(program["code"])),
    }


def main() -> None:
    run_dir, arm, report_dir = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    top_k = int(sys.argv[4]) if len(sys.argv) > 4 else TOP_K
    programs = load_programs(run_dir)
    valid = [p for p in programs if p["metrics"].get("is_valid") == 1.0]
    by_cv = sorted(valid, key=lambda p: p["metrics"]["fitness"], reverse=True)
    seed = min(valid, key=lambda p: p["created_at"])

    panel = [score(p) for p in by_cv[:top_k]]
    scored = {row["id"] for row in panel}
    no_nbr = next((p for p in by_cv if not has_neighbour(p)), None)
    if no_nbr is not None and no_nbr["id"] not in scored:
        panel.append(score(no_nbr))

    explicit = next((p for p in by_cv if memory_card_ids_used(p)), None)
    explicit_score = None
    if explicit is not None:
        explicit_score = next((r for r in panel if r["id"] == explicit["id"]), None)
        if explicit_score is None:
            explicit_score = score(explicit)

    out = {
        "seed": score(seed),
        "best": panel[0],
        "best_no_neighbour": next((r for r in panel if not r["neighbour"]), None),
        "best_explicit_memory": explicit_score,
        "panel": panel,
    }
    path = report_dir / "viz" / f"{arm}_test.json"
    path.write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
