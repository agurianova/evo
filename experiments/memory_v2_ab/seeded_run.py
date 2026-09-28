#!/usr/bin/env python3
"""Seed process-local search randomness, then execute the ordinary runner."""

from __future__ import annotations

import os
from pathlib import Path
import random
import runpy
import sys

import numpy as np


def main() -> None:
    seed = int(os.environ["GIGAEVO_EXPERIMENT_SEED"])
    random.seed(seed)
    np.random.seed(seed)
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))

    import gigaevo

    package_path = Path(gigaevo.__file__).resolve()
    if not package_path.is_relative_to(repo_root):
        raise RuntimeError(
            f"gigaevo resolved outside the experiment worktree: {package_path}"
        )
    print(
        f"[Experiment] code_root={repo_root} seed={seed}",
        file=sys.stderr,
        flush=True,
    )
    runpy.run_path(
        str(repo_root / "run.py"),
        run_name="__main__",
    )


if __name__ == "__main__":
    main()
