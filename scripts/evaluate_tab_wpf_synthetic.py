#!/usr/bin/env python3
"""Evaluate a selected PredictorDAG on a frozen synthetic outer split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from problems.tab_wpf.synthetic_tasks import META_SPLITS, META_TEST  # noqa: E402
from problems.tab_wpf.validate import score_on_synthetic_split  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("graph_json", type=Path)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--split", choices=META_SPLITS, required=True)
    parser.add_argument(
        "--allow-meta-test",
        action="store_true",
        help="explicitly unseal synthetic meta-test for final reporting",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.split == META_TEST and not args.allow_meta_test:
        parser.error("--split meta_test requires --allow-meta-test")
    payload = json.loads(args.graph_json.read_text())
    metrics, artifact = score_on_synthetic_split(
        payload,
        bank_dir=args.bank,
        meta_split=args.split,
        allow_meta_test=args.allow_meta_test,
    )
    result = {"metrics": metrics, "artifact": artifact}
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
        print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

