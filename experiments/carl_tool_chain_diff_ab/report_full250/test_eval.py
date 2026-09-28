"""Evaluate specific evolved chains (from disk storage) on the held-out HoVer test set.

Reuses the frozen test machinery in problems/chains/hover/full7/test.py — no eval
logic is re-implemented here. Reports discrete coverage (primary test metric: 1 iff
ALL gold titles retrieved) and soft coverage (for comparison with train fitness).

Usage:
  python test_eval.py <spec.json>
where spec.json = {"programs": [{"arm","label","run_dir","id"|"baseline":true}, ...],
                   "n_samples": 300, "max_concurrent": 24}
Writes test_metrics.json next to this script.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path
from statistics import mean
import sys

from problems.chains.chain_runner import run_chain_on_dataset_stepwise
from problems.chains.chain_validation import validate_chain_spec
from problems.chains.client import LLMClient
from problems.chains.hover.full7.config import FULL_CHAIN_CONFIG, load_baseline
from problems.chains.hover.full7.test import (
    evaluate_discrete_coverage_adaptive,
    load_test_context,
)
from problems.chains.hover.full7.validate import evaluate_soft_coverage_adaptive
from problems.chains.hover.shared_config import (
    get_llm_config,
    outer_context_builder,
)
from problems.chains.hover.utils.retrieval import make_retrieve_fn

HERE = Path(__file__).parent


def load_spec_json(run_dir: str, id_prefix: str) -> dict:
    matches = [
        f
        for f in glob.glob(f"{run_dir}/storage/*/programs/*.json")
        if Path(f).stem.startswith(id_prefix)
    ]
    if not matches:
        raise FileNotFoundError(f"no program {id_prefix} under {run_dir}")
    prog = json.loads(Path(matches[0]).read_text())
    return json.loads(prog["code"]), prog


def main() -> None:
    spec = json.loads(Path(sys.argv[1]).read_text())
    n_samples = spec.get("n_samples", 300)
    max_concurrent = spec.get("max_concurrent", 24)

    context = load_test_context(n_samples=n_samples)
    dataset = context["test_dataset"]
    client = LLMClient(**get_llm_config())
    # make_retrieve_fn is a batch fn (list[dict] -> list[str]) — dispatched
    # via batch_tool_registry, mirroring the production validate.py path.
    batch_tool_registry = {
        "retrieve": make_retrieve_fn(
            context["bm25s_index_dir"], k=7, corpus_path=context["corpus_path"]
        ),
        "retrieve_deep": make_retrieve_fn(
            context["bm25s_index_dir"], k=10, corpus_path=context["corpus_path"]
        ),
    }

    out = []
    for p in spec["programs"]:
        if p.get("baseline"):
            chain_spec, train_fit = load_baseline(), None
        else:
            chain_spec, prog = load_spec_json(p["run_dir"], p["id"])
            train_fit = (prog.get("metrics") or {}).get("fitness")
        chain = validate_chain_spec(
            chain_spec, mode="full_chain", full_chain_config=FULL_CHAIN_CONFIG
        )
        results = run_chain_on_dataset_stepwise(
            chain,
            client,
            dataset,
            outer_context_builder,
            batch_tool_registry=batch_tool_registry,
            max_concurrent=max_concurrent,
        )
        discrete = mean(evaluate_discrete_coverage_adaptive(dataset, results, chain))
        soft = mean(evaluate_soft_coverage_adaptive(dataset, results, chain))
        rec = {
            "arm": p["arm"],
            "label": p["label"],
            "id": p.get("id", "baseline"),
            "train_fitness_soft": train_fit,
            "test_soft_coverage": soft,
            "test_discrete_coverage": discrete,
            "n_test": len(dataset),
            "n_steps": len(chain.steps),
            "n_tool_steps": sum(1 for s in chain.steps if s.step_type == "tool"),
        }
        out.append(rec)
        print(
            f"[{rec['arm']}/{rec['label']}] train_soft={train_fit} "
            f"test_soft={soft:.4f} test_discrete={discrete:.4f} "
            f"(n={len(dataset)}, {rec['n_steps']}st/{rec['n_tool_steps']}tool)",
            flush=True,
        )
        (HERE / "test_metrics.json").write_text(json.dumps(out, indent=2))

    print("DONE -> test_metrics.json", flush=True)


if __name__ == "__main__":
    main()
