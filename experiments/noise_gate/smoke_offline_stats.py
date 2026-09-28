"""Offline statistical smoke of the paired archive gate on synthetic evals.

Runs the REAL toy_noise_gate validate() and the REAL selector classes over
controlled program families, and checks the accept rates against the
calibration that justified p_accept=0.75 (null churn ~49% -> ~25%,
truly-worse-by-0.007 <= ~10%, genuine gains kept). No LLM, no engine.

Usage: python experiments/noise_gate/smoke_offline_stats.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from gigaevo.evolution.strategies.paired_selectors import (
    PairedBootstrapArchiveSelector,
)
from gigaevo.evolution.strategies.selectors import SumArchiveSelector
from gigaevo.programs.program import Program, ProgramState
from problems.toy_noise_gate.validate import N_SAMPLES, Y_TRUE, validate

TRIALS = 200


def evaluated_program(preds: np.ndarray) -> Program:
    metrics, artifact = validate(preds)
    return Program(
        code="synthetic",
        state=ProgramState.RUNNING,
        metrics=metrics,
        metadata=dict(artifact["_program_metadata"]),
    )


def preds_with_base_quality(base: float, trial: int) -> np.ndarray:
    """Predictions whose noise-free per-sample score is exactly ``base``.

    The trial index perturbs the error SIGN pattern only, so every trial
    hashes to an independent noise stream at identical true quality.
    """
    err = -np.log(base) / 2.0
    signs = np.where(np.random.default_rng(trial).random(N_SAMPLES) < 0.5, -1.0, 1.0)
    return Y_TRUE + signs * err


def accept_rates(challenger_base: float, elite_base: float) -> tuple[float, float]:
    point = SumArchiveSelector(["fitness"], [True])
    paired = PairedBootstrapArchiveSelector(["fitness"], [True])
    point_hits = paired_hits = 0
    for trial in range(TRIALS):
        elite = evaluated_program(preds_with_base_quality(elite_base, 2 * trial))
        challenger = evaluated_program(
            preds_with_base_quality(challenger_base, 2 * trial + 1)
        )
        point_hits += point(challenger, elite)
        paired_hits += paired(challenger, elite)
    return point_hits / TRIALS, paired_hits / TRIALS


def main() -> int:
    failures: list[str] = []

    def check(label: str, ok: bool, detail: str) -> None:
        print(f"{'PASS' if ok else 'FAIL'}  {label}: {detail}")
        if not ok:
            failures.append(label)

    p_point, p_paired = accept_rates(0.80, 0.80)
    check(
        "null churn (equal quality)",
        0.35 <= p_point <= 0.65 and p_paired <= 0.35 and p_paired < p_point,
        f"point={p_point:.2f} (expect ~0.5), paired={p_paired:.2f} (expect ~0.25)",
    )

    p_point, p_paired = accept_rates(0.793, 0.80)
    check(
        "truly worse by 0.007",
        p_paired <= 0.15 and p_paired < p_point,
        f"point={p_point:.2f} (expect ~0.25-0.35), paired={p_paired:.2f} (expect <=0.10)",
    )

    p_point, p_paired = accept_rates(0.85, 0.80)
    check(
        "genuine gain +0.05",
        p_point >= 0.95 and p_paired >= 0.90,
        f"point={p_point:.2f}, paired={p_paired:.2f} (expect both ~1.0)",
    )

    paired = PairedBootstrapArchiveSelector(["fitness"], [True])
    same = evaluated_program(preds_with_base_quality(0.80, 7))
    twin = evaluated_program(preds_with_base_quality(0.80, 7))
    check(
        "identical program re-eval",
        paired(twin, same) is False,
        "same preds -> same noise -> P=0.5 -> REJECT",
    )

    elite = evaluated_program(preds_with_base_quality(0.80, 11))
    bare = Program(
        code="synthetic",
        state=ProgramState.RUNNING,
        metrics={"fitness": 0.99},
        metadata={},
    )
    point = SumArchiveSelector(["fitness"], [True])
    check(
        "missing vector falls back to point rule",
        paired(bare, elite) == point(bare, elite),
        "no per_sample_scores on challenger -> delegate",
    )

    off = PairedBootstrapArchiveSelector(["fitness"], [True], p_accept=0.5)
    strong = evaluated_program(preds_with_base_quality(0.85, 13))
    check(
        "p_accept=0.5 OFF position",
        off(strong, elite) == point(strong, elite),
        "delegates to SumArchiveSelector",
    )

    print(f"\n{'SMOKE OK' if not failures else 'SMOKE FAILED: ' + ', '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
