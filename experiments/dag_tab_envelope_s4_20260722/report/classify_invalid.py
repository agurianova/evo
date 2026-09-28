"""Bucket an arm's invalid genomes by the validator error that rejected them.

The validator's message is the only place that distinguishes a malformed genome
(grammar failure) from a semantically wrong one (contract failure), and that
distinction is the whole claim about the structured-diff operator.

Usage: python classify_invalid.py <run_dir> <arm-slug>
"""

import base64
from collections import Counter
import json
from pathlib import Path
import re
import sys

VIZ = Path(__file__).parent / "viz"
ERROR = re.compile(
    rb"(FeatureExecutionError|FeatureGraphError|ValidationError|GraphValidationError)"
    rb"[^\x00-\x08\x0b-\x1f]{0,140}"
)


def main() -> None:
    run_dir, arm = Path(sys.argv[1]), sys.argv[2]
    root = run_dir / "storage" / "dag_tab" / "programs"
    counts = Counter()
    for f in root.glob("*.json"):
        d = json.loads(f.read_text())
        if d["metrics"].get("is_valid") != 0.0:
            continue
        stage = (d.get("stage_results") or {}).get("CallValidatorFunction") or {}
        raw = base64.b64decode(stage["output"]) if stage.get("output") else b""
        m = ERROR.search(raw)
        msg = m.group(0).decode(errors="replace").rstrip("�") if m else "(unclassified)"
        counts[re.sub(r"'[^']*'", "'…'", msg)[:130]] += 1

    path = VIZ / f"{arm}_invalid.json"
    path.write_text(json.dumps(counts.most_common(), indent=1))
    for msg, n in counts.most_common():
        print(f"{n:3d}  {msg}")


if __name__ == "__main__":
    main()
