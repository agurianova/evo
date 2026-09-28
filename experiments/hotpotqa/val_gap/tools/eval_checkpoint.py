#!/usr/bin/env python3
"""
Evaluate a saved program file on the HotpotQA val or test set.

HotpotQA-specific. Imports chain infrastructure and hardcodes STATIC_CHAIN_TOPOLOGY.
For other problems, create an analogous script in experiments/<task>/<name>/tools/.

Takes a .py file saved by `top_programs.py --save-dir` (or any standalone program file
whose entrypoint() returns a chain spec), evaluates it on val or test, and prints EM,
F1, and extraction failure rate.

Useful for:
  - Evaluating archived programs after Redis is flushed
  - Cross-gen comparisons without fetching from Redis
  - Secondary metric (val EM) verification for Run F programs

Usage:
    HOTPOTQA_CHAIN_URL=http://10.226.17.25:8001/v1 \\
    PYTHONPATH=. python experiments/hotpotqa_val_gap/tools/eval_checkpoint.py \\
        --program-file experiments/hotpotqa_val_gap/archives/O/programs/rank01_0.6700_abc12345.py \\
        --dataset test \\
        --n-samples 300

    # Val set (fixed_300 subset)
    HOTPOTQA_CHAIN_URL=http://10.226.17.25:8001/v1 \\
    PYTHONPATH=. python experiments/hotpotqa_val_gap/tools/eval_checkpoint.py \\
        --program-file /tmp/my_program.py \\
        --dataset val \\
        --val-subset fixed_300
"""

import argparse
import os
from pathlib import Path
import sys

PROJ = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJ))

from problems.chains.chain_runner import run_chain_on_dataset_stepwise  # noqa: E402
from problems.chains.chain_validation import validate_chain_spec  # noqa: E402
from problems.chains.client import LLMClient  # noqa: E402
from problems.chains.hotpotqa.shared_config import (  # noqa: E402
    BM25S_INDEX_DIR,
    CORPUS_PATH,
    DATASET_CONFIG,
    LLM_CONFIG,
    load_jsonl,
    outer_context_builder,
    preprocess_sample,
)
from problems.chains.hotpotqa.static.config import (  # noqa: E402
    STATIC_CHAIN_TOPOLOGY,
    load_baseline,
)
from problems.chains.hotpotqa.static.validate import (  # noqa: E402
    calculate_exact_match,
    extract_answer,
)
from problems.chains.hotpotqa.utils.retrieval import batch_retrieve  # noqa: E402
from problems.chains.hotpotqa.utils.utils import normalize_text  # noqa: E402


def _compute_f1(prediction: str | None, target: str) -> float:
    """Token-level SQuAD F1 between prediction and target (after normalize_text)."""
    if prediction is None:
        return 0.0
    pred_tokens = normalize_text(prediction).split()
    tgt_tokens = normalize_text(str(target)).split()
    if not pred_tokens or not tgt_tokens:
        return float(pred_tokens == tgt_tokens)
    common = sum(
        min(pred_tokens.count(t), tgt_tokens.count(t)) for t in set(pred_tokens)
    )
    if common == 0:
        return 0.0
    precision = common / len(pred_tokens)
    recall = common / len(tgt_tokens)
    return 2 * precision * recall / (precision + recall)


def eval_program_file(
    program_path: str,
    dataset: str,
    n_samples: int,
    val_subset: str,
) -> dict:
    """Evaluate a saved program file on val or test and return metrics.

    Mirrors run_test_eval() from gen10_test_eval.py: uses run_chain_on_dataset_stepwise
    with the same batching topology, BM25 batch_retrieve, and per-step max_tokens.

    Args:
        program_path: Path to .py file with an entrypoint() function.
        dataset: "val" or "test".
        n_samples: Number of samples to evaluate.
        val_subset: "fixed_300" (first N samples) or "hash_seeded_300" (reserved for
            rotating val; not supported here — use fixed_300 for val evals).

    Returns:
        Dict with test_em, f1, extraction_failure_rate, n_samples, per_sample_correct.
    """
    # Load program
    exec_globals: dict = {}
    with open(program_path) as f:
        code = f.read()
    exec(code, exec_globals)  # noqa: S102
    chain_spec = exec_globals["entrypoint"]()

    baseline = load_baseline()
    chain = validate_chain_spec(
        chain_spec,
        mode="static",
        topology=STATIC_CHAIN_TOPOLOGY,
        frozen_baseline=baseline,
    )

    # Load dataset
    if dataset == "val":
        dataset_path = DATASET_CONFIG["train_path"]
    else:
        dataset_path = DATASET_CONFIG["test_path"]

    raw = load_jsonl(dataset_path)
    if n_samples and n_samples < len(raw):
        raw = raw[:n_samples]

    data = [preprocess_sample(s) for s in raw]
    targets = [s[DATASET_CONFIG["target_field"]] for s in data]

    client = LLMClient(**LLM_CONFIG)

    def _batch_retrieve(kwargs_list: list[dict]) -> list[str]:
        queries = [kw["query"] for kw in kwargs_list]
        return batch_retrieve(queries, BM25S_INDEX_DIR, k=7, corpus_path=CORPUS_PATH)

    batch_tool_registry = {"retrieve": _batch_retrieve}
    step_max_tokens = {
        2: 8192,
        3: 8192,
        5: 8192,
        6: 8192,
    }

    results = run_chain_on_dataset_stepwise(
        chain,
        client,
        data,
        outer_context_builder,
        batch_tool_registry=batch_tool_registry,
        step_max_tokens=step_max_tokens,
    )
    predictions = [extract_answer(r.final_output) for r in results]

    per_sample_correct = [
        int(pred is not None and normalize_text(pred) == normalize_text(str(tgt)))
        for pred, tgt in zip(predictions, targets)
    ]

    em = calculate_exact_match(targets, predictions)
    f1 = sum(_compute_f1(pred, tgt) for pred, tgt in zip(predictions, targets)) / len(
        targets
    )
    failure_rate = sum(1 for p in predictions if p is None) / len(predictions)

    return {
        "em": em,
        "f1": f1,
        "extraction_failure_rate": failure_rate,
        "n_samples": len(targets),
        "per_sample_correct": per_sample_correct,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a saved HotpotQA program file on val or test set",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
HotpotQA-specific. For other problems, create an analogous script in
experiments/<task>/<name>/tools/.

Chain server is read from HOTPOTQA_CHAIN_URL environment variable.

Example:
    HOTPOTQA_CHAIN_URL=http://10.226.17.25:8001/v1 \\
    PYTHONPATH=. python experiments/hotpotqa_val_gap/tools/eval_checkpoint.py \\
        --program-file /path/to/rank01_0.6700_abc12345.py \\
        --dataset test --n-samples 300
""",
    )
    parser.add_argument(
        "--program-file",
        required=True,
        metavar="PATH",
        help="Path to .py program file with entrypoint() function",
    )
    parser.add_argument(
        "--dataset",
        choices=["val", "test"],
        default="test",
        help="Which dataset to evaluate on (default: test)",
    )
    parser.add_argument(
        "--n-samples",
        type=int,
        default=300,
        help="Number of samples (default: 300)",
    )
    parser.add_argument(
        "--val-subset",
        choices=["fixed_300", "hash_seeded_300"],
        default="fixed_300",
        help="Val subset type (only relevant for --dataset val; default: fixed_300)",
    )
    args = parser.parse_args()

    chain_url = os.environ.get(
        "HOTPOTQA_CHAIN_URL", "(not set — using shared_config default)"
    )
    program_path = args.program_file

    if not Path(program_path).exists():
        print(f"Error: program file not found: {program_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Program: {program_path}")
    print(f"Dataset: {args.dataset} ({args.n_samples} samples)")
    if args.dataset == "val":
        print(f"Val subset: {args.val_subset}")
    print(f"Chain URL: {chain_url}")
    print()

    metrics = eval_program_file(
        program_path=program_path,
        dataset=args.dataset,
        n_samples=args.n_samples,
        val_subset=args.val_subset,
    )

    print("─" * 50)
    print(f"EM:                  {metrics['em'] * 100:.2f}%")
    print(f"F1:                  {metrics['f1'] * 100:.2f}%")
    print(f"Extraction failures: {metrics['extraction_failure_rate'] * 100:.1f}%")
    print(f"N samples:           {metrics['n_samples']}")


if __name__ == "__main__":
    main()
