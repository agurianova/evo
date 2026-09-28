"""Trace the best evolved program of each arm and, for arm B, render the
single-parent lineage from the seed as a series of structured slot-diffs.

Usage: python trace_lineage.py <armA_run_dir> <armB_run_dir> [--first-n N]
Writes lineage.json (structured) and lineage.md (human-readable) next to this
script.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_index(run_dir: Path):
    progs = {}
    for f in (run_dir / "storage/chains_summarizer/programs").glob("*.json"):
        p = json.loads(f.read_text())
        progs[p["id"]] = p
    return progs


def is_seed(p) -> bool:
    return p["metadata"].get("source") == "initial_program"


def fit(p):
    return (p.get("metrics") or {}).get("fitness")


def parent_id(p):
    lin = p.get("lineage") or {}
    parents = lin.get("parents") or []
    return parents[0] if parents else None


def steps_of(p):
    try:
        return json.loads(p["code"]).get("steps", [])
    except Exception:
        return []


def best_child(progs, first_n=None):
    kids = [p for p in progs.values() if not is_seed(p) and fit(p) is not None]
    kids.sort(key=lambda p: p.get("atomic_counter", 0))
    if first_n is not None:
        kids = kids[:first_n]
    valid = [p for p in kids if ((p.get("metrics") or {}).get("is_valid") or 0) >= 1]
    return max(valid, key=fit) if valid else None


def _slot_key(k):
    tail = k.split("_", 1)[1]
    return int(tail) if tail.isdigit() else tail


def diff_summary(p):
    """Compact rendering of the stored structured slot-diff (arm B): every
    output slot with its source id, kind (keep/edit/…) and any field edits."""
    mo = p["metadata"].get("mutation_output")
    if not isinstance(mo, dict):
        return None
    slots = []
    for k in sorted((kk for kk in mo if kk.startswith("slot_")), key=_slot_key):
        s = mo[k]
        if not isinstance(s, dict):
            continue
        entry = {"slot": k, "id": s.get("id"), "kind": s.get("kind")}
        if s.get("edits"):
            entry["edits"] = s["edits"]
        slots.append(entry)
    return {
        "archetype": mo.get("archetype"),
        "base_parent": mo.get("base_parent"),
        "justification": mo.get("justification"),
        "slots": slots,
        "edited_slots": [s for s in slots if s.get("edits")],
        "n_slots": len(slots),
        "n_edited": sum(1 for s in slots if s.get("edits")),
    }


def trace(progs, leaf):
    chain = []
    cur = leaf
    seen = set()
    while cur is not None and cur["id"] not in seen:
        seen.add(cur["id"])
        chain.append(cur)
        pid = parent_id(cur)
        cur = progs.get(pid) if pid else None
    chain.reverse()
    return chain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arm_a")
    ap.add_argument("arm_b")
    ap.add_argument("--first-n", type=int, default=None)
    args = ap.parse_args()
    out_dir = Path(__file__).parent

    A = load_index(Path(args.arm_a))
    B = load_index(Path(args.arm_b))

    bestA = best_child(A, args.first_n)
    bestB = best_child(B, args.first_n)
    bestB_overall = best_child(B, None)

    # Diff series showcases the true best B program (full run) — the "best
    # program for B" the reader wants to see reconstructed from the seed.
    chain = trace(B, bestB_overall) if bestB_overall else []

    result = {
        "first_n": args.first_n,
        "best_A": {
            "id": bestA["id"],
            "atomic_counter": bestA.get("atomic_counter"),
            "iteration": bestA.get("iteration"),
            "fitness": fit(bestA),
            "n_steps": (bestA.get("metrics") or {}).get("n_steps"),
            "code": bestA["code"],
        }
        if bestA
        else None,
        "best_B": {
            "id": bestB["id"],
            "atomic_counter": bestB.get("atomic_counter"),
            "iteration": bestB.get("iteration"),
            "fitness": fit(bestB),
            "n_steps": (bestB.get("metrics") or {}).get("n_steps"),
            "code": bestB["code"],
        }
        if bestB
        else None,
        "best_B_overall": {
            "id": bestB_overall["id"],
            "atomic_counter": bestB_overall.get("atomic_counter"),
            "iteration": bestB_overall.get("iteration"),
            "fitness": fit(bestB_overall),
            "n_steps": (bestB_overall.get("metrics") or {}).get("n_steps"),
            "code": bestB_overall["code"],
        }
        if bestB_overall
        else None,
        "best_B_overall_fitness": fit(bestB_overall) if bestB_overall else None,
        "best_B_overall_iter": bestB_overall.get("iteration")
        if bestB_overall
        else None,
        "lineage": [
            {
                "id": p["id"],
                "atomic_counter": p.get("atomic_counter"),
                "iteration": p.get("iteration"),
                "generation": (p.get("lineage") or {}).get("generation"),
                "is_seed": is_seed(p),
                "fitness": fit(p),
                "n_steps": (p.get("metrics") or {}).get("n_steps"),
                "diff": None if is_seed(p) else diff_summary(p),
            }
            for p in chain
        ],
    }
    (out_dir / "lineage.json").write_text(json.dumps(result, indent=2, default=str))

    lines = []
    lines.append(f"# Best-program lineage (first_n={args.first_n})\n")
    lines.append(
        f"best A child: iter={result['best_A']['iteration']} "
        f"fitness={result['best_A']['fitness']:.4f} "
        f"n_steps={result['best_A']['n_steps']}\n"
        if result["best_A"]
        else "best A child: none\n"
    )
    lines.append(
        f"best B child: iter={result['best_B']['iteration']} "
        f"fitness={result['best_B']['fitness']:.4f} "
        f"n_steps={result['best_B']['n_steps']}   "
        f"(best B over full run: {result['best_B_overall_fitness']:.4f} "
        f"@ iter {result['best_B_overall_iter']})\n"
        if result["best_B"]
        else "best B child: none\n"
    )
    lines.append(f"\n## Arm B lineage: seed -> best ({len(chain)} nodes)\n")
    for node in result["lineage"]:
        tag = "SEED" if node["is_seed"] else f"gen{node['generation']}"
        f = node["fitness"]
        fs = f"{f:.4f}" if isinstance(f, (int, float)) else str(f)
        lines.append(
            f"\n[{tag}] iter={node['iteration']} counter={node['atomic_counter']} "
            f"fitness={fs} n_steps={node['n_steps']}"
        )
        d = node["diff"]
        if d:
            keepmap = " ".join(
                f"{s['slot'].split('_')[1]}:{s['id']}" for s in d["slots"]
            )
            lines.append(
                f"    archetype={d['archetype']} base={d['base_parent']} "
                f"edits={d['n_edited']}/{d['n_slots']} slots"
            )
            lines.append(f"    output slots (pos:source_id): {keepmap}")
            for e in d["edited_slots"]:
                for field, val in (e.get("edits") or {}).items():
                    lines.append(f"      {e['slot']}({e['id']}).{field} := {val!r}")
            if d.get("justification"):
                lines.append(f"    why: {d['justification'][:200]}")
    (out_dir / "lineage.md").write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\nwrote {out_dir / 'lineage.json'} and lineage.md")


if __name__ == "__main__":
    main()
