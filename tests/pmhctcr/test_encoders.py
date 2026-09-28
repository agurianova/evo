"""Forward-only encoder/architecture contract tests (no validate() / full val)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch

from problems.pmhctcr.compiler import describe_compiled
from problems.pmhctcr.features import (
    _molecule_vecs,
    _seq_block,
    _seq_channel_width,
    build_feature_matrix,
)
from problems.pmhctcr.genotype import default_genotype, uses_learned_sequence
from problems.pmhctcr.nn_model import PmhctcrNet, _seq_max
from problems.pmhctcr.operators import apply_operator


def _row() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "epitope_seq": "SIINFEKL",
                "mhca_seq": "ACDEFGHIKLMNPQRSTVWY" * 8,
                "tcra_seq": "CASSABCD",
                "tcrb_seq": "CASSWXYZ",
                "tcra_vgene": "",
                "tcrb_vgene": "",
                "tcra_jgene": "",
                "tcrb_jgene": "",
                "tcra_seq_cdr3": "CASS",
                "tcrb_seq_cdr3": "CASS",
            }
        ]
    )


def _tiny(g):
    g.model.hidden_dim = 64
    g.model.num_layers = 1
    g.model.num_heads = 4
    g.encoders.sequence.hidden_dim = 64
    g.encoders.sequence.arch = "cnn"
    g.encoders.sequence.region = "cdr3"
    return g


def _ids_batch(g, B: int = 2) -> dict[str, torch.Tensor]:
    pep_n, mhc_n, tcr_n = _seq_max(g)
    return {
        "pep": torch.randint(1, 21, (B, pep_n)),
        "mhc": torch.randint(1, 21, (B, mhc_n)),
        "tcra": torch.randint(1, 21, (B, tcr_n)),
        "tcrb": torch.randint(1, 21, (B, tcr_n)),
        "trav": torch.zeros(B, dtype=torch.long),
        "trbv": torch.zeros(B, dtype=torch.long),
    }


def _run_backward(net: PmhctcrNet, batch: dict[str, torch.Tensor]) -> None:
    net.train()
    logits, _ = net(batch)
    loss = logits.sum()
    loss.backward()


def test_mlp_has_no_tab_self_attention():
    g = default_genotype()
    net = PmhctcrNet(g, tab_dim=32)
    assert net.seq_enc is None
    assert net.cross is None
    assert net._extra_cross is False


def test_mlp_cross_attention_promotes_and_calls_pair_mha():
    g = default_genotype()
    child = apply_operator(
        g,
        "CHANGE_INTERACTION",
        guided_text="OPERATOR=CHANGE_INTERACTION; set interaction.method to cross_attention",
    )
    _tiny(child)
    assert child.model.type == "seq_cross_encoder"
    spec = describe_compiled(child)
    assert spec["learned_sequence"] is True
    assert spec["cross_kind"] == "mha_pooled(peptide_tcr)"
    net = PmhctcrNet(child, tab_dim=16)
    assert net.seq_enc is not None
    assert net.cross is not None
    assert net._extra_cross is False
    called = {"n": 0}

    def _hook(_mod, _inp, _out):
        called["n"] += 1

    net.cross.register_forward_hook(_hook)
    batch = _ids_batch(child)
    batch["tab"] = torch.randn(2, 16)
    _run_backward(net, batch)
    assert called["n"] == 1
    assert net.seq_enc.emb.weight.grad is not None
    assert net.cross.in_proj_weight.grad is not None


def test_multimodal_cross_attn_mha_runs_between_modalities():
    g = default_genotype()
    g.model.type = "multimodal_cross_attn"
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True
    _tiny(g)
    spec = describe_compiled(g)
    assert spec["learned_sequence"] is True
    assert spec["cross_kind"] == "mha_modalities"
    net = PmhctcrNet(g, tab_dim=24)
    assert net.seq_enc is not None
    assert net.cross is not None
    assert net._extra_cross is False
    called = {"n": 0}
    net.cross.register_forward_hook(
        lambda *a, **k: called.__setitem__("n", called["n"] + 1)
    )
    batch = _ids_batch(g)
    batch["tab"] = torch.randn(2, 24)
    batch["masif_cat"] = torch.randn(2, 160)
    _run_backward(net, batch)
    assert called["n"] == 1
    assert net.cross.in_proj_weight.grad is not None
    assert net.surf_proj is not None
    assert net.surf_proj.weight.grad is not None


def test_masif_patch_has_patch_mha_not_tab_self_attn():
    g = default_genotype()
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True
    g.model.type = "masif_patch_cross_attn"
    _tiny(g)
    net = PmhctcrNet(g, tab_dim=20)
    assert net.patch_attn is not None
    assert net._extra_cross is False
    assert net.cross is None
    batch = _ids_batch(g)
    batch["tab"] = torch.randn(2, 20)
    batch["tcr_patch"] = torch.randn(2, 64, 80)
    batch["pmhc_patch"] = torch.randn(2, 64, 80)
    _run_backward(net, batch)
    assert net.patch_attn.in_proj_weight.grad is not None


def test_masif_siamese_two_tower_gets_grad():
    g = default_genotype()
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True
    g.model.type = "masif_siamese"
    _tiny(g)
    spec = describe_compiled(g)
    assert spec["learned_siamese"] is True
    net = PmhctcrNet(g, tab_dim=20)
    assert net.siamese is not None
    assert net._extra_cross is False
    batch = _ids_batch(g)
    batch["tab"] = torch.randn(2, 20)
    batch["tcr_pool"] = torch.randn(2, 80)
    batch["pmhc_pool"] = torch.randn(2, 80)
    _run_backward(net, batch)
    assert net.siamese.shared[0].weight.grad is not None


def test_seq_dual_drops_bag_of_aa_from_table():
    df = _row()
    mlp = default_genotype()
    dual = default_genotype()
    dual.model.type = "seq_dual_encoder"
    assert uses_learned_sequence(dual) is True
    assert _seq_channel_width(mlp) == 20
    assert _seq_channel_width(dual) == 0
    x_mlp = build_feature_matrix(mlp, df, train=False)
    x_dual = build_feature_matrix(dual, df, train=False)
    assert x_dual.shape[1] < x_mlp.shape[1]
    seq_dual = _seq_block(dual, df, 0, mask=False)
    mol = _molecule_vecs(dual, seq_dual, np.zeros(1), np.zeros(1))
    assert mol["peptide"].size == 1
    seq_mlp = _seq_block(mlp, df, 0, mask=False)
    mol_mlp = _molecule_vecs(mlp, seq_mlp, np.zeros(1), np.zeros(1))
    assert mol_mlp["peptide"].size == 20
    assert mol_mlp["mhc"].size == 20


def test_protein_lm_does_not_train_seq_encoder():
    g = default_genotype()
    child = apply_operator(
        g,
        "CHANGE_SEQUENCE",
        guided_text="OPERATOR=CHANGE_SEQUENCE; set encoders.sequence.arch to protein_lm",
    )
    assert child.model.type == "mlp_features"
    assert child.encoders.sequence.arch == "protein_lm"
    spec = describe_compiled(child)
    assert spec["learned_sequence"] is False
    net = PmhctcrNet(child, tab_dim=8)
    assert net.seq_enc is None


def test_cnn_insight_trains_seqencoder_not_dinucleotide_table():
    g = default_genotype()
    child = apply_operator(
        g,
        "CHANGE_SEQUENCE",
        guided_text="OPERATOR=CHANGE_SEQUENCE; set encoders.sequence.arch to cnn",
    )
    _tiny(child)
    child.encoders.sequence.arch = "cnn"
    assert child.model.type == "seq_dual_encoder"
    assert uses_learned_sequence(child)
    df = _row()
    seq = _seq_block(child, df, 0, mask=False)
    # Tabular sequence is V/J only (no 20-d AA, no dinucleotide 40-d).
    assert seq.size != 80
    net = PmhctcrNet(child, tab_dim=8)
    assert net.seq_enc is not None
    assert net.seq_enc.arch == "cnn"
    batch = _ids_batch(child, B=2)
    batch["tab"] = torch.randn(2, 8)
    _run_backward(net, batch)
    assert net.seq_enc.convs[0].weight.grad is not None
