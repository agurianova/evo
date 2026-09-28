#!/usr/bin/env python3
"""
Per-generation stats table for the HotpotQA P1×P2 factorial experiment.

Parses run_X.log files for operational metrics (wall-clock, mutations,
acceptance rate) and reads Redis history for fitness metrics.

Design:
  Run K — DB 10, standard pipeline,     static    (control: no P1, no P2)
  Run L — DB 11, hotpotqa_asi pipeline, static_a  (P2 only: ASI formatter)
  Run M — DB 12, standard pipeline,     static_r  (P1 only: rotation)
  Run N — DB 13, hotpotqa_asi pipeline, static_ra (P1+P2: rotation + ASI)

Usage:
    python experiments/hotpotqa_nlp_prompts/gen_stats.py             # all runs, print table
    python experiments/hotpotqa_nlp_prompts/gen_stats.py --csv out.csv
    python experiments/hotpotqa_nlp_prompts/gen_stats.py --run G     # single run
"""

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import re

import redis as redis_lib

PROJ = Path(__file__).parent.parent.parent
RUNS = [
    {
        "label": "K",
        "db": 0,
        "prefix": "chains/hotpotqa/static",
        "condition": "control (default prompts, fixed-300)",
        "log": PROJ / "experiments/hotpotqa_nlp_prompts/run_k.log",
    },
    {
        "label": "L",
        "db": 1,
        "prefix": "chains/hotpotqa/static_r",
        "condition": "NLP prompts + rotation",
        "log": PROJ / "experiments/hotpotqa_nlp_prompts/run_l.log",
    },
    {
        "label": "M",
        "db": 2,
        "prefix": "chains/hotpotqa/static_r",
        "condition": "NLP prompts + rotation",
        "log": PROJ / "experiments/hotpotqa_nlp_prompts/run_m.log",
    },
    {
        "label": "N",
        "db": 3,
        "prefix": "chains/hotpotqa/static_r",
        "condition": "NLP prompts + rotation",
        "log": PROJ / "experiments/hotpotqa_nlp_prompts/run_n.log",
    },
]


# ── Log parsing ────────────────────────────────────────────────────────────────

_TS = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)")
_IDLE = re.compile(r"Phase 1: Idle confirmed")
_GEN = re.compile(r"selecting elites \(gen=(\d+),")
_CREATED = re.compile(r"Phase 2: Created (\d+) mutant\(s\)")
_INGEST = re.compile(
    r"Ingest done \| added=(\d+), rejected_validation=(\d+), rejected_strategy=(\d+)"
)
_PHASE6 = re.compile(r"Phase 6: Refresh DAGs finished")


def _parse_ts(line: str) -> datetime | None:
    m = _TS.match(line)
    return datetime.fromisoformat(m.group(1)) if m else None


def parse_log(log_path: Path) -> list[dict]:
    """Parse a run log into a list of per-generation dicts."""
    if not log_path.exists():
        return []

    text = log_path.read_text(errors="replace")
    lines = text.splitlines()

    gens: list[dict] = []
    current: dict | None = None

    for line in lines:
        ts = _parse_ts(line)

        if _IDLE.search(line):
            if current is not None and current.get("gen") is not None:
                if current.get("end_ts") is None:
                    current["end_ts"] = ts
                _finalize(current)
                gens.append(current)
            current = {
                "start_ts": ts,
                "end_ts": None,
                "gen": None,
                "mutations_created": 0,
                "added": 0,
                "rejected_validation": 0,
                "rejected_strategy": 0,
            }
            continue

        if current is None:
            continue

        m = _GEN.search(line)
        if m:
            current["gen"] = int(m.group(1))
            continue

        m = _CREATED.search(line)
        if m:
            current["mutations_created"] += int(m.group(1))
            continue

        m = _INGEST.search(line)
        if m:
            current["added"] += int(m.group(1))
            current["rejected_validation"] += int(m.group(2))
            current["rejected_strategy"] += int(m.group(3))
            continue

        if _PHASE6.search(line):
            current["end_ts"] = ts
            continue

    if current is not None and current.get("gen") is not None:
        _finalize(current)
        gens.append(current)

    # De-duplicate: keep only last record per generation number
    by_gen: dict[int, dict] = {}
    for g in gens:
        gn = g["gen"]
        if gn not in by_gen:
            by_gen[gn] = g
        else:
            by_gen[gn]["mutations_created"] += g["mutations_created"]
            by_gen[gn]["added"] += g["added"]
            by_gen[gn]["rejected_validation"] += g["rejected_validation"]
            by_gen[gn]["rejected_strategy"] += g["rejected_strategy"]
            if g.get("end_ts"):
                by_gen[gn]["end_ts"] = g["end_ts"]
            _finalize(by_gen[gn])

    return sorted(by_gen.values(), key=lambda x: x["gen"])


def _finalize(g: dict):
    total = g["mutations_created"]
    if total > 0:
        g["acceptance_rate"] = g["added"] / total
    else:
        g["acceptance_rate"] = None

    if g.get("start_ts") and g.get("end_ts"):
        delta = (g["end_ts"] - g["start_ts"]).total_seconds()
        g["wall_clock_min"] = round(delta / 60, 1)
    else:
        g["wall_clock_min"] = None


# ── Redis fitness history ──────────────────────────────────────────────────────


def get_fitness_series(db: int, prefix: str) -> list[tuple[float, float]]:
    r = redis_lib.Redis(host="localhost", port=6379, db=db)
    key = f"{prefix}:metrics:history:program_metrics:valid_frontier_fitness"
    if r.type(key) != b"list":
        return []
    return [
        (json.loads(raw)["t"], json.loads(raw)["v"]) for raw in r.lrange(key, 0, -1)
    ]


def get_series(db: int, prefix: str, metric: str) -> list[tuple[float, float]]:
    r = redis_lib.Redis(host="localhost", port=6379, db=db)
    key = f"{prefix}:metrics:history:program_metrics:{metric}"
    if r.type(key) != b"list":
        return []
    return [
        (json.loads(raw)["t"], json.loads(raw)["v"]) for raw in r.lrange(key, 0, -1)
    ]


def sample_at(series: list[tuple[float, float]], ts: datetime | None) -> float | None:
    if not series or ts is None:
        return None
    target = ts.timestamp()
    val = None
    for t, v in series:
        if t <= target:
            val = v
        else:
            break
    return val


# ── Main ───────────────────────────────────────────────────────────────────────


def build_table(run: dict) -> list[dict]:
    gens = parse_log(run["log"])
    if not gens:
        return []

    prefix = run["prefix"]
    frontier_series = get_fitness_series(run["db"], prefix)
    mean_series = get_series(run["db"], prefix, "valid_gen_fitness_mean")
    std_series = get_series(run["db"], prefix, "valid_gen_fitness_std")
    r = redis_lib.Redis(host="localhost", port=6379, db=run["db"])
    arch_key = f"{prefix}:metrics:history:evolution_engine:size_fitness_island"
    archive_raw = r.lrange(arch_key, 0, -1) if r.type(arch_key) == b"list" else []
    archive_series = [(json.loads(x)["t"], json.loads(x)["v"]) for x in archive_raw]

    rows = []
    for g in gens:
        end_ts = g.get("end_ts")
        frontier = sample_at(frontier_series, end_ts)
        mean_em = sample_at(mean_series, end_ts)
        std_em = sample_at(std_series, end_ts)
        archive_size = sample_at(archive_series, end_ts)

        rows.append(
            {
                "run": run["label"],
                "condition": run["condition"],
                "gen": g["gen"],
                "frontier_EM_%": round(frontier * 100, 1)
                if frontier is not None
                else None,
                "gen_mean_EM_%": round(mean_em * 100, 1)
                if mean_em is not None
                else None,
                "gen_std_EM_%": round(std_em * 100, 2) if std_em is not None else None,
                "archive_size": int(archive_size) if archive_size is not None else None,
                "mutations_created": g["mutations_created"],
                "added": g["added"],
                "rejected_val": g["rejected_validation"],
                "rejected_arch": g["rejected_strategy"],
                "accept_rate_%": round(g["acceptance_rate"] * 100, 0)
                if g["acceptance_rate"] is not None
                else None,
                "wall_clock_min": g["wall_clock_min"],
            }
        )
    return rows


def print_table(rows: list[dict], run_label: str, condition: str):
    if not rows:
        print(f"Run {run_label} ({condition}): no data")
        return

    cols = [
        ("gen", 4),
        ("frontier_EM_%", 12),
        ("gen_mean_EM_%", 13),
        ("gen_std_EM_%", 12),
        ("archive_size", 7),
        ("mutations_created", 7),
        ("added", 6),
        ("rejected_val", 12),
        ("rejected_arch", 13),
        ("accept_rate_%", 11),
        ("wall_clock_min", 15),
    ]

    header = " | ".join(c.ljust(w) for c, w in cols)
    print(f"\n=== Run {run_label} ({condition}) ===")
    print(header)
    print("-" * len(header))
    for row in rows:
        parts = []
        for col, width in cols:
            v = row.get(col)
            parts.append(("—" if v is None else str(v)).ljust(width))
        print(" | ".join(parts))


def detect_plateau(rows: list[dict], window: int = 5) -> str:
    frontiers = [r["frontier_EM_%"] for r in rows if r["frontier_EM_%"] is not None]
    if len(frontiers) < window:
        return "insufficient data"
    last = frontiers[-window:]
    delta = last[-1] - last[0]
    if delta > 1.0:
        return f"rising (+{delta:.1f}pp over last {window} gens)"
    elif delta > 0:
        return f"slowly rising (+{delta:.1f}pp over last {window} gens)"
    else:
        return f"FLAT/STAGNANT ({delta:.1f}pp over last {window} gens)"


def print_factorial_summary(all_rows_by_run: dict[str, list[dict]]):
    """Print a P1×P2 2×2 summary at current gen counts."""
    print("\n=== P1×P2 Factorial Summary ===")
    print(f"{'':12} | P2 OFF (std)   | P2 ON (ASI)")
    print("-" * 45)
    for p1_label, no_p2, with_p2 in [("P1 OFF", "K", "L"), ("P1 ON", "M", "N")]:

        def last_em(label):
            rows = all_rows_by_run.get(label, [])
            vals = [r["frontier_EM_%"] for r in rows if r["frontier_EM_%"] is not None]
            return f"{vals[-1]}%" if vals else "—"

        print(
            f"{p1_label:12} | {no_p2}={last_em(no_p2):12} | {with_p2}={last_em(with_p2)}"
        )
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", choices=["K", "L", "M", "N"], help="Single run label")
    parser.add_argument("--csv", help="Write all data to CSV file")
    args = parser.parse_args()

    runs_to_show = [r for r in RUNS if args.run is None or r["label"] == args.run]

    all_rows = []
    all_rows_by_run: dict[str, list[dict]] = {}
    for run in runs_to_show:
        rows = build_table(run)
        all_rows.extend(rows)
        all_rows_by_run[run["label"]] = rows
        print_table(rows, run["label"], run["condition"])
        if rows:
            print(f"  Trend (last 5 gens): {detect_plateau(rows)}")
            last = rows[-1]
            print(
                f"  Latest: gen={last['gen']}  "
                f"frontier={last['frontier_EM_%']}%  "
                f"accept={last['accept_rate_%']}%  "
                f"archive={last['archive_size']}  "
                f"wall={last['wall_clock_min']}min"
            )

    if args.run is None:
        print_factorial_summary(all_rows_by_run)

    if args.csv and all_rows:
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_rows[0].keys())
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"\nCSV written: {args.csv}")


if __name__ == "__main__":
    main()
