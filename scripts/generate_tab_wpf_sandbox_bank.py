#!/usr/bin/env python3
"""Generate or strictly verify a balanced Tab-WPF sandbox bank."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from problems.tab_wpf.sandbox_tasks import (  # noqa: E402
    DEFAULT_MASTER_SEED,
    PILOT_TASKS_PER_PRIMARY_STRATUM,
    generate_sandbox_bank,
    verify_sandbox_bank,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--seed", type=int, default=DEFAULT_MASTER_SEED)
    parser.add_argument(
        "--tasks-per-primary-stratum",
        type=int,
        default=PILOT_TASKS_PER_PRIMARY_STRATUM,
        help=(
            "positive multiple of 5; 5 creates the 1,260-task pilot and "
            "50 creates the 12,600-task full bank"
        ),
    )
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()

    manifest = (
        verify_sandbox_bank(args.output_dir)
        if args.verify_only
        else generate_sandbox_bank(
            args.output_dir,
            master_seed=args.seed,
            tasks_per_primary_stratum=args.tasks_per_primary_stratum,
            workers=args.workers,
        )
    )
    print(
        json.dumps(
            {
                "path": str(args.output_dir.expanduser().resolve()),
                "task_count": manifest["task_count"],
                "primary_stratum_count": manifest["primary_stratum_count"],
                "tasks_per_primary_stratum": manifest["tasks_per_primary_stratum"],
                "split_counts": manifest["split_counts"],
                "family_counts": manifest["family_counts"],
                "parameter_support": manifest["parameter_support"],
                "bank_checksum": manifest["bank_checksum"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
