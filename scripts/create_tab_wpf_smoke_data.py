#!/usr/bin/env python3
"""Create tiny deterministic TabM-layout datasets for Tab-WPF smoke tests.

These datasets are deliberately synthetic and must never be used for reported
quality numbers.  They only exercise regression, classification, missing-value,
binary-feature, categorical-feature, and unseen-category code paths.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def _write_dataset(
    root: Path,
    name: str,
    *,
    task_type: str,
    splits: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray]],
) -> None:
    folder = root / name
    if folder.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing smoke dataset directory: {folder}"
        )
    folder.mkdir(parents=True)

    first_num, first_bin, first_cat, _ = splits["train"]
    info: dict[str, int | str] = {
        "task_type": task_type,
        "n_num_features": int(first_num.shape[1]),
        "n_bin_features": int(first_bin.shape[1]),
        "n_cat_features": 0 if first_cat is None else int(first_cat.shape[1]),
    }
    if task_type == "binclass":
        info["n_classes"] = 2
    (folder / "info.json").write_text(json.dumps(info, indent=2) + "\n")

    for split, (x_num, x_bin, x_cat, y) in splits.items():
        np.save(folder / f"X_num_{split}.npy", x_num)
        np.save(folder / f"X_bin_{split}.npy", x_bin)
        if x_cat is not None:
            np.save(folder / f"X_cat_{split}.npy", x_cat)
        np.save(folder / f"Y_{split}.npy", y)


def _split_rows(
    x_num: np.ndarray,
    x_bin: np.ndarray,
    x_cat: np.ndarray | None,
    y: np.ndarray,
) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray]]:
    bounds = {"train": (0, 240), "val": (240, 320), "test": (320, 400)}
    return {
        split: (
            x_num[start:end],
            x_bin[start:end],
            None if x_cat is None else x_cat[start:end],
            y[start:end],
        )
        for split, (start, end) in bounds.items()
    }


def _california(rng: np.random.Generator):
    x = rng.normal(size=(400, 8))
    x[::37, 2] = np.nan
    x_bin = (rng.random((400, 1)) > 0.55).astype(np.float64)
    clean = np.nan_to_num(x, nan=0.0)
    y = (
        1.8 * clean[:, 0]
        - 0.9 * clean[:, 1]
        + 0.7 * np.sin(clean[:, 3])
        + 0.45 * clean[:, 4] * clean[:, 5]
        + 0.3 * x_bin[:, 0]
        + rng.normal(scale=0.15, size=400)
    )
    return _split_rows(x, x_bin, None, y.astype(np.float64))


def _adult(rng: np.random.Generator):
    x = rng.normal(size=(400, 5))
    x[::41, 1] = np.nan
    x_bin = (rng.random((400, 2)) > np.array([0.45, 0.7])).astype(np.float64)
    occupations = np.array(["tech", "sales", "service", "admin"], dtype=object)
    education = np.array(["school", "college", "graduate"], dtype=object)
    x_cat = np.column_stack(
        [
            rng.choice(occupations, size=400),
            rng.choice(education, size=400),
        ]
    ).astype(object)
    x_cat[::53, 0] = None
    # Exercise the unseen-category path without contaminating the train vocabulary.
    x_cat[350, 0] = "unseen_test_level"
    clean = np.nan_to_num(x, nan=0.0)
    logit = (
        1.2 * clean[:, 0]
        - 0.8 * clean[:, 2]
        + 0.6 * x_bin[:, 0]
        + 0.7 * (x_cat[:, 0] == "tech")
        + 0.8 * (x_cat[:, 1] == "graduate")
        + rng.normal(scale=0.4, size=400)
    )
    y = (logit > np.median(logit)).astype(np.int64)
    return _split_rows(x, x_bin, x_cat, y)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output_root",
        type=Path,
        help="New/existing root under which california/ and adult/ are created",
    )
    args = parser.parse_args()

    root = args.output_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20260818)
    _write_dataset(root, "california", task_type="regression", splits=_california(rng))
    _write_dataset(root, "adult", task_type="binclass", splits=_adult(rng))
    print(root)


if __name__ == "__main__":
    main()
