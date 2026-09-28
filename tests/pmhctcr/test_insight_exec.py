from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from gigaevo.evolution.mutation.base import MutationSpec
from gigaevo.evolution.mutation.constants import MUTATION_CONTEXT_METADATA_KEY
from gigaevo.evolution.mutation.context import InsightsMutationContext
from gigaevo.llm.agents.insights import ProgramInsight, ProgramInsights
from gigaevo.programs.program import Program
from gigaevo.prompts import MutationSuggestionsPrompts, load_prompt
from problems.pmhctcr.codegen import loads_program, render_program
from problems.pmhctcr.genotype import default_genotype, functional_dumps, surface_on
from problems.pmhctcr.insight_exec import (
    map_operator,
    parse_primary_insight,
)
from problems.pmhctcr.mutation_operator import PmhctcrMutationOperator
from problems.pmhctcr.operators import apply_operator


def _insight_context(**kwargs) -> str:
    insight = ProgramInsight(
        type=kwargs.get("type", "missing_modality"),
        tag=kwargs.get("tag", "harmful"),
        severity=kwargs.get("severity", "high"),
        anchor_quote=kwargs.get("anchor_quote", '"tcr_direct": false'),
        evidence_source="program",
        mechanism=kwargs.get("mechanism", "surface pathway is off"),
        substitute=kwargs.get(
            "substitute",
            "OPERATOR=CREATE_SURFACE; enable masif.tcr_direct and masif.pmhc_flipped",
        ),
    )
    return InsightsMutationContext(
        insights=ProgramInsights(insights=[insight])
    ).format()


def test_parse_and_map_create_surface_from_operator_token():
    ctx = _insight_context()
    insight = parse_primary_insight(ctx)
    assert insight is not None
    assert insight.substitute.startswith("OPERATOR=CREATE_SURFACE")
    g = default_genotype()
    assert map_operator(insight, g) == "CREATE_SURFACE"


def test_map_masif_keywords_without_operator_token():
    ctx = _insight_context(
        substitute="turn on masif.tcr_direct / tcr.npz patches",
        mechanism="MaSIF surface descriptors are unused",
    )
    insight = parse_primary_insight(ctx)
    assert insight is not None
    assert map_operator(insight, default_genotype()) == "CREATE_SURFACE"


def test_guided_create_surface_turns_masif_on():
    g = default_genotype()
    child = apply_operator(
        g,
        "CREATE_SURFACE",
        guided_text="OPERATOR=CREATE_SURFACE; enable masif",
    )
    assert child.meta.operator_applied == "CREATE_SURFACE"
    assert surface_on(child)
    assert child.inputs.masif.tcr_direct is True
    assert child.inputs.masif.pmhc_flipped is True


def test_guided_interaction_sets_cross_attention():
    g = default_genotype()
    child = apply_operator(
        g,
        "CHANGE_INTERACTION",
        guided_text=(
            "OPERATOR=CHANGE_INTERACTION; set interaction.method to "
            "cross_attention and add pair peptide_tcr"
        ),
    )
    assert child.meta.operator_applied == "CHANGE_INTERACTION"
    assert child.interaction.method == "cross_attention"
    assert "peptide_tcr" in child.interaction.pairs
    assert child.model.type == "seq_cross_encoder"


def test_guided_interaction_method_without_pair_keeps_cross_attention():
    g = default_genotype()
    child = apply_operator(
        g,
        "CHANGE_INTERACTION",
        guided_text="OPERATOR=CHANGE_INTERACTION; set interaction.method to cross_attention",
    )
    assert child.meta.operator_applied == "CHANGE_INTERACTION"
    assert child.interaction.method == "cross_attention"
    assert child.interaction.pairs
    assert child.interaction.fusion is not None
    assert child.model.type == "seq_cross_encoder"


def test_mutate_single_executes_primary_llm_insight():
    parent = Program(
        code=render_program(default_genotype()),
        iteration=0,
        metadata={MUTATION_CONTEXT_METADATA_KEY: _insight_context()},
    )
    op = PmhctcrMutationOperator()

    async def _run():
        return await op.mutate_single([parent])

    spec = asyncio.run(_run())
    assert spec is not None
    assert "def entrypoint" in spec.code
    assert "GENOTYPE_JSON" in spec.code
    child = loads_program(spec.code)
    assert child.meta.operator_applied == "CREATE_SURFACE"
    assert child.inputs.masif.tcr_direct is True
    assert child.inputs.masif.pmhc_flipped is True
    assert spec.metadata["pmhctcr_guided"] is True
    assert spec.metadata[MutationSpec.META_OUTPUT]["insights_used"] == [
        "missing_modality"
    ]


def test_mutate_single_falls_back_to_scheduler_without_insights():
    parent = Program(code=render_program(default_genotype()), iteration=0)
    op = PmhctcrMutationOperator()

    async def _run():
        return await op.mutate_single([parent])

    spec = asyncio.run(_run())
    assert spec is not None
    assert spec.metadata["pmhctcr_guided"] is False
    assert "def entrypoint" in spec.code
    child = loads_program(spec.code)
    assert child.meta.operator_applied is not None


def test_mutation_suggestions_prompt_asks_for_one_operator_step():
    prompts_dir = (
        Path(__file__).resolve().parents[2] / "problems" / "pmhctcr" / "prompts"
    )
    text = load_prompt("mutation_suggestions", "system", prompts_dir=prompts_dir)
    assert "one most important next step" in text
    assert "OPERATOR=<ID>" in text
    assert "GENOTYPE_JSON" in text
    assert "CREATE_SURFACE" in text
    assert "CHANGE_SURFACE" in text
    assert "turns MaSIF on" in text
    filled = MutationSuggestionsPrompts.system(prompts_dir=prompts_dir).format(
        task_description="task",
        metrics_description="metrics",
        max_insights=1,
    )
    assert "list of length 1" in filled
    assert "{max_insights}" not in filled


def test_guided_create_surface_when_already_on_is_rejected():
    g = default_genotype()
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True
    child = apply_operator(
        g,
        "CREATE_SURFACE",
        guided_text="OPERATOR=CREATE_SURFACE; enable masif.tcr_direct and masif.pmhc_flipped",
    )
    assert child.meta.operator_applied == "CREATE_SURFACE_REJECTED"


def test_map_create_surface_not_remapped_when_already_on():
    g = default_genotype()
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True
    insight = parse_primary_insight(_insight_context())
    assert insight is not None
    assert map_operator(insight, g) is None


def test_map_create_surface_to_change_surface_only_for_spots():
    g = default_genotype()
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True
    insight = parse_primary_insight(
        _insight_context(
            substitute="OPERATOR=CREATE_SURFACE; enable complementary spots at NN L2 1.7"
        )
    )
    assert insight is not None
    assert map_operator(insight, g) == "CHANGE_SURFACE"


def test_guided_change_surface_enables_spots():
    g = default_genotype()
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True
    child = apply_operator(
        g,
        "CHANGE_SURFACE",
        guided_text="OPERATOR=CHANGE_SURFACE; enable complementary spots at NN L2 1.7",
    )
    assert child.meta.operator_applied == "CHANGE_SURFACE"
    assert child.encoders.surface.spots.enabled is True
    assert child.encoders.surface.spots.metric == "l2"
    assert child.encoders.surface.spots.threshold == pytest.approx(1.7)


def test_guided_interaction_keeps_concat_when_method_is_cross():
    g = default_genotype()
    child = apply_operator(
        g,
        "CHANGE_INTERACTION",
        guided_text=(
            "OPERATOR=CHANGE_INTERACTION; set interaction.method to "
            "cross_attention, interaction.fusion to concat, pair peptide_tcr"
        ),
    )
    assert child.meta.operator_applied == "CHANGE_INTERACTION"
    assert child.interaction.method == "cross_attention"
    assert child.interaction.fusion == "concat"
    assert "peptide_tcr" in child.interaction.pairs


def test_guided_interaction_fusion_cross_only_when_fusion_named():
    g = default_genotype()
    child = apply_operator(
        g,
        "CHANGE_INTERACTION",
        guided_text=(
            "OPERATOR=CHANGE_INTERACTION; set interaction.fusion to "
            "cross_attention and add pair peptide_tcr"
        ),
    )
    assert child.interaction.fusion == "cross_attention"


def test_mutate_single_does_not_retrain_identical_create_surface():
    parent = Program(
        code=render_program(default_genotype()),
        iteration=0,
        metadata={MUTATION_CONTEXT_METADATA_KEY: _insight_context()},
    )
    op = PmhctcrMutationOperator()

    async def _run():
        first = await op.mutate_single([parent])
        second = await op.mutate_single([parent])
        return first, second

    spec1, spec2 = asyncio.run(_run())
    assert spec1 is not None
    assert spec2 is not None
    assert "def entrypoint" in spec1.code
    child1 = loads_program(spec1.code)
    child2 = loads_program(spec2.code)
    assert child1.meta.operator_applied == "CREATE_SURFACE"
    assert spec1.metadata["pmhctcr_guided"] is True
    assert child2.meta.operator_applied != "CREATE_SURFACE"
    assert spec2.metadata["pmhctcr_guided"] is False
    assert functional_dumps(child1) != functional_dumps(child2)
    assert functional_dumps(child1) != functional_dumps(default_genotype())


def test_mutate_single_spent_insight_does_not_return_none_thirty_two_times():
    parent = Program(
        code=render_program(default_genotype()),
        iteration=0,
        metadata={MUTATION_CONTEXT_METADATA_KEY: _insight_context()},
    )
    op = PmhctcrMutationOperator()

    async def _run():
        specs = []
        for _ in range(32):
            specs.append(await op.mutate_single([parent]))
        return specs

    specs = asyncio.run(_run())
    assert specs[0] is not None
    assert loads_program(specs[0].code).meta.operator_applied == "CREATE_SURFACE"
    empties = sum(1 for spec in specs if spec is None)
    assert empties < 32
    assert any(spec is not None and not spec.metadata["pmhctcr_guided"] for spec in specs[1:])


def test_guided_training_sets_lr_not_a_random_loss():
    g = default_genotype()
    g.training.loss = "bce"
    g.training.lr = 1e-3
    child = apply_operator(
        g,
        "CHANGE_TRAINING",
        guided_text="OPERATOR=CHANGE_TRAINING; set lr to 1e-4",
    )
    assert child.training.loss == "bce"
    assert child.training.lr == pytest.approx(1e-4)


def test_guided_dropout_parses_number_instead_of_shrinking():
    g = default_genotype()
    g.model.dropout = 0.1
    child = apply_operator(
        g,
        "CHANGE_MODEL",
        guided_text="OPERATOR=CHANGE_MODEL; set dropout to 0.3",
    )
    assert child.model.dropout == pytest.approx(0.3)
    assert child.model.type == g.model.type


def test_guided_sequence_arch_promotes_mlp_to_seq_dual():
    g = default_genotype()
    assert g.model.type == "mlp_features"
    child = apply_operator(
        g,
        "CHANGE_SEQUENCE",
        guided_text="OPERATOR=CHANGE_SEQUENCE; set encoders.sequence.arch to cnn",
    )
    assert child.encoders.sequence.arch == "cnn"
    assert child.model.type == "seq_dual_encoder"


def test_guided_sequence_protein_lm_uses_esm_cache_flag():
    g = default_genotype()
    child = apply_operator(
        g,
        "CHANGE_SEQUENCE",
        guided_text="OPERATOR=CHANGE_SEQUENCE; set encoders.sequence.arch to protein_lm",
    )
    assert child.encoders.sequence.arch == "protein_lm"
    assert child.encoders.sequence.pretrained is True
    assert child.model.type == "mlp_features"


def test_guided_unparsed_does_not_randomize_sibling_field():
    g = default_genotype()
    loss = g.training.loss
    lr = g.training.lr
    child = apply_operator(
        g,
        "CHANGE_TRAINING",
        guided_text="OPERATOR=CHANGE_TRAINING; please think about the schedule in general",
    )
    assert child.training.loss == loss
    assert child.training.lr == lr
    assert child.meta.operator_applied == "CHANGE_TRAINING_REJECTED"


def test_pdb_gnn_without_pdb_is_repaired_to_mlp():
    from problems.pmhctcr.repair import repair

    g = default_genotype()
    g.model.type = "pdb_gnn"
    assert not g.inputs.pdb.present
    fixed = repair(g)
    assert fixed.model.type == "mlp_features"


def test_guided_change_input_sets_peptide_flag():
    g = default_genotype()
    g.inputs.sequence.peptide = False
    child = apply_operator(
        g,
        "CHANGE_INPUT",
        guided_text="OPERATOR=CHANGE_INPUT; set inputs.sequence.peptide to true",
    )
    assert child.meta.operator_applied == "CHANGE_INPUT"
    assert child.inputs.sequence.peptide is True
    assert child.inputs.sequence.mhc is True
    assert child.inputs.sequence.tcr_alpha is True
    assert child.inputs.sequence.tcr_beta is True
    assert child.inputs.masif.tcr_direct is False


def test_guided_change_input_already_true_is_rejected():
    g = default_genotype()
    assert g.inputs.sequence.peptide is True
    child = apply_operator(
        g,
        "CHANGE_INPUT",
        guided_text="OPERATOR=CHANGE_INPUT; set inputs.sequence.peptide to true",
    )
    assert child.meta.operator_applied == "CHANGE_INPUT_REJECTED"
    assert child.inputs.sequence.peptide is True
    assert child.inputs.sequence.tcr_alpha is True


def test_mutate_single_does_not_ucb_fallback_when_insight_is_noop():
    parent = Program(
        code=render_program(default_genotype()),
        iteration=0,
        metadata={
            MUTATION_CONTEXT_METADATA_KEY: _insight_context(
                type="redundant_input",
                substitute="OPERATOR=CHANGE_INPUT; set inputs.sequence.peptide to true",
                mechanism="peptide channel already on",
                anchor_quote='"peptide": true',
            )
        },
    )
    op = PmhctcrMutationOperator()

    async def _run():
        return await op.mutate_single([parent])

    assert asyncio.run(_run()) is None


def test_guided_model_seq_dual():
    g = default_genotype()
    child = apply_operator(
        g,
        "CHANGE_MODEL",
        guided_text="OPERATOR=CHANGE_MODEL; set model.type to seq_dual_encoder",
    )
    assert child.meta.operator_applied == "CHANGE_MODEL"
    assert child.model.type == "seq_dual_encoder"


def test_guided_surface_derived_ratio():
    g = default_genotype()
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True
    child = apply_operator(
        g,
        "CHANGE_SURFACE",
        guided_text="OPERATOR=CHANGE_SURFACE; add derived ratio cdr3_frac / area_frac",
    )
    assert child.meta.operator_applied == "CHANGE_SURFACE"
    assert child.encoders.surface.spots.enabled is True
    ops = {(d.op, d.a, d.b) for d in child.encoders.surface.spots.derived}
    assert ("ratio", "cdr3_frac", "area_frac") in ops


def test_guided_change_input_does_not_enable_masif():
    g = default_genotype()
    child = apply_operator(
        g,
        "CHANGE_INPUT",
        guided_text="OPERATOR=CHANGE_INPUT; enable masif.tcr_direct",
    )
    assert child.meta.operator_applied == "CHANGE_INPUT_REJECTED"
    assert child.inputs.masif.tcr_direct is False


def test_map_pdb_gnn_is_change_model_not_structure():
    ctx = _insight_context(
        substitute="train a pdb_gnn GAT on the Cα graph",
        mechanism="learned graph encoder",
        type="missing_encoder",
        anchor_quote='"type": "mlp_features"',
    )
    insight = parse_primary_insight(ctx)
    assert insight is not None
    g = default_genotype()
    g.inputs.pdb.present = True
    g.inputs.pdb.kind = "complex"
    assert map_operator(insight, g) == "CHANGE_MODEL"
