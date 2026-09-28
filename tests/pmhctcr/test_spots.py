from __future__ import annotations

import numpy as np

from problems.pmhctcr.assets import load_masif
from problems.pmhctcr.compiler import compile_genotype
from problems.pmhctcr.dataset import feature_frame, load_folds
from problems.pmhctcr.genotype import SurfaceDerived, default_genotype
from problems.pmhctcr.operators import apply_operator
from problems.pmhctcr.spots import SPOT_CORE, core_spot_features, spot_feature_vector


def _mini(n_train: int = 24, n_val: int = 12):
    folds = load_folds()
    return folds["train"].iloc[:n_train].copy(), folds["val"].iloc[:n_val].copy()


def test_spot_core_has_matches_and_cdr_geometry():
    train, _ = _mini(8, 2)
    row = train.iloc[0]
    asset = load_masif(row["masif_tcr_path"], row["masif_pmhc_path"])
    g = default_genotype()
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True
    g.encoders.surface.spots.enabled = True
    feat = core_spot_features(g, asset, row)
    assert set(feat) == set(SPOT_CORE)
    assert feat["n_match"] > 0
    assert 0.0 < feat["area_frac"] < 1.0
    assert feat["n_components"] >= 1
    assert feat["min_nn"] < 1.7
    assert feat["dist_peptide"] > 0.0


def test_derived_ratio_appended():
    train, _ = _mini(4, 2)
    row = train.iloc[0]
    asset = load_masif(row["masif_tcr_path"], row["masif_pmhc_path"])
    g = default_genotype()
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True
    g.encoders.surface.spots.enabled = True
    g.encoders.surface.spots.derived = [
        SurfaceDerived(op="ratio", a="cdr3_frac", b="area_frac")
    ]
    vec = spot_feature_vector(g, asset, row)
    assert vec.shape[0] == len(SPOT_CORE) + 1
    core = core_spot_features(g, asset, row)
    expected = core["cdr3_frac"] / (
        core["area_frac"] if abs(core["area_frac"]) > 1e-8 else 1e-8
    )
    assert abs(vec[-1] - expected) < 1e-6


def test_spots_change_scores_vs_pooled_masif():
    train, val = _mini()
    pooled = apply_operator(
        default_genotype(), "CREATE_SURFACE", rng=np.random.default_rng(0)
    )
    spots = apply_operator(pooled, "CHANGE_SURFACE", rng=np.random.default_rng(1))
    assert pooled.encoders.surface.spots.enabled is False
    assert spots.encoders.surface.spots.enabled is True
    a = compile_genotype(pooled)
    b = compile_genotype(spots)
    a.fit(train)
    b.fit(train)
    sa = a.score(feature_frame(val))
    sb = b.score(feature_frame(val))
    assert sa.shape == sb.shape
    assert not np.allclose(sa, sb, atol=1e-6)
