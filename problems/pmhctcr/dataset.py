"""Load ImmRep25 tables and the pMHC-out r0 split."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import pandas as pd

try:
    from assets import ESM2_RELDIR
    from split import load_split
except ImportError:
    from problems.pmhctcr.assets import ESM2_RELDIR
    from problems.pmhctcr.split import load_split

Fold = Literal["train", "val", "test"]
_PROBLEM_DIR = Path(__file__).resolve().parent
_DATA_ENV = "PMHCTCR_DATA"
_SPLIT_ENV = "PMHCTCR_SPLIT"
_FOLDS: dict[Fold, pd.DataFrame] | None = None


def problem_dir() -> Path:
    return _PROBLEM_DIR


def data_root() -> Path:
    """Extracted ImmRep25 tree (`pmhctcr_data/`), or the problem dir as fallback."""
    env = os.environ.get(_DATA_ENV)
    if env:
        return Path(env)
    candidate = _PROBLEM_DIR.parents[1] / "pmhctcr_data"
    if (candidate / "pdb").is_dir() or (candidate / "tables").is_dir():
        return candidate
    return _PROBLEM_DIR


def _tables_dir(root: Path | None) -> Path:
    if root is not None and (Path(root) / "tables" / "samples.parquet").is_file():
        return Path(root) / "tables"
    return _PROBLEM_DIR / "tables"


def split_mode() -> str:
    """``r0`` (frozen ImmRep25 12/4/4) or ``cv3`` (leave-one-pMHC-out)."""
    return os.environ.get(_SPLIT_ENV, "r0").strip().lower() or "r0"


def load_joined(root: Path | None = None) -> pd.DataFrame:
    """Join locked tables with asset paths.

    Tables always come from the problem dir (or ``root/tables`` if present).
    PDB / MaSIF files live under ``data_root()`` so a caller cannot accidentally
    look for parquet next to the 64 GiB asset tree.
    Explicit ``PMHCTCR_DATA`` is treated as ``root`` so a cohort like
    ``double_ood_seed`` supplies both tables and assets.
    """
    if root is None:
        env = os.environ.get(_DATA_ENV)
        if env:
            root = Path(env)
    tables = _tables_dir(root)
    samples = pd.read_parquet(tables / "samples.parquet")
    mhc = pd.read_parquet(tables / "mhc.parquet")
    epi = pd.read_parquet(tables / "epitope.parquet")
    tcr = pd.read_parquet(tables / "tcr.parquet")
    df = (
        samples.merge(mhc, on="mhc_id", how="left")
        .merge(epi, on="epitope_id", how="left")
        .merge(tcr, on="tcr_id", how="left")
    )
    assets = Path(root) if root is not None else data_root()
    if not (assets / "masif").is_dir() and (data_root() / "masif").is_dir():
        assets = data_root()
    df["pdb_path"] = str(assets / "pdb") + "/" + df["complex_id"] + ".pdb"
    masif = assets / "masif"
    df["masif_tcr_path"] = masif.as_posix() + "/" + df["complex_id"] + "/tcr.npz"
    df["masif_pmhc_path"] = masif.as_posix() + "/" + df["complex_id"] + "/pmhc.npz"
    esm = (assets / ESM2_RELDIR / "by_id").as_posix()
    df["esm_mhca_path"] = esm + "/" + df["mhca_id"] + ".npz"
    df["esm_peptide_path"] = esm + "/" + df["epitope_id"] + ".npz"
    df["esm_tcra_path"] = esm + "/" + df["tcra_id"] + ".npz"
    df["esm_tcrb_path"] = esm + "/" + df["tcrb_id"] + ".npz"
    return df


def apply_split(
    df: pd.DataFrame,
    split: dict | None = None,
) -> dict[Fold, pd.DataFrame]:
    split = split or load_split()
    out: dict[Fold, pd.DataFrame] = {}
    for fold in ("train", "val", "test"):
        ids = set(split["pmhc"][fold])
        part = df[df["mhc_epitope_id"].isin(ids)].copy()
        part["fold"] = fold
        out[fold] = part.reset_index(drop=True)
    return out


def load_folds(root: Path | None = None) -> dict[Fold, pd.DataFrame]:
    global _FOLDS
    if root is None:
        if _FOLDS is None:
            _FOLDS = apply_split(load_joined(None))
        return _FOLDS
    return apply_split(load_joined(root))


def load_cv3_folds(
    root: Path | None = None,
) -> list[tuple[pd.DataFrame, pd.DataFrame, str]]:
    """Leave-one-pMHC-out: 2 pMHCs train, 1 pMHC val, three rotations."""
    df = load_joined(root)
    ids = sorted(df["mhc_epitope_id"].astype(str).unique())
    if len(ids) != 3:
        raise ValueError(f"cv3 expects exactly 3 pMHCs, got {len(ids)}: {ids}")
    folds: list[tuple[pd.DataFrame, pd.DataFrame, str]] = []
    for val_id in ids:
        train = df[df["mhc_epitope_id"] != val_id].copy()
        val = df[df["mhc_epitope_id"] == val_id].copy()
        train["fold"] = "train"
        val["fold"] = "val"
        folds.append((train.reset_index(drop=True), val.reset_index(drop=True), val_id))
    return folds


def feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    drop = [c for c in ("label", "fold") if c in df.columns]
    return df.drop(columns=drop)
