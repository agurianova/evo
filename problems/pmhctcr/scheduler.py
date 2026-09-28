"""UCB1 operator scheduler. Reuses gigaevo.llm.bandit.SlidingWindowUCB1."""

from __future__ import annotations

import numpy as np

from gigaevo.llm.bandit import SlidingWindowUCB1

from problems.pmhctcr.genotype import OPERATOR_IDS
from problems.pmhctcr.operators import EARLY_OPS, LATE_OPS, is_applicable

NOOP_WEIGHT = 0.03
EARLY_UNTIL = 10


class OperatorScheduler:
    def __init__(self, *, exploration_constant: float = 1.41, window_size: int = 100):
        self.bandit = SlidingWindowUCB1(
            arm_names=list(OPERATOR_IDS),
            exploration_constant=exploration_constant,
            window_size=window_size,
        )
        self.rng = np.random.default_rng(0)

    def select(self, generation: int, parent) -> str:
        if self.rng.random() < NOOP_WEIGHT:
            return "NOOP"
        ucb = self.bandit.select()
        if generation < EARLY_UNTIL:
            pool = [op for op in EARLY_OPS if is_applicable(parent, op)]
        else:
            pool = [op for op in LATE_OPS if is_applicable(parent, op)]
        if pool and self.rng.random() < 0.5:
            return str(pool[int(self.rng.integers(0, len(pool)))])
        if is_applicable(parent, ucb):
            return ucb
        applicable = [op for op in OPERATOR_IDS if is_applicable(parent, op)]
        return applicable[int(self.rng.integers(0, len(applicable)))]

    def record_pull(self, operator_id: str) -> None:
        base = operator_id.removesuffix("_REJECTED")
        if base in OPERATOR_IDS:
            self.bandit.record_pull(base)

    def update_reward(self, operator_id: str, reward: float) -> None:
        base = operator_id.removesuffix("_REJECTED")
        if base in OPERATOR_IDS:
            self.bandit.update_reward(base, 0.0 if operator_id.endswith("_REJECTED") else reward)
