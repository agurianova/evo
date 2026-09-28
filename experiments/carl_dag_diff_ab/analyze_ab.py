"""Compare two CARL DAG-diff A/B arms: validity funnel, failure taxonomy, fitness.

Usage: python analyze_ab.py <armA_run_dir> <armB_run_dir> [--out report_dir]
Each run dir holds storage/chains_summarizer/programs/*.json and run.log.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from statistics import mean, median
import sys

MUTATION_FAIL_RE = re.compile(r"Failed to generate/persist mutation: (.+)$")
MUTATION_CALL_RE = re.compile(
    r'"stage": "(?:MutationAgent|DiffMutationAgent)", .*"ok": (true|false)'
)
TAXONOMY_PREFIXES = (
    "diff_schema_error",
    "diff_apply_assertion",
    "llm_call_error",
    "carl_validation_error",
    "json_parse_error",
)


def classify_failure(msg: str) -> str:
    for prefix in TAXONOMY_PREFIXES:
        if msg.startswith(prefix):
            return prefix
    # llm_call_error messages embed raw model/exception text that could
    # contain another taxonomy string; prefer the leftmost occurrence
    hits = [(msg.find(p), p) for p in TAXONOMY_PREFIXES if p in msg]
    if hits:
        return min(hits)[1]
    if "No code found" in msg:
        return "no_code_extracted"
    head = msg.split(":", 1)[0].strip()
    return head[:60] if head else "unknown"


def load_programs(run_dir: Path) -> list[dict]:
    progs = []
    for f in sorted((run_dir / "storage/chains_summarizer/programs").glob("*.json")):
        d = json.loads(f.read_text())
        progs.append(d)
    progs.sort(key=lambda d: d.get("atomic_counter", 0))
    return progs


def scan_log(run_dir: Path, first_ok: int | None = None) -> dict:
    """Tally mutation attempts/failures. If first_ok is set, stop once first_ok
    mutations have PERSISTED — the token/attempt cost of accepting that many
    mutants, retries included. A call logged ok=true can still die downstream
    (schema/apply/validation failure -> no stored child); each failure line is
    paired with the ok value of the most recent call line, so only failures
    following an ok=true call extend the window (failures after ok=false —
    llm_call_error, no_code_extracted — belong to that failed call). The
    window closes at the NEXT mutation-call line (not at the Nth ok line
    itself), so a between-call downstream failure is attributed inside the
    window unless a concurrent call line lands in the 1-3-line gap first
    (residual undercount of at most one failure)."""
    failures: Counter[str] = Counter()
    attempts = 0
    ok_calls = 0
    failed_after_ok = 0
    last_call_ok = False
    log = run_dir / "run.log"
    if not log.exists():
        return {"mutation_attempts": 0, "failures": failures}
    with log.open(errors="replace") as fh:
        for raw in fh:
            for line in raw.split("\r"):
                mc = MUTATION_CALL_RE.search(line)
                if mc:
                    if first_ok is not None and ok_calls - failed_after_ok >= first_ok:
                        return {"mutation_attempts": attempts, "failures": failures}
                    attempts += 1
                    last_call_ok = mc.group(1) == "true"
                    if last_call_ok:
                        ok_calls += 1
                m = MUTATION_FAIL_RE.search(line)
                if m:
                    failures[classify_failure(m.group(1))] += 1
                    if last_call_ok:
                        failed_after_ok += 1
    if first_ok is not None and ok_calls - failed_after_ok < first_ok:
        print(
            f"WARNING: {log} has only {ok_calls - failed_after_ok} persisted "
            f"mutations (< first_ok={first_ok}); window never closed, "
            "returning full-log tally",
            file=sys.stderr,
        )
    return {"mutation_attempts": attempts, "failures": failures}


def invalid_error_kinds(invalid_children: list[dict]) -> Counter:
    import base64
    import pickle

    kinds: Counter[str] = Counter()
    for p in invalid_children:
        kind = "unknown"
        for stage, res in (p.get("stage_results") or {}).items():
            if stage != "ValidateCodeStage" or not isinstance(res, dict):
                continue
            blob = res.get("error")
            if not blob:
                continue
            try:
                err = pickle.loads(base64.b64decode(blob))
                kind = classify_failure(str(getattr(err, "message", err)))
            except Exception:
                kind = "undecodable"
        kinds[kind] += 1
    return kinds


def arm_stats(run_dir: Path, first_n: int | None = None) -> dict:
    progs = load_programs(run_dir)
    seeds = [p for p in progs if p["metadata"].get("source") == "initial_program"]
    children = [p for p in progs if p["metadata"].get("source") != "initial_program"]
    # Iteration-matched cap: keep only the first_n accepted children (by
    # atomic_counter, already sorted) so both arms are compared over the same
    # number of mutants. seeds always retained.
    if first_n is not None:
        if len(children) < first_n:
            print(
                f"WARNING: {run_dir} stored only {len(children)} children "
                f"(< first_n={first_n}); cap is a no-op",
                file=sys.stderr,
            )
        children = children[:first_n]
        progs = seeds + children

    def fit(p):
        return (p.get("metrics") or {}).get("fitness")

    def valid(p):
        return ((p.get("metrics") or {}).get("is_valid") or 0) >= 1

    valid_children = [p for p in children if valid(p)]
    invalid_children = [p for p in children if not valid(p)]
    log = scan_log(run_dir, first_ok=first_n)

    trajectory = []
    best = None
    for p in progs:
        f = fit(p)
        if f is None:
            continue
        best = f if best is None else max(best, f)
        trajectory.append(
            {
                "counter": p.get("atomic_counter", 0),
                "iteration": p.get("iteration"),
                "fitness": round(f, 5),
                "best_so_far": round(best, 5),
                "is_seed": p["metadata"].get("source") == "initial_program",
            }
        )

    child_fits = [fit(p) for p in valid_children if fit(p) is not None]
    return {
        "run_dir": str(run_dir),
        "programs_total": len(progs),
        "seeds": len(seeds),
        "children_stored": len(children),
        "children_valid": len(valid_children),
        "children_invalid_stored": len(invalid_children),
        "invalid_error_kinds": dict(invalid_error_kinds(invalid_children)),
        "mutation_attempts_logged": log["mutation_attempts"],
        "mutation_failures": dict(log["failures"].most_common()),
        "mutation_failures_total": sum(log["failures"].values()),
        "fitness_best": max(
            (f for f in (fit(p) for p in progs) if f is not None), default=None
        ),
        "child_fitness_best": max(child_fits, default=None),
        "child_fitness_mean": mean(child_fits) if child_fits else None,
        "child_fitness_median": median(child_fits) if child_fits else None,
        "seed_fitness_best": max(
            (fit(p) for p in seeds if fit(p) is not None), default=None
        ),
        "n_steps": Counter(
            int((p.get("metrics") or {}).get("n_steps") or 0) for p in valid_children
        ),
        "executor_completion_tokens": sum(
            int((p.get("metrics") or {}).get("completion_tokens") or 0) for p in progs
        ),
        "states": Counter(p.get("state") for p in progs),
        "trajectory": trajectory,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("arm_a")
    ap.add_argument("arm_b")
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--first-n",
        type=int,
        default=None,
        help="iteration-matched cap: compare only the first N accepted children per arm",
    )
    args = ap.parse_args()

    stats = {
        "A_full_rewrite": arm_stats(Path(args.arm_a), first_n=args.first_n),
        "B_structured_diff": arm_stats(Path(args.arm_b), first_n=args.first_n),
    }
    if args.first_n is not None:
        print(f"(iteration-matched: first {args.first_n} accepted children per arm)\n")

    for name, s in stats.items():
        attempts = s["mutation_attempts_logged"]
        fails = s["mutation_failures_total"]
        print(f"=== arm {name} ===")
        print(
            f"  programs: {s['programs_total']} (seeds {s['seeds']}, children {s['children_stored']})"
        )
        print(f"  mutation attempts (log): {attempts}, generation failures: {fails}")
        if attempts:
            print(f"  generation success rate: {(attempts - fails) / attempts:.1%}")
        print(
            f"  children valid: {s['children_valid']}, invalid stored: {s['children_invalid_stored']}"
            f" (kinds: {s['invalid_error_kinds']})"
        )
        print(f"  failure taxonomy: {s['mutation_failures']}")
        print(
            f"  fitness — seed best {s['seed_fitness_best']}, child best {s['child_fitness_best']}, "
            f"child mean {s['child_fitness_mean']}, overall best {s['fitness_best']}"
        )
        print(f"  n_steps (valid children): {dict(sorted(s['n_steps'].items()))}")
        print(
            f"  executor completion tokens (stored programs): {s['executor_completion_tokens']}"
        )
        print(f"  states: {dict(s['states'])}")

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for name, s in stats.items():
            s["n_steps"] = dict(s["n_steps"])
            s["states"] = dict(s["states"])
        payload = {**stats, "first_n": args.first_n}
        (out / "ab_stats.json").write_text(json.dumps(payload, indent=2, default=str))
        print(f"\nwrote {out / 'ab_stats.json'}", file=sys.stderr)


if __name__ == "__main__":
    main()
