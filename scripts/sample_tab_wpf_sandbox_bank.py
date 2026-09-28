#!/usr/bin/env python3
"""Create a deterministic, family-balanced cohort from a frozen sandbox bank."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from problems.tab_wpf.sandbox_tasks import (  # noqa: E402
    META_SPLITS,
    load_sandbox_manifest,
    sample_sandbox_records,
)


def _checksum(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--split", choices=META_SPLITS, required=True)
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite existing cohort: {args.output}")

    manifest = load_sandbox_manifest(args.bank)
    records = sample_sandbox_records(
        args.bank,
        meta_split=args.split,
        sample_size=args.size,
        sample_seed=args.seed,
    )
    payload: dict[str, object] = {
        "schema_version": 1,
        "bank_checksum": manifest["bank_checksum"],
        "meta_split": args.split,
        "sample_seed": args.seed,
        "task_count": len(records),
        "task_ids": [record["task_id"] for record in records],
        "family_counts": {
            family: sum(record["family"] == family for record in records)
            for family in manifest["families"]
        },
        "primary_stratum_count": len(
            {record["primary_stratum_id"] for record in records}
        ),
    }
    payload["cohort_checksum"] = _checksum(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
