"""Learned sequence / GAT / cross-attention modules trained with the JSON head.

Frozen numpy blocks (AA fractions, pooled MaSIF, Cα readout) still feed the
MLP. This module adds trainable encoders when the genotype asks for them, and
always trains the MLP head in PyTorch so dropout / residual / optimizer /
scheduler / BCE-focal-contrastive actually move. The primary training
signal is within-pMHC ranking: each binder is compared to non-binders of
the same mhc_epitope_id so negatives cannot swamp positives globally.
"""

from __future__ import annotations

import os
import random
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

# Must be set before the first cuBLAS handle; needed for deterministic GEMM.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

try:
    from problems.pmhctcr.assets import ESM2_HIDDEN, load_masif, load_pdb
    from problems.pmhctcr.features import build_feature_matrix, hard_negative_index
    from problems.pmhctcr.genotype import (
        Genotype,
        surface_on,
        uses_learned_cross,
        uses_learned_gat,
        uses_learned_sequence,
        uses_modality_cross,
        uses_pair_cross,
        uses_patch_cross,
        uses_siamese,
    )
    from problems.pmhctcr.regions import (
        TRAV_ALLELES,
        TRBV_ALLELES,
        chain_region_from_row,
        gene_index,
    )
except ImportError:
    from assets import ESM2_HIDDEN, load_masif, load_pdb
    from features import build_feature_matrix, hard_negative_index
    from genotype import (
        Genotype,
        surface_on,
        uses_learned_cross,
        uses_learned_gat,
        uses_learned_sequence,
        uses_modality_cross,
        uses_pair_cross,
        uses_patch_cross,
        uses_siamese,
    )
    from regions import TRAV_ALLELES, TRBV_ALLELES, chain_region_from_row, gene_index

_AA = "ACDEFGHIKLMNPQRSTVWY"
_AA_TO_ID = {c: i + 1 for i, c in enumerate(_AA)}  # 0 = pad
_MAX_PEP = 16
_MAX_MHC = 48
_MAX_TCR = 64
_MAX_PDB = 96
_N_PATCH = 64
_EPOCHS = 8
_PDB_EPOCHS = 5


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def configure_torch_determinism(seed: int) -> None:
    """Pin Python / NumPy / Torch / cuDNN so the same genotype retrains identically."""
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(int(seed))
    np.random.seed(int(seed))
    torch.manual_seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    if hasattr(torch.backends, "cuda") and hasattr(torch.backends.cuda, "matmul"):
        torch.backends.cuda.matmul.allow_tf32 = False
    if hasattr(torch.backends.cudnn, "allow_tf32"):
        torch.backends.cudnn.allow_tf32 = False
    # Flash / mem-efficient SDPA is nondeterministic on CUDA; math SDPA is not.
    if torch.cuda.is_available() and hasattr(torch.backends.cuda, "enable_flash_sdp"):
        torch.backends.cuda.enable_flash_sdp(False)
        torch.backends.cuda.enable_mem_efficient_sdp(False)
        torch.backends.cuda.enable_math_sdp(True)
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except TypeError:
        try:
            torch.use_deterministic_algorithms(True)
        except RuntimeError:
            pass


def use_torch_head(g: Genotype) -> bool:
    if g.model.num_layers >= 2:
        return True
    if g.model.type != "mlp_features":
        return True
    if uses_learned_cross(g) or uses_learned_gat(g) or uses_learned_sequence(g):
        return True
    if g.training.scheduler != "none":
        return True
    if g.training.optimizer not in {"adamw", "adam"}:
        return True
    return False


def _encode_aa(text: str, max_len: int) -> np.ndarray:
    ids = np.zeros(max_len, dtype=np.int64)
    n = 0
    for ch in text:
        idx = _AA_TO_ID.get(ch)
        if idx is None:
            continue
        ids[n] = idx
        n += 1
        if n >= max_len:
            break
    return ids


def _seq_max(g: Genotype) -> tuple[int, int, int]:
    region = g.encoders.sequence.region
    tcr = (
        20
        if region in {"cdr3"}
        else (40 if region in {"cdr1", "cdr2", "all_cdr"} else _MAX_TCR)
    )
    mhc = 32 if region == "groove_a1a2" else _MAX_MHC
    return _MAX_PEP, mhc, tcr


class ResidualMLP(nn.Module):
    def __init__(
        self, in_dim: int, hidden: int, n_layers: int, dropout: float, residual: bool
    ):
        super().__init__()
        self.residual = residual
        n_hidden = max(int(n_layers) - 1, 1)
        layers: list[nn.Module] = []
        d = in_dim
        for _ in range(n_hidden):
            layers.append(nn.Linear(d, hidden))
            d = hidden
        self.blocks = nn.ModuleList(layers)
        self.drop = nn.Dropout(dropout)
        self.out = nn.Linear(d, 1)
        self.skip = nn.Linear(in_dim, hidden) if residual and in_dim != hidden else None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = x
        for i, lin in enumerate(self.blocks):
            z = self.drop(F.relu(lin(h)))
            if self.residual:
                if i == 0 and self.skip is not None:
                    h = z + self.skip(x)
                elif z.shape == h.shape:
                    h = z + h
                else:
                    h = z
            else:
                h = z
        return self.out(h).squeeze(-1)


class SeqEncoder(nn.Module):
    def __init__(self, g: Genotype, out_dim: int):
        super().__init__()
        h = int(g.encoders.sequence.hidden_dim)
        n_layers = max(1, min(int(g.model.num_layers), 3))
        heads = int(g.model.num_heads)
        if h % heads != 0:
            heads = 1
        self.arch = g.encoders.sequence.arch
        self.pooling = g.encoders.sequence.pooling
        self.emb = nn.Embedding(21, h, padding_idx=0)
        self.drop = nn.Dropout(g.model.dropout)
        if self.arch == "cnn":
            k = 3
            convs = []
            d = h
            for _ in range(n_layers):
                convs.append(nn.Conv1d(d, h, kernel_size=k, padding=k // 2))
                d = h
            self.convs = nn.ModuleList(convs)
            self.transformer = None
        else:
            layer = nn.TransformerEncoderLayer(
                d_model=h,
                nhead=heads,
                dim_feedforward=max(4 * h, 128),
                dropout=g.model.dropout,
                batch_first=True,
                activation="gelu",
            )
            self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
            self.convs = None
        self.attn_pool = nn.Linear(h, 1)
        self.proj = nn.Linear(h, out_dim)
        self.residual = g.model.residual

    def forward(self, ids: torch.Tensor) -> torch.Tensor:
        mask = ids.eq(0)
        h = self.drop(self.emb(ids))
        if self.convs is not None:
            x = h.transpose(1, 2)
            for conv in self.convs:
                y = F.relu(conv(x))
                x = x + y if self.residual and x.shape == y.shape else y
            h = x.transpose(1, 2)
        else:
            h = self.transformer(h, src_key_padding_mask=mask)
        weights = (~mask).float().unsqueeze(-1)
        if self.pooling == "attention":
            scores = self.attn_pool(h).squeeze(-1).masked_fill(mask, -1e9)
            w = torch.softmax(scores, dim=1).unsqueeze(-1)
            pooled = (h * w).sum(dim=1)
        else:
            pooled = (h * weights).sum(dim=1) / weights.sum(dim=1).clamp(min=1.0)
        return self.proj(pooled)


class GATEncoder(nn.Module):
    """Learned GAT on a dense Cα neighbourhood (subsampled)."""

    def __init__(self, g: Genotype, out_dim: int):
        super().__init__()
        h = int(g.encoders.structure.hidden_dim)
        n_layers = max(1, min(int(g.model.num_layers), 3))
        in_dim = 25  # 21 AA + 4 chain
        self.input = nn.Linear(in_dim, h)
        self.layers = nn.ModuleList([nn.Linear(h, h) for _ in range(n_layers)])
        self.att = nn.Linear(2 * h + 1, 1)
        self.drop = nn.Dropout(g.model.dropout)
        self.residual = g.model.residual
        self.attn_pool = nn.Linear(h, 1)
        self.pooling = g.encoders.structure.pooling
        self.proj = nn.Linear(h, out_dim)
        self.arch = g.encoders.structure.arch

    def forward(
        self,
        nodes: torch.Tensor,
        dist: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        # nodes: B,N,F  dist: B,N,N  mask: B,N (True = real node)
        h = F.relu(self.input(nodes))
        adj = mask.unsqueeze(1) & mask.unsqueeze(2)
        eye = torch.eye(nodes.size(1), device=nodes.device, dtype=torch.bool)
        adj = adj & ~eye.unsqueeze(0)
        for lin in self.layers:
            b, n, d = h.shape
            if self.arch == "mpnn":
                w = adj.float()
                w = w / w.sum(dim=-1, keepdim=True).clamp(min=1.0)
            elif self.arch in {"egnn", "se3_transformer"}:
                if self.arch == "se3_transformer":
                    inv = torch.exp(-0.5 * dist)
                else:
                    inv = dist.clamp(min=1e-4).reciprocal()
                w = inv.masked_fill(~adj, 0.0)
                w = w / w.sum(dim=-1, keepdim=True).clamp(min=1e-6)
            else:
                hi = h.unsqueeze(2).expand(b, n, n, d)
                hj = h.unsqueeze(1).expand(b, n, n, d)
                e = torch.cat([hi, hj, dist.unsqueeze(-1)], dim=-1)
                logits = self.att(e).squeeze(-1)
                logits = logits.masked_fill(~adj, -1e9)
                w = torch.softmax(logits, dim=-1)
                w = torch.nan_to_num(w, nan=0.0)
            msg = torch.matmul(w, h)
            y = self.drop(F.relu(lin(msg)))
            h = h + y if self.residual else y
        if self.pooling == "attention":
            scores = self.attn_pool(h).squeeze(-1).masked_fill(~mask, -1e9)
            a = torch.softmax(scores, dim=1).unsqueeze(-1)
            pooled = (h * a).sum(dim=1)
        else:
            m = mask.float().unsqueeze(-1)
            pooled = (h * m).sum(dim=1) / m.sum(dim=1).clamp(min=1.0)
        return self.proj(pooled)


class SiameseTower(nn.Module):
    """Shared MLP on pooled 80-d MaSIF (TCR vs pMHC)."""

    def __init__(self, hidden: int, dropout: float):
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(80, hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, hidden),
        )

    def forward(self, tcr: torch.Tensor, pmhc: torch.Tensor) -> torch.Tensor:
        a = self.shared(tcr)
        b = self.shared(pmhc)
        prod = a * b
        diff = (a - b).abs()
        cos = F.cosine_similarity(a, b, dim=-1, eps=1e-8).unsqueeze(-1)
        return torch.cat([prod, diff, cos], dim=-1)


class PmhctcrNet(nn.Module):
    def __init__(self, g: Genotype, tab_dim: int):
        super().__init__()
        self.g = g
        h = int(g.model.hidden_dim)
        pieces = tab_dim
        self.seq_enc: SeqEncoder | None = None
        self.gat_enc: GATEncoder | None = None
        self.cross: nn.MultiheadAttention | None = None
        self.lm_proj: nn.Linear | None = None
        self.surf_proj: nn.Linear | None = None
        self.siamese: SiameseTower | None = None
        self._extra_cross = False
        self.use_genes = bool(g.inputs.sequence.tcr_alpha or g.inputs.sequence.tcr_beta)
        if self.use_genes:
            self.gene_a = nn.Embedding(len(TRAV_ALLELES) + 1, 16, padding_idx=0)
            self.gene_b = nn.Embedding(len(TRBV_ALLELES) + 1, 16, padding_idx=0)
            pieces += 32
        else:
            self.gene_a = None
            self.gene_b = None
        if uses_learned_sequence(g):
            self.seq_enc = SeqEncoder(g, h)
            pieces += h
        if uses_learned_gat(g):
            self.gat_enc = GATEncoder(g, h)
            pieces += h
        heads = int(g.model.num_heads)
        if h % heads != 0:
            heads = 1
        dh = h
        self._dh = dh
        need_mha = uses_pair_cross(g) or uses_modality_cross(g)
        if need_mha:
            self.cross = nn.MultiheadAttention(
                dh, heads, dropout=g.model.dropout, batch_first=True
            )
        if g.encoders.sequence.arch == "protein_lm" and need_mha:
            self.lm_proj = nn.Linear(ESM2_HIDDEN, dh)
            if not uses_learned_sequence(g):
                pieces += dh
        n_surf = int(g.inputs.masif.tcr_direct) + int(g.inputs.masif.pmhc_flipped)
        if uses_modality_cross(g) and surface_on(g) and n_surf:
            self.surf_proj = nn.Linear(80 * n_surf, dh)
            pieces += dh
        elif uses_modality_cross(g):
            pieces += dh
        if uses_siamese(g):
            self.siamese = SiameseTower(h, float(g.model.dropout))
            pieces += 2 * h + 1
        self.patch_proj = nn.Linear(80, dh) if uses_patch_cross(g) else None
        if self.patch_proj is not None:
            self.patch_attn = nn.MultiheadAttention(
                dh, heads, dropout=g.model.dropout, batch_first=True
            )
            pieces += dh
        else:
            self.patch_attn = None
        self.head = ResidualMLP(
            in_dim=max(pieces, 1),
            hidden=h,
            n_layers=int(g.model.num_layers),
            dropout=float(g.model.dropout),
            residual=bool(g.model.residual),
        )
        self._h = h

    def _token_vec(
        self, batch: dict[str, torch.Tensor], key: str, ids_key: str
    ) -> torch.Tensor | None:
        if self.seq_enc is not None:
            return self.seq_enc(batch[ids_key])
        if self.lm_proj is not None and key in batch:
            return self.lm_proj(batch[key])
        return None

    def _seq_pool(self, batch: dict[str, torch.Tensor]) -> torch.Tensor | None:
        g = self.g
        parts: list[torch.Tensor] = []
        tcr_h: list[torch.Tensor] = []
        if g.inputs.sequence.peptide:
            vec = self._token_vec(batch, "esm_pep", "pep")
            if vec is not None:
                parts.append(vec)
        if g.inputs.sequence.mhc:
            vec = self._token_vec(batch, "esm_mhc", "mhc")
            if vec is not None:
                parts.append(vec)
        if g.inputs.sequence.tcr_alpha:
            vec = self._token_vec(batch, "esm_tcra", "tcra")
            if vec is not None:
                tcr_h.append(vec)
        if g.inputs.sequence.tcr_beta:
            vec = self._token_vec(batch, "esm_tcrb", "tcrb")
            if vec is not None:
                tcr_h.append(vec)
        if uses_pair_cross(g) and parts and tcr_h:
            a = torch.stack(parts, dim=1).mean(dim=1)
            b = torch.stack(tcr_h, dim=1).mean(dim=1)
            if self.cross is not None:
                fused, _ = self.cross(a.unsqueeze(1), b.unsqueeze(1), b.unsqueeze(1))
                return fused.squeeze(1)
            return 0.5 * (a + b)
        vecs = parts + tcr_h
        if not vecs:
            return None
        return torch.stack(vecs, dim=1).mean(dim=1)

    def forward(self, batch: dict[str, Any]) -> tuple[torch.Tensor, torch.Tensor]:
        chunks: list[torch.Tensor] = [batch["tab"]]
        if self.gene_a is not None and self.gene_b is not None:
            chunks.append(self.gene_a(batch["trav"]))
            chunks.append(self.gene_b(batch["trbv"]))
        seq_h = self._seq_pool(batch)
        if seq_h is not None:
            chunks.append(seq_h)
        gat_h = None
        if self.gat_enc is not None:
            gat_h = self.gat_enc(batch["pdb_x"], batch["pdb_d"], batch["pdb_m"])
            chunks.append(gat_h)
        if self.patch_attn is not None and "tcr_patch" in batch:
            q = self.patch_proj(batch["tcr_patch"])
            kv = self.patch_proj(batch["pmhc_patch"])
            fused, _ = self.patch_attn(q, kv, kv)
            chunks.append(fused.mean(dim=1))
        if self.siamese is not None and "tcr_pool" in batch:
            chunks.append(self.siamese(batch["tcr_pool"], batch["pmhc_pool"]))
        if uses_modality_cross(self.g) and self.cross is not None:
            tokens: list[torch.Tensor] = []
            if seq_h is not None:
                tokens.append(seq_h)
            if gat_h is not None:
                tokens.append(gat_h)
            if self.surf_proj is not None and "masif_cat" in batch:
                tokens.append(self.surf_proj(batch["masif_cat"]))
            if len(tokens) >= 2:
                stacked = torch.stack(tokens, dim=1)
                fused, _ = self.cross(stacked, stacked, stacked)
                chunks.append(fused.mean(dim=1))
            elif tokens:
                chunks.append(tokens[0])
        x = torch.cat(chunks, dim=-1)
        logits = self.head(x)
        return logits, x


def _tokenize_row(
    g: Genotype, row: pd.Series, pep_n: int, mhc_n: int, tcr_n: int
) -> dict[str, np.ndarray]:
    region = g.encoders.sequence.region
    pep = (
        str(row["epitope_seq"])
        if "epitope_seq" in row and pd.notna(row["epitope_seq"])
        else ""
    )
    mhc = (
        str(row["mhca_seq"]) if "mhca_seq" in row and pd.notna(row["mhca_seq"]) else ""
    )
    if region == "groove_a1a2" and mhc:
        mhc = mhc[24:204] if len(mhc) > 40 else mhc
    tcra = chain_region_from_row(row, "a", region)
    tcrb = chain_region_from_row(row, "b", region)
    return {
        "pep": _encode_aa(pep, pep_n),
        "mhc": _encode_aa(mhc, mhc_n),
        "tcra": _encode_aa(tcra, tcr_n),
        "tcrb": _encode_aa(tcrb, tcr_n),
        "trav": np.int64(gene_index(row.get("tcra_vgene"), "trav")),
        "trbv": np.int64(gene_index(row.get("tcrb_vgene"), "trbv")),
    }


def _pdb_tensors(g: Genotype, path: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    asset = load_pdb(path)
    nmax = _MAX_PDB
    x = np.zeros((nmax, 25), dtype=np.float32)
    dist = np.zeros((nmax, nmax), dtype=np.float32)
    mask = np.zeros(nmax, dtype=bool)
    if not asset.ok:
        return x, dist, mask
    xyz, chain, aa = asset.xyz, asset.chain, asset.aa
    if g.encoders.structure.scope == "interface":
        d_all = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=-1)
        inter = (chain[:, None] != chain[None, :]) & np.isfinite(d_all)
        keep = (inter & (d_all <= 8.0)).sum(axis=1) > 0
        if keep.any():
            xyz, chain, aa = xyz[keep], chain[keep], aa[keep]
    n = xyz.shape[0]
    if n > nmax:
        idx = np.linspace(0, n - 1, nmax).astype(np.int64)
        xyz, chain, aa = xyz[idx], chain[idx], aa[idx]
        n = nmax
    aa_oh = np.eye(21, dtype=np.float32)[np.clip(aa, 0, 20)]
    ch_oh = np.eye(4, dtype=np.float32)[np.clip(chain, 0, 3)]
    x[:n] = np.concatenate([aa_oh, ch_oh], axis=1)
    d = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=-1)
    dist[:n, :n] = d
    mask[:n] = True
    return x, dist, mask


def _masif_pooled(tcr_path: str, pmhc_path: str) -> tuple[np.ndarray, np.ndarray]:
    asset = load_masif(tcr_path, pmhc_path)
    tcr = (
        asset.tcr_pooled.astype(np.float32)
        if asset.ok_tcr
        else np.zeros(80, dtype=np.float32)
    )
    pmhc = (
        asset.pmhc_pooled.astype(np.float32)
        if asset.ok_pmhc
        else np.zeros(80, dtype=np.float32)
    )
    return tcr, pmhc


def _masif_patches(tcr_path: str, pmhc_path: str) -> tuple[np.ndarray, np.ndarray]:
    asset = load_masif(tcr_path, pmhc_path)
    tcr = np.zeros((_N_PATCH, 80), dtype=np.float32)
    pmhc = np.zeros((_N_PATCH, 80), dtype=np.float32)
    if asset.ok_tcr:
        k = min(_N_PATCH, asset.tcr_desc.shape[0])
        tcr[:k] = asset.tcr_desc[:k]
    if asset.ok_pmhc:
        k = min(_N_PATCH, asset.pmhc_desc.shape[0])
        pmhc[:k] = asset.pmhc_desc[:k]
    return tcr, pmhc


def _stack_batch(
    g: Genotype, df: pd.DataFrame, tab: np.ndarray, device: torch.device
) -> dict[str, torch.Tensor]:
    pep_n, mhc_n, tcr_n = _seq_max(g)
    n = len(df)
    pep = np.zeros((n, pep_n), np.int64)
    mhc = np.zeros((n, mhc_n), np.int64)
    tcra = np.zeros((n, tcr_n), np.int64)
    tcrb = np.zeros((n, tcr_n), np.int64)
    trav = np.zeros(n, np.int64)
    trbv = np.zeros(n, np.int64)
    for i in range(n):
        tok = _tokenize_row(g, df.iloc[i], pep_n, mhc_n, tcr_n)
        pep[i] = tok["pep"]
        mhc[i] = tok["mhc"]
        tcra[i] = tok["tcra"]
        tcrb[i] = tok["tcrb"]
        trav[i] = tok["trav"]
        trbv[i] = tok["trbv"]
    out: dict[str, torch.Tensor] = {
        "tab": torch.as_tensor(tab, dtype=torch.float32, device=device),
        "pep": torch.as_tensor(pep, device=device),
        "mhc": torch.as_tensor(mhc, device=device),
        "tcra": torch.as_tensor(tcra, device=device),
        "tcrb": torch.as_tensor(tcrb, device=device),
        "trav": torch.as_tensor(trav, device=device),
        "trbv": torch.as_tensor(trbv, device=device),
    }
    if uses_learned_gat(g):
        xs, ds, ms = [], [], []
        for i in range(n):
            path = str(df.iloc[i]["pdb_path"]) if "pdb_path" in df.columns else ""
            x, d, m = _pdb_tensors(g, path)
            xs.append(x)
            ds.append(d)
            ms.append(m)
        out["pdb_x"] = torch.as_tensor(np.stack(xs), dtype=torch.float32, device=device)
        out["pdb_d"] = torch.as_tensor(np.stack(ds), dtype=torch.float32, device=device)
        out["pdb_m"] = torch.as_tensor(np.stack(ms), dtype=torch.bool, device=device)
    if uses_patch_cross(g):
        tps, pps = [], []
        for i in range(n):
            tcr_p = (
                str(df.iloc[i]["masif_tcr_path"])
                if "masif_tcr_path" in df.columns
                else ""
            )
            pmhc_p = (
                str(df.iloc[i]["masif_pmhc_path"])
                if "masif_pmhc_path" in df.columns
                else ""
            )
            t, p = _masif_patches(tcr_p, pmhc_p)
            tps.append(t)
            pps.append(p)
        out["tcr_patch"] = torch.as_tensor(
            np.stack(tps), dtype=torch.float32, device=device
        )
        out["pmhc_patch"] = torch.as_tensor(
            np.stack(pps), dtype=torch.float32, device=device
        )
    if uses_siamese(g) or (uses_modality_cross(g) and surface_on(g)):
        tcr_pools, pmhc_pools, cats = [], [], []
        for i in range(n):
            tcr_p = (
                str(df.iloc[i]["masif_tcr_path"])
                if "masif_tcr_path" in df.columns
                else ""
            )
            pmhc_p = (
                str(df.iloc[i]["masif_pmhc_path"])
                if "masif_pmhc_path" in df.columns
                else ""
            )
            t80, p80 = _masif_pooled(tcr_p, pmhc_p)
            tcr_pools.append(t80)
            pmhc_pools.append(p80)
            sides = []
            if g.inputs.masif.tcr_direct:
                sides.append(t80)
            if g.inputs.masif.pmhc_flipped:
                sides.append(p80)
            cats.append(
                np.concatenate(sides) if sides else np.zeros(80, dtype=np.float32)
            )
        if uses_siamese(g):
            out["tcr_pool"] = torch.as_tensor(
                np.stack(tcr_pools), dtype=torch.float32, device=device
            )
            out["pmhc_pool"] = torch.as_tensor(
                np.stack(pmhc_pools), dtype=torch.float32, device=device
            )
        if uses_modality_cross(g) and surface_on(g):
            out["masif_cat"] = torch.as_tensor(
                np.stack(cats), dtype=torch.float32, device=device
            )
    if g.encoders.sequence.arch == "protein_lm" and (
        uses_pair_cross(g) or uses_modality_cross(g)
    ):
        try:
            from problems.pmhctcr.features import esm_channel_vecs
        except ImportError:
            from features import esm_channel_vecs
        chans = [esm_channel_vecs(g, df, i) for i in range(n)]
        for key in ("esm_pep", "esm_mhc", "esm_tcra", "esm_tcrb"):
            out[key] = torch.as_tensor(
                np.stack([c[key] for c in chans]), dtype=torch.float32, device=device
            )
    if "mhc_epitope_id" in df.columns:
        codes, _ = pd.factorize(df["mhc_epitope_id"].astype(str), sort=True)
        out["pmhc"] = torch.as_tensor(
            np.asarray(codes), dtype=torch.long, device=device
        )
    else:
        out["pmhc"] = torch.zeros(n, dtype=torch.long, device=device)
    return out


def _within_pmhc_rank_loss(
    logits: torch.Tensor,
    y: torch.Tensor,
    pmhc: torch.Tensor,
) -> torch.Tensor | None:
    """Mean logistic pairwise loss over (binder, non-binder) of the same pMHC.

    Unweighted across pMHCs so one peptide cannot dominate. Each positive is
    compared to the negatives in-batch of that pMHC — not to the global prior.
    """
    losses: list[torch.Tensor] = []
    for gid in torch.unique(pmhc):
        m = pmhc == gid
        pos = logits[m & y.bool()]
        neg = logits[m & ~y.bool()]
        if pos.numel() == 0 or neg.numel() == 0:
            continue
        losses.append(F.softplus(neg.unsqueeze(0) - pos.unsqueeze(1)).mean())
    if not losses:
        return None
    return torch.stack(losses).mean()


def _pmhc_pair_slices(
    pmhc: np.ndarray,
    y: np.ndarray,
    rng: np.random.Generator,
    batch_size: int,
) -> list[np.ndarray]:
    """One slice = all positives of a pMHC plus an equal-sized chunk of its negatives."""
    n = int(y.shape[0])
    fallback = [rng.permutation(n)[s : s + batch_size] for s in range(0, n, batch_size)]
    if pmhc.shape[0] != n:
        return fallback
    groups: list[np.ndarray] = []
    cap = max(int(batch_size) * 2, 32)
    for gid in rng.permutation(np.unique(pmhc)):
        idx = np.flatnonzero(pmhc == gid)
        pos = idx[y[idx] == 1]
        neg = idx[y[idx] == 0]
        if pos.size == 0 or neg.size == 0:
            continue
        neg = rng.permutation(neg)
        n_neg = min(int(neg.size), max(int(pos.size), 1))
        if int(pos.size) + n_neg > cap:
            n_neg = max(cap - int(pos.size), min(int(pos.size), int(neg.size)), 1)
            n_neg = min(n_neg, int(neg.size))
        for start in range(0, int(neg.size), n_neg):
            chunk = neg[start : start + n_neg]
            sl = np.concatenate([pos, chunk])
            groups.append(rng.permutation(sl))
    return groups or fallback


def _aux_loss(
    g: Genotype, logits: torch.Tensor, y: torch.Tensor, embed: torch.Tensor
) -> torch.Tensor:
    yf = y.float()
    if g.training.loss == "focal":
        gamma = float(g.training.focal_gamma or 2.0)
        p = torch.sigmoid(logits)
        ce = F.binary_cross_entropy_with_logits(logits, yf, reduction="none")
        mod = torch.where(y.bool(), 1.0 - p, p)
        return ((mod**gamma) * ce).mean()
    bce = F.binary_cross_entropy_with_logits(logits, yf)
    if g.training.loss != "contrastive":
        return bce
    z = F.normalize(embed, dim=-1)
    sim = z @ z.T
    labels = y.unsqueeze(0).eq(y.unsqueeze(1)).float()
    pos = (sim * labels).sum() / labels.sum().clamp(min=1.0)
    neg = (sim * (1.0 - labels)).sum() / (1.0 - labels).sum().clamp(min=1.0)
    return bce + 0.5 * (neg - pos)


def _loss_fn(
    g: Genotype,
    logits: torch.Tensor,
    y: torch.Tensor,
    embed: torch.Tensor,
    pmhc: torch.Tensor | None = None,
) -> torch.Tensor:
    aux = _aux_loss(g, logits, y, embed)
    if pmhc is None:
        return aux
    rank = _within_pmhc_rank_loss(logits, y, pmhc)
    if rank is None:
        return aux
    return rank + 0.1 * aux


def _optimizer(g: Genotype, params) -> torch.optim.Optimizer:
    lr = float(g.training.lr)
    wd = float(g.training.weight_decay)
    name = g.training.optimizer
    if name == "sgd":
        return torch.optim.SGD(params, lr=lr, momentum=0.9, weight_decay=wd)
    if name == "adam":
        return torch.optim.Adam(params, lr=lr, weight_decay=wd)
    return torch.optim.AdamW(params, lr=lr, weight_decay=wd)


def _scheduler(g: Genotype, opt: torch.optim.Optimizer, epochs: int):
    name = g.training.scheduler
    if name == "cosine":
        return torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(epochs, 1))
    if name == "step":
        return torch.optim.lr_scheduler.StepLR(
            opt, step_size=max(epochs // 3, 1), gamma=0.5
        )
    return None


class TorchPredictor:
    def __init__(self, genotype: Genotype):
        self.genotype = genotype
        self.model: PmhctcrNet | None = None
        self._prior = 0.1
        self._fitted = False
        self._tab_dim = 1
        self.device = _device()

    def fit(self, train_df: pd.DataFrame) -> None:
        g = self.genotype
        y_all = (
            train_df["label"].to_numpy(dtype=int)
            if "label" in train_df.columns
            else np.zeros(len(train_df), dtype=int)
        )
        self._prior = float(y_all.mean()) if len(y_all) else 0.1
        rng = np.random.default_rng(int(g.seed) + 7)
        idx = hard_negative_index(train_df, g, rng)
        part = train_df.iloc[idx].reset_index(drop=True)
        tab = build_feature_matrix(g, part, train=True)
        y = part["label"].to_numpy(dtype=np.int64)
        if tab.shape[0] < 2 or np.unique(y).size < 2:
            self._fitted = False
            return
        configure_torch_determinism(int(g.seed))
        net = PmhctcrNet(g, tab.shape[1]).to(self.device)
        opt = _optimizer(g, net.parameters())
        epochs = _PDB_EPOCHS if uses_learned_gat(g) else _EPOCHS
        sched = _scheduler(g, opt, epochs)
        bs = int(g.training.batch_size)
        n = len(part)
        pmhc_ids = (
            part["mhc_epitope_id"].astype(str).to_numpy()
            if "mhc_epitope_id" in part.columns
            else np.arange(n).astype(str)
        )
        net.train()
        for _ in range(epochs):
            for sl in _pmhc_pair_slices(pmhc_ids, y, rng, bs):
                sub = part.iloc[sl]
                batch = _stack_batch(g, sub, tab[sl], self.device)
                yt = torch.as_tensor(y[sl], dtype=torch.long, device=self.device)
                opt.zero_grad(set_to_none=True)
                logits, embed = net(batch)
                loss = _loss_fn(g, logits, yt, embed, batch.get("pmhc"))
                if not torch.isfinite(loss):
                    continue
                loss.backward()
                nn.utils.clip_grad_norm_(net.parameters(), 1.0)
                opt.step()
            if sched is not None:
                sched.step()
        self.model = net
        self._tab_dim = tab.shape[1]
        self._fitted = True

    def score(self, rows_df: pd.DataFrame) -> np.ndarray:
        if not self._fitted or self.model is None:
            raw = np.full(len(rows_df), self._prior, dtype=float)
            return _calibrate_np(raw, self.genotype.calibration.temperature)
        g = self.genotype
        tab = build_feature_matrix(g, rows_df, train=False)
        self.model.eval()
        outs = []
        bs = int(g.training.batch_size)
        with torch.no_grad():
            for start in range(0, len(rows_df), bs):
                sl = slice(start, start + bs)
                batch = _stack_batch(g, rows_df.iloc[sl], tab[sl], self.device)
                logits, _ = self.model(batch)
                outs.append(torch.sigmoid(logits).detach().cpu().numpy())
        raw = np.concatenate(outs) if outs else np.full(len(rows_df), self._prior)
        return _calibrate_np(raw.astype(float), g.calibration.temperature)


def _calibrate_np(p: np.ndarray, temperature: float) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    if abs(temperature - 1.0) < 1e-12:
        return p
    logit = np.log(p / (1.0 - p))
    return 1.0 / (1.0 + np.exp(-logit / temperature))
