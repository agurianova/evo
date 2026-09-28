from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil

import numpy as np
import pytest
from hydra import compose, initialize_config_dir
from hydra.utils import instantiate

from problems.tab_wpf.graph import PredictorGraph
from problems.tab_wpf.problem_context import TabWpfProblemContext
from problems.tab_wpf.synthetic_evaluation import (
    evaluate_synthetic_suite,
    predict_episode,
    predictor_episode,
)
from problems.tab_wpf.synthetic_tasks import (
    FAMILIES,
    META_TEST,
    META_TRAIN,
    META_VALID,
    _generate_task,
    generate_task_bank,
    iter_tasks,
    load_task,
    verify_task_bank,
)

ROOT = Path(__file__).parents[2]
CONFIG_DIR = ROOT / "config"
SEED = ROOT / "problems/tab_wpf/initial_programs/baseline.json"


def _baseline() -> PredictorGraph:
    return PredictorGraph.model_validate_json(SEED.read_text())


@pytest.fixture(scope="module")
def task_bank(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("tab_wpf_bank") / "synthetic_v1"
    generate_task_bank(root)
    return root


def test_generator_is_deterministic_for_one_task():
    first_metadata, first_arrays = _generate_task(
        3, 7, master_seed=20260819, attempt=0
    )
    second_metadata, second_arrays = _generate_task(
        3, 7, master_seed=20260819, attempt=0
    )
    assert first_metadata == second_metadata
    for name in first_arrays:
        assert np.array_equal(first_arrays[name], second_arrays[name], equal_nan=True)


def test_bank_has_exact_balanced_outer_split_and_checksums(task_bank):
    manifest = verify_task_bank(task_bank)
    assert manifest["task_count"] == 100
    assert manifest["split_counts"] == {
        META_TRAIN: 60,
        META_VALID: 20,
        META_TEST: 20,
    }
    assert manifest["family_counts"] == {family: 10 for family in FAMILIES}
    assert len(manifest["bank_checksum"]) == 64
    assert len(manifest["generator_source_sha256"]) == 64


def test_feature_provenance_follows_runtime_column_order(task_bank):
    mixed_record = next(
        record
        for record in verify_task_bank(task_bank)["tasks"]
        if record["family"] == "mixed_feature_types"
    )
    task = load_task(task_bank, mixed_record)
    observed = task.metadata["generator"]["observed_features"]
    assert len(observed) == len(task.columns)
    for index, (source, column) in enumerate(zip(observed, task.columns)):
        assert source["column_index"] == index
        assert source["kind"] == column.kind


@pytest.mark.parametrize("family_index", [0, FAMILIES.index("missing_heavy_tail")])
def test_target_parents_are_observed_and_requested_context_snr_is_realized(
    family_index,
):
    metadata, _ = _generate_task(
        family_index,
        3,
        master_seed=20260819,
        attempt=0,
    )
    generator = metadata["generator"]
    target_node = next(
        node for node in generator["nodes"] if node["id"] == generator["target_node"]
    )
    observed_node_ids = {
        source.get("node_id") for source in generator["observed_features"]
    }
    assert set(target_node["parents"]) <= observed_node_ids
    assert generator["observed_target_parent_count"] == len(target_node["parents"])

    postprocess = generator["target_postprocess"]
    assert postprocess["realized_context_signal_r2"] == pytest.approx(
        postprocess["requested_signal_r2"], abs=1e-12
    )


def test_loaded_predictor_episode_drops_query_target_and_hidden_generator(task_bank):
    task = next(iter_tasks(task_bank, meta_split=META_VALID))
    episode = predictor_episode(task)
    assert not hasattr(episode, "y_query")
    assert not hasattr(episode, "metadata")
    assert not hasattr(episode, "family")

    first, _ = predict_episode(_baseline(), episode, seed=11)
    changed_task = replace(task, y_query=np.asarray(task.y_query) + 10_000.0)
    second, _ = predict_episode(
        _baseline(), predictor_episode(changed_task), seed=11
    )
    assert np.array_equal(first, second)


def test_baseline_evaluates_finite_query_scores(task_bank):
    metrics, artifact = evaluate_synthetic_suite(
        _baseline(),
        task_bank,
        meta_split=META_VALID,
    )
    assert metrics["is_valid"] == 1.0
    assert metrics["evaluated_task_count"] == 20.0
    assert metrics["valid_task_rate"] == 1.0
    assert -1.0 <= metrics["fitness"] <= 1.0
    assert all(np.isfinite(float(value)) for value in metrics.values())
    assert artifact["score_unit"] == "synthetic_task"
    assert len(artifact["_program_metadata"]["per_sample_scores"]) == 20
    assert len(artifact["_program_metadata"]["per_sample_signature"]) == 64
    assert artifact["_evaluation_measurements"]["fitness"]["n"] == 20


def test_meta_test_is_sealed_without_explicit_reporting_opt_in(task_bank):
    with pytest.raises(PermissionError, match="sealed"):
        evaluate_synthetic_suite(
            _baseline(),
            task_bank,
            meta_split=META_TEST,
        )


def test_manifest_tampering_is_detected(task_bank, tmp_path):
    manifest = json.loads((task_bank / "manifest.json").read_text())
    manifest["master_seed"] += 1
    tampered = tmp_path / "tampered"
    tampered.mkdir()
    (tampered / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="manifest checksum mismatch"):
        verify_task_bank(tampered)


def test_task_metadata_tampering_is_detected(task_bank, tmp_path):
    tampered = tmp_path / "tampered_task_bank"
    shutil.copytree(task_bank, tampered)
    manifest = json.loads((tampered / "manifest.json").read_text())
    task_path = tampered / manifest["tasks"][0]["task_dir"] / "task.json"
    metadata = json.loads(task_path.read_text())
    metadata["replica"] += 1
    task_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_task_bank(tampered)


def test_synthetic_hydra_preset_routes_problem_context(monkeypatch, task_bank):
    monkeypatch.setenv("GIGAEVO_TAB_WPF_TASK_BANK", str(task_bank))
    with initialize_config_dir(config_dir=str(CONFIG_DIR), version_base=None):
        cfg = compose(config_name="config", overrides=["experiment=tab_wpf_synthetic"])
    assert cfg.problem.name == "tab_wpf"
    assert cfg.problem.evaluation_mode == "synthetic"
    assert cfg.problem.task_split == META_TRAIN
    assert Path(cfg.problem.task_bank) == task_bank
    assert list(cfg.behavior_space["keys"]) == [
        "graph_node_count",
        "graph_max_depth",
    ]
    assert cfg.behavior_space.dynamic is False
    assert cfg.islands[0].max_size == 79
    assert cfg.program_loader.evaluation_mode == "synthetic"
    assert Path(cfg.program_loader.task_bank) == task_bank
    behavior_space = instantiate(cfg.behavior_space)
    assert behavior_space.total_cells == 169
    assert behavior_space.get_cell(
        {"graph_node_count": 0.0, "graph_max_depth": 0.0}
    ) == (0, 0)
    assert behavior_space.get_cell(
        {"graph_node_count": 12.0, "graph_max_depth": 12.0}
    ) == (12, 12)


def test_synthetic_problem_context_fails_early_without_bank():
    with pytest.raises(ValueError, match="requires problem.task_bank"):
        TabWpfProblemContext(
            ROOT / "problems/tab_wpf",
            evaluation_mode="synthetic",
            task_bank=None,
        )


def test_synthetic_problem_context_exposes_protocol_not_hidden_tasks(task_bank):
    context = TabWpfProblemContext(
        ROOT / "problems/tab_wpf",
        evaluation_mode="synthetic",
        task_bank=task_bank,
        task_split=META_TRAIN,
    )
    description = context.task_description
    assert "60 frozen tasks" in description
    assert "X_context" in description
    assert "syn_f00" not in description
