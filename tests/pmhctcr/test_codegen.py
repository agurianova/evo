from __future__ import annotations

import ast
from pathlib import Path

from problems.pmhctcr.behavior import behavior_metrics
from problems.pmhctcr.codegen import exec_program, loads_program, render_program
from problems.pmhctcr.genotype import default_genotype
from problems.pmhctcr.nn_model import PmhctcrNet, TorchPredictor
from problems.pmhctcr.operators import apply_operator


def test_render_roundtrip_and_entrypoint():
    g = default_genotype()
    src = render_program(g, insight="OPERATOR=NOOP")
    assert "def entrypoint" in src
    assert "GENOTYPE_JSON" in src
    assert "# SeqEncoder: bag_of_aa" in src
    assert "# ignored:" in src
    back = loads_program(src)
    assert back.model.type == g.model.type
    pred = exec_program(src)
    assert hasattr(pred, "fit") and hasattr(pred, "score")
    assert pred.genotype.model.type == g.model.type
    metrics = behavior_metrics(src)
    assert metrics["modality_mix"] == 0.0
    assert metrics["interaction_kind"] == 0.0


def test_insight_cnn_python_trains_seq_encoder():
    g = default_genotype()
    insight = "OPERATOR=CHANGE_SEQUENCE; set encoders.sequence.arch to cnn"
    child = apply_operator(g, "CHANGE_SEQUENCE", guided_text=insight)
    src = render_program(child, insight=insight)
    assert "# SeqEncoder: cnn" in src
    assert child.model.type == "seq_dual_encoder"
    pred = exec_program(src)
    assert isinstance(pred, TorchPredictor)
    net = PmhctcrNet(loads_program(src), tab_dim=16)
    assert net.seq_enc is not None
    assert net.seq_enc.arch == "cnn"


def test_seed_py_matches_default_genotype():
    path = (
        Path(__file__).resolve().parents[2]
        / "problems"
        / "pmhctcr"
        / "initial_programs"
        / "seed.py"
    )
    src = path.read_text()
    g = loads_program(src)
    seed = default_genotype()
    assert g.model.type == seed.model.type
    assert g.encoders.sequence.arch == seed.encoders.sequence.arch
    assert g.inputs.sequence.peptide is True
    assert "# SeqEncoder: bag_of_aa" in src


def test_insight_with_markdown_rule_stays_valid_python():
    g = default_genotype()
    insight = "OPERATOR=CHANGE_MODEL; set model.type to seq_dual_encoder\n\n---"
    child = apply_operator(g, "CHANGE_MODEL", guided_text=insight)
    src = render_program(child, insight=insight)
    ast.parse(src)
    assert "\n---" not in src
    assert child.model.type == "seq_dual_encoder"
    assert "# insight: OPERATOR=CHANGE_MODEL; set model.type to seq_dual_encoder" in src
    from problems.pmhctcr.genotype import dumps

    g = default_genotype()
    assert loads_program(dumps(g)).seed == g.seed
