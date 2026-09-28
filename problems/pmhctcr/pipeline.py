"""pmhctcr DAG extras: validator timeout split from LLM/simple stages.

PDB GAT / MaSIF-patch fit runs inside ``CallValidatorFunction``. Terra smoke
used to set ``stage_timeout=240`` for every stage, so those fits died while
LLM stages did not need the extra budget. This builder keeps the short stage
timeout for IntraMemory / MutationSuggestion and gives the validator its own
cap. Global gigaevo defaults (3600 / 7200) are not reduced.
"""

from __future__ import annotations

from gigaevo.entrypoint.constants import (
    DEFAULT_SIMPLE_STAGE_TIMEOUT,
    MAX_CODE_LENGTH,
    MAX_MEMORY_MB,
    MAX_OUTPUT_SIZE,
)
from gigaevo.entrypoint.default_pipelines import (
    ChainStructuralMetricsFeature,
    DefaultPipelineBuilder,
    PipelineBuilder,
    PipelineFeature,
)
from gigaevo.entrypoint.evolution_context import EvolutionContext
from gigaevo.entrypoint.lineage_memory_pipeline import (
    GuidedMutationPipelineBuilder,
    MemoryGuidedMutationPipelineBuilder,
)
from gigaevo.programs.dag.automata import ExecutionOrderDependency
from gigaevo.programs.stages.mutation_suggestions import MutationSuggestionStage
from gigaevo.programs.stages.validator_metadata import ProgramMetadataValidatorStage


def resolve_validator_timeout(
    stage_timeout: float, validator_timeout: float | None
) -> float:
    """Never shrink below the DAG's simple-stage budget."""
    stage = float(stage_timeout)
    if validator_timeout is None:
        return stage
    return max(stage, float(validator_timeout))


class ValidatorTimeoutFeature(PipelineFeature):
    name = "validator_timeout"
    description = "Give CallValidatorFunction a longer budget than LLM stages."

    def __init__(self, timeout: float):
        self.timeout = float(timeout)

    def apply(self, builder: PipelineBuilder) -> None:
        problem_ctx = builder.ctx.problem_ctx
        validator_path = problem_ctx.problem_dir / "validate.py"
        timeout = self.timeout

        def _factory() -> ProgramMetadataValidatorStage:
            return ProgramMetadataValidatorStage(
                path=validator_path,
                function_name="validate",
                timeout=timeout,
                max_memory_mb=MAX_MEMORY_MB,
                max_output_size=MAX_OUTPUT_SIZE,
            )

        builder.replace_stage("CallValidatorFunction", _factory)


class PmhctcrGuidedPipelineBuilder(GuidedMutationPipelineBuilder):
    def __init__(self, *args, validator_timeout: float | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        vt = resolve_validator_timeout(self._stage_timeout, validator_timeout)
        self._validator_timeout = vt
        self.apply_feature(ValidatorTimeoutFeature(vt))


class PmhctcrPlainPipelineBuilder(DefaultPipelineBuilder):
    """Expert-on mutation DAG with intralineage feedback and memory cards off.

    ``MutationSuggestionStage`` still carries expert hypotheses into the
    mutator. It is not given an intra card, an ancestral trail, or memory
    cards. Legacy ``InsightsStage`` / ``LineageStage`` stay off too.
    """

    def __init__(
        self,
        ctx: EvolutionContext,
        *,
        dag_timeout: float = 3600.0,
        stage_timeout: float = DEFAULT_SIMPLE_STAGE_TIMEOUT,
        max_parallel: int | None = None,
        max_insights: int = 5,
        max_code_length: int = MAX_CODE_LENGTH,
        archive_gate_enabled: bool = False,
        program_format_feature: PipelineFeature | None = None,
        validator_timeout: float | None = None,
        intra_max_children: int = 24,
        mutation_mode: str | None = None,
        enable_optuna_stage: bool = False,
        optimization_time_budget: float | None = None,
        memory_block_last: bool = False,
        enable_chain_structural_metrics: bool = False,
    ):
        del intra_max_children, memory_block_last, optimization_time_budget
        if enable_optuna_stage:
            raise ValueError("PmhctcrPlainPipelineBuilder does not wire Optuna")
        super().__init__(
            ctx,
            dag_timeout=dag_timeout,
            stage_timeout=stage_timeout,
            max_parallel=max_parallel,
            max_insights=max_insights,
            max_code_length=max_code_length,
            archive_gate_enabled=archive_gate_enabled,
            include_legacy_feedback=False,
            program_format_feature=program_format_feature,
        )
        if enable_chain_structural_metrics:
            self.apply_feature(ChainStructuralMetricsFeature())
        vt = resolve_validator_timeout(self._stage_timeout, validator_timeout)
        self._validator_timeout = vt
        self.apply_feature(ValidatorTimeoutFeature(vt))
        self._wire_expert_only_suggestions(mutation_mode)

    def _wire_expert_only_suggestions(self, mutation_mode: str | None) -> None:
        stage_timeout = self._stage_timeout
        metrics_context = self.ctx.problem_ctx.metrics_context
        task_description = self.ctx.problem_ctx.task_description
        expert_hypotheses = self.ctx.problem_ctx.expert_hypotheses
        self.add_stage(
            "MutationSuggestionStage",
            lambda: MutationSuggestionStage(
                llm=self.ctx.llm_wrapper,
                storage=self.ctx.storage,
                metrics_context=metrics_context,
                task_description=task_description,
                expert_hypotheses=expert_hypotheses,
                max_insights=self._max_insights,
                timeout=stage_timeout,
                mutation_mode=mutation_mode,
                prompts_dir=self.ctx.prompts_dir,
                trail_max_depth=0,
                trail_max_ancestors=0,
            ),
        )
        self.add_data_flow_edge(
            "EvolutionaryStatisticsCollector",
            "MutationSuggestionStage",
            "evolutionary_statistics",
        )
        self.add_data_flow_edge(
            "MutationSuggestionStage", "MutationContextStage", "insights"
        )
        self.add_exec_dep(
            "MutationSuggestionStage",
            ExecutionOrderDependency.on_success("CallValidatorFunction"),
        )
        self.add_exec_dep(
            "MutationSuggestionStage",
            ExecutionOrderDependency.always_after("EnsureMetricsStage"),
        )
        self.add_exec_dep(
            "MutationSuggestionStage",
            ExecutionOrderDependency.always_after("EvolutionaryStatisticsCollector"),
        )
        if self._archive_gate_enabled:
            self.add_exec_dep(
                "MutationSuggestionStage",
                ExecutionOrderDependency.on_success("ArchivePotentialGateStage"),
            )


class PmhctcrMemoryGuidedPipelineBuilder(MemoryGuidedMutationPipelineBuilder):
    """Memory-card read/write path with the longer validator budget for PDB/MaSIF fits."""

    def __init__(self, *args, validator_timeout: float | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        vt = resolve_validator_timeout(self._stage_timeout, validator_timeout)
        self._validator_timeout = vt
        self.apply_feature(ValidatorTimeoutFeature(vt))
