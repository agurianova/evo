"""Insight-guided mutation: JSON operator in, generated Python child out.

The genome is still one TZ operator per child (no free JSON rewrite). The
guided pipeline's MutationSuggestionStage writes that insight into
``mutation_context``; this operator reads it, patches GENOTYPE_JSON, then
``render_program`` emits the Python script ``validate()`` execs.

Identical functional genomes (same JSON minus ``meta``) are not re-emitted,
so CREATE_SURFACE from the seed is trained once instead of once per
``parent_id``. A spent insight (duplicate genome) falls through to another
legal operator so the dispatcher does not treat it as a consecutive empty
mutation. A true guided no-op still returns None — no UCB hijack.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gigaevo.evolution.mutation.base import MutationOperator, MutationSpec
from gigaevo.llm.bandit import MutationOutcome, compute_bandit_reward
from gigaevo.programs.program import Program

from problems.pmhctcr.codegen import loads_program, render_program
from problems.pmhctcr.genotype import OPERATOR_IDS, functional_dumps
from problems.pmhctcr.insight_exec import (
    context_from_parent,
    map_operator,
    parse_primary_insight,
)
from problems.pmhctcr.operators import apply_operator, is_applicable
from problems.pmhctcr.scheduler import OperatorScheduler

if TYPE_CHECKING:
    from gigaevo.database.program_storage import ProgramStorage


class PmhctcrMutationOperator(MutationOperator):
    def __init__(self, *, fitness_key: str = "fitness", higher_is_better: bool = True):
        self.fitness_key = fitness_key
        self.higher_is_better = higher_is_better
        self.scheduler = OperatorScheduler()
        self._seen_functional: set[str] = set()

    def _penalize(self, operator_id: str) -> None:
        self.scheduler.record_pull(operator_id)
        self.scheduler.update_reward(operator_id, 0.0)

    def _spec(
        self,
        child,
        parent_prog: Program,
        insight,
        guided_text: str | None,
        parent_fit: float,
        op: str,
    ) -> MutationSpec:
        applied = child.meta.operator_applied or op
        if not str(applied).endswith("_REJECTED"):
            child.meta.parent_id = parent_prog.id
        self.scheduler.record_pull(applied)
        return MutationSpec(
            code=render_program(
                child,
                insight=insight.substitute if guided_text and insight else None,
            ),
            parents=[parent_prog],
            name=child.meta.operator_applied or op,
            metadata={
                MutationSpec.META_OUTPUT: {
                    "archetype": "Component Substitution",
                    "operator": child.meta.operator_applied,
                    "insights_used": [insight.type] if guided_text and insight else [],
                    "justification": (
                        insight.substitute[:500] if guided_text and insight else None
                    ),
                },
                "pmhctcr_operator": child.meta.operator_applied,
                "pmhctcr_parent_fitness": parent_fit,
                "pmhctcr_guided": bool(guided_text),
                "pmhctcr_insight_type": insight.type if guided_text and insight else None,
            },
        )

    def _try_child(
        self,
        parent,
        parent_prog: Program,
        op: str,
        guided_text: str | None,
        insight,
        parent_fit: float,
    ) -> tuple[MutationSpec | None, bool]:
        """Return ``(spec, rejected)``.

        ``rejected`` is True only for a guided no-op (``*_REJECTED``). A
        functional clone is ``(None, False)``: the insight already ran.
        """
        child = apply_operator(parent, op, guided_text=guided_text)
        applied = child.meta.operator_applied or op
        if str(applied).endswith("_REJECTED"):
            self._penalize(applied)
            return None, True
        key = functional_dumps(child)
        if key in self._seen_functional:
            self._penalize(applied)
            return None, False
        self._seen_functional.add(key)
        return self._spec(child, parent_prog, insight, guided_text, parent_fit, op), False

    def _candidate_ops(self, parent, guided_op: str | None, run_step: int) -> list[str]:
        if guided_op:
            return [guided_op] if is_applicable(parent, guided_op) else []
        ordered: list[str] = []
        pick = self.scheduler.select(run_step, parent)
        if is_applicable(parent, pick):
            ordered.append(pick)
        for op in OPERATOR_IDS:
            if op not in ordered and is_applicable(parent, op):
                ordered.append(op)
        return ordered

    async def mutate_single(
        self,
        selected_parents: list[Program],
        memory_instructions: str | None = None,
    ) -> MutationSpec | None:
        if not selected_parents:
            return None
        parent_prog = selected_parents[0]
        parent = loads_program(parent_prog.code)
        self._seen_functional.add(functional_dumps(parent))
        # iteration = engine eval counter; JSON meta.generation = lineage depth.
        # Early/late operator pool is run-level, not overwritten onto the genome.
        run_step = int(parent_prog.iteration or parent.meta.generation)
        context = context_from_parent(parent_prog, memory_instructions)
        insight = parse_primary_insight(context)
        parent_fit = 0.0
        if parent_prog.metrics and self.fitness_key in parent_prog.metrics:
            parent_fit = float(parent_prog.metrics[self.fitness_key])
        skip: set[str] = set()
        if insight is not None:
            mapped = map_operator(insight, parent)
            if mapped and is_applicable(parent, mapped):
                spec, rejected = self._try_child(
                    parent,
                    parent_prog,
                    mapped,
                    insight.substitute or insight.body,
                    insight,
                    parent_fit,
                )
                if spec is not None:
                    return spec
                if rejected:
                    return None
                skip.add(mapped)
            else:
                return None
        for op in self._candidate_ops(parent, None, run_step):
            if op in skip:
                continue
            spec, _rejected = self._try_child(
                parent, parent_prog, op, None, None, parent_fit
            )
            if spec is not None:
                return spec
        return None

    async def on_program_ingested(
        self,
        program: Program,
        storage: ProgramStorage,
        outcome: MutationOutcome | None = None,
    ) -> None:
        op = (program.metadata or {}).get("pmhctcr_operator")
        if not op:
            return
        parent_fit = float((program.metadata or {}).get("pmhctcr_parent_fitness") or 0.0)
        if outcome == MutationOutcome.REJECTED_ACCEPTOR or str(op).endswith("_REJECTED"):
            self.scheduler.update_reward(str(op), 0.0)
            return
        child_fit = 0.0
        if program.metrics and self.fitness_key in program.metrics:
            child_fit = float(program.metrics[self.fitness_key])
        reward = compute_bandit_reward(
            child_fit, parent_fit, higher_is_better=self.higher_is_better
        )
        self.scheduler.update_reward(str(op), reward)
