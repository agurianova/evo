from __future__ import annotations

from pathlib import Path

from problems.pmhctcr.pipeline import resolve_validator_timeout

REPO = Path(__file__).resolve().parents[2]


def test_resolve_validator_timeout_never_shrinks_stage_budget():
    assert resolve_validator_timeout(240, 900) == 900
    assert resolve_validator_timeout(3600, 900) == 3600
    assert resolve_validator_timeout(3600, None) == 3600


def test_launcher_splits_pdb_validator_timeout():
    text = (REPO / "scripts" / "launch_pmhctcr_terra_smoke.sh").read_text()
    assert "stage_timeout=240" in text
    assert "validator_timeout=900" in text
    assert "dag_timeout=1800" in text
    assert "request_timeout=180" in text


def test_experiment_wires_pmhctcr_pipeline_builder():
    text = (REPO / "config" / "experiment" / "pmhctcr.yaml").read_text()
    assert "PmhctcrGuidedPipelineBuilder" in text
    assert "validator_timeout" in text
