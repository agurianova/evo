#!/usr/bin/env python3
"""Evaluate stored chain programs on the HoVer TEST split with the hard metric.

Usage: eval_test_hard.py <label>:<program_json_path> [...] [--k 3]

Hard metric = discrete retrieval coverage (1 iff ALL gold articles found,
problems/chains/hover/full7/test.py); soft (fractional) coverage is reported
alongside for comparison with in-run fitness. Per-repeat scores, mean, SD and
a normal-approx 95% CI are printed and appended to test_eval_results.jsonl in
this directory. Requires HOVER_CHAIN_URL/HOVER_CHAIN_MODEL in the env (the
run's latest_*.env values).
"""

from datetime import UTC, datetime
import json
from pathlib import Path
from statistics import mean
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from problems.chains.chain_runner import run_chain_on_dataset_stepwise
from problems.chains.chain_validation import validate_chain_spec
from problems.chains.client import LLMClient
from problems.chains.hover.full7.config import FULL_CHAIN_CONFIG
from problems.chains.hover.full7.test import (
    evaluate_discrete_coverage_adaptive,
    load_test_context,
)
from problems.chains.hover.full7.validate import evaluate_soft_coverage_adaptive
from problems.chains.hover.shared_config import get_llm_config, outer_context_builder
from problems.chains.hover.utils.retrieval import make_retrieve_fn

HERE = Path(__file__).parent


def main():
    argv = sys.argv[1:]
    k = 3
    if "--k" in argv:
        i = argv.index("--k")
        k = int(argv[i + 1])
        del argv[i : i + 2]
    specs = [a for a in argv if not a.startswith("--")]

    context = load_test_context()
    dataset = context["test_dataset"]
    # Batch fns (list[dict] -> list[str]) dispatched via batch_tool_registry,
    # mirroring full7/validate.py — NOT the per-sample tool registry.
    batch_tool_registry = {
        "retrieve": make_retrieve_fn(
            context["bm25s_index_dir"], k=7, corpus_path=context["corpus_path"]
        ),
        "retrieve_deep": make_retrieve_fn(
            context["bm25s_index_dir"], k=10, corpus_path=context["corpus_path"]
        ),
    }
    sink = HERE / "test_eval_results.jsonl"

    for spec in specs:
        label, path = spec.split(":", 1)
        prog = json.loads(Path(path).read_text())
        chain = validate_chain_spec(
            json.loads(prog["code"]),
            mode="full_chain",
            full_chain_config=FULL_CHAIN_CONFIG,
        )
        stored = prog.get("metrics", {}).get("fitness")
        hard_runs, soft_runs = [], []
        for rep in range(1, k + 1):
            client = LLMClient(**get_llm_config())
            results = run_chain_on_dataset_stepwise(
                chain,
                client,
                dataset,
                outer_context_builder,
                batch_tool_registry=batch_tool_registry,
            )
            hard = mean(evaluate_discrete_coverage_adaptive(dataset, results, chain))
            soft = mean(evaluate_soft_coverage_adaptive(dataset, results, chain))
            hard_runs.append(hard)
            soft_runs.append(soft)
            print(f"{label} rep {rep}/{k}: hard={hard:.4f} soft={soft:.4f}", flush=True)
        h = np.asarray(hard_runs)
        s = np.asarray(soft_runs)
        h_sd = h.std(ddof=1) if k > 1 else 0.0
        ci = 1.96 * h_sd / np.sqrt(k) if k > 1 else 0.0
        rec = {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "label": label,
            "program_id": prog["id"],
            "stored_fitness_soft_train": stored,
            "n_test_samples": len(dataset),
            "k": k,
            "hard": hard_runs,
            "hard_mean": h.mean(),
            "hard_sd": h_sd,
            "hard_ci95": ci,
            "soft": soft_runs,
            "soft_mean": s.mean(),
        }
        with open(sink, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
        print(
            f"{label}: TEST hard={h.mean():.4f} sd={h_sd:.4f} 95%CI ±{ci:.4f} | "
            f"soft={s.mean():.4f} | stored train soft={stored:.4f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
