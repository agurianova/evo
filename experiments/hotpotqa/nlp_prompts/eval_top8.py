#!/usr/bin/env python3
"""
Evaluate top-8 programs by val_EM from runs L, M, N on the held-out test set.

Usage:
    HOTPOTQA_CHAIN_URL=http://<host>:<port>/v1 python \
        experiments/hotpotqa_nlp_prompts/eval_top8.py \
        --run-label L --redis-db 1 --redis-prefix chains/hotpotqa/static_r \
        --results-path experiments/hotpotqa_nlp_prompts/test_evals/top8_results.json

Run all three in parallel:
    for run in L M N; do
        CHAIN=... python eval_top8.py --run-label $run ... &
    done
    wait
"""

import argparse
import asyncio
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys

PROJ = Path(__file__).parent.parent.parent
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


def get_top_n_programs(redis_db: int, prefix: str, n: int = 8):
    """Return top-N programs by val fitness from Redis."""
    programs = asyncio.run(_fetch_programs(redis_db, prefix))
    eligible = [
        p
        for p in programs
        if "fitness" in p.metrics and p.metrics["fitness"] is not None
    ]
    eligible.sort(key=lambda p: p.metrics["fitness"], reverse=True)
    top = eligible[:n]
    print(
        f"Total programs: {len(programs)} | with fitness: {len(eligible)} | returning top {len(top)}"
    )
    for i, p in enumerate(top, 1):
        it = int(p.metadata.get("iteration", 0))
        print(
            f"  #{i:2d}  id={p.id[:8]}  gen={it:3d}  val_EM={p.metrics['fitness'] * 100:.2f}%"
        )
    return top


def run_test_eval_program(program, n_samples: int = 300) -> dict:
    """Evaluate a single program on the test set."""
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

    raw = load_jsonl(DATASET_CONFIG["test_path"])
    if n_samples and n_samples < len(raw):
        raw = raw[:n_samples]

    dataset = [preprocess_sample(s) for s in raw]
    targets = [s[DATASET_CONFIG["target_field"]] for s in dataset]

    client = LLMClient(**LLM_CONFIG)

    def _batch_retrieve(kwargs_list):
        queries = [kw["query"] for kw in kwargs_list]
        return batch_retrieve(queries, BM25S_INDEX_DIR, k=7, corpus_path=CORPUS_PATH)

    batch_tool_registry = {"retrieve": _batch_retrieve}
    step_max_tokens = {2: 8192, 3: 8192, 5: 8192, 6: 8192}

    results = run_chain_on_dataset_stepwise(
        chain,
        client,
        dataset,
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
    failure_rate = sum(1 for p in predictions if p is None) / len(predictions)

    return {
        "test_em": em,
        "extraction_failure_rate": failure_rate,
        "n_samples": len(targets),
        "per_sample_correct": per_sample_correct,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-label", required=True)
    parser.add_argument("--redis-db", type=int, required=True)
    parser.add_argument("--redis-prefix", required=True)
    parser.add_argument("--top-n", type=int, default=8)
    parser.add_argument("--n-samples", type=int, default=300)
    parser.add_argument("--results-path", required=True)
    args = parser.parse_args()

    chain_url = os.environ.get("HOTPOTQA_CHAIN_URL", "(default)")
    print(f"\n=== Top-{args.top_n} test eval — Run {args.run_label} ===")
    print(f"Chain URL: {chain_url}")

    top_programs = get_top_n_programs(args.redis_db, args.redis_prefix, args.top_n)
    if not top_programs:
        print("No programs found — aborting.")
        sys.exit(1)

    results_path = Path(args.results_path)
    results_path.parent.mkdir(parents=True, exist_ok=True)

    if results_path.exists():
        with open(results_path) as f:
            data = json.load(f)
    else:
        data = {"evaluation_date_utc": datetime.now(UTC).isoformat()}

    run_results = []
    for rank, program in enumerate(top_programs, 1):
        it = int(program.metadata.get("iteration", 0))
        val_em = program.metrics["fitness"]
        print(
            f"\n--- #{rank} id={program.id[:8]}  gen={it}  val_EM={val_em * 100:.2f}% ---"
        )

        try:
            metrics = run_test_eval_program(program, n_samples=args.n_samples)
        except Exception as e:
            print(f"  SKIP — eval failed: {type(e).__name__}: {str(e)[:120]}")
            run_results.append(
                {
                    "rank": rank,
                    "program_id": program.id,
                    "iteration": it,
                    "val_em": val_em,
                    "test_em": None,
                    "val_test_gap": None,
                    "extraction_failure_rate": None,
                    "n_test_samples": None,
                    "per_sample_correct": None,
                    "error": str(e)[:200],
                }
            )
            continue

        gap = val_em - metrics["test_em"]

        print(
            f"  test_EM={metrics['test_em'] * 100:.2f}%  gap={gap * 100:+.2f}pp  "
            f"fail={metrics['extraction_failure_rate'] * 100:.1f}%"
        )

        run_results.append(
            {
                "rank": rank,
                "program_id": program.id,
                "iteration": it,
                "val_em": val_em,
                "test_em": metrics["test_em"],
                "val_test_gap": gap,
                "extraction_failure_rate": metrics["extraction_failure_rate"],
                "n_test_samples": metrics["n_samples"],
                "per_sample_correct": metrics["per_sample_correct"],
            }
        )

    data[args.run_label] = {
        "chain_url": chain_url,
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "programs": run_results,
    }

    with open(results_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n=== Run {args.run_label} summary ===")
    print(f"{'Rank':>4}  {'Gen':>4}  {'Val%':>6}  {'Test%':>6}  {'Gap':>7}")
    for r in run_results:
        test_str = (
            f"{r['test_em'] * 100:6.2f}" if r["test_em"] is not None else "  SKIP"
        )
        gap_str = (
            f"{r['val_test_gap'] * 100:+7.2f}pp"
            if r["val_test_gap"] is not None
            else "      —"
        )
        print(
            f"  #{r['rank']:2d}  {r['iteration']:4d}  {r['val_em'] * 100:6.2f}  {test_str}  {gap_str}"
        )

    scored = [r for r in run_results if r["test_em"] is not None]
    best_by_test = max(scored, key=lambda r: r["test_em"]) if scored else None
    if best_by_test:
        print(
            f"\n  Best by test: #{best_by_test['rank']} (gen={best_by_test['iteration']}) "
            f"test_EM={best_by_test['test_em'] * 100:.2f}%"
        )
    else:
        print("\n  No programs successfully evaluated.")
    print(f"  Results written to {results_path}")


if __name__ == "__main__":
    main()
