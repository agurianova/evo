#!/usr/bin/env python3
"""Expert-hypothesis inspirations in terra expert-on r1–r5.

The mutator reads the parent's mutation_context. A child is inspired by
whatever insight is stored on its parent. Implementation is judged only from
lines present in the child and absent from the parent.

Hypotheses (problems/pmhctcr/expert_hypotheses.txt):
  1 surface complementarity
  2 transferable V-region features
  3 meta stable states
  4 structure confidence
Ranking-loss suggestions are the training contract, not one of the four.
"""

from __future__ import annotations

import importlib.util
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, fisher_exact

REPO = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "expert_hypothesis_mutation_gains.json"
SPEC = importlib.util.spec_from_file_location(
    "cl", Path(__file__).resolve().parent / "cluster_expert_on_similar_mutations.py"
)
cl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cl)

TAG_RE = re.compile(r"\*\*\[([^\]]+)\]")
SUB_RE = re.compile(r"substitute:\s*(.+?)(?:\s*\|\s*vs lineage:|\n## |\n\n|$)", re.I | re.S)

# Suggestion-side anchors. A hit is one phrase family, not one token.
SUGGESTION_ANCHORS: dict[str, list[tuple[str, str]]] = {
    "h1_surface": [
        ("masif_orient", r"desc_straight|desc_flipped|masif"),
        ("reciprocal_match", r"reciprocal[\s-]*match|mutual nn|l2\s*<\s*1\.7|distance\s*<=\s*1\.7|threshold\s*1\.7"),
        ("components", r"connected component|trace[_\s-]*length|n_components|matched[_\s-]*area|reciprocal_match_frac"),
        ("patch_distance", r"patch distance|patch matching|surface match"),
    ],
    "h2_vregion": [
        ("region_pool", r"region_indices|split_chain"),
        ("cdr_fr", r"cdr1|cdr2|framework region|fr1"),
        ("no_vgene", r"trav|trbv|v/j-gene|v-gene|gene identit"),
    ],
    "h3_states": [
        ("k_states", r"latent state|contact-state|k\s*=\s*[2-8]|n_states|states\s*[:=]"),
        ("aggregate", r"log-?sum-?exp|logsumexp|softmax gate|max pooling"),
        ("diversity", r"entropy penalty|state collapse|repulsion|diversity constraint"),
        ("parallel_heads", r"parallel head|state head|independent .*head"),
    ],
    "h4_confidence": [
        ("plddt", r"plddt|b-factor"),
        ("regional_conf", r"mean/min|interface plddt|confidence feature"),
        ("weight", r"confidence weight|key weight|down-weight|log-attention"),
        ("angstrom", r"8\s*å|8\s*a\b|<8|within 8"),
    ],
}

CODE_CHECKS = {
    "h1_surface": [
        ("desc_orient", r"desc_straight|desc_flipped"),
        ("threshold_17", r"1\.7"),
        ("reciprocal", r"reciprocal"),
        ("components", r"component|trace_length|area_frac"),
        ("surface_tree", r"cKDTree|masif_"),
    ],
    "h2_vregion": [
        ("region_indices", r"region_indices|split_chain"),
        ("region_names", r"cdr1|fr1|cdr2"),
        ("esm_pool", r"load_esm|residue"),
    ],
    "h3_states": [
        ("state_param", r"states:\s*int|self\.states|n_states|states\s*=\s*[2-8]"),
        ("per_state_loop", r"for state in range|range\(self\.states\)|range\(states\)"),
        ("aggregate", r"logsumexp|softmax"),
        ("diversity", r"entropy"),
        ("state_modules", r"ModuleList"),
    ],
    "h4_confidence": [
        ("plddt", r"plddt"),
        ("confidence_name", r"confidence|peptide_conf"),
        ("interface_8", r"8\.0|<= 8|<\s*8"),
        ("as_weight", r"clamp|log\(\)|weight"),
    ],
}

# Minimum distinct anchor families for a positive call.
SUGGEST_MIN = {"h1_surface": 1, "h2_vregion": 1, "h3_states": 1, "h4_confidence": 1}
# Code must show the mechanism, not a single generic token.
CODE_MIN = {"h1_surface": 2, "h2_vregion": 2, "h3_states": 2, "h4_confidence": 2}

NAMES = {
    "h1_surface": "1. Surface complementarity",
    "h2_vregion": "2. V-region features",
    "h3_states": "3. Meta stable states",
    "h4_confidence": "4. Structure confidence",
}


def hits(text: str, anchors: list[tuple[str, str]]) -> list[str]:
    found = []
    for name, pat in anchors:
        if re.search(pat, text, re.I):
            found.append(name)
    return found


def parse_insight(ctx: str) -> dict:
    if not ctx or "Program Insights" not in ctx:
        return {"tag": "", "substitute": "", "has_insight": False}
    block = ctx[ctx.find("## Program Insights") : ctx.find("## Program Insights") + 2500]
    tags = TAG_RE.findall(block)
    sub = SUB_RE.search(block)
    return {
        "tag": tags[0] if tags else "",
        "substitute": re.sub(r"\s+", " ", sub.group(1)).strip() if sub else "",
        "has_insight": True,
    }


def _tag_hypothesis(tag: str) -> str:
    tag_l = tag.lower()
    if any(s in tag_l for s in ("surface", "patch", "masif", "spatial", "complementar", "threshold")):
        return "h1_surface"
    if any(s in tag_l for s in ("v_region", "region_encod", "region_pool")):
        return "h2_vregion"
    if any(s in tag_l for s in ("latent_state", "multi_state", "state_ensemble", "state_collapse", "state_head")):
        return "h3_states"
    if "confidence" in tag_l or "plddt" in tag_l:
        return "h4_confidence"
    if any(s in tag_l for s in ("ranking", "bce", "loss", "objective")):
        return "training_contract"
    return ""


def label_suggestion(tag: str, substitute: str) -> dict[str, list[str]]:
    """Tag is the inspiration. Substitute text is used only when the tag is generic.

    Clauses that say to keep an existing mechanism are removed so a ranking
    edit that mentions 'keep pLDDT' is not counted as a confidence hypothesis.
    """
    mapped = _tag_hypothesis(tag)
    if mapped == "training_contract":
        return {"training_contract": ["tag"]}
    if mapped:
        return {mapped: ["tag"]}
    text = re.sub(
        r"keep the existing[^.;]*[.;]|retain the existing[^.;]*[.;]",
        " ",
        substitute,
        flags=re.I,
    )
    out = {}
    for hyp, anchors in SUGGESTION_ANCHORS.items():
        found = hits(text, anchors)
        if len(found) >= SUGGEST_MIN[hyp]:
            out[hyp] = found
    if re.search(r"ranking|softplus|binary_cross_entropy", text, re.I) and not out:
        out["training_contract"] = ["ranking"]
    return out


def label_code(added: str) -> dict[str, list[str]]:
    out = {}
    for hyp, anchors in CODE_CHECKS.items():
        found = hits(added, anchors)
        # H1: orientation + a match statistic, or components + threshold.
        if hyp == "h1_surface":
            ok = ("desc_orient" in found and ("reciprocal" in found or "threshold_17" in found or "components" in found)) or (
                "components" in found and ("reciprocal" in found or "threshold_17" in found)
            )
        elif hyp == "h2_vregion":
            ok = "region_indices" in found or ("region_names" in found and "esm_pool" in found)
        elif hyp == "h3_states":
            ok = "state_param" in found and len(found) >= 2
        elif hyp == "h4_confidence":
            ok = ("plddt" in found or "confidence_name" in found) and len(found) >= 2
        else:
            ok = False
        if ok:
            out[hyp] = found
    return out


def load_all() -> list[dict]:
    rows = []
    for name in cl.RUNS:
        rep = int(name.rsplit("_r", 1)[1])
        storage = REPO / "outputs" / name / "storage" / "pmhctcr" / "programs"
        progs = {}
        for path in storage.glob("*.json"):
            d = json.loads(path.read_text())
            progs[d["id"]] = d
        seed_ids = {
            d["id"]
            for d in progs.values()
            if not (d.get("lineage") or {}).get("parents")
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
        for d in progs.values():
            parents = (d.get("lineage") or {}).get("parents") or []
            if not parents:
                continue
            parent = progs.get(parents[0])
            if parent is None:
                continue
            added, _removed = cl.code_delta(parent.get("code") or "", d.get("code") or "")
            m = d.get("metrics") or {}
            pm = parent.get("metrics") or {}
            fit, pfit = m.get("fitness"), pm.get("fitness")
            scored = (
                m.get("is_valid") == 1
                and pm.get("is_valid") == 1
                and fit is not None
                and pfit is not None
                and fit >= 0
                and pfit >= 0
            )
            delta = (fit - pfit) if scored else None
            insight = parse_insight((parent.get("metadata") or {}).get("mutation_context") or "")
            sug = label_suggestion(insight["tag"], insight["substitute"]) if insight["has_insight"] else {}
            code = label_code(added) if len(cl.tokens_of(added)) >= 12 else {}
            rows.append(
                {
                    "run": rep,
                    "id": d["id"][:8],
                    "parent": parents[0][:8],
                    "generation": (d.get("lineage") or {}).get("generation"),
                    "on_champion_lineage": d["id"] in lineage,
                    "scored": scored,
                    "delta": delta,
                    "gain": bool(scored and delta > 1e-8),
                    "clear_gain": bool(scored and delta >= cl.CLEAR_DELTA),
                    "fitness": fit if scored else None,
                    "parent_fitness": pfit if scored else None,
                    "added": added,
                    "n_tokens": len(cl.tokens_of(added)),
                    "has_insight": insight["has_insight"],
                    "tag": insight["tag"],
                    "substitute": insight["substitute"],
                    "suggestion": sorted(k for k in sug if k.startswith("h")),
                    "suggestion_hits": {k: v for k, v in sug.items() if k.startswith("h")},
                    "training_contract": "training_contract" in sug and not any(k.startswith("h") for k in sug),
                    "code": sorted(code),
                    "code_hits": code,
                    "parent_is_seed": parents[0] in seed_ids,
                }
            )
    return rows


def summarize(members: list[dict], p0: float, n_gain_all: int, n_all: int) -> dict:
    scored = [m for m in members if m["scored"]]
    if not scored:
        return {"n": len(members), "n_scored": 0}
    gains = sum(m["gain"] for m in scored)
    clears = sum(m["clear_gain"] for m in scored)
    deltas = [m["delta"] for m in scored]
    by_run = defaultdict(list)
    by_parent = defaultdict(list)
    for m in scored:
        by_run[m["run"]].append(m["delta"])
        by_parent[(m["run"], m["parent"])].append(m["delta"])
    parent_meds = {k: float(np.median(v)) for k, v in by_parent.items()}
    run_meds = {r: float(np.median(v)) for r, v in by_run.items()}
    a, b = gains, len(scored) - gains
    c = n_gain_all - gains
    d = (n_all - len(scored)) - c
    p_fisher = None
    if min(a, b, c, d) >= 0:
        _odds, p_fisher = fisher_exact([[a, b], [c, d]], alternative="greater")
    p_parent = float(
        binomtest(
            sum(v > 0 for v in parent_meds.values()),
            len(parent_meds),
            p0,
            alternative="greater",
        ).pvalue
    ) if parent_meds else None
    return {
        "n": len(members),
        "n_scored": len(scored),
        "n_gain": gains,
        "gain_rate": gains / len(scored),
        "n_clear": clears,
        "clear_rate": clears / len(scored),
        "mean_delta": float(np.mean(deltas)),
        "median_delta": float(np.median(deltas)),
        "runs": sorted(by_run),
        "n_runs": len(by_run),
        "run_medians": {str(k): v for k, v in sorted(run_meds.items())},
        "runs_median_positive": sum(v > 0 for v in run_meds.values()),
        "n_parents": len(parent_meds),
        "parents_positive": sum(v > 0 for v in parent_meds.values()),
        "parent_positive_rate": sum(v > 0 for v in parent_meds.values()) / len(parent_meds),
        "parent_median_of_medians": float(np.median(list(parent_meds.values()))),
        "fisher_p": None if p_fisher is None else float(p_fisher),
        "parent_binom_p": p_parent,
        "n_champion_lineage": sum(m["on_champion_lineage"] for m in scored),
    }


def repeated_lines(members: list[dict], p0_n_gain: int, n_all: int) -> list[dict]:
    scored = [m for m in members if m["scored"]]
    line_members: dict[str, list[dict]] = defaultdict(list)
    for m in scored:
        for ln in set(m["added"].splitlines()):
            if len(ln) < 24:
                continue
            line_members[ln].append(m)
    rows = []
    for ln, group in line_members.items():
        # unique programs
        uniq = {m["id"]: m for m in group}
        group = list(uniq.values())
        runs = {m["run"] for m in group}
        if len(runs) < 3 or len(group) < 4:
            continue
        share = max(Counter(m["run"] for m in group).values()) / len(group)
        if share > 0.65:
            continue
        gains = sum(m["gain"] for m in group)
        rate = gains / len(group)
        deltas = [m["delta"] for m in group]
        if rate < 0.55 or float(np.mean(deltas)) <= 0:
            continue
        a, b = gains, len(group) - gains
        c = p0_n_gain - gains
        d = (n_all - len(group)) - c
        p = None
        if min(a, b, c, d) >= 0:
            _o, p = fisher_exact([[a, b], [c, d]], alternative="greater")
        by_parent = defaultdict(list)
        for m in group:
            by_parent[(m["run"], m["parent"])].append(m["delta"])
        rows.append(
            {
                "line": ln[:180],
                "n": len(group),
                "n_runs": len(runs),
                "runs": sorted(runs),
                "share": share,
                "gain_rate": rate,
                "n_gain": gains,
                "mean_delta": float(np.mean(deltas)),
                "median_delta": float(np.median(deltas)),
                "n_parents": len(by_parent),
                "parents_positive": sum(float(np.median(v)) > 0 for v in by_parent.values()),
                "fisher_p": None if p is None else float(p),
            }
        )
    rows.sort(key=lambda r: (r["fisher_p"] if r["fisher_p"] is not None else 1, -r["gain_rate"]))
    return rows[:12]


def main() -> None:
    rows = load_all()
    scored = [r for r in rows if r["scored"]]
    n_all = len(scored)
    n_gain = sum(r["gain"] for r in scored)
    p0 = n_gain / n_all
    print(f"children={len(rows)} scored={n_all} gain_rate={p0:.3f}")
    with_insight = [r for r in scored if r["has_insight"]]
    print(f"scored with parent insight={len(with_insight)} ({len(with_insight)/n_all:.0%})")

    inspired = [r for r in scored if r["suggestion"]]
    print(f"scored inspired by >=1 hypothesis={len(inspired)}")
    contract = [r for r in scored if r["training_contract"]]
    print(f"scored training-contract only={len(contract)} gain={sum(r['gain'] for r in contract)}/{len(contract) or 1}")

    report = {
        "baseline": {"n_scored": n_all, "gain_rate": p0, "n_gain": n_gain},
        "coverage": {
            "scored": n_all,
            "with_parent_insight": len(with_insight),
            "inspired": len(inspired),
        },
        "hypotheses": {},
    }
    for hyp in ("h1_surface", "h2_vregion", "h3_states", "h4_confidence"):
        sug = [r for r in scored if hyp in r["suggestion"]]
        code = [r for r in scored if hyp in r["code"]]
        both = [r for r in scored if hyp in r["suggestion"] and hyp in r["code"]]
        inspired_not_code = [r for r in sug if hyp not in r["code"]]
        print(f"\n==== {NAMES[hyp]} ====")
        for label, group in (
            ("suggested", sug),
            ("code", code),
            ("both", both),
            ("suggested_not_in_code", inspired_not_code),
        ):
            s = summarize(group, p0, n_gain, n_all)
            print(
                f"  {label}: n={s.get('n_scored')} gain={s.get('n_gain')}/{s.get('n_scored')} "
                f"({(s.get('gain_rate') or 0):.0%}) med={s.get('median_delta')} "
                f"parents+={s.get('parents_positive')}/{s.get('n_parents')} "
                f"runMed+={s.get('runs_median_positive')}/{s.get('n_runs')} "
                f"fisher={s.get('fisher_p')} parent_p={s.get('parent_binom_p')}"
            )
        lines = repeated_lines(both or code, n_gain, n_all)
        print("  repeated lines in both-or-code:")
        for ln in lines[:6]:
            print(
                f"    p={ln['fisher_p']:.2e} n={ln['n']} runs={ln['runs']} "
                f"gain={ln['gain_rate']:.0%} med={ln['median_delta']:+.4f} "
                f"parents+={ln['parents_positive']}/{ln['n_parents']} | {ln['line'][:110]}"
            )
        # audit substitutes
        print("  sample suggestions:")
        shown = 0
        for r in sug:
            if shown >= 3:
                break
            shown += 1
            print(f"    r{r['run']} {r['id']} tag={r['tag']} code={r['code']} d={r['delta']:+.4f}")
            print(f"      {r['substitute'][:220]}")
        report["hypotheses"][hyp] = {
            "name": NAMES[hyp],
            "suggested": summarize(sug, p0, n_gain, n_all),
            "code": summarize(code, p0, n_gain, n_all),
            "both": summarize(both, p0, n_gain, n_all),
            "suggested_not_in_code": summarize(inspired_not_code, p0, n_gain, n_all),
            "repeated_lines": lines,
            "both_members": [
                {
                    "run": m["run"],
                    "id": m["id"],
                    "parent": m["parent"],
                    "delta": m["delta"],
                    "gain": m["gain"],
                    "clear_gain": m["clear_gain"],
                    "tag": m["tag"],
                    "on_champion_lineage": m["on_champion_lineage"],
                    "fitness": m["fitness"],
                    "parent_fitness": m["parent_fitness"],
                    "substitute": m["substitute"][:300],
                }
                for m in sorted(both, key=lambda m: -(m["delta"] or -9))
            ],
        }

    # multi-hypothesis suggestions
    multi = [r for r in scored if len(r["suggestion"]) >= 2]
    print(f"\nmulti-hypothesis suggestions: {len(multi)}")
    none = [r for r in with_insight if not r["suggestion"] and not r["training_contract"]]
    print(f"insight but unclassified: {len(none)}")
    tags = Counter(r["tag"] for r in none)
    print(" unclassified tags", tags.most_common(12))
    for r in none[:6]:
        print(f"  r{r['run']} {r['tag']}: {r['substitute'][:160]}")

    report["training_contract"] = summarize(contract, p0, n_gain, n_all)
    OUT.write_text(json.dumps(report, indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
