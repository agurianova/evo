#!/usr/bin/env python3
"""
Statistical comparison of reasoning depth across mutation servers.

Sends N diverse prompts to each server, collects reasoning token counts,
then computes descriptive stats and pairwise significance tests.

Usage:
    NO_PROXY=... python experiments/hotpotqa_3run/test_reasoning_stats.py [--n 15]
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import statistics
import urllib.request

SERVERS = {
    "A": "http://10.226.72.211:8777/v1",
    "B": "http://10.226.15.38:8777/v1",
    "C": "http://10.226.185.131:8777/v1",
    "D": "http://10.225.51.251:8777/v1",
}

MODEL = "Qwen3-235B-A22B-Thinking-2507"

# Diverse prompts spanning different reasoning demands
PROMPTS = [
    # Simple algorithmic
    "Write a Python function that reverses a string.",
    "Write a Python function that checks if a number is prime.",
    "Write a Python function that computes the nth Fibonacci number.",
    # Data structure
    "Implement a stack in Python using a list.",
    "Write a Python function that finds the two numbers in a list that sum to a target.",
    # String processing
    "Write a Python function that counts the frequency of each character in a string.",
    "Write a Python function that checks if two strings are anagrams.",
    # Sorting / search
    "Implement binary search in Python.",
    "Implement merge sort in Python.",
    # Math / reasoning
    "Write a Python function that returns all prime factors of an integer.",
    "Write a Python function that computes the greatest common divisor of two numbers.",
    # Multi-step reasoning
    "Write a Python class implementing a simple LRU cache with get and put methods.",
    "Write a Python function that determines if a binary tree is balanced.",
    # Optimization style (closer to HotpotQA mutation prompts)
    "Rewrite the following Python function to be more efficient: def find_duplicates(lst): result = []; seen = set(); [result.append(x) for x in lst if x in seen or seen.add(x)]; return result",
    "Improve the following Python chain-of-thought prompt to better extract multi-hop answers: 'Answer the question step by step.'",
]


def call_server(base_url: str, prompt: str, max_tokens: int = 600) -> dict:
    payload = json.dumps(
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.6,
        }
    ).encode()

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read())

    choice = data["choices"][0]
    message = choice["message"]
    reasoning = message.get("reasoning") or message.get("reasoning_content") or ""
    content = message.get("content") or ""
    usage = data.get("usage", {})

    return {
        "reasoning_chars": len(reasoning),
        "content_chars": len(content),
        "completion_tokens": usage.get("completion_tokens", 0),
        "finish_reason": choice.get("finish_reason", "?"),
        "truncated": choice.get("finish_reason") == "length",
    }


def collect_samples(name: str, base_url: str, prompts: list[str]) -> list[dict]:
    results = []
    errors = 0
    print(f"  [{name}] Sending {len(prompts)} prompts...", flush=True)

    # Run sequentially per server to avoid overloading; servers run in parallel via threads
    for i, prompt in enumerate(prompts):
        try:
            r = call_server(base_url, prompt)
            r["prompt_idx"] = i
            results.append(r)
            print(
                f"  [{name}] {i + 1:2d}/{len(prompts)} "
                f"reasoning={r['reasoning_chars']:4d}ch "
                f"content={r['content_chars']:4d}ch "
                f"finish={r['finish_reason']}",
                flush=True,
            )
        except Exception as e:
            errors += 1
            print(f"  [{name}] {i + 1:2d}/{len(prompts)} ERROR: {e}", flush=True)

    print(f"  [{name}] Done: {len(results)} ok, {errors} errors\n", flush=True)
    return results


def mann_whitney_u(x: list[float], y: list[float]) -> tuple[float, float]:
    """Two-sided Mann-Whitney U test. Returns (U, p-value approx via normal approximation)."""
    import math

    nx, ny = len(x), len(y)
    combined = sorted([(v, "x") for v in x] + [(v, "y") for v in y])

    # Assign ranks (average for ties)
    ranks = []
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2
        for k in range(i, j):
            ranks.append((combined[k][1], avg_rank))
        i = j

    rank_sum_x = sum(r for label, r in ranks if label == "x")
    u_x = rank_sum_x - nx * (nx + 1) / 2
    u_y = nx * ny - u_x
    u = min(u_x, u_y)

    # Normal approximation
    mean_u = nx * ny / 2
    std_u = math.sqrt(nx * ny * (nx + ny + 1) / 12)
    if std_u == 0:
        return u, 1.0
    z = (u - mean_u) / std_u
    # Two-tailed p-value via error function approximation
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return u, p


def describe(values: list[float], label: str) -> dict:
    if not values:
        return {}
    return {
        "label": label,
        "n": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
        "pct_zero": 100 * sum(1 for v in values if v == 0) / len(values),
        "pct_truncated": None,  # filled later
    }


def print_table(rows: list[dict], cols: list[str], fmt: dict[str, str]):
    widths = {
        c: max(
            len(c),
            max(
                len(
                    fmt.get(c, "{}").format(r.get(c, ""))
                    if r.get(c) is not None
                    else "—"
                )
                for r in rows
            ),
        )
        for c in cols
    }
    header = "  ".join(c.ljust(widths[c]) for c in cols)
    print(header)
    print("-" * len(header))
    for row in rows:
        parts = []
        for c in cols:
            v = row.get(c)
            if v is None:
                parts.append("—".ljust(widths[c]))
            else:
                formatted = fmt.get(c, "{}").format(v)
                parts.append(formatted.ljust(widths[c]))
        print("  ".join(parts))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--n",
        type=int,
        default=len(PROMPTS),
        help="Number of prompts (uses first N from list)",
    )
    parser.add_argument(
        "--servers",
        nargs="+",
        default=list(SERVERS.keys()),
        help="Which servers to test (A B C)",
    )
    args = parser.parse_args()

    prompts = PROMPTS[: args.n]
    servers_to_test = {k: v for k, v in SERVERS.items() if k in args.servers}

    print(f"Testing {len(servers_to_test)} servers × {len(prompts)} prompts each\n")

    # Collect samples in parallel across servers
    all_results: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=len(servers_to_test)) as pool:
        futures = {
            pool.submit(collect_samples, name, url, prompts): name
            for name, url in servers_to_test.items()
        }
        for fut in as_completed(futures):
            name = futures[fut]
            all_results[name] = fut.result()

    print("\n" + "=" * 70)
    print("DESCRIPTIVE STATISTICS — Reasoning chars per response")
    print("=" * 70)

    stats_rows = []
    reasoning_by_server: dict[str, list[float]] = {}

    for name in sorted(all_results):
        samples = all_results[name]
        rc = [s["reasoning_chars"] for s in samples]
        trunc = sum(1 for s in samples if s["truncated"])
        reasoning_by_server[name] = rc

        d = describe(rc, f"Server {name}")
        d["pct_truncated"] = 100 * trunc / len(samples) if samples else 0
        stats_rows.append(d)
        print(
            f"\nServer {name} (n={d['n']}):\n"
            f"  mean={d['mean']:.0f}  median={d['median']:.0f}  "
            f"stdev={d['stdev']:.0f}  min={d['min']}  max={d['max']}\n"
            f"  zero-reasoning: {d['pct_zero']:.0f}%  "
            f"truncated (hit max_tokens): {d['pct_truncated']:.0f}%"
        )

    print("\n" + "=" * 70)
    print("PAIRWISE SIGNIFICANCE TESTS — Mann-Whitney U (two-sided)")
    print("  H0: no difference in reasoning char distribution")
    print("=" * 70)

    pairs = [
        ("A", "B", "mutation budget confound check"),
        ("A", "C", "warm-start confound check"),
        ("B", "C", "B vs C (should match)"),
    ]

    for s1, s2, label in pairs:
        if s1 not in reasoning_by_server or s2 not in reasoning_by_server:
            continue
        x, y = reasoning_by_server[s1], reasoning_by_server[s2]
        u, p = mann_whitney_u(x, y)
        median_diff = statistics.median(y) - statistics.median(x)
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        print(
            f"\n  {s1} vs {s2} ({label}):\n"
            f"    U={u:.0f}  p={p:.4f} {sig}\n"
            f"    median({s2})−median({s1}) = {median_diff:+.0f} chars\n"
            f"    {'SIGNIFICANT difference' if p < 0.05 else 'No significant difference'} at α=0.05"
        )

    print("\n" + "=" * 70)
    print("PER-PROMPT BREAKDOWN")
    print("=" * 70)
    for i, prompt in enumerate(prompts):
        row = f"  [{i + 1:2d}] {prompt[:60]!r:<62}"
        for name in sorted(all_results):
            samples = [s for s in all_results[name] if s["prompt_idx"] == i]
            if samples:
                row += f"  {name}:{samples[0]['reasoning_chars']:4d}ch"
            else:
                row += f"  {name}: err"
        print(row)

    print("\nDone.")


if __name__ == "__main__":
    main()
