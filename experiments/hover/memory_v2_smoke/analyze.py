#!/usr/bin/env python3
"""Audit and visualize one memory-v2 causal ledger."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import csv
from dataclasses import dataclass, field
from datetime import datetime
import json
import math
from pathlib import Path
import sqlite3
import sys
from typing import Any, Literal

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gigaevo.memory_v2.credit import LineageCreditResolver  # noqa: E402
from gigaevo.memory_v2.models import (  # noqa: E402
    ApplicabilityStatus,
    CandidateUniverseStatus,
    CausalObservation,
    DecisionRecord,
    MutationEdge,
    OutcomeMeasurement,
    TerminalOutcome,
    canonical_digest,
)
from gigaevo.memory_v2.ope import ConditionalOfferDREvaluator  # noqa: E402
from gigaevo.memory_v2.policy import safety_gate_admits  # noqa: E402


@dataclass
class Audit:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def warn(self, condition: bool, message: str) -> None:
        if not condition:
            self.warnings.append(message)


@dataclass(frozen=True)
class LedgerRow:
    decision: DecisionRecord
    terminal: TerminalOutcome | None
    decision_time: str
    terminal_time: str | None
    linked_attempt_id: str | None = None
    linked_child_id: str | None = None
    linked_base_id: str | None = None
    linked_completion_ordinal: int | None = None
    mutation_edges: tuple[MutationEdge, ...] = ()


def _finite(value: float | None) -> bool:
    return value is None or math.isfinite(value)


def _close(left: float, right: float, tolerance: float = 1e-10) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=tolerance)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_ledger(path: Path, audit: Audit) -> tuple[list[LedgerRow], str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    uri = f"file:{path.resolve()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        audit.require(integrity == "ok", f"SQLite integrity_check returned {integrity}")
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        audit.require(
            not foreign_key_errors,
            f"SQLite foreign_key_check returned {foreign_key_errors}",
        )
        rows = connection.execute(
            """
            SELECT d.decision_id, d.attempt_id, d.environment_hash, d.event_ordinal,
                   d.record_json, d.record_hash, d.recorded_at_utc,
                   t.terminal_json, t.terminal_hash, t.recorded_at_utc,
                   c.attempt_id, c.child_id, c.base_id, c.completion_ordinal
            FROM decisions AS d
            LEFT JOIN terminals AS t USING(decision_id)
            LEFT JOIN decision_children AS c USING(decision_id)
            ORDER BY d.event_ordinal, d.decision_id
            """
        ).fetchall()
        edge_rows = connection.execute(
            """
            SELECT parent_id, child_id, island_id, completion_ordinal,
                   status, measurement_json, archive_disposition, failure_stage
            FROM mutation_edges
            ORDER BY completion_ordinal, child_id
            """
        ).fetchall()

    mutation_edges = tuple(
        MutationEdge(
            parent_id=parent_id,
            child_id=child_id,
            island_id=island_id,
            completion_ordinal=completion_ordinal,
            status=status,
            measurement=(
                OutcomeMeasurement.model_validate_json(measurement_json)
                if measurement_json is not None
                else None
            ),
            archive_disposition=archive_disposition,
            failure_stage=failure_stage,
        )
        for (
            parent_id,
            child_id,
            island_id,
            completion_ordinal,
            status,
            measurement_json,
            archive_disposition,
            failure_stage,
        ) in edge_rows
    )

    result: list[LedgerRow] = []
    for (
        decision_id,
        attempt_id,
        environment_hash,
        event_ordinal,
        record_json,
        record_hash,
        decision_time,
        terminal_json,
        terminal_hash,
        terminal_time,
        linked_attempt_id,
        linked_child_id,
        linked_base_id,
        linked_completion_ordinal,
    ) in rows:
        raw_decision = json.loads(record_json)
        decision = DecisionRecord.model_validate(raw_decision)
        audit.require(
            (
                decision.decision_id == decision_id
                and decision.attempt_id == attempt_id
                and decision.context.environment.digest == environment_hash
                and decision.event_ordinal == event_ordinal
            ),
            f"denormalized decision columns disagree: {decision.decision_id}",
        )
        audit.require(
            canonical_digest(raw_decision) == record_hash,
            f"decision hash mismatch: {decision.decision_id}",
        )
        terminal = None
        if terminal_json is not None:
            raw_terminal = json.loads(terminal_json)
            terminal = TerminalOutcome.model_validate(raw_terminal)
            audit.require(
                canonical_digest(raw_terminal) == terminal_hash,
                f"terminal hash mismatch: {decision.decision_id}",
            )
            audit.require(
                terminal.decision_id == decision.decision_id,
                f"terminal joins the wrong decision: {decision.decision_id}",
            )
        if linked_child_id is not None:
            audit.require(
                (
                    linked_attempt_id == decision.attempt_id
                    and linked_base_id == decision.context.parent_id
                ),
                f"denormalized child link disagrees: {decision.decision_id}",
            )
        if terminal is not None:
            if linked_child_id is None:
                audit.require(
                    terminal.child_id == f"no-child:{decision.attempt_id}",
                    f"terminal lacks its child link: {decision.decision_id}",
                )
            else:
                audit.require(
                    (
                        terminal.child_id == linked_child_id
                        and terminal.base_id == linked_base_id
                        and terminal.completion_ordinal == linked_completion_ordinal
                    ),
                    f"terminal disagrees with child link: {decision.decision_id}",
                )
        result.append(
            LedgerRow(
                decision=decision,
                terminal=terminal,
                decision_time=str(decision_time),
                terminal_time=str(terminal_time) if terminal_time else None,
                linked_attempt_id=(
                    str(linked_attempt_id) if linked_attempt_id is not None else None
                ),
                linked_child_id=(
                    str(linked_child_id) if linked_child_id is not None else None
                ),
                linked_base_id=(
                    str(linked_base_id) if linked_base_id is not None else None
                ),
                linked_completion_ordinal=(
                    int(linked_completion_ordinal)
                    if linked_completion_ordinal is not None
                    else None
                ),
                mutation_edges=mutation_edges,
            )
        )
    return result, integrity


def audit_rows(rows: list[LedgerRow], audit: Audit) -> None:
    ordinals = [row.decision.event_ordinal for row in rows]
    audit.require(len(ordinals) == len(set(ordinals)), "event ordinals are not unique")
    audit.require(ordinals == sorted(ordinals), "event ordinals are not ordered")
    attempts = [row.decision.attempt_id for row in rows]
    audit.require(len(attempts) == len(set(attempts)), "attempt ids are not unique")
    terminal_children = [
        row.terminal.child_id for row in rows if row.terminal is not None
    ]
    audit.require(
        len(terminal_children) == len(set(terminal_children)),
        "terminal child ids are not unique",
    )
    if rows:
        audit.require(
            len({row.decision.context.run_id for row in rows}) == 1,
            "ledger mixes evolution trajectories",
        )
        audit.require(
            len({row.decision.context.environment.digest for row in rows}) == 1,
            "ledger mixes environment contracts",
        )
        audit.require(
            len({row.decision.run_seed for row in rows}) == 1,
            "ledger mixes run seeds",
        )
        audit.require(
            len({row.decision.policy.digest for row in rows}) == 1,
            "ledger mixes behavior policies",
        )
        audit.require(
            len({row.decision.candidate_universe.specification.digest for row in rows})
            == 1,
            "ledger mixes candidate-universe specifications",
        )
        audit.require(
            len({row.decision.model_config_hash for row in rows}) == 1,
            "ledger mixes decision model configurations",
        )

    previous_evidence = -1
    for ledger_row in rows:
        record = ledger_row.decision
        prefix = f"decision {record.decision_id}"
        actions = record.action_probabilities
        proposal_total = record.abstain_probability + sum(
            action.proposal_probability for action in actions
        )
        audit.require(_close(proposal_total, 1.0), f"{prefix}: proposal mass != 1")
        audit.require(
            record.fit_diagnostics.evidence_count >= previous_evidence,
            f"{prefix}: evidence count moved backwards",
        )
        previous_evidence = record.fit_diagnostics.evidence_count
        audit.require(
            record.fit_diagnostics.reward_observations
            <= record.fit_diagnostics.evidence_count,
            f"{prefix}: reward observations exceed causal evidence",
        )
        audit.require(
            record.fit_diagnostics.safety_observations
            == record.fit_diagnostics.evidence_count,
            f"{prefix}: safety model omitted an eligible terminal",
        )
        diagnostics = record.fit_diagnostics
        audit.require(
            diagnostics.offered_observations
            == diagnostics.used_observations + diagnostics.ignored_observations,
            f"{prefix}: offered use accounting does not close",
        )
        audit.require(
            diagnostics.used_observations <= diagnostics.evidence_count,
            f"{prefix}: cited uses exceed usefulness evidence",
        )
        audit.require(
            all(
                _finite(value)
                for value in (
                    diagnostics.reward_residual_sd,
                    diagnostics.reward_card_effect_sd,
                    diagnostics.safety_objective,
                    diagnostics.safety_gradient_inf,
                    diagnostics.safety_hessian_condition,
                )
            ),
            f"{prefix}: non-finite posterior diagnostic",
        )
        audit.require(
            diagnostics.safety_gradient_inf <= 1e-4,
            f"{prefix}: safety gradient is not converged",
        )
        audit.require(
            diagnostics.safety_hessian_condition <= 1e12,
            f"{prefix}: safety Hessian is ill-conditioned",
        )
        audit.warn(
            not diagnostics.reward_hyperparameters_at_boundary,
            f"{prefix}: empirical-Bayes scale reached a boundary",
        )
        audit.warn(
            diagnostics.reward_optimizer_success,
            f"{prefix}: empirical-Bayes fit fell back after optimizer failure",
        )

        reward = record.context.reward
        parent_fitness = record.context.parent_metrics[reward.primary_metric]
        if reward.higher_is_better:
            gain_lower = (reward.metric_lower_bound - parent_fitness) / reward.scale
            gain_upper = (reward.metric_upper_bound - parent_fitness) / reward.scale
        else:
            gain_lower = (parent_fitness - reward.metric_upper_bound) / reward.scale
            gain_upper = (parent_fitness - reward.metric_lower_bound) / reward.scale

        selected = None
        for action in actions:
            action_prefix = f"{prefix}, card {action.bank_card_id}"
            exploration = record.policy.proposal_exploration_probability
            if exploration == 0.0:
                expected_se = math.sqrt(
                    max(
                        action.proposal_probability
                        * (1.0 - action.proposal_probability)
                        / record.policy.proposal_worlds,
                        0.0,
                    )
                )
                audit.require(
                    _close(action.proposal_mc_se, expected_se),
                    f"{action_prefix}: proposal MC SE is inconsistent",
                )
            else:
                audit.require(
                    _finite(action.proposal_mc_se) and action.proposal_mc_se >= 0.0,
                    f"{action_prefix}: proposal MC SE is invalid",
                )
            if action.safe:
                audit.require(
                    safety_gate_admits(
                        gate_mode=record.policy.safety_gate_mode,
                        probability_acceptable=(action.prediction.probability_safe),
                        alpha=record.policy.safety_alpha,
                    ),
                    f"{action_prefix}: posterior failed the logged admission gate",
                )
                audit.require(
                    action.offer_probability is not None,
                    f"{action_prefix}: feasible card lacks offer propensity",
                )
                audit.require(
                    action.proposal_probability > 0.0,
                    f"{action_prefix}: feasible card lacks exploration support",
                )
            else:
                audit.require(
                    action.proposal_probability == 0.0
                    and action.joint_treated_probability == 0.0
                    and action.joint_control_probability == 0.0,
                    f"{action_prefix}: infeasible card has policy support",
                )
            if action.offer_probability is not None:
                offer = action.offer_probability
                audit.require(
                    _close(offer, record.policy.offer_probability),
                    f"{action_prefix}: offer propensity differs from fixed probe",
                )
                audit.require(
                    _close(
                        action.joint_treated_probability,
                        action.proposal_probability * offer,
                    )
                    and _close(
                        action.joint_control_probability,
                        action.proposal_probability * (1.0 - offer),
                    ),
                    f"{action_prefix}: joint propensity is inconsistent",
                )
            prediction = action.prediction
            audit.require(
                gain_lower - 1e-10
                <= prediction.usable_gain_control_mean
                <= gain_upper + 1e-10
                and gain_lower - 1e-10
                <= prediction.usable_gain_treated_mean
                <= gain_upper + 1e-10,
                f"{action_prefix}: reward posterior escaped parent opportunity bounds",
            )
            audit.require(
                all(
                    _finite(value)
                    for value in (
                        prediction.usable_effect_mean,
                        prediction.usable_effect_sd,
                        prediction.usable_gain_control_mean,
                        prediction.usable_gain_treated_mean,
                        prediction.usable_gain_predictive_sd,
                        prediction.safety_integration_error,
                    )
                ),
                f"{action_prefix}: non-finite posterior summary",
            )
            audit.require(
                prediction.safety_integration_error <= 1.01e-8,
                f"{action_prefix}: safety integration error exceeds smoke tolerance",
            )
            if action.treatment_id == record.proposed_treatment_id:
                selected = action

        if record.proposed_treatment_id is None:
            audit.require(selected is None, f"{prefix}: abstention has selected row")
        else:
            audit.require(selected is not None, f"{prefix}: proposal row is missing")
            if selected is not None:
                expected_joint = (
                    selected.joint_treated_probability
                    if record.delivered
                    else selected.joint_control_probability
                )
                audit.require(
                    _close(record.joint_action_probability or -1.0, expected_joint),
                    f"{prefix}: realized joint propensity is inconsistent",
                )
                audit.require(selected.safe, f"{prefix}: proposed card is infeasible")

        terminal = ledger_row.terminal
        if terminal is None:
            continue
        if record.proposed_treatment_id is not None and terminal.status != "censored":
            audit.require(
                terminal.ope_eligible,
                f"{prefix}: randomized terminal is marked OPE-ineligible",
            )
        audit.require(
            terminal.base_id == record.context.parent_id,
            f"{prefix}: terminal base differs from frozen parent",
        )
        audit.require(
            terminal.primary_metric == record.context.reward.primary_metric
            and terminal.higher_is_better == record.context.reward.higher_is_better,
            f"{prefix}: terminal reward contract changed",
        )
        if terminal.measurement is not None:
            audit.require(
                abs(terminal.measurement.value) <= record.context.reward.scale + 1e-9,
                f"{prefix}: terminal gain exceeds metric bounds",
            )
        decision_time = _parse_time(ledger_row.decision_time)
        terminal_time = _parse_time(ledger_row.terminal_time)
        audit.require(
            decision_time is not None
            and terminal_time is not None
            and terminal_time >= decision_time,
            f"{prefix}: terminal audit timestamp precedes decision",
        )


def flatten(
    rows: list[LedgerRow],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    decisions: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    terminals: list[dict[str, Any]] = []
    for ledger_row in rows:
        record = ledger_row.decision
        selected_action = next(
            (
                action
                for action in record.action_probabilities
                if action.treatment_id == record.proposed_treatment_id
            ),
            None,
        )
        diagnostics = record.fit_diagnostics
        decisions.append(
            {
                "ordinal": record.event_ordinal,
                "decision_id": record.decision_id,
                "attempt_id": record.attempt_id,
                "decision_time_utc": ledger_row.decision_time,
                "safety_gate_mode": record.policy.safety_gate_mode,
                "candidate_universe_status": record.candidate_universe.status,
                "eligible_bank_count": len(
                    record.candidate_universe.eligible_bank_card_ids
                ),
                "applicability_status": record.applicability.status,
                "applicable_count": len(record.applicability.applicable_bank_card_ids),
                "research_iterations": record.applicability.research_iterations,
                "candidate_count": len(record.candidates),
                "safe_count": sum(
                    action.safe for action in record.action_probabilities
                ),
                "abstention_reason": (
                    "proposed"
                    if selected_action is not None
                    else (
                        "no_candidates"
                        if not record.action_probabilities
                        else (
                            "no_feasible_candidates"
                            if not any(
                                action.safe for action in record.action_probabilities
                            )
                            else "reward_policy_or_abstain"
                        )
                    )
                ),
                "abstain_probability": record.abstain_probability,
                "proposed": selected_action is not None,
                "delivered": record.delivered,
                "proposal_probability": record.proposal_probability,
                "offer_probability": record.offer_probability,
                "joint_action_probability": record.joint_action_probability,
                "evidence_count": diagnostics.evidence_count,
                "offered_observations": diagnostics.offered_observations,
                "used_observations": diagnostics.used_observations,
                "ignored_observations": diagnostics.ignored_observations,
                "reward_observations": diagnostics.reward_observations,
                "pending_count": sum(record.pending_by_treatment.values()),
                "censored_count": record.censored_count,
                "ineligible_count": record.ineligible_count,
                "reward_residual_sd": diagnostics.reward_residual_sd,
                "reward_card_effect_sd": diagnostics.reward_card_effect_sd,
                "reward_optimizer_success": diagnostics.reward_optimizer_success,
                "safety_gradient_inf": diagnostics.safety_gradient_inf,
                "safety_hessian_condition": diagnostics.safety_hessian_condition,
                "map_coverage": record.context.map_elites.coverage,
                "parent_quality_quantile": record.context.map_elites.parent_quality_quantile,
                "neighbor_occupancy": record.context.map_elites.neighbor_occupancy,
                "archive_size": record.context.map_elites.archive_size,
                "parent_fitness": record.context.parent_metrics[
                    record.context.reward.primary_metric
                ],
                "terminal_status": (
                    ledger_row.terminal.status if ledger_row.terminal else "pending"
                ),
            }
        )
        for action in record.action_probabilities:
            prediction = action.prediction
            applicability = record.rag_applicability(action.bank_card_id)
            candidates.append(
                {
                    "ordinal": record.event_ordinal,
                    "decision_id": record.decision_id,
                    "bank_card_id": action.bank_card_id,
                    "treatment_id": action.treatment_id,
                    "rag_applicability": applicability.value,
                    "rag_applicable": applicability.value == "applicable",
                    "selected": action.treatment_id == record.proposed_treatment_id,
                    "delivered": record.delivered
                    and action.treatment_id == record.proposed_treatment_id,
                    "safe": action.safe,
                    "proposal_probability": action.proposal_probability,
                    "proposal_mc_se": action.proposal_mc_se,
                    "offer_probability": action.offer_probability,
                    "joint_treated_probability": action.joint_treated_probability,
                    "joint_control_probability": action.joint_control_probability,
                    "worst_feasible_gain": (
                        (
                            record.context.reward.metric_lower_bound
                            - record.context.parent_metrics[
                                record.context.reward.primary_metric
                            ]
                        )
                        / record.context.reward.scale
                        if record.context.reward.higher_is_better
                        else (
                            record.context.parent_metrics[
                                record.context.reward.primary_metric
                            ]
                            - record.context.reward.metric_upper_bound
                        )
                        / record.context.reward.scale
                    ),
                    **prediction.model_dump(mode="json"),
                }
            )
        if ledger_row.terminal is not None:
            terminal = ledger_row.terminal
            decision_time = _parse_time(ledger_row.decision_time)
            terminal_time = _parse_time(ledger_row.terminal_time)
            latency = (
                (terminal_time - decision_time).total_seconds()
                if decision_time is not None and terminal_time is not None
                else None
            )
            terminals.append(
                {
                    "ordinal": record.event_ordinal,
                    "decision_id": record.decision_id,
                    "child_id": terminal.child_id,
                    "status": terminal.status,
                    "ope_eligible": terminal.ope_eligible,
                    "gain": (
                        terminal.measurement.value if terminal.measurement else None
                    ),
                    "gain_se": (
                        terminal.measurement.se if terminal.measurement else None
                    ),
                    "measurement_kind": (
                        terminal.measurement.kind if terminal.measurement else None
                    ),
                    "failure_stage": terminal.failure_stage,
                    "censor_reason": terminal.censor_reason,
                    "completion_ordinal": terminal.completion_ordinal,
                    "terminal_time_utc": ledger_row.terminal_time,
                    "latency_seconds": latency,
                }
            )
    return decisions, candidates, terminals


def causal_observations(rows: list[LedgerRow]) -> tuple[CausalObservation, ...]:
    """Reconstruct the exact eligible rows frozen in the immutable ledger."""

    observations: list[CausalObservation] = []
    for ledger_row in rows:
        record = ledger_row.decision
        terminal = ledger_row.terminal
        if (
            record.proposed_treatment_id is None
            or terminal is None
            or terminal.status == "censored"
            or not terminal.ope_eligible
        ):
            continue
        card = next(
            candidate
            for candidate in record.candidates
            if candidate.treatment_id == record.proposed_treatment_id
        )
        observations.append(
            CausalObservation(
                decision_id=record.decision_id,
                event_ordinal=record.event_ordinal,
                card=card,
                context=record.context,
                rag_applicability=record.rag_applicability(card.bank_card_id),
                treatment=record.delivered,
                card_used=(
                    record.delivered and card.bank_card_id in terminal.used_card_ids
                ),
                offer_propensity=record.offer_probability,
                proposal_propensity=record.proposal_probability,
                joint_action_propensity=record.joint_action_probability,
                status=terminal.status,
                measurement=terminal.measurement,
                reward_q_hat_control=record.reward_q_hat_control,
                reward_q_hat_treated=record.reward_q_hat_treated,
                risk_q_hat_control=record.risk_q_hat_control,
                risk_q_hat_treated=record.risk_q_hat_treated,
            )
        )
    return tuple(observations)


def lineage_evidence(
    rows: list[LedgerRow],
    immediate: tuple[CausalObservation, ...],
):
    terminals = {
        row.decision.decision_id: row.terminal
        for row in rows
        if row.terminal is not None
    }
    return LineageCreditResolver().resolve(
        tuple(row.decision for row in rows),
        terminals,
        {row.decision_id: row for row in immediate},
        rows[0].mutation_edges if rows else (),
    )


def shadow_lineage_evidence(
    rows: list[LedgerRow],
    immediate: tuple[CausalObservation, ...],
    *,
    lineage_depth: int,
    opportunity_budget: int,
):
    """Re-evaluate a completed ledger under a non-policy lineage endpoint.

    The copied contexts are used only by offline analysis. The decisions, offer
    assignments, terminals, and ancestry are unchanged, so this cannot affect
    the behavior policy that generated the run.
    """

    if lineage_depth < 1:
        raise ValueError("lineage_depth must be positive")
    if opportunity_budget < 1:
        raise ValueError("opportunity_budget must be positive")
    endpoint = (
        "bounded_proximal_utility" if lineage_depth == 1 else "bounded_lineage_utility"
    )
    canonical_budget = 1 if lineage_depth == 1 else opportunity_budget
    contexts = {}
    shadow_decisions = []
    for ledger_row in rows:
        decision = ledger_row.decision
        reward = decision.context.reward.model_copy(
            update={
                "endpoint": endpoint,
                "lineage_depth": lineage_depth,
                "lineage_opportunity_budget": canonical_budget,
            }
        )
        context = decision.context.model_copy(update={"reward": reward})
        contexts[decision.decision_id] = context
        shadow_decisions.append(decision.model_copy(update={"context": context}))
    shadow_immediate = {
        row.decision_id: row.model_copy(update={"context": contexts[row.decision_id]})
        for row in immediate
    }
    terminals = {
        row.decision.decision_id: row.terminal
        for row in rows
        if row.terminal is not None
    }
    outcomes, rewards = LineageCreditResolver().resolve(
        tuple(shadow_decisions),
        terminals,
        shadow_immediate,
        rows[0].mutation_edges if rows else (),
    )
    return (
        tuple(shadow_immediate[row.decision_id] for row in immediate),
        outcomes,
        rewards,
    )


def evaluate_ope(
    reward_observations: tuple[CausalObservation, ...],
    safety_observations: tuple[CausalObservation, ...],
    *,
    reward_estimand: Literal["immediate_d1", "lineage_residual"],
) -> list[dict[str, Any]]:
    """Evaluate offer-gate alternatives for one explicitly named reward endpoint."""

    if not reward_observations and not safety_observations:
        return []
    evaluator = ConditionalOfferDREvaluator()
    reports: list[dict[str, Any]] = []
    for target in (0.0, 0.25, 0.5, 0.75, 1.0):

        def target_policy(_unit: Any, probability: float = target) -> float:
            return probability

        endpoint_reports = []
        if reward_observations:
            endpoint_reports.append(
                (
                    "reward",
                    evaluator.evaluate_reward(
                        reward_observations,
                        target_offer_probability=target_policy,
                    ),
                )
            )
        if safety_observations:
            endpoint_reports.append(
                (
                    "invalidity",
                    evaluator.evaluate_invalidity(
                        safety_observations,
                        target_offer_probability=target_policy,
                    ),
                )
            )
        for endpoint, report in endpoint_reports:
            observations = (
                reward_observations if endpoint == "reward" else safety_observations
            )
            reports.append(
                {
                    "target_offer_probability": target,
                    "behavior_offer_probability": float(
                        np.mean([row.offer_propensity for row in observations])
                    ),
                    "endpoint_kind": endpoint,
                    "reward_estimand": (
                        reward_estimand if endpoint == "reward" else ""
                    ),
                    **report.model_dump(mode="json"),
                }
            )
    return reports


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _series(
    rows: list[dict[str, Any]], key: str, default: float = np.nan
) -> np.ndarray:
    return np.asarray(
        [default if row.get(key) is None else float(row[key]) for row in rows],
        dtype=float,
    )


def randomized_support_h50(lam: float, offer: float = 0.5) -> float | None:
    """Cold-start median opportunities to collect two outcomes in each arm.

    This deliberately starts from zero treated and zero control observations. It
    is a throughput diagnostic at the observed randomized-evidence rate, not a
    forecast of the remaining time for a lineage that already has evidence.
    """
    if not math.isfinite(lam) or lam <= 0.0:
        return None
    lam = min(lam, 1.0)
    p_treated = lam * offer
    p_control = lam * (1.0 - offer)
    p_none = 1.0 - lam

    def ready_probability(n: int) -> float:
        def below_two(p: float) -> float:
            q = 1.0 - p
            return q**n + n * p * q ** max(n - 1, 0)

        both_below = (
            p_none**n
            + n * p_treated * p_none ** max(n - 1, 0)
            + n * p_control * p_none ** max(n - 1, 0)
            + n * (n - 1) * p_treated * p_control * p_none ** max(n - 2, 0)
        )
        return max(
            0.0,
            min(1.0, 1.0 - below_two(p_treated) - below_two(p_control) + both_below),
        )

    high = 1
    while high < 10_000_000 and ready_probability(high) < 0.5:
        high *= 2
    if high >= 10_000_000:
        return None
    low = 1
    while low < high:
        mid = (low + high) // 2
        if ready_probability(mid) >= 0.5:
            high = mid
        else:
            low = mid + 1
    return float(low)


def canonical_treatment_ids(rows: list[LedgerRow]) -> dict[str, str]:
    """Map historical card ids onto the latest observed merged survivor."""

    parent: dict[str, str] = {}
    snapshots: list[tuple[int, str]] = []

    def find(card_id: str) -> str:
        root = parent.setdefault(card_id, card_id)
        while root != parent[root]:
            root = parent[root]
        while card_id != root:
            next_id = parent[card_id]
            parent[card_id] = root
            card_id = next_id
        return root

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for row in rows:
        for card in row.decision.lineage_registry:
            lineage = (card.treatment_id, *card.bank_lineage_ids)
            for card_id in lineage:
                union(lineage[0], card_id)
            snapshots.append((row.decision.event_ordinal, card.treatment_id))

    latest_by_component: dict[str, tuple[int, str]] = {}
    for ordinal, treatment_id in snapshots:
        root = find(treatment_id)
        latest_by_component[root] = max(
            latest_by_component.get(root, (-1, "")),
            (ordinal, treatment_id),
        )
    return {card_id: latest_by_component[find(card_id)][1] for card_id in parent}


def evidence_lifecycle(
    rows: list[LedgerRow],
    candidates: list[dict[str, Any]],
    *,
    canonical_ids: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    by_decision = {row.decision.decision_id: row for row in rows}
    selected = [row for row in candidates if row["selected"]]
    canonical = dict(canonical_ids or canonical_treatment_ids(rows))
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in selected:
        treatment_id = canonical.get(row["treatment_id"], row["treatment_id"])
        grouped.setdefault(treatment_id, []).append(row)
    actions_by_decision: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for candidate in candidates:
        treatment_id = canonical.get(
            candidate["treatment_id"], candidate["treatment_id"]
        )
        actions_by_decision.setdefault(candidate["decision_id"], {}).setdefault(
            treatment_id, []
        ).append(candidate)
    closure_rate = sum(
        by_decision[item["decision_id"]].terminal is not None
        and by_decision[item["decision_id"]].terminal.ope_eligible
        and by_decision[item["decision_id"]].terminal.status != "censored"
        for item in selected
    ) / max(len(selected), 1)
    last_ordinal = max((row["ordinal"] for row in candidates), default=0)
    result: list[dict[str, Any]] = []
    for treatment_id, offers in sorted(grouped.items()):
        treated = cited = ignored = controls = closed = 0
        contexts: set[str] = set()
        for offer in offers:
            ledger_row = by_decision[offer["decision_id"]]
            terminal = ledger_row.terminal
            if (
                terminal is not None
                and terminal.ope_eligible
                and terminal.status != "censored"
            ):
                closed += 1
                if ledger_row.decision.delivered:
                    treated += 1
                    proposed_card = next(
                        card
                        for card in ledger_row.decision.candidates
                        if card.treatment_id
                        == ledger_row.decision.proposed_treatment_id
                    )
                    if proposed_card.bank_card_id in terminal.used_card_ids:
                        cited += 1
                    else:
                        ignored += 1
                else:
                    controls += 1
                contexts.add(ledger_row.decision.context_hash)
        active_opportunities = eligible_opportunities = slate_opportunities = 0
        proposal_mass = treated_mass = control_mass = 0.0
        first_active_ordinal: int | None = None
        for ledger_row in rows:
            decision = ledger_row.decision
            active_ids = {
                canonical.get(card_id, card_id)
                for card in decision.lineage_registry
                for card_id in (card.treatment_id, *card.bank_lineage_ids)
            }
            if treatment_id not in active_ids:
                continue
            active_opportunities += 1
            first_active_ordinal = (
                decision.event_ordinal
                if first_active_ordinal is None
                else min(first_active_ordinal, decision.event_ordinal)
            )
            eligible_ids = {
                canonical.get(card_id, card_id)
                for card_id in decision.candidate_universe.eligible_bank_card_ids
            }
            eligible_opportunities += treatment_id in eligible_ids
            actions = actions_by_decision.get(decision.decision_id, {}).get(
                treatment_id, []
            )
            slate_opportunities += bool(actions)
            proposal_mass += sum(
                float(action["proposal_probability"]) for action in actions
            )
            treated_mass += sum(
                float(action["joint_treated_probability"]) for action in actions
            )
            control_mass += sum(
                float(action["joint_control_probability"]) for action in actions
            )
        rho = proposal_mass / active_opportunities if active_opportunities else 0.0
        effective_treated_rate = (
            closure_rate * treated_mass / active_opportunities
            if active_opportunities
            else 0.0
        )
        effective_control_rate = (
            closure_rate * control_mass / active_opportunities
            if active_opportunities
            else 0.0
        )
        lam = effective_treated_rate + effective_control_rate
        effective_offer = effective_treated_rate / lam if lam > 0.0 else None
        ess = (
            0.0
            if treated + controls == 0
            else 4.0 * treated * controls / (treated + controls)
        )
        result.append(
            {
                "treatment_id": treatment_id,
                "component_treatment_ids": "|".join(
                    sorted({row["treatment_id"] for row in offers})
                ),
                "first_ordinal": min(row["ordinal"] for row in offers),
                "first_active_ordinal": first_active_ordinal,
                "last_ordinal": max(row["ordinal"] for row in offers),
                "age_decisions": last_ordinal - min(row["ordinal"] for row in offers),
                "offers": len(offers),
                "closed": closed,
                "treated": treated,
                "cited": cited,
                "ignored": ignored,
                "control": controls,
                "contexts": len(contexts),
                "balanced_ess": ess,
                "active_decision_opportunities": active_opportunities,
                "eligible_decision_opportunities": eligible_opportunities,
                "slate_decision_opportunities": slate_opportunities,
                "mean_proposal_probability": rho,
                "mean_offer_probability": effective_offer,
                "closure_rate": closure_rate,
                "effective_treated_rate": effective_treated_rate,
                "effective_control_rate": effective_control_rate,
                "effective_randomized_rate": lam,
                "randomized_evidence_h50": (
                    randomized_support_h50(lam, effective_offer)
                    if effective_offer is not None
                    else None
                ),
                "support_ready": cited >= 2 and controls >= 2 and len(contexts) >= 2,
            }
        )
    return result


def invalid_penalty_sensitivity(
    decisions: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    top_by_k: dict[float, dict[int, str]] = {k: {} for k in (0.0, 0.5, 1.0)}
    for candidate in candidates:
        p0 = float(candidate["control_invalid_probability"])
        p1 = float(candidate["treated_invalid_probability"])
        q0 = float(candidate["usable_gain_control_mean"])
        q1 = float(candidate["usable_gain_treated_mean"])
        worst = float(candidate["worst_feasible_gain"])
        v0 = (q0 - p0 * worst) / max(1.0 - p0, 1e-9)
        v1 = (q1 - p1 * worst) / max(1.0 - p1, 1e-9)
        for k in (0.0, 0.5, 1.0):
            adjusted0 = (1.0 - p0) * v0 + p0 * (k * worst)
            adjusted1 = (1.0 - p1) * v1 + p1 * (k * worst)
            rows.append(
                {
                    "decision_id": candidate["decision_id"],
                    "ordinal": candidate["ordinal"],
                    "treatment_id": candidate["treatment_id"],
                    "penalty_multiplier": k,
                    "effect": adjusted1 - adjusted0,
                    "leverage": abs((p1 - p0) * worst),
                    "safe": candidate["safe"],
                }
            )
            current = top_by_k[k].get(candidate["ordinal"])
            if current is None:
                top_by_k[k][candidate["ordinal"]] = candidate["treatment_id"]
            else:
                prior = next(
                    row["effect"]
                    for row in rows
                    if row["ordinal"] == candidate["ordinal"]
                    and row["treatment_id"] == current
                    and row["penalty_multiplier"] == k
                )
                if adjusted1 - adjusted0 > prior:
                    top_by_k[k][candidate["ordinal"]] = candidate["treatment_id"]
    baseline = top_by_k[1.0]
    summaries: dict[str, Any] = {"safety_sets_unchanged": True}
    for k in (0.0, 0.5):
        compared = [o for o, treatment in top_by_k[k].items() if o in baseline]
        summaries[f"top_action_agreement_k_{k:g}"] = (
            sum(top_by_k[k][o] == baseline[o] for o in compared) / len(compared)
            if compared
            else None
        )
    summaries["max_leverage"] = max((row["leverage"] for row in rows), default=0.0)
    summaries["sign_flips_vs_k1"] = sum(
        row["penalty_multiplier"] != 1.0
        and any(
            base["decision_id"] == row["decision_id"]
            and base["treatment_id"] == row["treatment_id"]
            and base["effect"] * row["effect"] < 0
            for base in rows
            if base["penalty_multiplier"] == 1.0
        )
        for row in rows
    )
    return rows, summaries


def render_dashboard(
    output: Path,
    decisions: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    terminals: list[dict[str, Any]],
) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(4, 2, figsize=(16, 19), constrained_layout=True)
    fig.suptitle("Memory v2 causal-bandit smoke audit", fontsize=18)
    x = _series(decisions, "ordinal")

    ax = axes[0, 0]
    ax.plot(
        x, _series(decisions, "abstain_probability"), label="abstain", color="#555555"
    )
    ax.plot(
        x,
        _series(decisions, "eligible_bank_count"),
        label="eligible bank",
        color="#777777",
    )
    ax.plot(x, _series(decisions, "candidate_count"), label="slate", color="#247ba0")
    ax.plot(
        x,
        _series(decisions, "applicable_count"),
        label="RAG applicable",
        color="#6a4c93",
    )
    ax.plot(x, _series(decisions, "safe_count"), label="admitted", color="#2a9d8f")
    ax.set(title="Policy support", xlabel="decision ordinal")
    ax.legend()

    ax = axes[0, 1]
    proposed = [row for row in decisions if row["proposed"]]
    px = _series(proposed, "ordinal")
    ax.plot(
        px,
        _series(proposed, "proposal_probability"),
        "o-",
        label="proposal rho",
        color="#247ba0",
    )
    ax.plot(
        px,
        _series(proposed, "offer_probability"),
        "o-",
        label="offer e",
        color="#e76f51",
    )
    ax.plot(
        px,
        _series(proposed, "joint_action_probability"),
        "o-",
        label="realized joint",
        color="#6a4c93",
    )
    ax.set(
        title="Realized action propensities",
        xlabel="decision ordinal",
        ylim=(-0.02, 1.02),
    )
    ax.legend()

    ax = axes[1, 0]
    selected = [row for row in candidates if row["selected"]]
    sx = _series(selected, "ordinal")
    effect = _series(selected, "usable_effect_mean")
    effect_sd = _series(selected, "usable_effect_sd")
    ax.errorbar(
        sx,
        effect,
        yerr=effect_sd,
        fmt="o",
        capsize=3,
        color="#247ba0",
        label="usable effect +/- SD",
    )
    ax.axhline(0.0, color="#333333", linewidth=1)
    ax.set(title="Selected-card posterior effect", xlabel="decision ordinal")
    ax.legend()

    ax = axes[1, 1]
    ax.plot(
        sx,
        _series(selected, "probability_helpful"),
        "o-",
        label="P(helpful)",
        color="#2a9d8f",
    )
    gate_label = (
        "P(increment acceptable)"
        if decisions
        and decisions[0]["safety_gate_mode"] == "exclude_confident_incremental_harm"
        else "P(joint safe)"
    )
    ax.plot(
        sx,
        _series(selected, "probability_safe"),
        "o-",
        label=gate_label,
        color="#6a4c93",
    )
    ax.plot(
        sx,
        _series(selected, "treated_invalid_probability"),
        "o-",
        label="treated invalid",
        color="#e76f51",
    )
    ax.plot(
        sx,
        _series(selected, "control_invalid_probability"),
        "o-",
        label="control invalid",
        color="#f4a261",
    )
    ax.set(
        title="Selected-card posterior probabilities",
        xlabel="decision ordinal",
        ylim=(-0.02, 1.02),
    )
    ax.legend(ncol=2)

    ax = axes[2, 0]
    ax.plot(
        x,
        _series(decisions, "evidence_count"),
        label="eligible evidence",
        color="#247ba0",
    )
    ax.plot(
        x,
        _series(decisions, "reward_observations"),
        label="valid reward rows",
        color="#2a9d8f",
    )
    ax.plot(
        x,
        _series(decisions, "pending_count"),
        label="pending proposals",
        color="#f4a261",
    )
    ax.plot(x, _series(decisions, "censored_count"), label="censored", color="#e76f51")
    ax.set(title="Evidence accounting", xlabel="decision ordinal")
    ax.legend()

    ax = axes[2, 1]
    ax.semilogy(
        x,
        np.maximum(_series(decisions, "safety_gradient_inf"), 1e-16),
        label="safety gradient inf",
        color="#e76f51",
    )
    ax.semilogy(
        x,
        np.maximum(_series(decisions, "safety_hessian_condition"), 1.0),
        label="Hessian condition",
        color="#6a4c93",
    )
    ax.semilogy(
        x,
        _series(decisions, "reward_residual_sd"),
        label="reward residual SD",
        color="#247ba0",
    )
    ax.semilogy(
        x,
        _series(decisions, "reward_card_effect_sd"),
        label="card SD",
        color="#2a9d8f",
    )
    ax.set(title="Posterior numerical health", xlabel="decision ordinal")
    ax.legend(ncol=2)

    ax = axes[3, 0]
    gain_rows = [row for row in terminals if row["gain"] is not None]
    status_colors = {"outcome": "#2a9d8f", "invalid": "#e76f51", "censored": "#777777"}
    for status in ("outcome", "invalid", "censored"):
        group = [row for row in terminals if row["status"] == status]
        if not group:
            continue
        ax.scatter(
            _series(group, "ordinal"),
            [0.0 if row["gain"] is None else row["gain"] for row in group],
            label=status,
            color=status_colors[status],
            s=42,
        )
    if not gain_rows and not terminals:
        ax.text(
            0.5,
            0.5,
            "No terminal outcomes",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
    ax.axhline(0.0, color="#333333", linewidth=1)
    ax.set(title="Terminal proximal gain and failures", xlabel="decision ordinal")
    ax.legend()

    ax = axes[3, 1]
    ax.plot(
        x, _series(decisions, "map_coverage"), label="archive coverage", color="#247ba0"
    )
    ax.plot(
        x,
        _series(decisions, "parent_quality_quantile"),
        label="parent quality quantile",
        color="#2a9d8f",
    )
    ax.plot(
        x,
        _series(decisions, "neighbor_occupancy"),
        label="neighbor occupancy",
        color="#e76f51",
    )
    ax.plot(
        x,
        _series(decisions, "parent_fitness"),
        label="absolute parent fitness",
        color="#6a4c93",
    )
    ax.set(
        title="Frozen MAP-Elites context", xlabel="decision ordinal", ylim=(-0.02, 1.02)
    )
    ax.legend(ncol=2)

    fig.savefig(output, dpi=180)
    plt.close(fig)


def render_calibration(output: Path, decisions: list[dict[str, Any]]) -> None:
    proposed = [row for row in decisions if row["proposed"]]
    offers = _series(proposed, "offer_probability", 0.0)
    observed = np.asarray([float(row["delivered"]) for row in proposed])
    x = np.arange(1, len(proposed) + 1)
    residual = np.cumsum(observed - offers)
    band = 2.0 * np.sqrt(np.maximum(np.cumsum(offers * (1.0 - offers)), 1e-12))

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(11, 5), constrained_layout=True)
    ax.axhline(0.0, color="#333333", linewidth=1)
    ax.fill_between(
        x, -band, band, color="#247ba0", alpha=0.15, label="+/- 2 conditional SD"
    )
    ax.plot(x, residual, "o-", color="#e76f51", label="cumulative delivered - expected")
    ax.set(
        title="Conditional-offer randomization calibration",
        xlabel="proposed decisions",
        ylabel="cumulative residual",
    )
    ax.legend()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def render_ope(output: Path, reports: list[dict[str, Any]]) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for ax, endpoint, title in (
        (axes[0], "reward", "DR immediate D1 reward endpoint"),
        (axes[1], "invalidity", "DR invalidity probability"),
    ):
        rows = [row for row in reports if row["endpoint_kind"] == endpoint]
        x = _series(rows, "target_offer_probability")
        y = _series(rows, "estimate")
        ax.plot(x, y, "o-", color="#247ba0")
        behavior = float(rows[0]["behavior_offer_probability"]) if rows else 0.5
        ax.axvline(
            behavior,
            color="#555555",
            linestyle="--",
            label=f"behavior e={behavior:.2g}",
        )
        if endpoint == "reward":
            ax.axhline(0.0, color="#333333", linewidth=1)
        else:
            ax.set_ylim(-0.02, 1.02)
        ax.set(title=title, xlabel="target offer probability")
        ax.legend()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def render_lifecycle(output: Path, lifecycle: list[dict[str, Any]]) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    labels = [row["treatment_id"][:10] for row in lifecycle]
    x = np.arange(len(lifecycle))
    axes[0].bar(x - 0.18, _series(lifecycle, "treated", 0.0), 0.36, label="treated")
    axes[0].bar(x + 0.18, _series(lifecycle, "control", 0.0), 0.36, label="control")
    axes[0].set(title="Stable-card randomized evidence", ylabel="closed outcomes")
    axes[0].set_xticks(x, labels, rotation=45, ha="right")
    axes[0].legend()
    h50 = _series(lifecycle, "randomized_evidence_h50")
    age = _series(lifecycle, "age_decisions")
    axes[1].scatter(h50, age, c="#247ba0")
    finite = h50[np.isfinite(h50)]
    if finite.size:
        bound = max(float(np.max(finite)), float(np.max(age)), 1.0)
        axes[1].plot([0, bound], [0, bound], "--", color="#777777", label="age = H50")
    axes[1].set(
        title="Evidence half-life vs observed age",
        xlabel="Cold-start H50 opportunities from zero evidence",
        ylabel="age",
    )
    axes[1].legend()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def render_penalty_sensitivity(output: Path, sensitivity: list[dict[str, Any]]) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    for k, color in ((0.0, "#247ba0"), (0.5, "#f4a261"), (1.0, "#2a9d8f")):
        group = [row for row in sensitivity if row["penalty_multiplier"] == k]
        ax.scatter(
            _series(group, "ordinal"),
            _series(group, "effect"),
            s=20,
            alpha=0.7,
            label=f"k={k:g}",
            color=color,
        )
    ax.axhline(0.0, color="#333333", linewidth=1)
    ax.set(
        title="Invalid-penalty mean-level sensitivity",
        xlabel="decision ordinal",
        ylabel="treated - control effect",
    )
    ax.legend()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def apply_smoke_gates(
    rows: list[LedgerRow],
    decisions: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    audit: Audit,
    args: argparse.Namespace,
) -> None:
    proposed = [row for row in rows if row.decision.proposed_treatment_id is not None]
    eligible = [
        row
        for row in proposed
        if row.terminal is not None
        and row.terminal.status != "censored"
        and row.terminal.ope_eligible
    ]
    delivered = sum(row.decision.delivered for row in proposed)
    controls = len(proposed) - delivered
    maximum_evidence = max(
        (row.decision.fit_diagnostics.evidence_count for row in rows), default=0
    )
    pending = sum(row.terminal is None for row in rows)

    audit.require(
        len(rows) >= args.min_decisions,
        f"smoke produced {len(rows)} decisions; need at least {args.min_decisions}",
    )
    audit.require(
        len(candidates) >= args.min_candidate_rows,
        f"smoke produced {len(candidates)} candidate rows; need at least "
        f"{args.min_candidate_rows}",
    )
    audit.require(
        len(proposed) >= args.min_proposals,
        f"smoke produced {len(proposed)} proposals; need at least {args.min_proposals}",
    )
    audit.require(
        delivered >= args.min_delivered,
        f"smoke produced {delivered} treated offers; need at least {args.min_delivered}",
    )
    audit.require(
        controls >= args.min_controls,
        f"smoke produced {controls} randomized controls; need at least {args.min_controls}",
    )
    audit.require(
        len(eligible) >= args.min_terminal_evidence,
        f"smoke produced {len(eligible)} eligible proposal terminals; need at least "
        f"{args.min_terminal_evidence}",
    )
    audit.require(
        maximum_evidence >= args.min_posterior_evidence,
        f"posterior saw at most {maximum_evidence} earlier terminals; need at least "
        f"{args.min_posterior_evidence}",
    )
    audit.require(
        pending <= args.max_pending,
        f"ledger has {pending} pending terminals; maximum is {args.max_pending}",
    )

    if proposed:
        residual = sum(
            float(row.decision.delivered) - float(row.decision.offer_probability)
            for row in proposed
        )
        variance = sum(
            float(row.decision.offer_probability)
            * (1.0 - float(row.decision.offer_probability))
            for row in proposed
        )
        z_score = abs(residual) / math.sqrt(max(variance, 1e-12))
        audit.require(
            z_score <= args.max_offer_imbalance_z,
            f"offer randomization imbalance z={z_score:.3f} exceeds "
            f"{args.max_offer_imbalance_z}",
        )


def summarize(
    rows: list[LedgerRow],
    decisions: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    terminals: list[dict[str, Any]],
    audit: Audit,
    integrity: str,
    ope_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    statuses = {
        status: sum(row["status"] == status for row in terminals)
        for status in ("outcome", "invalid", "censored")
    }
    proposed = [row for row in decisions if row["proposed"]]
    safe_rows = [row for row in candidates if row["safe"]]
    policy = rows[-1].decision.policy
    admission_boundary = (
        policy.safety_alpha
        if policy.safety_gate_mode == "exclude_confident_incremental_harm"
        else 1.0 - policy.safety_alpha
    )
    boundary_rows = [
        row
        for row in candidates
        if abs(row["probability_safe"] - admission_boundary) <= 0.05
        or (
            policy.max_treated_invalid_probability is not None
            and abs(
                row["treated_invalid_upper"] - policy.max_treated_invalid_probability
            )
            <= 0.03
        )
    ]
    closed_deliveries = [
        row
        for row in rows
        if row.decision.delivered
        and row.decision.proposed_treatment_id is not None
        and row.terminal is not None
        and row.terminal.status != "censored"
        and row.terminal.ope_eligible
    ]
    cited_deliveries = sum(
        next(
            card
            for card in row.decision.candidates
            if card.treatment_id == row.decision.proposed_treatment_id
        ).bank_card_id
        in row.terminal.used_card_ids
        for row in closed_deliveries
        if row.terminal is not None
    )
    return {
        "audit_passed": not audit.errors,
        "sqlite_integrity": integrity,
        "decisions": len(rows),
        "proposals": len(proposed),
        "delivered": sum(row["delivered"] for row in proposed),
        "closed_deliveries": len(closed_deliveries),
        "cited_deliveries": cited_deliveries,
        "ignored_deliveries": len(closed_deliveries) - cited_deliveries,
        "citation_rate": (
            cited_deliveries / len(closed_deliveries) if closed_deliveries else None
        ),
        "controls": sum(not row["delivered"] for row in proposed),
        "abstentions": sum(not row["proposed"] for row in decisions),
        "pending_terminals": sum(row.terminal is None for row in rows),
        "terminal_statuses": statuses,
        "candidate_rows": len(candidates),
        "safe_candidate_rows": len(safe_rows),
        "applicability": {
            "universe_status_counts": {
                status.value: sum(
                    row["candidate_universe_status"] == status for row in decisions
                )
                for status in CandidateUniverseStatus
            },
            "status_counts": {
                status.value: sum(
                    row["applicability_status"] == status for row in decisions
                )
                for status in ApplicabilityStatus
            },
            "mean_eligible_bank_size": (
                float(np.mean(_series(decisions, "eligible_bank_count")))
                if decisions
                else 0.0
            ),
            "mean_applicable_size": (
                float(np.mean(_series(decisions, "applicable_count")))
                if decisions
                else 0.0
            ),
            "mean_final_slate_size": (
                float(np.mean(_series(decisions, "candidate_count")))
                if decisions
                else 0.0
            ),
        },
        "safety_gate_mode": policy.safety_gate_mode,
        "boundary_risk_rows": len(boundary_rows),
        "abstention_reasons": {
            reason: sum(row["abstention_reason"] == reason for row in decisions)
            for reason in (
                "no_candidates",
                "no_feasible_candidates",
                "reward_policy_or_abstain",
            )
        },
        "maximum_posterior_evidence": max(
            (row["evidence_count"] for row in decisions), default=0
        ),
        "ope_reports": len(ope_reports),
        "mean_offer_probability": (
            float(np.mean(_series(proposed, "offer_probability"))) if proposed else None
        ),
        "mean_selected_probability_safe": (
            float(
                np.mean(
                    _series(
                        [row for row in candidates if row["selected"]],
                        "probability_safe",
                    )
                )
            )
            if proposed
            else None
        ),
        "max_safety_gradient_inf": (
            float(np.max(_series(decisions, "safety_gradient_inf")))
            if decisions
            else None
        ),
        "max_safety_hessian_condition": (
            float(np.max(_series(decisions, "safety_hessian_condition")))
            if decisions
            else None
        ),
        "errors": audit.errors,
        "warnings": audit.warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--min-decisions", type=int, default=8)
    parser.add_argument("--min-candidate-rows", type=int, default=8)
    parser.add_argument("--min-proposals", type=int, default=6)
    parser.add_argument("--min-delivered", type=int, default=1)
    parser.add_argument("--min-controls", type=int, default=1)
    parser.add_argument("--min-terminal-evidence", type=int, default=6)
    parser.add_argument("--min-posterior-evidence", type=int, default=1)
    parser.add_argument("--max-pending", type=int, default=0)
    parser.add_argument("--max-offer-imbalance-z", type=float, default=4.0)
    args = parser.parse_args()

    audit = Audit()
    rows, integrity = load_ledger(args.ledger, audit)
    audit_rows(rows, audit)
    decisions, candidates, terminals = flatten(rows)
    lifecycle = evidence_lifecycle(rows, candidates)
    penalty_sensitivity, penalty_summary = invalid_penalty_sensitivity(
        decisions, candidates
    )
    apply_smoke_gates(rows, decisions, candidates, audit, args)
    observations = causal_observations(rows)
    lineage_outcomes, lineage_observations = lineage_evidence(rows, observations)
    ope_reports = evaluate_ope(
        observations,
        observations,
        reward_estimand="immediate_d1",
    )
    audit.require(
        len(ope_reports) == 10,
        "conditional-offer OPE did not cover all reward/risk target policies",
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(args.output_dir / "decision_trace.csv", decisions)
    _write_csv(args.output_dir / "candidate_posterior_trace.csv", candidates)
    _write_csv(args.output_dir / "terminal_trace.csv", terminals)
    _write_csv(
        args.output_dir / "lineage_outcome_trace.csv",
        [row.model_dump(mode="json") for row in lineage_outcomes],
    )
    _write_csv(args.output_dir / "ope_trace.csv", ope_reports)
    _write_csv(args.output_dir / "card_evidence_lifecycle.csv", lifecycle)
    _write_csv(args.output_dir / "invalid_penalty_sensitivity.csv", penalty_sensitivity)
    render_dashboard(
        args.output_dir / "memory_v2_dashboard.png", decisions, candidates, terminals
    )
    render_calibration(args.output_dir / "offer_calibration.png", decisions)
    render_ope(args.output_dir / "ope_sensitivity.png", ope_reports)
    render_lifecycle(args.output_dir / "card_evidence_lifecycle.png", lifecycle)
    render_penalty_sensitivity(
        args.output_dir / "invalid_penalty_sensitivity.png", penalty_sensitivity
    )
    (args.output_dir / "ope_report.json").write_text(
        json.dumps(ope_reports, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = summarize(
        rows, decisions, candidates, terminals, audit, integrity, ope_reports
    )
    summary["card_evidence_lifecycle"] = lifecycle
    summary["lineage_outcomes"] = {
        status: sum(row.status == status for row in lineage_outcomes)
        for status in ("outcome", "invalid", "pending", "censored")
    }
    summary["lineage_residual_observations"] = len(lineage_observations)
    summary["invalid_penalty_sensitivity"] = penalty_summary
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report = [
        "# Memory v2 Smoke Audit",
        "",
        f"- Audit: {'PASS' if summary['audit_passed'] else 'FAIL'}",
        f"- SQLite integrity: `{integrity}`",
        f"- Decisions: {summary['decisions']}",
        f"- Proposed / delivered / control / abstained: {summary['proposals']} / {summary['delivered']} / {summary['controls']} / {summary['abstentions']}",
        f"- Closed delivered / cited / ignored / citation rate: {summary['closed_deliveries']} / {summary['cited_deliveries']} / {summary['ignored_deliveries']} / {summary['citation_rate']}",
        f"- Terminal outcomes / invalid / censored / pending: {summary['terminal_statuses']['outcome']} / {summary['terminal_statuses']['invalid']} / {summary['terminal_statuses']['censored']} / {summary['pending_terminals']}",
        f"- Candidate posterior rows / feasible rows: {summary['candidate_rows']} / {summary['safe_candidate_rows']}",
        f"- Applicability status counts: {summary['applicability']['status_counts']}",
        f"- Mean eligible / RAG-applicable / final slate sizes: {summary['applicability']['mean_eligible_bank_size']:.2f} / {summary['applicability']['mean_applicable_size']:.2f} / {summary['applicability']['mean_final_slate_size']:.2f}",
        f"- Boundary-risk candidate rows: {summary['boundary_risk_rows']}",
        f"- Abstention reasons: {summary['abstention_reasons']}",
        f"- Maximum earlier evidence seen by a posterior: {summary['maximum_posterior_evidence']}",
        f"- Conditional-offer DR reports: {summary['ope_reports']}",
        f"- Maximum safety gradient infinity norm: {summary['max_safety_gradient_inf']}",
        f"- Maximum safety Hessian condition: {summary['max_safety_hessian_condition']}",
        f"- Stable treatments observed / support-ready: {len(lifecycle)} / {sum(row['support_ready'] for row in lifecycle)}",
        f"- Median cold-start randomized-evidence H50 from zero evidence: {np.nanmedian(_series(lifecycle, 'randomized_evidence_h50')) if lifecycle else None}",
        f"- Invalid-penalty top-action agreement (k=0 / 0.5 vs k=1): {penalty_summary.get('top_action_agreement_k_0')} / {penalty_summary.get('top_action_agreement_k_0.5')}",
        "",
        "## Errors",
        *(f"- {message}" for message in audit.errors),
        "" if audit.errors else "- None",
        "",
        "## Warnings",
        *(f"- {message}" for message in audit.warnings),
        "" if audit.warnings else "- None",
    ]
    (args.output_dir / "report.md").write_text(
        "\n".join(report).rstrip() + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["audit_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
