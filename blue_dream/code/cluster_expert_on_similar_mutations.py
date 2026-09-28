#!/usr/bin/env python3
"""Cross-run similarity of expert-on mutations and their fitness gain vs parent.

Scope: pmhctcr_final_terra_expert_on_m100_r1..r5.

A mutation is the added/replaced lines of the SEARCH/REPLACE patch (unchanged
hunk context is removed). Similarity is Jaccard of token 5-grams on that
normalized edit. Clusters are complete-linkage, so every pair inside a cluster
meets the threshold.

Fitness association is computed after clustering. Baseline is the gain rate of
all scored substantive mutations, not of archive elites.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re

import numpy as np
from scipy.stats import binomtest, fisher_exact
from sklearn.cluster import AgglomerativeClustering

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
RUNS = [f"pmhctcr_final_terra_expert_on_m100_r{i}" for i in range(1, 6)]

PATCH_BLOCK = re.compile(
    r"<<<<<<< SEARCH\n(?P<search>.*?)\n=======\n(?P<replace>.*?)\n>>>>>>> REPLACE",
    re.S,
)
DOCSTRING = re.compile(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')')
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+\.\d+|\d+")
DEF_RE = re.compile(r"^(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
CLASS_RE = re.compile(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
FAMILY_RE = re.compile(r"interaction_family\s*=\s*['\"]([^'\"]+)['\"]")

SHINGLE_K = 5
MIN_TOKENS = 12
# Complete-linkage: every pair has Jaccard >= this. Chosen as "very similar"
# after inspecting edit text, not after ranking by fitness.
PRIMARY_JACCARD = 0.70
EXPLORATORY_JACCARD = 0.55
CLEAR_DELTA = 0.005


def normalize_code(text: str) -> str:
    text = DOCSTRING.sub(" ", text or "")
    lines = []
    for line in text.splitlines():
        code = re.sub(r"#.*", "", line).strip()
        if code:
            lines.append(re.sub(r"\s+", " ", code))
    return "\n".join(lines)


def tokens_of(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def shingles(tokens: list[str], k: int = SHINGLE_K) -> set[tuple[str, ...]]:
    if not tokens:
        return set()
    if len(tokens) < k:
        return {tuple(tokens)}
    return {tuple(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def code_delta(parent_code: str, child_code: str) -> tuple[str, str]:
    """Lines present in the child and absent from the parent, after comment stripping.

    SEARCH/REPLACE hunks keep unchanged neighbors, so hunk text is not the mutation.
    A line is a mutation only when the normalized child source contains it more times
    than the normalized parent source.
    """
    parent_lines = normalize_code(parent_code).splitlines()
    child_lines = normalize_code(child_code).splitlines()
    parent_count = Counter(parent_lines)
    added = []
    for line in child_lines:
        if parent_count[line] > 0:
            parent_count[line] -= 1
        else:
            added.append(line)
    child_count = Counter(child_lines)
    removed = []
    for line in parent_lines:
        if child_count[line] > 0:
            child_count[line] -= 1
        else:
            removed.append(line)
    return "\n".join(added), "\n".join(removed)


def n_patch_blocks(patch: str) -> int:
    return len(PATCH_BLOCK.findall(patch or ""))


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def load_run(name: str) -> list[dict]:
    storage = REPO / "outputs" / name / "storage" / "pmhctcr" / "programs"
    progs = {}
    for path in storage.glob("*.json"):
        d = json.loads(path.read_text())
        progs[d["id"]] = d
    seed_ids = {
        d["id"] for d in progs.values() if not (d.get("lineage") or {}).get("parents")
    }
    champ = None
    for d in progs.values():
        m = d.get("metrics") or {}
        if d.get("state") != "done" or m.get("is_valid") != 1:
            continue
        fit = m.get("fitness")
        if fit is None or fit < 0:
            continue
        if champ is None or fit > champ[0]:
            champ = (fit, d["id"])
    lineage = set()
    if champ:
        cur = champ[1]
        guard = 0
        while cur and cur in progs and guard < 200:
            lineage.add(cur)
            parents = (progs[cur].get("lineage") or {}).get("parents") or []
            cur = parents[0] if parents else ""
            guard += 1
    rows = []
    rep = int(name.rsplit("_r", 1)[1])
    for d in progs.values():
        parents = (d.get("lineage") or {}).get("parents") or []
        if not parents:
            continue
        parent = progs.get(parents[0])
        md = d.get("metadata") or {}
        patch = md.get("python_patch") or ""
        parent_code = (parent.get("code") or "") if parent else ""
        added, removed = code_delta(parent_code, d.get("code") or "")
        n_blocks = n_patch_blocks(patch)
        toks = tokens_of(added)
        m = d.get("metrics") or {}
        pm = (parent.get("metrics") or {}) if parent else {}
        fit = m.get("fitness")
        pfit = pm.get("fitness")
        child_ok = m.get("is_valid") == 1 and fit is not None and fit >= 0
        parent_ok = (
            pfit is not None
            and pfit >= 0
            and (
                pm.get("is_valid") == 1
                or parent in seed_ids
                or (parent and not (parent.get("lineage") or {}).get("parents"))
            )
        )
        # Seed may be valid. Parent invalid => delta undefined.
        parent_ok = pm.get("is_valid") == 1 and pfit is not None and pfit >= 0
        scored = bool(child_ok and parent_ok)
        delta = (fit - pfit) if scored else None
        fam = FAMILY_RE.search(d.get("code") or "")
        rows.append(
            {
                "run": rep,
                "id": d["id"],
                "short": d["id"][:8],
                "parent": parents[0],
                "parent_short": parents[0][:8],
                "parent_is_seed": parents[0] in seed_ids,
                "generation": (d.get("lineage") or {}).get("generation"),
                "iteration": d.get("iteration"),
                "state": d.get("state"),
                "on_champion_lineage": d["id"] in lineage,
                "fitness": fit if child_ok else None,
                "parent_fitness": pfit if parent_ok else None,
                "delta": delta,
                "scored": scored,
                "gain": bool(scored and delta > 1e-8),
                "clear_gain": bool(scored and delta >= CLEAR_DELTA),
                "n_blocks": n_blocks,
                "n_tokens": len(toks),
                "substantive": len(toks) >= MIN_TOKENS,
                "tokens": toks,
                "shingles": shingles(toks),
                "added": added,
                "removed": removed,
                "defs": sorted(
                    set(DEF_RE.findall(added)) - set(DEF_RE.findall(removed))
                ),
                "classes": sorted(
                    set(CLASS_RE.findall(added)) - set(CLASS_RE.findall(removed))
                ),
                "family": fam.group(1) if fam else "",
                "model": md.get("mutation_model") or "",
            }
        )
    return rows


def cluster_labels(sim: np.ndarray, threshold: float) -> np.ndarray:
    dist = np.clip(1.0 - sim, 0.0, 1.0)
    np.fill_diagonal(dist, 0.0)
    # Numerical noise can make a matrix slightly non-symmetric.
    dist = np.maximum(dist, dist.T)
    model = AgglomerativeClustering(
        metric="precomputed",
        linkage="complete",
        distance_threshold=1.0 - threshold + 1e-9,
        n_clusters=None,
    )
    return model.fit_predict(dist)


def bh_fdr(pvals: list[float]) -> list[float]:
    m = len(pvals)
    if m == 0:
        return []
    order = np.argsort(pvals)
    ranked = np.array(pvals, dtype=float)[order]
    adj = np.empty(m, dtype=float)
    prev = 1.0
    for i in range(m - 1, -1, -1):
        val = ranked[i] * m / (i + 1)
        prev = min(prev, val)
        adj[i] = prev
    out = np.empty(m, dtype=float)
    out[order] = np.clip(adj, 0, 1)
    return out.tolist()


def summarize_cluster(
    members: list[dict], sim: np.ndarray, index: dict[str, int]
) -> dict:
    scored = [m for m in members if m["scored"]]
    gains = [m for m in scored if m["gain"]]
    clears = [m for m in scored if m["clear_gain"]]
    deltas = [m["delta"] for m in scored]
    runs = sorted({m["run"] for m in members})
    scored_runs = sorted({m["run"] for m in scored})
    by_run = defaultdict(list)
    for m in scored:
        by_run[m["run"]].append(m["delta"])
    run_stats = []
    for run in scored_runs:
        ds = by_run[run]
        run_stats.append(
            {
                "run": run,
                "n": len(ds),
                "n_gain": sum(d > 1e-8 for d in ds),
                "n_clear": sum(d >= CLEAR_DELTA for d in ds),
                "mean_delta": float(np.mean(ds)),
                "median_delta": float(np.median(ds)),
            }
        )
    # Medoid: highest mean Jaccard to other members.
    idxs = [index[m["id"]] for m in members]
    if len(idxs) == 1:
        medoid_i = idxs[0]
        min_j = 1.0
        mean_j = 1.0
    else:
        sub = sim[np.ix_(idxs, idxs)]
        np.fill_diagonal(sub, np.nan)
        means = np.nanmean(sub, axis=1)
        medoid_local = int(np.nanargmax(means))
        medoid_i = idxs[medoid_local]
        min_j = float(np.nanmin(sub))
        mean_j = float(np.nanmean(sub))
    medoid = next(m for m in members if index[m["id"]] == medoid_i)
    # Leave-one-run-out gain rate.
    loro = []
    for held in scored_runs:
        kept = [m for m in scored if m["run"] != held]
        if not kept:
            continue
        loro.append(
            {
                "held_out_run": held,
                "n": len(kept),
                "gain_rate": sum(m["gain"] for m in kept) / len(kept),
                "mean_delta": float(np.mean([m["delta"] for m in kept])),
            }
        )
    # One observation per run: median delta. Avoids a single run's retries dominating.
    run_medians = [r["median_delta"] for r in run_stats]
    return {
        "n": len(members),
        "n_scored": len(scored),
        "n_unscored": len(members) - len(scored),
        "n_gain": len(gains),
        "n_clear": len(clears),
        "gain_rate": (len(gains) / len(scored)) if scored else None,
        "clear_rate": (len(clears) / len(scored)) if scored else None,
        "mean_delta": float(np.mean(deltas)) if deltas else None,
        "median_delta": float(np.median(deltas)) if deltas else None,
        "min_delta": float(np.min(deltas)) if deltas else None,
        "max_delta": float(np.max(deltas)) if deltas else None,
        "runs": runs,
        "n_runs": len(runs),
        "scored_runs": scored_runs,
        "n_scored_runs": len(scored_runs),
        "run_stats": run_stats,
        "runs_median_positive": sum(d > 0 for d in run_medians),
        "runs_mean_positive": sum(r["mean_delta"] > 0 for r in run_stats),
        "min_jaccard": min_j,
        "mean_jaccard": mean_j,
        "leave_one_run_out": loro,
        "loro_min_gain_rate": min((x["gain_rate"] for x in loro), default=None),
        "n_seed_parent": sum(m["parent_is_seed"] for m in members),
        "n_champion_lineage": sum(m["on_champion_lineage"] for m in members),
        "defs": sorted({d for m in members for d in m["defs"]}),
        "classes": sorted({c for m in members for c in m["classes"]}),
        "families": dict(Counter(m["family"] for m in members if m["family"])),
        "medoid_id": medoid["short"],
        "medoid_run": medoid["run"],
        "medoid_added": medoid["added"][:1800],
        "members": [
            {
                "run": m["run"],
                "id": m["short"],
                "parent": m["parent_short"],
                "parent_is_seed": m["parent_is_seed"],
                "generation": m["generation"],
                "state": m["state"],
                "on_champion_lineage": m["on_champion_lineage"],
                "fitness": m["fitness"],
                "parent_fitness": m["parent_fitness"],
                "delta": m["delta"],
                "gain": m["gain"],
                "clear_gain": m["clear_gain"],
                "n_tokens": m["n_tokens"],
                "family": m["family"],
                "defs": m["defs"],
                "added_head": m["added"][:400],
            }
            for m in sorted(members, key=lambda m: (-(m["delta"] or -9), m["run"]))
        ],
    }


def distinctive_tokens(members: list[dict], df: Counter, n_docs: int) -> list[str]:
    tf = Counter()
    for m in members:
        tf.update(set(m["tokens"]))
    scored = []
    for tok, c in tf.items():
        if len(tok) < 4 or tok in {"self", "return", "none", "true", "false"}:
            continue
        # Appears in most cluster members, rare globally.
        frac = c / len(members)
        rarity = 1.0 - (df[tok] / n_docs)
        if frac >= 0.6 and rarity >= 0.7:
            scored.append((frac * rarity, tok))
    scored.sort(reverse=True)
    return [t for _, t in scored[:8]]


def main() -> None:
    records = []
    for name in RUNS:
        records.extend(load_run(name))
    substantive = [r for r in records if r["substantive"]]
    print(
        f"mutations={len(records)} substantive>={MIN_TOKENS}tok={len(substantive)} "
        f"scored_substantive={sum(r['scored'] for r in substantive)}"
    )
    scored_sub = [r for r in substantive if r["scored"]]
    p0 = sum(r["gain"] for r in scored_sub) / len(scored_sub)
    p0_clear = sum(r["clear_gain"] for r in scored_sub) / len(scored_sub)
    mean0 = float(np.mean([r["delta"] for r in scored_sub]))
    print(
        f"baseline gain_rate={p0:.3f} clear_rate(d>={CLEAR_DELTA})={p0_clear:.3f} mean_delta={mean0:.4f}"
    )

    # Pairwise Jaccard on substantive edits only. Non-substantive edits are
    # too short for 5-gram identity to mean "the same mutation".
    n = len(substantive)
    index = {r["id"]: i for i, r in enumerate(substantive)}
    sim = np.eye(n, dtype=np.float32)
    sets = [r["shingles"] for r in substantive]
    cross = []
    for i in range(n):
        si = sets[i]
        for j in range(i + 1, n):
            val = jaccard(si, sets[j])
            if val <= 0:
                continue
            sim[i, j] = sim[j, i] = val
            if substantive[i]["run"] != substantive[j]["run"] and val >= 0.50:
                cross.append((val, i, j))
    cross.sort(reverse=True)
    print(f"cross-run pairs jaccard>=0.50: {len(cross)}")
    for thr in (0.55, 0.70, 0.85):
        print(f"  >= {thr}: {sum(v >= thr for v, _, _ in cross)}")

    df = Counter()
    for r in substantive:
        df.update(set(r["tokens"]))

    payloads = {}
    for thr in (EXPLORATORY_JACCARD, PRIMARY_JACCARD, 0.85):
        labels = cluster_labels(sim, thr)
        groups = defaultdict(list)
        for rec, lab in zip(substantive, labels):
            groups[int(lab)].append(rec)
        clusters = []
        for lab, members in groups.items():
            if len(members) < 2:
                continue
            runs = {m["run"] for m in members}
            if len(runs) < 2:
                continue
            summary = summarize_cluster(members, sim, index)
            summary["id"] = lab
            summary["threshold"] = thr
            summary["tokens"] = distinctive_tokens(members, df, n)
            clusters.append(summary)
        clusters.sort(
            key=lambda c: (
                -(c["n_scored_runs"] or 0),
                -(c["gain_rate"] or 0),
                -(c["mean_delta"] or -9),
                -(c["n_scored"] or 0),
            )
        )
        payloads[str(thr)] = clusters
        print(
            f"\n=== complete-linkage Jaccard>={thr} cross-run clusters: {len(clusters)} ==="
        )
        for c in clusters[:12]:
            print(
                f"  runs={c['runs']} n={c['n_scored']}/{c['n']} "
                f"gain={c['n_gain']}/{c['n_scored']} ({(c['gain_rate'] or 0):.0%}) "
                f"clear={c['n_clear']} mean={c['mean_delta']:.4f} med={c['median_delta']:.4f} "
                f"minJ={c['min_jaccard']:.2f} seed_par={c['n_seed_parent']} "
                f"champ_lin={c['n_champion_lineage']} toks={c['tokens'][:4]} defs={c['defs'][:4]}"
            )

    # Tests at the primary threshold, only clusters that could possibly be
    # "frequent": at least 3 runs and 5 scored mutations.
    primary = payloads[str(PRIMARY_JACCARD)]
    tested = []
    for c in primary:
        if c["n_scored_runs"] >= 3 and c["n_scored"] >= 5:
            table = [
                [c["n_gain"], c["n_scored"] - c["n_gain"]],
                [
                    sum(r["gain"] for r in scored_sub) - c["n_gain"],
                    len(scored_sub)
                    - c["n_scored"]
                    - (sum(r["gain"] for r in scored_sub) - c["n_gain"]),
                ],
            ]
            # Guard if a cluster somehow includes every gain.
            odds, p_fisher = fisher_exact(table, alternative="greater")
            p_binom = float(
                binomtest(c["n_gain"], c["n_scored"], p0, alternative="greater").pvalue
            )
            c["fisher_p"] = float(p_fisher)
            c["binom_p"] = p_binom
            c["fisher_odds"] = float(odds)
            tested.append(c)
        else:
            c["fisher_p"] = None
            c["binom_p"] = None
            c["fisher_odds"] = None
    fdrs = bh_fdr([c["fisher_p"] for c in tested])
    for c, q in zip(tested, fdrs):
        c["fisher_q"] = q

    def passes(c: dict) -> bool:
        if c.get("fisher_q") is None:
            return False
        loro = c["loro_min_gain_rate"]
        return bool(
            c["fisher_q"] < 0.05
            and c["gain_rate"] >= 0.60
            and c["mean_delta"] > 0
            and c["median_delta"] > 0
            and loro is not None
            and loro >= 0.50
            and c["runs_median_positive"] >= 3
        )

    strict = [c for c in primary if passes(c)]
    print(f"\nPRIMARY clusters tested (3+ runs, 5+ scored): {len(tested)}")
    print(f"STRICT pass: {len(strict)}")
    for c in primary:
        if (
            c["n_scored_runs"] >= 2
            and (c["gain_rate"] or 0) >= 0.5
            and (c["n_scored"] or 0) >= 3
        ):
            print(
                f"  candidate runs={c['runs']} gain={c['n_gain']}/{c['n_scored']} "
                f"mean={c['mean_delta']:.4f} med={c['median_delta']:.4f} "
                f"fisher_q={c.get('fisher_q')} loro_min={c.get('loro_min_gain_rate')} "
                f"run_med+={c['runs_median_positive']} PASS={passes(c)} toks={c['tokens']}"
            )
            print("   MEDOID r", c["medoid_run"], c["medoid_id"])
            print(c["medoid_added"][:700].replace("\n", "\n   "))
            print("   ---")

    # Top cross-run pairs for manual audit of the threshold.
    pair_audit = []
    for val, i, j in cross[:25]:
        a, b = substantive[i], substantive[j]
        pair_audit.append(
            {
                "jaccard": float(val),
                "a": {
                    "run": a["run"],
                    "id": a["short"],
                    "delta": a["delta"],
                    "added": a["added"][:500],
                },
                "b": {
                    "run": b["run"],
                    "id": b["short"],
                    "delta": b["delta"],
                    "added": b["added"][:500],
                },
            }
        )

    # Per-run baseline for the report.
    per_run = []
    for run in range(1, 6):
        rs = [r for r in scored_sub if r["run"] == run]
        per_run.append(
            {
                "run": run,
                "n": len(rs),
                "gain_rate": (sum(r["gain"] for r in rs) / len(rs)) if rs else None,
                "clear_rate": (sum(r["clear_gain"] for r in rs) / len(rs))
                if rs
                else None,
                "mean_delta": float(np.mean([r["delta"] for r in rs])) if rs else None,
            }
        )

    out = {
        "scope": RUNS,
        "min_tokens": MIN_TOKENS,
        "shingle_k": SHINGLE_K,
        "clear_delta": CLEAR_DELTA,
        "primary_jaccard": PRIMARY_JACCARD,
        "n_mutations": len(records),
        "n_substantive": len(substantive),
        "n_scored_substantive": len(scored_sub),
        "baseline": {
            "gain_rate": p0,
            "clear_rate": p0_clear,
            "mean_delta": mean0,
            "per_run": per_run,
        },
        "n_cross_pairs": {
            "0.50": sum(v >= 0.50 for v, _, _ in cross),
            "0.55": sum(v >= 0.55 for v, _, _ in cross),
            "0.70": sum(v >= 0.70 for v, _, _ in cross),
            "0.85": sum(v >= 0.85 for v, _, _ in cross),
        },
        "clusters": payloads,
        "pair_audit": pair_audit,
        "strict_ids": [c["id"] for c in strict],
    }
    # shingles/tokens are not JSON; clusters already stripped.
    path = OUT_DIR / "expert_on_similar_gain_clusters.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
