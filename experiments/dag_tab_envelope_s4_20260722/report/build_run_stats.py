"""Reduce a dag_tab run directory to the per-program and per-LLM-call series the
figures need, so the plots never re-read the multi-hundred-megabyte run tree.

Usage: python build_run_stats.py <run_dir> <arm-slug>
"""

from datetime import datetime
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).parent
VIZ = HERE / "viz"

LLM_CALL = re.compile(r"\[LLM_CALL\] (\{.*\})")


def parse_ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def program_series(run_dir: Path) -> tuple[list[dict], int]:
    """Rows for children whose evaluation *finished*, plus the incomplete count.

    A child still in the pipeline when the run exits is persisted with empty
    metrics. Counting it as invalid would blame the mutator for a teardown race,
    so it is excluded from every rate and reported on its own.
    """
    root = run_dir / "storage" / "dag_tab" / "programs"
    rows, incomplete = [], 0
    for f in root.glob("*.json"):
        d = json.loads(f.read_text())
        m = d["metrics"]
        if "is_valid" not in m:
            incomplete += 1
            continue
        rows.append(
            {
                "id": d["id"],
                "created_at": d["created_at"],
                "iteration": d.get("iteration"),
                "generation": d["lineage"].get("generation"),
                "fitness": m.get("fitness"),
                "is_valid": m.get("is_valid"),
                "node_count": m.get("graph_node_count"),
                "max_depth": m.get("graph_max_depth"),
                "feature_count": m.get("generated_feature_count"),
            }
        )
    rows.sort(key=lambda r: r["created_at"])
    t0 = parse_ts(rows[0]["created_at"])
    for i, r in enumerate(rows):
        r["index"] = i
        r["elapsed_s"] = (parse_ts(r["created_at"]) - t0).total_seconds()
    return rows, incomplete


LOG_TS = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)")


def run_seconds(run_dir: Path) -> float:
    """Process lifetime, from the log's first line to its last.

    The last *completed* child can be minutes before the process exits when a
    straggler LLM call runs out its timeout, so program timestamps alone would
    understate how long the run occupied the machine.
    """
    lines = (
        sorted(run_dir.glob("evolution_*.log"))[0]
        .read_text(errors="replace")
        .splitlines()
    )
    stamps = [m.group(1) for line in (lines[0], lines[-1]) if (m := LOG_TS.match(line))]
    return (parse_ts(stamps[-1]) - parse_ts(stamps[0])).total_seconds()


def llm_series(run_dir: Path) -> list[dict]:
    logs = sorted(run_dir.glob("evolution_*.log"))
    calls = []
    for log in logs:
        with log.open(errors="replace") as fh:
            for line in fh:
                m = LLM_CALL.search(line)
                if not m:
                    continue
                try:
                    e = json.loads(m.group(1))
                except json.JSONDecodeError:
                    continue
                calls.append(
                    {
                        "stage": e.get("stage"),
                        "model": e.get("model"),
                        "ok": e.get("ok"),
                        "latency_ms": e.get("latency_ms"),
                        "tokens_in": e.get("tokens_in"),
                        "tokens_out": e.get("tokens_out"),
                        "tokens_reasoning": e.get("tokens_reasoning"),
                        "error_type": e.get("error_type"),
                    }
                )
    return calls


def main() -> None:
    run_dir, arm = Path(sys.argv[1]), sys.argv[2]
    VIZ.mkdir(exist_ok=True)
    programs, incomplete = program_series(run_dir)
    stats = {
        "arm": arm,
        "run_dir": str(run_dir),
        "incomplete": incomplete,
        "run_seconds": run_seconds(run_dir),
        "programs": programs,
        "llm_calls": llm_series(run_dir),
    }
    out = VIZ / f"{arm}_stats.json"
    out.write_text(json.dumps(stats))
    valid = [p for p in stats["programs"] if p["is_valid"] == 1.0]
    errors = [c for c in stats["llm_calls"] if not c["ok"]]
    print(
        f"{out.name}: {len(stats['programs'])} completed "
        f"({len(valid)} valid, {incomplete} incomplete), "
        f"{len(stats['llm_calls'])} LLM calls, "
        f"{len(errors)} errors, best {max(p['fitness'] for p in valid):.6f}"
    )


if __name__ == "__main__":
    main()
