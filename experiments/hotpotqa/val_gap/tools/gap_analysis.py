#!/usr/bin/env python3
"""
Val-test gap analysis for the hotpotqa_val_gap experiment.

Reads best-val fitness from Redis and (optionally) test eval results from
results.json, then produces the primary gap table and gate verdicts needed for
05_results.md Section 1.

Usage:
    # Val-only (no results.json needed — works while runs are live)
    PYTHONPATH=. python experiments/hotpotqa_val_gap/tools/gap_analysis.py --val-only

    # Full analysis after test evals complete
    PYTHONPATH=. python experiments/hotpotqa_val_gap/tools/gap_analysis.py

    # Markdown table only (for pasting into 05_results.md)
    PYTHONPATH=. python experiments/hotpotqa_val_gap/tools/gap_analysis.py --markdown

    # Custom results.json path
    PYTHONPATH=. python experiments/hotpotqa_val_gap/tools/gap_analysis.py \\
        --results /tmp/results.json

Experiment-specific: hardcodes run specs (O/R/Q/F), gate thresholds from
03_plan.md, and Run Q invalidation status (Amendment 2). Not suitable for
reuse across experiments without significant rework.
"""

import argparse
import json
from pathlib import Path
import sys

import redis as redis_lib

PROJ = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJ))

from gigaevo.monitoring.run_spec import RunSpec  # noqa: E402

# ── Run specs (hardcoded: this is experiment-specific) ────────────────────────
# Format: label → (run_arg, condition_label, fitness_metric, is_invalidated)
RUNS = [
    ("O", "chains/hotpotqa/static@4:O", "fixed-300 EM (control)", "EM", False),
    ("R", "chains/hotpotqa/static_r@7:R", "rotating-300 EM", "EM", False),
    ("Q", "chains/hotpotqa/static_600@6:Q", "fixed-600 EM", "EM", True),  # Amendment 2
    ("F", "chains/hotpotqa/static_f1@5:F", "fixed-300 F1", "F1", False),
]

# Run F: val fitness in Redis = F1 (fitness key), but we also read val_EM separately.
F1_RUN = "F"
# Redis key for the secondary EM metric stored alongside F1 fitness in Run F.
# See 03_plan.md Amendment 1 dry-run verification.
FRONTIER_EM_KEY_SUFFIX = "valid_frontier_em"

# ── Gate thresholds (from 03_plan.md Success Criteria) ────────────────────────
POSITIVE_PP = 5.0  # gap reduction ≥ 5pp for POSITIVE
SUGGESTIVE_PP = 2.0  # gap reduction ≥ 2pp for SUGGESTIVE (< 5pp)
NEGATIVE_PP = -2.0  # gap delta ≤ -2pp for NEGATIVE (gap inflation)
# Absolute test EM floor for POSITIVE/SUGGESTIVE verdicts
FLOOR_TEST_EM_ABS = 0.60
# Relative floor: test EM(X) ≥ test EM(O) - 1.5pp
FLOOR_REL_PP = 1.5

DEFAULT_RESULTS_PATH = str(
    PROJ / "experiments/hotpotqa_val_gap/test_evals/results.json"
)


def _read_last_v(r: redis_lib.Redis, key: str) -> float | None:
    """Read last entry's 'v' field from a Redis list of JSON metrics entries."""
    raw = r.lindex(key, -1)
    if raw is None:
        return None
    try:
        return float(json.loads(raw)["v"])
    except (KeyError, json.JSONDecodeError, TypeError, ValueError):
        return None


def fetch_val_fitness(
    prefix: str, db: int, fitness_metric: str, host: str = "localhost", port: int = 6379
) -> dict[str, float | None]:
    """Read best val fitness from Redis.

    Returns dict with keys:
      val_fitness   -- best frontier fitness (F1 or EM depending on run config)
      val_em        -- best frontier EM (only for F1 runs; None otherwise)
    """
    r = redis_lib.Redis(host=host, port=port, db=db)
    try:
        fitness_key = f"{prefix}:metrics:history:program_metrics:valid_frontier_fitness"
        val_fitness = _read_last_v(r, fitness_key)

        val_em = None
        if fitness_metric == "F1":
            em_key = (
                f"{prefix}:metrics:history:program_metrics:{FRONTIER_EM_KEY_SUFFIX}"
            )
            val_em = _read_last_v(r, em_key)

        return {"val_fitness": val_fitness, "val_em": val_em}
    finally:
        r.close()


def load_results_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    with open(p) as f:
        return json.load(f)


def verdict_for_gap_delta(
    delta_pp: float,
    test_em: float | None,
    control_test_em: float | None,
    *,
    is_invalidated: bool,
    is_control: bool,
) -> str:
    """Return verdict string given gap delta (pp) relative to control."""
    if is_control:
        return "(control)"
    if is_invalidated:
        return "UNANSWERABLE [†]"
    if test_em is None:
        return "NO TEST DATA"

    floors_met = test_em >= FLOOR_TEST_EM_ABS and (
        control_test_em is None or test_em >= control_test_em - FLOOR_REL_PP / 100
    )

    if delta_pp >= POSITIVE_PP and floors_met:
        return "POSITIVE"
    elif delta_pp >= SUGGESTIVE_PP and floors_met:
        return "SUGGESTIVE"
    elif delta_pp < NEGATIVE_PP:
        return "NEGATIVE"
    else:
        return "NULL"


def format_pct(v: float | None, decimals: int = 1) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.{decimals}f}%"


def format_pp(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v:+.1f}pp"


def run_analysis(
    *,
    val_only: bool,
    results_path: str,
    markdown_only: bool,
    redis_host: str,
    redis_port: int,
) -> None:
    results = {} if val_only else load_results_json(results_path)

    # Collect data for each run
    rows = []
    for label, run_arg, condition, fitness_metric, is_invalidated in RUNS:
        _spec = RunSpec.parse(run_arg)
        prefix, db = _spec.prefix, _spec.db
        redis_data = fetch_val_fitness(
            prefix, db, fitness_metric, host=redis_host, port=redis_port
        )
        val_fitness = redis_data["val_fitness"]
        val_em_redis = redis_data["val_em"]  # only set for F1 runs

        run_result = results.get(label, {})
        # In results.json, "val_em" field = val_fitness at eval time (may be F1 for Run F)
        test_em = run_result.get("test_em")
        extraction_fail = run_result.get("extraction_failure_rate")

        rows.append(
            {
                "label": label,
                "condition": condition,
                "fitness_metric": fitness_metric,
                "is_invalidated": is_invalidated,
                "val_fitness": val_fitness,  # F1 or EM depending on run
                "val_em_redis": val_em_redis,  # EM from Redis (F1 runs only)
                "test_em": test_em,
                "extraction_fail": extraction_fail,
            }
        )

    # Control row for delta computation
    ctrl = next(r for r in rows if r["label"] == "O")
    ctrl_test_em = ctrl["test_em"]
    # Control gap: val_fitness - test_em (both EM for control)
    ctrl_gap = (
        ctrl["val_fitness"] - ctrl["test_em"]
        if ctrl["val_fitness"] is not None and ctrl["test_em"] is not None
        else None
    )

    if not markdown_only:
        print("Val-test gap analysis — hotpotqa_val_gap")
        print()

    # ── Table ─────────────────────────────────────────────────────────────────
    # Column widths
    W_RUN = 4
    W_COND = 26
    W_VAL = 13
    W_TEST = 8
    W_GAP = 9
    W_DELTA = 9
    W_VERDICT = 24

    def _row(*cols) -> str:
        return (
            f"  {cols[0]:<{W_RUN}}"
            f"  {cols[1]:<{W_COND}}"
            f"  {cols[2]:>{W_VAL}}"
            f"  {cols[3]:>{W_TEST}}"
            f"  {cols[4]:>{W_GAP}}"
            f"  {cols[5]:>{W_DELTA}}"
            f"  {cols[6]}"
        )

    sep = (
        "  "
        + "─" * W_RUN
        + "  "
        + "─" * W_COND
        + "  "
        + "─" * W_VAL
        + "  "
        + "─" * W_TEST
        + "  "
        + "─" * W_GAP
        + "  "
        + "─" * W_DELTA
        + "  "
        + "─" * W_VERDICT
    )

    print(
        _row("Run", "Condition", "Val fitness", "Test EM", "Gap", "Δ vs O", "Verdict")
    )
    print(sep)

    gap_by_label: dict[str, float | None] = {}
    verdict_by_label: dict[str, str] = {}
    cross_metric_rows: list[str] = []

    for row in rows:
        label = row["label"]
        is_ctrl = label == "O"
        is_inv = row["is_invalidated"]
        fm = row["fitness_metric"]

        val_fitness = row["val_fitness"]
        val_em_redis = row["val_em_redis"]
        test_em = row["test_em"]

        # ── Compute gap and delta ──────────────────────────────────────────────
        if fm == "F1":
            # Cross-metric: gap uses val_F1 (not directly comparable to EM gap)
            # For comparison with control we use gap_EM = val_EM - test_EM
            gap_f1 = (
                val_fitness - test_em
                if val_fitness is not None and test_em is not None
                else None
            )
            gap_em = (
                val_em_redis - test_em
                if val_em_redis is not None and test_em is not None
                else None
            )
            gap = gap_em  # use EM gap for delta comparison
            gap_by_label[label] = gap

            # Val fitness display: show both F1 and EM
            if val_fitness is not None and val_em_redis is not None:
                val_str = f"F1={format_pct(val_fitness)} EM={format_pct(val_em_redis)}"
            elif val_fitness is not None:
                val_str = f"F1={format_pct(val_fitness)}"
            else:
                val_str = "N/A"

            test_str = format_pct(test_em) if test_em is not None else "N/A"

            # Gap display: show both F1 gap and EM gap
            if gap_f1 is not None and gap_em is not None:
                gap_str = f"F1={format_pp(gap_f1)} EM={format_pp(gap_em)}"
            elif gap_f1 is not None:
                gap_str = f"F1={format_pp(gap_f1)}"
            else:
                gap_str = "N/A"
        else:
            # Standard: gap = val_EM - test_EM
            gap = (
                val_fitness - test_em
                if val_fitness is not None and test_em is not None
                else None
            )
            gap_by_label[label] = gap

            val_str = format_pct(val_fitness)
            test_str = format_pct(test_em) if test_em is not None else "N/A"
            gap_str = format_pp(gap) if gap is not None else "N/A"
            if val_only:
                test_str = "—"
                gap_str = "—"

        # ── Delta vs control ──────────────────────────────────────────────────
        if is_ctrl:
            delta_pp = None
            delta_str = "—"
        elif ctrl_gap is not None and gap is not None:
            # Positive delta = gap REDUCED (good); negative = gap INFLATED (bad)
            delta_pp = (ctrl_gap - gap) * 100
            delta_str = format_pp(delta_pp)
        else:
            delta_pp = None
            delta_str = "N/A"

        # ── Verdict ───────────────────────────────────────────────────────────
        verdict = verdict_for_gap_delta(
            delta_pp if delta_pp is not None else 0.0,
            test_em,
            ctrl_test_em,
            is_invalidated=is_inv,
            is_control=is_ctrl,
        )
        if test_em is None and not is_ctrl and not is_inv and not val_only:
            verdict = "NO TEST DATA"
        elif val_only and not is_ctrl:
            verdict = "(val only)"
        verdict_by_label[label] = verdict

        # ── Footnotes ─────────────────────────────────────────────────────────
        footnote = ""
        if is_inv:
            footnote = " [†]"
        elif fm == "F1":
            footnote = " [‡]"

        cond_display = row["condition"] + footnote

        print(_row(label, cond_display, val_str, test_str, gap_str, delta_str, verdict))

        # Collect cross-metric note
        if fm == "F1":
            cross_metric_rows.append(label)

    print()

    # ── Footnotes ─────────────────────────────────────────────────────────────
    print(
        "[†] Run Q invalidated (Amendment 2: stage_timeout too short for 600-sample eval)."
    )
    if cross_metric_rows:
        print(
            "[‡] Run F: val fitness is F1. Gap(EM) uses EM frontier from Redis"
            f" (`{FRONTIER_EM_KEY_SUFFIX}`); used for Δ vs O."
        )
    print()

    if markdown_only:
        return

    # ── Gate verdicts ─────────────────────────────────────────────────────────
    print("─" * 70)
    print("Gate verdicts")
    print()

    # Gate C: Q vs O (but Q is invalidated)
    print("Gate C (size effect, Q vs O):", end=" ")
    if RUNS[2][4]:  # Q is_invalidated
        print("UNANSWERABLE — Run Q invalidated (Amendment 2).")
    else:
        v = verdict_by_label.get("Q", "NO DATA")
        print(f"{v}")

    # Gate B: R vs O (rotation effect)
    print("Gate B (rotation effect, R vs O):", end=" ")
    r_verdict = verdict_by_label.get("R", "NO DATA")
    r_gap = gap_by_label.get("R")
    o_gap = gap_by_label.get("O")
    if r_gap is not None and o_gap is not None:
        delta_r = (o_gap - r_gap) * 100
        print(
            f"{r_verdict} — gap(R)={format_pp(r_gap)}, gap(O)={format_pp(o_gap)}, Δ={format_pp(delta_r)}."
        )
    else:
        print(f"{r_verdict}")

    # Gate E: F vs O (metric effect)
    print("Gate E (metric effect, F vs O):", end=" ")
    f_verdict = verdict_by_label.get("F", "NO DATA")
    f_gap = gap_by_label.get("F")  # EM gap for F
    if f_gap is not None and o_gap is not None:
        delta_f = (o_gap - f_gap) * 100
        print(
            f"{f_verdict} — gap_EM(F)={format_pp(f_gap)},"
            f" gap(O)={format_pp(o_gap)}, Δ={format_pp(delta_f)}."
        )
    else:
        print(f"{f_verdict}")

    print()
    print(
        "Thresholds (03_plan.md): POSITIVE ≥5pp reduction + floors, SUGGESTIVE 2–5pp, NULL <2pp, NEGATIVE ≤−2pp."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Val-test gap analysis for hotpotqa_val_gap experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Experiment-specific tool. Run specs (O/R/Q/F), gate thresholds, and Run Q
invalidation status are hardcoded from 03_plan.md. Not reusable without rework.

For Phase 5: run after test evals complete (run_test_eval.sh). Use --markdown
to get a table ready for copy-paste into 05_results.md.
""",
    )
    parser.add_argument(
        "--results",
        default=DEFAULT_RESULTS_PATH,
        metavar="PATH",
        help=f"Path to test_evals/results.json (default: {DEFAULT_RESULTS_PATH})",
    )
    parser.add_argument(
        "--val-only",
        action="store_true",
        help="Show best val fitness from Redis only — skip test eval data",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Output only the markdown table (no gate verdicts) for copy-paste into 05_results.md",
    )
    parser.add_argument("--redis-host", default="localhost")
    parser.add_argument("--redis-port", type=int, default=6379)
    args = parser.parse_args()

    if args.val_only and args.markdown:
        print("--val-only and --markdown are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    run_analysis(
        val_only=args.val_only,
        results_path=args.results,
        markdown_only=args.markdown,
        redis_host=args.redis_host,
        redis_port=args.redis_port,
    )


if __name__ == "__main__":
    main()
