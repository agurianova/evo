"""Freeze the two CV-selected Higgs FeatureGraphs from evolution storage."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_IDS = {
    "catboost": "beebd311-d416-4fea-9fa9-d59549751ec8",
    "tabm": "5d2ec2ca-f2cb-46aa-8815-3375d4bc2a36",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_program(path: Path, model: str) -> tuple[dict, dict, bytes]:
    source = path.read_bytes()
    program = json.loads(source)
    if program["id"] != EXPECTED_IDS[model]:
        raise ValueError(
            f"{model} winner mismatch: expected {EXPECTED_IDS[model]}, "
            f"found {program['id']}"
        )
    graph = json.loads(program["code"])
    if graph["dataset"] != "higgs-small":
        raise ValueError(f"{model} winner targets {graph['dataset']!r}")
    if program["metrics"].get("is_valid") != 1.0:
        raise ValueError(f"{model} winner is not valid")
    return program, graph, source


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catboost-program", type=Path, required=True)
    parser.add_argument("--tabm-program", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    loaded = {
        model: _load_program(getattr(args, f"{model}_program"), model)
        for model in EXPECTED_IDS
    }
    catboost_graph = loaded["catboost"][1]
    tabm_graph = loaded["tabm"][1]
    contract_fields = (
        "schema_version",
        "dataset",
        "raw_columns",
        "dropped_raw_columns",
    )
    for field in contract_fields:
        if catboost_graph[field] != tabm_graph[field]:
            raise ValueError(f"winner contract mismatch for {field}")
    if catboost_graph.get("target") != tabm_graph.get("target"):
        raise ValueError("winner target transforms differ")

    graph_dir = args.output_dir / "graphs"
    graph_dir.mkdir(parents=True, exist_ok=True)
    graph_payloads = {
        "raw": {
            **{field: catboost_graph[field] for field in contract_fields},
            "target": catboost_graph.get("target"),
            "nodes": [],
        },
        "catboost": catboost_graph,
        "tabm": tabm_graph,
    }
    graph_hashes = {}
    for model, graph in graph_payloads.items():
        rendered = (json.dumps(graph, indent=2) + "\n").encode()
        (graph_dir / f"{model}.json").write_bytes(rendered)
        graph_hashes[model] = _sha256(rendered)

    provenance = {
        "selection": "maximum valid three-fold CV accuracy",
        "test_labels_used_for_selection": False,
        "programs": {},
        "graph_sha256": graph_hashes,
    }
    for model, (program, _graph, source) in loaded.items():
        provenance["programs"][model] = {
            "id": program["id"],
            "iteration": program["iteration"],
            "generation": program["lineage"]["generation"],
            "metrics": program["metrics"],
            "source_program_sha256": _sha256(source),
        }
    (args.output_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
