"""Restore the paper bundles into the paths expected by analysis scripts."""

from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import tarfile

REPO = Path(__file__).resolve().parents[1]
ARTIFACTS = REPO / "artifacts"


def _restore(archive: Path, destination: Path, mapping: str) -> int:
    count = 0
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle:
            if not member.isfile():
                raise ValueError(f"unexpected non-file in {archive}: {member.name}")
            rel = PurePosixPath(member.name)
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError(f"unsafe archive path: {member.name}")
            if mapping != "plain" and rel.as_posix() == "run_state.json":
                rel = PurePosixPath(f"storage/{mapping}/run_state.json")
            elif mapping != "plain" and rel.parts[0] == "programs":
                rel = PurePosixPath("storage") / mapping / rel
            target = destination.joinpath(*rel.parts)
            stream = bundle.extractfile(member)
            assert stream is not None
            data = stream.read()
            if target.exists():
                if target.read_bytes() != data:
                    raise FileExistsError(target)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=REPO)
    args = parser.parse_args()
    dest = args.destination.resolve()
    count = 0
    for mode in ("on", "off"):
        for run in range(1, 6):
            name = f"pmhctcr_final_terra_expert_{mode}_m100_r{run}"
            count += _restore(
                ARTIFACTS / f"expert_{mode}_r{run}.tar.gz",
                dest / "outputs" / name,
                "pmhctcr",
            )
    for mode, storage in (
        ("plain", "pmhctcr_final_plain"),
        ("memory", "pmhctcr_final_mem"),
    ):
        for run in range(1, 6):
            name = f"pmhctcr_final_terra_expert_on_{mode}_m100_r{run}"
            count += _restore(
                ARTIFACTS / f"{mode}_r{run}.tar.gz",
                dest / "outputs" / name,
                storage,
            )
    for run in range(1, 6):
        name = f"pmhctcr_final_terra_expert_on_bon_m100_r{run}"
        count += _restore(
            ARTIFACTS / f"bon_r{run}.tar.gz",
            dest / "outputs" / name,
            "plain",
        )
    count += _restore(
        ARTIFACTS / "search_controls.tar.gz",
        dest / "outputs" / "pmhctcr_final_terra_expert_on_m100_r1-5",
        "plain",
    )
    count += _restore(
        ARTIFACTS / "transfer_gen2.tar.gz",
        dest / "outputs" / "_analysis" / "injection_factorial",
        "plain",
    )
    print(f"Restored {count} files under {dest}")


if __name__ == "__main__":
    main()
