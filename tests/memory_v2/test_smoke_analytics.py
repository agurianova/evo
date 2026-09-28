from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from experiments.heilbron.memory_v2_comparison.build_report import (
    ARM_LABELS,
    _annotate_intentional_agentic_stop,
    _audit_provenance_error,
    _bank_size,
    _config_signature,
    _experiment_contract,
    _fitness_contract,
    _ledger_metric_contract,
    _load_archive_trace,
    _load_config,
    _requested_budget_status,
    _research_accounting_gate,
    _retrieval_contract,
    _seed_facts,
    _validate_audit_artifacts,
)
from experiments.hover.memory_v2_smoke.analyze import (
    Audit,
    LedgerRow,
    audit_rows,
    causal_observations,
    evidence_lifecycle,
    flatten,
    load_ledger,
    randomized_support_h50,
    shadow_lineage_evidence,
    summarize,
)
from experiments.hover.memory_v2_smoke.latex_report import (
    _audit_input_paths,
    _coefficient_labels,
    _ledger_config_contract,
    _load_llm_calls,
    _load_run_llm_calls,
    _load_yaml_config,
    _wilson_interval,
)
from gigaevo.memory.storage.base import ResearchFailure
from gigaevo.memory_v2.ledger import SqliteCausalLedger
from gigaevo.memory_v2.models import (
    ApplicabilityRecord,
    ApplicabilitySpecification,
    ApplicabilityStatus,
    ArchiveDisposition,
    CandidateActionProbability,
    CandidateUniverseRecord,
    CandidateUniverseSpecification,
    CardSnapshot,
    EnvironmentFingerprint,
    EvolutionContext,
    MutationEdge,
    OutcomeMeasurement,
    RagApplicability,
    TerminalOutcome,
    canonical_digest,
)

from .factories import decision_record


def _used_card_ids(record) -> tuple[str, ...]:
    if not record.delivered or record.proposed_treatment_id is None:
        return ()
    card = next(
        card
        for card in record.candidates
        if card.treatment_id == record.proposed_treatment_id
    )
    return (card.bank_card_id,)


def link_decision(
    ledger: SqliteCausalLedger,
    record,
    child_id: str,
    completion_ordinal: int,
) -> None:
    ledger.record_mutation_edge(
        parent_id=record.context.parent_id,
        child_id=child_id,
        island_id=record.context.map_elites.island_id,
        completion_ordinal=completion_ordinal,
    )
    assert ledger.link_attempt_child(
        attempt_id=record.attempt_id,
        child_id=child_id,
        completion_ordinal=completion_ordinal,
    )


def test_coefficient_labels_include_retrieval_applicability() -> None:
    fitted = SimpleNamespace(
        space=SimpleNamespace(
            config=SimpleNamespace(
                behavior_keys=("fitness",),
                card_kind_contrast=True,
                retrieval_applicability_contrast=True,
            )
        )
    )

    assert _coefficient_labels(fitted)[-1] == "shared treatment: RAG applicability"


def test_research_accounting_accepts_one_recorded_transient_failure() -> None:
    summary = {
        "applicability_statuses": {
            ApplicabilityStatus.ASSESSED.value: 9,
            ApplicabilityStatus.FAILED.value: 1,
        },
        "research_errors": 1,
        "research_calls": 10,
        "committed_researched_decisions": 10,
    }

    passed, evidence = _research_accounting_gate(summary)

    assert passed
    assert "1 failed episodes / 1 failed decisions" in evidence
    summary["research_errors"] = 0
    assert not _research_accounting_gate(summary)[0]


def test_failed_applicability_is_reported_without_breaking_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    evolution_context: EvolutionContext,
    revisions: tuple[CardSnapshot, CardSnapshot],
) -> None:
    record = decision_record(evolution_context, revisions[0]).model_copy(
        update={
            "applicability": ApplicabilityRecord(
                specification=ApplicabilitySpecification(
                    name="agentic_research",
                    retrieval_applicability_contrast=True,
                    policy_digest="a" * 64,
                ),
                status=ApplicabilityStatus.FAILED,
                failure=ResearchFailure.TIMEOUT,
            )
        }
    )
    row = LedgerRow(
        decision=record,
        terminal=None,
        decision_time="2026-01-01T00:00:00Z",
        terminal_time=None,
    )
    ledger = tmp_path / "checkpoints" / "memory_v2_selection_evidence.sqlite3"
    ledger.parent.mkdir(parents=True)
    ledger.touch()
    monkeypatch.setattr(
        "experiments.heilbron.memory_v2_comparison.build_report.load_ledger",
        lambda *_args, **_kwargs: ([row], "ok"),
    )

    contract_ok, evidence = _retrieval_contract(
        SimpleNamespace(key="agentic", root=tmp_path)
    )
    decisions, candidates, terminals = flatten([row])
    summary = summarize(
        [row],
        decisions,
        candidates,
        terminals,
        Audit(),
        "ok",
        [],
    )

    assert contract_ok
    assert "failed" in evidence
    assert summary["applicability"]["status_counts"] == {
        status.value: int(status is ApplicabilityStatus.FAILED)
        for status in ApplicabilityStatus
    }


def test_wilson_interval_is_non_degenerate_at_boundary_rates() -> None:
    lower, upper = _wilson_interval(pd.Series([0.0, 1.0]), pd.Series([5, 5]))

    assert lower[0] == pytest.approx(0.0)
    assert 0.0 < upper[0] < 1.0
    assert 0.0 < lower[1] < 1.0
    assert upper[1] == pytest.approx(1.0)


def test_comparison_requires_complete_audit_bundle(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="incomplete Bayesian audit artifacts"):
        _validate_audit_artifacts(tmp_path)


def test_comparison_marks_only_stop_induced_closure_as_expected() -> None:
    label = ARM_LABELS["agentic"]
    gates = pd.DataFrame(
        [
            (f"{label} completed budget", False, "one pending"),
            (f"{label} completion counter aligned", False, "249"),
            (f"{label} terminal closure", False, "250/250; one pending"),
            (f"{label} depth-1 readiness audit", False, "terminal closure"),
            (f"{label} ledger integrity", True, "ok"),
            (f"{label} applicability contract", False, "broken"),
        ],
        columns=["gate", "passed", "evidence"],
    )
    arm = SimpleNamespace(
        memory_trace=pd.DataFrame({"terminal_status": ["outcome"] * 249 + ["pending"]}),
        audit_metrics={"failed_readiness_gates": ["terminal closure"]},
    )

    annotated, accepted = _annotate_intentional_agentic_stop(
        gates, arm, budget=250, enabled=True
    )

    assert accepted
    assert annotated["expected_limitation"].tolist() == [
        True,
        True,
        True,
        True,
        False,
        False,
    ]
    assert annotated["blocks_readiness"].tolist() == [
        False,
        False,
        False,
        False,
        False,
        True,
    ]


def test_metric_archive_contract_is_derived_from_both_ledgers(
    tmp_path: Path,
    environment: EnvironmentFingerprint,
    evolution_context: EvolutionContext,
    revisions: tuple[CardSnapshot, CardSnapshot],
) -> None:
    arms = []
    for key in ("agentic", "whole_bank"):
        root = tmp_path / key
        ledger_path = root / "checkpoints" / "memory_v2_selection_evidence.sqlite3"
        ledger = SqliteCausalLedger(path=ledger_path, environment=environment)
        ledger.activate()
        ledger.record_decision(decision_record(evolution_context, revisions[0]))
        ledger.close()
        arms.append(SimpleNamespace(key=key, root=root))
    arms.append(SimpleNamespace(key="no_memory", root=tmp_path / "no-memory"))
    reward = evolution_context.reward
    total_cells = evolution_context.map_elites.total_cells

    assert _ledger_metric_contract(
        arms,
        asserted_lower=reward.metric_lower_bound,
        asserted_upper=reward.metric_upper_bound,
        asserted_total_cells=total_cells,
    ) == (reward.metric_lower_bound, reward.metric_upper_bound, total_cells)
    with pytest.raises(ValueError, match="CLI metric/archive assertions"):
        _ledger_metric_contract(
            arms,
            asserted_lower=reward.metric_lower_bound,
            asserted_upper=reward.metric_upper_bound,
            asserted_total_cells=total_cells + 1,
        )


def test_llm_accounting_aggregates_checkpoint_segments(tmp_path: Path) -> None:
    payloads = (
        {"stage": "MutationAgent", "ok": True, "tokens_in": 3, "tokens_out": 2},
        {
            "stage": "RetrievalPlannerAgent",
            "ok": True,
            "tokens_in": 5,
            "tokens_out": 1,
            "tokens_reasoning": 1,
        },
    )
    for index, payload in enumerate(payloads):
        (tmp_path / f"evolution_20260101_00000{index}.log").write_text(
            f"INFO [LLM_CALL] {json.dumps(payload)}\n",
            encoding="utf-8",
        )
    (tmp_path / "evolution_20260101_000002.log").write_text(
        "startup failed before any LLM call\n", encoding="utf-8"
    )

    calls = _load_run_llm_calls(tmp_path)

    assert len(calls) == 2
    assert calls["total_tokens"].tolist() == [5, 6]
    assert calls["tokens_reasoning"].tolist() == [0, 1]
    assert calls["log_segment"].nunique() == 2


def test_llm_accounting_includes_run_log_and_later_segments(tmp_path: Path) -> None:
    for name, stage in (
        ("run.log", "MutationAgent"),
        ("evolution_20260101_000001.log", "RetrievalPlannerAgent"),
    ):
        (tmp_path / name).write_text(
            f"INFO [LLM_CALL] {json.dumps({'stage': stage, 'ok': True})}\n",
            encoding="utf-8",
        )

    calls = _load_run_llm_calls(tmp_path)

    assert len(calls) == 2
    assert set(calls["log_segment"]) == {
        "run.log",
        "evolution_20260101_000001.log",
    }
    assert set(calls["call_category"]) == {"mutation", "retrieval"}


def test_llm_accounting_rejects_malformed_canonical_event(tmp_path: Path) -> None:
    path = tmp_path / "run.log"
    path.write_text("INFO [LLM_CALL] {not-json}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="malformed LLM_CALL"):
        _load_llm_calls(path)


def test_config_signature_handles_nested_hydra_values() -> None:
    first = {"axes": [{"key": "fitness", "bins": 150}], "enabled": True}
    same = {"enabled": True, "axes": [{"bins": 150, "key": "fitness"}]}
    changed = {"axes": [{"key": "fitness", "bins": 100}], "enabled": True}

    assert _config_signature(first) == _config_signature(same)
    assert _config_signature(first) != _config_signature(changed)


def test_audit_provenance_rejects_a_swapped_run(tmp_path: Path) -> None:
    run = (tmp_path / "run").resolve()
    inputs = (
        run / "checkpoints" / "memory_v2_selection_evidence.sqlite3",
        run / ".hydra" / "config.yaml",
        run / "checkpoints" / "cards.json",
        run / "checkpoints" / "write_ledger.jsonl",
    )
    for index, path in enumerate(inputs):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"input-{index}\n", encoding="utf-8")
    metrics = {
        "run_root": str(run),
        "ledger": str(run / "checkpoints" / "memory_v2_selection_evidence.sqlite3"),
        "audit_input_sha256": {
            str(path.relative_to(run)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in inputs
        },
    }

    assert _audit_provenance_error("agentic", run, metrics) is None
    metrics["run_root"] = str(tmp_path / "different-run")
    assert "provenance mismatch" in str(
        _audit_provenance_error("agentic", run, metrics)
    )


def test_audit_provenance_rejects_changed_input_at_same_path(tmp_path: Path) -> None:
    run = (tmp_path / "run").resolve()
    inputs = (
        run / "checkpoints" / "memory_v2_selection_evidence.sqlite3",
        run / ".hydra" / "config.yaml",
        run / "checkpoints" / "cards.json",
        run / "checkpoints" / "write_ledger.jsonl",
    )
    for index, path in enumerate(inputs):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"input-{index}\n", encoding="utf-8")
    metrics = {
        "run_root": str(run),
        "ledger": str(inputs[0]),
        "audit_input_sha256": {
            str(path.relative_to(run)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in inputs
        },
    }

    inputs[2].write_text("replacement bank\n", encoding="utf-8")

    assert "fingerprint changed" in str(
        _audit_provenance_error("agentic", run, metrics)
    )


def test_audit_fingerprints_the_artifacts_consumed_by_report(
    tmp_path: Path,
) -> None:
    run = (tmp_path / "run").resolve()
    ledger = run / "checkpoints" / "memory_v2_selection_evidence.sqlite3"
    canonical = (
        ledger,
        run / "resolved_config.yaml",
        run / "memory" / "cards.json",
        run / "memory" / "write_ledger.jsonl",
    )
    alternates = (
        run / ".hydra" / "config.yaml",
        run / "checkpoints" / "cards.json",
        run / "checkpoints" / "write_ledger.jsonl",
    )
    for path in (*canonical, *alternates):
        path.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("ledger\n", encoding="utf-8")
    canonical[1].write_text("source: resolved\n", encoding="utf-8")
    canonical[2].write_text(
        json.dumps({"cards": {"one": {}, "two": {}}}), encoding="utf-8"
    )
    canonical[3].write_text("canonical-write\n", encoding="utf-8")
    alternates[0].write_text("source: hydra\n", encoding="utf-8")
    alternates[1].write_text(json.dumps({"cards": {"wrong": {}}}), encoding="utf-8")
    alternates[2].write_text("alternate-write\n", encoding="utf-8")

    assert _audit_input_paths(run, ledger) == canonical
    assert _load_yaml_config(run)["source"] == "resolved"
    assert _load_config(run)["source"] == "resolved"
    assert _bank_size(run) == 2

    metrics = {
        "run_root": str(run),
        "ledger": str(ledger),
        "audit_input_sha256": {
            str(path.relative_to(run)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in canonical
        },
    }
    assert _audit_provenance_error("agentic", run, metrics) is None

    canonical[1].write_text("source: changed\n", encoding="utf-8")
    assert "fingerprint changed" in str(
        _audit_provenance_error("agentic", run, metrics)
    )


def test_ledger_audit_rejects_duplicate_terminal_child(
    tmp_path: Path,
    environment: EnvironmentFingerprint,
    evolution_context: EvolutionContext,
    revisions: tuple[CardSnapshot, CardSnapshot],
) -> None:
    ledger_path = tmp_path / "evidence.sqlite3"
    ledger = SqliteCausalLedger(path=ledger_path, environment=environment)
    ledger.activate()
    records = [
        decision_record(
            evolution_context,
            revisions[0],
            ordinal=ordinal,
            attempt_id=f"attempt-{ordinal}",
        )
        for ordinal in range(2)
    ]
    for ordinal, record in enumerate(records):
        child_id = f"child-{ordinal}"
        ledger.record_decision(record)
        link_decision(ledger, record, child_id, ordinal + 4)
        ledger.record_terminal(
            TerminalOutcome(
                decision_id=record.decision_id,
                child_id=child_id,
                base_id=evolution_context.parent_id,
                primary_metric=evolution_context.reward.primary_metric,
                higher_is_better=evolution_context.reward.higher_is_better,
                ope_eligible=True,
                status="outcome",
                used_card_ids=_used_card_ids(record),
                measurement=OutcomeMeasurement(value=0.1, se=None, kind="scalar"),
                completion_ordinal=ordinal + 4,
            )
        )
    ledger.close()

    with sqlite3.connect(ledger_path) as connection:
        encoded = connection.execute(
            "SELECT terminal_json FROM terminals WHERE decision_id = ?",
            (records[1].decision_id,),
        ).fetchone()[0]
        payload = json.loads(encoded)
        payload["child_id"] = "child-0"
        connection.execute(
            """
            UPDATE terminals
            SET terminal_json = ?, terminal_hash = ?
            WHERE decision_id = ?
            """,
            (
                json.dumps(payload, sort_keys=True),
                canonical_digest(payload),
                records[1].decision_id,
            ),
        )

    audit = Audit()
    rows, _ = load_ledger(ledger_path, audit)
    audit_rows(rows, audit)

    assert any("terminal disagrees with child link" in error for error in audit.errors)
    assert "terminal child ids are not unique" in audit.errors


def test_randomized_outcome_eligibility_is_structural(
    evolution_context: EvolutionContext,
    revisions: tuple[CardSnapshot, CardSnapshot],
) -> None:
    record = decision_record(evolution_context, revisions[0])
    row = LedgerRow(
        decision=record,
        terminal=TerminalOutcome(
            decision_id=record.decision_id,
            child_id="child",
            base_id=evolution_context.parent_id,
            primary_metric=evolution_context.reward.primary_metric,
            higher_is_better=evolution_context.reward.higher_is_better,
            ope_eligible=False,
            status="outcome",
            used_card_ids=_used_card_ids(record),
            measurement=OutcomeMeasurement(value=0.1, se=None, kind="scalar"),
            completion_ordinal=1,
        ),
        decision_time="2026-01-01T00:00:00Z",
        terminal_time="2026-01-01T00:00:01Z",
    )

    audit = Audit()
    audit_rows([row], audit)

    assert any("marked OPE-ineligible" in error for error in audit.errors)
    assert causal_observations([row]) == ()


@pytest.mark.parametrize("rag_applicable", [False, True])
def test_causal_observations_preserve_rag_applicability(
    rag_applicable: bool,
    evolution_context: EvolutionContext,
    revisions: tuple[CardSnapshot, CardSnapshot],
) -> None:
    card = revisions[0]
    record = decision_record(evolution_context, card).model_copy(
        update={
            "applicability": ApplicabilityRecord(
                specification=ApplicabilitySpecification(
                    name="agentic_research",
                    retrieval_applicability_contrast=True,
                    policy_digest="a" * 64,
                ),
                status=(
                    ApplicabilityStatus.ASSESSED
                    if rag_applicable
                    else ApplicabilityStatus.EMPTY
                ),
                assessed_bank_card_ids=(card.bank_card_id,),
                applicable_bank_card_ids=(card.bank_card_id,) if rag_applicable else (),
            )
        }
    )
    row = LedgerRow(
        decision=record,
        terminal=TerminalOutcome(
            decision_id=record.decision_id,
            child_id="child",
            base_id=evolution_context.parent_id,
            primary_metric=evolution_context.reward.primary_metric,
            higher_is_better=evolution_context.reward.higher_is_better,
            ope_eligible=True,
            status="outcome",
            used_card_ids=_used_card_ids(record),
            measurement=OutcomeMeasurement(value=0.1, se=None, kind="scalar"),
            completion_ordinal=1,
        ),
        decision_time="2026-01-01T00:00:00Z",
        terminal_time="2026-01-01T00:00:01Z",
    )

    (observation,) = causal_observations([row])

    assert observation.rag_applicability is (
        RagApplicability.APPLICABLE
        if rag_applicable
        else RagApplicability.NOT_APPLICABLE
    )


def test_ledger_audit_accepts_single_pool_monte_carlo_se(
    evolution_context: EvolutionContext,
    revisions: tuple[CardSnapshot, CardSnapshot],
) -> None:
    core, tail = revisions
    record = decision_record(evolution_context, core)
    offer = record.policy.offer_probability
    core_probability = 0.375
    tail_probability = 0.125
    core_action = CandidateActionProbability(
        treatment_id=core.treatment_id,
        bank_card_id=core.bank_card_id,
        proposal_probability=core_probability,
        proposal_mc_se=math.sqrt(
            core_probability * (1.0 - core_probability) / record.policy.proposal_worlds
        ),
        offer_probability=offer,
        joint_treated_probability=core_probability * offer,
        joint_control_probability=core_probability * (1.0 - offer),
        safe=True,
        prediction=record.action_probabilities[0].prediction,
    )
    tail_action = CandidateActionProbability(
        treatment_id=tail.treatment_id,
        bank_card_id=tail.bank_card_id,
        proposal_probability=tail_probability,
        proposal_mc_se=math.sqrt(
            tail_probability * (1.0 - tail_probability) / record.policy.proposal_worlds
        ),
        offer_probability=offer,
        joint_treated_probability=tail_probability * offer,
        joint_control_probability=tail_probability * (1.0 - offer),
        safe=True,
        prediction=record.action_probabilities[0].prediction.model_copy(
            update={"treatment_id": tail.treatment_id}
        ),
    )
    candidate_universe = CandidateUniverseRecord(
        specification=CandidateUniverseSpecification(policy_digest="u" * 64),
        status="eligible_bank",
        eligible_bank_card_ids=tuple(sorted((core.bank_card_id, tail.bank_card_id))),
    )
    audited_record = record.model_copy(
        update={
            "candidate_universe": candidate_universe,
            "lineage_registry": (core, tail),
            "candidates": (core, tail),
            "action_probabilities": (core_action, tail_action),
            "abstain_probability": 0.5,
            "proposed_treatment_id": core.treatment_id,
            "proposal_probability": core_probability,
            "joint_action_probability": core_probability * offer,
        }
    )
    audit = Audit()

    audit_rows(
        [
            LedgerRow(
                decision=audited_record,
                terminal=None,
                decision_time="2026-01-01T00:00:00Z",
                terminal_time=None,
            )
        ],
        audit,
    )

    assert not audit.errors


def test_resolved_config_must_match_ledger_policy_retrieval_and_seed(
    evolution_context: EvolutionContext,
    revisions: tuple[CardSnapshot, CardSnapshot],
) -> None:
    record = decision_record(evolution_context, revisions[0])
    row = LedgerRow(
        decision=record,
        terminal=None,
        decision_time="2026-01-01T00:00:00Z",
        terminal_time=None,
    )
    config = {
        "mutation_mode": "rewrite",
        "memory": {
            "run_seed": 17,
            "policy_config": {
                "offer_probability": 0.6,
                "proposal_exploration_probability": 0.0,
                "posterior_summary_samples": 1024,
                "proposal_worlds": 512,
                "abstain_effect": 0.0,
                "max_pending_per_card": 2,
            },
            "safety": {
                "gate_mode": "credible_joint_safe",
                "max_treated_invalid_probability": 0.25,
                "max_incremental_invalid_probability": 0.1,
                "alpha": 0.1,
            },
            "candidate_source": {
                "_target_": ("gigaevo.memory_v2.candidates.WholeBankCandidateSource"),
            },
            "applicability": {
                "_target_": "gigaevo.memory_v2.candidates.NullApplicabilityProvider",
            },
        },
    }

    assert all(_ledger_config_contract(config, [row]).values())

    changed_policy = copy.deepcopy(config)
    changed_policy["memory"]["policy_config"]["offer_probability"] = 0.7
    assert not _ledger_config_contract(changed_policy, [row])["policy"]

    changed_applicability = copy.deepcopy(config)
    changed_applicability["memory"]["applicability"] = {
        "_target_": "gigaevo.memory_v2.candidates.AgenticApplicabilityProvider",
    }
    assert not _ledger_config_contract(changed_applicability, [row])["applicability"]

    changed_seed = copy.deepcopy(config)
    changed_seed["memory"]["run_seed"] = 18
    assert not _ledger_config_contract(changed_seed, [row])["run_seed"]


def test_requested_budget_and_rendered_contract_come_from_configs() -> None:
    config = {
        "max_mutants": 123,
        "problem": {"name": "custom_problem"},
        "model_name": "provider/mutator-v2",
        "num_parents": 2,
        "behavior_space": {"keys": ["fitness", "size"], "dynamic": False},
        "memory": {
            "run_seed": 9,
            "llm": {"models": [{"model": "provider/research-v3"}]},
            "policy_config": {"offer_probability": 0.65},
            "writer": {"max_task_cards": 7},
        },
    }
    arms = [
        SimpleNamespace(key=key, config=copy.deepcopy(config))
        for key in ("agentic", "whole_bank", "no_memory")
    ]

    assert _requested_budget_status(arms, 123)[0]
    assert not _requested_budget_status(arms, 250)[0]
    contract = _experiment_contract(arms, 123)
    assert contract == {
        "problem": "custom_problem",
        "mutation_model": "mutator-v2",
        "research_model": "research-v3",
        "budget": 123,
        "num_parents": 2,
        "memory_seed": 9,
        "offer_probability": 0.65,
        "behavior_dimensions": 2,
        "dynamic_archive": False,
        "bank_cap": 7,
    }


def test_seed_fitness_and_final_archive_are_required(tmp_path: Path) -> None:
    seeds = [
        {
            "id": f"seed-{index}",
            "iteration": index,
            "code": f"code-{index}",
            "metadata": {"source": "initial_program"},
            "metrics": {
                "is_valid": 0.0 if index == 0 else 1.0,
                "fitness": math.nan if index == 0 else 0.01,
            },
        }
        for index in range(5)
    ]
    with pytest.raises(ValueError, match="non-finite fitness"):
        _seed_facts(seeds)

    arm = SimpleNamespace(
        seed_valid_fitnesses=(100.0,),
        trace=pd.DataFrame({"valid": [True], "fitness": [0.02]}),
    )
    assert not _fitness_contract(arm, 0.0, 0.04)[0]

    with pytest.raises(FileNotFoundError):
        _load_archive_trace(tmp_path, 1)
    archive_path = (
        tmp_path / "storage" / "heilbron" / "archives" / "island_fitness_island.json"
    )
    archive_path.parent.mkdir(parents=True)
    archive_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid final archive"):
        _load_archive_trace(tmp_path, 1)

    archive_path.write_text('{"0": "invalid-program"}\n', encoding="utf-8")
    program_path = (
        tmp_path / "storage" / "heilbron" / "programs" / "invalid-program.json"
    )
    program_path.parent.mkdir(parents=True)
    program_path.write_text(
        json.dumps(
            {
                "id": "invalid-program",
                "iteration": 0,
                "created_at": "2026-01-01T00:00:00Z",
                "metadata": {},
                "metrics": {"is_valid": 0.0, "fitness": 0.01},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="non-valid programs"):
        _load_archive_trace(tmp_path, 1)


def test_evidence_lifecycle_pools_absorbed_card_ids(
    evolution_context: EvolutionContext,
    revisions: tuple[CardSnapshot, CardSnapshot],
) -> None:
    old, survivor = revisions
    survivor = survivor.model_copy(
        update={"absorbed_bank_card_ids": (old.bank_card_id,)}
    )
    decisions = (
        decision_record(
            evolution_context,
            old,
            ordinal=0,
            delivered=True,
            attempt_id="old-treated",
        ),
        decision_record(
            evolution_context,
            old,
            ordinal=1,
            delivered=False,
            attempt_id="old-control",
        ),
        decision_record(
            evolution_context,
            survivor,
            ordinal=2,
            delivered=True,
            attempt_id="survivor-treated",
        ),
        decision_record(
            evolution_context,
            survivor,
            ordinal=3,
            delivered=False,
            attempt_id="survivor-control",
        ),
    )
    rows = [
        LedgerRow(
            decision=decision,
            terminal=TerminalOutcome(
                decision_id=decision.decision_id,
                child_id=f"child-{decision.event_ordinal}",
                base_id=evolution_context.parent_id,
                primary_metric=evolution_context.reward.primary_metric,
                higher_is_better=evolution_context.reward.higher_is_better,
                ope_eligible=True,
                status="outcome",
                used_card_ids=_used_card_ids(decision),
                measurement=OutcomeMeasurement(value=0.1, se=None, kind="scalar"),
                completion_ordinal=decision.event_ordinal,
            ),
            decision_time="2026-01-01T00:00:00Z",
            terminal_time="2026-01-01T00:00:01Z",
        )
        for decision in decisions
    ]

    _, candidates, _ = flatten(rows)
    lifecycle = evidence_lifecycle(rows, candidates)

    assert len(lifecycle) == 1
    assert lifecycle[0]["treatment_id"] == survivor.treatment_id
    assert lifecycle[0]["component_treatment_ids"].split("|") == sorted(
        [old.treatment_id, survivor.treatment_id]
    )
    assert lifecycle[0]["offers"] == 4
    assert lifecycle[0]["treated"] == 2
    assert lifecycle[0]["control"] == 2


def test_evidence_lifecycle_uses_all_bank_active_opportunities(
    evolution_context: EvolutionContext,
    revisions: tuple[CardSnapshot, CardSnapshot],
) -> None:
    card = revisions[0]
    decisions = tuple(
        decision_record(
            evolution_context,
            card,
            ordinal=ordinal,
            delivered=ordinal == 0,
            attempt_id=f"opportunity-{ordinal}",
        )
        for ordinal in range(5)
    )
    rows = [
        LedgerRow(
            decision=decision,
            terminal=TerminalOutcome(
                decision_id=decision.decision_id,
                child_id=f"child-{decision.event_ordinal}",
                base_id=evolution_context.parent_id,
                primary_metric=evolution_context.reward.primary_metric,
                higher_is_better=evolution_context.reward.higher_is_better,
                ope_eligible=True,
                status="outcome",
                used_card_ids=_used_card_ids(decision),
                measurement=OutcomeMeasurement(value=0.1, se=None, kind="scalar"),
                completion_ordinal=decision.event_ordinal,
            ),
            decision_time="2026-01-01T00:00:00Z",
            terminal_time="2026-01-01T00:00:01Z",
        )
        for decision in decisions
    ]
    candidates = [
        {
            "ordinal": decision.event_ordinal,
            "decision_id": decision.decision_id,
            "treatment_id": card.treatment_id,
            "selected": index < 2,
            "proposal_probability": probability,
            "joint_treated_probability": probability * 0.7,
            "joint_control_probability": probability * 0.3,
        }
        for index, (decision, probability) in enumerate(
            zip(decisions[:4], (0.8, 0.8, 0.05, 0.05), strict=True)
        )
    ]

    lifecycle = evidence_lifecycle(rows, candidates)

    assert len(lifecycle) == 1
    row = lifecycle[0]
    assert row["active_decision_opportunities"] == 5
    assert row["eligible_decision_opportunities"] == 5
    assert row["slate_decision_opportunities"] == 4
    assert row["mean_proposal_probability"] == pytest.approx(0.34)
    assert row["mean_offer_probability"] == pytest.approx(0.7)
    assert row["effective_randomized_rate"] == pytest.approx(0.34)
    assert row["randomized_evidence_h50"] == randomized_support_h50(0.34, 0.7)


@pytest.mark.timeout(120)
def test_smoke_analyzer_audits_real_ledger_and_renders_plots(
    tmp_path: Path,
    environment: EnvironmentFingerprint,
    evolution_context: EvolutionContext,
    revisions: tuple[CardSnapshot, CardSnapshot],
) -> None:
    ledger_path = tmp_path / "evidence.sqlite3"
    ledger = SqliteCausalLedger(path=ledger_path, environment=environment)
    ledger.activate()
    record = decision_record(
        evolution_context,
        revisions[0],
        delivered=True,
        safety_gate_mode="exclude_confident_incremental_harm",
        max_treated_invalid_probability=None,
    )
    ledger.record_decision(record)
    link_decision(ledger, record, "analyzed-child", 4)
    ledger.record_terminal(
        TerminalOutcome(
            decision_id=record.decision_id,
            child_id="analyzed-child",
            base_id=evolution_context.parent_id,
            primary_metric=evolution_context.reward.primary_metric,
            higher_is_better=evolution_context.reward.higher_is_better,
            ope_eligible=True,
            status="outcome",
            used_card_ids=_used_card_ids(record),
            measurement=OutcomeMeasurement(value=0.2, se=None, kind="scalar"),
            completion_ordinal=4,
        )
    )
    control = decision_record(
        evolution_context,
        revisions[0],
        ordinal=1,
        delivered=False,
        attempt_id="attempt-control",
        safety_gate_mode="exclude_confident_incremental_harm",
        max_treated_invalid_probability=None,
    )
    ledger.record_decision(control)
    link_decision(ledger, control, "control-child", 5)
    ledger.record_terminal(
        TerminalOutcome(
            decision_id=control.decision_id,
            child_id="control-child",
            base_id=evolution_context.parent_id,
            primary_metric=evolution_context.reward.primary_metric,
            higher_is_better=evolution_context.reward.higher_is_better,
            ope_eligible=True,
            status="outcome",
            used_card_ids=_used_card_ids(control),
            measurement=OutcomeMeasurement(value=0.1, se=None, kind="scalar"),
            completion_ordinal=5,
        )
    )

    project_root = Path(__file__).parents[2]
    output_dir = tmp_path / "analytics"
    result = subprocess.run(
        [
            sys.executable,
            "experiments/hover/memory_v2_smoke/analyze.py",
            "--ledger",
            str(ledger_path),
            "--output-dir",
            str(output_dir),
            "--min-decisions",
            "2",
            "--min-candidate-rows",
            "2",
            "--min-proposals",
            "2",
            "--min-delivered",
            "1",
            "--min-controls",
            "1",
            "--min-terminal-evidence",
            "2",
            "--min-posterior-evidence",
            "0",
        ],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["audit_passed"]
    assert summary["decisions"] == 2
    assert summary["terminal_statuses"] == {
        "outcome": 2,
        "invalid": 0,
        "censored": 0,
    }
    assert (output_dir / "memory_v2_dashboard.png").stat().st_size > 10_000
    assert (output_dir / "offer_calibration.png").stat().st_size > 5_000
    assert (output_dir / "ope_sensitivity.png").stat().st_size > 5_000
    ope = json.loads((output_dir / "ope_report.json").read_text(encoding="utf-8"))
    assert len(ope) == 10


def test_shadow_lineage_analysis_does_not_change_logged_context(
    evolution_context: EvolutionContext,
    revisions: tuple[CardSnapshot, CardSnapshot],
) -> None:
    root = decision_record(evolution_context, revisions[0], delivered=True)
    later_context = evolution_context.model_copy(
        update={"parent_id": "unrelated-parent", "parent_iteration": 21}
    )
    later = decision_record(
        later_context,
        revisions[0],
        ordinal=1,
        attempt_id="later-attempt",
        delivered=False,
    )
    mutation_edges = tuple(
        MutationEdge(
            parent_id=record.context.parent_id,
            child_id=f"child-{record.event_ordinal}",
            island_id=record.context.map_elites.island_id,
            completion_ordinal=record.event_ordinal,
            status="outcome",
            measurement=OutcomeMeasurement(value=0.1, se=None, kind="scalar"),
            archive_disposition=ArchiveDisposition.ACCEPTED,
        )
        for record in (root, later)
    )
    rows = [
        LedgerRow(
            decision=record,
            terminal=TerminalOutcome(
                decision_id=record.decision_id,
                child_id=f"child-{record.event_ordinal}",
                base_id=record.context.parent_id,
                primary_metric="fitness",
                higher_is_better=True,
                ope_eligible=True,
                status="outcome",
                used_card_ids=_used_card_ids(record),
                measurement=OutcomeMeasurement(value=0.1, se=None, kind="scalar"),
                completion_ordinal=record.event_ordinal,
            ),
            decision_time="2026-01-01T00:00:00Z",
            terminal_time="2026-01-01T00:00:01Z",
            mutation_edges=mutation_edges,
        )
        for record in (root, later)
    ]
    immediate = causal_observations(rows)

    shadow_immediate, outcomes, rewards = shadow_lineage_evidence(
        rows, immediate, lineage_depth=3, opportunity_budget=1
    )

    assert root.context.reward.lineage_depth == 1
    assert shadow_immediate[0].context.reward.lineage_depth == 3
    assert outcomes[0].status == "outcome"
    assert rewards[0].context.reward.endpoint == "bounded_lineage_utility"
