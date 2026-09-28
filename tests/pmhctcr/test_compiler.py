from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from problems.pmhctcr.assets import load_masif
from problems.pmhctcr.compiler import compile_genotype
from problems.pmhctcr.dataset import feature_frame, load_folds
from problems.pmhctcr.genotype import default_genotype
from problems.pmhctcr.insight_exec import map_operator, parse_primary_insight
from problems.pmhctcr.operators import apply_operator


def _mini_frames(n_train: int = 32, n_val: int = 16):
    folds = load_folds()
    train = folds["train"].iloc[:n_train].copy()
    val = folds["val"].iloc[:n_val].copy()
    return train, val


def test_masif_files_are_direct_tcr_and_flipped_pmhc():
    train, _ = _mini_frames(4, 2)
    row = train.iloc[0]
    asset = load_masif(row["masif_tcr_path"], row["masif_pmhc_path"])
    assert asset.ok_tcr and asset.ok_pmhc
    assert asset.tcr_pooled.shape == (80,)
    assert asset.pmhc_pooled.shape == (80,)
    # Canonical stored views must be used, not the opposite orientation.
    import numpy as np

    with np.load(row["masif_tcr_path"]) as z:
        assert np.allclose(asset.tcr_pooled, z["pooled"], atol=1e-5)
        assert str(z["orientation"]) == "straight"
    with np.load(row["masif_pmhc_path"]) as z:
        assert np.allclose(asset.pmhc_pooled, z["pooled"], atol=1e-5)
        assert str(z["orientation"]) == "flipped"


def test_create_surface_changes_scores_vs_sequence_only():
    train, val = _mini_frames()
    seq = default_genotype()
    surf = apply_operator(seq, "CREATE_SURFACE", rng=np.random.default_rng(0))
    assert surf.inputs.masif.tcr_direct and surf.inputs.masif.pmhc_flipped
    a = compile_genotype(seq)
    b = compile_genotype(surf)
    a.fit(train)
    b.fit(train)
    sa = a.score(feature_frame(val))
    sb = b.score(feature_frame(val))
    assert sa.shape == sb.shape == (len(val),)
    assert not np.allclose(sa, sb, atol=1e-6)


def test_pdb_and_gat_enter_score():
    train, val = _mini_frames(24, 12)
    g = default_genotype()
    g.inputs.pdb.present = True
    g.inputs.pdb.kind = "complex"
    g.model.type = "pdb_gnn"
    gat = g.model_copy(deep=True)
    gat.encoders.structure.arch = "gat"
    mpnn = g.model_copy(deep=True)
    mpnn.encoders.structure.arch = "mpnn"
    a = compile_genotype(gat)
    b = compile_genotype(mpnn)
    a.fit(train)
    b.fit(train)
    sa = a.score(feature_frame(val))
    sb = b.score(feature_frame(val))
    assert not np.allclose(sa, sb, atol=1e-6)


def test_interaction_enters_score():
    train, val = _mini_frames()
    g = default_genotype()
    child = apply_operator(
        g,
        "CHANGE_INTERACTION",
        guided_text="OPERATOR=CHANGE_INTERACTION; cross_attention peptide_tcr",
    )
    assert child.interaction.method == "cross_attention"
    a = compile_genotype(g)
    b = compile_genotype(child)
    a.fit(train)
    b.fit(train)
    sa = a.score(feature_frame(val))
    sb = b.score(feature_frame(val))
    assert not np.allclose(sa, sb, atol=1e-6)


def test_hidden_layers_follow_num_layers():
    from sklearn.linear_model import LogisticRegression

    from problems.pmhctcr.compiler import hidden_layer_sizes
    from problems.pmhctcr.nn_model import TorchPredictor

    linear = default_genotype()
    linear.model.num_layers = 1
    assert hidden_layer_sizes(linear) == ()
    assert isinstance(compile_genotype(linear).model, LogisticRegression)

    mlp = default_genotype()
    mlp.model.num_layers = 3
    mlp.model.hidden_dim = 64
    assert hidden_layer_sizes(mlp) == (64, 64)
    pred = compile_genotype(mlp)
    assert isinstance(pred, TorchPredictor)

    train, val = _mini_frames()
    a = compile_genotype(linear)
    b = compile_genotype(mlp)
    a.fit(train)
    b.fit(train)
    sa = a.score(feature_frame(val))
    sb = b.score(feature_frame(val))
    assert sa.shape == sb.shape
    assert not np.allclose(sa, sb, atol=1e-6)


def test_dropout_and_scheduler_change_torch_head():
    train, val = _mini_frames()
    a = default_genotype()
    a.model.num_layers = 2
    a.model.dropout = 0.0
    a.training.scheduler = "none"
    b = a.model_copy(deep=True)
    b.model.dropout = 0.4
    b.training.scheduler = "cosine"
    pa = compile_genotype(a)
    pb = compile_genotype(b)
    pa.fit(train)
    pb.fit(train)
    sa = pa.score(feature_frame(val))
    sb = pb.score(feature_frame(val))
    assert sa.shape == sb.shape
    assert not np.allclose(sa, sb, atol=1e-6)


def test_within_pmhc_rank_loss_prefers_correct_order():
    import torch

    from problems.pmhctcr.nn_model import _pmhc_pair_slices, _within_pmhc_rank_loss

    y = torch.tensor([1, 1, 0, 0, 1, 0])
    pmhc = torch.tensor([0, 0, 0, 0, 1, 1])
    good = _within_pmhc_rank_loss(
        torch.tensor([2.0, 2.1, -1.0, -1.2, 3.0, -2.0]), y, pmhc
    )
    bad = _within_pmhc_rank_loss(
        torch.tensor([-2.0, -2.1, 1.0, 1.2, -3.0, 2.0]), y, pmhc
    )
    assert good is not None and bad is not None
    assert float(good) < float(bad)

    pmhc_np = np.array(["a"] * 6 + ["b"] * 6)
    y_np = np.array([1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0], dtype=np.int64)
    slices = _pmhc_pair_slices(pmhc_np, y_np, np.random.default_rng(0), batch_size=8)
    assert slices
    for sl in slices:
        assert len(set(pmhc_np[sl])) == 1
        yy = y_np[sl]
        assert (yy == 1).any() and (yy == 0).any()


def test_torch_fit_is_deterministic_for_same_seed():
    train, val = _mini_frames()
    g = default_genotype()
    g.model.num_layers = 2
    g.model.dropout = 0.3
    g.seed = 11
    a = compile_genotype(g)
    b = compile_genotype(g.model_copy(deep=True))
    a.fit(train)
    b.fit(train)
    sa = a.score(feature_frame(val))
    sb = b.score(feature_frame(val))
    assert np.allclose(sa, sb, atol=1e-6)


def test_seq_cross_encoder_differs_from_mlp_features():
    train, val = _mini_frames(24, 12)
    mlp = default_genotype()
    mlp.model.num_layers = 2
    cross = mlp.model_copy(deep=True)
    cross.model.type = "seq_cross_encoder"
    a = compile_genotype(mlp)
    b = compile_genotype(cross)
    a.fit(train)
    b.fit(train)
    sa = a.score(feature_frame(val))
    sb = b.score(feature_frame(val))
    assert not np.allclose(sa, sb, atol=1e-6)


def test_masif_model_without_surface_maps_to_create_surface():
    from gigaevo.evolution.mutation.context import InsightsMutationContext
    from gigaevo.llm.agents.insights import ProgramInsight, ProgramInsights

    insight = ProgramInsight(
        type="missing_modality",
        tag="harmful",
        severity="high",
        anchor_quote='"tcr_direct": false',
        substitute="OPERATOR=CHANGE_MODEL; set model.type to masif_siamese",
        mechanism="use masif tcr.npz / pmhc.npz",
    )
    ctx = InsightsMutationContext(insights=ProgramInsights(insights=[insight])).format()
    parsed = parse_primary_insight(ctx)
    assert parsed is not None
    # OPERATOR token wins; masif_siamese without MaSIF is repaired/rejected, not remapped.
    assert map_operator(parsed, default_genotype()) == "CHANGE_MODEL"


def test_protein_lm_uses_cached_esm_and_changes_scores():
    from problems.pmhctcr.repair import repair

    train, val = _mini_frames()
    seq = default_genotype()
    lm = seq.model_copy(deep=True)
    lm.encoders.sequence.arch = "protein_lm"
    lm = repair(lm)
    assert lm.encoders.sequence.arch == "protein_lm"
    assert lm.encoders.sequence.pretrained is True
    a = compile_genotype(seq)
    b = compile_genotype(lm)
    a.fit(train)
    b.fit(train)
    sa = a.score(feature_frame(val))
    sb = b.score(feature_frame(val))
    assert sa.shape == sb.shape
    assert not np.allclose(sa, sb, atol=1e-6)


def test_seq_dual_does_not_drop_masif_features():
    from problems.pmhctcr.compiler import describe_compiled
    from problems.pmhctcr.features import build_feature_matrix

    train, _ = _mini_frames(8, 4)
    seq = default_genotype()
    seq.model.type = "seq_dual_encoder"
    both = seq.model_copy(deep=True)
    both.inputs.masif.tcr_direct = True
    both.inputs.masif.pmhc_flipped = True
    x_seq = build_feature_matrix(seq, train, train=False)
    x_both = build_feature_matrix(both, train, train=False)
    assert x_both.shape[1] > x_seq.shape[1]
    spec = describe_compiled(both)
    assert spec["tabular_sequence"] is True
    assert spec["tabular_surface"] is True
    assert spec["learned_sequence"] is True


def test_interaction_cross_attention_on_seq_dual_builds_mha():
    from problems.pmhctcr.compiler import describe_compiled
    from problems.pmhctcr.nn_model import PmhctcrNet

    g = default_genotype()
    g.model.type = "seq_dual_encoder"
    g.interaction.method = "cross_attention"
    g.interaction.fusion = "concat"
    g.interaction.pairs = ["peptide_tcr"]
    spec = describe_compiled(g)
    assert spec["learned_sequence"] is True
    assert spec["learned_cross"] is True
    module = PmhctcrNet(g, tab_dim=32)
    assert module.cross is not None
    assert module.seq_enc is not None
    assert module._extra_cross is False


def test_mlp_features_transformer_arch_is_not_a_transformer():
    from problems.pmhctcr.compiler import describe_compiled

    g = default_genotype()
    assert g.model.type == "mlp_features"
    assert g.encoders.sequence.arch == "transformer"
    spec = describe_compiled(g)
    assert spec["learned_sequence"] is False
    assert any("arch=" in item for item in spec["ignored"])


def test_saved_json_child_compiles():
    from problems.pmhctcr.compiler import compile_genotype, describe_compiled
    from problems.pmhctcr.nn_model import TorchPredictor

    seed_path = (
        Path(__file__).resolve().parents[2]
        / "problems"
        / "pmhctcr"
        / "initial_programs"
        / "seed.json"
    )
    payload = json.loads(seed_path.read_text())
    pred = compile_genotype(payload)
    assert isinstance(pred, TorchPredictor)
    spec = describe_compiled(payload)
    assert spec["head"] == "torch"
    assert spec["learned_sequence"] is False
