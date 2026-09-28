"""Decide, per genome, whether the search actually built a neighbour feature.

The question this run exists to answer is whether removing the death classes lets
the search reach kNN-shaped features at all. Answering it by grepping for "knn"
would count a variable name as a capability, so the classifier reads the node's
AST and asks what the code *computes*:

  library   -- imports or calls a neighbour primitive (sklearn.neighbors,
               scipy.spatial, pairwise distances). Unambiguous.
  handrolled-- computes a distance AND ranks or selects on it (argsort,
               argpartition, searchsorted, topk). This is a kNN by construction
               even with no library involved.
  none      -- neither, whatever the identifiers are called.

A neighbour node is `supervised` when it is an aggregate node, since only the
aggregate ABI receives y_fit: a neighbour-average-of-target feature must be
aggregate, a neighbour-average-of-X feature need not be.

Every node in a graph reaches the estimator -- `FeatureGraph.estimator_columns`
(graph.py) unions every node's output_cols into the scored frame -- so presence
in a genome is presence on the scoring path, and no separate reachability test
is needed.

Usage: python analyze_neighbour_features.py <run_dir> <arm-slug> ...
"""

import ast
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).parent
VIZ = HERE / "viz"

NEIGHBOUR_MODULES = (
    "sklearn.neighbors",
    "scipy.spatial",
    "sklearn.metrics.pairwise",
)
NEIGHBOUR_SYMBOLS = {
    "NearestNeighbors",
    "KNeighborsRegressor",
    "KNeighborsClassifier",
    "KNeighborsTransformer",
    "RadiusNeighborsRegressor",
    "KDTree",
    "BallTree",
    "cKDTree",
    "kneighbors",
    "query_ball_point",
    "query_ball_tree",
    "cdist",
    "pdist",
    "distance_matrix",
    "pairwise_distances",
    "euclidean_distances",
    "haversine_distances",
}
DISTANCE_SYMBOLS = {"norm", "hypot", "cdist", "pdist", "euclidean", "sqeuclidean"}
RANK_SYMBOLS = {"argsort", "argpartition", "searchsorted", "topk", "nsmallest"}

# Intent, not implementation: prose anywhere in the program record that proposes a
# neighbour feature. Tracked separately because a genome that *talks* about kNN and
# ships a ratio has failed at a different step than one that never considers it.
MENTION = re.compile(
    r"nearest[ -]?neighbou?r|k-?nn\b|kneighbors|NearestNeighbors|KDTree|BallTree",
    re.IGNORECASE,
)


def _attr_names(tree: ast.AST) -> set[str]:
    """Every attribute and bare name the code touches, e.g. `np.argsort` -> argsort."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            out.add(node.attr)
        elif isinstance(node, ast.Name):
            out.add(node.id)
    return out


def _has_squared_difference(tree: ast.AST) -> bool:
    """`(a - b) ** 2` -- a hand-rolled euclidean distance with no library call."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Pow)
            and isinstance(node.left, ast.BinOp)
            and isinstance(node.left.op, ast.Sub)
        ):
            return True
    return False


def classify_node(code: str) -> dict:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"tier": "unparseable", "evidence": []}

    evidence = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith(NEIGHBOUR_MODULES):
                evidence.append(f"from {node.module}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(NEIGHBOUR_MODULES):
                    evidence.append(f"import {alias.name}")

    names = _attr_names(tree)
    evidence += sorted(names & NEIGHBOUR_SYMBOLS)
    if evidence:
        return {"tier": "library", "evidence": sorted(set(evidence))}

    ranks = sorted(names & RANK_SYMBOLS)
    dists = sorted(names & DISTANCE_SYMBOLS)
    if ranks and (dists or _has_squared_difference(tree)):
        return {
            "tier": "handrolled",
            "evidence": ranks + dists + (["(a-b)**2"] if not dists else []),
        }
    return {"tier": "none", "evidence": []}


def _strings(obj) -> list[str]:
    if isinstance(obj, dict):
        return [s for v in obj.values() for s in _strings(v)]
    if isinstance(obj, list):
        return [s for v in obj for s in _strings(v)]
    return [obj] if isinstance(obj, str) else []


def analyse_program(program: dict) -> dict:
    graph = json.loads(program["code"])
    nodes = []
    for node in graph.get("nodes", []):
        verdict = classify_node(node.get("code", ""))
        nodes.append(
            {
                "id": node.get("id"),
                "kind": node.get("kind"),
                "output_cols": node.get("output_cols", []),
                **verdict,
            }
        )
    hits = [n for n in nodes if n["tier"] in ("library", "handrolled")]
    return {
        "id": program["id"],
        "generation": program["lineage"].get("generation"),
        "fitness": program["metrics"].get("fitness"),
        "is_valid": program["metrics"].get("is_valid"),
        "created_at": program["created_at"],
        "neighbour_nodes": hits,
        "has_neighbour": bool(hits),
        "has_supervised_neighbour": any(n["kind"] == "aggregate" for n in hits),
        "mentions_neighbour": any(MENTION.search(s) for s in _strings(program)),
        "node_count": len(nodes),
        "aggregate_count": sum(n["kind"] == "aggregate" for n in nodes),
    }


def main() -> None:
    run_dir, arm = Path(sys.argv[1]), sys.argv[2]
    root = run_dir / "storage" / "dag_tab" / "programs"
    rows = []
    for f in sorted(root.glob("*.json")):
        program = json.loads(f.read_text())
        if "is_valid" not in program["metrics"]:
            continue
        rows.append(analyse_program(program))
    rows.sort(key=lambda r: r["created_at"])

    valid = [r for r in rows if r["is_valid"] == 1.0]
    with_n = [r for r in rows if r["has_neighbour"]]
    valid_n = [r for r in valid if r["has_neighbour"]]
    champion = max(valid, key=lambda r: r["fitness"]) if valid else None

    summary = {
        "arm": arm,
        "programs": len(rows),
        "valid": len(valid),
        "with_neighbour": len(with_n),
        "valid_with_neighbour": len(valid_n),
        "with_supervised_neighbour": sum(r["has_supervised_neighbour"] for r in rows),
        "mentions_neighbour": sum(r["mentions_neighbour"] for r in rows),
        "mentions_but_not_built": sum(
            r["mentions_neighbour"] and not r["has_neighbour"] for r in rows
        ),
        "with_aggregate": sum(r["aggregate_count"] > 0 for r in rows),
        "valid_with_supervised_neighbour": sum(
            r["has_supervised_neighbour"] for r in valid_n
        ),
        "first_neighbour_index": next(
            (i for i, r in enumerate(rows) if r["has_neighbour"]), None
        ),
        "best_neighbour_fitness": max((r["fitness"] for r in valid_n), default=None),
        "champion_has_neighbour": bool(champion and champion["has_neighbour"]),
        "champion_fitness": champion["fitness"] if champion else None,
        "champion_id": champion["id"] if champion else None,
        "programs_detail": rows,
    }
    VIZ.mkdir(exist_ok=True)
    (VIZ / f"{arm}_neighbour.json").write_text(json.dumps(summary, indent=1))
    print(
        f"{arm}: {len(rows)} programs, {len(with_n)} with a neighbour feature "
        f"({len(valid_n)} of them valid), supervised {summary['with_supervised_neighbour']}, "
        f"mentions {summary['mentions_neighbour']} (built none in {summary['mentions_but_not_built']}), "
        f"aggregate {summary['with_aggregate']}, "
        f"champion_has_neighbour={summary['champion_has_neighbour']}, "
        f"best neighbour fitness {summary['best_neighbour_fitness']}"
    )


CONTROLS = [
    (
        "library",
        "from sklearn.neighbors import NearestNeighbors\n"
        "def transform(df_fit, y_fit, df):\n"
        "    nn = NearestNeighbors(n_neighbors=10).fit(df_fit[['x6','x7']])\n"
        "    d, i = nn.kneighbors(df[['x6','x7']])\n"
        "    df['fe_knn'] = y_fit[i].mean(axis=1)\n"
        "    return df\n",
    ),
    (
        "handrolled",
        "import numpy as np\n"
        "def transform(df_fit, y_fit, df):\n"
        "    d = (df[['x6']].values - df_fit[['x6']].values.T) ** 2\n"
        "    idx = np.argsort(d, axis=1)[:, :10]\n"
        "    df['fe_knn'] = y_fit[idx].mean(axis=1)\n"
        "    return df\n",
    ),
    (
        "none",
        "def transform(df):\n"
        "    knn_ratio = df['x0'] / df['x1']  # named knn, computes a ratio\n"
        "    df['fe_ratio'] = knn_ratio\n"
        "    return df\n",
    ),
    (
        "none",
        "import numpy as np\n"
        "def transform(df):\n"
        "    df['fe_rank'] = np.argsort(df['x0'].values)  # ranks, no distance\n"
        "    return df\n",
    ),
]


def selftest() -> None:
    """The classifier's own precision check: a name is not a capability."""
    ok = True
    for expected, code in CONTROLS:
        got = classify_node(code)
        flag = "PASS" if got["tier"] == expected else "FAIL"
        ok &= got["tier"] == expected
        print(
            f"  {flag}  expected {expected:<10} got {got['tier']:<10} {got['evidence']}"
        )
    print("controls:", "all pass" if ok else "FAILURES PRESENT")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--selftest"]:
        selftest()
    else:
        main()
