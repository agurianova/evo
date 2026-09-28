from __future__ import annotations

from pathlib import Path
import sys

PROBLEM_DIR = Path(__file__).resolve().parents[2] / "problems" / "pmhctcr"
sys.path.insert(0, str(PROBLEM_DIR))

from split import assert_no_pmhc_leak, fold_stats, load_samples, load_split  # noqa: E402


def test_r0_no_pmhc_leak_keeps_all_pairs():
    df = load_samples()
    split = load_split()
    assert_no_pmhc_leak(split)
    assert len(split["pmhc"]["train"]) == 12
    assert len(split["pmhc"]["val"]) == 4
    assert len(split["pmhc"]["test"]) == 4
    assert split["dropped"] == 0
    stats = fold_stats(df, split["pmhc"])
    assert sum(stats[f]["n"] for f in ("train", "val", "test")) == len(df)
    for fold in ("train", "val", "test"):
        assert stats[fold]["n_pmhc"] == len(split["pmhc"][fold])
        for rec in stats[fold]["per_pmhc"].values():
            assert rec["n"] >= 2
            assert rec["n_pos"] >= 1
            assert rec["n_pos"] < rec["n"]


def test_r0_allele_counts():
    df = load_samples()
    split = load_split()
    allele = df.groupby("mhc_epitope_id")["mhca_allele"].first()
    for fold, expected in (
        ("train", {"HLA-A*02:01": 6, "HLA-B*40:01": 6}),
        ("val", {"HLA-A*02:01": 2, "HLA-B*40:01": 2}),
        ("test", {"HLA-A*02:01": 2, "HLA-B*40:01": 2}),
    ):
        got = allele.loc[list(split["pmhc"][fold])].value_counts().to_dict()
        assert got == expected
