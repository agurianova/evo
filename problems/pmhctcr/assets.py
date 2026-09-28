"""Lazy loaders for ImmRep25 MaSIF npz, PDB CA traces, and cached ESM-2.

TCR files are stored in the direct/straight orientation; pMHC files in the
flipped orientation. ``desc`` equals that canonical view; we still read
``desc_straight`` / ``desc_flipped`` explicitly so the compiler cannot mix them.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

_AA3 = {
    "ALA": 0,
    "CYS": 1,
    "ASP": 2,
    "GLU": 3,
    "PHE": 4,
    "GLY": 5,
    "HIS": 6,
    "ILE": 7,
    "LYS": 8,
    "LEU": 9,
    "MET": 10,
    "ASN": 11,
    "PRO": 12,
    "GLN": 13,
    "ARG": 14,
    "SER": 15,
    "THR": 16,
    "VAL": 17,
    "TRP": 18,
    "TYR": 19,
}
_CHAIN = {"A": 0, "B": 1, "C": 2, "D": 3}
_N_PATCH = 64
_MASIF_DIM = 80


@dataclass(frozen=True)
class MasifAsset:
    tcr_pooled: np.ndarray  # (80,)
    pmhc_pooled: np.ndarray
    tcr_desc: np.ndarray  # (K, 80) subsample of direct descriptors
    tcr_xyz: np.ndarray  # (K, 3)
    pmhc_desc: np.ndarray  # flipped
    pmhc_xyz: np.ndarray
    ok_tcr: bool
    ok_pmhc: bool


@dataclass(frozen=True)
class PdbAsset:
    xyz: np.ndarray  # (N, 3)
    chain: np.ndarray  # (N,) uint8 A=0..D=3
    aa: np.ndarray  # (N,) uint8 0..19, 20=unk
    plddt: np.ndarray  # (N,) Boltz-2 per-residue confidence in B-factor field
    ok: bool


def _subsample(
    desc: np.ndarray, xyz: np.ndarray, n: int = _N_PATCH
) -> tuple[np.ndarray, np.ndarray]:
    if desc.shape[0] <= n:
        return desc.astype(np.float32, copy=False), xyz.astype(np.float32, copy=False)
    idx = np.linspace(0, desc.shape[0] - 1, n).astype(np.int64)
    return desc[idx].astype(np.float32, copy=False), xyz[idx].astype(
        np.float32, copy=False
    )


def _zeros_masif() -> MasifAsset:
    z80 = np.zeros(_MASIF_DIM, dtype=np.float32)
    z_d = np.zeros((_N_PATCH, _MASIF_DIM), dtype=np.float32)
    z_x = np.zeros((_N_PATCH, 3), dtype=np.float32)
    return MasifAsset(z80, z80, z_d, z_x, z_d, z_x, False, False)


@lru_cache(maxsize=1024)
def load_masif(tcr_path: str, pmhc_path: str) -> MasifAsset:
    """Load TCR-direct and pMHC-flipped descriptors. Missing files → zeros."""
    tcr_p = Path(tcr_path)
    pmhc_p = Path(pmhc_path)
    asset = _zeros_masif()
    tcr_pooled = asset.tcr_pooled.copy()
    pmhc_pooled = asset.pmhc_pooled.copy()
    tcr_desc, tcr_xyz = asset.tcr_desc.copy(), asset.tcr_xyz.copy()
    pmhc_desc, pmhc_xyz = asset.pmhc_desc.copy(), asset.pmhc_xyz.copy()
    ok_tcr = ok_pmhc = False
    if tcr_p.is_file():
        with np.load(tcr_p, allow_pickle=False) as z:
            # Direct/straight view — do not use desc_flipped on the TCR file.
            key = "desc_straight" if "desc_straight" in z.files else "desc"
            desc = np.asarray(z[key], dtype=np.float32)
            xyz = (
                np.asarray(z["xyz"], dtype=np.float32)
                if "xyz" in z.files
                else np.zeros((len(desc), 3), np.float32)
            )
            if "pooled" in z.files:
                tcr_pooled = np.asarray(z["pooled"], dtype=np.float32).reshape(-1)[
                    :_MASIF_DIM
                ]
            else:
                tcr_pooled = desc.mean(axis=0)
            tcr_desc, tcr_xyz = _subsample(desc, xyz)
            ok_tcr = True
    if pmhc_p.is_file():
        with np.load(pmhc_p, allow_pickle=False) as z:
            # Flipped view — do not use desc_straight on the pMHC file.
            key = "desc_flipped" if "desc_flipped" in z.files else "desc"
            desc = np.asarray(z[key], dtype=np.float32)
            xyz = (
                np.asarray(z["xyz"], dtype=np.float32)
                if "xyz" in z.files
                else np.zeros((len(desc), 3), np.float32)
            )
            if "pooled" in z.files:
                pmhc_pooled = np.asarray(z["pooled"], dtype=np.float32).reshape(-1)[
                    :_MASIF_DIM
                ]
            else:
                pmhc_pooled = desc.mean(axis=0)
            pmhc_desc, pmhc_xyz = _subsample(desc, xyz)
            ok_pmhc = True
    return MasifAsset(
        tcr_pooled=tcr_pooled,
        pmhc_pooled=pmhc_pooled,
        tcr_desc=tcr_desc,
        tcr_xyz=tcr_xyz,
        pmhc_desc=pmhc_desc,
        pmhc_xyz=pmhc_xyz,
        ok_tcr=ok_tcr,
        ok_pmhc=ok_pmhc,
    )


def _aa_index(resn: str) -> int:
    return _AA3.get(resn, 20)


@lru_cache(maxsize=1024)
def load_pdb(pdb_path: str) -> PdbAsset:
    path = Path(pdb_path)
    if not path.is_file():
        return PdbAsset(
            xyz=np.zeros((1, 3), np.float32),
            chain=np.zeros(1, np.uint8),
            aa=np.full(1, 20, np.uint8),
            plddt=np.zeros(1, np.float32),
            ok=False,
        )
    xyz: list[list[float]] = []
    chain: list[int] = []
    aa: list[int] = []
    plddt: list[float] = []
    with path.open() as handle:
        for line in handle:
            if not line.startswith("ATOM"):
                continue
            if line[12:16].strip() != "CA":
                continue
            try:
                x = float(line[30:38])
                y = float(line[38:46])
                z = float(line[46:54])
                b = float(line[60:66])
            except ValueError:
                continue
            xyz.append([x, y, z])
            chain.append(_CHAIN.get(line[21], 0))
            aa.append(_aa_index(line[17:20].strip()))
            plddt.append(b)
    if not xyz:
        return PdbAsset(
            xyz=np.zeros((1, 3), np.float32),
            chain=np.zeros(1, np.uint8),
            aa=np.full(1, 20, np.uint8),
            plddt=np.zeros(1, np.float32),
            ok=False,
        )
    return PdbAsset(
        xyz=np.asarray(xyz, dtype=np.float32),
        chain=np.asarray(chain, dtype=np.uint8),
        aa=np.asarray(aa, dtype=np.uint8),
        plddt=np.asarray(plddt, dtype=np.float32),
        ok=True,
    )


# Frozen ESM-2 8M cache (facebook/esm2_t6_8M_UR50D). Lookup by ImmRep25 entity_id.
ESM2_MODEL_ID = "facebook/esm2_t6_8M_UR50D"
ESM2_HIDDEN = 320
ESM2_RELDIR = "esm2_t6_8M_UR50D"
_ESM_ZERO = np.zeros(ESM2_HIDDEN, dtype=np.float32)


@dataclass(frozen=True)
class EsmAsset:
    pooled: np.ndarray  # (320,) mean over residue tokens
    cls: np.ndarray  # (320,) BOS/CLS
    residue: np.ndarray  # (L, 320) float32 view of stored float16
    ok: bool


def esm_npz_path(cache_root: Path | str, entity_id: str) -> Path:
    return Path(cache_root) / "by_id" / f"{entity_id}.npz"


@lru_cache(maxsize=4096)
def load_esm(path: str) -> EsmAsset:
    """Load one cached ESM-2 vector. Missing file → zeros."""
    p = Path(path)
    if not p.is_file():
        return EsmAsset(
            _ESM_ZERO.copy(),
            _ESM_ZERO.copy(),
            np.zeros((1, ESM2_HIDDEN), np.float32),
            False,
        )
    with np.load(p, allow_pickle=False) as z:
        pooled = np.asarray(z["pooled"], dtype=np.float32).reshape(-1)[:ESM2_HIDDEN]
        cls = np.asarray(z["cls"], dtype=np.float32).reshape(-1)[:ESM2_HIDDEN]
        residue = np.asarray(z["residue"], dtype=np.float32)
    return EsmAsset(pooled=pooled, cls=cls, residue=residue, ok=True)
