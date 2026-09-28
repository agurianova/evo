"""Post-run assertions for the synthetic noise-gate smoke pair.

Usage: python experiments/noise_gate/checks_smoke.py <RUN_ROOT>
Reads <RUN_ROOT>/{POINT,PAIRED} produced by launch_smoke_synthetic.sh.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

N_SAMPLES = 64
GATE_TAG = "[PairedBootstrapArchiveSelector]"
POINT_TAG = "[SumArchiveSelector]"

failures: list[str] = []


def check(label: str, ok: bool, detail: str) -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}: {detail}")
    if not ok:
        failures.append(label)


def load_programs(run_dir: Path) -> dict[str, dict]:
    programs = {}
    for f in (run_dir / "storage" / "toy_noise_gate" / "programs").glob("*.json"):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(data, dict) and "id" in data:
            programs[data["id"]] = data
    return programs


def read_log(run_dir: Path) -> str:
    logs = sorted(run_dir.rglob("*.log"))
    return "\n".join(p.read_text(errors="replace") for p in logs)


def replay_flips(programs: dict[str, dict]) -> list[str]:
    """In-run flips are stochastic (a tiny run may only see twin challenges);
    replay every stored higher-mean pair through the real selectors instead."""
    from loguru import logger

    from gigaevo.evolution.strategies.map_elites import SumArchiveSelector
    from gigaevo.evolution.strategies.paired_selectors import (
        PairedBootstrapArchiveSelector,
    )
    from gigaevo.programs.program import Program

    logger.remove()
    progs = {}
    for pid, data in programs.items():
        slim = {k: v for k, v in data.items() if k != "stage_results"}
        progs[pid] = Program(**slim)
    point = SumArchiveSelector(["fitness"], [True])
    paired = PairedBootstrapArchiveSelector(["fitness"], [True])
    flips = []
    for new_id, new in progs.items():
        for cur_id, cur in progs.items():
            if new.metrics["fitness"] <= cur.metrics["fitness"]:
                continue
            if point(new, cur) and not paired(new, cur):
                flips.append(f"{new_id[:8]} vs {cur_id[:8]}")
    return flips


def main(run_root: Path) -> int:
    arms = {}
    for arm in ("POINT", "PAIRED"):
        run_dir = run_root / arm
        programs = load_programs(run_dir)
        log = read_log(run_dir)
        arms[arm] = (programs, log)

        scored = {
            pid: p
            for pid, p in programs.items()
            if isinstance(p.get("metrics"), dict) and "fitness" in p["metrics"]
        }
        check(
            f"{arm}: run completed",
            "Duration:" in log,
            f"{len(programs)} stored programs, {len(scored)} scored",
        )
        vec_ok = [
            pid
            for pid, p in scored.items()
            if isinstance(p.get("metadata"), dict)
            and isinstance(p["metadata"].get("per_sample_scores"), list)
            and len(p["metadata"]["per_sample_scores"]) == N_SAMPLES
        ]
        check(
            f"{arm}: transport (metadata vector, len {N_SAMPLES})",
            len(scored) > 0 and len(vec_ok) == len(scored),
            f"{len(vec_ok)}/{len(scored)} scored programs carry the vector",
        )
        coherent = sum(
            1
            for pid in vec_ok
            if abs(
                sum(scored[pid]["metadata"]["per_sample_scores"]) / N_SAMPLES
                - scored[pid]["metrics"]["fitness"]
            )
            <= 1e-4
        )
        check(
            f"{arm}: vector coheres with fitness",
            coherent == len(vec_ok),
            f"{coherent}/{len(vec_ok)} within 1e-4",
        )
        llm_io = run_dir / "llm_io"
        leaks = (
            [
                f
                for f in llm_io.rglob("*.jsonl")
                if "per_sample_scores" in f.read_text(errors="replace")
            ]
            if llm_io.exists()
            else []
        )
        check(
            f"{arm}: prompt hygiene",
            llm_io.exists() and not leaks,
            "no per_sample_scores in llm_io"
            if not leaks
            else f"LEAKED in {[f.name for f in leaks]}",
        )

    point_programs, point_log = arms["POINT"]
    paired_programs, paired_log = arms["PAIRED"]

    check(
        "POINT: stock rule decided (no gate lines)",
        GATE_TAG not in point_log and POINT_TAG in point_log,
        f"{point_log.count(POINT_TAG)} SumArchiveSelector decisions, 0 gate lines",
    )

    gate_lines = [ln for ln in paired_log.splitlines() if GATE_TAG in ln]
    decisions = [ln for ln in gate_lines if "P(better)=" in ln]
    fallbacks = [ln for ln in gate_lines if "fallback" in ln]
    accepts = sum("-> ACCEPT" in ln for ln in decisions)
    rejects = sum("-> REJECT" in ln for ln in decisions)
    check(
        "PAIRED: gate consumed decisions",
        len(decisions) > 0,
        f"{len(decisions)} paired decisions ({accepts} ACCEPT / {rejects} REJECT), "
        f"{len(fallbacks)} fallbacks",
    )

    fitness = {
        pid: p["metrics"]["fitness"]
        for pid, p in paired_programs.items()
        if isinstance(p.get("metrics"), dict) and "fitness" in p["metrics"]
    }
    flips = []
    pat = re.compile(r"\] (\S+) vs (\S+) -> REJECT \(P\(better\)=([0-9.]+)")
    for ln in decisions:
        m = pat.search(ln)
        if not m:
            continue
        new_id, cur_id, p_better = m.group(1), m.group(2), float(m.group(3))
        if (
            new_id in fitness
            and cur_id in fitness
            and fitness[new_id] > fitness[cur_id]
        ):
            flips.append(f"{new_id[:8]} vs {cur_id[:8]} P={p_better:.2f}")
    flip_src = "in-run"
    if not flips:
        flip_src = "stored-pair replay"
        flips = replay_flips(paired_programs)
    check(
        "PAIRED: gate flips point-rule accepts",
        len(flips) >= 1,
        f"{len(flips)} higher-mean challengers REJECTed ({flip_src}): "
        + ", ".join(flips[:5]),
    )

    print(f"\n{'SMOKE OK' if not failures else 'SMOKE FAILED: ' + ', '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    raise SystemExit(main(Path(sys.argv[1])))
