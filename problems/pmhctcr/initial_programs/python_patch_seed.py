"""Editable Python baseline for pMHC–TCR binding prediction.

The genome is this source file. A SEARCH/REPLACE mutator may edit only the
marked EVOLVE blocks. ``entrypoint()`` must keep returning an object with
``fit(train_df)`` / ``score(rows_df)`` used by the ImmRep25 validator.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from scipy.spatial import cKDTree

from problems.pmhctcr.assets import ESM2_HIDDEN, load_esm, load_pdb
from problems.pmhctcr.regions import region_indices

CHAINS = ("peptide", "mhca", "tcra", "tcrb")
SEQ_COL = dict(zip(CHAINS, ("epitope_seq", "mhca_seq", "tcra_seq", "tcrb_seq")))
PDB_CHAIN = {name: i for i, name in enumerate(("tcra", "tcrb", "peptide", "mhca"))}
AA = {aa: i for i, aa in enumerate("ACDEFGHIKLMNPQRSTVWY")}


# EVOLVE-BLOCK-START features
TCR_REGION_OPTIONS = ("full", "cdr1", "cdr2", "cdr3", "fr1", "fr2", "fr3", "fr4")
REGIONS = {name: "full" for name in CHAINS}


def _text(x) -> str:
    return "" if x is None or pd.isna(x) else str(x)


def _selection(row, name: str) -> tuple[str, np.ndarray]:
    seq = _text(getattr(row, SEQ_COL[name], ""))
    regions = REGIONS[name]
    regions = (regions,) if isinstance(regions, str) else regions
    if not seq:
        return seq, np.empty(0, int)
    if "full" in regions:
        return seq, np.arange(len(seq))
    parts = [region_indices(seq, region) for region in regions]
    return seq, np.unique(np.concatenate(parts)) if parts else np.empty(0, int)


def _residues(row, pdb, name: str) -> tuple[np.ndarray, str]:
    """Selected Cα indices and amino acids, only under exact alignment."""
    seq, keep = _selection(row, name)
    ca = np.flatnonzero(pdb.chain == PDB_CHAIN[name])
    if not seq or len(ca) != len(seq):
        return np.empty(0, int), ""
    return ca[keep], "".join(seq[i] for i in keep)


def _esm(row) -> np.ndarray:
    out = []
    for name in CHAINS:
        seq, keep = _selection(row, name)
        asset = load_esm(_text(getattr(row, f"esm_{name}_path", "")))
        ok = bool(asset.ok and len(asset.residue) == len(seq) and len(keep))
        out.extend((asset.residue[keep].mean(0) if ok else np.zeros(ESM2_HIDDEN), [ok]))
    return np.concatenate(out)


def _structure(row, pdb):
    selected = [_residues(row, pdb, name) for name in CHAINS] if pdb.ok else []
    if not selected or not any(len(pos) for pos, _ in selected):
        return np.zeros((1, 26)), np.zeros((1, 3)), np.zeros((2, 1), int)

    pos = np.concatenate([x[0] for x in selected])
    aas = "".join(x[1] for x in selected)
    chain = np.concatenate([
        np.full(len(item[0]), PDB_CHAIN[name]) for name, item in zip(CHAINS, selected)
    ])
    nodes = np.c_[
        np.eye(4)[chain],
        np.eye(21)[[AA.get(aa, 20) for aa in aas]],
        np.clip(np.asarray(pdb.plddt[pos]) / 100, 0, 1),
    ].astype(np.float32)
    xyz = np.asarray(pdb.xyz[pos], np.float32) / 10

    if len(pos) == 1:
        edges = np.zeros((2, 1), int)
    else:
        neighbors = cKDTree(xyz).query(xyz, k=min(9, len(pos)))[1][:, 1:]
        edges = np.stack((np.repeat(np.arange(len(pos)), neighbors.shape[1]), neighbors.ravel()))
    return nodes, xyz, edges


def _surface(row, pdb) -> np.ndarray:
    if not pdb.ok:
        return np.zeros(9)
    try:
        surfaces = []
        for side in ("tcr", "pmhc"):
            with np.load(_text(getattr(row, f"masif_{side}_path", ""))) as f:
                key = "desc" if "desc" in f else (
                    "desc_straight" if side == "tcr" else "desc_flipped"
                )
                surfaces.append((np.asarray(f[key]), np.asarray(f["xyz"])))
    except (OSError, ValueError, KeyError):
        return np.zeros(9)

    def select(surface, names):
        desc, xyz = surface
        all_ca = np.concatenate([np.flatnonzero(pdb.chain == PDB_CHAIN[n]) for n in names])
        keep = np.concatenate([_residues(row, pdb, n)[0] for n in names])
        if not len(all_ca) or not len(keep) or not len(xyz):
            return desc[:0]
        owner = all_ca[cKDTree(pdb.xyz[all_ca]).query(xyz)[1]]
        return desc[np.isin(owner, keep)]

    tcr = select(surfaces[0], ("tcra", "tcrb"))
    pmhc = select(surfaces[1], ("peptide", "mhca"))
    if not len(tcr) or not len(pmhc):
        return np.zeros(9)

    def stats(query, reference):
        distance = cKDTree(reference).query(query)[0]
        return np.r_[distance.mean(), np.quantile(distance, (.25, .5, .75))]

    return np.r_[stats(tcr, pmhc), stats(pmhc, tcr), 1.0]


def _row(row):
    pdb = load_pdb(_text(getattr(row, "pdb_path", "")))
    return (np.r_[_esm(row), _surface(row, pdb)].astype(np.float32), *_structure(row, pdb))


def _data(df: pd.DataFrame) -> list[tuple]:
    return [_row(row) for row in df.itertuples(index=False)]
# EVOLVE-BLOCK-END features


# EVOLVE-BLOCK-START model
def _pack(records, mean, std):
    vector = torch.tensor(
        np.stack([(record[0] - mean) / std for record in records]), dtype=torch.float32
    )
    nodes, xyz, edges, batch, offset = [], [], [], [], 0
    for graph_id, (_, h, x, e) in enumerate(records):
        nodes.append(h); xyz.append(x); edges.append(e + offset)
        batch.append(np.full(len(h), graph_id)); offset += len(h)
    return (
        vector,
        torch.tensor(np.concatenate(nodes), dtype=torch.float32),
        torch.tensor(np.concatenate(xyz), dtype=torch.float32),
        torch.tensor(np.concatenate(edges, axis=1), dtype=torch.long),
        torch.tensor(np.concatenate(batch), dtype=torch.long),
    )


class _EGNNLayer(torch.nn.Module):
    def __init__(self, hidden: int):
        super().__init__()

        def mlp(input_dim, output_dim):
            return torch.nn.Sequential(
                torch.nn.Linear(input_dim, hidden), torch.nn.SiLU(),
                torch.nn.Linear(hidden, output_dim),
            )

        self.edge = mlp(2 * hidden + 1, hidden)
        self.coord = mlp(hidden, 1)
        self.node = mlp(2 * hidden, hidden)

    def forward(self, h, x, edges):
        src, dst = edges
        delta = x[src] - x[dst]
        message = self.edge(torch.cat((
            h[src], h[dst], delta.square().sum(1, keepdim=True)
        ), 1))
        degree = torch.zeros(len(h), 1).index_add_(
            0, src, torch.ones(len(src), 1)
        ).clamp_min(1)
        aggregate = torch.zeros_like(h).index_add_(0, src, message) / degree
        move = torch.zeros_like(x).index_add_(
            0, src, delta * torch.tanh(self.coord(message))
        ) / degree
        return h + self.node(torch.cat((h, aggregate), 1)), x + 0.1 * move


class _FusionModel(torch.nn.Module):
    def __init__(self, vector_dim: int, hidden: int = 32):
        super().__init__()
        self.node_in = torch.nn.Linear(26, hidden)
        self.layers = torch.nn.ModuleList((_EGNNLayer(hidden), _EGNNLayer(hidden)))
        self.head = torch.nn.Sequential(
            torch.nn.Linear(vector_dim + hidden, hidden), torch.nn.SiLU(),
            torch.nn.Linear(hidden, 1),
        )

    def forward(self, vector, nodes, xyz, edges, batch):
        h = F.silu(self.node_in(nodes))
        for layer in self.layers:
            h, xyz = layer(h, xyz, edges)
        graph = torch.zeros(len(vector), h.shape[1]).index_add_(0, batch, h)
        count = torch.zeros(len(vector), 1).index_add_(0, batch, torch.ones(len(h), 1))
        return self.head(torch.cat((vector, graph / count.clamp_min(1)), 1)).squeeze(1)


class BindingPredictor:
    def __init__(self, epochs: int = 15, batch_size: int = 32):
        self.epochs, self.batch_size = epochs, batch_size
        self.active_modalities = ("esm", "structure", "surface")
        self.interaction_family = "explicit_patch_matching"
        self.model = self.mean = self.std = None

    def fit(self, train_df: pd.DataFrame) -> None:
        torch.manual_seed(0)
        records = _data(train_df)
        raw = np.stack([record[0] for record in records])
        self.mean, self.std = raw.mean(0), np.maximum(raw.std(0), 1e-6)
        self.model = _FusionModel(raw.shape[1])
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=1e-3)
        labels = train_df["label"].to_numpy(np.float32)
        positives, negatives = labels.sum(), len(labels) - labels.sum()
        pos_weight = torch.tensor(negatives / positives if positives and negatives else 1.0)
        rng = np.random.default_rng(0)

        self.model.train()
        for _ in range(self.epochs):
            order = rng.permutation(len(records))
            for start in range(0, len(records), self.batch_size):
                ids = order[start:start + self.batch_size]
                optimizer.zero_grad()
                loss = F.binary_cross_entropy_with_logits(
                    self.model(*_pack([records[i] for i in ids], self.mean, self.std)),
                    torch.tensor(labels[ids]), pos_weight=pos_weight,
                )
                loss.backward(); optimizer.step()
        self.model.eval()

    def score(self, rows_df: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            return np.zeros(len(rows_df))
        records, scores = _data(rows_df), []
        with torch.no_grad():
            for start in range(0, len(records), self.batch_size):
                batch = records[start:start + self.batch_size]
                scores.append(torch.sigmoid(
                    self.model(*_pack(batch, self.mean, self.std))
                ).numpy())
        return np.concatenate(scores) if scores else np.zeros(0)
# EVOLVE-BLOCK-END model


def entrypoint():
    return BindingPredictor()
