"""Verify ColBERT retrieval is working correctly before launching the experiment.

Checks:
  1. Index loads without errors
  2. Output format matches what the chain expects: "[1] Title | text\n[2] ..."
  3. parse_retrieved_titles regex correctly extracts titles from ColBERT output
  4. Gold document recall on 20 HotpotQA val samples (vs BM25 baseline)
  5. Single-query latency is acceptable (<500ms per query)

Run after build_colbert_index.py completes:
    PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python \
        experiments/hotpotqa/colbert_feedback/tools/verify_colbert.py

Exit code 0 = all checks passed. Non-zero = something is wrong.
"""

import json
from pathlib import Path
import re
import sys
import time

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
DATASET_PATH = REPO_ROOT / "problems/chains/hotpotqa/dataset/HotpotQA_train.jsonl"
N_SAMPLES = 20
K = 7  # passages retrieved per query


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_retrieved_titles(step_output: str) -> list[str]:
    """Same regex as validate.py — must match."""
    return re.findall(r"\[(?:\d+)\]\s+(.+?)\s+\|", step_output)


def load_samples(n: int) -> list[dict]:
    samples = []
    with open(DATASET_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
            if len(samples) >= n:
                break
    return samples


def check(name: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {name}"
    if detail:
        msg += f": {detail}"
    print(msg)
    return condition


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    from problems.chains.hotpotqa.shared_config import (
        BM25S_INDEX_DIR,
        COLBERT_CHECKPOINT,
        COLBERT_INDEX_DIR,
        CORPUS_PATH,
    )
    from problems.chains.hotpotqa.utils.retrieval import (
        BM25Retriever,
        ColBERTRetriever,
    )

    print("=" * 60)
    print("ColBERT Retrieval Verification")
    print("=" * 60)

    failures = []

    # -----------------------------------------------------------------------
    # 1. Load ColBERT index
    # -----------------------------------------------------------------------
    print("\n[1] Loading ColBERT index...")
    t0 = time.time()
    try:
        colbert = ColBERTRetriever(
            COLBERT_INDEX_DIR, checkpoint=COLBERT_CHECKPOINT, k=K
        )
        # Trigger lazy load
        colbert.batch_retrieve(["test query"], k=1)
        load_time = time.time() - t0
        ok = check("ColBERT index loads", True, f"{load_time:.1f}s")
    except Exception as e:
        ok = check("ColBERT index loads", False, str(e))
        failures.append("ColBERT index load failed")
        print("\nCannot continue — index not ready.")
        return 1

    # -----------------------------------------------------------------------
    # 2. Output format check
    # -----------------------------------------------------------------------
    print("\n[2] Output format verification...")
    query = "Who directed Inception?"
    results = colbert.batch_retrieve([query], k=K)
    output = results[0]

    lines = output.strip().split("\n")
    ok = check(
        "Returns K lines",
        len(lines) == K,
        f"got {len(lines)}, expected {K}",
    )
    if not ok:
        failures.append("wrong number of lines")

    ok = check(
        "Each line starts with [N]",
        all(re.match(r"^\[\d+\]", line) for line in lines if line),
        "",
    )
    if not ok:
        failures.append("line format mismatch")

    ok = check(
        "Each line contains ' | ' separator",
        all(" | " in line for line in lines if line),
        "",
    )
    if not ok:
        failures.append("missing | separator")

    titles = parse_retrieved_titles(output)
    ok = check(
        "parse_retrieved_titles extracts correct count",
        len(titles) == K,
        f"extracted {len(titles)} titles from {K} lines",
    )
    if not ok:
        failures.append("title parsing broken")

    print(f"  Sample output (query: '{query}'):")
    for line in lines[:3]:
        print(f"    {line[:100]}{'...' if len(line) > 100 else ''}")

    # -----------------------------------------------------------------------
    # 3. Latency check
    # -----------------------------------------------------------------------
    print("\n[3] Latency check (10 queries)...")
    test_queries = [
        "What year was Albert Einstein born?",
        "Who is the president of France?",
        "What is the capital of Japan?",
        "Who wrote Hamlet?",
        "What element has atomic number 79?",
        "Who invented the telephone?",
        "When did World War II end?",
        "What is the speed of light?",
        "Who painted the Mona Lisa?",
        "What is the largest planet?",
    ]
    t0 = time.time()
    _ = colbert.batch_retrieve(test_queries, k=K)
    elapsed = time.time() - t0
    per_query = elapsed / len(test_queries) * 1000

    ok = check(
        "Batch latency < 500ms/query",
        per_query < 500,
        f"{per_query:.1f}ms/query ({elapsed:.2f}s total for {len(test_queries)} queries)",
    )
    if not ok:
        failures.append(f"slow retrieval: {per_query:.0f}ms/query")

    # -----------------------------------------------------------------------
    # 4. Gold document recall on HotpotQA samples
    # -----------------------------------------------------------------------
    print(f"\n[4] Gold recall on {N_SAMPLES} HotpotQA val samples (k={K})...")
    samples = load_samples(N_SAMPLES)
    questions = [s["question"] for s in samples]

    # ColBERT recall
    colbert_outputs = colbert.batch_retrieve(questions, k=K)
    colbert_hop1_recalls = []
    for s, out in zip(samples, colbert_outputs):
        gold = set(s.get("supporting_facts", {}).get("title", []))
        retrieved = set(parse_retrieved_titles(out))
        if gold:
            colbert_hop1_recalls.append(len(gold & retrieved) / len(gold))

    colbert_recall = (
        sum(colbert_hop1_recalls) / len(colbert_hop1_recalls)
        if colbert_hop1_recalls
        else 0.0
    )

    # BM25 recall (for comparison)
    try:
        bm25 = BM25Retriever(BM25S_INDEX_DIR, CORPUS_PATH, k=K)
        bm25_outputs = bm25.batch_retrieve(questions, k=K)
        bm25_recalls = []
        for s, out in zip(samples, bm25_outputs):
            gold = set(s.get("supporting_facts", {}).get("title", []))
            retrieved = set(parse_retrieved_titles(out))
            if gold:
                bm25_recalls.append(len(gold & retrieved) / len(gold))
        bm25_recall = sum(bm25_recalls) / len(bm25_recalls) if bm25_recalls else 0.0
        bm25_available = True
    except Exception as e:
        bm25_recall = 0.0
        bm25_available = False
        print(f"  (BM25 unavailable for comparison: {e})")

    ok = check(
        "ColBERT hop-1 gold recall > 0.4",
        colbert_recall > 0.4,
        f"ColBERT={colbert_recall:.3f}"
        + (f", BM25={bm25_recall:.3f}" if bm25_available else ""),
    )
    if not ok:
        failures.append(f"low ColBERT recall: {colbert_recall:.3f}")

    if bm25_available:
        diff = colbert_recall - bm25_recall
        sign = "+" if diff >= 0 else ""
        print(f"  ColBERT vs BM25 recall delta: {sign}{diff:.3f}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    if failures:
        print(f"FAILED ({len(failures)} issue(s)):")
        for f in failures:
            print(f"  - {f}")
        print("=" * 60)
        return 1
    else:
        print("ALL CHECKS PASSED — ColBERT retrieval is ready.")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    sys.exit(main())
