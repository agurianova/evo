from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil

from hydra import compose, initialize_config_dir
import numpy as np
import pytest
from sklearn.model_selection import train_test_split

from problems.tab_wpf.graph import PredictorGraph
from problems.tab_wpf.problem_context import TabWpfProblemContext
from problems.tab_wpf.sandbox_evaluation import (
    evaluate_sandbox_suite,
    normalized_log_loss_score,
    predict_sandbox_episode,
    sandbox_predictor_episode,
)
from problems.tab_wpf.sandbox_tasks import (
    CATEGORICAL_FRACTIONS,
    CLASS_COUNT_CHOICES,
    CLASS_MARGINAL_TOLERANCE,
    ELIGIBLE_FEATURE_FRACTIONS,
    FAMILIES,
    FEATURE_CHOICES,
    MAX_CARDINALITY_CHOICES,
    META_TEST,
    META_TRAIN,
    META_VALID,
    MIN_CLASS_PROBABILITY_STD,
    NODE_COUNT_CHOICES,
    ORACLE_QUALITY_TARGETS,
    ORACLE_QUALITY_TOLERANCE,
    PILOT_TASKS_PER_PRIMARY_STRATUM,
    PRIMARY_STRATUM_COUNT,
    ROW_CHOICES,
    _generate_task,
    generate_sandbox_bank,
    iter_sandbox_tasks,
    load_sandbox_task,
    sample_sandbox_records,
    verify_sandbox_bank,
)
from problems.tab_wpf.validate import validate
from problems.tabular._common import tabular_data

ROOT = Path(__file__).parents[2]
CONFIG_DIR = ROOT / "config"
SEED = ROOT / "problems/tab_wpf/initial_programs/baseline.json"


def _baseline() -> PredictorGraph:
    return PredictorGraph.model_validate_json(SEED.read_text())


@pytest.fixture(scope="module")
def sandbox_bank(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("tab_wpf_sandbox") / "sandbox_v1"
    generate_sandbox_bank(
        root,
        tasks_per_primary_stratum=PILOT_TASKS_PER_PRIMARY_STRATUM,
        workers=16,
    )
    return root


@pytest.mark.parametrize("family_index", range(len(FAMILIES)))
def test_sandbox_generator_is_deterministic(family_index):
    for attempt in range(50):
        try:
            first_metadata, first_arrays = _generate_task(
                family_index,
                2,
                1,
                1,
                3,
                tasks_per_primary_stratum=PILOT_TASKS_PER_PRIMARY_STRATUM,
                master_seed=20260819,
                attempt=attempt,
            )
            break
        except ValueError:
            continue
    else:
        raise AssertionError("no valid deterministic generation attempt")
    second_metadata, second_arrays = _generate_task(
        family_index,
        2,
        1,
        1,
        3,
        tasks_per_primary_stratum=PILOT_TASKS_PER_PRIMARY_STRATUM,
        master_seed=20260819,
        attempt=attempt,
    )
    assert first_metadata == second_metadata
    for name in first_arrays:
        assert np.array_equal(first_arrays[name], second_arrays[name])


def test_sandbox_bank_is_exact_balanced_and_covers_parameter_support(sandbox_bank):
    manifest = verify_sandbox_bank(sandbox_bank)
    assert manifest["task_count"] == 1260
    assert manifest["primary_stratum_count"] == PRIMARY_STRATUM_COUNT == 252
    assert manifest["tasks_per_primary_stratum"] == 5
    assert manifest["family_counts"] == {family: 315 for family in FAMILIES}
    assert manifest["split_counts"] == {
        META_TRAIN: 756,
        META_VALID: 252,
        META_TEST: 252,
    }
    records = manifest["tasks"]
    assert {record["n_rows"] for record in records} == set(ROW_CHOICES)
    assert {record["n_features"] for record in records} == set(FEATURE_CHOICES)
    assert {record["n_classes"] for record in records} == set(CLASS_COUNT_CHOICES)

    requested_categorical = set()
    requested_cardinality = set()
    node_counts = set()
    for record in records:
        task = load_sandbox_task(sandbox_bank, record)
        requested_categorical.add(task.metadata["categorical_fraction_requested"])
        requested_cardinality.add(task.metadata["max_categorical_cardinality"])
        node_counts.add(task.metadata["generator"]["node_count"])
    assert requested_categorical == set(CATEGORICAL_FRACTIONS)
    assert requested_cardinality == set(MAX_CARDINALITY_CHOICES)
    assert node_counts == set(NODE_COUNT_CHOICES)

    for family in FAMILIES:
        for split in (META_VALID, META_TEST):
            selected = [
                record
                for record in records
                if record["family"] == family and record["meta_split"] == split
            ]
            selected_tasks = [
                load_sandbox_task(sandbox_bank, record) for record in selected
            ]
            assert {task.metadata["n_rows"] for task in selected_tasks} == set(
                ROW_CHOICES
            )
            assert {task.metadata["n_features"] for task in selected_tasks} == set(
                FEATURE_CHOICES
            )
            assert {task.n_classes for task in selected_tasks} == set(
                CLASS_COUNT_CHOICES
            )
            assert {
                task.metadata["generator"]["requested_oracle_quality"]
                for task in selected_tasks
            } == set(ORACLE_QUALITY_TARGETS)

    primary_strata = {}
    for record in records:
        primary_strata.setdefault(record["primary_stratum_id"], []).append(record)
    assert len(primary_strata) == PRIMARY_STRATUM_COUNT
    for stratum_records in primary_strata.values():
        assert len(stratum_records) == 5
        assert {
            split: sum(r["meta_split"] == split for r in stratum_records)
            for split in (META_TRAIN, META_VALID, META_TEST)
        } == {
            META_TRAIN: 3,
            META_VALID: 1,
            META_TEST: 1,
        }


def test_sandbox_sampler_is_deterministic_unique_and_family_balanced(sandbox_bank):
    first = sample_sandbox_records(
        sandbox_bank, meta_split=META_TRAIN, sample_size=64, sample_seed=17
    )
    second = sample_sandbox_records(
        sandbox_bank, meta_split=META_TRAIN, sample_size=64, sample_seed=17
    )
    assert [record["task_id"] for record in first] == [
        record["task_id"] for record in second
    ]
    assert len({record["task_id"] for record in first}) == 64
    assert {
        family: sum(record["family"] == family for record in first)
        for family in FAMILIES
    } == {family: 16 for family in FAMILIES}
    assert len({record["primary_stratum_id"] for record in first}) == 64

    with pytest.raises(ValueError, match="divisible by 4"):
        sample_sandbox_records(
            sandbox_bank, meta_split=META_TRAIN, sample_size=63, sample_seed=17
        )


def test_every_task_obeys_controlled_schema_and_productive_dag(sandbox_bank):
    manifest = verify_sandbox_bank(sandbox_bank)
    for record in manifest["tasks"]:
        task = load_sandbox_task(sandbox_bank, record)
        metadata = task.metadata
        assert metadata["n_rows"] == len(task.X_context) + len(task.X_query)
        assert metadata["n_rows"] in ROW_CHOICES
        assert metadata["n_features"] in FEATURE_CHOICES
        assert metadata["n_classes"] in CLASS_COUNT_CHOICES
        assert metadata["max_categorical_cardinality"] in MAX_CARDINALITY_CHOICES
        assert (
            abs(
                metadata["categorical_fraction_realized"]
                - metadata["categorical_fraction_requested"]
            )
            <= 1.0 / metadata["n_features"]
        )

        generator = metadata["generator"]
        nodes = generator["nodes"]
        assert len(nodes) == generator["node_count"]
        assert 2 <= len(nodes) <= 8
        assert generator["node_count_semantics"] == (
            "composition_blocks_including_class_logits"
        )
        assert len({node["id"] for node in nodes}) == len(nodes)
        hidden_ids = {node["id"] for node in nodes[:-1]}
        assert set(nodes[-1]["parents"]) == hidden_ids
        assert nodes[-1]["id"] == generator["output_node"] == "class_logits"
        assert nodes[-1]["op"] == "class_logits"
        available = {
            f"b{index}" for index in range(len(generator["basis_state"]["provenance"]))
        }
        for node in nodes[:-1]:
            assert node["parents"]
            assert len(node["parents"]) == len(set(node["parents"]))
            assert set(node["parents"]) <= available
            available.add(node["id"])

        assert generator["eligible_feature_fraction"] in ELIGIBLE_FEATURE_FRACTIONS
        assert set(generator["used_input_column_indices"]) <= set(
            generator["eligible_input_column_indices"]
        )
        assert generator["used_input_column_indices"]
        assert (
            abs(
                generator["realized_calibration_oracle_quality"]
                - generator["requested_oracle_quality"]
            )
            <= ORACLE_QUALITY_TOLERANCE
        )
        assert (
            generator["calibration_class_marginal_max_error"]
            <= CLASS_MARGINAL_TOLERANCE
        )
        assert (
            generator["minimum_calibration_class_probability_std"]
            >= MIN_CLASS_PROBABILITY_STD
        )

        if task.family != "mixed":
            assert {node["op"] for node in nodes[:-1]} == {task.family}
        else:
            assert len({node["op"] for node in nodes[:-1]} | {"linear"}) >= 2

        assert task.X_context.shape[1] == len(task.columns)
        assert task.X_query.shape[1] == len(task.columns)
        assert np.isfinite(task.X_context).all()
        assert np.isfinite(task.X_query).all()
        assert set(np.unique(np.concatenate([task.y_context, task.y_query]))) == set(
            range(task.n_classes)
        )
        assert np.bincount(task.y_context, minlength=task.n_classes).min() >= 15
        assert np.bincount(task.y_query, minlength=task.n_classes).min() >= 5
        assert task.task_type == (
            tabular_data.BINCLASS if task.n_classes == 2 else tabular_data.MULTICLASS
        )
        assert (
            metadata["class_counts_context"]
            == np.bincount(task.y_context, minlength=task.n_classes).tolist()
        )
        assert (
            metadata["class_counts_query"]
            == np.bincount(task.y_query, minlength=task.n_classes).tolist()
        )

        for column in task.columns:
            values = np.concatenate(
                [task.X_context[:, column.index], task.X_query[:, column.index]]
            )
            if column.kind == "categorical":
                assert column.cardinality is not None
                assert (
                    2 <= column.cardinality <= metadata["max_categorical_cardinality"]
                )
                assert np.array_equal(values, values.astype(int))
                assert int(values.min()) >= 0
                assert int(values.max()) < column.cardinality
                assert (
                    np.bincount(
                        task.X_context[:, column.index].astype(int),
                        minlength=column.cardinality,
                    ).min()
                    >= 5
                )
                assert set(task.X_query[:, column.index].astype(int)) <= set(
                    task.X_context[:, column.index].astype(int)
                )
        categorical = [
            column for column in task.columns if column.kind == "categorical"
        ]
        if categorical:
            assert (
                max(column.cardinality for column in categorical)
                == metadata["max_categorical_cardinality"]
            )


def test_actual_inner_split_retains_every_class(sandbox_bank):
    for task in iter_sandbox_tasks(sandbox_bank, meta_split=META_TRAIN):
        indices = np.arange(len(task.y_context))
        fit_idx, val_idx = train_test_split(
            indices,
            test_size=0.2,
            random_state=int.from_bytes(
                __import__("hashlib").sha256(task.task_id.encode()).digest()[:4],
                "little",
            ),
            shuffle=True,
            stratify=task.y_context,
        )
        expected = set(range(task.n_classes))
        assert set(task.y_context[fit_idx]) == expected
        assert set(task.y_context[val_idx]) == expected


def test_predictor_boundary_drops_query_labels_and_hidden_generator(sandbox_bank):
    task = next(iter_sandbox_tasks(sandbox_bank, meta_split=META_VALID))
    episode = sandbox_predictor_episode(task)
    assert not hasattr(episode, "y_query")
    assert not hasattr(episode, "metadata")
    assert not hasattr(episode, "family")

    first, _ = predict_sandbox_episode(_baseline(), episode, seed=19)
    poisoned = replace(task, y_query=np.full_like(task.y_query, -99))
    second, _ = predict_sandbox_episode(
        _baseline(), sandbox_predictor_episode(poisoned), seed=19
    )
    assert np.array_equal(first, second)


@pytest.mark.parametrize("n_classes", [2, 5])
def test_prediction_probability_contract(sandbox_bank, n_classes):
    task = next(
        task
        for task in iter_sandbox_tasks(sandbox_bank, meta_split=META_TRAIN)
        if task.n_classes == n_classes
    )
    probabilities, _ = predict_sandbox_episode(
        _baseline(), sandbox_predictor_episode(task), seed=23
    )
    assert probabilities.shape == (len(task.X_query), n_classes)
    assert np.isfinite(probabilities).all()
    assert (probabilities >= 0.0).all()
    assert (probabilities <= 1.0).all()
    assert np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-10)


def test_prediction_is_query_batch_and_order_invariant(sandbox_bank):
    task = next(iter_sandbox_tasks(sandbox_bank, meta_split=META_VALID))
    episode = sandbox_predictor_episode(task)
    reference, _ = predict_sandbox_episode(_baseline(), episode, seed=29)

    augmented = replace(
        episode, X_query=np.concatenate([episode.X_query, episode.X_query[:7]])
    )
    augmented_probabilities, _ = predict_sandbox_episode(
        _baseline(), augmented, seed=29
    )
    assert np.allclose(augmented_probabilities[: len(reference)], reference)

    order = np.arange(len(episode.X_query))[::-1]
    reordered = replace(episode, X_query=episode.X_query[order])
    reordered_probabilities, _ = predict_sandbox_episode(
        _baseline(), reordered, seed=29
    )
    assert np.allclose(reordered_probabilities[::-1], reference)


def test_normalized_log_loss_has_zero_context_prior_and_near_one_perfect():
    y_context = np.tile(np.arange(3), 20)
    y_query = np.tile(np.arange(3), 10)
    uniform = np.full((len(y_query), 3), 1.0 / 3.0)
    score, model_loss, prior_loss = normalized_log_loss_score(
        y_query, uniform, y_context=y_context, n_classes=3
    )
    assert score == pytest.approx(0.0, abs=1e-12)
    assert model_loss == pytest.approx(prior_loss, abs=1e-12)

    perfect = np.full((len(y_query), 3), 5e-7)
    perfect[np.arange(len(y_query)), y_query] = 1.0 - 1e-6
    perfect_score, _, _ = normalized_log_loss_score(
        y_query, perfect, y_context=y_context, n_classes=3
    )
    assert perfect_score > 0.999

    imbalanced_context = np.asarray([0] * 50 + [1] * 8 + [2] * 2)
    imbalanced_query = np.asarray([0] * 12 + [1] * 7 + [2] * 11)
    counts = np.bincount(imbalanced_context, minlength=3)
    laplace_prior = (counts + 1.0) / (counts.sum() + 3)
    prior_predictions = np.tile(laplace_prior, (len(imbalanced_query), 1))
    imbalanced_score, imbalanced_loss, imbalanced_prior_loss = (
        normalized_log_loss_score(
            imbalanced_query,
            prior_predictions,
            y_context=imbalanced_context,
            n_classes=3,
        )
    )
    assert imbalanced_score == pytest.approx(0.0, abs=1e-12)
    assert imbalanced_loss == pytest.approx(imbalanced_prior_loss, abs=1e-12)


def test_baseline_evaluates_balanced_meta_valid_cohort(sandbox_bank):
    metrics, artifact = evaluate_sandbox_suite(
        _baseline(),
        sandbox_bank,
        meta_split=META_VALID,
        sample_size=64,
        sample_seed=31,
    )
    assert metrics["is_valid"] == 1.0
    assert metrics["valid_task_rate"] == 1.0
    assert metrics["evaluated_task_count"] == 64.0
    assert -1.0 <= metrics["fitness"] <= 1.0
    assert all(np.isfinite(float(value)) for value in metrics.values())
    assert artifact["score_unit"] == "synthetic_classification_task"
    assert artifact["sampling"] == {
        "mode": "balanced_cohort",
        "sample_seed": 31,
    }
    assert len(artifact["_program_metadata"]["per_sample_scores"]) == 64
    assert len(artifact["_program_metadata"]["per_sample_signature"]) == 64
    assert artifact["_evaluation_measurements"]["fitness"]["n"] == 64


def test_sandbox_meta_test_is_sealed(sandbox_bank):
    with pytest.raises(PermissionError, match="sealed"):
        evaluate_sandbox_suite(_baseline(), sandbox_bank, meta_split=META_TEST)


def test_sandbox_manifest_tampering_is_detected(sandbox_bank, tmp_path):
    manifest = json.loads((sandbox_bank / "manifest.json").read_text())
    manifest["master_seed"] += 1
    tampered = tmp_path / "tampered_manifest"
    tampered.mkdir()
    (tampered / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="manifest checksum mismatch"):
        verify_sandbox_bank(tampered)


def test_sandbox_task_tampering_is_detected(sandbox_bank, tmp_path):
    tampered = tmp_path / "tampered_task_bank"
    shutil.copytree(sandbox_bank, tampered)
    manifest = json.loads((tampered / "manifest.json").read_text())
    task_path = tampered / manifest["tasks"][0]["task_dir"] / "task.json"
    metadata = json.loads(task_path.read_text())
    metadata["n_classes"] += 1
    task_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_sandbox_bank(tampered)


def test_sandbox_array_tampering_is_detected(sandbox_bank, tmp_path):
    tampered = tmp_path / "tampered_array_bank"
    shutil.copytree(sandbox_bank, tampered)
    manifest = json.loads((tampered / "manifest.json").read_text())
    data_path = tampered / manifest["tasks"][0]["task_dir"] / "data.npz"
    with np.load(data_path, allow_pickle=False) as stored:
        arrays = {name: np.asarray(stored[name]).copy() for name in stored.files}
    arrays["X_query"][0, 0] += 1.0
    np.savez_compressed(data_path, **arrays)
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_sandbox_bank(tampered)


def test_generation_refuses_to_overwrite_nonempty_directory(tmp_path):
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "keep.txt").write_text("user data\n")
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        generate_sandbox_bank(target)


def test_sandbox_hydra_preset_and_problem_context(monkeypatch, sandbox_bank):
    monkeypatch.setenv("GIGAEVO_TAB_WPF_TASK_BANK", str(sandbox_bank))
    with initialize_config_dir(config_dir=str(CONFIG_DIR), version_base=None):
        cfg = compose(config_name="config", overrides=["experiment=tab_wpf_sandbox"])
    assert cfg.problem.name == "tab_wpf"
    assert cfg.problem.evaluation_mode == "sandbox"
    assert cfg.problem.task_split == META_TRAIN
    assert Path(cfg.problem.task_bank) == sandbox_bank
    assert cfg.program_loader.evaluation_mode == "sandbox"
    assert list(cfg.behavior_space["keys"]) == [
        "graph_node_count",
        "graph_max_depth",
    ]

    context = TabWpfProblemContext(
        ROOT / "problems/tab_wpf",
        evaluation_mode="sandbox",
        task_bank=sandbox_bank,
        task_split=META_TRAIN,
    )
    description = context.task_description
    assert "756 frozen tasks" in description
    assert "classification" in description.lower()
    assert "sandbox_linear_n02_k02_q35_r0000" not in description


def test_validator_routes_to_sandbox_and_keeps_meta_test_sealed(
    monkeypatch, sandbox_bank
):
    payload = json.loads(SEED.read_text())
    monkeypatch.setenv("GIGAEVO_TAB_WPF_EVAL_MODE", "sandbox")
    monkeypatch.setenv("GIGAEVO_TAB_WPF_TASK_BANK", str(sandbox_bank))
    monkeypatch.setenv("GIGAEVO_TAB_WPF_META_SPLIT", META_VALID)
    monkeypatch.setenv("GIGAEVO_TAB_WPF_SAMPLE_SIZE", "64")
    monkeypatch.setenv("GIGAEVO_TAB_WPF_SAMPLE_SEED", "37")
    metrics, artifact = validate(payload)
    assert metrics["is_valid"] == 1.0
    assert artifact["evaluation_mode"] == "sandbox_classification_bank"
    assert artifact["task_count"] == 64
    assert artifact["sampling"] == {
        "mode": "balanced_cohort",
        "sample_seed": 37,
    }

    monkeypatch.setenv("GIGAEVO_TAB_WPF_META_SPLIT", META_TEST)
    sealed_metrics, sealed_artifact = validate(payload)
    assert sealed_metrics["is_valid"] == 0.0
    assert sealed_artifact["validation_failure_reason"] == "sandbox_task_bank"
    assert "sealed" in sealed_artifact["error"]
