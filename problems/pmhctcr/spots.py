"""Complementary MaSIF spots: TCR points whose nearest pMHC descriptor is close.

A spot is the set of (subsampled) TCR surface points with NN < threshold
(default L2 1.7). Localization features (CDR3 fraction, distance to peptide)
are the signal; mean pooled 80-d MaSIF is only a weak proxy.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from problems.pmhctcr.assets import MasifAsset, PdbAsset, load_pdb
from problems.pmhctcr.genotype import Genotype
from problems.pmhctcr.regions import region_indices, split_chain

SPOT_CORE = (
    "n_match",
    "area_frac",
    "n_components",
    "gyration",
    "com_x",
    "com_y",
    "com_z",
    "min_nn",
    "mean_nn",
    "alpha_frac",
    "beta_frac",
    "cdr3_frac",
    "all_cdr_frac",
    "all_fr_frac",
    "dist_peptide",
    "dist_mhc",
    "dist_cdr3",
)
_CHUNK = 64
_ZERO = np.zeros(len(SPOT_CORE), dtype=np.float64)


def _subsample(arr: np.ndarray, n: int) -> np.ndarray:
    if arr.shape[0] <= n:
        return arr
    idx = np.linspace(0, arr.shape[0] - 1, n).astype(np.int64)
    return arr[idx]


def _min_nn(tcr: np.ndarray, pmhc: np.ndarray, metric: str) -> np.ndarray:
    n = tcr.shape[0]
    out = np.full(n, np.inf, dtype=np.float32)
    if metric == "cosine":
        t = tcr / np.clip(np.linalg.norm(tcr, axis=1, keepdims=True), 1e-8, None)
        p = pmhc / np.clip(np.linalg.norm(pmhc, axis=1, keepdims=True), 1e-8, None)
        best = np.full(n, -np.inf, dtype=np.float32)
        for start in range(0, p.shape[0], _CHUNK):
            sim = t @ p[start : start + _CHUNK].T
            best = np.maximum(best, sim.max(axis=1))
        return (1.0 - best).astype(np.float32)
    for start in range(0, pmhc.shape[0], _CHUNK):
        chunk = pmhc[start : start + _CHUNK]
        d2 = ((tcr[:, None, :] - chunk[None, :, :]) ** 2).sum(axis=-1)
        out = np.minimum(out, np.sqrt(d2.min(axis=1)))
    return out


def _largest_component_mask(xyz: np.ndarray, linkage: float) -> np.ndarray:
    n = xyz.shape[0]
    if n == 0:
        return np.zeros(0, dtype=bool)
    if n == 1:
        return np.ones(1, dtype=bool)
    parent = np.arange(n)

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        pi, pj = find(i), find(j)
        if pi != pj:
            parent[pj] = pi

    d = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=-1)
    ii, jj = np.where(np.triu(d <= linkage, k=1))
    for i, j in zip(ii.tolist(), jj.tolist()):
        union(i, j)
    roots = np.fromiter((find(i) for i in range(n)), dtype=np.int64, count=n)
    sizes = np.bincount(roots)
    largest = int(sizes.argmax())
    return roots == largest


def _trace_length(xyz: np.ndarray, linkage: float) -> float:
    if xyz.shape[0] <= 1:
        return float(xyz.shape[0])
    mask = _largest_component_mask(xyz, linkage)
    pts = xyz[mask]
    if pts.shape[0] <= 1:
        return float(pts.shape[0])
    d = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=-1)
    return float(d.max())


def _nearest_indices(src: np.ndarray, dst: np.ndarray, metric: str) -> np.ndarray:
    n = src.shape[0]
    out = np.zeros(n, dtype=np.int64)
    if metric == "cosine":
        src_n = src / np.clip(np.linalg.norm(src, axis=1, keepdims=True), 1e-8, None)
        dst_n = dst / np.clip(np.linalg.norm(dst, axis=1, keepdims=True), 1e-8, None)
        for start in range(0, n, _CHUNK):
            chunk = src_n[start : start + _CHUNK]
            sim = chunk @ dst_n.T
            out[start : start + chunk.shape[0]] = sim.argmax(axis=1)
        return out
    for i in range(n):
        d2 = ((dst - src[i]) ** 2).sum(axis=1)
        out[i] = int(d2.argmin())
    return out


def _reciprocal_match_frac(
    tcr: np.ndarray,
    pmhc: np.ndarray,
    match: np.ndarray,
    metric: str,
) -> float:
    if not match.any():
        return 0.0
    tcr_to_pmhc = _nearest_indices(tcr, pmhc, metric)
    pmhc_to_tcr = _nearest_indices(pmhc, tcr, metric)
    reciprocal = 0
    for i in np.where(match)[0]:
        j = int(tcr_to_pmhc[i])
        if int(pmhc_to_tcr[j]) == int(i):
            reciprocal += 1
    return float(reciprocal / max(int(match.sum()), 1))


def masif_complementarity_stats(
    tcr_desc: np.ndarray,
    tcr_xyz: np.ndarray,
    pmhc_desc: np.ndarray,
    pmhc_xyz: np.ndarray,
    *,
    threshold: float = 1.7,
    linkage: float = 2.0,
    metric: str = "l2",
) -> dict[str, float]:
    """Complementary MaSIF match stats for hypothesis 1 (full or subsampled surfaces)."""
    nn = _min_nn(tcr_desc, pmhc_desc, metric)
    if metric == "cosine":
        cos_cut = 0.5 if threshold >= 1.0 else threshold
        match = nn <= (1.0 - cos_cut)
    else:
        match = nn < float(threshold)
    n_match = int(match.sum())
    out = {
        "n_match": float(n_match),
        "area_frac": float(n_match / max(len(match), 1)),
        "min_nn": float(nn.min()) if nn.size else 0.0,
        "mean_nn": float(nn[match].mean()) if n_match else float(nn.mean()) if nn.size else 0.0,
        "n_components": 0.0,
        "max_component_size": 0.0,
        "trace_length": 0.0,
        "reciprocal_match_frac": 0.0,
    }
    if n_match == 0:
        return out
    pts = tcr_xyz[match]
    out["n_components"] = float(_n_components(pts, linkage))
    comp_mask = _largest_component_mask(pts, linkage)
    out["max_component_size"] = float(comp_mask.sum())
    out["trace_length"] = _trace_length(pts, linkage)
    out["reciprocal_match_frac"] = _reciprocal_match_frac(
        tcr_desc, pmhc_desc, match, metric
    )
    return out


def _n_components(xyz: np.ndarray, linkage: float) -> int:
    n = xyz.shape[0]
    if n <= 1:
        return int(n)
    parent = np.arange(n)

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        pi, pj = find(i), find(j)
        if pi != pj:
            parent[pj] = pi

    d = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=-1)
    ii, jj = np.where(np.triu(d <= linkage, k=1))
    for i, j in zip(ii.tolist(), jj.tolist()):
        union(i, j)
    return len({find(i) for i in range(n)})


def _cell(val: object) -> str:
    if val is None:
        return ""
    if isinstance(val, float) and np.isnan(val):
        return ""
    return str(val)


def _vdomain(seq: str, cdr3: str, vgene: str) -> str:
    parts = split_chain(seq, cdr3, vgene)
    body = (
        parts["fr1"]
        + parts["cdr1"]
        + parts["fr2"]
        + parts["cdr2"]
        + parts["fr3"]
        + parts["cdr3"]
        + parts["fr4"]
    )
    return body or seq


def _seq_tags(seq: str, cdr3: str, vgene: str) -> np.ndarray:
    n = len(seq)
    tags = np.full(n, "other", dtype=object)
    if n == 0:
        return tags
    for name in ("fr1", "cdr1", "fr2", "cdr2", "fr3", "cdr3", "fr4"):
        idx = region_indices(seq, name, cdr3=cdr3, vgene=vgene)
        if idx.size:
            tags[idx] = name
    return tags


def _ca_region_fracs(
    masif_xyz: np.ndarray,
    match: np.ndarray,
    pdb: PdbAsset,
    row: pd.Series,
) -> tuple[float, float, float, float, float, np.ndarray]:
    """alpha_frac, beta_frac, cdr3_frac, all_cdr_frac, all_fr_frac, cdr3_com."""
    empty = (0.0, 0.0, 0.0, 0.0, 0.0, np.zeros(3, dtype=np.float64))
    if not pdb.ok or not match.any():
        return empty
    pts = masif_xyz[match]
    ca = pdb.xyz
    d2 = ((pts[:, None, :] - ca[None, :, :]) ** 2).sum(axis=-1)
    nearest = d2.argmin(axis=1)
    chains = pdb.chain[nearest]
    n = max(len(pts), 1)
    alpha = float((chains == 0).mean())
    beta = float((chains == 1).mean())
    cdr3 = all_cdr = all_fr = 0.0
    cdr3_xyz: list[np.ndarray] = []
    for chain_id, prefix in ((0, "tcra"), (1, "tcrb")):
        on = chains == chain_id
        if not on.any():
            continue
        seq = _vdomain(
            _cell(row.get(f"{prefix}_seq")),
            _cell(row.get(f"{prefix}_seq_cdr3")),
            _cell(row.get(f"{prefix}_vgene")),
        )
        if not seq:
            continue
        tags = _seq_tags(
            seq,
            _cell(row.get(f"{prefix}_seq_cdr3")),
            _cell(row.get(f"{prefix}_vgene")),
        )
        ca_idx = np.where(pdb.chain == chain_id)[0]
        if ca_idx.size == 0:
            continue
        local = np.searchsorted(ca_idx, nearest[on])
        local = np.clip(local, 0, ca_idx.size - 1)
        seq_i = (local * len(seq) / ca_idx.size).astype(np.int64)
        seq_i = np.clip(seq_i, 0, len(seq) - 1)
        lab = tags[seq_i]
        cdr3 += float((lab == "cdr3").sum())
        all_cdr += float(np.isin(lab, ("cdr1", "cdr2", "cdr3")).sum())
        all_fr += float(np.isin(lab, ("fr1", "fr2", "fr3", "fr4")).sum())
        if (lab == "cdr3").any():
            cdr3_xyz.append(pts[on][lab == "cdr3"])
    cdr3 /= n
    all_cdr /= n
    all_fr /= n
    if cdr3_xyz:
        com = np.concatenate(cdr3_xyz, axis=0).mean(axis=0).astype(np.float64)
    else:
        com = np.zeros(3, dtype=np.float64)
    return alpha, beta, cdr3, all_cdr, all_fr, com


def _chain_com(pdb: PdbAsset, chain_id: int) -> np.ndarray:
    m = pdb.chain == chain_id
    if not pdb.ok or not m.any():
        return np.zeros(3, dtype=np.float64)
    return pdb.xyz[m].mean(axis=0).astype(np.float64)


def core_spot_features(
    g: Genotype, asset: MasifAsset, row: pd.Series
) -> dict[str, float]:
    zeros = {name: 0.0 for name in SPOT_CORE}
    if not asset.ok_tcr or not asset.ok_pmhc:
        return zeros
    su = g.encoders.surface.spots
    n_keep = int(su.subsample)
    tcr = _subsample(asset.tcr_desc, n_keep)
    pmhc = _subsample(asset.pmhc_desc, n_keep)
    xyz = _subsample(asset.tcr_xyz, n_keep)
    nn = _min_nn(tcr, pmhc, su.metric)
    if su.metric == "cosine":
        # threshold is a cosine floor stored in the same field; match if 1-cos <= 1-thr
        # Callers keep 1.7 for L2. For cosine, values in (0.5, 4) are not a cosine
        # floor — treat >=1 as "use 0.5" so a leftover 1.7 does not match everything.
        thr = float(su.threshold)
        cos_cut = 0.5 if thr >= 1.0 else thr
        match = nn <= (1.0 - cos_cut)
    else:
        match = nn < float(su.threshold)
    n_match = int(match.sum())
    zeros["n_match"] = float(n_match)
    zeros["area_frac"] = float(n_match / max(len(match), 1))
    if n_match == 0:
        zeros["min_nn"] = float(nn.min()) if nn.size else 0.0
        zeros["mean_nn"] = float(nn.mean()) if nn.size else 0.0
        return zeros
    pts = xyz[match]
    com = pts.mean(axis=0)
    zeros["com_x"] = float(com[0])
    zeros["com_y"] = float(com[1])
    zeros["com_z"] = float(com[2])
    zeros["gyration"] = float(np.sqrt(((pts - com) ** 2).sum(axis=1).mean()))
    zeros["n_components"] = float(_n_components(pts, float(su.linkage_A)))
    zeros["min_nn"] = float(nn[match].min())
    zeros["mean_nn"] = float(nn[match].mean())
    pdb_path = str(row["pdb_path"]) if "pdb_path" in row.index else ""
    pdb = load_pdb(pdb_path) if pdb_path else None
    if pdb is not None and pdb.ok:
        alpha, beta, cdr3, all_cdr, all_fr, cdr3_com = _ca_region_fracs(
            xyz, match, pdb, row
        )
        zeros["alpha_frac"] = alpha
        zeros["beta_frac"] = beta
        zeros["cdr3_frac"] = cdr3
        zeros["all_cdr_frac"] = all_cdr
        zeros["all_fr_frac"] = all_fr
        pep = _chain_com(pdb, 2)
        mhc = _chain_com(pdb, 3)
        zeros["dist_peptide"] = float(np.linalg.norm(com.astype(np.float64) - pep))
        zeros["dist_mhc"] = float(np.linalg.norm(com.astype(np.float64) - mhc))
        if np.any(cdr3_com):
            zeros["dist_cdr3"] = float(np.linalg.norm(com.astype(np.float64) - cdr3_com))
    return zeros


def _combine(op: str, a: float, b: float) -> float:
    if op == "diff":
        return float(a - b)
    if op == "product":
        return float(a * b)
    denom = b if abs(b) > 1e-8 else 1e-8
    return float(a / denom)


def spot_feature_vector(g: Genotype, asset: MasifAsset, row: pd.Series) -> np.ndarray:
    if not g.encoders.surface.spots.enabled:
        return np.zeros(1, dtype=np.float64)
    core = core_spot_features(g, asset, row)
    parts = [core[name] for name in SPOT_CORE]
    for item in g.encoders.surface.spots.derived[:8]:
        parts.append(_combine(item.op, core.get(item.a, 0.0), core.get(item.b, 0.0)))
    return np.asarray(parts, dtype=np.float64)
