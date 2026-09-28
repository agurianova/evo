"""Check saved paper scores and champion selection without private assets."""

from __future__ import annotations

import json
from pathlib import Path
import statistics
import tarfile

from scipy.stats import binomtest, wilcoxon

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
HOSTS = (
    "g2_r2_275ae460",
    "g2_r4_4996f5b6",
    "g2_r4_52c245fc",
    "g2_r4_8777238d",
    "g2_r4_c840f89c",
    "g2_r5_773338c2",
    "g2_r5_c8991aef",
)


def _json(bundle: tarfile.TarFile, name: str) -> dict:
    stream = bundle.extractfile(name)
    if stream is None:
        raise FileNotFoundError(name)
    return json.load(stream)


def _run(mode: str, run: int) -> tuple[float, float]:
    path = ARTIFACTS / f"expert_{mode}_r{run}.tar.gz"
    with tarfile.open(path, "r:gz") as bundle:
        names = [n for n in bundle.getnames() if n.startswith("programs/")]
        assert len(names) == 101, (path, len(names))
        programs = [_json(bundle, n) for n in names]
        candidates = [
            p
            for p in programs
            if p["state"] == "done"
            and (p.get("metrics") or {}).get("is_valid") == 1
            and (p.get("metrics") or {}).get("fitness") is not None
        ]
        best = max(candidates, key=lambda p: p["metrics"]["fitness"])
        meta = _json(bundle, "test_eval/champion_meta.json")
        assert meta["program_id"] == best["id"], (mode, run)
        result = _json(bundle, "test_eval/results.json")
        metrics = result["metrics"]
        assert metrics["is_valid"] == 1
        assert metrics["n_pmhc"] == 4
        return metrics["mean_aucpr"], metrics["mean_auc01"]


def _controls() -> None:
    expected = {
        "bon": (0.109, 0.498),
        "plain": (0.102, 0.495),
        "memory": (0.113, 0.514),
        "guided": (0.125, 0.502),
    }
    with tarfile.open(ARTIFACTS / "search_controls.tar.gz", "r:gz") as bundle:
        for mode, rounded in expected.items():
            values = [
                _json(bundle, f"search_controls_test_cache/{mode}_r{i}.json")["metrics"]
                for i in range(1, 6)
            ]
            medians = (
                statistics.median(v["mean_aucpr"] for v in values),
                statistics.median(v["mean_auc01"] for v in values),
            )
            assert tuple(round(x, 3) for x in medians) == rounded, (mode, medians)
            print(mode, *(f"{x:.6f}" for x in medians))
        seed = _json(bundle, "search_controls_test_cache/seed.json")["metrics"]
        assert round(seed["mean_aucpr"], 3) == 0.081
        assert round(seed["mean_auc01"], 3) == 0.477


def _transfer() -> None:
    expected = {
        "surface": (7, 6, 0.0052, 0.125, 0.219),
        "kqv": (6, 0, -0.0046, 0.031, 0.031),
        "both": (6, 0, -0.0110, 0.031, 0.031),
    }
    with tarfile.open(ARTIFACTS / "transfer_gen2.tar.gz", "r:gz") as bundle:
        for arm, values in expected.items():
            deltas = []
            for host in HOSTS:
                base = _json(bundle, f"{host}_bare.json")["metrics"]["mean_aucpr"]
                result = _json(bundle, f"{host}_{arm}.json")
                if result["metrics"]["is_valid"] != 1:
                    assert host == "g2_r4_52c245fc" and arm in ("kqv", "both")
                    assert "return_entropy" in result["reason"]
                    continue
                deltas.append(result["metrics"]["mean_aucpr"] - base)
            positive = sum(delta > 0 for delta in deltas)
            sign = binomtest(positive, len(deltas), 0.5).pvalue
            rank = wilcoxon(deltas, method="exact").pvalue
            got = (
                len(deltas),
                positive,
                round(statistics.median(deltas), 4),
                round(sign, 3),
                round(rank, 3),
            )
            assert got == values, (arm, got)
            print(arm, got)


def main() -> None:
    on = [_run("on", i) for i in range(1, 6)]
    off = [_run("off", i) for i in range(1, 6)]
    assert [round(x[0], 3) for x in on] == [0.194, 0.133, 0.110, 0.103, 0.125]
    assert round(statistics.median(x[0] for x in off), 3) == 0.093
    assert round(statistics.median(x[1] for x in off), 3) == 0.491
    print("expert-on median", statistics.median(x[0] for x in on))
    print("expert-off median", statistics.median(x[0] for x in off))
    _controls()
    _transfer()
    print("Saved results agree with Tables 2-3 and Figure 4 summaries.")


if __name__ == "__main__":
    main()
