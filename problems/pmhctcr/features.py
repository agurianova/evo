"""Genotype-conditioned features. Sequence / MaSIF / PDB / interaction all enter X."""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from problems.pmhctcr.assets import (
        ESM2_HIDDEN,
        MasifAsset,
        load_esm,
        load_masif,
        load_pdb,
    )
    from problems.pmhctcr.genotype import (
        Genotype,
        sequence_on,
        structure_on,
        surface_on,
        uses_learned_sequence,
    )
    from problems.pmhctcr.regions import (
        chain_region_from_row,
        region_indices,
        vj_onehot_from_row,
    )
    from problems.pmhctcr.spots import spot_feature_vector
except ImportError:
    from assets import ESM2_HIDDEN, MasifAsset, load_esm, load_masif, load_pdb
    from genotype import (
        Genotype,
        sequence_on,
        structure_on,
        surface_on,
        uses_learned_sequence,
    )
    from regions import chain_region_from_row, region_indices, vj_onehot_from_row
    from spots import spot_feature_vector

_AA = "ACDEFGHIKLMNPQRSTVWY"


def _aa_frac(seq: object) -> np.ndarray:
    text = "" if seq is None or (isinstance(seq, float) and np.isnan(seq)) else str(seq)
    counts = np.zeros(len(_AA), dtype=np.float64)
    for ch in text:
        i = _AA.find(ch)
        if i >= 0:
            counts[i] += 1
    n = counts.sum()
    if n > 0:
        counts /= n
    return counts


def _seq_text(df: pd.DataFrame, col: str, i: int) -> str:
    if col not in df.columns:
        return ""
    val = df.iloc[i][col]
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    return str(val)


def _tcr_text(g: Genotype, row: pd.Series, chain: str) -> str:
    return chain_region_from_row(row, chain, g.encoders.sequence.region)


def _mhc_text(g: Genotype, df: pd.DataFrame, i: int) -> str:
    text = _seq_text(df, "mhca_seq", i)
    if g.encoders.sequence.region == "groove_a1a2" and text:
        # Mature HLA A1/A2 ≈ after the ~24-aa leader through residue ~180.
        return text[24:204] if len(text) > 40 else text
    return text


_ESM_PATH_COL = {
    "peptide": "esm_peptide_path",
    "mhc": "esm_mhca_path",
    "tcr_alpha": "esm_tcra_path",
    "tcr_beta": "esm_tcrb_path",
}


def _pool_esm(asset, indices: np.ndarray, pooling: str) -> np.ndarray:
    if not asset.ok:
        return np.zeros(ESM2_HIDDEN, dtype=np.float64)
    res = asset.residue
    if indices.size == 0:
        vec = asset.pooled
    else:
        idx = indices[(indices >= 0) & (indices < res.shape[0])]
        if idx.size == 0:
            vec = asset.pooled
        elif pooling == "attention":
            sl = res[idx]
            scores = np.linalg.norm(sl, axis=1)
            scores = scores - float(scores.max())
            w = np.exp(scores)
            w = w / (w.sum() + 1e-9)
            vec = w @ sl
        elif idx.size == res.shape[0]:
            vec = asset.pooled
        else:
            vec = res[idx].mean(axis=0)
    out = np.asarray(vec, dtype=np.float64).reshape(-1)
    if out.size < ESM2_HIDDEN:
        out = np.pad(out, (0, ESM2_HIDDEN - out.size))
    return out[:ESM2_HIDDEN]


def _esm_vec(g: Genotype, df: pd.DataFrame, i: int, source: str) -> np.ndarray:
    col = _ESM_PATH_COL[source]
    path = str(df.iloc[i][col]) if col in df.columns else ""
    asset = load_esm(path)
    enc = g.encoders.sequence
    if source == "peptide":
        seq = _seq_text(df, "epitope_seq", i)
        idx = region_indices(seq, "full")
    elif source == "mhc":
        seq = _seq_text(df, "mhca_seq", i)
        region = "groove_a1a2" if enc.region == "groove_a1a2" else "full"
        idx = region_indices(seq, region)
    else:
        prefix = "tcra" if source == "tcr_alpha" else "tcrb"
        seq = _seq_text(df, f"{prefix}_seq", i)
        idx = region_indices(
            seq,
            enc.region,
            cdr3=_seq_text(df, f"{prefix}_seq_cdr3", i),
            vgene=_seq_text(df, f"{prefix}_vgene", i),
        )
    return _pool_esm(asset, idx, enc.pooling)


def esm_channel_vecs(g: Genotype, df: pd.DataFrame, i: int) -> dict[str, np.ndarray]:
    """Frozen ESM-2 8M vectors for peptide / MHC / TCR channels."""
    zero = np.zeros(ESM2_HIDDEN, dtype=np.float64)
    s = g.inputs.sequence
    return {
        "esm_pep": _esm_vec(g, df, i, "peptide") if s.peptide else zero,
        "esm_mhc": _esm_vec(g, df, i, "mhc") if s.mhc else zero,
        "esm_tcra": _esm_vec(g, df, i, "tcr_alpha") if s.tcr_alpha else zero,
        "esm_tcrb": _esm_vec(g, df, i, "tcr_beta") if s.tcr_beta else zero,
    }


def _seq_channel_width(g: Genotype) -> int:
    """Width of one sequence channel in the tabular block (excludes V/J)."""
    if uses_learned_sequence(g):
        return 0
    if g.encoders.sequence.arch == "protein_lm":
        return int(ESM2_HIDDEN)
    return 20


def _seq_block(g: Genotype, df: pd.DataFrame, i: int, mask: bool) -> np.ndarray:
    parts: list[np.ndarray] = []
    s = g.inputs.sequence
    enc = g.encoders.sequence
    row = df.iloc[i]
    cols: list[tuple[str, str]] = []
    if s.peptide:
        cols.append(("peptide", _seq_text(df, "epitope_seq", i)))
    if s.mhc:
        cols.append(("mhc", _mhc_text(g, df, i)))
    if s.tcr_alpha:
        cols.append(("tcr_alpha", _tcr_text(g, row, "a")))
    if s.tcr_beta:
        cols.append(("tcr_beta", _tcr_text(g, row, "b")))
    rng = np.random.default_rng(g.seed + i) if mask else None
    p_mask = float(g.training.augmentation.seq_mask_p) if mask else 0.0
    learned = uses_learned_sequence(g)
    for source, text in cols:
        if learned:
            continue
        if rng is not None and p_mask > 0 and rng.random() < p_mask:
            if enc.arch == "protein_lm":
                parts.append(np.zeros(ESM2_HIDDEN, dtype=np.float64))
                continue
            text = ""
        if enc.arch == "protein_lm":
            parts.append(_esm_vec(g, df, i, source))
            continue
        parts.append(_aa_frac(text))
    if s.tcr_alpha or s.tcr_beta:
        parts.append(
            vj_onehot_from_row(row, alpha=bool(s.tcr_alpha), beta=bool(s.tcr_beta))
        )
    if not parts:
        return np.zeros(1, dtype=np.float64)
    return np.concatenate(parts)


def _pair_mask(tcr_xyz: np.ndarray, pmhc_xyz: np.ndarray, radius: float) -> np.ndarray:
    d2 = ((tcr_xyz[:, None, :] - pmhc_xyz[None, :, :]) ** 2).sum(axis=-1)
    return d2 <= (radius * radius)


def _knn_mask(tcr_desc: np.ndarray, pmhc_desc: np.ndarray, k: int = 8) -> np.ndarray:
    d2 = ((tcr_desc[:, None, :] - pmhc_desc[None, :, :]) ** 2).sum(axis=-1)
    k = min(k, pmhc_desc.shape[0])
    idx = np.argpartition(d2, kth=k - 1, axis=1)[:, :k]
    mask = np.zeros_like(d2, dtype=bool)
    rows = np.arange(tcr_desc.shape[0])[:, None]
    mask[rows, idx] = True
    return mask


def _safe_norm(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.clip(n, 1e-8, None)


def masif_metrics(g: Genotype, asset: MasifAsset) -> np.ndarray:
    """Scalar patch stats between TCR-direct and pMHC-flipped descriptors."""
    su = g.encoders.surface
    want = list(su.metrics) or ["cosine"]
    out = []
    use_tcr = g.inputs.masif.tcr_direct and asset.ok_tcr
    use_pmhc = g.inputs.masif.pmhc_flipped and asset.ok_pmhc
    if not (use_tcr and use_pmhc):
        return np.zeros(len(want), dtype=np.float64)
    tcr = asset.tcr_desc
    pmhc = asset.pmhc_desc
    if su.patch_boundary == "nn_learned":
        mask = _knn_mask(tcr, pmhc, k=8)
    else:
        mask = _pair_mask(asset.tcr_xyz, asset.pmhc_xyz, float(su.patch_radius_A))
    if not mask.any():
        mask = np.ones((tcr.shape[0], pmhc.shape[0]), dtype=bool)
    tcr_n = _safe_norm(tcr)
    pmhc_n = _safe_norm(pmhc)
    cosine = tcr_n @ pmhc_n.T
    dot = tcr @ pmhc.T
    l2 = np.sqrt(
        np.clip(
            (tcr**2).sum(axis=1, keepdims=True)
            + (pmhc**2).sum(axis=1)[None, :]
            - 2.0 * dot,
            0.0,
            None,
        )
    )
    valid_cos = cosine[mask]
    valid_dot = dot[mask]
    valid_l2 = l2[mask]
    topk = int(min(su.topk, valid_cos.size))
    for name in want:
        if name == "cosine":
            out.append(float(valid_cos.mean()) if valid_cos.size else 0.0)
        elif name == "dot":
            out.append(float(valid_dot.mean()) if valid_dot.size else 0.0)
        elif name == "l2":
            out.append(float(valid_l2.mean()) if valid_l2.size else 0.0)
        elif name == "max_sim":
            out.append(float(valid_cos.max()) if valid_cos.size else 0.0)
        elif name == "mean_topk":
            if valid_cos.size:
                top = np.partition(valid_cos, -topk)[-topk:]
                out.append(float(top.mean()))
            else:
                out.append(0.0)
        elif name == "count_above_thr":
            if valid_cos.size:
                out.append(float((valid_cos >= su.threshold).mean()))
            else:
                out.append(0.0)
        else:
            out.append(0.0)
    return np.asarray(out, dtype=np.float64)


def _masif_block(g: Genotype, df: pd.DataFrame, i: int) -> np.ndarray:
    tcr_path = (
        str(df.iloc[i]["masif_tcr_path"]) if "masif_tcr_path" in df.columns else ""
    )
    pmhc_path = (
        str(df.iloc[i]["masif_pmhc_path"]) if "masif_pmhc_path" in df.columns else ""
    )
    asset = load_masif(tcr_path, pmhc_path)
    parts: list[np.ndarray] = []
    if g.inputs.masif.tcr_direct:
        parts.append(
            asset.tcr_pooled.astype(np.float64) if asset.ok_tcr else np.zeros(80)
        )
    if g.inputs.masif.pmhc_flipped:
        parts.append(
            asset.pmhc_pooled.astype(np.float64) if asset.ok_pmhc else np.zeros(80)
        )
    parts.append(masif_metrics(g, asset))
    if g.encoders.surface.spots.enabled:
        parts.append(spot_feature_vector(g, asset, df.iloc[i]))
    return np.concatenate(parts) if parts else np.zeros(1)


def _neighbors(xyz: np.ndarray, k: int, radius: float, kind: str) -> list[np.ndarray]:
    n = xyz.shape[0]
    d = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=-1)
    np.fill_diagonal(d, np.inf)
    neigh: list[np.ndarray] = []
    if kind == "knn":
        kk = min(max(int(k), 1), n - 1)
        idx = np.argpartition(d, kk, axis=1)[:, :kk]
        for i in range(n):
            neigh.append(idx[i])
    else:
        for i in range(n):
            hit = np.where(d[i] <= radius)[0]
            neigh.append(hit if hit.size else np.array([i], dtype=int))
    return neigh


def _pdb_block(g: Genotype, df: pd.DataFrame, i: int, *, train: bool) -> np.ndarray:
    """One-step residue graph on Cα atoms.

    Node feature = 21-way AA one-hot. Edges from knn / radius. Message is a
    weighted mean of neighbour AA (no learned matrices):

    * ``mpnn`` — uniform 1/|N(v)|
    * ``gat``  — closer Cα get larger weight: softmax via ``exp(-distance)``
    * ``egnn`` — ``1/distance``, then mix 50/50 with self AA
    * ``se3_transformer`` — Cα distance kernel ``exp(-0.5 * distance)``, same 50/50 self mix (not SE(3))

    Graph readout is mean, or degree-weighted mean if pooling=attention.
    Extra scalars: chain-COM distances, interface fraction, n_CA.
    """
    path = str(df.iloc[i]["pdb_path"]) if "pdb_path" in df.columns else ""
    asset = load_pdb(path)
    if not asset.ok:
        return np.zeros(29, dtype=np.float64)
    st = g.encoders.structure
    xyz, chain, aa = asset.xyz, asset.chain, asset.aa
    n = xyz.shape[0]
    d_all = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=-1)
    inter = (chain[:, None] != chain[None, :]) & np.isfinite(d_all)
    contact_r = float(st.edges.radius_A or 8.0)
    interface_node = (inter & (d_all <= 8.0)).sum(axis=1) > 0
    if st.scope == "interface" and interface_node.any():
        keep = interface_node
        xyz, chain, aa = xyz[keep], chain[keep], aa[keep]
        n = xyz.shape[0]
    neigh = _neighbors(xyz, st.edges.k, contact_r, st.edges.type)
    drop_p = float(g.training.augmentation.structure_edge_dropout_p) if train else 0.0
    rng = np.random.default_rng(g.seed + 13 * i) if drop_p > 0 else None
    aa_oh = np.eye(21, dtype=np.float64)[np.clip(aa, 0, 20)]
    pooled = np.zeros((n, 21), dtype=np.float64)
    degrees = np.zeros(n, dtype=np.float64)
    for v in range(n):
        idx = neigh[v]
        if rng is not None and idx.size:
            keep = rng.random(idx.size) >= drop_p
            idx = idx[keep] if keep.any() else idx[:1]
        if idx.size == 0:
            pooled[v] = aa_oh[v]
            continue
        rel = xyz[idx] - xyz[v]
        dist = np.linalg.norm(rel, axis=1) + 1e-6
        if st.arch == "gat":
            w = np.exp(-dist)
            w = w / w.sum()
        elif st.arch == "egnn":
            w = 1.0 / dist
            w = w / w.sum()
        elif st.arch == "se3_transformer":
            # Two-hop proxy: mix 1-hop with a wider mean.
            w = np.exp(-0.5 * dist)
            w = w / w.sum()
        else:
            w = np.full(idx.size, 1.0 / idx.size)
        pooled[v] = w @ aa_oh[idx]
        if st.arch in {"egnn", "se3_transformer"}:
            pooled[v] = 0.5 * pooled[v] + 0.5 * aa_oh[v]
        degrees[v] = float(idx.size)
    if st.pooling == "attention" and degrees.sum() > 0:
        w = degrees / degrees.sum()
        graph_pool = w @ pooled
    else:
        graph_pool = pooled.mean(axis=0)
    com = []
    for c in range(4):
        m = chain == c
        com.append(xyz[m].mean(axis=0) if m.any() else np.zeros(3, np.float32))
    com = np.stack(com)
    pair_d = []
    for a, b in ((0, 2), (1, 2), (0, 3), (1, 3), (2, 3), (0, 1)):
        pair_d.append(float(np.linalg.norm(com[a] - com[b])))
    n_iface = float(interface_node.mean()) if interface_node.size else 0.0
    n_ca = float(min(n, 4000) / 4000.0)
    # Packed PDB vector (29):
    #   [0:21]  spatial AA composition (graph readout)
    #   [21:27] Cα-COM distances A-C, B-C, A-D, B-D, C-D, A-B
    #           (A/B=TCR, C=peptide, D=MHC)
    #   [27]    fraction of Cα with an 8Å inter-chain neighbour
    #   [28]    n_Cα / 4000
    return np.concatenate(
        [
            graph_pool,
            np.asarray(pair_d, dtype=np.float64),
            np.array([n_iface, n_ca], dtype=np.float64),
        ]
    )


def _align_mul(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    n = min(a.size, b.size)
    if n == 0:
        return np.zeros(1)
    return a[:n] * b[:n]


def _align_diff(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    n = min(a.size, b.size)
    if n == 0:
        return np.zeros(1)
    return np.abs(a[:n] - b[:n])


def _cross_attn(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    n = min(a.size, b.size)
    if n == 0:
        return np.zeros(1)
    score = float(np.dot(a[:n], b[:n]) / (n**0.5))
    w = 1.0 / (1.0 + np.exp(-score))
    return w * a[:n] + (1.0 - w) * b[:n]


def _pair_op(g: Genotype, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    method = g.interaction.method or "product"
    if method == "abs_diff":
        return _align_diff(a, b)
    if method == "bilinear":
        n = min(a.size, b.size)
        return np.array([float(np.dot(a[:n], b[:n]))]) if n else np.zeros(1)
    if method == "cross_attention":
        return _cross_attn(a, b)
    return _align_mul(a, b)


def _molecule_vecs(
    g: Genotype, seq: np.ndarray, masif: np.ndarray, pdb: np.ndarray
) -> dict[str, np.ndarray]:
    """Per-molecule views for numpy interaction pairs. Sequence slices exclude V/J."""
    vecs = {"peptide": np.zeros(1), "mhc": np.zeros(1), "tcr": np.zeros(1)}
    if sequence_on(g) and seq.size > 1:
        s = g.inputs.sequence
        width = _seq_channel_width(g)
        offset = 0

        def _take() -> np.ndarray:
            nonlocal offset
            if width <= 0 or offset + width > seq.size:
                return np.zeros(1)
            sl = seq[offset : offset + width]
            offset += width
            return sl

        if s.peptide:
            vecs["peptide"] = _take()
        if s.mhc:
            vecs["mhc"] = _take()
        tcr_parts = []
        if s.tcr_alpha:
            tcr_parts.append(_take())
        if s.tcr_beta:
            tcr_parts.append(_take())
        if tcr_parts:
            vecs["tcr"] = np.concatenate(tcr_parts)
    if surface_on(g) and masif.size > 1:
        if g.inputs.masif.tcr_direct:
            vecs["tcr"] = np.concatenate([vecs["tcr"], masif[:80]])
        if g.inputs.masif.pmhc_flipped:
            # Joint pMHC surface; usable as peptide and MHC evidence.
            chunk = masif[80:160] if g.inputs.masif.tcr_direct else masif[:80]
            vecs["peptide"] = np.concatenate([vecs["peptide"], chunk])
            vecs["mhc"] = np.concatenate([vecs["mhc"], chunk])
    if structure_on(g) and pdb.size > 21:
        vecs["tcr"] = np.concatenate([vecs["tcr"], pdb[:21]])
        vecs["peptide"] = np.concatenate([vecs["peptide"], pdb[:21]])
        vecs["mhc"] = np.concatenate([vecs["mhc"], pdb[:21]])
    return vecs


def _interaction_block(
    g: Genotype, seq: np.ndarray, masif: np.ndarray, pdb: np.ndarray
) -> np.ndarray:
    if not g.interaction.pairs:
        return np.zeros(1, dtype=np.float64)
    mol = _molecule_vecs(g, seq, masif, pdb)
    chunks: list[np.ndarray] = []
    for pair in g.interaction.pairs:
        if pair == "peptide_tcr":
            feat = _pair_op(g, mol["peptide"], mol["tcr"])
        elif pair == "peptide_mhc":
            feat = _pair_op(g, mol["peptide"], mol["mhc"])
        elif pair == "mhc_tcr":
            feat = _pair_op(g, mol["mhc"], mol["tcr"])
        else:
            feat = _pair_op(g, mol["peptide"], _pair_op(g, mol["mhc"], mol["tcr"]))
        chunks.append(feat)
    fused = chunks[0]
    fusion = g.interaction.fusion or "concat"
    for extra in chunks[1:]:
        if fusion == "gated_sum":
            n = min(fused.size, extra.size)
            gate = 1.0 / (1.0 + np.exp(-(fused[:n] + extra[:n]).mean()))
            fused = gate * fused[:n] + (1.0 - gate) * extra[:n]
        elif fusion == "cross_attention":
            fused = _cross_attn(fused, extra)
        else:
            fused = np.concatenate([fused, extra])
    return fused


def _row_features(
    g: Genotype, df: pd.DataFrame, i: int, *, train: bool
) -> dict[str, np.ndarray]:
    # Features follow input flags, not model.type. Type only chooses learned
    # torch modules and extra fusion channels.
    seq = _seq_block(g, df, i, mask=train) if sequence_on(g) else np.zeros(1)
    surf = _masif_block(g, df, i) if surface_on(g) else np.zeros(1)
    pdb = _pdb_block(g, df, i, train=train) if structure_on(g) else np.zeros(1)
    inter = _interaction_block(g, seq, surf, pdb)
    return {"seq": seq, "surf": surf, "pdb": pdb, "inter": inter}


def _fuse_model(g: Genotype, blocks: dict[str, np.ndarray]) -> np.ndarray:
    t = g.model.type
    seq, surf, pdb, inter = (
        blocks["seq"],
        blocks["surf"],
        blocks["pdb"],
        blocks["inter"],
    )
    chunks: list[np.ndarray] = []
    if sequence_on(g):
        chunks.append(seq)
    if surface_on(g):
        chunks.append(surf)
    if structure_on(g):
        chunks.append(pdb)
    chunks.append(inter)
    parts = [p for p in (seq, surf, pdb) if p.size > 1]
    if t == "multimodal_gated" and len(parts) >= 2:
        n = min(len(p) for p in parts)
        gate = 1.0 / (1.0 + np.exp(-np.stack([p[:n] for p in parts]).mean(axis=0)))
        mixed = gate * parts[0][:n] + (1.0 - gate) * parts[1][:n]
        chunks.append(mixed)
    return np.concatenate(chunks) if chunks else np.zeros(1)


def build_feature_matrix(
    g: Genotype,
    df: pd.DataFrame,
    *,
    train: bool,
) -> np.ndarray:
    if len(df) == 0:
        return np.zeros((0, 1), dtype=np.float64)
    rows = [
        _fuse_model(g, _row_features(g, df, i, train=train)) for i in range(len(df))
    ]
    width = max(r.size for r in rows)
    out = np.zeros((len(rows), width), dtype=np.float64)
    for i, r in enumerate(rows):
        out[i, : r.size] = r
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


def hard_negative_index(
    df: pd.DataFrame, g: Genotype, rng: np.random.Generator
) -> np.ndarray:
    """Keep all train positives; downsample negatives, preferring same pMHC."""
    y = df["label"].to_numpy(dtype=int)
    pos = np.where(y == 1)[0]
    neg = np.where(y == 0)[0]
    if g.training.sampling != "hard_negative" or pos.size == 0 or neg.size == 0:
        return np.arange(len(df))
    ratio = float(g.training.hard_negative_ratio)
    n_keep = max(int(neg.size * max(1.0 - ratio, 0.05)), pos.size)
    n_keep = min(n_keep, neg.size)
    same: list[int] = []
    if "mhc_epitope_id" in df.columns:
        pos_pmhc = set(df.iloc[pos]["mhc_epitope_id"].tolist())
        for j in neg:
            if df.iloc[j]["mhc_epitope_id"] in pos_pmhc:
                same.append(int(j))
    same_arr = np.array(same, dtype=int) if same else np.array([], dtype=int)
    n_hard = min(len(same_arr), max(int(n_keep * ratio), 0))
    picked = []
    if n_hard:
        picked.append(rng.choice(same_arr, size=n_hard, replace=False))
    remain = np.setdiff1d(neg, same_arr, assume_unique=False)
    n_easy = n_keep - n_hard
    if n_easy > 0 and remain.size:
        picked.append(rng.choice(remain, size=min(n_easy, remain.size), replace=False))
    elif n_easy > 0:
        leftover = np.setdiff1d(
            neg, np.concatenate(picked) if picked else np.array([], dtype=int)
        )
        if leftover.size:
            picked.append(
                rng.choice(leftover, size=min(n_easy, leftover.size), replace=False)
            )
    neg_keep = np.concatenate(picked) if picked else neg[:n_keep]
    return np.sort(np.concatenate([pos, neg_keep]))
