#!/usr/bin/env python3
"""K-times val re-eval of stored chain programs WITH per-claim score vectors.

Usage: reeval_winners_vec.py <label>:<program_json_path> [...] [--k 5]

Mirrors the eval-noise study protocol exactly (same load_context(n_samples=300)
train subset, evaluate_soft_coverage_adaptive per-claim scores, round-robin
reps so partial results carry equal replicates). Per-eval fitness + 300-claim
score vectors are saved incrementally to reeval_results_vec.json, matching the
prior_reeval/*.json schema so paired per-sample tests vs the prior winners
pair by construction. Requires HOVER_CHAIN_URL/HOVER_CHAIN_MODEL in the env.
"""

import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from problems.chains.chain_runner import run_chain_on_dataset_stepwise
from problems.chains.chain_validation import validate_chain_spec
from problems.chains.client import LLMClient
from problems.chains.hover.full7.config import FULL_CHAIN_CONFIG
from problems.chains.hover.full7.validate import evaluate_soft_coverage_adaptive
from problems.chains.hover.shared_config import (
    get_llm_config,
    load_context,
    outer_context_builder,
)
from problems.chains.hover.utils.retrieval import make_retrieve_fn

HERE = Path(__file__).parent
OUT = HERE / "reeval_results_vec.json"


def main():
    argv = sys.argv[1:]
    k = 5
    if "--k" in argv:
        i = argv.index("--k")
        k = int(argv[i + 1])
        del argv[i : i + 2]
    specs = [a.split(":", 1) for a in argv if not a.startswith("--")]

    results = json.loads(OUT.read_text()) if OUT.exists() else {}
    progs = {}
    for label, path in specs:
        p = json.loads(Path(path).read_text())
        progs[label] = p
        results.setdefault(
            label,
            {
                "in_run_fitness": p["metrics"]["fitness"],
                "program_id": p["id"],
                "evals": [],
            },
        )

    print("loading context + BM25 index ...", flush=True)
    context = load_context(n_samples=300)
    dataset = context["train_dataset"]
    batch_tool_registry = {
        "retrieve": make_retrieve_fn(
            context["bm25s_index_dir"], k=7, corpus_path=context["corpus_path"]
        ),
        "retrieve_deep": make_retrieve_fn(
            context["bm25s_index_dir"], k=10, corpus_path=context["corpus_path"]
        ),
    }
    print("context ready", flush=True)

    for rep in range(k):
        for label, _ in specs:
            if len(results[label]["evals"]) > rep:
                continue
            chain_spec = json.loads(progs[label]["code"])
            chain = validate_chain_spec(
                chain_spec, mode="full_chain", full_chain_config=FULL_CHAIN_CONFIG
            )
            client = LLMClient(**get_llm_config())
            t0 = time.time()
            res = run_chain_on_dataset_stepwise(
                chain,
                client,
                dataset,
                outer_context_builder,
                batch_tool_registry=batch_tool_registry,
            )
            scores = evaluate_soft_coverage_adaptive(dataset, res, chain)
            fit = sum(scores) / len(scores)
            results[label]["evals"].append(
                {"fitness": fit, "wall_s": round(time.time() - t0, 1), "scores": scores}
            )
            tmp = OUT.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(results))
            tmp.replace(OUT)
            print(
                f"rep {rep + 1}/{k} {label}: fitness {fit:.4f} "
                f"(in-run {results[label]['in_run_fitness']:.4f}) "
                f"[{time.time() - t0:.0f}s]",
                flush=True,
            )

    print("done")


if __name__ == "__main__":
    main()
