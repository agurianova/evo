from __future__ import annotations

import numpy as np

from problems.pmhctcr.assets import ESM2_HIDDEN, load_esm
from problems.pmhctcr.dataset import load_joined


def test_load_esm_missing_is_zero(tmp_path):
    asset = load_esm(str(tmp_path / "missing.npz"))
    assert not asset.ok
    assert asset.pooled.shape == (ESM2_HIDDEN,)
    assert np.all(asset.pooled == 0)


def test_load_esm_reads_cached_npz(tmp_path):
    path = tmp_path / "mhca_0000001.npz"
    pooled = np.linspace(0, 1, ESM2_HIDDEN, dtype=np.float32)
    cls = pooled[::-1].copy()
    residue = np.stack([pooled, cls]).astype(np.float16)
    np.savez_compressed(path, residue=residue, pooled=pooled, cls=cls)
    asset = load_esm(str(path))
    assert asset.ok
    assert np.allclose(asset.pooled, pooled)
    assert asset.residue.shape == (2, ESM2_HIDDEN)


def test_joined_frame_has_esm_paths():
    df = load_joined()
    for col in ("esm_mhca_path", "esm_peptide_path", "esm_tcra_path", "esm_tcrb_path"):
        assert col in df.columns
        assert df[col].str.endswith(".npz").all()
    row = df.iloc[0]
    assert row["mhca_id"] in row["esm_mhca_path"]
    assert row["epitope_id"] in row["esm_peptide_path"]
    assert row["tcra_id"] in row["esm_tcra_path"]
    assert row["tcrb_id"] in row["esm_tcrb_path"]


def test_real_esm_cache_loads_for_joined_row():
    from pathlib import Path

    df = load_joined()
    row = df.iloc[0]
    peptide = load_esm(row["esm_peptide_path"])
    assert Path(row["esm_peptide_path"]).is_file()
    assert peptide.ok
    assert peptide.pooled.shape == (ESM2_HIDDEN,)
    assert peptide.residue.shape[1] == ESM2_HIDDEN
    mhca = load_esm(row["esm_mhca_path"])
    assert mhca.ok
