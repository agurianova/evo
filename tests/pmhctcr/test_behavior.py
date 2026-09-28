from __future__ import annotations

from pathlib import Path

from hydra import compose, initialize_config_dir
from hydra.utils import instantiate
import numpy as np

from problems.pmhctcr.behavior import (
    INTERACTION_KIND_NAMES,
    MODALITY_MIX_NAMES,
    behavior_metrics,
    estimate_n_params,
    interaction_kind_name,
    modality_mix_name,
    used_modalities,
)
from problems.pmhctcr.genotype import default_genotype, dumps

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _clear_seq(g):
    g.inputs.sequence.peptide = False
    g.inputs.sequence.mhc = False
    g.inputs.sequence.tcr_alpha = False
    g.inputs.sequence.tcr_beta = False


def test_seed_is_sequence_none_interaction():
    g = default_genotype()
    assert modality_mix_name(g) == "sequence"
    assert interaction_kind_name(g) == "none"
    m = behavior_metrics(g)
    assert m["modality_mix"] == 0.0
    assert m["interaction_kind"] == 0.0
    assert m["compute_cost"] == m["n_params"]
    assert m["n_params"] > 1e5
    assert m["est_flops"] >= m["n_params"]


def test_compressed_modality_mix_from_inputs_and_model_type():
    cases = [
        ("sequence", dict(seq=True, pdb=False, masif=False, model="mlp_features")),
        ("structure", dict(seq=False, pdb=True, masif=False, model="pdb_gnn")),
        ("surface", dict(seq=False, pdb=False, masif=True, model="masif_siamese")),
        ("structure", dict(seq=True, pdb=True, masif=False, model="multimodal_mlp")),
        ("surface", dict(seq=True, pdb=False, masif=True, model="multimodal_gated")),
        ("structure+surface", dict(seq=False, pdb=True, masif=True, model="multimodal_mlp")),
        ("structure+surface", dict(seq=True, pdb=True, masif=True, model="multimodal_cross_attn")),
        ("structure", dict(seq=True, pdb=True, masif=False, model="pdb_gnn")),
        ("surface", dict(seq=True, pdb=False, masif=True, model="seq_dual_encoder")),
    ]
    for name, spec in cases:
        g = default_genotype()
        if not spec["seq"]:
            _clear_seq(g)
        g.inputs.pdb.present = spec["pdb"]
        g.inputs.pdb.kind = "complex" if spec["pdb"] else None
        g.inputs.masif.tcr_direct = spec["masif"]
        g.model.type = spec["model"]
        assert modality_mix_name(g) == name, (name, spec)
        assert int(behavior_metrics(g)["modality_mix"]) == MODALITY_MIX_NAMES.index(name)


def test_seq_dual_with_masif_maps_to_surface_cell():
    g = default_genotype()
    g.model.type = "seq_dual_encoder"
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True
    assert "sequence" in used_modalities(g)
    assert "surface" in used_modalities(g)
    assert modality_mix_name(g) == "surface"
    assert int(behavior_metrics(g)["modality_mix"]) == MODALITY_MIX_NAMES.index("surface")


def test_interaction_kind_priority():
    cases = [
        ("none", dict(pairs=[], method=None, fusion=None)),
        ("product", dict(pairs=["peptide_tcr"], method="product", fusion=None)),
        ("abs_diff", dict(pairs=["peptide_tcr"], method="abs_diff", fusion=None)),
        ("bilinear", dict(pairs=["peptide_tcr"], method="bilinear", fusion=None)),
        (
            "cross_attn_1pair",
            dict(pairs=["peptide_tcr"], method="cross_attention", fusion=None),
        ),
        (
            "cross_attn_multipair",
            dict(
                pairs=["peptide_tcr", "mhc_tcr"],
                method="cross_attention",
                fusion=None,
            ),
        ),
        (
            "fusion_gated",
            dict(pairs=["peptide_tcr"], method="cross_attention", fusion="gated_sum"),
        ),
        (
            "fusion_cross",
            dict(pairs=["peptide_tcr"], method="product", fusion="cross_attention"),
        ),
    ]
    for name, spec in cases:
        g = default_genotype()
        g.interaction.pairs = list(spec["pairs"])
        g.interaction.method = spec["method"]
        g.interaction.fusion = spec["fusion"]
        assert interaction_kind_name(g) == name, spec
        assert int(behavior_metrics(g)["interaction_kind"]) == INTERACTION_KIND_NAMES.index(
            name
        )


def test_se3_costs_more_than_gat_on_pdb_gnn():
    cheap = default_genotype()
    cheap.encoders.sequence.arch = "cnn"
    expensive = default_genotype()
    expensive.encoders.sequence.arch = "transformer"
    assert estimate_n_params(expensive) >= estimate_n_params(cheap)

    gnn = default_genotype()
    _clear_seq(gnn)
    gnn.inputs.pdb.present = True
    gnn.inputs.pdb.kind = "complex"
    gnn.model.type = "pdb_gnn"
    gat = gnn.model_copy(deep=True)
    gat.encoders.structure.arch = "gat"
    se3 = gnn.model_copy(deep=True)
    se3.encoders.structure.arch = "se3_transformer"
    assert estimate_n_params(se3) > estimate_n_params(gat)


def test_python_seed_defaults_to_sequence_only():
    m = behavior_metrics(object())
    assert m["modality_mix"] == 0.0
    assert m["interaction_kind"] == 0.0
    assert m["modality_count"] == 1.0
    assert m["arch_kind"] == 0.0
    assert m["compute_tier"] == 1.0
    assert m["compute_cost"] == 61.0


def test_python_predictor_reports_modalities_and_fitted_capacity():
    class FittedLogistic:
        coef_ = np.zeros((1, 256))
        intercept_ = np.zeros(1)

    class Predictor:
        active_modalities = ("sequence", "structure", "surface")
        model = FittedLogistic()

    metrics = behavior_metrics(Predictor())
    assert metrics["modality_count"] == 3.0
    assert metrics["modality_mix"] == 3.0
    assert metrics["arch_kind"] == 0.0
    assert metrics["n_params"] == 257.0
    assert metrics["compute_tier"] == 2.0


def test_python_pmhc_tcr_interaction_from_source_families():
    from problems.pmhctcr.behavior import (
        PMHC_TCR_INTERACTION_NAMES,
        _pmhc_tcr_interaction_from_source,
    )

    linear = (
        "class BindingPredictor:\n"
        "    def __init__(self):\n"
        "        self.interaction_family = 'global_concat'\n"
    )
    assert PMHC_TCR_INTERACTION_NAMES[_pmhc_tcr_interaction_from_source(linear)] == "global_concat"

    patch = """
class BindingPredictor:
    def __init__(self):
        self.interaction_family = 'explicit_patch_matching'
    def _features(self, df):
        return masif_complementarity_stats(tcr_desc, tcr_xyz, pmhc_desc, pmhc_xyz)
"""
    assert (
        PMHC_TCR_INTERACTION_NAMES[_pmhc_tcr_interaction_from_source(patch)]
        == "explicit_patch_matching"
    )

    bilinear = """
class BindingPredictor:
    def __init__(self):
        self.interaction_family = 'bilinear_product'
    def forward(self, a, b):
        return torch.einsum('bd,bd->b', a, b)
"""
    assert PMHC_TCR_INTERACTION_NAMES[_pmhc_tcr_interaction_from_source(bilinear)] == "bilinear_product"

    single = """
class BindingPredictor:
    def __init__(self):
        self.interaction_family = 'single_cross_attention'
        self.attn = torch.nn.MultiheadAttention(32, 4, batch_first=True)
"""
    assert (
        PMHC_TCR_INTERACTION_NAMES[_pmhc_tcr_interaction_from_source(single)]
        == "single_cross_attention"
    )

    dual = """
class BindingPredictor:
    def __init__(self):
        self.interaction_family = 'reciprocal_dual_attention'
    def forward(self, tcr_tokens, pmhc_tokens):
        a = self.attn_tcr_pmhc(tcr_tokens, pmhc_tokens, pmhc_tokens)
        b = self.attn_pmhc_tcr(pmhc_tokens, tcr_tokens, tcr_tokens)
"""
    assert (
        PMHC_TCR_INTERACTION_NAMES[_pmhc_tcr_interaction_from_source(dual)]
        == "reciprocal_dual_attention"
    )

    gated = """
class BindingPredictor:
    def __init__(self):
        self.interaction_family = 'multi_branch_gated'
        self.branch_gates = torch.nn.Linear(3, 3)
"""
    assert (
        PMHC_TCR_INTERACTION_NAMES[_pmhc_tcr_interaction_from_source(gated)]
        == "multi_branch_gated"
    )


def test_python_arch_kind_from_source_families():
    from problems.pmhctcr.behavior import ARCH_KIND_NAMES, _arch_kind_from_source

    linear = (
        "class BindingPredictor:\n"
        "    def __init__(self):\n"
        "        self.interaction_family = 'early_concat'\n"
    )
    assert ARCH_KIND_NAMES[_arch_kind_from_source(linear)] == "linear_mlp"

    modality = """
class ModalityAttention(torch.nn.Module):
    def __init__(self):
        self.attention = torch.nn.MultiheadAttention(32, 4, batch_first=True)
class BindingPredictor:
    def __init__(self):
        self.interaction_family = "modality_attention"
"""
    assert ARCH_KIND_NAMES[_arch_kind_from_source(modality)] == "modality_attention"

    geom = """
class BindingPredictor:
    def __init__(self):
        self.interaction_family = "structure_gnn_modality_attention"
    def fit(self, df):
        edge_index = knn_graph(xyz, k=8)
        h = gatconv(h, edge_index)
"""
    assert ARCH_KIND_NAMES[_arch_kind_from_source(geom)] == "geometric"

    interface = """
class BindingPredictor:
    def __init__(self):
        self.interaction_family = "masif_patch_cross_attn"
    def fit(self, df):
        tcr_tokens = proj(tcr_desc)
        pmhc_tokens = proj(pmhc_desc)
        out, _ = torch.nn.MultiheadAttention(32, 4)(tcr_tokens, pmhc_tokens, pmhc_tokens)
"""
    assert ARCH_KIND_NAMES[_arch_kind_from_source(interface)] == "interface_cross_attn"


def test_validate_attaches_behavior_keys():
    from importlib.util import module_from_spec, spec_from_file_location
    import json
    import sys

    problem_dir = Path(__file__).resolve().parents[2] / "problems" / "pmhctcr"
    sys.path.insert(0, str(problem_dir))
    spec = spec_from_file_location("_pmhctcr_validate_bd", problem_dir / "validate.py")
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    metrics, _ = module.validate(json.loads(dumps(default_genotype())))
    assert metrics["is_valid"] == 1.0
    assert metrics["modality_mix"] == 0.0
    assert metrics["interaction_kind"] == 0.0
    assert metrics["compute_cost"] > 0.0


def test_pmhctcr_map_elites_preset():
    from omegaconf import OmegaConf

    with initialize_config_dir(config_dir=str(CONFIG_DIR), version_base=None):
        cfg = compose(config_name="config", overrides=["experiment=pmhctcr"])
    assert list(cfg.behavior_space["keys"]) == ["modality_mix", "interaction_kind"]
    assert cfg.behavior_space.dynamic is False
    assert cfg.islands[0].max_size == 32
    space = instantiate(cfg.behavior_space)
    assert space.total_cells == 32
    for i, name in enumerate(MODALITY_MIX_NAMES):
        cell = space.get_cell({"modality_mix": float(i), "interaction_kind": 0.0})
        assert cell[0] == i, name
    for j, name in enumerate(INTERACTION_KIND_NAMES):
        cell = space.get_cell({"modality_mix": 0.0, "interaction_kind": float(j)})
        assert cell[1] == j, name
    seed_cell = space.get_cell({"modality_mix": 0.0, "interaction_kind": 0.0})
    surface_cell = space.get_cell({"modality_mix": 1.0, "interaction_kind": 0.0})
    cross_cell = space.get_cell({"modality_mix": 0.0, "interaction_kind": 4.0})
    assert seed_cell != surface_cell
    assert seed_cell != cross_cell
    assert surface_cell != cross_cell
    assert cfg.max_insights == 1
    assert cfg.program_format.id == "python_source"
    assert cfg.loader.pattern == "seed.py"
    raw = OmegaConf.to_container(cfg, resolve=False)
    assert raw["prompts"]["dir"] == "${problem.dir}/prompts"


def test_pmhctcr_python_patch_final_map_elites_preset():
    with initialize_config_dir(config_dir=str(CONFIG_DIR), version_base=None):
        cfg = compose(
            config_name="config",
            overrides=["experiment=pmhctcr_python_patch_final"],
        )
        assert list(cfg.behavior_space["keys"]) == ["pmhc_tcr_interaction", "compute_tier"]
        assert cfg.islands[0].max_size == 36
        assert cfg.problem_context.expert_hypotheses_enabled is True
        space = instantiate(cfg.behavior_space)
        assert space.total_cells == 36
        assert space.get_cell({"pmhc_tcr_interaction": 0.0, "compute_tier": 0.0}) == (0, 0)
        assert space.get_cell({"pmhc_tcr_interaction": 5.0, "compute_tier": 5.0}) == (5, 5)

        cfg_off = compose(
            config_name="config",
            overrides=[
                "experiment=pmhctcr_python_patch_final",
                "expert_prompt=disabled",
            ],
        )
        assert cfg_off.problem_context.expert_hypotheses_enabled is False


def test_pmhctcr_python_patch_map_elites_preset():
    with initialize_config_dir(config_dir=str(CONFIG_DIR), version_base=None):
        cfg = compose(config_name="config", overrides=["experiment=pmhctcr_python_patch"])
    assert list(cfg.behavior_space["keys"]) == ["arch_kind", "compute_tier"]
    assert cfg.islands[0].max_size == 24
    assert cfg.loader.pattern == "python_patch_seed.py"
    assert cfg.pipeline.id == "memory_guided"
    assert cfg.pipeline.reads_external_memory is True
    assert (
        cfg.memory.provider._target_
        == "gigaevo.memory_v2.provider.CausalBanditMemoryProvider"
    )
    assert cfg.memory.capabilities.read is True
    assert cfg.memory.capabilities.write is True
    assert cfg.memory.write.enabled is True
    assert cfg.memory.writer.authoring_enabled is True
    assert cfg.memory.writer.require_archive_or_positive_gain is False
    assert (
        cfg.post_step_hook._target_
        == "gigaevo.memory.live_memory_hook.LiveMemoryRefreshHook"
    )
    assert (
        cfg.pipeline_builder._target_
        == "problems.pmhctcr.pipeline.PmhctcrMemoryGuidedPipelineBuilder"
    )
    space = instantiate(cfg.behavior_space)
    assert space.total_cells == 24
    assert space.get_cell({"arch_kind": 0.0, "compute_tier": 0.0}) == (0, 0)
    assert space.get_cell({"arch_kind": 3.0, "compute_tier": 5.0}) == (3, 5)


def test_protein_lm_does_not_count_frozen_esm_as_trainable():
    from problems.pmhctcr.repair import repair

    trans = estimate_n_params(default_genotype())
    g = default_genotype()
    g.encoders.sequence.arch = "protein_lm"
    g = repair(g)
    n = estimate_n_params(g)
    assert n < 7_000_000
    # Frozen cache replaces the from-scratch transformer, so the estimate drops.
    assert n < trans
