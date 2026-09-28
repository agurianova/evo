from __future__ import annotations

from functools import cache
import json
from pathlib import Path
import re

from gigaevo.problems.context import ProblemContext
from problems.tabular._common import tabular_data
from problems.tab_wpf.sandbox_tasks import load_sandbox_manifest

_SECTION_PATTERN = re.compile(
    r"^(TASK|DATASET|COLUMNS|CONTRACT|PROTOCOL|STRATEGY|CONSTRAINTS)\b.*$",
    re.MULTILINE,
)


def _extract_dataset_context(text: str) -> str:
    sections: dict[str, str] = {}
    matches = list(_SECTION_PATTERN.finditer(text))
    for index, match in enumerate(matches):
        start = match.start()
        stop = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[start:stop].strip()

    selected = [
        sections[name] for name in ("TASK", "DATASET", "COLUMNS") if name in sections
    ]
    if not selected:
        raise ValueError(
            "tabular task description has no TASK, DATASET, or COLUMNS sections"
        )
    return "\n\n".join(selected)


@cache
def _dataset_description_path(tabular_root: Path, dataset: str) -> Path | None:
    direct = tabular_root / dataset / "task_description.txt"
    if direct.is_file():
        return direct
    for marker in sorted(tabular_root.glob("*/*/dataset_id.txt")):
        if marker.read_text().strip() == dataset:
            description = marker.parent / "task_description.txt"
            if description.is_file():
                return description
    return None


class TabWpfProblemContext(ProblemContext):
    """Reverse-SCM operator ABI combined with selected tabular dataset semantics."""

    def __init__(
        self,
        problem_dir: str | Path,
        dataset: str = "california",
        evaluation_mode: str = "real",
        task_bank: str | Path | None = None,
        task_split: str = "meta_train",
    ):
        super().__init__(problem_dir)
        self.dataset = dataset
        self.evaluation_mode = evaluation_mode
        self.task_bank = None if task_bank in (None, "") else Path(task_bank).resolve()
        self.task_split = task_split
        if self.evaluation_mode in {"synthetic", "sandbox"}:
            if self.task_bank is None:
                raise ValueError(
                    f"{self.evaluation_mode} tab_wpf requires problem.task_bank"
                )
            if not (self.task_bank / "manifest.json").is_file():
                raise FileNotFoundError(
                    f"{self.evaluation_mode} task bank has no manifest: {self.task_bank}"
                )

    def _tabular_root(self) -> Path:
        for ancestor in (self.problem_dir, *self.problem_dir.parents):
            candidate = ancestor / "tabular"
            if candidate.is_dir():
                return candidate
        raise FileNotFoundError(
            f"Missing canonical tabular problem root above {self.problem_dir}"
        )

    @property
    def task_description(self) -> str:
        abi = super().task_description
        if self.evaluation_mode == "sandbox":
            manifest = load_sandbox_manifest(self.task_bank)
            count = manifest.get("split_counts", {}).get(self.task_split, "?")
            support = manifest.get("parameter_support", {})
            return (
                f"{abi}\n\n"
                "RESTRICTED CLASSIFICATION SANDBOX\n"
                f"evaluation split: {self.task_split}; {count} frozen tasks; "
                f"bank checksum {manifest.get('bank_checksum', '<missing>')}.\n"
                "The hidden prior contains only linear, tree-rule, MLP, and "
                "mixed GeneratorDAGs. Raw inputs are not counted as generator "
                "nodes; every hidden graph has 2--8 productive composition "
                "blocks including its class-logit head. Tree and MLP blocks "
                "may contain different amounts of internal computation.\n"
                f"Controlled support: n_rows={support.get('n_rows')}; "
                f"n_features={support.get('n_features')}; categorical_fraction="
                f"{support.get('categorical_fraction')}; max_cardinality="
                f"{support.get('max_categorical_cardinality')}; n_classes="
                f"{support.get('n_classes')}.\n"
                "For every task the predictor receives only X_context, "
                "y_context, X_query, task type, and class count. Query labels "
                "and the task's hidden GeneratorDAG remain in the evaluator. "
                "The task score is one minus model log loss divided by the "
                "Laplace-smoothed context-prior log loss, clipped to [-1, 1]. "
                "Fitness is averaged within prior family and then equally "
                "across families. The statistical unit is one complete task."
            )
        if self.evaluation_mode == "synthetic":
            manifest_path = self.task_bank / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            count = manifest.get("split_counts", {}).get(self.task_split, "?")
            summary = (
                f"{count} frozen tasks from bank "
                f"{manifest.get('bank_checksum', '<missing>')}"
            )
            return (
                f"{abi}\n\n"
                "SYNTHETIC META-TRAIN PROTOCOL\n"
                f"evaluation split: {self.task_split}; {summary}.\n"
                "For every task, the predictor receives only X_context, "
                "y_context, and X_query. Query labels and each hidden "
                "GeneratorDAG are retained by the evaluator. Fitness is "
                "clipped query R2, averaged within generator family and then "
                "equally across families; the independent unit is one task. "
                "The genome must remain feature-agnostic and must not assume a "
                "fixed number, order, or type of columns."
            )
        if self.evaluation_mode != "real":
            raise ValueError(f"unknown tab_wpf evaluation mode {self.evaluation_mode!r}")
        dataset_path = _dataset_description_path(self._tabular_root(), self.dataset)
        if dataset_path is not None:
            dataset_context = _extract_dataset_context(dataset_path.read_text())
        else:
            dataset = tabular_data.load_dataset(self.dataset)
            task = {
                tabular_data.REGRESSION: "TABULAR REGRESSION",
                tabular_data.BINCLASS: "TABULAR BINARY CLASSIFICATION",
                tabular_data.MULTICLASS: "TABULAR MULTICLASS CLASSIFICATION",
            }[dataset.task_type]
            dataset_context = (
                f"TASK — {task} ({self.dataset})\n\n"
                f"{tabular_data.describe_columns(self.dataset)}"
            )
        return (
            f"{abi}\n\n"
            "SELECTED DATASET CONTEXT\n"
            f"dataset id: {self.dataset}\n"
            "The predictor graph is feature-agnostic: it never names raw columns. "
            "Runtime encodes the assembled table into a typed matrix before DAG "
            "execution.\n\n"
            f"{dataset_context}"
        )
