"""Retrieval benchmark: ColBERT vs BM25 on HotpotQA train split.

Metrics (all computed over first --n-samples train questions):
  - Recall@k for k in [1, 3, 5, 7, 10, 20, 50, 100]:
      * hop1_recall@k  : fraction of gold titles found in top-k (averaged per question)
      * both_recall@k  : fraction of questions where ALL gold titles in top-k
  - MRR (Mean Reciprocal Rank) of the first-retrieved gold title per query
  - Stratified by question type: bridge / comparison
  - Oracle 2nd-hop recall@k: given the first gold passage prepended to the query,
    how often is the second gold title in top-k? (bridge questions only)

Usage:
    # With running colbert_server.py (recommended — no GPU/memory overhead):
    PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python \\
        experiments/hotpotqa/colbert_feedback/tools/benchmark_retrieval.py \\
        --server-url http://127.0.0.1:8889 \\
        [--n-samples 1000] [--k-values 1,3,5,7,10,20,50,100]

    # Without server (loads index in-process; requires GPU + ~20 GB RAM):
    CUDA_VISIBLE_DEVICES=0 CUDA_HOME=/home/jovyan/envs/evo_fast \\
    GIT_PYTHON_GIT_EXECUTABLE=/usr/bin/git \\
    PYTHONPATH=. /home/jovyan/envs/evo_fast/bin/python \\
        experiments/hotpotqa/colbert_feedback/tools/benchmark_retrieval.py \\
        [--n-samples 1000] [--k-values 1,3,5,7,10,20,50,100]
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import time

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
DATASET_PATH = REPO_ROOT / "problems/chains/hotpotqa/dataset/HotpotQA_train.jsonl"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def load_samples(n: int) -> list[dict]:
    samples = []
    with open(DATASET_PATH, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
            if len(samples) >= n:
                break
    return samples


def load_corpus_index(corpus_path: str) -> dict[str, str]:
    """Build title -> first passage text map from the corpus for oracle 2nd-hop."""
    from problems.chains.hotpotqa.utils.retrieval import load_corpus

    passages = load_corpus(corpus_path)
    title_to_text: dict[str, str] = {}
    for p in passages:
        if " | " in p:
            title, text = p.split(" | ", 1)
            if title not in title_to_text:
                title_to_text[title] = text
    return title_to_text


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_titles(output: str) -> list[str]:
    """Extract titles (in rank order) from '[N] title | text' formatted output."""
    return re.findall(r"\[(?:\d+)\]\s+(.+?)\s+\|", output)


# ---------------------------------------------------------------------------
# Retrieval runner
# ---------------------------------------------------------------------------


def run_retrieval(
    retriever, questions: list[str], k: int, label: str, batch_size: int = 50
) -> list[list[str]]:
    """Return ranked title list per question (up to k titles).

    Sends requests in batches of batch_size to stay within server timeout.
    """
    t0 = time.time()
    all_outputs: list[str] = []
    for i in range(0, len(questions), batch_size):
        batch = questions[i : i + batch_size]
        all_outputs.extend(retriever.batch_retrieve(batch, k=k))
    elapsed = time.time() - t0
    ms = elapsed / len(questions) * 1000
    print(
        f"  {label}: {elapsed:.1f}s total, {ms:.1f}ms/query for {len(questions)} queries"
    )
    return [parse_titles(o) for o in all_outputs]


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def recall_at_k(ranked_titles: list[str], gold: set[str], k: int) -> float:
    """Fraction of gold titles in top-k retrieved titles."""
    if not gold:
        return 0.0
    found = sum(1 for t in ranked_titles[:k] if t in gold)
    return found / len(gold)


def both_at_k(ranked_titles: list[str], gold: set[str], k: int) -> float:
    """1.0 if all gold titles are in top-k, else 0.0."""
    if not gold:
        return 0.0
    return 1.0 if gold <= set(ranked_titles[:k]) else 0.0


def mrr(ranked_titles: list[str], gold: set[str]) -> float:
    """Reciprocal rank of the first gold title found (0.0 if not found)."""
    for i, t in enumerate(ranked_titles):
        if t in gold:
            return 1.0 / (i + 1)
    return 0.0


def compute_metrics(
    ranked_per_query: list[list[str]],
    samples: list[dict],
    k_values: list[int],
    qtype: str | None = None,
) -> dict:
    """Aggregate recall@k, both@k, MRR for a set of (sample, ranked_titles) pairs.

    qtype: if set, filter to only samples of that type.
    """
    max_k = max(k_values)

    hop1_at = defaultdict(list)
    both_at = defaultdict(list)
    mrr_vals = []
    n_used = 0

    for s, ranked in zip(samples, ranked_per_query):
        if qtype and s.get("type") != qtype:
            continue
        gold = set(s.get("supporting_facts", {}).get("title", []))
        if not gold:
            continue
        n_used += 1
        for k in k_values:
            hop1_at[k].append(recall_at_k(ranked, gold, k))
            both_at[k].append(both_at_k(ranked, gold, k))
        mrr_vals.append(mrr(ranked[:max_k], gold))

    if n_used == 0:
        return {"n": 0}

    result: dict = {"n": n_used, "mrr": sum(mrr_vals) / n_used}
    for k in k_values:
        result[f"hop1@{k}"] = sum(hop1_at[k]) / n_used
        result[f"both@{k}"] = sum(both_at[k]) / n_used
    return result


def compute_oracle_2hop_metrics(
    retriever,
    samples: list[dict],
    title_to_text: dict[str, str],
    k_values: list[int],
    label: str,
) -> dict:
    """Oracle 2nd-hop: for bridge questions, prepend first gold passage to query,
    then measure recall of the second gold title.

    The first gold title in supporting_facts is treated as the bridge document
    (the one whose content helps retrieve the answer document).
    """
    bridge_samples = [s for s in samples if s.get("type") == "bridge"]
    if not bridge_samples:
        return {}

    max_k = max(k_values)
    oracle_queries = []
    second_gold_titles = []

    for s in bridge_samples:
        titles = s["supporting_facts"]["title"]
        if len(titles) < 2:
            continue
        bridge_title = titles[0]
        answer_title = titles[1]
        bridge_text = title_to_text.get(bridge_title, "")
        # Oracle query: original question + bridge passage content
        oracle_query = (
            f"{s['question']} [context: {bridge_title} | {bridge_text[:300]}]"
        )
        oracle_queries.append(oracle_query)
        second_gold_titles.append(answer_title)

    if not oracle_queries:
        return {}

    print(
        f"\n  Oracle 2nd-hop ({label}): retrieving for {len(oracle_queries)} bridge questions..."
    )
    all_outputs: list[str] = []
    for i in range(0, len(oracle_queries), 50):
        all_outputs.extend(
            retriever.batch_retrieve(oracle_queries[i : i + 50], k=max_k)
        )
    ranked_lists = [parse_titles(o) for o in all_outputs]

    result: dict = {"n": len(oracle_queries)}
    for k in k_values:
        hits = [
            1.0 if gold in ranked[:k] else 0.0
            for gold, ranked in zip(second_gold_titles, ranked_lists)
        ]
        result[f"recall@{k}"] = sum(hits) / len(hits)
    return result


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------


def print_section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_recall_table(
    k_values: list[int],
    colbert_metrics: dict,
    bm25_metrics: dict,
    metric_prefix: str,
    label: str,
) -> None:
    n_c = colbert_metrics.get("n", 0)
    n_b = bm25_metrics.get("n", 0)
    print(f"\n{label}  (ColBERT n={n_c}, BM25 n={n_b})")
    print(f"  {'k':>4}  {'ColBERT':>8}  {'BM25':>8}  {'Delta':>8}")
    print(f"  {'-' * 36}")
    for k in k_values:
        key = f"{metric_prefix}@{k}"
        c = colbert_metrics.get(key, float("nan"))
        b = bm25_metrics.get(key, float("nan"))
        delta = c - b
        sign = "+" if delta >= 0 else ""
        print(f"  {k:>4}  {c:>8.3f}  {b:>8.3f}  {sign}{delta:>7.3f}")


def print_oracle_table(
    k_values: list[int],
    colbert_oracle: dict,
    bm25_oracle: dict,
) -> None:
    n_c = colbert_oracle.get("n", 0)
    n_b = bm25_oracle.get("n", 0)
    print(f"\nOracle 2nd-hop recall  (ColBERT n={n_c}, BM25 n={n_b})")
    print(f"  {'k':>4}  {'ColBERT':>8}  {'BM25':>8}  {'Delta':>8}")
    print(f"  {'-' * 36}")
    for k in k_values:
        key = f"recall@{k}"
        c = colbert_oracle.get(key, float("nan"))
        b = bm25_oracle.get(key, float("nan"))
        delta = c - b
        sign = "+" if delta >= 0 else ""
        print(f"  {k:>4}  {c:>8.3f}  {b:>8.3f}  {sign}{delta:>7.3f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-samples", type=int, default=1000)
    parser.add_argument(
        "--k-values",
        type=str,
        default="1,3,5,7,10,20,50,100",
        help="Comma-separated list of k values for recall@k",
    )
    parser.add_argument(
        "--oracle-k-values",
        type=str,
        default="1,3,5,7,10,20",
        help="k values for oracle 2nd-hop (subset of --k-values)",
    )
    parser.add_argument(
        "--server-url",
        type=str,
        default="",
        help="If set, use ColBERTServerRetriever at this URL instead of in-process loading",
    )
    args = parser.parse_args()

    k_values = sorted(set(int(x) for x in args.k_values.split(",")))
    oracle_k_values = sorted(set(int(x) for x in args.oracle_k_values.split(",")))

    from problems.chains.hotpotqa.shared_config import (
        BM25S_INDEX_DIR,
        COLBERT_CHECKPOINT,
        COLBERT_INDEX_DIR,
        CORPUS_PATH,
    )
    from problems.chains.hotpotqa.utils.retrieval import (
        BM25Retriever,
        ColBERTRetriever,
        ColBERTServerRetriever,
    )

    print(f"Loading {args.n_samples} HotpotQA train samples...")
    samples = load_samples(args.n_samples)
    questions = [s["question"] for s in samples]
    n_bridge = sum(1 for s in samples if s.get("type") == "bridge")
    n_comparison = sum(1 for s in samples if s.get("type") == "comparison")
    print(
        f"  Loaded {len(samples)} samples  (bridge={n_bridge}, comparison={n_comparison})"
    )

    max_k = max(k_values)

    # ── ColBERT ──────────────────────────────────────────────────────────────
    if args.server_url:
        print(f"\nConnecting to ColBERT server ({args.server_url})...")
        t0 = time.time()
        colbert = ColBERTServerRetriever(args.server_url, k=max_k)
        colbert.batch_retrieve(["warmup"], k=1)
        print(f"  Server ready in {time.time() - t0:.1f}s")
    else:
        print(f"\nLoading ColBERT index ({COLBERT_INDEX_DIR})...")
        t0 = time.time()
        colbert = ColBERTRetriever(
            COLBERT_INDEX_DIR, checkpoint=COLBERT_CHECKPOINT, k=max_k
        )
        colbert.batch_retrieve(["warmup"], k=1)
        print(f"  Index loaded in {time.time() - t0:.1f}s")

    print(f"\nRunning ColBERT retrieval (max_k={max_k}, n={len(questions)})...")
    colbert_ranked = run_retrieval(colbert, questions, max_k, "ColBERT")

    # ── BM25 ─────────────────────────────────────────────────────────────────
    print(f"\nLoading BM25 index ({BM25S_INDEX_DIR})...")
    t0 = time.time()
    bm25 = BM25Retriever(BM25S_INDEX_DIR, CORPUS_PATH, k=max_k)
    bm25.batch_retrieve(["warmup"], k=1)
    print(f"  Index loaded in {time.time() - t0:.1f}s")

    print(f"\nRunning BM25 retrieval (max_k={max_k}, n={len(questions)})...")
    bm25_ranked = run_retrieval(bm25, questions, max_k, "BM25")

    # ── Metrics ───────────────────────────────────────────────────────────────
    print_section(f"Retrieval Benchmark  (n={len(samples)}, max_k={max_k})")

    for qtype in [None, "bridge", "comparison"]:
        section = "ALL QUESTIONS" if qtype is None else qtype.upper() + " QUESTIONS"
        c_metrics = compute_metrics(colbert_ranked, samples, k_values, qtype)
        b_metrics = compute_metrics(bm25_ranked, samples, k_values, qtype)

        print_recall_table(
            k_values, c_metrics, b_metrics, "hop1", f"Hop-1 recall@k  [{section}]"
        )
        print_recall_table(
            k_values, c_metrics, b_metrics, "both", f"Both-hops recall@k  [{section}]"
        )

        # MRR
        c_mrr = c_metrics.get("mrr", float("nan"))
        b_mrr = b_metrics.get("mrr", float("nan"))
        delta = c_mrr - b_mrr
        sign = "+" if delta >= 0 else ""
        print(
            f"\n  MRR [{section}]  ColBERT={c_mrr:.4f}  BM25={b_mrr:.4f}  "
            f"delta={sign}{delta:.4f}"
        )

    # ── Oracle 2nd-hop (bridge only) ─────────────────────────────────────────
    print_section("Oracle 2nd-hop  (bridge questions only)")
    print("  Query = original question + first gold passage (truncated to 300 chars)")
    print("  Metric = recall of SECOND gold title in top-k")

    print("\n  Building title→text index from corpus...")
    t0 = time.time()
    title_to_text = load_corpus_index(CORPUS_PATH)
    print(f"  Done in {time.time() - t0:.1f}s  ({len(title_to_text):,} unique titles)")

    colbert_oracle = compute_oracle_2hop_metrics(
        colbert, samples, title_to_text, oracle_k_values, "ColBERT"
    )
    bm25_oracle = compute_oracle_2hop_metrics(
        bm25, samples, title_to_text, oracle_k_values, "BM25"
    )
    print_oracle_table(oracle_k_values, colbert_oracle, bm25_oracle)

    # ── Latency summary ───────────────────────────────────────────────────────
    print_section("Latency Summary")
    t0 = time.time()
    colbert.batch_retrieve(questions[:100], k=7)
    c_lat = (time.time() - t0) / 100 * 1000
    t0 = time.time()
    bm25.batch_retrieve(questions[:100], k=7)
    b_lat = (time.time() - t0) / 100 * 1000
    print(
        f"\n  ColBERT: {c_lat:.1f}ms/query  |  BM25: {b_lat:.1f}ms/query  "
        f"|  ratio: {c_lat / b_lat:.1f}x  (k=7, n=100)"
    )

    print()


if __name__ == "__main__":
    main()
