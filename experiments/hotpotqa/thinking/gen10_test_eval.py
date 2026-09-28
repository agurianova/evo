#!/usr/bin/env python3
"""
Gen-10 checkpoint: evaluate best program (generation ≤ 10) on the test set.

Usage:
    HOTPOTQA_CHAIN_URL=http://<host>:<port>/v1 python \
        experiments/hotpotqa_thinking/gen10_test_eval.py \
        --run-label E --redis-db 10 \
        --redis-prefix chains/hotpotqa/static --max-gen 9999
"""

import argparse
import asyncio
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import subprocess
import sys

PROJ = Path(__file__).parent.parent.parent
# Ensure project root is on PYTHONPATH
sys.path.insert(0, str(PROJ))

from gigaevo.database.redis_program_storage import (  # noqa: E402
    RedisProgramStorage,
    RedisProgramStorageConfig,
)
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

_DEFAULT_RESULTS_PATH = str(PROJ / "experiments/hotpotqa_p1p2/test_evals/results.json")


async def _fetch_programs(redis_db: int, prefix: str):
    storage = RedisProgramStorage(
        RedisProgramStorageConfig(
            redis_url=f"redis://localhost:6379/{redis_db}",
            key_prefix=prefix,
            max_connections=50,
            connection_pool_timeout=30.0,
            health_check_interval=60,
            read_only=True,
        )
    )
    try:
        return await storage.get_all()
    finally:
        await storage.close()


def get_best_program_at_gen(
    redis_db: int, prefix: str, max_gen: int, select_by: str = "fitness"
):
    """Return best program among programs with metadata['iteration'] <= max_gen.

    Args:
        select_by: "fitness" (default) selects by p.metrics["fitness"] (val F1 for F1
                   runs, val EM for EM runs). "val_em" selects by p.metrics["em"] when
                   available, falling back to p.metrics["fitness"]. Use "val_em" for
                   F1-fitness runs where the final reported metric is EM — the
                   best-by-F1 and best-by-EM programs may differ.
    """
    programs = asyncio.run(_fetch_programs(redis_db, prefix))

    eligible = [
        p
        for p in programs
        if int(p.metadata.get("iteration", 0)) <= max_gen
        and "fitness" in p.metrics
        and p.metrics["fitness"] is not None
    ]

    if not eligible:
        print(f"No programs found with iteration <= {max_gen}", flush=True)
        return None

    def _sort_key(p):
        if select_by == "val_em":
            return p.metrics.get("em", p.metrics["fitness"])
        return p.metrics["fitness"]

    best = max(eligible, key=_sort_key)
    iteration = int(best.metadata.get("iteration", 0))
    is_f1_run = "em" in best.metrics
    if select_by == "val_em":
        select_label = "val_EM (select_by=val_em)"
    else:
        select_label = "val_F1" if is_f1_run else "val_EM"
    selected_val = _sort_key(best)
    print(
        f"Best program at iteration <= {max_gen}: id={best.id}  iteration={iteration}  "
        f"{select_label}={selected_val * 100:.2f}%",
        flush=True,
    )
    return best


def run_test_eval(program, n_samples: int = 300, use_val_set: bool = False) -> dict:
    """Run the program on the test (or val) set and return metrics.

    Args:
        use_val_set: If True, evaluate on the fixed-300 val set (train split first
            300 samples) instead of the test set. Used ONLY for seed retest
            calibration per pre-registration §5 — never for primary test evals.

    Uses run_chain_on_dataset_stepwise to match the execution path of validation
    exactly (same batching topology, same BM25 batch_retrieve, same per-step
    max_tokens). This is critical for val-test gap comparability.
    """
    exec_globals = {}
    exec(program.code, exec_globals)
    chain_spec = exec_globals["entrypoint"]()

    baseline = load_baseline()
    chain = validate_chain_spec(
        chain_spec,
        mode="static",
        topology=STATIC_CHAIN_TOPOLOGY,
        frozen_baseline=baseline,
    )

    dataset_path = (
        DATASET_CONFIG["train_path"] if use_val_set else DATASET_CONFIG["test_path"]
    )
    raw = load_jsonl(dataset_path)
    if n_samples and n_samples < len(raw):
        raw = raw[:n_samples]

    dataset = [preprocess_sample(s) for s in raw]
    targets = [s[DATASET_CONFIG["target_field"]] for s in dataset]

    client = LLMClient(**LLM_CONFIG)

    # Batch retrieve mirrors static/validate.py exactly (homogeneous vLLM batches).
    def _batch_retrieve(kwargs_list: list[dict]) -> list[str]:
        queries = [kw["query"] for kw in kwargs_list]
        return batch_retrieve(queries, BM25S_INDEX_DIR, k=7, corpus_path=CORPUS_PATH)

    batch_tool_registry = {"retrieve": _batch_retrieve}
    # Per-step max_tokens: mirrors static/validate.py step_max_tokens exactly.
    step_max_tokens = {
        2: 8192,  # summarize retrieved facts
        3: 8192,  # generate search query
        5: 8192,  # combine evidence
        6: 8192,  # final answer
    }

    results = run_chain_on_dataset_stepwise(
        chain,
        client,
        dataset,
        outer_context_builder,
        batch_tool_registry=batch_tool_registry,
        step_max_tokens=step_max_tokens,
    )
    predictions = [extract_answer(r.final_output) for r in results]

    # Per-sample binary correct/incorrect (needed for McNemar tests per pre-registration §7.5)
    per_sample_correct = [
        int(pred is not None and normalize_text(pred) == normalize_text(str(tgt)))
        for pred, tgt in zip(predictions, targets)
    ]

    em = calculate_exact_match(targets, predictions)
    failure_rate = sum(1 for p in predictions if p is None) / len(predictions)

    return {
        "test_em": em,
        "extraction_failure_rate": failure_rate,
        "n_samples": len(targets),
        "per_sample_correct": per_sample_correct,
    }


def _get_preregistration_commit() -> str:
    """Return git commit hash of the pre-registration document, or 'unknown'."""
    preregistration_path = str(
        PROJ / "docs/plans/2026-03-02-test-eval-preregistration.md"
    )
    try:
        return (
            subprocess.check_output(
                ["git", "log", "-1", "--format=%H", "--", preregistration_path],
                cwd=str(PROJ),
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
            or "unknown"
        )
    except Exception:
        return "unknown"


def write_results_entry(
    run_label: str,
    best,
    metrics: dict,
    chain_url: str,
    results_path: str,
    val_subset: str = "fixed_300",
) -> None:
    """Write or update a single run's entry in results.json."""
    path = Path(results_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        with open(path) as f:
            data = json.load(f)
    else:
        data = {
            "preregistration_commit": _get_preregistration_commit(),
            "evaluation_date_utc": datetime.now(UTC).isoformat(),
        }

    # For F1 runs, best.metrics["fitness"] is F1 not EM. Use "em" if present
    # (stored by validate.py as a secondary metric for F1 problem variants).
    val_em = best.metrics.get("em", best.metrics["fitness"])

    data[run_label] = {
        "program_id": best.id,
        "iteration": int(best.metadata.get("iteration", 0)),
        "val_em": val_em,
        "val_subset": val_subset,  # "fixed_300" for E/F; "hash_seeded_300" for G/H
        "test_em": metrics["test_em"],
        "val_test_gap": val_em - metrics["test_em"],
        "extraction_failure_rate": metrics["extraction_failure_rate"],
        "n_test_samples": metrics["n_samples"],
        "chain_url": chain_url,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "per_sample_correct": metrics["per_sample_correct"],
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Results written to {path}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-label", required=True, help="Run label (E/F/G/H)")
    parser.add_argument("--redis-db", type=int, required=True)
    parser.add_argument(
        "--redis-prefix",
        required=True,
        help="Redis key prefix matching problem.name used during evolution. "
        "E: chains/hotpotqa/static  F: chains/hotpotqa/static_a  "
        "G: chains/hotpotqa/static_r  H: chains/hotpotqa/static_ra",
    )
    parser.add_argument(
        "--max-gen", type=int, default=10, help="Max generation to consider"
    )
    parser.add_argument("--n-samples", type=int, default=300)
    parser.add_argument(
        "--results-path",
        default=_DEFAULT_RESULTS_PATH,
        help="Path to results.json (appended per run). "
        f"Default: {_DEFAULT_RESULTS_PATH}",
    )
    parser.add_argument(
        "--val-subset",
        default="fixed_300",
        choices=["fixed_300", "hash_seeded_300"],
        help="Validation subset type: 'fixed_300' for E/F (P1=OFF), "
        "'hash_seeded_300' for G/H (P1=ON). Recorded in results.json.",
    )
    parser.add_argument(
        "--use-val-set",
        action="store_true",
        help="Evaluate on val set (train[:300]) instead of test set. "
        "Use ONLY for seed retest calibration per pre-registration §5.",
    )
    parser.add_argument(
        "--select-by",
        default="fitness",
        choices=["fitness", "val_em"],
        help="Criterion for selecting the best program. 'fitness' (default) uses "
        "p.metrics['fitness'] (val F1 for F1 runs). 'val_em' uses p.metrics['em'] "
        "when available — recommended for F1-fitness runs where the final reported "
        "metric is EM, since best-by-F1 and best-by-EM may be different programs.",
    )
    args = parser.parse_args()

    chain_url = os.environ.get("HOTPOTQA_CHAIN_URL", "(default)")

    dataset_label = "VAL (calibration)" if args.use_val_set else "TEST"
    print(
        f"\n=== Iteration-{args.max_gen} checkpoint {dataset_label} eval — Run {args.run_label} ===",
        flush=True,
    )
    print(f"Chain URL: {chain_url}", flush=True)

    best = get_best_program_at_gen(
        args.redis_db, args.redis_prefix, args.max_gen, select_by=args.select_by
    )
    if best is None:
        sys.exit(1)

    metrics = run_test_eval(
        best, n_samples=args.n_samples, use_val_set=args.use_val_set
    )

    val_em = best.metrics.get("em", best.metrics["fitness"])
    print("\n--- Results ---")
    if "em" in best.metrics:
        # F1 fitness run: report both val F1 (fitness) and val EM separately
        print(
            f"Run {args.run_label}:  val_F1={best.metrics['fitness'] * 100:.2f}%  "
            f"val_EM={val_em * 100:.2f}%  "
            f"test_EM={metrics['test_em'] * 100:.2f}%  "
            f"val_EM-test_EM_gap={(val_em - metrics['test_em']) * 100:+.2f}pp  "
            f"n_test={metrics['n_samples']}"
        )
    else:
        print(
            f"Run {args.run_label}:  val_EM={val_em * 100:.2f}%  "
            f"test_EM={metrics['test_em'] * 100:.2f}%  "
            f"val_EM-test_EM_gap={(val_em - metrics['test_em']) * 100:+.2f}pp  "
            f"n_test={metrics['n_samples']}"
        )
    print(f"Extraction failures: {metrics['extraction_failure_rate'] * 100:.1f}%")

    write_results_entry(
        run_label=args.run_label,
        best=best,
        metrics=metrics,
        chain_url=chain_url,
        results_path=args.results_path,
        val_subset=args.val_subset,
    )


if __name__ == "__main__":
    main()
