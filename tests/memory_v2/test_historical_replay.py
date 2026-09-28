from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from experiments.hover.memory_v2_smoke.replay_v1 import (
    ContextResult,
    HistoricalLineage,
    HistoricalMetadata,
    HistoricalMutationOutput,
    HistoricalProgram,
    HistoricalSelection,
    MutationLink,
    RunInputs,
    StoredNoCardEvidence,
    StoredNoCardObservation,
    _confusion,
    _episode_outcome,
    _shadow_cards,
    reconstruct_episodes,
)
from gigaevo.memory.cards import Card


def _inputs(
    *, current_card_description: str = "future checkpoint payload"
) -> RunInputs:
    started = datetime(2026, 7, 15, 8, 0, tzinfo=UTC)
    parent_id = "aaaaaaaa-parent"
    child_id = "bbbbbbbb-child"
    card_id = "card-1"
    parent = HistoricalProgram(
        id=parent_id,
        metrics={
            "fitness": 0.80,
            "is_valid": 1.0,
            "hop_depth": 2.0,
            "passages_fetched": 5.0,
            "instr_chars": 500.0,
        },
        iteration=4,
        state="done",
        lineage=HistoricalLineage(generation=2),
        created_at=started,
    )
    child = HistoricalProgram(
        id=child_id,
        metrics={"fitness": 0.79, "is_valid": 1.0},
        metadata=HistoricalMetadata(
            memory_base_selected_idea_ids=(),
            memory_injected_idea_ids=(),
            memory_base_metrics={"fitness": 0.80},
            memory_base_id=parent_id,
            memory_no_card_control=False,
            mutation_output=HistoricalMutationOutput(card_ids_used=()),
        ),
        iteration=5,
        state="done",
        lineage=HistoricalLineage(parents=(parent_id,), generation=3),
        created_at=started + timedelta(seconds=3),
    )
    selection = HistoricalSelection(
        event="MEMORY_READ_SELECTION",
        timestamp_utc=started + timedelta(seconds=1),
        decision_id="memsel-immutable-assignment",
        program_id=parent_id,
        selected_ids=(card_id,),
        candidate_ids=(card_id,),
    )
    return RunInputs(
        run_dir=Path("/historical/run"),
        checkpoint_dir=Path("/historical/checkpoint"),
        config={
            "pipeline_builder": {"no_card_control_probability": 0.1},
            "problem": {"name": "chains/hover/full7_vectorized"},
        },
        selections=(selection,),
        programs=(parent, child),
        contexts=(
            ContextResult(
                timestamp=started + timedelta(seconds=1, milliseconds=5),
                parent_prefix=parent_id[:8],
                action="withheld",
                card_ids=(card_id,),
            ),
        ),
        mutations=(
            MutationLink(
                timestamp=started + timedelta(seconds=2),
                parent_prefix=parent_id[:8],
                child_prefix=child_id[:8],
            ),
        ),
        metric_times={child_id[:8]: started + timedelta(seconds=4)},
        stored_no_card=StoredNoCardEvidence(
            observations=(
                StoredNoCardObservation(
                    id="cccccccc-false-positive",
                    randomized_control=True,
                    delta=0.01,
                ),
                StoredNoCardObservation(
                    id="dddddddd-true-negative",
                    randomized_control=False,
                    delta=0.02,
                ),
            )
        ),
        cards=(Card(id=card_id, description=current_card_description),),
    )


def test_later_mutable_flag_cannot_relabel_birth_assignment() -> None:
    inputs = _inputs()
    (episode,) = reconstruct_episodes(inputs)

    assert episode.action == "withheld"
    assert not episode.treatment
    assert episode.children[0].mutable_control_flag is False
    assert episode.children[0].stored_randomized_control is False
    assert _episode_outcome(episode, strict_storage_terminal=True) == pytest.approx(
        (-0.01, False, None, None)
    )
    assert _confusion(inputs, (episode,)) == {
        "true_positive": 0,
        "false_positive": 1,
        "false_negative": 1,
        "true_negative": 1,
    }


def test_current_checkpoint_payload_never_becomes_historical_treatment() -> None:
    inputs = _inputs(current_card_description="future revision must not leak")
    episodes = reconstruct_episodes(inputs)

    shadow = _shadow_cards(inputs, episodes)["card-1"]

    assert "future revision" not in shadow.delivered_text
    assert shadow.delivered_text.endswith("Historical treatment identity card-1")
