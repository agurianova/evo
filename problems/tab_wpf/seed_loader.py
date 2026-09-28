from __future__ import annotations

from pathlib import Path

from gigaevo.database.program_storage import ProgramStorage
from gigaevo.programs.program import Program

from .graph import PredictorGraph, ReadoutConfig
from .sandbox_tasks import load_sandbox_manifest
from .synthetic_tasks import load_manifest


class TabWpfSeedLoader:
    """Create a neutral raw-readout baseline predictor graph."""

    def __init__(
        self,
        dataset: str = "california",
        problem_dir: str | Path | None = None,
        evaluation_mode: str = "real",
        task_bank: str | Path | None = None,
        task_split: str = "meta_train",
    ):
        self.dataset = dataset
        self.problem_dir = Path(problem_dir) if problem_dir is not None else None
        self.evaluation_mode = evaluation_mode
        self.task_bank = None if task_bank in (None, "") else Path(task_bank).resolve()
        self.task_split = task_split

    async def load(self, storage: ProgramStorage) -> list[Program]:
        graph = PredictorGraph(
            nodes=[],
            readout=ReadoutConfig(kind="ridge", alpha=1.0, include_raw=True),
        )
        program = Program(code=graph.to_json(), iteration=0)
        metadata = {
            "source": "initial_program",
            "strategy_name": "raw_readout_baseline",
            "evaluation_mode": self.evaluation_mode,
        }
        if self.evaluation_mode in {"synthetic", "sandbox"}:
            if self.task_bank is None:
                raise ValueError(
                    f"{self.evaluation_mode} seed loading requires task_bank"
                )
            manifest = (
                load_manifest(self.task_bank)
                if self.evaluation_mode == "synthetic"
                else load_sandbox_manifest(self.task_bank)
            )
            if self.evaluation_mode == "synthetic":
                metadata.update(
                    {
                        "synthetic_task_bank": str(self.task_bank),
                        "synthetic_bank_checksum": manifest["bank_checksum"],
                        "synthetic_meta_split": self.task_split,
                    }
                )
            else:
                metadata.update(
                    {
                        "sandbox_task_bank": str(self.task_bank),
                        "sandbox_bank_checksum": manifest["bank_checksum"],
                        "sandbox_meta_split": self.task_split,
                    }
                )
        elif self.evaluation_mode == "real":
            metadata["dataset"] = self.dataset
        else:
            raise ValueError(f"unknown evaluation_mode {self.evaluation_mode!r}")
        program.metadata = metadata
        await storage.add(program)
        return [program]
