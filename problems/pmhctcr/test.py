"""Score a saved program on the held-out test pMHCs.

Generated children are Python (``GENOTYPE_JSON`` + ``entrypoint()``).
Raw JSON genomes and the leftover ``cdr3_logistic.py`` seed are still accepted.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate import score_on_test


def _load_payload(path: Path):
    text = path.read_text()
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            from compiler import compile_genotype
        except ImportError:
            from problems.pmhctcr.compiler import compile_genotype

        return compile_genotype(json.loads(text))
    try:
        from codegen import exec_program
    except ImportError:
        from problems.pmhctcr.codegen import exec_program
    return exec_program(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("program", type=Path)
    args = parser.parse_args()
    metrics, artifact = score_on_test(_load_payload(args.program))
    print(json.dumps({"metrics": metrics, "artifact": artifact}, indent=2, default=str))


if __name__ == "__main__":
    main()
