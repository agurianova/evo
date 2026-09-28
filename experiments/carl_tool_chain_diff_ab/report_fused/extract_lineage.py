"""Walk the winning arm-B program's parent chain back to the base seed and dump
one `viz_qwen/lineage_NN_<label>.json` per generation for make_lineage_viz_qwen.py.

Each dump carries {label,id,parents,generation,mutation,fitness,n_steps,
n_tool_steps,spec}. `spec` is the parsed wire-JSON chain (the genome in `code`);
the DAG figure is driven entirely by it, so no un-pickling of stage results is
needed. Winner = highest-fitness valid program unless an id prefix is passed.

Usage:
  python extract_lineage.py <run_dir> [winner_id_prefix] [--out DIR]
  e.g. python extract_lineage.py ../runs/armB_qwen --out viz_qwen
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_programs(run_dir: Path) -> dict:
    progs = {}
    for f in (run_dir / "storage").rglob("programs/*.json"):
        d = json.loads(f.read_text())
        progs[d["id"]] = d
    return progs


def pick_winner(progs: dict, prefix: str | None) -> dict:
    if prefix:
        hits = [d for i, d in progs.items() if i.startswith(prefix)]
        if not hits:
            raise SystemExit(f"no program id starts with {prefix!r}")
        return hits[0]
    valid = [d for d in progs.values() if (d["metrics"].get("is_valid") or 0) >= 1]
    pool = valid or list(progs.values())
    return max(pool, key=lambda d: d["metrics"].get("fitness") or -1)


def chain_to_base(progs: dict, winner: dict) -> list:
    chain = [winner]
    cur = winner
    seen = {winner["id"]}
    while True:
        parents = cur.get("lineage", {}).get("parents") or []
        parent = next((progs[p] for p in parents if p in progs and p not in seen), None)
        if parent is None:
            break
        chain.append(parent)
        seen.add(parent["id"])
        cur = parent
    chain.reverse()
    return chain


def spec_of(prog: dict) -> dict:
    return json.loads(prog["code"])


def label_for(i: int, n: int, prog: dict) -> str:
    if i == 0:
        return "base seed"
    if i == n - 1:
        return f"gen {prog['lineage']['generation']}  (best)"
    return f"gen {prog['lineage']['generation']}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("winner", nargs="?", default=None)
    ap.add_argument("--out", default="viz_qwen")
    args = ap.parse_args()

    progs = load_programs(args.run_dir)
    winner = pick_winner(progs, args.winner)
    chain = chain_to_base(progs, winner)

    out = Path(args.out)
    out.mkdir(exist_ok=True)
    for old in out.glob("lineage_*.json"):
        old.unlink()

    n = len(chain)
    manifest = []
    for i, prog in enumerate(chain):
        m = prog["metrics"]
        rec = {
            "label": label_for(i, n, prog),
            "id": prog["id"],
            "parents": prog["lineage"]["parents"],
            "generation": prog["lineage"]["generation"],
            "mutation": prog["lineage"]["mutation"],
            "fitness": m.get("fitness"),
            "n_steps": m.get("n_steps"),
            "n_tool_steps": m.get("n_tool_steps"),
            "spec": spec_of(prog),
        }
        tag = "base" if i == 0 else f"gen{prog['lineage']['generation']}"
        fname = f"lineage_{i:02d}_{tag}.json"
        (out / fname).write_text(json.dumps(rec, indent=2))
        manifest.append((fname, rec["label"], rec["fitness"]))
        print(
            f"  {fname}  {rec['label']:>14}  fit={rec['fitness']}  "
            f"steps={rec['n_steps']} tool={rec['n_tool_steps']}  id={prog['id'][:8]}"
        )

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(
        f"\nwinner {winner['id'][:8]} fit={winner['metrics'].get('fitness'):.4f} "
        f"gen={winner['lineage']['generation']} — {n} programs written to {out}/"
    )


if __name__ == "__main__":
    main()
