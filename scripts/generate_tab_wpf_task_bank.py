#!/usr/bin/env python3
"""Generate or verify the frozen 100-task Tab-WPF synthetic bank."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from problems.tab_wpf.synthetic_tasks import (  # noqa: E402
    DEFAULT_MASTER_SEED,
    generate_task_bank,
    verify_task_bank,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--seed", type=int, default=DEFAULT_MASTER_SEED)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="verify an existing bank instead of generating it",
    )
    args = parser.parse_args()

    if args.verify_only:
        manifest = verify_task_bank(args.output_dir)
    else:
        manifest = generate_task_bank(args.output_dir, master_seed=args.seed)
    print(
        json.dumps(
            {
                "path": str(args.output_dir.expanduser().resolve()),
                "task_count": manifest["task_count"],
                "split_counts": manifest["split_counts"],
                "family_counts": manifest["family_counts"],
                "bank_checksum": manifest["bank_checksum"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

