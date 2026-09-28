#!/usr/bin/env python3
# ruff: noqa: E402  -- proxy env vars must be set before imports
"""Experiment 0: Baseline evaluation of best program on test and validation sets.

This script:
1. Loads the best evolved program from a saved .py file
2. Evaluates it on the test set (300 samples) or validation set (300 samples)
3. Uses step-batched execution for efficiency
4. Reports EM score and extraction failure rate

Usage:
    # Test set evaluation
    PYTHONPATH=. python experiments/hotpotqa_improvement/exp0_baseline/evaluate.py \
        --program experiments/hotpotqa_improvement/exp0_baseline/rank01_0.6267_ddce37b4.py \
        --split test

    # Validation set evaluation (for variance measurement)
    PYTHONPATH=. python experiments/hotpotqa_improvement/exp0_baseline/evaluate.py \
        --program experiments/hotpotqa_improvement/exp0_baseline/rank01_0.6267_ddce37b4.py \
        --split val
"""

import argparse
import os
import time

# Bypass system proxy for internal LLM endpoints.
# httpx does not reliably parse CIDR notation in NO_PROXY — use exact IPs.
_no_proxy = os.environ.get("NO_PROXY", "")
_llm_ips = ["10.226.17.25"]  # chain-execution vLLM servers
for _ip in _llm_ips:
    if _ip not in _no_proxy:
        _no_proxy = ",".join(filter(None, [_no_proxy, _ip]))
os.environ["NO_PROXY"] = _no_proxy
os.environ["no_proxy"] = _no_proxy

from problems.chains.chain_runner import run_chain_on_dataset_stepwise
from problems.chains.chain_validation import validate_chain_spec
from problems.chains.client import LLMClient
from problems.chains.hotpotqa.shared_config import (
    BM25S_INDEX_DIR,
    CORPUS_PATH,
    DATASET_CONFIG,
    LLM_CONFIG,
    load_jsonl,
    outer_context_builder,
    preprocess_sample,
)
from problems.chains.hotpotqa.static.config import STATIC_CHAIN_TOPOLOGY, load_baseline
from problems.chains.hotpotqa.static.validate import (
    calculate_exact_match,
    extract_answer,
)
from problems.chains.hotpotqa.utils.retrieval import batch_retrieve


def load_program_from_file(path: str) -> dict:
    """Load chain spec from a saved program .py file."""
    with open(path) as f:
        code = f.read()
    exec_globals = {}
    exec(code, exec_globals)
    return exec_globals["entrypoint"]()


def evaluate(
    program_path: str,
    split: str = "test",
    n_samples: int | None = None,
    llm_base_url: str | None = None,
) -> dict:
    """Evaluate a program on the specified split.

    Args:
        program_path: Path to .py file with entrypoint() function
        split: "test" or "val"
        n_samples: Number of samples to use (None = all)
        llm_base_url: Override LLM endpoint (default: from LLM_CONFIG)

    Returns:
        Dict with exact_match, extraction_failures, wall_clock_seconds
    """
    # 1. Load program
    chain_spec = load_program_from_file(program_path)
    baseline = load_baseline()
    chain = validate_chain_spec(
        chain_spec,
        mode="static",
        topology=STATIC_CHAIN_TOPOLOGY,
        frozen_baseline=baseline,
    )

    # 2. Load dataset
    if split == "test":
        raw_samples = load_jsonl(DATASET_CONFIG["test_path"])
    elif split == "val":
        raw_samples = load_jsonl(DATASET_CONFIG["train_path"])
    else:
        raise ValueError(f"Unknown split: {split}")

    if n_samples is not None and n_samples < len(raw_samples):
        raw_samples = raw_samples[:n_samples]

    dataset = [preprocess_sample(s) for s in raw_samples]
    targets = [s["answer"] for s in dataset]

    print(f"Evaluating on {split} split: {len(dataset)} samples")

    # 3. Create LLM client (optionally override endpoint for parallel runs)
    llm_config = dict(LLM_CONFIG)
    if llm_base_url is not None:
        llm_config = {
            **llm_config,
            "client_kwargs": {**llm_config["client_kwargs"], "base_url": llm_base_url},
        }
    client = LLMClient(**llm_config)

    # 4. Build batch tool registry
    def _batch_retrieve(kwargs_list: list[dict]) -> list[str]:
        queries = [kw["query"] for kw in kwargs_list]
        return batch_retrieve(queries, BM25S_INDEX_DIR, k=7, corpus_path=CORPUS_PATH)

    batch_tool_registry = {"retrieve": _batch_retrieve}

    # 5. Run chain (step-batched)
    step_max_tokens = {
        2: 1024,
        3: 1024,
        5: 1024,
        6: 1024,
    }

    t0 = time.time()
    results = run_chain_on_dataset_stepwise(
        chain,
        client,
        dataset,
        outer_context_builder,
        batch_tool_registry=batch_tool_registry,
        step_max_tokens=step_max_tokens,
        max_concurrent=32,  # limit concurrency to avoid overwhelming vLLM under load
    )
    wall_clock = time.time() - t0

    # 6. Extract answers and compute metrics
    predictions = [extract_answer(r.final_output) for r in results]

    exact_match = calculate_exact_match(targets, predictions)
    extraction_failures = (
        sum(1 for p in predictions if p is None) / len(predictions)
        if predictions
        else 0.0
    )

    print(f"\n=== Results ({split}, {len(dataset)} samples) ===")
    print(f"Exact Match:          {exact_match:.4f} ({exact_match * 100:.2f}%)")
    print(
        f"Extraction failures:  {extraction_failures:.4f} ({extraction_failures * 100:.2f}%)"
    )
    print(f"Wall-clock time:      {wall_clock:.1f}s ({wall_clock / 60:.1f}min)")

    return {
        "split": split,
        "n_samples": len(dataset),
        "exact_match": exact_match,
        "extraction_failures": extraction_failures,
        "wall_clock_seconds": wall_clock,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate chain program on test/val")
    parser.add_argument(
        "--program",
        required=True,
        help="Path to .py file with entrypoint() function",
    )
    parser.add_argument(
        "--split",
        choices=["test", "val"],
        default="test",
        help="Dataset split to evaluate on",
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=None,
        help="Number of samples (None = all)",
    )
    parser.add_argument(
        "--llm-base-url",
        default=None,
        help="Override LLM endpoint URL (e.g. http://10.226.17.25:8000/v1)",
    )
    args = parser.parse_args()

    result = evaluate(
        args.program,
        split=args.split,
        n_samples=args.n_samples,
        llm_base_url=args.llm_base_url,
    )
    print(f"\nResult dict: {result}")
