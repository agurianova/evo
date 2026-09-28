#!/usr/bin/env python3
"""Factorial test injection on the seven frozen generation-2 hosts.

Donors are fixed: r1 3f46e909 _surface, r4 0fb367bd _FusionModel.
The donor child's entropy term in fit() is not copied. Outcomes use
score_on_test (train fit, four held-out pMHCs).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tarfile

import torch

REPO = Path(__file__).resolve().parents[2]
PROBLEM = REPO / "problems" / "pmhctcr"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(PROBLEM))

os.environ.setdefault("OMP_NUM_THREADS", "8")
os.environ.setdefault("MKL_NUM_THREADS", "8")

torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "8")))

from codegen import exec_program  # noqa: E402
from validate import score_on_test  # noqa: E402

GEN2_HOSTS = (
    (2, "275ae460"),
    (4, "4996f5b6"),
    (4, "52c245fc"),
    (4, "8777238d"),
    (4, "c840f89c"),
    (5, "773338c2"),
    (5, "c8991aef"),
)
SURFACE_DONOR = (1, "3f46e909")
KQV_DONOR = (4, "0fb367bd")
OUT = REPO / "outputs" / "_analysis" / "injection_factorial"
ARMS = ("bare", "surface", "kqv", "both")


def program_code(run: int, prefix: str) -> str:
    storage = (
        REPO
        / "outputs"
        / f"pmhctcr_final_terra_expert_on_m100_r{run}"
        / "storage"
        / "pmhctcr"
        / "programs"
    )
    hits = list(storage.glob(f"{prefix}*.json"))
    if len(hits) == 1:
        return json.loads(hits[0].read_text())["code"]
    archive = REPO / "artifacts" / f"expert_on_r{run}.tar.gz"
    if archive.is_file():
        with tarfile.open(archive, "r:gz") as bundle:
            names = [
                name
                for name in bundle.getnames()
                if name.startswith(f"programs/{prefix}") and name.endswith(".json")
            ]
            if len(names) == 1:
                member = bundle.extractfile(names[0])
                assert member is not None
                return json.loads(member.read())["code"]
    raise FileNotFoundError(f"r{run} {prefix}: {len(hits)} local files")


def block(src: str, start: str) -> str:
    lines = src.splitlines()
    s = next(i for i, ln in enumerate(lines) if ln.startswith(start))
    e = s + 1
    while e < len(lines) and not (
        lines[e].startswith("def ") or lines[e].startswith("class ")
    ):
        e += 1
    return "\n".join(lines[s:e]).rstrip() + "\n"


def replace_block(src: str, start: str, donor: str) -> str:
    lines = src.splitlines()
    s = next(i for i, ln in enumerate(lines) if ln.startswith(start))
    e = s + 1
    while e < len(lines) and not (
        lines[e].startswith("def ") or lines[e].startswith("class ")
    ):
        e += 1
    merged = lines[:s] + donor.splitlines() + lines[e:]
    text = "\n".join(merged)
    if src.endswith("\n"):
        text += "\n"
    if text.count("\n" + start) + int(text.startswith(start)) != 1:
        raise RuntimeError(f"expected exactly one {start!r}")
    return text


def build(host_src: str, surface: str, kqv: str, arm: str) -> str:
    if arm == "bare":
        return host_src
    if arm == "surface":
        return replace_block(host_src, "def _surface", surface)
    if arm == "kqv":
        return replace_block(host_src, "class _FusionModel", kqv)
    if arm == "both":
        return replace_block(
            replace_block(host_src, "def _surface", surface),
            "class _FusionModel",
            kqv,
        )
    raise ValueError(arm)


def evaluate(source: str) -> dict:
    payload = exec_program(source)
    metrics, artifact = score_on_test(payload)
    reason = artifact.get("reason")
    per = artifact.get("per_pmhc") or {}
    return {
        "metrics": {
            k: metrics.get(k)
            for k in (
                "fitness",
                "is_valid",
                "mean_aucpr",
                "mean_auc01",
                "min_aucpr",
                "min_auc01",
                "n_pmhc",
            )
        },
        "reason": reason,
        "per_pmhc": {
            k: {
                "aucpr": v.get("aucpr"),
                "auc0.1": v.get("auc0.1"),
                "n": v.get("n"),
                "n_pos": v.get("n_pos"),
            }
            for k, v in per.items()
        },
    }


SEED = REPO / "problems" / "pmhctcr" / "initial_programs" / "python_patch_seed.py"


def main() -> None:
    arm = sys.argv[1] if len(sys.argv) > 1 else None
    which = sys.argv[2] if len(sys.argv) > 2 else None
    surface = block(program_code(*SURFACE_DONOR), "def _surface")
    kqv = block(program_code(*KQV_DONOR), "class _FusionModel")
    if "self.key = torch.nn.ModuleList" not in kqv or "reciprocal" not in surface:
        raise RuntimeError("donor blocks do not contain the mechanisms")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "donor_surface.py").write_text(surface)
    (OUT / "donor_kqv.py").write_text(kqv)

    if which == "seed":
        jobs = (
            [("seed", a, None) for a in ARMS] if arm is None else [("seed", arm, None)]
        )
    elif which and ":" in which:
        run_s, prefix = which.split(":", 1)
        jobs = (
            [(int(run_s), a, prefix) for a in ARMS]
            if arm is None
            else [(int(run_s), arm, prefix)]
        )
    else:
        if which is not None and not which.isdigit():
            raise ValueError("host must be a run number or run:program-id")
        hosts = [
            (r, prefix) for r, prefix in GEN2_HOSTS if which is None or r == int(which)
        ]
        if not hosts:
            raise ValueError(f"no generation-2 hosts for run {which}")
        arms = ARMS if arm is None else (arm,)
        jobs = [(r, a, prefix) for r, prefix in hosts for a in arms]
    for r, a, prefix in jobs:
        if r == "seed":
            host_src = SEED.read_text()
            host_name = "python_patch_seed"
            stem = f"rseed_{a}"
        elif prefix:
            host_src = program_code(r, prefix)
            host_name = prefix
            stem = f"g2_r{r}_{prefix}_{a}"
        src = build(host_src, surface, kqv, a)
        (OUT / f"{stem}.py").write_text(src)
        if arm is None and prefix is None and r != "seed":
            exec_program(src)
            print(f"compiled r{r} {a}", flush=True)
            continue
        if arm is None:
            exec_program(src)
            print(f"compiled {stem}", flush=True)
            continue
        result = evaluate(src)
        out = {"run": r, "arm": a, "host": host_name, **result}
        (OUT / f"{stem}.json").write_text(json.dumps(out, indent=2, default=str))
        print(
            json.dumps(
                {
                    "run": r,
                    "host": host_name,
                    "arm": a,
                    "metrics": result["metrics"],
                    "reason": result["reason"],
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
