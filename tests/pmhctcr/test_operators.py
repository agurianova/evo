from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from problems.pmhctcr.codegen import loads_program, render_program
from problems.pmhctcr.compiler import compile_genotype
from problems.pmhctcr.genotype import (
    OPERATOR_IDS,
    default_genotype,
    dumps,
    loads,
    n_active_inputs,
)
from problems.pmhctcr.operators import apply_operator, is_applicable
from problems.pmhctcr.repair import integrity_errors, repair


def test_default_genotype_is_valid():
    g = default_genotype()
    assert not integrity_errors(g)
    assert n_active_inputs(g) == 4
    roundtrip = loads(dumps(g))
    assert roundtrip.inputs.sequence.peptide is True


def test_repair_drops_invalid_interaction_pairs():
    g = default_genotype()
    g.inputs.sequence.tcr_alpha = False
    g.inputs.sequence.tcr_beta = False
    g.interaction.pairs = ["peptide_tcr"]
    g.interaction.method = "product"
    g.interaction.fusion = "concat"
    fixed = repair(g)
    assert "peptide_tcr" not in fixed.interaction.pairs
    assert fixed.interaction.method is None


def test_change_input_does_not_drop_last_source():
    g = default_genotype()
    g.inputs.sequence.peptide = False
    g.inputs.sequence.mhc = False
    g.inputs.sequence.tcr_alpha = False
    g.inputs.sequence.tcr_beta = True
    rng = np.random.default_rng(0)
    for _ in range(20):
        child = apply_operator(g, "CHANGE_INPUT", rng=rng)
        assert n_active_inputs(child) >= 1
        assert (
            not str(child.meta.operator_applied).endswith("_REJECTED")
            or n_active_inputs(child) >= 1
        )


def test_change_sequence_rejected_without_sequence():
    g = default_genotype()
    g.inputs.sequence.peptide = False
    g.inputs.sequence.mhc = False
    g.inputs.sequence.tcr_alpha = False
    g.inputs.sequence.tcr_beta = False
    g.inputs.pdb.present = True
    g.inputs.pdb.kind = "complex"
    child = apply_operator(g, "CHANGE_SEQUENCE", rng=np.random.default_rng(1))
    assert child.meta.operator_applied == "CHANGE_SEQUENCE_REJECTED"


def test_create_surface_enables_masif_when_off():
    g = default_genotype()
    assert not g.inputs.masif.tcr_direct
    assert not g.inputs.masif.pmhc_flipped
    assert is_applicable(g, "CREATE_SURFACE")
    child = apply_operator(g, "CREATE_SURFACE", rng=np.random.default_rng(2))
    assert child.meta.operator_applied == "CREATE_SURFACE"
    assert child.inputs.masif.tcr_direct is True
    assert child.inputs.masif.pmhc_flipped is True
    from problems.pmhctcr.genotype import functional_dumps

    again = apply_operator(g, "CREATE_SURFACE", rng=np.random.default_rng(4))
    assert functional_dumps(child) == functional_dumps(again)


def test_create_surface_inapplicable_when_masif_on():
    g = default_genotype()
    g.inputs.masif.tcr_direct = True
    assert not is_applicable(g, "CREATE_SURFACE")
    child = apply_operator(g, "CREATE_SURFACE", rng=np.random.default_rng(3))
    assert child.meta.operator_applied == "CREATE_SURFACE_REJECTED"


def test_change_surface_enables_complementary_spots():
    g = default_genotype()
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True
    assert is_applicable(g, "CHANGE_SURFACE")
    child = apply_operator(g, "CHANGE_SURFACE", rng=np.random.default_rng(3))
    assert child.meta.operator_applied == "CHANGE_SURFACE"
    assert child.encoders.surface.spots.enabled is True
    assert child.encoders.surface.spots.threshold == pytest.approx(1.7)


def test_repair_keeps_protein_lm_pretrained():
    g = default_genotype()
    g.encoders.sequence.arch = "protein_lm"
    g.encoders.sequence.pretrained = False
    fixed = repair(g)
    assert fixed.encoders.sequence.arch == "protein_lm"
    assert fixed.encoders.sequence.pretrained is True


def test_interface_scope_requires_complex():
    g = default_genotype()
    g.inputs.pdb.present = True
    g.inputs.pdb.kind = "monomer"
    g.encoders.structure.scope = "interface"
    fixed = repair(g)
    assert fixed.encoders.structure.scope == "full_complex"


def test_noop_can_reseed():
    g = default_genotype()
    child = apply_operator(g, "NOOP", new_seed=99)
    assert child.meta.operator_applied == "NOOP"
    assert child.seed == 99
    assert child.inputs == g.inputs
    assert child.meta.generation == g.meta.generation + 1


def test_change_sequence_region_mhc_cannot_be_cdr():
    g = default_genotype()
    g.inputs.sequence.peptide = False
    g.inputs.sequence.tcr_alpha = False
    g.inputs.sequence.tcr_beta = False
    g.inputs.sequence.mhc = True
    rng = np.random.default_rng(11)
    for _ in range(40):
        g = apply_operator(g, "CHANGE_SEQUENCE", rng=rng)
        if g.encoders.sequence.region in {
            "cdr1",
            "cdr2",
            "cdr3",
            "all_cdr",
            "fr1",
            "fr2",
            "fr3",
            "fr4",
            "all_fr",
        }:
            raise AssertionError(g.encoders.sequence.region)
        assert g.encoders.sequence.region in {"full", "groove_a1a2", "mask"}


def test_rejected_keeps_parent_json():
    g = default_genotype()
    child = apply_operator(g, "CHANGE_STRUCTURE", rng=np.random.default_rng(4))
    assert child.meta.operator_applied == "CHANGE_STRUCTURE_REJECTED"
    assert child.meta.generation == g.meta.generation
    parent_dump = dumps(g)
    child.meta.operator_applied = None
    assert dumps(child) == parent_dump


def test_mutate_single_uses_existing_mutation_operator_base():
    import asyncio

    from gigaevo.evolution.mutation.base import MutationOperator, MutationSpec
    from gigaevo.programs.program import Program
    from problems.pmhctcr.mutation_operator import PmhctcrMutationOperator

    op = PmhctcrMutationOperator()
    assert isinstance(op, MutationOperator)
    parent = Program(code=render_program(default_genotype()), iteration=0)

    async def _run():
        return await op.mutate_single([parent])

    spec = asyncio.run(_run())
    assert spec is not None
    assert isinstance(spec, MutationSpec)
    assert "def entrypoint" in spec.code
    assert "GENOTYPE_JSON" in spec.code
    child = loads_program(spec.code)
    assert child.meta.operator_applied in {
        *OPERATOR_IDS,
        *(f"{x}_REJECTED" for x in OPERATOR_IDS if x != "NOOP"),
    }
    assert (
        spec.metadata[MutationSpec.META_OUTPUT]["operator"]
        == child.meta.operator_applied
    )


def test_validate_accepts_genotype_json():
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path
    import sys

    problem_dir = Path(__file__).resolve().parents[2] / "problems" / "pmhctcr"
    sys.path.insert(0, str(problem_dir))
    spec = spec_from_file_location(
        "_pmhctcr_validate_json", problem_dir / "validate.py"
    )
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    metrics, art = module.validate(default_genotype().model_dump(mode="json"))
    assert metrics["is_valid"] == 1.0
    assert art["eval_fold"] == "val"


def test_num_heads_divides_hidden_dim_after_model_change():
    g = default_genotype()
    rng = np.random.default_rng(7)
    for _ in range(30):
        g = apply_operator(g, "CHANGE_MODEL", rng=rng)
        assert g.model.hidden_dim % g.model.num_heads == 0


def test_compile_and_score_seed_on_val():
    from problems.pmhctcr.dataset import feature_frame, load_folds
    from problems.pmhctcr.evaluate import score_fold

    folds = load_folds()
    pred = compile_genotype(default_genotype())
    pred.fit(folds["train"])
    scores = pred.score(feature_frame(folds["val"]))
    metrics, _ = score_fold(folds["val"], scores)
    assert metrics["is_valid"] == 1.0
    assert metrics["n_pmhc"] == 4.0
    assert 0.0 <= metrics["fitness"] <= 1.0


def test_temperature_does_not_change_ranking():
    from problems.pmhctcr.dataset import feature_frame, load_folds

    g = default_genotype()
    folds = load_folds()
    pred = compile_genotype(g)
    pred.fit(folds["train"])
    sa = pred.score(feature_frame(folds["val"]))
    pred.genotype.calibration.temperature = 2.5
    sb = pred.score(feature_frame(folds["val"]))
    # Temperature is a monotone map of probabilities, not a linear one.
    ra = pd.Series(sa).rank().to_numpy()
    rb = pd.Series(sb).rank().to_numpy()
    assert np.corrcoef(ra, rb)[0, 1] > 0.999
