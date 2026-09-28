# tools/benchmarks/

Hand-rolled benchmark scripts for evolution-engine internals.

## Scripts

- **`bench_lpt.py`** — measures LPT (longest-processing-time) scheduling
  fairness across the worker pool.
  Run with `python tools/benchmarks/bench_lpt.py`.

## For the canonical 5-problem × 2-seed measurement grid

See [`tools/canonical_benchmark/`](../canonical_benchmark/) — that is the
authoritative end-to-end benchmark used to compare framework configurations
across releases. Results are appended to
`tools/canonical_benchmark/BENCHMARK_HISTORY.md`.
