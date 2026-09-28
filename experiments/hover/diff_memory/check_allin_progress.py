#!/usr/bin/env python3
"""In-progress treatment checks T1-T7 for the ALL-IN pair.

Prereg: prereg_bd3d_noise_allin_20260711.md. Each check traces a treatment's
output to the decision it changes (consumption, not just execution). Prints a
PASS/WARN/FAIL table per run and exits 1 if any FAIL (for the 1h hard gate,
pass --hard-gate to restrict failing checks to the abort set).

Usage:
    check_allin_progress.py [--env latest_allin.env] [--hard-gate]
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import sys

import numpy as np

EXP_DIR = Path(__file__).resolve().parent
PROJ = EXP_DIR.parents[2]
sys.path.insert(0, str(PROJ))

from gigaevo.evolution.mutation.constants import (  # noqa: E402
    MUTATION_MEMORY_LINEAGE_BLOCKED_IDS_METADATA_KEY,
)
from gigaevo.memory.read.bootstrap import bootstrap_ev_samples  # noqa: E402
from gigaevo.memory.read.reputation import beta_binomial_posterior  # noqa: E402

SELECTION_TAG = "[MEMORY_READ_SELECTION] "
GATE_TAG = "[PairedBootstrapArchiveSelector]"
STRUCT_KEYS = ("hop_depth", "passages_fetched", "instr_chars")
COHERENCE_TOL = 1e-4
MIN_CELLS_1H = 5
CREDITING_MIN_INJECTED_CHILDREN = 3

HARD_GATE_IDS = {"T1", "T3", "T5-W", "T7", "LIVE"}


def read_env(path: Path) -> dict:
    env = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


def load_pids(path: Path) -> dict:
    runs = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) == 4:
            runs[parts[0]] = {
                "pid": int(parts[1]),
                "log": Path(parts[2]),
                "out": Path(parts[3]),
            }
    return runs


def load_programs(run_dir: Path) -> list[dict]:
    programs = []
    for path in run_dir.glob("storage/*/programs/*.json"):
        try:
            programs.append(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    return programs


def load_cards(bank_dir: Path) -> list[dict]:
    path = bank_dir / "cards.json"
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    if isinstance(raw, dict):
        raw = raw.get("cards", raw)
    if isinstance(raw, dict):
        raw = list(raw.values())
    return raw if isinstance(raw, list) else []


def direct_events(card: dict) -> list[dict]:
    return [
        e
        for e in card.get("gain_events", [])
        if not e.get("invalid") and not e.get("unused") and not e.get("founding")
    ]


def check_liveness(pid: int, log: Path) -> tuple[str, str]:
    alive = Path(f"/proc/{pid}").exists()
    tail = ""
    if log.exists():
        lines = log.read_text(errors="replace").splitlines()
        errors = [ln for ln in lines[-200:] if "Traceback" in ln or "CRITICAL" in ln]
        tail = f"{len(lines)} log lines, {len(errors)} recent tracebacks"
    status = "PASS" if alive else "FAIL"
    return status, f"pid {pid} {'alive' if alive else 'DEAD'}; {tail}"


def check_t1_occupancy(run_dir: Path) -> tuple[str, str]:
    cells = {}
    for path in run_dir.glob("storage/*/archives/island_*.json"):
        data = json.loads(path.read_text())
        cells[path.stem] = len(data)
    total = sum(cells.values())
    status = "PASS" if total > MIN_CELLS_1H else "FAIL"
    return (
        status,
        f"{total} occupied cells {dict(cells)} (1h bar: >{MIN_CELLS_1H}; M1 end bar: >=35)",
    )


def check_t2_struct_metrics(programs: list[dict]) -> tuple[str, str]:
    valid = [p for p in programs if p.get("metrics", {}).get("is_valid") == 1.0]
    if not valid:
        return "WARN", "no valid programs yet"
    values = {
        k: [p["metrics"].get(k) for p in valid if k in p.get("metrics", {})]
        for k in STRUCT_KEYS
    }
    missing = [k for k, v in values.items() if not v]
    if missing:
        return "FAIL", f"metrics absent: {missing}"
    flat = {k: (len(set(v)), max(v)) for k, v in values.items()}
    all_zero = [k for k, v in values.items() if max(v) == 0]
    status = (
        "FAIL"
        if all_zero
        else ("WARN" if any(n == 1 for n, _ in flat.values()) else "PASS")
    )
    hop3 = sum(1 for v in values["hop_depth"] if v >= 3) / len(values["hop_depth"])
    return (
        status,
        f"distinct(max) per axis {flat}; hop>=3 share {hop3:.1%} (control 12.7%)",
    )


def check_t3_transport(programs: list[dict]) -> tuple[str, str]:
    scored = [
        p
        for p in programs
        if p.get("metrics", {}).get("is_valid") == 1.0
        and "fitness" in p.get("metrics", {})
    ]
    if not scored:
        return "WARN", "no scored programs yet"
    missing, incoherent, lengths = 0, 0, Counter()
    for p in scored:
        vec = p.get("metadata", {}).get("per_sample_scores")
        if not vec:
            missing += 1
            continue
        lengths[len(vec)] += 1
        if abs(statistics.fmean(vec) - p["metrics"]["fitness"]) > COHERENCE_TOL:
            incoherent += 1
    status = "PASS" if missing == 0 and incoherent == 0 else "FAIL"
    return (
        status,
        f"{len(scored)} scored: {missing} missing vector, {incoherent} incoherent, lens {dict(lengths)}",
    )


def check_t4_gate(log: Path) -> tuple[str, str]:
    accept = reject = fallback = 0
    if log.exists():
        for line in open(log, errors="replace"):
            if GATE_TAG in line:
                if "ACCEPT" in line:
                    accept += 1
                elif "REJECT" in line:
                    reject += 1
                elif "fallback" in line:
                    fallback += 1
    consulted = accept + reject
    if fallback:
        status = "FAIL"
    elif consulted == 0:
        status = "WARN"  # no occupied-cell challenge yet; escalate manually at 3h
    else:
        status = "PASS"
    return (
        status,
        f"{consulted} paired decisions ({accept} ACCEPT / {reject} REJECT), {fallback} fallbacks",
    )


def check_t5w_crediting(cards: list[dict], programs: list[dict]) -> tuple[str, str]:
    injected_children = sum(
        1
        for p in programs
        if p.get("metrics", {}).get("is_valid") == 1.0
        and p.get("metadata", {}).get("memory_injected_idea_ids")
    )
    direct = [e for c in cards for e in direct_events(c)]
    noisy = [e for e in direct if float(e.get("gain_se", 0.0)) > 0.0]
    if injected_children < CREDITING_MIN_INJECTED_CHILDREN:
        return (
            "WARN",
            f"only {injected_children} valid card-injected children; re-check later",
        )
    status = "PASS" if noisy else "FAIL"
    return status, (
        f"{len(noisy)}/{len(direct)} DIRECT events carry gain_se>0 "
        f"({injected_children} valid injected children; se==0 on vector-eligible events = degradation)"
    )


def check_t5r_consumption(cards: list[dict]) -> tuple[str, str]:
    max_db, max_dq, n_checked = 0.0, 0.0, 0
    for card in cards:
        events = direct_events(card)
        gains = [float(e.get("gain", 0.0)) for e in events]
        ses = [float(e.get("gain_se", 0.0)) for e in events]
        if not gains or not any(s > 0 for s in ses):
            continue
        n_checked += 1
        with_se = beta_binomial_posterior(gains, event_ses=ses)
        without = beta_binomial_posterior(gains)
        max_db = max(max_db, abs(with_se.posterior_b - without.posterior_b))
        rng_a, rng_b = np.random.default_rng(0), np.random.default_rng(0)
        jittered = bootstrap_ev_samples(gains, 0.0, 1.0, 4000, rng_a, ses=ses)
        exact = bootstrap_ev_samples(gains, 0.0, 1.0, 4000, rng_b, ses=None)
        for q in (0.2, 0.8):
            max_dq = max(
                max_dq, abs(float(np.quantile(jittered, q) - np.quantile(exact, q)))
            )
    if n_checked == 0:
        return "WARN", "no cards with noisy events yet (see T5-W)"
    status = "PASS" if (max_db > 0 or max_dq > 0) else "FAIL"
    return status, (
        f"{n_checked} noisy cards replayed: max |d posterior_b|={max_db:.4f}, "
        f"max |d EV q20/q80|={max_dq:.5f} (0 on both = se stored but never consumed)"
    )


def check_t6_memory_health(log: Path) -> tuple[str, str]:
    selections = []
    if log.exists():
        for line in open(log, errors="replace"):
            idx = line.find(SELECTION_TAG)
            if idx >= 0:
                try:
                    selections.append(json.loads(line[idx + len(SELECTION_TAG) :]))
                except json.JSONDecodeError:
                    pass
    if not selections:
        return "WARN", "no MEMORY_READ_SELECTION events yet"
    injected = [s for s in selections if s.get("selected_ids")]
    frac = len(injected) / len(selections)
    per_card = Counter(cid for s in injected for cid in s["selected_ids"])
    top = per_card.most_common(1)[0] if per_card else ("-", 0)
    status = "PASS" if 0.10 <= frac <= 0.70 and top[1] < 60 else "WARN"
    return (
        status,
        f"injection {len(injected)}/{len(selections)} ({frac:.1%}; band 30-55%), top card {top[1]}x (bar <60)",
    )


ACTIVE_MEMORY_METADATA = (
    "memory_used",
    "memory_selected_idea_ids",
    "memory_injected_idea_ids",
    MUTATION_MEMORY_LINEAGE_BLOCKED_IDS_METADATA_KEY,
    "memory_base_selected_idea_ids",
    "memory_candidate_slate",
    "memory_no_card_control",
)


def check_t7_purity(run_dir: Path, log: Path, programs: list[dict]) -> tuple[str, str]:
    # The engine stamps inert memory_* keys (memory_used=False, empty id lists,
    # memory_base_* snapshots feeding the paired gate) on EVERY child in both
    # arms — only truthy ACTIVE signals count as contamination.
    memory_lines = 0
    if log.exists():
        memory_lines = sum(
            1 for line in open(log, errors="replace") if "[MEMORY_" in line
        )
    banks = list(run_dir.glob("**/cards.json")) + list(
        run_dir.glob("memory/memory_events.jsonl")
    )
    tainted = sum(
        1
        for p in programs
        if any(p.get("metadata", {}).get(k) for k in ACTIVE_MEMORY_METADATA)
    )
    clean = memory_lines == 0 and not banks and tainted == 0
    return ("PASS" if clean else "FAIL"), (
        f"{memory_lines} MEMORY_ log lines, {len(banks)} bank/event files, "
        f"{tainted} programs with ACTIVE memory signals"
    )


def info_trajectory(programs: list[dict]) -> str:
    valid = [
        p
        for p in programs
        if p.get("metrics", {}).get("is_valid") == 1.0
        and "fitness" in p.get("metrics", {})
    ]
    if not valid:
        return "no valid programs yet"
    best = max(valid, key=lambda p: p["metrics"]["fitness"])
    return (
        f"{len(programs)} programs ({len(valid)} valid), best fitness {best['metrics']['fitness']:.4f} "
        f"(single-eval; sigma~0.0078 — trust re-evals, not this)"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=EXP_DIR / "latest_allin.env")
    parser.add_argument(
        "--hard-gate",
        action="store_true",
        help="only the 1h abort set can FAIL the exit code",
    )
    args = parser.parse_args()

    env = read_env(args.env)
    runs = load_pids(Path(env["PIDS_FILE"]))
    bank_dir = Path(env["MEM_R1_MEMORY_BANK"])

    failures = []
    for label, run in runs.items():
        is_mem = label.startswith("MEM")
        programs = load_programs(run["out"])
        cards = load_cards(bank_dir) if is_mem else []
        rows = [("LIVE", *check_liveness(run["pid"], run["log"]))]
        rows.append(("T1", *check_t1_occupancy(run["out"])))
        rows.append(("T2", *check_t2_struct_metrics(programs)))
        rows.append(("T3", *check_t3_transport(programs)))
        rows.append(("T4", *check_t4_gate(run["log"])))
        if is_mem:
            rows.append(("T5-W", *check_t5w_crediting(cards, programs)))
            rows.append(("T5-R", *check_t5r_consumption(cards)))
            rows.append(("T6", *check_t6_memory_health(run["log"])))
        else:
            rows.append(("T7", *check_t7_purity(run["out"], run["log"], programs)))

        print(f"\n=== {label} ({run['out']}) ===")
        print(f"  info: {info_trajectory(programs)}")
        for check_id, status, detail in rows:
            print(f"  [{status:4}] {check_id:5} {detail}")
            if status == "FAIL" and (not args.hard_gate or check_id in HARD_GATE_IDS):
                failures.append(f"{label}:{check_id}")

    if failures:
        print(f"\nFAILURES: {failures}")
        return 1
    print("\nAll checks pass (WARNs are informational).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
