"""Freeze a 12/4/4 pMHC split. No pMHC in two folds. All pairs are kept."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

FOLDS = ("train", "val", "test")
SPLIT_SEED = 0
SPLIT_NAME = "r0"

_PROBLEM_DIR = Path(__file__).resolve().parent


def load_samples(problem_dir: Path | None = None) -> pd.DataFrame:
    tables = (problem_dir or _PROBLEM_DIR) / "tables"
    samples = pd.read_parquet(tables / "samples.parquet")
    mhc = pd.read_parquet(tables / "mhc.parquet")[["mhc_id", "mhca_allele"]]
    return samples.merge(mhc, on="mhc_id", how="left")


def _allele_ids(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    allele = df.groupby("mhc_epitope_id")["mhca_allele"].first()
    a_ids = np.array(sorted(allele[allele.eq("HLA-A*02:01")].index))
    b_ids = np.array(sorted(allele[allele.eq("HLA-B*40:01")].index))
    if len(a_ids) != 10 or len(b_ids) != 10:
        raise ValueError(f"expected 10+10 alleles, got {len(a_ids)}+{len(b_ids)}")
    return a_ids, b_ids


def draw_pmhc_partition(df: pd.DataFrame, *, seed: int = SPLIT_SEED) -> dict[str, list[str]]:
    a_ids, b_ids = _allele_ids(df)
    rng = np.random.default_rng(seed)
    a = a_ids.copy()
    b = b_ids.copy()
    rng.shuffle(a)
    rng.shuffle(b)
    return {
        "train": sorted(a[:6].tolist() + b[:6].tolist()),
        "val": sorted(a[6:8].tolist() + b[6:8].tolist()),
        "test": sorted(a[8:].tolist() + b[8:].tolist()),
    }


def fold_stats(df: pd.DataFrame, pmhc: dict[str, list[str]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for fold, ids in pmhc.items():
        part = df[df["mhc_epitope_id"].isin(ids)]
        per = {}
        for p in ids:
            sub = part[part["mhc_epitope_id"] == p]
            per[p] = {"n": int(len(sub)), "n_pos": int(sub["label"].sum())}
        out[fold] = {
            "n": int(len(part)),
            "n_pos": int(part["label"].sum()),
            "n_tcr": int(part["tcr_id"].nunique()),
            "n_pmhc": len(ids),
            "pos_rate": float(part["label"].mean()) if len(part) else 0.0,
            "per_pmhc": per,
        }
    return out


def build_split(df: pd.DataFrame, *, seed: int = SPLIT_SEED) -> dict[str, Any]:
    pmhc = draw_pmhc_partition(df, seed=seed)
    stats = fold_stats(df, pmhc)
    n_pairs = int(len(df))
    kept = sum(stats[f]["n"] for f in FOLDS)
    if kept != n_pairs:
        raise AssertionError(f"expected all {n_pairs} pairs kept, got {kept}")
    return {
        "name": SPLIT_NAME,
        "seed": seed,
        "protocol": {
            "pmhc_counts": {"train": 12, "val": 4, "test": 4},
            "allele_counts": {
                "train": {"HLA-A*02:01": 6, "HLA-B*40:01": 6},
                "val": {"HLA-A*02:01": 2, "HLA-B*40:01": 2},
                "test": {"HLA-A*02:01": 2, "HLA-B*40:01": 2},
            },
            "keep": "all pairs; split unit is mhc_epitope_id",
            "no_pmhc_leak": True,
            "no_tcr_leak": False,
        },
        "pmhc": pmhc,
        "stats": stats,
        "dropped": 0,
        "n_pairs": n_pairs,
    }


def assert_no_pmhc_leak(split: dict[str, Any]) -> None:
    for left, right in (("train", "val"), ("train", "test"), ("val", "test")):
        if set(split["pmhc"][left]) & set(split["pmhc"][right]):
            raise AssertionError(f"pMHC leak {left}/{right}")
    assigned = set(split["pmhc"]["train"]) | set(split["pmhc"]["val"]) | set(split["pmhc"]["test"])
    if len(assigned) != 20:
        raise AssertionError(f"expected 20 pMHCs, got {len(assigned)}")


def fold_complex_ids(df: pd.DataFrame, split: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for fold in FOLDS:
        ids = set(split["pmhc"][fold])
        out[fold] = sorted(df.loc[df["mhc_epitope_id"].isin(ids), "complex_id"].tolist())
    return out


def write_split(path: Path, split: dict[str, Any]) -> None:
    assert_no_pmhc_leak(split)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(split, indent=2, sort_keys=False) + "\n")


def load_split(path: Path | None = None) -> dict[str, Any]:
    p = path or (_PROBLEM_DIR / "splits" / f"{SPLIT_NAME}.json")
    split = json.loads(p.read_text())
    assert_no_pmhc_leak(split)
    return split


def main() -> None:
    df = load_samples()
    split = build_split(df)
    out = _PROBLEM_DIR / "splits" / f"{SPLIT_NAME}.json"
    write_split(out, split)
    print(json.dumps({k: split[k] for k in ("name", "seed", "dropped", "n_pairs", "pmhc")}, indent=2))
    print("stats", json.dumps(split["stats"], indent=2))
    print("wrote", out)


if __name__ == "__main__":
    main()
