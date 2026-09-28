"""Extract the best program's ancestry from a dag_tab disk-storage run.

Writes viz/<arm>_lineage_NN_<gen>.json, one record per generation, each holding
the FeatureGraph genome, the mutator's own structured diff, and the fitness that
genome scored.  The renderers read only these records, so the figures can be
rebuilt without the run directory.

Usage: python extract_lineage.py <run_dir> <arm-slug>
"""

import json
from pathlib import Path
import sys

HERE = Path(__file__).parent
VIZ = HERE / "viz"


def load_programs(run_dir: Path) -> dict:
    root = run_dir / "storage" / "dag_tab" / "programs"
    out = {}
    for f in root.glob("*.json"):
        d = json.loads(f.read_text())
        out[d["id"]] = d
    return out


def best_program(programs: dict) -> dict:
    scored = [
        p
        for p in programs.values()
        if p["metrics"].get("is_valid", 0.0) == 1.0 and p["metrics"].get("fitness")
    ]
    return max(scored, key=lambda p: p["metrics"]["fitness"])


def ancestry(programs: dict, leaf: dict) -> list[dict]:
    chain = [leaf]
    seen = {leaf["id"]}
    node = leaf
    while True:
        parents = node["lineage"].get("parents") or []
        parents = [p for p in parents if p in programs and p not in seen]
        if not parents:
            break
        node = programs[parents[0]]
        seen.add(node["id"])
        chain.append(node)
    return list(reversed(chain))


def llm_diff(program: dict) -> dict:
    out = program["metadata"].get("mutation_output") or {}
    if not isinstance(out, dict):
        return {}
    return {
        "archetype": out.get("archetype") or out.get("structural_intent") or "",
        "base_parent": out.get("base_parent"),
        "changes": out.get("changes") or [],
        "insights_used": out.get("insights_used") or [],
    }


def record(program: dict) -> dict:
    return {
        "id": program["id"],
        "generation": program["lineage"].get("generation"),
        "iteration": program.get("iteration"),
        "fitness": program["metrics"].get("fitness"),
        "is_valid": program["metrics"].get("is_valid"),
        "node_count": program["metrics"].get("graph_node_count"),
        "max_depth": program["metrics"].get("graph_max_depth"),
        "generated_feature_count": program["metrics"].get("generated_feature_count"),
        "graph": json.loads(program["code"]),
        "llm_diff": llm_diff(program),
    }


def main() -> None:
    run_dir, arm = Path(sys.argv[1]), sys.argv[2]
    programs = load_programs(run_dir)
    leaf = best_program(programs)
    chain = ancestry(programs, leaf)
    VIZ.mkdir(exist_ok=True)
    for i, program in enumerate(chain):
        rec = record(program)
        path = VIZ / f"{arm}_lineage_{i:02d}_gen{rec['generation']}.json"
        path.write_text(json.dumps(rec, indent=1))
        print(
            f"{path.name}  id={rec['id'][:8]}  fitness={rec['fitness']:.6f}  "
            f"nodes={rec['node_count']:.0f}  depth={rec['max_depth']:.0f}"
        )


if __name__ == "__main__":
    main()
