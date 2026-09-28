"""Score a saved PredictorGraph JSON on the existing tabular test split."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

try:
    from .validate import score_on_test
except ImportError:
    from validate import score_on_test


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("program", type=Path)
    parser.add_argument("--dataset", default=os.environ.get("GIGAEVO_TABULAR_EVAL_DATASET", "california"))
    args = parser.parse_args()
    print(
        json.dumps(
            score_on_test(json.loads(args.program.read_text()), dataset=args.dataset),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
